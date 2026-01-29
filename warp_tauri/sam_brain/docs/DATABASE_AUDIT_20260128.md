# SAM Brain Audit - 2026-01-28

## AUDIT 1: Active Token Budget System

### The Three Competing Systems

| System | File | Purpose |
|--------|------|---------|
| `ContextBudget` | `context_budget.py` (root) | RAG-aware budget allocator with query-type detection, section priorities, and attention-curve ordering |
| `TokenBudgetManager` | `cognitive/token_budget.py` | Simpler budget for cognitive engine (512 for 1.5B, 256 for 3B) with presets |
| `ContextManager` | `context_manager.py` (root) | Context window manager with rolling summarization; internally imports `ContextBudget` from `context_budget.py` |

### Active Code Path Trace

```
sam_api.py::api_orchestrate()
  -> escalation_handler.py::process_request()      [primary path]
     -> cognitive.unified_orchestrator::CognitiveOrchestrator.process()
        -> CognitiveOrchestrator._build_context()   <-- THIS IS THE ACTIVE BUDGET SYSTEM

  -> orchestrator.py::orchestrate()                 [fallback if escalation_handler ImportError]
     -> MLXCognitiveEngine (no budget system)
```

### Verdict: NONE of the three budget files are active

The **CognitiveOrchestrator** in `cognitive/unified_orchestrator.py` implements its own **inline hardcoded token budgets** as class constants:

```python
# cognitive/unified_orchestrator.py lines 357-364
MAX_CONTEXT_TOKENS = 512
SYSTEM_PROMPT_TOKENS = 80
PROJECT_CONTEXT_TOKENS = 100
RETRIEVAL_TOKENS = 150
HISTORY_TOKENS = 200
QUERY_TOKENS = 62
RESERVE_TOKENS = 20
```

It does **not** import or use any of the three competing budget systems. It uses its own `_build_context()` method (line 1037) which applies these hardcoded values directly via `self.compressor.compress(text, target_tokens=X)`.

### Where are the three budget files actually used?

| File | Imported By | Status |
|------|-------------|--------|
| `context_budget.py` | `context_manager.py` (conditional), `sam_api.py` line 1475 (stats-only, in `api_compression_stats()`), test files only | **DEAD CODE** in active path |
| `cognitive/token_budget.py` | `cognitive/__init__.py` (exported), test files (`test_cognitive_system.py`) | **DEAD CODE** - exported but never imported by any active module |
| `context_manager.py` | Nothing imports it | **DEAD CODE** - completely orphaned |

### Recommendation

The active budget logic lives inline in `cognitive/unified_orchestrator.py` lines 357-364 and 1037-1132. The three standalone budget files (`context_budget.py`, `context_manager.py`, `cognitive/token_budget.py`) are all dead code -- candidates for cleanup or future integration.

---

## AUDIT 2: Duplicate Database Pairs

### Database Inventory

All databases reside on external storage at `/Volumes/David External/sam_memory/`.

#### Root level (`sam_memory/`) -- 15 databases

| Database | Size | Last Modified |
|----------|------|---------------|
| active_learning.db | 24 KB | Jan 24 17:25 |
| cache.db | 20 KB | Jan 24 17:25 |
| code_index.db | 8,729 KB | Jan 24 22:39 |
| decay.db | 16 KB | Jan 24 17:24 |
| facts.db | 68 KB | Jan 25 03:55 |
| feedback.db | 84 KB | Jan 24 17:24 |
| goals.db | 16 KB | Jan 24 17:24 |
| intelligence_core.db | 44 KB | Jan 24 17:24 |
| memory.db | 60 KB | Jan 24 17:24 |
| metacognition.db | 16 KB | Jan 24 17:24 |
| procedural.db | 24 KB | Jan 24 17:24 |
| project_context.db | 32 KB | Jan 24 17:24 |
| project_sessions.db | 24 KB | Jan 24 18:12 |
| rag_feedback.db | 80 KB | Jan 24 22:40 |
| relationships.db | 20 KB | Jan 24 17:24 |

#### Cognitive subdirectory (`sam_memory/cognitive/`) -- 7 databases

| Database | Size | Last Modified |
|----------|------|---------------|
| active_learning.db | 60 KB | Jan 25 08:40 |
| cache.db | 20 KB | Jan 25 08:40 |
| decay.db | 16 KB | Jan 25 08:40 |
| goals.db | 16 KB | Jan 25 08:40 |
| metacognition.db | 16 KB | Jan 25 08:40 |
| procedural.db | 24 KB | Jan 25 08:40 |
| relationships.db | 28 KB | Jan 25 08:40 |

### The 7 Duplicate Pairs

#### How duplicates were created

Each cognitive module (e.g., `enhanced_learning.py`, `enhanced_memory.py`, `cognitive_control.py`, `emotional_model.py`) has **two constructors**:

1. **Individual class init** -- default path is the root `sam_memory/` directory:
   ```python
   class ActiveLearner:
       def __init__(self, db_path="/Volumes/David External/sam_memory/active_learning.db"):
   ```

2. **Composite class init** -- passes in a base `db_path` and appends the filename:
   ```python
   class EnhancedLearningSystem:
       def __init__(self, db_path="/Volumes/David External/sam_memory"):
           self.active_learner = ActiveLearner(f"{db_path}/active_learning.db")
   ```

When the `CognitiveOrchestrator` is instantiated with `db_path="/Volumes/David External/sam_memory/cognitive"` (as done in both `sam_api.py` line 1343 and `escalation_handler.py` line 36), the composite classes create databases in the `cognitive/` subdirectory. The root-level databases were created earlier when modules were used with default paths or tested standalone.

#### Pair-by-pair analysis

##### 1. active_learning.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 24 KB | Jan 24 17:25 | `cognitive/enhanced_learning.py::ActiveLearner` (default path) |
| `sam_memory/cognitive/` | 60 KB | Jan 25 08:40 | Same class, called via `CognitiveOrchestrator` with cognitive/ base path |

**Authoritative: `sam_memory/cognitive/active_learning.db`** -- Larger (60 KB vs 24 KB), more recently modified (Jan 25 vs Jan 24). This is the copy written by the active `CognitiveOrchestrator` code path.

##### 2. cache.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 20 KB | Jan 24 17:25 | `cognitive/enhanced_learning.py::PredictiveCache` (default path) |
| `sam_memory/cognitive/` | 20 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/cache.db`** -- Same size but more recently modified. Active code path writes here.

##### 3. decay.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 16 KB | Jan 24 17:24 | `cognitive/enhanced_memory.py::DecayingMemory` (default path) |
| `sam_memory/cognitive/` | 16 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/decay.db`** -- Same size, more recently touched. Active code path.

##### 4. goals.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 16 KB | Jan 24 17:24 | `cognitive/cognitive_control.py::GoalManager` (default path) |
| `sam_memory/cognitive/` | 16 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/goals.db`** -- Same size, more recent. Active code path.

##### 5. metacognition.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 16 KB | Jan 24 17:24 | `cognitive/cognitive_control.py::MetaCognition` (default path) |
| `sam_memory/cognitive/` | 16 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/metacognition.db`** -- Same size, more recent. Active code path.

##### 6. procedural.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 24 KB | Jan 24 17:24 | `cognitive/enhanced_memory.py::ProceduralMemory` (default path) |
| `sam_memory/cognitive/` | 24 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/procedural.db`** -- Same size, more recent. Active code path.

##### 7. relationships.db

| Location | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| `sam_memory/` | 20 KB | Jan 24 17:24 | `cognitive/emotional_model.py::RelationshipTracker` (default path) |
| `sam_memory/cognitive/` | 28 KB | Jan 25 08:40 | Same class, via `CognitiveOrchestrator` |

**Authoritative: `sam_memory/cognitive/relationships.db`** -- Larger (28 KB vs 20 KB), more recent. Active code path writes here.

### Root-only databases (no duplicate)

These 8 databases exist only at the root `sam_memory/` level and have no duplicate in `cognitive/`:

| Database | Size | Modified | Writer Module |
|----------|------|----------|---------------|
| code_index.db | 8,729 KB | Jan 24 22:39 | `cognitive/code_indexer.py` and `code_indexer.py` (hardcoded root path) |
| facts.db | 68 KB | Jan 25 03:55 | `fact_memory.py` (hardcoded root path) |
| feedback.db | 84 KB | Jan 24 17:24 | `feedback_system.py` (hardcoded root path) |
| intelligence_core.db | 44 KB | Jan 24 17:24 | `intelligence_core.py` (hardcoded root path) |
| memory.db | 60 KB | Jan 24 17:24 | `conversation_memory.py` and `cognitive/enhanced_retrieval.py` |
| project_context.db | 32 KB | Jan 24 17:24 | `project_context.py` (hardcoded root path) |
| project_sessions.db | 24 KB | Jan 24 18:12 | `project_context.py` (hardcoded root path) |
| rag_feedback.db | 80 KB | Jan 24 22:40 | `rag_feedback.py` (hardcoded root path) |

### Root Cause

The duplication happened because the cognitive modules define **default paths pointing to `sam_memory/`** in their individual class constructors, but the **`CognitiveOrchestrator` passes `sam_memory/cognitive/`** as the base path. Both were used at different times -- individually during development/testing (creating root-level DBs) and via the orchestrator in production (creating cognitive/ DBs).

### Summary

- **All 7 duplicated databases are authoritative in `sam_memory/cognitive/`** -- this is where the active code path (via `CognitiveOrchestrator`) writes.
- The **root-level copies are stale** (last modified Jan 24 vs Jan 25 for cognitive/).
- The 8 root-only databases are correctly placed -- their writer modules hardcode the root path and are not routed through the orchestrator's `db_path` parameter.
- **No data loss risk**: The root copies appear to be from initial setup or testing. The cognitive/ copies are the ones accumulating real data.
