#!/usr/bin/env python3
"""
SAM Vision Engine - Multi-Modal Support for Cognitive System

Provides vision capabilities using small, efficient models that run on 8GB M2:
- SmolVLM (256M-2B) - Fast, MLX native
- Moondream (0.5B-2B) - Optimized for detection and description
- Claude escalation - For complex vision tasks via browser bridge

Architecture:
    Image Input
         │
         ▼
    ┌─────────────────────────────────────────┐
    │          VisionModelSelector            │
    │  - Analyze task complexity              │
    │  - Check memory availability            │
    │  - Select optimal model                 │
    └─────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │  [Simple/Fast]      [Complex/Detailed]  │
    │       │                    │            │
    │  SmolVLM-500M        Moondream-2B       │
    │  or Moondream-0.5B   or Claude          │
    └─────────────────────────────────────────┘
         │
         ▼
    VisionQualityValidator
         │
         ▼
    Response (with confidence)

Created: 2026-01-17
Version: 1.0.0
"""

import os
import sys
import json
import base64
import hashlib
import threading
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Union
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vision_engine")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model configurations - optimized for 8GB M2 Mac Mini
# Updated 2026-01-18 with working models for 8GB RAM
VISION_MODELS = {
    # RECOMMENDED: nanoLLaVA works without PyTorch, fits in 8GB
    "nanollava": {
        "model_id": "mlx-community/nanoLLaVA-1.5-bf16",
        "memory_mb": 1500,
        "max_tokens": 512,
        "speed": "fast",
        "quality": "good",
        "use_cases": ["caption", "description", "vqa", "reasoning"],
        "trust_remote_code": True,
    },
    # SmolVLM models - REQUIRE PyTorch for processor
    "smolvlm-256m": {
        "model_id": "mlx-community/SmolVLM2-256M-Video-Instruct-mlx",
        "memory_mb": 500,
        "max_tokens": 512,
        "speed": "fastest",
        "quality": "basic",
        "use_cases": ["quick_caption", "simple_detection", "yes_no"],
        "requires_pytorch": True,
    },
    "smolvlm-500m": {
        "model_id": "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "memory_mb": 1000,
        "max_tokens": 512,
        "speed": "fast",
        "quality": "good",
        "use_cases": ["caption", "description", "counting", "ocr_simple"],
        "requires_pytorch": True,
    },
    "smolvlm-2b-4bit": {
        "model_id": "mlx-community/SmolVLM-Instruct-4bit",
        "memory_mb": 3500,  # Too large for 8GB
        "max_tokens": 512,
        "speed": "moderate",
        "quality": "high",
        "use_cases": ["detailed_description", "reasoning", "complex_qa"],
        "requires_pytorch": True,
    },
    # Moondream models - compatibility issues with mlx_vlm
    "moondream-2b": {
        "model_id": "vikhyatk/moondream2",
        "memory_mb": 1800,
        "max_tokens": 256,
        "speed": "moderate",
        "quality": "high",
        "use_cases": ["detection", "caption", "vqa", "reasoning"],
        "deprecated": True,  # Model type not supported in current mlx_vlm
    },
    "moondream-3-int4": {
        "model_id": "moondream/md3p-int4",
        "memory_mb": 2450,
        "max_tokens": 512,
        "speed": "moderate",
        "quality": "highest",
        "use_cases": ["detailed_detection", "grounding", "complex_analysis"],
        "deprecated": True,
    },
}

# Default model (best balance for 8GB)
# nanoLLaVA is recommended: works without PyTorch, fits in 8GB RAM
DEFAULT_MODEL = "nanollava"

# Fallback chain when model loading fails
# nanoLLaVA is the primary fallback as it's most compatible
MODEL_FALLBACK_CHAIN = {
    "nanollava": [],  # No fallback - this is our best option
    "smolvlm-256m": ["nanollava"],
    "smolvlm-500m": ["nanollava"],
    "smolvlm-2b-4bit": ["nanollava"],
    "moondream-2b": ["nanollava"],
    "moondream-3-int4": ["nanollava"],
}

# Task patterns for model selection
TASK_PATTERNS = {
    "detection": ["detect", "find", "locate", "where", "count", "how many"],
    "caption": ["caption", "describe", "what is", "what's in"],
    "ocr": ["read", "text", "ocr", "words", "writing"],
    "reasoning": ["why", "explain", "analyze", "compare", "difference"],
    "grounding": ["point to", "show me", "bounding box", "coordinates"],
}

# ============================================================================
# DATA MODELS
# ============================================================================

class VisionTaskType(Enum):
    """Types of vision tasks"""
    CAPTION = "caption"
    DETECTION = "detection"
    OCR = "ocr"
    REASONING = "reasoning"
    GROUNDING = "grounding"
    GENERAL = "general"


@dataclass
class VisionConfig:
    """Configuration for vision generation"""
    max_tokens: int = 512
    temperature: float = 0.7
    model_key: Optional[str] = None  # None = auto-select
    force_local: bool = False  # Don't escalate to Claude
    return_bbox: bool = False  # Return bounding boxes if available


@dataclass
class VisionResult:
    """Result from vision processing"""
    response: str
    confidence: float
    model_used: str
    task_type: VisionTaskType
    processing_time_ms: int
    escalated: bool = False
    escalation_reason: Optional[str] = None
    bounding_boxes: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "response": self.response,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "task_type": self.task_type.value,
            "processing_time_ms": self.processing_time_ms,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
            "bounding_boxes": self.bounding_boxes,
            "metadata": self.metadata,
        }


@dataclass
class ModelSelection:
    """Result of model selection"""
    model_key: str
    model_id: str
    reason: str
    task_type: VisionTaskType
    escalate_to_claude: bool = False


# ============================================================================
# MLX-VLM LOADER
# ============================================================================

def _ensure_mlx_vlm() -> bool:
    """Check if mlx_vlm is available"""
    try:
        import mlx_vlm
        return True
    except ImportError:
        return False


class MLXVisionLoader:
    """Thread-safe MLX vision model loader with caching and auto-unload"""

    # Default idle timeout before auto-unloading model (5 minutes)
    DEFAULT_IDLE_TIMEOUT_SECONDS = 300

    def __init__(self):
        self._models: Dict[str, Tuple[Any, Any]] = {}  # model_key -> (model, processor)
        self._lock = threading.Lock()
        self._current_model: Optional[str] = None
        self._mlx_available = _ensure_mlx_vlm()

        # Auto-unload tracking
        self._last_used: Optional[datetime] = None
        self._unload_timer: Optional[threading.Timer] = None
        self._unload_timeout: int = self.DEFAULT_IDLE_TIMEOUT_SECONDS
        self._auto_unload_enabled: bool = True

    @property
    def mlx_available(self) -> bool:
        return self._mlx_available

    def _update_last_used(self):
        """Update the last used timestamp and schedule auto-unload."""
        self._last_used = datetime.now()
        if self._auto_unload_enabled:
            self.schedule_unload(self._unload_timeout)

    def is_model_loaded(self) -> bool:
        """Check if a vision model is currently loaded.

        Returns:
            True if a model is loaded and ready for inference
        """
        with self._lock:
            return self._current_model is not None and self._current_model in self._models

    def get_idle_seconds(self) -> Optional[float]:
        """Get seconds since last model use, or None if never used."""
        if self._last_used is None:
            return None
        return (datetime.now() - self._last_used).total_seconds()

    def schedule_unload(self, timeout_seconds: int = 300):
        """Schedule model unload after idle timeout.

        Args:
            timeout_seconds: Seconds of inactivity before unloading (default 5 minutes)

        The timer is reset each time the model is used. If the model sits idle
        for the specified timeout, it will be automatically unloaded to free
        GPU/memory resources.
        """
        # Cancel any existing timer
        if self._unload_timer is not None:
            self._unload_timer.cancel()
            self._unload_timer = None

        self._unload_timeout = timeout_seconds

        # Only schedule if model is loaded
        if not self.is_model_loaded():
            return

        def _auto_unload():
            """Callback to unload model after timeout."""
            # Check if model is still idle
            idle_seconds = self.get_idle_seconds()
            if idle_seconds is not None and idle_seconds >= timeout_seconds:
                logger.info(f"Auto-unloading vision model after {idle_seconds:.0f}s idle")
                self.unload_model()

                # Notify resource manager if available
                try:
                    from .resource_manager import ResourceManager
                    manager = ResourceManager()
                    logger.info(f"Resources after vision unload: {manager.get_snapshot().to_dict()}")
                except ImportError:
                    pass

        self._unload_timer = threading.Timer(timeout_seconds, _auto_unload)
        self._unload_timer.daemon = True  # Don't block process exit
        self._unload_timer.start()
        logger.debug(f"Scheduled vision model unload in {timeout_seconds}s")

    def unload_model(self):
        """Unload the current vision model to free GPU/memory.

        This can be called explicitly to free resources, or it will be
        called automatically after the idle timeout expires.
        """
        with self._lock:
            if self._current_model is None:
                logger.debug("No vision model loaded, nothing to unload")
                return

            model_key = self._current_model
            logger.info(f"Unloading vision model: {model_key}")

            # Cancel any pending unload timer
            if self._unload_timer is not None:
                self._unload_timer.cancel()
                self._unload_timer = None

            # Clear the model
            if model_key in self._models:
                del self._models[model_key]

            self._current_model = None
            self._last_used = None

            # Force garbage collection to free memory
            import gc
            gc.collect()

            logger.info(f"Vision model {model_key} unloaded successfully")

    def set_auto_unload(self, enabled: bool, timeout_seconds: int = None):
        """Configure auto-unload behavior.

        Args:
            enabled: Whether to automatically unload idle models
            timeout_seconds: New timeout value (optional)
        """
        self._auto_unload_enabled = enabled
        if timeout_seconds is not None:
            self._unload_timeout = timeout_seconds

        if not enabled and self._unload_timer is not None:
            self._unload_timer.cancel()
            self._unload_timer = None
            logger.info("Vision model auto-unload disabled")
        elif enabled and self.is_model_loaded():
            self.schedule_unload(self._unload_timeout)
            logger.info(f"Vision model auto-unload enabled ({self._unload_timeout}s timeout)")

    def load_model(self, model_key: str, try_fallbacks: bool = True) -> Tuple[Any, Any]:
        """Load a vision model (cached) with fallback support.

        Args:
            model_key: The model to load (e.g., "moondream-2b")
            try_fallbacks: If True, try fallback models on failure

        Returns:
            Tuple of (model, processor)

        Note:
            SmolVLM models require PyTorch for their processor even though
            MLX is used for inference. If torch is not installed, these
            models will fail and we'll try fallbacks.
        """
        if not self._mlx_available:
            raise RuntimeError("mlx_vlm not available")

        with self._lock:
            # Return cached model if loaded
            if model_key in self._models:
                self._current_model = model_key
                self._update_last_used()
                return self._models[model_key]

            # Unload current model to free memory (only keep one loaded)
            if self._current_model and self._current_model != model_key:
                logger.info(f"Unloading {self._current_model} to load {model_key}")
                if self._current_model in self._models:
                    del self._models[self._current_model]
                import gc
                gc.collect()

            # Try to load the requested model
            models_to_try = [model_key]
            if try_fallbacks and model_key in MODEL_FALLBACK_CHAIN:
                models_to_try.extend(MODEL_FALLBACK_CHAIN[model_key])

            last_error = None
            for attempt_key in models_to_try:
                config = VISION_MODELS.get(attempt_key)
                if not config:
                    continue

                model_id = config["model_id"]
                logger.info(f"Loading vision model: {model_id}")

                try:
                    from mlx_vlm import load
                    # Pass trust_remote_code if specified in model config
                    # Use lazy=True to defer weight loading until needed (saves memory)
                    trust_code = config.get("trust_remote_code", False)
                    model, processor = load(model_id, trust_remote_code=trust_code, lazy=True)

                    self._models[attempt_key] = (model, processor)
                    self._current_model = attempt_key
                    self._update_last_used()

                    if attempt_key != model_key:
                        logger.warning(f"Using fallback model {attempt_key} instead of {model_key}")

                    return model, processor

                except ModuleNotFoundError as e:
                    # SmolVLM requires torch for processor, even with MLX
                    logger.warning(f"Model {attempt_key} failed: {e}")
                    last_error = e
                    continue
                except Exception as e:
                    logger.warning(f"Model {attempt_key} failed: {e}")
                    last_error = e
                    continue

            # All models failed
            raise RuntimeError(
                f"Failed to load any vision model. Tried: {models_to_try}. "
                f"Last error: {last_error}"
            )

    def get_current_model(self) -> Optional[str]:
        return self._current_model

    def unload_all(self):
        """Unload all models to free memory"""
        # Cancel any pending unload timer
        if self._unload_timer is not None:
            self._unload_timer.cancel()
            self._unload_timer = None

        with self._lock:
            self._models.clear()
            self._current_model = None
            self._last_used = None
            import gc
            gc.collect()


# Global loader instance
_vision_loader = MLXVisionLoader()


# ============================================================================
# VISION MODEL SELECTOR
# ============================================================================

class VisionModelSelector:
    """
    Selects optimal vision model based on task, complexity, and memory.

    Selection logic:
    1. Parse task type from prompt
    2. Estimate complexity
    3. Check available memory
    4. Select best fitting model
    5. Optionally escalate to Claude
    """

    # Complexity patterns
    COMPLEX_PATTERNS = [
        r"detail(ed)?",
        r"thorough(ly)?",
        r"explain",
        r"analyze",
        r"compar(e|ison)",
        r"multiple",
        r"all (the|of)",
        r"every",
        r"relationship",
        r"why",
        r"how does",
    ]

    SIMPLE_PATTERNS = [
        r"what is",
        r"is (this|there)",
        r"yes or no",
        r"count",
        r"how many",
        r"color",
        r"caption",
    ]

    def __init__(self, max_memory_mb: int = 3000):
        """
        Args:
            max_memory_mb: Maximum memory to use for vision model (default 3GB)
        """
        self.max_memory_mb = max_memory_mb

    def detect_task_type(self, prompt: str) -> VisionTaskType:
        """Detect task type from prompt"""
        prompt_lower = prompt.lower()

        for task_type, patterns in TASK_PATTERNS.items():
            if any(p in prompt_lower for p in patterns):
                return VisionTaskType(task_type)

        return VisionTaskType.GENERAL

    def estimate_complexity(self, prompt: str) -> Tuple[int, str]:
        """
        Estimate task complexity (1-10).
        Returns (complexity, reason)
        """
        import re
        prompt_lower = prompt.lower()

        # Start with base complexity
        complexity = 5

        # Check for complexity indicators
        complex_matches = sum(1 for p in self.COMPLEX_PATTERNS
                             if re.search(p, prompt_lower))
        simple_matches = sum(1 for p in self.SIMPLE_PATTERNS
                            if re.search(p, prompt_lower))

        complexity += complex_matches * 1.5
        complexity -= simple_matches * 1

        # Prompt length factor
        word_count = len(prompt.split())
        if word_count > 30:
            complexity += 2
        elif word_count < 10:
            complexity -= 1

        # Bound complexity
        complexity = max(1, min(10, int(complexity)))

        # Generate reason
        if complex_matches > simple_matches:
            reason = "complex_patterns"
        elif simple_matches > complex_matches:
            reason = "simple_patterns"
        else:
            reason = "neutral"

        return complexity, reason

    def get_available_memory_mb(self) -> int:
        """Estimate available memory for vision model"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            # Use 40% of available memory, max 3GB
            available = int(mem.available / (1024 * 1024) * 0.4)
            return min(available, self.max_memory_mb)
        except ImportError:
            return self.max_memory_mb

    def select_model(
        self,
        prompt: str,
        image_size: Optional[Tuple[int, int]] = None,
        force_model: Optional[str] = None,
        confidence_required: float = 0.5,
    ) -> ModelSelection:
        """
        Select optimal model for the task.

        Args:
            prompt: User's prompt/question
            image_size: (width, height) of image
            force_model: Force specific model
            confidence_required: Minimum confidence needed

        Returns:
            ModelSelection with model choice and reasoning
        """
        # If model forced, use it
        if force_model and force_model in VISION_MODELS:
            task_type = self.detect_task_type(prompt)
            config = VISION_MODELS[force_model]
            return ModelSelection(
                model_key=force_model,
                model_id=config["model_id"],
                reason="forced",
                task_type=task_type,
            )

        # Detect task type and complexity
        task_type = self.detect_task_type(prompt)
        complexity, complexity_reason = self.estimate_complexity(prompt)

        # Get available memory
        available_mem = self.get_available_memory_mb()

        # Filter models by memory and compatibility
        # Exclude models that require PyTorch (not installed) or are deprecated
        viable_models = [
            (k, v) for k, v in VISION_MODELS.items()
            if v["memory_mb"] <= available_mem
            and not v.get("requires_pytorch", False)
            and not v.get("deprecated", False)
        ]

        if not viable_models:
            # Not enough memory for any local model - escalate to Claude
            return ModelSelection(
                model_key="claude",
                model_id="claude-browser",
                reason="insufficient_memory",
                task_type=task_type,
                escalate_to_claude=True,
            )

        # Score models for this task
        scored_models = []
        for model_key, config in viable_models:
            score = 0

            # Task match
            if task_type.value in config.get("use_cases", []):
                score += 3

            # Complexity match
            if complexity >= 7 and config["quality"] == "high":
                score += 2
            elif complexity <= 4 and config["speed"] == "fastest":
                score += 2
            elif config["quality"] == "good":
                score += 1

            # Confidence requirement
            if confidence_required > 0.7 and config["quality"] == "high":
                score += 2

            scored_models.append((model_key, config, score))

        # Sort by score (descending)
        scored_models.sort(key=lambda x: x[2], reverse=True)

        # Select best model
        best_key, best_config, best_score = scored_models[0]

        # Check if we should escalate to Claude
        escalate = False
        escalate_reason = None

        if complexity >= 9 and confidence_required > 0.8:
            escalate = True
            escalate_reason = "high_complexity_high_confidence"
        elif task_type == VisionTaskType.REASONING and complexity >= 7:
            escalate = True
            escalate_reason = "complex_reasoning"

        if escalate:
            return ModelSelection(
                model_key="claude",
                model_id="claude-browser",
                reason=escalate_reason,
                task_type=task_type,
                escalate_to_claude=True,
            )

        return ModelSelection(
            model_key=best_key,
            model_id=best_config["model_id"],
            reason=f"score={best_score}_complexity={complexity}_{complexity_reason}",
            task_type=task_type,
        )


# ============================================================================
# VISION QUALITY VALIDATOR
# ============================================================================

class VisionQualityValidator:
    """Validates vision model outputs"""

    # Low quality patterns
    LOW_QUALITY_PATTERNS = [
        r"i (cannot|can't) (see|view|process)",
        r"image (not|isn't) (clear|visible)",
        r"unable to",
        r"error",
        r"sorry",
        r"i don't (see|know)",
    ]

    # High confidence patterns
    HIGH_CONFIDENCE_PATTERNS = [
        r"^(the|this|there|i see|in the|a|an) ",  # Direct start
        r"\d+",  # Contains numbers (counting, coordinates)
        r"(shows|displays|contains|depicts|features)",
    ]

    def validate(
        self,
        response: str,
        prompt: str,
        task_type: VisionTaskType,
    ) -> Tuple[float, bool, Optional[str]]:
        """
        Validate response quality.

        Returns:
            (confidence, escalation_recommended, escalation_reason)
        """
        import re
        response_lower = response.lower()

        # Start with base confidence
        confidence = 0.7

        # Check for low quality patterns
        low_quality_count = sum(
            1 for p in self.LOW_QUALITY_PATTERNS
            if re.search(p, response_lower)
        )

        if low_quality_count > 0:
            confidence -= 0.2 * low_quality_count

        # Check for high confidence patterns
        high_quality_count = sum(
            1 for p in self.HIGH_CONFIDENCE_PATTERNS
            if re.search(p, response_lower)
        )

        confidence += 0.05 * high_quality_count

        # Response length factor
        word_count = len(response.split())

        if task_type == VisionTaskType.CAPTION:
            # Captions should be moderate length
            if 5 <= word_count <= 50:
                confidence += 0.1
            elif word_count < 3:
                confidence -= 0.2

        elif task_type == VisionTaskType.REASONING:
            # Reasoning should be detailed
            if word_count >= 30:
                confidence += 0.1
            elif word_count < 15:
                confidence -= 0.15

        elif task_type == VisionTaskType.DETECTION:
            # Detection should mention objects
            if any(w in response_lower for w in ["object", "item", "person", "thing"]):
                confidence += 0.1

        # Bound confidence
        confidence = max(0.0, min(1.0, confidence))

        # Determine if escalation recommended
        escalate = False
        escalate_reason = None

        if confidence < 0.3:
            escalate = True
            escalate_reason = "low_confidence"
        elif low_quality_count >= 2:
            escalate = True
            escalate_reason = "quality_issues"

        return confidence, escalate, escalate_reason


# ============================================================================
# MAIN VISION ENGINE
# ============================================================================

class VisionEngine:
    """
    Main vision processing engine.

    Features:
    - Multi-model support (SmolVLM, Moondream)
    - Automatic model selection
    - Claude escalation for complex tasks
    - Quality validation
    - Memory management
    """

    def __init__(
        self,
        adapter_path: Optional[str] = None,
        max_memory_mb: int = 3000,
    ):
        """
        Args:
            adapter_path: Path to custom adapter weights
            max_memory_mb: Maximum memory for vision models
        """
        self.adapter_path = adapter_path
        self.max_memory_mb = max_memory_mb

        self.selector = VisionModelSelector(max_memory_mb)
        self.validator = VisionQualityValidator()

        self._generation_count = 0
        self._escalation_count = 0

    def process_image(
        self,
        image_source: Union[str, Path, bytes],
        prompt: str,
        config: Optional[VisionConfig] = None,
    ) -> VisionResult:
        """
        Process an image with a prompt.

        Args:
            image_source: Path to image, URL, or base64 bytes
            prompt: Question or instruction about the image
            config: Optional configuration

        Returns:
            VisionResult with response and metadata
        """
        config = config or VisionConfig()
        start_time = datetime.now()

        # Select model
        selection = self.selector.select_model(
            prompt=prompt,
            force_model=config.model_key,
        )

        # Check if we should escalate to Claude
        if selection.escalate_to_claude and not config.force_local:
            return self._escalate_to_claude(
                image_source, prompt, selection, start_time
            )

        # Try local model
        try:
            result = self._process_local(
                image_source, prompt, selection, config, start_time
            )

            # Validate result
            confidence, escalate, escalate_reason = self.validator.validate(
                result.response, prompt, selection.task_type
            )

            result.confidence = confidence

            # Check if we need to escalate after validation
            # DISABLED: Claude browser escalation was causing tab explosion
            # if escalate and not config.force_local:
            #     logger.info(f"Escalating due to: {escalate_reason}")
            #     return self._escalate_to_claude(
            #         image_source, prompt, selection, start_time
            #     )

            self._generation_count += 1
            return result

        except Exception as e:
            logger.error(f"Local vision model error: {e}")
            # Don't escalate to Claude - just return error
            # Browser escalation was opening too many tabs
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return VisionResult(
                response=f"Vision processing failed: {str(e)}",
                confidence=0.0,
                model_used="none",
                task_type=selection.task_type,
                processing_time_ms=processing_time,
                escalated=False,
                escalation_reason=str(e),
            )

    def _process_via_subprocess(
        self,
        image_path: str,
        prompt: str,
        selection: ModelSelection,
        config: VisionConfig,
        start_time: datetime,
    ) -> VisionResult:
        """Process vision using mlx_vlm CLI module (more reliable than inline scripts)."""
        import subprocess
        import re

        try:
            # Use the module execution approach which works reliably
            # This matches exactly how the CLI tool runs
            result = subprocess.run(
                [
                    "python3", "-m", "mlx_vlm", "generate",
                    "--model", "mlx-community/nanoLLaVA-1.5-bf16",
                    "--image", image_path,
                    "--prompt", prompt,
                    "--max-tokens", str(config.max_tokens),
                    "--temperature", str(config.temperature),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                # Parse CLI output format:
                # ==========
                # Files: [...]
                # Prompt: <|im_start|>...
                # [actual response here]
                # ==========
                # Prompt: X tokens, ...
                # Generation: Y tokens, ...
                output = result.stdout

                # Extract response between the formatted prompt and stats
                # The response starts after "assistant\n" and ends before the final "=========="
                try:
                    # Find the response section
                    parts = output.split("==========")
                    if len(parts) >= 2:
                        # The middle part contains the prompt + response
                        middle = parts[1]
                        # Find where the assistant response starts
                        if "<|im_start|>assistant" in middle:
                            response_start = middle.find("<|im_start|>assistant")
                            after_assistant = middle[response_start:]
                            # Skip past the assistant tag and newline
                            if "\n" in after_assistant:
                                response = after_assistant.split("\n", 1)[1].strip()
                            else:
                                response = after_assistant.strip()
                        else:
                            # Fallback: take everything after Prompt line
                            lines = middle.strip().split("\n")
                            response_lines = []
                            found_prompt = False
                            for line in lines:
                                if found_prompt:
                                    response_lines.append(line)
                                elif line.startswith("Prompt:"):
                                    found_prompt = True
                            response = "\n".join(response_lines).strip()
                    else:
                        response = output.strip()
                except Exception as e:
                    logger.warning(f"Failed to parse CLI output, using raw: {e}")
                    response = output.strip()

                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return VisionResult(
                    response=response,
                    confidence=0.7,
                    model_used=selection.model_key,
                    task_type=selection.task_type,
                    processing_time_ms=processing_time,
                    metadata={"via": "mlx_vlm_cli"}
                )
            else:
                raise RuntimeError(f"Subprocess failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Vision processing timed out")
        except Exception as e:
            raise RuntimeError(f"Vision processing error: {e}")

    def _process_via_server(
        self,
        image_path: str,
        prompt: str,
        selection: ModelSelection,
        config: VisionConfig,
        start_time: datetime,
    ) -> VisionResult:
        """Process via persistent vision server (fast, model stays loaded)."""
        import requests

        VISION_SERVER_URL = "http://localhost:8766"

        try:
            # Check if server is running
            health = requests.get(f"{VISION_SERVER_URL}/health", timeout=2)
            if health.status_code != 200 or health.json().get("status") != "ok":
                raise RuntimeError("Vision server not ready")

            # Read image and encode
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Send to server
            response = requests.post(
                f"{VISION_SERVER_URL}/process",
                json={
                    "image_base64": image_b64,
                    "prompt": prompt,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                },
                timeout=120,
            )

            result = response.json()

            if result.get("success"):
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return VisionResult(
                    response=result.get("response", ""),
                    confidence=0.75,
                    model_used=selection.model_key,
                    task_type=selection.task_type,
                    processing_time_ms=processing_time,
                    metadata={"via": "vision_server", "server_time_ms": result.get("processing_time_ms")}
                )
            else:
                raise RuntimeError(result.get("error", "Vision server error"))

        except requests.exceptions.ConnectionError:
            raise RuntimeError("Vision server not running")
        except requests.exceptions.Timeout:
            raise RuntimeError("Vision server timeout")

    def _process_local(
        self,
        image_source: Union[str, Path, bytes],
        prompt: str,
        selection: ModelSelection,
        config: VisionConfig,
        start_time: datetime,
    ) -> VisionResult:
        """Process with local MLX model - tries persistent server first, falls back to CLI."""
        # Resolve image to path first
        image_path = self._resolve_image(image_source)

        # Try persistent server first (fast path - model already loaded)
        try:
            return self._process_via_server(image_path, prompt, selection, config, start_time)
        except RuntimeError as e:
            logger.info(f"Vision server not available ({e}), falling back to CLI")

        # Fall back to subprocess/CLI (slow path - loads model each time)
        return self._process_via_subprocess(image_path, prompt, selection, config, start_time)

    def _process_local_direct(
        self,
        image_source: Union[str, Path, bytes],
        prompt: str,
        selection: ModelSelection,
        config: VisionConfig,
        start_time: datetime,
    ) -> VisionResult:
        """Process directly in-process (original method, may cause GPU issues in server)"""
        if not _vision_loader.mlx_available:
            raise RuntimeError("mlx_vlm not available")

        # Load model
        model, processor = _vision_loader.load_model(selection.model_key)

        # Prepare image path
        image_path = self._resolve_image(image_source)

        # Generate response
        from mlx_vlm import generate, apply_chat_template

        # Format prompt with image tokens for vision models
        try:
            # Get model config for chat template
            model_config = VISION_MODELS.get(selection.model_key, {})
            formatted_prompt = apply_chat_template(
                processor,
                model.config if hasattr(model, 'config') else {},
                prompt,
                num_images=1,
            )
        except Exception as e:
            logger.warning(f"Chat template failed, using raw prompt: {e}")
            formatted_prompt = prompt

        # mlx_vlm.generate signature: (model, processor, prompt, image=..., ...)
        result = generate(
            model,
            processor,
            formatted_prompt,
            image=image_path,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            verbose=False,
        )

        # Extract text from GenerationResult
        response = result.text if hasattr(result, 'text') else str(result)

        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return VisionResult(
            response=response,
            confidence=0.7,  # Will be updated by validator
            model_used=selection.model_key,
            task_type=selection.task_type,
            processing_time_ms=processing_time,
            metadata={
                "model_id": selection.model_id,
                "selection_reason": selection.reason,
            }
        )

    def _escalate_to_claude(
        self,
        image_source: Union[str, Path, bytes],
        prompt: str,
        selection: ModelSelection,
        start_time: datetime,
        error: Optional[str] = None,
    ) -> VisionResult:
        """Escalate to Claude via browser bridge"""
        self._escalation_count += 1

        try:
            # Try to use browser bridge
            response = self._send_to_claude(image_source, prompt)

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return VisionResult(
                response=response,
                confidence=0.95,  # Claude is high confidence
                model_used="claude",
                task_type=selection.task_type,
                processing_time_ms=processing_time,
                escalated=True,
                escalation_reason=error or selection.reason,
                metadata={
                    "original_selection": selection.model_key,
                }
            )

        except Exception as e:
            logger.error(f"Claude escalation failed: {e}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return VisionResult(
                response=f"Vision processing failed: {error or str(e)}",
                confidence=0.0,
                model_used="none",
                task_type=selection.task_type,
                processing_time_ms=processing_time,
                escalated=True,
                escalation_reason=f"all_failed: {error or str(e)}",
            )

    def _send_to_claude(self, image_source: Union[str, Path, bytes], prompt: str) -> str:
        """Send image to Claude via browser bridge"""
        # For now, we'll create a prompt that describes what to do
        # The browser bridge would need to be extended to handle images
        # For this implementation, we'll use a text-based escalation

        bridge_path = Path(__file__).parent.parent.parent / "ai_bridge.cjs"

        if not bridge_path.exists():
            raise RuntimeError("Browser bridge not found")

        # Create combined prompt
        if isinstance(image_source, (str, Path)):
            combined_prompt = f"[Image at: {image_source}]\n\n{prompt}"
        else:
            combined_prompt = f"[Image provided as base64]\n\n{prompt}"

        cmd = ["node", str(bridge_path), "send", combined_prompt, "--claude"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(bridge_path.parent)
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data.get("response", result.stdout)
            except json.JSONDecodeError:
                return result.stdout
        else:
            raise RuntimeError(f"Bridge error: {result.stderr}")

    def _resolve_image(self, image_source: Union[str, Path, bytes], preprocess: bool = True) -> str:
        """Resolve image source to file path and optionally preprocess for memory efficiency.

        Args:
            image_source: Path to image, URL, or base64 bytes
            preprocess: If True, resize large images to save memory (default True)

        Returns:
            Path to (possibly preprocessed) image file
        """
        resolved_path = None

        if isinstance(image_source, bytes):
            # Save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_source)
                resolved_path = f.name

        elif isinstance(image_source, Path):
            resolved_path = str(image_source)

        elif isinstance(image_source, str):
            if image_source.startswith(("http://", "https://")):
                # Download URL
                import urllib.request
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    urllib.request.urlretrieve(image_source, f.name)
                    resolved_path = f.name
            else:
                resolved_path = image_source
        else:
            raise ValueError(f"Unsupported image source type: {type(image_source)}")

        # Preprocess image to save memory (resize large images >2048px)
        if preprocess and resolved_path:
            try:
                from .image_preprocessor import get_preprocessor
                preprocessor = get_preprocessor()
                info = preprocessor.get_image_info(resolved_path)

                if info.needs_resize:
                    logger.info(
                        f"Preprocessing image: {info.width}x{info.height} "
                        f"(estimated {info.estimated_memory_bytes // (1024*1024)}MB)"
                    )
                    resolved_path = preprocessor.preprocess_image(resolved_path)
            except ImportError:
                logger.warning("Image preprocessor not available, using original image")
            except Exception as e:
                logger.warning(f"Image preprocessing failed: {e}, using original image")

        return resolved_path

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        idle_seconds = _vision_loader.get_idle_seconds()
        return {
            "generation_count": self._generation_count,
            "escalation_count": self._escalation_count,
            "escalation_rate": (
                self._escalation_count / max(1, self._generation_count + self._escalation_count)
            ),
            "current_model": _vision_loader.get_current_model(),
            "model_loaded": _vision_loader.is_model_loaded(),
            "idle_seconds": round(idle_seconds, 1) if idle_seconds else None,
            "auto_unload_enabled": _vision_loader._auto_unload_enabled,
            "auto_unload_timeout": _vision_loader._unload_timeout,
            "mlx_available": _vision_loader.mlx_available,
        }

    def unload_models(self):
        """Unload all models to free memory"""
        _vision_loader.unload_all()

    def is_model_loaded(self) -> bool:
        """Check if a vision model is currently loaded.

        Returns:
            True if a model is loaded and ready for inference
        """
        return _vision_loader.is_model_loaded()

    def schedule_unload(self, timeout_seconds: int = 300):
        """Schedule model unload after idle timeout.

        Args:
            timeout_seconds: Seconds of inactivity before unloading (default 5 minutes)

        This is useful for freeing GPU/memory when vision is not actively being used.
        The timer resets each time the model is used.
        """
        _vision_loader.schedule_unload(timeout_seconds)

    def set_auto_unload(self, enabled: bool, timeout_seconds: int = None):
        """Configure auto-unload behavior.

        Args:
            enabled: Whether to automatically unload idle models
            timeout_seconds: New timeout value in seconds (optional)

        Example:
            engine.set_auto_unload(True, 300)  # Unload after 5 min idle
            engine.set_auto_unload(False)       # Disable auto-unload
        """
        _vision_loader.set_auto_unload(enabled, timeout_seconds)

    def get_idle_seconds(self) -> Optional[float]:
        """Get seconds since last vision model use.

        Returns:
            Seconds since last use, or None if model was never used
        """
        return _vision_loader.get_idle_seconds()


# ============================================================================
# MEMORY BENCHMARKING
# ============================================================================

def measure_memory_usage() -> Dict[str, Any]:
    """
    Measure current memory usage and report vision tier availability.

    Returns a detailed report of:
    - System memory status
    - Each vision tier's memory requirements and availability
    - Recommended tier based on current resources
    - Whether VLM operations are feasible

    Usage:
        from cognitive.vision_engine import measure_memory_usage
        report = measure_memory_usage()
        print(report)
    """
    import subprocess as sp

    # Get system memory info
    try:
        # Get page size
        pagesize = int(sp.check_output(['pagesize']).decode().strip())

        # Get vm_stat output
        vm_stat = sp.check_output(['vm_stat']).decode()

        # Parse the stats
        stats = {}
        for line in vm_stat.split('\n'):
            if ':' in line:
                key, value = line.split(':')
                value = value.strip().rstrip('.')
                try:
                    stats[key.strip()] = int(value)
                except ValueError:
                    pass

        # Calculate available memory (free + inactive + speculative)
        free_pages = stats.get('Pages free', 0)
        inactive_pages = stats.get('Pages inactive', 0)
        speculative_pages = stats.get('Pages speculative', 0)

        available_bytes = (free_pages + inactive_pages + speculative_pages) * pagesize
        available_gb = available_bytes / (1024 ** 3)

        # Get total memory
        total_bytes = int(sp.check_output(
            ['sysctl', '-n', 'hw.memsize']
        ).decode().strip())
        total_gb = total_bytes / (1024 ** 3)

    except Exception:
        # Fallback
        available_gb = 2.0
        total_gb = 8.0

    used_percent = ((total_gb - available_gb) / total_gb) * 100
    available_mb = available_gb * 1024

    # Define tier requirements
    tier_requirements = {
        "ZERO_COST": {
            "ram_mb": 0,
            "description": "Apple Vision OCR, PIL analysis",
            "always_available": True,
        },
        "LIGHTWEIGHT": {
            "ram_mb": 200,
            "description": "CoreML face detection, basic classifiers",
            "always_available": False,
        },
        "LOCAL_VLM": {
            "ram_mb": 4000,  # nanoLLaVA peak usage
            "description": "nanoLLaVA 1.5B for general vision Q&A",
            "always_available": False,
        },
        "CLAUDE": {
            "ram_mb": 0,
            "description": "Escalation to Claude via terminal bridge",
            "always_available": True,
        },
    }

    # Evaluate each tier
    vision_tiers = {}
    recommended_tier = "ZERO_COST"
    can_run_vlm = False

    for tier_name, info in tier_requirements.items():
        if info["always_available"]:
            status = "always_available"
        elif available_mb >= info["ram_mb"]:
            status = "available"
            recommended_tier = tier_name  # Higher tier available
        elif available_mb >= info["ram_mb"] * 0.8:
            status = "marginal"
        else:
            status = "insufficient_memory"

        vision_tiers[tier_name] = {
            "ram_mb": info["ram_mb"],
            "description": info["description"],
            "status": status,
        }

        if tier_name == "LOCAL_VLM" and status in ("available", "marginal"):
            can_run_vlm = True

    # Determine resource level
    if available_gb < 0.2:
        resource_level = "CRITICAL"
    elif available_gb < 0.4:
        resource_level = "LOW"
    elif available_gb < 0.7:
        resource_level = "MODERATE"
    else:
        resource_level = "GOOD"

    return {
        "system": {
            "available_gb": round(available_gb, 2),
            "available_mb": round(available_mb, 0),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 1),
        },
        "vision_tiers": vision_tiers,
        "recommended_tier": recommended_tier,
        "can_run_vlm": can_run_vlm,
        "resource_level": resource_level,
        "models": {
            "nanollava": {
                "model_id": VISION_MODELS["nanollava"]["model_id"],
                "reported_mb": VISION_MODELS["nanollava"]["memory_mb"],
                "actual_peak_mb": 4000,
                "available": can_run_vlm,
            }
        },
        "recommendations": _get_memory_recommendations(available_gb, can_run_vlm),
    }


def _get_memory_recommendations(available_gb: float, can_run_vlm: bool) -> List[str]:
    """Generate memory recommendations based on current state."""
    recommendations = []

    if available_gb < 0.5:
        recommendations.append("Memory critically low - only Tier 0 (OCR) recommended")
        recommendations.append("Close unused applications to free RAM")

    if not can_run_vlm:
        recommendations.append("VLM unavailable - use Tier 0/1 or escalate to Claude")
        recommendations.append("Need ~4GB free for nanoLLaVA")

    if 0.5 <= available_gb < 2.0:
        recommendations.append("Limited memory - prefer OCR and CoreML tasks")
        recommendations.append("VLM may work but could be slow")

    if available_gb >= 2.0:
        recommendations.append("Memory OK for vision operations")

    if available_gb >= 4.0:
        recommendations.append("Full vision capability available")

    return recommendations


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_vision_engine(
    adapter_path: Optional[str] = None,
    max_memory_mb: int = 3000,
) -> VisionEngine:
    """Create a configured vision engine"""
    return VisionEngine(
        adapter_path=adapter_path,
        max_memory_mb=max_memory_mb,
    )


def describe_image(
    image_path: str,
    detail_level: str = "medium",
) -> VisionResult:
    """
    Quick function to describe an image.

    Args:
        image_path: Path to image
        detail_level: "quick", "medium", or "detailed"

    Returns:
        VisionResult with description
    """
    engine = create_vision_engine()

    prompts = {
        "quick": "What is this image?",
        "medium": "Describe this image in a few sentences.",
        "detailed": "Provide a detailed description of everything you see in this image.",
    }

    prompt = prompts.get(detail_level, prompts["medium"])

    config = VisionConfig()
    if detail_level == "quick":
        config.model_key = "smolvlm-256m"
    elif detail_level == "detailed":
        config.model_key = "smolvlm-2b-4bit"

    return engine.process_image(image_path, prompt, config)


def detect_objects(image_path: str, target: Optional[str] = None) -> VisionResult:
    """
    Detect objects in an image.

    Args:
        image_path: Path to image
        target: Optional specific object to find

    Returns:
        VisionResult with detection results
    """
    engine = create_vision_engine()

    if target:
        prompt = f"Find and locate '{target}' in this image. Describe its position."
    else:
        prompt = "List all objects you can see in this image."

    config = VisionConfig(model_key="moondream-0.5b")

    return engine.process_image(image_path, prompt, config)


def answer_about_image(image_path: str, question: str) -> VisionResult:
    """
    Answer a question about an image.

    Args:
        image_path: Path to image
        question: Question to answer

    Returns:
        VisionResult with answer
    """
    engine = create_vision_engine()
    return engine.process_image(image_path, question)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Vision Engine")
    parser.add_argument("image", help="Path to image")
    parser.add_argument("prompt", nargs="?", default="Describe this image",
                       help="Prompt/question about the image")
    parser.add_argument("--model", help="Force specific model")
    parser.add_argument("--detail", choices=["quick", "medium", "detailed"],
                       default="medium", help="Detail level")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    engine = create_vision_engine()

    config = VisionConfig()
    if args.model:
        config.model_key = args.model

    result = engine.process_image(args.image, args.prompt, config)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Model: {result.model_used}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Task: {result.task_type.value}")
        print(f"Time: {result.processing_time_ms}ms")
        if result.escalated:
            print(f"Escalated: {result.escalation_reason}")
        print(f"{'='*60}")
        print(f"\n{result.response}\n")
