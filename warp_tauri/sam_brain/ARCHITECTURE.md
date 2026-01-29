# SAM Architecture

**Version:** 0.6.0 (Reorganization in Progress)
**Hardware:** M2 Mac Mini, 8GB RAM

## Visual Overview

```
                    ┌─────────────────────────────────────┐
                    │            USER INPUT               │
                    │  (Voice, Text, API, Terminal)       │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │         serve/ (HTTP/CLI)           │
                    │   Port 8765 • REST API • Daemons    │
                    └─────────────────┬───────────────────┘
                                      │
┌───────────────────┐ ┌───────────────▼───────────────┐ ┌───────────────────┐
│   listen/         │ │        core/ (brain)          │ │     speak/        │
│   Voice Input     │◄┤   Routes to right handler     ├►│   Voice Output    │
│   STT, Emotion    │ │   Identity, Config, Emotion   │ │   TTS, RVC        │
└───────────────────┘ └───────────────┬───────────────┘ └───────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   think/      │           │   remember/     │           │      see/       │
│   MLX LLM     │           │   Memory        │           │    Vision       │
│   1.5B / 3B   │           │   Embeddings    │           │    OCR, VLM     │
│   Escalate    │           │   Facts         │           │    UI State     │
└───────────────┘           └─────────────────┘           └─────────────────┘
        │                             │
        │                             │
        ▼                             ▼
┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   learn/      │           │   projects/     │           │      do/        │
│   Fine-tune   │           │   Code Search   │           │   Execution     │
│   Distill     │           │   Registry      │           │   Safe Run      │
│   Curriculum  │           │   Permissions   │           │   Approval      │
└───────────────┘           └─────────────────┘           └─────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │            utils/                   │
                    │   Audio, Image, Paths, Resources    │
                    └─────────────────────────────────────┘
```

## Package Summary

| Package | Purpose | Key File | Entry Point |
|---------|---------|----------|-------------|
| core/ | Routing & identity | brain.py | `brain.process()` |
| think/ | LLM inference | mlx.py | `mlx.generate()` |
| speak/ | Voice output | tts.py | `tts.say()` |
| listen/ | Voice input | stt.py | `stt.transcribe()` |
| see/ | Vision | describe.py | `describe.image()` |
| remember/ | Memory | embeddings.py | `embeddings.search()` |
| do/ | Execution | run.py | `run.execute()` |
| learn/ | Self-improvement | train.py | `train.run()` |
| projects/ | Project awareness | registry.py | `registry.get()` |
| serve/ | External interfaces | http.py | `python -m serve.http` |
| utils/ | Helpers | resources.py | Various |

## Data Flow Example

**User says:** "What was that bug we fixed yesterday?"

```
1. serve/http.py     → Receives HTTP request
2. core/brain.py     → Routes to memory + think
3. remember/embeddings.py → Semantic search for "bug fix yesterday"
4. remember/conversations.py → Get conversation context
5. think/mlx.py      → Generate response with context
6. core/brain.py     → Apply personality/style
7. speak/tts.py      → (if voice) Convert to speech
8. serve/http.py     → Return response
```

## Model Selection

| Task Type | Model | RAM | When |
|-----------|-------|-----|------|
| Simple chat | Qwen2.5-1.5B | ~2GB | Greetings, simple Q&A |
| Complex reasoning | Qwen2.5-3B | ~4GB | Code, analysis |
| Very complex | Claude (escalate) | 0 | Multi-step reasoning |

## Storage Layout

```
Internal SSD (limited):
└── ~/ReverseLab/SAM/warp_tauri/sam_brain/  # Code only

External Storage:
├── /Volumes/David External/SAM_models/      # Model weights
├── /Volumes/David External/sam_memory/      # Memory databases
├── /Volumes/David External/SAM_Voice_Training/  # Voice data
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
Phase 1: ✅ Structure created (directories + READMEs)
Phase 2: ⏳ Core migration (pending)
Phase 3: ⏳ Think migration (pending)
Phase 4: ⏳ Voice migration (pending)
Phase 5: ⏳ Vision migration (pending)
Phase 6: ⏳ Memory migration (pending)
Phase 7: ⏳ Execution migration (pending)
Phase 8: ⏳ Learning migration (pending)
Phase 9: ⏳ Projects migration (pending)
Phase 10: ⏳ Serve migration (pending)
Phase 11: ⏳ Cleanup (pending)
Phase 12: ⏳ Documentation (pending)
```
