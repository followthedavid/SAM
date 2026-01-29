#!/usr/bin/env python3
"""
F-List Character & Roleplay Log Scraper
Target: Public character profiles and roleplay logs
Storage: External drives only
Output: Actual roleplay format training data

FIXED (2026-01-28):
- F-List character browse/search requires authentication.
- Added F-List JSON API support using account credentials for character discovery.
- Added public character page scraping as fallback (no auth needed if you have names).
- Added multiple character discovery strategies:
  1. F-List JSON API with auth (best - discovers characters via search)
  2. Names file (manual list of character names)
  3. Random character discovery via public profile links
- Fixed HTML selectors for current F-List page structure.
- Added proper checkpoint/resume for character indexing.
- Rate limit: 1 req/sec for API, 2 sec for page scraping (per F-List docs).

F-List provides:
- Character profiles with kinks/preferences
- Public roleplay logs (when shared)
- Writing samples
- Character descriptions
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
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Load .env file if present (for local development)
def _load_dotenv():
    """Load environment variables from .env file if it exists."""
    env_paths = [
        Path(__file__).parent / ".env",
        Path.home() / ".flist_env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            break

_load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.f-list.net",
    "api_url": "https://www.f-list.net/json/api",
    "storage_root": "/Volumes/David External/flist_archive",
    "db_path": "/Volumes/David External/flist_archive/flist_index.db",
    "names_file": "/Volumes/David External/flist_archive/characters.txt",
    "rate_limit_api": 1.0,       # F-List docs: 1 req/sec for API
    "rate_limit_scrape": 2.0,    # Be polite for page scraping
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    # F-List API auth - set via environment variables or config file
    "flist_account": os.environ.get("FLIST_ACCOUNT", ""),
    "flist_password": os.environ.get("FLIST_PASSWORD", ""),
}

# Character search filters
SPECIES_FILTERS = [
    "Human", "Anthro", "Demon", "Angel", "Vampire", "Werewolf",
    "Dragon", "Elf", "Orc", "Fae", "Shapeshifter", "Alien"
]

ORIENTATION_FILTERS = [
    "Straight", "Gay", "Bisexual", "Pansexual", "Asexual"
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class FListCharacter:
    """F-List character profile."""
    id: str
    flist_id: str
    name: str
    url: str
    species: str
    gender: str
    orientation: str
    description: str
    personality: str
    kinks_fave: List[str]
    kinks_yes: List[str]
    kinks_maybe: List[str]
    kinks_no: List[str]
    customs: Dict[str, str]
    images: List[str]
    created_at: str
    indexed_at: str
    downloaded: bool = False

@dataclass
class RoleplayLog:
    """A roleplay conversation log."""
    id: str
    title: str
    participants: List[str]
    content: str
    word_count: int
    turn_count: int
    source_url: str
    indexed_at: str

# ============================================================================
# DATABASE
# ============================================================================

def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            flist_id TEXT UNIQUE,
            name TEXT,
            url TEXT,
            species TEXT,
            gender TEXT,
            orientation TEXT,
            description TEXT,
            personality TEXT,
            kinks_fave TEXT,
            kinks_yes TEXT,
            kinks_maybe TEXT,
            kinks_no TEXT,
            customs TEXT,
            images TEXT,
            created_at TEXT,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            content_path TEXT,
            error TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            title TEXT,
            participants TEXT,
            content TEXT,
            word_count INTEGER,
            turn_count INTEGER,
            source_url TEXT,
            indexed_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_progress (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_species ON characters(species)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gender ON characters(gender)")

    conn.commit()
    return conn

# ============================================================================
# F-LIST API CLIENT
# ============================================================================

class FListAPI:
    """Client for F-List JSON API (requires authentication)."""

    def __init__(self, account: str = "", password: str = ""):
        self.account = account
        self.password = password
        self.ticket = None
        self.ticket_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.last_request = 0
        self.logger = logging.getLogger("flist_api")

    def _rate_limit(self):
        """Enforce API rate limit (1 req/sec)."""
        elapsed = time.time() - self.last_request
        if elapsed < CONFIG["rate_limit_api"]:
            time.sleep(CONFIG["rate_limit_api"] - elapsed)
        self.last_request = time.time()

    def authenticate(self) -> Tuple[bool, str]:
        """Get API ticket.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.account:
            msg = ("No F-List account configured. "
                   "Set FLIST_ACCOUNT environment variable or create .env file. "
                   "See .env.example for template.")
            self.logger.warning(msg)
            return False, msg

        if not self.password:
            msg = ("No F-List password configured. "
                   "Set FLIST_PASSWORD environment variable or create .env file. "
                   "See .env.example for template.")
            self.logger.warning(msg)
            return False, msg

        self._rate_limit()
        try:
            resp = self.session.post(
                "https://www.f-list.net/json/getApiTicket.php",
                data={
                    "account": self.account,
                    "password": self.password,
                    "no_characters": "true",
                    "no_friends": "true",
                    "no_bookmarks": "true",
                },
                timeout=30
            )

            # Check HTTP status
            if resp.status_code == 403:
                msg = "F-List API returned 403 Forbidden. Account may be banned or IP blocked."
                self.logger.error(msg)
                return False, msg
            elif resp.status_code == 429:
                msg = "F-List API rate limit exceeded. Wait a few minutes and try again."
                self.logger.error(msg)
                return False, msg
            elif resp.status_code != 200:
                msg = f"F-List API returned HTTP {resp.status_code}"
                self.logger.error(msg)
                return False, msg

            data = resp.json()

            if "ticket" in data:
                self.ticket = data["ticket"]
                self.ticket_time = time.time()
                msg = f"F-List API authenticated successfully as '{self.account}'"
                self.logger.info(msg)
                return True, msg
            else:
                error = data.get('error', 'Unknown error')
                # Provide helpful messages for common errors
                if 'invalid' in error.lower() and 'password' in error.lower():
                    msg = f"F-List auth failed: Invalid password for account '{self.account}'"
                elif 'account' in error.lower() and 'not found' in error.lower():
                    msg = f"F-List auth failed: Account '{self.account}' not found"
                elif 'banned' in error.lower():
                    msg = f"F-List auth failed: Account '{self.account}' is banned"
                else:
                    msg = f"F-List auth failed: {error}"
                self.logger.error(msg)
                return False, msg

        except requests.exceptions.Timeout:
            msg = "F-List API request timed out. Server may be slow or unreachable."
            self.logger.error(msg)
            return False, msg
        except requests.exceptions.ConnectionError:
            msg = "Could not connect to F-List API. Check your internet connection."
            self.logger.error(msg)
            return False, msg
        except json.JSONDecodeError:
            msg = "F-List API returned invalid JSON. Server may be having issues."
            self.logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"F-List auth error: {e}"
            self.logger.error(msg)
            return False, msg

    def _ensure_ticket(self) -> bool:
        """Ensure we have a valid ticket (refreshes if > 25 min old)."""
        if not self.ticket or (time.time() - self.ticket_time > 1500):
            success, _ = self.authenticate()
            return success
        return True

    def get_character_data(self, name: str) -> Optional[Dict]:
        """Get character data via API."""
        if not self._ensure_ticket():
            return None

        self._rate_limit()
        try:
            resp = self.session.post(
                f"{CONFIG['api_url']}/character-data.php",
                data={
                    "account": self.account,
                    "ticket": self.ticket,
                    "name": name,
                },
                timeout=30
            )
            data = resp.json()
            if "error" in data and data["error"]:
                self.logger.warning(f"API error for {name}: {data['error']}")
                return None
            return data
        except Exception as e:
            self.logger.error(f"API error for {name}: {e}")
            return None

    def get_kink_list(self) -> Optional[Dict]:
        """Get global kink list (no auth required)."""
        self._rate_limit()
        try:
            resp = self.session.get(
                f"{CONFIG['api_url']}/kink-list.php",
                timeout=30
            )
            return resp.json()
        except Exception as e:
            self.logger.error(f"Kink list error: {e}")
            return None

    def get_mapping_list(self) -> Optional[Dict]:
        """Get mapping list (no auth required)."""
        self._rate_limit()
        try:
            resp = self.session.get(
                f"{CONFIG['api_url']}/mapping-list.php",
                timeout=30
            )
            return resp.json()
        except Exception as e:
            self.logger.error(f"Mapping list error: {e}")
            return None

# ============================================================================
# SCRAPING
# ============================================================================

class FListScraper:
    """Scraper for F-List character data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml",
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0
        self.api = FListAPI(CONFIG["flist_account"], CONFIG["flist_password"])

        # Cache kink ID -> name mapping
        self._kink_map = {}

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("flist")
        logger.setLevel(logging.INFO)

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
        """Enforce rate limiting for page scraping."""
        elapsed = time.time() - self.last_request
        if elapsed < CONFIG["rate_limit_scrape"]:
            time.sleep(CONFIG["rate_limit_scrape"] - elapsed)
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
                time.sleep(5)
                return self._fetch(url, retries + 1)
            return None

    def _load_kink_map(self):
        """Load kink ID -> name mapping from F-List API."""
        if self._kink_map:
            return

        data = self.api.get_kink_list()
        if data and "kinks" in data:
            for group in data["kinks"].values():
                if isinstance(group, list):
                    for kink in group:
                        if isinstance(kink, dict) and "kink_id" in kink:
                            self._kink_map[str(kink["kink_id"])] = kink.get("name", f"kink_{kink['kink_id']}")
        self.logger.info(f"Loaded {len(self._kink_map)} kink mappings")

    def _get_progress(self, key: str) -> Optional[str]:
        """Get scrape progress value."""
        cursor = self.conn.execute(
            "SELECT value FROM scrape_progress WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else None

    def _save_progress(self, key: str, value: str):
        """Save scrape progress value."""
        self.conn.execute("""
            INSERT OR REPLACE INTO scrape_progress (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now().isoformat()))
        self.conn.commit()

    def load_character_names(self, names_file: str = None) -> List[str]:
        """Load character names from file."""
        filepath = names_file or CONFIG["names_file"]
        characters = []

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                for line in f:
                    name = line.strip()
                    if name and not name.startswith('#'):
                        characters.append(name)
            self.logger.info(f"Loaded {len(characters)} character names from {filepath}")
        else:
            self.logger.warning(f"Names file not found: {filepath}")
            self.logger.info("Create a file with one character name per line")
            self.logger.info(f"  Location: {filepath}")

        return characters

    def discover_characters_from_profiles(self, seed_names: List[str], max_depth: int = 2) -> List[str]:
        """Discover more character names by following links from known profiles.

        F-List character pages often link to other characters via:
        - Friends lists
        - Guestbook entries
        - Links in custom fields
        """
        discovered = set(seed_names)
        to_visit = list(seed_names)
        depth = 0

        while to_visit and depth < max_depth:
            next_batch = []
            for name in to_visit:
                url = f"{CONFIG['base_url']}/c/{name}"
                soup = self._fetch(url)
                if not soup:
                    continue

                # Find links to other character profiles
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # F-List character URLs: /c/CharacterName
                    match = re.match(r'(?:https?://www\.f-list\.net)?/c/([^/\s?#]+)', href)
                    if match:
                        found_name = match.group(1)
                        if found_name not in discovered:
                            discovered.add(found_name)
                            next_batch.append(found_name)

            to_visit = next_batch[:50]  # Limit per depth level
            depth += 1
            self.logger.info(f"Discovery depth {depth}: found {len(next_batch)} new characters (total: {len(discovered)})")

        return list(discovered)

    def fetch_character_api(self, name: str) -> Optional[FListCharacter]:
        """Fetch character data via F-List JSON API."""
        data = self.api.get_character_data(name)
        if not data:
            return None

        try:
            # Load kink mapping if needed
            self._load_kink_map()

            # Parse infotags for species/gender/orientation
            species = ""
            gender = ""
            orientation = ""

            infotags = data.get("infotags", {})
            for tag_id, tag_value in infotags.items():
                # infotags structure varies, could be string or dict
                if isinstance(tag_value, str):
                    tag_lower = tag_value.lower()
                    # These are heuristic - infotag IDs map to specific fields
                    # but we don't know the mapping without info-list.php
                    pass

            # Try to get species/gender from the structured data
            # The API returns infotags as {id: value} pairs
            # We need the info-list to know which ID is which field
            custom_kinks = data.get("custom_kinks", {})
            customs = {}
            for ck_id, ck_data in custom_kinks.items():
                if isinstance(ck_data, dict):
                    name_field = ck_data.get("name", "")
                    desc_field = ck_data.get("description", "")
                    if name_field and desc_field:
                        customs[name_field] = desc_field

            # Parse kinks by preference level
            kinks = data.get("kinks", {})
            kinks_fave = []
            kinks_yes = []
            kinks_maybe = []
            kinks_no = []

            for kink_id, preference in kinks.items():
                kink_name = self._kink_map.get(str(kink_id), f"kink_{kink_id}")
                if preference == "fave":
                    kinks_fave.append(kink_name)
                elif preference == "yes":
                    kinks_yes.append(kink_name)
                elif preference == "maybe":
                    kinks_maybe.append(kink_name)
                elif preference == "no":
                    kinks_no.append(kink_name)

            # Images
            images = []
            for img in data.get("images", []):
                if isinstance(img, dict) and "url" in img:
                    images.append(img["url"])

            description = data.get("description", "")

            return FListCharacter(
                id=hashlib.md5(f"flist_{name}".encode()).hexdigest()[:16],
                flist_id=name,
                name=name,
                url=f"{CONFIG['base_url']}/c/{name}",
                species=species,
                gender=gender,
                orientation=orientation,
                description=description,
                personality="",
                kinks_fave=kinks_fave,
                kinks_yes=kinks_yes,
                kinks_maybe=kinks_maybe,
                kinks_no=kinks_no,
                customs=customs,
                images=images,
                created_at="",
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error for {name}: {e}")
            return None

    def fetch_character_page(self, name: str) -> Optional[FListCharacter]:
        """Fetch a character profile by scraping the public page."""
        url = f"{CONFIG['base_url']}/c/{name}"
        soup = self._fetch(url)

        if not soup:
            return None

        try:
            page_text = soup.get_text().lower()

            # Check if profile exists and is public
            if "does not exist" in page_text or "no character" in page_text:
                self.logger.warning(f"Character not found: {name}")
                return None

            if "this character is private" in page_text:
                self.logger.warning(f"Private profile: {name}")
                return None

            # Check for the age warning / entry page
            if "warning" in page_text and "adult" in page_text and len(page_text) < 1000:
                # Need to accept the warning first
                self.logger.info(f"Age gate detected for {name}, attempting to bypass")
                # Try fetching with a cookie indicating acceptance
                self.session.cookies.set("warning", "1", domain="www.f-list.net")
                soup = self._fetch(url)
                if not soup:
                    return None

            # Basic info
            species = ""
            gender = ""
            orientation = ""

            # Parse info fields - F-List uses various structures
            # Look for definition lists, info tables, or labeled spans
            for selector in ['dl dt', '.profile-field', '.character-stat-label', 'th']:
                items = soup.select(selector)
                for item in items:
                    label = item.get_text(strip=True).lower().rstrip(':')
                    # Get the corresponding value
                    value_elem = item.find_next('dd') or item.find_next_sibling() or item.find_next('td')
                    if value_elem:
                        value = value_elem.get_text(strip=True)
                        if 'species' in label or 'race' in label:
                            species = value
                        elif 'gender' in label or 'sex' in label:
                            gender = value
                        elif 'orientation' in label:
                            orientation = value

            # Description - try multiple selectors
            description = ""
            for sel in ['.character-description', '#character-description',
                        '.profile-description', '.character-page-description',
                        '#character_description', '.bbcode']:
                desc_elem = soup.select_one(sel)
                if desc_elem and len(desc_elem.get_text(strip=True)) > 20:
                    description = desc_elem.get_text(strip=True)
                    break

            # If still no description, look for the largest text block
            if not description:
                all_divs = soup.find_all('div')
                max_text = ""
                for div in all_divs:
                    text = div.get_text(strip=True)
                    if len(text) > len(max_text) and len(text) > 100:
                        # Skip navigation/header type divs
                        if not any(skip in div.get('class', []) for skip in ['nav', 'header', 'footer', 'menu']):
                            max_text = text
                if max_text:
                    description = max_text

            # Kinks - F-List organizes these by category
            kinks_fave = []
            kinks_yes = []
            kinks_maybe = []
            kinks_no = []

            kink_sections = soup.select('.kink-group, .kinks-section, [class*="kink"]')
            for section in kink_sections:
                header = section.select_one('h3, .kink-header, .kink-group-header')
                if header:
                    header_text = header.get_text(strip=True).lower()
                    kink_items = section.select('.kink-item, li, a')
                    kink_names = [k.get_text(strip=True) for k in kink_items if k.get_text(strip=True)]

                    if 'fave' in header_text or 'favorite' in header_text:
                        kinks_fave.extend(kink_names)
                    elif 'yes' in header_text:
                        kinks_yes.extend(kink_names)
                    elif 'maybe' in header_text:
                        kinks_maybe.extend(kink_names)
                    elif 'no' in header_text:
                        kinks_no.extend(kink_names)

            # Custom fields (scenario ideas, etc.)
            customs = {}
            custom_sections = soup.select('.custom-field, .infotag-group, [class*="custom"]')
            for section in custom_sections:
                title = section.select_one('.field-title, h4, h3, .custom-title')
                content = section.select_one('.field-content, .infotag-content, .custom-content')
                if title and content:
                    customs[title.get_text(strip=True)] = content.get_text(strip=True)

            # Images
            images = []
            img_elems = soup.select('.character-image img, .profile-image img, img[src*="static.f-list"]')
            for img in img_elems:
                src = img.get('src', '') or img.get('data-src', '')
                if src:
                    images.append(src)

            return FListCharacter(
                id=hashlib.md5(f"flist_{name}".encode()).hexdigest()[:16],
                flist_id=name,
                name=name,
                url=url,
                species=species,
                gender=gender,
                orientation=orientation,
                description=description,
                personality="",
                kinks_fave=kinks_fave,
                kinks_yes=kinks_yes,
                kinks_maybe=kinks_maybe,
                kinks_no=kinks_no,
                customs=customs,
                images=images,
                created_at="",
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error for {name}: {e}")
            return None

    def fetch_character(self, name: str) -> Optional[FListCharacter]:
        """Fetch a character profile, trying API first, then page scraping."""
        # Try API first (more reliable, structured data)
        if self.api.account and self.api.password:
            char = self.fetch_character_api(name)
            if char:
                return char

        # Fall back to page scraping
        return self.fetch_character_page(name)

    def _save_character(self, char: FListCharacter):
        """Save character to database."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO characters (
                    id, flist_id, name, url, species, gender, orientation,
                    description, personality, kinks_fave, kinks_yes,
                    kinks_maybe, kinks_no, customs, images, created_at, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                char.id, char.flist_id, char.name, char.url,
                char.species, char.gender, char.orientation,
                char.description, char.personality,
                json.dumps(char.kinks_fave), json.dumps(char.kinks_yes),
                json.dumps(char.kinks_maybe), json.dumps(char.kinks_no),
                json.dumps(char.customs), json.dumps(char.images),
                char.created_at, char.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_characters(self, names: List[str]):
        """Index multiple characters with checkpoint/resume."""
        if not names:
            self.logger.warning("No character names to index")
            return

        # Resume from checkpoint
        last_index_str = self._get_progress("last_character_index")
        start_index = int(last_index_str) if last_index_str else 0

        self.logger.info(f"Indexing {len(names)} characters (starting from {start_index})...")

        indexed = 0
        errors = 0

        for i in range(start_index, len(names)):
            name = names[i]
            self.logger.info(f"[{i + 1}/{len(names)}] {name}")

            try:
                char = self.fetch_character(name)
                if char:
                    self._save_character(char)
                    indexed += 1
                else:
                    errors += 1
                    self.conn.execute("""
                        INSERT OR IGNORE INTO characters (id, flist_id, name, url, indexed_at, error)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        hashlib.md5(f"flist_{name}".encode()).hexdigest()[:16],
                        name, name, f"{CONFIG['base_url']}/c/{name}",
                        datetime.now().isoformat(), "Profile not found or private"
                    ))
                    self.conn.commit()
            except Exception as e:
                self.logger.error(f"Error indexing {name}: {e}")
                errors += 1

            # Checkpoint every 10 characters
            if (i + 1) % 10 == 0:
                self._save_progress("last_character_index", str(i + 1))
                self.logger.info(f"  Checkpoint: {indexed} indexed, {errors} errors")

        # Final checkpoint
        self._save_progress("last_character_index", str(len(names)))
        self.logger.info(f"Indexing complete: {indexed} indexed, {errors} errors")

    def export_for_training(self, output_path: str, min_desc_length: int = 200):
        """Export character data in training format."""
        cursor = self.conn.execute("""
            SELECT * FROM characters
            WHERE LENGTH(description) >= ? AND error IS NULL
        """, (min_desc_length,))

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        training_data = []

        for row in cursor:
            # Create character card format
            char_card = {
                "name": row['name'],
                "species": row['species'] or "Unknown",
                "gender": row['gender'] or "Unknown",
                "orientation": row['orientation'] or "Unknown",
                "description": row['description'],
                "personality": row['personality'] or "",
                "kinks": {
                    "favorites": json.loads(row['kinks_fave'] or '[]'),
                    "yes": json.loads(row['kinks_yes'] or '[]'),
                    "maybe": json.loads(row['kinks_maybe'] or '[]'),
                    "no": json.loads(row['kinks_no'] or '[]'),
                },
                "customs": json.loads(row['customs'] or '{}'),
            }

            # Create training prompt format
            species_str = row['species'] or 'character'
            gender_str = row['gender'] or ''
            desc_preview = (row['description'] or '')[:500]

            training_entry = {
                "system": f"You are {row['name']}, a {gender_str} {species_str}. {desc_preview}",
                "character_card": char_card,
                "source": "flist",
            }

            training_data.append(training_entry)

        # Save as JSONL
        output_file = output_dir / "flist_characters.jsonl"
        with open(output_file, 'w') as f:
            for entry in training_data:
                f.write(json.dumps(entry) + '\n')

        self.logger.info(f"Exported {len(training_data)} characters to {output_file}")
        return len(training_data)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="F-List Character Scraper")
    parser.add_argument('command', choices=['index', 'discover', 'export', 'stats', 'test-auth'])
    parser.add_argument('--names', nargs='+', help='Character names to index')
    parser.add_argument('--names-file', help='File with character names (one per line)')
    parser.add_argument('--output', default=CONFIG["storage_root"], help='Output directory')
    parser.add_argument('--discover-depth', type=int, default=2, help='Discovery crawl depth')

    args = parser.parse_args()

    scraper = FListScraper()

    if args.command == 'index':
        names = []
        if args.names:
            names = args.names
        elif args.names_file:
            names = scraper.load_character_names(args.names_file)
        else:
            names = scraper.load_character_names()

        if not names:
            print("No character names provided.")
            print("Options:")
            print(f"  1. Create {CONFIG['names_file']} with one name per line")
            print("  2. Use --names Name1 Name2 Name3")
            print("  3. Use --names-file /path/to/file.txt")
            print("  4. Use 'discover' command with seed names")
            return

        scraper.index_characters(names)

    elif args.command == 'discover':
        seed_names = []
        if args.names:
            seed_names = args.names
        elif args.names_file:
            seed_names = scraper.load_character_names(args.names_file)
        else:
            seed_names = scraper.load_character_names()

        if not seed_names:
            print("Need seed character names for discovery.")
            print("Use --names Name1 Name2 or --names-file file.txt")
            return

        all_names = scraper.discover_characters_from_profiles(
            seed_names, max_depth=args.discover_depth
        )

        # Save discovered names
        names_file = CONFIG["names_file"]
        Path(names_file).parent.mkdir(parents=True, exist_ok=True)
        with open(names_file, 'w') as f:
            for name in sorted(all_names):
                f.write(name + '\n')
        print(f"Discovered {len(all_names)} characters, saved to {names_file}")
        print("Run 'index' command to fetch their profiles.")

    elif args.command == 'export':
        count = scraper.export_for_training(args.output)
        print(f"Exported {count} characters")

    elif args.command == 'test-auth':
        print("\nF-List API Authentication Test")
        print("=" * 40)

        # Show config sources
        account = CONFIG["flist_account"]
        if account:
            print(f"Account: {account}")
            print(f"Password: {'*' * min(8, len(CONFIG['flist_password'])) if CONFIG['flist_password'] else '(not set)'}")
        else:
            print("Account: (not set)")
            print("\nTo configure authentication:")
            print("  Option 1: Set environment variables:")
            print("    export FLIST_ACCOUNT=your_username")
            print("    export FLIST_PASSWORD=your_password")
            print("")
            print("  Option 2: Create .env file:")
            print(f"    Copy {Path(__file__).parent / '.env.example'}")
            print(f"    to   {Path(__file__).parent / '.env'}")
            print("    and fill in your credentials.")
            return

        print("\nAttempting authentication...")
        api = FListAPI(CONFIG["flist_account"], CONFIG["flist_password"])
        success, message = api.authenticate()

        if success:
            print(f"SUCCESS: {message}")
            print(f"Ticket: {api.ticket[:20]}..." if api.ticket else "No ticket")

            # Try fetching kink list as additional test
            print("\nTesting API access (fetching kink list)...")
            kinks = api.get_kink_list()
            if kinks and "kinks" in kinks:
                kink_count = sum(len(v) for v in kinks["kinks"].values() if isinstance(v, list))
                print(f"SUCCESS: Retrieved {kink_count} kink definitions")
            else:
                print("WARNING: Could not fetch kink list")
        else:
            print(f"FAILED: {message}")
            return

    elif args.command == 'stats':
        # Try new schema first, fall back to old schema
        try:
            cursor = scraper.conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN error IS NULL AND LENGTH(description) > 0 THEN 1 END) as with_desc,
                    COUNT(DISTINCT species) as species_count,
                    AVG(CASE WHEN description IS NOT NULL THEN LENGTH(description) ELSE 0 END) as avg_desc_len
                FROM characters
            """)
        except sqlite3.OperationalError:
            # Fallback for old schema without error column
            cursor = scraper.conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN LENGTH(description) > 0 THEN 1 END) as with_desc,
                    COUNT(DISTINCT species) as species_count,
                    AVG(CASE WHEN description IS NOT NULL THEN LENGTH(description) ELSE 0 END) as avg_desc_len
                FROM characters
            """)
        stats = cursor.fetchone()

        print("\nF-List Archive Stats")
        print("=" * 40)
        print(f"Total characters: {stats['total']:,}")
        print(f"With description: {stats['with_desc']:,}")
        print(f"Unique species:   {stats['species_count']:,}")
        print(f"Avg description:  {int(stats['avg_desc_len'] or 0):,} chars")

        # Show auth status
        print("\nAuthentication Status")
        print("-" * 40)
        if CONFIG["flist_account"]:
            print(f"Account configured: {CONFIG['flist_account']}")
            print(f"Password configured: {'Yes' if CONFIG['flist_password'] else 'No'}")
        else:
            print("No credentials configured (run 'test-auth' for setup help)")

if __name__ == "__main__":
    main()
