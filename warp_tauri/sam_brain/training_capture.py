#!/usr/bin/env python3
"""
Training Data Capture System - Phase 5.1.3 & 5.1.4

Captures training data from:
1. Claude conversation escalations (ConversationCapture)
2. User corrections and preferences (CorrectionCapture)

Integrates with:
- escalation_handler.py - Captures Claude responses
- feedback_system.py - Captures user corrections
- training_data.py - Stores in unified format

Usage:
    from training_capture import (
        ConversationCapture, CorrectionCapture,
        get_conversation_capture, get_correction_capture
    )

    # Capture Claude escalation
    capture = get_conversation_capture()
    example_id = capture.capture_escalation(
        query="How do I implement a binary tree?",
        sam_attempt="A binary tree is...",
        claude_response="Here's how to implement a binary tree:\n\n```python...",
        domain="code"
    )

    # Capture user correction
    correction_capture = get_correction_capture()
    example_id = correction_capture.capture_correction(
        original_query="What's the capital of France?",
        original_response="The capital of France is Lyon.",
        correction="The capital of France is Paris.",
        what_was_wrong="Incorrect city - Lyon is not the capital."
    )
"""

import json
import hashlib
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sqlite3


# Import local modules
try:
    from training_data import (
        TrainingExample, TrainingFormat, TrainingDataStore,
        DataSource, QualityTier, get_training_store
    )
except ImportError:
    # Will be imported when available
    TrainingExample = None
    TrainingDataStore = None
    get_training_store = None

try:
    from feedback_system import FeedbackDB, CorrectionAnalyzer
except ImportError:
    FeedbackDB = None
    CorrectionAnalyzer = None


# PII patterns for detection and removal
PII_PATTERNS = {
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'phone': r'(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'api_key': r'(?:api[_-]?key|token|secret)["\s:=]+["\']?[a-zA-Z0-9-_]{20,}["\']?',
    'password': r'(?:password|passwd|pwd)["\s:=]+["\']?[^\s"\']{4,}["\']?',
    'path_with_username': r'/(?:Users|home)/[a-zA-Z][a-zA-Z0-9_-]+/',
}

# Domain keywords for classification
DOMAIN_KEYWORDS = {
    'code': [
        'code', 'function', 'class', 'implement', 'bug', 'error', 'python',
        'javascript', 'typescript', 'rust', 'swift', 'sql', 'api', 'debug',
        'algorithm', 'data structure', 'compile', 'runtime', 'syntax'
    ],
    'reasoning': [
        'explain', 'why', 'how does', 'analyze', 'compare', 'evaluate',
        'what if', 'consider', 'think', 'reason', 'logic', 'argument'
    ],
    'creative': [
        'write', 'story', 'poem', 'creative', 'imagine', 'describe',
        'fiction', 'character', 'narrative', 'dialogue'
    ],
    'factual': [
        'what is', 'who is', 'when did', 'where is', 'define', 'fact',
        'history', 'science', 'geography', 'date', 'number'
    ],
    'planning': [
        'plan', 'schedule', 'organize', 'project', 'task', 'workflow',
        'steps', 'roadmap', 'strategy', 'milestone'
    ],
    'conversation': [
        'hello', 'hi', 'how are', 'thanks', 'goodbye', 'chat',
        'talk', 'feeling', 'opinion', 'think about'
    ],
}


class CaptureQuality(Enum):
    """Quality indicators for captured data."""
    HIGH = "high"           # Clear, complete, high-value
    MEDIUM = "medium"       # Usable but may need review
    LOW = "low"             # Likely needs filtering
    REJECTED = "rejected"   # Should not be used


@dataclass
class CaptureStats:
    """Statistics for capture operations."""
    total_captured: int = 0
    total_stored: int = 0
    total_rejected: int = 0
    pii_detections: int = 0
    duplicates_skipped: int = 0
    quality_scores: List[float] = field(default_factory=list)
    by_domain: Dict[str, int] = field(default_factory=dict)
    by_quality: Dict[str, int] = field(default_factory=dict)

    def average_quality(self) -> float:
        """Get average quality score."""
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)


class PIIDetector:
    """Detects and optionally removes PII from text."""

    def __init__(self, patterns: Optional[Dict[str, str]] = None):
        """Initialize with PII patterns."""
        self.patterns = patterns or PII_PATTERNS
        self._compiled = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }

    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text.

        Returns:
            List of detected PII with type, match, and position.
        """
        detections = []
        for pii_type, pattern in self._compiled.items():
            for match in pattern.finditer(text):
                detections.append({
                    'type': pii_type,
                    'match': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                })
        return detections

    def contains_pii(self, text: str) -> bool:
        """Check if text contains any PII."""
        for pattern in self._compiled.values():
            if pattern.search(text):
                return True
        return False

    def redact(self, text: str, replacement: str = '[REDACTED]') -> str:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            replacement: String to replace PII with

        Returns:
            Text with PII redacted
        """
        result = text
        for pii_type, pattern in self._compiled.items():
            result = pattern.sub(f'{replacement}_{pii_type.upper()}', result)
        return result

    def anonymize_path(self, text: str) -> str:
        """Anonymize file paths containing usernames."""
        # Replace /Users/username/ or /home/username/
        path_pattern = re.compile(r'(/(?:Users|home)/)[a-zA-Z][a-zA-Z0-9_-]+/')
        return path_pattern.sub(r'\1USER/', text)


class QualityEvaluator:
    """Evaluates quality of captured training data."""

    # Patterns indicating low quality
    LOW_QUALITY_PATTERNS = [
        r'^(?:ok|okay|sure|yes|no|thanks?)\.?$',  # Trivial responses
        r'^I (?:don\'t|cannot|can\'t) ',           # Refusals
        r'(?:I\'m not sure|I don\'t know)',        # Uncertainty
        r'\.{3,}$',                                 # Trailing ellipsis
        r'^(?:\s*\n){3,}',                          # Lots of blank lines
    ]

    # Patterns indicating high quality
    HIGH_QUALITY_PATTERNS = [
        r'```[\s\S]+```',          # Code blocks
        r'(?:1\.|a\)|\-|\*)\s+\w',  # Lists
        r'(?:First|Second|Third|Finally)',  # Step-by-step
        r'(?:For example|Here\'s how)',     # Examples
    ]

    def __init__(self):
        """Initialize evaluator."""
        self._low_quality_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.LOW_QUALITY_PATTERNS
        ]
        self._high_quality_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.HIGH_QUALITY_PATTERNS
        ]

    def evaluate(
        self,
        query: str,
        response: str,
        domain: str = 'general'
    ) -> Tuple[float, CaptureQuality, List[str]]:
        """
        Evaluate quality of a query-response pair.

        Returns:
            Tuple of (score, quality_tier, issues)
        """
        score = 0.5
        issues = []

        # === Length checks ===

        query_len = len(query.strip())
        response_len = len(response.strip())

        if query_len < 10:
            issues.append("query_too_short")
            score -= 0.15

        if response_len < 50:
            issues.append("response_too_short")
            score -= 0.2
        elif response_len > 200:
            score += 0.1
        elif response_len > 500:
            score += 0.15

        if response_len > 8000:
            issues.append("response_very_long")
            score -= 0.1  # May be rambling

        # === Low quality pattern checks ===

        for pattern in self._low_quality_compiled:
            if pattern.search(response):
                issues.append("low_quality_pattern")
                score -= 0.2
                break

        # === High quality pattern checks ===

        high_quality_count = 0
        for pattern in self._high_quality_compiled:
            if pattern.search(response):
                high_quality_count += 1

        if high_quality_count > 0:
            score += min(0.2, high_quality_count * 0.05)

        # === Domain-specific checks ===

        if domain == 'code':
            if '```' in response:
                score += 0.1
            if re.search(r'\bdef\b|\bfunction\b|\bclass\b', response):
                score += 0.05
            if re.search(r'error|traceback', response, re.IGNORECASE):
                score += 0.05  # Debugging help is valuable

        # === Repetition check ===

        if self._has_repetition(response):
            issues.append("repetitive")
            score -= 0.3

        # === Response completeness ===

        if response.strip().endswith(('...', '…', 'etc.', 'etc')):
            issues.append("incomplete")
            score -= 0.15

        # === Bound and classify ===

        score = max(0.0, min(1.0, score))

        if score >= 0.7:
            quality = CaptureQuality.HIGH
        elif score >= 0.4:
            quality = CaptureQuality.MEDIUM
        elif score >= 0.2:
            quality = CaptureQuality.LOW
        else:
            quality = CaptureQuality.REJECTED

        return score, quality, issues

    def _has_repetition(self, text: str, threshold: float = 0.4) -> bool:
        """Check for repetitive content."""
        if len(text) < 100:
            return False

        words = text.split()
        if len(words) < 10:
            return False

        # Count unique 3-grams
        ngrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        if not ngrams:
            return False

        unique_ratio = len(set(ngrams)) / len(ngrams)
        return unique_ratio < (1 - threshold)


class ConversationCapture:
    """
    Captures Claude conversation escalations as training data.

    Integrates with escalation_handler.py to capture high-quality
    Claude responses that SAM failed to handle.

    Usage:
        capture = ConversationCapture()

        # When Claude responds to an escalation
        example_id = capture.capture_escalation(
            query="How do I implement quicksort?",
            sam_attempt="I'm not sure about the implementation...",
            claude_response="Here's how to implement quicksort:\n\n```python..."
        )
    """

    def __init__(
        self,
        store: Optional[TrainingDataStore] = None,
        enable_pii_detection: bool = True,
        min_quality_score: float = 0.3,
        auto_batch_threshold: int = 100,
    ):
        """
        Initialize conversation capture.

        Args:
            store: TrainingDataStore instance (uses global if None)
            enable_pii_detection: Whether to check for and redact PII
            min_quality_score: Minimum quality to store
            auto_batch_threshold: Number of captures before auto-export
        """
        self.store = store or (get_training_store() if get_training_store else None)
        self.pii_detector = PIIDetector() if enable_pii_detection else None
        self.quality_evaluator = QualityEvaluator()
        self.min_quality_score = min_quality_score
        self.auto_batch_threshold = auto_batch_threshold

        # Stats tracking
        self.stats = CaptureStats()
        self._pending_batch: List[TrainingExample] = []

        # Recent capture hashes for deduplication
        self._recent_hashes: Set[str] = set()
        self._max_recent_hashes = 1000

    def capture_escalation(
        self,
        query: str,
        claude_response: str,
        sam_attempt: Optional[str] = None,
        domain: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Capture a Claude escalation as training data.

        Args:
            query: User's original query
            claude_response: Claude's response
            sam_attempt: SAM's failed attempt (if any)
            domain: Domain classification (auto-detected if None)
            escalation_reason: Why escalation happened
            conversation_context: Prior conversation turns
            metadata: Additional metadata

        Returns:
            Example ID if captured, None if rejected
        """
        self.stats.total_captured += 1

        # === PII Detection ===

        if self.pii_detector:
            if self.pii_detector.contains_pii(query):
                self.stats.pii_detections += 1
                query = self.pii_detector.redact(query)

            if self.pii_detector.contains_pii(claude_response):
                self.stats.pii_detections += 1
                claude_response = self.pii_detector.redact(claude_response)

            # Anonymize paths
            query = self.pii_detector.anonymize_path(query)
            claude_response = self.pii_detector.anonymize_path(claude_response)

            if sam_attempt:
                sam_attempt = self.pii_detector.anonymize_path(sam_attempt)
                if self.pii_detector.contains_pii(sam_attempt):
                    sam_attempt = self.pii_detector.redact(sam_attempt)

        # === Deduplication ===

        content_hash = self._compute_hash(query, claude_response)
        if content_hash in self._recent_hashes:
            self.stats.duplicates_skipped += 1
            return None

        self._recent_hashes.add(content_hash)
        if len(self._recent_hashes) > self._max_recent_hashes:
            # Remove oldest (arbitrary since sets don't have order, but limits size)
            self._recent_hashes.pop()

        # === Domain Classification ===

        if domain is None:
            domain = self._classify_domain(query, claude_response)

        # === Quality Evaluation ===

        score, quality, issues = self.quality_evaluator.evaluate(query, claude_response, domain)
        self.stats.quality_scores.append(score)

        if score < self.min_quality_score or quality == CaptureQuality.REJECTED:
            self.stats.total_rejected += 1
            self.stats.by_quality[quality.value] = self.stats.by_quality.get(quality.value, 0) + 1
            return None

        # === Create Training Example ===

        # Build system prompt
        system_prompt = self._build_system_prompt(domain)

        # Build metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'escalation_reason': escalation_reason,
            'capture_quality': quality.value,
            'quality_issues': issues,
            'has_sam_attempt': sam_attempt is not None,
        })

        if sam_attempt:
            # Create DPO example (Claude = chosen, SAM = rejected)
            example = TrainingExample(
                source=DataSource.CLAUDE_CAPTURE.value if DataSource else 'claude_capture',
                format=TrainingFormat.DPO.value if TrainingFormat else 'dpo',
                input_text=query,
                output_text=claude_response,
                rejected_output=sam_attempt,
                preference_reason=f"Claude provided better response. Escalation reason: {escalation_reason or 'unknown'}",
                system_prompt=system_prompt,
                conversation_history=conversation_context,
                domain=domain,
                complexity=self._estimate_complexity(query, claude_response),
                quality_tier=quality.value,
                quality_score=score,
                metadata=full_metadata,
            )
        else:
            # Create instruction/chat example
            example = TrainingExample(
                source=DataSource.CLAUDE_CAPTURE.value if DataSource else 'claude_capture',
                format=TrainingFormat.CHAT.value if TrainingFormat else 'chat',
                input_text=query,
                output_text=claude_response,
                system_prompt=system_prompt,
                conversation_history=conversation_context,
                domain=domain,
                complexity=self._estimate_complexity(query, claude_response),
                quality_tier=quality.value,
                quality_score=score,
                metadata=full_metadata,
            )

        # === Store ===

        example_id = None
        if self.store:
            example_id = self.store.add_example(example, skip_duplicate=True)
            if example_id:
                self.stats.total_stored += 1
                self.stats.by_domain[domain] = self.stats.by_domain.get(domain, 0) + 1
                self.stats.by_quality[quality.value] = self.stats.by_quality.get(quality.value, 0) + 1
        else:
            # Add to pending batch
            self._pending_batch.append(example)
            if len(self._pending_batch) >= self.auto_batch_threshold:
                self._flush_batch()
            example_id = example.id

        return example_id

    def _compute_hash(self, query: str, response: str) -> str:
        """Compute content hash for deduplication."""
        content = f"{query.strip().lower()}:{response[:500].strip().lower()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _classify_domain(self, query: str, response: str) -> str:
        """Auto-classify domain from content."""
        combined = f"{query} {response}".lower()

        domain_scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return 'general'

    def _build_system_prompt(self, domain: str) -> str:
        """Build appropriate system prompt for domain."""
        base = "You are SAM, a helpful AI assistant. "

        domain_prompts = {
            'code': "You excel at programming and software development. Provide clear, working code with explanations.",
            'reasoning': "You think step-by-step and explain your reasoning clearly.",
            'creative': "You are creative and engaging while being helpful.",
            'factual': "You provide accurate, well-sourced information.",
            'planning': "You help organize tasks and create actionable plans.",
            'conversation': "You are friendly, personable, and engaging.",
        }

        return base + domain_prompts.get(domain, "You provide clear, accurate, and helpful responses.")

    def _estimate_complexity(self, query: str, response: str) -> int:
        """Estimate task complexity 1-10."""
        score = 5  # Base

        # Query length
        if len(query) > 200:
            score += 1
        if len(query) > 500:
            score += 1

        # Response length
        if len(response) > 500:
            score += 1
        if len(response) > 1500:
            score += 1

        # Indicators of complexity
        complexity_indicators = [
            (r'implement|architecture|design', 2),
            (r'multiple|several|many', 1),
            (r'complex|complicated|difficult', 1),
            (r'optimize|performance', 1),
            (r'security|vulnerability', 2),
            (r'```[\s\S]+```.*```[\s\S]+```', 2),  # Multiple code blocks
        ]

        for pattern, delta in complexity_indicators:
            if re.search(pattern, query + response, re.IGNORECASE):
                score += delta

        return min(10, max(1, score))

    def _flush_batch(self):
        """Flush pending batch to storage."""
        if not self._pending_batch:
            return

        # Export to temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = Path("/Volumes/David External/sam_training/batches") / f"capture_batch_{timestamp}.jsonl"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with open(export_path, 'w') as f:
            for example in self._pending_batch:
                f.write(json.dumps(example.to_training_format()) + '\n')

        self._pending_batch = []

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics."""
        return {
            'total_captured': self.stats.total_captured,
            'total_stored': self.stats.total_stored,
            'total_rejected': self.stats.total_rejected,
            'pii_detections': self.stats.pii_detections,
            'duplicates_skipped': self.stats.duplicates_skipped,
            'average_quality': round(self.stats.average_quality(), 3),
            'by_domain': self.stats.by_domain,
            'by_quality': self.stats.by_quality,
            'pending_batch_size': len(self._pending_batch),
        }


class CorrectionCapture:
    """
    Captures user corrections and preferences as training data.

    Creates DPO (Direct Preference Optimization) pairs from:
    - User corrections (correct answer vs SAM's wrong answer)
    - User preferences (preferred response vs original)

    Integrates with feedback_system.py to process corrections.

    Usage:
        capture = CorrectionCapture()

        # Direct correction capture
        example_id = capture.capture_correction(
            original_query="What's 2+2?",
            original_response="2+2 equals 5.",
            correction="2+2 equals 4.",
            what_was_wrong="Math error"
        )

        # Process from feedback database
        processed = capture.process_feedback_corrections(limit=100)
    """

    def __init__(
        self,
        store: Optional[TrainingDataStore] = None,
        feedback_db: Optional[FeedbackDB] = None,
        enable_pii_detection: bool = True,
        min_quality_score: float = 0.3,
    ):
        """
        Initialize correction capture.

        Args:
            store: TrainingDataStore instance
            feedback_db: FeedbackDB instance for processing
            enable_pii_detection: Whether to check for PII
            min_quality_score: Minimum quality to store
        """
        self.store = store or (get_training_store() if get_training_store else None)
        self.feedback_db = feedback_db or (FeedbackDB() if FeedbackDB else None)
        self.correction_analyzer = CorrectionAnalyzer() if CorrectionAnalyzer else None
        self.pii_detector = PIIDetector() if enable_pii_detection else None
        self.quality_evaluator = QualityEvaluator()
        self.min_quality_score = min_quality_score

        # Stats
        self.stats = CaptureStats()

    def capture_correction(
        self,
        original_query: str,
        original_response: str,
        correction: str,
        what_was_wrong: Optional[str] = None,
        correction_type: Optional[str] = None,
        domain: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Capture a user correction as DPO training data.

        Args:
            original_query: The user's original question
            original_response: SAM's original (incorrect) response
            correction: The user's correction
            what_was_wrong: User's explanation of the error
            correction_type: Type of correction (full_replacement, partial_fix, etc.)
            domain: Domain classification
            metadata: Additional metadata

        Returns:
            Example ID if captured, None if rejected
        """
        self.stats.total_captured += 1

        # === PII Detection ===

        if self.pii_detector:
            for text_ref in [original_query, original_response, correction]:
                if self.pii_detector.contains_pii(text_ref):
                    self.stats.pii_detections += 1

            original_query = self.pii_detector.redact(original_query) if self.pii_detector.contains_pii(original_query) else original_query
            original_response = self.pii_detector.redact(original_response) if self.pii_detector.contains_pii(original_response) else original_response
            correction = self.pii_detector.redact(correction) if self.pii_detector.contains_pii(correction) else correction

            # Anonymize paths
            original_query = self.pii_detector.anonymize_path(original_query)
            original_response = self.pii_detector.anonymize_path(original_response)
            correction = self.pii_detector.anonymize_path(correction)

        # === Analyze Correction ===

        analysis = None
        error_types = []
        if self.correction_analyzer:
            try:
                analysis = self.correction_analyzer.analyze_correction(
                    original=original_response,
                    correction=correction,
                    query=original_query,
                    what_was_wrong=what_was_wrong,
                )
                error_types = analysis.error_types if hasattr(analysis, 'error_types') else []
            except Exception:
                pass

        # === Domain Classification ===

        if domain is None:
            combined = f"{original_query} {correction}".lower()
            domain_scores = {}
            for d, keywords in DOMAIN_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in combined)
                if score > 0:
                    domain_scores[d] = score
            domain = max(domain_scores, key=domain_scores.get) if domain_scores else 'general'

        # === Quality Evaluation ===

        # For corrections, evaluate the correction quality
        score, quality, issues = self.quality_evaluator.evaluate(original_query, correction, domain)

        # Boost score for corrections with explanation
        if what_was_wrong and len(what_was_wrong) > 20:
            score = min(1.0, score + 0.1)

        # Boost for analyzed corrections
        if analysis and error_types:
            score = min(1.0, score + 0.05)

        self.stats.quality_scores.append(score)

        if score < self.min_quality_score or quality == CaptureQuality.REJECTED:
            self.stats.total_rejected += 1
            return None

        # === Create DPO Example ===

        full_metadata = metadata or {}
        full_metadata.update({
            'correction_type': correction_type,
            'what_was_wrong': what_was_wrong,
            'error_types': error_types,
            'capture_quality': quality.value,
            'quality_issues': issues,
        })

        # Build preference reason
        preference_reason = what_was_wrong or "User-provided correction"
        if error_types:
            preference_reason += f" (Error types: {', '.join(error_types)})"

        example = TrainingExample(
            source=DataSource.USER_CORRECTION.value if DataSource else 'user_correction',
            format=TrainingFormat.DPO.value if TrainingFormat else 'dpo',
            input_text=original_query,
            output_text=correction,
            rejected_output=original_response,
            preference_reason=preference_reason,
            system_prompt="You are SAM, a helpful AI assistant. Provide accurate and helpful responses.",
            domain=domain,
            quality_tier=quality.value,
            quality_score=score,
            metadata=full_metadata,
        )

        # === Store ===

        example_id = None
        if self.store:
            example_id = self.store.add_example(example, skip_duplicate=True)
            if example_id:
                self.stats.total_stored += 1
                self.stats.by_domain[domain] = self.stats.by_domain.get(domain, 0) + 1
        else:
            example_id = example.id

        return example_id

    def capture_preference(
        self,
        original_query: str,
        original_response: str,
        preferred_response: str,
        comparison_basis: Optional[str] = None,
        domain: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Capture a user preference as DPO training data.

        Args:
            original_query: The user's question
            original_response: SAM's original response
            preferred_response: User's preferred alternative
            comparison_basis: Why the preferred is better
            domain: Domain classification
            metadata: Additional metadata

        Returns:
            Example ID if captured, None if rejected
        """
        self.stats.total_captured += 1

        # === PII Detection ===

        if self.pii_detector:
            original_query = self.pii_detector.redact(original_query) if self.pii_detector.contains_pii(original_query) else original_query
            original_response = self.pii_detector.redact(original_response) if self.pii_detector.contains_pii(original_response) else original_response
            preferred_response = self.pii_detector.redact(preferred_response) if self.pii_detector.contains_pii(preferred_response) else preferred_response

        # === Domain Classification ===

        if domain is None:
            combined = f"{original_query} {preferred_response}".lower()
            domain_scores = {}
            for d, keywords in DOMAIN_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in combined)
                if score > 0:
                    domain_scores[d] = score
            domain = max(domain_scores, key=domain_scores.get) if domain_scores else 'general'

        # === Quality Evaluation ===

        score, quality, issues = self.quality_evaluator.evaluate(original_query, preferred_response, domain)
        self.stats.quality_scores.append(score)

        if score < self.min_quality_score or quality == CaptureQuality.REJECTED:
            self.stats.total_rejected += 1
            return None

        # === Create DPO Example ===

        full_metadata = metadata or {}
        full_metadata.update({
            'comparison_basis': comparison_basis,
            'capture_quality': quality.value,
            'quality_issues': issues,
        })

        example = TrainingExample(
            source=DataSource.USER_PREFERENCE.value if DataSource else 'user_preference',
            format=TrainingFormat.DPO.value if TrainingFormat else 'dpo',
            input_text=original_query,
            output_text=preferred_response,
            rejected_output=original_response,
            preference_reason=comparison_basis or "User-preferred response",
            system_prompt="You are SAM, a helpful AI assistant.",
            domain=domain,
            quality_tier=quality.value,
            quality_score=score,
            metadata=full_metadata,
        )

        # === Store ===

        example_id = None
        if self.store:
            example_id = self.store.add_example(example, skip_duplicate=True)
            if example_id:
                self.stats.total_stored += 1
                self.stats.by_domain[domain] = self.stats.by_domain.get(domain, 0) + 1

        return example_id

    def process_feedback_corrections(
        self,
        limit: int = 100,
        mark_processed: bool = True,
    ) -> Dict[str, int]:
        """
        Process corrections from FeedbackDB and convert to training data.

        Args:
            limit: Maximum number to process
            mark_processed: Whether to mark feedback as processed

        Returns:
            Statistics on processing
        """
        if not self.feedback_db:
            return {'error': 'FeedbackDB not available'}

        # Get unprocessed corrections
        corrections = self.feedback_db.get_recent_feedback(
            limit=limit,
            feedback_type='correction',
            include_processed=False,
        )

        stats = {
            'total': len(corrections),
            'captured': 0,
            'rejected': 0,
            'errors': 0,
        }

        for fb in corrections:
            try:
                example_id = self.capture_correction(
                    original_query=fb.get('original_query', ''),
                    original_response=fb.get('original_response', ''),
                    correction=fb.get('correction', ''),
                    what_was_wrong=fb.get('what_was_wrong'),
                    correction_type=fb.get('correction_type'),
                    domain=fb.get('domain'),
                    metadata={
                        'feedback_id': fb.get('feedback_id'),
                        'session_id': fb.get('session_id'),
                    }
                )

                if example_id:
                    stats['captured'] += 1
                    if mark_processed:
                        self.feedback_db.mark_as_processed(
                            fb['feedback_id'],
                            training_format='dpo_correction'
                        )
                else:
                    stats['rejected'] += 1

            except Exception as e:
                stats['errors'] += 1
                continue

        return stats

    def process_feedback_preferences(
        self,
        limit: int = 100,
        mark_processed: bool = True,
    ) -> Dict[str, int]:
        """
        Process preferences from FeedbackDB and convert to training data.

        Args:
            limit: Maximum number to process
            mark_processed: Whether to mark feedback as processed

        Returns:
            Statistics on processing
        """
        if not self.feedback_db:
            return {'error': 'FeedbackDB not available'}

        # Get unprocessed preferences
        preferences = self.feedback_db.get_recent_feedback(
            limit=limit,
            feedback_type='preference',
            include_processed=False,
        )

        stats = {
            'total': len(preferences),
            'captured': 0,
            'rejected': 0,
            'errors': 0,
        }

        for fb in preferences:
            try:
                example_id = self.capture_preference(
                    original_query=fb.get('original_query', ''),
                    original_response=fb.get('original_response', ''),
                    preferred_response=fb.get('preferred_response', ''),
                    comparison_basis=fb.get('comparison_basis'),
                    domain=fb.get('domain'),
                    metadata={
                        'feedback_id': fb.get('feedback_id'),
                        'session_id': fb.get('session_id'),
                    }
                )

                if example_id:
                    stats['captured'] += 1
                    if mark_processed:
                        self.feedback_db.mark_as_processed(
                            fb['feedback_id'],
                            training_format='dpo_preference'
                        )
                else:
                    stats['rejected'] += 1

            except Exception as e:
                stats['errors'] += 1
                continue

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics."""
        return {
            'total_captured': self.stats.total_captured,
            'total_stored': self.stats.total_stored,
            'total_rejected': self.stats.total_rejected,
            'pii_detections': self.stats.pii_detections,
            'average_quality': round(self.stats.average_quality(), 3),
            'by_domain': self.stats.by_domain,
        }


# === Global Instances ===

_conversation_capture: Optional[ConversationCapture] = None
_correction_capture: Optional[CorrectionCapture] = None


def get_conversation_capture() -> ConversationCapture:
    """Get or create the global conversation capture instance."""
    global _conversation_capture
    if _conversation_capture is None:
        _conversation_capture = ConversationCapture()
    return _conversation_capture


def get_correction_capture() -> CorrectionCapture:
    """Get or create the global correction capture instance."""
    global _correction_capture
    if _correction_capture is None:
        _correction_capture = CorrectionCapture()
    return _correction_capture


# === Integration Hooks ===

def capture_from_escalation_handler(
    query: str,
    sam_response: Optional[str],
    claude_response: str,
    escalation_reason: str = "unknown",
    domain: str = "general",
) -> Optional[str]:
    """
    Hook for escalation_handler.py to capture training data.

    Call this after a successful Claude escalation.

    Args:
        query: Original user query
        sam_response: SAM's failed attempt (if any)
        claude_response: Claude's successful response
        escalation_reason: Why escalation was needed
        domain: Domain classification

    Returns:
        Example ID if captured
    """
    capture = get_conversation_capture()
    return capture.capture_escalation(
        query=query,
        sam_attempt=sam_response,
        claude_response=claude_response,
        escalation_reason=escalation_reason,
        domain=domain,
    )


def capture_from_feedback(
    feedback_entry: Dict[str, Any]
) -> Optional[str]:
    """
    Hook for feedback_system.py to capture training data.

    Call this when new correction/preference feedback is received.

    Args:
        feedback_entry: Feedback entry dictionary

    Returns:
        Example ID if captured
    """
    capture = get_correction_capture()
    feedback_type = feedback_entry.get('feedback_type')

    if feedback_type == 'correction':
        return capture.capture_correction(
            original_query=feedback_entry.get('original_query', ''),
            original_response=feedback_entry.get('original_response', ''),
            correction=feedback_entry.get('correction', ''),
            what_was_wrong=feedback_entry.get('what_was_wrong'),
            correction_type=feedback_entry.get('correction_type'),
            domain=feedback_entry.get('domain'),
        )

    elif feedback_type == 'preference':
        return capture.capture_preference(
            original_query=feedback_entry.get('original_query', ''),
            original_response=feedback_entry.get('original_response', ''),
            preferred_response=feedback_entry.get('preferred_response', ''),
            comparison_basis=feedback_entry.get('comparison_basis'),
            domain=feedback_entry.get('domain'),
        )

    return None


# === CLI ===

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Data Capture")
    parser.add_argument('command', choices=['stats', 'process-corrections', 'process-preferences', 'test'],
                       help="Command to run")
    parser.add_argument('--limit', type=int, default=100, help="Limit for processing")
    parser.add_argument('--dry-run', action='store_true', help="Don't mark as processed")

    args = parser.parse_args()

    if args.command == 'stats':
        print("\n=== Conversation Capture Stats ===")
        conv_capture = get_conversation_capture()
        stats = conv_capture.get_stats()
        print(json.dumps(stats, indent=2))

        print("\n=== Correction Capture Stats ===")
        corr_capture = get_correction_capture()
        stats = corr_capture.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == 'process-corrections':
        capture = get_correction_capture()
        result = capture.process_feedback_corrections(
            limit=args.limit,
            mark_processed=not args.dry_run,
        )
        print(f"Processed corrections: {json.dumps(result, indent=2)}")

    elif args.command == 'process-preferences':
        capture = get_correction_capture()
        result = capture.process_feedback_preferences(
            limit=args.limit,
            mark_processed=not args.dry_run,
        )
        print(f"Processed preferences: {json.dumps(result, indent=2)}")

    elif args.command == 'test':
        print("Testing capture system...")

        # Test conversation capture
        conv = get_conversation_capture()
        example_id = conv.capture_escalation(
            query="How do I implement a binary search tree in Python?",
            sam_attempt="I'm not sure how to implement that...",
            claude_response="""Here's how to implement a binary search tree in Python:

```python
class TreeNode:
    def __init__(self, val=0):
        self.val = val
        self.left = None
        self.right = None

class BST:
    def __init__(self):
        self.root = None

    def insert(self, val):
        if not self.root:
            self.root = TreeNode(val)
        else:
            self._insert(self.root, val)

    def _insert(self, node, val):
        if val < node.val:
            if node.left:
                self._insert(node.left, val)
            else:
                node.left = TreeNode(val)
        else:
            if node.right:
                self._insert(node.right, val)
            else:
                node.right = TreeNode(val)
```

This implementation includes:
1. A TreeNode class for individual nodes
2. A BST class with insert functionality
3. Recursive insertion based on value comparison
""",
            domain="code",
            escalation_reason="complexity",
        )
        print(f"Captured escalation: {example_id}")

        # Test correction capture
        corr = get_correction_capture()
        example_id = corr.capture_correction(
            original_query="What is the capital of Australia?",
            original_response="The capital of Australia is Sydney.",
            correction="The capital of Australia is Canberra.",
            what_was_wrong="Incorrect - Sydney is not the capital, Canberra is.",
        )
        print(f"Captured correction: {example_id}")

        print("\nConversation stats:", conv.get_stats())
        print("Correction stats:", corr.get_stats())


if __name__ == "__main__":
    main()
