# SAM Long-Term Fact Schema

*Phase 1.3.2 - User Fact Memory Design*
*Version: 1.0.0 | Created: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Schema Design](#schema-design)
3. [SQLite Table Definitions](#sqlite-table-definitions)
4. [Category Taxonomy](#category-taxonomy)
5. [Confidence System](#confidence-system)
6. [Decay Algorithm](#decay-algorithm)
7. [Fact Merging Strategy](#fact-merging-strategy)
8. [Example Facts](#example-facts)
9. [Integration Points](#integration-points)
10. [Query Patterns](#query-patterns)

---

## Overview

### Purpose

The Fact Schema provides persistent storage for user-specific knowledge that SAM learns over time. Unlike episodic memory (conversation history) or semantic memory (embeddings), facts are structured assertions about users that can be queried, decayed, reinforced, and merged.

### Design Principles

1. **Temporal Awareness** - Facts age and confidence decays without reinforcement
2. **Multi-Source** - Track whether facts came from explicit statements, inference, or conversation
3. **Mergeable** - Similar facts combine rather than duplicate
4. **Queryable** - Fast lookup by user, category, or content
5. **Auditable** - Full provenance tracking for debugging and transparency
6. **Multi-User Ready** - Support for multiple users from day one

### Storage Location

```
Primary:   /Volumes/David External/sam_memory/facts.db
Fallback:  ~/.sam/facts.db (if external drive not mounted)
```

---

## Schema Design

### Core Fact Entity

```python
@dataclass
class UserFact:
    """A single learned fact about a user."""

    # === Identity ===
    fact_id: str              # SHA256(user_id + fact + category)[:16]
    user_id: str              # User identifier (default: "david")

    # === Content ===
    fact: str                 # The actual fact text
    category: str             # Category from taxonomy
    subcategory: Optional[str]  # Optional refinement

    # === Confidence ===
    confidence: float         # 0.0-1.0 current confidence
    initial_confidence: float # Starting confidence when first learned

    # === Source Tracking ===
    source: str               # conversation, explicit, inferred, correction
    source_message_id: Optional[str]  # Link to originating message
    source_context: Optional[str]     # Surrounding context when learned

    # === Temporal ===
    first_seen: datetime      # When first learned
    last_reinforced: datetime # When last confirmed/mentioned
    last_accessed: datetime   # When last used by SAM

    # === Reinforcement ===
    reinforcement_count: int  # Times confirmed
    contradiction_count: int  # Times contradicted

    # === Decay ===
    decay_rate: float         # Per-day decay multiplier (0.0-1.0)
    decay_floor: float        # Minimum confidence after decay

    # === Metadata ===
    metadata: Dict[str, Any]  # Flexible extra context
    is_active: bool           # Soft delete flag
    superseded_by: Optional[str]  # If merged into another fact
```

### Fact Embedding (for semantic search)

```python
@dataclass
class FactEmbedding:
    """Vector embedding for semantic fact search."""

    fact_id: str              # Links to UserFact
    embedding: List[float]    # 384-dim MiniLM-L6-v2 vector
    embedding_model: str      # Model used (for version tracking)
    created_at: datetime
```

### Fact Relation (for fact graphs)

```python
@dataclass
class FactRelation:
    """Relationship between two facts."""

    relation_id: str
    source_fact_id: str
    target_fact_id: str
    relation_type: str        # implies, contradicts, related_to, part_of
    strength: float           # 0.0-1.0 relationship strength
    created_at: datetime
```

---

## SQLite Table Definitions

### Main Facts Table

```sql
CREATE TABLE IF NOT EXISTS user_facts (
    -- Identity
    fact_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'david',

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
    metadata TEXT,  -- JSON
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

-- Full-text search on fact content
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    fact_id,
    fact,
    category,
    subcategory,
    content='user_facts',
    content_rowid='rowid'
);
```

### Fact Embeddings Table

```sql
CREATE TABLE IF NOT EXISTS fact_embeddings (
    fact_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,  -- numpy array as bytes
    embedding_model TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    created_at TEXT NOT NULL,

    FOREIGN KEY (fact_id) REFERENCES user_facts(fact_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_model ON fact_embeddings(embedding_model);
```

### Fact Relations Table

```sql
CREATE TABLE IF NOT EXISTS fact_relations (
    relation_id TEXT PRIMARY KEY,
    source_fact_id TEXT NOT NULL,
    target_fact_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    strength REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,

    FOREIGN KEY (source_fact_id) REFERENCES user_facts(fact_id) ON DELETE CASCADE,
    FOREIGN KEY (target_fact_id) REFERENCES user_facts(fact_id) ON DELETE CASCADE,
    CHECK (relation_type IN ('implies', 'contradicts', 'related_to', 'part_of', 'supersedes')),
    CHECK (strength >= 0.0 AND strength <= 1.0),
    UNIQUE (source_fact_id, target_fact_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON fact_relations(source_fact_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON fact_relations(target_fact_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON fact_relations(relation_type);
```

### Fact History Table (for auditing)

```sql
CREATE TABLE IF NOT EXISTS fact_history (
    history_id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL,
    change_type TEXT NOT NULL,  -- created, reinforced, contradicted, merged, deleted
    old_confidence REAL,
    new_confidence REAL,
    change_reason TEXT,
    timestamp TEXT NOT NULL,

    FOREIGN KEY (fact_id) REFERENCES user_facts(fact_id)
);

CREATE INDEX IF NOT EXISTS idx_history_fact ON fact_history(fact_id);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON fact_history(timestamp DESC);
```

---

## Category Taxonomy

### Primary Categories

| Category | Description | Decay Rate | Examples |
|----------|-------------|------------|----------|
| `preferences` | User likes/dislikes, style choices | 0.99 | "Prefers dark mode", "Likes Python over JavaScript" |
| `biographical` | Personal facts about the user | 0.995 | "Lives in Sydney", "Works as a developer" |
| `projects` | Current and past work | 0.97 | "Building SAM AI assistant", "Uses Tauri for desktop apps" |
| `skills` | Technical and non-technical abilities | 0.98 | "Expert in Rust", "Learning MLX" |
| `corrections` | Things SAM got wrong that user corrected | 0.90 | "Sydney is not the capital of Australia" |
| `relationships` | People and entities the user knows | 0.99 | "Partner is named X", "Works with Y" |
| `context` | Situational facts that change | 0.85 | "Currently debugging memory issue" |
| `system` | Technical preferences about SAM | 0.999 | "Wants responses under 200 words" |

### Subcategories

```python
CATEGORY_SUBCATEGORIES = {
    "preferences": [
        "communication_style",   # How they want SAM to talk
        "coding_style",          # Code formatting, conventions
        "tools",                 # Preferred tools/editors
        "topics",                # Topics they enjoy discussing
        "dislikes",              # Things to avoid
    ],
    "biographical": [
        "location",
        "occupation",
        "name",
        "timezone",
        "background",
    ],
    "projects": [
        "active",                # Currently working on
        "completed",             # Past projects
        "goals",                 # Project objectives
        "technologies",          # Tech stack per project
    ],
    "skills": [
        "expert",                # High proficiency
        "intermediate",
        "learning",              # Currently developing
        "interested",            # Wants to learn
    ],
    "corrections": [
        "factual",               # Wrong facts
        "technical",             # Wrong code/technical info
        "style",                 # Wrong tone/format
        "personal",              # Wrong personal assumptions
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
    ],
}
```

---

## Confidence System

### Initial Confidence by Source

```python
SOURCE_INITIAL_CONFIDENCE = {
    "explicit": 0.95,      # User directly stated
    "correction": 0.90,    # User corrected SAM
    "conversation": 0.60,  # Extracted from conversation
    "inferred": 0.40,      # SAM inferred from context
    "system": 1.0,         # System-set facts (don't decay)
}
```

### Confidence Modifiers

```python
def calculate_confidence(fact: UserFact, current_time: datetime) -> float:
    """Calculate current effective confidence."""

    # Start with stored confidence
    base = fact.confidence

    # Apply time decay since last reinforcement
    days_since_reinforced = (current_time - fact.last_reinforced).days
    decayed = base * (fact.decay_rate ** days_since_reinforced)

    # Apply floor
    decayed = max(decayed, fact.decay_floor)

    # Boost from reinforcement count (log scale)
    reinforcement_boost = min(0.2, 0.05 * math.log1p(fact.reinforcement_count))

    # Penalty from contradictions
    contradiction_penalty = min(0.3, 0.1 * fact.contradiction_count)

    # Final confidence
    final = decayed + reinforcement_boost - contradiction_penalty
    return max(0.0, min(1.0, final))
```

### Confidence Thresholds

```python
CONFIDENCE_THRESHOLDS = {
    "certain": 0.9,         # Very confident, can state directly
    "likely": 0.7,          # Probably true, mention casually
    "possible": 0.5,        # Maybe true, ask for confirmation
    "uncertain": 0.3,       # Low confidence, don't use unless asked
    "forget": 0.1,          # Below this, mark for deletion
}
```

---

## Decay Algorithm

### Ebbinghaus-Inspired Decay

The decay model is based on the Ebbinghaus forgetting curve, modified for practical use:

```python
def decay_confidence(
    initial: float,
    days_elapsed: float,
    decay_rate: float,
    reinforcement_count: int,
    floor: float = 0.1
) -> float:
    """
    Calculate decayed confidence using modified forgetting curve.

    Formula: C(t) = max(floor, C0 * R^t * (1 + k*ln(1+n)))

    Where:
        C0 = initial confidence
        R = decay rate per day (0.98 default = 2% loss/day)
        t = days elapsed
        k = reinforcement factor (0.1)
        n = reinforcement count
        floor = minimum confidence
    """
    # Base decay
    decayed = initial * (decay_rate ** days_elapsed)

    # Reinforcement bonus (more reinforcements = slower effective decay)
    reinforcement_factor = 1 + 0.1 * math.log1p(reinforcement_count)
    decayed *= reinforcement_factor

    # Apply floor
    return max(floor, min(1.0, decayed))
```

### Category-Specific Decay Rates

```python
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

CATEGORY_DECAY_FLOORS = {
    "preferences": 0.2,       # Never forget strong preferences
    "biographical": 0.3,      # Keep biographical basics
    "projects": 0.1,          # Can forget old projects
    "skills": 0.15,           # Skills don't fully disappear
    "corrections": 0.05,      # Corrections can be forgotten
    "relationships": 0.2,     # Remember key relationships
    "context": 0.0,           # Context can fully expire
    "system": 0.9,            # System prefs stay high
}
```

### Maintenance Job

```python
def run_decay_maintenance(db: FactDB, current_time: datetime = None):
    """
    Periodic maintenance to apply decay and prune forgotten facts.

    Run daily or on session start.
    """
    current_time = current_time or datetime.now()

    # 1. Update confidence for all active facts
    facts = db.get_all_active_facts()
    for fact in facts:
        new_confidence = decay_confidence(
            fact.confidence,
            (current_time - fact.last_reinforced).days,
            fact.decay_rate,
            fact.reinforcement_count,
            fact.decay_floor
        )

        if new_confidence != fact.confidence:
            db.update_confidence(fact.fact_id, new_confidence)

    # 2. Mark facts below threshold as inactive
    forgotten = db.get_facts_below_confidence(0.1)
    for fact in forgotten:
        db.deactivate_fact(fact.fact_id, reason="decay_below_threshold")

    # 3. Permanently delete very old inactive facts (>30 days inactive)
    db.purge_old_inactive_facts(days=30)

    return {
        "updated": len(facts),
        "deactivated": len(forgotten),
    }
```

---

## Fact Merging Strategy

### When to Merge

Two facts should be merged when:

1. **Same semantic meaning** - Embedding similarity > 0.85
2. **Same category** - Both facts in same category
3. **Same user** - Belong to same user
4. **Compatible sources** - Neither is a system fact unless both are

### Merge Algorithm

```python
def should_merge_facts(fact1: UserFact, fact2: UserFact,
                       embedding1: np.ndarray, embedding2: np.ndarray) -> bool:
    """Determine if two facts should be merged."""

    # Must be same user and category
    if fact1.user_id != fact2.user_id:
        return False
    if fact1.category != fact2.category:
        return False

    # System facts don't merge with non-system
    if (fact1.source == 'system') != (fact2.source == 'system'):
        return False

    # Check semantic similarity
    similarity = cosine_similarity(embedding1, embedding2)

    # High threshold for merging
    return similarity > 0.85


def merge_facts(fact1: UserFact, fact2: UserFact) -> UserFact:
    """
    Merge two facts into one.

    Strategy:
    - Keep the more confident fact as base
    - Combine reinforcement counts
    - Use earliest first_seen
    - Use latest last_reinforced
    - Combine sources if different
    """
    # Determine which is primary (higher confidence)
    if fact2.confidence > fact1.confidence:
        primary, secondary = fact2, fact1
    else:
        primary, secondary = fact1, fact2

    # Create merged fact
    merged = UserFact(
        fact_id=generate_fact_id(primary.user_id, primary.fact, primary.category),
        user_id=primary.user_id,

        # Keep primary's content (higher confidence)
        fact=primary.fact,
        category=primary.category,
        subcategory=primary.subcategory or secondary.subcategory,

        # Combine confidence (weighted average + bonus)
        confidence=min(1.0,
            (primary.confidence * 0.6 + secondary.confidence * 0.4) + 0.1
        ),
        initial_confidence=max(primary.initial_confidence, secondary.initial_confidence),

        # Source: prefer explicit > correction > conversation > inferred
        source=_best_source(primary.source, secondary.source),
        source_message_id=primary.source_message_id,
        source_context=primary.source_context or secondary.source_context,

        # Temporal: earliest first, latest reinforced
        first_seen=min(primary.first_seen, secondary.first_seen),
        last_reinforced=max(primary.last_reinforced, secondary.last_reinforced),
        last_accessed=max(primary.last_accessed, secondary.last_accessed),

        # Combine counts
        reinforcement_count=primary.reinforcement_count + secondary.reinforcement_count,
        contradiction_count=primary.contradiction_count + secondary.contradiction_count,

        # Keep primary's decay settings
        decay_rate=primary.decay_rate,
        decay_floor=primary.decay_floor,

        # Merge metadata
        metadata={**secondary.metadata, **primary.metadata},
        is_active=True,
        superseded_by=None,
    )

    return merged


def _best_source(s1: str, s2: str) -> str:
    """Return the better source."""
    priority = {
        'explicit': 4,
        'correction': 3,
        'conversation': 2,
        'inferred': 1,
        'system': 5,
    }
    return s1 if priority.get(s1, 0) >= priority.get(s2, 0) else s2
```

### Contradiction Handling

```python
def handle_contradiction(existing: UserFact, new_fact: str,
                         source: str, db: FactDB) -> UserFact:
    """
    Handle when a new fact contradicts an existing one.

    Strategy:
    1. If new source > existing source: replace
    2. If sources equal: increment contradiction, maybe supersede
    3. If new source < existing: just note the contradiction
    """
    source_priority = {
        'explicit': 4,
        'correction': 3,
        'conversation': 2,
        'inferred': 1,
        'system': 5,
    }

    existing_priority = source_priority.get(existing.source, 0)
    new_priority = source_priority.get(source, 0)

    if new_priority > existing_priority:
        # Replace with new fact
        db.deactivate_fact(existing.fact_id, reason="superseded_by_higher_source")
        new = db.create_fact(
            user_id=existing.user_id,
            fact=new_fact,
            category=existing.category,
            source=source,
            metadata={"supersedes": existing.fact_id}
        )
        db.add_relation(new.fact_id, existing.fact_id, "supersedes", 1.0)
        return new

    elif new_priority == existing_priority:
        # Increment contradiction count
        existing.contradiction_count += 1

        # If too many contradictions, consider replacing
        if existing.contradiction_count >= 3:
            existing.confidence *= 0.5
            # Create competing fact with low confidence
            competing = db.create_fact(
                user_id=existing.user_id,
                fact=new_fact,
                category=existing.category,
                source=source,
                confidence=0.4,
                metadata={"contradicts": existing.fact_id}
            )
            db.add_relation(competing.fact_id, existing.fact_id, "contradicts", 0.8)
            return competing

        db.update_fact(existing)
        return existing

    else:
        # Note contradiction but don't change much
        existing.contradiction_count += 1
        existing.confidence *= 0.95  # Minor penalty
        db.update_fact(existing)
        return existing
```

---

## Example Facts

### David's Fact Examples

```json
[
  {
    "fact_id": "f_a1b2c3d4e5f6",
    "user_id": "david",
    "fact": "Prefers responses to be concise and under 200 words unless asked for detail",
    "category": "preferences",
    "subcategory": "communication_style",
    "confidence": 0.95,
    "source": "explicit",
    "first_seen": "2026-01-15T10:30:00",
    "last_reinforced": "2026-01-24T14:00:00",
    "reinforcement_count": 5,
    "decay_rate": 0.99
  },
  {
    "fact_id": "f_b2c3d4e5f6g7",
    "user_id": "david",
    "fact": "Building SAM, a self-improving AI assistant with personality",
    "category": "projects",
    "subcategory": "active",
    "confidence": 0.98,
    "source": "conversation",
    "first_seen": "2026-01-01T09:00:00",
    "last_reinforced": "2026-01-24T16:00:00",
    "reinforcement_count": 47,
    "decay_rate": 0.97
  },
  {
    "fact_id": "f_c3d4e5f6g7h8",
    "user_id": "david",
    "fact": "Has M2 Mac Mini with 8GB RAM - must optimize for memory constraints",
    "category": "biographical",
    "subcategory": "hardware",
    "confidence": 0.99,
    "source": "explicit",
    "first_seen": "2026-01-02T11:00:00",
    "last_reinforced": "2026-01-24T12:00:00",
    "reinforcement_count": 23,
    "decay_rate": 0.995
  },
  {
    "fact_id": "f_d4e5f6g7h8i9",
    "user_id": "david",
    "fact": "Expert in Python and Rust programming",
    "category": "skills",
    "subcategory": "expert",
    "confidence": 0.92,
    "source": "inferred",
    "first_seen": "2026-01-05T15:00:00",
    "last_reinforced": "2026-01-20T10:00:00",
    "reinforcement_count": 12,
    "decay_rate": 0.98
  },
  {
    "fact_id": "f_e5f6g7h8i9j0",
    "user_id": "david",
    "fact": "Lives in Sydney, Australia timezone (AEDT)",
    "category": "biographical",
    "subcategory": "location",
    "confidence": 0.88,
    "source": "conversation",
    "first_seen": "2026-01-10T08:00:00",
    "last_reinforced": "2026-01-18T09:00:00",
    "reinforcement_count": 3,
    "decay_rate": 0.995
  },
  {
    "fact_id": "f_f6g7h8i9j0k1",
    "user_id": "david",
    "fact": "Sydney is NOT the capital of Australia (Canberra is)",
    "category": "corrections",
    "subcategory": "factual",
    "confidence": 0.90,
    "source": "correction",
    "first_seen": "2026-01-22T14:30:00",
    "last_reinforced": "2026-01-22T14:30:00",
    "reinforcement_count": 1,
    "decay_rate": 0.90,
    "metadata": {
      "original_error": "SAM said Sydney was the capital"
    }
  },
  {
    "fact_id": "f_g7h8i9j0k1l2",
    "user_id": "david",
    "fact": "Uses external storage at /Volumes/David External for large files",
    "category": "system",
    "subcategory": "storage",
    "confidence": 1.0,
    "source": "system",
    "first_seen": "2026-01-01T00:00:00",
    "last_reinforced": "2026-01-24T00:00:00",
    "reinforcement_count": 100,
    "decay_rate": 1.0,
    "decay_floor": 0.9
  }
]
```

### Fact Relations Examples

```json
[
  {
    "source_fact_id": "f_b2c3d4e5f6g7",
    "target_fact_id": "f_c3d4e5f6g7h8",
    "relation_type": "related_to",
    "strength": 0.9,
    "comment": "SAM project requires 8GB RAM optimization"
  },
  {
    "source_fact_id": "f_d4e5f6g7h8i9",
    "target_fact_id": "f_b2c3d4e5f6g7",
    "relation_type": "implies",
    "strength": 0.8,
    "comment": "Python/Rust skills used for SAM development"
  },
  {
    "source_fact_id": "f_f6g7h8i9j0k1",
    "target_fact_id": "f_e5f6g7h8i9j0",
    "relation_type": "related_to",
    "strength": 0.6,
    "comment": "Both about Australia geography"
  }
]
```

---

## Integration Points

### With Existing Memory Systems

```python
# === Integration with conversation_memory.py ===
# When extracting facts from conversations

from conversation_memory import ConversationMemory
from fact_memory import FactDB

def on_message_processed(message_id: str, content: str, facts: List[str]):
    """Called when conversation memory extracts potential facts."""
    fact_db = FactDB()

    for fact_text in facts:
        # Check for similar existing facts
        similar = fact_db.find_similar_facts(fact_text, threshold=0.85)

        if similar:
            # Reinforce existing fact
            fact_db.reinforce_fact(similar[0].fact_id, message_id)
        else:
            # Create new fact
            fact_db.create_fact(
                fact=fact_text,
                source="conversation",
                source_message_id=message_id
            )


# === Integration with semantic_memory.py ===
# Use fact embeddings for search

from semantic_memory import get_memory

def get_relevant_facts_for_query(query: str, user_id: str) -> List[UserFact]:
    """Find facts relevant to a query using semantic search."""
    fact_db = FactDB()

    # Get query embedding
    memory = get_memory()
    query_embedding = memory._get_embedding(query)

    # Search fact embeddings
    return fact_db.semantic_search(
        query_embedding,
        user_id=user_id,
        limit=5,
        min_confidence=0.3
    )


# === Integration with enhanced_memory.py ===
# Add high-confidence facts to working memory

from cognitive.enhanced_memory import EnhancedMemoryManager, MemoryType

def load_relevant_facts_to_working_memory(
    manager: EnhancedMemoryManager,
    query: str,
    user_id: str
):
    """Load relevant user facts into working memory."""
    fact_db = FactDB()
    relevant = fact_db.get_relevant_facts(query, user_id, limit=3)

    for fact in relevant:
        if fact.confidence > 0.7:
            manager.add_fact(
                fact=f"[User fact] {fact.fact}",
                importance=fact.confidence
            )


# === Integration with feedback_system.py ===
# Corrections create high-confidence facts

from feedback_system import FeedbackDB

def on_correction_received(correction_entry):
    """Create fact from user correction."""
    fact_db = FactDB()

    # Extract the correct information
    fact_db.create_fact(
        fact=correction_entry.correction,
        category="corrections",
        source="correction",
        source_message_id=correction_entry.response_id,
        initial_confidence=0.90,
        metadata={
            "original_response": correction_entry.original_response,
            "what_was_wrong": correction_entry.what_was_wrong
        }
    )
```

### Context Building

```python
def build_user_context(user_id: str, query: str) -> str:
    """Build context string from user facts for prompt injection."""
    fact_db = FactDB()

    # Get high-confidence facts
    facts = fact_db.get_facts_for_context(
        user_id=user_id,
        min_confidence=0.5,
        limit=10
    )

    # Group by category
    by_category = {}
    for fact in facts:
        if fact.category not in by_category:
            by_category[fact.category] = []
        by_category[fact.category].append(fact)

    # Build context string
    parts = []

    if "preferences" in by_category:
        prefs = [f.fact for f in by_category["preferences"][:3]]
        parts.append(f"User preferences: {'; '.join(prefs)}")

    if "projects" in by_category:
        projects = [f.fact for f in by_category["projects"][:2]]
        parts.append(f"Current projects: {'; '.join(projects)}")

    if "skills" in by_category:
        skills = [f.fact for f in by_category["skills"][:3]]
        parts.append(f"User skills: {'; '.join(skills)}")

    if "corrections" in by_category:
        # Only include recent, high-confidence corrections
        corrections = [f for f in by_category["corrections"] if f.confidence > 0.7][:2]
        if corrections:
            parts.append(f"Remember: {'; '.join(c.fact for c in corrections)}")

    return "\n".join(parts) if parts else ""
```

---

## Query Patterns

### Common Queries

```python
class FactDB:
    """Fact database interface."""

    def get_user_facts(
        self,
        user_id: str,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[UserFact]:
        """Get facts for a user, optionally filtered."""
        query = """
            SELECT * FROM user_facts
            WHERE user_id = ? AND is_active = 1 AND confidence >= ?
        """
        params = [user_id, min_confidence]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        return self._execute_query(query, params)

    def find_similar_facts(
        self,
        fact_text: str,
        user_id: str,
        threshold: float = 0.85
    ) -> List[Tuple[UserFact, float]]:
        """Find semantically similar facts using embeddings."""
        embedding = self._get_embedding(fact_text)

        # Get all fact embeddings for user
        candidates = self._get_user_embeddings(user_id)

        similar = []
        for fact_id, fact_embedding in candidates:
            similarity = cosine_similarity(embedding, fact_embedding)
            if similarity >= threshold:
                fact = self.get_fact(fact_id)
                similar.append((fact, similarity))

        return sorted(similar, key=lambda x: x[1], reverse=True)

    def reinforce_fact(
        self,
        fact_id: str,
        source_message_id: Optional[str] = None
    ) -> UserFact:
        """Reinforce an existing fact (increases confidence)."""
        fact = self.get_fact(fact_id)

        fact.reinforcement_count += 1
        fact.last_reinforced = datetime.now()
        fact.last_accessed = datetime.now()

        # Confidence boost (diminishing returns)
        boost = 0.05 / math.log1p(fact.reinforcement_count)
        fact.confidence = min(1.0, fact.confidence + boost)

        self._update_fact(fact)
        self._log_history(fact_id, "reinforced", source_message_id)

        return fact

    def get_facts_for_context(
        self,
        user_id: str,
        min_confidence: float = 0.5,
        limit: int = 10
    ) -> List[UserFact]:
        """Get facts suitable for context injection."""
        query = """
            SELECT * FROM user_facts
            WHERE user_id = ?
              AND is_active = 1
              AND confidence >= ?
              AND category != 'context'  -- Skip ephemeral context
            ORDER BY
              CASE category
                WHEN 'corrections' THEN 1  -- Corrections first
                WHEN 'system' THEN 2       -- System prefs second
                WHEN 'preferences' THEN 3
                ELSE 4
              END,
              confidence DESC
            LIMIT ?
        """
        return self._execute_query(query, [user_id, min_confidence, limit])

    def semantic_search(
        self,
        query_embedding: np.ndarray,
        user_id: str,
        limit: int = 5,
        min_confidence: float = 0.3
    ) -> List[UserFact]:
        """Search facts by semantic similarity to query embedding."""
        # Get all active fact embeddings for user
        sql = """
            SELECT f.fact_id, e.embedding
            FROM user_facts f
            JOIN fact_embeddings e ON f.fact_id = e.fact_id
            WHERE f.user_id = ? AND f.is_active = 1 AND f.confidence >= ?
        """
        rows = self._execute_raw(sql, [user_id, min_confidence])

        # Score by similarity
        scored = []
        for fact_id, embedding_bytes in rows:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            similarity = cosine_similarity(query_embedding, embedding)
            scored.append((fact_id, similarity))

        # Sort and return top facts
        scored.sort(key=lambda x: x[1], reverse=True)

        return [self.get_fact(fid) for fid, _ in scored[:limit]]
```

---

## Next Steps

### Phase 1.3.3: Implement Fact Extraction

- Build regex/NLP patterns to extract facts from conversation
- Integrate with conversation_memory.py
- Hook into on_message callback

### Phase 1.3.4: Implement Fact Recall

- Build context injection for prompts
- Add fact-aware response generation
- Test with SAM personality

### Phase 1.4: Fact UI

- Display known facts in terminal/GUI
- Allow manual fact editing
- Show confidence decay visualization

---

## Related Documentation

- **Conversation Memory:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/conversation_memory.py`
- **Semantic Memory:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py`
- **Enhanced Memory:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/enhanced_memory.py`
- **Feedback System:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/FEEDBACK_LEARNING.md`
- **SAM Brain Architecture:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`

---

*This schema design is for SAM Phase 1.3.2 - Long-Term Fact Memory. Implementation will follow in subsequent phases.*
