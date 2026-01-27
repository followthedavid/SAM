#!/usr/bin/env python3
"""
SAM Terminal Session Manager

Manages multiple terminal sessions (SAM, Claude, etc.) with:
- Session persistence (survives crashes)
- Automatic restoration on restart
- Searchable history across all sessions
- Redaction and privacy controls
- Session state snapshots

Each terminal is a "session" that can be:
- Active (currently running)
- Suspended (process stopped, state saved)
- Restored (restarted from saved state)
- Archived (closed but searchable)
"""

import sqlite3
import json
import time
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


DB_PATH = Path.home() / ".sam" / "terminal_sessions.db"


class SessionType(Enum):
    SAM_LOCAL = "sam_local"      # Local SAM LLM
    CLAUDE = "claude"            # Claude Code CLI
    SHELL = "shell"              # Regular shell
    CUSTOM = "custom"            # Custom command


class SessionState(Enum):
    ACTIVE = "active"            # Currently running
    SUSPENDED = "suspended"      # Paused, can resume
    RESTORED = "restored"        # Just restored from save
    CRASHED = "crashed"          # Crashed, needs recovery
    ARCHIVED = "archived"        # Closed, in history
    REDACTED = "redacted"        # Content redacted


@dataclass
class TerminalMessage:
    """A single message in a terminal session"""
    id: int
    timestamp: float
    direction: str  # "input" or "output"
    content: str
    is_redacted: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class TerminalSession:
    """A terminal session"""
    session_id: str
    session_type: SessionType
    name: str
    state: SessionState
    created_at: float
    updated_at: float
    pid: Optional[int] = None
    working_dir: Optional[str] = None
    environment: dict = field(default_factory=dict)
    message_count: int = 0
    tags: List[str] = field(default_factory=list)


class TerminalSessionManager:
    """
    Manages multiple terminal sessions with persistence.

    Features:
    - Create/restore/archive sessions
    - Log all terminal I/O
    - Search across sessions
    - Redact sensitive content
    - Crash recovery
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._active_sessions: dict[str, TerminalSession] = {}

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_type TEXT,
                    name TEXT,
                    state TEXT,
                    created_at REAL,
                    updated_at REAL,
                    pid INTEGER,
                    working_dir TEXT,
                    environment TEXT,
                    message_count INTEGER DEFAULT 0,
                    tags TEXT,
                    scroll_position INTEGER DEFAULT 0,
                    cursor_position TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    timestamp REAL,
                    direction TEXT,
                    content TEXT,
                    is_redacted BOOLEAN DEFAULT 0,
                    redacted_content TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_content
                ON messages(content)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_state
                ON sessions(state)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_type
                ON sessions(session_type)
            """)
            # Full-text search for content
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                USING fts5(content, session_id, content='messages', content_rowid='id')
            """)

    def create_session(
        self,
        session_type: SessionType,
        name: Optional[str] = None,
        working_dir: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TerminalSession:
        """Create a new terminal session"""
        session_id = hashlib.sha256(
            f"{time.time()}{session_type.value}".encode()
        ).hexdigest()[:16]

        if not name:
            # Auto-generate name
            count = len(self.get_sessions_by_type(session_type))
            name = f"{session_type.value} #{count + 1}"

        session = TerminalSession(
            session_id=session_id,
            session_type=session_type,
            name=name,
            state=SessionState.ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
            working_dir=working_dir or str(Path.home()),
            tags=tags or []
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions
                (session_id, session_type, name, state, created_at, updated_at,
                 working_dir, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, session_type.value, name, SessionState.ACTIVE.value,
                session.created_at, session.updated_at, session.working_dir,
                json.dumps(tags or [])
            ))

        self._active_sessions[session_id] = session
        return session

    def log_message(
        self,
        session_id: str,
        direction: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Optional[int]:
        """Log a message (input or output) to a session"""
        timestamp = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO messages (session_id, timestamp, direction, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, timestamp, direction, content, json.dumps(metadata or {})))

            msg_id = cursor.lastrowid

            # Update FTS index
            conn.execute("""
                INSERT INTO messages_fts (rowid, content, session_id)
                VALUES (?, ?, ?)
            """, (msg_id, content, session_id))

            # Update session
            conn.execute("""
                UPDATE sessions
                SET message_count = message_count + 1, updated_at = ?
                WHERE session_id = ?
            """, (timestamp, session_id))

            return msg_id

    def log_input(self, session_id: str, content: str) -> Optional[int]:
        """Log user input"""
        return self.log_message(session_id, "input", content)

    def log_output(self, session_id: str, content: str) -> Optional[int]:
        """Log terminal output"""
        return self.log_message(session_id, "output", content)

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if row:
                return TerminalSession(
                    session_id=row["session_id"],
                    session_type=SessionType(row["session_type"]),
                    name=row["name"],
                    state=SessionState(row["state"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    pid=row["pid"],
                    working_dir=row["working_dir"],
                    message_count=row["message_count"],
                    tags=json.loads(row["tags"] or "[]")
                )
        return None

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 1000,
        offset: int = 0,
        include_redacted: bool = False
    ) -> List[dict]:
        """Get messages for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM messages
                WHERE session_id = ?
            """
            if not include_redacted:
                query += " AND is_redacted = 0"
            query += " ORDER BY timestamp LIMIT ? OFFSET ?"

            rows = conn.execute(query, (session_id, limit, offset)).fetchall()

            messages = []
            for row in rows:
                msg = dict(row)
                if msg["is_redacted"] and msg["redacted_content"]:
                    msg["content"] = msg["redacted_content"]
                messages.append(msg)

            return messages

    def get_sessions_by_type(self, session_type: SessionType) -> List[TerminalSession]:
        """Get all sessions of a type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE session_type = ? ORDER BY updated_at DESC",
                (session_type.value,)
            ).fetchall()

            return [TerminalSession(
                session_id=r["session_id"],
                session_type=SessionType(r["session_type"]),
                name=r["name"],
                state=SessionState(r["state"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                pid=r["pid"],
                working_dir=r["working_dir"],
                message_count=r["message_count"],
                tags=json.loads(r["tags"] or "[]")
            ) for r in rows]

    def get_active_sessions(self) -> List[TerminalSession]:
        """Get all active sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE state = ? ORDER BY updated_at DESC",
                (SessionState.ACTIVE.value,)
            ).fetchall()

            return [TerminalSession(
                session_id=r["session_id"],
                session_type=SessionType(r["session_type"]),
                name=r["name"],
                state=SessionState(r["state"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                pid=r["pid"],
                working_dir=r["working_dir"],
                message_count=r["message_count"],
                tags=json.loads(r["tags"] or "[]")
            ) for r in rows]

    def get_crashed_sessions(self) -> List[TerminalSession]:
        """Get sessions that crashed and need recovery"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE state IN (?, ?) ORDER BY updated_at DESC",
                (SessionState.CRASHED.value, SessionState.ACTIVE.value)
            ).fetchall()

            crashed = []
            for r in rows:
                # Check if PID is still running
                pid = r["pid"]
                if pid:
                    try:
                        os.kill(pid, 0)  # Check if process exists
                    except OSError:
                        # Process not running - mark as crashed
                        crashed.append(TerminalSession(
                            session_id=r["session_id"],
                            session_type=SessionType(r["session_type"]),
                            name=r["name"],
                            state=SessionState.CRASHED,
                            created_at=r["created_at"],
                            updated_at=r["updated_at"],
                            pid=pid,
                            working_dir=r["working_dir"],
                            message_count=r["message_count"],
                            tags=json.loads(r["tags"] or "[]")
                        ))
            return crashed

    def update_session_state(self, session_id: str, state: SessionState):
        """Update session state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET state = ?, updated_at = ? WHERE session_id = ?",
                (state.value, time.time(), session_id)
            )

    def update_session_pid(self, session_id: str, pid: int):
        """Update session PID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET pid = ?, updated_at = ? WHERE session_id = ?",
                (pid, time.time(), session_id)
            )

    def suspend_session(self, session_id: str):
        """Suspend a session (can be restored later)"""
        self.update_session_state(session_id, SessionState.SUSPENDED)
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

    def restore_session(self, session_id: str) -> Optional[TerminalSession]:
        """Restore a suspended or crashed session"""
        session = self.get_session(session_id)
        if session:
            self.update_session_state(session_id, SessionState.RESTORED)
            session.state = SessionState.RESTORED
            self._active_sessions[session_id] = session
            return session
        return None

    def archive_session(self, session_id: str):
        """Archive a session (keep in history but mark closed)"""
        self.update_session_state(session_id, SessionState.ARCHIVED)
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

    # ═══════════════════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════════════════

    def search(
        self,
        query: str,
        session_types: Optional[List[SessionType]] = None,
        limit: int = 100
    ) -> List[dict]:
        """Full-text search across all sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Use FTS for search
            sql = """
                SELECT m.*, s.name as session_name, s.session_type
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.rowid
                JOIN sessions s ON m.session_id = s.session_id
                WHERE messages_fts MATCH ?
                AND m.is_redacted = 0
            """
            params = [query]

            if session_types:
                placeholders = ",".join("?" * len(session_types))
                sql += f" AND s.session_type IN ({placeholders})"
                params.extend([st.value for st in session_types])

            sql += " ORDER BY m.timestamp DESC LIMIT ?"
            params.append(limit)

            results = conn.execute(sql, params).fetchall()
            return [dict(r) for r in results]

    def search_in_session(self, session_id: str, query: str) -> List[dict]:
        """Search within a specific session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            results = conn.execute("""
                SELECT m.*
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.rowid
                WHERE messages_fts MATCH ? AND m.session_id = ?
                AND m.is_redacted = 0
                ORDER BY m.timestamp
            """, (query, session_id)).fetchall()

            return [dict(r) for r in results]

    # ═══════════════════════════════════════════════════════════════════════
    # REDACTION
    # ═══════════════════════════════════════════════════════════════════════

    def redact_message(self, message_id: int, replacement: str = "[REDACTED]"):
        """Redact a specific message"""
        with sqlite3.connect(self.db_path) as conn:
            # Get original for redacted_content storage
            row = conn.execute(
                "SELECT content FROM messages WHERE id = ?",
                (message_id,)
            ).fetchone()

            if row:
                conn.execute("""
                    UPDATE messages
                    SET is_redacted = 1, redacted_content = ?, content = ?
                    WHERE id = ?
                """, (replacement, replacement, message_id))

                # Update FTS
                conn.execute(
                    "DELETE FROM messages_fts WHERE rowid = ?",
                    (message_id,)
                )

    def redact_pattern(
        self,
        session_id: str,
        pattern: str,
        replacement: str = "[REDACTED]"
    ) -> int:
        """Redact all messages matching a pattern in a session"""
        import re

        messages = self.get_session_messages(session_id, limit=10000)
        count = 0

        for msg in messages:
            if re.search(pattern, msg["content"], re.IGNORECASE):
                self.redact_message(msg["id"], replacement)
                count += 1

        return count

    def redact_session(self, session_id: str):
        """Redact all content in a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE messages
                SET is_redacted = 1, redacted_content = '[SESSION REDACTED]',
                    content = '[SESSION REDACTED]'
                WHERE session_id = ?
            """, (session_id,))

            conn.execute(
                "UPDATE sessions SET state = ? WHERE session_id = ?",
                (SessionState.REDACTED.value, session_id)
            )

    # ═══════════════════════════════════════════════════════════════════════
    # SCRUBBING (Secure Deletion)
    # ═══════════════════════════════════════════════════════════════════════

    def _secure_overwrite(self, data: str) -> str:
        """Overwrite string with random data of same length"""
        import secrets
        return secrets.token_hex(len(data) // 2 + 1)[:len(data)]

    def scrub_message(self, message_id: int) -> bool:
        """
        Securely delete a message.

        Unlike redaction (which keeps a placeholder), scrubbing:
        1. Overwrites content with random data
        2. Deletes from database
        3. Removes from FTS index

        Cannot be recovered.
        """
        with sqlite3.connect(self.db_path) as conn:
            # First overwrite the content (forensic protection)
            row = conn.execute(
                "SELECT content, session_id FROM messages WHERE id = ?",
                (message_id,)
            ).fetchone()

            if not row:
                return False

            # Overwrite with random data before deletion
            random_data = self._secure_overwrite(row[0])
            conn.execute(
                "UPDATE messages SET content = ?, redacted_content = ? WHERE id = ?",
                (random_data, random_data, message_id)
            )

            # Remove from FTS index
            conn.execute("DELETE FROM messages_fts WHERE rowid = ?", (message_id,))

            # Now delete
            conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))

            # Update session message count
            conn.execute("""
                UPDATE sessions
                SET message_count = message_count - 1, updated_at = ?
                WHERE session_id = ?
            """, (time.time(), row[1]))

            return True

    def scrub_pattern(
        self,
        session_id: str,
        pattern: str,
        confirm: bool = False
    ) -> int:
        """
        Scrub (permanently delete) all messages matching a pattern.

        Args:
            session_id: Session to scrub from
            pattern: Regex pattern to match
            confirm: Must be True to actually delete (safety check)

        Returns:
            Number of messages scrubbed
        """
        import re

        messages = self.get_session_messages(session_id, limit=100000, include_redacted=True)
        matching = []

        for msg in messages:
            if re.search(pattern, msg["content"], re.IGNORECASE):
                matching.append(msg["id"])

        if not confirm:
            return len(matching)  # Dry run - return count only

        for msg_id in matching:
            self.scrub_message(msg_id)

        return len(matching)

    def scrub_session(self, session_id: str, confirm: bool = False) -> dict:
        """
        Securely delete an entire session and all its messages.

        This is PERMANENT. All data is overwritten with random bytes
        before deletion for forensic protection.

        Args:
            session_id: Session to scrub
            confirm: Must be True to actually delete (safety check)

        Returns:
            Summary of what was/would be scrubbed
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        messages = self.get_session_messages(
            session_id, limit=100000, include_redacted=True
        )

        summary = {
            "session_id": session_id,
            "name": session.name,
            "message_count": len(messages),
            "action": "scrubbed" if confirm else "would_scrub"
        }

        if not confirm:
            return summary  # Dry run

        with sqlite3.connect(self.db_path) as conn:
            # Overwrite all message content with random data
            for msg in messages:
                random_data = self._secure_overwrite(msg["content"])
                conn.execute(
                    "UPDATE messages SET content = ?, redacted_content = ? WHERE id = ?",
                    (random_data, random_data, msg["id"])
                )

            # Delete all FTS entries for this session
            conn.execute("""
                DELETE FROM messages_fts
                WHERE rowid IN (SELECT id FROM messages WHERE session_id = ?)
            """, (session_id,))

            # Delete all messages
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

            # Overwrite session metadata
            random_name = self._secure_overwrite(session.name)
            conn.execute(
                "UPDATE sessions SET name = ? WHERE session_id = ?",
                (random_name, session_id)
            )

            # Delete session
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        return summary

    def scrub_old_sessions(
        self,
        older_than_days: int = 30,
        session_types: Optional[List[SessionType]] = None,
        confirm: bool = False
    ) -> dict:
        """
        Scrub sessions older than specified days.

        Args:
            older_than_days: Delete sessions older than this
            session_types: Only scrub these types (default: all)
            confirm: Must be True to actually delete

        Returns:
            Summary of scrubbed sessions
        """
        cutoff = time.time() - (older_than_days * 86400)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT session_id, name, message_count, updated_at
                FROM sessions
                WHERE updated_at < ?
            """
            params = [cutoff]

            if session_types:
                placeholders = ",".join("?" * len(session_types))
                sql += f" AND session_type IN ({placeholders})"
                params.extend([st.value for st in session_types])

            # Exclude active sessions
            sql += " AND state != ?"
            params.append(SessionState.ACTIVE.value)

            old_sessions = conn.execute(sql, params).fetchall()

        summary = {
            "older_than_days": older_than_days,
            "sessions_found": len(old_sessions),
            "sessions": [dict(s) for s in old_sessions],
            "action": "scrubbed" if confirm else "would_scrub"
        }

        if confirm:
            for s in old_sessions:
                self.scrub_session(s["session_id"], confirm=True)

        return summary

    def vacuum(self):
        """
        VACUUM the database to reclaim space after scrubbing.

        This physically removes deleted data from the database file.
        Should be run after large scrubbing operations.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")

        return {
            "status": "vacuumed",
            "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
        }

    def secure_wipe_database(self, confirm_phrase: str = "") -> dict:
        """
        NUCLEAR OPTION: Completely wipe all session data.

        This overwrites all data with random bytes, deletes everything,
        and vacuums the database.

        Args:
            confirm_phrase: Must be "WIPE ALL DATA" to proceed

        Returns:
            Summary of what was wiped
        """
        if confirm_phrase != "WIPE ALL DATA":
            return {
                "error": "Safety check failed",
                "message": "To wipe all data, pass confirm_phrase='WIPE ALL DATA'"
            }

        stats_before = self.get_stats()

        with sqlite3.connect(self.db_path) as conn:
            # Get all sessions
            sessions = conn.execute("SELECT session_id FROM sessions").fetchall()

            for (session_id,) in sessions:
                self.scrub_session(session_id, confirm=True)

        # Vacuum to reclaim space
        self.vacuum()

        return {
            "status": "WIPED",
            "sessions_removed": stats_before["total_sessions"],
            "messages_removed": stats_before["total_messages"],
            "db_size_before_mb": stats_before["db_size_mb"],
            "db_size_after_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
        }

    # ═══════════════════════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════════════════════

    def export_session(
        self,
        session_id: str,
        filepath: Path,
        include_redacted: bool = False
    ) -> bool:
        """Export a session to JSON"""
        session = self.get_session(session_id)
        if not session:
            return False

        messages = self.get_session_messages(
            session_id,
            limit=100000,
            include_redacted=include_redacted
        )

        data = {
            "session": {
                "id": session.session_id,
                "type": session.session_type.value,
                "name": session.name,
                "created_at": session.created_at,
                "message_count": session.message_count,
            },
            "messages": messages,
            "exported_at": time.time()
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return True

    # ═══════════════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        """Get overall statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total_sessions = conn.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]

            active_sessions = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE state = ?",
                (SessionState.ACTIVE.value,)
            ).fetchone()[0]

            total_messages = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]

            redacted_messages = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE is_redacted = 1"
            ).fetchone()[0]

            by_type = conn.execute("""
                SELECT session_type, COUNT(*) as count
                FROM sessions GROUP BY session_type
            """).fetchall()

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "redacted_messages": redacted_messages,
                "by_type": {r[0]: r[1] for r in by_type},
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0
            }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    manager = TerminalSessionManager()

    if len(sys.argv) < 2:
        print("SAM Terminal Session Manager")
        print("\nManages multiple terminal sessions with persistence.")
        print("\nUsage:")
        print("  python terminal_sessions.py stats         # Show statistics")
        print("  python terminal_sessions.py list          # List all sessions")
        print("  python terminal_sessions.py active        # List active sessions")
        print("  python terminal_sessions.py crashed       # List crashed sessions")
        print("  python terminal_sessions.py show <id>     # Show session details")
        print("  python terminal_sessions.py search <q>    # Search all sessions")
        print("  python terminal_sessions.py export <id> <file>")
        print("")
        print("Privacy:")
        print("  python terminal_sessions.py redact <id>   # Redact (keep placeholder)")
        print("")
        print("Scrubbing (Secure Deletion):")
        print("  python terminal_sessions.py scrub <id>           # Preview scrub")
        print("  python terminal_sessions.py scrub <id> --confirm # Permanently delete")
        print("  python terminal_sessions.py scrub-old <days>     # Preview old sessions")
        print("  python terminal_sessions.py scrub-old <days> --confirm")
        print("  python terminal_sessions.py vacuum               # Reclaim disk space")
        print("  python terminal_sessions.py wipe 'WIPE ALL DATA' # Nuclear option")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "stats":
        stats = manager.get_stats()
        print("\n📊 Terminal Session Statistics\n")
        print(f"  Total sessions:    {stats['total_sessions']}")
        print(f"  Active sessions:   {stats['active_sessions']}")
        print(f"  Total messages:    {stats['total_messages']}")
        print(f"  Redacted messages: {stats['redacted_messages']}")
        print(f"  Database size:     {stats['db_size_mb']} MB")
        print("\n  By type:")
        for t, count in stats["by_type"].items():
            print(f"    {t}: {count}")
        print()

    elif cmd == "list":
        with sqlite3.connect(manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 20"
            ).fetchall()

        print("\n📋 Recent Sessions\n")
        for s in sessions:
            ts = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")
            state_icon = {
                "active": "🟢", "suspended": "🟡", "crashed": "🔴",
                "archived": "📁", "restored": "🔄", "redacted": "🔒"
            }.get(s["state"], "?")
            print(f"  {state_icon} [{ts}] {s['session_id']} - {s['name']}")
            print(f"     Type: {s['session_type']} | Messages: {s['message_count']}")
            print()

    elif cmd == "active":
        sessions = manager.get_active_sessions()
        print(f"\n🟢 {len(sessions)} Active Sessions\n")
        for s in sessions:
            print(f"  {s.session_id} - {s.name} ({s.message_count} messages)")

    elif cmd == "crashed":
        sessions = manager.get_crashed_sessions()
        print(f"\n🔴 {len(sessions)} Crashed Sessions\n")
        for s in sessions:
            print(f"  {s.session_id} - {s.name}")
            print(f"     PID was: {s.pid} | Can be restored")
            print()

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python terminal_sessions.py search <query>")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        results = manager.search(query)

        print(f"\n🔍 Search results for \"{query}\": {len(results)} matches\n")
        for r in results[:20]:
            ts = datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M:%S")
            preview = r["content"][:60] + "..." if len(r["content"]) > 60 else r["content"]
            print(f"  [{ts}] {r['session_name']}: {preview}")

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: python terminal_sessions.py show <session_id>")
            sys.exit(1)

        session_id = sys.argv[2]
        session = manager.get_session(session_id)

        if not session:
            print(f"Session not found: {session_id}")
            sys.exit(1)

        messages = manager.get_session_messages(session_id, limit=50)

        print(f"\n📝 Session: {session.name}\n")
        print(f"  ID:       {session.session_id}")
        print(f"  Type:     {session.session_type.value}")
        print(f"  State:    {session.state.value}")
        print(f"  Messages: {session.message_count}")
        print()
        print("─" * 60)

        for msg in messages[-20:]:  # Last 20
            direction = "→" if msg["direction"] == "input" else "←"
            content = msg["content"][:100]
            print(f"  {direction} {content}")

        print("─" * 60)

    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: python terminal_sessions.py export <session_id> <file.json>")
            sys.exit(1)

        session_id = sys.argv[2]
        filepath = Path(sys.argv[3])

        if manager.export_session(session_id, filepath):
            print(f"✅ Exported to {filepath}")
        else:
            print(f"❌ Session not found: {session_id}")

    elif cmd == "redact":
        if len(sys.argv) < 3:
            print("Usage: python terminal_sessions.py redact <session_id>")
            sys.exit(1)

        session_id = sys.argv[2]
        manager.redact_session(session_id)
        print(f"🔒 Session {session_id} has been redacted")

    elif cmd == "scrub":
        if len(sys.argv) < 3:
            print("Usage:")
            print("  python terminal_sessions.py scrub <session_id>           # Preview")
            print("  python terminal_sessions.py scrub <session_id> --confirm # Execute")
            print("  python terminal_sessions.py scrub-old <days>             # Scrub old sessions")
            sys.exit(1)

        session_id = sys.argv[2]
        confirm = "--confirm" in sys.argv

        result = manager.scrub_session(session_id, confirm=confirm)

        if "error" in result:
            print(f"Error: {result['error']}")
        elif confirm:
            print(f"🗑️  SCRUBBED: {result['name']}")
            print(f"   Messages permanently deleted: {result['message_count']}")
            print("   Data has been overwritten with random bytes and cannot be recovered.")
        else:
            print(f"⚠️  DRY RUN - Would scrub: {result['name']}")
            print(f"   Messages to delete: {result['message_count']}")
            print("   Add --confirm to actually delete")

    elif cmd == "scrub-old":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        confirm = "--confirm" in sys.argv

        result = manager.scrub_old_sessions(older_than_days=days, confirm=confirm)

        if confirm:
            print(f"🗑️  SCRUBBED {result['sessions_found']} sessions older than {days} days")
        else:
            print(f"⚠️  DRY RUN - Would scrub {result['sessions_found']} sessions older than {days} days:")
            for s in result["sessions"][:10]:
                ts = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d")
                print(f"   • {s['name']} ({s['message_count']} messages, last: {ts})")
            if len(result["sessions"]) > 10:
                print(f"   ... and {len(result['sessions']) - 10} more")
            print("\n   Add --confirm to actually delete")

    elif cmd == "vacuum":
        print("🧹 Vacuuming database...")
        result = manager.vacuum()
        print(f"✅ Done. Database size: {result['db_size_mb']} MB")

    elif cmd == "wipe":
        if len(sys.argv) < 3 or sys.argv[2] != "WIPE ALL DATA":
            print("⚠️  NUCLEAR OPTION: This will permanently delete ALL session data.")
            print("   Usage: python terminal_sessions.py wipe 'WIPE ALL DATA'")
            sys.exit(1)

        result = manager.secure_wipe_database(confirm_phrase="WIPE ALL DATA")
        print("💥 DATABASE WIPED")
        print(f"   Sessions removed: {result['sessions_removed']}")
        print(f"   Messages removed: {result['messages_removed']}")
        print(f"   Size: {result['db_size_before_mb']} MB → {result['db_size_after_mb']} MB")

    else:
        print(f"Unknown command: {cmd}")
