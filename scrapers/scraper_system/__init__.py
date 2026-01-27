"""
SAM Scraper System
"Rest of Your Life" Edition

A comprehensive, production-grade scraping system for training data collection.

Architecture:
- Prefect (orchestration) - swappable to Celery
- Scrapy + Playwright (scraping)
- PostgreSQL (metadata, dedup)
- Redis (queue)

Usage:
    from scraper_system import get_runner, get_database

    # Run a scraper
    runner = get_runner()
    runner.run_now("ao3_spider", pages=100)

    # Check stats
    db = get_database()
    print(db.get_global_stats())

CLI:
    python -m scraper_system status
    python -m scraper_system run ao3
    python -m scraper_system schedule ao3 "0 2 * * *"
"""

__version__ = "1.0.0"
__author__ = "SAM"

from .core.task_runner import get_runner, task
from .core.resource_governor import get_governor
from .storage.database import get_database

__all__ = [
    "get_runner",
    "get_governor",
    "get_database",
    "task",
]
