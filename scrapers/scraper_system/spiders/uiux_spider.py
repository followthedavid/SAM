"""
UI/UX Spider - Scrapes accessibility guidelines, design systems, and UI testing docs

Targets:
1. W3C/WAI accessibility guidelines (WCAG)
2. Apple/Google Human Interface Guidelines
3. Design system documentation (Material, Ant Design, etc.)
4. UI testing best practices
5. Screen reader documentation
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


class UIUXSpider(BaseSpider):
    """
    Spider for UI/UX documentation and accessibility guidelines.

    Important for training SAM to:
    - Understand UI patterns
    - Test accessibility
    - Validate user interfaces
    - Understand design systems

    Usage:
        scrapy crawl uiux
        scrapy crawl uiux -a site=wcag
    """

    name = "uiux_spider"
    source = "uiux"

    # Documentation sites
    SITES = {
        "wcag": {
            "name": "WCAG Accessibility Guidelines",
            "start_urls": [
                "https://www.w3.org/WAI/WCAG21/quickref/",
                "https://www.w3.org/WAI/fundamentals/accessibility-intro/",
                "https://www.w3.org/WAI/test-evaluate/",
                "https://www.w3.org/WAI/tutorials/",
            ],
            "allowed_domains": ["w3.org"],
            "content_selector": "main, article, #main",
            "max_depth": 2,
        },
        "mdn_a11y": {
            "name": "MDN Accessibility",
            "start_urls": [
                "https://developer.mozilla.org/en-US/docs/Web/Accessibility",
                "https://developer.mozilla.org/en-US/docs/Learn/Accessibility",
                "https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA",
            ],
            "allowed_domains": ["developer.mozilla.org"],
            "content_selector": "article, main",
            "max_depth": 2,
        },
        "material": {
            "name": "Material Design",
            "start_urls": [
                "https://m3.material.io/foundations",
                "https://m3.material.io/components",
                "https://m3.material.io/develop",
            ],
            "allowed_domains": ["m3.material.io", "material.io"],
            "content_selector": "main, article",
            "max_depth": 2,
        },
        "apple_hig": {
            "name": "Apple Human Interface Guidelines",
            "start_urls": [
                "https://developer.apple.com/design/human-interface-guidelines/",
            ],
            "allowed_domains": ["developer.apple.com"],
            "content_selector": "main, article, .content",
            "max_depth": 2,
        },
        "playwright_testing": {
            "name": "Playwright Testing",
            "start_urls": [
                "https://playwright.dev/docs/intro",
                "https://playwright.dev/docs/test-assertions",
                "https://playwright.dev/docs/accessibility-testing",
            ],
            "allowed_domains": ["playwright.dev"],
            "content_selector": "article, main",
            "max_depth": 2,
        },
        "testing_library": {
            "name": "Testing Library",
            "start_urls": [
                "https://testing-library.com/docs/",
                "https://testing-library.com/docs/queries/about",
                "https://testing-library.com/docs/guide-disappearance",
            ],
            "allowed_domains": ["testing-library.com"],
            "content_selector": "article, main",
            "max_depth": 2,
        },
        "deque": {
            "name": "Deque Accessibility",
            "start_urls": [
                "https://www.deque.com/web-accessibility-beginners-guide/",
                "https://www.deque.com/axe/",
            ],
            "allowed_domains": ["deque.com"],
            "content_selector": "main, article, .content",
            "max_depth": 2,
        },
        "a11y_project": {
            "name": "A11Y Project",
            "start_urls": [
                "https://www.a11yproject.com/checklist/",
                "https://www.a11yproject.com/posts/",
            ],
            "allowed_domains": ["a11yproject.com"],
            "content_selector": "main, article",
            "max_depth": 2,
        },
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, site: str = None, max_pages: int = 300, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

        if site:
            if site in self.SITES:
                self.sites = {site: self.SITES[site]}
            else:
                self.sites = self.SITES
        else:
            self.sites = self.SITES

    def start_requests(self) -> Iterator[Request]:
        """Start crawling UI/UX doc sites."""
        for site_id, config in self.sites.items():
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
        """Parse a UI/UX documentation page."""
        site_id = response.meta.get("site_id", "unknown")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)
        url = response.url

        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
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

                # Analyze for training categories
                content_lower = content.lower()

                is_accessibility = any(a11y in content_lower for a11y in [
                    "accessibility", "wcag", "aria", "screen reader",
                    "assistive", "a11y", "keyboard navigation",
                ])

                is_design_system = any(ds in content_lower for ds in [
                    "component", "button", "input", "form", "layout",
                    "typography", "color", "spacing", "design token",
                ])

                is_testing = any(test in content_lower for test in [
                    "test", "assert", "expect", "selector", "query",
                    "screenshot", "visual", "automation",
                ])

                has_code_examples = "```" in content or "<code" in raw_html

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": "uiux_docs",
                        "author": config.get("name", site_id),
                        "site": site_id,
                        "site_name": config.get("name", ""),
                        "depth": depth,
                        "is_accessibility": is_accessibility,
                        "is_design_system": is_design_system,
                        "is_testing": is_testing,
                        "has_code_examples": has_code_examples,
                    }
                )

        # Follow links
        max_depth = config.get("max_depth", 2)
        if depth < max_depth:
            allowed_domains = config.get("allowed_domains", [])

            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                if parsed.netloc and not any(d in parsed.netloc for d in allowed_domains):
                    continue

                if full_url in self.visited_urls:
                    continue

                if any(full_url.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.pdf', '.zip']):
                    continue

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
        """Convert HTML to text."""
        if not html_content:
            return ""

        text = html_content

        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)

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
        "name": "uiux",
        "spider_class": UIUXSpider,
        "description": "UI/UX & Accessibility Docs",
        "type": "code",
        "priority": 2,
    }
