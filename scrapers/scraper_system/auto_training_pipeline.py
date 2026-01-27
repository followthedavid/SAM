#!/usr/bin/env python3
"""
Automatic Training Data Pipeline

Runs continuously alongside scrapers:
1. Watches for new scraped content
2. Converts to training format
3. Scores quality/complexity/diversity
4. Adds to training corpus (never duplicates)

Usage:
    python auto_training_pipeline.py watch     # Run continuously
    python auto_training_pipeline.py convert   # One-time conversion
    python auto_training_pipeline.py status    # Show stats
"""

import json
import sqlite3
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

# Import our SOTA pipeline
from sota_training_pipeline import SOTATrainingPipeline, DataScorer

# ============================================================================
# Source Configurations
# ============================================================================

# Content warning filters (AO3-specific)
# Set to empty list to include all content
EXCLUDED_WARNINGS = []  # No filtering - train on full dataset

SOURCES = {
    "ao3": {
        "db_path": "/Volumes/David External/ao3_archive/ao3_index.db",
        "content_dir": "/Volumes/David External/ao3_archive/works",
        "table": "works",
        "id_column": "work_id",
        "downloaded_check": "downloaded = 1",
        "content_type": "fiction",
        "format": "file",  # Content stored in files
        "has_warnings": True,  # Enable warning-based filtering
        "warnings_column": "warnings",
    },
    "ao3_roleplay": {
        "db_path": "/Volumes/David External/ao3_roleplay/ao3_roleplay_index.db",
        "content_dir": "/Volumes/David External/ao3_roleplay/works",
        "table": "works",
        "id_column": "work_id",
        "downloaded_check": "downloaded = 1",
        "content_type": "roleplay",
        "format": "file",
        "has_warnings": True,
        "warnings_column": "warnings",
    },
    "nifty": {
        "db_path": "/Volumes/David External/nifty_archive/nifty_index.db",
        "content_dir": "/Volumes/David External/nifty_archive/stories",
        "table": "stories",
        "id_column": "id",
        "downloaded_check": "downloaded = 1",
        "content_type": "fiction",
        "format": "file",
    },
    "wwd": {
        "db_path": "/Volumes/#1/wwd_archive/wwd_index.db",
        "content_dir": "/Volumes/#1/wwd_archive/articles",
        "table": "articles",
        "id_column": "id",
        "downloaded_check": "downloaded = 1",
        "content_type": "journalism",
        "format": "file",
    },
    "code": {
        "db_path": "/Volumes/David External/coding_training/code_collection.db",
        "table": "code_examples",
        "id_column": "id",
        "downloaded_check": "1=1",  # All rows are "downloaded"
        "content_type": "code",
        "format": "db_column",  # Content in database column
        "content_column": "code",
        "context_column": "context",
    },
}

# Output location
OUTPUT_DIR = Path("/Volumes/David External/SAM_training_corpus")


# ============================================================================
# Training Format Converters
# ============================================================================

class TrainingFormatConverter:
    """Converts raw content to training format."""

    @staticmethod
    def fiction_to_training(content: str, metadata: dict = None) -> List[dict]:
        """
        Convert fiction to instruction-following format.

        Creates multiple training examples from one story:
        - Story continuation prompts
        - Style analysis
        - Character voice
        """
        examples = []

        # Skip if too short
        if len(content) < 500:
            return []

        # Clean content
        content = content.strip()
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        if len(paragraphs) < 3:
            return []

        # Example 1: Story continuation
        split_point = len(paragraphs) // 2
        beginning = '\n\n'.join(paragraphs[:split_point])
        continuation = '\n\n'.join(paragraphs[split_point:])

        if len(beginning) > 200 and len(continuation) > 200:
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Continue this story:\n\n{beginning[:2000]}"},
                    {"from": "gpt", "value": continuation[:3000]}
                ]
            })

        # Example 2: Write in style (if long enough)
        if len(content) > 2000:
            sample = content[:1500]
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Write a short passage in this style:\n\n{sample}"},
                    {"from": "gpt", "value": content[1500:3500] if len(content) > 3500 else content[1500:]}
                ]
            })

        # Example 3: Full story as creative writing
        if 1000 < len(content) < 10000:
            title = metadata.get("title", "Untitled") if metadata else "Untitled"
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Write a creative story called '{title}'"},
                    {"from": "gpt", "value": content[:8000]}
                ]
            })

        return examples

    @staticmethod
    def roleplay_to_training(content: str, metadata: dict = None) -> List[dict]:
        """
        Convert roleplay content to conversational training format.
        """
        examples = []

        if len(content) < 300:
            return []

        # Try to detect dialogue patterns
        lines = content.split('\n')

        # Look for character dialogue markers
        dialogue_markers = [':', '"', '*', '-']
        has_dialogue = any(any(m in line[:50] for m in dialogue_markers) for line in lines[:20])

        if has_dialogue:
            # Format as roleplay conversation
            examples.append({
                "conversations": [
                    {"from": "human", "value": "Let's do a creative roleplay. You start:"},
                    {"from": "gpt", "value": content[:4000]}
                ]
            })
        else:
            # Fall back to fiction format
            examples.extend(TrainingFormatConverter.fiction_to_training(content, metadata))

        return examples

    @staticmethod
    def journalism_to_training(content: str, metadata: dict = None) -> List[dict]:
        """
        Convert journalism/articles to training format.
        """
        examples = []

        if len(content) < 300:
            return []

        title = metadata.get("title", "") if metadata else ""

        # Summarization example
        if len(content) > 500:
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Summarize this article:\n\n{content[:3000]}"},
                    {"from": "gpt", "value": f"This article discusses {title.lower() if title else 'the following topic'}. " +
                     content[:500].split('.')[0] + "..."}
                ]
            })

        # Writing style example
        if len(content) > 1000:
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Write a professional article about: {title or 'fashion trends'}"},
                    {"from": "gpt", "value": content[:4000]}
                ]
            })

        return examples

    @staticmethod
    def code_to_training(code: str, context: str = "", metadata: dict = None) -> List[dict]:
        """
        Convert code examples to training format.
        """
        examples = []

        if len(code) < 50:
            return []

        language = metadata.get("language", "python") if metadata else "python"

        # Code explanation
        examples.append({
            "conversations": [
                {"from": "human", "value": f"Explain this {language} code:\n\n```{language}\n{code[:2000]}\n```"},
                {"from": "gpt", "value": context[:1000] if context else f"This {language} code..."}
            ]
        })

        # Code writing
        if context:
            examples.append({
                "conversations": [
                    {"from": "human", "value": f"Write {language} code to: {context[:500]}"},
                    {"from": "gpt", "value": f"```{language}\n{code[:3000]}\n```"}
                ]
            })

        return examples


# ============================================================================
# Pipeline Runner
# ============================================================================

class AutoTrainingPipeline:
    """
    Automatic training data pipeline.
    """

    def __init__(self):
        self.sota_pipeline = SOTATrainingPipeline()
        self.scorer = DataScorer()
        self.converter = TrainingFormatConverter()

        # Tracking
        self.tracker_db = Path.home() / ".sam" / "pipeline_tracker.db"
        self._init_tracker()

        # Output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _init_tracker(self):
        """Initialize tracking database."""
        self.tracker_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.tracker_db)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed (
                source TEXT,
                item_id TEXT,
                processed_at TEXT,
                examples_created INTEGER,
                PRIMARY KEY (source, item_id)
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT,
                completed_at TEXT,
                source TEXT,
                items_processed INTEGER,
                examples_created INTEGER,
                errors INTEGER
            );
        """)
        conn.commit()
        conn.close()

    def _is_processed(self, source: str, item_id: str) -> bool:
        """Check if item already processed."""
        conn = sqlite3.connect(self.tracker_db)
        cursor = conn.execute(
            "SELECT 1 FROM processed WHERE source = ? AND item_id = ?",
            (source, str(item_id))
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def _mark_processed(self, source: str, item_id: str, examples_created: int):
        """Mark item as processed."""
        conn = sqlite3.connect(self.tracker_db)
        conn.execute(
            "INSERT OR REPLACE INTO processed (source, item_id, processed_at, examples_created) VALUES (?, ?, ?, ?)",
            (source, str(item_id), datetime.now().isoformat(), examples_created)
        )
        conn.commit()
        conn.close()

    def _get_unprocessed_items(self, source: str, limit: int = 100) -> List[tuple]:
        """Get unprocessed items from a source."""
        config = SOURCES.get(source)
        if not config:
            return []

        # Build query - include warnings column if applicable
        has_warnings = config.get("has_warnings", False)
        warnings_col = config.get("warnings_column", "warnings")

        if has_warnings:
            select_cols = f"{config['id_column']}, {warnings_col}"
        else:
            select_cols = config['id_column']

        # Get all downloaded items
        source_conn = sqlite3.connect(config["db_path"])
        cursor = source_conn.execute(f"""
            SELECT {select_cols} FROM {config['table']}
            WHERE {config['downloaded_check']}
        """)
        rows = cursor.fetchall()
        source_conn.close()

        # Filter out already processed and excluded warnings
        unprocessed = []
        filtered_by_warning = 0

        for row in rows:
            if has_warnings:
                item_id, warnings_json = row[0], row[1] if len(row) > 1 else "[]"

                # Check if any excluded warnings are present
                if EXCLUDED_WARNINGS and warnings_json:
                    skip = False
                    for excluded in EXCLUDED_WARNINGS:
                        if excluded in str(warnings_json):
                            skip = True
                            filtered_by_warning += 1
                            break
                    if skip:
                        continue
            else:
                item_id = row[0]

            if not self._is_processed(source, item_id):
                unprocessed.append(item_id)
                if len(unprocessed) >= limit:
                    break

        if filtered_by_warning > 0:
            print(f"  Filtered {filtered_by_warning} items by content warnings")

        return unprocessed

    def _load_content(self, source: str, item_id: str) -> tuple:
        """Load content for an item."""
        config = SOURCES.get(source)
        if not config:
            return None, {}

        if config["format"] == "file":
            # Content stored in files
            content_dir = Path(config["content_dir"])

            # Try common patterns
            for pattern in [f"{item_id}.txt", f"{item_id}.html", f"{item_id}/*"]:
                matches = list(content_dir.glob(pattern))
                if matches:
                    content_file = matches[0]
                    if content_file.is_file():
                        try:
                            content = content_file.read_text(errors='ignore')
                            return content, {"id": item_id}
                        except:
                            pass

            return None, {}

        elif config["format"] == "db_column":
            # Content in database
            source_conn = sqlite3.connect(config["db_path"])
            cursor = source_conn.execute(f"""
                SELECT {config['content_column']}, {config.get('context_column', "''")}
                FROM {config['table']}
                WHERE {config['id_column']} = ?
            """, (item_id,))
            row = cursor.fetchone()
            source_conn.close()

            if row:
                return row[0], {"context": row[1], "id": item_id}

        return None, {}

    def process_source(self, source: str, limit: int = 100) -> Dict[str, int]:
        """Process items from a source."""
        config = SOURCES.get(source)
        if not config:
            return {"error": f"Unknown source: {source}"}

        content_type = config["content_type"]

        # Get converter
        converters = {
            "fiction": self.converter.fiction_to_training,
            "roleplay": self.converter.roleplay_to_training,
            "journalism": self.converter.journalism_to_training,
            "code": self.converter.code_to_training,
        }
        converter = converters.get(content_type, self.converter.fiction_to_training)

        # Get unprocessed items
        items = self._get_unprocessed_items(source, limit)

        stats = {"processed": 0, "examples": 0, "errors": 0, "skipped": 0}
        all_examples = []

        for item_id in items:
            try:
                # Load content
                content, metadata = self._load_content(source, item_id)

                if not content or len(content) < 100:
                    stats["skipped"] += 1
                    self._mark_processed(source, item_id, 0)
                    continue

                # Convert to training format
                if content_type == "code":
                    examples = converter(content, metadata.get("context", ""), metadata)
                else:
                    examples = converter(content, metadata)

                # Score and add to SOTA pipeline
                for ex in examples:
                    text = json.dumps(ex)
                    result = self.sota_pipeline.process_and_score(
                        id=f"{source}_{item_id}_{len(all_examples)}",
                        source=source,
                        text=text
                    )

                    if result["status"] == "added":
                        all_examples.append(ex)

                stats["processed"] += 1
                stats["examples"] += len(examples)
                self._mark_processed(source, item_id, len(examples))

            except Exception as e:
                stats["errors"] += 1
                print(f"Error processing {source}/{item_id}: {e}")

        # Save examples to output file
        if all_examples:
            output_file = OUTPUT_DIR / f"{source}_training.jsonl"
            with open(output_file, "a") as f:
                for ex in all_examples:
                    f.write(json.dumps(ex) + "\n")

        return stats

    def watch(self, interval: int = 300):
        """Watch for new content and process continuously."""
        print("=" * 60)
        print("Auto Training Pipeline - Watch Mode")
        print(f"Checking every {interval} seconds")
        print("=" * 60)

        while True:
            for source in SOURCES:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing {source}...")
                stats = self.process_source(source, limit=50)

                if stats.get("processed", 0) > 0:
                    print(f"  Processed: {stats['processed']}, Examples: {stats['examples']}")
                elif stats.get("skipped", 0) > 0:
                    print(f"  Skipped: {stats['skipped']} (too short or empty)")
                else:
                    print(f"  No new items")

            print(f"\nSleeping {interval}s...")
            time.sleep(interval)

    def convert_all(self, limit_per_source: int = 1000):
        """One-time conversion of all sources."""
        print("=" * 60)
        print("Auto Training Pipeline - Full Conversion")
        print("=" * 60)

        total_stats = {"processed": 0, "examples": 0, "errors": 0}

        for source in SOURCES:
            print(f"\nProcessing {source}...")
            stats = self.process_source(source, limit=limit_per_source)

            for key in total_stats:
                total_stats[key] += stats.get(key, 0)

            print(f"  {source}: {stats}")

        print(f"\n{'=' * 60}")
        print(f"Total: {total_stats}")
        print(f"Output: {OUTPUT_DIR}")

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        status = {"sources": {}, "total": {"processed": 0, "examples": 0}}

        conn = sqlite3.connect(self.tracker_db)

        for source, config in SOURCES.items():
            # Get processed count
            cursor = conn.execute(
                "SELECT COUNT(*), SUM(examples_created) FROM processed WHERE source = ?",
                (source,)
            )
            row = cursor.fetchone()
            processed = row[0] or 0
            examples = row[1] or 0

            # Get total available
            try:
                source_conn = sqlite3.connect(config["db_path"])
                cursor = source_conn.execute(f"""
                    SELECT COUNT(*) FROM {config['table']} WHERE {config['downloaded_check']}
                """)
                total = cursor.fetchone()[0]
                source_conn.close()
            except:
                total = "?"

            status["sources"][source] = {
                "total": total,
                "processed": processed,
                "examples": examples,
                "remaining": total - processed if isinstance(total, int) else "?"
            }

            status["total"]["processed"] += processed
            status["total"]["examples"] += examples

        conn.close()

        # SOTA pipeline stats
        status["sota"] = self.sota_pipeline.get_stats()

        return status


def get_warning_stats():
    """Get content warning statistics for AO3 sources."""
    warning_stats = {}

    for source, config in SOURCES.items():
        if not config.get("has_warnings"):
            continue

        try:
            conn = sqlite3.connect(config["db_path"])
            warnings_col = config.get("warnings_column", "warnings")

            # Count by warning type
            cursor = conn.execute(f"""
                SELECT {warnings_col}, COUNT(*)
                FROM {config['table']}
                WHERE {config['downloaded_check']}
                GROUP BY {warnings_col}
            """)

            warning_counts = {}
            total = 0
            excluded_count = 0

            for row in cursor.fetchall():
                warnings_json = row[0] or "[]"
                count = row[1]
                total += count

                # Check if any excluded warning
                if EXCLUDED_WARNINGS:
                    for excluded in EXCLUDED_WARNINGS:
                        if excluded in str(warnings_json):
                            excluded_count += count
                            break

            warning_stats[source] = {
                "total": total,
                "excluded": excluded_count,
                "included": total - excluded_count,
                "excluded_warnings": EXCLUDED_WARNINGS
            }
            conn.close()
        except Exception as e:
            warning_stats[source] = {"error": str(e)}

    return warning_stats


def show_status():
    """Show pipeline status."""
    pipeline = AutoTrainingPipeline()
    status = pipeline.get_status()

    print("=" * 70)
    print("Auto Training Pipeline Status")
    print("=" * 70)

    # Show content filtering info
    if EXCLUDED_WARNINGS:
        print(f"\n⚠️  CONTENT FILTER ACTIVE:")
        print(f"   Excluding: {', '.join(EXCLUDED_WARNINGS)}")
        warning_stats = get_warning_stats()
        for source, ws in warning_stats.items():
            if "error" not in ws:
                pct = (ws["excluded"] / ws["total"] * 100) if ws["total"] > 0 else 0
                print(f"   {source}: {ws['excluded']:,} excluded ({pct:.1f}%), {ws['included']:,} included")

    print("\n📦 SOURCES:")
    for source, info in status["sources"].items():
        remaining = info["remaining"]
        remaining_str = f"{remaining:,}" if isinstance(remaining, int) else remaining
        print(f"\n   {source}:")
        print(f"      Total available: {info['total']:,}" if isinstance(info['total'], int) else f"      Total: {info['total']}")
        print(f"      Processed:       {info['processed']:,}")
        print(f"      Examples:        {info['examples']:,}")
        print(f"      Remaining:       {remaining_str}")

    print(f"\n📊 TOTALS:")
    print(f"   Processed items:    {status['total']['processed']:,}")
    print(f"   Training examples:  {status['total']['examples']:,}")

    print(f"\n🎯 SOTA PIPELINE:")
    sota = status["sota"]
    print(f"   Examples indexed:   {sota['examples']['total']:,}")
    print(f"   Avg quality:        {sota['examples']['avg_quality']}")
    print(f"   Curriculum stage:   {sota['curriculum']['current_stage']}")

    print(f"\n📁 Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python auto_training_pipeline.py status   - Show status")
        print("  python auto_training_pipeline.py convert  - Convert all sources")
        print("  python auto_training_pipeline.py watch    - Watch mode (continuous)")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        show_status()
    elif cmd == "convert":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        pipeline = AutoTrainingPipeline()
        pipeline.convert_all(limit)
    elif cmd == "watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        pipeline = AutoTrainingPipeline()
        pipeline.watch(interval)
    else:
        print(f"Unknown command: {cmd}")
