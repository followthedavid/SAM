#!/usr/bin/env python3
"""
F-List Character & Roleplay Log Scraper
Target: Public character profiles and roleplay logs
Storage: External drives only
Output: Actual roleplay format training data

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
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_url": "https://www.f-list.net",
    "storage_root": "/Volumes/David External/flist_archive",
    "db_path": "/Volumes/David External/flist_archive/flist_index.db",
    "rate_limit_seconds": 2.0,
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
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
            content_path TEXT
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

    conn.execute("CREATE INDEX IF NOT EXISTS idx_species ON characters(species)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gender ON characters(gender)")

    conn.commit()
    return conn

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

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("flist")
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
                time.sleep(5)
                return self._fetch(url, retries + 1)
            return None

    def _fetch_json(self, url: str, data: dict = None) -> Optional[dict]:
        """Fetch JSON API endpoint."""
        self._rate_limit()

        try:
            if data:
                resp = self.session.post(url, data=data, timeout=30)
            else:
                resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"API error: {e}")
            return None

    def search_characters(self, names_file: str = None, **filters) -> List[str]:
        """Search for character names.

        F-List's browse/search endpoints now require authentication.
        Options:
        1. Provide a file with character names to fetch
        2. Use known character names from other sources
        3. Login with F-List account (not implemented)
        """
        characters = []

        # Option 1: Load from file if provided
        if names_file and os.path.exists(names_file):
            with open(names_file, 'r') as f:
                for line in f:
                    name = line.strip()
                    if name and not name.startswith('#'):
                        characters.append(name)
            self.logger.info(f"Loaded {len(characters)} character names from {names_file}")
            return characters

        # Option 2: Try to get characters from kink list (which is public)
        # and any character references we can find
        self.logger.info("F-List character search requires authentication.")
        self.logger.info("Provide a file with character names using --names flag")
        self.logger.info("Or use: python flist_ripper.py index --names characters.txt")

        return characters

    def fetch_character(self, name: str) -> Optional[FListCharacter]:
        """Fetch a character profile."""
        url = f"{CONFIG['base_url']}/c/{name}"
        soup = self._fetch(url)

        if not soup:
            return None

        try:
            # Check if profile exists and is public
            error = soup.select_one('.error-message, .profile-error')
            if error:
                return None

            # Basic info
            info_section = soup.select_one('.character-info, #profile-info')

            species = ""
            gender = ""
            orientation = ""

            # Parse info fields
            info_items = soup.select('.info-field, .profile-field, dt')
            for item in info_items:
                label = item.get_text(strip=True).lower()
                value_elem = item.find_next('dd') or item.find_next_sibling()
                if value_elem:
                    value = value_elem.get_text(strip=True)

                    if 'species' in label:
                        species = value
                    elif 'gender' in label:
                        gender = value
                    elif 'orientation' in label:
                        orientation = value

            # Description
            desc_elem = soup.select_one('.character-description, #character-description, .profile-description')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Personality (custom field often used)
            personality = ""
            personality_elem = soup.select_one('[data-field="personality"], .personality')
            if personality_elem:
                personality = personality_elem.get_text(strip=True)

            # Kinks - F-List organizes these by category
            kinks_fave = []
            kinks_yes = []
            kinks_maybe = []
            kinks_no = []

            kink_sections = soup.select('.kink-group, .kinks-section')
            for section in kink_sections:
                header = section.select_one('h3, .kink-header')
                if header:
                    header_text = header.get_text(strip=True).lower()
                    kink_items = section.select('.kink-item, li')
                    kink_names = [k.get_text(strip=True) for k in kink_items]

                    if 'fave' in header_text or 'favorite' in header_text:
                        kinks_fave.extend(kink_names)
                    elif 'yes' in header_text:
                        kinks_yes.extend(kink_names)
                    elif 'maybe' in header_text:
                        kinks_maybe.extend(kink_names)
                    elif 'no' in header_text:
                        kinks_no.extend(kink_names)

            # Custom fields (scenario ideas, etc)
            customs = {}
            custom_sections = soup.select('.custom-field, .infotag-group')
            for section in custom_sections:
                title = section.select_one('.field-title, h4')
                content = section.select_one('.field-content, .infotag-content')
                if title and content:
                    customs[title.get_text(strip=True)] = content.get_text(strip=True)

            # Images
            images = []
            img_elems = soup.select('.character-image img, .profile-image img')
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
                personality=personality,
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
        """Index multiple characters."""
        self.logger.info(f"Indexing {len(names)} characters...")

        for i, name in enumerate(names, 1):
            self.logger.info(f"[{i}/{len(names)}] {name}")

            char = self.fetch_character(name)
            if char:
                self._save_character(char)

            if i % 50 == 0:
                self.logger.info(f"Progress: {i}/{len(names)}")

    def export_for_training(self, output_path: str, min_desc_length: int = 200):
        """Export character data in training format."""
        cursor = self.conn.execute("""
            SELECT * FROM characters
            WHERE LENGTH(description) >= ?
        """, (min_desc_length,))

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        training_data = []

        for row in cursor:
            # Create character card format
            char_card = {
                "name": row['name'],
                "species": row['species'],
                "gender": row['gender'],
                "orientation": row['orientation'],
                "description": row['description'],
                "personality": row['personality'],
                "kinks": {
                    "favorites": json.loads(row['kinks_fave'] or '[]'),
                    "yes": json.loads(row['kinks_yes'] or '[]'),
                    "maybe": json.loads(row['kinks_maybe'] or '[]'),
                    "no": json.loads(row['kinks_no'] or '[]'),
                },
                "customs": json.loads(row['customs'] or '{}'),
            }

            # Create training prompt format
            training_entry = {
                "system": f"You are {row['name']}, a {row['gender']} {row['species']}. {row['description'][:500]}",
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
# BLUE MOON FORUM SCRAPER
# ============================================================================

class BlueMoonScraper:
    """Scraper for Blue Moon Roleplaying forum."""

    def __init__(self):
        self.base_url = "https://bluemoonroleplaying.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = logging.getLogger("bluemoon")
        self.last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        self.last_request = time.time()

    def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        self._rate_limit()
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return None

    def scrape_thread(self, thread_url: str) -> Optional[RoleplayLog]:
        """Scrape a roleplay thread."""
        soup = self._fetch(thread_url)
        if not soup:
            return None

        try:
            # Title
            title_elem = soup.select_one('h1.p-title-value, .thread-title')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Posts
            posts = soup.select('.message-body, .post-content, article.message')

            participants = set()
            content_parts = []
            turn_count = 0

            for post in posts:
                # Get author
                author_elem = post.find_previous('a', class_='username') or \
                              post.select_one('.message-name a')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"
                participants.add(author)

                # Get content
                content_elem = post.select_one('.bbWrapper, .message-content')
                if content_elem:
                    text = content_elem.get_text(strip=True)
                    if text:
                        content_parts.append(f"[{author}]:\n{text}\n\n")
                        turn_count += 1

            full_content = ''.join(content_parts)

            return RoleplayLog(
                id=hashlib.md5(thread_url.encode()).hexdigest()[:16],
                title=title,
                participants=list(participants),
                content=full_content,
                word_count=len(full_content.split()),
                turn_count=turn_count,
                source_url=thread_url,
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_log(self, log: RoleplayLog):
        """Save roleplay log to database."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO logs (
                    id, title, participants, content, word_count,
                    turn_count, source_url, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.id, log.title, json.dumps(log.participants),
                log.content, log.word_count, log.turn_count,
                log.source_url, log.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="F-List/Blue Moon Scraper")
    parser.add_argument('command', choices=['search', 'index', 'export', 'stats'])
    parser.add_argument('--names', nargs='+', help='Character names to index')
    parser.add_argument('--output', default=CONFIG["storage_root"], help='Output directory')

    args = parser.parse_args()

    scraper = FListScraper()

    if args.command == 'search':
        chars = scraper.search_characters()
        print(f"Found {len(chars)} characters")
        for c in chars[:20]:
            print(f"  - {c}")

    elif args.command == 'index':
        if args.names:
            scraper.index_characters(args.names)
        else:
            # Search and index
            chars = scraper.search_characters()
            scraper.index_characters(chars[:100])  # Start with first 100

    elif args.command == 'export':
        count = scraper.export_for_training(args.output)
        print(f"Exported {count} characters")

    elif args.command == 'stats':
        cursor = scraper.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT species) as species_count,
                AVG(LENGTH(description)) as avg_desc_len
            FROM characters
        """)
        stats = cursor.fetchone()

        print("\n🎭 F-List Archive Stats")
        print("=" * 40)
        print(f"Total characters: {stats['total']:,}")
        print(f"Unique species:   {stats['species_count']:,}")
        print(f"Avg description:  {int(stats['avg_desc_len'] or 0):,} chars")

if __name__ == "__main__":
    main()
