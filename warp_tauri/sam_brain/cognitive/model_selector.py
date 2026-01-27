"""
Dynamic Model Selector for SAM Cognitive System

Intelligently selects between 1.5B and 3B models based on:
- Context size requirements
- Query complexity
- Memory pressure
- Task type
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of tasks for model selection."""
    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    REASONING = "reasoning"
    CREATIVE = "creative"
    SIMPLE = "simple"


@dataclass
class SelectionResult:
    """Result of model selection."""
    model_key: str          # "1.5b" or "3b"
    reason: str             # Primary reason for selection
    confidence: float       # Confidence in selection (0-1)
    factors: Dict[str, Any] # All factors considered


class DynamicModelSelector:
    """
    Selects optimal model based on multiple factors.

    Decision Matrix:

    | Factor              | 1.5B                | 3B                  |
    |---------------------|---------------------|---------------------|
    | Context size needed | > 256 tokens        | <= 256 tokens       |
    | Query complexity    | Simple/Medium       | Complex/Reasoning   |
    | Confidence required | < 0.8               | >= 0.8              |
    | Task type           | Chat, simple code   | Analysis, debugging |
    | Memory pressure     | High                | Low                 |
    """

    # Complexity patterns
    HIGH_COMPLEXITY_PATTERNS = [
        r"\b(analyze|evaluate|compare|contrast|assess)\b",
        r"\b(debug|trace|investigate|diagnose)\b",
        r"\b(optimize|refactor|architect|design)\b",
        r"\b(explain.*detail|in-depth|comprehensive)\b",
        r"why.*not working",
        r"multi.?step|complex|intricate"
    ]

    LOW_COMPLEXITY_PATTERNS = [
        r"^(hi|hello|hey|thanks|thank you)",
        r"\b(list|show|display|print)\b",
        r"\b(simple|quick|just|basic)\b",
        r"\b(format|lint|check|validate)\b"
    ]

    # Task type patterns
    TASK_PATTERNS = {
        TaskType.DEBUGGING: [
            r"\b(bug|error|exception|crash|fail)\b",
            r"\b(debug|trace|stack|breakpoint)\b",
            r"not working|doesn't work|won't"
        ],
        TaskType.ANALYSIS: [
            r"\b(analyze|evaluate|assess|review)\b",
            r"\b(compare|contrast|difference)\b",
            r"\b(pros|cons|trade.?off)\b"
        ],
        TaskType.REASONING: [
            r"\b(why|how come|explain why)\b",
            r"\b(should|would|could) (i|we|you)\b",
            r"\b(decide|choice|option)\b"
        ],
        TaskType.CODE: [
            r"\b(code|function|class|method)\b",
            r"\b(implement|write|create|build)\b",
            r"```|`[^`]+`"
        ],
        TaskType.CREATIVE: [
            r"\b(write|story|poem|creative)\b",
            r"\b(imagine|pretend|roleplay)\b"
        ],
        TaskType.CHAT: [
            r"^(hi|hello|hey|how are you)",
            r"\b(chat|talk|conversation)\b"
        ]
    }

    def __init__(self):
        """Initialize the model selector."""
        self._selection_history: List[SelectionResult] = []

    def select_model(
        self,
        query: str,
        context_tokens: int = 0,
        confidence_required: float = 0.5,
        memory_pressure: float = 0.5,
        task_type: Optional[TaskType] = None
    ) -> SelectionResult:
        """
        Select optimal model.

        Args:
            query: User query
            context_tokens: Estimated context token count
            confidence_required: Required confidence level (0-1)
            memory_pressure: Current memory pressure (0-1)
            task_type: Override task type detection

        Returns:
            SelectionResult with model choice and reasoning
        """
        factors = {
            "context_tokens": context_tokens,
            "confidence_required": confidence_required,
            "memory_pressure": memory_pressure,
            "query_length": len(query.split())
        }

        # Hard constraints - must use 1.5B
        if context_tokens > 256:
            return SelectionResult(
                model_key="1.5b",
                reason="context_exceeds_3b_limit",
                confidence=1.0,
                factors=factors
            )

        if memory_pressure > 0.85:
            return SelectionResult(
                model_key="1.5b",
                reason="high_memory_pressure",
                confidence=1.0,
                factors=factors
            )

        # Detect task type
        if task_type is None:
            task_type = self._detect_task_type(query)
        factors["detected_task_type"] = task_type.value

        # Estimate complexity
        complexity = self._estimate_complexity(query)
        factors["complexity"] = complexity

        # Calculate scores
        score_3b = 0.0
        reasons = []

        # Complexity factor
        if complexity > 0.7:
            score_3b += 0.35
            reasons.append("high_complexity")
        elif complexity > 0.5:
            score_3b += 0.15
            reasons.append("medium_complexity")

        # Confidence factor
        if confidence_required > 0.8:
            score_3b += 0.2
            reasons.append("high_confidence_needed")

        # Task type factor
        task_scores = {
            TaskType.DEBUGGING: 0.3,
            TaskType.ANALYSIS: 0.25,
            TaskType.REASONING: 0.25,
            TaskType.CODE: 0.1,
            TaskType.CREATIVE: 0.05,
            TaskType.CHAT: -0.1,
            TaskType.SIMPLE: -0.2
        }
        task_boost = task_scores.get(task_type, 0)
        score_3b += task_boost
        if task_boost > 0:
            reasons.append(f"task_type_{task_type.value}")

        # Context size factor (short context allows 3B)
        if context_tokens < 150:
            score_3b += 0.1
            reasons.append("short_context")

        factors["score_3b"] = score_3b

        # Decision threshold
        if score_3b >= 0.4:
            result = SelectionResult(
                model_key="3b",
                reason="+".join(reasons) if reasons else "score_threshold",
                confidence=min(1.0, 0.5 + score_3b),
                factors=factors
            )
        else:
            result = SelectionResult(
                model_key="1.5b",
                reason="default_safer_choice",
                confidence=0.7,
                factors=factors
            )

        self._selection_history.append(result)
        return result

    def _detect_task_type(self, query: str) -> TaskType:
        """Detect task type from query."""
        query_lower = query.lower()

        # Check each task type
        scores = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            scores[task_type] = score

        # Return highest scoring task type
        if scores:
            best_task = max(scores, key=scores.get)
            if scores[best_task] > 0:
                return best_task

        # Check for simple patterns
        for pattern in self.LOW_COMPLEXITY_PATTERNS:
            if re.search(pattern, query_lower):
                return TaskType.SIMPLE

        return TaskType.CHAT  # Default

    def _estimate_complexity(self, query: str) -> float:
        """
        Estimate query complexity (0-1).

        Higher = more complex, prefer 3B model.
        """
        complexity = 0.3  # Base

        query_lower = query.lower()

        # Length factor
        words = len(query.split())
        if words > 100:
            complexity += 0.25
        elif words > 50:
            complexity += 0.15
        elif words > 20:
            complexity += 0.05

        # High complexity patterns
        for pattern in self.HIGH_COMPLEXITY_PATTERNS:
            if re.search(pattern, query_lower):
                complexity += 0.15

        # Low complexity patterns reduce score
        for pattern in self.LOW_COMPLEXITY_PATTERNS:
            if re.search(pattern, query_lower):
                complexity -= 0.1

        # Technical indicators
        technical_patterns = [
            r"```",                      # Code blocks
            r"\b[A-Z][a-z]+[A-Z]\w*\b",  # CamelCase
            r"\b[a-z]+_[a-z_]+\b",       # snake_case
            r"https?://",               # URLs
            r"\d+\.\d+",                # Version numbers
        ]

        for pattern in technical_patterns:
            if re.search(pattern, query):
                complexity += 0.05

        # Question complexity
        if "?" in query:
            # Multiple questions
            if query.count("?") > 1:
                complexity += 0.1
            # "Why" questions are often complex
            if re.search(r"\bwhy\b", query_lower):
                complexity += 0.1

        return min(1.0, max(0.0, complexity))

    def get_selection_stats(self) -> Dict[str, Any]:
        """Get statistics on model selections."""
        if not self._selection_history:
            return {"total": 0}

        total = len(self._selection_history)
        model_counts = {"1.5b": 0, "3b": 0}

        for result in self._selection_history:
            model_counts[result.model_key] = model_counts.get(result.model_key, 0) + 1

        return {
            "total": total,
            "model_counts": model_counts,
            "3b_ratio": model_counts.get("3b", 0) / total if total > 0 else 0
        }


# Convenience function
def select_model(
    query: str,
    context_tokens: int = 0,
    confidence_required: float = 0.5,
    memory_pressure: float = 0.5
) -> Tuple[str, str]:
    """
    Quick model selection.

    Returns: (model_key, reason)
    """
    selector = DynamicModelSelector()
    result = selector.select_model(
        query=query,
        context_tokens=context_tokens,
        confidence_required=confidence_required,
        memory_pressure=memory_pressure
    )
    return result.model_key, result.reason


if __name__ == "__main__":
    # Demo
    print("Dynamic Model Selector Demo")
    print("=" * 50)

    selector = DynamicModelSelector()

    test_queries = [
        ("Hey, how are you?", 50),
        ("Debug this async error in my Python code", 100),
        ("Analyze the trade-offs between REST and GraphQL", 150),
        ("List all files in the directory", 50),
        ("Why is my React component re-rendering too often?", 200),
        ("Write a comprehensive guide to microservices architecture", 300),
    ]

    for query, ctx_tokens in test_queries:
        result = selector.select_model(query, context_tokens=ctx_tokens)
        print(f"\nQuery: {query[:50]}...")
        print(f"  Context: {ctx_tokens} tokens")
        print(f"  Model: {result.model_key}")
        print(f"  Reason: {result.reason}")
        print(f"  Confidence: {result.confidence:.2f}")

    print("\n" + "=" * 50)
    print("Stats:", selector.get_selection_stats())
