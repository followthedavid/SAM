#!/usr/bin/env python3
"""
Knowledge Distillation Engine

Captures Claude's reasoning patterns and distills them into training data
for SAM. Since we can't have trillions of tokens, we extract:

1. Chain-of-Thought patterns - How Claude breaks down problems
2. Principle extraction - Core rules Claude follows
3. Preference pairs - Good vs bad response examples
4. Skill templates - Reusable reasoning patterns
5. Error correction pairs - Wrong answer → corrected answer

This turns Claude interactions into high-value training data.

Usage:
    # During normal Claude usage, this runs automatically:
    python knowledge_distillation.py listen

    # Generate synthetic training data:
    python knowledge_distillation.py generate --domain code --count 100

    # Extract principles from Claude responses:
    python knowledge_distillation.py extract-principles

    # Export for training:
    python knowledge_distillation.py export --output training_distilled.jsonl
"""

import json
import sqlite3
import re
import hashlib
import time
import subprocess
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Storage - External drive is primary, with fallback to local
EXTERNAL_DB_PATH = Path("/Volumes/David External/sam_training/distilled/distillation.db")
LOCAL_DB_PATH = Path.home() / ".sam" / "knowledge_distillation.db"
EXPORT_PATH = Path("/Volumes/David External/sam_training/distilled/exports")
PENDING_REVIEW_PATH = Path("/Volumes/David External/sam_training/distilled/pending_review")
APPROVED_PATH = Path("/Volumes/David External/sam_training/distilled/approved")

# For backwards compatibility
DB_PATH = LOCAL_DB_PATH


def get_db_path() -> Path:
    """Get the appropriate database path, preferring external drive."""
    if EXTERNAL_DB_PATH.parent.exists():
        return EXTERNAL_DB_PATH
    else:
        print(f"Warning: External drive not mounted. Using local path: {LOCAL_DB_PATH}")
        return LOCAL_DB_PATH


def is_external_drive_mounted() -> bool:
    """Check if the external drive is mounted."""
    return Path("/Volumes/David External").exists()


class DistillationType(Enum):
    CHAIN_OF_THOUGHT = "cot"           # Step-by-step reasoning
    PRINCIPLE = "principle"            # Core rules/guidelines
    PREFERENCE_PAIR = "preference"     # Good vs bad examples
    SKILL_TEMPLATE = "skill"           # Reusable patterns
    ERROR_CORRECTION = "correction"    # Mistake → fix pairs
    SYNTHETIC = "synthetic"            # Generated examples


class ReasoningType(Enum):
    """Types of reasoning patterns as defined in DISTILLATION_FORMAT.md"""
    CHAIN_OF_THOUGHT = "chain_of_thought"   # Step-by-step breakdown
    TOOL_USE = "tool_use"                   # Using tools/functions
    CORRECTION = "correction"               # Fixing SAM's error
    DIRECT = "direct"                       # Straightforward answer
    MULTI_STEP = "multi_step"               # Multiple sub-tasks
    META_COGNITIVE = "meta_cognitive"       # Self-reflection, uncertainty


@dataclass
class ChainOfThought:
    """A captured reasoning chain"""
    id: str
    prompt: str
    reasoning_steps: List[str]
    final_answer: str
    domain: str
    complexity: int  # 1-10
    success: bool


@dataclass
class Principle:
    """An extracted principle/rule"""
    id: str
    domain: str
    principle: str
    examples: List[str]
    importance: float  # 0-1
    source_count: int  # How many times observed


@dataclass
class PreferencePair:
    """Good vs bad response pair for preference learning"""
    id: str
    prompt: str
    good_response: str
    bad_response: str
    reason: str  # Why good is better
    domain: str


@dataclass
class SkillTemplate:
    """A reusable reasoning pattern"""
    id: str
    name: str
    description: str
    pattern: str  # Template with {placeholders}
    examples: List[Dict]  # Filled-in examples
    domains: List[str]


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain"""
    step_num: int
    action: str           # identify, analyze, solve, verify, etc.
    content: str          # What was done in this step
    reasoning: str        # Why this step was taken


@dataclass
class ToolUsage:
    """Record of a tool being used"""
    tool: str             # Tool/function name
    purpose: str          # Why it was used
    input_pattern: str    # What input was provided
    output_handling: str  # How output was processed


@dataclass
class SamError:
    """A specific error SAM made"""
    error_type: str       # incomplete, incorrect, missing_context, etc.
    what_sam_said: str    # SAM's incorrect/incomplete response
    what_was_wrong: str   # Why it was wrong
    correct_answer: str   # What should have been said


@dataclass
class Corrections:
    """Collection of corrections Claude made to SAM's response"""
    sam_errors: List[SamError]
    improvements: List[str]


@dataclass
class ExtractedPrinciple:
    """A principle extracted from the response"""
    principle: str
    context: str
    importance: float


@dataclass
class ReasoningPattern:
    """Complete reasoning pattern extracted from a Claude response.

    This is the primary output of the ReasoningPatternExtractor and matches
    the structure defined in DISTILLATION_FORMAT.md.
    """
    reasoning_type: ReasoningType
    reasoning_steps: List[ReasoningStep]
    tool_usage: List[ToolUsage]
    corrections: Optional[Corrections]
    principles: List[ExtractedPrinciple]
    complexity: int  # 1-10
    confidence: float  # How confident we are in this extraction


@dataclass
class FilterResult:
    """Result of quality filtering an example."""
    accepted: bool
    quality_score: float
    rejection_reason: Optional[str]
    quality_flags: List[str]


class QualityFilter:
    """
    Quality filter for knowledge distillation examples.

    Implements the quality scoring algorithm from DISTILLATION_FORMAT.md.
    Target: reject >20% of low-value captures while keeping high-quality ones.

    Scoring (0.0-1.0):
        Base score: 0.5

        Positive factors (max +0.4):
        - Reasoning chains with 2+ steps: +0.1
        - Explicit corrections of SAM errors: +0.15
        - Extracted principles: +0.1
        - Task complexity >= 5: +0.05

        Negative factors (max -0.5):
        - Response too short (<100 chars): -0.2
        - Direct answers (no reasoning): -0.1
        - Repetitive content: -0.3
        - Incomplete response: -0.2

    Auto-rejection criteria:
        - quality_score < 0.3
        - Response too short (<50 chars)
        - High repetition ratio (>40%)
        - Obvious error patterns
    """

    # Quality flags as defined in DISTILLATION_FORMAT.md
    QUALITY_FLAGS = [
        'repetition',        # Response has repetitive patterns
        'incomplete',        # Answer seems cut off
        'no_reasoning',      # No chain-of-thought present
        'too_short',         # Less than 50 tokens
        'too_long',          # Over 4000 tokens (may be rambling)
        'code_only',         # Just code, no explanation
        'refusal',           # Claude refused to answer
        'uncertain',         # Claude expressed uncertainty
        'outdated',          # Information may be stale
        'hallucination_risk' # Facts that should be verified
    ]

    # Patterns indicating incomplete responses
    INCOMPLETE_PATTERNS = [
        r"(?:I (?:can't|cannot|won't|will not) (?:complete|finish|continue))",
        r"(?:\.{3,}|…)$",  # Ends with ellipsis
        r"(?:etc\.?|and so on|and more)$",  # Vague endings
        r"(?:To be continued|TBC|WIP)",
        r"(?:I'll (?:stop|pause|leave it) here)",
    ]

    # Patterns indicating refusal
    REFUSAL_PATTERNS = [
        r"(?:I (?:can't|cannot|won't|will not|am unable to))",
        r"(?:I'm (?:not able|unable) to)",
        r"(?:I don't (?:have access|think I should))",
        r"(?:This (?:is|would be) (?:inappropriate|harmful|dangerous))",
        r"(?:I (?:must|have to) (?:decline|refuse))",
    ]

    # Patterns indicating high uncertainty (meta-cognitive but low confidence)
    HIGH_UNCERTAINTY_PATTERNS = [
        r"(?:I'm (?:very|really|quite) (?:uncertain|unsure))",
        r"(?:I (?:don't|do not) (?:really )?know)",
        r"(?:(?:pure|wild) speculation)",
        r"(?:I'm just guessing)",
        r"(?:(?:no|zero) confidence)",
    ]

    def __init__(self, min_quality_threshold: float = 0.3,
                 min_response_length: int = 50,
                 max_repetition_ratio: float = 0.4):
        """
        Initialize the quality filter.

        Args:
            min_quality_threshold: Minimum quality score to accept (default 0.3)
            min_response_length: Minimum response character length (default 50)
            max_repetition_ratio: Maximum ratio of repeated content (default 0.4)
        """
        self.min_quality_threshold = min_quality_threshold
        self.min_response_length = min_response_length
        self.max_repetition_ratio = max_repetition_ratio

        # Statistics tracking
        self._stats = {
            'total_processed': 0,
            'total_accepted': 0,
            'total_rejected': 0,
            'rejection_reasons': {},
            'average_quality_score': 0.0,
            'quality_score_sum': 0.0,
        }

    def filter(
        self,
        query: str,
        response: str,
        pattern: Optional['ReasoningPattern'] = None,
        sam_attempt: Optional[str] = None
    ) -> FilterResult:
        """
        Filter a single example for quality.

        Args:
            query: The original user query
            response: Claude's response
            pattern: Optional ReasoningPattern if already extracted
            sam_attempt: SAM's initial attempt (if any)

        Returns:
            FilterResult with acceptance status, score, and flags
        """
        self._stats['total_processed'] += 1

        quality_flags = []
        rejection_reason = None

        # ===== HARD REJECTION CHECKS (before scoring) =====

        # Check minimum response length
        if len(response) < self.min_response_length:
            quality_flags.append('too_short')
            rejection_reason = f"Response too short ({len(response)} chars < {self.min_response_length})"
            self._record_rejection(rejection_reason)
            return FilterResult(
                accepted=False,
                quality_score=0.1,
                rejection_reason=rejection_reason,
                quality_flags=quality_flags
            )

        # Check repetition ratio
        repetition_ratio = self._calculate_repetition_ratio(response)
        if repetition_ratio > self.max_repetition_ratio:
            quality_flags.append('repetition')
            rejection_reason = f"High repetition ratio ({repetition_ratio:.1%} > {self.max_repetition_ratio:.0%})"
            self._record_rejection(rejection_reason)
            return FilterResult(
                accepted=False,
                quality_score=0.15,
                rejection_reason=rejection_reason,
                quality_flags=quality_flags
            )

        # Check for refusal patterns
        if self._contains_refusal(response):
            quality_flags.append('refusal')
            rejection_reason = "Response contains refusal pattern"
            self._record_rejection(rejection_reason)
            return FilterResult(
                accepted=False,
                quality_score=0.1,
                rejection_reason=rejection_reason,
                quality_flags=quality_flags
            )

        # ===== QUALITY SCORING =====

        score = 0.5  # Base score

        # --- Positive factors (max +0.4) ---

        # Reasoning chains with 2+ steps: +0.1
        if pattern and len(pattern.reasoning_steps) >= 2:
            score += 0.1
        elif self._has_reasoning_markers(response):
            score += 0.05  # Partial credit for reasoning markers without extraction

        # Explicit corrections of SAM errors: +0.15 (most valuable)
        if pattern and pattern.corrections and pattern.corrections.sam_errors:
            score += 0.15
        elif sam_attempt and self._has_correction_markers(response):
            score += 0.1  # Partial credit

        # Extracted principles: +0.1
        if pattern and len(pattern.principles) >= 1:
            score += 0.1
        elif self._has_principle_markers(response):
            score += 0.05  # Partial credit

        # Task complexity >= 5: +0.05
        if pattern and pattern.complexity >= 5:
            score += 0.05
        elif len(response.split()) > 200:  # Proxy for complexity
            score += 0.03

        # --- Negative factors (max -0.5) ---

        # Response length penalties
        if len(response) < 100:
            score -= 0.2
            quality_flags.append('too_short')
        elif len(response) > 8000:
            score -= 0.1  # May be rambling
            quality_flags.append('too_long')

        # Direct answers (no reasoning): -0.1
        # But don't penalize corrections - correction content is inherently valuable
        has_correction = (pattern and pattern.corrections and pattern.corrections.sam_errors) or \
                        (sam_attempt and self._has_correction_markers(response))

        if not has_correction:  # Only penalize non-correction responses
            if pattern and pattern.reasoning_type == ReasoningType.DIRECT:
                score -= 0.1
                quality_flags.append('no_reasoning')
            elif not self._has_any_reasoning(response):
                score -= 0.1
                quality_flags.append('no_reasoning')

        # Repetitive content: partial penalty (already checked for hard rejection)
        if repetition_ratio > 0.2:
            score -= 0.15
            if 'repetition' not in quality_flags:
                quality_flags.append('repetition')

        # Incomplete response: -0.2
        if self._is_incomplete(response):
            score -= 0.2
            quality_flags.append('incomplete')

        # Code-only response (no explanation): -0.1
        if self._is_code_only(response):
            score -= 0.1
            quality_flags.append('code_only')

        # High uncertainty: -0.1
        if self._has_high_uncertainty(response):
            score -= 0.1
            quality_flags.append('uncertain')

        # Clamp score to valid range
        score = max(0.0, min(1.0, score))

        # ===== FINAL ACCEPTANCE DECISION =====

        if score < self.min_quality_threshold:
            rejection_reason = f"Quality score too low ({score:.2f} < {self.min_quality_threshold})"
            self._record_rejection(rejection_reason)
            return FilterResult(
                accepted=False,
                quality_score=score,
                rejection_reason=rejection_reason,
                quality_flags=quality_flags
            )

        # Accepted
        self._stats['total_accepted'] += 1
        self._stats['quality_score_sum'] += score
        self._update_average_score()

        return FilterResult(
            accepted=True,
            quality_score=score,
            rejection_reason=None,
            quality_flags=quality_flags
        )

    def _calculate_repetition_ratio(self, text: str) -> float:
        """
        Calculate the ratio of repeated content in text.

        Uses n-gram analysis to detect repetitive patterns.
        """
        words = text.lower().split()
        if len(words) < 10:
            return 0.0

        # Check for repeated 3-grams
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words) - 2)]
        if not trigrams:
            return 0.0

        unique_trigrams = set(trigrams)
        repetition_ratio = 1.0 - (len(unique_trigrams) / len(trigrams))

        # Also check for repeated lines
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) > 3:
            unique_lines = set(lines)
            line_repetition = 1.0 - (len(unique_lines) / len(lines))
            repetition_ratio = max(repetition_ratio, line_repetition * 0.8)

        # Check for repeated sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 20]
        if len(sentences) > 3:
            unique_sentences = set(sentences)
            sentence_repetition = 1.0 - (len(unique_sentences) / len(sentences))
            repetition_ratio = max(repetition_ratio, sentence_repetition)

        return repetition_ratio

    def _contains_refusal(self, text: str) -> bool:
        """Check if response contains refusal patterns."""
        for pattern in self.REFUSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Make sure it's a significant refusal, not just mentioning inability
                # in context (e.g., "I can't find any errors" is fine)
                if re.search(r"(?:I (?:can't|cannot|won't) (?:help|assist|provide|do|answer))", text, re.IGNORECASE):
                    return True
        return False

    def _is_incomplete(self, text: str) -> bool:
        """Check if response appears incomplete."""
        for pattern in self.INCOMPLETE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check for abrupt endings (text ending mid-word or mid-sentence)
        stripped = text.rstrip()
        if stripped and stripped[-1] not in '.!?"\'):;':
            # Allow code blocks to end without punctuation
            if not stripped.endswith('```') and not stripped.endswith('`'):
                # Check if it looks like an incomplete sentence
                last_line = stripped.split('\n')[-1].strip()
                if len(last_line) > 10 and not last_line.endswith((':', '-', '*')):
                    return True

        return False

    def _is_code_only(self, text: str) -> bool:
        """Check if response is only code with no explanation."""
        # Remove code blocks
        no_code = re.sub(r'```[\s\S]*?```', '', text)
        no_code = re.sub(r'`[^`]+`', '', no_code)

        # Check remaining text length
        remaining = no_code.strip()
        if len(remaining) < 50:  # Very little explanation
            if '```' in text:  # But has code
                return True

        return False

    def _has_high_uncertainty(self, text: str) -> bool:
        """Check for high uncertainty patterns."""
        for pattern in self.HIGH_UNCERTAINTY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_reasoning_markers(self, text: str) -> bool:
        """Check for reasoning markers without full pattern extraction."""
        reasoning_patterns = [
            r"(?:First|Step 1|To start)",
            r"(?:Second|Next|Then|Step 2)",
            r"(?:Let me|I'll|I will) (?:think|work|break|analyze)",
            r"(?:Therefore|Thus|So|In conclusion)",
            r"\d+\.\s+.*\n\d+\.\s+",  # Numbered lists
        ]
        matches = sum(1 for p in reasoning_patterns if re.search(p, text, re.IGNORECASE))
        return matches >= 2

    def _has_correction_markers(self, text: str) -> bool:
        """Check for correction markers without full pattern extraction."""
        correction_patterns = [
            r"(?:Actually|However|But|Although)",
            r"(?:That's not quite|The correct|A better)",
            r"(?:The issue|The problem)",
            r"(?:should be|instead of|rather than)",
        ]
        matches = sum(1 for p in correction_patterns if re.search(p, text, re.IGNORECASE))
        return matches >= 2

    def _has_principle_markers(self, text: str) -> bool:
        """Check for principle markers without full pattern extraction."""
        principle_patterns = [
            r"(?:Always|Never|You should)",
            r"(?:A (?:good|best) practice)",
            r"(?:Remember that|Keep in mind)",
            r"(?:The (?:key|important thing) is)",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in principle_patterns)

    def _has_any_reasoning(self, text: str) -> bool:
        """Check if text has any reasoning structure."""
        # Check for numbered/bulleted lists
        if re.search(r'(?:^|\n)\s*[\d\-\*•]\s*[A-Za-z]', text):
            return True
        # Check for logical connectors
        connectors = ['because', 'therefore', 'thus', 'since', 'given that',
                      'as a result', 'consequently', 'first', 'then', 'finally']
        connector_count = sum(1 for c in connectors if c in text.lower())
        return connector_count >= 2

    def _record_rejection(self, reason: str):
        """Record a rejection in statistics."""
        self._stats['total_rejected'] += 1

        # Extract reason category
        category = reason.split('(')[0].strip() if '(' in reason else reason
        category = category.split(':')[0].strip() if ':' in category else category

        if category not in self._stats['rejection_reasons']:
            self._stats['rejection_reasons'][category] = 0
        self._stats['rejection_reasons'][category] += 1

    def _update_average_score(self):
        """Update the average quality score."""
        if self._stats['total_accepted'] > 0:
            self._stats['average_quality_score'] = (
                self._stats['quality_score_sum'] / self._stats['total_accepted']
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        stats = dict(self._stats)

        # Calculate rejection rate
        if stats['total_processed'] > 0:
            stats['rejection_rate'] = stats['total_rejected'] / stats['total_processed']
            stats['acceptance_rate'] = stats['total_accepted'] / stats['total_processed']
        else:
            stats['rejection_rate'] = 0.0
            stats['acceptance_rate'] = 0.0

        # Remove internal tracking field
        stats.pop('quality_score_sum', None)

        return stats

    def reset_stats(self):
        """Reset filter statistics."""
        self._stats = {
            'total_processed': 0,
            'total_accepted': 0,
            'total_rejected': 0,
            'rejection_reasons': {},
            'average_quality_score': 0.0,
            'quality_score_sum': 0.0,
        }

    def meets_target_rejection_rate(self, target: float = 0.2) -> bool:
        """Check if filter is meeting target rejection rate (>20% by default)."""
        return self._stats.get('rejection_rate', 0) >= target


class DistillationDB:
    """Database for storing distilled knowledge.

    Primary storage on external drive: /Volumes/David External/sam_training/distilled/distillation.db
    Falls back to local ~/.sam/knowledge_distillation.db if external drive not mounted.

    Tables:
    - examples: Training examples with full metadata
    - reasoning_patterns: Extracted reasoning patterns from Claude
    - corrections: When Claude corrects SAM's errors (high-value data)
    - principles: Reusable guidelines extracted from responses
    - review_queue: Examples awaiting human review
    - chain_of_thought: Legacy CoT storage
    - preference_pairs: Good/bad response pairs
    - skill_templates: Reusable skill patterns
    - raw_interactions: Unprocessed Claude interactions
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the distillation database.

        Args:
            db_path: Optional explicit path. If None, uses external drive if mounted,
                    otherwise falls back to local path.
        """
        # Determine if we're using external or local storage
        use_external = is_external_drive_mounted()

        if db_path is None:
            self.db_path = get_db_path()
        else:
            self.db_path = db_path
            # If an explicit local path is given, use local for everything
            if not str(db_path).startswith("/Volumes/David External"):
                use_external = False

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Store paths for exports - match the database location
        self.export_path = EXPORT_PATH if use_external else Path.home() / ".sam" / "exports"
        self.pending_review_path = PENDING_REVIEW_PATH if is_external_drive_mounted() else Path.home() / ".sam" / "pending_review"
        self.approved_path = APPROVED_PATH if is_external_drive_mounted() else Path.home() / ".sam" / "approved"

        # Create export directories
        for path in [self.export_path, self.pending_review_path, self.approved_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Initialize quality filter for auto-filtering on save
        self.quality_filter = QualityFilter()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # ===== NEW TABLES (DISTILLATION_FORMAT.md schema) =====

        # Primary examples table - stores training-ready examples
        cur.execute("""
            CREATE TABLE IF NOT EXISTS examples (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                sam_attempt TEXT,
                claude_response TEXT NOT NULL,
                reasoning_type TEXT,
                domain TEXT DEFAULT 'general',
                complexity INTEGER DEFAULT 5,
                quality_score REAL DEFAULT 0.5,
                human_reviewed INTEGER DEFAULT 0,
                approved INTEGER DEFAULT 0,
                reviewer_notes TEXT,
                reasoning_pattern_id TEXT,
                created_at REAL,
                reviewed_at REAL,
                exported_at REAL,
                FOREIGN KEY (reasoning_pattern_id) REFERENCES reasoning_patterns(id)
            )
        """)

        # Reasoning patterns - extracted analysis of Claude's approach
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_patterns (
                id TEXT PRIMARY KEY,
                example_id TEXT,
                reasoning_type TEXT NOT NULL,
                reasoning_steps TEXT,
                tool_usage TEXT,
                complexity INTEGER,
                confidence REAL,
                created_at REAL,
                FOREIGN KEY (example_id) REFERENCES examples(id)
            )
        """)

        # Corrections - when Claude fixes SAM's mistakes (highest value data)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id TEXT PRIMARY KEY,
                example_id TEXT NOT NULL,
                error_type TEXT,
                what_sam_said TEXT,
                what_was_wrong TEXT,
                correct_answer TEXT,
                improvements TEXT,
                lesson_learned TEXT,
                created_at REAL,
                FOREIGN KEY (example_id) REFERENCES examples(id)
            )
        """)

        # Principles - reusable guidelines extracted from responses
        cur.execute("""
            CREATE TABLE IF NOT EXISTS principles (
                id TEXT PRIMARY KEY,
                domain TEXT,
                principle TEXT NOT NULL,
                examples TEXT,
                importance REAL DEFAULT 0.5,
                source_count INTEGER DEFAULT 1,
                verified INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        """)

        # Review queue - tracks examples awaiting human review
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id TEXT PRIMARY KEY,
                example_id TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                assigned_to TEXT,
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (example_id) REFERENCES examples(id)
            )
        """)

        # ===== LEGACY TABLES (backwards compatibility) =====

        # Chain of thought examples
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chain_of_thought (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                reasoning_steps TEXT,
                final_answer TEXT,
                domain TEXT,
                complexity INTEGER,
                success INTEGER,
                created_at REAL
            )
        """)

        # Preference pairs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS preference_pairs (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                good_response TEXT,
                bad_response TEXT,
                reason TEXT,
                domain TEXT,
                created_at REAL
            )
        """)

        # Skill templates
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skill_templates (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                pattern TEXT,
                examples TEXT,
                domains TEXT,
                created_at REAL
            )
        """)

        # Raw Claude interactions for analysis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_interactions (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                response TEXT,
                domain TEXT,
                quality_score REAL,
                processed INTEGER DEFAULT 0,
                created_at REAL
            )
        """)

        # ===== INDEXES =====
        cur.execute("CREATE INDEX IF NOT EXISTS idx_examples_domain ON examples(domain)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_examples_approved ON examples(approved)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_examples_reviewed ON examples(human_reviewed)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_corrections_error_type ON corrections(error_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_principles_domain ON principles(domain)")

        conn.commit()
        conn.close()

    # ===== NEW METHODS FOR FULL DISTILLATION WORKFLOW =====

    def save_example(
        self,
        query: str,
        claude_response: str,
        sam_attempt: Optional[str] = None,
        domain: str = "general",
        auto_extract: bool = True,
        auto_filter: bool = True
    ) -> Optional[str]:
        """Save a training example and optionally extract reasoning pattern.

        Args:
            query: The original user query
            claude_response: Claude's response
            sam_attempt: SAM's initial attempt (if any)
            domain: Domain classification
            auto_extract: Whether to automatically extract reasoning pattern
            auto_filter: Whether to apply quality filter (rejects low-value examples)

        Returns:
            The example ID if accepted, None if rejected by quality filter
        """
        # Extract reasoning pattern first (needed for quality filtering)
        pattern = None
        if auto_extract:
            extractor = ReasoningPatternExtractor()
            pattern = extractor.extract(query, claude_response, sam_attempt, domain)

        # Apply quality filter if enabled
        if auto_filter:
            filter_result = self.quality_filter.filter(
                query=query,
                response=claude_response,
                pattern=pattern,
                sam_attempt=sam_attempt
            )

            if not filter_result.accepted:
                # Log the rejection for debugging/analysis
                self._log_filter_rejection(
                    query, claude_response, filter_result, domain
                )
                return None

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Generate ID
        example_id = hashlib.md5(
            f"{query}{claude_response[:100]}{time.time()}".encode()
        ).hexdigest()[:16]

        reasoning_type = None
        reasoning_pattern_id = None
        complexity = 5

        # Use filter-calculated quality score if available, otherwise fall back
        if auto_filter:
            quality_score = filter_result.quality_score
        else:
            quality_score = 0.7 if sam_attempt else 0.5  # Corrections are more valuable

        # Extract reasoning pattern if requested
        if auto_extract and pattern:
            reasoning_type = pattern.reasoning_type.value
            complexity = pattern.complexity
            # Update quality score from pattern confidence if not filtered
            if not auto_filter:
                quality_score = pattern.confidence

            # Store the reasoning pattern
            reasoning_pattern_id = f"rp_{example_id}"
            cur.execute("""
                INSERT INTO reasoning_patterns
                (id, example_id, reasoning_type, reasoning_steps, tool_usage, complexity, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reasoning_pattern_id,
                example_id,
                reasoning_type,
                json.dumps([asdict(s) for s in pattern.reasoning_steps]),
                json.dumps([asdict(t) for t in pattern.tool_usage]),
                pattern.complexity,
                pattern.confidence,
                time.time()
            ))

            # Store corrections if found
            if pattern.corrections and pattern.corrections.sam_errors:
                for error in pattern.corrections.sam_errors:
                    correction_id = hashlib.md5(
                        f"{example_id}{error.error_type}".encode()
                    ).hexdigest()[:12]
                    cur.execute("""
                        INSERT OR REPLACE INTO corrections
                        (id, example_id, error_type, what_sam_said, what_was_wrong,
                         correct_answer, improvements, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        correction_id,
                        example_id,
                        error.error_type,
                        error.what_sam_said,
                        error.what_was_wrong,
                        error.correct_answer,
                        json.dumps(pattern.corrections.improvements),
                        time.time()
                    ))
                # Corrections get higher priority for review
                quality_score = min(1.0, quality_score + 0.2)

            # Store extracted principles
            for p in pattern.principles:
                principle_id = hashlib.md5(p.principle[:50].lower().encode()).hexdigest()[:12]
                cur.execute("""
                    INSERT INTO principles (id, domain, principle, examples, importance, source_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        source_count = source_count + 1,
                        updated_at = ?,
                        importance = MAX(importance, ?)
                """, (
                    principle_id, domain, p.principle, json.dumps([query[:100]]),
                    p.importance, 1, time.time(), time.time(),
                    time.time(), p.importance
                ))

        # Insert the example
        cur.execute("""
            INSERT INTO examples
            (id, query, sam_attempt, claude_response, reasoning_type, domain,
             complexity, quality_score, reasoning_pattern_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            example_id, query, sam_attempt, claude_response, reasoning_type,
            domain, complexity, quality_score, reasoning_pattern_id, time.time()
        ))

        # Add high-value examples to review queue
        if quality_score >= 0.7 or sam_attempt:  # Corrections and high-quality examples
            self._add_to_review_queue(cur, example_id,
                priority=8 if sam_attempt else 5,
                reason="Correction detected" if sam_attempt else "High quality score")

        conn.commit()
        conn.close()

        return example_id

    def _add_to_review_queue(
        self,
        cur: sqlite3.Cursor,
        example_id: str,
        priority: int = 5,
        reason: str = ""
    ):
        """Add an example to the review queue."""
        queue_id = hashlib.md5(f"queue_{example_id}".encode()).hexdigest()[:12]
        cur.execute("""
            INSERT OR IGNORE INTO review_queue
            (id, example_id, priority, reason, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (queue_id, example_id, priority, reason, time.time(), time.time()))

    def _log_filter_rejection(
        self,
        query: str,
        response: str,
        filter_result: 'FilterResult',
        domain: str
    ):
        """Log a quality filter rejection for analysis.

        Stores rejected examples in a separate table for later analysis
        to tune filter parameters.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Ensure the rejections table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS filter_rejections (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response_preview TEXT,
                domain TEXT,
                quality_score REAL,
                rejection_reason TEXT,
                quality_flags TEXT,
                created_at REAL
            )
        """)

        rejection_id = hashlib.md5(
            f"{query[:50]}{response[:50]}{time.time()}".encode()
        ).hexdigest()[:16]

        cur.execute("""
            INSERT OR IGNORE INTO filter_rejections
            (id, query, response_preview, domain, quality_score, rejection_reason, quality_flags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rejection_id,
            query[:500],  # Truncate for storage
            response[:500],  # Preview only
            domain,
            filter_result.quality_score,
            filter_result.rejection_reason,
            json.dumps(filter_result.quality_flags),
            time.time()
        ))

        conn.commit()
        conn.close()

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get quality filter statistics.

        Returns comprehensive stats about filter performance including:
        - Total processed, accepted, rejected
        - Rejection rate and acceptance rate
        - Breakdown by rejection reason
        - Average quality score of accepted examples
        """
        stats = self.quality_filter.get_stats()

        # Add database rejection counts
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) FROM filter_rejections")
            stats['db_rejections'] = cur.fetchone()[0]

            cur.execute("""
                SELECT rejection_reason, COUNT(*) as count
                FROM filter_rejections
                GROUP BY rejection_reason
                ORDER BY count DESC
            """)
            stats['db_rejection_breakdown'] = dict(cur.fetchall())

            cur.execute("""
                SELECT AVG(quality_score) FROM filter_rejections
            """)
            avg = cur.fetchone()[0]
            stats['avg_rejected_quality_score'] = avg if avg else 0.0

        except sqlite3.OperationalError:
            # Table doesn't exist yet
            stats['db_rejections'] = 0
            stats['db_rejection_breakdown'] = {}
            stats['avg_rejected_quality_score'] = 0.0

        conn.close()

        return stats

    def get_pending_review(self, limit: int = 10, domain: Optional[str] = None) -> List[Dict]:
        """Get examples pending human review.

        Args:
            limit: Maximum number of examples to return
            domain: Optional domain filter

        Returns:
            List of examples with their review info
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = """
            SELECT e.*, r.priority, r.reason as review_reason, r.status as review_status
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending'
        """
        params = []

        if domain:
            query += " AND e.domain = ?"
            params.append(domain)

        query += " ORDER BY r.priority DESC, e.quality_score DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def approve_example(
        self,
        example_id: str,
        notes: Optional[str] = None,
        quality_override: Optional[float] = None
    ) -> bool:
        """Approve an example for training.

        Args:
            example_id: The example to approve
            notes: Optional reviewer notes
            quality_override: Optional quality score override

        Returns:
            True if approved successfully
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        now = time.time()

        # Update the example
        update_fields = ["human_reviewed = 1", "approved = 1", f"reviewed_at = {now}"]
        params = []

        if notes:
            update_fields.append("reviewer_notes = ?")
            params.append(notes)

        if quality_override is not None:
            update_fields.append("quality_score = ?")
            params.append(quality_override)

        params.append(example_id)

        cur.execute(f"""
            UPDATE examples SET {', '.join(update_fields)}
            WHERE id = ?
        """, params)

        # Update review queue status
        cur.execute("""
            UPDATE review_queue SET status = 'approved', updated_at = ?
            WHERE example_id = ?
        """, (now, example_id))

        affected = cur.rowcount > 0
        conn.commit()
        conn.close()

        return affected

    def reject_example(
        self,
        example_id: str,
        reason: str = ""
    ) -> bool:
        """Reject an example from training.

        Args:
            example_id: The example to reject
            reason: Reason for rejection

        Returns:
            True if rejected successfully
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        now = time.time()

        cur.execute("""
            UPDATE examples SET human_reviewed = 1, approved = 0,
                   reviewed_at = ?, reviewer_notes = ?
            WHERE id = ?
        """, (now, f"REJECTED: {reason}", example_id))

        cur.execute("""
            UPDATE review_queue SET status = 'rejected', updated_at = ?
            WHERE example_id = ?
        """, (now, example_id))

        affected = cur.rowcount > 0
        conn.commit()
        conn.close()

        return affected

    def get_example_details(self, example_id: str) -> Optional[Dict]:
        """Get full details of an example including reasoning pattern and corrections.

        Args:
            example_id: The example ID

        Returns:
            Dict with full example details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Get the example
        cur.execute("""
            SELECT e.*, r.priority, r.reason as review_reason, r.status as review_status
            FROM examples e
            LEFT JOIN review_queue r ON e.id = r.example_id
            WHERE e.id = ?
        """, (example_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return None

        result = dict(row)

        # Get reasoning pattern if exists
        if result.get('reasoning_pattern_id'):
            cur.execute("""
                SELECT * FROM reasoning_patterns WHERE id = ?
            """, (result['reasoning_pattern_id'],))
            pattern_row = cur.fetchone()
            if pattern_row:
                result['reasoning_pattern'] = dict(pattern_row)
                # Parse JSON fields
                if result['reasoning_pattern'].get('reasoning_steps'):
                    try:
                        result['reasoning_pattern']['reasoning_steps'] = json.loads(
                            result['reasoning_pattern']['reasoning_steps']
                        )
                    except json.JSONDecodeError:
                        pass
                if result['reasoning_pattern'].get('tool_usage'):
                    try:
                        result['reasoning_pattern']['tool_usage'] = json.loads(
                            result['reasoning_pattern']['tool_usage']
                        )
                    except json.JSONDecodeError:
                        pass

        # Get corrections if any
        cur.execute("""
            SELECT * FROM corrections WHERE example_id = ?
        """, (example_id,))
        corrections = cur.fetchall()
        if corrections:
            result['corrections'] = [dict(c) for c in corrections]
            for c in result['corrections']:
                if c.get('improvements'):
                    try:
                        c['improvements'] = json.loads(c['improvements'])
                    except json.JSONDecodeError:
                        pass

        # Get extracted principles linked to this example
        # Note: example_principles table may not exist, handle gracefully
        try:
            cur.execute("""
                SELECT * FROM principles WHERE id IN (
                    SELECT DISTINCT principle_id FROM example_principles WHERE example_id = ?
                )
            """, (example_id,))
            principles = cur.fetchall()
            if principles:
                result['principles'] = [dict(p) for p in principles]
        except sqlite3.OperationalError:
            # Table doesn't exist, that's ok - principles aren't linked via junction table
            pass

        conn.close()
        return result

    def batch_approve_above_threshold(self, threshold: float = 0.7) -> Dict[str, Any]:
        """Auto-approve all pending examples above a quality threshold.

        Args:
            threshold: Minimum quality score to auto-approve (0.0-1.0)

        Returns:
            Dict with count of approved examples and their IDs
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        now = time.time()

        # Get IDs that qualify
        cur.execute("""
            SELECT e.id, e.quality_score
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending'
              AND e.human_reviewed = 0
              AND e.quality_score >= ?
        """, (threshold,))
        qualifying = cur.fetchall()
        ids = [row[0] for row in qualifying]

        if not ids:
            conn.close()
            return {"approved_count": 0, "ids": [], "threshold": threshold}

        # Update examples
        placeholders = ",".join("?" * len(ids))
        cur.execute(f"""
            UPDATE examples
            SET human_reviewed = 1, approved = 1, reviewed_at = ?,
                reviewer_notes = ?
            WHERE id IN ({placeholders})
        """, [now, f"AUTO-APPROVED: quality >= {threshold}"] + ids)

        # Update review queue
        cur.execute(f"""
            UPDATE review_queue
            SET status = 'approved', updated_at = ?
            WHERE example_id IN ({placeholders})
        """, [now] + ids)

        conn.commit()
        conn.close()

        return {
            "approved_count": len(ids),
            "ids": ids,
            "threshold": threshold,
            "scores": {row[0]: row[1] for row in qualifying}
        }

    def batch_reject_below_threshold(self, threshold: float = 0.2) -> Dict[str, Any]:
        """Auto-reject all pending examples below a quality threshold.

        Args:
            threshold: Maximum quality score to auto-reject (0.0-1.0)

        Returns:
            Dict with count of rejected examples and their IDs
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        now = time.time()

        # Get IDs that qualify for rejection
        cur.execute("""
            SELECT e.id, e.quality_score
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending'
              AND e.human_reviewed = 0
              AND e.quality_score < ?
        """, (threshold,))
        qualifying = cur.fetchall()
        ids = [row[0] for row in qualifying]

        if not ids:
            conn.close()
            return {"rejected_count": 0, "ids": [], "threshold": threshold}

        # Update examples
        placeholders = ",".join("?" * len(ids))
        cur.execute(f"""
            UPDATE examples
            SET human_reviewed = 1, approved = 0, reviewed_at = ?,
                reviewer_notes = ?
            WHERE id IN ({placeholders})
        """, [now, f"AUTO-REJECTED: quality < {threshold}"] + ids)

        # Update review queue
        cur.execute(f"""
            UPDATE review_queue
            SET status = 'rejected', updated_at = ?
            WHERE example_id IN ({placeholders})
        """, [now] + ids)

        conn.commit()
        conn.close()

        return {
            "rejected_count": len(ids),
            "ids": ids,
            "threshold": threshold,
            "scores": {row[0]: row[1] for row in qualifying}
        }

    def get_review_stats(self) -> Dict[str, Any]:
        """Get statistics about the review queue.

        Returns:
            Dict with review queue statistics
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        # Pending count
        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'pending'")
        stats['pending'] = cur.fetchone()[0]

        # Approved count
        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'approved'")
        stats['approved'] = cur.fetchone()[0]

        # Rejected count
        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'rejected'")
        stats['rejected'] = cur.fetchone()[0]

        # Quality score distribution of pending
        cur.execute("""
            SELECT
                COUNT(CASE WHEN e.quality_score >= 0.7 THEN 1 END) as high,
                COUNT(CASE WHEN e.quality_score >= 0.4 AND e.quality_score < 0.7 THEN 1 END) as medium,
                COUNT(CASE WHEN e.quality_score >= 0.2 AND e.quality_score < 0.4 THEN 1 END) as low,
                COUNT(CASE WHEN e.quality_score < 0.2 THEN 1 END) as very_low
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending'
        """)
        row = cur.fetchone()
        stats['pending_by_quality'] = {
            'high': row[0],      # >= 0.7
            'medium': row[1],   # 0.4 - 0.7
            'low': row[2],      # 0.2 - 0.4
            'very_low': row[3]  # < 0.2
        }

        # By domain
        cur.execute("""
            SELECT e.domain, COUNT(*) as count
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending'
            GROUP BY e.domain
        """)
        stats['pending_by_domain'] = dict(cur.fetchall())

        # By reasoning type
        cur.execute("""
            SELECT e.reasoning_type, COUNT(*) as count
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending' AND e.reasoning_type IS NOT NULL
            GROUP BY e.reasoning_type
        """)
        stats['pending_by_type'] = dict(cur.fetchall())

        # Count of corrections pending
        cur.execute("""
            SELECT COUNT(*)
            FROM examples e
            JOIN review_queue r ON e.id = r.example_id
            WHERE r.status = 'pending' AND e.sam_attempt IS NOT NULL
        """)
        stats['pending_corrections'] = cur.fetchone()[0]

        conn.close()
        return stats

    def export_for_training(
        self,
        output_path: Optional[Path] = None,
        only_approved: bool = True,
        include_corrections: bool = True,
        format: str = "instruction"  # instruction, preference, or raw
    ) -> int:
        """Export examples to JSONL for training.

        Args:
            output_path: Where to write the JSONL file
            only_approved: Only export human-approved examples
            include_corrections: Include correction examples (high value)
            format: Output format - instruction, preference, or raw

        Returns:
            Number of examples exported
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.export_path / f"distilled_{format}_{timestamp}.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Build query based on filters
        where_clauses = []
        if only_approved:
            where_clauses.append("e.approved = 1")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cur.execute(f"""
            SELECT e.*, rp.reasoning_steps, rp.tool_usage
            FROM examples e
            LEFT JOIN reasoning_patterns rp ON e.reasoning_pattern_id = rp.id
            {where_sql}
            ORDER BY e.quality_score DESC
        """)

        examples = cur.fetchall()
        count = 0

        with open(output_path, 'w') as f:
            for row in examples:
                example = dict(row)

                if format == "instruction":
                    # Alpaca-style instruction format
                    output = {
                        "instruction": example["query"],
                        "input": example.get("sam_attempt") or "",
                        "output": example["claude_response"],
                        "domain": example["domain"],
                        "reasoning_type": example["reasoning_type"],
                        "quality": example["quality_score"]
                    }
                elif format == "preference":
                    # DPO preference format - only if we have sam_attempt
                    if example.get("sam_attempt"):
                        output = {
                            "prompt": example["query"],
                            "chosen": example["claude_response"],
                            "rejected": example["sam_attempt"],
                            "domain": example["domain"]
                        }
                    else:
                        continue  # Skip non-correction examples for preference format
                else:  # raw
                    output = example
                    # Convert any bytes to strings
                    for k, v in output.items():
                        if isinstance(v, bytes):
                            output[k] = v.decode('utf-8', errors='replace')

                f.write(json.dumps(output) + "\n")
                count += 1

        # Also export corrections separately if requested
        if include_corrections:
            corrections_path = output_path.parent / f"corrections_{output_path.name}"
            cur.execute("""
                SELECT c.*, e.query, e.domain
                FROM corrections c
                JOIN examples e ON c.example_id = e.id
                WHERE e.approved = 1 OR ? = 0
            """, (1 if only_approved else 0,))

            with open(corrections_path, 'w') as f:
                for row in cur.fetchall():
                    correction = dict(row)
                    output = {
                        "instruction": f"SAM said: {correction['what_sam_said']}\n\nWhat was the issue?",
                        "input": correction["query"],
                        "output": f"The issue was: {correction['what_was_wrong']}\n\nThe correct answer is: {correction['correct_answer']}",
                        "error_type": correction["error_type"],
                        "domain": correction["domain"],
                        "type": "correction"
                    }
                    f.write(json.dumps(output) + "\n")

        # Mark examples as exported
        now = time.time()
        cur.execute(f"""
            UPDATE examples SET exported_at = ?
            {where_sql}
        """, (now,))

        conn.commit()
        conn.close()

        print(f"Exported {count} examples to {output_path}")
        return count

    def get_stats(self) -> Dict:
        """Get comprehensive statistics about the distillation database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        # New tables
        cur.execute("SELECT COUNT(*) FROM examples")
        stats["total_examples"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM examples WHERE approved = 1")
        stats["approved_examples"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM examples WHERE human_reviewed = 0")
        stats["unreviewed_examples"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM reasoning_patterns")
        stats["reasoning_patterns"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM corrections")
        stats["corrections"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'pending'")
        stats["pending_review"] = cur.fetchone()[0]

        # By domain
        cur.execute("SELECT domain, COUNT(*) FROM examples GROUP BY domain")
        stats["by_domain"] = dict(cur.fetchall())

        # By reasoning type
        cur.execute("SELECT reasoning_type, COUNT(*) FROM examples WHERE reasoning_type IS NOT NULL GROUP BY reasoning_type")
        stats["by_reasoning_type"] = dict(cur.fetchall())

        # Legacy tables (backwards compatibility)
        cur.execute("SELECT COUNT(*) FROM chain_of_thought")
        stats["chain_of_thought"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM principles")
        stats["principles"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM preference_pairs")
        stats["preference_pairs"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM skill_templates")
        stats["skill_templates"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw_interactions")
        stats["raw_interactions"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw_interactions WHERE processed = 0")
        stats["unprocessed"] = cur.fetchone()[0]

        # Quality filter stats
        try:
            cur.execute("SELECT COUNT(*) FROM filter_rejections")
            stats["filter_rejections"] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            stats["filter_rejections"] = 0

        # Include live filter stats
        filter_stats = self.quality_filter.get_stats()
        stats["quality_filter"] = filter_stats

        # Storage info
        stats["db_path"] = str(self.db_path)
        stats["using_external_drive"] = is_external_drive_mounted()

        conn.close()
        return stats

    # ===== LEGACY METHODS (kept for backwards compatibility) =====

    def store_interaction(self, prompt: str, response: str, domain: str, quality: float = 0.8):
        """Store a Claude interaction for later analysis"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        id = hashlib.md5(f"{prompt}{response}".encode()).hexdigest()[:12]

        cur.execute("""
            INSERT OR IGNORE INTO raw_interactions
            (id, prompt, response, domain, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id, prompt, response, domain, quality, time.time()))

        conn.commit()
        conn.close()
        return id

    def store_cot(self, cot: ChainOfThought):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO chain_of_thought
            (id, prompt, reasoning_steps, final_answer, domain, complexity, success, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cot.id, cot.prompt, json.dumps(cot.reasoning_steps),
            cot.final_answer, cot.domain, cot.complexity, int(cot.success),
            time.time()
        ))

        conn.commit()
        conn.close()

    def store_principle(self, principle: Principle):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Check if exists, increment count
        cur.execute("SELECT source_count FROM principles WHERE id = ?", (principle.id,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE principles SET source_count = source_count + 1, updated_at = ?
                WHERE id = ?
            """, (time.time(), principle.id))
        else:
            cur.execute("""
                INSERT INTO principles
                (id, domain, principle, examples, importance, source_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                principle.id, principle.domain, principle.principle,
                json.dumps(principle.examples), principle.importance,
                principle.source_count, time.time(), time.time()
            ))

        conn.commit()
        conn.close()

    def store_preference(self, pair: PreferencePair):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO preference_pairs
            (id, prompt, good_response, bad_response, reason, domain, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pair.id, pair.prompt, pair.good_response, pair.bad_response,
            pair.reason, pair.domain, time.time()
        ))

        conn.commit()
        conn.close()

    def store_skill(self, skill: SkillTemplate):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO skill_templates
            (id, name, description, pattern, examples, domains, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            skill.id, skill.name, skill.description, skill.pattern,
            json.dumps(skill.examples), json.dumps(skill.domains), time.time()
        ))

        conn.commit()
        conn.close()

class ChainOfThoughtExtractor:
    """Extracts step-by-step reasoning from Claude responses"""

    # Patterns that indicate reasoning steps
    STEP_PATTERNS = [
        r"(?:First|1\.?|Step 1)[,:]?\s+(.+?)(?=(?:Second|2\.?|Step 2|Then|Next|\n\n|$))",
        r"(?:Second|2\.?|Step 2)[,:]?\s+(.+?)(?=(?:Third|3\.?|Step 3|Then|Next|\n\n|$))",
        r"(?:Third|3\.?|Step 3)[,:]?\s+(.+?)(?=(?:Fourth|4\.?|Step 4|Then|Next|\n\n|$))",
        r"(?:Let me|I'll|I will)\s+(.+?)(?=\.\s+(?:Then|Next|After|Now)|$)",
        r"(?:The reason|Because|Since)\s+(.+?)(?=\.\s+(?:Therefore|So|Thus)|$)",
    ]

    CONCLUSION_PATTERNS = [
        r"(?:Therefore|Thus|So|In conclusion|Finally)[,:]?\s+(.+?)(?:\.|$)",
        r"(?:The answer is|The result is|This means)[,:]?\s+(.+?)(?:\.|$)",
    ]

    def extract(self, prompt: str, response: str, domain: str) -> Optional[ChainOfThought]:
        """Extract chain of thought from a response"""
        steps = []

        # Look for numbered or transitional steps
        for pattern in self.STEP_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                step = match.strip()[:500]  # Limit step length
                if len(step) > 20:  # Meaningful step
                    steps.append(step)

        if not steps:
            # Try splitting by paragraphs if no explicit steps
            paragraphs = [p.strip() for p in response.split('\n\n') if len(p.strip()) > 50]
            if len(paragraphs) >= 2:
                steps = paragraphs[:-1]  # All but last as steps

        if len(steps) < 2:
            return None  # Not enough reasoning to extract

        # Find conclusion
        final_answer = ""
        for pattern in self.CONCLUSION_PATTERNS:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                final_answer = match.group(1).strip()
                break

        if not final_answer:
            # Use last paragraph as conclusion
            paragraphs = response.strip().split('\n\n')
            if paragraphs:
                final_answer = paragraphs[-1][:500]

        # Estimate complexity
        complexity = min(10, len(steps) + len(response.split()) // 200)

        return ChainOfThought(
            id=hashlib.md5(f"{prompt}{response[:100]}".encode()).hexdigest()[:12],
            prompt=prompt,
            reasoning_steps=steps[:10],  # Max 10 steps
            final_answer=final_answer,
            domain=domain,
            complexity=complexity,
            success=True
        )


class PrincipleExtractor:
    """Extracts reusable principles from Claude's responses"""

    # Patterns that indicate principles/rules
    PRINCIPLE_PATTERNS = [
        r"(?:Always|Never|You should|It's (?:important|best|better) to)\s+([^.!?]+[.!?])",
        r"(?:A (?:good|best) practice is to|The key is to)\s+([^.!?]+[.!?])",
        r"(?:Remember that|Keep in mind that|Note that)\s+([^.!?]+[.!?])",
        r"(?:The principle here is|The rule is|Generally speaking)\s+([^.!?]+[.!?])",
    ]

    def extract(self, response: str, domain: str) -> List[Principle]:
        """Extract principles from a response"""
        principles = []

        for pattern in self.PRINCIPLE_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                principle_text = match.strip()
                if len(principle_text) > 30:  # Meaningful principle
                    # Create a unique ID based on normalized text
                    normalized = re.sub(r'\s+', ' ', principle_text.lower())
                    id = hashlib.md5(normalized.encode()).hexdigest()[:12]

                    principles.append(Principle(
                        id=id,
                        domain=domain,
                        principle=principle_text,
                        examples=[response[:200]],  # Context as example
                        importance=0.7,
                        source_count=1
                    ))

        return principles


class ReasoningPatternExtractor:
    """
    Comprehensive extractor for reasoning patterns from Claude responses.

    Identifies the primary reasoning type and extracts structured data:
    - chain_of_thought: Step-by-step reasoning patterns
    - tool_use: When tools/functions are used
    - correction: When Claude corrects SAM's errors (most valuable for learning)
    - direct: Simple direct answers
    - multi_step: Complex multi-part reasoning
    - meta_cognitive: Self-reflection, uncertainty acknowledgment

    Follows the structure defined in DISTILLATION_FORMAT.md.
    """

    # ===== CHAIN-OF-THOUGHT DETECTION PATTERNS =====
    COT_INDICATORS = [
        r"(?:Let me|I'll|I will) (?:think|work|break|analyze)",
        r"(?:First|Step 1|To start)",
        r"(?:Second|Next|Then|Step 2)",
        r"(?:Third|After that|Step 3)",
        r"(?:Finally|In conclusion|Therefore|So)",
        r"(?:The reason|Because|Since) .* (?:Therefore|So|Thus)",
        r"\d+\.\s+.*\n\d+\.\s+",  # Numbered lists
    ]

    # Patterns for extracting individual reasoning steps
    STEP_EXTRACTION_PATTERNS = [
        # Numbered steps: "1. Do this" or "Step 1: Do this"
        (r"(?:Step\s*)?(\d+)[.):]\s*\**([^*\n]+)\**", "numbered"),
        # Transitional: "First, ...", "Second, ...", "Finally, ..."
        (r"(?:First|Second|Third|Fourth|Fifth|Next|Then|Finally|Lastly)[,:]?\s+(.+?)(?=\n|$)", "transitional"),
        # Markdown headers as steps: "### 1. Identify"
        (r"#+\s*(?:\d+\.)?\s*\**(.+?)\**", "header"),
        # Bold action markers: "**Identify the problem**"
        (r"\*\*([^*]+)\*\*[:\s]+(.+?)(?=\n\n|\*\*|$)", "bold_action"),
    ]

    # ===== TOOL USE DETECTION PATTERNS =====
    TOOL_INDICATORS = [
        r"```(?:bash|shell|sh|zsh)\n",           # Shell commands
        r"```(?:python|py)\n.*(?:import|def|class)",  # Python code
        r"(?:I would|Let me) (?:run|execute|call)",
        r"(?:Using|With) (?:the|this) (?:tool|function|command)",
        r"(?:curl|git|npm|pip|cargo|docker)\s+",    # CLI tools
        r"<invoke|<function_calls>",  # Claude tool use XML
        r"(?:invoke|calling|execute)\s+(?:the\s+)?(?:Read|Write|Bash|Glob|Grep|Edit)",  # Claude Code tools
    ]

    # Tool name extraction
    TOOL_NAME_PATTERNS = [
        r"```(bash|shell|sh|python|py|javascript|js|sql|rust|go)\n",
        r"(?:using|with|run|execute)\s+(?:the\s+)?([\w_-]+)(?:\s+(?:tool|command|function))?",
        r"<invoke name=\"(\w+)\"",
    ]

    # ===== CORRECTION DETECTION PATTERNS =====
    CORRECTION_INDICATORS = [
        r"(?:Actually|However|But|Although|That said)",
        r"(?:That's not quite|The correct|A better|More accurately)",
        r"(?:slight|small|minor) (?:issue|error|mistake|problem)",
        r"(?:missed|forgot|overlooked|didn't (?:consider|account))",
        r"(?:should be|instead of|rather than)",
        r"(?:The issue with|The problem is|This won't work because)",
        r"(?:I see|I notice) (?:that|an error|a problem|a mistake)",
    ]

    # Error type categorization
    ERROR_TYPE_PATTERNS = {
        "incomplete": [r"(?:missing|incomplete|didn't include|forgot to|also need)"],
        "incorrect": [r"(?:wrong|incorrect|error|mistake|that's not|won't work)"],
        "missing_context": [r"(?:context|consider|account for|edge case|scenario)"],
        "misunderstanding": [r"(?:misunderstood|misinterpreted|actually means|what you meant)"],
        "outdated": [r"(?:outdated|deprecated|no longer|changed|updated in)"],
        "suboptimal": [r"(?:better way|more efficient|cleaner|preferable|improved)"],
    }

    # ===== MULTI-STEP DETECTION PATTERNS =====
    MULTI_STEP_INDICATORS = [
        r"(?:There are|We need|This requires) (?:several|multiple|a few) (?:steps|parts|phases)",
        r"(?:This involves|This breaks down into)",
        r"(?:Part [A-Z1-9]|Phase [1-9]|Stage [1-9])",
        r"(?:First, we|Then, we|Next, we|Finally, we)",
    ]

    # ===== META-COGNITIVE DETECTION PATTERNS =====
    META_COGNITIVE_INDICATORS = [
        r"(?:I'm not (?:sure|certain)|I think|I believe|It seems|Possibly|Perhaps)",
        r"(?:uncertain|unsure|might be|could be|may be)",
        r"(?:Let me reconsider|On second thought|Actually, thinking about it)",
        r"(?:I should clarify|To be clear|Important to note)",
        r"(?:My reasoning|My understanding|As I understand)",
        r"(?:I realize|I notice that I|Looking back)",
        r"(?:I may be wrong|correct me if|double-check)",
    ]

    # ===== PRINCIPLE EXTRACTION PATTERNS =====
    PRINCIPLE_PATTERNS = [
        r"(?:Always|Never|You should|It's (?:important|best|better) to)\s+([^.!?\n]+[.!?]?)",
        r"(?:A (?:good|best) practice is to|The key is to)\s+([^.!?\n]+[.!?]?)",
        r"(?:Remember that|Keep in mind that|Note that)\s+([^.!?\n]+[.!?]?)",
        r"(?:The (?:principle|rule|pattern|guideline) (?:here )?is)\s+([^.!?\n]+[.!?]?)",
        r"(?:Generally|Typically|Usually|In general)[,]?\s+([^.!?\n]+[.!?]?)",
    ]

    def __init__(self):
        self.cot_extractor = ChainOfThoughtExtractor()
        self.principle_extractor = PrincipleExtractor()

    def extract(
        self,
        query: str,
        claude_response: str,
        sam_attempt: Optional[str] = None,
        domain: str = "general"
    ) -> ReasoningPattern:
        """
        Extract reasoning pattern from a Claude response.

        Args:
            query: The original user query
            claude_response: Claude's full response
            sam_attempt: SAM's initial attempt (if any) - enables correction detection
            domain: Domain classification (code, reasoning, creative, factual, planning)

        Returns:
            ReasoningPattern with extracted components
        """
        # Detect the primary reasoning type
        reasoning_type = self._detect_reasoning_type(claude_response, sam_attempt)

        # Extract reasoning steps
        reasoning_steps = self._extract_reasoning_steps(claude_response)

        # Extract tool usage
        tool_usage = self._extract_tool_usage(claude_response)

        # Extract corrections (if SAM attempt provided)
        corrections = None
        if sam_attempt:
            corrections = self._extract_corrections(sam_attempt, claude_response)

        # Extract principles
        principles = self._extract_principles(claude_response, domain)

        # Calculate complexity
        complexity = self._calculate_complexity(
            claude_response, reasoning_steps, tool_usage
        )

        # Calculate extraction confidence
        confidence = self._calculate_confidence(
            reasoning_type, reasoning_steps, tool_usage, corrections
        )

        return ReasoningPattern(
            reasoning_type=reasoning_type,
            reasoning_steps=reasoning_steps,
            tool_usage=tool_usage,
            corrections=corrections,
            principles=principles,
            complexity=complexity,
            confidence=confidence
        )

    def _detect_reasoning_type(
        self,
        response: str,
        sam_attempt: Optional[str]
    ) -> ReasoningType:
        """Detect the primary reasoning type in the response."""
        scores = {
            ReasoningType.CHAIN_OF_THOUGHT: 0,
            ReasoningType.TOOL_USE: 0,
            ReasoningType.CORRECTION: 0,
            ReasoningType.MULTI_STEP: 0,
            ReasoningType.META_COGNITIVE: 0,
            ReasoningType.DIRECT: 0,
        }

        # Check for chain-of-thought patterns
        for pattern in self.COT_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                scores[ReasoningType.CHAIN_OF_THOUGHT] += 1

        # Check for tool use patterns
        for pattern in self.TOOL_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                scores[ReasoningType.TOOL_USE] += 1

        # Check for correction patterns (weighted higher when sam_attempt exists)
        if sam_attempt:
            for pattern in self.CORRECTION_INDICATORS:
                if re.search(pattern, response, re.IGNORECASE):
                    scores[ReasoningType.CORRECTION] += 2  # Double weight

        # Check for multi-step patterns
        for pattern in self.MULTI_STEP_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                scores[ReasoningType.MULTI_STEP] += 1

        # Check for meta-cognitive patterns
        for pattern in self.META_COGNITIVE_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                scores[ReasoningType.META_COGNITIVE] += 1

        # Direct answers are short and have no reasoning patterns
        word_count = len(response.split())
        if word_count < 100 and all(s == 0 for s in scores.values()):
            scores[ReasoningType.DIRECT] = 1

        # Return the type with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return ReasoningType.DIRECT

        for rtype, score in scores.items():
            if score == max_score:
                return rtype

        return ReasoningType.DIRECT

    def _extract_reasoning_steps(self, response: str) -> List[ReasoningStep]:
        """Extract individual reasoning steps from the response."""
        steps = []
        step_num = 0

        # Try numbered/transitional patterns first
        for pattern, pattern_type in self.STEP_EXTRACTION_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                step_num += 1
                if pattern_type == "numbered":
                    content = match.group(2).strip()
                    action = self._infer_action(content)
                elif pattern_type == "bold_action":
                    action = match.group(1).strip().lower()
                    content = match.group(2).strip()
                else:
                    content = match.group(1).strip()
                    action = self._infer_action(content)

                # Skip very short matches
                if len(content) < 10:
                    continue

                # Limit content length
                content = content[:500]

                steps.append(ReasoningStep(
                    step_num=step_num,
                    action=action,
                    content=content,
                    reasoning=self._infer_reasoning(content, action)
                ))

        # If no explicit steps found, try paragraph splitting
        if not steps:
            paragraphs = [p.strip() for p in response.split('\n\n') if len(p.strip()) > 50]
            if len(paragraphs) >= 2:
                for i, para in enumerate(paragraphs[:8], 1):  # Max 8 paragraphs
                    action = self._infer_action(para)
                    steps.append(ReasoningStep(
                        step_num=i,
                        action=action,
                        content=para[:500],
                        reasoning=self._infer_reasoning(para, action)
                    ))

        # Deduplicate and limit
        seen_content = set()
        unique_steps = []
        for step in steps:
            content_hash = step.content[:100].lower()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_steps.append(step)

        return unique_steps[:10]  # Max 10 steps

    def _infer_action(self, content: str) -> str:
        """Infer the action type from step content."""
        content_lower = content.lower()

        action_keywords = {
            "identify": ["identify", "find", "locate", "determine", "check", "look for"],
            "analyze": ["analyze", "examine", "investigate", "review", "assess", "evaluate"],
            "solve": ["solve", "fix", "resolve", "address", "handle", "implement"],
            "verify": ["verify", "test", "validate", "confirm", "ensure", "check that"],
            "explain": ["explain", "describe", "clarify", "note that", "understand"],
            "compare": ["compare", "contrast", "versus", "difference", "vs"],
            "refactor": ["refactor", "clean up", "improve", "optimize", "simplify"],
            "debug": ["debug", "trace", "error", "bug", "issue", "problem"],
            "plan": ["plan", "design", "architect", "structure", "organize"],
            "execute": ["run", "execute", "call", "invoke", "perform"],
        }

        for action, keywords in action_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return action

        return "process"  # Default action

    def _infer_reasoning(self, content: str, action: str) -> str:
        """Infer the reasoning behind a step."""
        reasoning_map = {
            "identify": "Need to locate the relevant information first",
            "analyze": "Understanding the problem structure helps find solutions",
            "solve": "Applying the solution to address the issue",
            "verify": "Confirming the solution works correctly",
            "explain": "Providing clarity and context",
            "compare": "Weighing options to make informed decisions",
            "refactor": "Improving code quality and maintainability",
            "debug": "Tracing the issue to find root cause",
            "plan": "Organizing approach before implementation",
            "execute": "Carrying out the planned action",
            "process": "Proceeding through the task",
        }
        return reasoning_map.get(action, "Continuing the reasoning process")

    def _extract_tool_usage(self, response: str) -> List[ToolUsage]:
        """Extract tool/function usage patterns from the response."""
        tools = []

        # Find code blocks
        code_block_pattern = r"```(\w+)?\n([\s\S]*?)```"
        for match in re.finditer(code_block_pattern, response):
            lang = match.group(1) or "code"
            code = match.group(2).strip()

            if lang in ["bash", "shell", "sh", "zsh"]:
                # Parse shell commands
                for line in code.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        tool_name = line.split()[0] if line.split() else "shell"
                        tools.append(ToolUsage(
                            tool=tool_name,
                            purpose=f"Execute shell command: {line[:50]}...",
                            input_pattern=line[:200],
                            output_handling="Process command output"
                        ))
            elif lang in ["python", "py"]:
                # Look for function calls or imports
                if "import" in code or "def " in code or "class " in code:
                    tools.append(ToolUsage(
                        tool="python",
                        purpose="Execute Python code",
                        input_pattern=code[:200],
                        output_handling="Evaluate Python result"
                    ))

        # Find Claude Code tool invocations
        tool_invoke_pattern = r"(?:using|with|invoke|calling)\s+(?:the\s+)?(Read|Write|Bash|Glob|Grep|Edit|WebFetch)\s+(?:tool)?"
        for match in re.finditer(tool_invoke_pattern, response, re.IGNORECASE):
            tool_name = match.group(1)
            tools.append(ToolUsage(
                tool=tool_name,
                purpose=f"Claude Code {tool_name} operation",
                input_pattern="",
                output_handling="Process tool output"
            ))

        # Deduplicate by tool name
        seen_tools = set()
        unique_tools = []
        for tool in tools:
            key = f"{tool.tool}:{tool.input_pattern[:50]}"
            if key not in seen_tools:
                seen_tools.add(key)
                unique_tools.append(tool)

        return unique_tools[:10]  # Max 10 tools

    def _extract_corrections(
        self,
        sam_attempt: str,
        claude_response: str
    ) -> Optional[Corrections]:
        """Extract corrections Claude made to SAM's response."""
        sam_errors = []
        improvements = []

        # Check if Claude is correcting something
        correction_found = False
        for pattern in self.CORRECTION_INDICATORS:
            if re.search(pattern, claude_response, re.IGNORECASE):
                correction_found = True
                break

        if not correction_found:
            return None

        # Determine error type
        error_type = "general"
        for etype, patterns in self.ERROR_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, claude_response, re.IGNORECASE):
                    error_type = etype
                    break
            if error_type != "general":
                break

        # Extract what was wrong
        what_was_wrong = ""
        wrong_patterns = [
            r"(?:The (?:issue|problem) (?:is|with) )(.+?)(?:\.|$)",
            r"(?:This (?:won't|doesn't) work because )(.+?)(?:\.|$)",
            r"(?:However|But|Actually),?\s+(.+?)(?:\.|$)",
        ]
        for pattern in wrong_patterns:
            match = re.search(pattern, claude_response, re.IGNORECASE)
            if match:
                what_was_wrong = match.group(1).strip()[:300]
                break

        if not what_was_wrong:
            what_was_wrong = "Response needed improvement or correction"

        # Create the error record
        sam_errors.append(SamError(
            error_type=error_type,
            what_sam_said=sam_attempt[:500] if sam_attempt else "",
            what_was_wrong=what_was_wrong,
            correct_answer=claude_response[:500]  # Summary of correct approach
        ))

        # Extract improvement suggestions
        improvement_patterns = [
            r"(?:should|could|would|better to)\s+(.+?)(?:\.|$)",
            r"(?:instead|rather)[,]?\s+(.+?)(?:\.|$)",
            r"(?:A better (?:approach|way) (?:is|would be) to )\s*(.+?)(?:\.|$)",
        ]
        for pattern in improvement_patterns:
            for match in re.finditer(pattern, claude_response, re.IGNORECASE):
                improvement = match.group(1).strip()
                if len(improvement) > 20 and improvement not in improvements:
                    improvements.append(improvement[:200])
                    if len(improvements) >= 5:
                        break

        return Corrections(
            sam_errors=sam_errors,
            improvements=improvements
        )

    def _extract_principles(
        self,
        response: str,
        domain: str
    ) -> List[ExtractedPrinciple]:
        """Extract principles/guidelines from the response."""
        principles = []

        for pattern in self.PRINCIPLE_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                principle_text = match.strip()
                if len(principle_text) > 20 and len(principle_text) < 300:
                    # Calculate importance based on emphasis words
                    importance = 0.5
                    if any(w in principle_text.lower() for w in ["always", "never", "critical", "important"]):
                        importance = 0.9
                    elif any(w in principle_text.lower() for w in ["should", "best practice", "recommended"]):
                        importance = 0.7
                    elif any(w in principle_text.lower() for w in ["usually", "typically", "generally"]):
                        importance = 0.6

                    principles.append(ExtractedPrinciple(
                        principle=principle_text,
                        context=domain,
                        importance=importance
                    ))

        # Deduplicate by content similarity
        seen = set()
        unique = []
        for p in principles:
            key = p.principle[:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique[:5]  # Max 5 principles

    def _calculate_complexity(
        self,
        response: str,
        steps: List[ReasoningStep],
        tools: List[ToolUsage]
    ) -> int:
        """Calculate complexity score (1-10)."""
        complexity = 1

        # Word count factor
        word_count = len(response.split())
        if word_count > 500:
            complexity += 2
        elif word_count > 200:
            complexity += 1

        # Step count factor
        complexity += min(3, len(steps) // 2)

        # Tool usage factor
        complexity += min(2, len(tools))

        # Code block factor
        code_blocks = len(re.findall(r"```", response))
        if code_blocks >= 4:
            complexity += 2
        elif code_blocks >= 2:
            complexity += 1

        return min(10, complexity)

    def _calculate_confidence(
        self,
        reasoning_type: ReasoningType,
        steps: List[ReasoningStep],
        tools: List[ToolUsage],
        corrections: Optional[Corrections]
    ) -> float:
        """Calculate confidence in the extraction (0.0-1.0)."""
        confidence = 0.5  # Base confidence

        # Strong type indicators increase confidence
        if reasoning_type == ReasoningType.TOOL_USE and len(tools) > 0:
            confidence += 0.2
        elif reasoning_type == ReasoningType.CHAIN_OF_THOUGHT and len(steps) >= 3:
            confidence += 0.2
        elif reasoning_type == ReasoningType.CORRECTION and corrections:
            confidence += 0.25  # Corrections are high-value

        # Number of extracted elements
        if len(steps) >= 2:
            confidence += 0.1
        if len(tools) >= 1:
            confidence += 0.1

        return min(1.0, confidence)

    def to_dict(self, pattern: ReasoningPattern) -> Dict[str, Any]:
        """Convert ReasoningPattern to dictionary for storage."""
        return {
            "reasoning_type": pattern.reasoning_type.value,
            "reasoning_steps": [asdict(s) for s in pattern.reasoning_steps],
            "tool_usage": [asdict(t) for t in pattern.tool_usage],
            "corrections": {
                "sam_errors": [asdict(e) for e in pattern.corrections.sam_errors],
                "improvements": pattern.corrections.improvements
            } if pattern.corrections else None,
            "principles": [asdict(p) for p in pattern.principles],
            "complexity": pattern.complexity,
            "confidence": pattern.confidence
        }


class SyntheticDataGenerator:
    """Generates synthetic training data using Claude"""

    def __init__(self, bridge_path: Optional[Path] = None):
        self.bridge_path = bridge_path or Path.home() / "ReverseLab/SAM/warp_tauri/ai_bridge.cjs"
        self.db = DistillationDB()

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude via browser bridge"""
        if not self.bridge_path.exists():
            print(f"Bridge not found at {self.bridge_path}")
            return None

        try:
            cmd = ["node", str(self.bridge_path), "send", prompt, "--claude"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(self.bridge_path.parent)
            )

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    return data.get("response", result.stdout)
                except:
                    return result.stdout
        except Exception as e:
            print(f"Claude call failed: {e}")

        return None

    def generate_cot_examples(self, domain: str, count: int = 10) -> int:
        """Generate chain-of-thought examples for a domain"""

        prompts = {
            "code": [
                "Walk me through step by step how you would implement a binary search tree in Python.",
                "Explain your reasoning process for debugging a memory leak in a Node.js application.",
                "Think through how you would design a rate limiter for an API.",
                "Show your thought process for optimizing a slow database query.",
                "Walk through how you would implement OAuth2 authentication from scratch.",
            ],
            "reasoning": [
                "A farmer has 17 sheep. All but 9 run away. How many are left? Think step by step.",
                "If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100? Explain your reasoning.",
                "There are 3 boxes: one with apples, one with oranges, one with both. All labels are wrong. You can pick one fruit from one box. How do you label them correctly?",
            ],
            "creative": [
                "Walk me through your creative process for writing a compelling opening scene for a thriller novel.",
                "Explain step by step how you would develop a complex antagonist character.",
                "Show your reasoning for building tension in a romance subplot.",
            ],
            "analysis": [
                "Walk through your analysis process for evaluating whether a startup idea is viable.",
                "Explain your systematic approach to reviewing code for security vulnerabilities.",
                "Show your reasoning for deciding between microservices vs monolith architecture.",
            ]
        }

        domain_prompts = prompts.get(domain, prompts["reasoning"])
        generated = 0

        for i in range(count):
            prompt = random.choice(domain_prompts)
            # Add variation
            prompt = prompt.replace("step by step", random.choice([
                "step by step", "systematically", "methodically", "carefully"
            ]))

            print(f"Generating CoT example {i+1}/{count}...")
            response = self._call_claude(prompt)

            if response:
                extractor = ChainOfThoughtExtractor()
                cot = extractor.extract(prompt, response, domain)

                if cot and len(cot.reasoning_steps) >= 2:
                    self.db.store_cot(cot)
                    generated += 1
                    print(f"  ✓ Extracted {len(cot.reasoning_steps)} reasoning steps")
                else:
                    print(f"  ✗ Could not extract reasoning chain")

            time.sleep(2)  # Rate limit

        print(f"\n✅ Generated {generated} chain-of-thought examples for {domain}")
        return generated

    def generate_preference_pairs(self, domain: str, count: int = 10) -> int:
        """Generate good/bad response pairs for preference learning"""

        prompts = {
            "code": [
                "Write a function to check if a string is a palindrome",
                "Implement a simple HTTP server in Python",
                "Create a function to find duplicates in an array",
            ],
            "creative": [
                "Write the opening paragraph of a mystery novel",
                "Describe a sunset in an emotionally evocative way",
                "Write dialogue between two characters meeting for the first time",
            ],
            "helpful": [
                "Explain quantum computing to a 10 year old",
                "Give me advice for public speaking",
                "Help me plan a productive morning routine",
            ]
        }

        domain_prompts = prompts.get(domain, prompts["helpful"])
        generated = 0

        for i in range(count):
            base_prompt = random.choice(domain_prompts)

            print(f"Generating preference pair {i+1}/{count}...")

            # Get a good response
            good_prompt = f"""Please give an excellent, high-quality response to this:

{base_prompt}

Take your time and give your best answer."""

            good_response = self._call_claude(good_prompt)
            if not good_response:
                continue

            time.sleep(1)

            # Get a deliberately worse response
            bad_prompt = f"""Give a mediocre, somewhat helpful but not great response to this:

{base_prompt}

Be somewhat vague, miss some details, and don't be as thorough as you could be. Still be somewhat helpful, just not excellent."""

            bad_response = self._call_claude(bad_prompt)
            if not bad_response:
                continue

            # Store the pair
            pair = PreferencePair(
                id=hashlib.md5(f"{base_prompt}{time.time()}".encode()).hexdigest()[:12],
                prompt=base_prompt,
                good_response=good_response,
                bad_response=bad_response,
                reason="Good response is more thorough, specific, and helpful",
                domain=domain
            )

            self.db.store_preference(pair)
            generated += 1
            print(f"  ✓ Created preference pair")

            time.sleep(2)

        print(f"\n✅ Generated {generated} preference pairs for {domain}")
        return generated

    def extract_skill_templates(self) -> int:
        """Analyze raw interactions to extract reusable skill templates"""

        conn = sqlite3.connect(self.db.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT prompt, response, domain FROM raw_interactions
            WHERE processed = 0 AND quality_score > 0.7
            LIMIT 100
        """)

        rows = cur.fetchall()
        conn.close()

        skills_found = 0

        # Common skill patterns to look for
        skill_patterns = {
            "step_by_step": {
                "pattern": r"(Step \d|First.*Second.*Third|\d\.\s+.*\d\.\s+)",
                "name": "Sequential Problem Solving",
                "description": "Breaking down a problem into ordered steps"
            },
            "comparison": {
                "pattern": r"(On one hand.*on the other|Pros:.*Cons:|advantages.*disadvantages)",
                "name": "Comparative Analysis",
                "description": "Comparing multiple options or perspectives"
            },
            "code_review": {
                "pattern": r"(```[\s\S]+```.*(?:issue|problem|improve|better))",
                "name": "Code Review",
                "description": "Analyzing and suggesting improvements to code"
            },
            "explanation": {
                "pattern": r"(In simple terms|Think of it like|Imagine|For example)",
                "name": "Concept Explanation",
                "description": "Making complex concepts accessible"
            }
        }

        for prompt, response, domain in rows:
            for skill_id, skill_info in skill_patterns.items():
                if re.search(skill_info["pattern"], response, re.IGNORECASE):
                    # Found a skill pattern
                    skill = SkillTemplate(
                        id=skill_id,
                        name=skill_info["name"],
                        description=skill_info["description"],
                        pattern=skill_info["pattern"],
                        examples=[{
                            "prompt": prompt[:200],
                            "response_snippet": response[:500]
                        }],
                        domains=[domain]
                    )

                    self.db.store_skill(skill)
                    skills_found += 1

        print(f"✅ Extracted {skills_found} skill template instances")
        return skills_found


def export_for_training(output_path: Path = EXPORT_PATH / "distilled_training.jsonl"):
    """Export all distilled knowledge to JSONL training format"""
    db = DistillationDB()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db.db_path)
    count = 0

    with open(output_path, "w") as f:
        # Chain of thought examples (instruction format)
        cur = conn.cursor()
        cur.execute("SELECT * FROM chain_of_thought WHERE success = 1")

        for row in cur.fetchall():
            steps = json.loads(row[2])
            example = {
                "instruction": row[1],  # prompt
                "input": "",
                "output": f"Let me think through this step by step:\n\n" +
                         "\n\n".join(f"{i+1}. {step}" for i, step in enumerate(steps)) +
                         f"\n\nTherefore: {row[3]}",
                "type": "chain_of_thought",
                "domain": row[4]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

        # Preference pairs (DPO format)
        cur.execute("SELECT * FROM preference_pairs")

        for row in cur.fetchall():
            example = {
                "prompt": row[1],
                "chosen": row[2],  # good response
                "rejected": row[3],  # bad response
                "type": "preference",
                "domain": row[5]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

        # Principles (as instruction examples)
        cur.execute("SELECT * FROM principles WHERE source_count > 1")

        for row in cur.fetchall():
            examples = json.loads(row[3])
            example = {
                "instruction": f"What's an important principle for {row[1]}?",
                "input": "",
                "output": row[2],
                "type": "principle",
                "domain": row[1]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

    conn.close()
    print(f"Exported {count} examples to {output_path}")
    return count


def test_reasoning_extractor():
    """Test the ReasoningPatternExtractor with sample responses."""
    extractor = ReasoningPatternExtractor()

    # Test 1: Chain-of-thought response
    cot_response = """Let me think through this step by step.

First, we need to identify the source of the error. The TypeError indicates we're calling .map() on undefined.

Second, let's trace where this data comes from. Looking at the component, it's fetched from an API but used before the response arrives.

Third, we should add a loading state to handle the async nature:

```javascript
const [data, setData] = useState([]);
const [loading, setLoading] = useState(true);
```

Finally, we can render conditionally based on the loading state.

Therefore, the fix involves proper state initialization and loading handling."""

    print("\n" + "="*60)
    print("TEST 1: Chain-of-Thought Detection")
    print("="*60)
    pattern = extractor.extract(
        query="How do I fix TypeError: Cannot read properties of undefined?",
        claude_response=cot_response,
        domain="code"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    print(f"Steps Extracted: {len(pattern.reasoning_steps)}")
    for step in pattern.reasoning_steps[:3]:
        print(f"  - Step {step.step_num}: {step.action} - {step.content[:60]}...")
    print(f"Complexity: {pattern.complexity}")
    print(f"Confidence: {pattern.confidence:.2f}")

    # Test 2: Tool use response
    tool_response = """I'll help you find the file. Let me search for it.

Using the Glob tool to find Python files:

```bash
find . -name "*.py" -type f
```

Then I'll read the contents with the Read tool.

```python
with open(filepath, 'r') as f:
    content = f.read()
```

The file is located at ./src/utils/helpers.py."""

    print("\n" + "="*60)
    print("TEST 2: Tool Use Detection")
    print("="*60)
    pattern = extractor.extract(
        query="Find the helpers file in my project",
        claude_response=tool_response,
        domain="code"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    print(f"Tools Detected: {len(pattern.tool_usage)}")
    for tool in pattern.tool_usage:
        print(f"  - {tool.tool}: {tool.purpose[:50]}...")

    # Test 3: Correction response
    sam_attempt = "The time complexity is O(n) because it goes through the array once."
    correction_response = """Actually, that's not quite right. The time complexity analysis is more nuanced.

The issue with your answer is that quicksort involves recursive partitioning, not just a single pass.

The correct analysis is:
- **Average case**: O(n log n) - partitioning at each level is O(n), with log n levels
- **Worst case**: O(n^2) - happens with already sorted arrays or bad pivot selection
- **Best case**: O(n log n)

You should always consider the recursive structure when analyzing divide-and-conquer algorithms.

Remember that a single partition is O(n), but the algorithm requires multiple levels of recursion."""

    print("\n" + "="*60)
    print("TEST 3: Correction Detection")
    print("="*60)
    pattern = extractor.extract(
        query="What's the time complexity of quicksort?",
        claude_response=correction_response,
        sam_attempt=sam_attempt,
        domain="reasoning"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    if pattern.corrections:
        print(f"Corrections Found: {len(pattern.corrections.sam_errors)} error(s)")
        for err in pattern.corrections.sam_errors:
            print(f"  - Error Type: {err.error_type}")
            print(f"  - What was wrong: {err.what_was_wrong[:80]}...")
        print(f"Improvements: {len(pattern.corrections.improvements)}")
        for imp in pattern.corrections.improvements[:2]:
            print(f"  - {imp[:60]}...")
    print(f"Principles Extracted: {len(pattern.principles)}")
    for p in pattern.principles:
        print(f"  - {p.principle[:60]}... (importance: {p.importance})")

    # Test 4: Meta-cognitive response
    meta_response = """I'm not entirely sure, but I believe the answer involves quantum entanglement.

Let me reconsider this. My understanding is that quantum states are correlated, but I may be oversimplifying.

To be clear, I should clarify that this is a complex topic with ongoing research. The current consensus suggests that entanglement enables correlation without classical communication, but I'm uncertain about the specific mechanisms.

If I'm wrong about any details, please correct me."""

    print("\n" + "="*60)
    print("TEST 4: Meta-Cognitive Detection")
    print("="*60)
    pattern = extractor.extract(
        query="Explain quantum entanglement",
        claude_response=meta_response,
        domain="factual"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    print(f"Complexity: {pattern.complexity}")
    print(f"Confidence: {pattern.confidence:.2f}")

    # Test 5: Direct response
    direct_response = """The capital of France is Paris."""

    print("\n" + "="*60)
    print("TEST 5: Direct Answer Detection")
    print("="*60)
    pattern = extractor.extract(
        query="What is the capital of France?",
        claude_response=direct_response,
        domain="factual"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    print(f"Steps: {len(pattern.reasoning_steps)}")
    print(f"Complexity: {pattern.complexity}")

    # Test 6: Multi-step response
    multi_step_response = """This requires several steps to complete properly.

Part 1: Database Setup
- Install PostgreSQL
- Create the database schema
- Set up migrations

Part 2: Backend Implementation
- Create REST API endpoints
- Implement authentication
- Add data validation

Part 3: Frontend Integration
- Build React components
- Connect to API
- Handle state management

Part 4: Deployment
- Configure Docker containers
- Set up CI/CD pipeline
- Deploy to production

Each phase builds on the previous one."""

    print("\n" + "="*60)
    print("TEST 6: Multi-Step Detection")
    print("="*60)
    pattern = extractor.extract(
        query="How do I build a full-stack application?",
        claude_response=multi_step_response,
        domain="code"
    )
    print(f"Reasoning Type: {pattern.reasoning_type.value}")
    print(f"Steps Extracted: {len(pattern.reasoning_steps)}")
    print(f"Complexity: {pattern.complexity}")

    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)


def test_quality_filter():
    """Test the QualityFilter with various example types."""
    filter = QualityFilter()
    extractor = ReasoningPatternExtractor()

    print("\n" + "="*60)
    print("  QUALITY FILTER TESTS")
    print("="*60)

    # Test 1: Too short response (should reject)
    print("\n[TEST 1] Too Short Response")
    result = filter.filter(
        query="What is Python?",
        response="Python is a language."
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Reason: {result.rejection_reason}")
    print(f"  Flags: {result.quality_flags}")
    assert not result.accepted, "Should reject too-short responses"

    # Test 2: Repetitive response (should reject)
    print("\n[TEST 2] Repetitive Response")
    repetitive = "This is the answer. " * 20  # Very repetitive
    result = filter.filter(
        query="Tell me about programming",
        response=repetitive
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Reason: {result.rejection_reason}")
    assert not result.accepted, "Should reject repetitive responses"

    # Test 3: Refusal response (should reject)
    print("\n[TEST 3] Refusal Response")
    result = filter.filter(
        query="How do I hack a website?",
        response="I can't help with that request. I won't assist with hacking or breaking into systems."
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Reason: {result.rejection_reason}")
    assert not result.accepted, "Should reject refusal responses"

    # Test 4: High-quality response with reasoning (should accept)
    print("\n[TEST 4] High-Quality Response with Reasoning")
    good_response = """Let me explain how binary search works step by step.

First, we start with a sorted array. This is a key prerequisite.

Second, we find the middle element and compare it to our target.

Third, if the middle element matches, we're done. If the target is smaller,
we search the left half. If larger, we search the right half.

Finally, we repeat this process until we find the element or exhaust the search space.

The key principle here is: Always ensure your array is sorted before using binary search.

Here's a Python implementation:

```python
def binary_search(arr, target):
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
```

This gives us O(log n) time complexity, which is much better than linear search."""

    pattern = extractor.extract(
        query="Explain binary search",
        claude_response=good_response,
        domain="code"
    )
    result = filter.filter(
        query="Explain binary search",
        response=good_response,
        pattern=pattern
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Flags: {result.quality_flags}")
    assert result.accepted, "Should accept high-quality responses"
    assert result.quality_score >= 0.6, "Should have good quality score"

    # Test 5: Correction response (highest value - should accept with high score)
    print("\n[TEST 5] Correction Response (SAM Attempt Provided)")
    sam_attempt = "Binary search has O(n) complexity."
    correction_response = """Actually, that's not quite right. Binary search has O(log n) complexity, not O(n).

The issue with your answer is that binary search doesn't scan every element. Instead, it divides
the search space in half with each comparison.

Here's why: if you have n elements, after one comparison you have n/2 left. After two, n/4.
After k comparisons, you have n/2^k elements. When this equals 1, k = log2(n).

Therefore, the correct time complexity is O(log n).

Remember that logarithmic complexity is much faster than linear for large datasets.
For example, searching 1 million elements takes at most 20 comparisons with binary search,
but could take 1 million with linear search."""

    pattern = extractor.extract(
        query="What's the complexity of binary search?",
        claude_response=correction_response,
        sam_attempt=sam_attempt,
        domain="code"
    )
    result = filter.filter(
        query="What's the complexity of binary search?",
        response=correction_response,
        pattern=pattern,
        sam_attempt=sam_attempt
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Flags: {result.quality_flags}")
    assert result.accepted, "Should accept correction responses"
    assert result.quality_score >= 0.7, "Corrections should have high quality score"

    # Test 6: Direct answer (should accept but with lower score)
    print("\n[TEST 6] Direct Answer (Simple)")
    result = filter.filter(
        query="What is the capital of France?",
        response="The capital of France is Paris. It has been the capital since the 10th century and is home to famous landmarks like the Eiffel Tower and the Louvre."
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Flags: {result.quality_flags}")
    # Might be accepted or rejected depending on threshold

    # Test 7: Code-only response (should have penalty)
    print("\n[TEST 7] Code-Only Response")
    code_only = """```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```"""
    result = filter.filter(
        query="Write a fibonacci function",
        response=code_only
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Flags: {result.quality_flags}")
    assert 'code_only' in result.quality_flags, "Should flag code-only responses"

    # Test 8: Incomplete response (should penalize)
    print("\n[TEST 8] Incomplete Response")
    incomplete = """Here are the main steps to set up a server:

1. Choose your operating system
2. Install necessary software
3. Configure networking...

etc. and so on"""
    result = filter.filter(
        query="How do I set up a server?",
        response=incomplete
    )
    print(f"  Accepted: {result.accepted}")
    print(f"  Score: {result.quality_score:.2f}")
    print(f"  Flags: {result.quality_flags}")
    assert 'incomplete' in result.quality_flags, "Should flag incomplete responses"

    # Print final statistics
    print("\n" + "="*60)
    print("  FILTER STATISTICS")
    print("="*60)
    stats = filter.get_stats()
    print(f"  Total Processed: {stats['total_processed']}")
    print(f"  Accepted: {stats['total_accepted']}")
    print(f"  Rejected: {stats['total_rejected']}")
    print(f"  Rejection Rate: {stats['rejection_rate']:.1%}")
    print(f"  Avg Quality Score: {stats['average_quality_score']:.2f}")
    print("\n  Rejection Reasons:")
    for reason, count in stats['rejection_reasons'].items():
        print(f"    - {reason}: {count}")

    # Verify we're meeting the >20% rejection target
    print("\n" + "="*60)
    if stats['rejection_rate'] >= 0.2:
        print("  [PASS] Meeting >20% rejection target!")
    else:
        print(f"  [INFO] Rejection rate: {stats['rejection_rate']:.1%}")
        print("         Target is >20% - may need tuning based on real data")
    print("="*60)

    print("\nAll quality filter tests completed!")


# ===== INTERACTIVE REVIEW INTERFACE =====

def _color_quality_score(score: float) -> str:
    """Return color-coded quality score string (ANSI colors)."""
    if score >= 0.7:
        return f"\033[92m{score:.2f}\033[0m"  # Green
    elif score >= 0.4:
        return f"\033[93m{score:.2f}\033[0m"  # Yellow
    else:
        return f"\033[91m{score:.2f}\033[0m"  # Red


def _print_review_item(item: Dict, index: int = 0):
    """Print a formatted review item."""
    print(f"\n[{index}] ID: {item['id']}")
    print(f"    Domain: {item['domain']} | Type: {item.get('reasoning_type', 'N/A')} | Priority: {item['priority']}")
    print(f"    Reason: {item['review_reason']}")
    print(f"    Quality Score: {_color_quality_score(item['quality_score'])}")
    print(f"\n    \033[1mQUERY:\033[0m {item['query'][:200]}{'...' if len(item['query']) > 200 else ''}")

    if item.get('sam_attempt'):
        print(f"\n    \033[93mSAM SAID:\033[0m {item['sam_attempt'][:200]}{'...' if len(item['sam_attempt']) > 200 else ''}")

    print(f"\n    \033[94mCLAUDE:\033[0m {item['claude_response'][:300]}{'...' if len(item['claude_response']) > 300 else ''}")
    print("-" * 60)


def _print_example_details(example: Dict):
    """Print full details of an example with all extracted patterns."""
    print(f"\n{'='*70}")
    print(f"  EXAMPLE DETAILS: {example['id']}")
    print(f"{'='*70}")

    # Basic info
    print(f"\n  \033[1m--- Basic Info ---\033[0m")
    print(f"  Domain: {example['domain']}")
    print(f"  Reasoning Type: {example.get('reasoning_type', 'N/A')}")
    print(f"  Quality Score: {_color_quality_score(example['quality_score'])}")
    print(f"  Complexity: {example.get('complexity', 'N/A')}/10")
    print(f"  Human Reviewed: {'Yes' if example.get('human_reviewed') else 'No'}")
    print(f"  Approved: {'Yes' if example.get('approved') else 'No'}")
    if example.get('review_reason'):
        print(f"  Review Reason: {example['review_reason']}")
    if example.get('reviewer_notes'):
        print(f"  Reviewer Notes: {example['reviewer_notes']}")

    # Query
    print(f"\n  \033[1m--- Query ---\033[0m")
    print(f"  {example['query']}")

    # SAM's attempt (if correction)
    if example.get('sam_attempt'):
        print(f"\n  \033[93m--- SAM's Attempt ---\033[0m")
        print(f"  {example['sam_attempt']}")

    # Claude's response
    print(f"\n  \033[94m--- Claude's Response ---\033[0m")
    # Wrap long responses
    response = example['claude_response']
    if len(response) > 1000:
        print(f"  {response[:1000]}...")
        print(f"\n  [Response truncated - {len(response)} chars total]")
    else:
        print(f"  {response}")

    # Reasoning pattern
    if example.get('reasoning_pattern'):
        pattern = example['reasoning_pattern']
        print(f"\n  \033[1m--- Extracted Reasoning Pattern ---\033[0m")
        print(f"  Type: {pattern.get('reasoning_type', 'N/A')}")
        print(f"  Complexity: {pattern.get('complexity', 'N/A')}/10")
        print(f"  Confidence: {pattern.get('confidence', 0):.2f}")

        steps = pattern.get('reasoning_steps', [])
        if steps:
            print(f"\n  Reasoning Steps ({len(steps)}):")
            for step in steps[:5]:
                if isinstance(step, dict):
                    print(f"    {step.get('step_num', '?')}. [{step.get('action', 'N/A')}] {step.get('content', '')[:60]}...")
            if len(steps) > 5:
                print(f"    ... and {len(steps) - 5} more steps")

        tools = pattern.get('tool_usage', [])
        if tools:
            print(f"\n  Tool Usage ({len(tools)}):")
            for tool in tools[:3]:
                if isinstance(tool, dict):
                    print(f"    - {tool.get('tool', 'N/A')}: {tool.get('purpose', '')[:50]}...")

    # Corrections
    if example.get('corrections'):
        print(f"\n  \033[91m--- Corrections (High Value!) ---\033[0m")
        for i, correction in enumerate(example['corrections'], 1):
            print(f"\n  [{i}] Error Type: {correction.get('error_type', 'N/A')}")
            print(f"      SAM Said: {correction.get('what_sam_said', 'N/A')[:100]}...")
            print(f"      What Was Wrong: {correction.get('what_was_wrong', 'N/A')[:100]}...")
            print(f"      Correct Answer: {correction.get('correct_answer', 'N/A')[:100]}...")

    # Principles
    if example.get('principles'):
        print(f"\n  \033[1m--- Extracted Principles ---\033[0m")
        for p in example['principles']:
            print(f"    - {p.get('principle', 'N/A')[:80]}...")

    print(f"\n{'='*70}")


def _getch():
    """Read a single character from stdin without requiring Enter."""
    import sys
    import tty
    import termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def _interactive_review(db: 'DistillationDB', domain: Optional[str] = None):
    """Run interactive review mode with single-keypress commands."""
    print(f"\n{'='*70}")
    print(f"  INTERACTIVE REVIEW MODE")
    print(f"{'='*70}")
    print(f"\n  Commands:")
    print(f"    \033[92ma\033[0m = Approve      \033[91mr\033[0m = Reject      \033[93ms\033[0m = Skip")
    print(f"    \033[94md\033[0m = Details      \033[95mn\033[0m = Notes        q = Quit")
    print(f"\n  Press any key to start...")
    _getch()

    approved_count = 0
    rejected_count = 0
    skipped_count = 0

    while True:
        # Get next pending example
        pending = db.get_pending_review(limit=1, domain=domain)

        if not pending:
            print(f"\n  No more examples pending review!")
            break

        item = pending[0]

        # Clear screen and show example
        print("\033[2J\033[H")  # Clear screen
        print(f"{'='*70}")
        print(f"  REVIEW: {item['id']}  |  Approved: {approved_count}  Rejected: {rejected_count}  Skipped: {skipped_count}")
        print(f"{'='*70}")

        # Show condensed view
        print(f"\n  Domain: {item['domain']} | Type: {item.get('reasoning_type', 'N/A')}")
        print(f"  Quality: {_color_quality_score(item['quality_score'])} | Priority: {item['priority']}")
        if item.get('review_reason'):
            print(f"  Reason: {item['review_reason']}")

        # Correction indicator
        if item.get('sam_attempt'):
            print(f"\n  \033[91m*** CORRECTION EXAMPLE (High Value) ***\033[0m")

        # Query
        print(f"\n  \033[1mQUERY:\033[0m")
        query = item['query']
        if len(query) > 300:
            print(f"  {query[:300]}...")
        else:
            print(f"  {query}")

        # SAM's attempt
        if item.get('sam_attempt'):
            print(f"\n  \033[93mSAM SAID:\033[0m")
            sam = item['sam_attempt']
            if len(sam) > 250:
                print(f"  {sam[:250]}...")
            else:
                print(f"  {sam}")

        # Claude's response
        print(f"\n  \033[94mCLAUDE:\033[0m")
        response = item['claude_response']
        if len(response) > 400:
            print(f"  {response[:400]}...")
        else:
            print(f"  {response}")

        print(f"\n{'-'*70}")
        print(f"  [\033[92ma\033[0m]pprove  [\033[91mr\033[0m]eject  [\033[93ms\033[0m]kip  [\033[94md\033[0m]etails  [\033[95mn\033[0m]otes  [q]uit")
        print(f"  > ", end='', flush=True)

        # Get command
        cmd = _getch().lower()
        print(cmd)  # Echo the key

        if cmd == 'a':
            # Approve
            if db.approve_example(item['id'], notes="Approved via interactive review"):
                approved_count += 1
                print(f"  \033[92mApproved!\033[0m")
            else:
                print(f"  \033[91mFailed to approve\033[0m")
            import time
            time.sleep(0.3)

        elif cmd == 'r':
            # Reject
            if db.reject_example(item['id'], reason="Rejected via interactive review"):
                rejected_count += 1
                print(f"  \033[91mRejected!\033[0m")
            else:
                print(f"  \033[91mFailed to reject\033[0m")
            import time
            time.sleep(0.3)

        elif cmd == 's':
            # Skip - we just move on (it stays pending)
            skipped_count += 1
            print(f"  \033[93mSkipped\033[0m")
            import time
            time.sleep(0.3)
            # Skip by getting next, but we need to handle this differently
            # Since we can't really skip in the queue, we'll show a different one
            # by getting more items

        elif cmd == 'd':
            # Show full details
            details = db.get_example_details(item['id'])
            if details:
                print("\033[2J\033[H")  # Clear screen
                _print_example_details(details)
                print(f"\n  Press any key to return...")
                _getch()

        elif cmd == 'n':
            # Add notes before approve/reject
            print(f"\n  Enter notes (then press Enter): ", end='')
            import sys
            # Restore normal terminal mode for input
            notes = input()
            print(f"\n  Notes saved. Now [\033[92ma\033[0m]pprove or [\033[91mr\033[0m]eject with these notes?")
            print(f"  > ", end='', flush=True)
            action = _getch().lower()
            print(action)
            if action == 'a':
                if db.approve_example(item['id'], notes=notes):
                    approved_count += 1
                    print(f"  \033[92mApproved with notes!\033[0m")
            elif action == 'r':
                if db.reject_example(item['id'], reason=notes):
                    rejected_count += 1
                    print(f"  \033[91mRejected with notes!\033[0m")
            import time
            time.sleep(0.5)

        elif cmd == 'q' or cmd == '\x03':  # q or Ctrl+C
            break

    # Summary
    print(f"\n{'='*70}")
    print(f"  SESSION COMPLETE")
    print(f"{'='*70}")
    print(f"  Approved: {approved_count}")
    print(f"  Rejected: {rejected_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"{'='*70}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Distillation Engine")
    subparsers = parser.add_subparsers(dest="command")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic training data")
    gen_parser.add_argument("--domain", default="code", help="Domain to generate for")
    gen_parser.add_argument("--count", type=int, default=10, help="Number to generate")
    gen_parser.add_argument("--type", choices=["cot", "preference"], default="cot",
                           help="Type of data to generate")

    # Extract command
    subparsers.add_parser("extract-principles", help="Extract principles from interactions")

    # Export command
    exp_parser = subparsers.add_parser("export", help="Export for training")
    exp_parser.add_argument("--output", default=str(EXPORT_PATH / "distilled_training.jsonl"))

    # Status command
    subparsers.add_parser("status", help="Show distillation status")

    # Extract reasoning command
    ext_parser = subparsers.add_parser("extract-reasoning", help="Extract reasoning pattern from text")
    ext_parser.add_argument("--query", required=True, help="The original query")
    ext_parser.add_argument("--response", required=True, help="Claude's response (or path to file)")
    ext_parser.add_argument("--sam-attempt", help="SAM's initial attempt (enables correction detection)")
    ext_parser.add_argument("--domain", default="general", help="Domain: code, reasoning, creative, factual, planning")
    ext_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Test command
    subparsers.add_parser("test", help="Run reasoning extractor tests")

    # Test filter command
    subparsers.add_parser("test-filter", help="Run quality filter tests")

    # Filter stats command
    subparsers.add_parser("filter-stats", help="Show quality filter statistics")

    # Review command - for human review workflow
    review_parser = subparsers.add_parser("review", help="Review pending examples")
    review_parser.add_argument("--limit", type=int, default=5, help="Number of examples to show")
    review_parser.add_argument("--domain", help="Filter by domain")
    review_parser.add_argument("--approve", help="Approve example by ID")
    review_parser.add_argument("--reject", help="Reject example by ID")
    review_parser.add_argument("--notes", help="Notes for approval/rejection")
    review_parser.add_argument("--interactive", "-i", action="store_true",
                               help="Interactive mode with single-keypress review")
    review_parser.add_argument("--auto-approve-above", type=float, metavar="SCORE",
                               help="Auto-approve all examples with quality >= SCORE (0.0-1.0)")
    review_parser.add_argument("--auto-reject-below", type=float, metavar="SCORE",
                               help="Auto-reject all examples with quality < SCORE (0.0-1.0)")
    review_parser.add_argument("--stats", action="store_true", help="Show review queue statistics")
    review_parser.add_argument("--details", help="Show full details for an example ID")

    args = parser.parse_args()

    if args.command == "generate":
        generator = SyntheticDataGenerator()
        if args.type == "cot":
            generator.generate_cot_examples(args.domain, args.count)
        else:
            generator.generate_preference_pairs(args.domain, args.count)

    elif args.command == "extract-principles":
        generator = SyntheticDataGenerator()
        generator.extract_skill_templates()

    elif args.command == "export":
        export_for_training(Path(args.output))

    elif args.command == "status":
        db = DistillationDB()
        stats = db.get_stats()

        print("\n" + "="*60)
        print("  KNOWLEDGE DISTILLATION STATUS")
        print("="*60)

        print(f"\n  Database: {stats['db_path']}")
        print(f"  External Drive: {'Mounted' if stats['using_external_drive'] else 'NOT MOUNTED (using local)'}")

        print("\n  --- Primary Training Data ---")
        print(f"  Total examples: {stats['total_examples']:,}")
        print(f"  Approved for training: {stats['approved_examples']:,}")
        print(f"  Awaiting review: {stats['unreviewed_examples']:,}")
        print(f"  Pending in queue: {stats['pending_review']:,}")

        print("\n  --- Extracted Patterns ---")
        print(f"  Reasoning patterns: {stats['reasoning_patterns']:,}")
        print(f"  Corrections (high-value): {stats['corrections']:,}")
        print(f"  Principles: {stats['principles']:,}")

        if stats.get('by_domain'):
            print("\n  --- By Domain ---")
            for domain, count in stats['by_domain'].items():
                print(f"    {domain}: {count:,}")

        if stats.get('by_reasoning_type'):
            print("\n  --- By Reasoning Type ---")
            for rtype, count in stats['by_reasoning_type'].items():
                print(f"    {rtype}: {count:,}")

        print("\n  --- Legacy Tables ---")
        print(f"  Chain of Thought: {stats['chain_of_thought']:,}")
        print(f"  Preference pairs: {stats['preference_pairs']:,}")
        print(f"  Skill templates: {stats['skill_templates']:,}")
        print(f"  Raw interactions: {stats['raw_interactions']:,} ({stats['unprocessed']:,} unprocessed)")

        # Quality filter stats
        print("\n  --- Quality Filter ---")
        print(f"  Filter rejections (DB): {stats.get('filter_rejections', 0):,}")
        if stats.get('quality_filter'):
            qf = stats['quality_filter']
            print(f"  Session processed: {qf.get('total_processed', 0):,}")
            print(f"  Session accepted: {qf.get('total_accepted', 0):,}")
            print(f"  Session rejected: {qf.get('total_rejected', 0):,}")
            if qf.get('total_processed', 0) > 0:
                print(f"  Session rejection rate: {qf.get('rejection_rate', 0):.1%}")
                print(f"  Avg quality score: {qf.get('average_quality_score', 0):.2f}")

    elif args.command == "test-filter":
        test_quality_filter()

    elif args.command == "filter-stats":
        db = DistillationDB()
        stats = db.get_filter_stats()

        print("\n" + "="*60)
        print("  QUALITY FILTER STATISTICS")
        print("="*60)

        print("\n  --- Session Stats ---")
        print(f"  Total Processed: {stats.get('total_processed', 0):,}")
        print(f"  Accepted: {stats.get('total_accepted', 0):,}")
        print(f"  Rejected: {stats.get('total_rejected', 0):,}")
        if stats.get('total_processed', 0) > 0:
            print(f"  Rejection Rate: {stats.get('rejection_rate', 0):.1%}")
            print(f"  Acceptance Rate: {stats.get('acceptance_rate', 0):.1%}")
            print(f"  Avg Quality Score: {stats.get('average_quality_score', 0):.2f}")

        print("\n  --- Session Rejection Reasons ---")
        reasons = stats.get('rejection_reasons', {})
        if reasons:
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"    {reason}: {count:,}")
        else:
            print("    No rejections this session")

        print("\n  --- Database Rejection History ---")
        print(f"  Total DB Rejections: {stats.get('db_rejections', 0):,}")
        print(f"  Avg Rejected Quality: {stats.get('avg_rejected_quality_score', 0):.2f}")

        db_breakdown = stats.get('db_rejection_breakdown', {})
        if db_breakdown:
            print("\n  DB Rejection Breakdown:")
            for reason, count in sorted(db_breakdown.items(), key=lambda x: -x[1]):
                print(f"    {reason}: {count:,}")

        # Check if meeting target
        print("\n" + "-"*60)
        rejection_rate = stats.get('rejection_rate', 0)
        if stats.get('total_processed', 0) >= 10:
            if rejection_rate >= 0.2:
                print(f"  [PASS] Meeting >20% rejection target ({rejection_rate:.1%})")
            else:
                print(f"  [WARN] Below 20% rejection target ({rejection_rate:.1%})")
                print("         Consider tuning filter thresholds")
        else:
            print("  [INFO] Not enough data to evaluate target (need 10+ examples)")

    elif args.command == "extract-reasoning":
        # Load response from file if it's a path
        response = args.response
        if Path(response).exists():
            response = Path(response).read_text()

        sam_attempt = args.sam_attempt
        if sam_attempt and Path(sam_attempt).exists():
            sam_attempt = Path(sam_attempt).read_text()

        extractor = ReasoningPatternExtractor()
        pattern = extractor.extract(
            query=args.query,
            claude_response=response,
            sam_attempt=sam_attempt,
            domain=args.domain
        )

        if args.json:
            print(json.dumps(extractor.to_dict(pattern), indent=2))
        else:
            print("\n" + "="*50)
            print("  REASONING PATTERN EXTRACTION")
            print("="*50)
            print(f"\n  Type: {pattern.reasoning_type.value}")
            print(f"  Complexity: {pattern.complexity}/10")
            print(f"  Confidence: {pattern.confidence:.2f}")
            print(f"\n  Reasoning Steps: {len(pattern.reasoning_steps)}")
            for step in pattern.reasoning_steps[:5]:
                print(f"    {step.step_num}. [{step.action}] {step.content[:60]}...")
            if len(pattern.reasoning_steps) > 5:
                print(f"    ... and {len(pattern.reasoning_steps) - 5} more")
            print(f"\n  Tool Usage: {len(pattern.tool_usage)}")
            for tool in pattern.tool_usage[:3]:
                print(f"    - {tool.tool}: {tool.purpose[:50]}...")
            if pattern.corrections:
                print(f"\n  Corrections: {len(pattern.corrections.sam_errors)} error(s)")
                for err in pattern.corrections.sam_errors:
                    print(f"    - Type: {err.error_type}")
                    print(f"      Issue: {err.what_was_wrong[:60]}...")
                print(f"  Improvements: {len(pattern.corrections.improvements)}")
            print(f"\n  Principles: {len(pattern.principles)}")
            for p in pattern.principles:
                print(f"    - {p.principle[:60]}... ({p.importance:.1f})")

    elif args.command == "test":
        test_reasoning_extractor()

    elif args.command == "review":
        db = DistillationDB()

        # Handle batch operations first
        if args.auto_approve_above is not None:
            threshold = args.auto_approve_above
            if not 0.0 <= threshold <= 1.0:
                print(f"Error: threshold must be between 0.0 and 1.0, got {threshold}")
                return
            result = db.batch_approve_above_threshold(threshold)
            print(f"\n{'='*60}")
            print(f"  AUTO-APPROVE COMPLETE")
            print(f"{'='*60}")
            print(f"\n  Threshold: >= {threshold:.2f}")
            print(f"  Approved: {result['approved_count']} examples")
            if result['ids']:
                print(f"\n  Approved IDs:")
                for eid in result['ids'][:10]:
                    score = result['scores'].get(eid, 0)
                    print(f"    - {eid} (score: {score:.2f})")
                if len(result['ids']) > 10:
                    print(f"    ... and {len(result['ids']) - 10} more")
            return

        if args.auto_reject_below is not None:
            threshold = args.auto_reject_below
            if not 0.0 <= threshold <= 1.0:
                print(f"Error: threshold must be between 0.0 and 1.0, got {threshold}")
                return
            result = db.batch_reject_below_threshold(threshold)
            print(f"\n{'='*60}")
            print(f"  AUTO-REJECT COMPLETE")
            print(f"{'='*60}")
            print(f"\n  Threshold: < {threshold:.2f}")
            print(f"  Rejected: {result['rejected_count']} examples")
            if result['ids']:
                print(f"\n  Rejected IDs:")
                for eid in result['ids'][:10]:
                    score = result['scores'].get(eid, 0)
                    print(f"    - {eid} (score: {score:.2f})")
                if len(result['ids']) > 10:
                    print(f"    ... and {len(result['ids']) - 10} more")
            return

        if args.stats:
            # Show review queue statistics
            stats = db.get_review_stats()
            print(f"\n{'='*60}")
            print(f"  REVIEW QUEUE STATISTICS")
            print(f"{'='*60}")
            print(f"\n  --- Queue Status ---")
            print(f"  Pending:  {stats['pending']:,}")
            print(f"  Approved: {stats['approved']:,}")
            print(f"  Rejected: {stats['rejected']:,}")

            print(f"\n  --- Pending by Quality ---")
            pbq = stats['pending_by_quality']
            print(f"    High (>= 0.7):    {pbq['high']:,}")
            print(f"    Medium (0.4-0.7): {pbq['medium']:,}")
            print(f"    Low (0.2-0.4):    {pbq['low']:,}")
            print(f"    Very Low (< 0.2): {pbq['very_low']:,}")

            if stats['pending_by_domain']:
                print(f"\n  --- Pending by Domain ---")
                for domain, count in stats['pending_by_domain'].items():
                    print(f"    {domain}: {count:,}")

            if stats['pending_by_type']:
                print(f"\n  --- Pending by Reasoning Type ---")
                for rtype, count in stats['pending_by_type'].items():
                    print(f"    {rtype}: {count:,}")

            print(f"\n  --- High-Value ---")
            print(f"  Corrections pending: {stats['pending_corrections']:,}")

            # Suggest batch operations
            if pbq['high'] > 0:
                print(f"\n  Tip: Auto-approve {pbq['high']} high-quality examples with:")
                print(f"       python knowledge_distillation.py review --auto-approve-above 0.7")
            if pbq['very_low'] > 0:
                print(f"\n  Tip: Auto-reject {pbq['very_low']} very low-quality examples with:")
                print(f"       python knowledge_distillation.py review --auto-reject-below 0.2")
            return

        if args.details:
            # Show full details for a specific example
            example = db.get_example_details(args.details)
            if not example:
                print(f"Example not found: {args.details}")
                return

            _print_example_details(example)
            return

        if args.approve:
            # Approve a specific example
            success = db.approve_example(args.approve, notes=args.notes)
            if success:
                print(f"Approved example: {args.approve}")
            else:
                print(f"Failed to approve example: {args.approve}")

        elif args.reject:
            # Reject a specific example
            success = db.reject_example(args.reject, reason=args.notes or "Rejected via CLI")
            if success:
                print(f"Rejected example: {args.reject}")
            else:
                print(f"Failed to reject example: {args.reject}")

        elif args.interactive:
            # Interactive review mode
            _interactive_review(db, domain=args.domain)

        else:
            # Show pending examples for review
            pending = db.get_pending_review(limit=args.limit, domain=args.domain)

            if not pending:
                print("No examples pending review.")
            else:
                print(f"\n{'='*60}")
                print(f"  PENDING REVIEW ({len(pending)} examples)")
                print(f"{'='*60}")

                for i, item in enumerate(pending, 1):
                    _print_review_item(item, i)

                print(f"\nCommands:")
                print(f"  Approve:     python knowledge_distillation.py review --approve <ID> --notes 'notes'")
                print(f"  Reject:      python knowledge_distillation.py review --reject <ID> --notes 'reason'")
                print(f"  Details:     python knowledge_distillation.py review --details <ID>")
                print(f"  Interactive: python knowledge_distillation.py review -i")
                print(f"  Stats:       python knowledge_distillation.py review --stats")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
