# Voice Extraction Pipeline Documentation

## Overview

Advanced voice extraction system for RVC voice cloning. Designed to extract clean, single-speaker audio from multi-speaker video content.

## Features

1. **Speaker Diarization** - Identifies different speakers using pyannote.audio 4.0
2. **Climax Detection** - Uses audio energy analysis to find high-intensity vocal moments
3. **Cross-File Speaker ID** - Identifies same person across multiple files using climax moments
4. **Full Vocal Mode** - Captures breathing, moaning, sighs (not just speech)
5. **Quality Filtering** - Removes low-quality segments
6. **Caching** - Analyses are cached for fast re-runs

## Requirements

```bash
# Python virtual environment with dependencies
source /Volumes/Plex/DevSymlinks/venvs/SAM_voice_venv_diarization/bin/activate

# Required packages (already installed):
# - pyannote.audio >= 4.0.3
# - torch
# - torchaudio
# - numpy
```

## Quick Start

### 1. Basic Analysis
```bash
# Analyze a single file
python3 voice_extraction_pipeline.py info /path/to/audio.wav

# Analyze all files in a directory
python3 voice_extraction_pipeline.py analyze /path/to/audio/dir
```

### 2. Standard Extraction (Dominant Speaker)
```bash
# Auto-selects speaker with most total time across all files
python3 voice_extraction_pipeline.py extract \
    /path/to/input/dir \
    /path/to/output/dir
```

### 3. Climax-Based Extraction (Recommended for Adult Content)
```bash
# Step 1: Run climax detection to identify target speaker
python3 voice_extraction_pipeline.py climax \
    /path/to/input/dir \
    /path/to/output/dir

# Step 2: Extract using the climax speaker mapping
python3 voice_extraction_pipeline.py extract-climax \
    /path/to/input/dir \
    /path/to/output/dir
```

## Extraction Modes

### `speech_only` (Traditional)
- Only clear speech segments
- Minimum 2 second duration
- Good for: Narration, interviews

### `full_vocal` (Default, Best for RVC)
- Speech + breathing, moaning, sighs
- Minimum 0.5 second duration
- 0.5s padding around segments
- Merges adjacent segments
- Good for: Voice cloning, personality capture

### `raw_segments`
- Everything attributed to speaker
- No filtering
- Good for: Maximum data extraction

## How Climax Detection Works

Adult content typically has a climax moment with:
1. High audio energy peaks
2. Located in last 20-30% of video
3. Distinctive vocal patterns

The algorithm:
1. Focuses on last 30% of audio
2. Computes energy in 500ms windows
3. Finds peaks > 2.5x median energy
4. Maps peaks to speaker segments
5. Builds per-file speaker mapping

This allows cross-file speaker identification by finding the same person's climax vocalizations.

## Directory Structure

```
/Volumes/David External/SAM_Voice_Training/
├── .cache/                          # Cached analyses
│   └── *_analysis.json             # Per-file speaker analysis
├── extracted_dustin_full/           # Extracted audio output
│   ├── *_climax.wav                # Climax-extracted files
│   ├── climax_speaker_mapping.json # Speaker-to-file mapping
│   └── extraction_summary.json     # Processing summary
└── raw/                             # Input audio files
```

## Cache Format

Analysis cache files contain:
```json
{
  "file": "/path/to/audio.wav",
  "duration_seconds": 603.56,
  "speakers": {
    "SPEAKER_00": {
      "segments": [{"start": 0.5, "end": 2.3, "duration": 1.8}, ...],
      "total_duration": 53.3,
      "segment_count": 28
    }
  },
  "dominant_speaker": "SPEAKER_02",
  "dominant_speaker_duration": 146.19
}
```

## Resource Considerations

- **Memory**: Diarization uses ~500MB-1GB per file on MPS
- **CPU**: Uses Apple Silicon MPS when available
- **Time**: ~1-2 minutes per 10-minute file
- **Storage**: Cache files ~20-100KB each

For 8GB RAM systems:
- Process files sequentially (default)
- Close other apps during processing
- Expect some swap usage on longer files

## Workflow for New Performer

1. **Collect source videos** in a directory
2. **Extract audio** from videos (ffmpeg)
3. **Run analysis**: `python3 voice_extraction_pipeline.py analyze /input/dir`
4. **Run climax detection**: `python3 voice_extraction_pipeline.py climax /input/dir /output/dir`
5. **Review mapping**: Check `climax_speaker_mapping.json`
6. **Extract audio**: `python3 voice_extraction_pipeline.py extract-climax /input/dir /output/dir`
7. **Train RVC**: Use extracted audio for voice model training

## Troubleshooting

### "No climax detected"
- File may not have high-intensity moments
- Falls back to dominant speaker

### Memory issues / slow processing
- Close other applications
- Process fewer files at a time
- Consider using CPU instead of MPS

### "Speaker not found at climax"
- Climax moment may be in non-speech segment
- Algorithm finds closest speaker within 5 seconds

## API Reference

```python
from voice_extraction_pipeline import VoiceExtractionPipeline

pipeline = VoiceExtractionPipeline(use_gpu=True)

# Analyze file
analysis = pipeline.analyze_audio(Path("audio.wav"))

# Detect climax moments
peaks = pipeline.detect_climax_moments(Path("audio.wav"))

# Extract speaker
pipeline.extract_speaker(
    audio_path=Path("audio.wav"),
    output_path=Path("output.wav"),
    target_speaker="SPEAKER_02",
    mode="full_vocal",
    padding_seconds=0.5
)

# Process directory
pipeline.process_directory(
    input_dir=Path("/input"),
    output_dir=Path("/output"),
    target_speaker=None,  # Auto-select dominant
    auto_select_dominant=True
)
```

## Future Enhancements

- [ ] Speaker embedding clustering across files
- [ ] Reference audio matching
- [ ] Music/speech separation
- [ ] SNR-based quality filtering
- [ ] Parallel processing for multi-core
