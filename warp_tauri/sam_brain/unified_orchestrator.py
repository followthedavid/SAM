#!/usr/bin/env python3
"""
SAM Unified Project Orchestrator
================================
Master system that consolidates all projects and ideas into one cohesive native setup.
SAM can understand, prioritize, build, and evolve any project autonomously.
"""

import json
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from datetime import datetime
import sqlite3
import hashlib


class ProjectStatus(Enum):
    IDEA = "idea"              # Just an idea from ChatGPT
    PLANNED = "planned"        # Has a plan but not started
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectTier(Enum):
    CORE = 1           # SAM brain, fundamental infrastructure
    PLATFORM = 2       # Major platforms (Warp, GridPlayer)
    SERVICE = 3        # Background services (media, automation)
    TOOL = 4           # Individual tools and utilities
    EXPERIMENT = 5     # Experimental/learning projects


class ProjectCategory(Enum):
    SAM_CORE = "sam_core"
    APPLE_NATIVE = "apple_native"
    MEDIA = "media"
    AUTOMATION = "automation"
    ML_TRAINING = "ml_training"
    REVERSE_ENGINEERING = "reverse_engineering"
    GAMES_3D = "games_3d"
    VOICE_AUDIO = "voice_audio"
    IMAGE_GEN = "image_gen"
    DATA_ACQUISITION = "data_acquisition"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class Project:
    """Unified project representation."""
    id: str
    name: str
    description: str
    category: ProjectCategory
    tier: ProjectTier
    status: ProjectStatus

    # Paths
    path: Optional[str] = None
    docs_path: Optional[str] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)

    # Progress
    progress_pct: int = 0
    next_action: Optional[str] = None
    blockers: List[str] = field(default_factory=list)

    # Metadata
    source: str = "registry"  # "registry", "chatgpt", "generated"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    # SAM learning
    sam_can_handle: bool = False
    escalation_needed: List[str] = field(default_factory=list)
    training_examples: int = 0


class ProjectDatabase:
    """SQLite database for unified project tracking."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "unified_projects.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    tier INTEGER,
                    status TEXT,
                    path TEXT,
                    docs_path TEXT,
                    depends_on TEXT,
                    enables TEXT,
                    progress_pct INTEGER DEFAULT 0,
                    next_action TEXT,
                    blockers TEXT,
                    source TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    tags TEXT,
                    sam_can_handle INTEGER DEFAULT 0,
                    escalation_needed TEXT,
                    training_examples INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS project_ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    idea TEXT,
                    source TEXT,
                    priority INTEGER DEFAULT 0,
                    implemented INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS project_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    action_type TEXT,
                    description TEXT,
                    result TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS dependencies (
                    from_project TEXT,
                    to_project TEXT,
                    dependency_type TEXT,
                    PRIMARY KEY (from_project, to_project),
                    FOREIGN KEY (from_project) REFERENCES projects(id),
                    FOREIGN KEY (to_project) REFERENCES projects(id)
                );

                CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
                CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);
                CREATE INDEX IF NOT EXISTS idx_projects_tier ON projects(tier);
            """)

    def save_project(self, project: Project):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO projects
                (id, name, description, category, tier, status, path, docs_path,
                 depends_on, enables, progress_pct, next_action, blockers, source,
                 created_at, updated_at, tags, sam_can_handle, escalation_needed,
                 training_examples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id, project.name, project.description,
                project.category.value, project.tier.value, project.status.value,
                project.path, project.docs_path,
                json.dumps(project.depends_on), json.dumps(project.enables),
                project.progress_pct, project.next_action, json.dumps(project.blockers),
                project.source, project.created_at, project.updated_at,
                json.dumps(project.tags), 1 if project.sam_can_handle else 0,
                json.dumps(project.escalation_needed), project.training_examples
            ))

    def get_project(self, project_id: str) -> Optional[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if row:
                return self._row_to_project(row)
        return None

    def get_all_projects(self) -> List[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM projects ORDER BY tier, name").fetchall()
            return [self._row_to_project(row) for row in rows]

    def get_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY tier, name",
                (status.value,)
            ).fetchall()
            return [self._row_to_project(row) for row in rows]

    def get_projects_by_category(self, category: ProjectCategory) -> List[Project]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM projects WHERE category = ? ORDER BY tier, name",
                (category.value,)
            ).fetchall()
            return [self._row_to_project(row) for row in rows]

    def _row_to_project(self, row) -> Project:
        return Project(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            category=ProjectCategory(row['category']),
            tier=ProjectTier(row['tier']),
            status=ProjectStatus(row['status']),
            path=row['path'],
            docs_path=row['docs_path'],
            depends_on=json.loads(row['depends_on'] or '[]'),
            enables=json.loads(row['enables'] or '[]'),
            progress_pct=row['progress_pct'],
            next_action=row['next_action'],
            blockers=json.loads(row['blockers'] or '[]'),
            source=row['source'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags=json.loads(row['tags'] or '[]'),
            sam_can_handle=bool(row['sam_can_handle']),
            escalation_needed=json.loads(row['escalation_needed'] or '[]'),
            training_examples=row['training_examples']
        )

    def add_idea(self, project_id: str, idea: str, source: str = "chatgpt", priority: int = 0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO project_ideas (project_id, idea, source, priority, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, idea, source, priority, datetime.now().isoformat()))

    def log_action(self, project_id: str, action_type: str, description: str, result: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO project_actions (project_id, action_type, description, result, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, action_type, description, result, datetime.now().isoformat()))


class UnifiedOrchestrator:
    """
    Master orchestrator that unifies all projects into one cohesive system.
    SAM uses this to understand, prioritize, and work on any project.
    """

    # Existing projects from PROJECT_REGISTRY.md
    REGISTRY_PROJECTS = {
        # Tier 1: Core Infrastructure
        "sam_brain": {
            "name": "SAM Brain",
            "description": "Core intelligence - MLX inference, personality, memory, learning",
            "category": ProjectCategory.SAM_CORE,
            "tier": ProjectTier.CORE,
            "path": "~/ReverseLab/SAM/warp_tauri/sam_brain",
            "docs_path": "/Volumes/Plex/SSOT/projects/sam_brain.md",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 70,
            "tags": ["mlx", "inference", "personality", "learning"],
            "sam_can_handle": True
        },
        "warp_tauri": {
            "name": "Warp (Tauri)",
            "description": "Main SAM interface - native macOS app with Tauri backend",
            "category": ProjectCategory.APPLE_NATIVE,
            "tier": ProjectTier.CORE,
            "path": "~/ReverseLab/SAM/warp_tauri",
            "docs_path": "/Volumes/Plex/SSOT/projects/warp.md",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 60,
            "depends_on": ["sam_brain"],
            "tags": ["tauri", "rust", "swiftui", "native"],
            "sam_can_handle": True
        },

        # Tier 2: AI/ML Training
        "mlx_training": {
            "name": "MLX Training Pipeline",
            "description": "Fine-tuning pipeline for SAM's local models",
            "category": ProjectCategory.ML_TRAINING,
            "tier": ProjectTier.PLATFORM,
            "path": "~/ReverseLab/SAM/warp_tauri/sam_brain",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 80,
            "tags": ["mlx", "lora", "fine-tuning"],
            "sam_can_handle": True
        },
        "rvc_voice": {
            "name": "RVC Voice Cloning",
            "description": "Voice model training for SAM's voice",
            "category": ProjectCategory.VOICE_AUDIO,
            "tier": ProjectTier.SERVICE,
            "path": "~/ReverseLab/SAM/scripts/rvc_train.sh",
            "status": ProjectStatus.PAUSED,
            "progress_pct": 40,
            "tags": ["voice", "rvc", "docker"],
            "escalation_needed": ["gpu_training", "docker_setup"]
        },

        # Tier 3: Media Services
        "plex_server": {
            "name": "Plex Media Server",
            "description": "Media library management and streaming",
            "category": ProjectCategory.MEDIA,
            "tier": ProjectTier.SERVICE,
            "path": "/Volumes/Plex",
            "status": ProjectStatus.COMPLETED,
            "progress_pct": 100,
            "tags": ["plex", "streaming", "media"],
            "sam_can_handle": True
        },
        "navidrome": {
            "name": "Navidrome",
            "description": "Self-hosted music streaming server",
            "category": ProjectCategory.MEDIA,
            "tier": ProjectTier.SERVICE,
            "status": ProjectStatus.COMPLETED,
            "progress_pct": 100,
            "tags": ["music", "streaming", "navidrome"],
            "sam_can_handle": True
        },
        "stash": {
            "name": "Stash",
            "description": "Media organizer with scene detection",
            "category": ProjectCategory.MEDIA,
            "tier": ProjectTier.SERVICE,
            "path": "~/ReverseLab/stash",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 75,
            "tags": ["stash", "media", "scene-detection"],
            "sam_can_handle": True
        },

        # Tier 4: Automation
        "shortcuts_integration": {
            "name": "Shortcuts Integration",
            "description": "Apple Shortcuts automation with SAM",
            "category": ProjectCategory.AUTOMATION,
            "tier": ProjectTier.SERVICE,
            "status": ProjectStatus.PLANNED,
            "progress_pct": 10,
            "tags": ["shortcuts", "automation", "apple"],
            "sam_can_handle": True
        },
        "home_automation": {
            "name": "Home Automation",
            "description": "HomeKit/smart home control via SAM",
            "category": ProjectCategory.AUTOMATION,
            "tier": ProjectTier.SERVICE,
            "status": ProjectStatus.IDEA,
            "tags": ["homekit", "automation", "smart-home"],
            "escalation_needed": ["homekit_api"]
        },

        # Tier 5: Game/Character Dev
        "unity_game": {
            "name": "Unity Game Project",
            "description": "3D game development in Unity",
            "category": ProjectCategory.GAMES_3D,
            "tier": ProjectTier.TOOL,
            "status": ProjectStatus.PAUSED,
            "progress_pct": 20,
            "tags": ["unity", "game", "3d"],
            "escalation_needed": ["3d_modeling", "game_design"]
        },
        "character_creator": {
            "name": "Character Creator",
            "description": "AI-powered character generation",
            "category": ProjectCategory.IMAGE_GEN,
            "tier": ProjectTier.TOOL,
            "status": ProjectStatus.IDEA,
            "tags": ["character", "generation", "ai"],
            "escalation_needed": ["image_generation", "stable_diffusion"]
        },

        # Tier 6: Reverse Engineering
        "frida_scripts": {
            "name": "Frida Scripts",
            "description": "iOS/macOS reverse engineering tools",
            "category": ProjectCategory.REVERSE_ENGINEERING,
            "tier": ProjectTier.TOOL,
            "path": "~/ReverseLab/frida",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 50,
            "tags": ["frida", "reverse-engineering", "ios"],
            "sam_can_handle": True
        },
        "hopper_scripts": {
            "name": "Hopper Scripts",
            "description": "Binary analysis automation",
            "category": ProjectCategory.REVERSE_ENGINEERING,
            "tier": ProjectTier.TOOL,
            "path": "~/ReverseLab/hopper",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 30,
            "tags": ["hopper", "disassembly", "analysis"],
            "sam_can_handle": True
        },

        # Tier 7: Data Acquisition
        "scraping_tools": {
            "name": "Scraping Tools",
            "description": "Web scraping and data collection",
            "category": ProjectCategory.DATA_ACQUISITION,
            "tier": ProjectTier.TOOL,
            "path": "/Volumes/David External/scraped",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 60,
            "tags": ["scraping", "data", "automation"],
            "sam_can_handle": True
        },

        # Tier 8: GridPlayer
        "gridplayer": {
            "name": "GridPlayer",
            "description": "Multi-video grid player for macOS",
            "category": ProjectCategory.MEDIA,
            "tier": ProjectTier.PLATFORM,
            "path": "~/ReverseLab/GridPlayer",
            "status": ProjectStatus.IN_PROGRESS,
            "progress_pct": 65,
            "tags": ["video", "player", "grid", "native"],
            "sam_can_handle": True
        },

        # Tier 9: StashGrid
        "stashgrid": {
            "name": "StashGrid",
            "description": "Grid interface for Stash media",
            "category": ProjectCategory.MEDIA,
            "tier": ProjectTier.TOOL,
            "path": "~/ReverseLab/StashGrid",
            "depends_on": ["stash", "gridplayer"],
            "status": ProjectStatus.PLANNED,
            "progress_pct": 15,
            "tags": ["stash", "grid", "interface"],
            "sam_can_handle": True
        },

        # Tier 10: Muse
        "muse": {
            "name": "Muse",
            "description": "AI music composition and mixing",
            "category": ProjectCategory.VOICE_AUDIO,
            "tier": ProjectTier.EXPERIMENT,
            "status": ProjectStatus.IDEA,
            "tags": ["music", "ai", "composition"],
            "escalation_needed": ["audio_processing", "music_theory"]
        }
    }

    # ChatGPT idea categories mapped to projects
    CHATGPT_IDEAS = {
        ProjectCategory.SAM_CORE: [
            "Persistent memory across sessions",
            "Emotional state modeling",
            "Context window optimization",
            "Multi-modal understanding",
            "Self-improvement loops",
            "Confidence calibration",
            "Knowledge graph building",
            "Preference learning",
            "Task decomposition",
            "Autonomous goal setting"
        ],
        ProjectCategory.APPLE_NATIVE: [
            "System-wide hotkey activation",
            "Menu bar integration",
            "Notification Center integration",
            "Spotlight-like quick launcher",
            "Widget for Desktop/Today View",
            "Share sheet extension",
            "Quick Look plugins",
            "Services menu integration",
            "Accessibility API integration",
            "Calendar/Reminders sync"
        ],
        ProjectCategory.MEDIA: [
            "Smart playlists based on mood",
            "Auto-tagging for media",
            "Scene detection improvements",
            "Thumbnail generation",
            "Watch history tracking",
            "Cross-library sync",
            "Duplicate detection",
            "Quality analysis",
            "Metadata enrichment",
            "Streaming optimization"
        ],
        ProjectCategory.AUTOMATION: [
            "Time-based automations",
            "Location-based triggers",
            "App-specific macros",
            "File organization rules",
            "Backup automation",
            "Sync workflows",
            "Notification filtering",
            "Email rules",
            "Calendar automation",
            "Smart folder management"
        ],
        ProjectCategory.ML_TRAINING: [
            "Continuous learning from interactions",
            "Domain-specific fine-tuning",
            "Multi-task training",
            "Few-shot learning optimization",
            "Model distillation",
            "Quantization experiments",
            "Adapter composition",
            "Training data curation",
            "Evaluation benchmarks",
            "A/B testing framework"
        ],
        ProjectCategory.REVERSE_ENGINEERING: [
            "Automated binary analysis",
            "Pattern detection in binaries",
            "API discovery",
            "Protocol reverse engineering",
            "Obfuscation detection",
            "Vulnerability scanning",
            "Code similarity detection",
            "Symbol recovery",
            "Dynamic analysis automation",
            "Report generation"
        ],
        ProjectCategory.GAMES_3D: [
            "Procedural content generation",
            "NPC behavior systems",
            "Dialog systems",
            "Quest generation",
            "World building tools",
            "Asset management",
            "Level design assistance",
            "Physics simulation",
            "Animation blending",
            "Performance optimization"
        ],
        ProjectCategory.VOICE_AUDIO: [
            "Real-time voice conversion",
            "Emotion in speech synthesis",
            "Voice activity detection",
            "Noise cancellation",
            "Audio transcription",
            "Speaker diarization",
            "Audio effects processing",
            "Music analysis",
            "Beat detection",
            "Stem separation"
        ],
        ProjectCategory.IMAGE_GEN: [
            "Style transfer",
            "Image upscaling",
            "Background removal",
            "Face enhancement",
            "Pose estimation",
            "Image composition",
            "Texture generation",
            "Color palette extraction",
            "Image restoration",
            "Visual similarity search"
        ]
    }

    def __init__(self):
        self.db = ProjectDatabase()
        self.brain_path = Path(__file__).parent
        self._load_registry_projects()
        self._load_chatgpt_ideas()

    def _load_registry_projects(self):
        """Load projects from the registry into the database."""
        for project_id, data in self.REGISTRY_PROJECTS.items():
            existing = self.db.get_project(project_id)
            if existing:
                continue  # Don't overwrite existing projects

            project = Project(
                id=project_id,
                name=data["name"],
                description=data["description"],
                category=data["category"],
                tier=data["tier"],
                status=data.get("status", ProjectStatus.IDEA),
                path=data.get("path"),
                docs_path=data.get("docs_path"),
                depends_on=data.get("depends_on", []),
                enables=data.get("enables", []),
                progress_pct=data.get("progress_pct", 0),
                tags=data.get("tags", []),
                source="registry",
                sam_can_handle=data.get("sam_can_handle", False),
                escalation_needed=data.get("escalation_needed", [])
            )
            self.db.save_project(project)

    def _load_chatgpt_ideas(self):
        """Load ChatGPT ideas into the database."""
        for category, ideas in self.CHATGPT_IDEAS.items():
            # Find or create a general project for this category
            category_project_id = f"chatgpt_{category.value}"
            existing = self.db.get_project(category_project_id)

            if not existing:
                project = Project(
                    id=category_project_id,
                    name=f"ChatGPT Ideas: {category.value.replace('_', ' ').title()}",
                    description=f"Ideas extracted from ChatGPT conversations for {category.value}",
                    category=category,
                    tier=ProjectTier.EXPERIMENT,
                    status=ProjectStatus.IDEA,
                    source="chatgpt"
                )
                self.db.save_project(project)

            # Add ideas
            for idea in ideas:
                self.db.add_idea(category_project_id, idea, "chatgpt")

    def get_dashboard(self) -> Dict[str, Any]:
        """Get a comprehensive dashboard of all projects."""
        all_projects = self.db.get_all_projects()

        # Group by status
        by_status = {}
        for status in ProjectStatus:
            by_status[status.value] = [p for p in all_projects if p.status == status]

        # Group by category
        by_category = {}
        for category in ProjectCategory:
            by_category[category.value] = [p for p in all_projects if p.category == category]

        # Calculate stats
        total = len(all_projects)
        completed = len(by_status.get(ProjectStatus.COMPLETED.value, []))
        in_progress = len(by_status.get(ProjectStatus.IN_PROGRESS.value, []))
        sam_handles = len([p for p in all_projects if p.sam_can_handle])

        # Find blocked projects
        blocked = [p for p in all_projects if p.blockers]

        # Find next actionable projects
        actionable = [
            p for p in all_projects
            if p.status in [ProjectStatus.PLANNED, ProjectStatus.IN_PROGRESS]
            and not p.blockers
            and p.next_action
        ]

        return {
            "total_projects": total,
            "completed": completed,
            "in_progress": in_progress,
            "sam_can_handle": sam_handles,
            "sam_parity_pct": round(sam_handles / total * 100) if total else 0,
            "by_status": {k: len(v) for k, v in by_status.items()},
            "by_category": {k: len(v) for k, v in by_category.items()},
            "blocked_count": len(blocked),
            "actionable_count": len(actionable),
            "next_actions": [
                {"project": p.name, "action": p.next_action}
                for p in actionable[:5]
            ]
        }

    def suggest_next_project(self) -> Optional[Project]:
        """Suggest the highest priority project to work on next."""
        all_projects = self.db.get_all_projects()

        # Priority scoring
        def score(p: Project) -> float:
            s = 0
            # Higher tier = lower priority (Tier 1 is most important)
            s += (6 - p.tier.value) * 100
            # In progress projects get priority
            if p.status == ProjectStatus.IN_PROGRESS:
                s += 50
            # Projects with next actions defined
            if p.next_action:
                s += 30
            # SAM can handle = bonus
            if p.sam_can_handle:
                s += 20
            # Blocked = penalty
            if p.blockers:
                s -= 100
            # Progress bonus (reward partial completion)
            s += p.progress_pct * 0.5
            return s

        # Filter to actionable projects
        actionable = [
            p for p in all_projects
            if p.status in [ProjectStatus.PLANNED, ProjectStatus.IN_PROGRESS, ProjectStatus.IDEA]
            and not p.blockers
        ]

        if not actionable:
            return None

        return max(actionable, key=score)

    def get_project_graph(self) -> Dict[str, Any]:
        """Get dependency graph of all projects."""
        all_projects = self.db.get_all_projects()

        nodes = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category.value,
                "status": p.status.value,
                "tier": p.tier.value
            }
            for p in all_projects
        ]

        edges = []
        for p in all_projects:
            for dep in p.depends_on:
                edges.append({"from": dep, "to": p.id, "type": "depends"})
            for enables in p.enables:
                edges.append({"from": p.id, "to": enables, "type": "enables"})

        return {"nodes": nodes, "edges": edges}

    def update_project_status(self, project_id: str, status: ProjectStatus,
                              progress: int = None, next_action: str = None):
        """Update a project's status and progress."""
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        project.status = status
        project.updated_at = datetime.now().isoformat()

        if progress is not None:
            project.progress_pct = min(100, max(0, progress))

        if next_action is not None:
            project.next_action = next_action

        self.db.save_project(project)
        self.db.log_action(project_id, "status_update",
                          f"Status: {status.value}, Progress: {project.progress_pct}%")

    def create_project(self, name: str, description: str,
                       category: ProjectCategory, tier: ProjectTier = ProjectTier.TOOL,
                       source: str = "generated") -> Project:
        """Create a new project."""
        project_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]

        project = Project(
            id=project_id,
            name=name,
            description=description,
            category=category,
            tier=tier,
            status=ProjectStatus.IDEA,
            source=source
        )

        self.db.save_project(project)
        self.db.log_action(project_id, "created", f"New project: {name}")

        return project

    def get_sam_capabilities_needed(self) -> Dict[str, List[str]]:
        """Identify what capabilities SAM needs to develop."""
        all_projects = self.db.get_all_projects()

        # Collect all escalation needs
        needs = {}
        for p in all_projects:
            for need in p.escalation_needed:
                if need not in needs:
                    needs[need] = []
                needs[need].append(p.name)

        return needs

    def export_for_training(self) -> List[Dict]:
        """Export project context for SAM training."""
        all_projects = self.db.get_all_projects()

        training_data = []
        for p in all_projects:
            # Create Q&A pairs about the project
            training_data.append({
                "instruction": f"What is the {p.name} project?",
                "response": f"{p.name} is {p.description}. It's a {p.category.value} project at tier {p.tier.value}. Current status: {p.status.value} ({p.progress_pct}% complete)."
            })

            if p.next_action:
                training_data.append({
                    "instruction": f"What's the next step for {p.name}?",
                    "response": p.next_action
                })

            if p.depends_on:
                training_data.append({
                    "instruction": f"What does {p.name} depend on?",
                    "response": f"{p.name} depends on: {', '.join(p.depends_on)}"
                })

        return training_data

    def print_dashboard(self):
        """Print a formatted dashboard to console."""
        dash = self.get_dashboard()

        print("\n" + "=" * 60)
        print("SAM UNIFIED PROJECT ORCHESTRATOR")
        print("=" * 60)

        print(f"\nTotal Projects: {dash['total_projects']}")
        print(f"SAM Can Handle: {dash['sam_can_handle']} ({dash['sam_parity_pct']}% parity)")
        print(f"Completed: {dash['completed']}")
        print(f"In Progress: {dash['in_progress']}")
        print(f"Blocked: {dash['blocked_count']}")

        print("\n--- By Category ---")
        for cat, count in sorted(dash['by_category'].items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {cat}: {count}")

        print("\n--- By Status ---")
        for status, count in sorted(dash['by_status'].items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {status}: {count}")

        if dash['next_actions']:
            print("\n--- Next Actions ---")
            for item in dash['next_actions']:
                print(f"  [{item['project']}] {item['action']}")

        # Suggest next project
        next_proj = self.suggest_next_project()
        if next_proj:
            print(f"\n>>> SUGGESTED NEXT: {next_proj.name}")
            print(f"    {next_proj.description}")
            if next_proj.next_action:
                print(f"    Action: {next_proj.next_action}")

        print("\n" + "=" * 60)


class NativeProjectHub:
    """
    Native macOS hub for project orchestration.
    Provides system-level integration for SAM to manage projects.
    """

    def __init__(self):
        self.orchestrator = UnifiedOrchestrator()
        self.config_path = Path.home() / ".sam" / "project_hub.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def setup_native_integration(self):
        """Set up native macOS integration."""
        # Create project-specific Spotlight metadata
        self._setup_spotlight_integration()

        # Create Quick Actions
        self._setup_quick_actions()

        # Set up file associations
        self._setup_file_associations()

    def _setup_spotlight_integration(self):
        """Create Spotlight-searchable project index."""
        index_path = Path.home() / ".sam" / "spotlight_index"
        index_path.mkdir(parents=True, exist_ok=True)

        for project in self.orchestrator.db.get_all_projects():
            # Create a metadata file for each project
            meta_file = index_path / f"{project.id}.samproject"
            meta_file.write_text(json.dumps({
                "name": project.name,
                "description": project.description,
                "category": project.category.value,
                "status": project.status.value,
                "path": project.path
            }, indent=2))

    def _setup_quick_actions(self):
        """Create Automator quick actions for project management."""
        # This would create .workflow files in ~/Library/Services
        # For now, just log the intent
        print("Quick actions would be set up for:")
        print("  - Open project in editor")
        print("  - Show project status")
        print("  - Run project tests")

    def _setup_file_associations(self):
        """Set up file type associations."""
        # Associate .samproject files with SAM
        pass

    def get_project_for_file(self, file_path: str) -> Optional[Project]:
        """Find which project a file belongs to."""
        file_path = Path(file_path).resolve()

        for project in self.orchestrator.db.get_all_projects():
            if not project.path:
                continue
            proj_path = Path(project.path).expanduser().resolve()
            try:
                file_path.relative_to(proj_path)
                return project
            except ValueError:
                continue

        return None

    def open_project(self, project_id: str):
        """Open a project in the appropriate editor."""
        project = self.orchestrator.db.get_project(project_id)
        if not project or not project.path:
            print(f"Project not found or has no path: {project_id}")
            return

        path = Path(project.path).expanduser()
        if path.exists():
            # Open in VS Code or Xcode based on project type
            if any(tag in project.tags for tag in ["swift", "xcode", "ios"]):
                subprocess.run(["open", "-a", "Xcode", str(path)])
            else:
                subprocess.run(["code", str(path)])
        else:
            print(f"Project path does not exist: {path}")


def main():
    """Main entry point for the orchestrator."""
    import sys

    orchestrator = UnifiedOrchestrator()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "dashboard":
            orchestrator.print_dashboard()

        elif command == "suggest":
            project = orchestrator.suggest_next_project()
            if project:
                print(f"Suggested: {project.name}")
                print(f"Description: {project.description}")
                print(f"Status: {project.status.value}")
                if project.next_action:
                    print(f"Next action: {project.next_action}")
            else:
                print("No actionable projects found")

        elif command == "list":
            category = sys.argv[2] if len(sys.argv) > 2 else None
            projects = orchestrator.db.get_all_projects()
            if category:
                try:
                    cat = ProjectCategory(category)
                    projects = [p for p in projects if p.category == cat]
                except ValueError:
                    print(f"Unknown category: {category}")
                    return

            for p in projects:
                status_icon = {
                    ProjectStatus.COMPLETED: "[x]",
                    ProjectStatus.IN_PROGRESS: "[>]",
                    ProjectStatus.BLOCKED: "[!]",
                    ProjectStatus.PAUSED: "[-]",
                    ProjectStatus.PLANNED: "[ ]",
                    ProjectStatus.IDEA: "[?]"
                }.get(p.status, "[ ]")
                print(f"{status_icon} {p.name} ({p.category.value}) - {p.progress_pct}%")

        elif command == "capabilities":
            needs = orchestrator.get_sam_capabilities_needed()
            print("Capabilities SAM needs to develop:")
            for capability, projects in sorted(needs.items()):
                print(f"\n  {capability}:")
                for proj in projects:
                    print(f"    - {proj}")

        elif command == "export":
            data = orchestrator.export_for_training()
            output_path = Path(__file__).parent / "data" / "project_training.jsonl"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                for item in data:
                    f.write(json.dumps(item) + '\n')
            print(f"Exported {len(data)} training examples to {output_path}")

        else:
            print(f"Unknown command: {command}")
            print("Available: dashboard, suggest, list [category], capabilities, export")

    else:
        orchestrator.print_dashboard()


if __name__ == "__main__":
    main()
