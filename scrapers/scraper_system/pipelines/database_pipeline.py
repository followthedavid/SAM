"""
SAM Scraper System - Database Pipeline

Scrapy pipeline that saves items to PostgreSQL.
"""

import logging
from typing import Any

from ..storage.database import get_database, ScrapedItem

logger = logging.getLogger(__name__)


class DatabasePipeline:
    """
    Scrapy pipeline to save items to PostgreSQL.

    Automatically handles:
    - Deduplication (via content hash)
    - Progress tracking
    - Statistics
    """

    def __init__(self):
        self.db = None
        self.items_saved = 0
        self.items_skipped = 0

    def open_spider(self, spider):
        """Called when spider opens."""
        self.db = get_database()
        self.items_saved = 0
        self.items_skipped = 0
        logger.info(f"Database pipeline opened for {spider.name}")

    def close_spider(self, spider):
        """Called when spider closes."""
        logger.info(
            f"Database pipeline closed for {spider.name}: "
            f"{self.items_saved} saved, {self.items_skipped} skipped"
        )

    def process_item(self, item: Any, spider) -> Any:
        """Process an item and save to database."""
        if not self.db:
            return item

        # Convert to ScrapedItem if needed
        if isinstance(item, ScrapedItem):
            scraped_item = item
        elif isinstance(item, dict):
            scraped_item = ScrapedItem(
                source=item.get("source", spider.source if hasattr(spider, "source") else spider.name),
                url=item.get("url", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                metadata=item.get("metadata", {}),
            )
        else:
            logger.warning(f"Unknown item type: {type(item)}")
            return item

        # Generate content hash if not present
        if not scraped_item.content_hash:
            scraped_item.content_hash = self.db.hash_content(scraped_item.content)

        # Save to database (handles dedup internally)
        item_id = self.db.save_item(scraped_item)

        if item_id:
            self.items_saved += 1
            logger.debug(f"Saved item {item_id}: {scraped_item.url}")
        else:
            self.items_skipped += 1
            logger.debug(f"Skipped duplicate: {scraped_item.url}")

        return item
