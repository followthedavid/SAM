#!/usr/bin/env python3
"""
RAG Quality Feedback Loop for SAM (Phase 2.2.9)

Tracks the quality of RAG (Retrieval-Augmented Generation) results and uses
feedback to improve future retrievals. Implements a learning loop that:

1. Tracks which retrieved sources were actually used in responses
2. Records user feedback (positive/negative) after RAG-assisted responses
3. Identifies which sources are most helpful per project
4. Adjusts relevance scores based on historical performance

Integration:
    - Works with relevance_scorer.py to adjust scores
    - Works with code_indexer.py and doc_indexer for source tracking
    - Stores data in SQLite on external drive

Usage:
    from rag_feedback import (
        RAGFeedbackTracker, get_rag_feedback_tracker,
        record_rag_feedback, get_source_quality_scores,
        adjust_relevance_score
    )

    tracker = get_rag_feedback_tracker()

    # Record feedback after a RAG-assisted response
    tracker.record_rag_feedback(
        query="How does semantic memory work?",
        sources=[
            {"id": "src_123", "file_path": "/path/to/file.py", "score": 0.85},
            {"id": "src_456", "file_path": "/path/to/other.py", "score": 0.72}
        ],
        used_source_ids=["src_123"],  # Which sources were actually cited
        rating=1,  # +1 positive, -1 negative, 0 neutral
        project_id="sam_brain"
    )

    # Get quality scores for sources in a project
    scores = tracker.get_source_quality_scores(project_id="sam_brain")

    # Adjust a base relevance score using historical feedback
    adjusted = tracker.adjust_relevance_score(
        source_id="src_123",
        base_score=0.75,
        project_id="sam_brain"
    )

Storage: /Volumes/David External/sam_memory/rag_feedback.db
"""

import json
import sqlite3
import hashlib
import time
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

# =============================================================================
# Storage Configuration
# =============================================================================

# Primary storage on external drive
EXTERNAL_RAG_FEEDBACK_PATH = Path("/Volumes/David External/sam_memory/rag_feedback.db")
LOCAL_RAG_FEEDBACK_PATH = Path.home() / ".sam" / "rag_feedback.db"


def get_rag_feedback_db_path() -> Path:
    """Get RAG feedback database path, preferring external drive."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_RAG_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_RAG_FEEDBACK_PATH
    LOCAL_RAG_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOCAL_RAG_FEEDBACK_PATH


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RAGFeedbackEntry:
    """A single RAG feedback record."""
    feedback_id: str
    query: str
    query_hash: str
    sources: List[Dict]  # List of {id, file_path, score, name, type}
    used_source_ids: List[str]  # IDs of sources actually used in response
    unused_source_ids: List[str]  # IDs of sources retrieved but not used
    rating: int  # +1 positive, -1 negative, 0 neutral
    project_id: Optional[str]
    response_id: Optional[str]  # Link to the response if available
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'RAGFeedbackEntry':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SourceQualityMetrics:
    """Quality metrics for a single source."""
    source_id: str
    file_path: str
    project_id: Optional[str]

    # Usage stats
    times_retrieved: int = 0
    times_used: int = 0
    times_unused: int = 0

    # Feedback stats
    positive_feedback_when_used: int = 0
    negative_feedback_when_used: int = 0
    positive_feedback_when_unused: int = 0
    negative_feedback_when_unused: int = 0

    # Computed metrics
    usage_rate: float = 0.0  # times_used / times_retrieved
    helpfulness_score: float = 0.5  # Weighted score based on feedback
    confidence: float = 0.0  # How confident we are in the helpfulness_score

    # Temporal
    first_seen: float = 0.0
    last_seen: float = 0.0
    last_updated: float = 0.0

    def compute_metrics(self):
        """Recompute derived metrics from raw stats."""
        # Usage rate
        if self.times_retrieved > 0:
            self.usage_rate = self.times_used / self.times_retrieved
        else:
            self.usage_rate = 0.0

        # Helpfulness score calculation:
        # - High usage + positive feedback = very helpful
        # - High usage + negative feedback = needs review
        # - Low usage + positive feedback = hidden gem (boost)
        # - Low usage + negative feedback = probably not relevant

        total_used = self.positive_feedback_when_used + self.negative_feedback_when_used
        total_unused = self.positive_feedback_when_unused + self.negative_feedback_when_unused
        total_feedback = total_used + total_unused

        if total_feedback == 0:
            self.helpfulness_score = 0.5  # Neutral
            self.confidence = 0.0
            return

        # Base helpfulness from positive/negative ratio when used
        if total_used > 0:
            used_positivity = self.positive_feedback_when_used / total_used
        else:
            used_positivity = 0.5

        # Penalty/bonus for unused sources
        # If source was unused but response got positive feedback,
        # it might indicate the source wasn't needed
        if total_unused > 0:
            unused_positivity = self.positive_feedback_when_unused / total_unused
        else:
            unused_positivity = 0.5

        # Weight used feedback more heavily (70% used, 30% unused)
        if total_used > 0 and total_unused > 0:
            self.helpfulness_score = 0.7 * used_positivity + 0.3 * (1.0 - unused_positivity)
        elif total_used > 0:
            self.helpfulness_score = used_positivity
        else:
            # Only unused feedback - inverse relationship
            self.helpfulness_score = 1.0 - unused_positivity

        # Adjust by usage rate (sources that are actually used matter more)
        self.helpfulness_score = 0.6 * self.helpfulness_score + 0.4 * self.usage_rate

        # Confidence based on sample size (logarithmic growth)
        self.confidence = min(1.0, math.log(1 + total_feedback) / math.log(20))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectRAGStats:
    """Aggregate RAG statistics for a project."""
    project_id: str
    total_queries: int = 0
    total_sources_retrieved: int = 0
    total_sources_used: int = 0
    avg_sources_per_query: float = 0.0
    avg_usage_rate: float = 0.0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    neutral_feedback_count: int = 0
    overall_satisfaction_rate: float = 0.5
    top_sources: List[Dict] = field(default_factory=list)
    worst_sources: List[Dict] = field(default_factory=list)


# =============================================================================
# SQLite Schema
# =============================================================================

RAG_FEEDBACK_SCHEMA = """
-- RAG feedback entries
CREATE TABLE IF NOT EXISTS rag_feedback (
    feedback_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    used_source_ids_json TEXT NOT NULL,
    unused_source_ids_json TEXT NOT NULL,
    rating INTEGER NOT NULL,
    project_id TEXT,
    response_id TEXT,
    timestamp REAL NOT NULL,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_rag_feedback_project ON rag_feedback(project_id);
CREATE INDEX IF NOT EXISTS idx_rag_feedback_timestamp ON rag_feedback(timestamp);
CREATE INDEX IF NOT EXISTS idx_rag_feedback_query_hash ON rag_feedback(query_hash);
CREATE INDEX IF NOT EXISTS idx_rag_feedback_rating ON rag_feedback(rating);

-- Source quality metrics (per source per project)
CREATE TABLE IF NOT EXISTS source_quality (
    source_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    project_id TEXT,

    -- Usage stats
    times_retrieved INTEGER DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    times_unused INTEGER DEFAULT 0,

    -- Feedback when source was used
    positive_feedback_when_used INTEGER DEFAULT 0,
    negative_feedback_when_used INTEGER DEFAULT 0,

    -- Feedback when source was retrieved but not used
    positive_feedback_when_unused INTEGER DEFAULT 0,
    negative_feedback_when_unused INTEGER DEFAULT 0,

    -- Computed metrics
    usage_rate REAL DEFAULT 0.0,
    helpfulness_score REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.0,

    -- Timestamps
    first_seen REAL,
    last_seen REAL,
    last_updated REAL,

    PRIMARY KEY (source_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_source_quality_project ON source_quality(project_id);
CREATE INDEX IF NOT EXISTS idx_source_quality_helpfulness ON source_quality(helpfulness_score);
CREATE INDEX IF NOT EXISTS idx_source_quality_confidence ON source_quality(confidence);
CREATE INDEX IF NOT EXISTS idx_source_quality_file ON source_quality(file_path);

-- Project-level RAG statistics
CREATE TABLE IF NOT EXISTS project_rag_stats (
    project_id TEXT PRIMARY KEY,
    total_queries INTEGER DEFAULT 0,
    total_sources_retrieved INTEGER DEFAULT 0,
    total_sources_used INTEGER DEFAULT 0,
    avg_sources_per_query REAL DEFAULT 0.0,
    avg_usage_rate REAL DEFAULT 0.0,
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    neutral_feedback_count INTEGER DEFAULT 0,
    overall_satisfaction_rate REAL DEFAULT 0.5,
    last_updated REAL
);

-- Query-source effectiveness tracking
-- Helps identify which queries benefit most from certain sources
CREATE TABLE IF NOT EXISTS query_source_effectiveness (
    query_hash TEXT NOT NULL,
    source_id TEXT NOT NULL,
    project_id TEXT,
    times_paired INTEGER DEFAULT 0,
    times_used_together INTEGER DEFAULT 0,
    positive_outcomes INTEGER DEFAULT 0,
    negative_outcomes INTEGER DEFAULT 0,
    effectiveness_score REAL DEFAULT 0.5,
    last_updated REAL,

    PRIMARY KEY (query_hash, source_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_qse_query ON query_source_effectiveness(query_hash);
CREATE INDEX IF NOT EXISTS idx_qse_source ON query_source_effectiveness(source_id);
CREATE INDEX IF NOT EXISTS idx_qse_effectiveness ON query_source_effectiveness(effectiveness_score);
"""


# =============================================================================
# RAG Feedback Tracker
# =============================================================================

class RAGFeedbackTracker:
    """
    Tracks RAG retrieval quality and provides feedback-adjusted scoring.

    This class implements a feedback loop for improving RAG quality:
    1. Records which sources were retrieved and which were actually used
    2. Links feedback to source usage patterns
    3. Builds quality scores for sources over time
    4. Adjusts relevance scores using historical data
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the RAG feedback tracker."""
        self.db_path = db_path or get_rag_feedback_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(RAG_FEEDBACK_SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    # =========================================================================
    # Record Feedback
    # =========================================================================

    def record_rag_feedback(
        self,
        query: str,
        sources: List[Dict],
        used_source_ids: Optional[List[str]] = None,
        rating: int = 0,
        project_id: Optional[str] = None,
        response_id: Optional[str] = None
    ) -> str:
        """
        Record feedback for a RAG-assisted response.

        Args:
            query: The original query
            sources: List of retrieved sources, each with {id, file_path, score, ...}
            used_source_ids: IDs of sources that were actually used in the response
            rating: User feedback rating (+1 positive, -1 negative, 0 neutral)
            project_id: Optional project identifier
            response_id: Optional link to the response

        Returns:
            The feedback_id of the recorded entry
        """
        timestamp = time.time()
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
        feedback_id = hashlib.sha256(f"{query_hash}:{timestamp}".encode()).hexdigest()[:16]

        # Determine used vs unused sources
        all_source_ids = set(s.get('id', '') for s in sources if s.get('id'))
        used_set = set(used_source_ids or [])
        unused_set = all_source_ids - used_set

        # Create feedback entry
        entry = RAGFeedbackEntry(
            feedback_id=feedback_id,
            query=query,
            query_hash=query_hash,
            sources=sources,
            used_source_ids=list(used_set),
            unused_source_ids=list(unused_set),
            rating=rating,
            project_id=project_id,
            response_id=response_id,
            timestamp=timestamp
        )

        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Insert feedback entry
            cur.execute("""
                INSERT INTO rag_feedback
                (feedback_id, query, query_hash, sources_json, used_source_ids_json,
                 unused_source_ids_json, rating, project_id, response_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.feedback_id,
                entry.query,
                entry.query_hash,
                json.dumps(entry.sources),
                json.dumps(entry.used_source_ids),
                json.dumps(entry.unused_source_ids),
                entry.rating,
                entry.project_id,
                entry.response_id,
                entry.timestamp
            ))

            # Update source quality metrics
            for source in sources:
                source_id = source.get('id', '')
                if not source_id:
                    continue

                file_path = source.get('file_path', '')
                was_used = source_id in used_set

                self._update_source_quality(
                    cur, source_id, file_path, project_id,
                    was_used, rating, timestamp
                )

                # Update query-source effectiveness
                self._update_query_source_effectiveness(
                    cur, query_hash, source_id, project_id,
                    was_used, rating, timestamp
                )

            # Update project stats
            self._update_project_stats(
                cur, project_id, len(sources), len(used_set), rating, timestamp
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return feedback_id

    def _update_source_quality(
        self,
        cur: sqlite3.Cursor,
        source_id: str,
        file_path: str,
        project_id: Optional[str],
        was_used: bool,
        rating: int,
        timestamp: float
    ):
        """Update source quality metrics based on new feedback."""
        # Get existing record
        cur.execute("""
            SELECT times_retrieved, times_used, times_unused,
                   positive_feedback_when_used, negative_feedback_when_used,
                   positive_feedback_when_unused, negative_feedback_when_unused,
                   first_seen
            FROM source_quality
            WHERE source_id = ? AND (project_id = ? OR (project_id IS NULL AND ? IS NULL))
        """, (source_id, project_id, project_id))
        row = cur.fetchone()

        if row:
            times_retrieved = row[0] + 1
            times_used = row[1] + (1 if was_used else 0)
            times_unused = row[2] + (0 if was_used else 1)
            pos_used = row[3]
            neg_used = row[4]
            pos_unused = row[5]
            neg_unused = row[6]
            first_seen = row[7]
        else:
            times_retrieved = 1
            times_used = 1 if was_used else 0
            times_unused = 0 if was_used else 1
            pos_used = 0
            neg_used = 0
            pos_unused = 0
            neg_unused = 0
            first_seen = timestamp

        # Update feedback counts based on usage and rating
        if was_used:
            if rating > 0:
                pos_used += 1
            elif rating < 0:
                neg_used += 1
        else:
            if rating > 0:
                pos_unused += 1
            elif rating < 0:
                neg_unused += 1

        # Create metrics object to compute derived values
        metrics = SourceQualityMetrics(
            source_id=source_id,
            file_path=file_path,
            project_id=project_id,
            times_retrieved=times_retrieved,
            times_used=times_used,
            times_unused=times_unused,
            positive_feedback_when_used=pos_used,
            negative_feedback_when_used=neg_used,
            positive_feedback_when_unused=pos_unused,
            negative_feedback_when_unused=neg_unused,
            first_seen=first_seen,
            last_seen=timestamp
        )
        metrics.compute_metrics()

        # Upsert the record
        cur.execute("""
            INSERT INTO source_quality
            (source_id, file_path, project_id, times_retrieved, times_used, times_unused,
             positive_feedback_when_used, negative_feedback_when_used,
             positive_feedback_when_unused, negative_feedback_when_unused,
             usage_rate, helpfulness_score, confidence, first_seen, last_seen, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, project_id) DO UPDATE SET
                times_retrieved = excluded.times_retrieved,
                times_used = excluded.times_used,
                times_unused = excluded.times_unused,
                positive_feedback_when_used = excluded.positive_feedback_when_used,
                negative_feedback_when_used = excluded.negative_feedback_when_used,
                positive_feedback_when_unused = excluded.positive_feedback_when_unused,
                negative_feedback_when_unused = excluded.negative_feedback_when_unused,
                usage_rate = excluded.usage_rate,
                helpfulness_score = excluded.helpfulness_score,
                confidence = excluded.confidence,
                last_seen = excluded.last_seen,
                last_updated = excluded.last_updated
        """, (
            metrics.source_id, metrics.file_path, metrics.project_id,
            metrics.times_retrieved, metrics.times_used, metrics.times_unused,
            metrics.positive_feedback_when_used, metrics.negative_feedback_when_used,
            metrics.positive_feedback_when_unused, metrics.negative_feedback_when_unused,
            metrics.usage_rate, metrics.helpfulness_score, metrics.confidence,
            metrics.first_seen, metrics.last_seen, timestamp
        ))

    def _update_query_source_effectiveness(
        self,
        cur: sqlite3.Cursor,
        query_hash: str,
        source_id: str,
        project_id: Optional[str],
        was_used: bool,
        rating: int,
        timestamp: float
    ):
        """Update query-source effectiveness pairing."""
        cur.execute("""
            SELECT times_paired, times_used_together, positive_outcomes, negative_outcomes
            FROM query_source_effectiveness
            WHERE query_hash = ? AND source_id = ?
              AND (project_id = ? OR (project_id IS NULL AND ? IS NULL))
        """, (query_hash, source_id, project_id, project_id))
        row = cur.fetchone()

        if row:
            times_paired = row[0] + 1
            times_used = row[1] + (1 if was_used else 0)
            positive = row[2] + (1 if rating > 0 and was_used else 0)
            negative = row[3] + (1 if rating < 0 and was_used else 0)
        else:
            times_paired = 1
            times_used = 1 if was_used else 0
            positive = 1 if rating > 0 and was_used else 0
            negative = 1 if rating < 0 and was_used else 0

        # Compute effectiveness
        total_feedback = positive + negative
        if total_feedback > 0:
            effectiveness = positive / total_feedback
        else:
            effectiveness = 0.5

        cur.execute("""
            INSERT INTO query_source_effectiveness
            (query_hash, source_id, project_id, times_paired, times_used_together,
             positive_outcomes, negative_outcomes, effectiveness_score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(query_hash, source_id, project_id) DO UPDATE SET
                times_paired = excluded.times_paired,
                times_used_together = excluded.times_used_together,
                positive_outcomes = excluded.positive_outcomes,
                negative_outcomes = excluded.negative_outcomes,
                effectiveness_score = excluded.effectiveness_score,
                last_updated = excluded.last_updated
        """, (
            query_hash, source_id, project_id,
            times_paired, times_used, positive, negative,
            effectiveness, timestamp
        ))

    def _update_project_stats(
        self,
        cur: sqlite3.Cursor,
        project_id: Optional[str],
        sources_count: int,
        used_count: int,
        rating: int,
        timestamp: float
    ):
        """Update project-level RAG statistics."""
        if project_id is None:
            return

        cur.execute("""
            SELECT total_queries, total_sources_retrieved, total_sources_used,
                   positive_feedback_count, negative_feedback_count, neutral_feedback_count
            FROM project_rag_stats WHERE project_id = ?
        """, (project_id,))
        row = cur.fetchone()

        if row:
            total_queries = row[0] + 1
            total_retrieved = row[1] + sources_count
            total_used = row[2] + used_count
            positive = row[3] + (1 if rating > 0 else 0)
            negative = row[4] + (1 if rating < 0 else 0)
            neutral = row[5] + (1 if rating == 0 else 0)
        else:
            total_queries = 1
            total_retrieved = sources_count
            total_used = used_count
            positive = 1 if rating > 0 else 0
            negative = 1 if rating < 0 else 0
            neutral = 1 if rating == 0 else 0

        avg_sources = total_retrieved / total_queries if total_queries > 0 else 0
        usage_rate = total_used / total_retrieved if total_retrieved > 0 else 0
        total_feedback = positive + negative
        satisfaction = positive / total_feedback if total_feedback > 0 else 0.5

        cur.execute("""
            INSERT INTO project_rag_stats
            (project_id, total_queries, total_sources_retrieved, total_sources_used,
             avg_sources_per_query, avg_usage_rate,
             positive_feedback_count, negative_feedback_count, neutral_feedback_count,
             overall_satisfaction_rate, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                total_queries = excluded.total_queries,
                total_sources_retrieved = excluded.total_sources_retrieved,
                total_sources_used = excluded.total_sources_used,
                avg_sources_per_query = excluded.avg_sources_per_query,
                avg_usage_rate = excluded.avg_usage_rate,
                positive_feedback_count = excluded.positive_feedback_count,
                negative_feedback_count = excluded.negative_feedback_count,
                neutral_feedback_count = excluded.neutral_feedback_count,
                overall_satisfaction_rate = excluded.overall_satisfaction_rate,
                last_updated = excluded.last_updated
        """, (
            project_id, total_queries, total_retrieved, total_used,
            avg_sources, usage_rate, positive, negative, neutral,
            satisfaction, timestamp
        ))

    # =========================================================================
    # Query Quality Scores
    # =========================================================================

    def get_source_quality_scores(
        self,
        project_id: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[SourceQualityMetrics]:
        """
        Get quality scores for sources in a project.

        Args:
            project_id: Filter by project (None for all)
            min_confidence: Minimum confidence threshold
            limit: Maximum results to return

        Returns:
            List of SourceQualityMetrics sorted by helpfulness_score
        """
        conn = self._get_conn()
        cur = conn.cursor()

        if project_id:
            cur.execute("""
                SELECT source_id, file_path, project_id,
                       times_retrieved, times_used, times_unused,
                       positive_feedback_when_used, negative_feedback_when_used,
                       positive_feedback_when_unused, negative_feedback_when_unused,
                       usage_rate, helpfulness_score, confidence,
                       first_seen, last_seen, last_updated
                FROM source_quality
                WHERE project_id = ? AND confidence >= ?
                ORDER BY helpfulness_score DESC
                LIMIT ?
            """, (project_id, min_confidence, limit))
        else:
            cur.execute("""
                SELECT source_id, file_path, project_id,
                       times_retrieved, times_used, times_unused,
                       positive_feedback_when_used, negative_feedback_when_used,
                       positive_feedback_when_unused, negative_feedback_when_unused,
                       usage_rate, helpfulness_score, confidence,
                       first_seen, last_seen, last_updated
                FROM source_quality
                WHERE confidence >= ?
                ORDER BY helpfulness_score DESC
                LIMIT ?
            """, (min_confidence, limit))

        results = []
        for row in cur.fetchall():
            results.append(SourceQualityMetrics(
                source_id=row[0],
                file_path=row[1],
                project_id=row[2],
                times_retrieved=row[3],
                times_used=row[4],
                times_unused=row[5],
                positive_feedback_when_used=row[6],
                negative_feedback_when_used=row[7],
                positive_feedback_when_unused=row[8],
                negative_feedback_when_unused=row[9],
                usage_rate=row[10],
                helpfulness_score=row[11],
                confidence=row[12],
                first_seen=row[13],
                last_seen=row[14],
                last_updated=row[15]
            ))

        conn.close()
        return results

    def get_source_quality(
        self,
        source_id: str,
        project_id: Optional[str] = None
    ) -> Optional[SourceQualityMetrics]:
        """Get quality metrics for a specific source."""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT source_id, file_path, project_id,
                   times_retrieved, times_used, times_unused,
                   positive_feedback_when_used, negative_feedback_when_used,
                   positive_feedback_when_unused, negative_feedback_when_unused,
                   usage_rate, helpfulness_score, confidence,
                   first_seen, last_seen, last_updated
            FROM source_quality
            WHERE source_id = ? AND (project_id = ? OR (project_id IS NULL AND ? IS NULL))
        """, (source_id, project_id, project_id))

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return SourceQualityMetrics(
            source_id=row[0],
            file_path=row[1],
            project_id=row[2],
            times_retrieved=row[3],
            times_used=row[4],
            times_unused=row[5],
            positive_feedback_when_used=row[6],
            negative_feedback_when_used=row[7],
            positive_feedback_when_unused=row[8],
            negative_feedback_when_unused=row[9],
            usage_rate=row[10],
            helpfulness_score=row[11],
            confidence=row[12],
            first_seen=row[13],
            last_seen=row[14],
            last_updated=row[15]
        )

    # =========================================================================
    # Score Adjustment
    # =========================================================================

    def adjust_relevance_score(
        self,
        source_id: str,
        base_score: float,
        project_id: Optional[str] = None,
        query_hash: Optional[str] = None
    ) -> float:
        """
        Adjust a base relevance score using historical feedback.

        The adjustment is based on:
        1. Source helpfulness score (general quality)
        2. Query-source effectiveness (if query_hash provided)
        3. Confidence weighting (higher confidence = stronger adjustment)

        Args:
            source_id: The source ID
            base_score: The base relevance score (0.0 to 1.0)
            project_id: Optional project context
            query_hash: Optional query hash for query-specific boosting

        Returns:
            Adjusted score (still in 0.0 to 1.0 range)
        """
        conn = self._get_conn()
        cur = conn.cursor()

        # Get source quality
        cur.execute("""
            SELECT helpfulness_score, confidence
            FROM source_quality
            WHERE source_id = ? AND (project_id = ? OR (project_id IS NULL AND ? IS NULL))
        """, (source_id, project_id, project_id))
        source_row = cur.fetchone()

        # Get query-source effectiveness if query hash provided
        query_effectiveness = None
        if query_hash:
            cur.execute("""
                SELECT effectiveness_score, times_paired
                FROM query_source_effectiveness
                WHERE query_hash = ? AND source_id = ?
                  AND (project_id = ? OR (project_id IS NULL AND ? IS NULL))
            """, (query_hash, source_id, project_id, project_id))
            qse_row = cur.fetchone()
            if qse_row and qse_row[1] >= 2:  # Need at least 2 pairings
                query_effectiveness = qse_row[0]

        conn.close()

        # Calculate adjustment
        adjustment = 0.0
        max_adjustment = 0.15  # Maximum 15% adjustment in either direction

        if source_row:
            helpfulness, confidence = source_row

            # Helpfulness adjustment: 0.5 is neutral
            # Below 0.5 = negative adjustment, above 0.5 = positive adjustment
            helpfulness_adj = (helpfulness - 0.5) * 2 * max_adjustment

            # Weight by confidence
            adjustment += helpfulness_adj * confidence

        if query_effectiveness is not None:
            # Query-specific boost (smaller effect, max 5%)
            query_adj = (query_effectiveness - 0.5) * 2 * 0.05
            adjustment += query_adj

        # Apply adjustment and clamp to valid range
        adjusted = base_score + adjustment
        return max(0.0, min(1.0, adjusted))

    def batch_adjust_scores(
        self,
        results: List[Tuple[Any, float]],
        project_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Adjust scores for a batch of search results.

        Args:
            results: List of (result_object, score) tuples
            project_id: Optional project context
            query: Optional query for query-specific boosting

        Returns:
            List of (result_object, adjusted_score) tuples, re-sorted
        """
        query_hash = None
        if query:
            query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]

        adjusted_results = []
        for result, score in results:
            # Try to get source_id from result
            source_id = None
            if hasattr(result, 'id'):
                source_id = result.id
            elif isinstance(result, dict) and 'id' in result:
                source_id = result['id']

            if source_id:
                adjusted_score = self.adjust_relevance_score(
                    source_id, score, project_id, query_hash
                )
            else:
                adjusted_score = score

            adjusted_results.append((result, adjusted_score))

        # Re-sort by adjusted score
        adjusted_results.sort(key=lambda x: -x[1])
        return adjusted_results

    # =========================================================================
    # Statistics and Analysis
    # =========================================================================

    def get_project_stats(self, project_id: str) -> Optional[ProjectRAGStats]:
        """Get RAG statistics for a project."""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT total_queries, total_sources_retrieved, total_sources_used,
                   avg_sources_per_query, avg_usage_rate,
                   positive_feedback_count, negative_feedback_count, neutral_feedback_count,
                   overall_satisfaction_rate
            FROM project_rag_stats WHERE project_id = ?
        """, (project_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return None

        stats = ProjectRAGStats(
            project_id=project_id,
            total_queries=row[0],
            total_sources_retrieved=row[1],
            total_sources_used=row[2],
            avg_sources_per_query=row[3],
            avg_usage_rate=row[4],
            positive_feedback_count=row[5],
            negative_feedback_count=row[6],
            neutral_feedback_count=row[7],
            overall_satisfaction_rate=row[8]
        )

        # Get top sources
        cur.execute("""
            SELECT source_id, file_path, helpfulness_score, times_used, confidence
            FROM source_quality
            WHERE project_id = ? AND confidence >= 0.3
            ORDER BY helpfulness_score DESC
            LIMIT 5
        """, (project_id,))
        stats.top_sources = [
            {"id": r[0], "file_path": r[1], "score": r[2], "times_used": r[3], "confidence": r[4]}
            for r in cur.fetchall()
        ]

        # Get worst sources
        cur.execute("""
            SELECT source_id, file_path, helpfulness_score, times_retrieved, confidence
            FROM source_quality
            WHERE project_id = ? AND confidence >= 0.3
            ORDER BY helpfulness_score ASC
            LIMIT 5
        """, (project_id,))
        stats.worst_sources = [
            {"id": r[0], "file_path": r[1], "score": r[2], "times_retrieved": r[3], "confidence": r[4]}
            for r in cur.fetchall()
        ]

        conn.close()
        return stats

    def get_recent_feedback(
        self,
        project_id: Optional[str] = None,
        limit: int = 20
    ) -> List[RAGFeedbackEntry]:
        """Get recent RAG feedback entries."""
        conn = self._get_conn()
        cur = conn.cursor()

        if project_id:
            cur.execute("""
                SELECT feedback_id, query, query_hash, sources_json,
                       used_source_ids_json, unused_source_ids_json,
                       rating, project_id, response_id, timestamp
                FROM rag_feedback
                WHERE project_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (project_id, limit))
        else:
            cur.execute("""
                SELECT feedback_id, query, query_hash, sources_json,
                       used_source_ids_json, unused_source_ids_json,
                       rating, project_id, response_id, timestamp
                FROM rag_feedback
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        results = []
        for row in cur.fetchall():
            results.append(RAGFeedbackEntry(
                feedback_id=row[0],
                query=row[1],
                query_hash=row[2],
                sources=json.loads(row[3]),
                used_source_ids=json.loads(row[4]),
                unused_source_ids=json.loads(row[5]),
                rating=row[6],
                project_id=row[7],
                response_id=row[8],
                timestamp=row[9]
            ))

        conn.close()
        return results

    def get_low_quality_sources(
        self,
        project_id: Optional[str] = None,
        threshold: float = 0.3,
        min_retrievals: int = 5,
        limit: int = 20
    ) -> List[SourceQualityMetrics]:
        """
        Get sources with low quality scores that might need attention.

        These are sources that are frequently retrieved but have low helpfulness.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        if project_id:
            cur.execute("""
                SELECT source_id, file_path, project_id,
                       times_retrieved, times_used, times_unused,
                       positive_feedback_when_used, negative_feedback_when_used,
                       positive_feedback_when_unused, negative_feedback_when_unused,
                       usage_rate, helpfulness_score, confidence,
                       first_seen, last_seen, last_updated
                FROM source_quality
                WHERE project_id = ?
                  AND helpfulness_score < ?
                  AND times_retrieved >= ?
                  AND confidence >= 0.3
                ORDER BY helpfulness_score ASC
                LIMIT ?
            """, (project_id, threshold, min_retrievals, limit))
        else:
            cur.execute("""
                SELECT source_id, file_path, project_id,
                       times_retrieved, times_used, times_unused,
                       positive_feedback_when_used, negative_feedback_when_used,
                       positive_feedback_when_unused, negative_feedback_when_unused,
                       usage_rate, helpfulness_score, confidence,
                       first_seen, last_seen, last_updated
                FROM source_quality
                WHERE helpfulness_score < ?
                  AND times_retrieved >= ?
                  AND confidence >= 0.3
                ORDER BY helpfulness_score ASC
                LIMIT ?
            """, (threshold, min_retrievals, limit))

        results = []
        for row in cur.fetchall():
            results.append(SourceQualityMetrics(
                source_id=row[0],
                file_path=row[1],
                project_id=row[2],
                times_retrieved=row[3],
                times_used=row[4],
                times_unused=row[5],
                positive_feedback_when_used=row[6],
                negative_feedback_when_used=row[7],
                positive_feedback_when_unused=row[8],
                negative_feedback_when_unused=row[9],
                usage_rate=row[10],
                helpfulness_score=row[11],
                confidence=row[12],
                first_seen=row[13],
                last_seen=row[14],
                last_updated=row[15]
            ))

        conn.close()
        return results

    def get_global_stats(self) -> Dict:
        """Get global RAG feedback statistics."""
        conn = self._get_conn()
        cur = conn.cursor()

        stats = {}

        # Total feedback count
        cur.execute("SELECT COUNT(*) FROM rag_feedback")
        stats['total_feedback_entries'] = cur.fetchone()[0]

        # Feedback by rating
        cur.execute("""
            SELECT rating, COUNT(*) FROM rag_feedback
            GROUP BY rating
        """)
        stats['feedback_by_rating'] = {
            'positive': 0, 'negative': 0, 'neutral': 0
        }
        for row in cur.fetchall():
            if row[0] > 0:
                stats['feedback_by_rating']['positive'] = row[1]
            elif row[0] < 0:
                stats['feedback_by_rating']['negative'] = row[1]
            else:
                stats['feedback_by_rating']['neutral'] = row[1]

        # Total sources tracked
        cur.execute("SELECT COUNT(*) FROM source_quality")
        stats['total_sources_tracked'] = cur.fetchone()[0]

        # Average helpfulness
        cur.execute("SELECT AVG(helpfulness_score) FROM source_quality WHERE confidence >= 0.3")
        row = cur.fetchone()
        stats['avg_helpfulness'] = row[0] if row[0] else 0.5

        # Projects tracked
        cur.execute("SELECT COUNT(*) FROM project_rag_stats")
        stats['projects_tracked'] = cur.fetchone()[0]

        conn.close()
        return stats


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_rag_feedback_tracker: Optional[RAGFeedbackTracker] = None


def get_rag_feedback_tracker() -> RAGFeedbackTracker:
    """Get singleton RAG feedback tracker."""
    global _rag_feedback_tracker
    if _rag_feedback_tracker is None:
        _rag_feedback_tracker = RAGFeedbackTracker()
    return _rag_feedback_tracker


def record_rag_feedback(
    query: str,
    sources: List[Dict],
    used_source_ids: Optional[List[str]] = None,
    rating: int = 0,
    project_id: Optional[str] = None,
    response_id: Optional[str] = None
) -> str:
    """Convenience function to record RAG feedback."""
    return get_rag_feedback_tracker().record_rag_feedback(
        query, sources, used_source_ids, rating, project_id, response_id
    )


def get_source_quality_scores(
    project_id: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 100
) -> List[SourceQualityMetrics]:
    """Convenience function to get source quality scores."""
    return get_rag_feedback_tracker().get_source_quality_scores(
        project_id, min_confidence, limit
    )


def adjust_relevance_score(
    source_id: str,
    base_score: float,
    project_id: Optional[str] = None,
    query: Optional[str] = None
) -> float:
    """Convenience function to adjust a relevance score."""
    query_hash = None
    if query:
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    return get_rag_feedback_tracker().adjust_relevance_score(
        source_id, base_score, project_id, query_hash
    )


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM RAG Feedback Tracker (Phase 2.2.9)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show global statistics")

    # Project stats command
    project_parser = subparsers.add_parser("project", help="Show project statistics")
    project_parser.add_argument("project_id", help="Project ID")

    # Sources command
    sources_parser = subparsers.add_parser("sources", help="List source quality scores")
    sources_parser.add_argument("--project", "-p", help="Filter by project")
    sources_parser.add_argument("--min-confidence", "-c", type=float, default=0.3,
                                 help="Minimum confidence threshold")
    sources_parser.add_argument("--limit", "-l", type=int, default=20,
                                 help="Maximum results")

    # Low quality command
    low_parser = subparsers.add_parser("low-quality", help="Show low quality sources")
    low_parser.add_argument("--project", "-p", help="Filter by project")
    low_parser.add_argument("--threshold", "-t", type=float, default=0.3,
                             help="Helpfulness threshold")

    # Recent command
    recent_parser = subparsers.add_parser("recent", help="Show recent feedback")
    recent_parser.add_argument("--project", "-p", help="Filter by project")
    recent_parser.add_argument("--limit", "-l", type=int, default=10,
                                help="Maximum results")

    # Record command (for testing)
    record_parser = subparsers.add_parser("record", help="Record test feedback")
    record_parser.add_argument("query", help="Query text")
    record_parser.add_argument("--rating", "-r", type=int, default=1,
                                choices=[-1, 0, 1], help="Rating")
    record_parser.add_argument("--project", "-p", help="Project ID")

    args = parser.parse_args()
    tracker = get_rag_feedback_tracker()

    if args.command == "stats":
        stats = tracker.get_global_stats()
        print("RAG Feedback Global Statistics")
        print("=" * 50)
        print(f"Total feedback entries: {stats['total_feedback_entries']}")
        print(f"  Positive: {stats['feedback_by_rating']['positive']}")
        print(f"  Negative: {stats['feedback_by_rating']['negative']}")
        print(f"  Neutral: {stats['feedback_by_rating']['neutral']}")
        print(f"\nTotal sources tracked: {stats['total_sources_tracked']}")
        print(f"Average helpfulness: {stats['avg_helpfulness']:.3f}")
        print(f"Projects tracked: {stats['projects_tracked']}")

    elif args.command == "project":
        stats = tracker.get_project_stats(args.project_id)
        if not stats:
            print(f"No stats found for project: {args.project_id}")
        else:
            print(f"RAG Statistics for Project: {stats.project_id}")
            print("=" * 50)
            print(f"Total queries: {stats.total_queries}")
            print(f"Sources retrieved: {stats.total_sources_retrieved}")
            print(f"Sources used: {stats.total_sources_used}")
            print(f"Avg sources/query: {stats.avg_sources_per_query:.2f}")
            print(f"Usage rate: {stats.avg_usage_rate:.2%}")
            print(f"\nFeedback:")
            print(f"  Positive: {stats.positive_feedback_count}")
            print(f"  Negative: {stats.negative_feedback_count}")
            print(f"  Neutral: {stats.neutral_feedback_count}")
            print(f"Satisfaction rate: {stats.overall_satisfaction_rate:.2%}")

            if stats.top_sources:
                print("\nTop sources:")
                for src in stats.top_sources:
                    print(f"  {src['file_path']}: {src['score']:.3f} (used {src['times_used']}x)")

            if stats.worst_sources:
                print("\nLowest quality sources:")
                for src in stats.worst_sources:
                    print(f"  {src['file_path']}: {src['score']:.3f} (retrieved {src['times_retrieved']}x)")

    elif args.command == "sources":
        sources = tracker.get_source_quality_scores(
            project_id=args.project,
            min_confidence=args.min_confidence,
            limit=args.limit
        )
        print(f"Source Quality Scores (min confidence: {args.min_confidence})")
        if args.project:
            print(f"Project: {args.project}")
        print("=" * 50)
        for src in sources:
            print(f"\n{src.file_path}")
            print(f"  Helpfulness: {src.helpfulness_score:.3f} (confidence: {src.confidence:.3f})")
            print(f"  Retrieved: {src.times_retrieved}, Used: {src.times_used}")
            print(f"  Usage rate: {src.usage_rate:.2%}")

    elif args.command == "low-quality":
        sources = tracker.get_low_quality_sources(
            project_id=args.project,
            threshold=args.threshold
        )
        print(f"Low Quality Sources (below {args.threshold} helpfulness)")
        print("=" * 50)
        if not sources:
            print("No low quality sources found with sufficient data.")
        for src in sources:
            print(f"\n{src.file_path}")
            print(f"  Helpfulness: {src.helpfulness_score:.3f}")
            print(f"  Retrieved: {src.times_retrieved}, Used: {src.times_used}")
            print(f"  Pos/Neg when used: {src.positive_feedback_when_used}/{src.negative_feedback_when_used}")

    elif args.command == "recent":
        entries = tracker.get_recent_feedback(
            project_id=args.project,
            limit=args.limit
        )
        print(f"Recent RAG Feedback")
        if args.project:
            print(f"Project: {args.project}")
        print("=" * 50)
        for entry in entries:
            rating_str = {1: "+1", -1: "-1", 0: "0"}[entry.rating]
            time_str = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M")
            print(f"\n[{rating_str}] {time_str}")
            print(f"  Query: {entry.query[:60]}...")
            print(f"  Sources: {len(entry.sources)} retrieved, {len(entry.used_source_ids)} used")

    elif args.command == "record":
        # Test recording
        feedback_id = tracker.record_rag_feedback(
            query=args.query,
            sources=[
                {"id": "test_src_1", "file_path": "/test/path/file1.py", "score": 0.9},
                {"id": "test_src_2", "file_path": "/test/path/file2.py", "score": 0.7}
            ],
            used_source_ids=["test_src_1"] if args.rating >= 0 else [],
            rating=args.rating,
            project_id=args.project
        )
        print(f"Recorded feedback: {feedback_id}")
        print(f"  Query: {args.query}")
        print(f"  Rating: {args.rating}")
        print(f"  Project: {args.project or 'None'}")

    else:
        parser.print_help()
