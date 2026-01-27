#!/usr/bin/env python3
"""
Character.AI Conversation Dumps Finder
Searches for and processes public CAI conversation dumps/exports

Sources:
- GitHub repositories with CAI exports
- Archive.org CAI dumps
- Kaggle datasets
- HuggingFace datasets

These are GOLD for roleplay training - actual back-and-forth exchanges
"""

import os
import re
import json
import time
import hashlib
import logging
import sqlite3
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/cai_dumps",
    "db_path": "/Volumes/David External/cai_dumps/cai_index.db",
    "user_agent": "SAM-Training-Collector/1.0",
}

# Known sources for CAI data
KNOWN_SOURCES = {
    # HuggingFace datasets
    "hf_datasets": [
        "ehartford/wizard_vicuna_70k_unfiltered",  # Contains some CAI-style data
        "anon8231489123/ShareGPT_Vicuna_unfiltered",
        "RyokoAI/ShareGPT52K",
    ],

    # GitHub search terms
    "github_searches": [
        "character.ai export",
        "character ai conversations",
        "cai chat export",
        "character.ai dump",
    ],

    # Archive.org collections
    "archive_collections": [
        "characterai_conversations",
    ],
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CAIConversation:
    """A Character.AI conversation."""
    id: str
    character_name: str
    character_description: str
    messages: List[Dict[str, str]]  # {"role": "user/char", "content": "..."}
    turn_count: int
    word_count: int
    source: str
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
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            character_name TEXT,
            character_description TEXT,
            messages TEXT,
            turn_count INTEGER,
            word_count INTEGER,
            source TEXT,
            source_url TEXT,
            indexed_at TEXT,
            processed INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            url TEXT,
            type TEXT,
            status TEXT,
            conversation_count INTEGER,
            last_checked TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_character ON conversations(character_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON conversations(source)")

    conn.commit()
    return conn

# ============================================================================
# SCRAPERS/DOWNLOADERS
# ============================================================================

class CAIDumpsFinder:
    """Finder and processor for Character.AI conversation dumps."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CONFIG["user_agent"],
        })
        self.conn = init_database(CONFIG["db_path"])
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        log_dir = Path(CONFIG["storage_root"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("cai_dumps")
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_dir / "finder.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console)

        return logger

    def search_github(self, query: str) -> List[Dict]:
        """Search GitHub for CAI-related repositories."""
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('items', [])
        except Exception as e:
            self.logger.error(f"GitHub search error: {e}")
            return []

    def search_huggingface(self, query: str = "roleplay") -> List[Dict]:
        """Search HuggingFace for relevant datasets."""
        url = "https://huggingface.co/api/datasets"
        params = {
            "search": query,
            "limit": 50,
        }

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"HuggingFace search error: {e}")
            return []

    def download_hf_dataset(self, dataset_id: str, output_dir: Path) -> bool:
        """Download a HuggingFace dataset."""
        try:
            # Use HuggingFace Hub
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=dataset_id,
                repo_type="dataset",
                local_dir=str(output_dir / dataset_id.replace('/', '_')),
            )
            return True
        except ImportError:
            self.logger.warning("huggingface_hub not installed. Install with: pip install huggingface_hub")
            return False
        except Exception as e:
            self.logger.error(f"HF download error: {e}")
            return False

    def parse_cai_export(self, filepath: Path) -> Generator[CAIConversation, None, None]:
        """Parse a Character.AI export file."""
        try:
            # CAI exports are typically JSON
            if filepath.suffix == '.json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle different export formats
                if isinstance(data, list):
                    for conv in data:
                        yield self._parse_conversation(conv, str(filepath))
                elif isinstance(data, dict):
                    if 'conversations' in data:
                        for conv in data['conversations']:
                            yield self._parse_conversation(conv, str(filepath))
                    elif 'messages' in data:
                        yield self._parse_conversation(data, str(filepath))

            # Handle JSONL format
            elif filepath.suffix == '.jsonl':
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            conv = json.loads(line)
                            yield self._parse_conversation(conv, str(filepath))

        except Exception as e:
            self.logger.error(f"Parse error for {filepath}: {e}")

    def _parse_conversation(self, data: Dict, source: str) -> Optional[CAIConversation]:
        """Parse a single conversation from export data."""
        try:
            # Extract character info
            char_name = data.get('character_name') or data.get('char') or data.get('name', 'Unknown')
            char_desc = data.get('character_description') or data.get('description', '')

            # Extract messages
            messages = []
            raw_messages = data.get('messages') or data.get('conversation') or data.get('turns', [])

            for msg in raw_messages:
                if isinstance(msg, dict):
                    role = msg.get('role') or msg.get('sender') or msg.get('author', 'unknown')
                    content = msg.get('content') or msg.get('text') or msg.get('message', '')

                    # Normalize role names
                    if role.lower() in ['user', 'human', 'you']:
                        role = 'user'
                    elif role.lower() in ['assistant', 'char', 'character', 'ai', 'bot']:
                        role = 'character'

                    if content:
                        messages.append({"role": role, "content": content})

            if not messages:
                return None

            # Calculate stats
            full_text = ' '.join(m['content'] for m in messages)
            word_count = len(full_text.split())

            return CAIConversation(
                id=hashlib.md5(f"cai_{char_name}_{len(messages)}_{word_count}".encode()).hexdigest()[:16],
                character_name=char_name,
                character_description=char_desc,
                messages=messages,
                turn_count=len(messages),
                word_count=word_count,
                source="cai_export",
                source_url=source,
                indexed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Conversation parse error: {e}")
            return None

    def _save_conversation(self, conv: CAIConversation):
        """Save conversation to database."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO conversations (
                    id, character_name, character_description, messages,
                    turn_count, word_count, source, source_url, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv.id, conv.character_name, conv.character_description,
                json.dumps(conv.messages), conv.turn_count, conv.word_count,
                conv.source, conv.source_url, conv.indexed_at
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    def process_directory(self, directory: Path):
        """Process all JSON/JSONL files in a directory."""
        self.logger.info(f"Processing directory: {directory}")

        count = 0
        for filepath in directory.rglob('*.json'):
            for conv in self.parse_cai_export(filepath):
                if conv:
                    self._save_conversation(conv)
                    count += 1

        for filepath in directory.rglob('*.jsonl'):
            for conv in self.parse_cai_export(filepath):
                if conv:
                    self._save_conversation(conv)
                    count += 1

        self.logger.info(f"Processed {count} conversations")
        return count

    def find_sources(self):
        """Find potential CAI data sources."""
        self.logger.info("=" * 60)
        self.logger.info("Searching for Character.AI Data Sources")
        self.logger.info("=" * 60)

        sources_found = []

        # Search GitHub
        self.logger.info("\n📦 Searching GitHub...")
        for query in KNOWN_SOURCES["github_searches"]:
            repos = self.search_github(query)
            for repo in repos[:5]:  # Top 5 per query
                source = {
                    "type": "github",
                    "name": repo['full_name'],
                    "url": repo['html_url'],
                    "stars": repo['stargazers_count'],
                    "description": repo.get('description', ''),
                }
                sources_found.append(source)
                self.logger.info(f"  ⭐ {repo['full_name']} ({repo['stargazers_count']} stars)")

        # Search HuggingFace
        self.logger.info("\n🤗 Searching HuggingFace...")
        for query in ["roleplay", "character ai", "chat"]:
            datasets = self.search_huggingface(query)
            for ds in datasets[:5]:
                source = {
                    "type": "huggingface",
                    "name": ds.get('id', ''),
                    "url": f"https://huggingface.co/datasets/{ds.get('id', '')}",
                    "downloads": ds.get('downloads', 0),
                    "description": ds.get('description', ''),
                }
                sources_found.append(source)
                self.logger.info(f"  📊 {ds.get('id', '')} ({ds.get('downloads', 0)} downloads)")

        # Save sources
        sources_file = Path(CONFIG["storage_root"]) / "found_sources.json"
        sources_file.parent.mkdir(parents=True, exist_ok=True)
        with open(sources_file, 'w') as f:
            json.dump(sources_found, f, indent=2)

        self.logger.info(f"\n✅ Found {len(sources_found)} potential sources")
        self.logger.info(f"   Saved to: {sources_file}")

        return sources_found

    def export_training_data(self, output_path: str, min_turns: int = 4):
        """Export conversations as training data."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        cursor = self.conn.execute("""
            SELECT * FROM conversations
            WHERE turn_count >= ?
            ORDER BY turn_count DESC
        """, (min_turns,))

        training_data = []

        for row in cursor:
            messages = json.loads(row['messages'])

            # Format as training conversation
            entry = {
                "character": {
                    "name": row['character_name'],
                    "description": row['character_description'],
                },
                "conversation": messages,
                "metadata": {
                    "turn_count": row['turn_count'],
                    "word_count": row['word_count'],
                    "source": row['source'],
                }
            }
            training_data.append(entry)

        # Save as JSONL
        output_file = output_dir / "cai_conversations.jsonl"
        with open(output_file, 'w') as f:
            for entry in training_data:
                f.write(json.dumps(entry) + '\n')

        self.logger.info(f"Exported {len(training_data)} conversations to {output_file}")
        return len(training_data)

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Character.AI Dumps Finder")
    parser.add_argument('command', choices=['find', 'process', 'export', 'stats'])
    parser.add_argument('--directory', help='Directory to process')
    parser.add_argument('--output', default=CONFIG["storage_root"])
    parser.add_argument('--min-turns', type=int, default=4)

    args = parser.parse_args()

    finder = CAIDumpsFinder()

    if args.command == 'find':
        finder.find_sources()

    elif args.command == 'process':
        if args.directory:
            finder.process_directory(Path(args.directory))
        else:
            # Process default storage directory
            finder.process_directory(Path(CONFIG["storage_root"]) / "raw")

    elif args.command == 'export':
        finder.export_training_data(args.output, args.min_turns)

    elif args.command == 'stats':
        cursor = finder.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT character_name) as characters,
                SUM(turn_count) as total_turns,
                AVG(turn_count) as avg_turns,
                SUM(word_count) as total_words
            FROM conversations
        """)
        stats = cursor.fetchone()

        print("\n🤖 Character.AI Dumps Stats")
        print("=" * 40)
        print(f"Total conversations: {stats['total']:,}")
        print(f"Unique characters:   {stats['characters']:,}")
        print(f"Total turns:         {stats['total_turns']:,}")
        print(f"Avg turns/conv:      {stats['avg_turns']:.1f}")
        print(f"Total words:         {stats['total_words']:,}")

        # Top characters
        print("\n📊 Top Characters:")
        cursor = finder.conn.execute("""
            SELECT character_name, COUNT(*) as count, SUM(turn_count) as turns
            FROM conversations
            GROUP BY character_name
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor:
            print(f"  {row['character_name'][:30]:30} | {row['count']:4} convs | {row['turns']:6} turns")

if __name__ == "__main__":
    main()
