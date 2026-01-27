#!/usr/bin/env python3
"""
Reddit Roleplay Scraper
Target: r/DirtyPenPals, r/DirtyWritingPrompts, r/EroticRolePlay archives
Storage: External drives only
Output: Actual roleplay exchanges for training

Uses Pushshift/Arctic Shift archives for historical data
"""

import os
import re
import json
import time
import hashlib
import logging
import sqlite3
import gzip
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/reddit_roleplay",
    "db_path": "/Volumes/David External/reddit_roleplay/reddit_roleplay.db",
    "rate_limit_seconds": 1.0,
    "user_agent": "SAM-Training-Collector/1.0",

    # Arctic Shift (Pushshift replacement) - historical Reddit data
    "arctic_shift_base": "https://arctic-shift.photon-reddit.com/api",

    # Reddit API (for recent content)
    "reddit_base": "https://www.reddit.com",
}

# Target subreddits for roleplay content
ROLEPLAY_SUBREDDITS = [
    "DirtyPenPals",           # Actual roleplay requests/exchanges
    "DirtyWritingPrompts",    # NSFW writing prompts
    "EroticRolePlay",         # Erotic RP
    "NSFWroleplay",           # General NSFW RP
    "dirtyr4r",               # Roleplay personals
    "DPPprofiles",            # DPP character profiles
    "DirtyKikPals",           # Kik roleplay
    "DirtySnapchat",          # Snap roleplay
]

# Keywords that indicate actual roleplay content vs just requests
ROLEPLAY_CONTENT_KEYWORDS = [
    # Action markers
    '*', '~', '_', '**',

    # Common RP phrases
    'rp:', 'roleplay:', 'scenario:',
    'i walk', 'you see', 'she said', 'he whispered',
    '*smiles*', '*laughs*', '*looks*',

    # Dialogue markers
    '"', "'", '「', '」',
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class RedditPost:
    """A Reddit post (submission)."""
    id: str
    reddit_id: str
    subreddit: str
    title: str
    author: str
    selftext: str
    score: int
    num_comments: int
    created_utc: int
    url: str
    is_roleplay_content: bool
    has_scenario: bool
    indexed_at: str

@dataclass
class RedditComment:
    """A Reddit comment."""
    id: str
    reddit_id: str
    post_id: str
    subreddit: str
    author: str
    body: str
    score: int
    created_utc: int
    parent_id: str
    is_roleplay_content: bool
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
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            reddit_id TEXT UNIQUE,
            subreddit TEXT,
            title TEXT,
            author TEXT,
            selftext TEXT,
            score INTEGER,
            num_comments INTEGER,
            created_utc INTEGER,
            url TEXT,
            is_roleplay_content INTEGER,
            has_scenario INTEGER,
            indexed_at TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            reddit_id TEXT UNIQUE,
            post_id TEXT,
            subreddit TEXT,
            author TEXT,
            body TEXT,
            score INTEGER,
            created_utc INTEGER,
            parent_id TEXT,
            is_roleplay_content INTEGER,
            indexed_at TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(reddit_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            participants TEXT,
            content TEXT,
            turn_count INTEGER,
            word_count INTEGER,
            quality_score REAL,
            indexed_at TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(reddit_id)
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_subreddit ON posts(subreddit)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON posts(score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rp_content ON posts(is_roleplay_content)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPING
# ============================================================================

class RedditRoleplayScraper:
    """Scraper for Reddit roleplay content."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()
        self.last_request = 0

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("reddit_rp")
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

    def _is_roleplay_content(self, text: str) -> bool:
        """Check if text contains actual roleplay content."""
        if not text:
            return False

        text_lower = text.lower()

        # Check for action markers (asterisks, tildes)
        action_pattern = r'\*[^*]+\*|~[^~]+~|_[^_]+_'
        if re.search(action_pattern, text):
            return True

        # Check for dialogue patterns
        dialogue_pattern = r'"[^"]{10,}"|\'[^\']{10,}\''
        if re.search(dialogue_pattern, text):
            return True

        # Check for common RP phrases
        rp_phrases = [
            'i walk', 'you see', 'she says', 'he whispers',
            'i look at you', 'you feel', 'i lean', 'i smile',
            '*smiles*', '*laughs*', '*looks*', '*nods*',
        ]
        if any(phrase in text_lower for phrase in rp_phrases):
            return True

        return False

    def _has_scenario(self, text: str) -> bool:
        """Check if post contains a scenario setup."""
        if not text:
            return False

        text_lower = text.lower()

        scenario_markers = [
            'scenario:', 'setting:', 'premise:', 'plot:',
            'the scene:', 'you are', 'you\'re a', 'you play',
            'looking for someone to play', 'i\'ll be playing',
        ]

        return any(marker in text_lower for marker in scenario_markers)

    def _fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """Fetch JSON from API."""
        self._rate_limit()

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"API error: {e}")
            return None

    def fetch_subreddit_posts_reddit(self, subreddit: str, limit: int = 100, after: str = None) -> List[dict]:
        """Fetch posts from Reddit API (recent content)."""
        url = f"{CONFIG['reddit_base']}/r/{subreddit}/new.json"
        params = {"limit": min(limit, 100)}
        if after:
            params["after"] = after

        data = self._fetch_json(url, params)
        if not data:
            return []

        posts = []
        for child in data.get('data', {}).get('children', []):
            post_data = child.get('data', {})
            posts.append(post_data)

        return posts

    def fetch_subreddit_arctic(self, subreddit: str, limit: int = 1000) -> List[dict]:
        """Fetch historical posts from Arctic Shift (Pushshift replacement)."""
        url = f"{CONFIG['arctic_shift_base']}/posts/search"

        params = {
            "subreddit": subreddit,
            "limit": limit,
            "sort": "score",
            "sort_type": "desc",
        }

        data = self._fetch_json(url, params)
        if not data:
            return []

        return data.get('data', [])

    def _save_post(self, post: RedditPost):
        """Save post to database."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO posts (
                    id, reddit_id, subreddit, title, author, selftext,
                    score, num_comments, created_utc, url,
                    is_roleplay_content, has_scenario, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post.id, post.reddit_id, post.subreddit, post.title,
                post.author, post.selftext, post.score, post.num_comments,
                post.created_utc, post.url,
                1 if post.is_roleplay_content else 0,
                1 if post.has_scenario else 0,
                post.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def index_subreddit(self, subreddit: str, use_arctic: bool = True):
        """Index posts from a subreddit."""
        self.logger.info(f"Indexing r/{subreddit}...")

        total = 0
        rp_content = 0

        if use_arctic:
            # Try Arctic Shift for historical data
            posts = self.fetch_subreddit_arctic(subreddit, limit=5000)

            for post_data in posts:
                selftext = post_data.get('selftext', '') or ''
                title = post_data.get('title', '')

                is_rp = self._is_roleplay_content(selftext) or self._is_roleplay_content(title)
                has_scenario = self._has_scenario(selftext)

                post = RedditPost(
                    id=hashlib.md5(f"reddit_{post_data.get('id', '')}".encode()).hexdigest()[:16],
                    reddit_id=post_data.get('id', ''),
                    subreddit=subreddit,
                    title=title,
                    author=post_data.get('author', '[deleted]'),
                    selftext=selftext,
                    score=post_data.get('score', 0),
                    num_comments=post_data.get('num_comments', 0),
                    created_utc=post_data.get('created_utc', 0),
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    is_roleplay_content=is_rp,
                    has_scenario=has_scenario,
                    indexed_at=datetime.now().isoformat(),
                )

                self._save_post(post)
                total += 1
                if is_rp:
                    rp_content += 1

                if total % 100 == 0:
                    self.logger.info(f"  {total} posts indexed ({rp_content} RP content)...")

        # Also fetch recent from Reddit
        after = None
        for _ in range(10):  # 10 pages of 100
            posts = self.fetch_subreddit_posts_reddit(subreddit, limit=100, after=after)
            if not posts:
                break

            for post_data in posts:
                selftext = post_data.get('selftext', '') or ''
                title = post_data.get('title', '')

                is_rp = self._is_roleplay_content(selftext) or self._is_roleplay_content(title)
                has_scenario = self._has_scenario(selftext)

                post = RedditPost(
                    id=hashlib.md5(f"reddit_{post_data.get('id', '')}".encode()).hexdigest()[:16],
                    reddit_id=post_data.get('id', ''),
                    subreddit=subreddit,
                    title=title,
                    author=post_data.get('author', '[deleted]'),
                    selftext=selftext,
                    score=post_data.get('score', 0),
                    num_comments=post_data.get('num_comments', 0),
                    created_utc=int(post_data.get('created_utc', 0)),
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    is_roleplay_content=is_rp,
                    has_scenario=has_scenario,
                    indexed_at=datetime.now().isoformat(),
                )

                self._save_post(post)
                total += 1
                if is_rp:
                    rp_content += 1

            after = posts[-1].get('name') if posts else None

        self.logger.info(f"r/{subreddit}: {total} posts ({rp_content} with RP content)")

    def fetch_post_comments(self, reddit_id: str) -> List[dict]:
        """Fetch comments for a post."""
        url = f"{CONFIG['reddit_base']}/comments/{reddit_id}.json"

        data = self._fetch_json(url)
        if not data or len(data) < 2:
            return []

        # Comments are in the second element
        comments_data = data[1].get('data', {}).get('children', [])

        comments = []
        for child in comments_data:
            if child.get('kind') == 't1':
                comments.append(child.get('data', {}))

        return comments

    def build_conversation(self, post_id: str) -> Optional[dict]:
        """Build a conversation from post and comments."""
        # Get post
        cursor = self.conn.execute(
            "SELECT * FROM posts WHERE reddit_id = ?", (post_id,)
        )
        post = cursor.fetchone()
        if not post:
            return None

        # Fetch comments
        comments = self.fetch_post_comments(post_id)
        if not comments:
            return None

        # Build conversation
        participants = {post['author']}
        turns = []

        # Post as first turn
        if post['selftext']:
            turns.append({
                "author": post['author'],
                "content": post['selftext'],
                "type": "post"
            })

        # Add comments as turns
        for comment in comments:
            author = comment.get('author', '[deleted]')
            body = comment.get('body', '')

            if body and author != '[deleted]':
                participants.add(author)
                turns.append({
                    "author": author,
                    "content": body,
                    "type": "comment"
                })

        if len(turns) < 2:
            return None

        # Format as conversation
        content_parts = []
        for turn in turns:
            content_parts.append(f"[{turn['author']}]:\n{turn['content']}\n")

        full_content = '\n'.join(content_parts)

        return {
            "id": hashlib.md5(f"conv_{post_id}".encode()).hexdigest()[:16],
            "post_id": post_id,
            "participants": list(participants),
            "content": full_content,
            "turn_count": len(turns),
            "word_count": len(full_content.split()),
            "indexed_at": datetime.now().isoformat(),
        }

    def run_full_index(self):
        """Index all roleplay subreddits."""
        self.logger.info("=" * 60)
        self.logger.info("Reddit Roleplay Scraper")
        self.logger.info("=" * 60)

        for subreddit in ROLEPLAY_SUBREDDITS:
            try:
                self.index_subreddit(subreddit)
            except KeyboardInterrupt:
                self.logger.info("Interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error with r/{subreddit}: {e}")
                continue

        # Stats
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_roleplay_content = 1 THEN 1 ELSE 0 END) as rp_content,
                SUM(CASE WHEN has_scenario = 1 THEN 1 ELSE 0 END) as scenarios,
                SUM(score) as total_score
            FROM posts
        """)
        stats = cursor.fetchone()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("COMPLETE")
        self.logger.info(f"  Total posts:      {stats['total']:,}")
        self.logger.info(f"  RP content:       {stats['rp_content']:,}")
        self.logger.info(f"  With scenarios:   {stats['scenarios']:,}")
        self.logger.info(f"  Total score:      {stats['total_score']:,}")
        self.logger.info("=" * 60)

    def export_training_data(self, output_path: str, min_score: int = 10):
        """Export posts as training data."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        cursor = self.conn.execute("""
            SELECT * FROM posts
            WHERE is_roleplay_content = 1 AND score >= ?
            ORDER BY score DESC
        """, (min_score,))

        training_data = []

        for row in cursor:
            entry = {
                "title": row['title'],
                "content": row['selftext'],
                "subreddit": row['subreddit'],
                "score": row['score'],
                "has_scenario": bool(row['has_scenario']),
                "source": "reddit",
            }
            training_data.append(entry)

        # Save as JSONL
        output_file = output_dir / "reddit_roleplay.jsonl"
        with open(output_file, 'w') as f:
            for entry in training_data:
                f.write(json.dumps(entry) + '\n')

        self.logger.info(f"Exported {len(training_data)} posts to {output_file}")
        return len(training_data)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reddit Roleplay Scraper")
    parser.add_argument('command', choices=['index', 'export', 'stats'])
    parser.add_argument('--subreddit', help='Specific subreddit')
    parser.add_argument('--output', default=CONFIG["storage_root"])
    parser.add_argument('--min-score', type=int, default=10)

    args = parser.parse_args()

    scraper = RedditRoleplayScraper()

    if args.command == 'index':
        if args.subreddit:
            scraper.index_subreddit(args.subreddit)
        else:
            scraper.run_full_index()

    elif args.command == 'export':
        scraper.export_training_data(args.output, args.min_score)

    elif args.command == 'stats':
        cursor = scraper.conn.execute("""
            SELECT
                subreddit,
                COUNT(*) as total,
                SUM(CASE WHEN is_roleplay_content = 1 THEN 1 ELSE 0 END) as rp_content,
                AVG(score) as avg_score
            FROM posts
            GROUP BY subreddit
            ORDER BY total DESC
        """)

        print("\n🎭 Reddit Roleplay Archive Stats")
        print("=" * 60)

        for row in cursor:
            print(f"r/{row['subreddit']:20} | {row['total']:6,} posts | {row['rp_content']:5,} RP | avg {row['avg_score']:.1f}")

        # Totals
        cursor = scraper.conn.execute("SELECT COUNT(*), SUM(score) FROM posts")
        totals = cursor.fetchone()
        print("-" * 60)
        print(f"{'TOTAL':23} | {totals[0]:6,} posts | score: {totals[1]:,}")

if __name__ == "__main__":
    main()
