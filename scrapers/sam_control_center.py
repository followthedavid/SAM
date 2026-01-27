#!/usr/bin/env python3
"""
SAM CONTROL CENTER - Unified visual dashboard for everything.

Shows LIVE status with proof of activity:
- All scrapers with real-time progress
- Training data accumulation
- Evolution/learning pipeline
- System resources

Updates every 3 seconds with color-coded status.

Run: python3 sam_control_center.py
"""

import os
import sys
import time
import sqlite3
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ANSI colors and styles
class S:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLINK = "\033[5m"

    # Colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Backgrounds
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"


def clear():
    os.system('clear')


def get_terminal_size():
    try:
        cols, rows = os.get_terminal_size()
        return cols, rows
    except:
        return 120, 40


def progress_bar(current, total, width=30, show_pct=True):
    """Create a visual progress bar."""
    if total == 0:
        pct = 0
    else:
        pct = min(current / total, 1.0)

    filled = int(pct * width)
    empty = width - filled

    # Color based on progress
    if pct >= 0.9:
        color = S.GREEN
    elif pct >= 0.5:
        color = S.YELLOW
    elif pct >= 0.1:
        color = S.CYAN
    else:
        color = S.RED

    bar = f"{color}{'█' * filled}{'░' * empty}{S.RESET}"

    if show_pct:
        return f"[{bar}] {pct*100:5.1f}%"
    return f"[{bar}]"


def fmt_num(n):
    """Format number with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def get_running_processes():
    """Get all SAM-related running processes."""
    processes = {}

    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5
        )

        keywords = [
            "scraper", "ripper", "collector", "evolution",
            "sam_api", "overnight", "parallel", "firstview"
        ]

        for line in result.stdout.split('\n'):
            for kw in keywords:
                if kw in line.lower() and "python" in line.lower():
                    # Extract process name
                    parts = line.split()
                    if len(parts) > 10:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        cmd = ' '.join(parts[10:])[:60]

                        # Get a short name
                        for k in keywords:
                            if k in cmd.lower():
                                name = k
                                break
                        else:
                            name = cmd[:20]

                        processes[pid] = {
                            "name": name,
                            "cpu": cpu,
                            "mem": mem,
                            "cmd": cmd,
                        }
    except:
        pass

    return processes


def get_scraper_stats():
    """Get stats from all scraper databases."""
    stats = {}

    databases = {
        "apple_dev": {
            "db": "/Volumes/David External/apple_dev_archive/apple_dev.db",
            "query": "SELECT (SELECT COUNT(*) FROM docs) + (SELECT COUNT(*) FROM github_code) + (SELECT COUNT(*) FROM stackoverflow)",
        },
        "nifty": {
            "db": "/Volumes/David External/nifty_archive/nifty_index.db",
            "total": "SELECT COUNT(*) FROM stories",
            "done": "SELECT COUNT(*) FROM stories WHERE downloaded=1",
        },
        "ao3": {
            "db": "/Volumes/David External/ao3_archive/ao3_index.db",
            "total": "SELECT COUNT(*) FROM works",
            "done": "SELECT COUNT(*) FROM works WHERE downloaded=1",
        },
        "firstview": {
            "db": "/Volumes/David External/firstview_archive/firstview_index.db",
            "total": "SELECT COUNT(*) FROM photos",
            "done": "SELECT COUNT(*) FROM photos WHERE downloaded=1",
        },
        "wwd": {
            "db": "/Volumes/#1/wwd_archive/wwd_index.db",
            "total": "SELECT COUNT(*) FROM articles",
            "done": "SELECT COUNT(*) FROM articles WHERE downloaded=1",
        },
        "vmag": {
            "db": "/Volumes/#1/vmag_archive/vmag_index.db",
            "total": "SELECT COUNT(*) FROM articles",
            "done": "SELECT COUNT(*) FROM articles WHERE downloaded=1",
        },
        "wmag": {
            "db": "/Volumes/#1/wmag_archive/wmag_index.db",
            "total": "SELECT COUNT(*) FROM articles",
            "done": "SELECT COUNT(*) FROM articles WHERE downloaded=1",
        },
        "code": {
            "db": "/Volumes/David External/coding_training/code_collection.db",
            "query": "SELECT COUNT(*) FROM code_examples",
        },
    }

    for name, cfg in databases.items():
        db_path = Path(cfg["db"])
        if not db_path.exists():
            stats[name] = {"exists": False}
            continue

        try:
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()

            if "query" in cfg:
                c.execute(cfg["query"])
                total = c.fetchone()[0]
                done = total
            else:
                c.execute(cfg["total"])
                total = c.fetchone()[0]
                c.execute(cfg["done"])
                done = c.fetchone()[0]

            conn.close()

            stats[name] = {
                "exists": True,
                "total": total,
                "done": done,
            }
        except Exception as e:
            stats[name] = {"exists": True, "error": str(e)}

    return stats


def get_training_stats():
    """Get training data statistics."""
    stats = {
        "jsonl_lines": 0,
        "distillation": 0,
        "feedback": 0,
        "ready_to_train": False,
    }

    # Count JSONL training files
    training_dir = Path("/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_data")
    if training_dir.exists():
        for f in training_dir.glob("*.jsonl"):
            try:
                with open(f) as fp:
                    stats["jsonl_lines"] += sum(1 for _ in fp)
            except:
                pass

    # Distillation examples
    dist_db = Path("/Volumes/David External/sam_training/distilled/distillation.db")
    if dist_db.exists():
        try:
            conn = sqlite3.connect(str(dist_db))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM examples")
            stats["distillation"] = c.fetchone()[0]
            conn.close()
        except:
            pass

    # Learning queue
    learn_db = Path("/Volumes/David External/sam_learning/overnight_learning.db")
    if learn_db.exists():
        try:
            conn = sqlite3.connect(str(learn_db))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM question_queue WHERE escalated=0")
            stats["learning_queue"] = c.fetchone()[0]
            conn.close()
        except:
            stats["learning_queue"] = 0
    else:
        stats["learning_queue"] = 0

    stats["ready_to_train"] = stats["jsonl_lines"] >= 100

    return stats


def get_recent_log_activity():
    """Get recent activity from log files."""
    activity = []

    logs = [
        ("/Volumes/David External/scraper_daemon/daemon.log", "scraper"),
        ("/Volumes/David External/sam_evolution/evolution.log", "evolution"),
        ("/Volumes/David External/code_scraping/parallel_code.log", "code"),
        ("/Volumes/David External/firstview_archive/reindex.log", "firstview"),
    ]

    for log_path, source in logs:
        if Path(log_path).exists():
            try:
                result = subprocess.run(
                    ["tail", "-3", log_path],
                    capture_output=True, text=True, timeout=2
                )
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Truncate and clean
                        line = line.strip()[:80]
                        activity.append((source, line))
            except:
                pass

    return activity[-10:]  # Last 10 lines


def get_sam_api_status():
    """Check SAM API status."""
    try:
        import requests
        r = requests.get("http://localhost:8765/api/health", timeout=2)
        if r.status_code == 200:
            return {"running": True, "status": "healthy"}
    except:
        pass
    return {"running": False}


def render_dashboard():
    """Render the full dashboard."""
    clear()
    cols, rows = get_terminal_size()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header
    print(f"{S.BOLD}{S.BG_BLUE}{S.WHITE}")
    print("╔" + "═" * (cols - 2) + "╗")
    title = "SAM CONTROL CENTER"
    subtitle = f"Live Status • {now}"
    print(f"║{title:^{cols-2}}║")
    print(f"║{subtitle:^{cols-2}}║")
    print("╚" + "═" * (cols - 2) + "╝")
    print(S.RESET)

    # Get all data
    processes = get_running_processes()
    scraper_stats = get_scraper_stats()
    training_stats = get_training_stats()
    sam_status = get_sam_api_status()
    activity = get_recent_log_activity()

    # Section 1: Running Processes
    print(f"\n{S.CYAN}{S.BOLD}┌─ RUNNING PROCESSES ({'●' if processes else '○'}) {'─' * 50}┐{S.RESET}")

    if processes:
        for pid, info in list(processes.items())[:6]:
            status = f"{S.GREEN}●{S.RESET}"
            print(f"{S.CYAN}│{S.RESET} {status} {info['name']:<15} CPU:{info['cpu']:>5}% MEM:{info['mem']:>5}%  {S.DIM}{info['cmd'][:40]}{S.RESET}")
    else:
        print(f"{S.CYAN}│{S.RESET} {S.DIM}No SAM processes detected{S.RESET}")

    print(f"{S.CYAN}└{'─' * (cols - 2)}┘{S.RESET}")

    # Section 2: Data Collection (two columns)
    print(f"\n{S.GREEN}{S.BOLD}┌─ DATA COLLECTION {'─' * 55}┐{S.RESET}")

    # Coding sources
    print(f"{S.GREEN}│{S.RESET} {S.BOLD}CODING (Priority 1){S.RESET}")
    for name in ["apple_dev", "code"]:
        if name in scraper_stats and scraper_stats[name].get("exists"):
            s = scraper_stats[name]
            total = s.get("total", 0)
            done = s.get("done", 0)
            bar = progress_bar(done, total, width=20)
            print(f"{S.GREEN}│{S.RESET}   {name:<12} {bar} {fmt_num(done):>7}/{fmt_num(total):<7}")

    # Roleplay sources
    print(f"{S.GREEN}│{S.RESET}")
    print(f"{S.GREEN}│{S.RESET} {S.BOLD}ROLEPLAY{S.RESET}")
    for name in ["nifty", "ao3"]:
        if name in scraper_stats and scraper_stats[name].get("exists"):
            s = scraper_stats[name]
            total = s.get("total", 0)
            done = s.get("done", 0)
            bar = progress_bar(done, total, width=20)
            print(f"{S.GREEN}│{S.RESET}   {name:<12} {bar} {fmt_num(done):>7}/{fmt_num(total):<7}")

    # Fashion sources
    print(f"{S.GREEN}│{S.RESET}")
    print(f"{S.GREEN}│{S.RESET} {S.BOLD}FASHION{S.RESET}")
    for name in ["firstview", "wwd", "vmag", "wmag"]:
        if name in scraper_stats and scraper_stats[name].get("exists"):
            s = scraper_stats[name]
            total = s.get("total", 0)
            done = s.get("done", 0)
            bar = progress_bar(done, total, width=20)
            print(f"{S.GREEN}│{S.RESET}   {name:<12} {bar} {fmt_num(done):>7}/{fmt_num(total):<7}")

    print(f"{S.GREEN}└{'─' * (cols - 2)}┘{S.RESET}")

    # Section 3: Training Pipeline
    print(f"\n{S.MAGENTA}{S.BOLD}┌─ TRAINING PIPELINE {'─' * 53}┐{S.RESET}")

    ready_icon = f"{S.GREEN}✓{S.RESET}" if training_stats["ready_to_train"] else f"{S.RED}✗{S.RESET}"
    print(f"{S.MAGENTA}│{S.RESET}   Training Data:     {fmt_num(training_stats['jsonl_lines']):>10} examples")
    print(f"{S.MAGENTA}│{S.RESET}   Distillation:      {training_stats['distillation']:>10} captured")
    print(f"{S.MAGENTA}│{S.RESET}   Learning Queue:    {training_stats.get('learning_queue', 0):>10} pending")
    print(f"{S.MAGENTA}│{S.RESET}   Ready to Train:    {ready_icon} {'Yes - run train_roleplay_lora.py' if training_stats['ready_to_train'] else 'Need 100+ examples'}")

    print(f"{S.MAGENTA}└{'─' * (cols - 2)}┘{S.RESET}")

    # Section 4: SAM Brain Status
    print(f"\n{S.YELLOW}{S.BOLD}┌─ SAM BRAIN {'─' * 61}┐{S.RESET}")

    sam_icon = f"{S.GREEN}● ONLINE{S.RESET}" if sam_status["running"] else f"{S.RED}● OFFLINE{S.RESET}"
    print(f"{S.YELLOW}│{S.RESET}   API Status:        {sam_icon}")
    print(f"{S.YELLOW}│{S.RESET}   Endpoint:          http://localhost:8765")

    # Evolution daemon status
    evolution_running = any("evolution" in p["name"] for p in processes.values())
    evo_icon = f"{S.GREEN}● ACTIVE{S.RESET}" if evolution_running else f"{S.RED}● STOPPED{S.RESET}"
    print(f"{S.YELLOW}│{S.RESET}   Evolution Daemon:  {evo_icon}")

    print(f"{S.YELLOW}└{'─' * (cols - 2)}┘{S.RESET}")

    # Section 5: Recent Activity (proof it's working)
    print(f"\n{S.BLUE}{S.BOLD}┌─ LIVE ACTIVITY (proof of life) {'─' * 41}┐{S.RESET}")

    if activity:
        for source, line in activity[-6:]:
            # Color by type
            if "error" in line.lower():
                color = S.RED
            elif "success" in line.lower() or "downloaded" in line.lower() or "collected" in line.lower():
                color = S.GREEN
            elif "starting" in line.lower():
                color = S.CYAN
            else:
                color = S.DIM

            # Truncate
            display = f"[{source:>10}] {line[:60]}"
            print(f"{S.BLUE}│{S.RESET} {color}{display}{S.RESET}")
    else:
        print(f"{S.BLUE}│{S.RESET} {S.DIM}No recent activity - check if daemons are running{S.RESET}")

    print(f"{S.BLUE}└{'─' * (cols - 2)}┘{S.RESET}")

    # Totals
    total_indexed = sum(s.get("total", 0) for s in scraper_stats.values() if isinstance(s, dict) and s.get("exists"))
    total_downloaded = sum(s.get("done", 0) for s in scraper_stats.values() if isinstance(s, dict) and s.get("exists"))

    print(f"\n{S.BOLD}TOTALS: {fmt_num(total_downloaded)} downloaded / {fmt_num(total_indexed)} indexed")
    print(f"        {training_stats['jsonl_lines']:,} training examples ready{S.RESET}")

    print(f"\n{S.DIM}Auto-refreshing every 3s • Ctrl+C to exit{S.RESET}")


def main():
    print("Starting SAM Control Center...")

    try:
        while True:
            render_dashboard()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\nExiting Control Center.")


if __name__ == "__main__":
    main()
