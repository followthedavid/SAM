#!/usr/bin/env python3
"""
Exhaustive Content Tagging System

Tags untagged content (like Nifty) with comprehensive theme detection.
Uses multi-layered approach:
1. Keyword detection (fast, catches obvious themes)
2. Pattern matching (relationship dynamics, scenarios)
3. Optional LLM classification (for nuance)

Usage:
    python content_tagger.py analyze nifty     # Analyze and tag Nifty content
    python content_tagger.py status            # Show tagging stats
    python content_tagger.py search "tag"      # Find stories by tag
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# ============================================================================
# Tag Taxonomy - Exhaustive Categories
# ============================================================================

TAG_CATEGORIES = {
    "consent": {
        "consensual": ["consent", "willing", "eager", "wanted", "asked for"],
        "dubious_consent": ["dubcon", "reluctant", "hesitant", "unsure", "confused", "didn't stop"],
        "non_consensual": ["forced", "rape", "assault", "against his will", "no choice", "couldn't stop", "made him", "held down"],
        "coercion": ["blackmail", "threatened", "had to", "no choice", "or else", "leverage"],
    },

    "power_dynamics": {
        "authority_figure": ["teacher", "professor", "coach", "boss", "officer", "priest", "pastor", "doctor"],
        "age_gap": ["older", "younger", "daddy", "boy", "son", "father", "uncle", "nephew", "mature", "teen"],
        "dominance": ["dominant", "dom", "master", "sir", "control", "command", "obey", "submit"],
        "submission": ["submissive", "sub", "slave", "servant", "obedient", "kneel", "beg"],
        "power_imbalance": ["helpless", "vulnerable", "innocent", "naive", "inexperienced", "first time"],
    },

    "relationship_types": {
        "strangers": ["stranger", "unknown", "never met", "first meeting", "anonymous"],
        "friends": ["best friend", "buddy", "roommate", "neighbor"],
        "family": ["brother", "father", "uncle", "cousin", "stepbrother", "stepfather", "dad", "son"],
        "romantic": ["boyfriend", "husband", "partner", "lover", "dating", "relationship"],
        "transactional": ["paid", "money", "escort", "prostitute", "hustler", "rent"],
    },

    "settings": {
        "school": ["school", "college", "university", "dorm", "classroom", "locker room", "campus"],
        "sports": ["coach", "team", "locker", "gym", "athlete", "jock", "football", "wrestling"],
        "military": ["army", "navy", "marine", "soldier", "barracks", "drill", "sergeant"],
        "workplace": ["office", "boss", "coworker", "job", "work", "employee"],
        "prison": ["prison", "jail", "inmate", "cell", "guard", "warden"],
        "public": ["public", "park", "restroom", "beach", "outdoor", "caught"],
        "religious": ["church", "priest", "altar boy", "confession", "religious", "sin"],
    },

    "character_archetypes": {
        "jock": ["jock", "athlete", "muscular", "sports", "football", "wrestler"],
        "nerd": ["nerd", "geek", "glasses", "smart", "shy", "bookworm"],
        "bully": ["bully", "mean", "cruel", "picked on", "torment", "humiliate"],
        "twink": ["twink", "slim", "smooth", "young looking", "boyish"],
        "bear": ["bear", "hairy", "large", "burly", "daddy"],
        "preppy": ["preppy", "rich", "privileged", "fraternity", "country club"],
        "blue_collar": ["construction", "mechanic", "trucker", "working class", "rough hands"],
    },

    "emotional_tones": {
        "romantic": ["love", "tender", "gentle", "caring", "sweet", "passionate", "making love"],
        "dark": ["dark", "twisted", "sinister", "evil", "cruel", "sadistic"],
        "humiliation": ["humiliate", "embarrass", "shame", "degrade", "pathetic", "worthless"],
        "worship": ["worship", "admire", "perfect", "beautiful", "god", "adore"],
        "revenge": ["revenge", "payback", "get back", "punish", "teach a lesson"],
        "seduction": ["seduce", "tempt", "tease", "flirt", "charm", "lure"],
    },

    "acts": {
        "oral": ["blowjob", "suck", "mouth", "throat", "swallow", "lick", "rimming"],
        "anal": ["fuck", "ass", "bottom", "top", "penetrate", "pound", "breed"],
        "masturbation": ["jerk", "stroke", "masturbat", "jack off", "hand job", "cum"],
        "group": ["threesome", "gangbang", "orgy", "group", "train", "passed around"],
        "voyeurism": ["watch", "spy", "peek", "caught", "hidden", "camera"],
        "exhibitionism": ["show off", "display", "expose", "public", "caught"],
        "bondage": ["tied", "bound", "restrain", "handcuff", "rope", "chain"],
    },

    "kinks": {
        "size": ["big", "huge", "massive", "thick", "hung", "monster"],
        "underwear": ["underwear", "briefs", "jockstrap", "boxers", "bulge"],
        "feet": ["feet", "foot", "toes", "socks", "worship"],
        "leather": ["leather", "boots", "harness", "gear"],
        "uniform": ["uniform", "cop", "soldier", "firefighter", "doctor"],
        "verbal": ["talk dirty", "verbal", "call me", "say my name", "moan"],
        "breeding": ["breed", "seed", "load", "fill", "raw", "bare"],
    },

    "identity_dynamics": {
        "closeted": ["closet", "secret", "hide", "can't know", "straight acting", "no one knows"],
        "first_time": ["first time", "virgin", "never done", "new to this", "curious"],
        "straight_guy": ["straight", "not gay", "just this once", "experiment", "curious"],
        "coming_out": ["come out", "admit", "finally", "truth", "accept"],
        "internalized": ["hate myself", "wrong", "shouldn't", "sin", "disgusted"],
    },

    "antagonist_traits": {
        "homophobic": ["faggot", "queer", "homo", "gay boy", "sissy", "pansy", "fairy"],
        "aggressive": ["aggressive", "violent", "rough", "brutal", "force", "make you"],
        "manipulative": ["manipulate", "trick", "deceive", "use", "take advantage"],
        "sadistic": ["enjoy", "pain", "suffer", "cry", "scream", "hurt"],
    },
}

# Compile regex patterns for efficiency
COMPILED_PATTERNS = {}
for category, subcats in TAG_CATEGORIES.items():
    COMPILED_PATTERNS[category] = {}
    for tag, keywords in subcats.items():
        # Create pattern that matches whole words (case insensitive)
        pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
        COMPILED_PATTERNS[category][tag] = re.compile(pattern, re.IGNORECASE)


# ============================================================================
# Content Tagger
# ============================================================================

@dataclass
class TagResult:
    """Result of tagging a piece of content."""
    story_id: str
    tags: Dict[str, List[str]] = field(default_factory=dict)
    tag_scores: Dict[str, float] = field(default_factory=dict)
    word_count: int = 0

    def all_tags(self) -> List[str]:
        """Get flat list of all tags."""
        result = []
        for category, tags in self.tags.items():
            for tag in tags:
                result.append(f"{category}:{tag}")
        return result

    def has_tag(self, tag: str) -> bool:
        """Check if a specific tag is present."""
        if ":" in tag:
            cat, t = tag.split(":", 1)
            return t in self.tags.get(cat, [])
        else:
            return any(tag in tags for tags in self.tags.values())


class ContentTagger:
    """Tags content with comprehensive theme detection."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / ".sam" / "content_tags.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize tagging database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tagged_content (
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                tags_json TEXT,
                scores_json TEXT,
                word_count INTEGER,
                tagged_at TEXT,
                PRIMARY KEY (source, item_id)
            );

            CREATE TABLE IF NOT EXISTS tag_index (
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                category TEXT NOT NULL,
                tag TEXT NOT NULL,
                score REAL,
                PRIMARY KEY (source, item_id, category, tag)
            );

            CREATE INDEX IF NOT EXISTS idx_tag ON tag_index(tag);
            CREATE INDEX IF NOT EXISTS idx_category ON tag_index(category);
            CREATE INDEX IF NOT EXISTS idx_source ON tag_index(source);
        """)
        conn.commit()
        conn.close()

    def tag_content(self, text: str, story_id: str = "") -> TagResult:
        """
        Analyze text and return comprehensive tags.

        Uses keyword frequency and pattern matching.
        Score = occurrences / word_count * 1000 (normalized)
        """
        result = TagResult(story_id=story_id)
        result.word_count = len(text.split())

        if result.word_count < 50:
            return result

        # Analyze each category
        for category, patterns in COMPILED_PATTERNS.items():
            category_tags = []

            for tag, pattern in patterns.items():
                matches = pattern.findall(text)
                if matches:
                    # Score based on frequency normalized by length
                    score = len(matches) / result.word_count * 1000

                    # Threshold: at least 2 matches or 1 match in short text
                    if len(matches) >= 2 or (len(matches) >= 1 and result.word_count < 2000):
                        category_tags.append(tag)
                        result.tag_scores[f"{category}:{tag}"] = round(score, 2)

            if category_tags:
                result.tags[category] = category_tags

        return result

    def save_tags(self, source: str, item_id: str, result: TagResult):
        """Save tags to database."""
        from datetime import datetime

        conn = sqlite3.connect(self.db_path)

        # Save main record
        conn.execute("""
            INSERT OR REPLACE INTO tagged_content
            (source, item_id, tags_json, scores_json, word_count, tagged_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source, item_id,
            json.dumps(result.tags),
            json.dumps(result.tag_scores),
            result.word_count,
            datetime.now().isoformat()
        ))

        # Save tag index
        conn.execute(
            "DELETE FROM tag_index WHERE source = ? AND item_id = ?",
            (source, item_id)
        )

        for category, tags in result.tags.items():
            for tag in tags:
                score = result.tag_scores.get(f"{category}:{tag}", 0)
                conn.execute("""
                    INSERT INTO tag_index (source, item_id, category, tag, score)
                    VALUES (?, ?, ?, ?, ?)
                """, (source, item_id, category, tag, score))

        conn.commit()
        conn.close()

    def get_by_tag(self, tag: str, source: str = None, limit: int = 100) -> List[str]:
        """Find stories with a specific tag."""
        conn = sqlite3.connect(self.db_path)

        if ":" in tag:
            category, tag_name = tag.split(":", 1)
            query = "SELECT source, item_id FROM tag_index WHERE category = ? AND tag = ?"
            params = [category, tag_name]
        else:
            query = "SELECT source, item_id FROM tag_index WHERE tag = ?"
            params = [tag]

        if source:
            query += " AND source = ?"
            params.append(source)

        query += f" ORDER BY score DESC LIMIT {limit}"

        cursor = conn.execute(query, params)
        results = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        conn.close()

        return results

    def get_stats(self, source: str = None) -> Dict:
        """Get tagging statistics."""
        conn = sqlite3.connect(self.db_path)

        stats = {"total_tagged": 0, "by_category": {}, "top_tags": []}

        # Total tagged
        query = "SELECT COUNT(DISTINCT source || ':' || item_id) FROM tagged_content"
        if source:
            query += f" WHERE source = '{source}'"
        cursor = conn.execute(query)
        stats["total_tagged"] = cursor.fetchone()[0]

        # By category
        query = "SELECT category, COUNT(DISTINCT source || ':' || item_id) FROM tag_index"
        if source:
            query += f" WHERE source = '{source}'"
        query += " GROUP BY category"
        cursor = conn.execute(query)
        stats["by_category"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Top tags
        query = """
            SELECT category || ':' || tag, COUNT(*) as cnt
            FROM tag_index
        """
        if source:
            query += f" WHERE source = '{source}'"
        query += " GROUP BY category, tag ORDER BY cnt DESC LIMIT 30"
        cursor = conn.execute(query)
        stats["top_tags"] = [(row[0], row[1]) for row in cursor.fetchall()]

        conn.close()
        return stats


# ============================================================================
# Nifty Tagger
# ============================================================================

class NiftyTagger:
    """Tags Nifty archive content."""

    NIFTY_DB = Path("/Volumes/David External/nifty_archive/nifty_index.db")
    NIFTY_CONTENT = Path("/Volumes/David External/nifty_archive/stories")

    def __init__(self):
        self.tagger = ContentTagger()

    def tag_all(self, limit: int = None, skip_tagged: bool = True):
        """Tag all Nifty stories."""
        conn = sqlite3.connect(self.NIFTY_DB)
        cursor = conn.execute("""
            SELECT id, file_path, category FROM stories WHERE downloaded = 1
        """)
        stories = cursor.fetchall()
        conn.close()

        print(f"Found {len(stories)} downloaded stories")

        tagged = 0
        skipped = 0
        errors = 0

        for story_id, file_path, category in stories:
            if limit and tagged >= limit:
                break

            # Check if already tagged
            if skip_tagged:
                tag_conn = sqlite3.connect(self.tagger.db_path)
                cursor = tag_conn.execute(
                    "SELECT 1 FROM tagged_content WHERE source = 'nifty' AND item_id = ?",
                    (story_id,)
                )
                if cursor.fetchone():
                    skipped += 1
                    tag_conn.close()
                    continue
                tag_conn.close()

            # Load content - Nifty stores as {category}/{id}_{title}.json
            try:
                content = None
                category_dir = self.NIFTY_CONTENT / category if category else self.NIFTY_CONTENT

                # Find file matching the story ID
                if category_dir.exists():
                    for f in category_dir.glob(f"{story_id}_*.json"):
                        try:
                            data = json.loads(f.read_text(errors='ignore'))
                            content = data.get("content", data.get("text", ""))
                            break
                        except:
                            continue

                # Fallback: search all subdirs
                if not content:
                    for f in self.NIFTY_CONTENT.glob(f"*/{story_id}_*.json"):
                        try:
                            data = json.loads(f.read_text(errors='ignore'))
                            content = data.get("content", data.get("text", ""))
                            break
                        except:
                            continue

                if not content:
                    errors += 1
                    continue

                # Tag it
                result = self.tagger.tag_content(content, story_id)

                # Add Nifty category as a tag
                if category:
                    if "settings" not in result.tags:
                        result.tags["settings"] = []
                    result.tags["settings"].append(f"nifty_{category}")

                self.tagger.save_tags("nifty", story_id, result)
                tagged += 1

                if tagged % 100 == 0:
                    print(f"  Tagged {tagged} stories...")

            except Exception as e:
                errors += 1
                if errors < 10:
                    print(f"  Error tagging {story_id}: {e}")

        print(f"\nComplete: {tagged} tagged, {skipped} skipped, {errors} errors")
        return {"tagged": tagged, "skipped": skipped, "errors": errors}

    def show_stats(self):
        """Show Nifty tagging stats."""
        stats = self.tagger.get_stats("nifty")

        print("=" * 60)
        print("Nifty Content Tags")
        print("=" * 60)
        print(f"\nTotal tagged: {stats['total_tagged']}")

        print("\nBy category:")
        for cat, count in sorted(stats["by_category"].items()):
            print(f"  {cat}: {count}")

        print("\nTop 30 tags:")
        for tag, count in stats["top_tags"]:
            print(f"  {tag}: {count}")


# ============================================================================
# CLI
# ============================================================================

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python content_tagger.py analyze [source] [limit]  - Tag content")
        print("  python content_tagger.py status [source]           - Show stats")
        print("  python content_tagger.py search <tag>              - Find by tag")
        print("  python content_tagger.py categories                - List all tag categories")
        return

    cmd = sys.argv[1]

    if cmd == "analyze":
        source = sys.argv[2] if len(sys.argv) > 2 else "nifty"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None

        if source == "nifty":
            tagger = NiftyTagger()
            tagger.tag_all(limit=limit)
        else:
            print(f"Unknown source: {source}")

    elif cmd == "status":
        source = sys.argv[2] if len(sys.argv) > 2 else None

        if source == "nifty":
            tagger = NiftyTagger()
            tagger.show_stats()
        else:
            tagger = ContentTagger()
            stats = tagger.get_stats(source)
            print(f"Total tagged: {stats['total_tagged']}")
            print(f"Categories: {stats['by_category']}")
            print(f"Top tags: {stats['top_tags'][:20]}")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python content_tagger.py search <tag>")
            return

        tag = sys.argv[2]
        tagger = ContentTagger()
        results = tagger.get_by_tag(tag, limit=50)

        print(f"Stories with tag '{tag}':")
        for r in results:
            print(f"  {r}")

    elif cmd == "categories":
        print("Available tag categories and tags:\n")
        for category, tags in TAG_CATEGORIES.items():
            print(f"{category}:")
            for tag, keywords in tags.items():
                print(f"  {tag}: {', '.join(keywords[:5])}...")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
