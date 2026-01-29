# SAM Brain Master Audit Summary

**Generated:** 2026-01-29
**Synthesized from:** 20 audit documents
**Codebase:** 172 Python files, ~144,255 lines of code
**Hardware:** M2 Mac Mini, 8GB RAM

---

## 1. CRITICAL FIXES (Security, Crashes, Data Loss)

### 1.1 Security -- CRITICAL

| ID | Issue | File(s) | Severity |
|----|-------|---------|----------|
| SEC-1 | **Shell injection via LLM-generated commands.** `execute_tool()` passes LLM output to `subprocess.run(shell=True)` with a trivially bypassable blocklist (substring check, not a parser). Bypasses: path traversal, quote splitting, prefix injection, `curl | sh`. | `sam_agent.py:148-161` | CRITICAL |
| SEC-2 | **Shell injection via grep tool.** User-controlled `arg` interpolated into single-quoted shell command. `'; malicious; echo '` breaks out. | `sam_agent.py:156-161` | CRITICAL |
| SEC-3 | **Path traversal in static file serving.** No validation that requested paths stay within the static directory. | `sam_api.py` | CRITICAL |
| SEC-4 | **All three API servers (sam_api :8765, vision_server :8766, voice_server) have zero authentication, zero rate limiting, wildcard CORS, and bind to 0.0.0.0.** Any device on the network can access all endpoints, query SAM, read memory, delete facts, approve/reject items, trigger inference. | `sam_api.py`, `vision_server.py`, `voice/voice_server.py` | HIGH (CRITICAL if internet-exposed) |
| SEC-5 | **TLS private key stored in project directory.** `voice_key.pem` sits alongside code. Risk of accidental git commit. | `sam_brain/voice_key.pem` | MEDIUM |

**Immediate actions:**
1. Replace `shell=True` in `sam_agent.py` with `subprocess.run(shlex.split(...), shell=False)`
2. Add path canonicalization + prefix check to static file serving
3. Add localhost-only binding or API key auth to all servers
4. Move TLS keys to `~/.sam/certs/`

### 1.2 Data Loss Risk -- CRITICAL

| ID | Issue | Details |
|----|-------|---------|
| DATA-1 | **No backup strategy exists.** No Time Machine, no automated DB backup, no replication. 15+ SQLite databases across internal SSD and external drives are unprotected. | BACKUP_RECOVERY.md |
| DATA-2 | **2,740 uncommitted files.** Git repo has only 7 total commits. The vast majority of current code is NOT on GitHub. | BACKUP_RECOVERY.md |
| DATA-3 | **External drive dependency.** 50+ hardcoded paths reference `/Volumes/David External/` and `/Volumes/#1/`. If drives unmount or rename, SAM loses all memory, training data, and model access. No graceful degradation. | CONFIG_AND_PLATFORM.md |
| DATA-4 | **Broken symlinks.** Several symlinks point to `/Volumes/Applications/` which no longer exists. | BACKUP_RECOVERY.md |

**Immediate actions:**
1. Commit and push to GitHub NOW (even a bulk commit is better than nothing)
2. Create a daily `rsync` cron job for SQLite databases to a second drive
3. Add `os.path.exists()` guards on all external drive paths with graceful fallback

### 1.3 Stability / Crashes

| ID | Issue | Details |
|----|-------|---------|
| STAB-1 | **21 module-level singletons without thread-safe initialization.** In the multi-threaded HTTP server, race conditions can create duplicate instances, waste memory, or corrupt SQLite. `FactMemory` is the worst: global without lock. | STATE_AND_ERRORS.md |
| STAB-2 | **20+ unclosed file handles.** `json.load(open(...))` pattern throughout codebase. On 8GB system, FD exhaustion is possible under load. | IO_AND_PERFORMANCE.md |
| STAB-3 | **45 files exceed 1,000 lines.** `sam_api.py` is 5,658 lines. Difficult to maintain, test, or debug. | CODE_QUALITY_AND_TESTS.md |

---

## 2. DEAD CODE (Confirmed Dead Files with Evidence)

**93 files are orphaned** -- not reachable from any entry point (sam_api.py, perpetual_learner.py, auto_learner.py, vision_server.py, sam.py, sam_repl.py, or unified_daemon.py).

### Confirmed Dead (Safe to Archive)

| File | Lines | Evidence |
|------|-------|---------|
| `claude_orchestrator.py` | 584 | No importer found. CLI-only entry point, never called. |
| `re_orchestrator.py` | 874 | Only imported by orchestrator.py in a `try/except` that catches ImportError. Not used in production. |
| `sam_parity_orchestrator.py` | 543 | No importer found. |
| `system_orchestrator.py` | 802 | No importer found. |
| `unified_orchestrator.py` (root) | 1,016 | No importer found. Different from `cognitive/unified_orchestrator.py`. |
| `smart_summarizer.py` | -- | No internal importers. |
| `narrative_ui_spec.py` | -- | Only referenced by orchestrator in dead code path. |
| `parity_system.py` | -- | No importer found. |
| `auto_validator.py` | -- | No importer found. |
| `deduplication.py` | 1,105 | No importer found -- standalone CLI. |
| `data_quality.py` | 1,101 | No importer found -- standalone CLI. |
| `legitimate_extraction.py` | -- | No importer found. |
| `tts_pipeline.py` | -- | No internal importers (superseded by voice/voice_output.py). |
| All `cognitive/model_evaluation.py` | 2,089 | Only reachable from `cognitive/__init__.py` but never called at runtime. |

**Total dead code: ~93 files, estimated 40,000+ lines.**

These should be moved to `/Volumes/#1/SAM/dead_code_archive/` with manifest entries (not deleted).

---

## 3. DUPLICATES (Exact List)

### 3.1 Near-Exact File Duplicates (~1,000 lines recoverable)

| Keep | Remove | Shared Logic |
|------|--------|-------------|
| `code_indexer.py` (root, 2,074 lines) | `cognitive/code_indexer.py` (676 lines) | PythonParser, RustParser, CodeIndexer, SQLite schema, CLI -- root version is superset with embeddings + Swift support |

### 3.2 Duplicated Class/Enum Definitions (~300 lines recoverable)

| Class/Enum | Defined In | Recommendation |
|-----------|-----------|---------------|
| `VisionTier(Enum)` | `smart_vision.py`, `vision_selector.py`, `vision_client.py`, `resource_manager.py` (4 files, with INCONSISTENT values -- integers vs strings) | Define once in a shared `vision_types.py`, import everywhere |
| `GenerationConfig` | Multiple cognitive files | Consolidate into single definition |
| Various `TaskType` enums | Multiple files | Consolidate |

### 3.3 Overlapping Logic (~4,500 lines recoverable)

| Overlap | Files | Recommendation |
|---------|-------|---------------|
| Vision routing | `smart_vision.py` (695L), `vision_selector.py` (881L), `vision_engine.py` (1,604L), `vision_client.py` (811L) | Merge: vision_engine (core) + vision_client (HTTP wrapper). Remove smart_vision and vision_selector overlap. |
| MLX inference | `mlx_inference.py` (root), `cognitive/mlx_cognitive.py`, `cognitive/mlx_optimized.py` | mlx_inference.py is older/simpler. Route everything through cognitive/mlx_cognitive.py. |
| Training orchestration | `training_pipeline.py` (simpler, legacy), `training_runner.py` (full-featured) | Keep training_runner.py, archive training_pipeline.py |

**Total estimated removable lines: ~5,800**

---

## 4. ARCHITECTURE PROBLEMS

### 4.1 The `cognitive/__init__.py` Problem
- Exports **160+ symbols from 20 submodules**
- Acts as a massive re-export hub that creates tight coupling
- Any reorganization must handle this file carefully or everything breaks
- Many external files do `from cognitive import X` relying on this barrel export

### 4.2 Circular Dependencies (7 cycles identified)
- `cognitive/compression.py` imports `sam_api` (which imports cognitive)
- `query_decomposer.py` circular with `code_indexer.py`
- 5 additional cycles documented in MIGRATION_IMPACT.md
- These MUST be broken before reorganization

### 4.3 Flat Root Directory
- 77 Python files dumped in root with no package structure
- Mixed concerns: entry points, utilities, domain modules, one-off scripts
- No `__init__.py` at root means everything uses `sys.path.insert` hacks (38 instances)

### 4.4 `sam_api.py` is a God Object
- 5,658 lines handling routing, vision, voice, memory, facts, training, CLI, static file serving, streaming, and cognitive endpoints
- Should be split into route modules (at minimum: vision_routes, voice_routes, cognitive_routes, memory_routes, admin_routes)

### 4.5 Tauri App Still References Ollama
- The Rust backend (`src-tauri/src/`) has `ollama.rs` module and ~10 Ollama-related Tauri commands
- Ollama was decommissioned 2026-01-18; these should point to MLX via sam_api.py
- ~200+ Tauri commands total, only a handful actually call sam_brain Python

### 4.6 IPC is HTTP-Only
- All inter-process communication is localhost HTTP (no Unix sockets, no message queues)
- sam_api.py is the central hub; if it goes down, everything stops
- perpetual_learner.py talks to sam_api.py via HTTP POST to `/api/chat` -- SAM literally queries itself

---

## 5. WHAT ACTUALLY WORKS vs ASPIRATIONAL

### Working (Confirmed Active in Production)

| Capability | Status | Key Files |
|-----------|--------|-----------|
| Chat (MLX Qwen2.5 + SAM LoRA) | WORKING | orchestrator.py, cognitive/mlx_cognitive.py |
| Request routing | WORKING | orchestrator.py (CHAT, CODE, VISION, VOICE, etc.) |
| Semantic memory (MLX embeddings) | WORKING | memory/semantic_memory.py (MiniLM-L6-v2, 384-dim) |
| Fact memory (SQLite) | WORKING | memory/fact_memory.py |
| Vision OCR (Apple Vision) | WORKING | apple_ocr.py (22ms, 0 RAM) |
| Vision VLM (nanoLLaVA) | WORKING | cognitive/vision_engine.py |
| Voice TTS (macOS say) | WORKING | voice/voice_output.py |
| Command execution (sandboxed) | WORKING | execution/safe_executor.py, execution/command_classifier.py |
| Auto-learner daemon | WORKING | auto_learner.py (launchd, watches Claude sessions) |
| Privacy guard | WORKING | privacy_guard.py |
| SAM API server | WORKING | sam_api.py (launchd, port 8765, always running) |
| Personality/response styling | WORKING | response_styler.py |
| Launchd services (5 total) | WORKING | com.sam.api, com.sam.autolearner, com.sam.perpetual, com.sam.daemon, com.sam.voice |

### Partially Working

| Capability | Status | Gap |
|-----------|--------|-----|
| Voice STT (Whisper) | PARTIAL | Pipeline wired but needs Whisper MLX model |
| Voice TTS (F5-TTS) | PARTIAL | Optional dependency, not always installed |
| Voice cloning (RVC) | PARTIAL | Requires Docker on-demand, RVC WebUI |
| Emotion detection | PARTIAL | Prosodic backend works; full emotion2vec needs model weights |
| Image generation | PARTIAL | mflux needs `pipx install`; ComfyUI needs running server |
| Conversation engine | PARTIAL | v0.1.0, early-stage, wired to voice_pipeline but not battle-tested |

### Aspirational (Code Exists, Not Used in Production)

| Capability | Status | Evidence |
|-----------|--------|---------|
| Multi-agent coordination | ASPIRATIONAL | `cognitive/multi_agent_roles.py` (1,183L), `multi_agent.py` -- no importers call them |
| Claude orchestration | ASPIRATIONAL | `claude_orchestrator.py` -- no importers |
| Reverse engineering orchestrator | ASPIRATIONAL | `re_orchestrator.py` -- dead import |
| System orchestrator (ARR/scraper control) | ASPIRATIONAL | `system_orchestrator.py` -- no importers |
| Parity system | ASPIRATIONAL | `parity_system.py`, `sam_parity_orchestrator.py` -- no importers |
| Planning framework | ASPIRATIONAL | `cognitive/planning_framework.py` -- only via __init__.py, never called |
| Learning strategy | ASPIRATIONAL | `cognitive/learning_strategy.py` -- only via __init__.py |
| Data quality pipeline | ASPIRATIONAL | `data_quality.py` (1,101L) -- standalone CLI never called |
| Deduplication pipeline | ASPIRATIONAL | `deduplication.py` (1,105L) -- standalone CLI never called |

---

## 6. REORGANIZATION RECOMMENDATIONS

### Target Structure

```
sam_brain/
  core/          -- 15 files: orchestrators, routing, guards, styling
  think/         -- 16 files: MLX inference, model selection, compression
  speak/         -- 9 files: TTS, voice output, voice settings
  listen/        -- 2 files: voice input, extraction
  see/           -- 11 files: vision, OCR, UI awareness
  remember/      -- 15 files: memory, facts, embeddings, emotional model
  do/            -- 15 files: execution, commands, terminal coordination
  learn/         -- 32 files: training, evolution, feedback, self-improvement
  projects/      -- 4 files: project registry, code indexing, status
  serve/         -- 5 files: API, CLI, daemon, notifications
```

### Pre-Reorganization Cleanup (Do First)

1. **Archive 93 dead files** to `/Volumes/#1/SAM/dead_code_archive/` with manifest
2. **Remove `cognitive/code_indexer.py`** (root version is superset)
3. **Consolidate `VisionTier` enum** into a single `vision_types.py`
4. **Break 7 circular dependency cycles** before moving anything
5. **Extract `cognitive/__init__.py` barrel exports** into per-package `__init__.py` files in the new structure
6. **Remove all 38 `sys.path.insert` hacks** -- replace with proper package structure and editable install (`pip install -e .`)
7. **Split `sam_api.py`** into route modules before moving to `serve/`

### Post-Reorganization

1. Update 5 launchd plists with new paths
2. Update 5 shell scripts with new paths
3. Update Tauri Rust backend hardcoded Python paths
4. Replace Ollama references in Tauri with MLX/sam_api calls
5. Run full import verification script

---

## 7. RISKS DURING MIGRATION

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Breaking sam_api.py (always running via launchd)** | CRITICAL | Stop launchd services before migration. Test thoroughly before re-enabling. |
| **cognitive/__init__.py re-exports 160+ symbols** | HIGH | Map every `from cognitive import X` usage before dissolving the package. Create compatibility shims. |
| **122 import statements need updating** | HIGH | Use `sed` or AST-based rewriter. Verify with `python -c "import X"` for each module. |
| **7 circular dependency cycles** | HIGH | Must be broken BEFORE moving files, not during. |
| **Hardcoded paths (50+ locations)** | HIGH | Create `sam_brain/config.py` with `SAM_MEMORY_DIR`, `SAM_MODELS_DIR`, etc. Centralize all path definitions. |
| **External drive may be unmounted during migration** | MEDIUM | Verify drive is mounted before starting. Migration will take 2-4 hours. |
| **Tauri app integration** | MEDIUM | The Rust backend calls sam_brain via HTTP (port 8765) and subprocess. HTTP calls are path-agnostic. Subprocess calls to specific .py files need updating. |
| **5 launchd plists reference absolute paths** | MEDIUM | Update plists LAST, after all files are in place and tested. |
| **No tests for many modules** | MEDIUM | Only 18 test files exist for 172 source files. Many moves cannot be verified by tests. Manual smoke testing required. |
| **Perpetual learner state** | LOW | `.perpetual_state.json` (1MB) tracks learning progress. Back it up before migration. |

---

## 8. ORDER OF OPERATIONS

### Phase 0: Safety Net (Do Immediately)
1. `git add -A && git commit -m "Pre-reorganization snapshot"` -- get EVERYTHING into git
2. `git push origin main` -- get it to GitHub
3. Back up all SQLite databases: `rsync` all `.db` files to `/Volumes/David External/sam_backup_$(date +%Y%m%d)/`
4. Back up `.perpetual_state.json` and other state files
5. Export list of running launchd services: `launchctl list | grep sam`

### Phase 1: Clean Dead Code (Low Risk)
1. Archive 93 dead files to `/Volumes/#1/SAM/dead_code_archive/`
2. Update manifest.md in the archive
3. Verify sam_api.py still starts: `python3 sam_api.py server 8765`
4. Commit: "Archive 93 dead/orphan files"

### Phase 2: Fix Duplicates (Low Risk)
1. Remove `cognitive/code_indexer.py`, update imports to root `code_indexer`
2. Consolidate `VisionTier` enum into shared module
3. Archive `training_pipeline.py` (keep `training_runner.py`)
4. Verify and commit

### Phase 3: Fix Critical Bugs (Medium Risk)
1. Fix shell injection in `sam_agent.py` (replace `shell=True`)
2. Fix path traversal in `sam_api.py` static file serving
3. Fix unclosed file handles (20+ locations, use `with` statements)
4. Add thread-safe locks to `FactMemory` and other critical singletons
5. Test each fix individually, commit incrementally

### Phase 4: Break Circular Dependencies (Medium Risk)
1. Fix `compression.py` -> `sam_api` circular import (extract shared constants)
2. Fix `query_decomposer` <-> `code_indexer` cycle
3. Fix remaining 5 cycles
4. Verify with `python -c "import X"` for each affected module
5. Commit

### Phase 5: Split sam_api.py (High Risk)
1. Stop launchd service: `launchctl unload ~/Library/LaunchAgents/com.sam.api.plist`
2. Extract route handlers into separate modules (vision_routes, voice_routes, etc.)
3. Keep sam_api.py as thin entry point importing route modules
4. Test all API endpoints
5. Restart launchd, commit

### Phase 6: Reorganize Directory Structure (High Risk)
1. Stop ALL launchd services
2. Create new package directories with `__init__.py` files
3. Move files in dependency order (leaves first, roots last):
   - `remember/` first (fewest inbound dependencies)
   - `see/` second
   - `speak/` and `listen/` third
   - `think/` fourth
   - `do/` fifth
   - `learn/` sixth
   - `core/` seventh
   - `serve/` last (entry points)
4. Update all imports (122 statements)
5. Remove `sys.path.insert` hacks (38 instances)
6. Add `setup.py` or `pyproject.toml` for editable install
7. Run full import verification
8. Update launchd plists
9. Update shell scripts
10. Restart services, smoke test ALL capabilities
11. Commit

### Phase 7: Tauri Cleanup (Low Risk, Separate Track)
1. Remove Ollama commands from Rust backend
2. Update any subprocess calls to sam_brain Python files
3. Rebuild Tauri app
4. Test frontend-to-backend integration

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Python files | 172 |
| Total lines of code | ~144,255 |
| Active files (reachable from entry points) | 72 |
| Dead/orphan files | 93 |
| Daemon-only files | 2 |
| Vision-only files | 1 |
| CLI-only files | 4 |
| Critical security issues | 3 |
| High security issues | 4 |
| Databases (unprotected, no backup) | 15+ |
| Circular dependency cycles | 7 |
| Files over 1,000 lines | 45 |
| Hardcoded external drive paths | 50+ |
| sys.path.insert hacks | 38 |
| Estimated removable dead code | ~40,000 lines |
| Estimated removable duplicate code | ~5,800 lines |
| Import statements to update for reorg | 122 |
| Launchd services to update | 5 |
