"""
Prosody Control - Emotional expression for TTS output

Maps emotional state to prosodic parameters that can be applied
to SAM's voice synthesis (RVC or other TTS).

This enables SAM to EXPRESS emotions, not just detect them.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np

from .taxonomy import EmotionCategory, EmotionResult, PrimaryDimensions


@dataclass
class ProsodyParameters:
    """
    Parameters for controlling speech prosody.

    These can be applied to:
    - Pre-RVC text (SSML-like markup)
    - Post-RVC audio (pitch/time stretching)
    - Direct TTS engines that support prosody control
    """
    # Pitch modification
    pitch_shift_semitones: float  # -6 to +6 (negative = lower, positive = higher)
    pitch_variance: float  # 0.5 to 2.0 (1.0 = normal, higher = more expressive)

    # Timing modification
    speech_rate: float  # 0.7 to 1.5 (1.0 = normal)
    pause_multiplier: float  # 0.5 to 2.0 (affects pause duration)

    # Energy/dynamics
    volume_db: float  # -6 to +6 dB adjustment
    dynamic_range: float  # 0.5 to 1.5 (compression/expansion)

    # Advanced
    breathiness: float  # 0.0 to 1.0 (add breathy quality)
    tremolo_amount: float  # 0.0 to 1.0 (subtle pitch wobble for emotion)

    def to_dict(self) -> Dict[str, float]:
        return {
            "pitch_shift_semitones": round(self.pitch_shift_semitones, 2),
            "pitch_variance": round(self.pitch_variance, 2),
            "speech_rate": round(self.speech_rate, 2),
            "pause_multiplier": round(self.pause_multiplier, 2),
            "volume_db": round(self.volume_db, 2),
            "dynamic_range": round(self.dynamic_range, 2),
            "breathiness": round(self.breathiness, 2),
            "tremolo_amount": round(self.tremolo_amount, 2)
        }

    def describe(self) -> str:
        """Human-readable description."""
        parts = []
        if self.pitch_shift_semitones > 0.5:
            parts.append("higher pitch")
        elif self.pitch_shift_semitones < -0.5:
            parts.append("lower pitch")
        if self.speech_rate > 1.1:
            parts.append("faster")
        elif self.speech_rate < 0.9:
            parts.append("slower")
        if self.breathiness > 0.3:
            parts.append("breathy")
        if self.tremolo_amount > 0.2:
            parts.append("emotional tremor")
        return ", ".join(parts) if parts else "neutral delivery"


# Default/neutral prosody
NEUTRAL_PROSODY = ProsodyParameters(
    pitch_shift_semitones=0.0,
    pitch_variance=1.0,
    speech_rate=1.0,
    pause_multiplier=1.0,
    volume_db=0.0,
    dynamic_range=1.0,
    breathiness=0.0,
    tremolo_amount=0.0
)


class EmotionToProsody:
    """
    Maps emotional states to prosodic parameters.

    Based on research on acoustic correlates of emotion:
    - Scherer (2003): "Vocal communication of emotion"
    - Juslin & Laukka (2003): "Communication of emotions in vocal expression"
    """

    # Prosody profiles for each emotion category
    EMOTION_PROFILES: Dict[EmotionCategory, ProsodyParameters] = {
        # === Negative-Activated ===
        EmotionCategory.ANXIOUS: ProsodyParameters(
            pitch_shift_semitones=1.5,  # Slightly higher
            pitch_variance=1.4,  # More variable (unsteady)
            speech_rate=1.15,  # Faster
            pause_multiplier=0.7,  # Shorter pauses (rushed)
            volume_db=1.0,
            dynamic_range=1.2,
            breathiness=0.2,
            tremolo_amount=0.3  # Slight tremor
        ),
        EmotionCategory.NERVOUS: ProsodyParameters(
            pitch_shift_semitones=1.0,
            pitch_variance=1.3,
            speech_rate=1.1,
            pause_multiplier=0.8,
            volume_db=0.0,
            dynamic_range=1.1,
            breathiness=0.15,
            tremolo_amount=0.25
        ),
        EmotionCategory.FRUSTRATED: ProsodyParameters(
            pitch_shift_semitones=0.5,
            pitch_variance=1.5,  # Highly variable (exasperated)
            speech_rate=1.1,
            pause_multiplier=0.6,  # Clipped pauses
            volume_db=2.0,  # Louder
            dynamic_range=1.3,
            breathiness=0.0,
            tremolo_amount=0.1
        ),
        EmotionCategory.ANGRY: ProsodyParameters(
            pitch_shift_semitones=-0.5,  # Lower, more threatening
            pitch_variance=1.6,
            speech_rate=1.05,
            pause_multiplier=0.5,  # Clipped
            volume_db=3.0,  # Louder
            dynamic_range=1.4,
            breathiness=0.0,
            tremolo_amount=0.0
        ),
        EmotionCategory.STRESSED: ProsodyParameters(
            pitch_shift_semitones=1.0,
            pitch_variance=1.3,
            speech_rate=1.2,  # Faster
            pause_multiplier=0.6,
            volume_db=1.5,
            dynamic_range=1.2,
            breathiness=0.1,
            tremolo_amount=0.2
        ),
        EmotionCategory.PANICKED: ProsodyParameters(
            pitch_shift_semitones=2.5,  # Much higher
            pitch_variance=1.8,
            speech_rate=1.35,  # Very fast
            pause_multiplier=0.4,
            volume_db=4.0,
            dynamic_range=1.5,
            breathiness=0.3,
            tremolo_amount=0.5
        ),
        EmotionCategory.IMPATIENT: ProsodyParameters(
            pitch_shift_semitones=0.5,
            pitch_variance=1.2,
            speech_rate=1.25,
            pause_multiplier=0.5,
            volume_db=1.0,
            dynamic_range=1.1,
            breathiness=0.0,
            tremolo_amount=0.0
        ),

        # === Negative-Deactivated ===
        EmotionCategory.SAD: ProsodyParameters(
            pitch_shift_semitones=-1.5,  # Lower
            pitch_variance=0.6,  # Monotone
            speech_rate=0.8,  # Slower
            pause_multiplier=1.5,  # Longer pauses
            volume_db=-2.0,  # Quieter
            dynamic_range=0.7,  # Less dynamic
            breathiness=0.3,  # Breathy
            tremolo_amount=0.15
        ),
        EmotionCategory.TIRED: ProsodyParameters(
            pitch_shift_semitones=-1.0,
            pitch_variance=0.5,
            speech_rate=0.75,
            pause_multiplier=1.8,
            volume_db=-3.0,
            dynamic_range=0.6,
            breathiness=0.4,
            tremolo_amount=0.0
        ),
        EmotionCategory.BORED: ProsodyParameters(
            pitch_shift_semitones=-0.5,
            pitch_variance=0.4,  # Very monotone
            speech_rate=0.85,
            pause_multiplier=1.3,
            volume_db=-1.0,
            dynamic_range=0.5,
            breathiness=0.1,
            tremolo_amount=0.0
        ),
        EmotionCategory.DISAPPOINTED: ProsodyParameters(
            pitch_shift_semitones=-1.0,
            pitch_variance=0.7,
            speech_rate=0.85,
            pause_multiplier=1.4,
            volume_db=-1.5,
            dynamic_range=0.8,
            breathiness=0.2,
            tremolo_amount=0.1
        ),
        EmotionCategory.LONELY: ProsodyParameters(
            pitch_shift_semitones=-1.0,
            pitch_variance=0.6,
            speech_rate=0.8,
            pause_multiplier=1.6,
            volume_db=-2.0,
            dynamic_range=0.7,
            breathiness=0.35,
            tremolo_amount=0.2
        ),
        EmotionCategory.HOPELESS: ProsodyParameters(
            pitch_shift_semitones=-2.0,
            pitch_variance=0.4,
            speech_rate=0.7,
            pause_multiplier=2.0,
            volume_db=-3.0,
            dynamic_range=0.5,
            breathiness=0.4,
            tremolo_amount=0.25
        ),

        # === Positive-Activated ===
        EmotionCategory.EXCITED: ProsodyParameters(
            pitch_shift_semitones=2.0,  # Higher
            pitch_variance=1.6,  # Very expressive
            speech_rate=1.25,  # Faster
            pause_multiplier=0.6,
            volume_db=2.0,
            dynamic_range=1.4,
            breathiness=0.1,
            tremolo_amount=0.1
        ),
        EmotionCategory.HAPPY: ProsodyParameters(
            pitch_shift_semitones=1.5,
            pitch_variance=1.4,
            speech_rate=1.1,
            pause_multiplier=0.8,
            volume_db=1.5,
            dynamic_range=1.3,
            breathiness=0.0,
            tremolo_amount=0.0
        ),
        EmotionCategory.PLAYFUL: ProsodyParameters(
            pitch_shift_semitones=1.0,
            pitch_variance=1.5,  # Bouncy
            speech_rate=1.15,
            pause_multiplier=0.7,
            volume_db=1.0,
            dynamic_range=1.3,
            breathiness=0.1,
            tremolo_amount=0.05
        ),
        EmotionCategory.FLIRTY: ProsodyParameters(
            pitch_shift_semitones=0.5,
            pitch_variance=1.3,
            speech_rate=0.95,  # Slightly slower, deliberate
            pause_multiplier=1.1,
            volume_db=0.0,
            dynamic_range=1.2,
            breathiness=0.25,  # Breathy is flirty
            tremolo_amount=0.1
        ),
        EmotionCategory.CURIOUS: ProsodyParameters(
            pitch_shift_semitones=1.0,
            pitch_variance=1.3,
            speech_rate=1.0,
            pause_multiplier=1.0,
            volume_db=0.5,
            dynamic_range=1.1,
            breathiness=0.0,
            tremolo_amount=0.0
        ),
        EmotionCategory.CONFIDENT: ProsodyParameters(
            pitch_shift_semitones=-0.5,  # Slightly lower = authoritative
            pitch_variance=1.2,
            speech_rate=0.95,  # Deliberate
            pause_multiplier=1.1,
            volume_db=1.5,
            dynamic_range=1.2,
            breathiness=0.0,
            tremolo_amount=0.0
        ),
        EmotionCategory.AMUSED: ProsodyParameters(
            pitch_shift_semitones=1.0,
            pitch_variance=1.4,
            speech_rate=1.05,
            pause_multiplier=0.9,
            volume_db=1.0,
            dynamic_range=1.2,
            breathiness=0.15,
            tremolo_amount=0.05
        ),

        # === Positive-Deactivated ===
        EmotionCategory.CALM: ProsodyParameters(
            pitch_shift_semitones=-0.5,
            pitch_variance=0.8,
            speech_rate=0.9,
            pause_multiplier=1.2,
            volume_db=-1.0,
            dynamic_range=0.8,
            breathiness=0.1,
            tremolo_amount=0.0
        ),
        EmotionCategory.CONTENT: ProsodyParameters(
            pitch_shift_semitones=0.0,
            pitch_variance=0.9,
            speech_rate=0.95,
            pause_multiplier=1.1,
            volume_db=0.0,
            dynamic_range=0.9,
            breathiness=0.05,
            tremolo_amount=0.0
        ),
        EmotionCategory.THOUGHTFUL: ProsodyParameters(
            pitch_shift_semitones=-0.5,
            pitch_variance=0.8,
            speech_rate=0.85,
            pause_multiplier=1.4,  # More pauses for thinking
            volume_db=-0.5,
            dynamic_range=0.8,
            breathiness=0.1,
            tremolo_amount=0.0
        ),
        EmotionCategory.AFFECTIONATE: ProsodyParameters(
            pitch_shift_semitones=0.5,
            pitch_variance=1.1,
            speech_rate=0.9,
            pause_multiplier=1.1,
            volume_db=-0.5,
            dynamic_range=1.0,
            breathiness=0.2,  # Warm, breathy
            tremolo_amount=0.1
        ),

        # === Neutral ===
        EmotionCategory.NEUTRAL: NEUTRAL_PROSODY,
        EmotionCategory.CONFUSED: ProsodyParameters(
            pitch_shift_semitones=0.5,
            pitch_variance=1.2,
            speech_rate=0.9,
            pause_multiplier=1.3,
            volume_db=0.0,
            dynamic_range=1.0,
            breathiness=0.1,
            tremolo_amount=0.1
        ),
    }

    def __init__(self):
        """Initialize the mapper."""
        self._intensity_scale = 1.0

    def get_prosody(
        self,
        emotion: EmotionCategory,
        intensity: float = 1.0
    ) -> ProsodyParameters:
        """
        Get prosody parameters for an emotion.

        Args:
            emotion: The emotion to express
            intensity: 0.0 to 1.5 (1.0 = full profile, lower = more subtle)

        Returns:
            ProsodyParameters to apply to TTS
        """
        profile = self.EMOTION_PROFILES.get(emotion, NEUTRAL_PROSODY)

        if intensity == 1.0:
            return profile

        # Scale parameters toward neutral based on intensity
        return ProsodyParameters(
            pitch_shift_semitones=profile.pitch_shift_semitones * intensity,
            pitch_variance=1.0 + (profile.pitch_variance - 1.0) * intensity,
            speech_rate=1.0 + (profile.speech_rate - 1.0) * intensity,
            pause_multiplier=1.0 + (profile.pause_multiplier - 1.0) * intensity,
            volume_db=profile.volume_db * intensity,
            dynamic_range=1.0 + (profile.dynamic_range - 1.0) * intensity,
            breathiness=profile.breathiness * intensity,
            tremolo_amount=profile.tremolo_amount * intensity
        )

    def from_emotion_result(
        self,
        result: EmotionResult,
        response_strategy: str = "match"
    ) -> ProsodyParameters:
        """
        Generate prosody based on detected user emotion.

        Args:
            result: Emotion detection result from user's voice
            response_strategy: How SAM should respond emotionally
                - "match": Mirror the user's emotion
                - "complement": Respond complementarily (anxious user → calm response)
                - "amplify": Amplify the emotional direction
                - "neutral": Always respond neutrally

        Returns:
            Prosody parameters for SAM's response
        """
        if response_strategy == "neutral":
            return NEUTRAL_PROSODY

        user_emotion = result.primary_emotion
        confidence = result.confidence

        if response_strategy == "match":
            # Mirror the user's emotional state
            return self.get_prosody(user_emotion, intensity=confidence * 0.8)

        elif response_strategy == "complement":
            # Respond with complementary emotion
            complement = self._get_complement(user_emotion)
            return self.get_prosody(complement, intensity=0.7)

        elif response_strategy == "amplify":
            # Amplify in the same direction but more intensely
            return self.get_prosody(user_emotion, intensity=min(1.3, confidence + 0.3))

        return NEUTRAL_PROSODY

    def _get_complement(self, emotion: EmotionCategory) -> EmotionCategory:
        """Get the complementary emotion for response."""
        complements = {
            # Negative-activated → Calm/reassuring
            EmotionCategory.ANXIOUS: EmotionCategory.CALM,
            EmotionCategory.NERVOUS: EmotionCategory.CONFIDENT,
            EmotionCategory.FRUSTRATED: EmotionCategory.CALM,
            EmotionCategory.ANGRY: EmotionCategory.CALM,
            EmotionCategory.STRESSED: EmotionCategory.CALM,
            EmotionCategory.PANICKED: EmotionCategory.CALM,
            EmotionCategory.IMPATIENT: EmotionCategory.THOUGHTFUL,

            # Negative-deactivated → Warm/encouraging
            EmotionCategory.SAD: EmotionCategory.AFFECTIONATE,
            EmotionCategory.TIRED: EmotionCategory.CALM,
            EmotionCategory.BORED: EmotionCategory.CURIOUS,
            EmotionCategory.DISAPPOINTED: EmotionCategory.AFFECTIONATE,
            EmotionCategory.LONELY: EmotionCategory.AFFECTIONATE,
            EmotionCategory.HOPELESS: EmotionCategory.CONFIDENT,

            # Positive-activated → Match energy
            EmotionCategory.EXCITED: EmotionCategory.EXCITED,
            EmotionCategory.HAPPY: EmotionCategory.HAPPY,
            EmotionCategory.PLAYFUL: EmotionCategory.PLAYFUL,
            EmotionCategory.FLIRTY: EmotionCategory.FLIRTY,
            EmotionCategory.CURIOUS: EmotionCategory.CURIOUS,
            EmotionCategory.CONFIDENT: EmotionCategory.CONFIDENT,
            EmotionCategory.AMUSED: EmotionCategory.AMUSED,

            # Positive-deactivated → Match
            EmotionCategory.CALM: EmotionCategory.CALM,
            EmotionCategory.CONTENT: EmotionCategory.CONTENT,
            EmotionCategory.THOUGHTFUL: EmotionCategory.THOUGHTFUL,
            EmotionCategory.AFFECTIONATE: EmotionCategory.AFFECTIONATE,

            # Neutral
            EmotionCategory.NEUTRAL: EmotionCategory.NEUTRAL,
            EmotionCategory.CONFUSED: EmotionCategory.CONFIDENT,
        }
        return complements.get(emotion, EmotionCategory.NEUTRAL)

    def from_dimensions(
        self,
        valence: float,
        arousal: float,
        dominance: float = 0.5
    ) -> ProsodyParameters:
        """
        Generate prosody directly from VAD dimensions.

        Useful when you have dimensional predictions but not categorical.
        """
        # Arousal affects rate and pitch variance
        speech_rate = 0.85 + (arousal * 0.4)  # 0.85-1.25
        pitch_variance = 0.6 + (arousal * 0.8)  # 0.6-1.4

        # Valence affects pitch height
        pitch_shift = valence * 2.0  # -2 to +2 semitones

        # Dominance affects volume
        volume_db = (dominance - 0.5) * 4.0  # -2 to +2 dB

        # Negative + low arousal = breathy (sad)
        breathiness = max(0, (-valence) * (1 - arousal) * 0.4)

        # Negative + high arousal = tremor (anxious)
        tremolo = max(0, (-valence) * arousal * 0.3)

        return ProsodyParameters(
            pitch_shift_semitones=pitch_shift,
            pitch_variance=pitch_variance,
            speech_rate=speech_rate,
            pause_multiplier=1.0 + (1 - arousal) * 0.5,  # More pauses when calm
            volume_db=volume_db,
            dynamic_range=0.8 + (arousal * 0.4),
            breathiness=breathiness,
            tremolo_amount=tremolo
        )


class ProsodyApplicator:
    """
    Applies prosody parameters to audio.

    Methods for different application points:
    - SSML markup for TTS engines
    - Audio post-processing (pitch shift, time stretch)
    - RVC integration
    """

    def to_ssml(
        self,
        text: str,
        prosody: ProsodyParameters
    ) -> str:
        """
        Wrap text in SSML tags for prosody control.

        Works with TTS engines that support SSML (Google, Amazon, Azure).
        """
        # Build prosody attributes
        attrs = []

        # Rate
        if prosody.speech_rate != 1.0:
            rate_pct = int((prosody.speech_rate - 1.0) * 100)
            sign = "+" if rate_pct >= 0 else ""
            attrs.append(f'rate="{sign}{rate_pct}%"')

        # Pitch
        if prosody.pitch_shift_semitones != 0:
            pitch_pct = int(prosody.pitch_shift_semitones * 8)  # Rough conversion
            sign = "+" if pitch_pct >= 0 else ""
            attrs.append(f'pitch="{sign}{pitch_pct}%"')

        # Volume
        if prosody.volume_db != 0:
            vol = "loud" if prosody.volume_db > 2 else "soft" if prosody.volume_db < -2 else "medium"
            attrs.append(f'volume="{vol}"')

        if attrs:
            attr_str = " ".join(attrs)
            return f'<prosody {attr_str}>{text}</prosody>'
        return text

    def apply_to_audio(
        self,
        audio: np.ndarray,
        sr: int,
        prosody: ProsodyParameters
    ) -> np.ndarray:
        """
        Apply prosody modifications to audio array.

        Uses librosa for pitch shifting and time stretching.
        """
        try:
            import librosa

            modified = audio.copy()

            # Time stretch (inverse of rate - faster = shorter)
            if prosody.speech_rate != 1.0:
                modified = librosa.effects.time_stretch(
                    modified,
                    rate=prosody.speech_rate
                )

            # Pitch shift
            if prosody.pitch_shift_semitones != 0:
                modified = librosa.effects.pitch_shift(
                    modified,
                    sr=sr,
                    n_steps=prosody.pitch_shift_semitones
                )

            # Volume adjustment
            if prosody.volume_db != 0:
                gain = 10 ** (prosody.volume_db / 20)
                modified = modified * gain

            # Tremolo (amplitude modulation)
            if prosody.tremolo_amount > 0:
                t = np.arange(len(modified)) / sr
                tremolo_freq = 5  # 5 Hz tremolo
                tremolo_signal = 1 + prosody.tremolo_amount * 0.2 * np.sin(2 * np.pi * tremolo_freq * t)
                modified = modified * tremolo_signal

            return modified

        except ImportError:
            print("Warning: librosa not available for audio prosody modification")
            return audio

    def get_rvc_params(
        self,
        prosody: ProsodyParameters
    ) -> Dict[str, Any]:
        """
        Convert prosody to RVC-compatible parameters.

        Returns dict that can be passed to RVC inference.
        """
        return {
            # RVC pitch shift is in semitones
            "f0_up_key": prosody.pitch_shift_semitones,
            # Some RVC implementations support these
            "rate": prosody.speech_rate,
            # Custom metadata for post-processing
            "_prosody": prosody.to_dict()
        }


# Convenience function
def emotion_to_prosody(
    emotion: EmotionCategory,
    intensity: float = 1.0
) -> ProsodyParameters:
    """Quick function to get prosody for an emotion."""
    return EmotionToProsody().get_prosody(emotion, intensity)
