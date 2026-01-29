# SAM Brain Functional Map

Generated: 2026-01-29

Every `.py` file in `sam_brain/` grouped by what it does.
- **MAIN** = Primary module that does the work
- **HELPER** = Supporting module used by other files

---

## 1. REQUEST ROUTING

| File | Description | Role |
|------|-------------|------|
| `orchestrator.py` | Routes requests to specialized handlers (chat, code, vision, voice, etc.) based on intent | MAIN |
| `smart_router.py` | Decides whether to use local MLX, ChatGPT bridge, or Claude based on complexity | MAIN |
| `sam_parity_orchestrator.py` | Master router for achieving Claude Code + ChatGPT equivalence via capability mapping | MAIN |
| `query_decomposer.py` | Breaks complex multi-part queries into sub-searches for better retrieval | HELPER |
| `cognitive/model_selector.py` | Selects between 1.5B and 3B models based on task type, complexity, and memory pressure | HELPER |
| `cognitive/vision_selector.py` | Resource-aware selection of vision tier (Apple OCR vs CoreML vs VLM vs Claude) | HELPER |

---

## 2. LLM INFERENCE

| File | Description | Role |
|------|-------------|------|
| `cognitive/mlx_cognitive.py` | Native MLX inference engine with dynamic model selection, streaming, and quality validation | MAIN |
| `cognitive/mlx_optimized.py` | Optimized MLX engine with KV-cache quantization, system prompt caching, and prefill chunking | MAIN |
| `mlx_inference.py` | Direct MLX inference server using fine-tuned SAM LoRA adapters | MAIN |
| `live_thinking.py` | Streams real LLM token output so users can see reasoning as it happens | MAIN |
| `cognitive/token_budget.py` | Manages token allocation across system prompt, context, and generation | HELPER |
| `cognitive/quality_validator.py` | Validates response quality: repetition detection, truncation, confidence scoring | HELPER |
| `cognitive/compression.py` | LLMLingua-style prompt compression (4x reduction with minimal information loss) | HELPER |
| `cognitive/resource_manager.py` | Monitors memory, enforces request queuing, prevents freezes on 8GB systems | HELPER |
| `cognitive/cognitive_control.py` | Meta-cognition: confidence estimation, goal management, chain-of-thought reasoning | HELPER |

---

## 3. VOICE INPUT

| File | Description | Role |
|------|-------------|------|
| `conversation_engine/engine.py` | Core conversation orchestrator: continuous audio processing, turn-taking, interrupt handling | MAIN |
| `conversation_engine/turn_predictor.py` | Predicts when user is done speaking from prosodic, linguistic, and pause cues | HELPER |
| `conversation_engine/state.py` | Tracks conversation state: who is speaking, turn history, emotion trajectory | HELPER |
| `conversation_engine/events.py` | Event types emitted during conversation (backchannel, response, interrupt, etc.) | HELPER |
| `conversation_engine/__init__.py` | Package init for conversation engine | HELPER |
| `emotion2vec_mlx/detector.py` | Unified voice emotion detection interface with multiple backends | MAIN |
| `emotion2vec_mlx/backends/prosodic_backend.py` | Rule-based emotion detection from pitch, energy, speech rate (no ML required) | HELPER |
| `emotion2vec_mlx/backends/emotion2vec_backend.py` | Native MLX Emotion2Vec neural emotion classification backend | HELPER |
| `emotion2vec_mlx/taxonomy.py` | 26-category emotion taxonomy based on Russell's Circumplex Model | HELPER |
| `emotion2vec_mlx/backends/__init__.py` | Backend registry and availability checking | HELPER |
| `emotion2vec_mlx/__init__.py` | Package init exporting detector, taxonomy, prosody control | HELPER |
| `audio_utils.py` | Audio loading and processing with MLX-first approach, fallback to torchaudio/numpy | HELPER |
| `listen/__init__.py` | Package stub for voice input module | HELPER |

---

## 4. VOICE OUTPUT

| File | Description | Role |
|------|-------------|------|
| `voice/voice_pipeline.py` | Main voice interaction pipeline: emotion detection + conversation engine + prosody + TTS | MAIN |
| `voice/voice_output.py` | TTS integration supporting macOS voices, Coqui TTS, and RVC voice cloning | MAIN |
| `voice/voice_server.py` | HTTP API for TTS with Dustin Steele voice conversion (FastAPI) | MAIN |
| `tts_pipeline.py` | TTS with automatic fallback (F5-TTS to macOS say) based on RAM availability | MAIN |
| `voice/voice_bridge.py` | Connects SAM to RVC voice cloning for response audio | HELPER |
| `voice/voice_cache.py` | LRU cache for TTS output with pre-computation of common phrases | HELPER |
| `voice/voice_preprocessor.py` | Text preprocessing for TTS: markdown removal, abbreviation expansion, number-to-words | HELPER |
| `voice/voice_settings.py` | Persistent voice configuration: quality level, speed, pitch, auto-speak behavior | HELPER |
| `emotion2vec_mlx/prosody_control.py` | Maps emotional state to prosodic parameters for expressive TTS | HELPER |
| `voice/__init__.py` | Package init for voice module | HELPER |
| `speak/__init__.py` | Package stub for voice output module | HELPER |

---

## 5. VISION

| File | Description | Role |
|------|-------------|------|
| `cognitive/vision_engine.py` | Multi-tier vision engine: SmolVLM, Moondream, Apple Vision, Claude escalation | MAIN |
| `cognitive/smart_vision.py` | Intelligent tier routing: zero-cost Apple APIs to full VLM with progressive analysis | MAIN |
| `vision_server.py` | Persistent HTTP vision server (port 8766) keeping nanoLLaVA loaded in memory | MAIN |
| `apple_ocr.py` | Apple Vision framework OCR: zero-RAM text extraction using Neural Engine | HELPER |
| `cognitive/vision_client.py` | Client wrapper for vision API (HTTP and direct in-process modes) | HELPER |
| `cognitive/image_preprocessor.py` | Memory-efficient image preprocessing: resize, format conversion for 8GB constraint | HELPER |
| `cognitive/ui_awareness.py` | macOS Accessibility API: reads actual UI state, clicks buttons, types text | MAIN |
| `image_generator.py` | Native image generation via mflux (MLX Stable Diffusion) on Apple Silicon | MAIN |
| `comfyui_client.py` | ComfyUI API client for image generation workflows | HELPER |
| `see/__init__.py` | Package stub for vision module | HELPER |

---

## 6. MEMORY

| File | Description | Role |
|------|-------------|------|
| `memory/semantic_memory.py` | Vector embeddings (MLX MiniLM-L6-v2) for intelligent recall of past interactions | MAIN |
| `memory/conversation_memory.py` | Persistent multi-tier conversation memory with fact extraction and preference learning | MAIN |
| `memory/fact_memory.py` | Structured user/project facts with Ebbinghaus decay, reinforcement, and spaced repetition | MAIN |
| `memory/infinite_context.py` | Hierarchical state management for coherent long-form generation from small context models | MAIN |
| `memory/project_context.py` | Project detection, per-project memory, context injection, SSOT integration | MAIN |
| `memory/context_budget.py` | Token allocation across context sections with query-type-aware prioritization | HELPER |
| `memory/rag_feedback.py` | RAG quality feedback loop: tracks source usage, adjusts relevance scores | HELPER |
| `cognitive/enhanced_memory.py` | Working memory with 7+/-2 cognitive limit, decay mechanisms, procedural memory | HELPER |
| `cognitive/enhanced_retrieval.py` | HyDE, multi-hop retrieval, cross-encoder reranking, query decomposition | HELPER |
| `cognitive/self_knowledge_handler.py` | Handles "What do you know about me?" queries by formatting stored facts | HELPER |
| `code_indexer.py` | Indexes code files (functions, classes, modules) for semantic search with MLX embeddings | HELPER |
| `cognitive/code_indexer.py` | Indexes code entities for RAG retrieval (separate schema from root code_indexer.py) | HELPER |
| `cognitive/doc_indexer.py` | Indexes documentation (markdown sections, docstrings, comments) for semantic search | HELPER |
| `relevance_scorer.py` | Multi-factor reranking of RAG search results (keyword, symbol type, recency, etc.) | HELPER |
| `smart_summarizer.py` | Extractive summarization preserving key facts without LLM calls | HELPER |
| `memory/__init__.py` | Package init consolidating all memory modules | HELPER |
| `remember/__init__.py` | Package stub for memory module | HELPER |

---

## 7. LEARNING

| File | Description | Role |
|------|-------------|------|
| `claude_learning.py` | Extracts training patterns from Claude conversations: code gen, reasoning, debugging | MAIN |
| `knowledge_distillation.py` | Captures Claude's reasoning patterns and distills into training data | MAIN |
| `cognitive/enhanced_learning.py` | Active learning, predictive caching, sleep consolidation for memory reorganization | MAIN |
| `cognitive/learning_strategy.py` | 5-tier learning hierarchy: fundamentals to personal specifics with active learning | MAIN |
| `auto_learner.py` | Daemon that watches Claude Code sessions, extracts training pairs, triggers fine-tuning | MAIN |
| `perpetual_learner.py` | Runs indefinitely, continuously learning from all sources with curriculum management | MAIN |
| `terminal_learning.py` | Credit-free learning: generates questions, SAM attempts locally, Claude Code verifies | MAIN |
| `parallel_learn.py` | Runs multiple learning pipelines simultaneously for maximum throughput | MAIN |
| `execution/escalation_learner.py` | Learns from Claude escalations to progressively reduce API dependency | HELPER |
| `feedback_system.py` | Captures user feedback signals and converts to training data with correction analysis | HELPER |
| `intelligence_core.py` | Integrates knowledge distillation, feedback learning, and cross-session memory | HELPER |
| `learn/__init__.py` | Package stub for learning module | HELPER |

---

## 8. TRAINING

| File | Description | Role |
|------|-------------|------|
| `training_pipeline.py` | End-to-end automated fine-tuning: collect, validate, convert, train, evaluate, deploy | MAIN |
| `training_runner.py` | Training job orchestration with 8GB optimizations, memory monitoring, and auto-pause | MAIN |
| `training_prep.py` | Data preparation: MLX format conversion, tokenization, train/val/test splitting | MAIN |
| `training_data.py` | Unified training data schema and SQLite storage for all training sources | MAIN |
| `training_data_collector.py` | Collects training data from git history, code dedup DB, SSOT docs, task completions | MAIN |
| `training_capture.py` | Captures training data from Claude escalations and user corrections | MAIN |
| `training_scheduler.py` | Scheduled data gathering: periodic mining, deduplication, quality checks | MAIN |
| `training_stats.py` | Training data statistics dashboard: totals, by source, quality distribution, daily stats | HELPER |
| `data_quality.py` | Validates training examples: length, format, language, PII/secret detection, auto-fix | HELPER |
| `deduplication.py` | Removes duplicate training examples via exact hash, MinHash, and semantic similarity | HELPER |
| `model_deployment.py` | Safe model deployment with version tracking, sanity checks, rollback, canary releases | MAIN |
| `cognitive/model_evaluation.py` | Model evaluation suite: perplexity, BLEU, ROUGE, A/B testing, SAM-specific benchmarks | HELPER |
| `cognitive/code_pattern_miner.py` | Mines git history for training examples: bug fixes, refactoring, features, docs | HELPER |
| `doc_ingestion.py` | Ingests documentation (Markdown, RST, docstrings) and converts to training pairs | HELPER |
| `voice/voice_trainer.py` | RVC voice cloning training with automatic Docker management | MAIN |
| `voice/voice_extraction_pipeline.py` | Extracts clean single-speaker audio from multi-speaker video for RVC training | HELPER |
| `emotion2vec_mlx/models/emotion2vec_mlx.py` | Native MLX implementation of Emotion2Vec model architecture | HELPER |
| `emotion2vec_mlx/models/convert_to_mlx.py` | Converts extracted numpy weights to MLX format for Emotion2Vec | HELPER |
| `emotion2vec_mlx/models/convert_weights.py` | Converts Emotion2Vec PyTorch weights to MLX format | HELPER |
| `emotion2vec_mlx/models/extract_pytorch_weights.py` | Extracts Emotion2Vec weights from PyTorch to numpy | HELPER |
| `emotion2vec_mlx/models/__init__.py` | Package init for Emotion2Vec models | HELPER |

---

## 9. EXECUTION

| File | Description | Role |
|------|-------------|------|
| `execution/safe_executor.py` | Sandboxed command execution with resource limits, path validation, and environment sanitization | MAIN |
| `execution/command_classifier.py` | Classifies shell commands by risk level (SAFE/MODERATE/DANGEROUS/BLOCKED) | MAIN |
| `execution/auto_fix.py` | Automatically detects and fixes code issues using linters (ruff, black, eslint, etc.) | MAIN |
| `execution/auto_fix_control.py` | Per-project permission and rate limiting for auto-fix operations | HELPER |
| `execution/command_proposer.py` | Generates action proposals for user review instead of direct execution | HELPER |
| `execution/escalation_handler.py` | Tries local MLX first, escalates to Claude via browser bridge when needed | MAIN |
| `execution/execution_history.py` | Checkpoint creation, execution logging, and rollback capabilities | HELPER |
| `tool_system.py` | Claude Code-equivalent tool-calling: file ops, bash, git, web fetch, planning | MAIN |
| `approval_queue.py` | SQLite-backed queue for human review of SAM's proposed autonomous actions | HELPER |
| `auto_validator.py` | Automatically validates task results (syntax check, test run) without human review | HELPER |
| `execution/__init__.py` | Package init for execution system | HELPER |
| `do/__init__.py` | Package stub for execution module | HELPER |

---

## 10. API/SERVER

| File | Description | Role |
|------|-------------|------|
| `sam_api.py` | Main HTTP/CLI API (port 8765) for Tauri integration: query, projects, memory, facts, vision | MAIN |
| `vision_server.py` | Persistent vision HTTP server (port 8766) with nanoLLaVA loaded in memory | MAIN |
| `voice/voice_server.py` | FastAPI voice HTTP server for TTS with Dustin Steele RVC | MAIN |
| `serve/__init__.py` | Package stub for server module | HELPER |

---

## 11. CLI

| File | Description | Role |
|------|-------------|------|
| `sam.py` | Main CLI entry point: fast routing + direct execution + MLX inference + Claude escalation | MAIN |
| `sam_chat.py` | Interactive chat interface with MLX inference, Claude escalation, and tool execution | MAIN |
| `sam_repl.py` | Interactive REPL for terminal with command history, auto-escalation, interaction logging | MAIN |
| `sam_agent.py` | Local AI coding agent with tool access (read/write/run/search) | MAIN |
| `sam_enhanced.py` | Project-aware CLI with semantic memory, multi-agent orchestration, SSOT sync | MAIN |

---

## 12. UTILITIES

| File | Description | Role |
|------|-------------|------|
| `utils/parallel_utils.py` | ThreadPoolExecutor patterns optimized for 8GB M2 Mac Mini | HELPER |
| `utils/__init__.py` | Package init exporting ParallelExecutor, BatchProcessor | HELPER |
| `response_styler.py` | Styles SAM's responses with personality (cocky, flirty, loyal) and visual formatting | HELPER |
| `cognitive/personality.py` | SAM personality core: mode-specific system prompts, traits, training example generators | HELPER |
| `cognitive/emotional_model.py` | Mood state machine, emotional triggers, expression modulation, relationship tracking | HELPER |
| `thinking_verbs.py` | Collection of English verbs for "thinking" status messages with SAM's personality | HELPER |
| `thought_logger.py` | Logs every LLM token including discarded ideas for complete audit trail | HELPER |
| `privacy_guard.py` | Scans outgoing messages for PII/sensitive data, warns user, respects their decisions | HELPER |
| `transparency_guard.py` | Tamper-proof thinking display: ensures LLM cannot hide its output from users | HELPER |
| `conversation_logger.py` | Complete conversation history with privacy levels (full/redacted/encrypted/excluded) | HELPER |
| `impact_tracker.py` | Tracks environmental impact of LLM usage: local vs cloud energy, CO2, water | HELPER |

---

## 13. DATA COLLECTION

| File | Description | Role |
|------|-------------|------|
| `data_arsenal.py` | Intelligence gathering: site ripping, API harvesting, document extraction, pattern mining | MAIN |
| `legitimate_extraction.py` | Reverse engineering exposed APIs: AppleScript dictionaries, URL schemes, accessibility, SQLite | MAIN |
| `cognitive/app_knowledge_extractor.py` | Extracts macOS app automation capabilities (AppleScript, URL schemes, accessibility) | MAIN |
| `re_orchestrator.py` | Unified reverse engineering orchestrator: Frida, mitmproxy, OCR, desktop automation | MAIN |
| `system_orchestrator.py` | Controls scrapers, ARR stack (Radarr/Sonarr), intelligent search with filtering | MAIN |
| `warp_knowledge/analyze_warp_data.py` | Analyzes Warp terminal session data to extract patterns for SAM's knowledge base | HELPER |

---

## 14. PROJECT MANAGEMENT

| File | Description | Role |
|------|-------------|------|
| `unified_orchestrator.py` | Master project orchestrator: consolidates all projects into one cohesive system | MAIN |
| `project_dashboard.py` | Data-rich project status with SAM's voice, ranks by impact, actionable recommendations | MAIN |
| `project_status.py` | Generates rich per-project status: evolution level, activity, timeline, integration health | MAIN |
| `evolution_tracker.py` | Temporal tracking of all projects: progress history, improvements, cross-project mapping | MAIN |
| `evolution_ladders.py` | 5-level progression paths for project categories (brain, visual, voice, content, platform) | HELPER |
| `improvement_detector.py` | Scans for improvement opportunities: TODOs, missing docs, integration gaps, duplication | MAIN |
| `sam_intelligence.py` | SAM's consciousness layer: self-awareness, learning, proactive suggestions, action execution | MAIN |
| `parity_system.py` | Maps every Claude Code/ChatGPT capability to SAM's implementation strategy | HELPER |
| `exhaustive_analyzer.py` | Deep one-time project analysis: metadata, tech stack, relationships, health scoring | HELPER |
| `ssot_sync.py` | Bidirectional sync between Evolution Tracker and SSOT documentation | HELPER |
| `narrative_ui_spec.py` | Generates visual specs (symbols, palettes, animations) for Vue frontend project pages | HELPER |
| `project_permissions.py` | Per-project execution permissions for SAM's autonomous operations | HELPER |
| `startup/project_context.py` | Startup scanner: builds project registry with status, health, and git info | HELPER |
| `startup/__init__.py` | Package init for startup modules | HELPER |
| `projects/__init__.py` | Package stub for projects module | HELPER |

---

## 15. CONFIGURATION / ORCHESTRATION

| File | Description | Role |
|------|-------------|------|
| `cognitive/unified_orchestrator.py` | Integrates ALL cognitive systems: memory, retrieval, compression, control, learning, emotion | MAIN |
| `cognitive/planning_framework.py` | 4-tier solution cascade: bleeding edge down to 8GB fallback, supports seamless upgrades | MAIN |
| `claude_orchestrator.py` | Claude-to-SAM task delegation: Claude analyzes, SAM executes locally, Claude reviews | MAIN |
| `unified_daemon.py` | Manages all SAM services with priority-based resource management and RAM monitoring | MAIN |
| `proactive_notifier.py` | Background daemon pushing macOS notifications and voice announcements | MAIN |
| `terminal_coordination.py` | SQLite-based multi-terminal awareness: task broadcasting, conflict detection, context sharing | MAIN |
| `terminal_sessions.py` | Terminal session persistence, restoration, searchable history, privacy controls | HELPER |
| `auto_coordinator.py` | Transparent multi-terminal coordination: auto-registers, auto-broadcasts, auto-checks conflicts | HELPER |
| `multi_agent.py` | Spawns specialized sub-agents (Code, Review, Test, Doc, Research, Fix) for complex tasks | MAIN |
| `cognitive/multi_agent_roles.py` | Role coordination for multiple Claude Code instances (Builder, Reviewer, Tester, etc.) | HELPER |
| `cognitive/__init__.py` | Package init for cognitive system v1.13.0 with all exports | HELPER |
| `core/__init__.py` | Package stub for core brain module | HELPER |
| `think/__init__.py` | Package stub for LLM inference module | HELPER |

---

## NOT CATEGORIZED (Archive / Demos / Tests)

| File | Description | Role |
|------|-------------|------|
| `archive/autonomous_daemon.py` | **ARCHIVED** - Old autonomous improvement daemon (replaced by unified_daemon.py) | HELPER |
| `cognitive/demo_full_integration.py` | Demo exercising all cognitive systems in realistic scenarios | HELPER |
| `cognitive/test_cognitive_system.py` | Tests for cognitive system | HELPER |
| `cognitive/test_e2e_comprehensive.py` | End-to-end comprehensive tests | HELPER |
| `cognitive/test_vision_system.py` | Tests for vision system | HELPER |
| `test_evolution_system.py` | Tests for evolution tracking system | HELPER |
| `test_new_features.py` | Tests for new features | HELPER |
| `test_suite.py` | Main test suite | HELPER |
| `tests/test_auto_fix_safety.py` | Tests for auto-fix safety | HELPER |
| `tests/test_context_compression.py` | Tests for context compression | HELPER |
| `tests/test_execution_security.py` | Tests for execution security | HELPER |
| `tests/test_fact_injection.py` | Tests for fact injection | HELPER |
| `tests/test_fact_memory.py` | Tests for fact memory | HELPER |
| `tests/test_feedback_system.py` | Tests for feedback system | HELPER |
| `tests/test_image_followup.py` | Tests for image follow-up | HELPER |
| `tests/test_knowledge_distillation.py` | Tests for knowledge distillation | HELPER |
| `tests/test_project_context.py` | Tests for project context | HELPER |
| `tests/test_query_decomposer.py` | Tests for query decomposer | HELPER |
| `tests/test_rag_pipeline.py` | Tests for RAG pipeline | HELPER |
| `tests/test_training_data.py` | Tests for training data | HELPER |
| `tests/test_training_pipeline.py` | Tests for training pipeline | HELPER |
| `tests/test_vision_chat.py` | Tests for vision chat | HELPER |
| `tests/test_vision_performance.py` | Tests for vision performance | HELPER |
| `tests/test_voice_output.py` | Tests for voice output | HELPER |
| `tests/test_voice_performance.py` | Tests for voice performance | HELPER |
| `tests/__init__.py` | Tests package init | HELPER |

---

## Summary Statistics

| Category | MAIN Files | HELPER Files | Total |
|----------|-----------|-------------|-------|
| 1. Request Routing | 3 | 3 | 6 |
| 2. LLM Inference | 3 | 6 | 9 |
| 3. Voice Input | 2 | 11 | 13 |
| 4. Voice Output | 4 | 7 | 11 |
| 5. Vision | 5 | 5 | 10 |
| 6. Memory | 5 | 9 | 14 |
| 7. Learning | 8 | 4 | 12 |
| 8. Training | 10 | 11 | 21 |
| 9. Execution | 5 | 7 | 12 |
| 10. API/Server | 3 | 1 | 4 |
| 11. CLI | 5 | 0 | 5 |
| 12. Utilities | 0 | 11 | 11 |
| 13. Data Collection | 5 | 1 | 6 |
| 14. Project Management | 6 | 9 | 15 |
| 15. Configuration/Orchestration | 6 | 7 | 13 |
| Archive/Demos/Tests | 0 | 26 | 26 |
| **TOTAL** | **70** | **118** | **188** |

Note: `.auto_fix_backups/` directory contains timestamped backup copies and is excluded from this map.
The `code_indexer.py` at root level and `cognitive/code_indexer.py` are separate modules with incompatible schemas -- the root-level one is categorized under Memory (semantic search) while the cognitive one is under Memory (RAG retrieval). Both are HELPER files within the Memory category, used by the retrieval pipeline.
