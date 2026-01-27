#!/usr/bin/env python3
"""
Nifty.org Story Ripper - Advanced Site Scraper
Target: Gay male stories from nifty.org
Storage: External drives only
Output: Training data format for LLM fine-tuning

Site Structure Analysis:
- Base URL: https://www.nifty.org/nifty/gay/
- Categories: adult-friends, athletics, college, first-time, etc.
- Stories: Plain text with email-style headers (Date, From, Subject)
- Pagination: jscroll infinite scroll with next links
- Series: Directories containing multiple parts

Architecture:
1. Category crawler - enumerate all gay male categories
2. Story indexer - build comprehensive list of all stories
3. Content fetcher - download with rate limiting
4. Parser - extract clean text from email format
5. Formatter - convert to training data format
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
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.nifty.org",
    "gay_index": "/nifty/gay/",
    "storage_root": "/Volumes/David External/nifty_archive",  # External drive only
    "db_path": "/Volumes/David External/nifty_archive/nifty_index.db",
    "rate_limit_seconds": 2.0,  # Be respectful
    "max_retries": 3,
    "retry_delay": 5.0,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "max_workers": 3,  # Conservative parallelism
    "checkpoint_interval": 100,  # Save progress every N stories
}

# Categories to scrape (gay male focus)
GAY_CATEGORIES = [
    "adult-friends",
    "adult-youth",
    "athletics",
    "authoritarian",
    "beginnings",
    "camping",
    "celebrity",
    "college",
    "encounters",
    "first-time",
    "high-school",
    "historical",
    "incest",
    "interracial",
    "masturbation",
    "military",
    "no-sex",
    "relationships",
    "rural",
    "sf-fantasy",
    "urination",
    "young-friends",
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class StoryMetadata:
    """Metadata for a single story."""
    id: str  # MD5 hash of URL
    url: str
    category: str
    title: str
    author: Optional[str]
    author_email: Optional[str]
    date_published: Optional[str]
    file_size: Optional[int]
    is_series: bool
    series_name: Optional[str]
    part_number: Optional[int]
    word_count: Optional[int]
    downloaded: bool
    download_date: Optional[str]
    file_path: Optional[str]

@dataclass
class TrainingExample:
    """Formatted training data for LLM fine-tuning."""
    id: str
    source: str  # "nifty"
    category: str
    title: str
    author: str
    text: str
    word_count: int
    tags: List[str]
    # Enhanced metadata for roleplay training
    character_count: int
    has_dialogue: bool
    pov: str  # first-person, third-person
    content_intensity: str  # mild, moderate, explicit
    relationship_type: Optional[str]  # friends, strangers, authority, etc.
    setting: Optional[str]
    quality_score: float

# ============================================================================
# DATABASE
# ============================================================================

class NiftyDatabase:
    """SQLite database for tracking scrape progress."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    author_email TEXT,
                    date_published TEXT,
                    file_size INTEGER,
                    is_series BOOLEAN DEFAULT 0,
                    series_name TEXT,
                    part_number INTEGER,
                    word_count INTEGER,
                    downloaded BOOLEAN DEFAULT 0,
                    download_date TEXT,
                    file_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scrape_progress (
                    category TEXT PRIMARY KEY,
                    last_page_url TEXT,
                    stories_found INTEGER DEFAULT 0,
                    stories_downloaded INTEGER DEFAULT 0,
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

                CREATE INDEX IF NOT EXISTS idx_stories_category ON stories(category);
                CREATE INDEX IF NOT EXISTS idx_stories_downloaded ON stories(downloaded);
                CREATE INDEX IF NOT EXISTS idx_stories_author ON stories(author);
            """)

    def add_story(self, story: StoryMetadata) -> bool:
        """Add or update a story in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO stories
                    (id, url, category, title, author, author_email, date_published,
                     file_size, is_series, series_name, part_number, word_count,
                     downloaded, download_date, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    story.id, story.url, story.category, story.title,
                    story.author, story.author_email, story.date_published,
                    story.file_size, story.is_series, story.series_name,
                    story.part_number, story.word_count, story.downloaded,
                    story.download_date, story.file_path
                ))
            return True
        except Exception as e:
            logging.error(f"Database error adding story: {e}")
            return False

    def get_pending_stories(self, category: Optional[str] = None, limit: int = 100, skip_series: bool = True) -> List[StoryMetadata]:
        """Get stories that haven't been downloaded yet."""
        query = """SELECT id, url, category, title, author, author_email, date_published,
                   file_size, is_series, series_name, part_number, word_count,
                   downloaded, download_date, file_path
                   FROM stories WHERE downloaded = 0"""
        if skip_series:
            query += " AND is_series = 0"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += f" LIMIT {limit}"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [StoryMetadata(**dict(row)) for row in rows]

    def mark_downloaded(self, story_id: str, file_path: str, word_count: int):
        """Mark a story as downloaded with retry logic."""
        import time as _time
        for attempt in range(5):
            try:
                with sqlite3.connect(self.db_path, timeout=30) as conn:
                    conn.execute("""
                        UPDATE stories
                        SET downloaded = 1, download_date = ?, file_path = ?, word_count = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), file_path, word_count, story_id))
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < 4:
                    _time.sleep(1)
                    continue
                raise

    def log_error(self, url: str, error_type: str, message: str):
        """Log an error for later review."""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("""
                    INSERT INTO errors (url, error_type, error_message)
                    VALUES (?, ?, ?)
                """, (url, error_type, message))
        except sqlite3.OperationalError:
            pass  # Don't fail on error logging

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
            downloaded = conn.execute("SELECT COUNT(*) FROM stories WHERE downloaded = 1").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            by_category = conn.execute("""
                SELECT category, COUNT(*) as total, SUM(downloaded) as done
                FROM stories GROUP BY category
            """).fetchall()

            return {
                "total_indexed": total,
                "downloaded": downloaded,
                "pending": total - downloaded,
                "errors": errors,
                "by_category": {row[0]: {"total": row[1], "done": row[2]} for row in by_category}
            }

# ============================================================================
# SCRAPER
# ============================================================================

class NiftyScraper:
    """Main scraper class for nifty.org."""

    def __init__(self, config: Dict = CONFIG):
        self.config = config
        self.session = self._create_session()
        self.db = NiftyDatabase(config["db_path"])
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

    def _generate_id(self, url: str) -> str:
        """Generate unique ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()

    # ========================================================================
    # INDEXING
    # ========================================================================

    def index_category(self, category: str) -> int:
        """Index all stories in a category."""
        self.logger.info(f"Indexing category: {category}")

        base_url = f"{self.config['base_url']}{self.config['gay_index']}{category}/"
        stories_found = 0
        page_url = base_url

        while page_url:
            html = self._fetch_page(page_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")

            # Find story links in the table
            for row in soup.select(".ftr"):
                cells = row.select("div")
                if len(cells) >= 3:
                    # Parse: size | date | title link
                    size_text = cells[0].get_text(strip=True)
                    date_text = cells[1].get_text(strip=True)

                    link = cells[2].find("a")
                    if link and link.get("href"):
                        href = link["href"]
                        title = link.get_text(strip=True)

                        # Determine if it's a series (directory)
                        is_series = href.endswith("/") or size_text.lower() == "dir"

                        # Build full URL
                        if not href.startswith("http"):
                            story_url = f"{self.config['base_url']}{self.config['gay_index']}{category}/{href}"
                        else:
                            story_url = href

                        # Parse file size
                        file_size = None
                        if not is_series and size_text:
                            try:
                                file_size = int(float(size_text.replace("K", "")) * 1024)
                            except ValueError:
                                pass

                        # Create metadata
                        story = StoryMetadata(
                            id=self._generate_id(story_url),
                            url=story_url,
                            category=category,
                            title=title,
                            author=None,  # Will be extracted from content
                            author_email=None,
                            date_published=date_text,
                            file_size=file_size,
                            is_series=is_series,
                            series_name=title if is_series else None,
                            part_number=None,
                            word_count=None,
                            downloaded=False,
                            download_date=None,
                            file_path=None
                        )

                        if self.db.add_story(story):
                            stories_found += 1

            # Find next page link (jscroll pagination)
            next_link = soup.select_one("a.jscroll-next")
            if next_link and next_link.get("href"):
                next_href = next_link["href"]
                if not next_href.startswith("http"):
                    # Pagination is relative to current category URL
                    if next_href.startswith("/"):
                        page_url = f"{self.config['base_url']}{next_href}"
                    else:
                        # Relative path - append to base_url + category path
                        page_url = f"{base_url}{next_href}"
                else:
                    page_url = next_href
            else:
                page_url = None

            self.logger.info(f"  {category}: {stories_found} stories indexed so far...")

        self.logger.info(f"Completed {category}: {stories_found} stories indexed")
        return stories_found

    def index_series(self, series_url: str, series_name: str, category: str) -> int:
        """Index all parts in a series directory."""
        self.logger.info(f"Indexing series: {series_name}")

        html = self._fetch_page(series_url)
        if not html:
            return 0

        soup = BeautifulSoup(html, "html.parser")
        parts_found = 0

        for row in soup.select(".ftr"):
            cells = row.select("div")
            if len(cells) >= 3:
                link = cells[2].find("a")
                if link and link.get("href"):
                    href = link["href"]
                    title = link.get_text(strip=True)

                    # Skip parent directory links
                    if href == "../" or href.startswith(".."):
                        continue

                    # Skip directories within series
                    if href.endswith("/"):
                        continue

                    # Build URL
                    story_url = f"{series_url}{href}"

                    # Try to extract part number from title
                    part_match = re.search(r'(?:part|chapter|ch)?[\s\-_]*(\d+)', title, re.I)
                    part_number = int(part_match.group(1)) if part_match else parts_found + 1

                    story = StoryMetadata(
                        id=self._generate_id(story_url),
                        url=story_url,
                        category=category,
                        title=f"{series_name} - {title}",
                        author=None,
                        author_email=None,
                        date_published=cells[1].get_text(strip=True) if len(cells) > 1 else None,
                        file_size=None,
                        is_series=False,
                        series_name=series_name,
                        part_number=part_number,
                        word_count=None,
                        downloaded=False,
                        download_date=None,
                        file_path=None
                    )

                    if self.db.add_story(story):
                        parts_found += 1

        return parts_found

    def index_all_categories(self) -> Dict[str, int]:
        """Index all gay male categories."""
        results = {}
        for category in GAY_CATEGORIES:
            try:
                count = self.index_category(category)
                results[category] = count
            except Exception as e:
                self.logger.error(f"Error indexing {category}: {e}")
                results[category] = -1
        return results

    # ========================================================================
    # DOWNLOADING
    # ========================================================================

    def analyze_content(self, text: str) -> Dict:
        """Analyze story content for enhanced metadata."""
        analysis = {
            "character_count": 2,  # default assumption
            "has_dialogue": False,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "setting": None,
            "quality_score": 0.5
        }

        text_lower = text.lower()

        # Detect dialogue
        dialogue_markers = text.count('"') + text.count("'")
        analysis["has_dialogue"] = dialogue_markers > 20

        # Detect POV
        first_person_markers = len(re.findall(r'\bI\b', text)) + len(re.findall(r'\bmy\b', text_lower))
        third_person_markers = len(re.findall(r'\bhe\b', text_lower)) + len(re.findall(r'\bhis\b', text_lower))
        if first_person_markers > third_person_markers * 1.5:
            analysis["pov"] = "first-person"

        # Estimate character count from unique names/pronouns patterns
        # Simple heuristic: look for capitalized words in dialogue attribution
        name_pattern = re.findall(r'(?:said|asked|replied|whispered|moaned|groaned)\s+([A-Z][a-z]+)', text)
        unique_names = set(name_pattern)
        if len(unique_names) >= 2:
            analysis["character_count"] = len(unique_names)

        # Content intensity based on explicit terms frequency
        mild_terms = ["kiss", "touch", "hold", "embrace", "caress"]
        moderate_terms = ["naked", "hard", "stroke", "moan", "erect"]
        explicit_terms = ["cock", "dick", "fuck", "ass", "cum", "suck", "thrust"]

        mild_count = sum(text_lower.count(t) for t in mild_terms)
        moderate_count = sum(text_lower.count(t) for t in moderate_terms)
        explicit_count = sum(text_lower.count(t) for t in explicit_terms)

        if explicit_count > 10:
            analysis["content_intensity"] = "explicit"
        elif moderate_count > 5 or explicit_count > 3:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Relationship type detection
        relationship_markers = {
            "friends": ["friend", "buddy", "pal", "roommate", "knew him"],
            "strangers": ["stranger", "never met", "first time seeing", "didn't know"],
            "authority": ["boss", "coach", "teacher", "professor", "officer", "sir"],
            "family": ["brother", "cousin", "uncle", "dad", "father", "son"],
            "romantic": ["boyfriend", "lover", "dating", "relationship", "love you"],
        }
        for rel_type, markers in relationship_markers.items():
            if any(m in text_lower for m in markers):
                analysis["relationship_type"] = rel_type
                break

        # Setting detection
        setting_markers = {
            "bedroom": ["bed", "bedroom", "sheets", "pillow"],
            "dorm": ["dorm", "roommate", "campus", "college room"],
            "locker room": ["locker", "shower", "gym", "bench"],
            "office": ["office", "desk", "work", "cubicle"],
            "outdoors": ["woods", "beach", "park", "outside", "tent", "camping"],
            "car": ["car", "backseat", "truck", "parking"],
            "military": ["barracks", "base", "deployment", "uniform"],
        }
        for setting, markers in setting_markers.items():
            if any(m in text_lower for m in markers):
                analysis["setting"] = setting
                break

        # Quality score heuristics
        score = 0.5
        word_count = len(text.split())

        # Longer stories tend to be more developed
        if word_count > 3000:
            score += 0.1
        if word_count > 6000:
            score += 0.1

        # Dialogue indicates character development
        if analysis["has_dialogue"]:
            score += 0.1

        # Multiple characters = more complex
        if analysis["character_count"] >= 2:
            score += 0.1

        # Penalize very short stories
        if word_count < 1000:
            score -= 0.2

        analysis["quality_score"] = min(1.0, max(0.0, score))

        return analysis

    def parse_story_content(self, html: str) -> Dict:
        """Parse story content from email-style OR HTML format."""
        result = {
            "author": None,
            "author_email": None,
            "date": None,
            "title": None,
            "text": "",
            "word_count": 0
        }

        # Detect if this is HTML format (has <p> or <html> tags)
        is_html = bool(re.search(r'<(html|p|body|div)\b', html, re.I))

        if is_html:
            # Parse as HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            if title_tag:
                result["title"] = title_tag.get_text(strip=True)

            # Try to find author from h5 or similar
            author_tag = soup.find("h5")
            if author_tag:
                author_text = author_tag.get_text(strip=True)
                if author_text.lower().startswith("by "):
                    result["author"] = author_text[3:].strip()
                else:
                    result["author"] = author_text

            # Extract all paragraph/div text
            paragraphs = []
            for elem in soup.find_all(["p", "div"]):
                # Skip divs that contain other divs (container elements)
                if elem.name == "div" and elem.find("div"):
                    continue
                text = elem.get_text(strip=True)
                # Skip donation notices and disclaimers
                text_lower = text.lower()
                if "donate" in text_lower and "nifty" in text_lower:
                    continue
                if "disclaimer" in text_lower:
                    continue
                if len(text) < 10:  # Skip very short fragments
                    continue
                if text:
                    paragraphs.append(text)

            result["text"] = "\n\n".join(paragraphs)
            result["word_count"] = len(result["text"].split())

        else:
            # Parse as plain text email format
            lines = html.split("\n")
            content_start = 0

            # Parse email headers
            for i, line in enumerate(lines):
                if line.startswith("From:"):
                    match = re.match(r'From:\s*(.+?)\s*<([^>]+)>', line)
                    if match:
                        result["author"] = match.group(1).strip()
                        result["author_email"] = match.group(2).strip()
                    else:
                        result["author"] = line.replace("From:", "").strip()
                elif line.startswith("Date:"):
                    result["date"] = line.replace("Date:", "").strip()
                elif line.startswith("Subject:"):
                    result["title"] = line.replace("Subject:", "").strip()
                elif line.strip() == "" and i > 0:
                    content_start = i + 1
                    break

            content_lines = lines[content_start:]

            # Skip donation notices
            skip_until = 0
            for i, line in enumerate(content_lines[:20]):
                line_lower = line.lower()
                if "donate" in line_lower and "nifty" in line_lower:
                    for j in range(i, min(i + 5, len(content_lines))):
                        if content_lines[j].strip() == "":
                            skip_until = j + 1
                            break
                    break

            content_lines = content_lines[skip_until:]

            # Find end promo content
            promo_markers = [
                "if you want to read", "if you enjoyed this",
                "support nifty", "patreon", "send feedback",
                "comments to:", "the end"
            ]

            content_end = len(content_lines)
            for i in range(len(content_lines) - 1, max(0, len(content_lines) - 30), -1):
                line_lower = content_lines[i].lower().strip()
                if any(marker in line_lower for marker in promo_markers):
                    content_end = i
                    break

            text = "\n".join(content_lines[:content_end]).strip()
            text = re.sub(r'\n{3,}', '\n\n', text)

            result["text"] = text
            result["word_count"] = len(text.split())

        return result

    def download_story(self, story: StoryMetadata) -> bool:
        """Download and save a single story."""
        if story.is_series:
            # For series, index the parts first
            self.index_series(story.url, story.title, story.category)
            return True

        html = self._fetch_page(story.url)
        if not html:
            return False

        # Parse content
        parsed = self.parse_story_content(html)

        if not parsed["text"] or parsed["word_count"] < 100:
            self.logger.warning(f"Skipping {story.url}: insufficient content ({parsed['word_count']} words)")
            self.db.log_error(story.url, "insufficient_content", f"{parsed['word_count']} words")
            return False

        # Update story metadata
        story.author = parsed["author"] or story.author
        story.author_email = parsed["author_email"]
        story.word_count = parsed["word_count"]

        # Create directory structure
        category_dir = os.path.join(self.config["storage_root"], "stories", story.category)
        os.makedirs(category_dir, exist_ok=True)

        # Generate filename
        safe_title = re.sub(r'[^\w\-_]', '_', story.title)[:100]
        filename = f"{story.id}_{safe_title}.json"
        file_path = os.path.join(category_dir, filename)

        # Analyze content for enhanced metadata
        analysis = self.analyze_content(parsed["text"])

        # Build tags from analysis
        tags = [story.category, "gay", "male"]
        if analysis["content_intensity"]:
            tags.append(analysis["content_intensity"])
        if analysis["relationship_type"]:
            tags.append(analysis["relationship_type"])
        if analysis["setting"]:
            tags.append(analysis["setting"])
        if analysis["pov"]:
            tags.append(analysis["pov"])

        # Create training example with enhanced metadata
        training_example = TrainingExample(
            id=story.id,
            source="nifty",
            category=story.category,
            title=parsed["title"] or story.title,
            author=parsed["author"] or "Anonymous",
            text=parsed["text"],
            word_count=parsed["word_count"],
            tags=tags,
            character_count=analysis["character_count"],
            has_dialogue=analysis["has_dialogue"],
            pov=analysis["pov"],
            content_intensity=analysis["content_intensity"],
            relationship_type=analysis["relationship_type"],
            setting=analysis["setting"],
            quality_score=analysis["quality_score"]
        )

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(training_example), f, indent=2, ensure_ascii=False)

        # Update database
        self.db.mark_downloaded(story.id, file_path, parsed["word_count"])

        self.logger.info(f"Downloaded: {story.title} ({parsed['word_count']} words)")
        return True

    def download_pending(self, category: Optional[str] = None, limit: int = 1000):
        """Download pending stories."""
        pending = self.db.get_pending_stories(category, limit)
        self.logger.info(f"Found {len(pending)} pending stories")

        success = 0
        failed = 0

        for i, story in enumerate(pending):
            try:
                if self.download_story(story):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                self.logger.error(f"Error downloading {story.url}: {e}")
                self.db.log_error(story.url, "download_error", str(e))
                failed += 1

            # Checkpoint
            if (i + 1) % self.config["checkpoint_interval"] == 0:
                stats = self.db.get_stats()
                self.logger.info(f"Checkpoint: {stats['downloaded']}/{stats['total_indexed']} downloaded")

        return {"success": success, "failed": failed}

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_training_data(self, output_path: str, min_word_count: int = 500):
        """Export all stories as a single training JSONL file."""
        self.logger.info(f"Exporting training data to {output_path}")

        stories_dir = os.path.join(self.config["storage_root"], "stories")
        exported = 0

        with open(output_path, "w", encoding="utf-8") as out:
            for category in os.listdir(stories_dir):
                category_path = os.path.join(stories_dir, category)
                if not os.path.isdir(category_path):
                    continue

                for filename in os.listdir(category_path):
                    if not filename.endswith(".json"):
                        continue

                    file_path = os.path.join(category_path, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        if data.get("word_count", 0) >= min_word_count:
                            out.write(json.dumps(data, ensure_ascii=False) + "\n")
                            exported += 1
                    except Exception as e:
                        self.logger.error(f"Error reading {file_path}: {e}")

        self.logger.info(f"Exported {exported} stories to {output_path}")
        return exported

# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Nifty.org Story Ripper")
    parser.add_argument("command", choices=["index", "download", "export", "stats"],
                       help="Command to run")
    parser.add_argument("--category", "-c", help="Specific category to process")
    parser.add_argument("--limit", "-l", type=int, default=1000,
                       help="Maximum stories to download")
    parser.add_argument("--output", "-o", help="Output path for export")
    parser.add_argument("--min-words", type=int, default=500,
                       help="Minimum word count for export")

    args = parser.parse_args()

    try:
        scraper = NiftyScraper()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Please ensure the external drive is mounted.")
        return 1

    if args.command == "index":
        if args.category:
            count = scraper.index_category(args.category)
            print(f"Indexed {count} stories in {args.category}")
        else:
            results = scraper.index_all_categories()
            total = sum(v for v in results.values() if v > 0)
            print(f"Indexed {total} stories across {len(results)} categories")

    elif args.command == "download":
        results = scraper.download_pending(args.category, args.limit)
        print(f"Downloaded: {results['success']}, Failed: {results['failed']}")

    elif args.command == "export":
        output = args.output or os.path.join(
            scraper.config["storage_root"],
            "training_data.jsonl"
        )
        count = scraper.export_training_data(output, args.min_words)
        print(f"Exported {count} stories to {output}")

    elif args.command == "stats":
        stats = scraper.db.get_stats()
        print(f"\nNifty Archive Statistics:")
        print(f"  Total indexed: {stats['total_indexed']}")
        print(f"  Downloaded: {stats['downloaded']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Errors: {stats['errors']}")
        print(f"\nBy Category:")
        for cat, info in stats['by_category'].items():
            print(f"  {cat}: {info['done']}/{info['total']}")

    return 0

if __name__ == "__main__":
    exit(main())
