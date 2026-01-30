"""
Unified Training Scheduler
==========================
Resource-aware training scheduler that merges logic from both
perpetual_learner.py (_training_scheduler + _run_training) and
auto_learner.py (AutoTrainer).

Uses perpetual_learner thresholds as defaults:
- 500 examples or 6 hours between training runs
- Minimum 100 examples to train
- System resource gating via cognitive.resource_manager
"""

import sys
import json
import hashlib
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple

from cognitive.resource_manager import can_train as system_can_train

# Paths
BRAIN_PATH = Path(__file__).parent.parent
DATA_PATH = BRAIN_PATH / "data"
MODELS_PATH = BRAIN_PATH / "models"


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)


class TrainingScheduler:
    """
    Unified training scheduler combining perpetual_learner and auto_learner logic.

    Checks:
    - Example count threshold (default: 500)
    - Time threshold (default: 6 hours)
    - Minimum examples to train (default: 100)
    - System resources via system_can_train()

    Runs MLX LoRA training and records results in database.
    """

    def __init__(self, db,
                 train_every_n_examples: int = 500,
                 train_every_n_hours: int = 6,
                 min_examples_to_train: int = 100):
        """
        Args:
            db: A LearningDatabase instance
            train_every_n_examples: Trigger training after this many new examples
            train_every_n_hours: Trigger training after this many hours
            min_examples_to_train: Minimum examples required to start training
        """
        self.db = db
        self.TRAIN_EVERY_N_EXAMPLES = train_every_n_examples
        self.TRAIN_EVERY_N_HOURS = train_every_n_hours
        self.MIN_EXAMPLES_TO_TRAIN = min_examples_to_train

        self.training_lock = threading.Lock()
        self.is_training = False

        # Track examples since last training
        self.examples_since_train = 0
        self.last_train = self.db.get_last_training_time() or datetime(2000, 1, 1)

    def should_train(self) -> Tuple[bool, str]:
        """
        Check if training should be triggered.

        Returns (should_train, reason) tuple.
        """
        should = False
        reason = ""

        # Check example threshold
        unused_count = self.db.get_example_count(unused_only=True)
        if unused_count >= self.TRAIN_EVERY_N_EXAMPLES:
            should = True
            reason = f"{unused_count} unused examples"

        # Check time threshold
        hours_since = (datetime.now() - self.last_train).total_seconds() / 3600
        if hours_since >= self.TRAIN_EVERY_N_HOURS and unused_count >= self.MIN_EXAMPLES_TO_TRAIN:
            should = True
            reason = f"{hours_since:.1f} hours since last train, {unused_count} examples"

        if not should:
            return False, f"Not ready: {unused_count} examples, {hours_since:.1f}h since last"

        # Check system resources
        can_train, resource_msg = system_can_train()
        if not can_train:
            return False, f"DEFERRED: {reason} | {resource_msg}"

        return True, reason

    def trigger_training(self) -> bool:
        """Trigger a training run if not already running."""
        if not self.training_lock.acquire(blocking=False):
            log("[Training] Already running, skipping")
            return False

        try:
            self.is_training = True
            return self._run_training()
        finally:
            self.is_training = False
            self.training_lock.release()

    def _run_training(self) -> bool:
        """Execute training with accumulated data."""
        # Final resource check right before training
        can_train, msg = system_can_train()
        if not can_train:
            log(f"[Training] Aborted at launch: {msg}")
            return False

        try:
            # Get unused examples from database
            examples = self.db.get_unused_examples()
            if len(examples) < self.MIN_EXAMPLES_TO_TRAIN:
                log(f"[Training] Only {len(examples)} examples, need {self.MIN_EXAMPLES_TO_TRAIN}")
                return False

            log(f"[Training] Preparing {len(examples)} examples...")

            # Also merge perpetual data files if they exist
            merged_count = self._merge_perpetual_data()

            # Create train/valid split in MLX chat format
            import random
            random.shuffle(examples)
            split = int(len(examples) * 0.9)
            train_examples = examples[:split]
            val_examples = examples[split:]

            # Write training files
            DATA_PATH.mkdir(parents=True, exist_ok=True)

            with open(DATA_PATH / "train.jsonl", 'w') as f:
                for ex in train_examples:
                    f.write(json.dumps({
                        "messages": [
                            {"role": "user", "content": ex.user_input[:1500]},
                            {"role": "assistant", "content": ex.claude_response[:2000]},
                        ]
                    }) + "\n")

            with open(DATA_PATH / "valid.jsonl", 'w') as f:
                for ex in val_examples:
                    f.write(json.dumps({
                        "messages": [
                            {"role": "user", "content": ex.user_input[:1500]},
                            {"role": "assistant", "content": ex.claude_response[:2000]},
                        ]
                    }) + "\n")

            total_count = len(examples) + merged_count
            log(f"[Training] {len(train_examples)} train, {len(val_examples)} val (+{merged_count} perpetual)")

            # Run MLX LoRA training
            adapter_path = MODELS_PATH / "unified_trained" / "adapters"
            adapter_path.parent.mkdir(parents=True, exist_ok=True)

            iters = min(150, total_count // 10)
            log(f"[Training] Starting MLX LoRA training ({iters} iterations)...")

            result = subprocess.run([
                sys.executable, "-m", "mlx_lm.lora",
                "--model", "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
                "--train",
                "--data", str(DATA_PATH),
                "--adapter-path", str(adapter_path),
                "--iters", str(iters),
                "--batch-size", "1",
                "--num-layers", "4",
                "--max-seq-length", "1024",
                "--grad-checkpoint",
                "--save-every", "50"
            ], capture_output=True, text=True, cwd=BRAIN_PATH, timeout=3600)

            if result.returncode == 0:
                log("[Training] Complete!")
                self.last_train = datetime.now()
                self.examples_since_train = 0

                # Mark examples as used
                self.db.mark_examples_used([ex.id for ex in examples])

                # Record training run
                self.db.record_training_run(
                    examples_used=len(examples),
                    initial_loss=0.0,
                    final_loss=0.0,
                    adapter_path=str(adapter_path),
                    status="completed"
                )

                # Update latest symlink
                latest_link = MODELS_PATH / "latest"
                latest_link.unlink(missing_ok=True)
                latest_link.symlink_to("unified_trained")

                return True
            else:
                log(f"[Training] Failed: {result.stderr[:500]}")
                self.db.record_training_run(
                    examples_used=len(examples),
                    initial_loss=0.0,
                    final_loss=0.0,
                    adapter_path=str(adapter_path),
                    status="failed"
                )
                return False

        except subprocess.TimeoutExpired:
            log("[Training] Timed out after 1 hour")
            return False
        except Exception as e:
            log(f"[Training] Error: {e}")
            return False

    def _merge_perpetual_data(self) -> int:
        """Merge perpetual learning data files into training data. Returns count merged."""
        count = 0
        seen = set()

        # Check for perpetual data files
        perpetual_files = list(DATA_PATH.glob("perpetual_*.jsonl"))
        if not perpetual_files:
            return 0

        merged_path = DATA_PATH / "perpetual_merged.jsonl"
        with open(merged_path, 'w') as out:
            for stream_file in perpetual_files:
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

        if count > 0:
            # Append merged perpetual data to train.jsonl
            train_file = DATA_PATH / "train.jsonl"
            with open(train_file, 'a') as out:
                try:
                    with open(merged_path) as f:
                        for line in f:
                            d = json.loads(line)
                            example = {
                                "messages": [
                                    {"role": "user", "content": d.get("instruction", "")[:1500]},
                                    {"role": "assistant", "content": d.get("response", "")[:2000]}
                                ]
                            }
                            out.write(json.dumps(example) + '\n')
                except:
                    pass

        return count
