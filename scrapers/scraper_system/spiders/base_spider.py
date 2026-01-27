"""
SAM Scraper System - Base Spider

All spiders inherit from this base class which provides:
- Automatic database integration
- Progress tracking / resume support
- Rate limiting
- Resource checking
- Logging
"""

import logging
import random
from typing import Optional, Dict, Any, Iterator
from datetime import datetime

# Scrapy imports
try:
    import scrapy
    from scrapy import signals
    from scrapy.http import Request, Response
    from scrapy.exceptions import CloseSpider
    SCRAPY_AVAILABLE = True
except ImportError:
    SCRAPY_AVAILABLE = False
    # Create dummy classes for type hints
    class scrapy:
        class Spider:
            pass

from ..storage.database import get_database, ScrapedItem
from ..core.resource_governor import get_governor

logger = logging.getLogger(__name__)


class BaseSpider(scrapy.Spider if SCRAPY_AVAILABLE else object):
    """
    Base spider class for all SAM scrapers.

    Features:
    - Auto-connects to PostgreSQL for deduplication
    - Tracks progress for resuming
    - Checks resources before each request
    - Configurable rate limiting

    Usage:
        class MySpider(BaseSpider):
            name = "my_spider"
            source = "my_source"
            start_urls = ["https://example.com"]

            def parse(self, response):
                # Extract data
                yield ScrapedItem(
                    source=self.source,
                    url=response.url,
                    title="...",
                    content="...",
                )
    """

    # Override in subclass
    name: str = "base_spider"
    source: str = "unknown"  # Source identifier for database

    # Settings (can override in subclass)
    rate_limit: float = 2.0  # Seconds between requests
    max_pages: Optional[int] = None  # None = no limit
    respect_robots: bool = True

    # Internal state
    _db = None
    _governor = None
    _job_id: Optional[int] = None
    _items_scraped: int = 0
    _bytes_downloaded: int = 0
    _start_time: Optional[datetime] = None

    # Custom settings for Scrapy
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 1,  # One at a time on 8GB Mac
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "ROBOTSTXT_OBEY": False,  # Disabled - many sites have overly restrictive robots.txt
        "COOKIES_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, *args, **kwargs):
        if SCRAPY_AVAILABLE:
            super().__init__(*args, **kwargs)

        # Get settings from config
        from ..config.settings import RATE_LIMITS, USER_AGENTS

        # Set rate limit from config or use default
        self.rate_limit = RATE_LIMITS.get(self.source, RATE_LIMITS.get("default", 2.0))
        self.custom_settings["DOWNLOAD_DELAY"] = self.rate_limit

        # Random user agent
        self.user_agents = USER_AGENTS

        # Override max_pages if passed
        if "max_pages" in kwargs:
            self.max_pages = int(kwargs["max_pages"])

    # =========================================================================
    # Lifecycle Hooks
    # =========================================================================

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Create spider from crawler (Scrapy hook)."""
        spider = super().from_crawler(crawler, *args, **kwargs)

        # Connect signals
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.item_scraped, signal=signals.item_scraped)

        return spider

    def spider_opened(self, spider):
        """Called when spider starts."""
        logger.info(f"Spider {self.name} opened")
        self._start_time = datetime.now()

        # Initialize database
        self._db = get_database()

        # Initialize resource governor
        self._governor = get_governor()
        self._governor.start_monitoring()

        # Register pause callback
        self._governor.on_resources_low(self._on_low_resources)

        # Start job tracking
        self._job_id = self._db.start_job(self.name)
        logger.info(f"Started job {self._job_id}")

    def spider_closed(self, spider, reason):
        """Called when spider closes."""
        logger.info(f"Spider {self.name} closed: {reason}")

        # Complete job tracking
        if self._job_id and self._db:
            error = reason if reason not in ("finished", "shutdown") else None
            self._db.complete_job(
                self._job_id,
                items_scraped=self._items_scraped,
                bytes_downloaded=self._bytes_downloaded,
                error=error,
            )

        # Log summary
        duration = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        logger.info(f"Scraped {self._items_scraped} items in {duration:.1f}s")

    def item_scraped(self, item, response, spider):
        """Called when an item is scraped."""
        self._items_scraped += 1

        # Track bytes
        if hasattr(response, "body"):
            self._bytes_downloaded += len(response.body)

    def _on_low_resources(self):
        """Called when resources are low."""
        logger.warning("Resources low - pausing spider")
        # The governor will handle waiting

    # =========================================================================
    # Request Helpers
    # =========================================================================

    def make_request(
        self,
        url: str,
        callback=None,
        meta: Dict[str, Any] = None,
        **kwargs
    ) -> Request:
        """
        Create a request with standard settings.

        Adds:
        - Random user agent
        - Resource check
        - Progress tracking
        """
        if callback is None:
            callback = self.parse

        if meta is None:
            meta = {}

        # Add random user agent
        headers = kwargs.get("headers", {})
        headers["User-Agent"] = random.choice(self.user_agents)
        kwargs["headers"] = headers

        # Check resources before making request
        if self._governor and not self._governor.can_start_scraper():
            status = self._governor.get_status()
            logger.warning(f"Waiting for resources: {status.reason}")
            self._governor.wait_for_resources(timeout_seconds=600)

        return Request(url, callback=callback, meta=meta, **kwargs)

    # =========================================================================
    # Database Helpers
    # =========================================================================

    def url_seen(self, url: str) -> bool:
        """Check if URL has been scraped before."""
        if self._db:
            return self._db.url_exists(url)
        return False

    def content_seen(self, content: str) -> bool:
        """Check if content has been scraped before (deduplication)."""
        if self._db:
            content_hash = self._db.hash_content(content)
            return self._db.item_exists(content_hash)
        return False

    def save_item(self, item: ScrapedItem) -> Optional[int]:
        """Save an item to the database."""
        if self._db:
            return self._db.save_item(item)
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get saved progress for resuming."""
        if self._db:
            return self._db.get_progress(self.source)
        return {"last_page": 0, "last_url": None}

    def save_progress(self, **kwargs) -> None:
        """Save progress for resuming."""
        if self._db:
            self._db.save_progress(self.source, **kwargs)

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def parse(self, response: Response) -> Iterator[Any]:
        """
        Default parse method - override in subclass.

        Should yield ScrapedItem instances.
        """
        raise NotImplementedError("Subclass must implement parse()")

    def extract_text(self, response: Response, selector: str) -> str:
        """Extract text from a CSS selector."""
        elements = response.css(selector)
        return " ".join(e.get().strip() for e in elements if e.get())

    def extract_all_text(self, response: Response) -> str:
        """Extract all visible text from page."""
        # Remove script and style elements
        body = response.css("body")
        if not body:
            return ""

        text_parts = []
        for elem in body.css("*:not(script):not(style)::text").getall():
            text = elem.strip()
            if text:
                text_parts.append(text)

        return " ".join(text_parts)


# =============================================================================
# Example Spider (for reference)
# =============================================================================

class ExampleSpider(BaseSpider):
    """
    Example spider showing how to use BaseSpider.

    To run:
        scrapy crawl example_spider
    """
    name = "example_spider"
    source = "example"
    start_urls = ["https://example.com"]

    def parse(self, response):
        """Parse a page."""
        title = response.css("title::text").get()
        content = self.extract_all_text(response)

        # Skip if already seen
        if self.content_seen(content):
            logger.debug(f"Skipping duplicate: {response.url}")
            return

        # Create item
        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata={"scraped_by": self.name},
        )

        # Save to database
        self.save_item(item)

        # Yield for Scrapy pipeline
        yield item

        # Follow links
        for href in response.css("a::attr(href)").getall():
            yield self.make_request(response.urljoin(href))
