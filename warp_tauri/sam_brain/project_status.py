#!/usr/bin/env python3
"""
SAM Project Status Generator

Generates rich, project-specific status for:
1. UI display on project pages (not just placeholder checkboxes)
2. LLM consumption when user asks "what's up with X?"

Each project gets a living dashboard showing:
- Evolution level with specific criteria progress
- Recent activity (what SAM actually did, not approvals)
- Timeline of improvements and milestones
- Integration health with other projects
- Next steps and blockers
- Learnings from feedback loops
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass, field, asdict

# Import our existing modules
try:
    from evolution_tracker import EvolutionTracker
    from evolution_ladders import (
        EVOLUTION_LADDERS, get_project_category,
        assess_project_level, get_next_milestone
    )
    from improvement_detector import ImprovementDetector
    from semantic_memory import SemanticMemory
except ImportError:
    # Graceful fallback for standalone testing
    EvolutionTracker = None
    EVOLUTION_LADDERS = {}


@dataclass
class CriteriaStatus:
    """Status of a single evolution criteria"""
    name: str
    description: str
    met: bool
    progress: float  # 0.0 to 1.0
    evidence: str  # What proves this criteria is met/not met


@dataclass
class LevelProgress:
    """Progress within current evolution level"""
    current_level: int
    level_name: str
    criteria_met: int
    criteria_total: int
    criteria_details: List[CriteriaStatus]
    progress_percent: float
    next_level_name: str
    blocking_criteria: List[str]


@dataclass
class RecentActivity:
    """A single activity entry"""
    timestamp: float
    action: str  # "improved", "detected", "learned", "integrated", "fixed"
    description: str
    impact: str  # "minor", "moderate", "significant"
    details: Optional[dict] = None


@dataclass
class IntegrationLink:
    """Status of integration with another project"""
    target_project: str
    relationship: str  # "depends_on", "enables", "integrates_with"
    status: str  # "connected", "planned", "blocked", "partial"
    health: str  # "healthy", "degraded", "broken", "unknown"
    last_sync: Optional[float] = None
    notes: str = ""


@dataclass
class ProjectHealth:
    """Overall health indicators"""
    overall: str  # "excellent", "good", "needs_attention", "critical"
    test_status: str  # "passing", "failing", "no_tests", "unknown"
    error_rate: float  # Recent errors per hour
    performance: str  # "fast", "normal", "slow", "unknown"
    last_active: float
    uptime_percent: float


@dataclass
class ProjectStatus:
    """Complete status for a single project"""
    project_id: str
    name: str
    category: str

    # Evolution
    level_progress: LevelProgress
    evolution_timeline: List[dict]  # Historical level changes

    # Activity
    recent_activities: List[RecentActivity]
    improvements_completed: int
    improvements_pending: int

    # Integrations
    integrations: List[IntegrationLink]

    # Health
    health: ProjectHealth

    # Learnings
    lessons_learned: List[str]
    success_patterns: List[str]

    # Next steps
    next_milestone: str
    suggested_actions: List[str]
    blockers: List[str]

    # Meta
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_llm_summary(self) -> str:
        """
        Generate a natural language summary for LLM consumption.
        This is what SAM reads when you ask "what's up with X?"
        """
        lines = []

        # Header
        lines.append(f"## {self.name} Status Report")
        lines.append(f"Category: {self.category} | Generated: {datetime.fromtimestamp(self.generated_at).strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        # Evolution Level
        lp = self.level_progress
        lines.append(f"### Evolution: Level {lp.current_level} - {lp.level_name}")
        lines.append(f"Progress: {lp.progress_percent:.0f}% ({lp.criteria_met}/{lp.criteria_total} criteria met)")

        if lp.blocking_criteria:
            lines.append(f"Blocking: {', '.join(lp.blocking_criteria)}")
        lines.append(f"Next level: {lp.next_level_name}")
        lines.append("")

        # Recent Activity
        if self.recent_activities:
            lines.append("### Recent Activity")
            for act in self.recent_activities[:5]:
                ts = datetime.fromtimestamp(act.timestamp).strftime("%m/%d")
                impact_icon = {"minor": "·", "moderate": "•", "significant": "★"}.get(act.impact, "·")
                lines.append(f"  {impact_icon} [{ts}] {act.action}: {act.description}")
            lines.append("")

        # Health
        health_icons = {
            "excellent": "🟢", "good": "🟡",
            "needs_attention": "🟠", "critical": "🔴"
        }
        lines.append(f"### Health: {health_icons.get(self.health.overall, '⚪')} {self.health.overall.title()}")
        lines.append(f"Tests: {self.health.test_status} | Performance: {self.health.performance}")
        lines.append("")

        # Integrations
        if self.integrations:
            lines.append("### Integrations")
            for link in self.integrations:
                status_icon = {
                    "connected": "✓", "partial": "◐",
                    "planned": "○", "blocked": "✗"
                }.get(link.status, "?")
                lines.append(f"  {status_icon} {link.target_project} ({link.relationship}): {link.status}")
            lines.append("")

        # Improvements
        lines.append(f"### Improvements: {self.improvements_completed} completed, {self.improvements_pending} pending")
        lines.append("")

        # Lessons Learned
        if self.lessons_learned:
            lines.append("### What We've Learned")
            for lesson in self.lessons_learned[:3]:
                lines.append(f"  • {lesson}")
            lines.append("")

        # Next Steps
        lines.append("### Next Steps")
        if self.next_milestone:
            lines.append(f"  Milestone: {self.next_milestone}")
        if self.suggested_actions:
            for action in self.suggested_actions[:3]:
                lines.append(f"  → {action}")
        if self.blockers:
            lines.append("  Blockers:")
            for blocker in self.blockers:
                lines.append(f"    ⚠ {blocker}")

        return "\n".join(lines)


class ProjectStatusGenerator:
    """
    Generates rich project status by combining data from:
    - evolution_tracker (progress history)
    - evolution_ladders (level assessment)
    - improvement_detector (recent improvements)
    - semantic_memory (learnings)
    """

    def __init__(self):
        self.tracker = EvolutionTracker() if EvolutionTracker else None
        self.memory = SemanticMemory() if 'SemanticMemory' in dir() else None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def get_project_status(
        self,
        project_id: str,
        force_refresh: bool = False
    ) -> Optional[ProjectStatus]:
        """
        Get complete status for a project.

        This is the main method - call this to get everything
        needed for a project page or LLM summary.
        """
        # Check cache
        cache_key = f"status_{project_id}"
        if not force_refresh and cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached

        # Get base project info
        project = self._get_project_info(project_id)
        if not project:
            return None

        # Build complete status
        status = ProjectStatus(
            project_id=project_id,
            name=project.get("name", project_id),
            category=project.get("category", "unknown"),
            level_progress=self._get_level_progress(project_id, project.get("category")),
            evolution_timeline=self._get_evolution_timeline(project_id),
            recent_activities=self._get_recent_activities(project_id),
            improvements_completed=self._count_improvements(project_id, "completed"),
            improvements_pending=self._count_improvements(project_id, "pending"),
            integrations=self._get_integrations(project_id),
            health=self._get_health(project_id),
            lessons_learned=self._get_lessons(project_id),
            success_patterns=self._get_success_patterns(project_id),
            next_milestone=self._get_next_milestone(project_id, project.get("category")),
            suggested_actions=self._get_suggested_actions(project_id),
            blockers=self._get_blockers(project_id)
        )

        # Cache it
        self._cache[cache_key] = (status, time.time())

        return status

    def get_all_projects_summary(self) -> List[dict]:
        """Get summary status for all projects (for dashboard)"""
        if not self.tracker:
            return []

        projects = self.tracker.get_all_projects()
        summaries = []

        for p in projects:
            status = self.get_project_status(p["id"])
            if status:
                summaries.append({
                    "id": p["id"],
                    "name": status.name,
                    "category": status.category,
                    "level": status.level_progress.current_level,
                    "level_name": status.level_progress.level_name,
                    "progress": status.level_progress.progress_percent,
                    "health": status.health.overall,
                    "pending": status.improvements_pending
                })

        return summaries

    def get_llm_context(self, project_id: str) -> str:
        """
        Get project status formatted for LLM consumption.

        Call this when user asks "what's happening with X?"
        """
        status = self.get_project_status(project_id)
        if not status:
            return f"No status available for project: {project_id}"

        return status.to_llm_summary()

    def get_quick_status(self, project_id: str) -> dict:
        """
        Get minimal status for quick display (status bar, etc.)
        """
        status = self.get_project_status(project_id)
        if not status:
            return {"error": "Project not found"}

        return {
            "name": status.name,
            "level": status.level_progress.current_level,
            "level_name": status.level_progress.level_name,
            "progress": status.level_progress.progress_percent,
            "health": status.health.overall,
            "next": status.next_milestone,
            "pending": status.improvements_pending
        }

    # ═══════════════════════════════════════════════════════════════════════
    # Private helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _get_project_info(self, project_id: str) -> Optional[dict]:
        """Get base project info from tracker"""
        if not self.tracker:
            # Fallback: use known project list
            return {"id": project_id, "name": project_id, "category": "unknown"}

        return self.tracker.get_project(project_id)

    def _get_level_progress(self, project_id: str, category: str) -> LevelProgress:
        """Calculate detailed level progress"""
        # Get ladder for this category
        ladder = EVOLUTION_LADDERS.get(category, EVOLUTION_LADDERS.get("brain", []))

        # Assess current level (would come from evolution_ladders.assess_project_level)
        current_level = 1
        criteria_results = []

        if self.tracker:
            assessment = self.tracker.get_project_assessment(project_id)
            if assessment:
                current_level = assessment.get("level", 1)
                criteria_results = assessment.get("criteria", [])

        # Build criteria status
        level_def = ladder[current_level - 1] if current_level <= len(ladder) else ladder[-1]
        criteria_details = []

        for criterion in level_def.get("criteria", []):
            # Check if this criterion is met
            result = next((c for c in criteria_results if c.get("name") == criterion), None)
            criteria_details.append(CriteriaStatus(
                name=criterion,
                description=self._get_criterion_description(criterion),
                met=result.get("met", False) if result else False,
                progress=result.get("progress", 0.0) if result else 0.0,
                evidence=result.get("evidence", "") if result else ""
            ))

        criteria_met = sum(1 for c in criteria_details if c.met)
        criteria_total = len(criteria_details)

        # Next level
        next_level = ladder[current_level] if current_level < len(ladder) else None
        next_level_name = next_level.get("name", "Mastery") if next_level else "Max Level"

        # Blocking criteria
        blocking = [c.name for c in criteria_details if not c.met]

        return LevelProgress(
            current_level=current_level,
            level_name=level_def.get("name", f"Level {current_level}"),
            criteria_met=criteria_met,
            criteria_total=criteria_total,
            criteria_details=criteria_details,
            progress_percent=(criteria_met / criteria_total * 100) if criteria_total > 0 else 0,
            next_level_name=next_level_name,
            blocking_criteria=blocking[:3]  # Top 3 blockers
        )

    def _get_criterion_description(self, criterion: str) -> str:
        """Get human-readable description for a criterion"""
        descriptions = {
            "responds_to_queries": "Can respond to basic user queries",
            "routes_correctly": "Routes requests to appropriate handlers",
            "stores_interactions": "Persists conversation history",
            "retrieves_context": "Pulls relevant context from memory",
            "confidence_scoring": "Rates confidence in responses",
            "escalation": "Escalates uncertain responses appropriately",
            "auto_training": "Improves from interaction feedback",
            "self_improvement": "Identifies and implements improvements",
            "cross_project_optimization": "Optimizes across multiple projects",
            "proactive_suggestions": "Suggests improvements without prompting",
            "basic_image_gen": "Generates images from prompts",
            "lora_support": "Supports LoRA for style consistency",
            "character_consistency": "Maintains character appearance across images",
            "pose_control": "Controls character poses accurately",
            "automated_workflow": "Runs generation workflows automatically",
            "batch_processing": "Processes multiple images in batch",
            "quality_control": "Validates output quality automatically",
            "asset_management": "Organizes and tracks generated assets",
        }
        return descriptions.get(criterion, criterion.replace("_", " ").title())

    def _get_evolution_timeline(self, project_id: str) -> List[dict]:
        """Get historical evolution events"""
        if not self.tracker:
            return []

        history = self.tracker.get_progress_history(project_id, limit=20)
        return [
            {
                "timestamp": h.get("recorded_at"),
                "level": h.get("level"),
                "milestone": h.get("milestone"),
                "notes": h.get("notes")
            }
            for h in history
        ]

    def _get_recent_activities(self, project_id: str) -> List[RecentActivity]:
        """Get recent activities for this project"""
        activities = []

        if self.tracker:
            # Get improvements
            improvements = self.tracker.get_improvements(
                project_id=project_id,
                status=["completed", "implementing"],
                limit=10
            )

            for imp in improvements:
                activities.append(RecentActivity(
                    timestamp=imp.get("completed_at") or imp.get("detected_at", time.time()),
                    action="improved" if imp.get("status") == "completed" else "implementing",
                    description=imp.get("description", "Unknown improvement"),
                    impact=self._priority_to_impact(imp.get("priority", 3)),
                    details={"type": imp.get("type"), "id": imp.get("id")}
                ))

        # Sort by timestamp descending
        activities.sort(key=lambda a: a.timestamp, reverse=True)
        return activities[:10]

    def _priority_to_impact(self, priority: int) -> str:
        """Convert priority number to impact level"""
        if priority == 1:
            return "significant"
        elif priority == 2:
            return "moderate"
        return "minor"

    def _count_improvements(self, project_id: str, status: str) -> int:
        """Count improvements by status"""
        if not self.tracker:
            return 0

        if status == "pending":
            statuses = ["detected", "validated", "queued"]
        elif status == "completed":
            statuses = ["completed"]
        else:
            statuses = [status]

        improvements = self.tracker.get_improvements(
            project_id=project_id,
            status=statuses,
            limit=1000
        )
        return len(improvements)

    def _get_integrations(self, project_id: str) -> List[IntegrationLink]:
        """Get integration status with other projects"""
        if not self.tracker:
            return []

        relationships = self.tracker.get_relationships(project_id)
        return [
            IntegrationLink(
                target_project=r.get("target_project"),
                relationship=r.get("relationship_type"),
                status=r.get("status", "unknown"),
                health=r.get("health", "unknown"),
                last_sync=r.get("last_sync"),
                notes=r.get("notes", "")
            )
            for r in relationships
        ]

    def _get_health(self, project_id: str) -> ProjectHealth:
        """Calculate project health indicators"""
        # Default health (would be populated from actual metrics)
        return ProjectHealth(
            overall="good",
            test_status="unknown",
            error_rate=0.0,
            performance="unknown",
            last_active=time.time(),
            uptime_percent=99.0
        )

    def _get_lessons(self, project_id: str) -> List[str]:
        """Get lessons learned for this project"""
        if not self.memory:
            return []

        # Query semantic memory for feedback/lessons
        results = self.memory.search(
            f"project:{project_id} lesson learned feedback",
            tags=["improvement", "feedback"],
            limit=5
        )

        return [r.get("content", "")[:100] for r in results]

    def _get_success_patterns(self, project_id: str) -> List[str]:
        """Get patterns that worked well"""
        if not self.tracker:
            return []

        # Get high-impact completed improvements
        feedback = self.tracker.get_feedback(project_id, success_only=True, limit=5)
        return [f.get("lessons_learned", "") for f in feedback if f.get("lessons_learned")]

    def _get_next_milestone(self, project_id: str, category: str) -> str:
        """Get the next milestone for this project"""
        status = self._get_level_progress(project_id, category)

        if status.blocking_criteria:
            return f"Complete: {status.blocking_criteria[0]}"

        return f"Reach Level {status.current_level + 1}: {status.next_level_name}"

    def _get_suggested_actions(self, project_id: str) -> List[str]:
        """Get suggested next actions"""
        actions = []

        if self.tracker:
            # Get pending improvements
            pending = self.tracker.get_improvements(
                project_id=project_id,
                status=["detected", "validated", "queued"],
                limit=3
            )

            for imp in pending:
                actions.append(f"{imp.get('type', 'improve').title()}: {imp.get('description', 'Unknown')[:50]}")

        return actions or ["No pending improvements - project is stable"]

    def _get_blockers(self, project_id: str) -> List[str]:
        """Get current blockers"""
        blockers = []

        if self.tracker:
            # Check for blocked integrations
            relationships = self.tracker.get_relationships(project_id)
            for r in relationships:
                if r.get("status") == "blocked":
                    blockers.append(f"Integration with {r.get('target_project')} is blocked")

            # Check for rejected improvements
            rejected = self.tracker.get_improvements(
                project_id=project_id,
                status=["rejected"],
                limit=3
            )
            for imp in rejected:
                if imp.get("outcome"):
                    blockers.append(imp.get("outcome")[:50])

        return blockers


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    generator = ProjectStatusGenerator()

    if len(sys.argv) < 2:
        print("SAM Project Status Generator")
        print("\nGenerates rich project status for UI and LLM consumption.")
        print("\nUsage:")
        print("  python project_status.py status <project_id>  # Full status")
        print("  python project_status.py summary <project_id> # LLM summary")
        print("  python project_status.py quick <project_id>   # Quick status")
        print("  python project_status.py all                  # All projects summary")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: python project_status.py status <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        status = generator.get_project_status(project_id)

        if status:
            print(json.dumps(status.to_dict(), indent=2, default=str))
        else:
            print(f"Project not found: {project_id}")

    elif cmd == "summary":
        if len(sys.argv) < 3:
            print("Usage: python project_status.py summary <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        summary = generator.get_llm_context(project_id)
        print(summary)

    elif cmd == "quick":
        if len(sys.argv) < 3:
            print("Usage: python project_status.py quick <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        quick = generator.get_quick_status(project_id)

        print(f"\n{quick.get('name', project_id)}")
        print(f"  Level: {quick.get('level')} - {quick.get('level_name')}")
        print(f"  Progress: {quick.get('progress', 0):.0f}%")
        print(f"  Health: {quick.get('health')}")
        print(f"  Next: {quick.get('next')}")
        print(f"  Pending: {quick.get('pending')} improvements")

    elif cmd == "all":
        summaries = generator.get_all_projects_summary()

        print("\n📊 All Projects Status\n")
        for s in summaries:
            health_icon = {
                "excellent": "🟢", "good": "🟡",
                "needs_attention": "🟠", "critical": "🔴"
            }.get(s.get("health"), "⚪")

            print(f"  {health_icon} {s.get('name')}")
            print(f"     Level {s.get('level')}: {s.get('level_name')} ({s.get('progress', 0):.0f}%)")
            if s.get("pending", 0) > 0:
                print(f"     {s.get('pending')} pending improvements")
            print()

    else:
        print(f"Unknown command: {cmd}")
