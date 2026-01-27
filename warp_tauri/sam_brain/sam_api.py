#!/usr/bin/env python3
"""
SAM API - JSON interface for Tauri integration

Provides a simple CLI that outputs JSON for the Tauri app to consume.
Can also run as a local HTTP server.

Usage:
  sam_api.py query "list files in SAM"
  sam_api.py projects
  sam_api.py memory
  sam_api.py status
  sam_api.py search "<query>"
  sam_api.py categories
  sam_api.py starred
  sam_api.py self          # SAM explains itself
  sam_api.py suggest       # Top improvement suggestions
  sam_api.py proactive     # What SAM noticed
  sam_api.py learning      # What SAM has learned
  sam_api.py feedback      # Record feedback (JSON input)
  sam_api.py scan          # Trigger improvement scan
  sam_api.py context       # Full context for Claude (paste-ready)
  sam_api.py warp-status   # Warp replication status
  sam_api.py server [port]

Fact Management (Phase 1.3.9):
  sam_api.py facts list [--user X] [--category X] [--min-confidence 0.5]
  sam_api.py facts add "fact text" --category preferences [--user X]
  sam_api.py facts remove <fact_id>
  sam_api.py facts search "query" [--user X]
  sam_api.py facts get <fact_id>

Index Management (Phase 2.2.10):
  sam_api.py index status                              # Show index stats
  sam_api.py index build [path] [--project X] [--force]  # Build/rebuild index
  sam_api.py index search "query" [--project X] [--type X]  # Search index
  sam_api.py index watch [path] [--project X]          # Start file watcher
  sam_api.py index stop                                # Stop file watcher
  sam_api.py index clear [--project X]                 # Clear index
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Add sam_brain to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Exhaustive inventory (legacy)
INVENTORY_FILE = SCRIPT_DIR / "exhaustive_analysis" / "master_inventory.json"
STYLE_FILE = SCRIPT_DIR / "training_data" / "style_profile.json"

# SAM Intelligence singleton (lazy loaded)
_sam_intelligence = None

# Distillation DB singleton (lazy loaded)
_distillation_db = None

# Feedback DB singleton (lazy loaded) - Phase 1.2.2-1.2.4
_feedback_db = None

def get_feedback_db():
    """Lazy-load Feedback DB singleton."""
    global _feedback_db
    if _feedback_db is None:
        try:
            from feedback_system import FeedbackDB
            _feedback_db = FeedbackDB()
        except ImportError as e:
            print(f"Warning: Could not load FeedbackDB: {e}", file=sys.stderr)
            _feedback_db = None
        except Exception as e:
            print(f"Warning: Error initializing FeedbackDB: {e}", file=sys.stderr)
            _feedback_db = None
    return _feedback_db

def get_distillation_db():
    """Lazy-load Distillation DB singleton."""
    global _distillation_db
    if _distillation_db is None:
        try:
            from knowledge_distillation import DistillationDB
            _distillation_db = DistillationDB()
        except ImportError as e:
            print(f"Warning: Could not load DistillationDB: {e}", file=sys.stderr)
            _distillation_db = None
        except Exception as e:
            print(f"Warning: Error initializing DistillationDB: {e}", file=sys.stderr)
            _distillation_db = None
    return _distillation_db


def get_distillation_stats() -> dict:
    """Get comprehensive distillation statistics for the /api/self endpoint.

    Returns:
        dict with distillation stats including:
        - total_examples: Total captured examples
        - pending_review: Count awaiting review
        - approved: Count of approved examples
        - rejected: Count of rejected examples
        - filter_stats: Quality filter statistics
        - storage: Storage location and size info
    """
    db = get_distillation_db()
    if not db:
        return {
            "available": False,
            "error": "Distillation DB not available"
        }

    try:
        # Get full stats from the database
        raw_stats = db.get_stats()

        # Get storage size
        storage_path = Path(raw_stats.get("db_path", ""))
        storage_size_mb = 0.0
        if storage_path.exists():
            storage_size_mb = storage_path.stat().st_size / (1024 * 1024)

        # Calculate rejected count (examples that were reviewed but not approved)
        total_reviewed = raw_stats.get("total_examples", 0) - raw_stats.get("unreviewed_examples", 0)
        rejected_count = total_reviewed - raw_stats.get("approved_examples", 0)

        # Get quality filter stats
        filter_stats = raw_stats.get("quality_filter", {})

        return {
            "available": True,
            "total_examples": raw_stats.get("total_examples", 0),
            "pending_review": raw_stats.get("pending_review", 0),
            "approved": raw_stats.get("approved_examples", 0),
            "rejected": max(0, rejected_count),  # Ensure non-negative
            "unreviewed": raw_stats.get("unreviewed_examples", 0),
            "filter_stats": {
                "session_processed": filter_stats.get("total_processed", 0),
                "session_accepted": filter_stats.get("total_accepted", 0),
                "session_rejected": filter_stats.get("total_rejected", 0),
                "acceptance_rate": filter_stats.get("acceptance_rate", 0.0),
                "rejection_rate": filter_stats.get("rejection_rate", 0.0),
                "average_quality_score": filter_stats.get("average_quality_score", 0.0),
                "rejection_reasons": filter_stats.get("rejection_reasons", {}),
            },
            "by_domain": raw_stats.get("by_domain", {}),
            "by_reasoning_type": raw_stats.get("by_reasoning_type", {}),
            "patterns": {
                "reasoning_patterns": raw_stats.get("reasoning_patterns", 0),
                "corrections": raw_stats.get("corrections", 0),
                "chain_of_thought": raw_stats.get("chain_of_thought", 0),
                "principles": raw_stats.get("principles", 0),
                "preference_pairs": raw_stats.get("preference_pairs", 0),
                "skill_templates": raw_stats.get("skill_templates", 0),
            },
            "storage": {
                "location": raw_stats.get("db_path", "unknown"),
                "size_mb": round(storage_size_mb, 2),
                "using_external_drive": raw_stats.get("using_external_drive", False),
            },
            "filter_rejections_total": raw_stats.get("filter_rejections", 0),
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


def get_sam_intelligence():
    """Lazy-load SAM Intelligence singleton."""
    global _sam_intelligence
    if _sam_intelligence is None:
        try:
            from sam_intelligence import SamIntelligence
            _sam_intelligence = SamIntelligence()
        except ImportError as e:
            print(f"Warning: Could not load SAM Intelligence: {e}", file=sys.stderr)
            _sam_intelligence = None
    return _sam_intelligence


# ============ Compression Monitoring (Phase 2.3.6) ============

@dataclass
class CompressionRecord:
    """Single compression event record."""
    timestamp: datetime
    original_tokens: int
    compressed_tokens: int
    ratio: float
    query_type: str
    section: str  # Which section was compressed
    budget_overrun: bool = False  # True if compression couldn't meet target


class CompressionMonitor:
    """
    Tracks compression statistics across requests for monitoring.

    Phase 2.3.6: Provides insights into:
    - Tokens saved per request and cumulative
    - Average compression ratios
    - Section-by-section usage patterns
    - Budget overrun detection

    Stats are kept in memory and reset daily.
    """

    def __init__(self):
        self._records: List[CompressionRecord] = []
        self._daily_reset_date: datetime = datetime.now().date()
        self._section_usage: Dict[str, int] = defaultdict(int)
        self._query_type_counts: Dict[str, int] = defaultdict(int)
        self._total_tokens_saved_today: int = 0
        self._total_requests_today: int = 0
        self._budget_overruns_today: int = 0

    def _check_daily_reset(self):
        """Reset counters if it's a new day."""
        today = datetime.now().date()
        if today != self._daily_reset_date:
            self._records = []
            self._section_usage = defaultdict(int)
            self._query_type_counts = defaultdict(int)
            self._total_tokens_saved_today = 0
            self._total_requests_today = 0
            self._budget_overruns_today = 0
            self._daily_reset_date = today

    def record_compression(
        self,
        original_tokens: int,
        compressed_tokens: int,
        query_type: str = "unknown",
        section: str = "context",
        budget_target: Optional[int] = None
    ):
        """
        Record a compression event.

        Args:
            original_tokens: Tokens before compression
            compressed_tokens: Tokens after compression
            query_type: Type of query (code, chat, recall, etc.)
            section: Which context section was compressed
            budget_target: If set, check for budget overrun
        """
        self._check_daily_reset()

        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        tokens_saved = original_tokens - compressed_tokens
        budget_overrun = budget_target is not None and compressed_tokens > budget_target

        record = CompressionRecord(
            timestamp=datetime.now(),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            ratio=ratio,
            query_type=query_type,
            section=section,
            budget_overrun=budget_overrun
        )

        self._records.append(record)
        self._section_usage[section] += 1
        self._query_type_counts[query_type] += 1
        self._total_tokens_saved_today += tokens_saved
        self._total_requests_today += 1
        if budget_overrun:
            self._budget_overruns_today += 1

        # Keep only last 1000 records to prevent memory growth
        if len(self._records) > 1000:
            self._records = self._records[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive compression statistics.

        Returns:
            Dict with all compression metrics
        """
        self._check_daily_reset()

        if not self._records:
            return {
                "available": True,
                "total_requests": 0,
                "tokens_saved_today": 0,
                "avg_compression_ratio": 1.0,
                "avg_tokens_saved_per_request": 0,
                "section_usage": {},
                "query_type_breakdown": {},
                "budget_overruns": 0,
                "last_hour_requests": 0,
                "date": str(self._daily_reset_date)
            }

        # Calculate averages
        ratios = [r.ratio for r in self._records]
        avg_ratio = sum(ratios) / len(ratios)

        tokens_saved_list = [r.original_tokens - r.compressed_tokens for r in self._records]
        avg_saved = sum(tokens_saved_list) / len(tokens_saved_list)

        # Last hour stats
        one_hour_ago = datetime.now() - timedelta(hours=1)
        last_hour_records = [r for r in self._records if r.timestamp > one_hour_ago]

        # Section usage with percentages
        total_section_uses = sum(self._section_usage.values())
        section_usage = {
            section: {
                "count": count,
                "percentage": round(count / total_section_uses * 100, 1) if total_section_uses > 0 else 0
            }
            for section, count in self._section_usage.items()
        }

        # Query type breakdown
        total_query_types = sum(self._query_type_counts.values())
        query_type_breakdown = {
            qtype: {
                "count": count,
                "percentage": round(count / total_query_types * 100, 1) if total_query_types > 0 else 0
            }
            for qtype, count in self._query_type_counts.items()
        }

        # Efficiency score (higher is better)
        # Based on achieving good compression without overruns
        overrun_penalty = self._budget_overruns_today / max(1, self._total_requests_today)
        efficiency_score = round((1.0 - avg_ratio) * (1.0 - overrun_penalty) * 100, 1)

        return {
            "available": True,
            "total_requests": self._total_requests_today,
            "tokens_saved_today": self._total_tokens_saved_today,
            "avg_compression_ratio": round(avg_ratio, 3),
            "avg_tokens_saved_per_request": round(avg_saved, 1),
            "section_usage": section_usage,
            "query_type_breakdown": query_type_breakdown,
            "budget_overruns": self._budget_overruns_today,
            "overrun_rate": round(self._budget_overruns_today / max(1, self._total_requests_today) * 100, 1),
            "last_hour_requests": len(last_hour_records),
            "efficiency_score": efficiency_score,
            "date": str(self._daily_reset_date),
            "timestamp": datetime.now().isoformat()
        }

    def get_summary_for_self(self) -> Dict[str, Any]:
        """
        Get a summary suitable for /api/self endpoint.

        Returns:
            Condensed stats dict for context_stats field
        """
        self._check_daily_reset()

        if not self._records:
            return {
                "avg_compression": 1.0,
                "tokens_saved_today": 0,
                "section_usage": {}
            }

        ratios = [r.ratio for r in self._records]
        avg_ratio = sum(ratios) / len(ratios)

        return {
            "avg_compression": round(avg_ratio, 3),
            "tokens_saved_today": self._total_tokens_saved_today,
            "section_usage": dict(self._section_usage)
        }


# Compression monitor singleton
_compression_monitor: Optional[CompressionMonitor] = None


def get_compression_monitor() -> CompressionMonitor:
    """Get or create compression monitor singleton."""
    global _compression_monitor
    if _compression_monitor is None:
        _compression_monitor = CompressionMonitor()
    return _compression_monitor


def record_compression_stats(
    original_tokens: int,
    compressed_tokens: int,
    query_type: str = "unknown",
    section: str = "context",
    budget_target: Optional[int] = None
):
    """
    Convenience function to record compression stats.

    Use this from cognitive/compression.py or anywhere compression happens.
    """
    monitor = get_compression_monitor()
    monitor.record_compression(
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        query_type=query_type,
        section=section,
        budget_target=budget_target
    )


# ============ Vision Stats Monitoring (Phase 3.2.6) ============

@dataclass
class VisionRecord:
    """Single vision processing event record."""
    timestamp: datetime
    tier: str  # ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE
    processing_time_ms: int
    memory_peak_mb: float
    task_type: str
    escalated: bool = False
    success: bool = True
    from_cache: bool = False


class VisionStatsMonitor:
    """
    Tracks vision processing statistics across requests for monitoring.

    Phase 3.2.6: Provides insights into:
    - Requests per tier (ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE)
    - Average processing time per tier
    - Memory peaks during processing
    - Escalation rate to Claude
    - Cache hit rates

    Stats are kept in memory and reset daily.
    """

    def __init__(self):
        self._records: List[VisionRecord] = []
        self._daily_reset_date: datetime = datetime.now().date()
        self._tier_counts: Dict[str, int] = defaultdict(int)
        self._tier_times: Dict[str, List[int]] = defaultdict(list)
        self._task_type_counts: Dict[str, int] = defaultdict(int)
        self._total_requests_today: int = 0
        self._escalations_today: int = 0
        self._cache_hits_today: int = 0
        self._memory_peaks: List[float] = []
        self._max_memory_peak_today: float = 0.0

    def _check_daily_reset(self):
        """Reset counters if it's a new day."""
        today = datetime.now().date()
        if today != self._daily_reset_date:
            self._records = []
            self._tier_counts = defaultdict(int)
            self._tier_times = defaultdict(list)
            self._task_type_counts = defaultdict(int)
            self._total_requests_today = 0
            self._escalations_today = 0
            self._cache_hits_today = 0
            self._memory_peaks = []
            self._max_memory_peak_today = 0.0
            self._daily_reset_date = today

    def record_vision_request(
        self,
        tier: str,
        processing_time_ms: int,
        task_type: str = "unknown",
        escalated: bool = False,
        success: bool = True,
        from_cache: bool = False,
        memory_peak_mb: float = 0.0
    ):
        """
        Record a vision processing event.

        Args:
            tier: Which tier handled the request (ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE)
            processing_time_ms: Time taken to process
            task_type: Type of vision task (ocr, color, describe, detect, reasoning, etc.)
            escalated: Whether this was escalated to a higher tier
            success: Whether processing succeeded
            from_cache: Whether result came from cache
            memory_peak_mb: Peak memory usage during processing (if measured)
        """
        self._check_daily_reset()

        record = VisionRecord(
            timestamp=datetime.now(),
            tier=tier,
            processing_time_ms=processing_time_ms,
            memory_peak_mb=memory_peak_mb,
            task_type=task_type,
            escalated=escalated,
            success=success,
            from_cache=from_cache
        )

        self._records.append(record)
        self._tier_counts[tier] += 1
        self._tier_times[tier].append(processing_time_ms)
        self._task_type_counts[task_type] += 1
        self._total_requests_today += 1

        if escalated:
            self._escalations_today += 1
        if from_cache:
            self._cache_hits_today += 1
        if memory_peak_mb > 0:
            self._memory_peaks.append(memory_peak_mb)
            if memory_peak_mb > self._max_memory_peak_today:
                self._max_memory_peak_today = memory_peak_mb

        # Keep only last 500 records to prevent memory growth
        if len(self._records) > 500:
            self._records = self._records[-500:]
        # Keep only last 100 processing times per tier
        for tier_key in self._tier_times:
            if len(self._tier_times[tier_key]) > 100:
                self._tier_times[tier_key] = self._tier_times[tier_key][-100:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive vision statistics.

        Returns:
            Dict with all vision metrics
        """
        self._check_daily_reset()

        if self._total_requests_today == 0:
            return {
                "available": True,
                "requests_today": 0,
                "avg_time_ms": 0,
                "tier_usage": {},
                "memory_peak_mb": 0.0,
                "escalation_rate": 0.0,
                "cache_hit_rate": 0.0,
                "task_breakdown": {},
                "date": str(self._daily_reset_date)
            }

        # Calculate average time per tier
        avg_times = {}
        for tier, times in self._tier_times.items():
            if times:
                avg_times[tier] = round(sum(times) / len(times), 1)

        # Overall average time
        all_times = [r.processing_time_ms for r in self._records]
        overall_avg = round(sum(all_times) / len(all_times), 1) if all_times else 0

        # Tier usage with percentages
        tier_usage = {}
        for tier, count in self._tier_counts.items():
            tier_usage[tier] = {
                "count": count,
                "percentage": round(count / self._total_requests_today * 100, 1),
                "avg_time_ms": avg_times.get(tier, 0)
            }

        # Task type breakdown
        task_breakdown = {}
        for task_type, count in self._task_type_counts.items():
            task_breakdown[task_type] = {
                "count": count,
                "percentage": round(count / self._total_requests_today * 100, 1)
            }

        # Last hour stats
        one_hour_ago = datetime.now() - timedelta(hours=1)
        last_hour_records = [r for r in self._records if r.timestamp > one_hour_ago]

        # Memory stats
        avg_memory = 0.0
        if self._memory_peaks:
            avg_memory = round(sum(self._memory_peaks) / len(self._memory_peaks), 1)

        return {
            "available": True,
            "requests_today": self._total_requests_today,
            "avg_time_ms": overall_avg,
            "tier_usage": tier_usage,
            "memory_peak_mb": round(self._max_memory_peak_today, 1),
            "memory_avg_mb": avg_memory,
            "escalation_rate": round(self._escalations_today / self._total_requests_today * 100, 1),
            "escalations_today": self._escalations_today,
            "cache_hit_rate": round(self._cache_hits_today / self._total_requests_today * 100, 1),
            "cache_hits_today": self._cache_hits_today,
            "task_breakdown": task_breakdown,
            "last_hour_requests": len(last_hour_records),
            "date": str(self._daily_reset_date),
            "timestamp": datetime.now().isoformat()
        }

    def get_summary_for_self(self) -> Dict[str, Any]:
        """
        Get a summary suitable for /api/self endpoint.

        Returns:
            Condensed stats dict for vision_stats field
        """
        self._check_daily_reset()

        if self._total_requests_today == 0:
            return {
                "requests_today": 0,
                "avg_time_ms": 0,
                "tier_usage": {},
                "memory_peak_mb": 0.0
            }

        # Calculate overall average time
        all_times = [r.processing_time_ms for r in self._records]
        overall_avg = round(sum(all_times) / len(all_times), 1) if all_times else 0

        # Simple tier usage counts
        tier_usage = dict(self._tier_counts)

        return {
            "requests_today": self._total_requests_today,
            "avg_time_ms": overall_avg,
            "tier_usage": tier_usage,
            "memory_peak_mb": round(self._max_memory_peak_today, 1)
        }


# Vision stats monitor singleton
_vision_stats_monitor: Optional[VisionStatsMonitor] = None


def get_vision_stats_monitor() -> VisionStatsMonitor:
    """Get or create vision stats monitor singleton."""
    global _vision_stats_monitor
    if _vision_stats_monitor is None:
        _vision_stats_monitor = VisionStatsMonitor()
    return _vision_stats_monitor


def record_vision_stats(
    tier: str,
    processing_time_ms: int,
    task_type: str = "unknown",
    escalated: bool = False,
    success: bool = True,
    from_cache: bool = False,
    memory_peak_mb: float = 0.0
):
    """
    Convenience function to record vision stats.

    Use this from vision processing functions to track usage.
    """
    monitor = get_vision_stats_monitor()
    monitor.record_vision_request(
        tier=tier,
        processing_time_ms=processing_time_ms,
        task_type=task_type,
        escalated=escalated,
        success=success,
        from_cache=from_cache,
        memory_peak_mb=memory_peak_mb
    )


def load_inventory():
    """Load the exhaustive project inventory."""
    if INVENTORY_FILE.exists():
        return json.load(open(INVENTORY_FILE))
    return {"projects": {}, "meta": {}}

try:
    from sam_enhanced import sam, load_projects as load_projects_old, load_memory, find_project, route
except ImportError:
    # Fallback if sam_enhanced doesn't exist
    def sam(query): return f"SAM received: {query}"
    def load_projects_old(): return {"projects": []}
    def load_memory(): return {"interactions": []}
    def find_project(q): return None
    def route(q): return ("local", "fallback")


def api_query(query: str, speak: bool = False) -> dict:
    """Process a query and return JSON response."""
    start = datetime.now()

    # Find project
    project = find_project(query)
    handler_type, handler = route(query)

    result = {
        "query": query,
        "project": project["name"] if project else None,
        "route": f"{handler_type}/{handler}",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        output = sam(query)
        result["success"] = True
        result["output"] = output

        # Optionally speak the response
        if speak and output:
            try:
                from voice_output import SAMVoice
                voice = SAMVoice()
                # Truncate long responses for speech
                speech_text = output[:500] if len(output) > 500 else output
                voice_result = voice.speak(speech_text)
                result["voice"] = {
                    "spoken": voice_result.get("success", False),
                    "audio_path": voice_result.get("audio_path"),
                }
            except Exception as ve:
                result["voice"] = {"spoken": False, "error": str(ve)}

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    result["duration_ms"] = (datetime.now() - start).total_seconds() * 1000
    return result


def api_projects() -> dict:
    """Get project list from exhaustive inventory."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Group by status with top projects
    by_status = {}
    for path, data in projects.items():
        status = data.get("status", "unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append({
            "path": path,
            "name": data.get("name", ""),
            "languages": data.get("languages", []),
            "lines": data.get("total_lines", 0),
            "importance": data.get("importance_score", 0),
            "starred": data.get("starred", False),
        })

    # Sort and limit
    for status in by_status:
        by_status[status].sort(key=lambda x: -x["importance"])
        by_status[status] = by_status[status][:25]

    return {
        "success": True,
        "total": len(projects),
        "by_status": {s: len([p for p, d in projects.items() if d.get("status") == s])
                      for s in ["active", "recent", "stale", "abandoned"]},
        "starred_count": sum(1 for d in projects.values() if d.get("starred")),
        "projects": by_status
    }


def api_memory() -> dict:
    """Get memory/history."""
    memory = load_memory()
    return {
        "success": True,
        "interactions": memory.get("interactions", [])[-20:],
        "count": len(memory.get("interactions", []))
    }


def api_status() -> dict:
    """Get SAM status with exhaustive inventory info."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Check MLX availability (Ollama decommissioned 2026-01-18)
    mlx_available = False
    sam_model_ready = False
    try:
        from cognitive.mlx_cognitive import MLXCognitiveEngine
        mlx_available = True
        sam_model_ready = True  # MLX models load on-demand
    except ImportError:
        pass

    # Count by status
    active = sum(1 for d in projects.values() if d.get("status") == "active")
    starred = sum(1 for d in projects.values() if d.get("starred"))

    # Get drives scanned
    drives = set()
    for p in projects.keys():
        if p.startswith("/Volumes/"):
            drives.add(p.split("/")[2])
        elif p.startswith("/Users/"):
            drives.add("local")

    return {
        "success": True,
        "project_count": len(projects),
        "active_projects": active,
        "starred_projects": starred,
        "mlx_available": mlx_available,
        "sam_model_ready": sam_model_ready,
        "style_profile_loaded": STYLE_FILE.exists(),
        "drives_scanned": list(drives),
        "last_updated": inv.get("meta", {}).get("generated_at", "unknown"),
        "memory_count": len(load_memory().get("interactions", []))
    }


def api_search(query: str) -> dict:
    """Search projects by name, path, or description."""
    inv = load_inventory()
    projects = inv.get("projects", {})
    query_lower = query.lower()

    results = []
    for path, data in projects.items():
        name = data.get("name", "").lower()
        desc = data.get("description", "").lower()
        tags = " ".join(data.get("tags", [])).lower()

        if query_lower in name or query_lower in path.lower() or query_lower in desc or query_lower in tags:
            results.append({
                "path": path,
                "name": data.get("name", ""),
                "status": data.get("status", "unknown"),
                "languages": data.get("languages", []),
                "lines": data.get("total_lines", 0),
                "importance": data.get("importance_score", 0),
                "starred": data.get("starred", False),
                "description": data.get("description", "")[:100],
            })

    results.sort(key=lambda x: -x["importance"])
    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": results[:50]
    }


def api_categories() -> dict:
    """Get project categories."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Category patterns
    patterns = {
        "sam_core": ["sam", "warp_tauri", "warp_core", "sam_brain"],
        "voice": ["rvc", "voice", "tts", "speech", "audio", "clone"],
        "face_avatar": ["face", "deca", "mica", "avatar", "body", "mesh"],
        "image_gen": ["comfy", "diffusion", "lora", "stable"],
        "video": ["video", "rife", "motion", "frame", "animation"],
        "ml": ["train", "model", "neural", "inference"],
        "stash_adult": ["stash", "adult", "performer"],
        "media": ["plex", "media", "gallery", "download"],
        "web": ["react", "vue", "frontend", "dashboard"],
        "api": ["api", "server", "backend", "fastapi"],
        "games": ["unity", "unreal", "game"],
        "ios": ["ios", "swift", "macos"],
        "automation": ["script", "pipeline", "workflow"],
    }

    categories = {cat: 0 for cat in patterns}
    categories["other"] = 0

    for path, data in projects.items():
        name = data.get("name", "").lower()
        path_lower = path.lower()
        matched = False

        for cat, keywords in patterns.items():
            if any(kw in name or kw in path_lower for kw in keywords):
                categories[cat] += 1
                matched = True
                break

        if not matched:
            categories["other"] += 1

    return {
        "success": True,
        "categories": categories,
        "total": len(projects)
    }


def api_starred() -> dict:
    """Get starred/favorite projects."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    starred = []
    for path, data in projects.items():
        if data.get("starred"):
            starred.append({
                "path": path,
                "name": data.get("name", ""),
                "status": data.get("status", "unknown"),
                "languages": data.get("languages", []),
                "lines": data.get("total_lines", 0),
                "importance": data.get("importance_score", 0),
                "description": data.get("description", "")[:100],
            })

    starred.sort(key=lambda x: -x["importance"])
    return {
        "success": True,
        "count": len(starred),
        "projects": starred
    }


def api_speak(text: str, voice: str = None) -> dict:
    """Speak text using TTS."""
    try:
        from voice_output import SAMVoice
        sam_voice = SAMVoice()

        if voice:
            sam_voice.set_voice(voice)

        result = sam_voice.speak(text)
        return {
            "success": result.get("success", False),
            "text": text,
            "audio_path": result.get("audio_path"),
            "voice": result.get("voice"),
            "engine": result.get("engine"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def api_voices() -> dict:
    """List available voices."""
    try:
        from voice_output import SAMVoice
        sam_voice = SAMVoice()
        voices = sam_voice.list_voices()

        # Filter to English voices
        english = [v for v in voices if v.get("locale", "").startswith("en")]

        return {
            "success": True,
            "voices": english,
            "current": sam_voice.config.voice,
            "engine": sam_voice.config.engine,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ SAM Intelligence API ============

def get_training_stats() -> dict:
    """Get comprehensive training statistics for /api/self endpoint.

    Returns training pipeline status including:
    - model_version: Current deployed model version
    - last_training: Details of last training run
    - training_data: Training data statistics
    - evaluation_metrics: Model evaluation results
    - deployment_status: Deployment and rollback info
    """
    try:
        # Get deployment stats
        from model_deployment import get_deployer
        deployer = get_deployer()
        deployment_stats = deployer.get_deployment_stats()

        # Get training pipeline stats
        from training_pipeline import TrainingPipeline
        pipeline = TrainingPipeline()
        pipeline_stats = pipeline.stats()

        # Get last training run details
        last_run = None
        if pipeline.runs:
            run = pipeline.runs[-1]
            last_run = {
                "run_id": run.run_id,
                "start_time": run.start_time,
                "samples_count": run.samples_count,
                "status": run.status,
                "metrics": run.metrics,
            }

        # Get training data stats
        training_data_stats = {
            "total_samples": pipeline_stats.get("total_samples", 0),
            "min_for_training": pipeline_stats.get("min_for_training", 100),
            "ready_to_train": pipeline_stats.get("ready_to_train", False),
        }

        # Get distillation contribution
        distillation_db = get_distillation_db()
        distillation_contribution = 0
        if distillation_db:
            try:
                dist_stats = distillation_db.get_stats()
                distillation_contribution = dist_stats.get("approved_examples", 0)
            except:
                pass

        training_data_stats["distilled_samples"] = distillation_contribution

        return {
            "available": True,
            "model_version": deployment_stats.get("current_version"),
            "deployed_at": deployment_stats.get("current_deployed_at"),
            "last_training": last_run,
            "training_data": training_data_stats,
            "evaluation_metrics": last_run["metrics"] if last_run else {},
            "deployment": {
                "total_versions": deployment_stats.get("total_versions", 0),
                "rollback_available": deployment_stats.get("rollback_available", False),
                "canary_active": deployment_stats.get("canary_active", False),
                "canary_traffic_pct": deployment_stats.get("canary_traffic_pct", 0),
                "base_model": deployment_stats.get("base_model", "unknown"),
            },
            "mlx_available": pipeline_stats.get("mlx_available", False),
            "available_models": pipeline_stats.get("available_models", 0),
            "completed_runs": pipeline_stats.get("completed_runs", 0),
        }
    except ImportError as e:
        return {
            "available": False,
            "error": f"Training modules not available: {str(e)}"
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


def api_self() -> dict:
    """SAM explains itself - self-awareness endpoint.

    Returns comprehensive self-status including:
    - explanation: SAM's self-description
    - status: Current operational status
    - distillation: Knowledge distillation statistics
    - context_stats: Compression monitoring stats (Phase 2.3.6)
    - vision_stats: Vision processing statistics (Phase 3.2.6)
    - training_stats: Training pipeline and model deployment stats (Phase 5.2.10)
    """
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        explanation = sam.explain_myself()
        status = sam.get_self_status()

        # Get distillation stats (always try, even if main intelligence works)
        distillation_stats = get_distillation_stats()

        # Get compression/context stats (Phase 2.3.6)
        context_stats = None
        try:
            monitor = get_compression_monitor()
            context_stats = monitor.get_summary_for_self()
        except Exception:
            context_stats = {
                "avg_compression": 1.0,
                "tokens_saved_today": 0,
                "section_usage": {}
            }

        # Get vision stats (Phase 3.2.6)
        vision_stats = None
        try:
            vision_monitor = get_vision_stats_monitor()
            vision_stats = vision_monitor.get_summary_for_self()
        except Exception:
            vision_stats = {
                "requests_today": 0,
                "avg_time_ms": 0,
                "tier_usage": {},
                "memory_peak_mb": 0.0
            }

        # Get training stats (Phase 5.2.10)
        training_stats = get_training_stats()

        return {
            "success": True,
            "explanation": explanation,
            "status": status,
            "distillation": distillation_stats,
            "context_stats": context_stats,
            "vision_stats": vision_stats,
            "training_stats": training_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_suggest(limit: int = 5) -> dict:
    """Get top improvement suggestions (cached for speed)."""
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        suggestions = sam.get_top_suggestions_fast(limit)
        return {
            "success": True,
            "count": len(suggestions),
            "suggestions": suggestions,
            "cached": True,  # These are from cache for fast response
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_proactive() -> dict:
    """Get proactive suggestions - what SAM noticed on its own."""
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        proactive = sam.get_proactive_suggestions()
        return {
            "success": True,
            "count": len(proactive),
            "suggestions": proactive,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_learning() -> dict:
    """Get what SAM has learned from past improvements."""
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        # Get learning patterns from the intelligence layer
        # Access internal learning dict and also get formatted insights
        raw_patterns = getattr(sam, 'learning', {})
        insights = sam.get_learned_insights()

        learning_summary = []
        for key, pattern in raw_patterns.items():
            total = pattern.success_count + pattern.failure_count
            learning_summary.append({
                "category": key,
                "pattern_type": pattern.pattern_type,
                "pattern_value": pattern.pattern_value,
                "total_samples": total,
                "successes": pattern.success_count,
                "failures": pattern.failure_count,
                "success_rate": f"{pattern.success_rate:.0%}",
                "avg_impact": f"{pattern.avg_impact:.2f}",
                "confidence": f"{pattern.confidence:.0%}",
            })

        # Sort by total samples (most experience first)
        learning_summary.sort(key=lambda x: -x["total_samples"])

        return {
            "success": True,
            "patterns": learning_summary,
            "insights": insights,
            "total_learned": sum(p["total_samples"] for p in learning_summary),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_feedback(improvement_id: str, success: bool, impact: float = 0.5, lessons: str = "") -> dict:
    """Record feedback for an improvement."""
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        sam.learn_from_feedback(improvement_id, success, impact, lessons)
        return {
            "success": True,
            "improvement_id": improvement_id,
            "recorded": True,
            "message": f"Learned from {'successful' if success else 'failed'} improvement",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_scan() -> dict:
    """Trigger an improvement scan."""
    try:
        from improvement_detector import ImprovementDetector
        detector = ImprovementDetector()

        # Quick scan (don't do full scan via API - too slow)
        improvements = detector.detect_all(quick=True)

        return {
            "success": True,
            "count": len(improvements),
            "improvements": [
                {
                    "id": imp.get("id", ""),
                    "type": imp.get("type", ""),
                    "project": imp.get("project_id", ""),
                    "priority": imp.get("priority", 3),
                    "description": imp.get("description", "")[:200],
                }
                for imp in improvements[:20]  # Limit for API response
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_think(query: str) -> dict:
    """Have SAM think about a query using its intelligence."""
    sam = get_sam_intelligence()
    if not sam:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        start = datetime.now()
        response = sam.think(query)
        duration = (datetime.now() - start).total_seconds() * 1000

        return {
            "success": True,
            "query": query,
            "response": response,
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_orchestrate(message: str, auto_escalate: bool = True) -> dict:
    """Process message through SAM with escalation handling.

    Flow:
    1. Evaluate message complexity
    2. Try SAM cognitive system first
    3. Evaluate response confidence
    4. Auto-escalate to Claude if confidence is low (when auto_escalate=True)
    5. Log escalations for future learning

    Routes to: VOICE, IMAGE, DATA, TERMINAL, PROJECT, IMPROVE, CODE, ROLEPLAY, REASON, CHAT
    """
    try:
        start = datetime.now()

        # Use escalation handler for intelligent routing
        try:
            from escalation_handler import process_request, EscalationReason
            result = process_request(message, auto_escalate=auto_escalate)

            duration = (datetime.now() - start).total_seconds() * 1000

            return {
                "success": True,
                "message": message,
                "response": result.content,
                "confidence": result.confidence,
                "provider": result.provider,
                "escalated": result.provider == "claude",
                "escalation_reason": result.escalation_reason.value if result.escalation_reason != EscalationReason.NONE else None,
                "route": "escalation_handler",
                "model": "mlx-cognitive" if result.provider == "sam" else "claude-browser",
                "duration_ms": duration,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            # Fallback to direct orchestrator if escalation handler unavailable
            from orchestrator import orchestrate
            result = orchestrate(message)
            duration = (datetime.now() - start).total_seconds() * 1000

            return {
                "success": True,
                "message": message,
                **result,
                "duration_ms": duration,
                "timestamp": datetime.now().isoformat(),
            }
    except ImportError as e:
        return {"success": False, "error": f"Orchestrator not available: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ COGNITIVE SYSTEM API ============

# Cognitive orchestrator singleton
_cognitive_orchestrator = None

def get_cognitive_orchestrator():
    """Lazy-load cognitive orchestrator singleton."""
    global _cognitive_orchestrator
    if _cognitive_orchestrator is None:
        try:
            from cognitive import create_cognitive_orchestrator
            _cognitive_orchestrator = create_cognitive_orchestrator(
                db_path="/Volumes/David External/sam_memory/cognitive",
                retrieval_paths=["/Volumes/David External/sam_memory"]
            )
        except Exception as e:
            print(f"Warning: Could not load cognitive system: {e}", file=sys.stderr)
            return None
    return _cognitive_orchestrator


def api_cognitive_process(query: str, user_id: str = "default") -> dict:
    """Process query through cognitive system with MLX inference."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        _update_activity()  # Track activity for idle timeout
        start = datetime.now()
        result = orchestrator.process(query, user_id=user_id)
        duration = (datetime.now() - start).total_seconds() * 1000
        _update_activity()  # Update again after processing

        return {
            "success": True,
            "query": query,
            "response": result.response,
            "confidence": result.confidence,
            "mood": result.mood,
            "model_used": result.metadata.get("model_used", "unknown"),
            "escalated": result.metadata.get("escalated", False),
            "escalation_recommended": result.metadata.get("escalation_recommended", False),
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_state() -> dict:
    """Get cognitive system state."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        state = orchestrator.get_state()
        return {
            "success": True,
            "state": state,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_mood() -> dict:
    """Get current emotional state."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        emotional_state = orchestrator.emotional.get_state()
        return {
            "success": True,
            "mood": emotional_state,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_resources() -> dict:
    """Get current system resource state."""
    try:
        from cognitive.resource_manager import ResourceManager
        manager = ResourceManager()
        snapshot = manager.get_snapshot()
        stats = manager.get_stats()

        # Get model memory usage if cognitive system is loaded
        model_memory_mb = 0.0
        model_loaded = None
        orchestrator = get_cognitive_orchestrator()
        if orchestrator and hasattr(orchestrator, 'mlx_engine'):
            model_memory_mb = orchestrator.mlx_engine.get_memory_usage_mb()
            model_loaded = orchestrator.mlx_engine._current_model_key

        return {
            "success": True,
            "resources": snapshot.to_dict(),
            "model": {
                "loaded": model_loaded,
                "memory_mb": model_memory_mb,
                "idle_seconds": _get_idle_seconds(),
            },
            "stats": {
                "total_requests": stats.get('total_requests', 0),
                "rejected_requests": stats.get('rejected_requests', 0),
                "completed_requests": stats.get('completed_requests', 0),
                "timeouts": stats.get('timeouts', 0),
            },
            "limits": {
                "max_tokens": manager.get_max_tokens_for_level(),
                "can_perform_heavy_op": manager.can_perform_heavy_operation()[0],
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_context_stats() -> dict:
    """
    Get compression statistics for context management.

    Phase 2.3.6: Returns comprehensive compression monitoring data including:
    - Tokens saved per request and cumulative
    - Average compression ratios
    - Section-by-section usage patterns
    - Budget overrun detection
    - Efficiency scoring

    Returns:
        dict with compression statistics
    """
    try:
        monitor = get_compression_monitor()
        stats = monitor.get_stats()

        # Also try to get context budget stats if available
        try:
            from context_budget import ContextBudget
            budget = ContextBudget()
            allocation_stats = budget.get_allocation_stats()
            stats["budget_allocations"] = allocation_stats
        except Exception:
            stats["budget_allocations"] = None

        # Try to get compression engine stats if available
        try:
            from cognitive.compression import ContextualCompressor
            compressor = ContextualCompressor()
            last_stats = compressor.get_last_stats()
            if last_stats:
                stats["last_compression"] = {
                    "original_tokens": last_stats.original_tokens,
                    "compressed_tokens": last_stats.compressed_tokens,
                    "ratio": round(last_stats.ratio, 3),
                    "query_type": last_stats.query_type,
                    "importance_threshold": round(last_stats.importance_threshold, 3)
                }
        except Exception:
            stats["last_compression"] = None

        return {
            "success": True,
            **stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Track last activity for idle timeout
_last_activity_time = None
_idle_watcher_running = False
_idle_timeout_seconds = 300  # 5 minutes

def _update_activity():
    """Update the last activity timestamp."""
    global _last_activity_time
    _last_activity_time = datetime.now()

def _get_idle_seconds() -> float:
    """Get seconds since last activity."""
    global _last_activity_time
    if _last_activity_time is None:
        return 0.0
    return (datetime.now() - _last_activity_time).total_seconds()

def _start_idle_watcher():
    """Start background thread to auto-unload model after idle timeout."""
    global _idle_watcher_running
    if _idle_watcher_running:
        return

    import threading
    import time

    def idle_watcher():
        global _idle_watcher_running
        _idle_watcher_running = True
        while _idle_watcher_running:
            time.sleep(60)  # Check every minute
            idle_secs = _get_idle_seconds()
            if idle_secs > _idle_timeout_seconds:
                # Check if model is loaded
                try:
                    orchestrator = get_cognitive_orchestrator()
                    if orchestrator and hasattr(orchestrator, 'mlx_engine'):
                        engine = orchestrator.mlx_engine
                        if engine._current_model_key is not None:
                            print(f"[Idle Watcher] Auto-unloading after {idle_secs:.0f}s idle")
                            engine.unload_model()
                except Exception as e:
                    print(f"[Idle Watcher] Error: {e}")

    thread = threading.Thread(target=idle_watcher, daemon=True)
    thread.start()
    print("[Idle Watcher] Started (5 min timeout)")


def api_unload_model() -> dict:
    """Unload the MLX model to free memory."""
    try:
        orchestrator = get_cognitive_orchestrator()
        if not orchestrator:
            return {"success": False, "error": "Cognitive system not available"}

        if not hasattr(orchestrator, 'mlx_engine'):
            return {"success": False, "error": "MLX engine not available"}

        engine = orchestrator.mlx_engine
        was_loaded = engine._current_model_key

        if was_loaded is None:
            return {
                "success": True,
                "message": "No model was loaded",
                "freed_mb": 0,
                "timestamp": datetime.now().isoformat(),
            }

        memory_before = engine.get_memory_usage_mb()
        engine.unload_model()

        return {
            "success": True,
            "message": f"Unloaded model {was_loaded}",
            "freed_mb": memory_before,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback(
    response_id: str,
    helpful: bool = True,
    comment: str = "",
    query: str = "",
    response: str = "",
    user_id: str = "default",
    session_id: str = "default",
    # New Phase 1.2 parameters
    feedback_type: str = "rating",
    rating: int = None,
    correction: str = None,
    correction_type: str = None,
    what_was_wrong: str = None,
    preferred_response: str = None,
    comparison_basis: str = None,
    flag_type: str = None,
    flag_details: str = None,
    domain: str = "general",
    response_confidence: float = None,
    escalated_to_claude: bool = False,
    response_timestamp: float = None,
    conversation_context: str = None,
) -> dict:
    """Record user feedback on a response for learning.

    Phase 1.2 enhanced version with full feedback schema support.

    Supports multiple feedback types:
    - rating: Simple thumbs up/down (rating=1 or rating=-1)
    - correction: User provides the correct answer
    - preference: User provides a preferred alternative
    - flag: User flags problematic content

    Args:
        response_id: ID of the response being rated (required)
        helpful: Legacy parameter - maps to rating=1 if True, rating=-1 if False
        comment: Legacy parameter - maps to correction if feedback_type is correction
        query: Original user query
        response: SAM's original response
        user_id: User identifier
        session_id: Session identifier for grouping
        feedback_type: Type of feedback (rating, correction, preference, flag)
        rating: For rating type: 1 (thumbs up) or -1 (thumbs down)
        correction: For correction type: the correct answer
        correction_type: full_replacement, partial_fix, addition, clarification
        what_was_wrong: Explanation of what was wrong
        preferred_response: For preference type: user's preferred alternative
        comparison_basis: Why the preferred response is better
        flag_type: For flag type: harmful, incorrect, off_topic, unhelpful, etc.
        flag_details: Additional details for flag
        domain: Domain classification (code, reasoning, creative, factual, planning)
        response_confidence: SAM's confidence when responding
        escalated_to_claude: Whether this was escalated to Claude
        response_timestamp: When the original response was generated
        conversation_context: Recent conversation history

    Returns:
        dict with success status and feedback_id
    """
    try:
        feedback_id = None

        # Normalize legacy parameters to new schema
        if rating is None:
            rating = 1 if helpful else -1

        if correction is None and comment:
            correction = comment
            if feedback_type == "rating" and correction:
                feedback_type = "correction"

        # Record in FeedbackDB (Phase 1.2)
        fb_db = get_feedback_db()
        if fb_db:
            try:
                feedback_id = fb_db.save_feedback(
                    response_id=response_id,
                    session_id=session_id,
                    original_query=query,
                    original_response=response,
                    feedback_type=feedback_type,
                    rating=rating,
                    correction=correction,
                    correction_type=correction_type,
                    what_was_wrong=what_was_wrong,
                    preferred_response=preferred_response,
                    comparison_basis=comparison_basis,
                    flag_type=flag_type,
                    flag_details=flag_details,
                    domain=domain,
                    response_confidence=response_confidence,
                    escalated_to_claude=escalated_to_claude,
                    user_id=user_id,
                    response_timestamp=response_timestamp,
                    conversation_context=conversation_context,
                )
            except Exception as e:
                print(f"Warning: FeedbackDB save failed: {e}", file=sys.stderr)

        # Record in intelligence core (Phase 1 - legacy)
        try:
            from intelligence_core import get_intelligence_core
            core = get_intelligence_core()

            legacy_rating = "helpful" if rating == 1 else ("corrected" if correction else "not_helpful")
            core.record_feedback(
                response_id=response_id,
                query=query,
                response=response,
                rating=legacy_rating,
                correction=correction if correction else None,
                user_id=user_id
            )
        except ImportError:
            pass

        # Also record in escalation learner (legacy)
        try:
            from escalation_learner import EscalationLearner
            learner = EscalationLearner()
            learner.record_local_attempt(
                query=response_id,
                task_type="feedback",
                confidence=1.0 if rating == 1 else 0.0,
                success=rating == 1
            )
        except:
            pass

        return {
            "success": True,
            "feedback_id": feedback_id,
            "response_id": response_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "helpful": rating == 1,
            "correction_recorded": bool(correction),
            "recorded": True,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback_stats() -> dict:
    """Get feedback statistics.

    Returns comprehensive feedback statistics including:
    - total_feedback: Total captured feedback
    - by_type: Breakdown by feedback type
    - sentiment: Positive/negative breakdown
    - processed: Count of processed vs pending
    - quality: Average quality weight
    - recent_24h: Count in last 24 hours
    """
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        stats = fb_db.get_feedback_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback_recent(
    limit: int = 20,
    domain: str = None,
    feedback_type: str = None,
    session_id: str = None
) -> dict:
    """Get recent feedback entries for dashboard.

    Args:
        limit: Maximum number of entries to return
        domain: Filter by domain (code, reasoning, creative, factual, planning)
        feedback_type: Filter by type (rating, correction, preference, flag)
        session_id: Filter by session

    Returns:
        dict with recent feedback entries
    """
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        recent = fb_db.get_recent_feedback(
            limit=limit,
            domain=domain,
            feedback_type=feedback_type,
            session_id=session_id
        )

        return {
            "success": True,
            "count": len(recent),
            "feedback": recent,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_notifications() -> dict:
    """Get proactive feedback notifications for the UI.

    Phase 1.2.8: Returns feedback awareness stats including:
    - daily_corrections: Number of corrections today
    - daily_negative: Number of negative ratings today
    - unprocessed_count: Feedback items ready for training
    - declining_domains: Domains with accuracy drops
    - alerts: Active notification messages with urgency levels

    Alerts are generated when:
    - Corrections reach 3+ in a day
    - Negative feedback reaches 5+ in a day
    - Unprocessed items reach 5+ (training ready)
    - Domain accuracy drops significantly
    """
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        # Get all notification data from feedback system
        data = fb_db.get_feedback_notifications_data()

        return {
            "success": True,
            "daily_corrections": data.get("daily_corrections", 0),
            "daily_negative": data.get("daily_negative", 0),
            "unprocessed_count": data.get("unprocessed_count", 0),
            "declining_domains": data.get("declining_domains", []),
            "alerts": data.get("threshold_alerts", []),
            "alert_count": len(data.get("threshold_alerts", [])),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_feedback_dashboard() -> dict:
    """Get comprehensive feedback dashboard data for review UI.

    Phase 1.2.9: Returns all data needed for the feedback review dashboard:
    - summary: Today's feedback summary (positive/negative/corrections)
    - domain_breakdown: Accuracy per domain with sample counts
    - recent_corrections: Recent corrections needing review
    - training_status: Training data generation status
    - trends: 7-day accuracy trends per domain

    This endpoint powers the web dashboard for feedback review.
    """
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        # Get comprehensive dashboard data
        data = fb_db.get_dashboard_data()

        return {
            "success": True,
            "summary": data.get("summary", {}),
            "domain_breakdown": data.get("domain_breakdown", {}),
            "recent_corrections": data.get("recent_corrections", []),
            "training_status": data.get("training_status", {}),
            "trends": data.get("trends", {}),
            "generated_at": data.get("generated_at"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_intelligence_stats() -> dict:
    """Get intelligence core statistics (distillation, feedback, memory)."""
    try:
        from intelligence_core import get_intelligence_core
        core = get_intelligence_core()
        stats = core.get_stats()

        return {
            "success": True,
            "intelligence": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_user_facts(user_id: str = "david") -> dict:
    """Get facts known about a user."""
    try:
        from intelligence_core import get_intelligence_core
        core = get_intelligence_core()
        facts = core.get_user_facts(user_id)
        context = core.get_context_for_user(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "facts": facts,
            "context_snippet": context[:500] if context else "",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_remember_fact(user_id: str, fact: str, category: str = "preference") -> dict:
    """Remember a fact about a user."""
    try:
        from intelligence_core import get_intelligence_core, FactCategory
        core = get_intelligence_core()

        try:
            cat = FactCategory(category)
        except ValueError:
            cat = FactCategory.PREFERENCE

        fact_id = core.remember_fact(user_id, fact, cat, source="api")

        return {
            "success": True,
            "fact_id": fact_id,
            "user_id": user_id,
            "fact": fact,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_fact_context(user_id: str = "david") -> dict:
    """Get formatted fact context for prompt injection (Phase 1.3.6).

    This is the context string that gets injected into SAM's prompts
    so it knows facts about the user.
    """
    try:
        from fact_memory import get_fact_memory, build_user_context
        fm = get_fact_memory()

        # Get the formatted context using build_user_context
        context = build_user_context(user_id, min_confidence=0.3)
        stats = fm.get_stats()

        # Get facts for count by category
        facts = fm.get_facts(user_id, min_confidence=0.3)
        categories = {}
        for fact in facts:
            cat = fact.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "success": True,
            "user_id": user_id,
            "context_string": context,
            "fact_count": len(facts),
            "categories": categories,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ Fact Management API (Phase 1.3.9) ============

def api_facts_list(user_id: str = "david", category: str = None, min_confidence: float = 0.0, limit: int = 50) -> dict:
    """List facts for a user with optional filtering.

    Args:
        user_id: User identifier
        category: Optional category filter (preferences, biographical, projects, skills, corrections, etc.)
        min_confidence: Minimum confidence threshold (0.0-1.0)
        limit: Maximum number of facts to return

    Returns:
        List of facts with metadata
    """
    try:
        from fact_memory import get_fact_db

        db = get_fact_db()
        facts = db.get_facts(
            user_id=user_id,
            category=category,
            min_confidence=min_confidence,
            limit=limit,
        )

        facts_list = []
        for fact in facts:
            facts_list.append({
                "fact_id": fact.fact_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "source": fact.source,
                "reinforcement_count": fact.reinforcement_count,
                "first_seen": fact.first_seen,
                "last_reinforced": fact.last_reinforced,
                "is_active": fact.is_active,
            })

        return {
            "success": True,
            "user_id": user_id,
            "category_filter": category,
            "min_confidence": min_confidence,
            "count": len(facts_list),
            "facts": facts_list,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_add(fact: str, category: str, user_id: str = "david", source: str = "explicit", confidence: float = None) -> dict:
    """Add a new fact about a user.

    Args:
        fact: The fact text to remember
        category: Category (preferences, biographical, projects, skills, corrections, relationships, context, system)
        user_id: User identifier
        source: Fact source (explicit, conversation, correction, inferred, system)
        confidence: Optional confidence override (defaults to source-based confidence)

    Returns:
        The created or reinforced fact
    """
    try:
        from fact_memory import get_fact_db

        db = get_fact_db()
        saved_fact = db.save_fact(
            fact=fact,
            category=category,
            source=source,
            confidence=confidence,
            user_id=user_id,
        )

        return {
            "success": True,
            "action": "created" if saved_fact.reinforcement_count == 1 else "reinforced",
            "fact_id": saved_fact.fact_id,
            "fact": saved_fact.fact,
            "category": saved_fact.category,
            "confidence": round(saved_fact.confidence, 3),
            "source": saved_fact.source,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_remove(fact_id: str) -> dict:
    """Remove (deactivate) a fact by ID.

    Args:
        fact_id: The fact ID to remove

    Returns:
        Result of the removal operation
    """
    try:
        from fact_memory import get_fact_db

        db = get_fact_db()

        # First check if fact exists
        fact = db.get_fact(fact_id)
        if not fact:
            return {
                "success": False,
                "error": f"Fact with ID '{fact_id}' not found",
            }

        # Deactivate the fact (soft delete)
        success = db.deactivate_fact(fact_id, reason="removed_via_api")

        return {
            "success": success,
            "fact_id": fact_id,
            "fact": fact.fact,
            "category": fact.category,
            "action": "deactivated",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_search(query: str, user_id: str = "david", limit: int = 10) -> dict:
    """Search facts by text content.

    Args:
        query: Search query string
        user_id: User identifier
        limit: Maximum results to return

    Returns:
        Matching facts
    """
    try:
        from fact_memory import get_fact_db

        db = get_fact_db()
        facts = db.search_facts(
            query=query,
            user_id=user_id,
            limit=limit,
        )

        facts_list = []
        for fact in facts:
            facts_list.append({
                "fact_id": fact.fact_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "source": fact.source,
                "reinforcement_count": fact.reinforcement_count,
            })

        return {
            "success": True,
            "query": query,
            "user_id": user_id,
            "count": len(facts_list),
            "facts": facts_list,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_get(fact_id: str) -> dict:
    """Get a single fact by ID.

    Args:
        fact_id: The fact ID

    Returns:
        Full fact details
    """
    try:
        from fact_memory import get_fact_db

        db = get_fact_db()
        fact = db.get_fact(fact_id)

        if not fact:
            return {
                "success": False,
                "error": f"Fact with ID '{fact_id}' not found",
            }

        return {
            "success": True,
            "fact": {
                "fact_id": fact.fact_id,
                "user_id": fact.user_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "initial_confidence": round(fact.initial_confidence, 3),
                "source": fact.source,
                "source_context": fact.source_context,
                "first_seen": fact.first_seen,
                "last_reinforced": fact.last_reinforced,
                "last_accessed": fact.last_accessed,
                "reinforcement_count": fact.reinforcement_count,
                "contradiction_count": fact.contradiction_count,
                "decay_rate": fact.decay_rate,
                "decay_floor": fact.decay_floor,
                "is_active": fact.is_active,
                "metadata": fact.metadata,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_project_context(path: str = ".") -> dict:
    """Get project context for a path."""
    try:
        import os
        from project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(path))
        if not project:
            return {"success": True, "project": None, "message": "No project detected"}

        todos = ctx.get_project_todos(project.id, limit=5)
        session = ctx.get_last_session(project.id)
        context_text = ctx.get_project_context(project)

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "category": project.category,
                "tech_stack": project.tech_stack,
                "last_accessed": project.last_accessed.isoformat(),
            },
            "todos": todos,
            "last_session": {
                "working_on": session.working_on,
                "recent_files": session.recent_files,
                "timestamp": session.timestamp.isoformat(),
            } if session else None,
            "context_for_prompt": context_text,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_save_session(project_path: str, working_on: str = "", notes: str = "") -> dict:
    """Save session state for a project."""
    try:
        import os
        from project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(project_path))
        if not project:
            return {"success": False, "error": "No project detected at path"}

        ctx.save_session_state(
            project_id=project.id,
            working_on=working_on,
            notes=notes
        )

        return {
            "success": True,
            "project": project.name,
            "working_on": working_on,
            "saved": True,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_recent_projects(limit: int = 5) -> dict:
    """Get recently accessed projects."""
    try:
        from project_context import get_project_context
        ctx = get_project_context()

        projects = ctx.get_recent_projects(limit)

        return {
            "success": True,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "path": p.path,
                    "category": p.category,
                    "tech_stack": p.tech_stack,
                    "last_accessed": p.last_accessed.isoformat(),
                }
                for p in projects
            ],
            "count": len(projects),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_project_current() -> dict:
    """Get the current project based on active terminal/IDE working directory.

    Phase 2.1.9: Returns current project info for GUI header display.
    Uses the project watcher if available, otherwise detects from cwd.

    Returns:
        dict with:
        - project: Project info (name, type, status, icon) or None
        - detected_from: How the project was detected
        - timestamp: ISO timestamp
    """
    try:
        from project_context import get_project_watcher, get_current_project, SSOT_PROJECTS

        # Try the watcher first (it tracks the most recent project switch)
        watcher = get_project_watcher(auto_start=False)
        current_project = None
        detected_from = "none"

        if watcher and watcher._current_project:
            current_project = watcher._current_project
            detected_from = "watcher"
        else:
            # Fallback to detecting from cwd
            current_project = get_current_project()
            if current_project:
                detected_from = "cwd"

        if not current_project:
            return {
                "success": True,
                "project": None,
                "message": "No project detected",
                "detected_from": detected_from,
                "timestamp": datetime.now().isoformat(),
            }

        # Map project type to icon (SF Symbol names for SwiftUI)
        type_icons = {
            "python": "chevron.left.forwardslash.chevron.right",
            "swift": "swift",
            "swiftui": "swift",
            "rust": "gearshape.2.fill",
            "tauri": "macwindow",
            "typescript": "t.square.fill",
            "javascript": "j.square.fill",
            "unity": "gamecontroller.fill",
            "comfyui": "photo.artframe",
            "docker": "shippingbox.fill",
            "shell": "terminal.fill",
        }

        # Get the project type
        project_type = getattr(current_project, 'type', 'unknown')
        if hasattr(current_project, 'tech_stack') and current_project.tech_stack:
            project_type = current_project.tech_stack[0] if isinstance(current_project.tech_stack, list) else current_project.tech_stack

        # Normalize type
        project_type_lower = project_type.lower() if project_type else "unknown"
        icon = type_icons.get(project_type_lower, "folder.fill")

        # Get status
        status = getattr(current_project, 'status', 'active')

        return {
            "success": True,
            "project": {
                "name": current_project.name,
                "path": getattr(current_project, 'path', None),
                "type": project_type,
                "status": status,
                "icon": icon,
                "tier": getattr(current_project, 'tier', None),
            },
            "detected_from": detected_from,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "project": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def api_project_todos(path: str = ".", limit: int = 10) -> dict:
    """Get TODOs for a project."""
    try:
        import os
        from project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(path))
        if not project:
            return {"success": True, "project": None, "todos": [], "message": "No project detected"}

        # Scan for TODOs first (updates database)
        found = ctx.scan_for_todos(project.path, project.id)

        # Get TODOs
        todos = ctx.get_project_todos(project.id, limit)

        return {
            "success": True,
            "project": project.name,
            "todos": todos,
            "count": len(todos),
            "scanned": found,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_index(path: str, project_id: str = "default", force: bool = False) -> dict:
    """Index code files for a project."""
    try:
        import os
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        stats = indexer.index_project(os.path.abspath(path), project_id, force)

        return {
            "success": True,
            "project_id": project_id,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_search(query: str, project_id: str = None, entity_type: str = None, limit: int = 10) -> dict:
    """Search indexed code."""
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        results = indexer.search(query, project_id, entity_type, limit)

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "name": r.name,
                    "type": r.type,
                    "signature": r.signature,
                    "docstring": r.docstring[:200] if r.docstring else None,
                    "file": r.file_path.split("/")[-1],
                    "file_path": r.file_path,
                    "line": r.line_number,
                }
                for r in results
            ],
            "count": len(results),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_stats(project_id: str = None) -> dict:
    """Get code index statistics."""
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        stats = indexer.get_stats(project_id)

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ Index Management API (Phase 2.2.10) ============

# File watcher singleton for index watching
_index_watcher = None
_watcher_observer = None


def api_index_status() -> dict:
    """Get comprehensive index statistics.

    Returns:
        Index stats including total entities, files indexed,
        by type, by project, and last update time.
    """
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        # Get overall stats
        stats = indexer.get_stats()

        # Get per-project breakdown
        import sqlite3
        conn = sqlite3.connect(indexer.db_path)
        cur = conn.cursor()

        # Get unique projects
        cur.execute("SELECT DISTINCT project_id FROM code_entities")
        projects = [row[0] for row in cur.fetchall()]

        # Get per-project entity counts
        project_stats = {}
        for project_id in projects:
            cur.execute(
                "SELECT type, COUNT(*) FROM code_entities WHERE project_id = ? GROUP BY type",
                (project_id,)
            )
            project_stats[project_id] = {
                "by_type": {row[0]: row[1] for row in cur.fetchall()}
            }
            cur.execute(
                "SELECT COUNT(*) FROM indexed_files WHERE project_id = ?",
                (project_id,)
            )
            project_stats[project_id]["files_indexed"] = cur.fetchone()[0]

            # Get last indexed time
            cur.execute(
                "SELECT MAX(indexed_at) FROM indexed_files WHERE project_id = ?",
                (project_id,)
            )
            last_indexed = cur.fetchone()[0]
            if last_indexed:
                project_stats[project_id]["last_indexed"] = datetime.fromtimestamp(last_indexed).isoformat()

        conn.close()

        # Get watcher status
        global _watcher_observer
        watcher_running = _watcher_observer is not None and _watcher_observer.is_alive()

        return {
            "success": True,
            "total_entities": stats.get("total_entities", 0),
            "files_indexed": stats.get("files_indexed", 0),
            "by_type": stats.get("by_type", {}),
            "projects": project_stats,
            "project_count": len(projects),
            "db_path": str(indexer.db_path),
            "watcher_running": watcher_running,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_build(project_path: str, project_id: str = None, force: bool = False) -> dict:
    """Build or rebuild the code index for a project.

    Args:
        project_path: Path to the project directory
        project_id: Optional project identifier (defaults to directory name)
        force: Force re-indexing even if files haven't changed

    Returns:
        Indexing statistics
    """
    try:
        import os
        from pathlib import Path
        from cognitive.code_indexer import get_code_indexer

        indexer = get_code_indexer()
        abs_path = os.path.abspath(project_path)

        # Default project_id to directory name if not provided
        if not project_id:
            project_id = Path(abs_path).name

        # Check if path exists
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path not found: {abs_path}"
            }

        # Run indexing
        start_time = datetime.now()
        stats = indexer.index_project(abs_path, project_id, force)
        duration = (datetime.now() - start_time).total_seconds()

        return {
            "success": True,
            "project_id": project_id,
            "project_path": abs_path,
            "stats": stats,
            "duration_seconds": round(duration, 2),
            "force": force,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_clear(project_id: str = None) -> dict:
    """Clear the index for a project or all projects.

    Args:
        project_id: Project to clear, or None to clear all

    Returns:
        Clear result
    """
    try:
        from cognitive.code_indexer import get_code_indexer
        import sqlite3

        indexer = get_code_indexer()

        if project_id:
            # Clear specific project
            indexer.clear_project(project_id)
            return {
                "success": True,
                "cleared": project_id,
                "message": f"Cleared index for project: {project_id}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            # Clear all projects
            conn = sqlite3.connect(indexer.db_path)
            cur = conn.cursor()

            # Get counts before clearing
            cur.execute("SELECT COUNT(*) FROM code_entities")
            entities_cleared = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM indexed_files")
            files_cleared = cur.fetchone()[0]

            # Clear all
            cur.execute("DELETE FROM code_entities")
            cur.execute("DELETE FROM indexed_files")
            conn.commit()
            conn.close()

            return {
                "success": True,
                "cleared": "all",
                "entities_cleared": entities_cleared,
                "files_cleared": files_cleared,
                "message": "Cleared entire code index",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_watch(project_path: str, project_id: str = None) -> dict:
    """Start a file watcher for automatic index updates.

    Args:
        project_path: Path to watch
        project_id: Project identifier

    Returns:
        Watcher status
    """
    global _index_watcher, _watcher_observer

    try:
        import os
        from pathlib import Path
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        from cognitive.code_indexer import get_code_indexer

        abs_path = os.path.abspath(project_path)

        if not project_id:
            project_id = Path(abs_path).name

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path not found: {abs_path}"
            }

        # Stop existing watcher if running
        if _watcher_observer is not None and _watcher_observer.is_alive():
            _watcher_observer.stop()
            _watcher_observer.join(timeout=2)

        indexer = get_code_indexer()

        class IndexUpdateHandler(FileSystemEventHandler):
            """Handler that updates the code index on file changes."""

            EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs'}
            SKIP_DIRS = {'node_modules', '.git', '__pycache__', 'target', 'dist', 'build', '.venv', 'venv'}

            def __init__(self, indexer, project_id):
                self.indexer = indexer
                self.project_id = project_id
                self.last_event = {}
                self.debounce_seconds = 1

            def should_process(self, path: str) -> bool:
                """Check if file should be processed."""
                path_obj = Path(path)

                # Check extension
                if path_obj.suffix not in self.EXTENSIONS:
                    return False

                # Check skip directories
                if any(skip in path_obj.parts for skip in self.SKIP_DIRS):
                    return False

                # Debounce
                import time
                now = time.time()
                if path in self.last_event and (now - self.last_event[path]) < self.debounce_seconds:
                    return False
                self.last_event[path] = now

                return True

            def on_modified(self, event):
                if event.is_directory:
                    return
                if not self.should_process(event.src_path):
                    return

                # Re-index the single file by parsing and updating
                from cognitive.code_indexer import PythonParser, JavaScriptParser, RustParser
                import sqlite3
                import time

                file_path = Path(event.src_path)

                parsers = {
                    '.py': PythonParser,
                    '.js': JavaScriptParser,
                    '.ts': JavaScriptParser,
                    '.jsx': JavaScriptParser,
                    '.tsx': JavaScriptParser,
                    '.rs': RustParser,
                }

                if file_path.suffix not in parsers:
                    return

                parser = parsers[file_path.suffix]()
                entities = parser.parse(file_path, self.project_id)

                conn = sqlite3.connect(self.indexer.db_path)
                cur = conn.cursor()

                # Remove old entities for this file
                cur.execute("DELETE FROM code_entities WHERE file_path = ?", (str(file_path),))

                # Insert new entities
                for entity in entities:
                    cur.execute("""
                        INSERT OR REPLACE INTO code_entities
                        (id, name, type, signature, docstring, file_path, line_number, content, project_id, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entity.id, entity.name, entity.type, entity.signature,
                        entity.docstring, entity.file_path, entity.line_number,
                        entity.content, entity.project_id, time.time()
                    ))

                # Update file tracking
                cur.execute("""
                    INSERT OR REPLACE INTO indexed_files (file_path, project_id, mtime, indexed_at)
                    VALUES (?, ?, ?, ?)
                """, (str(file_path), self.project_id, file_path.stat().st_mtime, time.time()))

                conn.commit()
                conn.close()

                print(f"[Index Watch] Updated: {file_path.name} ({len(entities)} entities)")

            def on_created(self, event):
                # Treat new files same as modified
                self.on_modified(event)

            def on_deleted(self, event):
                if event.is_directory:
                    return

                # Remove entities for deleted file
                import sqlite3
                conn = sqlite3.connect(self.indexer.db_path)
                cur = conn.cursor()
                cur.execute("DELETE FROM code_entities WHERE file_path = ?", (event.src_path,))
                cur.execute("DELETE FROM indexed_files WHERE file_path = ?", (event.src_path,))
                conn.commit()
                conn.close()
                print(f"[Index Watch] Removed: {Path(event.src_path).name}")

        # Create and start observer
        _index_watcher = IndexUpdateHandler(indexer, project_id)
        _watcher_observer = Observer()
        _watcher_observer.schedule(_index_watcher, abs_path, recursive=True)
        _watcher_observer.start()

        return {
            "success": True,
            "watching": abs_path,
            "project_id": project_id,
            "message": f"Started watching {abs_path} for changes",
            "timestamp": datetime.now().isoformat(),
        }
    except ImportError:
        return {
            "success": False,
            "error": "watchdog package not installed. Install with: pip install watchdog"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_watch_stop() -> dict:
    """Stop the file watcher.

    Returns:
        Stop result
    """
    global _watcher_observer

    try:
        if _watcher_observer is None:
            return {
                "success": True,
                "message": "No watcher was running",
                "timestamp": datetime.now().isoformat(),
            }

        if _watcher_observer.is_alive():
            _watcher_observer.stop()
            _watcher_observer.join(timeout=2)

        _watcher_observer = None

        return {
            "success": True,
            "message": "Watcher stopped",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_escalate(query: str) -> dict:
    """Force escalation to Claude via browser bridge."""
    try:
        from escalation_handler import escalate_to_claude
        response = escalate_to_claude(query)
        return {
            "success": True,
            "query": query,
            "response": response,
            "provider": "claude",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_stream(query: str, user_id: str = "default"):
    """
    Stream cognitive response via Server-Sent Events.

    Yields SSE formatted events:
    - data: {"token": "..."} for each token
    - data: {"done": true, "response": "...", "confidence": 0.8} at end
    """
    import json as json_module

    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        yield f'data: {json_module.dumps({"error": "Cognitive system not available"})}\n\n'
        return

    try:
        # Get the MLX engine for streaming
        engine = orchestrator.mlx_engine

        # Build cognitive state
        cognitive_state = {
            "confidence": 0.5,
            "emotional_valence": 0.0
        }

        # Get context
        working_context = orchestrator.memory.get_context(max_tokens=100)

        # Stream tokens
        full_response = []
        for token in engine.generate_streaming(
            prompt=query,
            context=working_context,
            cognitive_state=cognitive_state
        ):
            if isinstance(token, str):
                full_response.append(token)
                yield f'data: {json_module.dumps({"token": token})}\n\n'

        # Final result
        final_text = "".join(full_response)
        yield f'data: {json_module.dumps({"done": True, "response": final_text, "confidence": 0.75})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_think_stream(query: str, mode: str = "structured"):
    """
    Stream of Consciousness - Real-time thinking display.

    Yields SSE formatted events showing SAM's thought process:
    - data: {"text": "...", "type": "reasoning", "tokens": 5, "elapsed_ms": 100}
    - data: {"done": true, "full_response": "...", "total_tokens": 50}

    Thought types: reasoning, planning, code, question, conclusion, error, uncertainty

    Args:
        query: What to think about
        mode: "standard", "structured", or "coding"
    """
    import json as json_module

    try:
        from live_thinking import (
            stream_thinking, stream_structured_thinking, stream_coding_thinking,
            thinking_to_sse, ThinkingSession
        )

        # Select thinking mode
        if mode == "coding":
            generator = stream_coding_thinking(query, show_live=False)
        elif mode == "structured":
            generator = stream_structured_thinking(query, show_live=False)
        else:
            generator = stream_thinking(query, show_live=False)

        # Stream thought chunks as SSE
        for chunk in generator:
            yield thinking_to_sse(chunk)

        # Note: The generator returns ThinkingSession at the end but we've
        # already streamed all chunks, so we just signal completion
        yield f'data: {json_module.dumps({"done": True})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_think_colors() -> dict:
    """Get color scheme for frontend thought display."""
    try:
        from live_thinking import get_thinking_colors
        return {
            "success": True,
            "colors": get_thinking_colors(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ VISION API ============

# Vision engine singleton
_vision_engine = None

def get_vision_engine():
    """Lazy-load vision engine singleton."""
    global _vision_engine
    if _vision_engine is None:
        try:
            from cognitive import create_vision_engine
            _vision_engine = create_vision_engine()
        except Exception as e:
            print(f"Warning: Could not load vision engine: {e}", file=sys.stderr)
            return None
    return _vision_engine


def api_vision_process(image_path: str = None, prompt: str = "", model: str = None,
                       image_base64: str = None) -> dict:
    """
    Process an image with a prompt.
    Accepts either image_path OR image_base64 (Phase 3 enhancement).
    """
    engine = get_vision_engine()
    if not engine:
        return {"success": False, "error": "Vision engine not available"}

    try:
        import tempfile
        import base64

        # Handle base64 image (Phase 3)
        temp_path = None
        if image_base64:
            # Decode base64 and save to temp file
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided (path or base64)"}

        from cognitive import VisionConfig
        config = VisionConfig()
        if model:
            config.model_key = model

        start = datetime.now()
        result = engine.process_image(image_path, prompt, config)

        # Clean up temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        # Record vision stats (Phase 3.2.6)
        # Map model to tier: local models = LOCAL_VLM, escalated = CLAUDE
        tier = "CLAUDE" if result.escalated else "LOCAL_VLM"
        record_vision_stats(
            tier=tier,
            processing_time_ms=result.processing_time_ms,
            task_type=result.task_type.value,
            escalated=result.escalated,
            success=True
        )

        return {
            "success": True,
            "image_path": image_path if not temp_path else "[base64 image]",
            "prompt": prompt,
            "response": result.response,
            "description": result.response,  # Alias for frontend compatibility
            "confidence": result.confidence,
            "model_used": result.model_used,
            "task_type": result.task_type.value,
            "escalated": result.escalated,
            "escalation_reason": result.escalation_reason,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        # Record failed request
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_stream(image_base64: str = None, image_path: str = None, prompt: str = "Describe this image"):
    """
    Stream vision response via Server-Sent Events (Phase 3.1.8).

    Vision models (nanoLLaVA via mlx_vlm) support token-by-token streaming.
    This endpoint provides real-time analysis progress.

    Yields SSE formatted events:
    - data: {"status": "loading", "message": "..."} - Loading model
    - data: {"status": "analyzing", "elapsed_ms": N} - During analysis
    - data: {"token": "..."} for each token
    - data: {"done": true, "response": "...", "processing_time_ms": N} at end
    - data: {"error": "..."} on failure
    """
    import json as json_module
    import tempfile
    import base64 as b64_module
    import time

    start_time = time.time()

    def elapsed_ms():
        return int((time.time() - start_time) * 1000)

    try:
        # Initial status
        yield f'data: {json_module.dumps({"status": "loading", "message": "Preparing image..."})}\n\n'

        # Handle base64 image
        temp_path = None
        actual_path = image_path
        if image_base64:
            image_data = b64_module.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_path = temp_path

        if not actual_path:
            yield f'data: {json_module.dumps({"error": "No image provided"})}\n\n'
            return

        # Try vision server first (fastest if running)
        try:
            import requests
            VISION_SERVER_URL = "http://localhost:8766"

            # Check if server supports streaming
            health = requests.get(f"{VISION_SERVER_URL}/health", timeout=2)
            if health.status_code == 200 and health.json().get("status") == "ok":
                yield f'data: {json_module.dumps({"status": "analyzing", "message": "Processing via vision server...", "elapsed_ms": elapsed_ms()})}\n\n'

                # Read image
                with open(actual_path, "rb") as f:
                    img_b64 = b64_module.b64encode(f.read()).decode("utf-8")

                # Stream from server (if supported) or get full response
                response = requests.post(
                    f"{VISION_SERVER_URL}/process/stream" if False else f"{VISION_SERVER_URL}/process",  # Server streaming TBD
                    json={"image_base64": img_b64, "prompt": prompt},
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        # Simulate progressive display for non-streaming server
                        text = result.get("response", "")
                        # Chunk the response for progressive display
                        words = text.split()
                        for i, word in enumerate(words):
                            yield f'data: {json_module.dumps({"token": word + " "})}\n\n'
                            if i < 5:  # Small delay for first few words
                                time.sleep(0.05)

                        yield f'data: {json_module.dumps({"done": True, "response": text, "processing_time_ms": elapsed_ms()})}\n\n'

                        # Cleanup
                        if temp_path:
                            import os
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        return

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass  # Fall through to direct processing

        # Direct mlx_vlm streaming
        yield f'data: {json_module.dumps({"status": "loading", "message": "Loading vision model (this takes 30-60s first time)...", "elapsed_ms": elapsed_ms()})}\n\n'

        try:
            from mlx_vlm import load, stream_generate
            from mlx_vlm.prompt_utils import apply_chat_template
            from mlx_vlm.utils import load_config

            model_path = "mlx-community/nanoLLaVA-1.5-bf16"

            yield f'data: {json_module.dumps({"status": "loading", "message": f"Loading {model_path}...", "elapsed_ms": elapsed_ms()})}\n\n'

            # Load model (cached after first load)
            config = load_config(model_path)
            model, processor = load(model_path, {"trust_remote_code": True})

            yield f'data: {json_module.dumps({"status": "analyzing", "message": "Analyzing image...", "elapsed_ms": elapsed_ms()})}\n\n'

            # Build prompt
            formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)

            # Stream generation
            full_response = []
            for token in stream_generate(
                model, processor,
                formatted_prompt,
                image=actual_path,
                max_tokens=200,
                temperature=0.3
            ):
                full_response.append(token)
                yield f'data: {json_module.dumps({"token": token})}\n\n'

            final_text = "".join(full_response).strip()
            yield f'data: {json_module.dumps({"done": True, "response": final_text, "processing_time_ms": elapsed_ms()})}\n\n'

        except ImportError as e:
            yield f'data: {json_module.dumps({"error": f"mlx_vlm not available: {e}"})}\n\n'
        except Exception as e:
            yield f'data: {json_module.dumps({"error": f"Vision processing failed: {e}"})}\n\n'

        # Cleanup temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_vision_analyze(image_base64: str = None, image_path: str = None, prompt: str = "Describe this image") -> dict:
    """
    Non-streaming vision analysis endpoint (Phase 3.1.8).

    This is the endpoint the Swift UI calls via /api/vision/analyze.
    Provides clear status and analysis response.
    """
    import tempfile
    import base64 as b64_module
    import time

    start_time = time.time()

    try:
        # Handle base64 image
        temp_path = None
        actual_path = image_path
        if image_base64:
            image_data = b64_module.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_path = temp_path

        if not actual_path:
            return {"success": False, "error": "No image provided"}

        # Use existing vision engine
        engine = get_vision_engine()
        if not engine:
            return {"success": False, "error": "Vision engine not available", "analysis": "Vision system is not loaded"}

        from cognitive import VisionConfig
        config = VisionConfig()

        result = engine.process_image(actual_path, prompt, config)

        # Cleanup temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Record vision stats (Phase 3.2.6)
        tier = "CLAUDE" if getattr(result, 'escalated', False) else "LOCAL_VLM"
        task_type_val = result.task_type.value if hasattr(result.task_type, 'value') else str(result.task_type)
        record_vision_stats(
            tier=tier,
            processing_time_ms=processing_time_ms,
            task_type=task_type_val,
            escalated=getattr(result, 'escalated', False),
            success=True
        )

        return {
            "success": True,
            "response": result.response,
            "analysis": result.response,  # Alias for Swift UI compatibility
            "description": result.response,  # Another alias
            "confidence": result.confidence,
            "model_used": result.model_used,
            "task_type": task_type_val,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e), "analysis": f"Analysis failed: {str(e)}"}


def api_vision_describe(image_path: str, detail_level: str = "medium") -> dict:
    """Describe an image at specified detail level."""
    try:
        from cognitive import describe_image
        start = datetime.now()
        result = describe_image(image_path, detail_level)
        duration = (datetime.now() - start).total_seconds() * 1000

        # Record vision stats (Phase 3.2.6)
        # detail_level maps roughly to tier: basic=LIGHTWEIGHT, medium/detailed=LOCAL_VLM
        tier = "LIGHTWEIGHT" if detail_level == "basic" else "LOCAL_VLM"
        record_vision_stats(
            tier=tier,
            processing_time_ms=result.processing_time_ms,
            task_type="describe",
            success=True
        )

        return {
            "success": True,
            "image_path": image_path,
            "detail_level": detail_level,
            "description": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="describe",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_ocr(image_path: str = None, image_base64: str = None) -> dict:
    """
    Extract text from an image using Apple Vision (fast, accurate, no GPU).
    Falls back to VLM if Apple Vision unavailable.
    """
    try:
        import tempfile
        import base64
        from datetime import datetime

        # Handle base64 image
        temp_path = None
        if image_base64:
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided"}

        start = datetime.now()

        # Try Apple Vision first (fast, accurate, no GPU)
        try:
            from apple_ocr import extract_text
            result = extract_text(image_path)

            if result.get("success"):
                processing_time = int((datetime.now() - start).total_seconds() * 1000)

                # Clean up temp file
                if temp_path:
                    import os
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

                # Record vision stats (Phase 3.2.6) - Apple Vision is ZERO_COST tier
                record_vision_stats(
                    tier="ZERO_COST",
                    processing_time_ms=processing_time,
                    task_type="ocr",
                    success=True
                )

                return {
                    "success": True,
                    "image_path": image_path if not temp_path else "[base64]",
                    "text": result.get("text", ""),
                    "lines": result.get("lines", []),
                    "line_count": result.get("line_count", 0),
                    "confidence": 1.0,  # Apple Vision is highly accurate
                    "model_used": "apple_vision",
                    "processing_time_ms": processing_time,
                    "timestamp": datetime.now().isoformat(),
                }
        except ImportError:
            pass  # Fall back to VLM

        # Fallback: Use vision model (slower, less accurate for OCR)
        engine = get_vision_engine()
        if not engine:
            return {"success": False, "error": "No OCR engine available"}

        from cognitive import VisionConfig
        config = VisionConfig()
        config.max_tokens = 200

        ocr_prompt = "Read the text in this image word by word. List all text exactly as written."
        result = engine.process_image(image_path, ocr_prompt, config)

        # Clean up temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        # Record vision stats (Phase 3.2.6) - VLM fallback is LOCAL_VLM tier
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=result.processing_time_ms,
            task_type="ocr",
            success=True
        )

        return {
            "success": True,
            "image_path": image_path if not temp_path else "[base64]",
            "text": result.response,
            "confidence": result.confidence,
            "model_used": "vlm_fallback",
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
            "note": "Used VLM fallback - accuracy may vary"
        }
    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="ocr",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_detect(image_path: str, target: str = None) -> dict:
    """Detect objects in an image."""
    try:
        from cognitive import detect_objects
        start = datetime.now()
        result = detect_objects(image_path, target)
        duration = (datetime.now() - start).total_seconds() * 1000

        return {
            "success": True,
            "image_path": image_path,
            "target": target,
            "detections": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "bounding_boxes": result.bounding_boxes,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_vision_models() -> dict:
    """List available vision models."""
    try:
        from cognitive import VISION_MODELS
        models = []
        for key, config in VISION_MODELS.items():
            models.append({
                "key": key,
                "model_id": config["model_id"],
                "memory_mb": config["memory_mb"],
                "speed": config["speed"],
                "quality": config["quality"],
                "use_cases": config["use_cases"],
            })
        return {
            "success": True,
            "models": models,
            "count": len(models),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_vision_stats() -> dict:
    """Get comprehensive vision statistics (Phase 3.2.6 enhanced).

    Returns:
        - engine_stats: Basic engine info (available models, etc.)
        - usage_stats: Requests per tier, processing times, memory peaks
        - escalation_rate: Percentage of requests escalated to Claude
        - cache_stats: Vision cache hit rates
    """
    # Get usage stats from our monitor
    usage_stats = {}
    try:
        vision_monitor = get_vision_stats_monitor()
        usage_stats = vision_monitor.get_stats()
    except Exception as e:
        usage_stats = {"error": str(e)}

    # Get engine stats (available models, etc.)
    engine_stats = {}
    engine = get_vision_engine()
    if engine:
        try:
            engine_stats = engine.get_stats()
        except Exception:
            engine_stats = {"available": True, "error": "Could not get engine stats"}
    else:
        engine_stats = {"available": False}

    # Get smart vision cache stats
    cache_stats = {}
    try:
        router = get_smart_vision_router()
        if router:
            cache_stats = router.memory.get_stats()
    except Exception:
        cache_stats = {"error": "Smart vision router not available"}

    return {
        "success": True,
        "engine": engine_stats,
        "usage": usage_stats,
        "cache": cache_stats,
        "timestamp": datetime.now().isoformat(),
    }


# Smart Vision singleton (lazy loaded)
_smart_vision_router = None

def get_smart_vision_router():
    """Lazy-load smart vision router singleton."""
    global _smart_vision_router
    if _smart_vision_router is None:
        try:
            from cognitive.smart_vision import SmartVisionRouter
            _smart_vision_router = SmartVisionRouter()
        except Exception as e:
            print(f"Warning: Could not load smart vision router: {e}", file=sys.stderr)
            return None
    return _smart_vision_router


def api_vision_smart(image_path: str = None, image_base64: str = None,
                     prompt: str = "What is this?",
                     force_tier: str = None,
                     skip_cache: bool = False) -> dict:
    """
    Smart vision endpoint - automatically routes to best tier.

    Tiers:
    - ZERO_COST: Apple Vision OCR, PIL color analysis (instant, 0 RAM)
    - LIGHTWEIGHT: CoreML face detection (fast, ~200MB)
    - LOCAL_VLM: nanoLLaVA (60s, 4GB RAM)
    - CLAUDE: Escalate to Claude (complex reasoning)

    Args:
        image_path: Path to local image
        image_base64: Base64 encoded image
        prompt: What to analyze
        force_tier: Override automatic routing (ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE)
        skip_cache: Bypass cache lookup
    """
    router = get_smart_vision_router()
    if not router:
        return {"success": False, "error": "Smart vision router not available"}

    try:
        import tempfile
        import base64
        from cognitive.smart_vision import VisionTier

        # Handle base64 image
        temp_path = None
        if image_base64:
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided (path or base64)"}

        # Parse force_tier if provided
        tier_override = None
        if force_tier:
            tier_map = {
                "ZERO_COST": VisionTier.ZERO_COST,
                "LIGHTWEIGHT": VisionTier.LIGHTWEIGHT,
                "LOCAL_VLM": VisionTier.LOCAL_VLM,
                "CLAUDE": VisionTier.CLAUDE,
            }
            tier_override = tier_map.get(force_tier.upper())

        # Process through smart router
        result = router.process(
            image_path=image_path,
            prompt=prompt,
            force_tier=tier_override,
            skip_cache=skip_cache
        )

        # Clean up temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        # Record vision stats (Phase 3.2.6)
        escalated = result.tier_used == VisionTier.CLAUDE
        record_vision_stats(
            tier=result.tier_used.name,
            processing_time_ms=result.processing_time_ms,
            task_type=result.task_type.value,
            escalated=escalated,
            success=result.success,
            from_cache=result.from_cache
        )

        return {
            "success": result.success,
            "response": result.response,
            "tier_used": result.tier_used.name,
            "task_type": result.task_type.value,
            "processing_time_ms": result.processing_time_ms,
            "confidence": result.confidence,
            "from_cache": result.from_cache,
            "metadata": result.metadata,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        # Record failed request
        record_vision_stats(
            tier=force_tier or "LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_smart_stats() -> dict:
    """Get smart vision cache statistics."""
    router = get_smart_vision_router()
    if not router:
        return {"success": False, "error": "Smart vision router not available"}

    try:
        stats = router.memory.get_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ IMAGE CONTEXT API (Phase 3.1.5) ============

def api_image_context_get() -> dict:
    """
    Phase 3.1.5: Get the current image context for follow-up questions.

    Returns the last image that was shared, allowing follow-up questions like:
    - "What color is the car?"
    - "Can you read the text in it?"
    - "What else do you see?"
    """
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        context = orchestrator.get_image_context()
        if context:
            return {
                "success": True,
                "has_context": True,
                "image_path": context.image_path,
                "image_hash": context.image_hash,
                "description": context.description,
                "task_type": context.task_type,
                "timestamp": context.timestamp.isoformat(),
                "age_seconds": (datetime.now() - context.timestamp).total_seconds(),
                "metadata": context.metadata,
            }
        else:
            return {
                "success": True,
                "has_context": False,
                "message": "No image context available. Share an image first.",
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_context_clear() -> dict:
    """Phase 3.1.5: Clear the current image context."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        orchestrator.clear_image_context()
        return {
            "success": True,
            "message": "Image context cleared",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_chat(
    query: str,
    image_path: str = None,
    image_base64: str = None,
    user_id: str = "default"
) -> dict:
    """
    Phase 3.1.5: Unified endpoint for image-aware chat.

    Handles three scenarios:
    1. New image + question: Process image and answer question
    2. Follow-up question: Use previous image context
    3. Regular text: Pass through to cognitive processing

    Args:
        query: User's message/question
        image_path: Optional path to a new image
        image_base64: Optional base64 encoded image
        user_id: User identifier

    Examples:
        - {"query": "What's in this image?", "image_path": "/tmp/photo.jpg"}
        - {"query": "What color is the car?"}  # Follow-up
        - {"query": "What else do you see?"}   # Follow-up
    """
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        import tempfile
        import base64 as b64

        _update_activity()  # Track activity for idle timeout

        # Handle base64 image
        temp_path = None
        actual_image_path = image_path

        if image_base64:
            image_data = b64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_image_path = temp_path

        # Process through orchestrator's unified handler
        start = datetime.now()
        result = orchestrator.process_with_image(
            user_input=query,
            image_path=actual_image_path,
            user_id=user_id
        )
        duration = (datetime.now() - start).total_seconds() * 1000

        # Clean up temp file
        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        _update_activity()  # Update after processing

        # Build response
        response_data = {
            "success": True,
            "query": query,
            "response": result.response,
            "confidence": result.confidence,
            "mood": result.mood,
            "query_type": result.metadata.get("query_type", "text"),
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }

        # Add image-specific fields if applicable
        if result.metadata.get("image_path"):
            response_data["image_path"] = result.metadata["image_path"]
        if result.metadata.get("model_used"):
            response_data["model_used"] = result.metadata["model_used"]
        if result.metadata.get("escalated"):
            response_data["escalated"] = result.metadata["escalated"]
        if result.metadata.get("followup_confidence"):
            response_data["followup_confidence"] = result.metadata["followup_confidence"]
        if result.metadata.get("image_context"):
            response_data["image_context"] = result.metadata["image_context"]

        return response_data

    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_followup_check(query: str) -> dict:
    """
    Phase 3.1.5: Check if a query is a follow-up about a previous image.

    Useful for UI to determine whether to show image context hint.
    """
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        is_followup, confidence = orchestrator.is_image_followup(query)
        has_context = orchestrator.has_image_context()

        return {
            "success": True,
            "query": query,
            "is_followup": is_followup,
            "confidence": confidence,
            "has_image_context": has_context,
            "will_use_image": is_followup and has_context and confidence >= 0.7,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ VOICE PIPELINE API ============

# Voice pipeline singleton (lazy loaded)
_voice_pipeline = None

def get_voice_pipeline():
    """Lazy-load voice pipeline singleton."""
    global _voice_pipeline
    if _voice_pipeline is None:
        try:
            from voice_pipeline import SAMVoicePipeline, VoicePipelineConfig
            _voice_pipeline = SAMVoicePipeline()
        except Exception as e:
            print(f"Warning: Could not load voice pipeline: {e}", file=sys.stderr)
            return None
    return _voice_pipeline


def api_voice_start() -> dict:
    """Start the voice pipeline."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        pipeline.start()
        return {
            "success": True,
            "running": True,
            "config": {
                "emotion_backend": pipeline.config.emotion_backend,
                "response_strategy": pipeline.config.response_strategy,
                "rvc_enabled": pipeline.config.rvc_enabled,
                "enable_backchannels": pipeline.config.enable_backchannels,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_stop() -> dict:
    """Stop the voice pipeline."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        pipeline.stop()
        return {
            "success": True,
            "running": False,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_status() -> dict:
    """Get voice pipeline status and statistics."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        emotion = pipeline.get_current_emotion()
        conversation_state = pipeline.get_conversation_state()
        stats = pipeline.get_stats()

        return {
            "success": True,
            "running": pipeline._running,
            "current_emotion": {
                "primary": emotion.primary_emotion.value if emotion else None,
                "confidence": emotion.confidence if emotion else 0.0,
                "valence": emotion.primary.valence if emotion else 0.0,
                "arousal": emotion.primary.arousal if emotion else 0.5,
            } if emotion else None,
            "conversation": {
                "phase": conversation_state.phase.value,
                "current_speaker": conversation_state.current_speaker.value,
                "turn_count": len(conversation_state.turns),
                "user_emotion": conversation_state.user_emotion,
            },
            "stats": stats,
            "config": {
                "emotion_backend": pipeline.config.emotion_backend,
                "response_strategy": pipeline.config.response_strategy,
                "rvc_enabled": pipeline.config.rvc_enabled,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_emotion() -> dict:
    """Get current detected user emotion."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        emotion = pipeline.get_current_emotion()
        trajectory = pipeline.get_emotional_trajectory()

        if emotion:
            return {
                "success": True,
                "emotion": {
                    "primary": emotion.primary_emotion.value,
                    "secondary": emotion.secondary_emotion.value if emotion.secondary_emotion else None,
                    "confidence": emotion.confidence,
                    "dimensions": {
                        "valence": emotion.primary.valence,
                        "arousal": emotion.primary.arousal,
                        "dominance": emotion.primary.dominance,
                    },
                    "intensity": emotion.intensity.value,
                    "context_string": emotion.to_context_string(),
                },
                "trajectory": trajectory,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": True,
                "emotion": None,
                "trajectory": trajectory,
                "message": "No emotion detected yet",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_config(config_updates: dict = None) -> dict:
    """Get or update voice pipeline configuration."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        if config_updates:
            # Update configuration
            if "response_strategy" in config_updates:
                pipeline.set_response_strategy(config_updates["response_strategy"])
            if "backchannel_probability" in config_updates:
                pipeline.set_backchannel_probability(config_updates["backchannel_probability"])
            if "rvc_enabled" in config_updates:
                pipeline.enable_rvc(config_updates["rvc_enabled"])
            if "rvc_model" in config_updates:
                pipeline.enable_rvc(True, config_updates["rvc_model"])

        return {
            "success": True,
            "config": {
                "sample_rate": pipeline.config.sample_rate,
                "chunk_size_ms": pipeline.config.chunk_size_ms,
                "emotion_backend": pipeline.config.emotion_backend,
                "emotion_update_interval_ms": pipeline.config.emotion_update_interval_ms,
                "conversation_mode": pipeline.config.conversation_mode,
                "enable_backchannels": pipeline.config.enable_backchannels,
                "backchannel_probability": pipeline.config.backchannel_probability,
                "response_strategy": pipeline.config.response_strategy,
                "prosody_intensity": pipeline.config.prosody_intensity,
                "rvc_enabled": pipeline.config.rvc_enabled,
                "rvc_model": pipeline.config.rvc_model,
                "enable_speculative_generation": pipeline.config.enable_speculative_generation,
                "max_response_tokens": pipeline.config.max_response_tokens,
            },
            "updated": bool(config_updates),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_process_audio(audio_base64: str) -> dict:
    """
    Process audio chunk through voice pipeline.

    Accepts base64-encoded audio (16kHz, mono, float32).
    Returns any events generated (backchannels, responses, etc.)
    """
    import base64
    import numpy as np

    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    if not pipeline._running:
        return {"success": False, "error": "Voice pipeline not running. Call /api/voice/start first."}

    try:
        # Decode base64 to numpy array
        audio_bytes = base64.b64decode(audio_base64)
        audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)

        # Process through pipeline
        events = []
        for event in pipeline.process_audio(audio_chunk):
            event_data = {
                "type": event.type.value,
                "timestamp": event.timestamp,
            }

            # Add type-specific fields
            if hasattr(event, 'text') and event.text:
                event_data["text"] = event.text
            if hasattr(event, 'audio') and event.audio is not None:
                # Return audio as base64
                event_data["audio_base64"] = base64.b64encode(
                    event.audio.astype(np.float32).tobytes()
                ).decode()
            if hasattr(event, 'partial_text'):
                event_data["partial_text"] = event.partial_text
            if hasattr(event, 'turn_end_probability'):
                event_data["turn_end_probability"] = event.turn_end_probability
            if hasattr(event, 'current_emotion'):
                event_data["current_emotion"] = event.current_emotion
            if hasattr(event, 'emotion'):
                event_data["emotion"] = event.emotion
            if hasattr(event, 'new_speaker'):
                event_data["new_speaker"] = event.new_speaker
            if hasattr(event, 'reason'):
                event_data["reason"] = event.reason
            if hasattr(event, 'trigger'):
                event_data["trigger"] = event.trigger

            events.append(event_data)

        return {
            "success": True,
            "events": events,
            "event_count": len(events),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_process_stream(audio_base64: str):
    """
    Process audio chunk and stream events via SSE.

    Yields SSE formatted events for real-time handling.
    """
    import base64
    import numpy as np
    import json as json_module

    pipeline = get_voice_pipeline()
    if not pipeline:
        yield f'data: {json_module.dumps({"error": "Voice pipeline not available"})}\n\n'
        return

    if not pipeline._running:
        yield f'data: {json_module.dumps({"error": "Voice pipeline not running"})}\n\n'
        return

    try:
        # Decode base64 to numpy array
        audio_bytes = base64.b64decode(audio_base64)
        audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)

        # Process through pipeline, yielding events
        for event in pipeline.process_audio(audio_chunk):
            event_data = {
                "type": event.type.value,
                "timestamp": event.timestamp,
            }

            if hasattr(event, 'text') and event.text:
                event_data["text"] = event.text
            if hasattr(event, 'audio') and event.audio is not None:
                event_data["audio_base64"] = base64.b64encode(
                    event.audio.astype(np.float32).tobytes()
                ).decode()
            if hasattr(event, 'partial_text'):
                event_data["partial_text"] = event.partial_text
            if hasattr(event, 'turn_end_probability'):
                event_data["turn_end_probability"] = event.turn_end_probability
            if hasattr(event, 'current_emotion'):
                event_data["current_emotion"] = event.current_emotion

            yield f'data: {json_module.dumps(event_data)}\n\n'

        yield f'data: {json_module.dumps({"done": True})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_voice_conversation_state() -> dict:
    """Get full conversation state."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        state = pipeline.get_conversation_state()
        timing = state.get_timing_stats()

        return {
            "success": True,
            "state": {
                "phase": state.phase.value,
                "current_speaker": state.current_speaker.value,
                "user_partial_text": state.user_partial_text,
                "user_final_text": state.user_final_text,
                "user_emotion": state.user_emotion,
                "user_arousal": state.user_arousal,
                "user_valence": state.user_valence,
                "sam_response_text": state.sam_response_text,
                "sam_response_emotion": state.sam_response_emotion,
                "recent_backchannels": state.recent_backchannels,
                "backchannel_count": state.backchannel_count,
                "interrupt_count": state.interrupt_count,
            },
            "timing": timing,
            "turns": [
                {
                    "speaker": turn.speaker.value,
                    "text": turn.text[:100] if len(turn.text) > 100 else turn.text,
                    "emotion": turn.emotion,
                    "was_interrupted": turn.was_interrupted,
                    "start_time": turn.start_time,
                    "end_time": turn.end_time,
                }
                for turn in state.turns[-10:]  # Last 10 turns
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===== DISTILLATION REVIEW API =====

def api_distillation_review_pending(limit: int = 10, domain: str = None) -> dict:
    """Get pending distillation examples for review.

    Args:
        limit: Maximum number of examples to return
        domain: Optional domain filter

    Returns:
        dict with pending examples and review stats
    """
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        pending = db.get_pending_review(limit=limit, domain=domain)
        stats = db.get_review_stats()

        # Format examples for API response
        examples = []
        for item in pending:
            examples.append({
                "id": item['id'],
                "query": item['query'],
                "sam_attempt": item.get('sam_attempt'),
                "claude_response": item['claude_response'],
                "domain": item['domain'],
                "reasoning_type": item.get('reasoning_type'),
                "quality_score": item['quality_score'],
                "complexity": item.get('complexity'),
                "priority": item.get('priority', 5),
                "review_reason": item.get('review_reason'),
                "has_correction": bool(item.get('sam_attempt')),
            })

        return {
            "success": True,
            "examples": examples,
            "count": len(examples),
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_details(example_id: str) -> dict:
    """Get full details of a distillation example.

    Args:
        example_id: The example ID

    Returns:
        dict with full example details
    """
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        details = db.get_example_details(example_id)
        if not details:
            return {"success": False, "error": f"Example not found: {example_id}"}

        return {
            "success": True,
            "example": details,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_action(
    example_id: str,
    action: str,
    notes: str = ""
) -> dict:
    """Approve or reject a distillation example.

    Args:
        example_id: The example ID
        action: "approve" or "reject"
        notes: Optional notes for the action

    Returns:
        dict with success status
    """
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        if action == "approve":
            success = db.approve_example(example_id, notes=notes)
            action_past = "approved"
        elif action == "reject":
            success = db.reject_example(example_id, reason=notes)
            action_past = "rejected"
        else:
            return {"success": False, "error": f"Invalid action: {action}. Use 'approve' or 'reject'"}

        if success:
            return {
                "success": True,
                "message": f"Example {example_id} {action_past}",
                "example_id": example_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": f"Failed to {action} example {example_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_batch(
    action: str,
    threshold: float
) -> dict:
    """Batch approve or reject examples based on quality threshold.

    Args:
        action: "approve" or "reject"
        threshold: Quality score threshold

    Returns:
        dict with count of affected examples
    """
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        if not 0.0 <= threshold <= 1.0:
            return {"success": False, "error": f"Threshold must be between 0.0 and 1.0, got {threshold}"}

        if action == "approve":
            result = db.batch_approve_above_threshold(threshold)
            return {
                "success": True,
                "action": "batch_approve",
                "threshold": threshold,
                "affected_count": result['approved_count'],
                "affected_ids": result['ids'],
                "timestamp": datetime.now().isoformat(),
            }
        elif action == "reject":
            result = db.batch_reject_below_threshold(threshold)
            return {
                "success": True,
                "action": "batch_reject",
                "threshold": threshold,
                "affected_count": result['rejected_count'],
                "affected_ids": result['ids'],
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": f"Invalid action: {action}. Use 'approve' or 'reject'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_stats() -> dict:
    """Get distillation review queue statistics.

    Returns:
        dict with comprehensive review stats
    """
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        stats = db.get_review_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_server(port: int = 8765):
    """Run a simple HTTP server for the API."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    class SAMHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Quiet

        def send_json(self, data: dict, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            params = urllib.parse.parse_qs(parsed.query)

            # Serve mobile web interface
            if path == "/" or path == "/mobile":
                try:
                    static_dir = Path(__file__).parent / "static"
                    mobile_html = static_dir / "mobile.html"
                    if mobile_html.exists():
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(mobile_html.read_bytes())
                    else:
                        self.send_json({"error": "Mobile interface not found"}, 404)
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                return
            elif path.startswith("/static/"):
                try:
                    static_dir = Path(__file__).parent / "static"
                    file_path = static_dir / path[8:]  # Remove /static/
                    if file_path.exists() and file_path.is_file():
                        content_type = "text/html" if path.endswith(".html") else \
                                      "text/css" if path.endswith(".css") else \
                                      "application/javascript" if path.endswith(".js") else \
                                      "application/octet-stream"
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(file_path.read_bytes())
                    else:
                        self.send_json({"error": "File not found"}, 404)
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                return
            elif path == "/api/health":
                # Simple health check endpoint for GUI ping
                self.send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
            elif path == "/api/status":
                self.send_json(api_status())
            elif path == "/api/projects":
                self.send_json(api_projects())
            elif path == "/api/memory":
                self.send_json(api_memory())
            elif path == "/api/query":
                query = params.get("q", [""])[0]
                if query:
                    self.send_json(api_query(query))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            # SAM Intelligence endpoints
            elif path == "/api/self":
                self.send_json(api_self())
            elif path == "/api/suggest":
                limit = int(params.get("limit", ["5"])[0])
                self.send_json(api_suggest(limit))
            elif path == "/api/intelligence":
                self.send_json(api_intelligence_stats())
            elif path == "/api/facts":
                # Phase 1.3.9: Enhanced fact listing
                user_id = params.get("user", ["david"])[0]
                category = params.get("category", [None])[0]
                min_confidence = float(params.get("min_confidence", ["0.0"])[0])
                limit = int(params.get("limit", ["50"])[0])
                self.send_json(api_facts_list(user_id, category, min_confidence, limit))
            elif path == "/api/facts/context":
                # Phase 1.3.6: Get formatted fact context for prompts
                user_id = params.get("user", ["david"])[0]
                self.send_json(api_fact_context(user_id))
            elif path == "/api/facts/search":
                # Phase 1.3.9: Search facts
                query = params.get("q", [""])[0]
                user_id = params.get("user", ["david"])[0]
                limit = int(params.get("limit", ["10"])[0])
                if query:
                    self.send_json(api_facts_search(query, user_id, limit))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            elif path.startswith("/api/facts/"):
                # Phase 1.3.9: Get single fact by ID
                fact_id = path.split("/")[-1]
                if fact_id and fact_id not in ["context", "search", "remember"]:
                    self.send_json(api_facts_get(fact_id))
                else:
                    self.send_json({"success": False, "error": "Invalid fact ID"}, 400)
            elif path == "/api/proactive":
                self.send_json(api_proactive())
            elif path == "/api/learning":
                self.send_json(api_learning())
            elif path == "/api/scan":
                self.send_json(api_scan())
            elif path == "/api/think":
                query = params.get("q", [""])[0]
                if query:
                    self.send_json(api_think(query))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            elif path == "/api/think/colors":
                self.send_json(api_think_colors())
            # Cognitive system endpoints
            elif path == "/api/cognitive/state":
                self.send_json(api_cognitive_state())
            elif path == "/api/cognitive/mood":
                self.send_json(api_cognitive_mood())
            elif path == "/api/resources":
                self.send_json(api_resources())
            # Context/Compression stats endpoint (Phase 2.3.6)
            elif path == "/api/context/stats":
                self.send_json(api_context_stats())
            elif path == "/api/unload":
                self.send_json(api_unload_model())
            elif path == "/api/cognitive/process":
                query = params.get("q", [""])[0]
                if query:
                    self.send_json(api_cognitive_process(query))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            # Cognitive feedback endpoints (Phase 1.2)
            elif path == "/api/cognitive/feedback":
                # GET returns stats
                self.send_json(api_cognitive_feedback_stats())
            elif path == "/api/cognitive/feedback/recent":
                limit = int(params.get("limit", ["20"])[0])
                domain = params.get("domain", [None])[0]
                feedback_type = params.get("type", [None])[0]
                session_id = params.get("session", [None])[0]
                self.send_json(api_cognitive_feedback_recent(limit, domain, feedback_type, session_id))
            # Proactive notifications endpoint (Phase 1.2.8)
            elif path == "/api/notifications":
                self.send_json(api_notifications())
            # Feedback Dashboard endpoint (Phase 1.2.9)
            elif path == "/api/feedback/dashboard":
                self.send_json(api_feedback_dashboard())
            # Vision system endpoints
            elif path == "/api/vision/models":
                self.send_json(api_vision_models())
            elif path == "/api/vision/stats":
                self.send_json(api_vision_stats())
            elif path == "/api/vision/describe":
                image_path = params.get("path", [""])[0]
                detail_level = params.get("level", ["medium"])[0]
                if image_path:
                    self.send_json(api_vision_describe(image_path, detail_level))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'path'"}, 400)
            elif path == "/api/vision/detect":
                image_path = params.get("path", [""])[0]
                target = params.get("target", [None])[0]
                if image_path:
                    self.send_json(api_vision_detect(image_path, target))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'path'"}, 400)
            # Smart Vision endpoints (Phase 3.5)
            elif path == "/api/vision/smart":
                image_path = params.get("path", [""])[0]
                prompt = params.get("prompt", ["What is this?"])[0]
                force_tier = params.get("tier", [None])[0]
                skip_cache = params.get("skip_cache", ["false"])[0].lower() == "true"
                if image_path:
                    self.send_json(api_vision_smart(
                        image_path=image_path,
                        prompt=prompt,
                        force_tier=force_tier,
                        skip_cache=skip_cache
                    ))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'path'"}, 400)
            elif path == "/api/vision/smart/stats":
                self.send_json(api_vision_smart_stats())
            # Image Context endpoints (Phase 3.1.5)
            elif path == "/api/image/context":
                self.send_json(api_image_context_get())
            elif path == "/api/image/context/clear":
                self.send_json(api_image_context_clear())
            elif path == "/api/image/followup/check":
                query = params.get("q", [""])[0]
                if query:
                    self.send_json(api_image_followup_check(query))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            # Project context endpoints (Phase 2)
            elif path == "/api/project":
                path_param = params.get("path", ["."])[0]
                self.send_json(api_project_context(path_param))
            elif path == "/api/project/recent":
                limit = int(params.get("limit", ["5"])[0])
                self.send_json(api_recent_projects(limit))
            elif path == "/api/project/current":
                # Phase 2.1.9: Current project for GUI header
                self.send_json(api_project_current())
            elif path == "/api/project/todos":
                path_param = params.get("path", ["."])[0]
                limit = int(params.get("limit", ["10"])[0])
                self.send_json(api_project_todos(path_param, limit))
            # Code Index endpoints (Phase 2.2)
            elif path == "/api/code/search":
                query = params.get("q", [""])[0]
                project_id = params.get("project", [None])[0]
                entity_type = params.get("type", [None])[0]
                limit = int(params.get("limit", ["10"])[0])
                if query:
                    self.send_json(api_code_search(query, project_id, entity_type, limit))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            elif path == "/api/code/stats":
                project_id = params.get("project", [None])[0]
                self.send_json(api_code_stats(project_id))
            # Index Management endpoints (Phase 2.2.10)
            elif path == "/api/index/status":
                self.send_json(api_index_status())
            elif path == "/api/index/search":
                query = params.get("q", [""])[0]
                project_id = params.get("project", [None])[0]
                entity_type = params.get("type", [None])[0]
                limit = int(params.get("limit", ["10"])[0])
                if query:
                    self.send_json(api_code_search(query, project_id, entity_type, limit))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            elif path == "/api/index/watch/stop":
                self.send_json(api_index_watch_stop())
            # Voice Pipeline endpoints
            elif path == "/api/voice/start":
                self.send_json(api_voice_start())
            elif path == "/api/voice/stop":
                self.send_json(api_voice_stop())
            elif path == "/api/voice/status":
                self.send_json(api_voice_status())
            elif path == "/api/voice/emotion":
                self.send_json(api_voice_emotion())
            elif path == "/api/voice/config":
                self.send_json(api_voice_config())
            elif path == "/api/voice/conversation":
                self.send_json(api_voice_conversation_state())
            # Distillation Review endpoints (Phase 1.1.8)
            elif path == "/api/distillation/review":
                limit = int(params.get("limit", ["10"])[0])
                domain = params.get("domain", [None])[0]
                self.send_json(api_distillation_review_pending(limit=limit, domain=domain))
            elif path == "/api/distillation/review/stats":
                self.send_json(api_distillation_review_stats())
            elif path.startswith("/api/distillation/review/"):
                # Get details for specific example: /api/distillation/review/<id>
                example_id = path.split("/")[-1]
                if example_id and example_id != "review":
                    self.send_json(api_distillation_review_details(example_id))
                else:
                    self.send_json({"success": False, "error": "Missing example ID"}, 400)
            else:
                self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

            if self.path == "/api/query":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    if query:
                        self.send_json(api_query(query))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/feedback":
                try:
                    data = json.loads(body)
                    improvement_id = data.get("improvement_id", "")
                    success = data.get("success", True)
                    impact = data.get("impact", 0.5)
                    lessons = data.get("lessons", "")
                    if improvement_id:
                        self.send_json(api_feedback(improvement_id, success, impact, lessons))
                    else:
                        self.send_json({"success": False, "error": "Missing improvement_id"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/think":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    if query:
                        self.send_json(api_think(query))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/think/stream":
                # Stream of Consciousness - SSE endpoint
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    mode = data.get("mode", "structured")  # standard, structured, coding
                    if query:
                        # Send SSE headers
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "keep-alive")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Stream thought chunks
                        for event in api_think_stream(query, mode):
                            self.wfile.write(event.encode())
                            self.wfile.flush()
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
                except Exception as e:
                    try:
                        self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode())
                    except:
                        pass
            # SAM Orchestrator endpoint (specialized routing: VOICE, IMAGE, DATA, etc.)
            elif self.path == "/api/orchestrate":
                try:
                    data = json.loads(body)
                    message = data.get("message", "")
                    if message:
                        self.send_json(api_orchestrate(message))
                    else:
                        self.send_json({"success": False, "error": "Missing message"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Cognitive system POST endpoints
            elif self.path == "/api/cognitive/process":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    user_id = data.get("user_id", "default")
                    if query:
                        self.send_json(api_cognitive_process(query, user_id))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/cognitive/feedback":
                try:
                    data = json.loads(body)
                    response_id = data.get("response_id", "")
                    if response_id:
                        # Phase 1.2 enhanced feedback with full validation
                        self.send_json(api_cognitive_feedback(
                            response_id=response_id,
                            helpful=data.get("helpful", True),
                            comment=data.get("comment", ""),
                            query=data.get("query", data.get("original_query", "")),
                            response=data.get("response", data.get("original_response", "")),
                            user_id=data.get("user_id", "default"),
                            session_id=data.get("session_id", "default"),
                            # New Phase 1.2 parameters
                            feedback_type=data.get("feedback_type", "rating"),
                            rating=data.get("rating"),
                            correction=data.get("correction"),
                            correction_type=data.get("correction_type"),
                            what_was_wrong=data.get("what_was_wrong"),
                            preferred_response=data.get("preferred_response"),
                            comparison_basis=data.get("comparison_basis"),
                            flag_type=data.get("flag_type"),
                            flag_details=data.get("flag_details"),
                            domain=data.get("domain", "general"),
                            response_confidence=data.get("response_confidence"),
                            escalated_to_claude=data.get("escalated_to_claude", False),
                            response_timestamp=data.get("response_timestamp"),
                            conversation_context=data.get("conversation_context"),
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing response_id"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/cognitive/escalate":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    if query:
                        self.send_json(api_cognitive_escalate(query))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/cognitive/stream":
                # Server-Sent Events streaming endpoint
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    user_id = data.get("user_id", "default")
                    if query:
                        # Send SSE headers
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "keep-alive")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Stream tokens
                        for event in api_cognitive_stream(query, user_id):
                            self.wfile.write(event.encode())
                            self.wfile.flush()
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
                except Exception as e:
                    # Try to send error as SSE if headers already sent
                    try:
                        self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode())
                    except:
                        pass
            # Vision system POST endpoints
            elif self.path == "/api/vision/process":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")  # Phase 3: base64 support
                    prompt = data.get("prompt", "Describe this image")
                    model = data.get("model")
                    if image_path or image_base64:
                        self.send_json(api_vision_process(
                            image_path=image_path if image_path else None,
                            prompt=prompt,
                            model=model,
                            image_base64=image_base64 if image_base64 else None
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path or image_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Phase 3.1.8: Vision analyze endpoint (for Swift UI)
            elif self.path == "/api/vision/analyze":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")
                    prompt = data.get("prompt", "Describe this image in detail.")
                    if image_path or image_base64:
                        self.send_json(api_vision_analyze(
                            image_path=image_path if image_path else None,
                            image_base64=image_base64 if image_base64 else None,
                            prompt=prompt
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path or image_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Phase 3.1.8: Streaming vision endpoint
            elif self.path == "/api/vision/stream":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")
                    prompt = data.get("prompt", "Describe this image")
                    if image_path or image_base64:
                        # Send SSE headers
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "keep-alive")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Stream vision response
                        for event in api_vision_stream(
                            image_base64=image_base64 if image_base64 else None,
                            image_path=image_path if image_path else None,
                            prompt=prompt
                        ):
                            self.wfile.write(event.encode())
                            self.wfile.flush()
                    else:
                        self.send_json({"success": False, "error": "Missing image_path or image_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
                except Exception as e:
                    try:
                        self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode())
                    except:
                        pass
            elif self.path == "/api/vision/describe":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    detail_level = data.get("detail_level", "medium")
                    if image_path:
                        self.send_json(api_vision_describe(image_path, detail_level))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/vision/detect":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    target = data.get("target")
                    if image_path:
                        self.send_json(api_vision_detect(image_path, target))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/vision/ocr":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")
                    if image_path or image_base64:
                        self.send_json(api_vision_ocr(
                            image_path=image_path if image_path else None,
                            image_base64=image_base64 if image_base64 else None
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path or image_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Smart Vision POST endpoint (Phase 3.5)
            elif self.path == "/api/vision/smart":
                try:
                    data = json.loads(body)
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")
                    prompt = data.get("prompt", "What is this?")
                    force_tier = data.get("force_tier")
                    skip_cache = data.get("skip_cache", False)
                    if image_path or image_base64:
                        self.send_json(api_vision_smart(
                            image_path=image_path if image_path else None,
                            image_base64=image_base64 if image_base64 else None,
                            prompt=prompt,
                            force_tier=force_tier,
                            skip_cache=skip_cache
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing image_path or image_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Image Chat POST endpoint (Phase 3.1.5)
            elif self.path == "/api/image/chat":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    image_path = data.get("image_path", "")
                    image_base64 = data.get("image_base64", "")
                    user_id = data.get("user_id", "default")
                    if query:
                        self.send_json(api_image_chat(
                            query=query,
                            image_path=image_path if image_path else None,
                            image_base64=image_base64 if image_base64 else None,
                            user_id=user_id
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/image/followup/check":
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    if query:
                        self.send_json(api_image_followup_check(query))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Project context POST endpoints
            elif self.path == "/api/project/session":
                try:
                    data = json.loads(body)
                    project_path = data.get("path", ".")
                    working_on = data.get("working_on", "")
                    notes = data.get("notes", "")
                    self.send_json(api_save_session(project_path, working_on, notes))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/facts/remember":
                # Legacy endpoint (Phase 1.3.5)
                try:
                    data = json.loads(body)
                    user_id = data.get("user_id", "david")
                    fact = data.get("fact", "")
                    category = data.get("category", "preference")
                    if fact:
                        self.send_json(api_remember_fact(user_id, fact, category))
                    else:
                        self.send_json({"success": False, "error": "Missing fact"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/facts":
                # Phase 1.3.9: Add fact endpoint
                try:
                    data = json.loads(body)
                    fact = data.get("fact", "")
                    category = data.get("category", "")
                    user_id = data.get("user_id", "david")
                    source = data.get("source", "explicit")
                    confidence = data.get("confidence")
                    if fact and category:
                        self.send_json(api_facts_add(fact, category, user_id, source, confidence))
                    else:
                        self.send_json({"success": False, "error": "Missing 'fact' or 'category'"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Code Index POST endpoint (Phase 2.2)
            elif self.path == "/api/code/index":
                try:
                    data = json.loads(body)
                    path = data.get("path", ".")
                    project_id = data.get("project_id", "default")
                    force = data.get("force", False)
                    self.send_json(api_code_index(path, project_id, force))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Index Management POST endpoints (Phase 2.2.10)
            elif self.path == "/api/index/build":
                try:
                    data = json.loads(body)
                    path = data.get("path", ".")
                    project_id = data.get("project_id")
                    force = data.get("force", False)
                    self.send_json(api_index_build(path, project_id, force))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/index/clear":
                try:
                    data = json.loads(body)
                    project_id = data.get("project_id")
                    self.send_json(api_index_clear(project_id))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/index/watch":
                try:
                    data = json.loads(body)
                    path = data.get("path", ".")
                    project_id = data.get("project_id")
                    self.send_json(api_index_watch(path, project_id))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            # Voice Pipeline POST endpoints
            elif self.path == "/api/voice/config":
                try:
                    data = json.loads(body)
                    self.send_json(api_voice_config(data))
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/voice/process":
                try:
                    data = json.loads(body)
                    audio_base64 = data.get("audio_base64", "")
                    if audio_base64:
                        self.send_json(api_voice_process_audio(audio_base64))
                    else:
                        self.send_json({"success": False, "error": "Missing audio_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/voice/stream":
                # Voice processing SSE streaming endpoint
                try:
                    data = json.loads(body)
                    audio_base64 = data.get("audio_base64", "")
                    if audio_base64:
                        # Send SSE headers
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "keep-alive")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Stream events
                        for event in api_voice_process_stream(audio_base64):
                            self.wfile.write(event.encode())
                            self.wfile.flush()
                    else:
                        self.send_json({"success": False, "error": "Missing audio_base64"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
                except Exception as e:
                    try:
                        self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode())
                    except:
                        pass
            # Distillation Review POST endpoints (Phase 1.1.8)
            elif self.path == "/api/distillation/review":
                try:
                    data = json.loads(body)
                    example_id = data.get("example_id", "")
                    action = data.get("action", "")  # "approve" or "reject"
                    notes = data.get("notes", "")
                    if example_id and action:
                        self.send_json(api_distillation_review_action(
                            example_id=example_id,
                            action=action,
                            notes=notes
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing example_id or action"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            elif self.path == "/api/distillation/review/batch":
                try:
                    data = json.loads(body)
                    action = data.get("action", "")  # "approve" or "reject"
                    threshold = data.get("threshold", 0.0)
                    if action and threshold is not None:
                        self.send_json(api_distillation_review_batch(
                            action=action,
                            threshold=float(threshold)
                        ))
                    else:
                        self.send_json({"success": False, "error": "Missing action or threshold"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            else:
                self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

        def do_DELETE(self):
            """Handle DELETE requests for fact removal (Phase 1.3.9)."""
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # DELETE /api/facts/<fact_id>
            if path.startswith("/api/facts/"):
                fact_id = path.split("/")[-1]
                if fact_id and fact_id not in ["context", "search", "remember"]:
                    self.send_json(api_facts_remove(fact_id))
                else:
                    self.send_json({"success": False, "error": "Invalid fact ID"}, 400)
            else:
                self.send_json({"success": False, "error": "DELETE not supported for this endpoint"}, 405)

    # Bind to all interfaces for network access (Tailscale, phone, etc.)
    server = HTTPServer(("0.0.0.0", port), SAMHandler)
    print(f"SAM API server running on http://0.0.0.0:{port}")
    print(f"  Local: http://localhost:{port}")
    print(f"  Network: http://100.100.11.31:{port} (Tailscale)")

    # Start idle watcher for auto-unload
    _start_idle_watcher()
    print("Endpoints:")
    print("  Legacy:")
    print("    GET  /api/status         - System status")
    print("    GET  /api/projects       - Project list")
    print("    GET  /api/memory         - Interaction history")
    print("    GET  /api/query?q=...    - Query SAM")
    print("    POST /api/query          - {\"query\": \"...\"}")
    print()
    print("  Intelligence:")
    print("    GET  /api/self           - SAM explains itself")
    print("    GET  /api/suggest        - Top improvement suggestions")
    print("    GET  /api/proactive      - What SAM noticed")
    print("    GET  /api/learning       - What SAM has learned")
    print("    GET  /api/scan           - Trigger improvement scan")
    print("    GET  /api/think?q=...    - SAM thinks about query")
    print("    GET  /api/think/colors   - Color scheme for thought types")
    print("    POST /api/feedback       - {improvement_id, success, impact, lessons}")
    print("    POST /api/think          - {\"query\": \"...\"}")
    print("    POST /api/think/stream   - SSE: {\"query\": \"...\", \"mode\": \"structured|coding|standard\"}")
    print("         → Stream of consciousness with thought type classification")
    print()
    print("  Cognitive (MLX + Full Pipeline):")
    print("    GET  /api/resources                - System resources (memory, model, limits)")
    print("    GET  /api/context/stats            - Compression monitoring (Phase 2.3.6)")
    print("         → tokens saved, avg compression, section usage, budget overruns")
    print("    GET  /api/unload                   - Unload model to free memory")
    print("    GET  /api/cognitive/state          - Cognitive system state")
    print("    GET  /api/cognitive/mood           - Current emotional state")
    print("    GET  /api/cognitive/process?q=...  - Process query (GET)")
    print("    POST /api/cognitive/process        - {\"query\": \"...\", \"user_id\": \"...\"}")
    print("    GET  /api/cognitive/feedback       - Feedback statistics")
    print("    GET  /api/cognitive/feedback/recent - Recent feedback (limit=, domain=, type=, session=)")
    print("    GET  /api/notifications            - Proactive feedback alerts (Phase 1.2.8)")
    print("         → daily corrections, negative feedback, training ready, accuracy drops")
    print("    POST /api/cognitive/feedback       - Save feedback (Phase 1.2 enhanced schema):")
    print("         {\"response_id\": \"...\", \"session_id\": \"...\", \"feedback_type\": \"rating|correction|preference|flag\",")
    print("          \"rating\": 1|-1, \"correction\": \"...\", \"domain\": \"code|reasoning|...\", ...}")
    print("    POST /api/cognitive/escalate       - {\"query\": \"...\"} → Claude browser bridge")
    print("    POST /api/cognitive/stream         - {\"query\": \"...\"} → SSE streaming tokens")
    print()
    print("  Vision (Multi-Modal MLX-VLM):")
    print("    GET  /api/vision/models            - List available vision models")
    print("    GET  /api/vision/stats             - Vision engine statistics")
    print("    GET  /api/vision/describe?path=... - Describe image (level=basic|medium|detailed)")
    print("    GET  /api/vision/detect?path=...   - Detect objects (target=optional)")
    print("    POST /api/vision/process           - {\"image_path\": \"...\", \"prompt\": \"...\", \"model\": \"...\"}")
    print("    POST /api/vision/analyze           - {\"image_base64\": \"...\", \"prompt\": \"...\"} (Swift UI)")
    print("    POST /api/vision/stream            - SSE: {\"image_base64\": \"...\", \"prompt\": \"...\"}")
    print("         -> Streams: status, token-by-token, done event (Phase 3.1.8)")
    print("    POST /api/vision/describe          - {\"image_path\": \"...\", \"detail_level\": \"medium\"}")
    print("    POST /api/vision/detect            - {\"image_path\": \"...\", \"target\": \"...\"}")
    print("    POST /api/vision/ocr               - {\"image_path\": \"...\"}  (uses Apple Vision)")
    print()
    print("  Smart Vision (Phase 3.5 - Auto-routed):")
    print("    GET  /api/vision/smart?path=...    - Smart routing (prompt, tier, skip_cache params)")
    print("    GET  /api/vision/smart/stats       - Cache statistics")
    print("    POST /api/vision/smart             - {\"image_path\": \"...\", \"prompt\": \"...\", \"force_tier\": \"...\"}")
    print("         Tiers: ZERO_COST (instant), LIGHTWEIGHT (fast), LOCAL_VLM (60s), CLAUDE (complex)")
    print()
    print("  Image Context (Phase 3.1.5 - Follow-up Questions):")
    print("    GET  /api/image/context            - Get current image context for follow-ups")
    print("    GET  /api/image/context/clear      - Clear image context")
    print("    GET  /api/image/followup/check?q=  - Check if query is a follow-up question")
    print("    POST /api/image/chat               - {\"query\": \"...\", \"image_path\": \"...\", \"image_base64\": \"...\"}")
    print("         Examples:")
    print("           {\"query\": \"What's this?\", \"image_path\": \"/tmp/photo.jpg\"} - New image")
    print("           {\"query\": \"What color is the car?\"}                          - Follow-up")
    print("           {\"query\": \"Can you read the text in it?\"}                    - Follow-up")
    print()
    print("  Project Context (Phase 2):")
    print("    GET  /api/project?path=...         - Detect project, get context")
    print("    GET  /api/project/recent           - Recently accessed projects")
    print("    GET  /api/project/todos?path=...   - TODOs for project")
    print("    POST /api/project/session          - {\"path\": \"...\", \"working_on\": \"...\", \"notes\": \"...\"}")
    print()
    print("  Intelligence Core (Phase 1):")
    print("    GET  /api/intelligence             - Distillation, feedback, memory stats")
    print("    GET  /api/facts?user=...           - Facts known about user")
    print("    POST /api/facts/remember           - {\"user_id\": \"...\", \"fact\": \"...\", \"category\": \"...\"}")
    print()
    print("  Fact Management (Phase 1.3.9):")
    print("    GET  /api/facts                    - List facts (user=, category=, min_confidence=, limit=)")
    print("    GET  /api/facts/<id>               - Get single fact by ID")
    print("    GET  /api/facts/search?q=...       - Search facts (user=, limit=)")
    print("    GET  /api/facts/context?user=...   - Get formatted context for prompts")
    print("    POST /api/facts                    - {\"fact\": \"...\", \"category\": \"...\", \"user_id\": \"...\", \"source\": \"...\"}")
    print("    DELETE /api/facts/<id>             - Remove (deactivate) a fact")
    print("         Categories: preferences, biographical, projects, skills, corrections, relationships, context, system")
    print("         Sources: explicit, conversation, correction, inferred, system")
    print()
    print("  Code Index (Phase 2.2):")
    print("    GET  /api/code/search?q=...        - Search indexed code (project=, type=, limit=)")
    print("    GET  /api/code/stats               - Code index statistics (project=)")
    print("    POST /api/code/index               - {\"path\": \"...\", \"project_id\": \"...\", \"force\": false}")
    print()
    print("  Index Management (Phase 2.2.10):")
    print("    GET  /api/index/status             - Comprehensive index statistics")
    print("    GET  /api/index/search?q=...       - Search index (project=, type=, limit=)")
    print("    GET  /api/index/watch/stop         - Stop file watcher")
    print("    POST /api/index/build              - {\"path\": \"...\", \"project_id\": \"...\", \"force\": false}")
    print("    POST /api/index/clear              - {\"project_id\": \"...\"} (null to clear all)")
    print("    POST /api/index/watch              - {\"path\": \"...\", \"project_id\": \"...\"} - Start watcher")
    print()
    print("  Voice Pipeline (Emotion + Conversation + Prosody):")
    print("    GET  /api/voice/start              - Start voice pipeline")
    print("    GET  /api/voice/stop               - Stop voice pipeline")
    print("    GET  /api/voice/status             - Pipeline status, stats, current emotion")
    print("    GET  /api/voice/emotion            - Current detected user emotion + trajectory")
    print("    GET  /api/voice/config             - Get pipeline configuration")
    print("    GET  /api/voice/conversation       - Full conversation state + turn history")
    print("    POST /api/voice/config             - Update config: {response_strategy, backchannel_probability, ...}")
    print("    POST /api/voice/process            - {\"audio_base64\": \"...\"} → process audio chunk")
    print("    POST /api/voice/stream             - SSE: {\"audio_base64\": \"...\"} → stream events")
    print("         Events: backchannel, response_start, user_speaking, user_finished, turn_change")
    print()
    print("  Knowledge Distillation Review (Phase 1.1.8):")
    print("    GET  /api/distillation/review      - Get pending examples (limit=, domain=)")
    print("    GET  /api/distillation/review/stats - Review queue statistics")
    print("    GET  /api/distillation/review/<id> - Get full details for example")
    print("    POST /api/distillation/review      - {\"example_id\": \"...\", \"action\": \"approve|reject\", \"notes\": \"...\"}")
    print("    POST /api/distillation/review/batch - {\"action\": \"approve|reject\", \"threshold\": 0.7}")
    print("         Auto-approve examples >= threshold, or auto-reject examples < threshold")
    print()
    server.serve_forever()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "query":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_query(query), indent=2))

    elif cmd == "projects":
        print(json.dumps(api_projects(), indent=2))

    elif cmd == "memory":
        print(json.dumps(api_memory(), indent=2))

    elif cmd == "status":
        print(json.dumps(api_status(), indent=2))

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_search(query), indent=2))

    elif cmd == "categories":
        print(json.dumps(api_categories(), indent=2))

    elif cmd == "starred":
        print(json.dumps(api_starred(), indent=2))

    elif cmd == "speak":
        text = " ".join(sys.argv[2:])
        print(json.dumps(api_speak(text), indent=2))

    elif cmd == "voices":
        print(json.dumps(api_voices(), indent=2))

    # SAM Intelligence commands
    elif cmd == "self":
        print(json.dumps(api_self(), indent=2))

    elif cmd == "suggest":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(json.dumps(api_suggest(limit), indent=2))

    elif cmd == "proactive":
        print(json.dumps(api_proactive(), indent=2))

    elif cmd == "learning":
        print(json.dumps(api_learning(), indent=2))

    elif cmd == "feedback":
        # Expects JSON input: {"improvement_id": "...", "success": true, "impact": 0.8, "lessons": "..."}
        if len(sys.argv) > 2:
            try:
                data = json.loads(sys.argv[2])
                result = api_feedback(
                    data.get("improvement_id", ""),
                    data.get("success", True),
                    data.get("impact", 0.5),
                    data.get("lessons", "")
                )
                print(json.dumps(result, indent=2))
            except json.JSONDecodeError:
                print(json.dumps({"success": False, "error": "Invalid JSON"}, indent=2))
        else:
            print(json.dumps({"success": False, "error": "Provide JSON: {improvement_id, success, impact, lessons}"}, indent=2))

    elif cmd == "scan":
        print(json.dumps(api_scan(), indent=2))

    elif cmd == "think":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_think(query), indent=2))

    elif cmd == "context":
        # Output the Claude context file for easy pasting
        context_file = SCRIPT_DIR / "warp_knowledge" / "CLAUDE_CONTEXT.md"
        if context_file.exists():
            print(context_file.read_text())
        else:
            print("Context file not found. Run analysis first.")

    elif cmd == "warp-status":
        # Output the Warp replication status
        status_file = SCRIPT_DIR / "warp_knowledge" / "WARP_REPLICATION_STATUS.md"
        if status_file.exists():
            print(status_file.read_text())
        else:
            print("Status file not found.")

    # ============ Fact Management CLI (Phase 1.3.9) ============
    elif cmd == "facts":
        # Subcommand handling: facts list|add|remove|search
        if len(sys.argv) < 3:
            print("Usage: sam_api.py facts <subcommand> [options]")
            print()
            print("Subcommands:")
            print("  list [--user X] [--category X] [--min-confidence 0.5]")
            print("  add \"fact\" --category X [--user X] [--source explicit]")
            print("  remove <fact_id>")
            print("  search \"query\" [--user X]")
            print("  get <fact_id>")
            print()
            print("Categories: preferences, biographical, projects, skills, corrections, relationships, context, system")
            print("Sources: explicit, conversation, correction, inferred, system")
            return

        subcmd = sys.argv[2]

        if subcmd == "list":
            # Parse optional arguments
            user_id = "david"
            category = None
            min_confidence = 0.0
            limit = 50

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                    category = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--min-confidence" and i + 1 < len(sys.argv):
                    min_confidence = float(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_facts_list(user_id, category, min_confidence, limit), indent=2))

        elif subcmd == "add":
            # Parse: facts add "fact text" --category X [--user X] [--source X] [--confidence X]
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts add \"fact\" --category <category> [--user X] [--source X]")
                return

            fact_text = sys.argv[3]
            user_id = "david"
            category = None
            source = "explicit"
            confidence = None

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                    category = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--source" and i + 1 < len(sys.argv):
                    source = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--confidence" and i + 1 < len(sys.argv):
                    confidence = float(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            if not category:
                print("Error: --category is required")
                print("Categories: preferences, biographical, projects, skills, corrections, relationships, context, system")
                return

            print(json.dumps(api_facts_add(fact_text, category, user_id, source, confidence), indent=2))

        elif subcmd == "remove":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts remove <fact_id>")
                return

            fact_id = sys.argv[3]
            print(json.dumps(api_facts_remove(fact_id), indent=2))

        elif subcmd == "search":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts search \"query\" [--user X]")
                return

            query = sys.argv[3]
            user_id = "david"
            limit = 10

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_facts_search(query, user_id, limit), indent=2))

        elif subcmd == "get":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts get <fact_id>")
                return

            fact_id = sys.argv[3]
            print(json.dumps(api_facts_get(fact_id), indent=2))

        else:
            print(f"Unknown facts subcommand: {subcmd}")
            print("Available: list, add, remove, search, get")

    # ============ Index Management CLI (Phase 2.2.10) ============
    elif cmd == "index":
        # Subcommand handling: index status|build|search|watch|clear
        if len(sys.argv) < 3:
            print("Usage: sam_api.py index <subcommand> [options]")
            print()
            print("Subcommands:")
            print("  status                     - Show index statistics")
            print("  build [path] [--project X] [--force]  - Build/rebuild index")
            print("  search \"query\" [--project X] [--type X] [--limit N]")
            print("  watch [path] [--project X] - Start file watcher")
            print("  stop                       - Stop file watcher")
            print("  clear [--project X]        - Clear index (all or specific project)")
            print()
            print("Examples:")
            print("  sam_api.py index status")
            print("  sam_api.py index build ~/Projects/myapp --project myapp")
            print("  sam_api.py index search \"parse function\"")
            print("  sam_api.py index watch . --project current")
            print("  sam_api.py index clear --project myapp")
            return

        subcmd = sys.argv[2]

        if subcmd == "status":
            print(json.dumps(api_index_status(), indent=2))

        elif subcmd == "build":
            # Parse: index build [path] [--project X] [--force]
            path = "."
            project_id = None
            force = False

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--force":
                    force = True
                    i += 1
                elif not sys.argv[i].startswith("-"):
                    path = sys.argv[i]
                    i += 1
                else:
                    i += 1

            print(json.dumps(api_index_build(path, project_id, force), indent=2))

        elif subcmd == "search":
            # Parse: index search "query" [--project X] [--type X] [--limit N]
            if len(sys.argv) < 4:
                print("Usage: sam_api.py index search \"query\" [--project X] [--type X] [--limit N]")
                return

            query = sys.argv[3]
            project_id = None
            entity_type = None
            limit = 10

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                    entity_type = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_code_search(query, project_id, entity_type, limit), indent=2))

        elif subcmd == "watch":
            # Parse: index watch [path] [--project X]
            path = "."
            project_id = None

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif not sys.argv[i].startswith("-"):
                    path = sys.argv[i]
                    i += 1
                else:
                    i += 1

            result = api_index_watch(path, project_id)
            print(json.dumps(result, indent=2))

            # If watch started successfully, keep running
            if result.get("success"):
                print("\nWatching for file changes. Press Ctrl+C to stop.")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    api_index_watch_stop()
                    print("\nWatcher stopped.")

        elif subcmd == "stop":
            print(json.dumps(api_index_watch_stop(), indent=2))

        elif subcmd == "clear":
            # Parse: index clear [--project X]
            project_id = None

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1

            # Confirmation for clearing all
            if project_id is None:
                print("Warning: This will clear the ENTIRE code index.")
                confirm = input("Type 'yes' to confirm: ")
                if confirm.lower() != "yes":
                    print("Cancelled.")
                    return

            print(json.dumps(api_index_clear(project_id), indent=2))

        else:
            print(f"Unknown index subcommand: {subcmd}")
            print("Available: status, build, search, watch, stop, clear")

    elif cmd == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        run_server(port)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
