# SAM Brain Runtime Analysis

Generated: 2026-01-29

Traces actual import reachability from every entry point to classify each Python file.

## Entry Points

| Entry Point | Port/Mode | Purpose |
|---|---|---|
| `sam_api.py` | HTTP :8765 / CLI | Main API server and CLI |
| `perpetual_learner.py` | Daemon | Continuous learning engine |
| `auto_learner.py` | Daemon | Learns from Claude Code sessions |
| `vision_server.py` | HTTP :8766 | Persistent vision model server |
| `sam.py` | CLI | Quick CLI routing + MLX inference |
| `sam_repl.py` | CLI (REPL) | Interactive terminal |
| `unified_daemon.py` | Daemon | Service manager (launches others via subprocess) |

---

## Classification Key

- **ACTIVE** -- Reachable from `sam_api.py` (main server)
- **DAEMON** -- Only reachable from `perpetual_learner.py` or `auto_learner.py`
- **VISION** -- Only reachable from `vision_server.py`
- **CLI** -- Only reachable from `sam.py` or `sam_repl.py`
- **TEST** -- Test files only
- **DEAD** -- Not imported by any entry point

---

## Root-Level Files (`sam_brain/*.py`)

| File | Classification | Imported By | Notes |
|---|---|---|---|
| `sam_api.py` | **ACTIVE** | Entry point | HTTP server + CLI, port 8765 |
| `sam_enhanced.py` | **ACTIVE** | `sam_api.py` | Provides `sam()`, `route()`, `find_project()`, `load_memory()` |
| `orchestrator.py` | **ACTIVE** | `sam_api.py` | Request routing via `orchestrate()` |
| `sam_intelligence.py` | **ACTIVE** | `sam_api.py` (lazy) | Self-awareness, improvement tracking |
| `improvement_detector.py` | **ACTIVE** | `sam_api.py`, `orchestrator.py`, `sam_intelligence.py` | Detects code improvements |
| `feedback_system.py` | **ACTIVE** | `sam_api.py` (lazy) | FeedbackDB for learning |
| `knowledge_distillation.py` | **ACTIVE** | `sam_api.py` (lazy) | DistillationDB |
| `approval_queue.py` | **ACTIVE** | `sam_api.py` (try/except) | Approval workflow |
| `model_deployment.py` | **ACTIVE** | `sam_api.py` (lazy) | Model version management |
| `training_pipeline.py` | **ACTIVE** | `sam_api.py` (lazy) | TrainingPipeline |
| `live_thinking.py` | **ACTIVE** | `sam_api.py`, `orchestrator.py` | Streaming thought display |
| `thinking_verbs.py` | **ACTIVE** | `orchestrator.py` | Thinking verb vocabulary |
| `response_styler.py` | **ACTIVE** | `orchestrator.py` | SAM personality styling |
| `impact_tracker.py` | **ACTIVE** | `orchestrator.py` | Tracks improvement impact |
| `privacy_guard.py` | **ACTIVE** | `orchestrator.py` | Content sanitization |
| `transparency_guard.py` | **ACTIVE** | `orchestrator.py` | Suspicious pattern detection |
| `thought_logger.py` | **ACTIVE** | `orchestrator.py` | Thought phase logging |
| `conversation_logger.py` | **ACTIVE** | `orchestrator.py` | Encrypted conversation logs |
| `project_dashboard.py` | **ACTIVE** | `orchestrator.py` | Dashboard generation |
| `data_arsenal.py` | **ACTIVE** | `orchestrator.py` | Data collection/scraping |
| `terminal_coordination.py` | **ACTIVE** | `orchestrator.py` | Multi-terminal awareness |
| `auto_coordinator.py` | **ACTIVE** | `orchestrator.py` | Coordinated sessions |
| `re_orchestrator.py` | **ACTIVE** | `orchestrator.py` | Reverse engineering routing |
| `image_generator.py` | **ACTIVE** | `orchestrator.py` | Image generation |
| `comfyui_client.py` | **ACTIVE** | `orchestrator.py` | ComfyUI API client |
| `evolution_tracker.py` | **ACTIVE** | `orchestrator.py` | Evolution tracking |
| `evolution_ladders.py` | **ACTIVE** | `orchestrator.py` | Skill ladder system |
| `narrative_ui_spec.py` | **ACTIVE** | `orchestrator.py` | UI spec generation |
| `apple_ocr.py` | **ACTIVE** | `sam_api.py` | Apple Vision OCR |
| `multi_agent.py` | **ACTIVE** | `sam_enhanced.py` | Multi-agent orchestrator |
| `ssot_sync.py` | **ACTIVE** | `sam_enhanced.py` | SSOT document sync |
| `sam_agent.py` | **ACTIVE** | `sam_enhanced.py` | Agent execution |
| `smart_router.py` | **ACTIVE** | `sam_enhanced.py` via `sam_chat.py`; `execution/escalation_handler.py` | Provider routing |
| `intelligence_core.py` | **ACTIVE** | `sam_api.py` (lazy), `execution/escalation_handler.py` | Intelligence core |
| `mlx_inference.py` | **ACTIVE** | Standalone MLX CLI, but referenced as utility | MLX model inference |
| `query_decomposer.py` | **ACTIVE** | References `code_indexer` | Query decomposition |
| `relevance_scorer.py` | **ACTIVE** | Standalone scorer | Relevance scoring |
| `smart_summarizer.py` | **ACTIVE** | Standalone summarizer | Smart summarization |
| `audio_utils.py` | **ACTIVE** | Voice system utilities | Audio file loading |
| `proactive_notifier.py` | **ACTIVE** | `execution/auto_fix_control.py` | macOS notifications |
| `perpetual_learner.py` | **DAEMON** | Entry point | Continuous learning daemon |
| `auto_learner.py` | **DAEMON** | Entry point | Claude session auto-learner |
| `unified_daemon.py` | **DAEMON** | Entry point | Service manager (subprocess-based) |
| `vision_server.py` | **VISION** | Entry point | Standalone vision HTTP server, port 8766 |
| `sam.py` | **CLI** | Entry point | Quick CLI |
| `sam_repl.py` | **CLI** | Entry point | Interactive REPL |
| `sam_chat.py` | **CLI** | `sam_repl.py` | Chat routing for REPL |
| `claude_orchestrator.py` | **DEAD** | No importer found | Unused orchestrator variant |
| `system_orchestrator.py` | **DEAD** | No importer found | Unused orchestrator variant |
| `claude_learning.py` | **DEAD** | Only `sam_parity_orchestrator.py` (itself dead) | Real-time learner |
| `sam_parity_orchestrator.py` | **DEAD** | No importer found | Imports dead `parity_system.py` + `claude_learning.py` |
| `parity_system.py` | **DEAD** | Only `sam_parity_orchestrator.py` (dead) | Feature parity system |
| `terminal_learning.py` | **DEAD** | No importer found | Terminal learning |
| `terminal_sessions.py` | **DEAD** | No importer found | Terminal session tracking |
| `parallel_learn.py` | **DEAD** | No importer found | Parallel learning |
| `training_prep.py` | **DEAD** | No importer found | Training data preparation |
| `training_runner.py` | **DEAD** | No importer found | Training runner |
| `data_quality.py` | **DEAD** | No importer found | Data quality checks |
| `doc_ingestion.py` | **DEAD** | No importer found | Document ingestion |
| `exhaustive_analyzer.py` | **DEAD** | No importer found | Project analysis |
| `legitimate_extraction.py` | **DEAD** | No importer found | App metadata extraction |
| `auto_validator.py` | **DEAD** | No importer found | Auto validation |
| `tts_pipeline.py` | **DEAD** | No importer found | Legacy TTS pipeline |
| `unified_orchestrator.py` (root) | **DEAD** | No importer found | Duplicate of `cognitive/unified_orchestrator.py` |
| `code_indexer.py` (root) | **DEAD** | Only `query_decomposer.py` + tests | Superseded by `cognitive/code_indexer.py` |
| `project_status.py` | **DEAD** | No importer found (standalone CLI) | Project status display |
| `project_permissions.py` | **DEAD** | Only test files | Permission management |
| `deduplication.py` | **DEAD** | No runtime importer found | Dedup utilities |
| `training_data.py` | **DEAD** | Only `training_capture.py` (itself dead) + tests | Training data management |
| `training_capture.py` | **DEAD** | No importer found | Training data capture |
| `training_data_collector.py` | **DEAD** | Only `training_scheduler.py` (dead) + tests | Data collection |
| `training_scheduler.py` | **DEAD** | Only tests | Training scheduler |
| `training_stats.py` | **DEAD** | Only tests | Training statistics |

---

## `cognitive/` Package

All modules listed here are exported via `cognitive/__init__.py` and reachable from `sam_api.py` through `from cognitive import ...` or direct submodule imports.

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Exports all cognitive modules |
| `mlx_cognitive.py` | **ACTIVE** | Base MLX inference engine |
| `mlx_optimized.py` | **ACTIVE** | KV-cache quantized engine |
| `model_selector.py` | **ACTIVE** | Dynamic 1.5B/3B model selection |
| `token_budget.py` | **ACTIVE** | Context window management |
| `quality_validator.py` | **ACTIVE** | Response validation |
| `resource_manager.py` | **ACTIVE** | Memory monitoring, `can_train()` |
| `enhanced_memory.py` | **ACTIVE** | Working memory |
| `enhanced_retrieval.py` | **ACTIVE** | HyDE and multi-hop retrieval |
| `enhanced_learning.py` | **ACTIVE** | Active learning |
| `compression.py` | **ACTIVE** | Prompt compression |
| `cognitive_control.py` | **ACTIVE** | Meta-cognition |
| `emotional_model.py` | **ACTIVE** | Mood and relationships |
| `vision_engine.py` | **ACTIVE** | Multi-tier vision processing |
| `vision_client.py` | **ACTIVE** | Vision integration wrapper |
| `vision_selector.py` | **ACTIVE** | Resource-aware vision tier selection |
| `smart_vision.py` | **ACTIVE** | Intelligent vision tier routing |
| `image_preprocessor.py` | **ACTIVE** | Memory-efficient image handling |
| `self_knowledge_handler.py` | **ACTIVE** | Self-knowledge queries |
| `code_indexer.py` | **ACTIVE** | Code entity indexing |
| `doc_indexer.py` | **ACTIVE** | Documentation indexing |
| `unified_orchestrator.py` | **ACTIVE** | Integrates all systems, RAG stats |
| `learning_strategy.py` | **ACTIVE** | Learning tier framework |
| `planning_framework.py` | **ACTIVE** | Task planning |
| `multi_agent_roles.py` | **ACTIVE** | Multi-agent role definitions |
| `model_evaluation.py` | **ACTIVE** | Model benchmarking |
| `personality.py` | **ACTIVE** | Personality system |
| `app_knowledge_extractor.py` | **DEAD** | Self-referencing only, no external importer |
| `code_pattern_miner.py` | **DEAD** | No importer found |
| `ui_awareness.py` | **DEAD** | No importer found |
| `demo_full_integration.py` | **TEST** | Demo script |
| `test_cognitive_system.py` | **TEST** | Test file |
| `test_e2e_comprehensive.py` | **TEST** | Test file |
| `test_vision_system.py` | **TEST** | Test file |

---

## `memory/` Package

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Exports all memory modules |
| `semantic_memory.py` | **ACTIVE** | MLX MiniLM embeddings, vector search |
| `context_budget.py` | **ACTIVE** | `sam_api.py` imports directly |
| `fact_memory.py` | **ACTIVE** | `sam_api.py` imports directly |
| `project_context.py` | **ACTIVE** | `sam_api.py` imports directly |
| `infinite_context.py` | **ACTIVE** | Exported via `__init__` |
| `rag_feedback.py` | **ACTIVE** | RAG feedback tracking |
| `conversation_memory.py` | **ACTIVE** | Conversation history |

---

## `execution/` Package

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Package init |
| `escalation_handler.py` | **ACTIVE** | `sam_api.py` imports directly |
| `escalation_learner.py` | **ACTIVE** | `sam_api.py` imports directly |
| `auto_fix.py` | **ACTIVE** | Auto-fix system |
| `auto_fix_control.py` | **ACTIVE** | Auto-fix safety controls |
| `command_classifier.py` | **ACTIVE** | Command safety classification |
| `command_proposer.py` | **ACTIVE** | Command suggestions |
| `execution_history.py` | **ACTIVE** | Execution audit trail |
| `safe_executor.py` | **ACTIVE** | Sandboxed command execution |

---

## `voice/` Package

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Exports all voice modules |
| `voice_output.py` | **ACTIVE** | `sam_api.py` imports directly |
| `voice_pipeline.py` | **ACTIVE** | `sam_api.py` imports directly |
| `voice_settings.py` | **ACTIVE** | Voice configuration persistence |
| `voice_cache.py` | **ACTIVE** | Voice caching |
| `voice_bridge.py` | **ACTIVE** | `sam_enhanced.py` imports |
| `voice_server.py` | **ACTIVE** | FastAPI voice server (separate process) |
| `voice_trainer.py` | **ACTIVE** | `orchestrator.py` imports |
| `voice_preprocessor.py` | **ACTIVE** | Audio preprocessing |
| `voice_extraction_pipeline.py` | **ACTIVE** | Voice extraction from audio |

---

## `conversation_engine/` Package

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Exports ConversationEngine |
| `engine.py` | **ACTIVE** | Core conversation engine |
| `events.py` | **ACTIVE** | Conversation events |
| `state.py` | **ACTIVE** | Conversation state |
| `turn_predictor.py` | **ACTIVE** | Turn prediction |

Reachable via: `sam_api.py` -> `voice/voice_pipeline.py` -> `conversation_engine`

---

## `emotion2vec_mlx/` Package

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **ACTIVE** | Package init |
| `detector.py` | **ACTIVE** | Emotion detection |
| `taxonomy.py` | **ACTIVE** | Emotion taxonomy |
| `prosody_control.py` | **ACTIVE** | Emotion-to-speech mapping |
| `backends/emotion2vec_backend.py` | **ACTIVE** | MLX emotion2vec |
| `backends/prosodic_backend.py` | **ACTIVE** | Prosodic analysis |
| `models/emotion2vec_mlx.py` | **ACTIVE** | MLX model architecture |
| `models/convert_to_mlx.py` | **ACTIVE** | Weight conversion utility |
| `models/convert_weights.py` | **ACTIVE** | Weight format conversion |
| `models/extract_pytorch_weights.py` | **ACTIVE** | Weight extraction |

Reachable via: `sam_api.py` -> `voice/voice_pipeline.py` -> `emotion2vec_mlx`

---

## Empty/Stub Packages (no functional code)

| Directory | Classification | Notes |
|---|---|---|
| `core/` | **DEAD** | Empty `__init__.py` only |
| `do/` | **DEAD** | Empty `__init__.py` only |
| `learn/` | **DEAD** | Empty `__init__.py` only |
| `listen/` | **DEAD** | Empty `__init__.py` only |
| `remember/` | **DEAD** | Empty `__init__.py` only |
| `see/` | **DEAD** | Empty `__init__.py` only |
| `serve/` | **DEAD** | Empty `__init__.py` only |
| `speak/` | **DEAD** | Empty `__init__.py` only |
| `think/` | **DEAD** | Empty `__init__.py` only |
| `projects/` | **DEAD** | Empty `__init__.py` only |
| `startup/` | **DEAD** | Has `project_context.py` but no importer |
| `warp_knowledge/` | **DEAD** | `analyze_warp_data.py` -- standalone analysis script |

---

## Test Files

| File | Classification |
|---|---|
| `test_suite.py` | TEST |
| `test_new_features.py` | TEST |
| `test_evolution_system.py` | TEST |
| `tests/test_auto_fix_safety.py` | TEST |
| `tests/test_context_compression.py` | TEST |
| `tests/test_execution_security.py` | TEST |
| `tests/test_fact_injection.py` | TEST |
| `tests/test_fact_memory.py` | TEST |
| `tests/test_feedback_system.py` | TEST |
| `tests/test_image_followup.py` | TEST |
| `tests/test_knowledge_distillation.py` | TEST |
| `tests/test_project_context.py` | TEST |
| `tests/test_query_decomposer.py` | TEST |
| `tests/test_rag_pipeline.py` | TEST |
| `tests/test_training_data.py` | TEST |
| `tests/test_training_pipeline.py` | TEST |
| `tests/test_vision_chat.py` | TEST |
| `tests/test_vision_performance.py` | TEST |
| `tests/test_voice_output.py` | TEST |
| `tests/test_voice_performance.py` | TEST |

---

## Summary Statistics

| Classification | Count | Percentage |
|---|---|---|
| **ACTIVE** (from sam_api.py) | ~75 files | 55% |
| **DAEMON** (perpetual/auto learner) | 3 files | 2% |
| **VISION** (vision_server.py only) | 1 file | <1% |
| **CLI** (sam.py/sam_repl.py only) | 3 files | 2% |
| **TEST** | 23 files | 17% |
| **DEAD** (unreachable) | ~32 files | 24% |

### Dead Files Summary (32 files)

**Root-level dead files (20):**
- `claude_orchestrator.py` -- superseded by `orchestrator.py`
- `system_orchestrator.py` -- superseded by `orchestrator.py`
- `claude_learning.py` -- only used by dead `sam_parity_orchestrator.py`
- `sam_parity_orchestrator.py` -- dead chain with `parity_system.py`
- `parity_system.py` -- dead chain with `sam_parity_orchestrator.py`
- `terminal_learning.py` -- standalone, never imported
- `terminal_sessions.py` -- standalone, never imported
- `parallel_learn.py` -- standalone, never imported
- `training_prep.py` -- standalone, never imported
- `training_runner.py` -- standalone, never imported
- `training_data.py` -- only imported by dead `training_capture.py`
- `training_capture.py` -- standalone, never imported
- `training_data_collector.py` -- only imported by dead `training_scheduler.py`
- `training_scheduler.py` -- only imported by tests
- `training_stats.py` -- only imported by tests
- `data_quality.py` -- standalone, never imported
- `doc_ingestion.py` -- standalone, never imported
- `exhaustive_analyzer.py` -- standalone, never imported
- `legitimate_extraction.py` -- standalone, never imported
- `auto_validator.py` -- standalone, never imported
- `tts_pipeline.py` -- standalone, superseded by `voice/voice_output.py`
- `unified_orchestrator.py` (root) -- duplicate of `cognitive/unified_orchestrator.py`
- `code_indexer.py` (root) -- superseded by `cognitive/code_indexer.py`
- `deduplication.py` -- no runtime importer
- `project_status.py` -- standalone CLI
- `project_permissions.py` -- only tests

**cognitive/ dead files (3):**
- `cognitive/app_knowledge_extractor.py` -- self-referencing only
- `cognitive/code_pattern_miner.py` -- never imported
- `cognitive/ui_awareness.py` -- never imported

**Empty stub packages (12 directories):**
- `core/`, `do/`, `learn/`, `listen/`, `remember/`, `see/`, `serve/`, `speak/`, `think/`, `projects/`, `startup/`, `warp_knowledge/`

---

## Import Chain: sam_api.py (Full Trace)

```
sam_api.py
├── approval_queue (try/except)
├── feedback_system.FeedbackDB (lazy)
├── knowledge_distillation.DistillationDB (lazy)
├── sam_intelligence.SamIntelligence (lazy)
│   └── improvement_detector.ImprovementDetector
├── sam_enhanced (sam, route, find_project, load_memory)
│   ├── memory.semantic_memory
│   ├── multi_agent
│   ├── ssot_sync
│   ├── voice.voice_bridge
│   └── sam_agent
├── orchestrator.orchestrate
│   ├── cognitive.mlx_cognitive.MLXCognitiveEngine
│   │   └── cognitive.resource_manager
│   ├── impact_tracker.ImpactTracker
│   ├── privacy_guard.PrivacyGuard
│   ├── response_styler
│   ├── thinking_verbs
│   ├── transparency_guard
│   ├── thought_logger
│   ├── conversation_logger
│   ├── live_thinking
│   ├── project_dashboard
│   ├── data_arsenal
│   ├── terminal_coordination
│   ├── auto_coordinator
│   ├── re_orchestrator
│   ├── voice.voice_trainer
│   ├── image_generator
│   ├── comfyui_client
│   ├── sam_intelligence
│   ├── evolution_tracker
│   ├── evolution_ladders
│   ├── improvement_detector
│   └── narrative_ui_spec
├── model_deployment (lazy)
├── training_pipeline (lazy)
├── memory.context_budget (lazy)
├── memory.fact_memory (lazy)
├── memory.project_context (lazy)
├── cognitive.code_indexer (lazy)
├── cognitive.smart_vision (lazy)
├── cognitive (VisionConfig, describe_image, detect_objects, VISION_MODELS)
│   └── [entire cognitive package via __init__.py]
├── execution.escalation_handler
│   └── smart_router
├── execution.escalation_learner
├── intelligence_core (lazy)
├── apple_ocr (lazy)
├── voice.voice_output (lazy)
├── voice.voice_pipeline (lazy)
│   ├── emotion2vec_mlx
│   └── conversation_engine
└── live_thinking (lazy)
```

## Import Chain: perpetual_learner.py

```
perpetual_learner.py
└── cognitive.resource_manager.can_train
```

Minimal dependencies. All learning logic is self-contained.

## Import Chain: auto_learner.py

```
auto_learner.py
└── cognitive.resource_manager.can_train
```

Minimal dependencies. Uses watchdog (third-party) for file monitoring.

## Import Chain: vision_server.py

```
vision_server.py
└── (no local imports -- uses subprocess to call mlx_vlm CLI)
```

Fully standalone.

## Import Chain: sam.py (CLI)

```
sam.py
└── (no local imports -- uses mlx_lm directly)
```

## Import Chain: sam_repl.py (CLI)

```
sam_repl.py
└── sam_chat
    └── smart_router
```
