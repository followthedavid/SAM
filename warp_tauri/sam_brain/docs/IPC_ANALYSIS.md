# SAM Inter-Process Communication Analysis

**Date:** 2026-01-29
**Scope:** All processes in `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`

---

## 1. Process Inventory

| Process | File | Port | Type | Managed By |
|---------|------|------|------|------------|
| SAM API | `sam_api.py` | 8765 | HTTP server | launchd (`com.sam.api`) |
| Vision Server | `vision_server.py` | 8766 | HTTP server | Manual / unified_daemon |
| Perpetual Learner | `perpetual_learner.py` | None | Daemon (threads) | Manual / launchd |
| Auto Learner | `auto_learner.py` | None | Daemon (watchdog) | launchd (`com.sam.autolearner`) |
| Unified Daemon | `unified_daemon.py` | None | Process supervisor | launchd (`com.sam.daemon`) |
| Proactive Notifier | `proactive_notifier.py` | None | Polling daemon | Manual |
| Terminal Learning | `terminal_learning.py` | None | Library (called by others) | Imported |
| Scraper Daemon | External (`scrapers/`) | 8089 | HTTP server | unified_daemon |

---

## 2. Communication Mechanisms

### 2.1 HTTP REST (Primary IPC Method)

SAM processes communicate almost exclusively over HTTP on localhost. There are no Unix sockets, shared memory segments, message queues (ZMQ, RabbitMQ, etc.), or `multiprocessing.Pipe`/`Queue` objects used between separate processes.

#### sam_api.py (port 8765) as Central Hub

The SAM API is the central communication hub. Other processes make HTTP calls to it:

| Caller | Target | Endpoint | Purpose |
|--------|--------|----------|---------|
| `perpetual_learner.py` | sam_api:8765 | `POST /api/chat` | Curriculum learning -- SAM attempts tasks via its own API |
| `terminal_learning.py` | sam_api:8765 | `POST /api/chat` | Local attempt at answering questions |
| `proactive_notifier.py` | sam_api:8765 | Various GET endpoints | Polls for suggestions, status, feedback stats |
| `cognitive/vision_client.py` | sam_api:8765 | `POST /api/vision/*` | Vision processing via API |
| `cognitive/test_e2e_comprehensive.py` | sam_api:8765 | Various | End-to-end testing |
| `unified_daemon.py` | sam_api:8765 | `GET /api/status` (via curl) | Health check |

#### vision_server.py (port 8766) as Specialist

The vision server is a secondary HTTP service. Multiple callers attempt it first, then fall back to direct CLI invocation:

| Caller | Target | Endpoint | Fallback |
|--------|--------|----------|----------|
| `sam_api.py` (vision streaming) | vision:8766 | `POST /process` | Direct `mlx_vlm` CLI |
| `cognitive/vision_engine.py` | vision:8766 | `GET /health`, `POST /process` | Direct `mlx_vlm` CLI |
| `cognitive/smart_vision.py` | vision:8766 | `GET /health`, `POST /process` | Direct `mlx_vlm` CLI |

**Pattern:** All vision callers use a try/except approach: attempt `localhost:8766` first, catch `ConnectionError`/`Timeout`, then fall through to direct model loading. The vision server is treated as an optional accelerator, not a hard dependency.

#### Scraper Daemon (port 8089, external)

Referenced in `unified_daemon.py` as a managed service at port 8089. Health-checked via `curl -s http://localhost:8089/status`.

### 2.2 Shared Databases (SQLite)

Multiple processes read from and write to shared SQLite databases. SQLite provides process-level concurrency via file locking, but there is no explicit coordination beyond what SQLite's default locking provides.

| Database | Location | Writers | Readers |
|----------|----------|---------|---------|
| `auto_learning.db` | `sam_brain/auto_learning.db` | `auto_learner.py` | `auto_learner.py` |
| `curriculum.db` | `/Volumes/David External/sam_learning/curriculum.db` | `perpetual_learner.py` | `perpetual_learner.py` |
| `evolution.db` | `sam_brain/evolution.db` | `evolution_tracker.py` | Various |
| `terminal_sessions.db` | `~/.sam/terminal_sessions.db` | `terminal_sessions.py` | `sam_api.py` (via import) |
| `approval_queue.db` | `~/.sam/approval_queue.db` | `approval_queue.py` | `sam_api.py` (via import) |
| `relationships.db` | `/Volumes/David External/sam_memory/relationships.db` | `cognitive/emotional_model.py` | Same |
| `vision_selector.db` | `~/.sam/vision_selector.db` | `cognitive/vision_selector.py` | Same |
| `patterns.db` | `/Volumes/David External/sam_code_patterns/patterns.db` | `cognitive/code_pattern_miner.py` | Same |
| Various scraper DBs | `/Volumes/David External/*/` | Scraper processes | `system_orchestrator.py` |

**Concurrency risk:** SQLite's default journal mode is `DELETE`, which uses file-level locking. If `perpetual_learner.py` is writing training data while `sam_api.py` (via imported modules) tries to read the same database, one will block briefly. The `approval_queue.py` uses `timeout=30.0` on its connection, which is good practice. Most other modules do not set a connection timeout.

### 2.3 Shared Files (JSONL, JSON State Files)

Several processes write to shared JSONL training data files and JSON state files:

| File | Location | Writers | Purpose |
|------|----------|---------|---------|
| `perpetual_*.jsonl` | `sam_brain/data/` | `perpetual_learner.py` (multiple threads) | Training data per category |
| `perpetual_merged.jsonl` | `sam_brain/data/` | `perpetual_learner.py` training scheduler | Merged for training |
| `train.jsonl` / `valid.jsonl` | `sam_brain/data/` | `perpetual_learner.py`, `auto_learner.py` | Training splits (both write to same path!) |
| `curriculum_learned.jsonl` | `sam_brain/data/` | `perpetual_learner.py` (curriculum stream) | Curriculum training data |
| `training_runs.json` | `sam_brain/` | `perpetual_learner.py` | Training run log |
| `.perpetual_state.json` | `sam_brain/` | `perpetual_learner.py` | Daemon state (dedup hashes, stats) |
| `daemon_status.json` | `sam_brain/` | SAM daemon | Daemon liveness |
| `realtime_learning_queue.jsonl` | `sam_brain/` | `claude_learning.py` | Queued learning pairs |
| `stats.json` | `sam_brain/` | Various | System statistics |
| `.ssot_sync_state.json` | `sam_brain/` | `ssot_sync.py` | Sync state |
| `state.json` | `~/.sam/daemon/` | `unified_daemon.py` | Supervisor state |

**Conflict risk:** Both `perpetual_learner.py` and `auto_learner.py` write `train.jsonl` and `valid.jsonl` in `sam_brain/data/`. If both run their training cycles simultaneously, they will overwrite each other's training splits. However, `auto_learner.py` writes to `sam_brain/auto_training_data/` (its own directory), so in practice this may be distinct. The `perpetual_learner.py` writes to `sam_brain/data/`.

### 2.4 PID Files (Process Liveness)

PID files are used for process lifecycle management:

| PID File | Written By | Read By |
|----------|-----------|---------|
| `~/.sam/daemon/unified_daemon.pid` | `unified_daemon.py` | `unified_daemon.py` (start/stop) |
| `sam_brain/.sam_daemon.pid` | `unified_daemon.py` | `unified_daemon.py` |
| `~/.sam_scraper_daemon.pid` | Scraper daemon | `unified_daemon.py` |
| `~/.sam_training_daemon.pid` | Training pipeline | `unified_daemon.py` |
| `~/.sam_dashboard.pid` | Dashboard | `unified_daemon.py` |
| `/tmp/sam_proactive_notifier.pid` | `proactive_notifier.py` | `proactive_notifier.py` |

### 2.5 Unix Signals

`unified_daemon.py` uses Unix signals for process control:

| Signal | Sender | Receiver | Effect |
|--------|--------|----------|--------|
| `SIGSTOP` | unified_daemon | Managed services | Pause (freeze) process to free RAM |
| `SIGCONT` | unified_daemon | Managed services | Resume frozen process |
| `SIGTERM` | unified_daemon | Managed services | Graceful shutdown |
| `SIGKILL` | unified_daemon | Managed services | Force kill (after SIGTERM timeout) |
| `SIGTERM` | OS/user | perpetual_learner | Triggers `running = False`, saves state |
| `SIGINT` | user (Ctrl+C) | perpetual_learner | Same as SIGTERM |

### 2.6 launchd Restart (Crash Recovery)

macOS launchd provides the only automatic crash recovery:

| Service | Plist | KeepAlive Policy |
|---------|-------|------------------|
| SAM API | `com.sam.api.plist` | Restart on crash (`Crashed: true`) and abnormal exit (`SuccessfulExit: false`) |
| Unified Daemon | `com.sam.daemon.plist` | Restart on abnormal exit (`SuccessfulExit: false`) |
| Auto Learner | Generated by `auto_learner.py install` | `KeepAlive: true` (always restart) |

---

## 3. Startup Order and Dependencies

### 3.1 launchd Startup (Login)

Both `com.sam.api` and `com.sam.daemon` have `RunAtLoad: true`. launchd starts them in parallel with no defined ordering. The `install_launchd.sh` script loads `com.sam.api` first, then `com.sam.daemon`, but launchd does not guarantee execution order.

### 3.2 Implied Dependency Graph

```
                    launchd
                   /       \
                  v         v
            sam_api.py    unified_daemon.py
            (port 8765)        |
                 ^             |-- starts --> sam_brain (cognitive)
                 |             |-- starts --> scrapers (port 8089)
                 |             |-- starts --> training pipeline
                 |             |-- starts --> dashboard
                 |             |-- monitors -> plex, backblaze, transmission
                 |
                 |--- perpetual_learner.py calls POST /api/chat
                 |--- proactive_notifier.py polls GET endpoints
                 |--- terminal_learning.py calls POST /api/chat
                 |
            vision_server.py (port 8766) -- optional, no hard dependents
```

### 3.3 Required Startup Order

1. **sam_api.py** -- Must be running before anything that calls `localhost:8765`
2. **vision_server.py** -- Optional. All callers gracefully fall back to direct CLI
3. **perpetual_learner.py** -- Independent. Calls sam_api but degrades gracefully (returns 0.1 confidence)
4. **auto_learner.py** -- Independent. Watches filesystem, no inter-process dependencies
5. **unified_daemon.py** -- Manages others but can start at any time; starts services itself

### 3.4 start_sam.sh Ordering

The `start_sam.sh` script in "all" mode:
1. Starts `sam_api.py server 8765` in background
2. Sleeps 2 seconds
3. Starts `autonomous_daemon.py` in foreground

This is the only script that enforces ordering. The launchd plists do not.

---

## 4. Failure Analysis: What Happens When One Crashes?

### 4.1 sam_api.py Crashes

**Impact: HIGH -- It is the central hub.**

| Affected Process | Behavior |
|------------------|----------|
| perpetual_learner.py | `_curriculum_attempt()` catches `requests` exception, logs "SAM API unavailable", returns confidence 0.1. Continues running. |
| terminal_learning.py | `attempt_question()` catches exception, returns `None`. Caller handles gracefully. |
| proactive_notifier.py | HTTP calls fail silently (urllib catches errors). Keeps polling. |
| vision_server.py | Unaffected (independent, no dependency on sam_api). |
| unified_daemon.py | Health check (`curl localhost:8765/api/status`) fails, triggers restart of `sam_brain` service. |
| auto_learner.py | Unaffected (watches filesystem only, does not call API). |
| launchd | Detects crash or abnormal exit, restarts sam_api.py (10-second throttle). |

**Recovery time:** ~10 seconds (launchd ThrottleInterval).

### 4.2 vision_server.py Crashes

**Impact: LOW -- All callers have fallbacks.**

| Affected Process | Behavior |
|------------------|----------|
| sam_api.py | `ConnectionError` caught, falls through to direct `mlx_vlm` CLI invocation. Slower but functional. |
| cognitive/vision_engine.py | Same pattern -- catches exception, uses direct model loading. |
| cognitive/smart_vision.py | Same pattern. |

**Recovery:** No automatic restart unless managed by unified_daemon. Vision continues working via CLI fallback.

### 4.3 perpetual_learner.py Crashes

**Impact: LOW -- No other process depends on it.**

| Affected Process | Behavior |
|------------------|----------|
| sam_api.py | Unaffected. |
| auto_learner.py | Unaffected (separate learner). |
| All others | Unaffected. |

**Data risk:** State file `.perpetual_state.json` is saved every 10 seconds in the main loop. At most 10 seconds of dedup hash state is lost. Training data already written to JSONL files is safe.

### 4.4 auto_learner.py Crashes

**Impact: LOW -- Completely independent.**

| Affected Process | Behavior |
|------------------|----------|
| All others | Unaffected. |

**Recovery:** If installed via launchd with `KeepAlive: true`, restarts automatically. Database state (`auto_learning.db`) is durable.

### 4.5 unified_daemon.py Crashes

**Impact: MEDIUM -- Supervisor dies, managed services keep running.**

| Affected Process | Behavior |
|------------------|----------|
| Managed services | Continue running (they are separate OS processes). No more health checks, restarts, or resource management until daemon recovers. |
| RAM management | No more SIGSTOP/SIGCONT resource management. Low-priority services may cause memory pressure. |

**Recovery:** launchd restarts it via `com.sam.daemon.plist`.

---

## 5. Communication Topology Summary

```
                      +-------------------+
                      |   launchd (macOS)  |
                      | (crash recovery)   |
                      +---+-------+-------+
                          |       |
                  restart |       | restart
                          v       v
   +---+     HTTP     +----------+     manages     +-----------------+
   |   | <----------> | sam_api  | <-------------- | unified_daemon  |
   |   |   :8765      | (hub)    |   health check  | (supervisor)    |
   | P |              +----+-----+                  +---+---+---+----+
   | E |                   ^                            |   |   |
   | R |     HTTP          |                     start/ |   |   | start/
   | P |     :8766         |                     stop   |   |   | stop
   | E | +-------------+  |                            v   v   v
   | T | |vision_server |  |                      scrapers dashboard
   | U | |(optional)    |  |                      training
   | A | +------+------+  |
   | L |        ^          |
   |   |        |          |
   | L |  try   |  HTTP    |
   | E |  first |  fallback|
   | A |        |          |
   | R | +------+----------+-----+
   | N | | sam_api.py             |
   | E | | cognitive/vision_engine|
   | R | | cognitive/smart_vision |
   |   | +------------------------+
   +---+
     |
     | HTTP POST /api/chat (curriculum attempts)
     +------> sam_api.py:8765
```

### IPC Method Breakdown

| Method | Usage | Between |
|--------|-------|---------|
| **HTTP REST** | Primary | sam_api <-> all callers; vision_server <-> vision clients |
| **SQLite files** | Shared state | Multiple processes via file locking |
| **JSONL files** | Training data | Learners write, training pipeline reads |
| **JSON files** | Daemon state | Each process owns its state file |
| **PID files** | Liveness | Daemon writes, supervisor reads |
| **Unix signals** | Process control | unified_daemon -> managed services |
| **launchd** | Crash recovery | OS -> managed services |
| **Unix sockets** | Not used | -- |
| **Shared memory** | Not used | -- |
| **Message queues** | Not used | -- |

---

## 6. Identified Issues and Risks

### 6.1 No Startup Ordering Guarantee

The two launchd plists (`com.sam.api` and `com.sam.daemon`) both have `RunAtLoad: true` with no dependency relationship. If `unified_daemon.py` starts and tries to health-check `sam_api.py` before it is ready, the health check will fail and trigger a (premature) restart attempt.

### 6.2 Training Data File Conflicts

Both `perpetual_learner.py` and `auto_learner.py` can trigger MLX training runs. If both trigger simultaneously:
- `perpetual_learner.py` writes `data/train.jsonl` and `data/valid.jsonl`
- `auto_learner.py` writes `auto_training_data/train.jsonl` and `auto_training_data/valid.jsonl`
- Both invoke `mlx_lm.lora` with the same base model

Running two LoRA training processes concurrently on 8GB RAM would almost certainly cause a system freeze. The `cognitive/resource_manager.py` `can_train()` check helps, but both processes call it independently -- there is no cross-process lock.

### 6.3 No Process Discovery

Processes find each other only by hardcoded ports (`localhost:8765`, `localhost:8766`, `localhost:8089`). If a port is occupied by another process, there is no detection mechanism beyond HTTP health check failures.

### 6.4 SQLite Concurrent Access

Most SQLite connections do not set a `timeout` parameter. Under concurrent access, writers will get `sqlite3.OperationalError: database is locked` immediately rather than retrying. Only `approval_queue.py` uses `timeout=30.0`.

### 6.5 No Crash Notification Between Processes

Beyond `unified_daemon.py`'s 60-second health check loop, processes do not actively detect each other's crashes. A crashed `vision_server.py` is only discovered when the next vision request tries to connect and gets a `ConnectionError`.

### 6.6 Perpetual Learner Internal Concurrency

`perpetual_learner.py` runs 15 daemon threads internally (scrapers, generators, curriculum, training, stats). These threads share the `_add_example()` method and the `seen_hashes` set without a lock. The `set.add()` operation in CPython is atomic due to the GIL, but this is an implementation detail, not a guarantee.

---

## 7. Recommendations

1. **Add a startup dependency** in launchd or use a readiness-check loop in `unified_daemon.py` before starting health checks on `sam_api.py`.
2. **Add a cross-process training lock** (e.g., a lockfile at `~/.sam/training.lock`) so `perpetual_learner.py` and `auto_learner.py` cannot train simultaneously.
3. **Set `timeout=10.0`** on all `sqlite3.connect()` calls to handle concurrent access gracefully.
4. **Add a `threading.Lock`** around `seen_hashes` mutations in `perpetual_learner.py`, or document reliance on CPython's GIL.
5. **Consider a health check endpoint** on `perpetual_learner.py` and `auto_learner.py` so the unified daemon can monitor them too.
