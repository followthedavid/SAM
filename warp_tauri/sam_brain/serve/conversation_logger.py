#!/usr/bin/env python3
"""
SAM Conversation Logger - Complete Conversation History

Logs ALL conversations with SAM except:
- Content the user chose to REDACT
- Content the user chose to ENCRYPT

This creates a full audit trail while respecting privacy choices.

Privacy levels:
- FULL: Complete conversation logged
- REDACTED: Sensitive parts replaced with [REDACTED_TYPE]
- ENCRYPTED: Stored encrypted, requires key to view
- EXCLUDED: Not logged at all (only for sensitive sessions user marks private)
"""

import sqlite3
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


# Database path
DB_PATH = Path.home() / ".sam" / "conversations.db"
ENCRYPTION_SALT_PATH = Path.home() / ".sam" / ".encryption_salt"


class PrivacyLevel(Enum):
    FULL = "full"           # Complete logging
    REDACTED = "redacted"   # Sensitive parts replaced
    ENCRYPTED = "encrypted" # Stored encrypted
    EXCLUDED = "excluded"   # Not logged (user explicitly opted out)


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    THOUGHT = "thought"     # LLM's internal thinking


@dataclass
class ConversationMessage:
    """A single message in a conversation"""
    role: MessageRole
    content: str
    timestamp: float
    privacy_level: PrivacyLevel
    original_content: Optional[str] = None  # Before redaction
    metadata: dict = field(default_factory=dict)


@dataclass
class Conversation:
    """A complete conversation"""
    conversation_id: str
    start_time: float
    end_time: Optional[float] = None
    messages: list = field(default_factory=list)
    privacy_level: PrivacyLevel = PrivacyLevel.FULL
    route: str = "chat"
    model: str = "unknown"
    summary: Optional[str] = None
    tags: list = field(default_factory=list)


class ConversationLogger:
    """
    Complete conversation logging with privacy controls.

    Respects user privacy choices:
    - Redacted: Sensitive data replaced
    - Encrypted: Requires passphrase to view
    - Excluded: User explicitly marked private
    """

    def __init__(self, db_path: Optional[Path] = None, encryption_key: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Set up encryption if key provided
        self._cipher = None
        if encryption_key:
            self._setup_encryption(encryption_key)

        self._active_conversations: dict[str, Conversation] = {}

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    start_time REAL,
                    end_time REAL,
                    privacy_level TEXT,
                    route TEXT,
                    model TEXT,
                    summary TEXT,
                    tags TEXT,
                    message_count INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    privacy_level TEXT,
                    is_encrypted BOOLEAN,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(start_time)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_route ON conversations(route)
            """)

    def _setup_encryption(self, passphrase: str):
        """Set up encryption using passphrase"""
        # Load or create salt
        if ENCRYPTION_SALT_PATH.exists():
            salt = ENCRYPTION_SALT_PATH.read_bytes()
        else:
            salt = os.urandom(16)
            ENCRYPTION_SALT_PATH.write_bytes(salt)
            ENCRYPTION_SALT_PATH.chmod(0o600)

        # Derive key from passphrase
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        self._cipher = Fernet(key)

    def _encrypt(self, content: str) -> str:
        """Encrypt content"""
        if self._cipher:
            return self._cipher.encrypt(content.encode()).decode()
        return content

    def _decrypt(self, content: str) -> str:
        """Decrypt content"""
        if self._cipher:
            try:
                return self._cipher.decrypt(content.encode()).decode()
            except Exception:
                return "[ENCRYPTED - Invalid key]"
        return content

    def start_conversation(
        self,
        route: str = "chat",
        model: str = "unknown",
        privacy_level: PrivacyLevel = PrivacyLevel.FULL
    ) -> Conversation:
        """Start a new conversation"""
        conv_id = hashlib.sha256(
            f"{time.time()}{route}".encode()
        ).hexdigest()[:16]

        conv = Conversation(
            conversation_id=conv_id,
            start_time=time.time(),
            privacy_level=privacy_level,
            route=route,
            model=model
        )

        # Don't log excluded conversations
        if privacy_level != PrivacyLevel.EXCLUDED:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations
                    (conversation_id, start_time, privacy_level, route, model, message_count)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (conv_id, conv.start_time, privacy_level.value, route, model))

        self._active_conversations[conv_id] = conv
        return conv

    def log_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        privacy_level: Optional[PrivacyLevel] = None,
        metadata: Optional[dict] = None
    ) -> Optional[ConversationMessage]:
        """Log a message to a conversation"""
        conv = self._active_conversations.get(conversation_id)
        if not conv:
            return None

        # Use conversation's privacy level if not specified
        msg_privacy = privacy_level or conv.privacy_level

        # Skip excluded messages
        if msg_privacy == PrivacyLevel.EXCLUDED:
            return None

        # Process content based on privacy level
        stored_content = content
        is_encrypted = False

        if msg_privacy == PrivacyLevel.ENCRYPTED:
            stored_content = self._encrypt(content)
            is_encrypted = True
        elif msg_privacy == PrivacyLevel.REDACTED:
            # Integrate with privacy_guard for redaction
            try:
                from core.privacy_guard import guard_outgoing
                result = guard_outgoing(content)
                if not result["safe"]:
                    stored_content = result["redacted"]
            except ImportError:
                pass  # Privacy guard not available

        msg = ConversationMessage(
            role=role,
            content=stored_content,
            timestamp=time.time(),
            privacy_level=msg_privacy,
            original_content=content if msg_privacy != PrivacyLevel.FULL else None,
            metadata=metadata or {}
        )

        conv.messages.append(msg)

        # Log to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages
                (conversation_id, role, content, timestamp, privacy_level, is_encrypted, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                role.value,
                stored_content,
                msg.timestamp,
                msg_privacy.value,
                is_encrypted,
                json.dumps(metadata) if metadata else None
            ))

            # Update message count
            conn.execute("""
                UPDATE conversations SET message_count = message_count + 1
                WHERE conversation_id = ?
            """, (conversation_id,))

        return msg

    def log_thought(
        self,
        conversation_id: str,
        thought: str,
        phase: str = "reasoning"
    ) -> Optional[ConversationMessage]:
        """Log an LLM thought (internal thinking)"""
        return self.log_message(
            conversation_id,
            MessageRole.THOUGHT,
            thought,
            metadata={"phase": phase}
        )

    def log_user_message(
        self,
        conversation_id: str,
        content: str,
        privacy_level: Optional[PrivacyLevel] = None
    ) -> Optional[ConversationMessage]:
        """Log a user message"""
        return self.log_message(conversation_id, MessageRole.USER, content, privacy_level)

    def log_assistant_message(
        self,
        conversation_id: str,
        content: str,
        privacy_level: Optional[PrivacyLevel] = None
    ) -> Optional[ConversationMessage]:
        """Log an assistant message"""
        return self.log_message(conversation_id, MessageRole.ASSISTANT, content, privacy_level)

    def complete_conversation(
        self,
        conversation_id: str,
        summary: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Optional[Conversation]:
        """Complete and finalize a conversation"""
        conv = self._active_conversations.get(conversation_id)
        if not conv:
            return None

        conv.end_time = time.time()
        conv.summary = summary
        conv.tags = tags or []

        # Update database
        if conv.privacy_level != PrivacyLevel.EXCLUDED:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE conversations
                    SET end_time = ?, summary = ?, tags = ?
                    WHERE conversation_id = ?
                """, (
                    conv.end_time,
                    summary,
                    json.dumps(tags) if tags else None,
                    conversation_id
                ))

        del self._active_conversations[conversation_id]
        return conv

    def mark_private(self, conversation_id: str) -> bool:
        """Mark a conversation as private (excluded from logs)"""
        with sqlite3.connect(self.db_path) as conn:
            # Delete messages
            conn.execute("""
                DELETE FROM messages WHERE conversation_id = ?
            """, (conversation_id,))

            # Delete conversation
            conn.execute("""
                DELETE FROM conversations WHERE conversation_id = ?
            """, (conversation_id,))

            return True

    def get_conversation(self, conversation_id: str, decrypt: bool = False) -> Optional[dict]:
        """Get a conversation with all messages"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            conv = conn.execute("""
                SELECT * FROM conversations WHERE conversation_id = ?
            """, (conversation_id,)).fetchone()

            if not conv:
                return None

            messages = conn.execute("""
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp
            """, (conversation_id,)).fetchall()

            result = {
                "conversation": dict(conv),
                "messages": []
            }

            for msg in messages:
                msg_dict = dict(msg)
                if decrypt and msg_dict["is_encrypted"]:
                    msg_dict["content"] = self._decrypt(msg_dict["content"])
                result["messages"].append(msg_dict)

            return result

    def get_recent_conversations(
        self,
        limit: int = 50,
        route: Optional[str] = None
    ) -> list:
        """Get recent conversations"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM conversations"
            params = []

            if route:
                sql += " WHERE route = ?"
                params.append(route)

            sql += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)

            results = conn.execute(sql, params).fetchall()
            return [dict(r) for r in results]

    def search_conversations(
        self,
        query: str,
        include_thoughts: bool = False,
        limit: int = 100
    ) -> list:
        """Search through conversations"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            role_filter = ""
            if not include_thoughts:
                role_filter = "AND m.role != 'thought'"

            results = conn.execute(f"""
                SELECT DISTINCT c.*, m.content as matching_content
                FROM conversations c
                JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE m.content LIKE ? {role_filter}
                AND m.is_encrypted = 0
                ORDER BY c.start_time DESC
                LIMIT ?
            """, (f"%{query}%", limit)).fetchall()

            return [dict(r) for r in results]

    def export_conversation(
        self,
        conversation_id: str,
        filepath: Path,
        decrypt: bool = False,
        include_thoughts: bool = True
    ) -> bool:
        """Export a conversation to JSON"""
        data = self.get_conversation(conversation_id, decrypt=decrypt)
        if not data:
            return False

        if not include_thoughts:
            data["messages"] = [
                m for m in data["messages"] if m["role"] != "thought"
            ]

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return True

    def get_stats(self) -> dict:
        """Get conversation statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conv_count = conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]

            msg_count = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]

            thought_count = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE role = 'thought'"
            ).fetchone()[0]

            encrypted_count = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE is_encrypted = 1"
            ).fetchone()[0]

            routes = conn.execute("""
                SELECT route, COUNT(*) as count
                FROM conversations
                GROUP BY route
                ORDER BY count DESC
            """).fetchall()

            return {
                "total_conversations": conv_count,
                "total_messages": msg_count,
                "thought_messages": thought_count,
                "encrypted_messages": encrypted_count,
                "routes": {r[0]: r[1] for r in routes},
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0
            }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logger = ConversationLogger()

    if len(sys.argv) < 2:
        print("SAM Conversation Logger")
        print("\nLogs ALL conversations except redacted/encrypted/excluded content.")
        print("\nUsage:")
        print("  python conversation_logger.py stats        # Show statistics")
        print("  python conversation_logger.py recent [n]   # Recent conversations")
        print("  python conversation_logger.py show <id>    # Show conversation")
        print("  python conversation_logger.py search <q>   # Search conversations")
        print("  python conversation_logger.py export <id> <file>")
        print("  python conversation_logger.py delete <id>  # Mark as private/delete")
        print("\nPrivacy levels:")
        print("  FULL      - Complete logging")
        print("  REDACTED  - Sensitive parts replaced")
        print("  ENCRYPTED - Stored encrypted (needs key)")
        print("  EXCLUDED  - Not logged at all")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "stats":
        stats = logger.get_stats()
        print("\n📊 Conversation Logger Statistics\n")
        print(f"  Total conversations: {stats['total_conversations']}")
        print(f"  Total messages:      {stats['total_messages']}")
        print(f"  Thought messages:    {stats['thought_messages']}")
        print(f"  Encrypted messages:  {stats['encrypted_messages']}")
        print(f"  Database size:       {stats['db_size_mb']} MB")
        print("\n  Routes:")
        for route, count in stats["routes"].items():
            print(f"    {route}: {count}")
        print()

    elif cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        convs = logger.get_recent_conversations(limit)

        print(f"\n📋 Recent {len(convs)} Conversations\n")
        for c in convs:
            ts = datetime.fromtimestamp(c["start_time"]).strftime("%Y-%m-%d %H:%M")
            summary = c["summary"][:40] + "..." if c["summary"] and len(c["summary"]) > 40 else (c["summary"] or "No summary")
            privacy_icon = {"full": "📝", "redacted": "🔒", "encrypted": "🔐"}.get(c["privacy_level"], "")

            print(f"  {privacy_icon} [{ts}] {c['conversation_id']} ({c['route']})")
            print(f"     Messages: {c['message_count']} | {summary}")
            print()

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: python conversation_logger.py show <conversation_id>")
            sys.exit(1)

        conv_id = sys.argv[2]
        data = logger.get_conversation(conv_id)

        if not data:
            print(f"Conversation not found: {conv_id}")
            sys.exit(1)

        conv = data["conversation"]
        messages = data["messages"]

        print(f"\n📝 Conversation: {conv_id}\n")
        print(f"  Route:    {conv['route']}")
        print(f"  Model:    {conv['model']}")
        print(f"  Privacy:  {conv['privacy_level']}")
        print(f"  Messages: {len(messages)}")
        print()

        print("═" * 60)
        for msg in messages:
            role_icon = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
                "thought": "💭"
            }.get(msg["role"], "?")

            ts = datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M:%S")
            encrypted_tag = " [ENCRYPTED]" if msg["is_encrypted"] else ""

            print(f"\n{role_icon} [{ts}] {msg['role'].upper()}{encrypted_tag}")
            print(f"   {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")

        print("\n" + "═" * 60)

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python conversation_logger.py search <query>")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        results = logger.search_conversations(query)

        print(f"\n🔍 Search results for \"{query}\":\n")
        for r in results:
            ts = datetime.fromtimestamp(r["start_time"]).strftime("%Y-%m-%d %H:%M")
            print(f"  [{ts}] {r['conversation_id']} ({r['route']})")
            print(f"     Match: \"{r['matching_content'][:60]}...\"")
            print()

    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: python conversation_logger.py export <conversation_id> <file.json>")
            sys.exit(1)

        conv_id = sys.argv[2]
        filepath = Path(sys.argv[3])

        if logger.export_conversation(conv_id, filepath):
            print(f"✅ Exported to {filepath}")
        else:
            print(f"❌ Conversation not found: {conv_id}")

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: python conversation_logger.py delete <conversation_id>")
            sys.exit(1)

        conv_id = sys.argv[2]
        if logger.mark_private(conv_id):
            print(f"✅ Conversation {conv_id} marked as private and deleted")
        else:
            print(f"❌ Failed to delete conversation")

    else:
        print(f"Unknown command: {cmd}")
