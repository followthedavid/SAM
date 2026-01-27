#!/usr/bin/env python3
"""
SAM Terminal Learning System - Credit-Free Foundation

Architecture:
  This system enables SAM to learn from Claude Code WITHOUT using API credits.
  Uses the terminal coordination system for inter-process communication.

How it works:
  1. PARALLEL WORKERS: Multiple processes generate learning questions
  2. LOCAL INFERENCE: SAM attempts answers with MLX (no cost)
  3. TERMINAL BRIDGE: Learning requests sent via coordination DB
  4. CLAUDE CODE PICKUP: Claude Code terminal monitors and responds
  5. CAPTURE: Responses captured as training data

Processes:
  - Question Generator (from ChatGPT data, curriculum, synthetic)
  - Local Attempt (MLX inference)
  - Verification Queue (waits for Claude Code)
  - Training Capture (JSONL export)

Usage:
    # Start the foundation (runs all workers in parallel)
    python3 terminal_learning.py start

    # Run individual components
    python3 terminal_learning.py generator    # Generate questions
    python3 terminal_learning.py attempt      # SAM attempts locally
    python3 terminal_learning.py queue        # Queue for Claude review
    python3 terminal_learning.py capture      # Capture training data

    # Status
    python3 terminal_learning.py status
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))
from terminal_coordination import TerminalCoordinator, CoordinationMessage

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)

CHATGPT_TRAINING = Path("/Volumes/David External/chatgpt_training")
TRAINING_OUTPUT = SAM_BRAIN / "training_data"
TRAINING_OUTPUT.mkdir(exist_ok=True)

DB_PATH = LEARNING_DIR / "terminal_learning.db"
LOG_PATH = LEARNING_DIR / "terminal_learning.log"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("terminal_learning")


class LearningDB:
    """Database for credit-free learning pipeline."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Questions from all sources
        c.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                source TEXT,           -- 'chatgpt', 'curriculum', 'synthetic', 'claude_session'
                category TEXT,         -- 'coding', 'roleplay', 'planning', 'coaching'
                question TEXT NOT NULL,
                reference_answer TEXT, -- From ChatGPT data (optional)
                created_at TEXT,
                processed INTEGER DEFAULT 0
            )
        """)

        # SAM's local attempts
        c.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                question_id TEXT NOT NULL,
                sam_answer TEXT,
                confidence REAL,
                model_used TEXT,       -- 'qwen2.5-1.5b', 'qwen2.5-3b'
                inference_time_ms INTEGER,
                attempted_at TEXT,
                needs_verification INTEGER DEFAULT 1,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)

        # Verification queue (for Claude Code to pick up)
        c.execute("""
            CREATE TABLE IF NOT EXISTS verification_queue (
                id TEXT PRIMARY KEY,
                attempt_id TEXT NOT NULL,
                question TEXT NOT NULL,
                sam_answer TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                queued_at TEXT,
                picked_up INTEGER DEFAULT 0,
                picked_up_by TEXT,
                picked_up_at TEXT,
                claude_response TEXT,
                responded_at TEXT,
                FOREIGN KEY (attempt_id) REFERENCES attempts(id)
            )
        """)

        # Captured training data
        c.execute("""
            CREATE TABLE IF NOT EXISTS training_capture (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                sam_attempt TEXT,
                reference_answer TEXT,  -- ChatGPT original or Claude response
                quality_score REAL,     -- 0-1 how good the pair is
                exported INTEGER DEFAULT 0,
                exported_to TEXT,
                created_at TEXT
            )
        """)

        # Learning statistics
        c.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                date TEXT PRIMARY KEY,
                questions_generated INTEGER DEFAULT 0,
                attempts_made INTEGER DEFAULT 0,
                verifications_requested INTEGER DEFAULT 0,
                verifications_completed INTEGER DEFAULT 0,
                training_pairs_captured INTEGER DEFAULT 0,
                api_calls_saved INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def add_question(self, question: str, source: str, category: str,
                     reference_answer: str = None) -> Optional[str]:
        """Add a question to the pool."""
        q_id = hashlib.md5(question.encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR IGNORE INTO questions
                (id, source, category, question, reference_answer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (q_id, source, category, question, reference_answer,
                  datetime.now().isoformat()))
            conn.commit()
            return q_id if c.rowcount > 0 else None
        finally:
            conn.close()

    def get_unprocessed_question(self) -> Optional[Dict]:
        """Get next question to process."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM questions
            WHERE processed = 0
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def mark_question_processed(self, q_id: str):
        """Mark question as processed."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE questions SET processed = 1 WHERE id = ?", (q_id,))
        conn.commit()
        conn.close()

    def add_attempt(self, question_id: str, sam_answer: str,
                    confidence: float, model: str, inference_ms: int) -> str:
        """Record SAM's local attempt."""
        a_id = hashlib.md5(f"{question_id}{time.time()}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO attempts
            (id, question_id, sam_answer, confidence, model_used,
             inference_time_ms, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (a_id, question_id, sam_answer, confidence, model,
              inference_ms, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return a_id

    def queue_for_verification(self, attempt_id: str, question: str,
                               sam_answer: str, priority: int = 2) -> str:
        """Add to verification queue for Claude Code."""
        v_id = hashlib.md5(f"{attempt_id}{time.time()}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO verification_queue
            (id, attempt_id, question, sam_answer, priority, queued_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (v_id, attempt_id, question, sam_answer, priority,
              datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return v_id

    def get_pending_verifications(self, limit: int = 10) -> List[Dict]:
        """Get pending verifications for Claude Code to process."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM verification_queue
            WHERE picked_up = 0
            ORDER BY priority ASC, queued_at ASC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_verification_picked_up(self, v_id: str, by: str):
        """Mark verification as picked up by Claude Code session."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE verification_queue
            SET picked_up = 1, picked_up_by = ?, picked_up_at = ?
            WHERE id = ?
        """, (by, datetime.now().isoformat(), v_id))
        conn.commit()
        conn.close()

    def complete_verification(self, v_id: str, claude_response: str):
        """Record Claude Code's response."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE verification_queue
            SET claude_response = ?, responded_at = ?
            WHERE id = ?
        """, (claude_response, datetime.now().isoformat(), v_id))
        conn.commit()
        conn.close()

    def capture_training(self, question: str, sam_attempt: str,
                        reference: str, quality: float) -> str:
        """Capture a training pair."""
        t_id = hashlib.md5(f"{question}{time.time()}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO training_capture
            (id, question, sam_attempt, reference_answer, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (t_id, question, sam_attempt, reference, quality,
              datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return t_id

    def get_unexported_training(self, limit: int = 100) -> List[Dict]:
        """Get training pairs that haven't been exported."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM training_capture
            WHERE exported = 0 AND quality_score >= 0.5
            ORDER BY quality_score DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_exported(self, ids: List[str], path: str):
        """Mark training pairs as exported."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for t_id in ids:
            c.execute("""
                UPDATE training_capture
                SET exported = 1, exported_to = ?
                WHERE id = ?
            """, (path, t_id))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get comprehensive stats."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        stats = {}

        c.execute("SELECT COUNT(*) FROM questions")
        stats["total_questions"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM questions WHERE processed = 0")
        stats["unprocessed_questions"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM attempts")
        stats["total_attempts"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM verification_queue WHERE picked_up = 0")
        stats["pending_verifications"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM verification_queue WHERE claude_response IS NOT NULL")
        stats["completed_verifications"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM training_capture")
        stats["training_pairs"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM training_capture WHERE exported = 1")
        stats["exported_pairs"] = c.fetchone()[0]

        c.execute("SELECT source, COUNT(*) FROM questions GROUP BY source")
        stats["by_source"] = dict(c.fetchall())

        c.execute("SELECT category, COUNT(*) FROM questions GROUP BY category")
        stats["by_category"] = dict(c.fetchall())

        conn.close()
        return stats


class QuestionGenerator:
    """Generates learning questions from multiple sources."""

    def __init__(self):
        self.db = LearningDB()

    def load_chatgpt_questions(self, limit_per_category: int = 1000) -> int:
        """Load questions from ChatGPT training data."""
        loaded = 0

        for category_file in CHATGPT_TRAINING.glob("chatgpt_*.jsonl"):
            if category_file.stem == "chatgpt_all":
                continue  # Skip the combined file

            category = category_file.stem.replace("chatgpt_", "")
            logger.info(f"Loading {category} from ChatGPT...")

            count = 0
            with open(category_file) as f:
                for line in f:
                    if count >= limit_per_category:
                        break
                    try:
                        data = json.loads(line)
                        messages = data.get("messages", [])
                        if len(messages) >= 2:
                            user_msg = messages[0].get("content", "")
                            assistant_msg = messages[1].get("content", "")

                            # Skip very long or very short
                            if 20 < len(user_msg) < 2000 and 50 < len(assistant_msg) < 5000:
                                if self.db.add_question(
                                    question=user_msg,
                                    source="chatgpt",
                                    category=category,
                                    reference_answer=assistant_msg
                                ):
                                    loaded += 1
                                    count += 1
                    except json.JSONDecodeError:
                        continue

            logger.info(f"  Loaded {count} from {category}")

        return loaded

    def generate_synthetic_questions(self, count: int = 100) -> int:
        """Generate synthetic learning questions."""
        templates = {
            "coding": [
                "How do I implement {concept} in Python?",
                "What's the best way to handle {pattern} in Swift?",
                "Explain the difference between {thing1} and {thing2}.",
                "Write a function that {task}.",
                "Debug this issue: {problem}",
            ],
            "roleplay": [
                "Write a dialogue where {character} confronts {situation}.",
                "Create a scene showing {emotion} in a {setting}.",
                "How would {persona} respond to {event}?",
            ],
            "architecture": [
                "Design a system for {requirement}.",
                "What are the trade-offs between {option1} and {option2}?",
                "How should I structure {project}?",
            ],
        }

        concepts = ["async/await", "decorators", "closures", "observers", "protocols"]
        patterns = ["error handling", "state management", "dependency injection"]

        generated = 0
        for category, temps in templates.items():
            for _ in range(count // len(templates)):
                template = random.choice(temps)
                # Simple placeholder filling
                question = template.format(
                    concept=random.choice(concepts),
                    pattern=random.choice(patterns),
                    thing1="struct", thing2="class",
                    task="validates an email address",
                    problem="function returns None unexpectedly",
                    character="a mentor",
                    situation="a student's failure",
                    emotion="quiet determination",
                    setting="dystopian future",
                    persona="a skeptical scientist",
                    event="unexplained phenomena",
                    requirement="real-time chat with 10K users",
                    option1="monolith", option2="microservices",
                    project="a local-first app"
                )

                if self.db.add_question(question, "synthetic", category):
                    generated += 1

        return generated

    def load_conversation_questions(self, jsonl_path: Path) -> int:
        """Load questions from conversation export."""
        loaded = 0

        if not jsonl_path.exists():
            return 0

        with open(jsonl_path) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    messages = data.get("messages", [])
                    topic = data.get("metadata", {}).get("topic", "coding")

                    for msg in messages:
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if 20 < len(content) < 2000:
                                if self.db.add_question(content, "claude_session", topic):
                                    loaded += 1
                except json.JSONDecodeError:
                    continue

        return loaded


class LocalAttempt:
    """SAM attempts to answer using local MLX inference."""

    def __init__(self):
        self.db = LearningDB()
        self.sam_api_url = "http://localhost:8765/api/chat"

    def attempt_question(self, question: str, question_id: str) -> Optional[str]:
        """Have SAM attempt to answer locally."""
        import requests

        start = time.time()

        try:
            response = requests.post(
                self.sam_api_url,
                json={
                    "message": question,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                sam_answer = data.get("response", "")
                confidence = data.get("confidence", 0.5)
                model = data.get("model", "qwen2.5-1.5b")

                inference_ms = int((time.time() - start) * 1000)

                attempt_id = self.db.add_attempt(
                    question_id=question_id,
                    sam_answer=sam_answer,
                    confidence=confidence,
                    model=model,
                    inference_ms=inference_ms
                )

                return attempt_id
        except Exception as e:
            logger.error(f"Local attempt failed: {e}")

        return None

    def process_batch(self, limit: int = 10) -> int:
        """Process a batch of questions."""
        processed = 0

        for _ in range(limit):
            question = self.db.get_unprocessed_question()
            if not question:
                break

            attempt_id = self.attempt_question(
                question["question"],
                question["id"]
            )

            if attempt_id:
                self.db.mark_question_processed(question["id"])

                # If we have a reference answer from ChatGPT, capture immediately
                if question.get("reference_answer"):
                    self.db.capture_training(
                        question=question["question"],
                        sam_attempt="",  # We don't need SAM's attempt for ChatGPT data
                        reference=question["reference_answer"],
                        quality=0.8  # ChatGPT answers are generally good
                    )
                else:
                    # Queue for Claude Code verification
                    conn = sqlite3.connect(self.db.db_path)
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()
                    c.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,))
                    attempt = dict(c.fetchone())
                    conn.close()

                    self.db.queue_for_verification(
                        attempt_id=attempt_id,
                        question=question["question"],
                        sam_answer=attempt["sam_answer"],
                        priority=2
                    )

                processed += 1
                logger.info(f"Processed: {question['question'][:50]}...")

        return processed


class VerificationBridge:
    """
    Bridge between SAM and Claude Code using terminal coordination.

    This allows SAM to request verification without API calls.
    Claude Code picks up requests and responds via shared DB.
    """

    def __init__(self):
        self.db = LearningDB()
        self.coord = TerminalCoordinator()
        self.session = None

    def register(self, terminal_type: str = "sam-learner"):
        """Register as a terminal."""
        self.session = self.coord.register_terminal(
            terminal_type=terminal_type,
            tags=["learning", "verification"]
        )
        return self.session.id

    def request_verification(self, question: str, sam_answer: str) -> str:
        """Send verification request via terminal coordination."""
        if not self.session:
            self.register()

        msg_id = self.coord.send_message(
            from_session=self.session.id,
            content=f"VERIFY: {question}",
            message_type="request",
            data={
                "question": question,
                "sam_answer": sam_answer,
                "request_type": "learning_verification"
            }
        )

        return msg_id

    def check_responses(self) -> List[Dict]:
        """Check for Claude Code responses."""
        if not self.session:
            return []

        messages = self.coord.get_messages(self.session.id, unacknowledged_only=True)
        responses = []

        for msg in messages:
            if msg.message_type == "response" and msg.data:
                if msg.data.get("response_type") == "learning_verification":
                    responses.append({
                        "message_id": msg.id,
                        "question": msg.data.get("question"),
                        "claude_answer": msg.data.get("claude_answer"),
                        "from_session": msg.from_session
                    })
                    self.coord.acknowledge_message(msg.id)

        return responses


class TrainingCapture:
    """Captures and exports training data."""

    def __init__(self):
        self.db = LearningDB()

    def capture_from_chatgpt(self):
        """
        Capture high-quality training pairs from ChatGPT data.
        These don't need Claude verification - they're already good.
        """
        # Already handled in LocalAttempt when reference_answer exists
        pass

    def capture_from_verification(self, question: str, sam_attempt: str,
                                  claude_response: str) -> str:
        """Capture training pair from Claude verification."""
        # Score quality based on response length and relevance
        quality = min(1.0, len(claude_response) / 500) * 0.8

        return self.db.capture_training(
            question=question,
            sam_attempt=sam_attempt,
            reference=claude_response,
            quality=quality
        )

    def export_to_jsonl(self, output_file: Path = None) -> Tuple[int, Path]:
        """Export captured training data to JSONL."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = TRAINING_OUTPUT / f"terminal_learning_{timestamp}.jsonl"

        pairs = self.db.get_unexported_training(limit=1000)
        exported_ids = []

        with open(output_file, 'w') as f:
            for pair in pairs:
                training_item = {
                    "messages": [
                        {"role": "user", "content": pair["question"]},
                        {"role": "assistant", "content": pair["reference_answer"]}
                    ],
                    "metadata": {
                        "source": "terminal_learning",
                        "quality": pair["quality_score"],
                        "captured_at": pair["created_at"]
                    }
                }
                f.write(json.dumps(training_item) + "\n")
                exported_ids.append(pair["id"])

        if exported_ids:
            self.db.mark_exported(exported_ids, str(output_file))

        return len(exported_ids), output_file


class LearningFoundation:
    """
    The main learning foundation - runs multiple parallel processes.

    Maximizes token efficiency by:
    1. Batching questions
    2. Using local inference for first-pass
    3. Only escalating uncertain answers to Claude
    4. Caching everything for future training
    """

    def __init__(self):
        self.db = LearningDB()
        self.generator = QuestionGenerator()
        self.attempt = LocalAttempt()
        self.bridge = VerificationBridge()
        self.capture = TrainingCapture()

    def initialize(self) -> Dict:
        """Initialize the learning foundation with data from all sources."""
        results = {
            "chatgpt_loaded": 0,
            "synthetic_generated": 0,
            "conversation_loaded": 0,
        }

        # Load ChatGPT training data (the goldmine)
        logger.info("Loading ChatGPT training data...")
        results["chatgpt_loaded"] = self.generator.load_chatgpt_questions(limit_per_category=2000)

        # Generate synthetic questions
        logger.info("Generating synthetic questions...")
        results["synthetic_generated"] = self.generator.generate_synthetic_questions(count=200)

        # Load from conversation exports
        logger.info("Loading conversation exports...")
        for jsonl_file in TRAINING_OUTPUT.glob("conversation_export_*.jsonl"):
            results["conversation_loaded"] += self.generator.load_conversation_questions(jsonl_file)

        logger.info(f"Foundation initialized: {results}")
        return results

    def run_learning_cycle(self, batch_size: int = 20) -> Dict:
        """Run one learning cycle."""
        results = {
            "questions_processed": 0,
            "attempts_made": 0,
            "training_captured": 0,
            "verifications_queued": 0,
        }

        # Process questions locally
        results["questions_processed"] = self.attempt.process_batch(batch_size)

        # Check for Claude Code responses
        responses = self.bridge.check_responses()
        for resp in responses:
            if resp.get("claude_answer"):
                self.capture.capture_from_verification(
                    question=resp["question"],
                    sam_attempt="",  # Not needed for direct captures
                    claude_response=resp["claude_answer"]
                )
                results["training_captured"] += 1

        # Export if we have enough
        unexported = self.db.get_unexported_training(limit=1)
        if len(unexported) >= 50:
            exported, path = self.capture.export_to_jsonl()
            logger.info(f"Exported {exported} training pairs to {path}")

        return results

    def run_parallel(self, workers: int = 4, cycles: int = 100):
        """Run learning with multiple parallel workers."""
        logger.info(f"Starting parallel learning: {workers} workers, {cycles} cycles")

        total_results = {
            "questions_processed": 0,
            "training_captured": 0,
            "elapsed_seconds": 0,
        }

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []

            for i in range(cycles):
                future = executor.submit(self.run_learning_cycle, batch_size=10)
                futures.append(future)

            for future in futures:
                result = future.result()
                total_results["questions_processed"] += result["questions_processed"]
                total_results["training_captured"] += result["training_captured"]

        total_results["elapsed_seconds"] = int(time.time() - start_time)

        logger.info(f"Parallel learning complete: {total_results}")
        return total_results


def status():
    """Print comprehensive status."""
    db = LearningDB()
    stats = db.get_stats()

    print("\n" + "=" * 60)
    print("SAM TERMINAL LEARNING - STATUS")
    print("=" * 60)

    print(f"\n📚 QUESTIONS:")
    print(f"   Total:         {stats['total_questions']:,}")
    print(f"   Unprocessed:   {stats['unprocessed_questions']:,}")

    if stats.get("by_source"):
        print(f"\n   By Source:")
        for source, count in stats["by_source"].items():
            print(f"      {source:15} {count:,}")

    if stats.get("by_category"):
        print(f"\n   By Category:")
        for cat, count in stats["by_category"].items():
            print(f"      {cat:15} {count:,}")

    print(f"\n🧠 ATTEMPTS:")
    print(f"   Total:         {stats['total_attempts']:,}")

    print(f"\n✅ VERIFICATIONS:")
    print(f"   Pending:       {stats['pending_verifications']:,}")
    print(f"   Completed:     {stats['completed_verifications']:,}")

    print(f"\n📝 TRAINING:")
    print(f"   Pairs captured: {stats['training_pairs']:,}")
    print(f"   Exported:       {stats['exported_pairs']:,}")

    # Estimate API savings
    api_saved = stats["training_pairs"] - stats["completed_verifications"]
    print(f"\n💰 API CALLS SAVED: ~{api_saved:,}")
    print(f"   (ChatGPT data used directly without verification)")

    print("\n" + "=" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        foundation = LearningFoundation()
        results = foundation.initialize()
        print(f"\nInitialized: {json.dumps(results, indent=2)}")

    elif cmd == "start":
        # Initialize and run parallel learning
        foundation = LearningFoundation()

        # Check if already initialized
        stats = foundation.db.get_stats()
        if stats["total_questions"] < 100:
            print("Initializing foundation...")
            foundation.initialize()

        print("\nStarting parallel learning...")
        results = foundation.run_parallel(workers=4, cycles=50)
        print(f"\nResults: {json.dumps(results, indent=2)}")

    elif cmd == "cycle":
        # Run one cycle
        foundation = LearningFoundation()
        results = foundation.run_learning_cycle(batch_size=10)
        print(f"Cycle results: {results}")

    elif cmd == "export":
        # Export training data
        capture = TrainingCapture()
        exported, path = capture.export_to_jsonl()
        print(f"Exported {exported} training pairs to {path}")

    elif cmd == "status":
        status()

    elif cmd == "generator":
        # Run just the question generator
        generator = QuestionGenerator()
        loaded = generator.load_chatgpt_questions(limit_per_category=500)
        print(f"Loaded {loaded} questions from ChatGPT data")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: init, start, cycle, export, status, generator")
        sys.exit(1)


if __name__ == "__main__":
    main()
