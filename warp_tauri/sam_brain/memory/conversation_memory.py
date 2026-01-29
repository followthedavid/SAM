#!/usr/bin/env python3
"""
SAM Conversation Memory System

Provides persistent memory across conversations:
1. Short-term: Current conversation context
2. Long-term: Extracted facts, preferences, patterns
3. Semantic: Embeddings for similarity search

Key features:
- Automatic fact extraction from conversations
- User preference learning
- Semantic search for relevant context
- Memory consolidation (short -> long term)
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "db_path": "/Volumes/David External/sam_memory/memory.db",
    "max_short_term": 50,      # Messages to keep in short-term
    "max_context_messages": 10, # Messages to include in context
    "consolidation_threshold": 20,  # Consolidate after this many messages
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Message:
    """A single conversation message."""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str
    session_id: str
    metadata: Dict = None
    image_path: str = None
    image_hash: str = None
    image_description: str = None

@dataclass
class Fact:
    """An extracted fact about the user or context."""
    id: str
    category: str  # preference, biographical, project, skill, etc.
    subject: str
    predicate: str
    object: str
    confidence: float
    source_message_id: str
    created_at: str
    last_verified: str
    verification_count: int = 1

@dataclass
class UserPreference:
    """A learned user preference."""
    id: str
    category: str  # coding_style, communication, interests, etc.
    key: str
    value: str
    strength: float  # 0-1, how confident we are
    examples: List[str]
    created_at: str
    updated_at: str

# ============================================================================
# DATABASE
# ============================================================================

def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize memory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Messages table (short-term memory)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            metadata TEXT,
            image_path TEXT,
            image_hash TEXT,
            image_description TEXT
        )
    """)

    # Facts table (long-term memory)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source_message_id TEXT,
            created_at TEXT,
            last_verified TEXT,
            verification_count INTEGER DEFAULT 1
        )
    """)

    # Preferences table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            examples TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(category, key)
        )
    """)

    # Sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            started_at TEXT,
            ended_at TEXT,
            summary TEXT,
            message_count INTEGER DEFAULT 0
        )
    """)

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_image ON messages(image_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prefs_category ON preferences(category)")

    conn.commit()
    return conn

# ============================================================================
# MEMORY MANAGER
# ============================================================================

class ConversationMemory:
    """Manages SAM's conversation memory."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or CONFIG["db_path"]
        self.conn = init_database(self.db_path)
        self.current_session_id = None

    def start_session(self) -> str:
        """Start a new conversation session."""
        session_id = hashlib.md5(
            f"session_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        self.conn.execute("""
            INSERT INTO sessions (id, started_at, message_count)
            VALUES (?, ?, 0)
        """, (session_id, datetime.now().isoformat()))
        self.conn.commit()

        self.current_session_id = session_id
        return session_id

    def end_session(self, summary: str = None):
        """End current session with optional summary."""
        if not self.current_session_id:
            return

        self.conn.execute("""
            UPDATE sessions
            SET ended_at = ?, summary = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), summary, self.current_session_id))
        self.conn.commit()

        # Consolidate memory
        self._consolidate_session(self.current_session_id)
        self.current_session_id = None

    def add_message(self, role: str, content: str, metadata: Dict = None) -> str:
        """Add a message to memory."""
        if not self.current_session_id:
            self.start_session()

        message_id = hashlib.md5(
            f"{role}_{content}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        self.conn.execute("""
            INSERT INTO messages (id, role, content, timestamp, session_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message_id, role, content, datetime.now().isoformat(),
            self.current_session_id, json.dumps(metadata or {})
        ))

        # Update session message count
        self.conn.execute("""
            UPDATE sessions SET message_count = message_count + 1
            WHERE id = ?
        """, (self.current_session_id,))

        self.conn.commit()

        # Extract facts from user messages
        if role == "user":
            self._extract_facts(message_id, content)

        # Check if consolidation needed
        cur = self.conn.execute(
            "SELECT message_count FROM sessions WHERE id = ?",
            (self.current_session_id,)
        )
        count = cur.fetchone()[0]
        if count >= CONFIG["consolidation_threshold"]:
            self._consolidate_session(self.current_session_id)

        return message_id

    def add_image_message(
        self,
        image_path: str,
        description: str,
        user_prompt: str = None,
        metadata: Dict = None
    ) -> str:
        """
        Add a message with image context to memory.

        Args:
            image_path: Path to the image file
            description: SAM's analysis/description of the image
            user_prompt: Optional user prompt that accompanied the image
            metadata: Additional metadata

        Returns:
            Message ID
        """
        if not self.current_session_id:
            self.start_session()

        # Generate image hash for deduplication/reference
        image_hash = None
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                image_hash = hashlib.md5(f.read()).hexdigest()

        message_id = hashlib.md5(
            f"image_{image_path}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Construct content combining user prompt and image context
        content_parts = []
        if user_prompt:
            content_parts.append(user_prompt)
        content_parts.append(f"[Image: {description}]")
        content = " ".join(content_parts)

        # Merge image info into metadata
        full_metadata = metadata or {}
        full_metadata['has_image'] = True
        full_metadata['image_timestamp'] = datetime.now().isoformat()

        self.conn.execute("""
            INSERT INTO messages
            (id, role, content, timestamp, session_id, metadata, image_path, image_hash, image_description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, "user", content, datetime.now().isoformat(),
            self.current_session_id, json.dumps(full_metadata),
            image_path, image_hash, description
        ))

        # Update session message count
        self.conn.execute("""
            UPDATE sessions SET message_count = message_count + 1
            WHERE id = ?
        """, (self.current_session_id,))

        self.conn.commit()

        # Extract facts from user prompt if present
        if user_prompt:
            self._extract_facts(message_id, user_prompt)

        return message_id

    def get_last_image_context(self) -> Optional[Dict]:
        """
        Get the most recent image context from the current session.

        Returns:
            Dict with 'path', 'description', 'hash', 'timestamp' or None
        """
        if not self.current_session_id:
            return None

        cur = self.conn.execute("""
            SELECT image_path, image_description, image_hash, timestamp
            FROM messages
            WHERE session_id = ?
              AND image_path IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """, (self.current_session_id,))

        row = cur.fetchone()
        if row:
            return {
                'path': row['image_path'],
                'description': row['image_description'],
                'hash': row['image_hash'],
                'timestamp': row['timestamp']
            }
        return None

    def get_images_in_conversation(self, limit: int = 5) -> List[Dict]:
        """
        Get recent images from the current conversation session.

        Args:
            limit: Maximum number of images to return (default 5)

        Returns:
            List of dicts with 'path', 'description', 'hash', 'timestamp', 'user_prompt'
        """
        if not self.current_session_id:
            return []

        cur = self.conn.execute("""
            SELECT image_path, image_description, image_hash, timestamp, content, metadata
            FROM messages
            WHERE session_id = ?
              AND image_path IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
        """, (self.current_session_id, limit))

        images = []
        for row in cur.fetchall():
            # Extract user prompt from content (strip the [Image: ...] part)
            content = row['content'] or ''
            user_prompt = content.split('[Image:')[0].strip() if '[Image:' in content else content

            images.append({
                'path': row['image_path'],
                'description': row['image_description'],
                'hash': row['image_hash'],
                'timestamp': row['timestamp'],
                'user_prompt': user_prompt if user_prompt else None,
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })

        return list(reversed(images))  # Chronological order

    def get_context(self, max_messages: int = None, include_images: bool = True) -> List[Dict]:
        """Get recent conversation context, optionally including image context."""
        max_messages = max_messages or CONFIG["max_context_messages"]

        cur = self.conn.execute("""
            SELECT role, content, timestamp, image_path, image_description, image_hash
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (self.current_session_id, max_messages))

        messages = []
        for row in cur.fetchall():
            msg = {
                "role": row["role"],
                "content": row["content"]
            }
            # Include image context if present and requested
            if include_images and row["image_path"]:
                msg["image"] = {
                    "path": row["image_path"],
                    "description": row["image_description"],
                    "hash": row["image_hash"]
                }
            messages.append(msg)

        return list(reversed(messages))

    def get_relevant_facts(self, query: str, limit: int = 5) -> List[Dict]:
        """Get facts relevant to a query."""
        # Simple keyword matching for now
        # TODO: Add embedding-based semantic search
        keywords = set(query.lower().split())

        cur = self.conn.execute("""
            SELECT * FROM facts
            ORDER BY confidence DESC, verification_count DESC
            LIMIT 50
        """)

        relevant = []
        for row in cur.fetchall():
            fact_text = f"{row['subject']} {row['predicate']} {row['object']}".lower()
            score = len(keywords.intersection(set(fact_text.split())))
            if score > 0:
                relevant.append((score, dict(row)))

        relevant.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in relevant[:limit]]

    def get_preferences(self, category: str = None) -> List[Dict]:
        """Get user preferences."""
        if category:
            cur = self.conn.execute(
                "SELECT * FROM preferences WHERE category = ? ORDER BY strength DESC",
                (category,)
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM preferences ORDER BY strength DESC"
            )

        return [dict(row) for row in cur.fetchall()]

    def set_preference(self, category: str, key: str, value: str, example: str = None):
        """Set or update a user preference."""
        now = datetime.now().isoformat()

        # Check if exists
        cur = self.conn.execute(
            "SELECT * FROM preferences WHERE category = ? AND key = ?",
            (category, key)
        )
        existing = cur.fetchone()

        if existing:
            # Update strength and examples
            examples = json.loads(existing['examples'] or '[]')
            if example and example not in examples:
                examples.append(example)
                examples = examples[-5:]  # Keep last 5 examples

            new_strength = min(1.0, existing['strength'] + 0.1)

            self.conn.execute("""
                UPDATE preferences
                SET value = ?, strength = ?, examples = ?, updated_at = ?
                WHERE category = ? AND key = ?
            """, (value, new_strength, json.dumps(examples), now, category, key))
        else:
            pref_id = hashlib.md5(f"{category}_{key}".encode()).hexdigest()[:16]
            examples = [example] if example else []

            self.conn.execute("""
                INSERT INTO preferences
                (id, category, key, value, strength, examples, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0.5, ?, ?, ?)
            """, (pref_id, category, key, value, json.dumps(examples), now, now))

        self.conn.commit()

    def _extract_facts(self, message_id: str, content: str):
        """Extract facts from a message."""
        facts = []

        # Pattern: "I am/I'm [something]"
        am_patterns = [
            r"(?:i am|i'm|im) (?:a |an )?(\w+(?:\s+\w+)?)",
            r"(?:my name is|call me) (\w+)",
        ]
        for pattern in am_patterns:
            matches = re.findall(pattern, content.lower())
            for match in matches:
                facts.append(("user", "is", match))

        # Pattern: "I like/love/prefer [something]"
        like_patterns = [
            r"i (?:like|love|prefer|enjoy) (\w+(?:\s+\w+)?(?:\s+\w+)?)",
        ]
        for pattern in like_patterns:
            matches = re.findall(pattern, content.lower())
            for match in matches:
                facts.append(("user", "likes", match))

        # Pattern: "I work on/with [something]"
        work_patterns = [
            r"i (?:work on|work with|use|am using) (\w+(?:\s+\w+)?)",
            r"(?:my project|working on) (?:is |called )?(\w+(?:\s+\w+)?)",
        ]
        for pattern in work_patterns:
            matches = re.findall(pattern, content.lower())
            for match in matches:
                facts.append(("user", "works_with", match))

        # Save extracted facts
        now = datetime.now().isoformat()
        for subject, predicate, obj in facts:
            fact_id = hashlib.md5(f"{subject}_{predicate}_{obj}".encode()).hexdigest()[:16]

            # Check if fact exists
            cur = self.conn.execute(
                "SELECT * FROM facts WHERE subject = ? AND predicate = ? AND object = ?",
                (subject, predicate, obj)
            )
            existing = cur.fetchone()

            if existing:
                # Increase confidence
                self.conn.execute("""
                    UPDATE facts
                    SET confidence = MIN(1.0, confidence + 0.1),
                        last_verified = ?,
                        verification_count = verification_count + 1
                    WHERE id = ?
                """, (now, existing['id']))
            else:
                self.conn.execute("""
                    INSERT INTO facts
                    (id, category, subject, predicate, object, confidence,
                     source_message_id, created_at, last_verified)
                    VALUES (?, 'extracted', ?, ?, ?, 0.5, ?, ?, ?)
                """, (fact_id, subject, predicate, obj, message_id, now, now))

        self.conn.commit()

    def _consolidate_session(self, session_id: str):
        """Consolidate session memory into long-term storage."""
        # Get all messages from session
        cur = self.conn.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))

        messages = cur.fetchall()

        # Extract key topics and themes
        all_content = " ".join(m['content'] for m in messages)

        # Simple topic extraction (word frequency)
        words = re.findall(r'\b\w{4,}\b', all_content.lower())
        word_freq = {}
        for word in words:
            if word not in ['that', 'this', 'with', 'have', 'from', 'they', 'been', 'were', 'what', 'when', 'your', 'will']:
                word_freq[word] = word_freq.get(word, 0) + 1

        top_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        # Create session summary
        summary = f"Topics discussed: {', '.join(t[0] for t in top_topics[:5])}"

        self.conn.execute(
            "UPDATE sessions SET summary = ? WHERE id = ?",
            (summary, session_id)
        )

        # Prune old messages (keep only recent ones)
        self.conn.execute("""
            DELETE FROM messages
            WHERE session_id = ?
            AND id NOT IN (
                SELECT id FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (session_id, session_id, CONFIG["max_short_term"]))

        self.conn.commit()

    def build_context_prompt(self, user_message: str, include_image_context: bool = True) -> str:
        """Build a context-aware prompt with memory, including image context."""
        context_parts = []

        # Add relevant facts
        facts = self.get_relevant_facts(user_message, limit=5)
        if facts:
            fact_strs = []
            for f in facts:
                fact_strs.append(f"{f['subject']} {f['predicate']} {f['object']}")
            context_parts.append(f"Known facts: {'; '.join(fact_strs)}")

        # Add relevant preferences
        prefs = self.get_preferences()
        if prefs:
            pref_strs = [f"{p['key']}: {p['value']}" for p in prefs[:3]]
            context_parts.append(f"User preferences: {'; '.join(pref_strs)}")

        # Add image context from recent conversation
        if include_image_context:
            recent_images = self.get_images_in_conversation(limit=3)
            if recent_images:
                image_context_parts = []
                for img in recent_images:
                    desc = img.get('description', 'No description')
                    # Truncate long descriptions
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    image_context_parts.append(desc)
                context_parts.append(f"Recent images discussed: {'; '.join(image_context_parts)}")

            # Add specific last image context if relevant
            last_image = self.get_last_image_context()
            if last_image:
                # Check if user message might reference the image
                image_ref_keywords = ['image', 'picture', 'photo', 'it', 'this', 'that', 'what', 'show', 'see', 'look']
                if any(kw in user_message.lower() for kw in image_ref_keywords):
                    context_parts.append(f"Last image context: {last_image.get('description', 'Available')}")

        # Add recent context
        recent = self.get_context(5, include_images=False)
        if len(recent) > 1:
            context_parts.append("Recent conversation context available")

        if context_parts:
            return f"[Memory context: {' | '.join(context_parts)}]\n\n"
        return ""

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        stats = {}

        cur = self.conn.execute("SELECT COUNT(*) FROM messages")
        stats['total_messages'] = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM facts")
        stats['total_facts'] = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM preferences")
        stats['total_preferences'] = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM sessions")
        stats['total_sessions'] = cur.fetchone()[0]

        # Image statistics
        cur = self.conn.execute("SELECT COUNT(*) FROM messages WHERE image_path IS NOT NULL")
        stats['total_image_messages'] = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(DISTINCT image_hash) FROM messages WHERE image_hash IS NOT NULL")
        stats['unique_images'] = cur.fetchone()[0]

        cur = self.conn.execute("""
            SELECT category, COUNT(*) as count
            FROM facts GROUP BY category
        """)
        stats['facts_by_category'] = dict(cur.fetchall())

        return stats

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Conversation Memory")
    parser.add_argument("command", choices=["stats", "facts", "prefs", "images", "clear", "demo"])

    args = parser.parse_args()
    memory = ConversationMemory()

    if args.command == "stats":
        stats = memory.get_stats()
        print("\n" + "="*50)
        print("  SAM MEMORY STATS")
        print("="*50)
        print(f"\nMessages: {stats['total_messages']}")
        print(f"Facts: {stats['total_facts']}")
        print(f"Preferences: {stats['total_preferences']}")
        print(f"Sessions: {stats['total_sessions']}")
        print(f"Image messages: {stats['total_image_messages']}")
        print(f"Unique images: {stats['unique_images']}")

        if stats['facts_by_category']:
            print("\nFacts by category:")
            for cat, count in stats['facts_by_category'].items():
                print(f"  {cat}: {count}")

    elif args.command == "facts":
        cur = memory.conn.execute(
            "SELECT * FROM facts ORDER BY confidence DESC LIMIT 20"
        )
        print("\nKnown facts:")
        for row in cur.fetchall():
            print(f"  [{row['confidence']:.1f}] {row['subject']} {row['predicate']} {row['object']}")

    elif args.command == "prefs":
        prefs = memory.get_preferences()
        print("\nUser preferences:")
        for p in prefs:
            print(f"  [{p['strength']:.1f}] {p['category']}.{p['key']} = {p['value']}")

    elif args.command == "images":
        # Show recent images across all sessions
        cur = memory.conn.execute("""
            SELECT image_path, image_description, image_hash, timestamp, session_id
            FROM messages
            WHERE image_path IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        print("\nRecent images in memory:")
        for row in cur.fetchall():
            desc = row['image_description'] or 'No description'
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"  [{row['timestamp'][:10]}] {row['image_path']}")
            print(f"    -> {desc}")
            print(f"    hash: {row['image_hash'][:12]}...")

    elif args.command == "clear":
        memory.conn.execute("DELETE FROM messages")
        memory.conn.execute("DELETE FROM facts")
        memory.conn.execute("DELETE FROM preferences")
        memory.conn.execute("DELETE FROM sessions")
        memory.conn.commit()
        print("Memory cleared")

    elif args.command == "demo":
        print("\nDemo: Simulating conversation...")

        memory.start_session()

        # Simulate messages
        messages = [
            ("user", "Hi, I'm David. I'm working on an AI project called SAM."),
            ("assistant", "Nice to meet you, David! SAM sounds like an interesting project. What kind of AI is it?"),
            ("user", "It's a personal AI assistant. I use Python and Rust for development."),
            ("assistant", "Great tech stack! Python for ML and Rust for performance makes sense."),
            ("user", "Yeah, I prefer Rust over Go. And I like using MLX for training on my Mac."),
            ("assistant", "MLX is perfect for Apple Silicon. What's your training setup?"),
        ]

        for role, content in messages:
            memory.add_message(role, content)
            print(f"  {role}: {content[:50]}...")

        memory.end_session("Demo session about SAM project")

        print("\nExtracted facts:")
        cur = memory.conn.execute("SELECT * FROM facts ORDER BY confidence DESC")
        for row in cur.fetchall():
            print(f"  [{row['confidence']:.1f}] {row['subject']} {row['predicate']} {row['object']}")

        print("\nMemory context for new message:")
        context = memory.build_context_prompt("How should I train the model?")
        print(f"  {context}")

if __name__ == "__main__":
    main()
