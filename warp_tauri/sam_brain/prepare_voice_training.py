#!/usr/bin/env python3
"""
Prepare Dustin Steele voice training data from video files.

Steps:
1. Extract audio from videos using ffmpeg
2. Convert to 16kHz mono WAV (RVC standard)
3. Split into segments (optional, RVC can handle long files)
4. Output to training directory
"""

import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Configuration
SOURCE_DIR = Path("/Volumes/David External/SAM_Voice_Training")
OUTPUT_DIR = Path("/Volumes/David External/SAM_Voice_Training/extracted_audio")
SAMPLE_RATE = 16000  # RVC standard

def extract_audio(video_path: Path) -> Path:
    """Extract audio from a video file."""
    output_path = OUTPUT_DIR / f"{video_path.stem}.wav"

    if output_path.exists():
        print(f"  Skipping {video_path.name} (already extracted)")
        return output_path

    print(f"  Extracting: {video_path.name}")

    try:
        # Extract audio, convert to 16kHz mono WAV
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", str(SAMPLE_RATE),  # Sample rate
            "-ac", "1",  # Mono
            str(output_path)
        ], capture_output=True, check=True)

        return output_path
    except subprocess.CalledProcessError as e:
        print(f"  Error extracting {video_path.name}: {e}")
        return None
    except FileNotFoundError:
        print("  Error: ffmpeg not found. Install with: brew install ffmpeg")
        return None


def main():
    """Main extraction pipeline."""
    print("=" * 60)
    print("Dustin Steele Voice Training Data Preparation")
    print("=" * 60)

    # Check source directory
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find video files
    video_extensions = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
    videos = [f for f in SOURCE_DIR.iterdir()
              if f.suffix.lower() in video_extensions and not f.name.startswith(".")]

    print(f"\nFound {len(videos)} video files")
    print(f"Output directory: {OUTPUT_DIR}\n")

    # Extract audio from each video
    extracted = []
    for video in sorted(videos):
        result = extract_audio(video)
        if result:
            extracted.append(result)

    print(f"\n{'=' * 60}")
    print(f"Extraction complete!")
    print(f"  Videos processed: {len(videos)}")
    print(f"  Audio files created: {len(extracted)}")
    print(f"  Output directory: {OUTPUT_DIR}")

    # Calculate total audio duration
    total_duration = 0
    for audio_file in extracted:
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ], capture_output=True, text=True)
            total_duration += float(result.stdout.strip())
        except:
            pass

    print(f"  Total audio duration: {total_duration / 60:.1f} minutes")
    print(f"\nNext step: Run RVC training with this audio")
    print(f"  cd ~/ReverseLab/SAM/warp_tauri/sam_brain")
    print(f"  python3 voice_trainer.py train '{OUTPUT_DIR}' --name dustin_steele")


if __name__ == "__main__":
    main()
