"""
Source Discovery Engine

Automatically discovers and evaluates new data sources for scraping.

Features:
1. Web search to find new sources (Google, DuckDuckGo, GitHub)
2. Source quality analysis and scoring
3. Automatic spider configuration generation
4. Gap detection in current data
5. Priority ranking based on relevance to SAM's needs

This is the "depth" component of the hybrid approach - automating
the expansion of scraping breadth.
"""

import json
import logging
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSource:
    """A potential new data source."""
    url: str
    name: str
    description: str
    source_type: str  # code, apple, documentation, tutorial, etc.
    discovered_at: datetime = field(default_factory=datetime.now)

    # Scoring
    relevance_score: float = 0.0  # 0-1
    quality_score: float = 0.0    # 0-1
    freshness_score: float = 0.0  # 0-1
    total_score: float = 0.0

    # Analysis results
    has_api: bool = False
    has_rss: bool = False
    estimated_pages: int = 0
    content_topics: List[str] = field(default_factory=list)

    # Metadata
    domain: str = ""
    robots_friendly: bool = True
    rate_limit_detected: float = 0.0


@dataclass
class SourceGap:
    """A gap in the current data coverage."""
    topic: str
    description: str
    priority: int  # 1-5
    suggested_queries: List[str] = field(default_factory=list)
    related_sources: List[str] = field(default_factory=list)


class SourceDiscoveryEngine:
    """
    Engine for automatically discovering new data sources.

    Usage:
        engine = SourceDiscoveryEngine()
        engine.initialize()

        # Discover sources for a topic
        sources = engine.discover_sources("SwiftUI tutorials")

        # Find gaps in coverage
        gaps = engine.analyze_gaps()

        # Generate spider config
        config = engine.generate_spider_config(source)
    """

    # Search queries for different categories
    SEARCH_TEMPLATES = {
        "apple": [
            "SwiftUI tutorial beginner site:github.com",
            "iOS development guide 2024",
            "visionOS development tutorial",
            "Swift best practices blog",
            "Apple developer community forum",
            "SwiftData tutorial example",
            "Xcode debugging guide",
            "UIKit to SwiftUI migration",
        ],
        "code": [
            "programming tutorial blog",
            "developer documentation open source",
            "coding best practices guide",
            "software architecture patterns",
            "debugging techniques tutorial",
            "test-driven development guide",
        ],
        "errors": [
            "common programming errors solutions",
            "stack trace debugging guide",
            "error handling best practices",
            "troubleshooting developer guide",
        ],
        "tools": [
            "developer tools documentation",
            "IDE configuration guide",
            "build system tutorial",
            "package manager guide",
        ],
    }

    # Known high-quality domains
    TRUSTED_DOMAINS = {
        # Apple ecosystem
        "developer.apple.com": {"type": "apple", "quality": 1.0},
        "hackingwithswift.com": {"type": "apple", "quality": 0.95},
        "swiftbysundell.com": {"type": "apple", "quality": 0.95},
        "swift.org": {"type": "apple", "quality": 1.0},
        "kodeco.com": {"type": "apple", "quality": 0.9},
        "nshipster.com": {"type": "apple", "quality": 0.9},
        "avanderlee.com": {"type": "apple", "quality": 0.85},
        "wwdcnotes.com": {"type": "apple", "quality": 0.9},

        # General coding
        "github.com": {"type": "code", "quality": 0.85},
        "stackoverflow.com": {"type": "code", "quality": 0.9},
        "dev.to": {"type": "code", "quality": 0.8},
        "medium.com": {"type": "code", "quality": 0.7},
        "hashnode.dev": {"type": "code", "quality": 0.75},

        # Documentation
        "docs.python.org": {"type": "docs", "quality": 1.0},
        "docs.docker.com": {"type": "docs", "quality": 1.0},
        "nodejs.org": {"type": "docs", "quality": 1.0},
        "docs.npmjs.com": {"type": "docs", "quality": 1.0},

        # Testing/Accessibility
        "playwright.dev": {"type": "testing", "quality": 0.95},
        "testing-library.com": {"type": "testing", "quality": 0.95},
        "w3.org": {"type": "accessibility", "quality": 1.0},
        "a11yproject.com": {"type": "accessibility", "quality": 0.9},
    }

    # Topics we care about (for relevance scoring)
    PRIORITY_TOPICS = {
        "swift": 1.0,
        "swiftui": 1.0,
        "ios": 0.95,
        "macos": 0.95,
        "visionos": 1.0,
        "watchos": 0.85,
        "xcode": 0.9,
        "apple": 0.9,
        "testing": 0.85,
        "debugging": 0.9,
        "error": 0.85,
        "tutorial": 0.8,
        "beginner": 0.85,
        "accessibility": 0.8,
        "ui": 0.75,
        "installation": 0.7,
        "setup": 0.7,
    }

    def __init__(self):
        self.discovered_sources: List[DiscoveredSource] = []
        self.known_urls: Set[str] = set()
        self.gaps: List[SourceGap] = []
        self._db = None

    def initialize(self):
        """Initialize the discovery engine."""
        from ..storage.database import get_database

        try:
            self._db = get_database()
            logger.info("Source discovery engine initialized")
        except Exception as e:
            logger.warning(f"Database not available: {e}")

    def discover_sources(
        self,
        query: str = None,
        category: str = None,
        max_results: int = 50
    ) -> List[DiscoveredSource]:
        """
        Discover new sources based on query or category.

        Args:
            query: Search query string
            category: Category from SEARCH_TEMPLATES
            max_results: Maximum sources to return

        Returns:
            List of discovered and scored sources
        """
        sources = []

        # If category provided, use templates
        if category and category in self.SEARCH_TEMPLATES:
            queries = self.SEARCH_TEMPLATES[category]
        elif query:
            queries = [query]
        else:
            # Default: search all categories
            queries = []
            for cat_queries in self.SEARCH_TEMPLATES.values():
                queries.extend(cat_queries)

        # Process each query
        for q in queries[:10]:  # Limit queries
            try:
                results = self._search(q)
                for result in results:
                    source = self._analyze_result(result, q)
                    if source and source.url not in self.known_urls:
                        self.known_urls.add(source.url)
                        sources.append(source)
            except Exception as e:
                logger.error(f"Search failed for '{q}': {e}")

        # Score all sources
        for source in sources:
            self._score_source(source)

        # Sort by score and limit
        sources.sort(key=lambda s: s.total_score, reverse=True)
        sources = sources[:max_results]

        self.discovered_sources.extend(sources)
        return sources

    def _search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for sources using available search methods.

        This is a placeholder - in production would use:
        - Google Custom Search API
        - DuckDuckGo API
        - GitHub Search API
        - Bing Search API
        """
        # For now, return predefined high-quality sources
        # In production, this would make actual API calls

        predefined_results = []
        query_lower = query.lower()

        # Return relevant predefined sources based on query
        if "swift" in query_lower or "apple" in query_lower or "ios" in query_lower:
            predefined_results.extend([
                {"url": "https://www.hackingwithswift.com/", "title": "Hacking with Swift", "snippet": "Free Swift tutorials"},
                {"url": "https://www.swiftbysundell.com/", "title": "Swift by Sundell", "snippet": "Weekly Swift articles"},
                {"url": "https://www.kodeco.com/", "title": "Kodeco", "snippet": "Mobile development tutorials"},
                {"url": "https://www.objc.io/", "title": "objc.io", "snippet": "Advanced Swift and iOS"},
                {"url": "https://www.raywenderlich.com/", "title": "Ray Wenderlich Archive", "snippet": "iOS tutorials"},
                {"url": "https://www.appcoda.com/", "title": "AppCoda", "snippet": "iOS programming tutorials"},
                {"url": "https://iosdevweekly.com/", "title": "iOS Dev Weekly", "snippet": "Weekly iOS news"},
                {"url": "https://sarunw.com/", "title": "Sarunw", "snippet": "Swift and iOS tips"},
            ])

        if "testing" in query_lower or "debug" in query_lower:
            predefined_results.extend([
                {"url": "https://playwright.dev/", "title": "Playwright", "snippet": "Browser automation"},
                {"url": "https://testing-library.com/", "title": "Testing Library", "snippet": "UI testing"},
                {"url": "https://www.browserstack.com/guide", "title": "BrowserStack Guide", "snippet": "Testing guides"},
            ])

        if "accessibility" in query_lower or "a11y" in query_lower:
            predefined_results.extend([
                {"url": "https://www.a11yproject.com/", "title": "The A11Y Project", "snippet": "Accessibility resources"},
                {"url": "https://www.deque.com/", "title": "Deque", "snippet": "Accessibility tools"},
                {"url": "https://webaim.org/", "title": "WebAIM", "snippet": "Web accessibility"},
            ])

        if "github" in query_lower or "code" in query_lower:
            predefined_results.extend([
                {"url": "https://github.com/topics/swift", "title": "GitHub Swift Topics", "snippet": "Swift repositories"},
                {"url": "https://github.com/topics/swiftui", "title": "GitHub SwiftUI Topics", "snippet": "SwiftUI examples"},
            ])

        return predefined_results

    def _analyze_result(self, result: Dict[str, Any], query: str) -> Optional[DiscoveredSource]:
        """Analyze a search result and create a DiscoveredSource."""
        url = result.get("url", "")
        if not url:
            return None

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Skip if already known
        if url in self.known_urls:
            return None

        # Determine source type
        source_type = "code"
        if domain in self.TRUSTED_DOMAINS:
            source_type = self.TRUSTED_DOMAINS[domain].get("type", "code")
        elif any(kw in domain for kw in ["apple", "swift", "ios"]):
            source_type = "apple"
        elif any(kw in domain for kw in ["test", "a11y", "accessibility"]):
            source_type = "testing"

        return DiscoveredSource(
            url=url,
            name=result.get("title", domain),
            description=result.get("snippet", ""),
            source_type=source_type,
            domain=domain,
            content_topics=self._extract_topics(result.get("title", "") + " " + result.get("snippet", "")),
        )

    def _extract_topics(self, text: str) -> List[str]:
        """Extract relevant topics from text."""
        text_lower = text.lower()
        return [topic for topic in self.PRIORITY_TOPICS if topic in text_lower]

    def _score_source(self, source: DiscoveredSource):
        """Calculate scores for a source."""
        # Relevance score based on topics
        if source.content_topics:
            topic_scores = [self.PRIORITY_TOPICS.get(t, 0.5) for t in source.content_topics]
            source.relevance_score = sum(topic_scores) / len(topic_scores)
        else:
            source.relevance_score = 0.3

        # Quality score based on domain reputation
        if source.domain in self.TRUSTED_DOMAINS:
            source.quality_score = self.TRUSTED_DOMAINS[source.domain].get("quality", 0.5)
        else:
            # Unknown domains get base score
            source.quality_score = 0.5

        # Freshness score (would check actual page in production)
        source.freshness_score = 0.7  # Default

        # Total score (weighted average)
        source.total_score = (
            source.relevance_score * 0.4 +
            source.quality_score * 0.4 +
            source.freshness_score * 0.2
        )

    def analyze_gaps(self) -> List[SourceGap]:
        """
        Analyze current data to find gaps in coverage.

        Returns:
            List of identified gaps with suggestions
        """
        gaps = []

        if not self._db:
            logger.warning("Database not available for gap analysis")
            return gaps

        # Get current source distribution
        try:
            stats = self._db.get_stats()
        except Exception:
            stats = {}

        # Define expected coverage
        expected_topics = {
            "Apple/Swift": {
                "sources": ["apple_dev", "swift_community", "wwdc"],
                "min_items": 500,
                "queries": ["swift tutorial", "swiftui guide", "ios development"],
            },
            "UI Testing": {
                "sources": ["uiux"],
                "min_items": 200,
                "queries": ["ui testing tutorial", "playwright guide", "xctest tutorial"],
            },
            "Error Handling": {
                "sources": ["stackoverflow", "github"],
                "min_items": 300,
                "queries": ["error handling swift", "debugging ios app"],
            },
            "App Store": {
                "sources": ["apple_dev"],
                "min_items": 100,
                "queries": ["app store submission guide", "storekit tutorial"],
            },
            "visionOS": {
                "sources": ["apple_dev", "wwdc"],
                "min_items": 100,
                "queries": ["visionos tutorial", "realitykit guide", "spatial computing"],
            },
        }

        for topic, config in expected_topics.items():
            # Check if we have enough data
            total_items = sum(
                stats.get(src, {}).get("total_items", 0)
                for src in config["sources"]
            )

            if total_items < config["min_items"]:
                gaps.append(SourceGap(
                    topic=topic,
                    description=f"Only {total_items} items, need {config['min_items']}",
                    priority=3 if total_items == 0 else (2 if total_items < config['min_items'] / 2 else 1),
                    suggested_queries=config["queries"],
                    related_sources=config["sources"],
                ))

        self.gaps = gaps
        return gaps

    def generate_spider_config(self, source: DiscoveredSource) -> Dict[str, Any]:
        """
        Generate a spider configuration for a discovered source.

        This creates a config that could be used to add a new spider.
        """
        # Determine spider type and settings
        config = {
            "name": source.name.lower().replace(" ", "_"),
            "source": source.source_type,
            "start_urls": [source.url],
            "allowed_domains": [source.domain],
            "content_selector": "main, article, .content",
            "max_depth": 2,
            "priority": 2,
            "download_delay": 2.0,
        }

        # Adjust based on source type
        if source.source_type == "apple":
            config["download_delay"] = 2.0
            config["max_depth"] = 3
            config["priority"] = 1
        elif source.source_type == "code":
            config["download_delay"] = 1.5

        # Add API info if detected
        if source.has_api:
            config["has_api"] = True
            config["api_base"] = f"https://api.{source.domain}"

        return config

    def generate_spider_code(self, source: DiscoveredSource) -> str:
        """
        Generate Python spider code for a discovered source.

        This creates actual spider code that could be saved to a file.
        """
        class_name = "".join(word.title() for word in source.name.split()) + "Spider"
        spider_name = source.name.lower().replace(" ", "_") + "_spider"

        code = f'''"""
{source.name} Spider - Auto-generated by Source Discovery Engine

Generated: {datetime.now().isoformat()}
Source URL: {source.url}
Topics: {", ".join(source.content_topics)}
"""

import logging
import html
import re
from typing import Iterator
from urllib.parse import urljoin, urlparse

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class {class_name}(BaseSpider):
    """
    Spider for {source.name}.

    Auto-generated spider targeting: {source.description}
    """

    name = "{spider_name}"
    source = "{source.source_type}"

    custom_settings = {{
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }}

    def __init__(self, *args, max_pages: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

    def start_requests(self) -> Iterator[Request]:
        """Start crawling."""
        yield self.make_request(
            "{source.url}",
            callback=self.parse_page,
            meta={{"depth": 0}}
        )

    def parse_page(self, response: Response) -> Iterator:
        """Parse a page."""
        url = response.url
        depth = response.meta.get("depth", 0)

        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
            return

        # Check database
        if self._db and self._db.url_exists(url):
            return

        # Extract content
        content_elem = response.css("main, article, .content")
        if content_elem:
            raw_html = content_elem.get()
            content = self._clean_html(raw_html)

            if content and len(content) > 200:
                self.pages_scraped += 1

                title = response.css("title::text").get() or ""
                title = title.strip()

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={{
                        "type": "{source.source_type}_content",
                        "author": "{source.name}",
                        "depth": depth,
                    }}
                )

        # Follow links
        if depth < 2:
            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                if "{source.domain}" not in parsed.netloc:
                    continue

                if full_url in self.visited_urls:
                    continue

                # Skip non-content
                if any(full_url.endswith(ext) for ext in [".png", ".jpg", ".pdf", ".zip"]):
                    continue

                yield self.make_request(
                    full_url,
                    callback=self.parse_page,
                    meta={{"depth": depth + 1}}
                )

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to text."""
        if not html_content:
            return ""

        text = html_content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\\s+', ' ', text)
        return text.strip()


def register():
    return {{
        "name": "{source.name.lower().replace(' ', '_')}",
        "spider_class": {class_name},
        "description": "{source.name}",
        "type": "{source.source_type}",
        "priority": 2,
    }}
'''
        return code

    def get_recommendations(self, limit: int = 10) -> List[DiscoveredSource]:
        """
        Get top recommended new sources to add.

        Returns sources sorted by potential value.
        """
        # Filter out already-scraped domains
        existing_domains = set()
        if self._db:
            try:
                stats = self._db.get_stats()
                # Would need to track domains in DB
            except Exception:
                pass

        # Sort by score and novelty
        recommendations = [
            s for s in self.discovered_sources
            if s.domain not in existing_domains
        ]
        recommendations.sort(key=lambda s: s.total_score, reverse=True)

        return recommendations[:limit]

    def export_discoveries(self, filepath: str):
        """Export discovered sources to JSON."""
        data = {
            "discovered_at": datetime.now().isoformat(),
            "total_sources": len(self.discovered_sources),
            "gaps": [
                {
                    "topic": g.topic,
                    "description": g.description,
                    "priority": g.priority,
                    "suggested_queries": g.suggested_queries,
                }
                for g in self.gaps
            ],
            "sources": [
                {
                    "url": s.url,
                    "name": s.name,
                    "description": s.description,
                    "type": s.source_type,
                    "domain": s.domain,
                    "relevance_score": s.relevance_score,
                    "quality_score": s.quality_score,
                    "total_score": s.total_score,
                    "topics": s.content_topics,
                }
                for s in self.discovered_sources
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(self.discovered_sources)} sources to {filepath}")


# Convenience function
def get_discovery_engine() -> SourceDiscoveryEngine:
    """Get initialized discovery engine."""
    engine = SourceDiscoveryEngine()
    engine.initialize()
    return engine
