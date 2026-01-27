#!/usr/bin/env python3
"""
Training Data Tracker

Tracks which scraped items have been used for training to avoid duplicates.
Supports incremental training as new data is scraped.

Usage:
    tracker = TrainingTracker()

    # Get only new (unprocessed) items
    new_items = tracker.get_unprocessed("ao3", limit=10000)

    # After converting to training data
    tracker.mark_processed("ao3", [item_ids...], batch_id="train_v2")

    # Check status
    tracker.get_stats("ao3")
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Central tracking database
TRACKER_DB = Path.home() / ".sam" / "training_tracker.db"


class TrainingTracker:
    """Tracks which items have been used for training."""

    def __init__(self, db_path: Path = TRACKER_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize tracking database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_items (
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                PRIMARY KEY (source, item_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_batches (
                batch_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                items_count INTEGER,
                created_at TEXT NOT NULL,
                output_file TEXT,
                notes TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON processed_items(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batch ON processed_items(batch_id)")
        conn.commit()
        conn.close()

    def get_unprocessed_ids(self, source: str, source_db_path: str,
                            table: str, id_column: str = "id",
                            where_clause: str = "") -> List[str]:
        """Get IDs of items not yet used for training.

        Args:
            source: Source name (e.g., "ao3", "nifty")
            source_db_path: Path to the source SQLite database
            table: Table name in source database
            id_column: Column name for item ID
            where_clause: Additional WHERE conditions (e.g., "downloaded = 1")
        """
        # Get already processed IDs
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT item_id FROM processed_items WHERE source = ?",
            (source,)
        )
        processed = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Get all IDs from source database
        source_conn = sqlite3.connect(source_db_path)
        where = f"WHERE {where_clause}" if where_clause else ""
        cursor = source_conn.execute(
            f"SELECT {id_column} FROM {table} {where}"
        )
        all_ids = [str(row[0]) for row in cursor.fetchall()]
        source_conn.close()

        # Return only unprocessed
        unprocessed = [id for id in all_ids if id not in processed]
        return unprocessed

    def mark_processed(self, source: str, item_ids: List[str],
                       batch_id: str, output_file: str = None,
                       notes: str = None):
        """Mark items as processed for training.

        Args:
            source: Source name
            item_ids: List of item IDs that were processed
            batch_id: Unique identifier for this training batch
            output_file: Path to generated training file
            notes: Any notes about this batch
        """
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()

        # Record the batch
        conn.execute("""
            INSERT OR REPLACE INTO training_batches
            (batch_id, source, items_count, created_at, output_file, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (batch_id, source, len(item_ids), now, output_file, notes))

        # Mark individual items
        conn.executemany("""
            INSERT OR IGNORE INTO processed_items
            (source, item_id, batch_id, processed_at)
            VALUES (?, ?, ?, ?)
        """, [(source, item_id, batch_id, now) for item_id in item_ids])

        conn.commit()
        conn.close()

        print(f"Marked {len(item_ids)} items as processed for {source} (batch: {batch_id})")

    def get_stats(self, source: str = None) -> Dict[str, Any]:
        """Get processing statistics."""
        conn = sqlite3.connect(self.db_path)

        if source:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM processed_items WHERE source = ?",
                (source,)
            )
            processed_count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT batch_id, items_count, created_at FROM training_batches WHERE source = ? ORDER BY created_at DESC",
                (source,)
            )
            batches = [{"batch_id": r[0], "items": r[1], "date": r[2]} for r in cursor.fetchall()]

            conn.close()
            return {
                "source": source,
                "total_processed": processed_count,
                "batches": batches
            }
        else:
            cursor = conn.execute(
                "SELECT source, COUNT(*) FROM processed_items GROUP BY source"
            )
            by_source = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return {"by_source": by_source}

    def reset_source(self, source: str):
        """Reset tracking for a source (use carefully - allows retraining on same data)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM processed_items WHERE source = ?", (source,))
        conn.execute("DELETE FROM training_batches WHERE source = ?", (source,))
        conn.commit()
        conn.close()
        print(f"Reset tracking for {source}")


# Source configurations
SOURCES = {
    "ao3": {
        "db_path": "/Volumes/David External/ao3_archive/ao3_index.db",
        "table": "works",
        "id_column": "work_id",
        "where": "downloaded = 1",
        "content_column": "content",  # or path to content files
    },
    "ao3_roleplay": {
        "db_path": "/Volumes/David External/ao3_roleplay/ao3_roleplay_index.db",
        "table": "works",
        "id_column": "work_id",
        "where": "downloaded = 1",
    },
    "nifty": {
        "db_path": "/Volumes/David External/nifty_archive/nifty_index.db",
        "table": "stories",
        "id_column": "id",
        "where": "downloaded = 1",
    },
}


def get_new_training_items(source: str, limit: int = None) -> List[str]:
    """Convenience function to get unprocessed item IDs."""
    if source not in SOURCES:
        raise ValueError(f"Unknown source: {source}. Available: {list(SOURCES.keys())}")

    config = SOURCES[source]
    tracker = TrainingTracker()

    ids = tracker.get_unprocessed_ids(
        source=source,
        source_db_path=config["db_path"],
        table=config["table"],
        id_column=config["id_column"],
        where_clause=config.get("where", "")
    )

    if limit:
        ids = ids[:limit]

    return ids


def show_status():
    """Show current tracking status."""
    tracker = TrainingTracker()

    print("=" * 60)
    print("Training Data Tracker Status")
    print("=" * 60)

    for source, config in SOURCES.items():
        # Get total in source DB
        try:
            conn = sqlite3.connect(config["db_path"])
            where = f"WHERE {config.get('where', '1=1')}"
            cursor = conn.execute(f"SELECT COUNT(*) FROM {config['table']} {where}")
            total = cursor.fetchone()[0]
            conn.close()
        except:
            total = "?"

        # Get processed count
        stats = tracker.get_stats(source)
        processed = stats["total_processed"]

        unprocessed = total - processed if isinstance(total, int) else "?"

        print(f"\n{source}:")
        print(f"  Total downloaded: {total:,}" if isinstance(total, int) else f"  Total: {total}")
        print(f"  Already trained:  {processed:,}")
        print(f"  New (untrained):  {unprocessed:,}" if isinstance(unprocessed, int) else f"  New: {unprocessed}")

        if stats["batches"]:
            print(f"  Recent batches:")
            for b in stats["batches"][:3]:
                print(f"    - {b['batch_id']}: {b['items']:,} items ({b['date'][:10]})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_status()
    else:
        print("Usage: python training_tracker.py status")
        print("\nOr import and use programmatically:")
        print("  from training_tracker import TrainingTracker, get_new_training_items")
