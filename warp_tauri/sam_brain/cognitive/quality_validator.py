"""
Quality Validator for SAM Cognitive System

Validates response quality with:
- Repetition detection and truncation
- Stop token cleaning
- Confidence scoring
- Escalation decision making
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class QualityIssue(Enum):
    """Types of quality issues."""
    REPETITION = "repetition"
    TRUNCATED = "truncated"
    INCOMPLETE_CODE = "incomplete_code"
    HEDGING = "hedging"
    REFUSAL = "refusal"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    OFF_TOPIC = "off_topic"


class EscalationReason(Enum):
    """Reasons for escalating to Claude."""
    REPETITION_LOOP = "repetition_loop"
    LOW_CONFIDENCE = "low_confidence"
    QUALITY_ISSUES = "quality_issues"
    REFUSAL = "refusal"
    TASK_TOO_COMPLEX = "task_too_complex"
    USER_REQUEST = "user_request"


@dataclass
class QualityAssessment:
    """Quality assessment of a generated response."""
    is_acceptable: bool
    score: float                           # 0-1 quality score
    issues: List[QualityIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    repetition_detected: bool = False
    escalation_recommended: bool = False
    escalation_reason: Optional[EscalationReason] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_acceptable": self.is_acceptable,
            "score": self.score,
            "issues": [i.value for i in self.issues],
            "suggestions": self.suggestions,
            "repetition_detected": self.repetition_detected,
            "escalation_recommended": self.escalation_recommended,
            "escalation_reason": self.escalation_reason.value if self.escalation_reason else None
        }


class QualityValidator:
    """
    Validates response quality with multiple checks.

    Checks performed:
    1. Repetition detection (line and phrase level)
    2. Stop token cleaning
    3. Response length validation
    4. Quality pattern detection
    5. Escalation decision
    """

    # Repetition detection settings
    MIN_REPEAT_LENGTH = 20
    MAX_REPEATS = 3

    # Response length bounds
    MIN_RESPONSE_LENGTH = 10   # Words
    MAX_RESPONSE_LENGTH = 500  # Words (for most queries)

    # Stop tokens to remove
    STOP_TOKENS = [
        "<|im_end|>",
        "<|end|>",
        "<|endoftext|>",
        "</s>",
        "<|assistant|>",
        "<|user|>",
        "[INST]",
        "[/INST]"
    ]

    # Quality issue patterns
    QUALITY_PATTERNS = {
        QualityIssue.TRUNCATED: [
            r"\.{3,}$",          # Ends with ...
            r"…$",               # Ends with ellipsis
            r"and then$",        # Incomplete sentence
            r"such as$"
        ],
        QualityIssue.INCOMPLETE_CODE: [
            r"```[a-z]*\n.*(?<!```)$",  # Unclosed code block
            r"def \w+\([^)]*$",          # Incomplete function def
            r"\{[^}]*$"                  # Unclosed brace
        ],
        QualityIssue.HEDGING: [
            r"i('m| am) not (sure|certain)",
            r"i (don't|do not) (really )?know",
            r"(maybe|perhaps|possibly) (you|we|i)",
            r"(could|might|may) be",
            r"i('m| am) (just|only) (a|an)"
        ],
        QualityIssue.REFUSAL: [
            r"i (can't|cannot|won't|will not) (help|assist|do)",
            r"(inappropriate|unethical|harmful|dangerous)",
            r"beyond my (capabilities|ability|scope)",
            r"(against|violates) (my|the) (guidelines|policies)",
            r"i('m| am) not able to"
        ]
    }

    # Confidence patterns (positive indicators)
    CONFIDENCE_PATTERNS = [
        r"^(here|this|the|to|let me)",  # Direct start
        r"```\w+\n.*```",                # Complete code block
        r"^\d+\.",                        # Numbered list
        r"^[-*]",                         # Bullet list
    ]

    # Uncertainty patterns (negative indicators)
    UNCERTAINTY_PATTERNS = [
        r"i('m| am) not (sure|certain)",
        r"(maybe|perhaps|possibly)",
        r"i (think|believe|guess)",
        r"(might|could|may) (be|work)",
        r"not (entirely|completely) sure"
    ]

    def __init__(self):
        """Initialize quality validator."""
        self._validation_history: List[QualityAssessment] = []

    def validate(
        self,
        response: str,
        original_query: str,
        cognitive_confidence: float = 0.5
    ) -> QualityAssessment:
        """
        Full quality validation of response.

        Args:
            response: Generated response
            original_query: Original user query
            cognitive_confidence: Confidence from cognitive system

        Returns:
            QualityAssessment with all checks
        """
        issues = []
        suggestions = []
        score = 1.0

        # Check for empty response
        if not response or not response.strip():
            return QualityAssessment(
                is_acceptable=False,
                score=0.0,
                issues=[QualityIssue.TOO_SHORT],
                suggestions=["Response is empty"],
                escalation_recommended=True,
                escalation_reason=EscalationReason.QUALITY_ISSUES
            )

        # Check response length
        word_count = len(response.split())

        if word_count < self.MIN_RESPONSE_LENGTH:
            issues.append(QualityIssue.TOO_SHORT)
            suggestions.append("Response is very short")
            score -= 0.2

        # Detect repetition
        cleaned_response, repetition_found = self.truncate_repetition(response)
        if repetition_found:
            issues.append(QualityIssue.REPETITION)
            suggestions.append("Repetition detected and truncated")
            score -= 0.4

        # Check quality patterns
        for issue_type, patterns in self.QUALITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, cleaned_response, re.IGNORECASE | re.DOTALL):
                    if issue_type not in issues:
                        issues.append(issue_type)
                        score -= 0.15
                    break

        # Calculate confidence contribution
        response_confidence = self._calculate_response_confidence(cleaned_response)
        combined_confidence = (cognitive_confidence * 0.6 + response_confidence * 0.4)

        if combined_confidence < 0.4:
            score -= 0.2
            suggestions.append("Low confidence in response")

        # Determine escalation
        escalation_recommended = False
        escalation_reason = None

        if repetition_found:
            escalation_recommended = True
            escalation_reason = EscalationReason.REPETITION_LOOP

        elif QualityIssue.REFUSAL in issues:
            escalation_recommended = True
            escalation_reason = EscalationReason.REFUSAL

        elif combined_confidence < 0.3:
            escalation_recommended = True
            escalation_reason = EscalationReason.LOW_CONFIDENCE

        elif len(issues) >= 3:
            escalation_recommended = True
            escalation_reason = EscalationReason.QUALITY_ISSUES

        # Final assessment
        is_acceptable = score >= 0.5 and not escalation_recommended

        assessment = QualityAssessment(
            is_acceptable=is_acceptable,
            score=max(0.0, min(1.0, score)),
            issues=issues,
            suggestions=suggestions,
            repetition_detected=repetition_found,
            escalation_recommended=escalation_recommended,
            escalation_reason=escalation_reason
        )

        self._validation_history.append(assessment)
        return assessment

    def truncate_repetition(
        self,
        text: str,
        min_repeat_length: int = None,
        max_repeats: int = None
    ) -> Tuple[str, bool]:
        """
        Detect and truncate repetitive patterns.

        Returns: (cleaned_text, was_repetition_found)
        """
        if min_repeat_length is None:
            min_repeat_length = self.MIN_REPEAT_LENGTH
        if max_repeats is None:
            max_repeats = self.MAX_REPEATS

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

        result_text = '\n'.join(result_lines)

        # Also check for repeated phrases within text
        # Pattern: same phrase (15+ chars) repeated 3+ times
        phrase_pattern = r'(.{15,}?)\1{2,}'
        if re.search(phrase_pattern, result_text):
            repetition_found = True
            result_text = re.sub(phrase_pattern, r'\1', result_text)

        # Check for repeated words (5+ times in a row)
        word_repeat_pattern = r'\b(\w+)(?:\s+\1){4,}\b'
        if re.search(word_repeat_pattern, result_text, re.IGNORECASE):
            repetition_found = True
            result_text = re.sub(word_repeat_pattern, r'\1', result_text, flags=re.IGNORECASE)

        return result_text, repetition_found

    def clean_stop_tokens(self, response: str) -> str:
        """Remove stop tokens from response."""
        if not response:
            return ""

        cleaned = response
        for token in self.STOP_TOKENS:
            if token in cleaned:
                cleaned = cleaned.split(token)[0]

        return cleaned.strip()

    def _calculate_response_confidence(self, response: str) -> float:
        """Calculate confidence based on response patterns."""
        confidence = 0.5  # Base

        response_lower = response.lower()

        # Positive patterns increase confidence
        for pattern in self.CONFIDENCE_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                confidence += 0.1

        # Negative patterns decrease confidence
        for pattern in self.UNCERTAINTY_PATTERNS:
            if re.search(pattern, response_lower):
                confidence -= 0.1

        # Code presence increases confidence
        if "```" in response:
            confidence += 0.15

        # Response length (moderate length is good)
        word_count = len(response.split())
        if 50 <= word_count <= 200:
            confidence += 0.1
        elif word_count < 20:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def should_escalate(
        self,
        assessment: QualityAssessment,
        cognitive_state: Dict[str, Any]
    ) -> Tuple[bool, Optional[EscalationReason]]:
        """
        Determine if response should be escalated to Claude.

        Args:
            assessment: Quality assessment from validate()
            cognitive_state: State from cognitive system

        Returns:
            (should_escalate, reason)
        """
        # Already decided in assessment
        if assessment.escalation_recommended:
            return True, assessment.escalation_reason

        # Check cognitive state
        cognitive_confidence = cognitive_state.get("confidence", 0.5)

        if cognitive_confidence < 0.25:
            return True, EscalationReason.LOW_CONFIDENCE

        # Check if task seems too complex
        active_goals = cognitive_state.get("active_goals", [])
        if len(active_goals) > 3:  # Multiple complex goals
            return True, EscalationReason.TASK_TOO_COMPLEX

        return False, None

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get statistics on validations."""
        if not self._validation_history:
            return {"total_validations": 0}

        total = len(self._validation_history)
        acceptable = sum(1 for a in self._validation_history if a.is_acceptable)
        escalated = sum(1 for a in self._validation_history if a.escalation_recommended)
        avg_score = sum(a.score for a in self._validation_history) / total

        issue_counts = {}
        for assessment in self._validation_history:
            for issue in assessment.issues:
                issue_counts[issue.value] = issue_counts.get(issue.value, 0) + 1

        return {
            "total_validations": total,
            "acceptable_ratio": acceptable / total,
            "escalation_ratio": escalated / total,
            "average_score": avg_score,
            "issue_counts": issue_counts
        }


# Convenience functions
def validate_response(
    response: str,
    query: str,
    confidence: float = 0.5
) -> QualityAssessment:
    """Quick response validation."""
    validator = QualityValidator()
    return validator.validate(response, query, confidence)


def clean_response(response: str) -> Tuple[str, bool]:
    """Clean response and detect repetition."""
    validator = QualityValidator()
    cleaned = validator.clean_stop_tokens(response)
    return validator.truncate_repetition(cleaned)


if __name__ == "__main__":
    # Demo
    print("Quality Validator Demo")
    print("=" * 50)

    validator = QualityValidator()

    test_cases = [
        # Good response
        ("Here's how to implement a decorator:\n```python\ndef my_decorator(func):\n    def wrapper(*args):\n        return func(*args)\n    return wrapper\n```",
         "How do decorators work?"),

        # Repetitive response
        ("use serde_json;\nuse serde_json;\nuse serde_json;\nuse serde_json;\nuse serde_json;",
         "How do I parse JSON in Rust?"),

        # Hedging response
        ("I'm not sure, but maybe you could try using async/await? Perhaps that might work, possibly.",
         "How do I handle async in Python?"),

        # Refusal
        ("I cannot help with that request as it would be inappropriate.",
         "Help me hack into a system"),

        # Too short
        ("Yes.",
         "Can you explain how neural networks work?"),
    ]

    for response, query in test_cases:
        print(f"\nQuery: {query}")
        print(f"Response: {response[:50]}...")

        assessment = validator.validate(response, query)
        print(f"  Acceptable: {assessment.is_acceptable}")
        print(f"  Score: {assessment.score:.2f}")
        print(f"  Issues: {[i.value for i in assessment.issues]}")
        print(f"  Escalate: {assessment.escalation_recommended}")
        if assessment.escalation_reason:
            print(f"  Reason: {assessment.escalation_reason.value}")

    print("\n" + "=" * 50)
    print("Stats:", validator.get_validation_stats())
