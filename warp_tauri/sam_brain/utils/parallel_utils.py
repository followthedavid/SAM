"""
Parallel Processing Utilities for SAM
=====================================
ThreadPoolExecutor patterns extracted from parallel_learn.py.
Optimized for 8GB M2 Mac Mini.
"""

import os
import concurrent.futures
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
)
from dataclasses import dataclass, field
from enum import Enum

T = TypeVar("T")
R = TypeVar("R")


class TaskStatus(Enum):
    """Status of a parallel task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Result of a parallel task execution."""
    name: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0


def get_optimal_workers(
    task_type: str = "io",
    max_override: Optional[int] = None
) -> int:
    """
    Calculate optimal worker count for 8GB M2 Mac Mini.

    Args:
        task_type: "io" for I/O-bound tasks (network, disk),
                   "cpu" for CPU-bound tasks
        max_override: Hard cap on workers (useful for testing)

    Returns:
        Recommended number of workers
    """
    cpu_count = os.cpu_count() or 4

    if task_type == "io":
        # I/O-bound: can use more threads since they spend time waiting
        # 8GB RAM constraint: keep it reasonable
        workers = min(cpu_count * 2, 8)
    elif task_type == "cpu":
        # CPU-bound: don't exceed cores, leave 1 for system
        workers = max(1, cpu_count - 1)
    else:
        # Default: conservative
        workers = min(cpu_count, 4)

    if max_override is not None:
        workers = min(workers, max_override)

    return workers


class ParallelExecutor:
    """
    ThreadPoolExecutor wrapper with progress tracking and error handling.

    Example usage:
        executor = ParallelExecutor(max_workers=4)

        def my_callback(result: TaskResult):
            print(f"{result.name}: {result.status.value}")

        tasks = {
            "task1": lambda: process_file("a.txt"),
            "task2": lambda: process_file("b.txt"),
            "task3": lambda: process_file("c.txt"),
        }

        results = executor.run_all(tasks, on_complete=my_callback)
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        task_type: str = "io"
    ):
        """
        Initialize the parallel executor.

        Args:
            max_workers: Number of worker threads. If None, auto-calculated.
            task_type: "io" or "cpu" for auto worker calculation
        """
        self.max_workers = max_workers or get_optimal_workers(task_type)
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

    def __enter__(self) -> "ParallelExecutor":
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def run_all(
        self,
        tasks: Dict[str, Callable[[], T]],
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        fail_fast: bool = False
    ) -> Dict[str, TaskResult]:
        """
        Execute all tasks in parallel, collecting results as they complete.

        Args:
            tasks: Dict mapping task name to callable
            on_complete: Optional callback invoked for each completed task
            fail_fast: If True, cancel remaining tasks on first error

        Returns:
            Dict mapping task name to TaskResult
        """
        import time

        results: Dict[str, TaskResult] = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all tasks
            future_to_name: Dict[concurrent.futures.Future, str] = {}
            task_starts: Dict[str, float] = {}

            for name, func in tasks.items():
                future = executor.submit(func)
                future_to_name[future] = name
                task_starts[name] = time.time()

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
                duration_ms = (time.time() - task_starts[name]) * 1000

                try:
                    result_value = future.result()
                    task_result = TaskResult(
                        name=name,
                        status=TaskStatus.COMPLETED,
                        result=result_value,
                        duration_ms=duration_ms
                    )
                except Exception as e:
                    task_result = TaskResult(
                        name=name,
                        status=TaskStatus.FAILED,
                        error=e,
                        duration_ms=duration_ms
                    )

                    if fail_fast:
                        # Cancel remaining futures
                        for f in future_to_name:
                            f.cancel()

                results[name] = task_result

                if on_complete:
                    on_complete(task_result)

        return results


class BatchProcessor:
    """
    Process items in batches with parallel workers.

    Useful for processing large lists of items where each item
    needs independent processing.

    Example usage:
        processor = BatchProcessor(max_workers=4, batch_size=10)

        items = list(range(100))

        def process_item(x):
            return x * 2

        results = processor.process(items, process_item)
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        batch_size: int = 10,
        task_type: str = "io"
    ):
        """
        Initialize the batch processor.

        Args:
            max_workers: Number of worker threads
            batch_size: Items per batch
            task_type: "io" or "cpu" for auto worker calculation
        """
        self.max_workers = max_workers or get_optimal_workers(task_type)
        self.batch_size = batch_size

    def process(
        self,
        items: List[T],
        processor: Callable[[T], R],
        on_item_complete: Optional[Callable[[T, R, Optional[Exception]], None]] = None,
        on_batch_complete: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process all items in parallel batches.

        Args:
            items: List of items to process
            processor: Function to process each item
            on_item_complete: Callback(item, result, error) for each item
            on_batch_complete: Callback(completed_count, total_count) after each batch

        Returns:
            List of dicts with keys: item, result, error
        """
        results: List[Dict[str, Any]] = []
        total = len(items)
        completed = 0

        # Process in batches
        for batch_start in range(0, total, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total)
            batch = items[batch_start:batch_end]

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                # Submit batch
                future_to_item = {
                    executor.submit(processor, item): item
                    for item in batch
                }

                # Collect results
                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    error = None
                    result = None

                    try:
                        result = future.result()
                    except Exception as e:
                        error = e

                    results.append({
                        "item": item,
                        "result": result,
                        "error": error
                    })

                    completed += 1

                    if on_item_complete:
                        on_item_complete(item, result, error)

            if on_batch_complete:
                on_batch_complete(completed, total)

        return results

    def iter_process(
        self,
        items: List[T],
        processor: Callable[[T], R]
    ) -> Iterator[Dict[str, Any]]:
        """
        Process items and yield results as they complete.

        Args:
            items: List of items to process
            processor: Function to process each item

        Yields:
            Dict with keys: item, result, error
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_item = {
                executor.submit(processor, item): item
                for item in items
            }

            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                error = None
                result = None

                try:
                    result = future.result()
                except Exception as e:
                    error = e

                yield {
                    "item": item,
                    "result": result,
                    "error": error
                }


# Convenience functions

def parallel_map(
    items: List[T],
    func: Callable[[T], R],
    max_workers: Optional[int] = None
) -> List[R]:
    """
    Simple parallel map - process items and return results in order.

    Unlike BatchProcessor, this preserves input order and raises
    on first error.

    Args:
        items: Items to process
        func: Function to apply to each item
        max_workers: Worker count (auto-calculated if None)

    Returns:
        List of results in same order as input

    Raises:
        First exception encountered during processing
    """
    workers = max_workers or get_optimal_workers()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(func, items))


def parallel_filter(
    items: List[T],
    predicate: Callable[[T], bool],
    max_workers: Optional[int] = None
) -> List[T]:
    """
    Filter items in parallel.

    Args:
        items: Items to filter
        predicate: Function returning True for items to keep
        max_workers: Worker count (auto-calculated if None)

    Returns:
        Filtered list preserving original order
    """
    workers = max_workers or get_optimal_workers()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda x: (x, predicate(x)), items))

    return [item for item, keep in results if keep]
