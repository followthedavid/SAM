#!/usr/bin/env python3
"""
SAM Evolution Ladders - Defines progression paths for project categories.

Each project type (brain, visual, voice, content, platform) has a 5-level
evolution ladder. Projects are assessed against these criteria to determine
their current level and next evolution targets.

Levels:
  1. Basic - Minimal viable functionality
  2. Functional - Core features working
  3. Integrated - Connected to other systems
  4. Autonomous - Self-managing capabilities
  5. Mastery - Optimized, teaching other systems
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from learn.evolution_tracker import EvolutionTracker, PROJECT_CATEGORIES


@dataclass
class LevelCriterion:
    """A single criterion for reaching a level."""
    id: str
    name: str
    description: str
    check_type: str  # file_exists, function_exists, integration, metric
    check_value: str  # path, function name, target project, threshold


@dataclass
class EvolutionLevel:
    """A level in the evolution ladder."""
    level: int
    name: str
    description: str
    criteria: List[LevelCriterion]
    estimated_progress: float  # 0.0-1.0, progress within this level to next


@dataclass
class ProjectAssessment:
    """Assessment result for a project."""
    project_id: str
    category: str
    current_level: int
    current_level_name: str
    level_progress: float  # Progress toward next level
    met_criteria: List[str]
    unmet_criteria: List[str]
    next_evolution: str  # Description of what's needed for next level


# =====================
# EVOLUTION LADDERS
# =====================

EVOLUTION_LADDERS: Dict[str, List[EvolutionLevel]] = {
    # SAM's own evolution ladder - separate from other brain projects
    "sam": [
        EvolutionLevel(
            level=1,
            name="Responsive",
            description="SAM responds to queries and routes appropriately",
            criteria=[
                LevelCriterion("responds", "Query Response", "Responds to user queries", "function_exists", "handle_chat"),
                LevelCriterion("routes", "Smart Routing", "Routes to appropriate handler", "function_exists", "route_message"),
                LevelCriterion("personality", "Personality", "Has defined personality", "file_exists", "personality.py"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Remembering",
            description="SAM remembers past interactions and learns from them",
            criteria=[
                LevelCriterion("memory_store", "Memory Storage", "Stores interactions", "function_exists", "add_interaction"),
                LevelCriterion("memory_search", "Memory Search", "Searches past context", "function_exists", "search"),
                LevelCriterion("embeddings", "Vector Embeddings", "Uses embeddings", "file_exists", "memory/index.npy"),
                LevelCriterion("bootstrap", "Knowledge Bootstrap", "Loads salvaged knowledge", "file_exists", "bootstrap_memory.py"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Self-Aware",
            description="SAM monitors and improves itself",
            criteria=[
                LevelCriterion("evolution_track", "Evolution Tracking", "Tracks own evolution", "file_exists", "evolution.db"),
                LevelCriterion("improvement_detect", "Improvement Detection", "Detects improvements", "function_exists", "full_scan"),
                LevelCriterion("confidence", "Confidence Scoring", "Evaluates own confidence", "function_exists", "evaluate_confidence"),
                LevelCriterion("escalation", "Smart Escalation", "Knows when to ask for help", "function_exists", "should_escalate"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Self-Improving",
            description="SAM autonomously improves itself and other projects",
            criteria=[
                LevelCriterion("auto_train", "Auto Training", "Triggers training automatically", "function_exists", "trigger_training"),
                LevelCriterion("feedback_loop", "Feedback Loop", "Learns from outcomes", "function_exists", "record_feedback"),
                LevelCriterion("project_improve", "Project Improvement", "Improves other projects", "function_exists", "run_evolution_cycle"),
                LevelCriterion("daemon", "Autonomous Daemon", "Runs continuously", "file_exists", "autonomous_daemon.py"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Orchestrator",
            description="SAM orchestrates exponential project growth and teaches",
            criteria=[
                LevelCriterion("multi_project", "Multi-Project Orchestration", "Manages many projects", "function_exists", "assess_all_projects"),
                LevelCriterion("cross_learn", "Cross-Project Learning", "Applies learnings across projects", "function_exists", "get_success_rate_by_type"),
                LevelCriterion("proactive", "Proactive Suggestions", "Suggests before asked", "function_exists", "get_top_improvements"),
                LevelCriterion("teaching", "Teaching Mode", "Can explain its decisions", "function_exists", "explain_decision"),
                LevelCriterion("exponential", "Exponential Growth", "Supports exponential project addition", "function_exists", "add_project"),
            ],
            estimated_progress=1.0
        ),
    ],

    "brain": [
        EvolutionLevel(
            level=1,
            name="Basic",
            description="Responds to queries with basic routing",
            criteria=[
                LevelCriterion("responds", "Query Response", "Responds to user queries", "function_exists", "handle_chat"),
                LevelCriterion("routes", "Basic Routing", "Routes to appropriate handler", "function_exists", "route_message"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Learning",
            description="Stores and retrieves context from memory",
            criteria=[
                LevelCriterion("memory_store", "Memory Storage", "Stores interactions in memory", "function_exists", "add_interaction"),
                LevelCriterion("memory_search", "Memory Search", "Retrieves relevant context", "function_exists", "search"),
                LevelCriterion("embeddings", "Embeddings", "Uses vector embeddings", "file_exists", "memory/index.npy"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Adaptive",
            description="Evaluates confidence and escalates appropriately",
            criteria=[
                LevelCriterion("confidence", "Confidence Scoring", "Evaluates response quality", "function_exists", "evaluate_confidence"),
                LevelCriterion("escalation", "Escalation", "Escalates uncertain responses", "function_exists", "should_escalate"),
                LevelCriterion("multi_model", "Multi-Model", "Uses different models for different tasks", "function_exists", "select_model"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Autonomous",
            description="Self-trains and improves without intervention",
            criteria=[
                LevelCriterion("auto_train", "Auto Training", "Triggers training automatically", "function_exists", "trigger_training"),
                LevelCriterion("feedback_loop", "Feedback Loop", "Learns from outcomes", "function_exists", "record_feedback"),
                LevelCriterion("evolution_track", "Evolution Tracking", "Tracks its own improvement", "file_exists", "evolution.db"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Mastery",
            description="Optimizes across projects, suggests improvements proactively",
            criteria=[
                LevelCriterion("cross_project", "Cross-Project Optimization", "Improves other projects", "function_exists", "optimize_project"),
                LevelCriterion("proactive", "Proactive Suggestions", "Suggests improvements before asked", "function_exists", "detect_improvements"),
                LevelCriterion("teaching", "Teaching Mode", "Can explain its decisions", "function_exists", "explain_decision"),
            ],
            estimated_progress=1.0
        ),
    ],

    "visual": [
        EvolutionLevel(
            level=1,
            name="Generation",
            description="Can generate basic images",
            criteria=[
                LevelCriterion("text2img", "Text-to-Image", "Generates images from prompts", "function_exists", "generate_image"),
                LevelCriterion("api_connect", "API Connection", "Connects to ComfyUI/SD", "integration", "COMFYUI"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Styled",
            description="Applies consistent styles with LoRA",
            criteria=[
                LevelCriterion("lora", "LoRA Support", "Can apply LoRA models", "function_exists", "apply_lora"),
                LevelCriterion("style_consistency", "Style Consistency", "Maintains style across generations", "metric", "style_variance<0.2"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Character",
            description="Creates consistent characters with pose control",
            criteria=[
                LevelCriterion("character_id", "Character Identity", "Maintains character consistency", "function_exists", "load_character"),
                LevelCriterion("pose_control", "Pose Control", "Controls poses via ControlNet", "function_exists", "apply_pose"),
                LevelCriterion("face_fix", "Face Restoration", "Fixes/enhances faces", "function_exists", "restore_face"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Pipeline",
            description="Automated workflow with batch processing",
            criteria=[
                LevelCriterion("batch", "Batch Processing", "Processes multiple images", "function_exists", "batch_generate"),
                LevelCriterion("workflow", "Workflow Automation", "Runs complete workflows", "function_exists", "run_workflow"),
                LevelCriterion("queue", "Job Queue", "Manages generation queue", "function_exists", "queue_job"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Production",
            description="Quality control and asset management",
            criteria=[
                LevelCriterion("quality_check", "Quality Control", "Automatically checks output quality", "function_exists", "check_quality"),
                LevelCriterion("asset_mgmt", "Asset Management", "Organizes and catalogs outputs", "function_exists", "catalog_asset"),
                LevelCriterion("variation", "Smart Variation", "Generates variations intelligently", "function_exists", "generate_variations"),
            ],
            estimated_progress=1.0
        ),
    ],

    "voice": [
        EvolutionLevel(
            level=1,
            name="Synthesis",
            description="Basic text-to-speech output",
            criteria=[
                LevelCriterion("tts", "Text-to-Speech", "Converts text to speech", "function_exists", "synthesize"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Cloned",
            description="Uses voice cloning (RVC)",
            criteria=[
                LevelCriterion("rvc", "RVC Integration", "Uses RVC for voice cloning", "function_exists", "clone_voice"),
                LevelCriterion("model_load", "Model Loading", "Loads custom voice models", "function_exists", "load_voice_model"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Expressive",
            description="Conveys emotion and context",
            criteria=[
                LevelCriterion("emotion", "Emotion Control", "Adjusts voice emotion", "function_exists", "set_emotion"),
                LevelCriterion("prosody", "Prosody Control", "Controls speech rhythm/tone", "function_exists", "set_prosody"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Conversational",
            description="Natural conversation flow",
            criteria=[
                LevelCriterion("streaming", "Streaming Output", "Streams audio in real-time", "function_exists", "stream_audio"),
                LevelCriterion("interruption", "Interruption Handling", "Handles mid-speech interrupts", "function_exists", "handle_interrupt"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Mastery",
            description="Indistinguishable from human",
            criteria=[
                LevelCriterion("natural", "Natural Cadence", "Human-like speech patterns", "metric", "naturalness>0.9"),
                LevelCriterion("context_aware", "Context Awareness", "Adjusts voice based on context", "function_exists", "adapt_to_context"),
            ],
            estimated_progress=1.0
        ),
    ],

    "content": [
        EvolutionLevel(
            level=1,
            name="Catalog",
            description="Basic media cataloging",
            criteria=[
                LevelCriterion("scan", "Media Scanning", "Scans for media files", "function_exists", "scan_media"),
                LevelCriterion("metadata", "Metadata Extraction", "Extracts media metadata", "function_exists", "extract_metadata"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Organized",
            description="Automatic organization and tagging",
            criteria=[
                LevelCriterion("auto_tag", "Auto Tagging", "Automatically tags content", "function_exists", "auto_tag"),
                LevelCriterion("categorize", "Categorization", "Categorizes content automatically", "function_exists", "categorize"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Enhanced",
            description="Content enhancement and matching",
            criteria=[
                LevelCriterion("match", "Content Matching", "Matches content to databases", "function_exists", "match_content"),
                LevelCriterion("enhance", "Enhancement", "Enhances content quality", "function_exists", "enhance_content"),
                LevelCriterion("dedup", "Deduplication", "Removes duplicates", "function_exists", "deduplicate"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Intelligent",
            description="Smart recommendations and insights",
            criteria=[
                LevelCriterion("recommend", "Recommendations", "Suggests related content", "function_exists", "recommend"),
                LevelCriterion("insights", "Content Insights", "Provides analytics/insights", "function_exists", "generate_insights"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Mastery",
            description="Autonomous content curation",
            criteria=[
                LevelCriterion("curate", "Auto Curation", "Curates collections automatically", "function_exists", "auto_curate"),
                LevelCriterion("predict", "Trend Prediction", "Predicts content trends", "function_exists", "predict_trends"),
            ],
            estimated_progress=1.0
        ),
    ],

    "platform": [
        EvolutionLevel(
            level=1,
            name="Interface",
            description="Basic user interface",
            criteria=[
                LevelCriterion("ui", "User Interface", "Has usable interface", "file_exists", "ui/"),
                LevelCriterion("commands", "Command Support", "Responds to commands", "function_exists", "handle_command"),
            ],
            estimated_progress=0.2
        ),
        EvolutionLevel(
            level=2,
            name="Connected",
            description="Connected to core services",
            criteria=[
                LevelCriterion("api", "API Integration", "Connects to SAM API", "integration", "SAM_BRAIN"),
                LevelCriterion("auth", "Authentication", "Handles authentication", "function_exists", "authenticate"),
            ],
            estimated_progress=0.4
        ),
        EvolutionLevel(
            level=3,
            name="Automated",
            description="Automation capabilities",
            criteria=[
                LevelCriterion("schedule", "Scheduling", "Schedules automated tasks", "function_exists", "schedule_task"),
                LevelCriterion("triggers", "Event Triggers", "Responds to events", "function_exists", "on_event"),
            ],
            estimated_progress=0.6
        ),
        EvolutionLevel(
            level=4,
            name="Smart",
            description="Context-aware and predictive",
            criteria=[
                LevelCriterion("context", "Context Awareness", "Understands context", "function_exists", "get_context"),
                LevelCriterion("predict", "Prediction", "Predicts user needs", "function_exists", "predict_action"),
            ],
            estimated_progress=0.8
        ),
        EvolutionLevel(
            level=5,
            name="Mastery",
            description="Self-managing platform",
            criteria=[
                LevelCriterion("self_heal", "Self-Healing", "Recovers from failures", "function_exists", "self_heal"),
                LevelCriterion("optimize", "Self-Optimization", "Optimizes performance", "function_exists", "optimize"),
            ],
            estimated_progress=1.0
        ),
    ],
}


class LadderAssessor:
    """Assesses projects against evolution ladders."""

    def __init__(self, tracker: EvolutionTracker = None):
        self.tracker = tracker or EvolutionTracker()

    def assess_project(self, project_id: str) -> ProjectAssessment:
        """Assess a project's evolution level."""
        project = self.tracker.get_project(project_id)
        if not project:
            # Create from known categories
            category = PROJECT_CATEGORIES.get(project_id, "platform")
        else:
            category = project.category

        ladder = EVOLUTION_LADDERS.get(category, EVOLUTION_LADDERS["platform"])

        met_criteria = []
        unmet_criteria = []
        current_level = 0

        for level in ladder:
            level_met = True
            for criterion in level.criteria:
                if self._check_criterion(project_id, criterion):
                    met_criteria.append(f"L{level.level}: {criterion.name}")
                else:
                    unmet_criteria.append(f"L{level.level}: {criterion.name}")
                    level_met = False

            if level_met:
                current_level = level.level
            else:
                break

        # Calculate progress toward next level
        current_ladder = ladder[min(current_level, len(ladder) - 1)]
        met_in_level = sum(1 for c in current_ladder.criteria if self._check_criterion(project_id, c))
        level_progress = met_in_level / len(current_ladder.criteria) if current_ladder.criteria else 1.0

        # Determine next evolution target
        if current_level < len(ladder):
            next_level = ladder[current_level]
            next_criteria = [c.name for c in next_level.criteria if not self._check_criterion(project_id, c)]
            next_evolution = f"Level {next_level.level} ({next_level.name}): Need {', '.join(next_criteria[:3])}"
        else:
            next_evolution = "Mastery achieved - focus on teaching other projects"

        return ProjectAssessment(
            project_id=project_id,
            category=category,
            current_level=current_level,
            current_level_name=ladder[min(current_level, len(ladder) - 1)].name if current_level > 0 else "Starting",
            level_progress=level_progress,
            met_criteria=met_criteria,
            unmet_criteria=unmet_criteria,
            next_evolution=next_evolution
        )

    def _check_criterion(self, project_id: str, criterion: LevelCriterion) -> bool:
        """Check if a criterion is met."""
        # Get project paths to search
        search_paths = self._get_project_paths(project_id)

        if criterion.check_type == "file_exists":
            for path in search_paths:
                if (path / criterion.check_value).exists():
                    return True
            return False

        elif criterion.check_type == "function_exists":
            for path in search_paths:
                if self._function_exists_in_path(path, criterion.check_value):
                    return True
            return False

        elif criterion.check_type == "integration":
            # Check if relationship exists and is connected
            rels = self.tracker.get_relationships(project_id)
            for rel in rels:
                if (rel["target_project"] == criterion.check_value or
                    rel["source_project"] == criterion.check_value):
                    if rel["status"] == "connected":
                        return True
            return False

        elif criterion.check_type == "metric":
            # Metric checks would need actual measurement
            # For now, return False (need implementation)
            return False

        return False

    def _get_project_paths(self, project_id: str) -> List[Path]:
        """Get filesystem paths for a project."""
        paths = []

        # Check known locations
        sam_base = Path("/Users/davidquinton/ReverseLab/SAM")
        ssot_base = Path("/Volumes/Plex/SSOT")

        # Common patterns
        patterns = [
            sam_base / "warp_tauri" / "sam_brain",
            sam_base / project_id.lower(),
            ssot_base / "projects" / f"{project_id}.md",
        ]

        for p in patterns:
            if p.exists():
                paths.append(p)

        return paths

    def _function_exists_in_path(self, path: Path, function_name: str) -> bool:
        """Check if a function exists in Python files under path."""
        import re

        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*.py"))

        pattern = rf"def\s+{function_name}\s*\("

        for file_path in files:
            try:
                content = file_path.read_text(errors='ignore')
                if re.search(pattern, content):
                    return True
            except Exception:
                continue

        return False

    def assess_all_projects(self) -> Dict[str, ProjectAssessment]:
        """Assess all known projects."""
        assessments = {}
        for project_id in PROJECT_CATEGORIES:
            assessments[project_id] = self.assess_project(project_id)
        return assessments

    def get_current_level(self, project_id: str, category: str = None) -> int:
        """Get current level for a project (convenience method)."""
        assessment = self.assess_project(project_id)
        return assessment.current_level

    def get_level_criteria(self, category: str, level: int) -> List[str]:
        """Get criteria names for a specific level in a category."""
        ladder = EVOLUTION_LADDERS.get(category, EVOLUTION_LADDERS.get("platform"))
        if not ladder:
            return []
        # Find the level (levels are 1-indexed)
        for lvl in ladder:
            if lvl.level == level:
                return [c.name for c in lvl.criteria]
        return []

    def get_evolution_roadmap(self) -> List[Dict]:
        """Get prioritized evolution roadmap across all projects."""
        assessments = self.assess_all_projects()

        roadmap = []
        for project_id, assessment in assessments.items():
            if assessment.current_level < 5:  # Not yet mastery
                roadmap.append({
                    "project": project_id,
                    "category": assessment.category,
                    "current_level": assessment.current_level,
                    "next_evolution": assessment.next_evolution,
                    "priority": 5 - assessment.current_level,  # Lower levels = higher priority
                    "unmet_count": len(assessment.unmet_criteria)
                })

        # Sort by priority (lower levels first), then by unmet count
        roadmap.sort(key=lambda x: (-x["priority"], x["unmet_count"]))
        return roadmap

    def summary(self) -> str:
        """Generate summary of all project levels."""
        assessments = self.assess_all_projects()

        lines = [
            "Evolution Ladder Summary",
            "=" * 50,
        ]

        # Group by category
        by_category = {}
        for project_id, assessment in assessments.items():
            cat = assessment.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(assessment)

        for category, projs in sorted(by_category.items()):
            lines.append(f"\n{category.upper()}:")
            for a in sorted(projs, key=lambda x: -x.current_level):
                bar = "█" * a.current_level + "░" * (5 - a.current_level)
                lines.append(f"  [{bar}] L{a.current_level} {a.project_id}")

        # Overall stats
        total = len(assessments)
        avg_level = sum(a.current_level for a in assessments.values()) / total
        lines.extend([
            "",
            f"Total Projects: {total}",
            f"Average Level: {avg_level:.1f}",
        ])

        return "\n".join(lines)


if __name__ == "__main__":
    import sys

    assessor = LadderAssessor()

    if len(sys.argv) > 1:
        project_id = sys.argv[1].upper()
        assessment = assessor.assess_project(project_id)
        print(f"\n{project_id} Assessment:")
        print(f"  Category: {assessment.category}")
        print(f"  Level: {assessment.current_level} ({assessment.current_level_name})")
        print(f"  Progress: {assessment.level_progress:.0%}")
        print(f"  Next: {assessment.next_evolution}")
        print(f"\n  Met: {', '.join(assessment.met_criteria[:5]) or 'None'}")
        print(f"  Unmet: {', '.join(assessment.unmet_criteria[:5]) or 'None'}")
    else:
        print(assessor.summary())
        print("\nTop 5 Evolution Priorities:")
        for item in assessor.get_evolution_roadmap()[:5]:
            print(f"  [{item['priority']}] {item['project']}: {item['next_evolution'][:50]}...")
