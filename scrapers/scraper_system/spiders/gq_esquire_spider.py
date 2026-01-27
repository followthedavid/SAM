"""
SAM Scraper System - GQ & Esquire Magazine Spider

Scrapes fashion, culture, and lifestyle articles from GQ and Esquire.
Focus on interviews, profiles, and longform content.
"""

import re
import hashlib
from typing import Dict, Any, Optional, Iterator, List
from urllib.parse import urljoin

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class GQSpider(BaseSpider):
    """
    Spider for GQ Magazine.

    Features:
    - Section-based crawling
    - Interview and profile detection
    - Quote extraction for dialogue training
    """

    name = "gq_spider"
    source = "gq"
    allowed_domains = ["gq.com"]

    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    # GQ sections to scrape
    SECTIONS = {
        "style": "https://www.gq.com/style",
        "culture": "https://www.gq.com/culture",
        "grooming": "https://www.gq.com/grooming",
        "lifestyle": "https://www.gq.com/lifestyle",
        "story": "https://www.gq.com/story",
    }

    def __init__(self, *args, section: str = None, max_pages: int = 50,
                 interviews_only: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_section = section
        self.max_pages = max_pages
        self.interviews_only = interviews_only
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start crawling sections."""
        progress = self.get_progress()
        self.articles_scraped = progress.get("total_items", 0)

        sections = {self.target_section: self.SECTIONS[self.target_section]} \
            if self.target_section and self.target_section in self.SECTIONS \
            else self.SECTIONS

        for section, url in sections.items():
            yield self.make_request(
                url,
                callback=self.parse_section,
                meta={"section": section, "page": 1}
            )

    def parse_section(self, response: Response) -> Iterator[Request]:
        """Parse a section page to find articles."""
        section = response.meta.get("section")
        page = response.meta.get("page", 1)

        self.logger.info(f"Parsing GQ/{section} page {page}")

        # Find article cards
        cards = response.css(
            "article, [class*='summary-item'], [class*='card'], [class*='river-item']"
        )

        if not cards:
            cards = response.css("a[href*='/story/'], a[href*='/gq/']")

        articles_found = 0
        for card in cards:
            # Get URL
            link = card.css("a[href*='/story/']::attr(href), a[href]::attr(href)").get()
            if not link:
                continue

            url = urljoin("https://www.gq.com", link)

            # Skip non-articles
            if "/video/" in url or "/gallery/" in url:
                continue

            # Get title for interview detection
            title = card.css("h2 ::text, h3 ::text, .headline ::text").get()
            if not title:
                title = card.css("a ::text").get() or ""
            title = title.strip()

            # Check for interview content
            is_interview = self._is_interview(title)

            if self.interviews_only and not is_interview:
                continue

            yield self.make_request(
                url,
                callback=self.parse_article,
                meta={
                    "section": section,
                    "title_hint": title,
                    "is_interview": is_interview,
                }
            )
            articles_found += 1

        # Paginate
        if articles_found > 0 and page < self.max_pages:
            next_url = f"{self.SECTIONS.get(section)}?page={page + 1}"
            yield self.make_request(
                next_url,
                callback=self.parse_section,
                meta={"section": section, "page": page + 1}
            )

    def _is_interview(self, text: str) -> bool:
        """Check if content appears to be an interview."""
        if not text:
            return False

        text_lower = text.lower()
        keywords = [
            "interview", "q&a", "q & a", "talks to", "speaks to",
            "sits down with", "conversation with", "chat with",
            "we asked", "we talked", "told us", "says to us"
        ]
        return any(kw in text_lower for kw in keywords)

    def _has_quotes(self, text: str) -> bool:
        """Check for substantial quotes/dialogue."""
        quotes = re.findall(r'"[^"]{20,}"', text)
        return len(quotes) >= 3

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse an article page."""
        section = response.meta.get("section", "")
        is_interview = response.meta.get("is_interview", False)

        # Extract title
        title = response.css("h1 ::text").get()
        if not title:
            return
        title = title.strip()

        # Extract author
        author = response.css("a.author-name ::text, span.author ::text, .byline ::text").get()
        if author:
            author = re.sub(r"^by\s+", "", author.strip(), flags=re.I)

        # Extract content
        body = response.css("article .body, .article-body, [class*='article-body']")
        if not body:
            body = response.css("article")
        if not body:
            return

        paragraphs = body.css("p ::text").getall()
        content = "\n\n".join(p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20)

        if len(content.split()) < 200:
            return

        # Re-check for interview content
        is_interview = is_interview or self._is_interview(content)
        has_quotes = self._has_quotes(content)

        # Extract tags
        tags = response.css("[class*='tag'] a ::text, .tags a ::text").getall()
        tags = [t.strip() for t in tags if t.strip()]

        metadata = {
            "author": author,
            "section": section,
            "is_interview": is_interview,
            "has_quotes": has_quotes,
            "word_count": len(content.split()),
            "tags": tags + ["fashion", "culture", "gq"],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata=metadata,
        )

        self.articles_scraped += 1
        self.save_progress(total_items=self.articles_scraped)

        yield item


class EsquireSpider(BaseSpider):
    """
    Spider for Esquire Magazine.

    Similar structure to GQ - focuses on culture, style, interviews.
    """

    name = "esquire_spider"
    source = "esquire"
    allowed_domains = ["esquire.com"]

    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    SECTIONS = {
        "style": "https://www.esquire.com/style",
        "entertainment": "https://www.esquire.com/entertainment",
        "lifestyle": "https://www.esquire.com/lifestyle",
        "news-politics": "https://www.esquire.com/news-politics",
        "food-drink": "https://www.esquire.com/food-drink",
    }

    def __init__(self, *args, section: str = None, max_pages: int = 50, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_section = section
        self.max_pages = max_pages
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start crawling sections."""
        sections = {self.target_section: self.SECTIONS[self.target_section]} \
            if self.target_section and self.target_section in self.SECTIONS \
            else self.SECTIONS

        for section, url in sections.items():
            yield self.make_request(
                url,
                callback=self.parse_section,
                meta={"section": section, "page": 1}
            )

    def parse_section(self, response: Response) -> Iterator[Request]:
        """Parse section page."""
        section = response.meta.get("section")
        page = response.meta.get("page", 1)

        self.logger.info(f"Parsing Esquire/{section} page {page}")

        cards = response.css(
            "article, [class*='summary-item'], [class*='card']"
        )

        articles_found = 0
        for card in cards:
            link = card.css("a[href*='/a/']::attr(href), a[href]::attr(href)").get()
            if not link:
                continue

            url = urljoin("https://www.esquire.com", link)

            if "/video/" in url or "/gallery/" in url:
                continue

            yield self.make_request(
                url,
                callback=self.parse_article,
                meta={"section": section}
            )
            articles_found += 1

        if articles_found > 0 and page < self.max_pages:
            next_url = f"{self.SECTIONS.get(section)}?page={page + 1}"
            yield self.make_request(
                next_url,
                callback=self.parse_section,
                meta={"section": section, "page": page + 1}
            )

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse article page."""
        section = response.meta.get("section", "")

        title = response.css("h1 ::text").get()
        if not title:
            return
        title = title.strip()

        author = response.css(".byline ::text, [class*='author'] ::text").get()
        if author:
            author = re.sub(r"^by\s+", "", author.strip(), flags=re.I)

        body = response.css("article .body, .article-body, article")
        if not body:
            return

        paragraphs = body.css("p ::text").getall()
        content = "\n\n".join(p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20)

        if len(content.split()) < 200:
            return

        metadata = {
            "author": author,
            "section": section,
            "word_count": len(content.split()),
            "tags": ["fashion", "culture", "esquire", section],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata=metadata,
        )

        self.articles_scraped += 1
        yield item
