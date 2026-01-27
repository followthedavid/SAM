#!/usr/bin/env python3
"""
GQ & Esquire Magazine Scraper
Target: Style, culture, celebrity interviews, longform profiles
Storage: External drives only
Output: Training data for sophisticated male voice, interview style

Content types:
- Celebrity interviews and profiles
- Style and fashion content
- Culture and lifestyle articles
- Opinion and essays
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
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/gq_esquire_archive",
    "db_path": "/Volumes/David External/gq_esquire_archive/gq_esquire_index.db",
    "rate_limit_seconds": 1.5,
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "pages_per_section": 100,
}

# GQ sections to scrape
GQ_SECTIONS = {
    "style": "https://www.gq.com/style",
    "culture": "https://www.gq.com/culture",
    "grooming": "https://www.gq.com/grooming",
    "lifestyle": "https://www.gq.com/lifestyle",
    "story": "https://www.gq.com/story",  # Longform
}

# Esquire sections to scrape
ESQUIRE_SECTIONS = {
    "style": "https://www.esquire.com/style",
    "entertainment": "https://www.esquire.com/entertainment",
    "lifestyle": "https://www.esquire.com/lifestyle",
    "news-politics": "https://www.esquire.com/news-politics",
    "food-drink": "https://www.esquire.com/food-drink",
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Article:
    """Magazine article metadata."""
    id: str
    url: str
    title: str
    subtitle: str
    author: str
    publication: str  # gq or esquire
    section: str
    date_published: str
    word_count: int
    has_interview: bool
    has_quotes: bool
    tags: List[str]
    indexed_at: str
    downloaded: bool = False
    processed: bool = False

# ============================================================================
# DATABASE
# ============================================================================

def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            subtitle TEXT,
            author TEXT,
            publication TEXT,
            section TEXT,
            date_published TEXT,
            word_count INTEGER,
            has_interview INTEGER,
            has_quotes INTEGER,
            tags TEXT,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0,
            content_path TEXT,
            error TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS section_progress (
            key TEXT PRIMARY KEY,
            publication TEXT,
            section TEXT,
            last_page INTEGER DEFAULT 0,
            total_found INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_publication ON articles(publication)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_section ON articles(section)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_interview ON articles(has_interview)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPING
# ============================================================================

class GQEsquireScraper:
    """Scraper for GQ and Esquire magazines."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("gq_esquire")
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_dir / "scraper.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console)

        return logger

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < CONFIG["rate_limit_seconds"]:
            time.sleep(CONFIG["rate_limit_seconds"] - elapsed)
        self.last_request = time.time()

    def _fetch(self, url: str, retries: int = 0) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        self._rate_limit()

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.logger.error(f"Fetch error for {url}: {e}")
            if retries < CONFIG["max_retries"]:
                time.sleep(3)
                return self._fetch(url, retries + 1)
            return None

    def _is_interview_content(self, text: str) -> bool:
        """Check if content appears to be an interview."""
        if not text:
            return False

        text_lower = text.lower()

        # Interview markers
        interview_keywords = [
            'interview', 'q&a', 'q & a', 'talks to', 'speaks to',
            'sits down with', 'conversation with', 'chat with',
            'we asked', 'we talked', 'told us', 'says to us'
        ]

        return any(kw in text_lower for kw in interview_keywords)

    def _has_substantial_quotes(self, text: str) -> bool:
        """Check if content has substantial dialogue/quotes."""
        if not text:
            return False

        # Count quoted text
        quotes = re.findall(r'"[^"]{20,}"', text)  # Quotes with 20+ chars
        return len(quotes) >= 3

    def _parse_gq_article_card(self, card, section: str) -> Optional[Article]:
        """Parse a GQ article card."""
        try:
            # Find link
            link = card.select_one('a[href*="/story/"], a[href*="/gq/"]')
            if not link:
                link = card.select_one('a[href]')
            if not link:
                return None

            url = link.get('href', '')
            if not url.startswith('http'):
                url = urljoin("https://www.gq.com", url)

            # Skip non-article URLs
            if '/video/' in url or '/gallery/' in url:
                return None

            # Title
            title_elem = card.select_one('h2, h3, .headline, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                title = link.get_text(strip=True)

            # Subtitle/dek
            subtitle_elem = card.select_one('.dek, .subtitle, [class*="dek"]')
            subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""

            # Author
            author_elem = card.select_one('.byline, [class*="author"], [class*="byline"]')
            author = author_elem.get_text(strip=True) if author_elem else ""
            author = re.sub(r'^by\s+', '', author, flags=re.I)

            # Date
            date_elem = card.select_one('time, [class*="date"]')
            date_published = ""
            if date_elem:
                date_published = date_elem.get('datetime', '') or date_elem.get_text(strip=True)

            # Check for interview indicators in title/subtitle
            combined_text = f"{title} {subtitle}"
            has_interview = self._is_interview_content(combined_text)

            return Article(
                id=hashlib.md5(url.encode()).hexdigest()[:16],
                url=url,
                title=title,
                subtitle=subtitle,
                author=author,
                publication="gq",
                section=section,
                date_published=date_published,
                word_count=0,
                has_interview=has_interview,
                has_quotes=False,
                tags=[],
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _parse_esquire_article_card(self, card, section: str) -> Optional[Article]:
        """Parse an Esquire article card."""
        try:
            # Find link
            link = card.select_one('a[href*="/a/"], a[href*="/esquire/"]')
            if not link:
                link = card.select_one('a[href]')
            if not link:
                return None

            url = link.get('href', '')
            if not url.startswith('http'):
                url = urljoin("https://www.esquire.com", url)

            # Skip non-article URLs
            if '/video/' in url or '/gallery/' in url:
                return None

            # Title
            title_elem = card.select_one('h2, h3, .headline, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                title = link.get_text(strip=True)

            # Subtitle
            subtitle_elem = card.select_one('.dek, .subtitle, [class*="dek"]')
            subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""

            # Author
            author_elem = card.select_one('.byline, [class*="author"]')
            author = author_elem.get_text(strip=True) if author_elem else ""
            author = re.sub(r'^by\s+', '', author, flags=re.I)

            # Date
            date_elem = card.select_one('time, [class*="date"]')
            date_published = ""
            if date_elem:
                date_published = date_elem.get('datetime', '') or date_elem.get_text(strip=True)

            combined_text = f"{title} {subtitle}"
            has_interview = self._is_interview_content(combined_text)

            return Article(
                id=hashlib.md5(url.encode()).hexdigest()[:16],
                url=url,
                title=title,
                subtitle=subtitle,
                author=author,
                publication="esquire",
                section=section,
                date_published=date_published,
                word_count=0,
                has_interview=has_interview,
                has_quotes=False,
                tags=[],
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_article(self, article: Article):
        """Save article to database."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO articles (
                    id, url, title, subtitle, author, publication, section,
                    date_published, word_count, has_interview, has_quotes,
                    tags, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id, article.url, article.title, article.subtitle,
                article.author, article.publication, article.section,
                article.date_published, article.word_count,
                1 if article.has_interview else 0,
                1 if article.has_quotes else 0,
                json.dumps(article.tags), article.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_section(self, publication: str, section: str, base_url: str):
        """Index articles from a section."""
        key = f"{publication}_{section}"

        # Check progress
        cursor = self.conn.execute(
            "SELECT last_page, completed FROM section_progress WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"{publication}/{section} already completed")
            return

        self.logger.info(f"Indexing {publication}/{section} (page {start_page})")

        total_found = 0
        page = start_page

        while page <= CONFIG["pages_per_section"]:
            # Construct page URL
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page}"

            soup = self._fetch(url)
            if not soup:
                break

            # Find article cards - Conde Nast sites use various patterns
            cards = soup.select('article, [class*="summary-item"], [class*="card"], [class*="river-item"]')

            if not cards:
                # Try finding any story links
                cards = soup.select('a[href*="/story/"], a[href*="/a/"]')

            if not cards:
                self.logger.info(f"No more articles at page {page}")
                self.conn.execute("""
                    INSERT OR REPLACE INTO section_progress
                    (key, publication, section, last_page, total_found, completed, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (key, publication, section, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            for card in cards:
                if publication == "gq":
                    article = self._parse_gq_article_card(card, section)
                else:
                    article = self._parse_esquire_article_card(card, section)

                if article:
                    self._save_article(article)
                    total_found += 1

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO section_progress
                (key, publication, section, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (key, publication, section, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            if total_found % 50 == 0 and total_found > 0:
                self.logger.info(f"  {total_found} articles indexed...")

            page += 1

        self.logger.info(f"{publication}/{section}: {total_found} articles")

    def download_article(self, url: str) -> Optional[Dict]:
        """Download and parse full article content."""
        soup = self._fetch(url)
        if not soup:
            return None

        try:
            # Find article body - Conde Nast pattern
            body = soup.select_one('article .body, .article-body, [class*="article-body"]')
            if not body:
                body = soup.select_one('article')

            if not body:
                return None

            # Extract text
            paragraphs = body.select('p')
            content_parts = []

            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Skip short fragments
                    content_parts.append(text)

            full_content = '\n\n'.join(content_parts)

            # Calculate stats
            word_count = len(full_content.split())
            has_quotes = self._has_substantial_quotes(full_content)
            has_interview = self._is_interview_content(full_content)

            # Get tags
            tag_elems = soup.select('[class*="tag"] a, .tags a')
            tags = [t.get_text(strip=True) for t in tag_elems]

            return {
                "content": full_content,
                "word_count": word_count,
                "has_quotes": has_quotes,
                "has_interview": has_interview,
                "tags": tags,
            }

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return None

    def download_pending(self, limit: int = 100, interviews_only: bool = False):
        """Download pending articles."""
        query = """
            SELECT id, url, title, publication FROM articles
            WHERE downloaded = 0
        """
        if interviews_only:
            query += " AND has_interview = 1"
        query += " ORDER BY has_interview DESC LIMIT ?"

        cursor = self.conn.execute(query, (limit,))
        articles = cursor.fetchall()

        self.logger.info(f"Downloading {len(articles)} articles")

        storage_dir = Path(CONFIG["storage_root"]) / "articles"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for i, row in enumerate(articles, 1):
            self.logger.info(f"[{i}/{len(articles)}] {row['title'][:50]}...")

            result = self.download_article(row['url'])

            if result and result['word_count'] > 200:
                # Save content
                safe_title = re.sub(r'[^\w\s-]', '', row['title'])[:50]
                filename = f"{row['publication']}_{row['id']}_{safe_title}.txt"
                filepath = storage_dir / filename

                filepath.write_text(result['content'], encoding='utf-8')

                # Update database
                self.conn.execute("""
                    UPDATE articles SET
                        downloaded = 1,
                        content_path = ?,
                        word_count = ?,
                        has_quotes = ?,
                        has_interview = ?,
                        tags = ?
                    WHERE id = ?
                """, (
                    str(filepath), result['word_count'],
                    1 if result['has_quotes'] else 0,
                    1 if result['has_interview'] else 0,
                    json.dumps(result['tags']),
                    row['id']
                ))
                self.conn.commit()
            else:
                self.conn.execute(
                    "UPDATE articles SET error = 'Download failed or too short' WHERE id = ?",
                    (row['id'],)
                )
                self.conn.commit()

    def run_full_index(self):
        """Index all sections from both publications."""
        self.logger.info("=" * 60)
        self.logger.info("GQ & Esquire Scraper")
        self.logger.info("=" * 60)

        # Index GQ
        self.logger.info("\n📰 Indexing GQ...")
        for section, url in GQ_SECTIONS.items():
            try:
                self.index_section("gq", section, url)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                return
            except Exception as e:
                self.logger.error(f"Error with GQ/{section}: {e}")

        # Index Esquire
        self.logger.info("\n📰 Indexing Esquire...")
        for section, url in ESQUIRE_SECTIONS.items():
            try:
                self.index_section("esquire", section, url)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                return
            except Exception as e:
                self.logger.error(f"Error with Esquire/{section}: {e}")

        # Stats
        self._print_stats()

    def _print_stats(self):
        """Print indexing stats."""
        cursor = self.conn.execute("""
            SELECT
                publication,
                COUNT(*) as total,
                SUM(CASE WHEN has_interview = 1 THEN 1 ELSE 0 END) as interviews,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded
            FROM articles
            GROUP BY publication
        """)

        self.logger.info("\n" + "=" * 60)
        self.logger.info("INDEXING COMPLETE")

        for row in cursor:
            self.logger.info(f"\n{row['publication'].upper()}:")
            self.logger.info(f"  Total articles:  {row['total']:,}")
            self.logger.info(f"  Interviews:      {row['interviews']:,}")
            self.logger.info(f"  Downloaded:      {row['downloaded']:,}")

        self.logger.info("=" * 60)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="GQ & Esquire Scraper")
    parser.add_argument('command', choices=['index', 'download', 'stats'])
    parser.add_argument('--publication', choices=['gq', 'esquire'])
    parser.add_argument('--section')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--interviews-only', action='store_true')

    args = parser.parse_args()

    scraper = GQEsquireScraper()

    if args.command == 'index':
        if args.publication and args.section:
            sections = GQ_SECTIONS if args.publication == 'gq' else ESQUIRE_SECTIONS
            if args.section in sections:
                scraper.index_section(args.publication, args.section, sections[args.section])
        else:
            scraper.run_full_index()

    elif args.command == 'download':
        scraper.download_pending(args.limit, args.interviews_only)

    elif args.command == 'stats':
        scraper._print_stats()

if __name__ == "__main__":
    main()
