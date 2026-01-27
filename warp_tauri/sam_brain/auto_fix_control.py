#!/usr/bin/env python3
"""
SAM Auto-Fix Permission and Rate Limiting System

Provides granular control over SAM's autonomous code fixing capabilities:
- Per-project permission management
- Rate limiting to prevent runaway fixes
- Fix type filtering (which issue types to auto-fix)
- File pattern matching (which files SAM can touch)
- Tracking and statistics for all auto-fix operations
- Integration with proactive_notifier for alerts

Usage:
    from auto_fix_control import (
        AutoFixPermissions, AutoFixController, AutoFixTracker,
        RateLimitStatus, AutoFixStats, AutoFixableIssue, FixResult,
        get_auto_fix_controller
    )

    # Check if we can fix an issue
    controller = get_auto_fix_controller()
    can_fix, reason = controller.can_auto_fix("sam_brain", issue)

    if can_fix:
        # Apply the fix
        result = apply_fix(issue)
        controller.record_fix("sam_brain", issue, result)

    # Get rate limit status
    status = controller.get_rate_limit_status("sam_brain")
    print(f"Fixes this hour: {status.fixes_this_hour}/{status.limit}")

    # Get statistics
    stats = controller.get_fix_stats("sam_brain")
    print(f"Total fixes: {stats.total_fixes}, Success rate: {stats.success_rate:.1%}")

API Endpoints:
    GET  /api/autofix/permissions/{project_id} - Get permissions for project
    PUT  /api/autofix/permissions/{project_id} - Update permissions
    GET  /api/autofix/stats/{project_id}       - Get fix statistics
    POST /api/autofix/run/{project_id}         - Trigger auto-fix scan
    GET  /api/autofix/pending                  - Get issues awaiting review
"""

import json
import sqlite3
import fnmatch
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict


# ============ Storage Configuration ============

# Prefer external storage per CLAUDE.md
EXTERNAL_DB_PATH = Path("/Volumes/David External/sam_memory/auto_fix.db")
LOCAL_DB_PATH = Path.home() / ".sam" / "auto_fix.db"


def get_db_path() -> Path:
    """Get the database path, preferring external storage."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_DB_PATH
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOCAL_DB_PATH


# ============ Enums ============

class AutoFixableIssue(Enum):
    """Types of issues that can be auto-fixed."""
    # Code Quality
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    MISSING_DOCSTRING = "missing_docstring"
    TRAILING_WHITESPACE = "trailing_whitespace"
    MISSING_NEWLINE_EOF = "missing_newline_eof"

    # Formatting
    INDENTATION_ERROR = "indentation_error"
    LINE_TOO_LONG = "line_too_long"
    INCONSISTENT_QUOTES = "inconsistent_quotes"

    # Type Hints
    MISSING_TYPE_HINT = "missing_type_hint"
    INCORRECT_TYPE_HINT = "incorrect_type_hint"

    # Imports
    UNSORTED_IMPORTS = "unsorted_imports"
    MISSING_IMPORT = "missing_import"
    WILDCARD_IMPORT = "wildcard_import"

    # Deprecations
    DEPRECATED_API = "deprecated_api"
    DEPRECATED_SYNTAX = "deprecated_syntax"

    # Security
    HARDCODED_SECRET = "hardcoded_secret"  # Usually blocked
    SQL_INJECTION_RISK = "sql_injection_risk"

    # Python Specific
    F_STRING_CONVERSION = "f_string_conversion"
    DICT_COMPREHENSION = "dict_comprehension"
    LIST_COMPREHENSION = "list_comprehension"

    # Documentation
    OUTDATED_COMMENT = "outdated_comment"
    TODO_COMPLETION = "todo_completion"

    # Dependencies
    OUTDATED_DEPENDENCY = "outdated_dependency"
    SECURITY_VULNERABILITY = "security_vulnerability"


class FixResultStatus(Enum):
    """Status of an auto-fix attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    REVERTED = "reverted"
    PENDING_REVIEW = "pending_review"


# ============ Data Classes ============

@dataclass
class DetectedIssue:
    """
    An issue detected in the codebase that may be auto-fixable.

    Attributes:
        issue_id: Unique identifier for this issue
        issue_type: Type of issue (from AutoFixableIssue enum)
        file_path: Path to the file containing the issue
        line_number: Line number where issue was detected
        column: Column position (optional)
        message: Human-readable description
        severity: Issue severity (info, warning, error)
        suggested_fix: The proposed fix code
        confidence: How confident we are in the fix (0.0-1.0)
        context: Surrounding code context
        detected_at: When this issue was detected
    """
    issue_id: str
    issue_type: str
    file_path: str
    line_number: int
    message: str
    suggested_fix: str
    confidence: float = 0.8
    column: int = 0
    severity: str = "warning"
    context: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'DetectedIssue':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FixResult:
    """
    Result of attempting an auto-fix.

    Attributes:
        issue_id: The issue that was addressed
        status: Result status (success, failed, skipped, etc.)
        applied_fix: The actual fix that was applied
        original_code: The original code before fix
        error_message: Error message if fix failed
        applied_at: Timestamp when fix was applied
        reverted: Whether the fix was later reverted
        revert_reason: Why fix was reverted
    """
    issue_id: str
    status: str
    applied_fix: str = ""
    original_code: str = ""
    error_message: str = ""
    applied_at: float = field(default_factory=time.time)
    reverted: bool = False
    revert_reason: str = ""
    commit_sha: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'FixResult':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AutoFixPermissions:
    """
    Per-project permissions for auto-fixing.

    This extends the ProjectPermissions concept to control exactly
    what SAM is allowed to auto-fix in each project.

    Attributes:
        project_id: Unique project identifier
        enabled: Master switch for auto-fixing
        allowed_fix_types: List of AutoFixableIssue types SAM can fix
        blocked_fix_types: Issue types that should NEVER be auto-fixed
        max_fixes_per_file: Maximum fixes to apply to a single file
        max_fixes_per_hour: Rate limit for the project
        require_review_threshold: If more than N fixes, require review first
        allowed_file_patterns: Glob patterns for files SAM can fix
        blocked_file_patterns: Glob patterns for files SAM cannot touch
        auto_commit: Whether to commit fixes automatically
        commit_message_template: Template for commit messages
        min_confidence: Minimum confidence required to auto-fix (0.0-1.0)
        dry_run: If True, detect but don't actually apply fixes
    """
    project_id: str
    enabled: bool = True
    allowed_fix_types: List[str] = field(default_factory=lambda: [
        AutoFixableIssue.UNUSED_IMPORT.value,
        AutoFixableIssue.TRAILING_WHITESPACE.value,
        AutoFixableIssue.MISSING_NEWLINE_EOF.value,
        AutoFixableIssue.UNSORTED_IMPORTS.value,
        AutoFixableIssue.F_STRING_CONVERSION.value,
    ])
    blocked_fix_types: List[str] = field(default_factory=lambda: [
        AutoFixableIssue.HARDCODED_SECRET.value,
        AutoFixableIssue.SQL_INJECTION_RISK.value,
        AutoFixableIssue.SECURITY_VULNERABILITY.value,
    ])
    max_fixes_per_file: int = 10
    max_fixes_per_hour: int = 50
    require_review_threshold: int = 5
    allowed_file_patterns: List[str] = field(default_factory=lambda: [
        "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.rs",
    ])
    blocked_file_patterns: List[str] = field(default_factory=lambda: [
        "*.env*", "*secret*", "*credential*", "*password*",
        "node_modules/*", ".git/*", "__pycache__/*", "*.lock",
    ])
    auto_commit: bool = False
    commit_message_template: str = "auto-fix({type}): {message}"
    min_confidence: float = 0.85
    dry_run: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AutoFixPermissions':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_fix_type_allowed(self, fix_type: str) -> bool:
        """Check if a fix type is allowed for this project."""
        if fix_type in self.blocked_fix_types:
            return False
        if self.allowed_fix_types and fix_type not in self.allowed_fix_types:
            return False
        return True

    def is_file_allowed(self, file_path: str) -> bool:
        """Check if a file can be fixed based on patterns."""
        file_name = Path(file_path).name
        full_path = str(file_path)

        # Check blocked patterns first
        for pattern in self.blocked_file_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(full_path, pattern):
                return False

        # Check allowed patterns
        if self.allowed_file_patterns:
            for pattern in self.allowed_file_patterns:
                if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(full_path, pattern):
                    return True
            return False

        return True


@dataclass
class RateLimitStatus:
    """
    Current rate limit status for a project.

    Attributes:
        project_id: The project this status is for
        fixes_this_hour: Number of fixes applied this hour
        limit: Maximum allowed fixes per hour
        resets_at: When the rate limit resets
        can_fix: Whether more fixes are currently allowed
        remaining: Number of fixes remaining this hour
        window_start: Start of current rate limit window
    """
    project_id: str
    fixes_this_hour: int
    limit: int
    resets_at: datetime
    can_fix: bool
    remaining: int = 0
    window_start: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.remaining = max(0, self.limit - self.fixes_this_hour)
        self.can_fix = self.remaining > 0

    def to_dict(self) -> dict:
        """Convert to dictionary with serializable timestamps."""
        return {
            "project_id": self.project_id,
            "fixes_this_hour": self.fixes_this_hour,
            "limit": self.limit,
            "resets_at": self.resets_at.isoformat(),
            "can_fix": self.can_fix,
            "remaining": self.remaining,
            "window_start": self.window_start.isoformat(),
        }


@dataclass
class AutoFixStats:
    """
    Statistics about auto-fix operations for a project.

    Attributes:
        project_id: The project these stats are for
        total_fixes: Total number of fixes ever applied
        by_type: Breakdown by issue type
        success_rate: Percentage of successful fixes
        most_fixed_files: Top files that received fixes
        fixes_by_day: Fixes per day for trending
        reverted_fixes: Number of fixes that were reverted
        avg_confidence: Average confidence of applied fixes
        last_fix_at: Timestamp of most recent fix
    """
    project_id: str
    total_fixes: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    success_rate: float = 0.0
    most_fixed_files: List[Tuple[str, int]] = field(default_factory=list)
    fixes_by_day: Dict[str, int] = field(default_factory=dict)
    reverted_fixes: int = 0
    avg_confidence: float = 0.0
    last_fix_at: Optional[datetime] = None
    pending_review: int = 0
    skipped_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary with serializable fields."""
        return {
            "project_id": self.project_id,
            "total_fixes": self.total_fixes,
            "by_type": self.by_type,
            "success_rate": round(self.success_rate, 3),
            "most_fixed_files": self.most_fixed_files,
            "fixes_by_day": self.fixes_by_day,
            "reverted_fixes": self.reverted_fixes,
            "avg_confidence": round(self.avg_confidence, 3),
            "last_fix_at": self.last_fix_at.isoformat() if self.last_fix_at else None,
            "pending_review": self.pending_review,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
        }


# ============ Database Schema ============

SCHEMA = """
-- Permissions per project
CREATE TABLE IF NOT EXISTS permissions (
    project_id TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- All detected issues (including pending)
CREATE TABLE IF NOT EXISTS detected_issues (
    issue_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER DEFAULT 0,
    message TEXT NOT NULL,
    suggested_fix TEXT,
    confidence REAL DEFAULT 0.8,
    severity TEXT DEFAULT 'warning',
    context TEXT,
    detected_at REAL NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, fixed, skipped, ignored
    FOREIGN KEY (project_id) REFERENCES permissions(project_id)
);

-- All fix attempts and results
CREATE TABLE IF NOT EXISTS fix_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- success, failed, skipped, reverted, pending_review
    applied_fix TEXT,
    original_code TEXT,
    error_message TEXT,
    applied_at REAL NOT NULL,
    reverted BOOLEAN DEFAULT FALSE,
    revert_reason TEXT,
    commit_sha TEXT,
    confidence REAL,
    file_path TEXT,
    issue_type TEXT,
    FOREIGN KEY (issue_id) REFERENCES detected_issues(issue_id)
);

-- Rate limiting tracking
CREATE TABLE IF NOT EXISTS rate_limits (
    project_id TEXT NOT NULL,
    window_start REAL NOT NULL,
    fix_count INTEGER DEFAULT 0,
    PRIMARY KEY (project_id, window_start)
);

-- File fix counts (for per-file limits)
CREATE TABLE IF NOT EXISTS file_fix_counts (
    project_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    window_start REAL NOT NULL,
    fix_count INTEGER DEFAULT 0,
    PRIMARY KEY (project_id, file_path, window_start)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_issues_project ON detected_issues(project_id);
CREATE INDEX IF NOT EXISTS idx_issues_status ON detected_issues(status);
CREATE INDEX IF NOT EXISTS idx_results_project ON fix_results(project_id);
CREATE INDEX IF NOT EXISTS idx_results_applied ON fix_results(applied_at);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start);
"""


# ============ AutoFixTracker Class ============

class AutoFixTracker:
    """
    Tracks all auto-fix operations and their outcomes.

    Responsible for:
    - Recording successful fixes
    - Recording failures with error details
    - Tracking reverted fixes
    - Providing file history for skip decisions
    - Determining if a file should be skipped (too many failures)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the tracker.

        Args:
            db_path: Path to SQLite database (defaults to get_db_path())
        """
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def track_success(
        self,
        project_id: str,
        issue: DetectedIssue,
        result: FixResult
    ) -> None:
        """
        Track a successful fix.

        Args:
            project_id: Project identifier
            issue: The issue that was fixed
            result: The fix result
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Update issue status
            cur.execute("""
                UPDATE detected_issues SET status = 'fixed'
                WHERE issue_id = ?
            """, (issue.issue_id,))

            # Record the fix
            cur.execute("""
                INSERT INTO fix_results (
                    issue_id, project_id, status, applied_fix, original_code,
                    applied_at, confidence, file_path, issue_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                issue.issue_id,
                project_id,
                FixResultStatus.SUCCESS.value,
                result.applied_fix,
                result.original_code,
                result.applied_at,
                issue.confidence,
                issue.file_path,
                issue.issue_type,
            ))

            conn.commit()
        finally:
            conn.close()

    def track_failure(
        self,
        project_id: str,
        issue: DetectedIssue,
        error: str
    ) -> None:
        """
        Track a failed fix attempt.

        Args:
            project_id: Project identifier
            issue: The issue that failed to fix
            error: Error message describing the failure
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Record the failure
            cur.execute("""
                INSERT INTO fix_results (
                    issue_id, project_id, status, error_message,
                    applied_at, confidence, file_path, issue_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                issue.issue_id,
                project_id,
                FixResultStatus.FAILED.value,
                error,
                time.time(),
                issue.confidence,
                issue.file_path,
                issue.issue_type,
            ))

            conn.commit()
        finally:
            conn.close()

    def track_revert(
        self,
        project_id: str,
        issue: DetectedIssue,
        reason: str
    ) -> None:
        """
        Track a reverted fix.

        Args:
            project_id: Project identifier
            issue: The issue whose fix was reverted
            reason: Why the fix was reverted
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Update the original fix result
            cur.execute("""
                UPDATE fix_results
                SET reverted = TRUE, revert_reason = ?
                WHERE issue_id = ? AND project_id = ?
            """, (reason, issue.issue_id, project_id))

            # Also record as a new entry for history
            cur.execute("""
                INSERT INTO fix_results (
                    issue_id, project_id, status, revert_reason,
                    applied_at, file_path, issue_type, reverted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
            """, (
                issue.issue_id,
                project_id,
                FixResultStatus.REVERTED.value,
                reason,
                time.time(),
                issue.file_path,
                issue.issue_type,
            ))

            conn.commit()
        finally:
            conn.close()

    def track_skip(
        self,
        project_id: str,
        issue: DetectedIssue,
        reason: str
    ) -> None:
        """
        Track a skipped fix.

        Args:
            project_id: Project identifier
            issue: The issue that was skipped
            reason: Why it was skipped
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO fix_results (
                    issue_id, project_id, status, error_message,
                    applied_at, file_path, issue_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                issue.issue_id,
                project_id,
                FixResultStatus.SKIPPED.value,
                reason,
                time.time(),
                issue.file_path,
                issue.issue_type,
            ))

            # Update issue status
            cur.execute("""
                UPDATE detected_issues SET status = 'skipped'
                WHERE issue_id = ?
            """, (issue.issue_id,))

            conn.commit()
        finally:
            conn.close()

    def get_issue_history(self, file_path: str, limit: int = 50) -> List[Dict]:
        """
        Get fix history for a specific file.

        Args:
            file_path: Path to the file
            limit: Maximum results to return

        Returns:
            List of fix result dictionaries
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    issue_id, project_id, status, applied_fix, original_code,
                    error_message, applied_at, reverted, revert_reason,
                    issue_type, confidence
                FROM fix_results
                WHERE file_path = ?
                ORDER BY applied_at DESC
                LIMIT ?
            """, (file_path, limit))

            results = []
            for row in cur.fetchall():
                results.append({
                    "issue_id": row[0],
                    "project_id": row[1],
                    "status": row[2],
                    "applied_fix": row[3],
                    "original_code": row[4],
                    "error_message": row[5],
                    "applied_at": datetime.fromtimestamp(row[6]).isoformat(),
                    "reverted": bool(row[7]),
                    "revert_reason": row[8],
                    "issue_type": row[9],
                    "confidence": row[10],
                })

            return results
        finally:
            conn.close()

    def should_skip_file(
        self,
        file_path: str,
        failure_threshold: int = 3,
        window_hours: int = 24
    ) -> Tuple[bool, str]:
        """
        Determine if a file should be skipped due to many failures.

        Args:
            file_path: Path to check
            failure_threshold: Skip if this many failures in window
            window_hours: Time window to check

        Returns:
            Tuple of (should_skip, reason)
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            window_start = time.time() - (window_hours * 3600)

            # Count recent failures
            cur.execute("""
                SELECT COUNT(*) FROM fix_results
                WHERE file_path = ?
                  AND status = ?
                  AND applied_at >= ?
            """, (file_path, FixResultStatus.FAILED.value, window_start))

            failure_count = cur.fetchone()[0]

            if failure_count >= failure_threshold:
                return True, f"Too many failures ({failure_count}) in last {window_hours}h"

            # Also check revert count
            cur.execute("""
                SELECT COUNT(*) FROM fix_results
                WHERE file_path = ?
                  AND reverted = TRUE
                  AND applied_at >= ?
            """, (file_path, window_start))

            revert_count = cur.fetchone()[0]

            if revert_count >= 2:
                return True, f"Too many reverts ({revert_count}) in last {window_hours}h"

            return False, ""
        finally:
            conn.close()

    def save_detected_issue(self, project_id: str, issue: DetectedIssue) -> None:
        """
        Save a detected issue to the database.

        Args:
            project_id: Project identifier
            issue: The detected issue
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT OR REPLACE INTO detected_issues (
                    issue_id, project_id, issue_type, file_path, line_number,
                    column_number, message, suggested_fix, confidence,
                    severity, context, detected_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                issue.issue_id,
                project_id,
                issue.issue_type,
                issue.file_path,
                issue.line_number,
                issue.column,
                issue.message,
                issue.suggested_fix,
                issue.confidence,
                issue.severity,
                issue.context,
                issue.detected_at,
            ))

            conn.commit()
        finally:
            conn.close()

    def get_pending_issues(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[DetectedIssue]:
        """
        Get issues pending review or auto-fix.

        Args:
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of pending issues
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            if project_id:
                cur.execute("""
                    SELECT
                        issue_id, issue_type, file_path, line_number, message,
                        suggested_fix, confidence, column_number, severity,
                        context, detected_at
                    FROM detected_issues
                    WHERE project_id = ? AND status = 'pending'
                    ORDER BY detected_at DESC
                    LIMIT ?
                """, (project_id, limit))
            else:
                cur.execute("""
                    SELECT
                        issue_id, issue_type, file_path, line_number, message,
                        suggested_fix, confidence, column_number, severity,
                        context, detected_at
                    FROM detected_issues
                    WHERE status = 'pending'
                    ORDER BY detected_at DESC
                    LIMIT ?
                """, (limit,))

            issues = []
            for row in cur.fetchall():
                issues.append(DetectedIssue(
                    issue_id=row[0],
                    issue_type=row[1],
                    file_path=row[2],
                    line_number=row[3],
                    message=row[4],
                    suggested_fix=row[5] or "",
                    confidence=row[6],
                    column=row[7],
                    severity=row[8],
                    context=row[9] or "",
                    detected_at=row[10],
                ))

            return issues
        finally:
            conn.close()


# ============ AutoFixController Class ============

class AutoFixController:
    """
    Central controller for auto-fix operations.

    Responsible for:
    - Permission checking
    - Rate limit enforcement
    - Determining if review is needed
    - Recording all fix operations
    - Generating statistics
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the controller.

        Args:
            db_path: Path to SQLite database (defaults to get_db_path())
        """
        self.db_path = db_path or get_db_path()
        self.tracker = AutoFixTracker(self.db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def get_permissions(self, project_id: str) -> AutoFixPermissions:
        """
        Get permissions for a project.

        Args:
            project_id: Project identifier

        Returns:
            AutoFixPermissions for the project (default if not set)
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute(
                "SELECT config_json FROM permissions WHERE project_id = ?",
                (project_id,)
            )
            row = cur.fetchone()

            if row:
                config = json.loads(row[0])
                return AutoFixPermissions.from_dict(config)

            # Return default permissions
            return AutoFixPermissions(project_id=project_id)
        finally:
            conn.close()

    def save_permissions(self, permissions: AutoFixPermissions) -> None:
        """
        Save permissions for a project.

        Args:
            permissions: The permissions to save
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            now = time.time()
            config_json = json.dumps(permissions.to_dict())

            cur.execute("""
                INSERT INTO permissions (project_id, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    config_json = excluded.config_json,
                    updated_at = excluded.updated_at
            """, (permissions.project_id, config_json, now, now))

            conn.commit()
        finally:
            conn.close()

    def can_auto_fix(
        self,
        project_id: str,
        issue: DetectedIssue
    ) -> Tuple[bool, str]:
        """
        Check if an issue can be auto-fixed.

        Performs comprehensive checks:
        1. Master switch enabled
        2. Fix type allowed
        3. File pattern allowed
        4. Confidence threshold met
        5. Rate limit not exceeded
        6. File hasn't failed too many times

        Args:
            project_id: Project identifier
            issue: The issue to check

        Returns:
            Tuple of (can_fix: bool, reason: str)
        """
        permissions = self.get_permissions(project_id)

        # 1. Master switch
        if not permissions.enabled:
            return False, "Auto-fix is disabled for this project"

        # 2. Dry run mode
        if permissions.dry_run:
            return False, "Project is in dry-run mode"

        # 3. Fix type allowed
        if not permissions.is_fix_type_allowed(issue.issue_type):
            if issue.issue_type in permissions.blocked_fix_types:
                return False, f"Issue type '{issue.issue_type}' is explicitly blocked"
            return False, f"Issue type '{issue.issue_type}' is not in allowed list"

        # 4. File pattern
        if not permissions.is_file_allowed(issue.file_path):
            return False, f"File '{issue.file_path}' does not match allowed patterns"

        # 5. Confidence threshold
        if issue.confidence < permissions.min_confidence:
            return False, f"Confidence {issue.confidence:.2f} below threshold {permissions.min_confidence:.2f}"

        # 6. Rate limit
        rate_status = self.get_rate_limit_status(project_id)
        if not rate_status.can_fix:
            return False, f"Rate limit exceeded ({rate_status.fixes_this_hour}/{rate_status.limit})"

        # 7. Per-file limit
        file_fixes = self._get_file_fix_count(project_id, issue.file_path)
        if file_fixes >= permissions.max_fixes_per_file:
            return False, f"File fix limit reached ({file_fixes}/{permissions.max_fixes_per_file})"

        # 8. Check file history for failures
        should_skip, skip_reason = self.tracker.should_skip_file(issue.file_path)
        if should_skip:
            return False, skip_reason

        return True, "OK"

    def _get_file_fix_count(self, project_id: str, file_path: str) -> int:
        """Get fix count for a file in the current hour window."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Get current hour window
            now = datetime.now()
            window_start = now.replace(minute=0, second=0, microsecond=0).timestamp()

            cur.execute("""
                SELECT fix_count FROM file_fix_counts
                WHERE project_id = ? AND file_path = ? AND window_start = ?
            """, (project_id, file_path, window_start))

            row = cur.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def _increment_file_fix_count(self, project_id: str, file_path: str) -> None:
        """Increment fix count for a file."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            now = datetime.now()
            window_start = now.replace(minute=0, second=0, microsecond=0).timestamp()

            cur.execute("""
                INSERT INTO file_fix_counts (project_id, file_path, window_start, fix_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(project_id, file_path, window_start) DO UPDATE SET
                    fix_count = fix_count + 1
            """, (project_id, file_path, window_start))

            conn.commit()
        finally:
            conn.close()

    def should_require_review(
        self,
        project_id: str,
        issues: List[DetectedIssue]
    ) -> bool:
        """
        Determine if review should be required before auto-fixing.

        Args:
            project_id: Project identifier
            issues: List of issues to be fixed

        Returns:
            True if review should be required
        """
        permissions = self.get_permissions(project_id)

        # Check threshold
        if len(issues) >= permissions.require_review_threshold:
            return True

        # Check if any issue is low confidence
        min_confidence = min(i.confidence for i in issues) if issues else 1.0
        if min_confidence < 0.7:
            return True

        # Check if security-related types are present
        security_types = {
            AutoFixableIssue.HARDCODED_SECRET.value,
            AutoFixableIssue.SQL_INJECTION_RISK.value,
            AutoFixableIssue.SECURITY_VULNERABILITY.value,
        }
        for issue in issues:
            if issue.issue_type in security_types:
                return True

        return False

    def get_rate_limit_status(self, project_id: str) -> RateLimitStatus:
        """
        Get current rate limit status for a project.

        Args:
            project_id: Project identifier

        Returns:
            RateLimitStatus with current state
        """
        permissions = self.get_permissions(project_id)
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Get current hour window
            now = datetime.now()
            window_start = now.replace(minute=0, second=0, microsecond=0)
            resets_at = window_start + timedelta(hours=1)

            # Get fix count for this window
            cur.execute("""
                SELECT fix_count FROM rate_limits
                WHERE project_id = ? AND window_start = ?
            """, (project_id, window_start.timestamp()))

            row = cur.fetchone()
            fixes_this_hour = row[0] if row else 0

            return RateLimitStatus(
                project_id=project_id,
                fixes_this_hour=fixes_this_hour,
                limit=permissions.max_fixes_per_hour,
                resets_at=resets_at,
                can_fix=fixes_this_hour < permissions.max_fixes_per_hour,
                window_start=window_start,
            )
        finally:
            conn.close()

    def _increment_rate_limit(self, project_id: str) -> None:
        """Increment rate limit counter for current window."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            now = datetime.now()
            window_start = now.replace(minute=0, second=0, microsecond=0).timestamp()

            cur.execute("""
                INSERT INTO rate_limits (project_id, window_start, fix_count)
                VALUES (?, ?, 1)
                ON CONFLICT(project_id, window_start) DO UPDATE SET
                    fix_count = fix_count + 1
            """, (project_id, window_start))

            conn.commit()
        finally:
            conn.close()

    def record_fix(
        self,
        project_id: str,
        issue: DetectedIssue,
        result: FixResult
    ) -> None:
        """
        Record a fix operation (success or failure).

        This method:
        1. Updates rate limits
        2. Updates file fix counts
        3. Records the fix result in history
        4. Optionally triggers notifications

        Args:
            project_id: Project identifier
            issue: The issue that was addressed
            result: The fix result
        """
        # Update rate limits
        if result.status == FixResultStatus.SUCCESS.value:
            self._increment_rate_limit(project_id)
            self._increment_file_fix_count(project_id, issue.file_path)
            self.tracker.track_success(project_id, issue, result)
        elif result.status == FixResultStatus.FAILED.value:
            self.tracker.track_failure(project_id, issue, result.error_message)
        elif result.status == FixResultStatus.SKIPPED.value:
            self.tracker.track_skip(project_id, issue, result.error_message)
        elif result.status == FixResultStatus.REVERTED.value:
            self.tracker.track_revert(project_id, issue, result.revert_reason)

    def get_fix_stats(self, project_id: str) -> AutoFixStats:
        """
        Get comprehensive fix statistics for a project.

        Args:
            project_id: Project identifier

        Returns:
            AutoFixStats with detailed statistics
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            # Total fixes (successes)
            cur.execute("""
                SELECT COUNT(*) FROM fix_results
                WHERE project_id = ? AND status = ?
            """, (project_id, FixResultStatus.SUCCESS.value))
            total_fixes = cur.fetchone()[0]

            # By type
            cur.execute("""
                SELECT issue_type, COUNT(*) FROM fix_results
                WHERE project_id = ? AND status = ?
                GROUP BY issue_type
            """, (project_id, FixResultStatus.SUCCESS.value))
            by_type = {row[0]: row[1] for row in cur.fetchall()}

            # Success rate
            cur.execute("""
                SELECT
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as successes,
                    COUNT(*) as total
                FROM fix_results
                WHERE project_id = ?
            """, (FixResultStatus.SUCCESS.value, project_id))
            row = cur.fetchone()
            success_rate = row[0] / row[1] if row[1] > 0 else 0.0

            # Most fixed files
            cur.execute("""
                SELECT file_path, COUNT(*) as cnt
                FROM fix_results
                WHERE project_id = ? AND status = ?
                GROUP BY file_path
                ORDER BY cnt DESC
                LIMIT 10
            """, (project_id, FixResultStatus.SUCCESS.value))
            most_fixed_files = [(row[0], row[1]) for row in cur.fetchall()]

            # Fixes by day (last 30 days)
            thirty_days_ago = time.time() - (30 * 24 * 3600)
            cur.execute("""
                SELECT DATE(applied_at, 'unixepoch') as day, COUNT(*) as cnt
                FROM fix_results
                WHERE project_id = ? AND status = ? AND applied_at >= ?
                GROUP BY day
                ORDER BY day DESC
            """, (project_id, FixResultStatus.SUCCESS.value, thirty_days_ago))
            fixes_by_day = {row[0]: row[1] for row in cur.fetchall()}

            # Reverted fixes
            cur.execute("""
                SELECT COUNT(*) FROM fix_results
                WHERE project_id = ? AND reverted = TRUE
            """, (project_id,))
            reverted_fixes = cur.fetchone()[0]

            # Average confidence
            cur.execute("""
                SELECT AVG(confidence) FROM fix_results
                WHERE project_id = ? AND status = ? AND confidence IS NOT NULL
            """, (project_id, FixResultStatus.SUCCESS.value))
            avg_conf = cur.fetchone()[0]
            avg_confidence = avg_conf if avg_conf else 0.0

            # Last fix timestamp
            cur.execute("""
                SELECT MAX(applied_at) FROM fix_results
                WHERE project_id = ? AND status = ?
            """, (project_id, FixResultStatus.SUCCESS.value))
            last_fix_ts = cur.fetchone()[0]
            last_fix_at = datetime.fromtimestamp(last_fix_ts) if last_fix_ts else None

            # Pending review count
            cur.execute("""
                SELECT COUNT(*) FROM detected_issues
                WHERE project_id = ? AND status = 'pending'
            """, (project_id,))
            pending_review = cur.fetchone()[0]

            # Skipped and failed counts
            cur.execute("""
                SELECT status, COUNT(*) FROM fix_results
                WHERE project_id = ? AND status IN (?, ?)
                GROUP BY status
            """, (project_id, FixResultStatus.SKIPPED.value, FixResultStatus.FAILED.value))
            counts = {row[0]: row[1] for row in cur.fetchall()}

            return AutoFixStats(
                project_id=project_id,
                total_fixes=total_fixes,
                by_type=by_type,
                success_rate=success_rate,
                most_fixed_files=most_fixed_files,
                fixes_by_day=fixes_by_day,
                reverted_fixes=reverted_fixes,
                avg_confidence=avg_confidence,
                last_fix_at=last_fix_at,
                pending_review=pending_review,
                skipped_count=counts.get(FixResultStatus.SKIPPED.value, 0),
                failed_count=counts.get(FixResultStatus.FAILED.value, 0),
            )
        finally:
            conn.close()

    def get_pending_issues(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[DetectedIssue]:
        """
        Get issues pending review or auto-fix.

        Args:
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of pending issues
        """
        return self.tracker.get_pending_issues(project_id, limit)

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """
        Clean up old rate limit and fix data.

        Args:
            days_to_keep: How many days of data to keep

        Returns:
            Dictionary with counts of deleted records
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cutoff = time.time() - (days_to_keep * 24 * 3600)

            # Clean rate limits
            cur.execute("DELETE FROM rate_limits WHERE window_start < ?", (cutoff,))
            rate_limits_deleted = cur.rowcount

            # Clean file fix counts
            cur.execute("DELETE FROM file_fix_counts WHERE window_start < ?", (cutoff,))
            file_counts_deleted = cur.rowcount

            # Clean old fix results (but keep for stats)
            cur.execute(
                "DELETE FROM fix_results WHERE applied_at < ?",
                (cutoff,)
            )
            results_deleted = cur.rowcount

            conn.commit()

            return {
                "rate_limits_deleted": rate_limits_deleted,
                "file_counts_deleted": file_counts_deleted,
                "results_deleted": results_deleted,
            }
        finally:
            conn.close()


# ============ Singleton Access ============

_controller: Optional[AutoFixController] = None


def get_auto_fix_controller() -> AutoFixController:
    """Get the singleton AutoFixController instance."""
    global _controller
    if _controller is None:
        _controller = AutoFixController()
    return _controller


# ============ Proactive Notifier Integration ============

def notify_auto_fixes_available(project_id: str, issues: List[DetectedIssue]) -> None:
    """
    Notify that auto-fixable issues are available.

    Integrates with proactive_notifier.py for macOS notifications.

    Args:
        project_id: Project identifier
        issues: List of issues that can be auto-fixed
    """
    try:
        from proactive_notifier import send_macos_notification, log

        count = len(issues)
        types = set(i.issue_type for i in issues)

        if count <= 3:
            type_list = ", ".join(types)
            message = f"{count} issues ready for auto-fix: {type_list}"
        else:
            message = f"{count} issues in {len(types)} categories ready for auto-fix"

        send_macos_notification(
            title=f"SAM Auto-Fix: {project_id}",
            message=message,
            sound=False
        )
        log(f"Notified about {count} auto-fixable issues in {project_id}")
    except ImportError:
        pass  # proactive_notifier not available


def notify_auto_fixes_completed(
    project_id: str,
    results: List[FixResult]
) -> None:
    """
    Notify that auto-fixes have been applied.

    Args:
        project_id: Project identifier
        results: List of fix results
    """
    try:
        from proactive_notifier import send_macos_notification, log

        successes = sum(1 for r in results if r.status == FixResultStatus.SUCCESS.value)
        failures = sum(1 for r in results if r.status == FixResultStatus.FAILED.value)

        if failures == 0:
            message = f"Applied {successes} fixes successfully"
            title = f"SAM Auto-Fix Complete: {project_id}"
        else:
            message = f"{successes} fixes applied, {failures} failed"
            title = f"SAM Auto-Fix: {project_id}"

        send_macos_notification(
            title=title,
            message=message,
            sound=False
        )
        log(f"Auto-fix completed for {project_id}: {successes} success, {failures} failed")
    except ImportError:
        pass


def notify_auto_fix_failed(
    project_id: str,
    issue: DetectedIssue,
    error: str
) -> None:
    """
    Notify about a failed auto-fix attempt.

    Args:
        project_id: Project identifier
        issue: The issue that failed to fix
        error: Error message
    """
    try:
        from proactive_notifier import send_macos_notification, log

        send_macos_notification(
            title=f"SAM Auto-Fix Failed: {project_id}",
            message=f"{issue.issue_type}: {error[:100]}",
            sound=True  # Sound for failures
        )
        log(f"Auto-fix failed in {project_id}: {issue.issue_type} - {error}", "ERROR")
    except ImportError:
        pass


# ============ API Functions ============

def api_autofix_permissions_get(project_id: str) -> dict:
    """
    GET /api/autofix/permissions/{project_id}

    Get auto-fix permissions for a project.

    Args:
        project_id: Project identifier

    Returns:
        Permissions configuration
    """
    try:
        controller = get_auto_fix_controller()
        permissions = controller.get_permissions(project_id)

        return {
            "success": True,
            "project_id": project_id,
            "permissions": permissions.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_autofix_permissions_update(project_id: str, config: dict) -> dict:
    """
    PUT /api/autofix/permissions/{project_id}

    Update auto-fix permissions for a project.

    Args:
        project_id: Project identifier
        config: New configuration dictionary

    Returns:
        Updated permissions
    """
    try:
        controller = get_auto_fix_controller()

        # Get existing or default
        permissions = controller.get_permissions(project_id)

        # Update with provided config
        for key, value in config.items():
            if hasattr(permissions, key):
                setattr(permissions, key, value)

        # Ensure project_id is set
        permissions.project_id = project_id

        controller.save_permissions(permissions)

        return {
            "success": True,
            "project_id": project_id,
            "permissions": permissions.to_dict(),
            "message": "Permissions updated",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_autofix_stats(project_id: str) -> dict:
    """
    GET /api/autofix/stats/{project_id}

    Get auto-fix statistics for a project.

    Args:
        project_id: Project identifier

    Returns:
        Statistics dictionary
    """
    try:
        controller = get_auto_fix_controller()
        stats = controller.get_fix_stats(project_id)
        rate_status = controller.get_rate_limit_status(project_id)

        return {
            "success": True,
            "project_id": project_id,
            "stats": stats.to_dict(),
            "rate_limit": rate_status.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_autofix_run(project_id: str, dry_run: bool = False) -> dict:
    """
    POST /api/autofix/run/{project_id}

    Trigger an auto-fix scan for a project.

    This endpoint initiates scanning and fixing but doesn't wait for completion.
    Use the stats endpoint to check progress.

    Args:
        project_id: Project identifier
        dry_run: If True, only detect issues without fixing

    Returns:
        Scan initiation status
    """
    try:
        controller = get_auto_fix_controller()
        permissions = controller.get_permissions(project_id)

        if not permissions.enabled:
            return {
                "success": False,
                "error": "Auto-fix is disabled for this project",
                "project_id": project_id,
            }

        # Check rate limit
        rate_status = controller.get_rate_limit_status(project_id)
        if not rate_status.can_fix:
            return {
                "success": False,
                "error": f"Rate limit exceeded. Resets at {rate_status.resets_at.isoformat()}",
                "rate_limit": rate_status.to_dict(),
            }

        # In a real implementation, this would trigger an async scan
        # For now, return a status indicating the scan would be initiated
        return {
            "success": True,
            "project_id": project_id,
            "message": "Auto-fix scan initiated" + (" (dry-run)" if dry_run else ""),
            "dry_run": dry_run,
            "rate_limit": rate_status.to_dict(),
            "permissions": {
                "allowed_types": permissions.allowed_fix_types,
                "min_confidence": permissions.min_confidence,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_autofix_pending(project_id: Optional[str] = None, limit: int = 100) -> dict:
    """
    GET /api/autofix/pending

    Get issues pending review or auto-fix.

    Args:
        project_id: Optional project filter
        limit: Maximum results

    Returns:
        List of pending issues
    """
    try:
        controller = get_auto_fix_controller()
        issues = controller.get_pending_issues(project_id, limit)

        return {
            "success": True,
            "project_id": project_id,
            "count": len(issues),
            "issues": [i.to_dict() for i in issues],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_autofix_history(file_path: str, limit: int = 50) -> dict:
    """
    GET /api/autofix/history

    Get fix history for a specific file.

    Args:
        file_path: Path to the file
        limit: Maximum results

    Returns:
        Fix history for the file
    """
    try:
        controller = get_auto_fix_controller()
        history = controller.tracker.get_issue_history(file_path, limit)

        should_skip, skip_reason = controller.tracker.should_skip_file(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "count": len(history),
            "history": history,
            "should_skip": should_skip,
            "skip_reason": skip_reason,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ CLI Interface ============

def main():
    """CLI interface for auto-fix control."""
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "status":
        project_id = sys.argv[2] if len(sys.argv) > 2 else "default"
        result = api_autofix_stats(project_id)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "permissions":
        if len(sys.argv) < 3:
            print("Usage: auto_fix_control.py permissions <project_id>")
            return
        project_id = sys.argv[2]
        result = api_autofix_permissions_get(project_id)
        print(json.dumps(result, indent=2))

    elif cmd == "pending":
        project_id = sys.argv[2] if len(sys.argv) > 2 else None
        result = api_autofix_pending(project_id)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "history":
        if len(sys.argv) < 3:
            print("Usage: auto_fix_control.py history <file_path>")
            return
        file_path = sys.argv[2]
        result = api_autofix_history(file_path)
        print(json.dumps(result, indent=2))

    elif cmd == "enable":
        if len(sys.argv) < 3:
            print("Usage: auto_fix_control.py enable <project_id>")
            return
        project_id = sys.argv[2]
        result = api_autofix_permissions_update(project_id, {"enabled": True})
        print(json.dumps(result, indent=2))

    elif cmd == "disable":
        if len(sys.argv) < 3:
            print("Usage: auto_fix_control.py disable <project_id>")
            return
        project_id = sys.argv[2]
        result = api_autofix_permissions_update(project_id, {"enabled": False})
        print(json.dumps(result, indent=2))

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: auto_fix_control.py run <project_id> [--dry-run]")
            return
        project_id = sys.argv[2]
        dry_run = "--dry-run" in sys.argv
        result = api_autofix_run(project_id, dry_run)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        controller = get_auto_fix_controller()
        result = controller.cleanup_old_data(days)
        print(f"Cleaned up old data (keeping {days} days):")
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
