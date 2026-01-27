#!/usr/bin/env python3
"""
SAM Training Data Statistics Dashboard
Phase 5.1.9: Data gathering stats for monitoring pipeline health

Provides:
- TrainingDataStats class for comprehensive statistics
- get_stats() - total examples, by source, by format, quality distribution
- get_daily_stats() - examples gathered per day
- get_source_health() - which sources are producing quality data
- Integration ready for /api/training/stats endpoint

Location: /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_stats.py
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

# Add parent to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


class DataSource(Enum):
    """Training data source types."""
    GIT_COMMITS = "git_commits"
    CODE_PATTERNS = "code_patterns"
    KNOWLEDGE_DOCS = "knowledge_docs"
    ROUTING_EXAMPLES = "routing_examples"
    CONVERSATION_CAPTURE = "conversation_capture"
    DISTILLATION = "distillation"
    MANUAL_CURATION = "manual_curation"
    SYNTHETIC = "synthetic"


class DataFormat(Enum):
    """Training data format types."""
    INSTRUCTION = "instruction"  # instruction/input/output
    CHAT = "chat"  # messages array
    COMPLETION = "completion"  # prompt/completion
    RAW = "raw"  # unstructured


class QualityTier(Enum):
    """Quality tier classification."""
    GOLD = "gold"  # Human-verified, high quality
    SILVER = "silver"  # Auto-validated, good quality
    BRONZE = "bronze"  # Basic filtering passed
    RAW = "raw"  # Unvalidated


@dataclass
class SourceStats:
    """Statistics for a single data source."""
    source: str
    total_examples: int
    quality_distribution: Dict[str, int]
    avg_token_length: float
    last_updated: Optional[str]
    health_score: float  # 0.0 to 1.0
    errors_24h: int
    examples_24h: int


@dataclass
class DailyStats:
    """Daily statistics."""
    date: str
    total_examples: int
    by_source: Dict[str, int]
    by_quality: Dict[str, int]
    avg_token_length: float


@dataclass
class OverallStats:
    """Overall training data statistics."""
    total_examples: int
    by_source: Dict[str, int]
    by_format: Dict[str, int]
    by_quality: Dict[str, int]
    avg_token_length: float
    total_tokens: int
    oldest_example: Optional[str]
    newest_example: Optional[str]
    storage_bytes: int


class TrainingDataStats:
    """
    Comprehensive training data statistics manager.

    Tracks data from multiple sources:
    - JSONL files in training_data/
    - Knowledge distillation database
    - Conversation capture
    - Git/code mining outputs
    """

    # Default paths
    TRAINING_DATA_DIR = SCRIPT_DIR / "training_data"
    DISTILLATION_DB = Path.home() / ".sam" / "memory" / "distillation.db"
    STATS_CACHE_FILE = SCRIPT_DIR / ".training_stats_cache.json"
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        training_data_dir: Optional[Path] = None,
        distillation_db: Optional[Path] = None,
    ):
        self.training_data_dir = training_data_dir or self.TRAINING_DATA_DIR
        self.distillation_db = distillation_db or self.DISTILLATION_DB
        # Use instance-level cache file based on training_data_dir
        if training_data_dir:
            self.stats_cache_file = training_data_dir / ".stats_cache.json"
        else:
            self.stats_cache_file = self.STATS_CACHE_FILE
        self._cache = None
        self._cache_time = None

    def _load_cache(self) -> Optional[Dict]:
        """Load cached stats if fresh."""
        if self.stats_cache_file.exists():
            try:
                data = json.loads(self.stats_cache_file.read_text())
                cache_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                if (datetime.now() - cache_time).seconds < self.CACHE_TTL_SECONDS:
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def _save_cache(self, data: Dict):
        """Save stats to cache."""
        data["cached_at"] = datetime.now().isoformat()
        try:
            self.stats_cache_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass  # Cache write failure is non-critical

    def _count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars per token average)."""
        return len(text) // 4 if text else 0

    def _detect_format(self, example: Dict) -> str:
        """Detect the format of a training example."""
        if "messages" in example:
            return DataFormat.CHAT.value
        if "instruction" in example and "output" in example:
            return DataFormat.INSTRUCTION.value
        if "prompt" in example and "completion" in example:
            return DataFormat.COMPLETION.value
        return DataFormat.RAW.value

    def _detect_quality(self, example: Dict) -> str:
        """Detect quality tier from example metadata."""
        if example.get("verified") or example.get("human_reviewed"):
            return QualityTier.GOLD.value
        if example.get("quality_score", 0) > 0.7:
            return QualityTier.SILVER.value
        if example.get("validated"):
            return QualityTier.BRONZE.value
        return QualityTier.RAW.value

    def _get_example_text(self, example: Dict) -> str:
        """Extract text content from example for token counting."""
        parts = []

        # Chat format
        if "messages" in example:
            for msg in example["messages"]:
                parts.append(msg.get("content", ""))

        # Instruction format
        if "instruction" in example:
            parts.append(example.get("instruction", ""))
            parts.append(example.get("input", ""))
            parts.append(example.get("output", ""))

        # Completion format
        if "prompt" in example:
            parts.append(example.get("prompt", ""))
            parts.append(example.get("completion", ""))

        return " ".join(filter(None, parts))

    def _analyze_jsonl_file(self, filepath: Path) -> Dict[str, Any]:
        """Analyze a JSONL file for statistics."""
        stats = {
            "total": 0,
            "formats": defaultdict(int),
            "qualities": defaultdict(int),
            "total_tokens": 0,
            "errors": 0,
            "dates": [],
        }

        if not filepath.exists():
            return stats

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        example = json.loads(line)
                        stats["total"] += 1
                        stats["formats"][self._detect_format(example)] += 1
                        stats["qualities"][self._detect_quality(example)] += 1
                        stats["total_tokens"] += self._count_tokens(
                            self._get_example_text(example)
                        )
                        if "timestamp" in example:
                            stats["dates"].append(example["timestamp"])
                        elif "created_at" in example:
                            stats["dates"].append(example["created_at"])
                    except json.JSONDecodeError:
                        stats["errors"] += 1
        except Exception as e:
            stats["error"] = str(e)

        return stats

    def _analyze_distillation_db(self) -> Dict[str, Any]:
        """Analyze distillation database for statistics."""
        stats = {
            "total": 0,
            "by_quality": defaultdict(int),
            "by_category": defaultdict(int),
            "total_tokens": 0,
            "dates": [],
            "validated": 0,
        }

        if not self.distillation_db.exists():
            return stats

        try:
            conn = sqlite3.connect(self.distillation_db)
            cursor = conn.cursor()

            # Check if distillations table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='distillations'"
            )
            if not cursor.fetchone():
                conn.close()
                return stats

            # Total count
            cursor.execute("SELECT COUNT(*) FROM distillations")
            stats["total"] = cursor.fetchone()[0]

            # Quality distribution
            cursor.execute("""
                SELECT quality_tier, COUNT(*)
                FROM distillations
                GROUP BY quality_tier
            """)
            for tier, count in cursor.fetchall():
                stats["by_quality"][tier or "unknown"] = count

            # Category distribution
            cursor.execute("""
                SELECT category, COUNT(*)
                FROM distillations
                GROUP BY category
            """)
            for cat, count in cursor.fetchall():
                stats["by_category"][cat or "uncategorized"] = count

            # Validated count
            cursor.execute("SELECT COUNT(*) FROM distillations WHERE validated = 1")
            stats["validated"] = cursor.fetchone()[0]

            # Date range
            cursor.execute("""
                SELECT MIN(created_at), MAX(created_at)
                FROM distillations
            """)
            row = cursor.fetchone()
            if row[0]:
                stats["oldest"] = row[0]
            if row[1]:
                stats["newest"] = row[1]

            # Approximate token count (sample-based)
            cursor.execute("""
                SELECT reasoning, response
                FROM distillations
                LIMIT 100
            """)
            sample_tokens = 0
            sample_count = 0
            for reasoning, response in cursor.fetchall():
                sample_tokens += self._count_tokens(reasoning or "")
                sample_tokens += self._count_tokens(response or "")
                sample_count += 1

            if sample_count > 0:
                avg_tokens = sample_tokens / sample_count
                stats["total_tokens"] = int(avg_tokens * stats["total"])

            conn.close()

        except Exception as e:
            stats["error"] = str(e)

        return stats

    def get_stats(self, force_refresh: bool = False) -> OverallStats:
        """
        Get overall training data statistics.

        Returns comprehensive stats including:
        - Total examples across all sources
        - Breakdown by source type
        - Breakdown by format (instruction, chat, completion)
        - Breakdown by quality tier
        - Token statistics
        - Date range
        - Storage usage
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached and "overall" in cached:
                return OverallStats(**cached["overall"])

        by_source = defaultdict(int)
        by_format = defaultdict(int)
        by_quality = defaultdict(int)
        total_tokens = 0
        total_examples = 0
        storage_bytes = 0
        oldest = None
        newest = None

        # Analyze JSONL files
        if self.training_data_dir.exists():
            for jsonl_file in self.training_data_dir.glob("*.jsonl"):
                file_stats = self._analyze_jsonl_file(jsonl_file)
                source_name = jsonl_file.stem

                by_source[source_name] = file_stats["total"]
                total_examples += file_stats["total"]
                total_tokens += file_stats["total_tokens"]
                storage_bytes += jsonl_file.stat().st_size

                for fmt, count in file_stats["formats"].items():
                    by_format[fmt] += count
                for qual, count in file_stats["qualities"].items():
                    by_quality[qual] += count

                for date_str in file_stats.get("dates", []):
                    if date_str:
                        if oldest is None or date_str < oldest:
                            oldest = date_str
                        if newest is None or date_str > newest:
                            newest = date_str

        # Analyze distillation database
        distill_stats = self._analyze_distillation_db()
        if distill_stats["total"] > 0:
            by_source["distillation"] = distill_stats["total"]
            total_examples += distill_stats["total"]
            total_tokens += distill_stats["total_tokens"]
            by_format[DataFormat.INSTRUCTION.value] += distill_stats["total"]

            for qual, count in distill_stats["by_quality"].items():
                by_quality[qual] += count

            if distill_stats.get("oldest"):
                if oldest is None or distill_stats["oldest"] < oldest:
                    oldest = distill_stats["oldest"]
            if distill_stats.get("newest"):
                if newest is None or distill_stats["newest"] > newest:
                    newest = distill_stats["newest"]

            if self.distillation_db.exists():
                storage_bytes += self.distillation_db.stat().st_size

        avg_token_length = total_tokens / total_examples if total_examples > 0 else 0

        result = OverallStats(
            total_examples=total_examples,
            by_source=dict(by_source),
            by_format=dict(by_format),
            by_quality=dict(by_quality),
            avg_token_length=round(avg_token_length, 1),
            total_tokens=total_tokens,
            oldest_example=oldest,
            newest_example=newest,
            storage_bytes=storage_bytes,
        )

        # Cache results
        cache_data = {"overall": asdict(result)}
        self._save_cache(cache_data)

        return result

    def get_daily_stats(self, days: int = 30) -> List[DailyStats]:
        """
        Get examples gathered per day for the last N days.

        Returns a list of DailyStats objects, one per day,
        showing data collection trends over time.
        """
        cutoff = datetime.now() - timedelta(days=days)
        daily = defaultdict(lambda: {
            "total": 0,
            "by_source": defaultdict(int),
            "by_quality": defaultdict(int),
            "tokens": 0,
        })

        # Analyze JSONL files for timestamps
        if self.training_data_dir.exists():
            for jsonl_file in self.training_data_dir.glob("*.jsonl"):
                source_name = jsonl_file.stem
                try:
                    with open(jsonl_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            try:
                                example = json.loads(line)
                                ts = example.get("timestamp") or example.get("created_at")
                                if ts:
                                    # Parse date
                                    try:
                                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                        if dt >= cutoff:
                                            date_key = dt.strftime("%Y-%m-%d")
                                            daily[date_key]["total"] += 1
                                            daily[date_key]["by_source"][source_name] += 1
                                            daily[date_key]["by_quality"][
                                                self._detect_quality(example)
                                            ] += 1
                                            daily[date_key]["tokens"] += self._count_tokens(
                                                self._get_example_text(example)
                                            )
                                    except ValueError:
                                        pass
                            except json.JSONDecodeError:
                                pass
                except Exception:
                    pass

        # Analyze distillation database
        if self.distillation_db.exists():
            try:
                conn = sqlite3.connect(self.distillation_db)
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT DATE(created_at) as date, quality_tier, COUNT(*)
                    FROM distillations
                    WHERE created_at >= ?
                    GROUP BY DATE(created_at), quality_tier
                """, (cutoff.isoformat(),))

                for date_str, quality, count in cursor.fetchall():
                    if date_str:
                        daily[date_str]["total"] += count
                        daily[date_str]["by_source"]["distillation"] += count
                        daily[date_str]["by_quality"][quality or "unknown"] += count

                conn.close()
            except Exception:
                pass

        # Convert to sorted list
        results = []
        for date_key in sorted(daily.keys()):
            day_data = daily[date_key]
            avg_tokens = day_data["tokens"] / day_data["total"] if day_data["total"] > 0 else 0
            results.append(DailyStats(
                date=date_key,
                total_examples=day_data["total"],
                by_source=dict(day_data["by_source"]),
                by_quality=dict(day_data["by_quality"]),
                avg_token_length=round(avg_tokens, 1),
            ))

        return results

    def get_source_health(self) -> List[SourceStats]:
        """
        Get health status for each data source.

        Health score is based on:
        - Recent activity (examples in last 24h)
        - Quality distribution (more gold/silver = higher)
        - Error rate
        - Last update time
        """
        sources = []
        now = datetime.now()
        cutoff_24h = now - timedelta(hours=24)

        # Analyze JSONL files
        if self.training_data_dir.exists():
            for jsonl_file in self.training_data_dir.glob("*.jsonl"):
                source_name = jsonl_file.stem
                file_stats = self._analyze_jsonl_file(jsonl_file)

                # Count examples in last 24h
                examples_24h = 0
                for date_str in file_stats.get("dates", []):
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if dt >= cutoff_24h:
                                examples_24h += 1
                        except ValueError:
                            pass

                # Calculate quality distribution
                quality_dist = dict(file_stats["qualities"])
                total = file_stats["total"]

                # Calculate health score
                health_score = 0.5  # Base score

                # Activity bonus (up to 0.2)
                if examples_24h > 0:
                    health_score += min(0.2, examples_24h / 100)

                # Quality bonus (up to 0.3)
                gold = quality_dist.get(QualityTier.GOLD.value, 0)
                silver = quality_dist.get(QualityTier.SILVER.value, 0)
                if total > 0:
                    quality_ratio = (gold + silver * 0.7) / total
                    health_score += quality_ratio * 0.3

                # Recency penalty
                file_mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                days_since_update = (now - file_mtime).days
                if days_since_update > 7:
                    health_score -= min(0.2, days_since_update * 0.02)

                # Error penalty
                error_rate = file_stats["errors"] / (total + file_stats["errors"]) if total > 0 else 0
                health_score -= error_rate * 0.2

                health_score = max(0.0, min(1.0, health_score))
                avg_tokens = file_stats["total_tokens"] / total if total > 0 else 0

                sources.append(SourceStats(
                    source=source_name,
                    total_examples=total,
                    quality_distribution=quality_dist,
                    avg_token_length=round(avg_tokens, 1),
                    last_updated=file_mtime.isoformat(),
                    health_score=round(health_score, 2),
                    errors_24h=file_stats["errors"],
                    examples_24h=examples_24h,
                ))

        # Analyze distillation database
        distill_stats = self._analyze_distillation_db()
        if distill_stats["total"] > 0:
            health_score = 0.7  # Distillation is generally high quality

            # Validated bonus
            if distill_stats["total"] > 0:
                validated_ratio = distill_stats["validated"] / distill_stats["total"]
                health_score += validated_ratio * 0.3

            avg_tokens = distill_stats["total_tokens"] / distill_stats["total"]

            sources.append(SourceStats(
                source="distillation",
                total_examples=distill_stats["total"],
                quality_distribution=dict(distill_stats["by_quality"]),
                avg_token_length=round(avg_tokens, 1),
                last_updated=distill_stats.get("newest"),
                health_score=round(health_score, 2),
                errors_24h=0,
                examples_24h=0,  # Would need timestamp analysis
            ))

        # Sort by health score descending
        sources.sort(key=lambda x: x.health_score, reverse=True)

        return sources

    def get_api_stats(self) -> Dict[str, Any]:
        """
        Get stats formatted for API response.

        Combines all stats into a single JSON-serializable dict
        suitable for the /api/training/stats endpoint.
        """
        overall = self.get_stats()
        daily = self.get_daily_stats(days=14)  # Last 2 weeks
        sources = self.get_source_health()

        return {
            "overall": asdict(overall),
            "daily": [asdict(d) for d in daily],
            "sources": [asdict(s) for s in sources],
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_examples": overall.total_examples,
                "total_tokens": overall.total_tokens,
                "storage_mb": round(overall.storage_bytes / (1024 * 1024), 2),
                "healthy_sources": sum(1 for s in sources if s.health_score >= 0.6),
                "total_sources": len(sources),
                "top_quality_percentage": round(
                    sum(
                        overall.by_quality.get(QualityTier.GOLD.value, 0) +
                        overall.by_quality.get(QualityTier.SILVER.value, 0)
                        for _ in [1]
                    ) / overall.total_examples * 100
                    if overall.total_examples > 0 else 0,
                    1
                ),
            }
        }


# =============================================================================
# API Integration Functions
# =============================================================================

def api_training_stats() -> Dict[str, Any]:
    """
    API endpoint handler for /api/training/stats.

    Returns comprehensive training data statistics.
    """
    try:
        stats = TrainingDataStats()
        return {
            "success": True,
            "data": stats.get_api_stats()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def api_training_daily(days: int = 30) -> Dict[str, Any]:
    """
    API endpoint handler for /api/training/daily.

    Returns daily collection statistics.
    """
    try:
        stats = TrainingDataStats()
        daily = stats.get_daily_stats(days=days)
        return {
            "success": True,
            "data": [asdict(d) for d in daily],
            "days": days
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def api_training_sources() -> Dict[str, Any]:
    """
    API endpoint handler for /api/training/sources.

    Returns source health information.
    """
    try:
        stats = TrainingDataStats()
        sources = stats.get_source_health()
        return {
            "success": True,
            "data": [asdict(s) for s in sources]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# CLI
# =============================================================================

def main():
    """Command-line interface for training stats."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Data Statistics")
    parser.add_argument("command", nargs="?", default="summary",
                       choices=["summary", "daily", "sources", "json"],
                       help="Command to run")
    parser.add_argument("--days", type=int, default=14,
                       help="Number of days for daily stats")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON")

    args = parser.parse_args()

    stats = TrainingDataStats()

    if args.command == "summary" or args.command is None:
        overall = stats.get_stats()

        if args.json:
            print(json.dumps(asdict(overall), indent=2))
        else:
            print("=" * 60)
            print("SAM Training Data Statistics")
            print("=" * 60)
            print(f"\nTotal Examples: {overall.total_examples:,}")
            print(f"Total Tokens: {overall.total_tokens:,}")
            print(f"Avg Token Length: {overall.avg_token_length:.1f}")
            print(f"Storage: {overall.storage_bytes / (1024*1024):.2f} MB")
            print(f"\nDate Range: {overall.oldest_example or 'N/A'} to {overall.newest_example or 'N/A'}")

            print("\nBy Source:")
            for source, count in sorted(overall.by_source.items(), key=lambda x: -x[1]):
                print(f"  {source}: {count:,}")

            print("\nBy Format:")
            for fmt, count in sorted(overall.by_format.items(), key=lambda x: -x[1]):
                print(f"  {fmt}: {count:,}")

            print("\nBy Quality:")
            for qual, count in sorted(overall.by_quality.items(), key=lambda x: -x[1]):
                print(f"  {qual}: {count:,}")

    elif args.command == "daily":
        daily = stats.get_daily_stats(days=args.days)

        if args.json:
            print(json.dumps([asdict(d) for d in daily], indent=2))
        else:
            print(f"\nDaily Stats (last {args.days} days):")
            print("-" * 40)
            for day in daily[-10:]:  # Show last 10 days
                print(f"{day.date}: {day.total_examples} examples, {day.avg_token_length:.0f} avg tokens")

    elif args.command == "sources":
        sources = stats.get_source_health()

        if args.json:
            print(json.dumps([asdict(s) for s in sources], indent=2))
        else:
            print("\nSource Health:")
            print("-" * 60)
            for src in sources:
                health_bar = "=" * int(src.health_score * 10) + "-" * (10 - int(src.health_score * 10))
                print(f"{src.source}: [{health_bar}] {src.health_score:.2f}")
                print(f"  Examples: {src.total_examples:,}, Last updated: {src.last_updated or 'N/A'}")

    elif args.command == "json":
        print(json.dumps(stats.get_api_stats(), indent=2))


if __name__ == "__main__":
    main()
