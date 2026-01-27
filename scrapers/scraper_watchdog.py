#!/usr/bin/env python3
"""
Scraper Watchdog - Kills stuck processes, restarts daemon.

Run via launchd every 5 minutes to ensure scrapers don't hang.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

DAEMON_DIR = Path("/Volumes/David External/scraper_daemon")
LOG_PATH = DAEMON_DIR / "daemon.log"
PID_PATH = DAEMON_DIR / "daemon.pid"
WATCHDOG_LOG = DAEMON_DIR / "watchdog.log"

# Max time a scraper can run before being killed
MAX_SCRAPER_RUNTIME = 1800  # 30 minutes max
MAX_DAEMON_SILENCE = 600    # 10 minutes without log = stuck


def log(msg: str):
    """Log to watchdog log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [WATCHDOG] {msg}"
    print(line)
    with open(WATCHDOG_LOG, 'a') as f:
        f.write(line + "\n")


def get_scraper_processes() -> list:
    """Get running scraper processes (not the daemon itself)."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        processes = []
        for line in result.stdout.split('\n'):
            if 'ripper.py' in line or 'collector.py' in line:
                if 'grep' not in line and 'watchdog' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = int(parts[1])
                        # Get process start time
                        processes.append({
                            'pid': pid,
                            'line': line
                        })
        return processes
    except Exception as e:
        log(f"Error getting processes: {e}")
        return []


def get_process_runtime(pid: int) -> float:
    """Get how long a process has been running (seconds)."""
    try:
        result = subprocess.run(
            ["ps", "-o", "etime=", "-p", str(pid)],
            capture_output=True,
            text=True
        )
        etime = result.stdout.strip()
        if not etime:
            return 0

        # Parse etime format: [[dd-]hh:]mm:ss
        parts = etime.replace('-', ':').split(':')
        parts = [int(p) for p in parts]

        if len(parts) == 2:  # mm:ss
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # hh:mm:ss
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 4:  # dd:hh:mm:ss
            return parts[0] * 86400 + parts[1] * 3600 + parts[2] * 60 + parts[3]
        return 0
    except Exception as e:
        return 0


def get_log_age() -> float:
    """Get seconds since last log entry."""
    try:
        if not LOG_PATH.exists():
            return 9999
        mtime = LOG_PATH.stat().st_mtime
        return time.time() - mtime
    except:
        return 9999


def kill_process(pid: int):
    """Kill a process."""
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        try:
            os.kill(pid, signal.SIGKILL)
        except:
            pass
        log(f"Killed PID {pid}")
    except Exception as e:
        log(f"Failed to kill PID {pid}: {e}")


def restart_daemon():
    """Restart the scraper daemon."""
    log("Restarting daemon...")

    # Kill existing daemon
    if PID_PATH.exists():
        try:
            pid = int(PID_PATH.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
        except:
            pass

    # Start new daemon
    subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "scraper_daemon.py"), "start", "--bg"],
        cwd=str(Path(__file__).parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    log("Daemon restarted")


def check_and_fix():
    """Main watchdog check."""
    log("Running watchdog check...")

    # Check for stuck scraper processes
    processes = get_scraper_processes()
    for proc in processes:
        runtime = get_process_runtime(proc['pid'])
        if runtime > MAX_SCRAPER_RUNTIME:
            log(f"Process stuck ({runtime:.0f}s): {proc['line'][:80]}")
            kill_process(proc['pid'])

    # Check if daemon log is stale (daemon might be stuck)
    log_age = get_log_age()
    if log_age > MAX_DAEMON_SILENCE:
        log(f"Daemon log stale ({log_age:.0f}s), restarting...")

        # Kill all scraper processes
        for proc in processes:
            kill_process(proc['pid'])

        restart_daemon()
    else:
        log(f"Daemon healthy (log age: {log_age:.0f}s)")


if __name__ == "__main__":
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    check_and_fix()
