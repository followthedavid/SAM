# SAM Brain - AI Companion Core

## What is SAM?
Self-improving AI companion with personality. Male, cocky, flirty, loyal. Voice: Dustin Steele (RVC).

**Current Version:** v0.6.0 (Reorganized Codebase - MLX Native)

## Architecture (Updated 2026-01-29)

### Core Systems

#### 1. MLX Cognitive Engine (`cognitive/`)
Native Apple Silicon inference with optimizations (32 files):

| Component | File | Purpose |
|-----------|------|---------|
| Base Engine | `cognitive/mlx_cognitive.py` | Model loading, generation, model selection |
| Optimized Engine | `cognitive/mlx_optimized.py` | KV-cache quantization, prefill chunking |
| Model Selector | `cognitive/model_selector.py` | Dynamic 1.5B/3B selection based on task |
| Token Budget | `cognitive/token_budget.py` | Context window management |
| Quality Validator | `cognitive/quality_validator.py` | Response validation, repetition detection |
| Resource Manager | `cognitive/resource_manager.py` | Memory monitoring, prevents freezes |

**Optimizations (v0.5.0+):**
- **KV-cache 8-bit quantization**: 75% memory savings
- **Prefill chunking**: 512 tokens/step for better memory management
- **Dynamic model selection**: 1.5B for simple, 3B for complex tasks

#### 2. Vision System (`cognitive/vision_engine.py`)
Multi-tier vision processing optimized for 8GB RAM. VisionTier enum consolidated in `cognitive/vision_types.py`.

| Tier | Method | Speed | RAM | Use Case |
|------|--------|-------|-----|----------|
| ZERO_COST | Apple Vision OCR | 22ms | 0 | Text extraction |
| LIGHTWEIGHT | CoreML | ~100ms | 200MB | Face detection |
| LOCAL_VLM | nanoLLaVA | 10-60s | 4GB | General vision |
| CLAUDE | Terminal escalation | varies | 0 | Complex reasoning |

**API Endpoints:**
```
GET  /api/vision/models      - Available models
GET  /api/vision/stats       - Engine statistics
POST /api/vision/process     - Process image (path or base64)
POST /api/vision/describe    - Describe image
POST /api/vision/detect      - Object detection
POST /api/vision/ocr         - Text extraction (Apple Vision)
POST /api/vision/smart       - Auto-routing to best tier
```

#### 3. Voice Pipeline (`voice/`)
Real-time voice processing with emotion awareness (10 files):

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline | `voice/voice_pipeline.py` | Orchestrates STT->Process->TTS |
| Voice Settings | `voice/voice_settings.py` | Persistent voice configuration |
| Voice Output | `voice/voice_output.py` | TTS engines (macOS, Coqui, RVC) |
| Voice Server | `voice/voice_server.py` | HTTP API for TTS |
| Emotion2Vec | `emotion2vec_mlx/` | MLX-native emotion recognition |
| Audio Utils | `speak/audio_utils.py` | Unified audio loading (soundfile) |
| Prosody | `voice/prosody_control.py` | Emotion-to-speech mapping |

**Quality Levels:**
- `FAST`: macOS say (instant, ~100ms)
- `BALANCED`: F5-TTS (natural, 2-5s)
- `QUALITY`: F5-TTS + RVC (best quality, 5-15s)

**API Endpoints:**
```
GET  /api/voice/start        - Start voice pipeline
GET  /api/voice/stop         - Stop pipeline
GET  /api/voice/status       - Pipeline status
GET  /api/voice/emotion      - Current emotion state
GET  /api/voice/config       - Configuration
GET  /api/voice/settings     - Get voice settings
PUT  /api/voice/settings     - Update voice settings
POST /api/voice/process      - Process audio
POST /api/voice/stream       - Streaming audio
```

**Documentation:** See `docs/VOICE_SYSTEM.md` for full details.

#### 4. Memory Systems

**Semantic Memory** (`memory/`):
- MLX MiniLM-L6-v2 embeddings (384-dim, 10ms)
- Cosine similarity search
- Stores: interactions, code, solutions, notes

**Working Memory** (`cognitive/enhanced_memory.py`):
- Short-term context with decay
- Procedural memory for learned patterns

**Emotional Model** (`cognitive/emotional_model.py`):
- Mood state machine (neutral, happy, frustrated, etc.)
- Relationship tracking per user

### Orchestrator (`orchestrator.py`)
Routes requests to specialized handlers:

| Route | Handler | Description |
|-------|---------|-------------|
| CHAT | MLX Qwen2.5 | Casual conversation |
| ROLEPLAY | MLX Qwen2.5 | Persona interactions |
| CODE | MLX Qwen2.5 | Programming help |
| REASON | MLX + Claude | Complex problems (terminal escalation) |
| IMAGE | ComfyUI API | Image generation |
| VISION | Vision Engine | Image understanding |
| VOICE | Voice Pipeline | Voice interaction |
| IMPROVE | SAM Intelligence | Self-evolution queries |
| PROJECT | Narrative gen | Project status |
| DATA | Data Arsenal | Scraping, intelligence |
| TERMINAL | Coordination | Multi-terminal awareness |

## Key Files

### Root Entry Points (10 files)
```
sam_api.py                    # HTTP/CLI API (port 8765) - route dispatch only (697 lines)
shared_state.py               # Singletons, monitors, constants (793 lines)
sam.py                        # Main SAM entry point
sam_repl.py                   # Interactive REPL
sam_chat.py                   # Chat interface
sam_enhanced.py               # Enhanced chat with all features
orchestrator.py               # Request routing
vision_server.py              # Persistent vision server (port 8766)
unified_daemon.py             # Unified background daemon
perpetual_learner.py          # Continuous learning daemon
auto_learner.py               # Learns from Claude Code sessions
```

### New Packages (after reorganization)
```
core/ (8 files)               # Identity, routing, safety
├── privacy_guard.py          # Privacy protection
├── transparency_guard.py     # Transparency enforcement
├── response_styler.py        # SAM personality styling
├── thinking_verbs.py         # Thinking verb generation
├── narrative_ui_spec.py      # Narrative UI specification
├── re_orchestrator.py        # Re-orchestration logic
├── smart_router.py           # Intelligent request routing
└── multi_agent.py            # Multi-agent coordination

think/ (1 file)               # LLM inference
└── mlx_inference.py          # MLX model inference

speak/ (1 file)               # Voice output utilities
└── audio_utils.py            # Unified audio loading (soundfile)

listen/                       # Voice input (empty scaffold)

see/ (1 file)                 # Vision
└── apple_ocr.py              # Apple Vision OCR

remember/ (2 files)           # Memory query processing
├── query_decomposer.py       # Breaks complex queries into sub-queries
└── relevance_scorer.py       # Scores memory relevance

do/ (3 files)                 # Execution & coordination
├── sam_agent.py              # Agent execution (shell injection fixed)
├── terminal_coordination.py  # Multi-terminal awareness
└── auto_coordinator.py       # Autonomous task coordination

learn/ (10 files)             # Self-improvement & evolution
├── training_pipeline.py      # Fine-tuning pipeline
├── knowledge_distillation.py # Knowledge distillation
├── model_deployment.py       # Model deployment
├── feedback_system.py        # Feedback collection
├── impact_tracker.py         # Impact measurement
├── intelligence_core.py      # Intelligence metrics
├── evolution_tracker.py      # Evolution tracking
├── evolution_ladders.py      # Skill progression ladders
├── improvement_detector.py   # Detects improvement opportunities
└── sam_intelligence.py       # Self-awareness & learning

projects/ (5 files)           # Project awareness
├── project_dashboard.py      # Project status dashboard
├── data_arsenal.py           # Data collection/scraping
├── comfyui_client.py         # ComfyUI API client
├── image_generator.py        # Image generation
└── ssot_sync.py              # SSOT synchronization

serve/ (5 files)              # External interfaces & logging
├── approval_queue.py         # Execution approval queue
├── proactive_notifier.py     # Proactive notifications
├── conversation_logger.py    # Conversation logging
├── thought_logger.py         # Thought process logging
└── live_thinking.py          # Live thinking display
```

### Route Modules (NEW - split from sam_api.py)
```
routes/ (11 files)            # HTTP API route handlers
├── __init__.py               # Route aggregation
├── core.py                   # Health, status, config (299 lines)
├── intelligence.py           # Learning, evolution (377 lines)
├── cognitive.py              # MLX engine, memory (482 lines)
├── facts.py                  # Fact CRUD + prefix routes (296 lines)
├── project.py                # Project dashboard (277 lines)
├── index.py                  # Code indexing (335 lines)
├── vision.py                 # Vision processing (633 lines)
├── image_context.py          # Image context (163 lines)
├── voice.py                  # Voice pipeline (329 lines)
└── distillation.py           # Knowledge distillation (178 lines)
```

### Existing Packages
```
cognitive/ (32 files)         # MLX engine, vision, memory, retrieval
memory/ (8 files)             # Semantic memory, embeddings
execution/ (8 files)          # Safe execution, sandboxing (command_proposer archived)
voice/ (10 files)             # Voice pipeline, TTS, settings
conversation_engine/ (5 files) # Conversation management
emotion2vec_mlx/ (4 files)    # MLX emotion recognition
utils/ (2 files)              # Shared utilities
tests/ (21 files)             # Test suite
```

## Import Convention
After reorganization, imports use package paths:
```python
from learn.evolution_tracker import EvolutionTracker
from core.response_styler import ResponseStyler
from do.sam_agent import SAMAgent
from remember.query_decomposer import QueryDecomposer
from projects.data_arsenal import DataArsenal
from serve.live_thinking import LiveThinking
```

## Quick Start
```bash
# Start SAM API (MLX - no Ollama needed)
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python3 sam_api.py server 8765

# Optional: Start vision server (faster repeated inference)
python3 vision_server.py 8766

# Interactive REPL
python3 sam_repl.py

# Voice training (Docker auto-managed)
rvc  # or tell SAM "train a voice"
```

## Resource Management
- **Ollama**: DECOMMISSIONED (2026-01-18)
- **Docker**: ON-DEMAND only (for RVC training)
- **MLX**: Native inference, always available
- **Memory Target**: <6GB total RAM usage

## Hardware Constraints
- **M2 Mac Mini, 8GB RAM**
- All models optimized for this constraint
- KV-cache quantization saves ~75% memory
- Apple Vision for zero-cost OCR

## External Storage
- **Models**: `/Volumes/David External/SAM_models/`
- **Training Data**: `/Volumes/David External/SAM_Voice_Training/`
- **Memory DB**: `/Volumes/David External/sam_memory/`
- **Caches/venvs**: `/Volumes/Plex/DevSymlinks/`
- **Dead Code Archive**: `/Volumes/#1/SAM/dead_code_archive/` (94 archived files)

## Related Documentation
- SSOT: `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md`
- Migration: `/Volumes/Plex/SSOT/context/session_20260118_ollama_to_mlx.md`
- Overlaps: `/Volumes/Plex/SSOT/PROJECT_OVERLAPS.md`
- Voice System: `docs/VOICE_SYSTEM.md`
- Voice Audit: `docs/VOICE_OUTPUT_AUDIT.md`
- Specs: `docs/` contains 27 detailed specification files covering memory, voice, training, vision, distillation, RAG, and execution systems
