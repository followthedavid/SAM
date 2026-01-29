# SAM Brain Complete File Audit

Generated: 2026-01-28

This document provides a comprehensive inventory of every Python file in `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`.

## Summary Statistics

| Category | Count | Total Lines |
|----------|-------|-------------|
| Root .py files | 77 | ~66,782 |
| cognitive/ | 34 | ~28,971 |
| memory/ | 8 | ~12,662 |
| voice/ | 10 | ~5,123 |
| execution/ | 9 | ~9,846 |
| emotion2vec_mlx/ | 12 | ~3,669 |
| startup/ | 2 | ~530 |
| utils/ | 2 | ~398 |
| tests/ | 18 | ~16,274 |
| **TOTAL** | **172** | **~144,255** |

---

## Root Directory Files (77 files)

### Core Entry Points

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `sam_api.py` | 5658 | Main HTTP/CLI API server (port 8765) - routes all requests | **ACTIVE** - Primary entry point |
| `sam.py` | 588 | Legacy CLI interface for SAM commands | ENTRY POINT |
| `sam_chat.py` | 523 | Interactive chat CLI with MLX inference | ENTRY POINT |
| `sam_repl.py` | 429 | REPL interface for direct SAM interaction | ENTRY POINT |
| `sam_agent.py` | 566 | Agent-mode SAM with tool calling capabilities | ENTRY POINT |
| `sam_enhanced.py` | 599 | Enhanced SAM with memory and voice integration | ENTRY POINT |

### Orchestration Layer

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `orchestrator.py` | 1469 | Request routing to specialized handlers (CHAT, CODE, VISION, etc.) | **ACTIVE** - imported by sam_api |
| `unified_orchestrator.py` | 1016 | Project consolidation and management across all SAM projects | ENTRY POINT |
| `system_orchestrator.py` | 802 | Scraper/ARR stack control and system-wide automation | ENTRY POINT |
| `claude_orchestrator.py` | 584 | Claude-directed task execution (Claude creates tasks, SAM executes) | ENTRY POINT |
| `re_orchestrator.py` | 874 | Reverse engineering orchestrator (Frida, mitmproxy, paywall bypass) | ENTRY POINT |
| `sam_parity_orchestrator.py` | 543 | Coordinates multiple SAM instances for parallel work | ENTRY POINT |

### MLX Inference

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `mlx_inference.py` | 584 | Base MLX model loading and generation | DORMANT - superseded by cognitive/mlx_cognitive.py |

### Memory & Context

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `semantic_memory.py` | 584 | **LEGACY** - MLX MiniLM embeddings for vector search | DORMANT - superseded by memory/semantic_memory.py |

### Intelligence & Learning

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `sam_intelligence.py` | 751 | Self-awareness, capability tracking, improvement suggestions | **ACTIVE** - imported by sam_api |
| `intelligence_core.py` | 813 | Core intelligence routines for reasoning | DORMANT |
| `perpetual_learner.py` | 1685 | Continuous learning daemon from Claude sessions | ENTRY POINT - launchd service |
| `auto_learner.py` | 961 | Automatic learning from Claude Code history | ENTRY POINT |
| `claude_learning.py` | 764 | Extracts training pairs from Claude interactions | ENTRY POINT |
| `terminal_learning.py` | 901 | Learns from terminal session patterns | DORMANT |

### Training Pipeline (Phase 5)

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `training_data.py` | 1280 | Unified training data schema and storage | DORMANT |
| `training_capture.py` | 1226 | Captures training data from escalations/corrections | DORMANT |
| `training_runner.py` | 980 | MLX LoRA training job orchestration | ENTRY POINT |
| `training_scheduler.py` | 942 | Scheduled data gathering jobs | DORMANT |
| `training_prep.py` | 779 | Training data preparation and splitting | DORMANT |
| `training_stats.py` | 775 | Training data statistics dashboard | DORMANT |
| `training_pipeline.py` | 564 | End-to-end training pipeline | DORMANT |
| `training_data_collector.py` | 456 | Collects training data from various sources | DORMANT |

### Knowledge & Feedback

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `knowledge_distillation.py` | 3739 | Captures Claude reasoning patterns for training | ENTRY POINT |
| `feedback_system.py` | 3872 | User feedback storage, correction analysis, confidence adjustment | **ACTIVE** - imported by sam_api |

### Terminal Coordination

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `terminal_coordination.py` | 796 | Multi-terminal awareness and task sharing | DORMANT |
| `terminal_sessions.py` | 1050 | Session persistence and restoration | DORMANT |

### Data & Scraping

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `data_arsenal.py` | 1143 | Intelligence gathering (scraping, API harvesting) | ENTRY POINT |
| `data_quality.py` | 1101 | Training data quality validation | DORMANT |
| `deduplication.py` | 1105 | Training data deduplication | DORMANT |
| `legitimate_extraction.py` | 855 | Legitimate data extraction methods | DORMANT |

### Code Analysis

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `code_indexer.py` | 2074 | Code indexing with MLX embeddings (semantic search) | **POTENTIAL DUPLICATE** - see cognitive/code_indexer.py |
| `exhaustive_analyzer.py` | 999 | Deep code analysis for understanding | ENTRY POINT |

### Documentation

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `doc_ingestion.py` | 1352 | Converts docs to training data (markdown, docstrings) | DORMANT |

### Vision & Image

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `vision_server.py` | 475 | Persistent MLX vision server (port 8766) | ENTRY POINT |
| `apple_ocr.py` | 119 | Apple Vision framework OCR (zero RAM) | **ACTIVE** - imported by sam_api |
| `image_generator.py` | 187 | Native image generation via mflux | ENTRY POINT |
| `comfyui_client.py` | 281 | ComfyUI API client for image generation | DORMANT |

### Voice & TTS

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `tts_pipeline.py` | 632 | TTS with automatic fallback (F5-TTS to macOS say) | **ACTIVE** - imported by sam_api |
| `audio_utils.py` | 213 | Audio loading utilities (MLX-first) | **ACTIVE** - imported by voice modules |

### Routing & Summarization

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `smart_router.py` | 396 | Routes queries to local vs external LLMs | DORMANT |
| `smart_summarizer.py` | 697 | Extractive summarization without LLM calls | DORMANT |
| `query_decomposer.py` | 753 | Decomposes complex queries into sub-queries | DORMANT |
| `relevance_scorer.py` | 902 | Multi-factor result reranking | **ACTIVE** - imported by cognitive/__init__.py |

### Evolution & Tracking

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `evolution_tracker.py` | 625 | Tracks project progress and improvements over time | DORMANT |
| `evolution_ladders.py` | 633 | Defines improvement paths for capabilities | DORMANT |
| `improvement_detector.py` | 616 | Detects opportunities for SAM improvement | DORMANT |
| `impact_tracker.py` | 487 | Tracks impact of changes | DORMANT |

### Permissions & Safety

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `project_permissions.py` | 1452 | Per-project execution permissions | DORMANT |
| `privacy_guard.py` | 452 | Redaction and privacy controls | DORMANT |
| `transparency_guard.py` | 398 | Ensures transparent operation | DORMANT |

### Tools & Execution

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `tool_system.py` | 843 | Claude Code-equivalent tool capabilities | DORMANT |
| `approval_queue.py` | 1139 | Approval workflow for autonomous actions | **ACTIVE** - imported by sam_api |

### Multi-Agent

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `multi_agent.py` | 564 | Spawn specialized sub-agents for complex tasks | ENTRY POINT |
| `auto_coordinator.py` | 596 | Coordinates autonomous operations | DORMANT |

### Daemon & Services

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `unified_daemon.py` | 780 | Manages all SAM services with priority-based resources | ENTRY POINT |
| `proactive_notifier.py` | 478 | Sends proactive notifications to user | DORMANT |

### UI & Display

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `project_dashboard.py` | 900 | Visual project status dashboard | ENTRY POINT |
| `project_status.py` | 659 | Project status reporting | DORMANT |
| `narrative_ui_spec.py` | 708 | UI specifications for narrative display | DORMANT |
| `live_thinking.py` | 473 | Live thinking display during generation | DORMANT |
| `thinking_verbs.py` | 721 | Verb variations for thinking display | DORMANT |
| `thought_logger.py` | 387 | Logs internal thought processes | DORMANT |

### Response & Style

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `response_styler.py` | 487 | Applies SAM's personality to responses | DORMANT |

### Validation & Testing

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `auto_validator.py` | 487 | Automatic response validation | DORMANT |
| `parity_system.py` | 1034 | Validates SAM/Claude parity | DORMANT |
| `model_deployment.py` | 851 | Model deployment and A/B testing | DORMANT |

### Sync & Integration

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `ssot_sync.py` | 753 | Syncs with SSOT documentation | DORMANT |
| `parallel_learn.py` | 564 | Parallel learning from multiple sources | DORMANT |
| `conversation_logger.py` | 627 | Logs conversations for analysis | DORMANT |

### Test Files

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `test_suite.py` | 564 | Main test suite | ENTRY POINT |
| `test_evolution_system.py` | 456 | Tests evolution tracking | ENTRY POINT |
| `test_new_features.py` | 398 | Tests new features | ENTRY POINT |

---

## cognitive/ Directory (34 files, ~28,971 lines)

The cognitive system provides the core AI capabilities.

### Core MLX Engine

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 573 | Package exports (v1.18.0) | **ACTIVE** |
| `mlx_cognitive.py` | 855 | Base MLX engine - model loading, generation | **ACTIVE** |
| `mlx_optimized.py` | 430 | Optimized engine with KV-cache quantization | **ACTIVE** |
| `model_selector.py` | 361 | Dynamic 1.5B/3B model selection | **ACTIVE** |
| `token_budget.py` | 326 | Context window management | **ACTIVE** |
| `quality_validator.py` | 450 | Response validation, repetition detection | **ACTIVE** |
| `resource_manager.py` | 1053 | Memory monitoring, prevents 8GB freezes | **ACTIVE** |

### Vision System

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `vision_engine.py` | 1604 | Multi-tier vision (OCR, CoreML, VLM, Claude) | **ACTIVE** |
| `vision_client.py` | 811 | Easy integration wrapper for vision | **ACTIVE** |
| `vision_selector.py` | 881 | Resource-aware tier selection | **ACTIVE** |
| `smart_vision.py` | 695 | Intelligent tier routing | **ACTIVE** |
| `image_preprocessor.py` | 712 | Memory-efficient image handling | **ACTIVE** |

### Memory & Retrieval

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `enhanced_memory.py` | 731 | Working memory with decay, procedural memory | **ACTIVE** |
| `enhanced_retrieval.py` | 858 | HyDE, multi-hop retrieval, reranking | **ACTIVE** |
| `enhanced_learning.py` | 690 | Active learning, predictive caching | **ACTIVE** |
| `compression.py` | 660 | LLMLingua-style prompt compression | **ACTIVE** |

### Cognition & Planning

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `cognitive_control.py` | 890 | Meta-cognition, goals, reasoning | **ACTIVE** |
| `emotional_model.py` | 681 | Mood state machine, relationships | **ACTIVE** |
| `planning_framework.py` | 823 | 4-tier solution cascade | **ACTIVE** |
| `learning_strategy.py` | 736 | 5-tier learning hierarchy | **ACTIVE** |
| `personality.py` | 377 | Mode-specific prompts and traits | **ACTIVE** |

### Orchestration

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `unified_orchestrator.py` | 1817 | Integrates all systems, RAG stats, image context | **ACTIVE** |
| `multi_agent_roles.py` | 1183 | Coordination between Claude instances | **ACTIVE** |

### Indexing

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `code_indexer.py` | 676 | Code entity indexing (functions, classes) | **ACTIVE** - **POTENTIAL DUPLICATE** with root code_indexer.py |
| `doc_indexer.py` | 905 | Documentation indexing | **ACTIVE** |
| `code_pattern_miner.py` | 1537 | Mines code patterns for training | ENTRY POINT |
| `app_knowledge_extractor.py` | 1330 | Extracts knowledge from apps | ENTRY POINT |

### Self-Knowledge

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `self_knowledge_handler.py` | 361 | Handles "what are you?" queries | **ACTIVE** |

### Evaluation

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `model_evaluation.py` | 2089 | A/B testing, benchmarks, metrics | ENTRY POINT |

### UI Awareness

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `ui_awareness.py` | 843 | UI context understanding | DORMANT |

### Test Files

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `test_cognitive_system.py` | 1074 | Tests cognitive system | ENTRY POINT |
| `test_e2e_comprehensive.py` | 1019 | End-to-end tests | ENTRY POINT |
| `test_vision_system.py` | 605 | Tests vision system | ENTRY POINT |
| `demo_full_integration.py` | 335 | Demo of full integration | ENTRY POINT |

---

## memory/ Directory (8 files, ~12,662 lines)

Persistent memory systems for SAM.

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 168 | Package exports | **ACTIVE** |
| `semantic_memory.py` | 627 | MLX MiniLM embeddings for vector search | **ACTIVE** |
| `fact_memory.py` | 2506 | User/project facts with decay | **ACTIVE** |
| `conversation_memory.py` | 769 | Persistent conversation history | **ACTIVE** |
| `project_context.py` | 3287 | Project detection, profile loading, session state | **ACTIVE** |
| `context_budget.py` | 2866 | Token allocation for RAG results | **ACTIVE** |
| `infinite_context.py` | 1101 | State management for long generation | ENTRY POINT |
| `rag_feedback.py` | 1338 | RAG quality feedback loop | **ACTIVE** |

---

## voice/ Directory (10 files, ~5,123 lines)

Voice input/output system.

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 182 | Package exports | **ACTIVE** |
| `voice_output.py` | 320 | TTS engines (macOS, Coqui, RVC) | **ACTIVE** |
| `voice_settings.py` | 664 | Persistent voice configuration | **ACTIVE** |
| `voice_pipeline.py` | 413 | Complete voice interaction pipeline | **ACTIVE** |
| `voice_cache.py` | 707 | TTS caching with LRU eviction | **ACTIVE** |
| `voice_bridge.py` | 306 | RVC voice cloning bridge | **ACTIVE** |
| `voice_preprocessor.py` | 805 | Text preprocessing for TTS | **ACTIVE** |
| `voice_trainer.py` | 229 | RVC voice training | ENTRY POINT |
| `voice_extraction_pipeline.py` | 1083 | Multi-speaker voice extraction | ENTRY POINT |
| `voice_server.py` | 414 | HTTP API for voice services | ENTRY POINT |

---

## execution/ Directory (9 files, ~9,846 lines)

Safe command execution and auto-fix capabilities.

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 243 | Package exports | **ACTIVE** |
| `auto_fix.py` | 1693 | Automatic code issue detection and fixing | ENTRY POINT |
| `auto_fix_control.py` | 1758 | Permission and rate limiting for auto-fix | **ACTIVE** |
| `command_classifier.py` | 1074 | Command safety classification | **ACTIVE** |
| `command_proposer.py` | 1344 | Command proposal generation | **ACTIVE** |
| `safe_executor.py` | 1071 | Sandboxed command execution | **ACTIVE** |
| `execution_history.py` | 1635 | Execution logging and rollback | **ACTIVE** |
| `escalation_handler.py` | 469 | Claude escalation logic | **ACTIVE** |
| `escalation_learner.py` | 559 | Learning from escalations | DORMANT |

---

## emotion2vec_mlx/ Directory (12 files, ~3,669 lines)

MLX-native emotion recognition from voice.

### Root

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 45 | Package exports | **ACTIVE** |
| `detector.py` | 341 | Emotion detection entry point | **ACTIVE** |
| `taxonomy.py` | 324 | Emotion taxonomy definitions | **ACTIVE** |
| `prosody_control.py` | 634 | Emotion-to-speech mapping | **ACTIVE** |

### backends/

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 111 | Backend registry | **ACTIVE** |
| `emotion2vec_backend.py` | 417 | MLX emotion2vec backend | DORMANT (model not converted) |
| `prosodic_backend.py` | 525 | Prosodic analysis backend (works now) | **ACTIVE** |

### models/

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 17 | Model exports | DORMANT |
| `emotion2vec_mlx.py` | 512 | MLX model architecture | DORMANT |
| `convert_to_mlx.py` | 250 | PyTorch weight conversion | ENTRY POINT |
| `convert_weights.py` | 372 | Weight format conversion | ENTRY POINT |
| `extract_pytorch_weights.py` | 121 | Weight extraction | ENTRY POINT |

---

## startup/ Directory (2 files, ~530 lines)

Session initialization and project awareness.

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 25 | Package exports | **ACTIVE** |
| `project_context.py` | 505 | Project scanning and registry | **ACTIVE** |

**Note:** `startup/project_context.py` is DIFFERENT from `memory/project_context.py`. The startup version scans and registers projects, while the memory version handles runtime context and session state.

---

## utils/ Directory (2 files, ~398 lines)

Reusable utility modules.

| File | Lines | Purpose | Runtime Status |
|------|-------|---------|----------------|
| `__init__.py` | 17 | Package exports | **ACTIVE** |
| `parallel_utils.py` | 381 | ThreadPoolExecutor patterns for 8GB M2 | **ACTIVE** |

---

## tests/ Directory (18 files, ~16,274 lines)

Test suite for SAM components.

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package marker |
| `test_auto_fix_safety.py` | 1434 | Auto-fix safety tests |
| `test_context_compression.py` | 886 | Context compression tests |
| `test_execution_security.py` | 1224 | Execution security tests |
| `test_fact_injection.py` | 284 | Fact injection tests |
| `test_fact_memory.py` | 1064 | Fact memory tests |
| `test_feedback_system.py` | 1118 | Feedback system tests |
| `test_image_followup.py` | 288 | Image followup tests |
| `test_knowledge_distillation.py` | 1132 | Knowledge distillation tests |
| `test_project_context.py` | 1473 | Project context tests |
| `test_query_decomposer.py` | 185 | Query decomposer tests |
| `test_rag_pipeline.py` | 1247 | RAG pipeline tests |
| `test_training_data.py` | 785 | Training data tests |
| `test_training_pipeline.py` | 790 | Training pipeline tests |
| `test_vision_chat.py` | 963 | Vision chat tests |
| `test_vision_performance.py` | 784 | Vision performance tests |
| `test_voice_output.py` | 800 | Voice output tests |
| `test_voice_performance.py` | 888 | Voice performance tests |

---

## Duplicates and Overlaps Analysis

### Confirmed Duplicates

| Location 1 | Location 2 | Issue |
|------------|------------|-------|
| `code_indexer.py` (root, 2074 lines) | `cognitive/code_indexer.py` (676 lines) | **DIFFERENT SCHEMAS** - root uses `code_index_semantic.db`, cognitive uses `code_index.db`. Root has MLX embeddings, cognitive is simpler. |
| `semantic_memory.py` (root) | `memory/semantic_memory.py` | Root version is likely legacy. `memory/` version is canonical. |
| `mlx_inference.py` (root) | `cognitive/mlx_cognitive.py` | Root is legacy. `cognitive/` version is canonical and actively used. |

### Potential Consolidation Candidates

| Files | Issue |
|-------|-------|
| `unified_orchestrator.py` (root) vs `cognitive/unified_orchestrator.py` | Different purposes but confusing names - root is project mgmt, cognitive is RAG orchestration |
| `startup/project_context.py` vs `memory/project_context.py` | Related but different - startup scans, memory manages runtime |
| Multiple training files | 8 training_*.py files could be consolidated into a training/ subdirectory |
| Multiple orchestrator files | 6 *_orchestrator.py files - consider consolidation |

### Files Safe to Archive/Remove

These files appear dormant and may be candidates for archival:

1. `mlx_inference.py` - superseded by cognitive/mlx_cognitive.py
2. `semantic_memory.py` (root) - superseded by memory/semantic_memory.py
3. `smart_router.py` - routing handled by orchestrator.py
4. `intelligence_core.py` - functionality in sam_intelligence.py
5. `terminal_learning.py` - not imported anywhere
6. `terminal_sessions.py` - not imported anywhere

---

## Import Hierarchy (Active Files)

```
sam_api.py (ENTRY POINT)
├── orchestrator.py
│   ├── cognitive/mlx_cognitive.py
│   └── voice/voice_trainer.py
├── cognitive/__init__.py
│   ├── mlx_cognitive.py, mlx_optimized.py
│   ├── vision_engine.py, vision_client.py
│   ├── enhanced_memory.py, enhanced_retrieval.py
│   ├── resource_manager.py
│   └── ... (all cognitive modules)
├── memory/__init__.py
│   ├── semantic_memory.py
│   ├── fact_memory.py
│   ├── project_context.py
│   └── context_budget.py
├── voice/__init__.py
│   ├── voice_output.py
│   ├── voice_pipeline.py
│   └── voice_settings.py
├── execution/__init__.py
│   ├── escalation_handler.py
│   ├── safe_executor.py
│   └── auto_fix_control.py
├── feedback_system.py
├── approval_queue.py
├── sam_intelligence.py
└── knowledge_distillation.py
```

---

## Recommendations

### High Priority

1. **Archive legacy root files**: Move `mlx_inference.py`, `semantic_memory.py` (root) to an `archive/` directory
2. **Clarify code_indexer**: Rename or document the difference between root and cognitive versions
3. **Create training/ subdirectory**: Consolidate 8 training_*.py files

### Medium Priority

4. **Consolidate orchestrators**: Consider merging or clearly documenting the 6 orchestrator variants
5. **Review terminal files**: `terminal_coordination.py`, `terminal_sessions.py`, `terminal_learning.py` are all dormant

### Low Priority

6. **Clean up dormant files**: Many root files are not imported by anything active
7. **Standardize test locations**: Some tests are in root, some in tests/

---

## File-by-File Import Analysis

### Files Imported by sam_api.py

- `approval_queue.py`
- `feedback_system.py`
- `sam_intelligence.py`
- `knowledge_distillation.py`
- `cognitive/*` (via lazy imports)
- `memory/*` (via lazy imports)
- `voice/*` (via lazy imports)
- `execution/*` (via lazy imports)

### Files with Entry Points (`if __name__ == "__main__"`)

50+ files have entry points, making them runnable directly. Key ones:

- `sam_api.py` - Main server
- `vision_server.py` - Vision server
- `perpetual_learner.py` - Learning daemon
- `auto_learner.py` - Auto-learning daemon
- `unified_daemon.py` - Service manager
- `training_runner.py` - Training jobs
- All test_*.py files
