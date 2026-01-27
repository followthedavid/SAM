"""
SAM Scraper System - The Cut (New York Magazine) Spider

Scrapes personal essays, relationship content, and first-person narratives.
Focus on feminine voice training data.
"""

import re
import hashlib
from typing import Dict, Any, Optional, Iterator, List
from urllib.parse import urljoin

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class TheCutSpider(BaseSpider):
    """
    Spider for The Cut (NY Magazine).

    Features:
    - Personal essays and first-person content
    - Relationship and dating content
    - Advice columns (Ask Polly, Sex Diaries)
    - Dialogue-heavy content detection
    """

    name = "thecut_spider"
    source = "thecut"
    allowed_domains = ["thecut.com"]

    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    # Sections focused on personal/relationship content
    SECTIONS = {
        # Core personal content
        "love-sex": "https://www.thecut.com/tags/love-and-dating/",
        "relationships": "https://www.thecut.com/tags/relationships/",
        "sex": "https://www.thecut.com/tags/sex/",
        "self": "https://www.thecut.com/self/",
        # Essays and first-person
        "essays": "https://www.thecut.com/tags/essays/",
        "personal-essays": "https://www.thecut.com/tags/personal-essays/",
        "first-person": "https://www.thecut.com/tags/first-person/",
        # Specific columns
        "ask-polly": "https://www.thecut.com/tags/ask-polly/",
        "sex-diaries": "https://www.thecut.com/tags/sex-diaries/",
        "how-i-get-it-done": "https://www.thecut.com/tags/how-i-get-it-done/",
    }

    def __init__(self, *args, section: str = None, max_pages: int = 100,
                 first_person_only: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_section = section
        self.max_pages = max_pages
        self.first_person_only = first_person_only
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

        self.logger.info(f"Parsing TheCut/{section} page {page}")

        # Find article cards
        cards = response.css(
            "article, [class*='feed-item'], [class*='story'], [class*='article-item']"
        )

        if not cards:
            cards = response.css("[class*='river'] > div, [class*='stream'] > div")

        articles_found = 0
        for card in cards:
            link = card.css("a[href*='/article/']::attr(href), a[href]::attr(href)").get()
            if not link:
                continue

            url = urljoin("https://www.thecut.com", link)

            if "/video/" in url or "/slideshow/" in url:
                continue

            # Get metadata from card
            title = card.css("h2 ::text, h3 ::text, h4 ::text, .headline ::text").get()
            if not title:
                title = card.css("a ::text").get() or ""
            title = title.strip()

            if len(title) < 10:
                continue

            # Detect content type from title
            content_type = self._detect_content_type(title, url)

            if self.first_person_only and not content_type.get("is_first_person"):
                continue

            yield self.make_request(
                url,
                callback=self.parse_article,
                meta={
                    "section": section,
                    "content_type": content_type,
                    "title_hint": title,
                }
            )
            articles_found += 1

        # Paginate
        if articles_found > 0 and page < self.max_pages:
            if "/tags/" in self.SECTIONS.get(section, ""):
                next_url = f"{self.SECTIONS.get(section)}?page={page + 1}"
            else:
                next_url = f"{self.SECTIONS.get(section)}?p={page + 1}"

            yield self.make_request(
                next_url,
                callback=self.parse_section,
                meta={"section": section, "page": page + 1}
            )

    def _detect_content_type(self, title: str, url: str) -> Dict[str, bool]:
        """Detect content type from title and URL."""
        combined = f"{title} {url}".lower()

        return {
            "is_first_person": any(kw in combined for kw in [
                "i ", "my ", "me ", "first-person", "personal essay",
                "diary", "how i", "what i", "why i"
            ]),
            "is_advice": any(kw in combined for kw in [
                "advice", "ask polly", "how to", "should i", "help",
                "tips", "guide", "what to do"
            ]),
            "is_diary": any(kw in combined for kw in [
                "diary", "sex diary", "diaries", "day in the life"
            ]),
            "is_interview": any(kw in combined for kw in [
                "interview", "q&a", "conversation", "talks", "says"
            ]),
        }

    def _detect_column(self, url: str, title: str) -> str:
        """Detect which column an article belongs to."""
        url_lower = url.lower()
        title_lower = title.lower()

        if "ask-polly" in url_lower or "ask polly" in title_lower:
            return "Ask Polly"
        if "sex-diaries" in url_lower or "sex diary" in title_lower:
            return "Sex Diaries"
        if "how-i-get-it-done" in url_lower:
            return "How I Get It Done"

        return ""

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse an article page."""
        section = response.meta.get("section", "")
        content_type = response.meta.get("content_type", {})

        # Extract title
        title = response.css("h1 ::text").get()
        if not title:
            return
        title = title.strip()

        # Extract author
        author = response.css(".byline ::text, [class*='author'] ::text").get()
        if author:
            author = re.sub(r"^by\s+", "", author.strip(), flags=re.I)

        # Extract content
        body = response.css("article .body, .article-body, [class*='article-content']")
        if not body:
            body = response.css("article")
        if not body:
            return

        paragraphs = body.css("p ::text").getall()
        content = "\n\n".join(p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20)

        word_count = len(content.split())
        if word_count < 300:
            return

        # Re-analyze content for type detection
        content_lower = content.lower()
        is_first_person = content.count(" I ") > 5 or content_lower.startswith("i ")
        has_dialogue = len(re.findall(r'"[^"]{15,}"', content)) >= 2

        # Detect column
        column = self._detect_column(response.url, title)

        # Extract tags
        tags = response.css("[class*='tag'] a ::text, .tags a ::text, [class*='topics'] a ::text").getall()
        tags = list(set(t.strip() for t in tags if t.strip()))

        metadata = {
            "author": author,
            "section": section,
            "column": column,
            "is_first_person": is_first_person or content_type.get("is_first_person", False),
            "is_advice": content_type.get("is_advice", False),
            "is_diary": content_type.get("is_diary", False),
            "has_dialogue": has_dialogue,
            "word_count": word_count,
            "tags": tags + ["personal", "essays", "thecut"],
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
