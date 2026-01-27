#!/usr/bin/env python3
"""
SAM Approval Queue - Supervised Code Execution System

Provides a data model and persistent storage for command approvals,
enabling David to review and approve/reject SAM's proposed actions
before execution.

This is the safety layer that allows SAM to be autonomous while
maintaining human oversight for potentially destructive operations.

Features:
- SQLite-backed persistent storage
- Thread-safe operations
- Automatic expiration of stale requests
- Full audit trail of executed commands
- Rollback information storage
- JSON serialization for API responses

Storage: ~/.sam/approval_queue.db (small DB on internal drive is OK)
"""

import os
import sys
import json
import uuid
import sqlite3
import threading
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


# =============================================================================
# Enums
# =============================================================================

class CommandType(str, Enum):
    """Types of commands SAM can propose."""
    SHELL = "shell"           # Shell/terminal commands
    FILE_EDIT = "file_edit"   # Editing existing files
    FILE_CREATE = "file_create"  # Creating new files
    FILE_DELETE = "file_delete"  # Deleting files
    GIT = "git"               # Git operations (commit, push, etc.)

    def __str__(self) -> str:
        return self.value


class RiskLevel(str, Enum):
    """Risk classification for proposed actions."""
    SAFE = "safe"            # Read-only, non-destructive (auto-approve candidate)
    MODERATE = "moderate"    # Writes data, reversible (needs review)
    DANGEROUS = "dangerous"  # Destructive, hard to reverse (requires explicit approval)
    BLOCKED = "blocked"      # Never allowed (rm -rf /, etc.)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_command(cls, command: str, command_type: CommandType) -> "RiskLevel":
        """Classify risk level based on command content."""
        command_lower = command.lower()

        # Blocked patterns - never allow
        blocked_patterns = [
            "rm -rf /",
            "rm -rf /*",
            "> /dev/sda",
            "mkfs.",
            ":(){:|:&};:",  # Fork bomb
            "dd if=/dev/zero of=/dev/sda",
            "chmod -R 777 /",
        ]
        for pattern in blocked_patterns:
            if pattern in command_lower:
                return cls.BLOCKED

        # Dangerous patterns
        dangerous_patterns = [
            "rm -rf",
            "rm -r",
            "rmdir",
            "git push --force",
            "git reset --hard",
            "git clean -f",
            "drop table",
            "drop database",
            "truncate",
            "> /dev/",
            "sudo rm",
            "chmod -R",
            "chown -R",
        ]
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return cls.DANGEROUS

        # Command type based classification
        if command_type == CommandType.FILE_DELETE:
            return cls.DANGEROUS

        if command_type in (CommandType.FILE_EDIT, CommandType.FILE_CREATE, CommandType.GIT):
            return cls.MODERATE

        # Shell commands - check for write operations
        write_patterns = [">>", ">", "mv ", "cp ", "touch ", "mkdir ", "git commit", "git add"]
        for pattern in write_patterns:
            if pattern in command_lower:
                return cls.MODERATE

        # Default to safe for read-only operations
        return cls.SAFE


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"      # Awaiting review
    APPROVED = "approved"    # Approved by user
    REJECTED = "rejected"    # Rejected by user
    EXECUTED = "executed"    # Successfully executed
    EXPIRED = "expired"      # Timed out without review
    FAILED = "failed"        # Execution failed

    def __str__(self) -> str:
        return self.value


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ApprovalItem:
    """A single approval request for a proposed action.

    Attributes:
        id: Unique identifier (UUID)
        command: The command/action SAM wants to execute
        command_type: Type of command (SHELL, FILE_EDIT, etc.)
        risk_level: Assessed risk level
        project_id: Optional project context
        reasoning: Why SAM wants to do this
        created_at: When the request was created
        expires_at: Auto-reject after this time
        status: Current status of the request
        executed_at: When the command was executed (if applicable)
        result: Execution output (if executed)
        error: Error message (if failed)
        rollback_info: Information needed to undo the action
        rejection_reason: Why it was rejected (if applicable)
        approved_by: Who approved it (default: "david")
    """
    id: str
    command: str
    command_type: CommandType
    risk_level: RiskLevel
    reasoning: str
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    project_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    rollback_info: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "command": self.command,
            "command_type": str(self.command_type),
            "risk_level": str(self.risk_level),
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": str(self.status),
            "project_id": self.project_id,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "result": self.result,
            "error": self.error,
            "rollback_info": self.rollback_info,
            "rejection_reason": self.rejection_reason,
            "approved_by": self.approved_by,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalItem":
        """Create from dictionary."""
        # Parse enums
        command_type = CommandType(data.get("command_type", "shell"))
        risk_level = RiskLevel(data.get("risk_level", "moderate"))
        status = ApprovalStatus(data.get("status", "pending"))

        # Parse datetimes
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        expires_at = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else datetime.now() + timedelta(hours=24)
        executed_at = datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            command=data.get("command", ""),
            command_type=command_type,
            risk_level=risk_level,
            reasoning=data.get("reasoning", ""),
            created_at=created_at,
            expires_at=expires_at,
            status=status,
            project_id=data.get("project_id"),
            executed_at=executed_at,
            result=data.get("result"),
            error=data.get("error"),
            rollback_info=data.get("rollback_info"),
            rejection_reason=data.get("rejection_reason"),
            approved_by=data.get("approved_by"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ApprovalItem":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @property
    def is_expired(self) -> bool:
        """Check if this request has expired."""
        return datetime.now() > self.expires_at

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining before expiration."""
        return max(timedelta(0), self.expires_at - datetime.now())

    @property
    def age(self) -> timedelta:
        """Get age of this request."""
        return datetime.now() - self.created_at


# =============================================================================
# Approval Queue (SQLite-backed)
# =============================================================================

class ApprovalQueue:
    """Thread-safe SQLite-backed approval queue.

    Storage location: ~/.sam/approval_queue.db

    Features:
    - Persistent storage across restarts
    - Thread-safe operations
    - Automatic expiration of old requests
    - Full history tracking
    - JSON API support

    Usage:
        queue = ApprovalQueue()

        # Add a new request
        item_id = queue.add(
            command="rm -rf /tmp/test",
            command_type=CommandType.SHELL,
            reasoning="Cleaning up temporary test directory",
            project_id="sam_brain"
        )

        # List pending items
        pending = queue.list_pending()

        # Approve/reject
        queue.approve(item_id)
        queue.reject(item_id, reason="Too risky")

        # Mark execution result
        queue.mark_executed(item_id, result="Success")
        queue.mark_failed(item_id, error="Permission denied")
    """

    # Default timeout: 24 hours
    DEFAULT_TIMEOUT_HOURS = 24

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the approval queue.

        Args:
            db_path: Optional custom database path. Defaults to ~/.sam/approval_queue.db
        """
        self._lock = threading.RLock()

        if db_path is None:
            sam_dir = Path.home() / ".sam"
            sam_dir.mkdir(exist_ok=True)
            db_path = sam_dir / "approval_queue.db"

        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        with self._lock:
            conn = self._get_connection()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS approval_items (
                        id TEXT PRIMARY KEY,
                        command TEXT NOT NULL,
                        command_type TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        reasoning TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        project_id TEXT,
                        executed_at TEXT,
                        result TEXT,
                        error TEXT,
                        rollback_info TEXT,
                        rejection_reason TEXT,
                        approved_by TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_status ON approval_items(status);
                    CREATE INDEX IF NOT EXISTS idx_created_at ON approval_items(created_at);
                    CREATE INDEX IF NOT EXISTS idx_project_id ON approval_items(project_id);
                    CREATE INDEX IF NOT EXISTS idx_risk_level ON approval_items(risk_level);
                """)
                conn.commit()
            finally:
                conn.close()

    def _row_to_item(self, row: sqlite3.Row) -> ApprovalItem:
        """Convert a database row to an ApprovalItem."""
        rollback_info = None
        if row["rollback_info"]:
            try:
                rollback_info = json.loads(row["rollback_info"])
            except json.JSONDecodeError:
                rollback_info = None

        return ApprovalItem(
            id=row["id"],
            command=row["command"],
            command_type=CommandType(row["command_type"]),
            risk_level=RiskLevel(row["risk_level"]),
            reasoning=row["reasoning"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            status=ApprovalStatus(row["status"]),
            project_id=row["project_id"],
            executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
            result=row["result"],
            error=row["error"],
            rollback_info=rollback_info,
            rejection_reason=row["rejection_reason"],
            approved_by=row["approved_by"],
        )

    def add(
        self,
        command: str,
        command_type: CommandType,
        reasoning: str,
        project_id: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        timeout_hours: float = None,
        rollback_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a new approval request to the queue.

        Args:
            command: The command/action to be approved
            command_type: Type of command
            reasoning: Why SAM wants to execute this
            project_id: Optional project context
            risk_level: Risk level (auto-detected if not provided)
            timeout_hours: Hours until auto-expiration (default: 24)
            rollback_info: Information needed to undo the action

        Returns:
            The UUID of the created approval item

        Raises:
            ValueError: If the command is blocked
        """
        # Auto-detect risk level if not provided
        if risk_level is None:
            risk_level = RiskLevel.from_command(command, command_type)

        # Block dangerous commands immediately
        if risk_level == RiskLevel.BLOCKED:
            raise ValueError(f"Command blocked: {command[:100]}...")

        # Create the item
        item_id = str(uuid.uuid4())
        now = datetime.now()
        timeout = timeout_hours if timeout_hours is not None else self.DEFAULT_TIMEOUT_HOURS
        expires_at = now + timedelta(hours=timeout)

        rollback_json = json.dumps(rollback_info) if rollback_info else None

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO approval_items
                    (id, command, command_type, risk_level, reasoning, created_at,
                     expires_at, status, project_id, rollback_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        command,
                        str(command_type),
                        str(risk_level),
                        reasoning,
                        now.isoformat(),
                        expires_at.isoformat(),
                        str(ApprovalStatus.PENDING),
                        project_id,
                        rollback_json,
                    )
                )
                conn.commit()
            finally:
                conn.close()

        return item_id

    def get(self, item_id: str) -> Optional[ApprovalItem]:
        """Get an approval item by ID.

        Args:
            item_id: UUID of the item

        Returns:
            ApprovalItem or None if not found
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT * FROM approval_items WHERE id = ?",
                    (item_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_item(row)
                return None
            finally:
                conn.close()

    def list_pending(self, project_id: Optional[str] = None) -> List[ApprovalItem]:
        """List all pending approval requests.

        Args:
            project_id: Optional filter by project

        Returns:
            List of pending ApprovalItems, oldest first
        """
        with self._lock:
            conn = self._get_connection()
            try:
                if project_id:
                    cursor = conn.execute(
                        """
                        SELECT * FROM approval_items
                        WHERE status = ? AND project_id = ?
                        ORDER BY created_at ASC
                        """,
                        (str(ApprovalStatus.PENDING), project_id)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM approval_items
                        WHERE status = ?
                        ORDER BY created_at ASC
                        """,
                        (str(ApprovalStatus.PENDING),)
                    )

                items = [self._row_to_item(row) for row in cursor.fetchall()]

                # Filter out expired items (and mark them as expired)
                result = []
                expired_ids = []
                for item in items:
                    if item.is_expired:
                        expired_ids.append(item.id)
                    else:
                        result.append(item)

                # Mark expired items
                if expired_ids:
                    for exp_id in expired_ids:
                        self._update_status(conn, exp_id, ApprovalStatus.EXPIRED)
                    conn.commit()

                return result
            finally:
                conn.close()

    def _update_status(
        self,
        conn: sqlite3.Connection,
        item_id: str,
        status: ApprovalStatus,
        **kwargs
    ):
        """Internal: Update item status and optional fields."""
        updates = ["status = ?"]
        values = [str(status)]

        for key, value in kwargs.items():
            if value is not None:
                if key == "rollback_info":
                    updates.append(f"{key} = ?")
                    values.append(json.dumps(value))
                else:
                    updates.append(f"{key} = ?")
                    values.append(value if not isinstance(value, datetime) else value.isoformat())

        values.append(item_id)

        conn.execute(
            f"UPDATE approval_items SET {', '.join(updates)} WHERE id = ?",
            values
        )

    def approve(self, item_id: str, approved_by: str = "david") -> bool:
        """Approve a pending item.

        Args:
            item_id: UUID of the item to approve
            approved_by: Who approved it

        Returns:
            True if approved, False if not found or not pending
        """
        with self._lock:
            conn = self._get_connection()
            try:
                item = self.get(item_id)
                if not item or item.status != ApprovalStatus.PENDING:
                    return False

                if item.is_expired:
                    self._update_status(conn, item_id, ApprovalStatus.EXPIRED)
                    conn.commit()
                    return False

                self._update_status(
                    conn, item_id, ApprovalStatus.APPROVED,
                    approved_by=approved_by
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def reject(self, item_id: str, reason: Optional[str] = None) -> bool:
        """Reject a pending item.

        Args:
            item_id: UUID of the item to reject
            reason: Optional rejection reason

        Returns:
            True if rejected, False if not found or not pending
        """
        with self._lock:
            conn = self._get_connection()
            try:
                item = self.get(item_id)
                if not item or item.status != ApprovalStatus.PENDING:
                    return False

                self._update_status(
                    conn, item_id, ApprovalStatus.REJECTED,
                    rejection_reason=reason
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def mark_executed(
        self,
        item_id: str,
        result: str,
        rollback_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark an approved item as successfully executed.

        Args:
            item_id: UUID of the item
            result: Execution output/result
            rollback_info: Updated rollback information (e.g., backup path)

        Returns:
            True if marked, False if not found or not approved
        """
        with self._lock:
            conn = self._get_connection()
            try:
                item = self.get(item_id)
                if not item or item.status != ApprovalStatus.APPROVED:
                    return False

                self._update_status(
                    conn, item_id, ApprovalStatus.EXECUTED,
                    executed_at=datetime.now(),
                    result=result,
                    rollback_info=rollback_info
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def mark_failed(self, item_id: str, error: str) -> bool:
        """Mark an item as failed execution.

        Args:
            item_id: UUID of the item
            error: Error message/details

        Returns:
            True if marked, False if not found or not approved
        """
        with self._lock:
            conn = self._get_connection()
            try:
                item = self.get(item_id)
                if not item or item.status != ApprovalStatus.APPROVED:
                    return False

                self._update_status(
                    conn, item_id, ApprovalStatus.FAILED,
                    executed_at=datetime.now(),
                    error=error
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def expire_old(self) -> int:
        """Mark all expired pending items as expired.

        Returns:
            Number of items expired
        """
        with self._lock:
            conn = self._get_connection()
            try:
                now = datetime.now().isoformat()
                cursor = conn.execute(
                    """
                    UPDATE approval_items
                    SET status = ?
                    WHERE status = ? AND expires_at < ?
                    """,
                    (str(ApprovalStatus.EXPIRED), str(ApprovalStatus.PENDING), now)
                )
                count = cursor.rowcount
                conn.commit()
                return count
            finally:
                conn.close()

    def get_history(
        self,
        limit: int = 50,
        project_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> List[ApprovalItem]:
        """Get recent approval history.

        Args:
            limit: Maximum items to return
            project_id: Filter by project
            status: Filter by status
            risk_level: Filter by risk level

        Returns:
            List of ApprovalItems, newest first
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conditions = []
                params = []

                if project_id:
                    conditions.append("project_id = ?")
                    params.append(project_id)

                if status:
                    conditions.append("status = ?")
                    params.append(str(status))

                if risk_level:
                    conditions.append("risk_level = ?")
                    params.append(str(risk_level))

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                params.append(limit)

                cursor = conn.execute(
                    f"""
                    SELECT * FROM approval_items
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    params
                )

                return [self._row_to_item(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def clear_old(self, days: int = 30) -> int:
        """Remove old completed items from the database.

        Args:
            days: Delete items older than this many days

        Returns:
            Number of items deleted
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = conn.execute(
                    """
                    DELETE FROM approval_items
                    WHERE created_at < ?
                    AND status NOT IN (?, ?)
                    """,
                    (cutoff, str(ApprovalStatus.PENDING), str(ApprovalStatus.APPROVED))
                )
                count = cursor.rowcount
                conn.commit()
                return count
            finally:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            conn = self._get_connection()
            try:
                # Count by status
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM approval_items
                    GROUP BY status
                """)
                by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

                # Count by risk level
                cursor = conn.execute("""
                    SELECT risk_level, COUNT(*) as count
                    FROM approval_items
                    GROUP BY risk_level
                """)
                by_risk = {row["risk_level"]: row["count"] for row in cursor.fetchall()}

                # Count by command type
                cursor = conn.execute("""
                    SELECT command_type, COUNT(*) as count
                    FROM approval_items
                    GROUP BY command_type
                """)
                by_type = {row["command_type"]: row["count"] for row in cursor.fetchall()}

                # Total count
                cursor = conn.execute("SELECT COUNT(*) as total FROM approval_items")
                total = cursor.fetchone()["total"]

                # Pending count
                pending = by_status.get(str(ApprovalStatus.PENDING), 0)

                # Approval rate (approved / (approved + rejected))
                approved = by_status.get(str(ApprovalStatus.APPROVED), 0) + by_status.get(str(ApprovalStatus.EXECUTED), 0)
                rejected = by_status.get(str(ApprovalStatus.REJECTED), 0)
                approval_rate = approved / (approved + rejected) if (approved + rejected) > 0 else 0.0

                return {
                    "total": total,
                    "pending": pending,
                    "by_status": by_status,
                    "by_risk_level": by_risk,
                    "by_command_type": by_type,
                    "approval_rate": round(approval_rate, 3),
                    "db_path": str(self.db_path),
                }
            finally:
                conn.close()

    def to_json_list(self, items: List[ApprovalItem]) -> str:
        """Serialize a list of items to JSON.

        Args:
            items: List of ApprovalItems

        Returns:
            JSON string
        """
        return json.dumps([item.to_dict() for item in items], indent=2)


# =============================================================================
# Singleton instance
# =============================================================================

_approval_queue: Optional[ApprovalQueue] = None
_queue_lock = threading.Lock()


def get_approval_queue() -> ApprovalQueue:
    """Get or create the singleton approval queue instance.

    Returns:
        The global ApprovalQueue instance
    """
    global _approval_queue
    with _queue_lock:
        if _approval_queue is None:
            _approval_queue = ApprovalQueue()
        return _approval_queue


# =============================================================================
# API Functions (for sam_api.py integration)
# =============================================================================

def api_approval_queue(project_id: Optional[str] = None) -> Dict[str, Any]:
    """API: Get pending approval items.

    Args:
        project_id: Optional filter by project

    Returns:
        dict with success status and pending items
    """
    try:
        queue = get_approval_queue()
        pending = queue.list_pending(project_id)
        stats = queue.get_stats()

        return {
            "success": True,
            "pending_count": len(pending),
            "items": [item.to_dict() for item in pending],
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_approval_approve(item_id: str, approved_by: str = "david") -> Dict[str, Any]:
    """API: Approve a pending item.

    Args:
        item_id: UUID of the item to approve
        approved_by: Who approved it

    Returns:
        dict with success status
    """
    try:
        queue = get_approval_queue()
        item = queue.get(item_id)

        if not item:
            return {"success": False, "error": f"Item not found: {item_id}"}

        if item.status != ApprovalStatus.PENDING:
            return {"success": False, "error": f"Item is not pending (status: {item.status})"}

        if item.is_expired:
            queue.expire_old()
            return {"success": False, "error": "Item has expired"}

        if queue.approve(item_id, approved_by):
            return {
                "success": True,
                "item_id": item_id,
                "command": item.command,
                "status": str(ApprovalStatus.APPROVED),
                "approved_by": approved_by,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": "Failed to approve item"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_approval_reject(
    item_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """API: Reject a pending item.

    Args:
        item_id: UUID of the item to reject
        reason: Optional rejection reason

    Returns:
        dict with success status
    """
    try:
        queue = get_approval_queue()
        item = queue.get(item_id)

        if not item:
            return {"success": False, "error": f"Item not found: {item_id}"}

        if item.status != ApprovalStatus.PENDING:
            return {"success": False, "error": f"Item is not pending (status: {item.status})"}

        if queue.reject(item_id, reason):
            return {
                "success": True,
                "item_id": item_id,
                "command": item.command,
                "status": str(ApprovalStatus.REJECTED),
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": "Failed to reject item"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_approval_history(
    limit: int = 50,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """API: Get approval history.

    Args:
        limit: Maximum items to return
        project_id: Optional filter by project
        status: Optional filter by status

    Returns:
        dict with success status and history items
    """
    try:
        queue = get_approval_queue()

        status_enum = ApprovalStatus(status) if status else None
        history = queue.get_history(limit, project_id, status_enum)

        return {
            "success": True,
            "count": len(history),
            "items": [item.to_dict() for item in history],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_approval_get(item_id: str) -> Dict[str, Any]:
    """API: Get a specific approval item.

    Args:
        item_id: UUID of the item

    Returns:
        dict with success status and item details
    """
    try:
        queue = get_approval_queue()
        item = queue.get(item_id)

        if not item:
            return {"success": False, "error": f"Item not found: {item_id}"}

        return {
            "success": True,
            "item": item.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_approval_stats() -> Dict[str, Any]:
    """API: Get approval queue statistics.

    Returns:
        dict with queue statistics
    """
    try:
        queue = get_approval_queue()
        stats = queue.get_stats()

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# CLI (for testing)
# =============================================================================

def main():
    """CLI for testing the approval queue."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Approval Queue CLI")
    parser.add_argument("command", choices=[
        "list", "add", "approve", "reject", "history", "stats", "get", "expire", "clear"
    ])
    parser.add_argument("--id", help="Item ID")
    parser.add_argument("--cmd", help="Command to add")
    parser.add_argument("--type", default="shell", help="Command type")
    parser.add_argument("--reason", help="Reasoning or rejection reason")
    parser.add_argument("--project", help="Project ID")
    parser.add_argument("--limit", type=int, default=50, help="Limit for history")
    parser.add_argument("--days", type=int, default=30, help="Days for clear")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()
    queue = get_approval_queue()

    if args.command == "list":
        result = api_approval_queue(args.project)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            items = result.get("items", [])
            if not items:
                print("No pending approvals")
            else:
                print(f"\n{'='*60}")
                print("  PENDING APPROVALS")
                print(f"{'='*60}\n")
                for item in items:
                    print(f"[{item['id'][:8]}] {item['command_type'].upper()} - {item['risk_level'].upper()}")
                    print(f"    Command: {item['command'][:60]}...")
                    print(f"    Reason: {item['reasoning'][:60]}...")
                    print(f"    Created: {item['created_at']}")
                    print()

    elif args.command == "add":
        if not args.cmd:
            print("Error: --cmd required")
            sys.exit(1)
        cmd_type = CommandType(args.type)
        item_id = queue.add(
            command=args.cmd,
            command_type=cmd_type,
            reasoning=args.reason or "CLI test",
            project_id=args.project
        )
        print(f"Added: {item_id}")

    elif args.command == "approve":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = api_approval_approve(args.id)
        print(json.dumps(result, indent=2) if args.json else f"Result: {result.get('success')}")

    elif args.command == "reject":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = api_approval_reject(args.id, args.reason)
        print(json.dumps(result, indent=2) if args.json else f"Result: {result.get('success')}")

    elif args.command == "history":
        result = api_approval_history(args.limit, args.project)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            items = result.get("items", [])
            for item in items:
                print(f"[{item['id'][:8]}] {item['status']} - {item['command'][:40]}...")

    elif args.command == "stats":
        result = api_approval_stats()
        print(json.dumps(result, indent=2))

    elif args.command == "get":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = api_approval_get(args.id)
        print(json.dumps(result, indent=2))

    elif args.command == "expire":
        count = queue.expire_old()
        print(f"Expired {count} items")

    elif args.command == "clear":
        count = queue.clear_old(args.days)
        print(f"Cleared {count} items older than {args.days} days")


if __name__ == "__main__":
    main()
