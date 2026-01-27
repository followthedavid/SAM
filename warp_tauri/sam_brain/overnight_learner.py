#!/usr/bin/env python3
"""
SAM Overnight Learner - Comprehensive learning while you sleep.

Strategy for 24/7 learning WITHOUT burning Claude credits:

1. QUEUE, DON'T ESCALATE
   - SAM tries to answer questions with local MLX
   - Low-confidence answers get queued (not sent to Claude immediately)
   - Queue builds up during the day

2. BATCH ESCALATION (scheduled, credit-efficient)
   - At night (or when idle), send batch to Claude API
   - One API call with multiple questions = maximum learning per credit
   - Capture all reasoning patterns from responses

3. SYNTHETIC TRAINING
   - Generate questions from existing training data
   - SAM attempts answers, scores confidence
   - Only escalate the hardest ones (most learning value)

4. SELF-IMPROVEMENT LOOP
   - After each batch, SAM re-evaluates its performance
   - Identifies weak areas for next batch focus
   - Tracks improvement over time

Usage:
    python3 overnight_learner.py start       # Start daemon
    python3 overnight_learner.py status      # Check queue and progress
    python3 overnight_learner.py batch       # Force a batch escalation now
    python3 overnight_learner.py generate    # Generate synthetic questions
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = LEARNING_DIR / "overnight_learning.db"
LOG_PATH = LEARNING_DIR / "overnight.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("overnight")

# Config
CONFIG = {
    # Batch settings
    "batch_size": 20,               # Questions per batch
    "min_queue_for_batch": 10,      # Minimum questions before batching

    # Schedule (24-hour format)
    "batch_hours": [2, 6, 14, 22],  # When to run batches (2am, 6am, 2pm, 10pm)
    "idle_threshold_minutes": 30,   # Consider idle after this long

    # Quality thresholds
    "min_confidence_to_skip": 0.85,  # Above this, don't queue
    "min_learning_value": 0.3,       # Below this, don't bother escalating

    # Credit management
    "max_daily_escalations": 50,     # Hard limit
    "prefer_api_over_code": True,    # Use API (cheaper) vs Claude Code
}


@dataclass
class QueuedQuestion:
    id: str
    question: str
    sam_attempt: str
    confidence: float
    domain: str  # coding, roleplay, reasoning, etc.
    source: str  # user, synthetic, self-eval
    queued_at: str
    learning_value: float  # estimated value of learning this
    escalated: bool = False
    claude_response: Optional[str] = None


class LearningDB:
    """SQLite storage for learning queue and history."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS question_queue (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                sam_attempt TEXT,
                confidence REAL,
                domain TEXT,
                source TEXT,
                queued_at TEXT,
                learning_value REAL,
                escalated INTEGER DEFAULT 0,
                claude_response TEXT,
                processed_at TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS batch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_time TEXT,
                questions_sent INTEGER,
                questions_answered INTEGER,
                training_examples_generated INTEGER,
                total_tokens_used INTEGER,
                domains TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                questions_queued INTEGER DEFAULT 0,
                questions_escalated INTEGER DEFAULT 0,
                training_examples INTEGER DEFAULT 0,
                improvement_score REAL
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_escalated ON question_queue(escalated)
        """)

        conn.commit()
        conn.close()

    def queue_question(self, q: QueuedQuestion):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO question_queue
            (id, question, sam_attempt, confidence, domain, source, queued_at, learning_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (q.id, q.question, q.sam_attempt, q.confidence, q.domain, q.source, q.queued_at, q.learning_value))
        conn.commit()
        conn.close()

    def get_pending_questions(self, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Prioritize by learning value
        c.execute("""
            SELECT * FROM question_queue
            WHERE escalated = 0
            ORDER BY learning_value DESC, queued_at ASC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_escalated(self, question_id: str, claude_response: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE question_queue
            SET escalated = 1, claude_response = ?, processed_at = ?
            WHERE id = ?
        """, (claude_response, datetime.now().isoformat(), question_id))
        conn.commit()
        conn.close()

    def record_batch(self, questions_sent: int, questions_answered: int, examples: int, tokens: int, domains: List[str]):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO batch_history
            (batch_time, questions_sent, questions_answered, training_examples_generated, total_tokens_used, domains)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), questions_sent, questions_answered, examples, tokens, json.dumps(domains)))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM question_queue WHERE escalated = 0")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM question_queue WHERE escalated = 1")
        processed = c.fetchone()[0]

        c.execute("SELECT SUM(training_examples_generated) FROM batch_history")
        examples = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM batch_history")
        batches = c.fetchone()[0]

        # Today's stats
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM question_queue WHERE escalated = 1 AND processed_at LIKE ?", (f"{today}%",))
        today_escalated = c.fetchone()[0]

        conn.close()

        return {
            "pending": pending,
            "processed": processed,
            "training_examples": examples,
            "batches_run": batches,
            "today_escalated": today_escalated,
            "daily_limit": CONFIG["max_daily_escalations"],
            "can_escalate": today_escalated < CONFIG["max_daily_escalations"],
        }


class SyntheticQuestionGenerator:
    """Generate questions that will teach SAM the most."""

    def __init__(self):
        self.training_data_path = SAM_BRAIN / "training_data"

    def generate_coding_questions(self, count: int = 10) -> List[Dict]:
        """Generate coding questions from existing data."""
        questions = []

        # Focus areas for Mac-native coding
        topics = [
            "SwiftUI state management",
            "Combine framework publishers",
            "Core Data migrations",
            "Metal shader optimization",
            "AppKit NSView lifecycle",
            "Swift concurrency with actors",
            "Xcode build configuration",
            "macOS sandboxing and entitlements",
            "Universal binary compilation",
            "Swift Package Manager dependency resolution",
        ]

        for topic in topics[:count]:
            q = {
                "question": f"Explain how to implement {topic} in a production macOS app. Include code examples and common pitfalls.",
                "domain": "coding",
                "source": "synthetic",
                "learning_value": 0.9,  # High value - Mac-native knowledge
            }
            questions.append(q)

        return questions

    def generate_reasoning_questions(self, count: int = 10) -> List[Dict]:
        """Generate complex reasoning questions."""
        questions = []

        scenarios = [
            "Design a system architecture for a local-first AI assistant that syncs across Apple devices",
            "How would you implement offline-capable semantic search on iOS with limited memory",
            "What's the optimal strategy for fine-tuning a 1.5B parameter model on 8GB RAM",
            "Design a rate-limiting system for a scraper that respects robots.txt and avoids bans",
            "How would you architect a plugin system for a macOS app that's sandboxed",
        ]

        for scenario in scenarios[:count]:
            q = {
                "question": scenario,
                "domain": "reasoning",
                "source": "synthetic",
                "learning_value": 0.85,
            }
            questions.append(q)

        return questions

    def generate_from_weak_areas(self, weak_domains: List[str], count: int = 10) -> List[Dict]:
        """Generate questions targeting SAM's weak areas."""
        questions = []

        domain_questions = {
            "coding": [
                "How do I debug memory leaks in a Swift app using Instruments?",
                "What's the best way to handle deep linking in a SwiftUI app?",
            ],
            "roleplay": [
                "Write a dialogue where a confident character admits vulnerability",
                "How do you maintain consistent character voice across a long scene?",
            ],
            "reasoning": [
                "Walk through your decision process for choosing a database technology",
                "How do you prioritize features when resources are limited?",
            ],
        }

        for domain in weak_domains:
            if domain in domain_questions:
                for q_text in domain_questions[domain][:count // len(weak_domains)]:
                    questions.append({
                        "question": q_text,
                        "domain": domain,
                        "source": "weak_area",
                        "learning_value": 0.95,  # Very high - addressing weakness
                    })

        return questions


class OvernightLearner:
    """Main daemon for overnight learning."""

    def __init__(self):
        self.db = LearningDB()
        self.generator = SyntheticQuestionGenerator()
        self.running = True

    def queue_from_user_interaction(self, question: str, sam_attempt: str, confidence: float, domain: str = "general"):
        """Called when SAM answers a user question with low confidence."""
        if confidence >= CONFIG["min_confidence_to_skip"]:
            return  # Don't queue high-confidence answers

        # Calculate learning value
        learning_value = self._calculate_learning_value(question, confidence, domain)

        if learning_value < CONFIG["min_learning_value"]:
            return  # Not worth learning

        q = QueuedQuestion(
            id=hashlib.md5(question.encode()).hexdigest()[:16],
            question=question,
            sam_attempt=sam_attempt,
            confidence=confidence,
            domain=domain,
            source="user",
            queued_at=datetime.now().isoformat(),
            learning_value=learning_value,
        )

        self.db.queue_question(q)
        logger.info(f"Queued question (confidence={confidence:.2f}, value={learning_value:.2f}): {question[:50]}...")

    def _calculate_learning_value(self, question: str, confidence: float, domain: str) -> float:
        """Estimate how valuable it would be to learn this."""
        value = 1.0 - confidence  # Lower confidence = higher learning value

        # Boost for priority domains
        domain_boosts = {
            "coding": 0.2,  # Top priority
            "reasoning": 0.15,
            "roleplay": 0.1,
        }
        value += domain_boosts.get(domain, 0)

        # Boost for longer/complex questions
        if len(question) > 200:
            value += 0.1

        return min(1.0, value)

    def generate_synthetic_batch(self, count: int = 20):
        """Generate synthetic questions to learn from."""
        logger.info(f"Generating {count} synthetic questions...")

        # Mix of question types
        questions = []
        questions.extend(self.generator.generate_coding_questions(count // 2))
        questions.extend(self.generator.generate_reasoning_questions(count // 4))

        # Get weak areas from distillation stats
        # TODO: Query actual weak areas from training stats
        questions.extend(self.generator.generate_from_weak_areas(["coding"], count // 4))

        for q in questions:
            qq = QueuedQuestion(
                id=hashlib.md5(q["question"].encode()).hexdigest()[:16],
                question=q["question"],
                sam_attempt="",  # Will be filled when SAM tries
                confidence=0.0,
                domain=q["domain"],
                source=q["source"],
                queued_at=datetime.now().isoformat(),
                learning_value=q["learning_value"],
            )
            self.db.queue_question(qq)

        logger.info(f"Queued {len(questions)} synthetic questions")

    def run_batch_escalation(self) -> Dict:
        """Run a batch escalation to Claude."""
        stats = self.db.get_stats()

        if not stats["can_escalate"]:
            logger.warning(f"Daily limit reached ({stats['today_escalated']}/{stats['daily_limit']})")
            return {"success": False, "reason": "daily_limit"}

        pending = self.db.get_pending_questions(CONFIG["batch_size"])
        if len(pending) < CONFIG["min_queue_for_batch"]:
            logger.info(f"Not enough questions ({len(pending)} < {CONFIG['min_queue_for_batch']})")
            return {"success": False, "reason": "insufficient_queue"}

        logger.info(f"=== Running Batch Escalation ({len(pending)} questions) ===")

        # Build batch prompt
        batch_prompt = self._build_batch_prompt(pending)

        # Send to Claude (via API or terminal)
        if CONFIG["prefer_api_over_code"]:
            responses = self._escalate_via_api(batch_prompt, pending)
        else:
            responses = self._escalate_via_terminal(batch_prompt, pending)

        # Process responses and create training examples
        examples_created = self._process_responses(pending, responses)

        # Record batch
        domains = list(set(q["domain"] for q in pending))
        self.db.record_batch(
            questions_sent=len(pending),
            questions_answered=len(responses),
            examples=examples_created,
            tokens=0,  # TODO: Track actual token usage
            domains=domains,
        )

        logger.info(f"Batch complete: {examples_created} training examples created")

        return {
            "success": True,
            "questions": len(pending),
            "examples_created": examples_created,
        }

    def _build_batch_prompt(self, questions: List[Dict]) -> str:
        """Build an efficient batch prompt."""
        prompt = """I'm going to ask you multiple questions. For each one, please:
1. Provide a clear, detailed answer
2. Explain your reasoning process
3. Note any important patterns or principles

Questions:

"""
        for i, q in enumerate(questions, 1):
            prompt += f"Q{i} [{q['domain']}]: {q['question']}\n\n"

        prompt += "\nPlease answer each question thoroughly, numbering your responses to match."
        return prompt

    def _escalate_via_api(self, batch_prompt: str, questions: List[Dict]) -> Dict[str, str]:
        """Send batch to Claude API."""
        # TODO: Implement actual API call
        # For now, this is a placeholder that shows the structure
        logger.info("Would send to Claude API (not implemented yet)")
        logger.info(f"Batch prompt length: {len(batch_prompt)} chars")

        # Placeholder - in production this would call the API
        return {}

    def _escalate_via_terminal(self, batch_prompt: str, questions: List[Dict]) -> Dict[str, str]:
        """Send batch via terminal (Claude Code)."""
        # TODO: Implement terminal escalation
        logger.info("Would escalate via terminal (not implemented yet)")
        return {}

    def _process_responses(self, questions: List[Dict], responses: Dict[str, str]) -> int:
        """Convert responses to training examples."""
        examples_created = 0

        for q in questions:
            if q["id"] in responses:
                response = responses[q["id"]]
                self.db.mark_escalated(q["id"], response)

                # Create training example
                example = {
                    "messages": [
                        {"role": "user", "content": q["question"]},
                        {"role": "assistant", "content": response}
                    ],
                    "domain": q["domain"],
                    "source": "overnight_batch",
                }

                # Save to training data
                output_file = SAM_BRAIN / "training_data" / "overnight_learned.jsonl"
                with open(output_file, "a") as f:
                    f.write(json.dumps(example) + "\n")

                examples_created += 1

        return examples_created

    def should_run_batch(self) -> bool:
        """Check if it's time to run a batch."""
        now = datetime.now()

        # Check if current hour is in batch hours
        if now.hour in CONFIG["batch_hours"]:
            # Check if we already ran this hour
            # TODO: Track last batch time
            return True

        return False

    def run_daemon(self):
        """Main daemon loop."""
        logger.info("=" * 60)
        logger.info("SAM Overnight Learner Starting")
        logger.info("=" * 60)

        while self.running:
            try:
                stats = self.db.get_stats()
                logger.info(f"Queue: {stats['pending']} pending, {stats['today_escalated']}/{stats['daily_limit']} escalated today")

                # Check if we should generate synthetic questions
                if stats["pending"] < CONFIG["min_queue_for_batch"]:
                    self.generate_synthetic_batch(20)

                # Check if it's batch time
                if self.should_run_batch():
                    self.run_batch_escalation()

                # Sleep for 10 minutes
                for _ in range(600):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Daemon error: {e}")
                time.sleep(60)

        logger.info("Overnight learner stopped")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Overnight Learner")
    parser.add_argument("command", choices=["start", "status", "batch", "generate"], default="status", nargs="?")

    args = parser.parse_args()

    learner = OvernightLearner()

    if args.command == "start":
        learner.run_daemon()
    elif args.command == "status":
        stats = learner.db.get_stats()
        print("\n=== SAM Overnight Learner Status ===")
        print(f"  Pending questions: {stats['pending']}")
        print(f"  Processed: {stats['processed']}")
        print(f"  Training examples: {stats['training_examples']}")
        print(f"  Batches run: {stats['batches_run']}")
        print(f"  Today's escalations: {stats['today_escalated']}/{stats['daily_limit']}")
        print(f"  Can escalate: {'Yes' if stats['can_escalate'] else 'No'}")
    elif args.command == "batch":
        result = learner.run_batch_escalation()
        print(f"Batch result: {result}")
    elif args.command == "generate":
        learner.generate_synthetic_batch(20)
        print("Generated 20 synthetic questions")


if __name__ == "__main__":
    main()
