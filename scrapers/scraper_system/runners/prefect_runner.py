"""
SAM Scraper System - Prefect Runner

Implements the TaskRunner interface using Prefect 3.x for orchestration.
Modern, Python-native, excellent UI, lighter than Airflow.

To swap to Celery: Change RUNNER = "celery" in config/settings.py
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

# Prefect 3.x imports (installed via: pip install prefect)
try:
    from prefect import flow, task as prefect_task_decorator
    from prefect.states import Completed, Failed, Cancelled, Running, Pending
    PREFECT_AVAILABLE = True
except ImportError:
    PREFECT_AVAILABLE = False
    logger.warning("Prefect not installed. Run: pip install prefect")


class PrefectRunner(TaskRunner):
    """
    Prefect 3.x implementation of TaskRunner.

    Features:
    - Sync/async task execution
    - Built-in UI (prefect server start)
    - Automatic retries
    - Resource checking integration

    Note: Scheduling in Prefect 3.x uses flow.serve() which is a long-running
    process. For scheduled tasks, you'll need to run a separate serve process.
    """

    def __init__(self):
        if not PREFECT_AVAILABLE:
            raise RuntimeError("Prefect not installed. Run: pip install prefect")

        self._tasks: Dict[str, Any] = {}  # Registered prefect tasks
        self._flows: Dict[str, Any] = {}  # Registered prefect flows
        self._schedules: Dict[str, ScheduleConfig] = {}  # Schedule configs
        self._paused = False

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(self) -> None:
        """Initialize Prefect connection."""
        logger.info("Initializing Prefect runner")
        try:
            # Register all @task decorated functions
            for name, info in get_registered_tasks().items():
                self.register_task(name, info["func"], **info.get("options", {}))
            logger.info(f"Registered {len(self._tasks)} tasks with Prefect")
        except Exception as e:
            logger.error(f"Failed to initialize Prefect: {e}")
            raise

    def shutdown(self) -> None:
        """Shutdown Prefect runner."""
        logger.info("Shutting down Prefect runner")

    # =========================================================================
    # Task Registration
    # =========================================================================

    def register_task(self, name: str, func: Callable, **options) -> None:
        """Register a function as a Prefect task."""
        retries = options.get("retries", 3)
        retry_delay = options.get("retry_delay_seconds", 60)

        @prefect_task_decorator(
            name=name,
            retries=retries,
            retry_delay_seconds=retry_delay,
            log_prints=True,
        )
        @wraps(func)
        def wrapped_task(*args, **kwargs):
            # Check resource governor before running
            from ..core.resource_governor import get_governor
            governor = get_governor()

            if not governor.can_start_scraper():
                status = governor.get_status()
                logger.warning(f"Resources unavailable: {status.reason}")
                governor.wait_for_resources(timeout_seconds=3600)  # Wait up to 1 hour

            return func(*args, **kwargs)

        self._tasks[name] = wrapped_task

        # Also create a flow for this task (flows are the top-level execution unit)
        @flow(name=f"{name}_flow", log_prints=True)
        def task_flow(**kwargs):
            return wrapped_task(**kwargs)

        self._flows[name] = task_flow
        logger.debug(f"Registered task with Prefect: {name}")

    # =========================================================================
    # Task Execution
    # =========================================================================

    def run_now(self, task_name: str, **kwargs) -> TaskResult:
        """Run a task immediately and wait for result."""
        if task_name not in self._flows:
            raise ValueError(f"Unknown task: {task_name}")

        if self._paused:
            return TaskResult(
                task_id="",
                task_name=task_name,
                status=TaskStatus.PAUSED,
                error="Runner is paused",
            )

        flow_func = self._flows[task_name]
        started_at = datetime.now()

        try:
            result = flow_func(**kwargs)
            return TaskResult(
                task_id=str(id(result)),
                task_name=task_name,
                status=TaskStatus.COMPLETED,
                started_at=started_at,
                completed_at=datetime.now(),
                result=result,
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
        if task_name not in self._flows:
            raise ValueError(f"Unknown task: {task_name}")

        if self._paused:
            raise RuntimeError("Runner is paused")

        # In Prefect 3.x, async execution requires a deployed flow
        # For now, we run synchronously but in a background thread
        import threading
        import uuid

        task_id = str(uuid.uuid4())

        def run_in_background():
            try:
                self._flows[task_name](**kwargs)
            except Exception as e:
                logger.error(f"Async task {task_name} failed: {e}")

        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()

        return task_id

    def run_chain(self, tasks: List[tuple]) -> str:
        """Run a chain of tasks in sequence."""
        @flow(name="task_chain", log_prints=True)
        def chain_flow():
            results = []
            for task_name, kwargs in tasks:
                if task_name in self._tasks:
                    result = self._tasks[task_name](**kwargs)
                    results.append(result)
                else:
                    raise ValueError(f"Unknown task in chain: {task_name}")
            return results

        import uuid
        chain_id = str(uuid.uuid4())

        # Run the chain
        chain_flow()
        return chain_id

    # =========================================================================
    # Scheduling
    # =========================================================================

    def schedule(self, config: ScheduleConfig) -> None:
        """
        Schedule a task with cron expression.

        Note: In Prefect 3.x, scheduling requires using flow.serve() which
        creates a long-running process. Store the config for reference.
        To actually run scheduled tasks, use:

            flow.serve(name="deployment", cron="0 2 * * *")
        """
        if config.task_name not in self._flows:
            raise ValueError(f"Unknown task: {config.task_name}")

        self._schedules[config.task_name] = config
        logger.info(f"Scheduled {config.task_name} with cron: {config.cron}")
        logger.info("Note: Run `python -m scraper_system serve` to start scheduled tasks")

    def unschedule(self, task_name: str) -> None:
        """Remove a scheduled task."""
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
        logger.info(f"Paused {task_name}")

    def resume(self, task_name: str) -> None:
        """Resume a specific task's schedule."""
        if task_name in self._schedules:
            self._schedules[task_name].enabled = True
        logger.info(f"Resumed {task_name}")

    def cancel(self, task_id: str) -> None:
        """Cancel a running task."""
        logger.warning(f"Cancel not fully implemented for Prefect 3.x sync execution")

    def pause_all(self) -> None:
        """Pause all tasks."""
        self._paused = True
        for task_name in self._schedules:
            self.pause(task_name)
        logger.info("All tasks paused")

    def resume_all(self) -> None:
        """Resume all tasks."""
        self._paused = False
        for task_name in self._schedules:
            self.resume(task_name)
        logger.info("All tasks resumed")

    # =========================================================================
    # Status & Monitoring
    # =========================================================================

    def get_status(self, task_id: str) -> TaskResult:
        """Get status of a specific task execution."""
        # Prefect 3.x requires API client for status checks
        logger.warning("Status check requires Prefect server running")
        return TaskResult(
            task_id=task_id,
            task_name="unknown",
            status=TaskStatus.PENDING,
        )

    def get_running_tasks(self) -> List[TaskResult]:
        """Get all currently running tasks."""
        # Would need Prefect API client
        return []

    def get_queued_tasks(self) -> List[TaskResult]:
        """Get all queued tasks."""
        return []

    def get_history(self, task_name: str = None, limit: int = 100) -> List[TaskResult]:
        """Get task execution history."""
        # Would need Prefect API client
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        return {
            "runner": "prefect",
            "version": "3.x",
            "registered_tasks": len(self._tasks),
            "active_schedules": len([s for s in self._schedules.values() if s.enabled]),
            "paused": self._paused,
        }
