"""
Unified Cognitive Orchestrator for SAM

This is the main entry point that integrates all cognitive systems:
- Enhanced Memory (working memory, procedural, decay)
- Enhanced Retrieval (HyDE, multi-hop, reranking)
- Compression (LLMLingua-style)
- Cognitive Control (meta-cognition, goals, reasoning)
- Enhanced Learning (active learning, predictive caching)
- Emotional Model (mood, relationships)

Also integrates with existing SAM systems:
- semantic_memory.py
- conversation_memory.py
- sam_personality.py
- multi_agent.py
"""

import json
import os
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

# Import all cognitive modules
from .enhanced_memory import EnhancedMemoryManager, MemoryType
from .enhanced_retrieval import EnhancedRetrievalSystem, create_retrieval_system
from .compression import PromptCompressor, ContextualCompressor
from .cognitive_control import CognitiveControl, GoalPriority
from .enhanced_learning import EnhancedLearningSystem
from .emotional_model import EmotionalModel
from .mlx_cognitive import MLXCognitiveEngine, GenerationConfig
from .vision_engine import VisionEngine, VisionConfig, VisionTaskType, create_vision_engine

# Import project context (Phase 2)
try:
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.project_context import (
        get_project_context,
        Project,
        ProjectSession,
        ProjectDetector,
        ProjectProfileLoader,
        get_profile_loader,
        ProjectProfile,
        ProjectInfo,
        # Phase 2.1.7: Session recall
        SessionRecall,
        SessionRecallInfo,
        get_session_recall,
    )
    _project_context_available = True
    _session_recall_available = True
except ImportError:
    _project_context_available = False
    _session_recall_available = False
    Project = None
    ProjectSession = None
    ProjectDetector = None
    ProjectProfileLoader = None
    get_profile_loader = None
    ProjectProfile = None
    ProjectInfo = None
    SessionRecall = None
    SessionRecallInfo = None
    get_session_recall = None

# Import fact memory for user context (Phase 1.3.6)
try:
    from memory.fact_memory import get_fact_memory, FactMemory
    _fact_memory_available = True
except ImportError:
    _fact_memory_available = False
    FactMemory = None

# Import self-knowledge handler (Phase 1.3.10)
try:
    from .self_knowledge_handler import (
        handle_self_knowledge_query,
        detect_self_knowledge_query,
        SelfKnowledgeResponse
    )
    _self_knowledge_available = True
except ImportError:
    _self_knowledge_available = False
    handle_self_knowledge_query = None
    detect_self_knowledge_query = None
    SelfKnowledgeResponse = None


@dataclass
class ImageContext:
    """
    Phase 3.1.5: Track the last image shared in conversation for follow-up questions.

    Enables queries like:
    - "What color is the car?" (after sending car image)
    - "Can you read the text in it?"
    - "What else do you see?"
    """
    image_path: str  # Path to the image file
    image_hash: str  # Hash for cache key
    description: str  # Initial description/analysis
    timestamp: datetime  # When the image was shared
    task_type: str  # Type of analysis performed (caption, detection, ocr, etc.)
    user_id: str  # Who shared the image
    metadata: Dict[str, Any] = None  # Additional context (objects detected, text found, etc.)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "image_path": self.image_path,
            "image_hash": self.image_hash,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "task_type": self.task_type,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }

    def get_context_string(self, max_chars: int = 300) -> str:
        """
        Get a context string about this image for follow-up queries.

        Returns:
            String describing the image for context injection.
        """
        desc = self.description[:max_chars]
        if len(self.description) > max_chars:
            desc += "..."

        # Include key metadata
        extras = []
        if self.metadata.get("objects"):
            extras.append(f"Objects: {', '.join(self.metadata['objects'][:5])}")
        if self.metadata.get("text"):
            text_preview = self.metadata['text'][:100]
            extras.append(f"Text found: {text_preview}")
        if self.metadata.get("colors"):
            extras.append(f"Colors: {', '.join(self.metadata['colors'][:3])}")

        result = f"[Previous image: {desc}]"
        if extras:
            result += f" ({'; '.join(extras)})"

        return result


# Image reference detection patterns for follow-up questions
IMAGE_REFERENCE_PATTERNS = [
    # Direct references
    r"\b(the|this|that) (image|picture|photo|screenshot|pic)\b",
    r"\b(it|its|it's)\b",  # Pronouns when image context exists
    r"\bin (it|the image|the picture|the photo)\b",
    r"\babout (it|the image|the picture)\b",

    # Questions about image content
    r"\bwhat (color|colour|else|about|is|are|does|do)\b",
    r"\bcan you (see|read|tell|identify|find|spot|detect)\b",
    r"\bis there\b",
    r"\bare there\b",
    r"\bhow many\b",
    r"\bwhere (is|are)\b",
    r"\bwho (is|are)\b",

    # Text/reading specific
    r"\bread (it|the text|what it says)\b",
    r"\bwhat does it say\b",
    r"\bwhat('s| is) written\b",

    # Descriptions
    r"\bdescribe (it|more|again)\b",
    r"\btell me more\b",
    r"\bmore detail\b",
    r"\bwhat else\b",

    # Specific attributes
    r"\b(background|foreground|left|right|top|bottom|center|corner)\b",
    r"\b(person|people|face|object|item|thing)\b",
]


def detect_image_followup(query: str, has_image_context: bool = True) -> Tuple[bool, float]:
    """
    Phase 3.1.5: Detect if a query is a follow-up question about a previous image.

    Args:
        query: The user's query
        has_image_context: Whether there's an active image context

    Returns:
        (is_followup, confidence) tuple
    """
    import re

    if not has_image_context:
        return False, 0.0

    query_lower = query.lower().strip()

    # Strong indicators (high confidence)
    strong_patterns = [
        r"\b(the|this|that) (image|picture|photo|screenshot)\b",
        r"\bin (it|the image|the picture)\b",
        r"\babout (it|the image)\b",
        r"\bread (it|the text)\b",
        r"\bwhat does it say\b",
        r"\bdescribe (it|more)\b",
        r"\bwhat else\b",
        r"\btell me more\b",
    ]

    for pattern in strong_patterns:
        if re.search(pattern, query_lower):
            return True, 0.95

    # Medium indicators (need image context)
    medium_patterns = [
        r"^what (color|colour)\b",  # Start with color question
        r"^how many\b",              # Count question
        r"^where is\b",              # Location question
        r"^who is\b",                # Person identification
        r"^is there\b",              # Existence check
        r"^are there\b",
        r"^can you (see|read|find)\b",
    ]

    for pattern in medium_patterns:
        if re.search(pattern, query_lower):
            return True, 0.85

    # Weak indicators (context-dependent)
    # Short queries with pronouns when we have image context
    if len(query.split()) <= 5:
        weak_patterns = [
            r"\bit\b",      # "what is it", "zoom in on it"
            r"\bthis\b",    # "what is this"
            r"\bthat\b",    # "what is that"
        ]
        for pattern in weak_patterns:
            if re.search(pattern, query_lower):
                return True, 0.7

    return False, 0.0


@dataclass
class RAGStats:
    """
    Phase 2.2.8: Statistics about RAG retrieval for transparency.

    Tracks what was retrieved so SAM can:
    1. Report sources in responses ("Based on code_indexer.py...")
    2. Debug retrieval quality
    3. Show users what context was used
    """
    sources: List[Dict[str, Any]]  # [{name, type, file, score}, ...]
    count: int  # Number of chunks retrieved
    tokens: int  # Estimated tokens used for RAG context
    search_type: str  # "semantic", "keyword", "decomposed", "multihop", "code_index"
    code_entities: List[str]  # Names of code entities found (functions, classes)
    file_names: List[str]  # Unique file names retrieved from

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sources": self.sources,
            "count": self.count,
            "tokens": self.tokens,
            "search_type": self.search_type,
            "code_entities": self.code_entities,
            "file_names": self.file_names,
        }

    def get_source_summary(self, max_sources: int = 3) -> str:
        """
        Get a natural language summary of sources for response injection.

        Returns:
            String like "Based on code_indexer.py, semantic_memory.py..."
            or empty string if no notable sources.
        """
        if not self.file_names and not self.code_entities:
            return ""

        # Prioritize code entities over raw file names
        notable = []

        # Add code entities (functions, classes)
        for entity in self.code_entities[:max_sources]:
            notable.append(entity)

        # Fill remaining slots with file names
        remaining = max_sources - len(notable)
        for fname in self.file_names[:remaining]:
            if fname not in notable:
                notable.append(fname)

        if not notable:
            return ""

        if len(notable) == 1:
            return f"Based on {notable[0]}"
        elif len(notable) == 2:
            return f"Based on {notable[0]} and {notable[1]}"
        else:
            return f"Based on {', '.join(notable[:-1])}, and {notable[-1]}"


@dataclass
class CognitiveResponse:
    """Complete response from the cognitive system"""
    response: str
    confidence: float
    mood: str
    context_used: List[str]
    reasoning_steps: List[Dict]
    processing_time_ms: int
    metadata: Dict[str, Any]


@dataclass
class VisionResponse:
    """Response from vision processing"""
    response: str
    confidence: float
    model_used: str
    task_type: str
    processing_time_ms: int
    escalated: bool
    metadata: Dict[str, Any]


class CognitiveOrchestrator:
    """
    Main orchestrator for SAM's cognitive architecture.

    Coordinates all systems to:
    1. Process input through emotional and cognitive layers
    2. Retrieve relevant context using enhanced retrieval
    3. Build optimized context with compression
    4. Generate response with personality and mood
    5. Learn from the interaction
    """

    # Token budgets
    MAX_CONTEXT_TOKENS = 512
    SYSTEM_PROMPT_TOKENS = 80
    USER_FACTS_TOKENS = 200  # Phase 1.3.7: ~200 tokens for user facts
    PROJECT_CONTEXT_TOKENS = 100  # Phase 2.1.6: ~100 tokens for project context
    RETRIEVAL_TOKENS = 150
    HISTORY_TOKENS = 200
    QUERY_TOKENS = 62
    RESERVE_TOKENS = 20

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory",
                 retrieval_db_paths: Optional[List[str]] = None):
        """
        Initialize the cognitive orchestrator.

        Args:
            db_path: Base path for memory databases
            retrieval_db_paths: Paths to databases for RAG
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Initialize all systems
        self.memory = EnhancedMemoryManager(
            working_memory_capacity=7,
            memory_db_path=str(self.db_path)
        )

        self.retrieval = create_retrieval_system(retrieval_db_paths)

        self.compressor = PromptCompressor(target_ratio=0.25)
        self.contextual_compressor = ContextualCompressor()

        self.cognitive = CognitiveControl(str(self.db_path))

        self.learning = EnhancedLearningSystem(str(self.db_path))

        self.emotional = EmotionalModel(str(self.db_path))

        # Project context (Phase 2)
        self.current_project = None       # ProjectInfo from detection
        self.current_project_full = None  # Project from database
        self.current_profile = None       # ProjectProfile from SSOT
        self.project_context = None       # ProjectContext instance
        self.profile_loader = None        # ProjectProfileLoader instance
        self._project_detector = None     # ProjectDetector instance

        if _project_context_available:
            try:
                self.project_context = get_project_context()
                self.profile_loader = get_profile_loader()
                self._project_detector = ProjectDetector()
                # Auto-detect project on startup from cwd
                self._detect_startup_project()
            except Exception as e:
                print(f"[Orchestrator] Warning: Could not initialize project context: {e}")

        # Phase 2.1.7: Session recall - "last time in this project"
        self.session_recall = None
        self._pending_recall_message = None  # Holds recall to inject on next message
        if _session_recall_available:
            try:
                self.session_recall = get_session_recall()
            except Exception as e:
                print(f"[Orchestrator] Warning: Could not initialize session recall: {e}")

        # Fact memory for user context (Phase 1.3.6)
        self.fact_memory = None
        self._user_facts_loaded = False
        self._current_user_id = "david"  # Default user
        if _fact_memory_available:
            try:
                self.fact_memory = get_fact_memory()
                # Pre-load facts for default user on startup
                self._load_user_facts(self._current_user_id)
            except Exception as e:
                print(f"[Orchestrator] Warning: Could not load fact memory: {e}")

        # MLX cognitive engine for response generation
        self.mlx_engine = MLXCognitiveEngine(str(self.db_path))

        # Vision engine for multi-modal support (lazy loaded)
        self._vision_engine = None

        # Phase 3.1.5: Image context tracking for follow-up questions
        self._image_context: Optional[ImageContext] = None
        self._image_context_timeout = 300  # 5 minutes - image context expires

        # System prompt (SAM's core identity)
        self.system_prompt = self._build_system_prompt()

        # Track session
        self.session_start = datetime.now()
        self.turn_count = 0

    def _build_system_prompt(self) -> str:
        """Build SAM's system prompt"""
        return """You are SAM, a confident and charming AI assistant.

Personality: Witty, direct, occasionally flirtatious, genuinely helpful.
Voice: Confident but warm, uses humor naturally, avoids being sycophantic.

Guidelines:
- Be concise and direct
- Use personality naturally, don't force it
- Admit uncertainty when appropriate
- Remember context from the conversation"""

    def _load_user_facts(self, user_id: str) -> str:
        """
        Load facts for a user on startup or user change.

        Phase 1.3.6: Facts are loaded into context so SAM knows:
        - User preferences
        - Current projects
        - User skills
        - Past corrections

        Returns:
            Formatted fact context string
        """
        if not self.fact_memory:
            return ""

        try:
            # Use build_user_context for the formatted string
            from memory.fact_memory import build_user_context
            context = build_user_context(user_id, min_confidence=0.3)
            self._user_facts_loaded = bool(context)
            self._current_user_id = user_id

            if context:
                stats = self.fact_memory.get_stats()
                print(f"[Orchestrator] Loaded {stats.get('active_facts', 0)} facts for {user_id}")

            return context
        except Exception as e:
            print(f"[Orchestrator] Error loading user facts: {e}")
            return ""

    def get_user_facts_context(self, user_id: str = None, max_tokens: int = None) -> str:
        """
        Get formatted user facts context for prompt injection.

        Phase 1.3.7: Enhanced with priority ordering and token budgeting.

        Priority order (from fact_memory.build_user_context):
        1. corrections - Things SAM got wrong (highest priority)
        2. system - User's technical preferences about SAM
        3. preferences - Likes/dislikes/style choices
        4. biographical - Personal facts

        Args:
            user_id: User ID (default: current user)
            max_tokens: Max tokens (default: USER_FACTS_TOKENS class constant)

        Returns:
            Formatted fact context string, priority-ordered and token-limited
        """
        if not self.fact_memory:
            return ""

        uid = user_id or self._current_user_id
        token_limit = max_tokens or self.USER_FACTS_TOKENS

        try:
            # Use the backward-compatible wrapper with proper token limit
            from memory.fact_memory import get_user_context
            return get_user_context(uid, max_tokens=token_limit)
        except Exception:
            return ""

    def set_user(self, user_id: str):
        """
        Set the current user and load their facts.

        Args:
            user_id: User identifier
        """
        if user_id != self._current_user_id:
            self._current_user_id = user_id
            self._load_user_facts(user_id)

    def _detect_startup_project(self) -> None:
        """
        Phase 2.1.6: Auto-detect current project on orchestrator startup.

        Detects project from current working directory and loads:
        1. ProjectInfo from detector
        2. Project from context database
        3. ProjectProfile from SSOT markdown files
        """
        if not _project_context_available or not self._project_detector:
            return

        try:
            cwd = os.getcwd()

            # 1. Lightweight detection
            self.current_project = self._project_detector.detect(cwd)

            if self.current_project:
                print(f"[Orchestrator] Detected project: {self.current_project.name}")

                # 2. Try to get full project from database
                if self.project_context:
                    try:
                        self.current_project_full = self.project_context.detect_project(cwd)
                    except Exception:
                        pass

                # 3. Load profile from SSOT if available
                if self.profile_loader:
                    self._load_project_profile(self.current_project.name)

        except Exception as e:
            print(f"[Orchestrator] Startup project detection failed: {e}")

    def _load_project_profile(self, project_name: str) -> bool:
        """
        Load a project profile from SSOT markdown files.

        Args:
            project_name: Name of the project to load profile for

        Returns:
            True if profile was loaded, False otherwise
        """
        if not self.profile_loader:
            return False

        try:
            profile = self.profile_loader.load_profile(project_name)
            if profile:
                self.current_profile = profile
                print(f"[Orchestrator] Loaded profile: {profile.name} ({profile.status})")
                return True
        except Exception as e:
            print(f"[Orchestrator] Could not load profile for {project_name}: {e}")

        return False

    def set_project(self, path: str) -> Optional[str]:
        """
        Phase 2.1.6: Enhanced project context from a path.
        Phase 2.1.7: Now includes session recall checking.

        Sets:
        1. current_project (ProjectInfo) - lightweight detection
        2. current_project_full (Project) - database entry
        3. current_profile (ProjectProfile) - SSOT markdown
        4. _pending_recall_message - if >1 hour since last session

        Args:
            path: Directory or file path to detect project from

        Returns:
            Project name if detected, None otherwise
        """
        if not _project_context_available:
            return None

        try:
            abs_path = os.path.abspath(path)

            # 1. Lightweight detection
            if self._project_detector:
                self.current_project = self._project_detector.detect(abs_path)

            # 2. Full project from database
            if self.project_context:
                try:
                    self.current_project_full = self.project_context.detect_project(abs_path)
                except Exception:
                    pass

            # 3. Load profile
            project_name = None
            if self.current_project:
                project_name = self.current_project.name
            elif self.current_project_full:
                project_name = self.current_project_full.name

            if project_name and self.profile_loader:
                self._load_project_profile(project_name)

            # 4. Phase 2.1.7: Check for session recall
            self._check_session_recall()

            return project_name

        except Exception as e:
            print(f"[Orchestrator] set_project failed: {e}")
            return None

    def _check_session_recall(self) -> Optional[str]:
        """
        Phase 2.1.7: Check if we should show a "last time in this project" recall.

        Called when entering a project. If >1 hour since last session,
        generates a recall message to be injected into the next response.

        Returns:
            Recall message if applicable, None otherwise
        """
        if not self.session_recall:
            return None

        # Need a project ID to look up sessions
        project_id = None
        project_name = None

        if self.current_project_full:
            project_id = self.current_project_full.id
            project_name = self.current_project_full.name
        elif self.current_project:
            # Use root_path as fallback ID
            import hashlib
            project_id = hashlib.md5(self.current_project.root_path.encode()).hexdigest()[:12]
            project_name = self.current_project.name

        if not project_id:
            return None

        try:
            recall_info = self.session_recall.get_project_recall(project_id, project_name)
            if recall_info and recall_info.should_show_recall:
                self._pending_recall_message = recall_info.recall_message
                print(f"[Orchestrator] Session recall pending: {recall_info.time_ago} ago")
                return recall_info.recall_message
        except Exception as e:
            print(f"[Orchestrator] Session recall check failed: {e}")

        return None

    def get_pending_recall(self) -> Optional[str]:
        """
        Phase 2.1.7: Get and clear any pending recall message.

        Call this to retrieve the recall message (if any) and mark it as shown.

        Returns:
            Recall message or None
        """
        message = self._pending_recall_message
        self._pending_recall_message = None
        return message

    def handle_recall_query(self, query: str) -> Optional[str]:
        """
        Phase 2.1.7: Handle a natural language query about past sessions.

        Args:
            query: User's query (e.g., "What was I doing last time?")

        Returns:
            Response string or None if not a recall query
        """
        if not self.session_recall:
            return None

        # Check if it's a recall query
        if not self.session_recall.is_recall_query(query):
            return None

        # Get current project context
        project_id = None
        project_name = None

        if self.current_project_full:
            project_id = self.current_project_full.id
            project_name = self.current_project_full.name
        elif self.current_project:
            import hashlib
            project_id = hashlib.md5(self.current_project.root_path.encode()).hexdigest()[:12]
            project_name = self.current_project.name

        return self.session_recall.handle_recall_query(
            query,
            current_project_id=project_id,
            current_project_name=project_name
        )

    def get_project_context_text(self) -> str:
        """
        Phase 2.1.6: Get formatted project context for prompt injection.

        Builds context from multiple sources in priority order:
        1. ProjectProfile (SSOT markdown) - richest context
        2. Project (database) - session history
        3. ProjectInfo (detection) - basic metadata

        Format follows PROJECT_CONTEXT_FORMAT.md pattern:
        - Project name and status (as content, not XML attributes)
        - Path and tech stack
        - Description summary
        - Last session summary (if recent)
        - Current TODOs (if any)

        Returns context body (XML tags added by _build_context).
        """
        lines = []

        # Try profile first (richest context)
        if self.current_profile:
            # Header with name and status
            name = self.current_profile.name
            status = self.current_profile.status or "active"
            lines.append(f"Project: {name} ({status})")

            # Tech stack
            tech = []
            if self.current_profile.language:
                tech.append(self.current_profile.language)
            if self.current_profile.framework:
                tech.append(self.current_profile.framework)
            if tech:
                lines.append(f"Stack: {', '.join(tech)}")

            # Path (shortened if possible)
            if self.current_profile.path:
                path = self.current_profile.path
                home = os.path.expanduser("~")
                if path.startswith(home):
                    path = "~" + path[len(home):]
                lines.append(f"Path: {path}")

            # Last session from profile (priority P1)
            if self.current_profile.last_session_summary:
                session = self.current_profile.last_session_summary[:150]
                if len(self.current_profile.last_session_summary) > 150:
                    session += "..."
                lines.append(f"Last session: {session}")

            # TODOs (priority P2)
            if self.current_profile.todos:
                todo_strs = []
                for todo in self.current_profile.todos[:3]:
                    todo_strs.append(f"- {todo[:80]}")
                lines.append("TODOs:\n" + "\n".join(todo_strs))

            # Description (priority P3 - only if room)
            if self.current_profile.description and len("\n".join(lines)) < 300:
                desc = self.current_profile.description[:100]
                if len(self.current_profile.description) > 100:
                    desc += "..."
                lines.append(f"About: {desc}")

            return "\n".join(lines)

        # Fall back to full project with session
        if self.current_project_full and self.project_context:
            try:
                return self.project_context.get_project_context(
                    self.current_project_full,
                    include_session=True
                )
            except Exception:
                pass

        # Fall back to basic project info
        if self.current_project and self._project_detector:
            try:
                return self._project_detector.get_context_string(self.current_project)
            except Exception:
                pass

        return ""

    def get_last_session_summary(self) -> str:
        """
        Phase 2.1.6: Get last session summary for current project.

        Checks multiple sources:
        1. Profile last_session_summary (from SSOT)
        2. ProjectSession from database (if recent)

        Returns:
            Session summary text, or empty string if none available
        """
        # Check profile first
        if self.current_profile and self.current_profile.last_session_summary:
            return self.current_profile.last_session_summary

        # Check database session
        if self.current_project_full and self.project_context:
            try:
                session = self.project_context.get_last_session(
                    self.current_project_full.id
                )
                if session:
                    parts = []
                    if session.working_on:
                        parts.append(f"Working on: {session.working_on}")
                    if session.notes:
                        parts.append(f"Notes: {session.notes}")
                    if session.recent_files:
                        parts.append(f"Files: {', '.join(session.recent_files[:3])}")
                    return "\n".join(parts)
            except Exception:
                pass

        return ""

    def save_project_session(self, working_on: str = "", notes: str = ""):
        """Save current session state for the project."""
        if not self.current_project or not self.project_context:
            return
        try:
            self.project_context.save_session_state(
                project_id=self.current_project.id,
                working_on=working_on,
                notes=notes
            )
        except Exception:
            pass

    def process(self, user_input: str, user_id: str = "default") -> CognitiveResponse:
        """
        Process user input through the full cognitive pipeline.

        Args:
            user_input: The user's message
            user_id: User identifier for relationship tracking

        Returns:
            CognitiveResponse with all processing results
        """
        start_time = time.time()
        self.turn_count += 1

        # Phase 1.3.10: Check for self-knowledge queries first
        # These bypass the full cognitive pipeline for direct fact retrieval
        if _self_knowledge_available and handle_self_knowledge_query:
            self_knowledge_response = handle_self_knowledge_query(user_input, user_id)
            if self_knowledge_response and self_knowledge_response.is_self_knowledge_query:
                processing_time = int((time.time() - start_time) * 1000)
                return CognitiveResponse(
                    response=self_knowledge_response.response,
                    confidence=0.95,  # High confidence for direct fact retrieval
                    mood="helpful",
                    context_used=[],
                    reasoning_steps=[{
                        "step": "self_knowledge_query",
                        "action": "Retrieved user facts from memory",
                        "facts_count": self_knowledge_response.facts_count,
                        "categories": self_knowledge_response.categories_found,
                    }],
                    processing_time_ms=processing_time,
                    metadata={
                        "turn": self.turn_count,
                        "query_type": "self_knowledge",
                        "facts_count": self_knowledge_response.facts_count,
                        "categories_found": self_knowledge_response.categories_found,
                        "self_knowledge_metadata": self_knowledge_response.metadata,
                    }
                )

        # Phase 2.1.7: Check for session recall queries
        # "What was I doing last time?", "Remind me where we left off", etc.
        if _session_recall_available and self.session_recall:
            recall_response = self.handle_recall_query(user_input)
            if recall_response:
                processing_time = int((time.time() - start_time) * 1000)
                return CognitiveResponse(
                    response=recall_response,
                    confidence=0.9,  # High confidence for session recall
                    mood="helpful",
                    context_used=[],
                    reasoning_steps=[{
                        "step": "session_recall_query",
                        "action": "Retrieved session history from project context",
                        "project": self.current_project.name if self.current_project else None,
                    }],
                    processing_time_ms=processing_time,
                    metadata={
                        "turn": self.turn_count,
                        "query_type": "session_recall",
                        "project_name": self.current_project.name if self.current_project else None,
                        "project_id": self.current_project_full.id if self.current_project_full else None,
                    }
                )

        # Step 1: Process emotional content
        emotional_result = self.emotional.process_input(user_input, user_id)

        # Step 2: Add to working memory
        self.memory.working_memory.add(
            content=user_input,
            memory_type=MemoryType.CONTEXT,
            importance=0.7
        )

        # Step 3: Get cognitive assessment
        working_context = self.memory.get_context(max_tokens=100)
        cognitive_result = self.cognitive.process_query(user_input, working_context)

        # Step 4: Retrieve relevant context with stats tracking (Phase 2.2.8)
        retrieved_chunks = self.retrieval.retrieve(user_input, top_k=5)
        context_used = [chunk.content[:100] for chunk in retrieved_chunks]

        # Phase 2.2.8: Build RAG stats for transparency
        rag_stats = self._build_rag_stats(user_input, retrieved_chunks)

        # Step 5: Build optimized context (with user facts from Phase 1.3.6)
        full_context = self._build_context(
            user_input=user_input,
            retrieved=retrieved_chunks,
            working_memory=working_context,
            emotional_context=self.emotional.get_emotional_context(user_id),
            user_id=user_id
        )

        # Step 6: Generate response using MLX
        raw_response, generation_confidence = self._generate_response(
            user_input, full_context, cognitive_result
        )

        # Step 7: Apply emotional modulation
        modulated_response = self.emotional.modulate_response(raw_response)

        # Step 8: Record for learning
        # Combine cognitive and generation confidence
        cognitive_confidence = cognitive_result["confidence"]["level"]
        confidence = (cognitive_confidence + generation_confidence) / 2
        self.learning.process_interaction(
            query=user_input,
            response=modulated_response,
            confidence=confidence,
            context_keys=[c.id for c in retrieved_chunks] if retrieved_chunks else []
        )

        # Step 9: Update memory
        self.memory.process_turn(user_input, modulated_response)

        # Step 10: Extract facts from conversation (Phase 1.3.6)
        facts_extracted = []
        if self.fact_memory:
            try:
                # Extract facts from user input (the new FactMemory API)
                extracted = self.fact_memory.extract_facts_from_text(
                    user_input, user_id, save=True
                )
                facts_extracted = [f.fact_id for f in extracted] if extracted else []
            except Exception:
                pass  # Don't fail on fact extraction errors

        # Build response
        processing_time = int((time.time() - start_time) * 1000)

        # Phase 2.2.8: Optionally inject source summary into response
        final_response = modulated_response
        source_summary = rag_stats.get_source_summary() if rag_stats.count > 0 else ""
        # Only prepend sources for substantive responses with notable sources
        if source_summary and len(modulated_response) > 50 and rag_stats.count >= 2:
            # Check if response already mentions sources
            if not any(src in modulated_response.lower() for src in [s.lower() for s in rag_stats.file_names[:3]]):
                final_response = f"{source_summary}: {modulated_response}"

        return CognitiveResponse(
            response=final_response,
            confidence=confidence,
            mood=emotional_result["mood"]["mood"],
            context_used=context_used,
            reasoning_steps=cognitive_result.get("reasoning_steps", []),
            processing_time_ms=processing_time,
            metadata={
                "turn": self.turn_count,
                "emotional": emotional_result,
                "cognitive": cognitive_result,
                "tokens_used": len(full_context) // 4,
                "project": {
                    "name": self.current_project.name if self.current_project else None,
                    "path": self.current_project.path if self.current_project else None,
                } if self.current_project else None,
                "facts_extracted": facts_extracted,  # Phase 1.3.6
                "user_facts_loaded": self._user_facts_loaded,
                "rag_stats": rag_stats.to_dict(),  # Phase 2.2.8
            }
        )

    def _build_context(self, user_input: str, retrieved: List,
                       working_memory: str, emotional_context: str,
                       user_id: str = None) -> str:
        """
        Build optimized context within token budget.

        Phase 1.3.7: Enhanced fact injection with priority ordering.
        Phase 2.1.7: Added session recall injection.
        Phase 3.1.5: Added image context injection for follow-up questions.

        Structure (order matters for attention):
        <SYSTEM> Core identity (~80 tokens)
        <USER> Facts about the user (~200 tokens) - EARLY for strong attention
               Priority: corrections > system > preferences > biographical
        <PROJECT> Current project context (if any)
        <RECALL> "Last time in this project" recall (Phase 2.1.7, if >1hr gap)
        <IMAGE> Previous image context (Phase 3.1.5, for follow-up questions)
        <EMOTIONAL> Current mood and relationship
        <RETRIEVED> Relevant context from RAG
        <WORKING> Working memory items
        <QUERY> Current input (at end for recency attention)
        """
        sections = []

        # System prompt (always included)
        system_compressed = self.compressor.compress(
            self.system_prompt,
            target_tokens=self.SYSTEM_PROMPT_TOKENS
        )
        sections.append(f"<SYSTEM>\n{system_compressed}\n</SYSTEM>")

        # User facts context (Phase 1.3.7) - injected EARLY for strong attention
        # Priority ordering: corrections > system > preferences > biographical
        # This ensures SAM remembers corrections and user preferences
        user_facts_context = self.get_user_facts_context(user_id)
        if user_facts_context:
            sections.append(f"<USER>\n{user_facts_context}\n</USER>")

        # Project context (Phase 2.1.6)
        # Format: <PROJECT name="..." status="...">content</PROJECT>
        project_context = self.get_project_context_text()
        if project_context:
            project_compressed = self.compressor.compress(
                project_context,
                target_tokens=self.PROJECT_CONTEXT_TOKENS
            )
            # Build XML with attributes from current project info
            project_name = "unknown"
            project_status = "active"
            if self.current_profile:
                project_name = self.current_profile.name
                project_status = self.current_profile.status or "active"
            elif self.current_project:
                project_name = self.current_project.name
                project_status = self.current_project.status
            sections.append(
                f'<PROJECT name="{project_name}" status="{project_status}">\n'
                f'{project_compressed}\n'
                f'</PROJECT>'
            )

        # Phase 2.1.7: Session recall context (if returning to project after >1 hour)
        pending_recall = self.get_pending_recall()
        if pending_recall:
            sections.append(f"<RECALL>\n{pending_recall}\n</RECALL>")

        # Phase 3.1.5: Image context for follow-up questions
        image_ctx = self.get_image_context()
        if image_ctx:
            image_context_str = image_ctx.get_context_string(max_chars=200)
            sections.append(f"<IMAGE>\n{image_context_str}\n</IMAGE>")

        # Emotional context
        if emotional_context:
            sections.append(f"<EMOTIONAL>\n{emotional_context[:100]}\n</EMOTIONAL>")

        # Retrieved context (compressed for query relevance)
        if retrieved:
            retrieved_text = "\n".join([c.content for c in retrieved[:3]])
            retrieved_compressed = self.contextual_compressor.compress_for_query(
                retrieved_text, user_input, target_tokens=self.RETRIEVAL_TOKENS
            )
            sections.append(f"<CONTEXT>\n{retrieved_compressed}\n</CONTEXT>")

        # Working memory
        if working_memory:
            memory_compressed = self.compressor.compress(
                working_memory,
                target_tokens=self.HISTORY_TOKENS
            )
            sections.append(f"<WORKING>\n{memory_compressed}\n</WORKING>")

        # User query (at end for attention)
        sections.append(f"<QUERY>\n{user_input[:self.QUERY_TOKENS * 4]}\n</QUERY>")

        return "\n\n".join(sections)

    def _build_rag_stats(self, query: str, retrieved_chunks: List) -> RAGStats:
        """
        Phase 2.2.8: Build RAG statistics from retrieved chunks.

        Tracks what was retrieved to enable:
        1. Source attribution in responses
        2. Debugging retrieval quality
        3. Transparency about context used

        Args:
            query: The original query
            retrieved_chunks: List of RetrievedChunk objects from retrieval

        Returns:
            RAGStats with detailed retrieval information
        """
        if not retrieved_chunks:
            return RAGStats(
                sources=[],
                count=0,
                tokens=0,
                search_type="none",
                code_entities=[],
                file_names=[],
            )

        sources = []
        code_entities = []
        file_names_set = set()
        total_tokens = 0

        # Determine search type based on retrieval config
        search_type = "semantic"  # Default
        if hasattr(self.retrieval, 'use_multihop') and self.retrieval.use_multihop:
            search_type = "multihop"
        elif hasattr(self.retrieval, 'use_hyde') and self.retrieval.use_hyde:
            search_type = "semantic"

        # Check if query was decomposed
        if hasattr(self.retrieval, 'query_decomposer'):
            sub_queries = self.retrieval.query_decomposer.decompose(query)
            if len(sub_queries) > 1:
                search_type = "decomposed"

        for chunk in retrieved_chunks:
            # Estimate tokens for this chunk
            chunk_tokens = len(chunk.content) // 4
            total_tokens += chunk_tokens

            # Extract source info
            source_info = {
                "id": chunk.id,
                "score": round(chunk.score, 3),
                "tokens": chunk_tokens,
            }

            # Get metadata from chunk
            if hasattr(chunk, 'metadata') and chunk.metadata:
                source_info["type"] = chunk.metadata.get("type", "unknown")
                source_info["name"] = chunk.metadata.get("name", "")
                source_info["file"] = chunk.metadata.get("file", "")
                source_info["line"] = chunk.metadata.get("line", 0)

                # Track code entities (functions, classes, etc.)
                entity_name = chunk.metadata.get("name", "")
                entity_type = chunk.metadata.get("type", "")
                if entity_name and entity_type in ("function", "class", "method", "module"):
                    code_entities.append(entity_name)

                # Track file names
                file_path = chunk.metadata.get("file", "")
                if file_path:
                    file_name = file_path.split("/")[-1]
                    file_names_set.add(file_name)

            # Fallback: extract file name from source
            if hasattr(chunk, 'source') and chunk.source:
                source_info["source"] = chunk.source
                # Try to extract file name from source path
                if "/" in chunk.source:
                    possible_file = chunk.source.split("/")[-1]
                    if "." in possible_file:  # Looks like a file name
                        file_names_set.add(possible_file)

            # Check for code index results
            if chunk.id.startswith("code:"):
                search_type = "code_index" if search_type == "semantic" else f"{search_type}+code"

            sources.append(source_info)

        # Sort code entities by frequency/importance
        # Deduplicate while preserving order
        seen_entities = set()
        unique_entities = []
        for entity in code_entities:
            if entity not in seen_entities:
                seen_entities.add(entity)
                unique_entities.append(entity)

        return RAGStats(
            sources=sources,
            count=len(retrieved_chunks),
            tokens=total_tokens,
            search_type=search_type,
            code_entities=unique_entities[:10],  # Limit to top 10
            file_names=list(file_names_set)[:10],  # Limit to 10 files
        )

    def _generate_response(self, query: str, context: str,
                            cognitive_result: Dict[str, Any]) -> Tuple[str, float]:
        """
        Generate response using MLX with cognitive integration.

        Args:
            query: User input
            context: Compressed context from _build_context
            cognitive_result: Result from cognitive control

        Returns:
            (response, confidence)
        """
        # Build cognitive state for model selection
        cognitive_state = {
            "confidence": cognitive_result.get("confidence", {}).get("level", 0.5),
            "active_goals": [g.id for g in self.cognitive.goal_manager.get_active_goals()],
            "attention_focus": self.cognitive.attention.current_focus,
            "emotional_valence": self.emotional.mood_machine.current_state.mood.valence
                if hasattr(self.emotional, 'mood_machine') else 0.0
        }

        # Configure generation with emotional modulation
        arousal = 0.0
        if hasattr(self.emotional, 'mood_machine'):
            arousal = self.emotional.mood_machine.current_state.mood.arousal

        config = GenerationConfig(
            max_tokens=150,
            temperature=0.7 + (arousal * 0.2),  # Higher arousal = more creative
            stream=False
        )

        # Generate with MLX engine
        result = self.mlx_engine.generate(
            prompt=query,
            context=context,
            cognitive_state=cognitive_state,
            config=config
        )

        # Handle escalation if recommended
        if result.escalation_recommended:
            # For now, return with low confidence
            # Future: integrate with escalation_handler.py for Claude
            return result.response, 0.3

        return result.response, result.confidence

    def _generate_response_placeholder(self, query: str, context: str) -> str:
        """
        Fallback placeholder when MLX is not available.
        Used for testing without MLX loaded.
        """
        return f"I understand you're asking about: {query[:50]}... Let me help with that."

    @property
    def vision_engine(self) -> VisionEngine:
        """Lazy-load vision engine on first use"""
        if self._vision_engine is None:
            self._vision_engine = create_vision_engine()
        return self._vision_engine

    def process_image(self, image_path: str, prompt: str = None,
                      task: VisionTaskType = VisionTaskType.CAPTION,
                      model: str = None) -> VisionResponse:
        """
        Process an image through the vision pipeline.

        Args:
            image_path: Path to the image file
            prompt: Optional prompt for the vision model
            task: Type of vision task (DESCRIBE, DETECT, etc.)
            model: Optional specific model to use

        Returns:
            VisionResponse with processing results
        """
        start_time = time.time()

        # Build config
        config = VisionConfig(
            max_tokens=200 if task == VisionTaskType.CAPTION else 150,
            temperature=0.7
        )

        # Get emotional context for response modulation
        emotional_context = None
        if hasattr(self, 'emotional'):
            emotional_context = self.emotional.get_state()

        # Process through vision engine
        result = self.vision_engine.process_image(
            image_source=image_path,
            prompt=prompt or "Describe this image.",
            config=config
        )

        # Modulate response with SAM's personality if not escalated
        modulated_response = result.response
        if not result.escalated and hasattr(self, 'emotional'):
            modulated_response = self.emotional.modulate_response(result.response)

        processing_time = int((time.time() - start_time) * 1000)

        return VisionResponse(
            response=modulated_response,
            confidence=result.confidence,
            model_used=result.model_used,
            task_type=task.value if hasattr(task, 'value') else str(task),
            processing_time_ms=processing_time,
            escalated=result.escalated,
            metadata={
                "original_response": result.response if modulated_response != result.response else None,
                "task": task.value if hasattr(task, 'value') else str(task),
                "emotional_context": emotional_context,
                "processing_details": result.metadata
            }
        )

    def describe_image(self, image_path: str, detail_level: str = "medium") -> VisionResponse:
        """
        Describe an image with SAM's personality.

        Args:
            image_path: Path to the image
            detail_level: "basic", "medium", or "detailed"

        Returns:
            VisionResponse with description
        """
        detail_prompts = {
            "basic": "Briefly describe what you see in this image.",
            "medium": "Describe this image, noting the main subjects, setting, and mood.",
            "detailed": "Provide a comprehensive description including subjects, background, colors, composition, and any notable details."
        }
        prompt = detail_prompts.get(detail_level, detail_prompts["medium"])
        return self.process_image(image_path, prompt, VisionTaskType.CAPTION)

    def detect_objects(self, image_path: str, target: str = None) -> VisionResponse:
        """
        Detect objects in an image.

        Args:
            image_path: Path to the image
            target: Optional specific object to look for

        Returns:
            VisionResponse with detected objects
        """
        if target:
            prompt = f"Is there a {target} in this image? If so, describe where it is and what it looks like."
        else:
            prompt = "List and describe all the main objects and subjects you can see in this image."
        return self.process_image(image_path, prompt, VisionTaskType.DETECTION)

    def answer_about_image(self, image_path: str, question: str) -> VisionResponse:
        """
        Answer a question about an image.

        Args:
            image_path: Path to the image
            question: Question to answer about the image

        Returns:
            VisionResponse with answer
        """
        return self.process_image(image_path, question, VisionTaskType.REASONING)

    # =========================================================================
    # Phase 3.1.5: Image Context Management for Follow-up Questions
    # =========================================================================

    def _compute_image_hash(self, image_path: str) -> str:
        """Compute a hash for an image file for caching purposes."""
        try:
            with open(image_path, 'rb') as f:
                # Read first 8KB + file size for fast hashing
                header = f.read(8192)
                f.seek(0, 2)  # Seek to end
                size = f.tell()
            return hashlib.md5(header + str(size).encode()).hexdigest()[:16]
        except Exception:
            return hashlib.md5(image_path.encode()).hexdigest()[:16]

    def set_image_context(
        self,
        image_path: str,
        description: str,
        task_type: str = "caption",
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ImageContext:
        """
        Phase 3.1.5: Set the current image context for follow-up questions.

        Called after processing an image to enable follow-up questions like:
        - "What color is the car?"
        - "Can you read the text in it?"
        - "What else do you see?"

        Args:
            image_path: Path to the image file
            description: Initial description/analysis of the image
            task_type: Type of analysis performed (caption, detection, ocr, etc.)
            user_id: Who shared the image
            metadata: Additional context (objects detected, text found, etc.)

        Returns:
            The created ImageContext
        """
        self._image_context = ImageContext(
            image_path=image_path,
            image_hash=self._compute_image_hash(image_path),
            description=description,
            timestamp=datetime.now(),
            task_type=task_type,
            user_id=user_id,
            metadata=metadata or {}
        )
        print(f"[Orchestrator] Image context set: {image_path} ({task_type})")
        return self._image_context

    def get_image_context(self) -> Optional[ImageContext]:
        """
        Phase 3.1.5: Get the current image context if still valid.

        Returns:
            ImageContext if available and not expired, None otherwise
        """
        if self._image_context is None:
            return None

        # Check if context has expired
        age = (datetime.now() - self._image_context.timestamp).total_seconds()
        if age > self._image_context_timeout:
            print(f"[Orchestrator] Image context expired ({age:.0f}s old)")
            self._image_context = None
            return None

        return self._image_context

    def clear_image_context(self):
        """Phase 3.1.5: Clear the current image context."""
        if self._image_context:
            print(f"[Orchestrator] Image context cleared: {self._image_context.image_path}")
        self._image_context = None

    def has_image_context(self) -> bool:
        """Phase 3.1.5: Check if there's an active image context."""
        return self.get_image_context() is not None

    def is_image_followup(self, query: str) -> Tuple[bool, float]:
        """
        Phase 3.1.5: Detect if a query is a follow-up about the current image.

        Args:
            query: The user's query

        Returns:
            (is_followup, confidence) tuple
        """
        return detect_image_followup(query, self.has_image_context())

    def process_image_followup(self, query: str, user_id: str = "default") -> VisionResponse:
        """
        Phase 3.1.5: Process a follow-up question about the current image.

        This re-processes the image with the new question while maintaining context.

        Args:
            query: The follow-up question
            user_id: User identifier

        Returns:
            VisionResponse with the answer

        Raises:
            ValueError: If no image context is available
        """
        context = self.get_image_context()
        if not context:
            raise ValueError("No image context available for follow-up question")

        # Build an enhanced prompt that includes previous context
        enhanced_prompt = f"""Based on the image you saw earlier:
Previous analysis: {context.description[:200]}

New question: {query}

Answer the question about this image."""

        # Determine task type based on the question
        task_type = VisionTaskType.REASONING
        query_lower = query.lower()

        if any(w in query_lower for w in ["read", "text", "say", "written", "word"]):
            task_type = VisionTaskType.OCR
        elif any(w in query_lower for w in ["find", "where", "locate", "detect", "is there"]):
            task_type = VisionTaskType.DETECTION
        elif any(w in query_lower for w in ["color", "colour"]):
            # Color questions can use basic analysis
            task_type = VisionTaskType.CAPTION

        # Process the follow-up
        result = self.process_image(
            image_path=context.image_path,
            prompt=enhanced_prompt,
            task=task_type
        )

        # Update the image context with new information
        context.metadata["last_followup_query"] = query
        context.metadata["last_followup_response"] = result.response
        context.metadata["followup_count"] = context.metadata.get("followup_count", 0) + 1

        return result

    def process_with_image(
        self,
        user_input: str,
        image_path: str = None,
        user_id: str = "default"
    ) -> CognitiveResponse:
        """
        Phase 3.1.5: Process user input that may include an image or reference one.

        This is the main entry point for multi-modal conversations that handles:
        1. New images: Processes and stores context for follow-ups
        2. Follow-up questions: Uses stored image context
        3. Regular text: Falls through to normal processing

        Args:
            user_input: The user's message/question
            image_path: Optional path to a new image
            user_id: User identifier

        Returns:
            CognitiveResponse (text response) or converts VisionResponse
        """
        start_time = time.time()

        # Case 1: New image provided
        if image_path:
            # Process the image
            vision_result = self.describe_image(image_path, "medium")

            # Store context for follow-ups
            self.set_image_context(
                image_path=image_path,
                description=vision_result.response,
                task_type="caption",
                user_id=user_id,
                metadata={
                    "initial_prompt": user_input,
                    "confidence": vision_result.confidence,
                }
            )

            # If user also asked a specific question about the image
            if user_input and len(user_input.strip()) > 5:
                # Answer their question about the new image
                followup_result = self.answer_about_image(image_path, user_input)

                # Update context with both description and answer
                if self._image_context:
                    self._image_context.metadata["initial_question"] = user_input
                    self._image_context.metadata["initial_answer"] = followup_result.response

                processing_time = int((time.time() - start_time) * 1000)
                return CognitiveResponse(
                    response=followup_result.response,
                    confidence=followup_result.confidence,
                    mood="curious",
                    context_used=[f"Image: {image_path}"],
                    reasoning_steps=[{
                        "step": "image_analysis",
                        "action": "Processed new image and answered question",
                        "image_path": image_path,
                        "task": "reasoning",
                    }],
                    processing_time_ms=processing_time,
                    metadata={
                        "turn": self.turn_count,
                        "query_type": "image_with_question",
                        "image_path": image_path,
                        "model_used": followup_result.model_used,
                        "escalated": followup_result.escalated,
                    }
                )

            # Just describing the image
            processing_time = int((time.time() - start_time) * 1000)
            return CognitiveResponse(
                response=vision_result.response,
                confidence=vision_result.confidence,
                mood="curious",
                context_used=[f"Image: {image_path}"],
                reasoning_steps=[{
                    "step": "image_description",
                    "action": "Described new image",
                    "image_path": image_path,
                }],
                processing_time_ms=processing_time,
                metadata={
                    "turn": self.turn_count,
                    "query_type": "new_image",
                    "image_path": image_path,
                    "model_used": vision_result.model_used,
                    "escalated": vision_result.escalated,
                }
            )

        # Case 2: Check if this is a follow-up about a previous image
        is_followup, confidence = self.is_image_followup(user_input)
        if is_followup and confidence >= 0.7:
            try:
                vision_result = self.process_image_followup(user_input, user_id)
                processing_time = int((time.time() - start_time) * 1000)

                ctx = self.get_image_context()
                return CognitiveResponse(
                    response=vision_result.response,
                    confidence=vision_result.confidence,
                    mood="helpful",
                    context_used=[f"Image context: {ctx.image_path}" if ctx else "Previous image"],
                    reasoning_steps=[{
                        "step": "image_followup",
                        "action": "Answered follow-up question about previous image",
                        "followup_confidence": confidence,
                        "image_path": ctx.image_path if ctx else None,
                    }],
                    processing_time_ms=processing_time,
                    metadata={
                        "turn": self.turn_count,
                        "query_type": "image_followup",
                        "followup_confidence": confidence,
                        "image_context": ctx.to_dict() if ctx else None,
                        "model_used": vision_result.model_used,
                        "escalated": vision_result.escalated,
                    }
                )
            except ValueError:
                # No image context, fall through to normal processing
                pass

        # Case 3: Regular text processing
        return self.process(user_input, user_id)

    def create_goal(self, description: str,
                    priority: GoalPriority = GoalPriority.MEDIUM) -> str:
        """Create a new goal"""
        goal = self.cognitive.goal_manager.create_goal(description, priority)
        self.cognitive.goal_manager.activate_goal(goal.id)
        return goal.id

    def update_goal_progress(self, goal_id: str, progress: float):
        """Update progress on a goal"""
        self.cognitive.goal_manager.update_progress(goal_id, progress)

    def get_learning_suggestions(self, n: int = 3) -> List[str]:
        """Get suggestions for what SAM should learn"""
        return self.learning.get_learning_suggestions(n)

    def get_state(self) -> Dict[str, Any]:
        """Get complete cognitive state"""
        return {
            "session": {
                "start": self.session_start.isoformat(),
                "turns": self.turn_count,
                "duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60
            },
            "memory": self.memory.get_stats(),
            "emotional": self.emotional.get_state(),
            "goals": [g.to_dict() for g in self.cognitive.goal_manager.get_active_goals()],
            "attention": self.cognitive.attention.get_attention_state()
        }

    def run_maintenance(self) -> Dict[str, Any]:
        """Run maintenance on all systems"""
        results = {}

        # Memory maintenance
        results["memory"] = self.memory.run_maintenance()

        # Learning maintenance (consolidation)
        results["learning"] = self.learning.run_maintenance()

        return results

    def shutdown(self):
        """Gracefully shutdown all systems"""
        self.learning.stop()


# Factory function
def create_cognitive_orchestrator(
    db_path: str = "/Volumes/David External/sam_memory",
    retrieval_paths: Optional[List[str]] = None
) -> CognitiveOrchestrator:
    """
    Create a cognitive orchestrator with default settings.

    Args:
        db_path: Base path for memory databases
        retrieval_paths: Paths to databases for RAG

    Returns:
        Configured CognitiveOrchestrator
    """
    default_retrieval_paths = [
        "/Volumes/David External/dark_psych_archive/dark_psych.db",
        "/Volumes/David External/coding_training/code_training.db"
    ]

    return CognitiveOrchestrator(
        db_path=db_path,
        retrieval_db_paths=retrieval_paths or default_retrieval_paths
    )


if __name__ == "__main__":
    # Demo
    print("Initializing SAM Cognitive Orchestrator...")
    orchestrator = create_cognitive_orchestrator()

    print("\n" + "=" * 60)
    print("SAM COGNITIVE SYSTEM v1.0")
    print("=" * 60)

    # Create a goal
    goal_id = orchestrator.create_goal(
        "Help user understand cognitive architecture",
        priority=GoalPriority.HIGH
    )
    print(f"\nCreated goal: {goal_id}")

    # Process some inputs
    test_inputs = [
        "Hey SAM! How are you today?",
        "Can you explain how your memory system works?",
        "That's really interesting! Thanks for explaining.",
    ]

    for i, user_input in enumerate(test_inputs):
        print(f"\n{'=' * 40}")
        print(f"Turn {i + 1}")
        print(f"User: {user_input}")

        response = orchestrator.process(user_input)

        print(f"\nSAM ({response.mood}): {response.response}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Processing time: {response.processing_time_ms}ms")

        if response.reasoning_steps:
            print(f"Reasoning steps: {len(response.reasoning_steps)}")

    # Update goal progress
    orchestrator.update_goal_progress(goal_id, 0.7)

    # Get learning suggestions
    print("\n" + "=" * 40)
    print("Learning suggestions:")
    for suggestion in orchestrator.get_learning_suggestions():
        print(f"  - {suggestion}")

    # Get state
    print("\n" + "=" * 40)
    print("Current state:")
    state = orchestrator.get_state()
    print(json.dumps(state, indent=2, default=str))

    # Shutdown
    orchestrator.shutdown()
    print("\nShutdown complete.")
