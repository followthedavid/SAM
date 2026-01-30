"""
Unified Learning Database
=========================
Single SQLite database combining auto_learning.db and curriculum tables.

Tables:
- examples: Training examples extracted from Claude sessions
- training_runs: Records of MLX LoRA training runs
- processed_files: Tracks which session files have been processed
- curriculum: Prioritized learning tasks with confidence scoring
- learning_sessions: Curriculum learning session records
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Paths - we're in learning/ subdirectory
BRAIN_PATH = Path(__file__).parent.parent
DATA_PATH = BRAIN_PATH / "data"

# New unified database
DB_PATH = BRAIN_PATH / "learning.db"


@dataclass
class TrainingExampleRow:
    """A training example as stored in the database."""
    id: str
    user_input: str
    claude_response: str
    category: str
    quality_score: float
    source_file: str
    extracted_at: str
    used_in_training: bool = False


class LearningDatabase:
    """
    Unified SQLite database for all learning subsystems.

    Combines:
    - AutoLearningDB tables (examples, training_runs, processed_files)
    - CurriculumManager tables (curriculum, learning_sessions)
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize all database tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # --- From auto_learner.py: AutoLearningDB ---

        c.execute("""
            CREATE TABLE IF NOT EXISTS examples (
                id TEXT PRIMARY KEY,
                user_input TEXT,
                claude_response TEXT,
                category TEXT,
                quality_score REAL,
                source_file TEXT,
                extracted_at TEXT,
                used_in_training INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                completed_at TEXT,
                examples_used INTEGER,
                initial_loss REAL,
                final_loss REAL,
                adapter_path TEXT,
                status TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                file_path TEXT PRIMARY KEY,
                processed_at TEXT,
                examples_extracted INTEGER
            )
        """)

        # --- From perpetual_learner.py: CurriculumManager ---

        c.execute("""
            CREATE TABLE IF NOT EXISTS curriculum (
                id TEXT PRIMARY KEY,
                task_type TEXT,
                instruction TEXT NOT NULL,
                context TEXT,
                expected_skills TEXT,
                priority INTEGER DEFAULT 3,
                created_at TEXT,
                created_by TEXT,
                attempted INTEGER DEFAULT 0,
                sam_attempt TEXT,
                sam_confidence REAL DEFAULT 0,
                verified_response TEXT,
                learning_captured INTEGER DEFAULT 0,
                completed_at TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                ended_at TEXT,
                tasks_attempted INTEGER DEFAULT 0,
                tasks_learned INTEGER DEFAULT 0,
                training_examples_created INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_curriculum_pending
            ON curriculum(attempted, priority)
        """)

        conn.commit()
        conn.close()

    # =========================================================================
    # Examples table (from AutoLearningDB)
    # =========================================================================

    def add_example(self, example: TrainingExampleRow) -> bool:
        """Add a training example if not duplicate."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO examples
                (id, user_input, claude_response, category, quality_score,
                 source_file, extracted_at, used_in_training)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example.id,
                example.user_input,
                example.claude_response,
                example.category,
                example.quality_score,
                example.source_file,
                example.extracted_at,
                0
            ))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def get_unused_examples(self, limit: int = None) -> List[TrainingExampleRow]:
        """Get examples not yet used in training."""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM examples WHERE used_in_training = 0 ORDER BY quality_score DESC"
        if limit:
            query += f" LIMIT {limit}"

        rows = conn.execute(query).fetchall()
        conn.close()

        return [TrainingExampleRow(
            id=r[0], user_input=r[1], claude_response=r[2],
            category=r[3], quality_score=r[4], source_file=r[5],
            extracted_at=r[6], used_in_training=bool(r[7])
        ) for r in rows]

    def mark_examples_used(self, example_ids: List[str]):
        """Mark examples as used in training."""
        conn = sqlite3.connect(self.db_path)
        conn.executemany(
            "UPDATE examples SET used_in_training = 1 WHERE id = ?",
            [(eid,) for eid in example_ids]
        )
        conn.commit()
        conn.close()

    def get_example_count(self, unused_only: bool = False) -> int:
        """Get count of examples."""
        conn = sqlite3.connect(self.db_path)
        if unused_only:
            count = conn.execute("SELECT COUNT(*) FROM examples WHERE used_in_training = 0").fetchone()[0]
        else:
            count = conn.execute("SELECT COUNT(*) FROM examples").fetchone()[0]
        conn.close()
        return count

    # =========================================================================
    # Processed files table
    # =========================================================================

    def is_file_processed(self, file_path: str) -> bool:
        """Check if a file has been processed."""
        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            "SELECT 1 FROM processed_files WHERE file_path = ?",
            (file_path,)
        ).fetchone()
        conn.close()
        return result is not None

    def mark_file_processed(self, file_path: str, examples_count: int):
        """Mark a file as processed."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO processed_files
            (file_path, processed_at, examples_extracted)
            VALUES (?, ?, ?)
        """, (file_path, datetime.now().isoformat(), examples_count))
        conn.commit()
        conn.close()

    # =========================================================================
    # Training runs table
    # =========================================================================

    def record_training_run(self, examples_used: int, initial_loss: float,
                            final_loss: float, adapter_path: str, status: str):
        """Record a training run."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO training_runs
            (started_at, completed_at, examples_used, initial_loss, final_loss, adapter_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            examples_used,
            initial_loss,
            final_loss,
            str(adapter_path),
            status
        ))
        conn.commit()
        conn.close()

    def get_last_training_time(self) -> Optional[datetime]:
        """Get the time of the last completed training run."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT completed_at FROM training_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

    # =========================================================================
    # Curriculum tables (from CurriculumManager)
    # =========================================================================

    def add_curriculum_task(self, task_id: str, task_type: str, instruction: str,
                           context: Optional[str], expected_skills: List[str],
                           priority: int, created_at: str, created_by: str) -> bool:
        """Add a curriculum task. Returns True if added."""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute("""
                INSERT OR IGNORE INTO curriculum
                (id, task_type, instruction, context, expected_skills, priority,
                 created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, task_type, instruction, context,
                json.dumps(expected_skills), priority,
                created_at, created_by
            ))
            conn.commit()
            return c.rowcount > 0
        finally:
            conn.close()

    def get_next_curriculum_task(self) -> Optional[Dict]:
        """Get the next pending curriculum task, ordered by priority."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM curriculum
            WHERE attempted = 0
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        row = c.fetchone()
        conn.close()
        if row:
            result = dict(row)
            result['expected_skills'] = json.loads(result.get('expected_skills', '[]'))
            return result
        return None

    def get_pending_curriculum_count(self) -> int:
        """Get count of pending curriculum tasks."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 0")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_low_confidence_tasks(self, threshold: float = 0.7, limit: int = 10) -> List[Dict]:
        """Get attempted tasks with confidence below threshold."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM curriculum
            WHERE attempted = 1 AND learning_captured = 0 AND sam_confidence < ?
            ORDER BY sam_confidence ASC
            LIMIT ?
        """, (threshold, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_curriculum_attempted(self, task_id: str, sam_attempt: str, confidence: float):
        """Mark a curriculum task as attempted."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE curriculum
            SET attempted = 1, sam_attempt = ?, sam_confidence = ?
            WHERE id = ?
        """, (sam_attempt, confidence, task_id))
        conn.commit()
        conn.close()

    def mark_curriculum_learned(self, task_id: str, verified_response: str):
        """Mark a curriculum task as learned."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE curriculum
            SET verified_response = ?, learning_captured = 1, completed_at = ?
            WHERE id = ?
        """, (verified_response, datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

    def get_curriculum_stats(self) -> Dict:
        """Get curriculum statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM curriculum")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 0")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM curriculum WHERE learning_captured = 1")
        learned = c.fetchone()[0]

        c.execute("SELECT AVG(sam_confidence) FROM curriculum WHERE attempted = 1")
        avg_confidence = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 1 AND sam_confidence < 0.7")
        needs_correction = c.fetchone()[0]

        c.execute("SELECT task_type, COUNT(*) FROM curriculum GROUP BY task_type")
        by_type = dict(c.fetchall())

        c.execute("SELECT priority, COUNT(*) FROM curriculum WHERE attempted = 0 GROUP BY priority")
        pending_by_priority = dict(c.fetchall())

        conn.close()

        return {
            "total_tasks": total,
            "pending": pending,
            "learned": learned,
            "in_progress": total - pending - learned,
            "avg_confidence": round(avg_confidence, 2),
            "needs_correction": needs_correction,
            "by_type": by_type,
            "pending_by_priority": pending_by_priority,
        }

    # =========================================================================
    # Combined stats
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get combined learning statistics."""
        conn = sqlite3.connect(self.db_path)

        total = conn.execute("SELECT COUNT(*) FROM examples").fetchone()[0]
        unused = conn.execute("SELECT COUNT(*) FROM examples WHERE used_in_training = 0").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM training_runs WHERE status = 'completed'").fetchone()[0]

        last_run = conn.execute(
            "SELECT completed_at FROM training_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()

        conn.close()

        curriculum_stats = self.get_curriculum_stats()

        return {
            "total_examples": total,
            "unused_examples": unused,
            "training_runs": runs,
            "last_training": last_run[0] if last_run else None,
            "ready_for_training": unused >= 100,
            "curriculum": curriculum_stats,
        }
