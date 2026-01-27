"""
Emotion2Vec MLX Backend

Native MLX-based emotion detection using the Emotion2Vec model.
This is the high-quality neural backend (vs prosodic heuristics).
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

from ..taxonomy import (
    EmotionCategory, PrimaryDimensions, EmotionResult,
    Intensity as EmotionIntensity, EmotionPrediction, ProsodicMarkers
)
from datetime import datetime


# Mapping from Emotion2Vec 9-class to our 26-class taxonomy
EMOTION2VEC_TO_TAXONOMY = {
    "angry": EmotionCategory.ANGRY,
    "disgusted": EmotionCategory.FRUSTRATED,  # Close approximation
    "fearful": EmotionCategory.ANXIOUS,
    "happy": EmotionCategory.HAPPY,
    "neutral": EmotionCategory.NEUTRAL,
    "other": EmotionCategory.NEUTRAL,
    "sad": EmotionCategory.SAD,
    "surprised": EmotionCategory.EXCITED,  # Map surprised to excited (high arousal positive)
    "unknown": EmotionCategory.NEUTRAL,
}

# VAD (Valence-Arousal-Dominance) for each Emotion2Vec class
EMOTION2VEC_VAD = {
    "angry": PrimaryDimensions(valence=-0.6, arousal=0.8, dominance=0.7),
    "disgusted": PrimaryDimensions(valence=-0.7, arousal=0.4, dominance=0.4),
    "fearful": PrimaryDimensions(valence=-0.7, arousal=0.7, dominance=-0.6),
    "happy": PrimaryDimensions(valence=0.8, arousal=0.6, dominance=0.5),
    "neutral": PrimaryDimensions(valence=0.0, arousal=0.0, dominance=0.0),
    "other": PrimaryDimensions(valence=0.0, arousal=0.0, dominance=0.0),
    "sad": PrimaryDimensions(valence=-0.6, arousal=-0.4, dominance=-0.5),
    "surprised": PrimaryDimensions(valence=0.3, arousal=0.7, dominance=-0.1),
    "unknown": PrimaryDimensions(valence=0.0, arousal=0.0, dominance=0.0),
}


class Emotion2VecBackend:
    """
    MLX-native emotion detection using Emotion2Vec.

    This backend uses the full neural model for high-accuracy
    emotion detection. Requires MLX and converted weights.
    """

    def __init__(
        self,
        model_size: str = "base",
        weights_path: Optional[str] = None,
        device: str = "auto"
    ):
        """
        Initialize Emotion2Vec backend.

        Args:
            model_size: "base" (~90M) or "large" (~300M)
            weights_path: Path to converted MLX weights
            device: "gpu", "cpu", or "auto"
        """
        if not MLX_AVAILABLE:
            raise ImportError("MLX is required for Emotion2Vec backend")

        self.model_size = model_size
        self.model = None
        self.weights_path = weights_path

        # Find weights if not specified
        if weights_path is None:
            self.weights_path = self._find_weights()

        # Statistics
        self._stats = {
            "inferences": 0,
            "total_audio_seconds": 0.0,
            "model_loaded": False,
        }

    def _find_weights(self) -> Optional[str]:
        """Find converted weights in standard locations."""
        # Check standard locations
        search_paths = [
            # Relative to this file
            Path(__file__).parent.parent / "models" / "weights",
            # External storage (following CLAUDE.md guidelines)
            Path("/Volumes/David External/SAM_models/emotion2vec"),
            # Home directory
            Path.home() / ".cache" / "emotion2vec_mlx",
        ]

        for base_path in search_paths:
            for ext in [".safetensors", ".npz"]:
                weights_file = base_path / f"emotion2vec_{self.model_size}{ext}"
                if weights_file.exists():
                    return str(weights_file)

        return None

    def load_model(self):
        """Load the Emotion2Vec model."""
        if self.model is not None:
            return

        from ..models.emotion2vec_mlx import Emotion2VecMLX, Emotion2VecConfig

        # Get config for model size
        if self.model_size == "large":
            config = Emotion2VecConfig.large()
        else:
            config = Emotion2VecConfig.base()

        if self.weights_path and os.path.exists(self.weights_path):
            print(f"Loading Emotion2Vec {self.model_size} from {self.weights_path}")
            self.model = Emotion2VecMLX.from_pretrained(self.weights_path, config)
        else:
            print(f"No weights found. Using random initialization (for testing only)")
            print(f"Run convert_weights.py to download and convert model weights")
            self.model = Emotion2VecMLX(config)

        self._stats["model_loaded"] = True

    def unload_model(self):
        """Unload model to free memory."""
        self.model = None
        self._stats["model_loaded"] = False
        # Trigger garbage collection
        import gc
        gc.collect()

    def analyze(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> EmotionResult:
        """
        Analyze emotion from audio.

        Args:
            audio: Audio samples (mono, float32)
            sample_rate: Sample rate (should be 16kHz)

        Returns:
            EmotionResult with detected emotion
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()

        # Resample if needed
        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)

        # Normalize
        audio = audio.astype(np.float32)
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        # Convert to MLX
        audio_mx = mx.array(audio)

        # Get prediction
        prediction = self.model.predict(audio_mx)

        # Update stats
        self._stats["inferences"] += 1
        self._stats["total_audio_seconds"] += len(audio) / 16000

        # Convert to our taxonomy
        all_probs = prediction["all_probs"]
        sorted_emotions = sorted(
            all_probs.items(), key=lambda x: x[1], reverse=True
        )

        # Build categorical predictions (top 3)
        categorical = []
        for e2v_emotion, confidence in sorted_emotions[:3]:
            emotion = EMOTION2VEC_TO_TAXONOMY.get(e2v_emotion, EmotionCategory.NEUTRAL)
            dims = EMOTION2VEC_VAD.get(e2v_emotion, PrimaryDimensions(0.0, 0.0, 0.0))

            # Determine intensity
            if confidence > 0.8 and abs(dims.arousal) > 0.5:
                intensity = EmotionIntensity.STRONG
            elif confidence > 0.6:
                intensity = EmotionIntensity.MODERATE
            elif confidence > 0.3:
                intensity = EmotionIntensity.SLIGHT
            else:
                intensity = EmotionIntensity.SLIGHT

            categorical.append(EmotionPrediction(
                emotion=emotion,
                confidence=confidence,
                intensity=intensity
            ))

        # Get primary emotion's VAD
        primary_e2v = sorted_emotions[0][0]
        primary_dims = EMOTION2VEC_VAD.get(
            primary_e2v,
            PrimaryDimensions(0.0, 0.0, 0.0)
        )

        # Create basic prosodic markers (not available from E2V alone)
        prosodic = ProsodicMarkers(
            pitch_mean_hz=0.0,  # Not extracted by E2V
            pitch_std_hz=0.0,
            pitch_elevated=False,
            speech_rate_sps=0.0,
            speech_rate_category="normal",
            pause_ratio=0.0,
            voice_tremor=False,
            breathiness=0.0,
            hesitation_count=0,
            energy_variance=0.0
        )

        return EmotionResult(
            primary=primary_dims,
            categorical=categorical,
            prosodic=prosodic,
            audio_quality=1.0,  # Assume good quality
            duration_seconds=len(audio) / 16000,
            timestamp=datetime.now().isoformat(),
            backend_used="emotion2vec_mlx"
        )

    def analyze_streaming(
        self,
        audio_chunk: np.ndarray,
        context: Optional[Dict] = None,
        sample_rate: int = 16000
    ) -> EmotionResult:
        """
        Analyze emotion from streaming audio chunk.

        For streaming, we buffer short chunks and analyze
        when we have enough audio (~500ms minimum).

        Args:
            audio_chunk: Audio samples
            context: Dict to maintain state across chunks
            sample_rate: Sample rate

        Returns:
            EmotionResult (may be cached if chunk too short)
        """
        if context is None:
            context = {"buffer": np.array([]), "last_result": None}

        # Add to buffer
        context["buffer"] = np.concatenate([context["buffer"], audio_chunk])

        # Need at least 500ms of audio
        min_samples = int(0.5 * sample_rate)
        if len(context["buffer"]) < min_samples:
            # Return last result or neutral default
            if context["last_result"]:
                return context["last_result"]
            # Return neutral default
            return EmotionResult(
                primary=PrimaryDimensions(0.0, 0.0, 0.0),
                categorical=[EmotionPrediction(
                    emotion=EmotionCategory.NEUTRAL,
                    confidence=0.0,
                    intensity=EmotionIntensity.SLIGHT
                )],
                prosodic=ProsodicMarkers(
                    pitch_mean_hz=0.0, pitch_std_hz=0.0, pitch_elevated=False,
                    speech_rate_sps=0.0, speech_rate_category="normal",
                    pause_ratio=0.0, voice_tremor=False, breathiness=0.0,
                    hesitation_count=0
                ),
                audio_quality=0.0,
                duration_seconds=0.0,
                timestamp=datetime.now().isoformat(),
                backend_used="emotion2vec_mlx"
            )

        # Analyze
        result = self.analyze(context["buffer"], sample_rate)
        context["last_result"] = result

        # Keep last 1 second for context
        max_samples = int(1.0 * sample_rate)
        if len(context["buffer"]) > max_samples:
            context["buffer"] = context["buffer"][-max_samples:]

        return result

    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """Resample audio to target sample rate."""
        try:
            import librosa
            return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
        except ImportError:
            # Simple linear interpolation fallback
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio)

    def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics."""
        return {
            **self._stats,
            "model_size": self.model_size,
            "weights_path": self.weights_path,
            "backend": "emotion2vec_mlx",
        }

    def is_available(self) -> bool:
        """Check if backend is available (MLX installed, weights exist)."""
        if not MLX_AVAILABLE:
            return False
        if self.weights_path and os.path.exists(self.weights_path):
            return True
        return False


class HybridEmotionBackend:
    """
    Hybrid backend that combines Emotion2Vec (neural) with
    prosodic analysis for best results.

    Uses Emotion2Vec for categorical classification and
    prosodic features for fine-grained VAD estimation.
    """

    def __init__(self, model_size: str = "base"):
        self.e2v_backend = Emotion2VecBackend(model_size=model_size)
        self.prosodic_backend = None  # Lazy load

    def _get_prosodic_backend(self):
        """Lazy load prosodic backend."""
        if self.prosodic_backend is None:
            from .prosodic_backend import ProsodicEmotionBackend
            self.prosodic_backend = ProsodicEmotionBackend()
        return self.prosodic_backend

    def analyze(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> EmotionResult:
        """
        Analyze emotion using hybrid approach.

        1. Use Emotion2Vec for categorical classification
        2. Use prosodic analysis for fine-grained VAD
        3. Combine for best result
        """
        # Get Emotion2Vec result if available
        if self.e2v_backend.is_available():
            e2v_result = self.e2v_backend.analyze(audio, sample_rate)
        else:
            e2v_result = None

        # Get prosodic result
        prosodic = self._get_prosodic_backend()
        prosodic_result = prosodic.analyze(audio, sample_rate)

        if e2v_result is None:
            # Fall back to pure prosodic
            return prosodic_result

        # Combine results
        # Use Emotion2Vec emotion category (more accurate)
        # Use weighted average of VAD dimensions
        e2v_weight = 0.7
        prosodic_weight = 0.3

        combined_vad = PrimaryDimensions(
            valence=e2v_weight * e2v_result.primary.valence +
                    prosodic_weight * prosodic_result.primary.valence,
            arousal=e2v_weight * e2v_result.primary.arousal +
                    prosodic_weight * prosodic_result.primary.arousal,
            dominance=e2v_weight * e2v_result.primary.dominance +
                      prosodic_weight * prosodic_result.primary.dominance,
        )

        return EmotionResult(
            primary_emotion=e2v_result.primary_emotion,
            secondary_emotion=e2v_result.secondary_emotion,
            primary=combined_vad,
            confidence=e2v_result.confidence,
            secondary_confidence=e2v_result.secondary_confidence,
            intensity=e2v_result.intensity,
            raw_scores=e2v_result.raw_scores,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = {"backend": "hybrid"}
        if self.e2v_backend:
            stats["emotion2vec"] = self.e2v_backend.get_stats()
        if self.prosodic_backend:
            stats["prosodic"] = self.prosodic_backend.get_stats()
        return stats
