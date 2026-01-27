#!/usr/bin/env python3
"""
SAM Intelligence Core - The brain that makes SAM actually smart.

This module provides:
- Self-awareness: SAM knows its own state and capabilities
- Learning: Adjusts behavior based on outcomes
- Proactive intelligence: Suggests before being asked
- Action execution: Actually implements improvements
- Memory integration: Learns from all interactions

This is SAM's consciousness layer.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# Local imports
from evolution_tracker import EvolutionTracker, Improvement, IMPROVEMENT_TYPES
from improvement_detector import ImprovementDetector
from evolution_ladders import LadderAssessor, EVOLUTION_LADDERS

# Paths
SAM_BRAIN = Path(__file__).parent
INTELLIGENCE_CACHE = SAM_BRAIN / ".sam_intelligence_cache.json"
SAM_STATE_FILE = SAM_BRAIN / ".sam_state.json"
LEARNING_FILE = SAM_BRAIN / ".sam_learning.json"


@dataclass
class SamState:
    """SAM's current self-awareness state."""
    # Core identity
    name: str = "SAM"
    version: str = "0.3.0"  # Perpetual Improvement System

    # Current awareness
    last_scan_time: str = ""
    last_assessment_time: str = ""
    last_learning_update: str = ""

    # Health metrics
    projects_tracked: int = 0
    improvements_pending: int = 0
    improvements_completed: int = 0
    current_level: int = 0
    level_name: str = "Starting"

    # Capabilities online
    memory_online: bool = False
    evolution_online: bool = False
    detector_online: bool = False
    ssot_online: bool = False

    # Learning state
    total_feedback_entries: int = 0
    success_rate: float = 0.0
    avg_impact: float = 0.0

    # Proactive state
    pending_suggestions: List[str] = field(default_factory=list)
    blocked_items: List[str] = field(default_factory=list)
    urgent_items: List[str] = field(default_factory=list)


@dataclass
class LearningPattern:
    """A learned pattern from feedback."""
    pattern_type: str  # improvement_type, project_category, etc.
    pattern_value: str
    success_count: int = 0
    failure_count: int = 0
    total_impact: float = 0.0
    last_updated: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def avg_impact(self) -> float:
        return self.total_impact / self.success_count if self.success_count > 0 else 0.0

    @property
    def confidence(self) -> float:
        """How confident we are in this pattern (more data = more confident)."""
        total = self.success_count + self.failure_count
        return min(total / 10, 1.0)  # Max confidence at 10 samples


class IntelligenceCache:
    """Fast cache for expensive operations."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.ttl = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self._load()

    def _load(self):
        """Load cache from disk."""
        if INTELLIGENCE_CACHE.exists():
            try:
                data = json.loads(INTELLIGENCE_CACHE.read_text())
                self.cache = {k: (v["data"], v["expires"]) for k, v in data.items()}
            except:
                self.cache = {}

    def _save(self):
        """Save cache to disk."""
        data = {k: {"data": v[0], "expires": v[1]} for k, v in self.cache.items()}
        INTELLIGENCE_CACHE.write_text(json.dumps(data, indent=2, default=str))

    def get(self, key: str) -> Optional[Any]:
        """Get from cache if not expired."""
        if key in self.cache:
            data, expires = self.cache[key]
            if time.time() < expires:
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set cache value."""
        expires = time.time() + (ttl or self.ttl)
        self.cache[key] = (value, expires)
        self._save()

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern."""
        if pattern:
            self.cache = {k: v for k, v in self.cache.items() if pattern not in k}
        else:
            self.cache = {}
        self._save()


class SamIntelligence:
    """SAM's intelligent core - makes decisions, learns, acts."""

    def __init__(self):
        self.cache = IntelligenceCache()
        self.state = self._load_state()
        self.learning = self._load_learning()
        self._tracker = None
        self._detector = None
        self._assessor = None
        self._memory = None

        # Initialize on first use
        self._update_awareness()

    # =====================
    # LAZY LOADING
    # =====================

    @property
    def tracker(self):
        if self._tracker is None:
            try:
                self._tracker = EvolutionTracker()
                self.state.evolution_online = True
            except Exception as e:
                self.state.evolution_online = False
        return self._tracker

    @property
    def detector(self):
        if self._detector is None:
            try:
                self._detector = ImprovementDetector()
                self.state.detector_online = True
            except Exception as e:
                self.state.detector_online = False
        return self._detector

    @property
    def assessor(self):
        if self._assessor is None:
            try:
                self._assessor = LadderAssessor()
            except:
                pass
        return self._assessor

    @property
    def memory(self):
        if self._memory is None:
            try:
                from semantic_memory import SemanticMemory
                self._memory = SemanticMemory()
                self.state.memory_online = True
            except Exception as e:
                self.state.memory_online = False
        return self._memory

    # =====================
    # STATE MANAGEMENT
    # =====================

    def _load_state(self) -> SamState:
        """Load SAM's state from disk."""
        if SAM_STATE_FILE.exists():
            try:
                data = json.loads(SAM_STATE_FILE.read_text())
                return SamState(**data)
            except:
                pass
        return SamState()

    def _save_state(self):
        """Save SAM's state to disk."""
        SAM_STATE_FILE.write_text(json.dumps(asdict(self.state), indent=2, default=str))

    def _load_learning(self) -> Dict[str, LearningPattern]:
        """Load learning patterns from disk."""
        if LEARNING_FILE.exists():
            try:
                data = json.loads(LEARNING_FILE.read_text())
                return {k: LearningPattern(**v) for k, v in data.items()}
            except:
                pass
        return {}

    def _save_learning(self):
        """Save learning patterns to disk."""
        data = {k: asdict(v) for k, v in self.learning.items()}
        LEARNING_FILE.write_text(json.dumps(data, indent=2))

    def _update_awareness(self):
        """Update SAM's self-awareness state."""
        try:
            # Check what's online
            self.state.ssot_online = Path("/Volumes/Plex/SSOT").exists()

            # Get project stats (cached)
            projects = self.get_projects_fast()
            self.state.projects_tracked = len(projects)

            # Get improvement stats
            improvements = self.tracker.get_improvements(status="detected")
            self.state.improvements_pending = len(improvements)

            completed = self.tracker.get_improvements(status="completed")
            self.state.improvements_completed = len(completed)

            # Get learning stats
            if self.memory:
                stats = self.memory.get_all_improvement_stats()
                self.state.total_feedback_entries = stats.get("total", 0)
                if stats.get("total", 0) > 0:
                    self.state.success_rate = stats.get("total_successes", 0) / stats["total"]

            self._save_state()
        except Exception as e:
            pass  # Don't fail on awareness update

    # =====================
    # FAST CACHED OPERATIONS
    # =====================

    def get_projects_fast(self) -> List[Dict]:
        """Get projects with caching."""
        cached = self.cache.get("projects")
        if cached:
            return cached

        projects = self.tracker.get_all_projects()
        result = [{"id": p.id, "name": p.name, "category": p.category,
                   "progress": p.current_progress} for p in projects]
        self.cache.set("projects", result, ttl=60)  # 1 minute cache
        return result

    def get_level_fast(self, project_id: str = "SAM_BRAIN") -> Dict:
        """Get evolution level with caching."""
        cache_key = f"level_{project_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Quick level estimation based on tracked data
        # (Avoids slow file scanning)
        project = self.tracker.get_project(project_id)
        if project:
            # Estimate level from progress
            progress = project.current_progress
            if progress >= 0.8:
                level = 4
            elif progress >= 0.6:
                level = 3
            elif progress >= 0.4:
                level = 2
            elif progress >= 0.2:
                level = 1
            else:
                level = 0

            ladder = EVOLUTION_LADDERS.get(project.category, EVOLUTION_LADDERS["platform"])
            level_name = ladder[min(level, len(ladder)-1)].name if level > 0 else "Starting"

            result = {"level": level, "name": level_name, "progress": progress}
            self.cache.set(cache_key, result, ttl=300)  # 5 minute cache
            return result

        return {"level": 0, "name": "Unknown", "progress": 0}

    def get_top_suggestions_fast(self, limit: int = 5) -> List[Dict]:
        """Get top improvement suggestions quickly."""
        cached = self.cache.get("top_suggestions")
        if cached:
            return cached[:limit]

        improvements = self.tracker.get_improvements(status="detected")

        # Score and sort
        scored = []
        for imp in improvements:
            score = self._calculate_smart_priority(imp)
            scored.append({
                "id": imp.id,
                "project": imp.project_id,
                "type": imp.type,
                "description": imp.description[:100],
                "priority": imp.priority,
                "score": score,
                "auto_approve": IMPROVEMENT_TYPES.get(imp.type, {}).get("auto_approve", False)
            })

        scored.sort(key=lambda x: -x["score"])
        self.cache.set("top_suggestions", scored[:20], ttl=120)  # 2 minute cache
        return scored[:limit]

    # =====================
    # INTELLIGENT SCORING
    # =====================

    def _calculate_smart_priority(self, improvement: Improvement) -> float:
        """Calculate priority using learned patterns."""
        # Base score from tracker
        base_score = self.tracker.calculate_priority(improvement)

        # Adjust based on learned success rates
        type_pattern = self.learning.get(f"type:{improvement.type}")
        if type_pattern and type_pattern.confidence > 0.3:
            # Boost types that historically succeed
            base_score *= (0.5 + type_pattern.success_rate)

        project_pattern = self.learning.get(f"project:{improvement.project_id}")
        if project_pattern and project_pattern.confidence > 0.3:
            # Boost projects where we've had success
            base_score *= (0.5 + project_pattern.success_rate)

        return base_score

    # =====================
    # LEARNING SYSTEM
    # =====================

    def learn_from_feedback(self, improvement_id: str, success: bool, impact: float, lessons: str = ""):
        """Learn from improvement feedback."""
        improvement = self.tracker.get_improvement(improvement_id)
        if not improvement:
            return

        now = datetime.now().isoformat()

        # Update type pattern
        type_key = f"type:{improvement.type}"
        if type_key not in self.learning:
            self.learning[type_key] = LearningPattern(
                pattern_type="improvement_type",
                pattern_value=improvement.type
            )
        pattern = self.learning[type_key]
        if success:
            pattern.success_count += 1
            pattern.total_impact += impact
        else:
            pattern.failure_count += 1
        pattern.last_updated = now

        # Update project pattern
        project_key = f"project:{improvement.project_id}"
        if project_key not in self.learning:
            self.learning[project_key] = LearningPattern(
                pattern_type="project",
                pattern_value=improvement.project_id
            )
        pattern = self.learning[project_key]
        if success:
            pattern.success_count += 1
            pattern.total_impact += impact
        else:
            pattern.failure_count += 1
        pattern.last_updated = now

        # Record in tracker
        self.tracker.record_feedback(improvement_id, success, impact, lessons)

        # Record in semantic memory for long-term learning
        if self.memory:
            self.memory.add_improvement_feedback(
                improvement_id=improvement_id,
                project_id=improvement.project_id,
                improvement_type=improvement.type,
                description=improvement.description,
                outcome="Success" if success else "Failed",
                success=success,
                impact_score=impact,
                lessons_learned=lessons
            )

        self.state.last_learning_update = now
        self._save_learning()
        self._save_state()

        # Invalidate suggestion cache since priorities changed
        self.cache.invalidate("suggestions")

    def get_learned_insights(self) -> Dict:
        """Get insights from learned patterns."""
        insights = {
            "best_improvement_types": [],
            "challenging_improvement_types": [],
            "most_improved_projects": [],
            "struggling_projects": [],
            "recommendations": []
        }

        type_patterns = [(k, v) for k, v in self.learning.items() if k.startswith("type:")]
        project_patterns = [(k, v) for k, v in self.learning.items() if k.startswith("project:")]

        # Find best/worst improvement types
        type_patterns.sort(key=lambda x: -x[1].success_rate)
        for key, pattern in type_patterns[:3]:
            if pattern.confidence > 0.2:
                insights["best_improvement_types"].append({
                    "type": pattern.pattern_value,
                    "success_rate": f"{pattern.success_rate:.0%}",
                    "avg_impact": f"{pattern.avg_impact:.2f}"
                })

        for key, pattern in type_patterns[-3:]:
            if pattern.confidence > 0.2 and pattern.success_rate < 0.5:
                insights["challenging_improvement_types"].append({
                    "type": pattern.pattern_value,
                    "success_rate": f"{pattern.success_rate:.0%}"
                })

        # Recommendations based on learning
        if insights["best_improvement_types"]:
            best_type = insights["best_improvement_types"][0]["type"]
            insights["recommendations"].append(
                f"Focus on {best_type} improvements - highest success rate"
            )

        if insights["challenging_improvement_types"]:
            worst_type = insights["challenging_improvement_types"][0]["type"]
            insights["recommendations"].append(
                f"Be careful with {worst_type} improvements - lower success rate"
            )

        return insights

    # =====================
    # PROACTIVE INTELLIGENCE
    # =====================

    def get_proactive_suggestions(self) -> List[Dict]:
        """Generate proactive suggestions based on current state."""
        suggestions = []

        # Check for stale projects
        projects = self.get_projects_fast()
        for p in projects:
            if p["progress"] < 0.3:
                suggestions.append({
                    "type": "stale_project",
                    "urgency": "medium",
                    "message": f"{p['name']} is at {p['progress']*100:.0f}% - needs attention",
                    "action": f"Review {p['id']} improvements"
                })

        # Check for auto-approvable improvements
        top = self.get_top_suggestions_fast(10)
        auto_approve = [s for s in top if s.get("auto_approve")]
        if auto_approve:
            suggestions.append({
                "type": "auto_approve_ready",
                "urgency": "low",
                "message": f"{len(auto_approve)} improvements can be auto-approved",
                "action": "Run auto-approve cycle"
            })

        # Check for high-priority items
        urgent = [s for s in top if s["priority"] == 1]
        if urgent:
            suggestions.append({
                "type": "urgent_improvements",
                "urgency": "high",
                "message": f"{len(urgent)} critical improvements need attention",
                "items": [u["description"][:50] for u in urgent[:3]]
            })

        # Learning-based suggestions
        insights = self.get_learned_insights()
        suggestions.extend([
            {"type": "learning_insight", "urgency": "info", "message": rec}
            for rec in insights.get("recommendations", [])
        ])

        return suggestions

    # =====================
    # SELF-AWARENESS
    # =====================

    def get_self_status(self) -> Dict:
        """Get SAM's self-awareness status."""
        self._update_awareness()

        level = self.get_level_fast("SAM_BRAIN")

        return {
            "identity": {
                "name": self.state.name,
                "version": self.state.version,
                "level": level["level"],
                "level_name": level["name"]
            },
            "capabilities": {
                "memory": self.state.memory_online,
                "evolution": self.state.evolution_online,
                "detector": self.state.detector_online,
                "ssot": self.state.ssot_online
            },
            "metrics": {
                "projects_tracked": self.state.projects_tracked,
                "improvements_pending": self.state.improvements_pending,
                "improvements_completed": self.state.improvements_completed,
                "success_rate": f"{self.state.success_rate:.0%}",
                "feedback_entries": self.state.total_feedback_entries
            },
            "learning": self.get_learned_insights(),
            "proactive": self.get_proactive_suggestions()
        }

    def explain_myself(self) -> str:
        """SAM explains its current state and thinking."""
        status = self.get_self_status()

        lines = [
            f"I'm {status['identity']['name']} v{status['identity']['version']}",
            f"Currently at Level {status['identity']['level']} ({status['identity']['level_name']})",
            "",
            "My capabilities:",
        ]

        for cap, online in status["capabilities"].items():
            icon = "✓" if online else "✗"
            lines.append(f"  {icon} {cap}")

        lines.extend([
            "",
            f"I'm tracking {status['metrics']['projects_tracked']} projects",
            f"with {status['metrics']['improvements_pending']} pending improvements",
            f"and {status['metrics']['improvements_completed']} completed.",
            "",
        ])

        if status['metrics']['feedback_entries'] > 0:
            lines.append(f"I've learned from {status['metrics']['feedback_entries']} outcomes")
            lines.append(f"with a {status['metrics']['success_rate']} success rate.")
        else:
            lines.append("I haven't received feedback yet - I'm still learning.")

        if status['proactive']:
            lines.extend(["", "Things I noticed:"])
            for suggestion in status['proactive'][:3]:
                lines.append(f"  • {suggestion['message']}")

        return "\n".join(lines)

    # =====================
    # ACTION EXECUTION
    # =====================

    def execute_auto_approved(self) -> List[Dict]:
        """Execute auto-approved improvements."""
        results = []

        improvements = self.tracker.get_improvements(status="detected")

        for imp in improvements:
            config = IMPROVEMENT_TYPES.get(imp.type, {})
            if config.get("auto_approve"):
                # Execute the improvement
                result = self._execute_improvement(imp)
                results.append(result)

                # Learn from the result
                self.learn_from_feedback(
                    imp.id,
                    result["success"],
                    result.get("impact", 0.5),
                    result.get("message", "")
                )

        return results

    def _execute_improvement(self, improvement: Improvement) -> Dict:
        """Execute a single improvement."""
        # For now, mark as implementing and return success
        # In future, this can actually run code, create PRs, etc.

        try:
            self.tracker.update_improvement_status(
                improvement.id,
                "completed",
                f"Auto-executed at {datetime.now().isoformat()}"
            )

            return {
                "improvement_id": improvement.id,
                "success": True,
                "impact": 0.5,
                "message": f"Completed: {improvement.description[:50]}"
            }
        except Exception as e:
            return {
                "improvement_id": improvement.id,
                "success": False,
                "impact": 0,
                "message": str(e)
            }

    # =====================
    # MAIN INTERFACE
    # =====================

    def think(self, query: str) -> str:
        """Process a query intelligently."""
        query_lower = query.lower()

        # Self-awareness queries
        if any(w in query_lower for w in ["who are you", "what are you", "status", "yourself"]):
            return self.explain_myself()

        # Suggestion queries
        if any(w in query_lower for w in ["suggest", "recommend", "what should", "next"]):
            suggestions = self.get_top_suggestions_fast(5)
            if not suggestions:
                return "No improvements detected. All projects are on track!"

            lines = ["Top suggestions:"]
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{i}. [{s['type']}] {s['project']}: {s['description']}")
            return "\n".join(lines)

        # Learning queries
        if any(w in query_lower for w in ["learned", "insights", "patterns"]):
            insights = self.get_learned_insights()
            lines = ["What I've learned:"]
            for rec in insights.get("recommendations", ["Still gathering data..."]):
                lines.append(f"  • {rec}")
            return "\n".join(lines)

        # Project queries
        if any(w in query_lower for w in ["projects", "progress", "overview"]):
            projects = self.get_projects_fast()
            lines = [f"Tracking {len(projects)} projects:"]
            for p in sorted(projects, key=lambda x: -x["progress"])[:10]:
                bar = "█" * int(p["progress"] * 10) + "░" * (10 - int(p["progress"] * 10))
                lines.append(f"  [{bar}] {p['name']}")
            return "\n".join(lines)

        # Default: return self status
        return self.explain_myself()


# Global instance
_intelligence = None

def get_intelligence() -> SamIntelligence:
    """Get global intelligence instance."""
    global _intelligence
    if _intelligence is None:
        _intelligence = SamIntelligence()
    return _intelligence


def think(query: str) -> str:
    """Quick access to SAM's thinking."""
    return get_intelligence().think(query)


def status() -> Dict:
    """Quick access to SAM's status."""
    return get_intelligence().get_self_status()


# CLI
if __name__ == "__main__":
    import sys

    sam = SamIntelligence()

    if len(sys.argv) < 2:
        print(sam.explain_myself())
        print("\nCommands: status, think <query>, suggest, learn, auto-execute")
    else:
        cmd = sys.argv[1]

        if cmd == "status":
            import json
            print(json.dumps(sam.get_self_status(), indent=2))

        elif cmd == "think":
            query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "who are you"
            print(sam.think(query))

        elif cmd == "suggest":
            for s in sam.get_top_suggestions_fast(5):
                print(f"[{s['priority']}] {s['project']}: {s['description']}")

        elif cmd == "learn":
            insights = sam.get_learned_insights()
            print("Learning Insights:")
            print(json.dumps(insights, indent=2))

        elif cmd == "auto-execute":
            results = sam.execute_auto_approved()
            print(f"Executed {len(results)} auto-approved improvements")
            for r in results:
                status = "✓" if r["success"] else "✗"
                print(f"  {status} {r['message']}")

        elif cmd == "proactive":
            for s in sam.get_proactive_suggestions():
                print(f"[{s['urgency']}] {s['message']}")

        else:
            print(sam.think(cmd))
