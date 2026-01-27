#!/usr/bin/env python3
"""
W Magazine Site Ripper
Target: Fashion/culture articles from wmagazine.com
Bypass: Content accessible via JS-disabled fetch
Storage: External drives only
Output: Organized by category with full metadata
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
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.wmagazine.com",
    "sitemap_index": "https://www.wmagazine.com/sitemaps/pages.xml",
    "storage_root": "/Volumes/#1/wmag_archive",
    "db_path": "/Volumes/#1/wmag_archive/wmag_index.db",
    "rate_limit_seconds": 1.5,  # Be respectful
    "max_retries": 3,
    "retry_delay": 5.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "min_word_count": 100,
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
    author: Optional[str]
    publish_date: Optional[str]
    modified_date: Optional[str]
    image_url: Optional[str]
    word_count: int
    downloaded: bool
    download_date: Optional[str]
    file_path: Optional[str]

# ============================================================================
# DATABASE
# ============================================================================

class WMagDatabase:
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
                    author TEXT,
                    publish_date TEXT,
                    modified_date TEXT,
                    image_url TEXT,
                    word_count INTEGER DEFAULT 0,
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
                CREATE INDEX IF NOT EXISTS idx_articles_publish_date ON articles(publish_date);
            """)

    def add_article(self, article: ArticleMetadata):
        """Add or update an article."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO articles
                (id, url, title, category, subcategory, author, publish_date,
                 modified_date, image_url, word_count, downloaded, download_date, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id, article.url, article.title, article.category,
                article.subcategory, article.author, article.publish_date,
                article.modified_date, article.image_url, article.word_count,
                article.downloaded, article.download_date, article.file_path
            ))

    def get_pending_articles(self, category: Optional[str] = None, limit: int = 1000) -> List[ArticleMetadata]:
        """Get articles that haven't been downloaded yet."""
        query = """SELECT id, url, title, category, subcategory, author, publish_date,
                   modified_date, image_url, word_count, downloaded, download_date, file_path
                   FROM articles WHERE downloaded = 0"""
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [ArticleMetadata(*row) for row in rows]

    def mark_downloaded(self, article_id: str, file_path: str, word_count: int):
        """Mark an article as downloaded."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                UPDATE articles
                SET downloaded = 1, download_date = ?, file_path = ?, word_count = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), file_path, word_count, article_id))

    def mark_sitemap_processed(self, url: str, article_count: int):
        """Mark a sitemap as processed."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sitemaps (url, article_count, processed, last_processed)
                VALUES (?, ?, 1, ?)
            """, (url, article_count, datetime.now().isoformat()))

    def is_sitemap_processed(self, url: str) -> bool:
        """Check if a sitemap has been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT processed FROM sitemaps WHERE url = ?", (url,))
            row = cursor.fetchone()
            return row is not None and row[0] == 1

    def log_error(self, url: str, error_type: str, message: str):
        """Log an error."""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("""
                    INSERT INTO errors (url, error_type, error_message)
                    VALUES (?, ?, ?)
                """, (url, error_type, message))
        except:
            pass

    def get_stats(self) -> Dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            stats['total_articles'] = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            stats['downloaded'] = conn.execute("SELECT COUNT(*) FROM articles WHERE downloaded = 1").fetchone()[0]
            stats['pending'] = conn.execute("SELECT COUNT(*) FROM articles WHERE downloaded = 0").fetchone()[0]
            stats['sitemaps_processed'] = conn.execute("SELECT COUNT(*) FROM sitemaps WHERE processed = 1").fetchone()[0]
            stats['total_words'] = conn.execute("SELECT SUM(word_count) FROM articles WHERE downloaded = 1").fetchone()[0] or 0
            stats['errors'] = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]

            # Category breakdown
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count, SUM(downloaded) as downloaded
                FROM articles GROUP BY category ORDER BY count DESC
            """)
            stats['categories'] = {row[0]: {'total': row[1], 'downloaded': row[2] or 0} for row in cursor.fetchall()}

            return stats

# ============================================================================
# SCRAPER
# ============================================================================

class WMagScraper:
    """W Magazine article scraper."""

    def __init__(self):
        self.config = CONFIG
        self.db = WMagDatabase(self.config["db_path"])
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.last_request_time = 0

        # Set up logging
        log_path = os.path.join(self.config["storage_root"], "scraper.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config["rate_limit_seconds"]:
            time.sleep(self.config["rate_limit_seconds"] - elapsed)
        self.last_request_time = time.time()

    def _fetch_page(self, url: str, retries: int = 0) -> Optional[str]:
        """Fetch a page with retry logic."""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if retries < self.config["max_retries"]:
                self.logger.warning(f"Retry {retries + 1} for {url}: {e}")
                time.sleep(self.config["retry_delay"])
                return self._fetch_page(url, retries + 1)
            else:
                self.logger.error(f"Failed to fetch {url}: {e}")
                self.db.log_error(url, "fetch_error", str(e))
                return None

    def _download_media(self, url: str, save_path: str) -> bool:
        """Download an image or media file."""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to download {url}: {e}")
            return False

    def _get_full_size_image_url(self, url: str) -> str:
        """Strip resize parameters to get full-size image."""
        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
        return url

    def _extract_images(self, soup, article_dir: str) -> List[str]:
        """Extract and download all images from article."""
        images = []
        image_dir = os.path.join(article_dir, "images")

        # Find all image sources in the article content
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue

            # Skip logos, icons, etc.
            if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'gravatar', 'pixel', 'tracking']):
                continue

            # Only get actual content images
            if 'imgix.bustle.com' not in src and 'cdn2.bustle.com' not in src:
                continue

            # Get full-size URL
            full_url = self._get_full_size_image_url(src)

            # Generate filename
            filename = hashlib.md5(full_url.encode()).hexdigest()[:16] + '.jpg'

            save_path = os.path.join(image_dir, filename)

            # Skip if already downloaded
            if os.path.exists(save_path):
                images.append(save_path)
                continue

            if self._download_media(full_url, save_path):
                images.append(save_path)

        return images

    def _extract_videos(self, soup) -> List[Dict]:
        """Extract video URLs and embeds."""
        videos = []

        # YouTube embeds
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'youtu.be' in src:
                video_id = None
                if 'youtube.com/embed/' in src:
                    video_id = src.split('/embed/')[1].split('?')[0]
                elif 'youtu.be/' in src:
                    video_id = src.split('youtu.be/')[1].split('?')[0]

                if video_id:
                    videos.append({
                        'type': 'youtube',
                        'id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}'
                    })

        # Vimeo embeds
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'vimeo.com' in src:
                video_id = re.search(r'vimeo\.com/video/(\d+)', src)
                if video_id:
                    videos.append({
                        'type': 'vimeo',
                        'id': video_id.group(1),
                        'url': f'https://vimeo.com/{video_id.group(1)}'
                    })

        return videos

    def _generate_id(self, url: str) -> str:
        """Generate unique ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _parse_category(self, url: str) -> Tuple[str, str]:
        """Extract category and subcategory from URL."""
        # URL pattern: https://www.wmagazine.com/category/article-slug
        path = urlparse(url).path.strip('/')
        parts = path.split('/')

        if len(parts) >= 2:
            return parts[0], ""  # W Magazine has flat category structure
        elif len(parts) == 1:
            return parts[0], ""
        return "uncategorized", ""

    # ========================================================================
    # INDEXING
    # ========================================================================

    def index_all_sitemaps(self):
        """Index all articles from all sitemaps."""
        self.logger.info("Fetching sitemap index...")

        xml = self._fetch_page(self.config["sitemap_index"])
        if not xml:
            self.logger.error("Failed to fetch sitemap index")
            return

        # Parse sitemap index - extract sub-sitemap URLs
        sub_sitemaps = re.findall(r'<loc>([^<]+)</loc>', xml)
        self.logger.info(f"Found {len(sub_sitemaps)} sub-sitemaps")

        total_articles = 0
        for i, sitemap_url in enumerate(sub_sitemaps):
            if self.db.is_sitemap_processed(sitemap_url):
                self.logger.info(f"[{i+1}/{len(sub_sitemaps)}] Skipping already processed: {sitemap_url}")
                continue

            self.logger.info(f"[{i+1}/{len(sub_sitemaps)}] Processing: {sitemap_url}")
            count = self.index_sitemap(sitemap_url)
            total_articles += count
            self.logger.info(f"  Indexed {count} articles (total: {total_articles})")

        self.logger.info(f"Indexing complete. Total articles: {total_articles}")

    def index_sitemap(self, sitemap_url: str) -> int:
        """Index articles from a single sitemap."""
        xml = self._fetch_page(sitemap_url)
        if not xml:
            return 0

        # Extract article URLs
        urls = re.findall(r'<loc>([^<]+)</loc>', xml)

        # Filter to only article URLs (exclude category pages, etc.)
        article_urls = [u for u in urls if '/story/' in u or '/culture/' in u or '/fashion/' in u]

        # Extract last modified dates
        lastmods = re.findall(r'<lastmod>([^<]+)</lastmod>', xml)

        count = 0
        for i, url in enumerate(article_urls):
            article_id = self._generate_id(url)
            category, subcategory = self._parse_category(url)

            # Get lastmod if available
            modified_date = lastmods[i] if i < len(lastmods) else None

            article = ArticleMetadata(
                id=article_id,
                url=url,
                title=None,  # Will be filled during download
                category=category,
                subcategory=subcategory,
                author=None,
                publish_date=None,
                modified_date=modified_date,
                image_url=None,
                word_count=0,
                downloaded=False,
                download_date=None,
                file_path=None
            )

            self.db.add_article(article)
            count += 1

        self.db.mark_sitemap_processed(sitemap_url, count)
        return count

    # ========================================================================
    # DOWNLOADING
    # ========================================================================

    def download_article(self, article: ArticleMetadata, download_media: bool = True) -> bool:
        """Download and save a single article with all media."""
        html = self._fetch_page(article.url)
        if not html:
            return False

        # Parse article content
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_el = soup.find('h1')
        title = title_el.get_text(strip=True) if title_el else "Untitled"

        # Extract author
        author_el = soup.find('a', {'data-testid': 'BylinesWrapper'}) or soup.find('a', rel='author')
        author = author_el.get_text(strip=True) if author_el else None

        # Extract publish date from meta or time element
        time_el = soup.find('time')
        publish_date = time_el.get('datetime') if time_el else None

        if not publish_date:
            meta_date = soup.find('meta', {'property': 'article:published_time'})
            publish_date = meta_date.get('content') if meta_date else None

        # Extract article body - try multiple selectors
        content = ""
        body_selectors = [
            'article',
            '[class*="ArticleBody"]',
            '[class*="body-content"]',
            '.article-content',
            '.post-content',
            '.entry-content',
        ]

        for selector in body_selectors:
            body = soup.select_one(selector)
            if body:
                # Get all paragraphs
                paragraphs = body.find_all('p')
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if len(content) > 200:
                    break

        # Fallback: get all p tags in main content area
        if len(content) < 200:
            main = soup.find('main') or soup.find('article')
            if main:
                paragraphs = main.find_all('p')
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        word_count = len(content.split())

        if word_count < self.config["min_word_count"]:
            self.logger.warning(f"Skipping {article.url}: insufficient content ({word_count} words)")
            self.db.log_error(article.url, "insufficient_content", f"{word_count} words")
            return False

        # Extract featured image
        og_image = soup.find('meta', property='og:image')
        image_url = og_image.get('content') if og_image else None

        # Create article directory structure
        # Format: /category/YYYY/MM/article_id/
        date_parts = publish_date.split('-')[:2] if publish_date and '-' in publish_date else ['unknown', '00']
        year = date_parts[0] if len(date_parts) > 0 else 'unknown'
        month = date_parts[1] if len(date_parts) > 1 else '00'

        article_dir = os.path.join(
            self.config["storage_root"],
            "articles",
            article.category or "general",
            year,
            month,
            article.id
        )
        os.makedirs(article_dir, exist_ok=True)

        # Download media if enabled
        images = []
        videos = []

        if download_media:
            # Download article images
            images = self._extract_images(soup, article_dir)

            # Extract video URLs (not downloading, just recording)
            videos = self._extract_videos(soup)

            # Download featured image
            if image_url:
                featured_filename = "featured_" + hashlib.md5(image_url.encode()).hexdigest()[:16] + ".jpg"
                featured_path = os.path.join(article_dir, featured_filename)
                if not os.path.exists(featured_path):
                    self._download_media(self._get_full_size_image_url(image_url), featured_path)

        # Build article data
        article_data = {
            "id": article.id,
            "url": article.url,
            "title": title,
            "author": author,
            "category": article.category,
            "publish_date": publish_date,
            "modified_date": article.modified_date,
            "featured_image_url": image_url,
            "word_count": word_count,
            "content": content,
            "source": "wmagazine.com",
            "scraped_at": datetime.now().isoformat(),
            # Media info
            "images": [os.path.basename(p) for p in images],
            "videos": videos,
            "image_count": len(images),
            "video_count": len(videos),
        }

        # Save article metadata
        metadata_path = os.path.join(article_dir, "article.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)

        # Update database
        self.db.mark_downloaded(article.id, metadata_path, word_count)

        media_info = f", {len(images)} images, {len(videos)} videos" if download_media else ""
        self.logger.info(f"Downloaded: {title[:50]} ({word_count} words{media_info})")

        return True

    def download_articles(self, category: Optional[str] = None, limit: int = 1000):
        """Download multiple articles."""
        articles = self.db.get_pending_articles(category=category, limit=limit)
        self.logger.info(f"Found {len(articles)} pending articles")

        success = 0
        failed = 0

        for i, article in enumerate(articles):
            self.logger.info(f"[{i+1}/{len(articles)}] Processing: {article.url}")

            if self.download_article(article):
                success += 1
            else:
                failed += 1

            # Progress checkpoint
            if (i + 1) % 100 == 0:
                self.logger.info(f"Progress: {success} downloaded, {failed} failed")

        self.logger.info(f"Download complete: {success} downloaded, {failed} failed")
        return success, failed

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_training_data(self, output_path: str, min_words: int = 500):
        """Export downloaded articles as training data."""
        storage_root = os.path.join(self.config["storage_root"], "articles")

        training_data = []

        for root, dirs, files in os.walk(storage_root):
            for filename in files:
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        article = json.load(f)

                    if article.get('word_count', 0) >= min_words:
                        training_data.append({
                            "id": article["id"],
                            "source": "wmag",
                            "category": article.get("category", ""),
                            "title": article.get("title", ""),
                            "author": article.get("author", ""),
                            "text": article.get("content", ""),
                            "word_count": article.get("word_count", 0),
                            "tags": [
                                article.get("category", ""),
                                "fashion",
                                "culture"
                            ]
                        })
                except Exception as e:
                    self.logger.warning(f"Error processing {file_path}: {e}")

        # Save training data
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Exported {len(training_data)} articles to {output_path}")
        return len(training_data)

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        return self.db.get_stats()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="W Magazine Site Ripper")
    parser.add_argument("command", choices=["index", "download", "export", "stats"],
                       help="Command to run")
    parser.add_argument("--category", "-c", help="Specific category to process")
    parser.add_argument("--limit", "-l", type=int, default=1000,
                       help="Maximum articles to download")
    parser.add_argument("--output", "-o", help="Output path for export")
    parser.add_argument("--min-words", type=int, default=500,
                       help="Minimum word count for export")

    args = parser.parse_args()

    try:
        scraper = WMagScraper()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    if args.command == "index":
        scraper.index_all_sitemaps()

    elif args.command == "download":
        scraper.download_articles(category=args.category, limit=args.limit)

    elif args.command == "export":
        output = args.output or os.path.join(scraper.config["storage_root"], "wmag_training.json")
        scraper.export_training_data(output, min_words=args.min_words)

    elif args.command == "stats":
        stats = scraper.get_stats()
        print("\n=== W Magazine Archive Statistics ===")
        print(f"Total articles indexed: {stats['total_articles']:,}")
        print(f"Downloaded: {stats['downloaded']:,}")
        print(f"Pending: {stats['pending']:,}")
        print(f"Total words: {stats['total_words']:,}")
        print(f"Sitemaps processed: {stats['sitemaps_processed']}")
        print(f"Errors: {stats['errors']}")
        print("\nCategories:")
        for cat, counts in sorted(stats['categories'].items(), key=lambda x: -x[1]['total']):
            pct = counts['downloaded'] / counts['total'] * 100 if counts['total'] > 0 else 0
            print(f"  {cat}: {counts['total']:,} total, {counts['downloaded']:,} downloaded ({pct:.1f}%)")

    return 0

if __name__ == "__main__":
    exit(main())
