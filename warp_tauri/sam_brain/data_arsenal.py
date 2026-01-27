#!/usr/bin/env python3
"""
SAM Data Arsenal

Intelligence gathering through:
- Site ripping and scraping
- API harvesting
- Document extraction
- Pattern mining
- Trend monitoring

Philosophy:
- Gather intelligence from everywhere
- Extract what matters, discard noise
- Store structured, searchable data
- Respect rate limits (but be thorough)
- Build a knowledge base that grows

This is SAM's eyes and ears on the world.
"""

import json
import time
import hashlib
import sqlite3
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Generator
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin
import asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class SourceType(Enum):
    """Types of data sources"""
    WEBSITE = "website"           # General web scraping
    GITHUB = "github"             # GitHub repos, issues, releases
    HACKERNEWS = "hackernews"     # HN posts and comments
    REDDIT = "reddit"             # Subreddit posts
    ARXIV = "arxiv"               # Research papers
    DOCUMENTATION = "documentation"  # Software docs
    API = "api"                   # API endpoints
    RSS = "rss"                   # RSS/Atom feeds
    EXPORT = "export"             # Exported data (Claude, ChatGPT, etc.)
    LOCAL = "local"               # Local files


class ExtractionType(Enum):
    """What to extract from sources"""
    FULL_CONTENT = "full_content"     # Everything
    ARTICLE = "article"               # Main article text
    CODE = "code"                     # Code blocks only
    LINKS = "links"                   # All links
    METADATA = "metadata"             # Title, date, author
    STRUCTURED = "structured"         # JSON-LD, schema.org
    PATTERNS = "patterns"             # UI/UX patterns
    CHANGELOG = "changelog"           # Version changes


@dataclass
class SourceConfig:
    """Configuration for a data source"""
    name: str
    source_type: SourceType
    url: str

    # Scraping config
    selectors: Dict = field(default_factory=dict)  # CSS selectors
    rate_limit_ms: int = 1000  # Delay between requests
    max_depth: int = 2  # Link following depth
    max_pages: int = 100

    # Extraction config
    extraction_types: List[ExtractionType] = field(default_factory=list)

    # Filtering
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)

    # Schedule
    refresh_hours: int = 24  # How often to re-scrape

    # Auth (if needed)
    auth_type: str = ""  # "bearer", "basic", "cookie"
    auth_value: str = ""


@dataclass
class ScrapedItem:
    """A single scraped item"""
    id: str
    source_name: str
    source_type: str
    url: str

    title: str
    content: str
    content_type: str  # "article", "code", "discussion", etc.

    metadata: Dict
    extracted_patterns: List[str]
    extracted_code: List[str]
    extracted_links: List[str]

    scraped_at: str
    content_hash: str  # For deduplication


@dataclass
class Pattern:
    """An extracted pattern or insight"""
    id: str
    name: str
    description: str
    category: str  # "ui", "api", "architecture", "algorithm"

    source_url: str
    source_name: str

    implementation_hint: str
    code_example: str

    relevance_score: float  # 0-1, how relevant to SAM
    discovered_at: str


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-CONFIGURED SOURCES
# ═══════════════════════════════════════════════════════════════════════════════

PRECONFIGURED_SOURCES = {
    "github_trending": SourceConfig(
        name="GitHub Trending",
        source_type=SourceType.GITHUB,
        url="https://github.com/trending",
        extraction_types=[ExtractionType.LINKS, ExtractionType.METADATA],
        rate_limit_ms=2000,
        max_pages=5,
        refresh_hours=12,
    ),

    "hackernews_front": SourceConfig(
        name="Hacker News",
        source_type=SourceType.HACKERNEWS,
        url="https://news.ycombinator.com",
        extraction_types=[ExtractionType.LINKS, ExtractionType.METADATA],
        selectors={"items": ".athing", "title": ".titleline > a"},
        rate_limit_ms=1000,
        max_pages=3,
        refresh_hours=6,
    ),

    "ollama_releases": SourceConfig(
        name="Ollama Releases",
        source_type=SourceType.GITHUB,
        url="https://github.com/ollama/ollama/releases",
        extraction_types=[ExtractionType.CHANGELOG, ExtractionType.METADATA],
        rate_limit_ms=2000,
        max_pages=1,
        refresh_hours=24,
    ),

    "tauri_releases": SourceConfig(
        name="Tauri Releases",
        source_type=SourceType.GITHUB,
        url="https://github.com/tauri-apps/tauri/releases",
        extraction_types=[ExtractionType.CHANGELOG, ExtractionType.METADATA],
        rate_limit_ms=2000,
        max_pages=1,
        refresh_hours=24,
    ),

    "arxiv_ai": SourceConfig(
        name="arXiv AI Papers",
        source_type=SourceType.ARXIV,
        url="https://arxiv.org/list/cs.AI/recent",
        extraction_types=[ExtractionType.METADATA, ExtractionType.ARTICLE],
        rate_limit_ms=3000,
        max_pages=2,
        refresh_hours=24,
    ),

    "reddit_localllama": SourceConfig(
        name="r/LocalLLaMA",
        source_type=SourceType.REDDIT,
        url="https://www.reddit.com/r/LocalLLaMA/hot.json",
        extraction_types=[ExtractionType.FULL_CONTENT, ExtractionType.LINKS],
        rate_limit_ms=2000,
        max_pages=2,
        refresh_hours=12,
    ),

    "warp_docs": SourceConfig(
        name="Warp Documentation",
        source_type=SourceType.DOCUMENTATION,
        url="https://docs.warp.dev",
        extraction_types=[ExtractionType.ARTICLE, ExtractionType.PATTERNS],
        rate_limit_ms=1500,
        max_depth=3,
        max_pages=50,
        refresh_hours=168,  # Weekly
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA ARSENAL
# ═══════════════════════════════════════════════════════════════════════════════

class DataArsenal:
    """
    SAM's intelligence gathering system.

    Capabilities:
    - Web scraping with rate limiting
    - Content extraction and parsing
    - Pattern recognition
    - Deduplication
    - Scheduled refreshes
    - Full-text search
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".sam" / "data_arsenal.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.sources = dict(PRECONFIGURED_SOURCES)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Scraped items
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    source_name TEXT,
                    source_type TEXT,
                    url TEXT UNIQUE,
                    title TEXT,
                    content TEXT,
                    content_type TEXT,
                    metadata TEXT,
                    extracted_patterns TEXT,
                    extracted_code TEXT,
                    extracted_links TEXT,
                    scraped_at TEXT,
                    content_hash TEXT
                )
            """)

            # Patterns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    category TEXT,
                    source_url TEXT,
                    source_name TEXT,
                    implementation_hint TEXT,
                    code_example TEXT,
                    relevance_score REAL,
                    discovered_at TEXT
                )
            """)

            # Scrape history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_log (
                    id INTEGER PRIMARY KEY,
                    source_name TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    items_found INTEGER,
                    items_new INTEGER,
                    errors TEXT,
                    status TEXT
                )
            """)

            # Full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS items_fts
                USING fts5(title, content, source_name, content='items', content_rowid='rowid')
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category)")

    # ═══════════════════════════════════════════════════════════════════════
    # SCRAPING
    # ═══════════════════════════════════════════════════════════════════════

    def scrape_source(self, source_name: str) -> Dict:
        """Scrape a configured source"""
        if source_name not in self.sources:
            return {"error": f"Unknown source: {source_name}"}

        config = self.sources[source_name]

        # Log start
        log_id = self._log_scrape_start(source_name)

        try:
            if config.source_type == SourceType.GITHUB:
                items = self._scrape_github(config)
            elif config.source_type == SourceType.HACKERNEWS:
                items = self._scrape_hackernews(config)
            elif config.source_type == SourceType.REDDIT:
                items = self._scrape_reddit(config)
            elif config.source_type == SourceType.ARXIV:
                items = self._scrape_arxiv(config)
            elif config.source_type == SourceType.DOCUMENTATION:
                items = self._scrape_documentation(config)
            elif config.source_type == SourceType.RSS:
                items = self._scrape_rss(config)
            else:
                items = self._scrape_generic(config)

            # Store items
            new_count = 0
            for item in items:
                if self._store_item(item):
                    new_count += 1

            # Log completion
            self._log_scrape_complete(log_id, len(items), new_count, None, "completed")

            return {
                "source": source_name,
                "items_found": len(items),
                "items_new": new_count,
                "status": "completed"
            }

        except Exception as e:
            self._log_scrape_complete(log_id, 0, 0, str(e), "failed")
            return {"error": str(e)}

    def _scrape_generic(self, config: SourceConfig) -> List[ScrapedItem]:
        """Generic web scraping with trafilatura"""
        items = []

        try:
            # Try trafilatura first (best for article extraction)
            import trafilatura

            downloaded = trafilatura.fetch_url(config.url)
            if downloaded:
                content = trafilatura.extract(
                    downloaded,
                    include_links=True,
                    include_formatting=True
                )

                if content:
                    item_id = hashlib.md5(config.url.encode()).hexdigest()[:16]
                    items.append(ScrapedItem(
                        id=item_id,
                        source_name=config.name,
                        source_type=config.source_type.value,
                        url=config.url,
                        title=trafilatura.extract_metadata(downloaded).title or "",
                        content=content,
                        content_type="article",
                        metadata={},
                        extracted_patterns=[],
                        extracted_code=self._extract_code_blocks(content),
                        extracted_links=self._extract_links(content, config.url),
                        scraped_at=datetime.now().isoformat(),
                        content_hash=hashlib.md5(content.encode()).hexdigest()
                    ))
        except ImportError:
            # Fallback to requests + beautifulsoup
            items = self._scrape_with_bs4(config)

        return items

    def _scrape_with_bs4(self, config: SourceConfig) -> List[ScrapedItem]:
        """Fallback scraping with BeautifulSoup"""
        items = []

        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(config.url, timeout=30, headers={
                "User-Agent": "SAM/1.0 (Personal AI Assistant)"
            })
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Remove scripts, styles
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()

            # Get main content
            main = soup.find('main') or soup.find('article') or soup.find('body')
            content = main.get_text(separator='\n', strip=True) if main else ""

            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""

            item_id = hashlib.md5(config.url.encode()).hexdigest()[:16]
            items.append(ScrapedItem(
                id=item_id,
                source_name=config.name,
                source_type=config.source_type.value,
                url=config.url,
                title=title_text,
                content=content[:50000],  # Limit size
                content_type="webpage",
                metadata={},
                extracted_patterns=[],
                extracted_code=self._extract_code_from_soup(soup),
                extracted_links=self._extract_links_from_soup(soup, config.url),
                scraped_at=datetime.now().isoformat(),
                content_hash=hashlib.md5(content.encode()).hexdigest()
            ))

        except Exception as e:
            print(f"BS4 scrape failed: {e}")

        return items

    def _scrape_github(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape GitHub pages (trending, releases, etc.)"""
        items = []

        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(config.url, timeout=30, headers={
                "User-Agent": "SAM/1.0"
            })
            soup = BeautifulSoup(resp.text, 'html.parser')

            # For trending page
            if "trending" in config.url:
                repos = soup.select('article.Box-row')
                for repo in repos[:config.max_pages * 10]:
                    link = repo.select_one('h2 a')
                    if link:
                        href = link.get('href', '')
                        repo_url = f"https://github.com{href}"
                        desc = repo.select_one('p')

                        item_id = hashlib.md5(repo_url.encode()).hexdigest()[:16]
                        items.append(ScrapedItem(
                            id=item_id,
                            source_name=config.name,
                            source_type="github",
                            url=repo_url,
                            title=href.strip('/'),
                            content=desc.get_text(strip=True) if desc else "",
                            content_type="repository",
                            metadata={"stars": self._extract_stars(repo)},
                            extracted_patterns=[],
                            extracted_code=[],
                            extracted_links=[repo_url],
                            scraped_at=datetime.now().isoformat(),
                            content_hash=hashlib.md5(repo_url.encode()).hexdigest()
                        ))

            # For releases page
            elif "releases" in config.url:
                releases = soup.select('.Box-body')
                for release in releases[:5]:
                    title_el = release.select_one('h2') or release.select_one('.f1')
                    body = release.select_one('.markdown-body')

                    if title_el:
                        item_id = hashlib.md5(f"{config.url}-{title_el.get_text()}".encode()).hexdigest()[:16]
                        items.append(ScrapedItem(
                            id=item_id,
                            source_name=config.name,
                            source_type="github",
                            url=config.url,
                            title=title_el.get_text(strip=True),
                            content=body.get_text(strip=True) if body else "",
                            content_type="release",
                            metadata={},
                            extracted_patterns=[],
                            extracted_code=self._extract_code_from_soup(body) if body else [],
                            extracted_links=[],
                            scraped_at=datetime.now().isoformat(),
                            content_hash=hashlib.md5(title_el.get_text().encode()).hexdigest()
                        ))

        except Exception as e:
            print(f"GitHub scrape failed: {e}")

        return items

    def _scrape_hackernews(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape Hacker News"""
        items = []

        try:
            import requests

            # Use the API
            resp = requests.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=30
            )
            story_ids = resp.json()[:30]  # Top 30

            for story_id in story_ids:
                time.sleep(config.rate_limit_ms / 1000)

                story_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=30
                )
                story = story_resp.json()

                if story and story.get('type') == 'story':
                    item_id = f"hn_{story_id}"
                    items.append(ScrapedItem(
                        id=item_id,
                        source_name=config.name,
                        source_type="hackernews",
                        url=story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                        title=story.get('title', ''),
                        content=story.get('text', ''),
                        content_type="discussion",
                        metadata={
                            "score": story.get('score', 0),
                            "comments": story.get('descendants', 0),
                            "by": story.get('by', '')
                        },
                        extracted_patterns=[],
                        extracted_code=[],
                        extracted_links=[story.get('url', '')] if story.get('url') else [],
                        scraped_at=datetime.now().isoformat(),
                        content_hash=hashlib.md5(str(story_id).encode()).hexdigest()
                    ))

        except Exception as e:
            print(f"HN scrape failed: {e}")

        return items

    def _scrape_reddit(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape Reddit via JSON API"""
        items = []

        try:
            import requests

            url = config.url
            if not url.endswith('.json'):
                url = url.rstrip('/') + '.json'

            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "SAM/1.0 (Personal AI)"
            })
            data = resp.json()

            posts = data.get('data', {}).get('children', [])
            for post in posts[:25]:
                post_data = post.get('data', {})

                item_id = f"reddit_{post_data.get('id', '')}"
                items.append(ScrapedItem(
                    id=item_id,
                    source_name=config.name,
                    source_type="reddit",
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    title=post_data.get('title', ''),
                    content=post_data.get('selftext', ''),
                    content_type="discussion",
                    metadata={
                        "score": post_data.get('score', 0),
                        "comments": post_data.get('num_comments', 0),
                        "author": post_data.get('author', ''),
                        "subreddit": post_data.get('subreddit', '')
                    },
                    extracted_patterns=[],
                    extracted_code=self._extract_code_blocks(post_data.get('selftext', '')),
                    extracted_links=[post_data.get('url', '')] if post_data.get('url') else [],
                    scraped_at=datetime.now().isoformat(),
                    content_hash=hashlib.md5(item_id.encode()).hexdigest()
                ))

        except Exception as e:
            print(f"Reddit scrape failed: {e}")

        return items

    def _scrape_arxiv(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape arXiv papers"""
        items = []

        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(config.url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            entries = soup.select('dd')  # arXiv list format

            for entry in entries[:20]:
                title_el = entry.select_one('.list-title')
                abstract = entry.select_one('.mathjax')
                link = entry.select_one('a[href*="/abs/"]')

                if title_el and link:
                    paper_url = urljoin(config.url, link.get('href', ''))
                    item_id = hashlib.md5(paper_url.encode()).hexdigest()[:16]

                    items.append(ScrapedItem(
                        id=item_id,
                        source_name=config.name,
                        source_type="arxiv",
                        url=paper_url,
                        title=title_el.get_text(strip=True).replace('Title:', '').strip(),
                        content=abstract.get_text(strip=True) if abstract else "",
                        content_type="paper",
                        metadata={},
                        extracted_patterns=[],
                        extracted_code=[],
                        extracted_links=[paper_url],
                        scraped_at=datetime.now().isoformat(),
                        content_hash=hashlib.md5(paper_url.encode()).hexdigest()
                    ))

        except Exception as e:
            print(f"arXiv scrape failed: {e}")

        return items

    def _scrape_documentation(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape documentation sites with link following"""
        items = []
        visited = set()
        to_visit = [config.url]

        try:
            import requests
            from bs4 import BeautifulSoup

            while to_visit and len(visited) < config.max_pages:
                url = to_visit.pop(0)
                if url in visited:
                    continue

                visited.add(url)
                time.sleep(config.rate_limit_ms / 1000)

                try:
                    resp = requests.get(url, timeout=30, headers={
                        "User-Agent": "SAM/1.0"
                    })
                    soup = BeautifulSoup(resp.text, 'html.parser')

                    # Remove nav, footer, sidebar
                    for tag in soup(['nav', 'footer', 'aside', 'header']):
                        tag.decompose()

                    main = soup.find('main') or soup.find('article') or soup.find('.content')
                    if not main:
                        continue

                    content = main.get_text(separator='\n', strip=True)
                    title = soup.find('title')

                    item_id = hashlib.md5(url.encode()).hexdigest()[:16]
                    items.append(ScrapedItem(
                        id=item_id,
                        source_name=config.name,
                        source_type="documentation",
                        url=url,
                        title=title.get_text(strip=True) if title else "",
                        content=content[:30000],
                        content_type="documentation",
                        metadata={},
                        extracted_patterns=self._extract_patterns_from_docs(content),
                        extracted_code=self._extract_code_from_soup(main),
                        extracted_links=[],
                        scraped_at=datetime.now().isoformat(),
                        content_hash=hashlib.md5(content.encode()).hexdigest()
                    ))

                    # Follow links if depth allows
                    if len(visited) < config.max_pages:
                        base_domain = urlparse(config.url).netloc
                        for link in main.find_all('a', href=True):
                            href = link['href']
                            full_url = urljoin(url, href)

                            if urlparse(full_url).netloc == base_domain:
                                if full_url not in visited and full_url not in to_visit:
                                    to_visit.append(full_url)

                except Exception as e:
                    continue

        except ImportError:
            pass

        return items

    def _scrape_rss(self, config: SourceConfig) -> List[ScrapedItem]:
        """Scrape RSS/Atom feeds"""
        items = []

        try:
            import feedparser

            feed = feedparser.parse(config.url)

            for entry in feed.entries[:25]:
                item_id = hashlib.md5(entry.get('link', entry.get('id', '')).encode()).hexdigest()[:16]

                content = entry.get('summary', '') or entry.get('content', [{}])[0].get('value', '')

                items.append(ScrapedItem(
                    id=item_id,
                    source_name=config.name,
                    source_type="rss",
                    url=entry.get('link', ''),
                    title=entry.get('title', ''),
                    content=content,
                    content_type="article",
                    metadata={
                        "published": entry.get('published', ''),
                        "author": entry.get('author', '')
                    },
                    extracted_patterns=[],
                    extracted_code=self._extract_code_blocks(content),
                    extracted_links=[entry.get('link', '')],
                    scraped_at=datetime.now().isoformat(),
                    content_hash=hashlib.md5(content.encode()).hexdigest()
                ))

        except ImportError:
            print("feedparser not installed")
        except Exception as e:
            print(f"RSS scrape failed: {e}")

        return items

    # ═══════════════════════════════════════════════════════════════════════
    # EXTRACTION HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from markdown/text"""
        code_blocks = []

        # Fenced code blocks
        pattern = r'```[\w]*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        code_blocks.extend(matches)

        # Indented code blocks
        lines = text.split('\n')
        current_block = []
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                current_block.append(line.strip())
            else:
                if current_block:
                    code_blocks.append('\n'.join(current_block))
                    current_block = []

        return code_blocks[:10]  # Limit

    def _extract_code_from_soup(self, soup) -> List[str]:
        """Extract code from BeautifulSoup element"""
        code_blocks = []

        for code in soup.find_all(['code', 'pre']):
            text = code.get_text(strip=True)
            if len(text) > 20:  # Skip tiny snippets
                code_blocks.append(text[:2000])

        return code_blocks[:10]

    def _extract_links(self, text: str, base_url: str) -> List[str]:
        """Extract links from text"""
        pattern = r'https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+'
        links = re.findall(pattern, text)
        return list(set(links))[:50]

    def _extract_links_from_soup(self, soup, base_url: str) -> List[str]:
        """Extract links from BeautifulSoup"""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(base_url, href))
        return list(set(links))[:50]

    def _extract_patterns_from_docs(self, content: str) -> List[str]:
        """Try to identify patterns in documentation"""
        patterns = []

        # Look for common pattern indicators
        pattern_keywords = [
            'best practice', 'recommended', 'pattern', 'approach',
            'architecture', 'design', 'implementation', 'technique'
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in pattern_keywords:
                if keyword in line_lower and len(line) > 20:
                    # Get this line and next few for context
                    context = '\n'.join(lines[i:i+3])
                    patterns.append(context[:200])
                    break

        return patterns[:5]

    def _extract_stars(self, element) -> int:
        """Extract star count from GitHub element"""
        try:
            star_el = element.select_one('[href$="/stargazers"]')
            if star_el:
                text = star_el.get_text(strip=True).replace(',', '')
                if 'k' in text.lower():
                    return int(float(text.lower().replace('k', '')) * 1000)
                return int(text)
        except:
            pass
        return 0

    # ═══════════════════════════════════════════════════════════════════════
    # STORAGE
    # ═══════════════════════════════════════════════════════════════════════

    def _store_item(self, item: ScrapedItem) -> bool:
        """Store item, returns True if new"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT content_hash FROM items WHERE url = ?",
                (item.url,)
            ).fetchone()

            if existing and existing[0] == item.content_hash:
                return False  # Duplicate

            conn.execute("""
                INSERT OR REPLACE INTO items
                (id, source_name, source_type, url, title, content, content_type,
                 metadata, extracted_patterns, extracted_code, extracted_links,
                 scraped_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.source_name, item.source_type, item.url,
                item.title, item.content, item.content_type,
                json.dumps(item.metadata), json.dumps(item.extracted_patterns),
                json.dumps(item.extracted_code), json.dumps(item.extracted_links),
                item.scraped_at, item.content_hash
            ))

            # Update FTS
            conn.execute("""
                INSERT INTO items_fts (rowid, title, content, source_name)
                SELECT rowid, title, content, source_name FROM items WHERE id = ?
            """, (item.id,))

            return True

    def _log_scrape_start(self, source_name: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO scrape_log (source_name, started_at, status)
                VALUES (?, ?, 'running')
            """, (source_name, datetime.now().isoformat()))
            return cursor.lastrowid

    def _log_scrape_complete(self, log_id: int, found: int, new: int, errors: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE scrape_log
                SET completed_at = ?, items_found = ?, items_new = ?, errors = ?, status = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), found, new, errors, status, log_id))

    # ═══════════════════════════════════════════════════════════════════════
    # SEARCH & QUERY
    # ═══════════════════════════════════════════════════════════════════════

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Full-text search across all scraped content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT i.* FROM items i
                JOIN items_fts fts ON i.rowid = fts.rowid
                WHERE items_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_recent(self, source_name: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get recently scraped items"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if source_name:
                rows = conn.execute("""
                    SELECT * FROM items
                    WHERE source_name = ?
                    ORDER BY scraped_at DESC
                    LIMIT ?
                """, (source_name, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM items
                    ORDER BY scraped_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [dict(r) for r in rows]

    def get_code_examples(self, query: str, limit: int = 10) -> List[Dict]:
        """Search specifically for code examples"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, source_name, url, title, extracted_code
                FROM items
                WHERE extracted_code != '[]'
                AND (title LIKE ? OR content LIKE ?)
                ORDER BY scraped_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()

            results = []
            for row in rows:
                codes = json.loads(row['extracted_code'])
                for code in codes:
                    if query.lower() in code.lower():
                        results.append({
                            "source": row['source_name'],
                            "url": row['url'],
                            "title": row['title'],
                            "code": code
                        })

            return results[:limit]

    def get_stats(self) -> Dict:
        """Get arsenal statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

            by_source = conn.execute("""
                SELECT source_name, COUNT(*) as count
                FROM items GROUP BY source_name
            """).fetchall()

            by_type = conn.execute("""
                SELECT content_type, COUNT(*) as count
                FROM items GROUP BY content_type
            """).fetchall()

            recent_scrapes = conn.execute("""
                SELECT source_name, completed_at, items_new, status
                FROM scrape_log
                ORDER BY completed_at DESC
                LIMIT 10
            """).fetchall()

            return {
                "total_items": total_items,
                "by_source": {r[0]: r[1] for r in by_source},
                "by_type": {r[0]: r[1] for r in by_type},
                "recent_scrapes": [
                    {"source": r[0], "at": r[1], "new": r[2], "status": r[3]}
                    for r in recent_scrapes
                ],
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
            }

    # ═══════════════════════════════════════════════════════════════════════
    # BATCH OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def scrape_all(self, sources: Optional[List[str]] = None) -> Dict:
        """Scrape all configured sources"""
        results = {}

        to_scrape = sources or list(self.sources.keys())

        for source_name in to_scrape:
            print(f"Scraping {source_name}...")
            result = self.scrape_source(source_name)
            results[source_name] = result

            # Rate limit between sources
            time.sleep(2)

        return results

    def add_custom_source(self, config: SourceConfig):
        """Add a custom source"""
        self.sources[config.name] = config


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    arsenal = DataArsenal()

    if len(sys.argv) < 2:
        print("SAM Data Arsenal")
        print("\nIntelligence gathering from the web.")
        print("\nUsage:")
        print("  python data_arsenal.py sources              # List sources")
        print("  python data_arsenal.py scrape <source>      # Scrape a source")
        print("  python data_arsenal.py scrape-all           # Scrape everything")
        print("  python data_arsenal.py search <query>       # Search content")
        print("  python data_arsenal.py code <query>         # Search code examples")
        print("  python data_arsenal.py recent [source]      # Recent items")
        print("  python data_arsenal.py stats                # Show statistics")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "sources":
        print("\n📡 Configured Sources\n")
        for name, config in arsenal.sources.items():
            print(f"  • {name}")
            print(f"    Type: {config.source_type.value}")
            print(f"    URL: {config.url}")
            print(f"    Refresh: every {config.refresh_hours}h")
            print()

    elif cmd == "scrape":
        if len(sys.argv) < 3:
            print("Usage: python data_arsenal.py scrape <source>")
            print("Sources:", ", ".join(arsenal.sources.keys()))
            sys.exit(1)

        source = sys.argv[2]
        print(f"\n🔍 Scraping {source}...\n")
        result = arsenal.scrape_source(source)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✓ Found: {result['items_found']} items")
            print(f"✓ New: {result['items_new']} items")

    elif cmd == "scrape-all":
        print("\n🔍 Scraping all sources...\n")
        results = arsenal.scrape_all()

        for source, result in results.items():
            status = "✓" if result.get('status') == 'completed' else "✗"
            new = result.get('items_new', 0)
            print(f"  {status} {source}: {new} new items")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python data_arsenal.py search <query>")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        results = arsenal.search(query)

        print(f"\n🔍 Results for \"{query}\": {len(results)} matches\n")
        for r in results[:10]:
            print(f"  [{r['source_name']}] {r['title'][:50]}")
            print(f"    {r['url']}")
            print()

    elif cmd == "code":
        if len(sys.argv) < 3:
            print("Usage: python data_arsenal.py code <query>")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        results = arsenal.get_code_examples(query)

        print(f"\n💻 Code examples for \"{query}\": {len(results)} found\n")
        for r in results[:5]:
            print(f"  From: {r['source']} - {r['title'][:40]}")
            print("  ```")
            print(f"  {r['code'][:200]}...")
            print("  ```")
            print()

    elif cmd == "recent":
        source = sys.argv[2] if len(sys.argv) > 2 else None
        items = arsenal.get_recent(source)

        title = f"Recent from {source}" if source else "Recent items"
        print(f"\n📋 {title}\n")

        for item in items[:15]:
            print(f"  [{item['source_name']}] {item['title'][:50]}")
            print(f"    {item['scraped_at'][:16]}")
            print()

    elif cmd == "stats":
        stats = arsenal.get_stats()

        print("\n📊 Data Arsenal Statistics\n")
        print(f"Total items: {stats['total_items']}")
        print(f"Database size: {stats['db_size_mb']} MB")

        print("\nBy source:")
        for source, count in stats['by_source'].items():
            print(f"  • {source}: {count}")

        print("\nBy type:")
        for typ, count in stats['by_type'].items():
            print(f"  • {typ}: {count}")

        print("\nRecent scrapes:")
        for scrape in stats['recent_scrapes'][:5]:
            status = "✓" if scrape['status'] == 'completed' else "✗"
            print(f"  {status} {scrape['source']}: {scrape['new']} new ({scrape['at'][:16]})")

    else:
        print(f"Unknown command: {cmd}")
