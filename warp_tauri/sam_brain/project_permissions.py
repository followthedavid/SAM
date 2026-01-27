#!/usr/bin/env python3
"""
SAM Project Permissions System

Per-project execution permissions for SAM's autonomous operations.
Controls what commands SAM can execute, what paths can be modified,
and what level of approval is required.

Usage:
    # CLI
    python project_permissions.py show [project_id]
    python project_permissions.py set <project_id> --preset {strict|normal|permissive|development}
    python project_permissions.py allow <project_id> --command "npm install"
    python project_permissions.py block <project_id> --path "/etc/passwd"
    python project_permissions.py defaults show
    python project_permissions.py defaults set --preset normal

    # Python API
    from project_permissions import PermissionManager, ProjectPermissions, RiskLevel

    manager = PermissionManager()
    can_exec, reason = manager.can_execute("sam_brain", "git status", RiskLevel.SAFE)
    if can_exec:
        # execute command
        pass
"""

import os
import sys
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto


# ============ Enums ============

class RiskLevel(Enum):
    """Risk level for commands and operations."""
    SAFE = "safe"           # Read-only, no side effects (ls, cat, git status)
    MODERATE = "moderate"   # May modify files but recoverable (git commit, npm install)
    DANGEROUS = "dangerous" # Destructive or irreversible (rm -rf, git push --force)
    FORBIDDEN = "forbidden" # Never allow (format disk, delete system files)

    def __lt__(self, other):
        """Allow comparison of risk levels."""
        order = {
            RiskLevel.SAFE: 0,
            RiskLevel.MODERATE: 1,
            RiskLevel.DANGEROUS: 2,
            RiskLevel.FORBIDDEN: 3,
        }
        return order[self] < order[other]


class NotificationLevel(Enum):
    """When to notify the user about operations."""
    ALL = "all"                     # Notify for every operation
    MODERATE_UP = "moderate_up"     # Notify for moderate and dangerous
    DANGEROUS_ONLY = "dangerous_only"  # Only notify for dangerous operations
    NONE = "none"                   # Never notify (silent operation)


class PermissionPreset(Enum):
    """Pre-configured permission profiles."""
    STRICT = "strict"           # Only safe commands, require approval for everything
    NORMAL = "normal"           # Safe auto-execute, moderate with approval, block dangerous
    PERMISSIVE = "permissive"   # Safe and moderate auto-execute, dangerous with approval
    DEVELOPMENT = "development" # Like permissive but also allow git operations


# ============ Data Classes ============

@dataclass
class ProjectPermissions:
    """
    Permission configuration for a single project.

    Attributes:
        project_id: Unique identifier for the project
        allow_safe_auto_execute: Run whitelisted safe commands without approval
        allow_moderate_with_approval: Allow moderate risk commands with user approval
        block_dangerous: Always block dangerous commands (cannot be overridden)
        allowed_commands: Additional whitelisted commands beyond defaults
        blocked_commands: Project-specific command blocklist
        allowed_paths: Paths SAM can modify
        blocked_paths: Paths SAM cannot touch
        max_timeout: Maximum execution time in seconds
        require_dry_run_first: Always show dry run before actual execution
        auto_rollback_on_error: Automatically rollback changes on error
        notification_level: When to notify user about operations
        created_at: When these permissions were created
        updated_at: When these permissions were last modified
        notes: Optional notes about permission decisions
    """
    project_id: str
    allow_safe_auto_execute: bool = True
    allow_moderate_with_approval: bool = True
    block_dangerous: bool = True
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    max_timeout: int = 120  # 2 minutes default
    require_dry_run_first: bool = False
    auto_rollback_on_error: bool = True
    notification_level: NotificationLevel = NotificationLevel.MODERATE_UP
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['notification_level'] = self.notification_level.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ProjectPermissions':
        """Create from dictionary."""
        if 'notification_level' in d and isinstance(d['notification_level'], str):
            d['notification_level'] = NotificationLevel(d['notification_level'])
        return cls(**d)


# ============ Command Risk Classification ============

# Commands that are always safe (read-only, no side effects)
SAFE_COMMANDS = {
    # File inspection
    'ls', 'cat', 'head', 'tail', 'less', 'more', 'wc', 'file', 'stat', 'du',
    'find', 'locate', 'which', 'whereis', 'type',
    # Text processing (read-only)
    'grep', 'egrep', 'fgrep', 'rg', 'ag', 'awk', 'sed',  # Note: sed -i is dangerous
    # Git read operations
    'git status', 'git log', 'git diff', 'git show', 'git branch', 'git remote',
    'git ls-files', 'git blame', 'git describe', 'git tag -l',
    # Python/Node read operations
    'python --version', 'python3 --version', 'pip list', 'pip show',
    'node --version', 'npm list', 'npm outdated', 'npm audit',
    # System info
    'pwd', 'whoami', 'hostname', 'date', 'uptime', 'uname',
    'env', 'printenv', 'echo',
    # Process info
    'ps', 'top -l 1', 'pgrep', 'lsof',
    # Disk/memory
    'df', 'free',
}

# Commands that can modify things but are generally recoverable
MODERATE_COMMANDS = {
    # Git write operations (recoverable via reflog)
    'git add', 'git commit', 'git checkout', 'git switch', 'git stash',
    'git fetch', 'git pull', 'git merge', 'git rebase',
    'git branch -d', 'git branch -m', 'git tag',
    # Package management (recoverable)
    'pip install', 'pip uninstall', 'pip upgrade',
    'npm install', 'npm uninstall', 'npm update', 'npm ci',
    'brew install', 'brew uninstall', 'brew update',
    # File operations (single files, not recursive)
    'touch', 'mkdir', 'cp', 'mv',
    # Build commands
    'make', 'cargo build', 'cargo run', 'cargo test',
    'python setup.py', 'python -m pytest', 'pytest',
    'npm run', 'npm test', 'npm build',
    # Editor commands
    'code', 'vim', 'nano',
}

# Commands that are destructive or hard to reverse
DANGEROUS_COMMANDS = {
    # Destructive file operations
    'rm', 'rmdir', 'rm -r', 'rm -rf', 'rm -f',
    'shred', 'truncate',
    # Git destructive operations
    'git push', 'git push --force', 'git push -f',
    'git reset --hard', 'git clean', 'git branch -D',
    'git rebase -i',  # Interactive rebase can lose commits
    # System modifications
    'chmod', 'chown', 'chgrp',
    'sudo', 'su',
    # Database operations
    'sqlite3', 'mysql', 'psql', 'mongo',
    # Network operations that could cause issues
    'curl -X POST', 'curl -X PUT', 'curl -X DELETE',
    'wget',
    # Container operations
    'docker rm', 'docker rmi', 'docker system prune',
    'docker-compose down', 'docker-compose rm',
}

# Commands that should never be allowed
FORBIDDEN_PATTERNS = [
    r'rm\s+-rf\s+/',             # Delete from root
    r'rm\s+-rf\s+\*',            # Delete everything in current dir
    r'rm\s+-rf\s+~',             # Delete home directory
    r':(){ :|:& };:',            # Fork bomb
    r'dd\s+if=.*of=/dev/',       # Write to disk device
    r'mkfs',                      # Format filesystem
    r'fdisk',                     # Partition disk
    r'>\s*/dev/sd',              # Overwrite disk
    r'mv\s+.*/dev/null',         # Move to null
    r'chmod\s+-R\s+777\s+/',     # World writable from root
    r'curl.*\|\s*bash',          # Pipe to bash (unsafe)
    r'wget.*\|\s*bash',          # Pipe to bash (unsafe)
    r'eval\s*\(',                 # Eval arbitrary code
]

# Sensitive paths that should always be blocked
SENSITIVE_PATHS = [
    '~/.ssh',
    '~/.gnupg',
    '~/.aws',
    '~/.config/gcloud',
    '~/.kube',
    '.env',
    '.env.local',
    '.env.production',
    'credentials.json',
    'credentials.yaml',
    'secrets.json',
    'secrets.yaml',
    '.netrc',
    '~/.bash_history',
    '~/.zsh_history',
    '/etc/passwd',
    '/etc/shadow',
    '/etc/sudoers',
    '/private/etc',
    '/System',
    '/Library/Preferences',
]


# ============ Path Validation ============

class PathValidator:
    """
    Validates paths for security and permission checks.
    Prevents path traversal attacks and blocks sensitive paths.
    """

    def __init__(self, allowed_paths: List[str] = None, blocked_paths: List[str] = None):
        """
        Initialize path validator.

        Args:
            allowed_paths: List of paths that are allowed (if empty, all non-blocked paths allowed)
            blocked_paths: List of paths that are always blocked
        """
        self.allowed_paths = [self._normalize_path(p) for p in (allowed_paths or [])]
        self.blocked_paths = [self._normalize_path(p) for p in (blocked_paths or [])]
        self.sensitive_paths = [self._normalize_path(p) for p in SENSITIVE_PATHS]

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path for comparison.
        Expands ~ and resolves relative paths.
        """
        # Expand home directory
        if path.startswith('~'):
            path = os.path.expanduser(path)

        # Resolve to absolute path if relative
        if not os.path.isabs(path):
            # Keep it relative but normalized
            path = os.path.normpath(path)
        else:
            path = os.path.abspath(path)

        return path

    def _is_subpath(self, path: str, parent: str) -> bool:
        """Check if path is under parent directory."""
        try:
            path = Path(path).resolve()
            parent = Path(parent).resolve()
            return path == parent or parent in path.parents
        except:
            return False

    def _contains_traversal(self, path: str) -> bool:
        """Check for path traversal attacks."""
        # Normalize and check for suspicious patterns
        normalized = os.path.normpath(path)

        # Check for common traversal patterns
        if '..' in path:
            # Allow .. only if it doesn't escape the resolved path
            try:
                # If the path with .. resolves differently than expected, it's traversal
                original_parts = path.split(os.sep)
                traversal_count = original_parts.count('..')
                if traversal_count > 0:
                    # Check if .. would go above an allowed directory
                    return True
            except:
                return True

        # Check for null bytes
        if '\x00' in path:
            return True

        # Check for suspicious URL-encoded patterns
        if '%2e' in path.lower() or '%2f' in path.lower():
            return True

        return False

    def is_sensitive(self, path: str) -> Tuple[bool, str]:
        """
        Check if a path is sensitive (credentials, keys, etc.).

        Returns:
            Tuple of (is_sensitive, reason)
        """
        normalized = self._normalize_path(path)
        path_lower = normalized.lower()
        filename = os.path.basename(path_lower)

        # Check against sensitive paths
        for sensitive in self.sensitive_paths:
            if self._is_subpath(normalized, sensitive):
                return True, f"Path is under sensitive directory: {sensitive}"
            if sensitive.endswith(filename):
                return True, f"Filename matches sensitive pattern: {filename}"

        # Check for common sensitive file patterns
        sensitive_patterns = [
            (r'\.env(\.\w+)?$', 'Environment file'),
            (r'credentials?\.(json|yaml|yml|xml)$', 'Credentials file'),
            (r'secrets?\.(json|yaml|yml|xml)$', 'Secrets file'),
            (r'\.pem$', 'Private key file'),
            (r'\.key$', 'Private key file'),
            (r'id_rsa', 'SSH private key'),
            (r'id_ed25519', 'SSH private key'),
            (r'\.p12$', 'Certificate file'),
            (r'\.pfx$', 'Certificate file'),
            (r'\.keystore$', 'Java keystore'),
            (r'token\.json$', 'OAuth token file'),
            (r'\.netrc$', 'Network credentials'),
        ]

        for pattern, reason in sensitive_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return True, reason

        return False, ""

    def validate(self, path: str, project_root: str = None) -> Tuple[bool, str]:
        """
        Validate if a path can be accessed/modified.

        Args:
            path: Path to validate
            project_root: Optional project root to restrict to

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check for path traversal
        if self._contains_traversal(path):
            return False, "Path traversal detected"

        normalized = self._normalize_path(path)

        # Check if blocked
        for blocked in self.blocked_paths:
            if self._is_subpath(normalized, blocked):
                return False, f"Path is blocked: {blocked}"

        # Check if sensitive
        is_sensitive, reason = self.is_sensitive(normalized)
        if is_sensitive:
            return False, f"Sensitive path: {reason}"

        # If allowed_paths specified, check if path is within allowed
        if self.allowed_paths:
            in_allowed = any(self._is_subpath(normalized, allowed) for allowed in self.allowed_paths)
            if not in_allowed:
                return False, f"Path not in allowed list"

        # If project_root specified, verify path is within project
        if project_root:
            project_root_normalized = self._normalize_path(project_root)
            if not self._is_subpath(normalized, project_root_normalized):
                return False, f"Path is outside project root: {project_root}"

        return True, "Path is valid"


# ============ Command Classifier ============

class CommandClassifier:
    """
    Classifies commands by risk level.
    Uses pattern matching and heuristics to determine command safety.
    """

    def __init__(self, extra_allowed: List[str] = None, extra_blocked: List[str] = None):
        """
        Initialize classifier with optional extra rules.

        Args:
            extra_allowed: Additional commands to treat as safe
            extra_blocked: Additional commands to always block
        """
        self.extra_allowed = set(extra_allowed or [])
        self.extra_blocked = set(extra_blocked or [])

    def _get_base_command(self, command: str) -> str:
        """Extract the base command from a full command line."""
        # Remove leading whitespace
        command = command.strip()

        # Handle pipes - classify based on first command
        if '|' in command:
            command = command.split('|')[0].strip()

        # Handle command substitution
        command = re.sub(r'\$\([^)]+\)', '', command)

        # Handle redirects
        command = re.split(r'[<>]', command)[0].strip()

        # Handle && and ||
        command = re.split(r'&&|\|\|', command)[0].strip()

        # Handle semicolons
        command = command.split(';')[0].strip()

        # Get first word (the actual command)
        parts = command.split()
        if not parts:
            return ""

        return parts[0]

    def _matches_pattern(self, command: str, patterns: set) -> bool:
        """Check if command matches any pattern in set."""
        command_lower = command.lower().strip()

        for pattern in patterns:
            pattern_lower = pattern.lower()
            # Exact match
            if command_lower == pattern_lower:
                return True
            # Prefix match (e.g., "git status" matches command "git status origin")
            if command_lower.startswith(pattern_lower + ' ') or command_lower.startswith(pattern_lower + '\t'):
                return True
            # The pattern itself is a prefix of command
            if pattern_lower.startswith(command_lower):
                return True

        return False

    def _is_forbidden(self, command: str) -> Tuple[bool, str]:
        """Check if command matches any forbidden pattern."""
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True, f"Matches forbidden pattern: {pattern}"
        return False, ""

    def classify(self, command: str) -> Tuple[RiskLevel, str]:
        """
        Classify a command by risk level.

        Args:
            command: Full command line to classify

        Returns:
            Tuple of (risk_level, reason)
        """
        command = command.strip()
        if not command:
            return RiskLevel.SAFE, "Empty command"

        # Check forbidden patterns first
        is_forbidden, reason = self._is_forbidden(command)
        if is_forbidden:
            return RiskLevel.FORBIDDEN, reason

        # Check extra blocked commands
        if self._matches_pattern(command, self.extra_blocked):
            return RiskLevel.FORBIDDEN, "Explicitly blocked command"

        # Check extra allowed commands
        if self._matches_pattern(command, self.extra_allowed):
            return RiskLevel.SAFE, "Explicitly allowed command"

        # Check safe commands
        if self._matches_pattern(command, SAFE_COMMANDS):
            return RiskLevel.SAFE, "Known safe command"

        # Check moderate commands
        if self._matches_pattern(command, MODERATE_COMMANDS):
            return RiskLevel.MODERATE, "Known moderate command"

        # Check dangerous commands
        if self._matches_pattern(command, DANGEROUS_COMMANDS):
            return RiskLevel.DANGEROUS, "Known dangerous command"

        # Special cases
        base_cmd = self._get_base_command(command)

        # rm with -f or -r flags is dangerous
        if base_cmd == 'rm':
            if '-f' in command or '-r' in command:
                return RiskLevel.DANGEROUS, "rm with force/recursive flags"
            return RiskLevel.MODERATE, "rm single file"

        # sed -i is dangerous (modifies in place)
        if base_cmd == 'sed' and '-i' in command:
            return RiskLevel.MODERATE, "sed in-place modification"

        # Any command with sudo
        if 'sudo' in command:
            return RiskLevel.DANGEROUS, "Command uses sudo"

        # Default to moderate for unknown commands
        return RiskLevel.MODERATE, f"Unknown command: {base_cmd}"


# ============ Permission Manager ============

class PermissionManager:
    """
    Manages project permissions with SQLite storage and optional JSON overrides.

    Storage hierarchy:
    1. Project-level JSON override: {project_root}/.sam/permissions.json
    2. SQLite database: ~/.sam/permissions.db
    3. Default permissions
    """

    DB_PATH = Path.home() / ".sam" / "permissions.db"

    def __init__(self, db_path: Path = None):
        """
        Initialize the permission manager.

        Args:
            db_path: Optional custom path for SQLite database
        """
        self.db_path = db_path or self.DB_PATH
        self._ensure_db()
        self._classifier = CommandClassifier()
        self._default_permissions: Optional[ProjectPermissions] = None

    def _ensure_db(self):
        """Ensure database and tables exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Main permissions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_permissions (
                project_id TEXT PRIMARY KEY,
                allow_safe_auto_execute INTEGER DEFAULT 1,
                allow_moderate_with_approval INTEGER DEFAULT 1,
                block_dangerous INTEGER DEFAULT 1,
                allowed_commands TEXT DEFAULT '[]',
                blocked_commands TEXT DEFAULT '[]',
                allowed_paths TEXT DEFAULT '[]',
                blocked_paths TEXT DEFAULT '[]',
                max_timeout INTEGER DEFAULT 120,
                require_dry_run_first INTEGER DEFAULT 0,
                auto_rollback_on_error INTEGER DEFAULT 1,
                notification_level TEXT DEFAULT 'moderate_up',
                created_at TEXT,
                updated_at TEXT,
                notes TEXT DEFAULT ''
            )
        """)

        # Defaults table (single row)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS default_permissions (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                allow_safe_auto_execute INTEGER DEFAULT 1,
                allow_moderate_with_approval INTEGER DEFAULT 1,
                block_dangerous INTEGER DEFAULT 1,
                allowed_commands TEXT DEFAULT '[]',
                blocked_commands TEXT DEFAULT '[]',
                allowed_paths TEXT DEFAULT '[]',
                blocked_paths TEXT DEFAULT '[]',
                max_timeout INTEGER DEFAULT 120,
                require_dry_run_first INTEGER DEFAULT 0,
                auto_rollback_on_error INTEGER DEFAULT 1,
                notification_level TEXT DEFAULT 'moderate_up',
                updated_at TEXT
            )
        """)

        # Audit log table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS permission_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                action TEXT,
                command TEXT,
                risk_level TEXT,
                allowed INTEGER,
                reason TEXT,
                timestamp TEXT
            )
        """)

        # Insert default row if not exists
        cur.execute("""
            INSERT OR IGNORE INTO default_permissions (id, updated_at)
            VALUES (1, ?)
        """, (datetime.now().isoformat(),))

        conn.commit()
        conn.close()

    def _load_project_json(self, project_id: str) -> Optional[ProjectPermissions]:
        """
        Load project-specific JSON override.

        Looks for .sam/permissions.json in the project directory.
        """
        # Try to find project root
        possible_roots = [
            Path.home() / "Projects" / project_id,
            Path.home() / "ReverseLab" / project_id,
            Path.home() / "ReverseLab" / "SAM" / project_id,
            Path.home() / "ReverseLab" / "SAM" / "warp_tauri" / project_id,
            Path(f"/Volumes/Plex/SSOT/projects/{project_id}"),
        ]

        for root in possible_roots:
            json_path = root / ".sam" / "permissions.json"
            if json_path.exists():
                try:
                    with open(json_path) as f:
                        data = json.load(f)
                        data['project_id'] = project_id
                        return ProjectPermissions.from_dict(data)
                except Exception as e:
                    print(f"Warning: Failed to load {json_path}: {e}", file=sys.stderr)

        return None

    def _load_from_db(self, project_id: str) -> Optional[ProjectPermissions]:
        """Load permissions from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM project_permissions WHERE project_id = ?", (project_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return ProjectPermissions(
            project_id=row['project_id'],
            allow_safe_auto_execute=bool(row['allow_safe_auto_execute']),
            allow_moderate_with_approval=bool(row['allow_moderate_with_approval']),
            block_dangerous=bool(row['block_dangerous']),
            allowed_commands=json.loads(row['allowed_commands']),
            blocked_commands=json.loads(row['blocked_commands']),
            allowed_paths=json.loads(row['allowed_paths']),
            blocked_paths=json.loads(row['blocked_paths']),
            max_timeout=row['max_timeout'],
            require_dry_run_first=bool(row['require_dry_run_first']),
            auto_rollback_on_error=bool(row['auto_rollback_on_error']),
            notification_level=NotificationLevel(row['notification_level']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            notes=row['notes'] or "",
        )

    def _save_to_db(self, permissions: ProjectPermissions):
        """Save permissions to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        permissions.updated_at = datetime.now().isoformat()

        cur.execute("""
            INSERT OR REPLACE INTO project_permissions
            (project_id, allow_safe_auto_execute, allow_moderate_with_approval, block_dangerous,
             allowed_commands, blocked_commands, allowed_paths, blocked_paths, max_timeout,
             require_dry_run_first, auto_rollback_on_error, notification_level, created_at, updated_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            permissions.project_id,
            int(permissions.allow_safe_auto_execute),
            int(permissions.allow_moderate_with_approval),
            int(permissions.block_dangerous),
            json.dumps(permissions.allowed_commands),
            json.dumps(permissions.blocked_commands),
            json.dumps(permissions.allowed_paths),
            json.dumps(permissions.blocked_paths),
            permissions.max_timeout,
            int(permissions.require_dry_run_first),
            int(permissions.auto_rollback_on_error),
            permissions.notification_level.value,
            permissions.created_at,
            permissions.updated_at,
            permissions.notes,
        ))

        conn.commit()
        conn.close()

    def _log_audit(self, project_id: str, action: str, command: str,
                   risk_level: RiskLevel, allowed: bool, reason: str):
        """Log permission check to audit log."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO permission_audit_log (project_id, action, command, risk_level, allowed, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, action, command, risk_level.value, int(allowed), reason, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_default_permissions(self) -> ProjectPermissions:
        """
        Get the default permissions used for new projects.

        Returns:
            Default ProjectPermissions configuration
        """
        if self._default_permissions:
            return self._default_permissions

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM default_permissions WHERE id = 1")
        row = cur.fetchone()
        conn.close()

        if not row:
            # Return hardcoded defaults
            return ProjectPermissions(
                project_id="__default__",
                notification_level=NotificationLevel.MODERATE_UP,
            )

        self._default_permissions = ProjectPermissions(
            project_id="__default__",
            allow_safe_auto_execute=bool(row['allow_safe_auto_execute']),
            allow_moderate_with_approval=bool(row['allow_moderate_with_approval']),
            block_dangerous=bool(row['block_dangerous']),
            allowed_commands=json.loads(row['allowed_commands']),
            blocked_commands=json.loads(row['blocked_commands']),
            allowed_paths=json.loads(row['allowed_paths']),
            blocked_paths=json.loads(row['blocked_paths']),
            max_timeout=row['max_timeout'],
            require_dry_run_first=bool(row['require_dry_run_first']),
            auto_rollback_on_error=bool(row['auto_rollback_on_error']),
            notification_level=NotificationLevel(row['notification_level']),
        )

        return self._default_permissions

    def set_default_permissions(self, permissions: ProjectPermissions):
        """
        Set the default permissions for new projects.

        Args:
            permissions: New default permissions
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            UPDATE default_permissions SET
                allow_safe_auto_execute = ?,
                allow_moderate_with_approval = ?,
                block_dangerous = ?,
                allowed_commands = ?,
                blocked_commands = ?,
                allowed_paths = ?,
                blocked_paths = ?,
                max_timeout = ?,
                require_dry_run_first = ?,
                auto_rollback_on_error = ?,
                notification_level = ?,
                updated_at = ?
            WHERE id = 1
        """, (
            int(permissions.allow_safe_auto_execute),
            int(permissions.allow_moderate_with_approval),
            int(permissions.block_dangerous),
            json.dumps(permissions.allowed_commands),
            json.dumps(permissions.blocked_commands),
            json.dumps(permissions.allowed_paths),
            json.dumps(permissions.blocked_paths),
            permissions.max_timeout,
            int(permissions.require_dry_run_first),
            int(permissions.auto_rollback_on_error),
            permissions.notification_level.value,
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()

        # Clear cache
        self._default_permissions = None

    def get_permissions(self, project_id: str) -> ProjectPermissions:
        """
        Get permissions for a project.

        Priority:
        1. Project-level JSON override
        2. SQLite database entry
        3. Default permissions

        Args:
            project_id: Project identifier

        Returns:
            ProjectPermissions for the project
        """
        # Try JSON override first
        json_perms = self._load_project_json(project_id)
        if json_perms:
            return json_perms

        # Try database
        db_perms = self._load_from_db(project_id)
        if db_perms:
            return db_perms

        # Return defaults with project_id set
        defaults = self.get_default_permissions()
        return ProjectPermissions(
            project_id=project_id,
            allow_safe_auto_execute=defaults.allow_safe_auto_execute,
            allow_moderate_with_approval=defaults.allow_moderate_with_approval,
            block_dangerous=defaults.block_dangerous,
            allowed_commands=defaults.allowed_commands.copy(),
            blocked_commands=defaults.blocked_commands.copy(),
            allowed_paths=defaults.allowed_paths.copy(),
            blocked_paths=defaults.blocked_paths.copy(),
            max_timeout=defaults.max_timeout,
            require_dry_run_first=defaults.require_dry_run_first,
            auto_rollback_on_error=defaults.auto_rollback_on_error,
            notification_level=defaults.notification_level,
        )

    def set_permissions(self, project_id: str, permissions: ProjectPermissions):
        """
        Set permissions for a project.

        Args:
            project_id: Project identifier
            permissions: New permissions to set
        """
        permissions.project_id = project_id
        self._save_to_db(permissions)

    def apply_preset(self, project_id: str, preset: PermissionPreset) -> ProjectPermissions:
        """
        Apply a permission preset to a project.

        Args:
            project_id: Project identifier
            preset: Preset to apply

        Returns:
            The resulting permissions
        """
        perms = self.get_permissions(project_id)

        if preset == PermissionPreset.STRICT:
            perms.allow_safe_auto_execute = False
            perms.allow_moderate_with_approval = True
            perms.block_dangerous = True
            perms.require_dry_run_first = True
            perms.notification_level = NotificationLevel.ALL
            perms.notes = "STRICT preset: Approval required for all commands"

        elif preset == PermissionPreset.NORMAL:
            perms.allow_safe_auto_execute = True
            perms.allow_moderate_with_approval = True
            perms.block_dangerous = True
            perms.require_dry_run_first = False
            perms.notification_level = NotificationLevel.MODERATE_UP
            perms.notes = "NORMAL preset: Safe commands auto-execute, moderate requires approval"

        elif preset == PermissionPreset.PERMISSIVE:
            perms.allow_safe_auto_execute = True
            perms.allow_moderate_with_approval = True
            perms.block_dangerous = False  # Allow with approval
            perms.require_dry_run_first = False
            perms.notification_level = NotificationLevel.DANGEROUS_ONLY
            perms.notes = "PERMISSIVE preset: Safe and moderate auto-execute, dangerous requires approval"

        elif preset == PermissionPreset.DEVELOPMENT:
            perms.allow_safe_auto_execute = True
            perms.allow_moderate_with_approval = True
            perms.block_dangerous = False
            perms.require_dry_run_first = False
            perms.notification_level = NotificationLevel.DANGEROUS_ONLY
            # Add git operations to allowed commands
            perms.allowed_commands = list(set(perms.allowed_commands + [
                'git push', 'git push origin', 'git push -u',
                'git reset --hard', 'git clean -fd',
            ]))
            perms.notes = "DEVELOPMENT preset: Permissive with git operations allowed"

        self.set_permissions(project_id, perms)
        return perms

    def can_execute(self, project_id: str, command: str,
                    risk_level: RiskLevel = None) -> Tuple[bool, str]:
        """
        Check if a command can be executed for a project.

        Args:
            project_id: Project identifier
            command: Command to check
            risk_level: Optional pre-computed risk level

        Returns:
            Tuple of (allowed, reason)
        """
        perms = self.get_permissions(project_id)

        # Create classifier with project-specific rules
        classifier = CommandClassifier(
            extra_allowed=perms.allowed_commands,
            extra_blocked=perms.blocked_commands,
        )

        # Classify command if not provided
        if risk_level is None:
            risk_level, classification_reason = classifier.classify(command)
        else:
            classification_reason = ""

        # Check based on risk level and permissions
        if risk_level == RiskLevel.FORBIDDEN:
            reason = f"FORBIDDEN: {classification_reason}"
            self._log_audit(project_id, "execute", command, risk_level, False, reason)
            return False, reason

        if risk_level == RiskLevel.DANGEROUS:
            if perms.block_dangerous:
                reason = f"BLOCKED: Dangerous command blocked by policy. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, False, reason)
                return False, reason
            else:
                reason = f"APPROVAL_REQUIRED: Dangerous command. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, True, reason)
                return True, reason

        if risk_level == RiskLevel.MODERATE:
            if perms.allow_moderate_with_approval:
                reason = f"APPROVAL_REQUIRED: Moderate risk command. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, True, reason)
                return True, reason
            else:
                reason = f"BLOCKED: Moderate commands require explicit approval. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, False, reason)
                return False, reason

        if risk_level == RiskLevel.SAFE:
            if perms.allow_safe_auto_execute:
                reason = f"AUTO_EXECUTE: Safe command. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, True, reason)
                return True, reason
            else:
                reason = f"APPROVAL_REQUIRED: Auto-execute disabled. {classification_reason}"
                self._log_audit(project_id, "execute", command, risk_level, True, reason)
                return True, reason

        # Default deny
        reason = f"DENIED: Unknown risk level"
        self._log_audit(project_id, "execute", command, risk_level, False, reason)
        return False, reason

    def can_modify_path(self, project_id: str, path: str,
                        project_root: str = None) -> Tuple[bool, str]:
        """
        Check if a path can be modified for a project.

        Args:
            project_id: Project identifier
            path: Path to check
            project_root: Optional project root directory

        Returns:
            Tuple of (allowed, reason)
        """
        perms = self.get_permissions(project_id)

        validator = PathValidator(
            allowed_paths=perms.allowed_paths,
            blocked_paths=perms.blocked_paths,
        )

        is_valid, reason = validator.validate(path, project_root)

        self._log_audit(project_id, "modify_path", path, RiskLevel.MODERATE, is_valid, reason)

        return is_valid, reason

    def list_projects(self) -> List[str]:
        """List all projects with stored permissions."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT project_id FROM project_permissions ORDER BY project_id")
        projects = [row[0] for row in cur.fetchall()]

        conn.close()
        return projects

    def get_audit_log(self, project_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit log entries.

        Args:
            project_id: Filter by project (None for all)
            limit: Maximum entries to return

        Returns:
            List of audit log entries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if project_id:
            cur.execute("""
                SELECT * FROM permission_audit_log
                WHERE project_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (project_id, limit))
        else:
            cur.execute("""
                SELECT * FROM permission_audit_log
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]


# ============ API Functions (for sam_api.py integration) ============

def api_permissions_get(project_id: str) -> Dict[str, Any]:
    """
    API endpoint: Get permissions for a project.

    GET /api/permissions/{project_id}
    """
    try:
        manager = PermissionManager()
        perms = manager.get_permissions(project_id)
        return {
            "success": True,
            "project_id": project_id,
            "permissions": perms.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_permissions_set(project_id: str, permissions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    API endpoint: Set permissions for a project.

    PUT /api/permissions/{project_id}
    """
    try:
        manager = PermissionManager()
        perms = ProjectPermissions.from_dict({**permissions_data, 'project_id': project_id})
        manager.set_permissions(project_id, perms)
        return {
            "success": True,
            "project_id": project_id,
            "message": f"Permissions updated for {project_id}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_permissions_defaults_get() -> Dict[str, Any]:
    """
    API endpoint: Get default permissions.

    GET /api/permissions/defaults
    """
    try:
        manager = PermissionManager()
        perms = manager.get_default_permissions()
        return {
            "success": True,
            "permissions": perms.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_permissions_defaults_set(permissions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    API endpoint: Set default permissions.

    PUT /api/permissions/defaults
    """
    try:
        manager = PermissionManager()
        perms = ProjectPermissions.from_dict({**permissions_data, 'project_id': '__default__'})
        manager.set_default_permissions(perms)
        return {
            "success": True,
            "message": "Default permissions updated",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_permissions_check(project_id: str, command: str) -> Dict[str, Any]:
    """
    API endpoint: Check if a command can be executed.

    POST /api/permissions/{project_id}/check
    """
    try:
        manager = PermissionManager()
        classifier = CommandClassifier()
        risk_level, classification = classifier.classify(command)
        can_exec, reason = manager.can_execute(project_id, command, risk_level)

        return {
            "success": True,
            "project_id": project_id,
            "command": command,
            "risk_level": risk_level.value,
            "classification": classification,
            "allowed": can_exec,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_permissions_audit(project_id: str = None, limit: int = 100) -> Dict[str, Any]:
    """
    API endpoint: Get audit log.

    GET /api/permissions/audit[/{project_id}]
    """
    try:
        manager = PermissionManager()
        logs = manager.get_audit_log(project_id, limit)
        return {
            "success": True,
            "project_id": project_id,
            "count": len(logs),
            "entries": logs,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ CLI ============

def cli_show(project_id: str = None):
    """Show permissions for a project or all projects."""
    manager = PermissionManager()

    if project_id:
        perms = manager.get_permissions(project_id)
        print(f"\nPermissions for: {project_id}")
        print("=" * 50)
        print(json.dumps(perms.to_dict(), indent=2))
    else:
        print("\nConfigured Projects:")
        print("=" * 50)
        projects = manager.list_projects()
        if not projects:
            print("No projects configured. Using defaults.")
        else:
            for pid in projects:
                perms = manager.get_permissions(pid)
                status = "STRICT" if not perms.allow_safe_auto_execute else (
                    "NORMAL" if perms.block_dangerous else "PERMISSIVE"
                )
                print(f"  {pid:30} [{status}]")

        print("\nDefault Permissions:")
        defaults = manager.get_default_permissions()
        print(json.dumps(defaults.to_dict(), indent=2))


def cli_set_preset(project_id: str, preset_name: str):
    """Set a permission preset for a project."""
    manager = PermissionManager()

    try:
        preset = PermissionPreset(preset_name.lower())
    except ValueError:
        print(f"Error: Unknown preset '{preset_name}'")
        print(f"Available presets: {', '.join(p.value for p in PermissionPreset)}")
        return

    perms = manager.apply_preset(project_id, preset)
    print(f"Applied {preset_name.upper()} preset to {project_id}")
    print(json.dumps(perms.to_dict(), indent=2))


def cli_allow_command(project_id: str, command: str):
    """Add a command to the allowed list."""
    manager = PermissionManager()
    perms = manager.get_permissions(project_id)

    if command not in perms.allowed_commands:
        perms.allowed_commands.append(command)
        manager.set_permissions(project_id, perms)
        print(f"Added '{command}' to allowed commands for {project_id}")
    else:
        print(f"Command '{command}' already in allowed list")


def cli_block_command(project_id: str, command: str):
    """Add a command to the blocked list."""
    manager = PermissionManager()
    perms = manager.get_permissions(project_id)

    if command not in perms.blocked_commands:
        perms.blocked_commands.append(command)
        manager.set_permissions(project_id, perms)
        print(f"Added '{command}' to blocked commands for {project_id}")
    else:
        print(f"Command '{command}' already in blocked list")


def cli_allow_path(project_id: str, path: str):
    """Add a path to the allowed list."""
    manager = PermissionManager()
    perms = manager.get_permissions(project_id)

    if path not in perms.allowed_paths:
        perms.allowed_paths.append(path)
        manager.set_permissions(project_id, perms)
        print(f"Added '{path}' to allowed paths for {project_id}")
    else:
        print(f"Path '{path}' already in allowed list")


def cli_block_path(project_id: str, path: str):
    """Add a path to the blocked list."""
    manager = PermissionManager()
    perms = manager.get_permissions(project_id)

    if path not in perms.blocked_paths:
        perms.blocked_paths.append(path)
        manager.set_permissions(project_id, perms)
        print(f"Added '{path}' to blocked paths for {project_id}")
    else:
        print(f"Path '{path}' already in blocked list")


def cli_check(project_id: str, command: str):
    """Check if a command would be allowed."""
    manager = PermissionManager()
    classifier = CommandClassifier()

    risk_level, classification = classifier.classify(command)
    can_exec, reason = manager.can_execute(project_id, command, risk_level)

    print(f"\nCommand Check for: {project_id}")
    print("=" * 50)
    print(f"Command:        {command}")
    print(f"Risk Level:     {risk_level.value}")
    print(f"Classification: {classification}")
    print(f"Allowed:        {'Yes' if can_exec else 'No'}")
    print(f"Reason:         {reason}")


def cli_audit(project_id: str = None, limit: int = 20):
    """Show recent audit log."""
    manager = PermissionManager()
    logs = manager.get_audit_log(project_id, limit)

    print(f"\nAudit Log{' for ' + project_id if project_id else ''}:")
    print("=" * 80)

    if not logs:
        print("No audit entries found.")
        return

    for entry in logs:
        status = "ALLOWED" if entry['allowed'] else "DENIED"
        print(f"[{entry['timestamp'][:19]}] {entry['project_id']:20} {status:7} {entry['risk_level']:10} {entry['command'][:30]}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAM Project Permissions Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all project permissions
  python project_permissions.py show

  # Show permissions for specific project
  python project_permissions.py show sam_brain

  # Apply a preset to a project
  python project_permissions.py set sam_brain --preset normal

  # Allow a specific command
  python project_permissions.py allow sam_brain --command "git push"

  # Block a path
  python project_permissions.py block sam_brain --path "~/.ssh"

  # Check if command would be allowed
  python project_permissions.py check sam_brain "rm -rf node_modules"

  # Show audit log
  python project_permissions.py audit
  python project_permissions.py audit sam_brain

  # Set default permissions
  python project_permissions.py defaults set --preset normal
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # show command
    show_parser = subparsers.add_parser('show', help='Show permissions')
    show_parser.add_argument('project_id', nargs='?', help='Project ID (optional)')

    # set command
    set_parser = subparsers.add_parser('set', help='Set permission preset')
    set_parser.add_argument('project_id', help='Project ID')
    set_parser.add_argument('--preset', required=True,
                           choices=['strict', 'normal', 'permissive', 'development'],
                           help='Permission preset to apply')

    # allow command
    allow_parser = subparsers.add_parser('allow', help='Allow command or path')
    allow_parser.add_argument('project_id', help='Project ID')
    allow_parser.add_argument('--command', help='Command to allow')
    allow_parser.add_argument('--path', help='Path to allow')

    # block command
    block_parser = subparsers.add_parser('block', help='Block command or path')
    block_parser.add_argument('project_id', help='Project ID')
    block_parser.add_argument('--command', help='Command to block')
    block_parser.add_argument('--path', help='Path to block')

    # check command
    check_parser = subparsers.add_parser('check', help='Check if command is allowed')
    check_parser.add_argument('project_id', help='Project ID')
    check_parser.add_argument('command', help='Command to check')

    # audit command
    audit_parser = subparsers.add_parser('audit', help='Show audit log')
    audit_parser.add_argument('project_id', nargs='?', help='Project ID (optional)')
    audit_parser.add_argument('--limit', type=int, default=20, help='Number of entries')

    # defaults command
    defaults_parser = subparsers.add_parser('defaults', help='Manage default permissions')
    defaults_sub = defaults_parser.add_subparsers(dest='defaults_cmd')

    defaults_show = defaults_sub.add_parser('show', help='Show defaults')
    defaults_set = defaults_sub.add_parser('set', help='Set defaults')
    defaults_set.add_argument('--preset', required=True,
                             choices=['strict', 'normal', 'permissive', 'development'],
                             help='Default preset')

    args = parser.parse_args()

    if args.command == 'show':
        cli_show(args.project_id)

    elif args.command == 'set':
        cli_set_preset(args.project_id, args.preset)

    elif args.command == 'allow':
        if args.command:
            cli_allow_command(args.project_id, args.command)
        elif args.path:
            cli_allow_path(args.project_id, args.path)
        else:
            print("Error: Must specify --command or --path")

    elif args.command == 'block':
        if hasattr(args, 'command') and args.command:
            cli_block_command(args.project_id, args.command)
        elif args.path:
            cli_block_path(args.project_id, args.path)
        else:
            print("Error: Must specify --command or --path")

    elif args.command == 'check':
        cli_check(args.project_id, args.command)

    elif args.command == 'audit':
        cli_audit(args.project_id, args.limit)

    elif args.command == 'defaults':
        if args.defaults_cmd == 'show':
            manager = PermissionManager()
            perms = manager.get_default_permissions()
            print("\nDefault Permissions:")
            print("=" * 50)
            print(json.dumps(perms.to_dict(), indent=2))
        elif args.defaults_cmd == 'set':
            manager = PermissionManager()
            manager.apply_preset("__default__", PermissionPreset(args.preset))
            # Actually set as defaults
            perms = manager.get_permissions("__default__")
            manager.set_default_permissions(perms)
            print(f"Default permissions set to {args.preset.upper()} preset")
        else:
            defaults_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
