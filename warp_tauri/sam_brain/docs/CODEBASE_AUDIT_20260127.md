# SAM Ecosystem Codebase Audit

**Date:** 2026-01-27
**Scope:** Full ecosystem -- sam_brain (Python), warp_tauri frontend (Vue/TypeScript), warp_tauri backend (Rust), scrapers, external projects
**Auditor:** Claude Code deep dive session with David

---

## 1. Executive Summary

The SAM ecosystem has accumulated significant technical debt across all layers. Key findings:

- **241 Python files** in sam_brain, roughly 15% documented
- **114 Vue composables** in the frontend, approximately 40 unused
- **70 Rust scaffolding modules** in the backend, unclear how many are active
- **55 dead scripts** in the warp_tauri root directory
- **Multiple conflicting/duplicate systems** for orchestration, memory, learning, and token budgeting
- **Ollama still referenced** in the Rust backend module (ollama.rs) and 25+ frontend composables despite being decommissioned on 2026-01-18
- **FIXED (2026-01-27):** Pre-warm call in main.rs replaced with MLX/sam_api health check (port 8765)
- **FIXED (2026-01-27):** perpetual_learner.py NameError on line 925 (ResourceManager constant import)

The codebase works but carries roughly 12,000+ lines of dead Python code, dozens of orphaned scripts, and several database duplicates that create real risk of data corruption.

---

## 2. sam_brain Dead Code

### 2.1 Dead Orchestrators (4 files)

| File | Lines | Issue |
|------|-------|-------|
| `native_hub.py` | -- | Declares itself "Master entry point" but is never imported by any other file. Self-referential only. |
| `sam_parity_orchestrator.py` | -- | Never imported anywhere in the codebase. |
| `unified_orchestrator.py` (root) | -- | Confusing duplicate of `cognitive/unified_orchestrator.py`. The root version is mostly dead code. |
| `claude_orchestrator.py` | -- | Only imported by `overnight_runner.py`, which itself may be inactive. |

### 2.2 Dead Learners (6 files, ~4,514 lines)

| File | Lines | Issue |
|------|-------|-------|
| `terminal_learning.py` | 901 | Not imported by anything. No launchd plist. |
| `exhaustive_learner.py` | 954 | 90% overlaps `perpetual_learner.py`. Associated 67MB dead database. |
| `efficient_learning.py` | 877 | Not imported by anything. |
| `overnight_learner.py` | 585 | Not imported by anything. |
| `parallel_learn.py` | 541 | 70% overlaps `perpetual_learner.py`. |
| `teacher_student.py` | 656 | Not imported by anything. |

All six learners appear to be earlier iterations of what became `auto_learner.py` and `perpetual_learner.py`. They share similar patterns (scrape/learn/store loops) but none are wired into the active system.

### 2.3 Dead Experiments (10 files, ~7,693 lines)

| File | Lines | Purpose (abandoned) |
|------|-------|---------------------|
| `advanced_planner.py` | 792 | Task planning system |
| `ui_verifier.py` | 926 | UI verification automation |
| `cutting_edge.py` | 767 | Experimental AI techniques |
| `reverse_engineering_strategy.py` | 851 | RE approach planning |
| `legitimate_extraction.py` | 856 | Data extraction methods |
| `apple_native_focus.py` | 786 | Apple ecosystem integration |
| `app_validator.py` | 798 | App validation pipeline |
| `accelerate.py` | 638 | Performance optimization |
| `app_store_builder.py` | 699 | App Store submission |
| `audio_tester.py` | 580 | Audio pipeline testing |

None of these files are imported by any active module. They represent exploration branches that were never integrated.

**Total dead Python code in sam_brain: ~12,207+ lines across 20 files.**

---

## 3. Conflicting and Duplicate Systems

### 3.1 Orchestrators (9 total, only 2 active)

| File | Status | Notes |
|------|--------|-------|
| `cognitive/unified_orchestrator.py` | **ACTIVE** | The real orchestrator. Called via escalation_handler from sam_api.py. |
| `orchestrator.py` | LEGACY FALLBACK | Used by sam_api.py only as a fallback path. |
| `re_orchestrator.py` | STANDALONE | Reverse engineering tool. Should live in tools/. |
| `multi_role_orchestrator.py` | STANDALONE | Multi-Claude coordination tool. |
| `system_orchestrator.py` | STANDALONE | Scraper/ARR service control. |
| `claude_orchestrator.py` | NEAR-DEAD | Only used by overnight_runner.py. |
| `sam_parity_orchestrator.py` | **DEAD** | Never imported. |
| `unified_orchestrator.py` (root) | **DEAD** | Confusing name collision with the active cognitive/ version. |
| `native_hub.py` | **DEAD** | Self-referential, never imported. |

**Recommendation:** Delete the 3 dead files. Move standalone tools into a `tools/` subdirectory. Rename or remove the root `unified_orchestrator.py` to eliminate confusion.

### 3.2 Memory and Context Systems (10 files, significant overlap)

**Token Budget -- 3 competing systems:**
- `context_budget.py` -- one implementation
- `cognitive/token_budget.py` -- another implementation
- `context_manager.py` -- superseded by context_budget.py

Only one should be active. If multiple are being called, they could give conflicting token allocations, leading to context window overflows or underutilization.

**Fact Storage -- 2 competing systems:**
- `fact_memory.py` -- structured facts with its own Fact schema
- `conversation_memory.py` -- contains a separate, incompatible Fact schema

Both define a "Fact" concept but store them differently. This means facts could be split across two databases with no cross-reference.

**Duplicate Databases:**
- `procedural.db` exists at both `/sam_memory/` and `/sam_memory/cognitive/`
- `decay.db` may also exist in multiple locations
- Writes could go to the wrong copy depending on which module is called

**Dead context modules:**
- `infinite_context.py` (1,101 lines) -- imported by nothing
- `context_manager.py` -- superseded by `context_budget.py`

### 3.3 Learners (11 files, only 3 active)

| Status | Files |
|--------|-------|
| **ACTIVE (daemon)** | `auto_learner.py`, `perpetual_learner.py` |
| **ACTIVE (library)** | `sam_intelligence.py` |
| **PARTIAL** | `claude_learning.py` (80% overlaps auto_learner) |
| **DEAD** | `terminal_learning.py`, `exhaustive_learner.py`, `efficient_learning.py`, `overnight_learner.py`, `parallel_learn.py`, `teacher_student.py` |
| **UNUSED EXPORT** | `cognitive/enhanced_learning.py` (exported but never called) |

---

## 4. Warp Tauri Frontend Issues

### 4.1 Dead Scripts in warp_tauri Root (55 files)

These scripts sit in the project root and are not part of any build or runtime system:

**ChatGPT Browser Automation (~20 files):**
- `.cjs` and `.js` files for automating ChatGPT in the browser
- `chatgpt_bridge.py`, `bridge_daemon.py`
- `mitm_chatgpt_intercept.py`, `list_all_chatgpt_windows.py`
- Various browser automation helpers

**Frida Reverse Engineering (~10 files):**
- Frida injection/hooking scripts
- Likely from the reverse engineering exploration phase

**Screen Scraping:**
- `screen_scraper.py`, `screen_scraper_vision.py`

**Miscellaneous dead bridges and automation scripts.**

All of these predate the current architecture and serve no active purpose. They clutter the project root and create confusion about what the project actually does.

### 4.2 Unused Composables (~40 of 114)

The following Vue composables exist in the frontend but are not wired into any active component:

```
useAccountAnonymizer     useBackgroundTasks       useBrowserAutomation
useCalendar              useCharacterCustomization useClipboardHistory
useCodebaseEmbeddings    useCollaboration         useContainers
useDaemonOrchestrator    useEmailCleaner          useImageUnderstanding
useKernelManager         useLSP                   useNextCommandPrediction
useNotebook              usePerformance           usePermissionModes
useProactiveNotifications usePromptTemplates      useRecording
useRelationships         useRemoteAgent           useSettingsSync
useSmartCommands         useSubAgents             useUniversalMemory
useVisualUnderstanding   useVoiceInterface        useWakeWord
useWarpDrive             useWorkflows
```

Additionally, 2 `.bak` files exist alongside the composables.

These represent aspirational features that were scaffolded but never completed. They add to bundle size and IDE clutter.

### 4.3 Ollama Still Active in Frontend

Despite Ollama being decommissioned on 2026-01-18:

- **25+ composables** still invoke `query_ollama` Tauri commands
- These calls will silently fail or error at runtime
- No graceful fallback to MLX in most of these composables

---

## 5. Rust Backend Issues

### 5.1 Ollama Still Live in Backend

| Item | Detail |
|------|--------|
| `ollama.rs` | 268 lines, fully imported in `main.rs` |
| Tauri commands registered | `query_ollama`, `query_ollama_stream`, `query_ollama_chat`, `list_ollama_models`, `prewarm_model` |
| Startup behavior | `main.rs` pre-warms `sam-trained:latest` on every app launch |
| Problem | The model `sam-trained:latest` does not exist. Ollama itself is decommissioned. |
| Scaffolding | `scaffolding/ollama_agent.rs` also exists |

**This is the highest-priority fix.** The pre-warm call runs on every app startup, attempting to connect to a service that should not be running, for a model that does not exist.

### 5.2 Backend Bloat

| Item | Detail |
|------|--------|
| `commands.rs` | 7,091 lines / 258KB -- monolithic command file |
| Scaffolding modules | 70 Rust modules in scaffolding/ |
| Dead modules | `agents.rs`, `phase1_6_tests.rs`, `policy_store.rs`, `plan_store.rs` |

The `commands.rs` file should be split into logical modules (conversation commands, memory commands, system commands, etc.) for maintainability.

---

## 6. Dead Directories

| Directory | Date | Purpose | Status |
|-----------|------|---------|--------|
| `warp_phase1_6_bundle/` | Nov 2025 | Complete old project version | Fully superseded. Safe to archive. |
| `phase4_trainer/` | Nov 2025 | Experimental ML training | Superseded by current training pipeline. |
| `character_pipeline/` | Dec 2025 | Future 3D character system | Not integrated. Separate project exists at `~/Projects/character-pipeline/`. |

These directories consume disk space on the internal drive and should be moved to `/Volumes/David External/` per the storage strategy.

---

## 7. Active Breakage Risks

### Risk 1: Ollama Pre-warm on Startup (SEVERITY: HIGH)
- `main.rs` calls `prewarm_model("sam-trained:latest")` on every app launch
- Ollama is decommissioned, the model does not exist
- This likely causes a timeout or error on every startup, slowing launch
- **Fix:** Remove the pre-warm call and the Ollama Tauri command registrations from main.rs

### Risk 2: Duplicate Databases (SEVERITY: MEDIUM)
- `procedural.db` exists at both `/sam_memory/` and `/sam_memory/cognitive/`
- `decay.db` may also be duplicated
- Different modules may read/write to different copies
- **Fix:** Consolidate to a single canonical location, update all imports

### Risk 3: Three Token Budget Systems (SEVERITY: MEDIUM)
- `context_budget.py`, `cognitive/token_budget.py`, and `context_manager.py` all manage token allocation
- If multiple are active simultaneously, they could give conflicting allocations
- **Fix:** Verify which one the active orchestrator uses, deprecate the others

### Risk 4: perpetual_learner.py NameError (SEVERITY: HIGH) -- FIXED 2026-01-27
- Line 925 referenced `MIN_FREE_RAM_GB`, `MAX_SWAP_USED_GB`, `MIN_DISK_FREE_GB` which no longer existed in the file
- The training scheduler thread crashed on startup with a `NameError`
- perpetual_learner was running (PID existed) but its training loop was dead
- **Fixed:** Added import of the correct constants from `cognitive.resource_manager`
- **Status:** Verified working after restart

### Risk 5: Dead Learner Databases (SEVERITY: LOW)
- `exhaustive_learner.py` left behind a 67MB+ database
- Other dead learners may have their own databases
- **Fix:** Archive databases to external storage, delete dead learner files

---

## 8. Cleanup Priority Tiers

### Tier 1 -- Fix Active Breakage (Do First)

| Task | Impact | Effort |
|------|--------|--------|
| Remove Ollama pre-warm from `main.rs` | Fixes startup error | 10 min |
| Consolidate duplicate databases (procedural.db, decay.db) | Prevents data corruption | 30 min |
| Verify which token budget system is active, disable others | Prevents conflicting allocations | 20 min |

### Tier 2 -- Remove Dead Code in sam_brain

| Task | Lines Removed | Effort |
|------|---------------|--------|
| Delete 6 dead learners | ~4,514 | 15 min |
| Delete 4 dead orchestrators | ~varies | 10 min |
| Delete 10 dead experiments | ~7,693 | 15 min |
| Archive associated databases to external | frees 67MB+ | 10 min |
| Remove `infinite_context.py` | 1,101 | 5 min |

### Tier 3 -- Clean warp_tauri

| Task | Files Removed | Effort |
|------|---------------|--------|
| Delete 20+ ChatGPT browser automation scripts | ~20 | 15 min |
| Delete ~10 Frida RE scripts | ~10 | 10 min |
| Remove `ollama.rs` and all frontend Ollama calls | 25+ files touched | 1 hour |
| Audit and remove ~40 unused composables | ~40 | 30 min |
| Remove 2 `.bak` files | 2 | 2 min |
| Delete remaining dead root scripts | ~15 | 10 min |

### Tier 4 -- Archive Old Projects

| Task | Space Freed | Effort |
|------|-------------|--------|
| Move `warp_phase1_6_bundle/` to external | varies | 10 min |
| Move `phase4_trainer/` to external | varies | 10 min |
| Evaluate `character_pipeline/` (may keep if active project) | varies | 5 min |

---

## 9. What Is Actually Active (The Real Architecture)

This section documents what is actually running and should NOT be touched during cleanup.

### 9.1 Entry Points

```
sam_api.py (port 8765)
  --> escalation_handler
    --> cognitive/unified_orchestrator.py
    --> (fallback) orchestrator.py

auto_learner.py        (launchd daemon - continuous learning)
perpetual_learner.py   (launchd daemon - continuous learning)
scraper_daemon.py      (launchd daemon - data collection)
```

### 9.2 Active Python Core (sam_brain)

**Cognitive Engine (`cognitive/` directory, 15+ modules):**
- MLX inference engine
- Vision processing
- Memory management
- Context compression
- Unified orchestration

**Memory Systems:**
- `semantic_memory.py` -- vector embeddings (MLX MiniLM-L6-v2)
- `fact_memory.py` -- structured fact storage

**Voice Pipeline:**
- `voice_pipeline.py` -- main voice processing
- `voice_*.py` -- supporting voice modules

**Training Infrastructure:**
- `training_pipeline.py` -- main training orchestration
- `training_*.py` -- supporting training modules

**Specialized:**
- `emotion2vec_mlx/` -- emotion detection from audio
- `sam_intelligence.py` -- core intelligence module

### 9.3 Active Frontend (Vue/TypeScript)

- ~40 Vue components that are actually wired into the UI
- ~70 composables that are actually imported and used
- 3 Pinia stores (clean, no issues found)
- Standard Tauri IPC bridge to Rust backend

### 9.4 Active Backend (Rust)

**Core modules:**
- `brain.rs` -- main brain/inference integration
- `commands.rs` -- Tauri command handlers (needs splitting but is active)
- `autonomous.rs` -- autonomous behavior
- `conversation.rs` -- conversation management

**Scaffolding core (active subset of 70 modules):**
- `smart_orchestrator` -- intelligent task routing
- `hybrid_router` -- model selection
- `character_library` -- personality/character management

---

## 10. Database Inventory

| Database | Location | Status | Notes |
|----------|----------|--------|-------|
| `procedural.db` | `/sam_memory/` | Active (?) | May conflict with cognitive/ copy |
| `procedural.db` | `/sam_memory/cognitive/` | Active (?) | Duplicate -- needs consolidation |
| `decay.db` | `/sam_memory/` | Active | Memory decay system |
| `semantic.db` | `/sam_memory/` | Active | Vector embeddings |
| `facts.db` | `/sam_memory/` | Active | Structured facts |
| `exhaustive_learner.db` | `/sam_memory/` | **DEAD** | 67MB, from dead learner |
| Various learner DBs | scattered | **DEAD** | From dead learner scripts |

---

## 11. Recommendations for Future Sessions

1. **Before writing any new module**, check this audit to avoid creating yet another duplicate system.
2. **All inference must use MLX**, not Ollama. If you see Ollama references, they are dead code.
3. **The canonical orchestrator is `cognitive/unified_orchestrator.py`**. All others are either standalone tools or dead.
4. **The canonical entry point is `sam_api.py` on port 8765.** It calls escalation_handler which calls the cognitive orchestrator.
5. **Active daemons are managed by launchd.** Check `~/Library/LaunchAgents/` for the actual plist files to confirm what runs.
6. **Storage rule applies**: Never write large files to internal SSD. Models, training data, and archives go to `/Volumes/David External/`.
7. **Do not delete files without David's explicit permission.** This audit identifies what CAN be deleted, but the decision is David's.
8. **On David External, folders prefixed with `_` are older personal content** (music, photos, documents, courses, etc.). Folders WITHOUT `_` are newer coding/SAM-related work.
9. **Fashion training data (117GB) is on /Volumes/#1/**: `wwd_archive/` (48GB), `wmag_archive/` (40GB), `vmag_archive/` (29GB). Previous sessions failed to find this. It will be used for LLM training AND other projects.
10. **SAM is blind to many projects.** CalCareers, Account Automation, Topaz Parity, Muse, and media tools all exist but have no orchestrator routing. Check `STORAGE_AND_DATA_MAP_20260127.md` for the full project inventory.
11. **See `STORAGE_AND_DATA_MAP_20260127.md`** for the complete drive-by-drive inventory, training data map, and project integration status.

---

## 12. File Counts Summary

| Category | Total | Active | Dead/Unused |
|----------|-------|--------|-------------|
| Python files (sam_brain) | 241 | ~80-100 | ~140-160 |
| Vue composables | 114 | ~70 | ~40 |
| Rust scaffolding modules | 70 | ~10-15 | ~55-60 |
| Root scripts (warp_tauri) | 55 | 0 | 55 |
| Orchestrator files | 9 | 2 | 4 dead + 3 standalone |
| Learner files | 11 | 3 | 6 dead + 1 partial + 1 unused |

---

*This audit was generated during a deep dive session on 2026-01-27. It should be updated after any major cleanup operation.*
*Next recommended action: Tier 1 fixes (Ollama pre-warm removal, database consolidation, token budget verification).*
