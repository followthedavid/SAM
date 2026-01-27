"""
Dev.to Spider - Scrapes beginner-friendly tutorials and articles

Targets:
1. Beginner tutorials (tagged #beginners, #tutorial)
2. Installation guides
3. How-to articles
4. Best practices
5. Error solutions

Uses Dev.to's public API.
"""

import json
import logging
import html
import re
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlencode

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class DevToSpider(BaseSpider):
    """
    Spider for Dev.to articles and tutorials.

    Focuses on:
    - Beginner-friendly content
    - Installation/setup tutorials
    - How-to guides
    - Coding best practices

    Usage:
        # Scrape general tutorials
        scrapy crawl devto

        # Focus on specific tags
        scrapy crawl devto -a tags="python,javascript,tutorial"
    """

    name = "devto_spider"
    source = "devto"

    # Dev.to API
    API_BASE = "https://dev.to/api"

    # Tags for beginners and tutorials
    BEGINNER_TAGS = [
        "beginners", "tutorial", "learning", "codenewbie",
        "programming", "webdev", "100daysofcode",
        "todayilearned", "help", "discuss",
    ]

    # Tags for installation/setup
    INSTALLER_TAGS = [
        "installation", "setup", "configuration", "devops",
        "docker", "kubernetes", "git", "github",
        "homebrew", "npm", "pip", "environment",
        "terminal", "cli", "bash", "shell", "linux", "macos",
    ]

    # Tags for debugging
    DEBUG_TAGS = [
        "debugging", "errors", "troubleshooting", "tips",
        "bestpractices", "productivity", "workflow",
    ]

    # Language-specific tags
    LANGUAGE_TAGS = [
        "python", "javascript", "typescript", "go", "rust",
        "node", "react", "vue", "nextjs", "fastapi",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.5,  # Dev.to is generous
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, tags: str = None, min_reactions: int = 10,
                 max_articles: int = 2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_reactions = int(min_reactions)
        self.max_articles = int(max_articles)
        self.articles_scraped = 0

        # Parse custom tags or use defaults
        if tags:
            self.tags = [t.strip() for t in tags.split(",")]
        else:
            self.tags = (self.BEGINNER_TAGS + self.INSTALLER_TAGS +
                        self.DEBUG_TAGS + self.LANGUAGE_TAGS)

    def start_requests(self) -> Iterator[Request]:
        """Start by fetching articles for each tag."""
        for tag in self.tags:
            url = f"{self.API_BASE}/articles?tag={tag}&per_page=30&page=1"

            yield self.make_request(
                url,
                callback=self.parse_articles,
                meta={"tag": tag, "page": 1}
            )

    def parse_articles(self, response: Response) -> Iterator:
        """Parse Dev.to article listings."""
        tag = response.meta.get("tag", "unknown")
        page = response.meta.get("page", 1)

        try:
            articles = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {response.url}")
            return

        if not articles:
            return

        logger.info(f"Tag '{tag}' page {page}: {len(articles)} articles")

        for article in articles:
            if self.articles_scraped >= self.max_articles:
                logger.info(f"Reached max articles limit ({self.max_articles})")
                return

            # Filter by reactions
            reactions = article.get("public_reactions_count", 0)
            if reactions < self.min_reactions:
                continue

            article_id = article.get("id")
            url = article.get("url", "")

            # Skip if already scraped
            if self._db and self._db.url_exists(url):
                continue

            self.articles_scraped += 1

            # Fetch full article content
            yield self.make_request(
                f"{self.API_BASE}/articles/{article_id}",
                callback=self.parse_full_article,
                meta={"article_meta": article, "tag": tag}
            )

        # Pagination (max 10 pages per tag)
        if len(articles) == 30 and page < 10:
            next_url = f"{self.API_BASE}/articles?tag={tag}&per_page=30&page={page+1}"

            yield self.make_request(
                next_url,
                callback=self.parse_articles,
                meta={"tag": tag, "page": page + 1}
            )

    def parse_full_article(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse full article content."""
        article_meta = response.meta.get("article_meta", {})
        tag = response.meta.get("tag", "")

        try:
            article = json.loads(response.text)
        except json.JSONDecodeError:
            return

        title = article.get("title", "")
        body_markdown = article.get("body_markdown", "")
        body_html = article.get("body_html", "")

        # Prefer markdown, fall back to HTML
        if body_markdown:
            content = body_markdown
        elif body_html:
            content = self._clean_html(body_html)
        else:
            return

        if len(content) < 200:  # Too short
            return

        url = article.get("url", "")

        # Analyze content for training value
        content_lower = content.lower()

        # Check for tutorial patterns
        is_tutorial = any(tut in content_lower for tut in [
            "step 1", "step 2", "how to", "let's build",
            "getting started", "tutorial", "guide", "walkthrough",
        ])

        # Check for installation patterns
        has_installation = any(inst in content_lower for inst in [
            "install", "setup", "configure", "npm install",
            "pip install", "brew install", "apt install",
        ])

        # Check for code examples
        has_code = "```" in content or "`" in content

        # Check for beginner-friendly markers
        is_beginner = any(beg in content_lower for beg in [
            "beginner", "newbie", "first time", "new to",
            "introduction", "basics", "fundamental", "101",
        ])

        # Check for error/debugging content
        has_debugging = any(debug in content_lower for debug in [
            "error", "debug", "fix", "solution", "troubleshoot",
            "problem", "issue", "bug", "mistake",
        ])

        yield ScrapedItem(
            source=self.source,
            url=url,
            title=title,
            content=content,
            metadata={
                "type": "tutorial",
                "author": article.get("user", {}).get("username", ""),
                "tag": tag,
                "all_tags": article.get("tags", []),
                "reactions": article.get("public_reactions_count", 0),
                "comments": article.get("comments_count", 0),
                "reading_time": article.get("reading_time_minutes", 0),
                "is_tutorial": is_tutorial,
                "has_installation": has_installation,
                "has_code": has_code,
                "is_beginner": is_beginner,
                "has_debugging": has_debugging,
                "published_at": article.get("published_at"),
            }
        )

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to markdown-ish text."""
        if not html_content:
            return ""

        text = html_content

        # Convert code blocks
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
                     r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

        # Convert links
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text)

        # Convert headers
        text = re.sub(r'<h(\d)[^>]*>(.*?)</h\d>',
                     lambda m: '#' * int(m.group(1)) + ' ' + m.group(2), text)

        # Convert paragraphs and line breaks
        text = re.sub(r'<p[^>]*>', '\n\n', text)
        text = re.sub(r'</p>', '', text)
        text = re.sub(r'<br\s*/?>', '\n', text)

        # Convert lists
        text = re.sub(r'<li>(.*?)</li>', r'- \1\n', text)
        text = re.sub(r'<[uo]l[^>]*>', '', text)
        text = re.sub(r'</[uo]l>', '', text)

        # Convert bold/italic
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)

        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


class HashNodeSpider(BaseSpider):
    """
    Spider for Hashnode articles - similar to Dev.to but different API.

    Hashnode uses GraphQL API.
    """

    name = "hashnode_spider"
    source = "hashnode"

    # Hashnode GraphQL API
    API_BASE = "https://gql.hashnode.com"

    TAGS = [
        "programming", "javascript", "python", "tutorial",
        "beginners", "webdev", "devops", "linux",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
    }

    def __init__(self, *args, max_articles: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_articles = int(max_articles)
        self.articles_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start with GraphQL queries."""
        for tag in self.TAGS:
            query = """
            query GetTagFeed($slug: String!, $first: Int!) {
                tag(slug: $slug) {
                    posts(first: $first) {
                        edges {
                            node {
                                id
                                title
                                brief
                                slug
                                url
                                content {
                                    markdown
                                }
                                author {
                                    username
                                }
                                reactionCount
                                responseCount
                                publishedAt
                            }
                        }
                    }
                }
            }
            """

            yield self.make_request(
                self.API_BASE,
                method="POST",
                callback=self.parse_hashnode,
                meta={"tag": tag},
                body=json.dumps({
                    "query": query,
                    "variables": {"slug": tag, "first": 20}
                }),
                headers={"Content-Type": "application/json"}
            )

    def parse_hashnode(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse Hashnode GraphQL response."""
        tag = response.meta.get("tag", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        posts = data.get("data", {}).get("tag", {}).get("posts", {}).get("edges", [])

        for edge in posts:
            if self.articles_scraped >= self.max_articles:
                return

            node = edge.get("node", {})
            url = node.get("url", "")

            if self._db and self._db.url_exists(url):
                continue

            self.articles_scraped += 1

            content = node.get("content", {}).get("markdown", "")
            if not content or len(content) < 200:
                continue

            yield ScrapedItem(
                source=self.source,
                url=url,
                title=node.get("title", ""),
                content=content,
                metadata={
                    "type": "tutorial",
                    "author": node.get("author", {}).get("username", ""),
                    "tag": tag,
                    "reactions": node.get("reactionCount", 0),
                    "comments": node.get("responseCount", 0),
                    "published_at": node.get("publishedAt"),
                }
            )


# Register with the spider registry
def register():
    return [
        {
            "name": "devto",
            "spider_class": DevToSpider,
            "description": "Dev.to Tutorials",
            "type": "code",
            "priority": 2,
        },
        {
            "name": "hashnode",
            "spider_class": HashNodeSpider,
            "description": "Hashnode Articles",
            "type": "code",
            "priority": 3,
        },
    ]
