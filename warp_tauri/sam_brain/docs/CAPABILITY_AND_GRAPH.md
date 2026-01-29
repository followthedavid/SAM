# SAM Brain: Capability Matrix & Knowledge Graph

**Generated:** 2026-01-29
**Version:** v0.5.0 (Full Multi-Modal - MLX Native)
**Hardware:** M2 Mac Mini, 8GB RAM

---

## Capability Matrix

| Capability | Files | API Endpoint | Dependencies | Working? | Documented? |
|---|---|---|---|---|---|
| **Chat** | `orchestrator.py`, `sam_chat.py`, `sam_enhanced.py`, `cognitive/mlx_cognitive.py`, `cognitive/mlx_optimized.py`, `response_styler.py` | `POST /api/chat`, `POST /api/query` | `mlx_lm`, Qwen2.5-1.5B/3B + SAM LoRA | Yes | Yes (`CLAUDE.md`, `ARCHITECTURE.md`) |
| **Code Assist** | `orchestrator.py` (CODE route), `tool_system.py`, `code_indexer.py`, `cognitive/code_indexer.py`, `sam_agent.py` | `POST /api/query` (routed CODE), `POST /api/index/search` | `mlx_lm`, `ast`, file system access | Yes | Yes (`EXECUTION_SYSTEM.md`) |
| **Voice STT** | `voice/voice_pipeline.py`, `conversation_engine/engine.py`, `conversation_engine/turn_predictor.py`, `audio_utils.py` | `POST /api/voice/process`, `POST /api/voice/stream`, `GET /api/voice/start` | `whisper` (MLX), `soundfile`, `numpy` | Partial -- pipeline wired, needs Whisper MLX | Yes (`docs/VOICE_SYSTEM.md`) |
| **Voice TTS** | `tts_pipeline.py`, `voice/voice_output.py`, `voice/voice_server.py`, `voice/voice_settings.py`, `voice/voice_cache.py` | `GET /api/voice/status`, `PUT /api/voice/settings` | macOS `say` (fallback), F5-TTS (optional), `edge_tts` (optional), Coqui TTS (optional) | Yes -- macOS `say` always works; F5-TTS optional | Yes (`docs/VOICE_SYSTEM.md`, `docs/VOICE_OUTPUT_AUDIT.md`) |
| **Voice Cloning** | `voice/voice_trainer.py`, `voice/voice_extraction_pipeline.py`, `voice/voice_preprocessor.py` | None (CLI/daemon triggered) | Docker, RVC WebUI, audio samples (10+ min) | Partial -- Docker on-demand, RVC WebUI needed | Yes (`VOICE_EXTRACTION.md`, `IPHONE_VOICE_SETUP.md`) |
| **Vision/OCR** | `apple_ocr.py`, `cognitive/vision_engine.py`, `cognitive/smart_vision.py`, `cognitive/vision_client.py`, `cognitive/vision_selector.py`, `cognitive/image_preprocessor.py`, `vision_server.py` | `POST /api/vision/ocr`, `POST /api/vision/process`, `POST /api/vision/describe`, `POST /api/vision/detect`, `POST /api/vision/smart`, `GET /api/vision/models` | Apple Vision (pyobjc, zero RAM), nanoLLaVA (1.5GB), SmolVLM (optional), Claude escalation | Yes -- OCR via Apple Vision (22ms, 0 RAM); VLM via nanoLLaVA | Yes (`CLAUDE.md` vision section) |
| **Image Gen** | `image_generator.py`, `comfyui_client.py` | `POST /api/query` (routed IMAGE) | `mflux` (native MLX Stable Diffusion) or ComfyUI (local server) | Partial -- mflux needs `pipx install mflux`; ComfyUI needs running server | Minimal |
| **Memory/Recall** | `memory/semantic_memory.py`, `memory/conversation_memory.py`, `memory/fact_memory.py`, `memory/context_budget.py`, `memory/infinite_context.py`, `memory/project_context.py`, `cognitive/enhanced_memory.py`, `cognitive/enhanced_retrieval.py` | `GET /api/memory`, `POST /api/facts/*`, `POST /api/query` (context injection) | `mlx` (MiniLM-L6-v2 embeddings, 384-dim), `numpy`, `sqlite3` | Yes | Yes (`FACT_SCHEMA.md`, `CONTEXT_COMPRESSION.md`) |
| **Learn from Claude** | `claude_learning.py`, `knowledge_distillation.py`, `auto_learner.py`, `claude_orchestrator.py` | None (daemon/background) | `watchdog` (file watcher), `sqlite3`, `~/.claude/` conversation files | Yes -- auto_learner daemon watches Claude sessions | Yes (`DISTILLATION.md`, `DISTILLATION_FORMAT.md`) |
| **Learn from Feedback** | `feedback_system.py`, `memory/rag_feedback.py`, `cognitive/enhanced_learning.py`, `cognitive/learning_strategy.py` | `POST /api/feedback`, `GET /api/feedback/stats` | `sqlite3`, external drive `/Volumes/David External/sam_memory/feedback.db` | Yes | Yes (`FEEDBACK_FORMAT.md`, `FEEDBACK_LEARNING.md`) |
| **Command Execution** | `execution/safe_executor.py`, `execution/command_classifier.py`, `execution/command_proposer.py`, `execution/auto_fix.py`, `execution/auto_fix_control.py`, `execution/execution_history.py`, `tool_system.py` | `POST /api/query` (routed CODE/TERMINAL) | `subprocess`, `resource` (macOS), `shlex` | Yes -- sandboxed with risk classification | Yes (`EXECUTION_SYSTEM.md`, `AUTO_FIX.md`) |
| **Project Awareness** | `project_dashboard.py`, `project_status.py`, `project_permissions.py`, `ssot_sync.py`, `code_indexer.py`, `cognitive/code_indexer.py`, `cognitive/doc_indexer.py`, `startup/project_context.py` | `GET /api/projects`, `GET /api/categories`, `GET /api/starred`, `POST /api/index/*` | `sqlite3`, SSOT docs at `/Volumes/Plex/SSOT/`, `projects.json` | Yes | Yes (`PROJECT_STATUS.md`) |
| **Emotion Detection** | `emotion2vec_mlx/detector.py`, `emotion2vec_mlx/taxonomy.py`, `emotion2vec_mlx/prosody_control.py`, `emotion2vec_mlx/backends/prosodic_backend.py`, `emotion2vec_mlx/backends/emotion2vec_backend.py`, `cognitive/emotional_model.py` | `GET /api/voice/emotion` | `numpy`, prosodic analysis (zero-cost), emotion2vec MLX model (optional) | Partial -- prosodic backend works; full emotion2vec needs model weights | Yes (`VOICE_EMOTION_DESIGN.md`) |
| **Self-Improvement** | `sam_intelligence.py`, `evolution_tracker.py`, `evolution_ladders.py`, `improvement_detector.py`, `perpetual_learner.py`, `training_runner.py`, `training_pipeline.py`, `training_data.py`, `training_prep.py`, `training_scheduler.py`, `training_capture.py`, `parity_system.py`, `auto_validator.py` | `GET /api/suggest`, `GET /api/scan`, `GET /api/learning` | `sqlite3` (`evolution.db`), `mlx_lm` (LoRA training), external storage | Yes -- perpetual learner daemon runs continuously | Yes (`PERPETUAL_LADDER_ARCHITECTURE.md`, `ADVANCEMENT_ROADMAP.md`) |
| **Data Scraping** | `data_arsenal.py`, `legitimate_extraction.py`, `doc_ingestion.py` | `POST /api/query` (routed DATA) | `urllib`, `asyncio`, `sqlite3`, `BeautifulSoup` (optional) | Yes | Yes (`DATA_ARSENAL_AUDIT.md`) |

### Status Legend
- **Yes** = Functional and tested
- **Partial** = Core logic exists but some dependencies missing or not fully integrated
- **Minimal** = Code present but limited documentation

---

## Knowledge Graph

### FILE -> imports -> FILE

```
orchestrator.py
  -> cognitive/mlx_cognitive.py (MLXCognitiveEngine, GenerationConfig)
  -> impact_tracker.py (ImpactTracker)
  -> privacy_guard.py (PrivacyGuard)
  -> response_styler.py (style_success, style_error, ...)
  -> thinking_verbs.py (get_thinking_verb)
  -> transparency_guard.py (TransparencyGuard)
  -> thought_logger.py (ThoughtLogger)
  -> conversation_logger.py (ConversationLogger)
  -> live_thinking.py (stream_thinking)
  -> project_dashboard.py (DashboardGenerator)
  -> data_arsenal.py (DataArsenal)
  -> terminal_coordination.py (TerminalCoordinator)
  -> auto_coordinator.py (get_coordinator, CoordinatedSession)

sam_api.py
  -> approval_queue.py (api_approval_*)
  -> feedback_system.py (FeedbackDB)
  -> knowledge_distillation.py (DistillationDB)
  -> sam_intelligence.py (SAMIntelligence)

sam_chat.py
  -> execution/escalation_handler.py (process_request, EscalationReason)
  -> smart_router.py (Provider, sanitize_content)

sam_enhanced.py
  -> orchestrator.py
  -> sam_chat.py

sam_intelligence.py
  -> evolution_tracker.py (EvolutionTracker, Improvement)
  -> improvement_detector.py (ImprovementDetector)
  -> evolution_ladders.py (LadderAssessor, EVOLUTION_LADDERS)

tts_pipeline.py
  -> cognitive/resource_manager.py (ResourceManager, VoiceTier)
  -> voice/voice_cache.py (VoiceCache)

voice/voice_pipeline.py
  -> emotion2vec_mlx/ (VoiceEmotionDetector, EmotionToProsody, ProsodyApplicator)
  -> conversation_engine/ (ConversationEngine, ConversationMode, ConversationEvent)

voice/voice_output.py
  (standalone - uses subprocess for macOS say, Coqui, RVC)

cognitive/mlx_cognitive.py
  -> cognitive/resource_manager.py (ResourceManager, ResourceLevel)
  -> mlx_lm (load, generate)

cognitive/vision_engine.py
  -> cognitive/resource_manager.py
  -> cognitive/image_preprocessor.py

execution/escalation_handler.py
  -> smart_router.py (estimate_complexity, sanitize_content, Provider)
  -> cognitive/ (create_cognitive_orchestrator)
  -> execution/escalation_learner.py (EscalationLearner)

execution/safe_executor.py
  -> execution/command_classifier.py (CommandClassifier)
  (standalone - subprocess, resource limits)

perpetual_learner.py
  -> cognitive/resource_manager.py (can_train)

auto_learner.py
  -> cognitive/resource_manager.py (can_train)
  -> watchdog (Observer, FileSystemEventHandler)

claude_learning.py
  (standalone - reads ~/.claude/ conversation files)

knowledge_distillation.py
  (standalone - sqlite3, reads Claude conversation data)

memory/semantic_memory.py
  -> mlx (MiniLM-L6-v2 via sentence-transformers)
  -> numpy

code_indexer.py
  -> mlx (MiniLM-L6-v2 embeddings)
  -> numpy, ast, sqlite3

emotion2vec_mlx/detector.py
  -> emotion2vec_mlx/taxonomy.py (EmotionResult, EmotionCategory)
  -> emotion2vec_mlx/backends/ (get_available_backends, create_backend)

conversation_engine/engine.py
  -> conversation_engine/state.py (ConversationState, Speaker)
  -> conversation_engine/turn_predictor.py (TurnPredictor)
  -> conversation_engine/events.py (ConversationEvent, EventType)

feedback_system.py
  -> sqlite3 (feedback.db)

ssot_sync.py
  -> /Volumes/Plex/SSOT/ (reads/writes SSOT docs)

tool_system.py
  (standalone - subprocess, pathlib, fnmatch, difflib)
```

### FILE -> defines -> CLASS

```
orchestrator.py -> (functions: route_request, warm_models, process_message)
sam_api.py -> (functions: main, server mode, CLI handlers)
sam_chat.py -> (functions: query_sam_brain, queue_browser_request)
sam_intelligence.py -> SamState, SAMIntelligence
cognitive/mlx_cognitive.py -> ModelSize, ModelConfig, MLXCognitiveEngine, GenerationConfig
cognitive/vision_engine.py -> VisionTier, VisionResult, VisionEngine
cognitive/emotional_model.py -> MoodState, EmotionalModel
cognitive/resource_manager.py -> ResourceManager, ResourceLevel, VoiceTier
cognitive/model_selector.py -> ModelSelector
cognitive/token_budget.py -> TokenBudget
cognitive/quality_validator.py -> QualityValidator
cognitive/enhanced_memory.py -> EnhancedMemory
cognitive/enhanced_retrieval.py -> EnhancedRetrieval
cognitive/enhanced_learning.py -> EnhancedLearning
cognitive/learning_strategy.py -> LearningStrategy
cognitive/smart_vision.py -> SmartVision
cognitive/vision_client.py -> VisionClient
cognitive/vision_selector.py -> VisionSelector
cognitive/image_preprocessor.py -> ImagePreprocessor
cognitive/self_knowledge_handler.py -> SelfKnowledgeHandler
cognitive/personality.py -> Personality
cognitive/planning_framework.py -> PlanningFramework
cognitive/compression.py -> ContextCompressor
cognitive/cognitive_control.py -> CognitiveControl
cognitive/code_indexer.py -> CodeIndexer
cognitive/doc_indexer.py -> DocIndexer
cognitive/unified_orchestrator.py -> UnifiedOrchestrator
tts_pipeline.py -> TTSEngine, QualityLevel, TTSPipeline
voice/voice_pipeline.py -> VoicePipelineConfig, SAMVoicePipeline
voice/voice_output.py -> VoiceConfig
voice/voice_cache.py -> VoiceCache
voice/voice_settings.py -> VoiceSettings
voice/voice_server.py -> VoiceServer
voice/voice_trainer.py -> VoiceTrainer
voice/voice_extraction_pipeline.py -> VoiceExtractionPipeline
voice/voice_preprocessor.py -> VoicePreprocessor
voice/voice_bridge.py -> VoiceBridge
conversation_engine/engine.py -> ConversationMode, EngineConfig, ConversationEngine
conversation_engine/state.py -> ConversationState, Speaker, ConversationPhase
conversation_engine/turn_predictor.py -> TurnPredictor, TurnPrediction
conversation_engine/events.py -> ConversationEvent, EventType
emotion2vec_mlx/detector.py -> VoiceEmotionDetector
emotion2vec_mlx/taxonomy.py -> EmotionResult, EmotionCategory
emotion2vec_mlx/prosody_control.py -> EmotionToProsody, ProsodyApplicator
emotion2vec_mlx/backends/prosodic_backend.py -> ProsodicBackend
emotion2vec_mlx/backends/emotion2vec_backend.py -> Emotion2VecBackend
emotion2vec_mlx/models/emotion2vec_mlx.py -> Emotion2VecMLX
execution/safe_executor.py -> SafeExecutor, ExecutionResult
execution/command_classifier.py -> CommandType, RiskLevel, CommandClassifier
execution/command_proposer.py -> CommandProposer
execution/auto_fix.py -> AutoFix
execution/auto_fix_control.py -> AutoFixControl
execution/escalation_handler.py -> EscalationReason, EscalationResult
execution/escalation_learner.py -> EscalationLearner
execution/execution_history.py -> ExecutionHistory
memory/semantic_memory.py -> MemoryEntry, SemanticMemory
memory/conversation_memory.py -> ConversationMemory
memory/fact_memory.py -> FactMemory
memory/context_budget.py -> ContextBudget
memory/infinite_context.py -> InfiniteContext
memory/project_context.py -> ProjectContext
memory/rag_feedback.py -> RAGFeedback
feedback_system.py -> FeedbackType, FeedbackEntry, FeedbackDB, CorrectionAnalyzer, ConfidenceAdjuster
knowledge_distillation.py -> DistillationDB
claude_learning.py -> TrainingPair, ConversationAnalysis, ClaudeLearner
auto_learner.py -> TrainingExample, AutoLearningDB, AutoLearner
perpetual_learner.py -> TaskType, TaskPriority, CurriculumManager, PerpetualLearner
training_runner.py -> TrainingStatus, TrainingConfig, TrainingRunner
training_data.py -> TrainingData
training_prep.py -> TrainingPrep
training_scheduler.py -> TrainingScheduler
training_stats.py -> TrainingStats
training_capture.py -> TrainingCapture
data_arsenal.py -> SourceType, ExtractionType, DataArsenal
code_indexer.py -> CodeIndexer (semantic variant)
smart_router.py -> Provider, RoutingDecision
tool_system.py -> ToolCategory, ToolResult, ToolSystem
approval_queue.py -> ApprovalQueue
project_dashboard.py -> DashboardGenerator
project_status.py -> ProjectStatus
project_permissions.py -> ProjectPermissions
ssot_sync.py -> SyncState, ProjectDocInfo
image_generator.py -> ImageGenerator
comfyui_client.py -> ComfyUIClient
apple_ocr.py -> (functions: extract_text, extract_text_simple)
evolution_tracker.py -> EvolutionTracker, Improvement
evolution_ladders.py -> LadderAssessor, EVOLUTION_LADDERS
improvement_detector.py -> ImprovementDetector
parity_system.py -> ParitySystem
auto_validator.py -> AutoValidator
privacy_guard.py -> PrivacyGuard
transparency_guard.py -> TransparencyGuard
response_styler.py -> ResponseType, style_*
thinking_verbs.py -> get_thinking_verb
thought_logger.py -> ThoughtLogger, ThoughtPhase
conversation_logger.py -> ConversationLogger, PrivacyLevel, MessageRole
live_thinking.py -> stream_thinking, classify_thought
terminal_coordination.py -> TerminalCoordinator
terminal_sessions.py -> TerminalSessions
auto_coordinator.py -> AutoCoordinator, CoordinatedSession
unified_daemon.py -> UnifiedDaemon
unified_orchestrator.py -> UnifiedOrchestrator (root-level)
model_deployment.py -> ModelDeployment
mlx_inference.py -> (functions: load_model, set_mode, inference)
```

### CLASS -> inherits -> CLASS

```
(Most classes are standalone dataclasses or use composition over inheritance.)
(Key composition patterns documented below instead.)

MoodState -> Enum
TTSEngine -> Enum
QualityLevel -> Enum
ModelSize -> Enum
CommandType -> Enum
RiskLevel -> Enum
Provider -> Enum
SourceType -> Enum
ExtractionType -> Enum
TaskType -> Enum
TaskPriority -> Enum
TrainingStatus -> Enum
FeedbackType -> Enum
ConversationMode -> Enum
VisionTier -> Enum
ResourceLevel -> Enum
EventType -> Enum
Speaker -> Enum
ConversationPhase -> Enum
```

### FILE -> reads/writes -> DATABASE

```
feedback_system.py -> /Volumes/David External/sam_memory/feedback.db (SQLite)
                   -> ~/.sam/feedback.db (fallback)

knowledge_distillation.py -> /Volumes/David External/sam_training/distilled/distillation.db (SQLite)
                          -> ~/.sam/knowledge_distillation.db (fallback)

auto_learner.py -> sam_brain/auto_learning.db (SQLite)

evolution_tracker.py -> sam_brain/evolution.db (SQLite)

perpetual_learner.py -> /Volumes/David External/sam_learning/curriculum.db (SQLite)
                     -> sam_brain/.perpetual_state.json (JSON state)

code_indexer.py -> /Volumes/David External/sam_memory/code_index_semantic.db (SQLite)

cognitive/code_indexer.py -> /Volumes/David External/sam_memory/code_index.db (SQLite)

memory/semantic_memory.py -> sam_brain/memory/embeddings.json (JSON)
                          -> sam_brain/memory/index.npy (numpy arrays)

cognitive/emotional_model.py -> (SQLite, path in code)

sam_intelligence.py -> sam_brain/.sam_intelligence_cache.json (JSON)
                    -> sam_brain/.sam_state.json (JSON)
                    -> sam_brain/.sam_learning.json (JSON)

data_arsenal.py -> (SQLite, internal DB)

conversation_logger.py -> (JSON logs at /Volumes/Plex/SSOT/sam_conversations.json)

ssot_sync.py -> sam_brain/.ssot_sync_state.json (JSON)
            -> /Volumes/Plex/SSOT/ (reads/writes markdown docs)

execution/execution_history.py -> (JSONL log at ~/.sam/execution_log.jsonl)

execution/safe_executor.py -> ~/.sam/backups/ (file backups)
                           -> ~/.sam/execution_log.jsonl (audit log)

training_runner.py -> sam_brain/training_logs/ (training metrics)
                   -> sam_brain/training_runs.json (JSON)

training_stats.py -> sam_brain/.training_stats_cache.json (JSON)
```

### FILE -> uses -> EXTERNAL_SERVICE

```
orchestrator.py -> MLX (local Apple Silicon inference via mlx_lm)

cognitive/mlx_cognitive.py -> MLX (mlx_lm.load, mlx_lm.generate)
                           -> Qwen2.5-1.5B-Instruct / Qwen2.5-3B-Instruct (local models)

mlx_inference.py -> MLX (mlx_lm.load, mlx_lm.generate)
                 -> Josiefied-Qwen2.5-1.5B-Instruct-abliterated (base model)

memory/semantic_memory.py -> MLX (MiniLM-L6-v2 sentence embeddings)

code_indexer.py -> MLX (MiniLM-L6-v2 sentence embeddings)

apple_ocr.py -> Apple Vision Framework (pyobjc, macOS Neural Engine)

cognitive/vision_engine.py -> nanoLLaVA (MLX VLM, local)
                           -> SmolVLM (MLX, optional)
                           -> Claude (terminal escalation for complex vision)

tts_pipeline.py -> macOS say (built-in TTS)
               -> F5-TTS (optional, local neural TTS)
               -> edge_tts (optional, Microsoft Edge TTS API)
               -> Coqui TTS (optional, local)

voice/voice_output.py -> macOS say (subprocess)
                      -> Coqui TTS (optional)
                      -> RVC (voice cloning, Docker-based)

voice/voice_trainer.py -> Docker (RVC WebUI container)

image_generator.py -> mflux (MLX Stable Diffusion, local)

comfyui_client.py -> ComfyUI (local server at 127.0.0.1:8188)

smart_router.py -> Claude (browser bridge escalation)
               -> ChatGPT (browser bridge escalation)

execution/escalation_handler.py -> Claude (browser bridge for complex tasks)

auto_learner.py -> watchdog (filesystem monitoring of ~/.claude/)

data_arsenal.py -> urllib (web scraping)
               -> GitHub API, HackerNews API, Reddit, arXiv, RSS feeds

ssot_sync.py -> /Volumes/Plex/SSOT/ (external SSOT documentation store)

perpetual_learner.py -> /Volumes/David External/ (external storage for models/data)

sam_api.py -> HTTP server (port 8765, aiohttp/flask)

vision_server.py -> HTTP server (port 8766)

voice/voice_server.py -> HTTP server (voice API)

emotion2vec_mlx/ -> MLX (emotion detection model, optional)
                 -> prosodic analysis (numpy, zero-cost acoustic features)
```

---

## Architecture Summary

```
                         +--------------------------+
                         |     ENTRY POINTS         |
                         |  sam_api.py (port 8765)  |
                         |  sam_chat.py (CLI)       |
                         |  sam_repl.py (REPL)      |
                         |  sam.py (launcher)       |
                         +-----------+--------------+
                                     |
                         +-----------v--------------+
                         |     ORCHESTRATION        |
                         |  orchestrator.py         |
                         |  smart_router.py         |
                         |  unified_orchestrator.py |
                         +-----------+--------------+
                                     |
          +----------+-------+-------+-------+-----------+
          |          |       |       |       |           |
     +----v---+ +---v--+ +-v----+ +v-----+ +v--------+ +v---------+
     | THINK  | |SPEAK | |LISTEN| | SEE  | |REMEMBER | |    DO    |
     | mlx_   | |tts_  | |voice/| |vision| |semantic | |execution/|
     | cogni  | |pipe  | |pipe  | |engine| |_memory  | |safe_exec |
     | tive   | |line  | |line  | |      | |fact_mem | |cmd_class |
     +----+---+ +------+ +------+ +------+ +----+----+ +----------+
          |                                      |
     +----v---------+                    +-------v--------+
     |   LEARN      |                    |   PROJECTS     |
     | auto_learner |                    | project_dash   |
     | perpetual_   |                    | ssot_sync      |
     | claude_learn |                    | code_indexer   |
     | knowledge_   |                    +----------------+
     | distillation |
     | training_*   |
     +--------------+
```

## Key Data Flows

1. **Chat Request**: `sam_api.py` -> `orchestrator.py` (route) -> `cognitive/mlx_cognitive.py` (generate) -> `response_styler.py` (style) -> response
2. **Voice Interaction**: mic -> `voice/voice_pipeline.py` (STT) -> `conversation_engine/` (turn mgmt) -> `cognitive/` (generate) -> `tts_pipeline.py` (TTS) -> speaker
3. **Learning Loop**: `auto_learner.py` (watch ~/.claude/) -> extract training pairs -> `auto_learning.db` -> `training_runner.py` (fine-tune) -> updated LoRA adapters
4. **Vision**: image -> `cognitive/vision_engine.py` (select tier) -> Apple OCR / nanoLLaVA / Claude -> response
5. **Command Execution**: request -> `execution/command_classifier.py` (classify risk) -> `execution/safe_executor.py` (sandbox) -> `approval_queue.py` (if needed) -> execute
6. **Memory Recall**: query -> `memory/semantic_memory.py` (embed + search) -> relevant memories -> inject into prompt context
7. **Self-Improvement**: `perpetual_learner.py` (daemon) -> scan for improvements -> `evolution_tracker.py` (track) -> `training_runner.py` (train) -> deploy
