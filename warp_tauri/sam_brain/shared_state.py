"""
SAM API Shared State - Singletons, monitors, accessors, and constants.

Extracted from sam_api.py to enable route modules to share state.
"""

import os
import sys
import json
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

# Approval Queue (Phase 4.1 - lazy loaded)
try:
    from serve.approval_queue import (
        api_approval_queue, api_approval_approve, api_approval_reject,
        api_approval_history, api_approval_get, api_approval_stats
    )
    APPROVAL_AVAILABLE = True
except ImportError:
    APPROVAL_AVAILABLE = False

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
            from learn.feedback_system import FeedbackDB
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
            from learn.knowledge_distillation import DistillationDB
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
            from learn.sam_intelligence import SamIntelligence
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


# ============ Cognitive Orchestrator Singleton ============

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


# ============ Idle Management ============

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


# ============ Index Watcher Globals ============

_index_watcher = None
_watcher_observer = None


# ============ Vision Engine Singleton ============

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


# ============ Smart Vision Router Singleton ============

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


# ============ Voice Pipeline Singleton ============

_voice_pipeline = None

def get_voice_pipeline():
    """Lazy-load voice pipeline singleton."""
    global _voice_pipeline
    if _voice_pipeline is None:
        try:
            from voice.voice_pipeline import SAMVoicePipeline, VoicePipelineConfig
            _voice_pipeline = SAMVoicePipeline()
        except Exception as e:
            print(f"Warning: Could not load voice pipeline: {e}", file=sys.stderr)
            return None
    return _voice_pipeline
