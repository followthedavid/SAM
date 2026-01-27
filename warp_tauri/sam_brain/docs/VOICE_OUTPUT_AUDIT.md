# Voice Output Capabilities Audit - Phase 6 Preparation

*Created: January 25, 2026*
*Location: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`*

## Executive Summary

SAM's voice output system is a multi-layered architecture designed for emotionally-aware, personalized speech synthesis. The system includes multiple TTS engines, RVC voice cloning integration for the "Dustin Steele" voice, and an emotion-to-prosody mapping system. **Current state: Infrastructure is well-designed but RVC training is incomplete (80% data prep, 0% model training).**

---

## 1. TTS Engines Available

### 1.1 macOS Built-in (`say` command)
**File:** `voice_output.py` - `MacOSVoice` class

| Feature | Value |
|---------|-------|
| Latency | Instant (~0ms overhead) |
| RAM Usage | 0 (system-level) |
| Setup Required | None |
| Voice Options | System voices (Daniel, Fred, Alex, etc.) |
| Output Format | AIFF (converted to WAV for pipeline) |
| Quality | Robotic but reliable |

**Configuration:**
```python
DEFAULT_TTS_VOICE = "Fred"  # Used as RVC base in voice_server.py
rate = 180  # Words per minute (configurable)
```

**Strengths:**
- Zero dependencies
- Always available on macOS
- Reliable fallback

**Limitations:**
- Robotic voice quality
- Limited prosody control
- No streaming support

### 1.2 Coqui TTS
**File:** `voice_output.py` - `CoquiVoice` class

| Feature | Value |
|---------|-------|
| Model | `tts_models/en/ljspeech/tacotron2-DDC` |
| Quality | More natural than macOS |
| Setup | `pip install TTS` |
| Status | Available but not primary |

**Usage:**
```python
voice.set_engine("coqui")
voice.speak("Hello world")
```

### 1.3 F5-TTS (MLX Native)
**File:** `voice_server_v2.py` - `VoiceEngineV2` class

| Feature | Value |
|---------|-------|
| Backend | MLX (Apple Silicon native) |
| Quality | High-quality natural speech |
| Quantization | 4-bit for 8GB RAM |
| Status | Available in `.venv` |
| Max Text Length | 500 characters |

**Pipeline:**
```
Text -> F5-TTS (MLX) -> RVC Voice Conversion -> Output
```

**Detection check:**
```python
def _check_f5(self) -> bool:
    result = subprocess.run(
        [str(SAM_VENV_PYTHON), "-c", "import f5_tts_mlx; print('ok')"],
        capture_output=True, text=True, timeout=10
    )
    return "ok" in result.stdout
```

### 1.4 OpenVoice
**File:** `openvoice/openvoice/api.py`

| Feature | Value |
|---------|-------|
| Type | Voice cloning/conversion |
| Languages | English, Chinese |
| Model | SynthesizerTrn (VITS-based) |
| Status | Code present, integration unclear |

**Capabilities:**
- Base TTS via `BaseSpeakerTTS`
- Tone color conversion via `ToneColorConverter`
- Watermark embedding for attribution
- Speaker embedding extraction

---

## 2. RVC (Retrieval-based Voice Conversion) Integration

### 2.1 Current Architecture

**Files:**
- `voice_bridge.py` - RVC bridge and CLI
- `voice_server.py` - HTTP API server (v1)
- `voice_server_v2.py` - F5-TTS + RVC pipeline (v2)
- `voice_trainer.py` - Training automation
- `train_dustin_voice.py` - Dustin-specific training
- `voice_extraction_pipeline.py` - Audio preparation

**RVC Project Location:**
```
RVC_PROJECT_PATH = Path("/Users/davidquinton/Projects/RVC/rvc-webui")
RVC_PYTHON = Path("/Volumes/Plex/DevSymlinks/venvs/RVC_venv/bin/python")
```

### 2.2 RVC Inference Parameters (voice_server.py)

```python
cmd = [
    str(rvc_python),
    str(RVC_PROJECT_PATH / "tools" / "infer_cli.py"),
    "--input_path", str(input_wav),
    "--opt_path", str(output_wav),
    "--model_name", "dustin_steele_final.pth",
    "--f0up_key", str(pitch_shift),      # Pitch adjustment
    "--f0method", "harvest",              # F0 extraction method
    "--index_rate", "0.5",                # Index blend rate
    "--filter_radius", "3",               # Median filter radius
    "--rms_mix_rate", "0.4",              # RMS mix rate
    "--protect", "0.45"                   # Protect voiceless
]
```

### 2.3 Dustin Steele Voice Model Status

**CRITICAL: Model NOT trained yet**

| Stage | Status | Details |
|-------|--------|---------|
| Video acquisition | DONE | URLs collected, videos downloaded |
| Audio extraction | DONE | 25 clean audio files |
| Chunking | DONE | 161 audio chunks in `datasets/dustin_steele/` |
| Ground truth wavs | DONE | 874 files in `0_gt_wavs` |
| 16k downsampling | DONE | 678 files in `1_16k_wavs` |
| F0 extraction | DONE | 678 files in `2a_f0`, `2b-f0nsf` |
| Feature extraction | DONE | 678 files in `3_feature768` |
| Training config | DONE | `config.json` created |
| **Model Training** | **NOT STARTED** | `train.log` empty, no `.pth` files |

**Expected Model Location:**
```
~/Projects/RVC/rvc-webui/assets/weights/dustin_steele_final.pth
```

**Training Configuration:**
- Sample rate: 40000 Hz
- Batch size: 4
- Epochs: 20000
- Learning rate: 0.0001

### 2.4 Training Data Sources

```python
TRAINING_SOURCES = [
    Path("/Volumes/David External/SAM_Voice_Training/dustin_moaning"),
    Path("/Volumes/David External/SAM_Voice_Training/extracted_dustin_full"),
    Path("/Volumes/David External/SAM_Voice_Training/extracted_dustin"),
]
```

---

## 3. Voice Pipeline Architecture

### 3.1 Complete Pipeline (`voice_pipeline.py`)

**Class:** `SAMVoicePipeline`

```
Audio Input -> Emotion Detection -> Conversation Engine -> Response Generation
                    |                                            |
                    v                                            v
              User Emotion -----> Prosody Mapping -----> TTS Synthesis
                                                              |
                                                              v
                                                     RVC Voice Conversion
                                                              |
                                                              v
                                                        Audio Output
```

**Configuration (`VoicePipelineConfig`):**
```python
sample_rate: int = 16000
chunk_size_ms: int = 100
emotion_backend: str = "prosodic"  # or "whisper_mlx", "emotion2vec"
emotion_update_interval_ms: int = 500
conversation_mode: str = "components"
enable_backchannels: bool = True
backchannel_probability: float = 0.25
response_strategy: str = "complement"  # or "match", "amplify", "neutral"
prosody_intensity: float = 0.8
rvc_enabled: bool = True
rvc_model: str = "dustin_steele"
enable_speculative_generation: bool = True
max_response_tokens: int = 150
```

### 3.2 Emotion-to-Prosody System

**Files:**
- `emotion2vec_mlx/__init__.py` - Main module exports
- `emotion2vec_mlx/prosody_control.py` - Prosody mapping

**Emotion Categories Supported:**
- Negative-Activated: anxious, nervous, frustrated, angry, stressed, panicked, impatient
- Negative-Deactivated: sad, tired, bored, disappointed, lonely, hopeless
- Positive-Activated: excited, happy, playful, flirty, curious, confident, amused
- Positive-Deactivated: calm, content, thoughtful, affectionate
- Neutral: neutral, confused

**Prosody Parameters:**
```python
@dataclass
class ProsodyParameters:
    pitch_shift_semitones: float  # -6 to +6
    pitch_variance: float         # 0.5 to 2.0
    speech_rate: float            # 0.7 to 1.5
    pause_multiplier: float       # 0.5 to 2.0
    volume_db: float              # -6 to +6 dB
    dynamic_range: float          # 0.5 to 1.5
    breathiness: float            # 0.0 to 1.0
    tremolo_amount: float         # 0.0 to 1.0
```

**Response Strategies:**
1. **match** - Mirror user's emotion (intensity * 0.8)
2. **complement** - Respond with complementary emotion (e.g., anxious -> calm)
3. **amplify** - Amplify in same direction (intensity + 0.3)
4. **neutral** - Always respond neutrally

---

## 4. HTTP API Server

### 4.1 Voice Server v1 (`voice_server.py`)

**Port:** 8765 (default)
**Framework:** FastAPI + Uvicorn

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/health` | GET | Health check |
| `/api/voices` | GET | List available voices |
| `/api/speak` | POST | Text to speech |
| `/api/speak/stream` | POST | Streaming (placeholder) |

**Request Model:**
```python
class SpeakRequest(BaseModel):
    text: str
    voice: str = "dustin"  # "dustin" or "default"
    pitch_shift: int = 0   # -12 to 12 semitones
    speed: float = 1.0     # Speech rate multiplier
    format: str = "wav"    # Output format
```

**Features:**
- CORS enabled for iPhone/web access
- HTTPS support with self-signed certs
- Audio caching (100 items max)
- Max text length: 5000 chars

### 4.2 Voice Server v2 (`voice_server_v2.py`)

**Pipeline:** F5-TTS (MLX) -> RVC

**Improvements over v1:**
- MLX-native TTS (better quality)
- 4-bit quantization for 8GB RAM
- Max text length: 500 chars (shorter for quality)

**Availability:**
```python
engine.f5_available  # F5-TTS MLX
engine.rvc_available  # RVC model
```

---

## 5. Streaming Capabilities

### 5.1 Current State

**Status: PLACEHOLDER**

```python
@app.post("/api/speak/stream")
async def speak_stream(request: SpeakRequest):
    """Stream audio (for longer texts) - placeholder for future"""
    return await speak(request)  # Currently just calls regular speak
```

### 5.2 Pipeline Streaming Capability

`voice_pipeline.py` has a generator-based design:

```python
def process_audio(self, audio_chunk: np.ndarray) -> Generator[ConversationEvent, None, None]:
    """Process an audio chunk from microphone. Yields events."""
```

This enables streaming but TTS generation itself is not streamed.

---

## 6. Latency Measurements

**Note:** No formal benchmarks found in codebase. Estimated values:

| Component | Estimated Latency |
|-----------|-------------------|
| macOS `say` | ~100-200ms |
| F5-TTS (MLX, 4-bit) | ~2-5 seconds |
| RVC conversion | ~3-10 seconds |
| Full pipeline (F5 + RVC) | ~5-15 seconds |
| Emotion detection (prosodic) | ~50-100ms |
| Cache hit | ~10ms |

**Caching:**
- MD5 hash key: `text:voice:pitch:speed`
- Max cache: 50-100 items
- Location: `voice_cache/` or `voice_cache_v2/`

---

## 7. Resource Usage

### 7.1 RAM Footprint

| Component | RAM Usage |
|-----------|-----------|
| macOS `say` | 0 (system) |
| F5-TTS (4-bit) | ~2-4 GB |
| RVC inference | ~1-2 GB |
| Full pipeline | ~4-6 GB |
| Docker RVC training | ~2 GB |
| Native MPS training | ~336 MB |

### 7.2 Docker vs Native

**Docker Mode:**
- RAM: ~2GB when running
- Start: `~/ReverseLab/SAM/scripts/rvc_train.sh`
- **Must quit after training to free RAM**

**Native MPS Mode (preferred):**
- RAM: ~336MB
- Start: `~/ReverseLab/SAM/scripts/rvc_native.sh`
- Uses Apple Silicon GPU acceleration

---

## 8. macOS Integration

### 8.1 AVSpeechSynthesizer Fallback

**Implementation:** Via `say` command (not direct AVFoundation)

**Available Voices:**
```bash
say -v ?  # Lists all system voices
```

**Default voices used:**
- `Daniel` - British English (voice_output.py default)
- `Fred` - American English (voice_server.py default for RVC base)

### 8.2 Audio Playback

```python
def play(self, audio_path: Path):
    subprocess.run(["afplay", str(audio_path)], capture_output=True)
```

### 8.3 Audio Format Conversion

Uses `ffmpeg` for format conversion:
```bash
ffmpeg -y -i input.aiff -ar 44100 -ac 1 output.wav
```

---

## 9. Audio Utilities

**File:** `audio_utils.py`

**Backend Priority:**
1. soundfile (fastest, handles many formats)
2. torchaudio (PyTorch ecosystem)
3. wave (standard library, WAV only)

**Key Functions:**
- `load_audio()` - Load to numpy array
- `load_audio_torch()` - Load to PyTorch tensor (for pyannote)
- `load_audio_mlx()` - Load to MLX array
- `compute_energy()` - Frame-wise RMS energy
- `find_high_energy_segments()` - Find loud segments

---

## 10. Current Limitations

### 10.1 Critical Issues

1. **RVC Model Not Trained**
   - All data prep is complete
   - Training has never been run
   - No `.pth` model file exists

2. **No Real Streaming**
   - Stream endpoint is placeholder
   - TTS generates full audio before response

3. **High Latency**
   - F5-TTS + RVC takes 5-15 seconds
   - Not suitable for real-time conversation

### 10.2 Architecture Issues

1. **Conversation Engine Missing**
   - `conversation_engine.py` imported but not found in codebase
   - `voice_pipeline.py` will fail on import

2. **OpenVoice Integration Incomplete**
   - Code present but not wired into main pipeline
   - Could provide alternative to RVC

3. **F5-TTS Reliability Unknown**
   - Availability check exists but success rate unclear
   - Fallback to macOS TTS not tested

### 10.3 Resource Constraints

1. **8GB RAM Limit**
   - F5-TTS + RVC pushes limits
   - Need careful memory management

2. **External Storage Dependency**
   - Training data on `/Volumes/David External/`
   - Must be mounted for training

---

## 11. Recommendations for Phase 6

### 11.1 Immediate Priorities

1. **Complete RVC Training**
   ```bash
   cd ~/Projects/RVC/rvc-webui
   python automate_training_v4.py  # Or use WebUI
   # Expected time: 1-6 hours
   ```

2. **Create Missing Conversation Engine**
   - Implement `conversation_engine.py` or remove imports
   - Essential for `voice_pipeline.py` to function

3. **Implement Real Streaming**
   - Use chunked TTS generation
   - Stream audio as it's generated

### 11.2 Performance Improvements

1. **Precompute Common Phrases**
   - Cache SAM's common responses
   - Pre-render with RVC

2. **Optimize F5-TTS**
   - Test 2-bit quantization (if available)
   - Profile memory usage

3. **Add Latency Metrics**
   - Instrument pipeline with timing
   - Log to file for analysis

### 11.3 Quality Improvements

1. **Prosody Application**
   - `ProsodyApplicator` exists but not wired to RVC
   - Add pitch shift integration

2. **Voice Quality Validation**
   - Add audio quality checks
   - Reject low-quality outputs

3. **Emotion Consistency**
   - Track emotion across conversation
   - Smooth prosody transitions

### 11.4 New Features

1. **Voice Selection API**
   - Allow switching between voices
   - OpenVoice as alternative to RVC

2. **Real-time Mode**
   - macOS TTS for low-latency
   - RVC only for pre-rendered content

3. **Hybrid Pipeline**
   ```
   Quick Response: macOS say (instant)
   Quality Response: F5-TTS + RVC (background, play when ready)
   ```

---

## 12. File Reference

### Core Voice Files
| File | Purpose |
|------|---------|
| `voice_output.py` | CLI and basic TTS engines |
| `voice_pipeline.py` | Complete voice interaction pipeline |
| `voice_bridge.py` | RVC bridge and configuration |
| `voice_server.py` | HTTP API server v1 |
| `voice_server_v2.py` | HTTP API server v2 (F5-TTS) |
| `voice_trainer.py` | Training automation |
| `train_dustin_voice.py` | Dustin-specific training |
| `voice_extraction_pipeline.py` | Audio preparation for training |
| `prepare_voice_training.py` | Video to audio extraction |
| `audio_utils.py` | Audio loading utilities |

### Emotion/Prosody Files
| File | Purpose |
|------|---------|
| `emotion2vec_mlx/__init__.py` | Module exports |
| `emotion2vec_mlx/prosody_control.py` | Emotion to prosody mapping |
| `cognitive/emotional_model.py` | SAM's emotional state |

### External Dependencies
| Path | Purpose |
|------|---------|
| `/Users/davidquinton/Projects/RVC/rvc-webui` | RVC installation |
| `/Volumes/David External/SAM_Voice_Training/` | Training data |
| `/Volumes/Plex/DevSymlinks/venvs/RVC_venv/` | RVC Python environment |

---

## 13. Testing Commands

```bash
# Test macOS TTS
python voice_output.py speak "Hello, I am SAM"

# List available macOS voices
python voice_output.py list-voices

# Test voice bridge
python voice_bridge.py test

# Check RVC status
python voice_bridge.py voices

# Start voice server v1
./start_voice_server.sh 8765

# Start voice server v2
python voice_server_v2.py --port 8765

# Check training status
python train_dustin_voice.py --check
```

---

*This audit provides a foundation for Phase 6 voice enhancements. Priority should be completing RVC training and implementing real streaming capabilities.*
