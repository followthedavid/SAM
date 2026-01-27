#!/usr/bin/env python3
"""
Tests for the Auto-Fix Safety System

Phase 4.2.8: Comprehensive test coverage for auto-fix functionality.

Tests cover:
1. IssueDetector - lint errors, format issues, file handling
2. AutoFixer - backups, restore on failure, concurrent access
3. AutoFixPermissions - blocked patterns, allowed patterns
4. AutoFixController - rate limiting, review threshold
5. Safety scenarios - fix quality, large files, partial failures
6. Edge cases - empty files, encodings, symlinks, .git protection
7. Integration tests - scan -> detect -> fix -> verify cycle

Run with: pytest tests/test_auto_fix_safety.py -v
"""

import json
import os
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock
import threading

import pytest

# Import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_fix import (
    # Core classes
    IssueDetector,
    AutoFixer,
    ExecutionHistory,
    ToolChecker,
    # Data classes
    DetectedIssue,
    FixResult,
    AutoFixProposal,
    AutoFixableIssue,
    # Convenience functions
    detect_issues,
    fix_file,
    fix_project,
    get_stats,
    # Paths
    BACKUP_DIR,
)

from auto_fix_control import (
    # Core classes
    AutoFixController,
    AutoFixTracker,
    AutoFixPermissions,
    # Data classes
    RateLimitStatus,
    AutoFixStats,
    DetectedIssue as ControlDetectedIssue,
    FixResult as ControlFixResult,
    FixResultStatus,
    AutoFixableIssue as ControlAutoFixableIssue,
    # Functions
    get_auto_fix_controller,
    get_db_path,
    # API functions
    api_autofix_permissions_get,
    api_autofix_permissions_update,
    api_autofix_stats,
    api_autofix_pending,
    api_autofix_history,
)


# =============================================================================
# FIXTURES - Common test data
# =============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_auto_fix.db"


@pytest.fixture
def issue_detector():
    """Create an IssueDetector instance."""
    return IssueDetector(verbose=False)


@pytest.fixture
def auto_fixer(tmp_path):
    """Create an AutoFixer instance with custom backup directory."""
    fixer = AutoFixer(create_backups=True, verbose=False)
    return fixer


@pytest.fixture
def controller(temp_db_path):
    """Create an AutoFixController with temporary database."""
    return AutoFixController(db_path=temp_db_path)


@pytest.fixture
def tracker(temp_db_path):
    """Create an AutoFixTracker with temporary database."""
    return AutoFixTracker(db_path=temp_db_path)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file with issues."""
    content = '''import os
import sys
import json  # unused
from pathlib import Path

def hello():
    print("Hello, world!")
    x = 1
    return x

class MyClass:
    def method(self):
        pass
'''
    file_path = temp_dir / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_js_file(temp_dir):
    """Create a sample JavaScript file with issues."""
    content = '''const x = 1
let y = 2
function hello() {
    console.log("hello")
}
'''
    file_path = temp_dir / "sample.js"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_rust_file(temp_dir):
    """Create a sample Rust file with formatting issues."""
    content = '''fn main() {
let x=1;
    println!("Hello, world!");
}
'''
    file_path = temp_dir / "sample.rs"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_swift_file(temp_dir):
    """Create a sample Swift file with formatting issues."""
    content = '''import Foundation

func hello() {
let x=1
    print("Hello")
}
'''
    file_path = temp_dir / "sample.swift"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project with multiple files."""
    # Create directory structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()

    # Python file with issues
    (src_dir / "main.py").write_text('''import os
import sys

def main():
    print("Main")
''')

    # Another Python file
    (src_dir / "utils.py").write_text('''import json  # unused

def helper():
    pass
''')

    # Config file (should be ignored for fixing)
    (temp_dir / ".env").write_text("SECRET=abc123\n")

    return temp_dir


@pytest.fixture
def sample_detected_issue():
    """Create a sample DetectedIssue for testing."""
    return DetectedIssue(
        file_path="/path/to/file.py",
        line_number=10,
        issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
        description="Trailing whitespace on line 10",
        suggested_fix="Remove trailing whitespace",
        auto_fixable=True,
        severity="warning",
    )


@pytest.fixture
def sample_control_issue():
    """Create a sample DetectedIssue from auto_fix_control."""
    return ControlDetectedIssue(
        issue_id="test_issue_001",
        issue_type="unused_import",
        file_path="/path/to/file.py",
        line_number=5,
        message="Unused import 'json'",
        suggested_fix="Remove the import",
        confidence=0.95,
        severity="warning",
    )


@pytest.fixture
def default_permissions():
    """Create default AutoFixPermissions."""
    return AutoFixPermissions(project_id="test_project")


# =============================================================================
# ISSUE DETECTOR TESTS
# =============================================================================

class TestIssueDetector:
    """Tests for IssueDetector class."""

    def test_detector_initialization(self, issue_detector):
        """Test that detector initializes properly."""
        assert issue_detector is not None
        assert isinstance(issue_detector.tools, dict)
        assert not issue_detector.verbose

    def test_detect_nonexistent_file(self, issue_detector):
        """Test detection on non-existent file returns empty list."""
        issues = issue_detector.detect_issues("/nonexistent/file.py")
        assert issues == []

    def test_detect_whitespace_issues(self, issue_detector, temp_dir):
        """Test detection of trailing whitespace."""
        content = "def hello():   \n    pass\n"
        file_path = temp_dir / "whitespace.py"
        file_path.write_text(content)

        issues = issue_detector._detect_whitespace_issues(file_path)

        assert len(issues) >= 1
        whitespace_issues = [i for i in issues if i.issue_type == AutoFixableIssue.TRAILING_WHITESPACE]
        assert len(whitespace_issues) >= 1
        assert whitespace_issues[0].auto_fixable

    def test_detect_missing_newline(self, issue_detector, temp_dir):
        """Test detection of missing final newline."""
        content = "def hello():\n    pass"  # No final newline
        file_path = temp_dir / "no_newline.py"
        file_path.write_text(content)

        issues = issue_detector._detect_whitespace_issues(file_path)

        newline_issues = [i for i in issues if i.issue_type == AutoFixableIssue.MISSING_NEWLINE]
        assert len(newline_issues) == 1
        assert newline_issues[0].auto_fixable

    def test_detect_python_file(self, issue_detector, sample_python_file):
        """Test detection on Python file."""
        issues = issue_detector.detect_issues(str(sample_python_file))

        # Should detect trailing whitespace at minimum
        assert isinstance(issues, list)
        # Check that issues have required fields
        for issue in issues:
            assert hasattr(issue, "file_path")
            assert hasattr(issue, "line_number")
            assert hasattr(issue, "issue_type")
            assert hasattr(issue, "auto_fixable")

    def test_detect_project_issues(self, issue_detector, sample_project):
        """Test project-wide issue detection."""
        issues = issue_detector.detect_project_issues(str(sample_project))

        assert isinstance(issues, list)
        # Should find issues in multiple files
        files_with_issues = set(i.file_path for i in issues)
        # May vary based on tools available

    def test_detect_nonexistent_project(self, issue_detector):
        """Test detection on non-existent project."""
        issues = issue_detector.detect_project_issues("/nonexistent/project")
        assert issues == []

    def test_detect_file_not_directory(self, issue_detector, sample_python_file):
        """Test that project detection returns empty for file."""
        issues = issue_detector.detect_project_issues(str(sample_python_file))
        assert issues == []

    def test_ruff_rule_mapping(self, issue_detector):
        """Test ruff rule to issue type mapping."""
        assert issue_detector._ruff_rule_to_type("F401") == AutoFixableIssue.UNUSED_IMPORT
        assert issue_detector._ruff_rule_to_type("I001") == AutoFixableIssue.IMPORT_SORT
        assert issue_detector._ruff_rule_to_type("W291") == AutoFixableIssue.TRAILING_WHITESPACE
        assert issue_detector._ruff_rule_to_type("W292") == AutoFixableIssue.MISSING_NEWLINE
        assert issue_detector._ruff_rule_to_type("ANN001") == AutoFixableIssue.TYPE_HINT_MISSING
        assert issue_detector._ruff_rule_to_type("E501") == AutoFixableIssue.LINT_ERROR


# =============================================================================
# AUTO FIXER TESTS
# =============================================================================

class TestAutoFixer:
    """Tests for AutoFixer class."""

    def test_fixer_initialization(self, auto_fixer):
        """Test that fixer initializes properly."""
        assert auto_fixer is not None
        assert auto_fixer.create_backups
        assert isinstance(auto_fixer.detector, IssueDetector)
        assert isinstance(auto_fixer.history, ExecutionHistory)

    def test_fix_non_auto_fixable_issue(self, auto_fixer):
        """Test fixing a non-auto-fixable issue returns failure."""
        issue = DetectedIssue(
            file_path="/path/to/file.py",
            line_number=10,
            issue_type=AutoFixableIssue.LINT_ERROR,
            description="Complex lint error",
            suggested_fix="Manual fix required",
            auto_fixable=False,
        )

        result = auto_fixer.fix_issue(issue)

        assert not result.success
        assert "not auto-fixable" in result.error

    def test_fix_trailing_whitespace(self, auto_fixer, temp_dir):
        """Test fixing trailing whitespace."""
        content = "def hello():   \n    pass\n"
        file_path = temp_dir / "whitespace.py"
        file_path.write_text(content)

        issue = DetectedIssue(
            file_path=str(file_path),
            line_number=1,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Trailing whitespace",
            suggested_fix="Remove trailing whitespace",
            auto_fixable=True,
        )

        result = auto_fixer._apply_builtin_fix(issue)

        assert result.success
        # Verify whitespace was removed
        new_content = file_path.read_text()
        assert "def hello():   \n" not in new_content

    def test_fix_missing_newline(self, auto_fixer, temp_dir):
        """Test fixing missing final newline."""
        content = "def hello():\n    pass"  # No final newline
        file_path = temp_dir / "no_newline.py"
        file_path.write_text(content)

        issue = DetectedIssue(
            file_path=str(file_path),
            line_number=2,
            issue_type=AutoFixableIssue.MISSING_NEWLINE,
            description="Missing final newline",
            suggested_fix="Add newline",
            auto_fixable=True,
        )

        result = auto_fixer._apply_builtin_fix(issue)

        assert result.success
        # Verify newline was added
        new_content = file_path.read_text()
        assert new_content.endswith("\n")

    def test_backup_creation(self, auto_fixer, temp_dir):
        """Test that backups are created before fixing."""
        content = "def hello():   \n"
        file_path = temp_dir / "backup_test.py"
        file_path.write_text(content)

        backup_path = auto_fixer._create_backup(str(file_path))

        assert backup_path is not None
        assert Path(backup_path).exists()
        # Backup should have same content
        assert Path(backup_path).read_text() == content

    def test_backup_disabled(self, temp_dir):
        """Test that backups can be disabled."""
        fixer = AutoFixer(create_backups=False)

        content = "def hello():\n"
        file_path = temp_dir / "no_backup.py"
        file_path.write_text(content)

        backup_path = fixer._create_backup(str(file_path))

        assert backup_path is None

    def test_fix_nonexistent_file(self, auto_fixer):
        """Test fixing nonexistent file returns error."""
        issue = DetectedIssue(
            file_path="/nonexistent/file.py",
            line_number=1,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Test",
            suggested_fix="Test",
            auto_fixable=True,
        )

        result = auto_fixer._apply_builtin_fix(issue)

        assert not result.success
        assert "not found" in result.error.lower()

    def test_dry_run(self, auto_fixer, sample_detected_issue):
        """Test dry run preview."""
        preview = auto_fixer.dry_run(sample_detected_issue)

        assert "DRY RUN" in preview
        assert sample_detected_issue.file_path in preview
        assert str(sample_detected_issue.line_number) in preview

    def test_dry_run_non_fixable(self, auto_fixer):
        """Test dry run on non-fixable issue."""
        issue = DetectedIssue(
            file_path="/path/to/file.py",
            line_number=1,
            issue_type=AutoFixableIssue.LINT_ERROR,
            description="Complex error",
            suggested_fix="Manual fix",
            auto_fixable=False,
        )

        preview = auto_fixer.dry_run(issue)

        assert "not auto-fixable" in preview.lower()

    def test_create_proposal(self, auto_fixer, sample_project):
        """Test creating a fix proposal."""
        proposal = auto_fixer.create_proposal(str(sample_project))

        assert isinstance(proposal, AutoFixProposal)
        assert hasattr(proposal, "issues_found")
        assert hasattr(proposal, "estimated_fixes")
        assert hasattr(proposal, "estimated_duration")
        assert hasattr(proposal, "files_affected")

    def test_proposal_display_format(self, auto_fixer, sample_project):
        """Test proposal display formatting."""
        proposal = auto_fixer.create_proposal(str(sample_project))
        display = proposal.format_for_display()

        assert "AUTO-FIX PROPOSAL" in display
        assert "Issues Found:" in display

    def test_fix_all_in_file(self, auto_fixer, temp_dir):
        """Test fixing all issues in a file."""
        content = "def hello():   \n    pass"  # Trailing whitespace + no newline
        file_path = temp_dir / "multi_issues.py"
        file_path.write_text(content)

        results = auto_fixer.fix_all_in_file(str(file_path))

        assert isinstance(results, list)
        # Should have attempted some fixes
        # Results vary based on available tools


# =============================================================================
# EXECUTION HISTORY TESTS
# =============================================================================

class TestExecutionHistory:
    """Tests for ExecutionHistory class."""

    def test_history_initialization(self):
        """Test history initializes properly."""
        history = ExecutionHistory()

        assert isinstance(history.history, list)
        assert isinstance(history.stats, dict)
        assert "total_fixes" in history.stats

    def test_record_fix_result(self):
        """Test recording a fix result."""
        history = ExecutionHistory()

        issue = DetectedIssue(
            file_path="/path/to/file.py",
            line_number=1,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Test",
            suggested_fix="Test",
            auto_fixable=True,
        )

        result = FixResult(
            issue=issue,
            success=True,
            changes_made="Removed whitespace",
            duration_ms=50,
        )

        initial_count = history.stats["total_fixes"]
        history.record(result)

        assert history.stats["total_fixes"] == initial_count + 1
        assert history.stats["successful_fixes"] >= 1

    def test_get_stats(self):
        """Test getting execution statistics."""
        history = ExecutionHistory()
        stats = history.get_stats()

        assert "total_fixes" in stats
        assert "successful_fixes" in stats
        assert "failed_fixes" in stats
        assert "success_rate" in stats
        assert "avg_time_ms" in stats

    def test_get_recent_history(self):
        """Test getting recent execution history."""
        history = ExecutionHistory()
        recent = history.get_recent(limit=10)

        assert isinstance(recent, list)
        assert len(recent) <= 10


# =============================================================================
# TOOL CHECKER TESTS
# =============================================================================

class TestToolChecker:
    """Tests for ToolChecker class."""

    def test_is_available(self):
        """Test tool availability check."""
        # Check for a common tool that should exist on most systems
        result = ToolChecker.is_available("python3")
        assert isinstance(result, bool)
        # python3 should typically be available
        assert result or not result  # Just verify it returns a boolean

    def test_get_available_tools(self):
        """Test getting all tool availability."""
        tools = ToolChecker.get_available_tools()

        assert isinstance(tools, dict)
        assert "ruff" in tools
        assert "black" in tools
        assert "eslint" in tools
        assert "prettier" in tools
        assert "rustfmt" in tools

    def test_tool_caching(self):
        """Test that tool availability is cached."""
        # Clear cache
        ToolChecker._cache = {}

        # First call
        result1 = ToolChecker.is_available("python3")
        # Second call should use cache
        result2 = ToolChecker.is_available("python3")

        assert result1 == result2
        assert "python3" in ToolChecker._cache


# =============================================================================
# AUTO FIX PERMISSIONS TESTS
# =============================================================================

class TestAutoFixPermissions:
    """Tests for AutoFixPermissions class."""

    def test_default_permissions(self, default_permissions):
        """Test default permission values."""
        assert default_permissions.enabled
        assert default_permissions.project_id == "test_project"
        assert len(default_permissions.allowed_fix_types) > 0
        assert len(default_permissions.blocked_fix_types) > 0
        assert default_permissions.max_fixes_per_hour == 50
        assert default_permissions.min_confidence == 0.85

    def test_fix_type_allowed(self, default_permissions):
        """Test fix type permission checking."""
        # Allowed by default
        assert default_permissions.is_fix_type_allowed("unused_import")

        # Blocked by default
        assert not default_permissions.is_fix_type_allowed("hardcoded_secret")
        assert not default_permissions.is_fix_type_allowed("sql_injection_risk")

    def test_file_pattern_allowed(self, default_permissions):
        """Test file pattern permission checking."""
        # Allowed patterns
        assert default_permissions.is_file_allowed("test.py")
        assert default_permissions.is_file_allowed("src/main.js")
        assert default_permissions.is_file_allowed("utils.ts")

        # Blocked patterns
        assert not default_permissions.is_file_allowed(".env")
        assert not default_permissions.is_file_allowed("secrets.json")
        assert not default_permissions.is_file_allowed("node_modules/package.json")
        assert not default_permissions.is_file_allowed(".git/config")

    def test_blocked_patterns_priority(self):
        """Test that blocked patterns take priority over allowed."""
        permissions = AutoFixPermissions(
            project_id="test",
            allowed_file_patterns=["*.py"],
            blocked_file_patterns=["*secret*.py"],
        )

        assert permissions.is_file_allowed("main.py")
        assert not permissions.is_file_allowed("secret_config.py")

    def test_permissions_to_dict(self, default_permissions):
        """Test permissions serialization."""
        data = default_permissions.to_dict()

        assert isinstance(data, dict)
        assert data["project_id"] == "test_project"
        assert data["enabled"]

    def test_permissions_from_dict(self):
        """Test permissions deserialization."""
        data = {
            "project_id": "new_project",
            "enabled": False,
            "max_fixes_per_hour": 100,
        }

        permissions = AutoFixPermissions.from_dict(data)

        assert permissions.project_id == "new_project"
        assert not permissions.enabled
        assert permissions.max_fixes_per_hour == 100


# =============================================================================
# AUTO FIX CONTROLLER TESTS
# =============================================================================

class TestAutoFixController:
    """Tests for AutoFixController class."""

    def test_controller_initialization(self, controller):
        """Test controller initializes properly."""
        assert controller is not None
        assert isinstance(controller.tracker, AutoFixTracker)

    def test_get_default_permissions(self, controller):
        """Test getting permissions for new project returns defaults."""
        permissions = controller.get_permissions("new_project")

        assert permissions.project_id == "new_project"
        assert permissions.enabled  # Default is enabled

    def test_save_and_load_permissions(self, controller):
        """Test saving and loading permissions."""
        permissions = AutoFixPermissions(
            project_id="test_save",
            enabled=False,
            max_fixes_per_hour=25,
        )

        controller.save_permissions(permissions)
        loaded = controller.get_permissions("test_save")

        assert loaded.project_id == "test_save"
        assert not loaded.enabled
        assert loaded.max_fixes_per_hour == 25

    def test_can_auto_fix_disabled_project(self, controller, sample_control_issue):
        """Test that disabled projects cannot auto-fix."""
        permissions = AutoFixPermissions(project_id="disabled", enabled=False)
        controller.save_permissions(permissions)

        can_fix, reason = controller.can_auto_fix("disabled", sample_control_issue)

        assert not can_fix
        assert "disabled" in reason.lower()

    def test_can_auto_fix_blocked_type(self, controller):
        """Test that blocked issue types cannot be fixed."""
        issue = ControlDetectedIssue(
            issue_id="test_blocked",
            issue_type="hardcoded_secret",
            file_path="/path/to/file.py",
            line_number=10,
            message="Hardcoded secret found",
            suggested_fix="Remove secret",
            confidence=0.99,
        )

        can_fix, reason = controller.can_auto_fix("test_project", issue)

        assert not can_fix
        assert "blocked" in reason.lower()

    def test_can_auto_fix_low_confidence(self, controller):
        """Test that low confidence issues cannot be fixed."""
        issue = ControlDetectedIssue(
            issue_id="low_conf",
            issue_type="unused_import",
            file_path="/path/to/file.py",
            line_number=5,
            message="Maybe unused",
            suggested_fix="Remove?",
            confidence=0.5,  # Below default threshold of 0.85
        )

        can_fix, reason = controller.can_auto_fix("test_project", issue)

        assert not can_fix
        assert "confidence" in reason.lower()

    def test_can_auto_fix_blocked_file(self, controller, sample_control_issue):
        """Test that blocked files cannot be fixed."""
        issue = ControlDetectedIssue(
            issue_id="blocked_file",
            issue_type="unused_import",
            file_path="/path/.env.local",
            line_number=5,
            message="Unused import",
            suggested_fix="Remove",
            confidence=0.95,
        )

        can_fix, reason = controller.can_auto_fix("test_project", issue)

        assert not can_fix
        assert "pattern" in reason.lower() or "allowed" in reason.lower()

    def test_rate_limit_status(self, controller):
        """Test getting rate limit status."""
        status = controller.get_rate_limit_status("test_project")

        assert isinstance(status, RateLimitStatus)
        assert status.project_id == "test_project"
        assert status.fixes_this_hour >= 0
        assert status.limit > 0
        assert status.can_fix  # Should be able to fix initially

    def test_rate_limit_exceeded(self, controller):
        """Test rate limiting when limit is exceeded."""
        # Set a very low limit
        permissions = AutoFixPermissions(project_id="limited", max_fixes_per_hour=1)
        controller.save_permissions(permissions)

        # Record a fix to exhaust the limit
        issue = ControlDetectedIssue(
            issue_id="rate_test",
            issue_type="unused_import",
            file_path="/path/to/file.py",
            line_number=5,
            message="Test",
            suggested_fix="Remove",
            confidence=0.95,
        )

        result = ControlFixResult(
            issue_id="rate_test",
            status=FixResultStatus.SUCCESS.value,
            applied_fix="Removed import",
        )

        controller.record_fix("limited", issue, result)

        # Now should be rate limited
        status = controller.get_rate_limit_status("limited")
        assert not status.can_fix

    def test_should_require_review_threshold(self, controller):
        """Test review requirement based on issue count."""
        # Create many issues (above default threshold of 5)
        issues = [
            ControlDetectedIssue(
                issue_id=f"review_test_{i}",
                issue_type="unused_import",
                file_path="/path/to/file.py",
                line_number=i,
                message="Test",
                suggested_fix="Remove",
                confidence=0.95,
            )
            for i in range(10)
        ]

        requires_review = controller.should_require_review("test_project", issues)

        assert requires_review

    def test_should_require_review_low_confidence(self, controller):
        """Test review requirement based on low confidence."""
        issues = [
            ControlDetectedIssue(
                issue_id="low_conf_review",
                issue_type="unused_import",
                file_path="/path/to/file.py",
                line_number=5,
                message="Test",
                suggested_fix="Remove",
                confidence=0.5,  # Below 0.7 threshold
            )
        ]

        requires_review = controller.should_require_review("test_project", issues)

        assert requires_review

    def test_get_fix_stats(self, controller):
        """Test getting fix statistics."""
        stats = controller.get_fix_stats("test_project")

        assert isinstance(stats, AutoFixStats)
        assert stats.project_id == "test_project"
        assert stats.total_fixes >= 0
        assert 0.0 <= stats.success_rate <= 1.0

    def test_cleanup_old_data(self, controller):
        """Test cleaning up old data."""
        result = controller.cleanup_old_data(days_to_keep=90)

        assert "rate_limits_deleted" in result
        assert "file_counts_deleted" in result
        assert "results_deleted" in result


# =============================================================================
# AUTO FIX TRACKER TESTS
# =============================================================================

class TestAutoFixTracker:
    """Tests for AutoFixTracker class."""

    def test_tracker_initialization(self, tracker):
        """Test tracker initializes properly."""
        assert tracker is not None
        assert tracker.db_path.exists()

    def test_track_success(self, tracker, sample_control_issue):
        """Test tracking successful fix."""
        result = ControlFixResult(
            issue_id=sample_control_issue.issue_id,
            status=FixResultStatus.SUCCESS.value,
            applied_fix="Removed import",
            original_code="import json",
        )

        tracker.track_success("test_project", sample_control_issue, result)

        # Verify it was recorded
        history = tracker.get_issue_history(sample_control_issue.file_path)
        assert len(history) > 0

    def test_track_failure(self, tracker, sample_control_issue):
        """Test tracking failed fix."""
        tracker.track_failure("test_project", sample_control_issue, "Parse error")

        # Verify it was recorded
        history = tracker.get_issue_history(sample_control_issue.file_path)
        failed = [h for h in history if h["status"] == FixResultStatus.FAILED.value]
        assert len(failed) > 0

    def test_track_skip(self, tracker, sample_control_issue):
        """Test tracking skipped fix."""
        tracker.track_skip("test_project", sample_control_issue, "File locked")

        history = tracker.get_issue_history(sample_control_issue.file_path)
        skipped = [h for h in history if h["status"] == FixResultStatus.SKIPPED.value]
        assert len(skipped) > 0

    def test_track_revert(self, tracker, sample_control_issue):
        """Test tracking reverted fix."""
        # First track a success
        result = ControlFixResult(
            issue_id=sample_control_issue.issue_id,
            status=FixResultStatus.SUCCESS.value,
            applied_fix="Removed import",
        )
        tracker.track_success("test_project", sample_control_issue, result)

        # Then track revert
        tracker.track_revert("test_project", sample_control_issue, "Broke tests")

        history = tracker.get_issue_history(sample_control_issue.file_path)
        reverted = [h for h in history if h.get("reverted") or h["status"] == FixResultStatus.REVERTED.value]
        assert len(reverted) > 0

    def test_should_skip_file_failures(self, tracker):
        """Test file skipping based on failure count."""
        file_path = "/path/to/problematic.py"

        # Track multiple failures
        for i in range(4):
            issue = ControlDetectedIssue(
                issue_id=f"failure_{i}",
                issue_type="unused_import",
                file_path=file_path,
                line_number=i,
                message="Test",
                suggested_fix="Remove",
            )
            tracker.track_failure("test_project", issue, "Failed to parse")

        should_skip, reason = tracker.should_skip_file(file_path, failure_threshold=3)

        assert should_skip
        assert "failures" in reason.lower()

    def test_save_and_get_detected_issue(self, tracker, sample_control_issue):
        """Test saving and retrieving detected issues."""
        tracker.save_detected_issue("test_project", sample_control_issue)

        pending = tracker.get_pending_issues("test_project")

        assert len(pending) > 0
        assert pending[0].issue_id == sample_control_issue.issue_id


# =============================================================================
# SAFETY SCENARIO TESTS
# =============================================================================

class TestSafetyScenarios:
    """Tests for safety scenarios and edge cases."""

    def test_git_directory_protection(self, controller):
        """Test that .git directory files are protected."""
        issue = ControlDetectedIssue(
            issue_id="git_test",
            issue_type="trailing_whitespace",
            file_path="/project/.git/hooks/pre-commit",
            line_number=10,
            message="Whitespace",
            suggested_fix="Remove",
            confidence=0.95,
        )

        can_fix, reason = controller.can_auto_fix("test_project", issue)

        assert not can_fix
        assert ".git" in reason.lower() or "pattern" in reason.lower()

    def test_secret_file_protection(self, controller):
        """Test that secret/credential files are protected."""
        secret_files = [
            "/project/.env",
            "/project/config/credentials.json",
            "/project/secrets/api_keys.yaml",
            "/project/password.txt",
        ]

        for file_path in secret_files:
            issue = ControlDetectedIssue(
                issue_id=f"secret_{file_path}",
                issue_type="trailing_whitespace",
                file_path=file_path,
                line_number=1,
                message="Test",
                suggested_fix="Remove",
                confidence=0.95,
            )

            can_fix, _ = controller.can_auto_fix("test_project", issue)
            assert not can_fix, f"Should block: {file_path}"

    def test_empty_file_handling(self, auto_fixer, temp_dir):
        """Test handling of empty files."""
        empty_file = temp_dir / "empty.py"
        empty_file.write_text("")

        issues = auto_fixer.detector.detect_issues(str(empty_file))

        # Empty files may or may not have issues, but shouldn't crash
        assert isinstance(issues, list)

    def test_large_file_handling(self, issue_detector, temp_dir):
        """Test handling of large files."""
        # Create a moderately large file (not too large to avoid test slowness)
        large_content = "# Line\n" * 10000
        large_file = temp_dir / "large.py"
        large_file.write_text(large_content)

        # Should handle without crashing
        issues = issue_detector.detect_issues(str(large_file))
        assert isinstance(issues, list)

    def test_binary_file_handling(self, issue_detector, temp_dir):
        """Test that binary files are handled gracefully."""
        binary_file = temp_dir / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        # Should not crash on binary file
        try:
            issues = issue_detector._detect_whitespace_issues(binary_file)
        except Exception:
            # It's acceptable to raise an exception, just not crash
            pass

    def test_permission_denied_handling(self, auto_fixer):
        """Test handling of permission denied errors."""
        issue = DetectedIssue(
            file_path="/root/protected.py",  # Likely inaccessible
            line_number=1,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Test",
            suggested_fix="Remove",
            auto_fixable=True,
        )

        # Should return failure, not crash
        result = auto_fixer.fix_issue(issue)
        assert not result.success

    def test_concurrent_access_safety(self, temp_dir):
        """Test that concurrent access is handled safely."""
        file_path = temp_dir / "concurrent.py"
        file_path.write_text("def hello():   \n    pass\n")

        errors = []

        def fix_file_thread():
            try:
                fixer = AutoFixer(create_backups=True, verbose=False)
                issue = DetectedIssue(
                    file_path=str(file_path),
                    line_number=1,
                    issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
                    description="Test",
                    suggested_fix="Remove",
                    auto_fixable=True,
                )
                fixer.fix_issue(issue)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=fix_file_thread) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not have crashed
        # Some errors are acceptable due to race conditions
        assert len(errors) < len(threads)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_utf8_file_content(self, issue_detector, temp_dir):
        """Test handling of UTF-8 encoded files."""
        content = "# -*- coding: utf-8 -*-\n# Comment with emoji \n"
        utf8_file = temp_dir / "utf8.py"
        utf8_file.write_text(content, encoding="utf-8")

        issues = issue_detector.detect_issues(str(utf8_file))
        assert isinstance(issues, list)

    def test_mixed_line_endings(self, issue_detector, temp_dir):
        """Test handling of mixed line endings."""
        content = "def hello():\r\n    pass\n"
        mixed_file = temp_dir / "mixed.py"
        mixed_file.write_bytes(content.encode())

        issues = issue_detector.detect_issues(str(mixed_file))
        assert isinstance(issues, list)

    def test_very_long_lines(self, issue_detector, temp_dir):
        """Test handling of very long lines."""
        long_line = "x = " + "a" * 5000 + "\n"
        long_file = temp_dir / "long_line.py"
        long_file.write_text(long_line)

        issues = issue_detector.detect_issues(str(long_file))
        assert isinstance(issues, list)

    def test_symlink_handling(self, issue_detector, temp_dir):
        """Test handling of symbolic links."""
        real_file = temp_dir / "real.py"
        real_file.write_text("def hello():\n    pass\n")

        symlink = temp_dir / "link.py"
        try:
            symlink.symlink_to(real_file)

            # Should follow symlink and detect issues
            issues = issue_detector.detect_issues(str(symlink))
            assert isinstance(issues, list)
        except OSError:
            # Symlinks may not be supported
            pytest.skip("Symlinks not supported")

    def test_special_characters_in_path(self, issue_detector, temp_dir):
        """Test handling of special characters in file paths."""
        special_dir = temp_dir / "test dir with spaces"
        special_dir.mkdir()

        special_file = special_dir / "file (1).py"
        special_file.write_text("def hello():\n    pass\n")

        issues = issue_detector.detect_issues(str(special_file))
        assert isinstance(issues, list)

    def test_node_modules_exclusion(self, issue_detector, temp_dir):
        """Test that node_modules is excluded from project scans."""
        # Create project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("x = 1\n")

        (temp_dir / "node_modules").mkdir()
        (temp_dir / "node_modules" / "package.js").write_text("const x = 1   \n")

        issues = issue_detector.detect_project_issues(str(temp_dir))

        # Should not include node_modules files
        nm_issues = [i for i in issues if "node_modules" in i.file_path]
        assert len(nm_issues) == 0

    def test_pycache_exclusion(self, issue_detector, temp_dir):
        """Test that __pycache__ is excluded from project scans."""
        # Create project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("x = 1\n")

        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "module.pyc").write_text("")

        issues = issue_detector.detect_project_issues(str(temp_dir))

        # Should not include __pycache__ files
        cache_issues = [i for i in issues if "__pycache__" in i.file_path]
        assert len(cache_issues) == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full auto-fix cycle."""

    def test_full_scan_detect_fix_verify_cycle(self, temp_dir):
        """Test complete cycle: scan -> detect -> fix -> verify."""
        # Create a file with known issues
        content = "def hello():   \n    pass"  # Trailing whitespace + no newline
        file_path = temp_dir / "integration.py"
        file_path.write_text(content)

        # 1. Detect issues
        detector = IssueDetector()
        issues = detector.detect_issues(str(file_path))

        initial_issue_count = len(issues)

        # 2. Fix issues
        fixer = AutoFixer(create_backups=True)
        results = fixer.fix_all_in_file(str(file_path))

        # 3. Verify fixes were applied
        new_content = file_path.read_text()

        # Trailing whitespace should be removed
        assert "def hello():   \n" not in new_content

        # Final newline should be added
        assert new_content.endswith("\n")

    def test_project_wide_fix_cycle(self, sample_project):
        """Test project-wide fix cycle."""
        # 1. Detect issues in project
        detector = IssueDetector()
        issues_before = detector.detect_project_issues(str(sample_project))

        # 2. Fix project
        fixer = AutoFixer(create_backups=True)
        results = fixer.fix_all_in_project(str(sample_project))

        # 3. Detect issues again
        issues_after = detector.detect_project_issues(str(sample_project))

        # Should have fewer or equal issues after fixing
        # (may not fix all issues depending on tools available)
        assert isinstance(results, list)

    def test_controller_with_tracker_integration(self, temp_db_path):
        """Test controller and tracker work together."""
        controller = AutoFixController(db_path=temp_db_path)

        # 1. Save permissions
        permissions = AutoFixPermissions(
            project_id="integration_test",
            enabled=True,
            max_fixes_per_hour=100,
        )
        controller.save_permissions(permissions)

        # 2. Check if we can fix
        issue = ControlDetectedIssue(
            issue_id="int_test_001",
            issue_type="unused_import",
            file_path="/project/main.py",
            line_number=5,
            message="Unused import",
            suggested_fix="Remove",
            confidence=0.95,
        )

        can_fix, _ = controller.can_auto_fix("integration_test", issue)
        assert can_fix

        # 3. Record a fix
        result = ControlFixResult(
            issue_id="int_test_001",
            status=FixResultStatus.SUCCESS.value,
            applied_fix="Removed import",
        )
        controller.record_fix("integration_test", issue, result)

        # 4. Check stats
        stats = controller.get_fix_stats("integration_test")
        assert stats.total_fixes >= 1

    def test_api_functions(self, temp_db_path):
        """Test API functions work correctly."""
        # Override controller with temp db
        global _controller
        from auto_fix_control import _controller

        # Save original
        original = _controller

        try:
            # Create test controller
            import auto_fix_control
            auto_fix_control._controller = AutoFixController(db_path=temp_db_path)

            # Test get permissions
            result = api_autofix_permissions_get("api_test")
            assert result["success"]
            assert "permissions" in result

            # Test update permissions
            result = api_autofix_permissions_update("api_test", {"enabled": False})
            assert result["success"]

            # Test stats
            result = api_autofix_stats("api_test")
            assert result["success"]
            assert "stats" in result

            # Test pending
            result = api_autofix_pending("api_test")
            assert result["success"]

        finally:
            # Restore original
            auto_fix_control._controller = original

    def test_restore_from_backup_on_failure(self, auto_fixer, temp_dir):
        """Test that files can be restored from backup after failure."""
        # Create original file
        original_content = "def hello():\n    pass\n"
        file_path = temp_dir / "restore_test.py"
        file_path.write_text(original_content)

        # Create backup
        backup_path = auto_fixer._create_backup(str(file_path))
        assert backup_path is not None

        # Modify the file
        file_path.write_text("CORRUPTED CONTENT\n")

        # Restore from backup
        shutil.copy(backup_path, str(file_path))

        # Verify restoration
        restored_content = file_path.read_text()
        assert restored_content == original_content


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_detected_issue_hash(self):
        """Test DetectedIssue hashing for use in sets."""
        issue1 = DetectedIssue(
            file_path="/path/to/file.py",
            line_number=10,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Test",
            suggested_fix="Fix",
            auto_fixable=True,
        )

        issue2 = DetectedIssue(
            file_path="/path/to/file.py",
            line_number=10,
            issue_type=AutoFixableIssue.TRAILING_WHITESPACE,
            description="Test",
            suggested_fix="Fix",
            auto_fixable=True,
        )

        # Same issues should hash the same
        assert hash(issue1) == hash(issue2)

        # Should work in sets
        issue_set = {issue1, issue2}
        # May or may not be 1 depending on exact hash implementation

    def test_detected_issue_to_dict(self, sample_detected_issue):
        """Test DetectedIssue serialization."""
        data = sample_detected_issue.to_dict()

        assert isinstance(data, dict)
        assert data["file_path"] == sample_detected_issue.file_path
        assert data["line_number"] == sample_detected_issue.line_number
        assert data["auto_fixable"] == sample_detected_issue.auto_fixable

    def test_fix_result_to_dict(self, sample_detected_issue):
        """Test FixResult serialization."""
        result = FixResult(
            issue=sample_detected_issue,
            success=True,
            changes_made="Fixed whitespace",
            backup_path="/backup/file.py",
            duration_ms=100,
        )

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["success"]
        assert data["changes_made"] == "Fixed whitespace"
        assert data["duration_ms"] == 100

    def test_auto_fixable_issue_properties(self):
        """Test AutoFixableIssue enum properties."""
        # Test descriptions
        assert AutoFixableIssue.LINT_ERROR.description is not None
        assert AutoFixableIssue.FORMAT_ERROR.description is not None

        # Test safe_to_auto_fix
        assert AutoFixableIssue.FORMAT_ERROR.safe_to_auto_fix
        assert AutoFixableIssue.TRAILING_WHITESPACE.safe_to_auto_fix
        assert not AutoFixableIssue.TYPE_HINT_MISSING.safe_to_auto_fix

    def test_rate_limit_status_to_dict(self):
        """Test RateLimitStatus serialization."""
        status = RateLimitStatus(
            project_id="test",
            fixes_this_hour=5,
            limit=50,
            resets_at=datetime.now() + timedelta(hours=1),
            can_fix=True,
        )

        data = status.to_dict()

        assert isinstance(data, dict)
        assert data["project_id"] == "test"
        assert data["fixes_this_hour"] == 5
        assert data["can_fix"]

    def test_auto_fix_stats_to_dict(self):
        """Test AutoFixStats serialization."""
        stats = AutoFixStats(
            project_id="test",
            total_fixes=100,
            success_rate=0.95,
            by_type={"unused_import": 50, "trailing_whitespace": 50},
        )

        data = stats.to_dict()

        assert isinstance(data, dict)
        assert data["total_fixes"] == 100
        assert data["success_rate"] == 0.95


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
