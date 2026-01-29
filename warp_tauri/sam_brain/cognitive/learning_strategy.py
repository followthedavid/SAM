#!/usr/bin/env python3
"""
SAM Learning Strategy Framework - 5-Tier Learning Hierarchy

Extracted from efficient_learning.py - the core concept of prioritized learning.

The key insight: With limited training tokens, prioritize WHAT you learn.
Learning fundamentals first enables faster acquisition of advanced concepts.

Tier Hierarchy (pyramid structure - lower tiers are foundations):
  ┌─────────────────────────────────────────────────────────────┐
  │  TIER 5: YOUR SPECIFICS (5%)                                │
  │    Personal preferences, your projects, your voice          │
  ├─────────────────────────────────────────────────────────────┤
  │  TIER 4: DOMAIN EXPERTISE (15%)                             │
  │    Swift/MLX, your frameworks, your stack                   │
  ├─────────────────────────────────────────────────────────────┤
  │  TIER 3: SKILL PATTERNS (25%)                               │
  │    How to code, how to reason, how to plan                  │
  ├─────────────────────────────────────────────────────────────┤
  │  TIER 2: COGNITIVE PRIMITIVES (30%)                         │
  │    Chain-of-thought, self-correction, uncertainty           │
  ├─────────────────────────────────────────────────────────────┤
  │  TIER 1: FUNDAMENTAL STRUCTURES (25%)                       │
  │    Language patterns, logic, consistency                    │
  └─────────────────────────────────────────────────────────────┘

Active Learning (80% savings):
  Only train on mistakes. If the model already knows it, don't waste tokens.

Usage:
    from cognitive.learning_strategy import LearningStrategyFramework, LearningTier

    framework = LearningStrategyFramework()

    # Categorize a training example
    tier = framework.categorize_example(example)

    # Get score for prioritization
    score = framework.score_example(example)

    # Get next priority based on coverage
    next_priority = framework.suggest_next_priority(current_coverage)
"""

import re
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


class LearningTier(Enum):
    """
    The 5-tier learning hierarchy.

    Lower numbers = more fundamental = should be learned first.
    Each tier builds on the previous ones.
    """
    FUNDAMENTAL_STRUCTURES = 1  # Language patterns, logic, consistency
    COGNITIVE_PRIMITIVES = 2    # Chain-of-thought, self-correction, reasoning
    SKILL_PATTERNS = 3          # Coding, planning, problem-solving
    DOMAIN_EXPERTISE = 4        # Swift/MLX/macOS/your specific stack
    YOUR_SPECIFICS = 5          # Personality, preferences, projects

    @property
    def name_readable(self) -> str:
        """Human-readable tier name."""
        names = {
            1: "Fundamental Structures",
            2: "Cognitive Primitives",
            3: "Skill Patterns",
            4: "Domain Expertise",
            5: "Your Specifics",
        }
        return names.get(self.value, "Unknown")


@dataclass
class LearningPriority:
    """
    Defines a learning priority with tier, token budget, and examples.

    Attributes:
        tier: The learning tier this priority belongs to
        percentage: Target percentage of total training tokens (0.0 to 1.0)
        description: Human-readable description of what this tier covers
        examples: List of example pattern types in this tier
        target_count: Target number of training examples for this tier
    """
    tier: LearningTier
    percentage: float
    description: str
    examples: List[str] = field(default_factory=list)
    target_count: int = 0

    @property
    def percentage_display(self) -> str:
        """Display percentage as string."""
        return f"{self.percentage * 100:.0f}%"

    def __post_init__(self):
        """Validate percentage is in valid range."""
        if not 0.0 <= self.percentage <= 1.0:
            raise ValueError(f"Percentage must be between 0 and 1, got {self.percentage}")


@dataclass
class ExampleAnalysis:
    """Result of analyzing a training example."""
    tier: LearningTier
    confidence: float  # 0.0 to 1.0
    detected_patterns: List[str]
    score: float
    reasoning: str


class LearningStrategyFramework:
    """
    Framework for the 5-tier learning hierarchy.

    Manages:
    - Tier definitions and token budgets
    - Example categorization into tiers
    - Priority suggestions based on current coverage
    - Scoring for training example selection

    Key Principle: 80% savings via active learning - prioritize learning from mistakes.
    """

    # Pattern detection regexes for each tier
    TIER_PATTERNS = {
        LearningTier.FUNDAMENTAL_STRUCTURES: {
            "sentence_structure": r"(sentence|grammar|syntax|structure)",
            "logical_connectives": r"(therefore|because|if.*then|however|although)",
            "consistency_patterns": r"(consistent|coherent|logical)",
            "instruction_following": r"(follow|instruction|step|direction)",
            "basic_qa": r"^(what|who|when|where|how many)\s",
            "definition": r"^(define|what is|explain)\s",
            "yes_no": r"^(is|are|can|does|do|will)\s",
        },
        LearningTier.COGNITIVE_PRIMITIVES: {
            "chain_of_thought": r"(let me think|first.*then|step by step)",
            "step_by_step_reasoning": r"(step \d|first,|second,|finally)",
            "self_correction": r"(actually|wait|let me reconsider|i was wrong)",
            "uncertainty_expression": r"(i'm not sure|might be|possibly|uncertain)",
            "asking_clarification": r"(could you clarify|do you mean|can you specify)",
            "deliberation": r"(considering|analyzing|evaluating|weighing)",
            "meta_cognition": r"(i think|i believe|my understanding)",
        },
        LearningTier.SKILL_PATTERNS: {
            "code_explanation": r"(```|def |function |class |import )",
            "debugging_approach": r"(debug|error|fix|issue|traceback|exception)",
            "architecture_thinking": r"(design|architect|system|component|module)",
            "problem_decomposition": r"(break down|decompose|sub-problem|smaller)",
            "solution_comparison": r"(compare|versus|trade-off|pros and cons|alternative)",
            "planning": r"(plan|strategy|approach|roadmap)",
            "how_to": r"^how (do|can|should|would)\s",
        },
        LearningTier.DOMAIN_EXPERTISE: {
            "swift_patterns": r"(swift|swiftui|uikit|cocoa|xcode)",
            "mlx_usage": r"(mlx|apple silicon|metal|neural engine)",
            "macos_native": r"(macos|darwin|appkit|core\s*\w+)",
            "python_async": r"(async|await|asyncio|coroutine)",
            "your_stack": r"(sam|warp|tauri|rust)",
            "framework_specific": r"(pytorch|tensorflow|huggingface|transformers)",
        },
        LearningTier.YOUR_SPECIFICS: {
            "communication_style": r"(personality|tone|voice|style)",
            "project_context": r"(project|repository|codebase|your)",
            "preference_patterns": r"(prefer|like|want|favorite)",
            "personality_voice": r"(cocky|flirty|confident|sarcastic)",
            "user_specific": r"(david|quinton|sam|reverselab)",
        },
    }

    def __init__(self, target_examples: int = 25000):
        """
        Initialize the learning strategy framework.

        Args:
            target_examples: Total target number of training examples
        """
        self.target_examples = target_examples
        self.priorities = self._build_priorities()
        self._coverage = defaultdict(int)  # Track current coverage by tier

    def _build_priorities(self) -> Dict[LearningTier, LearningPriority]:
        """Build the tier priority definitions."""
        tier_configs = {
            LearningTier.FUNDAMENTAL_STRUCTURES: {
                "percentage": 0.25,
                "description": "Language patterns, logic, consistency",
                "examples": [
                    "Sentence structure variations",
                    "Logical connectives usage",
                    "Consistency in responses",
                    "Instruction following",
                ],
            },
            LearningTier.COGNITIVE_PRIMITIVES: {
                "percentage": 0.30,
                "description": "Chain-of-thought, self-correction, uncertainty",
                "examples": [
                    "Step-by-step reasoning",
                    "Self-correction when wrong",
                    "Expressing uncertainty",
                    "Asking for clarification",
                    "Meta-cognitive awareness",
                ],
            },
            LearningTier.SKILL_PATTERNS: {
                "percentage": 0.25,
                "description": "How to code, reason, plan",
                "examples": [
                    "Code explanation patterns",
                    "Debugging approaches",
                    "Architecture thinking",
                    "Problem decomposition",
                    "Solution comparison",
                ],
            },
            LearningTier.DOMAIN_EXPERTISE: {
                "percentage": 0.15,
                "description": "Swift/MLX, your frameworks, your stack",
                "examples": [
                    "Swift/SwiftUI patterns",
                    "MLX usage and optimization",
                    "macOS native APIs",
                    "Your specific tech stack",
                ],
            },
            LearningTier.YOUR_SPECIFICS: {
                "percentage": 0.05,
                "description": "Personal preferences, projects, voice",
                "examples": [
                    "Communication style",
                    "Project context awareness",
                    "Personal preferences",
                    "SAM personality (cocky, flirty)",
                ],
            },
        }

        priorities = {}
        for tier, config in tier_configs.items():
            target_count = int(self.target_examples * config["percentage"])
            priorities[tier] = LearningPriority(
                tier=tier,
                percentage=config["percentage"],
                description=config["description"],
                examples=config["examples"],
                target_count=target_count,
            )

        return priorities

    def categorize_example(self, example: Dict[str, Any]) -> ExampleAnalysis:
        """
        Categorize a training example into the appropriate learning tier.

        Args:
            example: Training example dict with 'user_content'/'assistant_content'
                    or 'messages' format

        Returns:
            ExampleAnalysis with tier, confidence, patterns, and score
        """
        # Extract content from example
        user_content = ""
        assistant_content = ""

        if "messages" in example:
            for msg in example["messages"]:
                if msg.get("role") == "user":
                    user_content = msg.get("content", "")
                elif msg.get("role") == "assistant":
                    assistant_content = msg.get("content", "")
        else:
            user_content = example.get("user_content", "")
            assistant_content = example.get("assistant_content", "")

        combined = f"{user_content} {assistant_content}".lower()

        # Detect patterns for each tier
        tier_scores: Dict[LearningTier, Tuple[int, List[str]]] = {}

        for tier, patterns in self.TIER_PATTERNS.items():
            matches = []
            for pattern_name, regex in patterns.items():
                if re.search(regex, combined, re.IGNORECASE):
                    matches.append(pattern_name)
            tier_scores[tier] = (len(matches), matches)

        # Find the tier with most pattern matches
        # Bias toward higher tiers (more specific) when tied
        best_tier = LearningTier.FUNDAMENTAL_STRUCTURES
        best_score = 0
        best_patterns = []

        for tier in sorted(tier_scores.keys(), key=lambda t: t.value, reverse=True):
            score, patterns = tier_scores[tier]
            if score > best_score:
                best_score = score
                best_tier = tier
                best_patterns = patterns

        # Calculate confidence based on pattern match ratio
        max_patterns = len(self.TIER_PATTERNS.get(best_tier, {}))
        confidence = best_score / max_patterns if max_patterns > 0 else 0.0

        # Calculate overall score for prioritization
        example_score = self.score_example(example, best_tier)

        # Build reasoning
        if best_patterns:
            reasoning = f"Matched {len(best_patterns)} patterns in tier {best_tier.value}: {', '.join(best_patterns[:3])}"
        else:
            reasoning = "No strong pattern matches; defaulting to fundamental structures"

        return ExampleAnalysis(
            tier=best_tier,
            confidence=min(1.0, confidence),
            detected_patterns=best_patterns,
            score=example_score,
            reasoning=reasoning,
        )

    def score_example(self, example: Dict[str, Any],
                      tier: Optional[LearningTier] = None) -> float:
        """
        Score a training example for prioritization.

        Higher scores = higher priority for training.

        Scoring factors:
        - Tier value (lower tiers are foundational, score higher early)
        - Current coverage gap (under-represented tiers score higher)
        - Content quality signals (length, structure)

        Args:
            example: Training example dict
            tier: Pre-determined tier (if known), otherwise will categorize

        Returns:
            Score from 0.0 to 1.0
        """
        if tier is None:
            analysis = self.categorize_example(example)
            tier = analysis.tier

        # Base score from tier priority (foundational = higher base)
        # Invert so tier 1 gets highest base
        tier_weight = (6 - tier.value) / 5.0  # Tier 1 = 1.0, Tier 5 = 0.2

        # Coverage gap bonus
        coverage_gap = self._calculate_coverage_gap(tier)
        gap_bonus = coverage_gap * 0.3  # Up to 0.3 bonus for under-covered tiers

        # Content quality signals
        content = self._extract_content(example)
        quality_score = self._assess_content_quality(content)

        # Combine scores
        score = (tier_weight * 0.4) + (gap_bonus * 0.3) + (quality_score * 0.3)

        return min(1.0, max(0.0, score))

    def _extract_content(self, example: Dict[str, Any]) -> str:
        """Extract text content from example."""
        if "messages" in example:
            parts = []
            for msg in example["messages"]:
                parts.append(msg.get("content", ""))
            return " ".join(parts)
        return f"{example.get('user_content', '')} {example.get('assistant_content', '')}"

    def _assess_content_quality(self, content: str) -> float:
        """
        Assess content quality for training value.

        Returns score from 0.0 to 1.0.
        """
        score = 0.5  # Base score

        # Reward structured content
        if "```" in content:
            score += 0.1  # Has code blocks
        if re.search(r"\d+\.", content):
            score += 0.1  # Has numbered steps
        if re.search(r"\*\*.*\*\*", content):
            score += 0.05  # Has bold formatting

        # Optimal length bonus (not too short, not too long)
        length = len(content)
        if 200 <= length <= 2000:
            score += 0.1
        elif length < 50:
            score -= 0.2  # Too short
        elif length > 5000:
            score -= 0.1  # Too verbose

        # Reward reasoning indicators
        reasoning_patterns = [
            r"because", r"therefore", r"first.*then",
            r"let me", r"step \d", r"the reason"
        ]
        for pattern in reasoning_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.03
                break

        return min(1.0, max(0.0, score))

    def _calculate_coverage_gap(self, tier: LearningTier) -> float:
        """
        Calculate how under-covered a tier is.

        Returns:
            Gap ratio from 0.0 (fully covered) to 1.0 (no coverage)
        """
        priority = self.priorities[tier]
        current = self._coverage.get(tier, 0)
        target = priority.target_count

        if target == 0:
            return 0.0

        coverage_ratio = current / target
        gap = max(0.0, 1.0 - coverage_ratio)

        return gap

    def suggest_next_priority(self,
                              current_coverage: Optional[Dict[LearningTier, int]] = None
                              ) -> LearningPriority:
        """
        Suggest the next learning priority based on current coverage.

        The strategy prioritizes:
        1. Under-covered foundational tiers first
        2. Then moves up the hierarchy

        Args:
            current_coverage: Dict mapping tiers to example counts.
                            If None, uses internal tracking.

        Returns:
            The LearningPriority that should be focused on next
        """
        if current_coverage is not None:
            self._coverage = defaultdict(int, current_coverage)

        # Find the most under-covered tier, prioritizing lower tiers
        best_priority = None
        best_gap = -1.0

        for tier in LearningTier:
            priority = self.priorities[tier]
            gap = self._calculate_coverage_gap(tier)

            # Apply tier weighting - lower tiers get priority boost
            weighted_gap = gap * (6 - tier.value) / 5.0

            if weighted_gap > best_gap:
                best_gap = weighted_gap
                best_priority = priority

        return best_priority or self.priorities[LearningTier.FUNDAMENTAL_STRUCTURES]

    def update_coverage(self, tier: LearningTier, count: int = 1):
        """Update coverage tracking for a tier."""
        self._coverage[tier] += count

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get a report of current coverage by tier.

        Returns:
            Dict with coverage statistics
        """
        report = {
            "total_examples": sum(self._coverage.values()),
            "target_examples": self.target_examples,
            "tiers": {},
        }

        for tier in LearningTier:
            priority = self.priorities[tier]
            current = self._coverage.get(tier, 0)
            target = priority.target_count
            coverage_pct = (current / target * 100) if target > 0 else 0.0

            report["tiers"][tier.name] = {
                "name": tier.name_readable,
                "current": current,
                "target": target,
                "coverage_percent": round(coverage_pct, 1),
                "gap": max(0, target - current),
                "token_budget": priority.percentage_display,
            }

        return report

    def get_tier_hierarchy(self) -> List[Dict[str, Any]]:
        """
        Get the tier hierarchy as a list for display.

        Returns:
            List of tier info dicts, ordered by tier value
        """
        hierarchy = []
        for tier in LearningTier:
            priority = self.priorities[tier]
            hierarchy.append({
                "tier": tier.value,
                "name": tier.name_readable,
                "percentage": priority.percentage_display,
                "description": priority.description,
                "examples": priority.examples,
                "target_count": priority.target_count,
            })
        return hierarchy

    def apply_active_learning_filter(self,
                                      examples: List[Dict[str, Any]],
                                      known_examples: Optional[List[str]] = None
                                      ) -> List[Dict[str, Any]]:
        """
        Apply active learning principle: only train on what's not already known.

        This is the "80% savings via active learning" concept.

        Args:
            examples: List of training examples
            known_examples: List of example hashes/IDs that model already knows

        Returns:
            Filtered list of examples (mistakes/gaps only)
        """
        if known_examples is None:
            # Without knowledge testing, return all examples
            return examples

        known_set = set(known_examples)

        # Filter to only unknown examples
        filtered = []
        for ex in examples:
            # Generate example ID from content
            content = self._extract_content(ex)
            ex_id = hash(content) & 0xFFFFFFFF  # Simple hash

            if str(ex_id) not in known_set:
                filtered.append(ex)

        savings = (1 - len(filtered) / len(examples)) * 100 if examples else 0

        return filtered


# ============================================================================
# CLI MAIN
# ============================================================================

def main():
    """CLI for testing the learning strategy framework."""
    import sys
    import json

    print("\n" + "=" * 70)
    print("  SAM LEARNING STRATEGY FRAMEWORK")
    print("  5-Tier Learning Hierarchy")
    print("=" * 70)

    # Initialize framework
    framework = LearningStrategyFramework(target_examples=25000)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "hierarchy":
            # Show the tier hierarchy
            print("\nLEARNING TIER HIERARCHY")
            print("-" * 70)

            for info in framework.get_tier_hierarchy():
                bar = "#" * int(float(info["percentage"].rstrip("%")) / 5)
                print(f"\n  TIER {info['tier']}: {info['name'].upper()}")
                print(f"  [{bar:<20}] {info['percentage']}")
                print(f"  Description: {info['description']}")
                print(f"  Target: {info['target_count']:,} examples")
                print(f"  Examples:")
                for ex in info["examples"][:3]:
                    print(f"    - {ex}")

        elif cmd == "categorize":
            # Categorize a sample example
            if len(sys.argv) > 2:
                # Read example from file
                with open(sys.argv[2]) as f:
                    example = json.load(f)
            else:
                # Use sample example
                example = {
                    "user_content": "How do I implement async/await in Python?",
                    "assistant_content": """Let me walk you through async/await in Python step by step.

First, understand that async functions are coroutines that can be paused and resumed.

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)  # Simulates I/O
    return "data"

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

The key concepts are:
1. `async def` creates a coroutine function
2. `await` pauses execution until the awaited coroutine completes
3. `asyncio.run()` starts the event loop

This pattern is especially useful for I/O-bound operations.""",
                }

            analysis = framework.categorize_example(example)

            print("\nEXAMPLE ANALYSIS")
            print("-" * 70)
            print(f"  Tier: {analysis.tier.value} - {analysis.tier.name_readable}")
            print(f"  Confidence: {analysis.confidence:.1%}")
            print(f"  Score: {analysis.score:.3f}")
            print(f"  Reasoning: {analysis.reasoning}")
            print(f"  Patterns detected: {', '.join(analysis.detected_patterns)}")

        elif cmd == "coverage":
            # Show coverage report (simulated)
            # Simulate some coverage
            framework.update_coverage(LearningTier.FUNDAMENTAL_STRUCTURES, 1500)
            framework.update_coverage(LearningTier.COGNITIVE_PRIMITIVES, 2000)
            framework.update_coverage(LearningTier.SKILL_PATTERNS, 1000)
            framework.update_coverage(LearningTier.DOMAIN_EXPERTISE, 500)
            framework.update_coverage(LearningTier.YOUR_SPECIFICS, 100)

            report = framework.get_coverage_report()

            print("\nCOVERAGE REPORT")
            print("-" * 70)
            print(f"  Total: {report['total_examples']:,} / {report['target_examples']:,}")
            print()

            for tier_name, info in report["tiers"].items():
                bar_filled = int(info["coverage_percent"] / 5)
                bar = "#" * bar_filled + "-" * (20 - bar_filled)
                print(f"  {info['name']:<25} [{bar}] {info['coverage_percent']:5.1f}%")
                print(f"    {info['current']:,} / {info['target']:,} (gap: {info['gap']:,})")

            # Suggest next priority
            next_priority = framework.suggest_next_priority()
            print(f"\n  NEXT PRIORITY: Tier {next_priority.tier.value} - {next_priority.tier.name_readable}")

        elif cmd == "score":
            # Score example batches
            sample_examples = [
                {
                    "user_content": "What is Python?",
                    "assistant_content": "Python is a programming language.",
                },
                {
                    "user_content": "How do I debug this error?",
                    "assistant_content": "Let me analyze the error step by step. First, I notice...",
                },
                {
                    "user_content": "Design a system for SAM's memory",
                    "assistant_content": """I'll architect this with consideration for your constraints.

**System Design:**
1. **Working Memory** - Short-term context with decay
2. **Semantic Memory** - Vector embeddings for retrieval
3. **Procedural Memory** - Learned patterns

The key insight is using MLX for efficient embeddings...""",
                },
            ]

            print("\nEXAMPLE SCORING")
            print("-" * 70)

            for i, ex in enumerate(sample_examples, 1):
                analysis = framework.categorize_example(ex)
                print(f"\n  Example {i}:")
                print(f"    User: {ex['user_content'][:50]}...")
                print(f"    Tier: {analysis.tier.value} - {analysis.tier.name_readable}")
                print(f"    Score: {analysis.score:.3f}")

        else:
            print(f"Unknown command: {cmd}")
            print("\nCommands: hierarchy, categorize [file], coverage, score")

    else:
        # Default: show summary
        print("\n80% SAVINGS VIA ACTIVE LEARNING")
        print("-" * 70)
        print("  Only train on mistakes. If the model already knows it,")
        print("  don't waste tokens teaching it again.")
        print()
        print("  Token Savings Strategies:")
        print("    - Active Learning:     ~80% (only train on gaps)")
        print("    - Pattern Extraction:  ~90% (one pattern > 100 examples)")
        print("    - Curriculum Order:    ~50% (simple -> complex)")
        print("    - Compression:         ~70% (remove filler, keep signal)")
        print("    - Transfer:            ~95% (learn once, apply everywhere)")

        print("\nTIER HIERARCHY SUMMARY")
        print("-" * 70)
        for info in framework.get_tier_hierarchy():
            print(f"  Tier {info['tier']}: {info['name']:<25} {info['percentage']:>5}")

        print("\nCommands:")
        print("  python learning_strategy.py hierarchy    - Show full tier details")
        print("  python learning_strategy.py categorize   - Categorize sample example")
        print("  python learning_strategy.py coverage     - Show coverage report")
        print("  python learning_strategy.py score        - Score example batch")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
