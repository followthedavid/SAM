"""
SAM Scraper System - WWD (Women's Wear Daily) Spider

Scrapes fashion industry news and articles from WWD.
Uses sitemap-based discovery for comprehensive coverage.
"""

import re
import hashlib
from typing import Dict, Any, Optional, Iterator, Tuple
from urllib.parse import urlparse

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class WWDSpider(BaseSpider):
    """
    Spider for Women's Wear Daily (WWD).

    Features:
    - Sitemap-based article discovery
    - Category and date organization
    - Rich metadata extraction
    - Fashion industry content
    """

    name = "wwd_spider"
    source = "wwd"
    allowed_domains = ["wwd.com"]

    # WWD rate limiting
    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    SITEMAP_INDEX = "https://wwd.com/sitemap_index.xml"
    MIN_WORD_COUNT = 100

    def __init__(self, *args, category: str = None, max_articles: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_category = category
        self.max_articles = max_articles
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start by fetching the sitemap index."""
        # Resume from progress
        progress = self.get_progress()
        self.articles_scraped = progress.get("total_items", 0)

        self.logger.info("Fetching sitemap index...")
        yield self.make_request(
            self.SITEMAP_INDEX,
            callback=self.parse_sitemap_index
        )

    def parse_sitemap_index(self, response: Response) -> Iterator[Request]:
        """Parse the sitemap index to find monthly sitemaps."""
        # Extract post sitemaps (not image sitemaps)
        sitemap_urls = re.findall(
            r'<loc>(https://wwd\.com/post-sitemap[^<]+)</loc>',
            response.text
        )

        self.logger.info(f"Found {len(sitemap_urls)} monthly sitemaps")

        # Process sitemaps (most recent first based on URL naming)
        for sitemap_url in sorted(sitemap_urls, reverse=True):
            yield self.make_request(
                sitemap_url,
                callback=self.parse_sitemap,
                meta={"sitemap_url": sitemap_url}
            )

    def parse_sitemap(self, response: Response) -> Iterator[Request]:
        """Parse a monthly sitemap to extract article URLs."""
        sitemap_url = response.meta.get("sitemap_url", "")
        self.logger.info(f"Parsing sitemap: {sitemap_url}")

        # Extract article URLs (exclude images)
        urls = re.findall(r'<loc>(https://wwd\.com/[^<]+)</loc>', response.text)
        article_urls = [u for u in urls if "/wp-content/" not in u]

        # Extract lastmod dates
        lastmods = re.findall(r'<lastmod>([^<]+)</lastmod>', response.text)

        self.logger.info(f"Found {len(article_urls)} articles in {sitemap_url}")

        for i, url in enumerate(article_urls):
            if self.articles_scraped >= self.max_articles:
                self.logger.info(f"Reached max articles limit: {self.max_articles}")
                return

            # Parse category from URL
            category, subcategory = self._parse_category(url)

            # Filter by category if specified
            if self.target_category and category != self.target_category:
                continue

            lastmod = lastmods[i] if i < len(lastmods) else None

            yield self.make_request(
                url,
                callback=self.parse_article,
                meta={
                    "category": category,
                    "subcategory": subcategory,
                    "modified_date": lastmod,
                }
            )

    def _parse_category(self, url: str) -> Tuple[str, str]:
        """Extract category and subcategory from URL."""
        path = urlparse(url).path.strip("/")
        parts = path.split("/")

        if len(parts) >= 2:
            return parts[0], parts[1]
        elif len(parts) == 1:
            return parts[0], ""
        return "uncategorized", ""

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse an article page."""
        category = response.meta.get("category", "")
        subcategory = response.meta.get("subcategory", "")
        modified_date = response.meta.get("modified_date")

        # Extract title
        title_elem = response.css("h1 ::text").get()
        title = title_elem.strip() if title_elem else "Untitled"

        self.logger.info(f"Parsing: {title[:60]}...")

        # Extract author
        author_elem = response.css("a.author-name ::text, span.author ::text").get()
        author = author_elem.strip() if author_elem else None

        # Extract publish date
        time_elem = response.css("time::attr(datetime)").get()
        publish_date = time_elem if time_elem else None

        # Extract article content
        content = self._extract_content(response)
        word_count = len(content.split())

        if word_count < self.MIN_WORD_COUNT:
            self.logger.debug(f"Skipping {response.url}: only {word_count} words")
            return

        # Extract featured image
        og_image = response.css("meta[property='og:image']::attr(content)").get()

        # Build metadata
        metadata = {
            "author": author,
            "category": category,
            "subcategory": subcategory,
            "publish_date": publish_date,
            "modified_date": modified_date,
            "featured_image_url": og_image,
            "word_count": word_count,
            "tags": self._generate_tags(category, subcategory, content),
        }

        # Create ScrapedItem
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

    def _extract_content(self, response: Response) -> str:
        """Extract article body content."""
        # Try multiple selectors for article content
        body_selectors = [
            "article",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".a-content",
            "[class*='article-body']",
        ]

        for selector in body_selectors:
            body = response.css(selector)
            if body:
                paragraphs = body.css("p ::text").getall()
                content = "\n\n".join(p.strip() for p in paragraphs if p.strip())
                if len(content) > 200:
                    return content

        # Fallback: get all paragraphs from main content area
        main = response.css("main, article")
        if main:
            paragraphs = main.css("p ::text").getall()
            return "\n\n".join(p.strip() for p in paragraphs if p.strip())

        return ""

    def _generate_tags(self, category: str, subcategory: str, content: str) -> list:
        """Generate tags for the article."""
        tags = ["fashion", "industry"]

        if category:
            tags.append(category.replace("-", " "))
        if subcategory:
            tags.append(subcategory.replace("-", " "))

        # Content-based tags
        content_lower = content.lower()

        tag_keywords = {
            "runway": ["runway", "fashion show", "collection"],
            "retail": ["retail", "store", "shop", "sales"],
            "luxury": ["luxury", "haute couture", "high-end"],
            "beauty": ["beauty", "cosmetics", "skincare", "makeup"],
            "business": ["revenue", "profit", "acquisition", "merger"],
            "sustainability": ["sustainable", "eco", "green", "ethical"],
            "celebrity": ["celebrity", "red carpet", "star", "actress", "actor"],
            "designer": ["designer", "creative director", "atelier"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)

        return tags


class VMagSpider(BaseSpider):
    """
    Spider for Vogue Magazine content.
    Similar structure to WWD.
    """

    name = "vmag_spider"
    source = "vogue"
    allowed_domains = ["vogue.com"]

    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, max_articles: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_articles = max_articles
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start with sitemap or section pages."""
        # Vogue uses a different sitemap structure
        sitemaps = [
            "https://www.vogue.com/sitemap.xml",
        ]

        for url in sitemaps:
            yield self.make_request(url, callback=self.parse_sitemap)

    def parse_sitemap(self, response: Response) -> Iterator[Request]:
        """Parse Vogue sitemap."""
        # Extract article URLs
        urls = re.findall(r'<loc>([^<]+)</loc>', response.text)

        for url in urls:
            if "/article/" in url or "/story/" in url:
                if self.articles_scraped < self.max_articles:
                    yield self.make_request(url, callback=self.parse_article)

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a Vogue article."""
        # Extract title
        title = response.css("h1 ::text").get()
        if not title:
            return

        title = title.strip()

        # Extract content
        paragraphs = response.css("article p ::text, .body-text p ::text").getall()
        content = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        if len(content.split()) < 100:
            return

        # Extract metadata
        author = response.css(".byline-name ::text, .author ::text").get()
        date = response.css("time::attr(datetime)").get()

        metadata = {
            "author": author.strip() if author else None,
            "publish_date": date,
            "word_count": len(content.split()),
            "tags": ["fashion", "vogue", "style"],
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


class WMagSpider(BaseSpider):
    """
    Spider for W Magazine content.
    """

    name = "wmag_spider"
    source = "wmag"
    allowed_domains = ["wmagazine.com"]

    rate_limit = 1.5
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, max_articles: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_articles = max_articles
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start with sitemap."""
        yield self.make_request(
            "https://www.wmagazine.com/sitemap.xml",
            callback=self.parse_sitemap
        )

    def parse_sitemap(self, response: Response) -> Iterator[Request]:
        """Parse W Magazine sitemap."""
        urls = re.findall(r'<loc>([^<]+)</loc>', response.text)

        for url in urls:
            if "/story/" in url or "/article/" in url:
                if self.articles_scraped < self.max_articles:
                    yield self.make_request(url, callback=self.parse_article)

    def parse_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a W Magazine article."""
        title = response.css("h1 ::text").get()
        if not title:
            return

        title = title.strip()

        paragraphs = response.css("article p ::text, .body p ::text").getall()
        content = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        if len(content.split()) < 100:
            return

        author = response.css(".byline ::text, .author ::text").get()
        date = response.css("time::attr(datetime)").get()

        metadata = {
            "author": author.strip() if author else None,
            "publish_date": date,
            "word_count": len(content.split()),
            "tags": ["fashion", "culture", "art"],
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
