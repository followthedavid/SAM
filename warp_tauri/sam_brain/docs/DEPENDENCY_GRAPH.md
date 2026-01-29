# SAM Brain Dependency Graph

**Generated:** 2026-01-28

This document maps the dependency relationships between all Python files in `sam_brain/`, categorized by which entry point(s) can reach them.

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| ACTIVE | 72 | Reachable from `sam_api.py` (main API) |
| DAEMON | 2 | Only reachable from learning daemons |
| VISION | 1 | Only reachable from vision server |
| ORPHAN | 93 | Not reachable from any entry point |

## Entry Points

| File | Type | Direct Imports | Transitive Reach |
|------|------|----------------|------------------|
| `sam_api.py` | Main HTTP/CLI API | 25 | 72 files |
| `perpetual_learner.py` | Background learning | 1 | 4 files |
| `auto_learner.py` | Claude session learning | 1 | 4 files |
| `vision_server.py` | Vision HTTP server | 0 | 1 file |

---

## ACTIVE Files (72)

Files reachable from `sam_api.py` - the main API entry point. These are production code.

### Root Level
| File | Description | Key Dependencies |
|------|-------------|------------------|
| `apple_ocr.py` | Apple Vision OCR | Foundation framework |
| `approval_queue.py` | Request approval system | sqlite3 |
| `audio_utils.py` | Audio file handling | soundfile |
| `auto_coordinator.py` | Terminal coordination | terminal_coordination |
| `comfyui_client.py` | ComfyUI image gen client | websocket |
| `conversation_logger.py` | Encrypted conv logging | cryptography |
| `data_arsenal.py` | Web scraping/data collection | requests, trafilatura |
| `evolution_ladders.py` | Evolution progress tracking | evolution_tracker |
| `evolution_tracker.py` | Improvement tracking | sqlite3 |
| `feedback_system.py` | User feedback collection | sqlite3 |
| `image_generator.py` | Image generation wrapper | subprocess |
| `impact_tracker.py` | Impact measurement | sqlite3 |
| `improvement_detector.py` | Improvement suggestions | evolution_tracker |
| `intelligence_core.py` | Core intelligence facts | sqlite3 |
| `knowledge_distillation.py` | Learning distillation | sqlite3 |
| `live_thinking.py` | Streaming thought display | cognitive.mlx_cognitive |
| `mlx_inference.py` | MLX model inference | mlx_lm |
| `model_deployment.py` | Model deployment | mlx_lm |
| `multi_agent.py` | Multi-agent orchestration | - |
| `narrative_ui_spec.py` | UI spec generation | - |
| `orchestrator.py` | Main request router | many modules |
| `privacy_guard.py` | Privacy filtering | - |
| `proactive_notifier.py` | Proactive notifications | feedback_system |
| `project_dashboard.py` | Project status dashboard | evolution_* |
| `re_orchestrator.py` | Reverse engineering tools | subprocess |
| `relevance_scorer.py` | Relevance scoring | - |
| `response_styler.py` | Response formatting | - |
| `sam_agent.py` | Agent behavior | - |
| `sam_api.py` | Main API (entry point) | orchestrator |
| `sam_enhanced.py` | Enhanced SAM features | memory.semantic_memory |
| `sam_intelligence.py` | Self-improvement | evolution_* |
| `smart_router.py` | Request routing | - |
| `ssot_sync.py` | SSOT synchronization | evolution_tracker |
| `terminal_coordination.py` | Multi-terminal mgmt | sqlite3 |
| `thinking_verbs.py` | Thinking verb generation | - |
| `thought_logger.py` | Thought logging | sqlite3 |
| `training_pipeline.py` | Training data pipeline | - |
| `transparency_guard.py` | Transparency checks | - |

### cognitive/ Package
| File | Description |
|------|-------------|
| `__init__.py` | Package exports (imports all submodules) |
| `code_indexer.py` | Code indexing with AST |
| `compression.py` | Context compression |
| `mlx_cognitive.py` | MLX inference engine |
| `resource_manager.py` | Memory/resource monitoring |
| `smart_vision.py` | Smart vision routing |

### execution/ Package
| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `auto_fix.py` | Auto-fix implementation |
| `auto_fix_control.py` | Auto-fix control flow |
| `command_classifier.py` | Command classification |
| `command_proposer.py` | Command proposal |
| `escalation_handler.py` | Claude escalation |
| `escalation_learner.py` | Learn from escalations |
| `execution_history.py` | Command history |
| `safe_executor.py` | Safe command execution |

### memory/ Package
| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `context_budget.py` | Context budget management |
| `conversation_memory.py` | Conversation storage |
| `fact_memory.py` | Fact storage |
| `infinite_context.py` | Infinite context handling |
| `project_context.py` | Project context tracking |
| `rag_feedback.py` | RAG feedback |
| `semantic_memory.py` | Vector embeddings (MLX) |

### voice/ Package
| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `voice_bridge.py` | Voice I/O bridge |
| `voice_cache.py` | TTS caching |
| `voice_extraction_pipeline.py` | Voice extraction |
| `voice_output.py` | TTS output |
| `voice_pipeline.py` | Voice processing |
| `voice_preprocessor.py` | Audio preprocessing |
| `voice_settings.py` | Voice settings |
| `voice_trainer.py` | RVC voice training |

### Other Active
| File | Description |
|------|-------------|
| `conversation_engine/__init__.py` | Conversation engine exports |
| `emotion2vec_mlx/__init__.py` | Emotion detection exports |

---

## DAEMON Files (2)

Files only reachable from background learning daemons. These are standalone entry points.

| File | Purpose | Dependencies |
|------|---------|--------------|
| `perpetual_learner.py` | Continuous learning from multiple sources | cognitive.resource_manager |
| `auto_learner.py` | Learns from Claude Code sessions | cognitive.resource_manager |

**Note:** Both daemons share `cognitive.resource_manager` with ACTIVE to check system resources before training.

---

## VISION Files (1)

Files only reachable from the vision server.

| File | Purpose |
|------|---------|
| `vision_server.py` | Standalone vision HTTP server (port 8766) |

**Note:** `vision_server.py` is self-contained and uses subprocess to call `mlx_vlm` CLI. It does not import other sam_brain modules.

---

## ORPHAN Files (93)

Files not reachable from any entry point. These may be:
- Dead code (unused)
- Standalone scripts meant to be run directly
- Future/planned features not yet integrated
- Test files miscategorized
- Module stubs

### Potentially Dead Code (Recommend Review)

These files exist in the codebase but are never imported:

#### cognitive/ Submodules (Not exported via __init__.py)
| File | Notes |
|------|-------|
| `cognitive/cognitive_control.py` | Meta-cognition - listed in CLAUDE.md but not used |
| `cognitive/doc_indexer.py` | Documentation indexing |
| `cognitive/emotional_model.py` | Emotion modeling - listed in CLAUDE.md |
| `cognitive/enhanced_learning.py` | Active learning |
| `cognitive/enhanced_memory.py` | Working memory |
| `cognitive/enhanced_retrieval.py` | HyDE retrieval |
| `cognitive/image_preprocessor.py` | Image preprocessing |
| `cognitive/learning_strategy.py` | Learning strategy |
| `cognitive/mlx_optimized.py` | Optimized MLX engine |
| `cognitive/model_evaluation.py` | Model evaluation |
| `cognitive/model_selector.py` | Dynamic model selection |
| `cognitive/multi_agent_roles.py` | Multi-agent roles |
| `cognitive/personality.py` | Personality system |
| `cognitive/planning_framework.py` | Planning |
| `cognitive/quality_validator.py` | Response validation |
| `cognitive/self_knowledge_handler.py` | Self-knowledge |
| `cognitive/token_budget.py` | Token budgeting |
| `cognitive/ui_awareness.py` | UI awareness |
| `cognitive/unified_orchestrator.py` | Unified orchestrator |
| `cognitive/vision_client.py` | Vision client wrapper |
| `cognitive/vision_engine.py` | Vision engine - listed in CLAUDE.md |
| `cognitive/vision_selector.py` | Vision tier selection |
| `cognitive/app_knowledge_extractor.py` | App knowledge extraction |
| `cognitive/code_pattern_miner.py` | Code pattern mining |
| `cognitive/demo_full_integration.py` | Demo script |

**Issue:** `cognitive/__init__.py` imports these modules but the imports are conditional or behind try/except blocks that fail silently.

#### conversation_engine/ (Imported but chain broken)
| File | Notes |
|------|-------|
| `conversation_engine/engine.py` | Core conversation engine |
| `conversation_engine/events.py` | Event types |
| `conversation_engine/state.py` | State management |
| `conversation_engine/turn_predictor.py` | Turn prediction |

**Issue:** `voice/voice_pipeline.py` imports from `conversation_engine` but the package `__init__.py` has a self-reference bug.

#### emotion2vec_mlx/ (Imported but chain broken)
| File | Notes |
|------|-------|
| `emotion2vec_mlx/backends/__init__.py` | Backend selection |
| `emotion2vec_mlx/backends/emotion2vec_backend.py` | MLX emotion backend |
| `emotion2vec_mlx/backends/prosodic_backend.py` | Prosodic analysis |
| `emotion2vec_mlx/detector.py` | Main detector |
| `emotion2vec_mlx/models/*.py` | Model files |
| `emotion2vec_mlx/prosody_control.py` | Prosody control |
| `emotion2vec_mlx/taxonomy.py` | Emotion taxonomy |

**Issue:** `emotion2vec_mlx/__init__.py` is reached but its internal imports use relative imports that the tracer doesn't fully resolve.

### Standalone Scripts / Entry Points

These appear to be standalone entry points, not meant to be imported:

| File | Purpose |
|------|---------|
| `sam.py` | Legacy SAM entry point? |
| `sam_chat.py` | Chat interface |
| `sam_repl.py` | REPL interface |
| `sam_parity_orchestrator.py` | Parity orchestrator |
| `test_evolution_system.py` | Test script |
| `test_new_features.py` | Test script |
| `test_suite.py` | Test script |
| `exhaustive_analyzer.py` | Analysis script |
| `query_decomposer.py` | Query decomposition |
| `system_orchestrator.py` | System orchestration |

### Module Stubs (Empty packages)

These are empty or minimal package stubs:

| Directory | Notes |
|-----------|-------|
| `core/__init__.py` | Imports non-existent `sam.core` |
| `do/__init__.py` | Imports non-existent `sam.do` |
| `learn/__init__.py` | Imports non-existent `sam.learn` |
| `listen/__init__.py` | Imports non-existent `sam.listen` |
| `projects/__init__.py` | Imports non-existent `sam.projects` |
| `remember/__init__.py` | Imports non-existent `sam.remember` |
| `see/__init__.py` | Imports non-existent `sam.see` |
| `speak/__init__.py` | Imports non-existent `sam.speak` |
| `think/__init__.py` | Imports non-existent `sam.think` |
| `serve/__init__.py` | Likely unused |
| `startup/__init__.py` | Startup helpers |
| `utils/__init__.py` | Utility helpers |

### Training / Data Processing

| File | Notes |
|------|-------|
| `training_capture.py` | Training data capture |
| `training_data.py` | Training data handling |
| `training_data_collector.py` | Data collection |
| `training_prep.py` | Data preparation |
| `training_runner.py` | Training execution |
| `training_scheduler.py` | Training scheduling |
| `training_stats.py` | Training statistics |
| `data_quality.py` | Data quality checks |
| `deduplication.py` | Deduplication |

**Note:** These may be invoked directly by training scripts or daemons not analyzed here.

### Other Orphans

| File | Notes |
|------|-------|
| `auto_validator.py` | Validation |
| `claude_learning.py` | Claude learning |
| `claude_orchestrator.py` | Claude orchestration |
| `code_indexer.py` | Duplicate of cognitive/code_indexer.py |
| `doc_ingestion.py` | Document ingestion |
| `legitimate_extraction.py` | Data extraction |
| `parallel_learn.py` | Parallel learning |
| `parity_system.py` | Parity checks |
| `project_permissions.py` | Project permissions |
| `project_status.py` | Project status |
| `smart_summarizer.py` | Summarization |
| `terminal_learning.py` | Terminal learning |
| `terminal_sessions.py` | Session tracking |
| `tool_system.py` | Tool system |
| `tts_pipeline.py` | TTS pipeline |
| `unified_daemon.py` | Unified daemon |
| `unified_orchestrator.py` | Duplicate? |
| `voice/voice_server.py` | Voice HTTP server |
| `warp_knowledge/analyze_warp_data.py` | Warp analysis |
| `archive/autonomous_daemon.py` | Archived daemon |

---

## Recommendations

### High Priority

1. **Fix `cognitive/__init__.py`**: Many cognitive submodules are documented in CLAUDE.md but not actually reachable. Review the conditional imports.

2. **Fix `conversation_engine/__init__.py`**: Has self-reference bug preventing proper import chain.

3. **Review duplicate files**:
   - `code_indexer.py` vs `cognitive/code_indexer.py`
   - `unified_orchestrator.py` vs `cognitive/unified_orchestrator.py`

### Medium Priority

4. **Clean up module stubs**: The `sam.X` package structure (core, do, learn, etc.) appears abandoned. Consider removing.

5. **Integrate or remove training files**: Many training-related files are orphaned. Either integrate with entry points or move to a separate training package.

6. **Document standalone scripts**: Mark scripts like `sam_chat.py`, `sam_repl.py` as entry points or deprecate them.

### Low Priority

7. **Archive truly dead code**: After review, move confirmed dead code to `archive/`.

---

## Dependency Tree (sam_api.py)

```
sam_api.py
├── orchestrator.py
│   ├── cognitive.mlx_cognitive
│   ├── live_thinking
│   ├── response_styler
│   ├── thinking_verbs
│   ├── thought_logger
│   ├── transparency_guard
│   ├── privacy_guard
│   ├── conversation_logger
│   ├── evolution_ladders
│   │   └── evolution_tracker
│   ├── evolution_tracker
│   ├── improvement_detector
│   ├── impact_tracker
│   ├── project_dashboard
│   ├── data_arsenal
│   ├── comfyui_client
│   ├── image_generator
│   ├── re_orchestrator
│   ├── narrative_ui_spec
│   ├── terminal_coordination
│   ├── auto_coordinator
│   └── voice.voice_trainer
├── cognitive (package)
│   ├── mlx_cognitive
│   │   └── resource_manager
│   ├── compression
│   ├── smart_vision
│   │   ├── apple_ocr
│   │   └── execution.escalation_handler
│   ├── code_indexer
│   └── resource_manager
├── sam_enhanced
│   ├── memory.semantic_memory
│   ├── multi_agent
│   ├── ssot_sync
│   ├── sam_agent
│   └── voice.voice_bridge
├── sam_intelligence
│   ├── evolution_ladders
│   ├── evolution_tracker
│   ├── improvement_detector
│   └── memory.semantic_memory
├── execution (package)
│   ├── escalation_handler
│   │   ├── smart_router
│   │   ├── intelligence_core
│   │   ├── knowledge_distillation
│   │   └── escalation_learner
│   └── ...other execution modules
├── memory (package)
│   ├── semantic_memory
│   ├── fact_memory
│   ├── project_context
│   ├── context_budget
│   └── ...other memory modules
├── voice (package)
│   ├── voice_pipeline
│   │   ├── conversation_engine
│   │   └── emotion2vec_mlx
│   ├── voice_output
│   └── ...other voice modules
├── feedback_system
├── knowledge_distillation
├── intelligence_core
├── approval_queue
├── live_thinking
├── model_deployment
└── training_pipeline
```

---

## File Count by Directory

| Directory | Active | Orphan | Total |
|-----------|--------|--------|-------|
| root | 37 | 31 | 68 |
| cognitive/ | 6 | 21 | 27 |
| execution/ | 9 | 0 | 9 |
| memory/ | 8 | 0 | 8 |
| voice/ | 9 | 1 | 10 |
| conversation_engine/ | 1 | 4 | 5 |
| emotion2vec_mlx/ | 1 | 10 | 11 |
| tests/ | 0 | (not counted) | - |
| Other subdirs | 1 | 26 | 27 |

---

*Last updated: 2026-01-28*
