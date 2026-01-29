"""
Audio Utilities for SAM Brain

Provides audio loading and processing with MLX-first approach.
Falls back to torchaudio or standard library when needed.

Priority order:
1. mlx-audio (fastest on Apple Silicon)
2. torchaudio (if available)
3. wave + numpy (always available)
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union
import warnings


def load_audio(
    path: Union[str, Path],
    target_sr: Optional[int] = None,
    mono: bool = True,
) -> Tuple[np.ndarray, int]:
    """
    Load audio file to numpy array.

    Args:
        path: Path to audio file
        target_sr: Target sample rate (None = keep original)
        mono: Convert to mono if True

    Returns:
        (waveform, sample_rate) - waveform is float32, normalized [-1, 1]
    """
    path = Path(path)

    # Try soundfile first (if available - handles many formats)
    try:
        import soundfile as sf

        waveform, sr = sf.read(str(path), dtype='float32')

        # Handle mono conversion
        if mono and len(waveform.shape) > 1:
            waveform = waveform.mean(axis=1)

        # Resample if needed
        if target_sr is not None and sr != target_sr:
            waveform = _simple_resample(waveform, sr, target_sr)
            sr = target_sr

        return waveform.astype(np.float32), sr

    except ImportError:
        pass
    except Exception as e:
        warnings.warn(f"soundfile failed: {e}, trying fallback")

    # Try torchaudio second
    try:
        import torch
        import torchaudio

        waveform, sr = torchaudio.load(str(path))

        # Convert to mono
        if mono and waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Resample if needed
        if target_sr is not None and sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)
            sr = target_sr

        # Convert to numpy
        waveform = waveform.numpy().squeeze()
        return waveform.astype(np.float32), sr

    except ImportError:
        pass
    except Exception as e:
        warnings.warn(f"torchaudio failed: {e}, trying fallback")

    # Fallback to wave module (WAV only)
    return _load_with_wave(path, target_sr, mono)


def _load_with_wave(
    path: Path,
    target_sr: Optional[int],
    mono: bool
) -> Tuple[np.ndarray, int]:
    """Load audio using standard library (WAV only)."""
    import wave

    with wave.open(str(path), 'rb') as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(n_frames)

    # Convert to numpy array
    if sample_width == 1:
        waveform = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        waveform = (waveform - 128) / 128.0
    elif sample_width == 2:
        waveform = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        waveform = waveform / 32768.0
    elif sample_width == 3:
        # 24-bit audio
        raw = np.frombuffer(frames, dtype=np.uint8)
        waveform = np.zeros(len(raw) // 3, dtype=np.float32)
        for i in range(len(waveform)):
            val = raw[i*3] | (raw[i*3+1] << 8) | (raw[i*3+2] << 16)
            if val >= 0x800000:
                val -= 0x1000000
            waveform[i] = val / 8388608.0
    elif sample_width == 4:
        waveform = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
        waveform = waveform / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    # Handle multi-channel
    if n_channels > 1:
        waveform = waveform.reshape(-1, n_channels)
        if mono:
            waveform = waveform.mean(axis=1)

    # Resample if needed
    if target_sr is not None and sr != target_sr:
        waveform = _simple_resample(waveform, sr, target_sr)
        sr = target_sr

    return waveform.astype(np.float32), sr


def _simple_resample(
    waveform: np.ndarray,
    orig_sr: int,
    target_sr: int
) -> np.ndarray:
    """Simple linear interpolation resampling."""
    if orig_sr == target_sr:
        return waveform

    orig_len = len(waveform)
    new_len = int(orig_len * target_sr / orig_sr)

    indices = np.linspace(0, orig_len - 1, new_len)
    return np.interp(indices, np.arange(orig_len), waveform)


def load_audio_torch(
    path: Union[str, Path],
    target_sr: Optional[int] = None,
    mono: bool = True,
) -> Tuple["torch.Tensor", int]:
    """
    Load audio and return as PyTorch tensor.

    For compatibility with pyannote and other torch-based models.
    """
    import torch

    waveform, sr = load_audio(path, target_sr, mono)

    # Convert to torch tensor with correct shape for pyannote [channels, samples]
    tensor = torch.from_numpy(waveform)
    if tensor.dim() == 1:
        tensor = tensor.unsqueeze(0)  # Add channel dimension

    return tensor, sr


def load_audio_mlx(
    path: Union[str, Path],
    target_sr: Optional[int] = None,
    mono: bool = True,
) -> Tuple["mx.array", int]:
    """
    Load audio and return as MLX array.

    For use with MLX-based models like Emotion2Vec.
    """
    import mlx.core as mx

    waveform, sr = load_audio(path, target_sr, mono)
    return mx.array(waveform), sr


def compute_energy(
    waveform: np.ndarray,
    sr: int,
    window_ms: float = 25.0,
    hop_ms: float = 10.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute frame-wise energy (RMS).

    Args:
        waveform: Audio samples
        sr: Sample rate
        window_ms: Window size in milliseconds
        hop_ms: Hop size in milliseconds

    Returns:
        (energies, timestamps) - energy values and their timestamps
    """
    window_size = int(window_ms * sr / 1000)
    hop_size = int(hop_ms * sr / 1000)

    energies = []
    timestamps = []

    for start in range(0, len(waveform) - window_size, hop_size):
        frame = waveform[start:start + window_size]
        energy = np.sqrt(np.mean(frame ** 2))
        energies.append(energy)
        timestamps.append(start / sr)

    return np.array(energies), np.array(timestamps)


def find_high_energy_segments(
    waveform: np.ndarray,
    sr: int,
    threshold_ratio: float = 2.0,
    min_duration: float = 0.3,
    max_gap: float = 1.0,
) -> list:
    """
    Find segments with energy above threshold.

    Args:
        waveform: Audio samples
        sr: Sample rate
        threshold_ratio: Minimum energy as multiple of median
        min_duration: Minimum segment duration in seconds
        max_gap: Maximum gap between segments to merge

    Returns:
        List of dicts with start, end, duration, energy
    """
    energies, timestamps = compute_energy(waveform, sr)

    if len(energies) == 0:
        return []

    median_energy = np.median(energies)
    threshold = median_energy * threshold_ratio

    # Find high-energy windows
    high_energy = []
    for energy, ts in zip(energies, timestamps):
        if energy > threshold:
            high_energy.append((ts, energy))

    if not high_energy:
        return []

    # Convert to segments
    segments = []
    current_start = high_energy[0][0]
    current_end = current_start + 0.025  # window size
    current_energy_sum = high_energy[0][1]
    current_count = 1

    for ts, energy in high_energy[1:]:
        if ts - current_end <= max_gap:
            current_end = ts + 0.025
            current_energy_sum += energy
            current_count += 1
        else:
            duration = current_end - current_start
            if duration >= min_duration:
                segments.append({
                    "start": current_start,
                    "end": current_end,
                    "duration": duration,
                    "energy": current_energy_sum / current_count
                })
            current_start = ts
            current_end = ts + 0.025
            current_energy_sum = energy
            current_count = 1

    # Don't forget last segment
    duration = current_end - current_start
    if duration >= min_duration:
        segments.append({
            "start": current_start,
            "end": current_end,
            "duration": duration,
            "energy": current_energy_sum / current_count
        })

    return segments


def get_audio_backend() -> str:
    """Return the name of the available audio backend."""
    try:
        import soundfile
        return "soundfile"
    except ImportError:
        pass

    try:
        import torchaudio
        return "torchaudio"
    except ImportError:
        pass

    return "wave"


# Quick test when run directly
if __name__ == "__main__":
    print(f"Audio backend: {get_audio_backend()}")

    # Test with a sample file if provided
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"\nLoading: {path}")
        waveform, sr = load_audio(path, target_sr=16000)
        print(f"Sample rate: {sr}")
        print(f"Duration: {len(waveform)/sr:.2f}s")
        print(f"Shape: {waveform.shape}")
        print(f"Range: [{waveform.min():.3f}, {waveform.max():.3f}]")
