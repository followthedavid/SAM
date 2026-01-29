#!/usr/bin/env python3
"""
SAM Project Context System - Phase 2.1.5

Provides:
1. Project Detection - Knows which project you're working on (ProjectDetector)
2. Project Memory - Remembers per-project state (ProjectContext)
3. Context Injection - Adds project info to prompts
4. Session Continuity - "Last time you were debugging X"
5. SSOT Integration - Maps directories to known projects
6. Project Profile Loading - Reads from SSOT markdown files (Phase 2.1.2)
7. Directory Watcher - Monitors for project switches (Phase 2.1.4)
8. Session State Persistence - Per-project session tracking (Phase 2.1.5)

Usage:
    # Phase 2.1.1: Lightweight detection
    from project_context import ProjectDetector, get_current_project

    detector = ProjectDetector()
    project = detector.detect()  # from cwd
    project = detector.detect("/path/to/project")

    # Or use convenience function
    project = get_current_project()

    # Phase 2.1.2: Profile loading from SSOT markdown files
    from project_context import ProjectProfileLoader, get_profile_loader

    loader = ProjectProfileLoader()
    profile = loader.load_profile("SAM_TERMINAL")  # By name
    all_profiles = loader.get_all_profiles()       # All profiles
    context = profile.to_context_string()          # For prompt injection

    # Or use singleton
    loader = get_profile_loader()
    profile = loader.load_profile("orchestrator")

    # Phase 2.1.4: Directory watcher for project switches
    from project_context import ProjectWatcher, get_project_watcher

    watcher = ProjectWatcher(poll_interval=5.0)

    def on_change(old_project, new_project, profile):
        print(f"Switched to: {new_project.name if new_project else 'none'}")

    watcher.on_project_change(on_change)
    watcher.start()

    # Or use singleton
    watcher = get_project_watcher(auto_start=True)

    # Or use context manager
    with ProjectWatcher() as watcher:
        watcher.on_project_change(on_change)
        # ... do work ...

    # Phase 2.1.5: Per-project session state persistence
    from project_context import SessionState, ProjectSessionState, get_session_state

    session_state = get_session_state()

    # Save a session
    state = SessionState(
        project_name="SAM Brain",
        conversation_summary="Added session persistence",
        files_touched=["project_context.py"],
        todos_added=["Write tests"]
    )
    session_state.save_session("SAM Brain", state)

    # Get last session
    last = session_state.get_last_session("SAM Brain")

    # Update files touched during session
    session_state.update_files_touched("SAM Brain", ["new_file.py"])

    # Add freeform notes
    session_state.add_session_note("SAM Brain", "Remember edge cases")

    # Get session history
    history = session_state.get_session_history("SAM Brain", limit=5)

    # Legacy: Full context with persistence
    from project_context import ProjectContext
    ctx = ProjectContext()
    project = ctx.detect_project("/Users/david/ReverseLab/SAM/warp_tauri")

CLI:
    # Phase 2.1.1: Detection
    python project_context.py detect [path]
    python project_context.py detect . --json
    python project_context.py list

    # Phase 2.1.2: Profile loading
    python project_context.py profile SAM_TERMINAL
    python project_context.py profile SAM_TERMINAL --json
    python project_context.py profiles
    python project_context.py profiles --json

    # Phase 2.1.4: Directory watcher
    python project_context.py watch
    python project_context.py watch --interval 3 --verbose
"""

import os
import sys
import json
import sqlite3
import hashlib
import re
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict, field

# =============================================================================
# Phase 2.1.1: Known SSOT Projects (from PROJECT_REGISTRY.md)
# =============================================================================

SSOT_PROJECTS = {
    # Tier 1: Core Infrastructure
    "~/ReverseLab/SAM/warp_tauri": {
        "name": "SAM Terminal",
        "type": "tauri",
        "language": "rust+typescript",
        "status": "building",
        "tier": 1,
    },
    "~/ReverseLab/SAM/SAMControlCenter": {
        "name": "SAMControlCenter",
        "type": "swiftui",
        "language": "swift",
        "status": "active",
        "tier": 1,
    },
    "~/ReverseLab/SAM/warp_tauri/sam_brain": {
        "name": "SAM Brain",
        "type": "python",
        "language": "python",
        "status": "active",
        "tier": 1,
    },
    "~/ReverseLab/SAM/warp_core": {
        "name": "Warp Core",
        "type": "rust",
        "language": "rust",
        "status": "active",
        "tier": 1,
    },
    "/Volumes/Plex/SSOT": {
        "name": "SSOT System",
        "type": "documentation",
        "language": "markdown",
        "status": "active",
        "tier": 1,
    },
    # Tier 2: AI/ML Training
    "~/Projects/RVC": {
        "name": "RVC Voice Training",
        "type": "ml",
        "language": "python",
        "status": "ready",
        "tier": 2,
    },
    "~/ai-studio/ComfyUI": {
        "name": "ComfyUI/LoRA",
        "type": "ml",
        "language": "python",
        "status": "setup",
        "tier": 2,
    },
    "~/Projects/motion-pipeline": {
        "name": "Motion Pipeline",
        "type": "ml",
        "language": "python",
        "status": "idle",
        "tier": 2,
    },
    "/Volumes/Plex/DevSymlinks/topaz_parity": {
        "name": "Topaz Parity",
        "type": "reverse-engineering",
        "language": "python",
        "status": "research",
        "tier": 2,
    },
    # Tier 4: Automation
    "/Volumes/Plex/DevSymlinks/account_automation": {
        "name": "Account Automation",
        "type": "automation",
        "language": "python",
        "status": "active",
        "tier": 4,
    },
    "~/ReverseLab/warp_auto": {
        "name": "Warp Auto",
        "type": "automation",
        "language": "python",
        "status": "idle",
        "tier": 4,
    },
    "~/Projects/calcareers-automation": {
        "name": "CalCareers Automation",
        "type": "automation",
        "language": "python",
        "status": "idle",
        "tier": 4,
    },
    # Tier 5: Game/Character Dev
    "~/Projects/character-pipeline": {
        "name": "Character Pipeline",
        "type": "game-dev",
        "language": "python",
        "status": "ready",
        "tier": 5,
    },
    "~/ReverseLab/SAM/unity_project": {
        "name": "Unity Project",
        "type": "game-dev",
        "language": "csharp",
        "status": "scaffolded",
        "tier": 5,
    },
    # Tier 6: Reverse Engineering
    "~/ReverseLab": {
        "name": "ReverseLab Core",
        "type": "reverse-engineering",
        "language": "mixed",
        "status": "active",
        "tier": 6,
    },
    # Tier 7: GridPlayer / StashGrid
    "~/Projects/gridplayer": {
        "name": "GridPlayer",
        "type": "desktop-app",
        "language": "python",
        "status": "working",
        "tier": 7,
    },
    # Tier 8: Muse
    "~/Projects/muse": {
        "name": "Muse",
        "type": "app",
        "language": "swift",
        "status": "planned",
        "tier": 8,
    },
}

# Project markers and their associated languages
PROJECT_MARKERS = {
    "Cargo.toml": "rust",
    "package.json": "javascript",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "go.mod": "go",
    "Package.swift": "swift",
    "Gemfile": "ruby",
    "composer.json": "php",
    "build.gradle": "java",
    "pom.xml": "java",
    "CMakeLists.txt": "cpp",
    "Makefile": None,  # Language agnostic
    ".git": None,  # Just a marker
    "CLAUDE.md": None,  # SAM/Claude project marker
}

# Storage
DB_PATH = Path("/Volumes/David External/sam_memory/project_context.db")
INVENTORY_PATH = Path("/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/exhaustive_analysis/master_inventory.json")
SSOT_PROJECTS_PATH = Path("/Volumes/Plex/SSOT/projects/")


# =============================================================================
# Phase 2.1.1: Lightweight Project Detection
# =============================================================================

@dataclass
class ProjectInfo:
    """Lightweight project info from detection."""
    name: str
    type: str
    root_path: str
    language: str
    status: str
    tier: int = 0
    is_known: bool = False  # True if in SSOT registry
    markers_found: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self) -> str:
        known_str = " (SSOT)" if self.is_known else ""
        return f"{self.name}{known_str} [{self.type}] @ {self.root_path}"


class ProjectDetector:
    """
    Lightweight project detector for SAM (Phase 2.1.1).

    Detects projects from file paths by:
    1. Checking against known SSOT projects
    2. Looking for project markers in directory tree
    3. Inferring project type from markers

    Usage:
        detector = ProjectDetector()
        project = detector.detect()  # from cwd
        project = detector.detect("/path/to/project")
    """

    def __init__(self):
        # Expand ~ in all SSOT project paths
        self.known_projects = {}
        for path, info in SSOT_PROJECTS.items():
            expanded = os.path.expanduser(path)
            self.known_projects[expanded] = info

    def detect(self, path: str = None) -> Optional[ProjectInfo]:
        """
        Detect project from path (defaults to cwd).

        Args:
            path: Directory or file path to detect project from

        Returns:
            ProjectInfo if project detected, None otherwise
        """
        if path is None:
            path = os.getcwd()

        path = os.path.abspath(os.path.expanduser(path))

        # Try to match against known SSOT projects first
        known = self._match_known_project(path)
        if known:
            return known

        # Fall back to marker detection
        return self._detect_from_markers(path)

    def _match_known_project(self, path: str) -> Optional[ProjectInfo]:
        """Check if path is within a known SSOT project."""
        # Sort by path length (longest first) to match most specific project
        sorted_projects = sorted(
            self.known_projects.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for project_path, info in sorted_projects:
            # Check if path is within or equals project path
            if path.startswith(project_path) or project_path.startswith(path):
                return ProjectInfo(
                    name=info["name"],
                    type=info["type"],
                    root_path=project_path,
                    language=info["language"],
                    status=info["status"],
                    tier=info.get("tier", 0),
                    is_known=True,
                    markers_found=self._find_markers(project_path)
                )

        return None

    def _detect_from_markers(self, path: str) -> Optional[ProjectInfo]:
        """Detect project by walking up directory tree looking for markers."""
        current = Path(path)
        if not current.is_dir():
            current = current.parent

        max_depth = 10
        for _ in range(max_depth):
            markers = self._find_markers(str(current))

            if markers:
                # Found project root
                language = self._infer_language(markers)
                project_type = self._infer_type(markers, language)

                return ProjectInfo(
                    name=current.name,
                    type=project_type,
                    root_path=str(current),
                    language=language or "unknown",
                    status="detected",
                    is_known=False,
                    markers_found=markers
                )

            # Move up
            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def _find_markers(self, path: str) -> List[str]:
        """Find project markers in directory."""
        markers = []
        p = Path(path)

        if not p.exists():
            return markers

        for marker in PROJECT_MARKERS.keys():
            if (p / marker).exists():
                markers.append(marker)

        return markers

    def _infer_language(self, markers: List[str]) -> Optional[str]:
        """Infer primary language from markers."""
        for marker in markers:
            lang = PROJECT_MARKERS.get(marker)
            if lang:
                return lang
        return None

    def _infer_type(self, markers: List[str], language: str) -> str:
        """Infer project type from markers and language."""
        if "Cargo.toml" in markers:
            return "rust"
        if "Package.swift" in markers:
            return "swift"
        if "package.json" in markers:
            return "node"
        if any(m in markers for m in ["pyproject.toml", "setup.py", "requirements.txt"]):
            return "python"
        if "go.mod" in markers:
            return "go"
        if "CLAUDE.md" in markers:
            return "claude-project"

        return language or "unknown"

    def get_context_string(self, project: ProjectInfo) -> str:
        """Get formatted context string for prompt injection."""
        lines = [
            f"[Project: {project.name}]",
            f"Path: {project.root_path}",
            f"Type: {project.type}",
            f"Language: {project.language}",
            f"Status: {project.status}",
        ]

        if project.is_known:
            lines.append(f"Tier: {project.tier} (SSOT registered)")

        if project.markers_found:
            lines.append(f"Markers: {', '.join(project.markers_found)}")

        return "\n".join(lines)


def get_current_project(path: str = None) -> Optional[ProjectInfo]:
    """
    Get project info for current working directory or specified path.

    This is the primary entry point for Phase 2.1.1 project detection.

    Args:
        path: Optional path (defaults to cwd)

    Returns:
        ProjectInfo or None if no project detected

    Example:
        project = get_current_project()
        if project:
            print(f"Working in: {project.name}")
    """
    detector = ProjectDetector()
    return detector.detect(path)


@dataclass
class Project:
    """A detected project."""
    id: str
    name: str
    path: str
    category: str
    description: str
    status: str  # active, stale, archived
    tech_stack: List[str]
    last_accessed: datetime


@dataclass
class ProjectSession:
    """A session's state for a project."""
    project_id: str
    working_on: str
    recent_files: List[str]
    recent_errors: List[str]
    notes: str
    timestamp: datetime


# =============================================================================
# Phase 2.1.7: Session Recall - "Last time in this project" feature
# =============================================================================

@dataclass
class SessionRecallInfo:
    """Information about a past session for recall."""
    project_name: str
    project_id: str
    working_on: str
    notes: str
    recent_files: List[str]
    timestamp: datetime
    time_ago: str
    should_show_recall: bool  # True if >1 hour since last session
    recall_message: str  # Formatted recall message

    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "working_on": self.working_on,
            "notes": self.notes,
            "recent_files": self.recent_files,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "time_ago": self.time_ago,
            "should_show_recall": self.should_show_recall,
            "recall_message": self.recall_message,
        }


class SessionRecall:
    """
    Phase 2.1.7: "Last time in this project" recall system.

    Provides session continuity by:
    1. Tracking when you last worked on a project
    2. Generating recall summaries for returning to a project
    3. Handling natural language queries about past work

    Usage:
        from project_context import SessionRecall

        recall = SessionRecall()

        # When entering a project
        info = recall.get_project_recall("project_id", "Project Name")
        if info.should_show_recall:
            print(info.recall_message)

        # Query handling
        if recall.is_recall_query("What was I doing last time?"):
            response = recall.handle_recall_query(
                "What was I doing last time?",
                current_project_id="abc123"
            )

        # Save session state when leaving
        recall.save_session_state(
            project_id="abc123",
            working_on="Implementing feature X",
            notes="Need to test edge cases",
            recent_files=["src/main.py", "tests/test_main.py"]
        )
    """

    # Time threshold for showing recall (1 hour in seconds)
    RECALL_THRESHOLD_SECONDS = 3600

    # Natural language patterns for recall queries
    RECALL_PATTERNS = [
        # "What was I doing last time?"
        (r"what\s+(?:was\s+i|were\s+we)\s+(?:doing|working\s+on)(?:\s+last\s+time)?", "last_activity"),
        # "What did we work on yesterday/last week?"
        (r"what\s+did\s+(?:i|we)\s+(?:work\s+on|do)(?:\s+yesterday|\s+last\s+\w+)?", "past_work"),
        # "Remind me where we left off"
        (r"remind\s+me\s+(?:where\s+we|what\s+we|where\s+I)\s+(?:left\s+off|stopped|were)", "left_off"),
        # "Where did we leave off?"
        (r"where\s+did\s+(?:we|I)\s+(?:leave\s+off|stop|end)", "left_off"),
        # "What's the status of [project]?"
        (r"what(?:'s|\s+is)\s+the\s+status\s+of\s+(\w+)", "project_status"),
        # "When did I last work on this/[project]?"
        (r"when\s+did\s+(?:i|we)\s+last\s+(?:work|touch|modify)", "last_worked"),
        # "Continue from last time"
        (r"continue\s+(?:from\s+)?(?:last\s+time|where\s+we\s+left)", "continue"),
        # "Pick up where we left off"
        (r"pick\s+up\s+(?:from\s+)?where", "continue"),
    ]

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), query_type)
            for pattern, query_type in self.RECALL_PATTERNS
        ]

    def get_project_recall(
        self,
        project_id: str,
        project_name: str = None,
        db_path: Path = None
    ) -> Optional[SessionRecallInfo]:
        """
        Get recall information when entering a project.

        Args:
            project_id: The project's unique ID
            project_name: Optional project name for display
            db_path: Optional override for database path

        Returns:
            SessionRecallInfo if last session exists, None otherwise
        """
        db = db_path or self.db_path
        if not db.exists():
            return None

        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            # Get the most recent session for this project
            cur.execute("""
                SELECT project_id, working_on, recent_files, recent_errors, notes, timestamp
                FROM project_sessions
                WHERE project_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (project_id,))

            row = cur.fetchone()
            conn.close()

            if not row:
                return None

            session_timestamp = datetime.fromtimestamp(row[5]) if row[5] else None
            if not session_timestamp:
                return None

            # Calculate time since last session
            time_diff = datetime.now() - session_timestamp
            time_ago = self._format_time_ago(time_diff)
            should_show = time_diff.total_seconds() > self.RECALL_THRESHOLD_SECONDS

            # Build recall message
            working_on = row[1] or ""
            notes = row[4] or ""
            recent_files = json.loads(row[2]) if row[2] else []

            recall_message = self._build_recall_message(
                project_name or project_id,
                working_on,
                notes,
                recent_files,
                time_ago,
                should_show
            )

            return SessionRecallInfo(
                project_name=project_name or project_id,
                project_id=project_id,
                working_on=working_on,
                notes=notes,
                recent_files=recent_files,
                timestamp=session_timestamp,
                time_ago=time_ago,
                should_show_recall=should_show,
                recall_message=recall_message,
            )

        except Exception as e:
            print(f"[SessionRecall] Error getting recall: {e}")
            return None

    def _format_time_ago(self, delta: timedelta) -> str:
        """Format a timedelta as human-readable time ago string."""
        total_seconds = delta.total_seconds()
        minutes = int(total_seconds / 60)
        hours = int(total_seconds / 3600)
        days = int(total_seconds / 86400)

        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif days < 7:
            return f"{days} day{'s' if days != 1 else ''}"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''}"
        else:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''}"

    def _build_recall_message(
        self,
        project_name: str,
        working_on: str,
        notes: str,
        recent_files: List[str],
        time_ago: str,
        should_show: bool
    ) -> str:
        """Build a formatted recall message."""
        if not should_show:
            return ""

        parts = [f"Last time you worked on {project_name} ({time_ago} ago):"]

        if working_on:
            # Determine status verb based on content
            if any(word in working_on.lower() for word in ["fix", "debug", "error", "bug"]):
                status = "debugging"
            elif any(word in working_on.lower() for word in ["implement", "add", "build", "create"]):
                status = "implementing"
            elif any(word in working_on.lower() for word in ["test", "verify", "check"]):
                status = "testing"
            elif any(word in working_on.lower() for word in ["refactor", "clean", "improve"]):
                status = "refactoring"
            else:
                status = "working on"
            parts.append(f"  You were {status}: {working_on}")

        if notes:
            parts.append(f"  Notes: {notes[:200]}")

        if recent_files:
            files_str = ", ".join(recent_files[:3])
            if len(recent_files) > 3:
                files_str += f" (+{len(recent_files) - 3} more)"
            parts.append(f"  Recent files: {files_str}")

        return "\n".join(parts)

    def is_recall_query(self, query: str) -> bool:
        """
        Check if a query is asking about past session state.

        Args:
            query: User's natural language query

        Returns:
            True if this is a recall-related query
        """
        query_lower = query.lower().strip()
        for pattern, _ in self._compiled_patterns:
            if pattern.search(query_lower):
                return True
        return False

    def detect_recall_query_type(self, query: str) -> Optional[str]:
        """
        Detect the type of recall query.

        Args:
            query: User's natural language query

        Returns:
            Query type string or None if not a recall query
        """
        query_lower = query.lower().strip()
        for pattern, query_type in self._compiled_patterns:
            if pattern.search(query_lower):
                return query_type
        return None

    def handle_recall_query(
        self,
        query: str,
        current_project_id: str = None,
        current_project_name: str = None,
        db_path: Path = None
    ) -> Optional[str]:
        """
        Handle a natural language recall query.

        Args:
            query: User's query (e.g., "What was I doing last time?")
            current_project_id: ID of current project context (if any)
            current_project_name: Name of current project (if any)
            db_path: Optional override for database path

        Returns:
            Response string or None if not a recall query
        """
        query_type = self.detect_recall_query_type(query)
        if not query_type:
            return None

        db = db_path or self.db_path
        if not db.exists():
            return "I don't have any session history recorded yet."

        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            # Handle different query types
            if query_type in ("last_activity", "past_work", "left_off", "continue"):
                # Get last session for current project or most recent overall
                if current_project_id:
                    cur.execute("""
                        SELECT ps.project_id, ps.working_on, ps.recent_files,
                               ps.notes, ps.timestamp, p.name
                        FROM project_sessions ps
                        LEFT JOIN projects p ON ps.project_id = p.id
                        WHERE ps.project_id = ?
                        ORDER BY ps.timestamp DESC
                        LIMIT 1
                    """, (current_project_id,))
                else:
                    cur.execute("""
                        SELECT ps.project_id, ps.working_on, ps.recent_files,
                               ps.notes, ps.timestamp, p.name
                        FROM project_sessions ps
                        LEFT JOIN projects p ON ps.project_id = p.id
                        ORDER BY ps.timestamp DESC
                        LIMIT 1
                    """)

                row = cur.fetchone()
                conn.close()

                if not row:
                    return "I don't have any recorded sessions for this project."

                project_name = row[5] or current_project_name or row[0]
                working_on = row[1] or "general work"
                notes = row[3] or ""
                recent_files = json.loads(row[2]) if row[2] else []
                timestamp = datetime.fromtimestamp(row[4]) if row[4] else None

                time_ago = self._format_time_ago(datetime.now() - timestamp) if timestamp else "some time"

                response = f"In {project_name} ({time_ago} ago), you were working on: {working_on}"
                if notes:
                    response += f"\n\nNotes you left: {notes}"
                if recent_files:
                    response += f"\n\nFiles you were touching: {', '.join(recent_files[:5])}"

                return response

            elif query_type == "last_worked":
                # When did I last work on this?
                if current_project_id:
                    cur.execute("""
                        SELECT timestamp FROM project_sessions
                        WHERE project_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                    """, (current_project_id,))
                    row = cur.fetchone()
                    conn.close()

                    if row:
                        timestamp = datetime.fromtimestamp(row[0])
                        time_ago = self._format_time_ago(datetime.now() - timestamp)
                        return f"You last worked on this project {time_ago} ago ({timestamp.strftime('%Y-%m-%d %H:%M')})."
                    else:
                        return "I don't have any recorded work history for this project."
                else:
                    return "No project context. Try asking about a specific project."

            elif query_type == "project_status":
                # Get status of a named project (extract from query)
                match = re.search(r"status\s+of\s+(\w+)", query, re.IGNORECASE)
                if match:
                    project_search = match.group(1)
                    cur.execute("""
                        SELECT p.id, p.name, ps.working_on, ps.notes, ps.timestamp
                        FROM projects p
                        LEFT JOIN project_sessions ps ON p.id = ps.project_id
                        WHERE p.name LIKE ?
                        ORDER BY ps.timestamp DESC
                        LIMIT 1
                    """, (f"%{project_search}%",))
                    row = cur.fetchone()
                    conn.close()

                    if row:
                        name = row[1]
                        working_on = row[2] or "No recent activity recorded"
                        timestamp = datetime.fromtimestamp(row[4]) if row[4] else None
                        time_ago = self._format_time_ago(datetime.now() - timestamp) if timestamp else "unknown"
                        return f"Project '{name}': Last active {time_ago} ago. Last working on: {working_on}"
                    else:
                        return f"I don't have records for a project named '{project_search}'."

            conn.close()
            return None

        except Exception as e:
            print(f"[SessionRecall] Error handling query: {e}")
            return f"Error retrieving session history: {e}"

    def get_recent_sessions(
        self,
        limit: int = 5,
        db_path: Path = None
    ) -> List[Dict]:
        """
        Get recent sessions across all projects.

        Args:
            limit: Maximum number of sessions to return
            db_path: Optional override for database path

        Returns:
            List of session dictionaries
        """
        db = db_path or self.db_path
        if not db.exists():
            return []

        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            cur.execute("""
                SELECT ps.project_id, p.name, ps.working_on, ps.notes, ps.timestamp
                FROM project_sessions ps
                LEFT JOIN projects p ON ps.project_id = p.id
                ORDER BY ps.timestamp DESC
                LIMIT ?
            """, (limit,))

            sessions = []
            for row in cur.fetchall():
                timestamp = datetime.fromtimestamp(row[4]) if row[4] else None
                sessions.append({
                    "project_id": row[0],
                    "project_name": row[1] or row[0],
                    "working_on": row[2],
                    "notes": row[3],
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "time_ago": self._format_time_ago(datetime.now() - timestamp) if timestamp else None,
                })

            conn.close()
            return sessions

        except Exception as e:
            print(f"[SessionRecall] Error getting recent sessions: {e}")
            return []

    def save_session_state(
        self,
        project_id: str,
        working_on: str = "",
        notes: str = "",
        recent_files: List[str] = None,
        recent_errors: List[str] = None,
        db_path: Path = None
    ) -> bool:
        """
        Save session state for a project.

        Args:
            project_id: Project ID
            working_on: What was being worked on
            notes: Any notes for next session
            recent_files: List of recently touched files
            recent_errors: List of recent errors encountered
            db_path: Optional override for database path

        Returns:
            True if saved successfully
        """
        db = db_path or self.db_path
        db.parent.mkdir(parents=True, exist_ok=True)

        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    working_on TEXT,
                    recent_files TEXT,
                    recent_errors TEXT,
                    notes TEXT,
                    timestamp REAL
                )
            """)

            cur.execute("""
                INSERT INTO project_sessions
                (project_id, working_on, recent_files, recent_errors, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                working_on,
                json.dumps(recent_files or []),
                json.dumps(recent_errors or []),
                notes,
                time.time()
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[SessionRecall] Error saving session: {e}")
            return False


# Singleton for session recall
_session_recall: Optional[SessionRecall] = None

def get_session_recall() -> SessionRecall:
    """Get singleton session recall instance."""
    global _session_recall
    if _session_recall is None:
        _session_recall = SessionRecall()
    return _session_recall


# =============================================================================
# Phase 2.1.2: Project Profile Loader (from SSOT markdown files)
# =============================================================================

@dataclass
class ProjectProfile:
    """
    A project profile loaded from SSOT markdown files.

    Contains structured information about a project including:
    - Basic info (name, path, status)
    - Technical details (language, framework)
    - Documentation (description, architecture summary)
    - Session state (recent files, todos, notes)

    Usage:
        loader = ProjectProfileLoader()
        profile = loader.load_profile("SAM_TERMINAL")
        context = profile.to_context_string()
    """
    name: str
    path: str = ""
    status: str = "unknown"  # active, paused, complete, planned, unknown
    language: str = ""  # Primary language: python, rust, swift, javascript, etc.
    framework: str = ""  # Primary framework: tauri, swiftui, fastapi, vue, etc.
    description: str = ""
    architecture_summary: str = ""
    recent_files: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    notes: str = ""
    last_session_summary: str = ""
    raw_content: str = ""  # Full markdown content for advanced parsing
    file_path: str = ""  # Path to the SSOT markdown file

    def to_context_string(self) -> str:
        """Format profile as context string for prompt injection."""
        lines = [f"[Project Profile: {self.name}]"]

        if self.status:
            lines.append(f"Status: {self.status}")
        if self.path:
            lines.append(f"Path: {self.path}")
        if self.language:
            lines.append(f"Language: {self.language}")
        if self.framework:
            lines.append(f"Framework: {self.framework}")
        if self.description:
            lines.append(f"Description: {self.description[:300]}")
        if self.architecture_summary:
            lines.append(f"\nArchitecture:\n{self.architecture_summary[:500]}")
        if self.todos:
            lines.append(f"\nTODOs ({len(self.todos)}):")
            for todo in self.todos[:5]:
                lines.append(f"  - {todo[:100]}")
        if self.last_session_summary:
            lines.append(f"\nLast Session:\n{self.last_session_summary[:300]}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes raw_content for brevity)."""
        return {
            "name": self.name,
            "path": self.path,
            "status": self.status,
            "language": self.language,
            "framework": self.framework,
            "description": self.description,
            "architecture_summary": self.architecture_summary[:500] if self.architecture_summary else "",
            "recent_files": self.recent_files[:10],
            "todos": self.todos[:10],
            "notes": self.notes,
            "last_session_summary": self.last_session_summary,
            "file_path": self.file_path,
        }


class ProjectProfileLoader:
    """
    Loads project profiles from SSOT markdown files.

    The SSOT (Single Source of Truth) at /Volumes/Plex/SSOT/projects/
    contains markdown files for each project with structured information
    about status, architecture, recent work, and TODOs.

    Features:
    - Parses markdown structure to extract key sections
    - Caches profiles in memory with configurable TTL
    - Falls back to auto-detection if no SSOT file exists
    - Normalizes project names for flexible lookup

    Usage:
        loader = ProjectProfileLoader()

        # Load a single profile by name
        profile = loader.load_profile("SAM_TERMINAL")
        profile = loader.load_profile("sam-terminal")  # Normalized

        # Get all available profiles
        all_profiles = loader.get_all_profiles()

        # Refresh the cache after external changes
        loader.refresh_cache()

        # Get profile names
        names = loader.get_profile_names()
    """

    def __init__(self, ssot_path: Path = SSOT_PROJECTS_PATH):
        self.ssot_path = ssot_path
        self._cache: Dict[str, ProjectProfile] = {}
        self._cache_time: Optional[float] = None
        self._cache_max_age: float = 300.0  # 5 minutes

    def load_profile(self, project_name: str) -> Optional[ProjectProfile]:
        """
        Load a project profile by name.

        Args:
            project_name: The project name (e.g., "SAM_TERMINAL" or "sam_terminal")
                          Can also be the filename without .md extension.

        Returns:
            ProjectProfile if found, None otherwise.
        """
        # Normalize the name
        normalized = self._normalize_name(project_name)

        # Check cache first
        if self._is_cache_valid() and normalized in self._cache:
            return self._cache[normalized]

        # Try to find and load the file
        file_path = self._find_profile_file(normalized)
        if file_path is None:
            return self._auto_detect_profile(project_name)

        profile = self._parse_profile(file_path)
        if profile:
            self._cache[normalized] = profile

        return profile

    def get_all_profiles(self) -> List[ProjectProfile]:
        """
        Get all available project profiles from SSOT.

        Returns:
            List of all ProjectProfile objects.
        """
        if self._is_cache_valid() and self._cache:
            return list(self._cache.values())

        self.refresh_cache()
        return list(self._cache.values())

    def get_profile_names(self) -> List[str]:
        """Get list of all available profile names."""
        if not self._is_cache_valid():
            self.refresh_cache()
        return [p.name for p in self._cache.values()]

    def refresh_cache(self) -> None:
        """
        Refresh the profile cache by re-reading all SSOT files.
        """
        self._cache.clear()

        if not self.ssot_path.exists():
            return

        for file_path in self.ssot_path.glob("*.md"):
            profile = self._parse_profile(file_path)
            if profile:
                normalized = self._normalize_name(profile.name)
                # Also store by filename for easy lookup
                file_normalized = self._normalize_name(file_path.stem)
                self._cache[normalized] = profile
                if file_normalized != normalized:
                    self._cache[file_normalized] = profile

        self._cache_time = time.time()

    def _normalize_name(self, name: str) -> str:
        """Normalize a project name for consistent lookup."""
        return name.upper().replace(" ", "_").replace("-", "_")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_time is None:
            return False
        return (time.time() - self._cache_time) < self._cache_max_age

    def _find_profile_file(self, normalized_name: str) -> Optional[Path]:
        """Find the markdown file for a project."""
        if not self.ssot_path.exists():
            return None

        # Try exact match first
        exact_path = self.ssot_path / f"{normalized_name}.md"
        if exact_path.exists():
            return exact_path

        # Try with different case patterns
        for file_path in self.ssot_path.glob("*.md"):
            file_normalized = self._normalize_name(file_path.stem)
            if file_normalized == normalized_name:
                return file_path

        return None

    def _parse_profile(self, file_path: Path) -> Optional[ProjectProfile]:
        """
        Parse a markdown file into a ProjectProfile.

        Handles the common SSOT markdown structure with sections like:
        - ## What This Is / ## Vision / ## Purpose
        - ## Current State / ## Status
        - ## Architecture
        - ## File Locations
        - ## Next Steps / ## TODOs / ## Action Items
        - ## Current Action Items / ## What Needs To Be Done
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return None

        profile = ProjectProfile(
            name=self._extract_title(content, file_path.stem),
            file_path=str(file_path),
            raw_content=content
        )

        # Extract status
        profile.status = self._extract_status(content)

        # Extract path
        profile.path = self._extract_project_path(content)

        # Extract language and framework
        profile.language, profile.framework = self._extract_tech_stack(content)

        # Extract description
        profile.description = self._extract_description(content)

        # Extract architecture summary
        profile.architecture_summary = self._extract_architecture(content)

        # Extract TODOs
        profile.todos = self._extract_todos(content)

        # Extract recent files
        profile.recent_files = self._extract_recent_files(content)

        # Extract notes
        profile.notes = self._extract_notes(content)

        # Extract last session summary
        profile.last_session_summary = self._extract_last_session(content)

        return profile

    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract the title from the first heading."""
        # Match # Title - Subtitle or # Title
        match = re.search(r'^#\s+(.+?)(?:\s*[-–—]\s*.+)?$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return fallback.replace("_", " ").title()

    def _extract_status(self, content: str) -> str:
        """Extract project status."""
        # Look for status patterns
        patterns = [
            r'\*\*Status[:\s]*\*\*\s*(.+?)(?:\n|$)',  # **Status:** value
            r'Status:\s*(.+?)(?:\n|$)',  # Status: value
            r'##\s+Current State[:\s]*(.+?)(?:\n|$)',  # ## Current State: value
            r'Current State[:\s]+(.+?)(?:\n|$)',  # Current State: value
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                status_text = match.group(1).strip()
                # Normalize common status values
                lower = status_text.lower()
                if any(x in lower for x in ['complet', 'done', 'finished', 'working']):
                    return 'complete'
                elif any(x in lower for x in ['pause', 'hold', 'wait', 'idle']):
                    return 'paused'
                elif any(x in lower for x in ['active', 'progress', 'current', 'building']):
                    return 'active'
                elif any(x in lower for x in ['not started', 'planned', 'todo', 'ready']):
                    return 'planned'
                return status_text[:50]

        return 'unknown'

    def _extract_project_path(self, content: str) -> str:
        """Extract the project path."""
        # Look for path patterns
        patterns = [
            r'\*\*(?:Location|Path|Source)[:\s]*\*\*\s*`?([~/][^`\n]+)`?',
            r'(?:Location|Path|Source):\s*`?([~/][^`\n]+)`?',
            r'(?:Root):\s*`?([~/][^`\n]+)`?',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ''

    def _extract_tech_stack(self, content: str) -> Tuple[str, str]:
        """Extract primary language and framework."""
        language = ''
        framework = ''

        # Language detection (order matters - more specific first)
        lang_patterns = [
            (r'\blanguage[:\s]+(?:python|Python)\b', 'python'),
            (r'\blanguage[:\s]+(?:rust|Rust)\b', 'rust'),
            (r'\blanguage[:\s]+(?:swift|Swift)\b', 'swift'),
            (r'\bPython\b', 'python'),
            (r'\bRust\b', 'rust'),
            (r'\bSwift\b', 'swift'),
            (r'\bTypeScript\b', 'typescript'),
            (r'\bJavaScript\b', 'javascript'),
            (r'\bGo\b', 'go'),
            (r'\bC#\b', 'csharp'),
        ]

        for pattern, lang in lang_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                language = lang
                break

        # Framework detection
        framework_patterns = [
            (r'\bTauri\b', 'tauri'),
            (r'\bSwiftUI\b', 'swiftui'),
            (r'\bFastAPI\b', 'fastapi'),
            (r'\bVue(?:\.js)?\b', 'vue'),
            (r'\bReact\b', 'react'),
            (r'\bDjango\b', 'django'),
            (r'\bFlask\b', 'flask'),
            (r'\bMLX\b', 'mlx'),
            (r'\bComfyUI\b', 'comfyui'),
            (r'\bUnity\b', 'unity'),
            (r'\bPyTorch\b', 'pytorch'),
            (r'\bRVC\b', 'rvc'),
        ]

        for pattern, fw in framework_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                framework = fw
                break

        return language, framework

    def _extract_description(self, content: str) -> str:
        """Extract project description from 'What This Is', 'Vision', or 'Purpose' sections."""
        # Look for description sections
        patterns = [
            r'##\s+(?:What\s+This\s+Is|Vision|Purpose|Overview)\s*\n+(.+?)(?=\n##|\n\*\*|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1).strip()
                # Clean up markdown
                desc = re.sub(r'\n+', ' ', desc)
                desc = re.sub(r'\s+', ' ', desc)
                return desc[:500]

        # Fallback: get first paragraph after title
        match = re.search(r'^#[^#].+?\n+(.+?)(?=\n\n|\n#|\Z)', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            desc = re.sub(r'\n+', ' ', desc)
            return desc[:300]

        return ''

    def _extract_architecture(self, content: str) -> str:
        """Extract architecture summary."""
        match = re.search(
            r'##\s+(?:Architecture|System\s+Overview|Design|Complete\s+Architecture)\s*.*?\n+(.+?)(?=\n##|\Z)',
            content, re.IGNORECASE | re.DOTALL
        )

        if match:
            arch = match.group(1).strip()
            # Limit to reasonable length
            return arch[:1500]

        return ''

    def _extract_todos(self, content: str) -> List[str]:
        """Extract TODO items."""
        todos = []

        # Look for TODO sections
        sections = re.findall(
            r'##\s+(?:Next\s+Steps|TODOs?|Action\s+Items|What\s+Needs|Current\s+Action|To\s+Resume)\s*.*?\n+(.+?)(?=\n##|\Z)',
            content, re.IGNORECASE | re.DOTALL
        )

        for section in sections:
            # Extract checkbox items (unchecked)
            checkbox_items = re.findall(r'[-*]\s*\[\s*\]\s*(.+?)(?:\n|$)', section)
            todos.extend(checkbox_items)

            # Extract numbered items
            numbered_items = re.findall(r'\d+\.\s+(?!\[x\])(.+?)(?:\n|$)', section)
            todos.extend(numbered_items)

            # Extract bullet items that look like tasks (skip checked items)
            bullet_items = re.findall(r'[-*]\s+(?!\[x\])(?!\[\s*\])(.+?)(?:\n|$)', section)
            todos.extend([item for item in bullet_items if len(item) > 10 and not item.startswith('~~')])

        # Deduplicate and clean
        seen = set()
        clean_todos = []
        for todo in todos:
            todo = todo.strip()
            # Remove markdown formatting
            todo = re.sub(r'\*\*([^*]+)\*\*', r'\1', todo)
            todo = re.sub(r'`([^`]+)`', r'\1', todo)
            if todo and todo not in seen and len(todo) > 5:
                seen.add(todo)
                clean_todos.append(todo)

        return clean_todos[:20]  # Limit to 20 items

    def _extract_recent_files(self, content: str) -> List[str]:
        """Extract recently mentioned file paths."""
        files = []

        # Find file paths in backticks or in File Locations section
        file_patterns = [
            r'`([~/][\w/._-]+\.\w+)`',  # `~/path/to/file.py`
            r'\|\s*`?([~/][\w/._-]+\.\w+)`?\s*\|',  # Table cells
            r'(?:File|Source):\s*`?([~/][\w/._-]+\.\w+)`?',  # File: path
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            files.extend(matches)

        # Deduplicate while preserving order
        return list(dict.fromkeys(files))[:10]

    def _extract_notes(self, content: str) -> str:
        """Extract notes section if present."""
        patterns = [
            r'##\s+(?:Notes|Important|Key\s+Info|Dependencies)\s*\n+(.+?)(?=\n##|\Z)',
            r'##\s+(?:Hardware\s+Constraints|Constraints)\s*\n+(.+?)(?=\n##|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        return ''

    def _extract_last_session(self, content: str) -> str:
        """Extract last session or history summary."""
        # Look for history or recent work sections
        patterns = [
            r'##\s+(?:History|Recent\s+Work|Last\s+Session)\s*\n+(.+?)(?=\n##|\Z)',
            r'##\s+(?:Current\s+State|What\'s\s+Done)\s*\n+(.+?)(?=\n##|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                session = match.group(1).strip()
                return session[:500]

        return ''

    def _auto_detect_profile(self, project_name: str) -> Optional[ProjectProfile]:
        """
        Fall back to auto-detection if no SSOT file exists.
        Creates a minimal profile from the project path if possible.
        """
        # Try common project locations
        search_paths = [
            Path.home() / "ReverseLab" / "SAM",
            Path.home() / "Projects",
            Path.home() / "ai-studio",
            Path("/Volumes/Plex/DevSymlinks"),
        ]

        normalized = project_name.lower().replace("_", "-").replace(" ", "-")

        for base_path in search_paths:
            if not base_path.exists():
                continue

            # Try to find matching directory
            try:
                for subdir in base_path.iterdir():
                    if subdir.is_dir():
                        subdir_normalized = subdir.name.lower().replace("_", "-")
                        if normalized in subdir_normalized or subdir_normalized in normalized:
                            return ProjectProfile(
                                name=subdir.name,
                                path=str(subdir),
                                status='unknown',
                                notes=f"Auto-detected project. No SSOT file found at {self.ssot_path}"
                            )
            except PermissionError:
                continue

        return None


# Singleton for profile loader
_profile_loader: Optional[ProjectProfileLoader] = None

def get_profile_loader() -> ProjectProfileLoader:
    """Get singleton profile loader."""
    global _profile_loader
    if _profile_loader is None:
        _profile_loader = ProjectProfileLoader()
    return _profile_loader


# =============================================================================
# Phase 2.1.4: Project Watcher (monitors for project switches)
# =============================================================================

class ProjectWatcher:
    """
    Monitors for working directory changes and project switches.

    Uses polling (default 5 seconds) to detect when the user switches
    projects, then triggers registered callbacks and loads the new
    project profile automatically.

    Features:
    - Lightweight polling-based detection (no external dependencies)
    - Callback registration for project change events
    - Automatic profile loading on project switch
    - Thread-safe operation
    - Graceful start/stop

    Usage:
        watcher = ProjectWatcher()

        # Register callback for project changes
        def on_change(old_project, new_project, profile):
            print(f"Switched from {old_project} to {new_project}")

        watcher.on_project_change(on_change)

        # Start watching
        watcher.start()

        # Get current project at any time
        project = watcher.get_current_project()

        # Stop when done
        watcher.stop()

    CLI:
        python project_context.py watch [--interval 5] [--verbose]
    """

    def __init__(
        self,
        poll_interval: float = 5.0,
        auto_load_profile: bool = True
    ):
        """
        Initialize the project watcher.

        Args:
            poll_interval: Seconds between directory checks (default: 5.0)
            auto_load_profile: Whether to auto-load project profile on switch
        """
        self.poll_interval = poll_interval
        self.auto_load_profile = auto_load_profile

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[Optional[ProjectInfo], Optional[ProjectInfo], Optional[ProjectProfile]], None]] = []

        # Current state
        self._current_path: Optional[str] = None
        self._current_project: Optional[ProjectInfo] = None
        self._current_profile: Optional[ProjectProfile] = None

        # Components
        self._detector = ProjectDetector()
        self._profile_loader = get_profile_loader()

    def start(self) -> None:
        """
        Start watching for project changes.

        Spawns a background thread that polls the current working directory
        and detects project switches.
        """
        with self._lock:
            if self._running:
                return

            self._running = True

            # Initialize with current state
            self._current_path = os.getcwd()
            self._current_project = self._detector.detect(self._current_path)

            if self._current_project and self.auto_load_profile:
                self._current_profile = self._profile_loader.load_profile(
                    self._current_project.name
                )

            # Start polling thread
            self._thread = threading.Thread(
                target=self._poll_loop,
                name="ProjectWatcher",
                daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """
        Stop watching for project changes.

        Gracefully stops the polling thread.
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.poll_interval + 1.0)

        self._thread = None

    def on_project_change(
        self,
        callback: Callable[[Optional[ProjectInfo], Optional[ProjectInfo], Optional[ProjectProfile]], None]
    ) -> None:
        """
        Register a callback for project change events.

        Args:
            callback: Function called with (old_project, new_project, new_profile)
                      when the project changes. Profile may be None if not found.

        Example:
            def my_callback(old_project, new_project, profile):
                if new_project:
                    print(f"Now in: {new_project.name}")

            watcher.on_project_change(my_callback)
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(
        self,
        callback: Callable[[Optional[ProjectInfo], Optional[ProjectInfo], Optional[ProjectProfile]], None]
    ) -> bool:
        """
        Remove a previously registered callback.

        Args:
            callback: The callback function to remove

        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def get_current_project(self) -> Optional[ProjectInfo]:
        """
        Get the currently detected project.

        Returns:
            ProjectInfo for current project, or None if not in a project
        """
        with self._lock:
            return self._current_project

    def get_current_profile(self) -> Optional[ProjectProfile]:
        """
        Get the profile for the current project.

        Returns:
            ProjectProfile if available, None otherwise
        """
        with self._lock:
            return self._current_profile

    def get_current_path(self) -> Optional[str]:
        """
        Get the current working directory being monitored.

        Returns:
            Current path string
        """
        with self._lock:
            return self._current_path

    def is_running(self) -> bool:
        """
        Check if the watcher is currently running.

        Returns:
            True if watching, False otherwise
        """
        with self._lock:
            return self._running

    def check_now(self) -> bool:
        """
        Manually trigger a project check.

        Useful for immediate detection without waiting for the poll interval.

        Returns:
            True if project changed, False otherwise
        """
        return self._check_for_change()

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while True:
            with self._lock:
                if not self._running:
                    break

            self._check_for_change()
            time.sleep(self.poll_interval)

    def _check_for_change(self) -> bool:
        """
        Check if the working directory or project has changed.

        Returns:
            True if project changed, False otherwise
        """
        try:
            current_path = os.getcwd()
        except OSError:
            # Directory might have been deleted
            return False

        with self._lock:
            # Check if path changed
            if current_path == self._current_path:
                return False

            # Path changed, detect new project
            old_project = self._current_project
            new_project = self._detector.detect(current_path)

            # Check if project actually changed (not just subdirectory)
            if old_project and new_project:
                if old_project.root_path == new_project.root_path:
                    # Same project, just different subdirectory
                    self._current_path = current_path
                    return False

            # Project changed
            self._current_path = current_path
            self._current_project = new_project

            # Load new profile if available
            new_profile = None
            if new_project and self.auto_load_profile:
                new_profile = self._profile_loader.load_profile(new_project.name)
            self._current_profile = new_profile

            # Copy callbacks to avoid holding lock during callbacks
            callbacks = list(self._callbacks)

        # Fire callbacks outside the lock
        for callback in callbacks:
            try:
                callback(old_project, new_project, new_profile)
            except Exception as e:
                # Log but don't crash on callback errors
                print(f"ProjectWatcher callback error: {e}", file=sys.stderr)

        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get current watcher status.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "running": self._running,
                "poll_interval": self.poll_interval,
                "auto_load_profile": self.auto_load_profile,
                "current_path": self._current_path,
                "current_project": self._current_project.to_dict() if self._current_project else None,
                "has_profile": self._current_profile is not None,
                "callback_count": len(self._callbacks),
            }

    def __enter__(self) -> "ProjectWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


# Singleton for project watcher
_project_watcher: Optional[ProjectWatcher] = None

def get_project_watcher(
    poll_interval: float = 5.0,
    auto_start: bool = False
) -> ProjectWatcher:
    """
    Get singleton project watcher.

    Args:
        poll_interval: Seconds between checks (only used on first call)
        auto_start: Whether to start watching immediately

    Returns:
        ProjectWatcher instance
    """
    global _project_watcher
    if _project_watcher is None:
        _project_watcher = ProjectWatcher(poll_interval=poll_interval)
        if auto_start:
            _project_watcher.start()
    return _project_watcher


# =============================================================================
# Phase 2.1.5: Per-Project Session State Persistence
# =============================================================================

SESSION_DB_PATH = Path("/Volumes/David External/sam_memory/project_sessions.db")


@dataclass
class SessionState:
    """
    Session state for a project.

    Tracks what happened during a session with a project:
    - When the project was last accessed
    - Which files were touched/modified
    - Summary of what was discussed
    - TODOs added and completed
    - Freeform notes

    Usage:
        state = SessionState(
            project_name="SAM Brain",
            conversation_summary="Fixed memory leak in semantic_memory.py",
            files_touched=["semantic_memory.py", "sam_api.py"],
            todos_added=["Add caching layer"],
            notes="Consider using LRU cache"
        )
    """
    project_name: str
    last_accessed: datetime = field(default_factory=datetime.now)
    files_touched: List[str] = field(default_factory=list)
    conversation_summary: str = ""
    todos_added: List[str] = field(default_factory=list)
    todos_completed: List[str] = field(default_factory=list)
    notes: str = ""
    session_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "last_accessed": self.last_accessed.isoformat(),
            "files_touched": self.files_touched,
            "conversation_summary": self.conversation_summary,
            "todos_added": self.todos_added,
            "todos_completed": self.todos_completed,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        return cls(
            session_id=data.get("session_id"),
            project_name=data["project_name"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if isinstance(data.get("last_accessed"), str) else data.get("last_accessed", datetime.now()),
            files_touched=data.get("files_touched", []),
            conversation_summary=data.get("conversation_summary", ""),
            todos_added=data.get("todos_added", []),
            todos_completed=data.get("todos_completed", []),
            notes=data.get("notes", ""),
        )

    def __str__(self) -> str:
        age = datetime.now() - self.last_accessed
        hours = age.total_seconds() / 3600
        if hours < 1:
            age_str = f"{int(age.total_seconds() / 60)}m ago"
        elif hours < 24:
            age_str = f"{int(hours)}h ago"
        else:
            age_str = f"{int(hours / 24)}d ago"

        summary = self.conversation_summary[:50] if self.conversation_summary else "(no summary)"
        return f"[{self.project_name}] {age_str}: {summary}..."


class ProjectSessionState:
    """
    Per-project session state persistence (Phase 2.1.5).

    Tracks session state for each project including:
    - Timestamps of when projects were accessed
    - Files modified during sessions
    - Conversation summaries
    - TODOs added and completed
    - Freeform session notes

    All data persists to SQLite at /Volumes/David External/sam_memory/project_sessions.db

    Usage:
        session_state = ProjectSessionState()

        # Save a session
        state = SessionState(
            project_name="SAM Brain",
            conversation_summary="Added session persistence",
            files_touched=["project_context.py"],
            todos_added=["Write tests"]
        )
        session_state.save_session("SAM Brain", state)

        # Get last session
        last = session_state.get_last_session("SAM Brain")
        print(f"Last time: {last.conversation_summary}")

        # Update files touched
        session_state.update_files_touched("SAM Brain", ["new_file.py"])

        # Add a note
        session_state.add_session_note("SAM Brain", "Remember to test edge cases")

        # Get session history
        history = session_state.get_session_history("SAM Brain", limit=5)
        for session in history:
            print(session)
    """

    def __init__(self, db_path: Path = SESSION_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the session state database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Project sessions table - stores full session state
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                last_accessed REAL NOT NULL,
                files_touched TEXT,
                conversation_summary TEXT,
                todos_added TEXT,
                todos_completed TEXT,
                notes TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)

        # Index for fast lookups by project name
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_project
            ON project_sessions(project_name, last_accessed DESC)
        """)

        # Separate notes table for incremental note additions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS session_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_project
            ON session_notes(project_name, created_at DESC)
        """)

        conn.commit()
        conn.close()

    def save_session(self, project_name: str, state: SessionState) -> int:
        """
        Save a session state for a project.

        Args:
            project_name: The project name (e.g., "SAM Brain", "SAM Terminal")
            state: The SessionState to save

        Returns:
            The session ID of the saved session
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO project_sessions
            (project_name, last_accessed, files_touched, conversation_summary,
             todos_added, todos_completed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_name,
            state.last_accessed.timestamp(),
            json.dumps(state.files_touched),
            state.conversation_summary,
            json.dumps(state.todos_added),
            json.dumps(state.todos_completed),
            state.notes,
        ))

        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        return session_id

    def get_last_session(self, project_name: str) -> Optional[SessionState]:
        """
        Get the most recent session state for a project.

        Args:
            project_name: The project name to look up

        Returns:
            SessionState if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_name, last_accessed, files_touched,
                   conversation_summary, todos_added, todos_completed, notes
            FROM project_sessions
            WHERE project_name = ?
            ORDER BY last_accessed DESC
            LIMIT 1
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return SessionState(
                session_id=row[0],
                project_name=row[1],
                last_accessed=datetime.fromtimestamp(row[2]),
                files_touched=json.loads(row[3]) if row[3] else [],
                conversation_summary=row[4] or "",
                todos_added=json.loads(row[5]) if row[5] else [],
                todos_completed=json.loads(row[6]) if row[6] else [],
                notes=row[7] or "",
            )

        return None

    def update_files_touched(self, project_name: str, files: List[str]) -> bool:
        """
        Update the files_touched list for the most recent session of a project.

        If no session exists, creates a new minimal session.
        Files are appended and deduplicated.

        Args:
            project_name: The project name
            files: List of file paths to add

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Get the most recent session
        cur.execute("""
            SELECT id, files_touched
            FROM project_sessions
            WHERE project_name = ?
            ORDER BY last_accessed DESC
            LIMIT 1
        """, (project_name,))

        row = cur.fetchone()

        if row:
            # Update existing session
            session_id = row[0]
            existing_files = json.loads(row[1]) if row[1] else []

            # Merge and deduplicate, keeping most recent at the end
            all_files = existing_files + files
            # Preserve order while deduplicating (keeps last occurrence)
            seen = set()
            unique_files = []
            for f in reversed(all_files):
                if f not in seen:
                    seen.add(f)
                    unique_files.append(f)
            unique_files.reverse()

            # Keep only the most recent 50 files
            unique_files = unique_files[-50:]

            cur.execute("""
                UPDATE project_sessions
                SET files_touched = ?, last_accessed = ?
                WHERE id = ?
            """, (json.dumps(unique_files), time.time(), session_id))
        else:
            # Create a new minimal session
            cur.execute("""
                INSERT INTO project_sessions
                (project_name, last_accessed, files_touched, conversation_summary,
                 todos_added, todos_completed, notes)
                VALUES (?, ?, ?, '', '[]', '[]', '')
            """, (project_name, time.time(), json.dumps(files[-50:])))

        conn.commit()
        conn.close()
        return True

    def add_session_note(self, project_name: str, note: str) -> int:
        """
        Add a freeform note for a project.

        Notes are stored separately and can be retrieved with get_session_history.
        Also appends to the most recent session's notes field.

        Args:
            project_name: The project name
            note: The note text to add

        Returns:
            The note ID
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Add to separate notes table
        cur.execute("""
            INSERT INTO session_notes (project_name, note)
            VALUES (?, ?)
        """, (project_name, note))

        note_id = cur.lastrowid

        # Also update the most recent session's notes field
        cur.execute("""
            SELECT id, notes
            FROM project_sessions
            WHERE project_name = ?
            ORDER BY last_accessed DESC
            LIMIT 1
        """, (project_name,))

        row = cur.fetchone()
        if row:
            session_id = row[0]
            existing_notes = row[1] or ""

            # Append the new note with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_notes = f"{existing_notes}\n[{timestamp}] {note}" if existing_notes else f"[{timestamp}] {note}"

            # Truncate if too long (keep last 5000 chars)
            if len(new_notes) > 5000:
                new_notes = "..." + new_notes[-4997:]

            cur.execute("""
                UPDATE project_sessions
                SET notes = ?, last_accessed = ?
                WHERE id = ?
            """, (new_notes, time.time(), session_id))
        else:
            # Create a minimal session with this note
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            cur.execute("""
                INSERT INTO project_sessions
                (project_name, last_accessed, files_touched, conversation_summary,
                 todos_added, todos_completed, notes)
                VALUES (?, ?, '[]', '', '[]', '[]', ?)
            """, (project_name, time.time(), f"[{timestamp}] {note}"))

        conn.commit()
        conn.close()
        return note_id

    def get_session_history(self, project_name: str, limit: int = 5) -> List[SessionState]:
        """
        Get the session history for a project.

        Args:
            project_name: The project name
            limit: Maximum number of sessions to return (default 5)

        Returns:
            List of SessionState objects, most recent first
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_name, last_accessed, files_touched,
                   conversation_summary, todos_added, todos_completed, notes
            FROM project_sessions
            WHERE project_name = ?
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (project_name, limit))

        sessions = []
        for row in cur.fetchall():
            sessions.append(SessionState(
                session_id=row[0],
                project_name=row[1],
                last_accessed=datetime.fromtimestamp(row[2]),
                files_touched=json.loads(row[3]) if row[3] else [],
                conversation_summary=row[4] or "",
                todos_added=json.loads(row[5]) if row[5] else [],
                todos_completed=json.loads(row[6]) if row[6] else [],
                notes=row[7] or "",
            ))

        conn.close()
        return sessions

    def get_all_project_sessions(self) -> Dict[str, SessionState]:
        """
        Get the most recent session for all projects.

        Returns:
            Dictionary mapping project names to their most recent SessionState
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Use a subquery to get the most recent session per project
        cur.execute("""
            SELECT id, project_name, last_accessed, files_touched,
                   conversation_summary, todos_added, todos_completed, notes
            FROM project_sessions p1
            WHERE last_accessed = (
                SELECT MAX(last_accessed)
                FROM project_sessions p2
                WHERE p2.project_name = p1.project_name
            )
            ORDER BY last_accessed DESC
        """)

        sessions = {}
        for row in cur.fetchall():
            sessions[row[1]] = SessionState(
                session_id=row[0],
                project_name=row[1],
                last_accessed=datetime.fromtimestamp(row[2]),
                files_touched=json.loads(row[3]) if row[3] else [],
                conversation_summary=row[4] or "",
                todos_added=json.loads(row[5]) if row[5] else [],
                todos_completed=json.loads(row[6]) if row[6] else [],
                notes=row[7] or "",
            )

        conn.close()
        return sessions

    def get_project_notes(self, project_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get all notes for a project from the separate notes table.

        Args:
            project_name: The project name
            limit: Maximum number of notes to return

        Returns:
            List of note dictionaries with 'id', 'note', and 'created_at' fields
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, note, created_at
            FROM session_notes
            WHERE project_name = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_name, limit))

        notes = []
        for row in cur.fetchall():
            notes.append({
                "id": row[0],
                "note": row[1],
                "created_at": datetime.fromtimestamp(row[2]).isoformat(),
            })

        conn.close()
        return notes

    def get_recent_activity(self, days: int = 7, limit: int = 20) -> List[SessionState]:
        """
        Get recent session activity across all projects.

        Args:
            days: How many days back to look
            limit: Maximum number of sessions to return

        Returns:
            List of SessionState objects from recent sessions
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).timestamp()

        cur.execute("""
            SELECT id, project_name, last_accessed, files_touched,
                   conversation_summary, todos_added, todos_completed, notes
            FROM project_sessions
            WHERE last_accessed >= ?
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (cutoff, limit))

        sessions = []
        for row in cur.fetchall():
            sessions.append(SessionState(
                session_id=row[0],
                project_name=row[1],
                last_accessed=datetime.fromtimestamp(row[2]),
                files_touched=json.loads(row[3]) if row[3] else [],
                conversation_summary=row[4] or "",
                todos_added=json.loads(row[5]) if row[5] else [],
                todos_completed=json.loads(row[6]) if row[6] else [],
                notes=row[7] or "",
            ))

        conn.close()
        return sessions

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about session state storage."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM project_sessions")
        total_sessions = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT project_name) FROM project_sessions")
        unique_projects = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM session_notes")
        total_notes = cur.fetchone()[0]

        # Get most active projects
        cur.execute("""
            SELECT project_name, COUNT(*) as count
            FROM project_sessions
            GROUP BY project_name
            ORDER BY count DESC
            LIMIT 5
        """)
        most_active = [{"project": row[0], "sessions": row[1]} for row in cur.fetchall()]

        # Get recently active projects
        week_ago = (datetime.now() - timedelta(days=7)).timestamp()
        cur.execute("""
            SELECT DISTINCT project_name
            FROM project_sessions
            WHERE last_accessed >= ?
            ORDER BY last_accessed DESC
        """, (week_ago,))
        recent_projects = [row[0] for row in cur.fetchall()]

        conn.close()

        return {
            "total_sessions": total_sessions,
            "unique_projects": unique_projects,
            "total_notes": total_notes,
            "most_active_projects": most_active,
            "recently_active_projects": recent_projects,
            "db_path": str(self.db_path),
        }


# Singleton for session state
_session_state: Optional[ProjectSessionState] = None


def get_session_state() -> ProjectSessionState:
    """Get singleton session state manager."""
    global _session_state
    if _session_state is None:
        _session_state = ProjectSessionState()
    return _session_state


class ProjectContext:
    """
    Manages project context for SAM.

    Knows what project you're in, what you were doing,
    and injects relevant context into prompts.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_inventory()

    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Projects table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                category TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                tech_stack TEXT,
                last_accessed REAL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_project_path ON projects(path)")

        # Project sessions (per-project memory)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                working_on TEXT,
                recent_files TEXT,
                recent_errors TEXT,
                notes TEXT,
                timestamp REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Project TODOs (extracted from code)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_todos (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                content TEXT,
                priority TEXT DEFAULT 'normal',
                is_done INTEGER DEFAULT 0,
                found_at REAL
            )
        """)

        conn.commit()
        conn.close()

    def _load_inventory(self):
        """Load project inventory from exhaustive analysis."""
        self.inventory = {}
        if INVENTORY_PATH.exists():
            try:
                with open(INVENTORY_PATH) as f:
                    data = json.load(f)
                    for item in data.get("projects", []):
                        path = item.get("path", "")
                        if path:
                            self.inventory[path] = item
            except Exception:
                pass

    def detect_project(self, path: str) -> Optional[Project]:
        """
        Detect which project a path belongs to.
        Returns Project info if found.
        """
        path = os.path.abspath(path)

        # Check if it's a known project path
        for project_path, info in self.inventory.items():
            if path.startswith(project_path) or project_path.startswith(path):
                project = self._get_or_create_project(project_path, info)
                self._update_last_accessed(project.id)
                return project

        # Try to detect from directory structure
        return self._detect_from_structure(path)

    def _get_or_create_project(self, path: str, info: dict) -> Project:
        """Get project from DB or create it."""
        project_id = hashlib.md5(path.encode()).hexdigest()[:12]

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()

        if row:
            project = Project(
                id=row[0], name=row[1], path=row[2],
                category=row[3], description=row[4], status=row[5],
                tech_stack=json.loads(row[6]) if row[6] else [],
                last_accessed=datetime.fromtimestamp(row[7]) if row[7] else datetime.now()
            )
        else:
            # Create from inventory info
            tech_stack = []
            if info.get("languages"):
                tech_stack = info.get("languages", [])[:5]

            project = Project(
                id=project_id,
                name=info.get("name", os.path.basename(path)),
                path=path,
                category=info.get("category", "unknown"),
                description=info.get("description", ""),
                status=info.get("status", "active"),
                tech_stack=tech_stack,
                last_accessed=datetime.now()
            )

            cur.execute("""
                INSERT INTO projects (id, name, path, category, description, status, tech_stack, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id, project.name, project.path, project.category,
                project.description, project.status, json.dumps(project.tech_stack),
                time.time()
            ))
            conn.commit()

        conn.close()
        return project

    def _detect_from_structure(self, path: str) -> Optional[Project]:
        """Detect project from directory structure."""
        path = Path(path)

        # Look for project markers going up the tree
        markers = {
            "package.json": "javascript",
            "Cargo.toml": "rust",
            "pyproject.toml": "python",
            "setup.py": "python",
            "go.mod": "go",
            ".git": None,  # Just a marker
        }

        current = path if path.is_dir() else path.parent

        for _ in range(10):  # Max 10 levels up
            for marker, lang in markers.items():
                if (current / marker).exists():
                    # Found project root
                    return self._get_or_create_project(str(current), {
                        "name": current.name,
                        "languages": [lang] if lang else [],
                    })

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def _update_last_accessed(self, project_id: str):
        """Update last accessed timestamp."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE projects SET last_accessed = ? WHERE id = ?",
            (time.time(), project_id)
        )
        conn.commit()
        conn.close()

    def get_last_session(self, project_id: str) -> Optional[ProjectSession]:
        """Get the last session for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT project_id, working_on, recent_files, recent_errors, notes, timestamp
            FROM project_sessions
            WHERE project_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (project_id,))

        row = cur.fetchone()
        conn.close()

        if row:
            return ProjectSession(
                project_id=row[0],
                working_on=row[1] or "",
                recent_files=json.loads(row[2]) if row[2] else [],
                recent_errors=json.loads(row[3]) if row[3] else [],
                notes=row[4] or "",
                timestamp=datetime.fromtimestamp(row[5]) if row[5] else datetime.now()
            )
        return None

    def save_session_state(
        self,
        project_id: str,
        working_on: str = "",
        recent_files: List[str] = None,
        recent_errors: List[str] = None,
        notes: str = ""
    ):
        """Save session state for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO project_sessions (project_id, working_on, recent_files, recent_errors, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id, working_on,
            json.dumps(recent_files or []),
            json.dumps(recent_errors or []),
            notes, time.time()
        ))

        conn.commit()
        conn.close()

    def get_project_context(self, project: Project, include_session: bool = True) -> str:
        """
        Get formatted context for prompt injection.
        """
        lines = [f"[Project: {project.name}]"]
        lines.append(f"Path: {project.path}")
        lines.append(f"Category: {project.category}")

        if project.tech_stack:
            lines.append(f"Tech: {', '.join(project.tech_stack)}")

        if project.description:
            lines.append(f"Description: {project.description[:200]}")

        if include_session:
            session = self.get_last_session(project.id)
            if session:
                age = datetime.now() - session.timestamp
                if age < timedelta(days=7):  # Only show recent sessions
                    lines.append(f"\n[Last Session - {self._format_age(age)} ago]")
                    if session.working_on:
                        lines.append(f"Working on: {session.working_on}")
                    if session.recent_files:
                        lines.append(f"Files: {', '.join(session.recent_files[:3])}")
                    if session.notes:
                        lines.append(f"Notes: {session.notes[:200]}")

        return "\n".join(lines)

    def _format_age(self, delta: timedelta) -> str:
        """Format timedelta as human-readable."""
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"{int(delta.total_seconds() / 60)} minutes"
        elif hours < 24:
            return f"{int(hours)} hours"
        else:
            return f"{int(hours / 24)} days"

    def get_project_todos(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get TODOs for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, file_path, line_number, content, priority
            FROM project_todos
            WHERE project_id = ? AND is_done = 0
            ORDER BY
                CASE priority WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                found_at DESC
            LIMIT ?
        """, (project_id, limit))

        todos = []
        for row in cur.fetchall():
            todos.append({
                "id": row[0],
                "file": row[1],
                "line": row[2],
                "content": row[3],
                "priority": row[4]
            })

        conn.close()
        return todos

    def scan_for_todos(self, project_path: str, project_id: str) -> int:
        """Scan project for TODOs and FIXMEs."""
        path = Path(project_path)
        if not path.exists():
            return 0

        todo_pattern = re.compile(r'#\s*(TODO|FIXME|HACK|XXX)[:\s]+(.+?)$', re.IGNORECASE | re.MULTILINE)
        extensions = {'.py', '.js', '.ts', '.rs', '.go', '.vue', '.jsx', '.tsx'}

        found = 0
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        try:
            for file in path.rglob('*'):
                if file.suffix not in extensions:
                    continue
                if any(skip in str(file) for skip in ['node_modules', '.git', 'target', 'dist', '__pycache__', '.venv', 'venv', 'site-packages']):
                    continue

                try:
                    content = file.read_text(errors='ignore')
                    for line_num, line in enumerate(content.split('\n'), 1):
                        match = todo_pattern.search(line)
                        if match:
                            todo_type = match.group(1).upper()
                            todo_content = match.group(2).strip()
                            todo_id = hashlib.md5(f"{file}:{line_num}:{todo_content}".encode()).hexdigest()[:12]

                            priority = "high" if todo_type in ['FIXME', 'XXX'] else "normal"

                            cur.execute("""
                                INSERT OR REPLACE INTO project_todos
                                (id, project_id, file_path, line_number, content, priority, found_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                todo_id, project_id, str(file.relative_to(path)),
                                line_num, todo_content[:500], priority, time.time()
                            ))
                            found += 1
                except Exception:
                    continue

        finally:
            conn.commit()
            conn.close()

        return found

    def get_recent_projects(self, limit: int = 5) -> List[Project]:
        """Get recently accessed projects."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, path, category, description, status, tech_stack, last_accessed
            FROM projects
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (limit,))

        projects = []
        for row in cur.fetchall():
            projects.append(Project(
                id=row[0], name=row[1], path=row[2],
                category=row[3], description=row[4], status=row[5],
                tech_stack=json.loads(row[6]) if row[6] else [],
                last_accessed=datetime.fromtimestamp(row[7]) if row[7] else datetime.now()
            ))

        conn.close()
        return projects

    def get_stats(self) -> Dict:
        """Get project context statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM projects")
        total_projects = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM project_sessions")
        total_sessions = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM project_todos WHERE is_done = 0")
        open_todos = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT project_id) FROM project_sessions")
        projects_with_sessions = cur.fetchone()[0]

        conn.close()

        return {
            "total_projects": total_projects,
            "projects_with_sessions": projects_with_sessions,
            "total_sessions": total_sessions,
            "open_todos": open_todos
        }


# Singleton
_project_context = None

def get_project_context() -> ProjectContext:
    """Get singleton project context."""
    global _project_context
    if _project_context is None:
        _project_context = ProjectContext()
    return _project_context


# CLI
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="SAM Project Context & Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Phase 2.1.1: Lightweight detection
    python project_context.py detect
    python project_context.py detect ~/ReverseLab/SAM
    python project_context.py detect . --json
    python project_context.py list

    # Phase 2.1.2: Profile loading from SSOT markdown files
    python project_context.py profile SAM_TERMINAL
    python project_context.py profile orchestrator --json
    python project_context.py profiles
    python project_context.py profiles --json

    # Phase 2.1.4: Project watcher
    python project_context.py watch
    python project_context.py watch --interval 3 --verbose

    # Phase 2.1.7: Session recall ("last time in this project")
    python project_context.py recall                                   # Recall for current project
    python project_context.py recall ~/ReverseLab/SAM --json           # Recall with JSON output
    python project_context.py sessions                                 # Show recent sessions
    python project_context.py sessions --limit 10                      # More sessions
    python project_context.py query "What was I doing last time?"      # Natural language query
    python project_context.py query "Remind me where we left off" --project .
    python project_context.py save-session abc123 --working-on "Feature X" --notes "Need tests"

    # Legacy commands (require external DB)
    python project_context.py context --path .
    python project_context.py recent
    python project_context.py stats
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Phase 2.1.1: detect command (lightweight)
    detect_parser = subparsers.add_parser("detect", help="Detect project from path (Phase 2.1.1)")
    detect_parser.add_argument("path", nargs="?", default=".", help="Path to detect (default: .)")
    detect_parser.add_argument("--json", action="store_true", help="Output as JSON")
    detect_parser.add_argument("--context", action="store_true", help="Output as context string")

    # Phase 2.1.1: list command
    list_parser = subparsers.add_parser("list", help="List known SSOT projects")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Phase 2.1.2: profile command
    profile_parser = subparsers.add_parser("profile", help="Load a project profile from SSOT (Phase 2.1.2)")
    profile_parser.add_argument("name", help="Project name (e.g., SAM_TERMINAL, orchestrator)")
    profile_parser.add_argument("--json", action="store_true", help="Output as JSON")
    profile_parser.add_argument("--context", action="store_true", help="Output as context string for prompts")

    # Phase 2.1.2: profiles command
    profiles_parser = subparsers.add_parser("profiles", help="List all SSOT project profiles (Phase 2.1.2)")
    profiles_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Phase 2.1.4: watch command
    watch_parser = subparsers.add_parser("watch", help="Watch for project switches (Phase 2.1.4)")
    watch_parser.add_argument("--interval", type=float, default=5.0, help="Poll interval in seconds (default: 5)")
    watch_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    # Phase 2.1.7: Session recall commands
    recall_parser = subparsers.add_parser("recall", help="Get session recall for a project (Phase 2.1.7)")
    recall_parser.add_argument("project", nargs="?", help="Project name or path (default: current)")
    recall_parser.add_argument("--json", action="store_true", help="Output as JSON")

    sessions_parser = subparsers.add_parser("sessions", help="Show recent sessions (Phase 2.1.7)")
    sessions_parser.add_argument("--limit", type=int, default=5, help="Number of sessions to show")
    sessions_parser.add_argument("--json", action="store_true", help="Output as JSON")

    query_parser = subparsers.add_parser("query", help="Handle a recall query (Phase 2.1.7)")
    query_parser.add_argument("question", help="Natural language question (e.g., 'What was I doing last time?')")
    query_parser.add_argument("--project", help="Project context (optional)")

    save_session_parser = subparsers.add_parser("save-session", help="Save session state (Phase 2.1.7)")
    save_session_parser.add_argument("project_id", help="Project ID")
    save_session_parser.add_argument("--working-on", default="", help="What you were working on")
    save_session_parser.add_argument("--notes", default="", help="Notes for next session")
    save_session_parser.add_argument("--files", nargs="*", default=[], help="Recent files")

    # Legacy commands
    context_parser = subparsers.add_parser("context", help="Get full project context (legacy)")
    context_parser.add_argument("--path", default=".", help="Path")

    recent_parser = subparsers.add_parser("recent", help="Show recent projects (legacy)")

    todos_parser = subparsers.add_parser("todos", help="Show project TODOs (legacy)")
    todos_parser.add_argument("--path", default=".", help="Path")

    scan_parser = subparsers.add_parser("scan", help="Scan for TODOs (legacy)")
    scan_parser.add_argument("--path", default=".", help="Path")

    stats_parser = subparsers.add_parser("stats", help="Show stats (legacy)")

    args = parser.parse_args()

    # Phase 2.1.1: Lightweight commands
    if args.command == "detect":
        detector = ProjectDetector()
        project = detector.detect(os.path.abspath(args.path))

        if project:
            if args.json:
                print(json.dumps(project.to_dict(), indent=2))
            elif args.context:
                print(detector.get_context_string(project))
            else:
                print(f"Detected: {project.name}")
                print(f"  Path: {project.root_path}")
                print(f"  Type: {project.type}")
                print(f"  Language: {project.language}")
                print(f"  Status: {project.status}")
                if project.is_known:
                    print(f"  Tier: {project.tier} (SSOT registered)")
                if project.markers_found:
                    print(f"  Markers: {', '.join(project.markers_found)}")
        else:
            print("No project detected")
            sys.exit(1)

    elif args.command == "list":
        if args.json:
            print(json.dumps(SSOT_PROJECTS, indent=2))
        else:
            print("Known SSOT Projects:")
            print("-" * 60)
            # Group by tier
            by_tier = {}
            for path, info in SSOT_PROJECTS.items():
                tier = info.get("tier", 0)
                if tier not in by_tier:
                    by_tier[tier] = []
                by_tier[tier].append((path, info))

            for tier in sorted(by_tier.keys()):
                print(f"\nTier {tier}:")
                for path, info in by_tier[tier]:
                    status_icon = {"active": "+", "building": "*", "ready": "o", "idle": "-"}.get(info["status"], "?")
                    print(f"  [{status_icon}] {info['name']}")
                    print(f"      {path}")

    # Phase 2.1.2: Profile commands
    elif args.command == "profile":
        loader = get_profile_loader()
        profile = loader.load_profile(args.name)

        if profile:
            if args.json:
                print(json.dumps(profile.to_dict(), indent=2))
            elif args.context:
                print(profile.to_context_string())
            else:
                print(f"Project Profile: {profile.name}")
                print("-" * 60)
                print(f"  Status: {profile.status}")
                if profile.path:
                    print(f"  Path: {profile.path}")
                if profile.language:
                    print(f"  Language: {profile.language}")
                if profile.framework:
                    print(f"  Framework: {profile.framework}")
                if profile.description:
                    print(f"\n  Description:")
                    print(f"    {profile.description[:200]}...")
                if profile.todos:
                    print(f"\n  TODOs ({len(profile.todos)}):")
                    for todo in profile.todos[:5]:
                        print(f"    - {todo[:80]}")
                if profile.notes:
                    print(f"\n  Notes:")
                    print(f"    {profile.notes[:200]}...")
                print(f"\n  Source: {profile.file_path}")
        else:
            print(f"Profile not found: {args.name}")
            print("\nAvailable profiles:")
            loader.refresh_cache()
            for name in loader.get_profile_names():
                print(f"  - {name}")
            sys.exit(1)

    elif args.command == "profiles":
        loader = get_profile_loader()
        profiles = loader.get_all_profiles()

        if args.json:
            print(json.dumps([p.to_dict() for p in profiles], indent=2))
        else:
            print(f"SSOT Project Profiles ({len(profiles)}):")
            print("-" * 60)

            # Group by status
            by_status = {}
            for profile in profiles:
                status = profile.status or 'unknown'
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(profile)

            status_order = ['active', 'complete', 'planned', 'paused', 'unknown']
            for status in status_order:
                if status in by_status:
                    status_icon = {"active": "+", "complete": "o", "planned": "*", "paused": "-", "unknown": "?"}.get(status, "?")
                    print(f"\n[{status_icon}] {status.upper()}:")
                    for profile in by_status[status]:
                        lang = f" ({profile.language})" if profile.language else ""
                        fw = f" + {profile.framework}" if profile.framework else ""
                        print(f"    {profile.name}{lang}{fw}")

    # Phase 2.1.4: Watch command
    elif args.command == "watch":
        verbose = args.verbose

        def on_project_change(old_project, new_project, profile):
            timestamp = datetime.now().strftime("%H:%M:%S")
            old_name = old_project.name if old_project else "(none)"
            new_name = new_project.name if new_project else "(none)"

            print(f"\n[{timestamp}] Project switch detected:")
            print(f"  From: {old_name}")
            print(f"  To:   {new_name}")

            if verbose and new_project:
                print(f"  Path: {new_project.root_path}")
                print(f"  Type: {new_project.type}")
                print(f"  Language: {new_project.language}")
                if new_project.is_known:
                    print(f"  Tier: {new_project.tier} (SSOT registered)")

            if verbose and profile:
                print(f"  Profile loaded: {profile.file_path}")
                if profile.todos:
                    print(f"  TODOs: {len(profile.todos)}")

        watcher = ProjectWatcher(poll_interval=args.interval)
        watcher.on_project_change(on_project_change)

        print(f"ProjectWatcher started (polling every {args.interval}s)")
        print("Press Ctrl+C to stop\n")

        # Show initial state
        watcher.start()
        project = watcher.get_current_project()
        if project:
            print(f"Current project: {project.name}")
            print(f"  Path: {project.root_path}")
            if verbose:
                print(f"  Type: {project.type}")
                print(f"  Language: {project.language}")
        else:
            print("Current project: (none detected)")

        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping watcher...")
            watcher.stop()
            print("Done.")

    # Legacy commands
    elif args.command == "context":
        ctx = get_project_context()
        project = ctx.detect_project(os.path.abspath(args.path))
        if project:
            print(ctx.get_project_context(project))
        else:
            print("No project detected")

    elif args.command == "recent":
        ctx = get_project_context()
        projects = ctx.get_recent_projects()
        print("Recent projects:")
        for p in projects:
            print(f"  - {p.name} ({p.category})")

    elif args.command == "todos":
        ctx = get_project_context()
        project = ctx.detect_project(os.path.abspath(args.path))
        if project:
            todos = ctx.get_project_todos(project.id)
            print(f"TODOs in {project.name}:")
            for t in todos:
                print(f"  [{t['priority']}] {t['file']}:{t['line']} - {t['content'][:60]}")

    elif args.command == "scan":
        ctx = get_project_context()
        project = ctx.detect_project(os.path.abspath(args.path))
        if project:
            count = ctx.scan_for_todos(project.path, project.id)
            print(f"Found {count} TODOs in {project.name}")

    elif args.command == "stats":
        ctx = get_project_context()
        stats = ctx.get_stats()
        print(json.dumps(stats, indent=2))

    # Phase 2.1.7: Session recall commands
    elif args.command == "recall":
        recall = get_session_recall()
        ctx = get_project_context()

        # Get project from arg or detect from current path
        if args.project:
            project = ctx.detect_project(os.path.abspath(args.project))
        else:
            project = ctx.detect_project(os.getcwd())

        if not project:
            print("No project detected. Specify a project path.")
            sys.exit(1)

        info = recall.get_project_recall(project.id, project.name)

        if args.json:
            if info:
                print(json.dumps(info.to_dict(), indent=2))
            else:
                print(json.dumps({"error": "No session history found"}, indent=2))
        else:
            if info:
                print(f"Project: {info.project_name}")
                print(f"Last session: {info.time_ago} ago")
                if info.should_show_recall:
                    print(f"\n{info.recall_message}")
                else:
                    print("(Recent session - no recall needed)")
            else:
                print(f"No session history found for {project.name}")

    elif args.command == "sessions":
        recall = get_session_recall()
        sessions = recall.get_recent_sessions(limit=args.limit)

        if args.json:
            print(json.dumps(sessions, indent=2))
        else:
            print(f"Recent sessions ({len(sessions)}):")
            print("-" * 60)
            for session in sessions:
                print(f"  {session['project_name']} ({session['time_ago']} ago)")
                if session['working_on']:
                    print(f"    Working on: {session['working_on'][:50]}")
                if session['notes']:
                    print(f"    Notes: {session['notes'][:50]}")
                print()

    elif args.command == "query":
        recall = get_session_recall()

        # Get project context if specified
        project_id = None
        project_name = None
        if args.project:
            ctx = get_project_context()
            project = ctx.detect_project(os.path.abspath(args.project))
            if project:
                project_id = project.id
                project_name = project.name

        # Check if it's a recall query
        if recall.is_recall_query(args.question):
            response = recall.handle_recall_query(
                args.question,
                current_project_id=project_id,
                current_project_name=project_name
            )
            print(response)
        else:
            print(f"Not recognized as a recall query: {args.question}")
            print("\nSupported queries:")
            print("  - What was I doing last time?")
            print("  - What did we work on yesterday?")
            print("  - Remind me where we left off")
            print("  - When did I last work on this?")
            sys.exit(1)

    elif args.command == "save-session":
        recall = get_session_recall()
        success = recall.save_session_state(
            project_id=args.project_id,
            working_on=args.working_on,
            notes=args.notes,
            recent_files=args.files
        )
        if success:
            print(f"Session saved for project {args.project_id}")
        else:
            print("Failed to save session")
            sys.exit(1)

    else:
        parser.print_help()
