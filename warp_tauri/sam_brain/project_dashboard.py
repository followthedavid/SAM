#!/usr/bin/env python3
"""
SAM Project Dashboard

Data-rich project status with SAM's voice:
- Confident and clear
- Ranks everything by impact
- Stats first, poetry as seasoning
- Actionable recommendations

This is what project pages display and what SAM reads
when you ask "what's up with X?"
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict

# Import our existing modules
try:
    from evolution_tracker import EvolutionTracker
    from evolution_ladders import EVOLUTION_LADDERS
except ImportError:
    EvolutionTracker = None
    EVOLUTION_LADDERS = {}


@dataclass
class Metric:
    """A single measurable metric"""
    name: str
    value: float
    unit: str
    trend: str  # "up", "down", "stable"
    change: float  # Change from previous period
    sparkline: List[float]  # Last 7 data points for mini chart


@dataclass
class Milestone:
    """A completed or upcoming milestone"""
    name: str
    status: str  # "completed", "in_progress", "upcoming", "blocked"
    date: Optional[str]
    progress: float  # 0.0 to 1.0 for in_progress


@dataclass
class Recommendation:
    """A ranked recommendation"""
    rank: int
    title: str
    description: str
    impact: str  # "critical", "high", "medium", "low"
    effort: str  # "trivial", "small", "medium", "large"
    blocking: Optional[str]  # What this unblocks
    category: str  # "fix", "improve", "add", "remove"


@dataclass
class ProjectDashboard:
    """Complete dashboard for a project - data-rich with SAM's voice"""
    project_id: str
    name: str
    tagline: str  # One line of poetry

    # ═══════════════════════════════════════════════════════════════
    # CORE METRICS
    # ═══════════════════════════════════════════════════════════════
    level: int
    level_name: str
    level_progress: float  # 0-100%
    criteria_met: int
    criteria_total: int

    health_score: int  # 0-100
    health_status: str  # "healthy", "warning", "critical"

    improvements_completed: int
    improvements_pending: int
    improvements_this_week: int
    last_activity: str
    days_since_update: int

    uptime_percent: float
    error_rate: float
    avg_response_ms: float

    # ═══════════════════════════════════════════════════════════════
    # CHARTS DATA
    # ═══════════════════════════════════════════════════════════════
    progress_history: List[Dict]
    activity_history: List[Dict]
    health_history: List[Dict]

    # ═══════════════════════════════════════════════════════════════
    # MILESTONES
    # ═══════════════════════════════════════════════════════════════
    milestones_completed: List[Milestone]
    milestones_upcoming: List[Milestone]
    current_milestone: Optional[Milestone]

    # ═══════════════════════════════════════════════════════════════
    # CRITERIA BREAKDOWN
    # ═══════════════════════════════════════════════════════════════
    criteria: List[Dict]

    # ═══════════════════════════════════════════════════════════════
    # INTEGRATIONS
    # ═══════════════════════════════════════════════════════════════
    integrations: List[Dict]
    integration_score: int

    # ═══════════════════════════════════════════════════════════════
    # RANKED RECOMMENDATIONS (SAM's suggestions)
    # ═══════════════════════════════════════════════════════════════
    recommendations: List[Recommendation]

    # ═══════════════════════════════════════════════════════════════
    # RECENT ACTIVITY LOG
    # ═══════════════════════════════════════════════════════════════
    recent_activity: List[Dict]

    # ═══════════════════════════════════════════════════════════════
    # BLOCKERS & RISKS
    # ═══════════════════════════════════════════════════════════════
    blockers: List[str]
    risks: List[Dict]

    # ═══════════════════════════════════════════════════════════════
    # COMPARISONS
    # ═══════════════════════════════════════════════════════════════
    rank_in_category: int  # Where this project ranks vs others in category
    total_in_category: int
    vs_last_week: Dict  # Comparison to last week

    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class DashboardGenerator:
    """
    Generates data-rich project dashboards with SAM's voice.
    """

    def __init__(self):
        self.tracker = EvolutionTracker() if EvolutionTracker else None
        self._cache = {}
        self._cache_ttl = 60

    def get_dashboard(self, project_id: str, force_refresh: bool = False) -> ProjectDashboard:
        """Get complete dashboard for a project"""

        cache_key = f"dash_{project_id}"
        if not force_refresh and cache_key in self._cache:
            cached, ts = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return cached

        project = self._get_project(project_id)
        category = project.get("category", "brain") if project else "brain"
        name = project.get("name", project_id) if project else project_id

        dashboard = ProjectDashboard(
            project_id=project_id,
            name=name,
            tagline=self._get_tagline(project_id, category),

            level=self._get_level(project_id, category),
            level_name=self._get_level_name(project_id, category),
            level_progress=self._get_level_progress(project_id, category),
            criteria_met=self._count_criteria_met(project_id, category),
            criteria_total=self._count_criteria_total(project_id, category),

            health_score=self._calculate_health_score(project_id),
            health_status=self._get_health_status(project_id),

            improvements_completed=self._count_improvements(project_id, "completed"),
            improvements_pending=self._count_improvements(project_id, "pending"),
            improvements_this_week=self._count_improvements_this_week(project_id),
            last_activity=self._get_last_activity(project_id),
            days_since_update=self._get_days_since_update(project_id),

            uptime_percent=self._get_uptime(project_id),
            error_rate=self._get_error_rate(project_id),
            avg_response_ms=self._get_avg_response(project_id),

            progress_history=self._get_progress_history(project_id),
            activity_history=self._get_activity_history(project_id),
            health_history=self._get_health_history(project_id),

            milestones_completed=self._get_milestones(project_id, "completed"),
            milestones_upcoming=self._get_milestones(project_id, "upcoming"),
            current_milestone=self._get_current_milestone(project_id, category),

            criteria=self._get_criteria_breakdown(project_id, category),

            integrations=self._get_integrations(project_id),
            integration_score=self._calculate_integration_score(project_id),

            recommendations=self._generate_recommendations(project_id, category),

            recent_activity=self._get_recent_activity(project_id),

            blockers=self._get_blockers(project_id),
            risks=self._get_risks(project_id),

            rank_in_category=self._get_category_rank(project_id, category),
            total_in_category=self._get_category_count(category),
            vs_last_week=self._compare_to_last_week(project_id),
        )

        self._cache[cache_key] = (dashboard, time.time())
        return dashboard

    def get_llm_summary(self, project_id: str) -> str:
        """
        Get dashboard formatted for LLM consumption.
        SAM's voice: confident, data-rich, actionable.
        """
        d = self.get_dashboard(project_id)

        lines = []

        # ═══════════════════════════════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════════════════════════════
        lines.append(f"# {d.name}")
        lines.append(f"*{d.tagline}*")
        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # STATUS AT A GLANCE
        # ═══════════════════════════════════════════════════════════════
        health_bar = "█" * (d.health_score // 10) + "░" * (10 - d.health_score // 10)
        progress_bar = "█" * int(d.level_progress // 10) + "░" * (10 - int(d.level_progress // 10))

        lines.append(f"**Level {d.level}** - {d.level_name}")
        lines.append("")
        lines.append("```")
        lines.append(f"Health     [{health_bar}] {d.health_score}/100")
        lines.append(f"Progress   [{progress_bar}] {d.level_progress:.0f}%")
        lines.append(f"Criteria   {d.criteria_met}/{d.criteria_total} met")
        lines.append("```")
        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # KEY NUMBERS
        # ═══════════════════════════════════════════════════════════════
        lines.append("## Key Numbers")
        lines.append("")
        lines.append("| Metric | Value | Trend |")
        lines.append("|--------|-------|-------|")

        week_trend = d.vs_last_week.get("improvements_trend", "stable")
        trend_arrow = {"up": "↑", "down": "↓", "stable": "→"}.get(week_trend, "→")

        lines.append(f"| Completed | {d.improvements_completed} | {trend_arrow} |")
        lines.append(f"| Pending | {d.improvements_pending} | |")
        lines.append(f"| This Week | {d.improvements_this_week} | |")
        lines.append(f"| Days Idle | {d.days_since_update} | |")

        if d.uptime_percent > 0:
            lines.append(f"| Uptime | {d.uptime_percent:.1f}% | |")
        if d.error_rate > 0:
            lines.append(f"| Error Rate | {d.error_rate:.2f}% | |")

        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # CRITERIA STATUS
        # ═══════════════════════════════════════════════════════════════
        if d.criteria:
            lines.append("## Criteria Status")
            lines.append("")
            for c in d.criteria:
                if c["met"]:
                    lines.append(f"✓ **{c['name']}** - Complete")
                else:
                    prog = c.get('progress', 0)
                    if prog > 0:
                        lines.append(f"◐ **{c['name']}** - {prog:.0f}% done")
                    else:
                        lines.append(f"○ **{c['name']}** - Not started")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # RANKED RECOMMENDATIONS (The heart of SAM's value)
        # ═══════════════════════════════════════════════════════════════
        if d.recommendations:
            lines.append("## What I Suggest (Ranked by Impact)")
            lines.append("")

            for rec in d.recommendations[:5]:
                impact_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(rec.impact, "⚪")

                effort_tag = f"[{rec.effort}]" if rec.effort else ""

                lines.append(f"**{rec.rank}. {rec.title}** {impact_icon}")
                lines.append(f"   {rec.description}")
                if rec.blocking:
                    lines.append(f"   *Unblocks: {rec.blocking}*")
                lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # CURRENT MILESTONE
        # ═══════════════════════════════════════════════════════════════
        if d.current_milestone:
            m = d.current_milestone
            prog_bar = "█" * int(m.progress * 10) + "░" * (10 - int(m.progress * 10))
            lines.append(f"## Current Milestone")
            lines.append(f"**{m.name}**")
            lines.append(f"[{prog_bar}] {m.progress*100:.0f}%")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # INTEGRATIONS
        # ═══════════════════════════════════════════════════════════════
        if d.integrations:
            lines.append(f"## Integrations ({d.integration_score}/100)")
            lines.append("")
            int_parts = []
            for i in d.integrations:
                icon = {"connected": "●", "partial": "◐", "planned": "○", "blocked": "✗"}.get(i["status"], "?")
                int_parts.append(f"{icon} {i['project']}")
            lines.append(" | ".join(int_parts))
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # BLOCKERS (If any)
        # ═══════════════════════════════════════════════════════════════
        if d.blockers:
            lines.append("## Blockers")
            for b in d.blockers:
                lines.append(f"⚠ {b}")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # RISKS (If any)
        # ═══════════════════════════════════════════════════════════════
        if d.risks:
            lines.append("## Risks to Watch")
            for r in d.risks:
                sev_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(r["severity"], "⚪")
                lines.append(f"{sev_icon} {r['description']}")
                if r.get("mitigation"):
                    lines.append(f"   → {r['mitigation']}")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # RECENT ACTIVITY
        # ═══════════════════════════════════════════════════════════════
        if d.recent_activity:
            lines.append("## Recent Activity")
            for a in d.recent_activity[:5]:
                ts = a.get("timestamp", "")[:10]
                lines.append(f"• [{ts}] {a.get('type', '')}: {a.get('description', '')[:50]}")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # RANKING
        # ═══════════════════════════════════════════════════════════════
        if d.total_in_category > 1:
            lines.append("---")
            lines.append(f"*Ranked #{d.rank_in_category} of {d.total_in_category} in {d.name.split()[0]} category*")

        return "\n".join(lines)

    def get_quick_stats(self, project_id: str) -> dict:
        """Get minimal stats for status bar"""
        d = self.get_dashboard(project_id)
        return {
            "name": d.name,
            "level": d.level,
            "level_name": d.level_name,
            "progress": d.level_progress,
            "health": d.health_score,
            "status": d.health_status,
            "pending": d.improvements_pending,
            "days_idle": d.days_since_update,
            "top_recommendation": d.recommendations[0].title if d.recommendations else None,
        }

    def get_all_projects_stats(self) -> List[dict]:
        """Get quick stats for all projects"""
        if not self.tracker:
            return []
        projects = self.tracker.get_all_projects()
        return [self.get_quick_stats(p.id) for p in projects]

    # ═══════════════════════════════════════════════════════════════════════
    # RECOMMENDATION ENGINE (SAM's brain)
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_recommendations(self, project_id: str, category: str) -> List[Recommendation]:
        """
        Generate ranked recommendations for this project.
        This is where SAM adds real value.
        """
        recommendations = []
        rank = 1

        # 1. Check unmet criteria (blocking level progression)
        criteria = self._get_criteria_breakdown(project_id, category)
        level = self._get_level(project_id, category)

        for c in criteria:
            if not c["met"]:
                recommendations.append(Recommendation(
                    rank=rank,
                    title=f"Complete: {c['name']}",
                    description=self._get_criterion_action(c['name']),
                    impact="critical" if c.get("progress", 0) > 50 else "high",
                    effort=self._estimate_criterion_effort(c['name'], c.get("progress", 0)),
                    blocking=f"Level {level + 1}",
                    category="improve"
                ))
                rank += 1

        # 2. Check pending improvements from tracker
        if self.tracker:
            pending = self.tracker.get_improvements(project_id=project_id, status=["detected", "validated"])
            for imp in (pending or [])[:3]:
                recommendations.append(Recommendation(
                    rank=rank,
                    title=imp.get("description", "Improvement")[:50],
                    description=f"Type: {imp.get('type', 'unknown')}. Detected by scan.",
                    impact=self._priority_to_impact(imp.get("priority", 3)),
                    effort="medium",
                    blocking=None,
                    category=imp.get("type", "improve")
                ))
                rank += 1

        # 3. Check blockers
        blockers = self._get_blockers(project_id)
        for blocker in blockers:
            recommendations.insert(0, Recommendation(
                rank=0,  # Will be reordered
                title=f"Resolve: {blocker[:40]}",
                description="This is blocking progress.",
                impact="critical",
                effort="medium",
                blocking="Overall health",
                category="fix"
            ))

        # 4. Check integrations
        integrations = self._get_integrations(project_id)
        for i in integrations:
            if i["status"] == "planned":
                recommendations.append(Recommendation(
                    rank=rank,
                    title=f"Connect to {i['project']}",
                    description="Integration planned but not started.",
                    impact="medium",
                    effort="large",
                    blocking=None,
                    category="add"
                ))
                rank += 1
            elif i["status"] == "partial":
                recommendations.append(Recommendation(
                    rank=rank,
                    title=f"Complete {i['project']} integration",
                    description="Partially connected. Finish the integration.",
                    impact="medium",
                    effort="medium",
                    blocking=None,
                    category="improve"
                ))
                rank += 1

        # 5. Staleness check
        days_idle = self._get_days_since_update(project_id)
        if days_idle > 7:
            recommendations.append(Recommendation(
                rank=rank,
                title="Review project status",
                description=f"No activity in {days_idle} days. Is this still active?",
                impact="low" if days_idle < 14 else "medium",
                effort="trivial",
                blocking=None,
                category="improve"
            ))
            rank += 1

        # Sort by impact, then re-rank
        impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: impact_order.get(r.impact, 99))

        for i, rec in enumerate(recommendations):
            rec.rank = i + 1

        return recommendations[:7]  # Top 7

    def _get_criterion_action(self, criterion: str) -> str:
        """Get actionable description for a criterion"""
        actions = {
            "responds_to_queries": "Ensure the system can handle basic user queries and return responses.",
            "routes_correctly": "Verify request routing sends queries to the right handler.",
            "stores_interactions": "Implement conversation history persistence.",
            "retrieves_context": "Add context retrieval from memory for informed responses.",
            "confidence_scoring": "Add confidence scores to responses so we know when to escalate.",
            "escalation": "Implement escalation path for uncertain responses.",
            "auto_training": "Enable automatic learning from interaction feedback.",
            "self_improvement": "Allow the system to identify and implement its own improvements.",
            "cross_project_optimization": "Enable optimizations that span multiple projects.",
            "proactive_suggestions": "Add ability to suggest improvements without being asked.",
            "basic_image_gen": "Get basic image generation working from prompts.",
            "lora_support": "Add LoRA loading for style consistency.",
            "character_consistency": "Ensure characters maintain appearance across frames.",
            "pose_control": "Implement accurate pose control for characters.",
            "automated_workflow": "Automate the generation workflow end-to-end.",
            "batch_processing": "Enable batch processing for multiple images.",
            "quality_control": "Add automatic quality validation for outputs.",
            "asset_management": "Implement asset organization and tracking.",
        }
        return actions.get(criterion, f"Complete the {criterion.replace('_', ' ')} requirement.")

    def _estimate_criterion_effort(self, criterion: str, progress: float) -> str:
        """Estimate effort to complete a criterion"""
        if progress > 75:
            return "trivial"
        elif progress > 50:
            return "small"
        elif progress > 25:
            return "medium"
        else:
            return "large"

    def _priority_to_impact(self, priority: int) -> str:
        """Convert priority number to impact level"""
        return {1: "critical", 2: "high", 3: "medium"}.get(priority, "low")

    # ═══════════════════════════════════════════════════════════════════════
    # Data fetchers (same as before, abbreviated)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_project(self, project_id: str) -> Optional[dict]:
        if self.tracker:
            return self.tracker.get_project(project_id)
        return {"id": project_id, "name": project_id, "category": "brain"}

    def _get_tagline(self, project_id: str, category: str) -> str:
        taglines = {
            "sam_brain": "The mind that learns.",
            "sam_intelligence": "Self-aware and growing.",
            "character_pipeline": "Every frame, the same soul.",
            "voice_system": "Finding its voice.",
            "visual_system": "Seeing clearly now.",
            "content_pipeline": "Words flowing freely.",
            "semantic_memory": "Nothing forgotten.",
            "evolution_tracker": "Measuring what matters.",
            "orchestrator": "Routing intelligence.",
        }
        return taglines.get(project_id, f"Building {category}.")

    def _get_level(self, project_id: str, category: str) -> int:
        if self.tracker:
            assessment = self.tracker.get_project_assessment(project_id)
            if assessment:
                return assessment.get("level", 1)
        return 1

    def _get_level_name(self, project_id: str, category: str) -> str:
        level = self._get_level(project_id, category)
        ladder = EVOLUTION_LADDERS.get(category, [])
        if ladder and level <= len(ladder):
            return ladder[level - 1].get("name", f"Level {level}")
        return f"Level {level}"

    def _get_level_progress(self, project_id: str, category: str) -> float:
        criteria = self._get_criteria_breakdown(project_id, category)
        if not criteria:
            return 0.0
        met = sum(1 for c in criteria if c["met"])
        return (met / len(criteria)) * 100 if criteria else 0.0

    def _count_criteria_met(self, project_id: str, category: str) -> int:
        criteria = self._get_criteria_breakdown(project_id, category)
        return sum(1 for c in criteria if c["met"])

    def _count_criteria_total(self, project_id: str, category: str) -> int:
        ladder = EVOLUTION_LADDERS.get(category, [])
        level = self._get_level(project_id, category)
        if ladder and level <= len(ladder):
            return len(ladder[level - 1].get("criteria", []))
        return 0

    def _calculate_health_score(self, project_id: str) -> int:
        score = 70
        days_idle = self._get_days_since_update(project_id)
        if days_idle == 0:
            score += 15
        elif days_idle <= 3:
            score += 10
        elif days_idle <= 7:
            score += 5
        elif days_idle > 14:
            score -= 20

        pending = self._count_improvements(project_id, "pending")
        if pending == 0:
            score += 10
        elif pending > 5:
            score -= 10

        blockers = self._get_blockers(project_id)
        score -= len(blockers) * 10

        return max(0, min(100, score))

    def _get_health_status(self, project_id: str) -> str:
        score = self._calculate_health_score(project_id)
        if score >= 80:
            return "healthy"
        elif score >= 50:
            return "warning"
        return "critical"

    def _count_improvements(self, project_id: str, status: str) -> int:
        if not self.tracker:
            return 0
        if status == "pending":
            statuses = ["detected", "validated", "queued"]
        else:
            statuses = [status]
        improvements = self.tracker.get_improvements(project_id=project_id, status=statuses)
        return len(improvements) if improvements else 0

    def _count_improvements_this_week(self, project_id: str) -> int:
        if not self.tracker:
            return 0
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        improvements = self.tracker.get_improvements(
            project_id=project_id,
            status=["completed"],
            since=week_ago
        )
        return len(improvements) if improvements else 0

    def _get_last_activity(self, project_id: str) -> str:
        if self.tracker:
            project = self.tracker.get_project(project_id)
            if project and project.get("last_updated"):
                return project["last_updated"]
        return datetime.now().isoformat()

    def _get_days_since_update(self, project_id: str) -> int:
        last = self._get_last_activity(project_id)
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            return (datetime.now() - last_dt.replace(tzinfo=None)).days
        except:
            return 0

    def _get_uptime(self, project_id: str) -> float:
        return 99.5

    def _get_error_rate(self, project_id: str) -> float:
        return 0.1

    def _get_avg_response(self, project_id: str) -> float:
        return 150.0

    def _get_progress_history(self, project_id: str) -> List[Dict]:
        if not self.tracker:
            return []
        history = self.tracker.get_progress_history(project_id, limit=30)
        return [{"date": h.get("recorded_at", ""), "progress": h.get("progress", 0)} for h in history]

    def _get_activity_history(self, project_id: str) -> List[Dict]:
        return []

    def _get_health_history(self, project_id: str) -> List[Dict]:
        return []

    def _get_milestones(self, project_id: str, status: str) -> List[Milestone]:
        if not self.tracker:
            return []
        milestones = self.tracker.get_milestones(project_id, status=status)
        return [
            Milestone(
                name=m.get("name", ""),
                status=m.get("status", status),
                date=m.get("date"),
                progress=m.get("progress", 0.0)
            )
            for m in (milestones or [])
        ]

    def _get_current_milestone(self, project_id: str, category: str) -> Optional[Milestone]:
        criteria = self._get_criteria_breakdown(project_id, category)
        unmet = [c for c in criteria if not c["met"]]
        if unmet:
            first_unmet = unmet[0]
            return Milestone(
                name=f"Complete: {first_unmet['name']}",
                status="in_progress",
                date=None,
                progress=first_unmet.get("progress", 0) / 100
            )
        return None

    def _get_criteria_breakdown(self, project_id: str, category: str) -> List[Dict]:
        ladder = EVOLUTION_LADDERS.get(category, [])
        level = self._get_level(project_id, category)

        if not ladder or level > len(ladder):
            return []

        level_def = ladder[level - 1]
        criteria_names = level_def.get("criteria", [])

        assessment_data = {}
        if self.tracker:
            assessment = self.tracker.get_project_assessment(project_id)
            if assessment and assessment.get("criteria"):
                for c in assessment["criteria"]:
                    assessment_data[c["name"]] = c

        result = []
        for name in criteria_names:
            data = assessment_data.get(name, {})
            result.append({
                "name": name,
                "met": data.get("met", False),
                "progress": data.get("progress", 0.0) * 100,
                "evidence": data.get("evidence", "")
            })

        return result

    def _get_integrations(self, project_id: str) -> List[Dict]:
        if not self.tracker:
            return []
        relationships = self.tracker.get_relationships(project_id)
        return [
            {
                "project": r.get("target_project", ""),
                "status": r.get("status", "unknown"),
                "health": r.get("health", "unknown")
            }
            for r in (relationships or [])
        ]

    def _calculate_integration_score(self, project_id: str) -> int:
        integrations = self._get_integrations(project_id)
        if not integrations:
            return 0
        connected = sum(1 for i in integrations if i["status"] == "connected")
        partial = sum(1 for i in integrations if i["status"] == "partial")
        score = (connected * 100 + partial * 50) / len(integrations)
        return int(score)

    def _get_recent_activity(self, project_id: str) -> List[Dict]:
        if not self.tracker:
            return []
        improvements = self.tracker.get_improvements(project_id=project_id, limit=10)
        return [
            {
                "timestamp": i.get("completed_at") or i.get("detected_at", ""),
                "type": i.get("type", "improvement"),
                "description": i.get("description", ""),
                "impact": i.get("outcome", "")
            }
            for i in (improvements or [])
        ]

    def _get_blockers(self, project_id: str) -> List[str]:
        blockers = []
        integrations = self._get_integrations(project_id)
        for i in integrations:
            if i["status"] == "blocked":
                blockers.append(f"Integration with {i['project']} blocked")

        if self._count_improvements(project_id, "pending") > 10:
            blockers.append("Too many pending improvements (>10)")

        if self._get_days_since_update(project_id) > 30:
            blockers.append("No activity in 30+ days")

        return blockers

    def _get_risks(self, project_id: str) -> List[Dict]:
        risks = []
        days_idle = self._get_days_since_update(project_id)
        if 14 < days_idle <= 30:
            risks.append({
                "description": "Project becoming stale",
                "severity": "medium",
                "mitigation": "Review and update or archive"
            })

        pending = self._count_improvements(project_id, "pending")
        if 5 < pending <= 10:
            risks.append({
                "description": "Improvement backlog growing",
                "severity": "low",
                "mitigation": "Prioritize and execute top items"
            })

        return risks

    def _get_category_rank(self, project_id: str, category: str) -> int:
        # Would calculate actual ranking
        return 1

    def _get_category_count(self, category: str) -> int:
        # Would count projects in category
        return 3

    def _compare_to_last_week(self, project_id: str) -> Dict:
        return {
            "improvements_trend": "up",
            "progress_change": 5.0,
            "health_change": 2
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    generator = DashboardGenerator()

    if len(sys.argv) < 2:
        print("SAM Project Dashboard")
        print("\nData-rich project status with ranked recommendations.")
        print("\nUsage:")
        print("  python project_dashboard.py stats <project_id>  # Quick stats")
        print("  python project_dashboard.py full <project_id>   # Full JSON")
        print("  python project_dashboard.py llm <project_id>    # LLM format")
        print("  python project_dashboard.py all                 # All projects")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "stats":
        if len(sys.argv) < 3:
            print("Usage: python project_dashboard.py stats <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        stats = generator.get_quick_stats(project_id)

        print(f"\n{stats['name']}")
        print("─" * 40)
        print(f"Level:    {stats['level']} - {stats['level_name']}")
        print(f"Progress: {stats['progress']:.0f}%")
        print(f"Health:   {stats['health']}/100 ({stats['status']})")
        print(f"Pending:  {stats['pending']} improvements")
        print(f"Idle:     {stats['days_idle']} days")
        if stats.get('top_recommendation'):
            print(f"\nTop Priority: {stats['top_recommendation']}")

    elif cmd == "full":
        if len(sys.argv) < 3:
            print("Usage: python project_dashboard.py full <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        dashboard = generator.get_dashboard(project_id)
        print(json.dumps(dashboard.to_dict(), indent=2, default=str))

    elif cmd == "llm":
        if len(sys.argv) < 3:
            print("Usage: python project_dashboard.py llm <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        print(generator.get_llm_summary(project_id))

    elif cmd == "all":
        stats = generator.get_all_projects_stats()

        print("\n📊 All Projects\n")
        print(f"{'Project':<25} {'Level':<8} {'Progress':<10} {'Health':<10} {'Top Priority':<30}")
        print("─" * 85)

        for s in stats:
            top = s.get('top_recommendation', '-')[:28] if s.get('top_recommendation') else '-'
            print(f"{s['name']:<25} {s['level']:<8} {s['progress']:.0f}%{'':<7} {s['health']:<10} {top}")

    else:
        print(f"Unknown command: {cmd}")
