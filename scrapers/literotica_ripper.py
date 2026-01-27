#!/usr/bin/env python3
"""
Literotica Interactive/Dialogue Scraper
Target: Interactive stories, chat/text format, dialogue-heavy content
Storage: External drives only
Output: Training data optimized for roleplay conversation

Focus categories:
- Interactive (actual CYOA)
- Letters & Transcripts (dialogue/chat format)
- Text With Audio (conversational)
- High dialogue ratio stories
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
from urllib.parse import urljoin, quote_plus

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.literotica.com",
    "storage_root": "/Volumes/David External/literotica_archive",
    "db_path": "/Volumes/David External/literotica_archive/literotica_index.db",
    "rate_limit_seconds": 2.0,
    "max_retries": 3,
    "retry_delay": 5.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "pages_per_category": 500,
}

# Categories to scrape - focus on interactive/dialogue
CATEGORIES = {
    # Primary targets - interactive/conversational
    "interracial-erotic-stories": "Interracial Love",  # Often dialogue-heavy
    "loving-wives": "Loving Wives",  # Lots of dialogue
    "erotic-couplings": "Erotic Couplings",
    "romance-stories": "Romance",
    "first-time-sex-stories": "First Time",
    "lesbian-sex-stories": "Lesbian Sex",
    "gay-male-stories": "Gay Male",
    "mature-sex": "Mature",
    "group-sex-stories": "Group Sex",
    "fetish-stories": "Fetish",
    "bdsm-stories": "BDSM",
    "mind-control": "Mind Control",
    "non-consent-stories": "NonConsent/Reluctance",
    "taboo-sex-stories": "Taboo",
}

# Story tags that indicate roleplay-suitable content
ROLEPLAY_INDICATORS = [
    'dialogue', 'conversation', 'texting', 'chat', 'roleplay',
    'pov', 'second person', 'you', 'interactive', 'choose',
    'first person', 'narrative', 'story'
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LitStory:
    """Metadata for a Literotica story."""
    id: str
    lit_id: str
    url: str
    title: str
    author: str
    author_url: str
    category: str
    description: str
    rating: float
    views: int
    favorites: int
    page_count: int
    date_published: str
    tags: List[str]
    has_dialogue: bool
    dialogue_ratio: float
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
        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY,
            lit_id TEXT UNIQUE,
            url TEXT,
            title TEXT,
            author TEXT,
            author_url TEXT,
            category TEXT,
            description TEXT,
            rating REAL,
            views INTEGER,
            favorites INTEGER,
            page_count INTEGER,
            date_published TEXT,
            tags TEXT,
            has_dialogue INTEGER,
            dialogue_ratio REAL,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0,
            content_path TEXT,
            error TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_progress (
            category TEXT PRIMARY KEY,
            last_page INTEGER DEFAULT 0,
            total_found INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON stories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rating ON stories(rating)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogue ON stories(has_dialogue)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPING
# ============================================================================

class LiteroticaScraper:
    """Scraper for Literotica interactive/dialogue content."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml",
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("literotica")
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
                time.sleep(CONFIG["retry_delay"])
                return self._fetch(url, retries + 1)
            return None

    def _calculate_dialogue_ratio(self, text: str) -> float:
        """Calculate ratio of dialogue to narrative."""
        if not text:
            return 0.0

        # Count quoted text (dialogue)
        dialogue_matches = re.findall(r'"[^"]+"|\'[^\']+\'', text)
        dialogue_chars = sum(len(m) for m in dialogue_matches)

        total_chars = len(text)
        if total_chars == 0:
            return 0.0

        return dialogue_chars / total_chars

    def _parse_story_card(self, card, category: str) -> Optional[LitStory]:
        """Parse a story card from category page (updated for CSS modules)."""
        try:
            # Title and URL - Literotica uses CSS modules with hashed classes
            # Look for card link or title patterns
            title_elem = card.select_one('a[class*="_card_link"], a[class*="_card_title"], a[href*="/s/"]')
            if not title_elem:
                # Try finding any link that points to a story
                links = card.select('a[href*="/s/"]')
                for link in links:
                    if link.get_text(strip=True):
                        title_elem = link
                        break

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            if not url.startswith('http'):
                url = urljoin(CONFIG["base_url"], url)

            # Extract story ID from URL
            lit_id_match = re.search(r'/s/([^/]+)', url)
            lit_id = lit_id_match.group(1) if lit_id_match else hashlib.md5(url.encode()).hexdigest()[:12]

            # Author
            author_elem = card.select_one('a.br_author, .author a, span.b-user-info a')
            author = author_elem.get_text(strip=True) if author_elem else "Anonymous"
            author_url = author_elem.get('href', '') if author_elem else ""

            # Description
            desc_elem = card.select_one('.br_desc, .story-description, p')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Rating
            rating_elem = card.select_one('.br_rate, .rating, .score')
            rating = 0.0
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'([\d.]+)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))

            # Views
            views = 0
            views_elem = card.select_one('.br_views, .views')
            if views_elem:
                views_text = views_elem.get_text(strip=True).replace(',', '').replace('K', '000').replace('M', '000000')
                views_match = re.search(r'(\d+)', views_text)
                if views_match:
                    views = int(views_match.group(1))

            # Date
            date_elem = card.select_one('.br_date, .date, time')
            date_published = date_elem.get_text(strip=True) if date_elem else ""

            # Tags from description
            tags = []
            desc_lower = description.lower()
            for indicator in ROLEPLAY_INDICATORS:
                if indicator in desc_lower:
                    tags.append(indicator)

            return LitStory(
                id=hashlib.md5(f"lit_{lit_id}".encode()).hexdigest()[:16],
                lit_id=lit_id,
                url=url,
                title=title,
                author=author,
                author_url=author_url,
                category=category,
                description=description,
                rating=rating,
                views=views,
                favorites=0,
                page_count=1,
                date_published=date_published,
                tags=tags,
                has_dialogue=len(tags) > 0,
                dialogue_ratio=0.0,  # Calculate on download
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_story(self, story: LitStory):
        """Save story to database."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO stories (
                    id, lit_id, url, title, author, author_url, category,
                    description, rating, views, favorites, page_count,
                    date_published, tags, has_dialogue, dialogue_ratio, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                story.id, story.lit_id, story.url, story.title, story.author,
                story.author_url, story.category, story.description,
                story.rating, story.views, story.favorites, story.page_count,
                story.date_published, json.dumps(story.tags),
                1 if story.has_dialogue else 0, story.dialogue_ratio,
                story.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_category(self, category_slug: str, category_name: str):
        """Index stories from a category."""
        # Check progress
        cursor = self.conn.execute(
            "SELECT last_page, completed FROM category_progress WHERE category = ?",
            (category_slug,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"Category '{category_name}' already completed")
            return

        self.logger.info(f"Indexing: {category_name} (page {start_page})")

        total_found = 0
        page = start_page

        while page <= CONFIG["pages_per_category"]:
            url = f"{CONFIG['base_url']}/c/{category_slug}/{page}-page"
            soup = self._fetch(url)

            if not soup:
                break

            # Find story cards - Literotica uses CSS modules with hashed class names
            # Pattern: _card_XXXXX_NNN where XXXXX is a hash
            cards = soup.select('[class*="_card_"]')

            # Filter to only actual story cards (not cover images, etc)
            story_cards = []
            for card in cards:
                # Must contain a story link
                if card.select_one('a[href*="/s/"]'):
                    story_cards.append(card)
            cards = story_cards

            if not cards:
                # Fallback: just find story links directly
                story_links = soup.select('a[href*="/s/"]')
                if story_links:
                    # Create pseudo-cards from links
                    cards = [link.parent for link in story_links if link.parent]

            if not cards:
                    self.logger.info(f"No more stories at page {page}")
                    self.conn.execute("""
                        INSERT OR REPLACE INTO category_progress
                        (category, last_page, total_found, completed, updated_at)
                        VALUES (?, ?, ?, 1, ?)
                    """, (category_slug, page, total_found, datetime.now().isoformat()))
                    self.conn.commit()
                    break

            for card in cards:
                story = self._parse_story_card(card, category_slug)
                if story:
                    self._save_story(story)
                    total_found += 1

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO category_progress
                (category, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, 0, ?)
            """, (category_slug, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            if total_found % 100 == 0:
                self.logger.info(f"  {total_found} stories indexed...")

            page += 1

        self.logger.info(f"Category '{category_name}': {total_found} stories")

    def download_story(self, url: str) -> Optional[str]:
        """Download full story content."""
        soup = self._fetch(url)
        if not soup:
            return None

        content_parts = []

        # Find story content
        content_div = soup.select_one('.aa_ht, .story-content, #storytext, article.story')
        if content_div:
            for p in content_div.find_all(['p', 'div.aa_ht']):
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text + "\n\n")

        # Check for multiple pages
        page_links = soup.select('a.l_bj, .page-link, a[href*="page="]')
        if page_links:
            # Find max page number
            max_page = 1
            for link in page_links:
                href = link.get('href', '')
                page_match = re.search(r'page=(\d+)', href)
                if page_match:
                    max_page = max(max_page, int(page_match.group(1)))

            # Fetch remaining pages
            for page_num in range(2, max_page + 1):
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"

                page_soup = self._fetch(page_url)
                if page_soup:
                    content_div = page_soup.select_one('.aa_ht, .story-content, #storytext')
                    if content_div:
                        for p in content_div.find_all(['p', 'div.aa_ht']):
                            text = p.get_text(strip=True)
                            if text:
                                content_parts.append(text + "\n\n")

        return ''.join(content_parts)

    def download_pending(self, limit: int = 100, min_rating: float = 4.0):
        """Download pending stories."""
        cursor = self.conn.execute("""
            SELECT lit_id, url, title FROM stories
            WHERE downloaded = 0 AND rating >= ?
            ORDER BY rating DESC, views DESC
            LIMIT ?
        """, (min_rating, limit))

        stories = cursor.fetchall()
        self.logger.info(f"Downloading {len(stories)} stories (min rating {min_rating})")

        storage_dir = Path(CONFIG["storage_root"]) / "stories"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for i, row in enumerate(stories, 1):
            lit_id = row['lit_id']
            url = row['url']
            title = row['title']

            self.logger.info(f"[{i}/{len(stories)}] {title[:50]}...")

            content = self.download_story(url)

            if content:
                # Calculate dialogue ratio
                dialogue_ratio = self._calculate_dialogue_ratio(content)

                # Save content
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
                filename = f"{lit_id}_{safe_title}.txt"
                filepath = storage_dir / filename

                filepath.write_text(content, encoding='utf-8')

                # Update database
                self.conn.execute("""
                    UPDATE stories SET
                        downloaded = 1,
                        content_path = ?,
                        dialogue_ratio = ?,
                        has_dialogue = ?
                    WHERE lit_id = ?
                """, (str(filepath), dialogue_ratio, 1 if dialogue_ratio > 0.2 else 0, lit_id))
                self.conn.commit()
            else:
                self.conn.execute(
                    "UPDATE stories SET error = 'Download failed' WHERE lit_id = ?",
                    (lit_id,)
                )
                self.conn.commit()

    def run_full_index(self):
        """Index all categories."""
        self.logger.info("=" * 60)
        self.logger.info("Literotica Scraper - Dialogue/Interactive Focus")
        self.logger.info("=" * 60)

        for slug, name in CATEGORIES.items():
            try:
                self.index_category(slug, name)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error with {name}: {e}")
                continue

        # Stats
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN has_dialogue = 1 THEN 1 ELSE 0 END) as dialogue_heavy,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded,
                AVG(rating) as avg_rating
            FROM stories
        """)
        stats = cursor.fetchone()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("COMPLETE")
        self.logger.info(f"  Total stories:    {stats['total']:,}")
        self.logger.info(f"  Dialogue-heavy:   {stats['dialogue_heavy']:,}")
        self.logger.info(f"  Downloaded:       {stats['downloaded']:,}")
        self.logger.info(f"  Avg rating:       {stats['avg_rating']:.2f}")
        self.logger.info("=" * 60)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Literotica Scraper")
    parser.add_argument('command', choices=['index', 'download', 'stats'])
    parser.add_argument('--category', help='Specific category slug')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--min-rating', type=float, default=4.0)

    args = parser.parse_args()

    scraper = LiteroticaScraper()

    if args.command == 'index':
        if args.category:
            name = CATEGORIES.get(args.category, args.category)
            scraper.index_category(args.category, name)
        else:
            scraper.run_full_index()

    elif args.command == 'download':
        scraper.download_pending(args.limit, args.min_rating)

    elif args.command == 'stats':
        cursor = scraper.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN has_dialogue = 1 THEN 1 ELSE 0 END) as dialogue_heavy,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded,
                SUM(views) as total_views,
                AVG(dialogue_ratio) as avg_dialogue
            FROM stories
        """)
        stats = cursor.fetchone()

        print("\n📖 Literotica Archive Stats")
        print("=" * 40)
        print(f"Total indexed:    {stats['total']:,}")
        print(f"Dialogue-heavy:   {stats['dialogue_heavy']:,}")
        print(f"Downloaded:       {stats['downloaded']:,}")
        print(f"Total views:      {stats['total_views']:,}")
        print(f"Avg dialogue %:   {(stats['avg_dialogue'] or 0) * 100:.1f}%")

if __name__ == "__main__":
    main()
