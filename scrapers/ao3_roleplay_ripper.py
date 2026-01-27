#!/usr/bin/env python3
"""
AO3 Roleplay-Format Story Ripper
Target: Reader-insert, second-person POV, interactive fiction
Storage: External drives only
Output: Training data optimized for roleplay interaction

Key tags to target:
- Reader (x Reader fics)
- Reader-Insert
- Second Person
- You (POV)
- Interactive Fiction
- Choose Your Own Adventure
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
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://archiveofourown.org",
    "storage_root": "/Volumes/David External/ao3_roleplay",
    "db_path": "/Volumes/David External/ao3_roleplay/ao3_roleplay_index.db",
    "rate_limit_seconds": 3.0,  # AO3 is stricter - be respectful
    "max_retries": 3,
    "retry_delay": 10.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "max_workers": 1,  # Single-threaded to respect AO3
    "checkpoint_interval": 50,
    "pages_per_search": 200,  # Max pages to crawl per search
}

# Search filters for roleplay-style content
SEARCH_FILTERS = {
    "work_search[rating_ids][]": "13",    # Explicit rating
    "work_search[complete]": "T",          # Complete works only
    "work_search[language_id]": "en",      # English
    "work_search[sort_column]": "kudos_count",  # Sort by popularity
    "work_search[sort_direction]": "desc",
}

# Roleplay-specific tag searches - these are the gold mine
ROLEPLAY_TAGS = [
    # Core reader-insert tags
    "Reader-Insert",
    "Reader",
    "x Reader",
    "Second Person",
    "POV Second Person",
    "You",

    # Interactive formats
    "Interactive Fiction",
    "Choose Your Own Adventure",
    "CYOA",
    "Text Messages",
    "Texting",
    "Chat Format",

    # Character x Reader by fandom (high quality)
    "Loki (Marvel)/Reader",
    "Bucky Barnes/Reader",
    "Steve Rogers/Reader",
    "Tony Stark/Reader",
    "Geralt z Rivii | Geralt of Rivia/Reader",
    "Din Djarin/Reader",
    "Kylo Ren/Reader",
    "Draco Malfoy/Reader",
    "Severus Snape/Reader",
    "Lucifer Morningstar/Reader",
    "Dean Winchester/Reader",
    "Sam Winchester/Reader",
    "Crowley (Good Omens)/Reader",
    "Aziraphale (Good Omens)/Reader",

    # Scenario types that produce good roleplay
    "Flirting",
    "Seduction",
    "Power Play",
    "Teasing",
    "Dirty Talk",
    "Praise Kink",
    "Dom/sub",
    "Light Dom/sub",
]

# Category filters - can include any pairing type for reader-insert
CATEGORY_IDS = {
    "gen": "21",
    "ff": "22",
    "fm": "116742",  # F/M
    "mm": "23",
    "multi": "2246",
    "other": "24",
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AO3RoleplayWork:
    """Metadata for an AO3 roleplay-style work."""
    id: str
    ao3_id: int
    url: str
    title: str
    author: str
    rating: str
    category: str
    fandoms: List[str]
    relationships: List[str]
    characters: List[str]
    tags: List[str]
    warnings: List[str]
    word_count: int
    chapter_count: int
    kudos: int
    hits: int
    bookmarks: int
    comments: int
    date_published: str
    date_updated: str
    summary: str
    is_reader_insert: bool
    is_second_person: bool
    has_dialogue: bool
    indexed_at: str
    downloaded: bool = False
    processed: bool = False

# ============================================================================
# DATABASE
# ============================================================================

def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database for tracking."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS works (
            id TEXT PRIMARY KEY,
            ao3_id INTEGER UNIQUE,
            url TEXT,
            title TEXT,
            author TEXT,
            rating TEXT,
            category TEXT,
            fandoms TEXT,
            relationships TEXT,
            characters TEXT,
            tags TEXT,
            warnings TEXT,
            word_count INTEGER,
            chapter_count INTEGER,
            kudos INTEGER,
            hits INTEGER,
            bookmarks INTEGER,
            comments INTEGER,
            date_published TEXT,
            date_updated TEXT,
            summary TEXT,
            is_reader_insert INTEGER,
            is_second_person INTEGER,
            has_dialogue INTEGER,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0,
            content_path TEXT,
            error TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_progress (
            tag TEXT PRIMARY KEY,
            last_page INTEGER DEFAULT 0,
            total_found INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_ao3_id ON works(ao3_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded ON works(downloaded)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kudos ON works(kudos)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reader_insert ON works(is_reader_insert)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPING
# ============================================================================

class AO3RoleplayScraper:
    """Scraper for AO3 roleplay-format content."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("ao3_roleplay")
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
        """Fetch and parse a page with retry logic."""
        self._rate_limit()

        try:
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 429:
                # Rate limited - back off significantly
                self.logger.warning("Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                return self._fetch(url, retries)

            if resp.status_code == 503:
                # AO3 maintenance or overload
                self.logger.warning("AO3 unavailable (503). Waiting 120 seconds...")
                time.sleep(120)
                if retries < CONFIG["max_retries"]:
                    return self._fetch(url, retries + 1)
                return None

            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')

        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            if retries < CONFIG["max_retries"]:
                time.sleep(CONFIG["retry_delay"])
                return self._fetch(url, retries + 1)
            return None

    def _is_roleplay_content(self, tags: List[str], summary: str) -> Tuple[bool, bool]:
        """Check if work is roleplay-style content."""
        tags_lower = [t.lower() for t in tags]
        summary_lower = summary.lower() if summary else ""

        # Check for reader-insert
        reader_keywords = ['reader', 'reader-insert', 'x reader', '/reader']
        is_reader = any(kw in t for t in tags_lower for kw in reader_keywords)
        is_reader = is_reader or 'reader' in summary_lower

        # Check for second person
        second_person_keywords = ['second person', 'pov second', '2nd person']
        is_second = any(kw in t for t in tags_lower for kw in second_person_keywords)
        is_second = is_second or any(kw in summary_lower for kw in second_person_keywords)

        return is_reader, is_second

    def _parse_work_listing(self, work_elem) -> Optional[AO3RoleplayWork]:
        """Parse a work from search results."""
        try:
            # Get work ID
            work_id_elem = work_elem.get('id', '')
            ao3_id = int(work_id_elem.replace('work_', '')) if work_id_elem else None
            if not ao3_id:
                return None

            # Title and URL
            title_elem = work_elem.select_one('h4.heading a')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            url = f"{CONFIG['base_url']}{title_elem['href']}" if title_elem else ""

            # Author
            author_elem = work_elem.select_one('a[rel="author"]')
            author = author_elem.get_text(strip=True) if author_elem else "Anonymous"

            # Rating
            rating_elem = work_elem.select_one('span.rating')
            rating = rating_elem.get_text(strip=True) if rating_elem else "Unknown"

            # Category
            cat_elem = work_elem.select_one('span.category')
            category = cat_elem.get_text(strip=True) if cat_elem else ""

            # Fandoms
            fandom_elems = work_elem.select('h5.fandoms a.tag')
            fandoms = [f.get_text(strip=True) for f in fandom_elems]

            # Relationships
            rel_elems = work_elem.select('li.relationships a.tag')
            relationships = [r.get_text(strip=True) for r in rel_elems]

            # Characters
            char_elems = work_elem.select('li.characters a.tag')
            characters = [c.get_text(strip=True) for c in char_elems]

            # Freeform tags
            tag_elems = work_elem.select('li.freeforms a.tag')
            tags = [t.get_text(strip=True) for t in tag_elems]

            # Warnings
            warn_elems = work_elem.select('li.warnings a.tag')
            warnings = [w.get_text(strip=True) for w in warn_elems]

            # Stats
            stats = work_elem.select_one('dl.stats')
            word_count = 0
            chapter_count = 1
            kudos = 0
            hits = 0
            bookmarks = 0
            comments = 0

            if stats:
                wc = stats.select_one('dd.words')
                word_count = int(wc.get_text().replace(',', '')) if wc else 0

                ch = stats.select_one('dd.chapters')
                if ch:
                    ch_text = ch.get_text()
                    if '/' in ch_text:
                        chapter_count = int(ch_text.split('/')[0])
                    else:
                        chapter_count = int(ch_text) if ch_text.isdigit() else 1

                kd = stats.select_one('dd.kudos')
                kudos = int(kd.get_text().replace(',', '')) if kd else 0

                ht = stats.select_one('dd.hits')
                hits = int(ht.get_text().replace(',', '')) if ht else 0

                bk = stats.select_one('dd.bookmarks')
                bookmarks = int(bk.get_text().replace(',', '')) if bk else 0

                cm = stats.select_one('dd.comments')
                comments = int(cm.get_text().replace(',', '')) if cm else 0

            # Dates
            date_elem = work_elem.select_one('p.datetime')
            date_published = date_elem.get_text(strip=True) if date_elem else ""

            # Summary
            summary_elem = work_elem.select_one('blockquote.summary')
            summary = summary_elem.get_text(strip=True) if summary_elem else ""

            # Check roleplay indicators
            all_tags = tags + relationships + fandoms
            is_reader, is_second = self._is_roleplay_content(all_tags, summary)

            # Check for dialogue-heavy content
            has_dialogue = any(kw in t.lower() for t in tags for kw in [
                'dialogue', 'texting', 'text messages', 'chat', 'conversation'
            ])

            return AO3RoleplayWork(
                id=hashlib.md5(f"ao3_{ao3_id}".encode()).hexdigest()[:16],
                ao3_id=ao3_id,
                url=url,
                title=title,
                author=author,
                rating=rating,
                category=category,
                fandoms=fandoms,
                relationships=relationships,
                characters=characters,
                tags=tags,
                warnings=warnings,
                word_count=word_count,
                chapter_count=chapter_count,
                kudos=kudos,
                hits=hits,
                bookmarks=bookmarks,
                comments=comments,
                date_published=date_published,
                date_updated=date_published,
                summary=summary,
                is_reader_insert=is_reader,
                is_second_person=is_second,
                has_dialogue=has_dialogue,
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_work(self, work: AO3RoleplayWork):
        """Save work metadata to database."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO works (
                    id, ao3_id, url, title, author, rating, category,
                    fandoms, relationships, characters, tags, warnings,
                    word_count, chapter_count, kudos, hits, bookmarks, comments,
                    date_published, date_updated, summary,
                    is_reader_insert, is_second_person, has_dialogue,
                    indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work.id, work.ao3_id, work.url, work.title, work.author,
                work.rating, work.category,
                json.dumps(work.fandoms), json.dumps(work.relationships),
                json.dumps(work.characters), json.dumps(work.tags),
                json.dumps(work.warnings),
                work.word_count, work.chapter_count, work.kudos, work.hits,
                work.bookmarks, work.comments,
                work.date_published, work.date_updated, work.summary,
                1 if work.is_reader_insert else 0,
                1 if work.is_second_person else 0,
                1 if work.has_dialogue else 0,
                work.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_tag(self, tag: str, max_pages: int = None):
        """Index all works for a specific tag."""
        max_pages = max_pages or CONFIG["pages_per_search"]

        # Check progress
        cursor = self.conn.execute(
            "SELECT last_page, completed FROM search_progress WHERE tag = ?",
            (tag,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"Tag '{tag}' already completed")
            return

        self.logger.info(f"Indexing tag: {tag} (starting page {start_page})")

        encoded_tag = quote_plus(tag)
        base_url = f"{CONFIG['base_url']}/tags/{encoded_tag}/works"

        total_found = 0
        page = start_page

        while page <= max_pages:
            params = dict(SEARCH_FILTERS)
            params['page'] = str(page)

            url = f"{base_url}?{urlencode(params)}"
            soup = self._fetch(url)

            if not soup:
                self.logger.warning(f"Failed to fetch page {page}")
                break

            # Find work listings
            works = soup.select('li.work.blurb')

            if not works:
                self.logger.info(f"No more works found at page {page}")
                # Mark as completed
                self.conn.execute("""
                    INSERT OR REPLACE INTO search_progress
                    (tag, last_page, total_found, completed, updated_at)
                    VALUES (?, ?, ?, 1, ?)
                """, (tag, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            for work_elem in works:
                work = self._parse_work_listing(work_elem)
                if work:
                    self._save_work(work)
                    total_found += 1

                    if total_found % 100 == 0:
                        self.logger.info(f"  Indexed {total_found} works...")

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO search_progress
                (tag, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, 0, ?)
            """, (tag, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            page += 1

        self.logger.info(f"Completed tag '{tag}': {total_found} works indexed")

    def download_work(self, ao3_id: int) -> Optional[str]:
        """Download full work content."""
        url = f"{CONFIG['base_url']}/works/{ao3_id}?view_adult=true&view_full_work=true"
        soup = self._fetch(url)

        if not soup:
            return None

        # Get chapter content
        chapters = soup.select('div.chapter div.userstuff')
        if not chapters:
            # Single chapter work
            chapters = soup.select('div.userstuff[role="article"]')

        if not chapters:
            return None

        content_parts = []
        for i, chapter in enumerate(chapters, 1):
            # Get chapter title if exists
            title_elem = chapter.find_previous('h3', class_='title')
            if title_elem:
                content_parts.append(f"\n## Chapter {i}: {title_elem.get_text(strip=True)}\n")
            else:
                content_parts.append(f"\n## Chapter {i}\n")

            # Get text content, preserving paragraphs
            for p in chapter.find_all(['p', 'br']):
                if p.name == 'p':
                    text = p.get_text(strip=True)
                    if text:
                        content_parts.append(text + "\n\n")

        return ''.join(content_parts)

    def download_pending(self, limit: int = 100, min_kudos: int = 50):
        """Download pending works."""
        cursor = self.conn.execute("""
            SELECT ao3_id, title FROM works
            WHERE downloaded = 0 AND kudos >= ?
            ORDER BY kudos DESC
            LIMIT ?
        """, (min_kudos, limit))

        works = cursor.fetchall()
        self.logger.info(f"Downloading {len(works)} works (min {min_kudos} kudos)")

        storage_dir = Path(CONFIG["storage_root"]) / "stories"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for i, row in enumerate(works, 1):
            ao3_id = row['ao3_id']
            title = row['title']

            self.logger.info(f"[{i}/{len(works)}] Downloading: {title[:50]}...")

            content = self.download_work(ao3_id)

            if content:
                # Save content
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
                filename = f"{ao3_id}_{safe_title}.txt"
                filepath = storage_dir / filename

                filepath.write_text(content, encoding='utf-8')

                # Update database
                self.conn.execute("""
                    UPDATE works SET downloaded = 1, content_path = ?
                    WHERE ao3_id = ?
                """, (str(filepath), ao3_id))
                self.conn.commit()
            else:
                self.conn.execute("""
                    UPDATE works SET error = 'Download failed'
                    WHERE ao3_id = ?
                """, (ao3_id,))
                self.conn.commit()

    def run_full_index(self):
        """Run full indexing for all roleplay tags."""
        self.logger.info("=" * 60)
        self.logger.info("AO3 Roleplay Content Indexer")
        self.logger.info("=" * 60)

        for tag in ROLEPLAY_TAGS:
            try:
                self.index_tag(tag)
            except KeyboardInterrupt:
                self.logger.info("Interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error indexing tag '{tag}': {e}")
                continue

        # Print stats
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_reader_insert = 1 THEN 1 ELSE 0 END) as reader_insert,
                SUM(CASE WHEN is_second_person = 1 THEN 1 ELSE 0 END) as second_person,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded
            FROM works
        """)
        stats = cursor.fetchone()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("INDEXING COMPLETE")
        self.logger.info(f"  Total works:      {stats['total']:,}")
        self.logger.info(f"  Reader-insert:    {stats['reader_insert']:,}")
        self.logger.info(f"  Second person:    {stats['second_person']:,}")
        self.logger.info(f"  Downloaded:       {stats['downloaded']:,}")
        self.logger.info("=" * 60)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AO3 Roleplay Content Scraper")
    parser.add_argument('command', choices=['index', 'download', 'stats'],
                        help='Command to run')
    parser.add_argument('--tag', help='Specific tag to index')
    parser.add_argument('--limit', type=int, default=100,
                        help='Download limit')
    parser.add_argument('--min-kudos', type=int, default=50,
                        help='Minimum kudos for download')

    args = parser.parse_args()

    scraper = AO3RoleplayScraper()

    if args.command == 'index':
        if args.tag:
            scraper.index_tag(args.tag)
        else:
            scraper.run_full_index()

    elif args.command == 'download':
        scraper.download_pending(args.limit, args.min_kudos)

    elif args.command == 'stats':
        cursor = scraper.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_reader_insert = 1 THEN 1 ELSE 0 END) as reader_insert,
                SUM(CASE WHEN is_second_person = 1 THEN 1 ELSE 0 END) as second_person,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded,
                SUM(kudos) as total_kudos,
                AVG(word_count) as avg_words
            FROM works
        """)
        stats = cursor.fetchone()

        print("\n📚 AO3 Roleplay Archive Stats")
        print("=" * 40)
        print(f"Total indexed:    {stats['total']:,}")
        print(f"Reader-insert:    {stats['reader_insert']:,}")
        print(f"Second person:    {stats['second_person']:,}")
        print(f"Downloaded:       {stats['downloaded']:,}")
        print(f"Total kudos:      {stats['total_kudos']:,}")
        print(f"Avg word count:   {int(stats['avg_words'] or 0):,}")

if __name__ == "__main__":
    main()
