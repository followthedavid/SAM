"""
Scrapy Settings for SAM Scraper System

These settings are optimized for an 8GB Mac running multiple services.
"""

from config.settings import (
    RATE_LIMITS,
    USER_AGENTS,
    LOG_DIR,
    LOG_LEVEL,
    MAX_CONCURRENT_SPIDERS,
)

# =============================================================================
# Basic Settings
# =============================================================================

BOT_NAME = "sam_scraper"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# =============================================================================
# Crawl Responsibly
# =============================================================================

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests (8GB Mac = be conservative)
CONCURRENT_REQUESTS = MAX_CONCURRENT_SPIDERS
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS_PER_IP = 1

# Configure a delay for requests to the same website
DOWNLOAD_DELAY = RATE_LIMITS.get("default", 2.0)
RANDOMIZE_DOWNLOAD_DELAY = True

# =============================================================================
# AutoThrottle
# =============================================================================

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# =============================================================================
# Cookies & Sessions
# =============================================================================

COOKIES_ENABLED = True
COOKIES_DEBUG = False

# =============================================================================
# HTTP Caching (helps with resume)
# =============================================================================

HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = str(LOG_DIR / "httpcache")
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# =============================================================================
# Retry
# =============================================================================

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# =============================================================================
# User Agents
# =============================================================================

USER_AGENT = USER_AGENTS[0]

# =============================================================================
# Logging
# =============================================================================

LOG_LEVEL = LOG_LEVEL
LOG_FILE = str(LOG_DIR / "scrapy.log")
LOG_STDOUT = False

# =============================================================================
# Pipelines (save to database)
# =============================================================================

ITEM_PIPELINES = {
    "pipelines.database_pipeline.DatabasePipeline": 300,
}

# =============================================================================
# Extensions
# =============================================================================

EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,  # Disable telnet
    "scrapy.extensions.corestats.CoreStats": 500,
    "scrapy.extensions.logstats.LogStats": 500,
}

# =============================================================================
# Download Handlers
# =============================================================================

# Use asyncio reactor for better performance
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Download timeout
DOWNLOAD_TIMEOUT = 30

# =============================================================================
# Memory Management (important for 8GB Mac)
# =============================================================================

MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 1024  # 1GB max for Scrapy
MEMUSAGE_WARNING_MB = 768  # Warn at 768MB
MEMUSAGE_NOTIFY_MAIL = False
MEMUSAGE_CHECK_INTERVAL_SECONDS = 60

# Close spider if memory exceeded
CLOSESPIDER_PAGECOUNT = 0  # Disabled
CLOSESPIDER_ITEMCOUNT = 0  # Disabled

# =============================================================================
# Depth & Breadth
# =============================================================================

DEPTH_LIMIT = 10  # Max depth to crawl
DEPTH_PRIORITY = 1
DEPTH_STATS_VERBOSE = True

# =============================================================================
# DNS
# =============================================================================

DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 1000
