"""
SAM Scraper System - Literotica Spider

Scrapes gay male stories from Literotica for training data.

ANTI-BOT MEASURES (updated 2026-01-28):
- User-Agent rotation with realistic browser signatures
- Random delays between requests (2-5 seconds)
- Referer header spoofing
- AutoThrottle enabled with adaptive delays
- Exponential backoff on 403/429 responses
- Cookie persistence for session handling
"""

import re
import random
import time
from typing import Dict, Any, Iterator

from scrapy.http import Request, Response
from scrapy.downloadermiddlewares.retry import get_retry_request

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


# Realistic User-Agents for rotation
USER_AGENTS = [
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class LiteroticaSpider(BaseSpider):
    """Spider for Literotica gay male stories.

    Includes enhanced anti-bot detection countermeasures:
    - Rotating User-Agents
    - Random request delays (2-5s)
    - Referer header spoofing
    - AutoThrottle with adaptive delays
    - Exponential backoff on rate limiting
    """

    name = "literotica_spider"
    source = "literotica"
    allowed_domains = ["literotica.com", "www.literotica.com"]

    rate_limit = 3.0  # Increased base delay

    # Track retry attempts for exponential backoff
    _retry_counts: Dict[str, int] = {}
    _last_request_time: float = 0

    custom_settings = {
        **BaseSpider.custom_settings,
        # Base delay with randomization
        "DOWNLOAD_DELAY": 3.0,
        "RANDOMIZE_DOWNLOAD_DELAY": True,  # Adds 0.5x to 1.5x randomization
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        # AutoThrottle for adaptive delays
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3.0,
        "AUTOTHROTTLE_MAX_DELAY": 30.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "AUTOTHROTTLE_DEBUG": False,
        # Retry configuration
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504, 408, 522, 524],
        # Cookie handling
        "COOKIES_ENABLED": True,
        "COOKIES_DEBUG": False,
        # Default headers
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            # Note: Don't request 'br' (Brotli) unless brotli library is installed
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
    }

    # Gay male category
    BASE_URL = "https://www.literotica.com"
    CATEGORY_URL = "/c/gay-male-stories"

    def __init__(self, *args, max_pages: int = 50, min_words: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max_pages
        self.min_words = min_words
        self._retry_counts = {}
        self._last_request_time = 0

    def _get_random_user_agent(self) -> str:
        """Get a random realistic User-Agent."""
        return random.choice(USER_AGENTS)

    def _get_random_delay(self) -> float:
        """Get a random delay between 2-5 seconds."""
        return random.uniform(2.0, 5.0)

    def _add_jitter_delay(self):
        """Add random jitter delay between requests."""
        elapsed = time.time() - self._last_request_time
        min_delay = self._get_random_delay()
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed + random.uniform(0.5, 1.5))
        self._last_request_time = time.time()

    def make_request(
        self,
        url: str,
        callback=None,
        meta: Dict[str, Any] = None,
        **kwargs
    ) -> Request:
        """Create a request with anti-bot headers and random User-Agent."""
        if callback is None:
            callback = self.parse

        if meta is None:
            meta = {}

        # Add retry tracking to meta
        meta.setdefault("retry_count", 0)

        # Build headers with random User-Agent and Referer
        headers = kwargs.get("headers", {})
        headers["User-Agent"] = self._get_random_user_agent()
        headers["Referer"] = f"{self.BASE_URL}/"

        # Add some browser-like headers
        headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        headers.setdefault("Accept-Encoding", "gzip, deflate, br")

        kwargs["headers"] = headers

        # Use dont_filter=False to allow Scrapy's deduplication
        kwargs.setdefault("dont_filter", False)

        return Request(url, callback=callback, meta=meta, errback=self.handle_error, **kwargs)

    def handle_error(self, failure):
        """Handle request errors with exponential backoff."""
        request = failure.request
        url = request.url

        # Get current retry count
        retry_count = request.meta.get("retry_count", 0)

        # Check if it's a rate limit or forbidden error
        if hasattr(failure.value, "response"):
            response = failure.value.response
            if response and response.status in [403, 429]:
                # Exponential backoff: 5s, 10s, 20s, 40s, 80s
                backoff_delay = min(5 * (2 ** retry_count), 120)
                self.logger.warning(
                    f"Got {response.status} for {url}. "
                    f"Backing off for {backoff_delay}s (retry {retry_count + 1})"
                )
                time.sleep(backoff_delay)

                # Retry with incremented count
                if retry_count < 5:
                    new_request = request.copy()
                    new_request.meta["retry_count"] = retry_count + 1
                    new_request.headers["User-Agent"] = self._get_random_user_agent()
                    return new_request

        self.logger.error(f"Failed to fetch {url}: {failure.value}")

    def start_requests(self) -> Iterator[Request]:
        """Start crawling the gay male category."""
        progress = self.get_progress()
        start_page = progress.get("last_page", 0) + 1

        url = f"{self.BASE_URL}{self.CATEGORY_URL}/{start_page}/"
        yield self.make_request(url, callback=self.parse_listing, meta={"page": start_page})

    def parse_listing(self, response: Response) -> Iterator[Any]:
        """Parse category listing page."""
        page = response.meta.get("page", 1)
        self.logger.info(f"Parsing listing page {page}")

        # Find story links
        stories = response.css("div.b-story-list-box")
        for story in stories:
            link = story.css("a.b-story-list-box__title::attr(href)").get()
            title = story.css("a.b-story-list-box__title::text").get()
            author = story.css("span.b-story-list-box__author a::text").get()

            if link and title:
                yield self.make_request(
                    link,
                    callback=self.parse_story,
                    meta={
                        "title": title.strip(),
                        "author": author.strip() if author else "Anonymous",
                    }
                )

        self.save_progress(last_page=page)

        # Next page
        if page < self.max_pages:
            next_url = f"{self.BASE_URL}{self.CATEGORY_URL}/{page + 1}/"
            yield self.make_request(
                next_url,
                callback=self.parse_listing,
                meta={"page": page + 1}
            )

    def parse_story(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse individual story page."""
        title = response.meta.get("title", "Untitled")
        author = response.meta.get("author", "Anonymous")

        self.logger.info(f"Parsing story: {title}")

        # Extract story text
        content_div = response.css("div.aa_ht")
        if not content_div:
            content_div = response.css("div.b-story-body-x")

        if not content_div:
            self.logger.warning(f"No content found: {response.url}")
            return

        paragraphs = content_div.css("p::text").getall()
        text = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        word_count = len(text.split())
        if word_count < self.min_words:
            self.logger.warning(f"Skipping {title}: only {word_count} words")
            return

        # Get tags/categories
        tags = response.css("a.av_as::text").getall()
        tags = [t.strip() for t in tags if t.strip()]
        tags.extend(["gay", "male", "literotica"])

        # Analysis
        analysis = self._analyze_content(text)

        metadata = {
            "author": author,
            "tags": tags,
            "character_count": analysis["character_count"],
            "has_dialogue": analysis["has_dialogue"],
            "pov": analysis["pov"],
            "content_intensity": analysis["content_intensity"],
            "relationship_type": analysis["relationship_type"],
            "quality_score": analysis["quality_score"],
        }

        yield ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=text,
            metadata=metadata,
        )

        # Check for multi-page stories
        next_page = response.css("a.b-pager-next::attr(href)").get()
        if next_page:
            yield self.make_request(
                next_page,
                callback=self.parse_story_continuation,
                meta={
                    "title": title,
                    "author": author,
                    "accumulated_text": text,
                }
            )

    def parse_story_continuation(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse continuation pages of multi-page stories."""
        title = response.meta.get("title")
        author = response.meta.get("author")
        accumulated = response.meta.get("accumulated_text", "")

        content_div = response.css("div.aa_ht, div.b-story-body-x")
        if content_div:
            paragraphs = content_div.css("p::text").getall()
            new_text = "\n\n".join(p.strip() for p in paragraphs if p.strip())
            accumulated += "\n\n" + new_text

        # Check for more pages
        next_page = response.css("a.b-pager-next::attr(href)").get()
        if next_page:
            yield self.make_request(
                next_page,
                callback=self.parse_story_continuation,
                meta={
                    "title": title,
                    "author": author,
                    "accumulated_text": accumulated,
                }
            )
        # Final page - don't yield again, already yielded first page

    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze content for metadata."""
        text_lower = text.lower()

        analysis = {
            "character_count": 2,
            "has_dialogue": text.count('"') > 20,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "quality_score": 0.5,
        }

        # POV
        first_person = len(re.findall(r'\bI\b', text))
        third_person = len(re.findall(r'\bhe\b', text_lower))
        if first_person > third_person * 1.5:
            analysis["pov"] = "first-person"

        # Intensity
        explicit_terms = ["cock", "dick", "fuck", "cum", "suck"]
        explicit_count = sum(text_lower.count(t) for t in explicit_terms)
        if explicit_count > 15:
            analysis["content_intensity"] = "explicit"
        elif explicit_count > 5:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Quality
        word_count = len(text.split())
        score = 0.5
        if word_count > 3000:
            score += 0.2
        if analysis["has_dialogue"]:
            score += 0.1
        analysis["quality_score"] = min(1.0, score)

        return analysis
