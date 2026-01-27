#!/usr/bin/env python3
"""
Continuous Training Pipeline for SAM

Runs automatically to:
1. Process new scraped data into training format
2. Trigger fine-tuning when enough new data accumulates
3. Manage training data versions
4. Track training metrics

Can be run as a cron job or daemon.

Usage:
    # Run once
    python continuous_pipeline.py --process

    # Run as daemon (checks every hour)
    python continuous_pipeline.py --daemon

    # Process and trigger training if threshold met
    python continuous_pipeline.py --process --auto-train --threshold 1000
"""

import argparse
import json
import logging
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ContinuousPipeline:
    """
    Continuous pipeline for processing scraped data and triggering training.

    Features:
    - Incremental processing (only new items)
    - Training data versioning
    - Automatic training triggers
    - Quality filtering
    - Statistics tracking
    """

    # Paths
    DATA_DIR = Path("/Volumes/David External/scraper_data")
    TRAINING_DIR = DATA_DIR / "training_data"
    VERSIONS_DIR = DATA_DIR / "training_versions"
    METRICS_FILE = DATA_DIR / "pipeline_metrics.json"

    # Thresholds
    DEFAULT_TRAINING_THRESHOLD = 1000  # New examples before auto-training
    MIN_QUALITY_SCORE = 0.5

    def __init__(self):
        self.TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        self.VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

        self.metrics = self._load_metrics()
        self._db = None
        self._pipeline = None

    def _load_metrics(self) -> Dict:
        """Load pipeline metrics."""
        if self.METRICS_FILE.exists():
            with open(self.METRICS_FILE, 'r') as f:
                return json.load(f)
        return {
            "total_processed": 0,
            "total_examples": 0,
            "last_process_time": None,
            "last_training_time": None,
            "training_runs": 0,
            "versions": [],
        }

    def _save_metrics(self):
        """Save pipeline metrics."""
        with open(self.METRICS_FILE, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)

    def initialize(self):
        """Initialize database and pipeline connections."""
        from storage.database import get_database
        from core.training_pipeline import get_pipeline

        self._db = get_database()
        self._pipeline = get_pipeline(str(self.TRAINING_DIR))

        logger.info("Continuous pipeline initialized")

    def get_new_item_count(self) -> int:
        """Get count of unprocessed items."""
        try:
            with self._db.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM scraped_items WHERE processed = FALSE")
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get item count: {e}")
            return 0

    def process_new_items(self, batch_size: int = 500) -> Dict[str, Any]:
        """
        Process new scraped items into training format.

        Args:
            batch_size: Number of items to process per batch

        Returns:
            Processing statistics
        """
        logger.info("Processing new items...")

        # Process items
        stats = self._pipeline.process_all(limit=batch_size)

        # Update metrics
        self.metrics["total_processed"] += stats.total_items_processed
        self.metrics["total_examples"] += stats.examples_generated
        self.metrics["last_process_time"] = datetime.now().isoformat()

        self._save_metrics()

        logger.info(f"Processed {stats.total_items_processed} items → {stats.examples_generated} examples")

        return {
            "items_processed": stats.total_items_processed,
            "examples_generated": stats.examples_generated,
            "errors": stats.errors,
            "by_type": stats.by_type,
            "by_source": stats.by_source,
        }

    def create_training_version(self, min_quality: float = None) -> str:
        """
        Create a new versioned training dataset.

        Combines all examples and filters by quality.

        Returns:
            Path to the versioned dataset
        """
        if min_quality is None:
            min_quality = self.MIN_QUALITY_SCORE

        version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir = self.VERSIONS_DIR / version_id
        version_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating training version {version_id}")

        # Collect all examples from existing training files
        all_examples = []

        for jsonl_file in self.TRAINING_DIR.glob("*.jsonl"):
            with open(jsonl_file, 'r') as f:
                for line in f:
                    try:
                        example = json.loads(line)
                        quality = example.get('metadata', {}).get('quality', 0)
                        if quality >= min_quality:
                            all_examples.append(example)
                    except json.JSONDecodeError:
                        continue

        logger.info(f"Collected {len(all_examples)} examples (quality >= {min_quality})")

        if not all_examples:
            logger.warning("No examples to version")
            return None

        # Deduplicate by content hash
        seen_hashes = set()
        unique_examples = []

        for ex in all_examples:
            # Create hash of instruction + response
            content = ex.get('messages', [{}])[-1].get('content', '')
            content_hash = hashlib.md5(content.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_examples.append(ex)

        logger.info(f"Deduplicated to {len(unique_examples)} unique examples")

        # Split train/val
        import random
        random.shuffle(unique_examples)

        val_size = int(len(unique_examples) * 0.1)
        val_examples = unique_examples[:val_size]
        train_examples = unique_examples[val_size:]

        # Save files
        train_path = version_dir / "train.jsonl"
        val_path = version_dir / "valid.jsonl"

        with open(train_path, 'w') as f:
            for ex in train_examples:
                f.write(json.dumps(ex) + '\n')

        with open(val_path, 'w') as f:
            for ex in val_examples:
                f.write(json.dumps(ex) + '\n')

        # Save metadata
        metadata = {
            "version_id": version_id,
            "created_at": datetime.now().isoformat(),
            "total_examples": len(unique_examples),
            "train_examples": len(train_examples),
            "val_examples": len(val_examples),
            "min_quality": min_quality,
            "source_files": [str(f) for f in self.TRAINING_DIR.glob("*.jsonl")],
        }

        with open(version_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        # Update metrics
        self.metrics["versions"].append({
            "id": version_id,
            "examples": len(unique_examples),
            "created_at": datetime.now().isoformat(),
        })
        self._save_metrics()

        logger.info(f"Created version {version_id}: {len(train_examples)} train, {len(val_examples)} val")

        return str(version_dir)

    def trigger_training(self, version_dir: str, epochs: int = 3) -> bool:
        """
        Trigger fine-tuning with the specified version.

        Args:
            version_dir: Path to training version directory
            epochs: Number of training epochs

        Returns:
            True if training started successfully
        """
        train_path = Path(version_dir) / "train.jsonl"

        if not train_path.exists():
            logger.error(f"Training file not found: {train_path}")
            return False

        logger.info(f"Triggering training with {train_path}")

        # Build training command
        finetune_script = Path(__file__).parent / "finetune_sam.py"

        cmd = [
            sys.executable,
            str(finetune_script),
            "--data", str(train_path),
            "--epochs", str(epochs),
            "--batch-size", "1",
        ]

        # Run in background
        log_file = Path(version_dir) / "training.log"

        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        logger.info(f"Training started with PID {process.pid}")
        logger.info(f"Log file: {log_file}")

        # Update metrics
        self.metrics["last_training_time"] = datetime.now().isoformat()
        self.metrics["training_runs"] += 1
        self._save_metrics()

        return True

    def should_train(self, threshold: int = None) -> bool:
        """Check if training should be triggered."""
        if threshold is None:
            threshold = self.DEFAULT_TRAINING_THRESHOLD

        # Check if enough new examples since last training
        new_count = self.get_new_item_count()

        if new_count >= threshold:
            logger.info(f"Training threshold met: {new_count} >= {threshold}")
            return True

        logger.info(f"Training threshold not met: {new_count} < {threshold}")
        return False

    def run_once(
        self,
        auto_train: bool = False,
        threshold: int = None,
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """
        Run the pipeline once.

        Args:
            auto_train: Automatically trigger training if threshold met
            threshold: Training threshold (new examples)
            batch_size: Processing batch size

        Returns:
            Pipeline run statistics
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "processing": None,
            "training_triggered": False,
            "version": None,
        }

        # Process new items
        results["processing"] = self.process_new_items(batch_size)

        # Check if should train
        if auto_train and self.should_train(threshold):
            # Create new version
            version_dir = self.create_training_version()
            results["version"] = version_dir

            if version_dir:
                # Trigger training
                results["training_triggered"] = self.trigger_training(version_dir)

        return results

    def run_daemon(
        self,
        interval_hours: float = 1.0,
        auto_train: bool = True,
        threshold: int = None,
    ):
        """
        Run as a daemon, processing periodically.

        Args:
            interval_hours: Hours between runs
            auto_train: Automatically trigger training
            threshold: Training threshold
        """
        logger.info(f"Starting daemon (interval: {interval_hours}h)")

        while True:
            try:
                logger.info("=" * 60)
                logger.info("Running pipeline...")

                results = self.run_once(
                    auto_train=auto_train,
                    threshold=threshold,
                )

                logger.info(f"Results: {json.dumps(results, indent=2, default=str)}")

            except Exception as e:
                logger.error(f"Pipeline error: {e}")

            # Sleep until next run
            sleep_seconds = interval_hours * 3600
            logger.info(f"Sleeping for {interval_hours} hours...")
            time.sleep(sleep_seconds)

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "metrics": self.metrics,
            "pending_items": self.get_new_item_count(),
            "training_dir": str(self.TRAINING_DIR),
            "versions": len(self.metrics.get("versions", [])),
            "latest_version": self.metrics.get("versions", [{}])[-1] if self.metrics.get("versions") else None,
        }


def main():
    parser = argparse.ArgumentParser(description="SAM Continuous Training Pipeline")

    parser.add_argument("--process", action="store_true", help="Process new items")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--create-version", action="store_true", help="Create training version")
    parser.add_argument("--train", action="store_true", help="Trigger training")

    parser.add_argument("--auto-train", action="store_true", help="Auto-trigger training")
    parser.add_argument("--threshold", type=int, default=1000, help="Training threshold")
    parser.add_argument("--batch-size", type=int, default=500, help="Processing batch size")
    parser.add_argument("--interval", type=float, default=1.0, help="Daemon interval (hours)")
    parser.add_argument("--min-quality", type=float, default=0.5, help="Minimum quality score")

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = ContinuousPipeline()
    pipeline.initialize()

    if args.status:
        status = pipeline.get_status()
        print(json.dumps(status, indent=2, default=str))

    elif args.daemon:
        pipeline.run_daemon(
            interval_hours=args.interval,
            auto_train=args.auto_train,
            threshold=args.threshold,
        )

    elif args.create_version:
        version_dir = pipeline.create_training_version(args.min_quality)
        print(f"Created version: {version_dir}")

    elif args.train:
        # Get latest version
        versions = sorted(pipeline.VERSIONS_DIR.iterdir())
        if versions:
            latest = versions[-1]
            pipeline.trigger_training(str(latest))
        else:
            print("No versions found. Run --create-version first.")

    elif args.process:
        results = pipeline.run_once(
            auto_train=args.auto_train,
            threshold=args.threshold,
            batch_size=args.batch_size,
        )
        print(json.dumps(results, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
