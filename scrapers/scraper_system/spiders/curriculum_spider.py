"""
Curriculum Spider - Scrapes structured learning paths and courses

Targets:
1. Apple's Swift Playgrounds curriculum
2. Stanford CS193p (iOS Development)
3. Hacking with Swift 100 Days
4. Kodeco Learning Paths
5. freeCodeCamp curricula
6. The Odin Project structure
7. Apple's "Develop in Swift" curriculum

Critical for teaching SAM how to plan learning progressions and project structure.
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


class CurriculumSpider(BaseSpider):
    """
    Spider for structured learning curricula.

    Extracts:
    - Course outlines and syllabi
    - Learning progressions
    - Prerequisites and dependencies
    - Project-based learning sequences
    - Assessment structures

    Usage:
        scrapy crawl curriculum
        scrapy crawl curriculum -a source=stanford
    """

    name = "curriculum_spider"
    source = "curriculum"

    # Curriculum sources
    CURRICULA = {
        "100days_swiftui": {
            "name": "100 Days of SwiftUI",
            "start_urls": [
                "https://www.hackingwithswift.com/100/swiftui",
            ],
            "allowed_domains": ["hackingwithswift.com"],
            "content_selector": "article, main, .content",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 1,
        },
        "100days_swift": {
            "name": "100 Days of Swift",
            "start_urls": [
                "https://www.hackingwithswift.com/100",
            ],
            "allowed_domains": ["hackingwithswift.com"],
            "content_selector": "article, main, .content",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 1,
        },
        "stanford_cs193p": {
            "name": "Stanford CS193p",
            "start_urls": [
                "https://cs193p.sites.stanford.edu/",
                "https://cs193p.sites.stanford.edu/2023",
            ],
            "allowed_domains": ["cs193p.sites.stanford.edu", "stanford.edu"],
            "content_selector": "main, article, .content",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 1,
        },
        "apple_develop_swift": {
            "name": "Develop in Swift",
            "start_urls": [
                "https://developer.apple.com/learn/curriculum/",
                "https://developer.apple.com/tutorials/develop-in-swift",
            ],
            "allowed_domains": ["developer.apple.com"],
            "content_selector": "main, article",
            "is_sequential": True,
            "max_depth": 3,
            "priority": 1,
        },
        "apple_tutorials": {
            "name": "Apple SwiftUI Tutorials",
            "start_urls": [
                "https://developer.apple.com/tutorials/swiftui",
                "https://developer.apple.com/tutorials/app-dev-training",
            ],
            "allowed_domains": ["developer.apple.com"],
            "content_selector": "main, article",
            "is_sequential": True,
            "max_depth": 3,
            "priority": 1,
        },
        "kodeco_paths": {
            "name": "Kodeco Learning Paths",
            "start_urls": [
                "https://www.kodeco.com/ios/paths",
                "https://www.kodeco.com/ios/paths/learn",
            ],
            "allowed_domains": ["kodeco.com"],
            "content_selector": "main, article",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 2,
        },
        "freecodecamp": {
            "name": "freeCodeCamp",
            "start_urls": [
                "https://www.freecodecamp.org/learn/",
            ],
            "allowed_domains": ["freecodecamp.org"],
            "content_selector": "main, article",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 2,
        },
        "odin_project": {
            "name": "The Odin Project",
            "start_urls": [
                "https://www.theodinproject.com/paths",
                "https://www.theodinproject.com/paths/full-stack-javascript",
            ],
            "allowed_domains": ["theodinproject.com"],
            "content_selector": "main, article, .content",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 2,
        },
        "exercism": {
            "name": "Exercism Swift Track",
            "start_urls": [
                "https://exercism.org/tracks/swift",
                "https://exercism.org/tracks/swift/concepts",
            ],
            "allowed_domains": ["exercism.org"],
            "content_selector": "main, article",
            "is_sequential": True,
            "max_depth": 2,
            "priority": 2,
        },
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, source: str = None, max_pages: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

        # Filter to specific source
        if source:
            if source in self.CURRICULA:
                self.curricula = {source: self.CURRICULA[source]}
            else:
                self.curricula = self.CURRICULA
        else:
            self.curricula = self.CURRICULA

    def start_requests(self) -> Iterator[Request]:
        """Start crawling curricula."""
        for curr_id, config in self.curricula.items():
            for url in config["start_urls"]:
                yield self.make_request(
                    url,
                    callback=self.parse_curriculum_page,
                    meta={
                        "curriculum_id": curr_id,
                        "config": config,
                        "depth": 0,
                        "sequence_num": 0,
                    }
                )

    def parse_curriculum_page(self, response: Response) -> Iterator:
        """Parse a curriculum page."""
        curr_id = response.meta.get("curriculum_id", "unknown")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)
        sequence_num = response.meta.get("sequence_num", 0)
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

                # Analyze curriculum structure
                content_lower = content.lower()

                # Detect lesson/chapter structure
                is_lesson = any(marker in content_lower for marker in [
                    "lesson", "chapter", "day ", "week ", "module",
                    "part ", "section", "unit", "step ",
                ])

                is_project = any(marker in content_lower for marker in [
                    "project", "challenge", "exercise", "build",
                    "create", "implement", "practice",
                ])

                is_overview = any(marker in content_lower for marker in [
                    "overview", "introduction", "curriculum", "syllabus",
                    "course outline", "learning path", "prerequisites",
                ])

                # Extract learning objectives
                objectives = self._extract_objectives(content)

                # Extract prerequisites
                prerequisites = self._extract_prerequisites(content)

                # Detect sequence number from title/url
                detected_seq = self._extract_sequence_number(title, url)

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": "curriculum",
                        "author": config.get("name", curr_id),
                        "curriculum_id": curr_id,
                        "curriculum_name": config.get("name", ""),
                        "is_sequential": config.get("is_sequential", True),
                        "sequence_num": detected_seq or sequence_num,
                        "depth": depth,
                        "is_lesson": is_lesson,
                        "is_project": is_project,
                        "is_overview": is_overview,
                        "learning_objectives": objectives,
                        "prerequisites": prerequisites,
                    }
                )

        # Follow curriculum links
        max_depth = config.get("max_depth", 2)
        if depth < max_depth:
            allowed_domains = config.get("allowed_domains", [])

            # Track sequence for sequential curricula
            seq = sequence_num

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
                    "/login", "/signup", "/cart", "/checkout",
                    ".pdf", ".zip", ".mp4", ".mov",
                    "/forums", "/community", "/discuss",
                ]
                if any(p in full_url.lower() for p in skip_patterns):
                    continue

                # Prefer curriculum links
                curriculum_patterns = [
                    "/day", "/lesson", "/chapter", "/module",
                    "/part", "/section", "/unit", "/week",
                    "/tutorial", "/learn", "/path", "/track",
                    "/exercise", "/challenge", "/project",
                ]

                if any(p in full_url.lower() for p in curriculum_patterns):
                    seq += 1
                    yield self.make_request(
                        full_url,
                        callback=self.parse_curriculum_page,
                        meta={
                            "curriculum_id": curr_id,
                            "config": config,
                            "depth": depth + 1,
                            "sequence_num": seq,
                        }
                    )

    def _extract_objectives(self, content: str) -> List[str]:
        """Extract learning objectives from content."""
        objectives = []

        # Common patterns for objectives
        patterns = [
            r"(?:you(?:'ll| will) learn|learning objectives?|by the end.*you(?:'ll| will)|what you(?:'ll| will) learn)[:\s]*(.*?)(?:\n\n|\Z)",
            r"(?:goals?|objectives?)[:\s]*(.*?)(?:\n\n|\Z)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Extract bullet points
                bullets = re.findall(r'[-•*]\s*(.+?)(?:\n|$)', match)
                objectives.extend(bullets[:10])

        return objectives[:10]

    def _extract_prerequisites(self, content: str) -> List[str]:
        """Extract prerequisites from content."""
        prerequisites = []

        patterns = [
            r"(?:prerequisites?|before you (?:start|begin)|requirements?|you(?:'ll| will) need)[:\s]*(.*?)(?:\n\n|\Z)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                bullets = re.findall(r'[-•*]\s*(.+?)(?:\n|$)', match)
                prerequisites.extend(bullets[:10])

        return prerequisites[:10]

    def _extract_sequence_number(self, title: str, url: str) -> Optional[int]:
        """Extract sequence number from title or URL."""
        combined = f"{title} {url}".lower()

        # Day/lesson/chapter number
        patterns = [
            r'day[- ]?(\d+)',
            r'lesson[- ]?(\d+)',
            r'chapter[- ]?(\d+)',
            r'module[- ]?(\d+)',
            r'part[- ]?(\d+)',
            r'week[- ]?(\d+)',
            r'/(\d+)(?:/|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                return int(match.group(1))

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
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

        # Convert headers
        for i in range(1, 7):
            text = re.sub(f'<h{i}[^>]*>(.*?)</h{i}>',
                         lambda m, level=i: '#' * level + ' ' + m.group(1) + '\n',
                         text, flags=re.DOTALL)

        # Convert lists
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)

        # Convert paragraphs
        text = re.sub(r'<p[^>]*>', '\n\n', text)
        text = re.sub(r'<br\s*/?>', '\n', text)

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
        "name": "curriculum",
        "spider_class": CurriculumSpider,
        "description": "Structured Learning Paths",
        "type": "planning",
        "priority": 1,
    }
