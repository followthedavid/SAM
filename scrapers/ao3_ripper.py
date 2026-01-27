#!/usr/bin/env python3
"""
Archive of Our Own (AO3) Story Ripper
Target: M/M explicit fiction from AO3
Storage: External drives only
Output: Training data format for LLM fine-tuning

AO3 Structure:
- Works searchable by tags, ratings, categories
- URL pattern: /works/[numeric_id]
- Rich metadata: tags, word count, kudos, chapters
- Rate limiting required (be respectful)
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
    "storage_root": "/Volumes/David External/ao3_archive",
    "db_path": "/Volumes/David External/ao3_archive/ao3_index.db",
    "rate_limit_seconds": 3.0,  # AO3 is stricter - be respectful
    "max_retries": 3,
    "retry_delay": 10.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "max_workers": 1,  # Single-threaded to respect AO3
    "checkpoint_interval": 50,
    "pages_per_search": 100,  # Max pages to crawl per search
}

# Search filters for M/M explicit content
SEARCH_FILTERS = {
    "work_search[category_ids][]": "23",  # M/M category
    "work_search[rating_ids][]": "13",    # Explicit rating
    "work_search[complete]": "T",          # Complete works only
    "work_search[language_id]": "en",      # English
    "work_search[sort_column]": "kudos_count",  # Sort by popularity
    "work_search[sort_direction]": "desc",
}

# Additional tag searches for variety
TAG_SEARCHES = [
    "Gay Sex",
    "Anal Sex",
    "Oral Sex",
    "First Time",
    "Friends to Lovers",
    "Enemies to Lovers",
    "Slow Burn",
    "PWP",
    "Smut",
    "Romance",
    "BDSM",
    "Dominant/Submissive",
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AO3Work:
    """Metadata for an AO3 work."""
    id: str
    ao3_id: int
    url: str
    title: str
    author: str
    rating: str
    category: str  # M/M, F/F, etc.
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
    complete: bool
    downloaded: bool
    download_date: Optional[str]
    file_path: Optional[str]

@dataclass
class TrainingExample:
    """Formatted training data for LLM fine-tuning."""
    id: str
    source: str  # "ao3"
    title: str
    author: str
    text: str
    word_count: int
    tags: List[str]
    # Enhanced metadata
    character_count: int
    has_dialogue: bool
    pov: str
    content_intensity: str
    relationship_type: Optional[str]
    setting: Optional[str]
    quality_score: float
    # AO3-specific
    fandoms: List[str]
    relationships: List[str]
    kudos: int
    hits: int

# ============================================================================
# DATABASE
# ============================================================================

class AO3Database:
    """SQLite database for tracking AO3 scrape progress."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS works (
                    id TEXT PRIMARY KEY,
                    ao3_id INTEGER UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    rating TEXT,
                    category TEXT,
                    fandoms TEXT,  -- JSON array
                    relationships TEXT,  -- JSON array
                    characters TEXT,  -- JSON array
                    tags TEXT,  -- JSON array
                    warnings TEXT,  -- JSON array
                    word_count INTEGER,
                    chapter_count INTEGER,
                    kudos INTEGER,
                    hits INTEGER,
                    bookmarks INTEGER,
                    comments INTEGER,
                    date_published TEXT,
                    date_updated TEXT,
                    summary TEXT,
                    complete BOOLEAN,
                    downloaded BOOLEAN DEFAULT 0,
                    download_date TEXT,
                    file_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS search_progress (
                    search_query TEXT PRIMARY KEY,
                    last_page INTEGER DEFAULT 0,
                    works_found INTEGER DEFAULT 0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_works_ao3_id ON works(ao3_id);
                CREATE INDEX IF NOT EXISTS idx_works_downloaded ON works(downloaded);
                CREATE INDEX IF NOT EXISTS idx_works_kudos ON works(kudos);
                CREATE INDEX IF NOT EXISTS idx_works_word_count ON works(word_count);
            """)

    def add_work(self, work: AO3Work) -> bool:
        """Add or update a work in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO works
                    (id, ao3_id, url, title, author, rating, category,
                     fandoms, relationships, characters, tags, warnings,
                     word_count, chapter_count, kudos, hits, bookmarks, comments,
                     date_published, date_updated, summary, complete,
                     downloaded, download_date, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    work.id, work.ao3_id, work.url, work.title, work.author,
                    work.rating, work.category,
                    json.dumps(work.fandoms), json.dumps(work.relationships),
                    json.dumps(work.characters), json.dumps(work.tags),
                    json.dumps(work.warnings), work.word_count, work.chapter_count,
                    work.kudos, work.hits, work.bookmarks, work.comments,
                    work.date_published, work.date_updated, work.summary,
                    work.complete, work.downloaded, work.download_date, work.file_path
                ))
            return True
        except Exception as e:
            logging.error(f"Database error adding work: {e}")
            return False

    def get_pending_works(self, min_kudos: int = 0, min_words: int = 1000, limit: int = 100) -> List[AO3Work]:
        """Get works that haven't been downloaded yet."""
        query = """
            SELECT * FROM works
            WHERE downloaded = 0
            AND kudos >= ?
            AND word_count >= ?
            ORDER BY kudos DESC
            LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (min_kudos, min_words, limit)).fetchall()
            works = []
            for row in rows:
                works.append(AO3Work(
                    id=row["id"],
                    ao3_id=row["ao3_id"],
                    url=row["url"],
                    title=row["title"],
                    author=row["author"],
                    rating=row["rating"],
                    category=row["category"],
                    fandoms=json.loads(row["fandoms"]) if row["fandoms"] else [],
                    relationships=json.loads(row["relationships"]) if row["relationships"] else [],
                    characters=json.loads(row["characters"]) if row["characters"] else [],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    warnings=json.loads(row["warnings"]) if row["warnings"] else [],
                    word_count=row["word_count"],
                    chapter_count=row["chapter_count"],
                    kudos=row["kudos"],
                    hits=row["hits"],
                    bookmarks=row["bookmarks"],
                    comments=row["comments"],
                    date_published=row["date_published"],
                    date_updated=row["date_updated"],
                    summary=row["summary"],
                    complete=row["complete"],
                    downloaded=row["downloaded"],
                    download_date=row["download_date"],
                    file_path=row["file_path"]
                ))
            return works

    def mark_downloaded(self, work_id: str, file_path: str):
        """Mark a work as downloaded."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE works
                SET downloaded = 1, download_date = ?, file_path = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), file_path, work_id))

    def log_error(self, url: str, error_type: str, message: str):
        """Log an error for later review."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO errors (url, error_type, error_message)
                VALUES (?, ?, ?)
            """, (url, error_type, message))

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
            downloaded = conn.execute("SELECT COUNT(*) FROM works WHERE downloaded = 1").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            total_words = conn.execute("SELECT SUM(word_count) FROM works").fetchone()[0] or 0
            avg_kudos = conn.execute("SELECT AVG(kudos) FROM works").fetchone()[0] or 0

            return {
                "total_indexed": total,
                "downloaded": downloaded,
                "pending": total - downloaded,
                "errors": errors,
                "total_words": total_words,
                "avg_kudos": int(avg_kudos)
            }

# ============================================================================
# SCRAPER
# ============================================================================

class AO3Scraper:
    """Main scraper class for AO3."""

    def __init__(self, config: Dict = CONFIG):
        self.config = config
        self.session = self._create_session()
        self.db = AO3Database(config["db_path"])
        self.logger = self._setup_logging()

        # Verify external drive is mounted
        if not os.path.exists(os.path.dirname(config["storage_root"])):
            raise RuntimeError(f"External drive not mounted: {config['storage_root']}")

        os.makedirs(config["storage_root"], exist_ok=True)

    def _create_session(self) -> requests.Session:
        """Create a session with proper headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.config["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        return session

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_path = os.path.join(self.config["storage_root"], "scraper.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def _rate_limit(self):
        """Respect rate limiting."""
        time.sleep(self.config["rate_limit_seconds"])

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

    def _generate_id(self, ao3_id: int) -> str:
        """Generate unique ID from AO3 work ID."""
        return hashlib.md5(f"ao3_{ao3_id}".encode()).hexdigest()

    # ========================================================================
    # PARSING
    # ========================================================================

    def parse_search_results(self, html: str) -> List[Dict]:
        """Parse search results page for work metadata."""
        soup = BeautifulSoup(html, "html.parser")
        works = []

        for article in soup.select("li.work.blurb"):
            try:
                work_data = self._parse_work_blurb(article)
                if work_data:
                    works.append(work_data)
            except Exception as e:
                self.logger.warning(f"Error parsing work blurb: {e}")
                continue

        return works

    def _parse_work_blurb(self, article) -> Optional[Dict]:
        """Parse a single work blurb from search results."""
        # Get work ID from the article
        work_id_match = re.search(r'work_(\d+)', article.get("id", ""))
        if not work_id_match:
            return None

        ao3_id = int(work_id_match.group(1))

        # Title and URL
        title_link = article.select_one("h4.heading a")
        if not title_link:
            return None
        title = title_link.get_text(strip=True)
        url = f"{self.config['base_url']}{title_link.get('href', '')}"

        # Author
        author_link = article.select_one("h4.heading a[rel='author']")
        author = author_link.get_text(strip=True) if author_link else "Anonymous"

        # Rating
        rating_tag = article.select_one("span.rating")
        rating = rating_tag.get_text(strip=True) if rating_tag else "Not Rated"

        # Category (M/M, F/F, etc.)
        category_tag = article.select_one("span.category")
        category = category_tag.get_text(strip=True) if category_tag else ""

        # Fandoms
        fandom_tags = article.select("h5.fandoms a.tag")
        fandoms = [f.get_text(strip=True) for f in fandom_tags]

        # Relationships
        rel_tags = article.select("li.relationships a.tag")
        relationships = [r.get_text(strip=True) for r in rel_tags]

        # Characters
        char_tags = article.select("li.characters a.tag")
        characters = [c.get_text(strip=True) for c in char_tags]

        # Freeform tags
        tag_elements = article.select("li.freeforms a.tag")
        tags = [t.get_text(strip=True) for t in tag_elements]

        # Warnings
        warning_tags = article.select("li.warnings a.tag")
        warnings = [w.get_text(strip=True) for w in warning_tags]

        # Stats
        stats = article.select_one("dl.stats")
        word_count = 0
        chapter_count = 0
        kudos = 0
        hits = 0
        bookmarks = 0
        comments = 0

        if stats:
            # Word count
            words_dd = stats.select_one("dd.words")
            if words_dd:
                word_text = words_dd.get_text(strip=True).replace(",", "")
                try:
                    word_count = int(word_text)
                except ValueError:
                    pass

            # Chapters
            chapters_dd = stats.select_one("dd.chapters")
            if chapters_dd:
                chapters_text = chapters_dd.get_text(strip=True)
                chapter_match = re.match(r'(\d+)', chapters_text)
                if chapter_match:
                    chapter_count = int(chapter_match.group(1))

            # Kudos
            kudos_dd = stats.select_one("dd.kudos")
            if kudos_dd:
                kudos_link = kudos_dd.select_one("a")
                kudos_text = kudos_link.get_text(strip=True) if kudos_link else kudos_dd.get_text(strip=True)
                try:
                    kudos = int(kudos_text.replace(",", ""))
                except ValueError:
                    pass

            # Hits
            hits_dd = stats.select_one("dd.hits")
            if hits_dd:
                try:
                    hits = int(hits_dd.get_text(strip=True).replace(",", ""))
                except ValueError:
                    pass

            # Bookmarks
            bookmarks_dd = stats.select_one("dd.bookmarks")
            if bookmarks_dd:
                bookmarks_link = bookmarks_dd.select_one("a")
                bookmarks_text = bookmarks_link.get_text(strip=True) if bookmarks_link else bookmarks_dd.get_text(strip=True)
                try:
                    bookmarks = int(bookmarks_text.replace(",", ""))
                except ValueError:
                    pass

            # Comments
            comments_dd = stats.select_one("dd.comments")
            if comments_dd:
                comments_link = comments_dd.select_one("a")
                comments_text = comments_link.get_text(strip=True) if comments_link else comments_dd.get_text(strip=True)
                try:
                    comments = int(comments_text.replace(",", ""))
                except ValueError:
                    pass

        # Dates
        date_tag = article.select_one("p.datetime")
        date_published = date_tag.get_text(strip=True) if date_tag else ""

        # Summary
        summary_tag = article.select_one("blockquote.summary")
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        # Check if complete
        chapters_text = ""
        if stats:
            chapters_dd = stats.select_one("dd.chapters")
            if chapters_dd:
                chapters_text = chapters_dd.get_text(strip=True)
        complete = "/" in chapters_text and not chapters_text.endswith("/?")

        return {
            "ao3_id": ao3_id,
            "url": url,
            "title": title,
            "author": author,
            "rating": rating,
            "category": category,
            "fandoms": fandoms,
            "relationships": relationships,
            "characters": characters,
            "tags": tags,
            "warnings": warnings,
            "word_count": word_count,
            "chapter_count": chapter_count,
            "kudos": kudos,
            "hits": hits,
            "bookmarks": bookmarks,
            "comments": comments,
            "date_published": date_published,
            "date_updated": date_published,  # Same for search results
            "summary": summary,
            "complete": complete
        }

    # ========================================================================
    # INDEXING
    # ========================================================================

    def build_search_url(self, tag_query: Optional[str] = None, page: int = 1) -> str:
        """Build a search URL with filters."""
        params = dict(SEARCH_FILTERS)
        if tag_query:
            params["work_search[query]"] = tag_query
        params["page"] = str(page)

        return f"{self.config['base_url']}/works/search?{urlencode(params)}"

    def index_search(self, tag_query: Optional[str] = None, max_pages: int = None) -> int:
        """Index works from a search query."""
        max_pages = max_pages or self.config["pages_per_search"]
        query_name = tag_query or "all_mm_explicit"
        self.logger.info(f"Indexing search: {query_name}")

        works_found = 0
        page = 1

        while page <= max_pages:
            url = self.build_search_url(tag_query, page)
            self.logger.info(f"  Fetching page {page}...")

            html = self._fetch_page(url)
            if not html:
                break

            works = self.parse_search_results(html)
            if not works:
                self.logger.info(f"  No more works found on page {page}")
                break

            for work_data in works:
                work = AO3Work(
                    id=self._generate_id(work_data["ao3_id"]),
                    downloaded=False,
                    download_date=None,
                    file_path=None,
                    **work_data
                )
                if self.db.add_work(work):
                    works_found += 1

            self.logger.info(f"  Page {page}: {len(works)} works, {works_found} total")
            page += 1

        self.logger.info(f"Completed indexing '{query_name}': {works_found} works")
        return works_found

    def index_all_tags(self) -> Dict[str, int]:
        """Index works from all configured tag searches."""
        results = {}

        # First, do the main M/M Explicit search
        results["main"] = self.index_search(None, max_pages=50)

        # Then search by specific tags
        for tag in TAG_SEARCHES:
            try:
                count = self.index_search(tag, max_pages=20)
                results[tag] = count
            except Exception as e:
                self.logger.error(f"Error indexing tag '{tag}': {e}")
                results[tag] = -1

        return results

    # ========================================================================
    # DOWNLOADING
    # ========================================================================

    def download_work(self, work: AO3Work) -> bool:
        """Download a single work's full text."""
        # AO3 provides a download option - use the HTML download
        download_url = f"{self.config['base_url']}/works/{work.ao3_id}?view_adult=true&view_full_work=true"

        html = self._fetch_page(download_url)
        if not html:
            return False

        soup = BeautifulSoup(html, "html.parser")

        # Extract the story text from chapter content
        chapters = soup.select("div.userstuff")
        if not chapters:
            self.logger.warning(f"No content found for work {work.ao3_id}")
            return False

        # Combine all chapter text
        full_text = []
        for chapter in chapters:
            # Remove any notes sections
            for notes in chapter.select(".notes"):
                notes.decompose()
            text = chapter.get_text(separator="\n", strip=True)
            full_text.append(text)

        story_text = "\n\n---\n\n".join(full_text)

        if len(story_text) < 500:
            self.logger.warning(f"Insufficient content for work {work.ao3_id}")
            return False

        # Analyze content
        analysis = self.analyze_content(story_text)

        # Build tags
        all_tags = work.tags + [work.rating, work.category]
        if analysis["content_intensity"]:
            all_tags.append(analysis["content_intensity"])
        if analysis["relationship_type"]:
            all_tags.append(analysis["relationship_type"])

        # Create training example
        training_example = TrainingExample(
            id=work.id,
            source="ao3",
            title=work.title,
            author=work.author,
            text=story_text,
            word_count=len(story_text.split()),
            tags=all_tags,
            character_count=analysis["character_count"],
            has_dialogue=analysis["has_dialogue"],
            pov=analysis["pov"],
            content_intensity=analysis["content_intensity"],
            relationship_type=analysis["relationship_type"],
            setting=analysis["setting"],
            quality_score=analysis["quality_score"],
            fandoms=work.fandoms,
            relationships=work.relationships,
            kudos=work.kudos,
            hits=work.hits
        )

        # Save to file
        fandom_dir = work.fandoms[0] if work.fandoms else "misc"
        fandom_dir = re.sub(r'[^\w\-_]', '_', fandom_dir)[:50]
        save_dir = os.path.join(self.config["storage_root"], "works", fandom_dir)
        os.makedirs(save_dir, exist_ok=True)

        safe_title = re.sub(r'[^\w\-_]', '_', work.title)[:80]
        filename = f"{work.ao3_id}_{safe_title}.json"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(training_example), f, indent=2, ensure_ascii=False)

        self.db.mark_downloaded(work.id, file_path)
        self.logger.info(f"Downloaded: {work.title} ({len(story_text.split())} words, {work.kudos} kudos)")

        return True

    def analyze_content(self, text: str) -> Dict:
        """Analyze story content for enhanced metadata."""
        analysis = {
            "character_count": 2,
            "has_dialogue": False,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "setting": None,
            "quality_score": 0.5
        }

        text_lower = text.lower()

        # Detect dialogue
        dialogue_markers = text.count('"') + text.count('"') + text.count('"')
        analysis["has_dialogue"] = dialogue_markers > 20

        # Detect POV
        first_person = len(re.findall(r'\bI\b', text)) + len(re.findall(r'\bmy\b', text_lower))
        third_person = len(re.findall(r'\bhe\b', text_lower)) + len(re.findall(r'\bhis\b', text_lower))
        if first_person > third_person * 1.5:
            analysis["pov"] = "first-person"

        # Content intensity
        mild_terms = ["kiss", "touch", "hold", "embrace"]
        moderate_terms = ["naked", "hard", "stroke", "moan"]
        explicit_terms = ["cock", "dick", "fuck", "ass", "cum", "suck"]

        explicit_count = sum(text_lower.count(t) for t in explicit_terms)
        moderate_count = sum(text_lower.count(t) for t in moderate_terms)

        if explicit_count > 15:
            analysis["content_intensity"] = "explicit"
        elif moderate_count > 5 or explicit_count > 5:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Relationship type
        rel_markers = {
            "friends": ["friend", "buddy", "roommate"],
            "strangers": ["stranger", "never met", "first time seeing"],
            "enemies": ["enemy", "rival", "hate"],
            "romantic": ["boyfriend", "lover", "love you"],
        }
        for rel_type, markers in rel_markers.items():
            if any(m in text_lower for m in markers):
                analysis["relationship_type"] = rel_type
                break

        # Quality score
        word_count = len(text.split())
        score = 0.5
        if word_count > 5000:
            score += 0.1
        if word_count > 10000:
            score += 0.1
        if analysis["has_dialogue"]:
            score += 0.1
        if word_count < 2000:
            score -= 0.1

        analysis["quality_score"] = min(1.0, max(0.0, score))

        return analysis

    def download_pending(self, min_kudos: int = 100, min_words: int = 2000, limit: int = 500):
        """Download pending works meeting criteria."""
        pending = self.db.get_pending_works(min_kudos, min_words, limit)
        self.logger.info(f"Found {len(pending)} pending works (kudos>={min_kudos}, words>={min_words})")

        success = 0
        failed = 0

        for i, work in enumerate(pending):
            try:
                if self.download_work(work):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                self.logger.error(f"Error downloading work {work.ao3_id}: {e}")
                self.db.log_error(work.url, "download_error", str(e))
                failed += 1

            if (i + 1) % self.config["checkpoint_interval"] == 0:
                stats = self.db.get_stats()
                self.logger.info(f"Checkpoint: {stats['downloaded']}/{stats['total_indexed']} downloaded")

        return {"success": success, "failed": failed}

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_training_data(self, output_path: str, min_word_count: int = 2000, min_kudos: int = 50):
        """Export all downloaded works as training JSONL."""
        self.logger.info(f"Exporting training data to {output_path}")

        works_dir = os.path.join(self.config["storage_root"], "works")
        exported = 0

        with open(output_path, "w", encoding="utf-8") as out:
            for fandom in os.listdir(works_dir):
                fandom_path = os.path.join(works_dir, fandom)
                if not os.path.isdir(fandom_path):
                    continue

                for filename in os.listdir(fandom_path):
                    if not filename.endswith(".json"):
                        continue

                    file_path = os.path.join(fandom_path, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        if data.get("word_count", 0) >= min_word_count:
                            if data.get("kudos", 0) >= min_kudos:
                                out.write(json.dumps(data, ensure_ascii=False) + "\n")
                                exported += 1
                    except Exception as e:
                        self.logger.error(f"Error reading {file_path}: {e}")

        self.logger.info(f"Exported {exported} works to {output_path}")
        return exported

# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AO3 Story Ripper")
    parser.add_argument("command", choices=["index", "download", "export", "stats"],
                       help="Command to run")
    parser.add_argument("--tag", "-t", help="Specific tag to search")
    parser.add_argument("--pages", "-p", type=int, default=20,
                       help="Max pages to index")
    parser.add_argument("--limit", "-l", type=int, default=500,
                       help="Maximum works to download")
    parser.add_argument("--min-kudos", type=int, default=100,
                       help="Minimum kudos for download")
    parser.add_argument("--min-words", type=int, default=2000,
                       help="Minimum word count")
    parser.add_argument("--output", "-o", help="Output path for export")

    args = parser.parse_args()

    try:
        scraper = AO3Scraper()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Please ensure the external drive is mounted.")
        return 1

    if args.command == "index":
        if args.tag:
            count = scraper.index_search(args.tag, args.pages)
            print(f"Indexed {count} works for tag '{args.tag}'")
        else:
            results = scraper.index_all_tags()
            total = sum(v for v in results.values() if v > 0)
            print(f"Indexed {total} works across {len(results)} searches")

    elif args.command == "download":
        results = scraper.download_pending(args.min_kudos, args.min_words, args.limit)
        print(f"Downloaded: {results['success']}, Failed: {results['failed']}")

    elif args.command == "export":
        output = args.output or os.path.join(
            scraper.config["storage_root"],
            "training_data.jsonl"
        )
        count = scraper.export_training_data(output, args.min_words, args.min_kudos)
        print(f"Exported {count} works to {output}")

    elif args.command == "stats":
        stats = scraper.db.get_stats()
        print(f"\nAO3 Archive Statistics:")
        print(f"  Total indexed: {stats['total_indexed']}")
        print(f"  Downloaded: {stats['downloaded']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Total words: {stats['total_words']:,}")
        print(f"  Avg kudos: {stats['avg_kudos']}")
        print(f"  Errors: {stats['errors']}")

    return 0

if __name__ == "__main__":
    exit(main())
