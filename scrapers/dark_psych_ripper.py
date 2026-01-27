#!/usr/bin/env python3
"""
Dark Psychology Adult Content Scraper
Target: Manipulation, power dynamics, psychological control in adult fiction
Storage: External drives only
Output: MASSIVE training corpus for dark roleplay dynamics

This is a PRIMARY training category - we want hundreds of thousands of examples.

Sources:
- AO3 (extensive dark tags)
- Literotica (Mind Control, NonConsent)
- CHYOA (interactive dark content)
- Dark romance archives
- Wattpad mature/dark romance
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
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
from urllib.parse import urlencode, quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/dark_psych_archive",
    "db_path": "/Volumes/David External/dark_psych_archive/dark_psych_index.db",
    "rate_limit_ao3": 3.0,  # AO3 is strict
    "rate_limit_lit": 1.5,
    "rate_limit_other": 1.0,
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "pages_per_tag": 500,  # Go DEEP on each tag
    "target_total": 500000,  # Half million stories target
}

# ============================================================================
# DARK PSYCHOLOGY TAGS - COMPREHENSIVE
# ============================================================================

# AO3 Dark Psychology Tags - THE MAIN EVENT
AO3_DARK_TAGS = [
    # Core psychological manipulation
    "Manipulation",
    "Mind Games",
    "Psychological Torture",
    "Psychological Horror",
    "Gaslighting",
    "Mindfuck",
    "Brainwashing",
    "Conditioning",

    # Power and control
    "Power Imbalance",
    "Power Dynamics",
    "Power Play",
    "Control",
    "Controlling Behavior",
    "Dominance",
    "Submission",
    "Master/Slave",
    "Master/Pet",
    "Ownership",

    # Obsession and possession
    "Possessive Behavior",
    "Possessiveness",
    "Obsession",
    "Obsessive Behavior",
    "Obsessive Love",
    "Yandere",
    "Stalking",
    "Jealousy",
    "Jealous",
    "Possessive Sex",

    # Dark relationship dynamics
    "Unhealthy Relationships",
    "Toxic Relationship",
    "Abusive Relationship",
    "Emotional Manipulation",
    "Emotional Abuse",
    "Psychological Abuse",
    "Verbal Abuse",
    "Dark Romance",
    "Fucked Up",

    # Consent spectrum
    "Dubious Consent",
    "Dubcon",
    "Consensual Non-Consent",
    "CNC",
    "Non-Consensual",
    "Rape/Non-con Elements",
    "Coercion",
    "Blackmail",
    "Threats",
    "Intimidation",

    # Captivity and control
    "Captivity",
    "Kidnapping",
    "Imprisonment",
    "Cage",
    "Locked In",
    "Stockholm Syndrome",
    "Lima Syndrome",
    "Captor/Captive",

    # Dark character types
    "Villain",
    "Villain Protagonist",
    "Dark Character",
    "Morally Ambiguous Character",
    "Morally Grey",
    "Anti-Hero",
    "Predator/Prey",
    "Predatory Behavior",

    # Specific dark dynamics
    "Corruption",
    "Innocence",
    "Loss of Innocence",
    "Seduction",
    "Seduction to the Dark Side",
    "Temptation",
    "Breaking",
    "Broken",
    "Training",
    "Pet Play",

    # Warning tags (often the darkest content)
    "Dead Dove: Do Not Eat",
    "Dark",
    "Darkfic",
    "Dark Content",
    "Extremely Dubious Consent",
    "No Happy Ending",
    "Unhappy Ending",
    "Tragedy",
    "Heavy Angst",

    # BDSM psychological
    "Sadism",
    "Masochism",
    "Sadomasochism",
    "Punishment",
    "Degradation",
    "Humiliation",
    "Dehumanization",
    "Objectification",
    "Praise Kink",
    "Fear Play",
    "Edge Play",

    # Mind control specific
    "Mind Control",
    "Hypnotism",
    "Hypnosis",
    "Mind Manipulation",
    "Memory Alteration",
    "Memory Manipulation",
    "Compulsion",
    "Telepathy",

    # Dependency and addiction
    "Emotional Dependency",
    "Codependency",
    "Addiction",
    "Drug Use",
    "Drugged Sex",
    "Intoxication",

    # Isolation tactics
    "Isolation",
    "Social Isolation",
    "Cutting Off From Friends",
    "Alienation",

    # DEEP PSYCHOLOGICAL DAMAGE
    "Psychological Trauma",
    "Trauma",
    "PTSD",
    "Mental Breakdown",
    "Emotional Breakdown",
    "Broken",
    "Breaking",
    "Shattered",
    "Destroyed",
    "Ruined",
    "Grooming",
    "Trauma Bonding",
    "Learned Helplessness",
    "Coercive Control",
    "Emotional Abuse",
    "Verbal Abuse",
    "Lovebombing",
    "Love Bombing",
    "Cycle of Abuse",
    "Abuser POV",
    "Villain POV",
    "No Comfort",
    "Hurt No Comfort",
    "Whump",
    "Dark Whump",
    "Extremely Fucked Up",
    "Author Is Going To Hell",
    "This Is Why We Can't Have Nice Things",
    "Victim Blaming",
    "Self-Blame",
    "Self-Worth Issues",
    "Low Self-Esteem",
    "Worthlessness",
    "Hopelessness",
    "Despair",
    "Giving Up",
    "Surrender",
    "Complete Control",
    "Total Control",
    "Absolute Control",
    "Remade",
    "Reconstruction",
    "Identity Death",
    "Loss of Identity",
    "Who I Was",
    "Empty",
    "Hollow",
    "Shell",
    "Nothing Left",
    "Permanently Changed",
    "Irreversible",
    "Point of No Return",

    # Specific kink tags that involve psychology
    "Breeding",
    "Breeding Kink",
    "Forced Pregnancy",
    "Claiming",
    "Marking",
    "Biting",
    "Mating",
    "Knotting",
    "Alpha/Beta/Omega Dynamics",
    "Alpha/Omega",

    # Age/experience dynamics (legal adults)
    "Age Difference",
    "Experience Difference",
    "Older Man/Younger Woman",
    "Older Woman/Younger Man",
    "Teacher-Student Relationship",
    "Boss/Employee",
    "Authority Figures",

    # Betrayal and trust
    "Betrayal",
    "Trust Issues",
    "Broken Trust",
    "Deception",
    "Lies",
    "Secrets",
    "Cheating",
    "Infidelity",
]

# High-volume fandoms known for dark content
DARK_FANDOMS = [
    "Hannibal (TV)",
    "Killing Eve",
    "You (TV)",
    "Twilight",
    "Fifty Shades",
    "Star Wars",  # Reylo, Kylux
    "Marvel",  # Loki fics
    "Harry Potter",  # Certain pairings
    "Game of Thrones",
    "The Vampire Diaries",
    "True Blood",
    "Supernatural",
    "Lucifer",
    "Good Omens",
    "Sherlock",
    "Criminal Minds",
    "Dexter",
]

# Literotica categories
LITEROTICA_DARK_CATEGORIES = [
    "mind-control",
    "non-consent-stories",
    "bdsm-stories",
    "fetish-stories",
    "erotic-horror",
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class DarkStory:
    """Dark psychology story metadata."""
    id: str
    source: str  # ao3, literotica, chyoa, etc.
    source_id: str
    url: str
    title: str
    author: str

    # Classification
    dark_tags: List[str]
    intensity_score: float  # 0-1 based on tag count/type

    # Content markers
    has_manipulation: bool
    has_power_dynamic: bool
    has_obsession: bool
    has_noncon_elements: bool
    has_captivity: bool
    has_mind_control: bool

    # Metadata
    word_count: int
    rating: str
    warnings: List[str]

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
            source TEXT,
            source_id TEXT,
            url TEXT UNIQUE,
            title TEXT,
            author TEXT,
            dark_tags TEXT,
            intensity_score REAL,
            has_manipulation INTEGER,
            has_power_dynamic INTEGER,
            has_obsession INTEGER,
            has_noncon_elements INTEGER,
            has_captivity INTEGER,
            has_mind_control INTEGER,
            word_count INTEGER,
            rating TEXT,
            warnings TEXT,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0,
            content_path TEXT,
            error TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tag_progress (
            key TEXT PRIMARY KEY,
            source TEXT,
            tag TEXT,
            last_page INTEGER DEFAULT 0,
            total_found INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    # Indexes for fast queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON stories(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intensity ON stories(intensity_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manipulation ON stories(has_manipulation)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_power ON stories(has_power_dynamic)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obsession ON stories(has_obsession)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded ON stories(downloaded)")

    conn.commit()
    return conn

# ============================================================================
# PSYCHOLOGICAL DAMAGE PATTERNS
# ============================================================================

# These are the REAL tactics - the ones that leave lasting damage
# Training data should include authentic examples of these patterns

PSYCHOLOGICAL_DAMAGE_PATTERNS = {
    # Core gaslighting - making them doubt their own reality
    "gaslighting": [
        "that never happened",
        "you're imagining things",
        "you're being crazy",
        "no one will believe you",
        "you're too sensitive",
        "you're overreacting",
        "i never said that",
        "you made me do this",
        "this is your fault",
        "you're remembering it wrong",
    ],

    # Identity destruction - erasing who they are
    "identity_destruction": [
        "you're nothing without me",
        "no one else would want you",
        "you were nothing before me",
        "i made you who you are",
        "you'd be lost without me",
        "who would you even be",
        "everything you are is because of me",
    ],

    # Isolation tactics - cutting off support
    "isolation": [
        "they don't really care about you",
        "your friends are using you",
        "your family never understood you",
        "i'm the only one who truly knows you",
        "they're turning you against me",
        "you don't need anyone else",
        "they're jealous of what we have",
    ],

    # Worthlessness conditioning - breaking self-esteem
    "worthlessness": [
        "you're lucky i put up with you",
        "no one else would tolerate you",
        "you should be grateful",
        "you don't deserve this",
        "you're not good enough",
        "you'll never be good enough",
        "you're broken",
        "something is wrong with you",
    ],

    # Dependency creation - learned helplessness
    "dependency": [
        "you need me",
        "you can't do this without me",
        "you'd fall apart",
        "i'm the only one who understands",
        "i'm doing this for your own good",
        "you can't trust yourself",
        "let me think for you",
        "i know what's best",
    ],

    # Love bombing / withdrawal cycle
    "intermittent_reinforcement": [
        "i love you so much",
        "you're perfect",
        "you're everything to me",
        # then withdrawal, coldness, punishment
        "maybe i was wrong about you",
        "you've changed",
        "you're not the person i fell in love with",
        "i don't know if i can do this anymore",
    ],

    # Blame shifting - they're always at fault
    "blame_shifting": [
        "look what you made me do",
        "if you hadn't...",
        "you pushed me to this",
        "you know what happens when you...",
        "this wouldn't happen if you just...",
        "you bring this on yourself",
    ],

    # Future faking / hope manipulation
    "hope_manipulation": [
        "things will be different",
        "i'm going to change",
        "just give me another chance",
        "it'll never happen again",
        "we're so close to perfect",
        "don't give up on us",
    ],

    # Reality distortion - rewriting history
    "reality_distortion": [
        "that's not what happened",
        "you're confused",
        "i remember it differently",
        "ask anyone, they'll tell you",
        "you always do this",
        "you have a pattern of...",
    ],

    # Threats disguised as concern
    "veiled_threats": [
        "i worry about what would happen to you",
        "i don't know what i'd do if you left",
        "you know i can't live without you",
        "i just want to protect you",
        "the world is dangerous",
        "people will hurt you",
    ],
}

# ============================================================================
# TAG ANALYSIS
# ============================================================================

class DarkTagAnalyzer:
    """Analyze tags to classify dark content."""

    MANIPULATION_KEYWORDS = {
        'manipulation', 'manipulative', 'gaslighting', 'mind games',
        'coercion', 'blackmail', 'threats', 'intimidation', 'deception',
        'lies', 'conditioning', 'brainwashing', 'grooming', 'lovebombing',
        'trauma bonding', 'learned helplessness', 'psychological torture',
        'emotional abuse', 'verbal abuse', 'coercive control'
    }

    POWER_KEYWORDS = {
        'power', 'control', 'dominance', 'submission', 'master', 'slave',
        'pet', 'ownership', 'authority', 'boss', 'teacher', 'student',
        'helpless', 'powerless', 'trapped', 'no escape', 'breaking'
    }

    OBSESSION_KEYWORDS = {
        'obsession', 'obsessive', 'possessive', 'jealous', 'yandere',
        'stalking', 'stalker', 'claiming', 'marking', 'mine', 'belong to me',
        'only mine', 'never leave', 'forever', 'watching'
    }

    NONCON_KEYWORDS = {
        'non-con', 'noncon', 'dubcon', 'dubious consent', 'rape',
        'forced', 'coerced', 'reluctant', 'unwilling', 'no choice',
        'made to', 'had to'
    }

    CAPTIVITY_KEYWORDS = {
        'captivity', 'kidnapping', 'kidnapped', 'imprisonment', 'cage',
        'locked', 'stockholm', 'captor', 'captive', 'prisoner', 'trapped',
        'no escape', 'isolation', 'cut off'
    }

    MIND_CONTROL_KEYWORDS = {
        'mind control', 'hypnosis', 'hypnotism', 'brainwashing',
        'compulsion', 'telepathy', 'memory', 'programming', 'conditioning',
        'breaking', 'remaking', 'blank slate', 'obedience'
    }

    # NEW: Specifically for psychologically devastating content
    DEVASTATING_KEYWORDS = {
        'psychological trauma', 'ptsd', 'breakdown', 'broken',
        'destroyed', 'ruined', 'shattered', 'empty', 'hollow',
        'nothing left', 'dead inside', 'gave up', 'surrender',
        'completely his', 'completely hers', 'owned', 'remade',
        'no longer', 'used to be', 'before', 'what i was'
    }

    @classmethod
    def analyze(cls, tags: List[str]) -> Dict:
        """Analyze tags and return classification."""
        tags_lower = {t.lower() for t in tags}
        tags_text = ' '.join(tags_lower)

        def check_keywords(keywords: Set[str]) -> bool:
            return any(kw in tags_text for kw in keywords)

        has_manipulation = check_keywords(cls.MANIPULATION_KEYWORDS)
        has_power = check_keywords(cls.POWER_KEYWORDS)
        has_obsession = check_keywords(cls.OBSESSION_KEYWORDS)
        has_noncon = check_keywords(cls.NONCON_KEYWORDS)
        has_captivity = check_keywords(cls.CAPTIVITY_KEYWORDS)
        has_mind_control = check_keywords(cls.MIND_CONTROL_KEYWORDS)
        has_devastating = check_keywords(cls.DEVASTATING_KEYWORDS)

        # Calculate intensity score (0-1)
        # Weight devastating content higher
        dark_indicators = [
            has_manipulation, has_power, has_obsession,
            has_noncon, has_captivity, has_mind_control,
            has_devastating,  # Count this
            has_devastating,  # Weight it double
            'dark' in tags_text,
            'dead dove' in tags_text,
            'unhealthy' in tags_text,
            'toxic' in tags_text,
            'abuse' in tags_text,
            'trauma' in tags_text,
            'broken' in tags_text,
            'destroyed' in tags_text,
            'no comfort' in tags_text,
            'hurt no comfort' in tags_text,
            'psychological' in tags_text,
            'gaslighting' in tags_text,
            'grooming' in tags_text,
        ]
        intensity = sum(dark_indicators) / len(dark_indicators)

        return {
            'has_manipulation': has_manipulation,
            'has_power_dynamic': has_power,
            'has_obsession': has_obsession,
            'has_noncon_elements': has_noncon,
            'has_captivity': has_captivity,
            'has_mind_control': has_mind_control,
            'has_devastating': has_devastating,
            'intensity_score': min(intensity * 1.2, 1.0),  # Boost intensity
        }

    @classmethod
    def extract_dark_dialogue(cls, text: str) -> List[Dict]:
        """
        Extract dialogue that contains psychological manipulation patterns.
        Returns list of {speaker, dialogue, pattern_type} dicts.
        """
        extracted = []

        # Find quoted dialogue
        dialogue_pattern = r'"([^"]{10,500})"'
        quotes = re.findall(dialogue_pattern, text)

        for quote in quotes:
            quote_lower = quote.lower()

            # Check against each damage pattern
            for pattern_type, phrases in PSYCHOLOGICAL_DAMAGE_PATTERNS.items():
                for phrase in phrases:
                    if phrase in quote_lower:
                        extracted.append({
                            'dialogue': quote,
                            'pattern_type': pattern_type,
                            'matched_phrase': phrase
                        })
                        break  # One match per quote is enough

        return extracted

    @classmethod
    def score_content_darkness(cls, text: str) -> float:
        """
        Score how dark/devastating the actual content is (not just tags).
        Looks for psychological damage patterns in the text itself.
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        total_matches = 0
        total_patterns = 0

        for pattern_type, phrases in PSYCHOLOGICAL_DAMAGE_PATTERNS.items():
            total_patterns += len(phrases)
            for phrase in phrases:
                if phrase in text_lower:
                    total_matches += 1

        # Also check for devastating keywords in narrative
        devastating_narrative = [
            'broke something in', 'shattered', 'destroyed',
            'nothing left of', 'used to be', 'before this',
            'who i was', 'empty inside', 'hollow', 'gave up',
            'stopped fighting', 'surrendered', 'belonged to',
            'owned', 'remade', 'rebuilt', 'conditioned',
            'trained', 'learned to', 'knew better than to',
            'never again', 'always would', 'forever his',
            'forever hers', 'completely', 'totally', 'absolutely'
        ]

        for phrase in devastating_narrative:
            if phrase in text_lower:
                total_matches += 1
        total_patterns += len(devastating_narrative)

        return min(total_matches / (total_patterns * 0.1), 1.0)

# ============================================================================
# AO3 SCRAPER
# ============================================================================

class AO3DarkScraper:
    """AO3 scraper focused on dark psychology content."""

    def __init__(self, conn: sqlite3.Connection, logger: logging.Logger):
        self.conn = conn
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < CONFIG["rate_limit_ao3"]:
            time.sleep(CONFIG["rate_limit_ao3"] - elapsed)
        self.last_request = time.time()

    def _fetch(self, url: str, retries: int = 0) -> Optional[BeautifulSoup]:
        self._rate_limit()
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 429:
                self.logger.warning("Rate limited, waiting 60s...")
                time.sleep(60)
                return self._fetch(url, retries)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            if retries < CONFIG["max_retries"]:
                time.sleep(10)
                return self._fetch(url, retries + 1)
            return None

    def _parse_work(self, work_elem, tag: str) -> Optional[DarkStory]:
        """Parse a work from AO3 search results."""
        try:
            work_id = work_elem.get('id', '').replace('work_', '')
            if not work_id:
                return None

            # Title and URL
            title_elem = work_elem.select_one('h4.heading a')
            title = title_elem.get_text(strip=True) if title_elem else ""
            url = f"https://archiveofourown.org{title_elem['href']}" if title_elem else ""

            # Author
            author_elem = work_elem.select_one('a[rel="author"]')
            author = author_elem.get_text(strip=True) if author_elem else "Anonymous"

            # Tags
            tag_elems = work_elem.select('li.freeforms a.tag, li.warnings a.tag')
            tags = [t.get_text(strip=True) for t in tag_elems]

            # Rating
            rating_elem = work_elem.select_one('span.rating')
            rating = rating_elem.get_text(strip=True) if rating_elem else ""

            # Warnings
            warning_elems = work_elem.select('li.warnings a.tag')
            warnings = [w.get_text(strip=True) for w in warning_elems]

            # Word count
            wc_elem = work_elem.select_one('dd.words')
            word_count = int(wc_elem.get_text().replace(',', '')) if wc_elem else 0

            # Analyze dark content
            analysis = DarkTagAnalyzer.analyze(tags + [tag])

            # Filter: only keep if has dark elements
            if analysis['intensity_score'] < 0.1:
                return None

            return DarkStory(
                id=hashlib.md5(f"ao3_{work_id}".encode()).hexdigest()[:16],
                source="ao3",
                source_id=work_id,
                url=url,
                title=title,
                author=author,
                dark_tags=tags,
                intensity_score=analysis['intensity_score'],
                has_manipulation=analysis['has_manipulation'],
                has_power_dynamic=analysis['has_power_dynamic'],
                has_obsession=analysis['has_obsession'],
                has_noncon_elements=analysis['has_noncon_elements'],
                has_captivity=analysis['has_captivity'],
                has_mind_control=analysis['has_mind_control'],
                word_count=word_count,
                rating=rating,
                warnings=warnings,
                indexed_at=datetime.now().isoformat(),
            )
        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_story(self, story: DarkStory):
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO stories (
                    id, source, source_id, url, title, author,
                    dark_tags, intensity_score,
                    has_manipulation, has_power_dynamic, has_obsession,
                    has_noncon_elements, has_captivity, has_mind_control,
                    word_count, rating, warnings, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                story.id, story.source, story.source_id, story.url,
                story.title, story.author,
                json.dumps(story.dark_tags), story.intensity_score,
                1 if story.has_manipulation else 0,
                1 if story.has_power_dynamic else 0,
                1 if story.has_obsession else 0,
                1 if story.has_noncon_elements else 0,
                1 if story.has_captivity else 0,
                1 if story.has_mind_control else 0,
                story.word_count, story.rating,
                json.dumps(story.warnings), story.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"DB error: {e}")

    def index_tag(self, tag: str):
        """Index all works for a dark tag."""
        key = f"ao3_{tag}"

        cursor = self.conn.execute(
            "SELECT last_page, completed FROM tag_progress WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"AO3 tag '{tag}' already completed")
            return

        self.logger.info(f"Indexing AO3: {tag} (page {start_page})")

        encoded_tag = quote_plus(tag)
        base_url = f"https://archiveofourown.org/tags/{encoded_tag}/works"

        # Filter for explicit content
        params = {
            "work_search[rating_ids][]": "13",  # Explicit
            "work_search[complete]": "T",
            "work_search[language_id]": "en",
            "work_search[sort_column]": "kudos_count",
            "work_search[sort_direction]": "desc",
        }

        total_found = 0
        page = start_page

        while page <= CONFIG["pages_per_tag"]:
            params["page"] = str(page)
            url = f"{base_url}?{urlencode(params)}"

            soup = self._fetch(url)
            if not soup:
                break

            works = soup.select('li.work.blurb')
            if not works:
                self.conn.execute("""
                    INSERT OR REPLACE INTO tag_progress
                    (key, source, tag, last_page, total_found, completed, updated_at)
                    VALUES (?, 'ao3', ?, ?, ?, 1, ?)
                """, (key, tag, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            for work in works:
                story = self._parse_work(work, tag)
                if story:
                    self._save_story(story)
                    total_found += 1

            self.conn.execute("""
                INSERT OR REPLACE INTO tag_progress
                (key, source, tag, last_page, total_found, completed, updated_at)
                VALUES (?, 'ao3', ?, ?, ?, 0, ?)
            """, (key, tag, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            if total_found % 200 == 0 and total_found > 0:
                self.logger.info(f"  {total_found} stories indexed...")

            page += 1

        self.logger.info(f"AO3 '{tag}': {total_found} stories")

# ============================================================================
# LITEROTICA SCRAPER
# ============================================================================

class LiteroticaDarkScraper:
    """Literotica scraper for dark categories."""

    def __init__(self, conn: sqlite3.Connection, logger: logging.Logger):
        self.conn = conn
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < CONFIG["rate_limit_lit"]:
            time.sleep(CONFIG["rate_limit_lit"] - elapsed)
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

    def index_category(self, category: str):
        """Index a Literotica category."""
        key = f"lit_{category}"

        cursor = self.conn.execute(
            "SELECT last_page, completed FROM tag_progress WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        start_page = (row['last_page'] + 1) if row else 1

        if row and row['completed']:
            self.logger.info(f"Literotica '{category}' already completed")
            return

        self.logger.info(f"Indexing Literotica: {category} (page {start_page})")

        total_found = 0
        page = start_page

        while page <= CONFIG["pages_per_tag"]:
            url = f"https://www.literotica.com/c/{category}/{page}-page"
            soup = self._fetch(url)

            if not soup:
                break

            # Find story cards
            cards = soup.select('.b-story-list-box, .story-list-item, article')

            if not cards:
                self.conn.execute("""
                    INSERT OR REPLACE INTO tag_progress
                    (key, source, tag, last_page, total_found, completed, updated_at)
                    VALUES (?, 'literotica', ?, ?, ?, 1, ?)
                """, (key, category, page, total_found, datetime.now().isoformat()))
                self.conn.commit()
                break

            for card in cards:
                story = self._parse_story(card, category)
                if story:
                    self._save_story(story)
                    total_found += 1

            self.conn.execute("""
                INSERT OR REPLACE INTO tag_progress
                (key, source, tag, last_page, total_found, completed, updated_at)
                VALUES (?, 'literotica', ?, ?, ?, 0, ?)
            """, (key, category, page, total_found, datetime.now().isoformat()))
            self.conn.commit()

            if total_found % 200 == 0 and total_found > 0:
                self.logger.info(f"  {total_found} stories indexed...")

            page += 1

        self.logger.info(f"Literotica '{category}': {total_found} stories")

    def _parse_story(self, card, category: str) -> Optional[DarkStory]:
        """Parse a story card."""
        try:
            link = card.select_one('a[href*="/s/"]')
            if not link:
                return None

            url = link.get('href', '')
            if not url.startswith('http'):
                url = f"https://www.literotica.com{url}"

            title = link.get_text(strip=True)

            # Extract ID from URL
            id_match = re.search(r'/s/([^/]+)', url)
            source_id = id_match.group(1) if id_match else hashlib.md5(url.encode()).hexdigest()[:12]

            # Author
            author_elem = card.select_one('.b-story-user-y a, .author a')
            author = author_elem.get_text(strip=True) if author_elem else ""

            # Set dark tags based on category
            dark_tags = [category]
            if category == "mind-control":
                dark_tags.extend(["Mind Control", "Manipulation"])
            elif category == "non-consent-stories":
                dark_tags.extend(["Non-Consensual", "Dubious Consent"])
            elif category == "bdsm-stories":
                dark_tags.extend(["BDSM", "Power Dynamics"])

            analysis = DarkTagAnalyzer.analyze(dark_tags)

            return DarkStory(
                id=hashlib.md5(f"lit_{source_id}".encode()).hexdigest()[:16],
                source="literotica",
                source_id=source_id,
                url=url,
                title=title,
                author=author,
                dark_tags=dark_tags,
                intensity_score=analysis['intensity_score'],
                has_manipulation=analysis['has_manipulation'],
                has_power_dynamic=analysis['has_power_dynamic'],
                has_obsession=analysis['has_obsession'],
                has_noncon_elements=analysis['has_noncon_elements'],
                has_captivity=analysis['has_captivity'],
                has_mind_control=analysis['has_mind_control'],
                word_count=0,
                rating="Explicit",
                warnings=[],
                indexed_at=datetime.now().isoformat(),
            )
        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None

    def _save_story(self, story: DarkStory):
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO stories (
                    id, source, source_id, url, title, author,
                    dark_tags, intensity_score,
                    has_manipulation, has_power_dynamic, has_obsession,
                    has_noncon_elements, has_captivity, has_mind_control,
                    word_count, rating, warnings, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                story.id, story.source, story.source_id, story.url,
                story.title, story.author,
                json.dumps(story.dark_tags), story.intensity_score,
                1 if story.has_manipulation else 0,
                1 if story.has_power_dynamic else 0,
                1 if story.has_obsession else 0,
                1 if story.has_noncon_elements else 0,
                1 if story.has_captivity else 0,
                1 if story.has_mind_control else 0,
                story.word_count, story.rating,
                json.dumps(story.warnings), story.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"DB error: {e}")

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class DarkPsychScraper:
    """Main orchestrator for dark psychology content scraping."""

    def __init__(self):
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()

        self.ao3_scraper = AO3DarkScraper(self.conn, self.logger)
        self.lit_scraper = LiteroticaDarkScraper(self.conn, self.logger)

    def _setup_logging(self) -> logging.Logger:
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("dark_psych")
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

    def run_full_index(self):
        """Run full indexing across all sources."""
        self.logger.info("=" * 70)
        self.logger.info("DARK PSYCHOLOGY CONTENT SCRAPER")
        self.logger.info(f"Target: {CONFIG['target_total']:,} stories")
        self.logger.info("=" * 70)

        # AO3 - Primary source
        self.logger.info("\n📚 INDEXING AO3 DARK TAGS...")
        self.logger.info(f"   {len(AO3_DARK_TAGS)} tags to process\n")

        for i, tag in enumerate(AO3_DARK_TAGS, 1):
            self.logger.info(f"[{i}/{len(AO3_DARK_TAGS)}] {tag}")
            try:
                self.ao3_scraper.index_tag(tag)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")

        # Literotica
        self.logger.info("\n📚 INDEXING LITEROTICA DARK CATEGORIES...")

        for category in LITEROTICA_DARK_CATEGORIES:
            try:
                self.lit_scraper.index_category(category)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")

        self._print_stats()

    def download_stories(self, limit: int = 500, min_intensity: float = 0.3):
        """Download story content."""
        self.logger.info(f"Downloading stories (min intensity: {min_intensity})")

        cursor = self.conn.execute("""
            SELECT id, source, source_id, url, title FROM stories
            WHERE downloaded = 0 AND intensity_score >= ?
            ORDER BY intensity_score DESC, word_count DESC
            LIMIT ?
        """, (min_intensity, limit))

        stories = cursor.fetchall()
        self.logger.info(f"Found {len(stories)} stories to download")

        storage_dir = Path(CONFIG["storage_root"]) / "stories"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for i, row in enumerate(stories, 1):
            self.logger.info(f"[{i}/{len(stories)}] {row['title'][:50]}...")

            content = self._download_content(row['source'], row['url'])

            if content and len(content) > 500:
                safe_title = re.sub(r'[^\w\s-]', '', row['title'])[:40]
                filename = f"{row['source']}_{row['id']}_{safe_title}.txt"
                filepath = storage_dir / filename

                filepath.write_text(content, encoding='utf-8')

                self.conn.execute("""
                    UPDATE stories SET downloaded = 1, content_path = ?, word_count = ?
                    WHERE id = ?
                """, (str(filepath), len(content.split()), row['id']))
                self.conn.commit()
            else:
                self.conn.execute(
                    "UPDATE stories SET error = 'Download failed' WHERE id = ?",
                    (row['id'],)
                )
                self.conn.commit()

    def _download_content(self, source: str, url: str) -> Optional[str]:
        """Download content from source."""
        try:
            if source == "ao3":
                return self._download_ao3(url)
            elif source == "literotica":
                return self._download_literotica(url)
        except Exception as e:
            self.logger.error(f"Download error: {e}")
        return None

    def _download_ao3(self, url: str) -> Optional[str]:
        """Download AO3 story."""
        full_url = f"{url}?view_adult=true&view_full_work=true"

        time.sleep(CONFIG["rate_limit_ao3"])

        try:
            resp = requests.get(full_url, headers={"User-Agent": CONFIG["user_agent"]}, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            chapters = soup.select('div.userstuff[role="article"], div.chapter div.userstuff')

            content_parts = []
            for chapter in chapters:
                for p in chapter.find_all('p'):
                    text = p.get_text(strip=True)
                    if text:
                        content_parts.append(text)

            return '\n\n'.join(content_parts)
        except Exception as e:
            self.logger.error(f"AO3 download error: {e}")
            return None

    def _download_literotica(self, url: str) -> Optional[str]:
        """Download Literotica story."""
        time.sleep(CONFIG["rate_limit_lit"])

        try:
            resp = requests.get(url, headers={"User-Agent": CONFIG["user_agent"]}, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            body = soup.select_one('.aa_ht, .story-content, #storytext')
            if not body:
                return None

            content_parts = []
            for p in body.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text)

            return '\n\n'.join(content_parts)
        except Exception as e:
            self.logger.error(f"Literotica download error: {e}")
            return None

    def _print_stats(self):
        """Print comprehensive stats."""
        cursor = self.conn.execute("""
            SELECT
                source,
                COUNT(*) as total,
                SUM(CASE WHEN has_manipulation = 1 THEN 1 ELSE 0 END) as manipulation,
                SUM(CASE WHEN has_power_dynamic = 1 THEN 1 ELSE 0 END) as power,
                SUM(CASE WHEN has_obsession = 1 THEN 1 ELSE 0 END) as obsession,
                SUM(CASE WHEN has_noncon_elements = 1 THEN 1 ELSE 0 END) as noncon,
                SUM(CASE WHEN has_captivity = 1 THEN 1 ELSE 0 END) as captivity,
                SUM(CASE WHEN has_mind_control = 1 THEN 1 ELSE 0 END) as mind_control,
                SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded,
                AVG(intensity_score) as avg_intensity
            FROM stories
            GROUP BY source
        """)

        self.logger.info("\n" + "=" * 70)
        self.logger.info("INDEXING COMPLETE - DARK PSYCHOLOGY ARCHIVE")
        self.logger.info("=" * 70)

        grand_total = 0
        for row in cursor:
            self.logger.info(f"\n{row['source'].upper()}:")
            self.logger.info(f"  Total stories:    {row['total']:,}")
            self.logger.info(f"  Manipulation:     {row['manipulation']:,}")
            self.logger.info(f"  Power dynamics:   {row['power']:,}")
            self.logger.info(f"  Obsession:        {row['obsession']:,}")
            self.logger.info(f"  Non-con elements: {row['noncon']:,}")
            self.logger.info(f"  Captivity:        {row['captivity']:,}")
            self.logger.info(f"  Mind control:     {row['mind_control']:,}")
            self.logger.info(f"  Downloaded:       {row['downloaded']:,}")
            self.logger.info(f"  Avg intensity:    {row['avg_intensity']:.2f}")
            grand_total += row['total']

        self.logger.info("\n" + "-" * 70)
        self.logger.info(f"GRAND TOTAL: {grand_total:,} stories indexed")
        self.logger.info(f"TARGET:      {CONFIG['target_total']:,}")
        self.logger.info(f"PROGRESS:    {grand_total / CONFIG['target_total'] * 100:.1f}%")
        self.logger.info("=" * 70)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dark Psychology Content Scraper")
    parser.add_argument('command', choices=['index', 'download', 'stats'])
    parser.add_argument('--tag', help='Specific tag to index')
    parser.add_argument('--limit', type=int, default=500)
    parser.add_argument('--min-intensity', type=float, default=0.3)

    args = parser.parse_args()

    scraper = DarkPsychScraper()

    if args.command == 'index':
        if args.tag:
            scraper.ao3_scraper.index_tag(args.tag)
        else:
            scraper.run_full_index()

    elif args.command == 'download':
        scraper.download_stories(args.limit, args.min_intensity)

    elif args.command == 'stats':
        scraper._print_stats()

if __name__ == "__main__":
    main()
