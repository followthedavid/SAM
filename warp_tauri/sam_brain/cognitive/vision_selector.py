#!/usr/bin/env python3
"""
SAM Vision Selector - Resource-Aware Tier Selection

Phase 3.2.4: Smart vision model selection based on system resources,
task complexity, time constraints, and historical success rates.

Selection Logic:
    - <4GB available: Only Apple Vision + CoreML (ZERO_COST/LIGHTWEIGHT)
    - 4-6GB available: Can load nanoLLaVA (LOCAL_VLM)
    - Complex tasks: Escalate to Claude (CLAUDE tier)

Integration:
    - Uses ResourceManager for real-time memory monitoring
    - Tracks tier success rates in SQLite
    - Provides fallback chains when primary tier fails

Created: 2026-01-25
"""

import os
import re
import sqlite3
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

from .resource_manager import ResourceManager, ResourceLevel, ResourceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vision_selector")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Selector database for tracking success rates
SELECTOR_DB_PATH = Path.home() / ".sam" / "vision_selector.db"
SELECTOR_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Memory thresholds for tier selection (in GB)
# Tuned for 8GB M2 Mac Mini with typical app usage
MEMORY_THRESHOLDS = {
    "zero_cost_max": float("inf"),  # Always available
    "lightweight_min": 0.3,          # Needs ~200MB for CoreML
    "local_vlm_min": 4.0,            # nanoLLaVA needs ~4GB
    "claude_min": 0.5,               # Just needs network + small buffer
}

# Task complexity indicators
COMPLEXITY_PATTERNS = {
    "high": [
        r"explain\s+(in\s+detail|thoroughly|completely)",
        r"analyze\s+(all|every|the\s+relationship)",
        r"compare\s+and\s+contrast",
        r"what\s+is\s+the\s+relationship",
        r"(why|how)\s+does",
        r"step\s+by\s+step",
        r"comprehensive",
        r"deep\s+dive",
        r"all\s+(the\s+)?(details|elements|aspects)",
    ],
    "medium": [
        r"describe",
        r"what\s+(is|are)",
        r"find\s+all",
        r"list\s+(all|every)",
        r"identify",
        r"explain",
    ],
    "low": [
        r"is\s+(this|there|it)",
        r"yes\s+or\s+no",
        r"how\s+many",
        r"what\s+color",
        r"read\s+(the\s+)?text",
        r"count",
        r"quick",
    ],
}

# Task type to minimum viable tier mapping
TASK_MINIMUM_TIERS = {
    "ocr": "ZERO_COST",           # Apple Vision handles OCR perfectly
    "color": "ZERO_COST",         # PIL color analysis
    "basic": "LIGHTWEIGHT",       # Quick classifier
    "face": "LIGHTWEIGHT",        # CoreML face detection
    "detailed": "LOCAL_VLM",      # Need VLM for detailed descriptions
    "detect": "LOCAL_VLM",        # Object detection needs VLM
    "reasoning": "CLAUDE",        # Complex reasoning -> Claude
    "code": "CLAUDE",             # Code review -> Claude
    "ui": "CLAUDE",               # UI analysis -> Claude
    "compare": "CLAUDE",          # Comparison tasks -> Claude
}


class VisionTier(Enum):
    """Vision processing tiers ordered by resource cost."""
    ZERO_COST = 0      # Apple Vision, PIL (instant, 0 extra RAM)
    LIGHTWEIGHT = 1    # CoreML, small classifiers (~200MB)
    LOCAL_VLM = 2      # nanoLLaVA (~4GB RAM)
    CLAUDE = 3         # Claude via terminal bridge (network, 0 local RAM)


@dataclass
class TierCapabilities:
    """Capabilities of each vision tier."""
    tier: VisionTier
    memory_required_gb: float
    typical_latency_ms: int
    tasks_supported: List[str]
    quality_rating: float  # 0-1 scale


# Define tier capabilities
# Each tier should list ALL tasks it can handle, not just its specialties
TIER_CAPABILITIES: Dict[VisionTier, TierCapabilities] = {
    VisionTier.ZERO_COST: TierCapabilities(
        tier=VisionTier.ZERO_COST,
        memory_required_gb=0.0,
        typical_latency_ms=50,
        # OCR and color are zero-cost specialties
        tasks_supported=["ocr", "color"],
        quality_rating=0.7,
    ),
    VisionTier.LIGHTWEIGHT: TierCapabilities(
        tier=VisionTier.LIGHTWEIGHT,
        memory_required_gb=0.2,
        typical_latency_ms=200,
        # Basic descriptions, face detection, plus OCR/color fallback
        tasks_supported=["basic", "face", "ocr", "color"],
        quality_rating=0.75,
    ),
    VisionTier.LOCAL_VLM: TierCapabilities(
        tier=VisionTier.LOCAL_VLM,
        memory_required_gb=4.0,
        typical_latency_ms=30000,  # ~30 seconds typical
        # VLM can handle most tasks except complex reasoning
        tasks_supported=["detailed", "detect", "basic", "face", "ocr", "color"],
        quality_rating=0.85,
    ),
    VisionTier.CLAUDE: TierCapabilities(
        tier=VisionTier.CLAUDE,
        memory_required_gb=0.1,  # Just network buffer
        typical_latency_ms=15000,  # ~15 seconds via terminal
        # Claude handles complex reasoning + everything else
        tasks_supported=["reasoning", "code", "ui", "compare", "detailed", "detect", "basic", "face", "ocr", "color"],
        quality_rating=0.95,
    ),
}


@dataclass
class SelectionContext:
    """Context for tier selection decision."""
    available_memory_gb: float
    resource_level: ResourceLevel
    task_type: str
    complexity: str  # "low", "medium", "high"
    time_constraint_ms: Optional[int]
    previous_tier_failed: Optional[VisionTier]


@dataclass
class TierSelection:
    """Result of tier selection."""
    tier: VisionTier
    reason: str
    fallback_tier: Optional[VisionTier]
    confidence: float
    estimated_latency_ms: int
    context: SelectionContext


# ============================================================================
# TIER SUCCESS TRACKER
# ============================================================================

class TierSuccessTracker:
    """
    Tracks success/failure rates for each tier to inform future selections.

    Stores recent results in SQLite and computes rolling success rates.
    """

    def __init__(self, db_path: Path = SELECTOR_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for tracking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tier_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    latency_ms INTEGER,
                    memory_gb_at_time REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tier_task
                ON tier_results(tier, task_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created
                ON tier_results(created_at)
            """)

    def record_result(
        self,
        tier: VisionTier,
        task_type: str,
        success: bool,
        latency_ms: int,
        memory_gb: float
    ):
        """Record a tier usage result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO tier_results
                   (tier, task_type, success, latency_ms, memory_gb_at_time, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tier.name, task_type, int(success), latency_ms, memory_gb,
                 datetime.now().isoformat())
            )

            # Cleanup old records (keep last 7 days)
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            conn.execute(
                "DELETE FROM tier_results WHERE created_at < ?",
                (cutoff,)
            )

    def get_success_rate(
        self,
        tier: VisionTier,
        task_type: Optional[str] = None,
        hours: int = 24
    ) -> Tuple[float, int]:
        """
        Get success rate for a tier.

        Returns: (success_rate, sample_count)
        """
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            if task_type:
                cursor = conn.execute(
                    """SELECT AVG(success), COUNT(*) FROM tier_results
                       WHERE tier = ? AND task_type = ? AND created_at > ?""",
                    (tier.name, task_type, cutoff)
                )
            else:
                cursor = conn.execute(
                    """SELECT AVG(success), COUNT(*) FROM tier_results
                       WHERE tier = ? AND created_at > ?""",
                    (tier.name, cutoff)
                )

            row = cursor.fetchone()
            rate = row[0] if row[0] is not None else 0.8  # Default 80%
            count = row[1] or 0
            return float(rate), count

    def get_average_latency(
        self,
        tier: VisionTier,
        task_type: Optional[str] = None
    ) -> Optional[int]:
        """Get average latency for a tier."""
        with sqlite3.connect(self.db_path) as conn:
            if task_type:
                cursor = conn.execute(
                    """SELECT AVG(latency_ms) FROM tier_results
                       WHERE tier = ? AND task_type = ? AND success = 1""",
                    (tier.name, task_type)
                )
            else:
                cursor = conn.execute(
                    """SELECT AVG(latency_ms) FROM tier_results
                       WHERE tier = ? AND success = 1""",
                    (tier.name,)
                )

            row = cursor.fetchone()
            return int(row[0]) if row[0] else None

    def get_stats(self) -> Dict[str, Any]:
        """Get overall tracking statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT tier,
                          COUNT(*) as total,
                          SUM(success) as successes,
                          AVG(latency_ms) as avg_latency
                   FROM tier_results
                   GROUP BY tier"""
            )

            stats = {}
            for row in cursor.fetchall():
                tier_name, total, successes, avg_latency = row
                stats[tier_name] = {
                    "total": total,
                    "successes": successes or 0,
                    "success_rate": (successes or 0) / total if total > 0 else 0,
                    "avg_latency_ms": int(avg_latency) if avg_latency else None
                }

            return stats


# ============================================================================
# VISION SELECTOR
# ============================================================================

class VisionSelector:
    """
    Smart vision tier selector based on resources, task, and history.

    Selection Algorithm:
    1. Check available memory
    2. Classify task type and complexity
    3. Determine viable tiers (memory + task support)
    4. Apply success rate weighting
    5. Consider time constraints
    6. Select optimal tier with fallback

    Usage:
        selector = VisionSelector()

        # Basic selection
        selection = selector.select_tier("ocr", available_ram_gb=2.0)

        # Full recommendation
        selection = selector.get_recommended_tier(
            "/path/to/image.png",
            "What text is in this image?"
        )
    """

    def __init__(self):
        self.resource_manager = ResourceManager()
        self.tracker = TierSuccessTracker()
        self._selection_count = 0

    def _classify_task_type(self, prompt: str) -> str:
        """Classify the vision task type from prompt."""
        prompt_lower = prompt.lower()

        # Task type keywords (from smart_vision.py patterns)
        task_keywords = {
            "ocr": ["read", "text", "ocr", "words", "says", "written", "transcribe"],
            "color": ["color", "colour", "hue", "shade", "rgb", "what color"],
            "face": ["face", "person", "who", "people", "portrait"],
            "code": ["code", "programming", "function", "bug", "error", "syntax"],
            "ui": ["ui", "interface", "button", "screen", "app", "click", "layout"],
            "reasoning": ["why", "explain", "analyze", "relationship", "because"],
            "compare": ["compare", "difference", "similar", "versus", "vs"],
            "detect": ["find", "locate", "detect", "where", "count", "how many"],
            "detailed": ["describe", "detail", "everything", "full", "comprehensive"],
            "basic": ["what", "is this", "quick", "brief"],
        }

        # Score each task type
        scores = {}
        for task_type, keywords in task_keywords.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[task_type] = score

        if scores:
            return max(scores, key=scores.get)

        return "basic"  # Default

    def _classify_complexity(self, prompt: str) -> str:
        """Classify task complexity from prompt."""
        prompt_lower = prompt.lower()

        # Check complexity patterns
        for level in ["high", "medium", "low"]:
            patterns = COMPLEXITY_PATTERNS.get(level, [])
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    return level

        # Default based on prompt length
        word_count = len(prompt.split())
        if word_count > 30:
            return "high"
        elif word_count > 10:
            return "medium"
        return "low"

    def _get_viable_tiers(
        self,
        available_ram_gb: float,
        task_type: str
    ) -> List[VisionTier]:
        """
        Get tiers that are viable given memory and task constraints.

        Returns tiers in order of preference (cheapest first that can handle the task).

        Strategy:
        - Start from minimum tier needed for task
        - Include tiers that have enough memory
        - Prefer cheaper tiers over expensive ones
        """
        viable = []

        # Get minimum tier for this task
        min_tier_name = TASK_MINIMUM_TIERS.get(task_type, "LIGHTWEIGHT")
        min_tier = VisionTier[min_tier_name]

        for tier in VisionTier:
            # Must meet minimum tier requirement
            if tier.value < min_tier.value:
                continue

            capabilities = TIER_CAPABILITIES[tier]

            # Check memory requirement
            if tier == VisionTier.LOCAL_VLM:
                # LOCAL_VLM has strict memory requirement (4GB)
                if available_ram_gb < MEMORY_THRESHOLDS["local_vlm_min"]:
                    continue
            elif tier == VisionTier.LIGHTWEIGHT:
                if available_ram_gb < MEMORY_THRESHOLDS["lightweight_min"]:
                    continue
            # ZERO_COST and CLAUDE always viable memory-wise

            # Check if this tier supports the task type
            if task_type in capabilities.tasks_supported:
                viable.append(tier)

        # Sort by value (cheapest first)
        viable.sort(key=lambda t: t.value)

        return viable

    def _apply_success_weighting(
        self,
        tiers: List[VisionTier],
        task_type: str
    ) -> List[Tuple[VisionTier, float]]:
        """
        Apply success rate weighting to tier list.

        Philosophy: STRONGLY prefer cheaper tiers. Only escalate when:
        - Cheaper tier has poor success rate
        - Task explicitly requires complex reasoning

        Returns: List of (tier, score) tuples, sorted by score descending.
        """
        weighted = []

        for tier in tiers:
            success_rate, sample_count = self.tracker.get_success_rate(tier, task_type)

            # Base score: START HIGH and penalize for cost
            # This ensures cheaper tiers are preferred by default
            base_score = 1.0

            # Quality bonus (small - 0.1 max)
            quality_bonus = TIER_CAPABILITIES[tier].quality_rating * 0.1
            base_score += quality_bonus

            # Success rate adjustment (if we have data)
            if sample_count >= 5:
                # Penalize tiers with poor success rate
                if success_rate < 0.5:
                    base_score -= 0.3
                elif success_rate < 0.7:
                    base_score -= 0.1
                # Small bonus for very successful tiers
                elif success_rate > 0.9:
                    base_score += 0.05

            # STRONG cost penalty to prefer cheaper tiers
            # ZERO_COST: 0 penalty, LIGHTWEIGHT: -0.15, LOCAL_VLM: -0.3, CLAUDE: -0.45
            cost_penalty = tier.value * 0.15
            base_score -= cost_penalty

            weighted.append((tier, base_score))

        # Sort by score descending
        weighted.sort(key=lambda x: x[1], reverse=True)

        return weighted

    def _apply_time_constraint(
        self,
        weighted_tiers: List[Tuple[VisionTier, float]],
        time_constraint_ms: Optional[int]
    ) -> List[Tuple[VisionTier, float]]:
        """
        Filter/reweight tiers based on time constraint.
        """
        if time_constraint_ms is None:
            return weighted_tiers

        result = []
        for tier, score in weighted_tiers:
            typical_latency = TIER_CAPABILITIES[tier].typical_latency_ms

            # Check if tier can meet time constraint
            if typical_latency <= time_constraint_ms:
                result.append((tier, score))
            elif typical_latency <= time_constraint_ms * 2:
                # Might make it - reduce score
                result.append((tier, score * 0.7))

        return result

    def select_tier(
        self,
        task_type: str,
        available_ram_gb: Optional[float] = None,
        complexity: str = "medium",
        time_constraint_ms: Optional[int] = None,
        previous_tier_failed: Optional[VisionTier] = None,
    ) -> TierSelection:
        """
        Select the optimal vision tier for a task.

        Args:
            task_type: Type of task ("ocr", "detect", "reasoning", etc.)
            available_ram_gb: Available RAM in GB (auto-detected if None)
            complexity: Task complexity ("low", "medium", "high")
            time_constraint_ms: Maximum acceptable latency
            previous_tier_failed: Tier that failed (for retry logic)

        Returns:
            TierSelection with chosen tier and reasoning
        """
        self._selection_count += 1

        # Get available memory if not provided
        if available_ram_gb is None:
            available_ram_gb, _ = self.resource_manager.get_memory_info()

        resource_level = self.resource_manager.get_resource_level()

        # Build selection context
        context = SelectionContext(
            available_memory_gb=available_ram_gb,
            resource_level=resource_level,
            task_type=task_type,
            complexity=complexity,
            time_constraint_ms=time_constraint_ms,
            previous_tier_failed=previous_tier_failed,
        )

        # Get viable tiers
        viable_tiers = self._get_viable_tiers(available_ram_gb, task_type)

        # Remove previously failed tier
        if previous_tier_failed and previous_tier_failed in viable_tiers:
            viable_tiers.remove(previous_tier_failed)

        # Handle no viable tiers
        if not viable_tiers:
            # Force ZERO_COST as last resort
            return TierSelection(
                tier=VisionTier.ZERO_COST,
                reason="no_viable_tiers_fallback",
                fallback_tier=None,
                confidence=0.3,
                estimated_latency_ms=100,
                context=context,
            )

        # Apply success rate weighting
        weighted_tiers = self._apply_success_weighting(viable_tiers, task_type)

        # Apply time constraint
        if time_constraint_ms:
            weighted_tiers = self._apply_time_constraint(weighted_tiers, time_constraint_ms)

        # Handle empty after constraints
        if not weighted_tiers:
            # Use fastest viable tier
            fastest = min(viable_tiers, key=lambda t: TIER_CAPABILITIES[t].typical_latency_ms)
            return TierSelection(
                tier=fastest,
                reason="time_constraint_fastest_available",
                fallback_tier=viable_tiers[1] if len(viable_tiers) > 1 else None,
                confidence=0.6,
                estimated_latency_ms=TIER_CAPABILITIES[fastest].typical_latency_ms,
                context=context,
            )

        # Select best tier
        best_tier, best_score = weighted_tiers[0]

        # Determine fallback
        fallback_tier = None
        if len(weighted_tiers) > 1:
            fallback_tier = weighted_tiers[1][0]

        # Adjust for complexity
        if complexity == "high" and best_tier.value < VisionTier.LOCAL_VLM.value:
            # High complexity might benefit from better tier
            for tier, score in weighted_tiers:
                if tier.value >= VisionTier.LOCAL_VLM.value:
                    best_tier = tier
                    best_score = score
                    break

        # Build reason
        reasons = []
        reasons.append(f"ram={available_ram_gb:.1f}GB")
        reasons.append(f"task={task_type}")
        reasons.append(f"complexity={complexity}")
        if resource_level == ResourceLevel.CRITICAL:
            reasons.append("memory_critical")
        if previous_tier_failed:
            reasons.append(f"retry_after_{previous_tier_failed.name}")

        return TierSelection(
            tier=best_tier,
            reason="_".join(reasons),
            fallback_tier=fallback_tier,
            confidence=min(best_score, 1.0),
            estimated_latency_ms=TIER_CAPABILITIES[best_tier].typical_latency_ms,
            context=context,
        )

    def get_recommended_tier(
        self,
        image_path: str,
        prompt: str,
        time_constraint_ms: Optional[int] = None,
    ) -> TierSelection:
        """
        Get recommended tier for an image + prompt combination.

        This is the main entry point - analyzes the prompt to determine
        task type and complexity, then selects the optimal tier.

        Args:
            image_path: Path to the image
            prompt: User's question/request
            time_constraint_ms: Optional time limit

        Returns:
            TierSelection with recommendation
        """
        # Classify task
        task_type = self._classify_task_type(prompt)
        complexity = self._classify_complexity(prompt)

        # Get available memory
        available_ram_gb, _ = self.resource_manager.get_memory_info()

        # Special case: if image appears to be a screenshot with text,
        # OCR tier might be sufficient
        if task_type == "basic" and self._looks_like_text_image(image_path):
            task_type = "ocr"

        logger.info(
            f"Vision selection: task={task_type}, complexity={complexity}, "
            f"ram={available_ram_gb:.1f}GB"
        )

        return self.select_tier(
            task_type=task_type,
            available_ram_gb=available_ram_gb,
            complexity=complexity,
            time_constraint_ms=time_constraint_ms,
        )

    def _looks_like_text_image(self, image_path: str) -> bool:
        """Quick check if image likely contains primarily text (screenshot, document)."""
        try:
            from PIL import Image, ImageFilter

            img = Image.open(image_path).convert('L')

            # Check image characteristics
            # Text images tend to have:
            # - High contrast
            # - Many edges (text characters)
            # - Structured patterns

            # Quick edge detection
            edges = img.filter(ImageFilter.FIND_EDGES)
            edge_density = sum(edges.getdata()) / (img.width * img.height * 255)

            # High edge density suggests text
            return edge_density > 0.15

        except Exception:
            return False

    def record_tier_result(
        self,
        tier: VisionTier,
        task_type: str,
        success: bool,
        latency_ms: int
    ):
        """Record a tier usage result for future selection optimization."""
        available_ram_gb, _ = self.resource_manager.get_memory_info()
        self.tracker.record_result(tier, task_type, success, latency_ms, available_ram_gb)

    def get_stats(self) -> Dict[str, Any]:
        """Get selector statistics."""
        return {
            "total_selections": self._selection_count,
            "tier_stats": self.tracker.get_stats(),
            "current_memory_gb": self.resource_manager.get_memory_info()[0],
            "resource_level": self.resource_manager.get_resource_level().value,
            "memory_thresholds": MEMORY_THRESHOLDS,
        }


# ============================================================================
# PUBLIC API
# ============================================================================

# Singleton selector
_selector: Optional[VisionSelector] = None


def get_selector() -> VisionSelector:
    """Get the vision selector instance."""
    global _selector
    if _selector is None:
        _selector = VisionSelector()
    return _selector


def select_tier(
    task: str,
    available_ram: Optional[float] = None,
    **kwargs
) -> VisionTier:
    """
    Quick function to select a vision tier.

    Args:
        task: Task type or prompt string
        available_ram: Available RAM in GB (auto-detected if None)
        **kwargs: Additional args passed to selector

    Returns:
        VisionTier enum value
    """
    selector = get_selector()

    # Determine if task is a type or a prompt
    if task in TASK_MINIMUM_TIERS:
        task_type = task
    else:
        task_type = selector._classify_task_type(task)

    selection = selector.select_tier(
        task_type=task_type,
        available_ram_gb=available_ram,
        **kwargs
    )

    return selection.tier


def get_recommended_tier(image_path: str, prompt: str) -> VisionTier:
    """
    Quick function to get recommended tier for image + prompt.

    Args:
        image_path: Path to image
        prompt: User's question/request

    Returns:
        VisionTier enum value
    """
    selector = get_selector()
    selection = selector.get_recommended_tier(image_path, prompt)
    return selection.tier


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="SAM Vision Selector")
    parser.add_argument("--task", default="basic", help="Task type or prompt")
    parser.add_argument("--image", help="Image path (for full recommendation)")
    parser.add_argument("--ram", type=float, help="Override available RAM (GB)")
    parser.add_argument("--time", type=int, help="Time constraint (ms)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    selector = get_selector()

    if args.stats:
        stats = selector.get_stats()
        if args.json:
            import json
            print(json.dumps(stats, indent=2))
        else:
            print("\nVision Selector Statistics:")
            print(f"  Total selections: {stats['total_selections']}")
            print(f"  Current memory: {stats['current_memory_gb']:.2f} GB")
            print(f"  Resource level: {stats['resource_level']}")
            print("\n  Tier success rates:")
            for tier, data in stats['tier_stats'].items():
                print(f"    {tier}: {data['success_rate']*100:.1f}% ({data['total']} samples)")
        sys.exit(0)

    if args.image:
        # Full recommendation with image
        selection = selector.get_recommended_tier(
            args.image, args.task, time_constraint_ms=args.time
        )
    else:
        # Check if task is a known task type or a prompt string
        if args.task in TASK_MINIMUM_TIERS:
            # Direct task type
            task_type = args.task
            complexity = "medium"
        else:
            # Classify from prompt string
            task_type = selector._classify_task_type(args.task)
            complexity = selector._classify_complexity(args.task)

        selection = selector.select_tier(
            task_type=task_type,
            available_ram_gb=args.ram,
            complexity=complexity,
            time_constraint_ms=args.time,
        )

    if args.json:
        import json
        output = {
            "tier": selection.tier.name,
            "reason": selection.reason,
            "fallback_tier": selection.fallback_tier.name if selection.fallback_tier else None,
            "confidence": selection.confidence,
            "estimated_latency_ms": selection.estimated_latency_ms,
            "context": {
                "available_memory_gb": selection.context.available_memory_gb,
                "resource_level": selection.context.resource_level.value,
                "task_type": selection.context.task_type,
                "complexity": selection.context.complexity,
            }
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Selected Tier: {selection.tier.name}")
        print(f"Reason: {selection.reason}")
        print(f"Confidence: {selection.confidence:.2f}")
        print(f"Estimated Latency: {selection.estimated_latency_ms}ms")
        if selection.fallback_tier:
            print(f"Fallback Tier: {selection.fallback_tier.name}")
        print(f"\nContext:")
        print(f"  Available RAM: {selection.context.available_memory_gb:.1f} GB")
        print(f"  Resource Level: {selection.context.resource_level.value}")
        print(f"  Task Type: {selection.context.task_type}")
        print(f"  Complexity: {selection.context.complexity}")
        print(f"{'='*60}\n")
