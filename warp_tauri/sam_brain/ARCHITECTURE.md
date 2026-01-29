# SAM Architecture

**Version:** 0.6.0 (Reorganization Complete)
**Hardware:** M2 Mac Mini, 8GB RAM

## Visual Overview

```
                    ┌─────────────────────────────────────┐
                    │            USER INPUT               │
                    │  (Voice, Text, API, Terminal)       │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │       serve/ (HTTP/CLI/Logging)     │
                    │   approval_queue, notifier,         │
                    │   conversation_logger, thought_     │
                    │   logger, live_thinking             │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │    Root Entry Points (10 files)     │
                    │  sam_api.py (8765) │ orchestrator   │
                    │  sam.py │ sam_repl │ sam_chat       │
                    │  sam_enhanced │ vision_server(8766) │
                    │  unified_daemon │ perpetual_learner │
                    │  auto_learner                       │
                    └─────────────────┬───────────────────┘
                                      │
┌───────────────────┐ ┌───────────────▼───────────────┐ ┌───────────────────┐
│   listen/         │ │        core/ (brain)          │ │     speak/        │
│   Voice Input     │◄┤   smart_router, multi_agent   ├►│   audio_utils     │
│   (scaffold)      │ │   privacy_guard, styler       │ │                   │
└───────────────────┘ └───────────────┬───────────────┘ └───────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   think/      │           │   remember/     │           │      see/       │
│   mlx_        │           │   query_        │           │    apple_ocr    │
│   inference   │           │   decomposer    │           │                 │
│               │           │   relevance_    │           │                 │
│               │           │   scorer        │           │                 │
└───────────────┘           └─────────────────┘           └─────────────────┘
        │                             │
        │                             │
        ▼                             ▼
┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   learn/      │           │   projects/     │           │      do/        │
│   training,   │           │   dashboard,    │           │   sam_agent,    │
│   distill,    │           │   data_arsenal, │           │   terminal_     │
│   evolution,  │           │   comfyui,      │           │   coordination, │
│   feedback    │           │   image_gen,    │           │   auto_coord    │
│   (10 files)  │           │   ssot_sync     │           │                 │
└───────────────┘           └─────────────────┘           └─────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
              ┌───────────────────────────────────────────────┐
              │         Existing Packages (unchanged)         │
              │  cognitive/ (32) │ memory/ (8) │ execution/(9)│
              │  voice/ (10) │ conversation_engine/ (5)       │
              │  emotion2vec_mlx/ (4) │ utils/ (2)            │
              └───────────────────────────────────────────────┘
```

## Package Summary

| Package | Files | Purpose | Key Files |
|---------|-------|---------|-----------|
| core/ | 8 | Routing, identity, safety | smart_router.py, response_styler.py, privacy_guard.py |
| think/ | 1 | LLM inference | mlx_inference.py |
| speak/ | 1 | Voice output utilities | audio_utils.py |
| listen/ | 0 | Voice input (scaffold) | -- |
| see/ | 1 | Vision | apple_ocr.py |
| remember/ | 2 | Memory query processing | query_decomposer.py, relevance_scorer.py |
| do/ | 3 | Execution & coordination | sam_agent.py, terminal_coordination.py, auto_coordinator.py |
| learn/ | 10 | Self-improvement & evolution | training_pipeline.py, evolution_tracker.py, sam_intelligence.py |
| projects/ | 5 | Project awareness & tools | project_dashboard.py, data_arsenal.py, ssot_sync.py |
| serve/ | 5 | External interfaces & logging | approval_queue.py, live_thinking.py, conversation_logger.py |
| cognitive/ | 32 | MLX engine, vision, retrieval | mlx_cognitive.py, vision_engine.py, vision_types.py |
| memory/ | 8 | Semantic memory, embeddings | semantic_memory.py |
| execution/ | 9 | Safe execution, sandboxing | -- |
| voice/ | 10 | Voice pipeline, TTS | voice_pipeline.py, voice_output.py |
| conversation_engine/ | 5 | Conversation management | -- |
| emotion2vec_mlx/ | 4 | MLX emotion recognition | detector.py |
| utils/ | 2 | Shared utilities | -- |
| tests/ | 21 | Test suite | -- |

## Data Flow Example

**User says:** "What was that bug we fixed yesterday?"

```
1. sam_api.py             -> Receives HTTP request (port 8765)
2. orchestrator.py        -> Routes to memory + think
3. remember/query_decomposer.py -> Decomposes query
4. memory/semantic_memory.py    -> Semantic search for "bug fix yesterday"
5. remember/relevance_scorer.py -> Scores and ranks results
6. think/mlx_inference.py       -> Generate response with context
7. core/response_styler.py      -> Apply SAM personality/style
8. speak/audio_utils.py         -> (if voice) Prepare audio
9. sam_api.py             -> Return response
```

## Import Convention

After reorganization, all imports use package paths:
```python
from learn.evolution_tracker import EvolutionTracker
from core.response_styler import ResponseStyler
from do.sam_agent import SAMAgent
from remember.query_decomposer import QueryDecomposer
from projects.data_arsenal import DataArsenal
from serve.live_thinking import LiveThinking
```

## Model Selection

| Task Type | Model | RAM | When |
|-----------|-------|-----|------|
| Simple chat | Qwen2.5-1.5B | ~2GB | Greetings, simple Q&A |
| Complex reasoning | Qwen2.5-3B | ~4GB | Code, analysis |
| Very complex | Claude (escalate) | 0 | Multi-step reasoning |

## Security Fixes (v0.6.0)

| Fix | File | Description |
|-----|------|-------------|
| Shell injection | do/sam_agent.py | Sanitized shell command construction |
| Path traversal | sam_api.py | Validated file path inputs |
| VisionTier consolidation | cognitive/vision_types.py | Single source of truth for vision tier enum |

## Storage Layout

```
Internal SSD (limited):
└── ~/ReverseLab/SAM/warp_tauri/sam_brain/  # Code only

External Storage:
├── /Volumes/David External/SAM_models/      # Model weights
├── /Volumes/David External/sam_memory/      # Memory databases
├── /Volumes/David External/SAM_Voice_Training/  # Voice data
├── /Volumes/#1/SAM/dead_code_archive/       # 33 archived dead files
└── /Volumes/Plex/DevSymlinks/               # Caches, venvs
```

## Background Services

| Service | Purpose | Status |
|---------|---------|--------|
| com.sam.api | HTTP API (8765) | Enabled |
| com.sam.perpetual | Learning daemon | Enabled |
| com.sam.autolearner | Claude watcher | Enabled |

## Migration Status

```
Phase 1:  [DONE] Structure created (directories + READMEs)
Phase 2:  [DONE] Core migration (8 files -> core/)
Phase 3:  [DONE] Think migration (1 file -> think/)
Phase 4:  [DONE] Voice migration (1 file -> speak/)
Phase 5:  [DONE] Vision migration (1 file -> see/)
Phase 6:  [DONE] Memory migration (2 files -> remember/)
Phase 7:  [DONE] Execution migration (3 files -> do/)
Phase 8:  [DONE] Learning migration (10 files -> learn/)
Phase 9:  [DONE] Projects migration (5 files -> projects/)
Phase 10: [DONE] Serve migration (5 files -> serve/)
Phase 11: [DONE] Cleanup (33 dead files archived)
Phase 12: [DONE] Documentation (this update)
```
