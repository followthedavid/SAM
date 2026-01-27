"""
Turn Predictor - Predict when user is done speaking

Instead of just waiting for silence, this predicts turn-end from:
- Prosodic cues (falling pitch, slowing rate)
- Linguistic cues (complete sentences, question marks)
- Pause patterns (mid-turn pauses vs end-of-turn)

This is what makes conversation feel natural - responding at the
right moment, not just after N seconds of silence.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
import re


@dataclass
class TurnPrediction:
    """Prediction about whether the user's turn is ending."""
    probability: float  # 0-1, how likely they're done
    confidence: float   # How confident we are in this prediction
    reason: str         # Why we think they're done/not done

    # Contributing factors
    prosodic_score: float = 0.0
    linguistic_score: float = 0.0
    pause_score: float = 0.0


class TurnPredictor:
    """
    Predicts when a speaker's turn is ending.

    Uses multiple cues:
    1. Prosodic: pitch contour, speech rate, energy
    2. Linguistic: sentence completion, questions
    3. Temporal: pause duration, rhythm

    Can be upgraded to neural predictor in future.
    """

    def __init__(self, mode: str = "heuristic"):
        """
        Initialize predictor.

        Args:
            mode: "heuristic" (rule-based, works now) or "neural" (future)
        """
        self.mode = mode

        # Thresholds (tunable)
        self.silence_threshold_ms = 700  # Silence to consider turn-end
        self.pitch_drop_threshold = 0.15  # Relative pitch drop
        self.rate_slow_threshold = 0.2   # Relative rate slowdown

        # State for temporal tracking
        self._recent_pitches: List[float] = []
        self._recent_energies: List[float] = []
        self._recent_rates: List[float] = []
        self._last_word_time: float = 0
        self._current_pause_ms: float = 0

    def predict(
        self,
        partial_text: str,
        audio_features: Optional[dict] = None,
        pause_duration_ms: float = 0
    ) -> TurnPrediction:
        """
        Predict if the current turn is ending.

        Args:
            partial_text: Transcript so far
            audio_features: Optional prosodic features dict
            pause_duration_ms: Current pause duration

        Returns:
            TurnPrediction with probability and reasons
        """
        self._current_pause_ms = pause_duration_ms

        # Get scores from each cue type
        linguistic_score, linguistic_reason = self._linguistic_score(partial_text)
        pause_score, pause_reason = self._pause_score(pause_duration_ms)

        if audio_features:
            prosodic_score, prosodic_reason = self._prosodic_score(audio_features)
        else:
            prosodic_score, prosodic_reason = 0.5, "no_audio_features"

        # Combine scores
        # Weights: linguistic cues are strongest, then pause, then prosodic
        weights = {
            "linguistic": 0.45,
            "pause": 0.35,
            "prosodic": 0.20
        }

        combined = (
            linguistic_score * weights["linguistic"] +
            pause_score * weights["pause"] +
            prosodic_score * weights["prosodic"]
        )

        # Boost if multiple strong signals agree
        strong_signals = sum([
            linguistic_score > 0.7,
            pause_score > 0.7,
            prosodic_score > 0.7
        ])
        if strong_signals >= 2:
            combined = min(1.0, combined + 0.15)

        # Determine primary reason
        scores = [
            (linguistic_score, linguistic_reason),
            (pause_score, pause_reason),
            (prosodic_score, prosodic_reason)
        ]
        primary_reason = max(scores, key=lambda x: x[0])[1]

        # Confidence based on agreement between signals
        score_std = np.std([linguistic_score, pause_score, prosodic_score])
        confidence = 1.0 - (score_std * 2)  # Lower std = higher confidence

        return TurnPrediction(
            probability=combined,
            confidence=max(0.3, confidence),
            reason=primary_reason,
            prosodic_score=prosodic_score,
            linguistic_score=linguistic_score,
            pause_score=pause_score
        )

    def _linguistic_score(self, text: str) -> Tuple[float, str]:
        """
        Score based on linguistic completeness.

        Looks for:
        - Complete sentences (period, question mark, exclamation)
        - Question endings
        - Trailing off ("so...", "well...")
        - Incomplete thoughts
        """
        if not text.strip():
            return 0.3, "no_text"

        text = text.strip()

        # Strong completion signals
        if text.endswith("?"):
            return 0.95, "question_complete"

        if text.endswith(".") or text.endswith("!"):
            # Check if it's a real sentence end or abbreviation
            words = text.split()
            if len(words) >= 3:
                return 0.9, "sentence_complete"
            else:
                return 0.7, "short_sentence"

        # Trailing off patterns
        if text.endswith("...") or text.endswith(".."):
            return 0.75, "trailing_off"

        # Common turn-end phrases
        turn_end_phrases = [
            "you know", "right", "so yeah", "anyway", "that's it",
            "i guess", "i think", "i mean", "something like that",
            "or something", "or whatever", "and stuff"
        ]
        for phrase in turn_end_phrases:
            if text.lower().endswith(phrase):
                return 0.8, f"turn_end_phrase:{phrase}"

        # Incomplete sentence signals
        incomplete_patterns = [
            r"\b(but|and|or|so|because|if|when|while|although)\s*$",
            r"\b(the|a|an|my|your|their|his|her|its)\s*$",
            r"\b(to|of|for|with|in|on|at)\s*$",
        ]
        for pattern in incomplete_patterns:
            if re.search(pattern, text.lower()):
                return 0.2, "incomplete_sentence"

        # Default: middle of turn
        return 0.4, "mid_utterance"

    def _pause_score(self, pause_ms: float) -> Tuple[float, str]:
        """
        Score based on pause duration.

        Key insight: not all pauses are turn-endings.
        Short pauses (< 300ms) = breathing, thinking
        Medium pauses (300-700ms) = clause boundary or hesitation
        Long pauses (> 700ms) = likely turn end
        """
        if pause_ms < 200:
            return 0.1, "no_pause"

        if pause_ms < 400:
            return 0.25, "brief_pause"

        if pause_ms < 600:
            return 0.45, "short_pause"

        if pause_ms < 800:
            return 0.7, "medium_pause"

        if pause_ms < 1200:
            return 0.85, "long_pause"

        # Very long pause
        return 0.95, "extended_silence"

    def _prosodic_score(self, features: dict) -> Tuple[float, str]:
        """
        Score based on prosodic features.

        Turn-ending prosody typically shows:
        - Falling pitch (declarative) or rising then falling (question)
        - Slowing speech rate
        - Decreasing energy
        - Creaky voice (sometimes)
        """
        score = 0.5
        reason = "neutral"

        pitch = features.get("pitch_mean", 0)
        pitch_slope = features.get("pitch_slope", 0)
        energy = features.get("energy_mean", 0)
        energy_slope = features.get("energy_slope", 0)
        rate = features.get("speech_rate", 0)

        # Track recent values
        if pitch > 0:
            self._recent_pitches.append(pitch)
            if len(self._recent_pitches) > 10:
                self._recent_pitches.pop(0)

        if energy > 0:
            self._recent_energies.append(energy)
            if len(self._recent_energies) > 10:
                self._recent_energies.pop(0)

        # Pitch falling = likely turn end
        if pitch_slope < -self.pitch_drop_threshold:
            score += 0.2
            reason = "falling_pitch"
        elif len(self._recent_pitches) >= 3:
            recent_trend = self._recent_pitches[-1] - np.mean(self._recent_pitches[:-1])
            if recent_trend < -10:  # Hz drop
                score += 0.15
                reason = "pitch_dropping"

        # Energy falling
        if energy_slope < -0.1:
            score += 0.15
            reason = reason + "+falling_energy" if reason != "neutral" else "falling_energy"
        elif len(self._recent_energies) >= 3:
            recent_trend = self._recent_energies[-1] - np.mean(self._recent_energies[:-1])
            if recent_trend < -0.05:
                score += 0.1

        # Rate slowing
        if len(self._recent_rates) >= 3 and rate > 0:
            self._recent_rates.append(rate)
            if rate < np.mean(self._recent_rates[:-1]) * (1 - self.rate_slow_threshold):
                score += 0.15
                reason = reason + "+slowing" if reason != "neutral" else "slowing_rate"

        return min(1.0, score), reason

    def update_audio_features(
        self,
        pitch: float,
        energy: float,
        rate: float
    ):
        """Update tracked audio features for trend analysis."""
        if pitch > 0:
            self._recent_pitches.append(pitch)
            if len(self._recent_pitches) > 10:
                self._recent_pitches.pop(0)

        if energy > 0:
            self._recent_energies.append(energy)
            if len(self._recent_energies) > 10:
                self._recent_energies.pop(0)

        if rate > 0:
            self._recent_rates.append(rate)
            if len(self._recent_rates) > 10:
                self._recent_rates.pop(0)

    def reset(self):
        """Reset state for new turn."""
        self._recent_pitches = []
        self._recent_energies = []
        self._recent_rates = []
        self._current_pause_ms = 0

    def get_optimal_response_delay(
        self,
        prediction: TurnPrediction,
        user_emotion: str = "neutral"
    ) -> int:
        """
        Calculate optimal delay before responding.

        Natural conversations have variable response times:
        - Simple acknowledgments: fast (100-200ms)
        - Normal responses: medium (300-500ms)
        - Complex/thoughtful: slow (600-1000ms)
        - Emotional support: deliberate (500-800ms)
        """
        base_delay = 300  # ms

        # High confidence turn-end = respond faster
        if prediction.probability > 0.9 and prediction.confidence > 0.8:
            base_delay = 200

        # Question = faster response expected
        if "question" in prediction.reason:
            base_delay = min(base_delay, 250)

        # User seems upset = slightly slower, more deliberate
        if user_emotion in ["anxious", "frustrated", "sad", "angry"]:
            base_delay += 200

        # User seems excited = can respond faster
        if user_emotion in ["excited", "happy", "playful"]:
            base_delay = max(150, base_delay - 100)

        # Add some natural variation (±50ms)
        variation = np.random.randint(-50, 50)
        base_delay += variation

        return max(100, min(1000, base_delay))


class NeuralTurnPredictor(TurnPredictor):
    """
    Future: Neural network for turn-taking prediction.

    Would use a small transformer or CNN trained on:
    - Audio features (MFCCs, pitch, energy)
    - Token embeddings from partial transcript
    - Conversation context

    For now, falls back to heuristic.
    """

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(mode="neural")
        self.model = None
        self.model_path = model_path

        if model_path:
            self._load_model(model_path)

    def _load_model(self, path: str):
        """Load neural model."""
        # TODO: Implement MLX-based turn prediction model
        print(f"Neural turn predictor not yet implemented, using heuristic")
        self.mode = "heuristic"

    def predict(
        self,
        partial_text: str,
        audio_features: Optional[dict] = None,
        pause_duration_ms: float = 0
    ) -> TurnPrediction:
        """Neural prediction (falls back to heuristic for now)."""
        if self.model is None:
            return super().predict(partial_text, audio_features, pause_duration_ms)

        # TODO: Run neural inference
        return super().predict(partial_text, audio_features, pause_duration_ms)
