# speak/ - Voice Output

## What This Does
Converts SAM's text responses into spoken audio. Makes SAM talk.

## Why It Exists
SAM has a specific voice personality (Dustin Steele via RVC).
This package handles the full TTS pipeline from text to SAM's voice.

## When To Use
- Converting any text to speech
- Training or using voice clones
- Adjusting speech emotion/prosody
- Caching frequently-spoken phrases

## How To Use
```python
from sam.speak import tts
audio = tts.say("Hello! How can I help?")

from sam.speak import rvc
audio = rvc.clone_voice(audio, target="dustin_steele")
```

## Key Files
- `tts.py` - Text-to-speech engines (macOS say, F5-TTS)
- `rvc.py` - Voice cloning via RVC (Dustin Steele voice)
- `emotion.py` - Emotion-to-prosody mapping (happy = higher pitch, faster)
- `cache.py` - Cache repeated phrases for instant playback
- `settings.py` - Voice configuration (speed, pitch, model)

## Quality Levels
| Level | Engine | Latency | Quality |
|-------|--------|---------|---------|
| FAST | macOS say | ~100ms | Robotic |
| BALANCED | F5-TTS | 2-5s | Natural |
| QUALITY | F5-TTS + RVC | 5-15s | SAM's voice |

## Dependencies
- **Requires:** RVC model files (external storage)
- **Required by:** core/ (for voice responses)

## What Was Here Before
This consolidates:
- `voice/voice_output.py` (323 lines)
- `voice/voice_bridge.py` (285 lines)
- `voice/voice_settings.py` (561 lines)
- `voice/voice_cache.py` (623 lines)
- `tts_pipeline.py` (422 lines) - deleted duplicate
