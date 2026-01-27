"""
SAM Scraper System - Celery Runner (Backup)

Implements the TaskRunner interface using Celery for orchestration.
This is the BACKUP runner - use if Prefect ever becomes unavailable.

15+ years proven, massive community, will exist forever.

To activate: Change RUNNER = "celery" in config/settings.py
Then: pip install celery redis flower
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from functools import wraps

from ..core.task_runner import (
    TaskRunner,
    TaskStatus,
    TaskResult,
    ScheduleConfig,
    get_registered_tasks,
)

logger = logging.getLogger(__name__)

# Celery imports
try:
    from celery import Celery, Task
    from celery.schedules import crontab
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not installed. Run: pip install celery redis")


def parse_cron(cron_str: str) -> dict:
    """Parse cron string to Celery crontab format."""
    parts = cron_str.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron string: {cron_str}")

    minute, hour, day_of_month, month, day_of_week = parts

    return {
        "minute": minute,
        "hour": hour,
        "day_of_month": day_of_month,
        "month_of_year": month,
        "day_of_week": day_of_week,
    }


class CeleryRunner(TaskRunner):
    """
    Celery implementation of TaskRunner.

    This is the BACKUP/SWAP-IN runner if Prefect becomes unavailable.

    Requirements:
        pip install celery redis flower

    Services needed:
        - Redis server (brew services start redis)
        - Celery worker (celery -A runners.celery_runner worker)
        - Celery beat for scheduling (celery -A runners.celery_runner beat)
        - Flower for monitoring (celery -A runners.celery_runner flower)

    Features:
        - 15+ years battle-tested
        - Massive community
        - Will exist as long as Python exists
    """

    def __init__(self):
        if not CELERY_AVAILABLE:
            raise RuntimeError("Celery not installed. Run: pip install celery redis")

        from ..config.settings import REDIS_URL

        # Create Celery app
        self.app = Celery(
            "sam_scraper",
            broker=REDIS_URL,
            backend=REDIS_URL,
        )

        # Configure Celery
        self.app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,  # One task at a time (8GB Mac)
            beat_schedule={},  # Will be populated by schedule()
        )

        self._tasks: Dict[str, Task] = {}
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._paused = False

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(self) -> None:
        """Initialize Celery connection."""
        logger.info("Initializing Celery runner")

        # Register all @task decorated functions
        for name, info in get_registered_tasks().items():
            self.register_task(name, info["func"], **info.get("options", {}))

        logger.info(f"Registered {len(self._tasks)} tasks with Celery")

    def shutdown(self) -> None:
        """Shutdown Celery runner."""
        logger.info("Shutting down Celery runner")
        self.app.control.shutdown()

    # =========================================================================
    # Task Registration
    # =========================================================================

    def register_task(self, name: str, func: Callable, **options) -> None:
        """Register a function as a Celery task."""
        retries = options.get("retries", 3)
        retry_delay = options.get("retry_delay_seconds", 60)

        @self.app.task(
            name=name,
            bind=True,
            max_retries=retries,
            default_retry_delay=retry_delay,
            acks_late=True,
        )
        @wraps(func)
        def celery_task(self_task, *args, **kwargs):
            # Check resource governor before running
            from ..core.resource_governor import get_governor
            governor = get_governor()

            if not governor.can_start_scraper():
                status = governor.get_status()
                logger.warning(f"Resources unavailable: {status.reason}")

                # Retry later
                raise self_task.retry(
                    countdown=300,  # 5 minutes
                    exc=Exception(f"Resources unavailable: {status.reason}"),
                )

            return func(*args, **kwargs)

        self._tasks[name] = celery_task
        logger.debug(f"Registered task with Celery: {name}")

    # =========================================================================
    # Task Execution
    # =========================================================================

    def run_now(self, task_name: str, **kwargs) -> TaskResult:
        """Run a task immediately and wait for result."""
        if task_name not in self._tasks:
            raise ValueError(f"Unknown task: {task_name}")

        if self._paused:
            return TaskResult(
                task_id="",
                task_name=task_name,
                status=TaskStatus.PAUSED,
                error="Runner is paused",
            )

        task = self._tasks[task_name]
        started_at = datetime.now()

        try:
            # Run synchronously (blocking)
            result = task.apply(kwargs=kwargs)
            return TaskResult(
                task_id=result.id,
                task_name=task_name,
                status=TaskStatus.COMPLETED if result.successful() else TaskStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                result=result.get() if result.successful() else None,
                error=str(result.result) if not result.successful() else None,
            )
        except Exception as e:
            logger.error(f"Task {task_name} failed: {e}")
            return TaskResult(
                task_id="",
                task_name=task_name,
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )

    def run_async(self, task_name: str, **kwargs) -> str:
        """Queue a task for async execution."""
        if task_name not in self._tasks:
            raise ValueError(f"Unknown task: {task_name}")

        if self._paused:
            raise RuntimeError("Runner is paused")

        task = self._tasks[task_name]
        result = task.apply_async(kwargs=kwargs)
        return result.id

    def run_chain(self, tasks: List[tuple]) -> str:
        """Run a chain of tasks in sequence."""
        from celery import chain

        task_signatures = []
        for task_name, kwargs in tasks:
            if task_name not in self._tasks:
                raise ValueError(f"Unknown task in chain: {task_name}")
            task_signatures.append(self._tasks[task_name].s(**kwargs))

        chain_result = chain(*task_signatures).apply_async()
        return chain_result.id

    # =========================================================================
    # Scheduling
    # =========================================================================

    def schedule(self, config: ScheduleConfig) -> None:
        """Schedule a task with cron expression."""
        if config.task_name not in self._tasks:
            raise ValueError(f"Unknown task: {config.task_name}")

        if config.enabled:
            cron_parts = parse_cron(config.cron)
            self.app.conf.beat_schedule[config.task_name] = {
                "task": config.task_name,
                "schedule": crontab(**cron_parts),
                "kwargs": config.kwargs or {},
            }
        else:
            if config.task_name in self.app.conf.beat_schedule:
                del self.app.conf.beat_schedule[config.task_name]

        self._schedules[config.task_name] = config
        logger.info(f"Scheduled {config.task_name} with cron: {config.cron}")

    def unschedule(self, task_name: str) -> None:
        """Remove a scheduled task."""
        if task_name in self.app.conf.beat_schedule:
            del self.app.conf.beat_schedule[task_name]

        if task_name in self._schedules:
            del self._schedules[task_name]

        logger.info(f"Unscheduled {task_name}")

    def get_schedules(self) -> List[ScheduleConfig]:
        """Get all active schedules."""
        return list(self._schedules.values())

    # =========================================================================
    # Task Control
    # =========================================================================

    def pause(self, task_name: str) -> None:
        """Pause a specific task's schedule."""
        if task_name in self._schedules:
            self._schedules[task_name].enabled = False
            self.unschedule(task_name)
        logger.info(f"Paused {task_name}")

    def resume(self, task_name: str) -> None:
        """Resume a specific task's schedule."""
        if task_name in self._schedules:
            config = self._schedules[task_name]
            config.enabled = True
            self.schedule(config)
        logger.info(f"Resumed {task_name}")

    def cancel(self, task_id: str) -> None:
        """Cancel a running task."""
        self.app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled task {task_id}")

    def pause_all(self) -> None:
        """Pause all tasks."""
        self._paused = True
        # Pause all workers
        self.app.control.broadcast("pool_pause")
        logger.info("All tasks paused")

    def resume_all(self) -> None:
        """Resume all tasks."""
        self._paused = False
        self.app.control.broadcast("pool_resume")
        logger.info("All tasks resumed")

    # =========================================================================
    # Status & Monitoring
    # =========================================================================

    def get_status(self, task_id: str) -> TaskResult:
        """Get status of a specific task execution."""
        result = AsyncResult(task_id, app=self.app)

        state_map = {
            "PENDING": TaskStatus.PENDING,
            "STARTED": TaskStatus.RUNNING,
            "SUCCESS": TaskStatus.COMPLETED,
            "FAILURE": TaskStatus.FAILED,
            "REVOKED": TaskStatus.CANCELLED,
        }

        return TaskResult(
            task_id=task_id,
            task_name=result.name or "unknown",
            status=state_map.get(result.state, TaskStatus.PENDING),
            result=result.result if result.successful() else None,
            error=str(result.result) if result.failed() else None,
        )

    def get_running_tasks(self) -> List[TaskResult]:
        """Get all currently running tasks."""
        inspect = self.app.control.inspect()
        active = inspect.active() or {}

        results = []
        for worker, tasks in active.items():
            for task in tasks:
                results.append(TaskResult(
                    task_id=task["id"],
                    task_name=task["name"],
                    status=TaskStatus.RUNNING,
                    started_at=datetime.fromtimestamp(task.get("time_start", 0)),
                ))
        return results

    def get_queued_tasks(self) -> List[TaskResult]:
        """Get all queued tasks."""
        inspect = self.app.control.inspect()
        reserved = inspect.reserved() or {}

        results = []
        for worker, tasks in reserved.items():
            for task in tasks:
                results.append(TaskResult(
                    task_id=task["id"],
                    task_name=task["name"],
                    status=TaskStatus.QUEUED,
                ))
        return results

    def get_history(self, task_name: str = None, limit: int = 100) -> List[TaskResult]:
        """Get task execution history."""
        # Celery doesn't store history by default
        # Would need to implement with a results backend
        logger.warning("History not fully implemented for Celery runner")
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        inspect = self.app.control.inspect()
        stats = inspect.stats() or {}

        total_processed = 0
        total_active = 0

        for worker, worker_stats in stats.items():
            total_processed += worker_stats.get("total", {}).get("tasks.task", 0)
            total_active += len((inspect.active() or {}).get(worker, []))

        return {
            "runner": "celery",
            "registered_tasks": len(self._tasks),
            "active_schedules": len([s for s in self._schedules.values() if s.enabled]),
            "paused": self._paused,
            "total_processed": total_processed,
            "currently_active": total_active,
            "workers": list(stats.keys()),
        }


# =============================================================================
# Celery app instance (for CLI commands)
# =============================================================================

# This allows running: celery -A scraper_system.runners.celery_runner worker
if CELERY_AVAILABLE:
    from ..config.settings import REDIS_URL

    app = Celery(
        "sam_scraper",
        broker=REDIS_URL,
        backend=REDIS_URL,
    )
