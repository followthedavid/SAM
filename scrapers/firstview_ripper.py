#!/usr/bin/env python3
"""
FirstVIEW Fashion Photo Scraper

Collects runway fashion photos with rich metadata:
- Designer/brand
- Season (SS26, FW25, etc.)
- City (Paris, Milan, London, NYC)
- Look numbers
- Credits (photographer, stylist, etc.)

Usage:
    python firstview_ripper.py index          # Index all collections
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
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse, parse_qs

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
    "rate_limit": 1.0,  # seconds between requests
    "timeout": 30,
    "max_retries": 3,
}

# Season patterns - ALL YEARS from 1990 to 2026
SEASONS = []
for year in range(26, 89, -1):  # 2026 down to 1990
    yr = str(year).zfill(2)
    SEASONS.extend([f"SS{yr}", f"FW{yr}"])
# Also add alternate formats seen in archives
SEASONS.extend([
    "Spring", "Fall", "Autumn", "Winter", "Summer",
    "Resort", "Cruise", "Pre-Fall", "Pre-Spring",
    "Couture", "Haute Couture", "RTW", "Ready-to-Wear",
])

CITIES = ["Paris", "Milan", "London", "New York", "Tokyo", "Berlin"]

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
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
    indexed_at: str

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

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
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
                indexed_at TEXT
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

        conn.commit()
        conn.close()

    def add_collection(self, collection: Collection) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO collections
                (id, designer, season, city, show_type, url, photo_count, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                collection.id, collection.designer, collection.season,
                collection.city, collection.show_type, collection.url,
                collection.photo_count, collection.indexed_at
            ))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def add_photo(self, photo: Photo) -> bool:
        conn = sqlite3.connect(self.db_path)
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

    def mark_downloaded(self, photo_id: str, local_path: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            UPDATE photos SET downloaded = 1, local_path = ?
            WHERE id = ?
        """, (local_path, photo_id))
        conn.commit()
        conn.close()

    def get_pending_photos(self, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM photos WHERE downloaded = 0 LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        cur.execute("SELECT COUNT(*) FROM collections")
        stats["total_collections"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos")
        stats["total_photos"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos WHERE downloaded = 1")
        stats["downloaded"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM photos WHERE downloaded = 0")
        stats["pending"] = cur.fetchone()[0]

        # By season
        cur.execute("""
            SELECT season, COUNT(*) FROM photos GROUP BY season ORDER BY season DESC
        """)
        stats["by_season"] = dict(cur.fetchall())

        # By city
        cur.execute("""
            SELECT city, COUNT(*) FROM photos GROUP BY city ORDER BY COUNT(*) DESC
        """)
        stats["by_city"] = dict(cur.fetchall())

        # Top designers
        cur.execute("""
            SELECT designer, COUNT(*) FROM photos
            GROUP BY designer ORDER BY COUNT(*) DESC LIMIT 20
        """)
        stats["top_designers"] = dict(cur.fetchall())

        conn.close()
        return stats


# ============================================================================
# SCRAPER
# ============================================================================

class FirstViewScraper:
    def __init__(self):
        self.db = FirstViewDB(Path(CONFIG["storage_root"]) / CONFIG["db_name"])

        # Use robust session if available
        if HAS_ROBUST:
            self.session = create_robust_session(
                retries=3,
                backoff_factor=1.0,
                timeout=(10, 30),
                pool_connections=3,
                pool_maxsize=3,
            )
        else:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
            })

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page with rate limiting and retries."""
        for attempt in range(CONFIG["max_retries"]):
            try:
                time.sleep(CONFIG["rate_limit"])
                resp = self.session.get(url, timeout=CONFIG["timeout"])
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "html.parser")
                logger.warning(f"HTTP {resp.status_code} for {url}")
            except Exception as e:
                logger.error(f"Request error: {e}")
                time.sleep(2 ** attempt)
        return None

    def _extract_collections_from_soup(self, soup: BeautifulSoup, collections: set) -> int:
        """Extract collection IDs from a page and add to set. Returns count of new collections."""
        initial_count = len(collections)
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
                    collections.add((coll_id, title))
        return len(collections) - initial_count

    def _paginate_browse(self, base_url: str, collections: set, max_pages: int = 500):
        """Paginate through browse results until no more collections found."""
        page = 1
        consecutive_empty = 0

        while page <= max_pages and consecutive_empty < 3:
            # Try different pagination patterns
            if "?" in base_url:
                url = f"{base_url}&page={page}"
            else:
                url = f"{base_url}?page={page}"

            logger.info(f"  Page {page}: {url[:80]}...")
            soup = self._get(url)
            if not soup:
                consecutive_empty += 1
                page += 1
                continue

            new_count = self._extract_collections_from_soup(soup, collections)

            if new_count == 0:
                consecutive_empty += 1
            else:
                consecutive_empty = 0
                logger.info(f"    Found {new_count} new, total: {len(collections)}")

            page += 1

        return len(collections)

    def discover_collections(self) -> List[Tuple[int, str]]:
        """Discover all collection IDs from the site with full pagination."""
        collections = set()

        # =====================================================================
        # STRATEGY 1: Browse by Gender with pagination
        # =====================================================================
        logger.info("=== Strategy 1: Browse by Gender ===")
        genders = ["Women", "Men"]
        sort_methods = ["date", "alpha"]

        for gender in genders:
            for sort_by in sort_methods:
                base_url = f"{CONFIG['base_url']}/collection_results.php?s_g={gender}&b={sort_by}&clear=1"
                logger.info(f"Scanning {gender} by {sort_by}...")
                self._paginate_browse(base_url, collections)

        logger.info(f"After gender browse: {len(collections)} collections")

        # =====================================================================
        # STRATEGY 2: Browse by Season
        # =====================================================================
        logger.info("=== Strategy 2: Browse by Season ===")
        # Expand seasons to cover ALL years - back to 1900 for historical archives
        seasons_full = []
        for year in range(2026, 1899, -1):  # Go back to 1900!
            seasons_full.append(f"Spring / Summer {year}")
            seasons_full.append(f"Fall / Winter {year}")
            seasons_full.append(f"Spring {year}")
            seasons_full.append(f"Fall {year}")
            seasons_full.append(f"Autumn / Winter {year}")
            seasons_full.append(f"Resort {year}")
            seasons_full.append(f"Pre-Fall {year}")
            seasons_full.append(f"Cruise {year}")
            seasons_full.append(f"Couture Spring {year}")
            seasons_full.append(f"Couture Fall {year}")
            seasons_full.append(f"Haute Couture {year}")
            # Also try just the year
            seasons_full.append(str(year))

        for season in seasons_full:
            # URL encode the season
            season_encoded = season.replace(" ", "+").replace("/", "%2F")
            for gender in genders:
                url = f"{CONFIG['base_url']}/collection_results.php?s_g={gender}&s_s={season_encoded}"
                soup = self._get(url)
                if soup:
                    new = self._extract_collections_from_soup(soup, collections)
                    if new > 0:
                        logger.info(f"  {season} {gender}: +{new} (total: {len(collections)})")

        logger.info(f"After season browse: {len(collections)} collections")

        # =====================================================================
        # STRATEGY 3: Browse by City
        # =====================================================================
        logger.info("=== Strategy 3: Browse by City ===")
        cities_extended = [
            "Paris", "Milan", "London", "New York", "Tokyo", "Berlin",
            "Florence", "Los Angeles", "Shanghai", "Sydney", "Copenhagen",
            "Stockholm", "Moscow", "Seoul", "Mumbai", "Sao Paulo"
        ]

        for city in cities_extended:
            city_encoded = city.replace(" ", "+")
            for gender in genders:
                url = f"{CONFIG['base_url']}/collection_results.php?s_g={gender}&s_c={city_encoded}"
                soup = self._get(url)
                if soup:
                    new = self._extract_collections_from_soup(soup, collections)
                    if new > 0:
                        logger.info(f"  {city} {gender}: +{new} (total: {len(collections)})")

        logger.info(f"After city browse: {len(collections)} collections")

        # =====================================================================
        # STRATEGY 4: Designer Directory (A-Z)
        # =====================================================================
        logger.info("=== Strategy 4: Designer Directory A-Z ===")
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0":
            url = f"{CONFIG['base_url']}/alpha_list.php?type=designer&l={letter}"
            soup = self._get(url)
            if soup:
                new = self._extract_collections_from_soup(soup, collections)
                if new > 0:
                    logger.info(f"  Letter {letter}: +{new} (total: {len(collections)})")

                # Also look for designer-specific links to get all their shows
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "designer_results.php" in href or "collection_list.php" in href:
                        designer_url = urljoin(CONFIG['base_url'], href)
                        designer_soup = self._get(designer_url)
                        if designer_soup:
                            self._extract_collections_from_soup(designer_soup, collections)

        logger.info(f"After designer directory: {len(collections)} collections")

        # =====================================================================
        # STRATEGY 5: Season Directory (discover ALL seasons from site)
        # =====================================================================
        logger.info("=== Strategy 5: Season Directory ===")
        season_list_url = f"{CONFIG['base_url']}/alpha_list.php?type=season"
        soup = self._get(season_list_url)
        if soup:
            # Extract all season links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "collection_results.php" in href and "s_s=" in href:
                    season_url = urljoin(CONFIG['base_url'], href)
                    season_soup = self._get(season_url)
                    if season_soup:
                        new = self._extract_collections_from_soup(season_soup, collections)
                        if new > 0:
                            season_text = link.get_text(strip=True)[:30]
                            logger.info(f"  {season_text}: +{new} (total: {len(collections)})")
                            # Paginate this season
                            self._paginate_browse(season_url, collections, max_pages=100)

        logger.info(f"After season directory: {len(collections)} collections")

        # =====================================================================
        # STRATEGY 6: Sequential ID scan for gaps
        # =====================================================================
        if len(collections) > 0:
            logger.info("=== Strategy 5: Sequential ID Scan ===")
            # Find the range of IDs we have
            ids = [c[0] for c in collections]
            min_id = min(ids)
            max_id = max(ids)

            # Scan a range around known IDs (they're sequential on the site)
            # Current max we saw is around 57000, so scan back
            scan_start = max(1, min_id - 1000)
            scan_end = max_id + 100

            # Sample every 100th ID to find valid ranges
            logger.info(f"  Sampling ID range {scan_start} to {scan_end}...")
            sampled = 0
            for test_id in range(scan_start, scan_end, 100):
                if test_id not in [c[0] for c in collections]:
                    url = f"{CONFIG['base_url']}/collection_images.php?id={test_id}"
                    soup = self._get(url)
                    if soup:
                        # Check if it's a valid collection page
                        if soup.find("img") and "collection" in str(soup).lower():
                            header = soup.find("h1") or soup.find("h2")
                            title = header.get_text(strip=True)[:100] if header else f"Collection {test_id}"
                            collections.add((test_id, title))
                            sampled += 1
                            logger.info(f"    Found ID {test_id}: {title[:50]}")

            logger.info(f"  Sequential scan found {sampled} additional collections")

        logger.info(f"=== TOTAL: {len(collections)} unique collections discovered ===")
        return list(collections)

    def index_collection(self, collection_id: int, title: str = "") -> int:
        """Index all photos in a collection."""
        url = f"{CONFIG['base_url']}/collection_images.php?id={collection_id}"
        soup = self._get(url)

        if not soup:
            return 0

        # Extract collection metadata
        designer = ""
        season = ""
        city = ""
        show_type = "RTW"

        # Parse title/header for metadata
        header = soup.find("h1") or soup.find("h2")
        if header:
            header_text = header.get_text(strip=True)
            # Try to extract designer, season, city from header
            for s in SEASONS:
                if s in header_text:
                    season = s
                    break
            for c in CITIES:
                if c.lower() in header_text.lower():
                    city = c
                    break
            # Designer is usually the first part
            designer = title or header_text.split()[0] if header_text else f"Unknown_{collection_id}"

        if "Couture" in str(soup):
            show_type = "Couture"
        elif "Menswear" in str(soup) or "Men" in str(soup):
            show_type = "Menswear"

        # Find all images
        photos_indexed = 0
        look_number = 1

        # Look for image patterns
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue

            # Skip navigation/UI images
            if any(x in src.lower() for x in ["logo", "icon", "nav", "button"]):
                continue

            # Convert thumbnail to full size
            if "thumb_" in src:
                full_url = src.replace("thumb_", "")
            else:
                full_url = src

            # Make absolute URL
            if not full_url.startswith("http"):
                full_url = urljoin(CONFIG["base_url"], full_url)
                src = urljoin(CONFIG["base_url"], src)

            # Generate photo ID
            photo_id = hashlib.md5(full_url.encode()).hexdigest()[:12]

            # Extract any credits from nearby text
            credits = {}
            parent = img.find_parent()
            if parent:
                text = parent.get_text()
                if "Photo:" in text:
                    credits["photographer"] = text.split("Photo:")[-1].split("\n")[0].strip()
                if "Stylist:" in text:
                    credits["stylist"] = text.split("Stylist:")[-1].split("\n")[0].strip()

            photo = Photo(
                id=photo_id,
                collection_id=collection_id,
                look_number=look_number,
                image_url=full_url,
                thumb_url=src,
                designer=designer,
                season=season,
                city=city,
                credits=credits,
                tags=[show_type, season, city, designer],
                downloaded=False,
                local_path=None
            )

            if self.db.add_photo(photo):
                photos_indexed += 1
                look_number += 1

        # Save collection
        collection = Collection(
            id=collection_id,
            designer=designer,
            season=season,
            city=city,
            show_type=show_type,
            url=url,
            photo_count=photos_indexed,
            indexed_at=datetime.now().isoformat()
        )
        self.db.add_collection(collection)

        return photos_indexed

    def index_all(self) -> Dict[str, int]:
        """Index all discoverable collections."""
        logger.info("Discovering collections...")
        collections = self.discover_collections()
        logger.info(f"Found {len(collections)} collections")

        results = {"collections": 0, "photos": 0}

        for i, (coll_id, title) in enumerate(collections):
            logger.info(f"[{i+1}/{len(collections)}] Indexing {title} (ID: {coll_id})...")
            photos = self.index_collection(coll_id, title)
            if photos > 0:
                results["collections"] += 1
                results["photos"] += photos
                logger.info(f"  → {photos} photos indexed")

        return results

    def download_photos(self, limit: int = 1000):
        """Download pending photos."""
        storage = Path(CONFIG["storage_root"]) / "photos"
        storage.mkdir(parents=True, exist_ok=True)

        pending = self.db.get_pending_photos(limit)
        logger.info(f"Downloading {len(pending)} photos...")

        downloaded = 0
        for photo in pending:
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
                        elif resp.status_code == 429:  # Rate limited
                            wait = (2 ** attempt) * 5
                            logger.warning(f"Rate limited, waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            logger.warning(f"HTTP {resp.status_code} for {photo['id']}")
                            break
                    except Exception as e:
                        if attempt < CONFIG["max_retries"] - 1:
                            wait = 2 ** attempt
                            logger.warning(f"Retry {attempt+1}/{CONFIG['max_retries']}: {e}")
                            time.sleep(wait)
                        else:
                            logger.error(f"Failed after retries: {photo['id']}: {e}")

                if success and downloaded % 50 == 0:
                    logger.info(f"  Downloaded {downloaded}/{len(pending)}")

                if not success:
                    logger.warning(f"HTTP {resp.status_code} for {photo['image_url']}")

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

        conn.close()
        logger.info(f"Exported metadata to {output_path}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="FirstVIEW Fashion Photo Scraper")
    parser.add_argument("command", choices=["index", "download", "stats", "export"])
    parser.add_argument("--limit", type=int, default=1000, help="Max items to process")
    parser.add_argument("--output", type=str, help="Output path for export")
    args = parser.parse_args()

    scraper = FirstViewScraper()

    if args.command == "index":
        results = scraper.index_all()
        print(f"\nIndexed {results['collections']} collections, {results['photos']} photos")

    elif args.command == "download":
        downloaded = scraper.download_photos(args.limit)
        print(f"\nDownloaded {downloaded} photos")

    elif args.command == "stats":
        stats = scraper.db.get_stats()
        print("\n" + "=" * 50)
        print("  FIRSTVIEW ARCHIVE STATISTICS")
        print("=" * 50)
        print(f"\nCollections indexed: {stats['total_collections']}")
        print(f"Photos indexed: {stats['total_photos']}")
        print(f"Downloaded: {stats['downloaded']}")
        print(f"Pending: {stats['pending']}")

        if stats.get("by_season"):
            print("\nBy Season:")
            for season, count in list(stats["by_season"].items())[:10]:
                print(f"  {season}: {count}")

        if stats.get("by_city"):
            print("\nBy City:")
            for city, count in stats["by_city"].items():
                print(f"  {city}: {count}")

        if stats.get("top_designers"):
            print("\nTop Designers:")
            for designer, count in list(stats["top_designers"].items())[:10]:
                print(f"  {designer}: {count}")

    elif args.command == "export":
        output = Path(args.output) if args.output else Path(CONFIG["storage_root"]) / "metadata.jsonl"
        scraper.export_metadata(output)


if __name__ == "__main__":
    main()
