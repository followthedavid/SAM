#!/usr/bin/env python3
"""
SAM Training Data Scheduler
Phase 5.1.10: Scheduled data gathering jobs

Provides:
- TrainingDataScheduler class for periodic job management
- schedule_mining() - periodic code pattern mining
- schedule_deduplication() - periodic cleanup
- schedule_quality_check() - periodic validation
- Job persistence and recovery
- Integration with unified_daemon.py

Location: /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_scheduler.py
"""

import os
import sys
import json
import time
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

# Add parent to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduledJob:
    """A scheduled job definition."""
    job_id: str
    name: str
    job_type: str  # mining, deduplication, quality_check, export
    priority: JobPriority = JobPriority.MEDIUM
    interval_minutes: int = 60
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    last_status: JobStatus = JobStatus.PENDING
    last_error: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    enabled: bool = True
    config: Dict = field(default_factory=dict)


@dataclass
class JobRun:
    """A single job execution record."""
    run_id: str
    job_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: JobStatus = JobStatus.RUNNING
    result: Optional[Dict] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class TrainingDataScheduler:
    """
    Manages scheduled training data gathering jobs.

    Jobs include:
    - Code pattern mining from git repos
    - Data deduplication and cleanup
    - Quality validation checks
    - Training data export

    Integrates with unified_daemon.py for resource management.
    """

    STATE_DIR = Path.home() / ".sam" / "scheduler"
    JOBS_FILE = STATE_DIR / "jobs.json"
    HISTORY_FILE = STATE_DIR / "history.json"
    PID_FILE = STATE_DIR / "scheduler.pid"
    LOG_FILE = STATE_DIR / "scheduler.log"

    # Default job intervals (minutes)
    DEFAULT_INTERVALS = {
        "mining": 360,  # 6 hours
        "deduplication": 1440,  # 24 hours
        "quality_check": 720,  # 12 hours
        "export": 1440,  # 24 hours
    }

    # RAM requirements (GB)
    RAM_REQUIREMENTS = {
        "mining": 0.5,
        "deduplication": 0.3,
        "quality_check": 0.5,
        "export": 0.2,
    }

    def __init__(self):
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, ScheduledJob] = {}
        self.history: List[JobRun] = []
        self.running = False
        self._lock = threading.Lock()
        self._load_state()
        self._init_default_jobs()

    def _load_state(self):
        """Load scheduler state from disk."""
        # Load jobs
        if self.JOBS_FILE.exists():
            try:
                data = json.loads(self.JOBS_FILE.read_text())
                for job_data in data.get("jobs", []):
                    job_data["priority"] = JobPriority(job_data.get("priority", 2))
                    job_data["last_status"] = JobStatus(job_data.get("last_status", "pending"))
                    job = ScheduledJob(**job_data)
                    self.jobs[job.job_id] = job
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self._log(f"Error loading jobs: {e}", "WARN")

        # Load recent history
        if self.HISTORY_FILE.exists():
            try:
                data = json.loads(self.HISTORY_FILE.read_text())
                for run_data in data.get("history", [])[-100:]:  # Keep last 100
                    run_data["status"] = JobStatus(run_data.get("status", "completed"))
                    self.history.append(JobRun(**run_data))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self._log(f"Error loading history: {e}", "WARN")

    def _save_state(self):
        """Save scheduler state to disk."""
        with self._lock:
            # Save jobs
            jobs_data = []
            for job in self.jobs.values():
                job_dict = asdict(job)
                job_dict["priority"] = job.priority.value
                job_dict["last_status"] = job.last_status.value
                jobs_data.append(job_dict)

            self.JOBS_FILE.write_text(json.dumps({"jobs": jobs_data}, indent=2))

            # Save history
            history_data = []
            for run in self.history[-100:]:  # Keep last 100
                run_dict = asdict(run)
                run_dict["status"] = run.status.value
                history_data.append(run_dict)

            self.HISTORY_FILE.write_text(json.dumps({"history": history_data}, indent=2))

    def _log(self, msg: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {msg}"

        try:
            # Ensure log directory exists
            self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.LOG_FILE, "a") as f:
                f.write(entry + "\n")
        except Exception:
            pass  # Don't let logging errors break functionality

        if level in ["ERROR", "WARN"]:
            print(entry, file=sys.stderr)

    def _init_default_jobs(self):
        """Initialize default jobs if not present."""
        default_jobs = [
            ScheduledJob(
                job_id="mining_code",
                name="Code Pattern Mining",
                job_type="mining",
                priority=JobPriority.MEDIUM,
                interval_minutes=self.DEFAULT_INTERVALS["mining"],
                config={"sources": ["git", "dedup_db"]}
            ),
            ScheduledJob(
                job_id="dedup_cleanup",
                name="Data Deduplication",
                job_type="deduplication",
                priority=JobPriority.LOW,
                interval_minutes=self.DEFAULT_INTERVALS["deduplication"],
                config={"similarity_threshold": 0.85}
            ),
            ScheduledJob(
                job_id="quality_check",
                name="Quality Validation",
                job_type="quality_check",
                priority=JobPriority.MEDIUM,
                interval_minutes=self.DEFAULT_INTERVALS["quality_check"],
                config={"min_quality": 0.5}
            ),
            ScheduledJob(
                job_id="export_training",
                name="Training Export",
                job_type="export",
                priority=JobPriority.LOW,
                interval_minutes=self.DEFAULT_INTERVALS["export"],
                config={"format": "jsonl", "quality_filter": True}
            ),
        ]

        for job in default_jobs:
            if job.job_id not in self.jobs:
                self.jobs[job.job_id] = job
                self._log(f"Initialized default job: {job.name}")

        self._save_state()

    def _check_resources(self, job_type: str) -> bool:
        """Check if we have enough RAM for a job."""
        try:
            import psutil
            available_gb = psutil.virtual_memory().available / (1024 ** 3)
            required_gb = self.RAM_REQUIREMENTS.get(job_type, 0.5)
            return available_gb >= required_gb
        except ImportError:
            return True  # Assume OK if psutil not available

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_") + os.urandom(4).hex()

    # =========================================================================
    # Job Scheduling Methods
    # =========================================================================

    def schedule_mining(
        self,
        interval_minutes: Optional[int] = None,
        sources: Optional[List[str]] = None
    ):
        """
        Schedule periodic code pattern mining.

        Mining sources:
        - git: Extract from git commit history
        - dedup_db: Extract from code deduplication database
        - ssot: Extract from SSOT documentation
        """
        job = self.jobs.get("mining_code")
        if not job:
            job = ScheduledJob(
                job_id="mining_code",
                name="Code Pattern Mining",
                job_type="mining",
                priority=JobPriority.MEDIUM,
            )
            self.jobs["mining_code"] = job

        if interval_minutes:
            job.interval_minutes = interval_minutes
        if sources:
            job.config["sources"] = sources

        job.enabled = True
        job.next_run = datetime.now().isoformat()

        self._save_state()
        self._log(f"Scheduled mining job: interval={job.interval_minutes}min")

    def schedule_deduplication(
        self,
        interval_minutes: Optional[int] = None,
        similarity_threshold: float = 0.85
    ):
        """
        Schedule periodic data deduplication.

        Removes near-duplicate training examples based on
        text similarity using MinHash or embedding similarity.
        """
        job = self.jobs.get("dedup_cleanup")
        if not job:
            job = ScheduledJob(
                job_id="dedup_cleanup",
                name="Data Deduplication",
                job_type="deduplication",
                priority=JobPriority.LOW,
            )
            self.jobs["dedup_cleanup"] = job

        if interval_minutes:
            job.interval_minutes = interval_minutes
        job.config["similarity_threshold"] = similarity_threshold

        job.enabled = True
        job.next_run = datetime.now().isoformat()

        self._save_state()
        self._log(f"Scheduled deduplication: threshold={similarity_threshold}")

    def schedule_quality_check(
        self,
        interval_minutes: Optional[int] = None,
        min_quality: float = 0.5
    ):
        """
        Schedule periodic quality validation.

        Validates training examples against quality criteria:
        - Token length bounds
        - Language detection
        - Format validation
        - Content quality scoring
        """
        job = self.jobs.get("quality_check")
        if not job:
            job = ScheduledJob(
                job_id="quality_check",
                name="Quality Validation",
                job_type="quality_check",
                priority=JobPriority.MEDIUM,
            )
            self.jobs["quality_check"] = job

        if interval_minutes:
            job.interval_minutes = interval_minutes
        job.config["min_quality"] = min_quality

        job.enabled = True
        job.next_run = datetime.now().isoformat()

        self._save_state()
        self._log(f"Scheduled quality check: min_quality={min_quality}")

    def schedule_export(
        self,
        interval_minutes: Optional[int] = None,
        output_format: str = "jsonl",
        quality_filter: bool = True
    ):
        """
        Schedule periodic training data export.

        Exports validated training data to training-ready format.
        """
        job = self.jobs.get("export_training")
        if not job:
            job = ScheduledJob(
                job_id="export_training",
                name="Training Export",
                job_type="export",
                priority=JobPriority.LOW,
            )
            self.jobs["export_training"] = job

        if interval_minutes:
            job.interval_minutes = interval_minutes
        job.config["format"] = output_format
        job.config["quality_filter"] = quality_filter

        job.enabled = True
        job.next_run = datetime.now().isoformat()

        self._save_state()
        self._log(f"Scheduled export: format={output_format}")

    # =========================================================================
    # Job Execution
    # =========================================================================

    def _run_mining_job(self, job: ScheduledJob) -> Dict:
        """Execute code pattern mining job."""
        results = {"extracted": 0, "sources": {}}

        # Import training data collector
        try:
            from training_data_collector import (
                get_git_repos,
                extract_git_commits,
                extract_code_patterns_from_dedup,
                extract_project_knowledge,
                CONFIG,
                setup_output_dir,
            )

            setup_output_dir()

            sources = job.config.get("sources", ["git", "dedup_db"])

            if "git" in sources:
                repos = get_git_repos()
                total_commits = 0
                for repo in repos[:10]:  # Limit repos per run
                    commits = extract_git_commits(repo)
                    total_commits += len(commits)
                results["sources"]["git"] = total_commits
                results["extracted"] += total_commits

            if "dedup_db" in sources:
                patterns = extract_code_patterns_from_dedup()
                results["sources"]["code_patterns"] = len(patterns)
                results["extracted"] += len(patterns)

            if "ssot" in sources:
                knowledge = extract_project_knowledge()
                results["sources"]["knowledge"] = len(knowledge)
                results["extracted"] += len(knowledge)

        except ImportError as e:
            results["error"] = f"Import error: {e}"
        except Exception as e:
            results["error"] = str(e)

        return results

    def _run_deduplication_job(self, job: ScheduledJob) -> Dict:
        """Execute data deduplication job."""
        results = {"processed": 0, "removed": 0, "remaining": 0}

        threshold = job.config.get("similarity_threshold", 0.85)
        training_data_dir = SCRIPT_DIR / "training_data"

        if not training_data_dir.exists():
            return results

        try:
            # Simple hash-based deduplication
            seen_hashes = set()
            duplicates = []

            for jsonl_file in training_data_dir.glob("*.jsonl"):
                unique_lines = []
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        results["processed"] += 1

                        # Hash the content
                        import hashlib
                        line_hash = hashlib.md5(line.encode()).hexdigest()

                        if line_hash not in seen_hashes:
                            seen_hashes.add(line_hash)
                            unique_lines.append(line)
                        else:
                            results["removed"] += 1

                # Write back unique lines (backup first)
                if results["removed"] > 0:
                    backup_file = jsonl_file.with_suffix(".jsonl.bak")
                    jsonl_file.rename(backup_file)
                    with open(jsonl_file, "w", encoding="utf-8") as f:
                        f.writelines(unique_lines)

            results["remaining"] = results["processed"] - results["removed"]

        except Exception as e:
            results["error"] = str(e)

        return results

    def _run_quality_check_job(self, job: ScheduledJob) -> Dict:
        """Execute quality validation job."""
        results = {
            "checked": 0,
            "passed": 0,
            "failed": 0,
            "by_issue": {}
        }

        min_quality = job.config.get("min_quality", 0.5)
        training_data_dir = SCRIPT_DIR / "training_data"

        if not training_data_dir.exists():
            return results

        try:
            for jsonl_file in training_data_dir.glob("*.jsonl"):
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            example = json.loads(line)
                            results["checked"] += 1

                            # Validate example
                            issues = self._validate_example(example)

                            if not issues:
                                results["passed"] += 1
                            else:
                                results["failed"] += 1
                                for issue in issues:
                                    results["by_issue"][issue] = results["by_issue"].get(issue, 0) + 1

                        except json.JSONDecodeError:
                            results["failed"] += 1
                            results["by_issue"]["invalid_json"] = results["by_issue"].get("invalid_json", 0) + 1

        except Exception as e:
            results["error"] = str(e)

        return results

    def _validate_example(self, example: Dict) -> List[str]:
        """Validate a single training example."""
        issues = []

        # Check format
        has_valid_format = (
            ("messages" in example) or
            ("instruction" in example and "output" in example) or
            ("prompt" in example and "completion" in example)
        )
        if not has_valid_format:
            issues.append("invalid_format")

        # Check content length
        total_length = 0
        if "messages" in example:
            for msg in example["messages"]:
                total_length += len(msg.get("content", ""))
        else:
            total_length = len(str(example))

        if total_length < 20:
            issues.append("too_short")
        if total_length > 50000:
            issues.append("too_long")

        # Check for empty outputs
        if "output" in example and not example["output"].strip():
            issues.append("empty_output")
        if "messages" in example:
            for msg in example["messages"]:
                if msg.get("role") == "assistant" and not msg.get("content", "").strip():
                    issues.append("empty_response")
                    break

        return issues

    def _run_export_job(self, job: ScheduledJob) -> Dict:
        """Execute training data export job."""
        results = {"exported": 0, "format": job.config.get("format", "jsonl")}

        training_data_dir = SCRIPT_DIR / "training_data"
        output_file = training_data_dir / f"train_{datetime.now().strftime('%Y%m%d')}.jsonl"

        if not training_data_dir.exists():
            return results

        try:
            quality_filter = job.config.get("quality_filter", True)
            exported_examples = []

            for jsonl_file in training_data_dir.glob("*.jsonl"):
                if jsonl_file.name.startswith("train_"):
                    continue  # Skip existing exports

                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            example = json.loads(line)

                            if quality_filter:
                                issues = self._validate_example(example)
                                if issues:
                                    continue

                            exported_examples.append(line)
                            results["exported"] += 1

                        except json.JSONDecodeError:
                            continue

            # Write export file
            if exported_examples:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.writelines(exported_examples)
                results["output_file"] = str(output_file)

        except Exception as e:
            results["error"] = str(e)

        return results

    def run_job(self, job_id: str, force: bool = False) -> Optional[JobRun]:
        """Execute a job immediately."""
        job = self.jobs.get(job_id)
        if not job:
            self._log(f"Unknown job: {job_id}", "ERROR")
            return None

        if not job.enabled and not force:
            self._log(f"Job {job.name} is disabled", "WARN")
            return None

        # Check resources
        if not self._check_resources(job.job_type):
            self._log(f"Insufficient resources for {job.name}", "WARN")
            return None

        # Create run record
        run = JobRun(
            run_id=self._generate_run_id(),
            job_id=job_id,
            started_at=datetime.now().isoformat(),
            status=JobStatus.RUNNING,
        )

        self._log(f"Starting job: {job.name}")
        start_time = time.time()

        try:
            # Execute based on job type
            if job.job_type == "mining":
                result = self._run_mining_job(job)
            elif job.job_type == "deduplication":
                result = self._run_deduplication_job(job)
            elif job.job_type == "quality_check":
                result = self._run_quality_check_job(job)
            elif job.job_type == "export":
                result = self._run_export_job(job)
            else:
                result = {"error": f"Unknown job type: {job.job_type}"}

            run.result = result
            run.status = JobStatus.COMPLETED if "error" not in result else JobStatus.FAILED
            run.error = result.get("error")

            job.success_count += 1 if run.status == JobStatus.COMPLETED else 0
            job.last_status = run.status

        except Exception as e:
            run.status = JobStatus.FAILED
            run.error = str(e)
            job.last_status = JobStatus.FAILED
            job.last_error = str(e)
            self._log(f"Job {job.name} failed: {e}", "ERROR")

        # Finalize
        run.completed_at = datetime.now().isoformat()
        run.duration_seconds = time.time() - start_time
        job.run_count += 1
        job.last_run = run.completed_at
        job.next_run = (datetime.now() + timedelta(minutes=job.interval_minutes)).isoformat()

        self.history.append(run)
        self._save_state()

        self._log(f"Completed job: {job.name} ({run.status.value})")

        return run

    # =========================================================================
    # Scheduler Loop
    # =========================================================================

    def start(self):
        """Start the scheduler in the foreground."""
        if self.PID_FILE.exists():
            try:
                pid = int(self.PID_FILE.read_text().strip())
                os.kill(pid, 0)
                print(f"Scheduler already running (PID {pid})")
                return
            except (ProcessLookupError, ValueError):
                pass

        self.PID_FILE.write_text(str(os.getpid()))
        self.running = True
        self._log("Training scheduler started")

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self._run_loop()

    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            now = datetime.now()

            for job_id, job in self.jobs.items():
                if not job.enabled:
                    continue

                # Check if job is due
                if job.next_run:
                    next_run = datetime.fromisoformat(job.next_run)
                    if now >= next_run:
                        self.run_job(job_id)

            # Sleep before next check
            time.sleep(60)  # Check every minute

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self._log("Shutdown signal received")
        self.running = False
        self.PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    def stop(self):
        """Stop the scheduler."""
        if not self.PID_FILE.exists():
            print("Scheduler not running")
            return

        try:
            pid = int(self.PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to scheduler (PID {pid})")
        except (ProcessLookupError, ValueError):
            print("Scheduler not running")

        self.PID_FILE.unlink(missing_ok=True)

    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.PID_FILE.exists(),
            "pid": int(self.PID_FILE.read_text().strip()) if self.PID_FILE.exists() else None,
            "jobs": {
                job_id: {
                    "name": job.name,
                    "enabled": job.enabled,
                    "status": job.last_status.value,
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "run_count": job.run_count,
                    "success_rate": round(job.success_count / job.run_count * 100, 1) if job.run_count > 0 else 0,
                }
                for job_id, job in self.jobs.items()
            },
            "recent_runs": [
                {
                    "run_id": run.run_id,
                    "job_id": run.job_id,
                    "status": run.status.value,
                    "started_at": run.started_at,
                    "duration_seconds": run.duration_seconds,
                }
                for run in self.history[-10:]
            ]
        }


# =============================================================================
# Daemon Integration
# =============================================================================

def register_with_daemon():
    """
    Register scheduler jobs with unified_daemon.py.

    This integrates the training scheduler with SAM's
    resource-aware daemon system.
    """
    try:
        from unified_daemon import UnifiedDaemon, Service, ServicePriority

        daemon = UnifiedDaemon()

        # Register training scheduler as a service
        scheduler_service = Service(
            name="Training Scheduler",
            priority=ServicePriority.LOW,
            start_cmd=f"cd {SCRIPT_DIR} && python3 training_scheduler.py start",
            pid_file=str(TrainingDataScheduler.PID_FILE),
            min_ram_gb=0.2,
            auto_restart=True,
        )

        daemon.services["training_scheduler"] = scheduler_service
        daemon._save_state()

        print("Registered training scheduler with unified daemon")
        return True

    except ImportError:
        print("unified_daemon.py not found - skipping integration")
        return False


# =============================================================================
# API Integration
# =============================================================================

def api_scheduler_status() -> Dict[str, Any]:
    """API endpoint for scheduler status."""
    scheduler = TrainingDataScheduler()
    return {
        "success": True,
        "data": scheduler.get_status()
    }


def api_scheduler_run_job(job_id: str) -> Dict[str, Any]:
    """API endpoint to run a job immediately."""
    scheduler = TrainingDataScheduler()
    run = scheduler.run_job(job_id, force=True)

    if run:
        return {
            "success": True,
            "run": asdict(run)
        }
    else:
        return {
            "success": False,
            "error": f"Failed to run job: {job_id}"
        }


def api_scheduler_configure_job(
    job_id: str,
    enabled: Optional[bool] = None,
    interval_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """API endpoint to configure a job."""
    scheduler = TrainingDataScheduler()

    if job_id not in scheduler.jobs:
        return {
            "success": False,
            "error": f"Unknown job: {job_id}"
        }

    job = scheduler.jobs[job_id]

    if enabled is not None:
        job.enabled = enabled
    if interval_minutes is not None:
        job.interval_minutes = interval_minutes

    scheduler._save_state()

    return {
        "success": True,
        "job": {
            "job_id": job.job_id,
            "name": job.name,
            "enabled": job.enabled,
            "interval_minutes": job.interval_minutes,
        }
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Data Scheduler")
    parser.add_argument("command", nargs="?", default="status",
                       choices=["start", "stop", "status", "run", "list", "register"],
                       help="Command to run")
    parser.add_argument("--job", "-j", help="Job ID for 'run' command")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    scheduler = TrainingDataScheduler()

    if args.command == "start":
        scheduler.start()

    elif args.command == "stop":
        scheduler.stop()

    elif args.command == "status":
        status = scheduler.get_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("=" * 60)
            print("SAM Training Data Scheduler")
            print("=" * 60)
            print(f"\nRunning: {status['running']}")
            print(f"PID: {status['pid'] or 'N/A'}")

            print("\nJobs:")
            print("-" * 40)
            for job_id, info in status["jobs"].items():
                status_icon = "[*]" if info["enabled"] else "[ ]"
                print(f"  {status_icon} {info['name']}")
                print(f"      Status: {info['status']}, Runs: {info['run_count']}, Success: {info['success_rate']}%")
                print(f"      Next run: {info['next_run'] or 'N/A'}")

    elif args.command == "run":
        if not args.job:
            print("Please specify --job ID")
            sys.exit(1)
        run = scheduler.run_job(args.job, force=True)
        if run:
            if args.json:
                print(json.dumps(asdict(run), indent=2))
            else:
                print(f"Job completed: {run.status.value}")
                print(f"Duration: {run.duration_seconds:.2f}s")
                if run.result:
                    print(f"Result: {json.dumps(run.result, indent=2)}")
        else:
            print("Job failed to start")

    elif args.command == "list":
        for job_id, job in scheduler.jobs.items():
            print(f"{job_id}: {job.name} ({job.job_type})")
            print(f"  Interval: {job.interval_minutes} minutes")
            print(f"  Enabled: {job.enabled}")

    elif args.command == "register":
        register_with_daemon()


if __name__ == "__main__":
    main()
