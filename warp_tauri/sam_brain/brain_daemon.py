#!/usr/bin/env python3
"""
SAM Brain Daemon - Background automation for SAM.

Runs as a background service to:
1. Keep Ollama models warm and responsive
2. Monitor for new drives and scan for projects
3. Consolidate semantic memory
4. Watch for changes in active projects
5. Pre-warm caches for fast responses

Usage:
  python brain_daemon.py start     # Start daemon
  python brain_daemon.py stop      # Stop daemon
  python brain_daemon.py status    # Check status
  python brain_daemon.py logs      # Show recent logs
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

SCRIPT_DIR = Path(__file__).parent
PID_FILE = Path.home() / ".sam_brain_daemon.pid"
LOG_FILE = Path.home() / ".sam_brain_daemon.log"
STATUS_FILE = SCRIPT_DIR / "daemon_status.json"

# Configuration
CONFIG = {
    "ollama_warm_interval": 300,     # Keep model warm every 5 minutes
    "project_scan_interval": 3600,   # Scan for new projects every hour
    "memory_consolidate_interval": 1800,  # Consolidate memory every 30 min
    "active_project_watch": 60,      # Check active projects every minute
}

class BrainDaemon:
    def __init__(self):
        self.running = False
        self.logs = deque(maxlen=1000)
        self.last_warm = None
        self.last_scan = None
        self.last_consolidate = None

    def log(self, msg: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {msg}"
        self.logs.append(entry)

        # Write to log file
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")

        if level == "ERROR":
            print(entry, file=sys.stderr)

    def update_status(self, **kwargs):
        """Update daemon status file."""
        status = {
            "running": self.running,
            "pid": os.getpid(),
            "last_warm": self.last_warm.isoformat() if self.last_warm else None,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "last_consolidate": self.last_consolidate.isoformat() if self.last_consolidate else None,
            "uptime_hours": 0,
            **kwargs
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)

    def warm_ollama(self):
        """Keep Ollama model warm with a simple query."""
        try:
            result = subprocess.run(
                ["ollama", "run", "sam-coder", "# ready"],
                capture_output=True,
                text=True,
                timeout=30
            )
            self.last_warm = datetime.now()
            self.log("Ollama model warmed successfully")
            return True
        except subprocess.TimeoutExpired:
            self.log("Ollama warm timeout", "WARN")
            return False
        except Exception as e:
            self.log(f"Ollama warm failed: {e}", "ERROR")
            return False

    def check_ollama_health(self):
        """Check if Ollama is running and healthy."""
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def restart_ollama(self):
        """Restart Ollama if it's down."""
        self.log("Attempting to restart Ollama...")
        try:
            subprocess.run(["pkill", "-9", "ollama"], timeout=5)
            time.sleep(2)
            subprocess.Popen(
                ["nohup", "ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(5)
            if self.check_ollama_health():
                self.log("Ollama restarted successfully")
                return True
            else:
                self.log("Ollama restart failed", "ERROR")
                return False
        except Exception as e:
            self.log(f"Failed to restart Ollama: {e}", "ERROR")
            return False

    def scan_for_new_projects(self):
        """Scan for newly mounted drives."""
        try:
            result = subprocess.run(
                ["python3", str(SCRIPT_DIR / "exhaustive_analyzer.py")],
                capture_output=True,
                text=True,
                timeout=600
            )
            self.last_scan = datetime.now()
            self.log("Project scan completed")
            return True
        except subprocess.TimeoutExpired:
            self.log("Project scan timeout", "WARN")
            return False
        except Exception as e:
            self.log(f"Project scan failed: {e}", "ERROR")
            return False

    def consolidate_memory(self):
        """Consolidate semantic memory entries."""
        try:
            from semantic_memory import SemanticMemory
            mem = SemanticMemory()

            # Decay old memories
            mem.decay_memories(factor=0.99)

            # Save
            mem.save()

            self.last_consolidate = datetime.now()
            self.log("Memory consolidation completed")
            return True
        except Exception as e:
            self.log(f"Memory consolidation failed: {e}", "WARN")
            return False

    def run(self):
        """Main daemon loop."""
        self.running = True
        self.log("SAM Brain Daemon starting...")

        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Initial warm
        self.warm_ollama()
        self.update_status()

        start_time = datetime.now()

        while self.running:
            try:
                now = datetime.now()

                # NOTE: Ollama decommissioned 2026-01-18 - using MLX native inference
                # check_ollama_health() and restart_ollama() no longer called
                # MLX models load on-demand, no warming needed

                # Warm MLX model periodically (optional - loads on first use anyway)
                # if (not self.last_warm or
                #     (now - self.last_warm).total_seconds() > CONFIG["ollama_warm_interval"]):
                #     self.warm_mlx()

                # Consolidate memory
                if (not self.last_consolidate or
                    (now - self.last_consolidate).total_seconds() > CONFIG["memory_consolidate_interval"]):
                    self.consolidate_memory()

                # Update status
                uptime = (now - start_time).total_seconds() / 3600
                self.update_status(uptime_hours=round(uptime, 2))

                # Sleep before next iteration
                time.sleep(60)

            except Exception as e:
                self.log(f"Daemon loop error: {e}", "ERROR")
                time.sleep(10)

        self.log("SAM Brain Daemon stopped")
        self.update_status(running=False)

    def stop(self):
        """Stop the daemon."""
        self.running = False


def get_daemon_pid():
    """Get running daemon PID if any."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            return None
    return None


def cmd_start():
    """Start the daemon."""
    existing_pid = get_daemon_pid()
    if existing_pid:
        print(f"Daemon already running (PID {existing_pid})")
        return

    # Fork and run in background
    if os.fork() > 0:
        print("SAM Brain Daemon started in background")
        return

    # Child process
    os.setsid()
    daemon = BrainDaemon()

    def signal_handler(signum, frame):
        daemon.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    daemon.run()


def cmd_stop():
    """Stop the daemon."""
    pid = get_daemon_pid()
    if not pid:
        print("Daemon not running")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent stop signal to daemon (PID {pid})")
        time.sleep(2)
        PID_FILE.unlink(missing_ok=True)
    except OSError as e:
        print(f"Error stopping daemon: {e}")


def cmd_status():
    """Show daemon status."""
    pid = get_daemon_pid()

    if STATUS_FILE.exists():
        status = json.load(open(STATUS_FILE))
        print("SAM Brain Daemon Status:")
        print(f"  Running: {status.get('running', False)}")
        print(f"  PID: {pid or 'N/A'}")
        print(f"  Uptime: {status.get('uptime_hours', 0):.1f} hours")
        print(f"  Last Ollama warm: {status.get('last_warm', 'never')}")
        print(f"  Last memory consolidate: {status.get('last_consolidate', 'never')}")
    else:
        print("Daemon not running (no status file)")


def cmd_logs():
    """Show recent logs."""
    if LOG_FILE.exists():
        # Tail last 50 lines
        with open(LOG_FILE) as f:
            lines = f.readlines()[-50:]
            for line in lines:
                print(line.rstrip())
    else:
        print("No logs available")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "start":
        cmd_start()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "status":
        cmd_status()
    elif cmd == "logs":
        cmd_logs()
    elif cmd == "run":
        # Run in foreground (for debugging)
        daemon = BrainDaemon()
        daemon.run()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
