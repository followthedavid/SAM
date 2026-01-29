"""
Resource Manager for SAM Cognitive System

Prevents system freezes by:
1. Monitoring available memory before model loads
2. Enforcing request queuing (max 1 concurrent heavy operation)
3. Configurable resource caps
4. Graceful degradation when resources are low
5. Vision model lifecycle tracking (load/unload/auto-cleanup)

Designed for 8GB M2 Mac Mini - prioritizes stability over speed.
"""

import os
import time
import threading
from typing import Optional, Dict, Any, Callable, TypeVar, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import json
from pathlib import Path

if TYPE_CHECKING:
    from .vision_engine import VisionEngine


class ResourceLevel(Enum):
    """Current resource availability level."""
    CRITICAL = "critical"   # < 1GB free - refuse heavy operations
    LOW = "low"             # 1-2GB free - use smallest models only
    MODERATE = "moderate"   # 2-4GB free - normal operation
    GOOD = "good"           # > 4GB free - full capability


# Training resource thresholds for 8GB M2 Mac Mini
TRAINING_MIN_FREE_RAM_GB = 2.0      # Don't train unless 2GB+ RAM free
TRAINING_MAX_SWAP_USED_GB = 3.0     # Don't train if swap exceeds 3GB
TRAINING_MIN_DISK_FREE_GB = 20.0    # Don't train if disk < 20GB free


from .vision_types import VisionTier


class VoiceTier(Enum):
    """Voice processing tiers for TTS and voice conversion."""
    MACOS_SAY = "macos_say"     # macOS built-in say command - 0 RAM, instant
    EDGE_TTS = "edge_tts"       # Edge TTS (network) - ~50MB
    COQUI = "coqui"             # Coqui TTS - ~500MB-1GB
    F5_TTS = "f5_tts"           # F5-TTS - ~1.5GB
    RVC = "rvc"                 # RVC voice conversion - ~2GB additional


# Memory requirements per vision tier (in MB)
VISION_TIER_MEMORY_MB = {
    VisionTier.ZERO_COST: 0,
    VisionTier.LIGHTWEIGHT: 200,
    VisionTier.LOCAL_VLM: 1500,  # nanoLLaVA default
    VisionTier.CLAUDE: 0,
}

# Memory requirements per voice tier (in MB)
VOICE_TIER_MEMORY_MB = {
    VoiceTier.MACOS_SAY: 0,      # Uses system process, negligible
    VoiceTier.EDGE_TTS: 50,      # Minimal network client
    VoiceTier.COQUI: 800,        # Tacotron2 model
    VoiceTier.F5_TTS: 1500,      # F5-TTS model
    VoiceTier.RVC: 2000,         # RVC model (additional on top of TTS)
}


@dataclass
class VisionModelState:
    """Tracks vision model lifecycle state."""
    is_loaded: bool = False
    tier: Optional[VisionTier] = None
    model_name: Optional[str] = None
    memory_used_mb: float = 0.0
    last_used: Optional[datetime] = None
    load_count: int = 0
    unload_count: int = 0
    auto_unload_after_seconds: float = 300.0  # 5 minutes default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_loaded": self.is_loaded,
            "tier": self.tier.name if self.tier else None,
            "model_name": self.model_name,
            "memory_used_mb": round(self.memory_used_mb, 1),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "load_count": self.load_count,
            "unload_count": self.unload_count,
            "auto_unload_after_seconds": self.auto_unload_after_seconds,
            "should_unload": self.should_auto_unload(),
        }

    def should_auto_unload(self) -> bool:
        """Check if model should be auto-unloaded due to inactivity."""
        if not self.is_loaded or not self.last_used:
            return False
        elapsed = (datetime.now() - self.last_used).total_seconds()
        return elapsed > self.auto_unload_after_seconds


@dataclass
class VoiceResourceState:
    """
    Tracks voice/TTS resource state.

    Task 6.2.3: Voice resource management for 8GB RAM constraint.
    """
    tts_model_loaded: bool = False
    rvc_model_loaded: bool = False
    tts_tier: Optional[VoiceTier] = None
    rvc_model_name: Optional[str] = None
    estimated_voice_ram_mb: float = 0.0
    last_used: Optional[datetime] = None
    use_count: int = 0

    # Quality vs performance thresholds
    quality_ram_threshold_mb: float = 2500.0  # Need this much free for F5+RVC
    fallback_ram_threshold_mb: float = 500.0   # Below this, use macOS say only

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tts_model_loaded": self.tts_model_loaded,
            "rvc_model_loaded": self.rvc_model_loaded,
            "tts_tier": self.tts_tier.value if self.tts_tier else None,
            "rvc_model_name": self.rvc_model_name,
            "estimated_voice_ram_mb": round(self.estimated_voice_ram_mb, 1),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
        }

    def can_use_quality_voice(self, available_ram_mb: float) -> bool:
        """
        Check if enough RAM is available for high-quality voice (F5-TTS + RVC).

        Args:
            available_ram_mb: Currently available RAM in MB

        Returns:
            True if quality voice can be used
        """
        return available_ram_mb >= self.quality_ram_threshold_mb

    def should_use_fallback(self, available_ram_mb: float) -> bool:
        """
        Check if should fall back to basic TTS (macOS say).

        Returns True if:
        - Available RAM is below fallback threshold
        - System is under heavy load
        - Quality TTS models not available

        Args:
            available_ram_mb: Currently available RAM in MB

        Returns:
            True if fallback voice should be used
        """
        return available_ram_mb < self.fallback_ram_threshold_mb

    def get_recommended_tier(self, available_ram_mb: float) -> VoiceTier:
        """
        Get recommended voice tier based on available RAM.

        Args:
            available_ram_mb: Currently available RAM in MB

        Returns:
            Recommended VoiceTier
        """
        if available_ram_mb >= VOICE_TIER_MEMORY_MB[VoiceTier.F5_TTS] + VOICE_TIER_MEMORY_MB[VoiceTier.RVC] + 500:
            return VoiceTier.F5_TTS  # Best quality
        elif available_ram_mb >= VOICE_TIER_MEMORY_MB[VoiceTier.COQUI] + 500:
            return VoiceTier.COQUI  # Good quality
        elif available_ram_mb >= VOICE_TIER_MEMORY_MB[VoiceTier.EDGE_TTS] + 200:
            return VoiceTier.EDGE_TTS  # Network-based, low RAM
        else:
            return VoiceTier.MACOS_SAY  # Fallback, zero RAM


@dataclass
class ResourceConfig:
    """Configurable resource limits."""
    # Memory thresholds (in GB) - tuned for 8GB M2 Mac Mini WITH other apps running
    # Reality: Safari + Claude Code + OS = ~7GB used, leaving ~1GB
    # These are AFTER safety margin is applied
    memory_critical_gb: float = 0.2   # Below this: refuse (true emergency only)
    memory_low_gb: float = 0.4        # Below this: minimal tokens
    memory_moderate_gb: float = 0.7   # Below this: reduced tokens
    # Above moderate = GOOD: normal operation (0.7GB+ available)

    # Request limits
    max_concurrent_heavy_ops: int = 1
    max_queue_size: int = 5
    request_timeout_seconds: float = 120.0

    # Model limits - realistic for always-running system
    max_tokens_critical: int = 50     # Emergency minimal
    max_tokens_low: int = 100         # Short but useful
    max_tokens_moderate: int = 150    # Normal response
    max_tokens_good: int = 200        # Full response (still conservative)

    # Safety margins - minimal since model stays cached
    memory_safety_margin_gb: float = 0.1  # Very small - model is cached
    cooldown_after_heavy_op_seconds: float = 0.0  # No cooldown - model is cached

    # Vision model settings
    vision_auto_unload_seconds: float = 300.0  # Unload after 5 minutes of inactivity
    vision_min_memory_mb: float = 500.0  # Minimum free memory to load vision model
    vision_reserve_for_llm_mb: float = 800.0  # Reserve this much for LLM operations

    @classmethod
    def load_from_file(cls, path: str = None) -> "ResourceConfig":
        """Load config from file, with defaults as fallback."""
        if path is None:
            path = "/Volumes/David External/sam_memory/resource_config.json"

        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                return cls(**data)
        except Exception:
            pass

        return cls()

    def save_to_file(self, path: str = None):
        """Save current config to file."""
        if path is None:
            path = "/Volumes/David External/sam_memory/resource_config.json"

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump({
                'memory_critical_gb': self.memory_critical_gb,
                'memory_low_gb': self.memory_low_gb,
                'memory_moderate_gb': self.memory_moderate_gb,
                'max_concurrent_heavy_ops': self.max_concurrent_heavy_ops,
                'max_queue_size': self.max_queue_size,
                'request_timeout_seconds': self.request_timeout_seconds,
                'max_tokens_critical': self.max_tokens_critical,
                'max_tokens_low': self.max_tokens_low,
                'max_tokens_moderate': self.max_tokens_moderate,
                'max_tokens_good': self.max_tokens_good,
                'memory_safety_margin_gb': self.memory_safety_margin_gb,
                'cooldown_after_heavy_op_seconds': self.cooldown_after_heavy_op_seconds,
                'vision_auto_unload_seconds': self.vision_auto_unload_seconds,
                'vision_min_memory_mb': self.vision_min_memory_mb,
                'vision_reserve_for_llm_mb': self.vision_reserve_for_llm_mb,
            }, f, indent=2)


@dataclass
class ResourceSnapshot:
    """Current system resource state."""
    available_memory_gb: float
    total_memory_gb: float
    memory_percent_used: float
    resource_level: ResourceLevel
    active_heavy_ops: int
    queue_length: int
    vision_state: Optional[Dict[str, Any]] = None
    voice_state: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'available_memory_gb': round(self.available_memory_gb, 2),
            'total_memory_gb': round(self.total_memory_gb, 2),
            'memory_percent_used': round(self.memory_percent_used, 1),
            'resource_level': self.resource_level.value,
            'active_heavy_ops': self.active_heavy_ops,
            'queue_length': self.queue_length,
            'timestamp': self.timestamp.isoformat()
        }
        if self.vision_state:
            result['vision'] = self.vision_state
        if self.voice_state:
            result['voice'] = self.voice_state
        return result


@dataclass
class OperationResult:
    """Result of a resource-managed operation."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    waited_seconds: float = 0.0
    resource_level_at_start: ResourceLevel = ResourceLevel.MODERATE


T = TypeVar('T')


class ResourceManager:
    """
    Manages system resources to prevent freezes.

    Usage:
        manager = ResourceManager()

        # Check before heavy operation
        if manager.can_perform_heavy_operation():
            with manager.heavy_operation_context():
                # do model loading/generation
                pass

        # Or use the wrapper
        result = manager.execute_with_limits(heavy_function, args)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - one resource manager for the whole system."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = ResourceConfig.load_from_file()
        self._heavy_op_semaphore = threading.Semaphore(self.config.max_concurrent_heavy_ops)
        self._active_heavy_ops = 0
        self._ops_lock = threading.Lock()
        self._request_queue: deque = deque(maxlen=self.config.max_queue_size)
        self._last_heavy_op_end: Optional[datetime] = None
        self._stats = {
            'total_requests': 0,
            'rejected_requests': 0,
            'queued_requests': 0,
            'completed_requests': 0,
            'timeouts': 0,
        }

        # Vision model tracking
        self._vision_state = VisionModelState(
            auto_unload_after_seconds=self.config.vision_auto_unload_seconds
        )
        self._vision_lock = threading.Lock()
        self._vision_engine_ref: Optional["VisionEngine"] = None
        self._auto_unload_timer: Optional[threading.Timer] = None

        # Voice resource tracking (Task 6.2.3)
        self._voice_state = VoiceResourceState()
        self._voice_lock = threading.Lock()

        self._initialized = True

    def get_memory_info(self) -> tuple[float, float]:
        """
        Get available and total memory in GB.

        Uses vm_stat on macOS for accurate memory info.
        """
        try:
            import subprocess

            # Get page size
            pagesize = int(subprocess.check_output(['pagesize']).decode().strip())

            # Get vm_stat output
            vm_stat = subprocess.check_output(['vm_stat']).decode()

            # Parse the stats
            stats = {}
            for line in vm_stat.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    # Remove trailing period and convert to int
                    value = value.strip().rstrip('.')
                    try:
                        stats[key.strip()] = int(value)
                    except ValueError:
                        pass

            # Calculate available memory (free + inactive + speculative)
            free_pages = stats.get('Pages free', 0)
            inactive_pages = stats.get('Pages inactive', 0)
            speculative_pages = stats.get('Pages speculative', 0)

            available_bytes = (free_pages + inactive_pages + speculative_pages) * pagesize
            available_gb = available_bytes / (1024 ** 3)

            # Get total memory
            total_bytes = int(subprocess.check_output(
                ['sysctl', '-n', 'hw.memsize']
            ).decode().strip())
            total_gb = total_bytes / (1024 ** 3)

            return available_gb, total_gb

        except Exception as e:
            # Fallback: assume 8GB total, 2GB available (conservative)
            return 2.0, 8.0

    def get_swap_usage_gb(self) -> float:
        """Get current swap usage in GB."""
        try:
            import subprocess
            import re
            swap_out = subprocess.check_output(['sysctl', 'vm.swapusage']).decode()
            # Format: "vm.swapusage: total = 3072.00M  used = 1448.38M  free = 1623.62M  (encrypted)"
            match = re.search(r'used\s*=\s*([\d.]+)M', swap_out)
            if match:
                return float(match.group(1)) / 1024.0
        except Exception:
            pass
        return 99.0  # Assume worst case on failure

    def get_disk_free_gb(self, path: str = '/') -> float:
        """Get free disk space in GB for the given path."""
        try:
            import subprocess
            df_out = subprocess.check_output(['df', '-g', path]).decode()
            for line in df_out.strip().split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    return float(parts[3])
        except Exception:
            pass
        return 0.0  # Assume worst case on failure

    def can_train(self) -> tuple[bool, str]:
        """
        Check if the system has enough resources for MLX LoRA training.

        Checks RAM, swap, and disk. Used by both perpetual_learner and
        auto_learner to gate training runs.

        Returns:
            (can_train, reason) tuple
        """
        free_ram_gb, _ = self.get_memory_info()
        swap_used_gb = self.get_swap_usage_gb()
        disk_free_gb = self.get_disk_free_gb()

        if free_ram_gb < TRAINING_MIN_FREE_RAM_GB:
            return False, f"RAM too low: {free_ram_gb:.1f}GB free (need {TRAINING_MIN_FREE_RAM_GB}GB)"
        if swap_used_gb > TRAINING_MAX_SWAP_USED_GB:
            return False, f"Swap too high: {swap_used_gb:.1f}GB used (max {TRAINING_MAX_SWAP_USED_GB}GB)"
        if disk_free_gb < TRAINING_MIN_DISK_FREE_GB:
            return False, f"Disk too low: {disk_free_gb:.0f}GB free (need {TRAINING_MIN_DISK_FREE_GB}GB)"
        return True, f"OK: RAM={free_ram_gb:.1f}GB, swap={swap_used_gb:.1f}GB, disk={disk_free_gb:.0f}GB"

    def get_resource_level(self) -> ResourceLevel:
        """Determine current resource availability level."""
        available_gb, _ = self.get_memory_info()

        # Apply safety margin
        effective_available = available_gb - self.config.memory_safety_margin_gb

        if effective_available < self.config.memory_critical_gb:
            return ResourceLevel.CRITICAL
        elif effective_available < self.config.memory_low_gb:
            return ResourceLevel.LOW
        elif effective_available < self.config.memory_moderate_gb:
            return ResourceLevel.MODERATE
        else:
            return ResourceLevel.GOOD

    def get_snapshot(self) -> ResourceSnapshot:
        """Get current resource state snapshot."""
        available_gb, total_gb = self.get_memory_info()

        return ResourceSnapshot(
            available_memory_gb=available_gb,
            total_memory_gb=total_gb,
            memory_percent_used=((total_gb - available_gb) / total_gb) * 100,
            resource_level=self.get_resource_level(),
            active_heavy_ops=self._active_heavy_ops,
            queue_length=len(self._request_queue),
            vision_state=self._vision_state.to_dict() if self._vision_state else None,
            voice_state=self._voice_state.to_dict() if self._voice_state else None
        )

    # =========================================================================
    # VISION MODEL MANAGEMENT
    # =========================================================================

    def get_vision_status(self) -> Dict[str, Any]:
        """
        Get current vision model status.

        Returns:
            Dict with vision model state including:
            - is_loaded: bool
            - tier: current tier if loaded
            - model_name: name of loaded model
            - memory_used_mb: memory consumed
            - last_used: when last used
            - should_unload: if auto-unload is recommended
            - available_memory_mb: current free memory
            - can_load_local_vlm: whether LOCAL_VLM tier is possible
        """
        with self._vision_lock:
            available_gb, _ = self.get_memory_info()
            available_mb = available_gb * 1024

            status = self._vision_state.to_dict()
            status['available_memory_mb'] = round(available_mb, 1)
            status['can_load_local_vlm'] = self.can_load_vision_model(VisionTier.LOCAL_VLM)
            status['recommended_tier'] = self._recommend_vision_tier().name

            return status

    def can_load_vision_model(self, tier: VisionTier = VisionTier.LOCAL_VLM) -> bool:
        """
        Check if enough RAM is available to load a vision model.

        Args:
            tier: The vision tier to check (default: LOCAL_VLM)

        Returns:
            True if the model can be loaded safely
        """
        # Zero-cost and Claude tiers always OK
        if tier in (VisionTier.ZERO_COST, VisionTier.CLAUDE):
            return True

        available_gb, _ = self.get_memory_info()
        available_mb = available_gb * 1024

        # Get memory requirement for this tier
        required_mb = VISION_TIER_MEMORY_MB.get(tier, 1500)

        # Reserve space for LLM operations
        reserve_mb = self.config.vision_reserve_for_llm_mb

        # Need: required memory + reserve + minimum threshold
        min_needed = required_mb + reserve_mb + self.config.vision_min_memory_mb

        return available_mb >= min_needed

    def request_vision_resources(self, tier: VisionTier) -> bool:
        """
        Request resources to load a vision model.

        If resources are available, marks the model as loading.
        If a different model is loaded, triggers unload first.

        Args:
            tier: The vision tier being requested

        Returns:
            True if resources are available and reserved
        """
        with self._vision_lock:
            # Cancel any pending auto-unload timer
            if self._auto_unload_timer:
                self._auto_unload_timer.cancel()
                self._auto_unload_timer = None

            # Check if we can load this tier
            if not self.can_load_vision_model(tier):
                return False

            # If a different model is loaded, unload it first
            if self._vision_state.is_loaded and self._vision_state.tier != tier:
                self._trigger_vision_unload()

            return True

    def notify_vision_loaded(
        self,
        tier: VisionTier,
        model_name: str,
        memory_used_mb: float
    ) -> None:
        """
        Called by vision_engine when a model has been loaded.

        Args:
            tier: The tier that was loaded
            model_name: Name/ID of the model
            memory_used_mb: Estimated memory usage
        """
        with self._vision_lock:
            self._vision_state.is_loaded = True
            self._vision_state.tier = tier
            self._vision_state.model_name = model_name
            self._vision_state.memory_used_mb = memory_used_mb
            self._vision_state.last_used = datetime.now()
            self._vision_state.load_count += 1

            # Schedule auto-unload timer
            self._schedule_auto_unload()

    def notify_vision_used(self) -> None:
        """
        Called by vision_engine when the model is used for inference.
        Resets the auto-unload timer.
        """
        with self._vision_lock:
            if self._vision_state.is_loaded:
                self._vision_state.last_used = datetime.now()
                # Reschedule auto-unload
                self._schedule_auto_unload()

    def notify_vision_unloaded(self) -> None:
        """
        Called by vision_engine when a model has been unloaded.
        """
        with self._vision_lock:
            if self._vision_state.is_loaded:
                self._vision_state.unload_count += 1

            self._vision_state.is_loaded = False
            self._vision_state.tier = None
            self._vision_state.model_name = None
            self._vision_state.memory_used_mb = 0.0

            # Cancel any pending auto-unload
            if self._auto_unload_timer:
                self._auto_unload_timer.cancel()
                self._auto_unload_timer = None

    def register_vision_engine(self, engine: "VisionEngine") -> None:
        """
        Register the vision engine for auto-unload callbacks.

        Args:
            engine: The VisionEngine instance to manage
        """
        self._vision_engine_ref = engine

    def _recommend_vision_tier(self) -> VisionTier:
        """
        Recommend the best vision tier based on current resources.

        Returns:
            The recommended VisionTier
        """
        available_gb, _ = self.get_memory_info()
        available_mb = available_gb * 1024

        # Check tiers from highest to lowest capability
        if self.can_load_vision_model(VisionTier.LOCAL_VLM):
            return VisionTier.LOCAL_VLM
        elif self.can_load_vision_model(VisionTier.LIGHTWEIGHT):
            return VisionTier.LIGHTWEIGHT
        else:
            # Fall back to zero-cost or Claude
            return VisionTier.ZERO_COST

    def _schedule_auto_unload(self) -> None:
        """Schedule automatic unload of vision model after inactivity."""
        # Cancel existing timer
        if self._auto_unload_timer:
            self._auto_unload_timer.cancel()

        # Schedule new timer
        timeout = self._vision_state.auto_unload_after_seconds
        self._auto_unload_timer = threading.Timer(
            timeout,
            self._auto_unload_callback
        )
        self._auto_unload_timer.daemon = True
        self._auto_unload_timer.start()

    def _auto_unload_callback(self) -> None:
        """Timer callback to check and trigger auto-unload."""
        with self._vision_lock:
            if self._vision_state.should_auto_unload():
                self._trigger_vision_unload()

    def _trigger_vision_unload(self) -> None:
        """Trigger unload of vision model via registered engine."""
        if self._vision_engine_ref:
            try:
                self._vision_engine_ref.unload_models()
                self.notify_vision_unloaded()
            except Exception as e:
                # Log but don't raise - this is called from timer
                import logging
                logging.getLogger("resource_manager").warning(
                    f"Failed to auto-unload vision model: {e}"
                )

    def force_vision_unload(self) -> bool:
        """
        Force immediate unload of vision model.

        Useful when memory is critically low.

        Returns:
            True if model was unloaded, False if none was loaded
        """
        with self._vision_lock:
            if not self._vision_state.is_loaded:
                return False

            self._trigger_vision_unload()
            return True

    # =========================================================================
    # VOICE RESOURCE MANAGEMENT (Task 6.2.3)
    # =========================================================================

    def get_voice_status(self) -> Dict[str, Any]:
        """
        Get current voice resource status.

        Returns:
            Dict with voice state including:
            - tts_model_loaded: bool
            - rvc_model_loaded: bool
            - tts_tier: current TTS tier
            - estimated_voice_ram_mb: estimated RAM usage
            - can_use_quality_voice: if high-quality voice is available
            - should_use_fallback: if fallback (macOS say) is recommended
            - recommended_tier: best tier for current resources
        """
        with self._voice_lock:
            available_gb, _ = self.get_memory_info()
            available_mb = available_gb * 1024

            status = self._voice_state.to_dict()
            status['available_memory_mb'] = round(available_mb, 1)
            status['can_use_quality_voice'] = self._voice_state.can_use_quality_voice(available_mb)
            status['should_use_fallback'] = self._voice_state.should_use_fallback(available_mb)
            status['recommended_tier'] = self._voice_state.get_recommended_tier(available_mb).value

            return status

    def can_use_quality_voice(self) -> bool:
        """
        Check if enough RAM is available for high-quality voice (F5-TTS + RVC).

        Returns:
            True if quality voice can be used
        """
        available_gb, _ = self.get_memory_info()
        available_mb = available_gb * 1024
        return self._voice_state.can_use_quality_voice(available_mb)

    def should_use_voice_fallback(self) -> bool:
        """
        Check if should fall back to basic TTS (macOS say).

        Returns True if:
        - Available RAM is below threshold
        - Quality TTS not available
        - System under heavy load
        """
        available_gb, _ = self.get_memory_info()
        available_mb = available_gb * 1024
        return self._voice_state.should_use_fallback(available_mb)

    def get_recommended_voice_tier(self) -> VoiceTier:
        """
        Get recommended voice tier based on available resources.

        Returns:
            VoiceTier enum value
        """
        available_gb, _ = self.get_memory_info()
        available_mb = available_gb * 1024
        return self._voice_state.get_recommended_tier(available_mb)

    def notify_voice_loaded(
        self,
        tier: VoiceTier,
        memory_used_mb: float,
        rvc_model: Optional[str] = None
    ) -> None:
        """
        Called when a TTS/voice model is loaded.

        Args:
            tier: The voice tier loaded
            memory_used_mb: Estimated memory usage
            rvc_model: Name of RVC model if loaded
        """
        with self._voice_lock:
            self._voice_state.tts_model_loaded = True
            self._voice_state.tts_tier = tier
            self._voice_state.estimated_voice_ram_mb = memory_used_mb
            self._voice_state.last_used = datetime.now()
            self._voice_state.use_count += 1

            if rvc_model:
                self._voice_state.rvc_model_loaded = True
                self._voice_state.rvc_model_name = rvc_model

    def notify_voice_used(self) -> None:
        """Called when voice synthesis is performed."""
        with self._voice_lock:
            self._voice_state.last_used = datetime.now()
            self._voice_state.use_count += 1

    def notify_voice_unloaded(self) -> None:
        """Called when voice models are unloaded."""
        with self._voice_lock:
            self._voice_state.tts_model_loaded = False
            self._voice_state.rvc_model_loaded = False
            self._voice_state.tts_tier = None
            self._voice_state.rvc_model_name = None
            self._voice_state.estimated_voice_ram_mb = 0.0

    def get_max_tokens_for_level(self, level: ResourceLevel = None) -> int:
        """Get maximum tokens allowed for current resource level."""
        if level is None:
            level = self.get_resource_level()

        return {
            ResourceLevel.CRITICAL: self.config.max_tokens_critical,
            ResourceLevel.LOW: self.config.max_tokens_low,
            ResourceLevel.MODERATE: self.config.max_tokens_moderate,
            ResourceLevel.GOOD: self.config.max_tokens_good,
        }[level]

    def can_perform_heavy_operation(self) -> tuple[bool, str]:
        """
        Check if a heavy operation (model load/generation) can be performed.

        Returns: (can_perform, reason)
        """
        level = self.get_resource_level()

        # Critical memory - refuse
        if level == ResourceLevel.CRITICAL:
            return False, f"Memory critically low ({self.get_memory_info()[0]:.1f}GB available)"

        # Check cooldown
        if self._last_heavy_op_end:
            elapsed = (datetime.now() - self._last_heavy_op_end).total_seconds()
            if elapsed < self.config.cooldown_after_heavy_op_seconds:
                remaining = self.config.cooldown_after_heavy_op_seconds - elapsed
                return False, f"Cooldown active ({remaining:.1f}s remaining)"

        # Check concurrent ops
        if self._active_heavy_ops >= self.config.max_concurrent_heavy_ops:
            return False, f"Max concurrent operations reached ({self._active_heavy_ops}/{self.config.max_concurrent_heavy_ops})"

        return True, "Resources available"

    def heavy_operation_context(self):
        """Context manager for heavy operations."""
        return HeavyOperationContext(self)

    def execute_with_limits(
        self,
        func: Callable[..., T],
        *args,
        timeout: float = None,
        **kwargs
    ) -> OperationResult:
        """
        Execute a function with resource limits.

        Will wait for resources if needed, up to timeout.
        """
        if timeout is None:
            timeout = self.config.request_timeout_seconds

        self._stats['total_requests'] += 1
        start_time = time.time()
        start_level = self.get_resource_level()

        # Wait for resources
        while True:
            can_perform, reason = self.can_perform_heavy_operation()

            if can_perform:
                break

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self._stats['timeouts'] += 1
                return OperationResult(
                    success=False,
                    error=f"Timeout waiting for resources: {reason}",
                    waited_seconds=elapsed,
                    resource_level_at_start=start_level
                )

            # Wait a bit before retrying
            time.sleep(0.5)
            self._stats['queued_requests'] += 1

        # Execute with resource tracking
        waited = time.time() - start_time

        try:
            with self.heavy_operation_context():
                result = func(*args, **kwargs)

            self._stats['completed_requests'] += 1
            return OperationResult(
                success=True,
                result=result,
                waited_seconds=waited,
                resource_level_at_start=start_level
            )

        except Exception as e:
            return OperationResult(
                success=False,
                error=str(e),
                waited_seconds=waited,
                resource_level_at_start=start_level
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get resource manager statistics."""
        snapshot = self.get_snapshot()
        return {
            **self._stats,
            'current_snapshot': snapshot.to_dict(),
            'config': {
                'max_concurrent_heavy_ops': self.config.max_concurrent_heavy_ops,
                'request_timeout_seconds': self.config.request_timeout_seconds,
                'memory_thresholds_gb': {
                    'critical': self.config.memory_critical_gb,
                    'low': self.config.memory_low_gb,
                    'moderate': self.config.memory_moderate_gb,
                }
            },
            'vision': self.get_vision_status(),
            'voice': self.get_voice_status()
        }

    def update_config(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Update semaphore if max_concurrent changed
        if 'max_concurrent_heavy_ops' in kwargs:
            self._heavy_op_semaphore = threading.Semaphore(
                self.config.max_concurrent_heavy_ops
            )

        # Save updated config
        self.config.save_to_file()


class HeavyOperationContext:
    """Context manager for tracking heavy operations."""

    def __init__(self, manager: ResourceManager):
        self.manager = manager
        self.acquired = False

    def __enter__(self):
        self.manager._heavy_op_semaphore.acquire()
        with self.manager._ops_lock:
            self.manager._active_heavy_ops += 1
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            with self.manager._ops_lock:
                self.manager._active_heavy_ops -= 1
            self.manager._last_heavy_op_end = datetime.now()
            self.manager._heavy_op_semaphore.release()
        return False


# Convenience function for quick checks
def check_resources() -> Dict[str, Any]:
    """Quick check of current resources."""
    manager = ResourceManager()
    return manager.get_snapshot().to_dict()


def get_safe_max_tokens() -> int:
    """Get safe max tokens for current resource level."""
    manager = ResourceManager()
    return manager.get_max_tokens_for_level()


def get_vision_status() -> Dict[str, Any]:
    """Quick check of current vision model status."""
    manager = ResourceManager()
    return manager.get_vision_status()


def can_load_vision(tier: str = "local_vlm") -> bool:
    """
    Check if a vision model can be loaded.

    Args:
        tier: One of "zero_cost", "lightweight", "local_vlm", "claude"

    Returns:
        True if the tier can be loaded
    """
    manager = ResourceManager()
    tier_enum = VisionTier(tier)
    return manager.can_load_vision_model(tier_enum)


def force_unload_vision() -> bool:
    """Force unload any loaded vision model."""
    manager = ResourceManager()
    return manager.force_vision_unload()


# Voice resource convenience functions (Task 6.2.3)
def get_voice_status() -> Dict[str, Any]:
    """Quick check of current voice resource status."""
    manager = ResourceManager()
    return manager.get_voice_status()


def can_use_quality_voice() -> bool:
    """Check if high-quality voice (F5-TTS + RVC) can be used."""
    manager = ResourceManager()
    return manager.can_use_quality_voice()


def should_use_voice_fallback() -> bool:
    """Check if fallback voice (macOS say) should be used."""
    manager = ResourceManager()
    return manager.should_use_voice_fallback()


def get_recommended_voice_tier() -> str:
    """
    Get recommended voice tier based on current resources.

    Returns:
        Tier name: "macos_say", "edge_tts", "coqui", "f5_tts"
    """
    manager = ResourceManager()
    return manager.get_recommended_voice_tier().value


def can_train() -> tuple[bool, str]:
    """Check if system has enough resources for MLX LoRA training."""
    manager = ResourceManager()
    return manager.can_train()
