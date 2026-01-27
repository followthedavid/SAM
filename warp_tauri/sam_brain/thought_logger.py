#!/usr/bin/env python3
"""
SAM Thought Logger - Complete Pre-Thought Capture

Logs EVERY token the LLM generates, including:
- The cycling thoughts before the final response
- Discarded ideas (if using a model with rejection sampling)
- The full stream before any editing/truncation
- Token-by-token timing for analysis

This creates a complete audit trail of what the LLM "considered"
even if it didn't include everything in the final output.

Nothing is hidden. Everything is logged.
"""

import sqlite3
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Generator
from dataclasses import dataclass, field
from enum import Enum


# Database path - always in .sam directory
DB_PATH = Path.home() / ".sam" / "thought_logs.db"


class ThoughtPhase(Enum):
    """Phases of LLM thinking"""
    INITIAL = "initial"           # First tokens, understanding the prompt
    REASONING = "reasoning"       # Working through the problem
    ALTERNATIVES = "alternatives" # Considering different approaches
    DRAFTING = "drafting"         # Writing the response
    REVISING = "revising"         # Editing/refining
    FINALIZING = "finalizing"     # Last tokens
    COMPLETE = "complete"         # Done


@dataclass
class ThoughtToken:
    """A single token with metadata"""
    token: str
    token_index: int
    timestamp_ms: float
    phase: ThoughtPhase
    confidence: Optional[float] = None  # If model provides it
    alternatives: Optional[list] = None  # Other tokens considered


@dataclass
class ThoughtSession:
    """A complete thinking session"""
    session_id: str
    prompt: str
    model: str
    start_time: float
    end_time: Optional[float] = None
    tokens: list = field(default_factory=list)
    final_response: str = ""
    was_interrupted: bool = False
    safety_flags: list = field(default_factory=list)


class ThoughtLogger:
    """
    Comprehensive thought logging system.

    Captures and stores EVERY token from LLM generation.
    Provides replay and analysis capabilities.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._active_sessions: dict[str, ThoughtSession] = {}

    def _init_db(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thought_sessions (
                    session_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    model TEXT,
                    start_time REAL,
                    end_time REAL,
                    final_response TEXT,
                    total_tokens INTEGER,
                    was_interrupted BOOLEAN,
                    safety_flags TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thought_tokens (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    token TEXT,
                    token_index INTEGER,
                    timestamp_ms REAL,
                    phase TEXT,
                    confidence REAL,
                    alternatives TEXT,
                    FOREIGN KEY (session_id) REFERENCES thought_sessions(session_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tokens_session ON thought_tokens(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_time ON thought_sessions(start_time)
            """)

    def start_session(self, prompt: str, model: str = "unknown") -> ThoughtSession:
        """Start a new thought logging session"""
        session_id = hashlib.sha256(
            f"{prompt}{time.time()}".encode()
        ).hexdigest()[:16]

        session = ThoughtSession(
            session_id=session_id,
            prompt=prompt,
            model=model,
            start_time=time.time()
        )

        self._active_sessions[session_id] = session

        # Log session start
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO thought_sessions
                (session_id, prompt, model, start_time, total_tokens, was_interrupted)
                VALUES (?, ?, ?, ?, 0, 0)
            """, (session_id, prompt, model, session.start_time))

        return session

    def log_token(
        self,
        session_id: str,
        token: str,
        phase: ThoughtPhase = ThoughtPhase.REASONING,
        confidence: Optional[float] = None,
        alternatives: Optional[list] = None
    ) -> ThoughtToken:
        """Log a single token from the LLM output"""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        token_obj = ThoughtToken(
            token=token,
            token_index=len(session.tokens),
            timestamp_ms=(time.time() - session.start_time) * 1000,
            phase=phase,
            confidence=confidence,
            alternatives=alternatives
        )

        session.tokens.append(token_obj)
        session.final_response += token

        # Log to database immediately (for crash safety)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO thought_tokens
                (session_id, token, token_index, timestamp_ms, phase, confidence, alternatives)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                token,
                token_obj.token_index,
                token_obj.timestamp_ms,
                phase.value,
                confidence,
                json.dumps(alternatives) if alternatives else None
            ))

        return token_obj

    def log_stream(
        self,
        session_id: str,
        token_stream: Generator,
        phase_detector: Optional[callable] = None
    ) -> Generator[ThoughtToken, None, None]:
        """
        Log a stream of tokens from an LLM.
        Yields each token after logging it.
        """
        for token in token_stream:
            # Detect phase if detector provided
            phase = ThoughtPhase.REASONING
            if phase_detector:
                phase = phase_detector(token)

            token_obj = self.log_token(session_id, token, phase)
            if token_obj:
                yield token_obj

    def complete_session(
        self,
        session_id: str,
        was_interrupted: bool = False,
        safety_flags: list = None
    ) -> Optional[ThoughtSession]:
        """Complete a thought session"""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        session.end_time = time.time()
        session.was_interrupted = was_interrupted
        session.safety_flags = safety_flags or []

        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE thought_sessions
                SET end_time = ?, final_response = ?, total_tokens = ?,
                    was_interrupted = ?, safety_flags = ?
                WHERE session_id = ?
            """, (
                session.end_time,
                session.final_response,
                len(session.tokens),
                was_interrupted,
                json.dumps(safety_flags) if safety_flags else None,
                session_id
            ))

        # Remove from active sessions
        del self._active_sessions[session_id]

        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a complete session with all tokens"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get session
            session = conn.execute("""
                SELECT * FROM thought_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()

            if not session:
                return None

            # Get all tokens
            tokens = conn.execute("""
                SELECT * FROM thought_tokens
                WHERE session_id = ?
                ORDER BY token_index
            """, (session_id,)).fetchall()

            return {
                "session": dict(session),
                "tokens": [dict(t) for t in tokens]
            }

    def get_recent_sessions(self, limit: int = 50) -> list:
        """Get recent thought sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute("""
                SELECT * FROM thought_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(s) for s in sessions]

    def replay_session(self, session_id: str, speed: float = 1.0) -> Generator:
        """
        Replay a session's tokens with original timing.
        Useful for reviewing what the LLM "thought".
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return

        tokens = session_data["tokens"]
        if not tokens:
            return

        last_ts = 0
        for token in tokens:
            # Wait based on original timing
            delay = (token["timestamp_ms"] - last_ts) / 1000 / speed
            if delay > 0:
                time.sleep(delay)
            last_ts = token["timestamp_ms"]

            yield token

    def get_session_timeline(self, session_id: str) -> list:
        """
        Get a timeline of the thinking process.
        Groups tokens into phases for easier analysis.
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return []

        phases = {}
        for token in session_data["tokens"]:
            phase = token["phase"]
            if phase not in phases:
                phases[phase] = {
                    "phase": phase,
                    "tokens": [],
                    "text": "",
                    "start_ms": token["timestamp_ms"],
                    "end_ms": token["timestamp_ms"]
                }
            phases[phase]["tokens"].append(token)
            phases[phase]["text"] += token["token"]
            phases[phase]["end_ms"] = token["timestamp_ms"]

        return sorted(phases.values(), key=lambda p: p["start_ms"])

    def search_thoughts(
        self,
        query: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> list:
        """Search through logged thoughts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT ts.session_id, ts.prompt, ts.start_time,
                       GROUP_CONCAT(tt.token, '') as thought_text
                FROM thought_sessions ts
                JOIN thought_tokens tt ON ts.session_id = tt.session_id
            """
            params = []

            if since:
                sql += " WHERE ts.start_time > ?"
                params.append(since.timestamp())

            sql += " GROUP BY ts.session_id"
            sql += " HAVING thought_text LIKE ?"
            params.append(f"%{query}%")
            sql += " ORDER BY ts.start_time DESC"
            sql += " LIMIT ?"
            params.append(limit)

            results = conn.execute(sql, params).fetchall()
            return [dict(r) for r in results]

    def export_session(self, session_id: str, filepath: Path) -> bool:
        """Export a session to JSON for review"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)

        return True

    def get_stats(self) -> dict:
        """Get logging statistics"""
        with sqlite3.connect(self.db_path) as conn:
            session_count = conn.execute(
                "SELECT COUNT(*) FROM thought_sessions"
            ).fetchone()[0]

            token_count = conn.execute(
                "SELECT COUNT(*) FROM thought_tokens"
            ).fetchone()[0]

            flagged_count = conn.execute(
                "SELECT COUNT(*) FROM thought_sessions WHERE safety_flags IS NOT NULL AND safety_flags != '[]'"
            ).fetchone()[0]

            # Recent activity
            recent = conn.execute("""
                SELECT COUNT(*) FROM thought_sessions
                WHERE start_time > ?
            """, (time.time() - 86400,)).fetchone()[0]  # Last 24h

            return {
                "total_sessions": session_count,
                "total_tokens": token_count,
                "flagged_sessions": flagged_count,
                "sessions_last_24h": recent,
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0
            }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logger = ThoughtLogger()

    if len(sys.argv) < 2:
        print("SAM Thought Logger - Complete Pre-Thought Capture")
        print("\nUsage:")
        print("  python thought_logger.py stats            # Show logging statistics")
        print("  python thought_logger.py recent [n]       # Show recent sessions")
        print("  python thought_logger.py show <session_id> # Show session details")
        print("  python thought_logger.py replay <session_id> # Replay thinking")
        print("  python thought_logger.py search <query>   # Search through thoughts")
        print("  python thought_logger.py export <session_id> <file>")
        print("\nLogs are stored at:", DB_PATH)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "stats":
        stats = logger.get_stats()
        print("\n📊 Thought Logger Statistics\n")
        print(f"  Total sessions:     {stats['total_sessions']}")
        print(f"  Total tokens:       {stats['total_tokens']}")
        print(f"  Flagged sessions:   {stats['flagged_sessions']}")
        print(f"  Sessions (24h):     {stats['sessions_last_24h']}")
        print(f"  Database size:      {stats['db_size_mb']} MB")
        print()

    elif cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        sessions = logger.get_recent_sessions(limit)

        print(f"\n📋 Recent {len(sessions)} Sessions\n")
        for s in sessions:
            ts = datetime.fromtimestamp(s["start_time"]).strftime("%Y-%m-%d %H:%M")
            prompt_preview = s["prompt"][:40] + "..." if len(s["prompt"]) > 40 else s["prompt"]
            flags = "⚠️" if s["safety_flags"] else ""
            interrupted = "🛑" if s["was_interrupted"] else ""

            print(f"  {flags}{interrupted} [{ts}] {s['session_id']}")
            print(f"     Tokens: {s['total_tokens']} | Prompt: \"{prompt_preview}\"")
            print()

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: python thought_logger.py show <session_id>")
            sys.exit(1)

        session_id = sys.argv[2]
        data = logger.get_session(session_id)

        if not data:
            print(f"Session not found: {session_id}")
            sys.exit(1)

        session = data["session"]
        tokens = data["tokens"]

        print(f"\n📝 Session: {session_id}\n")
        print(f"  Model:   {session['model']}")
        print(f"  Prompt:  \"{session['prompt'][:100]}...\"")
        print(f"  Tokens:  {len(tokens)}")
        print(f"  Flags:   {session['safety_flags']}")
        print()

        print("═" * 60)
        print("COMPLETE THOUGHT STREAM:")
        print("═" * 60)

        current_phase = None
        for t in tokens:
            if t["phase"] != current_phase:
                current_phase = t["phase"]
                print(f"\n[{current_phase}]")

            sys.stdout.write(t["token"])

        print("\n")
        print("═" * 60)

    elif cmd == "replay":
        if len(sys.argv) < 3:
            print("Usage: python thought_logger.py replay <session_id> [speed]")
            sys.exit(1)

        session_id = sys.argv[2]
        speed = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

        print(f"\n🔄 Replaying session {session_id} at {speed}x speed...\n")
        print("─" * 40)

        for token in logger.replay_session(session_id, speed=speed):
            sys.stdout.write(token["token"])
            sys.stdout.flush()

        print("\n")
        print("─" * 40)
        print("\n✅ Replay complete")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python thought_logger.py search <query>")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        results = logger.search_thoughts(query)

        print(f"\n🔍 Search results for \"{query}\":\n")
        for r in results:
            ts = datetime.fromtimestamp(r["start_time"]).strftime("%Y-%m-%d %H:%M")
            print(f"  [{ts}] {r['session_id']}")
            print(f"     Prompt: \"{r['prompt'][:50]}...\"")
            print()

    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: python thought_logger.py export <session_id> <file.json>")
            sys.exit(1)

        session_id = sys.argv[2]
        filepath = Path(sys.argv[3])

        if logger.export_session(session_id, filepath):
            print(f"✅ Exported to {filepath}")
        else:
            print(f"❌ Session not found: {session_id}")

    else:
        print(f"Unknown command: {cmd}")
