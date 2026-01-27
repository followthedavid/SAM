"""
SAM Scraper System - Resource Governor

Prevents the 8GB Mac from choking by:
- Monitoring RAM usage
- Pausing scrapers when resources are low
- Pausing when VLM/Ollama is running
- Managing concurrent spider limits
"""

import psutil
import re
import time
import logging
from typing import List, Callable, Optional
from dataclasses import dataclass
from threading import Lock, Thread
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceState(Enum):
    """Current state of system resources."""
    AVAILABLE = "available"      # Good to run scrapers
    LOW_RAM = "low_ram"          # RAM below threshold
    VLM_RUNNING = "vlm_running"  # Heavy AI model running
    PAUSED = "paused"            # Manually paused


@dataclass
class ResourceStatus:
    """Current resource status."""
    state: ResourceState
    available_ram_gb: float
    total_ram_gb: float
    cpu_percent: float
    blocking_processes: List[str]
    can_start_scraper: bool
    reason: str


class ResourceGovernor:
    """
    Monitors system resources and controls scraper execution.

    Usage:
        governor = ResourceGovernor()
        governor.start_monitoring()

        # Check before starting a scraper
        if governor.can_start_scraper():
            run_scraper()

        # Register callbacks for state changes
        governor.on_resources_low(pause_all_scrapers)
        governor.on_resources_available(resume_scrapers)
    """

    def __init__(
        self,
        min_free_ram_gb: float = 1.0,
        check_interval_seconds: float = 30.0,
        blocking_process_patterns: List[str] = None,
    ):
        """
        Initialize the resource governor.

        Args:
            min_free_ram_gb: Minimum free RAM to allow scraping
            check_interval_seconds: How often to check resources
            blocking_process_patterns: Regex patterns for processes that should pause scraping
        """
        self.min_free_ram_bytes = int(min_free_ram_gb * 1024 * 1024 * 1024)
        self.check_interval = check_interval_seconds
        self.blocking_patterns = blocking_process_patterns or [
            r"mlx_vlm",
            r"ollama",
            r"python.*vlm",
            r"llama",
        ]

        self._state = ResourceState.AVAILABLE
        self._manually_paused = False
        self._monitoring = False
        self._monitor_thread: Optional[Thread] = None
        self._lock = Lock()

        # Callbacks
        self._on_low_callbacks: List[Callable] = []
        self._on_available_callbacks: List[Callable] = []
        self._on_state_change_callbacks: List[Callable[[ResourceState, ResourceState], None]] = []

    # =========================================================================
    # Resource Checking
    # =========================================================================

    def get_status(self) -> ResourceStatus:
        """Get current resource status."""
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        available_ram_gb = mem.available / (1024 ** 3)
        total_ram_gb = mem.total / (1024 ** 3)

        # Check for blocking processes
        blocking = self._find_blocking_processes()

        # Determine state
        if self._manually_paused:
            state = ResourceState.PAUSED
            reason = "Manually paused"
            can_start = False
        elif blocking:
            state = ResourceState.VLM_RUNNING
            reason = f"Blocked by: {', '.join(blocking)}"
            can_start = False
        elif mem.available < self.min_free_ram_bytes:
            state = ResourceState.LOW_RAM
            reason = f"RAM too low: {available_ram_gb:.1f}GB < {self.min_free_ram_bytes / (1024**3):.1f}GB"
            can_start = False
        else:
            state = ResourceState.AVAILABLE
            reason = "Resources available"
            can_start = True

        return ResourceStatus(
            state=state,
            available_ram_gb=available_ram_gb,
            total_ram_gb=total_ram_gb,
            cpu_percent=cpu,
            blocking_processes=blocking,
            can_start_scraper=can_start,
            reason=reason,
        )

    def can_start_scraper(self) -> bool:
        """Quick check if a scraper can be started."""
        return self.get_status().can_start_scraper

    def _find_blocking_processes(self) -> List[str]:
        """Find processes that should block scraping."""
        blocking = []

        # Exact process names that block scraping
        blocking_names = {"ollama", "mlx_vlm", "llama"}
        # Cmdline patterns for VLM servers (must be the main command, not just mentioned)
        cmdline_patterns = [r"python\s+.*\bvlm\b", r"python\s+-m\s+vlm"]

        for proc in psutil.process_iter(['name', 'cmdline', 'status', 'exe']):
            try:
                # Skip zombie/defunct processes
                status = proc.info.get('status', '')
                if status == psutil.STATUS_ZOMBIE:
                    continue

                name = (proc.info.get('name') or "").lower()
                exe = (proc.info.get('exe') or "").lower()

                # Check exact process name matches
                if name in blocking_names:
                    # Skip if this is just a grep/ps/killall command
                    cmdline = proc.info.get('cmdline') or []
                    cmdline_str = " ".join(cmdline).lower()
                    if any(skip in cmdline_str for skip in ["grep", "ps ", "pgrep", "killall"]):
                        continue
                    # Also skip if the process name is just mentioned in a shell command
                    if "/bin/zsh" in exe or "/bin/bash" in exe or "/bin/sh" in exe:
                        continue
                    blocking.append(name)
                    continue

                # Check executable path for ollama binary
                if "ollama" in exe and "bin/ollama" in exe:
                    blocking.append("ollama")
                    continue

                # Check cmdline patterns for VLM servers
                cmdline = proc.info.get('cmdline') or []
                if cmdline and len(cmdline) > 1:
                    cmdline_str = " ".join(cmdline)
                    for pattern in cmdline_patterns:
                        if re.search(pattern, cmdline_str, re.IGNORECASE):
                            blocking.append(name or "vlm")
                            break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return list(set(blocking))

    # =========================================================================
    # Monitoring
    # =========================================================================

    def start_monitoring(self) -> None:
        """Start background resource monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Resource monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Resource monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                status = self.get_status()
                new_state = status.state

                with self._lock:
                    old_state = self._state

                    if new_state != old_state:
                        self._state = new_state
                        logger.info(f"Resource state changed: {old_state.value} -> {new_state.value}")

                        # Fire callbacks
                        self._fire_state_change_callbacks(old_state, new_state)

                        if new_state == ResourceState.AVAILABLE and old_state != ResourceState.AVAILABLE:
                            self._fire_available_callbacks()
                        elif new_state != ResourceState.AVAILABLE and old_state == ResourceState.AVAILABLE:
                            self._fire_low_callbacks()

            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")

            time.sleep(self.check_interval)

    # =========================================================================
    # Manual Control
    # =========================================================================

    def pause(self) -> None:
        """Manually pause scraping."""
        with self._lock:
            self._manually_paused = True
            self._state = ResourceState.PAUSED
        logger.info("Scraping manually paused")

    def resume(self) -> None:
        """Resume from manual pause."""
        with self._lock:
            self._manually_paused = False
        logger.info("Scraping manually resumed")

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_resources_low(self, callback: Callable) -> None:
        """Register callback for when resources become low."""
        self._on_low_callbacks.append(callback)

    def on_resources_available(self, callback: Callable) -> None:
        """Register callback for when resources become available."""
        self._on_available_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[ResourceState, ResourceState], None]) -> None:
        """Register callback for any state change."""
        self._on_state_change_callbacks.append(callback)

    def _fire_low_callbacks(self) -> None:
        """Fire all low-resource callbacks."""
        for cb in self._on_low_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in low-resource callback: {e}")

    def _fire_available_callbacks(self) -> None:
        """Fire all available-resource callbacks."""
        for cb in self._on_available_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in available-resource callback: {e}")

    def _fire_state_change_callbacks(self, old: ResourceState, new: ResourceState) -> None:
        """Fire all state change callbacks."""
        for cb in self._on_state_change_callbacks:
            try:
                cb(old, new)
            except Exception as e:
                logger.error(f"Error in state-change callback: {e}")

    # =========================================================================
    # Wait Helpers
    # =========================================================================

    def wait_for_resources(self, timeout_seconds: float = None) -> bool:
        """
        Block until resources are available.

        Args:
            timeout_seconds: Maximum time to wait (None = forever)

        Returns:
            True if resources became available, False if timeout
        """
        start = time.time()

        while not self.can_start_scraper():
            if timeout_seconds and (time.time() - start) > timeout_seconds:
                return False

            status = self.get_status()
            logger.info(f"Waiting for resources: {status.reason}")
            time.sleep(self.check_interval)

        return True


# =============================================================================
# Singleton instance
# =============================================================================

_governor: Optional[ResourceGovernor] = None


def get_governor() -> ResourceGovernor:
    """Get the singleton resource governor instance."""
    global _governor

    if _governor is None:
        from ..config.settings import MIN_FREE_RAM_BYTES, PAUSE_WHEN_RUNNING

        _governor = ResourceGovernor(
            min_free_ram_gb=MIN_FREE_RAM_BYTES / (1024 ** 3),
            blocking_process_patterns=PAUSE_WHEN_RUNNING,
        )

    return _governor


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    governor = ResourceGovernor(min_free_ram_gb=2.0)
    status = governor.get_status()

    print(f"\n{'='*50}")
    print("SAM Resource Governor Status")
    print(f"{'='*50}")
    print(f"State: {status.state.value}")
    print(f"RAM: {status.available_ram_gb:.1f}GB / {status.total_ram_gb:.1f}GB available")
    print(f"CPU: {status.cpu_percent:.1f}%")
    print(f"Can start scraper: {status.can_start_scraper}")
    print(f"Reason: {status.reason}")

    if status.blocking_processes:
        print(f"Blocking processes: {', '.join(status.blocking_processes)}")

    print(f"{'='*50}\n")
