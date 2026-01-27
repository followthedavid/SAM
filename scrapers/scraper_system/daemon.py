#!/usr/bin/env python3
"""
SAM Scraper Daemon - Continuous Background Scraping

Runs scrapers continuously with:
- Live status updates (what's happening now)
- Queue management (multiple scrapers, one at a time)
- Resource-aware execution (pauses when RAM is low)
- Automatic retry and scheduling
- HTTP API for status monitoring

Usage:
    python -m scraper_system.daemon             # Start daemon
    python -m scraper_system.daemon --port 8089 # Custom status port
    python -m scraper_system.daemon --add ao3   # Add scraper to queue
    python -m scraper_system.daemon --status    # Show current status

The daemon runs one scraper at a time (safe for 8GB Mac) but maintains a queue
so you can "run all at the same time" in the sense that they'll all complete.
"""

import json
import logging
import os
import signal
import sqlite3
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scraper_daemon")


class ScraperState(Enum):
    """Possible states for a scraper."""
    IDLE = "idle"
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    RATE_LIMITED = "rate_limited"
    PAUSED_LOW_RAM = "paused_low_ram"
    PAUSED_VLM = "paused_vlm"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_RETRY = "waiting_retry"


@dataclass
class ScraperProgress:
    """Real-time progress of a running scraper."""
    scraper_id: str
    state: ScraperState
    started_at: Optional[datetime] = None
    current_page: int = 0
    total_pages: Optional[int] = None
    items_scraped: int = 0
    items_downloaded: int = 0
    bytes_downloaded: int = 0
    current_url: str = ""
    last_activity: Optional[datetime] = None
    error: Optional[str] = None
    eta_seconds: Optional[int] = None
    rate_limit_remaining: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d['state'] = self.state.value
        d['started_at'] = self.started_at.isoformat() if self.started_at else None
        d['last_activity'] = self.last_activity.isoformat() if self.last_activity else None
        return d

    @property
    def status_message(self) -> str:
        """Human-readable status message."""
        if self.state == ScraperState.IDLE:
            return "Idle"
        elif self.state == ScraperState.QUEUED:
            return "Queued, waiting for turn"
        elif self.state == ScraperState.STARTING:
            return "Starting up..."
        elif self.state == ScraperState.RUNNING:
            pages = f"page {self.current_page}"
            if self.total_pages:
                pages += f"/{self.total_pages}"
            items = f"{self.items_scraped:,} items"
            mb = self.bytes_downloaded / (1024 * 1024)
            return f"Running: {pages}, {items}, {mb:.1f}MB"
        elif self.state == ScraperState.RATE_LIMITED:
            return f"Rate limited, {self.rate_limit_remaining}s remaining"
        elif self.state == ScraperState.PAUSED_LOW_RAM:
            return "Paused: Low RAM"
        elif self.state == ScraperState.PAUSED_VLM:
            return "Paused: VLM running"
        elif self.state == ScraperState.COMPLETED:
            return f"Completed: {self.items_scraped:,} items"
        elif self.state == ScraperState.FAILED:
            return f"Failed: {self.error}"
        elif self.state == ScraperState.WAITING_RETRY:
            return f"Waiting to retry (attempt {self.retry_count})"
        return self.state.value


@dataclass
class DaemonStatus:
    """Overall daemon status."""
    running: bool = True
    current_scraper: Optional[str] = None
    queue: List[str] = None
    schedules: Dict[str, str] = None  # scraper_id -> next_run_time
    resource_state: str = "available"
    available_ram_gb: float = 0.0
    cpu_percent: float = 0.0
    total_items_today: int = 0
    total_bytes_today: int = 0
    uptime_seconds: int = 0
    last_error: Optional[str] = None

    def __post_init__(self):
        if self.queue is None:
            self.queue = []
        if self.schedules is None:
            self.schedules = {}


class ScraperDaemon:
    """
    Background daemon that manages scraper execution.

    Key features:
    - One scraper at a time (8GB safe)
    - Queue multiple scrapers
    - Live progress tracking
    - Resource-aware pausing
    - HTTP API for monitoring
    """

    def __init__(self, status_port: int = 8089, state_file: str = None):
        self.status_port = status_port
        self.state_file = state_file or str(Path.home() / ".sam" / "scraper_daemon.json")

        # State
        self.running = True
        self.started_at = datetime.now()
        self.queue: deque = deque()
        self.progress: Dict[str, ScraperProgress] = {}
        self.current_scraper: Optional[str] = None
        self.lock = threading.Lock()

        # Statistics
        self.items_today = 0
        self.bytes_today = 0
        self.errors_today = 0

        # Threads
        self._worker_thread: Optional[threading.Thread] = None
        self._http_thread: Optional[threading.Thread] = None
        self._scheduler_thread: Optional[threading.Thread] = None

        # Ensure state directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_state()

    # =========================================================================
    # State Persistence
    # =========================================================================

    def _load_state(self):
        """Load persisted state from disk."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.queue = deque(state.get("queue", []))
                    logger.info(f"Loaded state: {len(self.queue)} items in queue")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")

    def _save_state(self):
        """Persist state to disk."""
        try:
            state = {
                "queue": list(self.queue),
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    # =========================================================================
    # Queue Management
    # =========================================================================

    def add_to_queue(self, scraper_id: str, priority: bool = False) -> bool:
        """Add a scraper to the execution queue."""
        with self.lock:
            if scraper_id in self.queue:
                return False  # Already queued

            if priority:
                self.queue.appendleft(scraper_id)
            else:
                self.queue.append(scraper_id)

            # Initialize progress
            self.progress[scraper_id] = ScraperProgress(
                scraper_id=scraper_id,
                state=ScraperState.QUEUED
            )

            self._save_state()
            logger.info(f"Added {scraper_id} to queue (position: {list(self.queue).index(scraper_id) + 1})")
            return True

    def add_all_enabled(self):
        """Add all enabled scrapers to the queue."""
        from .config.settings import DATA_SOURCES

        for source_id, info in DATA_SOURCES.items():
            if info.get("enabled"):
                self.add_to_queue(source_id)

    def remove_from_queue(self, scraper_id: str) -> bool:
        """Remove a scraper from the queue."""
        with self.lock:
            if scraper_id in self.queue:
                self.queue.remove(scraper_id)
                if scraper_id in self.progress:
                    del self.progress[scraper_id]
                self._save_state()
                return True
            return False

    def clear_queue(self):
        """Clear all queued scrapers."""
        with self.lock:
            self.queue.clear()
            self.progress.clear()
            self._save_state()

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def update_progress(self, scraper_id: str, **kwargs):
        """Update progress for a scraper."""
        with self.lock:
            if scraper_id not in self.progress:
                self.progress[scraper_id] = ScraperProgress(scraper_id=scraper_id, state=ScraperState.IDLE)

            progress = self.progress[scraper_id]
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            progress.last_activity = datetime.now()

    def get_progress(self, scraper_id: str) -> Optional[ScraperProgress]:
        """Get progress for a scraper."""
        return self.progress.get(scraper_id)

    def get_status(self) -> DaemonStatus:
        """Get overall daemon status."""
        from .core.resource_governor import get_governor

        governor = get_governor()
        resource_status = governor.get_status()

        # Calculate schedules
        from .config.settings import SCRAPER_SCHEDULES
        schedules = {}
        # TODO: Calculate next run times from cron expressions

        return DaemonStatus(
            running=self.running,
            current_scraper=self.current_scraper,
            queue=list(self.queue),
            schedules=schedules,
            resource_state=resource_status.state.value,
            available_ram_gb=resource_status.available_ram_gb,
            cpu_percent=resource_status.cpu_percent,
            total_items_today=self.items_today,
            total_bytes_today=self.bytes_today,
            uptime_seconds=int((datetime.now() - self.started_at).total_seconds()),
        )

    # =========================================================================
    # Worker Thread
    # =========================================================================

    def _worker_loop(self):
        """Main worker loop - processes queue with concurrent workers."""
        from .core.resource_governor import get_governor
        from .config.settings import MAX_CONCURRENT_SPIDERS

        governor = get_governor()
        active_futures: Dict[str, Future] = {}

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SPIDERS, thread_name_prefix="scraper") as executor:
            while self.running:
                try:
                    # Clean up completed futures
                    completed = [sid for sid, future in active_futures.items() if future.done()]
                    for sid in completed:
                        future = active_futures.pop(sid)
                        try:
                            future.result()  # Raise any exceptions
                        except Exception as e:
                            logger.error(f"Scraper {sid} raised: {e}")

                    # Check if we can start more
                    slots_available = MAX_CONCURRENT_SPIDERS - len(active_futures)

                    if slots_available <= 0 or not self.queue:
                        time.sleep(5)
                        continue

                    # Check resources before starting new scraper
                    resource_status = governor.get_status()
                    if not resource_status.can_start_scraper:
                        # Update status for queued scrapers
                        with self.lock:
                            if self.queue:
                                next_scraper = self.queue[0]
                                self.update_progress(
                                    next_scraper,
                                    state=ScraperState.PAUSED_LOW_RAM if resource_status.state.value == "low_ram" else ScraperState.PAUSED_VLM
                                )
                        logger.info(f"Waiting for resources: {resource_status.reason}")
                        time.sleep(30)
                        continue

                    # Start scrapers up to available slots
                    for _ in range(min(slots_available, len(self.queue))):
                        with self.lock:
                            if not self.queue:
                                break
                            scraper_id = self.queue.popleft()
                            self._save_state()

                        logger.info(f"Starting concurrent scraper: {scraper_id} (active: {len(active_futures) + 1}/{MAX_CONCURRENT_SPIDERS})")
                        future = executor.submit(self._run_scraper, scraper_id)
                        active_futures[scraper_id] = future

                    # Update current scraper list
                    with self.lock:
                        self.current_scraper = ", ".join(active_futures.keys()) if active_futures else None

                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    self.errors_today += 1
                    time.sleep(60)

            # Wait for remaining scrapers to finish
            for sid, future in active_futures.items():
                logger.info(f"Waiting for {sid} to complete...")
                future.result()

    def _run_scraper(self, scraper_id: str):
        """Run a single scraper with progress tracking."""
        from .config.settings import DATA_SOURCES, RATE_LIMITS

        logger.info(f"Starting scraper: {scraper_id}")

        self.update_progress(
            scraper_id,
            state=ScraperState.STARTING,
            started_at=datetime.now(),
            items_scraped=0,
            bytes_downloaded=0
        )

        try:
            # Get spider configuration
            source_config = DATA_SOURCES.get(scraper_id, {})
            rate_limit = RATE_LIMITS.get(scraper_id, RATE_LIMITS["default"])

            # Run with Scrapy in-process
            self._run_scrapy_spider(scraper_id, source_config, rate_limit)

            self.update_progress(scraper_id, state=ScraperState.COMPLETED)
            logger.info(f"Completed scraper: {scraper_id}")

        except Exception as e:
            logger.error(f"Scraper {scraper_id} failed: {e}")
            self.update_progress(
                scraper_id,
                state=ScraperState.FAILED,
                error=str(e)
            )
            self.errors_today += 1

    def _run_scrapy_spider(self, scraper_id: str, config: dict, rate_limit: float):
        """Run a Scrapy spider in a subprocess for memory isolation.

        Using subprocess instead of in-process CrawlerProcess because:
        1. Memory is freed when subprocess exits
        2. Twisted reactor issues are avoided
        3. Can run multiple spiders truly in parallel
        """
        import subprocess

        self.update_progress(scraper_id, state=ScraperState.RUNNING)

        # Build command to run spider via our module
        scraper_dir = Path(__file__).parent.parent  # scrapers/
        spider_script = f'''
import sys
sys.path.insert(0, "{scraper_dir}")
from scraper_system.__main__ import cmd_run
import argparse
args = argparse.Namespace(name="{scraper_id}", pages=None, force=True)
cmd_run(args)
'''

        cmd = [sys.executable, "-c", spider_script]

        logger.info(f"Running spider in subprocess: {scraper_id}")

        try:
            # Run in subprocess with output capture
            proc = subprocess.Popen(
                cmd,
                cwd=str(scraper_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, "SCRAPY_SETTINGS_MODULE": "scraper_system.config.scrapy_settings"},
            )

            items_count = 0
            last_url = ""

            # Monitor output for progress updates
            while proc.poll() is None:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                line = line.strip()

                # Parse Scrapy stats from output
                if "Scraped" in line:
                    try:
                        # Parse "Scraped 123 items"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "Scraped" and i + 1 < len(parts):
                                items_count = int(parts[i + 1])
                                break
                    except:
                        pass
                elif "item_scraped_count" in line:
                    try:
                        items_count = int(line.split(":")[-1].strip())
                    except:
                        pass
                elif "Crawled" in line and "http" in line:
                    # Extract URL from "Crawled (200) <GET http://...>"
                    try:
                        last_url = line.split("<GET ")[-1].split(">")[0]
                    except:
                        pass

                self.update_progress(
                    scraper_id,
                    items_scraped=items_count,
                    current_url=last_url,
                )

            # Read any remaining output
            remaining = proc.stdout.read()
            if remaining:
                for line in remaining.split("\n"):
                    if "item_scraped_count" in line:
                        try:
                            items_count = int(line.split(":")[-1].strip())
                        except:
                            pass

            # Update final count
            self.update_progress(scraper_id, items_scraped=items_count)
            self.items_today += items_count

            # Wait for completion
            proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(f"Spider exited with code {proc.returncode}")

            logger.info(f"Spider {scraper_id} completed: {items_count} items")

        except Exception as e:
            logger.error(f"Spider {scraper_id} error: {e}")
            raise

    def _get_spider_class(self, scraper_id: str):
        """Get spider class for a scraper ID."""
        try:
            from .spiders import (
                AO3Spider, NiftySpider, LiteroticaSpider, DarkPsychSpider,
                FListSpider, BlueMoonSpider, WWDSpider, VMagSpider, WMagSpider,
                GQSpider, EsquireSpider, TheCutSpider,
                RedditRoleplaySpider, AO3RoleplaySpider,
                CalCareersSpider, ResumeSpider, CoverLetterSpider, SOQExamplesSpider,
                BiasRatingsSpider, RSSNewsSpider, FullArticleSpider,
            )

            spider_map = {
                "ao3": AO3Spider,
                "nifty": NiftySpider,
                "literotica": LiteroticaSpider,
                "dark_psych": DarkPsychSpider,
                "flist": FListSpider,
                "bluemoon": BlueMoonSpider,
                "wwd": WWDSpider,
                "vmag": VMagSpider,
                "wmag": WMagSpider,
                "gq_esquire": GQSpider,
                "thecut": TheCutSpider,
                "reddit_rp": RedditRoleplaySpider,
                "calcareers": CalCareersSpider,
                "resumes": ResumeSpider,
                "coverletters": CoverLetterSpider,
                "soq": SOQExamplesSpider,
                "bias_ratings": BiasRatingsSpider,
                "news": RSSNewsSpider,
                "articles": FullArticleSpider,
            }

            return spider_map.get(scraper_id)
        except ImportError as e:
            logger.warning(f"Could not import spiders: {e}")
            return None

    # =========================================================================
    # HTTP Status Server
    # =========================================================================

    def _start_http_server(self):
        """Start HTTP server for status API."""
        daemon = self

        class StatusHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logging

            def do_GET(self):
                if self.path == "/status":
                    self.send_json(self._get_full_status())
                elif self.path == "/queue":
                    self.send_json({"queue": list(daemon.queue)})
                elif self.path.startswith("/progress/"):
                    scraper_id = self.path.split("/")[-1]
                    progress = daemon.get_progress(scraper_id)
                    if progress:
                        self.send_json(progress.to_dict())
                    else:
                        self.send_error(404, "Not found")
                elif self.path == "/add-all":
                    daemon.add_all_enabled()
                    self.send_json({"success": True, "queue": list(daemon.queue)})
                else:
                    self.send_json({
                        "endpoints": [
                            "GET /status - Full daemon status",
                            "GET /queue - Current queue",
                            "GET /progress/<id> - Progress for specific scraper",
                            "GET /add-all - Add all enabled scrapers to queue",
                            "POST /add - Add scraper to queue (JSON: {scraper_id})",
                            "POST /remove - Remove from queue (JSON: {scraper_id})",
                            "POST /stop - Stop daemon",
                        ]
                    })

            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')

                try:
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    data = {}

                if self.path == "/add":
                    scraper_id = data.get("scraper_id")
                    if scraper_id:
                        success = daemon.add_to_queue(scraper_id)
                        self.send_json({"success": success, "queue": list(daemon.queue)})
                    else:
                        self.send_error(400, "Missing scraper_id")
                elif self.path == "/remove":
                    scraper_id = data.get("scraper_id")
                    if scraper_id:
                        success = daemon.remove_from_queue(scraper_id)
                        self.send_json({"success": success, "queue": list(daemon.queue)})
                    else:
                        self.send_error(400, "Missing scraper_id")
                elif self.path == "/stop":
                    daemon.running = False
                    self.send_json({"success": True, "message": "Daemon stopping"})
                else:
                    self.send_error(404, "Not found")

            def _get_full_status(self) -> dict:
                from scraper_system.config.settings import MAX_CONCURRENT_SPIDERS

                status = daemon.get_status()

                # Add progress for all scrapers
                progress = {}
                active_scrapers = []
                for scraper_id, p in daemon.progress.items():
                    progress[scraper_id] = {
                        "state": p.state.value,
                        "message": p.status_message,
                        "items": p.items_scraped,
                        "bytes": p.bytes_downloaded,
                    }
                    if p.state == ScraperState.RUNNING:
                        active_scrapers.append({
                            "id": scraper_id,
                            "status": p.status_message,
                            "items": p.items_scraped,
                        })

                return {
                    "running": status.running,
                    "concurrent_limit": MAX_CONCURRENT_SPIDERS,
                    "active_count": len(active_scrapers),
                    "active_scrapers": active_scrapers,
                    "current": status.current_scraper,  # Comma-separated list of active
                    "queue": status.queue,
                    "queue_length": len(status.queue),
                    "resources": {
                        "state": status.resource_state,
                        "available_ram_gb": round(status.available_ram_gb, 2),
                        "cpu_percent": round(status.cpu_percent, 1),
                    },
                    "today": {
                        "items": status.total_items_today,
                        "bytes": status.total_bytes_today,
                        "mb": round(status.total_bytes_today / (1024 * 1024), 2),
                    },
                    "uptime_seconds": status.uptime_seconds,
                    "progress": progress,
                }

            def send_json(self, data: dict, status: int = 200):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode())

        server = HTTPServer(("0.0.0.0", self.status_port), StatusHandler)
        logger.info(f"Status server running on http://localhost:{self.status_port}")

        while self.running:
            server.handle_request()

    # =========================================================================
    # Scheduler Thread
    # =========================================================================

    def _scheduler_loop(self):
        """Check schedules and add scrapers to queue when due."""
        from .config.settings import SCRAPER_SCHEDULES

        # Track last run times
        last_check = {}

        while self.running:
            now = datetime.now()

            for scraper_id, cron_expr in SCRAPER_SCHEDULES.items():
                # Simple cron parsing (hour and day of week)
                # Format: "0 2 * * *" = 2 AM daily
                try:
                    parts = cron_expr.split()
                    if len(parts) >= 2:
                        minute = int(parts[0])
                        hour = int(parts[1])

                        # Check if it's time to run
                        if now.hour == hour and now.minute == minute:
                            # Avoid adding multiple times in same minute
                            last_key = f"{scraper_id}_{now.date()}_{hour}_{minute}"
                            if last_key not in last_check:
                                last_check[last_key] = True
                                if scraper_id not in self.queue:
                                    logger.info(f"Scheduled run: {scraper_id}")
                                    self.add_to_queue(scraper_id)
                except Exception as e:
                    logger.warning(f"Invalid cron for {scraper_id}: {e}")

            time.sleep(30)  # Check every 30 seconds

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def start(self):
        """Start the daemon."""
        logger.info("Starting SAM Scraper Daemon")

        # Handle signals
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Start threads
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._http_thread = threading.Thread(target=self._start_http_server, daemon=True)
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)

        self._worker_thread.start()
        self._http_thread.start()
        self._scheduler_thread.start()

        print(f"\n{'=' * 60}")
        print("SAM SCRAPER DAEMON")
        print(f"{'=' * 60}")
        print(f"Status API: http://localhost:{self.status_port}/status")
        print(f"Add all:    http://localhost:{self.status_port}/add-all")
        print(f"Queue:      http://localhost:{self.status_port}/queue")
        print(f"{'=' * 60}")
        print("\nPress Ctrl+C to stop\n")

        # Wait for threads
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self):
        """Stop the daemon gracefully."""
        logger.info("Stopping daemon...")
        self.running = False
        self._save_state()
        logger.info("Daemon stopped")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Scraper Daemon")
    parser.add_argument("--port", type=int, default=8089, help="Status API port")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--add", metavar="SCRAPER", help="Add scraper to queue")
    parser.add_argument("--add-all", action="store_true", help="Add all enabled scrapers")

    args = parser.parse_args()

    # Quick commands that don't start daemon
    if args.status:
        import urllib.request
        try:
            url = f"http://localhost:{args.port}/status"
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read())
                print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Daemon not running or not reachable: {e}")
        return

    if args.add:
        import urllib.request
        try:
            url = f"http://localhost:{args.port}/add"
            data = json.dumps({"scraper_id": args.add}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as response:
                print(json.loads(response.read()))
        except Exception as e:
            print(f"Could not add to queue: {e}")
        return

    if args.add_all:
        import urllib.request
        try:
            url = f"http://localhost:{args.port}/add-all"
            with urllib.request.urlopen(url, timeout=2) as response:
                print(json.loads(response.read()))
        except Exception as e:
            print(f"Could not add all: {e}")
        return

    # Start daemon
    daemon = ScraperDaemon(status_port=args.port)
    daemon.start()


if __name__ == "__main__":
    main()
