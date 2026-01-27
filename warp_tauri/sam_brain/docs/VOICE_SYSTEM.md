# SAM Voice System Documentation

*Last Updated: January 25, 2026*
*Version: Phase 6.1*

## Overview

SAM's voice system provides text-to-speech capabilities with multiple TTS engines, voice cloning via RVC (Retrieval-based Voice Conversion), and emotion-aware prosody control. The system is designed for SAM's companion personality with the "Dustin Steele" voice as the primary clone target.

```
┌─────────────────────────────────────────────────────────────┐
│                    SAM Voice System                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Text Input                                                  │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Preprocessor │───▶│  TTS Engine  │───▶│  RVC Voice   │  │
│  │ - Markdown   │    │ - macOS say  │    │  Conversion  │  │
│  │ - Abbrevs    │    │ - F5-TTS     │    │ (optional)   │  │
│  │ - Chunking   │    │ - Coqui      │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                    │          │
│                             ▼                    ▼          │
│                      ┌──────────────┐    ┌──────────────┐  │
│                      │   Prosody    │    │    Audio     │  │
│                      │   Control    │───▶│   Output     │  │
│                      │ (emotion)    │    │   Player     │  │
│                      └──────────────┘    └──────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Voice Output | `voice_output.py` | Main TTS interface, CLI |
| Voice Settings | `voice_settings.py` | Persistent configuration |
| Voice Bridge | `voice_bridge.py` | RVC integration |
| Voice Server | `voice_server.py` | HTTP API (v1) |
| Voice Server v2 | `voice_server_v2.py` | F5-TTS + RVC pipeline |
| Voice Pipeline | `voice_pipeline.py` | Full interaction pipeline |

### Supporting Components

| Component | File | Purpose |
|-----------|------|---------|
| Audio Utils | `audio_utils.py` | Audio loading/conversion |
| Emotion2Vec | `emotion2vec_mlx/` | Emotion detection |
| Prosody Control | `prosody_control.py` | Emotion-to-prosody mapping |
| Conversation Engine | `conversation_engine.py` | Turn-taking, backchannels |

## TTS Engines

### 1. macOS Built-in (`say` command)

The default fallback engine. Zero dependencies, instant latency.

**Pros:**
- Always available on macOS
- No RAM overhead (system-level)
- Instant startup
- Multiple built-in voices

**Cons:**
- Robotic voice quality
- Limited prosody control
- No streaming support

**Usage:**
```python
from voice_output import MacOSVoice

voice = MacOSVoice(voice="Daniel", rate=180)
path = voice.speak("Hello, I am SAM")
voice.play(path)
```

**Available Voices:**
```bash
say -v ?  # List all voices
```

Common English voices:
- `Daniel` (British male, default)
- `Alex` (American male)
- `Fred` (American male, good for RVC base)
- `Samantha` (American female)

### 2. F5-TTS (MLX Native)

High-quality neural TTS optimized for Apple Silicon.

**Pros:**
- Natural-sounding speech
- MLX native (fast on Apple Silicon)
- 4-bit quantization for 8GB RAM

**Cons:**
- Slower than macOS (~2-5 seconds)
- Higher RAM usage (~2-4 GB)
- Max 500 character input

**Usage:**
```python
from voice_server_v2 import VoiceEngineV2

engine = VoiceEngineV2()
if engine.f5_available:
    audio = engine.generate_f5("Hello world")
```

### 3. Coqui TTS

Open-source neural TTS with multiple models.

**Pros:**
- Many voice models available
- Good quality
- Voice cloning support

**Cons:**
- Requires separate installation
- Higher latency
- More RAM usage

**Usage:**
```python
from voice_output import CoquiVoice

voice = CoquiVoice(model="tts_models/en/ljspeech/tacotron2-DDC")
path = voice.speak("Hello world")
```

### 4. OpenVoice

Voice cloning and tone transfer (experimental).

**Location:** `openvoice/`

**Capabilities:**
- Zero-shot voice cloning
- Tone color transfer
- Multi-lingual support

## RVC Voice Conversion

RVC (Retrieval-based Voice Conversion) transforms TTS output into SAM's custom voice (Dustin Steele).

### Architecture

```
TTS Audio → RVC Model → Converted Audio
             │
             ├── dustin_steele_final.pth (model)
             └── dustin_steele.index (optional)
```

### Model Location

```
~/Projects/RVC/rvc-webui/assets/weights/dustin_steele_final.pth
```

### RVC Parameters

```python
{
    "f0up_key": 0,           # Pitch shift (-12 to 12 semitones)
    "f0method": "harvest",    # F0 extraction (harvest, pm, crepe)
    "index_rate": 0.5,        # Index blend rate
    "filter_radius": 3,       # Median filter radius
    "rms_mix_rate": 0.4,      # RMS mix rate
    "protect": 0.45           # Protect voiceless consonants
}
```

### Training Status

| Stage | Status |
|-------|--------|
| Video acquisition | DONE |
| Audio extraction | DONE |
| Chunking | DONE |
| Preprocessing | DONE |
| Model Training | NOT STARTED |

Training data: `/Volumes/David External/SAM_Voice_Training/`

## Voice Pipeline

The full voice pipeline (`voice_pipeline.py`) integrates:
1. Audio input processing
2. Emotion detection from user's voice
3. Turn-taking and conversation flow
4. Emotionally-aware response generation
5. Prosody-controlled speech synthesis
6. Voice cloning via RVC

### Configuration

```python
from voice_pipeline import VoicePipelineConfig

config = VoicePipelineConfig(
    sample_rate=16000,
    chunk_size_ms=100,
    emotion_backend="prosodic",
    response_strategy="complement",  # calm if user is anxious
    rvc_enabled=True,
    rvc_model="dustin_steele"
)
```

### Response Strategies

| Strategy | Description |
|----------|-------------|
| `match` | Mirror user's emotion |
| `complement` | Respond with complementary emotion |
| `amplify` | Amplify in same direction |
| `neutral` | Always respond neutrally |

## GUI Integration

### SwiftUI/Tauri Integration

Voice output can be triggered from the GUI:

```swift
// Swift
func speak(text: String) {
    let url = URL(string: "http://localhost:8765/api/speak")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(["text": text])
    URLSession.shared.dataTask(with: request) { data, _, _ in
        // Play audio data
    }.resume()
}
```

```typescript
// Tauri/TypeScript
async function speak(text: string) {
    const response = await fetch('http://localhost:8765/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    });
    const audioBlob = await response.blob();
    const audio = new Audio(URL.createObjectURL(audioBlob));
    audio.play();
}
```

## API Reference

### Voice Settings API

#### GET /api/voice/settings

Get current voice settings.

**Response:**
```json
{
    "success": true,
    "settings": {
        "enabled": true,
        "voice": "default",
        "speed": 1.0,
        "pitch": 0,
        "auto_speak": false,
        "queue_enabled": true,
        "engine": "macos",
        "rvc_enabled": false
    },
    "available_voices": [...],
    "engines": ["macos", "f5", "coqui", "openvoice"]
}
```

#### PUT /api/voice/settings

Update voice settings.

**Request:**
```json
{
    "voice": "daniel",
    "speed": 1.2,
    "rvc_enabled": true
}
```

**Response:**
```json
{
    "success": true,
    "settings": {...}
}
```

### Voice Server API (v1)

#### POST /api/speak

Convert text to speech.

**Request:**
```json
{
    "text": "Hello, I am SAM",
    "voice": "dustin",
    "pitch_shift": 0,
    "speed": 1.0,
    "format": "wav"
}
```

**Response:** Audio file (WAV)

#### GET /api/voices

List available voices.

**Response:**
```json
[
    {
        "id": "dustin",
        "name": "Dustin Steele",
        "description": "SAM's voice via RVC",
        "available": true
    },
    {
        "id": "default",
        "name": "Default (Alex)",
        "description": "macOS default voice",
        "available": true
    }
]
```

#### GET /api/health

Health check.

**Response:**
```json
{
    "status": "ok",
    "rvc_available": true,
    "timestamp": 1706180000.0
}
```

### Voice Pipeline API

#### GET /api/voice/start

Start the voice pipeline.

#### GET /api/voice/stop

Stop the voice pipeline.

#### GET /api/voice/status

Get pipeline status.

**Response:**
```json
{
    "success": true,
    "running": true,
    "emotion_backend": "prosodic",
    "response_strategy": "complement",
    "rvc_enabled": true,
    "stats": {
        "utterances_processed": 42,
        "responses_generated": 38,
        "backchannels_emitted": 15
    }
}
```

#### GET /api/voice/emotion

Get current detected emotion.

**Response:**
```json
{
    "success": true,
    "emotion": {
        "primary": "calm",
        "confidence": 0.85,
        "valence": 0.6,
        "arousal": 0.3
    }
}
```

#### POST /api/voice/config

Update pipeline configuration.

**Request:**
```json
{
    "response_strategy": "match",
    "backchannel_probability": 0.3
}
```

## Settings and Configuration

### Voice Settings File

Location: `~/.sam/voice_settings.json`

```json
{
    "enabled": true,
    "voice": "default",
    "speed": 1.0,
    "pitch": 0,
    "auto_speak": false,
    "queue_enabled": true,
    "volume": 1.0,
    "engine": "macos",
    "rvc_enabled": false,
    "rvc_model": "dustin_steele",
    "max_text_length": 5000,
    "cache_enabled": true,
    "cache_max_items": 100,
    "interruption_enabled": true,
    "emotion_prosody": true
}
```

### Voice Config File

Location: `sam_brain/voice_config.json`

```json
{
    "engine": "macos",
    "voice": "Daniel",
    "rate": 180,
    "save_audio": true,
    "play_audio": true,
    "rvc_model": null
}
```

## Troubleshooting

### Common Issues

#### No Sound Output

1. Check if voice is enabled:
   ```bash
   python voice_settings.py show
   ```

2. Test macOS TTS directly:
   ```bash
   say "Hello"
   ```

3. Check audio output device in System Preferences

#### RVC Not Working

1. Check if model exists:
   ```bash
   ls ~/Projects/RVC/rvc-webui/assets/weights/dustin_steele_final.pth
   ```

2. Check RVC Python environment:
   ```bash
   /Volumes/Plex/DevSymlinks/venvs/RVC_venv/bin/python --version
   ```

3. Test voice bridge:
   ```bash
   python voice_bridge.py test
   ```

#### High Latency

1. Use macOS engine for quick responses:
   ```python
   settings.update(engine="macos")
   ```

2. Enable caching:
   ```python
   settings.update(cache_enabled=True)
   ```

3. Consider precomputing common phrases

#### Out of Memory

1. Switch to macOS TTS (0 RAM overhead)
2. Reduce cache size:
   ```python
   settings.update(cache_max_items=50)
   ```

3. Use F5-TTS 4-bit quantization

### Debug Commands

```bash
# Test TTS
python voice_output.py test

# List voices
python voice_output.py list-voices

# Check voice bridge status
python voice_bridge.py

# Test voice server
curl http://localhost:8765/api/health

# View settings
python voice_settings.py show
```

## Performance Considerations

### Latency Benchmarks

| Component | Typical Latency |
|-----------|-----------------|
| macOS `say` | 100-200ms |
| F5-TTS (MLX, 4-bit) | 2-5 seconds |
| RVC conversion | 3-10 seconds |
| Full pipeline (F5 + RVC) | 5-15 seconds |
| Cache hit | ~10ms |

### RAM Usage

| Component | RAM |
|-----------|-----|
| macOS `say` | 0 (system) |
| F5-TTS (4-bit) | ~2-4 GB |
| RVC inference | ~1-2 GB |
| Full pipeline | ~4-6 GB |

### Optimization Strategies

1. **Caching**: Enable cache for repeated phrases
2. **Hybrid mode**: macOS for quick, RVC for quality
3. **Preprocessing**: Split long text into chunks
4. **Async generation**: Generate audio while user reads text

### 8GB RAM Constraints

For M2 Mac Mini with 8GB RAM:

1. Use macOS TTS as primary (0 RAM)
2. F5-TTS with 4-bit quantization when quality needed
3. Avoid running F5-TTS and RVC simultaneously
4. Clear cache periodically:
   ```bash
   rm -rf sam_brain/voice_cache/*.wav
   ```

## Future Enhancements

### Planned Features

1. **Real-time streaming**: Generate audio as text is produced
2. **Voice selection UI**: GUI for choosing voices
3. **Emotion visualization**: Show detected emotion in UI
4. **Multi-speaker**: Different voices for different contexts
5. **Lip sync**: Generate viseme data for avatar

### Training Dustin Voice

To complete RVC voice training:

```bash
cd ~/Projects/RVC/rvc-webui

# Verify training data
ls datasets/dustin_steele/

# Start training (estimated 1-6 hours)
python train.py --experiment_name dustin_steele --epochs 20000

# Or use WebUI
python app.py
# Navigate to http://localhost:7865
```

## Related Documentation

- [VOICE_OUTPUT_AUDIT.md](VOICE_OUTPUT_AUDIT.md) - Detailed system audit
- [RVC_VOICE_TRAINING.md](/Volumes/Plex/SSOT/projects/RVC_VOICE_TRAINING.md) - Training guide
- [SAM_IDENTITY.md](/Volumes/Plex/SSOT/SAM_IDENTITY.md) - SAM's personality

---

*For questions or issues, check the VOICE_OUTPUT_AUDIT.md for detailed system analysis.*
