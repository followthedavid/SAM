#!/usr/bin/env python3
"""
Live Scraper Status - Real-time terminal dashboard.
Shows actual proof that things are happening.

Run: python3 live_status.py
"""

import os
import sys
import time
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

# ANSI colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"

# Paths
DAEMON_LOG = Path("/Volumes/David External/scraper_daemon/daemon.log")
DAEMON_PID = Path("/Volumes/David External/scraper_daemon/daemon.pid")
DAEMON_DB = Path("/Volumes/David External/scraper_daemon/daemon_state.db")

# All archives to check
ARCHIVES = {
    "nifty": ("/Volumes/David External/nifty_archive/nifty_index.db", "stories", "downloaded=1"),
    "ao3": ("/Volumes/David External/ao3_archive/ao3_index.db", "works", "downloaded=1"),
    "literotica": ("/Volumes/David External/literotica_archive/literotica_index.db", "stories", "downloaded=1"),
    "firstview": ("/Volumes/David External/firstview_archive/firstview_index.db", "photos", "downloaded=1"),
    "wwd": ("/Volumes/#1/wwd_archive/wwd_index.db", "articles", "downloaded=1"),
    "wmag": ("/Volumes/#1/wmag_archive/wmag_index.db", "articles", "downloaded=1"),
    "vmag": ("/Volumes/#1/vmag_archive/vmag_index.db", "articles", "downloaded=1"),
    "apple_dev": ("/Volumes/David External/apple_dev_archive/apple_dev.db", "docs", None),
    "code": ("/Volumes/David External/coding_training/code_collection.db", "code_examples", None),
}


def clear_screen():
    os.system('clear')


def get_daemon_pid():
    """Get daemon PID if running."""
    if not DAEMON_PID.exists():
        return None
    try:
        pid = int(DAEMON_PID.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        return None


def get_current_scraper():
    """Get currently running scraper from daemon log."""
    if not DAEMON_LOG.exists():
        return None, None

    try:
        # Read last 50 lines
        result = subprocess.run(
            ["tail", "-50", str(DAEMON_LOG)],
            capture_output=True, text=True, timeout=2
        )
        lines = result.stdout.strip().split('\n')

        current = None
        last_activity = None

        for line in reversed(lines):
            if "Starting " in line and "..." in line:
                # Extract scraper name: "Starting apple_github..."
                parts = line.split("Starting ")
                if len(parts) > 1:
                    current = parts[1].split("...")[0].strip()
                    # Extract timestamp
                    if line[:19].replace("-", "").replace(":", "").replace(" ", "").replace(",", "").isdigit() or "202" in line[:25]:
                        last_activity = line[:23]
                    break
            elif "[INFO]" in line and ("Downloaded" in line or "Collected" in line or "Processing" in line):
                last_activity = line[:23]

        return current, last_activity
    except:
        return None, None


def get_recent_log_lines(n=8):
    """Get last N meaningful log lines."""
    if not DAEMON_LOG.exists():
        return []

    try:
        result = subprocess.run(
            ["tail", "-100", str(DAEMON_LOG)],
            capture_output=True, text=True, timeout=2
        )
        lines = result.stdout.strip().split('\n')

        # Filter to meaningful lines
        meaningful = []
        for line in lines:
            if any(x in line for x in ["Downloaded", "Collected", "Processing", "Starting", "Finished", "items", "ERROR", "success"]):
                # Trim to fit terminal
                if len(line) > 100:
                    line = line[:97] + "..."
                meaningful.append(line)

        return meaningful[-n:]
    except:
        return []


def get_archive_stats():
    """Get download counts from all archives."""
    stats = {}
    for name, (db_path, table, where) in ARCHIVES.items():
        if not Path(db_path).exists():
            stats[name] = {"total": 0, "downloaded": 0, "exists": False}
            continue

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Total count
            c.execute(f"SELECT COUNT(*) FROM {table}")
            total = c.fetchone()[0]

            # Downloaded count
            if where:
                c.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}")
                downloaded = c.fetchone()[0]
            else:
                downloaded = total

            conn.close()
            stats[name] = {"total": total, "downloaded": downloaded, "exists": True}
        except Exception as e:
            stats[name] = {"total": 0, "downloaded": 0, "exists": False, "error": str(e)}

    return stats


def get_items_last_hour():
    """Get items downloaded in the last hour from daemon DB."""
    if not DAEMON_DB.exists():
        return 0

    try:
        conn = sqlite3.connect(str(DAEMON_DB))
        c = conn.cursor()

        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        c.execute("""
            SELECT SUM(items_processed) FROM runs
            WHERE finished_at > ? AND status = 'success'
        """, (hour_ago,))

        result = c.fetchone()[0]
        conn.close()
        return result or 0
    except:
        return 0


def format_number(n):
    """Format number with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def render_progress_bar(current, total, width=20):
    """Render a progress bar."""
    if total == 0:
        return f"[{'░' * width}]"

    pct = min(current / total, 1.0)
    filled = int(pct * width)
    empty = width - filled

    return f"[{'█' * filled}{'░' * empty}]"


def render_dashboard():
    """Render the full dashboard."""
    clear_screen()

    # Header
    now = datetime.now().strftime("%H:%M:%S")
    pid = get_daemon_pid()

    if pid:
        status = f"{C.GREEN}● RUNNING{C.RESET} (PID {pid})"
    else:
        status = f"{C.RED}● STOPPED{C.RESET}"

    print(f"{C.BOLD}╔══════════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}║  SAM SCRAPER LIVE STATUS                      {now}  ║{C.RESET}")
    print(f"{C.BOLD}╚══════════════════════════════════════════════════════════════╝{C.RESET}")
    print(f"  Daemon: {status}")
    print()

    # Current Activity
    current_scraper, last_activity = get_current_scraper()
    items_hour = get_items_last_hour()

    print(f"{C.CYAN}┌─ CURRENT ACTIVITY ─────────────────────────────────────────────┐{C.RESET}")
    if current_scraper:
        print(f"{C.CYAN}│{C.RESET} {C.GREEN}▶{C.RESET} Running: {C.BOLD}{current_scraper}{C.RESET}")
    else:
        print(f"{C.CYAN}│{C.RESET} {C.DIM}Idle - waiting for next scraper{C.RESET}")

    print(f"{C.CYAN}│{C.RESET} Items this hour: {C.YELLOW}{items_hour}{C.RESET}")
    if last_activity:
        print(f"{C.CYAN}│{C.RESET} Last activity: {C.DIM}{last_activity}{C.RESET}")
    print(f"{C.CYAN}└────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()

    # Archive Stats
    print(f"{C.BLUE}┌─ ARCHIVES ─────────────────────────────────────────────────────┐{C.RESET}")
    stats = get_archive_stats()

    total_items = 0
    total_downloaded = 0

    for name, data in sorted(stats.items(), key=lambda x: -x[1].get("downloaded", 0)):
        if not data["exists"]:
            continue

        total_items += data["total"]
        total_downloaded += data["downloaded"]

        pct = (data["downloaded"] / data["total"] * 100) if data["total"] > 0 else 0
        bar = render_progress_bar(data["downloaded"], data["total"], 15)

        # Color based on progress
        if pct >= 90:
            color = C.GREEN
        elif pct >= 50:
            color = C.YELLOW
        else:
            color = C.DIM

        dl_str = format_number(data["downloaded"])
        tot_str = format_number(data["total"])

        print(f"{C.BLUE}│{C.RESET} {name:12} {color}{bar}{C.RESET} {dl_str:>6}/{tot_str:<6} ({pct:5.1f}%)")

    print(f"{C.BLUE}├────────────────────────────────────────────────────────────────┤{C.RESET}")
    print(f"{C.BLUE}│{C.RESET} {C.BOLD}TOTAL:{C.RESET}       {format_number(total_downloaded):>20} / {format_number(total_items):<10}")
    print(f"{C.BLUE}└────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()

    # Recent Activity Log
    print(f"{C.MAGENTA}┌─ RECENT ACTIVITY ──────────────────────────────────────────────┐{C.RESET}")
    recent = get_recent_log_lines(6)
    if recent:
        for line in recent:
            # Colorize based on content
            if "ERROR" in line or "failed" in line.lower():
                color = C.RED
            elif "Downloaded" in line or "success" in line:
                color = C.GREEN
            elif "Starting" in line:
                color = C.CYAN
            else:
                color = C.DIM

            # Truncate timestamp
            if len(line) > 23 and line[10] == " ":
                line = line[11:]  # Remove date, keep time

            print(f"{C.MAGENTA}│{C.RESET} {color}{line[:66]}{C.RESET}")
    else:
        print(f"{C.MAGENTA}│{C.RESET} {C.DIM}No recent activity{C.RESET}")
    print(f"{C.MAGENTA}└────────────────────────────────────────────────────────────────┘{C.RESET}")

    print()
    print(f"{C.DIM}Auto-refreshing every 5s. Press Ctrl+C to exit.{C.RESET}")


def main():
    """Main loop."""
    print("Starting live status monitor...")

    try:
        while True:
            render_dashboard()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nExiting.")


if __name__ == "__main__":
    main()
