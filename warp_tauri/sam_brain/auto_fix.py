#!/usr/bin/env python3
"""
SAM Auto-Fix System - Automatically detects and fixes simple code issues.

This module provides:
- Issue detection: Runs linters and parsers to find fixable issues
- Automatic fixing: Applies safe fixes for simple issues
- Proposal generation: Shows what would be fixed before applying
- Execution logging: Tracks all fixes with backups and history

Supported tools:
- Python: ruff, black, isort, autoflake
- JavaScript/TypeScript: eslint --fix, prettier
- Rust: rustfmt, clippy --fix
- Swift: swift-format
- General: sed for simple replacements

Usage:
  from auto_fix import AutoFixer, IssueDetector

  # Detect issues
  detector = IssueDetector()
  issues = detector.detect_issues("/path/to/file.py")

  # Fix issues
  fixer = AutoFixer()
  results = fixer.fix_all_in_file("/path/to/file.py")

  # Dry run
  preview = fixer.dry_run(issues[0])
"""

import os
import re
import sys
import json
import time
import shutil
import hashlib
import subprocess
from enum import Enum, auto
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Paths
SAM_BRAIN = Path(__file__).parent
EXECUTION_HISTORY_FILE = SAM_BRAIN / ".auto_fix_history.json"
BACKUP_DIR = SAM_BRAIN / ".auto_fix_backups"


class AutoFixableIssue(Enum):
    """Types of issues that can be automatically fixed."""

    LINT_ERROR = auto()  # ruff, eslint, etc.
    FORMAT_ERROR = auto()  # black, prettier, etc.
    TYPO = auto()  # in comments/strings
    IMPORT_SORT = auto()  # isort
    TRAILING_WHITESPACE = auto()
    MISSING_NEWLINE = auto()
    UNUSED_IMPORT = auto()
    TYPE_HINT_MISSING = auto()  # simple cases only

    @property
    def description(self) -> str:
        """Human-readable description of issue type."""
        descriptions = {
            self.LINT_ERROR: "Linting error (ruff, eslint, clippy)",
            self.FORMAT_ERROR: "Code formatting issue",
            self.TYPO: "Typo in comment or string",
            self.IMPORT_SORT: "Import ordering issue",
            self.TRAILING_WHITESPACE: "Trailing whitespace",
            self.MISSING_NEWLINE: "Missing final newline",
            self.UNUSED_IMPORT: "Unused import statement",
            self.TYPE_HINT_MISSING: "Missing type hint (simple case)",
        }
        return descriptions.get(self, "Unknown issue type")

    @property
    def safe_to_auto_fix(self) -> bool:
        """Whether this issue type is generally safe to auto-fix."""
        safe_types = {
            self.FORMAT_ERROR,
            self.IMPORT_SORT,
            self.TRAILING_WHITESPACE,
            self.MISSING_NEWLINE,
            self.UNUSED_IMPORT,
        }
        return self in safe_types


@dataclass
class DetectedIssue:
    """A detected issue that may be auto-fixable.

    Attributes:
        file_path: Absolute path to the file containing the issue.
        line_number: Line number where the issue occurs (1-indexed).
        issue_type: Type of issue from AutoFixableIssue enum.
        description: Human-readable description of the issue.
        suggested_fix: Suggested fix or corrected code.
        auto_fixable: Whether this issue can be automatically fixed.
        fix_command: Optional shell command that can fix this issue.
        rule_id: Optional rule ID from the linter (e.g., "F401" for unused import).
        column: Optional column number where the issue starts.
        severity: Issue severity (error, warning, info).
    """

    file_path: str
    line_number: int
    issue_type: AutoFixableIssue
    description: str
    suggested_fix: str
    auto_fixable: bool
    fix_command: Optional[str] = None
    rule_id: Optional[str] = None
    column: Optional[int] = None
    severity: str = "warning"

    def __hash__(self):
        return hash((self.file_path, self.line_number, self.rule_id or self.description))

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type.name,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "auto_fixable": self.auto_fixable,
            "fix_command": self.fix_command,
            "rule_id": self.rule_id,
            "column": self.column,
            "severity": self.severity,
        }


@dataclass
class FixResult:
    """Result of attempting to fix an issue.

    Attributes:
        issue: The issue that was attempted to be fixed.
        success: Whether the fix was successful.
        changes_made: Description of changes made.
        backup_path: Path to backup file if created.
        error: Error message if fix failed.
        duration_ms: Time taken to apply the fix in milliseconds.
    """

    issue: DetectedIssue
    success: bool
    changes_made: str
    backup_path: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "issue": self.issue.to_dict(),
            "success": self.success,
            "changes_made": self.changes_made,
            "backup_path": self.backup_path,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AutoFixProposal:
    """A proposal for auto-fixing issues in a project or file.

    Attributes:
        issues_found: List of detected issues.
        estimated_fixes: Number of issues that can be auto-fixed.
        estimated_duration: Estimated time to fix all issues.
        commands_to_run: List of commands that would be run.
        files_affected: List of files that would be modified.
        created_at: Timestamp when proposal was created.
    """

    issues_found: List[DetectedIssue]
    estimated_fixes: int
    estimated_duration: str
    commands_to_run: List[str]
    files_affected: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def format_for_display(self) -> str:
        """Format proposal for user display."""
        lines = [
            "=" * 60,
            "AUTO-FIX PROPOSAL",
            "=" * 60,
            "",
            f"Issues Found: {len(self.issues_found)}",
            f"Auto-Fixable: {self.estimated_fixes}",
            f"Estimated Duration: {self.estimated_duration}",
            "",
        ]

        if self.files_affected:
            lines.append("Files Affected:")
            for f in sorted(set(self.files_affected))[:20]:
                lines.append(f"  - {f}")
            if len(self.files_affected) > 20:
                lines.append(f"  ... and {len(self.files_affected) - 20} more")
            lines.append("")

        if self.commands_to_run:
            lines.append("Commands to Run:")
            for cmd in self.commands_to_run[:10]:
                lines.append(f"  $ {cmd}")
            if len(self.commands_to_run) > 10:
                lines.append(f"  ... and {len(self.commands_to_run) - 10} more")
            lines.append("")

        # Group issues by type
        by_type: Dict[AutoFixableIssue, List[DetectedIssue]] = {}
        for issue in self.issues_found:
            by_type.setdefault(issue.issue_type, []).append(issue)

        lines.append("Issues by Type:")
        for issue_type, issues in sorted(by_type.items(), key=lambda x: -len(x[1])):
            fixable = sum(1 for i in issues if i.auto_fixable)
            lines.append(f"  {issue_type.name}: {len(issues)} ({fixable} auto-fixable)")

        lines.extend(["", "=" * 60])

        return "\n".join(lines)


class ToolChecker:
    """Checks availability of external tools."""

    _cache: Dict[str, bool] = {}

    @classmethod
    def is_available(cls, tool: str) -> bool:
        """Check if a tool is available on the system."""
        if tool not in cls._cache:
            cls._cache[tool] = shutil.which(tool) is not None
        return cls._cache[tool]

    @classmethod
    def get_available_tools(cls) -> Dict[str, bool]:
        """Get availability status of all supported tools."""
        tools = [
            "ruff",
            "black",
            "isort",
            "autoflake",
            "eslint",
            "prettier",
            "rustfmt",
            "cargo",
            "swift-format",
        ]
        return {tool: cls.is_available(tool) for tool in tools}


class IssueDetector:
    """Detects fixable issues in files and projects.

    The IssueDetector runs various linters and parsers to identify issues
    that can potentially be auto-fixed. It supports multiple languages
    and tools.

    Example:
        detector = IssueDetector()
        issues = detector.detect_issues("/path/to/file.py")
        project_issues = detector.detect_project_issues("/path/to/project")
    """

    def __init__(self, verbose: bool = False):
        """Initialize the detector.

        Args:
            verbose: If True, print detailed progress information.
        """
        self.verbose = verbose
        self.tools = ToolChecker.get_available_tools()

    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[IssueDetector] {message}")

    def detect_issues(self, file_path: str) -> List[DetectedIssue]:
        """Detect issues in a single file.

        Args:
            file_path: Path to the file to check.

        Returns:
            List of detected issues in the file.
        """
        path = Path(file_path)
        if not path.exists():
            return []

        issues: List[DetectedIssue] = []
        suffix = path.suffix.lower()

        # Detect based on file type
        if suffix == ".py":
            issues.extend(self._detect_python_issues(path))
        elif suffix in (".js", ".jsx", ".ts", ".tsx"):
            issues.extend(self._detect_javascript_issues(path))
        elif suffix == ".rs":
            issues.extend(self._detect_rust_issues(path))
        elif suffix == ".swift":
            issues.extend(self._detect_swift_issues(path))

        # Always check for whitespace issues
        issues.extend(self._detect_whitespace_issues(path))

        return issues

    def detect_project_issues(self, project_path: str) -> List[DetectedIssue]:
        """Detect issues in an entire project.

        Args:
            project_path: Path to the project root.

        Returns:
            List of all detected issues in the project.
        """
        path = Path(project_path)
        if not path.exists() or not path.is_dir():
            return []

        all_issues: List[DetectedIssue] = []

        # Find all source files
        extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".swift"}
        skip_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "build",
            "dist",
        }

        files_to_check = []
        for root, dirs, files in os.walk(path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for f in files:
                if Path(f).suffix.lower() in extensions:
                    files_to_check.append(Path(root) / f)

        self._log(f"Found {len(files_to_check)} source files to check")

        # Run project-wide linters if available
        if self.tools.get("ruff") and any(f.suffix == ".py" for f in files_to_check):
            all_issues.extend(self._run_ruff_project(path))

        if self.tools.get("eslint"):
            js_files = [f for f in files_to_check if f.suffix in (".js", ".jsx", ".ts", ".tsx")]
            if js_files:
                all_issues.extend(self._run_eslint_project(path))

        # Check individual files for issues not caught by project-wide linters
        for file_path in files_to_check:
            all_issues.extend(self._detect_whitespace_issues(file_path))

        return all_issues

    def _detect_python_issues(self, path: Path) -> List[DetectedIssue]:
        """Detect Python-specific issues using ruff, black, isort."""
        issues: List[DetectedIssue] = []

        # Use ruff for linting
        if self.tools.get("ruff"):
            issues.extend(self._run_ruff(path))

        # Check black formatting
        if self.tools.get("black"):
            issues.extend(self._check_black_formatting(path))

        # Check isort
        if self.tools.get("isort"):
            issues.extend(self._check_isort(path))

        return issues

    def _run_ruff(self, path: Path) -> List[DetectedIssue]:
        """Run ruff linter and parse output."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.stdout:
                try:
                    ruff_issues = json.loads(result.stdout)
                    for item in ruff_issues:
                        # Determine issue type based on ruff rule
                        rule = item.get("code", "")
                        issue_type = self._ruff_rule_to_type(rule)

                        # Check if ruff can fix it
                        fixable = item.get("fix", {}).get("applicability", "") in (
                            "safe",
                            "unsafe",
                        )

                        issues.append(
                            DetectedIssue(
                                file_path=str(path),
                                line_number=item.get("location", {}).get("row", 1),
                                column=item.get("location", {}).get("column"),
                                issue_type=issue_type,
                                description=item.get("message", "Unknown issue"),
                                suggested_fix=item.get("fix", {}).get("message", ""),
                                auto_fixable=fixable,
                                fix_command=f"ruff check --fix {path}" if fixable else None,
                                rule_id=rule,
                                severity="error" if rule.startswith("E") else "warning",
                            )
                        )
                except json.JSONDecodeError:
                    self._log(f"Failed to parse ruff output for {path}")

        except subprocess.TimeoutExpired:
            self._log(f"Ruff timed out for {path}")
        except Exception as e:
            self._log(f"Ruff error: {e}")

        return issues

    def _run_ruff_project(self, project_path: Path) -> List[DetectedIssue]:
        """Run ruff on entire project."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(project_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.stdout:
                try:
                    ruff_issues = json.loads(result.stdout)
                    for item in ruff_issues:
                        rule = item.get("code", "")
                        issue_type = self._ruff_rule_to_type(rule)
                        fixable = item.get("fix", {}).get("applicability", "") in (
                            "safe",
                            "unsafe",
                        )

                        issues.append(
                            DetectedIssue(
                                file_path=item.get("filename", str(project_path)),
                                line_number=item.get("location", {}).get("row", 1),
                                column=item.get("location", {}).get("column"),
                                issue_type=issue_type,
                                description=item.get("message", "Unknown issue"),
                                suggested_fix=item.get("fix", {}).get("message", ""),
                                auto_fixable=fixable,
                                fix_command=f"ruff check --fix {project_path}" if fixable else None,
                                rule_id=rule,
                                severity="error" if rule.startswith("E") else "warning",
                            )
                        )
                except json.JSONDecodeError:
                    self._log("Failed to parse ruff project output")

        except Exception as e:
            self._log(f"Ruff project error: {e}")

        return issues

    def _ruff_rule_to_type(self, rule: str) -> AutoFixableIssue:
        """Map ruff rule codes to issue types."""
        if rule.startswith("F401"):
            return AutoFixableIssue.UNUSED_IMPORT
        elif rule.startswith("I"):
            return AutoFixableIssue.IMPORT_SORT
        elif rule.startswith("W291") or rule.startswith("W293"):
            return AutoFixableIssue.TRAILING_WHITESPACE
        elif rule.startswith("W292"):
            return AutoFixableIssue.MISSING_NEWLINE
        elif rule.startswith("ANN"):
            return AutoFixableIssue.TYPE_HINT_MISSING
        else:
            return AutoFixableIssue.LINT_ERROR

    def _check_black_formatting(self, path: Path) -> List[DetectedIssue]:
        """Check if file needs black formatting."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["black", "--check", "--diff", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                # File needs formatting
                issues.append(
                    DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="File needs black formatting",
                        suggested_fix="Run black to format",
                        auto_fixable=True,
                        fix_command=f"black {path}",
                        severity="warning",
                    )
                )

        except Exception as e:
            self._log(f"Black check error: {e}")

        return issues

    def _check_isort(self, path: Path) -> List[DetectedIssue]:
        """Check if imports need sorting."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                issues.append(
                    DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.IMPORT_SORT,
                        description="Imports need sorting",
                        suggested_fix="Run isort to sort imports",
                        auto_fixable=True,
                        fix_command=f"isort {path}",
                        severity="warning",
                    )
                )

        except Exception as e:
            self._log(f"isort check error: {e}")

        return issues

    def _detect_javascript_issues(self, path: Path) -> List[DetectedIssue]:
        """Detect JavaScript/TypeScript issues using eslint."""
        issues: List[DetectedIssue] = []

        if self.tools.get("eslint"):
            issues.extend(self._run_eslint(path))

        if self.tools.get("prettier"):
            issues.extend(self._check_prettier(path))

        return issues

    def _run_eslint(self, path: Path) -> List[DetectedIssue]:
        """Run eslint and parse output."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["eslint", "--format=json", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            try:
                eslint_output = json.loads(result.stdout)
                for file_result in eslint_output:
                    for msg in file_result.get("messages", []):
                        # Check if fixable
                        fixable = msg.get("fix") is not None

                        issues.append(
                            DetectedIssue(
                                file_path=str(path),
                                line_number=msg.get("line", 1),
                                column=msg.get("column"),
                                issue_type=AutoFixableIssue.LINT_ERROR,
                                description=msg.get("message", "Unknown issue"),
                                suggested_fix=msg.get("fix", {}).get("text", "") if fixable else "",
                                auto_fixable=fixable,
                                fix_command=f"eslint --fix {path}" if fixable else None,
                                rule_id=msg.get("ruleId"),
                                severity="error" if msg.get("severity") == 2 else "warning",
                            )
                        )
            except json.JSONDecodeError:
                self._log(f"Failed to parse eslint output for {path}")

        except Exception as e:
            self._log(f"eslint error: {e}")

        return issues

    def _run_eslint_project(self, project_path: Path) -> List[DetectedIssue]:
        """Run eslint on entire project."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["eslint", "--format=json", str(project_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )

            try:
                eslint_output = json.loads(result.stdout)
                for file_result in eslint_output:
                    file_path = file_result.get("filePath", str(project_path))
                    for msg in file_result.get("messages", []):
                        fixable = msg.get("fix") is not None

                        issues.append(
                            DetectedIssue(
                                file_path=file_path,
                                line_number=msg.get("line", 1),
                                column=msg.get("column"),
                                issue_type=AutoFixableIssue.LINT_ERROR,
                                description=msg.get("message", "Unknown issue"),
                                suggested_fix=msg.get("fix", {}).get("text", "") if fixable else "",
                                auto_fixable=fixable,
                                fix_command=f"eslint --fix {project_path}" if fixable else None,
                                rule_id=msg.get("ruleId"),
                                severity="error" if msg.get("severity") == 2 else "warning",
                            )
                        )
            except json.JSONDecodeError:
                self._log("Failed to parse eslint project output")

        except Exception as e:
            self._log(f"eslint project error: {e}")

        return issues

    def _check_prettier(self, path: Path) -> List[DetectedIssue]:
        """Check if file needs prettier formatting."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["prettier", "--check", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                issues.append(
                    DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="File needs prettier formatting",
                        suggested_fix="Run prettier to format",
                        auto_fixable=True,
                        fix_command=f"prettier --write {path}",
                        severity="warning",
                    )
                )

        except Exception as e:
            self._log(f"prettier check error: {e}")

        return issues

    def _detect_rust_issues(self, path: Path) -> List[DetectedIssue]:
        """Detect Rust issues using rustfmt and clippy."""
        issues: List[DetectedIssue] = []

        # Check rustfmt
        if self.tools.get("rustfmt"):
            issues.extend(self._check_rustfmt(path))

        return issues

    def _check_rustfmt(self, path: Path) -> List[DetectedIssue]:
        """Check if file needs rustfmt formatting."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["rustfmt", "--check", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                issues.append(
                    DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="File needs rustfmt formatting",
                        suggested_fix="Run rustfmt to format",
                        auto_fixable=True,
                        fix_command=f"rustfmt {path}",
                        severity="warning",
                    )
                )

        except Exception as e:
            self._log(f"rustfmt check error: {e}")

        return issues

    def _detect_swift_issues(self, path: Path) -> List[DetectedIssue]:
        """Detect Swift issues using swift-format."""
        issues: List[DetectedIssue] = []

        if self.tools.get("swift-format"):
            issues.extend(self._check_swift_format(path))

        return issues

    def _check_swift_format(self, path: Path) -> List[DetectedIssue]:
        """Check if file needs swift-format formatting."""
        issues: List[DetectedIssue] = []

        try:
            result = subprocess.run(
                ["swift-format", "lint", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 or result.stderr:
                # Parse swift-format output
                for line in (result.stderr or result.stdout).splitlines():
                    # Format: path:line:col: warning/error: message
                    match = re.match(r"[^:]+:(\d+):(\d+):\s*(warning|error):\s*(.+)", line)
                    if match:
                        issues.append(
                            DetectedIssue(
                                file_path=str(path),
                                line_number=int(match.group(1)),
                                column=int(match.group(2)),
                                issue_type=AutoFixableIssue.FORMAT_ERROR,
                                description=match.group(4),
                                suggested_fix="Run swift-format to fix",
                                auto_fixable=True,
                                fix_command=f"swift-format format -i {path}",
                                severity=match.group(3),
                            )
                        )

        except Exception as e:
            self._log(f"swift-format check error: {e}")

        return issues

    def _detect_whitespace_issues(self, path: Path) -> List[DetectedIssue]:
        """Detect whitespace issues (trailing whitespace, missing newline)."""
        issues: List[DetectedIssue] = []

        try:
            content = path.read_text()
            lines = content.splitlines(keepends=True)

            # Check trailing whitespace
            for i, line in enumerate(lines, 1):
                stripped = line.rstrip("\r\n")
                if stripped != stripped.rstrip():
                    issues.append(
                        DetectedIssue(
                            file_path=str(path),
                            line_number=i,
                            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
                            description=f"Trailing whitespace on line {i}",
                            suggested_fix="Remove trailing whitespace",
                            auto_fixable=True,
                            severity="warning",
                        )
                    )

            # Check missing final newline
            if content and not content.endswith("\n"):
                issues.append(
                    DetectedIssue(
                        file_path=str(path),
                        line_number=len(lines),
                        issue_type=AutoFixableIssue.MISSING_NEWLINE,
                        description="File does not end with newline",
                        suggested_fix="Add final newline",
                        auto_fixable=True,
                        severity="warning",
                    )
                )

        except Exception as e:
            self._log(f"Whitespace check error for {path}: {e}")

        return issues


class ExecutionHistory:
    """Tracks auto-fix execution history with persistence."""

    def __init__(self):
        """Initialize execution history."""
        self.history: List[Dict] = []
        self.stats = {
            "total_fixes": 0,
            "successful_fixes": 0,
            "failed_fixes": 0,
            "total_time_ms": 0,
        }
        self._load()

    def _load(self):
        """Load history from disk."""
        if EXECUTION_HISTORY_FILE.exists():
            try:
                data = json.loads(EXECUTION_HISTORY_FILE.read_text())
                self.history = data.get("history", [])
                self.stats = data.get("stats", self.stats)
            except Exception:
                pass

    def _save(self):
        """Save history to disk."""
        data = {"history": self.history[-1000:], "stats": self.stats}  # Keep last 1000
        EXECUTION_HISTORY_FILE.write_text(json.dumps(data, indent=2, default=str))

    def record(self, result: FixResult):
        """Record a fix result."""
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "file": result.issue.file_path,
                "issue_type": result.issue.issue_type.name,
                "success": result.success,
                "changes": result.changes_made,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "backup": result.backup_path,
            }
        )

        self.stats["total_fixes"] += 1
        if result.success:
            self.stats["successful_fixes"] += 1
        else:
            self.stats["failed_fixes"] += 1
        self.stats["total_time_ms"] += result.duration_ms

        self._save()

    def get_stats(self) -> Dict:
        """Get execution statistics."""
        success_rate = 0
        if self.stats["total_fixes"] > 0:
            success_rate = self.stats["successful_fixes"] / self.stats["total_fixes"]

        return {
            **self.stats,
            "success_rate": f"{success_rate:.1%}",
            "avg_time_ms": (
                self.stats["total_time_ms"] / self.stats["total_fixes"]
                if self.stats["total_fixes"] > 0
                else 0
            ),
        }

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent execution history."""
        return self.history[-limit:][::-1]


class AutoFixer:
    """Automatically fixes detected issues.

    The AutoFixer applies fixes for issues detected by IssueDetector.
    It creates backups before making changes and logs all operations.

    Example:
        fixer = AutoFixer()

        # Fix a single issue
        result = fixer.fix_issue(detected_issue)

        # Fix all issues in a file
        results = fixer.fix_all_in_file("/path/to/file.py")

        # Dry run to preview changes
        preview = fixer.dry_run(detected_issue)
    """

    def __init__(self, create_backups: bool = True, verbose: bool = False):
        """Initialize the AutoFixer.

        Args:
            create_backups: If True, create backups before fixing.
            verbose: If True, print detailed progress information.
        """
        self.create_backups = create_backups
        self.verbose = verbose
        self.detector = IssueDetector(verbose=verbose)
        self.history = ExecutionHistory()
        self.tools = ToolChecker.get_available_tools()

        # Ensure backup directory exists
        if self.create_backups:
            BACKUP_DIR.mkdir(exist_ok=True)

    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[AutoFixer] {message}")

    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create a backup of a file before modification.

        Args:
            file_path: Path to the file to backup.

        Returns:
            Path to the backup file, or None if backup failed.
        """
        if not self.create_backups:
            return None

        try:
            path = Path(file_path)
            if not path.exists():
                return None

            # Create unique backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_hash = hashlib.md5(path.read_bytes()).hexdigest()[:8]
            backup_name = f"{path.stem}_{timestamp}_{content_hash}{path.suffix}"
            backup_path = BACKUP_DIR / backup_name

            shutil.copy2(file_path, backup_path)
            self._log(f"Created backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            self._log(f"Failed to create backup: {e}")
            return None

    def fix_issue(self, issue: DetectedIssue) -> FixResult:
        """Fix a single detected issue.

        Args:
            issue: The issue to fix.

        Returns:
            FixResult indicating success or failure.
        """
        start_time = time.time()

        if not issue.auto_fixable:
            return FixResult(
                issue=issue,
                success=False,
                changes_made="",
                error="Issue is not auto-fixable",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Create backup
        backup_path = self._create_backup(issue.file_path)

        try:
            # Try to fix using the fix command if available
            if issue.fix_command:
                result = self._run_fix_command(issue)
            else:
                # Use built-in fixers
                result = self._apply_builtin_fix(issue)

            result.backup_path = backup_path
            result.duration_ms = int((time.time() - start_time) * 1000)

            # Record in history
            self.history.record(result)

            return result

        except Exception as e:
            result = FixResult(
                issue=issue,
                success=False,
                changes_made="",
                backup_path=backup_path,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            self.history.record(result)
            return result

    def _run_fix_command(self, issue: DetectedIssue) -> FixResult:
        """Run a shell command to fix an issue."""
        try:
            result = subprocess.run(
                issue.fix_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = result.returncode == 0
            return FixResult(
                issue=issue,
                success=success,
                changes_made=f"Ran: {issue.fix_command}",
                error=result.stderr if not success else None,
            )

        except subprocess.TimeoutExpired:
            return FixResult(
                issue=issue,
                success=False,
                changes_made="",
                error="Command timed out",
            )

    def _apply_builtin_fix(self, issue: DetectedIssue) -> FixResult:
        """Apply a built-in fix for common issues."""
        path = Path(issue.file_path)
        if not path.exists():
            return FixResult(
                issue=issue,
                success=False,
                changes_made="",
                error="File not found",
            )

        content = path.read_text()
        original_content = content
        changes = []

        if issue.issue_type == AutoFixableIssue.TRAILING_WHITESPACE:
            # Remove trailing whitespace
            lines = content.splitlines(keepends=True)
            new_lines = []
            for i, line in enumerate(lines, 1):
                stripped = line.rstrip("\r\n").rstrip() + (
                    "\n" if line.endswith("\n") else ""
                )
                if stripped != line:
                    changes.append(f"Line {i}: removed trailing whitespace")
                new_lines.append(stripped if stripped else line.rstrip() + "\n")
            content = "".join(new_lines)

        elif issue.issue_type == AutoFixableIssue.MISSING_NEWLINE:
            # Add final newline
            if not content.endswith("\n"):
                content += "\n"
                changes.append("Added final newline")

        if content != original_content:
            path.write_text(content)
            return FixResult(
                issue=issue,
                success=True,
                changes_made="; ".join(changes) if changes else "Applied fix",
            )
        else:
            return FixResult(
                issue=issue,
                success=False,
                changes_made="",
                error="No changes made",
            )

    def fix_all_in_file(self, file_path: str) -> List[FixResult]:
        """Fix all auto-fixable issues in a file.

        Args:
            file_path: Path to the file to fix.

        Returns:
            List of FixResult for each attempted fix.
        """
        results: List[FixResult] = []

        # First, try to use tool-based fixes (more efficient)
        path = Path(file_path)
        suffix = path.suffix.lower()

        # Create single backup for all fixes
        backup_path = self._create_backup(file_path)

        # Run formatters first
        if suffix == ".py":
            results.extend(self._fix_python_file(path, backup_path))
        elif suffix in (".js", ".jsx", ".ts", ".tsx"):
            results.extend(self._fix_javascript_file(path, backup_path))
        elif suffix == ".rs":
            results.extend(self._fix_rust_file(path, backup_path))
        elif suffix == ".swift":
            results.extend(self._fix_swift_file(path, backup_path))

        # Fix whitespace issues
        whitespace_issues = self.detector._detect_whitespace_issues(path)
        for issue in whitespace_issues:
            if issue.auto_fixable:
                result = self._apply_builtin_fix(issue)
                result.backup_path = backup_path
                results.append(result)
                self.history.record(result)

        return results

    def _fix_python_file(self, path: Path, backup_path: Optional[str]) -> List[FixResult]:
        """Fix all Python issues in a file."""
        results: List[FixResult] = []
        start_time = time.time()

        # Run ruff --fix
        if self.tools.get("ruff"):
            try:
                result = subprocess.run(
                    ["ruff", "check", "--fix", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.LINT_ERROR,
                        description="Ruff lint fixes",
                        suggested_fix="ruff --fix",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made=f"Ran ruff --fix",
                    backup_path=backup_path,
                    error=result.stderr if result.returncode != 0 else None,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"Ruff fix error: {e}")

        # Run isort
        if self.tools.get("isort"):
            try:
                result = subprocess.run(
                    ["isort", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.IMPORT_SORT,
                        description="Import sorting",
                        suggested_fix="isort",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran isort",
                    backup_path=backup_path,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"isort error: {e}")

        # Run black
        if self.tools.get("black"):
            try:
                result = subprocess.run(
                    ["black", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="Black formatting",
                        suggested_fix="black",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran black",
                    backup_path=backup_path,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"black error: {e}")

        return results

    def _fix_javascript_file(
        self, path: Path, backup_path: Optional[str]
    ) -> List[FixResult]:
        """Fix all JavaScript/TypeScript issues in a file."""
        results: List[FixResult] = []
        start_time = time.time()

        # Run eslint --fix
        if self.tools.get("eslint"):
            try:
                result = subprocess.run(
                    ["eslint", "--fix", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.LINT_ERROR,
                        description="ESLint fixes",
                        suggested_fix="eslint --fix",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran eslint --fix",
                    backup_path=backup_path,
                    error=result.stderr if result.returncode != 0 else None,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"eslint fix error: {e}")

        # Run prettier
        if self.tools.get("prettier"):
            try:
                result = subprocess.run(
                    ["prettier", "--write", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="Prettier formatting",
                        suggested_fix="prettier --write",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran prettier",
                    backup_path=backup_path,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"prettier error: {e}")

        return results

    def _fix_rust_file(self, path: Path, backup_path: Optional[str]) -> List[FixResult]:
        """Fix all Rust issues in a file."""
        results: List[FixResult] = []
        start_time = time.time()

        # Run rustfmt
        if self.tools.get("rustfmt"):
            try:
                result = subprocess.run(
                    ["rustfmt", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="Rustfmt formatting",
                        suggested_fix="rustfmt",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran rustfmt",
                    backup_path=backup_path,
                    error=result.stderr if result.returncode != 0 else None,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"rustfmt error: {e}")

        return results

    def _fix_swift_file(self, path: Path, backup_path: Optional[str]) -> List[FixResult]:
        """Fix all Swift issues in a file."""
        results: List[FixResult] = []
        start_time = time.time()

        # Run swift-format
        if self.tools.get("swift-format"):
            try:
                result = subprocess.run(
                    ["swift-format", "format", "-i", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.FORMAT_ERROR,
                        description="Swift format",
                        suggested_fix="swift-format",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran swift-format",
                    backup_path=backup_path,
                    error=result.stderr if result.returncode != 0 else None,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"swift-format error: {e}")

        return results

    def fix_all_in_project(self, project_path: str) -> List[FixResult]:
        """Fix all auto-fixable issues in a project.

        Args:
            project_path: Path to the project root.

        Returns:
            List of FixResult for each attempted fix.
        """
        results: List[FixResult] = []
        path = Path(project_path)

        if not path.exists() or not path.is_dir():
            return results

        self._log(f"Fixing project: {project_path}")

        # Find all source files
        extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".swift"}
        skip_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "build",
            "dist",
        }

        files_to_fix = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if Path(f).suffix.lower() in extensions:
                    files_to_fix.append(Path(root) / f)

        self._log(f"Found {len(files_to_fix)} files to check")

        # Run project-wide fixes first (more efficient)
        if self.tools.get("ruff") and any(f.suffix == ".py" for f in files_to_fix):
            self._log("Running ruff --fix on project...")
            start_time = time.time()
            try:
                result = subprocess.run(
                    ["ruff", "check", "--fix", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                fix_result = FixResult(
                    issue=DetectedIssue(
                        file_path=str(path),
                        line_number=1,
                        issue_type=AutoFixableIssue.LINT_ERROR,
                        description="Project-wide ruff fixes",
                        suggested_fix="ruff --fix",
                        auto_fixable=True,
                    ),
                    success=result.returncode == 0,
                    changes_made="Ran ruff --fix on project",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                results.append(fix_result)
                self.history.record(fix_result)
            except Exception as e:
                self._log(f"Project ruff error: {e}")

        # Fix individual files for remaining issues
        for file_path in files_to_fix:
            file_results = self.fix_all_in_file(str(file_path))
            results.extend(file_results)

        return results

    def dry_run(self, issue: DetectedIssue) -> str:
        """Preview what changes would be made without applying them.

        Args:
            issue: The issue to preview fixing.

        Returns:
            String description of what would change.
        """
        if not issue.auto_fixable:
            return f"Issue is not auto-fixable: {issue.description}"

        lines = [
            "=" * 60,
            "DRY RUN - No changes will be made",
            "=" * 60,
            "",
            f"File: {issue.file_path}",
            f"Line: {issue.line_number}",
            f"Type: {issue.issue_type.name}",
            f"Description: {issue.description}",
            "",
        ]

        if issue.fix_command:
            lines.append(f"Would run: {issue.fix_command}")
        else:
            lines.append(f"Would apply built-in fix for: {issue.issue_type.name}")

        if issue.suggested_fix:
            lines.extend(["", "Suggested fix:", issue.suggested_fix])

        # For format errors, show diff if possible
        path = Path(issue.file_path)
        if (
            issue.issue_type == AutoFixableIssue.FORMAT_ERROR
            and path.exists()
            and path.suffix == ".py"
        ):
            if self.tools.get("black"):
                try:
                    result = subprocess.run(
                        ["black", "--diff", str(path)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.stdout:
                        lines.extend(["", "Diff preview:", result.stdout[:2000]])
                        if len(result.stdout) > 2000:
                            lines.append("... (truncated)")
                except Exception:
                    pass

        lines.extend(["", "=" * 60])
        return "\n".join(lines)

    def create_proposal(
        self, path: str, include_non_fixable: bool = False
    ) -> AutoFixProposal:
        """Create a proposal for fixing issues in a file or project.

        Args:
            path: Path to file or project.
            include_non_fixable: Include non-auto-fixable issues in proposal.

        Returns:
            AutoFixProposal with details of proposed fixes.
        """
        p = Path(path)

        if p.is_file():
            issues = self.detector.detect_issues(str(p))
        elif p.is_dir():
            issues = self.detector.detect_project_issues(str(p))
        else:
            return AutoFixProposal(
                issues_found=[],
                estimated_fixes=0,
                estimated_duration="0ms",
                commands_to_run=[],
            )

        if not include_non_fixable:
            display_issues = [i for i in issues if i.auto_fixable]
        else:
            display_issues = issues

        fixable_count = sum(1 for i in issues if i.auto_fixable)

        # Collect unique commands
        commands = list(set(i.fix_command for i in issues if i.fix_command))

        # Collect affected files
        files = list(set(i.file_path for i in issues))

        # Estimate duration (rough: 100ms per issue)
        est_ms = fixable_count * 100
        if est_ms < 1000:
            est_duration = f"{est_ms}ms"
        else:
            est_duration = f"{est_ms / 1000:.1f}s"

        return AutoFixProposal(
            issues_found=display_issues,
            estimated_fixes=fixable_count,
            estimated_duration=est_duration,
            commands_to_run=commands,
            files_affected=files,
        )


# Convenience functions
def detect_issues(path: str) -> List[DetectedIssue]:
    """Detect issues in a file or project.

    Args:
        path: Path to file or project directory.

    Returns:
        List of detected issues.
    """
    detector = IssueDetector()
    p = Path(path)

    if p.is_file():
        return detector.detect_issues(path)
    elif p.is_dir():
        return detector.detect_project_issues(path)
    return []


def fix_file(path: str, create_backups: bool = True) -> List[FixResult]:
    """Fix all issues in a file.

    Args:
        path: Path to the file.
        create_backups: Whether to create backups.

    Returns:
        List of fix results.
    """
    fixer = AutoFixer(create_backups=create_backups)
    return fixer.fix_all_in_file(path)


def fix_project(path: str, create_backups: bool = True) -> List[FixResult]:
    """Fix all issues in a project.

    Args:
        path: Path to the project.
        create_backups: Whether to create backups.

    Returns:
        List of fix results.
    """
    fixer = AutoFixer(create_backups=create_backups)
    return fixer.fix_all_in_project(path)


def get_stats() -> Dict:
    """Get execution statistics.

    Returns:
        Dictionary of execution statistics.
    """
    history = ExecutionHistory()
    return history.get_stats()


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SAM Auto-Fix System - Automatically fix code issues"
    )
    parser.add_argument("command", choices=["detect", "fix", "dry-run", "stats", "tools"])
    parser.add_argument("path", nargs="?", default=".", help="File or project path")
    parser.add_argument(
        "--no-backup", action="store_true", help="Don't create backups"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.command == "tools":
        print("Available tools:")
        for tool, available in ToolChecker.get_available_tools().items():
            status = "[OK]" if available else "[NOT FOUND]"
            print(f"  {status} {tool}")
        sys.exit(0)

    if args.command == "stats":
        stats = get_stats()
        print("Auto-Fix Statistics:")
        print(f"  Total fixes attempted: {stats['total_fixes']}")
        print(f"  Successful: {stats['successful_fixes']}")
        print(f"  Failed: {stats['failed_fixes']}")
        print(f"  Success rate: {stats['success_rate']}")
        print(f"  Average time: {stats['avg_time_ms']:.0f}ms")
        sys.exit(0)

    # Resolve path
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    if args.command == "detect":
        detector = IssueDetector(verbose=args.verbose)
        if path.is_file():
            issues = detector.detect_issues(str(path))
        else:
            issues = detector.detect_project_issues(str(path))

        if not issues:
            print("No issues detected.")
        else:
            print(f"Found {len(issues)} issues:")
            for i, issue in enumerate(issues[:50], 1):
                fixable = "[FIXABLE]" if issue.auto_fixable else "[MANUAL]"
                print(f"  {i}. {fixable} {Path(issue.file_path).name}:{issue.line_number}")
                print(f"      {issue.issue_type.name}: {issue.description[:60]}")
            if len(issues) > 50:
                print(f"  ... and {len(issues) - 50} more")

    elif args.command == "dry-run":
        fixer = AutoFixer(create_backups=not args.no_backup, verbose=args.verbose)
        proposal = fixer.create_proposal(str(path))
        print(proposal.format_for_display())

    elif args.command == "fix":
        fixer = AutoFixer(create_backups=not args.no_backup, verbose=args.verbose)

        if path.is_file():
            results = fixer.fix_all_in_file(str(path))
        else:
            results = fixer.fix_all_in_project(str(path))

        success = sum(1 for r in results if r.success)
        failed = len(results) - success

        print(f"\nFix Results:")
        print(f"  Successful: {success}")
        print(f"  Failed: {failed}")

        if failed > 0:
            print("\nFailed fixes:")
            for r in results:
                if not r.success:
                    print(f"  - {Path(r.issue.file_path).name}: {r.error}")
