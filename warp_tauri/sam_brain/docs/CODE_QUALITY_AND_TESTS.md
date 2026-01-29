# SAM Brain - Code Quality, Naming, and Test Audit

**Date:** 2026-01-29
**Scope:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`
**Total Python files:** 189 (excluding venv, __pycache__, .auto_fix_backups)
**Total lines of Python:** ~145,400

---

## 1. CODE QUALITY

### 1.1 Files Over 1000 Lines (Need Splitting)

**45 files exceed 1000 lines.** The worst offenders:

| Lines | File | Recommendation |
|------:|------|----------------|
| 5,658 | `sam_api.py` | Split into route modules (vision_routes, voice_routes, cognitive_routes, etc.) |
| 3,872 | `feedback_system.py` | Extract dashboard, training data gen, and CLI into separate files |
| 3,739 | `knowledge_distillation.py` | Extract filtering, export, review CLI into separate modules |
| 3,287 | `memory/project_context.py` | Extract recall handler, context builder, project scanner |
| 2,866 | `memory/context_budget.py` | Extract builders, formatters, serializers |
| 2,506 | `memory/fact_memory.py` | Extract CLI/main, storage layer, query layer |
| 2,089 | `cognitive/model_evaluation.py` | Extract benchmarks, reporters, runners |
| 2,074 | `code_indexer.py` | Extract parsers (3 `parse()` functions), search, CLI |
| 1,817 | `cognitive/unified_orchestrator.py` | Extract RAG stats, vision processing, context building |
| 1,758 | `execution/auto_fix_control.py` | Extract stats, history tracking, fix strategies |
| 1,693 | `execution/auto_fix.py` | Extract fix patterns, validation, backup logic |
| 1,685 | `perpetual_learner.py` | Extract scrapers, training runner, scheduling |
| 1,635 | `execution/execution_history.py` | Extract analytics, export, CLI |
| 1,604 | `cognitive/vision_engine.py` | Extract memory measurement, model management |
| 1,537 | `cognitive/code_pattern_miner.py` | Extract pattern types, mining strategies |
| 1,469 | `orchestrator.py` | Extract handler methods into separate handler classes |
| 1,452 | `project_permissions.py` | Extract permission types, CLI |
| 1,352 | `doc_ingestion.py` | Extract parsers, chunkers |
| 1,344 | `execution/command_proposer.py` | Extract proposal strategies |
| 1,338 | `memory/rag_feedback.py` | Extract analytics, feedback processing |
| 1,330 | `cognitive/app_knowledge_extractor.py` | Extract extractors per app type |
| 1,280 | `training_data.py` | Extract formatters, validators |
| 1,226 | `training_capture.py` | Extract capture strategies |
| 1,183 | `cognitive/multi_agent_roles.py` | Extract role definitions, coordination |
| 1,143 | `data_arsenal.py` | Extract scraper types |
| 1,139 | `approval_queue.py` | Extract queue processing, CLI |
| 1,105 | `deduplication.py` | Extract dedup strategies |
| 1,101 | `memory/infinite_context.py` | Extract compression, retrieval |
| 1,101 | `data_quality.py` | Extract quality checks, reporters |
| 1,083 | `voice/voice_extraction_pipeline.py` | Extract extraction strategies |
| 1,074 | `execution/command_classifier.py` | Extract classification rules |
| 1,071 | `execution/safe_executor.py` | Extract safety checks, sandbox |
| 1,053 | `cognitive/resource_manager.py` | Extract monitors, alerts |
| 1,050 | `terminal_sessions.py` | Extract session management, coordination |
| 1,034 | `parity_system.py` | Extract extractors, reporters |
| 1,016 | `unified_orchestrator.py` | Merge with or replace duplicate orchestrator |

### 1.2 Functions Over 100 Lines (Too Complex)

**91 functions exceed 100 lines.** The 15 worst:

| Lines | Function | File |
|------:|----------|------|
| 944 | `run_server()` | `sam_api.py` |
| 700 | `main()` | `feedback_system.py` |
| 495 | `do_POST()` | `sam_api.py` |
| 357 | `main()` | `knowledge_distillation.py` |
| 356 | `main()` | `sam_api.py` |
| 301 | `main()` | `memory/fact_memory.py` |
| 284 | `do_GET()` | `sam_api.py` |
| 250 | `handle_improve()` | `orchestrator.py` |
| 237 | `handle_data()` | `orchestrator.py` |
| 215 | `main()` | `cognitive/app_knowledge_extractor.py` |
| 207 | `main()` | `cognitive/code_pattern_miner.py` |
| 199 | `propose_for_task()` | `execution/command_proposer.py` |
| 198 | `test_quality_filter()` | `knowledge_distillation.py` |
| 181 | `test_reasoning_extractor()` | `knowledge_distillation.py` |
| 175 | `execute()` | `execution/safe_executor.py` |

**Pattern:** Many `main()` functions are bloated CLI entrypoints with argument parsing, business logic, and output formatting all combined. The `sam_api.py` file has a single `run_server()` function at 944 lines that defines all routes inline.

### 1.3 Docstring Coverage

| Category | Count | With Docstrings | Coverage |
|----------|------:|----------------:|---------:|
| Modules | 189 | 188 | **99.5%** |
| Classes | 850 | 791 | **93.1%** |
| Functions/Methods | 4,682 | 4,036 | **86.2%** |

Docstring coverage is strong. The ~14% of functions missing docstrings are mostly short utility/helper methods and test functions, which is acceptable.

---

## 2. NAMING

### 2.1 The Orchestrator Problem (7 Orchestrators + 1 Coordinator)

The codebase has **7 files with "orchestrator" in the name** plus 1 coordinator, all doing different things:

| File | Purpose | Lines |
|------|---------|------:|
| `orchestrator.py` | Main request router (CHAT, CODE, VISION, etc.) | 1,469 |
| `unified_orchestrator.py` | Project management hub | 1,016 |
| `cognitive/unified_orchestrator.py` | Cognitive system integrator with RAG | 1,817 |
| `system_orchestrator.py` | Scraper/ARR service management | 802 |
| `claude_orchestrator.py` | Claude-to-SAM task delegation | 399 |
| `re_orchestrator.py` | Reverse engineering tools | 874 |
| `sam_parity_orchestrator.py` | Claude Code / ChatGPT parity tracking | 530 |
| `auto_coordinator.py` | Multi-terminal coordination | 596 |

**Key confusion:** Two files are both named `unified_orchestrator.py` (root and `cognitive/`). They do completely different things -- one manages projects, the other integrates cognitive subsystems.

**Recommendation:** Rename for clarity:
- `orchestrator.py` -> `request_router.py`
- `unified_orchestrator.py` -> `project_hub.py`
- `cognitive/unified_orchestrator.py` -> `cognitive/cognitive_pipeline.py`
- `system_orchestrator.py` -> `service_manager.py`
- `claude_orchestrator.py` -> `claude_task_bridge.py`
- `sam_parity_orchestrator.py` -> `parity_tracker.py`

### 2.2 Duplicate Filenames (Identical Names, Different Locations)

| Filename | Locations | Problem |
|----------|-----------|---------|
| `code_indexer.py` | root, `cognitive/` | Two separate code indexing implementations |
| `unified_orchestrator.py` | root, `cognitive/` | Completely different purposes (see above) |
| `project_context.py` | `memory/`, `startup/` | Related but separate context handling |

These create import ambiguity and make it unclear which version is active.

### 2.3 The "sam_*" Proliferation (7 files)

| File | Purpose | Lines |
|------|---------|------:|
| `sam.py` | CLI fast router | 464 |
| `sam_api.py` | HTTP/CLI JSON API for Tauri | 5,658 |
| `sam_chat.py` | Chat interface with MLX | 291 |
| `sam_enhanced.py` | Project-aware coding assistant | 599 |
| `sam_intelligence.py` | Self-awareness and learning | 751 |
| `sam_agent.py` | Local AI coding agent with tools | 311 |
| `sam_repl.py` | Interactive REPL | 180 |

**Problem:** Unclear entry point hierarchy. Which is the "main" SAM? The CLAUDE.md says `sam_api.py` is the primary interface, but there are 6 other entry points.

### 2.4 The "training_*" Proliferation (8 files)

| File | Purpose | Lines |
|------|---------|------:|
| `training_data.py` | Training data formatting/management | 1,280 |
| `training_data_collector.py` | Collects training examples | 616 |
| `training_capture.py` | Captures escalations/corrections | 1,226 |
| `training_pipeline.py` | End-to-end training pipeline | 673 |
| `training_prep.py` | Data preparation and splitting | 447 |
| `training_runner.py` | MLX fine-tuning execution | 980 |
| `training_scheduler.py` | Automated training scheduling | 942 |
| `training_stats.py` | Training statistics tracking | 484 |

While each has a distinct purpose, the naming is not self-documenting. `training_data.py` vs `training_data_collector.py` vs `training_capture.py` -- what is the difference at a glance?

### 2.5 Naming Convention Consistency

**snake_case compliance: 100%** -- No camelCase function names found. All functions and methods consistently use snake_case, which is good.

### 2.6 Names That May Not Match What Code Does

| File | Name Suggests | Actually Does |
|------|---------------|---------------|
| `intelligence_core.py` | Core intelligence module | Small wrapper, mostly unused |
| `multi_agent.py` | Multi-agent orchestration | Different from `cognitive/multi_agent_roles.py` |
| `parity_system.py` | Generic parity system | Specifically tracks Claude/ChatGPT feature parity |
| `legitimate_extraction.py` | Vague "extraction" | Specifically extracts content for training legally |
| `data_arsenal.py` | Military-sounding data tools | Web scraping and content collection |

---

## 3. TESTS

### 3.1 Test Location

Tests are split across **three locations**:

| Location | Files | Tests | Lines |
|----------|------:|------:|------:|
| `tests/` directory | 17 | 816 | 14,736 |
| `cognitive/` (inline) | 3 | 109 | 2,698 |
| Root directory (inline) | 3 | 74 | 1,392 |
| **Total** | **23** | **999** | **18,826** |

**Problem:** Tests in `cognitive/` and root should be moved to `tests/` for consistency.

### 3.2 Test Coverage by File

**Files WITH test coverage (9 source files covered):**

| Test File | Tests | Covers |
|-----------|------:|--------|
| `tests/test_fact_memory.py` | 82 | `memory/fact_memory.py` |
| `tests/test_project_context.py` | 88 | `memory/project_context.py`, `startup/project_context.py` |
| `tests/test_feedback_system.py` | 47 | `feedback_system.py` |
| `tests/test_knowledge_distillation.py` | 35 | `knowledge_distillation.py` |
| `tests/test_query_decomposer.py` | 20 | `query_decomposer.py` |
| `tests/test_training_data.py` | 48 | `training_data.py`, `training_data_collector.py` |
| `tests/test_training_pipeline.py` | 36 | `training_pipeline.py` |
| `tests/test_voice_output.py` | 42 | `voice/voice_output.py` |

**Integration/system-level tests (no direct 1:1 source mapping):**

| Test File | Tests | What It Tests |
|-----------|------:|---------------|
| `tests/test_auto_fix_safety.py` | 79 | `execution/auto_fix.py`, `execution/auto_fix_control.py` |
| `tests/test_context_compression.py` | 54 | `cognitive/compression.py`, `memory/context_budget.py` |
| `tests/test_execution_security.py` | 69 | `execution/safe_executor.py`, `execution/command_classifier.py` |
| `tests/test_fact_injection.py` | 4 | Fact injection pipeline |
| `tests/test_image_followup.py` | 4 | Vision follow-up conversations |
| `tests/test_rag_pipeline.py` | 67 | RAG end-to-end pipeline |
| `tests/test_vision_chat.py` | 48 | Vision chat integration |
| `tests/test_vision_performance.py` | 48 | Vision system performance |
| `tests/test_voice_performance.py` | 45 | Voice pipeline performance |
| `cognitive/test_cognitive_system.py` | 51 | Cognitive subsystem integration |
| `cognitive/test_e2e_comprehensive.py` | 32 | End-to-end comprehensive |
| `cognitive/test_vision_system.py` | 26 | Vision system |
| `test_evolution_system.py` | 25 | Evolution tracking |
| `test_new_features.py` | 18 | Feature verification |
| `test_suite.py` | 31 | General test suite |

### 3.3 Files WITHOUT Any Tests

**136 out of 145 source files (93.8%) have NO dedicated tests.** Major untested areas:

**Critical untested files (core functionality):**
- `sam_api.py` (5,658 lines -- the largest file, completely untested)
- `orchestrator.py` (1,469 lines -- main request router)
- `memory/context_budget.py` (2,866 lines)
- `memory/semantic_memory.py` (embeddings layer)
- `memory/conversation_memory.py`
- `memory/infinite_context.py` (1,101 lines)
- `memory/rag_feedback.py` (1,338 lines)
- `mlx_inference.py` (MLX inference layer)
- `cognitive/mlx_cognitive.py` (base MLX engine)
- `cognitive/mlx_optimized.py` (optimized engine)
- `sam_intelligence.py` (self-awareness)

**Untested execution system:**
- `execution/safe_executor.py` (1,071 lines -- has integration tests but no unit tests)
- `execution/command_classifier.py` (1,074 lines)
- `execution/command_proposer.py` (1,344 lines)
- `execution/execution_history.py` (1,635 lines)
- `execution/escalation_handler.py`
- `execution/escalation_learner.py`

**Untested training pipeline:**
- `training_capture.py` (1,226 lines)
- `training_runner.py` (980 lines)
- `training_scheduler.py` (942 lines)
- `training_prep.py`
- `training_stats.py`

**Untested voice system:**
- `voice/voice_server.py`
- `voice/voice_pipeline.py`
- `voice/voice_extraction_pipeline.py` (1,083 lines)
- `voice/voice_cache.py`
- `voice/voice_bridge.py`
- `voice/voice_preprocessor.py`
- `voice/voice_settings.py`
- `voice/voice_trainer.py`

**All cognitive subsystem files (except through integration tests):**
- `cognitive/enhanced_memory.py`
- `cognitive/emotional_model.py`
- `cognitive/cognitive_control.py`
- `cognitive/resource_manager.py` (1,053 lines)
- `cognitive/vision_engine.py` (1,604 lines)
- `cognitive/model_selector.py`
- `cognitive/model_evaluation.py` (2,089 lines)
- Plus 14 more cognitive files

---

## 4. SUMMARY AND PRIORITIES

### Critical Issues (Fix First)

1. **`sam_api.py` at 5,658 lines with a 944-line function** -- This is the primary API entry point and is unmaintainable. Split into route modules.

2. **7 orchestrators with 2 sharing the same name** -- Import confusion and unclear architecture. Consolidate or rename.

3. **93.8% of source files have no tests** -- Only 9 source files have direct test coverage out of 145. Core systems like `sam_api.py`, `orchestrator.py`, `mlx_inference.py`, and the entire execution pipeline are untested.

### Moderate Issues (Fix Next)

4. **45 files over 1000 lines** -- Nearly a third of source files are oversized. Prioritize splitting the top 10.

5. **91 functions over 100 lines** -- Many `main()` functions serve as CLI, business logic, and formatting combined.

6. **Duplicate filenames** (`code_indexer.py` x2, `unified_orchestrator.py` x2, `project_context.py` x2) -- Clarify or merge.

7. **Tests scattered across 3 locations** -- Move all to `tests/` directory.

### What Is Good

- **Docstring coverage is excellent** (86-99% across modules, classes, and functions)
- **snake_case naming is 100% consistent** -- No convention violations
- **Well-organized subpackages** (cognitive/, execution/, memory/, voice/, emotion2vec_mlx/)
- **Test quality is decent** -- The 999 tests that exist are substantial (18,826 lines), covering security, performance, and integration
