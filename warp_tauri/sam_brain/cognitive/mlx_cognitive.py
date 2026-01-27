"""
MLX Cognitive Engine for SAM

Connects the cognitive pipeline to MLX inference with:
- Dynamic model selection (1.5B vs 3B)
- Token budget management
- Streaming generation
- Quality validation
- Escalation handling
- Resource-aware operation (prevents freezes on 8GB systems)
"""

import time
import threading
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Generator
from dataclasses import dataclass, field
from enum import Enum

# Resource management for stability
from .resource_manager import ResourceManager, ResourceLevel, get_safe_max_tokens

# MLX imports (lazy loaded to avoid import errors when MLX not available)
_mlx_available = None
_load = None
_generate = None


def _ensure_mlx():
    """Lazy load MLX to avoid import errors."""
    global _mlx_available, _load, _generate
    if _mlx_available is None:
        try:
            from mlx_lm import load, generate
            _load = load
            _generate = generate
            _mlx_available = True
        except ImportError:
            _mlx_available = False
    return _mlx_available


class ModelSize(Enum):
    """Available model sizes."""
    SMALL = "1.5b"  # 512 context, 4 layers
    LARGE = "3b"    # 256 context, 2 layers


@dataclass
class ModelConfig:
    """Configuration for a model adapter."""
    name: str
    base_model: str
    adapter_path: Path
    max_context_tokens: int
    parameter_count: str
    lora_layers: int
    memory_footprint_mb: int
    strengths: List[str]


@dataclass
class GenerationConfig:
    """Configuration for generation request."""
    max_tokens: int = 150
    temperature: float = 0.7
    top_p: float = 0.9
    stop_tokens: List[str] = field(default_factory=lambda: ["<|im_end|>", "<|end|>", "</s>"])
    stream: bool = False
    repetition_penalty: float = 1.1


@dataclass
class GenerationResult:
    """Result from generation."""
    response: str
    tokens_generated: int
    generation_time_ms: int
    model_used: str
    confidence: float
    repetition_detected: bool
    escalation_recommended: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


# Model configurations
MODEL_CONFIGS = {
    "1.5b": ModelConfig(
        name="sam_lora_1.5b_v2",
        base_model="mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        adapter_path=Path("/Volumes/David External/sam_models/adapters/sam_lora_1.5b_v2"),
        max_context_tokens=512,
        parameter_count="1.5B",
        lora_layers=4,
        memory_footprint_mb=1200,
        strengths=["general", "code", "chat", "longer_context"]
    ),
    "3b": ModelConfig(
        name="sam_lora_3b_lite",
        base_model="mlx-community/Qwen2.5-3B-Instruct-4bit",
        adapter_path=Path("/Volumes/David External/sam_models/adapters/sam_lora_3b_lite"),
        max_context_tokens=256,
        parameter_count="3B",
        lora_layers=2,
        memory_footprint_mb=2400,
        strengths=["complex_reasoning", "analysis", "quality"]
    )
}

# System prompts by size
SYSTEM_PROMPTS = {
    "full": """You are SAM, a confident and charming AI assistant.

Personality: Witty, direct, occasionally flirtatious, genuinely helpful.
Voice: Confident but warm, uses humor naturally, avoids being sycophantic.

Guidelines:
- Be concise and direct
- Use personality naturally, don't force it
- Admit uncertainty when appropriate
- Remember context from the conversation""",

    "medium": """You are SAM, a confident AI assistant. Be witty, direct, and helpful. Use natural humor. Be concise.""",

    "minimal": """SAM: Confident, witty AI. Be direct and helpful."""
}


class MLXCognitiveEngine:
    """
    Main engine for MLX-based generation integrated with cognitive systems.

    Features:
    - Dynamic model selection based on query complexity
    - Token budget management for hardware limits
    - Streaming generation support
    - Quality validation with repetition detection
    - Escalation to Claude when needed
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory"):
        """Initialize the MLX cognitive engine."""
        self.db_path = Path(db_path)

        # Resource manager for stability
        self._resource_manager = ResourceManager()

        # Model state
        self._current_model_key: Optional[str] = None
        self._model = None
        self._tokenizer = None
        self._model_lock = threading.Lock()

        # Statistics
        self._generation_count = 0
        self._total_tokens = 0
        self._escalation_count = 0
        self._resource_rejections = 0

    def generate(
        self,
        prompt: str,
        context: str,
        cognitive_state: Dict[str, Any],
        config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        Generate response using MLX with cognitive integration.

        Args:
            prompt: User input
            context: Compressed context from cognitive orchestrator
            cognitive_state: State from CognitiveControl
            config: Generation configuration

        Returns:
            GenerationResult with response and metadata
        """
        if not _ensure_mlx():
            return self._fallback_response(prompt, "MLX not available")

        config = config or GenerationConfig()
        start_time = time.time()

        # Check resource availability first
        can_proceed, reason = self._resource_manager.can_perform_heavy_operation()
        if not can_proceed:
            self._resource_rejections += 1
            # Return a polite waiting message instead of failing
            return GenerationResult(
                response=f"I need a moment - {reason}. Try again shortly.",
                tokens_generated=0,
                generation_time_ms=0,
                model_used="none",
                confidence=0.5,
                repetition_detected=False,
                escalation_recommended=False,
                metadata={"resource_limited": True, "reason": reason}
            )

        # Cap max_tokens based on resource level
        safe_max_tokens = get_safe_max_tokens()
        if config.max_tokens > safe_max_tokens:
            config.max_tokens = safe_max_tokens

        # Select model based on context and complexity
        model_key, selection_reason = self._select_model(
            prompt, context, cognitive_state
        )

        # Force smaller model if resources are low
        resource_level = self._resource_manager.get_resource_level()
        if resource_level in (ResourceLevel.CRITICAL, ResourceLevel.LOW):
            model_key = "1.5b"
            selection_reason = f"Resource-limited to 1.5B ({resource_level.value})"

        # Load model if needed (with resource tracking)
        try:
            with self._resource_manager.heavy_operation_context():
                model, tokenizer = self._load_model(model_key)
        except Exception as e:
            # Try fallback model
            fallback_key = "1.5b" if model_key == "3b" else "3b"
            try:
                with self._resource_manager.heavy_operation_context():
                    model, tokenizer = self._load_model(fallback_key)
                model_key = fallback_key
            except Exception as e2:
                return self._fallback_response(prompt, f"Model load failed: {e2}")

        # Build formatted prompt
        model_config = MODEL_CONFIGS[model_key]
        formatted_prompt = self._format_prompt(
            prompt, context, cognitive_state, tokenizer, model_config
        )

        # Generate response
        try:
            raw_response = _generate(
                model,
                tokenizer,
                prompt=formatted_prompt,
                max_tokens=config.max_tokens,
                verbose=False
            )
        except Exception as e:
            return self._fallback_response(prompt, f"Generation failed: {e}")

        # Clean and validate response
        cleaned_response, repetition_detected = self._clean_response(raw_response)

        # Calculate confidence
        confidence = self._calculate_confidence(
            cleaned_response, cognitive_state, repetition_detected
        )

        # Determine if escalation needed
        escalation_recommended = self._should_escalate(
            cleaned_response, confidence, repetition_detected
        )

        # Update statistics
        self._generation_count += 1
        tokens_generated = len(cleaned_response.split())
        self._total_tokens += tokens_generated
        if escalation_recommended:
            self._escalation_count += 1

        generation_time = int((time.time() - start_time) * 1000)

        return GenerationResult(
            response=cleaned_response,
            tokens_generated=tokens_generated,
            generation_time_ms=generation_time,
            model_used=model_key,
            confidence=confidence,
            repetition_detected=repetition_detected,
            escalation_recommended=escalation_recommended,
            metadata={
                "selection_reason": selection_reason,
                "model_config": model_config.name,
                "formatted_prompt_tokens": len(formatted_prompt.split())
            }
        )

    def generate_streaming(
        self,
        prompt: str,
        context: str,
        cognitive_state: Dict[str, Any],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, GenerationResult]:
        """
        Streaming generation for real-time output.

        Yields tokens as they're generated, returns GenerationResult at end.
        """
        if not _ensure_mlx():
            yield "MLX not available for streaming."
            return self._fallback_response(prompt, "MLX not available")

        config = config or GenerationConfig()
        config.stream = True
        start_time = time.time()

        # Check resource availability first
        can_proceed, reason = self._resource_manager.can_perform_heavy_operation()
        if not can_proceed:
            self._resource_rejections += 1
            yield f"I need a moment - {reason}."
            return self._fallback_response(prompt, reason)

        # Cap max_tokens based on resource level
        safe_max_tokens = get_safe_max_tokens()
        if config.max_tokens > safe_max_tokens:
            config.max_tokens = safe_max_tokens

        # Select and load model
        model_key, selection_reason = self._select_model(prompt, context, cognitive_state)

        # Force smaller model if resources are low
        resource_level = self._resource_manager.get_resource_level()
        if resource_level in (ResourceLevel.CRITICAL, ResourceLevel.LOW):
            model_key = "1.5b"

        try:
            with self._resource_manager.heavy_operation_context():
                model, tokenizer = self._load_model(model_key)
        except Exception as e:
            yield f"Error loading model: {e}"
            return self._fallback_response(prompt, str(e))

        # Format prompt
        model_config = MODEL_CONFIGS[model_key]
        formatted_prompt = self._format_prompt(
            prompt, context, cognitive_state, tokenizer, model_config
        )

        # Stream generation
        full_response = []
        repetition_buffer = []
        repetition_detected = False

        try:
            # Use mlx_lm.stream_generate for real streaming
            from mlx_lm import stream_generate
            from mlx_lm.sample_utils import make_sampler

            sampler = make_sampler(temp=config.temperature)

            for response in stream_generate(
                model,
                tokenizer,
                prompt=formatted_prompt,
                max_tokens=config.max_tokens,
                sampler=sampler,
            ):
                # stream_generate yields GenerationResponse objects
                token = response.text if hasattr(response, 'text') else str(response)
                # Check for repetition in buffer
                repetition_buffer.append(token)
                if len(repetition_buffer) > 30:
                    buffer_text = "".join(repetition_buffer[-30:])
                    if self._detect_repetition_live(buffer_text.split()):
                        repetition_detected = True
                        break
                    repetition_buffer = repetition_buffer[-20:]

                full_response.append(token)
                yield token

        except Exception as e:
            yield f"\nError: {e}"
            return self._fallback_response(prompt, str(e))

        # Clean final response
        final_text = " ".join(full_response)
        cleaned, rep_found = self._clean_response(final_text)
        repetition_detected = repetition_detected or rep_found

        confidence = self._calculate_confidence(cleaned, cognitive_state, repetition_detected)
        escalation_recommended = self._should_escalate(cleaned, confidence, repetition_detected)

        generation_time = int((time.time() - start_time) * 1000)

        return GenerationResult(
            response=cleaned,
            tokens_generated=len(cleaned.split()),
            generation_time_ms=generation_time,
            model_used=model_key,
            confidence=confidence,
            repetition_detected=repetition_detected,
            escalation_recommended=escalation_recommended,
            metadata={"selection_reason": selection_reason, "streamed": True}
        )

    def _select_model(
        self,
        prompt: str,
        context: str,
        cognitive_state: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Select optimal model based on multiple factors.

        Returns: (model_key, reason)
        """
        context_tokens = len(context.split()) + len(prompt.split())

        # Hard constraint: context size
        if context_tokens > 256:
            return "1.5b", "context_exceeds_3b_limit"

        # Hard constraint: memory pressure
        memory_pressure = self._get_memory_pressure()
        if memory_pressure > 0.85:
            return "1.5b", "high_memory_pressure"

        # Soft preferences
        complexity = self._estimate_complexity(prompt)
        confidence_needed = cognitive_state.get("confidence", 0.5)

        score_3b = 0.0
        reasons = []

        # Complex reasoning prefers 3B
        if complexity > 0.7:
            score_3b += 0.3
            reasons.append("complex_query")

        # High confidence needed prefers 3B
        if confidence_needed > 0.8:
            score_3b += 0.2
            reasons.append("high_confidence_needed")

        # Short context allows 3B
        if context_tokens < 200:
            score_3b += 0.15
            reasons.append("short_context")

        # Reasoning patterns prefer 3B
        reasoning_patterns = [
            r"\b(analyze|explain|compare|evaluate|debug|investigate)\b",
            r"\b(why|how come|what if)\b.*\?",
            r"\b(optimize|refactor|architect)\b"
        ]
        for pattern in reasoning_patterns:
            if re.search(pattern, prompt.lower()):
                score_3b += 0.1
                reasons.append("reasoning_pattern")
                break

        # Decision
        if score_3b >= 0.5:
            return "3b", "+".join(reasons) if reasons else "score_threshold"

        return "1.5b", "default_safer_choice"

    def _load_model(self, model_key: str) -> Tuple[Any, Any]:
        """Thread-safe model loading with adapter."""
        with self._model_lock:
            if self._current_model_key == model_key and self._model is not None:
                return self._model, self._tokenizer

            # Unload current model
            self._model = None
            self._tokenizer = None

            config = MODEL_CONFIGS[model_key]

            # Try loading with adapter
            if config.adapter_path.exists():
                self._model, self._tokenizer = _load(
                    config.base_model,
                    adapter_path=str(config.adapter_path)
                )
            else:
                # Fall back to base model
                self._model, self._tokenizer = _load(config.base_model)

            self._current_model_key = model_key
            return self._model, self._tokenizer

    def _format_prompt(
        self,
        prompt: str,
        context: str,
        cognitive_state: Dict[str, Any],
        tokenizer: Any,
        model_config: ModelConfig
    ) -> str:
        """Format prompt with chat template."""
        # Select system prompt size based on available tokens
        available_system = int(model_config.max_context_tokens * 0.15)

        if available_system >= 80:
            system_prompt = SYSTEM_PROMPTS["full"]
        elif available_system >= 40:
            system_prompt = SYSTEM_PROMPTS["medium"]
        else:
            system_prompt = SYSTEM_PROMPTS["minimal"]

        # Add emotional context if available
        emotional_valence = cognitive_state.get("emotional_valence", 0)
        if emotional_valence > 0.3:
            system_prompt += "\nCurrent mood: Positive and engaged."
        elif emotional_valence < -0.3:
            system_prompt += "\nCurrent mood: More focused and serious."

        # Build user content with context
        user_content = prompt
        if context and context.strip():
            user_content = f"Context:\n{context}\n\nQuestion: {prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        formatted = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False
        )

        return formatted

    def _clean_response(self, response: str) -> Tuple[str, bool]:
        """
        Clean response and detect repetition.

        Returns: (cleaned_text, repetition_detected)
        """
        if not response:
            return "", False

        # Remove stop tokens
        for marker in ["<|im_end|>", "<|end|>", "<|endoftext|>", "</s>", "<|assistant|>"]:
            if marker in response:
                response = response.split(marker)[0]

        # Detect and truncate repetition
        response, repetition_found = self._truncate_repetition(response)

        return response.strip(), repetition_found

    def _truncate_repetition(
        self,
        text: str,
        min_repeat_length: int = 20,
        max_repeats: int = 3
    ) -> Tuple[str, bool]:
        """
        Detect and truncate repetitive patterns.

        Returns: (cleaned_text, was_repetition_found)
        """
        lines = text.split('\n')
        seen_lines = {}
        result_lines = []
        repetition_found = False

        for line in lines:
            stripped = line.strip()
            if len(stripped) >= min_repeat_length:
                count = seen_lines.get(stripped, 0) + 1
                seen_lines[stripped] = count
                if count > max_repeats:
                    repetition_found = True
                    break
            result_lines.append(line)

        # Also check for repeated phrases within a line
        result_text = '\n'.join(result_lines)

        # Pattern: same phrase repeated 3+ times
        phrase_pattern = r'(.{15,}?)\1{2,}'
        if re.search(phrase_pattern, result_text):
            repetition_found = True
            result_text = re.sub(phrase_pattern, r'\1', result_text)

        return result_text, repetition_found

    def _detect_repetition_live(self, buffer: List[str]) -> bool:
        """Detect repetition during streaming."""
        if len(buffer) < 10:
            return False

        # Check for repeated sequences
        text = " ".join(buffer[-20:])
        # Look for 3+ repetitions of 10+ char phrases
        if re.search(r'(.{10,}?)\1{2,}', text):
            return True

        return False

    def _calculate_confidence(
        self,
        response: str,
        cognitive_state: Dict[str, Any],
        repetition_detected: bool
    ) -> float:
        """
        Calculate confidence score for response.

        Confidence represents: "How likely is this response correct/helpful?"
        - Simple factual questions with direct answers → high confidence
        - Complex open-ended questions → moderate confidence
        - Uncertain or hedging responses → low confidence
        """
        word_count = len(response.split())
        response_lower = response.lower()

        # Detect if this is a simple factual/deterministic question
        # (math, definitions, yes/no, lookups)
        is_factual_response = self._is_factual_response(response)

        # Base confidence depends on response type
        if is_factual_response and word_count <= 15:
            # Short, direct factual answer - this is GOOD
            base_confidence = 0.90
        else:
            # Open-ended response - start moderate, adjust based on quality
            cognitive_conf = cognitive_state.get("confidence", 0.5)
            base_confidence = 0.6 + (cognitive_conf * 0.2)  # Range: 0.6 to 0.8

        # Universal penalties
        if repetition_detected:
            base_confidence -= 0.4

        # Uncertainty patterns (always bad)
        uncertainty_patterns = [
            r"i('m| am) not (sure|certain)",
            r"i (don't|do not) know",
            r"(maybe|perhaps|possibly)",
            r"(could be|might be)",
            r"i (can't|cannot) (help|assist)"
        ]

        for pattern in uncertainty_patterns:
            if re.search(pattern, response_lower):
                base_confidence -= 0.2
                break

        # Quality boosters (for non-factual responses)
        if not is_factual_response:
            # Code blocks indicate concrete answer
            if "```" in response:
                base_confidence += 0.1

            # Structured response (lists)
            if re.search(r'^\d+\.|^[-*]', response, re.MULTILINE):
                base_confidence += 0.05

            # Good explanatory length (20-200 words)
            if 20 <= word_count <= 200:
                base_confidence += 0.1
            elif word_count < 10:
                base_confidence -= 0.1  # Too short for complex question

        # Direct, confident start (universal boost)
        if re.match(r'^(here|this|the|to|yes|no|it\'s|it is|\d)', response_lower):
            base_confidence += 0.05

        return min(1.0, max(0.0, base_confidence))

    def _is_factual_response(self, response: str) -> bool:
        """
        Detect if response is a simple factual answer.

        Factual responses are short, direct, and contain concrete information
        like numbers, names, yes/no, or single-concept answers.
        """
        response_lower = response.lower().strip()
        word_count = len(response.split())

        # Very short responses to likely factual questions
        if word_count <= 10:
            # Contains a number (math answers, dates, quantities)
            if re.search(r'\b\d+\b', response):
                return True

            # Yes/No answers
            if re.match(r'^(yes|no|yeah|nope|correct|incorrect|true|false)', response_lower):
                return True

            # Direct "It's X" or "It is X" pattern
            if re.match(r"^it'?s?\s+\w+", response_lower):
                return True

            # Single word or very short phrase answers
            if word_count <= 5 and not re.search(r"(i don't|i can't|maybe|perhaps)", response_lower):
                return True

        return False

    def _should_escalate(
        self,
        response: str,
        confidence: float,
        repetition_detected: bool
    ) -> bool:
        """Determine if response should be escalated to Claude."""
        # Immediate escalation triggers
        if repetition_detected:
            return True

        if confidence < 0.3:
            return True

        # Refusal patterns
        refusal_patterns = [
            r"i (can't|cannot|won't|will not) (help|assist|do)",
            r"(inappropriate|unethical|harmful)",
            r"beyond my (capabilities|ability)"
        ]

        for pattern in refusal_patterns:
            if re.search(pattern, response.lower()):
                return True

        return False

    def _get_memory_pressure(self) -> float:
        """Get current system memory pressure (0-1)."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent / 100.0
        except ImportError:
            return 0.5  # Assume moderate pressure

    def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity (0-1)."""
        complexity = 0.3  # Base

        # Length factor
        words = len(query.split())
        if words > 50:
            complexity += 0.2
        elif words > 20:
            complexity += 0.1

        # Complex patterns
        complex_patterns = [
            (r"\b(analyze|evaluate|compare|contrast)\b", 0.15),
            (r"\b(debug|trace|investigate)\b", 0.2),
            (r"\b(optimize|refactor|architect)\b", 0.15),
            (r"\b(explain|why|how)\b.*\?", 0.1),
            (r"multi.?step|complex|detailed", 0.1)
        ]

        for pattern, boost in complex_patterns:
            if re.search(pattern, query.lower()):
                complexity += boost

        # Simple patterns reduce complexity
        simple_patterns = [
            r"^(hi|hello|hey|thanks)",
            r"\b(list|show|display)\b",
            r"\b(simple|quick|just)\b"
        ]

        for pattern in simple_patterns:
            if re.search(pattern, query.lower()):
                complexity -= 0.1

        return min(1.0, max(0.0, complexity))

    def _fallback_response(self, prompt: str, error: str) -> GenerationResult:
        """Generate fallback response when MLX fails."""
        return GenerationResult(
            response=f"I apologize, but I'm having trouble processing that right now. ({error})",
            tokens_generated=0,
            generation_time_ms=0,
            model_used="fallback",
            confidence=0.0,
            repetition_detected=False,
            escalation_recommended=True,
            metadata={"error": error}
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including resource info."""
        return {
            "generation_count": self._generation_count,
            "total_tokens": self._total_tokens,
            "escalation_count": self._escalation_count,
            "resource_rejections": self._resource_rejections,
            "current_model": self._current_model_key,
            "mlx_available": _mlx_available,
            "resources": self._resource_manager.get_stats()
        }

    def get_resource_snapshot(self) -> Dict[str, Any]:
        """Get current resource state."""
        return self._resource_manager.get_snapshot().to_dict()

    def unload_model(self):
        """Unload current model to free memory."""
        import gc
        with self._model_lock:
            self._model = None
            self._tokenizer = None
            self._current_model_key = None
        # Force garbage collection to actually free memory
        gc.collect()
        try:
            import mlx.core as mx
            mx.metal.clear_cache()  # Clear MLX metal cache
        except:
            pass

    def get_memory_usage_mb(self) -> float:
        """Estimate current model memory usage."""
        if self._model is None:
            return 0.0
        # Rough estimate based on model size
        if self._current_model_key == "1.5b":
            return 1200  # ~1.2GB
        elif self._current_model_key == "3b":
            return 2400  # ~2.4GB
        return 0.0


# Factory function
def create_mlx_engine(db_path: str = "/Volumes/David External/sam_memory") -> MLXCognitiveEngine:
    """Create MLX cognitive engine."""
    return MLXCognitiveEngine(db_path)


if __name__ == "__main__":
    # Demo
    print("MLX Cognitive Engine Demo")
    print("=" * 50)

    engine = MLXCognitiveEngine()

    if not _ensure_mlx():
        print("MLX not available - skipping generation test")
    else:
        result = engine.generate(
            prompt="What is Python?",
            context="",
            cognitive_state={"confidence": 0.7}
        )

        print(f"Response: {result.response[:100]}...")
        print(f"Model: {result.model_used}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Time: {result.generation_time_ms}ms")
        print(f"Escalation: {result.escalation_recommended}")

    print("\nStats:", engine.get_stats())
