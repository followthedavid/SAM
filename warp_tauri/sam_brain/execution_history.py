#!/usr/bin/env python3
"""
SAM Execution History and Rollback System

Provides comprehensive rollback capabilities and execution tracking for SAM's
autonomous actions. Enables safe experimentation with the ability to restore
previous states when needed.

Features:
- Checkpoint creation with file backups
- Command execution logging
- Rollback to any checkpoint
- Execution statistics and analytics
- Automatic cleanup of old checkpoints
- Compressed backup storage

Usage:
    from execution_history import RollbackManager, ExecutionLogger

    # Create a checkpoint before changes
    manager = RollbackManager()
    checkpoint_id = manager.create_checkpoint("my-project", "Before refactoring")
    manager.add_file_backup(checkpoint_id, "/path/to/file.py")

    # Log executions
    logger = ExecutionLogger()
    logger.log_execution(approval_id="abc123", command="git commit",
                        result=result, duration_ms=150)

    # Rollback if needed
    result = manager.rollback(checkpoint_id)

Storage:
    - SQLite: ~/.sam/execution_history.db
    - Backups: ~/.sam/backups/{checkpoint_id}/
"""

import os
import sys
import json
import gzip
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    EXPIRED = "expired"


class ExecutionStatus(Enum):
    """Status of an execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExecutionResult:
    """Result of a command execution.

    Attributes:
        success: Whether the execution succeeded
        output: Standard output from the command
        error: Error output or exception message
        exit_code: Process exit code (if applicable)
        metadata: Additional execution metadata
    """
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionResult":
        """Create from dictionary."""
        return cls(
            success=data.get("success", False),
            output=data.get("output", ""),
            error=data.get("error", ""),
            exit_code=data.get("exit_code", 0),
            metadata=data.get("metadata", {})
        )


@dataclass
class CommandLog:
    """Log entry for an executed command.

    Attributes:
        command: The command that was executed
        result: Result of the execution
        timestamp: When the command was executed
        duration_ms: Execution duration in milliseconds
    """
    command: str
    result: ExecutionResult
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "command": self.command,
            "result": self.result.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandLog":
        """Create from dictionary."""
        return cls(
            command=data.get("command", ""),
            result=ExecutionResult.from_dict(data.get("result", {})),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            duration_ms=data.get("duration_ms", 0.0)
        )


@dataclass
class Checkpoint:
    """Represents a system checkpoint for rollback.

    Attributes:
        id: Unique checkpoint identifier (UUID)
        project_id: Associated project identifier
        description: Human-readable description
        created_at: When the checkpoint was created
        files_backed_up: List of file paths that were backed up
        commands_executed: List of commands executed after checkpoint
        status: Current checkpoint status
        rolled_back_at: When rollback was performed (if applicable)
    """
    id: str
    project_id: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    files_backed_up: List[str] = field(default_factory=list)
    commands_executed: List[CommandLog] = field(default_factory=list)
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    rolled_back_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "files_backed_up": self.files_backed_up,
            "commands_executed": [cmd.to_dict() for cmd in self.commands_executed],
            "status": self.status.value,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            files_backed_up=data.get("files_backed_up", []),
            commands_executed=[CommandLog.from_dict(cmd) for cmd in data.get("commands_executed", [])],
            status=CheckpointStatus(data.get("status", "active")),
            rolled_back_at=datetime.fromisoformat(data["rolled_back_at"]) if data.get("rolled_back_at") else None
        )


@dataclass
class CheckpointInfo:
    """Summary information about a checkpoint.

    Attributes:
        id: Checkpoint UUID
        project_id: Associated project
        description: Checkpoint description
        created_at: Creation timestamp
        file_count: Number of files backed up
        command_count: Number of commands executed
        status: Current status
        backup_size_bytes: Total size of backup files
    """
    id: str
    project_id: str
    description: str
    created_at: datetime
    file_count: int
    command_count: int
    status: CheckpointStatus
    backup_size_bytes: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "file_count": self.file_count,
            "command_count": self.command_count,
            "status": self.status.value,
            "backup_size_bytes": self.backup_size_bytes
        }


@dataclass
class RollbackResult:
    """Result of a rollback operation.

    Attributes:
        success: Whether rollback was fully successful
        files_restored: List of files that were restored
        errors: List of errors encountered during rollback
        partial: True if only some files could be restored
        checkpoint_id: ID of the checkpoint that was rolled back
    """
    success: bool
    files_restored: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    partial: bool = False
    checkpoint_id: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "files_restored": self.files_restored,
            "errors": self.errors,
            "partial": self.partial,
            "checkpoint_id": self.checkpoint_id
        }


@dataclass
class ExecutionStats:
    """Statistics about command executions.

    Attributes:
        total_executions: Total number of executions
        successful: Count of successful executions
        failed: Count of failed executions
        timed_out: Count of timed out executions
        rolled_back: Count of rolled back executions
        by_command_type: Execution counts by command type
        by_project: Execution counts by project
        average_duration_ms: Average execution duration
    """
    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    timed_out: int = 0
    rolled_back: int = 0
    by_command_type: Dict[str, int] = field(default_factory=dict)
    by_project: Dict[str, int] = field(default_factory=dict)
    average_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_executions": self.total_executions,
            "successful": self.successful,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "rolled_back": self.rolled_back,
            "by_command_type": self.by_command_type,
            "by_project": self.by_project,
            "average_duration_ms": self.average_duration_ms
        }


class RollbackManager:
    """Manages checkpoints and rollback operations for SAM's autonomous actions.

    Provides the ability to create save points, backup files, log commands,
    and restore to previous states when needed.

    Attributes:
        db_path: Path to SQLite database
        backup_dir: Directory for file backups

    Example:
        manager = RollbackManager()

        # Create checkpoint before risky operation
        cp_id = manager.create_checkpoint("my-project", "Before major refactor")

        # Backup files that will be modified
        manager.add_file_backup(cp_id, "/path/to/important_file.py")

        # Log commands as they execute
        manager.add_command_log(cp_id, "git commit -m 'changes'", result)

        # If something goes wrong, rollback
        result = manager.rollback(cp_id)
        if result.success:
            print("Successfully restored previous state")
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the rollback manager.

        Args:
            base_dir: Base directory for storage. Defaults to ~/.sam/
        """
        self.base_dir = base_dir or Path.home() / ".sam"
        self.db_path = self.base_dir / "execution_history.db"
        self.backup_dir = self.base_dir / "backups"

        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for database operations
        self._lock = threading.Lock()

        # Initialize database
        self._init_db()

        logger.info(f"RollbackManager initialized with base_dir={self.base_dir}")

    def _init_db(self):
        """Initialize the SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()

                # Checkpoints table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        files_backed_up TEXT,
                        commands_executed TEXT,
                        status TEXT NOT NULL DEFAULT 'active',
                        rolled_back_at TEXT
                    )
                """)

                # Index for project lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_project
                    ON checkpoints(project_id)
                """)

                # Index for status queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_status
                    ON checkpoints(status)
                """)

                conn.commit()
            finally:
                conn.close()

        logger.debug("Database schema initialized")

    def create_checkpoint(self, project_id: str, description: str) -> str:
        """Create a new checkpoint for a project.

        Args:
            project_id: Identifier for the project
            description: Human-readable description of the checkpoint

        Returns:
            The checkpoint ID (UUID string)

        Example:
            checkpoint_id = manager.create_checkpoint(
                "sam-brain",
                "Before adding new API endpoints"
            )
        """
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            id=checkpoint_id,
            project_id=project_id,
            description=description,
            created_at=datetime.now(),
            status=CheckpointStatus.ACTIVE
        )

        # Create backup directory for this checkpoint
        checkpoint_backup_dir = self.backup_dir / checkpoint_id
        checkpoint_backup_dir.mkdir(parents=True, exist_ok=True)

        # Save to database
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO checkpoints
                    (id, project_id, description, created_at, files_backed_up,
                     commands_executed, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint.id,
                    checkpoint.project_id,
                    checkpoint.description,
                    checkpoint.created_at.isoformat(),
                    json.dumps(checkpoint.files_backed_up),
                    json.dumps([]),
                    checkpoint.status.value
                ))
                conn.commit()
            finally:
                conn.close()

        logger.info(f"Created checkpoint {checkpoint_id} for project {project_id}")
        return checkpoint_id

    def add_file_backup(self, checkpoint_id: str, file_path: str) -> bool:
        """Backup a file to the checkpoint.

        Creates a gzip-compressed copy of the file in the checkpoint's
        backup directory. The original path is preserved for restoration.

        Args:
            checkpoint_id: The checkpoint to add the backup to
            file_path: Path to the file to backup

        Returns:
            True if backup was successful, False otherwise

        Example:
            success = manager.add_file_backup(
                checkpoint_id,
                "/Users/david/project/main.py"
            )
        """
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        if not file_path.is_file():
            logger.warning(f"Not a file: {file_path}")
            return False

        checkpoint_backup_dir = self.backup_dir / checkpoint_id
        if not checkpoint_backup_dir.exists():
            logger.error(f"Checkpoint backup directory not found: {checkpoint_id}")
            return False

        try:
            # Create a safe filename for the backup (preserve path structure)
            # Use the full path as a base for the backup filename
            safe_name = str(file_path).replace("/", "__").replace("\\", "__")
            backup_path = checkpoint_backup_dir / f"{safe_name}.gz"

            # Compress and save the file
            with open(file_path, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Store the original path mapping
            mapping_file = checkpoint_backup_dir / "path_mapping.json"
            mapping = {}
            if mapping_file.exists():
                with open(mapping_file) as f:
                    mapping = json.load(f)

            mapping[safe_name] = str(file_path)
            with open(mapping_file, "w") as f:
                json.dump(mapping, f, indent=2)

            # Update database
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT files_backed_up FROM checkpoints WHERE id = ?",
                        (checkpoint_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        files = json.loads(row[0]) if row[0] else []
                        if str(file_path) not in files:
                            files.append(str(file_path))
                            cursor.execute(
                                "UPDATE checkpoints SET files_backed_up = ? WHERE id = ?",
                                (json.dumps(files), checkpoint_id)
                            )
                            conn.commit()
                finally:
                    conn.close()

            logger.info(f"Backed up file {file_path} to checkpoint {checkpoint_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to backup file {file_path}: {e}")
            return False

    def add_command_log(self, checkpoint_id: str, command: str,
                       result: ExecutionResult) -> bool:
        """Log a command execution to a checkpoint.

        Args:
            checkpoint_id: The checkpoint to add the log to
            command: The command that was executed
            result: The execution result

        Returns:
            True if log was added successfully

        Example:
            result = ExecutionResult(success=True, output="Changes committed")
            manager.add_command_log(checkpoint_id, "git commit -m 'update'", result)
        """
        cmd_log = CommandLog(
            command=command,
            result=result,
            timestamp=datetime.now()
        )

        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT commands_executed FROM checkpoints WHERE id = ?",
                        (checkpoint_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        commands = json.loads(row[0]) if row[0] else []
                        commands.append(cmd_log.to_dict())
                        cursor.execute(
                            "UPDATE checkpoints SET commands_executed = ? WHERE id = ?",
                            (json.dumps(commands), checkpoint_id)
                        )
                        conn.commit()
                        logger.debug(f"Logged command to checkpoint {checkpoint_id}: {command[:50]}")
                        return True
                    else:
                        logger.warning(f"Checkpoint not found: {checkpoint_id}")
                        return False
                finally:
                    conn.close()
        except Exception as e:
            logger.error(f"Failed to log command: {e}")
            return False

    def rollback(self, checkpoint_id: str) -> RollbackResult:
        """Rollback to a checkpoint, restoring all backed up files.

        This will:
        1. Restore all files that were backed up in the checkpoint
        2. Mark the checkpoint as rolled back
        3. Return a result indicating success/failure

        Args:
            checkpoint_id: The checkpoint to rollback to

        Returns:
            RollbackResult with details about the rollback

        Example:
            result = manager.rollback(checkpoint_id)
            if result.success:
                print(f"Restored {len(result.files_restored)} files")
            elif result.partial:
                print(f"Partial rollback: {result.errors}")
        """
        checkpoint_backup_dir = self.backup_dir / checkpoint_id
        result = RollbackResult(success=False, checkpoint_id=checkpoint_id)

        if not checkpoint_backup_dir.exists():
            result.errors.append(f"Checkpoint backup directory not found: {checkpoint_id}")
            logger.error(result.errors[0])
            return result

        # Load path mapping
        mapping_file = checkpoint_backup_dir / "path_mapping.json"
        if not mapping_file.exists():
            result.errors.append("No path mapping found - no files to restore")
            logger.warning(result.errors[0])
            result.success = True  # Nothing to restore is still successful
            return result

        try:
            with open(mapping_file) as f:
                mapping = json.load(f)
        except Exception as e:
            result.errors.append(f"Failed to load path mapping: {e}")
            logger.error(result.errors[0])
            return result

        # Restore each file
        for safe_name, original_path in mapping.items():
            backup_path = checkpoint_backup_dir / f"{safe_name}.gz"

            if not backup_path.exists():
                result.errors.append(f"Backup file not found: {backup_path}")
                result.partial = True
                continue

            try:
                # Decompress and restore
                with gzip.open(backup_path, "rb") as f_in:
                    original_path_obj = Path(original_path)
                    original_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    with open(original_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

                result.files_restored.append(original_path)
                logger.info(f"Restored file: {original_path}")

            except Exception as e:
                result.errors.append(f"Failed to restore {original_path}: {e}")
                result.partial = True
                logger.error(result.errors[-1])

        # Update checkpoint status
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE checkpoints
                    SET status = ?, rolled_back_at = ?
                    WHERE id = ?
                """, (
                    CheckpointStatus.ROLLED_BACK.value,
                    datetime.now().isoformat(),
                    checkpoint_id
                ))
                conn.commit()
            finally:
                conn.close()

        result.success = not result.partial or len(result.files_restored) > 0
        logger.info(f"Rollback {'completed' if result.success else 'failed'} for checkpoint {checkpoint_id}")
        return result

    def list_checkpoints(self, project_id: str, limit: int = 20) -> List[CheckpointInfo]:
        """List checkpoints for a project.

        Args:
            project_id: The project to list checkpoints for
            limit: Maximum number of checkpoints to return

        Returns:
            List of CheckpointInfo objects, most recent first

        Example:
            checkpoints = manager.list_checkpoints("sam-brain", limit=10)
            for cp in checkpoints:
                print(f"{cp.description} - {cp.file_count} files")
        """
        checkpoints = []

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, project_id, description, created_at,
                           files_backed_up, commands_executed, status
                    FROM checkpoints
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (project_id, limit))

                for row in cursor.fetchall():
                    files = json.loads(row[4]) if row[4] else []
                    commands = json.loads(row[5]) if row[5] else []

                    # Calculate backup size
                    backup_size = 0
                    checkpoint_backup_dir = self.backup_dir / row[0]
                    if checkpoint_backup_dir.exists():
                        for f in checkpoint_backup_dir.glob("*.gz"):
                            backup_size += f.stat().st_size

                    checkpoints.append(CheckpointInfo(
                        id=row[0],
                        project_id=row[1],
                        description=row[2],
                        created_at=datetime.fromisoformat(row[3]),
                        file_count=len(files),
                        command_count=len(commands),
                        status=CheckpointStatus(row[6]),
                        backup_size_bytes=backup_size
                    ))
            finally:
                conn.close()

        return checkpoints

    def get_checkpoint_details(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get full details for a specific checkpoint.

        Args:
            checkpoint_id: The checkpoint ID

        Returns:
            Checkpoint object with full details, or None if not found

        Example:
            checkpoint = manager.get_checkpoint_details(checkpoint_id)
            if checkpoint:
                for cmd in checkpoint.commands_executed:
                    print(f"Executed: {cmd.command}")
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, project_id, description, created_at,
                           files_backed_up, commands_executed, status, rolled_back_at
                    FROM checkpoints
                    WHERE id = ?
                """, (checkpoint_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return Checkpoint(
                    id=row[0],
                    project_id=row[1],
                    description=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    files_backed_up=json.loads(row[4]) if row[4] else [],
                    commands_executed=[CommandLog.from_dict(cmd) for cmd in json.loads(row[5])] if row[5] else [],
                    status=CheckpointStatus(row[6]),
                    rolled_back_at=datetime.fromisoformat(row[7]) if row[7] else None
                )
            finally:
                conn.close()

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """Remove checkpoints older than specified days.

        This will:
        1. Mark old checkpoints as EXPIRED
        2. Delete their backup files
        3. Remove the database entries

        Args:
            days: Number of days after which checkpoints are considered old

        Returns:
            Number of checkpoints cleaned up

        Example:
            removed = manager.cleanup_old_checkpoints(days=30)
            print(f"Cleaned up {removed} old checkpoints")
        """
        cutoff = datetime.now() - timedelta(days=days)
        removed_count = 0

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()

                # Find old checkpoints
                cursor.execute("""
                    SELECT id FROM checkpoints
                    WHERE created_at < ? AND status != ?
                """, (cutoff.isoformat(), CheckpointStatus.ROLLED_BACK.value))

                old_checkpoints = [row[0] for row in cursor.fetchall()]

                for checkpoint_id in old_checkpoints:
                    # Remove backup files
                    checkpoint_backup_dir = self.backup_dir / checkpoint_id
                    if checkpoint_backup_dir.exists():
                        try:
                            shutil.rmtree(checkpoint_backup_dir)
                            logger.info(f"Removed backup directory for checkpoint {checkpoint_id}")
                        except Exception as e:
                            logger.error(f"Failed to remove backup directory: {e}")
                            continue

                    # Remove from database
                    cursor.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
                    removed_count += 1

                conn.commit()
            finally:
                conn.close()

        logger.info(f"Cleaned up {removed_count} old checkpoints")
        return removed_count


class ExecutionLogger:
    """Logs and tracks all command executions for analytics and auditing.

    Provides comprehensive logging of all autonomous actions SAM takes,
    enabling analysis of success rates, common commands, and execution patterns.

    Attributes:
        db_path: Path to the SQLite database

    Example:
        logger = ExecutionLogger()

        # Log an execution
        result = ExecutionResult(success=True, output="Done")
        logger.log_execution(
            approval_id="abc123",
            command="git push origin main",
            result=result,
            duration_ms=1500
        )

        # Get statistics
        stats = logger.get_execution_stats()
        print(f"Success rate: {stats.successful / stats.total_executions * 100}%")
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the execution logger.

        Args:
            base_dir: Base directory for storage. Defaults to ~/.sam/
        """
        self.base_dir = base_dir or Path.home() / ".sam"
        self.db_path = self.base_dir / "execution_history.db"

        # Ensure directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for database operations
        self._lock = threading.Lock()

        # Initialize database
        self._init_db()

        logger.info(f"ExecutionLogger initialized with db_path={self.db_path}")

    def _init_db(self):
        """Initialize the SQLite database schema for executions."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()

                # Executions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        approval_id TEXT,
                        project_id TEXT,
                        command TEXT NOT NULL,
                        command_type TEXT,
                        status TEXT NOT NULL,
                        output TEXT,
                        error TEXT,
                        exit_code INTEGER DEFAULT 0,
                        duration_ms REAL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        metadata TEXT
                    )
                """)

                # Indexes for common queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_executions_project
                    ON executions(project_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_executions_status
                    ON executions(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_executions_created
                    ON executions(created_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_executions_approval
                    ON executions(approval_id)
                """)

                conn.commit()
            finally:
                conn.close()

        logger.debug("Execution logger database schema initialized")

    def _detect_command_type(self, command: str) -> str:
        """Detect the type of command for categorization.

        Args:
            command: The command string

        Returns:
            A command type string (e.g., 'git', 'python', 'npm')
        """
        command = command.strip().lower()

        # Common command prefixes
        type_prefixes = [
            ("git ", "git"),
            ("npm ", "npm"),
            ("yarn ", "yarn"),
            ("pip ", "pip"),
            ("python", "python"),
            ("pytest", "pytest"),
            ("docker ", "docker"),
            ("kubectl ", "kubernetes"),
            ("brew ", "homebrew"),
            ("cargo ", "cargo"),
            ("go ", "go"),
            ("make", "make"),
            ("cmake", "cmake"),
            ("rm ", "file_delete"),
            ("mv ", "file_move"),
            ("cp ", "file_copy"),
            ("mkdir", "directory"),
            ("touch", "file_create"),
            ("curl ", "http"),
            ("wget ", "http"),
            ("ssh ", "ssh"),
            ("scp ", "ssh"),
            ("rsync", "sync"),
        ]

        for prefix, cmd_type in type_prefixes:
            if command.startswith(prefix):
                return cmd_type

        return "other"

    def log_execution(self, approval_id: Optional[str], command: str,
                     result: ExecutionResult, duration_ms: float = 0,
                     project_id: Optional[str] = None) -> int:
        """Log a command execution.

        Args:
            approval_id: ID of the approval (if any) that authorized this execution
            command: The command that was executed
            result: The execution result
            duration_ms: Execution duration in milliseconds
            project_id: Associated project ID (optional)

        Returns:
            The ID of the logged execution record

        Example:
            result = ExecutionResult(success=True, output="Branch created")
            exec_id = logger.log_execution(
                approval_id="approval-123",
                command="git checkout -b feature/new",
                result=result,
                duration_ms=45.5,
                project_id="my-project"
            )
        """
        # Determine status
        if result.success:
            status = ExecutionStatus.SUCCESS.value
        elif "timeout" in result.error.lower():
            status = ExecutionStatus.TIMED_OUT.value
        else:
            status = ExecutionStatus.FAILED.value

        command_type = self._detect_command_type(command)

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO executions
                    (approval_id, project_id, command, command_type, status,
                     output, error, exit_code, duration_ms, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    approval_id,
                    project_id,
                    command,
                    command_type,
                    status,
                    result.output[:10000] if result.output else "",  # Truncate long output
                    result.error[:5000] if result.error else "",
                    result.exit_code,
                    duration_ms,
                    datetime.now().isoformat(),
                    json.dumps(result.metadata) if result.metadata else None
                ))
                conn.commit()
                exec_id = cursor.lastrowid
            finally:
                conn.close()

        logger.debug(f"Logged execution {exec_id}: {command[:50]}...")
        return exec_id

    def get_recent_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the most recent executions.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of execution records as dictionaries

        Example:
            recent = logger.get_recent_executions(limit=50)
            for exec in recent:
                print(f"{exec['command']} - {exec['status']}")
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, approval_id, project_id, command, command_type,
                           status, output, error, exit_code, duration_ms, created_at
                    FROM executions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def get_executions_by_project(self, project_id: str,
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Get executions for a specific project.

        Args:
            project_id: The project ID to filter by
            limit: Maximum number of executions to return

        Returns:
            List of execution records as dictionaries

        Example:
            project_execs = logger.get_executions_by_project("sam-brain", limit=25)
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, approval_id, project_id, command, command_type,
                           status, output, error, exit_code, duration_ms, created_at
                    FROM executions
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (project_id, limit))

                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def get_execution_stats(self) -> ExecutionStats:
        """Get comprehensive execution statistics.

        Returns:
            ExecutionStats object with aggregated statistics

        Example:
            stats = logger.get_execution_stats()
            success_rate = stats.successful / max(stats.total_executions, 1) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print(f"Most common: {max(stats.by_command_type, key=stats.by_command_type.get)}")
        """
        stats = ExecutionStats()

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()

                # Total and by status
                cursor.execute("""
                    SELECT status, COUNT(*) as cnt
                    FROM executions
                    GROUP BY status
                """)
                for row in cursor.fetchall():
                    status, count = row
                    stats.total_executions += count
                    if status == ExecutionStatus.SUCCESS.value:
                        stats.successful = count
                    elif status == ExecutionStatus.FAILED.value:
                        stats.failed = count
                    elif status == ExecutionStatus.TIMED_OUT.value:
                        stats.timed_out = count
                    elif status == ExecutionStatus.ROLLED_BACK.value:
                        stats.rolled_back = count

                # By command type
                cursor.execute("""
                    SELECT command_type, COUNT(*) as cnt
                    FROM executions
                    GROUP BY command_type
                    ORDER BY cnt DESC
                """)
                for row in cursor.fetchall():
                    stats.by_command_type[row[0] or "unknown"] = row[1]

                # By project
                cursor.execute("""
                    SELECT project_id, COUNT(*) as cnt
                    FROM executions
                    WHERE project_id IS NOT NULL
                    GROUP BY project_id
                    ORDER BY cnt DESC
                """)
                for row in cursor.fetchall():
                    stats.by_project[row[0]] = row[1]

                # Average duration
                cursor.execute("""
                    SELECT AVG(duration_ms) FROM executions
                    WHERE duration_ms > 0
                """)
                row = cursor.fetchone()
                if row and row[0]:
                    stats.average_duration_ms = row[0]

            finally:
                conn.close()

        return stats

    def export_to_json(self, start_date: datetime, end_date: datetime) -> str:
        """Export executions within a date range to JSON.

        Args:
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)

        Returns:
            JSON string containing the exported executions

        Example:
            from datetime import datetime, timedelta

            end = datetime.now()
            start = end - timedelta(days=7)

            json_data = logger.export_to_json(start, end)
            with open("executions_export.json", "w") as f:
                f.write(json_data)
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, approval_id, project_id, command, command_type,
                           status, output, error, exit_code, duration_ms,
                           created_at, metadata
                    FROM executions
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at ASC
                """, (start_date.isoformat(), end_date.isoformat()))

                executions = [dict(row) for row in cursor.fetchall()]

                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "total_count": len(executions),
                    "executions": executions
                }

                return json.dumps(export_data, indent=2)
            finally:
                conn.close()

    def mark_as_rolled_back(self, approval_id: str) -> bool:
        """Mark all executions with the given approval ID as rolled back.

        Args:
            approval_id: The approval ID to update

        Returns:
            True if any records were updated
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE executions
                    SET status = ?
                    WHERE approval_id = ?
                """, (ExecutionStatus.ROLLED_BACK.value, approval_id))
                conn.commit()
                updated = cursor.rowcount > 0
            finally:
                conn.close()

        if updated:
            logger.info(f"Marked executions as rolled back for approval {approval_id}")
        return updated


# ============ API Functions for sam_api.py integration ============

# Singleton instances
_rollback_manager: Optional[RollbackManager] = None
_execution_logger: Optional[ExecutionLogger] = None


def get_rollback_manager() -> RollbackManager:
    """Get or create the RollbackManager singleton."""
    global _rollback_manager
    if _rollback_manager is None:
        _rollback_manager = RollbackManager()
    return _rollback_manager


def get_execution_logger() -> ExecutionLogger:
    """Get or create the ExecutionLogger singleton."""
    global _execution_logger
    if _execution_logger is None:
        _execution_logger = ExecutionLogger()
    return _execution_logger


def api_execution_history(limit: int = 100, project_id: str = None) -> dict:
    """API: Get execution history.

    GET /api/execution/history?limit=100&project=my-project

    Args:
        limit: Maximum executions to return
        project_id: Filter by project (optional)

    Returns:
        dict with executions list
    """
    try:
        execution_logger = get_execution_logger()

        if project_id:
            executions = execution_logger.get_executions_by_project(project_id, limit)
        else:
            executions = execution_logger.get_recent_executions(limit)

        return {
            "success": True,
            "count": len(executions),
            "executions": executions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get execution history: {e}")
        return {"success": False, "error": str(e)}


def api_execution_stats() -> dict:
    """API: Get execution statistics.

    GET /api/execution/stats

    Returns:
        dict with comprehensive execution statistics
    """
    try:
        execution_logger = get_execution_logger()
        stats = execution_logger.get_execution_stats()

        return {
            "success": True,
            "stats": stats.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get execution stats: {e}")
        return {"success": False, "error": str(e)}


def api_execution_rollback(checkpoint_id: str) -> dict:
    """API: Rollback to a checkpoint.

    POST /api/execution/rollback/{checkpoint_id}

    Args:
        checkpoint_id: The checkpoint to rollback to

    Returns:
        dict with rollback result
    """
    try:
        rollback_manager = get_rollback_manager()
        result = rollback_manager.rollback(checkpoint_id)

        return {
            "success": result.success,
            "result": result.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        return {"success": False, "error": str(e)}


def api_execution_checkpoints(project_id: str, limit: int = 20) -> dict:
    """API: Get checkpoints for a project.

    GET /api/execution/checkpoints/{project_id}?limit=20

    Args:
        project_id: The project ID
        limit: Maximum checkpoints to return

    Returns:
        dict with checkpoints list
    """
    try:
        rollback_manager = get_rollback_manager()
        checkpoints = rollback_manager.list_checkpoints(project_id, limit)

        return {
            "success": True,
            "project_id": project_id,
            "count": len(checkpoints),
            "checkpoints": [cp.to_dict() for cp in checkpoints],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get checkpoints: {e}")
        return {"success": False, "error": str(e)}


def api_checkpoint_details(checkpoint_id: str) -> dict:
    """API: Get detailed checkpoint information.

    GET /api/execution/checkpoint/{checkpoint_id}

    Args:
        checkpoint_id: The checkpoint ID

    Returns:
        dict with checkpoint details
    """
    try:
        rollback_manager = get_rollback_manager()
        checkpoint = rollback_manager.get_checkpoint_details(checkpoint_id)

        if checkpoint:
            return {
                "success": True,
                "checkpoint": checkpoint.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"Checkpoint not found: {checkpoint_id}"
            }
    except Exception as e:
        logger.error(f"Failed to get checkpoint details: {e}")
        return {"success": False, "error": str(e)}


def api_create_checkpoint(project_id: str, description: str) -> dict:
    """API: Create a new checkpoint.

    POST /api/execution/checkpoint
    Body: {"project_id": "...", "description": "..."}

    Args:
        project_id: The project ID
        description: Checkpoint description

    Returns:
        dict with checkpoint ID
    """
    try:
        rollback_manager = get_rollback_manager()
        checkpoint_id = rollback_manager.create_checkpoint(project_id, description)

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "project_id": project_id,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        return {"success": False, "error": str(e)}


def api_cleanup_checkpoints(days: int = 7) -> dict:
    """API: Clean up old checkpoints.

    POST /api/execution/cleanup?days=7

    Args:
        days: Age threshold in days

    Returns:
        dict with cleanup result
    """
    try:
        rollback_manager = get_rollback_manager()
        removed = rollback_manager.cleanup_old_checkpoints(days)

        return {
            "success": True,
            "removed_count": removed,
            "threshold_days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to cleanup checkpoints: {e}")
        return {"success": False, "error": str(e)}


def api_export_executions(start_date: str, end_date: str) -> dict:
    """API: Export executions to JSON.

    GET /api/execution/export?start=2026-01-01&end=2026-01-31

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        dict with export data
    """
    try:
        execution_logger = get_execution_logger()

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        json_data = execution_logger.export_to_json(start, end)

        return {
            "success": True,
            "data": json.loads(json_data),
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        return {"success": False, "error": f"Invalid date format: {e}"}
    except Exception as e:
        logger.error(f"Failed to export executions: {e}")
        return {"success": False, "error": str(e)}


# ============ CLI Interface ============

def main():
    """Command-line interface for the execution history system."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAM Execution History and Rollback System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Checkpoint commands
    cp_parser = subparsers.add_parser("checkpoint", help="Checkpoint operations")
    cp_sub = cp_parser.add_subparsers(dest="cp_action")

    cp_create = cp_sub.add_parser("create", help="Create a checkpoint")
    cp_create.add_argument("project_id", help="Project ID")
    cp_create.add_argument("description", help="Checkpoint description")

    cp_list = cp_sub.add_parser("list", help="List checkpoints")
    cp_list.add_argument("project_id", help="Project ID")
    cp_list.add_argument("--limit", type=int, default=20, help="Max results")

    cp_details = cp_sub.add_parser("details", help="Get checkpoint details")
    cp_details.add_argument("checkpoint_id", help="Checkpoint ID")

    cp_rollback = cp_sub.add_parser("rollback", help="Rollback to checkpoint")
    cp_rollback.add_argument("checkpoint_id", help="Checkpoint ID")

    cp_backup = cp_sub.add_parser("backup", help="Add file to checkpoint")
    cp_backup.add_argument("checkpoint_id", help="Checkpoint ID")
    cp_backup.add_argument("file_path", help="File to backup")

    cp_cleanup = cp_sub.add_parser("cleanup", help="Clean up old checkpoints")
    cp_cleanup.add_argument("--days", type=int, default=7, help="Age threshold")

    # Execution commands
    exec_parser = subparsers.add_parser("executions", help="Execution operations")
    exec_sub = exec_parser.add_subparsers(dest="exec_action")

    exec_list = exec_sub.add_parser("list", help="List recent executions")
    exec_list.add_argument("--limit", type=int, default=20, help="Max results")
    exec_list.add_argument("--project", help="Filter by project")

    exec_stats = exec_sub.add_parser("stats", help="Show execution statistics")

    exec_export = exec_sub.add_parser("export", help="Export executions to JSON")
    exec_export.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    exec_export.add_argument("end_date", help="End date (YYYY-MM-DD)")
    exec_export.add_argument("--output", "-o", help="Output file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "checkpoint":
        manager = RollbackManager()

        if args.cp_action == "create":
            cp_id = manager.create_checkpoint(args.project_id, args.description)
            print(f"Created checkpoint: {cp_id}")

        elif args.cp_action == "list":
            checkpoints = manager.list_checkpoints(args.project_id, args.limit)
            if not checkpoints:
                print(f"No checkpoints found for project: {args.project_id}")
            else:
                print(f"\nCheckpoints for {args.project_id}:")
                print("-" * 60)
                for cp in checkpoints:
                    print(f"  {cp.id[:8]}... | {cp.description[:40]}")
                    print(f"    Created: {cp.created_at} | Files: {cp.file_count} | Status: {cp.status.value}")

        elif args.cp_action == "details":
            cp = manager.get_checkpoint_details(args.checkpoint_id)
            if cp:
                print(json.dumps(cp.to_dict(), indent=2, default=str))
            else:
                print(f"Checkpoint not found: {args.checkpoint_id}")

        elif args.cp_action == "rollback":
            result = manager.rollback(args.checkpoint_id)
            print(json.dumps(result.to_dict(), indent=2))

        elif args.cp_action == "backup":
            success = manager.add_file_backup(args.checkpoint_id, args.file_path)
            if success:
                print(f"Backed up: {args.file_path}")
            else:
                print(f"Failed to backup: {args.file_path}")

        elif args.cp_action == "cleanup":
            removed = manager.cleanup_old_checkpoints(args.days)
            print(f"Removed {removed} old checkpoints")

    elif args.command == "executions":
        execution_logger = ExecutionLogger()

        if args.exec_action == "list":
            if args.project:
                executions = execution_logger.get_executions_by_project(args.project, args.limit)
            else:
                executions = execution_logger.get_recent_executions(args.limit)

            print(f"\nRecent Executions ({len(executions)} results):")
            print("-" * 70)
            for ex in executions:
                cmd = ex['command'][:50] + "..." if len(ex['command']) > 50 else ex['command']
                print(f"  [{ex['status']}] {cmd}")
                print(f"    Time: {ex['created_at']} | Duration: {ex['duration_ms']:.1f}ms")

        elif args.exec_action == "stats":
            stats = execution_logger.get_execution_stats()
            print("\nExecution Statistics:")
            print("-" * 40)
            print(f"  Total: {stats.total_executions}")
            print(f"  Successful: {stats.successful}")
            print(f"  Failed: {stats.failed}")
            print(f"  Timed Out: {stats.timed_out}")
            print(f"  Rolled Back: {stats.rolled_back}")
            print(f"  Avg Duration: {stats.average_duration_ms:.1f}ms")
            if stats.by_command_type:
                print("\n  By Command Type:")
                for cmd_type, count in sorted(stats.by_command_type.items(),
                                               key=lambda x: -x[1])[:10]:
                    print(f"    {cmd_type}: {count}")

        elif args.exec_action == "export":
            start = datetime.fromisoformat(args.start_date)
            end = datetime.fromisoformat(args.end_date)
            json_data = execution_logger.export_to_json(start, end)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(json_data)
                print(f"Exported to: {args.output}")
            else:
                print(json_data)


if __name__ == "__main__":
    main()
