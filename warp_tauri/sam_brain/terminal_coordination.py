#!/usr/bin/env python3
"""
Terminal Coordination System

Enables multiple terminal windows (Claude Code, SAM, etc.) to be aware of each other,
share context, and coordinate work without repetition.

Architecture:
- SQLite-based shared state (fast, file-based, no server needed)
- Each terminal registers itself and broadcasts its current task
- Terminals can query what others are doing and wait for dependencies
- SAM has full visibility across all terminal activities

Usage:
    from terminal_coordination import TerminalCoordinator

    # In each terminal
    coord = TerminalCoordinator()
    session = coord.register_terminal("claude-code")

    # Before starting work
    coord.broadcast_task(session.id, "Implementing user auth")

    # Check if someone else is already doing this
    conflicts = coord.check_conflicts("user auth")

    # Wait for another terminal to complete
    coord.wait_for(other_session_id, timeout=60)

    # Get full context (what SAM sees)
    context = coord.get_global_context()
"""

import sqlite3
import json
import uuid
import time
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from enum import Enum


class TerminalStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


@dataclass
class TerminalSession:
    """Represents a single terminal session."""
    id: str
    terminal_type: str  # "claude-code", "sam", "warp", "custom"
    pid: int
    hostname: str
    started_at: str
    last_heartbeat: str
    status: str
    current_task: Optional[str] = None
    task_context: Optional[str] = None
    working_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Sessions this one is waiting for
    tags: List[str] = field(default_factory=list)


@dataclass
class TaskBroadcast:
    """A task announcement from a terminal."""
    id: str
    session_id: str
    task: str
    description: Optional[str]
    started_at: str
    completed_at: Optional[str]
    status: str
    files_involved: List[str]
    keywords: List[str]  # For conflict detection


@dataclass
class CoordinationMessage:
    """Messages between terminals."""
    id: str
    from_session: str
    to_session: Optional[str]  # None = broadcast to all
    message_type: str  # "info", "request", "response", "alert"
    content: str
    data: Optional[Dict]
    sent_at: str
    acknowledged: bool


class TerminalCoordinator:
    """
    Coordinates multiple terminal sessions.

    All terminals share state via SQLite - no server needed.
    Each terminal is a peer that can see all others.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Shared location accessible by all terminals
            db_dir = Path.home() / ".sam" / "coordination"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "terminals.db")

        self.db_path = db_path
        self._init_db()

        # Heartbeat interval (seconds)
        self.heartbeat_interval = 5

        # Session timeout (seconds) - session considered dead after this
        self.session_timeout = 30

    def _init_db(self):
        """Initialize coordination database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Terminal sessions
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                terminal_type TEXT NOT NULL,
                pid INTEGER NOT NULL,
                hostname TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                status TEXT NOT NULL,
                current_task TEXT,
                task_context TEXT,
                working_files TEXT,
                dependencies TEXT,
                tags TEXT
            )
        """)

        # Task broadcasts
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task TEXT NOT NULL,
                description TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                files_involved TEXT,
                keywords TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        # Inter-terminal messages
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                from_session TEXT NOT NULL,
                to_session TEXT,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                data TEXT,
                sent_at TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (from_session) REFERENCES sessions(id)
            )
        """)

        # Shared context (knowledge that persists across sessions)
        c.execute("""
            CREATE TABLE IF NOT EXISTS shared_context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            )
        """)

        # FTS for task search
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                task, description, keywords,
                content='tasks',
                content_rowid='rowid'
            )
        """)

        conn.commit()
        conn.close()

    def register_terminal(
        self,
        terminal_type: str = "custom",
        tags: Optional[List[str]] = None
    ) -> TerminalSession:
        """
        Register this terminal and get a session.

        Call this when your terminal starts up.
        """
        session = TerminalSession(
            id=str(uuid.uuid4())[:8],
            terminal_type=terminal_type,
            pid=os.getpid(),
            hostname=os.uname().nodename,
            started_at=datetime.now().isoformat(),
            last_heartbeat=datetime.now().isoformat(),
            status=TerminalStatus.IDLE.value,
            tags=tags or []
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO sessions
            (id, terminal_type, pid, hostname, started_at, last_heartbeat, status, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.terminal_type,
            session.pid,
            session.hostname,
            session.started_at,
            session.last_heartbeat,
            session.status,
            json.dumps(session.tags)
        ))

        conn.commit()
        conn.close()

        return session

    def heartbeat(self, session_id: str):
        """
        Send a heartbeat to indicate this session is still alive.

        Call this periodically (every 5 seconds recommended).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            UPDATE sessions
            SET last_heartbeat = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), session_id))

        conn.commit()
        conn.close()

    def broadcast_task(
        self,
        session_id: str,
        task: str,
        description: Optional[str] = None,
        files: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> str:
        """
        Announce what this terminal is working on.

        Other terminals can see this and avoid duplicating work.
        Returns the task ID.
        """
        task_id = str(uuid.uuid4())[:8]

        # Auto-extract keywords if not provided
        if keywords is None:
            keywords = self._extract_keywords(task + " " + (description or ""))

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Update session status
        c.execute("""
            UPDATE sessions
            SET status = ?, current_task = ?, task_context = ?, working_files = ?
            WHERE id = ?
        """, (
            TerminalStatus.WORKING.value,
            task,
            description,
            json.dumps(files or []),
            session_id
        ))

        # Create task broadcast
        c.execute("""
            INSERT INTO tasks
            (id, session_id, task, description, started_at, status, files_involved, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            session_id,
            task,
            description,
            datetime.now().isoformat(),
            "active",
            json.dumps(files or []),
            json.dumps(keywords)
        ))

        # Update FTS
        c.execute("""
            INSERT INTO tasks_fts (rowid, task, description, keywords)
            VALUES (last_insert_rowid(), ?, ?, ?)
        """, (task, description or "", " ".join(keywords)))

        conn.commit()
        conn.close()

        return task_id

    def complete_task(self, task_id: str, session_id: str):
        """Mark a task as completed."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            UPDATE tasks
            SET status = ?, completed_at = ?
            WHERE id = ?
        """, ("completed", datetime.now().isoformat(), task_id))

        c.execute("""
            UPDATE sessions
            SET status = ?, current_task = NULL
            WHERE id = ?
        """, (TerminalStatus.IDLE.value, session_id))

        conn.commit()
        conn.close()

    def check_conflicts(
        self,
        task_description: str,
        exclude_session: Optional[str] = None
    ) -> List[Dict]:
        """
        Check if any other terminal is already working on a similar task.

        Returns list of potential conflicts with session info.
        """
        keywords = self._extract_keywords(task_description)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Find active tasks with overlapping keywords
        conflicts = []

        for keyword in keywords:
            c.execute("""
                SELECT t.id, t.session_id, t.task, t.description, t.started_at,
                       s.terminal_type, s.status
                FROM tasks t
                JOIN sessions s ON t.session_id = s.id
                WHERE t.status = 'active'
                  AND t.keywords LIKE ?
                  AND (? IS NULL OR t.session_id != ?)
            """, (f'%"{keyword}"%', exclude_session, exclude_session))

            for row in c.fetchall():
                conflicts.append({
                    "task_id": row[0],
                    "session_id": row[1],
                    "task": row[2],
                    "description": row[3],
                    "started_at": row[4],
                    "terminal_type": row[5],
                    "session_status": row[6],
                    "matching_keyword": keyword
                })

        conn.close()

        # Deduplicate by task_id
        seen = set()
        unique_conflicts = []
        for c in conflicts:
            if c["task_id"] not in seen:
                seen.add(c["task_id"])
                unique_conflicts.append(c)

        return unique_conflicts

    def wait_for(
        self,
        session_id: str,
        target_session_id: str,
        timeout: int = 60
    ) -> bool:
        """
        Wait for another terminal to complete its current task.

        Returns True if target completed, False if timeout.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Mark this session as waiting
        c.execute("""
            UPDATE sessions
            SET status = ?, dependencies = ?
            WHERE id = ?
        """, (
            TerminalStatus.WAITING.value,
            json.dumps([target_session_id]),
            session_id
        ))
        conn.commit()

        start_time = time.time()

        while time.time() - start_time < timeout:
            c.execute("""
                SELECT status, current_task FROM sessions WHERE id = ?
            """, (target_session_id,))
            row = c.fetchone()

            if row is None:
                # Target session doesn't exist
                break

            if row[0] == TerminalStatus.IDLE.value or row[1] is None:
                # Target completed
                c.execute("""
                    UPDATE sessions
                    SET status = ?, dependencies = '[]'
                    WHERE id = ?
                """, (TerminalStatus.IDLE.value, session_id))
                conn.commit()
                conn.close()
                return True

            time.sleep(1)

        # Timeout
        c.execute("""
            UPDATE sessions
            SET status = ?, dependencies = '[]'
            WHERE id = ?
        """, (TerminalStatus.IDLE.value, session_id))
        conn.commit()
        conn.close()
        return False

    def get_active_terminals(self) -> List[TerminalSession]:
        """Get all terminals that are currently active."""
        self._cleanup_stale_sessions()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT id, terminal_type, pid, hostname, started_at, last_heartbeat,
                   status, current_task, task_context, working_files, dependencies, tags
            FROM sessions
            WHERE status != 'disconnected'
        """)

        sessions = []
        for row in c.fetchall():
            sessions.append(TerminalSession(
                id=row[0],
                terminal_type=row[1],
                pid=row[2],
                hostname=row[3],
                started_at=row[4],
                last_heartbeat=row[5],
                status=row[6],
                current_task=row[7],
                task_context=row[8],
                working_files=json.loads(row[9]) if row[9] else [],
                dependencies=json.loads(row[10]) if row[10] else [],
                tags=json.loads(row[11]) if row[11] else []
            ))

        conn.close()
        return sessions

    def get_global_context(self) -> Dict:
        """
        Get full context of all terminal activity.

        This is what SAM sees - a complete picture of what's happening.
        """
        terminals = self.get_active_terminals()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Recent tasks
        c.execute("""
            SELECT t.id, t.task, t.description, t.status, t.started_at, t.completed_at,
                   s.terminal_type
            FROM tasks t
            JOIN sessions s ON t.session_id = s.id
            ORDER BY t.started_at DESC
            LIMIT 20
        """)
        recent_tasks = [
            {
                "id": row[0],
                "task": row[1],
                "description": row[2],
                "status": row[3],
                "started_at": row[4],
                "completed_at": row[5],
                "terminal_type": row[6]
            }
            for row in c.fetchall()
        ]

        # Shared context
        c.execute("SELECT key, value, updated_at FROM shared_context")
        shared = {row[0]: {"value": json.loads(row[1]), "updated": row[2]} for row in c.fetchall()}

        conn.close()

        # Count by status
        status_counts = {}
        for t in terminals:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1

        return {
            "terminals": {
                "active": len(terminals),
                "by_status": status_counts,
                "sessions": [asdict(t) for t in terminals]
            },
            "tasks": {
                "recent": recent_tasks,
                "active": [t for t in recent_tasks if t["status"] == "active"],
                "completed_today": len([
                    t for t in recent_tasks
                    if t["completed_at"] and t["completed_at"][:10] == datetime.now().isoformat()[:10]
                ])
            },
            "shared_context": shared,
            "timestamp": datetime.now().isoformat()
        }

    def send_message(
        self,
        from_session: str,
        content: str,
        to_session: Optional[str] = None,
        message_type: str = "info",
        data: Optional[Dict] = None
    ) -> str:
        """
        Send a message to another terminal (or broadcast to all).

        Returns message ID.
        """
        msg_id = str(uuid.uuid4())[:8]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO messages
            (id, from_session, to_session, message_type, content, data, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            from_session,
            to_session,
            message_type,
            content,
            json.dumps(data) if data else None,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return msg_id

    def get_messages(
        self,
        session_id: str,
        unacknowledged_only: bool = True
    ) -> List[CoordinationMessage]:
        """Get messages for a terminal session."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        query = """
            SELECT id, from_session, to_session, message_type, content, data, sent_at, acknowledged
            FROM messages
            WHERE (to_session = ? OR to_session IS NULL)
        """
        params = [session_id]

        if unacknowledged_only:
            query += " AND acknowledged = 0"

        query += " ORDER BY sent_at DESC LIMIT 50"

        c.execute(query, params)

        messages = []
        for row in c.fetchall():
            messages.append(CoordinationMessage(
                id=row[0],
                from_session=row[1],
                to_session=row[2],
                message_type=row[3],
                content=row[4],
                data=json.loads(row[5]) if row[5] else None,
                sent_at=row[6],
                acknowledged=bool(row[7])
            ))

        conn.close()
        return messages

    def acknowledge_message(self, message_id: str):
        """Mark a message as acknowledged."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE messages SET acknowledged = 1 WHERE id = ?", (message_id,))
        conn.commit()
        conn.close()

    def set_shared_context(self, key: str, value: Any, session_id: str):
        """
        Set a shared context value that all terminals can see.

        Use for things like "current_branch", "active_project", etc.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT OR REPLACE INTO shared_context (key, value, updated_at, updated_by)
            VALUES (?, ?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat(), session_id))

        conn.commit()
        conn.close()

    def get_shared_context(self, key: str) -> Optional[Any]:
        """Get a shared context value."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT value FROM shared_context WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def disconnect(self, session_id: str):
        """Mark a session as disconnected (call on terminal exit)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            UPDATE sessions SET status = ? WHERE id = ?
        """, (TerminalStatus.DISCONNECTED.value, session_id))

        # Complete any active tasks
        c.execute("""
            UPDATE tasks SET status = 'abandoned', completed_at = ?
            WHERE session_id = ? AND status = 'active'
        """, (datetime.now().isoformat(), session_id))

        conn.commit()
        conn.close()

    def _cleanup_stale_sessions(self):
        """Mark sessions with old heartbeats as disconnected."""
        cutoff = (datetime.now() - timedelta(seconds=self.session_timeout)).isoformat()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            UPDATE sessions
            SET status = ?
            WHERE last_heartbeat < ? AND status != ?
        """, (TerminalStatus.DISCONNECTED.value, cutoff, TerminalStatus.DISCONNECTED.value))

        conn.commit()
        conn.close()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for conflict detection."""
        # Simple keyword extraction - remove common words
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just",
            "and", "but", "if", "or", "because", "until", "while", "about",
            "implement", "implementing", "add", "adding", "create", "creating",
            "fix", "fixing", "update", "updating", "work", "working"
        }

        words = text.lower().split()
        keywords = [
            w.strip(".,;:!?\"'()[]{}") for w in words
            if w.lower() not in stopwords and len(w) > 2
        ]

        return list(set(keywords))[:10]  # Max 10 keywords


# CLI interface
if __name__ == "__main__":
    import sys

    coord = TerminalCoordinator()

    if len(sys.argv) < 2:
        print("Terminal Coordination System")
        print("\nUsage:")
        print("  python terminal_coordination.py status        # Show all terminals")
        print("  python terminal_coordination.py context       # Full global context")
        print("  python terminal_coordination.py register      # Register this terminal")
        print("  python terminal_coordination.py broadcast MSG # Broadcast a task")
        print("  python terminal_coordination.py conflicts MSG # Check for conflicts")
        print("  python terminal_coordination.py messages ID   # Get messages for session")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        terminals = coord.get_active_terminals()
        print(f"Active Terminals: {len(terminals)}\n")
        for t in terminals:
            status_icon = {
                "idle": "●",
                "working": "◐",
                "waiting": "○",
                "blocked": "✗",
                "disconnected": "✗"
            }.get(t.status, "?")
            task = t.current_task[:40] if t.current_task else "idle"
            print(f"  {status_icon} [{t.id}] {t.terminal_type}: {task}")

    elif cmd == "context":
        ctx = coord.get_global_context()
        print(json.dumps(ctx, indent=2))

    elif cmd == "register":
        term_type = sys.argv[2] if len(sys.argv) > 2 else "cli"
        session = coord.register_terminal(term_type)
        print(f"Registered session: {session.id}")
        print(f"Type: {session.terminal_type}")
        print(f"PID: {session.pid}")

    elif cmd == "broadcast":
        session_id = sys.argv[2]
        task = " ".join(sys.argv[3:])
        task_id = coord.broadcast_task(session_id, task)
        print(f"Broadcasted task: {task_id}")
        print(f"Task: {task}")

    elif cmd == "conflicts":
        task = " ".join(sys.argv[2:])
        conflicts = coord.check_conflicts(task)
        if conflicts:
            print(f"Found {len(conflicts)} potential conflicts:\n")
            for c in conflicts:
                print(f"  [{c['session_id']}] {c['task']}")
                print(f"    Matching: {c['matching_keyword']}")
        else:
            print("No conflicts found.")

    elif cmd == "messages":
        session_id = sys.argv[2]
        messages = coord.get_messages(session_id)
        print(f"Messages for {session_id}: {len(messages)}\n")
        for m in messages:
            print(f"  [{m.message_type}] from {m.from_session}: {m.content}")

    else:
        print(f"Unknown command: {cmd}")
