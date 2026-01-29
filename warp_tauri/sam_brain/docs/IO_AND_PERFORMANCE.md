# I/O and Performance Analysis

**Analyzed:** 2026-01-29
**Scope:** All Python files in `sam_brain/` (excluding venv, tests, archive)
**Hardware Context:** M2 Mac Mini, 8GB RAM

---

## 1. FILE I/O

### 1.1 Unclosed File Handles (CRITICAL)

Multiple files use `json.load(open(...))` and `json.dump(..., open(...))` without context managers. These leave file descriptors dangling until garbage collected.

**Affected files and lines:**

| File | Pattern | Line(s) |
|------|---------|---------|
| `memory/semantic_memory.py` | `json.load(open(EMBEDDINGS_FILE))` | 65 |
| `memory/semantic_memory.py` | `json.dump(data, open(EMBEDDINGS_FILE, "w"), indent=2)` | 81 |
| `memory/semantic_memory.py` | `json.load(open(memory_file))` | 418 |
| `sam_enhanced.py` | `json.load(open(PROJECTS_FILE))` | 95 |
| `sam_enhanced.py` | `json.load(open(MEMORY_FILE))` | 174 |
| `sam_enhanced.py` | `json.dump(memory, open(MEMORY_FILE, 'w'), indent=2)` | 188 |
| `sam_enhanced.py` | `json.load(open(BRIDGE_QUEUE))` | 383 |
| `sam_enhanced.py` | `json.dump(queue, open(BRIDGE_QUEUE, 'w'), indent=2)` | 406 |
| `ssot_sync.py` | `json.load(open(SYNC_STATE_FILE))` | 68 |
| `ssot_sync.py` | `json.dump(..., open(SYNC_STATE_FILE, "w"), ...)` | 82 |
| `ssot_sync.py` | `json.load(open(memory_file))` | 165 |
| `ssot_sync.py` | `json.dump(summary, open(..., "w"), indent=2)` | 174 |
| `training_pipeline.py` | `json.load(open(self.runs_file))` | 62 |
| `training_pipeline.py` | `json.dump(data, open(self.runs_file, "w"), indent=2)` | 81 |
| `perpetual_learner.py` | `json.load(open(STATE_FILE))` | 477 |
| `perpetual_learner.py` | `json.load(open(runs_file))` | 1452 |
| `perpetual_learner.py` | `json.dump(runs, open(runs_file, 'w'), indent=2)` | 1460 |
| `claude_learning.py` | `json.load(open(conv_file))` | 91 |
| `claude_learning.py` | `json.load(open(export_file))` | 313 |
| `claude_learning.py` | `json.load(open(stats_file))` | 746 |
| `voice/voice_output.py` | `json.load(open(CONFIG_FILE))` | 55 |

**Impact:** On an 8GB system, file descriptor exhaustion can occur if many singletons are created or if data import functions like `import_from_memory_json()` or `import_from_training_data()` are called in loops. CPython's refcounting usually closes these promptly, but under memory pressure or with PyPy/alternate runtimes, this is a real leak.

**Fix pattern:**
```python
# Before (leaking):
data = json.load(open(file_path))
# After (safe):
with open(file_path) as f:
    data = json.load(f)
```

### 1.2 Large File Reads Into Memory

Several patterns read entire files into memory:

| File | What | Risk |
|------|------|------|
| `perpetual_learner.py:598` | `json.load(chatgpt_path)` for full ChatGPT export | Could be 100MB+ |
| `perpetual_learner.py:89` | `TRAINING_DATA.read_text().strip().split("\n")` | Full JSONL file in memory |
| `perpetual_learner.py:1395-1397` | Re-reads merged training file into list | Double memory usage |
| `memory/semantic_memory.py:71` | `np.load(INDEX_FILE, allow_pickle=True)` | Grows with memory entries |
| `unified_daemon.py:773` | `LOG_FILE.read_text().strip().split("\n")` | Unbounded log file |
| `training_pipeline.py:89` | `TRAINING_DATA.read_text().strip().split("\n")` | Full JSONL in memory |

**Impact:** On 8GB RAM with MLX models loaded (~1.2-2.4GB), a large ChatGPT export or accumulated training data could trigger swap thrashing.

### 1.3 File Write Patterns

Training data and logs use append-mode writes (`"a"` mode) without size rotation:

- `perpetual_learner.py:518` - Appends to `perpetual_{category}.jsonl` (unbounded)
- `perpetual_learner.py:61` - Appends to `perpetual_learner.log` (unbounded)
- `unified_daemon.py:254` - Appends to `daemon.log` (unbounded)
- `cognitive/enhanced_learning.py:592` - Appends to learning logs
- `claude_learning.py:652` - Appends to queue file

Only the unified daemon log and a few in-memory record lists have any size management (e.g., `deque(maxlen=1000)` for in-memory logs).

---

## 2. NETWORK I/O

### 2.1 HTTP Server (Blocking, Single-Threaded)

`sam_api.py` (5,658 lines) runs a `BaseHTTPRequestHandler` on port 8765. This is:

- **Single-threaded** - one request at a time
- **Synchronous** - ML inference blocks all other API requests
- **No request timeout** - a slow MLX generation blocks the entire server

The voice server (`voice/voice_server.py`) uses FastAPI/uvicorn which is async-capable -- a much better pattern.

The vision server (`vision_server.py`) also uses `BaseHTTPRequestHandler` with the same single-threaded blocking issue.

### 2.2 Outbound HTTP (Blocking, in Threads)

`perpetual_learner.py` runs 15 daemon threads making blocking HTTP requests:

| Stream Thread | Target | Method |
|---------------|--------|--------|
| `_stream_chatgpt_continuous` | Local file only | File I/O |
| `_stream_stackoverflow` | stackoverflow.com | `urllib.request.urlopen` |
| `_stream_github` | api.github.com | `urllib.request.urlopen` |
| `_stream_reddit` | old.reddit.com | `urllib.request.urlopen` |
| `_stream_apple_docs` | developer.apple.com | `urllib.request.urlopen` |
| `_stream_frida_docs` | frida.re | `urllib.request.urlopen` |
| `_stream_literotica` | literotica.com | `urllib.request.urlopen` |
| `_stream_roleplay_scraper` | nifty.org, archiveofourown.org | `urllib.request.urlopen` |
| `_stream_curriculum_learner` | localhost:8765 | `requests.post` |

All network calls use 30-second timeouts, which is appropriate. However:

- **15 threads** is excessive for an 8GB system -- thread stacks consume ~8MB each per default (~120MB total)
- No connection pooling (each request creates/tears down a fresh TCP connection)
- No retry logic with exponential backoff for transient failures
- All scrapers use `User-Agent: Mozilla/5.0` with no rate-limit tracking

### 2.3 Internal Service Communication

| Caller | Target | Pattern |
|--------|--------|---------|
| `cognitive/smart_vision.py` | `localhost:8766` | `requests.get/post` (blocking) |
| `cognitive/vision_engine.py` | `localhost:8766` | `requests.get/post` (blocking) |
| `system_orchestrator.py` | Various localhost ports | `requests.get` (blocking) |
| `perpetual_learner.py` | `localhost:8765` | `requests.post` (blocking, 120s timeout) |
| `comfyui_client.py` | `127.0.0.1:8188` | `urllib.request` (blocking) |

All inter-service calls are synchronous/blocking. When the SAM API server is busy with ML inference, curriculum learner requests to localhost:8765 will block for up to 120 seconds.

---

## 3. DATABASE I/O

### 3.1 SQLite Connection Management

There are two patterns in the codebase:

**Pattern A -- Context Manager (GOOD):**
`terminal_sessions.py` consistently uses `with sqlite3.connect(self.db_path) as conn:` across all 20+ methods.

**Pattern B -- Manual connect/close (LEAK RISK):**

| File | Occurrences | Issue |
|------|-------------|-------|
| `cognitive/enhanced_memory.py` | ~15 methods | `conn = sqlite3.connect(...)` then `conn.close()` in finally blocks -- but some methods lack try/finally |
| `cognitive/emotional_model.py` | 4 methods | Manual connect, close at end -- exception could skip close |
| `cognitive/doc_indexer.py` | 6 methods | Manual connect/close |
| `cognitive/cognitive_control.py` | 3 methods | Manual connect/close |
| `cognitive/enhanced_retrieval.py` | 1 method | Manual connect/close |
| `perpetual_learner.py` (CurriculumManager) | 8 methods | Uses try/finally in `add_task` but manual close elsewhere |
| `auto_learner.py` (AutoLearningDB) | 8 methods | Manual connect/close in every method |
| `knowledge_distillation.py` | Multiple | Manual connect/close |
| `feedback_system.py` | Multiple | Manual connect/close |

**Impact:** If an exception occurs between `sqlite3.connect()` and `conn.close()`, the connection leaks. SQLite has a process-level limit (typically 1024 file descriptors). Under sustained error conditions, this could exhaust available connections.

### 3.2 Connection-Per-Call Pattern

Every SQLite method opens a new connection, executes one query, and closes it. For example, `CurriculumManager.get_next_task()`, `get_pending_count()`, `mark_attempted()`, `mark_learned()` each open/close a connection independently. This is safe for correctness but introduces overhead:

- **Connection setup cost:** ~0.5-1ms per call (SQLite on SSD)
- **No connection pooling:** No reuse across rapid-fire calls
- **WAL mode not set:** Default journal mode means writes block reads

### 3.3 Database File Locations

| Database | Path | Notes |
|----------|------|-------|
| `auto_learning.db` | Internal SSD (`sam_brain/`) | Grows with sessions |
| `evolution.db` | Internal SSD (`sam_brain/`) | Evolution tracking |
| `curriculum.db` | External drive (`/Volumes/David External/sam_learning/`) | Good -- on external |
| `distillation.db` | External drive (with local fallback) | Good fallback pattern |
| `feedback.db` | External drive (with local fallback) | Good fallback pattern |
| `embeddings.json` + `index.npy` | Internal SSD (`sam_brain/memory/`) | Grows with memories |

`auto_learning.db` on the internal SSD violates the storage rule. It should be on `/Volumes/David External/`.

---

## 4. BLOCKING vs ASYNC

### 4.1 Entirely Synchronous Architecture

The codebase has **zero** async/await usage in production code. The only `async def` / `asyncio` references are in:
- Example strings in `perpetual_learner.py` (synthetic training data)
- Pattern detection in `cognitive/learning_strategy.py`
- `multi_agent.py` imports `asyncio` but it is unclear if it is used in production

**Consequence:** Every operation blocks the calling thread:
1. ML inference (1-60 seconds) blocks the HTTP server
2. Web scraping (up to 30s per request) blocks scraper threads
3. SQLite queries block their callers
4. Training runs (subprocess, up to 1 hour) block the training scheduler thread

### 4.2 Thread-Based Concurrency

Threading is used extensively:
- `perpetual_learner.py`: 15 daemon threads
- `unified_daemon.py`: Main loop with timed checks
- `cognitive/mlx_cognitive.py`: `threading.Lock()` for model loading
- `cognitive/resource_manager.py`: `threading.Semaphore`, `threading.Timer`, multiple locks

The `ResourceManager` correctly uses a semaphore to limit concurrent heavy operations to 1, preventing parallel model loads from OOMing the system.

---

## 5. RESOURCE CLEANUP

### 5.1 Model Unloading

`MLXCognitiveEngine.unload_model()` properly:
- Clears model references under lock
- Calls `gc.collect()`
- Clears MLX metal cache with `mx.metal.clear_cache()`

Vision models have auto-unload timers (300s inactivity), managed by `ResourceManager._schedule_auto_unload()`.

**Gap:** No auto-unload for the main LLM model. If the system goes idle, the 1.2-2.4GB model stays resident indefinitely.

### 5.2 Process Cleanup

`unified_daemon.py` has robust process cleanup:
- Terminates children before parent
- Uses `psutil.wait_procs()` with 3-second timeout
- Force-kills survivors
- Cleans PID files
- Orphan detection via command-line pattern matching

### 5.3 Audio Buffer Growth

`voice/voice_pipeline.py:289` trims the audio buffer:
```python
if len(self._audio_buffer) > 30:
    self._audio_buffer = self._audio_buffer[-20:]
```
This is adequate for short sessions but the buffer list can still grow to 30 x chunk_size numpy arrays before trimming. At 16kHz with 100ms chunks (1600 samples x 4 bytes = 6.4KB each), this is only ~192KB, which is fine.

### 5.4 Hash Set Growth

`perpetual_learner.py` maintains a deduplication set:
- `MAX_DEDUP_HASHES = 10000`
- LRU pruning in `_save_state()`
- Both set and list maintained (set for O(1) lookup, list for ordering)

This is well-bounded.

---

## 6. PERFORMANCE ANALYSIS

### 6.1 Expensive Operations

| Operation | File | Cost | Frequency |
|-----------|------|------|-----------|
| MLX model load | `mlx_cognitive.py:460-483` | 2-10s, 1.2-2.4GB RAM | On model switch |
| MLX inference | `mlx_cognitive.py:240-246` | 1-60s depending on tokens | Every request |
| Vision model load (nanoLLaVA) | `vision_engine.py` | 5-15s, 1.5GB RAM | On vision request |
| Embedding generation | `semantic_memory.py:87-111` | ~10ms per text | Every memory add/search |
| Training run | `perpetual_learner.py:1431-1441` | Up to 1 hour | Every 500 examples or 6 hours |
| ChatGPT export parse | `perpetual_learner.py:598-600` | Seconds, 100MB+ RAM | Every 30 minutes |
| Codebase scan (rglob) | `perpetual_learner.py:728` | Seconds to minutes | Every hour |

### 6.2 Nested Loops Over Large Collections

**`perpetual_learner.py:601-628` -- ChatGPT mining:**
```
for conv in conversations:           # O(conversations)
    for node in mapping.values():    # O(messages per conv)
        ...
    for domain, keywords in domains: # O(7 domains)
        for i in range(messages):    # O(messages)
```
Total: O(conversations x messages x domains). For a large ChatGPT export with 1000+ conversations, this is significant.

**`memory/semantic_memory.py:350-371` -- Search:**
```
for entry_id, entry in self.entries.items():  # O(all entries)
    if entry_id not in self.embeddings:       # O(1)
    similarity = np.dot(...)                  # O(384) - embedding dimension
```
Linear scan over all entries for every search. For large memory stores (10K+ entries), this becomes a bottleneck. No indexing structure (no FAISS, no annoy, no ball tree).

**`cognitive/mlx_cognitive.py:441-458` -- Regex patterns in model selection:**
Runs 3 reasoning patterns + 3 simple patterns as regex against every prompt. The regexes are simple, so this is O(1) per prompt effectively.

### 6.3 Repeated Expensive Computations

**Resource checks via subprocess:**
`ResourceManager.get_memory_info()` runs `vm_stat` and `sysctl` as subprocesses every time it is called. This method is called from:
- `get_resource_level()` (called for every inference request)
- `get_snapshot()` (called for status endpoints)
- `can_perform_heavy_operation()` (called before every heavy op)
- `can_load_vision_model()` (called for vision tier decisions)
- `get_voice_status()`, `can_use_quality_voice()`, `should_use_voice_fallback()`, `get_recommended_voice_tier()`

A single API request may call `get_memory_info()` 3-5 times, each spawning 2 subprocesses. At 30 requests/minute, that is 180-300 subprocess spawns per minute just for memory checks.

**Fix:** Cache the result for 5-10 seconds. Memory availability does not change meaningfully within that window.

**Training data reload:**
`training_pipeline.py:83-100` (`load_training_data()`) is called by both `should_train()` and `start_training()`. The latter calls `should_train()` first, then `load_training_data()` again, reading the entire JSONL file twice.

**MLX availability check:**
`training_pipeline.py:136-144` (`check_mlx_available()`) spawns a subprocess every time it is called. It is called from `stats()` which is called on every status check.

### 6.4 Memory-Intensive Operations

**Model loading (1.2-2.4GB):**
The `MLXCognitiveEngine` correctly caches loaded models and uses a thread lock. Model switching (1.5B to 3B or vice versa) requires unloading the current model first. There is no preemptive unloading -- the old model stays in memory until the new one replaces it, briefly doubling memory usage during the swap.

**Embedding storage:**
`semantic_memory.py` loads ALL embeddings into a Python dict of numpy arrays at startup. For 10K entries at 384-dim float32, that is ~15MB -- manageable. But there is no lazy loading or pagination.

**Perpetual learner state:**
The `seen_hashes` set is bounded at 10K entries, but the `state` dict also stores the full list as JSON. The JSON serialization of 10K hashes is ~400KB -- negligible.

---

## 7. SUMMARY OF ISSUES BY SEVERITY

### CRITICAL (Fix immediately)

1. **Unclosed file handles** in 20+ locations using `json.load(open(...))` pattern
2. **Subprocess-per-memory-check** in `ResourceManager.get_memory_info()` -- should cache for 5-10s
3. **Single-threaded HTTP server** (`sam_api.py`) blocks on ML inference

### HIGH (Fix soon)

4. **SQLite connections without context managers** in `enhanced_memory.py`, `emotional_model.py`, `doc_indexer.py`, `cognitive_control.py`, `auto_learner.py`
5. **ChatGPT export loaded fully into memory** in `perpetual_learner.py` -- should stream
6. **Linear scan for semantic search** -- no vector index for similarity search
7. **15 daemon threads in perpetual_learner.py** -- consolidate to fewer threads with task scheduling
8. **auto_learning.db stored on internal SSD** -- should be on external drive

### MEDIUM (Address when refactoring)

9. **No log rotation** for append-mode log files
10. **Training data read twice** in training pipeline (should_train + start_training)
11. **No auto-unload for main LLM model** after idle period
12. **MLX availability check** spawns subprocess repeatedly -- should cache
13. **No connection pooling** for HTTP requests in perpetual_learner
14. **Vision server uses blocking BaseHTTPRequestHandler** -- should match voice server's FastAPI pattern

### LOW (Nice to have)

15. **No async/await anywhere** -- the entire stack is synchronous
16. **No HTTP request retry logic** for scraper threads
17. **Cosine similarity computed manually** instead of using numpy batch operations
18. **Double memory during model switch** (old model + new model briefly coexist)

---

## 8. RECOMMENDED QUICK WINS

### 8.1 Cache ResourceManager.get_memory_info() (saves ~300 subprocesses/min)

Add a 5-second TTL cache:
```python
_memory_cache = None
_memory_cache_time = 0

def get_memory_info(self):
    now = time.time()
    if self._memory_cache and (now - self._memory_cache_time) < 5.0:
        return self._memory_cache
    # ... existing subprocess logic ...
    self._memory_cache = (available_gb, total_gb)
    self._memory_cache_time = now
    return self._memory_cache
```

### 8.2 Fix all json.load(open(...)) patterns (prevents FD leaks)

Search-and-replace across codebase:
```python
# Replace: json.load(open(path))
# With:
with open(path) as f:
    data = json.load(f)
```

### 8.3 Use context managers for SQLite (prevents connection leaks)

```python
# Replace:
conn = sqlite3.connect(self.db_path)
# ... queries ...
conn.close()

# With:
with sqlite3.connect(self.db_path) as conn:
    # ... queries ...
```

### 8.4 Move auto_learning.db to external drive

Change in `auto_learner.py`:
```python
TRAINING_DB = Path("/Volumes/David External/sam_learning/auto_learning.db")
```
With fallback to local if external drive not mounted.
