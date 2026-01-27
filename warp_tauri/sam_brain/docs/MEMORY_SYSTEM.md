# SAM Memory System Documentation

**Phase:** 1.3.12 - Memory System Documentation
**Version:** 1.0.0
**Date:** 2026-01-24
**Status:** Complete

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Core Components](#3-core-components)
4. [Fact Categories and Sources](#4-fact-categories-and-sources)
5. [Confidence Decay Algorithm](#5-confidence-decay-algorithm)
6. [CLI Commands](#6-cli-commands)
7. [API Endpoints](#7-api-endpoints)
8. [What Do You Know About Me Feature](#8-what-do-you-know-about-me-feature)
9. [Integration with Orchestrator](#9-integration-with-orchestrator)
10. [Troubleshooting](#10-troubleshooting)
11. [Related Documentation](#11-related-documentation)

---

## 1. Overview

SAM's memory system enables persistent, cross-session knowledge retention. Unlike traditional chatbots that forget everything between sessions, SAM learns about users over time and naturally forgets unused information - just like human memory.

### Key Capabilities

- **Long-term fact storage** - Remembers user preferences, skills, projects, and biographical information
- **Natural decay** - Facts fade over time unless reinforced, preventing stale information
- **Multiple sources** - Tracks whether facts came from explicit statements, conversation extraction, or inference
- **Confidence scoring** - Each fact has a confidence level that affects when and how SAM uses it
- **Semantic memory** - Vector embeddings for similarity-based recall
- **Working memory** - Cognitive-inspired short-term memory with limited capacity

### Design Principles

1. **Temporal Awareness** - Facts age and confidence decays without reinforcement
2. **Multi-Source Tracking** - Know where each fact came from
3. **Mergeable** - Similar facts combine rather than duplicate
4. **Queryable** - Fast lookup by user, category, or content
5. **Auditable** - Full provenance tracking for transparency
6. **Multi-User Ready** - Support for multiple users from day one

### Storage Locations

```
Primary Fact Store:   /Volumes/David External/sam_memory/facts.db
Fallback:             ~/.sam/facts.db (if external drive not mounted)

Semantic Memory:      sam_brain/memory/embeddings.json
                      sam_brain/memory/index.npy

Conversation Memory:  /Volumes/David External/sam_memory/memory.db
Procedural Memory:    /Volumes/David External/sam_memory/procedural.db
```

---

## 2. Architecture

### High-Level Architecture

```
+------------------------------------------------------------------+
|                     SAM MEMORY SYSTEM                            |
+------------------------------------------------------------------+
|                                                                  |
|  +-----------------+    +------------------+    +---------------+|
|  |   User Input    |--->|   Orchestrator   |--->|   Response    ||
|  +-----------------+    +--------+---------+    +---------------+|
|                                  |                               |
|                                  v                               |
|  +---------------------------------------------------------------+
|  |                    MEMORY LAYER                               |
|  |                                                               |
|  |  +-------------+  +---------------+  +--------------------+   |
|  |  | FactMemory  |  | SemanticMemory|  | ConversationMemory |   |
|  |  | (facts.db)  |  | (embeddings)  |  |    (memory.db)     |   |
|  |  +------+------+  +-------+-------+  +---------+----------+   |
|  |         |                 |                    |              |
|  |         v                 v                    v              |
|  |  +-------------+  +---------------+  +--------------------+   |
|  |  | UserFact    |  | MemoryEntry   |  | Message, Fact,     |   |
|  |  | (dataclass) |  | (dataclass)   |  | Preference         |   |
|  |  +-------------+  +---------------+  +--------------------+   |
|  +---------------------------------------------------------------+
|                                                                  |
|  +---------------------------------------------------------------+
|  |                 COGNITIVE LAYER                               |
|  |                                                               |
|  |  +----------------+  +----------------+  +------------------+ |
|  |  | WorkingMemory  |  | ProceduralMem  |  | MemoryDecayMgr   | |
|  |  | (7+/-2 items)  |  | (skills.db)    |  | (Ebbinghaus)     | |
|  |  +----------------+  +----------------+  +------------------+ |
|  +---------------------------------------------------------------+
+------------------------------------------------------------------+
```

### Data Flow: Fact Extraction and Retrieval

```
User Message: "I'm a Python developer from Sydney"
                    |
                    v
         +--------------------+
         |   FactExtractor    |  <-- Pattern matching on input
         +--------------------+
                    |
                    | Extracts:
                    |   - "Is a Python developer" (biographical/occupation)
                    |   - "Located in Sydney" (biographical/location)
                    v
         +--------------------+
         |    FactMemory      |  <-- Deduplication & storage
         +--------------------+
                    |
                    | Checks for existing similar facts
                    | Either reinforces or creates new
                    v
         +--------------------+
         |     facts.db       |  <-- SQLite persistence
         +--------------------+
                    |
         (Later, on next query)
                    v
         +--------------------+
         | build_user_context |  <-- Retrieves high-confidence facts
         +--------------------+
                    |
                    | Priority: corrections > system > preferences > bio
                    v
         +--------------------+
         |   Prompt Injection  |  <-- Facts included in prompt
         +--------------------+
                    |
                    v
             SAM Response with context awareness
```

### Component Relationships

```
+------------------------+
|      sam_api.py        |  <-- HTTP API entry point
|  (port 8765)           |
+----------+-------------+
           |
           v
+------------------------+        +------------------------+
| orchestrator.py        |<------>| cognitive/             |
| (request routing)      |        | unified_orchestrator.py|
+----------+-------------+        +------------------------+
           |                                  |
           v                                  v
+------------------------+        +------------------------+
| fact_memory.py         |        | self_knowledge_handler |
| (FactMemory, UserFact) |        | ("What do you know?")  |
+------------------------+        +------------------------+
           |
           v
+------------------------+        +------------------------+
| semantic_memory.py     |<------>| conversation_memory.py |
| (vector embeddings)    |        | (session tracking)     |
+------------------------+        +------------------------+
           |
           v
+------------------------+
| cognitive/             |
| enhanced_memory.py     |
| (working memory, decay)|
+------------------------+
```

---

## 3. Core Components

### 3.1 FactMemory (`fact_memory.py`)

The primary fact storage system for user-specific knowledge.

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/fact_memory.py`

**Key Classes:**

#### UserFact Dataclass

```python
@dataclass
class UserFact:
    # Identity
    fact_id: str              # SHA256(user_id + fact + category)[:16]
    user_id: str              # User identifier (default: "david")

    # Content
    fact: str                 # The actual fact text
    category: str             # Category from taxonomy
    subcategory: Optional[str]  # Optional refinement

    # Confidence
    confidence: float         # 0.0-1.0 current confidence
    initial_confidence: float # Starting confidence when first learned

    # Source Tracking
    source: str               # conversation, explicit, inferred, correction, system
    source_message_id: Optional[str]  # Link to originating message
    source_context: Optional[str]     # Surrounding context when learned

    # Temporal
    first_seen: Optional[str]         # When first learned
    last_reinforced: Optional[str]    # When last confirmed/mentioned
    last_accessed: Optional[str]      # When last used by SAM

    # Reinforcement
    reinforcement_count: int  # Times confirmed
    contradiction_count: int  # Times contradicted

    # Decay
    decay_rate: float         # Per-day decay multiplier (0.0-1.0)
    decay_floor: float        # Minimum confidence after decay

    # Metadata
    metadata: Optional[str]   # JSON string for flexible extra context
    is_active: bool           # Soft delete flag
    superseded_by: Optional[str]  # If merged into another fact
```

#### FactMemory Class Methods

| Method | Description |
|--------|-------------|
| `save_fact(fact, category, source, ...)` | Save a new fact or reinforce existing |
| `get_facts(user_id, category, min_confidence, limit)` | Query facts with filters |
| `get_facts_for_context(user_id, min_confidence, limit)` | Get facts for prompt injection |
| `search_facts(query, user_id, min_confidence, limit)` | Keyword search on facts |
| `extract_facts_from_text(text, user_id, save)` | Extract facts using patterns |
| `reinforce_fact(fact_id)` | Increase confidence on access |
| `contradict_fact(fact_id, reason)` | Record contradiction |
| `apply_decay(days_threshold)` | Apply Ebbinghaus decay to all facts |
| `get_stats()` | Get comprehensive statistics |
| `deactivate_fact(fact_id, reason)` | Soft-delete a fact |
| `reactivate_fact(fact_id)` | Restore a deactivated fact |

### 3.2 FactExtractor

Pattern-based extraction of facts from natural language.

**Patterns Recognized:**

| Pattern | Category | Subcategory | Example |
|---------|----------|-------------|---------|
| `my name is X` | biographical | name | "My name is David" |
| `I'm a/an X` | biographical | occupation | "I'm a software engineer" |
| `I'm in/from X` | biographical | location | "I'm from Sydney" |
| `I live in X` | biographical | location | "I live in Australia" |
| `I like/love/enjoy X` | preferences | topics | "I love Python" |
| `I hate/dislike X` | preferences | dislikes | "I hate meetings" |
| `I prefer X over Y` | preferences | tools | "I prefer vim over emacs" |
| `I'm working on X` | projects | active | "I'm working on SAM" |
| `I work with X` | projects | active | "I work with AI models" |
| `I'm good at X` | skills | expert | "I'm good at debugging" |
| `I'm learning X` | skills | learning | "I'm learning Rust" |
| `I know/use X` | skills | intermediate | "I use MLX" |
| `My wife/husband/partner is X` | relationships | family | "My partner is Sarah" |
| `I have cats/dogs named X` | relationships | pets | "I have a cat named Pixel" |
| `Keep responses short` | system | response_length | "Keep your responses concise" |
| `Don't use emojis` | system | emoji_use | "Don't use emojis" |
| `Remember that X` | (inferred) | - | "Remember that I prefer dark mode" |

### 3.3 SemanticMemory (`semantic_memory.py`)

Vector embeddings for similarity-based recall using MLX MiniLM-L6-v2.

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py`

**Key Features:**

- **MLX Native** - Uses Apple Silicon for fast 384-dim embeddings (~10ms)
- **Entry Types** - interaction, code, solution, note, pattern, improvement_feedback
- **Cosine Similarity** - Semantic search across all memories
- **Evolution Feedback** - Tracks improvement attempts and outcomes

**Key Methods:**

```python
# Add memories
memory.add_interaction(query, response, project, success)
memory.add_code(code, language, description, file_path)
memory.add_solution(problem, solution, tags)
memory.add_note(note, category)
memory.add_improvement_feedback(...)

# Search memories
memory.search(query, limit, entry_type)
memory.search_similar_problems(problem, limit)
memory.search_relevant_code(description, limit)

# Get context
memory.get_context_for_query(query, max_entries)
```

### 3.4 EnhancedMemory (`cognitive/enhanced_memory.py`)

Cognitive-inspired memory with working memory limits and decay.

**Components:**

#### WorkingMemory

Implements Miller's Law: 7+/-2 items in active memory.

```python
class WorkingMemory:
    MIN_CAPACITY = 5
    MAX_CAPACITY = 9
    DEFAULT_CAPACITY = 7
    DECAY_RATE = 0.1      # Per turn
    REHEARSAL_BOOST = 0.3  # Activation boost on access
```

Features:
- Activation-based decay per conversation turn
- Importance-weighted retention
- Focus mechanism for keeping items active
- Thread-safe operations

#### ProceduralMemory

Stores learned skills with trigger patterns.

```python
@dataclass
class Skill:
    id: str
    name: str
    description: str
    trigger_patterns: List[str]  # Regex patterns
    implementation: str          # Python code or prompt template
    success_count: int
    failure_count: int
    last_used: Optional[datetime]
```

#### MemoryDecayManager

Implements Ebbinghaus forgetting curve for memory decay.

```python
class MemoryDecayManager:
    RETENTION_RATE = 0.9      # Base retention per day
    IMPORTANCE_WEIGHT = 0.5   # How much importance affects retention
```

---

## 4. Fact Categories and Sources

### 4.1 Primary Categories

| Category | Description | Decay Rate | Floor |
|----------|-------------|------------|-------|
| `preferences` | User likes/dislikes, style choices | 0.99 | 0.2 |
| `biographical` | Personal facts about the user | 0.995 | 0.3 |
| `projects` | Current and past work | 0.97 | 0.1 |
| `skills` | Technical and non-technical abilities | 0.98 | 0.15 |
| `corrections` | Things SAM got wrong that user corrected | 0.90 | 0.05 |
| `relationships` | People and entities the user knows | 0.99 | 0.2 |
| `context` | Situational facts that change | 0.85 | 0.0 |
| `system` | Technical preferences about SAM | 1.0 | 0.9 |

### 4.2 Subcategories

```
preferences:
  - communication_style   # How they want SAM to talk
  - coding_style          # Code formatting, conventions
  - tools                 # Preferred tools/editors
  - topics                # Topics they enjoy discussing
  - dislikes              # Things to avoid

biographical:
  - location
  - occupation
  - name
  - timezone
  - background
  - hardware

projects:
  - active                # Currently working on
  - completed             # Past projects
  - goals                 # Project objectives
  - technologies          # Tech stack per project

skills:
  - expert                # High proficiency
  - intermediate
  - learning              # Currently developing
  - interested            # Wants to learn

corrections:
  - factual               # Wrong facts
  - technical             # Wrong code/technical info
  - style                 # Wrong tone/format
  - personal              # Wrong personal assumptions

relationships:
  - family
  - professional
  - pets
  - social

context:
  - current_task
  - mood
  - availability
  - environment

system:
  - response_length
  - formality
  - emoji_use
  - explanation_depth
  - storage
```

### 4.3 Fact Sources

| Source | Initial Confidence | Description |
|--------|-------------------|-------------|
| `explicit` | 0.95 | User directly stated ("Remember that...") |
| `correction` | 0.90 | User corrected SAM |
| `conversation` | 0.60 | Extracted from conversation |
| `inferred` | 0.40 | SAM inferred from context |
| `system` | 1.0 | System-set facts (don't decay) |

---

## 5. Confidence Decay Algorithm

SAM uses an **Ebbinghaus forgetting curve** for natural memory decay. Facts that aren't accessed or reinforced gradually lose confidence, eventually becoming inactive.

### 5.1 The Formula

```
C(t) = max(floor, C0 * e^(-t/S))

Where:
  C(t)  = confidence at time t
  C0    = initial confidence
  t     = days elapsed since last reinforcement
  S     = stability = base_stability * (1 + k * ln(1 + n))
  floor = minimum confidence (category-specific)
  k     = reinforcement factor (0.3)
  n     = reinforcement count
```

### 5.2 Half-Life Examples

| Decay Rate | Half-Life | Use Case |
|------------|-----------|----------|
| 0.98 | ~50 days | Stable facts (preferences, bio) |
| 0.95 | ~14 days | Moderate change (projects) |
| 0.90 | ~7 days | Frequent change (corrections) |
| 0.85 | ~4 days | Ephemeral (context) |

### 5.3 How Decay Works

1. **Automatic on Startup** - When SAM starts, it calculates days since last run and applies decay
2. **Reinforcement Slows Decay** - Each time a fact is accessed or confirmed, its stability increases
3. **Deactivation at Threshold** - Facts below 0.1 confidence are soft-deleted
4. **Permanent Purge** - Inactive facts older than 30 days are permanently deleted

### 5.4 Testing Effect

When facts are retrieved for context, they receive a small reinforcement boost:

```python
# ~1-2% boost when accessed (testing effect)
boost = 0.02 / math.log1p(reinforcement_count + 1)
new_confidence = min(1.0, old_confidence + boost)
```

This simulates the memory research finding that recalling information strengthens the memory.

### 5.5 Decay Simulation

Preview what would happen after N days:

```bash
# Simulate 7 days of decay
python fact_memory.py decay --simulate 7

# See which facts would be affected
# Output shows confidence changes and potential deactivations
```

---

## 6. CLI Commands

The fact memory system includes a comprehensive CLI for management and debugging.

### 6.1 List Facts

```bash
# List all active facts
python fact_memory.py list

# Filter by category
python fact_memory.py list --category preferences

# Filter by minimum confidence
python fact_memory.py list --min-confidence 0.7

# Filter by user
python fact_memory.py list --user david

# Include inactive facts
python fact_memory.py list --inactive

# Combine filters
python fact_memory.py list --user david --category skills --min-confidence 0.5 --limit 10
```

### 6.2 Add Facts

```bash
# Add a fact explicitly
python fact_memory.py add "Prefers Python over JavaScript" --category preferences

# Add with source type
python fact_memory.py add "Expert in Rust" --category skills --source explicit

# Add with custom confidence
python fact_memory.py add "Lives in Sydney" --category biographical --confidence 0.9

# Add for specific user
python fact_memory.py add "Uses M2 Mac Mini" --category biographical --user david
```

### 6.3 Extract Facts

```bash
# Extract facts from text (auto-saves)
python fact_memory.py extract "I am a software engineer from Sydney who loves Python"

# Extract without saving (preview only)
python fact_memory.py extract "I prefer dark mode" --no-save

# Extract for specific user
python fact_memory.py extract "I'm learning Rust" --user david
```

**Example Output:**

```
Extracted and saved 2 fact(s):
------------------------------------------------------------

[biographical] Is a software engineer
  Confidence: 0.70 | Subcategory: occupation

[biographical] Located in Sydney
  Confidence: 0.80 | Subcategory: location
```

### 6.4 Search Facts

```bash
# Search by keyword
python fact_memory.py search "python"

# Search with limit
python fact_memory.py search "project" --limit 5

# Search for specific user
python fact_memory.py search "rust" --user david
```

### 6.5 View Statistics

```bash
python fact_memory.py stats

# Output:
# Fact Memory Statistics
# ========================================
# Total facts: 47
# Active facts: 42
# Average confidence: 0.723
# High confidence (>=0.9): 12
# Low confidence (<0.3): 3
#
# By Category:
#   biographical: 8
#   preferences: 15
#   projects: 10
#   skills: 6
#   corrections: 3
#
# By Source:
#   conversation: 25
#   explicit: 15
#   inferred: 7
#
# By User:
#   david: 47
#
# Storage:
#   Location: /Volumes/David External/sam_memory/facts.db
#   External drive: yes
```

### 6.6 Decay Management

```bash
# Preview decay status (no changes)
python fact_memory.py decay

# Show what would happen after 7 days
python fact_memory.py decay --simulate 7

# Actually apply decay
python fact_memory.py decay --apply

# Apply decay with custom purge threshold
python fact_memory.py decay --apply --days 60
```

**Simulation Output:**

```
Simulating decay for 7 days (Ebbinghaus forgetting curve)...
------------------------------------------------------------

After 7 days, 5 facts would change:

[projects] Working on SAM...
  Confidence: 0.850 -> 0.789

[context] Currently debugging memory issue...
  Confidence: 0.600 -> 0.312 [DEACTIVATE]

Summary: 5 would decay, 1 would be deactivated

To apply decay, run: python fact_memory.py decay --apply
```

### 6.7 Build Context

```bash
# Build context string for a user
python fact_memory.py context

# With custom confidence threshold
python fact_memory.py context --min-confidence 0.7

# For specific user
python fact_memory.py context --user david
```

**Output:**

```
Context for user 'david':
----------------------------------------
IMPORTANT - Remember: Sydney is NOT the capital (Canberra is)
User preferences: Prefers concise responses; Dislikes emojis
Preferences: Likes Python; Prefers dark mode
About user: Is a software engineer; Located in Sydney
Current projects: Working on SAM; Building AI assistant
Skills: Expert in Python; Expert in Rust
```

---

## 7. API Endpoints

The SAM API (`sam_api.py`) exposes fact memory via HTTP on port 8765.

### 7.1 Get User Context

**Endpoint:** `GET /api/facts/context/{user_id}`

Returns formatted context string with all active facts.

```bash
curl http://localhost:8765/api/facts/context/david
```

**Response:**

```json
{
  "user_id": "david",
  "context": "IMPORTANT - Remember: ... \nUser preferences: ...",
  "fact_count": 15,
  "storage_location": "/Volumes/David External/sam_memory/facts.db",
  "stats": {
    "total_facts": 47,
    "active_facts": 42,
    "avg_confidence": 0.723
  }
}
```

### 7.2 List Facts

**Endpoint:** `GET /api/facts/list`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | "david" | User identifier |
| `category` | string | null | Filter by category |
| `min_confidence` | float | 0.0 | Minimum confidence |
| `limit` | int | 50 | Maximum results |
| `include_inactive` | bool | false | Include deactivated facts |

```bash
curl "http://localhost:8765/api/facts/list?category=preferences&min_confidence=0.5"
```

**Response:**

```json
{
  "facts": [
    {
      "fact_id": "a1b2c3d4e5f6",
      "fact": "Prefers concise responses",
      "category": "preferences",
      "subcategory": "communication_style",
      "confidence": 0.95,
      "source": "explicit",
      "first_seen": "2026-01-15T10:30:00",
      "reinforcement_count": 5
    }
  ],
  "total": 15,
  "filtered_count": 8
}
```

### 7.3 Add Fact

**Endpoint:** `POST /api/facts/add`

**Request Body:**

```json
{
  "fact": "Prefers Python for ML",
  "category": "preferences",
  "subcategory": "tools",
  "source": "explicit",
  "confidence": 0.9,
  "user_id": "david"
}
```

```bash
curl -X POST http://localhost:8765/api/facts/add \
  -H "Content-Type: application/json" \
  -d '{"fact": "Prefers Python for ML", "category": "preferences"}'
```

**Response:**

```json
{
  "success": true,
  "fact_id": "b2c3d4e5f6g7",
  "fact": "Prefers Python for ML",
  "confidence": 0.9,
  "is_new": true
}
```

### 7.4 Reinforce Fact

**Endpoint:** `POST /api/facts/{fact_id}/reinforce`

Increases confidence and updates last_reinforced timestamp.

```bash
curl -X POST http://localhost:8765/api/facts/a1b2c3d4e5f6/reinforce
```

**Response:**

```json
{
  "success": true,
  "fact_id": "a1b2c3d4e5f6",
  "old_confidence": 0.85,
  "new_confidence": 0.89,
  "reinforcement_count": 6
}
```

### 7.5 Deactivate Fact

**Endpoint:** `DELETE /api/facts/{fact_id}`

Soft-deletes a fact (can be reactivated later).

```bash
curl -X DELETE http://localhost:8765/api/facts/a1b2c3d4e5f6
```

**Response:**

```json
{
  "success": true,
  "fact_id": "a1b2c3d4e5f6",
  "action": "deactivated"
}
```

### 7.6 Get Statistics

**Endpoint:** `GET /api/facts/stats`

```bash
curl http://localhost:8765/api/facts/stats
```

**Response:**

```json
{
  "total_facts": 47,
  "active_facts": 42,
  "avg_confidence": 0.723,
  "high_confidence_count": 12,
  "low_confidence_count": 3,
  "by_category": {
    "preferences": 15,
    "biographical": 8,
    "projects": 10
  },
  "by_source": {
    "conversation": 25,
    "explicit": 15,
    "inferred": 7
  },
  "storage": {
    "location": "/Volumes/David External/sam_memory/facts.db",
    "using_external_drive": true
  }
}
```

---

## 8. What Do You Know About Me Feature

SAM can respond to questions about stored knowledge with a formatted summary.

### 8.1 Trigger Patterns

The following queries activate the self-knowledge handler:

- "What do you know about me?"
- "What have you learned about me?"
- "What do you remember about me?"
- "Tell me what you know about me"
- "Tell me everything you know about me"
- "Show me my profile"
- "Show my facts"
- "What's in my memory?"
- "List my facts"
- "Do you know anything about me?"

### 8.2 Response Format

**Example Response:**

```
Alright, let me share what I've picked up about you. I've got 12 things
noted across 5 categories:

**About You:**
- Is a software engineer (very confident) [learned 2 weeks ago]
- Located in Sydney, Australia (confident) [learned 1 week ago]
- Has M2 Mac Mini with 8GB RAM (very confident) [learned 3 weeks ago]

**Your Preferences:**
- Prefers concise responses (very confident) [learned 2 weeks ago]
- Likes Python over JavaScript (confident) [learned 1 week ago]
- Dislikes emojis in responses (confident) [learned 5 days ago]

**Your Projects:**
- Building SAM, a self-improving AI assistant (very confident) [learned 3 weeks ago]
- Working on RVC voice training (fairly sure) [learned 3 days ago]

**Your Skills:**
- Expert in Python and Rust (confident) [learned 2 weeks ago]
- Learning MLX (fairly sure) [learned 1 week ago]

**Things You've Corrected Me On:**
- Sydney is NOT the capital of Australia (Canberra is) (confident) [learned 2 days ago]

Anything I should add, update, or forget? Just let me know.
```

### 8.3 Confidence Labels

| Confidence Range | Label |
|-----------------|-------|
| >= 0.9 | "very confident" |
| >= 0.7 | "confident" |
| >= 0.5 | "fairly sure" |
| >= 0.3 | "uncertain" |
| < 0.3 | "vague memory" |

### 8.4 Using the Handler

**From Python:**

```python
from cognitive.self_knowledge_handler import handle_self_knowledge_query

# Check if query is about self-knowledge
response = handle_self_knowledge_query("What do you know about me?", user_id="david")

if response:
    print(response.response)
    print(f"Facts: {response.facts_count}")
    print(f"Categories: {response.categories_found}")
```

**CLI:**

```bash
# Test query detection
python cognitive/self_knowledge_handler.py --query "What do you know about me?"

# Show knowledge directly
python cognitive/self_knowledge_handler.py --show --user david
```

---

## 9. Integration with Orchestrator

The memory system is integrated into SAM's request processing pipeline.

### 9.1 Unified Orchestrator Integration

**Location:** `cognitive/unified_orchestrator.py`

The orchestrator:

1. **Loads FactMemory on init** - Creates singleton instance on startup
2. **Injects user context** - Adds facts to prompts before sending to LLM
3. **Extracts facts from responses** - Analyzes user messages for new facts

```python
class UnifiedOrchestrator:
    def __init__(self):
        # ...
        if _fact_memory_available:
            self.fact_memory = get_fact_memory()

    def _get_user_context(self, user_id: str) -> str:
        """Get formatted user context for prompt injection."""
        if not self.fact_memory:
            return ""

        from fact_memory import build_user_context
        context = build_user_context(user_id, min_confidence=0.3)
        return context

    def process(self, user_input: str, ...):
        # Get user context
        user_context = self._get_user_context(user_id)

        # Build prompt with context
        prompt = f"{user_context}\n\nUser: {user_input}"

        # Extract facts from user input
        if self.fact_memory:
            extracted = self.fact_memory.extract_facts_from_text(
                user_input, user_id
            )
```

### 9.2 Context Priority Order

When building context, facts are ordered by importance:

1. **Corrections** - Things SAM got wrong (MUST not repeat)
2. **System** - User's technical preferences about SAM
3. **Preferences** - Likes/dislikes/style choices
4. **Biographical** - Personal facts about the user
5. **Projects** - What the user is working on
6. **Skills** - User's abilities

### 9.3 Automatic Fact Extraction

Every user message is analyzed for extractable facts:

```python
# In process() method
if self.fact_memory:
    extracted = self.fact_memory.extract_facts_from_text(
        user_input,
        user_id,
        save=True  # Automatically persist
    )
    if extracted:
        log_info(f"Extracted {len(extracted)} facts from user input")
```

### 9.4 Self-Knowledge Query Handling

The orchestrator checks for self-knowledge queries before routing:

```python
from cognitive.self_knowledge_handler import handle_self_knowledge_query

# Check if this is a "what do you know about me?" query
self_knowledge_response = handle_self_knowledge_query(user_input, user_id)
if self_knowledge_response:
    return self_knowledge_response.response
```

---

## 10. Troubleshooting

### 10.1 Facts Not Persisting

**Symptom:** Facts disappear after restart.

**Causes & Solutions:**

1. **External drive not mounted**
   ```bash
   # Check if drive is mounted
   ls /Volumes/David\ External/

   # If not, facts go to fallback location
   ls ~/.sam/facts.db
   ```

2. **Auto-decay running on startup**
   ```bash
   # Check decay status
   python fact_memory.py decay

   # See last decay run timestamp
   sqlite3 /Volumes/David\ External/sam_memory/facts.db \
     "SELECT * FROM fact_metadata WHERE key='last_decay_run'"
   ```

3. **Confidence too low**
   ```bash
   # Check for inactive facts
   python fact_memory.py list --inactive
   ```

### 10.2 Facts Not Appearing in Context

**Symptom:** SAM doesn't seem to remember facts during conversation.

**Causes & Solutions:**

1. **Confidence below threshold**
   ```bash
   # Check confidence levels
   python fact_memory.py list --min-confidence 0.0

   # Reinforce important facts
   python fact_memory.py add "Important fact" --category preferences --source explicit
   ```

2. **Orchestrator not loading facts**
   ```python
   # Check if fact_memory is available in orchestrator
   from cognitive.unified_orchestrator import UnifiedOrchestrator
   orch = UnifiedOrchestrator()
   print(f"FactMemory available: {orch.fact_memory is not None}")
   ```

3. **Context truncated**
   ```bash
   # Check full context output
   python fact_memory.py context

   # Verify token limit isn't too low
   ```

### 10.3 Duplicate Facts

**Symptom:** Same fact stored multiple times.

**Solutions:**

1. **Check for similar facts**
   ```bash
   python fact_memory.py search "python"
   ```

2. **Reinforce instead of add**
   ```python
   # The save_fact method auto-reinforces if fact exists
   db.save_fact("Likes Python", "preferences")  # Will reinforce if exists
   ```

3. **Manual cleanup**
   ```bash
   # View all facts with IDs
   sqlite3 /Volumes/David\ External/sam_memory/facts.db \
     "SELECT fact_id, fact, confidence FROM user_facts WHERE fact LIKE '%python%'"

   # Deactivate duplicates
   # (through API or code, not direct SQL to preserve history)
   ```

### 10.4 Decay Running Too Aggressively

**Symptom:** Facts disappearing faster than expected.

**Solutions:**

1. **Check decay rates**
   ```bash
   python fact_memory.py stats
   # Look at category decay rates
   ```

2. **Increase reinforcement**
   ```bash
   # Manually reinforce important facts
   curl -X POST http://localhost:8765/api/facts/FACT_ID/reinforce
   ```

3. **Adjust category settings** (in code)
   ```python
   # In fact_memory.py, modify CATEGORY_DECAY_RATES
   # Higher = slower decay (0.99 = 1% per day)
   ```

### 10.5 Common SQL Queries

```bash
# Connect to database
sqlite3 /Volumes/David\ External/sam_memory/facts.db

# View all active facts
SELECT fact_id, fact, category, confidence, source
FROM user_facts
WHERE is_active = 1
ORDER BY confidence DESC;

# View facts by category
SELECT * FROM user_facts WHERE category = 'preferences';

# View fact history
SELECT h.*, f.fact
FROM fact_history h
JOIN user_facts f ON h.fact_id = f.fact_id
ORDER BY h.timestamp DESC
LIMIT 20;

# View metadata
SELECT * FROM fact_metadata;

# Count by category
SELECT category, COUNT(*), AVG(confidence) as avg_conf
FROM user_facts
WHERE is_active = 1
GROUP BY category;
```

### 10.6 Reset Everything

**WARNING: This deletes all facts!**

```bash
# Backup first!
cp /Volumes/David\ External/sam_memory/facts.db \
   /Volumes/David\ External/sam_memory/facts.db.backup

# Delete and recreate (or just delete - will recreate on next run)
rm /Volumes/David\ External/sam_memory/facts.db
```

---

## 11. Related Documentation

### Core Files

| File | Location | Purpose |
|------|----------|---------|
| `fact_memory.py` | `sam_brain/` | Primary fact storage and decay |
| `semantic_memory.py` | `sam_brain/` | Vector embeddings for semantic search |
| `conversation_memory.py` | `sam_brain/` | Session-based conversation memory |
| `enhanced_memory.py` | `sam_brain/cognitive/` | Working memory and procedural memory |
| `self_knowledge_handler.py` | `sam_brain/cognitive/` | "What do you know?" handler |
| `unified_orchestrator.py` | `sam_brain/cognitive/` | Request processing with memory |
| `sam_api.py` | `sam_brain/` | HTTP API endpoints |

### Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| FACT_SCHEMA.md | `sam_brain/docs/` | Detailed schema design |
| MEMORY_AUDIT.md | `sam_brain/docs/` | Memory system analysis |
| CLAUDE.md | `sam_brain/` | SAM Brain architecture overview |

### SSOT References

| Document | Location | Purpose |
|----------|----------|---------|
| CLAUDE_READ_FIRST.md | `/Volumes/Plex/SSOT/` | Master context and rules |
| SAM_TERMINAL.md | `/Volumes/Plex/SSOT/projects/` | Terminal interface docs |
| ORCHESTRATOR.md | `/Volumes/Plex/SSOT/projects/` | Request routing docs |

### External Storage

| Path | Purpose |
|------|---------|
| `/Volumes/David External/sam_memory/` | Primary memory storage |
| `/Volumes/David External/sam_memory/facts.db` | Fact database |
| `/Volumes/David External/sam_memory/memory.db` | Conversation memory |
| `/Volumes/David External/sam_memory/procedural.db` | Skills database |
| `~/.sam/` | Fallback storage if external not mounted |

---

*Documentation generated for SAM Phase 1.3.12 - Memory System Documentation*
*Last updated: 2026-01-24*
