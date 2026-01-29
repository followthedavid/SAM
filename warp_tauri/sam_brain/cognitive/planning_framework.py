"""
4-Tier Solution Cascade Planning Framework

SAM's approach to planning: Start with the bleeding edge vision,
cascade down to what actually works on the 8GB M2 Mac Mini.

Tiers:
  TIER 1: BLEEDING_EDGE  - Ideal solution (64GB+ RAM)
  TIER 2: CUTTING_EDGE   - Newly available, stable (16-32GB RAM)
  TIER 3: STABLE_OPTIMIZED - Battle-tested, reliable (8GB RAM)
  TIER 4: FALLBACK       - Guaranteed to work, minimal resources

Philosophy:
  Every solution SAM plans follows this hierarchy. We vision the ideal,
  but ship what works. The architecture supports seamless upgrades
  as hardware capabilities expand.

Usage:
    from cognitive.planning_framework import PlanningFramework, Capability

    framework = PlanningFramework()

    # Get best available option for inference
    option = framework.get_best_available(Capability.INFERENCE)
    print(f"Using: {option.name} at {option.tier.value}")

    # Generate full system plan
    plan = framework.generate_system_plan()
    for cap, opt in plan.items():
        print(f"{cap.value}: {opt.name}")

    # Check specific tier availability
    available = framework.check_tier_availability(Capability.TTS, SolutionTier.CUTTING_EDGE)
"""

import os
import subprocess
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class SolutionTier(Enum):
    """Solution tiers from most ambitious to most practical."""
    BLEEDING_EDGE = "bleeding_edge"      # 64GB+ RAM, GPU, experimental
    CUTTING_EDGE = "cutting_edge"        # 16-32GB RAM, recent stable
    STABLE_OPTIMIZED = "stable_optimized"  # 8GB RAM, battle-tested
    FALLBACK = "fallback"                # Minimal resources, always works


class Capability(Enum):
    """System capabilities that can be planned."""
    INFERENCE = "inference"      # LLM inference
    TTS = "tts"                  # Text-to-speech
    STT = "stt"                  # Speech-to-text
    VISION = "vision"           # Image understanding
    EMBEDDING = "embedding"     # Vector embeddings
    TRAINING = "training"       # Model fine-tuning
    MEMORY = "memory"           # RAG/memory systems
    CODE = "code"               # Code execution/analysis
    TERMINAL = "terminal"       # System control


@dataclass
class TierOption:
    """A solution option at a specific tier."""
    tier: SolutionTier
    name: str
    description: str
    requirements: str
    ram_estimate_gb: float
    latency_estimate: str  # e.g., "100ms", "2-5s"
    availability_check: Optional[Callable[[], bool]] = None
    _available: Optional[bool] = field(default=None, repr=False)

    @property
    def available(self) -> bool:
        """Check if this option is available on the system."""
        if self._available is not None:
            return self._available
        if self.availability_check is not None:
            self._available = self.availability_check()
        else:
            # Default: available if RAM requirement is met
            self._available = _get_available_ram_gb() >= self.ram_estimate_gb
        return self._available

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tier": self.tier.value,
            "name": self.name,
            "description": self.description,
            "requirements": self.requirements,
            "ram_estimate_gb": self.ram_estimate_gb,
            "latency_estimate": self.latency_estimate,
            "available": self.available
        }


def _get_available_ram_gb() -> float:
    """Get available RAM in GB."""
    try:
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # Parse vm_stat output
        lines = result.stdout.strip().split("\n")
        page_size = 16384  # Default macOS page size

        # Get free + inactive pages
        free_pages = 0
        inactive_pages = 0
        for line in lines:
            if "Pages free:" in line:
                free_pages = int(line.split(":")[1].strip().rstrip("."))
            elif "Pages inactive:" in line:
                inactive_pages = int(line.split(":")[1].strip().rstrip("."))

        available_bytes = (free_pages + inactive_pages) * page_size
        return available_bytes / (1024 ** 3)
    except Exception:
        return 4.0  # Conservative default


def _check_mlx_available() -> bool:
    """Check if MLX is available."""
    try:
        import mlx.core
        return True
    except ImportError:
        return False


def _check_macos() -> bool:
    """Check if running on macOS."""
    import platform
    return platform.system() == "Darwin"


def _check_rvc_model_exists() -> bool:
    """Check if RVC voice model exists."""
    rvc_path = os.path.expanduser("~/ReverseLab/SAM/voice_models/dustin_steele")
    return os.path.exists(rvc_path)


def _check_whisper_model_exists() -> bool:
    """Check if Whisper model exists."""
    whisper_path = os.path.expanduser("~/.cache/huggingface/hub/models--openai--whisper-large-v3")
    base_path = os.path.expanduser("~/.cache/huggingface/hub/models--openai--whisper-base")
    return os.path.exists(whisper_path) or os.path.exists(base_path)


def _check_vlm_model_exists() -> bool:
    """Check if a local VLM model exists."""
    # Check for nanoLLaVA or similar
    model_paths = [
        os.path.expanduser("~/.cache/huggingface/hub/models--qnguyen3--nanoLLaVA"),
        "/Volumes/David External/SAM_models/nanoLLaVA",
    ]
    return any(os.path.exists(p) for p in model_paths)


# Pre-defined capability options for 8GB M2 Mac Mini
CAPABILITY_OPTIONS: Dict[Capability, Dict[SolutionTier, TierOption]] = {

    Capability.INFERENCE: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Qwen2.5-32B + MLX Speculative",
            description="Large model with speculative decoding for speed",
            requirements="64GB+ RAM, or GPU offloading",
            ram_estimate_gb=64.0,
            latency_estimate="1-3s",
            availability_check=lambda: False  # Never on 8GB
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="Qwen2.5-7B MLX 4-bit",
            description="Medium model with excellent reasoning",
            requirements="16GB RAM, MLX",
            ram_estimate_gb=16.0,
            latency_estimate="2-5s",
            availability_check=lambda: _check_mlx_available() and _get_available_ram_gb() >= 14.0
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="Qwen2.5-3B MLX 4-bit",
            description="Compact model with KV-cache quantization",
            requirements="8GB RAM, MLX",
            ram_estimate_gb=6.0,
            latency_estimate="1-3s",
            availability_check=_check_mlx_available
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="Qwen2.5-1.5B MLX 4-bit + SAM LoRA",
            description="Fast inference with fine-tuned personality",
            requirements="4GB RAM, MLX",
            ram_estimate_gb=2.5,
            latency_estimate="500ms-1s",
            availability_check=_check_mlx_available
        ),
    },

    Capability.TTS: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="XTTS-v2 + Real-time Emotion + RVC",
            description="Zero-shot cloning with live emotion control",
            requirements="GPU with 8GB+ VRAM",
            ram_estimate_gb=16.0,
            latency_estimate="200-500ms",
            availability_check=lambda: False
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="F5-TTS + RVC Voice Cloning",
            description="High quality synthesis with Dustin Steele voice",
            requirements="CPU/MPS, RVC model",
            ram_estimate_gb=4.0,
            latency_estimate="5-15s",
            availability_check=_check_rvc_model_exists
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="F5-TTS Native",
            description="Natural voice without cloning, faster",
            requirements="CPU/MPS",
            ram_estimate_gb=2.0,
            latency_estimate="2-5s",
            availability_check=_check_mlx_available
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="macOS 'say' with Prosody Control",
            description="Instant response with pitch/rate emotion mapping",
            requirements="macOS only",
            ram_estimate_gb=0.0,
            latency_estimate="<100ms",
            availability_check=_check_macos
        ),
    },

    Capability.STT: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Whisper Large-v3 + Real-time Streaming",
            description="State-of-the-art accuracy with word-by-word output",
            requirements="16GB+ RAM, low latency audio pipeline",
            ram_estimate_gb=16.0,
            latency_estimate="<500ms",
            availability_check=lambda: False
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="Whisper Large-v3 MLX Batch",
            description="Best accuracy, batch processing",
            requirements="8GB RAM, Whisper model",
            ram_estimate_gb=6.0,
            latency_estimate="2-4s",
            availability_check=_check_whisper_model_exists
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="Whisper Base/Small MLX",
            description="Good accuracy, faster processing",
            requirements="4GB RAM, Whisper model",
            ram_estimate_gb=2.0,
            latency_estimate="1-2s",
            availability_check=_check_mlx_available
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="macOS Dictation API",
            description="System dictation, always available",
            requirements="macOS, microphone",
            ram_estimate_gb=0.0,
            latency_estimate="real-time",
            availability_check=_check_macos
        ),
    },

    Capability.VISION: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Claude Vision / GPT-4V",
            description="State-of-the-art visual reasoning",
            requirements="API access, cost",
            ram_estimate_gb=0.0,
            latency_estimate="2-5s",
            availability_check=lambda: True  # Via terminal escalation
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="nanoLLaVA MLX",
            description="Local VLM for general image understanding",
            requirements="4GB RAM, VLM model",
            ram_estimate_gb=4.0,
            latency_estimate="10-60s",
            availability_check=_check_vlm_model_exists
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="CoreML Detection + Apple OCR",
            description="Fast object/face detection with text extraction",
            requirements="macOS CoreML",
            ram_estimate_gb=0.5,
            latency_estimate="100ms",
            availability_check=_check_macos
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="Apple Vision OCR Only",
            description="Zero-cost text extraction from images",
            requirements="macOS",
            ram_estimate_gb=0.0,
            latency_estimate="22ms",
            availability_check=_check_macos
        ),
    },

    Capability.EMBEDDING: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="BGE-Large + Reranker",
            description="High-dimensional embeddings with cross-encoder reranking",
            requirements="8GB+ RAM, GPU preferred",
            ram_estimate_gb=8.0,
            latency_estimate="50-100ms",
            availability_check=lambda: False
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="E5-Small MLX + BM25 Hybrid",
            description="Semantic + keyword hybrid search",
            requirements="4GB RAM, MLX",
            ram_estimate_gb=1.5,
            latency_estimate="20-50ms",
            availability_check=_check_mlx_available
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="MiniLM-L6-v2 MLX",
            description="384-dim embeddings, fast and efficient",
            requirements="2GB RAM, MLX",
            ram_estimate_gb=0.5,
            latency_estimate="10ms",
            availability_check=_check_mlx_available
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="SQLite FTS5 Full-Text Search",
            description="Keyword-based search, no ML required",
            requirements="SQLite",
            ram_estimate_gb=0.0,
            latency_estimate="<5ms",
            availability_check=lambda: True
        ),
    },

    Capability.TRAINING: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Full Fine-tuning with DeepSpeed",
            description="Complete model weight updates at scale",
            requirements="Multi-GPU, 100GB+ VRAM",
            ram_estimate_gb=100.0,
            latency_estimate="hours-days",
            availability_check=lambda: False
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="QLoRA 4-bit Training",
            description="Quantized LoRA training on consumer GPUs",
            requirements="16GB GPU VRAM",
            ram_estimate_gb=16.0,
            latency_estimate="1-4 hours",
            availability_check=lambda: False
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="MLX LoRA Training",
            description="Apple Silicon native LoRA fine-tuning",
            requirements="8GB RAM, MLX",
            ram_estimate_gb=6.0,
            latency_estimate="2-8 hours",
            availability_check=_check_mlx_available
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="Prompt Engineering + Few-shot",
            description="Behavior modification without training",
            requirements="None",
            ram_estimate_gb=0.0,
            latency_estimate="instant",
            availability_check=lambda: True
        ),
    },

    Capability.MEMORY: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="GraphRAG + Multi-hop Reasoning",
            description="Knowledge graph with relationship traversal",
            requirements="Graph DB, 16GB+ RAM",
            ram_estimate_gb=16.0,
            latency_estimate="100-500ms",
            availability_check=lambda: False
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="Vector DB + HyDE Retrieval",
            description="Hypothetical document embeddings for better recall",
            requirements="8GB RAM, MLX embeddings",
            ram_estimate_gb=4.0,
            latency_estimate="50-100ms",
            availability_check=_check_mlx_available
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="SQLite + MLX Embeddings",
            description="Semantic + FTS5 hybrid in single file",
            requirements="4GB RAM, SQLite",
            ram_estimate_gb=1.0,
            latency_estimate="10-30ms",
            availability_check=lambda: True
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="In-memory Context with Decay",
            description="Working memory with importance-based forgetting",
            requirements="RAM only",
            ram_estimate_gb=0.1,
            latency_estimate="<1ms",
            availability_check=lambda: True
        ),
    },

    Capability.CODE: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Secure Sandbox + Live Preview",
            description="Isolated execution with UI rendering",
            requirements="Docker/VM, resources",
            ram_estimate_gb=8.0,
            latency_estimate="1-5s",
            availability_check=lambda: False  # Docker on-demand only
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="Python Subprocess + AST Validation",
            description="Execute with security checks and output capture",
            requirements="Python runtime",
            ram_estimate_gb=0.5,
            latency_estimate="100ms-2s",
            availability_check=lambda: True
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="Syntax Validation + Static Analysis",
            description="Parse and validate without execution",
            requirements="Python AST",
            ram_estimate_gb=0.0,
            latency_estimate="<50ms",
            availability_check=lambda: True
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="Code Formatting + Explanation",
            description="Format, explain, and suggest without running",
            requirements="None",
            ram_estimate_gb=0.0,
            latency_estimate="instant",
            availability_check=lambda: True
        ),
    },

    Capability.TERMINAL: {
        SolutionTier.BLEEDING_EDGE: TierOption(
            tier=SolutionTier.BLEEDING_EDGE,
            name="Full System Control + AppleScript + CLI",
            description="Control any app, read/write anywhere",
            requirements="Full disk access, automation permissions",
            ram_estimate_gb=0.0,
            latency_estimate="<100ms",
            availability_check=_check_macos
        ),
        SolutionTier.CUTTING_EDGE: TierOption(
            tier=SolutionTier.CUTTING_EDGE,
            name="Multi-Terminal Coordination",
            description="Aware of all terminals, coordinate work sessions",
            requirements="SQLite coordination DB",
            ram_estimate_gb=0.0,
            latency_estimate="<50ms",
            availability_check=lambda: True
        ),
        SolutionTier.STABLE_OPTIMIZED: TierOption(
            tier=SolutionTier.STABLE_OPTIMIZED,
            name="Subprocess Commands",
            description="Run shell commands with output capture",
            requirements="Shell access",
            ram_estimate_gb=0.0,
            latency_estimate="varies",
            availability_check=lambda: True
        ),
        SolutionTier.FALLBACK: TierOption(
            tier=SolutionTier.FALLBACK,
            name="Command Suggestions Only",
            description="Tell user what commands to run",
            requirements="None",
            ram_estimate_gb=0.0,
            latency_estimate="instant",
            availability_check=lambda: True
        ),
    },
}

# Tier ordering for cascade (best to fallback)
TIER_ORDER = [
    SolutionTier.BLEEDING_EDGE,
    SolutionTier.CUTTING_EDGE,
    SolutionTier.STABLE_OPTIMIZED,
    SolutionTier.FALLBACK,
]


class PlanningFramework:
    """
    SAM's 4-tier solution cascade planning framework.

    Provides methods to:
    - Check which tier is available for each capability
    - Suggest the best available option
    - Generate a full system plan based on resources
    - Compare options across tiers
    """

    def __init__(self, options: Optional[Dict[Capability, Dict[SolutionTier, TierOption]]] = None):
        """
        Initialize the planning framework.

        Args:
            options: Custom capability options (defaults to CAPABILITY_OPTIONS)
        """
        self.options = options or CAPABILITY_OPTIONS
        self._availability_cache: Dict[str, bool] = {}

    def get_option(self, capability: Capability, tier: SolutionTier) -> Optional[TierOption]:
        """Get the option for a capability at a specific tier."""
        cap_options = self.options.get(capability)
        if cap_options is None:
            return None
        return cap_options.get(tier)

    def get_all_options(self, capability: Capability) -> List[TierOption]:
        """Get all options for a capability, ordered by tier."""
        cap_options = self.options.get(capability)
        if cap_options is None:
            return []
        return [cap_options[tier] for tier in TIER_ORDER if tier in cap_options]

    def check_tier_availability(self, capability: Capability, tier: SolutionTier) -> bool:
        """Check if a specific tier is available for a capability."""
        cache_key = f"{capability.value}:{tier.value}"
        if cache_key in self._availability_cache:
            return self._availability_cache[cache_key]

        option = self.get_option(capability, tier)
        if option is None:
            self._availability_cache[cache_key] = False
            return False

        available = option.available
        self._availability_cache[cache_key] = available
        return available

    def get_best_available(self, capability: Capability) -> Optional[TierOption]:
        """
        Get the best available option for a capability.

        Cascades from BLEEDING_EDGE down to FALLBACK.
        """
        for tier in TIER_ORDER:
            if self.check_tier_availability(capability, tier):
                return self.get_option(capability, tier)
        return None

    def get_available_tier(self, capability: Capability) -> Optional[SolutionTier]:
        """Get the best available tier for a capability."""
        option = self.get_best_available(capability)
        return option.tier if option else None

    def get_all_available(self, capability: Capability) -> List[TierOption]:
        """Get all available options for a capability."""
        return [opt for opt in self.get_all_options(capability) if opt.available]

    def generate_system_plan(self) -> Dict[Capability, TierOption]:
        """
        Generate a full system plan based on available resources.

        Returns the best available option for each capability.
        """
        plan = {}
        for capability in Capability:
            best = self.get_best_available(capability)
            if best:
                plan[capability] = best
        return plan

    def generate_tiered_plan(self) -> Dict[Capability, Dict[str, TierOption]]:
        """
        Generate a plan showing all tiers for each capability.

        Returns dict with 'available' and 'unavailable' options per capability.
        """
        plan = {}
        for capability in Capability:
            available = []
            unavailable = []
            for tier in TIER_ORDER:
                option = self.get_option(capability, tier)
                if option:
                    if option.available:
                        available.append(option)
                    else:
                        unavailable.append(option)
            plan[capability] = {
                "available": available,
                "unavailable": unavailable
            }
        return plan

    def estimate_total_ram(self, plan: Optional[Dict[Capability, TierOption]] = None) -> float:
        """
        Estimate total RAM usage for a plan.

        Note: This is a rough estimate; actual usage varies based on
        concurrent operations and system overhead.
        """
        if plan is None:
            plan = self.generate_system_plan()

        # Sum RAM estimates (with some overlap consideration)
        total = 0.0
        for option in plan.values():
            total += option.ram_estimate_gb

        # Apply overlap factor (components share some memory)
        overlap_factor = 0.7
        return total * overlap_factor

    def get_capability_summary(self, capability: Capability) -> Dict[str, Any]:
        """Get a summary of a capability across all tiers."""
        options = self.get_all_options(capability)
        best = self.get_best_available(capability)

        return {
            "capability": capability.value,
            "best_available": best.name if best else None,
            "best_tier": best.tier.value if best else None,
            "all_tiers": [
                {
                    "tier": opt.tier.value,
                    "name": opt.name,
                    "available": opt.available,
                    "ram_gb": opt.ram_estimate_gb,
                    "latency": opt.latency_estimate
                }
                for opt in options
            ]
        }

    def get_system_summary(self) -> Dict[str, Any]:
        """Get a complete system summary."""
        plan = self.generate_system_plan()
        return {
            "estimated_ram_gb": self.estimate_total_ram(plan),
            "available_ram_gb": _get_available_ram_gb(),
            "capabilities": {
                cap.value: {
                    "tier": opt.tier.value,
                    "name": opt.name,
                    "latency": opt.latency_estimate
                }
                for cap, opt in plan.items()
            }
        }

    def clear_cache(self):
        """Clear the availability cache."""
        self._availability_cache.clear()
        # Also reset cached availability on options
        for cap_options in self.options.values():
            for option in cap_options.values():
                option._available = None


# Singleton instance
_framework: Optional[PlanningFramework] = None


def get_framework() -> PlanningFramework:
    """Get or create the global planning framework instance."""
    global _framework
    if _framework is None:
        _framework = PlanningFramework()
    return _framework


def get_best_option(capability: Capability) -> Optional[TierOption]:
    """Convenience function to get best available option."""
    return get_framework().get_best_available(capability)


def generate_plan() -> Dict[Capability, TierOption]:
    """Convenience function to generate system plan."""
    return get_framework().generate_system_plan()


def main():
    """CLI for testing the planning framework."""
    import sys
    import json

    framework = PlanningFramework()

    def print_header(text: str):
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def print_tier_icon(tier: SolutionTier) -> str:
        icons = {
            SolutionTier.BLEEDING_EDGE: "[1]",
            SolutionTier.CUTTING_EDGE: "[2]",
            SolutionTier.STABLE_OPTIMIZED: "[3]",
            SolutionTier.FALLBACK: "[4]",
        }
        return icons.get(tier, "[?]")

    if len(sys.argv) < 2 or sys.argv[1] == "status":
        # Show system status
        print_header("SAM 4-TIER PLANNING FRAMEWORK")

        print(f"\n  Available RAM: {_get_available_ram_gb():.1f} GB")
        print(f"  MLX Available: {_check_mlx_available()}")
        print(f"  Platform: {'macOS' if _check_macos() else 'Other'}")

        print_header("CURRENT SYSTEM PLAN")
        plan = framework.generate_system_plan()

        for cap in Capability:
            option = plan.get(cap)
            if option:
                tier_icon = print_tier_icon(option.tier)
                avail = "[OK]" if option.available else "[--]"
                print(f"\n  {cap.value.upper():12} {tier_icon} {option.name}")
                print(f"               {avail} {option.latency_estimate}, {option.ram_estimate_gb}GB RAM")

        print(f"\n  Estimated Total RAM: {framework.estimate_total_ram():.1f} GB")

    elif sys.argv[1] == "tiers":
        # Show all tiers for a capability
        cap_name = sys.argv[2] if len(sys.argv) > 2 else "inference"
        try:
            cap = Capability(cap_name.lower())
        except ValueError:
            print(f"Unknown capability: {cap_name}")
            print(f"Available: {[c.value for c in Capability]}")
            sys.exit(1)

        print_header(f"{cap.value.upper()} OPTIONS")

        for option in framework.get_all_options(cap):
            tier_icon = print_tier_icon(option.tier)
            avail = "[OK]" if option.available else "[--]"
            print(f"\n  {tier_icon} {option.tier.value.upper()}")
            print(f"      Name: {option.name}")
            print(f"      {avail} {option.description}")
            print(f"      Requirements: {option.requirements}")
            print(f"      RAM: {option.ram_estimate_gb}GB, Latency: {option.latency_estimate}")

    elif sys.argv[1] == "json":
        # Output as JSON
        summary = framework.get_system_summary()
        print(json.dumps(summary, indent=2))

    elif sys.argv[1] == "all":
        # Show everything
        print_header("SAM 4-TIER PLANNING FRAMEWORK - FULL STATUS")

        tiered = framework.generate_tiered_plan()

        for cap in Capability:
            print(f"\n{'=' * 60}")
            print(f"  {cap.value.upper()}")
            print(f"{'=' * 60}")

            for option in framework.get_all_options(cap):
                tier_icon = print_tier_icon(option.tier)
                avail = "[OK]" if option.available else "[--]"
                print(f"\n  {tier_icon} {option.tier.value}: {option.name}")
                print(f"      {avail} {option.description}")
                print(f"      RAM: {option.ram_estimate_gb}GB | Latency: {option.latency_estimate}")

    else:
        print("Usage: python planning_framework.py [command]")
        print("\nCommands:")
        print("  status     Show current system plan (default)")
        print("  tiers CAP  Show all tiers for a capability")
        print("  all        Show all capabilities and tiers")
        print("  json       Output system summary as JSON")
        print("\nCapabilities:")
        for cap in Capability:
            print(f"  {cap.value}")


if __name__ == "__main__":
    main()
