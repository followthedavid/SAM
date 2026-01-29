# Migration Impact Analysis: sam_brain/ Reorganization

**Generated:** 2026-01-29
**Scope:** Reorganize 124 Python files from flat/legacy layout into `core/`, `think/`, `speak/`, `listen/`, `see/`, `remember/`, `do/`, `learn/`, `projects/`, `serve/`
**Risk Level:** HIGH - 7 circular dependency cycles, 122 import statements to update, 93 cross-module edges

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [File-by-File Move Impact](#2-file-by-file-move-impact)
3. [Total Import Statements Needing Update](#3-total-import-statements-needing-update)
4. [Files That CANNOT Be Moved Safely](#4-files-that-cannot-be-moved-safely)
5. [Safest Migration Order](#5-safest-migration-order)
6. [Circular Dependencies](#6-circular-dependencies)
7. [Hardcoded Paths](#7-hardcoded-paths)
8. [Unmapped Files and Directories](#8-unmapped-files-and-directories)
9. [The cognitive/__init__.py Problem](#9-the-cognitive-init-problem)
10. [Recommended Strategy](#10-recommended-strategy)

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| Total files to move | 124 |
| Cross-module import edges | 93 |
| Total import statements to update | 122 |
| Circular dependency cycles | 7 |
| Hardcoded path locations | 26+ |
| Shell scripts with hardcoded paths | 5 |
| Launchd plists with hardcoded paths | 2 |
| Files per target directory | see breakdown below |
| Existing packages to dissolve | 4 (cognitive/, memory/, execution/, voice/) |
| `sys.path.insert` hacks to fix | 38 |
| `cognitive/__init__.py` exports | 160+ symbols from 20 submodules |

**Files per target directory:**

| Directory | Files | Purpose |
|-----------|-------|---------|
| `core/` | 15 | Central routing, orchestrators, guards |
| `think/` | 16 | MLX inference, model selection, compression |
| `speak/` | 9 | TTS, voice output, voice settings |
| `listen/` | 2 | Voice input, extraction |
| `see/` | 11 | Vision, OCR, UI awareness |
| `remember/` | 15 | Memory, facts, embeddings, emotional model |
| `do/` | 15 | Execution, commands, terminal coordination |
| `learn/` | 32 | Training, evolution, feedback, self-improvement |
| `projects/` | 4 | Project registry, code indexing, status |
| `serve/` | 5 | API, CLI, daemon, notifications |

---

## 2. File-by-File Move Impact

### core/ (Central Routing) -- 15 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `orchestrator.py` | `sam_api.py`, `test_evolution_system.py`, `test_suite.py`, `execution/safe_executor.py` | 4 `from orchestrator import` / `import orchestrator` statements |
| `smart_router.py` | `sam_chat.py`, `execution/escalation_handler.py` | 2 imports |
| `re_orchestrator.py` | `orchestrator.py` | 1 import |
| `system_orchestrator.py` | (no internal importers found) | Low risk |
| `unified_orchestrator.py` (root) | (no internal importers found) | Low risk, but has `Path(__file__).parent` for db paths |
| `sam.py` | (no internal importers found) | Low risk |
| `sam_agent.py` | `sam_enhanced.py` | 1 import |
| `sam_enhanced.py` | `sam_api.py` | 1 import |
| `intelligence_core.py` | `sam_api.py`, `execution/escalation_handler.py` | 2 imports |
| `response_styler.py` | `orchestrator.py` | 1 import |
| `thinking_verbs.py` | `orchestrator.py` | 1 import |
| `thought_logger.py` | `orchestrator.py` | 1 import |
| `narrative_ui_spec.py` | `orchestrator.py` | 1 import |
| `privacy_guard.py` | `orchestrator.py`, `conversation_logger.py` | 2 imports |
| `transparency_guard.py` | `orchestrator.py` | 1 import |

### think/ (LLM Inference) -- 16 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `mlx_inference.py` | `sam_chat.py`, `memory/infinite_context.py` | 2 imports |
| `cognitive/mlx_cognitive.py` | `orchestrator.py`, `live_thinking.py`, `sam_api.py`, `cognitive/__init__.py` | 3 external + relative imports |
| `cognitive/mlx_optimized.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/model_selector.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/model_evaluation.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/token_budget.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/quality_validator.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/resource_manager.py` | `auto_learner.py`, `perpetual_learner.py`, `tts_pipeline.py`, `sam_api.py`, `cognitive/__init__.py` | 4 external + relative imports |
| `cognitive/compression.py` | `sam_api.py`, `cognitive/__init__.py` | 1 external + relative. **CIRCULAR: imports sam_api** |
| `cognitive/cognitive_control.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/planning_framework.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/multi_agent_roles.py` | `cognitive/__init__.py` | Relative imports only |
| `live_thinking.py` | `orchestrator.py`, `sam_api.py` | 2 imports |
| `multi_agent.py` | `sam_enhanced.py` | 1 import |
| `query_decomposer.py` | `code_indexer.py`, tests | 1 import. **CIRCULAR with code_indexer.py** |
| `smart_summarizer.py` | (no internal importers found) | Low risk |

### speak/ (Voice Output) -- 9 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `tts_pipeline.py` | (no internal importers found) | Low risk |
| `voice/voice_output.py` | `sam_api.py`, tests | 2+ imports via `voice.voice_output` |
| `voice/voice_settings.py` | tests | Tests use `voice.voice_settings` |
| `voice/voice_server.py` | (no internal importers found) | Has `Path(__file__).parent` for cache/static dirs |
| `voice/voice_cache.py` | `tts_pipeline.py`, `voice/__init__.py` | 1 import |
| `voice/voice_pipeline.py` | `sam_api.py`, `voice/__init__.py` | 1 import. **Imports conversation_engine** |
| `voice/voice_bridge.py` | `sam_enhanced.py`, `voice/__init__.py` | 1 import |
| `voice/voice_preprocessor.py` | tests | Tests use `voice.voice_preprocessor` |
| `audio_utils.py` | `voice/voice_extraction_pipeline.py` | 1 import |

### listen/ (Voice Input) -- 2 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `voice/voice_trainer.py` | `orchestrator.py`, `voice/__init__.py` | 1 import via `voice.voice_trainer` |
| `voice/voice_extraction_pipeline.py` | `voice/__init__.py` | Relative import. Imports `audio_utils` (moving to speak/) |

### see/ (Vision) -- 11 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `cognitive/vision_engine.py` | `cognitive/__init__.py`, tests | Relative imports. Has `Path(__file__).parent.parent.parent` for bridge path |
| `cognitive/vision_client.py` | `cognitive/__init__.py`, tests | Relative imports from vision_engine, smart_vision |
| `cognitive/vision_selector.py` | `cognitive/__init__.py` | Relative import from resource_manager (moving to think/) |
| `cognitive/smart_vision.py` | `sam_api.py`, tests | Imports `execution.escalation_handler` (do/) and `apple_ocr` (see/) |
| `cognitive/image_preprocessor.py` | `cognitive/__init__.py` | Relative imports only |
| `apple_ocr.py` | `sam_api.py`, `cognitive/smart_vision.py` | 2 imports |
| `vision_server.py` | (no internal importers found) | Low risk |
| `cognitive/ui_awareness.py` | (no internal importers found) | Low risk |
| `cognitive/app_knowledge_extractor.py` | (no internal importers found) | Low risk |
| `image_generator.py` | `orchestrator.py` | 1 import |
| `comfyui_client.py` | `orchestrator.py` | 1 import |

### remember/ (Memory) -- 15 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `memory/semantic_memory.py` | `improvement_detector.py`, `sam_enhanced.py`, `sam_intelligence.py`, `project_status.py`, tests | 5+ imports via `memory.semantic_memory` |
| `memory/conversation_memory.py` | `memory/__init__.py`, tests | Package-internal + tests |
| `memory/fact_memory.py` | `cognitive/self_knowledge_handler.py`, `cognitive/unified_orchestrator.py`, `sam_api.py`, tests | 3+ external imports |
| `memory/context_budget.py` | `sam_api.py`, tests | 1 external import |
| `memory/infinite_context.py` | `memory/__init__.py` | Imports `mlx_inference` (moving to think/) |
| `memory/project_context.py` | `cognitive/unified_orchestrator.py`, `sam_api.py` | 2 external imports. Has hardcoded INVENTORY_PATH |
| `memory/rag_feedback.py` | `memory/__init__.py` | Package-internal only |
| `cognitive/enhanced_memory.py` | `cognitive/__init__.py`, `cognitive/unified_orchestrator.py` | Relative imports |
| `cognitive/enhanced_retrieval.py` | `cognitive/__init__.py`, `cognitive/unified_orchestrator.py` | Imports `relevance_scorer` (also remember/) |
| `cognitive/enhanced_learning.py` | `cognitive/__init__.py`, `cognitive/unified_orchestrator.py` | Relative imports |
| `cognitive/emotional_model.py` | `cognitive/__init__.py`, `cognitive/unified_orchestrator.py` | Relative imports |
| `cognitive/personality.py` | `cognitive/__init__.py` | Relative imports only |
| `cognitive/self_knowledge_handler.py` | `cognitive/__init__.py`, tests | Imports `memory.fact_memory` |
| `conversation_logger.py` | `orchestrator.py` | 1 import. Imports `privacy_guard` (core/) |
| `relevance_scorer.py` | `cognitive/__init__.py`, `cognitive/enhanced_retrieval.py` | 2 imports |

### do/ (Execution) -- 15 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `execution/safe_executor.py` | `execution/__init__.py`, tests | **Imports orchestrator (core/) -- CIRCULAR** |
| `execution/command_classifier.py` | `execution/__init__.py`, `execution/command_proposer.py`, tests | 1 internal import |
| `execution/command_proposer.py` | `execution/__init__.py` | Imports `execution.command_classifier` |
| `execution/auto_fix.py` | `execution/__init__.py`, tests | Has `Path(__file__).parent` = execution/ dir |
| `execution/auto_fix_control.py` | `execution/__init__.py`, tests | **Imports proactive_notifier (serve/)** |
| `execution/escalation_handler.py` | `claude_orchestrator.py`, `sam_api.py`, `sam_chat.py`, `cognitive/smart_vision.py` | 4 external importers. Imports `intelligence_core` (core/), `knowledge_distillation` (learn/), `smart_router` (core/), `cognitive` package |
| `execution/escalation_learner.py` | `execution/__init__.py`, `sam_api.py`, `execution/escalation_handler.py` | 2 external imports |
| `execution/execution_history.py` | `execution/__init__.py`, tests | Package-internal |
| `approval_queue.py` | `sam_api.py` | 1 import |
| `project_permissions.py` | tests | Tests only |
| `tool_system.py` | `sam_parity_orchestrator.py` | 1 import. Has `Path(__file__).parent` |
| `terminal_coordination.py` | `orchestrator.py`, `auto_coordinator.py`, `terminal_learning.py`, `test_suite.py` | 4 imports |
| `terminal_sessions.py` | (no internal importers found) | Low risk |
| `terminal_learning.py` | (no internal importers found as an import target) | Imports `terminal_coordination` |
| `auto_coordinator.py` | `orchestrator.py`, `test_suite.py` | 2 imports |

### learn/ (Self-Improvement) -- 32 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `evolution_tracker.py` | `evolution_ladders.py`, `improvement_detector.py`, `orchestrator.py`, `project_dashboard.py`, `project_status.py`, `sam_intelligence.py`, `ssot_sync.py`, `test_evolution_system.py`, `test_suite.py` | **9 importers** -- HIGHEST IMPACT FILE |
| `evolution_ladders.py` | `orchestrator.py`, `project_dashboard.py`, `project_status.py`, `sam_intelligence.py`, `test_evolution_system.py`, `test_suite.py` | **6 importers** |
| `improvement_detector.py` | `orchestrator.py`, `project_status.py`, `sam_api.py`, `sam_intelligence.py`, `test_evolution_system.py`, `test_suite.py` | **6 importers**. Imports `memory.semantic_memory` (remember/) |
| `feedback_system.py` | `proactive_notifier.py`, `sam_api.py`, `training_capture.py` | 3 importers |
| `knowledge_distillation.py` | `execution/escalation_handler.py`, `sam_api.py` | 2 importers |
| `training_pipeline.py` | `sam_api.py`, tests | 1 import |
| `training_data.py` | `training_capture.py` | 1 import |
| `training_data_collector.py` | `training_scheduler.py`, tests | 1 import |
| `training_capture.py` | (no internal importers found) | Low risk |
| `training_runner.py` | (no internal importers found) | Low risk |
| `training_scheduler.py` | (no internal importers found) | Imports `unified_daemon` (serve/) |
| `training_prep.py` | (no internal importers found) | Low risk |
| `training_stats.py` | tests | Tests only |
| `claude_learning.py` | `sam_parity_orchestrator.py` | 1 import |
| `impact_tracker.py` | `orchestrator.py` | 1 import |
| `data_quality.py` | (no internal importers found) | Imports `deduplication` (also learn/) |
| `deduplication.py` | `data_quality.py` | 1 import |
| `data_arsenal.py` | `orchestrator.py`, `test_suite.py` | 2 imports |
| `auto_learner.py` | (no internal importers found) | Imports `cognitive.resource_manager` (think/) |
| `auto_validator.py` | (no internal importers found) | Low risk |
| `perpetual_learner.py` | (no internal importers found) | Imports `cognitive.resource_manager` (think/) |
| `parallel_learn.py` | (no internal importers found) | Low risk |
| `sam_intelligence.py` | `orchestrator.py`, `sam_api.py`, `test_suite.py` | 3 imports |
| `model_deployment.py` | `sam_api.py`, tests | 1 import |
| `doc_ingestion.py` | (no internal importers found) | Low risk |
| `legitimate_extraction.py` | (no internal importers found) | Low risk |
| `parity_system.py` | `sam_parity_orchestrator.py` | 1 import |
| `sam_parity_orchestrator.py` | (no internal importers found) | Imports from learn/ internals |
| `cognitive/code_indexer.py` | `cognitive/__init__.py`, `sam_api.py` | 1 external import |
| `cognitive/code_pattern_miner.py` | (no internal importers found) | Low risk |
| `cognitive/doc_indexer.py` | `cognitive/__init__.py` | Relative import only |
| `cognitive/learning_strategy.py` | `cognitive/__init__.py` | Relative import only |

### projects/ (Project Awareness) -- 4 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `code_indexer.py` (root) | `query_decomposer.py`, tests | 1 import. **CIRCULAR with query_decomposer** |
| `project_dashboard.py` | `orchestrator.py`, `test_suite.py` | 2 imports |
| `project_status.py` | (no internal importers found as target) | Imports many learn/ modules |
| `ssot_sync.py` | `sam_enhanced.py` | 1 import |

### serve/ (External Interfaces) -- 5 files

| Current Location | Imported By | What Breaks |
|-----------------|------------|-------------|
| `sam_api.py` | **cognitive/compression.py** (CIRCULAR), tests | 1 circular import + tests |
| `sam_chat.py` | `sam_repl.py` | 1 import |
| `sam_repl.py` | (no internal importers found) | Low risk - entry point |
| `unified_daemon.py` | `training_scheduler.py` | 1 import |
| `proactive_notifier.py` | `execution/auto_fix_control.py`, `test_new_features.py` | 1 import |

---

## 3. Total Import Statements Needing Update

### Summary

| Category | Count |
|----------|-------|
| Cross-module import edges (file A in dir X imports file B in dir Y) | 93 |
| Same-module imports that change path (e.g., `from cognitive.X` to `from think.X`) | 29 |
| **Total import statements to update** | **122** |
| `sys.path.insert` hacks in codebase | 38 |
| `cognitive/__init__.py` re-exports (must be split or shimmed) | 160+ symbols |
| `memory/__init__.py` re-exports | 30+ symbols |
| `execution/__init__.py` re-exports | 40+ symbols |
| `voice/__init__.py` re-exports | 30+ symbols |

### Breakdown by source module

| From Module | Import Count to Other Modules |
|------------|------------------------------|
| `core/` (orchestrator.py alone) | 22 imports across 8 other modules |
| `serve/` (sam_api.py alone) | 27 imports across 7 other modules |
| `do/` (execution/escalation_handler.py) | 5 imports across 3 modules |
| `learn/` (improvement_detector, sam_intelligence) | 8 imports to remember/ and do/ |
| `think/` (cognitive/compression.py) | 1 circular import to serve/ |
| `projects/` (project_status.py) | 4 imports to learn/ and remember/ |

### The Big Two: orchestrator.py and sam_api.py

These two files are the heart of the problem. They import from nearly every module:

**`orchestrator.py`** imports from: learn/ (7), core/ (6), think/ (2), do/ (1), see/ (2), speak/ (1), projects/ (1), remember/ (1)

**`sam_api.py`** imports from: learn/ (5), think/ (4), remember/ (5), do/ (3), see/ (2), speak/ (2), core/ (3), serve/ (0, it IS serve/)

---

## 4. Files That CANNOT Be Moved Without Breaking Things

### HIGH RISK - Do Not Move Without Compatibility Shims

1. **`cognitive/__init__.py`** -- Re-exports 160+ symbols from 20 submodules. Moving its children to different directories destroys the `from cognitive import X` pattern used across the codebase. Every file that does `from cognitive import MLXCognitiveEngine` or `import cognitive` breaks.

2. **`sam_api.py`** -- 27 internal imports, plus `cognitive/compression.py` imports it back (circular). The central API file. Also referenced in `com.sam.api.plist` launchd config.

3. **`orchestrator.py`** -- 22 internal imports spanning 8 target modules. Most-connected hub file. Imported by 4 other files.

4. **`evolution_tracker.py`** -- Imported by 9 other files. Moving it requires updating all 9.

5. **`execution/__init__.py`** -- Re-exports 40+ symbols. Files import `from execution.auto_fix import X`, `from execution.escalation_handler import Y`, etc.

6. **`memory/__init__.py`** -- Re-exports 30+ symbols. Files import `from memory.semantic_memory import X`, `from memory.fact_memory import Y`, etc.

7. **`voice/__init__.py`** -- Re-exports 30+ symbols from 8 submodules.

### MEDIUM RISK - Move With Care

8. **`terminal_coordination.py`** -- Imported by 4 files
9. **`improvement_detector.py`** -- Imported by 6 files
10. **`evolution_ladders.py`** -- Imported by 6 files
11. **`cognitive/resource_manager.py`** -- Imported by 4 external files
12. **`execution/escalation_handler.py`** -- Imported by 4 external files + imports from 4 other modules

### UNMOVABLE Without Re-architecture

13. **`conversation_engine/`** -- This entire package (4 files: `engine.py`, `events.py`, `state.py`, `turn_predictor.py`) is not mapped to any target directory. `voice/voice_pipeline.py` imports from it. Must be assigned to a target first (likely `speak/` or `core/`).

14. **`cognitive/unified_orchestrator.py`** -- This is different from root `unified_orchestrator.py`. It lives in cognitive/ and is the main cognitive processing engine. It imports from both `memory.project_context` and `memory.fact_memory`. Splitting it between core/ and remember/ is architecturally complex.

---

## 5. Safest Migration Order

### Phase 0: Preparation (No File Moves)
1. Add `__init__.py` compatibility shims in all 10 target directories
2. Ensure `sam_brain/` itself has an `__init__.py` if not present
3. Create a `compat/` directory with re-export shims for old paths

### Phase 1: Leaf Modules (No Dependents)
These files are imported by nothing or only by tests. Move these first.

```
Order  File                              Target    Risk
-----  ----                              ------    ----
1.1    smart_summarizer.py               think/    NONE
1.2    system_orchestrator.py            core/     NONE
1.3    terminal_sessions.py             do/       NONE
1.4    vision_server.py                 see/      NONE
1.5    cognitive/ui_awareness.py         see/      NONE
1.6    cognitive/app_knowledge_extractor.py  see/  NONE
1.7    doc_ingestion.py                 learn/    NONE
1.8    legitimate_extraction.py         learn/    NONE
1.9    auto_validator.py                learn/    NONE
1.10   parallel_learn.py               learn/    NONE
1.11   training_prep.py                learn/    NONE
1.12   training_runner.py              learn/    NONE
1.13   project_permissions.py          do/       NONE
1.14   sam.py                          core/     NONE
1.15   sam_repl.py                     serve/    LOW (imports sam_chat)
1.16   cognitive/code_pattern_miner.py  learn/    NONE
```

### Phase 2: Low-Dependency Modules (1-2 dependents, no circulars)
```
Order  File                              Target    Dependents
-----  ----                              ------    ----------
2.1    audio_utils.py                   speak/    voice/voice_extraction_pipeline.py
2.2    deduplication.py                 learn/    data_quality.py
2.3    data_quality.py                  learn/    (none)
2.4    training_data.py                 learn/    training_capture.py
2.5    training_capture.py              learn/    (none)
2.6    approval_queue.py               do/       sam_api.py
2.7    tool_system.py                  do/       sam_parity_orchestrator.py
2.8    parity_system.py                learn/    sam_parity_orchestrator.py
2.9    claude_learning.py              learn/    sam_parity_orchestrator.py
2.10   sam_parity_orchestrator.py       learn/    (none)
2.11   apple_ocr.py                    see/      sam_api.py, cognitive/smart_vision.py
2.12   image_generator.py              see/      orchestrator.py
2.13   comfyui_client.py               see/      orchestrator.py
2.14   model_deployment.py             learn/    sam_api.py
2.15   impact_tracker.py               learn/    orchestrator.py
2.16   conversation_logger.py          remember/ orchestrator.py
2.17   response_styler.py              core/     orchestrator.py
2.18   thinking_verbs.py               core/     orchestrator.py
2.19   thought_logger.py               core/     orchestrator.py
2.20   narrative_ui_spec.py            core/     orchestrator.py
2.21   transparency_guard.py           core/     orchestrator.py
```

### Phase 3: Medium-Dependency Modules (3-4 dependents)
```
Order  File                              Target    Dependents
-----  ----                              ------    ----------
3.1    privacy_guard.py                core/     orchestrator.py, conversation_logger.py
3.2    relevance_scorer.py             remember/ cognitive/__init__.py, cognitive/enhanced_retrieval.py
3.3    feedback_system.py              learn/    proactive_notifier.py, sam_api.py, training_capture.py
3.4    knowledge_distillation.py       learn/    execution/escalation_handler.py, sam_api.py
3.5    mlx_inference.py                think/    sam_chat.py, memory/infinite_context.py
3.6    terminal_coordination.py        do/       orchestrator.py, auto_coordinator.py, terminal_learning.py, test_suite.py
3.7    auto_coordinator.py             do/       orchestrator.py, test_suite.py
3.8    terminal_learning.py            do/       (none as target)
3.9    live_thinking.py                think/    orchestrator.py, sam_api.py
3.10   multi_agent.py                  think/    sam_enhanced.py
```

### Phase 4: High-Dependency Modules (5+ dependents)
```
Order  File                              Target    Dependents
-----  ----                              ------    ----------
4.1    evolution_tracker.py            learn/    9 files - MUST add compat shim
4.2    evolution_ladders.py            learn/    6 files
4.3    improvement_detector.py         learn/    6 files
4.4    memory/semantic_memory.py       remember/ 5 files
4.5    cognitive/resource_manager.py    think/    4 files
4.6    intelligence_core.py            core/     2 files
4.7    smart_router.py                 core/     2 files
4.8    sam_intelligence.py             learn/    3 files
4.9    data_arsenal.py                 learn/    2 files
4.10   project_dashboard.py            projects/ 2 files
```

### Phase 5: Memory Package Dissolution
```
5.1    memory/fact_memory.py           remember/
5.2    memory/context_budget.py        remember/
5.3    memory/project_context.py       remember/
5.4    memory/conversation_memory.py   remember/
5.5    memory/infinite_context.py      remember/
5.6    memory/rag_feedback.py          remember/
5.7    memory/__init__.py              DELETE (replace with remember/__init__.py)
```

### Phase 6: Cognitive Package Dissolution
This is the riskiest phase. The `cognitive/__init__.py` re-exports 160+ symbols.

```
6.1    cognitive/enhanced_memory.py     remember/
6.2    cognitive/enhanced_retrieval.py  remember/
6.3    cognitive/enhanced_learning.py   remember/
6.4    cognitive/emotional_model.py     remember/
6.5    cognitive/personality.py         remember/
6.6    cognitive/self_knowledge_handler.py  remember/
6.7    cognitive/vision_engine.py       see/
6.8    cognitive/vision_client.py       see/
6.9    cognitive/vision_selector.py     see/
6.10   cognitive/smart_vision.py        see/
6.11   cognitive/image_preprocessor.py  see/
6.12   cognitive/mlx_cognitive.py       think/
6.13   cognitive/mlx_optimized.py       think/
6.14   cognitive/model_selector.py      think/
6.15   cognitive/model_evaluation.py    think/
6.16   cognitive/token_budget.py        think/
6.17   cognitive/quality_validator.py   think/
6.18   cognitive/compression.py         think/
6.19   cognitive/cognitive_control.py   think/
6.20   cognitive/planning_framework.py  think/
6.21   cognitive/multi_agent_roles.py   think/
6.22   cognitive/code_indexer.py        learn/
6.23   cognitive/doc_indexer.py         learn/
6.24   cognitive/learning_strategy.py   learn/
6.25   cognitive/unified_orchestrator.py  core/ (or think/)
6.26   cognitive/__init__.py            KEEP as compat shim
```

### Phase 7: Execution & Voice Package Dissolution
```
7.1    execution/* files                do/
7.2    execution/__init__.py            KEEP as compat shim
7.3    voice/* files                    speak/ (output) / listen/ (input)
7.4    voice/__init__.py                KEEP as compat shim
```

### Phase 8: Hub Files (LAST - Most Risk)
```
8.1    orchestrator.py                  core/     + compat shim at old location
8.2    sam_enhanced.py                  core/     + compat shim
8.3    sam_agent.py                     core/     + compat shim
8.4    sam_api.py                       serve/    + compat shim + update plist
8.5    sam_chat.py                      serve/    + compat shim
8.6    unified_daemon.py               serve/    + update plist
```

---

## 6. Circular Dependencies

### Direct Cycles (Would Be Created Between New Modules)

#### Cycle 1: `core/` <-> `do/`
```
core/orchestrator.py  -->  do/auto_coordinator.py
core/orchestrator.py  -->  do/terminal_coordination.py
do/execution/safe_executor.py  -->  core/orchestrator.py
do/execution/escalation_handler.py  -->  core/intelligence_core.py
do/execution/escalation_handler.py  -->  core/smart_router.py
```
**Impact:** Bidirectional. Cannot resolve without extracting shared interfaces.
**Fix:** Extract `orchestrator` interface to a shared types module, or use lazy imports in `safe_executor.py`.

#### Cycle 2: `core/` <-> `remember/`
```
core/orchestrator.py  -->  remember/conversation_logger.py
remember/conversation_logger.py  -->  core/privacy_guard.py
```
**Impact:** Mild. Privacy guard is a utility.
**Fix:** Move `privacy_guard.py` to a shared `utils/` module, or move `conversation_logger.py` to core/.

#### Cycle 3: `do/` <-> `learn/`
```
do/execution/escalation_handler.py  -->  learn/knowledge_distillation.py
do/execution/auto_fix_control.py  -->  serve/proactive_notifier.py
learn/training_scheduler.py  -->  serve/unified_daemon.py
```
**Impact:** Indirect via serve/. The escalation_handler uses knowledge_distillation for learning from escalations.
**Fix:** Use lazy imports in escalation_handler.

#### Cycle 4: `do/` <-> `serve/`
```
do/execution/auto_fix_control.py  -->  serve/proactive_notifier.py
serve/sam_chat.py  -->  do/execution/escalation_handler.py
serve/sam_api.py  -->  do/execution/escalation_handler.py
serve/sam_api.py  -->  do/approval_queue.py
```
**Impact:** Moderate. API layer naturally depends on execution.
**Fix:** Notifications should flow outward (do/ -> serve/ is fine). The serve/ -> do/ direction is natural (API calls execution). Accept this as acceptable dependency direction.

#### Cycle 5: `learn/` <-> `serve/`
```
learn/training_scheduler.py  -->  serve/unified_daemon.py
serve/sam_api.py  -->  learn/training_pipeline.py
serve/sam_api.py  -->  learn/improvement_detector.py
serve/sam_api.py  -->  learn/knowledge_distillation.py
serve/sam_api.py  -->  learn/feedback_system.py
serve/sam_api.py  -->  learn/sam_intelligence.py
```
**Impact:** sam_api.py imports heavily from learn/. training_scheduler references daemon.
**Fix:** Accept serve/ -> learn/ as natural direction. Move daemon reference to config or lazy import.

#### Cycle 6: `projects/` <-> `think/`
```
projects/code_indexer.py  -->  think/query_decomposer.py
think/query_decomposer.py  -->  projects/code_indexer.py
```
**Impact:** Direct mutual import. These two files are tightly coupled.
**Fix:** Merge into one file, or extract shared interface. Consider keeping both in `projects/` since they serve project search.

#### Cycle 7: `serve/` <-> `think/`
```
think/cognitive/compression.py  -->  serve/sam_api.py
serve/sam_api.py  -->  think/cognitive/mlx_cognitive.py
serve/sam_api.py  -->  think/cognitive/compression.py
serve/sam_api.py  -->  think/cognitive/resource_manager.py
```
**Impact:** `compression.py` imports `sam_api` (likely for API access to Claude). This is the most problematic circular.
**Fix:** Extract the Claude API call from sam_api into a separate module (e.g., `think/claude_client.py`) that compression.py can use without importing all of sam_api.

### Additional Cross-Module Dependencies (Not Circular but Notable)

```
listen/ --> speak/           (voice_extraction_pipeline imports audio_utils)
see/    --> do/              (smart_vision imports escalation_handler)
speak/  --> think/           (tts_pipeline imports cognitive.resource_manager)
remember/ --> think/         (infinite_context imports mlx_inference)
```

---

## 7. Hardcoded Paths

### Python Files Using `Path(__file__).parent`

These files compute their location relative to `__file__` and will break if moved without updating path calculations:

| File | Current `__file__` Usage | Impact |
|------|-------------------------|--------|
| `ssot_sync.py` | `SAM_BRAIN = Path(__file__).parent` | DB/export paths break |
| `system_orchestrator.py` | `SAM_BRAIN = Path(__file__).parent` | Same |
| `unified_orchestrator.py` (root) | `Path(__file__).parent / "data"` | DB path breaks |
| `claude_learning.py` | `Path(__file__).parent / "claude_training_data"` | Training data path breaks |
| `perpetual_learner.py` | `BRAIN_PATH = Path(__file__).parent` | Path breaks |
| `training_pipeline.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `multi_agent.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `training_scheduler.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `training_stats.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `evolution_tracker.py` | `EVOLUTION_DB = Path(__file__).parent / "evolution.db"` | **DB path breaks** |
| `auto_learner.py` | `BRAIN_DIR = Path(__file__).parent` | Path breaks |
| `sam_enhanced.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `memory/semantic_memory.py` | `MEMORY_DIR = Path(__file__).parent / "memory"` | **Double-nesting issue** |
| `parity_system.py` | `brain_dir = Path(__file__).parent` | Path breaks |
| `parallel_learn.py` | `BRAIN_PATH = Path(__file__).parent` | Path breaks |
| `voice/voice_output.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `voice/voice_server.py` | `CACHE_DIR = Path(__file__).parent / "voice_cache"` | Cache path breaks |
| `voice/voice_bridge.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `execution/auto_fix.py` | `SAM_BRAIN = Path(__file__).parent` | Points to execution/ not sam_brain/ |
| `execution/command_proposer.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `tts_pipeline.py` | `SCRIPT_DIR = Path(__file__).parent` | Path breaks |
| `tool_system.py` | `Path(__file__).parent / "tasks.json"` | Task storage breaks |
| `unified_daemon.py` | `base_dir = Path(__file__).parent.parent` | Daemon start commands break |
| `cognitive/vision_engine.py` | `Path(__file__).parent.parent.parent / "ai_bridge.cjs"` | Bridge path breaks |
| `execution/escalation_handler.py` | `Path(__file__).parent.parent / "ai_bridge.cjs"` | Bridge path breaks |

### Hardcoded Absolute Paths

| File | Hardcoded Path |
|------|---------------|
| `memory/project_context.py:272` | `INVENTORY_PATH = Path("/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/exhaustive_analysis/master_inventory.json")` |
| `cognitive/test_e2e_comprehensive.py:971` | `"/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/test_report.json"` |
| `memory/embeddings.json` | Contains `"SAM source code: /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/"` |

### Shell Scripts with Hardcoded Paths

| File | Path Referenced |
|------|----------------|
| `sam_aliases.sh:4` | `export SAM_HOME="$HOME/ReverseLab/SAM/warp_tauri/sam_brain"` |
| `sam_aliases.sh:44` | `sam_brain/projects.json` |
| `health_check.sh:35` | `sam_brain/exhaustive_analysis/master_inventory.json` |
| `health_check.sh:55` | `cd "$HOME/ReverseLab/SAM/warp_tauri/sam_brain"` |
| `ladder_local.sh:47` | `sam_brain/mlx_server.py` |
| `parallel_builder.sh:13` | `/Users/davidquinton/ReverseLab/SAM/warp_tauri` |

### Launchd Plists with Hardcoded Paths

| File | Path Referenced |
|------|----------------|
| `com.sam.api.plist:11` | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/sam_api.py` |
| `com.sam.api.plist:28` | WorkingDirectory: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| `com.sam.daemon.plist:11` | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/unified_daemon.py` |
| `com.sam.daemon.plist:25` | WorkingDirectory: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |

### `sys.path.insert` Hacks (38 locations)

These files manually add directories to Python's import path. Every single one needs review during migration:

**Root-level files (14):**
`sam_api.py`, `sam_chat.py`, `sam_repl.py`, `sam_parity_orchestrator.py`, `claude_orchestrator.py`, `terminal_learning.py`, `training_scheduler.py`, `training_stats.py`, `re_orchestrator.py`, `test_evolution_system.py`, `test_new_features.py`

**cognitive/ files (5):**
`cognitive/__init__.py`, `cognitive/self_knowledge_handler.py`, `cognitive/unified_orchestrator.py`, `cognitive/enhanced_retrieval.py`, `cognitive/test_e2e_comprehensive.py`

**execution/ files (1):**
`execution/escalation_handler.py`

**tests/ files (17):**
All 17 test files use `sys.path.insert(0, str(Path(__file__).parent.parent))`

---

## 8. Unmapped Files and Directories

The following files/directories have no planned target and must be addressed:

### Unmapped Python Files
| File | Suggested Target | Reason |
|------|-----------------|--------|
| `conversation_engine/` (4 files) | `speak/` or `core/` | Voice pipeline conversation management |
| `exhaustive_analyzer.py` | `learn/` or leave | Analysis tool |
| `cognitive/demo_full_integration.py` | DELETE or `tests/` | Demo script |
| `cognitive/test_*.py` (3 files) | `tests/` | Test files |
| `warp_knowledge/analyze_warp_data.py` | `learn/` or leave | Analysis tool |
| `startup/project_context.py` | `remember/` or `projects/` | Startup context |

### Unmapped Non-Python Files That Reference Paths
| File | Notes |
|------|-------|
| `projects.json` | Project registry data |
| `projects_discovered.json` | Discovery cache |
| `project_favorites.json` | User preferences |
| `daemon_status.json` | Runtime state |
| `stats.json` | Runtime stats |
| `evolution.db` | SQLite database -- referenced by `evolution_tracker.py` via `Path(__file__).parent` |
| `auto_learning.db` | SQLite database |
| `data/` directory | Database files for unified_orchestrator |
| `training_data/` directory | Training data storage |
| `voice_cache/`, `voice_cache_v2/` | Voice cache directories |
| `checkpoints/` | Model checkpoints |
| `models/` | MLX models |
| `static/` | Web static files |
| `escalation_data/` | Escalation learning data |

---

## 9. The cognitive/__init__.py Problem

This is the single biggest obstacle to migration. The `cognitive/__init__.py` file:

1. **Re-exports 160+ symbols** from 20 submodules
2. **Is imported as `import cognitive`** or `from cognitive import X` in 15+ files
3. **Its submodules are scattered across 5 target directories**: think/, see/, remember/, learn/, core/
4. **Has a `sys.path.insert` hack** to import `relevance_scorer` from the parent directory

### Files That Import `cognitive` Package Directly

```python
# These break if cognitive/ is dissolved:
from cognitive import MLXCognitiveEngine         # -> think/
from cognitive import VisionEngine               # -> see/
from cognitive import WorkingMemory              # -> remember/
from cognitive import CognitiveOrchestrator      # -> core/
from cognitive import CodeIndexer                # -> learn/
import cognitive                                 # in execution/escalation_handler.py
```

### Required Solution

Keep `cognitive/__init__.py` as a **compatibility shim** that re-imports from new locations:

```python
# cognitive/__init__.py -- COMPATIBILITY SHIM
# All modules have moved. This file provides backward compatibility.
from think.mlx_cognitive import MLXCognitiveEngine, GenerationConfig, ...
from see.vision_engine import VisionEngine, VisionConfig, ...
from remember.enhanced_memory import WorkingMemory, ...
from core.cognitive_orchestrator import CognitiveOrchestrator, ...
from learn.code_indexer import CodeIndexer, ...
```

The same approach is needed for `memory/__init__.py`, `execution/__init__.py`, and `voice/__init__.py`.

---

## 10. Recommended Strategy

### Option A: Big Bang (NOT Recommended)
Move all 124 files at once. Update all 122 imports. Fix all 38 sys.path hacks. Fix all hardcoded paths.
- **Risk:** If anything breaks, everything breaks. No rollback path.
- **Time:** 4-8 hours with no testing breaks.

### Option B: Phased Migration with Compatibility Shims (RECOMMENDED)

1. **Create compatibility layer first** (1 hour)
   - Add re-export shims in old locations that forward to new
   - This means old `from orchestrator import X` still works after move

2. **Move leaf modules** (Phase 1-2, ~30 files, 1 hour)
   - Zero-dependent files first
   - Validate with `python -c "import X"` after each batch

3. **Move medium-dependency modules** (Phase 3-4, ~20 files, 1 hour)
   - Add compat shims at old locations
   - Run test suite after each batch

4. **Dissolve legacy packages** (Phase 5-7, ~40 files, 2 hours)
   - Keep `cognitive/__init__.py`, `memory/__init__.py`, etc. as shims
   - These shims can be removed in a future cleanup pass

5. **Move hub files last** (Phase 8, ~6 files, 1 hour)
   - orchestrator.py, sam_api.py last
   - Update launchd plists
   - Update shell scripts

6. **Cleanup** (1 hour)
   - Remove compat shims after confirming all imports use new paths
   - Update CLAUDE.md, ARCHITECTURE.md, all documentation
   - Fix all `Path(__file__).parent` references to use a central `SAM_BRAIN_ROOT` constant

### Option C: Facade Pattern (SAFEST but Slowest)

Keep all files in place. Create the 10 new directories as **facades** that re-export from current locations:

```python
# think/__init__.py
from cognitive.mlx_cognitive import *
from cognitive.mlx_optimized import *
from mlx_inference import *
# etc.
```

Then gradually update imports throughout the codebase to use new paths. Only physically move files once all imports point to the new location.

- **Risk:** Lowest. Nothing breaks during transition.
- **Time:** Spread over weeks/months.
- **Downside:** Two import paths exist simultaneously. Confusing.

### Critical Pre-Migration Tasks

1. **Define `SAM_BRAIN_ROOT`** -- A single constant for the project root, replacing 25+ `Path(__file__).parent` hacks
2. **Resolve the 7 circular dependencies** before or during migration
3. **Decide where `conversation_engine/` goes** (unmapped)
4. **Decide where `cognitive/unified_orchestrator.py` goes** (imports from both memory and cognitive)
5. **Fix the `compression.py` -> `sam_api.py` circular** before any moves
6. **Back up `evolution.db` and `auto_learning.db`** -- these are SQLite files with relative path references

---

*This analysis covers 124 Python files, 93 cross-module dependency edges, 7 circular dependency cycles, 38 sys.path hacks, and 26+ hardcoded path references. The recommended approach is Option B (Phased Migration with Compatibility Shims) executed over Phase 0-8 as detailed in Section 5.*
