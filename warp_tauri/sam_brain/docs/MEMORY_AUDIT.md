# SAM Memory System Audit

**Phase:** 1.3.1 - Memory Persistence Analysis
**Date:** 2026-01-24
**Status:** Research Complete

---

## Executive Summary

SAM has a sophisticated multi-tier memory system spread across 5 main components. The current implementation provides good infrastructure but has key gaps in **fact persistence integration** and **cross-session recall**. The foundation exists; it needs wiring together.

---

## 1. Memory System Components

### 1.1 conversation_memory.py
**Purpose:** Multi-tier persistent conversation memory

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/conversation_memory.py`

**Storage:**
- **Database:** `/Volumes/David External/sam_memory/memory.db` (SQLite)
- **Format:** Relational tables with indexes

**Tables:**
| Table | Purpose | Record Count |
|-------|---------|--------------|
| messages | Short-term conversation history | 6 |
| facts | Extracted knowledge (subject-predicate-object) | 6 |
| preferences | User preference tracking | 0 |
| sessions | Session metadata with summaries | 1 |

**Key Features:**
- `ConversationMemory` class manages all operations
- Automatic fact extraction via regex patterns from user messages
- Session-based conversation tracking
- Confidence scoring for facts (increases on repetition)
- Verification counting for fact reinforcement
- Memory consolidation after 20 messages (configurable)
- Context prompt builder with fact/preference injection

**Fact Extraction Patterns:**
```python
# "I am/I'm [something]" -> (user, is, something)
# "I like/love/prefer [something]" -> (user, likes, something)
# "I work on/with [something]" -> (user, works_with, something)
```

**Limitations:**
1. Fact extraction is regex-based, missing nuanced statements
2. No semantic deduplication (similar facts stored separately)
3. Preferences table is empty (not being populated)
4. No automatic loading of facts into conversation context
5. Consolidation only creates word-frequency summaries

---

### 1.2 semantic_memory.py
**Purpose:** Vector embeddings for semantic search

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py`

**Storage:**
- **Entries:** `sam_brain/memory/embeddings.json` (21KB, ~20 entries)
- **Index:** `sam_brain/memory/index.npy` (5KB, numpy vectors)

**Entry Types:**
- `interaction` - Q&A pairs from conversations
- `solution` - Problem/solution pairs
- `code` - Code snippets with descriptions
- `note` - General notes
- `pattern` - Recognized patterns
- `improvement_feedback` - Evolution feedback loop data

**Key Features:**
- MLX MiniLM-L6-v2 embeddings (384-dim, ~10ms per embedding)
- Cosine similarity search
- Entry type filtering
- Improvement feedback tracking for self-evolution
- Success rate calculations per improvement type

**Limitations:**
1. Local file storage, not in main memory.db
2. No automatic integration with conversation flow
3. Requires explicit `add_*` calls to store memories
4. No automatic pruning/decay mechanism
5. Embeddings regenerated on every add (no incremental updates)

---

### 1.3 cognitive/enhanced_memory.py
**Purpose:** Cognitive-inspired memory with working memory limits

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/enhanced_memory.py`

**Storage:**
- **Procedural:** `/Volumes/David External/sam_memory/procedural.db`
- **Decay:** `/Volumes/David External/sam_memory/decay.db`

**Components:**

#### WorkingMemory
- Implements Miller's Law (7+/-2 items)
- Activation-based decay per turn (0.1 rate)
- Importance-weighted retention
- Focus mechanism for keeping items active
- Thread-safe with locks

#### ProceduralMemory
- Skill storage with trigger patterns (regex)
- Success/failure tracking
- Confidence scoring based on usage history
- Usage logging for learning

#### MemoryDecayManager
- Ebbinghaus forgetting curve (power law)
- Importance-weighted retention
- Spacing effect for rehearsal bonuses
- Weak memory pruning

**Limitations:**
1. Working memory is session-scoped only
2. Procedural memory has no pre-loaded skills
3. Decay manager tracks IDs but doesn't connect to actual data
4. Not integrated into main orchestrator flow

---

### 1.4 infinite_context.py
**Purpose:** Long-form generation with state management

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/infinite_context.py`

**Storage:**
- **Database:** `~/.sam/infinite_context.db`

**Memory Tiers:**
- `WORKING` - Current chunk context
- `SHORT_TERM` - Recent chunks (max 20)
- `LONG_TERM` - Persistent facts (SQLite)
- `EPISODIC` - Key events/milestones

**Domain Handlers:**
- `StoryStateHandler` - Tracks characters, locations, plot, tone
- `CodeStateHandler` - Tracks functions, classes, imports, TODOs
- `AnalysisStateHandler` - Tracks sections, terms, key points
- `ConversationStateHandler` - Tracks topics, questions, user facts

**Limitations:**
1. Separate database from main memory system
2. State handlers extract domain-specific info but don't persist cross-session
3. User facts extracted but not fed back to conversation memory

---

### 1.5 intelligence_core.db (SAM Intelligence)
**Purpose:** User facts and feedback tracking

**Storage:** `/Volumes/David External/sam_memory/intelligence_core.db`

**Tables:**
| Table | Purpose |
|-------|---------|
| user_facts | Explicit user facts with confidence |
| response_feedback | Response quality feedback |
| distilled_examples | Claude responses for training |
| confidence_adjustments | Topic-based confidence tuning |

**Key Features:**
- User facts stored with `user_id`, `category`, `confidence`
- Confirmation counting for fact reinforcement
- Active/inactive flag for fact validity

**Limitations:**
1. Not integrated with conversation_memory.py facts table
2. Separate from semantic search
3. No automatic population from conversations

---

## 2. Current Data Flow

```
User Message
     |
     v
+--------------------+
| conversation_memory|  <-- Stores message, extracts basic facts
|   (memory.db)      |
+--------------------+
     |
     v (not connected)
+--------------------+
|  semantic_memory   |  <-- Requires explicit add_* calls
|  (embeddings.json) |
+--------------------+
     |
     v (not connected)
+--------------------+
|  enhanced_memory   |  <-- Working memory per session only
|  (procedural.db)   |
+--------------------+
     |
     v (not connected)
+--------------------+
| intelligence_core  |  <-- user_facts table isolated
|                    |
+--------------------+
```

---

## 3. What is Persisted vs Ephemeral

### Persisted (Survives Restart)
| Data | Location | Format |
|------|----------|--------|
| Messages | memory.db/messages | SQLite |
| Extracted facts (basic) | memory.db/facts | SQLite |
| User preferences (unused) | memory.db/preferences | SQLite |
| Session summaries | memory.db/sessions | SQLite |
| Semantic embeddings | memory/embeddings.json | JSON |
| Vector index | memory/index.npy | NumPy |
| Procedural skills | procedural.db | SQLite |
| Decay tracking | decay.db | SQLite |
| User facts | intelligence_core.db/user_facts | SQLite |
| Feedback | feedback.db | SQLite |

### Ephemeral (Lost on Restart)
| Data | Component | Issue |
|------|-----------|-------|
| Working memory items | enhanced_memory.WorkingMemory | In-memory only |
| Current session state | conversation_memory | Session ID regenerated |
| Activation levels | enhanced_memory | Not persisted |
| Focus tracking | enhanced_memory | In-memory only |
| Model cache | semantic_memory | Reloaded on startup |

---

## 4. Cross-Session Memory Gaps

### Gap 1: Facts Not Loaded at Startup
**Issue:** Facts exist in `memory.db/facts` but aren't loaded into context for new sessions.

**Current State:**
- `get_relevant_facts(query)` exists but requires a query
- No automatic "load all high-confidence facts" on startup
- New sessions start with blank context

### Gap 2: Multiple Fact Stores
**Issue:** Facts stored in three places:
1. `memory.db/facts` - conversation_memory.py
2. `intelligence_core.db/user_facts` - sam_intelligence.py
3. `infinite_context.db/long_term_memory` - infinite_context.py

**Impact:** Facts don't transfer between systems.

### Gap 3: Semantic Memory Disconnected
**Issue:** `semantic_memory.py` stores interactions but:
- Not called during normal conversation flow
- No automatic chunking of conversations
- Manual `add_interaction()` required

### Gap 4: No Fact Verification Loop
**Issue:** Facts are extracted but:
- Never confirmed with user
- No contradiction detection
- Confidence only increases, never decreases

### Gap 5: Preferences Table Empty
**Issue:** `set_preference()` method exists but never called in normal flow.

---

## 5. What Needs to be Added for Fact Persistence

### Priority 1: Unified Fact Store
**Action:** Consolidate facts into single authoritative store

Options:
1. Use `memory.db/facts` as primary, sync to others
2. Use `intelligence_core.db/user_facts` (has user_id, category, confidence)
3. Create new unified `facts.db` combining best of both

**Recommendation:** Use `intelligence_core.db/user_facts` schema - it has:
- `user_id` for multi-user support
- `category` for organization
- `confidence` with decay support
- `is_active` for soft deletion
- `confirmation_count` for verification

### Priority 2: Startup Fact Loading
**Action:** Load high-confidence facts at session start

```python
def load_persistent_facts(self, min_confidence=0.6):
    """Load facts that should persist across sessions."""
    facts = self.conn.execute("""
        SELECT fact, category, confidence FROM user_facts
        WHERE confidence >= ? AND is_active = 1
        ORDER BY confidence DESC
        LIMIT 50
    """, (min_confidence,))
    return facts.fetchall()
```

### Priority 3: Enhanced Fact Extraction
**Action:** Improve regex patterns or use LLM-based extraction

Current patterns miss:
- "My wife's name is Sarah" (possession + identity)
- "I've been coding for 20 years" (experience duration)
- "I prefer dark mode" (preferences stated indirectly)
- "Remember that I hate meetings" (explicit remember requests)

### Priority 4: Fact Integration in Context
**Action:** Automatically include relevant facts in prompts

```python
def build_context_prompt(self, user_message: str) -> str:
    # Get all high-confidence facts
    persistent_facts = self.load_persistent_facts(0.7)

    # Get query-relevant facts from semantic search
    relevant_facts = semantic_memory.search(user_message, limit=5)

    # Combine and deduplicate
    context = self._merge_fact_sources(persistent_facts, relevant_facts)

    return f"[User Facts: {context}]\n\n{user_message}"
```

### Priority 5: Explicit Remember Commands
**Action:** Handle "Remember that..." statements specially

Pattern: `remember\s+that\s+(.+)` -> Direct fact storage with high confidence

### Priority 6: Fact Decay and Pruning
**Action:** Implement forgetting for contradicted/old facts

```python
def decay_facts(self, days_threshold=30):
    """Reduce confidence of unconfirmed facts."""
    self.conn.execute("""
        UPDATE user_facts
        SET confidence = confidence * 0.95
        WHERE last_confirmed < datetime('now', ? || ' days')
        AND confirmation_count < 3
    """, (-days_threshold,))
```

---

## 6. Storage Locations Summary

| Component | Path | Size |
|-----------|------|------|
| Main Memory DB | /Volumes/David External/sam_memory/memory.db | 61KB |
| Intelligence Core | /Volumes/David External/sam_memory/intelligence_core.db | 45KB |
| Feedback DB | /Volumes/David External/sam_memory/feedback.db | 86KB |
| Procedural DB | /Volumes/David External/sam_memory/procedural.db | 24KB |
| Decay DB | /Volumes/David External/sam_memory/decay.db | 16KB |
| Semantic Embeddings | sam_brain/memory/embeddings.json | 22KB |
| Semantic Index | sam_brain/memory/index.npy | 5KB |

**Total External Storage:** ~232KB active databases

---

## 7. Recommendations for Phase 1.3.2

### Immediate Actions
1. **Choose primary fact store** - Recommend `intelligence_core.db/user_facts`
2. **Add startup fact loading** to `ConversationMemory.__init__`
3. **Wire `_extract_facts` to use user_facts table** instead of local facts table
4. **Add explicit "remember" command handler**

### Medium-Term Actions
5. **Implement semantic fact deduplication** using embeddings
6. **Add contradiction detection** using cosine similarity
7. **Integrate semantic_memory.search() into context building**
8. **Add fact confirmation prompts** ("You mentioned X before - still true?")

### Long-Term Actions
9. **Unified FactManager class** bridging all stores
10. **Periodic fact consolidation** merging duplicates
11. **User-facing fact review interface** ("What do you know about me?")
12. **Export/import for backup**

---

## 8. Code Files to Modify

| File | Changes Needed |
|------|----------------|
| `conversation_memory.py` | Add startup loading, unified fact storage |
| `sam_intelligence.py` | Add fact query API, deduplication |
| `semantic_memory.py` | Add fact-specific entry type, auto-chunking |
| `cognitive/unified_orchestrator.py` | Wire fact loading into context |
| `sam_api.py` | Add `/facts` endpoint for debugging |

---

## 9. Testing Commands

```bash
# Check current facts in memory.db
sqlite3 /Volumes/David\ External/sam_memory/memory.db "SELECT * FROM facts;"

# Check user_facts in intelligence_core.db
sqlite3 /Volumes/David\ External/sam_memory/intelligence_core.db "SELECT * FROM user_facts;"

# Run memory stats
python3 /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/conversation_memory.py stats

# Check semantic memory
python3 /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py stats
```

---

## 10. Conclusion

SAM's memory architecture has all the necessary components but they're isolated silos. The path forward is:

1. **Unify** - Single authoritative fact store
2. **Wire** - Connect extraction to storage to retrieval
3. **Load** - Automatic fact loading at session start
4. **Validate** - Confirmation and contradiction detection

The infrastructure is solid. It needs integration, not rebuilding.

---

*Audit completed by Claude Code - Phase 1.3.1*
