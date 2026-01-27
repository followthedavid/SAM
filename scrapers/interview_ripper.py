#!/usr/bin/env python3
"""
Interview Magazine Site Ripper
Target: Celebrity interviews, cultural commentary, witty dialogue
Bypass: Standard fetch (no paywall)
Storage: External drives only
Output: Organized by category with full metadata

This source is HIGH VALUE for SAM personality training:
- Interview format provides natural dialogue patterns
- Celebrity conversations show confident, witty interaction style
- Cultural content adds depth and contemporary knowledge
"""

import os
import re
import json
import time
import hashlib
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.interviewmagazine.com",
    "sitemap_index": "https://www.interviewmagazine.com/sitemap_index.xml",
    "storage_root": "/Volumes/David External/interview_archive",
    "db_path": "/Volumes/David External/interview_archive/interview_index.db",
    "rate_limit_seconds": 1.5,
    "max_retries": 3,
    "retry_delay": 5.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "min_word_count": 200,
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ArticleMetadata:
    """Article metadata from sitemap and page."""
    id: str
    url: str
    title: str
    category: str
    subcategory: str
    interviewee: Optional[str]
    interviewer: Optional[str]
    publish_date: Optional[str]
    modified_date: Optional[str]
    image_url: Optional[str]
    word_count: int
    is_interview: bool
    downloaded: bool
    download_date: Optional[str]
    file_path: Optional[str]

# ============================================================================
# DATABASE
# ============================================================================

class InterviewDatabase:
    """SQLite database for tracking scrape progress."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    category TEXT,
                    subcategory TEXT,
                    interviewee TEXT,
                    interviewer TEXT,
                    publish_date TEXT,
                    modified_date TEXT,
                    image_url TEXT,
                    word_count INTEGER DEFAULT 0,
                    is_interview BOOLEAN DEFAULT 0,
                    downloaded BOOLEAN DEFAULT 0,
                    download_date TEXT,
                    file_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sitemaps (
                    url TEXT PRIMARY KEY,
                    article_count INTEGER DEFAULT 0,
                    processed BOOLEAN DEFAULT 0,
                    last_processed TEXT
                );

                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_articles_downloaded ON articles(downloaded);
                CREATE INDEX IF NOT EXISTS idx_articles_interview ON articles(is_interview);
            """)

    def add_article(self, article: ArticleMetadata) -> bool:
        """Add or update an article in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO articles
                    (id, url, title, category, subcategory, interviewee, interviewer,
                     publish_date, modified_date, image_url, word_count, is_interview,
                     downloaded, download_date, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article.id, article.url, article.title, article.category,
                    article.subcategory, article.interviewee, article.interviewer,
                    article.publish_date, article.modified_date, article.image_url,
                    article.word_count, article.is_interview, article.downloaded,
                    article.download_date, article.file_path
                ))
            return True
        except Exception as e:
            logging.error(f"Failed to add article {article.url}: {e}")
            return False

    def get_pending_articles(self, limit: int = 100) -> List[Dict]:
        """Get articles that haven't been downloaded yet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM articles
                WHERE downloaded = 0
                ORDER BY is_interview DESC, publish_date DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_downloaded(self, article_id: str, file_path: str):
        """Mark an article as downloaded."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE articles
                SET downloaded = 1, download_date = ?, file_path = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), file_path, article_id))

    def get_stats(self) -> Dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            stats['total'] = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            stats['downloaded'] = conn.execute("SELECT COUNT(*) FROM articles WHERE downloaded = 1").fetchone()[0]
            stats['pending'] = conn.execute("SELECT COUNT(*) FROM articles WHERE downloaded = 0").fetchone()[0]
            stats['interviews'] = conn.execute("SELECT COUNT(*) FROM articles WHERE is_interview = 1").fetchone()[0]
            return stats

# ============================================================================
# SCRAPER
# ============================================================================

class InterviewScraper:
    """Scraper for Interview Magazine."""

    def __init__(self, config: Dict = None):
        self.config = config or CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.db = InterviewDatabase(self.config["db_path"])

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )

    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch a URL with retry logic."""
        for attempt in range(self.config["max_retries"]):
            try:
                time.sleep(self.config["rate_limit_seconds"])
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config["max_retries"] - 1:
                    time.sleep(self.config["retry_delay"])
        return None

    def discover_sitemaps(self) -> List[str]:
        """Discover all article sitemaps from the sitemap index."""
        logging.info("Discovering sitemaps...")
        sitemaps = []

        content = self.fetch_url(self.config["sitemap_index"])
        if not content:
            # Try alternate sitemap locations
            alternates = [
                f"{self.config['base_url']}/sitemap.xml",
                f"{self.config['base_url']}/post-sitemap.xml",
                f"{self.config['base_url']}/sitemap-posts.xml",
            ]
            for alt in alternates:
                content = self.fetch_url(alt)
                if content:
                    break

        if not content:
            logging.error("Could not fetch any sitemap")
            return sitemaps

        try:
            # Try parsing as sitemap index
            root = ET.fromstring(content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check if it's a sitemap index
            for sitemap in root.findall('.//sm:sitemap', ns):
                loc = sitemap.find('sm:loc', ns)
                if loc is not None and 'post' in loc.text.lower():
                    sitemaps.append(loc.text)

            # If no sitemaps found, treat as direct sitemap
            if not sitemaps:
                for url in root.findall('.//sm:url/sm:loc', ns):
                    if url.text:
                        sitemaps.append(url.text)

        except ET.ParseError:
            # Try parsing as HTML (some sites use HTML sitemaps)
            soup = BeautifulSoup(content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'sitemap' in href.lower() and 'post' in href.lower():
                    sitemaps.append(urljoin(self.config['base_url'], href))

        logging.info(f"Found {len(sitemaps)} sitemaps")
        return sitemaps

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse a sitemap and extract article URLs."""
        urls = []
        content = self.fetch_url(sitemap_url)
        if not content:
            return urls

        try:
            root = ET.fromstring(content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for url in root.findall('.//sm:url', ns):
                loc = url.find('sm:loc', ns)
                if loc is not None and loc.text:
                    # Filter for article URLs
                    article_url = loc.text
                    if self._is_article_url(article_url):
                        urls.append(article_url)

        except ET.ParseError as e:
            logging.error(f"Failed to parse sitemap {sitemap_url}: {e}")

        return urls

    def _is_article_url(self, url: str) -> bool:
        """Check if a URL is likely an article."""
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/page/',
            '/wp-content/', '/wp-includes/', '/feed/',
            '.jpg', '.png', '.gif', '.pdf', '.css', '.js'
        ]
        return not any(p in url.lower() for p in skip_patterns)

    def parse_article(self, url: str) -> Optional[ArticleMetadata]:
        """Parse an article page and extract metadata and content."""
        content = self.fetch_url(url)
        if not content:
            return None

        soup = BeautifulSoup(content, 'html.parser')

        # Generate ID from URL
        article_id = hashlib.md5(url.encode()).hexdigest()[:16]

        # Extract title
        title = None
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Extract category from URL or meta
        category = "general"
        subcategory = ""
        parsed_url = urlparse(url)
        path_parts = [p for p in parsed_url.path.split('/') if p]
        if path_parts:
            category = path_parts[0]
            if len(path_parts) > 1 and path_parts[1] not in ['page']:
                subcategory = path_parts[1]

        # Try to identify interviewee and interviewer
        interviewee = None
        interviewer = None

        # Look for interview patterns in content
        article_body = soup.find('article') or soup.find(class_=re.compile(r'article|content|post'))
        article_text = article_body.get_text() if article_body else ""

        # Common patterns: "Interview by X", "X talks with Y", "X in conversation with Y"
        is_interview = bool(re.search(r'\b(interview|talks?\s+with|in\s+conversation|speaks?\s+to)\b', article_text, re.I))

        # Try to extract from title
        if title:
            # Pattern: "Name: Subtitle" or "Name on Topic"
            title_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', title)
            if title_match and is_interview:
                interviewee = title_match.group(1)

        # Extract dates
        publish_date = None
        modified_date = None

        # Try meta tags
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '') or meta.get('name', '')
            if 'published' in prop.lower() or prop == 'article:published_time':
                publish_date = meta.get('content')
            elif 'modified' in prop.lower() or prop == 'article:modified_time':
                modified_date = meta.get('content')

        # Extract featured image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content')

        # Calculate word count
        word_count = len(article_text.split()) if article_text else 0

        return ArticleMetadata(
            id=article_id,
            url=url,
            title=title,
            category=category,
            subcategory=subcategory,
            interviewee=interviewee,
            interviewer=interviewer,
            publish_date=publish_date,
            modified_date=modified_date,
            image_url=image_url,
            word_count=word_count,
            is_interview=is_interview,
            downloaded=False,
            download_date=None,
            file_path=None
        )

    def download_article(self, article: Dict) -> Optional[str]:
        """Download and save article content."""
        content = self.fetch_url(article['url'])
        if not content:
            return None

        soup = BeautifulSoup(content, 'html.parser')

        # Find article body
        article_body = soup.find('article') or soup.find(class_=re.compile(r'article|content|post|entry'))
        if not article_body:
            logging.warning(f"No article body found for {article['url']}")
            return None

        # Clean up the content
        for tag in article_body.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
            tag.decompose()

        # Extract clean text
        text = article_body.get_text(separator='\n', strip=True)

        # Skip if too short
        if len(text.split()) < self.config["min_word_count"]:
            logging.info(f"Article too short: {article['url']}")
            return None

        # Determine output path
        category = article.get('category', 'general')
        safe_id = article['id']
        output_dir = Path(self.config["storage_root"]) / "articles" / category
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{safe_id}.json"

        # Save as JSON with metadata
        output_data = {
            "url": article['url'],
            "title": article.get('title'),
            "category": category,
            "subcategory": article.get('subcategory'),
            "interviewee": article.get('interviewee'),
            "interviewer": article.get('interviewer'),
            "publish_date": article.get('publish_date'),
            "is_interview": article.get('is_interview', False),
            "word_count": len(text.split()),
            "text": text
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def index(self, limit: int = None):
        """Index all articles from sitemaps."""
        logging.info("Starting indexing...")

        # Discover sitemaps
        sitemaps = self.discover_sitemaps()
        if not sitemaps:
            # Try direct article discovery
            logging.info("No sitemaps found, trying direct discovery...")
            self._discover_from_homepage()
            return

        total_indexed = 0
        for sitemap_url in sitemaps:
            logging.info(f"Processing sitemap: {sitemap_url}")
            urls = self.parse_sitemap(sitemap_url)
            logging.info(f"  Found {len(urls)} URLs")

            for url in urls:
                if limit and total_indexed >= limit:
                    logging.info(f"Reached limit of {limit}")
                    return

                article = self.parse_article(url)
                if article:
                    self.db.add_article(article)
                    total_indexed += 1

                    if total_indexed % 100 == 0:
                        logging.info(f"Indexed {total_indexed} articles...")

        logging.info(f"Indexing complete. Total: {total_indexed}")

    def _discover_from_homepage(self):
        """Discover articles from the homepage and category pages."""
        content = self.fetch_url(self.config["base_url"])
        if not content:
            return

        soup = BeautifulSoup(content, 'html.parser')

        # Find article links
        article_urls = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(self.config['base_url'], href)
            if self._is_article_url(full_url) and self.config['base_url'] in full_url:
                article_urls.add(full_url)

        logging.info(f"Found {len(article_urls)} articles from homepage")

        for url in article_urls:
            article = self.parse_article(url)
            if article:
                self.db.add_article(article)

    def download(self, limit: int = 1000):
        """Download pending articles."""
        logging.info(f"Starting download (limit: {limit})...")

        pending = self.db.get_pending_articles(limit)
        logging.info(f"Found {len(pending)} pending articles")

        downloaded = 0
        for article in pending:
            file_path = self.download_article(article)
            if file_path:
                self.db.mark_downloaded(article['id'], file_path)
                downloaded += 1

                if downloaded % 50 == 0:
                    logging.info(f"Downloaded {downloaded}/{len(pending)}")

        logging.info(f"Download complete. Downloaded: {downloaded}")

    def stats(self):
        """Print database statistics."""
        stats = self.db.get_stats()
        print("\n" + "=" * 50)
        print("  INTERVIEW MAGAZINE ARCHIVE STATISTICS")
        print("=" * 50)
        print(f"\nTotal articles indexed: {stats['total']:,}")
        print(f"Downloaded: {stats['downloaded']:,}")
        print(f"Pending: {stats['pending']:,}")
        print(f"Interviews: {stats['interviews']:,}")
        print()

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Interview Magazine Scraper")
    parser.add_argument('action', choices=['index', 'download', 'stats'],
                        help='Action to perform')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of items to process')
    args = parser.parse_args()

    scraper = InterviewScraper()

    if args.action == 'index':
        scraper.index(limit=args.limit)
    elif args.action == 'download':
        scraper.download(limit=args.limit or 1000)
    elif args.action == 'stats':
        scraper.stats()

if __name__ == "__main__":
    main()
