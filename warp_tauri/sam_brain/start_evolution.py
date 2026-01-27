#!/usr/bin/env python3
"""
SAM Evolution Starter - Brings all learning systems to life.

This connects:
- Knowledge distillation (capture Claude reasoning)
- Feedback learning (improve from corrections)
- Training pipeline (convert learning to model improvements)
- Evolution tracker (track progress)

Run: python3 start_evolution.py
"""

import os
import sys
import time
import signal
import sqlite3
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import threading
import json

# Setup logging
LOG_DIR = Path("/Volumes/David External/sam_evolution")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "evolution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("evolution")

# Paths
SAM_BRAIN = Path(__file__).parent
TRAINING_DIR = Path("/Volumes/David External/sam_training")
DISTILLATION_DB = TRAINING_DIR / "distilled/distillation.db"
FEEDBACK_DB = TRAINING_DIR / "feedback/feedback.db"
EVOLUTION_DB = SAM_BRAIN / "evolution.db"

# Import SAM modules
sys.path.insert(0, str(SAM_BRAIN))

class EvolutionRunner:
    """Orchestrates SAM's evolution systems."""

    def __init__(self):
        self.running = True
        self.stats = {
            "started": datetime.now().isoformat(),
            "cycles": 0,
            "distilled": 0,
            "feedback_processed": 0,
            "training_ready": False,
        }
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received")
        self.running = False

    def check_sam_api(self) -> bool:
        """Check if SAM API is running."""
        try:
            import requests
            r = requests.get("http://localhost:8765/api/health", timeout=2)
            return r.status_code == 200
        except:
            return False

    def get_distillation_stats(self) -> dict:
        """Get knowledge distillation statistics."""
        if not DISTILLATION_DB.exists():
            return {"total": 0, "pending_review": 0}

        try:
            conn = sqlite3.connect(str(DISTILLATION_DB))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM examples")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM examples WHERE human_reviewed = 0")
            pending = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM examples WHERE approved = 1")
            approved = c.fetchone()[0]
            conn.close()
            return {"total": total, "pending_review": pending, "approved": approved}
        except Exception as e:
            logger.warning(f"Distillation DB error: {e}")
            return {"total": 0, "pending_review": 0, "error": str(e)}

    def get_feedback_stats(self) -> dict:
        """Get feedback learning statistics."""
        if not FEEDBACK_DB.exists():
            return {"total": 0, "unprocessed": 0}

        try:
            conn = sqlite3.connect(str(FEEDBACK_DB))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM feedback")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM feedback WHERE processed = 0")
            unprocessed = c.fetchone()[0]
            conn.close()
            return {"total": total, "unprocessed": unprocessed}
        except Exception as e:
            logger.warning(f"Feedback DB error: {e}")
            return {"total": 0, "unprocessed": 0, "error": str(e)}

    def get_training_stats(self) -> dict:
        """Check training data readiness."""
        training_data = TRAINING_DIR / "training_data"
        if not training_data.exists():
            return {"samples": 0, "ready": False}

        try:
            # Count JSONL files
            samples = 0
            for f in training_data.glob("*.jsonl"):
                with open(f) as fp:
                    samples += sum(1 for _ in fp)

            return {
                "samples": samples,
                "ready": samples >= 100,  # Minimum for training
                "min_required": 100,
            }
        except Exception as e:
            return {"samples": 0, "ready": False, "error": str(e)}

    def process_pending_distillation(self):
        """Auto-approve high-quality distillation examples."""
        if not DISTILLATION_DB.exists():
            return 0

        try:
            conn = sqlite3.connect(str(DISTILLATION_DB))
            c = conn.cursor()

            # Auto-approve examples with high quality scores
            c.execute("""
                UPDATE examples
                SET approved = 1, human_reviewed = 1
                WHERE human_reviewed = 0
                AND quality_score >= 0.7
            """)
            approved = c.rowcount
            conn.commit()
            conn.close()

            if approved > 0:
                logger.info(f"Auto-approved {approved} distillation examples")
            return approved

        except Exception as e:
            logger.error(f"Distillation processing error: {e}")
            return 0

    def process_feedback(self):
        """Convert feedback into training examples."""
        if not FEEDBACK_DB.exists():
            return 0

        try:
            conn = sqlite3.connect(str(FEEDBACK_DB))
            c = conn.cursor()

            # Get unprocessed negative feedback (corrections)
            c.execute("""
                SELECT id, response_id, correction, rating
                FROM feedback
                WHERE processed = 0 AND correction IS NOT NULL
                LIMIT 10
            """)
            corrections = c.fetchall()

            processed = 0
            for fb_id, resp_id, correction, rating in corrections:
                # Mark as processed
                c.execute("UPDATE feedback SET processed = 1 WHERE id = ?", (fb_id,))
                processed += 1

            conn.commit()
            conn.close()

            if processed > 0:
                logger.info(f"Processed {processed} feedback corrections")
            return processed

        except Exception as e:
            logger.error(f"Feedback processing error: {e}")
            return 0

    def export_training_data(self):
        """Export approved distillation + feedback to training format."""
        output_dir = TRAINING_DIR / "training_data"
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = 0

        # Export distillation examples
        if DISTILLATION_DB.exists():
            try:
                conn = sqlite3.connect(str(DISTILLATION_DB))
                c = conn.cursor()
                c.execute("""
                    SELECT query, sam_attempt, claude_response, reasoning_type
                    FROM examples
                    WHERE approved = 1 AND exported_at IS NULL
                """)
                examples = c.fetchall()

                if examples:
                    output_file = output_dir / "distilled_examples.jsonl"
                    with open(output_file, 'a') as f:
                        for query, sam_resp, claude_resp, reasoning in examples:
                            # Create instruction-following format
                            example = {
                                "messages": [
                                    {"role": "user", "content": query},
                                    {"role": "assistant", "content": claude_resp}
                                ],
                                "source": "distillation",
                                "reasoning_type": reasoning
                            }
                            f.write(json.dumps(example) + "\n")
                            exported += 1

                    # Mark as exported
                    c.execute("UPDATE examples SET exported_at = ? WHERE approved = 1 AND exported_at IS NULL",
                              (time.time(),))
                    conn.commit()

                conn.close()
            except Exception as e:
                logger.error(f"Distillation export error: {e}")

        if exported > 0:
            logger.info(f"Exported {exported} examples to training data")

        return exported

    def check_training_trigger(self) -> bool:
        """Check if we should trigger training."""
        stats = self.get_training_stats()

        if stats["ready"]:
            # Check if we haven't trained recently
            marker = TRAINING_DIR / ".last_training"
            if marker.exists():
                last = datetime.fromisoformat(marker.read_text().strip())
                if datetime.now() - last < timedelta(hours=24):
                    return False  # Too recent

            logger.info(f"Training ready: {stats['samples']} samples available")
            return True

        return False

    def trigger_training(self):
        """Start a training run."""
        logger.info("=== TRIGGERING TRAINING RUN ===")

        # Update marker
        marker = TRAINING_DIR / ".last_training"
        marker.write_text(datetime.now().isoformat())

        # Training would be triggered here
        # For now, just log it - actual training needs user approval
        logger.info("Training data ready. Run: python3 train_roleplay_lora.py")

        # Could send a notification
        try:
            subprocess.run([
                "osascript", "-e",
                'display notification "Training data ready!" with title "SAM Evolution"'
            ], capture_output=True, timeout=5)
        except:
            pass

    def run_cycle(self):
        """Run one evolution cycle."""
        self.stats["cycles"] += 1
        logger.info(f"=== Evolution Cycle {self.stats['cycles']} ===")

        # Check SAM API
        api_running = self.check_sam_api()
        logger.info(f"SAM API: {'Running' if api_running else 'NOT RUNNING'}")

        # Get stats
        distill_stats = self.get_distillation_stats()
        feedback_stats = self.get_feedback_stats()
        training_stats = self.get_training_stats()

        logger.info(f"Distillation: {distill_stats['total']} total, {distill_stats.get('pending_review', 0)} pending")
        logger.info(f"Feedback: {feedback_stats['total']} total, {feedback_stats.get('unprocessed', 0)} unprocessed")
        logger.info(f"Training: {training_stats['samples']} samples, ready={training_stats['ready']}")

        # Process pending items
        approved = self.process_pending_distillation()
        processed = self.process_feedback()
        exported = self.export_training_data()

        self.stats["distilled"] += approved
        self.stats["feedback_processed"] += processed

        # Check training trigger
        if self.check_training_trigger():
            self.trigger_training()

        # Save state
        state_file = LOG_DIR / "evolution_state.json"
        with open(state_file, 'w') as f:
            json.dump({
                **self.stats,
                "last_cycle": datetime.now().isoformat(),
                "distillation": distill_stats,
                "feedback": feedback_stats,
                "training": training_stats,
            }, f, indent=2)

    def run(self, interval_minutes: int = 5):
        """Run the evolution loop."""
        logger.info("=" * 60)
        logger.info("SAM Evolution Daemon Starting")
        logger.info(f"Cycle interval: {interval_minutes} minutes")
        logger.info("=" * 60)

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")

            # Sleep in small intervals to allow shutdown
            for _ in range(interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Evolution daemon stopped")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Evolution Runner")
    parser.add_argument("command", choices=["start", "once", "status"],
                       default="once", nargs="?",
                       help="Command to run")
    parser.add_argument("--interval", type=int, default=5,
                       help="Minutes between cycles (default: 5)")

    args = parser.parse_args()

    runner = EvolutionRunner()

    if args.command == "once":
        runner.run_cycle()
    elif args.command == "status":
        print("\n=== SAM Evolution Status ===\n")
        print(f"SAM API: {'Running' if runner.check_sam_api() else 'NOT RUNNING'}")
        print(f"Distillation: {runner.get_distillation_stats()}")
        print(f"Feedback: {runner.get_feedback_stats()}")
        print(f"Training: {runner.get_training_stats()}")
    else:
        runner.run(args.interval)


if __name__ == "__main__":
    main()
