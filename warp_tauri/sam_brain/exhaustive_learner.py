#!/usr/bin/env python3
"""
SAM Exhaustive Learning System - Comprehensive Foundation

This system makes SAM learn EVERYTHING needed to be your daily AI companion,
while Claude stands by for complex reasoning.

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │                     EXHAUSTIVE LEARNING                          │
  ├─────────────────────────────────────────────────────────────────┤
  │                                                                   │
  │  1. DATA INGESTION (Parallel)                                    │
  │     ├── ChatGPT History (filtered for current relevance)         │
  │     ├── Claude Session Exports                                   │
  │     ├── Scraped Training Data (coding, roleplay, etc.)          │
  │     └── Synthetic Generation (from templates)                    │
  │                                                                   │
  │  2. PROCESSING PIPELINE (4 parallel workers)                     │
  │     ├── Quality Filter (remove outdated, low-quality)            │
  │     ├── Category Classification                                  │
  │     ├── Deduplication                                            │
  │     └── Priority Assignment                                       │
  │                                                                   │
  │  3. LEARNING MODES                                               │
  │     ├── Direct Capture (ChatGPT/Claude already good)             │
  │     ├── Local Refinement (SAM tries, compares)                   │
  │     └── Claude Escalation (only when needed)                     │
  │                                                                   │
  │  4. CONTINUOUS TRAINING                                          │
  │     ├── Export to JSONL                                          │
  │     ├── LoRA fine-tuning                                         │
  │     └── Quality metrics tracking                                  │
  │                                                                   │
  └─────────────────────────────────────────────────────────────────┘

OUTDATED CONTENT FILTER:
  These concepts are now OUTDATED and should be deprioritized:
  - Docker (dropped 2026-01-18, now MLX native)
  - Ollama (dropped for MLX)
  - LangChain (too heavy)
  - Traditional embeddings (using MLX MiniLM now)

CURRENT FOCUS:
  - MLX native inference
  - Apple Silicon optimization
  - Swift/SwiftUI development
  - Local-first architecture
  - Terminal coordination
  - Voice pipeline (F5-TTS + RVC)

Usage:
    python3 exhaustive_learner.py start      # Run exhaustive learning
    python3 exhaustive_learner.py status     # Comprehensive status
    python3 exhaustive_learner.py analyze    # Analyze data quality
    python3 exhaustive_learner.py export     # Export all training data
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import multiprocessing

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)

CHATGPT_TRAINING = Path("/Volumes/David External/chatgpt_training")
SCRAPED_DATA = Path("/Volumes/David External")
TRAINING_OUTPUT = SAM_BRAIN / "training_data"
TRAINING_OUTPUT.mkdir(exist_ok=True)

DB_PATH = LEARNING_DIR / "exhaustive_learner.db"
LOG_PATH = LEARNING_DIR / "exhaustive_learner.log"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("exhaustive_learner")


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT FILTERS - What's current vs outdated
# ═══════════════════════════════════════════════════════════════════════════════

OUTDATED_PATTERNS = [
    r'\bollama\b',           # Dropped for MLX
    r'\bdocker\b',           # On-demand only now
    r'\blangchain\b',        # Too heavy
    r'\bopenai\.ChatCompletion\b',  # Old API
    r'pip install ollama',
    r'docker run',
    r'docker-compose',
    r'ollama pull',
    r'ollama run',
]

CURRENT_FOCUS_PATTERNS = [
    r'\bmlx\b',              # Native ML
    r'\bapple silicon\b',
    r'\bm[123] \w+\b',       # M1/M2/M3 chips
    r'\bswift\b',
    r'\bswiftui\b',
    r'\bmetal\b',            # GPU
    r'\bacceler\w+\b',       # Accelerate framework
    r'\bcore ?ml\b',
    r'\btauri\b',
    r'\brust\b',
    r'\bwarp\b',
    r'\bqwen\b',             # Model family
    r'\bf5-?tts\b',          # Voice
    r'\brvc\b',              # Voice cloning
]

PRIORITY_TOPICS = {
    # Highest priority - SAM's core capabilities
    1: [
        "mlx", "apple silicon", "native", "local inference",
        "swift", "swiftui", "macos", "ios",
        "semantic memory", "embeddings", "vector search",
        "voice", "tts", "stt", "emotion",
    ],
    # High priority - coding skills
    2: [
        "python", "rust", "typescript",
        "async", "concurrency", "parallel",
        "api", "http", "websocket",
        "database", "sqlite", "caching",
    ],
    # Medium priority - general capabilities
    3: [
        "roleplay", "character", "persona",
        "planning", "architecture", "design",
        "debugging", "testing", "optimization",
    ],
    # Lower priority - general knowledge
    4: [
        "explanation", "tutorial", "how to",
        "general", "coaching", "advice",
    ],
}


def is_outdated(text: str) -> bool:
    """Check if content references outdated concepts."""
    text_lower = text.lower()
    for pattern in OUTDATED_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_current_focus(text: str) -> bool:
    """Check if content matches current SAM focus."""
    text_lower = text.lower()
    for pattern in CURRENT_FOCUS_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def get_priority(text: str) -> int:
    """Determine priority level (1=highest)."""
    text_lower = text.lower()

    for priority, keywords in PRIORITY_TOPICS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return priority

    return 5  # Default lowest


def calculate_quality(user_msg: str, assistant_msg: str) -> float:
    """Calculate quality score for a training pair."""
    score = 0.5  # Base score

    # Length checks
    if len(assistant_msg) > 100:
        score += 0.1
    if len(assistant_msg) > 500:
        score += 0.1

    # Has code
    if "```" in assistant_msg:
        score += 0.1

    # Current focus content
    if is_current_focus(user_msg) or is_current_focus(assistant_msg):
        score += 0.15

    # Outdated content penalty
    if is_outdated(user_msg) or is_outdated(assistant_msg):
        score -= 0.3

    # Clamp to 0-1
    return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

class ExhaustiveDB:
    """Database for exhaustive learning pipeline."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Raw ingested data
        c.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id TEXT PRIMARY KEY,
                source TEXT,           -- 'chatgpt_coding', 'scraped_apple', 'claude_session', etc.
                user_content TEXT NOT NULL,
                assistant_content TEXT NOT NULL,
                original_category TEXT,
                ingested_at TEXT
            )
        """)

        # Processed training pairs
        c.execute("""
            CREATE TABLE IF NOT EXISTS training_pairs (
                id TEXT PRIMARY KEY,
                raw_id TEXT,
                user_content TEXT NOT NULL,
                assistant_content TEXT NOT NULL,
                category TEXT,
                priority INTEGER,
                quality_score REAL,
                is_outdated INTEGER DEFAULT 0,
                is_current_focus INTEGER DEFAULT 0,
                processed_at TEXT,
                exported INTEGER DEFAULT 0,
                exported_to TEXT,
                FOREIGN KEY (raw_id) REFERENCES raw_data(id)
            )
        """)

        # Processing stats
        c.execute("""
            CREATE TABLE IF NOT EXISTS processing_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                total_ingested INTEGER,
                passed_filter INTEGER,
                outdated_filtered INTEGER,
                duplicates_removed INTEGER,
                avg_quality REAL,
                processed_at TEXT
            )
        """)

        # Deduplication index
        c.execute("""
            CREATE TABLE IF NOT EXISTS dedup_hashes (
                hash TEXT PRIMARY KEY,
                pair_id TEXT
            )
        """)

        # Create indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_training_priority ON training_pairs(priority, quality_score DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_training_exported ON training_pairs(exported)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_training_category ON training_pairs(category)")

        conn.commit()
        conn.close()

    def ingest_raw(self, source: str, user_content: str,
                   assistant_content: str, category: str) -> Optional[str]:
        """Ingest raw data."""
        raw_id = hashlib.md5(f"{user_content}{assistant_content}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR IGNORE INTO raw_data
                (id, source, user_content, assistant_content, original_category, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (raw_id, source, user_content, assistant_content, category,
                  datetime.now().isoformat()))
            conn.commit()
            return raw_id if c.rowcount > 0 else None
        finally:
            conn.close()

    def is_duplicate(self, user_content: str) -> bool:
        """Check if content is duplicate."""
        content_hash = hashlib.md5(user_content.strip().lower().encode()).hexdigest()[:32]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT 1 FROM dedup_hashes WHERE hash = ?", (content_hash,))
        exists = c.fetchone() is not None
        conn.close()
        return exists

    def add_dedup_hash(self, user_content: str, pair_id: str):
        """Add deduplication hash."""
        content_hash = hashlib.md5(user_content.strip().lower().encode()).hexdigest()[:32]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO dedup_hashes (hash, pair_id) VALUES (?, ?)",
                  (content_hash, pair_id))
        conn.commit()
        conn.close()

    def add_training_pair(self, raw_id: str, user_content: str, assistant_content: str,
                          category: str, priority: int, quality: float,
                          outdated: bool, current_focus: bool) -> str:
        """Add processed training pair."""
        pair_id = hashlib.md5(f"{user_content}{time.time()}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO training_pairs
            (id, raw_id, user_content, assistant_content, category, priority,
             quality_score, is_outdated, is_current_focus, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pair_id, raw_id, user_content, assistant_content, category,
              priority, quality, int(outdated), int(current_focus),
              datetime.now().isoformat()))
        conn.commit()
        conn.close()

        self.add_dedup_hash(user_content, pair_id)
        return pair_id

    def get_unexported(self, category: str = None, min_quality: float = 0.5,
                       limit: int = 1000) -> List[Dict]:
        """Get unexported training pairs."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = """
            SELECT * FROM training_pairs
            WHERE exported = 0
              AND quality_score >= ?
              AND is_outdated = 0
        """
        params = [min_quality]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY priority ASC, quality_score DESC LIMIT ?"
        params.append(limit)

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_exported(self, ids: List[str], path: str):
        """Mark pairs as exported."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for pair_id in ids:
            c.execute("""
                UPDATE training_pairs
                SET exported = 1, exported_to = ?
                WHERE id = ?
            """, (path, pair_id))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get comprehensive stats."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        stats = {}

        # Raw data stats
        c.execute("SELECT COUNT(*) FROM raw_data")
        stats["total_raw"] = c.fetchone()[0]

        c.execute("SELECT source, COUNT(*) FROM raw_data GROUP BY source")
        stats["raw_by_source"] = dict(c.fetchall())

        # Training pairs stats
        c.execute("SELECT COUNT(*) FROM training_pairs")
        stats["total_pairs"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM training_pairs WHERE exported = 0")
        stats["unexported"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM training_pairs WHERE is_outdated = 1")
        stats["outdated"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM training_pairs WHERE is_current_focus = 1")
        stats["current_focus"] = c.fetchone()[0]

        c.execute("SELECT category, COUNT(*) FROM training_pairs GROUP BY category")
        stats["by_category"] = dict(c.fetchall())

        c.execute("SELECT priority, COUNT(*) FROM training_pairs GROUP BY priority")
        stats["by_priority"] = dict(c.fetchall())

        c.execute("SELECT AVG(quality_score) FROM training_pairs")
        stats["avg_quality"] = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM dedup_hashes")
        stats["unique_hashes"] = c.fetchone()[0]

        conn.close()
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCES
# ═══════════════════════════════════════════════════════════════════════════════

class DataIngester:
    """Ingests data from all sources."""

    def __init__(self):
        self.db = ExhaustiveDB()

    def ingest_chatgpt(self, limit_per_file: int = 5000) -> Dict[str, int]:
        """Ingest all ChatGPT training data."""
        results = {}

        for jsonl_file in CHATGPT_TRAINING.glob("chatgpt_*.jsonl"):
            if jsonl_file.stem == "chatgpt_all":
                continue

            category = jsonl_file.stem.replace("chatgpt_", "")
            source = f"chatgpt_{category}"
            count = 0

            logger.info(f"Ingesting {source}...")

            with open(jsonl_file) as f:
                for line in f:
                    if count >= limit_per_file:
                        break
                    try:
                        data = json.loads(line)
                        messages = data.get("messages", [])
                        if len(messages) >= 2:
                            user_msg = messages[0].get("content", "")
                            assistant_msg = messages[1].get("content", "")

                            if 20 < len(user_msg) < 3000 and 50 < len(assistant_msg) < 8000:
                                if self.db.ingest_raw(source, user_msg, assistant_msg, category):
                                    count += 1
                    except json.JSONDecodeError:
                        continue

            results[source] = count
            logger.info(f"  Ingested {count} from {source}")

        return results

    def ingest_scraped_training(self) -> Dict[str, int]:
        """Ingest training data from scrapers."""
        results = {}

        # Apple dev data
        apple_db = SCRAPED_DATA / "apple_dev_archive" / "apple_dev.db"
        if apple_db.exists():
            try:
                conn = sqlite3.connect(str(apple_db))
                c = conn.cursor()

                # Get docs as Q&A pairs
                c.execute("""
                    SELECT title, content FROM docs
                    WHERE content IS NOT NULL AND LENGTH(content) > 100
                    LIMIT 2000
                """)
                count = 0
                for title, content in c.fetchall():
                    question = f"Explain {title} in Apple development."
                    if self.db.ingest_raw("scraped_apple", question, content[:5000], "coding"):
                        count += 1

                # Get code examples
                c.execute("""
                    SELECT description, code FROM github_code
                    WHERE code IS NOT NULL AND LENGTH(code) > 50
                    LIMIT 2000
                """)
                for desc, code in c.fetchall():
                    question = f"Show me code for: {desc}"
                    answer = f"Here's an example:\n\n```\n{code}\n```"
                    if self.db.ingest_raw("scraped_github", question, answer, "coding"):
                        count += 1

                conn.close()
                results["scraped_apple"] = count
                logger.info(f"  Ingested {count} from Apple dev archive")
            except Exception as e:
                logger.error(f"Error ingesting Apple data: {e}")

        # Code collection
        code_db = SCRAPED_DATA / "coding_training" / "code_collection.db"
        if code_db.exists():
            try:
                conn = sqlite3.connect(str(code_db))
                c = conn.cursor()
                c.execute("""
                    SELECT description, code, language FROM code_examples
                    WHERE code IS NOT NULL AND LENGTH(code) > 50
                    LIMIT 3000
                """)
                count = 0
                for desc, code, lang in c.fetchall():
                    question = f"Write {lang} code to: {desc}"
                    answer = f"```{lang}\n{code}\n```"
                    if self.db.ingest_raw("scraped_code", question, answer, "coding"):
                        count += 1
                conn.close()
                results["scraped_code"] = count
                logger.info(f"  Ingested {count} from code collection")
            except Exception as e:
                logger.error(f"Error ingesting code data: {e}")

        return results

    def ingest_conversation_exports(self) -> int:
        """Ingest from Claude session exports."""
        count = 0

        for jsonl_file in TRAINING_OUTPUT.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        messages = data.get("messages", [])
                        topic = data.get("metadata", {}).get("topic", "general")

                        if len(messages) >= 2:
                            user_msg = messages[0].get("content", "")
                            assistant_msg = messages[1].get("content", "")

                            if user_msg and assistant_msg:
                                if self.db.ingest_raw("claude_session", user_msg, assistant_msg, topic):
                                    count += 1
                    except json.JSONDecodeError:
                        continue

        logger.info(f"  Ingested {count} from Claude sessions")
        return count


class DataProcessor:
    """Processes raw data into training pairs."""

    def __init__(self):
        self.db = ExhaustiveDB()

    def process_all(self, workers: int = 4) -> Dict:
        """Process all raw data with parallel workers."""
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Get unprocessed raw data
        c.execute("""
            SELECT r.* FROM raw_data r
            LEFT JOIN training_pairs t ON r.id = t.raw_id
            WHERE t.id IS NULL
            LIMIT 10000
        """)
        raw_data = [dict(r) for r in c.fetchall()]
        conn.close()

        if not raw_data:
            logger.info("No new raw data to process")
            return {"processed": 0}

        logger.info(f"Processing {len(raw_data)} raw entries...")

        results = {
            "processed": 0,
            "passed": 0,
            "outdated": 0,
            "duplicates": 0,
            "low_quality": 0,
        }

        def process_one(item: Dict) -> Dict:
            """Process a single item."""
            user_content = item["user_content"]
            assistant_content = item["assistant_content"]

            # Check duplicate
            if self.db.is_duplicate(user_content):
                return {"status": "duplicate"}

            # Check outdated
            outdated = is_outdated(user_content) or is_outdated(assistant_content)
            current_focus = is_current_focus(user_content) or is_current_focus(assistant_content)

            # Calculate quality
            quality = calculate_quality(user_content, assistant_content)

            # Determine priority
            priority = get_priority(user_content + " " + assistant_content)

            # Skip low quality outdated content
            if outdated and quality < 0.6:
                return {"status": "outdated_low_quality"}

            # Add to training pairs
            self.db.add_training_pair(
                raw_id=item["id"],
                user_content=user_content,
                assistant_content=assistant_content,
                category=item["original_category"],
                priority=priority,
                quality=quality,
                outdated=outdated,
                current_focus=current_focus
            )

            return {"status": "passed", "quality": quality}

        # Process in parallel
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_one, item): item for item in raw_data}

            for future in as_completed(futures):
                result = future.result()
                results["processed"] += 1

                if result["status"] == "passed":
                    results["passed"] += 1
                elif result["status"] == "duplicate":
                    results["duplicates"] += 1
                elif result["status"] == "outdated_low_quality":
                    results["outdated"] += 1

        logger.info(f"Processing complete: {results}")
        return results


class TrainingExporter:
    """Exports training data to various formats."""

    def __init__(self):
        self.db = ExhaustiveDB()

    def export_by_category(self, min_quality: float = 0.5) -> Dict[str, Tuple[int, Path]]:
        """Export training data by category."""
        results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get all categories
        conn = sqlite3.connect(self.db.db_path)
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM training_pairs WHERE exported = 0")
        categories = [r[0] for r in c.fetchall()]
        conn.close()

        for category in categories:
            pairs = self.db.get_unexported(category=category, min_quality=min_quality)
            if not pairs:
                continue

            output_file = TRAINING_OUTPUT / f"exhaustive_{category}_{timestamp}.jsonl"
            exported_ids = []

            with open(output_file, 'w') as f:
                for pair in pairs:
                    training_item = {
                        "messages": [
                            {"role": "user", "content": pair["user_content"]},
                            {"role": "assistant", "content": pair["assistant_content"]}
                        ],
                        "metadata": {
                            "source": "exhaustive_learner",
                            "category": category,
                            "priority": pair["priority"],
                            "quality": pair["quality_score"],
                            "is_current_focus": bool(pair["is_current_focus"]),
                        }
                    }
                    f.write(json.dumps(training_item) + "\n")
                    exported_ids.append(pair["id"])

            self.db.mark_exported(exported_ids, str(output_file))
            results[category] = (len(exported_ids), output_file)
            logger.info(f"Exported {len(exported_ids)} {category} pairs to {output_file}")

        return results

    def export_priority_mix(self, limit: int = 5000, min_quality: float = 0.6) -> Tuple[int, Path]:
        """Export a balanced mix prioritizing current focus."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = TRAINING_OUTPUT / f"exhaustive_priority_mix_{timestamp}.jsonl"

        pairs = self.db.get_unexported(min_quality=min_quality, limit=limit)
        if not pairs:
            return (0, output_file)

        exported_ids = []

        with open(output_file, 'w') as f:
            for pair in pairs:
                training_item = {
                    "messages": [
                        {"role": "user", "content": pair["user_content"]},
                        {"role": "assistant", "content": pair["assistant_content"]}
                    ]
                }
                f.write(json.dumps(training_item) + "\n")
                exported_ids.append(pair["id"])

        self.db.mark_exported(exported_ids, str(output_file))
        logger.info(f"Exported {len(exported_ids)} priority pairs to {output_file}")
        return (len(exported_ids), output_file)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ExhaustiveLearner:
    """Main orchestrator for exhaustive learning."""

    def __init__(self):
        self.db = ExhaustiveDB()
        self.ingester = DataIngester()
        self.processor = DataProcessor()
        self.exporter = TrainingExporter()

    def run_full_pipeline(self, workers: int = 4) -> Dict:
        """Run the complete exhaustive learning pipeline."""
        results = {
            "ingestion": {},
            "processing": {},
            "export": {},
            "elapsed_seconds": 0,
        }

        start_time = time.time()

        # Phase 1: Ingest all data
        logger.info("=" * 60)
        logger.info("PHASE 1: DATA INGESTION")
        logger.info("=" * 60)

        results["ingestion"]["chatgpt"] = self.ingester.ingest_chatgpt(limit_per_file=3000)
        results["ingestion"]["scraped"] = self.ingester.ingest_scraped_training()
        results["ingestion"]["sessions"] = self.ingester.ingest_conversation_exports()

        # Phase 2: Process into training pairs
        logger.info("=" * 60)
        logger.info("PHASE 2: PROCESSING")
        logger.info("=" * 60)

        results["processing"] = self.processor.process_all(workers=workers)

        # Phase 3: Export
        logger.info("=" * 60)
        logger.info("PHASE 3: EXPORT")
        logger.info("=" * 60)

        export_results = self.exporter.export_by_category(min_quality=0.5)
        results["export"]["by_category"] = {k: v[0] for k, v in export_results.items()}

        priority_count, priority_path = self.exporter.export_priority_mix(limit=5000, min_quality=0.6)
        results["export"]["priority_mix"] = priority_count

        results["elapsed_seconds"] = int(time.time() - start_time)

        logger.info("=" * 60)
        logger.info(f"PIPELINE COMPLETE in {results['elapsed_seconds']}s")
        logger.info("=" * 60)

        return results


def status():
    """Print comprehensive status."""
    db = ExhaustiveDB()
    stats = db.get_stats()

    print("\n" + "═" * 70)
    print("  SAM EXHAUSTIVE LEARNER - COMPREHENSIVE STATUS")
    print("═" * 70)

    print(f"\n{'─' * 70}")
    print("  📥 RAW DATA INGESTED")
    print(f"{'─' * 70}")
    print(f"   Total:                  {stats['total_raw']:,}")

    if stats.get("raw_by_source"):
        for source, count in sorted(stats["raw_by_source"].items()):
            print(f"      {source:25} {count:>8,}")

    print(f"\n{'─' * 70}")
    print("  📝 TRAINING PAIRS")
    print(f"{'─' * 70}")
    print(f"   Total processed:        {stats['total_pairs']:,}")
    print(f"   Unexported:             {stats['unexported']:,}")
    print(f"   Average quality:        {stats['avg_quality']:.2f}")

    print(f"\n   Content Analysis:")
    print(f"      Current focus:       {stats['current_focus']:,} pairs ({stats['current_focus']*100/max(1,stats['total_pairs']):.1f}%)")
    print(f"      Outdated content:    {stats['outdated']:,} pairs ({stats['outdated']*100/max(1,stats['total_pairs']):.1f}%)")

    if stats.get("by_category"):
        print(f"\n   By Category:")
        for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
            pct = count * 100 / max(1, stats['total_pairs'])
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"      {cat:15} [{bar}] {count:>6,} ({pct:4.1f}%)")

    if stats.get("by_priority"):
        print(f"\n   By Priority:")
        priority_labels = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Default"}
        for pri, count in sorted(stats["by_priority"].items()):
            label = priority_labels.get(pri, f"P{pri}")
            print(f"      {label:15} {count:>8,}")

    print(f"\n   Deduplication:")
    print(f"      Unique hashes:       {stats['unique_hashes']:,}")

    # Training data files
    print(f"\n{'─' * 70}")
    print("  📁 TRAINING FILES")
    print(f"{'─' * 70}")

    total_training_examples = 0
    for jsonl_file in sorted(TRAINING_OUTPUT.glob("*.jsonl")):
        try:
            with open(jsonl_file) as f:
                lines = sum(1 for _ in f)
                total_training_examples += lines
                size_mb = jsonl_file.stat().st_size / (1024 * 1024)
                print(f"   {jsonl_file.name:45} {lines:>6,} examples ({size_mb:.1f} MB)")
        except:
            pass

    print(f"\n   TOTAL TRAINING EXAMPLES: {total_training_examples:,}")

    print("\n" + "═" * 70)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "start":
        learner = ExhaustiveLearner()
        results = learner.run_full_pipeline(workers=4)
        print(f"\nResults: {json.dumps(results, indent=2)}")

    elif cmd == "ingest":
        ingester = DataIngester()
        print("\nIngesting ChatGPT data...")
        results = ingester.ingest_chatgpt(limit_per_file=5000)
        print(f"ChatGPT: {results}")
        print("\nIngesting scraped data...")
        results = ingester.ingest_scraped_training()
        print(f"Scraped: {results}")
        print("\nIngesting session exports...")
        count = ingester.ingest_conversation_exports()
        print(f"Sessions: {count}")

    elif cmd == "process":
        processor = DataProcessor()
        results = processor.process_all(workers=4)
        print(f"\nProcessing results: {results}")

    elif cmd == "export":
        exporter = TrainingExporter()
        results = exporter.export_by_category(min_quality=0.5)
        for cat, (count, path) in results.items():
            print(f"  {cat}: {count} -> {path}")

    elif cmd == "status":
        status()

    elif cmd == "analyze":
        status()
        print("\n" + "─" * 70)
        print("  CONTENT ANALYSIS")
        print("─" * 70)

        # Sample some content to show outdated vs current
        db = ExhaustiveDB()
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        print("\n  CURRENT FOCUS SAMPLES (high priority):")
        c.execute("""
            SELECT user_content, quality_score FROM training_pairs
            WHERE is_current_focus = 1 AND is_outdated = 0
            ORDER BY quality_score DESC LIMIT 5
        """)
        for row in c.fetchall():
            content = row["user_content"][:80].replace("\n", " ")
            print(f"    [{row['quality_score']:.2f}] {content}...")

        print("\n  OUTDATED CONTENT SAMPLES (filtered out):")
        c.execute("""
            SELECT user_content, quality_score FROM training_pairs
            WHERE is_outdated = 1
            ORDER BY quality_score DESC LIMIT 5
        """)
        for row in c.fetchall():
            content = row["user_content"][:80].replace("\n", " ")
            print(f"    [{row['quality_score']:.2f}] {content}...")

        conn.close()

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: start, ingest, process, export, status, analyze")
        sys.exit(1)


if __name__ == "__main__":
    main()
