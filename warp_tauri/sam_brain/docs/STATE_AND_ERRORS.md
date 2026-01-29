# SAM Brain: State Management and Error Handling Analysis

*Generated: 2026-01-29*

---

## Part 1: State Management

### 1.1 Singletons (Thread-Safe)

Four classes use the classic `__new__` + `_lock` singleton pattern:

| Class | File | Thread-Safe Lock |
|-------|------|-----------------|
| `AutoCoordinator` | `auto_coordinator.py:55-64` | `threading.Lock()` with double-check |
| `ResourceManager` | `cognitive/resource_manager.py:323-333` | `threading.Lock()` with double-check |
| `VoiceSettingsManager` | `voice/voice_settings.py:330-344` | `threading.Lock()` via `get_instance()` classmethod |
| `FactMemory` | `memory/fact_memory.py:1924-1932` | **NOT thread-safe** - simple `global` without lock |

**Risk**: `FactMemory`'s `get_fact_db()` is a module-level global singleton without any thread lock. In a multi-threaded context (e.g., the API server), two threads could simultaneously create separate instances. Since it wraps SQLite, the worst case is two connections to the same DB, but it wastes memory.

### 1.2 Module-Level Global Singletons (Lazy-Loaded via `global`)

These use the `global _variable` + `get_X()` function pattern. **None are thread-safe** -- all rely on single-threaded initialization:

| Variable | File | Getter Function |
|----------|------|----------------|
| `_memory` | `memory/semantic_memory.py:453` | `get_memory()` |
| `_fact_db_instance` | `memory/fact_memory.py:1924` | `get_fact_db()` |
| `_selector` | `cognitive/vision_selector.py` | `get_selector()` |
| `_miner` | `cognitive/code_pattern_miner.py` | `get_miner()` |
| `_doc_indexer` | `cognitive/doc_indexer.py` | `get_doc_indexer()` |
| `_preprocessor` | `cognitive/image_preprocessor.py` | `get_preprocessor()` |
| `_framework` | `cognitive/planning_framework.py` | `get_framework()` |
| `_code_indexer` | `cognitive/code_indexer.py` | `get_code_indexer()` |
| `_router` | `cognitive/smart_vision.py` | `get_router()` |
| `_rag_feedback_tracker` | `memory/rag_feedback.py` | `get_tracker()` |
| `_importance_scorer` | `memory/context_budget.py` | `get_scorer()` |
| `_adaptive_manager` | `memory/context_budget.py` | `get_manager()` |
| `_session_recall` | `memory/project_context.py:1022` | `get_session_recall()` |
| `_profile_loader` | `memory/project_context.py:1556` | `get_profile_loader()` |
| `_project_watcher` | `memory/project_context.py:1880` | `get_watcher()` |
| `_session_state` | `memory/project_context.py:2465` | `get_session_state()` |
| `_project_context` | `memory/project_context.py:2881` | `get_project_context()` |
| `_training_store` | `training_data.py:1110` | `get_store()` |
| `_auto_coord` | `auto_coordinator.py:323` | `get_coordinator()` |
| `_sync` | `ssot_sync.py:629` | `get_sync()` |
| `_approval_queue` | `approval_queue.py:851` | `get_approval_queue()` |

**Count: 21 module-level singletons**, none with thread-safe initialization.

### 1.3 Module-Level Instantiated Globals (Orchestrator)

`orchestrator.py` creates module-level instances eagerly via `try/except ImportError`:

| Variable | Type | Line |
|----------|------|------|
| `MLX_ENGINE` | `MLXCognitiveEngine` | 23 |
| `IMPACT_TRACKER` | `ImpactTracker` | 33 |
| `PRIVACY_GUARD` | `PrivacyGuard` | 40 |
| `TRANSPARENCY_GUARD` | `TransparencyGuard` | 66 |
| `THOUGHT_LOGGER` | `ThoughtLogger` | 73 |
| `CONVERSATION_LOGGER` | `ConversationLogger` | 80 |
| `DASHBOARD_GENERATOR` | `DashboardGenerator` | 94 |
| `DATA_ARSENAL` | `DataArsenal` | 101 |
| `TERMINAL_COORD` | `TerminalCoordinator` | 108 |
| `AUTO_COORD` | auto_coordinator | 115 |
| `COORDINATED` | `CoordinatedSession` | 116 |

Each has an `_AVAILABLE` boolean flag set based on import success. If any import fails, the feature degrades gracefully to `None` checks.

**Pattern**: Each is wrapped in `try/except ImportError` to allow optional dependencies.

### 1.4 Module-Level Globals in sam_enhanced.py

Five lazy-loaded globals with `False` as sentinel for "failed to load":

```python
_semantic_memory = None   # -> get_semantic_memory()
_multi_agent = None       # -> get_multi_agent()
_ssot_sync = None         # -> get_ssot()
_favorites = None         # -> get_favorites()
_voice = None             # -> get_voice()
```

Uses `False` as sentinel: if import fails, sets to `False` so subsequent calls return `None` without retrying. This is a **smart pattern** -- avoids repeated import failures.

### 1.5 MLX Model State

| Variable | File | Purpose |
|----------|------|---------|
| `_mlx_available` | `cognitive/mlx_cognitive.py:25` | Lazy-loaded MLX availability flag |
| `_load`, `_generate` | `cognitive/mlx_cognitive.py:26-27` | Lazy-loaded MLX functions |
| `_mlx_model`, `_mlx_tokenizer` | `memory/semantic_memory.py:31-32` | Cached embedding model |
| `_mlx_model`, `_mlx_tokenizer` | `cognitive/doc_indexer.py:473` | Cached embedding model (separate instance) |
| `_cached_models` | `mlx_inference.py:35` | Dict cache of loaded models by mode |
| `_current_mode` | `mlx_inference.py:34` | Current inference mode string |

**Risk**: `_mlx_model`/`_mlx_tokenizer` exist independently in both `semantic_memory.py` and `doc_indexer.py`. If both are loaded simultaneously, two copies of MiniLM-L6-v2 occupy memory (~90MB each). On 8GB RAM this matters.

### 1.6 Threading Locks

| Lock | File | Purpose |
|------|------|---------|
| `AutoCoordinator._lock` | `auto_coordinator.py:56` | Singleton creation |
| `ApprovalQueue._lock` | `approval_queue.py:296` | DB operations (RLock - reentrant) |
| `_queue_lock` | `approval_queue.py:842` | Global queue creation |
| `ResourceManager._lock` | `cognitive/resource_manager.py:324` | Singleton creation |
| `ResourceManager._ops_lock` | `cognitive/resource_manager.py:342` | Heavy operation serialization |
| `ResourceManager._vision_lock` | `cognitive/resource_manager.py:357` | Vision model lifecycle |
| `ResourceManager._voice_lock` | `cognitive/resource_manager.py:363` | Voice model lifecycle |
| `MLXCognitiveEngine._model_lock` | `cognitive/mlx_cognitive.py:153` | Model swap protection |
| `EnhancedMemoryManager._lock` | `cognitive/enhanced_memory.py:101` | Memory operations |
| `CognitiveControl._lock` | `cognitive/cognitive_control.py:409` | Meta-cognition state |
| `VisionEngine._lock` | `cognitive/vision_engine.py:229` | Vision processing |
| `VoiceSettingsManager._lock` | `voice/voice_settings.py:331` | Singleton + file I/O |
| `ModelEvaluation._test_lock` | `cognitive/model_evaluation.py:1373` | Test execution |
| `AutoLearner.training_lock` | `auto_learner.py:531` | Training exclusion |
| `AutoLearner.process_lock` | `auto_learner.py:689` | Process exclusion |
| `ProjectWatcher._lock` | `memory/project_context.py:1621` | File watching |
| `TrainingScheduler._lock` | `training_scheduler.py:123` | Job scheduling |
| `ModelDeployment._lock` | `model_deployment.py:153,245` | Deployment operations |
| `model_lock` | `vision_server.py:31` | Global model access |

**Total: 19 locks across the codebase.** The `ResourceManager` is the most lock-heavy with 4 locks for different subsystems.

### 1.7 Background Threads

| Thread(s) | File | Purpose |
|-----------|------|---------|
| Heartbeat thread | `auto_coordinator.py:178` | Terminal heartbeat (daemon) |
| 15 worker threads | `perpetual_learner.py:539-557` | Scraping, training, reporting (all daemon) |
| Consolidation thread | `cognitive/enhanced_learning.py:477` | Memory consolidation (daemon) |
| File watcher thread | `memory/project_context.py:1656` | Project file monitoring (daemon) |
| Processing thread | `conversation_engine/engine.py:135` | Conversation processing |

The `perpetual_learner.py` spawns **15 daemon threads** simultaneously (staggered by 0.5s), each running an infinite loop for different data sources.

### 1.8 What Persists Across Restarts vs What Is Lost

#### PERSISTS (SQLite databases):

| Database | Path | Content |
|----------|------|---------|
| Terminal sessions | `~/.sam/terminal_sessions.db` | Session history, context transfers |
| Terminal coordination | `~/.sam/terminal_coordination.db` | Multi-terminal state |
| Approval queue | `~/.sam/approval_queue.db` | Pending/completed approvals |
| Emotional model | External path configurable | Mood state, relationship history |
| Facts | `/Volumes/David External/sam_memory/facts.db` (fallback `~/.sam/facts.db`) | Learned facts with confidence scores |
| RAG feedback | `/Volumes/David External/sam_memory/rag_feedback.db` | Retrieval quality metrics |
| Project context | `/Volumes/David External/sam_memory/project_context.db` | Project detection, profiles |
| Project sessions | `/Volumes/David External/sam_memory/project_sessions.db` | Session recall data |
| Vision selector | `~/.sam/vision_selector.db` | Vision tier usage stats |
| Vision memory | `~/.sam/vision_memory.db` | Smart vision routing data |
| Code patterns | `/Volumes/#1/SAM/training_data/code_patterns/patterns.db` | Mined code patterns |
| Impact tracker | `~/.sam/impact_tracker.db` | Environmental monitoring |
| Execution log | `~/.sam/execution_log.jsonl` | Command execution audit trail |

#### PERSISTS (JSON files):

| File | Path | Content |
|------|------|---------|
| Voice settings | `~/.sam/voice_settings.json` | Voice configuration |
| Semantic memory | `sam_brain/memory/embeddings.json` + `index.npy` | Vector embeddings |
| Projects registry | `sam_brain/projects.json` | Project definitions |
| User memory | `~/.sam_memory.json` | Legacy user memory |
| SSOT sync state | `sam_brain/.ssot_sync_state.json` | Last sync timestamps |
| Training stats | `sam_brain/stats.json` | Training statistics |
| Backups | `~/.sam/backups/` | File modification rollbacks |

#### LOST ON RESTART (in-memory only):

| State | File | Content Lost |
|-------|------|-------------|
| MLX model cache | `mlx_inference.py:_cached_models` | Loaded model weights (must reload ~2-4s) |
| MLX embedding model | `semantic_memory.py:_mlx_model` | Must reload on first query |
| Working memory | `cognitive/enhanced_memory.py` | Short-term context, decay states |
| Cognitive control | `cognitive/cognitive_control.py` | Current goals, reasoning state |
| Generation statistics | `cognitive/mlx_cognitive.py:156-159` | Token counts, escalation counts |
| Conversation state | `conversation_engine/state.py` | Current turn, emotion trajectory |
| Resource levels | `cognitive/resource_manager.py` | RAM/swap monitoring state |
| All 21 module singletons | Various | Must re-initialize on restart |
| Perpetual learner state | `perpetual_learner.py` | Thread states, queues (partially saved via `_save_state()`) |
| Daemon service states | `unified_daemon.py` | Process status tracking |
| Heartbeat/coordination | `auto_coordinator.py` | Terminal awareness (DB persists but active sessions lost) |
| Prompt cache | `cognitive/mlx_optimized.py` | KV-cache for conversation continuity |

### 1.9 State Sharing Between Processes

SAM uses **SQLite as IPC** -- no direct shared memory or pipes between processes:

1. **Terminal coordination** (`~/.sam/terminal_coordination.db`): Multiple Claude Code terminals + SAM daemon share state via SQLite. Each terminal reads/writes sessions, tasks, and heartbeats. SQLite's WAL mode handles concurrent access.

2. **Approval queue** (`~/.sam/approval_queue.db`): SAM proposes actions, David approves/rejects via separate process. Thread-safe with `threading.RLock` and SQLite `timeout=30.0`.

3. **JSON file bridges**: `~/.sam_chatgpt_queue.json` and `~/.sam_claude_queue.json` serve as inter-process message queues (read by `orchestrator.py`, written by external tools). **No file locking** -- relies on atomic write semantics of small files.

4. **HTTP API** (`sam_api.py` on port 8765): Primary inter-process communication for Tauri frontend. State passed via JSON request/response.

5. **Vision server** (`vision_server.py` on port 8766): Separate process for persistent vision model serving, communicates via HTTP with main SAM process.

**Risk**: The JSON file bridges (`~/.sam_chatgpt_queue.json`, `~/.sam_claude_queue.json`) have no file-level locking. If two processes write simultaneously, data corruption is possible.

---

## Part 2: Error Handling

### 2.1 Overall Statistics

| Pattern | Count |
|---------|-------|
| Total `except` clauses (non-test, non-archive) | ~940 |
| **Bare `except:` clauses** | **138** |
| `except Exception` clauses | 488 |
| Specific exception types (KeyError, ValueError, etc.) | 148 |
| `raise` statements (re-raise or new) | 57 |
| `logging.error/warning/exception` calls | 69 |
| `print(...error/fail...)` calls | 211 |

**Key finding**: Only ~7% of exceptions are properly logged via `logging`. The vast majority use `print()` for error reporting, which means errors are lost if stdout is not captured. The 138 bare `except:` clauses are a significant code quality concern.

### 2.2 Bare `except:` Clauses (Bad Practice)

**138 bare `except:` clauses** across the codebase. The worst offenders:

| File | Count | Typical Pattern |
|------|-------|----------------|
| `perpetual_learner.py` | 14 | All scraper threads -- `except: continue` |
| `feedback_system.py` | 10 | Data processing loops |
| `claude_learning.py` | 5 | Session parsing |
| `unified_daemon.py` | 5 | Service management |
| `cognitive/vision_client.py` | 4 | Vision processing fallbacks |
| `system_orchestrator.py` | 4 | Scraper/service management |
| `deduplication.py` | 1 | Dedup processing |
| `cognitive/mlx_cognitive.py` | 1 | Model operations |
| `cognitive/smart_vision.py` | 2 | Vision routing |
| `memory/infinite_context.py` | 2 | Context management |
| `memory/semantic_memory.py` | 1 | JSONL import |
| `sam_enhanced.py` | 2 | Enhanced features |
| `sam_chat.py` | 2 | Chat interface |
| `multi_agent.py` | 1 | Agent orchestration |
| `claude_orchestrator.py` | 1 | Orchestration |
| `parity_system.py` | 2 | Parity checking |
| `doc_ingestion.py` | 1 | Document ingestion |
| `training_pipeline.py` | 1 | Training |
| `emotion2vec_mlx/detector.py` | 1 | Emotion detection |

These catch `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` in addition to regular exceptions, which can prevent clean process shutdown.

### 2.3 Silently Swallowed Exceptions

The most concerning patterns where exceptions are caught and silently discarded:

#### Pattern 1: `except: pass` (complete silence)
```python
# system_orchestrator.py:411, 421
# cognitive/vision_client.py:506, 576, 635
# cognitive/mlx_cognitive.py:813
# unified_daemon.py:206, 376, 394
# memory/infinite_context.py:674
# memory/semantic_memory.py:447
# sam_enhanced.py:176, 385
# deduplication.py:1039
```

#### Pattern 2: `except: continue` (loop continues silently)
```python
# perpetual_learner.py:744, 757, 771, 900, 937, 1386, 1414
# claude_learning.py:461, 482, 685
# feedback_system.py:3356
```

#### Pattern 3: `except Exception: return None/[]/{}/False` (silent degradation)
```python
# cognitive/vision_selector.py:705  -> return False
# cognitive/code_pattern_miner.py:899 -> return None
# cognitive/unified_orchestrator.py:526 -> return ""
# cognitive/enhanced_retrieval.py:745 -> return []
# memory/context_budget.py:1435 -> return None
# memory/project_context.py:1254 -> return None
# perpetual_learner.py:480 -> return {}
```

**Total silent swallows: ~80+ locations** where errors vanish without any logging.

### 2.4 Error Propagation Patterns

#### Pattern A: "Graceful Degradation" (dominant pattern)
Most of the codebase follows a pattern where optional features fail silently:

```python
# orchestrator.py - repeated 12+ times
try:
    from some_module import SomeClass
    SOME_FEATURE = SomeClass()
except ImportError:
    SOME_FEATURE = None
```

Then at call sites:
```python
if SOME_FEATURE:
    SOME_FEATURE.do_thing()
# else: silently skip
```

This is intentional -- SAM is designed to run with missing optional dependencies. However, it means import-time errors in cognitive modules (typos, missing files) will silently disable features with no indication.

#### Pattern B: "Log and Return Default" (memory/cognitive modules)
```python
try:
    result = expensive_operation()
except Exception as e:
    print(f"Error: {e}")
    return default_value
```

Used extensively in:
- `cognitive/unified_orchestrator.py` (returns `""` or `{}`)
- `memory/project_context.py` (returns `None`)
- `cognitive/enhanced_retrieval.py` (returns `[]`)

#### Pattern C: "Raise RuntimeError" (vision system)
The vision system is the **most aggressive** about raising errors:

```python
# cognitive/vision_engine.py - 10 raise statements
raise RuntimeError("mlx_vlm not available")
raise RuntimeError("Vision processing timed out")
raise RuntimeError("Vision server not running")
raise RuntimeError(f"Subprocess failed: {result.stderr}")
```

These propagate up to the caller, which is correct. The vision client (`vision_client.py`) then catches these with `except Exception as e` and logs them.

#### Pattern D: "Domain-Specific Exceptions" (execution system)
```python
# auto_coordinator.py
raise ConflictError(f"File {file_path} is being edited by ...")

# approval_queue.py
raise ValueError(f"Command blocked: {command[:100]}...")

# cognitive/image_preprocessor.py
raise FileNotFoundError(f"Image not found: {path}")
```

This is the most correct pattern, used primarily in the execution and safety subsystems.

#### Pattern E: "Global Signal Handler" (daemons)
```python
# perpetual_learner.py:1677, unified_daemon.py:647, training_scheduler.py:695
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

Daemons register signal handlers for graceful shutdown. The perpetual learner sets a global `running = False` flag. The unified daemon calls `_handle_shutdown()` which stops services in priority order.

### 2.5 Logging Infrastructure Problems

The codebase has **inconsistent error reporting**:

- **10 files use `logging` module properly**: `system_orchestrator.py`, `vision_engine.py`, `vision_selector.py`, `smart_vision.py`, `image_preprocessor.py`, `ui_awareness.py`, `resource_manager.py`, `training_prep.py`, `vision_server.py`, `training_runner.py`
- **All other files use `print()`** for error reporting (211 print-based error messages found)
- **No centralized error tracking** -- errors go to stdout/stderr and are lost unless the process output is captured
- **No structured error types** -- no custom exception hierarchy; uses `Exception`, `RuntimeError`, `ValueError` ad hoc

### 2.6 Specific High-Risk Error Locations

1. **`perpetual_learner.py`** (14 bare excepts): All 15 daemon threads swallow all exceptions with `except: continue`. A thread crash is invisible. If a thread dies from an uncaught exception *within* the bare except (e.g., MemoryError), the thread silently exits and that data source stops collecting forever.

2. **`feedback_system.py`** (10 bare excepts): Feedback processing silently drops malformed data. Lost feedback means the system cannot learn from user corrections.

3. **`unified_daemon.py`** (5 bare excepts): Service monitoring swallows errors. If a health check throws an unexpected exception type, the daemon may think a service is running when it is crashed.

4. **`cognitive/vision_client.py`** (4 bare excepts): Vision processing fallbacks catch everything. If the vision model produces corrupt output, it will be silently discarded instead of flagged.

5. **`memory/semantic_memory.py:446`**: JSONL import has `except: pass` -- corrupt training data lines are silently skipped with no count of how many were dropped.

### 2.7 Thread Safety Gaps in Error Handling

- The `ResourceManager` correctly uses locks for heavy operations, but its `_check_memory()` method (called to decide if an operation is safe) does not hold a lock, meaning two threads could simultaneously pass the memory check and both proceed, exceeding available RAM.
- `_cached_models` dict in `mlx_inference.py` is modified without locks. Concurrent model loads for different modes could cause dict corruption.
- All 21 lazy-loaded module singletons lack initialization locks. First access from two threads simultaneously could create two instances.

---

## Summary of Critical Issues

### State Management

1. **21 lazy singletons without thread-safe init** -- race condition on first access
2. **Duplicate embedding models** in `semantic_memory.py` and `doc_indexer.py` waste RAM on 8GB system
3. **JSON file IPC** (`~/.sam_chatgpt_queue.json`, `~/.sam_claude_queue.json`) has no file locking
4. **Working memory, conversation state, and KV-cache are lost on restart** with no graceful persistence
5. **15 daemon threads** in perpetual_learner with no health monitoring -- dead threads are invisible

### Error Handling

1. **138 bare `except:` clauses** catch SystemExit/KeyboardInterrupt, preventing clean shutdown
2. **~80 silently swallowed exceptions** hide real failures
3. **211 print-based errors** vs only **69 logged errors** -- most errors lost in production
4. **No custom exception hierarchy** -- difficult to distinguish expected vs unexpected failures
5. **Perpetual learner threads** silently die on unexpected errors with no restart mechanism
