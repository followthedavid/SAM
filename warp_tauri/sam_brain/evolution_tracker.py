#!/usr/bin/env python3
"""
SAM Evolution Tracker - Tracks project progress, improvements, and learning.

Provides temporal tracking of all SAM projects, enabling:
- Progress history over time
- Improvement detection and prioritization
- Cross-project relationship mapping
- Feedback-driven learning
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Database location
EVOLUTION_DB = Path(__file__).parent / "evolution.db"
SSOT_PROJECTS = Path("/Volumes/Plex/SSOT/projects")


@dataclass
class Project:
    id: str
    name: str
    category: str  # brain, visual, voice, content, platform
    current_progress: float
    last_updated: str
    ssot_path: str


@dataclass
class Improvement:
    id: str
    project_id: str
    type: str  # efficiency, reliability, feature, integration, documentation
    priority: int  # 1=critical, 2=high, 3=medium
    status: str  # detected, validated, queued, implementing, completed, rejected
    description: str
    detected_at: str
    completed_at: Optional[str] = None
    outcome: Optional[str] = None


@dataclass
class Feedback:
    id: int
    improvement_id: str
    success: bool
    impact_score: float  # 0.0-1.0
    lessons_learned: str
    recorded_at: str


# Improvement type configuration
IMPROVEMENT_TYPES = {
    "efficiency": {"weight": 1.2, "auto_approve": False},
    "reliability": {"weight": 1.5, "auto_approve": True},
    "feature": {"weight": 1.0, "auto_approve": False},
    "integration": {"weight": 1.3, "auto_approve": False},
    "documentation": {"weight": 0.8, "auto_approve": True},
}

# Project category mapping
PROJECT_CATEGORIES = {
    # SAM itself - special category for self-evolution
    "SAM": "sam",
    "SAM_BRAIN": "sam",  # SAM Brain is SAM's core
    # Other brain projects
    "ORCHESTRATOR": "brain",
    "SAM_TERMINAL": "brain",
    "CHARACTER_PIPELINE": "visual",
    "COMFYUI_LORA": "visual",
    "MOTION_PIPELINE": "visual",
    "UNITY_UNREAL": "visual",
    "RVC_VOICE_TRAINING": "voice",
    "STASH_ENHANCEMENT": "content",
    "MEDIA_SERVICES": "content",
    "STASHGRID": "content",
    "GRIDPLAYER": "content",
    "APPLE_ECOSYSTEM": "platform",
    "ACCOUNT_AUTOMATION": "platform",
    "WARP_AUTO": "platform",
    "TOPAZ_PARITY": "visual",
    "REVERSELAB": "platform",
    "SSOT_SYSTEM": "platform",
}


class EvolutionTracker:
    """Tracks project evolution and improvements."""

    def __init__(self, db_path: Path = EVOLUTION_DB):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with self.conn:
            # Projects table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT,
                    current_progress REAL,
                    last_updated TEXT,
                    ssot_path TEXT
                )
            """)

            # Progress history
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS progress_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    progress REAL,
                    milestone TEXT,
                    recorded_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)

            # Improvements
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS improvements (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    type TEXT,
                    priority INTEGER,
                    status TEXT,
                    description TEXT,
                    detected_at TEXT,
                    completed_at TEXT,
                    outcome TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)

            # Cross-project relationships
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_project TEXT,
                    target_project TEXT,
                    relationship_type TEXT,
                    status TEXT,
                    FOREIGN KEY (source_project) REFERENCES projects(id),
                    FOREIGN KEY (target_project) REFERENCES projects(id)
                )
            """)

            # Learning feedback
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    improvement_id TEXT,
                    success INTEGER,
                    impact_score REAL,
                    lessons_learned TEXT,
                    recorded_at TEXT,
                    FOREIGN KEY (improvement_id) REFERENCES improvements(id)
                )
            """)

            # Create indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_progress_project ON progress_history(project_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_improvements_project ON improvements(project_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_improvements_status ON improvements(status)")

    # =====================
    # PROJECT OPERATIONS
    # =====================

    def add_project(self, project: Project) -> str:
        """Add or update a project."""
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO projects (id, name, category, current_progress, last_updated, ssot_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project.id, project.name, project.category, project.current_progress,
                  project.last_updated, project.ssot_path))
        return project.id

    def add_or_update_project(self, project_id: str, name: str, category: str,
                               current_progress: float, ssot_path: str = None) -> str:
        """Convenience method to add/update project from parameters."""
        project = Project(
            id=project_id,
            name=name,
            category=category,
            current_progress=current_progress,
            last_updated=datetime.now().isoformat(),
            ssot_path=ssot_path or ""
        )
        return self.add_project(project)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row:
            return Project(**dict(row))
        return None

    def get_all_projects(self) -> List[Project]:
        """Get all projects."""
        rows = self.conn.execute("SELECT * FROM projects ORDER BY category, name").fetchall()
        return [Project(**dict(row)) for row in rows]

    def update_project_progress(self, project_id: str, progress: float, milestone: str = None, notes: str = None):
        """Update project progress and record history."""
        now = datetime.now().isoformat()

        with self.conn:
            # Update current progress
            self.conn.execute("""
                UPDATE projects SET current_progress = ?, last_updated = ?
                WHERE id = ?
            """, (progress, now, project_id))

            # Record in history
            self.conn.execute("""
                INSERT INTO progress_history (project_id, progress, milestone, recorded_at, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, progress, milestone, now, notes))

    def record_progress(self, project_id: str, progress: float, milestone: str = None, notes: str = None):
        """Alias for update_project_progress."""
        return self.update_project_progress(project_id, progress, milestone, notes)

    def get_progress_history(self, project_id: str, limit: int = 20) -> List[Dict]:
        """Get progress history for a project."""
        rows = self.conn.execute("""
            SELECT * FROM progress_history
            WHERE project_id = ?
            ORDER BY recorded_at DESC
            LIMIT ?
        """, (project_id, limit)).fetchall()
        return [dict(row) for row in rows]

    # =====================
    # IMPROVEMENT OPERATIONS
    # =====================

    def add_improvement(self, improvement: Improvement) -> str:
        """Add a new improvement."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO improvements (id, project_id, type, priority, status, description, detected_at, completed_at, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (improvement.id, improvement.project_id, improvement.type, improvement.priority,
                  improvement.status, improvement.description, improvement.detected_at,
                  improvement.completed_at, improvement.outcome))
        return improvement.id

    def get_improvement(self, improvement_id: str) -> Optional[Improvement]:
        """Get an improvement by ID."""
        row = self.conn.execute(
            "SELECT * FROM improvements WHERE id = ?", (improvement_id,)
        ).fetchone()
        if row:
            return Improvement(**dict(row))
        return None

    def get_improvements_by_status(self, status: str) -> List[Improvement]:
        """Get all improvements with a given status."""
        rows = self.conn.execute(
            "SELECT * FROM improvements WHERE status = ? ORDER BY priority, detected_at",
            (status,)
        ).fetchall()
        return [Improvement(**dict(row)) for row in rows]

    def get_improvements_for_project(self, project_id: str) -> List[Improvement]:
        """Get all improvements for a project."""
        rows = self.conn.execute(
            "SELECT * FROM improvements WHERE project_id = ? ORDER BY status, priority",
            (project_id,)
        ).fetchall()
        return [Improvement(**dict(row)) for row in rows]

    def get_improvements(self, project_id: str = None, status: str = None) -> List[Improvement]:
        """Get improvements with optional filters."""
        query = "SELECT * FROM improvements WHERE 1=1"
        params = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY priority, detected_at"
        rows = self.conn.execute(query, params).fetchall()
        return [Improvement(**dict(row)) for row in rows]

    def update_improvement_status(self, improvement_id: str, status: str, outcome: str = None):
        """Update improvement status."""
        now = datetime.now().isoformat()
        completed_at = now if status == "completed" else None

        with self.conn:
            self.conn.execute("""
                UPDATE improvements
                SET status = ?, outcome = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ?
            """, (status, outcome, completed_at, improvement_id))

    def get_queued_improvements(self, limit: int = 10) -> List[Tuple[Improvement, float]]:
        """Get queued improvements sorted by calculated priority."""
        improvements = self.get_improvements_by_status("queued")
        scored = [(imp, self.calculate_priority(imp)) for imp in improvements]
        scored.sort(key=lambda x: -x[1])  # Higher score = higher priority
        return scored[:limit]

    def calculate_priority(self, improvement: Improvement) -> float:
        """Calculate priority score for an improvement."""
        score = 10.0  # base

        # Type weight
        type_config = IMPROVEMENT_TYPES.get(improvement.type, {"weight": 1.0})
        score *= type_config["weight"]

        # Age factor (older = higher priority, max +10)
        detected = datetime.fromisoformat(improvement.detected_at)
        days_old = (datetime.now() - detected).days
        score += min(days_old * 0.5, 10)

        # Priority factor (1=critical gets boost)
        if improvement.priority == 1:
            score *= 1.5
        elif improvement.priority == 2:
            score *= 1.2

        # Project progress factor (help lagging projects)
        project = self.get_project(improvement.project_id)
        if project and project.current_progress < 0.3:
            score *= 1.3

        return score

    # =====================
    # RELATIONSHIP OPERATIONS
    # =====================

    def add_relationship(self, source: str, target: str, rel_type: str, status: str = "planned"):
        """Add a relationship between projects."""
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO relationships (source_project, target_project, relationship_type, status)
                VALUES (?, ?, ?, ?)
            """, (source, target, rel_type, status))

    def get_relationships(self, project_id: str) -> List[Dict]:
        """Get all relationships for a project."""
        rows = self.conn.execute("""
            SELECT * FROM relationships
            WHERE source_project = ? OR target_project = ?
        """, (project_id, project_id)).fetchall()
        return [dict(row) for row in rows]

    def update_relationship_status(self, source: str, target: str, status: str):
        """Update relationship status."""
        with self.conn:
            self.conn.execute("""
                UPDATE relationships SET status = ?
                WHERE source_project = ? AND target_project = ?
            """, (status, source, target))

    def get_all_relationships(self) -> List:
        """Get all relationships."""
        rows = self.conn.execute("SELECT * FROM relationships").fetchall()
        # Return as simple objects with attributes
        class Rel:
            def __init__(self, row):
                self.source_project = row["source_project"]
                self.target_project = row["target_project"]
                self.relationship_type = row["relationship_type"]
                self.status = row["status"]
        return [Rel(dict(row)) for row in rows]

    # =====================
    # FEEDBACK OPERATIONS
    # =====================

    def record_feedback(self, improvement_id: str, success: bool, impact_score: float, lessons: str):
        """Record feedback for an improvement."""
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO feedback (improvement_id, success, impact_score, lessons_learned, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            """, (improvement_id, int(success), impact_score, lessons, now))

    def get_feedback_for_improvement(self, improvement_id: str) -> List[Feedback]:
        """Get feedback for an improvement."""
        rows = self.conn.execute(
            "SELECT * FROM feedback WHERE improvement_id = ?", (improvement_id,)
        ).fetchall()
        return [Feedback(**dict(row)) for row in rows]

    def get_success_rate_by_type(self) -> Dict[str, float]:
        """Get success rate for each improvement type."""
        rows = self.conn.execute("""
            SELECT i.type,
                   COUNT(*) as total,
                   SUM(CASE WHEN f.success = 1 THEN 1 ELSE 0 END) as successes
            FROM improvements i
            JOIN feedback f ON i.id = f.improvement_id
            GROUP BY i.type
        """).fetchall()

        return {row["type"]: row["successes"] / row["total"] if row["total"] > 0 else 0
                for row in rows}

    # =====================
    # SUMMARY & REPORTING
    # =====================

    def get_project_status_summary(self) -> Dict:
        """Get summary of all projects grouped by category."""
        projects = self.get_all_projects()

        by_category = {}
        for project in projects:
            if project.category not in by_category:
                by_category[project.category] = []
            by_category[project.category].append({
                "name": project.name,
                "progress": project.current_progress,
                "last_updated": project.last_updated
            })

        return {
            "total_projects": len(projects),
            "by_category": by_category,
            "average_progress": sum(p.current_progress for p in projects) / len(projects) if projects else 0
        }

    def get_improvement_summary(self) -> Dict:
        """Get summary of improvements."""
        rows = self.conn.execute("""
            SELECT status, COUNT(*) as count FROM improvements GROUP BY status
        """).fetchall()

        status_counts = {row["status"]: row["count"] for row in rows}

        return {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "queued": status_counts.get("queued", 0),
            "completed": status_counts.get("completed", 0)
        }

    def get_evolution_timeline(self, project_id: str = None) -> List[Dict]:
        """Get evolution timeline for one or all projects."""
        if project_id:
            query = """
                SELECT p.name, h.progress, h.milestone, h.recorded_at, h.notes
                FROM progress_history h
                JOIN projects p ON h.project_id = p.id
                WHERE h.project_id = ?
                ORDER BY h.recorded_at DESC
                LIMIT 50
            """
            rows = self.conn.execute(query, (project_id,)).fetchall()
        else:
            query = """
                SELECT p.name, h.progress, h.milestone, h.recorded_at, h.notes
                FROM progress_history h
                JOIN projects p ON h.project_id = p.id
                ORDER BY h.recorded_at DESC
                LIMIT 100
            """
            rows = self.conn.execute(query).fetchall()

        return [dict(row) for row in rows]

    def get_context_summary(self) -> str:
        """Get a context summary for LLM queries."""
        projects = self.get_all_projects()
        improvements = self.get_improvements(status="detected")

        lines = [f"Total projects: {len(projects)}"]
        for p in projects[:10]:
            lines.append(f"- {p.name}: {p.current_progress*100:.0f}% ({p.category})")

        if improvements:
            lines.append(f"\nPending improvements: {len(improvements)}")
            for imp in improvements[:5]:
                lines.append(f"- [{imp.type}] {imp.description[:50]}")

        return "\n".join(lines)

    def summary(self) -> str:
        """Generate text summary of evolution state."""
        projects = self.get_project_status_summary()
        improvements = self.get_improvement_summary()

        lines = [
            "SAM Evolution Tracker Summary",
            "=" * 40,
            f"Projects: {projects['total_projects']}",
            f"Average Progress: {projects['average_progress']:.1%}",
            "",
            "By Category:",
        ]

        for category, projs in projects["by_category"].items():
            avg = sum(p["progress"] for p in projs) / len(projs)
            lines.append(f"  {category}: {len(projs)} projects, {avg:.1%} avg")

        lines.extend([
            "",
            f"Improvements: {improvements['total']}",
            f"  Queued: {improvements.get('queued', 0)}",
            f"  Completed: {improvements.get('completed', 0)}",
        ])

        return "\n".join(lines)

    # =====================
    # SSOT SYNC
    # =====================

    def sync_from_ssot(self):
        """Sync projects from SSOT markdown files."""
        if not SSOT_PROJECTS.exists():
            return

        for md_file in SSOT_PROJECTS.glob("*.md"):
            project_id = md_file.stem.upper()
            if project_id in PROJECT_CATEGORIES:
                # Parse progress from file (look for patterns like "70%" or "Status: Working")
                content = md_file.read_text()
                progress = self._parse_progress_from_md(content)

                project = Project(
                    id=project_id,
                    name=project_id.replace("_", " ").title(),
                    category=PROJECT_CATEGORIES.get(project_id, "platform"),
                    current_progress=progress,
                    last_updated=datetime.now().isoformat(),
                    ssot_path=str(md_file)
                )
                self.add_project(project)

    def _parse_progress_from_md(self, content: str) -> float:
        """Extract progress percentage from markdown content."""
        import re

        # Look for "X% Built" or "X% Complete"
        match = re.search(r'(\d+)%\s*(built|complete|done)', content.lower())
        if match:
            return int(match.group(1)) / 100.0

        # Count "Working" vs "Pending" in status tables
        working = content.lower().count("working") + content.lower().count("done")
        pending = content.lower().count("pending") + content.lower().count("planned")
        total = working + pending
        if total > 0:
            return working / total

        return 0.5  # Default to 50% if can't determine

    def __del__(self):
        """Clean up database connection."""
        try:
            self.conn.close()
        except:
            pass


def generate_improvement_id(project_id: str, description: str) -> str:
    """Generate unique improvement ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_input = f"{project_id}:{description}:{timestamp}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"imp_{timestamp}_{short_hash}"


# CLI interface
if __name__ == "__main__":
    import sys

    tracker = EvolutionTracker()

    if len(sys.argv) < 2:
        print(tracker.summary())
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "sync":
        tracker.sync_from_ssot()
        print("Synced from SSOT")
        print(tracker.summary())

    elif cmd == "projects":
        for project in tracker.get_all_projects():
            print(f"{project.id}: {project.current_progress:.1%} ({project.category})")

    elif cmd == "improvements":
        status = sys.argv[2] if len(sys.argv) > 2 else "queued"
        for imp in tracker.get_improvements_by_status(status):
            print(f"[{imp.priority}] {imp.id}: {imp.description[:60]}...")

    elif cmd == "timeline":
        project_id = sys.argv[2] if len(sys.argv) > 2 else None
        for entry in tracker.get_evolution_timeline(project_id):
            print(f"{entry['recorded_at']}: {entry['name']} @ {entry['progress']:.1%}")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: evolution_tracker.py [sync|projects|improvements|timeline]")
