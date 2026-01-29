# SAM Brain Function Call Graph

Generated: 2026-01-28

This document traces actual function call chains from HTTP entry points through the codebase.

## Table of Contents

1. [Entry Points (sam_api.py)](#entry-points)
2. [Call Chains by Route](#call-chains-by-route)
3. [Hot Paths (Most-Called Functions)](#hot-paths)
4. [Dead Code (Never Called)](#dead-code)
5. [Circular Call Patterns](#circular-patterns)
6. [Dependency Summary](#dependency-summary)

---

## Entry Points

### HTTP Server Entry Points (sam_api.py)

The `run_server()` function creates an HTTPServer with `SAMHandler` class that routes requests:

```
run_server(port=8765)
  -> HTTPServer(SAMHandler)
     -> do_GET() / do_POST() / do_DELETE()
        -> api_* functions
```

### Primary API Functions (72 total)

| Route | Method | API Function | Calls |
|-------|--------|--------------|-------|
| `/api/status` | GET | `api_status()` | `load_inventory()`, `MLXCognitiveEngine` |
| `/api/projects` | GET | `api_projects()` | `load_inventory()` |
| `/api/memory` | GET | `api_memory()` | `load_memory()` |
| `/api/query` | GET/POST | `api_query()` | `find_project()`, `route()`, `sam()` |
| `/api/self` | GET | `api_self()` | `get_sam_intelligence()`, `get_distillation_stats()`, `get_compression_monitor()`, `get_vision_stats_monitor()`, `get_training_stats()` |
| `/api/suggest` | GET | `api_suggest()` | `get_sam_intelligence()` |
| `/api/proactive` | GET | `api_proactive()` | `get_sam_intelligence()` |
| `/api/learning` | GET | `api_learning()` | `get_sam_intelligence()` |
| `/api/scan` | GET | `api_scan()` | `ImprovementDetector.detect_all()` |
| `/api/think` | GET/POST | `api_think()` | `get_sam_intelligence().think()` |
| `/api/orchestrate` | POST | `api_orchestrate()` | `orchestrate()` from orchestrator.py |
| `/api/cognitive/process` | GET/POST | `api_cognitive_process()` | `get_cognitive_orchestrator().process()` |
| `/api/cognitive/state` | GET | `api_cognitive_state()` | `get_cognitive_orchestrator().get_state()` |
| `/api/cognitive/feedback` | POST | `api_cognitive_feedback()` | `get_feedback_db()`, `intelligence_core`, `EscalationLearner` |
| `/api/vision/*` | GET/POST | `api_vision_*()` | `get_vision_engine()`, `SmartVisionRouter` |
| `/api/voice/*` | GET/POST | `api_voice_*()` | `get_voice_pipeline()` |
| `/api/facts/*` | GET/POST/DELETE | `api_facts_*()` | `get_fact_db()` |

---

## Call Chains by Route

### 1. Main Orchestration Chain

```
POST /api/orchestrate
  -> api_orchestrate(message)
     -> from execution.escalation_handler import process_request
        -> process_request(message, auto_escalate)
           -> evaluate_complexity(message)
           -> SAM cognitive attempt
           -> evaluate_response()
           -> escalate_to_claude() if needed
        (fallback) -> orchestrate(message)  # from orchestrator.py

orchestrate(message)  # orchestrator.py:1280
  |
  +-> AUTO_COORD.check_conflicts(message)   # terminal coordination
  +-> AUTO_COORD.start_task()
  +-> route_request(message)                # keyword-based routing
  |     -> returns: CHAT|ROLEPLAY|CODE|REASON|IMAGE|PROJECT|IMPROVE|DATA|TERMINAL|VOICE|RE
  |
  +-> handlers[route](message)
  |     -> handle_chat(m)       -> _mlx_generate()
  |     -> handle_roleplay(m)   -> _mlx_generate()
  |     -> handle_code(m)       -> _mlx_generate() + subprocess.run()
  |     -> handle_reason(m)     -> guard_outgoing() + _mlx_generate()
  |     -> handle_image(m)      -> image_generate() / generate_image()
  |     -> handle_improve(m)    -> SamIntelligence.*()
  |     -> handle_project(m)    -> DashboardGenerator.*()
  |     -> handle_data(m)       -> DataArsenal.*()
  |     -> handle_terminal(m)   -> TerminalCoordinator.*()
  |     -> handle_voice(m)      -> voice_trainer.*()
  |     -> handle_re(m)         -> handle_re_request()
  |
  +-> TRANSPARENCY_GUARD.process_chunk()
  +-> THOUGHT_LOGGER.log_token()
  +-> CONVERSATION_LOGGER.log_*()
  +-> track_impact()
  +-> AUTO_COORD.finish_task()
```

### 2. Cognitive Processing Chain

```
POST /api/cognitive/process
  -> api_cognitive_process(query, user_id)
     -> get_cognitive_orchestrator()
        -> create_cognitive_orchestrator()  # from cognitive/__init__.py
           -> CognitiveOrchestrator(db_path, retrieval_paths)
              -> EnhancedMemoryManager()
              -> EnhancedRetrievalSystem()
              -> CognitiveControl()
              -> EnhancedLearningSystem()
              -> EmotionalModel()
              -> MLXCognitiveEngine()
     -> orchestrator.process(query, user_id)
        -> memory.get_context()
        -> retrieval.retrieve()
        -> cognitive_control.evaluate()
        -> mlx_engine.generate()
        -> emotional.update_state()
```

### 3. Vision Processing Chain

```
POST /api/vision/smart
  -> api_vision_smart(image_path, prompt, ...)
     -> get_smart_vision_router()
        -> SmartVisionRouter()  # from cognitive/smart_vision.py
     -> router.process(image_path, prompt)
        -> analyze_task(prompt)
        -> select_tier()  # ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE
        |
        +-> ZERO_COST: apple_ocr.extract_text() / PIL analysis
        +-> LIGHTWEIGHT: CoreML face detection
        +-> LOCAL_VLM: mlx_vlm.load() + generate()
        +-> CLAUDE: terminal escalation
     -> record_vision_stats()

POST /api/vision/ocr
  -> api_vision_ocr(image_path)
     -> apple_ocr.extract_text()  # primary - fast, accurate
     -> (fallback) get_vision_engine().process_image()
```

### 4. SAM Intelligence Chain

```
GET /api/self
  -> api_self()
     -> get_sam_intelligence()
        -> SamIntelligence()  # from sam_intelligence.py
           -> IntelligenceCache()
           -> _load_state() -> SamState
           -> _load_learning() -> Dict[str, LearningPattern]
           -> _update_awareness()
              -> tracker.get_all_projects()
              -> tracker.get_improvements()
              -> memory.get_all_improvement_stats()
     -> sam.explain_myself()
     -> sam.get_self_status()
     -> get_distillation_stats()
        -> get_distillation_db().get_stats()
     -> get_compression_monitor().get_summary_for_self()
     -> get_vision_stats_monitor().get_summary_for_self()
     -> get_training_stats()
        -> TrainingPipeline().stats()
        -> get_deployer().get_deployment_stats()

GET /api/suggest
  -> api_suggest(limit)
     -> sam.get_top_suggestions_fast(limit)
        -> cache.get("suggestions")
        -> (if miss) detector.detect_all()
        -> _score_and_rank()
        -> _apply_learning()
```

### 5. Voice Pipeline Chain

```
POST /api/voice/process
  -> api_voice_process_audio(audio_base64)
     -> get_voice_pipeline()
        -> SAMVoicePipeline()  # from voice/voice_pipeline.py
           -> VoicePipelineConfig()
           -> emotion2vec detector
           -> prosody_control
           -> rvc_model (if enabled)
     -> pipeline.process_audio(audio_chunk)
        -> detect_emotion()
        -> check_turn_end()
        -> generate_response() if needed
        -> apply_prosody()
        -> rvc_convert() if enabled
        -> yield events
```

### 6. Facts/Memory Chain

```
GET /api/facts
  -> api_facts_list(user_id, category, min_confidence, limit)
     -> from memory.fact_memory import get_fact_db
     -> db.get_facts(user_id, category, min_confidence, limit)
        -> SQLite query with filtering

POST /api/facts
  -> api_facts_add(fact, category, user_id, source, confidence)
     -> db.save_fact(fact, category, source, confidence, user_id)
        -> check_duplicate()
        -> _calculate_confidence()
        -> INSERT/UPDATE fact
```

---

## Hot Paths (Most-Called Functions)

Based on call chain analysis, these functions are in the most critical paths:

### Tier 1: Called on Nearly Every Request

| Function | Location | Called By |
|----------|----------|-----------|
| `get_cognitive_orchestrator()` | sam_api.py:1336 | 15+ API endpoints |
| `_update_activity()` | sam_api.py:1511 | All cognitive endpoints |
| `get_sam_intelligence()` | sam_api.py:186 | 8 API endpoints |
| `datetime.now().isoformat()` | everywhere | All API responses |

### Tier 2: Called by Multiple Routes

| Function | Location | Called By |
|----------|----------|-----------|
| `_mlx_generate()` | orchestrator.py:278 | handle_chat, handle_roleplay, handle_code, handle_reason, handle_improve |
| `route_request()` | orchestrator.py:168 | orchestrate(), CONVERSATION_LOGGER |
| `get_compression_monitor()` | sam_api.py:398 | api_self(), api_context_stats() |
| `get_vision_stats_monitor()` | sam_api.py:653 | api_self(), all vision endpoints |
| `record_vision_stats()` | sam_api.py:661 | All vision endpoints |
| `get_vision_engine()` | sam_api.py:2963 | 7 vision endpoints |
| `get_smart_vision_router()` | sam_api.py:3520 | api_vision_smart(), api_vision_stats() |
| `get_voice_pipeline()` | sam_api.py:3833 | 8 voice endpoints |
| `get_feedback_db()` | sam_api.py:79 | 6 feedback endpoints |
| `get_distillation_db()` | sam_api.py:94 | 7 distillation endpoints |

### Tier 3: Core Processing

| Function | Location | Called By |
|----------|----------|-----------|
| `orchestrate()` | orchestrator.py:1280 | api_orchestrate() fallback |
| `handle_*()` handlers | orchestrator.py | orchestrate() |
| `track_impact()` | orchestrator.py:1263 | orchestrate() |
| `MLXCognitiveEngine.generate()` | cognitive/mlx_cognitive.py | _mlx_generate(), cognitive process |

---

## Dead Code (Never Called)

Functions that exist but are not in any call chain:

### orchestrator.py

| Function | Line | Status | Notes |
|----------|------|--------|-------|
| `warm_models()` | 151 | RARELY USED | Only called via CLI `python orchestrator.py warm` |

### sam_api.py

| Function | Line | Status | Notes |
|----------|------|--------|-------|
| `api_speak()` | 938 | UNREACHABLE | No route in HTTP server |
| `api_voices()` | 962 | UNREACHABLE | No route in HTTP server |
| `api_code_index()` | 2399 | ROUTED | Called via POST /api/code/index |

### cognitive/__init__.py Exports

The following exports exist but may not be actively used:

| Export | Module | Status |
|--------|--------|--------|
| `SleepConsolidator` | enhanced_learning.py | POTENTIALLY UNUSED - Requires daemon |
| `CrossEncoderReranker` | enhanced_retrieval.py | CONDITIONALLY USED - Falls back if MLX unavailable |
| `get_role_prompt()` | multi_agent_roles.py | MULTI-AGENT ONLY - For Claude coordination |
| `stream_evaluate()` | model_evaluation.py | BENCHMARKING ONLY |
| `export_training_examples()` | personality.py | TRAINING ONLY |

### Legacy Functions (sam_enhanced.py imports)

```python
# These are imported but rarely used if orchestrator.py is primary:
from sam_enhanced import sam, load_projects_old, load_memory, find_project, route
```

- `sam()` - Used by `api_query()` only
- `load_projects_old()` - Renamed, potentially unused
- `find_project()` - Used by `api_query()` only
- `route()` - Used by `api_query()` only

---

## Circular Call Patterns

### Pattern 1: Cache Invalidation Loop (Benign)

```
SamIntelligence.learn_from_feedback()
  -> self.cache.invalidate("suggestions")
  -> (next call) get_top_suggestions_fast()
     -> cache.get("suggestions") == None
     -> detector.detect_all()
     -> cache.set("suggestions", result)
```

This is intentional - feedback invalidates cached suggestions.

### Pattern 2: Orchestrator Cross-References (Safe)

```
orchestrate()
  -> handle_improve()
     -> SamIntelligence.get_top_suggestions_fast()
        -> detector.detect_all()
           -> tracker.get_improvements()
              -> (reads same DB as orchestrate logging)
```

No actual circular calls, just shared data access.

### Pattern 3: Lazy Loading Recursion Guard (Safe)

```
get_cognitive_orchestrator()
  -> create_cognitive_orchestrator()
     -> CognitiveOrchestrator.__init__()
        -> (various subsystem inits)
        -> Returns before any callback
  -> Stored in _cognitive_orchestrator singleton
```

Singleton pattern prevents re-entry.

---

## Dependency Summary

### Primary Dependencies by Module

```
sam_api.py
  |
  +-- orchestrator.py
  |     +-- cognitive.mlx_cognitive (MLXCognitiveEngine)
  |     +-- cognitive.smart_vision (SmartVisionRouter)
  |     +-- impact_tracker
  |     +-- privacy_guard
  |     +-- response_styler
  |     +-- thinking_verbs
  |     +-- transparency_guard
  |     +-- thought_logger
  |     +-- conversation_logger
  |     +-- live_thinking
  |     +-- project_dashboard
  |     +-- data_arsenal
  |     +-- terminal_coordination
  |     +-- auto_coordinator
  |
  +-- sam_intelligence.py
  |     +-- evolution_tracker
  |     +-- improvement_detector
  |     +-- evolution_ladders
  |     +-- memory.semantic_memory
  |
  +-- cognitive/ (package)
  |     +-- mlx_cognitive.py (MLXCognitiveEngine, GenerationConfig)
  |     +-- mlx_optimized.py (OptimizedMLXEngine)
  |     +-- vision_engine.py (VisionEngine, VISION_MODELS)
  |     +-- smart_vision.py (SmartVisionRouter)
  |     +-- enhanced_memory.py (WorkingMemory, ProceduralMemory)
  |     +-- enhanced_retrieval.py (HyDERetriever, MultiHopRetriever)
  |     +-- compression.py (PromptCompressor)
  |     +-- cognitive_control.py (CognitiveControl)
  |     +-- enhanced_learning.py (ActiveLearner, PredictiveCache)
  |     +-- emotional_model.py (EmotionalModel, MoodState)
  |     +-- unified_orchestrator.py (CognitiveOrchestrator)
  |     +-- code_indexer.py (CodeIndexer)
  |     +-- doc_indexer.py (DocIndexer)
  |     +-- resource_manager.py (ResourceManager)
  |
  +-- memory/ (package)
  |     +-- fact_memory.py (get_fact_db, build_user_context)
  |     +-- project_context.py (get_project_context)
  |     +-- context_budget.py (ContextBudget)
  |
  +-- voice/ (package)
  |     +-- voice_pipeline.py (SAMVoicePipeline)
  |     +-- voice_output.py (SAMVoice)
  |
  +-- feedback_system.py (FeedbackDB)
  +-- knowledge_distillation.py (DistillationDB)
  +-- execution/ (package)
        +-- escalation_handler.py
        +-- escalation_learner.py
```

### Singleton Instances

| Singleton | Location | Lazy? | Purpose |
|-----------|----------|-------|---------|
| `_sam_intelligence` | sam_api.py:71 | Yes | SAM self-awareness |
| `_distillation_db` | sam_api.py:74 | Yes | Knowledge distillation |
| `_feedback_db` | sam_api.py:77 | Yes | User feedback storage |
| `_compression_monitor` | sam_api.py:395 | Yes | Context compression stats |
| `_vision_stats_monitor` | sam_api.py:650 | Yes | Vision usage stats |
| `_cognitive_orchestrator` | sam_api.py:1334 | Yes | Full cognitive system |
| `_vision_engine` | sam_api.py:2961 | Yes | Vision processing |
| `_smart_vision_router` | sam_api.py:3518 | Yes | Smart vision routing |
| `_voice_pipeline` | sam_api.py:3831 | Yes | Voice processing |
| `_index_watcher` | sam_api.py:2468 | Yes | File watching |
| `MLX_ENGINE` | orchestrator.py:23 | No | MLX inference at module load |
| `IMPACT_TRACKER` | orchestrator.py:33 | No | Impact tracking at module load |
| `PRIVACY_GUARD` | orchestrator.py:40 | No | Privacy scanning at module load |

---

## Recommendations

### 1. Dead Code Removal Candidates

```
- api_speak() and api_voices() - Add routes or remove
- warm_models() - Move to CLI-only module
```

### 2. Hot Path Optimization

```
- _update_activity() - Called twice per request; consider single call
- datetime.now().isoformat() - Cache in request context
- get_*_singleton() - Already lazy-loaded, good pattern
```

### 3. Potential Consolidation

```
- Multiple vision endpoints (api_vision_*) could share more code
- Feedback endpoints could use shared validation
```

### 4. Testing Priority

Based on call frequency, prioritize tests for:
1. `orchestrate()` and all `handle_*()` functions
2. `api_cognitive_process()` and related
3. Vision processing chain
4. Feedback recording chain
