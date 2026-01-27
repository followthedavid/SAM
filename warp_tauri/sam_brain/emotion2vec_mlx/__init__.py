"""
Voice Emotion Detection & Expression - MLX Native

Bidirectional emotional intelligence for SAM:

INPUT (Detection):
    detector = VoiceEmotionDetector(backend="prosodic")
    result = detector.analyze("user_audio.wav")
    print(f"User feels: {result.primary_emotion}")

OUTPUT (Expression):
    mapper = EmotionToProsody()
    prosody = mapper.from_emotion_result(result, strategy="complement")
    # Apply to SAM's TTS output

Backends:
- prosodic: Fast, no ML, pure acoustic features (works now)
- whisper_mlx: MLX Whisper embeddings + classifier
- emotion2vec: Full Emotion2Vec port (coming soon)
"""

from .detector import VoiceEmotionDetector
from .taxonomy import EmotionCategory, Intensity, EmotionResult, PrimaryDimensions
from .prosody_control import (
    EmotionToProsody, ProsodyParameters, ProsodyApplicator,
    emotion_to_prosody, NEUTRAL_PROSODY
)
from .backends import get_available_backends

__version__ = "0.1.0"
__all__ = [
    # Detection
    "VoiceEmotionDetector",
    "EmotionCategory",
    "Intensity",
    "EmotionResult",
    "PrimaryDimensions",
    "get_available_backends",
    # Expression
    "EmotionToProsody",
    "ProsodyParameters",
    "ProsodyApplicator",
    "emotion_to_prosody",
    "NEUTRAL_PROSODY",
]
