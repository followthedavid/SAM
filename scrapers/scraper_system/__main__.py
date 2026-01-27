#!/usr/bin/env python3
"""
SAM Scraper System - CLI

Usage:
    python -m scraper_system status           # Show system status
    python -m scraper_system list             # List all scrapers
    python -m scraper_system run <name>       # Run a scraper now
    python -m scraper_system schedule <name> <cron>  # Schedule a scraper
    python -m scraper_system pause            # Pause all scrapers
    python -m scraper_system resume           # Resume all scrapers
    python -m scraper_system stats            # Show statistics
    python -m scraper_system history [name]   # Show job history
    python -m scraper_system resources        # Show resource status
    python -m scraper_system init-db          # Initialize database
"""

import sys
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("scraper_cli")


def cmd_status(args):
    """Show system status."""
    from .core.resource_governor import get_governor
    from .config.settings import RUNNER, DATA_SOURCES

    print("\n" + "=" * 60)
    print("SAM SCRAPER SYSTEM STATUS")
    print("=" * 60)

    # Runner info
    print(f"\nRunner: {RUNNER.upper()}")

    # Resource status
    governor = get_governor()
    status = governor.get_status()
    print(f"\nResources:")
    print(f"  State: {status.state.value}")
    print(f"  RAM: {status.available_ram_gb:.1f}GB / {status.total_ram_gb:.1f}GB")
    print(f"  CPU: {status.cpu_percent:.1f}%")
    print(f"  Can scrape: {'Yes' if status.can_start_scraper else 'No'}")
    if status.blocking_processes:
        print(f"  Blocked by: {', '.join(status.blocking_processes)}")

    # Scraper status
    enabled = sum(1 for s in DATA_SOURCES.values() if s.get("enabled"))
    print(f"\nScrapers:")
    print(f"  Total: {len(DATA_SOURCES)}")
    print(f"  Enabled: {enabled}")

    # Try to get runner stats
    try:
        from .core.task_runner import get_runner
        runner = get_runner()
        runner.initialize()
        stats = runner.get_stats()
        print(f"\nRunner Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"\nRunner not available: {e}")

    print("=" * 60 + "\n")


def cmd_list(args):
    """List all scrapers."""
    from .config.settings import DATA_SOURCES

    print("\n" + "=" * 60)
    print("AVAILABLE SCRAPERS")
    print("=" * 60)

    for source_id, info in sorted(DATA_SOURCES.items()):
        status = "✓" if info.get("enabled") else "✗"
        needs_pw = " (Playwright)" if info.get("needs_playwright") else ""
        print(f"  [{status}] {source_id:<15} - {info['name']}{needs_pw}")
        print(f"      Type: {info['type']}, Priority: {info['priority']}")

    print("=" * 60 + "\n")


def cmd_run(args):
    """Run a scraper now."""
    from .config.settings import DATA_SOURCES
    from .core.resource_governor import get_governor

    source_id = args.name

    if source_id not in DATA_SOURCES:
        print(f"Unknown scraper: {source_id}")
        print(f"Available: {', '.join(DATA_SOURCES.keys())}")
        return 1

    # Check resources first
    governor = get_governor()
    status = governor.get_status()
    if not status.can_start_scraper:
        print(f"Cannot start scraper: {status.reason}")
        print("Use --force to override")
        if not getattr(args, 'force', False):
            return 1

    print(f"\nStarting scraper: {source_id}")

    # Map source_id to spider class
    spider_map = {
        "ao3": "ao3_spider",
        "nifty": "nifty_spider",
        "literotica": "literotica_spider",
        "dark_psych": "dark_psych_spider",
        "flist": "flist_spider",
        "bluemoon": "bluemoon_spider",
        "wwd": "wwd_spider",
        "vogue": "vmag_spider",
        "wmag": "wmag_spider",
        "gq": "gq_spider",
        "esquire": "esquire_spider",
        "thecut": "thecut_spider",
        "reddit_rp": "reddit_roleplay_spider",
        "ao3_rp": "ao3_roleplay_spider",
        "calcareers": "calcareers_spider",
        "resumes": "resume_spider",
        "coverletters": "coverletter_spider",
        "soq": "soq_spider",
        "bias_ratings": "bias_ratings_spider",
        "news": "rss_news_spider",
        "articles": "full_article_spider",
        "github": "github_spider",
        "stackoverflow": "stackoverflow_spider",
        "devto": "devto_spider",
        "hashnode": "hashnode_spider",
        "docs": "docs_spider",
        "uiux": "uiux_spider",
        "apple_dev": "apple_dev_spider",
        "swift_community": "swift_community_spider",
        "wwdc": "wwdc_spider",
        "github_events": "github_events_spider",
        "hackernews": "hackernews_spider",
        "reddit_stream": "reddit_stream_spider",
        "error_corpus": "error_corpus_spider",
        "swift_error_db": "swift_error_db_spider",
        "curriculum": "curriculum_spider",
        "architecture": "architecture_spider",
        "templates": "templates_spider",
        "planning_qa": "planning_qa_spider",
        "specs": "specs_spider",
    }

    spider_name = spider_map.get(source_id, f"{source_id}_spider")

    try:
        # Run with Scrapy
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings

        # Get spider class
        from .spiders import (
            AO3Spider, NiftySpider, LiteroticaSpider, DarkPsychSpider,
            FListSpider, BlueMoonSpider, WWDSpider, VMagSpider, WMagSpider,
            GQSpider, EsquireSpider, TheCutSpider,
            RedditRoleplaySpider, AO3RoleplaySpider,
            CalCareersSpider, ResumeSpider, CoverLetterSpider, SOQExamplesSpider,
            BiasRatingsSpider, RSSNewsSpider, FullArticleSpider,
            GitHubSpider, StackOverflowSpider,
            DevToSpider, HashNodeSpider, DocsSpider, UIUXSpider,
            AppleDevSpider, SwiftCommunitySpider, WWDCSpider,
            GitHubEventsSpider, HackerNewsSpider, RedditStreamSpider,
            ErrorCorpusSpider, SwiftErrorDatabaseSpider,
            CurriculumSpider, ArchitectureSpider, ProjectTemplatesSpider,
            SpecificationSpider,
        )
        from .spiders.planning_qa_spider import PlanningQASpider

        spider_classes = {
            "ao3_spider": AO3Spider,
            "nifty_spider": NiftySpider,
            "literotica_spider": LiteroticaSpider,
            "dark_psych_spider": DarkPsychSpider,
            "flist_spider": FListSpider,
            "bluemoon_spider": BlueMoonSpider,
            "wwd_spider": WWDSpider,
            "vmag_spider": VMagSpider,
            "wmag_spider": WMagSpider,
            "gq_spider": GQSpider,
            "esquire_spider": EsquireSpider,
            "thecut_spider": TheCutSpider,
            "reddit_roleplay_spider": RedditRoleplaySpider,
            "ao3_roleplay_spider": AO3RoleplaySpider,
            "calcareers_spider": CalCareersSpider,
            "resume_spider": ResumeSpider,
            "coverletter_spider": CoverLetterSpider,
            "soq_spider": SOQExamplesSpider,
            "bias_ratings_spider": BiasRatingsSpider,
            "rss_news_spider": RSSNewsSpider,
            "full_article_spider": FullArticleSpider,
            "github_spider": GitHubSpider,
            "stackoverflow_spider": StackOverflowSpider,
            "devto_spider": DevToSpider,
            "hashnode_spider": HashNodeSpider,
            "docs_spider": DocsSpider,
            "uiux_spider": UIUXSpider,
            "apple_dev_spider": AppleDevSpider,
            "swift_community_spider": SwiftCommunitySpider,
            "wwdc_spider": WWDCSpider,
            "github_events_spider": GitHubEventsSpider,
            "hackernews_spider": HackerNewsSpider,
            "reddit_stream_spider": RedditStreamSpider,
            "error_corpus_spider": ErrorCorpusSpider,
            "swift_error_db_spider": SwiftErrorDatabaseSpider,
            "curriculum_spider": CurriculumSpider,
            "architecture_spider": ArchitectureSpider,
            "templates_spider": ProjectTemplatesSpider,
            "planning_qa_spider": PlanningQASpider,
            "specs_spider": SpecificationSpider,
        }

        spider_class = spider_classes.get(spider_name)
        if not spider_class:
            print(f"Spider not implemented yet: {spider_name}")
            return 1

        # Configure settings
        settings = {
            "LOG_LEVEL": "INFO",
            "ITEM_PIPELINES": {
                "scraper_system.pipelines.database_pipeline.DatabasePipeline": 300,
            },
        }

        # Add spider-specific settings
        if hasattr(spider_class, "custom_settings"):
            settings.update(spider_class.custom_settings)

        # Build spider kwargs
        spider_kwargs = {}
        if args.pages:
            spider_kwargs["max_pages"] = args.pages
        if getattr(args, 'nc_mode', False):
            spider_kwargs["nc_mode"] = True
            print("NC MODE ENABLED - targeting non-consent content")

        # Run the spider
        process = CrawlerProcess(settings)
        process.crawl(spider_class, **spider_kwargs)
        process.start()

        print("\nScraper completed!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def cmd_schedule(args):
    """Schedule a scraper."""
    from .core.task_runner import get_runner, ScheduleConfig
    from .config.settings import DATA_SOURCES

    source_id = args.name
    cron = args.cron

    if source_id not in DATA_SOURCES:
        print(f"Unknown scraper: {source_id}")
        return 1

    print(f"\nScheduling {source_id} with cron: {cron}")

    try:
        runner = get_runner()
        runner.initialize()

        config = ScheduleConfig(
            task_name=f"{source_id}_spider",
            cron=cron,
            enabled=True,
        )
        runner.schedule(config)

        print(f"Scheduled successfully!")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_pause(args):
    """Pause all scrapers."""
    from .core.task_runner import get_runner

    print("\nPausing all scrapers...")

    try:
        runner = get_runner()
        runner.initialize()
        runner.pause_all()
        print("All scrapers paused.")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_resume(args):
    """Resume all scrapers."""
    from .core.task_runner import get_runner

    print("\nResuming all scrapers...")

    try:
        runner = get_runner()
        runner.initialize()
        runner.resume_all()
        print("All scrapers resumed.")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_stats(args):
    """Show statistics."""
    from .storage.database import get_database

    print("\n" + "=" * 60)
    print("SCRAPER STATISTICS")
    print("=" * 60)

    try:
        db = get_database()

        # Global stats
        global_stats = db.get_global_stats()
        print("\nGlobal:")
        print(f"  Total items: {global_stats.get('total_items') or 0:,}")
        print(f"  Total sources: {global_stats.get('total_sources') or 0}")
        print(f"  Total bytes: {global_stats.get('total_bytes') or 0:,}")
        print(f"  Processed: {global_stats.get('processed_count') or 0:,}")
        print(f"  Total jobs: {global_stats.get('total_jobs') or 0:,}")
        print(f"  Completed: {global_stats.get('completed_jobs') or 0:,}")
        print(f"  Failed: {global_stats.get('failed_jobs') or 0:,}")

        # Per-source stats
        source_stats = db.get_stats()
        if source_stats:
            print("\nBy Source:")
            for source, stats in sorted(source_stats.items(), key=lambda x: -x[1].get('total_items', 0)):
                items = stats.get('total_items', 0)
                bytes_size = stats.get('total_bytes', 0) or 0
                mb = bytes_size / (1024 * 1024)
                print(f"  {source:<15}: {items:>8,} items ({mb:>8.1f} MB)")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    print("=" * 60 + "\n")
    return 0


def cmd_history(args):
    """Show job history."""
    from .storage.database import get_database

    print("\n" + "=" * 60)
    print("JOB HISTORY")
    print("=" * 60)

    try:
        db = get_database()
        history = db.get_job_history(task_name=args.name, limit=args.limit)

        for job in history:
            status_icon = "✓" if job.status == "completed" else "✗" if job.status == "failed" else "○"
            started = job.started_at.strftime("%Y-%m-%d %H:%M") if job.started_at else "N/A"
            print(f"  [{status_icon}] {job.task_name:<20} {started} - {job.items_scraped:>6} items")
            if job.error:
                print(f"      Error: {job.error[:50]}...")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    print("=" * 60 + "\n")
    return 0


def cmd_resources(args):
    """Show resource status."""
    from .core.resource_governor import get_governor

    governor = get_governor()
    status = governor.get_status()

    print("\n" + "=" * 60)
    print("RESOURCE STATUS")
    print("=" * 60)
    print(f"State: {status.state.value}")
    print(f"Available RAM: {status.available_ram_gb:.2f} GB")
    print(f"Total RAM: {status.total_ram_gb:.2f} GB")
    print(f"CPU: {status.cpu_percent:.1f}%")
    print(f"Can start scraper: {status.can_start_scraper}")
    print(f"Reason: {status.reason}")
    if status.blocking_processes:
        print(f"Blocking processes: {', '.join(status.blocking_processes)}")
    print("=" * 60 + "\n")
    return 0


def cmd_init_db(args):
    """Initialize the database."""
    from .storage.database import get_database

    print("\nInitializing database...")

    try:
        db = get_database()
        print("Database initialized successfully!")
        print(f"Tables created in PostgreSQL")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  brew services start postgresql")
        print("\nAnd create the database:")
        print("  createdb sam_scraper")
        return 1

    return 0


def cmd_dashboard(args):
    """Run the web dashboard."""
    from .dashboard import run_dashboard
    port = getattr(args, 'port', 8080)
    print(f"\nStarting dashboard on http://localhost:{port}")
    print("No SAM/Ollama required - reads directly from PostgreSQL")
    run_dashboard(port)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="SAM Scraper System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # status
    subparsers.add_parser("status", help="Show system status")

    # list
    subparsers.add_parser("list", help="List all scrapers")

    # run
    run_parser = subparsers.add_parser("run", help="Run a scraper")
    run_parser.add_argument("name", help="Scraper name")
    run_parser.add_argument("--pages", type=int, help="Max pages to scrape")
    run_parser.add_argument("--nc-mode", action="store_true", dest="nc_mode",
                           help="Enable NC mode for AO3 spider (non-consent content)")
    run_parser.add_argument("--force", action="store_true",
                           help="Force run even if system resources are low")

    # schedule
    sched_parser = subparsers.add_parser("schedule", help="Schedule a scraper")
    sched_parser.add_argument("name", help="Scraper name")
    sched_parser.add_argument("cron", help="Cron expression (e.g., '0 2 * * *')")

    # pause
    subparsers.add_parser("pause", help="Pause all scrapers")

    # resume
    subparsers.add_parser("resume", help="Resume all scrapers")

    # stats
    subparsers.add_parser("stats", help="Show statistics")

    # history
    hist_parser = subparsers.add_parser("history", help="Show job history")
    hist_parser.add_argument("name", nargs="?", help="Filter by scraper name")
    hist_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # resources
    subparsers.add_parser("resources", help="Show resource status")

    # init-db
    subparsers.add_parser("init-db", help="Initialize database")

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Run web dashboard")
    dash_parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "status": cmd_status,
        "list": cmd_list,
        "run": cmd_run,
        "schedule": cmd_schedule,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "stats": cmd_stats,
        "history": cmd_history,
        "resources": cmd_resources,
        "init-db": cmd_init_db,
        "dashboard": cmd_dashboard,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
