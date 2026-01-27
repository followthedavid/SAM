#!/usr/bin/env python3
"""
Parallel Code Scraper - Maximum speed for coding training data.

Runs multiple coding sources in parallel threads:
- Apple Dev (GitHub, StackOverflow, Swift Evolution)
- General GitHub (trending repos, PRs)
- StackOverflow (high-quality Q&A)

Usage:
    python3 parallel_code_scraper.py start    # Start parallel scraping
    python3 parallel_code_scraper.py status   # Show progress
    python3 parallel_code_scraper.py stop     # Stop all threads
"""

import os
import sys
import time
import signal
import sqlite3
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import json

# Setup
SCRAPER_DIR = Path(__file__).parent
LOG_DIR = Path("/Volumes/David External/code_scraping")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "parallel_code.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("parallel_code")

# Scraping sources - all coding focused
CODE_SOURCES = [
    # Apple/Mac native development - TOP PRIORITY
    {
        "name": "apple_github",
        "script": "apple_dev_collector.py",
        "args": ["github", "--limit", "500"],
        "priority": 1,
        "threads": 2,  # Can run multiple GitHub queries
    },
    {
        "name": "apple_stackoverflow",
        "script": "apple_dev_collector.py",
        "args": ["stackoverflow", "--limit", "500"],
        "priority": 1,
        "threads": 1,
    },
    {
        "name": "apple_cutting_edge",
        "script": "apple_dev_collector.py",
        "args": ["cutting-edge", "--limit", "200"],
        "priority": 1,
        "threads": 1,
    },
    # General coding
    {
        "name": "code_github",
        "script": "code_collector.py",
        "args": ["github", "--limit", "300"],
        "priority": 2,
        "threads": 1,
    },
    {
        "name": "code_stackoverflow",
        "script": "code_collector.py",
        "args": ["stackoverflow", "--limit", "300"],
        "priority": 2,
        "threads": 1,
    },
    {
        "name": "code_prs",
        "script": "code_collector.py",
        "args": ["prs", "--limit", "100"],
        "priority": 2,
        "threads": 1,
    },
]

# Global state
running = True
results = {}
threads_active = 0


def signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def run_scraper(source: dict) -> dict:
    """Run a single scraper and return results."""
    global threads_active
    threads_active += 1

    name = source["name"]
    script = SCRAPER_DIR / source["script"]
    args = source["args"]

    logger.info(f"Starting {name}...")
    start_time = time.time()

    try:
        cmd = [sys.executable, str(script)] + args
        result = subprocess.run(
            cmd,
            cwd=str(SCRAPER_DIR),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min max per source
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        elapsed = time.time() - start_time

        # Parse output for stats
        output = result.stdout + result.stderr
        items = 0

        # Look for collection counts in output
        for line in output.split('\n'):
            if 'collected' in line.lower() or 'downloaded' in line.lower():
                # Try to extract number
                import re
                nums = re.findall(r'\d+', line)
                if nums:
                    items = max(items, int(nums[0]))

        logger.info(f"Finished {name}: {items} items in {elapsed:.1f}s")

        return {
            "name": name,
            "success": result.returncode == 0,
            "items": items,
            "elapsed": elapsed,
            "error": None if result.returncode == 0 else result.stderr[:200]
        }

    except subprocess.TimeoutExpired:
        logger.error(f"{name} timed out after 30 minutes")
        return {"name": name, "success": False, "items": 0, "error": "timeout"}

    except Exception as e:
        logger.error(f"{name} error: {e}")
        return {"name": name, "success": False, "items": 0, "error": str(e)}

    finally:
        threads_active -= 1


def get_current_stats() -> dict:
    """Get stats from all coding databases."""
    stats = {}

    # Apple dev
    apple_db = Path("/Volumes/David External/apple_dev_archive/apple_dev.db")
    if apple_db.exists():
        try:
            conn = sqlite3.connect(str(apple_db))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM docs")
            docs = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM github_code")
            github = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM stackoverflow")
            so = c.fetchone()[0]
            conn.close()
            stats["apple_dev"] = {"docs": docs, "github": github, "stackoverflow": so, "total": docs + github + so}
        except:
            pass

    # General code
    code_db = Path("/Volumes/David External/coding_training/code_collection.db")
    if code_db.exists():
        try:
            conn = sqlite3.connect(str(code_db))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM code_examples")
            total = c.fetchone()[0]
            conn.close()
            stats["general_code"] = {"total": total}
        except:
            pass

    return stats


def run_parallel(max_workers: int = 4):
    """Run all code scrapers in parallel."""
    global running, results

    logger.info("=" * 60)
    logger.info("PARALLEL CODE SCRAPER STARTING")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Sources: {len(CODE_SOURCES)}")
    logger.info("=" * 60)

    # Initial stats
    initial_stats = get_current_stats()
    logger.info(f"Initial stats: {json.dumps(initial_stats, indent=2)}")

    cycle = 0
    while running:
        cycle += 1
        logger.info(f"\n=== CYCLE {cycle} ===")

        # Sort by priority
        sources = sorted(CODE_SOURCES, key=lambda x: x["priority"])

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="scraper") as executor:
            futures = {}

            for source in sources:
                if not running:
                    break
                future = executor.submit(run_scraper, source)
                futures[future] = source["name"]

            for future in as_completed(futures):
                if not running:
                    break
                name = futures[future]
                try:
                    result = future.result()
                    results[name] = result
                except Exception as e:
                    logger.error(f"{name} failed: {e}")
                    results[name] = {"success": False, "error": str(e)}

        # End of cycle stats
        final_stats = get_current_stats()
        logger.info(f"Cycle {cycle} complete. Current stats: {json.dumps(final_stats, indent=2)}")

        # Calculate gains
        for key in final_stats:
            if key in initial_stats:
                initial = initial_stats[key].get("total", 0)
                current = final_stats[key].get("total", 0)
                gained = current - initial
                if gained > 0:
                    logger.info(f"  {key}: +{gained} items")

        if running:
            logger.info("Sleeping 60s before next cycle...")
            for _ in range(60):
                if not running:
                    break
                time.sleep(1)

    logger.info("Parallel scraper stopped")


def show_status():
    """Show current scraping status."""
    stats = get_current_stats()

    print("\n" + "=" * 50)
    print("PARALLEL CODE SCRAPER STATUS")
    print("=" * 50)

    total = 0
    for source, data in stats.items():
        source_total = data.get("total", sum(v for k, v in data.items() if isinstance(v, int)))
        total += source_total
        print(f"\n{source}:")
        for key, val in data.items():
            print(f"  {key}: {val:,}")

    print(f"\n{'=' * 50}")
    print(f"TOTAL CODING EXAMPLES: {total:,}")
    print("=" * 50)

    # Check if parallel scraper is running
    log_file = LOG_DIR / "parallel_code.log"
    if log_file.exists():
        # Get last log line
        result = subprocess.run(
            ["tail", "-5", str(log_file)],
            capture_output=True, text=True
        )
        print(f"\nRecent activity:\n{result.stdout}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Code Scraper")
    parser.add_argument("command", choices=["start", "status", "stop"], default="status", nargs="?")
    parser.add_argument("--workers", type=int, default=4, help="Max parallel workers")

    args = parser.parse_args()

    if args.command == "start":
        run_parallel(args.workers)
    elif args.command == "status":
        show_status()
    elif args.command == "stop":
        # Find and kill the process
        subprocess.run(["pkill", "-f", "parallel_code_scraper.py"])
        print("Stop signal sent")


if __name__ == "__main__":
    main()
