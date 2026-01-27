"""
Package Manager & Official Docs Spider

Targets official documentation for:
1. Homebrew (macOS package manager)
2. pip/PyPI (Python packages)
3. npm (Node.js packages)
4. apt/dpkg (Debian/Ubuntu)
5. Other package managers

Also includes general developer documentation sites.
"""

import json
import logging
import html
import re
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

try:
    from scrapy.http import Request, Response
    from scrapy.linkextractors import LinkExtractor
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class DocsSpider(BaseSpider):
    """
    Spider for official package manager and developer documentation.

    Crawls structured documentation sites to extract:
    - Installation instructions
    - Command references
    - Troubleshooting guides
    - Configuration options

    Usage:
        # Scrape all configured doc sites
        scrapy crawl docs

        # Scrape specific site
        scrapy crawl docs -a site=homebrew
    """

    name = "docs_spider"
    source = "docs"

    # Documentation sites and their configurations
    DOC_SITES = {
        "homebrew": {
            "name": "Homebrew",
            "start_urls": [
                "https://docs.brew.sh/",
                "https://docs.brew.sh/Manpage",
                "https://docs.brew.sh/FAQ",
                "https://docs.brew.sh/Installation",
                "https://docs.brew.sh/Troubleshooting",
            ],
            "allowed_domains": ["docs.brew.sh"],
            "content_selector": "article, .markdown-body, main",
            "link_patterns": [r"/.*"],
            "max_depth": 3,
        },
        "pip": {
            "name": "pip/PyPI",
            "start_urls": [
                "https://pip.pypa.io/en/stable/",
                "https://pip.pypa.io/en/stable/installation/",
                "https://pip.pypa.io/en/stable/getting-started/",
                "https://pip.pypa.io/en/stable/cli/",
                "https://packaging.python.org/en/latest/tutorials/installing-packages/",
            ],
            "allowed_domains": ["pip.pypa.io", "packaging.python.org"],
            "content_selector": "article, .document, main, [role='main']",
            "link_patterns": [r"/en/stable/.*", r"/en/latest/.*"],
            "max_depth": 3,
        },
        "npm": {
            "name": "npm",
            "start_urls": [
                "https://docs.npmjs.com/",
                "https://docs.npmjs.com/cli/v10/commands",
                "https://docs.npmjs.com/getting-started",
                "https://docs.npmjs.com/packages-and-modules",
            ],
            "allowed_domains": ["docs.npmjs.com"],
            "content_selector": "article, main, .markdown-body",
            "link_patterns": [r"/.*"],
            "max_depth": 3,
        },
        "docker": {
            "name": "Docker",
            "start_urls": [
                "https://docs.docker.com/get-started/",
                "https://docs.docker.com/engine/install/",
                "https://docs.docker.com/reference/cli/docker/",
                "https://docs.docker.com/compose/",
            ],
            "allowed_domains": ["docs.docker.com"],
            "content_selector": "article, main, .content",
            "link_patterns": [r"/.*"],
            "max_depth": 2,
        },
        "git": {
            "name": "Git",
            "start_urls": [
                "https://git-scm.com/doc",
                "https://git-scm.com/book/en/v2/Getting-Started-Installing-Git",
                "https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository",
            ],
            "allowed_domains": ["git-scm.com"],
            "content_selector": "#main, article, .book-content",
            "link_patterns": [r"/book/.*", r"/doc.*"],
            "max_depth": 2,
        },
        "python": {
            "name": "Python",
            "start_urls": [
                "https://docs.python.org/3/tutorial/",
                "https://docs.python.org/3/installing/index.html",
                "https://docs.python.org/3/using/index.html",
            ],
            "allowed_domains": ["docs.python.org"],
            "content_selector": ".document, article, main",
            "link_patterns": [r"/3/tutorial/.*", r"/3/installing/.*", r"/3/using/.*"],
            "max_depth": 2,
        },
        "nodejs": {
            "name": "Node.js",
            "start_urls": [
                "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs",
                "https://nodejs.org/en/learn/getting-started/how-to-install-nodejs",
            ],
            "allowed_domains": ["nodejs.org"],
            "content_selector": "article, main, .content",
            "link_patterns": [r"/en/learn/.*"],
            "max_depth": 2,
        },
        "rust": {
            "name": "Rust",
            "start_urls": [
                "https://www.rust-lang.org/learn/get-started",
                "https://doc.rust-lang.org/book/ch01-01-installation.html",
                "https://doc.rust-lang.org/cargo/",
            ],
            "allowed_domains": ["rust-lang.org", "doc.rust-lang.org"],
            "content_selector": "#content, main, article",
            "link_patterns": [r"/book/.*", r"/cargo/.*"],
            "max_depth": 2,
        },
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
        "DEPTH_LIMIT": 3,
    }

    def __init__(self, *args, site: str = None, max_pages: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.pages_scraped = 0
        self.visited_urls = set()

        # Filter to specific site or scrape all
        if site:
            if site in self.DOC_SITES:
                self.sites_to_scrape = {site: self.DOC_SITES[site]}
            else:
                logger.warning(f"Unknown site '{site}', scraping all")
                self.sites_to_scrape = self.DOC_SITES
        else:
            self.sites_to_scrape = self.DOC_SITES

    def start_requests(self) -> Iterator[Request]:
        """Start by crawling doc site entry points."""
        for site_id, config in self.sites_to_scrape.items():
            for url in config["start_urls"]:
                yield self.make_request(
                    url,
                    callback=self.parse_doc_page,
                    meta={
                        "site_id": site_id,
                        "config": config,
                        "depth": 0,
                    }
                )

    def parse_doc_page(self, response: Response) -> Iterator:
        """Parse a documentation page."""
        site_id = response.meta.get("site_id", "unknown")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)

        url = response.url

        # Skip if already visited
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        if self.pages_scraped >= self.max_pages:
            return

        # Extract content
        content_selector = config.get("content_selector", "main, article")
        content_elem = response.css(content_selector)

        if content_elem:
            # Get text content
            raw_html = content_elem.get()
            content = self._clean_html(raw_html)

            if content and len(content) > 200:
                self.pages_scraped += 1

                # Extract title
                title = response.css("title::text").get() or ""
                title = title.strip()
                if " | " in title:
                    title = title.split(" | ")[0]
                if " - " in title:
                    title = title.split(" - ")[0]

                # Analyze content
                content_lower = content.lower()

                has_installation = any(inst in content_lower for inst in [
                    "install", "setup", "getting started", "quick start",
                ])

                has_commands = any(cmd in content_lower for cmd in [
                    "command", "usage", "syntax", "options", "flags",
                ])

                has_troubleshooting = any(ts in content_lower for ts in [
                    "troubleshoot", "error", "problem", "issue", "fix",
                    "faq", "common issues", "known issues",
                ])

                has_examples = "```" in content or "example" in content_lower

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": "documentation",
                        "author": config.get("name", site_id),
                        "site": site_id,
                        "site_name": config.get("name", ""),
                        "depth": depth,
                        "has_installation": has_installation,
                        "has_commands": has_commands,
                        "has_troubleshooting": has_troubleshooting,
                        "has_examples": has_examples,
                    }
                )

        # Follow links if within depth limit
        max_depth = config.get("max_depth", 2)
        if depth < max_depth:
            allowed_domains = config.get("allowed_domains", [])
            link_patterns = config.get("link_patterns", [])

            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                # Check domain
                if parsed.netloc and not any(d in parsed.netloc for d in allowed_domains):
                    continue

                # Check path pattern
                if link_patterns:
                    if not any(re.match(p, parsed.path) for p in link_patterns):
                        continue

                # Skip already visited
                if full_url in self.visited_urls:
                    continue

                # Skip non-HTML resources
                if any(full_url.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.pdf', '.zip']):
                    continue

                yield self.make_request(
                    full_url,
                    callback=self.parse_doc_page,
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

        # Remove script and style tags
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


# Register with the spider registry
def register():
    return {
        "name": "docs",
        "spider_class": DocsSpider,
        "description": "Package Manager Docs",
        "type": "code",
        "priority": 1,
    }
