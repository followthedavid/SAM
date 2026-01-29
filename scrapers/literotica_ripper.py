#!/usr/bin/env python3
"""
Literotica Interactive/Dialogue Scraper
Target: Interactive stories, chat/text format, dialogue-heavy content
Storage: External drives only
Output: Training data optimized for roleplay conversation

FIXED (2026-01-28):
- Literotica is now a React SPA using React Server Components (RSC) streaming.
- HTML parsing fails because story data is serialized in RSC format, not DOM elements.
- Solution: Extract story JSON objects from the RSC serialized data in the page source.
- Story content pages still render text in <p> tags, so download_story works with
  minor adjustments to also extract from RSC data when needed.

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
import random
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
    "rate_limit_seconds": 3.0,  # Increased base delay
    "random_delay_min": 2.0,    # Minimum random delay
    "random_delay_max": 5.0,    # Maximum random delay
    "max_retries": 5,           # Increased retries
    "retry_delay": 5.0,         # Base retry delay (exponential backoff applied)
    "pages_per_category": 500,
}

# Realistic User-Agents for rotation (updated 2026-01-28)
USER_AGENTS = [
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

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
# RSC DATA EXTRACTION
# ============================================================================

def extract_stories_from_rsc(html: str) -> List[Dict]:
    """
    Extract story objects from Literotica's JavaScript hydration data.

    Literotica uses a custom JavaScript format with $R array assignments.
    Story objects have fields like: id, url, title, rate_all, view_count, etc.
    The format uses unquoted keys and JavaScript boolean values (!0, !1).

    Example format in page (fields can be in any order):
    {...,date_approve:"01/28/2026",description:"...",id:4282320,...,title:"Story Title",
    type:"story",url:"story-slug",view_count:107,...}

    Updated 2026-01-28: Handles the $R[] hydration format with flexible field ordering.
    """
    stories = []
    seen_ids = set()

    # The story objects contain type:"story" and have specific fields.
    # Fields can appear in any order, and objects can be nested (tags array).
    # We need to find objects with type:"story" that also have id, url, title, view_count.

    # Strategy: Find all type:"story" positions, then extract the surrounding object
    type_story_positions = [m.start() for m in re.finditer(r'type:"story"', html)]

    for pos in type_story_positions:
        # Find the object boundaries by looking for the opening {
        # We need to be careful because there are nested objects (tags)
        # Look backwards for a { that isn't part of a nested object

        # Start search from a reasonable distance back
        search_start = max(0, pos - 1500)
        region = html[search_start:pos + 200]

        # Find the opening brace - it should be before "allow_vote" or "date_approve" or similar
        # Actually, let's find all { positions and match with }
        # Simpler: extract the fields we need using regex on this region

        # Extract fields from the region
        id_match = re.search(r'id:(\d{7})', region)
        title_match = re.search(r'title:"([^"]+)"', region)
        url_match = re.search(r'url:"([a-z0-9-]+)"', region)
        view_count_match = re.search(r'view_count:(\d+)', region)

        # Must have at least id, title, url to be a valid story
        if not (id_match and title_match and url_match):
            continue

        story_id = id_match.group(1)
        if story_id in seen_ids:
            continue
        seen_ids.add(story_id)

        title = title_match.group(1)
        url_slug = url_match.group(1)

        # Extract optional fields
        rating = 0.0
        rate_match = re.search(r'rate_all:([\d.]+)', region)
        if rate_match:
            rating = float(rate_match.group(1))

        views = 0
        if view_count_match:
            views = int(view_count_match.group(1))

        favorites = 0
        fav_match = re.search(r'favorite_count:(\d+)', region)
        if fav_match:
            favorites = int(fav_match.group(1))

        date_published = ""
        date_match = re.search(r'date_approve:"([^"]*)"', region)
        if date_match:
            date_published = date_match.group(1)

        description = ""
        desc_match = re.search(r'description:"([^"]*)"', region)
        if desc_match:
            description = desc_match.group(1)

        story = {
            "id": int(story_id),
            "url": url_slug,
            "title": title,
            "authorname": "",  # Author is in a separate $R reference
            "description": description,
            "rate_all": rating,
            "view_count": views,
            "favorite_count": favorites,
            "date_approve": date_published,
            "category": 0,
        }
        stories.append(story)

    return stories


def extract_story_content_from_rsc(html: str) -> str:
    """
    Extract story text content from a story page's RSC data.

    Story pages may also use RSC format. The actual story text is typically
    in <p> tags within the rendered HTML, but if that fails, we try to
    extract text content from the RSC stream.
    """
    # First try standard HTML parsing
    soup = BeautifulSoup(html, 'html.parser')

    content_parts = []

    # Try multiple content selectors
    for selector in ['div.aa_ht p', '.aa_ht p', 'article p', '.panel-body p']:
        paragraphs = soup.select(selector)
        if paragraphs and len(paragraphs) > 2:
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
            break

    # If HTML parsing yielded content, use it
    if content_parts and sum(len(p) for p in content_parts) > 500:
        return '\n\n'.join(content_parts)

    # Fallback: try to find all substantial <p> tags
    all_paragraphs = soup.find_all('p')
    for p in all_paragraphs:
        text = p.get_text(strip=True)
        if text and len(text) > 50:
            content_parts.append(text)

    if content_parts and sum(len(p) for p in content_parts) > 500:
        return '\n\n'.join(content_parts)

    # Last resort: extract text blocks from RSC data
    # Look for long text strings that appear to be story content
    text_blocks = re.findall(r'"([^"]{200,})"', html)
    story_texts = []
    for block in text_blocks:
        # Unescape common sequences
        block = block.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
        # Skip if it looks like code or metadata
        if not any(skip in block for skip in ['function(', 'className', 'createElement', '{', '}']):
            story_texts.append(block)

    if story_texts:
        return '\n\n'.join(story_texts)

    return ''

# ============================================================================
# SCRAPING
# ============================================================================

class LiteroticaScraper:
    """Scraper for Literotica interactive/dialogue content.

    Uses RSC data extraction instead of HTML DOM parsing, since Literotica
    is now a React SPA that uses React Server Components streaming format.

    ANTI-BOT MEASURES (updated 2026-01-28):
    - User-Agent rotation with realistic browser signatures
    - Random delays between requests (2-5 seconds)
    - Referer header spoofing
    - Exponential backoff on 403/429 responses
    - Session cookie persistence
    """

    def __init__(self):
        self.session = requests.Session()
        self._update_session_headers()
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0
        self._consecutive_errors = 0

    def _get_random_user_agent(self) -> str:
        """Get a random realistic User-Agent."""
        return random.choice(USER_AGENTS)

    def _get_random_delay(self) -> float:
        """Get a random delay between configured min and max."""
        return random.uniform(
            CONFIG.get("random_delay_min", 2.0),
            CONFIG.get("random_delay_max", 5.0)
        )

    def _update_session_headers(self):
        """Update session with new random User-Agent and browser headers."""
        self.session.headers.update({
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            # Note: Don't request 'br' (Brotli) unless brotli library is installed
            # requests handles gzip/deflate automatically
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": f"{CONFIG['base_url']}/",
        })

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("literotica")
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers on re-init
        if not logger.handlers:
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
        """Enforce rate limiting with random jitter."""
        elapsed = time.time() - self.last_request
        # Use random delay instead of fixed delay
        min_delay = self._get_random_delay()
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed + random.uniform(0.5, 1.5)
            time.sleep(sleep_time)
        self.last_request = time.time()

    def _fetch_raw(self, url: str, retries: int = 0) -> Optional[str]:
        """Fetch raw HTML text from a URL with anti-bot measures."""
        self._rate_limit()

        # Rotate User-Agent on each request
        self.session.headers["User-Agent"] = self._get_random_user_agent()

        # Set Referer based on URL
        if "/s/" in url:
            self.session.headers["Referer"] = f"{CONFIG['base_url']}/c/gay-male-stories"
        else:
            self.session.headers["Referer"] = f"{CONFIG['base_url']}/"

        try:
            resp = self.session.get(url, timeout=30)

            # Handle rate limiting and forbidden responses
            if resp.status_code in [403, 429]:
                self._consecutive_errors += 1
                # Exponential backoff: 5s, 10s, 20s, 40s, 80s, max 120s
                backoff_delay = min(CONFIG["retry_delay"] * (2 ** retries), 120)
                # Add random jitter to backoff
                backoff_delay += random.uniform(1, 5)

                self.logger.warning(
                    f"Got {resp.status_code} for {url}. "
                    f"Backing off for {backoff_delay:.1f}s (retry {retries + 1}/{CONFIG['max_retries']})"
                )

                if retries < CONFIG["max_retries"]:
                    time.sleep(backoff_delay)
                    # Rotate User-Agent before retry
                    self._update_session_headers()
                    return self._fetch_raw(url, retries + 1)
                else:
                    self.logger.error(f"Max retries exceeded for {url}")
                    return None

            resp.raise_for_status()
            self._consecutive_errors = 0  # Reset on success
            return resp.text

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fetch error for {url}: {e}")
            if retries < CONFIG["max_retries"]:
                # Exponential backoff for other errors too
                backoff_delay = min(CONFIG["retry_delay"] * (2 ** retries), 60)
                time.sleep(backoff_delay)
                return self._fetch_raw(url, retries + 1)
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

    def _rsc_story_to_litstory(self, story_data: Dict, category_slug: str) -> LitStory:
        """Convert an RSC-extracted story dict to a LitStory object."""
        url_slug = story_data.get("url", "")
        lit_id = url_slug or str(story_data.get("id", ""))
        full_url = f"{CONFIG['base_url']}/s/{url_slug}"

        title = story_data.get("title", "Untitled")
        author = story_data.get("authorname", "Anonymous")
        description = story_data.get("description", "")
        rating = story_data.get("rate_all", 0.0)
        views = story_data.get("view_count", 0)
        favorites = story_data.get("favorite_count", 0)
        date_published = story_data.get("date_approve", "")

        # Tags from description
        tags = []
        desc_lower = description.lower()
        title_lower = title.lower()
        combined = f"{desc_lower} {title_lower}"
        for indicator in ROLEPLAY_INDICATORS:
            if indicator in combined:
                tags.append(indicator)

        return LitStory(
            id=hashlib.md5(f"lit_{lit_id}".encode()).hexdigest()[:16],
            lit_id=lit_id,
            url=full_url,
            title=title,
            author=author,
            author_url=f"{CONFIG['base_url']}/stories/memberpage.php?uid={author}&page=submissions",
            category=category_slug,
            description=description,
            rating=rating,
            views=views,
            favorites=favorites,
            page_count=1,
            date_published=date_published,
            tags=tags,
            has_dialogue=len(tags) > 0,
            dialogue_ratio=0.0,  # Calculate on download
            indexed_at=datetime.now().isoformat(),
        )

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
        """Index stories from a category using RSC data extraction."""
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
        empty_pages = 0
        page = start_page

        while page <= CONFIG["pages_per_category"]:
            url = f"{CONFIG['base_url']}/c/{category_slug}/{page}-page"
            html = self._fetch_raw(url)

            if not html:
                empty_pages += 1
                if empty_pages >= 3:
                    self.logger.info(f"3 consecutive failed fetches, stopping at page {page}")
                    break
                page += 1
                continue

            # Extract stories from the RSC data in the page source
            stories = extract_stories_from_rsc(html)

            if not stories:
                empty_pages += 1
                if empty_pages >= 3:
                    self.logger.info(f"No stories found for 3 consecutive pages, stopping at page {page}")
                    self.conn.execute("""
                        INSERT OR REPLACE INTO category_progress
                        (category, last_page, total_found, completed, updated_at)
                        VALUES (?, ?, ?, 1, ?)
                    """, (category_slug, page, total_found, datetime.now().isoformat()))
                    self.conn.commit()
                    break
                page += 1
                continue

            empty_pages = 0  # Reset on success

            for story_data in stories:
                story = self._rsc_story_to_litstory(story_data, category_slug)
                self._save_story(story)
                total_found += 1

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO category_progress
                (category, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, 0, ?)
            """, (category_slug, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            self.logger.info(f"  Page {page}: {len(stories)} stories (total: {total_found})")

            page += 1

        self.logger.info(f"Category '{category_name}': {total_found} stories")

    def download_story(self, url: str) -> Optional[str]:
        """Download full story content."""
        html = self._fetch_raw(url)
        if not html:
            return None

        content = extract_story_content_from_rsc(html)

        if not content or len(content) < 200:
            return None

        # Check for multiple pages - look for page links in the HTML
        # Literotica story pages use ?page=N format
        page_matches = re.findall(r'["\']([^"\']*\?page=(\d+)[^"\']*)["\']', html)
        if page_matches:
            max_page = max(int(m[1]) for m in page_matches)

            for page_num in range(2, max_page + 1):
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"

                page_html = self._fetch_raw(page_url)
                if page_html:
                    page_content = extract_story_content_from_rsc(page_html)
                    if page_content:
                        content += "\n\n" + page_content

        return content

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
        self.logger.info("Literotica Scraper - RSC Data Extraction Mode")
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
        if stats['avg_rating']:
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

        print("\nLiterotica Archive Stats")
        print("=" * 40)
        print(f"Total indexed:    {stats['total']:,}")
        print(f"Dialogue-heavy:   {stats['dialogue_heavy']:,}")
        print(f"Downloaded:       {stats['downloaded']:,}")
        print(f"Total views:      {stats['total_views'] or 0:,}")
        print(f"Avg dialogue %:   {(stats['avg_dialogue'] or 0) * 100:.1f}%")

if __name__ == "__main__":
    main()
