"""
Swift Community Spider - Tutorials and Articles from Swift Community Sites

Targets:
1. Hacking with Swift (hackingwithswift.com)
2. Swift by Sundell (swiftbysundell.com)
3. Ray Wenderlich / Kodeco (kodeco.com)
4. Swift.org official docs
5. NSHipster

Critical for learning Swift patterns and best practices.
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


class SwiftCommunitySpider(BaseSpider):
    """
    Spider for Swift community tutorials and articles.

    Focuses on:
    - Beginner-friendly tutorials
    - SwiftUI guides
    - iOS/macOS development patterns
    - Swift language features

    Usage:
        scrapy crawl swift_community
        scrapy crawl swift_community -a site=hackingwithswift
    """

    name = "swift_community_spider"
    source = "swift_community"

    # Community sites configuration
    SITES = {
        "hackingwithswift": {
            "name": "Hacking with Swift",
            "start_urls": [
                "https://www.hackingwithswift.com/quick-start/swiftui",
                "https://www.hackingwithswift.com/quick-start/beginners",
                "https://www.hackingwithswift.com/100/swiftui",
                "https://www.hackingwithswift.com/articles",
                "https://www.hackingwithswift.com/example-code",
            ],
            "allowed_domains": ["hackingwithswift.com"],
            "content_selector": "article, .content-wrapper, main",
            "max_depth": 3,
            "priority": 1,
        },
        "swiftbysundell": {
            "name": "Swift by Sundell",
            "start_urls": [
                "https://www.swiftbysundell.com/articles/",
                "https://www.swiftbysundell.com/tips/",
                "https://www.swiftbysundell.com/basics/",
            ],
            "allowed_domains": ["swiftbysundell.com"],
            "content_selector": "article, main, .content",
            "max_depth": 2,
            "priority": 1,
        },
        "kodeco": {
            "name": "Kodeco (Ray Wenderlich)",
            "start_urls": [
                "https://www.kodeco.com/ios/paths",
                "https://www.kodeco.com/swift",
                "https://www.kodeco.com/swiftui",
            ],
            "allowed_domains": ["kodeco.com"],
            "content_selector": "article, main, .content",
            "max_depth": 2,
            "priority": 2,
        },
        "swiftorg": {
            "name": "Swift.org",
            "start_urls": [
                "https://www.swift.org/documentation/",
                "https://www.swift.org/getting-started/",
                "https://www.swift.org/documentation/api-design-guidelines/",
                "https://www.swift.org/blog/",
            ],
            "allowed_domains": ["swift.org"],
            "content_selector": "main, article, .content",
            "max_depth": 2,
            "priority": 1,
        },
        "nshipster": {
            "name": "NSHipster",
            "start_urls": [
                "https://nshipster.com/",
            ],
            "allowed_domains": ["nshipster.com"],
            "content_selector": "article, main",
            "max_depth": 2,
            "priority": 2,
        },
        "appcoda": {
            "name": "AppCoda",
            "start_urls": [
                "https://www.appcoda.com/category/swift-programming/",
                "https://www.appcoda.com/category/swiftui/",
                "https://www.appcoda.com/category/ios-programming/",
            ],
            "allowed_domains": ["appcoda.com"],
            "content_selector": "article, main, .entry-content",
            "max_depth": 2,
            "priority": 2,
        },
        "donnywals": {
            "name": "Donny Wals",
            "start_urls": [
                "https://www.donnywals.com/the-blog/",
            ],
            "allowed_domains": ["donnywals.com"],
            "content_selector": "article, main, .entry-content",
            "max_depth": 2,
            "priority": 2,
        },
        "avanderlee": {
            "name": "SwiftLee",
            "start_urls": [
                "https://www.avanderlee.com/",
            ],
            "allowed_domains": ["avanderlee.com"],
            "content_selector": "article, main, .entry-content",
            "max_depth": 2,
            "priority": 2,
        },
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, site: str = None, max_pages: int = 2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

        # Filter to specific site or scrape all
        if site:
            if site in self.SITES:
                self.sites = {site: self.SITES[site]}
            else:
                logger.warning(f"Unknown site '{site}', scraping all")
                self.sites = self.SITES
        else:
            self.sites = self.SITES

    def start_requests(self) -> Iterator[Request]:
        """Start crawling Swift community sites."""
        # Sort by priority
        sorted_sites = sorted(
            self.sites.items(),
            key=lambda x: x[1].get("priority", 99)
        )

        for site_id, config in sorted_sites:
            for url in config["start_urls"]:
                yield self.make_request(
                    url,
                    callback=self.parse_page,
                    meta={
                        "site_id": site_id,
                        "config": config,
                        "depth": 0,
                    }
                )

    def parse_page(self, response: Response) -> Iterator:
        """Parse a Swift community page."""
        site_id = response.meta.get("site_id", "unknown")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)
        url = response.url

        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
            return

        # Check if already in database
        if self._db and self._db.url_exists(url):
            return

        # Extract content
        content_selector = config.get("content_selector", "main, article")
        content_elem = response.css(content_selector)

        if content_elem:
            raw_html = content_elem.get()
            content = self._clean_html(raw_html)

            if content and len(content) > 300:
                self.pages_scraped += 1

                title = response.css("title::text").get() or ""
                title = title.strip()
                # Clean up title
                for sep in [" | ", " - ", " :: ", " — "]:
                    if sep in title:
                        title = title.split(sep)[0].strip()

                # Analyze content
                content_lower = content.lower()

                # Tutorial markers
                is_tutorial = any(tut in content_lower for tut in [
                    "step 1", "step 2", "how to", "let's",
                    "tutorial", "guide", "getting started",
                    "in this article", "in this tutorial",
                ])

                # Code presence
                has_code = "```" in content or "func " in content or "var " in content

                # Topic detection
                topics = []
                topic_markers = {
                    "swiftui": ["swiftui", "@state", "@binding", "@observable"],
                    "uikit": ["uikit", "uiviewcontroller", "uiview", "uicollectionview"],
                    "combine": ["combine", "publisher", "subscriber", "@published"],
                    "async": ["async", "await", "task {", "actor"],
                    "networking": ["urlsession", "networking", "api call", "fetch data"],
                    "coredata": ["core data", "coredata", "nsmanagedobject"],
                    "swiftdata": ["swiftdata", "@model", "@query"],
                    "testing": ["xctest", "testing", "unit test", "ui test"],
                    "animation": ["animation", "withanimation", "transition"],
                    "navigation": ["navigation", "navigationstack", "navigationlink"],
                }

                for topic, markers in topic_markers.items():
                    if any(m in content_lower for m in markers):
                        topics.append(topic)

                # Difficulty detection
                is_beginner = any(beg in content_lower for beg in [
                    "beginner", "introduction", "basics", "getting started",
                    "first app", "learn", "101", "for beginners",
                ])

                is_advanced = any(adv in content_lower for adv in [
                    "advanced", "deep dive", "under the hood", "internals",
                    "performance", "optimization", "architecture",
                ])

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": "swift_tutorial",
                        "author": config.get("name", site_id),
                        "site": site_id,
                        "site_name": config.get("name", ""),
                        "depth": depth,
                        "is_tutorial": is_tutorial,
                        "has_code": has_code,
                        "topics": topics,
                        "is_beginner": is_beginner,
                        "is_advanced": is_advanced,
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
                    "/tag/", "/category/", "/author/", "/page/",
                    "/cart", "/checkout", "/login", "/register",
                    ".zip", ".pdf", ".png", ".jpg", ".gif",
                    "/feed", "/rss", "/comments",
                ]
                if any(p in full_url.lower() for p in skip_patterns):
                    continue

                # Prefer article/tutorial URLs
                good_patterns = [
                    "/article", "/tutorial", "/guide", "/quick-start",
                    "/100/", "/example", "/tip", "/basic",
                    "/swiftui", "/swift", "/ios", "/macos",
                ]
                if any(p in full_url.lower() for p in good_patterns):
                    yield self.make_request(
                        full_url,
                        callback=self.parse_page,
                        meta={
                            "site_id": site_id,
                            "config": config,
                            "depth": depth + 1,
                        }
                    )

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to markdown-ish text."""
        if not html_content:
            return ""

        text = html_content

        # Remove script/style/nav
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
        text = re.sub(r'<aside[^>]*>.*?</aside>', '', text, flags=re.DOTALL)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)

        # Convert code blocks - detect Swift
        text = re.sub(r'<pre[^>]*><code[^>]*class="[^"]*swift[^"]*"[^>]*>(.*?)</code></pre>',
                     r'```swift\n\1\n```', text, flags=re.DOTALL)
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
        "name": "swift_community",
        "spider_class": SwiftCommunitySpider,
        "description": "Swift Community Tutorials",
        "type": "code",
        "priority": 1,
    }
