"""
Apple Developer Documentation Spider

Targets:
1. Apple Developer Documentation (developer.apple.com/documentation)
2. Human Interface Guidelines
3. Sample Code
4. WWDC Session Notes
5. Technical Notes and Q&A

Critical for building Apple-exclusive app store builder.
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


class AppleDevSpider(BaseSpider):
    """
    Spider for Apple Developer Documentation.

    Covers:
    - Swift/SwiftUI/UIKit documentation
    - visionOS, watchOS, tvOS, macOS, iOS APIs
    - Sample code and tutorials
    - Human Interface Guidelines

    Usage:
        scrapy crawl apple_dev
        scrapy crawl apple_dev -a framework=swiftui
    """

    name = "apple_dev_spider"
    source = "apple_dev"

    # Apple Developer Documentation structure
    DOC_SECTIONS = {
        # Core Frameworks
        "swiftui": {
            "name": "SwiftUI",
            "urls": [
                "https://developer.apple.com/documentation/swiftui",
                "https://developer.apple.com/tutorials/swiftui",
                "https://developer.apple.com/documentation/swiftui/views",
                "https://developer.apple.com/documentation/swiftui/app-structure-and-behavior",
            ],
            "priority": 1,
        },
        "uikit": {
            "name": "UIKit",
            "urls": [
                "https://developer.apple.com/documentation/uikit",
                "https://developer.apple.com/documentation/uikit/views_and_controls",
                "https://developer.apple.com/documentation/uikit/view_controllers",
            ],
            "priority": 1,
        },
        "appkit": {
            "name": "AppKit",
            "urls": [
                "https://developer.apple.com/documentation/appkit",
                "https://developer.apple.com/documentation/appkit/views_and_controls",
            ],
            "priority": 2,
        },
        # Platform-specific
        "visionos": {
            "name": "visionOS",
            "urls": [
                "https://developer.apple.com/documentation/visionos",
                "https://developer.apple.com/documentation/realitykit",
                "https://developer.apple.com/documentation/arkit",
                "https://developer.apple.com/visionos/",
            ],
            "priority": 1,
        },
        "watchos": {
            "name": "watchOS",
            "urls": [
                "https://developer.apple.com/documentation/watchos-apps",
                "https://developer.apple.com/documentation/watchkit",
            ],
            "priority": 2,
        },
        # Data & Storage
        "swiftdata": {
            "name": "SwiftData",
            "urls": [
                "https://developer.apple.com/documentation/swiftdata",
                "https://developer.apple.com/tutorials/develop-in-swift/save-data",
            ],
            "priority": 1,
        },
        "coredata": {
            "name": "Core Data",
            "urls": [
                "https://developer.apple.com/documentation/coredata",
            ],
            "priority": 2,
        },
        # App Distribution
        "appstore": {
            "name": "App Store",
            "urls": [
                "https://developer.apple.com/documentation/storekit",
                "https://developer.apple.com/documentation/appstoreconnectapi",
                "https://developer.apple.com/app-store/review/guidelines/",
                "https://developer.apple.com/app-store/",
            ],
            "priority": 1,
        },
        # Development Tools
        "xcode": {
            "name": "Xcode",
            "urls": [
                "https://developer.apple.com/documentation/xcode",
                "https://developer.apple.com/documentation/xcode/building-and-running-an-app",
                "https://developer.apple.com/documentation/xcode/debugging",
            ],
            "priority": 1,
        },
        "xctest": {
            "name": "XCTest",
            "urls": [
                "https://developer.apple.com/documentation/xctest",
                "https://developer.apple.com/documentation/xctest/user_interface_tests",
                "https://developer.apple.com/documentation/xctestextensioninfoplistkeys",
            ],
            "priority": 1,
        },
        # Swift Language
        "swift": {
            "name": "Swift",
            "urls": [
                "https://developer.apple.com/documentation/swift",
                "https://developer.apple.com/swift/",
                "https://developer.apple.com/documentation/swift/swift-standard-library",
            ],
            "priority": 1,
        },
        # Networking
        "networking": {
            "name": "Networking",
            "urls": [
                "https://developer.apple.com/documentation/foundation/url_loading_system",
                "https://developer.apple.com/documentation/network",
            ],
            "priority": 2,
        },
        # HIG
        "hig": {
            "name": "Human Interface Guidelines",
            "urls": [
                "https://developer.apple.com/design/human-interface-guidelines/",
                "https://developer.apple.com/design/human-interface-guidelines/foundations",
                "https://developer.apple.com/design/human-interface-guidelines/patterns",
                "https://developer.apple.com/design/human-interface-guidelines/components",
            ],
            "priority": 1,
        },
        # Accessibility
        "accessibility": {
            "name": "Accessibility",
            "urls": [
                "https://developer.apple.com/documentation/accessibility",
                "https://developer.apple.com/documentation/accessibility/supporting_voiceover_in_your_app",
                "https://developer.apple.com/design/human-interface-guidelines/accessibility",
            ],
            "priority": 1,
        },
        # Security
        "security": {
            "name": "Security",
            "urls": [
                "https://developer.apple.com/documentation/security",
                "https://developer.apple.com/documentation/authenticationservices",
            ],
            "priority": 2,
        },
    }

    # Allowed domains for following links
    ALLOWED_DOMAINS = [
        "developer.apple.com",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,  # Be polite to Apple
        "CONCURRENT_REQUESTS": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    def __init__(self, *args, framework: str = None, max_pages: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

        # Filter to specific framework or scrape all
        if framework:
            if framework in self.DOC_SECTIONS:
                self.sections = {framework: self.DOC_SECTIONS[framework]}
            else:
                logger.warning(f"Unknown framework '{framework}', scraping all")
                self.sections = self.DOC_SECTIONS
        else:
            self.sections = self.DOC_SECTIONS

    def start_requests(self) -> Iterator[Request]:
        """Start by crawling documentation entry points."""
        # Sort by priority
        sorted_sections = sorted(
            self.sections.items(),
            key=lambda x: x[1].get("priority", 99)
        )

        for section_id, config in sorted_sections:
            for url in config["urls"]:
                yield self.make_request(
                    url,
                    callback=self.parse_doc_page,
                    meta={
                        "section_id": section_id,
                        "section_name": config["name"],
                        "depth": 0,
                        "max_depth": 3,
                    }
                )

    def parse_doc_page(self, response: Response) -> Iterator:
        """Parse an Apple documentation page."""
        section_id = response.meta.get("section_id", "unknown")
        section_name = response.meta.get("section_name", "")
        depth = response.meta.get("depth", 0)
        max_depth = response.meta.get("max_depth", 3)

        url = response.url

        # Skip if already visited
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
            return

        # Check if already in database
        if self._db and self._db.url_exists(url):
            return

        # Extract content from Apple's documentation structure
        # Apple docs have different structures for different page types

        content = ""
        title = ""

        # Try different content selectors
        content_selectors = [
            "main",
            "#main",
            ".documentation-content",
            ".content",
            "article",
            "[role='main']",
        ]

        for selector in content_selectors:
            content_elem = response.css(selector)
            if content_elem:
                raw_html = content_elem.get()
                content = self._clean_html(raw_html)
                if content and len(content) > 200:
                    break

        # Extract title
        title_selectors = [
            "h1::text",
            ".documentation-title::text",
            "title::text",
        ]
        for selector in title_selectors:
            title = response.css(selector).get()
            if title:
                title = title.strip()
                break

        if content and len(content) > 200:
            self.pages_scraped += 1

            # Analyze content type
            content_lower = content.lower()

            is_api_reference = any(marker in content_lower for marker in [
                "declaration", "parameters", "return value", "availability",
                "see also", "topics", "instance method", "type method",
            ])

            is_tutorial = any(marker in content_lower for marker in [
                "step 1", "step 2", "tutorial", "getting started",
                "learn", "build", "create your first",
            ])

            has_code_examples = "```" in content or "swift" in content_lower and "func " in content

            is_hig = "human interface" in content_lower or "design" in url

            is_sample_code = "sample" in url or "example" in content_lower

            # Detect platform
            platforms = []
            if "ios" in url or "uikit" in url:
                platforms.append("iOS")
            if "macos" in url or "appkit" in url:
                platforms.append("macOS")
            if "watchos" in url or "watchkit" in url:
                platforms.append("watchOS")
            if "tvos" in url:
                platforms.append("tvOS")
            if "visionos" in url or "realitykit" in url:
                platforms.append("visionOS")

            yield ScrapedItem(
                source=self.source,
                url=url,
                title=title or "Apple Developer Documentation",
                content=content,
                metadata={
                    "type": "apple_docs",
                    "author": "Apple Inc.",
                    "section": section_id,
                    "section_name": section_name,
                    "depth": depth,
                    "is_api_reference": is_api_reference,
                    "is_tutorial": is_tutorial,
                    "is_hig": is_hig,
                    "is_sample_code": is_sample_code,
                    "has_code_examples": has_code_examples,
                    "platforms": platforms,
                }
            )

        # Follow links if within depth limit
        if depth < max_depth:
            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                # Only follow Apple developer links
                if not any(d in parsed.netloc for d in self.ALLOWED_DOMAINS):
                    continue

                # Skip already visited
                if full_url in self.visited_urls:
                    continue

                # Skip non-documentation links
                skip_patterns = [
                    "/videos/", "/download/", "/forums/", "/account/",
                    ".zip", ".pdf", ".dmg", ".pkg",
                    "/login", "/register", "/support/",
                ]
                if any(p in full_url.lower() for p in skip_patterns):
                    continue

                # Prefer documentation and tutorial links
                doc_patterns = [
                    "/documentation/", "/tutorials/", "/design/",
                    "/sample-code/", "/library/",
                ]
                if any(p in full_url.lower() for p in doc_patterns):
                    yield self.make_request(
                        full_url,
                        callback=self.parse_doc_page,
                        meta={
                            "section_id": section_id,
                            "section_name": section_name,
                            "depth": depth + 1,
                            "max_depth": max_depth,
                        }
                    )

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to markdown-ish text."""
        if not html_content:
            return ""

        text = html_content

        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)

        # Convert code blocks
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
                     r'```swift\n\1\n```', text, flags=re.DOTALL)
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
        text = re.sub(r'<div[^>]*>', '\n', text)
        text = re.sub(r'</div>', '\n', text)

        # Convert bold/italic
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text)
        text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text)
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text)
        text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text)

        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


def register():
    return {
        "name": "apple_dev",
        "spider_class": AppleDevSpider,
        "description": "Apple Developer Docs",
        "type": "code",
        "priority": 1,
    }
