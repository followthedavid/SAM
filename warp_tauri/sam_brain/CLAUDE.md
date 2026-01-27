# SAM Brain - AI Companion Core

## What is SAM?
Self-improving AI companion with personality. Male, cocky, flirty, loyal. Voice: Dustin Steele (RVC).

**Current Version:** v0.5.0 (Full Multi-Modal - MLX Native)

## Architecture (Updated 2026-01-21)

### Core Systems

#### 1. MLX Cognitive Engine (`cognitive/`)
Native Apple Silicon inference with optimizations:

| Component | File | Purpose |
|-----------|------|---------|
| Base Engine | `mlx_cognitive.py` | Model loading, generation, model selection |
| Optimized Engine | `mlx_optimized.py` | KV-cache quantization, prefill chunking |
| Model Selector | `model_selector.py` | Dynamic 1.5B/3B selection based on task |
| Token Budget | `token_budget.py` | Context window management |
| Quality Validator | `quality_validator.py` | Response validation, repetition detection |
| Resource Manager | `resource_manager.py` | Memory monitoring, prevents freezes |

**Optimizations (v0.5.0):**
- **KV-cache 8-bit quantization**: 75% memory savings
- **Prefill chunking**: 512 tokens/step for better memory management
- **Dynamic model selection**: 1.5B for simple, 3B for complex tasks

#### 2. Vision System (`cognitive/vision_engine.py`)
Multi-tier vision processing optimized for 8GB RAM:

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

#### 3. Voice Pipeline (`voice_pipeline.py`)
Real-time voice processing with emotion awareness:

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline | `voice_pipeline.py` | Orchestrates STT→Process→TTS |
| Voice Settings | `voice_settings.py` | Persistent voice configuration |
| Voice Output | `voice_output.py` | TTS engines (macOS, Coqui, RVC) |
| Voice Server | `voice_server.py` | HTTP API for TTS |
| Emotion2Vec | `emotion2vec_mlx/` | MLX-native emotion recognition |
| Audio Utils | `audio_utils.py` | Unified audio loading (soundfile) |
| Prosody | `prosody_control.py` | Emotion-to-speech mapping |

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
GET  /api/voice/settings     - Get voice settings (Phase 6.1)
PUT  /api/voice/settings     - Update voice settings (Phase 6.1)
POST /api/voice/process      - Process audio
POST /api/voice/stream       - Streaming audio
```

**Documentation:** See `docs/VOICE_SYSTEM.md` for full details.

#### 4. Memory Systems

**Semantic Memory** (`semantic_memory.py`):
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
```
sam_api.py                    # HTTP/CLI API (port 8765)
orchestrator.py               # Request routing
semantic_memory.py            # Vector embeddings (MLX)
sam_intelligence.py           # Self-awareness & learning
voice_pipeline.py             # Voice processing pipeline
voice_settings.py             # Voice settings persistence (Phase 6.1)
voice_output.py               # TTS engines interface
voice_server.py               # Voice HTTP API
audio_utils.py                # Audio loading (soundfile backend)
vision_server.py              # Persistent vision server (port 8766)

cognitive/
├── __init__.py               # v1.4.0 - All exports
├── mlx_cognitive.py          # Base MLX engine
├── mlx_optimized.py          # Optimized engine (KV-cache)
├── vision_engine.py          # Multi-tier vision
├── smart_vision.py           # Intelligent tier routing
├── enhanced_memory.py        # Working memory
├── emotional_model.py        # Mood & relationships
├── compression.py            # Prompt compression
├── cognitive_control.py      # Meta-cognition
└── resource_manager.py       # Memory monitoring

emotion2vec_mlx/
├── models/
│   ├── emotion2vec_mlx.py    # MLX model architecture
│   └── convert_to_mlx.py     # PyTorch weight conversion
└── emotion2vec_inference.py  # Inference wrapper
```

## Quick Start
```bash
# Start SAM API (MLX - no Ollama needed)
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python3 sam_api.py server 8765

# Optional: Start vision server (faster repeated inference)
python3 vision_server.py 8766

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

## Related Documentation
- SSOT: `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md`
- Migration: `/Volumes/Plex/SSOT/context/session_20260118_ollama_to_mlx.md`
- Overlaps: `/Volumes/Plex/SSOT/PROJECT_OVERLAPS.md`
- Voice System: `docs/VOICE_SYSTEM.md` (Phase 6.1)
- Voice Audit: `docs/VOICE_OUTPUT_AUDIT.md`
