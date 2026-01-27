#!/usr/bin/env python3
"""
SAM Parity System - Comprehensive path to Claude Code + ChatGPT equivalence

TRUTH: A 1.5B model can't match the raw intelligence of 100B+ models.
STRATEGY: Compensate through orchestration, memory, specialization, and escalation.

This system:
1. Defines every capability Claude Code and ChatGPT have
2. Maps each to SAM's implementation strategy
3. Provides self-training loops where SAM learns from escalations
4. Extracts patterns from successful Claude responses

The goal: SAM handles 80%+ of requests locally, learns from escalations,
and eventually needs Claude less and less.
"""

import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import re


# =============================================================================
# CAPABILITY MAPPING: What Claude Code + ChatGPT can do
# =============================================================================

class Capability(Enum):
    # Claude Code capabilities
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    GLOB_SEARCH = "glob_search"
    GREP_SEARCH = "grep_search"
    BASH_EXECUTE = "bash_execute"
    GIT_OPERATIONS = "git_operations"
    WEB_SEARCH = "web_search"
    WEB_FETCH = "web_fetch"
    MULTI_STEP_PLAN = "multi_step_plan"
    TASK_TRACKING = "task_tracking"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ERROR_ANALYSIS = "error_analysis"
    CONTEXT_MANAGEMENT = "context_management"

    # ChatGPT capabilities
    GENERAL_KNOWLEDGE = "general_knowledge"
    CREATIVE_WRITING = "creative_writing"
    MATH_REASONING = "math_reasoning"
    CODE_EXPLANATION = "code_explanation"
    CONVERSATION = "conversation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_UNDERSTANDING = "image_understanding"
    VOICE_INTERACTION = "voice_interaction"

    # Combined/Advanced
    COMPLEX_REASONING = "complex_reasoning"
    MULTI_FILE_REFACTOR = "multi_file_refactor"
    ARCHITECTURE_DESIGN = "architecture_design"
    DEBUGGING = "debugging"


@dataclass
class CapabilityProfile:
    """Profile for each capability with SAM's approach."""
    capability: Capability
    sam_can_handle: bool
    sam_method: str
    confidence_threshold: float  # Below this, escalate
    training_strategy: str
    example_patterns: List[str] = field(default_factory=list)


# SAM's capability map
CAPABILITY_MAP: Dict[Capability, CapabilityProfile] = {
    # =========================================================================
    # FILE OPERATIONS - SAM handles natively
    # =========================================================================
    Capability.FILE_READ: CapabilityProfile(
        capability=Capability.FILE_READ,
        sam_can_handle=True,
        sam_method="Direct pathlib read",
        confidence_threshold=0.9,
        training_strategy="Not needed - deterministic operation",
        example_patterns=["read", "show", "cat", "display file"],
    ),

    Capability.FILE_WRITE: CapabilityProfile(
        capability=Capability.FILE_WRITE,
        sam_can_handle=True,
        sam_method="Direct pathlib write with validation",
        confidence_threshold=0.8,
        training_strategy="Train on file content generation",
        example_patterns=["write", "create file", "save to"],
    ),

    Capability.FILE_EDIT: CapabilityProfile(
        capability=Capability.FILE_EDIT,
        sam_can_handle=True,
        sam_method="Diff-based editing with old_string/new_string",
        confidence_threshold=0.7,
        training_strategy="Train on code diffs, learn edit patterns",
        example_patterns=["change", "modify", "update", "replace", "fix"],
    ),

    Capability.GLOB_SEARCH: CapabilityProfile(
        capability=Capability.GLOB_SEARCH,
        sam_can_handle=True,
        sam_method="pathlib.glob + ripgrep",
        confidence_threshold=0.95,
        training_strategy="Not needed - deterministic",
        example_patterns=["find files", "list *.py", "search for files"],
    ),

    Capability.GREP_SEARCH: CapabilityProfile(
        capability=Capability.GREP_SEARCH,
        sam_can_handle=True,
        sam_method="ripgrep subprocess",
        confidence_threshold=0.95,
        training_strategy="Train on regex pattern generation",
        example_patterns=["search for", "grep", "find in files", "where is"],
    ),

    # =========================================================================
    # BASH / GIT - SAM handles with safety checks
    # =========================================================================
    Capability.BASH_EXECUTE: CapabilityProfile(
        capability=Capability.BASH_EXECUTE,
        sam_can_handle=True,
        sam_method="Subprocess with allowlist + timeout",
        confidence_threshold=0.85,
        training_strategy="Train on command generation + safety patterns",
        example_patterns=["run", "execute", "install", "build", "test"],
    ),

    Capability.GIT_OPERATIONS: CapabilityProfile(
        capability=Capability.GIT_OPERATIONS,
        sam_can_handle=True,
        sam_method="Git CLI wrapper with safety rules",
        confidence_threshold=0.8,
        training_strategy="Train on git workflows, commit message generation",
        example_patterns=["commit", "push", "branch", "merge", "diff", "status"],
    ),

    # =========================================================================
    # WEB - SAM has limited capability, often escalates
    # =========================================================================
    Capability.WEB_SEARCH: CapabilityProfile(
        capability=Capability.WEB_SEARCH,
        sam_can_handle=False,  # No API access
        sam_method="Escalate to Claude or use cached knowledge",
        confidence_threshold=0.3,
        training_strategy="Build local knowledge base from scraped docs",
        example_patterns=["search the web", "look up", "google", "find online"],
    ),

    Capability.WEB_FETCH: CapabilityProfile(
        capability=Capability.WEB_FETCH,
        sam_can_handle=True,
        sam_method="requests + BeautifulSoup for scraping",
        confidence_threshold=0.9,
        training_strategy="Train on HTML parsing, content extraction",
        example_patterns=["fetch url", "get page", "download", "scrape"],
    ),

    # =========================================================================
    # PLANNING - Hybrid (SAM plans, Claude validates complex ones)
    # =========================================================================
    Capability.MULTI_STEP_PLAN: CapabilityProfile(
        capability=Capability.MULTI_STEP_PLAN,
        sam_can_handle=True,  # With templates
        sam_method="Template-based planning + decomposition",
        confidence_threshold=0.6,
        training_strategy="Train on Claude's plan outputs, learn decomposition",
        example_patterns=["plan", "steps to", "how do I", "implement"],
    ),

    Capability.TASK_TRACKING: CapabilityProfile(
        capability=Capability.TASK_TRACKING,
        sam_can_handle=True,
        sam_method="Local todo list + state machine",
        confidence_threshold=0.95,
        training_strategy="Not needed - deterministic",
        example_patterns=["todo", "tasks", "progress", "what's left"],
    ),

    # =========================================================================
    # CODE - SAM's specialty with fine-tuning
    # =========================================================================
    Capability.CODE_GENERATION: CapabilityProfile(
        capability=Capability.CODE_GENERATION,
        sam_can_handle=True,
        sam_method="MLX Qwen2.5-Coder + LoRA fine-tuning",
        confidence_threshold=0.6,
        training_strategy="Fine-tune on your codebase + Claude outputs",
        example_patterns=["write function", "create class", "implement", "code"],
    ),

    Capability.CODE_REVIEW: CapabilityProfile(
        capability=Capability.CODE_REVIEW,
        sam_can_handle=True,  # With checklists
        sam_method="AST analysis + pattern matching + model review",
        confidence_threshold=0.5,
        training_strategy="Train on review patterns, security checklist",
        example_patterns=["review", "check", "analyze code", "any bugs"],
    ),

    Capability.CODE_EXPLANATION: CapabilityProfile(
        capability=Capability.CODE_EXPLANATION,
        sam_can_handle=True,
        sam_method="Model explanation + code structure analysis",
        confidence_threshold=0.6,
        training_strategy="Train on Claude explanations of code",
        example_patterns=["explain", "what does", "how does", "walk through"],
    ),

    Capability.ERROR_ANALYSIS: CapabilityProfile(
        capability=Capability.ERROR_ANALYSIS,
        sam_can_handle=True,  # With pattern library
        sam_method="Error pattern matching + model analysis",
        confidence_threshold=0.5,
        training_strategy="Build error→fix pattern database from Claude",
        example_patterns=["error", "exception", "failed", "not working", "bug"],
    ),

    # =========================================================================
    # COMPLEX REASONING - Often escalates
    # =========================================================================
    Capability.COMPLEX_REASONING: CapabilityProfile(
        capability=Capability.COMPLEX_REASONING,
        sam_can_handle=False,  # 1.5B limitation
        sam_method="Escalate to Claude, learn from response",
        confidence_threshold=0.3,
        training_strategy="Extract reasoning chains from Claude responses",
        example_patterns=["why", "figure out", "analyze", "compare", "decide"],
    ),

    Capability.ARCHITECTURE_DESIGN: CapabilityProfile(
        capability=Capability.ARCHITECTURE_DESIGN,
        sam_can_handle=False,  # Needs broad knowledge
        sam_method="Template library + Claude escalation",
        confidence_threshold=0.3,
        training_strategy="Build architecture template library",
        example_patterns=["design", "architect", "structure", "organize"],
    ),

    Capability.DEBUGGING: CapabilityProfile(
        capability=Capability.DEBUGGING,
        sam_can_handle=True,  # With strategy
        sam_method="Systematic debugging protocol + model assistance",
        confidence_threshold=0.5,
        training_strategy="Train on debugging sessions, stack trace analysis",
        example_patterns=["debug", "fix", "trace", "diagnose"],
    ),

    # =========================================================================
    # MEDIA - SAM handles through integrations
    # =========================================================================
    Capability.IMAGE_GENERATION: CapabilityProfile(
        capability=Capability.IMAGE_GENERATION,
        sam_can_handle=True,
        sam_method="ComfyUI API integration",
        confidence_threshold=0.9,
        training_strategy="Train on prompt engineering for Stable Diffusion",
        example_patterns=["generate image", "create picture", "draw", "visualize"],
    ),

    Capability.IMAGE_UNDERSTANDING: CapabilityProfile(
        capability=Capability.IMAGE_UNDERSTANDING,
        sam_can_handle=True,
        sam_method="Vision engine (Apple Vision + nanoLLaVA + Claude escalation)",
        confidence_threshold=0.7,
        training_strategy="Vision fine-tuning if model available",
        example_patterns=["what's in", "describe image", "look at", "see"],
    ),

    Capability.VOICE_INTERACTION: CapabilityProfile(
        capability=Capability.VOICE_INTERACTION,
        sam_can_handle=True,
        sam_method="Voice pipeline (Whisper + TTS + emotion)",
        confidence_threshold=0.9,
        training_strategy="Already implemented",
        example_patterns=["voice", "speak", "listen", "say"],
    ),

    # =========================================================================
    # CONVERSATION - SAM's personality
    # =========================================================================
    Capability.CONVERSATION: CapabilityProfile(
        capability=Capability.CONVERSATION,
        sam_can_handle=True,
        sam_method="MLX model with personality fine-tuning",
        confidence_threshold=0.8,
        training_strategy="Fine-tune on SAM personality data",
        example_patterns=["chat", "talk", "hey", "what's up"],
    ),

    Capability.GENERAL_KNOWLEDGE: CapabilityProfile(
        capability=Capability.GENERAL_KNOWLEDGE,
        sam_can_handle=False,  # 1.5B knowledge limited
        sam_method="RAG from indexed knowledge + Claude escalation",
        confidence_threshold=0.4,
        training_strategy="Build searchable knowledge base",
        example_patterns=["what is", "who is", "explain", "tell me about"],
    ),

    Capability.CREATIVE_WRITING: CapabilityProfile(
        capability=Capability.CREATIVE_WRITING,
        sam_can_handle=True,  # With personality
        sam_method="Model generation with SAM personality",
        confidence_threshold=0.7,
        training_strategy="Fine-tune on creative writing samples",
        example_patterns=["write", "story", "poem", "creative"],
    ),
}


# =============================================================================
# ESCALATION LEARNING SYSTEM
# =============================================================================

@dataclass
class EscalationEvent:
    """Record of when SAM escalated to Claude."""
    timestamp: str
    user_request: str
    capability_needed: Capability
    sam_attempt: Optional[str]  # What SAM tried first
    claude_response: str
    learned_pattern: Optional[str]  # Pattern extracted
    quality_score: float  # 1-10, human feedback


class EscalationLearner:
    """
    Learns from every escalation to Claude.

    The key insight: Every time we call Claude, we get a free training example.
    Over time, SAM should need Claude less and less.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = data_dir / "escalation_events.jsonl"
        self.patterns_file = data_dir / "learned_patterns.json"
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, List[Dict]]:
        """Load previously learned patterns."""
        if self.patterns_file.exists():
            return json.load(open(self.patterns_file))
        return {}

    def _save_patterns(self):
        """Save learned patterns."""
        with open(self.patterns_file, "w") as f:
            json.dump(self.patterns, f, indent=2)

    def record_escalation(
        self,
        user_request: str,
        capability: Capability,
        claude_response: str,
        sam_attempt: Optional[str] = None,
    ) -> EscalationEvent:
        """Record an escalation event for learning."""
        event = EscalationEvent(
            timestamp=datetime.now().isoformat(),
            user_request=user_request,
            capability_needed=capability,
            sam_attempt=sam_attempt,
            claude_response=claude_response,
            learned_pattern=None,
            quality_score=0.0,
        )

        # Extract pattern
        pattern = self._extract_pattern(user_request, claude_response, capability)
        event.learned_pattern = pattern

        # Save event
        with open(self.events_file, "a") as f:
            f.write(json.dumps({
                "timestamp": event.timestamp,
                "request": event.user_request,
                "capability": capability.value,
                "sam_attempt": event.sam_attempt,
                "claude_response": event.claude_response[:2000],  # Truncate
                "pattern": event.learned_pattern,
            }) + "\n")

        # Add to patterns
        if pattern:
            cap_key = capability.value
            if cap_key not in self.patterns:
                self.patterns[cap_key] = []
            self.patterns[cap_key].append({
                "request_type": self._categorize_request(user_request),
                "pattern": pattern,
                "example_request": user_request[:200],
                "example_response": claude_response[:500],
            })
            self._save_patterns()

        return event

    def _extract_pattern(
        self,
        request: str,
        response: str,
        capability: Capability
    ) -> Optional[str]:
        """Extract a reusable pattern from Claude's response."""

        # Different extraction strategies per capability
        if capability == Capability.CODE_GENERATION:
            # Extract the code structure
            code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
            if code_blocks:
                return f"CODE_TEMPLATE: {self._generalize_code(code_blocks[0])}"

        elif capability == Capability.ERROR_ANALYSIS:
            # Extract error→fix mapping
            if "error" in request.lower() and "fix" in response.lower():
                return f"ERROR_FIX: {self._extract_fix_pattern(response)}"

        elif capability == Capability.COMPLEX_REASONING:
            # Extract reasoning chain
            steps = re.findall(r'(?:First|Then|Next|Finally|Step \d)[,:]?\s*([^.]+\.)', response)
            if steps:
                return f"REASONING_CHAIN: {' -> '.join(steps[:5])}"

        elif capability == Capability.MULTI_STEP_PLAN:
            # Extract plan structure
            numbered = re.findall(r'\d+\.\s*([^\n]+)', response)
            if numbered:
                return f"PLAN_TEMPLATE: {' | '.join(numbered[:7])}"

        elif capability == Capability.CODE_EXPLANATION:
            # Extract explanation style
            if "This" in response and "because" in response:
                return f"EXPLANATION_STYLE: Identified"

        return None

    def _generalize_code(self, code: str) -> str:
        """Generalize code to a reusable template."""
        # Replace specific names with placeholders
        generalized = re.sub(r'def (\w+)', r'def FUNCTION_NAME', code[:200])
        generalized = re.sub(r'class (\w+)', r'class CLASS_NAME', generalized)
        return generalized

    def _extract_fix_pattern(self, response: str) -> str:
        """Extract the fix pattern from an error response."""
        # Look for "change X to Y" patterns
        changes = re.findall(r'change\s+[`"]?(\w+)[`"]?\s+to\s+[`"]?(\w+)[`"]?', response, re.I)
        if changes:
            return f"CHANGE: {changes[0][0]} -> {changes[0][1]}"
        return "FIX_IDENTIFIED"

    def _categorize_request(self, request: str) -> str:
        """Categorize the request type."""
        request_lower = request.lower()

        if any(w in request_lower for w in ["create", "write", "implement"]):
            return "creation"
        elif any(w in request_lower for w in ["fix", "debug", "error"]):
            return "debugging"
        elif any(w in request_lower for w in ["explain", "what", "how"]):
            return "explanation"
        elif any(w in request_lower for w in ["refactor", "improve", "optimize"]):
            return "improvement"
        else:
            return "general"

    def get_similar_patterns(self, request: str, capability: Capability) -> List[Dict]:
        """Find similar patterns from past escalations."""
        cap_key = capability.value
        if cap_key not in self.patterns:
            return []

        request_type = self._categorize_request(request)

        # Return matching patterns
        return [
            p for p in self.patterns[cap_key]
            if p.get("request_type") == request_type
        ][:5]

    def generate_training_data(self) -> List[Dict]:
        """Generate training data from escalation events."""
        if not self.events_file.exists():
            return []

        training_pairs = []

        for line in open(self.events_file):
            try:
                event = json.loads(line)

                # Skip low-quality or incomplete events
                if not event.get("claude_response"):
                    continue

                training_pairs.append({
                    "instruction": event["request"],
                    "input": "",
                    "output": event["claude_response"][:2000],
                    "capability": event["capability"],
                })
            except:
                continue

        return training_pairs

    def get_stats(self) -> Dict:
        """Get escalation statistics."""
        if not self.events_file.exists():
            return {"total_escalations": 0, "by_capability": {}}

        stats = {"total_escalations": 0, "by_capability": {}}

        for line in open(self.events_file):
            try:
                event = json.loads(line)
                stats["total_escalations"] += 1
                cap = event.get("capability", "unknown")
                stats["by_capability"][cap] = stats["by_capability"].get(cap, 0) + 1
            except:
                continue

        return stats


# =============================================================================
# SELF-TRAINING LOOP
# =============================================================================

class SelfTrainingLoop:
    """
    Automated self-improvement through escalation learning.

    The loop:
    1. SAM receives request
    2. SAM attempts to handle locally
    3. If confidence low → Escalate to Claude
    4. Record Claude's response as training example
    5. Extract patterns for future use
    6. Periodically fine-tune on accumulated examples
    """

    def __init__(self, brain_dir: Path):
        self.brain_dir = brain_dir
        self.learner = EscalationLearner(brain_dir / "escalation_data")
        self.training_queue = brain_dir / "training_queue.jsonl"
        self.min_examples_for_training = 50

    def should_escalate(self, request: str, capability: Capability) -> Tuple[bool, float]:
        """
        Decide if we should escalate to Claude.

        Returns (should_escalate, confidence)
        """
        profile = CAPABILITY_MAP.get(capability)
        if not profile:
            return True, 0.0

        # Check if we have learned patterns
        patterns = self.learner.get_similar_patterns(request, capability)
        pattern_boost = min(len(patterns) * 0.1, 0.3)  # Up to 30% boost

        # Base confidence from profile
        confidence = profile.confidence_threshold + pattern_boost

        # Check request complexity
        complexity = self._estimate_complexity(request)
        confidence -= complexity * 0.1

        return confidence < profile.confidence_threshold, confidence

    def _estimate_complexity(self, request: str) -> float:
        """Estimate request complexity (0-1)."""
        indicators = 0

        # Length
        if len(request) > 200:
            indicators += 1
        if len(request) > 500:
            indicators += 1

        # Multiple parts
        if " and " in request.lower():
            indicators += 1
        if re.search(r'\d+\.\s', request):  # Numbered list
            indicators += 1

        # Technical depth
        technical_terms = ["architecture", "refactor", "optimize", "security", "design"]
        for term in technical_terms:
            if term in request.lower():
                indicators += 1

        return min(indicators / 5, 1.0)

    def process_with_escalation(
        self,
        request: str,
        capability: Capability,
        local_handler,  # Function that tries locally
        claude_handler,  # Function that calls Claude
    ) -> Tuple[str, bool]:
        """
        Process request with escalation learning.

        Returns (response, was_escalated)
        """
        should_esc, confidence = self.should_escalate(request, capability)

        if not should_esc:
            # Try local first
            try:
                response = local_handler(request)

                # Validate response quality
                if self._is_quality_response(response):
                    return response, False
            except Exception as e:
                pass  # Fall through to escalation

        # Escalate to Claude
        claude_response = claude_handler(request)

        # Record for learning
        self.learner.record_escalation(
            user_request=request,
            capability=capability,
            claude_response=claude_response,
        )

        # Add to training queue
        self._add_to_training_queue(request, claude_response, capability)

        return claude_response, True

    def _is_quality_response(self, response: str) -> bool:
        """Check if response meets quality threshold."""
        if not response or len(response) < 10:
            return False

        # Check for error indicators
        error_indicators = ["I don't", "I can't", "Error:", "Sorry,", "I'm not sure"]
        for indicator in error_indicators:
            if indicator in response:
                return False

        return True

    def _add_to_training_queue(
        self,
        request: str,
        response: str,
        capability: Capability
    ):
        """Add to training queue for next fine-tuning run."""
        with open(self.training_queue, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "instruction": request,
                "output": response[:2000],
                "capability": capability.value,
            }) + "\n")

    def check_training_ready(self) -> Tuple[bool, int]:
        """Check if we have enough examples for training."""
        if not self.training_queue.exists():
            return False, 0

        count = sum(1 for _ in open(self.training_queue))
        return count >= self.min_examples_for_training, count

    def export_training_data(self) -> Path:
        """Export training queue to MLX format."""
        if not self.training_queue.exists():
            return None

        output_dir = self.brain_dir / "auto_training_data"
        output_dir.mkdir(exist_ok=True)

        # Read queue
        examples = []
        for line in open(self.training_queue):
            try:
                examples.append(json.loads(line))
            except:
                continue

        # Split train/val
        split = int(len(examples) * 0.9)

        # Write in MLX format
        train_file = output_dir / "train.jsonl"
        val_file = output_dir / "valid.jsonl"

        with open(train_file, "w") as f:
            for ex in examples[:split]:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex["instruction"]},
                        {"role": "assistant", "content": ex["output"]},
                    ]
                }) + "\n")

        with open(val_file, "w") as f:
            for ex in examples[split:]:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex["instruction"]},
                        {"role": "assistant", "content": ex["output"]},
                    ]
                }) + "\n")

        return output_dir


# =============================================================================
# CAPABILITY ROUTER
# =============================================================================

class CapabilityRouter:
    """
    Routes requests to the appropriate capability handler.

    Determines what capability is needed and whether to handle
    locally or escalate.
    """

    def __init__(self):
        self.capability_keywords = self._build_keyword_map()

    def _build_keyword_map(self) -> Dict[str, Capability]:
        """Build keyword → capability mapping."""
        mapping = {}

        for cap, profile in CAPABILITY_MAP.items():
            for pattern in profile.example_patterns:
                mapping[pattern.lower()] = cap

        return mapping

    def detect_capability(self, request: str) -> List[Tuple[Capability, float]]:
        """
        Detect which capabilities are needed for a request.

        Returns list of (capability, confidence) tuples.
        """
        request_lower = request.lower()
        detected = []

        # Check keyword matches
        for keyword, cap in self.capability_keywords.items():
            if keyword in request_lower:
                # Higher confidence for longer keyword matches
                conf = 0.5 + (len(keyword) / 50)
                detected.append((cap, min(conf, 0.9)))

        # Additional heuristics
        if re.search(r'```|code|function|class|def ', request_lower):
            detected.append((Capability.CODE_GENERATION, 0.8))

        if re.search(r'error|exception|traceback|failed', request_lower):
            detected.append((Capability.ERROR_ANALYSIS, 0.85))

        if re.search(r'\.py|\.js|\.ts|\.rs', request_lower):
            detected.append((Capability.FILE_READ, 0.7))

        if "?" in request and len(request) < 100:
            detected.append((Capability.CONVERSATION, 0.6))

        # Deduplicate and sort by confidence
        seen = set()
        unique = []
        for cap, conf in sorted(detected, key=lambda x: -x[1]):
            if cap not in seen:
                seen.add(cap)
                unique.append((cap, conf))

        return unique or [(Capability.CONVERSATION, 0.5)]


# =============================================================================
# COMPREHENSIVE EXTRACTION TARGETS
# =============================================================================

def get_all_extraction_targets() -> Dict[str, Dict]:
    """
    Comprehensive list of everything we can legitimately extract.
    """
    return {
        # =====================================================================
        # APPLE NATIVE (No SIP issues - these are public APIs)
        # =====================================================================
        "applescript_dictionaries": {
            "description": "Every app's automation API",
            "method": "sdef command + XML parsing",
            "value": "HIGH - SAM can control any scriptable app",
            "sip_issue": False,
        },
        "url_schemes": {
            "description": "Deep linking into apps",
            "method": "Info.plist parsing",
            "value": "MEDIUM - Quick app control",
            "sip_issue": False,
        },
        "accessibility_api": {
            "description": "UI element control and reading",
            "method": "AXUIElement APIs via pyobjc",
            "value": "HIGH - UI automation and verification",
            "sip_issue": False,  # Just needs permission
        },
        "shortcuts_actions": {
            "description": "All Shortcuts.app actions",
            "method": "Export and parse .shortcut files",
            "value": "HIGH - Apple's blessed automation",
            "sip_issue": False,
        },
        "xcode_headers": {
            "description": "Apple's public framework APIs",
            "method": "Parse headers in Xcode.app",
            "value": "HIGH - All native APIs documented",
            "sip_issue": False,
        },
        "spotlight_metadata": {
            "description": "File metadata and indexing",
            "method": "mdls and mdfind commands",
            "value": "MEDIUM - File discovery",
            "sip_issue": False,
        },

        # =====================================================================
        # OPEN SOURCE (Fully legitimate)
        # =====================================================================
        "mlx_examples": {
            "description": "Apple's ML framework examples",
            "method": "Clone ml-explore/mlx-examples",
            "value": "HIGH - Native Apple Silicon patterns",
            "sip_issue": False,
        },
        "llama_cpp": {
            "description": "Inference optimization patterns",
            "method": "Clone ggerganov/llama.cpp",
            "value": "HIGH - Quantization, context management",
            "sip_issue": False,
        },
        "whisper_cpp": {
            "description": "Speech recognition patterns",
            "method": "Clone ggerganov/whisper.cpp",
            "value": "HIGH - Audio processing",
            "sip_issue": False,
        },
        "homebrew_formulae": {
            "description": "CLI tool patterns",
            "method": "Parse Homebrew/homebrew-core",
            "value": "MEDIUM - How good CLI tools work",
            "sip_issue": False,
        },

        # =====================================================================
        # YOUR OWN DATA (Highest value)
        # =====================================================================
        "chatgpt_exports": {
            "description": "Your ChatGPT conversation history",
            "method": "Parse exported JSON",
            "value": "HIGHEST - Learning from GPT-4 outputs",
            "sip_issue": False,
        },
        "claude_exports": {
            "description": "Your Claude conversation history",
            "method": "Parse exported JSON/conversations.json",
            "value": "HIGHEST - Learning from Claude outputs",
            "sip_issue": False,
        },
        "browser_history": {
            "description": "Sites you actually use",
            "method": "Safari History.db (SQLite)",
            "value": "MEDIUM - What SAM should know about",
            "sip_issue": False,
        },
        "notes_database": {
            "description": "Your notes and knowledge",
            "method": "Apple Notes SQLite DB",
            "value": "HIGH - Personal knowledge base",
            "sip_issue": False,
        },

        # =====================================================================
        # DOCUMENTATION (Public)
        # =====================================================================
        "man_pages": {
            "description": "Unix command documentation",
            "method": "man -k . | parse",
            "value": "MEDIUM - Command-line knowledge",
            "sip_issue": False,
        },
        "installed_packages": {
            "description": "Python/npm package docs",
            "method": "pip show, npm info",
            "value": "HIGH - API knowledge",
            "sip_issue": False,
        },

        # =====================================================================
        # APP BUNDLES (Read-only, SIP allows this)
        # =====================================================================
        "app_resources": {
            "description": "Icons, strings, NIBs from apps",
            "method": "Parse .app bundles",
            "value": "MEDIUM - UI patterns",
            "sip_issue": False,  # Reading is allowed
        },
        "app_entitlements": {
            "description": "What permissions apps request",
            "method": "codesign -d --entitlements",
            "value": "LOW - Security patterns",
            "sip_issue": False,
        },
    }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    import sys

    brain_dir = Path(__file__).parent

    if len(sys.argv) < 2:
        print("SAM Parity System")
        print("=" * 60)
        print()
        print("Commands:")
        print("  capabilities     - Show all capability mappings")
        print("  extraction       - Show all extraction targets")
        print("  stats            - Show escalation learning stats")
        print("  training         - Check training readiness")
        print("  detect <request> - Detect capabilities needed")
        print()

        # Show quick stats
        learner = EscalationLearner(brain_dir / "escalation_data")
        stats = learner.get_stats()
        print(f"Escalation events recorded: {stats['total_escalations']}")

        loop = SelfTrainingLoop(brain_dir)
        ready, count = loop.check_training_ready()
        print(f"Training queue: {count} examples ({'ready' if ready else 'need more'})")

        return

    cmd = sys.argv[1]

    if cmd == "capabilities":
        print("CAPABILITY MAP")
        print("=" * 70)

        for cap, profile in CAPABILITY_MAP.items():
            status = "✓ SAM handles" if profile.sam_can_handle else "→ Escalates"
            print(f"\n{cap.value}")
            print(f"  {status}")
            print(f"  Method: {profile.sam_method}")
            print(f"  Confidence threshold: {profile.confidence_threshold}")
            print(f"  Training: {profile.training_strategy}")

    elif cmd == "extraction":
        print("EXTRACTION TARGETS")
        print("=" * 70)

        targets = get_all_extraction_targets()
        for name, info in targets.items():
            print(f"\n{name}")
            print(f"  Description: {info['description']}")
            print(f"  Method: {info['method']}")
            print(f"  Value: {info['value']}")
            print(f"  SIP Issue: {'Yes' if info['sip_issue'] else 'No'}")

    elif cmd == "stats":
        learner = EscalationLearner(brain_dir / "escalation_data")
        stats = learner.get_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "training":
        loop = SelfTrainingLoop(brain_dir)
        ready, count = loop.check_training_ready()
        print(f"Training examples: {count}")
        print(f"Minimum needed: {loop.min_examples_for_training}")
        print(f"Ready to train: {ready}")

        if ready:
            print("\nTo export training data:")
            print("  python parity_system.py export")

    elif cmd == "export":
        loop = SelfTrainingLoop(brain_dir)
        output = loop.export_training_data()
        if output:
            print(f"Training data exported to: {output}")
        else:
            print("No training data to export")

    elif cmd == "detect" and len(sys.argv) > 2:
        request = " ".join(sys.argv[2:])
        router = CapabilityRouter()
        detected = router.detect_capability(request)

        print(f"Request: {request}")
        print("\nDetected capabilities:")
        for cap, conf in detected:
            profile = CAPABILITY_MAP.get(cap)
            handles = "SAM" if profile and profile.sam_can_handle else "Claude"
            print(f"  {cap.value}: {conf:.2f} → {handles}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
