# listen/ - Voice Input

## What This Does
Converts spoken audio into text and detects emotions. Makes SAM hear.

## Why It Exists
SAM needs to understand what you're saying AND how you're feeling.
This enables natural voice conversations with emotional awareness.

## When To Use
- Converting speech to text
- Detecting emotion from voice
- Processing audio streams in real-time

## How To Use
```python
from sam.listen import stt
text = stt.transcribe(audio_file)

from sam.listen import emotion_detect
emotion = emotion_detect.analyze(audio_file)
# Returns: {'emotion': 'happy', 'confidence': 0.85}
```

## Key Files
- `stt.py` - Speech-to-text (Whisper MLX)
- `emotion_detect.py` - Emotion2Vec emotion detection from voice
- `stream.py` - Real-time audio stream processing

## Detected Emotions
- happy, sad, angry, fearful, disgusted, surprised, neutral

## Dependencies
- **Requires:** emotion2vec_mlx/ models
- **Required by:** core/ (for voice input processing)

## What Was Here Before
This extracts STT parts from:
- `voice/voice_pipeline.py` (520 lines) - the input side
- `emotion2vec_mlx/` - kept as dependency
