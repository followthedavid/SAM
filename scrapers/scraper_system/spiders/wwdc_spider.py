"""
WWDC Spider - Scrapes WWDC session transcripts and notes

Targets:
1. Apple WWDC session videos (developer.apple.com/videos)
2. WWDC Notes community transcripts (wwdcnotes.com)
3. ASCIIwwdc transcripts (asciiwwdc.com)

Critical for understanding Apple's latest APIs and announcements.
"""

import json
import logging
import html
import re
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class WWDCSpider(BaseSpider):
    """
    Spider for WWDC session transcripts and notes.

    Covers:
    - Official Apple WWDC session pages
    - Community-maintained transcripts
    - Session notes and summaries

    Usage:
        scrapy crawl wwdc
        scrapy crawl wwdc -a year=2024
    """

    name = "wwdc_spider"
    source = "wwdc"

    # WWDC content sources
    SOURCES = {
        "apple_videos": {
            "name": "Apple WWDC Videos",
            "start_urls": [
                "https://developer.apple.com/videos/",
                "https://developer.apple.com/videos/wwdc2024/",
                "https://developer.apple.com/videos/wwdc2023/",
                "https://developer.apple.com/videos/wwdc2022/",
                "https://developer.apple.com/videos/wwdc2021/",
            ],
            "allowed_domains": ["developer.apple.com"],
            "content_selector": "main, article, .content",
            "max_depth": 2,
            "priority": 1,
        },
        "wwdcnotes": {
            "name": "WWDC Notes",
            "start_urls": [
                "https://www.wwdcnotes.com/",
                "https://www.wwdcnotes.com/notes/wwdc24/",
                "https://www.wwdcnotes.com/notes/wwdc23/",
                "https://www.wwdcnotes.com/notes/wwdc22/",
            ],
            "allowed_domains": ["wwdcnotes.com"],
            "content_selector": "article, main, .content",
            "max_depth": 3,
            "priority": 1,
        },
        "asciiwwdc": {
            "name": "ASCII WWDC",
            "start_urls": [
                "https://asciiwwdc.com/",
            ],
            "allowed_domains": ["asciiwwdc.com"],
            "content_selector": "article, main, .content, .session",
            "max_depth": 2,
            "priority": 2,
        },
    }

    # Topic categories for classification
    TOPIC_PATTERNS = {
        "swiftui": ["swiftui", "declarative ui", "@state", "@binding"],
        "swift": ["swift language", "swift 5", "swift 6", "swift concurrency"],
        "visionos": ["visionos", "spatial computing", "vision pro", "realitykit"],
        "ai_ml": ["machine learning", "core ml", "create ml", "ai", "intelligence"],
        "accessibility": ["accessibility", "voiceover", "assistive"],
        "testing": ["testing", "xctest", "ui testing", "test plan"],
        "performance": ["performance", "optimization", "instruments"],
        "networking": ["networking", "urlsession", "http"],
        "security": ["security", "privacy", "keychain", "authentication"],
        "appstore": ["app store", "in-app purchase", "storekit"],
        "xcode": ["xcode", "debugging", "simulator", "previews"],
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, year: str = None, source: str = None,
                 max_pages: int = 1500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()
        self.target_year = year

        # Filter to specific source
        if source:
            if source in self.SOURCES:
                self.sources = {source: self.SOURCES[source]}
            else:
                self.sources = self.SOURCES
        else:
            self.sources = self.SOURCES

    def start_requests(self) -> Iterator[Request]:
        """Start crawling WWDC content sources."""
        sorted_sources = sorted(
            self.sources.items(),
            key=lambda x: x[1].get("priority", 99)
        )

        for source_id, config in sorted_sources:
            for url in config["start_urls"]:
                # Filter by year if specified
                if self.target_year and self.target_year not in url:
                    # Only skip year-specific URLs
                    if any(f"wwdc{y}" in url for y in ["2024", "2023", "2022", "2021", "2020"]):
                        continue

                yield self.make_request(
                    url,
                    callback=self.parse_page,
                    meta={
                        "source_id": source_id,
                        "config": config,
                        "depth": 0,
                    }
                )

    def parse_page(self, response: Response) -> Iterator:
        """Parse a WWDC content page."""
        source_id = response.meta.get("source_id", "unknown")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)
        url = response.url

        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
            return

        # Check database
        if self._db and self._db.url_exists(url):
            return

        # Extract content
        content_selector = config.get("content_selector", "main, article")
        content_elem = response.css(content_selector)

        if content_elem:
            raw_html = content_elem.get()
            content = self._clean_html(raw_html)

            if content and len(content) > 200:
                self.pages_scraped += 1

                title = response.css("title::text").get() or ""
                title = title.strip()

                # Extract year from URL or content
                year = self._extract_year(url, content)

                # Detect topics
                content_lower = content.lower()
                topics = []
                for topic, markers in self.TOPIC_PATTERNS.items():
                    if any(m in content_lower for m in markers):
                        topics.append(topic)

                # Session number if present
                session_match = re.search(r'(?:session|wwdc\d{2})[-_]?(\d{3,5})', url.lower())
                session_number = session_match.group(1) if session_match else None

                # Content type detection
                is_transcript = any(trans in content_lower for trans in [
                    "transcript", ">>", "speaker:", "[applause]",
                    "good morning", "good afternoon", "welcome to",
                ])

                is_notes = any(note in content_lower for note in [
                    "notes", "summary", "key takeaways", "highlights",
                    "overview", "tl;dr",
                ])

                has_code = "```" in content or "func " in content or "class " in content

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": "wwdc",
                        "author": config.get("name", source_id),
                        "source_site": source_id,
                        "year": year,
                        "session_number": session_number,
                        "topics": topics,
                        "is_transcript": is_transcript,
                        "is_notes": is_notes,
                        "has_code": has_code,
                        "depth": depth,
                    }
                )

        # Follow links
        max_depth = config.get("max_depth", 2)
        if depth < max_depth:
            allowed_domains = config.get("allowed_domains", [])

            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                # Check domain
                if parsed.netloc and not any(d in parsed.netloc for d in allowed_domains):
                    continue

                # Skip visited
                if full_url in self.visited_urls:
                    continue

                # Skip non-content
                skip_patterns = [
                    "/download", "/subscribe", "/login", "/account",
                    ".zip", ".pdf", ".mp4", ".mov",
                    "/forums", "/feedback",
                ]
                if any(p in full_url.lower() for p in skip_patterns):
                    continue

                # Filter by year if specified
                if self.target_year:
                    # Allow URLs that don't have year, or match target year
                    has_year = any(f"wwdc{y}" in full_url.lower() or f"/{y}/" in full_url
                                  for y in ["2024", "2023", "2022", "2021", "2020"])
                    if has_year and self.target_year not in full_url:
                        continue

                # Prefer session/video/notes URLs
                good_patterns = [
                    "/videos/", "/play/", "/notes/", "/session",
                    "/wwdc", "/watch/", "/transcript",
                ]
                if any(p in full_url.lower() for p in good_patterns):
                    yield self.make_request(
                        full_url,
                        callback=self.parse_page,
                        meta={
                            "source_id": source_id,
                            "config": config,
                            "depth": depth + 1,
                        }
                    )

    def _extract_year(self, url: str, content: str) -> Optional[str]:
        """Extract WWDC year from URL or content."""
        # Try URL first
        year_match = re.search(r'wwdc[_-]?(\d{2,4})', url.lower())
        if year_match:
            year = year_match.group(1)
            if len(year) == 2:
                year = "20" + year
            return year

        # Try content
        for year in ["2024", "2023", "2022", "2021", "2020", "2019"]:
            if f"WWDC {year}" in content or f"WWDC{year}" in content:
                return year

        return None

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to text."""
        if not html_content:
            return ""

        text = html_content

        # Remove non-content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)

        # Convert code blocks
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
                     r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<pre[^>]*>(.*?)</pre>',
                     r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

        # Convert headers
        for i in range(1, 7):
            text = re.sub(f'<h{i}[^>]*>(.*?)</h{i}>',
                         lambda m, level=i: '#' * level + ' ' + m.group(1) + '\n',
                         text, flags=re.DOTALL)

        # Convert links
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text)

        # Convert lists
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
        text = re.sub(r'<[uo]l[^>]*>', '\n', text)
        text = re.sub(r'</[uo]l>', '\n', text)

        # Convert paragraphs
        text = re.sub(r'<p[^>]*>', '\n\n', text)
        text = re.sub(r'</p>', '', text)
        text = re.sub(r'<br\s*/?>', '\n', text)

        # Bold/italic
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text)
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text)

        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)

        # Unescape
        text = html.unescape(text)

        # Clean whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()


def register():
    return {
        "name": "wwdc",
        "spider_class": WWDCSpider,
        "description": "WWDC Session Transcripts",
        "type": "code",
        "priority": 1,
    }
