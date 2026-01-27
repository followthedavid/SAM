#!/usr/bin/env python3
"""
SAM Teacher-Student Learning System

Architecture:
  Claude Code (Teacher) → writes curriculum → SAM (Student) → queries Claude API → learns

This enables 24/7 learning where:
1. Claude Code sessions generate learning objectives
2. SAM picks them up and attempts answers with local MLX
3. SAM verifies with Claude API
4. SAM captures the delta as training data

Usage:
    # Teacher (Claude Code) writes tasks:
    python3 teacher_student.py teach "Explain SwiftUI @State vs @Binding"
    python3 teacher_student.py teach-batch curriculum.json

    # Student (SAM) learns:
    python3 teacher_student.py learn              # Process one task
    python3 teacher_student.py study              # Continuous learning daemon

    # Status:
    python3 teacher_student.py status
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = LEARNING_DIR / "teacher_student.db"
LOG_PATH = LEARNING_DIR / "teacher_student.log"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("teacher_student")


class TaskType(Enum):
    CODING = "coding"
    REASONING = "reasoning"
    ROLEPLAY = "roleplay"
    KNOWLEDGE = "knowledge"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"


class TaskPriority(Enum):
    CRITICAL = 1    # Learn immediately
    HIGH = 2        # Learn today
    MEDIUM = 3      # Learn this week
    LOW = 4         # Learn eventually


@dataclass
class LearningTask:
    id: str
    task_type: str
    instruction: str           # What to learn
    context: Optional[str]     # Additional context
    expected_skills: List[str] # What SAM should learn from this
    priority: int
    created_at: str
    created_by: str            # "claude_code", "user", "self"

    # Learning progress
    attempted: bool = False
    sam_attempt: Optional[str] = None
    sam_confidence: float = 0.0
    claude_response: Optional[str] = None
    learning_captured: bool = False
    completed_at: Optional[str] = None


class TeacherStudentDB:
    """Database for curriculum and learning progress."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

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
                claude_response TEXT,
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
                training_examples_created INTEGER DEFAULT 0,
                api_calls_made INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_curriculum_pending
            ON curriculum(attempted, priority)
        """)

        conn.commit()
        conn.close()

    def add_task(self, task: LearningTask) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR IGNORE INTO curriculum
                (id, task_type, instruction, context, expected_skills, priority,
                 created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.task_type, task.instruction, task.context,
                json.dumps(task.expected_skills), task.priority,
                task.created_at, task.created_by
            ))
            conn.commit()
            return c.rowcount > 0
        finally:
            conn.close()

    def get_next_task(self) -> Optional[Dict]:
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
        return dict(row) if row else None

    def get_pending_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 0")
        count = c.fetchone()[0]
        conn.close()
        return count

    def mark_attempted(self, task_id: str, sam_attempt: str, confidence: float):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE curriculum
            SET attempted = 1, sam_attempt = ?, sam_confidence = ?
            WHERE id = ?
        """, (sam_attempt, confidence, task_id))
        conn.commit()
        conn.close()

    def mark_learned(self, task_id: str, claude_response: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE curriculum
            SET claude_response = ?, learning_captured = 1, completed_at = ?
            WHERE id = ?
        """, (claude_response, datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM curriculum")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 0")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM curriculum WHERE learning_captured = 1")
        learned = c.fetchone()[0]

        c.execute("SELECT task_type, COUNT(*) FROM curriculum GROUP BY task_type")
        by_type = dict(c.fetchall())

        conn.close()

        return {
            "total_tasks": total,
            "pending": pending,
            "learned": learned,
            "in_progress": total - pending - learned,
            "by_type": by_type,
        }


class Teacher:
    """Claude Code acts as teacher - writes curriculum for SAM."""

    def __init__(self):
        self.db = TeacherStudentDB()

    def teach(self, instruction: str, task_type: str = "coding",
              context: str = None, skills: List[str] = None,
              priority: int = 2) -> str:
        """Add a learning task to the curriculum."""

        task = LearningTask(
            id=hashlib.md5(instruction.encode()).hexdigest()[:16],
            task_type=task_type,
            instruction=instruction,
            context=context,
            expected_skills=skills or [],
            priority=priority,
            created_at=datetime.now().isoformat(),
            created_by="claude_code",
        )

        if self.db.add_task(task):
            logger.info(f"📚 Added task: {instruction[:60]}...")
            return task.id
        else:
            logger.info(f"Task already exists: {instruction[:40]}...")
            return None

    def teach_batch(self, tasks: List[Dict]) -> int:
        """Add multiple learning tasks."""
        added = 0
        for t in tasks:
            if self.teach(
                instruction=t["instruction"],
                task_type=t.get("type", "coding"),
                context=t.get("context"),
                skills=t.get("skills", []),
                priority=t.get("priority", 2)
            ):
                added += 1
        return added

    def generate_curriculum_from_conversation(self, topics: List[str]) -> int:
        """Generate learning tasks from conversation topics."""
        tasks = []

        for topic in topics:
            # Coding topics
            if any(kw in topic.lower() for kw in ["swift", "macos", "ios", "xcode", "swiftui"]):
                tasks.append({
                    "instruction": f"Explain and demonstrate: {topic}. Include code examples, common patterns, and pitfalls.",
                    "type": "coding",
                    "skills": ["swift", "macos", "native_development"],
                    "priority": 1,  # High priority - Mac native is critical
                })

            # Architecture topics
            elif any(kw in topic.lower() for kw in ["architecture", "design", "system", "pipeline"]):
                tasks.append({
                    "instruction": f"Design a solution for: {topic}. Consider trade-offs, scalability, and implementation steps.",
                    "type": "architecture",
                    "skills": ["system_design", "architecture"],
                    "priority": 2,
                })

            # General knowledge
            else:
                tasks.append({
                    "instruction": f"Explain thoroughly: {topic}",
                    "type": "knowledge",
                    "skills": ["general"],
                    "priority": 3,
                })

        return self.teach_batch(tasks)


class Student:
    """SAM acts as student - attempts tasks and learns from Claude API."""

    def __init__(self):
        self.db = TeacherStudentDB()
        self.training_output = SAM_BRAIN / "training_data" / "teacher_student_learned.jsonl"

    def attempt_with_mlx(self, instruction: str) -> Tuple[str, float]:
        """Have SAM attempt the task with local MLX model."""
        try:
            # Use SAM API if running
            import requests
            response = requests.post(
                "http://localhost:8765/api/chat",
                json={"message": instruction, "mode": "default"},
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "")
                confidence = self._estimate_confidence(answer)
                return answer, confidence

        except Exception as e:
            logger.warning(f"SAM API unavailable: {e}")

        # Fallback: simple attempt marker
        return f"[SAM attempt pending - API not available]", 0.1

    def _estimate_confidence(self, response: str) -> float:
        """Estimate confidence in the response."""
        confidence = 0.5  # Base

        # Longer responses often better
        if len(response) > 500:
            confidence += 0.1
        if len(response) > 1000:
            confidence += 0.1

        # Code blocks indicate practical answer
        if "```" in response:
            confidence += 0.15

        # Hedging language reduces confidence
        hedges = ["i think", "maybe", "possibly", "not sure", "i don't know"]
        for hedge in hedges:
            if hedge in response.lower():
                confidence -= 0.1

        return max(0.1, min(0.95, confidence))

    def verify_with_claude(self, instruction: str, sam_attempt: str) -> Optional[str]:
        """Send to Claude API for verification and better answer."""
        try:
            import anthropic

            # Get API key from environment
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                # Try reading from common locations
                for keyfile in [Path.home() / ".anthropic_key", Path.home() / ".config/anthropic/key"]:
                    if keyfile.exists():
                        api_key = keyfile.read_text().strip()
                        break

            if not api_key:
                logger.error("No ANTHROPIC_API_KEY found")
                return None

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""I'm training a local AI assistant called SAM. SAM attempted to answer this task:

TASK: {instruction}

SAM'S ATTEMPT:
{sam_attempt}

Please provide:
1. A thorough, correct answer to the task
2. What SAM got right
3. What SAM should improve
4. Key patterns or principles to remember

Be detailed and educational - SAM will learn from your response."""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            return None
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def capture_learning(self, task: Dict, sam_attempt: str, claude_response: str):
        """Convert the learning into training data."""

        # Create instruction-following training example
        example = {
            "messages": [
                {"role": "user", "content": task["instruction"]},
                {"role": "assistant", "content": claude_response}
            ],
            "metadata": {
                "source": "teacher_student",
                "task_type": task["task_type"],
                "task_id": task["id"],
                "sam_attempt_confidence": task.get("sam_confidence", 0),
                "learned_at": datetime.now().isoformat(),
            }
        }

        # Also create a correction example if SAM was wrong
        if task.get("sam_confidence", 0) < 0.7:
            correction_example = {
                "messages": [
                    {"role": "user", "content": task["instruction"]},
                    {"role": "assistant", "content": sam_attempt},
                    {"role": "user", "content": "That's not quite right. Can you do better?"},
                    {"role": "assistant", "content": claude_response}
                ],
                "metadata": {
                    "source": "teacher_student_correction",
                    "task_type": task["task_type"],
                }
            }

            with open(self.training_output, "a") as f:
                f.write(json.dumps(correction_example) + "\n")

        # Write main example
        with open(self.training_output, "a") as f:
            f.write(json.dumps(example) + "\n")

        logger.info(f"📝 Captured learning for: {task['instruction'][:40]}...")

    def learn_one(self) -> bool:
        """Process one learning task."""
        task = self.db.get_next_task()
        if not task:
            logger.info("No pending tasks in curriculum")
            return False

        logger.info(f"📖 Learning: {task['instruction'][:60]}...")

        # Step 1: SAM attempts
        sam_attempt, confidence = self.attempt_with_mlx(task["instruction"])
        self.db.mark_attempted(task["id"], sam_attempt, confidence)
        logger.info(f"   SAM attempt confidence: {confidence:.2f}")

        # Step 2: Verify with Claude API
        claude_response = self.verify_with_claude(task["instruction"], sam_attempt)

        if claude_response:
            # Step 3: Capture learning
            task["sam_confidence"] = confidence
            self.capture_learning(task, sam_attempt, claude_response)
            self.db.mark_learned(task["id"], claude_response)
            logger.info(f"✅ Learned successfully!")
            return True
        else:
            logger.warning("❌ Could not verify with Claude API")
            return False

    def study_session(self, max_tasks: int = 10, interval_seconds: int = 30):
        """Run a study session - learn multiple tasks."""
        logger.info(f"📚 Starting study session (max {max_tasks} tasks)")

        learned = 0
        for i in range(max_tasks):
            pending = self.db.get_pending_count()
            if pending == 0:
                logger.info("No more tasks to learn")
                break

            logger.info(f"\n--- Task {i+1}/{max_tasks} ({pending} pending) ---")

            if self.learn_one():
                learned += 1

            # Pause between API calls
            if i < max_tasks - 1 and pending > 1:
                logger.info(f"Waiting {interval_seconds}s before next task...")
                time.sleep(interval_seconds)

        logger.info(f"\n📊 Session complete: {learned} tasks learned")
        return learned

    def study_daemon(self, interval_minutes: int = 30):
        """Run continuous study daemon."""
        logger.info("=" * 60)
        logger.info("SAM Student Daemon Starting")
        logger.info(f"Study interval: {interval_minutes} minutes")
        logger.info("=" * 60)

        while True:
            try:
                pending = self.db.get_pending_count()

                if pending > 0:
                    logger.info(f"\n{pending} tasks in curriculum, starting study session...")
                    self.study_session(max_tasks=5)  # 5 tasks per session
                else:
                    logger.info("Curriculum empty, waiting for new tasks...")

                # Wait for next session
                logger.info(f"Next study session in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                logger.info("Student daemon stopped")
                break
            except Exception as e:
                logger.error(f"Study error: {e}")
                time.sleep(60)


def write_initial_curriculum():
    """Write initial curriculum based on SAM's learning needs."""
    teacher = Teacher()

    # Critical Mac/iOS development knowledge
    mac_topics = [
        "SwiftUI @State, @Binding, @ObservedObject, and @EnvironmentObject - when to use each",
        "Swift async/await and structured concurrency with TaskGroups",
        "Core Data with SwiftUI - fetching, updating, and CloudKit sync",
        "Metal compute shaders for GPU acceleration on Apple Silicon",
        "App Sandbox and entitlements for macOS apps",
        "Swift Package Manager - creating, publishing, and dependency resolution",
        "Combine framework publishers, subscribers, and operators",
        "AppKit NSView and NSWindow lifecycle and customization",
        "XCTest and UI testing for SwiftUI apps",
        "Notarization and distribution outside the App Store",
    ]

    # Architecture and design
    architecture_topics = [
        "Design a local-first sync architecture for an iOS/macOS app",
        "Implement a plugin system for a sandboxed macOS app",
        "Architecture for a CLI tool that integrates with Claude API",
        "Design a training data pipeline for fine-tuning language models",
        "Implement efficient semantic search with limited RAM (8GB)",
    ]

    # Roleplay and conversation
    roleplay_topics = [
        "Writing dialogue with distinct character voices and emotional beats",
        "Maintaining narrative consistency across long conversations",
        "Transitioning between different emotional tones naturally",
    ]

    count = 0

    for topic in mac_topics:
        teacher.teach(topic, task_type="coding", priority=1,
                     skills=["swift", "macos", "ios"])
        count += 1

    for topic in architecture_topics:
        teacher.teach(topic, task_type="architecture", priority=2,
                     skills=["design", "architecture"])
        count += 1

    for topic in roleplay_topics:
        teacher.teach(topic, task_type="roleplay", priority=3,
                     skills=["conversation", "creativity"])
        count += 1

    logger.info(f"Wrote {count} tasks to curriculum")
    return count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Teacher-Student Learning")
    parser.add_argument("command", choices=[
        "teach", "teach-batch", "learn", "study", "status", "init"
    ], nargs="?", default="status")
    parser.add_argument("instruction", nargs="?", help="Learning instruction (for teach)")
    parser.add_argument("--type", default="coding", help="Task type")
    parser.add_argument("--priority", type=int, default=2, help="Priority 1-4")
    parser.add_argument("--interval", type=int, default=30, help="Study interval (minutes)")

    args = parser.parse_args()

    if args.command == "teach":
        if not args.instruction:
            print("Usage: teacher_student.py teach 'instruction'")
            sys.exit(1)
        teacher = Teacher()
        task_id = teacher.teach(args.instruction, task_type=args.type, priority=args.priority)
        if task_id:
            print(f"✅ Added task: {task_id}")

    elif args.command == "teach-batch":
        if not args.instruction or not Path(args.instruction).exists():
            print("Usage: teacher_student.py teach-batch curriculum.json")
            sys.exit(1)
        teacher = Teacher()
        with open(args.instruction) as f:
            tasks = json.load(f)
        count = teacher.teach_batch(tasks)
        print(f"✅ Added {count} tasks")

    elif args.command == "learn":
        student = Student()
        student.learn_one()

    elif args.command == "study":
        student = Student()
        student.study_daemon(interval_minutes=args.interval)

    elif args.command == "init":
        count = write_initial_curriculum()
        print(f"✅ Initialized curriculum with {count} tasks")

    elif args.command == "status":
        db = TeacherStudentDB()
        stats = db.get_stats()

        print("\n" + "=" * 50)
        print("SAM TEACHER-STUDENT STATUS")
        print("=" * 50)
        print(f"  Total tasks:     {stats['total_tasks']}")
        print(f"  Pending:         {stats['pending']}")
        print(f"  In progress:     {stats['in_progress']}")
        print(f"  Learned:         {stats['learned']}")
        print(f"\n  By type:")
        for t, count in stats.get('by_type', {}).items():
            print(f"    {t}: {count}")
        print()


if __name__ == "__main__":
    main()
