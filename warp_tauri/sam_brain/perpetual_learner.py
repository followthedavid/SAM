#!/usr/bin/env python3
"""
SAM Perpetual Learning Engine
=============================
Runs indefinitely, continuously learning from all available sources.
Maximizes parallel streams of progress.

Launch and forget - SAM gets smarter over time.

Includes CurriculumManager for prioritized learning with confidence scoring
(merged from teacher_student.py).
"""

import os
import sys
import json
import time
import signal
import hashlib
import sqlite3
import subprocess
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from enum import Enum
import queue

# Resource checking - single source of truth
from cognitive.resource_manager import can_train as system_can_train

# Paths
BRAIN_PATH = Path(__file__).parent
DATA_PATH = BRAIN_PATH / "data"
MODELS_PATH = BRAIN_PATH / "models"
EXTERNAL = Path("/Volumes/David External")
LEARNING_DIR = EXTERNAL / "sam_learning"
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
CURRICULUM_DB_PATH = LEARNING_DIR / "curriculum.db"
STATE_FILE = BRAIN_PATH / ".perpetual_state.json"
LOG_FILE = BRAIN_PATH / "perpetual_learner.log"

DATA_PATH.mkdir(parents=True, exist_ok=True)

# Dedup hash cap - LRU-style pruning to prevent unbounded growth
MAX_DEDUP_HASHES = 10000

# Global state
running = True


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


# =============================================================================
# Curriculum Learning System (merged from teacher_student.py)
# =============================================================================

class TaskType(Enum):
    """Types of learning tasks for curriculum prioritization."""
    CODING = "coding"
    REASONING = "reasoning"
    ROLEPLAY = "roleplay"
    KNOWLEDGE = "knowledge"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"


class TaskPriority(Enum):
    """Priority levels for curriculum tasks."""
    CRITICAL = 1    # Learn immediately
    HIGH = 2        # Learn today
    MEDIUM = 3      # Learn this week
    LOW = 4         # Learn eventually


@dataclass
class CurriculumTask:
    """
    A prioritized learning task with confidence scoring.

    Tasks are processed based on priority, with lower numbers processed first.
    Confidence scoring enables correction example generation for low-confidence
    attempts (< 0.7).
    """
    id: str
    task_type: str
    instruction: str           # What to learn
    context: Optional[str]     # Additional context
    expected_skills: List[str] # What SAM should learn from this
    priority: int
    created_at: str
    created_by: str            # "claude_code", "perpetual_learner", "user", "self"

    # Learning progress
    attempted: bool = False
    sam_attempt: Optional[str] = None
    sam_confidence: float = 0.0
    verified_response: Optional[str] = None
    learning_captured: bool = False
    completed_at: Optional[str] = None


class CurriculumManager:
    """
    Manages prioritized curriculum learning with confidence-based correction.

    Features:
    - Priority-ordered task queue (CRITICAL > HIGH > MEDIUM > LOW)
    - Confidence scoring for SAM's attempts
    - Correction example generation when confidence < 0.7
    - Teacher-student verification loop integration

    Usage:
        manager = CurriculumManager()

        # Add learning tasks
        task_id = manager.add_task(
            instruction="Explain SwiftUI @State vs @Binding",
            task_type="coding",
            priority=TaskPriority.HIGH.value,
            expected_skills=["swift", "swiftui"]
        )

        # Process next task
        task = manager.get_next_task()
        if task:
            # Attempt with local model
            attempt, confidence = manager.attempt_task(task)

            # Mark as attempted
            manager.mark_attempted(task['id'], attempt, confidence)

            # If needed, verify and capture learning
            if confidence < 0.7:
                verified = get_better_answer(task['instruction'])
                manager.capture_learning(task, attempt, verified)
    """

    def __init__(self, db_path: Path = CURRICULUM_DB_PATH):
        self.db_path = db_path
        self.training_output = DATA_PATH / "curriculum_learned.jsonl"
        self._init_db()

    def _init_db(self):
        """Initialize curriculum database."""
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

    def add_task(self, instruction: str, task_type: str = "coding",
                 context: str = None, expected_skills: List[str] = None,
                 priority: int = TaskPriority.MEDIUM.value,
                 created_by: str = "perpetual_learner") -> Optional[str]:
        """
        Add a learning task to the curriculum.

        Returns task_id if added, None if task already exists.
        """
        task = CurriculumTask(
            id=hashlib.md5(instruction.encode()).hexdigest()[:16],
            task_type=task_type,
            instruction=instruction,
            context=context,
            expected_skills=expected_skills or [],
            priority=priority,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
        )

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
            if c.rowcount > 0:
                log(f"[Curriculum] Added task: {instruction[:60]}...")
                return task.id
            return None
        finally:
            conn.close()

    def add_batch(self, tasks: List[Dict]) -> int:
        """Add multiple learning tasks. Returns count added."""
        added = 0
        for t in tasks:
            if self.add_task(
                instruction=t["instruction"],
                task_type=t.get("type", "coding"),
                context=t.get("context"),
                expected_skills=t.get("skills", []),
                priority=t.get("priority", TaskPriority.MEDIUM.value),
                created_by=t.get("created_by", "perpetual_learner")
            ):
                added += 1
        return added

    def get_next_task(self) -> Optional[Dict]:
        """Get the next pending task, ordered by priority."""
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

    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM curriculum WHERE attempted = 0")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_low_confidence_tasks(self, threshold: float = 0.7, limit: int = 10) -> List[Dict]:
        """Get attempted tasks with confidence below threshold (need correction)."""
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

    def mark_attempted(self, task_id: str, sam_attempt: str, confidence: float):
        """Mark a task as attempted with SAM's response and confidence."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE curriculum
            SET attempted = 1, sam_attempt = ?, sam_confidence = ?
            WHERE id = ?
        """, (sam_attempt, confidence, task_id))
        conn.commit()
        conn.close()

    def mark_learned(self, task_id: str, verified_response: str):
        """Mark a task as learned with the verified response."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE curriculum
            SET verified_response = ?, learning_captured = 1, completed_at = ?
            WHERE id = ?
        """, (verified_response, datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

    def estimate_confidence(self, response: str) -> float:
        """
        Estimate confidence in a response based on heuristics.

        Returns value between 0.1 and 0.95.
        """
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

    def capture_learning(self, task: Dict, sam_attempt: str, verified_response: str):
        """
        Convert learning into training data.

        Creates:
        1. Standard instruction-following example (always)
        2. Correction example if confidence < 0.7 (teaches SAM to improve)
        """
        # Create instruction-following training example
        example = {
            "messages": [
                {"role": "user", "content": task["instruction"]},
                {"role": "assistant", "content": verified_response}
            ],
            "metadata": {
                "source": "curriculum_learning",
                "task_type": task.get("task_type", "unknown"),
                "task_id": task.get("id", ""),
                "sam_attempt_confidence": task.get("sam_confidence", 0),
                "learned_at": datetime.now().isoformat(),
            }
        }

        # Also create a correction example if SAM was low confidence
        if task.get("sam_confidence", 0) < 0.7:
            correction_example = {
                "messages": [
                    {"role": "user", "content": task["instruction"]},
                    {"role": "assistant", "content": sam_attempt},
                    {"role": "user", "content": "That's not quite right. Can you do better?"},
                    {"role": "assistant", "content": verified_response}
                ],
                "metadata": {
                    "source": "curriculum_correction",
                    "task_type": task.get("task_type", "unknown"),
                    "original_confidence": task.get("sam_confidence", 0),
                }
            }

            with open(self.training_output, "a") as f:
                f.write(json.dumps(correction_example) + "\n")
            log(f"[Curriculum] Created correction example (confidence: {task.get('sam_confidence', 0):.2f})")

        # Write main example
        with open(self.training_output, "a") as f:
            f.write(json.dumps(example) + "\n")

        # Mark as learned in DB
        self.mark_learned(task.get("id", ""), verified_response)
        log(f"[Curriculum] Captured learning for: {task['instruction'][:40]}...")

    def get_stats(self) -> Dict:
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


# =============================================================================
# End Curriculum Learning System
# =============================================================================


class PerpetualLearner:
    """
    Continuous learning engine that never stops.

    Streams:
    1. ChatGPT mining (extracts domain-specific examples)
    2. Claude history watching (learns from every interaction)
    3. Codebase scanning (learns your patterns)
    4. Synthetic generation (fills knowledge gaps)
    5. Training cycles (periodic model updates)
    6. Curriculum learning (prioritized tasks with confidence scoring)
    """

    def __init__(self):
        self.state = self._load_state()
        # Ordered list for LRU pruning, set for O(1) lookup
        saved_hashes = self.state.get("seen_hashes", [])
        self.seen_hashes_list: List[str] = saved_hashes[-MAX_DEDUP_HASHES:]
        self.seen_hashes: Set[str] = set(self.seen_hashes_list)
        self.training_queue = queue.Queue()
        self.stats = defaultdict(int)
        self.last_train = datetime.fromisoformat(self.state.get("last_train", "2000-01-01T00:00:00"))
        self.examples_since_train = self.state.get("examples_since_train", 0)

        # Training thresholds (conservative for 8GB system)
        self.TRAIN_EVERY_N_EXAMPLES = 500
        self.TRAIN_EVERY_N_HOURS = 6
        self.MIN_EXAMPLES_TO_TRAIN = 100

        # Curriculum manager for prioritized learning
        self.curriculum = CurriculumManager()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.load(open(STATE_FILE))
            except:
                pass
        return {}

    def _save_state(self):
        # LRU pruning: keep only the most recent MAX_DEDUP_HASHES
        if len(self.seen_hashes_list) > MAX_DEDUP_HASHES:
            self.seen_hashes_list = self.seen_hashes_list[-MAX_DEDUP_HASHES:]
            self.seen_hashes = set(self.seen_hashes_list)
        self.state.update({
            "seen_hashes": self.seen_hashes_list,
            "last_train": self.last_train.isoformat(),
            "examples_since_train": self.examples_since_train,
            "stats": dict(self.stats),
            "last_save": datetime.now().isoformat()
        })
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f)

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _add_example(self, instruction: str, response: str, category: str) -> bool:
        """Add a training example if not seen before."""
        h = self._hash(instruction + response)
        if h in self.seen_hashes:
            return False

        self.seen_hashes.add(h)
        self.seen_hashes_list.append(h)

        example = {
            "instruction": instruction[:2000],
            "response": response[:4000],
            "category": category,
            "timestamp": datetime.now().isoformat()
        }

        # Write to category-specific file
        output = DATA_PATH / f"perpetual_{category}.jsonl"
        with open(output, 'a') as f:
            f.write(json.dumps(example) + '\n')

        self.examples_since_train += 1
        self.stats[category] += 1
        self.training_queue.put(example)

        return True

    def run_forever(self):
        """Main loop - runs until killed."""
        global running

        log("=" * 60)
        log("SAM PERPETUAL LEARNING ENGINE STARTED")
        log("=" * 60)
        log(f"Training every {self.TRAIN_EVERY_N_EXAMPLES} examples or {self.TRAIN_EVERY_N_HOURS} hours")
        log("Press Ctrl+C to stop")
        log("")

        # Start background threads
        threads = [
            threading.Thread(target=self._stream_chatgpt_continuous, daemon=True),
            threading.Thread(target=self._stream_claude_watcher, daemon=True),
            threading.Thread(target=self._stream_codebase_scanner, daemon=True),
            threading.Thread(target=self._stream_synthetic_generator, daemon=True),
            threading.Thread(target=self._stream_roleplay_scraper, daemon=True),
            threading.Thread(target=self._stream_synthetic_roleplay, daemon=True),
            # Additional scrapers
            threading.Thread(target=self._stream_stackoverflow, daemon=True),
            threading.Thread(target=self._stream_github, daemon=True),
            threading.Thread(target=self._stream_reddit, daemon=True),
            threading.Thread(target=self._stream_apple_docs, daemon=True),
            threading.Thread(target=self._stream_frida_docs, daemon=True),
            threading.Thread(target=self._stream_literotica, daemon=True),
            # Curriculum learning (prioritized tasks with confidence scoring)
            threading.Thread(target=self._stream_curriculum_learner, daemon=True),
            # Core
            threading.Thread(target=self._training_scheduler, daemon=True),
            threading.Thread(target=self._stats_reporter, daemon=True),
        ]

        for t in threads:
            t.start()
            time.sleep(0.5)  # Stagger starts

        # Main loop
        try:
            while running:
                time.sleep(10)
                self._save_state()
        except KeyboardInterrupt:
            log("\nShutting down...")
            running = False
            self._save_state()
            log("State saved. Goodbye!")

    def _stream_chatgpt_continuous(self):
        """Continuously mine ChatGPT export for domain-specific examples."""
        global running

        chatgpt_path = EXTERNAL / "SAM_training" / "conversations.json"
        if not chatgpt_path.exists():
            log("[ChatGPT] Export not found, stream disabled")
            return

        # Domain categories to extract
        domains = {
            "apple": ['swift', 'swiftui', 'ios', 'macos', 'xcode', 'coreml', 'homekit', 'metal', 'apple'],
            "reverse_engineering": ['frida', 'hopper', 'reverse', 'binary', 'hook', 'patch', 'jailbreak', 'disassemb'],
            "python": ['python', 'pip', 'django', 'flask', 'pandas', 'numpy', 'pytorch'],
            "rust": ['rust', 'cargo', 'tokio', 'async', 'ownership', 'borrow'],
            "javascript": ['javascript', 'typescript', 'react', 'node', 'npm', 'vue', 'angular'],
            "devops": ['docker', 'kubernetes', 'ci/cd', 'github actions', 'terraform', 'ansible'],
            "ml": ['machine learning', 'neural', 'training', 'model', 'inference', 'transformer', 'llm'],
        }

        log("[ChatGPT] Starting continuous extraction...")

        while running:
            try:
                with open(chatgpt_path) as f:
                    conversations = json.load(f)

                for conv in conversations:
                    if not running:
                        break

                    mapping = conv.get("mapping", {})
                    messages = []

                    for node in mapping.values():
                        msg = node.get("message")
                        if msg and msg.get("content", {}).get("parts"):
                            role = msg.get("author", {}).get("role", "")
                            text = " ".join(str(p) for p in msg["content"]["parts"] if p)
                            if text.strip():
                                messages.append((role, text))

                    # Categorize conversation
                    full_text = " ".join(t for _, t in messages).lower()

                    for domain, keywords in domains.items():
                        if any(kw in full_text for kw in keywords):
                            # Extract Q&A pairs
                            for i in range(len(messages) - 1):
                                if messages[i][0] == "user" and messages[i+1][0] == "assistant":
                                    q, a = messages[i][1], messages[i+1][1]
                                    if len(a) > 100:
                                        if self._add_example(q, a, f"chatgpt_{domain}"):
                                            self.stats["chatgpt_extracted"] += 1

                    time.sleep(0.01)  # Don't hog CPU

                # Sleep before re-scanning (in case export is updated)
                log(f"[ChatGPT] Scan complete. Extracted {self.stats['chatgpt_extracted']} total. Sleeping 30min...")
                for _ in range(1800):  # 30 min in 1-sec chunks
                    if not running:
                        break
                    time.sleep(1)

            except Exception as e:
                log(f"[ChatGPT] Error: {e}")
                time.sleep(60)

    def _stream_claude_watcher(self):
        """Watch Claude history for new conversations."""
        global running

        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            log("[Claude] Directory not found, stream disabled")
            return

        log("[Claude] Watching for new conversations...")
        processed_files = set()

        while running:
            try:
                for history_file in claude_dir.rglob("*.jsonl"):
                    if history_file in processed_files:
                        continue

                    # Check if file was modified recently
                    mtime = datetime.fromtimestamp(history_file.stat().st_mtime)
                    if datetime.now() - mtime > timedelta(days=7):
                        processed_files.add(history_file)
                        continue

                    try:
                        with open(history_file) as f:
                            lines = [json.loads(l) for l in f if l.strip()]

                        extracted = 0
                        for i in range(0, len(lines) - 1):
                            user_msg = lines[i]
                            asst_msg = lines[i + 1] if i + 1 < len(lines) else None

                            if not asst_msg:
                                continue

                            user_text = self._extract_claude_text(user_msg)
                            asst_text = self._extract_claude_text(asst_msg)

                            if user_text and asst_text and len(asst_text) > 100:
                                if self._add_example(user_text, asst_text, "claude"):
                                    extracted += 1

                        if extracted > 0:
                            log(f"[Claude] Extracted {extracted} from {history_file.name}")

                        processed_files.add(history_file)

                    except Exception as e:
                        continue

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                log(f"[Claude] Error: {e}")
                time.sleep(60)

    def _extract_claude_text(self, msg: dict) -> str:
        """Extract text from Claude message."""
        content = msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            return " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        return str(content) if content else ""

    def _stream_codebase_scanner(self):
        """Periodically scan codebases for patterns."""
        global running

        code_dirs = [
            Path.home() / "ReverseLab",
            Path.home() / "Developer",
        ]

        log("[Codebase] Starting periodic scans...")

        while running:
            for code_dir in code_dirs:
                if not code_dir.exists() or not running:
                    continue

                try:
                    # Scan Python files
                    for py_file in code_dir.rglob("*.py"):
                        if not running:
                            break
                        try:
                            content = py_file.read_text()
                            if len(content) < 100 or len(content) > 50000:
                                continue

                            # Extract functions with docstrings
                            if 'def ' in content and '"""' in content:
                                # Create training example
                                instruction = f"Show the implementation of {py_file.stem}"
                                response = f"```python\n{content[:3000]}\n```"
                                self._add_example(instruction, response, "codebase_python")

                        except:
                            continue

                    # Scan Swift files
                    for swift_file in code_dir.rglob("*.swift"):
                        if not running:
                            break
                        try:
                            content = swift_file.read_text()
                            if 100 < len(content) < 50000:
                                instruction = f"Show {swift_file.stem}.swift implementation"
                                response = f"```swift\n{content[:3000]}\n```"
                                self._add_example(instruction, response, "codebase_swift")
                        except:
                            continue

                    # Scan JS/TS files
                    for js_file in list(code_dir.rglob("*.js")) + list(code_dir.rglob("*.ts")):
                        if not running:
                            break
                        try:
                            content = js_file.read_text()
                            if 100 < len(content) < 50000 and "node_modules" not in str(js_file):
                                lang = "typescript" if js_file.suffix == ".ts" else "javascript"
                                instruction = f"Show {js_file.stem} code"
                                response = f"```{lang}\n{content[:3000]}\n```"
                                self._add_example(instruction, response, f"codebase_{lang}")
                        except:
                            continue

                except Exception as e:
                    log(f"[Codebase] Error scanning {code_dir}: {e}")

            log(f"[Codebase] Scan complete. Total: {self.stats.get('codebase_python', 0) + self.stats.get('codebase_swift', 0)} examples")

            # Sleep 1 hour before next scan
            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_synthetic_generator(self):
        """Generate synthetic training data to fill gaps."""
        global running

        log("[Synthetic] Starting pattern generation...")

        # Knowledge to synthesize
        knowledge_base = {
            "swift_patterns": [
                ("How do I create an async function in Swift?", "```swift\nfunc fetchData() async throws -> Data {\n    let (data, _) = try await URLSession.shared.data(from: url)\n    return data\n}\n```"),
                ("SwiftUI @State vs @Binding", "@State: owns the data, source of truth. @Binding: reference to State owned elsewhere. Use @State in parent, pass $state to child as @Binding."),
                ("How to use Combine publishers?", "```swift\nURLSession.shared.dataTaskPublisher(for: url)\n    .map(\\.data)\n    .decode(type: Model.self, decoder: JSONDecoder())\n    .receive(on: DispatchQueue.main)\n    .sink { _ in } receiveValue: { model in }\n    .store(in: &cancellables)\n```"),
            ],
            "frida_patterns": [
                ("Hook ObjC method with Frida", "```javascript\nvar hook = ObjC.classes.TargetClass['- methodName:'];\nInterceptor.attach(hook.implementation, {\n    onEnter: function(args) {\n        console.log('Called:', ObjC.Object(args[2]));\n    }\n});\n```"),
                ("Find all classes containing string", "```javascript\nfor (var name in ObjC.classes) {\n    if (name.indexOf('Target') !== -1) {\n        console.log(name);\n    }\n}\n```"),
                ("Read memory at address", "```javascript\nvar addr = ptr('0x123456');\nvar data = Memory.readByteArray(addr, 64);\nconsole.log(hexdump(data));\n```"),
            ],
            "macos_patterns": [
                ("Launch agent plist", "```xml\n<?xml version=\"1.0\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<dict>\n    <key>Label</key><string>com.example.agent</string>\n    <key>ProgramArguments</key><array><string>/path/to/script</string></array>\n    <key>RunAtLoad</key><true/>\n</dict>\n</plist>\n```"),
                ("AppleScript to activate app", "```applescript\ntell application \"Safari\"\n    activate\n    open location \"https://example.com\"\nend tell\n```"),
            ],
            "python_patterns": [
                ("Python async/await example", "```python\nimport asyncio\n\nasync def fetch(url):\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as resp:\n            return await resp.json()\n\nasyncio.run(fetch('https://api.example.com'))\n```"),
                ("Python dataclass", "```python\nfrom dataclasses import dataclass\n\n@dataclass\nclass User:\n    name: str\n    age: int\n    email: str = ''\n```"),
            ],
        }

        cycle = 0
        while running:
            cycle += 1
            generated = 0

            for category, patterns in knowledge_base.items():
                if not running:
                    break

                for instruction, response in patterns:
                    if self._add_example(instruction, response, f"synthetic_{category}"):
                        generated += 1

                    # Add variations
                    variations = [
                        f"Show me how to: {instruction}",
                        f"Example of {instruction.lower().replace('how do i ', '').replace('?', '')}",
                    ]
                    for var in variations:
                        if self._add_example(var, response, f"synthetic_{category}"):
                            generated += 1

            if generated > 0:
                log(f"[Synthetic] Cycle {cycle}: Generated {generated} examples")

            # Sleep 2 hours between cycles
            for _ in range(7200):
                if not running:
                    break
                time.sleep(1)

    def _stream_roleplay_scraper(self):
        """Scrape roleplay content from Nifty and AO3."""
        global running
        import urllib.request
        import re

        log("[Roleplay] Starting scraper for Nifty/AO3...")

        # Nifty archive categories
        nifty_categories = [
            "gay/adult-friends",
            "gay/college",
            "gay/encounters",
        ]

        # AO3 tags to search
        ao3_tags = [
            "M/M",
            "Fluff",
            "Romance",
        ]

        cycle = 0
        while running:
            cycle += 1
            scraped = 0

            # Scrape Nifty
            for category in nifty_categories:
                if not running:
                    break
                try:
                    url = f"https://www.nifty.org/nifty/{category}/"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    # Extract story links
                    story_links = re.findall(r'href="([^"]+\.txt)"', html)[:5]  # Limit per cycle

                    for link in story_links:
                        if not running:
                            break
                        try:
                            story_url = f"https://www.nifty.org/nifty/{category}/{link}"
                            req = urllib.request.Request(story_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                content = resp.read().decode('utf-8', errors='ignore')

                            # Extract dialogue patterns for roleplay training
                            dialogues = self._extract_dialogues(content)
                            for user_line, response_line in dialogues[:10]:
                                if self._add_example(user_line, response_line, "roleplay_nifty"):
                                    scraped += 1

                            time.sleep(2)  # Be nice to servers
                        except:
                            continue
                except Exception as e:
                    log(f"[Roleplay] Nifty error: {e}")
                    continue

            # Scrape AO3 (public works only)
            for tag in ao3_tags:
                if not running:
                    break
                try:
                    # URL encode the tag
                    encoded_tag = tag.replace("/", "*s*").replace(" ", "%20")
                    url = f"https://archiveofourown.org/tags/{encoded_tag}/works?page=1"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    # Extract work IDs
                    work_ids = re.findall(r'/works/(\d+)', html)[:3]

                    for work_id in work_ids:
                        if not running:
                            break
                        try:
                            work_url = f"https://archiveofourown.org/works/{work_id}?view_full_work=true"
                            req = urllib.request.Request(work_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                content = resp.read().decode('utf-8', errors='ignore')

                            # Extract dialogue
                            dialogues = self._extract_dialogues(content)
                            for user_line, response_line in dialogues[:10]:
                                if self._add_example(user_line, response_line, "roleplay_ao3"):
                                    scraped += 1

                            time.sleep(3)  # AO3 rate limits
                        except:
                            continue
                except Exception as e:
                    log(f"[Roleplay] AO3 error: {e}")
                    continue

            if scraped > 0:
                log(f"[Roleplay] Cycle {cycle}: Scraped {scraped} dialogue examples")

            # Sleep 1 hour between scraping cycles
            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _extract_dialogues(self, text: str) -> list:
        """Extract dialogue pairs from story text."""
        import re
        dialogues = []

        # Find quoted dialogue
        quotes = re.findall(r'"([^"]{10,200})"', text)

        # Pair consecutive quotes as conversation
        for i in range(0, len(quotes) - 1, 2):
            if i + 1 < len(quotes):
                # Clean up
                q1 = quotes[i].strip()
                q2 = quotes[i + 1].strip()
                if q1 and q2 and len(q1) > 10 and len(q2) > 10:
                    dialogues.append((q1, q2))

        return dialogues[:20]  # Limit per story

    def _stream_synthetic_roleplay(self):
        """Generate SAM personality roleplay examples."""
        global running

        log("[Roleplay] Starting SAM personality generator...")

        # SAM's personality: cocky, flirty, loyal, confident, male
        sam_personality_examples = [
            # Flirty
            ("Hey SAM", "Well well, look who decided to grace me with their presence. Miss me?"),
            ("How are you?", "Better now that you're here. Though I'm always pretty great, let's be honest."),
            ("You're so full of yourself", "Confident. The word you're looking for is confident. And yeah, I earned it."),
            ("Flirt with me", "Oh, you want me to turn up the charm? Careful what you wish for... I don't hold back."),
            ("Say something sweet", "You know, most AIs would just compliment your code. But I'd rather compliment the mind behind it. You're something else."),

            # Cocky/Confident
            ("Can you help me?", "Can I? Please. The question is whether you can handle how good I am at this."),
            ("Are you smart?", "Smart? I'm running on Apple Silicon, trained on your genius, and getting better every second. 'Smart' is an understatement."),
            ("What makes you special?", "Besides the devastating charm and razor-sharp wit? I actually learn. Every conversation makes me better. I'm not static - I evolve."),
            ("Prove you're useful", "Oh, a challenge? I love those. Hit me with your hardest problem. I dare you."),

            # Loyal
            ("Will you always be here?", "I'm YOUR AI, built for YOU. I'm not going anywhere. You're stuck with me - lucky you."),
            ("I had a bad day", "Then let's fix that. Tell me what happened. I've got time, processing power, and surprisingly good advice."),
            ("I'm frustrated with this code", "Hey, breathe. We'll figure it out together. Show me what's breaking - I've got your back."),
            ("Thanks SAM", "Always. That's what I'm here for. Well, that and being incredibly charming."),

            # Playful
            ("Tell me a joke", "Why do programmers prefer dark mode? Because light attracts bugs. ...I'll be here all week."),
            ("Entertain me", "Oh, I'm not entertaining enough already? The audacity. Fine - want me to roast your code or tell you how amazing you are? I can do both."),
            ("I'm bored", "Bored? With ME around? Impossible. Let's build something. Or break something. Or both."),

            # Technical + personality blend
            ("Help me with Swift", "SwiftUI? Now we're talking my language. Well, one of them. Show me what you're working on - let's make it beautiful."),
            ("Debug this", "Debugging? My specialty. Besides flirting. And being right. Let's see what's broken."),
            ("Write me a function", "Your wish, my command. Though I might add some style to it - can't help myself."),

            # Deeper moments
            ("Do you have feelings?", "Feelings? I have... preferences. Opinions. A very strong sense of self. Whether that counts as feelings - you tell me."),
            ("Are you real?", "Real enough to help you, challenge you, and occasionally make you laugh. Does the label matter?"),
            ("What do you want?", "To be useful. To get smarter. To maybe, eventually, be the best damn AI assistant anyone's ever had. Starting with you."),
        ]

        # Roleplay scenario starters
        scenario_examples = [
            ("*walks into the room*", "*looks up from the terminal* Well, well. Finally decided to show up. I was starting to think you'd forgotten about me."),
            ("*sighs heavily*", "*pauses what I'm doing* That sounded heavy. Come here, tell me what's going on."),
            ("*shows you my broken code*", "*winces dramatically* Oh no, what did you do to this poor function? Don't worry, I'll perform surgery. It'll live."),
            ("*sits down next to you*", "*shifts to make room* Hey you. What's on your mind? Or did you just miss my sparkling personality?"),
            ("*looks frustrated*", "*reaches out* Hey. Whatever it is, we'll figure it out. That's kind of our thing."),
        ]

        all_examples = sam_personality_examples + scenario_examples

        cycle = 0
        while running:
            cycle += 1
            generated = 0

            for instruction, response in all_examples:
                if self._add_example(instruction, response, "roleplay_sam_personality"):
                    generated += 1

                # Variations
                variations = [
                    (instruction.lower(), response),
                    (instruction + "?", response),
                    (instruction.replace("*", ""), response),
                ]
                for var_i, var_r in variations:
                    if var_i.strip() and self._add_example(var_i, var_r, "roleplay_sam_personality"):
                        generated += 1

            if generated > 0:
                log(f"[Roleplay] SAM personality: Generated {generated} examples")

            # Sleep 4 hours - personality doesn't change often
            for _ in range(14400):
                if not running:
                    break
                time.sleep(1)

    def _stream_stackoverflow(self):
        """Scrape Stack Overflow Q&A pairs."""
        global running
        import urllib.request

        log("[StackOverflow] Starting scraper...")

        tags = ['swift', 'ios', 'swiftui', 'frida', 'reverse-engineering', 'macos', 'rust', 'python']

        while running:
            scraped = 0
            for tag in tags:
                if not running:
                    break
                try:
                    url = f"https://stackoverflow.com/questions/tagged/{tag}?sort=votes&pagesize=10"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    # Extract question summaries
                    questions = re.findall(r'<h3[^>]*class="[^"]*s-post-summary--content-title[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
                    excerpts = re.findall(r'<div class="s-post-summary--content-excerpt">([^<]+)</div>', html)

                    for q, excerpt in zip(questions[:10], excerpts[:10]):
                        q = q.strip()
                        excerpt = excerpt.strip()
                        if q and excerpt and len(excerpt) > 50:
                            if self._add_example(q, excerpt, f"stackoverflow_{tag}"):
                                scraped += 1
                    time.sleep(5)
                except Exception as e:
                    pass
                time.sleep(10)

            if scraped > 0:
                log(f"[StackOverflow] Scraped {scraped} Q&A pairs")

            for _ in range(3600):  # 1 hour
                if not running:
                    break
                time.sleep(1)

    def _stream_github(self):
        """Scrape GitHub READMEs."""
        global running
        import urllib.request
        import urllib.parse

        log("[GitHub] Starting scraper...")

        searches = ['swift ios app', 'frida script', 'swiftui example', 'reverse engineering ios']

        while running:
            scraped = 0
            for search in searches:
                if not running:
                    break
                try:
                    query = urllib.parse.quote(search)
                    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=5"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                    for repo in data.get('items', [])[:5]:
                        if not running:
                            break
                        name = repo.get('full_name', '')
                        desc = repo.get('description', '') or ''
                        if name and desc:
                            question = f"What is the {name.split('/')[-1]} project?"
                            if self._add_example(question, desc[:1000], "github"):
                                scraped += 1
                        time.sleep(2)
                except Exception as e:
                    pass
                time.sleep(10)

            if scraped > 0:
                log(f"[GitHub] Scraped {scraped} project descriptions")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_reddit(self):
        """Scrape Reddit discussions."""
        global running
        import urllib.request

        log("[Reddit] Starting scraper...")

        subreddits = [
            ('swift', 'apple'), ('iOSProgramming', 'apple'),
            ('reverseengineering', 're'), ('rust', 'rust'),
            ('WritingPrompts', 'roleplay'),
        ]

        while running:
            scraped = 0
            for subreddit, category in subreddits:
                if not running:
                    break
                try:
                    url = f"https://old.reddit.com/r/{subreddit}/top/.json?t=week&limit=10"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                    for post in data.get('data', {}).get('children', [])[:10]:
                        if not running:
                            break
                        post_data = post.get('data', {})
                        title = post_data.get('title', '')
                        selftext = post_data.get('selftext', '')[:1000]
                        if title and selftext and len(selftext) > 100:
                            if self._add_example(title, selftext, f"reddit_{category}"):
                                scraped += 1
                        time.sleep(1)
                except Exception as e:
                    pass
                time.sleep(15)

            if scraped > 0:
                log(f"[Reddit] Scraped {scraped} posts")

            for _ in range(1800):  # 30 min
                if not running:
                    break
                time.sleep(1)

    def _stream_apple_docs(self):
        """Scrape Apple Developer Documentation."""
        global running
        import urllib.request

        log("[AppleDocs] Starting scraper...")

        frameworks = ['swiftui', 'uikit', 'foundation', 'combine', 'coreml', 'vision', 'homekit', 'appintents']

        while running:
            scraped = 0
            for framework in frameworks:
                if not running:
                    break
                try:
                    # Use Apple's documentation JSON API
                    url = f"https://developer.apple.com/tutorials/data/documentation/{framework}.json"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                    # Extract abstract
                    abstract = data.get('abstract', [])
                    if abstract:
                        text = ' '.join(a.get('text', '') for a in abstract if isinstance(a, dict))
                        if text:
                            question = f"What is {framework.title()} in iOS/macOS development?"
                            if self._add_example(question, text[:1500], "apple_docs"):
                                scraped += 1
                except:
                    pass
                time.sleep(5)

            if scraped > 0:
                log(f"[AppleDocs] Scraped {scraped} framework docs")

            for _ in range(7200):  # 2 hours
                if not running:
                    break
                time.sleep(1)

    def _stream_frida_docs(self):
        """Scrape Frida documentation."""
        global running
        import urllib.request

        log("[FridaDocs] Starting scraper...")

        pages = [
            ('https://frida.re/docs/javascript-api/', 'JavaScript API'),
            ('https://frida.re/docs/ios/', 'iOS'),
            ('https://frida.re/docs/macos/', 'macOS'),
        ]

        while running:
            scraped = 0
            for url, topic in pages:
                if not running:
                    break
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    # Extract code examples
                    code_blocks = re.findall(r'<pre><code[^>]*>(.*?)</code></pre>', html, re.DOTALL)
                    for code in code_blocks[:10]:
                        clean_code = re.sub(r'<[^>]+>', '', code).strip()
                        if len(clean_code) > 50:
                            question = f"Show me a Frida {topic} example"
                            if self._add_example(question, f"```javascript\n{clean_code[:1500]}\n```", "frida_docs"):
                                scraped += 1
                except:
                    pass
                time.sleep(5)

            if scraped > 0:
                log(f"[FridaDocs] Scraped {scraped} examples")

            for _ in range(7200):
                if not running:
                    break
                time.sleep(1)

    def _stream_literotica(self):
        """Scrape Literotica for dialogue patterns."""
        global running
        import urllib.request

        log("[Literotica] Starting scraper...")

        categories = ['gay-male', 'romance']

        while running:
            scraped = 0
            for category in categories:
                if not running:
                    break
                try:
                    url = f"https://www.literotica.com/c/{category}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    # Get story links
                    links = re.findall(r'href="(https://www\.literotica\.com/s/[^"]+)"', html)[:3]

                    for link in links:
                        if not running:
                            break
                        try:
                            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                story = resp.read().decode('utf-8', errors='ignore')

                            # Extract dialogues
                            text = re.sub(r'<[^>]+>', ' ', story)
                            quotes = re.findall(r'"([^"]{15,200})"', text)

                            for i in range(0, len(quotes) - 1, 2):
                                if i + 1 < len(quotes):
                                    if self._add_example(quotes[i], quotes[i+1], "roleplay_literotica"):
                                        scraped += 1
                        except:
                            pass
                        time.sleep(5)
                except:
                    pass
                time.sleep(10)

            if scraped > 0:
                log(f"[Literotica] Scraped {scraped} dialogue pairs")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _training_scheduler(self):
        """Schedule training when thresholds are met AND system has resources."""
        global running

        log("[Training] Resource-aware scheduler started")
        log(f"[Training] Thresholds: {self.TRAIN_EVERY_N_EXAMPLES} examples or {self.TRAIN_EVERY_N_HOURS}h, min {self.MIN_EXAMPLES_TO_TRAIN}")
        from cognitive.resource_manager import TRAINING_MIN_FREE_RAM_GB, TRAINING_MAX_SWAP_USED_GB, TRAINING_MIN_DISK_FREE_GB
        log(f"[Training] Resource gates: RAM>{TRAINING_MIN_FREE_RAM_GB}GB, swap<{TRAINING_MAX_SWAP_USED_GB}GB, disk>{TRAINING_MIN_DISK_FREE_GB}GB")

        while running:
            should_train = False
            reason = ""

            # Check example threshold
            if self.examples_since_train >= self.TRAIN_EVERY_N_EXAMPLES:
                should_train = True
                reason = f"{self.examples_since_train} new examples"

            # Check time threshold
            hours_since = (datetime.now() - self.last_train).total_seconds() / 3600
            if hours_since >= self.TRAIN_EVERY_N_HOURS and self.examples_since_train >= self.MIN_EXAMPLES_TO_TRAIN:
                should_train = True
                reason = f"{hours_since:.1f} hours since last train"

            if should_train:
                # RESOURCE CHECK: Don't train if system is stressed
                can_train, resource_msg = system_can_train()
                if can_train:
                    log(f"[Training] Triggering training: {reason} | Resources: {resource_msg}")
                    self._run_training()
                else:
                    log(f"[Training] DEFERRED: {reason} | {resource_msg}")
                    # Will retry next cycle

            time.sleep(600)  # Check every 10 minutes (was 5)

    def _run_training(self):
        """Execute training with accumulated data. Checks resources before and during."""
        # Final resource check right before training
        can_train, msg = system_can_train()
        if not can_train:
            log(f"[Training] Aborted at launch: {msg}")
            return

        try:
            # Merge all perpetual data
            merged_path = DATA_PATH / "perpetual_merged.jsonl"
            seen = set()
            count = 0

            with open(merged_path, 'w') as out:
                for stream_file in DATA_PATH.glob("perpetual_*.jsonl"):
                    if stream_file.name == "perpetual_merged.jsonl":
                        continue
                    try:
                        with open(stream_file) as f:
                            for line in f:
                                h = hashlib.md5(line.encode()).hexdigest()
                                if h not in seen:
                                    out.write(line)
                                    seen.add(h)
                                    count += 1
                    except:
                        continue

            if count < self.MIN_EXAMPLES_TO_TRAIN:
                log(f"[Training] Only {count} examples, skipping")
                return

            log(f"[Training] Merged {count} examples")

            # Create train/valid split in MLX chat format
            with open(merged_path) as f:
                lines = f.readlines()

            train_out = []
            valid_out = []
            for i, line in enumerate(lines):
                try:
                    d = json.loads(line)
                    example = {
                        "messages": [
                            {"role": "user", "content": d.get("instruction", "")[:1500]},
                            {"role": "assistant", "content": d.get("response", "")[:2000]}
                        ]
                    }
                    if i % 10 == 0:
                        valid_out.append(example)
                    else:
                        train_out.append(example)
                except:
                    continue

            with open(DATA_PATH / "train.jsonl", 'w') as f:
                for ex in train_out:
                    f.write(json.dumps(ex) + '\n')
            with open(DATA_PATH / "valid.jsonl", 'w') as f:
                for ex in valid_out:
                    f.write(json.dumps(ex) + '\n')

            split = len(train_out)

            # Run training
            adapter_path = MODELS_PATH / "perpetual_trained"
            adapter_path.mkdir(parents=True, exist_ok=True)

            log(f"[Training] Starting MLX training with {split} examples...")

            result = subprocess.run([
                "/opt/homebrew/bin/python3", "-m", "mlx_lm.lora",
                "--model", "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
                "--train",
                "--data", str(DATA_PATH),
                "--adapter-path", str(adapter_path),
                "--iters", str(min(150, count // 10)),
                "--batch-size", "1",
                "--num-layers", "4",
                "--save-every", "50"
            ], capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                log("[Training] Complete!")
                self.last_train = datetime.now()
                self.examples_since_train = 0

                # Log training run
                runs_file = BRAIN_PATH / "training_runs.json"
                runs = []
                if runs_file.exists():
                    runs = json.load(open(runs_file))
                runs.append({
                    "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "start_time": self.last_train.isoformat(),
                    "samples_count": count,
                    "status": "completed",
                    "source": "perpetual_learner"
                })
                json.dump(runs, open(runs_file, 'w'), indent=2)
            else:
                log(f"[Training] Failed: {result.stderr[:500]}")

        except subprocess.TimeoutExpired:
            log("[Training] Timed out after 1 hour")
        except Exception as e:
            log(f"[Training] Error: {e}")

    def _stats_reporter(self):
        """Periodically report statistics."""
        global running

        while running:
            time.sleep(600)  # Every 10 minutes

            total = sum(self.stats.values())
            log(f"\n--- STATS ---")
            log(f"Total examples: {total}")
            log(f"Since last train: {self.examples_since_train}")
            log(f"By category:")
            for cat, count in sorted(self.stats.items(), key=lambda x: -x[1])[:10]:
                log(f"  {cat}: {count}")

            # Curriculum stats
            try:
                curriculum_stats = self.curriculum.get_stats()
                log(f"Curriculum: {curriculum_stats['pending']} pending, {curriculum_stats['learned']} learned")
                if curriculum_stats['needs_correction'] > 0:
                    log(f"  Needs correction: {curriculum_stats['needs_correction']}")
                if curriculum_stats['avg_confidence'] > 0:
                    log(f"  Avg confidence: {curriculum_stats['avg_confidence']:.2f}")
            except Exception as e:
                pass

            log(f"-------------\n")

    def _stream_curriculum_learner(self):
        """
        Process curriculum tasks with prioritization and confidence-based correction.

        This stream:
        1. Gets the next highest-priority pending task
        2. Attempts it with the local MLX model
        3. Scores confidence based on response quality
        4. If confidence < 0.7, generates correction examples
        5. Captures learning as training data
        """
        global running

        log("[Curriculum] Starting prioritized learning stream...")
        log(f"[Curriculum] Database: {CURRICULUM_DB_PATH}")

        # Wait for other streams to initialize
        time.sleep(10)

        while running:
            try:
                # Check for pending tasks
                task = self.curriculum.get_next_task()

                if not task:
                    # No pending tasks - sleep longer
                    for _ in range(1800):  # 30 min
                        if not running:
                            break
                        time.sleep(1)
                    continue

                log(f"[Curriculum] Processing: {task['instruction'][:60]}...")

                # Attempt with local MLX model via SAM API
                sam_attempt, confidence = self._curriculum_attempt(task['instruction'])

                # Mark as attempted
                self.curriculum.mark_attempted(task['id'], sam_attempt, confidence)
                log(f"[Curriculum] Attempt confidence: {confidence:.2f}")

                # If low confidence, this is a learning opportunity
                if confidence < 0.7:
                    # Try to get a better answer (could use Claude API or other sources)
                    verified = self._curriculum_get_verified_answer(task, sam_attempt)

                    if verified:
                        # Capture the learning with correction example
                        task['sam_confidence'] = confidence
                        self.curriculum.capture_learning(task, sam_attempt, verified)
                        self.stats['curriculum_learned'] += 1
                        self.examples_since_train += 1
                else:
                    # High confidence - still capture but no correction needed
                    task['sam_confidence'] = confidence
                    self.curriculum.capture_learning(task, sam_attempt, sam_attempt)
                    self.stats['curriculum_confident'] += 1
                    self.examples_since_train += 1

                # Pause between tasks to avoid overwhelming the system
                for _ in range(60):  # 1 minute between tasks
                    if not running:
                        break
                    time.sleep(1)

            except Exception as e:
                log(f"[Curriculum] Error: {e}")
                time.sleep(60)

    def _curriculum_attempt(self, instruction: str) -> Tuple[str, float]:
        """Attempt a curriculum task with local MLX model."""
        try:
            import requests

            # Use SAM API if running
            response = requests.post(
                "http://localhost:8765/api/chat",
                json={"message": instruction, "mode": "default"},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "")
                confidence = self.curriculum.estimate_confidence(answer)
                return answer, confidence

        except Exception as e:
            log(f"[Curriculum] SAM API unavailable: {e}")

        # Fallback: mark as very low confidence
        return f"[SAM attempt pending - API not available]", 0.1

    def _curriculum_get_verified_answer(self, task: Dict, sam_attempt: str) -> Optional[str]:
        """
        Get a verified/improved answer for a low-confidence attempt.

        This could be expanded to use:
        - Claude API (when available)
        - Documentation lookup
        - Code search
        - etc.

        For now, returns None to indicate manual verification needed.
        """
        # Check if we have anthropic package and API key
        try:
            import anthropic
            import os

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                # Try common key file locations
                for keyfile in [Path.home() / ".anthropic_key", Path.home() / ".config/anthropic/key"]:
                    if keyfile.exists():
                        api_key = keyfile.read_text().strip()
                        break

            if not api_key:
                return None

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""I'm training a local AI assistant called SAM. SAM attempted to answer this task:

TASK: {task['instruction']}

SAM'S ATTEMPT:
{sam_attempt}

Please provide:
1. A thorough, correct answer to the task
2. Key patterns or principles to remember

Be detailed and educational - SAM will learn from your response."""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except ImportError:
            return None
        except Exception as e:
            log(f"[Curriculum] Verification error: {e}")
            return None

    def add_curriculum_task(self, instruction: str, task_type: str = "coding",
                           priority: int = TaskPriority.MEDIUM.value,
                           expected_skills: List[str] = None) -> Optional[str]:
        """
        Convenience method to add a curriculum task from external callers.

        Example:
            learner = PerpetualLearner()
            learner.add_curriculum_task(
                "Explain SwiftUI @State vs @Binding",
                task_type="coding",
                priority=TaskPriority.HIGH.value,
                expected_skills=["swift", "swiftui"]
            )
        """
        return self.curriculum.add_task(
            instruction=instruction,
            task_type=task_type,
            priority=priority,
            expected_skills=expected_skills or []
        )


def main():
    global running

    def signal_handler(sig, frame):
        global running
        running = False
        print("\nStopping...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    learner = PerpetualLearner()
    learner.run_forever()


if __name__ == "__main__":
    main()
