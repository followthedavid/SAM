#!/usr/bin/env python3
"""
Fashion Archive - Unified Database
Consolidates articles from all scrapers into a searchable archive.
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "db_path": "/Volumes/#1/fashion_archive/fashion_archive.db",
    "sources": {
        "wwd": {
            "name": "Women's Wear Daily",
            "articles_path": "/Volumes/#1/wwd_archive/articles",
            "type": "trade_news"
        },
        "wmag": {
            "name": "W Magazine",
            "articles_path": "/Volumes/#1/wmag_archive/articles",
            "type": "fashion_culture"
        },
        "vmag": {
            "name": "V Magazine",
            "articles_path": "/Volumes/#1/vmag_archive/articles",
            "type": "fashion_culture"
        }
    }
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Article:
    id: str
    source: str
    source_name: str
    url: str
    title: str
    author: Optional[str]
    category: str
    subcategory: Optional[str]
    publish_date: Optional[str]
    content: str
    word_count: int
    image_count: int
    tags: List[str]
    scraped_at: str
    file_path: str

@dataclass
class AnalyticsResult:
    metric: str
    value: Any
    breakdown: Optional[Dict] = None

# ============================================================================
# DATABASE
# ============================================================================

class FashionArchiveDB:
    """Unified fashion archive database with full-text search."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or CONFIG["db_path"]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database with FTS5 for full-text search."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Main articles table
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_name TEXT,
                    url TEXT UNIQUE,
                    title TEXT,
                    author TEXT,
                    category TEXT,
                    subcategory TEXT,
                    publish_date TEXT,
                    publish_year INTEGER,
                    publish_month INTEGER,
                    content TEXT,
                    word_count INTEGER,
                    image_count INTEGER DEFAULT 0,
                    tags TEXT,  -- JSON array
                    scraped_at TEXT,
                    file_path TEXT,
                    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Full-text search index
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                    title, content, author, category, tags,
                    content='articles',
                    content_rowid='rowid'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                    INSERT INTO articles_fts(rowid, title, content, author, category, tags)
                    VALUES (new.rowid, new.title, new.content, new.author, new.category, new.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                    INSERT INTO articles_fts(articles_fts, rowid, title, content, author, category, tags)
                    VALUES('delete', old.rowid, old.title, old.content, old.author, old.category, old.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                    INSERT INTO articles_fts(articles_fts, rowid, title, content, author, category, tags)
                    VALUES('delete', old.rowid, old.title, old.content, old.author, old.category, old.tags);
                    INSERT INTO articles_fts(rowid, title, content, author, category, tags)
                    VALUES (new.rowid, new.title, new.content, new.author, new.category, new.tags);
                END;

                -- Analytics cache
                CREATE TABLE IF NOT EXISTS analytics_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,  -- JSON
                    computed_at TEXT
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_articles_year ON articles(publish_year);
                CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(publish_date);
            """)

    def add_article(self, article: Article) -> bool:
        """Add or update an article."""
        try:
            # Parse date components
            year, month = None, None
            if article.publish_date:
                parts = article.publish_date.split('-')
                if len(parts) >= 2:
                    try:
                        year = int(parts[0])
                        month = int(parts[1])
                    except:
                        pass

            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO articles
                    (id, source, source_name, url, title, author, category, subcategory,
                     publish_date, publish_year, publish_month, content, word_count,
                     image_count, tags, scraped_at, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article.id, article.source, article.source_name, article.url,
                    article.title, article.author, article.category, article.subcategory,
                    article.publish_date, year, month, article.content, article.word_count,
                    article.image_count, json.dumps(article.tags), article.scraped_at,
                    article.file_path
                ))
            return True
        except Exception as e:
            print(f"Error adding article: {e}")
            return False

    def search(self, query: str, source: str = None, category: str = None,
               year: int = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Full-text search with filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Build query
            if query:
                sql = """
                    SELECT a.*,
                           highlight(articles_fts, 1, '<mark>', '</mark>') as content_highlight,
                           bm25(articles_fts) as relevance
                    FROM articles_fts f
                    JOIN articles a ON a.rowid = f.rowid
                    WHERE articles_fts MATCH ?
                """
                params = [query]
            else:
                sql = "SELECT * FROM articles WHERE 1=1"
                params = []

            if source:
                sql += " AND a.source = ?" if query else " AND source = ?"
                params.append(source)
            if category:
                sql += " AND a.category = ?" if query else " AND category = ?"
                params.append(category)
            if year:
                sql += " AND a.publish_year = ?" if query else " AND publish_year = ?"
                params.append(year)

            if query:
                sql += " ORDER BY relevance"
            else:
                sql += " ORDER BY publish_date DESC"

            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_article(self, article_id: str) -> Optional[Dict]:
        """Get a single article by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_stats(self) -> Dict:
        """Get archive statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Total counts
            stats['total_articles'] = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            stats['total_words'] = conn.execute("SELECT SUM(word_count) FROM articles").fetchone()[0] or 0
            stats['total_images'] = conn.execute("SELECT SUM(image_count) FROM articles").fetchone()[0] or 0

            # By source
            cursor = conn.execute("""
                SELECT source, source_name, COUNT(*) as count, SUM(word_count) as words
                FROM articles GROUP BY source ORDER BY count DESC
            """)
            stats['by_source'] = [
                {'source': r[0], 'name': r[1], 'count': r[2], 'words': r[3]}
                for r in cursor.fetchall()
            ]

            # By year
            cursor = conn.execute("""
                SELECT publish_year, COUNT(*) as count
                FROM articles WHERE publish_year IS NOT NULL
                GROUP BY publish_year ORDER BY publish_year DESC
            """)
            stats['by_year'] = {r[0]: r[1] for r in cursor.fetchall()}

            # Top categories
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM articles WHERE category IS NOT NULL
                GROUP BY category ORDER BY count DESC LIMIT 20
            """)
            stats['top_categories'] = {r[0]: r[1] for r in cursor.fetchall()}

            return stats

    def get_trends(self, term: str, by: str = 'year') -> Dict:
        """Get trend data for a search term over time."""
        with sqlite3.connect(self.db_path) as conn:
            if by == 'year':
                cursor = conn.execute("""
                    SELECT publish_year as period, COUNT(*) as mentions
                    FROM articles
                    WHERE content LIKE ? AND publish_year IS NOT NULL
                    GROUP BY publish_year
                    ORDER BY publish_year
                """, (f'%{term}%',))
            else:  # by month
                cursor = conn.execute("""
                    SELECT substr(publish_date, 1, 7) as period, COUNT(*) as mentions
                    FROM articles
                    WHERE content LIKE ? AND publish_date IS NOT NULL
                    GROUP BY period
                    ORDER BY period
                """, (f'%{term}%',))

            return {
                'term': term,
                'by': by,
                'data': [{'period': r[0], 'mentions': r[1]} for r in cursor.fetchall()]
            }

    def compare_terms(self, terms: List[str], by: str = 'year') -> Dict:
        """Compare multiple terms over time."""
        results = {}
        for term in terms:
            trend = self.get_trends(term, by)
            results[term] = {d['period']: d['mentions'] for d in trend['data']}
        return {'terms': terms, 'by': by, 'data': results}

    def get_category_evolution(self) -> Dict:
        """Track how category distribution changes over time."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT publish_year, category, COUNT(*) as count
                FROM articles
                WHERE publish_year IS NOT NULL AND category IS NOT NULL
                GROUP BY publish_year, category
                ORDER BY publish_year, count DESC
            """)

            evolution = {}
            for year, category, count in cursor.fetchall():
                if year not in evolution:
                    evolution[year] = {}
                evolution[year][category] = count

            return evolution

    def get_top_authors(self, source: str = None, limit: int = 50) -> List[Dict]:
        """Get most prolific authors."""
        with sqlite3.connect(self.db_path) as conn:
            sql = """
                SELECT author, source, COUNT(*) as article_count, SUM(word_count) as total_words
                FROM articles
                WHERE author IS NOT NULL AND author != ''
            """
            params = []
            if source:
                sql += " AND source = ?"
                params.append(source)

            sql += " GROUP BY author, source ORDER BY article_count DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [
                {'author': r[0], 'source': r[1], 'articles': r[2], 'words': r[3]}
                for r in cursor.fetchall()
            ]


# ============================================================================
# IMPORT FUNCTIONS
# ============================================================================

def import_from_scraper(db: FashionArchiveDB, source_key: str, articles_path: str) -> int:
    """Import articles from a scraper's output directory."""
    source_config = CONFIG["sources"].get(source_key, {})
    source_name = source_config.get("name", source_key)

    imported = 0

    for root, dirs, files in os.walk(articles_path):
        for filename in files:
            if filename != "article.json":
                continue

            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                article = Article(
                    id=data.get('id', hashlib.md5(data.get('url', '').encode()).hexdigest()),
                    source=source_key,
                    source_name=source_name,
                    url=data.get('url', ''),
                    title=data.get('title', 'Untitled'),
                    author=data.get('author'),
                    category=data.get('category', ''),
                    subcategory=data.get('subcategory'),
                    publish_date=data.get('publish_date'),
                    content=data.get('content', ''),
                    word_count=data.get('word_count', 0),
                    image_count=data.get('image_count', 0),
                    tags=data.get('tags', []),
                    scraped_at=data.get('scraped_at', ''),
                    file_path=file_path
                )

                if db.add_article(article):
                    imported += 1

                if imported % 1000 == 0:
                    print(f"  Imported {imported} articles from {source_key}...")

            except Exception as e:
                print(f"Error importing {file_path}: {e}")

    return imported


def import_all_sources(db: FashionArchiveDB) -> Dict[str, int]:
    """Import from all configured sources."""
    results = {}

    for source_key, config in CONFIG["sources"].items():
        articles_path = config["articles_path"]
        if os.path.exists(articles_path):
            print(f"\nImporting from {config['name']}...")
            count = import_from_scraper(db, source_key, articles_path)
            results[source_key] = count
            print(f"  Completed: {count} articles")
        else:
            print(f"Skipping {config['name']} - path not found: {articles_path}")
            results[source_key] = 0

    return results


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fashion Archive Database")
    parser.add_argument("command", choices=["import", "stats", "search", "trends"],
                       help="Command to run")
    parser.add_argument("--source", "-s", help="Source to import/filter")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--term", "-t", help="Term for trend analysis")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Result limit")

    args = parser.parse_args()

    db = FashionArchiveDB()

    if args.command == "import":
        if args.source:
            config = CONFIG["sources"].get(args.source)
            if config:
                count = import_from_scraper(db, args.source, config["articles_path"])
                print(f"Imported {count} articles from {args.source}")
            else:
                print(f"Unknown source: {args.source}")
        else:
            results = import_all_sources(db)
            print(f"\n=== Import Complete ===")
            for source, count in results.items():
                print(f"  {source}: {count}")
            print(f"  Total: {sum(results.values())}")

    elif args.command == "stats":
        stats = db.get_stats()
        print(f"\n=== Fashion Archive Statistics ===")
        print(f"Total articles: {stats['total_articles']:,}")
        print(f"Total words: {stats['total_words']:,}")
        print(f"Total images: {stats['total_images']:,}")
        print(f"\nBy Source:")
        for s in stats['by_source']:
            print(f"  {s['name']}: {s['count']:,} articles, {s['words']:,} words")
        print(f"\nTop Categories:")
        for cat, count in list(stats['top_categories'].items())[:10]:
            print(f"  {cat}: {count:,}")

    elif args.command == "search":
        if args.query:
            results = db.search(args.query, source=args.source, limit=args.limit)
            print(f"\n=== Search Results for '{args.query}' ===")
            print(f"Found {len(results)} results\n")
            for r in results[:10]:
                print(f"[{r['source']}] {r['title'][:60]}...")
                print(f"  {r['publish_date']} | {r['word_count']} words | {r['category']}")
                print()
        else:
            print("Please provide a search query with --query")

    elif args.command == "trends":
        if args.term:
            trend = db.get_trends(args.term)
            print(f"\n=== Trend: '{args.term}' ===")
            for d in trend['data']:
                bar = '█' * (d['mentions'] // 10)
                print(f"  {d['period']}: {d['mentions']:4} {bar}")
        else:
            print("Please provide a term with --term")


if __name__ == "__main__":
    main()
