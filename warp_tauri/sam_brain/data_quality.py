#!/usr/bin/env python3
"""
SAM Data Quality Validator - Ensures training data meets quality standards.

Validates training examples for:
- Length constraints (50-4096 tokens)
- Format correctness (required fields)
- Language detection (English by default)
- Coherence scoring
- PII detection (emails, phones, addresses)
- Secret detection (API keys, passwords, tokens)
- Quality scoring across multiple dimensions

Provides auto-fix capabilities for common issues.
"""

import re
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import unicodedata


class IssueType(Enum):
    """Types of quality issues that can be detected."""
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    MISSING_FIELD = "missing_field"
    INVALID_FORMAT = "invalid_format"
    NON_ENGLISH = "non_english"
    LOW_COHERENCE = "low_coherence"
    CONTAINS_PII = "contains_pii"
    CONTAINS_SECRET = "contains_secret"
    REPETITIVE = "repetitive"
    EMPTY_CONTENT = "empty_content"
    ENCODING_ERROR = "encoding_error"
    TRUNCATED = "truncated"


class IssueSeverity(Enum):
    """Severity levels for quality issues."""
    WARNING = "warning"      # Minor issue, can proceed
    ERROR = "error"          # Serious issue, should fix
    CRITICAL = "critical"    # Must fix before training


@dataclass
class QualityIssue:
    """Represents a single quality issue found in an example."""
    issue_type: IssueType
    severity: IssueSeverity
    message: str
    field: Optional[str] = None
    position: Optional[Tuple[int, int]] = None  # (start, end) character positions
    suggested_fix: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field,
            "position": self.position,
            "suggested_fix": self.suggested_fix
        }


@dataclass
class QualityScore:
    """Quality scores across multiple dimensions."""
    length_score: float = 0.0       # 0-1: appropriate length
    specificity_score: float = 0.0  # 0-1: specific vs generic
    diversity_score: float = 0.0    # 0-1: vocabulary diversity
    difficulty_score: float = 0.0   # 0-1: task complexity
    relevance_score: float = 0.0    # 0-1: domain relevance
    overall_score: float = 0.0      # 0-1: weighted average

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of validating a single example."""
    is_valid: bool
    issues: List[QualityIssue] = field(default_factory=list)
    quality_score: Optional[QualityScore] = None
    example_id: Optional[str] = None
    auto_fixed: bool = False
    fixed_content: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
            "example_id": self.example_id,
            "auto_fixed": self.auto_fixed,
            "fixed_content": self.fixed_content
        }


@dataclass
class ValidationReport:
    """Comprehensive report from validating a dataset."""
    total_examples: int = 0
    valid_examples: int = 0
    invalid_examples: int = 0
    auto_fixed_examples: int = 0
    issue_counts: Dict[str, int] = field(default_factory=dict)
    severity_counts: Dict[str, int] = field(default_factory=dict)
    average_quality_score: float = 0.0
    score_distribution: Dict[str, int] = field(default_factory=dict)  # buckets
    recommendations: List[str] = field(default_factory=list)
    validation_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class DataQualityValidator:
    """
    Validates training data quality for fine-tuning.

    Usage:
        validator = DataQualityValidator()
        is_valid, issues = validator.validate(example)

        # Or with auto-fix
        result = validator.validate_and_fix(example)
        if result.auto_fixed:
            use_example = result.fixed_content
    """

    # Token length constraints (approximate, assuming ~4 chars per token)
    MIN_TOKENS = 50
    MAX_TOKENS = 4096
    CHARS_PER_TOKEN = 4

    # Required fields for training examples - supports multiple formats
    # Standard format: input/output
    # Alternative formats: prompt/response, prompt/good_response, messages
    REQUIRED_FIELDS = {"input", "output"}
    OPTIONAL_FIELDS = {"instruction", "context", "metadata", "source"}

    # Field aliases for different training data formats
    FIELD_ALIASES = {
        "input": ["input", "prompt", "query", "question", "user", "human"],
        "output": ["output", "response", "answer", "assistant", "good_response", "completion"],
        "instruction": ["instruction", "system", "system_prompt"],
        "context": ["context", "background", "personality_notes"],
    }

    # PII patterns
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_us": r'\b(?:\+1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "phone_intl": r'\b\+[1-9][0-9]{6,14}\b',
        "ssn": r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b',
        "credit_card": r'\b(?:[0-9]{4}[-\s]?){3}[0-9]{4}\b',
        "address": r'\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|court|ct)\b',
        "ip_address": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
    }

    # Secret patterns
    SECRET_PATTERNS = {
        "api_key_generic": r'(?i)(?:api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?',
        "api_key_openai": r'\b(?:sk-[A-Za-z0-9]{48})\b',
        "api_key_anthropic": r'\b(?:sk-ant-api[A-Za-z0-9_-]{32,})\b',
        "bearer_token": r'(?i)bearer\s+[A-Za-z0-9_\-.~+/]+=*',
        "password_field": r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{6,})["\']?',
        "aws_key": r'\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b',
        "aws_secret": r'(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
        "github_token": r'\b(?:gh[pousr]_[A-Za-z0-9_]{36,})\b',
        "private_key": r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
        "jwt": r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b',
    }

    # Common English words for language detection
    ENGLISH_COMMON_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'function', 'class', 'def', 'return', 'if', 'else', 'import', 'from', 'print',
        'code', 'file', 'create', 'write', 'read', 'help', 'how', 'can', 'please',
    }

    def __init__(
        self,
        min_tokens: int = None,
        max_tokens: int = None,
        required_fields: Set[str] = None,
        detect_pii: bool = True,
        detect_secrets: bool = True,
        auto_fix: bool = False,
        domain_keywords: Set[str] = None,
    ):
        """
        Initialize the validator.

        Args:
            min_tokens: Minimum token count (default: 50)
            max_tokens: Maximum token count (default: 4096)
            required_fields: Fields that must be present
            detect_pii: Whether to check for PII
            detect_secrets: Whether to check for secrets
            auto_fix: Whether to attempt automatic fixes
            domain_keywords: Keywords relevant to your domain for relevance scoring
        """
        self.min_tokens = min_tokens or self.MIN_TOKENS
        self.max_tokens = max_tokens or self.MAX_TOKENS
        self.required_fields = required_fields or self.REQUIRED_FIELDS
        self.detect_pii = detect_pii
        self.detect_secrets = detect_secrets
        self.auto_fix = auto_fix
        self.domain_keywords = domain_keywords or {
            'sam', 'code', 'python', 'function', 'file', 'project', 'help',
            'create', 'build', 'fix', 'error', 'debug', 'test', 'api'
        }

        # Compile patterns for efficiency
        self._pii_compiled = {k: re.compile(v, re.IGNORECASE) for k, v in self.PII_PATTERNS.items()}
        self._secret_compiled = {k: re.compile(v) for k, v in self.SECRET_PATTERNS.items()}

    def _normalize_fields(self, example: Dict) -> Dict:
        """
        Normalize field names to standard format (input/output).

        This allows the validator to work with different training data formats:
        - Standard: input/output
        - Chat: prompt/response
        - Personality: prompt/good_response
        - OpenAI: messages (list format)
        """
        normalized = dict(example)

        # Handle messages format (OpenAI style)
        if "messages" in example and isinstance(example["messages"], list):
            messages = example["messages"]
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                if role in ["user", "human"]:
                    normalized["input"] = content
                elif role in ["assistant", "ai", "bot"]:
                    normalized["output"] = content
                elif role in ["system"]:
                    normalized["instruction"] = content

        # Map aliases to standard field names
        for standard_field, aliases in self.FIELD_ALIASES.items():
            if standard_field not in normalized or not normalized.get(standard_field):
                for alias in aliases:
                    if alias in example and example[alias]:
                        normalized[standard_field] = example[alias]
                        break

        return normalized

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from character count."""
        return len(text) // self.CHARS_PER_TOKEN

    def _generate_id(self, example: Dict) -> str:
        """Generate a unique ID for an example."""
        content = json.dumps(example, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _check_length(self, text: str, field: str) -> List[QualityIssue]:
        """Check if text length is within bounds."""
        issues = []
        tokens = self._estimate_tokens(text)

        if tokens < self.min_tokens:
            issues.append(QualityIssue(
                issue_type=IssueType.TOO_SHORT,
                severity=IssueSeverity.ERROR,
                message=f"Content too short: ~{tokens} tokens (minimum: {self.min_tokens})",
                field=field
            ))
        elif tokens > self.max_tokens:
            issues.append(QualityIssue(
                issue_type=IssueType.TOO_LONG,
                severity=IssueSeverity.WARNING,
                message=f"Content too long: ~{tokens} tokens (maximum: {self.max_tokens})",
                field=field,
                suggested_fix=f"Truncate to {self.max_tokens * self.CHARS_PER_TOKEN} characters"
            ))

        return issues

    def _check_format(self, example: Dict) -> List[QualityIssue]:
        """Check if example has required fields and valid format."""
        issues = []

        # Check required fields
        for field in self.required_fields:
            if field not in example:
                issues.append(QualityIssue(
                    issue_type=IssueType.MISSING_FIELD,
                    severity=IssueSeverity.CRITICAL,
                    message=f"Missing required field: {field}",
                    field=field
                ))
            elif not example[field] or (isinstance(example[field], str) and not example[field].strip()):
                issues.append(QualityIssue(
                    issue_type=IssueType.EMPTY_CONTENT,
                    severity=IssueSeverity.CRITICAL,
                    message=f"Field is empty: {field}",
                    field=field
                ))

        # Check for encoding issues
        for field, value in example.items():
            if isinstance(value, str):
                try:
                    # Check for encoding issues by re-encoding
                    value.encode('utf-8').decode('utf-8')
                except UnicodeError:
                    issues.append(QualityIssue(
                        issue_type=IssueType.ENCODING_ERROR,
                        severity=IssueSeverity.ERROR,
                        message=f"Encoding error in field: {field}",
                        field=field,
                        suggested_fix="Re-encode as UTF-8"
                    ))

        return issues

    def _check_language(self, text: str, field: str) -> List[QualityIssue]:
        """Check if text appears to be primarily English."""
        issues = []

        # Normalize and tokenize
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        if not words:
            return issues

        # Calculate English word ratio
        english_count = sum(1 for w in words if w in self.ENGLISH_COMMON_WORDS)
        ratio = english_count / min(len(words), 100)  # Sample first 100 words

        if ratio < 0.05:  # Less than 5% common English words
            issues.append(QualityIssue(
                issue_type=IssueType.NON_ENGLISH,
                severity=IssueSeverity.WARNING,
                message=f"Content may not be English (common word ratio: {ratio:.2%})",
                field=field
            ))

        return issues

    def _check_coherence(self, text: str, field: str) -> Tuple[float, List[QualityIssue]]:
        """Check text coherence and return score + issues."""
        issues = []
        score = 1.0

        # Check for excessive repetition
        words = text.lower().split()
        if len(words) > 10:
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1

            max_repeat = max(word_counts.values()) if word_counts else 0
            repeat_ratio = max_repeat / len(words)

            if repeat_ratio > 0.3:  # Same word appears > 30% of text
                issues.append(QualityIssue(
                    issue_type=IssueType.REPETITIVE,
                    severity=IssueSeverity.WARNING,
                    message=f"Highly repetitive content (repetition ratio: {repeat_ratio:.2%})",
                    field=field
                ))
                score *= (1 - repeat_ratio)

        # Check for truncated content (ends mid-sentence)
        stripped = text.strip()
        if stripped and stripped[-1] not in '.!?":;)]\'"':
            # Could be truncated - check if it looks like a sentence ending
            if not stripped.endswith(('```', '---', '===', '***')):
                issues.append(QualityIssue(
                    issue_type=IssueType.TRUNCATED,
                    severity=IssueSeverity.WARNING,
                    message="Content may be truncated (doesn't end with punctuation)",
                    field=field
                ))
                score *= 0.9

        # Check sentence structure (very basic)
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 1:
            avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_len < 3:
                score *= 0.8  # Very short sentences
            elif avg_sentence_len > 50:
                score *= 0.9  # Very long sentences

        return score, issues

    def _check_pii(self, text: str, field: str) -> List[QualityIssue]:
        """Detect PII in text."""
        issues = []

        for pii_type, pattern in self._pii_compiled.items():
            matches = pattern.findall(text)
            if matches:
                # Get positions of first match
                match = pattern.search(text)
                pos = (match.start(), match.end()) if match else None

                issues.append(QualityIssue(
                    issue_type=IssueType.CONTAINS_PII,
                    severity=IssueSeverity.CRITICAL,
                    message=f"Contains {pii_type.replace('_', ' ')}: found {len(matches)} instance(s)",
                    field=field,
                    position=pos,
                    suggested_fix=f"Redact or remove {pii_type}"
                ))

        return issues

    def _check_secrets(self, text: str, field: str) -> List[QualityIssue]:
        """Detect secrets in text."""
        issues = []

        for secret_type, pattern in self._secret_compiled.items():
            matches = pattern.findall(text)
            if matches:
                match = pattern.search(text)
                pos = (match.start(), match.end()) if match else None

                issues.append(QualityIssue(
                    issue_type=IssueType.CONTAINS_SECRET,
                    severity=IssueSeverity.CRITICAL,
                    message=f"Contains potential {secret_type.replace('_', ' ')}",
                    field=field,
                    position=pos,
                    suggested_fix=f"Remove or redact {secret_type}"
                ))

        return issues

    def _calculate_quality_score(
        self,
        example: Dict,
        issues: List[QualityIssue]
    ) -> QualityScore:
        """Calculate quality scores across multiple dimensions."""

        # Combine all text fields
        all_text = ""
        for field in ['input', 'output', 'instruction', 'context']:
            if field in example and isinstance(example[field], str):
                all_text += example[field] + " "

        words = all_text.lower().split()
        unique_words = set(words)

        # Length score (bell curve around ideal length)
        tokens = self._estimate_tokens(all_text)
        ideal_tokens = (self.min_tokens + self.max_tokens) / 2
        length_score = max(0, 1 - abs(tokens - ideal_tokens) / ideal_tokens)

        # Specificity score (ratio of unique/specific words)
        if words:
            non_common = len([w for w in unique_words if w not in self.ENGLISH_COMMON_WORDS and len(w) > 3])
            specificity_score = min(1.0, non_common / (len(unique_words) + 1) * 2)
        else:
            specificity_score = 0.0

        # Diversity score (vocabulary richness)
        if words:
            diversity_score = min(1.0, len(unique_words) / (len(words) ** 0.5))
        else:
            diversity_score = 0.0

        # Difficulty score (based on technical indicators)
        difficulty_indicators = [
            'function', 'class', 'algorithm', 'optimize', 'implement',
            'debug', 'refactor', 'architecture', 'integrate', 'async'
        ]
        difficulty_count = sum(1 for w in words if w in difficulty_indicators)
        difficulty_score = min(1.0, difficulty_count / 3)

        # Relevance score (domain keyword matching)
        if self.domain_keywords and words:
            domain_matches = sum(1 for w in unique_words if w in self.domain_keywords)
            relevance_score = min(1.0, domain_matches / 3)
        else:
            relevance_score = 0.5  # Neutral if no domain keywords

        # Penalize for issues
        issue_penalty = 0
        for issue in issues:
            if issue.severity == IssueSeverity.CRITICAL:
                issue_penalty += 0.3
            elif issue.severity == IssueSeverity.ERROR:
                issue_penalty += 0.15
            elif issue.severity == IssueSeverity.WARNING:
                issue_penalty += 0.05

        # Overall score (weighted average with penalty)
        overall = (
            length_score * 0.15 +
            specificity_score * 0.25 +
            diversity_score * 0.15 +
            difficulty_score * 0.15 +
            relevance_score * 0.30
        ) * max(0, 1 - issue_penalty)

        return QualityScore(
            length_score=round(length_score, 3),
            specificity_score=round(specificity_score, 3),
            diversity_score=round(diversity_score, 3),
            difficulty_score=round(difficulty_score, 3),
            relevance_score=round(relevance_score, 3),
            overall_score=round(overall, 3)
        )

    def _auto_fix(self, example: Dict, issues: List[QualityIssue]) -> Optional[Dict]:
        """Attempt to automatically fix issues in the example."""
        if not issues:
            return None

        fixed = example.copy()
        changes_made = False

        for issue in issues:
            field = issue.field
            if not field or field not in fixed:
                continue

            content = fixed[field]
            if not isinstance(content, str):
                continue

            # Fix: Truncate long content
            if issue.issue_type == IssueType.TOO_LONG:
                max_chars = self.max_tokens * self.CHARS_PER_TOKEN
                if len(content) > max_chars:
                    # Try to truncate at sentence boundary
                    truncated = content[:max_chars]
                    last_period = truncated.rfind('.')
                    if last_period > max_chars * 0.8:
                        truncated = truncated[:last_period + 1]
                    fixed[field] = truncated
                    changes_made = True

            # Fix: Redact PII
            elif issue.issue_type == IssueType.CONTAINS_PII:
                for pii_type, pattern in self._pii_compiled.items():
                    fixed[field] = pattern.sub(f'[{pii_type.upper()}_REDACTED]', fixed[field])
                changes_made = True

            # Fix: Redact secrets
            elif issue.issue_type == IssueType.CONTAINS_SECRET:
                for secret_type, pattern in self._secret_compiled.items():
                    fixed[field] = pattern.sub(f'[{secret_type.upper()}_REDACTED]', fixed[field])
                changes_made = True

            # Fix: Normalize encoding
            elif issue.issue_type == IssueType.ENCODING_ERROR:
                try:
                    # Try to fix common encoding issues
                    fixed[field] = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore').decode('ascii')
                    changes_made = True
                except:
                    pass

            # Fix: Normalize whitespace
            if isinstance(fixed.get(field), str):
                normalized = re.sub(r'\s+', ' ', fixed[field]).strip()
                if normalized != fixed[field]:
                    fixed[field] = normalized
                    changes_made = True

        return fixed if changes_made else None

    def validate(self, example: Dict) -> Tuple[bool, List[QualityIssue]]:
        """
        Validate a single training example.

        Args:
            example: Dictionary with 'input', 'output', and optionally other fields
                     Supports alternative formats like prompt/response, messages, etc.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Normalize field names to standard format
        example = self._normalize_fields(example)

        # Format validation
        issues.extend(self._check_format(example))

        # If missing critical fields, can't continue
        if any(i.issue_type == IssueType.MISSING_FIELD for i in issues):
            return False, issues

        # Check each text field
        for field in ['input', 'output', 'instruction', 'context']:
            if field not in example:
                continue

            content = example[field]
            if not isinstance(content, str):
                continue

            # Length check
            if field in ['input', 'output']:  # Only check main fields
                issues.extend(self._check_length(content, field))

            # Language check
            if field in ['input', 'output']:
                issues.extend(self._check_language(content, field))

            # Coherence check
            _, coherence_issues = self._check_coherence(content, field)
            issues.extend(coherence_issues)

            # PII check
            if self.detect_pii:
                issues.extend(self._check_pii(content, field))

            # Secret check
            if self.detect_secrets:
                issues.extend(self._check_secrets(content, field))

        # Determine validity
        has_critical = any(i.severity == IssueSeverity.CRITICAL for i in issues)
        is_valid = not has_critical

        return is_valid, issues

    def validate_and_fix(self, example: Dict) -> ValidationResult:
        """
        Validate an example and optionally auto-fix issues.

        Args:
            example: Dictionary with training data

        Returns:
            ValidationResult with validation status and any fixes
        """
        example_id = self._generate_id(example)

        # Normalize fields for consistent processing
        normalized_example = self._normalize_fields(example)

        is_valid, issues = self.validate(example)

        # Calculate quality score on normalized example
        quality_score = self._calculate_quality_score(normalized_example, issues)

        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            quality_score=quality_score,
            example_id=example_id
        )

        # Attempt auto-fix if enabled and there are fixable issues
        if self.auto_fix and issues:
            fixed = self._auto_fix(example, issues)
            if fixed:
                # Re-validate fixed content
                is_valid_after, remaining_issues = self.validate(fixed)
                if is_valid_after or len(remaining_issues) < len(issues):
                    result.auto_fixed = True
                    result.fixed_content = fixed
                    result.is_valid = is_valid_after
                    result.issues = remaining_issues

        return result

    def validate_dataset(
        self,
        examples: List[Dict],
        progress_callback=None
    ) -> ValidationReport:
        """
        Validate an entire dataset of training examples.

        Args:
            examples: List of training examples
            progress_callback: Optional callback(current, total) for progress

        Returns:
            ValidationReport with comprehensive statistics
        """
        import time
        start_time = time.time()

        report = ValidationReport(total_examples=len(examples))

        all_scores = []

        for i, example in enumerate(examples):
            result = self.validate_and_fix(example)

            if result.is_valid:
                report.valid_examples += 1
            else:
                report.invalid_examples += 1

            if result.auto_fixed:
                report.auto_fixed_examples += 1

            # Count issues
            for issue in result.issues:
                issue_type = issue.issue_type.value
                severity = issue.severity.value

                report.issue_counts[issue_type] = report.issue_counts.get(issue_type, 0) + 1
                report.severity_counts[severity] = report.severity_counts.get(severity, 0) + 1

            # Track scores
            if result.quality_score:
                all_scores.append(result.quality_score.overall_score)

            # Progress callback
            if progress_callback and i % 100 == 0:
                progress_callback(i + 1, len(examples))

        # Calculate statistics
        if all_scores:
            report.average_quality_score = sum(all_scores) / len(all_scores)

            # Score distribution in buckets
            for score in all_scores:
                if score >= 0.8:
                    bucket = "excellent (0.8+)"
                elif score >= 0.6:
                    bucket = "good (0.6-0.8)"
                elif score >= 0.4:
                    bucket = "fair (0.4-0.6)"
                else:
                    bucket = "poor (<0.4)"
                report.score_distribution[bucket] = report.score_distribution.get(bucket, 0) + 1

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        report.validation_time = time.time() - start_time

        return report

    def _generate_recommendations(self, report: ValidationReport) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []

        if report.total_examples == 0:
            return ["No examples to validate"]

        invalid_ratio = report.invalid_examples / report.total_examples

        if invalid_ratio > 0.3:
            recommendations.append(
                f"High invalid rate ({invalid_ratio:.1%}). Review data collection process."
            )

        # Issue-specific recommendations
        if report.issue_counts.get('contains_pii', 0) > 0:
            recommendations.append(
                f"Found {report.issue_counts['contains_pii']} examples with PII. "
                "Run with auto_fix=True or manually redact before training."
            )

        if report.issue_counts.get('contains_secret', 0) > 0:
            recommendations.append(
                f"CRITICAL: Found {report.issue_counts['contains_secret']} examples with secrets. "
                "Remove these immediately before training."
            )

        if report.issue_counts.get('too_short', 0) > report.total_examples * 0.2:
            recommendations.append(
                "Many examples are too short. Consider combining related examples "
                "or lowering min_tokens threshold."
            )

        if report.issue_counts.get('too_long', 0) > report.total_examples * 0.2:
            recommendations.append(
                "Many examples are too long. Consider chunking or summarizing content."
            )

        if report.average_quality_score < 0.5:
            recommendations.append(
                f"Low average quality score ({report.average_quality_score:.2f}). "
                "Consider filtering examples below 0.4 score."
            )

        if not recommendations:
            recommendations.append(
                f"Dataset looks good! {report.valid_examples}/{report.total_examples} valid examples "
                f"with {report.average_quality_score:.2f} average quality score."
            )

        return recommendations


def validate_jsonl_file(
    filepath: Path,
    output_path: Optional[Path] = None,
    auto_fix: bool = False
) -> ValidationReport:
    """
    Validate a JSONL file of training examples.

    Args:
        filepath: Path to JSONL file
        output_path: Optional path to write fixed examples
        auto_fix: Whether to attempt fixes

    Returns:
        ValidationReport
    """
    examples = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    validator = DataQualityValidator(auto_fix=auto_fix)
    report = validator.validate_dataset(examples, progress_callback=lambda c, t: print(f"\r  Validating: {c}/{t}", end=''))
    print()  # New line after progress

    # Write fixed examples if requested
    if output_path and auto_fix:
        fixed_examples = []
        for example in examples:
            result = validator.validate_and_fix(example)
            if result.auto_fixed and result.fixed_content:
                fixed_examples.append(result.fixed_content)
            elif result.is_valid:
                fixed_examples.append(example)

        with open(output_path, 'w', encoding='utf-8') as f:
            for ex in fixed_examples:
                f.write(json.dumps(ex) + '\n')

        print(f"  Wrote {len(fixed_examples)} examples to {output_path}")

    return report


def process_training_data(
    input_path: Path,
    output_path: Path,
    validate: bool = True,
    deduplicate: bool = True,
    auto_fix: bool = True,
    min_quality_score: float = 0.3,
    jaccard_threshold: float = 0.8,
) -> Dict[str, Any]:
    """
    Complete training data processing pipeline: validate, fix, deduplicate.

    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file
        validate: Whether to run validation
        deduplicate: Whether to run deduplication
        auto_fix: Whether to auto-fix issues
        min_quality_score: Minimum quality score to keep
        jaccard_threshold: Similarity threshold for deduplication

    Returns:
        Dictionary with processing statistics
    """
    print(f"\nProcessing: {input_path}")

    # Load examples
    examples = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    print(f"  Loaded: {len(examples)} examples")

    stats = {
        "input_examples": len(examples),
        "validation_report": None,
        "deduplication_stats": None,
        "output_examples": 0,
    }

    processed = examples

    # Step 1: Validate and optionally fix/filter
    if validate:
        print("\n  Validating...")
        validator = DataQualityValidator(auto_fix=auto_fix, min_tokens=20)

        valid_examples = []
        for example in processed:
            result = validator.validate_and_fix(example)

            # Use fixed content if available
            ex_to_check = result.fixed_content if result.auto_fixed else example

            # Filter by quality score
            if result.quality_score and result.quality_score.overall_score >= min_quality_score:
                valid_examples.append(ex_to_check)
            elif result.is_valid:
                valid_examples.append(ex_to_check)

        stats["validation_report"] = {
            "before": len(processed),
            "after": len(valid_examples),
            "filtered": len(processed) - len(valid_examples),
        }
        print(f"    Valid: {len(valid_examples)}/{len(processed)} (filtered {len(processed) - len(valid_examples)})")
        processed = valid_examples

    # Step 2: Deduplicate
    if deduplicate and len(processed) > 0:
        print("\n  Deduplicating...")

        try:
            from deduplication import Deduplicator

            dedup = Deduplicator(
                jaccard_threshold=jaccard_threshold,
                use_semantic=False  # Semantic can be slow for large datasets
            )
            unique, dedup_stats = dedup.deduplicate(processed)

            stats["deduplication_stats"] = dedup_stats.to_dict()
            print(f"    Unique: {len(unique)}/{len(processed)} (removed {dedup_stats.duplicates_removed} duplicates)")
            processed = unique

        except ImportError:
            print("    Warning: deduplication module not available")

    # Step 3: Write output
    stats["output_examples"] = len(processed)

    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in processed:
            f.write(json.dumps(ex) + '\n')

    print(f"\n  Output: {len(processed)} examples -> {output_path}")

    return stats


if __name__ == "__main__":
    import sys

    print("SAM Data Quality Validator")
    print("-" * 40)

    if len(sys.argv) < 2:
        print("\nUsage: python data_quality.py <command> [args]")
        print("\nCommands:")
        print("  validate <file.jsonl>          - Validate training data file")
        print("  fix <file.jsonl> <output.jsonl> - Validate and fix, write clean file")
        print("  process <file.jsonl> <output.jsonl> - Full pipeline: validate, fix, dedupe")
        print("  check <text>                   - Check a single text for issues")
        print("  demo                           - Run demo with sample data")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "process" and len(sys.argv) > 3:
        input_path = Path(sys.argv[2])
        output_path = Path(sys.argv[3])

        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)

        stats = process_training_data(input_path, output_path)
        print(f"\nSummary:")
        print(f"  Input: {stats['input_examples']}")
        print(f"  Output: {stats['output_examples']}")
        print(f"  Reduction: {(1 - stats['output_examples']/stats['input_examples'])*100:.1f}%")

    elif cmd == "validate" and len(sys.argv) > 2:
        filepath = Path(sys.argv[2])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        print(f"\nValidating: {filepath}")
        report = validate_jsonl_file(filepath)

        print(f"\nResults:")
        print(f"  Total: {report.total_examples}")
        print(f"  Valid: {report.valid_examples}")
        print(f"  Invalid: {report.invalid_examples}")
        print(f"  Avg Quality: {report.average_quality_score:.2f}")
        print(f"\nIssue breakdown:")
        for issue, count in sorted(report.issue_counts.items()):
            print(f"  {issue}: {count}")
        print(f"\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")

    elif cmd == "fix" and len(sys.argv) > 3:
        filepath = Path(sys.argv[2])
        output_path = Path(sys.argv[3])

        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        print(f"\nValidating and fixing: {filepath}")
        report = validate_jsonl_file(filepath, output_path, auto_fix=True)

        print(f"\nResults:")
        print(f"  Total: {report.total_examples}")
        print(f"  Valid: {report.valid_examples}")
        print(f"  Auto-fixed: {report.auto_fixed_examples}")

    elif cmd == "check" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        validator = DataQualityValidator()

        example = {"input": "Please help with this:", "output": text}
        is_valid, issues = validator.validate(example)

        print(f"\nText: {text[:100]}...")
        print(f"Valid: {is_valid}")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  [{issue.severity.value}] {issue.issue_type.value}: {issue.message}")

    elif cmd == "demo":
        print("\nRunning demo validation...")

        # Sample training data with various issues
        samples = [
            # Good example
            {"input": "Write a Python function to sort a list", "output": "def sort_list(items):\n    return sorted(items)"},
            # Too short
            {"input": "Hi", "output": "Hello"},
            # Contains PII
            {"input": "My email is test@example.com, please help", "output": "I'll help you with your request."},
            # Contains secret
            {"input": "Use this API key: sk-1234567890abcdef1234567890abcdef12345678", "output": "I cannot use API keys."},
            # Missing field
            {"input": "Test input"},
            # Good technical example
            {
                "input": "How do I implement a binary search in Python?",
                "output": """def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# This implements binary search with O(log n) time complexity."""
            }
        ]

        validator = DataQualityValidator(auto_fix=True)
        report = validator.validate_dataset(samples)

        print(f"\nDemo Results:")
        print(f"  Samples: {report.total_examples}")
        print(f"  Valid: {report.valid_examples}")
        print(f"  Invalid: {report.invalid_examples}")
        print(f"  Auto-fixed: {report.auto_fixed_examples}")
        print(f"  Avg Quality: {report.average_quality_score:.2f}")

        print("\nScore Distribution:")
        for bucket, count in sorted(report.score_distribution.items()):
            print(f"  {bucket}: {count}")

        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")
