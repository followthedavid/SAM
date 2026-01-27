#!/usr/bin/env python3
"""
SAM Overnight Runner
====================

Runs SAM tasks autonomously without human intervention.
Designed to work overnight while you sleep.

Features:
- Batch execution with auto-validation
- Automatic retry for failed tasks
- Progress logging to SSOT
- Email/notification on completion (optional)

Usage:
  python overnight_runner.py              # Run all pending tasks
  python overnight_runner.py --max 50     # Limit to 50 tasks
  python overnight_runner.py --daemon     # Continuous mode
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from claude_orchestrator import (
    load_tasks, save_tasks, run_pending_tasks,
    get_status, TaskStatus
)
from auto_validator import auto_review_tasks, validate_task, ValidationResult

# Configuration
SSOT_LOG = Path("/Volumes/Plex/SSOT/outputs")
MAX_RETRIES = 2
BATCH_SIZE = 5
SLEEP_BETWEEN_BATCHES = 10  # seconds

def log_progress(message: str, level: str = "INFO"):
    """Log to console and SSOT."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)

    # Log to SSOT
    log_file = SSOT_LOG / f"sam_overnight_{datetime.now().strftime('%Y%m%d')}.log"
    try:
        with open(log_file, "a") as f:
            f.write(line + "\n")
    except:
        pass

def run_overnight(max_tasks: int = 100, daemon: bool = False):
    """
    Main overnight runner.

    Args:
        max_tasks: Maximum tasks to process
        daemon: If True, run continuously
    """
    log_progress("=" * 60)
    log_progress("SAM Overnight Runner Started")
    log_progress(f"Max tasks: {max_tasks}, Daemon mode: {daemon}")
    log_progress("=" * 60)

    total_completed = 0
    total_failed = 0
    retry_counts = {}  # task_id -> retry count

    while True:
        status = get_status()
        pending = status['pending']

        if pending == 0:
            log_progress("No pending tasks")
            if not daemon:
                break
            log_progress("Daemon mode: sleeping 60s...")
            time.sleep(60)
            continue

        if total_completed >= max_tasks:
            log_progress(f"Reached max tasks limit ({max_tasks})")
            break

        # Run a batch
        batch_size = min(BATCH_SIZE, max_tasks - total_completed, pending)
        log_progress(f"Running batch of {batch_size} tasks...")

        try:
            results = run_pending_tasks(batch_size)
        except Exception as e:
            log_progress(f"Batch execution error: {e}", "ERROR")
            time.sleep(30)
            continue

        # Auto-validate results
        log_progress("Running auto-validation...")
        tasks = load_tasks()

        for task in tasks:
            if task.status != TaskStatus.NEEDS_REVIEW:
                continue

            report = validate_task(task.to_dict())

            if report.result == ValidationResult.PASSED:
                task.status = TaskStatus.COMPLETED
                total_completed += 1
                log_progress(f"[APPROVED] {task.id}: {task.description[:40]}...")

            elif report.result == ValidationResult.FAILED:
                # Check retry count
                retries = retry_counts.get(task.id, 0)
                if retries < MAX_RETRIES:
                    task.status = TaskStatus.PENDING
                    task.instructions += f"\n\n[RETRY {retries + 1}]: {report.reason}"
                    retry_counts[task.id] = retries + 1
                    log_progress(f"[RETRY] {task.id}: {report.reason}")
                else:
                    task.status = TaskStatus.FAILED
                    total_failed += 1
                    log_progress(f"[FAILED] {task.id}: Max retries exceeded", "ERROR")
            else:
                # NEEDS_HUMAN - skip for overnight
                log_progress(f"[SKIPPED] {task.id}: Needs human review")

        save_tasks(tasks)

        # Progress report
        status = get_status()
        log_progress(f"Progress: {status['completed']} completed, {status['pending']} pending, {status['failed']} failed")

        # Sleep between batches to avoid overloading
        if status['pending'] > 0 and total_completed < max_tasks:
            log_progress(f"Sleeping {SLEEP_BETWEEN_BATCHES}s between batches...")
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # Final report
    log_progress("=" * 60)
    log_progress("SAM Overnight Runner Complete")
    log_progress(f"Total completed: {total_completed}")
    log_progress(f"Total failed: {total_failed}")
    log_progress("=" * 60)

    return total_completed, total_failed

def create_launchd_plist():
    """Create a launchd plist for scheduled overnight runs."""
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sam.overnight-runner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{Path(__file__).absolute()}</string>
        <string>--max</string>
        <string>50</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/sam_overnight.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/sam_overnight_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>'''

    plist_path = Path.home() / "Library/LaunchAgents/com.sam.overnight-runner.plist"
    plist_path.write_text(plist_content)
    print(f"Created: {plist_path}")
    print(f"To enable: launchctl load {plist_path}")
    print(f"To disable: launchctl unload {plist_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Overnight Runner")
    parser.add_argument("--max", type=int, default=100, help="Max tasks to process")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--install", action="store_true", help="Install launchd plist for 2am runs")
    args = parser.parse_args()

    if args.install:
        create_launchd_plist()
    else:
        run_overnight(max_tasks=args.max, daemon=args.daemon)
