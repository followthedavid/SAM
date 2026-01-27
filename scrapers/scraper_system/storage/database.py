"""
SAM Scraper System - PostgreSQL Storage Layer

Handles:
- Job history and progress tracking
- Content deduplication
- Scraper metadata
- Statistics

PostgreSQL: 35 years old, will outlive us all.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# PostgreSQL via psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("psycopg2 not installed. Run: pip install psycopg2-binary")


@dataclass
class ScrapedItem:
    """A scraped item record."""
    id: Optional[int] = None
    source: str = ""
    url: str = ""
    content_hash: str = ""
    title: str = ""
    content: str = ""
    metadata: Dict[str, Any] = None
    scraped_at: Optional[datetime] = None
    processed: bool = False

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class JobRecord:
    """A scraper job record."""
    id: Optional[int] = None
    task_name: str = ""
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_scraped: int = 0
    bytes_downloaded: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class ScraperDatabase:
    """
    PostgreSQL database for scraper system.

    Tables:
    - scraped_items: All scraped content (with deduplication)
    - scraper_jobs: Job history
    - scraper_progress: Resume state for each scraper
    - scraper_stats: Aggregate statistics
    """

    def __init__(self, connection_string: str = None):
        if not POSTGRES_AVAILABLE:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary")

        if connection_string is None:
            from ..config.settings import POSTGRES_URL
            connection_string = POSTGRES_URL

        self.connection_string = connection_string
        self._conn = None

    # =========================================================================
    # Connection Management
    # =========================================================================

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self._conn = psycopg2.connect(self.connection_string)
            self._conn.autocommit = False
            logger.info("Connected to PostgreSQL")
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            logger.info("Make sure PostgreSQL is running: brew services start postgresql")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def cursor(self):
        """Get a database cursor with automatic commit/rollback."""
        if not self._conn:
            self.connect()

        cursor = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    # =========================================================================
    # Schema Management
    # =========================================================================

    def init_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self.cursor() as cur:
            # Scraped items table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scraped_items (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    url TEXT NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    title TEXT,
                    content TEXT,
                    metadata JSONB DEFAULT '{}',
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    UNIQUE(content_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_items_source ON scraped_items(source);
                CREATE INDEX IF NOT EXISTS idx_items_hash ON scraped_items(content_hash);
                CREATE INDEX IF NOT EXISTS idx_items_processed ON scraped_items(processed);
            """)

            # Jobs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scraper_jobs (
                    id SERIAL PRIMARY KEY,
                    task_name VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    items_scraped INTEGER DEFAULT 0,
                    bytes_downloaded BIGINT DEFAULT 0,
                    error TEXT,
                    metadata JSONB DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_task ON scraper_jobs(task_name);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON scraper_jobs(status);
            """)

            # Progress table (for resuming)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scraper_progress (
                    source VARCHAR(50) PRIMARY KEY,
                    last_page INTEGER DEFAULT 0,
                    last_url TEXT,
                    last_id TEXT,
                    total_items INTEGER DEFAULT 0,
                    metadata JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Stats table (aggregates)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scraper_stats (
                    source VARCHAR(50) PRIMARY KEY,
                    total_items INTEGER DEFAULT 0,
                    total_bytes BIGINT DEFAULT 0,
                    last_run TIMESTAMP,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0
                );
            """)

            logger.info("Database schema initialized")

    # =========================================================================
    # Scraped Items
    # =========================================================================

    @staticmethod
    def hash_content(content: str) -> str:
        """Generate SHA-256 hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    def item_exists(self, content_hash: str) -> bool:
        """Check if item already exists (deduplication)."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM scraped_items WHERE content_hash = %s LIMIT 1",
                (content_hash,)
            )
            return cur.fetchone() is not None

    def url_exists(self, url: str) -> bool:
        """Check if URL has been scraped."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM scraped_items WHERE url = %s LIMIT 1",
                (url,)
            )
            return cur.fetchone() is not None

    def save_item(self, item: ScrapedItem) -> Optional[int]:
        """Save a scraped item (skips if duplicate)."""
        if not item.content_hash:
            item.content_hash = self.hash_content(item.content)

        # Skip if duplicate
        if self.item_exists(item.content_hash):
            logger.debug(f"Skipping duplicate: {item.url}")
            return None

        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO scraped_items (source, url, content_hash, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
                RETURNING id
            """, (
                item.source,
                item.url,
                item.content_hash,
                item.title,
                item.content,
                psycopg2.extras.Json(item.metadata),
            ))
            result = cur.fetchone()
            return result["id"] if result else None

    def save_items_batch(self, items: List[ScrapedItem]) -> int:
        """Save multiple items efficiently."""
        saved = 0
        with self.cursor() as cur:
            for item in items:
                if not item.content_hash:
                    item.content_hash = self.hash_content(item.content)

            values = [
                (i.source, i.url, i.content_hash, i.title, i.content, psycopg2.extras.Json(i.metadata))
                for i in items
            ]

            execute_values(
                cur,
                """
                INSERT INTO scraped_items (source, url, content_hash, title, content, metadata)
                VALUES %s
                ON CONFLICT (content_hash) DO NOTHING
                """,
                values,
            )
            saved = cur.rowcount

        return saved

    def get_items(
        self,
        source: str = None,
        processed: bool = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ScrapedItem]:
        """Get scraped items with filters."""
        with self.cursor() as cur:
            conditions = []
            params = []

            if source:
                conditions.append("source = %s")
                params.append(source)

            if processed is not None:
                conditions.append("processed = %s")
                params.append(processed)

            where = " AND ".join(conditions) if conditions else "1=1"
            params.extend([limit, offset])

            cur.execute(f"""
                SELECT * FROM scraped_items
                WHERE {where}
                ORDER BY scraped_at DESC
                LIMIT %s OFFSET %s
            """, params)

            return [ScrapedItem(**row) for row in cur.fetchall()]

    def mark_processed(self, item_ids: List[int]) -> None:
        """Mark items as processed."""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE scraped_items SET processed = TRUE WHERE id = ANY(%s)",
                (item_ids,)
            )

    # =========================================================================
    # Job Tracking
    # =========================================================================

    def start_job(self, task_name: str) -> int:
        """Record a job starting."""
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO scraper_jobs (task_name, status, started_at)
                VALUES (%s, 'running', CURRENT_TIMESTAMP)
                RETURNING id
            """, (task_name,))
            return cur.fetchone()["id"]

    def complete_job(
        self,
        job_id: int,
        items_scraped: int,
        bytes_downloaded: int,
        error: str = None,
    ) -> None:
        """Record a job completing."""
        status = "failed" if error else "completed"
        with self.cursor() as cur:
            cur.execute("""
                UPDATE scraper_jobs
                SET status = %s,
                    completed_at = CURRENT_TIMESTAMP,
                    items_scraped = %s,
                    bytes_downloaded = %s,
                    error = %s
                WHERE id = %s
            """, (status, items_scraped, bytes_downloaded, error, job_id))

    def get_job_history(self, task_name: str = None, limit: int = 50) -> List[JobRecord]:
        """Get job history."""
        with self.cursor() as cur:
            if task_name:
                cur.execute("""
                    SELECT * FROM scraper_jobs
                    WHERE task_name = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (task_name, limit))
            else:
                cur.execute("""
                    SELECT * FROM scraper_jobs
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (limit,))

            return [JobRecord(**row) for row in cur.fetchall()]

    # =========================================================================
    # Progress Tracking (for resume)
    # =========================================================================

    def get_progress(self, source: str) -> Dict[str, Any]:
        """Get progress for a source (for resuming)."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM scraper_progress WHERE source = %s",
                (source,)
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
                # Merge metadata into result if present
                if result.get("metadata"):
                    result.update(result["metadata"])
                return result
            return {
                "source": source,
                "last_page": 0,
                "last_url": None,
                "last_id": None,
                "total_items": 0,
            }

    def save_progress(self, source: str, **kwargs) -> None:
        """
        Save progress for a source (for resuming).

        Standard fields: last_page, last_url, last_id, total_items
        Any additional kwargs are stored in metadata JSON column.
        """
        # Extract standard fields
        last_page = kwargs.pop("last_page", None)
        last_url = kwargs.pop("last_url", None)
        last_id = kwargs.pop("last_id", None)
        total_items = kwargs.pop("total_items", None)

        # Remaining kwargs go into metadata
        metadata = kwargs if kwargs else None

        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO scraper_progress (source, last_page, last_url, last_id, total_items, metadata, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (source) DO UPDATE SET
                    last_page = COALESCE(EXCLUDED.last_page, scraper_progress.last_page),
                    last_url = COALESCE(EXCLUDED.last_url, scraper_progress.last_url),
                    last_id = COALESCE(EXCLUDED.last_id, scraper_progress.last_id),
                    total_items = COALESCE(EXCLUDED.total_items, scraper_progress.total_items),
                    metadata = COALESCE(EXCLUDED.metadata, scraper_progress.metadata),
                    updated_at = CURRENT_TIMESTAMP
            """, (source, last_page, last_url, last_id, total_items, psycopg2.extras.Json(metadata) if metadata else None))

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self, source: str = None) -> Dict[str, Any]:
        """Get statistics for a source or all sources."""
        with self.cursor() as cur:
            if source:
                cur.execute("""
                    SELECT
                        source,
                        COUNT(*) as total_items,
                        SUM(LENGTH(content)) as total_bytes,
                        MAX(scraped_at) as last_scraped,
                        COUNT(CASE WHEN processed THEN 1 END) as processed_count
                    FROM scraped_items
                    WHERE source = %s
                    GROUP BY source
                """, (source,))
            else:
                cur.execute("""
                    SELECT
                        source,
                        COUNT(*) as total_items,
                        SUM(LENGTH(content)) as total_bytes,
                        MAX(scraped_at) as last_scraped,
                        COUNT(CASE WHEN processed THEN 1 END) as processed_count
                    FROM scraped_items
                    GROUP BY source
                    ORDER BY total_items DESC
                """)

            rows = cur.fetchall()
            return {row["source"]: dict(row) for row in rows}

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics."""
        with self.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_items,
                    COUNT(DISTINCT source) as total_sources,
                    SUM(LENGTH(content)) as total_bytes,
                    COUNT(CASE WHEN processed THEN 1 END) as processed_count
                FROM scraped_items
            """)
            items_stats = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    COUNT(*) as total_jobs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs
                FROM scraper_jobs
            """)
            jobs_stats = dict(cur.fetchone())

            return {**items_stats, **jobs_stats}


# =============================================================================
# Singleton instance
# =============================================================================

_db: Optional[ScraperDatabase] = None


def get_database() -> ScraperDatabase:
    """Get the singleton database instance."""
    global _db

    if _db is None:
        _db = ScraperDatabase()
        _db.connect()
        _db.init_schema()

    return _db


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing database connection...")
    db = get_database()

    print("\nGlobal stats:")
    stats = db.get_global_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nStats by source:")
    source_stats = db.get_stats()
    for source, data in source_stats.items():
        print(f"  {source}: {data['total_items']} items")
