"""
SAM Scraper System - Task Runner Abstraction Layer

This abstraction allows swapping between Prefect and Celery without
changing any scraper code. Your scrapers call this interface, not
the orchestration system directly.

To swap systems: Change RUNNER in config/settings.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task/job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class TaskResult:
    """Result from a task execution."""
    task_id: str
    task_name: str
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    items_scraped: int = 0
    bytes_downloaded: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled task."""
    task_name: str
    cron: str  # Cron expression
    enabled: bool = True
    kwargs: Dict[str, Any] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class TaskRunner(ABC):
    """
    Abstract base class for task orchestration.

    Implement this interface to add a new orchestration system.
    Current implementations:
    - PrefectRunner (prefect_runner.py)
    - CeleryRunner (celery_runner.py)
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the runner (connect to services, etc.)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully shutdown the runner."""
        pass

    # =========================================================================
    # Task Registration
    # =========================================================================

    @abstractmethod
    def register_task(self, name: str, func: Callable, **options) -> None:
        """
        Register a function as a task.

        Args:
            name: Unique task name
            func: The function to execute
            **options: Runner-specific options (retries, timeout, etc.)
        """
        pass

    # =========================================================================
    # Task Execution
    # =========================================================================

    @abstractmethod
    def run_now(self, task_name: str, **kwargs) -> TaskResult:
        """
        Run a task immediately.

        Args:
            task_name: Name of registered task
            **kwargs: Arguments to pass to task

        Returns:
            TaskResult with execution details
        """
        pass

    @abstractmethod
    def run_async(self, task_name: str, **kwargs) -> str:
        """
        Queue a task for async execution.

        Args:
            task_name: Name of registered task
            **kwargs: Arguments to pass to task

        Returns:
            task_id for tracking
        """
        pass

    @abstractmethod
    def run_chain(self, tasks: List[tuple]) -> str:
        """
        Run a chain of tasks in sequence.

        Args:
            tasks: List of (task_name, kwargs) tuples

        Returns:
            chain_id for tracking
        """
        pass

    # =========================================================================
    # Scheduling
    # =========================================================================

    @abstractmethod
    def schedule(self, config: ScheduleConfig) -> None:
        """
        Schedule a task to run on a cron schedule.

        Args:
            config: Schedule configuration
        """
        pass

    @abstractmethod
    def unschedule(self, task_name: str) -> None:
        """Remove a scheduled task."""
        pass

    @abstractmethod
    def get_schedules(self) -> List[ScheduleConfig]:
        """Get all active schedules."""
        pass

    # =========================================================================
    # Task Control
    # =========================================================================

    @abstractmethod
    def pause(self, task_name: str) -> None:
        """Pause a running or scheduled task."""
        pass

    @abstractmethod
    def resume(self, task_name: str) -> None:
        """Resume a paused task."""
        pass

    @abstractmethod
    def cancel(self, task_id: str) -> None:
        """Cancel a running or queued task."""
        pass

    @abstractmethod
    def pause_all(self) -> None:
        """Pause all tasks (e.g., when RAM is low)."""
        pass

    @abstractmethod
    def resume_all(self) -> None:
        """Resume all paused tasks."""
        pass

    # =========================================================================
    # Status & Monitoring
    # =========================================================================

    @abstractmethod
    def get_status(self, task_id: str) -> TaskResult:
        """Get status of a specific task execution."""
        pass

    @abstractmethod
    def get_running_tasks(self) -> List[TaskResult]:
        """Get all currently running tasks."""
        pass

    @abstractmethod
    def get_queued_tasks(self) -> List[TaskResult]:
        """Get all queued tasks."""
        pass

    @abstractmethod
    def get_history(self, task_name: str = None, limit: int = 100) -> List[TaskResult]:
        """
        Get task execution history.

        Args:
            task_name: Filter by task name (None for all)
            limit: Maximum results
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        pass


def get_runner() -> TaskRunner:
    """
    Factory function to get the configured task runner.

    This is the main entry point. Your code should use this:

        from scraper_system.core.task_runner import get_runner

        runner = get_runner()
        runner.run_now("scrape_ao3", pages=100)

    To swap orchestration systems, change RUNNER in config/settings.py
    """
    from ..config.settings import RUNNER

    if RUNNER == "prefect":
        from ..runners.prefect_runner import PrefectRunner
        return PrefectRunner()
    elif RUNNER == "celery":
        from ..runners.celery_runner import CeleryRunner
        return CeleryRunner()
    else:
        raise ValueError(f"Unknown runner: {RUNNER}. Use 'prefect' or 'celery'.")


# =============================================================================
# Decorators for easy task registration
# =============================================================================

_registered_tasks: Dict[str, Callable] = {}


def task(name: str = None, **options):
    """
    Decorator to register a function as a task.

    Usage:
        @task("scrape_ao3")
        def scrape_ao3(pages: int = 100):
            # scraping logic
            pass

    The task can then be run via:
        runner = get_runner()
        runner.run_now("scrape_ao3", pages=50)
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__
        _registered_tasks[task_name] = {
            "func": func,
            "options": options,
        }
        logger.debug(f"Registered task: {task_name}")
        return func
    return decorator


def get_registered_tasks() -> Dict[str, Callable]:
    """Get all tasks registered via @task decorator."""
    return _registered_tasks
