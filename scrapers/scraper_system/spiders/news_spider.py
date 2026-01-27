"""
SAM News Aggregation Spiders

Collects news from multiple sources with bias awareness for training SAM
on current events. Replicates core Ground News functionality.

Spiders:
- BiasRatingsSpider: Scrapes bias/factuality ratings from AllSides and MBFC
- RSSNewsSpider: Aggregates news from RSS feeds across the political spectrum
- NewsAPISpider: Uses NewsAPI.org for additional coverage
"""

import re
import json
import hashlib
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy import Request

from .base_spider import BaseSpider


class BiasRatingsSpider(BaseSpider):
    """
    Scrapes media bias ratings from:
    - AllSides.com
    - Media Bias Fact Check (mediabiasfactcheck.com)

    Creates a database of outlet -> bias rating mappings.
    """

    name = "bias_ratings_spider"
    source = "bias_ratings"

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 1,
        "ROBOTSTXT_OBEY": False,
    }

    # AllSides bias categories
    ALLSIDES_URL = "https://www.allsides.com/media-bias/ratings"

    # Media Bias Fact Check categories
    MBFC_CATEGORIES = {
        "left": "https://mediabiasfactcheck.com/left/",
        "left-center": "https://mediabiasfactcheck.com/leftcenter/",
        "center": "https://mediabiasfactcheck.com/center/",
        "right-center": "https://mediabiasfactcheck.com/right-center/",
        "right": "https://mediabiasfactcheck.com/right/",
        "questionable": "https://mediabiasfactcheck.com/fake-news/",
        "satire": "https://mediabiasfactcheck.com/satire/",
        "pro-science": "https://mediabiasfactcheck.com/pro-science/",
    }

    def start_requests(self):
        """Start with AllSides, then MBFC."""
        yield Request(
            self.ALLSIDES_URL,
            callback=self.parse_allsides,
            meta={"source": "allsides"}
        )

        for bias, url in self.MBFC_CATEGORIES.items():
            yield Request(
                url,
                callback=self.parse_mbfc_category,
                meta={"bias": bias, "source": "mbfc"}
            )

    def parse_allsides(self, response):
        """Parse AllSides media bias ratings page."""
        # AllSides lists outlets in a table with bias ratings
        rows = response.css("table.views-table tbody tr")

        for row in rows:
            outlet_name = row.css("td.views-field-title a::text").get()
            outlet_url = row.css("td.views-field-field-bias-image a::attr(href)").get()

            # Bias is indicated by the image/class
            bias_cell = row.css("td.views-field-field-bias-image")
            bias_class = bias_cell.css("a::attr(class)").get() or ""

            # Extract bias from class name
            bias = "center"
            if "left" in bias_class.lower():
                if "lean" in bias_class.lower():
                    bias = "left-center"
                else:
                    bias = "left"
            elif "right" in bias_class.lower():
                if "lean" in bias_class.lower():
                    bias = "right-center"
                else:
                    bias = "right"

            if outlet_name:
                yield self.create_item(
                    content=json.dumps({
                        "outlet": outlet_name.strip(),
                        "bias": bias,
                        "source": "allsides",
                        "url": outlet_url,
                    }),
                    title=f"Bias Rating: {outlet_name.strip()}",
                    url=response.url,
                    metadata={
                        "outlet": outlet_name.strip(),
                        "bias": bias,
                        "rating_source": "allsides",
                        "type": "bias_rating",
                    }
                )

    def parse_mbfc_category(self, response):
        """Parse MBFC category page listing outlets."""
        bias = response.meta["bias"]

        # MBFC lists outlets as links in the main content
        outlet_links = response.css("article a[href*='mediabiasfactcheck.com']")

        for link in outlet_links:
            outlet_name = link.css("::text").get()
            outlet_page = link.css("::attr(href)").get()

            if outlet_name and outlet_page and "/author/" not in outlet_page:
                # Skip navigation/author links
                if any(skip in outlet_name.lower() for skip in ["next", "previous", "page", "comment"]):
                    continue

                yield self.create_item(
                    content=json.dumps({
                        "outlet": outlet_name.strip(),
                        "bias": bias,
                        "source": "mbfc",
                        "detail_url": outlet_page,
                    }),
                    title=f"Bias Rating: {outlet_name.strip()}",
                    url=response.url,
                    metadata={
                        "outlet": outlet_name.strip(),
                        "bias": bias,
                        "rating_source": "mbfc",
                        "type": "bias_rating",
                    }
                )


class RSSNewsSpider(BaseSpider):
    """
    Aggregates news from RSS feeds across the political spectrum.

    Curated list of sources with known bias ratings for balanced coverage.
    """

    name = "rss_news_spider"
    source = "rss_news"

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 4,
        "ROBOTSTXT_OBEY": False,
    }

    # Curated RSS feeds with bias labels
    # Format: (name, rss_url, bias, factuality)
    RSS_SOURCES = [
        # Left-leaning
        ("MSNBC", "https://www.msnbc.com/feeds/latest", "left", "mixed"),
        ("Huffington Post", "https://www.huffpost.com/section/front-page/feed", "left", "mixed"),
        ("The Guardian", "https://www.theguardian.com/us/rss", "left-center", "high"),
        ("Vox", "https://www.vox.com/rss/index.xml", "left", "high"),
        ("Slate", "https://slate.com/feeds/all.rss", "left", "high"),

        # Left-center
        ("NPR", "https://feeds.npr.org/1001/rss.xml", "left-center", "high"),
        ("Washington Post", "https://feeds.washingtonpost.com/rss/national", "left-center", "high"),
        ("New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "left-center", "high"),
        ("BBC", "http://feeds.bbci.co.uk/news/rss.xml", "left-center", "high"),
        ("CBS News", "https://www.cbsnews.com/latest/rss/main", "left-center", "high"),
        ("ABC News", "https://abcnews.go.com/abcnews/topstories", "left-center", "high"),
        ("Politico", "https://www.politico.com/rss/politicopicks.xml", "left-center", "high"),

        # Center
        ("Reuters", "https://www.reutersagency.com/feed/", "center", "high"),
        ("Associated Press", "https://rsshub.app/apnews/topics/apf-topnews", "center", "high"),
        ("The Hill", "https://thehill.com/feed/", "center", "high"),
        ("USA Today", "http://rssfeeds.usatoday.com/usatoday-NewsTopStories", "center", "high"),
        ("C-SPAN", "https://www.c-span.org/feeds/", "center", "high"),

        # Right-center
        ("Wall Street Journal", "https://feeds.a]content.wsj.com/rss/RSSWorldNews.xml", "right-center", "high"),
        ("The Economist", "https://www.economist.com/united-states/rss.xml", "right-center", "high"),
        ("Forbes", "https://www.forbes.com/news/feed/", "right-center", "high"),

        # Right
        ("Fox News", "https://moxie.foxnews.com/google-publisher/latest.xml", "right", "mixed"),
        ("Washington Examiner", "https://www.washingtonexaminer.com/feed", "right", "mixed"),
        ("New York Post", "https://nypost.com/feed/", "right", "mixed"),
        ("Daily Wire", "https://www.dailywire.com/feeds/rss.xml", "right", "mixed"),
        ("The Federalist", "https://thefederalist.com/feed/", "right", "mixed"),
        ("Breitbart", "https://feeds.feedburner.com/breitbart", "right", "mixed"),

        # International perspectives
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "left-center", "high"),
        ("France 24", "https://www.france24.com/en/rss", "center", "high"),
        ("DW", "https://rss.dw.com/rdf/rss-en-all", "center", "high"),
    ]

    def __init__(self, *args, max_age_days: int = 7, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_age = timedelta(days=max_age_days)
        self.cutoff_date = datetime.now() - self.max_age

    def start_requests(self):
        """Request all RSS feeds."""
        for name, url, bias, factuality in self.RSS_SOURCES:
            yield Request(
                url,
                callback=self.parse_feed,
                meta={
                    "outlet": name,
                    "bias": bias,
                    "factuality": factuality,
                },
                errback=self.handle_feed_error,
            )

    def handle_feed_error(self, failure):
        """Log feed errors but continue."""
        self.logger.warning(f"Failed to fetch feed: {failure.request.url}")

    def parse_feed(self, response):
        """Parse RSS feed and extract articles."""
        outlet = response.meta["outlet"]
        bias = response.meta["bias"]
        factuality = response.meta["factuality"]

        # Parse with feedparser
        feed = feedparser.parse(response.text)

        for entry in feed.entries:
            # Extract publication date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6])

            # Skip old articles
            if pub_date and pub_date < self.cutoff_date:
                continue

            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))

            # Clean HTML from summary
            summary = re.sub(r'<[^>]+>', '', summary)

            if title and link:
                yield self.create_item(
                    content=json.dumps({
                        "headline": title,
                        "summary": summary[:1000],  # Truncate long summaries
                        "url": link,
                        "outlet": outlet,
                        "bias": bias,
                        "factuality": factuality,
                        "published": pub_date.isoformat() if pub_date else None,
                    }),
                    title=title,
                    url=link,
                    metadata={
                        "outlet": outlet,
                        "bias": bias,
                        "factuality": factuality,
                        "published": pub_date.isoformat() if pub_date else None,
                        "type": "news_article",
                        "has_full_text": False,
                    }
                )


class FullArticleSpider(BaseSpider):
    """
    Fetches full article text from news URLs.

    Uses archive.today and direct fetching with paywall bypass techniques.
    Intended to be fed URLs from RSSNewsSpider results.
    """

    name = "full_article_spider"
    source = "news_articles"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 2,
        "ROBOTSTXT_OBEY": False,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    }

    # Sites with soft paywalls (JavaScript-based)
    SOFT_PAYWALL_SITES = [
        "nytimes.com", "washingtonpost.com", "wsj.com", "theatlantic.com",
        "wired.com", "newyorker.com", "bloomberg.com",
    ]

    # Sites that work better through archive
    USE_ARCHIVE_SITES = [
        "ft.com", "economist.com", "barrons.com",
    ]

    def __init__(self, *args, urls_file: str = None, urls: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_urls = []

        if urls_file:
            with open(urls_file) as f:
                self.target_urls = [line.strip() for line in f if line.strip()]
        elif urls:
            self.target_urls = [u.strip() for u in urls.split(",")]

    def start_requests(self):
        """Start fetching articles."""
        for url in self.target_urls:
            domain = urlparse(url).netloc

            # Decide fetch strategy
            if any(site in domain for site in self.USE_ARCHIVE_SITES):
                # Try archive.today first
                archive_url = f"https://archive.today/newest/{url}"
                yield Request(
                    archive_url,
                    callback=self.parse_archive,
                    meta={"original_url": url},
                    errback=lambda f, u=url: self.try_direct(u),
                )
            else:
                # Direct fetch with headers
                yield Request(
                    url,
                    callback=self.parse_article,
                    meta={"original_url": url},
                )

    def try_direct(self, url):
        """Fallback to direct fetch."""
        return Request(url, callback=self.parse_article, meta={"original_url": url})

    def parse_archive(self, response):
        """Parse archived version of article."""
        original_url = response.meta["original_url"]

        # Archive.today wraps content
        article_text = self._extract_article_text(response)

        if article_text and len(article_text) > 200:
            yield self.create_item(
                content=article_text,
                title=response.css("title::text").get() or "Unknown",
                url=original_url,
                metadata={
                    "fetched_via": "archive.today",
                    "type": "full_article",
                }
            )

    def parse_article(self, response):
        """Parse article directly."""
        original_url = response.meta.get("original_url", response.url)

        article_text = self._extract_article_text(response)
        title = response.css("title::text").get() or ""

        # Try to get cleaner title from meta
        og_title = response.css("meta[property='og:title']::attr(content)").get()
        if og_title:
            title = og_title

        if article_text and len(article_text) > 200:
            yield self.create_item(
                content=article_text,
                title=title,
                url=original_url,
                metadata={
                    "fetched_via": "direct",
                    "type": "full_article",
                    "word_count": len(article_text.split()),
                }
            )

    def _extract_article_text(self, response) -> str:
        """Extract main article text from page."""
        # Try common article containers
        selectors = [
            "article",
            "[class*='article-body']",
            "[class*='story-body']",
            "[class*='post-content']",
            "[class*='entry-content']",
            ".content-body",
            "#article-body",
            "main",
        ]

        for selector in selectors:
            container = response.css(selector)
            if container:
                # Get all paragraph text
                paragraphs = container.css("p::text, p *::text").getall()
                if paragraphs:
                    text = " ".join(p.strip() for p in paragraphs if p.strip())
                    if len(text) > 500:  # Likely found the article
                        return text

        # Fallback: get all paragraphs
        all_paragraphs = response.css("p::text, p *::text").getall()
        return " ".join(p.strip() for p in all_paragraphs if p.strip())


class StoryClustersSpider(BaseSpider):
    """
    Groups related news stories across outlets.

    Uses headline similarity to identify same-story coverage.
    This enables "blindspot" analysis - what stories left/right miss.

    Note: This spider reads from the database, not the web.
    Run RSSNewsSpider first to populate headlines.
    """

    name = "story_clusters_spider"
    source = "story_clusters"

    def __init__(self, *args, similarity_threshold: float = 0.7, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = similarity_threshold
        self.headlines = []

    def start_requests(self):
        """
        This spider doesn't make web requests.
        It processes existing data from the database.
        """
        # Placeholder - actual clustering happens in closed()
        yield Request(
            "https://example.com",
            callback=self.dummy_parse,
            dont_filter=True,
        )

    def dummy_parse(self, response):
        """Placeholder for Scrapy's request flow."""
        pass

    def closed(self, reason):
        """
        Perform clustering when spider closes.

        In production, this would:
        1. Load recent headlines from PostgreSQL
        2. Generate embeddings using sentence-transformers
        3. Cluster similar headlines
        4. Calculate bias distribution per cluster
        5. Identify "blindspots"
        """
        self.logger.info("Story clustering would run here with embeddings")
        self.logger.info("Requires: pip install sentence-transformers")
        # Implementation note: Use all-MiniLM-L6-v2 for fast embeddings
        # Then HDBSCAN or agglomerative clustering
