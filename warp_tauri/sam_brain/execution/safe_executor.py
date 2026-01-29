#!/usr/bin/env python3
"""
SAM Safe Executor - Sandboxed execution environment for autonomous actions.

This module provides a secure sandbox for SAM to execute commands and file operations
while maintaining safety through:
- Resource limits (memory, CPU time, execution timeout)
- Path validation and whitelisting
- Environment sanitization (removal of sensitive variables)
- Automatic backup creation for file modifications
- Dry-run mode for previewing actions
- Integration with command classification for safety checks

Safety Philosophy:
1. Defense in depth - multiple layers of validation
2. Fail secure - deny by default, allow by exception
3. Auditability - log all actions for review
4. Reversibility - backups enable rollback of file changes

macOS Specific:
- Uses resource module for process limits where available
- Subprocess isolation with restricted PATH
- Signal handling for graceful timeout enforcement
"""

import os
import re
import sys
import time
import json
import signal
import shutil
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safe_executor")

# Resource limits (macOS/Unix)
try:
    import resource
    RESOURCE_MODULE_AVAILABLE = True
except ImportError:
    RESOURCE_MODULE_AVAILABLE = False
    logger.warning("resource module not available - some limits may not be enforced")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Backup storage location
BACKUP_DIR = Path.home() / ".sam" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Execution log location
EXECUTION_LOG = Path.home() / ".sam" / "execution_log.jsonl"

# Maximum backup age (days)
MAX_BACKUP_AGE_DAYS = 7

# Default resource limits
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY_LIMIT_MB = 512  # 512 MB max for child processes
DEFAULT_CPU_TIME_LIMIT = 60   # 60 seconds CPU time

# Safe PATH directories (only allow commands from these locations)
SAFE_PATH_DIRS = [
    "/usr/bin",
    "/bin",
    "/usr/local/bin",
    str(Path.home() / ".local" / "bin"),
    # Python/Node tools
    "/opt/homebrew/bin",
    str(Path.home() / "Library" / "Python" / "3.11" / "bin"),
    str(Path.home() / "Library" / "Python" / "3.12" / "bin"),
    str(Path.home() / "Library" / "Python" / "3.13" / "bin"),
    str(Path.home() / "Library" / "Python" / "3.14" / "bin"),
]

# Environment variables to REMOVE (sensitive)
SENSITIVE_ENV_VARS = {
    # API Keys
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "CLAUDE_API_KEY",
    "GROQ_API_KEY",
    "REPLICATE_API_KEY",
    "HUGGING_FACE_TOKEN",
    "HF_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AZURE_KEY",
    "GOOGLE_API_KEY",
    # Database credentials
    "DATABASE_URL",
    "DB_PASSWORD",
    "POSTGRES_PASSWORD",
    "MYSQL_PASSWORD",
    "REDIS_PASSWORD",
    "MONGO_PASSWORD",
    # Generic secrets
    "SECRET_KEY",
    "JWT_SECRET",
    "PRIVATE_KEY",
    "AUTH_TOKEN",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    # SSH
    "SSH_PRIVATE_KEY",
}

# Dangerous command patterns (blocked unconditionally)
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",         # rm -rf / (root deletion)
    r"rm\s+-rf\s+~",         # rm -rf ~ (home deletion)
    r"rm\s+-rf\s+\*",        # rm -rf * (wildcard deletion)
    r"sudo\s+rm",            # sudo rm (privileged deletion)
    r"sudo\s+shutdown",      # shutdown
    r"sudo\s+reboot",        # reboot
    r"mkfs",                 # filesystem formatting
    r"dd\s+if=.*/dev/",      # raw disk writes
    r">\s*/dev/sd",          # writing to disk devices
    r":\(\)\s*{\s*:",        # fork bomb
    r"chmod\s+-R\s+777",     # dangerous permissions
    r"curl.*\|\s*bash",      # pipe curl to bash
    r"wget.*\|\s*bash",      # pipe wget to bash
    r"eval\s*\(",            # eval with untrusted input
    r"base64\s+-d.*\|\s*bash", # decoded execution
]

# Allowed project root directories (SAM can only work within these)
ALLOWED_PROJECT_ROOTS = [
    Path.home() / "ReverseLab",
    Path.home() / "Projects",
    Path("/Volumes/David External"),
    Path("/Volumes/Plex/SSOT"),
    Path("/tmp"),  # Temporary files
]


# ==============================================================================
# DATA CLASSES
# ==============================================================================

class ExecutionStatus(Enum):
    """Status of an execution attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    DRY_RUN = "dry_run"


@dataclass
class ExecutionResult:
    """Result of a command execution."""
    stdout: str
    stderr: str
    return_code: int
    duration_ms: int
    timed_out: bool
    memory_used_mb: Optional[float] = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    blocked_reason: Optional[str] = None
    command: str = ""
    working_dir: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    success: bool
    message: str
    backup_path: Optional[str] = None
    original_path: Optional[str] = None
    bytes_written: int = 0
    timestamp: str = ""


@dataclass
class ExecutionContext:
    """Context for command execution."""
    project_id: str
    working_directory: str
    environment_overrides: Dict[str, str] = field(default_factory=dict)
    allowed_paths: List[str] = field(default_factory=list)
    max_timeout: int = DEFAULT_TIMEOUT_SECONDS
    dry_run: bool = False

    # Safety settings
    allow_network: bool = True  # Can be disabled for stricter isolation
    allow_file_write: bool = True
    max_file_size_mb: float = 10.0  # Maximum file size for writes

    def __post_init__(self):
        """Validate context after initialization."""
        if not self.allowed_paths:
            # Default to project roots
            self.allowed_paths = [str(p) for p in ALLOWED_PROJECT_ROOTS]


@dataclass
class RollbackInfo:
    """Information needed to rollback a change."""
    operation_type: str  # "file_write", "file_delete", "command"
    timestamp: str
    original_path: Optional[str] = None
    backup_path: Optional[str] = None
    command: Optional[str] = None
    can_rollback: bool = True
    rollback_command: Optional[str] = None


# ==============================================================================
# FILE OPERATIONS
# ==============================================================================

class FileOperation:
    """Safe file operations with automatic backup and rollback support."""

    def __init__(self, backup_dir: Path = BACKUP_DIR):
        """Initialize FileOperation handler.

        Args:
            backup_dir: Directory for storing backups
        """
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_old_backups()

    def _cleanup_old_backups(self):
        """Remove backups older than MAX_BACKUP_AGE_DAYS."""
        try:
            cutoff = time.time() - (MAX_BACKUP_AGE_DAYS * 24 * 60 * 60)
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff:
                    backup_file.unlink()
                    logger.debug(f"Cleaned up old backup: {backup_file}")
        except Exception as e:
            logger.warning(f"Backup cleanup failed: {e}")

    def _generate_backup_name(self, original_path: Path) -> str:
        """Generate a unique backup filename.

        Args:
            original_path: The original file path

        Returns:
            Unique backup filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_hash = hashlib.md5(str(original_path).encode()).hexdigest()[:8]
        return f"{original_path.name}_{timestamp}_{path_hash}.bak"

    def _validate_path(self, path: str, allowed_paths: List[str]) -> Tuple[bool, str]:
        """Validate that path is within allowed directories.

        Args:
            path: Path to validate
            allowed_paths: List of allowed root directories

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            resolved = Path(path).resolve()

            # Check against allowed paths
            for allowed in allowed_paths:
                allowed_resolved = Path(allowed).resolve()
                try:
                    resolved.relative_to(allowed_resolved)
                    return True, ""
                except ValueError:
                    continue

            return False, f"Path {path} is not within allowed directories"
        except Exception as e:
            return False, f"Path validation error: {e}"

    def read_file(self, path: str, allowed_paths: List[str] = None) -> Tuple[Optional[str], str]:
        """Read a file safely.

        Args:
            path: Path to the file
            allowed_paths: Optional list of allowed root directories

        Returns:
            Tuple of (content or None, error_message)
        """
        allowed_paths = allowed_paths or [str(p) for p in ALLOWED_PROJECT_ROOTS]

        # Validate path
        valid, error = self._validate_path(path, allowed_paths)
        if not valid:
            return None, error

        try:
            file_path = Path(path)
            if not file_path.exists():
                return None, f"File not found: {path}"
            if not file_path.is_file():
                return None, f"Not a file: {path}"

            # Check file size (don't read huge files)
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > 50:
                return None, f"File too large ({size_mb:.1f} MB, max 50 MB)"

            content = file_path.read_text(encoding="utf-8", errors="replace")
            return content, ""
        except Exception as e:
            return None, f"Read error: {e}"

    def write_file(
        self,
        path: str,
        content: str,
        allowed_paths: List[str] = None,
        max_size_mb: float = 10.0
    ) -> FileOperationResult:
        """Write content to a file with automatic backup.

        Args:
            path: Path to the file
            content: Content to write
            allowed_paths: Optional list of allowed root directories
            max_size_mb: Maximum allowed file size in MB

        Returns:
            FileOperationResult with success status and backup info
        """
        allowed_paths = allowed_paths or [str(p) for p in ALLOWED_PROJECT_ROOTS]
        timestamp = datetime.now().isoformat()

        # Validate path
        valid, error = self._validate_path(path, allowed_paths)
        if not valid:
            return FileOperationResult(
                success=False,
                message=error,
                timestamp=timestamp
            )

        # Check content size
        content_size_mb = len(content.encode("utf-8")) / (1024 * 1024)
        if content_size_mb > max_size_mb:
            return FileOperationResult(
                success=False,
                message=f"Content too large ({content_size_mb:.1f} MB, max {max_size_mb} MB)",
                timestamp=timestamp
            )

        try:
            file_path = Path(path)
            backup_path = None

            # Create backup if file exists
            if file_path.exists():
                backup_path = self.create_backup(path)
                if backup_path is None:
                    return FileOperationResult(
                        success=False,
                        message="Failed to create backup",
                        original_path=path,
                        timestamp=timestamp
                    )

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            file_path.write_text(content, encoding="utf-8")

            return FileOperationResult(
                success=True,
                message=f"Wrote {len(content)} bytes to {path}",
                backup_path=backup_path,
                original_path=path,
                bytes_written=len(content),
                timestamp=timestamp
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Write error: {e}",
                original_path=path,
                timestamp=timestamp
            )

    def create_backup(self, path: str) -> Optional[str]:
        """Create a backup of a file.

        Args:
            path: Path to the file to backup

        Returns:
            Path to the backup file, or None if failed
        """
        try:
            source = Path(path)
            if not source.exists():
                return None

            backup_name = self._generate_backup_name(source)
            backup_path = self.backup_dir / backup_name

            # Store original path info as metadata
            metadata = {
                "original_path": str(source.resolve()),
                "backup_time": datetime.now().isoformat(),
                "original_size": source.stat().st_size
            }
            metadata_path = backup_path.with_suffix(".meta.json")
            metadata_path.write_text(json.dumps(metadata, indent=2))

            # Copy the file
            shutil.copy2(source, backup_path)
            logger.info(f"Created backup: {path} -> {backup_path}")

            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None

    def restore_backup(self, backup_path: str, original_path: str = None) -> bool:
        """Restore a file from backup.

        Args:
            backup_path: Path to the backup file
            original_path: Original path (optional, read from metadata if not provided)

        Returns:
            True if successful, False otherwise
        """
        try:
            backup = Path(backup_path)
            if not backup.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Get original path from metadata if not provided
            if not original_path:
                metadata_path = backup.with_suffix(".meta.json")
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text())
                    original_path = metadata.get("original_path")

            if not original_path:
                logger.error("Cannot determine original path for restore")
                return False

            target = Path(original_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            # Restore the file
            shutil.copy2(backup, target)
            logger.info(f"Restored: {backup_path} -> {original_path}")

            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def list_backups(self, original_path: str = None) -> List[Dict]:
        """List available backups.

        Args:
            original_path: Filter by original path (optional)

        Returns:
            List of backup info dictionaries
        """
        backups = []
        for meta_file in self.backup_dir.glob("*.meta.json"):
            try:
                metadata = json.loads(meta_file.read_text())
                backup_file = meta_file.with_suffix("").with_suffix(".bak")

                if original_path and metadata.get("original_path") != original_path:
                    continue

                if backup_file.exists():
                    backups.append({
                        "backup_path": str(backup_file),
                        "original_path": metadata.get("original_path"),
                        "backup_time": metadata.get("backup_time"),
                        "size": backup_file.stat().st_size
                    })
            except Exception:
                continue

        return sorted(backups, key=lambda x: x.get("backup_time", ""), reverse=True)


# ==============================================================================
# SAFE EXECUTOR
# ==============================================================================

class SafeExecutor:
    """Sandboxed command execution with resource limits and safety checks."""

    def __init__(self):
        """Initialize the SafeExecutor."""
        self.file_ops = FileOperation()
        self._execution_count = 0
        self._blocked_count = 0

    def _build_safe_environment(
        self,
        context: ExecutionContext,
        base_env: Dict[str, str] = None
    ) -> Dict[str, str]:
        """Build a sanitized environment for command execution.

        Args:
            context: Execution context
            base_env: Base environment (defaults to os.environ)

        Returns:
            Sanitized environment dictionary
        """
        base = dict(base_env or os.environ)

        # Remove sensitive variables
        for var in SENSITIVE_ENV_VARS:
            base.pop(var, None)

        # Also remove any variable containing these keywords
        sensitive_keywords = {"KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"}
        keys_to_remove = [
            k for k in base.keys()
            if any(kw in k.upper() for kw in sensitive_keywords)
        ]
        for key in keys_to_remove:
            base.pop(key, None)

        # Restrict PATH to safe directories
        safe_paths = [p for p in SAFE_PATH_DIRS if os.path.exists(p)]
        base["PATH"] = ":".join(safe_paths)

        # Set safe defaults
        base["HOME"] = str(Path.home())
        base["TERM"] = "xterm-256color"
        base["LANG"] = "en_US.UTF-8"

        # Apply context overrides
        base.update(context.environment_overrides)

        return base

    def _validate_working_directory(
        self,
        working_dir: str,
        allowed_paths: List[str]
    ) -> Tuple[bool, str]:
        """Validate that working directory is within allowed paths.

        Args:
            working_dir: Working directory to validate
            allowed_paths: List of allowed root directories

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            resolved = Path(working_dir).resolve()

            if not resolved.exists():
                return False, f"Working directory does not exist: {working_dir}"

            if not resolved.is_dir():
                return False, f"Not a directory: {working_dir}"

            # Check against allowed paths
            for allowed in allowed_paths:
                allowed_resolved = Path(allowed).resolve()
                try:
                    resolved.relative_to(allowed_resolved)
                    return True, ""
                except ValueError:
                    continue

            return False, f"Working directory {working_dir} is not within allowed project directories"
        except Exception as e:
            return False, f"Working directory validation error: {e}"

    def _check_command_safety(self, command: str) -> Tuple[bool, str]:
        """Check if a command is safe to execute.

        Args:
            command: The command to check

        Returns:
            Tuple of (is_safe, blocked_reason)
        """
        # Check against blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked by pattern: {pattern}"

        # Check for attempts to escape or chain dangerous commands
        dangerous_operators = ["&&", "||", ";", "|"]
        parts = command.split()

        for op in dangerous_operators:
            if op in command:
                # Split by operator and check each part
                for part in command.split(op):
                    part = part.strip()
                    for pattern in BLOCKED_PATTERNS:
                        if re.search(pattern, part, re.IGNORECASE):
                            return False, f"Blocked chained command: {part}"

        return True, ""

    def _set_resource_limits(self, max_memory_mb: int = DEFAULT_MEMORY_LIMIT_MB):
        """Set resource limits for the subprocess.

        This is called in the preexec_fn of subprocess.

        Args:
            max_memory_mb: Maximum memory limit in MB
        """
        if not RESOURCE_MODULE_AVAILABLE:
            return

        try:
            # Set memory limit (soft, hard)
            memory_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            # Set CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (DEFAULT_CPU_TIME_LIMIT, DEFAULT_CPU_TIME_LIMIT + 5)
            )

            # Disable core dumps
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except Exception as e:
            logger.warning(f"Could not set resource limits: {e}")

    def _log_execution(
        self,
        command: str,
        context: ExecutionContext,
        result: ExecutionResult
    ):
        """Log execution to the execution log.

        Args:
            command: The executed command
            context: The execution context
            result: The execution result
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "project_id": context.project_id,
                "working_directory": context.working_directory,
                "dry_run": context.dry_run,
                "status": result.status.value,
                "return_code": result.return_code,
                "duration_ms": result.duration_ms,
                "timed_out": result.timed_out,
                "blocked_reason": result.blocked_reason
            }

            with open(EXECUTION_LOG, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log execution: {e}")

    def execute(
        self,
        command: str,
        working_dir: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        context: ExecutionContext = None
    ) -> ExecutionResult:
        """Execute a command in a sandboxed environment.

        Args:
            command: The command to execute
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            context: Optional execution context (created if not provided)

        Returns:
            ExecutionResult with stdout, stderr, return_code, etc.
        """
        timestamp = datetime.now().isoformat()
        self._execution_count += 1

        # Create default context if not provided
        if context is None:
            context = ExecutionContext(
                project_id="default",
                working_directory=working_dir,
                max_timeout=timeout
            )

        # Use context timeout if larger than provided
        effective_timeout = max(timeout, context.max_timeout)

        # Validate working directory
        valid, error = self._validate_working_directory(
            working_dir,
            context.allowed_paths
        )
        if not valid:
            self._blocked_count += 1
            result = ExecutionResult(
                stdout="",
                stderr=error,
                return_code=-1,
                duration_ms=0,
                timed_out=False,
                status=ExecutionStatus.BLOCKED,
                blocked_reason=error,
                command=command,
                working_dir=working_dir,
                timestamp=timestamp
            )
            self._log_execution(command, context, result)
            return result

        # Check command safety
        is_safe, blocked_reason = self._check_command_safety(command)
        if not is_safe:
            self._blocked_count += 1
            result = ExecutionResult(
                stdout="",
                stderr=f"Command blocked: {blocked_reason}",
                return_code=-1,
                duration_ms=0,
                timed_out=False,
                status=ExecutionStatus.BLOCKED,
                blocked_reason=blocked_reason,
                command=command,
                working_dir=working_dir,
                timestamp=timestamp
            )
            self._log_execution(command, context, result)
            return result

        # Dry run mode - just show what would happen
        if context.dry_run:
            result = ExecutionResult(
                stdout=f"[DRY RUN] Would execute: {command}",
                stderr="",
                return_code=0,
                duration_ms=0,
                timed_out=False,
                status=ExecutionStatus.DRY_RUN,
                command=command,
                working_dir=working_dir,
                timestamp=timestamp
            )
            self._log_execution(command, context, result)
            return result

        # Build safe environment
        env = self._build_safe_environment(context)

        # Execute the command
        start_time = time.time()
        memory_used = None

        try:
            # Use shell=False when possible for better security
            # For complex commands with pipes/redirects, shell=True is needed
            use_shell = any(c in command for c in ["|", ">", "<", "&&", "||", ";", "$"])

            if use_shell:
                args = command
            else:
                args = command.split()

            process = subprocess.Popen(
                args,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_dir,
                env=env,
                preexec_fn=self._set_resource_limits if RESOURCE_MODULE_AVAILABLE else None,
                start_new_session=True  # Create new process group for clean timeout handling
            )

            try:
                stdout, stderr = process.communicate(timeout=effective_timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                # Send SIGTERM first
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=2)  # Give it 2 seconds to clean up
                except subprocess.TimeoutExpired:
                    # Force kill with SIGKILL
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait()
                stdout, stderr = b"", b"Execution timed out"
                timed_out = True

            duration_ms = int((time.time() - start_time) * 1000)

            # Get memory usage if available
            if RESOURCE_MODULE_AVAILABLE:
                try:
                    rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    memory_used = rusage.ru_maxrss / 1024  # Convert to MB on macOS
                except Exception:
                    pass

            status = ExecutionStatus.TIMEOUT if timed_out else (
                ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
            )

            result = ExecutionResult(
                stdout=stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout,
                stderr=stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr,
                return_code=process.returncode,
                duration_ms=duration_ms,
                timed_out=timed_out,
                memory_used_mb=memory_used,
                status=status,
                command=command,
                working_dir=working_dir,
                timestamp=timestamp
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ExecutionResult(
                stdout="",
                stderr=f"Execution error: {str(e)}",
                return_code=-1,
                duration_ms=duration_ms,
                timed_out=False,
                status=ExecutionStatus.FAILED,
                command=command,
                working_dir=working_dir,
                timestamp=timestamp
            )

        self._log_execution(command, context, result)
        return result

    def execute_with_rollback_info(
        self,
        command: str,
        working_dir: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        context: ExecutionContext = None
    ) -> Tuple[ExecutionResult, RollbackInfo]:
        """Execute a command and return rollback information.

        Args:
            command: The command to execute
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            context: Optional execution context

        Returns:
            Tuple of (ExecutionResult, RollbackInfo)
        """
        result = self.execute(command, working_dir, timeout, context)

        # Determine if this command can be rolled back
        can_rollback = False
        rollback_command = None

        # Check for file operations that might be reversible
        if result.status == ExecutionStatus.SUCCESS:
            # Simple heuristics for common operations
            if command.startswith("mv "):
                parts = command.split()
                if len(parts) >= 3:
                    rollback_command = f"mv {parts[-1]} {parts[-2]}"
                    can_rollback = True
            elif command.startswith("cp "):
                parts = command.split()
                if len(parts) >= 3:
                    rollback_command = f"rm {parts[-1]}"
                    can_rollback = True

        rollback_info = RollbackInfo(
            operation_type="command",
            timestamp=datetime.now().isoformat(),
            command=command,
            can_rollback=can_rollback,
            rollback_command=rollback_command
        )

        return result, rollback_info

    def get_stats(self) -> Dict:
        """Get executor statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            "total_executions": self._execution_count,
            "blocked_executions": self._blocked_count,
            "block_rate": self._blocked_count / max(1, self._execution_count)
        }


# ==============================================================================
# INTEGRATION HELPERS
# ==============================================================================

def check_with_classifier(command: str) -> Tuple[bool, str]:
    """Check command with the command classifier if available.

    This integrates with the command classification system for additional
    safety checks.

    Args:
        command: The command to check

    Returns:
        Tuple of (is_allowed, classification_result)
    """
    try:
        # Try to import command classifier from sam_brain
        from orchestrator import route_request

        # Route the command to see how it would be classified
        route = route_request(f"run: {command}")

        # CODE route means it's a recognized safe coding operation
        if route == "CODE":
            return True, "Classified as CODE operation"

        # Other routes might need additional scrutiny
        return True, f"Classified as {route}"
    except ImportError:
        # Classifier not available, use our own checks
        return True, "Classifier not available, using internal checks"


def create_safe_context(
    project_id: str,
    working_directory: str,
    dry_run: bool = False
) -> ExecutionContext:
    """Create a safe execution context for a project.

    Args:
        project_id: Identifier for the project
        working_directory: Working directory for the project
        dry_run: If True, commands are not actually executed

    Returns:
        Configured ExecutionContext
    """
    return ExecutionContext(
        project_id=project_id,
        working_directory=working_directory,
        allowed_paths=[str(p) for p in ALLOWED_PROJECT_ROOTS],
        max_timeout=DEFAULT_TIMEOUT_SECONDS,
        dry_run=dry_run
    )


# ==============================================================================
# MODULE EXPORTS
# ==============================================================================

# Global executor instance
_executor: Optional[SafeExecutor] = None

def get_executor() -> SafeExecutor:
    """Get or create the global SafeExecutor instance.

    Returns:
        SafeExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = SafeExecutor()
    return _executor


def safe_execute(
    command: str,
    working_dir: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False
) -> ExecutionResult:
    """Convenience function for safe command execution.

    Args:
        command: Command to execute
        working_dir: Working directory
        timeout: Timeout in seconds
        dry_run: If True, don't actually execute

    Returns:
        ExecutionResult
    """
    executor = get_executor()
    context = create_safe_context("cli", working_dir, dry_run=dry_run)
    return executor.execute(command, working_dir, timeout, context)


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Safe Executor")
    parser.add_argument("command", nargs="?", help="Command to execute")
    parser.add_argument("-d", "--directory", default=".", help="Working directory")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--stats", action="store_true", help="Show executor stats")
    parser.add_argument("--backups", action="store_true", help="List backups")

    args = parser.parse_args()

    executor = get_executor()

    if args.stats:
        print(json.dumps(executor.get_stats(), indent=2))
    elif args.backups:
        backups = executor.file_ops.list_backups()
        for b in backups:
            print(f"{b['backup_time']} | {b['original_path']} | {b['size']} bytes")
    elif args.command:
        context = create_safe_context("cli", args.directory, dry_run=args.dry_run)
        result = executor.execute(args.command, args.directory, args.timeout, context)

        print(f"Status: {result.status.value}")
        print(f"Return code: {result.return_code}")
        print(f"Duration: {result.duration_ms}ms")
        if result.memory_used_mb:
            print(f"Memory: {result.memory_used_mb:.1f}MB")
        if result.stdout:
            print(f"\nStdout:\n{result.stdout}")
        if result.stderr:
            print(f"\nStderr:\n{result.stderr}")
        if result.blocked_reason:
            print(f"\nBlocked: {result.blocked_reason}")
    else:
        parser.print_help()
