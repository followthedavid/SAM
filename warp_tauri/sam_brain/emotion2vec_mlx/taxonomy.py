"""
Emotion Taxonomy - 26 nuanced emotional states

Based on Russell's Circumplex Model with categorical extensions
for detecting subtle states like anxiety, nervousness, frustration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class EmotionCategory(Enum):
    """26 nuanced emotion categories."""

    # Negative-Activated (High Arousal, Negative Valence)
    ANXIOUS = "anxious"
    NERVOUS = "nervous"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    STRESSED = "stressed"
    PANICKED = "panicked"
    IMPATIENT = "impatient"

    # Negative-Deactivated (Low Arousal, Negative Valence)
    SAD = "sad"
    TIRED = "tired"
    BORED = "bored"
    DISAPPOINTED = "disappointed"
    LONELY = "lonely"
    HOPELESS = "hopeless"

    # Positive-Activated (High Arousal, Positive Valence)
    EXCITED = "excited"
    HAPPY = "happy"
    PLAYFUL = "playful"
    FLIRTY = "flirty"
    CURIOUS = "curious"
    CONFIDENT = "confident"
    AMUSED = "amused"

    # Positive-Deactivated (Low Arousal, Positive Valence)
    CALM = "calm"
    CONTENT = "content"
    THOUGHTFUL = "thoughtful"
    AFFECTIONATE = "affectionate"

    # Neutral
    NEUTRAL = "neutral"
    CONFUSED = "confused"


class Intensity(Enum):
    """Emotion intensity levels."""
    SLIGHT = "slight"
    MODERATE = "moderate"
    STRONG = "strong"
    INTENSE = "intense"

    @classmethod
    def from_score(cls, score: float) -> "Intensity":
        """Convert 0-1 score to intensity."""
        if score < 0.3:
            return cls.SLIGHT
        elif score < 0.5:
            return cls.MODERATE
        elif score < 0.75:
            return cls.STRONG
        else:
            return cls.INTENSE


@dataclass
class PrimaryDimensions:
    """Russell's Circumplex primary dimensions."""
    valence: float      # -1 (negative) to +1 (positive)
    arousal: float      # 0 (calm) to 1 (activated)
    dominance: float    # 0 (submissive) to 1 (dominant)

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3)
        }

    def describe(self) -> str:
        """Natural language description."""
        parts = []

        if self.valence > 0.3:
            parts.append("positive")
        elif self.valence < -0.3:
            parts.append("negative")

        if self.arousal > 0.6:
            parts.append("activated/energized")
        elif self.arousal < 0.3:
            parts.append("calm/subdued")

        if self.dominance > 0.6:
            parts.append("assertive")
        elif self.dominance < 0.3:
            parts.append("uncertain")

        return ", ".join(parts) if parts else "neutral"


@dataclass
class EmotionPrediction:
    """Single emotion prediction with confidence."""
    emotion: EmotionCategory
    confidence: float  # 0-1
    intensity: Intensity

    def to_dict(self) -> dict:
        return {
            "emotion": self.emotion.value,
            "confidence": round(self.confidence, 3),
            "intensity": self.intensity.value
        }


@dataclass
class ProsodicMarkers:
    """Voice prosody features extracted from audio."""
    # Pitch features
    pitch_mean_hz: float
    pitch_std_hz: float
    pitch_elevated: bool  # Above speaker's baseline

    # Speech rate
    speech_rate_sps: float  # Syllables per second (estimated)
    speech_rate_category: str  # "slow", "normal", "fast"

    # Other markers
    pause_ratio: float  # Ratio of silence to speech
    voice_tremor: bool  # Pitch instability detected
    breathiness: float  # 0-1, breathy voice quality
    hesitation_count: int  # Number of filled pauses detected
    energy_variance: float  # Dynamic range

    def to_dict(self) -> dict:
        return {
            "pitch_mean_hz": round(self.pitch_mean_hz, 1),
            "pitch_std_hz": round(self.pitch_std_hz, 1),
            "pitch_elevated": self.pitch_elevated,
            "speech_rate_sps": round(self.speech_rate_sps, 2),
            "speech_rate_category": self.speech_rate_category,
            "pause_ratio": round(self.pause_ratio, 3),
            "voice_tremor": self.voice_tremor,
            "breathiness": round(self.breathiness, 3),
            "hesitation_count": self.hesitation_count,
            "energy_variance": round(self.energy_variance, 3)
        }

    def describe(self) -> str:
        """Natural language description of prosodic state."""
        parts = []

        if self.pitch_elevated:
            parts.append("elevated pitch")
        if self.voice_tremor:
            parts.append("voice tremor")
        if self.speech_rate_category == "fast":
            parts.append("speaking quickly")
        elif self.speech_rate_category == "slow":
            parts.append("speaking slowly")
        if self.hesitation_count > 2:
            parts.append(f"{self.hesitation_count} hesitations")
        if self.breathiness > 0.5:
            parts.append("breathy voice")
        if self.pause_ratio > 0.3:
            parts.append("many pauses")

        return ", ".join(parts) if parts else "normal prosody"


@dataclass
class EmotionResult:
    """Complete emotion analysis result."""
    # Primary outputs
    primary: PrimaryDimensions
    categorical: List[EmotionPrediction]  # Top 3 emotions
    prosodic: ProsodicMarkers

    # Metadata
    audio_quality: float  # 0-1, affects confidence
    duration_seconds: float
    timestamp: str
    backend_used: str

    # Optional
    raw_embedding: Optional[List[float]] = None  # For downstream tasks

    @property
    def primary_emotion(self) -> EmotionCategory:
        """Most likely emotion."""
        return self.categorical[0].emotion if self.categorical else EmotionCategory.NEUTRAL

    @property
    def confidence(self) -> float:
        """Confidence of primary emotion."""
        return self.categorical[0].confidence if self.categorical else 0.0

    def to_dict(self) -> dict:
        return {
            "primary_dimensions": self.primary.to_dict(),
            "emotions": [e.to_dict() for e in self.categorical],
            "prosodic_markers": self.prosodic.to_dict(),
            "primary_emotion": self.primary_emotion.value,
            "confidence": round(self.confidence, 3),
            "audio_quality": round(self.audio_quality, 3),
            "duration_seconds": round(self.duration_seconds, 2),
            "timestamp": self.timestamp,
            "backend": self.backend_used
        }

    def to_context_string(self) -> str:
        """
        Generate natural language context for LLM.
        This is what gets injected into SAM's prompt.
        """
        top_emotion = self.categorical[0] if self.categorical else None

        if not top_emotion or top_emotion.confidence < 0.4:
            return "[Voice: neutral/unclear emotional state]"

        parts = [f"[Voice sounds {top_emotion.intensity.value}ly {top_emotion.emotion.value}"]

        # Add prosodic context
        prosodic_desc = self.prosodic.describe()
        if prosodic_desc != "normal prosody":
            parts.append(f"({prosodic_desc})")

        # Add secondary emotion if confident
        if len(self.categorical) > 1 and self.categorical[1].confidence > 0.35:
            parts.append(f", possibly also {self.categorical[1].emotion.value}")

        parts.append("]")

        return " ".join(parts)


# Emotion mappings for dimension → category inference
EMOTION_QUADRANTS = {
    # (valence_sign, arousal_level) → likely emotions
    ("negative", "high"): [
        EmotionCategory.ANXIOUS,
        EmotionCategory.FRUSTRATED,
        EmotionCategory.ANGRY,
        EmotionCategory.STRESSED
    ],
    ("negative", "low"): [
        EmotionCategory.SAD,
        EmotionCategory.TIRED,
        EmotionCategory.DISAPPOINTED,
        EmotionCategory.HOPELESS
    ],
    ("positive", "high"): [
        EmotionCategory.EXCITED,
        EmotionCategory.HAPPY,
        EmotionCategory.PLAYFUL,
        EmotionCategory.CONFIDENT
    ],
    ("positive", "low"): [
        EmotionCategory.CALM,
        EmotionCategory.CONTENT,
        EmotionCategory.THOUGHTFUL,
        EmotionCategory.AFFECTIONATE
    ],
    ("neutral", "any"): [
        EmotionCategory.NEUTRAL,
        EmotionCategory.CONFUSED,
        EmotionCategory.CURIOUS
    ]
}


def dimensions_to_likely_emotions(
    valence: float,
    arousal: float,
    dominance: float
) -> List[EmotionCategory]:
    """
    Map primary dimensions to likely emotion categories.
    Used when we have dimension predictions but need categories.
    """
    # Determine quadrant
    if abs(valence) < 0.2:
        valence_sign = "neutral"
    else:
        valence_sign = "positive" if valence > 0 else "negative"

    if valence_sign == "neutral":
        return EMOTION_QUADRANTS[("neutral", "any")]

    arousal_level = "high" if arousal > 0.5 else "low"

    base_emotions = EMOTION_QUADRANTS.get(
        (valence_sign, arousal_level),
        [EmotionCategory.NEUTRAL]
    )

    # Refine based on dominance
    refined = []
    for emotion in base_emotions:
        # Low dominance + high arousal + negative = anxious/nervous
        if dominance < 0.4 and arousal > 0.6 and valence < 0:
            if emotion in [EmotionCategory.ANXIOUS, EmotionCategory.NERVOUS]:
                refined.insert(0, emotion)
            else:
                refined.append(emotion)
        # High dominance + negative = frustrated/angry
        elif dominance > 0.6 and valence < 0:
            if emotion in [EmotionCategory.FRUSTRATED, EmotionCategory.ANGRY]:
                refined.insert(0, emotion)
            else:
                refined.append(emotion)
        else:
            refined.append(emotion)

    return refined[:4]  # Top 4 likely
