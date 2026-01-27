#!/usr/bin/env python3
"""
Feedback System for SAM
Phase 1.2.2-1.2.6: Feedback storage, API integration, correction analysis, and confidence adjustment

Captures user signals about SAM's response quality and converts them
into training data. Implements the schema from FEEDBACK_FORMAT.md.

Usage:
    # Via Python API:
    from feedback_system import (
        FeedbackDB, FeedbackEntry, FeedbackType,
        CorrectionAnalyzer, ConfidenceAdjuster,
        get_feedback_db, get_confidence_adjuster
    )

    db = FeedbackDB()
    feedback_id = db.save_feedback(
        response_id="resp_abc123",
        session_id="sess_xyz789",
        feedback_type="rating",
        rating=1,
        original_query="How do I reverse a list?",
        original_response="Use list[::-1]..."
    )

    # Get feedback for a response
    feedback = db.get_feedback_for_response("resp_abc123")

    # Get recent feedback
    recent = db.get_recent_feedback(limit=20)

    # Get statistics
    stats = db.get_feedback_stats()

    # Analyze corrections (Phase 1.2.5)
    analyzer = CorrectionAnalyzer()
    analysis = analyzer.analyze_correction(
        original="The capital of Australia is Sydney.",
        correction="The capital of Australia is Canberra."
    )

    # Confidence adjustment (Phase 1.2.6)
    adjuster = ConfidenceAdjuster()

    # Get confidence modifier for a domain/topic
    modifier = adjuster.get_confidence_modifier("code", "python")
    adjusted_confidence = base_confidence + modifier  # Range: -0.3 to +0.3

    # Check if SAM should escalate to Claude
    if adjuster.should_suggest_escalation("reasoning"):
        escalate_to_claude()

    # Get comprehensive domain stats
    stats = adjuster.get_domain_stats()
"""

import json
import sqlite3
import hashlib
import time
import re
import difflib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


# Storage paths - External drive is primary, with fallback to local
EXTERNAL_FEEDBACK_PATH = Path("/Volumes/David External/sam_memory/feedback.db")
LOCAL_FEEDBACK_PATH = Path.home() / ".sam" / "feedback.db"


def get_feedback_db_path() -> Path:
    """Get feedback database path, preferring external drive."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_FEEDBACK_PATH
    LOCAL_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOCAL_FEEDBACK_PATH


def is_external_drive_mounted() -> bool:
    """Check if the external drive is mounted."""
    return Path("/Volumes/David External").exists()


class FeedbackType(Enum):
    """Types of feedback users can provide."""
    RATING = "rating"           # Simple thumbs up/down or 1-5 scale
    CORRECTION = "correction"   # User provides the correct answer
    PREFERENCE = "preference"   # User provides a preferred alternative
    FLAG = "flag"               # User flags problematic content


class CorrectionType(Enum):
    """Types of corrections users can provide."""
    FULL_REPLACEMENT = "full_replacement"  # Completely replace the response
    PARTIAL_FIX = "partial_fix"            # Fix specific parts
    ADDITION = "addition"                   # Add missing information
    CLARIFICATION = "clarification"         # Rephrase for clarity


class FlagType(Enum):
    """Types of flags for problematic responses."""
    HARMFUL = "harmful"         # Potentially dangerous content
    INCORRECT = "incorrect"     # Factually wrong
    OFF_TOPIC = "off_topic"     # Didn't address the question
    UNHELPFUL = "unhelpful"     # Technically correct but not useful
    REPETITIVE = "repetitive"   # Too much repetition
    INCOMPLETE = "incomplete"   # Missing important information
    OTHER = "other"             # Other issues


@dataclass
class FeedbackEntry:
    """A single piece of user feedback about a SAM response.

    Matches the schema defined in FEEDBACK_FORMAT.md.
    """

    # === Identifiers ===
    feedback_id: str              # Unique ID (SHA256(response_id + timestamp)[:16])
    response_id: str              # Links to the SAM response being rated
    session_id: str               # Groups feedback within a conversation session
    user_id: Optional[str] = None # User identifier (if multi-user)

    # === Timestamps ===
    timestamp: float = field(default_factory=time.time)  # When feedback was given
    response_timestamp: Optional[float] = None  # When the original response was generated

    # === Feedback Type ===
    feedback_type: str = "rating"  # rating, correction, preference, flag

    # === Rating (for feedback_type="rating") ===
    rating: Optional[int] = None   # Thumbs: -1 (down) or +1 (up), Scale: 1-5

    # === Correction (for feedback_type="correction") ===
    correction: Optional[str] = None            # User-provided correct answer
    correction_type: Optional[str] = None       # full_replacement, partial_fix, addition
    what_was_wrong: Optional[str] = None        # User explanation of the error

    # === Preference (for feedback_type="preference") ===
    preferred_response: Optional[str] = None    # User's preferred alternative
    comparison_basis: Optional[str] = None      # Why this is better

    # === Flag (for feedback_type="flag") ===
    flag_type: Optional[str] = None             # harmful, incorrect, off_topic, etc.
    flag_details: Optional[str] = None          # Additional details

    # === Context ===
    original_query: str = ""                    # The user's original question
    original_response: str = ""                 # SAM's response that received feedback
    conversation_context: Optional[str] = None  # Recent conversation history

    # === Metadata ===
    domain: str = "general"                     # code, reasoning, creative, factual, planning
    response_confidence: Optional[float] = None # SAM's confidence when responding
    escalated_to_claude: bool = False           # Was this an escalated response?

    # === Processing Status ===
    processed: bool = False                     # Has this been converted to training data?
    training_format: Optional[str] = None       # preference, correction, or excluded
    quality_weight: float = 0.5                 # Computed weight for training (0.0-1.0)
    processed_at: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'FeedbackEntry':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def generate_response_id(query: str, timestamp: float) -> str:
    """Generate unique response ID."""
    content = f"{query}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_feedback_id(response_id: str, timestamp: float) -> str:
    """Generate unique feedback ID."""
    content = f"{response_id}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def calculate_feedback_weight(
    feedback: FeedbackEntry,
    current_time: Optional[float] = None
) -> float:
    """
    Calculate training weight for a feedback entry.

    Weights range from 0.0 to 1.0:
    - Higher = more influence in training
    - Corrections weighted highest
    - Recent feedback weighted higher than old

    Implements the algorithm from FEEDBACK_FORMAT.md.
    """
    if current_time is None:
        current_time = time.time()

    weight = 0.5  # Base weight

    # ===== FEEDBACK TYPE WEIGHTS =====

    type_weights = {
        'correction': 0.3,     # Corrections are most valuable
        'preference': 0.2,     # Preferences are very valuable
        'rating': 0.1,         # Ratings provide signal
        'flag': 0.0,           # Flags are for analysis, not training
    }
    weight += type_weights.get(feedback.feedback_type, 0.0)

    # ===== TEMPORAL DECAY =====

    # Recent feedback is more relevant than old feedback
    age_hours = (current_time - feedback.timestamp) / 3600

    # Half-life of 30 days (720 hours)
    half_life_hours = 720
    decay = 0.5 ** (age_hours / half_life_hours)

    # Apply decay as a multiplier (range: 0.5 to 1.0)
    temporal_factor = 0.5 + (0.5 * decay)
    weight *= temporal_factor

    # ===== CORRECTION QUALITY BONUSES =====

    if feedback.feedback_type == 'correction':
        # Bonus for detailed explanation
        if feedback.what_was_wrong and len(feedback.what_was_wrong) > 50:
            weight += 0.05

        # Bonus for substantial correction
        if feedback.correction and len(feedback.correction) > 100:
            weight += 0.05

        # Bonus for full replacement (complete answer)
        if feedback.correction_type == 'full_replacement':
            weight += 0.05

    # ===== PREFERENCE QUALITY BONUSES =====

    if feedback.feedback_type == 'preference':
        # Bonus for explaining why preferred
        if feedback.comparison_basis and len(feedback.comparison_basis) > 30:
            weight += 0.05

    # ===== CONTEXT BONUSES =====

    # Bonus if this was a Claude-escalated response
    # (Feedback on Claude responses validates distillation)
    if feedback.escalated_to_claude:
        weight += 0.05

    # Bonus for high-confidence responses that got negative feedback
    # (Overconfident mistakes are important to learn)
    if (feedback.response_confidence and
        feedback.response_confidence > 0.8 and
        feedback.rating == -1):
        weight += 0.1

    # ===== CLAMP TO VALID RANGE =====

    return max(0.0, min(1.0, weight))


# ===== SQLite Schema =====

FEEDBACK_SCHEMA = """
-- Primary feedback storage
CREATE TABLE IF NOT EXISTS feedback (
    -- Identifiers
    feedback_id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT,

    -- Timestamps
    timestamp REAL NOT NULL,
    response_timestamp REAL,

    -- Feedback type and data
    feedback_type TEXT NOT NULL,  -- rating, correction, preference, flag

    -- Rating data (when feedback_type = 'rating')
    rating INTEGER,  -- -1, +1 (thumbs) or 1-5 (scale)

    -- Correction data (when feedback_type = 'correction')
    correction TEXT,
    correction_type TEXT,
    what_was_wrong TEXT,

    -- Preference data (when feedback_type = 'preference')
    preferred_response TEXT,
    comparison_basis TEXT,

    -- Flag data (when feedback_type = 'flag')
    flag_type TEXT,
    flag_details TEXT,

    -- Context
    original_query TEXT NOT NULL,
    original_response TEXT NOT NULL,
    conversation_context TEXT,

    -- Metadata
    domain TEXT DEFAULT 'general',
    response_confidence REAL,
    escalated_to_claude INTEGER DEFAULT 0,

    -- Processing status
    processed INTEGER DEFAULT 0,
    training_format TEXT,
    quality_weight REAL DEFAULT 0.5,
    processed_at REAL,

    -- Timestamps
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_feedback_response ON feedback(response_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback(processed);
CREATE INDEX IF NOT EXISTS idx_feedback_domain ON feedback(domain);
CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp);
CREATE INDEX IF NOT EXISTS idx_feedback_quality ON feedback(quality_weight);

-- Confidence tracking per domain/topic (Phase 1.2.6)
CREATE TABLE IF NOT EXISTS confidence_tracking (
    domain TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT 'general',

    -- Accuracy metrics
    total_responses INTEGER DEFAULT 0,
    positive_feedback INTEGER DEFAULT 0,
    negative_feedback INTEGER DEFAULT 0,
    corrections_received INTEGER DEFAULT 0,

    -- Computed accuracy rate (updated on each feedback)
    accuracy_rate REAL DEFAULT 0.5,

    -- Error type tracking (JSON: {"factual": 3, "incomplete": 5, ...})
    error_types TEXT DEFAULT '{}',

    -- Trend tracking (last N feedback items)
    recent_feedback TEXT DEFAULT '[]',  -- JSON array of recent {timestamp, rating}
    trend_direction TEXT DEFAULT 'stable',  -- improving, declining, stable
    trend_strength REAL DEFAULT 0.0,  -- 0.0 to 1.0

    -- Confidence modifier computed from all factors
    confidence_modifier REAL DEFAULT 0.0,  -- -0.3 to +0.3

    -- Timestamps
    first_feedback_at REAL,
    last_feedback_at REAL,
    last_recalculated_at REAL,

    PRIMARY KEY (domain, topic)
);

CREATE INDEX IF NOT EXISTS idx_confidence_domain ON confidence_tracking(domain);
CREATE INDEX IF NOT EXISTS idx_confidence_modifier ON confidence_tracking(confidence_modifier);

-- Aggregate feedback statistics per response
CREATE TABLE IF NOT EXISTS feedback_aggregates (
    response_id TEXT PRIMARY KEY,

    -- Rating counts
    thumbs_up_count INTEGER DEFAULT 0,
    thumbs_down_count INTEGER DEFAULT 0,
    avg_rating REAL,  -- If using 1-5 scale

    -- Feedback type counts
    correction_count INTEGER DEFAULT 0,
    preference_count INTEGER DEFAULT 0,
    flag_count INTEGER DEFAULT 0,

    -- Computed metrics
    net_sentiment REAL,  -- (up - down) / total
    confidence_delta REAL,  -- How much feedback changed confidence

    -- Timestamps
    first_feedback_at REAL,
    last_feedback_at REAL,

    -- Links
    session_ids TEXT,  -- JSON array of session_ids that provided feedback

    updated_at REAL DEFAULT (strftime('%s', 'now'))
);

-- Track feedback patterns across sessions
CREATE TABLE IF NOT EXISTS feedback_sessions (
    session_id TEXT PRIMARY KEY,

    -- Session metrics
    total_responses INTEGER DEFAULT 0,
    feedback_given INTEGER DEFAULT 0,
    feedback_rate REAL,  -- feedback_given / total_responses

    -- Sentiment
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,

    -- Session quality score
    session_quality REAL,

    -- Timestamps
    started_at REAL,
    last_activity_at REAL,

    -- Context
    primary_domain TEXT,
    topics TEXT  -- JSON array of topics discussed
);
"""


class FeedbackDB:
    """SQLite database for feedback storage.

    Primary storage on external drive: /Volumes/David External/sam_memory/feedback.db
    Falls back to local ~/.sam/feedback.db if external drive not mounted.

    Implements the schema from FEEDBACK_FORMAT.md.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the feedback database.

        Args:
            db_path: Optional explicit path. If None, uses external drive if mounted,
                    otherwise falls back to local path.
        """
        if db_path is None:
            self.db_path = get_feedback_db_path()
        else:
            self.db_path = db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(FEEDBACK_SCHEMA)
        conn.commit()
        conn.close()

    def save_feedback(
        self,
        response_id: str,
        session_id: str,
        original_query: str,
        original_response: str,
        feedback_type: str = "rating",
        rating: Optional[int] = None,
        correction: Optional[str] = None,
        correction_type: Optional[str] = None,
        what_was_wrong: Optional[str] = None,
        preferred_response: Optional[str] = None,
        comparison_basis: Optional[str] = None,
        flag_type: Optional[str] = None,
        flag_details: Optional[str] = None,
        domain: str = "general",
        response_confidence: Optional[float] = None,
        escalated_to_claude: bool = False,
        user_id: Optional[str] = None,
        response_timestamp: Optional[float] = None,
        conversation_context: Optional[str] = None,
    ) -> str:
        """
        Save feedback for a response.

        Args:
            response_id: ID of the response being rated
            session_id: Current conversation session ID
            original_query: The user's original question
            original_response: SAM's response that received feedback
            feedback_type: Type of feedback (rating, correction, preference, flag)
            rating: For rating type: -1 (down), +1 (up), or 1-5 scale
            correction: For correction type: the correct answer
            correction_type: For correction: full_replacement, partial_fix, addition
            what_was_wrong: For correction: explanation of the error
            preferred_response: For preference: user's preferred alternative
            comparison_basis: For preference: why this is better
            flag_type: For flag: harmful, incorrect, off_topic, etc.
            flag_details: For flag: additional details
            domain: Domain classification (code, reasoning, creative, factual, planning)
            response_confidence: SAM's confidence when responding
            escalated_to_claude: Whether this was a Claude-escalated response
            user_id: Optional user identifier
            response_timestamp: When the original response was generated
            conversation_context: Recent conversation history

        Returns:
            The feedback ID
        """
        timestamp = time.time()
        feedback_id = generate_feedback_id(response_id, timestamp)

        # Create FeedbackEntry for weight calculation
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            response_id=response_id,
            session_id=session_id,
            user_id=user_id,
            timestamp=timestamp,
            response_timestamp=response_timestamp,
            feedback_type=feedback_type,
            rating=rating,
            correction=correction,
            correction_type=correction_type,
            what_was_wrong=what_was_wrong,
            preferred_response=preferred_response,
            comparison_basis=comparison_basis,
            flag_type=flag_type,
            flag_details=flag_details,
            original_query=original_query,
            original_response=original_response,
            conversation_context=conversation_context,
            domain=domain,
            response_confidence=response_confidence,
            escalated_to_claude=escalated_to_claude,
        )

        # Calculate quality weight
        quality_weight = calculate_feedback_weight(entry)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO feedback (
                    feedback_id, response_id, session_id, user_id,
                    timestamp, response_timestamp,
                    feedback_type, rating,
                    correction, correction_type, what_was_wrong,
                    preferred_response, comparison_basis,
                    flag_type, flag_details,
                    original_query, original_response, conversation_context,
                    domain, response_confidence, escalated_to_claude,
                    quality_weight, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id, response_id, session_id, user_id,
                timestamp, response_timestamp,
                feedback_type, rating,
                correction, correction_type, what_was_wrong,
                preferred_response, comparison_basis,
                flag_type, flag_details,
                original_query, original_response, conversation_context,
                domain, response_confidence, int(escalated_to_claude),
                quality_weight, timestamp
            ))

            # Update aggregates
            self._update_aggregates(cur, response_id, feedback_type, rating, session_id, timestamp)

            # Update session tracking
            self._update_session(cur, session_id, feedback_type, rating, domain, timestamp)

            conn.commit()
        finally:
            conn.close()

        return feedback_id

    def _update_aggregates(
        self,
        cur: sqlite3.Cursor,
        response_id: str,
        feedback_type: str,
        rating: Optional[int],
        session_id: str,
        timestamp: float
    ):
        """Update feedback aggregates for a response."""
        # Check if aggregate exists
        cur.execute("SELECT session_ids FROM feedback_aggregates WHERE response_id = ?", (response_id,))
        row = cur.fetchone()

        if row:
            # Update existing
            session_ids = json.loads(row[0]) if row[0] else []
            if session_id not in session_ids:
                session_ids.append(session_id)

            # Calculate updates
            thumbs_up_inc = 1 if feedback_type == 'rating' and rating == 1 else 0
            thumbs_down_inc = 1 if feedback_type == 'rating' and rating == -1 else 0
            correction_inc = 1 if feedback_type == 'correction' else 0
            preference_inc = 1 if feedback_type == 'preference' else 0
            flag_inc = 1 if feedback_type == 'flag' else 0

            cur.execute("""
                UPDATE feedback_aggregates SET
                    thumbs_up_count = thumbs_up_count + ?,
                    thumbs_down_count = thumbs_down_count + ?,
                    correction_count = correction_count + ?,
                    preference_count = preference_count + ?,
                    flag_count = flag_count + ?,
                    last_feedback_at = ?,
                    session_ids = ?,
                    updated_at = ?
                WHERE response_id = ?
            """, (
                thumbs_up_inc, thumbs_down_inc,
                correction_inc, preference_inc, flag_inc,
                timestamp, json.dumps(session_ids), timestamp,
                response_id
            ))

            # Update net sentiment
            cur.execute("""
                UPDATE feedback_aggregates SET
                    net_sentiment = CASE
                        WHEN (thumbs_up_count + thumbs_down_count) > 0
                        THEN CAST(thumbs_up_count - thumbs_down_count AS REAL) / (thumbs_up_count + thumbs_down_count)
                        ELSE 0.0
                    END
                WHERE response_id = ?
            """, (response_id,))
        else:
            # Insert new
            cur.execute("""
                INSERT INTO feedback_aggregates (
                    response_id,
                    thumbs_up_count, thumbs_down_count,
                    correction_count, preference_count, flag_count,
                    net_sentiment,
                    first_feedback_at, last_feedback_at,
                    session_ids, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response_id,
                1 if feedback_type == 'rating' and rating == 1 else 0,
                1 if feedback_type == 'rating' and rating == -1 else 0,
                1 if feedback_type == 'correction' else 0,
                1 if feedback_type == 'preference' else 0,
                1 if feedback_type == 'flag' else 0,
                1.0 if rating == 1 else (-1.0 if rating == -1 else 0.0),
                timestamp, timestamp,
                json.dumps([session_id]), timestamp
            ))

    def _update_session(
        self,
        cur: sqlite3.Cursor,
        session_id: str,
        feedback_type: str,
        rating: Optional[int],
        domain: str,
        timestamp: float
    ):
        """Update session tracking."""
        # Check if session exists
        cur.execute("SELECT * FROM feedback_sessions WHERE session_id = ?", (session_id,))
        row = cur.fetchone()

        positive_inc = 1 if feedback_type == 'rating' and rating == 1 else 0
        negative_inc = 1 if feedback_type == 'rating' and rating == -1 else 0
        correction_inc = 1 if feedback_type == 'correction' else 0

        if row:
            cur.execute("""
                UPDATE feedback_sessions SET
                    feedback_given = feedback_given + 1,
                    positive_count = positive_count + ?,
                    negative_count = negative_count + ?,
                    correction_count = correction_count + ?,
                    last_activity_at = ?,
                    feedback_rate = CASE
                        WHEN total_responses > 0
                        THEN CAST(feedback_given + 1 AS REAL) / total_responses
                        ELSE 0.0
                    END,
                    session_quality = CASE
                        WHEN (positive_count + ? + negative_count + ?) > 0
                        THEN CAST(positive_count + ? AS REAL) / (positive_count + ? + negative_count + ?)
                        ELSE 0.5
                    END
                WHERE session_id = ?
            """, (
                positive_inc, negative_inc, correction_inc,
                timestamp,
                positive_inc, negative_inc,
                positive_inc, positive_inc, negative_inc,
                session_id
            ))
        else:
            quality = 1.0 if positive_inc else (0.0 if negative_inc else 0.5)
            cur.execute("""
                INSERT INTO feedback_sessions (
                    session_id, total_responses, feedback_given,
                    feedback_rate, positive_count, negative_count, correction_count,
                    session_quality, started_at, last_activity_at, primary_domain
                ) VALUES (?, 0, 1, 0.0, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, positive_inc, negative_inc, correction_inc,
                quality, timestamp, timestamp, domain
            ))

    def get_feedback_for_response(self, response_id: str) -> List[Dict]:
        """Get all feedback for a specific response.

        Args:
            response_id: The response ID to get feedback for

        Returns:
            List of feedback entries as dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM feedback
            WHERE response_id = ?
            ORDER BY timestamp DESC
        """, (response_id,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recent_feedback(
        self,
        limit: int = 20,
        domain: Optional[str] = None,
        feedback_type: Optional[str] = None,
        session_id: Optional[str] = None,
        include_processed: bool = True
    ) -> List[Dict]:
        """Get recent feedback entries.

        Args:
            limit: Maximum number of entries to return
            domain: Filter by domain
            feedback_type: Filter by feedback type
            session_id: Filter by session
            include_processed: Include already-processed feedback

        Returns:
            List of feedback entries as dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = "SELECT * FROM feedback WHERE 1=1"
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if feedback_type:
            query += " AND feedback_type = ?"
            params.append(feedback_type)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if not include_processed:
            query += " AND processed = 0"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get comprehensive feedback statistics.

        Returns:
            Dictionary with statistics including:
            - total_feedback: Total captured feedback
            - by_type: Breakdown by feedback type
            - sentiment: Positive/negative breakdown
            - processed: Count of processed vs pending
            - quality: Average quality weight
            - recent_24h: Count in last 24 hours
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        # Total feedback
        cur.execute("SELECT COUNT(*) FROM feedback")
        stats["total_feedback"] = cur.fetchone()[0]

        # By type
        cur.execute("""
            SELECT feedback_type, COUNT(*)
            FROM feedback
            GROUP BY feedback_type
        """)
        stats["by_type"] = dict(cur.fetchall())

        # Sentiment (from ratings)
        cur.execute("SELECT COUNT(*) FROM feedback WHERE rating = 1")
        positive = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedback WHERE rating = -1")
        negative = cur.fetchone()[0]
        total_rated = positive + negative

        stats["sentiment"] = {
            "positive": positive,
            "negative": negative,
            "net_sentiment": (positive - negative) / total_rated if total_rated > 0 else 0.0
        }

        # Processed status
        cur.execute("SELECT COUNT(*) FROM feedback WHERE processed = 1")
        processed = cur.fetchone()[0]
        stats["processed"] = {
            "total": processed,
            "pending": stats["total_feedback"] - processed
        }

        # Quality
        cur.execute("SELECT AVG(quality_weight) FROM feedback")
        avg_weight = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedback WHERE quality_weight >= 0.7")
        high_quality = cur.fetchone()[0]

        stats["quality"] = {
            "avg_weight": round(avg_weight, 3) if avg_weight else 0.0,
            "high_quality_count": high_quality
        }

        # Recent 24h
        day_ago = time.time() - 86400
        cur.execute("SELECT COUNT(*) FROM feedback WHERE timestamp > ?", (day_ago,))
        stats["recent_24h"] = cur.fetchone()[0]

        # By domain
        cur.execute("""
            SELECT domain, COUNT(*)
            FROM feedback
            GROUP BY domain
        """)
        stats["by_domain"] = dict(cur.fetchall())

        # Storage info
        stats["storage"] = {
            "location": str(self.db_path),
            "using_external_drive": is_external_drive_mounted()
        }

        conn.close()
        return stats

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a specific session.

        Args:
            session_id: The session to get stats for

        Returns:
            Session statistics or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM feedback_sessions WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_response_aggregates(self, response_id: str) -> Optional[Dict]:
        """Get aggregated feedback for a specific response.

        Args:
            response_id: The response to get aggregates for

        Returns:
            Aggregate statistics or None if no feedback
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM feedback_aggregates WHERE response_id = ?", (response_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            result = dict(row)
            # Parse session_ids JSON
            if result.get('session_ids'):
                result['session_ids'] = json.loads(result['session_ids'])
            return result
        return None

    def mark_as_processed(
        self,
        feedback_id: str,
        training_format: str = "excluded"
    ) -> bool:
        """Mark feedback as processed for training.

        Args:
            feedback_id: The feedback to mark
            training_format: How it was used (preference, correction, instruction, excluded)

        Returns:
            True if updated, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            UPDATE feedback SET
                processed = 1,
                training_format = ?,
                processed_at = ?
            WHERE feedback_id = ?
        """, (training_format, time.time(), feedback_id))

        updated = cur.rowcount > 0
        conn.commit()
        conn.close()

        return updated

    def get_unprocessed_for_training(
        self,
        limit: int = 100,
        min_quality: float = 0.3
    ) -> List[Dict]:
        """Get unprocessed feedback suitable for training.

        Args:
            limit: Maximum number to return
            min_quality: Minimum quality weight threshold

        Returns:
            List of high-quality unprocessed feedback
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM feedback
            WHERE processed = 0
              AND quality_weight >= ?
              AND feedback_type != 'flag'
            ORDER BY quality_weight DESC, timestamp DESC
            LIMIT ?
        """, (min_quality, limit))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def increment_session_responses(self, session_id: str) -> None:
        """Increment the total responses counter for a session.

        Call this when SAM generates a response (before feedback is received).
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        timestamp = time.time()

        # Check if session exists
        cur.execute("SELECT * FROM feedback_sessions WHERE session_id = ?", (session_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE feedback_sessions SET
                    total_responses = total_responses + 1,
                    last_activity_at = ?,
                    feedback_rate = CASE
                        WHEN (total_responses + 1) > 0
                        THEN CAST(feedback_given AS REAL) / (total_responses + 1)
                        ELSE 0.0
                    END
                WHERE session_id = ?
            """, (timestamp, session_id))
        else:
            cur.execute("""
                INSERT INTO feedback_sessions (
                    session_id, total_responses, feedback_given,
                    feedback_rate, positive_count, negative_count, correction_count,
                    session_quality, started_at, last_activity_at
                ) VALUES (?, 1, 0, 0.0, 0, 0, 0, 0.5, ?, ?)
            """, (session_id, timestamp, timestamp))

        conn.commit()
        conn.close()

    # ===== Phase 1.2.8: Daily Stats for Proactive Notifications =====

    def get_daily_correction_count(self) -> int:
        """Get the number of corrections received today.

        Returns:
            Number of correction-type feedback entries since midnight.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Calculate midnight timestamp
        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_ts = today.timestamp()

        cur.execute("""
            SELECT COUNT(*) FROM feedback
            WHERE feedback_type = 'correction' AND timestamp >= ?
        """, (midnight_ts,))
        count = cur.fetchone()[0]
        conn.close()

        return count

    def get_daily_negative_count(self) -> int:
        """Get the number of negative feedback entries today.

        Returns:
            Number of negative ratings (rating=-1) since midnight.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_ts = today.timestamp()

        cur.execute("""
            SELECT COUNT(*) FROM feedback
            WHERE rating = -1 AND timestamp >= ?
        """, (midnight_ts,))
        count = cur.fetchone()[0]
        conn.close()

        return count

    def get_unprocessed_count(self) -> int:
        """Get the count of unprocessed feedback items.

        Returns:
            Number of feedback entries not yet processed for training.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM feedback WHERE processed = 0")
        count = cur.fetchone()[0]
        conn.close()

        return count

    def get_domain_accuracy_trends(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get accuracy trends by domain over recent days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with domain -> {recent_accuracy, previous_accuracy, trend}
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        from datetime import datetime, timedelta

        now = datetime.now()
        mid_point = now - timedelta(days=days // 2)
        start_point = now - timedelta(days=days)

        mid_ts = mid_point.timestamp()
        start_ts = start_point.timestamp()

        trends = {}

        # Get unique domains
        cur.execute("SELECT DISTINCT domain FROM feedback WHERE domain IS NOT NULL")
        domains = [row[0] for row in cur.fetchall()]

        for domain in domains:
            # Recent period (mid to now)
            cur.execute("""
                SELECT
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as positive,
                    COUNT(CASE WHEN rating = -1 THEN 1 END) as negative
                FROM feedback
                WHERE domain = ? AND timestamp >= ?
            """, (domain, mid_ts))
            recent = cur.fetchone()
            recent_total = (recent[0] or 0) + (recent[1] or 0)
            recent_accuracy = (recent[0] or 0) / recent_total if recent_total > 0 else None

            # Previous period (start to mid)
            cur.execute("""
                SELECT
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as positive,
                    COUNT(CASE WHEN rating = -1 THEN 1 END) as negative
                FROM feedback
                WHERE domain = ? AND timestamp >= ? AND timestamp < ?
            """, (domain, start_ts, mid_ts))
            previous = cur.fetchone()
            prev_total = (previous[0] or 0) + (previous[1] or 0)
            prev_accuracy = (previous[0] or 0) / prev_total if prev_total > 0 else None

            # Determine trend
            if recent_accuracy is not None and prev_accuracy is not None:
                diff = recent_accuracy - prev_accuracy
                if diff < -0.1:
                    trend = "declining"
                elif diff > 0.1:
                    trend = "improving"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            trends[domain] = {
                "recent_accuracy": round(recent_accuracy, 3) if recent_accuracy else None,
                "previous_accuracy": round(prev_accuracy, 3) if prev_accuracy else None,
                "trend": trend,
                "recent_samples": recent_total,
                "previous_samples": prev_total
            }

        conn.close()
        return trends

    def get_feedback_notifications_data(self) -> Dict[str, Any]:
        """Get all data needed for proactive notifications about feedback.

        Returns:
            Dictionary with:
            - daily_corrections: Number of corrections today
            - daily_negative: Number of negative ratings today
            - unprocessed_count: Feedback ready for training export
            - declining_domains: Domains with accuracy drops
            - threshold_alerts: List of notification messages
        """
        data = {
            "daily_corrections": self.get_daily_correction_count(),
            "daily_negative": self.get_daily_negative_count(),
            "unprocessed_count": self.get_unprocessed_count(),
            "declining_domains": [],
            "threshold_alerts": []
        }

        # Check domain trends
        trends = self.get_domain_accuracy_trends(days=7)
        for domain, info in trends.items():
            if info["trend"] == "declining":
                data["declining_domains"].append({
                    "domain": domain,
                    "recent_accuracy": info["recent_accuracy"],
                    "previous_accuracy": info["previous_accuracy"],
                    "drop": round((info["previous_accuracy"] or 0) - (info["recent_accuracy"] or 0), 3)
                })

        # Generate threshold alerts
        if data["daily_corrections"] >= 3:
            data["threshold_alerts"].append({
                "type": "corrections_threshold",
                "message": f"You received {data['daily_corrections']} corrections today - want to review them?",
                "urgency": "medium"
            })

        if data["daily_negative"] >= 5:
            data["threshold_alerts"].append({
                "type": "negative_feedback",
                "message": f"{data['daily_negative']} negative ratings today - consider reviewing responses",
                "urgency": "medium"
            })

        if data["unprocessed_count"] >= 5:
            data["threshold_alerts"].append({
                "type": "training_ready",
                "message": f"{data['unprocessed_count']} new feedback items ready for training export",
                "urgency": "low"
            })

        for declining in data["declining_domains"]:
            data["threshold_alerts"].append({
                "type": "accuracy_drop",
                "message": f"Feedback accuracy dropped in {declining['domain']} - consider reviewing",
                "urgency": "medium"
            })

        return data

    # ===== Phase 1.2.9: Dashboard Data =====

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for feedback review.

        Returns:
            Dictionary with:
            - summary: Today's feedback summary
            - domain_breakdown: Accuracy per domain
            - recent_corrections: List of recent corrections needing review
            - training_status: Training data generation status
            - trends: 7-day trends
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        from datetime import datetime, timedelta
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_ts = today.timestamp()
        week_ago_ts = (now - timedelta(days=7)).timestamp()

        # Today's summary
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as positive,
                COUNT(CASE WHEN rating = -1 THEN 1 END) as negative,
                COUNT(CASE WHEN feedback_type = 'correction' THEN 1 END) as corrections,
                COUNT(CASE WHEN feedback_type = 'preference' THEN 1 END) as preferences,
                COUNT(CASE WHEN feedback_type = 'flag' THEN 1 END) as flags
            FROM feedback WHERE timestamp >= ?
        """, (today_ts,))
        today_row = cur.fetchone()

        summary = {
            "date": today.strftime("%Y-%m-%d"),
            "total": today_row["total"] or 0,
            "positive": today_row["positive"] or 0,
            "negative": today_row["negative"] or 0,
            "corrections": today_row["corrections"] or 0,
            "preferences": today_row["preferences"] or 0,
            "flags": today_row["flags"] or 0,
            "sentiment_ratio": (today_row["positive"] or 0) / max(1, (today_row["positive"] or 0) + (today_row["negative"] or 0))
        }

        # Domain breakdown with accuracy
        cur.execute("""
            SELECT
                domain,
                COUNT(*) as total,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as positive,
                COUNT(CASE WHEN rating = -1 THEN 1 END) as negative,
                COUNT(CASE WHEN feedback_type = 'correction' THEN 1 END) as corrections
            FROM feedback
            WHERE timestamp >= ?
            GROUP BY domain
            ORDER BY total DESC
        """, (week_ago_ts,))

        domain_breakdown = {}
        for row in cur.fetchall():
            total_rated = (row["positive"] or 0) + (row["negative"] or 0)
            domain_breakdown[row["domain"] or "general"] = {
                "total": row["total"],
                "positive": row["positive"] or 0,
                "negative": row["negative"] or 0,
                "corrections": row["corrections"] or 0,
                "accuracy": round((row["positive"] or 0) / max(1, total_rated), 3)
            }

        # Recent corrections needing review (unprocessed)
        cur.execute("""
            SELECT
                feedback_id, timestamp, domain, original_query, original_response,
                correction, what_was_wrong, quality_weight, processed
            FROM feedback
            WHERE feedback_type = 'correction'
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        recent_corrections = []
        for row in cur.fetchall():
            recent_corrections.append({
                "feedback_id": row["feedback_id"],
                "timestamp": datetime.fromtimestamp(row["timestamp"]).isoformat(),
                "domain": row["domain"] or "general",
                "query": (row["original_query"] or "")[:100] + ("..." if len(row["original_query"] or "") > 100 else ""),
                "original": (row["original_response"] or "")[:150] + ("..." if len(row["original_response"] or "") > 150 else ""),
                "correction": (row["correction"] or "")[:150] + ("..." if len(row["correction"] or "") > 150 else ""),
                "what_was_wrong": row["what_was_wrong"],
                "quality_weight": row["quality_weight"],
                "processed": bool(row["processed"])
            })

        # Training status
        cur.execute("SELECT COUNT(*) FROM feedback WHERE processed = 0")
        unprocessed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedback WHERE processed = 1")
        processed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedback WHERE quality_weight >= 0.7")
        high_quality = cur.fetchone()[0]

        training_status = {
            "unprocessed": unprocessed,
            "processed": processed,
            "high_quality_pending": high_quality,
            "ready_for_export": unprocessed >= 5
        }

        # 7-day trends
        trends = self.get_domain_accuracy_trends(days=7)

        conn.close()

        return {
            "summary": summary,
            "domain_breakdown": domain_breakdown,
            "recent_corrections": recent_corrections,
            "training_status": training_status,
            "trends": trends,
            "generated_at": datetime.now().isoformat()
        }

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Dict]:
        """Get a single feedback entry by ID.

        Args:
            feedback_id: The feedback ID

        Returns:
            Feedback entry as dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM feedback WHERE feedback_id = ?", (feedback_id,))
        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def update_feedback(
        self,
        feedback_id: str,
        correction: Optional[str] = None,
        what_was_wrong: Optional[str] = None,
        processed: Optional[bool] = None,
        training_format: Optional[str] = None
    ) -> bool:
        """Update a feedback entry.

        Args:
            feedback_id: The feedback ID to update
            correction: New correction text (optional)
            what_was_wrong: New explanation (optional)
            processed: Mark as processed (optional)
            training_format: Training format used (optional)

        Returns:
            True if updated, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        updates = []
        params = []

        if correction is not None:
            updates.append("correction = ?")
            params.append(correction)
        if what_was_wrong is not None:
            updates.append("what_was_wrong = ?")
            params.append(what_was_wrong)
        if processed is not None:
            updates.append("processed = ?")
            params.append(int(processed))
            if processed:
                updates.append("processed_at = ?")
                params.append(time.time())
        if training_format is not None:
            updates.append("training_format = ?")
            params.append(training_format)

        if not updates:
            conn.close()
            return False

        params.append(feedback_id)
        query = f"UPDATE feedback SET {', '.join(updates)} WHERE feedback_id = ?"

        cur.execute(query, params)
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()

        return updated


# ===== Singleton instance =====

_feedback_db = None


def get_feedback_db() -> FeedbackDB:
    """Get the singleton FeedbackDB instance."""
    global _feedback_db
    if _feedback_db is None:
        _feedback_db = FeedbackDB()
    return _feedback_db


# ===== Phase 1.2.5: Correction Analyzer =====

class ErrorCategory(Enum):
    """Categories of errors that SAM can make."""
    FACTUAL = "factual"             # Wrong facts (dates, names, numbers)
    INCOMPLETE = "incomplete"       # Missing important information
    FORMAT = "format"               # Wrong format/structure
    TONE = "tone"                   # Wrong tone (too formal, too casual, etc.)
    OUTDATED = "outdated"           # Information is out of date
    LOGICAL = "logical"             # Logic error or contradiction
    CODE_SYNTAX = "code_syntax"     # Syntax error in code
    CODE_LOGIC = "code_logic"       # Logic error in code
    CODE_STYLE = "code_style"       # Style/convention issues in code
    MISUNDERSTOOD = "misunderstood" # Misunderstood the question
    HALLUCINATION = "hallucination" # Made up information
    VERBOSE = "verbose"             # Too wordy, should be concise
    UNCLEAR = "unclear"             # Confusing or ambiguous
    OTHER = "other"                 # Doesn't fit other categories


@dataclass
class DiffSegment:
    """A segment of text that was changed in a correction."""
    operation: str      # 'delete', 'insert', 'replace', 'equal'
    original: str       # Text from original response
    corrected: str      # Text from correction
    position: int       # Character position in original

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CorrectionAnalysis:
    """Result of analyzing a correction.

    Contains structured information about what was wrong with SAM's
    response and how it should have been different.
    """
    # What SAM said that was wrong
    original_text: str

    # What the correct answer should be
    corrected_text: str

    # Error categorization
    error_type: str                     # Primary error category
    error_types: List[str]              # All detected error categories

    # Detailed diff analysis
    diff_segments: List[DiffSegment]    # Specific changes made
    similarity_ratio: float             # 0.0 (completely different) to 1.0 (identical)
    change_ratio: float                 # Percentage of text that changed

    # Pattern extraction
    error_patterns: List[Dict]          # Specific patterns to avoid

    # For training
    training_example: Optional[Dict]    # Formatted for fine-tuning

    # Metadata
    query: Optional[str] = None         # Original query (if available)
    what_was_wrong: Optional[str] = None # User's explanation (if provided)
    analyzed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        result = asdict(self)
        result['diff_segments'] = [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.diff_segments]
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class CorrectionAnalyzer:
    """
    Analyzes corrections to extract structured training data.

    Phase 1.2.5: Uses text comparison techniques to understand what
    SAM said wrong and how to avoid similar mistakes.

    Usage:
        analyzer = CorrectionAnalyzer()

        # Analyze a single correction
        analysis = analyzer.analyze_correction(
            original="The capital of Australia is Sydney.",
            correction="The capital of Australia is Canberra.",
            query="What is the capital of Australia?"
        )

        # Process all unprocessed corrections from FeedbackDB
        training_data = analyzer.process_corrections_from_db(db)
    """

    # Patterns for detecting error types
    ERROR_PATTERNS = {
        # Factual errors: numbers, dates, names that changed
        ErrorCategory.FACTUAL: [
            r'\b\d{4}\b',                           # Years
            r'\b\d+(?:\.\d+)?%?\b',                 # Numbers/percentages
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Proper nouns
        ],

        # Code syntax: common programming patterns
        ErrorCategory.CODE_SYNTAX: [
            r'```[\s\S]*?```',                      # Code blocks
            r'\b(def|function|class|import|from)\b',
            r'[{}\[\]();]',                         # Brackets/syntax
            r'=>|->|::|\.\.\.|\?\.',               # Operators
        ],

        # Outdated: temporal words
        ErrorCategory.OUTDATED: [
            r'\b(currently|now|today|recent|latest|new|modern)\b',
            r'\b(was|used to|previously|formerly|deprecated)\b',
            r'\b20\d{2}\b',                         # Years (2000-2099)
        ],

        # Verbose: filler words
        ErrorCategory.VERBOSE: [
            r'\b(basically|essentially|actually|really|very|quite|rather)\b',
            r'\b(in order to|due to the fact that|at this point in time)\b',
            r'\b(it is important to note that|it should be noted that)\b',
        ],
    }

    # Keywords suggesting specific error types in user explanations
    EXPLANATION_KEYWORDS = {
        ErrorCategory.FACTUAL: ['wrong', 'incorrect', 'false', 'not true', 'actually'],
        ErrorCategory.INCOMPLETE: ['missing', 'forgot', 'didn\'t mention', 'also', 'left out'],
        ErrorCategory.FORMAT: ['format', 'structure', 'layout', 'organize', 'bullet'],
        ErrorCategory.TONE: ['too formal', 'too casual', 'tone', 'friendly', 'professional'],
        ErrorCategory.OUTDATED: ['outdated', 'old', 'deprecated', 'no longer', 'updated'],
        ErrorCategory.LOGICAL: ['doesn\'t make sense', 'contradiction', 'logic', 'inconsistent'],
        ErrorCategory.CODE_SYNTAX: ['syntax', 'typo', 'compile', 'error', 'bug'],
        ErrorCategory.CODE_LOGIC: ['doesn\'t work', 'wrong output', 'logic error', 'bug'],
        ErrorCategory.CODE_STYLE: ['style', 'convention', 'naming', 'pep8', 'format'],
        ErrorCategory.MISUNDERSTOOD: ['misunderstood', 'not what I asked', 'different question'],
        ErrorCategory.HALLUCINATION: ['made up', 'doesn\'t exist', 'fabricated', 'not real'],
        ErrorCategory.VERBOSE: ['too long', 'wordy', 'concise', 'shorter', 'brief'],
        ErrorCategory.UNCLEAR: ['confusing', 'unclear', 'ambiguous', 'don\'t understand'],
    }

    def __init__(self):
        """Initialize the correction analyzer."""
        pass

    def analyze_correction(
        self,
        original: str,
        correction: str,
        query: Optional[str] = None,
        what_was_wrong: Optional[str] = None,
    ) -> CorrectionAnalysis:
        """
        Analyze a correction to extract structured training data.

        Args:
            original: SAM's original response
            correction: The user's corrected version
            query: The original question (if available)
            what_was_wrong: User's explanation of the error (if provided)

        Returns:
            CorrectionAnalysis with detailed breakdown
        """
        # Compute similarity
        similarity_ratio = self._compute_similarity(original, correction)

        # Get detailed diff
        diff_segments = self._compute_diff(original, correction)

        # Calculate change ratio
        change_ratio = self._compute_change_ratio(diff_segments)

        # Detect error types
        error_types = self._detect_error_types(
            original, correction, diff_segments, what_was_wrong
        )

        # Extract error patterns
        error_patterns = self._extract_error_patterns(
            original, correction, diff_segments, error_types
        )

        # Generate training example
        training_example = self._generate_training_example(
            original, correction, query, error_types, error_patterns
        )

        return CorrectionAnalysis(
            original_text=original,
            corrected_text=correction,
            error_type=error_types[0] if error_types else ErrorCategory.OTHER.value,
            error_types=error_types,
            diff_segments=diff_segments,
            similarity_ratio=similarity_ratio,
            change_ratio=change_ratio,
            error_patterns=error_patterns,
            training_example=training_example,
            query=query,
            what_was_wrong=what_was_wrong,
        )

    def _compute_similarity(self, original: str, correction: str) -> float:
        """Compute semantic similarity between original and correction."""
        return difflib.SequenceMatcher(None, original, correction).ratio()

    def _compute_diff(self, original: str, correction: str) -> List[DiffSegment]:
        """Compute detailed diff between original and correction."""
        segments = []
        matcher = difflib.SequenceMatcher(None, original, correction)

        position = 0
        for opcode, a1, a2, b1, b2 in matcher.get_opcodes():
            original_text = original[a1:a2]
            corrected_text = correction[b1:b2]

            if opcode == 'equal':
                segments.append(DiffSegment(
                    operation='equal',
                    original=original_text,
                    corrected=corrected_text,
                    position=a1
                ))
            elif opcode == 'replace':
                segments.append(DiffSegment(
                    operation='replace',
                    original=original_text,
                    corrected=corrected_text,
                    position=a1
                ))
            elif opcode == 'delete':
                segments.append(DiffSegment(
                    operation='delete',
                    original=original_text,
                    corrected='',
                    position=a1
                ))
            elif opcode == 'insert':
                segments.append(DiffSegment(
                    operation='insert',
                    original='',
                    corrected=corrected_text,
                    position=a1
                ))

            position = a2

        return segments

    def _compute_change_ratio(self, diff_segments: List[DiffSegment]) -> float:
        """Compute what percentage of text was changed."""
        total_original_chars = sum(len(s.original) for s in diff_segments)
        changed_chars = sum(
            len(s.original) for s in diff_segments
            if s.operation != 'equal'
        )

        if total_original_chars == 0:
            return 1.0 if any(s.corrected for s in diff_segments) else 0.0

        return changed_chars / total_original_chars

    def _detect_error_types(
        self,
        original: str,
        correction: str,
        diff_segments: List[DiffSegment],
        what_was_wrong: Optional[str]
    ) -> List[str]:
        """Detect the types of errors present in the correction."""
        error_types = []
        scores: Dict[str, float] = {}

        # Check user explanation for keywords
        if what_was_wrong:
            what_lower = what_was_wrong.lower()
            for error_cat, keywords in self.EXPLANATION_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in what_lower:
                        scores[error_cat.value] = scores.get(error_cat.value, 0) + 1.0

        # Analyze changed segments for patterns
        changed_segments = [s for s in diff_segments if s.operation != 'equal']

        for segment in changed_segments:
            changed_text = segment.original + ' ' + segment.corrected

            for error_cat, patterns in self.ERROR_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, changed_text, re.IGNORECASE):
                        scores[error_cat.value] = scores.get(error_cat.value, 0) + 0.5

        # Check for specific heuristics

        # Incomplete: correction is significantly longer
        if len(correction) > len(original) * 1.3:
            scores[ErrorCategory.INCOMPLETE.value] = scores.get(ErrorCategory.INCOMPLETE.value, 0) + 0.8

        # Verbose: correction is significantly shorter
        if len(correction) < len(original) * 0.7:
            scores[ErrorCategory.VERBOSE.value] = scores.get(ErrorCategory.VERBOSE.value, 0) + 0.8

        # Code errors: contains code blocks
        if '```' in original or '```' in correction:
            # More likely to be code-related errors
            for code_cat in [ErrorCategory.CODE_SYNTAX, ErrorCategory.CODE_LOGIC, ErrorCategory.CODE_STYLE]:
                scores[code_cat.value] = scores.get(code_cat.value, 0) + 0.3

        # Sort by score and return top categories
        sorted_errors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        error_types = [err_type for err_type, score in sorted_errors if score >= 0.5]

        # Always return at least one type
        if not error_types:
            error_types = [ErrorCategory.OTHER.value]

        return error_types

    def _extract_error_patterns(
        self,
        original: str,
        correction: str,
        diff_segments: List[DiffSegment],
        error_types: List[str]
    ) -> List[Dict]:
        """Extract specific error patterns to avoid."""
        patterns = []

        for segment in diff_segments:
            if segment.operation == 'equal':
                continue

            # Skip very small changes (likely typos)
            if len(segment.original) < 3 and len(segment.corrected) < 3:
                continue

            pattern = {
                'original_fragment': segment.original.strip()[:200],
                'corrected_fragment': segment.corrected.strip()[:200],
                'operation': segment.operation,
                'error_types': error_types,
            }

            # Add context (surrounding text)
            pos = segment.position
            context_before = original[max(0, pos-50):pos].strip()
            context_after = original[pos+len(segment.original):pos+len(segment.original)+50].strip()

            if context_before:
                pattern['context_before'] = context_before[-50:]
            if context_after:
                pattern['context_after'] = context_after[:50]

            # Detect pattern type
            if segment.operation == 'replace':
                # Check if it's a simple word/phrase replacement
                orig_words = segment.original.split()
                corr_words = segment.corrected.split()

                if len(orig_words) == len(corr_words) == 1:
                    pattern['pattern_type'] = 'word_replacement'
                elif len(orig_words) <= 3 and len(corr_words) <= 3:
                    pattern['pattern_type'] = 'phrase_replacement'
                else:
                    pattern['pattern_type'] = 'section_rewrite'

            elif segment.operation == 'insert':
                pattern['pattern_type'] = 'missing_content'

            elif segment.operation == 'delete':
                pattern['pattern_type'] = 'excess_content'

            patterns.append(pattern)

        return patterns

    def _generate_training_example(
        self,
        original: str,
        correction: str,
        query: Optional[str],
        error_types: List[str],
        error_patterns: List[Dict]
    ) -> Dict:
        """Generate a training example suitable for fine-tuning."""

        # Build explanation of what was wrong
        explanation_parts = []

        if error_types:
            explanation_parts.append(f"Error types: {', '.join(error_types)}")

        for pattern in error_patterns[:3]:  # Limit to top 3 patterns
            if pattern.get('original_fragment') and pattern.get('corrected_fragment'):
                explanation_parts.append(
                    f"Changed '{pattern['original_fragment'][:50]}' to '{pattern['corrected_fragment'][:50]}'"
                )

        explanation = "; ".join(explanation_parts) if explanation_parts else "General correction"

        return {
            'error_type': error_types[0] if error_types else 'other',
            'original': original,
            'corrected': correction,
            'explanation': explanation,
            'query': query or '',
            # Format for instruction fine-tuning
            'instruction': f"Correct this response: {original[:500]}...",
            'input': query or "No query provided",
            'output': correction,
        }

    def process_corrections_from_db(
        self,
        db: FeedbackDB,
        limit: int = 100,
        mark_processed: bool = True
    ) -> List[CorrectionAnalysis]:
        """
        Process all unprocessed corrections from FeedbackDB.

        Args:
            db: FeedbackDB instance
            limit: Maximum number of corrections to process
            mark_processed: Whether to mark corrections as processed

        Returns:
            List of CorrectionAnalysis objects
        """
        # Get unprocessed corrections
        corrections = db.get_recent_feedback(
            limit=limit,
            feedback_type='correction',
            include_processed=False
        )

        analyses = []

        for fb in corrections:
            if not fb.get('correction') or not fb.get('original_response'):
                continue

            try:
                analysis = self.analyze_correction(
                    original=fb['original_response'],
                    correction=fb['correction'],
                    query=fb.get('original_query'),
                    what_was_wrong=fb.get('what_was_wrong')
                )
                analyses.append(analysis)

                # Mark as processed
                if mark_processed:
                    db.mark_as_processed(
                        fb['feedback_id'],
                        training_format='correction_analysis'
                    )

            except Exception as e:
                # Log but don't fail on individual corrections
                print(f"Error analyzing correction {fb.get('feedback_id')}: {e}")
                continue

        return analyses

    def export_training_data(
        self,
        analyses: List[CorrectionAnalysis],
        output_path: Path,
        format: str = 'jsonl'
    ) -> int:
        """
        Export analyzed corrections as training data.

        Args:
            analyses: List of CorrectionAnalysis objects
            output_path: Where to save the training data
            format: Output format ('jsonl' or 'json')

        Returns:
            Number of examples exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0

        if format == 'jsonl':
            with open(output_path, 'w') as f:
                for analysis in analyses:
                    if analysis.training_example:
                        f.write(json.dumps(analysis.training_example) + '\n')
                        count += 1
        else:
            data = [a.training_example for a in analyses if a.training_example]
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            count = len(data)

        return count

    def get_error_statistics(
        self,
        analyses: List[CorrectionAnalysis]
    ) -> Dict[str, Any]:
        """
        Get statistics about error types from a list of analyses.

        Args:
            analyses: List of CorrectionAnalysis objects

        Returns:
            Dictionary with error statistics
        """
        stats = {
            'total_corrections': len(analyses),
            'error_type_counts': {},
            'avg_similarity': 0.0,
            'avg_change_ratio': 0.0,
            'common_patterns': [],
        }

        if not analyses:
            return stats

        # Count error types
        for analysis in analyses:
            for err_type in analysis.error_types:
                stats['error_type_counts'][err_type] = (
                    stats['error_type_counts'].get(err_type, 0) + 1
                )

        # Calculate averages
        stats['avg_similarity'] = sum(a.similarity_ratio for a in analyses) / len(analyses)
        stats['avg_change_ratio'] = sum(a.change_ratio for a in analyses) / len(analyses)

        # Find common patterns
        pattern_counts: Dict[str, int] = {}
        for analysis in analyses:
            for pattern in analysis.error_patterns:
                pattern_type = pattern.get('pattern_type', 'unknown')
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1

        stats['common_patterns'] = sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return stats


# ===== Phase 1.2.6: Confidence Adjuster =====

class ConfidenceAdjuster:
    """
    Adjusts SAM's confidence based on feedback patterns.

    Tracks historical accuracy per domain/topic and provides confidence
    modifiers to help SAM know when to be more or less confident, and
    when to suggest escalating to Claude.

    Usage:
        adjuster = ConfidenceAdjuster()

        # Get confidence modifier for a domain/topic
        modifier = adjuster.get_confidence_modifier("code", "python")
        adjusted_confidence = base_confidence + modifier

        # Check if should escalate
        if adjuster.should_suggest_escalation("reasoning", "math"):
            escalate_to_claude()

        # Get domain statistics
        stats = adjuster.get_domain_stats()
    """

    # Domain expertise levels (baseline confidence)
    DOMAIN_EXPERTISE = {
        "code": 0.7,       # SAM is trained on code, high baseline
        "roleplay": 0.8,   # SAM's personality, very high baseline
        "general": 0.5,    # General knowledge, medium baseline
        "factual": 0.4,    # Facts may need verification
        "reasoning": 0.4,  # Complex reasoning, lower baseline
        "creative": 0.6,   # Creative tasks, decent baseline
        "planning": 0.5,   # Planning tasks, medium baseline
    }

    # Escalation thresholds per domain
    ESCALATION_THRESHOLDS = {
        "code": 0.3,       # Escalate if accuracy drops below 30%
        "roleplay": 0.2,   # Rarely escalate roleplay
        "general": 0.4,    # Escalate if below 40%
        "factual": 0.5,    # Factual queries need higher accuracy
        "reasoning": 0.5,  # Reasoning needs higher accuracy
        "creative": 0.3,   # Creative is more subjective
        "planning": 0.4,   # Planning needs decent accuracy
    }

    # Recent feedback window size
    RECENT_WINDOW_SIZE = 20

    # Minimum feedback count for reliable statistics
    MIN_FEEDBACK_FOR_STATS = 5

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the confidence adjuster.

        Uses the same database as FeedbackDB.
        """
        if db_path is None:
            self.db_path = get_feedback_db_path()
        else:
            self.db_path = db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure the confidence_tracking table exists."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS confidence_tracking (
                domain TEXT NOT NULL,
                topic TEXT NOT NULL DEFAULT 'general',
                total_responses INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                corrections_received INTEGER DEFAULT 0,
                accuracy_rate REAL DEFAULT 0.5,
                error_types TEXT DEFAULT '{}',
                recent_feedback TEXT DEFAULT '[]',
                trend_direction TEXT DEFAULT 'stable',
                trend_strength REAL DEFAULT 0.0,
                confidence_modifier REAL DEFAULT 0.0,
                first_feedback_at REAL,
                last_feedback_at REAL,
                last_recalculated_at REAL,
                PRIMARY KEY (domain, topic)
            );
            CREATE INDEX IF NOT EXISTS idx_confidence_domain ON confidence_tracking(domain);
            CREATE INDEX IF NOT EXISTS idx_confidence_modifier ON confidence_tracking(confidence_modifier);
        """)
        conn.commit()
        conn.close()

    def record_feedback(
        self,
        domain: str,
        topic: str = "general",
        is_positive: bool = True,
        is_correction: bool = False,
        error_type: Optional[str] = None
    ):
        """
        Record feedback for confidence tracking.

        Call this when feedback is received to update confidence tracking.

        Args:
            domain: The domain (code, roleplay, general, etc.)
            topic: Specific topic within the domain
            is_positive: Whether the feedback was positive
            is_correction: Whether this was a correction
            error_type: Type of error if applicable (factual, incomplete, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        timestamp = time.time()

        # Normalize domain
        domain = domain.lower() if domain else "general"
        topic = topic.lower() if topic else "general"

        # Get existing record
        cur.execute("""
            SELECT total_responses, positive_feedback, negative_feedback,
                   corrections_received, error_types, recent_feedback,
                   first_feedback_at
            FROM confidence_tracking
            WHERE domain = ? AND topic = ?
        """, (domain, topic))
        row = cur.fetchone()

        if row:
            total, positive, negative, corrections, error_types_json, recent_json, first_at = row
            error_types_dict = json.loads(error_types_json) if error_types_json else {}
            recent = json.loads(recent_json) if recent_json else []
        else:
            total, positive, negative, corrections = 0, 0, 0, 0
            error_types_dict = {}
            recent = []
            first_at = timestamp

        # Update counts
        total += 1
        if is_positive:
            positive += 1
        else:
            negative += 1
        if is_correction:
            corrections += 1

        # Update error types
        if error_type:
            error_types_dict[error_type] = error_types_dict.get(error_type, 0) + 1

        # Update recent feedback (keep last N)
        recent.append({"timestamp": timestamp, "positive": is_positive})
        if len(recent) > self.RECENT_WINDOW_SIZE:
            recent = recent[-self.RECENT_WINDOW_SIZE:]

        # Calculate accuracy rate
        accuracy_rate = positive / total if total > 0 else 0.5

        # Calculate trend
        trend_direction, trend_strength = self._calculate_trend(recent)

        # Calculate confidence modifier
        confidence_modifier = self._calculate_confidence_modifier(
            domain, accuracy_rate, trend_direction, trend_strength, total
        )

        # Update or insert
        if row:
            cur.execute("""
                UPDATE confidence_tracking SET
                    total_responses = ?,
                    positive_feedback = ?,
                    negative_feedback = ?,
                    corrections_received = ?,
                    accuracy_rate = ?,
                    error_types = ?,
                    recent_feedback = ?,
                    trend_direction = ?,
                    trend_strength = ?,
                    confidence_modifier = ?,
                    last_feedback_at = ?,
                    last_recalculated_at = ?
                WHERE domain = ? AND topic = ?
            """, (
                total, positive, negative, corrections,
                accuracy_rate, json.dumps(error_types_dict), json.dumps(recent),
                trend_direction, trend_strength, confidence_modifier,
                timestamp, timestamp,
                domain, topic
            ))
        else:
            cur.execute("""
                INSERT INTO confidence_tracking (
                    domain, topic, total_responses, positive_feedback,
                    negative_feedback, corrections_received, accuracy_rate,
                    error_types, recent_feedback, trend_direction,
                    trend_strength, confidence_modifier,
                    first_feedback_at, last_feedback_at, last_recalculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                domain, topic, total, positive, negative, corrections,
                accuracy_rate, json.dumps(error_types_dict), json.dumps(recent),
                trend_direction, trend_strength, confidence_modifier,
                first_at, timestamp, timestamp
            ))

        conn.commit()
        conn.close()

    def _calculate_trend(self, recent_feedback: List[Dict]) -> Tuple[str, float]:
        """
        Calculate trend direction and strength from recent feedback.

        Returns:
            (trend_direction, trend_strength) where direction is
            'improving', 'declining', or 'stable'
        """
        if len(recent_feedback) < 5:
            return "stable", 0.0

        # Split into first and second half
        mid = len(recent_feedback) // 2
        first_half = recent_feedback[:mid]
        second_half = recent_feedback[mid:]

        # Calculate positive rate for each half
        first_rate = sum(1 for f in first_half if f.get("positive")) / len(first_half)
        second_rate = sum(1 for f in second_half if f.get("positive")) / len(second_half)

        # Calculate trend
        diff = second_rate - first_rate
        strength = min(abs(diff) * 2, 1.0)  # Scale to 0-1

        if diff > 0.1:
            return "improving", strength
        elif diff < -0.1:
            return "declining", strength
        else:
            return "stable", 0.0

    def _calculate_confidence_modifier(
        self,
        domain: str,
        accuracy_rate: float,
        trend_direction: str,
        trend_strength: float,
        total_feedback: int
    ) -> float:
        """
        Calculate confidence modifier from all factors.

        Returns a value between -0.3 and +0.3.
        """
        modifier = 0.0

        # Base expertise level for domain
        base_expertise = self.DOMAIN_EXPERTISE.get(domain, 0.5)

        # Accuracy factor: deviation from expected accuracy
        # If accuracy is better than base, boost confidence
        # If accuracy is worse than base, reduce confidence
        accuracy_delta = accuracy_rate - base_expertise
        modifier += accuracy_delta * 0.3  # Scale to max +-0.3

        # Trend factor
        if trend_direction == "improving":
            modifier += 0.05 * trend_strength
        elif trend_direction == "declining":
            modifier -= 0.1 * trend_strength  # Penalize declining more

        # Confidence in the modifier itself (based on sample size)
        if total_feedback < self.MIN_FEEDBACK_FOR_STATS:
            # Not enough data, reduce the modifier's impact
            modifier *= total_feedback / self.MIN_FEEDBACK_FOR_STATS

        # Clamp to valid range
        return max(-0.3, min(0.3, modifier))

    def get_confidence_modifier(
        self,
        domain: str,
        topic: str = "general"
    ) -> float:
        """
        Get confidence modifier for a domain/topic.

        Args:
            domain: The domain (code, roleplay, general, etc.)
            topic: Specific topic within the domain

        Returns:
            Confidence modifier between -0.3 and +0.3.
            Add this to SAM's base confidence.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        domain = domain.lower() if domain else "general"
        topic = topic.lower() if topic else "general"

        # Try specific topic first
        cur.execute("""
            SELECT confidence_modifier, total_responses
            FROM confidence_tracking
            WHERE domain = ? AND topic = ?
        """, (domain, topic))
        row = cur.fetchone()

        if row and row[1] >= self.MIN_FEEDBACK_FOR_STATS:
            conn.close()
            return row[0]

        # Fall back to domain-level (topic='general')
        if topic != "general":
            cur.execute("""
                SELECT confidence_modifier, total_responses
                FROM confidence_tracking
                WHERE domain = ? AND topic = 'general'
            """, (domain,))
            row = cur.fetchone()

            if row and row[1] >= self.MIN_FEEDBACK_FOR_STATS:
                conn.close()
                return row[0]

        conn.close()

        # No data, return neutral
        return 0.0

    def should_suggest_escalation(
        self,
        domain: str,
        query_type: Optional[str] = None
    ) -> bool:
        """
        Determine if SAM should suggest escalating to Claude.

        Args:
            domain: The domain of the query
            query_type: Optional specific query type/topic

        Returns:
            True if escalation is recommended
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        domain = domain.lower() if domain else "general"

        # Get domain statistics
        cur.execute("""
            SELECT accuracy_rate, trend_direction, trend_strength, total_responses
            FROM confidence_tracking
            WHERE domain = ? AND topic = 'general'
        """, (domain,))
        row = cur.fetchone()
        conn.close()

        if not row:
            # No data for this domain, use default threshold
            return False

        accuracy_rate, trend_direction, trend_strength, total = row

        # Not enough data to make a recommendation
        if total < self.MIN_FEEDBACK_FOR_STATS:
            return False

        # Get escalation threshold for this domain
        threshold = self.ESCALATION_THRESHOLDS.get(domain, 0.4)

        # Check accuracy against threshold
        if accuracy_rate < threshold:
            return True

        # Check if declining rapidly
        if trend_direction == "declining" and trend_strength > 0.5:
            # Declining trend might warrant escalation
            if accuracy_rate < threshold + 0.15:
                return True

        return False

    def get_domain_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all tracked domains.

        Returns:
            Dictionary with stats per domain including:
            - accuracy_rate
            - trend
            - confidence_modifier
            - error_distribution
            - escalation_recommended
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT domain, topic, total_responses, positive_feedback,
                   negative_feedback, corrections_received, accuracy_rate,
                   error_types, trend_direction, trend_strength,
                   confidence_modifier, first_feedback_at, last_feedback_at
            FROM confidence_tracking
            ORDER BY domain, topic
        """)

        rows = cur.fetchall()
        conn.close()

        stats = {
            "domains": {},
            "summary": {
                "total_domains": 0,
                "total_feedback_tracked": 0,
                "average_accuracy": 0.0,
                "domains_needing_attention": [],
            }
        }

        total_accuracy = 0.0
        domain_count = 0

        for row in rows:
            row_dict = dict(row)
            domain = row_dict["domain"]
            topic = row_dict["topic"]

            if domain not in stats["domains"]:
                stats["domains"][domain] = {
                    "topics": {},
                    "overall_accuracy": 0.0,
                    "total_feedback": 0,
                    "confidence_modifier": 0.0,
                    "escalation_recommended": False,
                }

            # Parse JSON fields
            error_types_data = json.loads(row_dict["error_types"]) if row_dict["error_types"] else {}

            topic_stats = {
                "total_responses": row_dict["total_responses"],
                "positive_feedback": row_dict["positive_feedback"],
                "negative_feedback": row_dict["negative_feedback"],
                "corrections_received": row_dict["corrections_received"],
                "accuracy_rate": round(row_dict["accuracy_rate"], 3),
                "trend": {
                    "direction": row_dict["trend_direction"],
                    "strength": round(row_dict["trend_strength"], 3),
                },
                "confidence_modifier": round(row_dict["confidence_modifier"], 3),
                "error_distribution": error_types_data,
                "first_feedback": datetime.fromtimestamp(row_dict["first_feedback_at"]).isoformat() if row_dict["first_feedback_at"] else None,
                "last_feedback": datetime.fromtimestamp(row_dict["last_feedback_at"]).isoformat() if row_dict["last_feedback_at"] else None,
            }

            stats["domains"][domain]["topics"][topic] = topic_stats
            stats["domains"][domain]["total_feedback"] += row_dict["total_responses"]

            # Track domain-level stats (from 'general' topic)
            if topic == "general":
                stats["domains"][domain]["overall_accuracy"] = round(row_dict["accuracy_rate"], 3)
                stats["domains"][domain]["confidence_modifier"] = round(row_dict["confidence_modifier"], 3)
                stats["domains"][domain]["escalation_recommended"] = self.should_suggest_escalation(domain)

                total_accuracy += row_dict["accuracy_rate"]
                domain_count += 1

            stats["summary"]["total_feedback_tracked"] += row_dict["total_responses"]

        stats["summary"]["total_domains"] = len(stats["domains"])
        stats["summary"]["average_accuracy"] = round(total_accuracy / domain_count, 3) if domain_count > 0 else 0.0

        # Find domains needing attention
        for domain, domain_stats in stats["domains"].items():
            if domain_stats["escalation_recommended"]:
                stats["summary"]["domains_needing_attention"].append(domain)

        return stats

    def get_topic_error_patterns(self, domain: str, topic: str = "general") -> Dict[str, int]:
        """
        Get common error types for a domain/topic.

        Useful for understanding what kinds of mistakes SAM makes
        in specific areas.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT error_types FROM confidence_tracking
            WHERE domain = ? AND topic = ?
        """, (domain.lower(), topic.lower()))

        row = cur.fetchone()
        conn.close()

        if row and row[0]:
            return json.loads(row[0])
        return {}

    def reset_topic(self, domain: str, topic: str = "general"):
        """
        Reset confidence tracking for a specific domain/topic.

        Use this when SAM has been retrained or significantly updated.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM confidence_tracking
            WHERE domain = ? AND topic = ?
        """, (domain.lower(), topic.lower()))

        conn.commit()
        conn.close()

    def reset_all(self):
        """
        Reset all confidence tracking data.

        Use this after a major retraining of SAM.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM confidence_tracking")
        conn.commit()
        conn.close()


# ===== Integration helper =====

def record_feedback_for_confidence(
    feedback_entry: FeedbackEntry,
    adjuster: Optional['ConfidenceAdjuster'] = None
):
    """
    Helper to automatically update confidence tracking when feedback is saved.

    Call this after saving feedback to update confidence tracking.
    """
    if adjuster is None:
        adjuster = get_confidence_adjuster()

    # Determine if positive/negative
    is_positive = False
    if feedback_entry.feedback_type == "rating":
        is_positive = feedback_entry.rating == 1
    elif feedback_entry.feedback_type == "preference":
        # Preference implies the response wasn't ideal
        is_positive = False
    elif feedback_entry.feedback_type == "correction":
        # Correction is negative feedback
        is_positive = False
    elif feedback_entry.feedback_type == "flag":
        # Flags are always negative
        is_positive = False

    # Determine error type
    error_type = None
    if feedback_entry.feedback_type == "flag":
        error_type = feedback_entry.flag_type
    elif feedback_entry.feedback_type == "correction":
        error_type = feedback_entry.correction_type

    # Extract topic from query if possible
    topic = "general"
    query = feedback_entry.original_query.lower()

    # Simple topic extraction based on keywords
    if any(kw in query for kw in ["python", "def ", "import ", "class "]):
        topic = "python"
    elif any(kw in query for kw in ["javascript", "typescript", "const ", "function "]):
        topic = "javascript"
    elif any(kw in query for kw in ["rust", "fn ", "impl ", "cargo"]):
        topic = "rust"
    elif any(kw in query for kw in ["math", "calculate", "equation"]):
        topic = "math"
    elif any(kw in query for kw in ["explain", "what is", "how does"]):
        topic = "explanation"

    adjuster.record_feedback(
        domain=feedback_entry.domain,
        topic=topic,
        is_positive=is_positive,
        is_correction=(feedback_entry.feedback_type == "correction"),
        error_type=error_type
    )


# ===== Singleton instances =====

_confidence_adjuster = None


def get_confidence_adjuster() -> ConfidenceAdjuster:
    """Get the singleton ConfidenceAdjuster instance."""
    global _confidence_adjuster
    if _confidence_adjuster is None:
        _confidence_adjuster = ConfidenceAdjuster()
    return _confidence_adjuster


# ===== Phase 1.2.7: Training Example Generator =====

# External storage paths for training data
FEEDBACK_TRAINING_PATH = Path("/Volumes/David External/sam_training/feedback_derived")
DISTILLATION_PATH = Path("/Volumes/David External/sam_training/distilled/exports")
MERGED_TRAINING_PATH = Path("/Volumes/David External/sam_training/merged")


class TrainingExampleGenerator:
    """
    Generates training examples from analyzed corrections and feedback.

    Phase 1.2.7: Converts user corrections and feedback into multiple training
    formats suitable for fine-tuning SAM.

    Training Formats:
        1. Instruction (Alpaca-style):
           {"instruction": "...", "input": "...", "output": "..."}

        2. Error Correction:
           {"original": "...", "corrected": "...", "error_type": "..."}

        3. DPO Preference Pairs:
           {"prompt": "...", "chosen": "...", "rejected": "..."}

    Usage:
        generator = TrainingExampleGenerator()

        # Generate instruction format training data
        result = generator.generate_training_data(format_type="instruction")

        # Generate DPO pairs
        result = generator.generate_training_data(format_type="dpo")

        # Merge with distillation training data
        result = generator.merge_with_distillation()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the training example generator.

        Args:
            db_path: Optional explicit database path. If None, uses default feedback DB.
        """
        if db_path is None:
            self.db_path = get_feedback_db_path()
        else:
            self.db_path = db_path

        self.feedback_training_path = FEEDBACK_TRAINING_PATH
        self.distillation_path = DISTILLATION_PATH
        self.merged_path = MERGED_TRAINING_PATH

        # Ensure directories exist if external drive is mounted
        if Path("/Volumes/David External").exists():
            self.feedback_training_path.mkdir(parents=True, exist_ok=True)
            self.merged_path.mkdir(parents=True, exist_ok=True)

        self.analyzer = CorrectionAnalyzer()
        self._seen_hashes: set = set()  # For deduplication

    def _compute_example_hash(self, query: str, response: str) -> str:
        """Compute a hash for deduplication."""
        content = f"{query.strip().lower()}:{response.strip().lower()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_duplicate(self, query: str, response: str) -> bool:
        """Check if this example is a duplicate."""
        h = self._compute_example_hash(query, response)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    def _get_feedback_entries(
        self,
        min_quality: float = 0.4,
        feedback_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get feedback entries suitable for training.

        Args:
            min_quality: Minimum quality weight threshold
            feedback_types: Filter by specific feedback types

        Returns:
            List of feedback dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = """
            SELECT * FROM feedback
            WHERE quality_weight >= ?
            AND feedback_type != 'flag'
        """
        params: List[Any] = [min_quality]

        if feedback_types:
            placeholders = ",".join("?" * len(feedback_types))
            query += f" AND feedback_type IN ({placeholders})"
            params.extend(feedback_types)

        query += " ORDER BY quality_weight DESC, timestamp DESC"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _format_instruction(self, feedback: Dict, analysis: Optional[CorrectionAnalysis] = None) -> Optional[Dict]:
        """Format feedback as an instruction training example.

        Alpaca-style format:
        {
            "instruction": "User query",
            "input": "SAM's original response (optional context)",
            "output": "Correct response"
        }
        """
        query = feedback.get("original_query", "").strip()
        if not query:
            return None

        if feedback["feedback_type"] == "correction":
            correction = feedback.get("correction", "").strip()
            original = feedback.get("original_response", "").strip()

            if not correction:
                return None

            # Build instruction with context about what was wrong
            what_was_wrong = feedback.get("what_was_wrong", "")
            if what_was_wrong:
                instruction = f"{query}\n\n(Note: A previous response was incorrect. Issue: {what_was_wrong})"
            else:
                instruction = query

            return {
                "instruction": instruction,
                "input": original[:500] if original else "",
                "output": correction,
                "domain": feedback.get("domain", "general"),
                "source": "feedback_correction",
                "quality_weight": feedback.get("quality_weight", 0.5),
                "error_types": analysis.error_types if analysis else [],
            }

        elif feedback["feedback_type"] == "preference":
            preferred = feedback.get("preferred_response", "").strip()
            original = feedback.get("original_response", "").strip()
            comparison = feedback.get("comparison_basis", "")

            if not preferred:
                return None

            # Use the preferred response as the target output
            if comparison:
                instruction = f"{query}\n\n(Preference note: {comparison})"
            else:
                instruction = query

            return {
                "instruction": instruction,
                "input": original[:500] if original else "",
                "output": preferred,
                "domain": feedback.get("domain", "general"),
                "source": "feedback_preference",
                "quality_weight": feedback.get("quality_weight", 0.5),
            }

        elif feedback["feedback_type"] == "rating" and feedback.get("rating") == 1:
            # Positive rating - use original response as good example
            original = feedback.get("original_response", "").strip()
            if not original or len(original) < 50:
                return None

            return {
                "instruction": query,
                "input": "",
                "output": original,
                "domain": feedback.get("domain", "general"),
                "source": "feedback_positive",
                "quality_weight": feedback.get("quality_weight", 0.5),
            }

        return None

    def _format_correction(self, feedback: Dict, analysis: Optional[CorrectionAnalysis] = None) -> Optional[Dict]:
        """Format feedback as error correction training example.

        Format:
        {
            "original": "SAM's incorrect response",
            "corrected": "Corrected response",
            "error_type": "factual|incomplete|etc",
            "query": "Original query",
            "explanation": "What was wrong"
        }
        """
        if feedback["feedback_type"] != "correction":
            return None

        original = feedback.get("original_response", "").strip()
        correction = feedback.get("correction", "").strip()

        if not original or not correction:
            return None

        error_type = "other"
        if analysis and analysis.error_types:
            error_type = analysis.error_types[0]

        return {
            "original": original,
            "corrected": correction,
            "error_type": error_type,
            "query": feedback.get("original_query", ""),
            "explanation": feedback.get("what_was_wrong", ""),
            "domain": feedback.get("domain", "general"),
            "source": "feedback_correction",
            "quality_weight": feedback.get("quality_weight", 0.5),
            "similarity_ratio": analysis.similarity_ratio if analysis else None,
            "change_ratio": analysis.change_ratio if analysis else None,
        }

    def _format_dpo(self, feedback: Dict, analysis: Optional[CorrectionAnalysis] = None) -> Optional[Dict]:
        """Format feedback as DPO preference pair.

        DPO format:
        {
            "prompt": "User query",
            "chosen": "Better response (correction/preference)",
            "rejected": "Worse response (original)"
        }
        """
        query = feedback.get("original_query", "").strip()
        original = feedback.get("original_response", "").strip()

        if not query or not original:
            return None

        chosen = None
        rejected = original

        if feedback["feedback_type"] == "correction":
            chosen = feedback.get("correction", "").strip()
        elif feedback["feedback_type"] == "preference":
            chosen = feedback.get("preferred_response", "").strip()
        elif feedback["feedback_type"] == "rating" and feedback.get("rating") == -1:
            # Negative rating - we have rejected but not chosen
            # Skip unless we have context about what would be better
            return None

        if not chosen or chosen == rejected:
            return None

        return {
            "prompt": query,
            "chosen": chosen,
            "rejected": rejected,
            "domain": feedback.get("domain", "general"),
            "source": "feedback",
            "quality_weight": feedback.get("quality_weight", 0.5),
        }

    def generate_training_data(
        self,
        format_type: str = "instruction",
        output_path: Optional[Path] = None,
        min_quality: float = 0.4,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """Generate training data from feedback.

        Args:
            format_type: Output format - "instruction", "dpo", "correction", or "all"
            output_path: Where to save the JSONL file(s)
            min_quality: Minimum quality weight threshold
            deduplicate: Whether to deduplicate similar examples

        Returns:
            Dictionary with results including count and output path
        """
        self._seen_hashes.clear()

        # Determine which feedback types to include
        if format_type == "dpo":
            feedback_types = ["correction", "preference"]
        elif format_type == "correction":
            feedback_types = ["correction"]
        else:
            feedback_types = None  # All types

        entries = self._get_feedback_entries(min_quality=min_quality, feedback_types=feedback_types)

        if not entries:
            return {
                "count": 0,
                "output_path": None,
                "message": "No feedback entries found matching criteria"
            }

        # Analyze corrections for additional metadata
        analyzed: Dict[str, CorrectionAnalysis] = {}
        for entry in entries:
            if entry["feedback_type"] == "correction" and entry.get("correction") and entry.get("original_response"):
                try:
                    analysis = self.analyzer.analyze_correction(
                        original=entry["original_response"],
                        correction=entry["correction"],
                        query=entry.get("original_query"),
                        what_was_wrong=entry.get("what_was_wrong")
                    )
                    analyzed[entry["feedback_id"]] = analysis
                except Exception:
                    pass

        # Generate examples based on format
        examples = []
        stats = {
            "total_entries": len(entries),
            "duplicates_removed": 0,
            "by_source": {},
            "by_domain": {},
        }

        for entry in entries:
            analysis = analyzed.get(entry["feedback_id"])

            if format_type == "instruction" or format_type == "all":
                example = self._format_instruction(entry, analysis)
                if example:
                    if deduplicate and self._is_duplicate(example.get("instruction", ""), example.get("output", "")):
                        stats["duplicates_removed"] += 1
                        continue
                    example["format"] = "instruction"
                    examples.append(example)

            if format_type == "correction" or format_type == "all":
                example = self._format_correction(entry, analysis)
                if example:
                    if deduplicate and self._is_duplicate(example.get("query", ""), example.get("corrected", "")):
                        stats["duplicates_removed"] += 1
                        continue
                    example["format"] = "correction"
                    examples.append(example)

            if format_type == "dpo" or format_type == "all":
                example = self._format_dpo(entry, analysis)
                if example:
                    if deduplicate and self._is_duplicate(example.get("prompt", ""), example.get("chosen", "")):
                        stats["duplicates_removed"] += 1
                        continue
                    example["format"] = "dpo"
                    examples.append(example)

        # Weight examples by quality score
        examples.sort(key=lambda x: x.get("quality_weight", 0.5), reverse=True)

        # Count statistics
        for ex in examples:
            source = ex.get("source", "unknown")
            domain = ex.get("domain", "general")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

        # Determine output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if Path("/Volumes/David External").exists():
                output_path = self.feedback_training_path / f"feedback_{format_type}_{timestamp}.jsonl"
            else:
                output_path = Path.home() / ".sam" / "training_data" / f"feedback_{format_type}_{timestamp}.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write examples
        with open(output_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")

        return {
            "count": len(examples),
            "output_path": str(output_path),
            "stats": stats
        }

    def merge_with_distillation(
        self,
        output_path: Optional[Path] = None,
        feedback_weight: float = 1.0,
        distillation_weight: float = 1.0
    ) -> Dict[str, Any]:
        """Merge feedback-derived training data with distillation training data.

        Creates a unified training dataset combining:
        1. Feedback-derived examples (corrections, preferences, positive ratings)
        2. Distillation examples (Claude reasoning patterns)

        Args:
            output_path: Where to save the merged JSONL file
            feedback_weight: Weight multiplier for feedback examples
            distillation_weight: Weight multiplier for distillation examples

        Returns:
            Dictionary with merge results
        """
        # Generate fresh feedback training data
        feedback_result = self.generate_training_data(format_type="instruction", deduplicate=True)
        feedback_examples = []

        if feedback_result["output_path"] and Path(feedback_result["output_path"]).exists():
            with open(feedback_result["output_path"], 'r') as f:
                for line in f:
                    if line.strip():
                        example = json.loads(line)
                        example["training_source"] = "feedback"
                        example["weight"] = example.get("quality_weight", 0.5) * feedback_weight
                        feedback_examples.append(example)

        # Load distillation training data
        distillation_examples = []

        if self.distillation_path.exists():
            for jsonl_file in self.distillation_path.glob("distilled_instruction_*.jsonl"):
                try:
                    with open(jsonl_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                example = json.loads(line)
                                example["training_source"] = "distillation"
                                example["weight"] = example.get("quality", 0.5) * distillation_weight
                                distillation_examples.append(example)
                except Exception as e:
                    print(f"Warning: Could not load {jsonl_file}: {e}")

        # Also check for corrections from distillation
        for jsonl_file in self.distillation_path.glob("corrections_*.jsonl"):
            try:
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            example = json.loads(line)
                            example["training_source"] = "distillation_correction"
                            example["weight"] = 0.8 * distillation_weight  # High weight for corrections
                            distillation_examples.append(example)
            except Exception as e:
                print(f"Warning: Could not load {jsonl_file}: {e}")

        # Merge and sort by weight
        all_examples = feedback_examples + distillation_examples
        all_examples.sort(key=lambda x: x.get("weight", 0.5), reverse=True)

        # Determine output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if Path("/Volumes/David External").exists():
                output_path = self.merged_path / f"merged_training_{timestamp}.jsonl"
            else:
                output_path = Path.home() / ".sam" / "training_data" / f"merged_training_{timestamp}.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write merged examples
        with open(output_path, 'w') as f:
            for example in all_examples:
                f.write(json.dumps(example) + "\n")

        return {
            "feedback_count": len(feedback_examples),
            "distillation_count": len(distillation_examples),
            "total_count": len(all_examples),
            "output_path": str(output_path),
        }

    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics about available training data.

        Returns:
            Dictionary with stats about feedback and distillation data
        """
        stats = {
            "feedback": {
                "total_corrections": 0,
                "total_preferences": 0,
                "total_positive_ratings": 0,
                "high_quality_count": 0,
                "avg_quality": 0.0,
            },
            "distillation": {},
            "estimated": {
                "instruction": 0,
                "dpo": 0,
                "correction": 0,
            }
        }

        # Get feedback stats
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM feedback WHERE feedback_type = 'correction'")
        stats["feedback"]["total_corrections"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE feedback_type = 'preference'")
        stats["feedback"]["total_preferences"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE feedback_type = 'rating' AND rating = 1")
        stats["feedback"]["total_positive_ratings"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE quality_weight >= 0.7")
        stats["feedback"]["high_quality_count"] = cur.fetchone()[0]

        cur.execute("SELECT AVG(quality_weight) FROM feedback")
        avg = cur.fetchone()[0]
        stats["feedback"]["avg_quality"] = round(avg, 3) if avg else 0.0

        conn.close()

        # Estimate training examples
        stats["estimated"]["instruction"] = (
            stats["feedback"]["total_corrections"] +
            stats["feedback"]["total_preferences"] +
            stats["feedback"]["total_positive_ratings"]
        )
        stats["estimated"]["dpo"] = (
            stats["feedback"]["total_corrections"] +
            stats["feedback"]["total_preferences"]
        )
        stats["estimated"]["correction"] = stats["feedback"]["total_corrections"]

        # Check distillation stats if available
        try:
            # Try to import and get distillation stats
            distillation_db = Path("/Volumes/David External/sam_training/distilled/distillation.db")
            if distillation_db.exists():
                conn = sqlite3.connect(distillation_db)
                cur = conn.cursor()

                try:
                    cur.execute("SELECT COUNT(*) FROM examples")
                    stats["distillation"]["total_examples"] = cur.fetchone()[0]

                    cur.execute("SELECT COUNT(*) FROM examples WHERE approved = 1")
                    stats["distillation"]["approved_examples"] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    pass  # Tables might not exist

                conn.close()
        except Exception:
            pass

        return stats


# Singleton instance
_training_generator = None


def get_training_generator() -> TrainingExampleGenerator:
    """Get the singleton TrainingExampleGenerator instance."""
    global _training_generator
    if _training_generator is None:
        _training_generator = TrainingExampleGenerator()
    return _training_generator


# ===== CLI interface =====

def main():
    """CLI interface for feedback system."""
    import sys

    if len(sys.argv) < 2:
        print("""
Feedback System CLI

Usage:
    python feedback_system.py stats           - Show feedback statistics
    python feedback_system.py recent [N]      - Show N recent feedback entries
    python feedback_system.py session <id>    - Show session statistics
    python feedback_system.py response <id>   - Show feedback for a response
    python feedback_system.py unprocessed [N] - Show N unprocessed entries

    # Correction Analysis (Phase 1.2.5)
    python feedback_system.py analyze-corrections [N]  - Analyze N unprocessed corrections
    python feedback_system.py analyze-text <orig> <corr> - Analyze a single correction
    python feedback_system.py export-training [output]  - Export corrections as training data
    python feedback_system.py error-stats              - Show error type statistics

    # Confidence Adjustment (Phase 1.2.6)
    python feedback_system.py confidence-stats         - Show confidence stats by domain
    python feedback_system.py confidence <domain>      - Get confidence modifier for domain
    python feedback_system.py escalate <domain>        - Check if escalation recommended

    # Training Example Generation (Phase 1.2.7)
    python feedback_system.py generate-training [--format instruction|dpo|correction|all] [--min-quality 0.4]
    python feedback_system.py training-stats           - Show training data statistics
    python feedback_system.py merge-training           - Merge feedback with distillation data

    # Dashboard & Review (Phase 1.2.9)
    python feedback_system.py dashboard                - Interactive dashboard with summary
    python feedback_system.py review-feedback          - Interactive feedback review mode
        """)
        return

    db = FeedbackDB()
    cmd = sys.argv[1]

    if cmd == "stats":
        stats = db.get_feedback_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        recent = db.get_recent_feedback(limit=limit)
        for fb in recent:
            print(f"\n[{fb['feedback_id']}] {fb['feedback_type']} @ {datetime.fromtimestamp(fb['timestamp']).isoformat()}")
            print(f"  Response: {fb['response_id']}")
            if fb['rating'] is not None:
                print(f"  Rating: {'Positive' if fb['rating'] == 1 else 'Negative'}")
            if fb['correction']:
                print(f"  Correction: {fb['correction'][:100]}...")
            print(f"  Quality: {fb['quality_weight']:.2f}")

    elif cmd == "session":
        if len(sys.argv) < 3:
            print("Usage: python feedback_system.py session <session_id>")
            return
        session_id = sys.argv[2]
        stats = db.get_session_stats(session_id)
        if stats:
            print(json.dumps(stats, indent=2))
        else:
            print(f"No session found: {session_id}")

    elif cmd == "response":
        if len(sys.argv) < 3:
            print("Usage: python feedback_system.py response <response_id>")
            return
        response_id = sys.argv[2]
        feedback = db.get_feedback_for_response(response_id)
        aggregates = db.get_response_aggregates(response_id)

        if aggregates:
            print("Aggregates:")
            print(json.dumps(aggregates, indent=2))

        if feedback:
            print(f"\nFeedback ({len(feedback)} entries):")
            for fb in feedback:
                print(f"  [{fb['feedback_id']}] {fb['feedback_type']}: rating={fb['rating']}")
        else:
            print(f"No feedback found for response: {response_id}")

    elif cmd == "unprocessed":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        unprocessed = db.get_unprocessed_for_training(limit=limit)
        print(f"Unprocessed feedback for training ({len(unprocessed)} entries):")
        for fb in unprocessed:
            print(f"  [{fb['feedback_id']}] {fb['feedback_type']} quality={fb['quality_weight']:.2f}")

    # ===== Correction Analysis Commands (Phase 1.2.5) =====

    elif cmd == "analyze-corrections":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        analyzer = CorrectionAnalyzer()

        print(f"Analyzing up to {limit} unprocessed corrections...")
        analyses = analyzer.process_corrections_from_db(db, limit=limit, mark_processed=False)

        print(f"\nAnalyzed {len(analyses)} corrections:")
        for i, analysis in enumerate(analyses, 1):
            print(f"\n[{i}] Error type: {analysis.error_type}")
            print(f"    Similarity: {analysis.similarity_ratio:.2%}")
            print(f"    Change ratio: {analysis.change_ratio:.2%}")
            print(f"    Error types: {', '.join(analysis.error_types)}")
            if analysis.error_patterns:
                print(f"    Patterns found: {len(analysis.error_patterns)}")
                for p in analysis.error_patterns[:2]:
                    print(f"      - {p.get('pattern_type', 'unknown')}: '{p.get('original_fragment', '')[:40]}' -> '{p.get('corrected_fragment', '')[:40]}'")

    elif cmd == "analyze-text":
        if len(sys.argv) < 4:
            print("Usage: python feedback_system.py analyze-text <original> <correction>")
            print("Example: python feedback_system.py analyze-text 'Sydney is the capital' 'Canberra is the capital'")
            return

        original = sys.argv[2]
        correction = sys.argv[3]

        analyzer = CorrectionAnalyzer()
        analysis = analyzer.analyze_correction(original, correction)

        print("\n=== Correction Analysis ===")
        print(f"Original:   {analysis.original_text}")
        print(f"Corrected:  {analysis.corrected_text}")
        print(f"\nSimilarity: {analysis.similarity_ratio:.2%}")
        print(f"Change ratio: {analysis.change_ratio:.2%}")
        print(f"Error type: {analysis.error_type}")
        print(f"All error types: {', '.join(analysis.error_types)}")

        if analysis.error_patterns:
            print(f"\nError patterns ({len(analysis.error_patterns)}):")
            for p in analysis.error_patterns:
                print(f"  [{p.get('pattern_type')}]")
                if p.get('original_fragment'):
                    print(f"    Original: '{p['original_fragment']}'")
                if p.get('corrected_fragment'):
                    print(f"    Corrected: '{p['corrected_fragment']}'")

        print("\nTraining example:")
        print(json.dumps(analysis.training_example, indent=2))

    elif cmd == "export-training":
        output_path = sys.argv[2] if len(sys.argv) > 2 else str(Path.home() / ".sam" / "training_data" / "corrections.jsonl")

        analyzer = CorrectionAnalyzer()
        print("Processing corrections from database...")
        analyses = analyzer.process_corrections_from_db(db, limit=1000, mark_processed=True)

        if not analyses:
            print("No unprocessed corrections found.")
            return

        count = analyzer.export_training_data(analyses, Path(output_path))
        print(f"Exported {count} training examples to {output_path}")

        # Also print statistics
        stats = analyzer.get_error_statistics(analyses)
        print(f"\nError type distribution:")
        for err_type, count in sorted(stats['error_type_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {err_type}: {count}")

    elif cmd == "error-stats":
        analyzer = CorrectionAnalyzer()

        # Get corrections without marking as processed
        corrections = db.get_recent_feedback(
            limit=500,
            feedback_type='correction',
            include_processed=True
        )

        analyses = []
        for fb in corrections:
            if fb.get('correction') and fb.get('original_response'):
                try:
                    analysis = analyzer.analyze_correction(
                        original=fb['original_response'],
                        correction=fb['correction'],
                        query=fb.get('original_query'),
                        what_was_wrong=fb.get('what_was_wrong')
                    )
                    analyses.append(analysis)
                except:
                    continue

        if not analyses:
            print("No corrections to analyze.")
            return

        stats = analyzer.get_error_statistics(analyses)

        print(f"\n=== Error Statistics ({stats['total_corrections']} corrections) ===")
        print(f"Average similarity: {stats['avg_similarity']:.2%}")
        print(f"Average change ratio: {stats['avg_change_ratio']:.2%}")

        print(f"\nError type distribution:")
        for err_type, count in sorted(stats['error_type_counts'].items(), key=lambda x: x[1], reverse=True):
            pct = count / stats['total_corrections'] * 100
            print(f"  {err_type}: {count} ({pct:.1f}%)")

        if stats['common_patterns']:
            print(f"\nCommon pattern types:")
            for pattern_type, count in stats['common_patterns']:
                print(f"  {pattern_type}: {count}")

    # ===== Confidence Adjustment Commands (Phase 1.2.6) =====

    elif cmd == "confidence-stats":
        adjuster = ConfidenceAdjuster()
        stats = adjuster.get_domain_stats()

        print("\n=== Confidence Statistics by Domain ===")
        print(f"\nSummary:")
        print(f"  Total domains tracked: {stats['summary']['total_domains']}")
        print(f"  Total feedback tracked: {stats['summary']['total_feedback_tracked']}")
        print(f"  Average accuracy: {stats['summary']['average_accuracy']:.1%}")

        if stats['summary']['domains_needing_attention']:
            print(f"  Domains needing attention: {', '.join(stats['summary']['domains_needing_attention'])}")

        if stats['domains']:
            print("\nBy Domain:")
            for domain, domain_stats in sorted(stats['domains'].items()):
                modifier = domain_stats['confidence_modifier']
                modifier_str = f"+{modifier:.2f}" if modifier >= 0 else f"{modifier:.2f}"
                escalate = " [ESCALATE]" if domain_stats['escalation_recommended'] else ""

                print(f"\n  {domain.upper()}{escalate}")
                print(f"    Accuracy: {domain_stats['overall_accuracy']:.1%}")
                print(f"    Feedback count: {domain_stats['total_feedback']}")
                print(f"    Confidence modifier: {modifier_str}")

                # Show topics if more than just 'general'
                if len(domain_stats['topics']) > 1:
                    print(f"    Topics:")
                    for topic, topic_stats in domain_stats['topics'].items():
                        if topic != 'general':
                            trend_arrow = ""
                            if topic_stats['trend']['direction'] == 'improving':
                                trend_arrow = " /"
                            elif topic_stats['trend']['direction'] == 'declining':
                                trend_arrow = " \\"
                            print(f"      - {topic}: {topic_stats['accuracy_rate']:.1%}{trend_arrow}")
        else:
            print("\nNo confidence data tracked yet.")
            print("Feedback will be tracked as users provide ratings and corrections.")

    elif cmd == "confidence":
        if len(sys.argv) < 3:
            print("Usage: python feedback_system.py confidence <domain> [topic]")
            print("Example: python feedback_system.py confidence code python")
            return

        domain = sys.argv[2]
        topic = sys.argv[3] if len(sys.argv) > 3 else "general"

        adjuster = ConfidenceAdjuster()
        modifier = adjuster.get_confidence_modifier(domain, topic)

        print(f"\nConfidence Modifier for {domain}/{topic}:")
        modifier_str = f"+{modifier:.3f}" if modifier >= 0 else f"{modifier:.3f}"
        print(f"  Modifier: {modifier_str}")

        # Show what this means
        base = adjuster.DOMAIN_EXPERTISE.get(domain.lower(), 0.5)
        adjusted = base + modifier
        print(f"  Base expertise: {base:.1%}")
        print(f"  Adjusted confidence: {adjusted:.1%}")

        # Show error patterns if available
        errors = adjuster.get_topic_error_patterns(domain, topic)
        if errors:
            print(f"\n  Common error types:")
            for err_type, count in sorted(errors.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {err_type}: {count}")

    elif cmd == "escalate":
        if len(sys.argv) < 3:
            print("Usage: python feedback_system.py escalate <domain>")
            print("Example: python feedback_system.py escalate reasoning")
            return

        domain = sys.argv[2]

        adjuster = ConfidenceAdjuster()
        should_escalate = adjuster.should_suggest_escalation(domain)

        print(f"\nEscalation Check for {domain}:")
        if should_escalate:
            print("  RECOMMENDATION: Escalate to Claude")
            print(f"  Reason: Historical accuracy below threshold for this domain")
        else:
            print("  No escalation needed")
            print(f"  SAM is performing adequately in this domain")

        # Show threshold info
        threshold = adjuster.ESCALATION_THRESHOLDS.get(domain.lower(), 0.4)
        print(f"\n  Escalation threshold: {threshold:.1%}")

    elif cmd == "confidence-reset":
        if len(sys.argv) < 3:
            print("Usage: python feedback_system.py confidence-reset <domain> [topic]")
            print("       python feedback_system.py confidence-reset all")
            print("Example: python feedback_system.py confidence-reset code python")
            return

        target = sys.argv[2]
        adjuster = ConfidenceAdjuster()

        if target.lower() == "all":
            confirm = input("Reset ALL confidence tracking data? (yes/no): ")
            if confirm.lower() == "yes":
                adjuster.reset_all()
                print("All confidence tracking data has been reset.")
            else:
                print("Reset cancelled.")
        else:
            topic = sys.argv[3] if len(sys.argv) > 3 else "general"
            adjuster.reset_topic(target, topic)
            print(f"Reset confidence tracking for {target}/{topic}")

    # ===== Training Example Generation Commands (Phase 1.2.7) =====

    elif cmd == "generate-training":
        # Parse format option
        format_type = "instruction"  # default
        min_quality = 0.4

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--format" and i + 1 < len(sys.argv):
                format_type = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--min-quality" and i + 1 < len(sys.argv):
                min_quality = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--no-dedup":
                deduplicate = False
                i += 1
            else:
                i += 1

        valid_formats = ["instruction", "dpo", "correction", "all"]
        if format_type not in valid_formats:
            print(f"Invalid format: {format_type}")
            print(f"Valid formats: {', '.join(valid_formats)}")
            return

        generator = TrainingExampleGenerator()

        print(f"Generating training data (format: {format_type}, min_quality: {min_quality})...")
        result = generator.generate_training_data(
            format_type=format_type,
            min_quality=min_quality,
            deduplicate=True
        )

        if result["count"] == 0:
            print("No training examples generated.")
            print(result.get("message", "Check feedback database for entries."))
            return

        print(f"\nGenerated {result['count']} training examples")
        print(f"Output: {result['output_path']}")

        if result.get("stats"):
            stats = result["stats"]
            print(f"\nStatistics:")
            print(f"  Total feedback entries: {stats['total_entries']}")
            print(f"  Duplicates removed: {stats['duplicates_removed']}")

            if stats.get("by_source"):
                print(f"  By source:")
                for source, count in stats["by_source"].items():
                    print(f"    - {source}: {count}")

            if stats.get("by_domain"):
                print(f"  By domain:")
                for domain, count in stats["by_domain"].items():
                    print(f"    - {domain}: {count}")

    elif cmd == "training-stats":
        generator = TrainingExampleGenerator()
        stats = generator.get_training_stats()

        print("\n=== Training Data Statistics ===")
        print("\nFeedback-derived:")
        print(f"  Corrections: {stats['feedback']['total_corrections']}")
        print(f"  Preferences: {stats['feedback']['total_preferences']}")
        print(f"  Positive ratings: {stats['feedback']['total_positive_ratings']}")
        print(f"  High quality (>0.7): {stats['feedback']['high_quality_count']}")
        print(f"  Average quality: {stats['feedback']['avg_quality']:.3f}")

        print("\nEstimated training examples:")
        print(f"  Instruction format: ~{stats['estimated']['instruction']}")
        print(f"  DPO format: ~{stats['estimated']['dpo']}")
        print(f"  Correction format: ~{stats['estimated']['correction']}")

        if stats.get("distillation"):
            print("\nDistillation data:")
            for key, value in stats["distillation"].items():
                print(f"  {key}: {value}")

    elif cmd == "merge-training":
        generator = TrainingExampleGenerator()

        print("Merging feedback and distillation training data...")
        result = generator.merge_with_distillation()

        print(f"\nMerge complete:")
        print(f"  Feedback examples: {result['feedback_count']}")
        print(f"  Distillation examples: {result['distillation_count']}")
        print(f"  Total: {result['total_count']}")
        print(f"  Output: {result['output_path']}")

    # ===== Dashboard & Review Commands (Phase 1.2.9) =====

    elif cmd == "dashboard":
        # Interactive dashboard showing feedback summary
        dashboard_data = db.get_dashboard_data()

        # ANSI color codes
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        DIM = "\033[2m"

        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}{CYAN}  SAM Feedback Dashboard{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")

        # Today's summary
        summary = dashboard_data["summary"]
        print(f"\n{BOLD}Today's Summary ({summary['date']}){RESET}")
        print(f"  Total feedback: {summary['total']}")

        if summary['positive'] > 0 or summary['negative'] > 0:
            sentiment_pct = summary['sentiment_ratio'] * 100
            sentiment_color = GREEN if sentiment_pct >= 70 else (YELLOW if sentiment_pct >= 50 else RED)
            print(f"  {GREEN}Positive:{RESET} {summary['positive']}  {RED}Negative:{RESET} {summary['negative']}  "
                  f"({sentiment_color}{sentiment_pct:.0f}% positive{RESET})")

        if summary['corrections'] > 0:
            print(f"  {YELLOW}Corrections:{RESET} {summary['corrections']}")
        if summary['preferences'] > 0:
            print(f"  Preferences: {summary['preferences']}")
        if summary['flags'] > 0:
            print(f"  {RED}Flags:{RESET} {summary['flags']}")

        # Domain breakdown
        domain_breakdown = dashboard_data["domain_breakdown"]
        if domain_breakdown:
            print(f"\n{BOLD}Domain Accuracy (7 days){RESET}")
            for domain, stats in sorted(domain_breakdown.items(), key=lambda x: x[1]["total"], reverse=True):
                accuracy_pct = stats["accuracy"] * 100
                accuracy_color = GREEN if accuracy_pct >= 70 else (YELLOW if accuracy_pct >= 50 else RED)
                bar_len = int(stats["accuracy"] * 20)
                bar = f"[{'#' * bar_len}{'-' * (20 - bar_len)}]"
                print(f"  {domain:12} {accuracy_color}{accuracy_pct:5.1f}%{RESET} {bar} ({stats['total']} samples)")

        # Training status
        training = dashboard_data["training_status"]
        print(f"\n{BOLD}Training Data Status{RESET}")
        print(f"  Unprocessed: {training['unprocessed']}")
        print(f"  Processed: {training['processed']}")
        print(f"  High quality pending: {training['high_quality_pending']}")
        if training['ready_for_export']:
            print(f"  {GREEN}Ready for training export!{RESET}")

        # Recent corrections needing review
        corrections = dashboard_data["recent_corrections"]
        unprocessed_corrections = [c for c in corrections if not c["processed"]]
        if unprocessed_corrections:
            print(f"\n{BOLD}Recent Corrections Needing Review{RESET}")
            for i, corr in enumerate(unprocessed_corrections[:5], 1):
                domain_str = f"[{corr['domain']}]"
                print(f"\n  {DIM}{i}. {corr['timestamp']}{RESET} {CYAN}{domain_str}{RESET}")
                print(f"     Q: {corr['query']}")
                if corr['what_was_wrong']:
                    print(f"     {RED}Issue: {corr['what_was_wrong']}{RESET}")

            if len(unprocessed_corrections) > 5:
                print(f"\n  {DIM}... and {len(unprocessed_corrections) - 5} more{RESET}")
            print(f"\n  {DIM}Run 'python feedback_system.py review-feedback' to review{RESET}")

        # Trends
        trends = dashboard_data["trends"]
        declining_domains = [d for d, info in trends.items() if info["trend"] == "declining"]
        improving_domains = [d for d, info in trends.items() if info["trend"] == "improving"]

        if declining_domains or improving_domains:
            print(f"\n{BOLD}7-Day Trends{RESET}")
            for domain in improving_domains:
                print(f"  {GREEN}/{RESET} {domain} is improving")
            for domain in declining_domains:
                print(f"  {RED}\\{RESET} {domain} is declining")

        print(f"\n{DIM}Generated at: {dashboard_data['generated_at']}{RESET}")
        print(f"{BOLD}{'='*60}{RESET}\n")

    elif cmd == "review-feedback":
        # Interactive review mode for feedback
        corrections = db.get_recent_feedback(
            limit=100,
            feedback_type='correction',
            include_processed=True
        )

        if not corrections:
            print("No corrections to review.")
            return

        # ANSI codes
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        DIM = "\033[2m"
        CLEAR = "\033[2J\033[H"

        current_idx = 0

        def show_feedback(idx):
            """Display a single feedback entry."""
            fb = corrections[idx]
            processed_str = f"{GREEN}[PROCESSED]{RESET}" if fb.get("processed") else f"{YELLOW}[PENDING]{RESET}"

            print(f"{CLEAR}")
            print(f"{BOLD}{'='*60}{RESET}")
            print(f"{BOLD}Feedback Review{RESET} - {idx + 1}/{len(corrections)} {processed_str}")
            print(f"{BOLD}{'='*60}{RESET}")
            print(f"\n{DIM}ID: {fb['feedback_id']}{RESET}")
            print(f"{DIM}Time: {datetime.fromtimestamp(fb['timestamp']).isoformat()}{RESET}")
            print(f"{DIM}Domain: {fb.get('domain', 'general')}{RESET}")
            print(f"{DIM}Quality: {fb.get('quality_weight', 0):.2f}{RESET}")

            print(f"\n{BOLD}{CYAN}Original Query:{RESET}")
            print(f"  {fb.get('original_query', 'N/A')}")

            print(f"\n{BOLD}{RED}SAM's Response:{RESET}")
            response = fb.get('original_response', 'N/A')
            # Word wrap at 70 chars
            for line in response.split('\n'):
                while len(line) > 70:
                    print(f"  {line[:70]}")
                    line = line[70:]
                print(f"  {line}")

            print(f"\n{BOLD}{GREEN}Correction:{RESET}")
            correction = fb.get('correction', 'N/A')
            for line in correction.split('\n'):
                while len(line) > 70:
                    print(f"  {line[:70]}")
                    line = line[70:]
                print(f"  {line}")

            if fb.get('what_was_wrong'):
                print(f"\n{BOLD}{YELLOW}What was wrong:{RESET}")
                print(f"  {fb.get('what_was_wrong')}")

            print(f"\n{BOLD}{'='*60}{RESET}")
            print(f"{DIM}Commands: [n]ext  [p]revious  [m]ark processed  [e]dit  [q]uit{RESET}")

        def get_single_key():
            """Get a single keypress without Enter."""
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

        print(f"\n{BOLD}Interactive Feedback Review{RESET}")
        print(f"Loaded {len(corrections)} corrections")
        print(f"Press any key to start...")

        try:
            get_single_key()
        except:
            input()

        while True:
            show_feedback(current_idx)

            try:
                key = get_single_key().lower()
            except:
                key = input("\nCommand: ").strip().lower()
                if key:
                    key = key[0]

            if key == 'q':
                print(f"\n{GREEN}Exiting review mode.{RESET}\n")
                break

            elif key == 'n':
                if current_idx < len(corrections) - 1:
                    current_idx += 1
                else:
                    print(f"\n{YELLOW}Already at last entry{RESET}")
                    try:
                        get_single_key()
                    except:
                        input()

            elif key == 'p':
                if current_idx > 0:
                    current_idx -= 1
                else:
                    print(f"\n{YELLOW}Already at first entry{RESET}")
                    try:
                        get_single_key()
                    except:
                        input()

            elif key == 'm':
                fb = corrections[current_idx]
                if db.mark_as_processed(fb['feedback_id'], training_format='reviewed'):
                    corrections[current_idx]['processed'] = 1
                    print(f"\n{GREEN}Marked as processed!{RESET}")
                else:
                    print(f"\n{RED}Failed to mark as processed{RESET}")
                try:
                    import time as t
                    t.sleep(0.5)
                except:
                    pass

            elif key == 'e':
                fb = corrections[current_idx]
                print(f"\n{BOLD}Edit correction{RESET}")
                print("Enter new correction (press Enter twice to finish, or 'cancel' to abort):")

                lines = []
                while True:
                    try:
                        line = input()
                    except EOFError:
                        break
                    if line.lower() == 'cancel':
                        lines = []
                        break
                    if line == '' and lines and lines[-1] == '':
                        lines.pop()  # Remove trailing empty line
                        break
                    lines.append(line)

                if lines:
                    new_correction = '\n'.join(lines)
                    if db.update_feedback(fb['feedback_id'], correction=new_correction):
                        corrections[current_idx]['correction'] = new_correction
                        print(f"{GREEN}Correction updated!{RESET}")
                    else:
                        print(f"{RED}Failed to update correction{RESET}")
                else:
                    print(f"{YELLOW}Edit cancelled{RESET}")

                try:
                    import time as t
                    t.sleep(0.5)
                except:
                    pass

            elif key == 'j':
                # Jump to specific entry
                print(f"\nJump to entry (1-{len(corrections)}): ", end='')
                try:
                    num = int(input().strip())
                    if 1 <= num <= len(corrections):
                        current_idx = num - 1
                    else:
                        print(f"{RED}Invalid entry number{RESET}")
                        try:
                            import time as t
                            t.sleep(0.5)
                        except:
                            pass
                except ValueError:
                    print(f"{RED}Invalid number{RESET}")
                    try:
                        import time as t
                        t.sleep(0.5)
                    except:
                        pass

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
