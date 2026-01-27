"""
SAM Scraper System - Dark Psychology Spider

Scrapes dark psychology, manipulation, and persuasion content.
For SAM's understanding of human psychology and influence.
"""

import re
from typing import Dict, Any, Iterator

from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class DarkPsychSpider(BaseSpider):
    """Spider for dark psychology and persuasion content."""

    name = "dark_psych_spider"
    source = "dark_psych"
    allowed_domains = []  # Will be set dynamically

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
    }

    # Target sources for psychology content
    SOURCES = [
        # Psychology blogs and sites
        ("https://www.psychologytoday.com/us/basics/dark-triad", "psychology_today"),
        ("https://www.psychologytoday.com/us/basics/manipulation", "psychology_today"),
        ("https://www.psychologytoday.com/us/basics/persuasion", "psychology_today"),
    ]

    def __init__(self, *args, min_words: int = 300, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_words = min_words
        # Set allowed domains from sources
        self.allowed_domains = list(set(
            re.search(r'://([^/]+)', url).group(1)
            for url, _ in self.SOURCES if re.search(r'://([^/]+)', url)
        ))

    def start_requests(self) -> Iterator[Request]:
        """Start with configured source URLs."""
        for url, source_type in self.SOURCES:
            yield self.make_request(
                url,
                callback=self.parse_index,
                meta={"source_type": source_type}
            )

    def parse_index(self, response: Response) -> Iterator[Any]:
        """Parse index/listing page."""
        source_type = response.meta.get("source_type")
        self.logger.info(f"Parsing index: {response.url}")

        # Find article links
        article_links = response.css("article a::attr(href), .article-link::attr(href), h2 a::attr(href)").getall()

        for link in set(article_links):
            if link and not link.startswith("#"):
                full_url = response.urljoin(link)
                yield self.make_request(
                    full_url,
                    callback=self.parse_article,
                    meta={"source_type": source_type}
                )

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse individual article."""
        self.logger.info(f"Parsing article: {response.url}")

        # Extract title
        title = response.css("h1::text").get()
        if not title:
            title = response.css("title::text").get()
        title = title.strip() if title else "Untitled"

        # Extract author
        author = response.css(".author-name::text, .byline::text, [rel='author']::text").get()
        author = author.strip() if author else "Unknown"

        # Extract content
        content_selectors = [
            "article p::text",
            ".article-body p::text",
            ".post-content p::text",
            ".entry-content p::text",
            "main p::text",
        ]

        paragraphs = []
        for selector in content_selectors:
            texts = response.css(selector).getall()
            if texts:
                paragraphs.extend(texts)
                break

        if not paragraphs:
            # Fallback: get all p tags
            paragraphs = response.css("p::text").getall()

        text = "\n\n".join(p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20)

        word_count = len(text.split())
        if word_count < self.min_words:
            self.logger.warning(f"Skipping: only {word_count} words")
            return

        # Extract topics/tags from the content
        tags = ["psychology", "dark_psychology"]

        text_lower = text.lower()
        topic_keywords = {
            "manipulation": ["manipulat", "exploit", "control"],
            "persuasion": ["persuad", "persuasion", "influence", "convinc"],
            "narcissism": ["narciss", "egotist", "self-centered"],
            "machiavellianism": ["machiavelli", "cunning", "scheming"],
            "psychopathy": ["psychopath", "antisocial", "empathy"],
            "gaslighting": ["gaslight", "reality distortion"],
            "coercion": ["coerci", "force", "pressure"],
            "deception": ["decei", "decept", "lie", "lying"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(topic)

        metadata = {
            "author": author,
            "tags": tags,
            "word_count": word_count,
            "source_type": response.meta.get("source_type"),
        }

        yield ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=text,
            metadata=metadata,
        )
