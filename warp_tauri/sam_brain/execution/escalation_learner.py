#!/usr/bin/env python3
"""
SAM Escalation Learning System

Goal: Progressively reduce Claude API dependency by learning from escalations.

Every time SAM escalates to Claude:
1. Log the query and Claude's response
2. Categorize the task type
3. Periodically retrain SAM on escalation data
4. Track escalation rate over time (should decrease)

Usage:
    from execution.escalation_learner import EscalationLearner

    learner = EscalationLearner()

    # When escalating
    learner.log_escalation(query, claude_response, task_type)

    # Check if we should handle locally
    if learner.should_escalate(query):
        # escalate to Claude
    else:
        # handle locally

    # Export for retraining
    learner.export_training_data()

    # View stats
    learner.get_stats()
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "db_path": Path.home() / ".sam/escalation_learning.db",
    "training_export_path": Path.home() / ".sam/escalation_training.jsonl",
    "confidence_threshold": 0.7,  # Below this, escalate
    "similarity_threshold": 0.85,  # Above this, consider "seen before"
    "min_examples_to_learn": 5,  # Need this many examples before handling locally
}

# Task categories
TASK_TYPES = [
    "coding",
    "reasoning",
    "creative_writing",
    "roleplay",
    "factual_qa",
    "analysis",
    "planning",
    "debugging",
    "explanation",
    "conversation",
    "unknown"
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("escalation_learner")

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Escalation:
    id: str
    query: str
    query_hash: str
    response: str
    task_type: str
    tokens_used: int
    cost_estimate: float
    created_at: str
    learned: bool = False  # Has SAM been retrained on this?

@dataclass
class TaskPattern:
    """Patterns SAM has learned to handle locally"""
    task_type: str
    example_count: int
    success_rate: float
    avg_confidence: float
    can_handle_locally: bool

# ============================================================================
# DATABASE
# ============================================================================

class EscalationDB:
    def __init__(self, db_path: Path = CONFIG["db_path"]):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Escalation log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                response TEXT NOT NULL,
                task_type TEXT,
                tokens_used INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0,
                created_at TEXT,
                learned INTEGER DEFAULT 0
            )
        """)

        # Local handling attempts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS local_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                task_type TEXT,
                confidence REAL,
                success INTEGER,  -- 1 if user accepted, 0 if escalated after
                created_at TEXT
            )
        """)

        # Daily stats
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_queries INTEGER DEFAULT 0,
                local_handled INTEGER DEFAULT 0,
                escalated INTEGER DEFAULT 0,
                escalation_cost REAL DEFAULT 0
            )
        """)

        # Task patterns learned
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_patterns (
                task_type TEXT PRIMARY KEY,
                example_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                total_confidence REAL DEFAULT 0,
                can_handle_locally INTEGER DEFAULT 0
            )
        """)

        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_escalations_hash ON escalations(query_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_escalations_type ON escalations(task_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_local_hash ON local_attempts(query_hash)")

        conn.commit()
        conn.close()

    def add_escalation(self, escalation: Escalation) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR REPLACE INTO escalations
                (id, query, query_hash, response, task_type, tokens_used, cost_estimate, created_at, learned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                escalation.id, escalation.query, escalation.query_hash,
                escalation.response, escalation.task_type, escalation.tokens_used,
                escalation.cost_estimate, escalation.created_at, 0
            ))

            # Update daily stats
            today = datetime.now().strftime("%Y-%m-%d")
            cur.execute("""
                INSERT INTO daily_stats (date, total_queries, escalated, escalation_cost)
                VALUES (?, 1, 1, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_queries = total_queries + 1,
                    escalated = escalated + 1,
                    escalation_cost = escalation_cost + ?
            """, (today, escalation.cost_estimate, escalation.cost_estimate))

            # Update task pattern
            cur.execute("""
                INSERT INTO task_patterns (task_type, example_count)
                VALUES (?, 1)
                ON CONFLICT(task_type) DO UPDATE SET
                    example_count = example_count + 1
            """, (escalation.task_type,))

            conn.commit()
            return True
        finally:
            conn.close()

    def add_local_attempt(self, query: str, task_type: str, confidence: float, success: bool):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()

        cur.execute("""
            INSERT INTO local_attempts (query, query_hash, task_type, confidence, success, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query, query_hash, task_type, confidence, 1 if success else 0, datetime.now().isoformat()))

        # Update daily stats
        today = datetime.now().strftime("%Y-%m-%d")
        cur.execute("""
            INSERT INTO daily_stats (date, total_queries, local_handled)
            VALUES (?, 1, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_queries = total_queries + 1,
                local_handled = local_handled + ?
        """, (today, 1 if success else 0, 1 if success else 0))

        # Update task pattern success
        if success:
            cur.execute("""
                INSERT INTO task_patterns (task_type, success_count, total_confidence)
                VALUES (?, 1, ?)
                ON CONFLICT(task_type) DO UPDATE SET
                    success_count = success_count + 1,
                    total_confidence = total_confidence + ?
            """, (task_type, confidence, confidence))

        conn.commit()
        conn.close()

    def find_similar_escalations(self, query_hash: str, limit: int = 5) -> List[Dict]:
        """Find previous escalations with similar queries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Exact hash match
        cur.execute("""
            SELECT * FROM escalations WHERE query_hash = ? ORDER BY created_at DESC LIMIT ?
        """, (query_hash, limit))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_task_pattern(self, task_type: str) -> Optional[TaskPattern]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM task_patterns WHERE task_type = ?", (task_type,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        example_count = row["example_count"] or 0
        success_count = row["success_count"] or 0
        total_confidence = row["total_confidence"] or 0

        success_rate = success_count / max(example_count, 1)
        avg_confidence = total_confidence / max(success_count, 1)
        can_handle = (
            example_count >= CONFIG["min_examples_to_learn"] and
            success_rate >= 0.7
        )

        return TaskPattern(
            task_type=task_type,
            example_count=example_count,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
            can_handle_locally=can_handle
        )

    def get_unlearned_escalations(self, limit: int = 1000) -> List[Dict]:
        """Get escalations that haven't been used for training yet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM escalations WHERE learned = 0 ORDER BY created_at LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_as_learned(self, escalation_ids: List[str]):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for eid in escalation_ids:
            cur.execute("UPDATE escalations SET learned = 1 WHERE id = ?", (eid,))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        # Total escalations
        cur.execute("SELECT COUNT(*) FROM escalations")
        stats["total_escalations"] = cur.fetchone()[0]

        # Total local attempts
        cur.execute("SELECT COUNT(*) FROM local_attempts")
        stats["total_local_attempts"] = cur.fetchone()[0]

        # Successful local
        cur.execute("SELECT COUNT(*) FROM local_attempts WHERE success = 1")
        stats["successful_local"] = cur.fetchone()[0]

        # Total cost
        cur.execute("SELECT SUM(cost_estimate) FROM escalations")
        stats["total_cost"] = cur.fetchone()[0] or 0

        # Escalation rate over time (last 30 days)
        cur.execute("""
            SELECT date, total_queries, local_handled, escalated, escalation_cost
            FROM daily_stats
            ORDER BY date DESC
            LIMIT 30
        """)
        stats["daily_history"] = [dict(zip(["date", "total", "local", "escalated", "cost"], row))
                                   for row in cur.fetchall()]

        # By task type
        cur.execute("""
            SELECT task_type, COUNT(*) as count FROM escalations GROUP BY task_type ORDER BY count DESC
        """)
        stats["by_task_type"] = dict(cur.fetchall())

        # Calculate escalation rate
        total = stats["total_escalations"] + stats["total_local_attempts"]
        if total > 0:
            stats["escalation_rate"] = stats["total_escalations"] / total
            stats["local_rate"] = stats["total_local_attempts"] / total
        else:
            stats["escalation_rate"] = 1.0
            stats["local_rate"] = 0.0

        conn.close()
        return stats


# ============================================================================
# ESCALATION LEARNER
# ============================================================================

class EscalationLearner:
    def __init__(self):
        self.db = EscalationDB()

    def classify_task(self, query: str) -> str:
        """Classify the task type of a query."""
        query_lower = query.lower()

        # Simple keyword-based classification
        if any(w in query_lower for w in ["code", "function", "bug", "error", "implement", "fix"]):
            return "coding"
        elif any(w in query_lower for w in ["debug", "traceback", "exception"]):
            return "debugging"
        elif any(w in query_lower for w in ["explain", "what is", "how does", "why"]):
            return "explanation"
        elif any(w in query_lower for w in ["write a story", "creative", "fiction", "poem"]):
            return "creative_writing"
        elif any(w in query_lower for w in ["roleplay", "pretend", "act as", "you are"]):
            return "roleplay"
        elif any(w in query_lower for w in ["analyze", "review", "evaluate"]):
            return "analysis"
        elif any(w in query_lower for w in ["plan", "steps", "how to", "strategy"]):
            return "planning"
        elif any(w in query_lower for w in ["think", "reason", "logic", "solve"]):
            return "reasoning"
        elif "?" in query and len(query) < 200:
            return "factual_qa"
        else:
            return "conversation"

    def should_escalate(self, query: str, local_confidence: float = 0.5) -> Tuple[bool, str]:
        """
        Determine if a query should be escalated to Claude.

        Returns: (should_escalate, reason)
        """
        task_type = self.classify_task(query)
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()

        # Check if we've seen this exact query before
        similar = self.db.find_similar_escalations(query_hash)
        if similar:
            # We have Claude's answer for this exact query
            return False, f"exact_match_found:{similar[0]['id']}"

        # Check if we've learned this task type
        pattern = self.db.get_task_pattern(task_type)
        if pattern and pattern.can_handle_locally:
            if local_confidence >= CONFIG["confidence_threshold"]:
                return False, f"learned_pattern:{task_type}"

        # Check confidence
        if local_confidence >= CONFIG["confidence_threshold"]:
            return False, "high_confidence"

        # Default: escalate
        return True, f"low_confidence:{local_confidence:.2f}"

    def log_escalation(
        self,
        query: str,
        response: str,
        task_type: str = None,
        tokens_used: int = 0,
        model: str = "claude-sonnet"
    ):
        """Log an escalation to Claude for future learning."""

        if task_type is None:
            task_type = self.classify_task(query)

        # Estimate cost (rough)
        cost_per_1k = {"claude-opus": 0.015, "claude-sonnet": 0.003, "claude-haiku": 0.00025}
        cost = (tokens_used / 1000) * cost_per_1k.get(model, 0.003)

        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        escalation_id = hashlib.md5(f"{query_hash}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        escalation = Escalation(
            id=escalation_id,
            query=query,
            query_hash=query_hash,
            response=response,
            task_type=task_type,
            tokens_used=tokens_used,
            cost_estimate=cost,
            created_at=datetime.now().isoformat()
        )

        self.db.add_escalation(escalation)
        logger.info(f"Logged escalation: {task_type} ({tokens_used} tokens, ${cost:.4f})")

        return escalation_id

    def log_local_success(self, query: str, confidence: float, success: bool = True):
        """Log a successful local handling."""
        task_type = self.classify_task(query)
        self.db.add_local_attempt(query, task_type, confidence, success)

    def export_training_data(self, output_path: Path = None) -> int:
        """Export unlearned escalations as training data for fine-tuning."""
        output_path = output_path or CONFIG["training_export_path"]

        escalations = self.db.get_unlearned_escalations()
        if not escalations:
            logger.info("No new escalations to export")
            return 0

        count = 0
        with open(output_path, "a") as f:
            for esc in escalations:
                # Format as instruction-following training example
                example = {
                    "instruction": esc["query"],
                    "input": "",
                    "output": esc["response"],
                    "task_type": esc["task_type"],
                    "source": "claude_escalation"
                }
                f.write(json.dumps(example) + "\n")
                count += 1

        # Mark as learned
        self.db.mark_as_learned([e["id"] for e in escalations])

        logger.info(f"Exported {count} escalations to {output_path}")
        return count

    def get_stats(self) -> Dict:
        """Get escalation learning statistics."""
        return self.db.get_stats()

    def print_stats(self):
        """Print formatted statistics."""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("  ESCALATION LEARNING STATISTICS")
        print("=" * 60)

        total = stats["total_escalations"] + stats["total_local_attempts"]
        print(f"\nTotal Queries: {total}")
        print(f"  Local Handled: {stats['total_local_attempts']} ({stats['local_rate']*100:.1f}%)")
        print(f"  Escalated: {stats['total_escalations']} ({stats['escalation_rate']*100:.1f}%)")
        print(f"  Total API Cost: ${stats['total_cost']:.2f}")

        if stats.get("by_task_type"):
            print("\nEscalations by Task Type:")
            for task_type, count in stats["by_task_type"].items():
                print(f"  {task_type}: {count}")

        if stats.get("daily_history"):
            print("\nRecent Daily Stats:")
            for day in stats["daily_history"][:7]:
                total_day = day["local"] + day["escalated"]
                if total_day > 0:
                    local_pct = day["local"] / total_day * 100
                    print(f"  {day['date']}: {day['local']}/{total_day} local ({local_pct:.0f}%), ${day['cost']:.2f}")


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Escalation Learning System")
    parser.add_argument("command", choices=["stats", "export", "test"])
    parser.add_argument("--query", type=str, help="Test query for should_escalate")
    args = parser.parse_args()

    learner = EscalationLearner()

    if args.command == "stats":
        learner.print_stats()

    elif args.command == "export":
        count = learner.export_training_data()
        print(f"Exported {count} escalations for training")

    elif args.command == "test":
        if args.query:
            should_esc, reason = learner.should_escalate(args.query)
            task_type = learner.classify_task(args.query)
            print(f"Query: {args.query[:50]}...")
            print(f"Task Type: {task_type}")
            print(f"Should Escalate: {should_esc}")
            print(f"Reason: {reason}")


if __name__ == "__main__":
    main()
