#!/usr/bin/env python3
"""
FirstVIEW Fashion Photo Scraper v2.0

Collects runway fashion photos with rich metadata:
- Designer/brand
- Season (SS26, FW25, etc.)
- City (Paris, Milan, London, NYC)
- Look numbers
- Credits (photographer, stylist, etc.)

Key improvements over v1:
- Zero-based pagination matching the site's actual API
- Full photo pagination within collections (infinite scroll pages)
- Checkpoint/resume: survives crashes, restarts from where it left off
- Incremental updates: only indexes new/changed collections
- Batched DB writes for performance
- WAL mode for crash-safe database

Usage:
    python firstview_ripper.py index          # Index all collections (resumable)
    python firstview_ripper.py index --fresh  # Wipe and re-index from scratch
    python firstview_ripper.py download       # Download photos + metadata
    python firstview_ripper.py stats          # Show statistics
    python firstview_ripper.py export         # Export to training format
"""

import os
import re
import json
import time
import sqlite3
import hashlib
import logging
import argparse
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse, parse_qs, quote_plus

import requests
from bs4 import BeautifulSoup

# Import robust session utilities
try:
    from robust_session import create_robust_session, robust_get, robust_download
    HAS_ROBUST = True
except ImportError:
    HAS_ROBUST = False

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://firstview.com",
    "storage_root": "/Volumes/David External/firstview_archive",
    "db_name": "firstview_index.db",
    "rate_limit": 1.0,        # seconds between requests
    "timeout": 30,
    "max_retries": 5,
    "checkpoint_every": 50,   # save checkpoint every N collections indexed
    "batch_size": 100,        # DB batch insert size
    "collections_per_page": 20,  # site returns 20 per page
}

# The site's actual filter values (discovered from the site)
FILTER_SEASONS = ["Spring/Summer", "Fall/Winter", "Prefall", "Cruise"]
FILTER_YEARS = list(range(2027, 1988, -1))  # 2027 down to 1989

# Cities from the site's s_p filter (country-city format)
FILTER_CITIES = [
    "Australia-Sydney", "Brazil-Sao+Paulo", "Canada-Toronto",
    "China-Beijing", "China-Shanghai", "Denmark-Copenhagen",
    "England-London", "France-Paris", "Germany-Berlin",
    "India-Mumbai", "Italy-Florence", "Italy-Milan",
    "Japan-Tokyo", "Kenya-Nairobi", "Korea-Seoul",
    "Malaysia-Kuala+Lumpur", "Mexico-Mexico+City",
    "Netherlands-Amsterdam", "New+Zealand-Auckland",
    "Portugal-Lisbon", "Russia-Moscow", "Singapore-Singapore",
    "Spain-Barcelona", "Spain-Madrid", "Sweden-Stockholm",
    "Thailand-Bangkok", "USA-Los+Angeles", "USA-New+York",
]

# Collection types from the site's s_t filter
COLLECTION_TYPES = [
    "Runway Collection", "Runway Details", "Runway Atmosphere",
    "Backstage Beauty and Fashion", "Lookbook", "Bridal Collection",
]

# Season short codes for metadata extraction
SEASON_CODES = []
for year in range(27, 88, -1):  # 2027 down to 1989
    yr = str(year).zfill(2)
    SEASON_CODES.extend([f"SS{yr}", f"FW{yr}", f"PF{yr}", f"CR{yr}"])

SEASON_LABELS = [
    "Spring/Summer", "Fall/Winter", "Spring / Summer", "Fall / Winter",
    "Autumn/Winter", "Autumn / Winter", "Pre-Fall", "Prefall",
    "Resort", "Cruise", "Couture", "Haute Couture",
    "RTW", "Ready-to-Wear",
]

CITIES = [
    "Paris", "Milan", "London", "New York", "Tokyo", "Berlin",
    "Florence", "Los Angeles", "Shanghai", "Sydney", "Copenhagen",
    "Stockholm", "Moscow", "Seoul", "Mumbai", "Sao Paulo",
    "Barcelona", "Madrid", "Amsterdam", "Toronto", "Beijing",
]

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Set up logging to both console and file."""
    log_dir = Path(CONFIG["storage_root"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ]
    )
    return logging.getLogger("firstview")

logger = logging.getLogger("firstview")

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Collection:
    id: int
    designer: str
    season: str
    city: str
    show_type: str  # RTW, Couture, Menswear
    url: str
    photo_count: int
    total_photos: int  # total photos reported by the site
    indexed_at: str
    fully_indexed: bool  # True if all photo pages were scraped

@dataclass
class Photo:
    id: str
    collection_id: int
    look_number: int
    image_url: str
    thumb_url: str
    designer: str
    season: str
    city: str
    credits: Dict  # photographer, stylist, hair, makeup, etc.
    tags: List[str]
    downloaded: bool
    local_path: Optional[str]

# ============================================================================
# DATABASE
# ============================================================================

class FirstViewDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a connection with WAL mode for crash safety."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY,
                designer TEXT,
                season TEXT,
                city TEXT,
                show_type TEXT,
                url TEXT,
                photo_count INTEGER DEFAULT 0,
                total_photos INTEGER DEFAULT 0,
                indexed_at TEXT,
                fully_indexed INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id TEXT PRIMARY KEY,
                collection_id INTEGER,
                look_number INTEGER,
                image_url TEXT,
                thumb_url TEXT,
                designer TEXT,
                season TEXT,
                city TEXT,
                credits TEXT,
                tags TEXT,
                downloaded INTEGER DEFAULT 0,
                local_path TEXT,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_photos_collection
            ON photos(collection_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_photos_downloaded
            ON photos(downloaded)
        """)

        # Checkpoint table for resumable discovery
        cur.execute("""
            CREATE TABLE IF NOT EXISTS discovery_checkpoint (
                strategy TEXT PRIMARY KEY,
                last_key TEXT,
                completed INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)

        # Discovered but not-yet-indexed collections
        cur.execute("""
            CREATE TABLE IF NOT EXISTS discovered_collections (
                id INTEGER PRIMARY KEY,
                title TEXT,
                discovered_at TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_collection(self, collection: Collection) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR REPLACE INTO collections
                (id, designer, season, city, show_type, url, photo_count,
                 total_photos, indexed_at, fully_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                collection.id, collection.designer, collection.season,
                collection.city, collection.show_type, collection.url,
                collection.photo_count, collection.total_photos,
                collection.indexed_at, 1 if collection.fully_indexed else 0
            ))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def add_photos_batch(self, photos: List[Photo]) -> int:
        """Batch insert photos for performance."""
        if not photos:
            return 0
        conn = self._get_conn()
        cur = conn.cursor()
        inserted = 0
        try:
            for photo in photos:
                cur.execute("""
                    INSERT OR IGNORE INTO photos
                    (id, collection_id, look_number, image_url, thumb_url,
                     designer, season, city, credits, tags, downloaded, local_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    photo.id, photo.collection_id, photo.look_number,
                    photo.image_url, photo.thumb_url, photo.designer,
                    photo.season, photo.city, json.dumps(photo.credits),
                    json.dumps(photo.tags), 0, None
                ))
                inserted += cur.rowcount
            conn.commit()
            return inserted
        finally:
            conn.close()

    def add_photo(self, photo: Photo) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO photos
                (id, collection_id, look_number, image_url, thumb_url,
                 designer, season, city, credits, tags, downloaded, local_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                photo.id, photo.collection_id, photo.look_number,
                photo.image_url, photo.thumb_url, photo.designer,
                photo.season, photo.city, json.dumps(photo.credits),
                json.dumps(photo.tags), 0, None
            ))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def add_discovered(self, coll_id: int, title: str) -> bool:
        """Record a discovered collection ID."""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO discovered_collections (id, title, discovered_at)
                VALUES (?, ?, ?)
            """, (coll_id, title, datetime.now().isoformat()))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def add_discovered_batch(self, items: List[Tuple[int, str]]) -> int:
        """Batch-record discovered collections."""
        if not items:
            return 0
        conn = self._get_conn()
        cur = conn.cursor()
        added = 0
        try:
            now = datetime.now().isoformat()
            for coll_id, title in items:
                cur.execute("""
                    INSERT OR IGNORE INTO discovered_collections (id, title, discovered_at)
                    VALUES (?, ?, ?)
                """, (coll_id, title, now))
                added += cur.rowcount
            conn.commit()
            return added
        finally:
            conn.close()

    def get_all_discovered(self) -> List[Tuple[int, str]]:
        """Get all discovered collection IDs."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM discovered_collections ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_unindexed_collections(self) -> List[Tuple[int, str]]:
        """Get discovered collections that haven't been fully indexed yet."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT d.id, d.title FROM discovered_collections d
            LEFT JOIN collections c ON d.id = c.id
            WHERE c.id IS NULL OR c.fully_indexed = 0
            ORDER BY d.id
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_indexed_collection_ids(self) -> Set[int]:
        """Get set of fully indexed collection IDs."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM collections WHERE fully_indexed = 1")
        ids = {row[0] for row in cur.fetchall()}
        conn.close()
        return ids

    def get_discovered_ids(self) -> Set[int]:
        """Get set of all discovered collection IDs."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM discovered_collections")
        ids = {row[0] for row in cur.fetchall()}
        conn.close()
        return ids

    def save_checkpoint(self, strategy: str, last_key: str, completed: bool = False):
        """Save discovery checkpoint for resume."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO discovery_checkpoint
            (strategy, last_key, completed, updated_at)
            VALUES (?, ?, ?, ?)
        """, (strategy, last_key, 1 if completed else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_checkpoint(self, strategy: str) -> Optional[Tuple[str, bool]]:
        """Get checkpoint for a strategy. Returns (last_key, completed)."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT last_key, completed FROM discovery_checkpoint WHERE strategy = ?
        """, (strategy,))
        row = cur.fetchone()
        conn.close()
        if row:
            return (row[0], bool(row[1]))
        return None

    def clear_checkpoints(self):
        """Clear all checkpoints for a fresh run."""
        conn = self._get_conn()
        conn.execute("DELETE FROM discovery_checkpoint")
        conn.execute("DELETE FROM discovered_collections")
        conn.commit()
        conn.close()

    def mark_downloaded(self, photo_id: str, local_path: str):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE photos SET downloaded = 1, local_path = ?
            WHERE id = ?
        """, (local_path, photo_id))
        conn.commit()
        conn.close()

    def get_pending_photos(self, limit: int = 100) -> List[Dict]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM photos WHERE downloaded = 0 LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()

        stats = {}

        cur.execute("SELECT COUNT(*) FROM discovered_collections")
        stats["discovered_collections"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM collections")
        stats["indexed_collections"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM collections WHERE fully_indexed = 1")
        stats["fully_indexed"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos")
        stats["total_photos"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos WHERE downloaded = 1")
        stats["downloaded"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos WHERE downloaded = 0")
        stats["pending"] = cur.fetchone()[0]

        # By season
        cur.execute("""
            SELECT season, COUNT(*) FROM photos
            WHERE season != '' GROUP BY season ORDER BY COUNT(*) DESC
        """)
        stats["by_season"] = dict(cur.fetchall())

        # By city
        cur.execute("""
            SELECT city, COUNT(*) FROM photos
            WHERE city != '' GROUP BY city ORDER BY COUNT(*) DESC
        """)
        stats["by_city"] = dict(cur.fetchall())

        # Top designers
        cur.execute("""
            SELECT designer, COUNT(*) FROM photos
            WHERE designer != '' GROUP BY designer ORDER BY COUNT(*) DESC LIMIT 20
        """)
        stats["top_designers"] = dict(cur.fetchall())

        # Checkpoint status
        cur.execute("SELECT strategy, completed FROM discovery_checkpoint")
        stats["checkpoints"] = dict(cur.fetchall())

        conn.close()
        return stats


# ============================================================================
# SCRAPER
# ============================================================================

class FirstViewScraper:
    def __init__(self):
        self.db = FirstViewDB(Path(CONFIG["storage_root"]) / CONFIG["db_name"])
        self._shutdown = False

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Use robust session if available
        if HAS_ROBUST:
            self.session = create_robust_session(
                retries=5,
                backoff_factor=1.5,
                timeout=(10, 30),
                pool_connections=3,
                pool_maxsize=3,
            )
        else:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        logger.info("Shutdown signal received. Finishing current operation...")
        self._shutdown = True

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page with rate limiting and retries."""
        for attempt in range(CONFIG["max_retries"]):
            if self._shutdown:
                return None
            try:
                time.sleep(CONFIG["rate_limit"])
                resp = self.session.get(url, timeout=CONFIG["timeout"])
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "html.parser")
                elif resp.status_code == 429:
                    wait = (2 ** attempt) * 5
                    logger.warning(f"Rate limited (429), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                elif resp.status_code == 403:
                    wait = (2 ** attempt) * 10
                    logger.warning(f"Forbidden (403), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    logger.warning(f"HTTP {resp.status_code} for {url[:80]}")
                    return None
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout (attempt {attempt+1}) for {url[:80]}")
                time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt+1}): {e}")
                time.sleep(2 ** (attempt + 1))
            except Exception as e:
                logger.error(f"Request error (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)
        return None

    def _get_json(self, url: str) -> Optional[str]:
        """Fetch raw HTML text (for pages that need text parsing, not soup)."""
        for attempt in range(CONFIG["max_retries"]):
            if self._shutdown:
                return None
            try:
                time.sleep(CONFIG["rate_limit"])
                resp = self.session.get(url, timeout=CONFIG["timeout"])
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 429:
                    wait = (2 ** attempt) * 5
                    logger.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                elif resp.status_code == 403:
                    wait = (2 ** attempt) * 10
                    logger.warning(f"Forbidden, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    return None
            except Exception as e:
                logger.warning(f"Request error: {e}")
                time.sleep(2 ** attempt)
        return None

    # ========================================================================
    # COLLECTION DISCOVERY
    # ========================================================================

    def _extract_collections_from_soup(self, soup: BeautifulSoup) -> List[Tuple[int, str]]:
        """Extract (collection_id, title) pairs from a page."""
        found = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "collection_images.php?id=" in href:
                match = re.search(r'id=(\d+)', href)
                if match:
                    coll_id = int(match.group(1))
                    title = link.get_text(strip=True)
                    if not title:
                        parent = link.find_parent()
                        if parent:
                            title = parent.get_text(strip=True)[:100]
                    title = title or f"Collection {coll_id}"
                    found.append((coll_id, title))
        return found

    def _extract_total_pages(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract total page count from '48659 results - 2433 page(s)' text."""
        text = soup.get_text()
        match = re.search(r'(\d+)\s+results?\s*-\s*(\d+)\s+page', text)
        if match:
            return int(match.group(2))
        return None

    def _paginate_browse(self, base_url: str, strategy_key: str) -> int:
        """
        Paginate through browse results with checkpoint/resume.
        Uses zero-based pagination matching the site's actual API.
        Returns count of newly discovered collections.
        """
        total_new = 0
        batch_buffer = []

        # Check checkpoint for resume
        checkpoint = self.db.get_checkpoint(strategy_key)
        if checkpoint and checkpoint[1]:  # completed
            logger.info(f"  [{strategy_key}] Already completed, skipping")
            return 0

        start_page = 0
        if checkpoint:
            start_page = int(checkpoint[0]) + 1
            logger.info(f"  [{strategy_key}] Resuming from page {start_page}")

        # First, get page 0 to find total pages
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page=0"

        if start_page == 0:
            soup = self._get(url)
            if not soup:
                return 0

            total_pages = self._extract_total_pages(soup)
            if total_pages is None:
                total_pages = 100  # conservative fallback

            found = self._extract_collections_from_soup(soup)
            if found:
                batch_buffer.extend(found)
                total_new += self.db.add_discovered_batch(found)

            logger.info(f"  [{strategy_key}] {total_pages} pages to scan, "
                        f"found {len(found)} on page 0")
            start_page = 1
        else:
            # We need total_pages - fetch page 0 just for the count
            soup = self._get(url)
            total_pages = self._extract_total_pages(soup) if soup else 5000

        consecutive_empty = 0

        for page in range(start_page, (total_pages or 5000)):
            if self._shutdown:
                self.db.save_checkpoint(strategy_key, str(page - 1))
                logger.info(f"  [{strategy_key}] Shutdown at page {page}")
                break

            url = f"{base_url}{sep}page={page}"
            soup = self._get(url)

            if not soup:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    logger.info(f"  [{strategy_key}] 5 consecutive failures, stopping")
                    break
                continue

            found = self._extract_collections_from_soup(soup)

            if not found:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    logger.info(f"  [{strategy_key}] 5 consecutive empty pages, stopping")
                    break
            else:
                consecutive_empty = 0
                new = self.db.add_discovered_batch(found)
                total_new += new

            # Checkpoint every 50 pages
            if page % 50 == 0:
                self.db.save_checkpoint(strategy_key, str(page))
                logger.info(f"  [{strategy_key}] Page {page}/{total_pages}, "
                            f"+{total_new} new collections")

        # Mark strategy complete
        if not self._shutdown:
            self.db.save_checkpoint(strategy_key, str(total_pages or 0), completed=True)
            logger.info(f"  [{strategy_key}] Complete. +{total_new} new collections")

        return total_new

    def discover_collections(self) -> int:
        """
        Discover all collection IDs from the site.
        Uses checkpoints so it can resume after crashes.
        Returns total count of newly discovered collections.
        """
        total_new = 0

        # ==================================================================
        # STRATEGY 1: Browse Women by date (the biggest set: ~48K results)
        # ==================================================================
        logger.info("=== Strategy 1: Browse Women by date ===")
        base = f"{CONFIG['base_url']}/collection_results.php?s_g=Women&b=date&clear=1"
        total_new += self._paginate_browse(base, "women_by_date")

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 2: Browse Men by date (~6.6K results)
        # ==================================================================
        logger.info("=== Strategy 2: Browse Men by date ===")
        base = f"{CONFIG['base_url']}/collection_results.php?s_g=Men&b=date&clear=1"
        total_new += self._paginate_browse(base, "men_by_date")

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 3: Browse by year + season + gender (catch stragglers)
        # ==================================================================
        logger.info("=== Strategy 3: Year/Season/Gender combinations ===")
        checkpoint = self.db.get_checkpoint("year_season_combos")
        if checkpoint and checkpoint[1]:
            logger.info("  Already completed, skipping")
        else:
            resume_from = checkpoint[0] if checkpoint else None
            started = resume_from is None

            for year in FILTER_YEARS:
                for season in FILTER_SEASONS:
                    for gender in ["Women", "Men"]:
                        key = f"{year}_{season}_{gender}"
                        if not started:
                            if key == resume_from:
                                started = True
                            continue

                        if self._shutdown:
                            self.db.save_checkpoint("year_season_combos", key)
                            return total_new

                        season_enc = quote_plus(season)
                        url = (f"{CONFIG['base_url']}/collection_results.php?"
                               f"s_g={gender}&filter_year={year}"
                               f"&filter_season={season_enc}")
                        soup = self._get(url)
                        if soup:
                            found = self._extract_collections_from_soup(soup)
                            if found:
                                new = self.db.add_discovered_batch(found)
                                total_new += new
                                # If there are multiple pages, paginate them
                                total_pages = self._extract_total_pages(soup)
                                if total_pages and total_pages > 1:
                                    total_new += self._paginate_browse(
                                        url, f"ys_{year}_{season}_{gender}"
                                    )

                self.db.save_checkpoint("year_season_combos", f"{year}_last_Women")
                if year % 5 == 0:
                    discovered = len(self.db.get_discovered_ids())
                    logger.info(f"  Year {year} done. Total discovered: {discovered}")

            if not self._shutdown:
                self.db.save_checkpoint("year_season_combos", "done", completed=True)

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 4: Browse by city + gender (catch city-specific shows)
        # ==================================================================
        logger.info("=== Strategy 4: By City ===")
        checkpoint = self.db.get_checkpoint("city_browse")
        if checkpoint and checkpoint[1]:
            logger.info("  Already completed, skipping")
        else:
            resume_from = checkpoint[0] if checkpoint else None
            started = resume_from is None

            for city in FILTER_CITIES:
                for gender in ["Women", "Men"]:
                    key = f"{city}_{gender}"
                    if not started:
                        if key == resume_from:
                            started = True
                        continue

                    if self._shutdown:
                        self.db.save_checkpoint("city_browse", key)
                        return total_new

                    url = (f"{CONFIG['base_url']}/collection_results.php?"
                           f"s_g={gender}&s_p={city}")
                    soup = self._get(url)
                    if soup:
                        found = self._extract_collections_from_soup(soup)
                        if found:
                            new = self.db.add_discovered_batch(found)
                            total_new += new
                            total_pages = self._extract_total_pages(soup)
                            if total_pages and total_pages > 1:
                                total_new += self._paginate_browse(
                                    url, f"city_{city}_{gender}"
                                )

                    self.db.save_checkpoint("city_browse", key)

            if not self._shutdown:
                self.db.save_checkpoint("city_browse", "done", completed=True)

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 5: Browse by collection type (Runway, Backstage, etc.)
        # ==================================================================
        logger.info("=== Strategy 5: By Collection Type ===")
        checkpoint = self.db.get_checkpoint("type_browse")
        if checkpoint and checkpoint[1]:
            logger.info("  Already completed, skipping")
        else:
            for ctype in COLLECTION_TYPES:
                for gender in ["Women", "Men"]:
                    if self._shutdown:
                        self.db.save_checkpoint("type_browse", f"{ctype}_{gender}")
                        return total_new

                    ctype_enc = quote_plus(ctype)
                    url = (f"{CONFIG['base_url']}/collection_results.php?"
                           f"s_g={gender}&s_t={ctype_enc}")
                    total_new += self._paginate_browse(
                        url, f"type_{ctype}_{gender}"
                    )

            if not self._shutdown:
                self.db.save_checkpoint("type_browse", "done", completed=True)

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 6: Designer A-Z directory
        # ==================================================================
        logger.info("=== Strategy 6: Designer Directory A-Z ===")
        checkpoint = self.db.get_checkpoint("designer_az")
        if checkpoint and checkpoint[1]:
            logger.info("  Already completed, skipping")
        else:
            resume_from = checkpoint[0] if checkpoint else None
            started = resume_from is None

            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
                if not started:
                    if letter == resume_from:
                        started = True
                    continue

                if self._shutdown:
                    self.db.save_checkpoint("designer_az", letter)
                    return total_new

                url = f"{CONFIG['base_url']}/alpha_list.php?type=designer&l={letter}"
                soup = self._get(url)
                if not soup:
                    continue

                # Extract collections directly from this page
                found = self._extract_collections_from_soup(soup)
                if found:
                    self.db.add_discovered_batch(found)
                    total_new += len(found)

                # Follow designer-specific links to get all their shows
                designer_links = []
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if ("designer_results.php" in href or
                            "collection_list.php" in href):
                        designer_links.append(urljoin(CONFIG['base_url'], href))

                for durl in designer_links:
                    if self._shutdown:
                        break
                    dsoup = self._get(durl)
                    if dsoup:
                        found = self._extract_collections_from_soup(dsoup)
                        if found:
                            new = self.db.add_discovered_batch(found)
                            total_new += new

                self.db.save_checkpoint("designer_az", letter)
                logger.info(f"  Letter {letter}: total discovered = "
                            f"{len(self.db.get_discovered_ids())}")

            if not self._shutdown:
                self.db.save_checkpoint("designer_az", "done", completed=True)

        if self._shutdown:
            return total_new

        # ==================================================================
        # STRATEGY 7: Sequential ID scan to fill gaps
        # ==================================================================
        logger.info("=== Strategy 7: Sequential ID Gap Scan ===")
        checkpoint = self.db.get_checkpoint("id_scan")
        if checkpoint and checkpoint[1]:
            logger.info("  Already completed, skipping")
        else:
            known_ids = self.db.get_discovered_ids()
            if known_ids:
                max_id = max(known_ids)
                # Scan from 1 to max_id+500, but skip known IDs
                # Sample every 50th to find valid ranges first
                resume_id = int(checkpoint[0]) if checkpoint else 0

                logger.info(f"  Scanning IDs 1 to {max_id + 500} "
                            f"(sampling every 50th, resume from {resume_id})")
                scan_found = 0

                for test_id in range(max(1, resume_id), max_id + 500, 50):
                    if self._shutdown:
                        self.db.save_checkpoint("id_scan", str(test_id))
                        return total_new

                    if test_id in known_ids:
                        continue

                    url = f"{CONFIG['base_url']}/collection_images.php?id={test_id}"
                    soup = self._get(url)
                    if soup:
                        # Valid collection pages have runway images
                        imgs = soup.find_all("img", src=re.compile(r'/files/\d+/'))
                        if imgs:
                            header = soup.find("h1") or soup.find("h2")
                            title = header.get_text(strip=True)[:100] if header else f"Collection {test_id}"
                            self.db.add_discovered(test_id, title)
                            scan_found += 1
                            total_new += 1

                    if test_id % 1000 == 0:
                        self.db.save_checkpoint("id_scan", str(test_id))
                        logger.info(f"  ID scan at {test_id}, found {scan_found} new")

                if not self._shutdown:
                    self.db.save_checkpoint("id_scan", "done", completed=True)
                    logger.info(f"  ID scan complete. Found {scan_found} new collections")

        discovered = len(self.db.get_discovered_ids())
        logger.info(f"=== DISCOVERY COMPLETE: {discovered} total collections ===")
        return total_new

    # ========================================================================
    # COLLECTION INDEXING (photo extraction)
    # ========================================================================

    def _parse_collection_metadata(self, soup: BeautifulSoup, title: str = "") -> Dict:
        """Extract designer, season, city, show_type from a collection page."""
        designer = ""
        season = ""
        city = ""
        show_type = "RTW"

        # The page header usually contains "DESIGNER - TYPE SEASON CITY"
        header = soup.find("h1") or soup.find("h2")
        header_text = ""
        if header:
            header_text = header.get_text(strip=True)

        # Use title from discovery if header is empty
        parse_text = header_text or title or ""

        # Extract season code (e.g., SS26, FW25)
        for code in SEASON_CODES:
            if code in parse_text:
                season = code
                break

        # If no short code, look for full labels
        if not season:
            for label in SEASON_LABELS:
                if label.lower() in parse_text.lower():
                    # Try to find year nearby
                    year_match = re.search(r'20(\d{2})', parse_text)
                    if year_match:
                        yr = year_match.group(1)
                        if "spring" in label.lower() or "summer" in label.lower():
                            season = f"SS{yr}"
                        elif "fall" in label.lower() or "winter" in label.lower() or "autumn" in label.lower():
                            season = f"FW{yr}"
                        elif "pre-fall" in label.lower() or "prefall" in label.lower():
                            season = f"PF{yr}"
                        elif "cruise" in label.lower() or "resort" in label.lower():
                            season = f"CR{yr}"
                        else:
                            season = f"{label} {year_match.group(0)}"
                    else:
                        season = label
                    break

        # Extract city
        for c in CITIES:
            if c.lower() in parse_text.lower():
                city = c
                break

        # Determine show type
        page_text = str(soup)[:5000].lower()
        if "couture" in parse_text.lower() or "couture" in page_text:
            show_type = "Couture"
        elif "menswear" in parse_text.lower() or "men" in page_text[:500]:
            show_type = "Menswear"

        # Designer: typically everything before the " - " separator
        if " - " in parse_text:
            designer = parse_text.split(" - ")[0].strip()
        elif parse_text:
            # Take up to the first recognized keyword
            designer = parse_text
            for marker in SEASON_CODES + SEASON_LABELS + ["RTW", "Couture", "Menswear"]:
                if marker in designer:
                    designer = designer.split(marker)[0].strip()
                    break
        else:
            designer = title.split(" - ")[0].strip() if " - " in title else title

        designer = designer.strip(" -,") or f"Unknown_{hash(title) % 10000}"

        return {
            "designer": designer,
            "season": season,
            "city": city,
            "show_type": show_type,
            "header_text": header_text,
        }

    def _extract_total_photos_from_collection(self, soup: BeautifulSoup) -> int:
        """Extract total photo count from collection page (e.g., '169 pictures')."""
        text = soup.get_text()
        match = re.search(r'(\d+)\s+pictures?', text)
        if match:
            return int(match.group(1))
        # Also check for maxPage in the JavaScript
        script_text = str(soup)
        match = re.search(r'maxPage:\s*(\d+)', script_text)
        if match:
            return (int(match.group(1)) + 1) * 20  # rough estimate
        return 0

    def _extract_max_page_from_collection(self, soup: BeautifulSoup) -> int:
        """Extract maxPage from the collection's JavaScript (for infinite scroll)."""
        script_text = str(soup)
        match = re.search(r'maxPage:\s*(\d+)', script_text)
        if match:
            return int(match.group(1))
        return 0

    def _extract_photos_from_soup(self, soup: BeautifulSoup, collection_id: int,
                                   meta: Dict, start_look: int = 1) -> List[Photo]:
        """Extract photo records from a collection page or next-page fragment."""
        photos = []
        look_number = start_look

        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue

            # Only process collection photos (they're in /files/ID/ paths)
            if f"/files/{collection_id}/" not in src and "/files/" not in src:
                # Also check for common thumb patterns
                if "thumb_" not in src:
                    continue

            # Skip navigation/UI images
            if any(x in src.lower() for x in [
                "logo", "icon", "nav", "button", "banner", "ad_",
                "social", "facebook", "twitter", "instagram",
                "sprite", "pixel", "spacer",
            ]):
                continue

            # Convert thumbnail to full size URL
            if "thumb_" in src:
                full_url = src.replace("thumb_", "")
            else:
                full_url = src

            # Make absolute URL
            if not full_url.startswith("http"):
                full_url = urljoin(CONFIG["base_url"], full_url)
            if not src.startswith("http"):
                src = urljoin(CONFIG["base_url"], src)

            # Generate deterministic photo ID from the full URL
            photo_id = hashlib.md5(full_url.encode()).hexdigest()[:12]

            # Extract any credits from nearby text
            credits = {}
            parent = img.find_parent()
            if parent:
                text = parent.get_text()
                for credit_type in ["Photo", "Photographer", "Stylist", "Hair", "Makeup"]:
                    if f"{credit_type}:" in text:
                        val = text.split(f"{credit_type}:")[-1].split("\n")[0].strip()
                        credits[credit_type.lower()] = val[:100]

            photo = Photo(
                id=photo_id,
                collection_id=collection_id,
                look_number=look_number,
                image_url=full_url,
                thumb_url=src,
                designer=meta["designer"],
                season=meta["season"],
                city=meta["city"],
                credits=credits,
                tags=[meta["show_type"], meta["season"], meta["city"], meta["designer"]],
                downloaded=False,
                local_path=None,
            )
            photos.append(photo)
            look_number += 1

        return photos

    def index_collection(self, collection_id: int, title: str = "") -> int:
        """
        Index ALL photos in a collection, including infinite-scroll pages.
        The site uses collection_images_nextpage.php?id=X&page=Y for pagination.
        """
        url = f"{CONFIG['base_url']}/collection_images.php?id={collection_id}"
        soup = self._get(url)

        if not soup:
            return 0

        # Parse metadata
        meta = self._parse_collection_metadata(soup, title)
        total_photos_reported = self._extract_total_photos_from_collection(soup)
        max_page = self._extract_max_page_from_collection(soup)

        # Extract photos from page 0
        all_photos = self._extract_photos_from_soup(soup, collection_id, meta, start_look=1)

        # Fetch additional pages (infinite scroll pages)
        if max_page > 0:
            for page_num in range(1, max_page + 1):
                if self._shutdown:
                    break

                next_url = (f"{CONFIG['base_url']}/collection_images_nextpage.php?"
                            f"id={collection_id}&page={page_num}")
                next_soup = self._get(next_url)
                if next_soup:
                    page_photos = self._extract_photos_from_soup(
                        next_soup, collection_id, meta,
                        start_look=len(all_photos) + 1
                    )
                    all_photos.extend(page_photos)
                else:
                    # If a page fails, try a couple more before giving up
                    pass

        # Batch insert all photos
        inserted = self.db.add_photos_batch(all_photos)

        # Save collection record
        collection = Collection(
            id=collection_id,
            designer=meta["designer"],
            season=meta["season"],
            city=meta["city"],
            show_type=meta["show_type"],
            url=url,
            photo_count=inserted,
            total_photos=total_photos_reported,
            indexed_at=datetime.now().isoformat(),
            fully_indexed=not self._shutdown,
        )
        self.db.add_collection(collection)

        return inserted

    def index_all(self, fresh: bool = False) -> Dict[str, int]:
        """
        Index all discoverable collections with full resume support.
        Phase 1: Discover collection IDs
        Phase 2: Index photos for each collection
        """
        if fresh:
            logger.info("FRESH RUN: Clearing all checkpoints")
            self.db.clear_checkpoints()

        # Phase 1: Discovery
        logger.info("=" * 60)
        logger.info("PHASE 1: DISCOVERING COLLECTIONS")
        logger.info("=" * 60)
        new_discovered = self.discover_collections()
        logger.info(f"Newly discovered: {new_discovered}")

        if self._shutdown:
            return {"discovered": new_discovered, "collections": 0, "photos": 0}

        # Phase 2: Index photos for unindexed collections
        logger.info("=" * 60)
        logger.info("PHASE 2: INDEXING COLLECTION PHOTOS")
        logger.info("=" * 60)

        unindexed = self.db.get_unindexed_collections()
        logger.info(f"{len(unindexed)} collections need photo indexing")

        results = {"discovered": new_discovered, "collections": 0, "photos": 0}

        for i, (coll_id, title) in enumerate(unindexed):
            if self._shutdown:
                logger.info(f"Shutdown at collection {i}/{len(unindexed)}")
                break

            photos = self.index_collection(coll_id, title)
            if photos > 0:
                results["collections"] += 1
                results["photos"] += photos

            if (i + 1) % 25 == 0:
                logger.info(
                    f"  Progress: {i+1}/{len(unindexed)} collections, "
                    f"{results['photos']} photos indexed"
                )

        return results

    def download_photos(self, limit: int = 1000):
        """Download pending photos."""
        storage = Path(CONFIG["storage_root"]) / "photos"
        storage.mkdir(parents=True, exist_ok=True)

        pending = self.db.get_pending_photos(limit)
        logger.info(f"Downloading {len(pending)} photos...")

        downloaded = 0
        for photo in pending:
            if self._shutdown:
                break
            try:
                # Create path: designer/season/photo.jpg
                designer_safe = re.sub(r'[^\w\-]', '_', photo["designer"])[:50]
                season = photo["season"] or "unknown"

                photo_dir = storage / designer_safe / season
                photo_dir.mkdir(parents=True, exist_ok=True)

                filename = f"look_{photo['look_number']:03d}_{photo['id']}.jpg"
                local_path = photo_dir / filename

                if local_path.exists():
                    self.db.mark_downloaded(photo["id"], str(local_path))
                    downloaded += 1
                    continue

                # Download with retry
                time.sleep(CONFIG["rate_limit"])

                success = False
                for attempt in range(CONFIG["max_retries"]):
                    try:
                        resp = self.session.get(photo["image_url"], timeout=(10, 60))
                        if resp.status_code == 200:
                            local_path.write_bytes(resp.content)
                            self.db.mark_downloaded(photo["id"], str(local_path))
                            downloaded += 1
                            success = True
                            break
                        elif resp.status_code == 429:
                            wait = (2 ** attempt) * 5
                            logger.warning(f"Rate limited, waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            logger.warning(f"HTTP {resp.status_code} for {photo['id']}")
                            break
                    except Exception as e:
                        if attempt < CONFIG["max_retries"] - 1:
                            wait = 2 ** attempt
                            logger.warning(f"Retry {attempt+1}: {e}")
                            time.sleep(wait)
                        else:
                            logger.error(f"Failed after retries: {photo['id']}: {e}")

                if success and downloaded % 50 == 0:
                    logger.info(f"  Downloaded {downloaded}/{len(pending)}")

            except Exception as e:
                logger.error(f"Error downloading {photo['id']}: {e}")

        logger.info(f"Downloaded {downloaded} photos")
        return downloaded

    def export_metadata(self, output_path: Path):
        """Export photo metadata for training."""
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM photos WHERE downloaded = 1")

        count = 0
        with open(output_path, "w") as f:
            for row in cur.fetchall():
                record = {
                    "image_path": row["local_path"],
                    "designer": row["designer"],
                    "season": row["season"],
                    "city": row["city"],
                    "look_number": row["look_number"],
                    "credits": json.loads(row["credits"]) if row["credits"] else {},
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "caption": f"{row['designer']} {row['season']} Look {row['look_number']}"
                }
                f.write(json.dumps(record) + "\n")
                count += 1

        conn.close()
        logger.info(f"Exported {count} records to {output_path}")


# ============================================================================
# CLI
# ============================================================================

def main():
    global logger
    logger = setup_logging()

    parser = argparse.ArgumentParser(description="FirstVIEW Fashion Photo Scraper v2.0")
    parser.add_argument("command", choices=["index", "download", "stats", "export"])
    parser.add_argument("--limit", type=int, default=1000, help="Max items to process")
    parser.add_argument("--output", type=str, help="Output path for export")
    parser.add_argument("--fresh", action="store_true",
                        help="Wipe checkpoints and start fresh (index command)")
    args = parser.parse_args()

    scraper = FirstViewScraper()

    if args.command == "index":
        results = scraper.index_all(fresh=args.fresh)
        print(f"\nDiscovered {results['discovered']} new collections")
        print(f"Indexed {results['collections']} collections, {results['photos']} photos")
        stats = scraper.db.get_stats()
        print(f"Total in database: {stats['total_photos']} photos across "
              f"{stats['indexed_collections']} collections")

    elif args.command == "download":
        downloaded = scraper.download_photos(args.limit)
        print(f"\nDownloaded {downloaded} photos")

    elif args.command == "stats":
        stats = scraper.db.get_stats()
        print("\n" + "=" * 60)
        print("  FIRSTVIEW ARCHIVE STATISTICS")
        print("=" * 60)
        print(f"\nDiscovered collections: {stats['discovered_collections']}")
        print(f"Indexed collections:   {stats['indexed_collections']}")
        print(f"Fully indexed:         {stats['fully_indexed']}")
        print(f"Total photos indexed:  {stats['total_photos']}")
        print(f"Downloaded:            {stats['downloaded']}")
        print(f"Pending download:      {stats['pending']}")

        if stats.get("checkpoints"):
            print("\nDiscovery Checkpoints:")
            for strategy, completed in stats["checkpoints"].items():
                status = "DONE" if completed else "IN PROGRESS"
                print(f"  {strategy}: {status}")

        if stats.get("by_season"):
            print("\nBy Season (top 15):")
            for season, count in list(stats["by_season"].items())[:15]:
                print(f"  {season}: {count:,}")

        if stats.get("by_city"):
            print("\nBy City:")
            for city, count in stats["by_city"].items():
                print(f"  {city}: {count:,}")

        if stats.get("top_designers"):
            print("\nTop Designers:")
            for designer, count in list(stats["top_designers"].items())[:15]:
                print(f"  {designer}: {count:,}")

    elif args.command == "export":
        output = Path(args.output) if args.output else Path(CONFIG["storage_root"]) / "metadata.jsonl"
        scraper.export_metadata(output)


if __name__ == "__main__":
    main()
