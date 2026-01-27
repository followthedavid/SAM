"""
Prosodic Backend - Pure audio feature analysis

No ML model required. Extracts pitch, energy, rate, pauses
and maps to emotions using rule-based logic.

Fast, lightweight, works anywhere. Good baseline.
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import time

from ..taxonomy import (
    EmotionResult, EmotionPrediction, PrimaryDimensions,
    ProsodicMarkers, EmotionCategory, Intensity,
    dimensions_to_likely_emotions
)


class ProsodicBackend:
    """
    Prosodic-only emotion detection.

    Uses acoustic features:
    - F0 (pitch) mean, std, contour
    - Energy mean, variance
    - Speech rate estimation
    - Pause detection
    - Voice quality (jitter, shimmer)
    """

    def __init__(self):
        self.name = "prosodic"
        self._baseline_pitch = None  # Personalized baseline (optional)

    def analyze(
        self,
        audio_path: str,
        sample_rate: int = 16000
    ) -> EmotionResult:
        """Analyze audio file for emotional content."""
        start_time = time.time()
        path = Path(audio_path)

        # Load audio
        waveform, sr = self._load_audio(path, sample_rate)
        duration = len(waveform) / sr

        # Extract prosodic features
        prosodic = self._extract_prosodic_features(waveform, sr)

        # Map to primary dimensions
        primary = self._prosodic_to_dimensions(prosodic)

        # Map to categorical emotions
        likely_emotions = dimensions_to_likely_emotions(
            primary.valence, primary.arousal, primary.dominance
        )

        # Create predictions with confidence based on feature clarity
        feature_confidence = self._calculate_feature_confidence(prosodic)
        categorical = []
        for i, emotion in enumerate(likely_emotions[:3]):
            conf = feature_confidence * (0.7 ** i)  # Decay for secondary emotions
            intensity = Intensity.from_score(primary.arousal)
            categorical.append(EmotionPrediction(emotion, conf, intensity))

        return EmotionResult(
            primary=primary,
            categorical=categorical,
            prosodic=prosodic,
            audio_quality=self._estimate_audio_quality(waveform, sr),
            duration_seconds=duration,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            backend_used=self.name
        )

    def _load_audio(
        self,
        path: Path,
        target_sr: int
    ) -> Tuple[np.ndarray, int]:
        """Load audio, convert to mono, resample."""
        try:
            # Try mlx-audio first
            import mlx_audio
            waveform, sr = mlx_audio.load(str(path), sr=target_sr)
            if len(waveform.shape) > 1:
                waveform = waveform.mean(axis=0)
            return np.array(waveform), sr
        except ImportError:
            pass

        try:
            # Fall back to torchaudio
            import torchaudio
            waveform, sr = torchaudio.load(str(path))
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0)

            # Resample if needed
            if sr != target_sr:
                resampler = torchaudio.transforms.Resample(sr, target_sr)
                waveform = resampler(waveform)

            return waveform.numpy(), target_sr
        except ImportError:
            pass

        # Last resort: scipy
        from scipy.io import wavfile
        sr, waveform = wavfile.read(str(path))
        if len(waveform.shape) > 1:
            waveform = waveform.mean(axis=1)
        waveform = waveform.astype(np.float32) / 32768.0
        return waveform, sr

    def _extract_prosodic_features(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> ProsodicMarkers:
        """Extract all prosodic features from audio."""

        # Pitch estimation using autocorrelation
        pitch_mean, pitch_std, pitch_elevated, voice_tremor = self._analyze_pitch(
            waveform, sr
        )

        # Energy analysis
        energy_mean, energy_var = self._analyze_energy(waveform, sr)

        # Speech rate estimation
        speech_rate, rate_category = self._estimate_speech_rate(waveform, sr)

        # Pause analysis
        pause_ratio = self._analyze_pauses(waveform, sr)

        # Hesitation detection (energy dips in speech regions)
        hesitation_count = self._count_hesitations(waveform, sr)

        # Voice quality
        breathiness = self._estimate_breathiness(waveform, sr)

        return ProsodicMarkers(
            pitch_mean_hz=pitch_mean,
            pitch_std_hz=pitch_std,
            pitch_elevated=pitch_elevated,
            speech_rate_sps=speech_rate,
            speech_rate_category=rate_category,
            pause_ratio=pause_ratio,
            voice_tremor=voice_tremor,
            breathiness=breathiness,
            hesitation_count=hesitation_count,
            energy_variance=energy_var
        )

    def _analyze_pitch(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> Tuple[float, float, bool, bool]:
        """
        Extract F0 (fundamental frequency) features.

        Returns: (mean_hz, std_hz, is_elevated, has_tremor)
        """
        try:
            # Use librosa if available for better pitch tracking
            import librosa
            f0, voiced_flag, _ = librosa.pyin(
                waveform,
                fmin=50,
                fmax=500,
                sr=sr
            )
            f0_valid = f0[~np.isnan(f0)]
        except ImportError:
            # Simple autocorrelation-based pitch
            f0_valid = self._simple_pitch_track(waveform, sr)

        if len(f0_valid) == 0:
            return 0.0, 0.0, False, False

        mean_f0 = float(np.mean(f0_valid))
        std_f0 = float(np.std(f0_valid))

        # Elevated if above typical speech range center (~180Hz)
        baseline = self._baseline_pitch or 150.0
        is_elevated = mean_f0 > baseline * 1.15

        # Tremor: high frequency pitch variation (jitter)
        if len(f0_valid) > 10:
            pitch_diff = np.abs(np.diff(f0_valid))
            jitter = np.mean(pitch_diff) / mean_f0 if mean_f0 > 0 else 0
            has_tremor = jitter > 0.02  # 2% jitter threshold
        else:
            has_tremor = False

        return mean_f0, std_f0, is_elevated, has_tremor

    def _simple_pitch_track(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> np.ndarray:
        """Simple autocorrelation pitch tracking."""
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop

        pitches = []
        for start in range(0, len(waveform) - frame_length, hop_length):
            frame = waveform[start:start + frame_length]

            # Autocorrelation
            corr = np.correlate(frame, frame, mode='full')
            corr = corr[len(corr)//2:]

            # Find first peak (skip 0-lag)
            min_lag = int(sr / 500)  # Max 500Hz
            max_lag = int(sr / 50)   # Min 50Hz

            if max_lag > len(corr):
                continue

            peak_region = corr[min_lag:max_lag]
            if len(peak_region) == 0:
                continue

            peak_idx = np.argmax(peak_region) + min_lag

            # Only accept if correlation is strong enough
            if corr[peak_idx] > 0.3 * corr[0]:
                pitch = sr / peak_idx
                if 50 < pitch < 500:
                    pitches.append(pitch)

        return np.array(pitches)

    def _analyze_energy(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> Tuple[float, float]:
        """Analyze energy/loudness characteristics."""
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)

        energies = []
        for start in range(0, len(waveform) - frame_length, hop_length):
            frame = waveform[start:start + frame_length]
            energy = np.sqrt(np.mean(frame ** 2))
            energies.append(energy)

        if not energies:
            return 0.0, 0.0

        mean_energy = float(np.mean(energies))
        energy_var = float(np.var(energies))

        return mean_energy, energy_var

    def _estimate_speech_rate(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> Tuple[float, str]:
        """
        Estimate speech rate in syllables per second.

        Uses energy envelope to count syllable-like peaks.
        """
        # Compute smoothed energy envelope
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)

        envelope = []
        for start in range(0, len(waveform) - frame_length, hop_length):
            frame = waveform[start:start + frame_length]
            envelope.append(np.sqrt(np.mean(frame ** 2)))

        envelope = np.array(envelope)

        if len(envelope) < 10:
            return 0.0, "unknown"

        # Smooth
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(envelope, kernel, mode='same')

        # Find peaks (syllable nuclei)
        threshold = np.mean(smoothed) * 0.5
        peaks = []
        for i in range(1, len(smoothed) - 1):
            if (smoothed[i] > smoothed[i-1] and
                smoothed[i] > smoothed[i+1] and
                smoothed[i] > threshold):
                peaks.append(i)

        # Calculate rate
        duration = len(waveform) / sr
        if duration > 0:
            syllable_rate = len(peaks) / duration
        else:
            syllable_rate = 0.0

        # Categorize
        if syllable_rate < 3.5:
            category = "slow"
        elif syllable_rate < 5.5:
            category = "normal"
        else:
            category = "fast"

        return syllable_rate, category

    def _analyze_pauses(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> float:
        """Calculate ratio of silence to total duration."""
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)

        silence_frames = 0
        total_frames = 0

        # Silence threshold (adaptive)
        rms = np.sqrt(np.mean(waveform ** 2))
        silence_thresh = rms * 0.1

        for start in range(0, len(waveform) - frame_length, hop_length):
            frame = waveform[start:start + frame_length]
            frame_rms = np.sqrt(np.mean(frame ** 2))

            total_frames += 1
            if frame_rms < silence_thresh:
                silence_frames += 1

        return silence_frames / total_frames if total_frames > 0 else 0.0

    def _count_hesitations(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> int:
        """
        Count hesitation markers (brief energy dips in speech).

        Hesitations are short (100-400ms) low-energy segments
        within otherwise continuous speech.
        """
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)

        energies = []
        for start in range(0, len(waveform) - frame_length, hop_length):
            frame = waveform[start:start + frame_length]
            energies.append(np.sqrt(np.mean(frame ** 2)))

        energies = np.array(energies)
        if len(energies) < 20:
            return 0

        # Find speech threshold
        mean_e = np.mean(energies)
        speech_thresh = mean_e * 0.3

        # Look for brief dips (4-16 frames = 100-400ms)
        hesitation_count = 0
        in_dip = False
        dip_length = 0

        for e in energies:
            if e < speech_thresh:
                if not in_dip:
                    in_dip = True
                    dip_length = 1
                else:
                    dip_length += 1
            else:
                if in_dip and 4 <= dip_length <= 16:
                    hesitation_count += 1
                in_dip = False
                dip_length = 0

        return hesitation_count

    def _estimate_breathiness(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> float:
        """
        Estimate voice breathiness (0-1).

        Breathy voice has more noise in the spectrum.
        """
        try:
            import librosa
            # Spectral flatness is higher for breathy/noisy voice
            flatness = librosa.feature.spectral_flatness(y=waveform)
            return float(np.mean(flatness))
        except ImportError:
            # Simple approximation: ratio of high to low frequencies
            fft = np.abs(np.fft.rfft(waveform))
            low = np.mean(fft[:len(fft)//4])
            high = np.mean(fft[len(fft)//2:])
            if low > 0:
                return min(1.0, high / low)
            return 0.5

    def _prosodic_to_dimensions(
        self,
        prosodic: ProsodicMarkers
    ) -> PrimaryDimensions:
        """
        Map prosodic features to valence/arousal/dominance.

        Based on acoustic correlates of emotion from literature.
        """
        # Arousal: high pitch, fast rate, high energy variance = high arousal
        arousal = 0.5
        if prosodic.pitch_elevated:
            arousal += 0.2
        if prosodic.speech_rate_category == "fast":
            arousal += 0.15
        elif prosodic.speech_rate_category == "slow":
            arousal -= 0.15
        if prosodic.energy_variance > 0.01:
            arousal += 0.1
        if prosodic.voice_tremor:
            arousal += 0.1

        # Valence: harder to determine from prosody alone
        # High pitch + high rate can be positive (excited) or negative (anxious)
        # Use other cues
        valence = 0.0  # Start neutral
        if prosodic.breathiness > 0.3:
            valence -= 0.1  # Breathy can indicate sadness
        if prosodic.hesitation_count > 2:
            valence -= 0.15  # Hesitation often negative
        if prosodic.pause_ratio > 0.3:
            valence -= 0.1  # Many pauses often negative

        # Dominance: loud, fast, low pitch variation = dominant
        dominance = 0.5
        if prosodic.energy_variance > 0.02:
            dominance += 0.1
        if prosodic.speech_rate_category == "fast":
            dominance += 0.1
        if prosodic.pitch_std_hz < 30:  # Monotone
            dominance += 0.1
        if prosodic.hesitation_count > 2:
            dominance -= 0.2

        return PrimaryDimensions(
            valence=max(-1.0, min(1.0, valence)),
            arousal=max(0.0, min(1.0, arousal)),
            dominance=max(0.0, min(1.0, dominance))
        )

    def _calculate_feature_confidence(
        self,
        prosodic: ProsodicMarkers
    ) -> float:
        """
        Calculate confidence based on feature clarity.

        High confidence when features are distinctive.
        """
        confidence = 0.5  # Base

        # Clear pitch = higher confidence
        if prosodic.pitch_mean_hz > 0:
            confidence += 0.1
            if prosodic.pitch_std_hz > 20:  # Expressive
                confidence += 0.1

        # Clear rate = higher confidence
        if prosodic.speech_rate_sps > 0:
            confidence += 0.1

        # Distinctive features boost confidence
        if prosodic.voice_tremor:
            confidence += 0.1  # Clear anxiety marker
        if prosodic.speech_rate_category in ["fast", "slow"]:
            confidence += 0.05

        return min(0.75, confidence)  # Cap at 0.75 for prosodic-only

    def _estimate_audio_quality(
        self,
        waveform: np.ndarray,
        sr: int
    ) -> float:
        """Estimate audio quality (affects confidence)."""
        # Check for clipping
        max_amp = np.max(np.abs(waveform))
        if max_amp > 0.99:
            return 0.5  # Likely clipped

        # Check for very low signal
        rms = np.sqrt(np.mean(waveform ** 2))
        if rms < 0.01:
            return 0.3  # Very quiet

        # Check signal-to-noise (simple estimate)
        # Good quality if dynamic range is reasonable
        if max_amp > 0 and rms > 0:
            crest_factor = max_amp / rms
            if 3 < crest_factor < 20:
                return 0.9  # Good dynamic range
            else:
                return 0.6  # Unusual dynamics

        return 0.7  # Default reasonable quality

    def set_baseline(self, pitch_hz: float):
        """Set personalized pitch baseline for this speaker."""
        self._baseline_pitch = pitch_hz
