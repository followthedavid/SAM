"""
Voice Emotion Detector - Main Interface

Unified interface for voice emotion detection with multiple backends.
"""

from pathlib import Path
from typing import Optional, List, Union
import time
import numpy as np

from .taxonomy import EmotionResult, EmotionCategory
from .backends import get_available_backends, create_backend


class VoiceEmotionDetector:
    """
    Detects nuanced emotional states from voice.

    Usage:
        detector = VoiceEmotionDetector()
        result = detector.analyze("audio.wav")

        print(f"Primary: {result.primary_emotion.value}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Context: {result.to_context_string()}")

    Backends:
        - prosodic: Fast, no ML, pure acoustic features (default)
        - whisper_mlx: MLX Whisper embeddings + classifier
        - emotion2vec: Full Emotion2Vec port (coming soon)
    """

    def __init__(
        self,
        backend: str = "prosodic",
        device: str = "auto"
    ):
        """
        Initialize detector.

        Args:
            backend: Which backend to use ("prosodic", "whisper_mlx", "emotion2vec")
            device: Device for inference ("auto", "cpu", "mps", "cuda")
        """
        available = get_available_backends()

        if backend not in available:
            fallback = available[0] if available else "prosodic"
            print(f"Backend '{backend}' not available, using '{fallback}'")
            backend = fallback

        self.backend_name = backend
        self._backend = create_backend(backend)
        self._device = device

        # History for trajectory analysis
        self._history: List[EmotionResult] = []
        self._max_history = 100

        # Personalization
        self._speaker_baseline = None

    def analyze(
        self,
        audio: Union[str, Path, np.ndarray],
        sample_rate: int = 16000
    ) -> EmotionResult:
        """
        Analyze audio for emotional content.

        Args:
            audio: Path to audio file or numpy array
            sample_rate: Sample rate if audio is array

        Returns:
            EmotionResult with full analysis
        """
        if isinstance(audio, (str, Path)):
            audio_path = str(audio)
        else:
            # Save array to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                audio_path = f.name
                self._save_audio(audio, sample_rate, audio_path)

        result = self._backend.analyze(audio_path, sample_rate)

        # Add to history
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return result

    def analyze_streaming(
        self,
        chunk: np.ndarray,
        sample_rate: int = 16000,
        min_duration: float = 1.0
    ) -> Optional[EmotionResult]:
        """
        Analyze audio chunk for streaming applications.

        Accumulates audio until min_duration reached, then analyzes.
        Returns None if not enough audio accumulated yet.
        """
        if not hasattr(self, '_stream_buffer'):
            self._stream_buffer = []
            self._stream_samples = 0

        self._stream_buffer.append(chunk)
        self._stream_samples += len(chunk)

        # Check if we have enough
        required_samples = int(min_duration * sample_rate)
        if self._stream_samples >= required_samples:
            # Analyze accumulated audio
            full_audio = np.concatenate(self._stream_buffer)
            result = self.analyze(full_audio, sample_rate)

            # Reset buffer (keep last bit for continuity)
            overlap = int(0.5 * sample_rate)  # 500ms overlap
            self._stream_buffer = [full_audio[-overlap:]]
            self._stream_samples = overlap

            return result

        return None

    def get_history(
        self,
        window_seconds: float = 60.0
    ) -> List[EmotionResult]:
        """Get recent emotion detections."""
        if not self._history:
            return []

        # Filter by time window
        cutoff_time = time.time() - window_seconds
        recent = []

        for result in reversed(self._history):
            try:
                result_time = time.mktime(
                    time.strptime(result.timestamp, "%Y-%m-%d %H:%M:%S")
                )
                if result_time >= cutoff_time:
                    recent.insert(0, result)
                else:
                    break
            except:
                recent.insert(0, result)

        return recent

    def get_trajectory(self) -> dict:
        """
        Analyze emotional trajectory over recent history.

        Returns dict with:
        - trend: "improving", "declining", "stable", "volatile"
        - valence_change: float
        - arousal_change: float
        - dominant_emotion: EmotionCategory
        - shifts: list of notable emotion changes
        """
        history = self.get_history(window_seconds=300)  # Last 5 min

        if len(history) < 3:
            return {
                "trend": "insufficient_data",
                "valence_change": 0.0,
                "arousal_change": 0.0,
                "dominant_emotion": EmotionCategory.NEUTRAL,
                "shifts": []
            }

        # Calculate changes
        first_half = history[:len(history)//2]
        second_half = history[len(history)//2:]

        avg_valence_1 = np.mean([r.primary.valence for r in first_half])
        avg_valence_2 = np.mean([r.primary.valence for r in second_half])
        valence_change = avg_valence_2 - avg_valence_1

        avg_arousal_1 = np.mean([r.primary.arousal for r in first_half])
        avg_arousal_2 = np.mean([r.primary.arousal for r in second_half])
        arousal_change = avg_arousal_2 - avg_arousal_1

        # Determine trend
        valence_std = np.std([r.primary.valence for r in history])
        if valence_std > 0.3:
            trend = "volatile"
        elif valence_change > 0.15:
            trend = "improving"
        elif valence_change < -0.15:
            trend = "declining"
        else:
            trend = "stable"

        # Find dominant emotion
        emotion_counts = {}
        for result in history:
            emotion = result.primary_emotion
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        dominant = max(emotion_counts, key=emotion_counts.get)

        # Find notable shifts
        shifts = []
        prev_emotion = None
        for result in history:
            if prev_emotion and result.primary_emotion != prev_emotion:
                if result.confidence > 0.5:
                    shifts.append({
                        "from": prev_emotion.value,
                        "to": result.primary_emotion.value,
                        "time": result.timestamp
                    })
            prev_emotion = result.primary_emotion

        return {
            "trend": trend,
            "valence_change": float(valence_change),
            "arousal_change": float(arousal_change),
            "dominant_emotion": dominant,
            "shifts": shifts[-5:]  # Last 5 shifts
        }

    def calibrate_baseline(self, audio_samples: List[str]) -> dict:
        """
        Calibrate to a specific speaker's baseline.

        Provide 3-5 samples of the speaker in neutral state.
        Returns baseline statistics.
        """
        pitches = []
        rates = []

        for sample in audio_samples:
            result = self.analyze(sample)
            if result.prosodic.pitch_mean_hz > 0:
                pitches.append(result.prosodic.pitch_mean_hz)
            if result.prosodic.speech_rate_sps > 0:
                rates.append(result.prosodic.speech_rate_sps)

        if not pitches:
            return {"error": "Could not extract pitch from samples"}

        baseline = {
            "pitch_mean": float(np.mean(pitches)),
            "pitch_std": float(np.std(pitches)),
            "speech_rate_mean": float(np.mean(rates)) if rates else 4.0,
            "sample_count": len(audio_samples)
        }

        # Set baseline on backend
        if hasattr(self._backend, 'set_baseline'):
            self._backend.set_baseline(baseline["pitch_mean"])

        self._speaker_baseline = baseline
        return baseline

    def clear_history(self):
        """Clear emotion history."""
        self._history = []

    def get_stats(self) -> dict:
        """Get detector statistics."""
        return {
            "backend": self.backend_name,
            "history_length": len(self._history),
            "has_baseline": self._speaker_baseline is not None,
            "available_backends": get_available_backends()
        }

    def _save_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        path: str
    ):
        """Save numpy array as WAV file."""
        try:
            from scipy.io import wavfile
            # Ensure int16 format
            if audio.dtype == np.float32 or audio.dtype == np.float64:
                audio = (audio * 32767).astype(np.int16)
            wavfile.write(path, sample_rate, audio)
        except ImportError:
            # Manual WAV writing
            import struct
            with open(path, 'wb') as f:
                # WAV header
                num_samples = len(audio)
                byte_rate = sample_rate * 2
                f.write(b'RIFF')
                f.write(struct.pack('<I', 36 + num_samples * 2))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, byte_rate, 2, 16))
                f.write(b'data')
                f.write(struct.pack('<I', num_samples * 2))
                if audio.dtype != np.int16:
                    audio = (audio * 32767).astype(np.int16)
                f.write(audio.tobytes())


# Quick test
if __name__ == "__main__":
    import sys

    print("Voice Emotion Detector")
    print("=" * 50)
    print(f"Available backends: {get_available_backends()}")

    detector = VoiceEmotionDetector(backend="prosodic")
    print(f"Using: {detector.backend_name}")

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        print(f"\nAnalyzing: {audio_path}")

        result = detector.analyze(audio_path)

        print(f"\nResults:")
        print(f"  Primary emotion: {result.primary_emotion.value}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Valence: {result.primary.valence:.2f}")
        print(f"  Arousal: {result.primary.arousal:.2f}")
        print(f"  Dominance: {result.primary.dominance:.2f}")
        print(f"\nProsodic markers:")
        print(f"  Pitch: {result.prosodic.pitch_mean_hz:.1f} Hz (std: {result.prosodic.pitch_std_hz:.1f})")
        print(f"  Speech rate: {result.prosodic.speech_rate_sps:.1f} sps ({result.prosodic.speech_rate_category})")
        print(f"  Tremor: {result.prosodic.voice_tremor}")
        print(f"  Hesitations: {result.prosodic.hesitation_count}")
        print(f"\nContext string for LLM:")
        print(f"  {result.to_context_string()}")
    else:
        print("\nUsage: python detector.py <audio_file.wav>")
