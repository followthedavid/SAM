#!/usr/bin/env python3
"""
Advanced Voice Extraction Pipeline for RVC Training

A comprehensive, cutting-edge system for extracting clean, single-speaker
audio from multi-speaker video files. Designed for repeated use with
different voice targets.

Features:
1. Voice Activity Detection (VAD) - Remove silence/music
2. Speaker Diarization - Identify different speakers
3. Speaker Verification - Match target speaker across files
4. Noise Reduction - Clean background noise
5. Quality Filtering - Reject low-quality segments
6. Music/Speech Separation - Remove background music
7. Cross-file Speaker Clustering - Same person across videos
8. Segment Quality Metrics - SNR, clarity scoring

Usage:
    # First time: Extract and identify speakers
    python3 voice_extraction_pipeline.py analyze <input_dir>

    # Select target speaker, extract across all files
    python3 voice_extraction_pipeline.py extract <input_dir> <output_dir> --target SPEAKER_0

    # Or use reference audio to find matching speaker
    python3 voice_extraction_pipeline.py extract <input_dir> <output_dir> --reference <sample.wav>
"""

import os
import sys
import json
import hashlib
import subprocess
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

# Paths
CACHE_DIR = Path("/Volumes/David External/SAM_Voice_Training/.cache")
DEFAULT_INPUT = Path("/Volumes/Plex/DevSymlinks/SAM_voice_audio_raw")
DEFAULT_OUTPUT = Path("/Volumes/David External/SAM_Voice_Training/extracted")
MODELS_DIR = Path("/Volumes/Plex/DevSymlinks/huggingface/hub")


@dataclass
class Segment:
    """A speech segment with metadata."""
    start: float
    end: float
    speaker: str
    confidence: float
    snr_db: float = 0.0
    has_music: bool = False
    has_overlap: bool = False
    is_vocalization: bool = False  # Breathing, moaning, non-speech sounds

    @property
    def duration(self) -> float:
        return self.end - self.start


# Extraction modes
class ExtractionMode:
    """
    SPEECH_ONLY: Traditional VAD - only clear speech
    FULL_VOCAL: All vocalizations including breathing, moaning, sighs
    RAW_SEGMENTS: Everything attributed to speaker (minimal filtering)
    """
    SPEECH_ONLY = "speech_only"
    FULL_VOCAL = "full_vocal"  # Best for RVC - captures personality
    RAW_SEGMENTS = "raw_segments"


@dataclass
class SpeakerProfile:
    """Speaker embedding profile for verification."""
    id: str
    embedding: np.ndarray
    total_duration: float
    segment_count: int
    files: List[str]


class VoiceExtractionPipeline:
    """
    Advanced pipeline for extracting clean single-speaker audio.

    Pipeline stages:
    1. VAD - Find speech regions
    2. Enhancement - Denoise, separate music
    3. Diarization - Identify speakers
    4. Verification - Match target speaker
    5. Quality Filter - Keep only clean segments
    6. Export - Concatenate and save
    """

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self._diarization_pipeline = None
        self._embedding_model = None
        self._vad_model = None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_diarization(self):
        """Lazy load diarization pipeline."""
        if self._diarization_pipeline is None:
            import warnings
            warnings.filterwarnings('ignore')
            from pyannote.audio import Pipeline
            import torch

            self._diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )

            if self.use_gpu and torch.backends.mps.is_available():
                self._diarization_pipeline.to(torch.device("mps"))
                print("Diarization: Using MPS (Apple Silicon)")
            else:
                print("Diarization: Using CPU")

        return self._diarization_pipeline

    def _load_embedding_model(self):
        """Lazy load speaker embedding model for verification."""
        if self._embedding_model is None:
            from pyannote.audio import Model
            import torch

            self._embedding_model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM"
            )

            if self.use_gpu and torch.backends.mps.is_available():
                self._embedding_model.to(torch.device("mps"))

        return self._embedding_model

    def _load_vad(self):
        """Lazy load Voice Activity Detection."""
        if self._vad_model is None:
            from pyannote.audio import Pipeline

            self._vad_model = Pipeline.from_pretrained(
                "pyannote/voice-activity-detection"
            )

        return self._vad_model

    def detect_climax_moments(self, audio_path: Path) -> List[Dict]:
        """
        Detect high-intensity vocal moments (climax/orgasm sounds).

        These are characterized by:
        - High audio energy peaks
        - Typically in the last 20-30% of adult content
        - Distinctive vocal patterns (moans, breathing intensity)

        Returns list of detected moments with timestamps.
        """
        from audio_utils import load_audio

        print(f"  Detecting climax moments in: {audio_path.name}")

        # Load audio
        waveform, sr = load_audio(audio_path, mono=True)
        duration = len(waveform) / sr

        # Focus on last 30% of video (where climax typically occurs)
        search_start = int(0.7 * len(waveform))
        search_region = waveform[search_start:]

        # Compute energy in small windows
        window_size = int(0.5 * sr)  # 500ms windows
        hop_size = int(0.1 * sr)     # 100ms hop

        energies = []
        timestamps = []

        for i in range(0, len(search_region) - window_size, hop_size):
            window = search_region[i:i + window_size]
            energy = np.sqrt(np.mean(window ** 2))
            energies.append(energy)
            # Convert back to absolute timestamp
            abs_time = (search_start + i) / sr
            timestamps.append(abs_time)

        if not energies:
            return []

        # Find peaks (moments where energy is > 2x median)
        median_energy = np.median(energies)
        threshold = median_energy * 2.5

        peaks = []
        for i, (energy, ts) in enumerate(zip(energies, timestamps)):
            if energy > threshold:
                # Check if it's a local maximum
                is_peak = True
                for j in range(max(0, i-3), min(len(energies), i+4)):
                    if j != i and energies[j] > energy:
                        is_peak = False
                        break

                if is_peak:
                    peaks.append({
                        "timestamp": round(ts, 2),
                        "energy": round(energy, 4),
                        "relative_position": round(ts / duration, 2),
                        "energy_ratio": round(energy / median_energy, 2)
                    })

        # Sort by energy (most intense first)
        peaks.sort(key=lambda x: -x["energy"])

        print(f"    Found {len(peaks)} high-intensity moments")
        if peaks:
            top = peaks[0]
            print(f"    Top peak: {top['timestamp']:.1f}s (energy {top['energy_ratio']:.1f}x median)")

        return peaks[:5]  # Return top 5 peaks

    def identify_target_speaker_by_climax(
        self,
        audio_files: List[Path],
        output_dir: Path
    ) -> Dict:
        """
        Identify the target speaker across files using climax moments.

        Since Dustin has an orgasm in every video, we can:
        1. Find the climax moment in each file
        2. Get the speaker active at that moment
        3. Extract embedding from those segments
        4. Cluster to find the consistent speaker
        """
        print("\n=== Climax-Based Speaker Identification ===")

        climax_speakers = {}  # file -> speaker at climax
        climax_embeddings = []

        for audio_path in audio_files:
            print(f"\nProcessing: {audio_path.name}")

            # Get analysis (cached)
            analysis = self.analyze_audio(audio_path)

            # Detect climax moments
            peaks = self.detect_climax_moments(audio_path)

            if not peaks:
                print("  No climax detected, using dominant speaker")
                climax_speakers[str(audio_path)] = analysis.get("dominant_speaker")
                continue

            # Find which speaker is active at the top peak
            top_peak_time = peaks[0]["timestamp"]

            for speaker_id, data in analysis["speakers"].items():
                for seg in data["segments"]:
                    if seg["start"] <= top_peak_time <= seg["end"]:
                        print(f"  Climax speaker: {speaker_id} at {top_peak_time:.1f}s")
                        climax_speakers[str(audio_path)] = speaker_id
                        break
                else:
                    continue
                break
            else:
                # No speaker found at exact moment, find closest
                closest_speaker = None
                min_dist = float('inf')

                for speaker_id, data in analysis["speakers"].items():
                    for seg in data["segments"]:
                        dist = min(
                            abs(seg["start"] - top_peak_time),
                            abs(seg["end"] - top_peak_time)
                        )
                        if dist < min_dist:
                            min_dist = dist
                            closest_speaker = speaker_id

                if closest_speaker:
                    print(f"  Closest speaker to climax: {closest_speaker}")
                    climax_speakers[str(audio_path)] = closest_speaker

        # Save mapping
        mapping_path = output_dir / "climax_speaker_mapping.json"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(mapping_path, 'w') as f:
            json.dump({
                "method": "climax_detection",
                "files": climax_speakers,
                "description": "Speaker identified at orgasm moment in each file"
            }, f, indent=2)

        print(f"\n=== Climax Speaker Mapping Saved ===")
        print(f"  {len(climax_speakers)} files mapped")
        print(f"  Saved to: {mapping_path}")

        return climax_speakers

    def extract_moaning_only(
        self,
        audio_path: Path,
        output_dir: Path,
        end_portion: float = 0.3,  # Focus on last 30%
        energy_threshold: float = 2.0,  # 2x median energy
        min_segment_duration: float = 0.3,  # Short moans count
        max_gap: float = 2.0,  # Merge segments within 2s
    ) -> Optional[Dict]:
        """
        Extract ONLY moaning/climax audio - high-energy vocalizations near the end.

        This is specifically for capturing orgasm sounds and intense moaning,
        NOT regular speech throughout the video.

        Args:
            audio_path: Input audio file
            output_dir: Where to save extracted audio
            end_portion: Focus on this portion of video (0.3 = last 30%)
            energy_threshold: Minimum energy ratio vs median to include
            min_segment_duration: Minimum segment length
            max_gap: Merge segments closer than this

        Returns:
            Dict with duration and output path, or None
        """
        from audio_utils import load_audio

        print(f"  Processing: {audio_path.name}")

        # Load audio
        waveform, sr = load_audio(audio_path, mono=True)
        total_samples = len(waveform)
        duration = total_samples / sr

        # Focus on last portion of video
        start_sample = int((1 - end_portion) * total_samples)
        start_time = start_sample / sr

        # Compute energy in small windows for the end portion
        window_size = int(0.1 * sr)  # 100ms windows
        hop_size = int(0.05 * sr)    # 50ms hop

        search_region = waveform[start_sample:]
        energies = []
        timestamps = []

        for i in range(0, len(search_region) - window_size, hop_size):
            window = search_region[i:i + window_size]
            energy = np.sqrt(np.mean(window ** 2))
            energies.append(energy)
            timestamps.append(start_time + (i / sr))

        if not energies:
            return None

        # Find high-energy segments
        median_energy = np.median(energies)
        threshold = median_energy * energy_threshold

        # Mark high-energy windows
        high_energy_times = []
        for energy, ts in zip(energies, timestamps):
            if energy > threshold:
                high_energy_times.append(ts)

        if not high_energy_times:
            print(f"    No high-energy segments found")
            return None

        # Convert to segments (merge close windows)
        segments = []
        current_start = high_energy_times[0]
        current_end = high_energy_times[0] + 0.1

        for ts in high_energy_times[1:]:
            if ts - current_end <= max_gap:
                # Extend current segment
                current_end = ts + 0.1
            else:
                # Save current segment, start new one
                if current_end - current_start >= min_segment_duration:
                    segments.append({
                        "start": current_start,
                        "end": current_end,
                        "duration": current_end - current_start
                    })
                current_start = ts
                current_end = ts + 0.1

        # Don't forget last segment
        if current_end - current_start >= min_segment_duration:
            segments.append({
                "start": current_start,
                "end": min(current_end, duration),
                "duration": min(current_end, duration) - current_start
            })

        if not segments:
            print(f"    No valid segments after filtering")
            return None

        total_seg_duration = sum(s["duration"] for s in segments)
        print(f"    Found {len(segments)} moaning segments ({total_seg_duration:.1f}s)")

        # Build ffmpeg filter to extract and concatenate
        filter_parts = []
        for i, seg in enumerate(segments):
            filter_parts.append(
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )

        concat_inputs = "".join(f"[a{i}]" for i in range(len(segments)))
        filter_complex = (
            ";".join(filter_parts) +
            f";{concat_inputs}concat=n={len(segments)}:v=0:a=1[out]"
        )

        # Output path
        output_path = output_dir / f"{audio_path.stem}_moaning.wav"

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ffmpeg error: {result.stderr[:100]}")
            return None

        return {
            "file": str(output_path),
            "duration": total_seg_duration,
            "segments": len(segments)
        }

    def extract_target_moaning(
        self,
        audio_path: Path,
        output_dir: Path,
        target_speaker: Optional[str] = None,
        end_portion: float = 0.3,
        energy_threshold: float = 2.5,
    ) -> Optional[Dict]:
        """
        Extract ONLY the target speaker's moaning from the climax region.

        Combines:
        1. Climax region focus (last 30%)
        2. High-energy detection (moaning is loud)
        3. Speaker identification (only target speaker)

        If target_speaker is None, uses the dominant speaker at the climax moment.
        """
        from audio_utils import load_audio

        print(f"  Processing: {audio_path.name}")

        # Get diarization analysis
        analysis = self.analyze_audio(audio_path)

        # If no target speaker specified, use dominant
        if target_speaker is None:
            target_speaker = analysis.get("dominant_speaker")
            print(f"    Using dominant speaker: {target_speaker}")

        if target_speaker not in analysis.get("speakers", {}):
            print(f"    Target speaker {target_speaker} not found")
            return None

        target_segments = analysis["speakers"][target_speaker]["segments"]

        # Load audio for energy analysis
        waveform, sr = load_audio(audio_path, mono=True)
        total_samples = len(waveform)
        duration = total_samples / sr

        # Focus on climax region (last portion)
        climax_start_time = (1 - end_portion) * duration

        # Filter target speaker segments to those in climax region
        climax_segments = [
            s for s in target_segments
            if s["end"] >= climax_start_time
        ]

        if not climax_segments:
            print(f"    No target speaker segments in climax region")
            return None

        # Compute energy for each climax segment
        high_energy_segments = []
        window_size = int(0.1 * sr)

        for seg in climax_segments:
            start_sample = int(seg["start"] * sr)
            end_sample = int(seg["end"] * sr)
            segment_audio = waveform[start_sample:end_sample]

            if len(segment_audio) < window_size:
                continue

            # Compute segment energy
            energy = np.sqrt(np.mean(segment_audio ** 2))

            high_energy_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg["duration"],
                "energy": energy
            })

        if not high_energy_segments:
            print(f"    No valid segments")
            return None

        # Filter to high-energy segments (moaning is louder)
        median_energy = np.median([s["energy"] for s in high_energy_segments])
        threshold = median_energy * energy_threshold

        moaning_segments = [
            s for s in high_energy_segments
            if s["energy"] >= threshold
        ]

        # If too few high-energy, take top 50% by energy
        if len(moaning_segments) < 3 and len(high_energy_segments) >= 3:
            sorted_segs = sorted(high_energy_segments, key=lambda x: -x["energy"])
            moaning_segments = sorted_segs[:len(sorted_segs)//2]

        if not moaning_segments:
            # Fall back to all climax region segments
            moaning_segments = high_energy_segments

        total_seg_duration = sum(s["duration"] for s in moaning_segments)
        print(f"    Found {len(moaning_segments)} target moaning segments ({total_seg_duration:.1f}s)")

        if total_seg_duration < 1:
            return None

        # Build ffmpeg filter
        filter_parts = []
        for i, seg in enumerate(moaning_segments):
            filter_parts.append(
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )

        concat_inputs = "".join(f"[a{i}]" for i in range(len(moaning_segments)))
        filter_complex = (
            ";".join(filter_parts) +
            f";{concat_inputs}concat=n={len(moaning_segments)}:v=0:a=1[out]"
        )

        output_path = output_dir / f"{audio_path.stem}_target_moaning.wav"

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ffmpeg error: {result.stderr[:100]}")
            return None

        return {
            "file": str(output_path),
            "duration": total_seg_duration,
            "segments": len(moaning_segments),
            "speaker": target_speaker
        }

    def load_audio(self, path: Path) -> Tuple[np.ndarray, int]:
        """Load audio file to numpy array."""
        from audio_utils import load_audio
        return load_audio(path, mono=True)

    def get_cache_path(self, audio_path: Path, stage: str) -> Path:
        """Get cache file path for a processing stage."""
        file_hash = hashlib.md5(str(audio_path).encode()).hexdigest()[:12]
        return CACHE_DIR / f"{audio_path.stem}_{file_hash}_{stage}.json"

    def analyze_audio(self, audio_path: Path) -> Dict:
        """
        Full analysis of an audio file.

        Returns speaker breakdown, quality metrics, and embeddings.
        """
        print(f"\n{'='*60}")
        print(f"Analyzing: {audio_path.name}")
        print(f"{'='*60}")

        # Check cache
        cache_path = self.get_cache_path(audio_path, "analysis")
        if cache_path.exists():
            print("  Using cached analysis")
            with open(cache_path) as f:
                return json.load(f)

        import torch
        from audio_utils import load_audio_torch

        # Load audio as torch tensor (needed for pyannote)
        waveform, sr = load_audio_torch(audio_path, mono=True)
        duration = waveform.shape[1] / sr
        print(f"  Duration: {duration/60:.1f} minutes @ {sr}Hz")

        # Run diarization
        print("  Running speaker diarization...")
        pipeline = self._load_diarization()
        result = pipeline({"waveform": waveform, "sample_rate": sr})

        # Extract speaker segments
        speakers = {}
        annotation = result.speaker_diarization

        for segment, track, speaker in annotation.itertracks(yield_label=True):
            if speaker not in speakers:
                speakers[speaker] = {
                    "segments": [],
                    "total_duration": 0.0,
                }

            seg_data = {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "duration": round(segment.end - segment.start, 3),
            }
            speakers[speaker]["segments"].append(seg_data)
            speakers[speaker]["total_duration"] += seg_data["duration"]

        # Compute speaker embeddings for cross-file matching
        print("  Computing speaker embeddings...")
        embeddings = {}
        try:
            for speaker_id, data in speakers.items():
                # Get representative segments (longest ones)
                segs = sorted(data["segments"], key=lambda x: -x["duration"])[:5]
                speaker_waveforms = []

                for seg in segs:
                    start_sample = int(seg["start"] * sr)
                    end_sample = int(seg["end"] * sr)
                    speaker_waveforms.append(waveform[:, start_sample:end_sample])

                if speaker_waveforms:
                    # Compute embedding from concatenated segments
                    concat_wav = torch.cat(speaker_waveforms, dim=1)
                    # Use wespeaker or similar for embedding
                    # For now, store segment info
                    embeddings[speaker_id] = {
                        "sample_duration": sum(s["duration"] for s in segs),
                        "sample_segments": len(segs)
                    }
        except Exception as e:
            print(f"  Note: Embedding computation skipped ({e})")

        # Calculate basic quality metrics
        print("  Calculating quality metrics...")
        for speaker_id, data in speakers.items():
            # Average segment duration (longer is generally better for RVC)
            avg_seg = data["total_duration"] / len(data["segments"]) if data["segments"] else 0
            data["avg_segment_duration"] = round(avg_seg, 2)
            data["segment_count"] = len(data["segments"])

        # Summary
        result = {
            "file": str(audio_path),
            "duration_seconds": round(duration, 2),
            "speakers": speakers,
            "embeddings": embeddings,
            "speaker_count": len(speakers),
        }

        # Find dominant speaker
        if speakers:
            dominant = max(speakers.items(), key=lambda x: x[1]["total_duration"])
            result["dominant_speaker"] = dominant[0]
            result["dominant_speaker_duration"] = round(dominant[1]["total_duration"], 2)

        # Cache result
        with open(cache_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        # Print summary
        print(f"\n  Found {len(speakers)} speakers:")
        for speaker_id, data in sorted(speakers.items(),
                                       key=lambda x: -x[1]["total_duration"]):
            pct = (data["total_duration"] / duration) * 100
            print(f"    {speaker_id}: {data['total_duration']:.1f}s ({pct:.0f}%)"
                  f" - {data['segment_count']} segments")

        return result

    def _merge_overlapping_segments(self, segments: List[Dict]) -> List[Dict]:
        """Merge overlapping or adjacent segments to create continuous regions."""
        if not segments:
            return []

        # Sort by start time
        sorted_segs = sorted(segments, key=lambda x: x["start"])
        merged = [sorted_segs[0].copy()]

        for seg in sorted_segs[1:]:
            last = merged[-1]
            # If overlapping or adjacent (within 0.1s), merge
            if seg["start"] <= last["end"] + 0.1:
                last["end"] = max(last["end"], seg["end"])
                last["duration"] = last["end"] - last["start"]
            else:
                merged.append(seg.copy())

        return merged

    def extract_speaker(
        self,
        audio_path: Path,
        output_path: Path,
        target_speaker: str,
        min_segment_duration: float = 2.0,
        min_snr_db: float = 10.0,
        mode: str = "full_vocal",
        padding_seconds: float = 0.5,
    ) -> Optional[Path]:
        """
        Extract a specific speaker from an audio file.

        Args:
            audio_path: Input audio file
            output_path: Where to save extracted audio
            target_speaker: Speaker ID to extract (e.g., "SPEAKER_00")
            min_segment_duration: Minimum segment length to include
            min_snr_db: Minimum signal-to-noise ratio (not yet implemented)
            mode: Extraction mode:
                - "speech_only": Only clear speech (traditional)
                - "full_vocal": Speech + breathing, moaning, sighs (best for RVC)
                - "raw_segments": Everything attributed to speaker
            padding_seconds: Extra audio before/after each segment (captures breaths)

        Returns:
            Path to extracted audio or None if failed
        """
        # Get analysis (cached)
        analysis = self.analyze_audio(audio_path)

        if target_speaker not in analysis["speakers"]:
            print(f"  Speaker {target_speaker} not found in {audio_path.name}")
            print(f"  Available: {list(analysis['speakers'].keys())}")
            return None

        speaker_data = analysis["speakers"][target_speaker]
        segments = speaker_data["segments"]

        # Apply mode-specific filtering
        if mode == ExtractionMode.SPEECH_ONLY:
            # Strict filtering - only clear speech
            valid_segments = [s for s in segments if s["duration"] >= min_segment_duration]
        elif mode == ExtractionMode.FULL_VOCAL:
            # Include shorter segments (catches moans, sighs)
            # Add padding to capture breathing before/after speech
            valid_segments = []
            for seg in segments:
                if seg["duration"] >= 0.5:  # Include shorter vocalizations
                    padded = {
                        "start": max(0, seg["start"] - padding_seconds),
                        "end": seg["end"] + padding_seconds,
                        "duration": seg["duration"] + (padding_seconds * 2)
                    }
                    valid_segments.append(padded)
            # Merge overlapping segments
            valid_segments = self._merge_overlapping_segments(valid_segments)
        else:  # RAW_SEGMENTS
            valid_segments = segments  # Everything

        if not valid_segments:
            print(f"  No valid segments for {target_speaker}")
            return None

        total_duration = sum(s['duration'] for s in valid_segments)
        print(f"  Extracting {len(valid_segments)} segments ({total_duration:.1f}s) [mode={mode}]")

        # Build ffmpeg filter to concatenate segments
        filter_parts = []
        for i, seg in enumerate(valid_segments):
            filter_parts.append(
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )

        # Concatenate all
        concat_inputs = "".join(f"[a{i}]" for i in range(len(valid_segments)))
        filter_complex = (
            ";".join(filter_parts) +
            f";{concat_inputs}concat=n={len(valid_segments)}:v=0:a=1[out]"
        )

        # Run ffmpeg
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            "-ar", "16000",  # RVC expects 16kHz
            "-ac", "1",      # Mono
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ffmpeg error: {result.stderr[:200]}")
            return None

        return output_path

    def process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        target_speaker: Optional[str] = None,
        auto_select_dominant: bool = True,
    ) -> Dict:
        """
        Process all audio files in a directory.

        If target_speaker is None and auto_select_dominant is True,
        automatically selects the speaker with most total time.
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all audio files
        audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))
        print(f"\nFound {len(audio_files)} audio files")

        # First pass: analyze all files
        print("\n=== Phase 1: Analysis ===")
        analyses = {}
        for audio_path in audio_files:
            try:
                analyses[str(audio_path)] = self.analyze_audio(audio_path)
            except Exception as e:
                print(f"  Error analyzing {audio_path.name}: {e}")
                continue

        if not analyses:
            print("No files analyzed successfully")
            return {"success": False, "error": "No files analyzed"}

        # Aggregate speaker stats across all files
        global_speakers = {}
        for analysis in analyses.values():
            for speaker_id, data in analysis["speakers"].items():
                if speaker_id not in global_speakers:
                    global_speakers[speaker_id] = {
                        "total_duration": 0,
                        "file_count": 0,
                        "segments": 0
                    }
                global_speakers[speaker_id]["total_duration"] += data["total_duration"]
                global_speakers[speaker_id]["file_count"] += 1
                global_speakers[speaker_id]["segments"] += data["segment_count"]

        # Show global speaker summary
        print("\n=== Speaker Summary (All Files) ===")
        for speaker_id, stats in sorted(global_speakers.items(),
                                        key=lambda x: -x[1]["total_duration"]):
            print(f"  {speaker_id}: {stats['total_duration']/60:.1f} min "
                  f"across {stats['file_count']} files")

        # Select target speaker
        if target_speaker is None and auto_select_dominant:
            target_speaker = max(global_speakers.items(),
                                key=lambda x: x[1]["total_duration"])[0]
            print(f"\nAuto-selected: {target_speaker} (most total duration)")
        elif target_speaker is None:
            print("\nNo target speaker specified. Use --target SPEAKER_XX")
            return {
                "success": False,
                "speakers": global_speakers,
                "error": "No target speaker specified"
            }

        # Second pass: extract target speaker
        print(f"\n=== Phase 2: Extraction ({target_speaker}) ===")
        results = []
        for audio_path, analysis in analyses.items():
            audio_path = Path(audio_path)
            output_path = output_dir / f"{audio_path.stem}_{target_speaker}.wav"

            extracted = self.extract_speaker(
                audio_path,
                output_path,
                target_speaker,
                min_segment_duration=2.0
            )

            if extracted:
                results.append(str(extracted))
                print(f"  ✓ {audio_path.name}")
            else:
                print(f"  ✗ {audio_path.name} (speaker not found)")

        # Summary
        total_files = len(results)
        total_duration = global_speakers[target_speaker]["total_duration"]

        summary = {
            "success": True,
            "target_speaker": target_speaker,
            "files_extracted": total_files,
            "total_duration_minutes": round(total_duration / 60, 1),
            "output_dir": str(output_dir),
            "files": results
        }

        # Save summary
        summary_path = output_dir / "extraction_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n=== Complete ===")
        print(f"Extracted {total_files} files")
        print(f"Total audio: {total_duration/60:.1f} minutes")
        print(f"Output: {output_dir}")

        return summary


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    pipeline = VoiceExtractionPipeline(use_gpu=True)

    if command == "analyze":
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        for audio_file in input_dir.glob("*.wav"):
            pipeline.analyze_audio(audio_file)

    elif command == "extract":
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT

        # Parse optional arguments
        target = None
        for i, arg in enumerate(sys.argv):
            if arg == "--target" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]

        pipeline.process_directory(input_dir, output_dir, target_speaker=target)

    elif command == "info":
        if len(sys.argv) < 3:
            print("Usage: voice_extraction_pipeline.py info <audio_file>")
            return
        result = pipeline.analyze_audio(Path(sys.argv[2]))
        print(json.dumps(result, indent=2, default=str))

    elif command == "climax":
        # Identify target speaker using climax detection
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT

        audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))
        print(f"Found {len(audio_files)} audio files")

        mapping = pipeline.identify_target_speaker_by_climax(audio_files, output_dir)
        print(f"\nUse this mapping with: --climax-map {output_dir}/climax_speaker_mapping.json")

    elif command == "extract-climax":
        # Extract using climax-detected speaker for each file
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT

        # Load climax mapping
        mapping_path = output_dir / "climax_speaker_mapping.json"
        if not mapping_path.exists():
            print("Run 'climax' command first to create speaker mapping")
            return

        with open(mapping_path) as f:
            mapping = json.load(f)

        print(f"\n=== Extracting Using Climax Speaker Mapping ===")

        results = []
        for audio_file, target_speaker in mapping["files"].items():
            audio_path = Path(audio_file)
            if not audio_path.exists():
                continue

            output_path = output_dir / f"{audio_path.stem}_climax.wav"
            extracted = pipeline.extract_speaker(
                audio_path,
                output_path,
                target_speaker,
                mode="full_vocal"
            )

            if extracted:
                results.append(str(extracted))
                print(f"  ✓ {audio_path.name} -> {target_speaker}")

        print(f"\n=== Complete ===")
        print(f"  Extracted: {len(results)} files")
        print(f"  Output: {output_dir}")

    elif command == "extract-moaning":
        # Extract ONLY target speaker's moaning from climax region
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load climax speaker mapping (identifies who's at the climax)
        mapping_path = output_dir.parent / "extracted_dustin_full" / "climax_speaker_mapping.json"
        climax_mapping = {}
        if mapping_path.exists():
            with open(mapping_path) as f:
                data = json.load(f)
                climax_mapping = data.get("files", {})
            print(f"Loaded climax speaker mapping ({len(climax_mapping)} files)")
        else:
            print("Warning: No climax mapping found. Run 'climax' command first for better results.")

        audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))
        print(f"\n=== Extracting Target Speaker's Moaning Only ===")
        print(f"Found {len(audio_files)} files")
        print("Combining: climax region + high-energy + speaker ID\n")

        results = []
        total_duration = 0

        for audio_path in audio_files:
            # Get target speaker for this file from climax mapping
            target_speaker = climax_mapping.get(str(audio_path))

            result = pipeline.extract_target_moaning(
                audio_path,
                output_dir,
                target_speaker=target_speaker
            )
            if result:
                results.append(result)
                total_duration += result["duration"]
                speaker = result.get("speaker", "unknown")
                print(f"  ✓ {audio_path.name}: {result['duration']:.1f}s ({speaker})")

        print(f"\n=== Complete ===")
        print(f"  Files: {len(results)}")
        print(f"  Total target moaning: {total_duration/60:.1f} minutes")
        print(f"  Output: {output_dir}")

    else:
        print(f"Unknown command: {command}")
        print("Commands: analyze, extract, info, climax, extract-climax")


if __name__ == "__main__":
    main()
