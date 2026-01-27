"""
SAM Scraper System - Configuration
"Rest of Your Life" Edition

All settings in one place. Modify this file to configure the system.
"""

from pathlib import Path
from typing import Literal

# =============================================================================
# RUNNER CONFIGURATION (Swappable)
# =============================================================================

# Which orchestration system to use
# Options: "prefect", "celery"
# Change this one line to swap orchestration systems
RUNNER: Literal["prefect", "celery"] = "prefect"

# =============================================================================
# STORAGE PATHS
# =============================================================================

# Base directories
# Try external drive first, fall back to home directory
EXTERNAL_DRIVE = Path("/Volumes/David External")
if EXTERNAL_DRIVE.exists() and EXTERNAL_DRIVE.is_dir():
    try:
        # Test if writable
        test_file = EXTERNAL_DRIVE / ".write_test"
        test_file.touch()
        test_file.unlink()
        SCRAPER_DATA_DIR = EXTERNAL_DRIVE / "scraper_data"
    except (PermissionError, OSError):
        # Fall back to home directory
        SCRAPER_DATA_DIR = Path.home() / ".sam" / "scraper_data"
else:
    SCRAPER_DATA_DIR = Path.home() / ".sam" / "scraper_data"

RAW_ARCHIVES_DIR = SCRAPER_DATA_DIR / "raw_archives"
PROCESSED_DIR = SCRAPER_DATA_DIR / "processed"
TRAINING_DATA_DIR = SCRAPER_DATA_DIR / "training_data"

# Ensure directories exist
for dir_path in [SCRAPER_DATA_DIR, RAW_ARCHIVES_DIR, PROCESSED_DIR, TRAINING_DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL (metadata, job history, deduplication)
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "sam_scraper"
POSTGRES_USER = ""  # Empty = use current macOS user (peer auth)
POSTGRES_PASSWORD = ""

# macOS uses peer auth by default, so just dbname is enough
POSTGRES_URL = f"postgresql:///{POSTGRES_DB}"

# Redis (queue, fast state)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# =============================================================================
# RESOURCE LIMITS (8GB Mac)
# =============================================================================

# Minimum free RAM to start new scraper (bytes)
MIN_FREE_RAM_BYTES = 1 * 1024 * 1024 * 1024  # 1GB (lowered for current session)

# Maximum concurrent spiders
# 8GB Mac can handle 2-3 lightweight scrapers if VLM/Ollama not running
# ResourceGovernor will pause if RAM gets too low
MAX_CONCURRENT_SPIDERS = 1  # Reduced for coexistence with LoRA training

# Pause scraping when these processes are detected
PAUSE_WHEN_RUNNING = [
    "mlx_vlm",      # Vision model
    "ollama",       # LLM server
    "python.*vlm",  # Any VLM process
]

# =============================================================================
# SCRAPER SETTINGS
# =============================================================================

# Default rate limits (seconds between requests)
RATE_LIMITS = {
    "default": 2.0,
    "ao3": 3.0,           # AO3 is strict
    "nifty": 2.0,
    "literotica": 2.0,
    "reddit": 1.0,
    "github": 0.5,
    "wwd": 1.5,
    "magazine": 1.5,
}

# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60

# =============================================================================
# SCHEDULING
# =============================================================================

# Default schedule (cron format)
DEFAULT_SCHEDULE = "0 2 * * *"  # 2 AM daily

# Scraper-specific schedules
SCRAPER_SCHEDULES = {
    "ao3": "0 2 * * *",        # 2 AM
    "nifty": "0 3 * * *",      # 3 AM
    "literotica": "0 4 * * *", # 4 AM
    "dark_psych": "0 5 * * *", # 5 AM
    "reddit": "0 1 * * *",     # 1 AM (fast)
    "github": "0 0 * * 0",     # Midnight Sunday
    "wwd": "0 2 * * 6",        # 2 AM Saturday
}

# =============================================================================
# LOGGING
# =============================================================================

LOG_DIR = Path.home() / ".sam" / "scraper_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# DATA SOURCES REGISTRY
# =============================================================================

# All available scrapers and their configurations
DATA_SOURCES = {
    # Fiction/Roleplay
    "ao3": {
        "name": "Archive of Our Own",
        "type": "fiction",
        "spider": "ao3_spider",
        "priority": 1,
        "enabled": True,
    },
    "nifty": {
        "name": "Nifty Archive",
        "type": "fiction",
        "spider": "nifty_spider",
        "priority": 1,
        "enabled": True,
    },
    "literotica": {
        "name": "Literotica",
        "type": "fiction",
        "spider": "literotica_spider",
        "priority": 2,
        "enabled": True,
    },
    "dark_psych": {
        "name": "Dark Psychology",
        "type": "fiction",
        "spider": "dark_psych_spider",
        "priority": 2,
        "enabled": True,
    },
    "flist": {
        "name": "F-List",
        "type": "roleplay",
        "spider": "flist_spider",
        "priority": 3,
        "enabled": True,
    },
    "reddit_rp": {
        "name": "Reddit Roleplay",
        "type": "roleplay",
        "spider": "reddit_rp_spider",
        "priority": 3,
        "enabled": True,
    },

    # Fashion/Culture
    "wwd": {
        "name": "Women's Wear Daily",
        "type": "fashion",
        "spider": "wwd_spider",
        "priority": 2,
        "enabled": True,
        "needs_playwright": True,
    },
    "wmag": {
        "name": "W Magazine",
        "type": "fashion",
        "spider": "wmag_spider",
        "priority": 3,
        "enabled": True,
    },
    "vmag": {
        "name": "V Magazine",
        "type": "fashion",
        "spider": "vmag_spider",
        "priority": 3,
        "enabled": True,
    },
    "thecut": {
        "name": "The Cut",
        "type": "culture",
        "spider": "thecut_spider",
        "priority": 2,
        "enabled": True,
    },
    "gq_esquire": {
        "name": "GQ & Esquire",
        "type": "culture",
        "spider": "gq_esquire_spider",
        "priority": 3,
        "enabled": True,
    },
    "interview": {
        "name": "Interview Magazine",
        "type": "culture",
        "spider": "interview_spider",
        "priority": 3,
        "enabled": True,
    },

    # Code/Technical
    "github": {
        "name": "GitHub READMEs & Issues",
        "type": "code",
        "spider": "github_spider",
        "priority": 1,
        "enabled": True,
    },
    "stackoverflow": {
        "name": "Stack Overflow Q&A",
        "type": "code",
        "spider": "stackoverflow_spider",
        "priority": 1,
        "enabled": True,
    },
    "devto": {
        "name": "Dev.to Tutorials",
        "type": "code",
        "spider": "devto_spider",
        "priority": 2,
        "enabled": True,
    },
    "hashnode": {
        "name": "Hashnode Articles",
        "type": "code",
        "spider": "hashnode_spider",
        "priority": 3,
        "enabled": True,
    },
    "docs": {
        "name": "Package Manager Docs",
        "type": "code",
        "spider": "docs_spider",
        "priority": 1,
        "enabled": True,
    },
    "uiux": {
        "name": "UI/UX & Accessibility",
        "type": "code",
        "spider": "uiux_spider",
        "priority": 2,
        "enabled": True,
    },

    # Apple Ecosystem (CRITICAL for app builder)
    "apple_dev": {
        "name": "Apple Developer Docs",
        "type": "apple",
        "spider": "apple_dev_spider",
        "priority": 1,
        "enabled": True,
    },
    "swift_community": {
        "name": "Swift Community Tutorials",
        "type": "apple",
        "spider": "swift_community_spider",
        "priority": 1,
        "enabled": True,
    },
    "wwdc": {
        "name": "WWDC Session Transcripts",
        "type": "apple",
        "spider": "wwdc_spider",
        "priority": 1,
        "enabled": True,
    },

    # Real-Time Streams
    "github_events": {
        "name": "GitHub Events Stream",
        "type": "realtime",
        "spider": "github_events_spider",
        "priority": 1,
        "enabled": True,
    },
    "hackernews": {
        "name": "HackerNews Stories",
        "type": "realtime",
        "spider": "hackernews_spider",
        "priority": 2,
        "enabled": True,
    },
    "reddit_stream": {
        "name": "Reddit Programming",
        "type": "realtime",
        "spider": "reddit_stream_spider",
        "priority": 2,
        "enabled": True,
    },

    # Error Corpus (CRITICAL for debugging)
    "error_corpus": {
        "name": "Error Messages & Solutions",
        "type": "errors",
        "spider": "error_corpus_spider",
        "priority": 1,
        "enabled": True,
    },
    "swift_error_db": {
        "name": "Swift Error Database",
        "type": "errors",
        "spider": "swift_error_db_spider",
        "priority": 1,
        "enabled": True,
    },

    # Books/PDFs (future)
    "books": {
        "name": "Book Collection",
        "type": "books",
        "spider": "book_spider",
        "priority": 1,
        "enabled": False,  # Not yet implemented
    },

    # Job Applications
    "calcareers": {
        "name": "California State Jobs",
        "type": "jobs",
        "spider": "calcareers_spider",
        "priority": 1,
        "enabled": True,
    },
    "resumes": {
        "name": "Resume Examples",
        "type": "jobs",
        "spider": "resume_spider",
        "priority": 2,
        "enabled": True,
    },
    "coverletters": {
        "name": "Cover Letter Examples",
        "type": "jobs",
        "spider": "coverletter_spider",
        "priority": 2,
        "enabled": True,
    },
    "soq": {
        "name": "SOQ Examples",
        "type": "jobs",
        "spider": "soq_spider",
        "priority": 2,
        "enabled": True,
    },

    # News & Current Events
    "bias_ratings": {
        "name": "Media Bias Ratings",
        "type": "news",
        "spider": "bias_ratings_spider",
        "priority": 1,
        "enabled": True,
    },
    "news": {
        "name": "RSS News Aggregator",
        "type": "news",
        "spider": "rss_news_spider",
        "priority": 1,
        "enabled": True,
    },
    "articles": {
        "name": "Full Article Fetcher",
        "type": "news",
        "spider": "full_article_spider",
        "priority": 2,
        "enabled": True,
    },

    # Planning & Architecture (CRITICAL for app builder)
    "curriculum": {
        "name": "Structured Learning Paths",
        "type": "planning",
        "spider": "curriculum_spider",
        "priority": 1,
        "enabled": True,
    },
    "architecture": {
        "name": "Architecture Patterns & ADRs",
        "type": "planning",
        "spider": "architecture_spider",
        "priority": 1,
        "enabled": True,
    },
    "templates": {
        "name": "Project Templates & Boilerplates",
        "type": "planning",
        "spider": "templates_spider",
        "priority": 1,
        "enabled": True,
    },
    "planning_qa": {
        "name": "Planning Q&A Generator",
        "type": "planning",
        "spider": "planning_qa_spider",
        "priority": 1,
        "enabled": True,
    },
    "specs": {
        "name": "PRDs & Technical Specs",
        "type": "planning",
        "spider": "specs_spider",
        "priority": 1,
        "enabled": True,
    },
}
