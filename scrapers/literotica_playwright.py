#!/usr/bin/env python3
"""
Literotica Playwright Scraper

Uses headless browser to scrape Literotica's JavaScript SPA.
Targets dialogue-heavy and roleplay-suitable content.

Usage:
    python literotica_playwright.py index --categories gay-male-stories,romance-stories
    python literotica_playwright.py download --limit 1000
    python literotica_playwright.py stats
"""

import os
import re
import json
import time
import asyncio
import hashlib
import sqlite3
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.literotica.com",
    "storage_root": "/Volumes/David External/literotica_archive",
    "db_path": "/Volumes/David External/literotica_archive/literotica_index.db",
    "rate_limit_seconds": 2.0,
    "page_timeout": 30000,
    "max_pages_per_category": 100,
}

# Categories to scrape
CATEGORIES = [
    "gay-male-stories",
    "romance-stories",
    "erotic-couplings",
    "first-time-sex-stories",
    "lesbian-sex-stories",
    "group-sex-stories",
    "bdsm-stories",
    "mind-control",
    "fetish-stories",
]

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
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            author TEXT,
            category TEXT,
            description TEXT,
            rating REAL,
            page_count INTEGER DEFAULT 1,
            word_count INTEGER DEFAULT 0,
            date_published TEXT,
            tags TEXT,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            content_path TEXT
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded ON stories(downloaded)")

    conn.commit()
    return conn

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LitStory:
    id: str
    url: str
    title: str
    author: str
    category: str
    description: str
    rating: float
    page_count: int
    word_count: int
    date_published: str
    tags: List[str]
    indexed_at: str
    downloaded: int = 0
    content_path: str = ""

# ============================================================================
# SCRAPER
# ============================================================================

class LiteroticaPlaywrightScraper:
    """Playwright-based scraper for Literotica."""

    def __init__(self):
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def _setup_logging(self) -> logging.Logger:
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("literotica_pw")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler(log_dir / "playwright_scraper.log")
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)

            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(console)

        return logger

    async def init_browser(self):
        """Initialize Playwright browser with stealth settings."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
            ]
        )
        # Create context with realistic viewport and user agent
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        self.page = await context.new_page()

        # Stealth: Override navigator properties
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

    async def close_browser(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    async def scrape_category_page(self, category: str, page_num: int, retry: int = 0) -> List[LitStory]:
        """Scrape a single category page with retry logic."""
        url = f"{CONFIG['base_url']}/c/{category}/{page_num}-page"
        self.logger.info(f"Scraping {url}...")
        max_retries = 3

        try:
            # Random delay before request (2-5 seconds)
            await asyncio.sleep(random.uniform(2, 5))

            await self.page.goto(url, timeout=CONFIG["page_timeout"], wait_until="domcontentloaded")

            # Wait for page to stabilize
            await asyncio.sleep(random.uniform(1, 3))

            # Check for Cloudflare or consent dialogs
            try:
                accept_btn = await self.page.query_selector('button:has-text("Accept"), button:has-text("I Accept"), [class*="consent"] button')
                if accept_btn:
                    await accept_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Wait for story cards to load
            await asyncio.sleep(1)

            stories = []

            # Find all story links - they contain /s/ in href
            story_links = await self.page.query_selector_all('a[href*="/s/"]')

            seen_urls = set()
            for link in story_links:
                try:
                    href = await link.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    if '/s/' not in href:
                        continue

                    seen_urls.add(href)

                    # Get story URL
                    story_url = href if href.startswith('http') else urljoin(CONFIG['base_url'], href)

                    # Get title from link text or parent
                    title = await link.inner_text()
                    title = title.strip() if title else ""

                    if not title or len(title) < 3:
                        continue

                    # Extract story ID from URL
                    id_match = re.search(r'/s/([^/]+)', story_url)
                    story_id = id_match.group(1) if id_match else hashlib.md5(story_url.encode()).hexdigest()[:16]

                    # Try to get parent card for more info
                    parent = await link.evaluate_handle('el => el.closest("[class*=card]")')

                    description = ""
                    author = ""
                    rating = 0.0

                    if parent:
                        # Try to extract description
                        try:
                            desc_el = await parent.query_selector('[class*="content"], p')
                            if desc_el:
                                description = await desc_el.inner_text()
                                description = description[:500] if description else ""
                        except:
                            pass

                        # Try to extract author
                        try:
                            author_el = await parent.query_selector('a[href*="/stories/memberpage"]')
                            if author_el:
                                author = await author_el.inner_text()
                        except:
                            pass

                    story = LitStory(
                        id=hashlib.md5(f"lit_{story_id}".encode()).hexdigest()[:16],
                        url=story_url,
                        title=title,
                        author=author,
                        category=category,
                        description=description,
                        rating=rating,
                        page_count=1,
                        word_count=0,
                        date_published="",
                        tags=[],
                        indexed_at=datetime.now().isoformat(),
                    )
                    stories.append(story)

                except Exception as e:
                    continue

            return stories

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            # Retry with exponential backoff
            if retry < max_retries:
                wait_time = (2 ** retry) * 5 + random.uniform(1, 5)
                self.logger.info(f"Retrying in {wait_time:.1f}s (attempt {retry + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                return await self.scrape_category_page(category, page_num, retry + 1)
            return []

    def save_story(self, story: LitStory):
        """Save story to database."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO stories
                (id, url, title, author, category, description, rating,
                 page_count, word_count, date_published, tags, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                story.id, story.url, story.title, story.author, story.category,
                story.description, story.rating, story.page_count, story.word_count,
                story.date_published, json.dumps(story.tags), story.indexed_at
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error saving story: {e}")
            return False

    async def index_category(self, category: str, max_pages: int = 100):
        """Index all stories in a category."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Indexing category: {category}")
        self.logger.info('='*60)

        # Get progress
        cur = self.conn.execute(
            "SELECT last_page, total_found FROM category_progress WHERE category = ?",
            (category,)
        )
        row = cur.fetchone()
        start_page = (row['last_page'] + 1) if row else 1
        total_found = row['total_found'] if row else 0

        for page in range(start_page, start_page + max_pages):
            stories = await self.scrape_category_page(category, page)

            if not stories:
                self.logger.info(f"No more stories at page {page}")
                # Mark complete
                self.conn.execute("""
                    INSERT OR REPLACE INTO category_progress
                    (category, last_page, total_found, completed, updated_at)
                    VALUES (?, ?, ?, 1, ?)
                """, (category, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            for story in stories:
                if self.save_story(story):
                    total_found += 1

            self.logger.info(f"  Page {page}: {len(stories)} stories (total: {total_found})")

            # Save progress
            self.conn.execute("""
                INSERT OR REPLACE INTO category_progress
                (category, last_page, total_found, completed, updated_at)
                VALUES (?, ?, ?, 0, ?)
            """, (category, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            # Rate limit
            await asyncio.sleep(CONFIG["rate_limit_seconds"])

        self.logger.info(f"Category {category}: {total_found} total stories")
        return total_found

    async def download_story(self, url: str) -> Optional[str]:
        """Download full story content."""
        try:
            await self.page.goto(url, timeout=CONFIG["page_timeout"])
            await self.page.wait_for_load_state("networkidle", timeout=CONFIG["page_timeout"])

            # Wait for content to load
            await asyncio.sleep(1)

            # Find story content - usually in article or main content area
            content_selectors = [
                'article.aa_ht',
                '[class*="story-content"]',
                '.aa_ht',
                'article',
                'main',
            ]

            content = ""
            for selector in content_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        content = await el.inner_text()
                        if len(content) > 500:
                            break
                except:
                    continue

            if not content:
                # Try getting all paragraphs
                paragraphs = await self.page.query_selector_all('p')
                texts = []
                for p in paragraphs:
                    text = await p.inner_text()
                    if len(text) > 50:
                        texts.append(text)
                content = "\n\n".join(texts)

            return content if len(content) > 500 else None

        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return None

    async def download_stories(self, limit: int = 100):
        """Download story content for indexed stories."""
        self.logger.info(f"\nDownloading up to {limit} stories...")

        cur = self.conn.execute("""
            SELECT * FROM stories
            WHERE downloaded = 0
            ORDER BY rating DESC
            LIMIT ?
        """, (limit,))

        stories = cur.fetchall()
        downloaded = 0

        for story in stories:
            url = story['url']
            story_id = story['id']

            content = await self.download_story(url)

            if content:
                # Save content to file
                content_dir = Path(CONFIG["storage_root"]) / "stories" / story['category']
                content_dir.mkdir(parents=True, exist_ok=True)

                content_path = content_dir / f"{story_id}.txt"
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Update database
                word_count = len(content.split())
                self.conn.execute("""
                    UPDATE stories
                    SET downloaded = 1, content_path = ?, word_count = ?
                    WHERE id = ?
                """, (str(content_path), word_count, story_id))
                self.conn.commit()

                downloaded += 1
                self.logger.info(f"  Downloaded: {story['title'][:50]}... ({word_count} words)")

            await asyncio.sleep(CONFIG["rate_limit_seconds"])

        self.logger.info(f"\nDownloaded {downloaded} stories")
        return downloaded

    async def run_index(self, categories: List[str] = None, max_pages: int = 100):
        """Run full indexing."""
        categories = categories or CATEGORIES

        await self.init_browser()

        try:
            total = 0
            for category in categories:
                count = await self.index_category(category, max_pages)
                total += count

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"INDEXING COMPLETE: {total} total stories")
            self.logger.info('='*60)

        finally:
            await self.close_browser()

    async def run_download(self, limit: int = 100):
        """Run download."""
        await self.init_browser()

        try:
            await self.download_stories(limit)
        finally:
            await self.close_browser()

    def get_stats(self) -> Dict:
        """Get scraper statistics."""
        stats = {}

        cur = self.conn.execute("SELECT COUNT(*) FROM stories")
        stats['total_indexed'] = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM stories WHERE downloaded = 1")
        stats['total_downloaded'] = cur.fetchone()[0]

        cur = self.conn.execute("""
            SELECT category, COUNT(*) as count
            FROM stories GROUP BY category
            ORDER BY count DESC
        """)
        stats['by_category'] = dict(cur.fetchall())

        return stats

# ============================================================================
# CLI
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Literotica Playwright Scraper")
    parser.add_argument("command", choices=["index", "download", "stats"])
    parser.add_argument("--categories", "-c", help="Comma-separated categories")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Download limit")
    parser.add_argument("--pages", "-p", type=int, default=100, help="Max pages per category")

    args = parser.parse_args()

    scraper = LiteroticaPlaywrightScraper()

    if args.command == "index":
        categories = args.categories.split(",") if args.categories else None
        await scraper.run_index(categories, args.pages)

    elif args.command == "download":
        await scraper.run_download(args.limit)

    elif args.command == "stats":
        stats = scraper.get_stats()
        print("\n" + "="*50)
        print("  LITEROTICA SCRAPER STATS")
        print("="*50)
        print(f"\nTotal indexed: {stats['total_indexed']:,}")
        print(f"Total downloaded: {stats['total_downloaded']:,}")
        print("\nBy category:")
        for cat, count in stats['by_category'].items():
            print(f"  {cat}: {count:,}")

if __name__ == "__main__":
    asyncio.run(main())
