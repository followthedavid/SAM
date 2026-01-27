#!/usr/bin/env python3
"""
SAM Auto-Learner - Automatically learns from every Claude Code session

This daemon:
1. Watches ~/.claude/ for new conversation data
2. Extracts training pairs from Claude's responses
3. Accumulates examples in a training queue
4. Automatically triggers fine-tuning when threshold is met
5. No manual intervention required

Run as: python auto_learner.py daemon
Or add to launchd for always-on learning.
"""

import os
import sys
import json
import time
import signal
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import sqlite3

# Paths
CLAUDE_DIR = Path.home() / ".claude"
BRAIN_DIR = Path(__file__).parent
TRAINING_DB = BRAIN_DIR / "auto_learning.db"
ADAPTER_PATH = BRAIN_DIR / "models" / "auto_trained" / "adapters"
LOG_FILE = BRAIN_DIR / "auto_learner.log"

# Thresholds
MIN_EXAMPLES_FOR_TRAINING = 100
TRAINING_COOLDOWN_HOURS = 24
MIN_RESPONSE_LENGTH = 100
MIN_QUALITY_SCORE = 0.5


@dataclass
class TrainingExample:
    """A training example extracted from Claude."""
    id: str
    user_input: str
    claude_response: str
    category: str
    quality_score: float
    source_file: str
    extracted_at: str
    used_in_training: bool = False


class AutoLearningDB:
    """SQLite database for tracking learning progress."""

    def __init__(self, db_path: Path = TRAINING_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
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
        conn.execute("""
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                file_path TEXT PRIMARY KEY,
                processed_at TEXT,
                examples_extracted INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def add_example(self, example: TrainingExample) -> bool:
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

    def get_unused_examples(self, limit: int = None) -> List[TrainingExample]:
        """Get examples not yet used in training."""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM examples WHERE used_in_training = 0 ORDER BY quality_score DESC"
        if limit:
            query += f" LIMIT {limit}"

        rows = conn.execute(query).fetchall()
        conn.close()

        return [TrainingExample(
            id=r[0], user_input=r[1], claude_response=r[2],
            category=r[3], quality_score=r[4], source_file=r[5],
            extracted_at=r[6], used_in_training=bool(r[7])
        ) for r in rows]

    def mark_examples_used(self, example_ids: List[str]):
        """Mark examples as used in training."""
        conn = sqlite3.connect(self.db_path)
        conn.executemany(
            "UPDATE examples SET used_in_training = 1 WHERE id = ?",
            [(id,) for id in example_ids]
        )
        conn.commit()
        conn.close()

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

    def get_stats(self) -> Dict:
        """Get learning statistics."""
        conn = sqlite3.connect(self.db_path)

        total = conn.execute("SELECT COUNT(*) FROM examples").fetchone()[0]
        unused = conn.execute("SELECT COUNT(*) FROM examples WHERE used_in_training = 0").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM training_runs WHERE status = 'completed'").fetchone()[0]

        last_run = conn.execute(
            "SELECT completed_at FROM training_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()

        conn.close()

        return {
            "total_examples": total,
            "unused_examples": unused,
            "training_runs": runs,
            "last_training": last_run[0] if last_run else None,
            "ready_for_training": unused >= MIN_EXAMPLES_FOR_TRAINING,
        }

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


class ClaudeSessionExtractor:
    """Extract training data from Claude Code sessions."""

    def __init__(self):
        self.db = AutoLearningDB()

    def find_session_files(self) -> List[Path]:
        """Find all Claude session files."""
        files = []

        # Main history file - THIS IS THE KEY ONE
        history_file = CLAUDE_DIR / "history.jsonl"
        if history_file.exists():
            files.append(history_file)

        # Check projects directory
        projects_dir = CLAUDE_DIR / "projects"
        if projects_dir.exists():
            # Look for conversation JSON files
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for f in project.glob("**/*.json"):
                        files.append(f)

        # Check for other JSONL conversation logs
        for f in CLAUDE_DIR.glob("*.jsonl"):
            if f.name != "history.jsonl":  # Already added
                files.append(f)

        # Filter to unprocessed - but always reprocess history.jsonl
        # since it grows over time
        return [f for f in files if f.name == "history.jsonl" or
                not self.db.is_file_processed(str(f))]

    def extract_from_file(self, file_path: Path) -> List[TrainingExample]:
        """Extract training examples from a session file."""
        examples = []

        try:
            if file_path.suffix == '.jsonl':
                examples = self._extract_from_jsonl(file_path)
            else:
                examples = self._extract_from_json(file_path)
        except Exception as e:
            self._log(f"Error extracting from {file_path}: {e}")

        return examples

    def _extract_from_jsonl(self, file_path: Path) -> List[TrainingExample]:
        """Extract from JSONL format."""
        examples = []

        # Special handling for Claude Code history.jsonl
        if file_path.name == "history.jsonl":
            return self._extract_from_claude_history(file_path)

        current_user_msg = None

        for line in open(file_path):
            try:
                msg = json.loads(line)
                role = msg.get("role", "")
                content = self._get_content(msg)

                if role == "user":
                    current_user_msg = content
                elif role == "assistant" and current_user_msg:
                    example = self._create_example(
                        current_user_msg, content, str(file_path)
                    )
                    if example:
                        examples.append(example)
                    current_user_msg = None
            except:
                continue

        return examples

    def _extract_from_claude_history(self, file_path: Path) -> List[TrainingExample]:
        """Extract from Claude Code history.jsonl format.

        The format alternates: user message, assistant message, user, assistant...
        Each entry has a "display" field with the content.
        """
        examples = []
        messages = []

        # Read all messages
        for line in open(file_path, errors='replace'):
            try:
                msg = json.loads(line)
                content = msg.get("display", "")
                session_id = msg.get("sessionId", "")
                timestamp = msg.get("timestamp", 0)

                if content:
                    messages.append({
                        "content": content,
                        "session_id": session_id,
                        "timestamp": timestamp,
                    })
            except:
                continue

        # Group by session and pair up messages
        # Messages alternate: user, assistant, user, assistant
        sessions = {}
        for msg in messages:
            sid = msg["session_id"]
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(msg)

        # Extract pairs from each session
        processed_hashes = set()

        for session_id, session_msgs in sessions.items():
            # Sort by timestamp within session
            session_msgs.sort(key=lambda x: x["timestamp"])

            # Pair up: assume alternating user/assistant
            for i in range(0, len(session_msgs) - 1, 2):
                user_content = session_msgs[i]["content"]
                assistant_content = session_msgs[i + 1]["content"]

                # Heuristic: user messages are usually shorter or questions
                # If assistant msg looks like a user msg, swap
                if len(assistant_content) < len(user_content) / 3:
                    user_content, assistant_content = assistant_content, user_content

                # Create hash to avoid duplicates
                pair_hash = hashlib.md5(
                    f"{user_content[:100]}{assistant_content[:100]}".encode()
                ).hexdigest()

                if pair_hash in processed_hashes:
                    continue
                processed_hashes.add(pair_hash)

                example = self._create_example(
                    user_content, assistant_content, str(file_path)
                )
                if example:
                    examples.append(example)

        return examples

    def _extract_from_json(self, file_path: Path) -> List[TrainingExample]:
        """Extract from JSON format."""
        examples = []

        try:
            data = json.load(open(file_path))
        except:
            return []

        # Handle different formats
        messages = data.get("messages", [])
        if not messages and "conversation" in data:
            messages = data["conversation"]
        if not messages and "mapping" in data:
            # ChatGPT format
            messages = self._flatten_mapping(data["mapping"])

        current_user_msg = None

        for msg in messages:
            role = msg.get("role", msg.get("author", {}).get("role", ""))
            content = self._get_content(msg)

            if role in ["user", "human"]:
                current_user_msg = content
            elif role in ["assistant", "ai"] and current_user_msg:
                example = self._create_example(
                    current_user_msg, content, str(file_path)
                )
                if example:
                    examples.append(example)
                current_user_msg = None

        return examples

    def _flatten_mapping(self, mapping: Dict) -> List[Dict]:
        """Flatten ChatGPT mapping format to messages."""
        messages = []
        for node in mapping.values():
            msg = node.get("message")
            if msg:
                messages.append(msg)
        return sorted(messages, key=lambda x: x.get("create_time", 0))

    def _get_content(self, msg: Dict) -> str:
        """Extract text content from a message."""
        content = msg.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            parts = content.get("parts", [])
            if parts:
                return parts[0] if isinstance(parts[0], str) else str(parts[0])

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            return "\n".join(text_parts)

        return str(content)

    def _create_example(self, user_input: str, response: str,
                       source: str) -> Optional[TrainingExample]:
        """Create a training example if quality is sufficient."""

        # Skip short exchanges
        if len(user_input) < 10 or len(response) < MIN_RESPONSE_LENGTH:
            return None

        # Skip refusals
        refusal_indicators = ["I can't", "I cannot", "I'm sorry, but", "I won't"]
        if any(ind in response for ind in refusal_indicators):
            return None

        # Calculate quality score
        quality = self._calculate_quality(user_input, response)
        if quality < MIN_QUALITY_SCORE:
            return None

        # Categorize
        category = self._categorize(user_input, response)

        # Create unique ID
        example_id = hashlib.md5(
            f"{user_input[:100]}{response[:100]}".encode()
        ).hexdigest()

        return TrainingExample(
            id=example_id,
            user_input=user_input[:4000],
            claude_response=response[:8000],
            category=category,
            quality_score=quality,
            source_file=source,
            extracted_at=datetime.now().isoformat(),
        )

    def _calculate_quality(self, user_input: str, response: str) -> float:
        """Calculate quality score for a training example."""
        score = 0.5

        # Length bonus
        if len(response) > 200: score += 0.1
        if len(response) > 500: score += 0.1
        if len(response) > 1000: score += 0.05

        # Code bonus
        if "```" in response: score += 0.15

        # Structure bonus
        import re
        if re.search(r'\d+\.\s', response): score += 0.1  # Numbered list
        if re.search(r'^#+\s', response, re.MULTILINE): score += 0.05  # Headers

        # Reasoning indicators
        reasoning = ["because", "therefore", "since", "thus", "this means"]
        if any(w in response.lower() for w in reasoning): score += 0.1

        # Penalty for very short prompts (might be ambiguous)
        if len(user_input) < 20: score -= 0.1

        return min(max(score, 0.0), 1.0)

    def _categorize(self, user_input: str, response: str) -> str:
        """Categorize the training example."""
        user_lower = user_input.lower()

        if "```" in response:
            if any(kw in user_lower for kw in ["write", "create", "implement", "code"]):
                return "code_generation"
            if any(kw in user_lower for kw in ["fix", "error", "bug", "debug"]):
                return "debugging"
            return "code_general"

        if any(kw in user_lower for kw in ["explain", "what", "how", "why"]):
            return "explanation"

        if any(kw in user_lower for kw in ["plan", "steps", "approach"]):
            return "planning"

        return "general"

    def _log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
        print(log_line.strip())


class AutoTrainer:
    """Automatically triggers training when ready."""

    def __init__(self):
        self.db = AutoLearningDB()
        self.training_lock = threading.Lock()
        self.is_training = False

    def should_train(self) -> bool:
        """Check if we should trigger training."""
        stats = self.db.get_stats()

        if stats["unused_examples"] < MIN_EXAMPLES_FOR_TRAINING:
            return False

        # Check cooldown
        if stats["last_training"]:
            last = datetime.fromisoformat(stats["last_training"])
            if datetime.now() - last < timedelta(hours=TRAINING_COOLDOWN_HOURS):
                return False

        return True

    def trigger_training(self) -> bool:
        """Trigger a training run."""
        if not self.training_lock.acquire(blocking=False):
            return False

        try:
            self.is_training = True
            return self._run_training()
        finally:
            self.is_training = False
            self.training_lock.release()

    def _run_training(self) -> bool:
        """Run the actual training."""
        self._log("Starting automatic training run...")

        # Get unused examples
        examples = self.db.get_unused_examples()
        if len(examples) < MIN_EXAMPLES_FOR_TRAINING:
            self._log(f"Not enough examples: {len(examples)}/{MIN_EXAMPLES_FOR_TRAINING}")
            return False

        # Prepare training data
        train_dir = BRAIN_DIR / "auto_training_data"
        train_dir.mkdir(exist_ok=True)

        # Shuffle and split
        import random
        random.shuffle(examples)
        split = int(len(examples) * 0.9)
        train_examples = examples[:split]
        val_examples = examples[split:]

        # Write training files
        with open(train_dir / "train.jsonl", "w") as f:
            for ex in train_examples:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex.user_input},
                        {"role": "assistant", "content": ex.claude_response},
                    ]
                }) + "\n")

        with open(train_dir / "valid.jsonl", "w") as f:
            for ex in val_examples:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex.user_input},
                        {"role": "assistant", "content": ex.claude_response},
                    ]
                }) + "\n")

        self._log(f"Prepared {len(train_examples)} train, {len(val_examples)} val examples")

        # Run training
        ADAPTER_PATH.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "mlx_lm.lora",
            "--model", "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
            "--data", str(train_dir),
            "--train",
            "--batch-size", "1",
            "--num-layers", "4",
            "--iters", "300",
            "--max-seq-length", "1024",
            "--grad-checkpoint",
            "--adapter-path", str(ADAPTER_PATH),
        ]

        self._log(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BRAIN_DIR,
            timeout=3600,  # 1 hour max
        )

        if result.returncode == 0:
            # Mark examples as used
            self.db.mark_examples_used([ex.id for ex in examples])

            # Record training run
            self.db.record_training_run(
                examples_used=len(examples),
                initial_loss=0.0,  # Would need to parse from output
                final_loss=0.0,
                adapter_path=str(ADAPTER_PATH),
                status="completed"
            )

            # Update latest symlink
            latest_link = BRAIN_DIR / "models" / "latest"
            latest_link.unlink(missing_ok=True)
            latest_link.symlink_to("auto_trained")

            self._log("Training completed successfully!")
            return True
        else:
            self._log(f"Training failed: {result.stderr}")
            self.db.record_training_run(
                examples_used=len(examples),
                initial_loss=0.0,
                final_loss=0.0,
                adapter_path=str(ADAPTER_PATH),
                status="failed"
            )
            return False

    def _log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [TRAINER] {message}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
        print(log_line.strip())


class ClaudeWatcher(FileSystemEventHandler):
    """Watch for new Claude session files."""

    def __init__(self, extractor: ClaudeSessionExtractor, trainer: AutoTrainer):
        self.extractor = extractor
        self.trainer = trainer
        self.db = AutoLearningDB()
        self.pending_files: Set[Path] = set()
        self.process_lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        self._queue_file(Path(event.src_path))

    def on_created(self, event):
        if event.is_directory:
            return
        self._queue_file(Path(event.src_path))

    def _queue_file(self, file_path: Path):
        """Queue a file for processing."""
        if file_path.suffix in ['.json', '.jsonl']:
            self.pending_files.add(file_path)

    def process_pending(self):
        """Process pending files."""
        with self.process_lock:
            files_to_process = list(self.pending_files)
            self.pending_files.clear()

        total_new = 0

        for file_path in files_to_process:
            if not file_path.exists():
                continue

            if self.db.is_file_processed(str(file_path)):
                continue

            # Wait a bit for file to be fully written
            time.sleep(1)

            examples = self.extractor.extract_from_file(file_path)

            new_count = 0
            for ex in examples:
                if self.db.add_example(ex):
                    new_count += 1

            self.db.mark_file_processed(str(file_path), len(examples))

            if new_count > 0:
                self._log(f"Extracted {new_count} new examples from {file_path.name}")
                total_new += new_count

        # Check if we should train
        if total_new > 0 and self.trainer.should_train():
            self._log("Training threshold reached, starting automatic training...")
            threading.Thread(target=self.trainer.trigger_training).start()

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [WATCHER] {message}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
        print(log_line.strip())


class AutoLearnerDaemon:
    """Main daemon that runs continuously."""

    def __init__(self):
        self.extractor = ClaudeSessionExtractor()
        self.trainer = AutoTrainer()
        self.db = AutoLearningDB()
        self.running = False
        self.observer = None

    def start(self):
        """Start the daemon."""
        self._log("SAM Auto-Learner starting...")
        self.running = True

        # Initial scan
        self._log("Performing initial scan of existing sessions...")
        self._initial_scan()

        # Set up file watcher
        watcher = ClaudeWatcher(self.extractor, self.trainer)
        self.observer = Observer()
        self.observer.schedule(watcher, str(CLAUDE_DIR), recursive=True)
        self.observer.start()

        self._log(f"Watching {CLAUDE_DIR} for new sessions...")
        self._log(f"Training threshold: {MIN_EXAMPLES_FOR_TRAINING} examples")

        # Main loop
        try:
            while self.running:
                watcher.process_pending()

                # Periodic stats
                stats = self.db.get_stats()
                self._log(
                    f"Stats: {stats['unused_examples']} pending examples, "
                    f"{stats['training_runs']} training runs"
                )

                # Check if should train
                if self.trainer.should_train() and not self.trainer.is_training:
                    self._log("Training threshold reached!")
                    threading.Thread(target=self.trainer.trigger_training).start()

                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self._log("Shutting down...")
        finally:
            self.observer.stop()
            self.observer.join()
            self._log("SAM Auto-Learner stopped")

    def _initial_scan(self):
        """Scan existing session files."""
        files = self.extractor.find_session_files()
        self._log(f"Found {len(files)} unprocessed session files")

        total_new = 0
        for f in files:
            examples = self.extractor.extract_from_file(f)

            new_count = 0
            for ex in examples:
                if self.db.add_example(ex):
                    new_count += 1

            self.db.mark_file_processed(str(f), len(examples))
            total_new += new_count

        self._log(f"Extracted {total_new} new training examples from existing sessions")

    def stop(self):
        """Stop the daemon."""
        self.running = False

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [DAEMON] {message}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
        print(log_line.strip())


def create_launchd_plist():
    """Create a launchd plist for auto-starting the daemon."""
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sam.autolearner</string>

    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{BRAIN_DIR / 'auto_learner.py'}</string>
        <string>daemon</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{BRAIN_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{BRAIN_DIR / 'auto_learner_stdout.log'}</string>

    <key>StandardErrorPath</key>
    <string>{BRAIN_DIR / 'auto_learner_stderr.log'}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
"""

    plist_path = Path.home() / "Library/LaunchAgents/com.sam.autolearner.plist"
    plist_path.write_text(plist_content)

    print(f"Created: {plist_path}")
    print()
    print("To enable auto-start on login:")
    print(f"  launchctl load {plist_path}")
    print()
    print("To disable:")
    print(f"  launchctl unload {plist_path}")

    return plist_path


def main():
    if len(sys.argv) < 2:
        print("SAM Auto-Learner")
        print("=" * 60)
        print()
        print("Commands:")
        print("  daemon     - Run the auto-learning daemon")
        print("  stats      - Show learning statistics")
        print("  scan       - Scan for new sessions now")
        print("  train      - Force training now")
        print("  install    - Install as launchd service (auto-start)")
        print("  uninstall  - Remove launchd service")
        print()

        db = AutoLearningDB()
        stats = db.get_stats()
        print("Current Status:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    cmd = sys.argv[1]

    if cmd == "daemon":
        daemon = AutoLearnerDaemon()
        daemon.start()

    elif cmd == "stats":
        db = AutoLearningDB()
        stats = db.get_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "scan":
        extractor = ClaudeSessionExtractor()
        db = AutoLearningDB()

        files = extractor.find_session_files()
        print(f"Found {len(files)} unprocessed files")

        total = 0
        for f in files:
            examples = extractor.extract_from_file(f)
            for ex in examples:
                if db.add_example(ex):
                    total += 1
            db.mark_file_processed(str(f), len(examples))

        print(f"Extracted {total} new examples")

    elif cmd == "train":
        trainer = AutoTrainer()
        trainer.trigger_training()

    elif cmd == "install":
        plist_path = create_launchd_plist()
        subprocess.run(["launchctl", "load", str(plist_path)])
        print("Auto-learner installed and started!")

    elif cmd == "uninstall":
        plist_path = Path.home() / "Library/LaunchAgents/com.sam.autolearner.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)])
            plist_path.unlink()
            print("Auto-learner uninstalled")
        else:
            print("Not installed")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
