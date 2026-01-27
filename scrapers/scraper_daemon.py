#!/usr/bin/env python3
"""
SAM Scraper Daemon - Crash-resilient, memory-safe scraper rotation.

Features:
- Runs ONE scraper at a time (8GB RAM safe)
- SQLite-based progress tracking (survives crashes)
- Automatic resume on restart
- Aggressive rate limiting
- Logging to file
- Optional launchd integration for auto-restart

Usage:
    python3 scraper_daemon.py start          # Run daemon (foreground)
    python3 scraper_daemon.py start --bg     # Run daemon (background)
    python3 scraper_daemon.py status         # Show status
    python3 scraper_daemon.py stop           # Stop daemon
    python3 scraper_daemon.py install        # Install launchd plist
"""

import os
import sys
import json
import time
import signal
import sqlite3
import logging
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# Paths
SCRAPER_DIR = Path(__file__).parent
DAEMON_DIR = Path("/Volumes/David External/scraper_daemon")
DB_PATH = DAEMON_DIR / "daemon_state.db"
LOG_PATH = DAEMON_DIR / "daemon.log"
PID_PATH = DAEMON_DIR / "daemon.pid"
PLIST_PATH = Path.home() / "Library/LaunchAgents/com.sam.scraper-daemon.plist"

# Scraper configurations organized by category
# Each scraper: script, init_command, command, storage, rate_limit, priority, enabled
# Lower priority number = runs first

SCRAPERS = {
    # ============ ROLEPLAY CONTENT (Priority 1-10) ============
    "nifty": {
        "script": "nifty_ripper.py",
        "init_command": None,  # Already indexed: 64,557 stories
        "command": ["download", "--limit", "50"],
        "storage": "/Volumes/David External/nifty_archive",
        "rate_limit": 3.0,
        "priority": 1,
        "enabled": True,
        "category": "roleplay",
    },
    "ao3": {
        "script": "ao3_ripper.py",
        "init_command": None,  # Already indexed
        "command": ["download", "--limit", "20"],
        "storage": "/Volumes/David External/ao3_archive",
        "rate_limit": 5.0,  # AO3 is strict
        "priority": 2,
        "enabled": True,
        "category": "roleplay",
    },
    "ao3_roleplay": {
        "script": "ao3_roleplay_ripper.py",
        "init_command": ["index", "--limit", "100"],  # Small init, AO3 is slow
        "command": ["download", "--limit", "10"],
        "storage": "/Volumes/David External/ao3_archive",
        "rate_limit": 5.0,
        "priority": 8,  # Lower priority - slow site
        "enabled": True,
        "category": "roleplay",
    },
    "literotica": {
        "script": "literotica_ripper.py",
        "init_command": ["index", "--limit", "500"],  # Smaller init
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/literotica_archive",
        "rate_limit": 3.0,
        "priority": 9,
        "enabled": True,
        "category": "roleplay",
    },
    "dark_psych": {
        "script": "dark_psych_ripper.py",
        "init_command": ["index", "--limit", "300"],  # Smaller init
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/dark_psych_archive",
        "rate_limit": 3.0,
        "priority": 10,
        "enabled": True,
        "category": "roleplay",
    },

    # ============ CODING CONTENT (Priority 11-20) ============
    "code_github": {
        "script": "code_collector.py",
        "init_command": None,
        "command": ["github", "--limit", "100"],
        "storage": "/Volumes/David External/code_archive",
        "rate_limit": 1.0,  # GitHub API has rate limits
        "priority": 11,
        "enabled": True,
        "category": "coding",
    },
    "code_stackoverflow": {
        "script": "code_collector.py",
        "init_command": None,
        "command": ["stackoverflow", "--limit", "100"],
        "storage": "/Volumes/David External/code_archive",
        "rate_limit": 1.0,
        "priority": 12,
        "enabled": True,
        "category": "coding",
    },
    "code_prs": {
        "script": "code_collector.py",
        "init_command": None,
        "command": ["prs", "--limit", "50"],
        "storage": "/Volumes/David External/code_archive",
        "rate_limit": 1.0,
        "priority": 13,
        "enabled": True,
        "category": "coding",
    },

    # ============ FASHION/MAGAZINE CONTENT (Priority 21-30) ============
    "wmag": {
        "script": "wmag_ripper.py",
        "init_command": ["index", "--limit", "500"],
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/wmag_archive",
        "rate_limit": 2.0,
        "priority": 21,
        "enabled": True,
        "category": "fashion",
    },
    "vmag": {
        "script": "vmag_ripper.py",
        "init_command": ["index", "--limit", "500"],
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/vmag_archive",
        "rate_limit": 2.0,
        "priority": 22,
        "enabled": True,
        "category": "fashion",
    },
    "gq_esquire": {
        "script": "gq_esquire_ripper.py",
        "init_command": ["index", "--limit", "500"],
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/gq_esquire_archive",
        "rate_limit": 2.0,
        "priority": 23,
        "enabled": True,
        "category": "fashion",
    },
    "thecut": {
        "script": "thecut_ripper.py",
        "init_command": ["index", "--limit", "500"],
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/thecut_archive",
        "rate_limit": 2.0,
        "priority": 24,
        "enabled": True,
        "category": "fashion",
    },
    "interview_mag": {
        "script": "interview_ripper.py",
        "init_command": ["index", "--limit", "500"],
        "command": ["download", "--limit", "30"],
        "storage": "/Volumes/David External/interview_archive",
        "rate_limit": 2.0,
        "priority": 25,
        "enabled": True,
        "category": "fashion",
    },
    "firstview": {
        "script": "firstview_ripper.py",
        "init_command": None,  # Already indexed 337K photos
        "command": ["download", "--limit", "500"],
        "storage": "/Volumes/David External/firstview_archive",
        "rate_limit": 0.3,
        "priority": 3,  # HIGH PRIORITY - already indexed
        "enabled": True,
        "category": "fashion",
    },
    "wwd": {
        "script": "wwd_ripper.py",
        "init_command": None,  # Already indexed 247K articles
        "command": ["download", "--limit", "50"],
        "storage": "/Volumes/#1/wwd_archive",
        "rate_limit": 2.0,
        "priority": 4,  # HIGH PRIORITY - already indexed
        "enabled": True,
        "category": "fashion",
    },

    # ============ APPLE/MAC DEVELOPMENT (Priority 5-7) ============
    # HIGH PRIORITY - Native Mac coding knowledge for SAM
    "apple_github": {
        "script": "apple_dev_collector.py",
        "init_command": None,
        "command": ["github", "--limit", "200"],
        "storage": "/Volumes/David External/apple_dev_archive",
        "rate_limit": 1.0,  # GitHub API rate limits
        "priority": 5,
        "enabled": True,
        "category": "coding",
        "refresh_days": 7,  # Re-run weekly for new repos
    },
    "apple_stackoverflow": {
        "script": "apple_dev_collector.py",
        "init_command": None,
        "command": ["stackoverflow", "--limit", "200"],
        "storage": "/Volumes/David External/apple_dev_archive",
        "rate_limit": 1.0,
        "priority": 6,
        "enabled": True,
        "category": "coding",
        "refresh_days": 3,  # Re-run every 3 days for new Q&A
    },
    "apple_cutting_edge": {
        "script": "apple_dev_collector.py",
        "init_command": None,
        "command": ["cutting-edge", "--limit", "100"],
        "storage": "/Volumes/David External/apple_dev_archive",
        "rate_limit": 2.0,
        "priority": 7,
        "enabled": True,
        "category": "coding",
        "refresh_days": 1,  # Daily - catch Swift Evolution, WWDC updates
    },

    # ============ OTHER CONTENT (Priority 31+) ============
    "cai_dumps": {
        "script": "cai_dumps_finder.py",
        "init_command": ["find"],
        "command": ["process"],
        "storage": "/Volumes/David External/cai_archive",
        "rate_limit": 0.5,  # Local processing
        "priority": 31,
        "enabled": False,  # Enable if you have CAI dumps to process
        "category": "other",
    },
}

# Global state
running = True


def setup_logging():
    """Setup logging to file and console."""
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("scraper_daemon")


def init_db():
    """Initialize SQLite database for state tracking."""
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Scraper run history
    c.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraper TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            items_processed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            error_message TEXT
        )
    ''')

    # Daemon state
    c.execute('''
        CREATE TABLE IF NOT EXISTS daemon_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def get_last_run(scraper: str) -> Optional[Dict]:
    """Get last run info for a scraper."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT started_at, finished_at, items_processed, status
        FROM runs WHERE scraper = ?
        ORDER BY id DESC LIMIT 1
    ''', (scraper,))
    row = c.fetchone()
    conn.close()

    if row:
        return {
            "started_at": row[0],
            "finished_at": row[1],
            "items_processed": row[2],
            "status": row[3]
        }
    return None


def record_run_start(scraper: str) -> int:
    """Record start of a scraper run, return run ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO runs (scraper, started_at, status)
        VALUES (?, ?, 'running')
    ''', (scraper, datetime.now().isoformat()))
    run_id = c.lastrowid
    conn.commit()
    conn.close()
    return run_id


def record_run_end(run_id: int, items: int, status: str, error: str = None):
    """Record end of a scraper run."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE runs SET finished_at = ?, items_processed = ?, status = ?, error_message = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), items, status, error, run_id))
    conn.commit()
    conn.close()


def get_next_scraper() -> Optional[str]:
    """Get next scraper to run based on priority, last run time, and refresh schedule."""
    enabled = {k: v for k, v in SCRAPERS.items() if v["enabled"]}

    if not enabled:
        return None

    # Sort by priority, then by oldest last run, with refresh_days override
    scored = []
    for name, config in enabled.items():
        last_run = get_last_run(name)

        # Calculate time since last run
        if last_run and last_run["finished_at"]:
            last_time = datetime.fromisoformat(last_run["finished_at"])
            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            days_since = hours_since / 24
        else:
            hours_since = 999  # Never run = high priority
            days_since = 999

        # Check if this scraper needs a refresh (cutting-edge content)
        refresh_days = config.get("refresh_days")
        needs_refresh = refresh_days and days_since >= refresh_days

        # Score: lower is better (run sooner)
        # Scrapers needing refresh get massive priority boost
        if needs_refresh:
            # Boost priority significantly - run before anything else
            score = config["priority"] - 100 - (hours_since * 0.1)
        else:
            score = config["priority"] - (hours_since * 0.1)

        scored.append((name, score, needs_refresh))

    scored.sort(key=lambda x: x[1])
    return scored[0][0] if scored else None


def needs_init(scraper_name: str) -> bool:
    """Check if scraper needs initialization (indexing)."""
    config = SCRAPERS[scraper_name]
    if not config.get("init_command"):
        return False

    # Check database for previous init
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM runs
        WHERE scraper = ? AND status = 'init_complete'
    ''', (scraper_name,))
    count = c.fetchone()[0]
    conn.close()

    return count == 0


def run_init(scraper_name: str, logger) -> bool:
    """Run initialization (indexing) for a scraper."""
    config = SCRAPERS[scraper_name]
    script_path = SCRAPER_DIR / config["script"]

    if not config.get("init_command"):
        return True

    cmd = [sys.executable, str(script_path)] + config["init_command"]
    logger.info(f"Initializing {scraper_name}: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRAPER_DIR),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max for init - keep it short
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        if result.stdout:
            for line in result.stdout.strip().split('\n')[-5:]:
                logger.info(f"  {line}")

        if result.returncode == 0:
            # Record init complete
            conn = get_db()
            c = conn.cursor()
            c.execute('''
                INSERT INTO runs (scraper, started_at, finished_at, status)
                VALUES (?, ?, ?, 'init_complete')
            ''', (scraper_name, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        else:
            logger.error(f"Init failed: {result.stderr[-300:] if result.stderr else 'no error'}")
            return False

    except Exception as e:
        logger.error(f"Init exception: {e}")
        return False


def run_scraper(scraper_name: str, logger) -> tuple[int, str]:
    """Run a single scraper batch. Returns (items_processed, status)."""
    config = SCRAPERS[scraper_name]
    script_path = SCRAPER_DIR / config["script"]

    if not script_path.exists():
        logger.warning(f"Script not found: {script_path}")
        return 0, "error"

    # Check if init needed
    if needs_init(scraper_name):
        logger.info(f"{scraper_name} needs initialization...")
        if not run_init(scraper_name, logger):
            return 0, "init_failed"
        logger.info(f"{scraper_name} initialized successfully")

    # Build command
    cmd = [
        sys.executable,
        str(script_path),
    ] + config["command"]

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        # Run with Popen for real-time output logging
        process = subprocess.Popen(
            cmd,
            cwd=str(SCRAPER_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        # Read output line by line with timeout
        output_lines = []
        start_time = time.time()
        timeout = 1800  # 30 minutes max

        import select
        while process.poll() is None:
            # Check timeout
            if time.time() - start_time > timeout:
                process.kill()
                logger.warning("Scraper timed out")
                return 0, "timeout"

            # Read available output (non-blocking)
            if select.select([process.stdout], [], [], 5.0)[0]:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line)
                    # Log progress lines to keep daemon log alive
                    if any(x in line.lower() for x in ['download', 'progress', 'indexed', '%', '/']):
                        logger.info(f"  {line.strip()[:100]}")

        # Get remaining output
        remaining = process.stdout.read()
        if remaining:
            output_lines.extend(remaining.split('\n'))

        result_stdout = '\n'.join(output_lines)
        result_returncode = process.returncode

        # Log final output
        for line in output_lines[-5:]:
            if line.strip():
                logger.info(f"  {line.strip()[:100]}")

        if result_returncode == 0:
            items = extract_items_count(result_stdout)
            return items, "success"
        else:
            logger.error(f"Scraper failed (exit {result_returncode})")
            return 0, "error"

    except Exception as e:
        logger.warning(f"Scraper error: {e}")
        return 0, "timeout"
    except Exception as e:
        logger.error(f"Scraper exception: {e}")
        return 0, "exception"


def extract_items_count(output: str) -> int:
    """Try to extract items processed from scraper output."""
    import re

    # Look for common patterns
    patterns = [
        r"Downloaded\s+(\d+)",
        r"Processed\s+(\d+)",
        r"(\d+)\s+items",
        r"(\d+)\s+stories",
        r"(\d+)\s+works",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return 0


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    running = False


def write_pid():
    """Write PID file."""
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_PATH, 'w') as f:
        f.write(str(os.getpid()))


def read_pid() -> Optional[int]:
    """Read PID from file."""
    if PID_PATH.exists():
        with open(PID_PATH, 'r') as f:
            return int(f.read().strip())
    return None


def is_running() -> bool:
    """Check if daemon is running."""
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, 0)  # Check if process exists
            return True
        except OSError:
            pass
    return False


def daemon_loop(logger):
    """Main daemon loop."""
    global running

    logger.info("=" * 60)
    logger.info("SAM Scraper Daemon starting")
    logger.info(f"Enabled scrapers: {[k for k, v in SCRAPERS.items() if v['enabled']]}")
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    write_pid()
    consecutive_errors = 0
    max_consecutive_errors = 5

    while running:
        try:
            # Get next scraper
            scraper_name = get_next_scraper()

            if not scraper_name:
                logger.info("No scrapers enabled, sleeping 5 minutes...")
                time.sleep(300)
                continue

            config = SCRAPERS[scraper_name]

            # Check storage exists
            storage_path = Path(config["storage"])
            if not storage_path.parent.exists():
                logger.warning(f"Storage path unavailable: {storage_path}, skipping {scraper_name}")
                time.sleep(60)
                continue

            # Run scraper
            logger.info(f"Starting {scraper_name}...")
            run_id = record_run_start(scraper_name)

            items, status = run_scraper(scraper_name, logger)

            record_run_end(run_id, items, status)
            logger.info(f"Finished {scraper_name}: {items} items, status={status}")

            if status == "success":
                consecutive_errors = 0
            else:
                consecutive_errors += 1

            # Back off if too many errors
            if consecutive_errors >= max_consecutive_errors:
                logger.warning(f"{consecutive_errors} consecutive errors, sleeping 10 minutes...")
                time.sleep(600)
                consecutive_errors = 0

            # Rate limit between scrapers
            sleep_time = max(config["rate_limit"] * 10, 30)  # At least 30 seconds between batches
            logger.info(f"Sleeping {sleep_time}s before next batch...")
            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Daemon loop error: {e}", exc_info=True)
            time.sleep(60)

    # Cleanup
    if PID_PATH.exists():
        PID_PATH.unlink()
    logger.info("Daemon stopped")


def show_status():
    """Show current daemon status."""
    print("\n" + "=" * 60)
    print("SAM Scraper Daemon Status")
    print("=" * 60)

    # Daemon running?
    if is_running():
        pid = read_pid()
        print(f"\nDaemon: RUNNING (PID {pid})")
    else:
        print(f"\nDaemon: STOPPED")

    # Database exists?
    if not DB_PATH.exists():
        print("\nNo run history found.")
        return

    print(f"\nLast runs:")
    print("-" * 60)

    conn = get_db()
    c = conn.cursor()

    for name, config in SCRAPERS.items():
        c.execute('''
            SELECT started_at, finished_at, items_processed, status
            FROM runs WHERE scraper = ?
            ORDER BY id DESC LIMIT 1
        ''', (name,))
        row = c.fetchone()

        enabled = "✓" if config["enabled"] else "✗"
        if row:
            status = row[3]
            items = row[2]
            when = row[0][:16] if row[0] else "never"
            print(f"  [{enabled}] {name:20} {status:10} {items:6} items  ({when})")
        else:
            print(f"  [{enabled}] {name:20} never run")

    conn.close()

    # Total items
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT SUM(items_processed) FROM runs WHERE status = "success"')
    total = c.fetchone()[0] or 0
    conn.close()

    print("-" * 60)
    print(f"Total items processed: {total:,}")
    print()


def stop_daemon():
    """Stop the daemon."""
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")

            # Wait for shutdown
            for _ in range(10):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except OSError:
                    print("Daemon stopped")
                    return

            print("Daemon did not stop, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
        except OSError as e:
            print(f"Error stopping daemon: {e}")
    else:
        print("Daemon not running")


def install_launchd():
    """Install launchd plist for auto-restart."""
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sam.scraper-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{__file__}</string>
        <string>start</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{SCRAPER_DIR}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <dict>
        <key>Crashed</key>
        <true/>
    </dict>
    <key>StandardOutPath</key>
    <string>{LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_PATH}</string>
    <key>ThrottleInterval</key>
    <integer>60</integer>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
'''

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content)

    print(f"Installed: {PLIST_PATH}")
    print("\nTo load (start on crash/restart):")
    print(f"  launchctl load {PLIST_PATH}")
    print("\nTo unload:")
    print(f"  launchctl unload {PLIST_PATH}")
    print("\nTo start now:")
    print(f"  launchctl start com.sam.scraper-daemon")


def main():
    parser = argparse.ArgumentParser(description="SAM Scraper Daemon")
    parser.add_argument("command", choices=["start", "status", "stop", "install"],
                       help="Command to run")
    parser.add_argument("--bg", action="store_true", help="Run in background")

    args = parser.parse_args()

    if args.command == "start":
        if is_running():
            print("Daemon already running")
            sys.exit(1)

        init_db()
        logger = setup_logging()

        if args.bg:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                print(f"Daemon started in background (PID {pid})")
                sys.exit(0)
            else:
                # Child process
                os.setsid()
                daemon_loop(logger)
        else:
            daemon_loop(logger)

    elif args.command == "status":
        init_db()
        show_status()

    elif args.command == "stop":
        stop_daemon()

    elif args.command == "install":
        install_launchd()


if __name__ == "__main__":
    main()
