#!/usr/bin/env python3
"""
SAM Scraper Launcher

Starts everything in the background - no terminal windows needed.
Just double-click this file or run: python start_scrapers.py

Opens:
- Dashboard at http://localhost:8088
- Daemon running in background
- Auto-opens browser

To stop: python start_scrapers.py stop
"""

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

SCRAPER_DIR = Path(__file__).parent
PID_FILE = Path.home() / ".sam" / "scraper_pids.txt"
DASHBOARD_PORT = 8088
DAEMON_PORT = 8089


def get_pids():
    """Get running PIDs."""
    if not PID_FILE.exists():
        return {}
    try:
        pids = {}
        for line in PID_FILE.read_text().strip().split("\n"):
            if "=" in line:
                name, pid = line.split("=")
                pids[name] = int(pid)
        return pids
    except:
        return {}


def save_pids(pids):
    """Save PIDs to file."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text("\n".join(f"{k}={v}" for k, v in pids.items()))


def is_running(pid):
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start():
    """Start dashboard and daemon in background."""
    pids = get_pids()

    # Find venv python
    venv_python = SCRAPER_DIR / "scraper_system" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = sys.executable  # Fallback to system python

    # Check if already running
    if pids.get("dashboard") and is_running(pids["dashboard"]):
        print(f"Dashboard already running (PID {pids['dashboard']})")
    else:
        print("Starting dashboard...")
        proc = subprocess.Popen(
            [str(venv_python), "-m", "scraper_system.dashboard", str(DASHBOARD_PORT)],
            cwd=str(SCRAPER_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pids["dashboard"] = proc.pid
        print(f"  Dashboard started (PID {proc.pid})")

    if pids.get("daemon") and is_running(pids["daemon"]):
        print(f"Daemon already running (PID {pids['daemon']})")
    else:
        print("Starting daemon...")
        proc = subprocess.Popen(
            [str(venv_python), "-m", "scraper_system.daemon", "--port", str(DAEMON_PORT)],
            cwd=str(SCRAPER_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pids["daemon"] = proc.pid
        print(f"  Daemon started (PID {proc.pid})")

    save_pids(pids)

    # Wait for services to start
    time.sleep(2)

    # Open browser
    url = f"http://localhost:{DASHBOARD_PORT}"
    print(f"\nOpening {url}")
    webbrowser.open(url)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  SAM Scrapers Running                                     ║
╠══════════════════════════════════════════════════════════╣
║  Dashboard: http://localhost:{DASHBOARD_PORT:<5}                       ║
║  Daemon:    http://localhost:{DAEMON_PORT:<5}/status                   ║
╠══════════════════════════════════════════════════════════╣
║  To stop:   python start_scrapers.py stop                 ║
║  To add all scrapers: Click "Add All Scrapers to Queue"   ║
╚══════════════════════════════════════════════════════════╝
""")


def stop():
    """Stop all running services."""
    pids = get_pids()

    for name, pid in pids.items():
        if is_running(pid):
            print(f"Stopping {name} (PID {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                if is_running(pid):
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    PID_FILE.unlink(missing_ok=True)
    print("All services stopped.")


def status():
    """Show status of services."""
    pids = get_pids()

    print("\nSAM Scraper Status")
    print("=" * 40)

    for name in ["dashboard", "daemon"]:
        pid = pids.get(name)
        if pid and is_running(pid):
            print(f"  {name}: Running (PID {pid})")
        else:
            print(f"  {name}: Not running")

    # Try to get daemon status
    try:
        import urllib.request
        import json
        with urllib.request.urlopen(f"http://localhost:{DAEMON_PORT}/status", timeout=2) as resp:
            data = json.loads(resp.read())
            print(f"\nDaemon Status:")
            print(f"  Active: {data.get('active_count', 0)} scrapers")
            print(f"  Queue: {data.get('queue_length', 0)} pending")
            print(f"  Today: {data.get('today', {}).get('items', 0)} items")
    except:
        pass

    print()


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "stop":
            stop()
        elif cmd == "status":
            status()
        elif cmd == "restart":
            stop()
            time.sleep(2)
            start()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python start_scrapers.py [start|stop|status|restart]")
    else:
        start()


if __name__ == "__main__":
    main()
