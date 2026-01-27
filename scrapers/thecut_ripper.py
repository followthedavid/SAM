#!/usr/bin/env python3
"""
The Cut (New York Magazine) Scraper
Target: Culture, style, relationships, essays, profiles
Storage: External drives only
Output: Training data for sophisticated feminine voice, personal essays

Content types:
- Personal essays and first-person narratives
- Relationship advice and stories
- Style and beauty content
- Celebrity profiles and interviews
- Cultural commentary
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
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/thecut_archive",
    "db_path": "/Volumes/David External/thecut_archive/thecut_index.db",
    "rate_limit_seconds": 1.5,
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "pages_per_section": 150,
}

# The Cut sections - focusing on personal/relationship content
SECTIONS = {
    # Core personal content
    "love-sex": "https://www.thecut.com/tags/love-and-dating/",
    "relationships": "https://www.thecut.com/tags/relationships/",
    "sex": "https://www.thecut.com/tags/sex/",
    "self": "https://www.thecut.com/self/",

    # Essays and first-person
    "essays": "https://www.thecut.com/tags/essays/",
    "personal-essays": "https://www.thecut.com/tags/personal-essays/",
    "first-person": "https://www.thecut.com/tags/first-person/",

    # Culture and profiles
    "culture": "https://www.thecut.com/culture/",
    "power": "https://www.thecut.com/power/",
    "style": "https://www.thecut.com/style/",

    # Specific columns that are dialogue/advice heavy
    "ask-polly": "https://www.thecut.com/tags/ask-polly/",
    "sex-diaries": "https://www.thecut.com/tags/sex-diaries/",
    "how-i-get-it-done": "https://www.thecut.com/tags/how-i-get-it-done/",
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Article:
    """The Cut article metadata."""
    id: str
    url: str
    title: str
    subtitle: str
    author: str
    section: str
    column: str  # e.g., "Ask Polly", "Sex Diaries"
    date_published: str
    word_count: int
    is_first_person: bool
    is_advice: bool
    is_diary: bool
    has_dialogue: bool
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
            section TEXT,
            column_name TEXT,
            date_published TEXT,
            word_count INTEGER,
            is_first_person INTEGER,
            is_advice INTEGER,
            is_diary INTEGER,
            has_dialogue INTEGER,
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
            section TEXT PRIMARY KEY,
            last_page INTEGER DEFAULT 0,
            total_found INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_section ON articles(section)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_first_person ON articles(is_first_person)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_advice ON articles(is_advice)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_column ON articles(column_name)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPING
# ============================================================================

class TheCutScraper:
    """Scraper for The Cut."""

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

        logger = logging.getLogger("thecut")
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
            self.logger.error(f"Fetch error: {e}")
            if retries < CONFIG["max_retries"]:
                time.sleep(3)
                return self._fetch(url, retries + 1)
            return None

    def _detect_content_type(self, title: str, subtitle: str, tags: List[str]) -> Dict[str, bool]:
        """Detect content type from metadata."""
        combined = f"{title} {subtitle} {' '.join(tags)}".lower()

        return {
            "is_first_person": any(kw in combined for kw in [
                'i ', 'my ', 'me ', 'first-person', 'personal essay',
                'diary', 'how i', 'what i', 'why i'
            ]),
            "is_advice": any(kw in combined for kw in [
                'advice', 'ask polly', 'how to', 'should i', 'help',
                'tips', 'guide', 'what to do'
            ]),
            "is_diary": any(kw in combined for kw in [
                'diary', 'sex diary', 'diaries', 'day in the life'
            ]),
            "has_dialogue": any(kw in combined for kw in [
                'interview', 'q&a', 'conversation', 'talks', 'says'
            ]),
        }

    def _detect_column(self, url: str, title: str) -> str:
        """Detect which column an article belongs to."""
        url_lower = url.lower()
        title_lower = title.lower()

        if 'ask-polly' in url_lower or 'ask polly' in title_lower:
            return "Ask Polly"
        if 'sex-diaries' in url_lower or 'sex diary' in title_lower:
            return "Sex Diaries"
        if 'how-i-get-it-done' in url_lower:
            return "How I Get It Done"
        if 'beauty-school' in url_lower:
            return "Beauty School"
        if 'fashion-school' in url_lower:
            return "Fashion School"

        return ""

    def _parse_article_card(self, card, section: str) -> Optional[Article]:
        """Parse an article card from section page."""
        try:
            # Find link
            link = card.select_one('a[href*="/article/"], a[href*="/thecut/"]')
            if not link:
                link = card.select_one('a[href]')
            if not link:
                return None

            url = link.get('href', '')
            if not url.startswith('http'):
                url = urljoin("https://www.thecut.com", url)

            # Skip non-article URLs
            if '/video/' in url or '/slideshow/' in url:
                return None

            # Title
            title_elem = card.select_one('h2, h3, h4, .headline, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                title = link.get_text(strip=True)

            if not title or len(title) < 10:
                return None

            # Subtitle/dek
            subtitle_elem = card.select_one('.dek, .teaser, [class*="dek"], [class*="teaser"]')
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

            # Tags from card
            tag_elems = card.select('[class*="tag"] a, .tags a')
            tags = [t.get_text(strip=True) for t in tag_elems]

            # Detect content type
            content_types = self._detect_content_type(title, subtitle, tags)

            # Detect column
            column = self._detect_column(url, title)

            return Article(
                id=hashlib.md5(url.encode()).hexdigest()[:16],
                url=url,
                title=title,
                subtitle=subtitle,
                author=author,
                section=section,
                column=column,
                date_published=date_published,
                word_count=0,
                is_first_person=content_types['is_first_person'],
                is_advice=content_types['is_advice'],
                is_diary=content_types['is_diary'],
                has_dialogue=content_types['has_dialogue'],
                tags=tags,
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
                    id, url, title, subtitle, author, section, column_name,
                    date_published, word_count, is_first_person, is_advice,
                    is_diary, has_dialogue, tags, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id, article.url, article.title, article.subtitle,
                article.author, article.section, article.column,
                article.date_published, article.word_count,
                1 if article.is_first_person else 0,
                1 if article.is_advice else 0,
                1 if article.is_diary else 0,
                1 if article.has_dialogue else 0,
                json.dumps(article.tags), article.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_section(self, section: str, base_url: str):
        """Index articles from a section."""
        # Check progress
        cursor = self.conn.execute(
            "SELECT last_page, completed FROM section_progress WHERE section = ?",
            (section,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"Section '{section}' already completed")
            return

        self.logger.info(f"Indexing: {section} (page {start_page})")

        total_found = 0
        page = start_page

        while page <= CONFIG["pages_per_section"]:
            # Construct page URL
            if page == 1:
                url = base_url
            else:
                # The Cut uses different pagination patterns
                if '/tags/' in base_url:
                    url = f"{base_url}?page={page}"
                else:
                    url = f"{base_url}?p={page}"

            soup = self._fetch(url)
            if not soup:
                break

            # Find article cards - NY Mag/Vox Media patterns
            cards = soup.select('article, [class*="feed-item"], [class*="story"], [class*="article-item"]')

            if not cards:
                # Try river/stream patterns
                cards = soup.select('[class*="river"] > div, [class*="stream"] > div')

            if not cards:
                self.logger.info(f"No more articles at page {page}")
                self.conn.execute("""
                    INSERT OR REPLACE INTO section_progress
                    (section, last_page, total_found, completed, updated_at)
                    VALUES (?, ?, ?, 1, ?)
                """, (section, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            found_this_page = 0
            for card in cards:
                article = self._parse_article_card(card, section)
                if article:
                    self._save_article(article)
                    total_found += 1
                    found_this_page += 1

            # If we found nothing on this page, we might be done
            if found_this_page == 0:
                self.logger.info(f"No articles found at page {page}")
                break

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO section_progress
                (section, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, 0, ?)
            """, (section, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            if total_found % 50 == 0 and total_found > 0:
                self.logger.info(f"  {total_found} articles indexed...")

            page += 1

        self.logger.info(f"Section '{section}': {total_found} articles")

    def download_article(self, url: str) -> Optional[Dict]:
        """Download and parse full article content."""
        soup = self._fetch(url)
        if not soup:
            return None

        try:
            # Find article body - NY Mag patterns
            body = soup.select_one('article .body, .article-body, [class*="article-content"]')
            if not body:
                body = soup.select_one('article')

            if not body:
                return None

            # Extract text
            paragraphs = body.select('p')
            content_parts = []

            for p in paragraphs:
                # Skip ads, related links
                if p.select('[class*="ad"], [class*="related"]'):
                    continue

                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    content_parts.append(text)

            full_content = '\n\n'.join(content_parts)

            # Calculate stats
            word_count = len(full_content.split())

            # Detect dialogue (quotes)
            quotes = re.findall(r'"[^"]{15,}"', full_content)
            has_dialogue = len(quotes) >= 2

            # Re-check content types with full content
            content_lower = full_content.lower()
            is_first_person = full_content.count(' I ') > 5 or content_lower.startswith('i ')
            is_advice = 'dear ' in content_lower or 'should you' in content_lower

            # Get tags
            tag_elems = soup.select('[class*="tag"] a, .tags a, [class*="topics"] a')
            tags = list(set([t.get_text(strip=True) for t in tag_elems]))

            return {
                "content": full_content,
                "word_count": word_count,
                "has_dialogue": has_dialogue,
                "is_first_person": is_first_person,
                "is_advice": is_advice,
                "tags": tags,
            }

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return None

    def download_pending(self, limit: int = 100, priority: str = "all"):
        """Download pending articles."""
        query = """
            SELECT id, url, title, section FROM articles
            WHERE downloaded = 0
        """

        if priority == "first-person":
            query += " AND is_first_person = 1"
        elif priority == "advice":
            query += " AND is_advice = 1"
        elif priority == "diary":
            query += " AND is_diary = 1"

        query += " ORDER BY is_first_person DESC, is_advice DESC, is_diary DESC LIMIT ?"

        cursor = self.conn.execute(query, (limit,))
        articles = cursor.fetchall()

        self.logger.info(f"Downloading {len(articles)} articles (priority: {priority})")

        storage_dir = Path(CONFIG["storage_root"]) / "articles"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for i, row in enumerate(articles, 1):
            self.logger.info(f"[{i}/{len(articles)}] {row['title'][:50]}...")

            result = self.download_article(row['url'])

            if result and result['word_count'] > 300:
                # Save content
                safe_title = re.sub(r'[^\w\s-]', '', row['title'])[:50]
                filename = f"{row['id']}_{safe_title}.txt"
                filepath = storage_dir / filename

                filepath.write_text(result['content'], encoding='utf-8')

                # Update database
                self.conn.execute("""
                    UPDATE articles SET
                        downloaded = 1,
                        content_path = ?,
                        word_count = ?,
                        has_dialogue = ?,
                        is_first_person = ?,
                        is_advice = ?,
                        tags = ?
                    WHERE id = ?
                """, (
                    str(filepath), result['word_count'],
                    1 if result['has_dialogue'] else 0,
                    1 if result['is_first_person'] else 0,
                    1 if result['is_advice'] else 0,
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
        """Index all sections."""
        self.logger.info("=" * 60)
        self.logger.info("The Cut Scraper")
        self.logger.info("=" * 60)

        for section, url in SECTIONS.items():
            try:
                self.index_section(section, url)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                return
            except Exception as e:
                self.logger.error(f"Error with {section}: {e}")

        self._print_stats()

    def _print_stats(self):
        """Print indexing stats."""
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_first_person = 1 THEN 1 ELSE 0 END) as first_person,
                SUM(CASE WHEN is_advice = 1 THEN 1 ELSE 0 END) as advice,
                SUM(CASE WHEN is_diary = 1 THEN 1 ELSE 0 END) as diary,
                SUM(CASE WHEN has_dialogue = 1 THEN 1 ELSE 0 END) as dialogue,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded
            FROM articles
        """)
        stats = cursor.fetchone()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("INDEXING COMPLETE")
        self.logger.info(f"  Total articles:   {stats['total']:,}")
        self.logger.info(f"  First-person:     {stats['first_person']:,}")
        self.logger.info(f"  Advice columns:   {stats['advice']:,}")
        self.logger.info(f"  Diaries:          {stats['diary']:,}")
        self.logger.info(f"  With dialogue:    {stats['dialogue']:,}")
        self.logger.info(f"  Downloaded:       {stats['downloaded']:,}")
        self.logger.info("=" * 60)

        # Column breakdown
        self.logger.info("\n📊 By Column:")
        cursor = self.conn.execute("""
            SELECT column_name, COUNT(*) as count
            FROM articles
            WHERE column_name != ''
            GROUP BY column_name
            ORDER BY count DESC
        """)
        for row in cursor:
            self.logger.info(f"  {row['column_name']:25} {row['count']:,}")

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="The Cut Scraper")
    parser.add_argument('command', choices=['index', 'download', 'stats'])
    parser.add_argument('--section')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--priority', choices=['all', 'first-person', 'advice', 'diary'],
                        default='all')

    args = parser.parse_args()

    scraper = TheCutScraper()

    if args.command == 'index':
        if args.section and args.section in SECTIONS:
            scraper.index_section(args.section, SECTIONS[args.section])
        else:
            scraper.run_full_index()

    elif args.command == 'download':
        scraper.download_pending(args.limit, args.priority)

    elif args.command == 'stats':
        scraper._print_stats()

if __name__ == "__main__":
    main()
