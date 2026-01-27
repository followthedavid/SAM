#!/usr/bin/env python3
"""
Speaker Diarization for Voice Training

Separates audio by speaker to extract only Dustin Steele's voice.
Uses pyannote.audio for speaker detection.

Usage:
    python3 speaker_diarization.py process <audio_dir> <output_dir>
    python3 speaker_diarization.py info <audio_file>
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

# Diarization venv
DIARIZATION_VENV = Path("/Volumes/Plex/DevSymlinks/venvs/SAM_voice_venv_diarization")
HUGGINGFACE_TOKEN = os.environ.get("HF_TOKEN", "")

# Output paths
DEFAULT_INPUT = Path("/Volumes/Plex/DevSymlinks/SAM_voice_audio_raw")
DEFAULT_OUTPUT = Path("/Volumes/David External/SAM_Voice_Training/diarized")


def check_dependencies():
    """Check if pyannote is available."""
    try:
        from pyannote.audio import Pipeline
        return True
    except ImportError:
        print("pyannote.audio not installed. Install with:")
        print(f"  source {DIARIZATION_VENV}/bin/activate")
        print("  pip install pyannote.audio torch soundfile")
        return False


def load_pipeline():
    """Load the diarization pipeline."""
    from pyannote.audio import Pipeline
    import torch

    # Use MPS on Apple Silicon if available
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")

    # Try loading with local cache first
    cache_dir = Path("/Volumes/Plex/DevSymlinks/huggingface/hub")

    try:
        # pyannote 4.0+ uses 'token' instead of 'use_auth_token'
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            cache_dir=str(cache_dir)
        )
        pipeline.to(device)
        print("Loaded pyannote speaker-diarization-3.1")
        return pipeline
    except Exception as e:
        print(f"Note: Could not load 3.1 ({e})")

        # Try without token (might work if model is cached)
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )
            pipeline.to(device)
            print("Loaded pyannote speaker-diarization-3.1 (cached)")
            return pipeline
        except Exception as e2:
            print(f"Error loading pipeline: {e2}")
            print("\nYou may need to:")
            print("  1. Accept model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1")
            print("  2. Set HF_TOKEN environment variable")
            print("  3. Or run: huggingface-cli login")
            return None


def load_audio(audio_path: Path) -> Dict:
    """Load audio file for pyannote (returns torch tensor)."""
    from audio_utils import load_audio_torch

    waveform, sample_rate = load_audio_torch(audio_path, mono=True)

    return {
        "waveform": waveform,
        "sample_rate": sample_rate
    }


def process_audio(audio_path: Path, pipeline) -> Dict:
    """Run diarization on an audio file."""
    print(f"\nProcessing: {audio_path.name}")

    # Pre-load audio (uses soundfile backend for better macOS compatibility)
    audio_data = load_audio(audio_path)
    print(f"  Loaded: {audio_data['waveform'].shape[1]/audio_data['sample_rate']:.1f}s @ {audio_data['sample_rate']}Hz")

    # Run diarization with pre-loaded audio
    diarization = pipeline(audio_data)

    # Extract speaker segments
    speakers = {}
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        if speaker not in speakers:
            speakers[speaker] = []
        speakers[speaker].append({
            "start": turn.start,
            "end": turn.end,
            "duration": turn.end - turn.start
        })

    # Calculate total duration per speaker
    summary = {}
    for speaker, segments in speakers.items():
        total_duration = sum(s["duration"] for s in segments)
        summary[speaker] = {
            "total_duration": total_duration,
            "segment_count": len(segments),
            "segments": segments
        }

    return summary


def extract_speaker_audio(
    audio_path: Path,
    segments: List[Dict],
    output_path: Path,
    min_segment_duration: float = 2.0
):
    """Extract audio segments for a specific speaker using ffmpeg."""

    # Filter short segments
    valid_segments = [s for s in segments if s["duration"] >= min_segment_duration]

    if not valid_segments:
        print(f"  No segments >= {min_segment_duration}s")
        return None

    # Create a filter complex to concat all segments
    filter_parts = []
    for i, seg in enumerate(valid_segments):
        # For each segment, create a trim filter
        filter_parts.append(
            f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},asetpts=PTS-STARTPTS[a{i}]"
        )

    # Concat all segments
    concat_inputs = "".join(f"[a{i}]" for i in range(len(valid_segments)))
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(valid_segments)}:v=0:a=1[out]"

    # Run ffmpeg
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
        print(f"  ffmpeg error: {result.stderr[:200]}")
        return None

    return output_path


def identify_main_speaker(summary: Dict) -> str:
    """Identify which speaker is likely the main voice (longest total duration)."""
    main_speaker = max(summary.keys(), key=lambda s: summary[s]["total_duration"])
    return main_speaker


def process_directory(input_dir: Path, output_dir: Path):
    """Process all audio files in a directory."""

    if not check_dependencies():
        return

    pipeline = load_pipeline()
    if not pipeline:
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find audio files
    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))
    print(f"Found {len(audio_files)} audio files")

    results = {}

    for audio_path in audio_files:
        try:
            # Diarize
            summary = process_audio(audio_path, pipeline)

            if not summary:
                print(f"  No speakers detected")
                continue

            # Show speaker breakdown
            print(f"  Found {len(summary)} speakers:")
            for speaker, data in sorted(summary.items(),
                                       key=lambda x: -x[1]["total_duration"]):
                print(f"    {speaker}: {data['total_duration']:.1f}s ({data['segment_count']} segments)")

            # Extract main speaker (longest)
            main_speaker = identify_main_speaker(summary)
            main_data = summary[main_speaker]

            print(f"  Main speaker: {main_speaker} ({main_data['total_duration']:.1f}s)")

            # Extract to output
            output_path = output_dir / f"{audio_path.stem}_main.wav"
            extracted = extract_speaker_audio(
                audio_path,
                main_data["segments"],
                output_path,
                min_segment_duration=2.0
            )

            if extracted:
                print(f"  Extracted to: {extracted}")
                results[audio_path.name] = {
                    "main_speaker": main_speaker,
                    "duration": main_data["total_duration"],
                    "output": str(extracted)
                }

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Save summary
    summary_path = output_dir / "diarization_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")

    # Total stats
    total_extracted = sum(r["duration"] for r in results.values())
    print(f"\n=== Complete ===")
    print(f"Files processed: {len(results)}/{len(audio_files)}")
    print(f"Total extracted audio: {total_extracted/60:.1f} minutes")


def show_info(audio_path: Path):
    """Show diarization info for a single file."""
    if not check_dependencies():
        return

    pipeline = load_pipeline()
    if not pipeline:
        return

    summary = process_audio(audio_path, pipeline)

    print(f"\n=== Speaker Analysis: {audio_path.name} ===")
    for speaker, data in sorted(summary.items(),
                               key=lambda x: -x[1]["total_duration"]):
        print(f"\n{speaker}:")
        print(f"  Total: {data['total_duration']:.1f}s")
        print(f"  Segments: {data['segment_count']}")
        print("  First 5 segments:")
        for seg in data["segments"][:5]:
            print(f"    {seg['start']:.1f}s - {seg['end']:.1f}s ({seg['duration']:.1f}s)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nDefaults:")
        print(f"  Input:  {DEFAULT_INPUT}")
        print(f"  Output: {DEFAULT_OUTPUT}")
        return

    command = sys.argv[1]

    if command == "process":
        input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT
        process_directory(input_dir, output_dir)

    elif command == "info":
        if len(sys.argv) < 3:
            print("Usage: speaker_diarization.py info <audio_file>")
            return
        show_info(Path(sys.argv[2]))

    else:
        print(f"Unknown command: {command}")
        print("Use 'process' or 'info'")


if __name__ == "__main__":
    main()
