#!/usr/bin/env python3
"""
Fact Memory System for SAM
Phase 1.3.3-1.3.8: Fact extraction, categories, persistence, and decay
Phase 2.1.8: Project-specific memory (facts per project)

Implements persistent storage for user-specific and project-specific knowledge that
SAM learns over time. Unlike episodic memory (conversation history) or semantic
memory (embeddings), facts are structured assertions about users and projects that
can be queried, decayed, reinforced, and merged.

Key Features:
- Ebbinghaus forgetting curve for natural memory decay
- Automatic decay on startup (applies decay for days since last run)
- Reinforcement when facts are accessed/used (testing effect)
- Deactivation of facts that drop below 0.1 confidence
- Spaced repetition: reinforcements increase memory stability
- Project-specific facts (Phase 2.1.8): Store facts about individual projects

Usage:
    # Via Python API:
    from fact_memory import (
        FactMemory, UserFact, FactCategory, FactSource,
        get_fact_db, get_fact_db_path, build_user_context,
        build_context_with_project
    )

    # Initialize (auto-applies decay since last run)
    db = FactMemory()

    # Initialize without auto-decay (for testing)
    db = FactMemory(auto_decay=False)

    # Save a user fact
    fact = db.save_fact(
        fact="Prefers dark mode",
        category="preferences",
        source="explicit",
        confidence=0.9,
        user_id="david"
    )

    # Save a project-specific fact (Phase 2.1.8)
    project_fact = db.save_project_fact(
        project_id="sam_brain",
        fact="Uses MLX instead of Ollama for inference",
        category="projects",
        subcategory="technology"
    )

    # Get facts for a user
    facts = db.get_facts("david", category="preferences", min_confidence=0.5)

    # Get facts for a specific project (Phase 2.1.8)
    project_facts = db.get_project_facts("sam_brain", min_confidence=0.3)

    # Extract facts from text
    extracted = db.extract_facts_from_text("I am a Python developer", "david")

    # Reinforce a fact (increases confidence)
    db.reinforce_fact(fact_id)

    # Apply decay manually
    db.apply_decay()

    # Get facts for context building (also reinforces accessed facts)
    context_facts = db.get_facts_for_context("david", min_confidence=0.5)

    # Get combined user + project facts for context (Phase 2.1.8)
    combined = db.get_facts_for_context_with_project("david", project_id="sam_brain")

    # Build context string for prompts
    context = build_user_context("david")

    # Build context with project facts included (Phase 2.1.8)
    project_context = build_context_with_project("david", project_id="sam_brain")

CLI:
    # List facts
    python fact_memory.py list [--category preferences] [--user david]

    # Add a fact
    python fact_memory.py add "fact text" --category preferences [--user david]

    # Extract facts from text
    python fact_memory.py extract "I am a software engineer"

    # Show statistics
    python fact_memory.py stats

    # Preview decay status
    python fact_memory.py decay

    # Apply decay (Ebbinghaus forgetting curve)
    python fact_memory.py decay --apply

    # Simulate N days of decay (preview)
    python fact_memory.py decay --simulate 7

    # Search facts
    python fact_memory.py search "python"

    # Build context string
    python fact_memory.py context [--user david]
"""

import json
import sqlite3
import hashlib
import time
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import argparse


# ============================================================================
# STORAGE PATHS
# ============================================================================

# External drive is primary, with fallback to local
EXTERNAL_FACTS_PATH = Path("/Volumes/David External/sam_memory/facts.db")
LOCAL_FACTS_PATH = Path.home() / ".sam" / "facts.db"


def get_fact_db_path() -> Path:
    """Get fact database path, preferring external drive."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_FACTS_PATH
    LOCAL_FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOCAL_FACTS_PATH


def is_external_drive_mounted() -> bool:
    """Check if the external drive is mounted."""
    return Path("/Volumes/David External").exists()


# ============================================================================
# ENUMS
# ============================================================================

class FactCategory(Enum):
    """Categories for user facts."""
    PREFERENCES = "preferences"       # User likes/dislikes, style choices
    BIOGRAPHICAL = "biographical"     # Personal facts about the user
    PROJECTS = "projects"             # Current and past work
    SKILLS = "skills"                 # Technical and non-technical abilities
    CORRECTIONS = "corrections"       # Things SAM got wrong that user corrected
    RELATIONSHIPS = "relationships"   # People and entities the user knows
    CONTEXT = "context"               # Situational facts that change
    SYSTEM = "system"                 # Technical preferences about SAM


class FactSource(Enum):
    """Sources of facts."""
    EXPLICIT = "explicit"             # User directly stated
    CORRECTION = "correction"         # User corrected SAM
    CONVERSATION = "conversation"     # Extracted from conversation
    INFERRED = "inferred"             # SAM inferred from context
    SYSTEM = "system"                 # System-set facts (don't decay)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Initial confidence by source
SOURCE_INITIAL_CONFIDENCE = {
    "explicit": 0.95,
    "correction": 0.90,
    "conversation": 0.60,
    "inferred": 0.40,
    "system": 1.0,
}

# Decay rates by category (per day)
CATEGORY_DECAY_RATES = {
    "preferences": 0.99,      # Very slow - preferences are stable
    "biographical": 0.995,    # Very slow - biographical facts rarely change
    "projects": 0.97,         # Moderate - projects come and go
    "skills": 0.98,           # Slow - skills build over time
    "corrections": 0.90,      # Fast - corrections should fade if not repeated
    "relationships": 0.99,    # Slow - relationships are stable
    "context": 0.85,          # Fast - context changes frequently
    "system": 1.0,            # No decay - system preferences are explicit
}

# Minimum confidence after decay (floor)
CATEGORY_DECAY_FLOORS = {
    "preferences": 0.2,
    "biographical": 0.3,
    "projects": 0.1,
    "skills": 0.15,
    "corrections": 0.05,
    "relationships": 0.2,
    "context": 0.0,
    "system": 0.9,
}

# Confidence thresholds for usage
CONFIDENCE_THRESHOLDS = {
    "certain": 0.9,       # Very confident, can state directly
    "likely": 0.7,        # Probably true, mention casually
    "possible": 0.5,      # Maybe true, ask for confirmation
    "uncertain": 0.3,     # Low confidence, don't use unless asked
    "forget": 0.1,        # Below this, mark for deletion
}

# Subcategories for organization
CATEGORY_SUBCATEGORIES = {
    "preferences": [
        "communication_style",
        "coding_style",
        "tools",
        "topics",
        "dislikes",
    ],
    "biographical": [
        "location",
        "occupation",
        "name",
        "timezone",
        "background",
        "hardware",
    ],
    "projects": [
        "active",
        "completed",
        "goals",
        "technologies",
    ],
    "skills": [
        "expert",
        "intermediate",
        "learning",
        "interested",
    ],
    "corrections": [
        "factual",
        "technical",
        "style",
        "personal",
    ],
    "relationships": [
        "family",
        "professional",
        "pets",
        "social",
    ],
    "context": [
        "current_task",
        "mood",
        "availability",
        "environment",
    ],
    "system": [
        "response_length",
        "formality",
        "emoji_use",
        "explanation_depth",
        "storage",
    ],
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class UserFact:
    """A single learned fact about a user or project.

    Implements the schema from FACT_SCHEMA.md.
    Phase 2.1.8: Added project_id for project-specific facts.
    """

    # === Identity ===
    fact_id: str                      # SHA256(user_id + fact + category)[:16]
    user_id: str                      # User identifier (default: "david")

    # === Content ===
    fact: str                         # The actual fact text
    category: str                     # Category from taxonomy

    # === Optional fields (all have defaults) ===
    project_id: Optional[str] = None  # Phase 2.1.8: Project identifier (e.g., "sam_brain")
    subcategory: Optional[str] = None # Optional refinement

    # === Confidence ===
    confidence: float = 0.5           # 0.0-1.0 current confidence
    initial_confidence: float = 0.5   # Starting confidence when first learned

    # === Source Tracking ===
    source: str = "conversation"      # conversation, explicit, inferred, correction, system
    source_message_id: Optional[str] = None   # Link to originating message
    source_context: Optional[str] = None      # Surrounding context when learned

    # === Temporal ===
    first_seen: Optional[str] = None          # When first learned
    last_reinforced: Optional[str] = None     # When last confirmed/mentioned
    last_accessed: Optional[str] = None       # When last used by SAM

    # === Reinforcement ===
    reinforcement_count: int = 1      # Times confirmed
    contradiction_count: int = 0      # Times contradicted

    # === Decay ===
    decay_rate: float = 0.98          # Per-day decay multiplier (0.0-1.0)
    decay_floor: float = 0.1          # Minimum confidence after decay

    # === Metadata ===
    metadata: Optional[str] = None    # JSON string for flexible extra context
    is_active: bool = True            # Soft delete flag
    superseded_by: Optional[str] = None  # If merged into another fact

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'UserFact':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'UserFact':
        """Create from SQLite row."""
        # Handle project_id which may not exist in older databases
        project_id = None
        try:
            project_id = row['project_id']
        except (IndexError, KeyError):
            pass

        return cls(
            fact_id=row['fact_id'],
            user_id=row['user_id'],
            fact=row['fact'],
            category=row['category'],
            project_id=project_id,
            subcategory=row['subcategory'],
            confidence=row['confidence'],
            initial_confidence=row['initial_confidence'],
            source=row['source'],
            source_message_id=row['source_message_id'],
            source_context=row['source_context'],
            first_seen=row['first_seen'],
            last_reinforced=row['last_reinforced'],
            last_accessed=row['last_accessed'],
            reinforcement_count=row['reinforcement_count'],
            contradiction_count=row['contradiction_count'],
            decay_rate=row['decay_rate'],
            decay_floor=row['decay_floor'],
            metadata=row['metadata'],
            is_active=bool(row['is_active']),
            superseded_by=row['superseded_by'],
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_fact_id(user_id: str, fact: str, category: str) -> str:
    """Generate unique fact ID."""
    content = f"{user_id}:{fact}:{category}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_history_id(fact_id: str, timestamp: float) -> str:
    """Generate unique history entry ID."""
    content = f"{fact_id}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def decay_confidence_ebbinghaus(
    initial: float,
    days_elapsed: float,
    decay_rate: float,
    reinforcement_count: int,
    floor: float = 0.1
) -> float:
    """
    Calculate decayed confidence using Ebbinghaus forgetting curve.

    The Ebbinghaus forgetting curve models memory retention as:
        R(t) = e^(-t/S)

    Where:
        R(t) = retention at time t
        t = time elapsed
        S = memory stability (increases with repetitions)

    We adapt this for fact confidence:
        C(t) = max(floor, C0 * e^(-t/S))

    Where:
        C0 = initial confidence
        S = stability = base_stability * (1 + k * ln(1 + n))
        base_stability = derived from decay_rate (higher decay_rate = higher stability)
        k = reinforcement factor (0.3)
        n = reinforcement count

    The decay_rate parameter (0.0-1.0) maps to stability:
        decay_rate 0.98 -> ~50 days half-life
        decay_rate 0.95 -> ~14 days half-life
        decay_rate 0.90 -> ~7 days half-life
        decay_rate 0.85 -> ~4 days half-life

    Args:
        initial: Initial confidence (0.0-1.0)
        days_elapsed: Days since last reinforcement
        decay_rate: Per-day retention rate (0.0-1.0), used to derive stability
        reinforcement_count: Number of times this fact has been reinforced
        floor: Minimum confidence after decay

    Returns:
        Decayed confidence value
    """
    if days_elapsed <= 0:
        return initial

    # Convert decay_rate to base stability (half-life in days)
    # decay_rate^half_life = 0.5 -> half_life = ln(0.5) / ln(decay_rate)
    if decay_rate >= 1.0:
        return initial  # No decay for system facts
    if decay_rate <= 0.0:
        return floor

    # Calculate base stability from decay_rate
    # Using: after 1 day, retention = decay_rate
    # e^(-1/S) = decay_rate -> S = -1/ln(decay_rate)
    base_stability = -1.0 / math.log(decay_rate)

    # Reinforcement increases stability (spaced repetition effect)
    # Each reinforcement adds ~20-30% to effective stability
    reinforcement_factor = 1.0 + 0.3 * math.log1p(reinforcement_count)
    effective_stability = base_stability * reinforcement_factor

    # Ebbinghaus formula: R(t) = e^(-t/S)
    retention = math.exp(-days_elapsed / effective_stability)

    # Apply to initial confidence
    decayed = initial * retention

    # Apply floor
    return max(floor, min(1.0, decayed))


def decay_confidence(
    initial: float,
    days_elapsed: float,
    decay_rate: float,
    reinforcement_count: int,
    floor: float = 0.1
) -> float:
    """
    Calculate decayed confidence using Ebbinghaus forgetting curve.

    This is an alias for decay_confidence_ebbinghaus() for backward compatibility.

    Formula: C(t) = max(floor, C0 * e^(-t/S))

    Where:
        C0 = initial confidence
        t = days elapsed since last reinforcement
        S = stability = base_stability * (1 + 0.3 * ln(1 + reinforcements))
        floor = minimum confidence

    Args:
        initial: Initial confidence (0.0-1.0)
        days_elapsed: Days since last reinforcement
        decay_rate: Per-day retention rate (0.0-1.0)
        reinforcement_count: Number of reinforcements
        floor: Minimum confidence after decay

    Returns:
        Decayed confidence value
    """
    return decay_confidence_ebbinghaus(
        initial, days_elapsed, decay_rate, reinforcement_count, floor
    )


# ============================================================================
# FACT EXTRACTION PATTERNS
# ============================================================================

class FactExtractor:
    """
    Extract facts from text using pattern matching.

    Patterns recognize:
    - "I am/I'm [something]" -> biographical
    - "I like/love/prefer [something]" -> preferences
    - "I work on/with [something]" -> projects
    - "My name is [X]" -> biographical
    - "Remember that..." -> explicit facts
    - Corrections from user
    """

    # Compiled patterns for efficiency
    PATTERNS = [
        # Identity patterns
        (
            re.compile(r"(?:my name is|i'm called|call me)\s+([a-zA-Z][a-zA-Z\s]{1,30})", re.IGNORECASE),
            "biographical",
            "name",
            lambda m: f"Name is {m.group(1).strip()}",
            0.9
        ),
        (
            re.compile(r"i(?:'m| am)\s+(?:a |an )?([a-zA-Z][a-zA-Z\s]{2,40}?)(?:\.|,|$)", re.IGNORECASE),
            "biographical",
            "occupation",
            lambda m: f"Is {m.group(1).strip()}",
            0.7
        ),

        # Location patterns
        (
            re.compile(r"i(?:'m| am) (?:in|from|based in|located in)\s+([a-zA-Z][a-zA-Z\s,]{2,50})", re.IGNORECASE),
            "biographical",
            "location",
            lambda m: f"Located in {m.group(1).strip()}",
            0.8
        ),
        (
            re.compile(r"i live in\s+([a-zA-Z][a-zA-Z\s,]{2,50})", re.IGNORECASE),
            "biographical",
            "location",
            lambda m: f"Lives in {m.group(1).strip()}",
            0.85
        ),

        # Preference patterns
        (
            re.compile(r"i (?:like|love|enjoy|prefer)\s+(.{3,60}?)(?:\.|,|$|!)", re.IGNORECASE),
            "preferences",
            "topics",
            lambda m: f"Likes {m.group(1).strip()}",
            0.7
        ),
        (
            re.compile(r"i (?:hate|dislike|don't like|can't stand)\s+(.{3,60}?)(?:\.|,|$|!)", re.IGNORECASE),
            "preferences",
            "dislikes",
            lambda m: f"Dislikes {m.group(1).strip()}",
            0.75
        ),
        (
            re.compile(r"i prefer\s+(.{3,40}?)\s+(?:over|to|instead of)\s+(.{3,40}?)(?:\.|,|$)", re.IGNORECASE),
            "preferences",
            "tools",
            lambda m: f"Prefers {m.group(1).strip()} over {m.group(2).strip()}",
            0.8
        ),

        # Project patterns
        (
            re.compile(r"i(?:'m| am) (?:working on|building|developing|creating)\s+(.{3,80}?)(?:\.|,|$)", re.IGNORECASE),
            "projects",
            "active",
            lambda m: f"Working on {m.group(1).strip()}",
            0.75
        ),
        (
            re.compile(r"i work (?:on|with)\s+(.{3,60}?)(?:\.|,|$)", re.IGNORECASE),
            "projects",
            "active",
            lambda m: f"Works with {m.group(1).strip()}",
            0.7
        ),

        # Skill patterns
        (
            re.compile(r"i(?:'m| am) (?:good at|skilled in|experienced with|expert in)\s+(.{3,60}?)(?:\.|,|$)", re.IGNORECASE),
            "skills",
            "expert",
            lambda m: f"Expert in {m.group(1).strip()}",
            0.7
        ),
        (
            re.compile(r"i(?:'m| am) (?:learning|studying|trying to learn)\s+(.{3,60}?)(?:\.|,|$)", re.IGNORECASE),
            "skills",
            "learning",
            lambda m: f"Learning {m.group(1).strip()}",
            0.7
        ),
        (
            re.compile(r"i (?:know|use|code in|program in)\s+([a-zA-Z][a-zA-Z\s#+]{2,30}?)(?:\.|,|$| for)", re.IGNORECASE),
            "skills",
            "intermediate",
            lambda m: f"Uses {m.group(1).strip()}",
            0.6
        ),

        # Relationship patterns
        (
            re.compile(r"my (?:wife|husband|partner|spouse)(?:'s name is| is called| is)\s+([a-zA-Z][a-zA-Z\s]{1,30})", re.IGNORECASE),
            "relationships",
            "family",
            lambda m: f"Partner is {m.group(1).strip()}",
            0.85
        ),
        (
            re.compile(r"i have (?:a )?([0-9]+)?\s*(?:cat|dog|pet)s?\s*(?:named|called)?\s*([a-zA-Z][a-zA-Z\s,&]{0,40})?", re.IGNORECASE),
            "relationships",
            "pets",
            lambda m: f"Has pet(s) {m.group(2).strip() if m.group(2) else ''}".strip(),
            0.8
        ),

        # System preference patterns
        (
            re.compile(r"(?:keep|make) (?:your |the )?(?:response|answer)s?\s+(?:short|concise|brief)", re.IGNORECASE),
            "system",
            "response_length",
            lambda m: "Prefers concise responses",
            0.9
        ),
        (
            re.compile(r"(?:don't|do not) use emojis?", re.IGNORECASE),
            "system",
            "emoji_use",
            lambda m: "Does not want emojis in responses",
            0.9
        ),

        # Explicit remember command (highest priority)
        (
            re.compile(r"remember (?:that |this:? )?(.{5,200})", re.IGNORECASE),
            None,  # Category determined from content
            None,
            lambda m: m.group(1).strip(),
            0.95  # High confidence for explicit remembers
        ),
    ]

    @classmethod
    def extract(cls, text: str, user_id: str = "david") -> List[UserFact]:
        """
        Extract facts from text using pattern matching.

        Args:
            text: The text to extract facts from
            user_id: User identifier

        Returns:
            List of extracted UserFact objects
        """
        facts = []
        now = datetime.now().isoformat()

        for pattern, category, subcategory, formatter, confidence in cls.PATTERNS:
            matches = pattern.finditer(text)
            for match in matches:
                fact_text = formatter(match)

                # Skip very short facts
                if len(fact_text) < 5:
                    continue

                # For explicit "remember" commands, try to infer category
                inferred_category = category
                inferred_subcategory = subcategory
                if category is None:
                    inferred_category = cls._infer_category(fact_text)
                    inferred_subcategory = None

                # Get category-specific decay settings
                decay_rate = CATEGORY_DECAY_RATES.get(inferred_category, 0.98)
                decay_floor = CATEGORY_DECAY_FLOORS.get(inferred_category, 0.1)

                fact = UserFact(
                    fact_id=generate_fact_id(user_id, fact_text, inferred_category),
                    user_id=user_id,
                    fact=fact_text,
                    category=inferred_category,
                    subcategory=inferred_subcategory,
                    confidence=confidence,
                    initial_confidence=confidence,
                    source="conversation",
                    source_context=text[:200] if len(text) > 200 else text,
                    first_seen=now,
                    last_reinforced=now,
                    last_accessed=now,
                    reinforcement_count=1,
                    contradiction_count=0,
                    decay_rate=decay_rate,
                    decay_floor=decay_floor,
                    is_active=True,
                )
                facts.append(fact)

        return facts

    @classmethod
    def _infer_category(cls, fact_text: str) -> str:
        """Infer category from fact text content."""
        text_lower = fact_text.lower()

        # Check for category keywords
        if any(kw in text_lower for kw in ['prefer', 'like', 'hate', 'dislike', 'want']):
            return "preferences"
        if any(kw in text_lower for kw in ['project', 'building', 'working on', 'developing']):
            return "projects"
        if any(kw in text_lower for kw in ['know', 'expert', 'skill', 'learn', 'code', 'program']):
            return "skills"
        if any(kw in text_lower for kw in ['live', 'from', 'name', 'age', 'job', 'work as']):
            return "biographical"
        if any(kw in text_lower for kw in ['wife', 'husband', 'partner', 'friend', 'colleague']):
            return "relationships"
        if any(kw in text_lower for kw in ['response', 'answer', 'emoji', 'format']):
            return "system"

        # Default to biographical for explicit remembers
        return "biographical"


# ============================================================================
# SQLITE SCHEMA
# ============================================================================

FACTS_SCHEMA = """
-- Main facts table
CREATE TABLE IF NOT EXISTS user_facts (
    -- Identity
    fact_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'david',
    project_id TEXT,  -- Phase 2.1.8: Optional project identifier for project-specific facts

    -- Content
    fact TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,

    -- Confidence
    confidence REAL NOT NULL DEFAULT 0.5,
    initial_confidence REAL NOT NULL DEFAULT 0.5,

    -- Source
    source TEXT NOT NULL DEFAULT 'conversation',
    source_message_id TEXT,
    source_context TEXT,

    -- Temporal
    first_seen TEXT NOT NULL,
    last_reinforced TEXT NOT NULL,
    last_accessed TEXT NOT NULL,

    -- Reinforcement
    reinforcement_count INTEGER NOT NULL DEFAULT 1,
    contradiction_count INTEGER NOT NULL DEFAULT 0,

    -- Decay
    decay_rate REAL NOT NULL DEFAULT 0.98,
    decay_floor REAL NOT NULL DEFAULT 0.1,

    -- Metadata
    metadata TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT,

    -- Constraints
    FOREIGN KEY (superseded_by) REFERENCES user_facts(fact_id),
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (decay_rate >= 0.0 AND decay_rate <= 1.0),
    CHECK (source IN ('conversation', 'explicit', 'inferred', 'correction', 'system'))
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_facts_user_id ON user_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_facts_category ON user_facts(category);
CREATE INDEX IF NOT EXISTS idx_facts_user_category ON user_facts(user_id, category);
CREATE INDEX IF NOT EXISTS idx_facts_confidence ON user_facts(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_facts_last_reinforced ON user_facts(last_reinforced DESC);
CREATE INDEX IF NOT EXISTS idx_facts_active ON user_facts(is_active);
CREATE INDEX IF NOT EXISTS idx_facts_project_id ON user_facts(project_id);
CREATE INDEX IF NOT EXISTS idx_facts_user_project ON user_facts(user_id, project_id);

-- Fact history table (for auditing)
CREATE TABLE IF NOT EXISTS fact_history (
    history_id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_confidence REAL,
    new_confidence REAL,
    change_reason TEXT,
    timestamp TEXT NOT NULL,

    FOREIGN KEY (fact_id) REFERENCES user_facts(fact_id)
);

CREATE INDEX IF NOT EXISTS idx_history_fact ON fact_history(fact_id);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON fact_history(timestamp DESC);

-- Metadata table for system state (e.g., last decay run)
CREATE TABLE IF NOT EXISTS fact_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


# ============================================================================
# FACT MEMORY DATABASE
# ============================================================================

class FactMemory:
    """SQLite database for fact storage.

    Primary storage on external drive: /Volumes/David External/sam_memory/facts.db
    Falls back to local ~/.sam/facts.db if external drive not mounted.

    Implements the schema from FACT_SCHEMA.md.
    """

    def __init__(self, db_path: Optional[Path] = None, auto_decay: bool = True):
        """Initialize the fact database.

        Args:
            db_path: Optional explicit path. If None, uses external drive if mounted,
                    otherwise falls back to local path.
            auto_decay: If True, automatically apply decay for days since last run
                       on initialization. Set to False for testing or batch operations.
        """
        if db_path is None:
            self.db_path = get_fact_db_path()
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Apply automatic decay on startup
        if auto_decay:
            self._apply_startup_decay()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)

        # Phase 2.1.8: Migrate existing databases to add project_id column FIRST
        # This must happen before FACTS_SCHEMA runs because schema has indexes on project_id
        self._migrate_add_project_id(conn)

        # Now run full schema (creates tables if not exist, adds indexes)
        conn.executescript(FACTS_SCHEMA)
        conn.commit()
        conn.close()

    def _migrate_add_project_id(self, conn: sqlite3.Connection):
        """Add project_id column to existing databases if missing."""
        cur = conn.cursor()

        # Check if user_facts table exists at all
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_facts'")
        if not cur.fetchone():
            # Table doesn't exist yet, schema will create it with project_id
            return

        # Check if project_id column exists
        cur.execute("PRAGMA table_info(user_facts)")
        columns = [row[1] for row in cur.fetchall()]

        if 'project_id' not in columns:
            try:
                cur.execute("ALTER TABLE user_facts ADD COLUMN project_id TEXT")
                conn.commit()
                print("[FactMemory] Migrated: Added project_id column")
            except sqlite3.OperationalError:
                # Column already exists or other error
                pass

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # METADATA / STATE TRACKING
    # ========================================================================

    def _get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value by key."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM fact_metadata WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row['value'] if row else None

    def _set_metadata(self, key: str, value: str):
        """Set a metadata value."""
        conn = self._get_connection()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("""
            INSERT OR REPLACE INTO fact_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))
        conn.commit()
        conn.close()

    def _apply_startup_decay(self):
        """
        Apply decay automatically on startup based on days since last run.

        Uses Ebbinghaus forgetting curve to decay all active facts based on
        the time elapsed since the last decay operation.

        This ensures facts naturally fade if SAM hasn't been used for a while,
        simulating the natural forgetting process.
        """
        now = datetime.now()

        # Get last decay timestamp
        last_decay_str = self._get_metadata("last_decay_run")

        if last_decay_str:
            try:
                last_decay = datetime.fromisoformat(last_decay_str)
                days_since_decay = (now - last_decay).total_seconds() / 86400.0

                # Only apply decay if at least 1 day has passed
                if days_since_decay >= 1.0:
                    stats = self._apply_decay_for_elapsed_days(days_since_decay)
                    # Update last decay timestamp
                    self._set_metadata("last_decay_run", now.isoformat())

                    # Log if significant changes occurred
                    if stats['updated'] > 0 or stats['deactivated'] > 0:
                        print(f"[FactMemory] Startup decay applied ({days_since_decay:.1f} days): "
                              f"{stats['updated']} updated, {stats['deactivated']} deactivated")
            except ValueError:
                # Invalid timestamp, reset it
                self._set_metadata("last_decay_run", now.isoformat())
        else:
            # First run, set the timestamp
            self._set_metadata("last_decay_run", now.isoformat())

    def _apply_decay_for_elapsed_days(self, days_elapsed: float) -> Dict[str, int]:
        """
        Apply decay for a specific number of elapsed days.

        This is used by startup decay to catch up on missed decay periods.

        Args:
            days_elapsed: Number of days to simulate decay for

        Returns:
            Statistics about the decay operation
        """
        conn = self._get_connection()
        cur = conn.cursor()

        stats = {
            "updated": 0,
            "deactivated": 0,
        }

        # Get all active facts
        cur.execute("SELECT * FROM user_facts WHERE is_active = 1")
        rows = cur.fetchall()

        for row in rows:
            fact = UserFact.from_row(row)

            # Skip system facts (no decay)
            if fact.source == "system":
                continue

            # Calculate new decayed confidence using Ebbinghaus curve
            new_confidence = decay_confidence_ebbinghaus(
                fact.confidence,
                days_elapsed,
                fact.decay_rate,
                fact.reinforcement_count,
                fact.decay_floor
            )

            if abs(new_confidence - fact.confidence) > 0.001:  # Only update if changed significantly
                # Update confidence
                cur.execute("""
                    UPDATE user_facts SET confidence = ?
                    WHERE fact_id = ?
                """, (new_confidence, fact.fact_id))
                stats["updated"] += 1

                # Deactivate if below threshold (0.1)
                if new_confidence < CONFIDENCE_THRESHOLDS["forget"]:
                    cur.execute("""
                        UPDATE user_facts SET is_active = 0
                        WHERE fact_id = ?
                    """, (fact.fact_id,))
                    self._log_history(
                        cur, fact.fact_id, "deactivated",
                        fact.confidence, new_confidence,
                        f"startup_decay_{days_elapsed:.1f}_days"
                    )
                    stats["deactivated"] += 1
                else:
                    # Log the decay
                    self._log_history(
                        cur, fact.fact_id, "decayed",
                        fact.confidence, new_confidence,
                        f"startup_decay_{days_elapsed:.1f}_days"
                    )

        conn.commit()
        conn.close()

        return stats

    # ========================================================================
    # SAVE / CREATE
    # ========================================================================

    def save_fact(
        self,
        fact: str,
        category: str,
        source: str = "conversation",
        confidence: Optional[float] = None,
        user_id: str = "david",
        project_id: Optional[str] = None,
        subcategory: Optional[str] = None,
        source_message_id: Optional[str] = None,
        source_context: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> UserFact:
        """
        Save a fact to the database.

        If a similar fact already exists (same user, category, and text), it will
        be reinforced instead of creating a duplicate.

        Args:
            fact: The fact text
            category: Category from FactCategory enum
            source: Source from FactSource enum
            confidence: Override confidence (default uses source-based confidence)
            user_id: User identifier
            project_id: Optional project identifier for project-specific facts
            subcategory: Optional subcategory
            source_message_id: ID of the message that produced this fact
            source_context: Context around the fact
            metadata: Additional metadata

        Returns:
            The created or reinforced UserFact
        """
        now = datetime.now().isoformat()

        # Set confidence based on source if not provided
        if confidence is None:
            confidence = SOURCE_INITIAL_CONFIDENCE.get(source, 0.6)

        # Get category-specific decay settings
        decay_rate = CATEGORY_DECAY_RATES.get(category, 0.98)
        decay_floor = CATEGORY_DECAY_FLOORS.get(category, 0.1)

        # Generate fact ID
        fact_id = generate_fact_id(user_id, fact, category)

        # Check if fact already exists
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM user_facts WHERE fact_id = ?",
            (fact_id,)
        )
        existing = cur.fetchone()

        if existing:
            # Reinforce existing fact
            conn.close()
            return self.reinforce_fact(fact_id, source_message_id)

        # Create new fact
        user_fact = UserFact(
            fact_id=fact_id,
            user_id=user_id,
            project_id=project_id,
            fact=fact,
            category=category,
            subcategory=subcategory,
            confidence=confidence,
            initial_confidence=confidence,
            source=source,
            source_message_id=source_message_id,
            source_context=source_context,
            first_seen=now,
            last_reinforced=now,
            last_accessed=now,
            reinforcement_count=1,
            contradiction_count=0,
            decay_rate=decay_rate,
            decay_floor=decay_floor,
            metadata=json.dumps(metadata) if metadata else None,
            is_active=True,
            superseded_by=None,
        )

        # Insert into database
        cur.execute("""
            INSERT INTO user_facts (
                fact_id, user_id, project_id, fact, category, subcategory,
                confidence, initial_confidence, source, source_message_id, source_context,
                first_seen, last_reinforced, last_accessed,
                reinforcement_count, contradiction_count,
                decay_rate, decay_floor, metadata, is_active, superseded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_fact.fact_id, user_fact.user_id, user_fact.project_id, user_fact.fact,
            user_fact.category, user_fact.subcategory,
            user_fact.confidence, user_fact.initial_confidence,
            user_fact.source, user_fact.source_message_id, user_fact.source_context,
            user_fact.first_seen, user_fact.last_reinforced, user_fact.last_accessed,
            user_fact.reinforcement_count, user_fact.contradiction_count,
            user_fact.decay_rate, user_fact.decay_floor,
            user_fact.metadata, int(user_fact.is_active), user_fact.superseded_by
        ))

        # Log history
        self._log_history(cur, fact_id, "created", None, confidence, f"Source: {source}")

        conn.commit()
        conn.close()

        return user_fact

    def save_facts(self, facts: List[UserFact]) -> List[UserFact]:
        """Save multiple facts at once."""
        saved = []
        for fact in facts:
            saved_fact = self.save_fact(
                fact=fact.fact,
                category=fact.category,
                source=fact.source,
                confidence=fact.confidence,
                user_id=fact.user_id,
                project_id=fact.project_id,
                subcategory=fact.subcategory,
                source_message_id=fact.source_message_id,
                source_context=fact.source_context,
                metadata=json.loads(fact.metadata) if fact.metadata else None,
            )
            saved.append(saved_fact)
        return saved

    # ========================================================================
    # GET / QUERY
    # ========================================================================

    def get_fact(self, fact_id: str) -> Optional[UserFact]:
        """Get a fact by ID."""
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM user_facts WHERE fact_id = ?", (fact_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            return UserFact.from_row(row)
        return None

    def get_facts(
        self,
        user_id: str = "david",
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[UserFact]:
        """
        Get facts for a user, optionally filtered.

        Args:
            user_id: User identifier
            category: Optional category filter
            min_confidence: Minimum confidence threshold
            limit: Maximum number of facts to return
            include_inactive: Include soft-deleted facts

        Returns:
            List of UserFact objects
        """
        conn = self._get_connection()
        cur = conn.cursor()

        query = """
            SELECT * FROM user_facts
            WHERE user_id = ? AND confidence >= ?
        """
        params: List[Any] = [user_id, min_confidence]

        if not include_inactive:
            query += " AND is_active = 1"

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [UserFact.from_row(row) for row in rows]

    def get_facts_for_context(
        self,
        user_id: str = "david",
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[UserFact]:
        """
        Get facts suitable for context injection into prompts.

        Prioritizes corrections and system preferences, then by confidence.

        Args:
            user_id: User identifier
            min_confidence: Minimum confidence threshold
            limit: Maximum number of facts

        Returns:
            List of UserFact objects
        """
        conn = self._get_connection()
        cur = conn.cursor()

        query = """
            SELECT * FROM user_facts
            WHERE user_id = ?
              AND is_active = 1
              AND confidence >= ?
              AND category != 'context'
            ORDER BY
              CASE category
                WHEN 'corrections' THEN 1
                WHEN 'system' THEN 2
                WHEN 'preferences' THEN 3
                ELSE 4
              END,
              confidence DESC
            LIMIT ?
        """

        cur.execute(query, [user_id, min_confidence, limit])
        rows = cur.fetchall()
        conn.close()

        # Update last_accessed for retrieved facts
        fact_ids = [row['fact_id'] for row in rows]
        if fact_ids:
            self._update_accessed(fact_ids)

        return [UserFact.from_row(row) for row in rows]

    def search_facts(
        self,
        query: str,
        user_id: str = "david",
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> List[UserFact]:
        """
        Search facts by text content using keyword matching.

        Args:
            query: Search query
            user_id: User identifier
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching UserFact objects
        """
        conn = self._get_connection()
        cur = conn.cursor()

        # Simple keyword search
        search_pattern = f"%{query}%"

        cur.execute("""
            SELECT * FROM user_facts
            WHERE user_id = ? AND is_active = 1 AND confidence >= ?
              AND fact LIKE ?
            ORDER BY confidence DESC
            LIMIT ?
        """, [user_id, min_confidence, search_pattern, limit])

        rows = cur.fetchall()
        conn.close()

        return [UserFact.from_row(row) for row in rows]

    # ========================================================================
    # PROJECT-SPECIFIC MEMORY (Phase 2.1.8)
    # ========================================================================

    def save_project_fact(
        self,
        project_id: str,
        fact: str,
        category: str = "projects",
        source: str = "conversation",
        confidence: Optional[float] = None,
        user_id: str = "david",
        subcategory: Optional[str] = None,
        source_context: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> UserFact:
        """
        Save a project-specific fact.

        Project facts are things like:
        - "This project uses SQLite for storage"
        - "The main entry point is sam_api.py"
        - "We decided to use MLX instead of Ollama"

        Args:
            project_id: Project identifier (e.g., "sam_brain", "character_pipeline")
            fact: The fact text
            category: Category (defaults to "projects")
            source: Source from FactSource enum
            confidence: Override confidence (default uses source-based confidence)
            user_id: User identifier
            subcategory: Optional subcategory (e.g., "architecture", "decision", "technology")
            source_context: Context around the fact
            metadata: Additional metadata

        Returns:
            The created or reinforced UserFact
        """
        return self.save_fact(
            fact=fact,
            category=category,
            source=source,
            confidence=confidence,
            user_id=user_id,
            project_id=project_id,
            subcategory=subcategory,
            source_context=source_context,
            metadata=metadata,
        )

    def get_project_facts(
        self,
        project_id: str,
        min_confidence: float = 0.3,
        category: Optional[str] = None,
        limit: int = 50,
        include_inactive: bool = False,
    ) -> List[UserFact]:
        """
        Get all facts for a specific project.

        Args:
            project_id: Project identifier
            min_confidence: Minimum confidence threshold
            category: Optional category filter
            limit: Maximum number of facts
            include_inactive: Include soft-deleted facts

        Returns:
            List of UserFact objects for the project
        """
        conn = self._get_connection()
        cur = conn.cursor()

        query = """
            SELECT * FROM user_facts
            WHERE project_id = ? AND confidence >= ?
        """
        params: List[Any] = [project_id, min_confidence]

        if not include_inactive:
            query += " AND is_active = 1"

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [UserFact.from_row(row) for row in rows]

    def get_facts_for_context_with_project(
        self,
        user_id: str = "david",
        project_id: Optional[str] = None,
        min_confidence: float = 0.5,
        user_limit: int = 10,
        project_limit: int = 10,
    ) -> List[UserFact]:
        """
        Get facts for context injection, combining user facts and project facts.

        When in a specific project, this returns both:
        1. User-level facts (preferences, corrections, etc.)
        2. Project-specific facts (architecture decisions, technologies, etc.)

        Project facts are prioritized when project_id is provided.

        Args:
            user_id: User identifier
            project_id: Optional project identifier
            min_confidence: Minimum confidence threshold
            user_limit: Maximum user facts
            project_limit: Maximum project facts

        Returns:
            List of UserFact objects (user facts + project facts)
        """
        all_facts = []

        # Get user-level facts (no project_id)
        conn = self._get_connection()
        cur = conn.cursor()

        user_query = """
            SELECT * FROM user_facts
            WHERE user_id = ?
              AND is_active = 1
              AND confidence >= ?
              AND category != 'context'
              AND project_id IS NULL
            ORDER BY
              CASE category
                WHEN 'corrections' THEN 1
                WHEN 'system' THEN 2
                WHEN 'preferences' THEN 3
                ELSE 4
              END,
              confidence DESC
            LIMIT ?
        """

        cur.execute(user_query, [user_id, min_confidence, user_limit])
        user_rows = cur.fetchall()
        all_facts.extend([UserFact.from_row(row) for row in user_rows])

        # Get project-specific facts if project_id provided
        if project_id:
            project_query = """
                SELECT * FROM user_facts
                WHERE project_id = ?
                  AND is_active = 1
                  AND confidence >= ?
                ORDER BY
                  CASE category
                    WHEN 'corrections' THEN 1
                    WHEN 'system' THEN 2
                    WHEN 'projects' THEN 3
                    ELSE 4
                  END,
                  confidence DESC
                LIMIT ?
            """

            cur.execute(project_query, [project_id, min_confidence, project_limit])
            project_rows = cur.fetchall()
            all_facts.extend([UserFact.from_row(row) for row in project_rows])

        conn.close()

        # Update last_accessed for all retrieved facts
        fact_ids = [f.fact_id for f in all_facts]
        if fact_ids:
            self._update_accessed(fact_ids)

        return all_facts

    # ========================================================================
    # EXTRACTION
    # ========================================================================

    def extract_facts_from_text(
        self,
        text: str,
        user_id: str = "david",
        save: bool = True,
    ) -> List[UserFact]:
        """
        Extract facts from text and optionally save them.

        Args:
            text: Text to extract facts from
            user_id: User identifier
            save: Whether to save extracted facts

        Returns:
            List of extracted UserFact objects
        """
        facts = FactExtractor.extract(text, user_id)

        if save and facts:
            facts = self.save_facts(facts)

        return facts

    # ========================================================================
    # REINFORCE / CONTRADICT
    # ========================================================================

    def reinforce_fact(
        self,
        fact_id: str,
        source_message_id: Optional[str] = None,
    ) -> Optional[UserFact]:
        """
        Reinforce an existing fact (increases confidence).

        Args:
            fact_id: The fact to reinforce
            source_message_id: Optional message ID that caused reinforcement

        Returns:
            The updated UserFact or None if not found
        """
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM user_facts WHERE fact_id = ?", (fact_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return None

        fact = UserFact.from_row(row)
        now = datetime.now().isoformat()

        # Calculate new confidence with diminishing returns
        old_confidence = fact.confidence
        boost = 0.05 / math.log1p(fact.reinforcement_count + 1)
        new_confidence = min(1.0, old_confidence + boost)

        # Update fact
        cur.execute("""
            UPDATE user_facts SET
                confidence = ?,
                reinforcement_count = reinforcement_count + 1,
                last_reinforced = ?,
                last_accessed = ?
            WHERE fact_id = ?
        """, (new_confidence, now, now, fact_id))

        # Log history
        self._log_history(
            cur, fact_id, "reinforced",
            old_confidence, new_confidence,
            f"message_id: {source_message_id}" if source_message_id else None
        )

        conn.commit()
        conn.close()

        # Return updated fact
        return self.get_fact(fact_id)

    def contradict_fact(
        self,
        fact_id: str,
        reason: Optional[str] = None,
    ) -> Optional[UserFact]:
        """
        Record a contradiction to a fact (decreases confidence).

        Args:
            fact_id: The fact that was contradicted
            reason: Optional explanation of the contradiction

        Returns:
            The updated UserFact or None if not found
        """
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM user_facts WHERE fact_id = ?", (fact_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return None

        fact = UserFact.from_row(row)
        now = datetime.now().isoformat()

        # Reduce confidence
        old_confidence = fact.confidence
        new_confidence = old_confidence * 0.8  # 20% reduction

        # Update fact
        cur.execute("""
            UPDATE user_facts SET
                confidence = ?,
                contradiction_count = contradiction_count + 1,
                last_accessed = ?
            WHERE fact_id = ?
        """, (new_confidence, now, fact_id))

        # Log history
        self._log_history(
            cur, fact_id, "contradicted",
            old_confidence, new_confidence,
            reason
        )

        conn.commit()
        conn.close()

        return self.get_fact(fact_id)

    # ========================================================================
    # DECAY
    # ========================================================================

    def apply_decay(self, days_threshold: int = 30) -> Dict[str, int]:
        """
        Apply decay to all facts and prune very old inactive facts.

        Should be run periodically (daily or on session start).

        Args:
            days_threshold: Days before inactive facts are permanently deleted

        Returns:
            Statistics about the decay operation
        """
        conn = self._get_connection()
        cur = conn.cursor()

        stats = {
            "updated": 0,
            "deactivated": 0,
            "purged": 0,
        }

        now = datetime.now()

        # Get all active facts
        cur.execute("SELECT * FROM user_facts WHERE is_active = 1")
        rows = cur.fetchall()

        for row in rows:
            fact = UserFact.from_row(row)

            # Skip system facts (no decay)
            if fact.source == "system":
                continue

            # Calculate days since last reinforcement
            try:
                last_reinforced = datetime.fromisoformat(fact.last_reinforced)
                days_elapsed = (now - last_reinforced).days
            except (ValueError, TypeError):
                days_elapsed = 0

            if days_elapsed <= 0:
                continue

            # Calculate new decayed confidence
            new_confidence = decay_confidence(
                fact.confidence,
                days_elapsed,
                fact.decay_rate,
                fact.reinforcement_count,
                fact.decay_floor
            )

            if new_confidence != fact.confidence:
                # Update confidence
                cur.execute("""
                    UPDATE user_facts SET confidence = ?
                    WHERE fact_id = ?
                """, (new_confidence, fact.fact_id))
                stats["updated"] += 1

                # Deactivate if below threshold
                if new_confidence < CONFIDENCE_THRESHOLDS["forget"]:
                    cur.execute("""
                        UPDATE user_facts SET is_active = 0
                        WHERE fact_id = ?
                    """, (fact.fact_id,))
                    self._log_history(
                        cur, fact.fact_id, "deactivated",
                        fact.confidence, new_confidence,
                        "decay_below_threshold"
                    )
                    stats["deactivated"] += 1

        # Purge very old inactive facts
        cutoff = (now - timedelta(days=days_threshold)).isoformat()
        cur.execute("""
            DELETE FROM user_facts
            WHERE is_active = 0 AND last_accessed < ?
        """, (cutoff,))
        stats["purged"] = cur.rowcount

        conn.commit()
        conn.close()

        return stats

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive fact statistics."""
        conn = self._get_connection()
        cur = conn.cursor()

        stats: Dict[str, Any] = {}

        # Total facts
        cur.execute("SELECT COUNT(*) FROM user_facts")
        stats["total_facts"] = cur.fetchone()[0]

        # Active facts
        cur.execute("SELECT COUNT(*) FROM user_facts WHERE is_active = 1")
        stats["active_facts"] = cur.fetchone()[0]

        # By category
        cur.execute("""
            SELECT category, COUNT(*) FROM user_facts
            WHERE is_active = 1
            GROUP BY category
        """)
        stats["by_category"] = dict(cur.fetchall())

        # By source
        cur.execute("""
            SELECT source, COUNT(*) FROM user_facts
            WHERE is_active = 1
            GROUP BY source
        """)
        stats["by_source"] = dict(cur.fetchall())

        # Confidence distribution
        cur.execute("SELECT AVG(confidence) FROM user_facts WHERE is_active = 1")
        avg_conf = cur.fetchone()[0]
        stats["avg_confidence"] = round(avg_conf, 3) if avg_conf else 0.0

        cur.execute("SELECT COUNT(*) FROM user_facts WHERE is_active = 1 AND confidence >= 0.9")
        stats["high_confidence_count"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_facts WHERE is_active = 1 AND confidence < 0.3")
        stats["low_confidence_count"] = cur.fetchone()[0]

        # By user
        cur.execute("""
            SELECT user_id, COUNT(*) FROM user_facts
            WHERE is_active = 1
            GROUP BY user_id
        """)
        stats["by_user"] = dict(cur.fetchall())

        # Storage info
        stats["storage"] = {
            "location": str(self.db_path),
            "using_external_drive": is_external_drive_mounted()
        }

        conn.close()
        return stats

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _log_history(
        self,
        cur: sqlite3.Cursor,
        fact_id: str,
        change_type: str,
        old_confidence: Optional[float],
        new_confidence: Optional[float],
        reason: Optional[str] = None,
    ):
        """Log a change to fact history."""
        history_id = generate_history_id(fact_id, time.time())
        cur.execute("""
            INSERT INTO fact_history (
                history_id, fact_id, change_type,
                old_confidence, new_confidence, change_reason, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id, fact_id, change_type,
            old_confidence, new_confidence, reason,
            datetime.now().isoformat()
        ))

    def _update_accessed(self, fact_ids: List[str], reinforce: bool = True):
        """
        Update last_accessed for a list of facts and optionally reinforce them.

        When facts are accessed/used by SAM, they receive a small confidence boost
        to simulate the "testing effect" in memory research - recalling information
        strengthens the memory.

        Args:
            fact_ids: List of fact IDs that were accessed
            reinforce: If True, also apply a small reinforcement boost (default True)
        """
        if not fact_ids:
            return

        conn = self._get_connection()
        cur = conn.cursor()

        now = datetime.now().isoformat()

        for fact_id in fact_ids:
            # Get current fact state
            cur.execute("SELECT * FROM user_facts WHERE fact_id = ?", (fact_id,))
            row = cur.fetchone()
            if not row:
                continue

            fact = UserFact.from_row(row)

            # Update last_accessed
            updates = ["last_accessed = ?"]
            params = [now]

            # Apply small reinforcement boost when accessed (testing effect)
            # This is smaller than explicit reinforcement - just 1-2% boost
            if reinforce and fact.source != "system":
                old_confidence = fact.confidence
                # Small boost with diminishing returns based on access frequency
                boost = 0.02 / math.log1p(fact.reinforcement_count + 1)
                new_confidence = min(1.0, old_confidence + boost)

                if new_confidence > old_confidence:
                    updates.append("confidence = ?")
                    params.append(new_confidence)

                    # Also update last_reinforced since this counts as weak reinforcement
                    updates.append("last_reinforced = ?")
                    params.append(now)

            params.append(fact_id)

            cur.execute(f"""
                UPDATE user_facts SET {', '.join(updates)}
                WHERE fact_id = ?
            """, params)

        conn.commit()
        conn.close()

    def deactivate_fact(self, fact_id: str, reason: Optional[str] = None) -> bool:
        """Soft-delete a fact."""
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT confidence FROM user_facts WHERE fact_id = ?", (fact_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return False

        cur.execute("""
            UPDATE user_facts SET is_active = 0
            WHERE fact_id = ?
        """, (fact_id,))

        self._log_history(cur, fact_id, "deactivated", row[0], 0.0, reason)

        conn.commit()
        conn.close()
        return True

    def reactivate_fact(self, fact_id: str) -> bool:
        """Reactivate a soft-deleted fact."""
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE user_facts SET is_active = 1
            WHERE fact_id = ?
        """, (fact_id,))

        success = cur.rowcount > 0
        if success:
            cur.execute("SELECT confidence FROM user_facts WHERE fact_id = ?", (fact_id,))
            row = cur.fetchone()
            self._log_history(cur, fact_id, "reactivated", 0.0, row[0] if row else 0.5, None)

        conn.commit()
        conn.close()
        return success


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_fact_db_instance: Optional[FactMemory] = None


def get_fact_db() -> FactMemory:
    """Get singleton instance of FactMemory."""
    global _fact_db_instance
    if _fact_db_instance is None:
        _fact_db_instance = FactMemory()
    return _fact_db_instance


# ============================================================================
# CONTEXT BUILDER
# ============================================================================

def build_user_context(
    user_id: str = "david",
    min_confidence: float = 0.5,
    max_tokens: int = 200
) -> str:
    """
    Build context string from user facts for prompt injection.

    Phase 1.3.7: Enhanced with explicit priority ordering and token budget.

    Priority Order (highest to lowest):
    1. corrections - Things SAM got wrong, MUST not repeat
    2. system - User's technical preferences about SAM
    3. preferences - Likes/dislikes/style choices
    4. biographical - Personal facts about the user

    Args:
        user_id: User identifier
        min_confidence: Minimum confidence threshold
        max_tokens: Maximum approximate tokens (~4 chars per token)

    Returns:
        Context string suitable for including in prompts
    """
    db = get_fact_db()
    facts = db.get_facts_for_context(user_id, min_confidence, limit=15)

    if not facts:
        return ""

    # Group by category
    by_category: Dict[str, List[UserFact]] = {}
    for fact in facts:
        if fact.category not in by_category:
            by_category[fact.category] = []
        by_category[fact.category].append(fact)

    # Build context string with EXPLICIT priority ordering
    # Phase 1.3.7: corrections > system > preferences > biographical
    parts = []
    max_chars = max_tokens * 4  # Approximate token to char ratio
    current_chars = 0

    # Priority 1: CORRECTIONS (highest priority - things SAM got wrong)
    if "corrections" in by_category and current_chars < max_chars:
        corrections = [f.fact for f in by_category["corrections"][:3]]
        correction_text = f"IMPORTANT - Remember: {'; '.join(corrections)}"
        parts.append(correction_text)
        current_chars += len(correction_text)

    # Priority 2: SYSTEM preferences (how user wants SAM to behave)
    if "system" in by_category and current_chars < max_chars:
        system = [f.fact for f in by_category["system"][:2]]
        system_text = f"User preferences: {'; '.join(system)}"
        parts.append(system_text)
        current_chars += len(system_text)

    # Priority 3: General PREFERENCES
    if "preferences" in by_category and current_chars < max_chars:
        prefs = [f.fact for f in by_category["preferences"][:3]]
        pref_text = f"Preferences: {'; '.join(prefs)}"
        parts.append(pref_text)
        current_chars += len(pref_text)

    # Priority 4: BIOGRAPHICAL (lower priority for context)
    if "biographical" in by_category and current_chars < max_chars:
        bio = [f.fact for f in by_category["biographical"][:2]]
        bio_text = f"About user: {'; '.join(bio)}"
        parts.append(bio_text)
        current_chars += len(bio_text)

    # Lower priority items (only if space remains)
    if "projects" in by_category and current_chars < max_chars * 0.9:
        projects = [f.fact for f in by_category["projects"][:2]]
        proj_text = f"Current projects: {'; '.join(projects)}"
        parts.append(proj_text)
        current_chars += len(proj_text)

    if "skills" in by_category and current_chars < max_chars * 0.9:
        skills = [f.fact for f in by_category["skills"][:2]]
        skill_text = f"Skills: {'; '.join(skills)}"
        parts.append(skill_text)
        current_chars += len(skill_text)

    return "\n".join(parts) if parts else ""


def build_context_with_project(
    user_id: str = "david",
    project_id: Optional[str] = None,
    min_confidence: float = 0.5,
    max_tokens: int = 300
) -> str:
    """
    Build context string combining user facts and project-specific facts.

    Phase 2.1.8: Enhanced to include project-specific memory.

    Priority Order (highest to lowest):
    1. PROJECT corrections - Project-specific things to remember
    2. corrections - User-level things SAM got wrong
    3. PROJECT facts - Architecture, decisions, technologies for current project
    4. system - User's technical preferences about SAM
    5. preferences - Likes/dislikes/style choices
    6. biographical - Personal facts about the user

    Args:
        user_id: User identifier
        project_id: Optional project identifier for project-specific facts
        min_confidence: Minimum confidence threshold
        max_tokens: Maximum approximate tokens (~4 chars per token)

    Returns:
        Context string suitable for including in prompts
    """
    db = get_fact_db()

    # Get combined user + project facts
    facts = db.get_facts_for_context_with_project(
        user_id=user_id,
        project_id=project_id,
        min_confidence=min_confidence,
        user_limit=10,
        project_limit=10
    )

    if not facts:
        return ""

    # Separate project facts from user facts
    project_facts: List[UserFact] = []
    user_facts: List[UserFact] = []

    for fact in facts:
        if fact.project_id:
            project_facts.append(fact)
        else:
            user_facts.append(fact)

    # Group user facts by category
    by_category: Dict[str, List[UserFact]] = {}
    for fact in user_facts:
        if fact.category not in by_category:
            by_category[fact.category] = []
        by_category[fact.category].append(fact)

    # Build context string
    parts = []
    max_chars = max_tokens * 4
    current_chars = 0

    # Priority 1: PROJECT-SPECIFIC FACTS (highest priority when in a project)
    if project_facts and current_chars < max_chars:
        # Group project facts by category
        proj_corrections = [f.fact for f in project_facts if f.category == "corrections"][:2]
        proj_other = [f.fact for f in project_facts if f.category != "corrections"][:5]

        if proj_corrections:
            proj_corr_text = f"PROJECT [{project_id}] IMPORTANT: {'; '.join(proj_corrections)}"
            parts.append(proj_corr_text)
            current_chars += len(proj_corr_text)

        if proj_other and current_chars < max_chars:
            proj_text = f"PROJECT [{project_id}]: {'; '.join(proj_other)}"
            parts.append(proj_text)
            current_chars += len(proj_text)

    # Priority 2: User CORRECTIONS (things SAM got wrong)
    if "corrections" in by_category and current_chars < max_chars:
        corrections = [f.fact for f in by_category["corrections"][:3]]
        correction_text = f"IMPORTANT - Remember: {'; '.join(corrections)}"
        parts.append(correction_text)
        current_chars += len(correction_text)

    # Priority 3: SYSTEM preferences (how user wants SAM to behave)
    if "system" in by_category and current_chars < max_chars:
        system = [f.fact for f in by_category["system"][:2]]
        system_text = f"User preferences: {'; '.join(system)}"
        parts.append(system_text)
        current_chars += len(system_text)

    # Priority 4: General PREFERENCES
    if "preferences" in by_category and current_chars < max_chars:
        prefs = [f.fact for f in by_category["preferences"][:3]]
        pref_text = f"Preferences: {'; '.join(prefs)}"
        parts.append(pref_text)
        current_chars += len(pref_text)

    # Priority 5: BIOGRAPHICAL (lower priority for context)
    if "biographical" in by_category and current_chars < max_chars * 0.9:
        bio = [f.fact for f in by_category["biographical"][:2]]
        bio_text = f"About user: {'; '.join(bio)}"
        parts.append(bio_text)
        current_chars += len(bio_text)

    return "\n".join(parts) if parts else ""


# ============================================================================
# BACKWARD COMPATIBILITY (FactMemory wrapper for existing code)
# ============================================================================

# Aliases for existing code that uses the old interface
def get_fact_memory() -> FactMemory:
    """Get singleton FactMemory instance (alias for get_fact_db)."""
    return get_fact_db()


def get_user_context(user_id: str = "david", max_tokens: int = 150) -> str:
    """
    Get user context string (backward compatible).

    Args:
        user_id: User identifier
        max_tokens: Maximum approximate tokens (chars/4)

    Returns:
        Formatted context string for prompt injection
    """
    context = build_user_context(user_id)

    # Truncate if needed
    max_chars = max_tokens * 4
    if len(context) > max_chars:
        truncated = context[:max_chars]
        last_semicolon = truncated.rfind(";")
        if last_semicolon > max_chars * 0.7:
            truncated = truncated[:last_semicolon + 1]
        return truncated + "..."

    return context


def remember_fact(
    user_id: str,
    fact: str,
    category: str = "preferences"
) -> Optional[str]:
    """
    Convenience function to remember a fact.

    Args:
        user_id: User identifier
        fact: The fact to remember
        category: Fact category

    Returns:
        Fact ID if stored
    """
    db = get_fact_db()
    saved = db.save_fact(
        fact=fact,
        category=category,
        source="explicit",
        user_id=user_id,
    )
    return saved.fact_id if saved else None


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SAM Fact Memory System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fact_memory.py list
  python fact_memory.py list --category preferences
  python fact_memory.py list --user david --min-confidence 0.7
  python fact_memory.py add "Likes Python" --category preferences
  python fact_memory.py extract "I am a software engineer from Sydney"
  python fact_memory.py search "python"
  python fact_memory.py stats
  python fact_memory.py decay --apply
  python fact_memory.py decay --apply --simulate 7
  python fact_memory.py context
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List facts")
    list_parser.add_argument("--category", "-c", help="Filter by category")
    list_parser.add_argument("--user", "-u", default="david", help="User ID")
    list_parser.add_argument("--min-confidence", "-m", type=float, default=0.0,
                            help="Minimum confidence threshold")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    list_parser.add_argument("--inactive", "-i", action="store_true",
                            help="Include inactive facts")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a fact")
    add_parser.add_argument("fact", help="The fact text")
    add_parser.add_argument("--category", "-c", required=True, help="Fact category")
    add_parser.add_argument("--user", "-u", default="david", help="User ID")
    add_parser.add_argument("--source", "-s", default="explicit",
                           choices=["explicit", "conversation", "correction", "inferred", "system"],
                           help="Fact source")
    add_parser.add_argument("--confidence", type=float, help="Override confidence")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract facts from text")
    extract_parser.add_argument("text", help="Text to extract facts from")
    extract_parser.add_argument("--user", "-u", default="david", help="User ID")
    extract_parser.add_argument("--no-save", action="store_true", help="Don't save extracted facts")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search facts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--user", "-u", default="david", help="User ID")
    search_parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")

    # Stats command
    subparsers.add_parser("stats", help="Show statistics")

    # Decay command
    decay_parser = subparsers.add_parser("decay", help="Apply decay maintenance")
    decay_parser.add_argument("--apply", "-a", action="store_true",
                             help="Actually apply decay (without this, shows preview only)")
    decay_parser.add_argument("--simulate", "-s", type=float, default=None,
                             help="Simulate decay for N days (for testing)")
    decay_parser.add_argument("--days", "-d", type=int, default=30,
                             help="Days before purging inactive facts")

    # Context command
    context_parser = subparsers.add_parser("context", help="Build context string")
    context_parser.add_argument("--user", "-u", default="david", help="User ID")
    context_parser.add_argument("--min-confidence", "-m", type=float, default=0.5,
                               help="Minimum confidence threshold")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    db = FactMemory()

    if args.command == "list":
        facts = db.get_facts(
            user_id=args.user,
            category=args.category,
            min_confidence=args.min_confidence,
            limit=args.limit,
            include_inactive=args.inactive,
        )

        if not facts:
            print("No facts found.")
            return

        print(f"\nFacts for user '{args.user}':")
        print("-" * 60)

        for fact in facts:
            status = "ACTIVE" if fact.is_active else "INACTIVE"
            print(f"\n[{fact.category}] {fact.fact}")
            print(f"  Confidence: {fact.confidence:.2f} | Source: {fact.source} | {status}")
            print(f"  Reinforced: {fact.reinforcement_count}x | First seen: {fact.first_seen[:10] if fact.first_seen else 'unknown'}")

        print(f"\n{len(facts)} fact(s) found.")

    elif args.command == "add":
        fact = db.save_fact(
            fact=args.fact,
            category=args.category,
            source=args.source,
            confidence=args.confidence,
            user_id=args.user,
        )

        print(f"\nFact saved:")
        print(f"  ID: {fact.fact_id}")
        print(f"  Fact: {fact.fact}")
        print(f"  Category: {fact.category}")
        print(f"  Source: {fact.source}")
        print(f"  Confidence: {fact.confidence:.2f}")

    elif args.command == "extract":
        facts = db.extract_facts_from_text(
            text=args.text,
            user_id=args.user,
            save=not args.no_save,
        )

        if not facts:
            print("No facts extracted from the text.")
            return

        action = "Extracted and saved" if not args.no_save else "Extracted (not saved)"
        print(f"\n{action} {len(facts)} fact(s):")
        print("-" * 60)

        for fact in facts:
            print(f"\n[{fact.category}] {fact.fact}")
            print(f"  Confidence: {fact.confidence:.2f} | Subcategory: {fact.subcategory or 'none'}")

    elif args.command == "search":
        facts = db.search_facts(
            query=args.query,
            user_id=args.user,
            limit=args.limit,
        )

        if not facts:
            print(f"No facts matching '{args.query}'.")
            return

        print(f"\nFacts matching '{args.query}':")
        print("-" * 60)

        for fact in facts:
            print(f"\n[{fact.category}] {fact.fact}")
            print(f"  Confidence: {fact.confidence:.2f} | Source: {fact.source}")

        print(f"\n{len(facts)} fact(s) found.")

    elif args.command == "stats":
        stats = db.get_stats()

        print("\nFact Memory Statistics")
        print("=" * 40)
        print(f"Total facts: {stats['total_facts']}")
        print(f"Active facts: {stats['active_facts']}")
        print(f"Average confidence: {stats['avg_confidence']:.3f}")
        print(f"High confidence (>=0.9): {stats['high_confidence_count']}")
        print(f"Low confidence (<0.3): {stats['low_confidence_count']}")

        print("\nBy Category:")
        for cat, count in sorted(stats['by_category'].items()):
            print(f"  {cat}: {count}")

        print("\nBy Source:")
        for source, count in sorted(stats['by_source'].items()):
            print(f"  {source}: {count}")

        print("\nBy User:")
        for user, count in sorted(stats['by_user'].items()):
            print(f"  {user}: {count}")

        print("\nStorage:")
        print(f"  Location: {stats['storage']['location']}")
        print(f"  External drive: {'yes' if stats['storage']['using_external_drive'] else 'no'}")

    elif args.command == "decay":
        if args.simulate is not None:
            # Simulation mode: show what would happen if N days passed
            print(f"\nSimulating decay for {args.simulate} days (Ebbinghaus forgetting curve)...")
            print("-" * 60)

            facts = db.get_facts(include_inactive=False, limit=100)
            if not facts:
                print("No facts to simulate decay for.")
                return

            simulated_deactivated = 0
            simulated_changes = []

            for fact in facts:
                if fact.source == "system":
                    continue

                old_conf = fact.confidence
                new_conf = decay_confidence_ebbinghaus(
                    fact.confidence,
                    args.simulate,
                    fact.decay_rate,
                    fact.reinforcement_count,
                    fact.decay_floor
                )

                if abs(new_conf - old_conf) > 0.001:
                    will_deactivate = new_conf < CONFIDENCE_THRESHOLDS["forget"]
                    status = " [WOULD DEACTIVATE]" if will_deactivate else ""
                    simulated_changes.append({
                        'fact': fact.fact[:50],
                        'category': fact.category,
                        'old': old_conf,
                        'new': new_conf,
                        'deactivate': will_deactivate
                    })
                    if will_deactivate:
                        simulated_deactivated += 1

            if simulated_changes:
                print(f"\nAfter {args.simulate} days, {len(simulated_changes)} facts would change:")
                for change in simulated_changes:
                    status = " [DEACTIVATE]" if change['deactivate'] else ""
                    print(f"\n[{change['category']}] {change['fact']}...")
                    print(f"  Confidence: {change['old']:.3f} -> {change['new']:.3f}{status}")

                print(f"\n\nSummary: {len(simulated_changes)} would decay, {simulated_deactivated} would be deactivated")
                print("\nTo apply decay, run: python fact_memory.py decay --apply")
            else:
                print("No significant changes would occur.")

        elif args.apply:
            # Actually apply decay
            print("Applying decay maintenance (Ebbinghaus forgetting curve)...")
            stats = db.apply_decay(days_threshold=args.days)

            # Update the last_decay_run timestamp
            db._set_metadata("last_decay_run", datetime.now().isoformat())

            print("\nDecay Results:")
            print(f"  Facts updated: {stats['updated']}")
            print(f"  Facts deactivated: {stats['deactivated']}")
            print(f"  Old inactive facts purged: {stats['purged']}")

            # Show last decay run
            last_decay = db._get_metadata("last_decay_run")
            if last_decay:
                print(f"\n  Last decay run: {last_decay}")

        else:
            # Preview mode (default without --apply)
            print("\nDecay Preview (use --apply to execute, --simulate N to test N days)")
            print("-" * 60)

            # Get last decay timestamp
            last_decay = db._get_metadata("last_decay_run")
            if last_decay:
                try:
                    last_dt = datetime.fromisoformat(last_decay)
                    days_since = (datetime.now() - last_dt).total_seconds() / 86400.0
                    print(f"Last decay run: {last_decay}")
                    print(f"Days since last decay: {days_since:.1f}")

                    if days_since >= 1.0:
                        print(f"\nRunning 'python fact_memory.py decay --apply' would apply {days_since:.1f} days of decay.")
                    else:
                        print("\nLess than 1 day since last decay - no changes would be applied.")
                except ValueError:
                    print("Last decay timestamp is invalid.")
            else:
                print("No previous decay run recorded.")
                print("First 'decay --apply' will set the baseline timestamp.")

            # Show some stats about what would be affected
            facts = db.get_facts(include_inactive=False, limit=100)
            system_facts = sum(1 for f in facts if f.source == "system")
            decayable = len(facts) - system_facts
            low_conf = sum(1 for f in facts if f.confidence < 0.3 and f.source != "system")

            print(f"\nCurrent state:")
            print(f"  Total active facts: {len(facts)}")
            print(f"  System facts (no decay): {system_facts}")
            print(f"  Facts subject to decay: {decayable}")
            print(f"  Low confidence (<0.3): {low_conf}")

    elif args.command == "context":
        context = build_user_context(args.user, args.min_confidence)

        if context:
            print(f"\nContext for user '{args.user}':")
            print("-" * 40)
            print(context)
        else:
            print("No facts available for context.")


if __name__ == "__main__":
    main()
