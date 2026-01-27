#!/usr/bin/env python3
"""
SAM Unified Daemon - Continuous Operation Manager

Manages ALL SAM services with priority-based resource management:
1. SAM Brain (MLX inference) - Priority 1
2. Scrapers (data collection) - Priority 2
3. Training Pipeline - Priority 3
4. External Services (Plex, Backblaze, etc.) - Monitored

Resource Management:
- Monitors RAM usage
- Pauses low-priority tasks when RAM is tight
- Resumes when resources available
- Respects external services (Plex streaming, etc.)

Usage:
    python unified_daemon.py start      # Start daemon
    python unified_daemon.py stop       # Stop daemon
    python unified_daemon.py status     # Show status
    python unified_daemon.py logs       # Show recent logs
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import deque


class ServicePriority(Enum):
    """Service priorities (lower = higher priority)"""
    CRITICAL = 1    # SAM Brain, MLX
    HIGH = 2        # Scrapers
    MEDIUM = 3      # Training
    LOW = 4         # Background tasks
    EXTERNAL = 5    # Monitored only (Plex, Backblaze)


@dataclass
class Service:
    """A managed service"""
    name: str
    priority: ServicePriority
    start_cmd: str
    stop_cmd: Optional[str] = None
    pid_file: Optional[str] = None
    health_check: Optional[str] = None
    min_ram_gb: float = 0.5
    status: str = "stopped"
    pid: Optional[int] = None
    last_health: Optional[str] = None
    auto_restart: bool = True
    external: bool = False  # If True, don't manage, just monitor


@dataclass
class ResourceStatus:
    """Current resource status"""
    total_ram_gb: float
    available_ram_gb: float
    cpu_percent: float
    active_services: List[str]
    paused_services: List[str]
    external_services: Dict[str, bool]  # name -> is_running


class UnifiedDaemon:
    """
    Manages all SAM services with resource-aware scheduling.

    Priority order (when RAM is tight):
    1. SAM Brain (MLX) - Never pause
    2. Scrapers - Pause if RAM < 1.5GB
    3. Training - Pause if RAM < 2GB
    4. Background - Pause if RAM < 2.5GB
    """

    STATE_DIR = Path.home() / ".sam" / "daemon"
    PID_FILE = STATE_DIR / "unified_daemon.pid"
    STATE_FILE = STATE_DIR / "state.json"
    LOG_FILE = STATE_DIR / "daemon.log"

    # RAM thresholds (GB)
    RAM_CRITICAL = 1.0   # Below this, pause everything except SAM Brain
    RAM_LOW = 1.5        # Pause training
    RAM_MEDIUM = 2.0     # Pause background tasks
    RAM_OK = 2.5         # All systems go

    # Check intervals (seconds)
    RESOURCE_CHECK_INTERVAL = 30
    HEALTH_CHECK_INTERVAL = 60
    SCRAPER_SCHEDULE_INTERVAL = 300  # 5 minutes

    def __init__(self):
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.services: Dict[str, Service] = {}
        self.logs = deque(maxlen=1000)
        self.paused_by_resource: List[str] = []

        self._init_services()
        self._load_state()

    def _init_services(self):
        """Initialize service definitions."""
        base_dir = Path(__file__).parent.parent
        scraper_dir = Path.home() / "ReverseLab" / "SAM" / "scrapers"

        self.services = {
            # SAM Brain - CRITICAL
            "sam_brain": Service(
                name="SAM Brain",
                priority=ServicePriority.CRITICAL,
                start_cmd=f"cd {base_dir}/sam_brain && python3 -c 'from cognitive.unified_orchestrator import CognitiveOrchestrator; import time; o=CognitiveOrchestrator(); [time.sleep(60) for _ in iter(int, 1)]'",
                pid_file=str(base_dir / "sam_brain" / ".sam_daemon.pid"),
                health_check="curl -s http://localhost:8765/api/status",
                min_ram_gb=0.8,
            ),

            # Multi-Role Orchestrator - CRITICAL
            "orchestrator": Service(
                name="Orchestrator",
                priority=ServicePriority.CRITICAL,
                start_cmd=f"cd {base_dir}/sam_brain && python3 multi_role_orchestrator.py server",
                pid_file=str(self.STATE_DIR / "orchestrator.pid"),
                min_ram_gb=0.2,
            ),

            # Scrapers - HIGH
            "scrapers": Service(
                name="Scrapers",
                priority=ServicePriority.HIGH,
                start_cmd=f"cd {scraper_dir} && python3 -m scraper_system.daemon --port 8089",
                pid_file=str(Path.home() / ".sam_scraper_daemon.pid"),
                health_check=f"curl -s http://localhost:8089/status",
                min_ram_gb=0.5,
            ),

            # Training Pipeline - MEDIUM
            "training": Service(
                name="Training Pipeline",
                priority=ServicePriority.MEDIUM,
                start_cmd=f"cd {scraper_dir} && python3 -m scraper_system.training.continuous_pipeline",
                pid_file=str(Path.home() / ".sam_training_daemon.pid"),
                min_ram_gb=1.0,
            ),

            # Dashboard - LOW
            "dashboard": Service(
                name="Dashboard",
                priority=ServicePriority.LOW,
                start_cmd=f"cd {scraper_dir} && python3 -m scraper_system.dashboard 8088",
                pid_file=str(Path.home() / ".sam_dashboard.pid"),
                min_ram_gb=0.2,
            ),

            # External Services (monitored only)
            "plex": Service(
                name="Plex Media Server",
                priority=ServicePriority.EXTERNAL,
                start_cmd="",
                health_check="pgrep -f 'Plex Media Server'",
                external=True,
            ),
            "backblaze": Service(
                name="Backblaze",
                priority=ServicePriority.EXTERNAL,
                start_cmd="",
                health_check="pgrep -f 'bztransmit\\|bzfilelist'",
                external=True,
            ),
            "transmission": Service(
                name="Transmission",
                priority=ServicePriority.EXTERNAL,
                start_cmd="",
                health_check="pgrep -f 'transmission-daemon'",
                external=True,
            ),
        }

    def _load_state(self):
        """Load daemon state from disk."""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE) as f:
                    data = json.load(f)
                    self.paused_by_resource = data.get("paused_by_resource", [])
                    # Also restore service states
                    if "services" in data:
                        for name, info in data["services"].items():
                            if name in self.services:
                                self.services[name].status = info.get("status", "stopped")
                                self.services[name].pid = info.get("pid")
                                self.services[name].last_health = info.get("last_health")
            except:
                pass
        # Verify processes are actually running
        self._verify_running_processes()

    def _verify_running_processes(self):
        """Verify that services marked as running are actually running."""
        for name, svc in self.services.items():
            if svc.status == "running" and svc.pid:
                try:
                    # Check if process exists
                    os.kill(svc.pid, 0)
                except OSError:
                    # Process not running
                    svc.status = "stopped"
                    svc.pid = None
            elif svc.status == "stopped" and not svc.external:
                # Check if process is running via pid file or pgrep
                if svc.pid_file and Path(svc.pid_file).exists():
                    try:
                        pid = int(Path(svc.pid_file).read_text().strip())
                        os.kill(pid, 0)
                        svc.status = "running"
                        svc.pid = pid
                    except (OSError, ValueError):
                        pass

    def _save_state(self):
        """Save daemon state to disk."""
        with open(self.STATE_FILE, "w") as f:
            json.dump({
                "paused_by_resource": self.paused_by_resource,
                "services": {
                    name: {
                        "status": svc.status,
                        "pid": svc.pid,
                        "last_health": svc.last_health,
                    }
                    for name, svc in self.services.items()
                },
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2)

    def log(self, msg: str, level: str = "INFO"):
        """Log a message and optionally send macOS notification."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {msg}"
        self.logs.append(entry)

        with open(self.LOG_FILE, "a") as f:
            f.write(entry + "\n")

        if level in ["ERROR", "WARN"]:
            print(entry, file=sys.stderr)
            # Send macOS notification for important events
            self._send_notification(msg, level)

    def _send_notification(self, message: str, level: str = "INFO"):
        """Send a macOS notification using osascript."""
        try:
            title = "SAM Daemon"
            subtitle = level
            # Truncate long messages
            message = message[:200] if len(message) > 200 else message

            # Use osascript for reliable notifications
            script = f'''
            display notification "{message}" with title "{title}" subtitle "{subtitle}"
            '''
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # Don't let notification failures affect daemon

    # =========================================================================
    # Resource Management
    # =========================================================================

    def get_resource_status(self) -> ResourceStatus:
        """Get current resource status."""
        mem = psutil.virtual_memory()

        active = [name for name, svc in self.services.items()
                  if svc.status == "running" and not svc.external]

        paused = [name for name, svc in self.services.items()
                  if svc.status == "paused"]

        external = {}
        for name, svc in self.services.items():
            if svc.external and svc.health_check:
                external[name] = self._check_external_service(svc)

        return ResourceStatus(
            total_ram_gb=mem.total / (1024**3),
            available_ram_gb=mem.available / (1024**3),
            cpu_percent=psutil.cpu_percent(interval=1),
            active_services=active,
            paused_services=paused,
            external_services=external,
        )

    def _check_external_service(self, svc: Service) -> bool:
        """Check if an external service is running."""
        try:
            result = subprocess.run(
                svc.health_check,
                shell=True,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def manage_resources(self):
        """Manage services based on available resources."""
        status = self.get_resource_status()
        available_gb = status.available_ram_gb

        # Check if Plex is actively streaming (higher RAM usage expected)
        plex_active = status.external_services.get("plex", False)

        # Adjust thresholds if Plex is active
        threshold_adjustment = 0.5 if plex_active else 0

        self.log(f"RAM: {available_gb:.1f}GB free, Plex: {'active' if plex_active else 'idle'}")

        # Critical: Pause everything except SAM Brain
        if available_gb < self.RAM_CRITICAL + threshold_adjustment:
            self.log("CRITICAL: Low RAM, pausing non-critical services", "WARN")
            for name, svc in self.services.items():
                if svc.priority.value > ServicePriority.CRITICAL.value and svc.status == "running":
                    self._pause_service(name)

        # Low: Pause training
        elif available_gb < self.RAM_LOW + threshold_adjustment:
            self.log("Low RAM, pausing training", "WARN")
            if self.services["training"].status == "running":
                self._pause_service("training")

        # Medium: Pause background
        elif available_gb < self.RAM_MEDIUM + threshold_adjustment:
            if self.services["dashboard"].status == "running":
                self._pause_service("dashboard")

        # OK: Resume paused services
        elif available_gb > self.RAM_OK:
            for name in self.paused_by_resource.copy():
                if name in self.services:
                    self._resume_service(name)

    def _pause_service(self, name: str):
        """Pause a service to free resources."""
        svc = self.services.get(name)
        if not svc or svc.status != "running":
            return

        self.log(f"Pausing {svc.name} to free resources")

        if svc.pid:
            try:
                os.kill(svc.pid, signal.SIGSTOP)
                svc.status = "paused"
                if name not in self.paused_by_resource:
                    self.paused_by_resource.append(name)
                self._save_state()
            except:
                pass

    def _resume_service(self, name: str):
        """Resume a paused service."""
        svc = self.services.get(name)
        if not svc or svc.status != "paused":
            return

        self.log(f"Resuming {svc.name}")

        if svc.pid:
            try:
                os.kill(svc.pid, signal.SIGCONT)
                svc.status = "running"
                if name in self.paused_by_resource:
                    self.paused_by_resource.remove(name)
                self._save_state()
            except:
                pass

    # =========================================================================
    # Service Management
    # =========================================================================

    def start_service(self, name: str) -> bool:
        """Start a service."""
        svc = self.services.get(name)
        if not svc or svc.external:
            return False

        if svc.status == "running":
            self.log(f"{svc.name} already running")
            return True

        # Kill any orphan processes first
        self._kill_orphans(name)

        # Check RAM
        status = self.get_resource_status()
        if status.available_ram_gb < svc.min_ram_gb:
            self.log(f"Not enough RAM to start {svc.name}", "WARN")
            return False

        self.log(f"Starting {svc.name}...")

        try:
            # Use process group for proper cleanup
            proc = subprocess.Popen(
                svc.start_cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Creates new process group
                preexec_fn=os.setpgrp,   # Set process group leader
            )

            # Wait briefly and find the actual Python process PID
            time.sleep(1)
            actual_pid = self._find_service_pid(name, proc.pid)

            svc.pid = actual_pid or proc.pid
            svc.status = "running"

            if svc.pid_file:
                Path(svc.pid_file).write_text(str(svc.pid))

            self._save_state()
            self.log(f"{svc.name} started (PID {svc.pid})")
            return True

        except Exception as e:
            self.log(f"Failed to start {svc.name}: {e}", "ERROR")
            return False

    def _find_service_pid(self, name: str, parent_pid: int) -> Optional[int]:
        """Find the actual service PID (child of shell)."""
        try:
            parent = psutil.Process(parent_pid)
            children = parent.children(recursive=True)
            # Look for python process
            for child in children:
                if 'python' in child.name().lower():
                    return child.pid
            # Return first child if no python found
            if children:
                return children[0].pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return None

    def _kill_orphans(self, name: str):
        """Kill orphan processes for a service."""
        patterns = {
            "scrapers": ["scraper_system.daemon", "scraper_system"],
            "training": ["continuous_pipeline", "training"],
            "dashboard": ["scraper_system.dashboard"],
            "orchestrator": ["multi_role_orchestrator"],
            "sam_brain": ["cognitive"],
        }

        if name not in patterns:
            return

        for pattern in patterns[name]:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if pattern in cmdline and proc.pid != os.getpid():
                            self.log(f"Killing orphan {name} process (PID {proc.pid})")
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception as e:
                self.log(f"Error killing orphans: {e}", "WARN")

    def stop_service(self, name: str) -> bool:
        """Stop a service and all its child processes."""
        svc = self.services.get(name)
        if not svc or svc.external:
            return False

        if svc.status == "stopped":
            return True

        self.log(f"Stopping {svc.name}...")

        pid = svc.pid
        if not pid and svc.pid_file and Path(svc.pid_file).exists():
            try:
                pid = int(Path(svc.pid_file).read_text().strip())
            except (ValueError, FileNotFoundError):
                pass

        if pid:
            try:
                # Kill process and all children
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)

                    # Terminate children first
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass

                    # Terminate parent
                    parent.terminate()

                    # Wait for graceful shutdown
                    gone, alive = psutil.wait_procs([parent] + children, timeout=3)

                    # Force kill survivors
                    for p in alive:
                        try:
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass

                except psutil.NoSuchProcess:
                    pass

                # Also kill any orphans with matching pattern
                self._kill_orphans(name)

                svc.status = "stopped"
                svc.pid = None

                # Clean up PID file
                if svc.pid_file and Path(svc.pid_file).exists():
                    Path(svc.pid_file).unlink(missing_ok=True)

                self._save_state()
                self.log(f"{svc.name} stopped")
                return True

            except Exception as e:
                self.log(f"Failed to stop {svc.name}: {e}", "ERROR")

        # Even if no PID, try to kill orphans
        self._kill_orphans(name)
        svc.status = "stopped"
        svc.pid = None
        self._save_state()
        return True

    def health_check(self, name: str) -> bool:
        """Check if a service is healthy."""
        svc = self.services.get(name)
        if not svc:
            return False

        # Check PID
        if svc.pid:
            try:
                os.kill(svc.pid, 0)
            except ProcessLookupError:
                svc.status = "stopped"
                svc.pid = None
                return False

        # Check health endpoint
        if svc.health_check:
            try:
                result = subprocess.run(
                    svc.health_check,
                    shell=True,
                    capture_output=True,
                    timeout=10
                )
                healthy = result.returncode == 0
                svc.last_health = datetime.now().isoformat()
                return healthy
            except:
                return False

        return svc.status == "running"

    # =========================================================================
    # Daemon Control
    # =========================================================================

    def start_daemon(self):
        """Start the unified daemon."""
        if self.PID_FILE.exists():
            pid = int(self.PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                print(f"Daemon already running (PID {pid})")
                return
            except ProcessLookupError:
                pass

        # Fork to background
        if os.fork() > 0:
            sys.exit(0)

        os.setsid()

        if os.fork() > 0:
            sys.exit(0)

        self.PID_FILE.write_text(str(os.getpid()))
        self.running = True

        self.log("Unified daemon starting...")
        self._run()

    def stop_daemon(self):
        """Stop the daemon."""
        if not self.PID_FILE.exists():
            print("Daemon not running")
            return

        pid = int(self.PID_FILE.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to daemon (PID {pid})")
        except ProcessLookupError:
            print("Daemon not running")

        self.PID_FILE.unlink(missing_ok=True)

    def _run(self):
        """Main daemon loop."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Start critical services
        for name, svc in self.services.items():
            if svc.priority == ServicePriority.CRITICAL and not svc.external:
                self.start_service(name)
                time.sleep(2)

        # Start high priority services
        for name, svc in self.services.items():
            if svc.priority == ServicePriority.HIGH and not svc.external:
                self.start_service(name)
                time.sleep(2)

        last_resource_check = datetime.now()
        last_health_check = datetime.now()

        while self.running:
            try:
                now = datetime.now()

                # Resource check
                if (now - last_resource_check).seconds >= self.RESOURCE_CHECK_INTERVAL:
                    self.manage_resources()
                    last_resource_check = now

                # Health check
                if (now - last_health_check).seconds >= self.HEALTH_CHECK_INTERVAL:
                    for name, svc in self.services.items():
                        if svc.status == "running" and svc.auto_restart:
                            if not self.health_check(name):
                                self.log(f"{svc.name} unhealthy, restarting", "WARN")
                                self.stop_service(name)
                                time.sleep(2)
                                self.start_service(name)
                    last_health_check = now

                time.sleep(5)

            except Exception as e:
                self.log(f"Daemon error: {e}", "ERROR")
                time.sleep(30)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.log("Shutdown signal received")
        self.running = False

        # Stop services in reverse priority order
        for name, svc in sorted(
            self.services.items(),
            key=lambda x: x[1].priority.value,
            reverse=True
        ):
            if not svc.external:
                self.stop_service(name)

        self.PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    def get_status(self) -> Dict:
        """Get daemon status."""
        resource = self.get_resource_status()

        return {
            "daemon": {
                "running": self.PID_FILE.exists(),
                "pid": int(self.PID_FILE.read_text().strip()) if self.PID_FILE.exists() else None,
            },
            "resources": {
                "ram_total_gb": round(resource.total_ram_gb, 1),
                "ram_available_gb": round(resource.available_ram_gb, 1),
                "cpu_percent": round(resource.cpu_percent, 1),
            },
            "services": {
                name: {
                    "status": svc.status,
                    "priority": svc.priority.name,
                    "pid": svc.pid,
                }
                for name, svc in self.services.items()
                if not svc.external
            },
            "external": resource.external_services,
            "paused_by_resource": self.paused_by_resource,
        }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    daemon = UnifiedDaemon()

    if len(sys.argv) < 2:
        print("SAM Unified Daemon")
        print("")
        print("Usage:")
        print("  python unified_daemon.py start    # Start daemon")
        print("  python unified_daemon.py stop     # Stop daemon")
        print("  python unified_daemon.py status   # Show status")
        print("  python unified_daemon.py logs     # Show recent logs")
        print("  python unified_daemon.py restart  # Restart daemon")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "start":
        daemon.start_daemon()

    elif cmd == "stop":
        daemon.stop_daemon()

    elif cmd == "restart":
        daemon.stop_daemon()
        time.sleep(2)
        daemon.start_daemon()

    elif cmd == "status":
        status = daemon.get_status()
        print(json.dumps(status, indent=2))

    elif cmd == "logs":
        if daemon.LOG_FILE.exists():
            lines = daemon.LOG_FILE.read_text().strip().split("\n")
            for line in lines[-50:]:
                print(line)
        else:
            print("No logs yet")

    else:
        print(f"Unknown command: {cmd}")
