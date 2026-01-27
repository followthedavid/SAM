#!/usr/bin/env python3
"""
SAM Training Data Schema and Storage - Phase 5.1.2

Unified training data schema for all SAM training sources:
- Claude conversation captures
- User corrections (DPO pairs)
- Synthetic examples
- Distilled knowledge

This provides a single format for all training data that can be exported
to various training frameworks (MLX, HuggingFace, etc.)

Usage:
    from training_data import (
        TrainingExample, TrainingFormat, TrainingDataStore,
        get_training_store
    )

    # Create a training example
    example = TrainingExample(
        source="claude_capture",
        format=TrainingFormat.INSTRUCTION,
        input_text="How do I reverse a list in Python?",
        output_text="Use list[::-1] or list.reverse()...",
        system_prompt="You are SAM, a helpful coding assistant."
    )

    # Store it
    store = get_training_store()
    example_id = store.add_example(example)

    # Export for training
    store.export_to_jsonl("/path/to/output.jsonl", format=TrainingFormat.INSTRUCTION)
"""

import json
import sqlite3
import hashlib
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, asdict, field
from enum import Enum


# Storage paths - External drive is primary
EXTERNAL_DB_PATH = Path("/Volumes/David External/sam_training/training_data.db")
LOCAL_DB_PATH = Path.home() / ".sam" / "training_data.db"
EXPORT_PATH = Path("/Volumes/David External/sam_training/exports")


def get_db_path() -> Path:
    """Get the appropriate database path, preferring external drive."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_DB_PATH
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOCAL_DB_PATH


class TrainingFormat(Enum):
    """Training data formats supported by different training frameworks."""

    # Standard instruction format: {"input": ..., "output": ...}
    INSTRUCTION = "instruction"

    # Chat format: {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}
    CHAT = "chat"

    # DPO (Direct Preference Optimization): {"prompt": ..., "chosen": ..., "rejected": ...}
    DPO = "dpo"

    # Completion format: just the text to complete
    COMPLETION = "completion"

    # Multi-turn conversation with context
    MULTI_TURN = "multi_turn"


class DataSource(Enum):
    """Sources of training data."""

    CLAUDE_CAPTURE = "claude_capture"       # Escalated conversations
    USER_CORRECTION = "user_correction"     # User corrections (DPO)
    USER_PREFERENCE = "user_preference"     # User preferences (DPO)
    SYNTHETIC = "synthetic"                 # Generated examples
    DISTILLATION = "distillation"           # Knowledge distillation
    MANUAL = "manual"                       # Manually curated
    FEEDBACK = "feedback"                   # From feedback system
    GIT_HISTORY = "git_history"             # From git commits
    DOCUMENTATION = "documentation"         # From docs


class QualityTier(Enum):
    """Quality tiers for training data."""

    GOLD = "gold"           # Manually verified, highest quality
    SILVER = "silver"       # High confidence automated capture
    BRONZE = "bronze"       # Standard automated capture
    UNVERIFIED = "unverified"  # Not yet evaluated


@dataclass
class TrainingExample:
    """
    A single training example with all metadata needed for fine-tuning.

    This is the core data structure for all training data in SAM.
    It can be exported to various formats (JSONL, HuggingFace datasets, etc.)
    """

    # === Required Fields ===
    source: str                    # DataSource value: claude_capture, user_correction, etc.
    format: Union[TrainingFormat, str]   # TrainingFormat value or string
    input_text: str                # User query/prompt
    output_text: str               # Expected response

    # === Identity ===
    id: Optional[str] = None       # Unique ID (generated if not provided)

    # === Optional Fields ===
    system_prompt: Optional[str] = None     # System prompt for chat format
    context: Optional[str] = None           # Additional context

    # === DPO Fields (when format=DPO) ===
    rejected_output: Optional[str] = None   # The "bad" response for DPO
    preference_reason: Optional[str] = None # Why chosen > rejected

    # === Multi-turn Fields ===
    conversation_history: Optional[List[Dict[str, str]]] = None  # Prior turns

    # === Metadata ===
    metadata: Dict[str, Any] = field(default_factory=dict)
    domain: str = "general"                 # code, reasoning, creative, etc.
    complexity: int = 5                     # 1-10 scale
    quality_tier: str = "bronze"            # gold, silver, bronze, unverified
    quality_score: float = 0.5              # 0.0-1.0

    # === Provenance ===
    created_at: float = field(default_factory=time.time)
    source_id: Optional[str] = None         # ID of source (feedback_id, etc.)
    parent_id: Optional[str] = None         # ID of parent example (for variants)

    # === Processing Status ===
    validated: bool = False                 # Has been quality-validated
    used_in_training: bool = False          # Has been used for training
    training_run_id: Optional[str] = None   # Which training run used this

    def __post_init__(self):
        """Generate ID if not provided and normalize format."""
        if self.id is None:
            self.id = self._generate_id()
        if isinstance(self.format, TrainingFormat):
            self.format = self.format.value

    def _generate_id(self) -> str:
        """Generate unique ID from content hash."""
        content = f"{self.source}:{self.input_text}:{self.output_text}:{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingExample':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_training_format(self, target_format: Optional[TrainingFormat] = None) -> Dict[str, Any]:
        """
        Convert to a specific training format.

        Args:
            target_format: Format to convert to. Uses self.format if not specified.

        Returns:
            Dictionary in the target format.
        """
        format_str = target_format.value if target_format else self.format

        if format_str == TrainingFormat.INSTRUCTION.value:
            return {
                "instruction": self.system_prompt or "You are SAM, a helpful AI assistant.",
                "input": self.input_text,
                "output": self.output_text,
            }

        elif format_str == TrainingFormat.CHAT.value:
            messages = []

            # Add system message if present
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})

            # Add conversation history if present
            if self.conversation_history:
                messages.extend(self.conversation_history)

            # Add current turn
            messages.append({"role": "user", "content": self.input_text})
            messages.append({"role": "assistant", "content": self.output_text})

            return {"messages": messages}

        elif format_str == TrainingFormat.DPO.value:
            return {
                "prompt": self.input_text,
                "chosen": self.output_text,
                "rejected": self.rejected_output or "",
                "reason": self.preference_reason,
            }

        elif format_str == TrainingFormat.COMPLETION.value:
            return {
                "text": f"{self.input_text}\n\n{self.output_text}"
            }

        elif format_str == TrainingFormat.MULTI_TURN.value:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            if self.conversation_history:
                messages.extend(self.conversation_history)
            messages.append({"role": "user", "content": self.input_text})
            messages.append({"role": "assistant", "content": self.output_text})
            return {"messages": messages, "context": self.context}

        else:
            # Default to instruction format
            return {
                "input": self.input_text,
                "output": self.output_text,
            }

    def validate(self) -> List[str]:
        """
        Validate the training example.

        Returns:
            List of validation issues (empty if valid).
        """
        issues = []

        # Required fields
        if not self.input_text or not self.input_text.strip():
            issues.append("input_text is empty")
        if not self.output_text or not self.output_text.strip():
            issues.append("output_text is empty")

        # Length checks
        if len(self.input_text) > 32000:
            issues.append("input_text exceeds 32K characters")
        if len(self.output_text) > 32000:
            issues.append("output_text exceeds 32K characters")

        # DPO format checks
        if self.format == TrainingFormat.DPO.value:
            if not self.rejected_output:
                issues.append("DPO format requires rejected_output")

        # Quality checks
        if self._has_repetition(self.output_text):
            issues.append("output_text contains excessive repetition")

        if self._looks_incomplete(self.output_text):
            issues.append("output_text appears incomplete")

        return issues

    def _has_repetition(self, text: str, threshold: float = 0.3) -> bool:
        """Check for repetitive content."""
        if len(text) < 100:
            return False

        # Check for repeated phrases
        words = text.split()
        if len(words) < 10:
            return False

        # Count unique n-grams
        ngrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        unique_ratio = len(set(ngrams)) / len(ngrams) if ngrams else 1.0

        return unique_ratio < (1 - threshold)

    def _looks_incomplete(self, text: str) -> bool:
        """Check if text appears incomplete."""
        incomplete_patterns = [
            r'\.\.\.$',           # Ends with ...
            r'…$',                # Ends with ellipsis
            r'etc\.$',            # Ends with etc.
            r'and so on\.$',      # Ends with "and so on"
            r'^\s*$',             # Empty/whitespace only
        ]

        text_stripped = text.strip()
        for pattern in incomplete_patterns:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                return True

        return False


# === SQLite Schema ===

TRAINING_DATA_SCHEMA = """
-- Primary training examples table
CREATE TABLE IF NOT EXISTS training_examples (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    format TEXT NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,

    -- Optional fields
    system_prompt TEXT,
    context TEXT,
    rejected_output TEXT,
    preference_reason TEXT,
    conversation_history TEXT,  -- JSON

    -- Metadata
    metadata TEXT,  -- JSON
    domain TEXT DEFAULT 'general',
    complexity INTEGER DEFAULT 5,
    quality_tier TEXT DEFAULT 'bronze',
    quality_score REAL DEFAULT 0.5,

    -- Provenance
    created_at REAL NOT NULL,
    source_id TEXT,
    parent_id TEXT,

    -- Processing
    validated INTEGER DEFAULT 0,
    used_in_training INTEGER DEFAULT 0,
    training_run_id TEXT,

    -- Dedup
    content_hash TEXT,
    input_hash TEXT,

    -- Timestamps
    updated_at REAL
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_examples_source ON training_examples(source);
CREATE INDEX IF NOT EXISTS idx_examples_format ON training_examples(format);
CREATE INDEX IF NOT EXISTS idx_examples_domain ON training_examples(domain);
CREATE INDEX IF NOT EXISTS idx_examples_quality ON training_examples(quality_tier, quality_score);
CREATE INDEX IF NOT EXISTS idx_examples_validated ON training_examples(validated);
CREATE INDEX IF NOT EXISTS idx_examples_used ON training_examples(used_in_training);
CREATE INDEX IF NOT EXISTS idx_examples_created ON training_examples(created_at);
CREATE INDEX IF NOT EXISTS idx_examples_content_hash ON training_examples(content_hash);
CREATE INDEX IF NOT EXISTS idx_examples_input_hash ON training_examples(input_hash);

-- Export tracking
CREATE TABLE IF NOT EXISTS export_history (
    export_id TEXT PRIMARY KEY,
    export_path TEXT NOT NULL,
    export_format TEXT NOT NULL,
    example_count INTEGER NOT NULL,
    filters_applied TEXT,  -- JSON
    created_at REAL NOT NULL
);

-- Training run tracking
CREATE TABLE IF NOT EXISTS training_runs (
    run_id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    completed_at REAL,
    examples_used INTEGER,
    status TEXT DEFAULT 'pending',
    config TEXT,  -- JSON
    metrics TEXT,  -- JSON
    model_path TEXT
);

-- Quality validation log
CREATE TABLE IF NOT EXISTS validation_log (
    validation_id TEXT PRIMARY KEY,
    example_id TEXT NOT NULL,
    validated_at REAL NOT NULL,
    validator TEXT,  -- 'auto' or user identifier
    issues TEXT,  -- JSON list
    quality_score REAL,
    quality_tier TEXT,
    approved INTEGER
);

-- Statistics cache
CREATE TABLE IF NOT EXISTS stats_cache (
    stat_key TEXT PRIMARY KEY,
    stat_value TEXT,  -- JSON
    computed_at REAL
);
"""


class TrainingDataStore:
    """
    SQLite-backed storage for training examples.

    Provides:
    - Adding/retrieving examples
    - Deduplication
    - Quality filtering
    - Export to various formats
    - Training run tracking
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the training data store.

        Args:
            db_path: Path to SQLite database. Uses external drive if available.
        """
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(TRAINING_DATA_SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _compute_content_hash(self, example: TrainingExample) -> str:
        """Compute hash of example content for deduplication."""
        content = f"{example.input_text}:{example.output_text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _compute_input_hash(self, input_text: str) -> str:
        """Compute hash of input for duplicate detection."""
        # Normalize input
        normalized = ' '.join(input_text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    # === Core CRUD Operations ===

    def add_example(
        self,
        example: TrainingExample,
        skip_duplicate: bool = True,
        validate: bool = True
    ) -> Optional[str]:
        """
        Add a training example to the store.

        Args:
            example: TrainingExample to add
            skip_duplicate: If True, skip if duplicate exists
            validate: If True, validate before adding

        Returns:
            Example ID if added, None if skipped as duplicate
        """
        # Validate
        if validate:
            issues = example.validate()
            if issues:
                # Log but don't fail for minor issues
                if any('empty' in i for i in issues):
                    return None

        # Compute hashes
        content_hash = self._compute_content_hash(example)
        input_hash = self._compute_input_hash(example.input_text)

        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Check for duplicates
            if skip_duplicate:
                cur.execute(
                    "SELECT id FROM training_examples WHERE content_hash = ?",
                    (content_hash,)
                )
                if cur.fetchone():
                    conn.close()
                    return None

            # Insert
            cur.execute("""
                INSERT INTO training_examples (
                    id, source, format, input_text, output_text,
                    system_prompt, context, rejected_output, preference_reason,
                    conversation_history, metadata, domain, complexity,
                    quality_tier, quality_score, created_at, source_id, parent_id,
                    validated, used_in_training, training_run_id,
                    content_hash, input_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example.id,
                example.source,
                example.format if isinstance(example.format, str) else example.format.value,
                example.input_text,
                example.output_text,
                example.system_prompt,
                example.context,
                example.rejected_output,
                example.preference_reason,
                json.dumps(example.conversation_history) if example.conversation_history else None,
                json.dumps(example.metadata) if example.metadata else None,
                example.domain,
                example.complexity,
                example.quality_tier,
                example.quality_score,
                example.created_at,
                example.source_id,
                example.parent_id,
                1 if example.validated else 0,
                1 if example.used_in_training else 0,
                example.training_run_id,
                content_hash,
                input_hash,
                time.time()
            ))

            conn.commit()
            return example.id

        finally:
            conn.close()

    def get_example(self, example_id: str) -> Optional[TrainingExample]:
        """Get a single example by ID."""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM training_examples WHERE id = ?", (example_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            return self._row_to_example(row)
        return None

    def _row_to_example(self, row: sqlite3.Row) -> TrainingExample:
        """Convert database row to TrainingExample."""
        return TrainingExample(
            id=row['id'],
            source=row['source'],
            format=row['format'],
            input_text=row['input_text'],
            output_text=row['output_text'],
            system_prompt=row['system_prompt'],
            context=row['context'],
            rejected_output=row['rejected_output'],
            preference_reason=row['preference_reason'],
            conversation_history=json.loads(row['conversation_history']) if row['conversation_history'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            domain=row['domain'],
            complexity=row['complexity'],
            quality_tier=row['quality_tier'],
            quality_score=row['quality_score'],
            created_at=row['created_at'],
            source_id=row['source_id'],
            parent_id=row['parent_id'],
            validated=bool(row['validated']),
            used_in_training=bool(row['used_in_training']),
            training_run_id=row['training_run_id'],
        )

    # === Query Methods ===

    def get_examples_for_training(
        self,
        formats: Optional[List[TrainingFormat]] = None,
        domains: Optional[List[str]] = None,
        min_quality: float = 0.3,
        quality_tiers: Optional[List[str]] = None,
        exclude_used: bool = False,
        limit: Optional[int] = None,
    ) -> List[TrainingExample]:
        """
        Get examples suitable for training.

        Args:
            formats: Filter by training formats
            domains: Filter by domains
            min_quality: Minimum quality score
            quality_tiers: Filter by quality tiers
            exclude_used: If True, exclude already-used examples
            limit: Maximum number to return

        Returns:
            List of TrainingExample objects
        """
        conn = self._get_conn()
        cur = conn.cursor()

        query = "SELECT * FROM training_examples WHERE quality_score >= ?"
        params: List[Any] = [min_quality]

        if formats:
            placeholders = ','.join('?' * len(formats))
            query += f" AND format IN ({placeholders})"
            params.extend(f.value if isinstance(f, TrainingFormat) else f for f in formats)

        if domains:
            placeholders = ','.join('?' * len(domains))
            query += f" AND domain IN ({placeholders})"
            params.extend(domains)

        if quality_tiers:
            placeholders = ','.join('?' * len(quality_tiers))
            query += f" AND quality_tier IN ({placeholders})"
            params.extend(quality_tiers)

        if exclude_used:
            query += " AND used_in_training = 0"

        query += " ORDER BY quality_score DESC, created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [self._row_to_example(row) for row in rows]

    def get_examples_by_source(
        self,
        source: Union[DataSource, str],
        limit: int = 100
    ) -> List[TrainingExample]:
        """Get examples from a specific source."""
        source_str = source.value if isinstance(source, DataSource) else source

        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM training_examples WHERE source = ? ORDER BY created_at DESC LIMIT ?",
            (source_str, limit)
        )
        rows = cur.fetchall()
        conn.close()

        return [self._row_to_example(row) for row in rows]

    # === Export Methods ===

    def export_to_jsonl(
        self,
        output_path: Union[str, Path],
        format: Optional[TrainingFormat] = None,
        filters: Optional[Dict[str, Any]] = None,
        mark_as_used: bool = False,
        training_run_id: Optional[str] = None,
    ) -> int:
        """
        Export examples to JSONL format for training.

        Args:
            output_path: Path to output file
            format: Target training format (uses example's format if None)
            filters: Query filters (domains, min_quality, etc.)
            mark_as_used: If True, mark exported examples as used
            training_run_id: Training run ID to associate with

        Returns:
            Number of examples exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get examples
        filters = filters or {}
        examples = self.get_examples_for_training(
            formats=filters.get('formats'),
            domains=filters.get('domains'),
            min_quality=filters.get('min_quality', 0.3),
            quality_tiers=filters.get('quality_tiers'),
            exclude_used=filters.get('exclude_used', False),
            limit=filters.get('limit'),
        )

        # Write to JSONL
        count = 0
        with open(output_path, 'w') as f:
            for example in examples:
                try:
                    formatted = example.to_training_format(format)
                    f.write(json.dumps(formatted) + '\n')
                    count += 1

                    # Mark as used
                    if mark_as_used:
                        self._mark_example_used(example.id, training_run_id)

                except Exception as e:
                    print(f"Error exporting example {example.id}: {e}")
                    continue

        # Record export
        export_id = hashlib.sha256(f"{output_path}:{time.time()}".encode()).hexdigest()[:16]
        self._record_export(export_id, str(output_path), format, count, filters)

        return count

    def _mark_example_used(self, example_id: str, training_run_id: Optional[str] = None):
        """Mark an example as used in training."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE training_examples SET used_in_training = 1, training_run_id = ?, updated_at = ? WHERE id = ?",
            (training_run_id, time.time(), example_id)
        )
        conn.commit()
        conn.close()

    def _record_export(
        self,
        export_id: str,
        path: str,
        format: Optional[TrainingFormat],
        count: int,
        filters: Optional[Dict]
    ):
        """Record an export in the history."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO export_history (export_id, export_path, export_format, example_count, filters_applied, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            export_id,
            path,
            format.value if format else 'mixed',
            count,
            json.dumps(filters) if filters else None,
            time.time()
        ))
        conn.commit()
        conn.close()

    # === Deduplication ===

    def deduplicate(
        self,
        strategy: str = 'content',
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Deduplicate training examples.

        Args:
            strategy: 'content' (exact match), 'input' (same input), 'semantic' (similar)
            dry_run: If True, report but don't delete

        Returns:
            Statistics about duplicates found/removed
        """
        conn = self._get_conn()
        cur = conn.cursor()

        stats = {
            'strategy': strategy,
            'dry_run': dry_run,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'groups': [],
        }

        if strategy == 'content':
            # Find exact content duplicates
            cur.execute("""
                SELECT content_hash, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
                FROM training_examples
                GROUP BY content_hash
                HAVING cnt > 1
            """)

            for row in cur.fetchall():
                ids = row['ids'].split(',')
                stats['duplicates_found'] += len(ids) - 1
                stats['groups'].append({
                    'hash': row['content_hash'],
                    'count': row['cnt'],
                    'ids': ids,
                })

                # Keep first (oldest), remove rest
                if not dry_run:
                    to_remove = ids[1:]
                    for example_id in to_remove:
                        cur.execute("DELETE FROM training_examples WHERE id = ?", (example_id,))
                        stats['duplicates_removed'] += 1

        elif strategy == 'input':
            # Find same-input duplicates
            cur.execute("""
                SELECT input_hash, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
                FROM training_examples
                GROUP BY input_hash
                HAVING cnt > 1
            """)

            for row in cur.fetchall():
                ids = row['ids'].split(',')
                stats['duplicates_found'] += len(ids) - 1
                stats['groups'].append({
                    'hash': row['input_hash'],
                    'count': row['cnt'],
                    'ids': ids,
                })

                # Keep highest quality, remove rest
                if not dry_run:
                    # Get quality scores
                    cur.execute(f"""
                        SELECT id, quality_score FROM training_examples
                        WHERE id IN ({','.join('?' * len(ids))})
                        ORDER BY quality_score DESC
                    """, ids)
                    sorted_ids = [r['id'] for r in cur.fetchall()]

                    to_remove = sorted_ids[1:]
                    for example_id in to_remove:
                        cur.execute("DELETE FROM training_examples WHERE id = ?", (example_id,))
                        stats['duplicates_removed'] += 1

        if not dry_run:
            conn.commit()

        conn.close()
        return stats

    # === Quality Validation ===

    def validate_example(
        self,
        example_id: str,
        validator: str = 'auto',
        approve: bool = True,
        quality_tier: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> bool:
        """
        Validate a training example.

        Args:
            example_id: ID of example to validate
            validator: 'auto' or user identifier
            approve: Whether to approve the example
            quality_tier: Override quality tier
            quality_score: Override quality score

        Returns:
            True if updated successfully
        """
        example = self.get_example(example_id)
        if not example:
            return False

        issues = example.validate()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Update example
        updates = ["validated = 1", "updated_at = ?"]
        params: List[Any] = [time.time()]

        if quality_tier:
            updates.append("quality_tier = ?")
            params.append(quality_tier)

        if quality_score is not None:
            updates.append("quality_score = ?")
            params.append(quality_score)

        params.append(example_id)

        cur.execute(f"UPDATE training_examples SET {', '.join(updates)} WHERE id = ?", params)

        # Log validation
        validation_id = hashlib.sha256(f"{example_id}:{time.time()}".encode()).hexdigest()[:16]
        cur.execute("""
            INSERT INTO validation_log (validation_id, example_id, validated_at, validator, issues, quality_score, quality_tier, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            validation_id,
            example_id,
            time.time(),
            validator,
            json.dumps(issues),
            quality_score or example.quality_score,
            quality_tier or example.quality_tier,
            1 if approve else 0,
        ))

        conn.commit()
        conn.close()
        return True

    def auto_validate_all(
        self,
        min_quality_threshold: float = 0.3
    ) -> Dict[str, int]:
        """
        Auto-validate all unvalidated examples.

        Returns:
            Statistics on validation results
        """
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM training_examples WHERE validated = 0")
        rows = cur.fetchall()
        conn.close()

        stats = {'validated': 0, 'approved': 0, 'rejected': 0}

        for row in rows:
            example = self._row_to_example(row)
            issues = example.validate()

            # Compute quality score
            quality_score = self._compute_auto_quality_score(example, issues)
            quality_tier = self._compute_quality_tier(quality_score)

            approved = quality_score >= min_quality_threshold and not any('empty' in i for i in issues)

            self.validate_example(
                example.id,
                validator='auto',
                approve=approved,
                quality_tier=quality_tier,
                quality_score=quality_score,
            )

            stats['validated'] += 1
            if approved:
                stats['approved'] += 1
            else:
                stats['rejected'] += 1

        return stats

    def _compute_auto_quality_score(self, example: TrainingExample, issues: List[str]) -> float:
        """Compute automatic quality score based on heuristics."""
        score = 0.5

        # Penalize for issues
        score -= len(issues) * 0.1

        # Bonus for longer, more detailed content
        if len(example.output_text) > 200:
            score += 0.1
        if len(example.output_text) > 500:
            score += 0.05

        # Bonus for certain sources
        high_quality_sources = ['manual', 'claude_capture']
        if example.source in high_quality_sources:
            score += 0.15

        # Bonus for DPO (requires more curation)
        if example.format == TrainingFormat.DPO.value:
            score += 0.1

        # Bonus for code domain with code blocks
        if example.domain == 'code' and '```' in example.output_text:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _compute_quality_tier(self, score: float) -> str:
        """Determine quality tier from score."""
        if score >= 0.8:
            return QualityTier.GOLD.value
        elif score >= 0.6:
            return QualityTier.SILVER.value
        elif score >= 0.4:
            return QualityTier.BRONZE.value
        else:
            return QualityTier.UNVERIFIED.value

    # === Statistics ===

    def get_stats(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the training data.

        Args:
            use_cache: If True, use cached stats if available

        Returns:
            Dictionary with statistics
        """
        if use_cache:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT stat_value, computed_at FROM stats_cache WHERE stat_key = 'main'")
            row = cur.fetchone()
            conn.close()

            if row and time.time() - row['computed_at'] < 3600:  # 1 hour cache
                return json.loads(row['stat_value'])

        # Compute fresh stats
        conn = self._get_conn()
        cur = conn.cursor()

        stats = {}

        # Total counts
        cur.execute("SELECT COUNT(*) FROM training_examples")
        stats['total_examples'] = cur.fetchone()[0]

        # By source
        cur.execute("SELECT source, COUNT(*) FROM training_examples GROUP BY source")
        stats['by_source'] = dict(cur.fetchall())

        # By format
        cur.execute("SELECT format, COUNT(*) FROM training_examples GROUP BY format")
        stats['by_format'] = dict(cur.fetchall())

        # By domain
        cur.execute("SELECT domain, COUNT(*) FROM training_examples GROUP BY domain")
        stats['by_domain'] = dict(cur.fetchall())

        # By quality tier
        cur.execute("SELECT quality_tier, COUNT(*) FROM training_examples GROUP BY quality_tier")
        stats['by_quality_tier'] = dict(cur.fetchall())

        # Quality score distribution
        cur.execute("SELECT AVG(quality_score), MIN(quality_score), MAX(quality_score) FROM training_examples")
        row = cur.fetchone()
        stats['quality_score'] = {
            'avg': row[0],
            'min': row[1],
            'max': row[2],
        }

        # Validation status
        cur.execute("SELECT COUNT(*) FROM training_examples WHERE validated = 1")
        validated = cur.fetchone()[0]
        stats['validation'] = {
            'validated': validated,
            'unvalidated': stats['total_examples'] - validated,
        }

        # Usage status
        cur.execute("SELECT COUNT(*) FROM training_examples WHERE used_in_training = 1")
        used = cur.fetchone()[0]
        stats['usage'] = {
            'used': used,
            'unused': stats['total_examples'] - used,
        }

        # Recent additions
        day_ago = time.time() - 86400
        cur.execute("SELECT COUNT(*) FROM training_examples WHERE created_at > ?", (day_ago,))
        stats['recent_24h'] = cur.fetchone()[0]

        # Storage info
        stats['storage'] = {
            'db_path': str(self.db_path),
            'db_size_mb': round(self.db_path.stat().st_size / (1024*1024), 2) if self.db_path.exists() else 0,
        }

        conn.close()

        # Cache stats
        self._cache_stats(stats)

        return stats

    def _cache_stats(self, stats: Dict):
        """Cache stats for future use."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO stats_cache (stat_key, stat_value, computed_at)
            VALUES ('main', ?, ?)
        """, (json.dumps(stats), time.time()))
        conn.commit()
        conn.close()


# === Global Instance ===

_training_store: Optional[TrainingDataStore] = None


def get_training_store() -> TrainingDataStore:
    """Get or create the global training data store."""
    global _training_store
    if _training_store is None:
        _training_store = TrainingDataStore()
    return _training_store


# === Utility Functions ===

def convert_feedback_to_training_example(
    feedback_entry: Dict[str, Any],
    format: TrainingFormat = TrainingFormat.INSTRUCTION
) -> Optional[TrainingExample]:
    """
    Convert a FeedbackDB entry to a TrainingExample.

    Args:
        feedback_entry: Dictionary from FeedbackDB
        format: Target training format

    Returns:
        TrainingExample or None if conversion fails
    """
    feedback_type = feedback_entry.get('feedback_type')

    if feedback_type == 'correction':
        # Use DPO format for corrections
        return TrainingExample(
            source=DataSource.USER_CORRECTION.value,
            format=TrainingFormat.DPO.value,
            input_text=feedback_entry.get('original_query', ''),
            output_text=feedback_entry.get('correction', ''),
            rejected_output=feedback_entry.get('original_response', ''),
            preference_reason=feedback_entry.get('what_was_wrong'),
            domain=feedback_entry.get('domain', 'general'),
            quality_score=feedback_entry.get('quality_weight', 0.5),
            source_id=feedback_entry.get('feedback_id'),
            metadata={
                'correction_type': feedback_entry.get('correction_type'),
                'feedback_type': feedback_type,
            }
        )

    elif feedback_type == 'preference':
        return TrainingExample(
            source=DataSource.USER_PREFERENCE.value,
            format=TrainingFormat.DPO.value,
            input_text=feedback_entry.get('original_query', ''),
            output_text=feedback_entry.get('preferred_response', ''),
            rejected_output=feedback_entry.get('original_response', ''),
            preference_reason=feedback_entry.get('comparison_basis'),
            domain=feedback_entry.get('domain', 'general'),
            quality_score=feedback_entry.get('quality_weight', 0.5),
            source_id=feedback_entry.get('feedback_id'),
            metadata={
                'feedback_type': feedback_type,
            }
        )

    elif feedback_type == 'rating' and feedback_entry.get('rating') == 1:
        # Positive rating - use as instruction example
        return TrainingExample(
            source=DataSource.FEEDBACK.value,
            format=TrainingFormat.INSTRUCTION.value,
            input_text=feedback_entry.get('original_query', ''),
            output_text=feedback_entry.get('original_response', ''),
            domain=feedback_entry.get('domain', 'general'),
            quality_score=feedback_entry.get('quality_weight', 0.5) * 0.8,  # Slightly lower weight
            source_id=feedback_entry.get('feedback_id'),
            metadata={
                'feedback_type': feedback_type,
                'rating': feedback_entry.get('rating'),
            }
        )

    return None


def convert_distillation_to_training_example(
    interaction: Dict[str, Any],
    format: TrainingFormat = TrainingFormat.CHAT
) -> Optional[TrainingExample]:
    """
    Convert a knowledge distillation interaction to TrainingExample.

    Args:
        interaction: Dictionary from DistillationDB
        format: Target training format

    Returns:
        TrainingExample or None if conversion fails
    """
    return TrainingExample(
        source=DataSource.DISTILLATION.value,
        format=format.value,
        input_text=interaction.get('query', ''),
        output_text=interaction.get('response', ''),
        system_prompt="You are SAM, a helpful and knowledgeable AI assistant. You provide clear, accurate, and well-reasoned responses.",
        domain=interaction.get('domain', 'general'),
        complexity=interaction.get('complexity', 5),
        quality_score=interaction.get('quality', 0.7),
        source_id=interaction.get('id'),
        metadata={
            'reasoning_type': interaction.get('reasoning_type'),
            'has_corrections': interaction.get('has_corrections', False),
        }
    )


# === CLI ===

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Data Store")
    parser.add_argument('command', choices=['stats', 'export', 'dedupe', 'validate'],
                       help="Command to run")
    parser.add_argument('--output', '-o', help="Output path for export")
    parser.add_argument('--format', '-f', choices=['instruction', 'chat', 'dpo', 'completion'],
                       help="Export format")
    parser.add_argument('--domain', '-d', help="Filter by domain")
    parser.add_argument('--min-quality', type=float, default=0.3, help="Minimum quality score")
    parser.add_argument('--dry-run', action='store_true', help="Dry run for dedupe")

    args = parser.parse_args()

    store = get_training_store()

    if args.command == 'stats':
        stats = store.get_stats(use_cache=False)
        print(json.dumps(stats, indent=2))

    elif args.command == 'export':
        if not args.output:
            print("Error: --output required for export")
            return

        format_map = {
            'instruction': TrainingFormat.INSTRUCTION,
            'chat': TrainingFormat.CHAT,
            'dpo': TrainingFormat.DPO,
            'completion': TrainingFormat.COMPLETION,
        }

        filters = {'min_quality': args.min_quality}
        if args.domain:
            filters['domains'] = [args.domain]

        count = store.export_to_jsonl(
            args.output,
            format=format_map.get(args.format) if args.format else None,
            filters=filters,
        )
        print(f"Exported {count} examples to {args.output}")

    elif args.command == 'dedupe':
        result = store.deduplicate(strategy='content', dry_run=args.dry_run)
        print(f"Duplicates found: {result['duplicates_found']}")
        if not args.dry_run:
            print(f"Duplicates removed: {result['duplicates_removed']}")
        else:
            print("(dry run - no changes made)")

    elif args.command == 'validate':
        result = store.auto_validate_all(min_quality_threshold=args.min_quality)
        print(f"Validated: {result['validated']}")
        print(f"Approved: {result['approved']}")
        print(f"Rejected: {result['rejected']}")


if __name__ == "__main__":
    main()
