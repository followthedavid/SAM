# Scrapy settings for scraper_system project
#
# Memory-optimized for 8GB Mac Mini

BOT_NAME = "scraper_system"

SPIDER_MODULES = ["scraper_system.spiders"]
NEWSPIDER_MODULE = "scraper_system.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
# Low for 8GB Mac - let multiple spiders share resources
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Configure delays
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies (save memory)
COOKIES_ENABLED = False

# Disable Telnet Console (save memory)
TELNETCONSOLE_ENABLED = False

# Memory management - critical for 8GB Mac
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512  # Kill spider if it exceeds 512MB
MEMUSAGE_NOTIFY_MAIL = []
MEMUSAGE_WARNING_MB = 400

# Configure item pipelines
ITEM_PIPELINES = {
    "scraper_system.pipelines.database_pipeline.DatabasePipeline": 300,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Reduce logging for performance
LOG_LEVEL = "INFO"
LOG_STDOUT = True

# HTTP cache for efficiency (don't re-download same pages)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = "/Volumes/David External/scraper_cache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# DNS cache to reduce lookups
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# Reduce memory for downloads
DOWNLOAD_MAXSIZE = 10485760  # 10MB max per page
DOWNLOAD_WARNSIZE = 5242880  # Warn at 5MB

# Twisted reactor - use selectreactor for lower memory
# TWISTED_REACTOR = "twisted.internet.selectreactor.SelectReactor"

# Request fingerprinter (Scrapy 2.7+)
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
