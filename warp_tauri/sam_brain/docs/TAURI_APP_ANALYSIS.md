# Tauri App Analysis: How warp_tauri Connects to sam_brain

**Date:** 2026-01-29
**Purpose:** Map all integration points between the Tauri app and sam_brain so that reorganizing sam_brain does not break the Tauri frontend or Rust backend.

---

## 1. Architecture Overview

The SAM Tauri app is a three-layer system:

```
Frontend (Vue 3 + TypeScript)    -- src/
    |
    | Tauri IPC (invoke)          -- ~200+ registered commands
    v
Rust Backend (Tauri v1.5)        -- src-tauri/src/
    |
    | HTTP / subprocess / file I/O
    v
Python Backend (sam_brain/)      -- sam_api.py, semantic_memory.py, project_browser.py, sam_repl.py
```

The Rust layer is the central hub. It exposes Tauri commands to the frontend and either handles them natively in Rust or delegates to Python/external services.

---

## 2. Tauri Commands (Rust -> Frontend IPC)

The app registers approximately **200+ Tauri commands** in `src-tauri/src/main.rs` via `tauri::generate_handler![]`. These are invoked from the frontend using `@tauri-apps/api/tauri`'s `invoke()` function.

### Command Categories

| Category | Commands | Implemented In |
|----------|----------|---------------|
| **PTY/Terminal** | `spawn_pty`, `send_input`, `resize_pty`, `read_pty`, `close_pty`, `start_pty_output_stream` | `commands.rs` (uses `warp_core::pty::WarpPty`) |
| **AI Query** | `ai_query`, `ai_query_stream` | `commands.rs` (HTTP to Ollama on localhost:11434) |
| **Ollama (Legacy)** | `query_ollama_stream`, `query_ollama`, `query_ollama_chat`, `list_ollama_models`, `prewarm_model` | `ollama.rs` (HTTP to localhost:11434) |
| **Ollama Management** | `cmd_ollama_status`, `cmd_restart_ollama`, `cmd_warm_model`, `cmd_unload_model` | `commands.rs` |
| **Smart Orchestrator** | `smart_process`, `smart_set_character`, `smart_clear_character` | `scaffolding/smart_orchestrator.rs` (HTTP to Ollama) |
| **Shell/Files** | `execute_shell`, `read_file`, `write_file`, `list_directory`, `list_directory_tree`, `current_working_dir`, `edit_file`, `web_fetch` | `commands.rs` |
| **SSH** | `ssh_connect_password`, `ssh_connect_key`, `ssh_send_input`, `ssh_read_output`, `ssh_resize`, `ssh_disconnect`, `ssh_list_sessions` | `ssh_session.rs` |
| **Code Navigation** | `glob_files`, `grep_files` | `commands.rs` |
| **Smart Edit** | `smart_edit`, `edit_line`, `insert_after_line`, `delete_lines`, `regex_replace`, `undo_edit`, `create_file_safe`, `append_to_file` | `scaffolding/smart_edit.rs` |
| **Intelligence Engine** | `intelligence_run`, `intelligence_parse`, `intelligence_v2_run`, `intelligence_v2_parse` | `scaffolding/intelligence_engine.rs`, `scaffolding/intelligence_v2.rs` |
| **Session State** | `get_session_state`, `get_history`, `get_last_command`, `add_alias`, `detect_project`, `get_error_suggestion` | `scaffolding/session_state.rs` |
| **Workflows** | `workflow_create`, `workflow_add_step`, `workflow_list`, `workflow_get`, `workflow_resolve`, `workflow_delete`, `workflow_builtins` | `scaffolding/workflows.rs` |
| **Multi-Edit** | `multi_edit_begin`, `multi_edit_add`, `multi_edit_commit`, `multi_edit_rollback`, `multi_edit_list` | `scaffolding/multi_edit.rs` |
| **Todo Tracker** | `todo_add`, `todo_add_many`, `todo_set_status`, `todo_list`, `todo_stats`, `todo_remove`, `todo_clear`, `todo_clear_completed` | `scaffolding/todo_tracker.rs` |
| **Command Palette** | `palette_search`, `palette_search_files`, `palette_update_files`, `palette_record_usage`, `palette_recent` | `scaffolding/command_palette.rs` |
| **Pane Manager** | `pane_new_tab`, `pane_close_tab`, `pane_split`, `pane_focus`, etc. | `scaffolding/pane_manager.rs` |
| **AI Routing** | `ai_route_request`, `ai_routing_stats` | `scaffolding/hybrid_router.rs` |
| **Embeddings** | `embedding_index_directory`, `embedding_search`, `embedding_search_name`, `embedding_stats`, `embedding_save`, `embedding_load` | `scaffolding/embedding_engine.rs` |
| **Templates** | `template_list`, `template_get`, `template_search`, `template_fill`, `template_generate_prompt` | `scaffolding/template_library.rs` |
| **Model Management** | `model_select`, `model_stats`, `model_list_available`, `model_mark_loaded`, etc. | `scaffolding/micro_models.rs` |
| **Orchestrator** | `orchestrate_request`, `orchestrate_stats` | `scaffolding/orchestrator.rs` |
| **Browser Bridge** | `poll_bridge_response`, `get_bridge_tasks`, `queue_browser_task` | `scaffolding/orchestrator.rs` |
| **Background Tasks** | `background_tasks_list`, `background_tasks_running`, `background_task_get`, `background_task_cancel`, etc. | `scaffolding/background_tasks.rs` |
| **Streaming** | `stream_create_session`, `stream_poll`, `stream_close_session`, `stream_read_file`, `stream_search` | `scaffolding/streaming.rs` |
| **Hooks** | `hooks_init`, `hooks_list`, `hooks_register`, `hooks_unregister`, `hooks_set_enabled`, `hooks_run` | `scaffolding/hooks.rs` |
| **Skills** | `skills_list`, `skills_search`, `skills_parse`, `skills_execute`, `skills_execute_raw` | `scaffolding/skills.rs` |
| **MCP** | `mcp_add_server`, `mcp_connect`, `mcp_list_tools`, `mcp_call_tool`, `mcp_load_config`, `mcp_list_servers` | `scaffolding/mcp.rs` |
| **Speed Cache** | `cache_get_stats`, `cache_check`, `cache_clear_all`, `cache_hit_rate` | `scaffolding/speed_cache.rs` |
| **Web Search** | `cmd_web_search`, `cmd_web_fetch` | `scaffolding/web_search.rs` |
| **Config Files** | `cmd_load_project_config`, `cmd_get_instructions`, `cmd_get_rules` | `scaffolding/config_files.rs` |
| **Parallel Agents** | `cmd_execute_parallel`, `cmd_create_parallel_task`, `cmd_cancel_parallel_agents`, `cmd_parallel_stats` | `scaffolding/parallel_agents.rs` |
| **Autocomplete** | `cmd_get_completions`, `cmd_add_completion_history`, `cmd_autocomplete_stats` | `scaffolding/autocomplete.rs` |
| **Hot Reload** | `cmd_watch_directory`, `cmd_unwatch_directory`, `cmd_start_watcher`, `cmd_stop_watcher`, `cmd_reindex`, `cmd_indexer_stats` | `scaffolding/hot_reload.rs` |
| **Autonomy** | `cmd_set_autonomy_level`, `cmd_get_autonomy_level`, `cmd_requires_approval`, `cmd_approve_action`, `cmd_dispatch_mode_on/off` | `scaffolding/autonomy.rs` |
| **Subagents** | `cmd_create_delegation_plan`, `cmd_execute_delegation_plan`, `cmd_get_delegation_plan`, `cmd_cancel_delegation_plan` | `scaffolding/subagents.rs` |
| **Character Library** | `cmd_list_archetypes`, `cmd_get_archetype`, `cmd_create_from_archetype`, `cmd_save_character`, etc. | `scaffolding/character_library.rs` |
| **Character Memory** | `cmd_get_character_memory`, `cmd_add_character_message`, `cmd_remember_character_fact`, etc. | `scaffolding/persistence.rs` |
| **Conversation** | `send_test_message`, `send_user_message`, `get_conversation_state` | `conversation.rs` |
| **Telemetry** | `telemetry_insert_event`, `telemetry_query_recent`, `telemetry_export_csv` | `telemetry.rs` |
| **Policy** | `policy_list_rules`, `policy_propose_diff`, `policy_apply_suggestion`, `policy_rollback`, etc. | `policy_store.rs` |
| **Agents** | `agent_register`, `agent_update`, `agent_set_status`, `agent_list`, `agent_unregister` | `agents.rs` |
| **Plans** | `phase6_create_plan`, `phase6_get_plan`, `phase6_update_plan_status`, etc. | `plan_store.rs` |
| **Monitoring** | `get_monitoring_events`, `clear_monitoring_phase`, `clear_monitoring_all` | `monitoring.rs` |
| **Scheduler** | `start_scheduler`, `stop_scheduler` | `scheduler.rs` |
| **Unified Agent** | `start_unified_task`, `resume_unified_task`, `list_unified_tasks`, `get_unified_task_status` | `scaffolding/unified_agent.rs` |
| **Scaffolded Agent** | `start_agent_task`, `list_agent_models`, `check_ollama_status`, `execute_agent_tool` | `scaffolding/ollama_agent.rs` |
| **Session** | `save_session`, `load_session` | `session.rs` |
| **Test Harness** | `test_status`, `test_get_cases` | `scaffolding/test_harness.rs` |
| **Misc** | `get_app_version`, `debug_log`, `execute_action` | `main.rs`, `commands.rs` |

---

## 3. How the Frontend Communicates with sam_brain

There are **four distinct communication channels** between the Tauri app and sam_brain:

### Channel 1: Tauri IPC -> Rust -> Python subprocess (brain.rs)

**File:** `src-tauri/src/brain.rs`

The `brain.rs` module defines Tauri commands that call Python scripts in sam_brain via `std::process::Command`:

```rust
const BRAIN_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../sam_brain");
```

**Commands that shell out to Python:**
- `search_projects()` -- runs `python3 project_browser.py search <query>` (also reads `master_inventory.json` directly)
- `get_project_categories()` -- runs `python3 project_browser.py categories`
- `generate_code()` -- runs `ollama run sam-coder <prompt>`
- `add_memory()` -- runs inline Python: `from semantic_memory import SemanticMemory; mem.add(...)`
- `query_memory()` -- runs inline Python: `from semantic_memory import SemanticMemory; mem.query(...)`

**CRITICAL:** These commands reference `project_browser.py` and `semantic_memory.py` by name in the sam_brain directory. Renaming or moving these files will break these commands.

**NOTE:** `brain.rs` commands (`get_brain_status`, `search_projects`, `get_project_categories`, `generate_code`, `get_starred_projects`, `add_memory`, `query_memory`) are defined but NOT registered in the `main.rs` invoke_handler. They exist but are currently unused by the frontend. They may be intended for future use or were superseded by the scaffolding system.

### Channel 2: Direct HTTP to sam_api.py (localhost:8765)

The frontend makes direct HTTP calls to the sam_brain Python API server:

**Startup pre-warm (Rust side, `main.rs`):**
```rust
// Health check: GET http://localhost:8765/api/health
// Warm-up:     POST http://localhost:8765/api/query {"query":"warmup"}
```

**Frontend direct HTTP calls:**
- `src/components/AIChatTab.vue` -- `POST http://localhost:8765/api/vision/process` (image analysis)
- `src/composables/useCognitiveAPI.ts` -- Full HTTP client for `http://localhost:8765`:
  - Health checks, text processing, streaming SSE, vision, mood, learning/feedback
- `src/composables/useSAM.ts` -- Initializes `useCognitiveAPI({ baseUrl: 'http://localhost:8765' })`
- `src/composables/useAvatarBridge.ts` -- WebSocket on port 8765
- `src/core/sam.ts` -- Config with `wsPort: 8765`

**CRITICAL:** Port 8765 is the primary interface between the Tauri frontend and the MLX Python backend. The frontend bypasses the Rust layer entirely for cognitive/vision queries. If `sam_api.py` changes its API routes or port, these frontend files break.

### Channel 3: Tauri IPC -> Rust PTY -> sam_repl.py

**File:** `src/composables/useDualTerminal.ts`

The "dual terminal" view spawns a PTY running sam_brain's REPL:

```typescript
const samBrainPath = '/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain'
const result = await invoke('spawn_pty', {
  shell: `/bin/zsh -c "cd ${samBrainPath} && source .venv/bin/activate; python sam_repl.py"`
})
```

**CRITICAL:** This hardcodes the absolute path to sam_brain and references `sam_repl.py` by name.

### Channel 4: Tauri IPC -> Rust -> Shell -> sam_brain scripts

**File:** `src/composables/useEvolution.ts`

The evolution system references sam_brain paths on the SSOT volume:

```typescript
const SSOT_PATH = '/Volumes/Plex/SSOT'
const SAM_BRAIN_PATH = `${SSOT_PATH}/sam_brain`
```

It runs `python3 sam_brain/advanced_evolution.py run --interval 15` via `execute_shell` Tauri command.

---

## 4. What the Rust Code Does Natively vs Delegating to Python

### Done entirely in Rust (no Python dependency):

- **Terminal/PTY management** -- spawn, read, write, resize, close PTY sessions
- **File operations** -- read_file, write_file, edit_file, smart_edit, multi_edit, glob, grep
- **Shell execution** -- execute_shell (runs commands and returns output)
- **SSH sessions** -- full SSH client using `ssh2` crate
- **Conversation state** -- in-memory conversation tracking
- **Intelligence engine** -- keyword-based task classification and execution (no AI)
- **Session state** -- project detection, command history, aliases, error suggestions
- **Workflows, todos, command palette, pane management** -- all pure Rust
- **Embeddings** -- Rust-native embedding engine (simple bag-of-words in `embedding_engine.rs`)
- **Template library, micro model management** -- Rust data structures
- **Speed cache, hooks, skills, MCP** -- all Rust
- **Autonomy controls, subagents, parallel agents** -- coordination logic in Rust
- **Character library** -- archetype definitions and character CRUD in Rust
- **Telemetry, policy store, plans, monitoring** -- SQLite via `rusqlite`
- **Test harness** -- test execution framework in Rust

### Delegates to Ollama (HTTP to localhost:11434):

- `ai_query_stream` -- sends chat messages to Ollama's `/api/chat`
- `query_ollama_stream`, `query_ollama`, `query_ollama_chat` -- direct Ollama API calls
- `prewarm_model`, `list_ollama_models` -- Ollama management
- `smart_orchestrator` -- model swapping, loading, unloading via Ollama API
- `check_ollama_status`, `cmd_ollama_status`, etc. -- status checks

**Note:** Ollama was decommissioned 2026-01-18. These still exist for API compatibility but the primary inference path is now MLX via sam_api.py.

### Delegates to Python (sam_brain):

- `brain.rs` commands (currently unregistered): `project_browser.py`, `semantic_memory.py`
- Startup health check/warm-up of `sam_api.py` on port 8765
- `useDualTerminal.ts` spawns `sam_repl.py` via PTY
- `useEvolution.ts` runs `advanced_evolution.py` via shell

### Delegates to Python (frontend direct, bypasses Rust):

- `useCognitiveAPI.ts` -- all cognitive processing via HTTP to port 8765
- `AIChatTab.vue` -- vision processing via HTTP to port 8765

---

## 5. IPC Mechanisms Beyond HTTP

### 5.1 Tauri IPC (Primary)

The dominant communication mechanism. Frontend calls `invoke('command_name', { args })` which crosses the Tauri IPC bridge to call `#[tauri::command]` functions in Rust. This is synchronous request/response.

### 5.2 Tauri Events (Streaming)

For streaming responses, the Rust side uses `app_handle.emit_all()` and the frontend listens with `listen()`:

- **Ollama streaming:** Event `ollama://stream/{sessionId}` emits token chunks; `ollama://stream/{sessionId}/done` signals completion
- **AI response chunks:** Event `ai_response_chunk` with `{ tabId, chunk }`
- **Model loading:** Event `model-loading` with `{ model, status }`
- **PTY output streaming:** `start_pty_output_stream` polls PTY and emits `pty_output_{id}` events at adaptive rates (16-100ms)

### 5.3 WebSocket (Test Bridge)

`test_bridge.rs` runs a WebSocket server on port 9223 (when `WARP_OPEN_TEST_MODE=1`). External test scripts connect to control the app.

### 5.4 HTTP Debug Server

`debug_server.rs` runs an HTTP server on port 9998 (currently disabled in main.rs). Provides endpoints: `/debug/state`, `/debug/ollama`, `/debug/warm`, `/debug/ping`.

### 5.5 File-Based IPC (Test Harness)

`main.rs` spawns a thread that watches `/tmp/sam_test_command.json` for test commands and writes results to `/tmp/sam_test_results.json`. Supports commands: `test_run_suite`, `test_run_smoke`, `test_run_single`, `smart_process`.

### 5.6 Direct HTTP from Frontend

`useCognitiveAPI.ts` and `AIChatTab.vue` make direct `fetch()` calls to `http://localhost:8765` bypassing Tauri IPC entirely. This is the primary path for cognitive/vision features.

---

## 6. sam_brain Files Referenced by the Tauri App

### Direct references (will break if renamed/moved):

| File | Referenced By | How |
|------|--------------|-----|
| `sam_api.py` | `main.rs` (startup), `useCognitiveAPI.ts`, `useSAM.ts`, `AIChatTab.vue`, `useAvatarBridge.ts`, `core/sam.ts` | HTTP on port 8765 |
| `project_browser.py` | `brain.rs` | `python3 project_browser.py search/categories` |
| `semantic_memory.py` | `brain.rs` | `from semantic_memory import SemanticMemory` |
| `sam_repl.py` | `useDualTerminal.ts` | `python sam_repl.py` via PTY |
| `advanced_evolution.py` | `useEvolution.ts` | `python3 sam_brain/advanced_evolution.py` |
| `exhaustive_analysis/master_inventory.json` | `brain.rs` | Direct file read |
| `training_data/style_profile.json` | `brain.rs` | Existence check |

### Indirect references (via BRAIN_DIR constant):

```rust
// In brain.rs
const BRAIN_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../sam_brain");
```

This resolves to the sam_brain directory relative to `src-tauri/Cargo.toml` at compile time.

### Hardcoded paths in frontend:

```typescript
// useDualTerminal.ts
const samBrainPath = '/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain'

// useEvolution.ts
const SSOT_PATH = '/Volumes/Plex/SSOT'
const SAM_BRAIN_PATH = `${SSOT_PATH}/sam_brain`
```

---

## 7. Managed State (Rust Singletons)

The Tauri app manages these state objects, passed to commands via dependency injection:

| State | Type | Storage |
|-------|------|---------|
| `PtyRegistry` | In-memory HashMap of PTY sessions | RAM only |
| `ConversationState` | In-memory conversation tracking | RAM only |
| `SshState` | SSH session manager | RAM only |
| `TelemetryStore` | SQLite at `~/.warp_open/telemetry.sqlite` | Disk |
| `PolicyStore` | SQLite at `~/.warp_open/policy.sqlite` | Disk |
| `AgentCoordinator` | In-memory agent registry | RAM only |
| `PlanStore` | SQLite at `~/.warp_open/plans.sqlite` | Disk |
| `MonitoringState` | In-memory monitoring events | RAM only |
| `Scheduler` | Periodic task runner (10s interval) | RAM only |

---

## 8. External Dependencies

### Rust crate: `warp_core`

```toml
warp_core = { path = "../../warp_core" }
```

Located at `/Users/davidquinton/ReverseLab/SAM/warp_core`. Provides `WarpPty` for terminal emulation.

### Port Map

| Port | Service | Used By |
|------|---------|---------|
| 8765 | sam_api.py (MLX inference) | Rust startup, frontend composables, AIChatTab |
| 11434 | Ollama (LEGACY, decommissioned) | ollama.rs, commands.rs, smart_orchestrator.rs |
| 5173 | Vite dev server | Tauri dev mode |
| 9223 | Test bridge WebSocket | test_bridge.rs (test mode only) |
| 9998 | Debug HTTP server | debug_server.rs (currently disabled) |

---

## 9. Impact Assessment for sam_brain Reorganization

### HIGH RISK -- Will immediately break:

1. **Renaming/moving `sam_api.py`** -- Breaks frontend cognitive API, vision, and Rust startup health check
2. **Changing port 8765** -- Breaks all HTTP clients in frontend and Rust
3. **Renaming `sam_repl.py`** -- Breaks dual terminal feature
4. **Moving sam_brain directory** -- Breaks `BRAIN_DIR` compile-time constant in brain.rs

### MEDIUM RISK -- Will break if used:

5. **Renaming `project_browser.py`** -- Breaks brain.rs commands (currently unregistered but code exists)
6. **Renaming `semantic_memory.py`** -- Breaks brain.rs inline Python calls (currently unregistered)
7. **Renaming `advanced_evolution.py`** -- Breaks evolution dashboard
8. **Moving `exhaustive_analysis/master_inventory.json`** -- Breaks brain.rs inventory queries

### LOW RISK -- Safe to change:

9. **Internal Python modules** not referenced by name from Rust/frontend
10. **Training data files** (referenced only by Python code)
11. **Config files** within sam_brain (loaded by Python, not Rust)

### Recommended Approach:

1. Keep `sam_api.py` as the single HTTP interface (port 8765) -- the frontend already depends on it
2. Keep `sam_repl.py` name stable or update `useDualTerminal.ts`
3. The `brain.rs` commands are currently dead code (not in invoke_handler) -- safe to ignore or clean up
4. If reorganizing internal modules, only `sam_api.py` needs to maintain backward-compatible imports
5. Consider making the hardcoded path in `useDualTerminal.ts` configurable

---

## 10. Scaffolding System (src-tauri/src/scaffolding/)

The `scaffolding/` directory contains **70+ Rust modules** implementing a massive feature set. This is all native Rust code with no Python dependency. Key modules:

- `smart_orchestrator.rs` -- Model swapping, RAG memory, tool augmentation (talks to Ollama)
- `intelligence_engine.rs` / `intelligence_v2.rs` -- Keyword-based task routing (no AI needed)
- `embedding_engine.rs` -- Simple bag-of-words embeddings in Rust
- `character_library.rs` -- Character archetype definitions
- `persistence.rs` -- File-based persistence for tasks, characters, memory
- `unified_agent.rs` -- Guaranteed-success agent loop
- `hybrid_router.rs` -- Routes requests between local/AI/browser providers

These modules are independent of sam_brain and safe to ignore during reorganization.
