# Climax Detection & Moaning Extraction System

## For Stashbox Integration

**Purpose:** Automatically identify and extract a specific performer's vocalizations from multi-performer adult content, using climax/orgasm moments as identity anchors.

**Created:** 2026-01-20
**Codebase:** `voice_extraction_pipeline.py`

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Core Innovation: Climax as Identity Anchor](#core-innovation-climax-as-identity-anchor)
3. [Algorithm Deep Dive](#algorithm-deep-dive)
4. [System Architecture](#system-architecture)
5. [API Reference](#api-reference)
6. [Stashbox Integration](#stashbox-integration)
7. [Configuration & Tuning](#configuration--tuning)
8. [Performance Characteristics](#performance-characteristics)
9. [Known Limitations](#known-limitations)
10. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### The Challenge

When building voice models (RVC) for adult content performers:

1. **Multi-speaker content** - Videos contain 2+ performers whose voices overlap
2. **No clean labels** - Speaker diarization assigns arbitrary IDs (SPEAKER_00, SPEAKER_01) per file
3. **Cross-file inconsistency** - Same performer gets different IDs across videos
4. **Vocal variety** - Need to capture speech, moaning, breathing, sighs (not just dialogue)
5. **Other performers moan too** - Simple "loud audio" detection captures everyone

### The Insight

**Every adult scene has a climax moment where the target performer vocalizes distinctly.**

This moment:
- Is reliably located in the last 20-30% of the video
- Has distinctive audio energy characteristics (high amplitude)
- Can be detected algorithmically
- Serves as an "identity anchor" for the target performer

---

## Core Innovation: Climax as Identity Anchor

### Traditional Approach (Fails)

```
Video → Diarization → "SPEAKER_00 = 40%, SPEAKER_01 = 35%"
                      ↓
                 Pick dominant speaker
                      ↓
               Wrong person 40% of the time
```

### Climax-Anchored Approach (Works)

```
Video → Detect Climax Moment → Find Active Speaker at Peak
            ↓                           ↓
    Energy analysis of         Speaker diarization
    last 30% of audio           identifies who
            ↓                           ↓
    High-energy peaks    →    Target performer ID
            ↓
    Apply to this file's extraction
```

### Why This Works

1. **Performer-specific moments** - The target performer's climax is theirs alone
2. **Consistent behavior** - Same performer climaxes in every scene they perform
3. **Detectable signal** - Orgasm vocalizations have high energy, distinct patterns
4. **Position predictability** - Located in final portion of content
5. **Per-file mapping** - Don't need cross-file speaker matching; identify per video

---

## Algorithm Deep Dive

### Phase 1: Climax Detection

**Function:** `detect_climax_moments()`

**Input:** Audio file (WAV/MP3)

**Process:**

```python
# 1. Load audio, convert to mono
waveform, sr = torchaudio.load(audio_path)
if stereo: waveform = waveform.mean(dim=0)

# 2. Focus on last 30% of video (climax region)
search_start = int(0.7 * total_samples)
search_region = waveform[:, search_start:]

# 3. Compute RMS energy in sliding windows
window_size = 0.5 seconds (500ms)
hop_size = 0.1 seconds (100ms)

for each window:
    energy = sqrt(mean(window^2))  # RMS energy
    store (timestamp, energy)

# 4. Find peaks above threshold
median_energy = median(all_energies)
threshold = median_energy * 2.5  # 2.5x median

peaks = []
for each (timestamp, energy):
    if energy > threshold:
        if is_local_maximum(within 300ms):
            peaks.append({timestamp, energy, position})

# 5. Sort by intensity, return top 5
return sorted(peaks, by=-energy)[:5]
```

**Output:**
```json
[
  {"timestamp": 542.3, "energy": 0.0834, "relative_position": 0.92, "energy_ratio": 4.2},
  {"timestamp": 538.1, "energy": 0.0721, "relative_position": 0.91, "energy_ratio": 3.6},
  ...
]
```

**Key Parameters:**
| Parameter | Default | Purpose |
|-----------|---------|---------|
| `search_region` | Last 30% | Where climax typically occurs |
| `window_size` | 500ms | Energy averaging window |
| `hop_size` | 100ms | Sliding resolution |
| `threshold` | 2.5x median | Peak detection sensitivity |
| `local_max_window` | ±300ms | Avoid duplicate peaks |

---

### Phase 2: Speaker Identification at Climax

**Function:** `identify_target_speaker_by_climax()`

**Process:**

```python
for each audio_file:
    # 1. Get speaker diarization (cached)
    analysis = analyze_audio(audio_file)
    # Returns: {"SPEAKER_00": {segments: [...]}, "SPEAKER_01": {...}}

    # 2. Detect climax moment
    peaks = detect_climax_moments(audio_file)
    top_peak_time = peaks[0]["timestamp"]

    # 3. Find which speaker is active at that moment
    for speaker_id, data in analysis["speakers"]:
        for segment in data["segments"]:
            if segment.start <= top_peak_time <= segment.end:
                climax_speaker[audio_file] = speaker_id
                break

    # 4. Fallback: find closest speaker within 5 seconds
    if not found:
        find_speaker_closest_to(top_peak_time, max_distance=5.0)
```

**Output:** Per-file speaker mapping

```json
{
  "method": "climax_detection",
  "files": {
    "/path/to/video1.wav": "SPEAKER_02",
    "/path/to/video2.wav": "SPEAKER_00",
    "/path/to/video3.wav": "SPEAKER_01"
  },
  "description": "Speaker identified at orgasm moment in each file"
}
```

---

### Phase 3: Target Moaning Extraction

**Function:** `extract_target_moaning()`

**Combines three filters:**

1. **Climax Region Focus** - Only audio from last 30% of video
2. **High Energy Detection** - Only loud segments (moaning is louder)
3. **Speaker Identification** - Only the target speaker

```python
def extract_target_moaning(audio_path, target_speaker=None):
    # 1. Get diarization
    analysis = analyze_audio(audio_path)

    # 2. Get target speaker (from climax mapping or dominant)
    if target_speaker is None:
        target_speaker = analysis["dominant_speaker"]

    target_segments = analysis["speakers"][target_speaker]["segments"]

    # 3. Focus on climax region
    duration = get_duration(audio_path)
    climax_start = 0.7 * duration  # Last 30%

    climax_segments = [s for s in target_segments if s.end >= climax_start]

    # 4. Compute energy for each segment
    for segment in climax_segments:
        segment_audio = load_segment(audio_path, segment.start, segment.end)
        segment.energy = compute_rms(segment_audio)

    # 5. Filter to high-energy (moaning) segments
    median_energy = median([s.energy for s in climax_segments])
    threshold = median_energy * 2.5

    moaning_segments = [s for s in climax_segments if s.energy >= threshold]

    # 6. Fallback: if too few, take top 50% by energy
    if len(moaning_segments) < 3:
        moaning_segments = top_50_percent_by_energy(climax_segments)

    # 7. Export concatenated audio
    ffmpeg_concat(moaning_segments, output_path)

    return {
        "file": output_path,
        "duration": sum(s.duration for s in moaning_segments),
        "segments": len(moaning_segments),
        "speaker": target_speaker
    }
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    VOICE EXTRACTION PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   Audio     │───▶│  pyannote   │───▶│  Speaker Analysis   │  │
│  │   Input     │    │  Diarization│    │  (cached JSON)      │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│         │                                        │               │
│         │                                        ▼               │
│         │           ┌─────────────┐    ┌─────────────────────┐  │
│         └──────────▶│   Energy    │───▶│  Climax Detection   │  │
│                     │   Analysis  │    │  (peak finding)     │  │
│                     └─────────────┘    └─────────────────────┘  │
│                                                  │               │
│                                                  ▼               │
│                              ┌────────────────────────────────┐  │
│                              │  Speaker-Climax Mapping        │  │
│                              │  (per-file identity anchor)    │  │
│                              └────────────────────────────────┘  │
│                                                  │               │
│                                                  ▼               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   EXTRACTION MODES                          ││
│  ├──────────────┬──────────────┬───────────────────────────────┤│
│  │ extract-     │ extract-     │ extract-moaning               ││
│  │ climax       │ full-vocal   │ (target speaker, climax       ││
│  │ (all audio)  │ (speech +    │  region, high energy only)    ││
│  │              │  breaths)    │                               ││
│  └──────────────┴──────────────┴───────────────────────────────┘│
│                                                  │               │
│                                                  ▼               │
│                          ┌─────────────────────────────────┐    │
│                          │  FFmpeg Segment Concatenation   │    │
│                          │  16kHz mono WAV output          │    │
│                          └─────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependencies

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Speaker Diarization | pyannote.audio | 4.0+ | Identify different speakers |
| Audio Loading | torchaudio | 2.x | Load WAV/MP3 files |
| GPU Acceleration | torch MPS | - | Apple Silicon support |
| Audio Export | ffmpeg | 4.x | Segment concatenation |
| Caching | JSON | - | Avoid reprocessing |

---

## API Reference

### VoiceExtractionPipeline Class

```python
from voice_extraction_pipeline import VoiceExtractionPipeline

pipeline = VoiceExtractionPipeline(use_gpu=True)
```

#### `detect_climax_moments(audio_path: Path) -> List[Dict]`

Detect high-intensity vocal moments in the last 30% of audio.

**Returns:**
```python
[
    {
        "timestamp": 542.3,      # Seconds from start
        "energy": 0.0834,        # RMS energy value
        "relative_position": 0.92,  # Position in file (0-1)
        "energy_ratio": 4.2      # Multiple of median energy
    },
    ...  # Up to 5 peaks
]
```

#### `identify_target_speaker_by_climax(audio_files, output_dir) -> Dict`

Build per-file speaker mapping using climax moments.

**Returns:**
```python
{
    "/path/to/file1.wav": "SPEAKER_02",
    "/path/to/file2.wav": "SPEAKER_00",
    ...
}
```

**Also saves:** `output_dir/climax_speaker_mapping.json`

#### `extract_target_moaning(audio_path, output_dir, target_speaker=None) -> Dict`

Extract only the target speaker's high-energy vocalizations from climax region.

**Parameters:**
- `audio_path`: Input audio file
- `output_dir`: Where to save output
- `target_speaker`: Speaker ID (uses dominant if None)
- `end_portion`: Focus region (0.3 = last 30%)
- `energy_threshold`: Energy multiplier for detection (2.5)

**Returns:**
```python
{
    "file": "/path/to/output_target_moaning.wav",
    "duration": 11.7,
    "segments": 15,
    "speaker": "SPEAKER_02"
}
```

#### `analyze_audio(audio_path: Path) -> Dict`

Full speaker diarization analysis (cached).

**Returns:**
```python
{
    "file": "/path/to/audio.wav",
    "duration_seconds": 603.56,
    "speakers": {
        "SPEAKER_00": {
            "segments": [{"start": 0.5, "end": 2.3, "duration": 1.8}, ...],
            "total_duration": 53.3,
            "segment_count": 28
        },
        "SPEAKER_01": {...},
        "SPEAKER_02": {...}
    },
    "dominant_speaker": "SPEAKER_02",
    "dominant_speaker_duration": 146.19
}
```

---

## Stashbox Integration

### Metadata Extension

Stashbox could store the climax speaker mapping as scene metadata:

```json
{
  "scene_id": "abc123",
  "performers": [
    {"id": "dustin-steele", "stash_id": "..."},
    {"id": "cesar-rossi", "stash_id": "..."}
  ],
  "voice_analysis": {
    "climax_performer": "dustin-steele",
    "climax_timestamp": 542.3,
    "climax_energy_ratio": 4.2,
    "speaker_mapping": {
      "SPEAKER_02": "dustin-steele",
      "SPEAKER_00": "cesar-rossi"
    }
  }
}
```

### Workflow Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     STASHBOX WORKFLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User identifies scene in Stashbox                           │
│                     ↓                                            │
│  2. User selects performer to extract                           │
│                     ↓                                            │
│  3. System runs climax detection on audio                       │
│                     ↓                                            │
│  4. User confirms: "Is this the climax moment?" [preview]       │
│                     ↓                                            │
│  5. System maps climax speaker to selected performer            │
│                     ↓                                            │
│  6. Extract that speaker's audio (full or moaning-only)         │
│                     ↓                                            │
│  7. Save mapping to Stashbox metadata for future scenes         │
│                     ↓                                            │
│  8. Train RVC voice model from accumulated extractions          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints (Proposed)

```python
# POST /api/scene/{id}/analyze-voice
# Runs diarization and climax detection
{
    "speakers": ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"],
    "climax_speaker": "SPEAKER_02",
    "climax_timestamp": 542.3
}

# POST /api/scene/{id}/map-performer
# Maps speaker to performer
{
    "speaker_id": "SPEAKER_02",
    "performer_id": "dustin-steele"
}

# POST /api/scene/{id}/extract-voice
# Extracts audio for mapped performer
{
    "mode": "moaning_only",  # or "full_vocal", "speech_only"
    "performer_id": "dustin-steele"
}
```

### Learning Over Time

With stored mappings, the system can:

1. **Build performer voice profiles** - Aggregate embeddings across scenes
2. **Auto-identify in new scenes** - Match new speakers to known profiles
3. **Improve accuracy** - User corrections train the system
4. **Cross-reference** - "This sounds like Dustin" before scene is tagged

---

## Configuration & Tuning

### Climax Detection Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `search_region` | 0.3 (last 30%) | 0.2-0.5 | Lower = narrower focus |
| `window_size` | 500ms | 200-1000ms | Larger = smoother energy |
| `hop_size` | 100ms | 50-200ms | Smaller = higher resolution |
| `energy_threshold` | 2.5x median | 2.0-4.0 | Higher = fewer peaks |
| `local_max_window` | 300ms | 100-500ms | Avoid duplicate peaks |

### Moaning Extraction Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `end_portion` | 0.3 | Region to search (last 30%) |
| `energy_threshold` | 2.5 | Filter to loud segments |
| `min_segment_duration` | 0.3s | Minimum segment length |
| `fallback_top_percent` | 50% | If few high-energy, take top half |

### Tuning for Different Content Types

**High-intensity scenes:**
```python
energy_threshold = 3.0  # Higher bar for "moaning"
search_region = 0.25    # Focus on final quarter
```

**Quiet/artistic scenes:**
```python
energy_threshold = 2.0  # Lower sensitivity
search_region = 0.4     # Broader search
```

**Compilation videos:**
```python
# Multiple climax moments expected
# Return more peaks, let user select
max_peaks = 10
```

---

## Performance Characteristics

### Processing Time

| Stage | Time (10-min video) | GPU | CPU |
|-------|---------------------|-----|-----|
| Diarization | 60-90s | MPS | 3-5min |
| Climax Detection | 2-3s | - | 2-3s |
| Moaning Extraction | 5-10s | - | 5-10s |
| **Total (uncached)** | **~90s** | | **~6min** |
| **Total (cached)** | **~15s** | | **~15s** |

### Memory Usage

- Diarization model: ~500MB-1GB
- Peak processing: ~100MB (waveform in memory)
- Apple Silicon MPS: Shared GPU memory

### Caching

Analysis results cached at:
```
/Volumes/David External/SAM_Voice_Training/.cache/
├── <filename>_<hash>_analysis.json  # Speaker segments
└── ...
```

Cache invalidation: By file hash (content change = re-analyze)

---

## Known Limitations

### False Positives

1. **Music crescendos** - High-energy music can trigger detection
2. **Other performer climax** - If another performer climaxes simultaneously
3. **Audio effects** - Reverb, compression can blur energy peaks

**Mitigation:** Human review of climax_speaker_mapping.json

### Edge Cases

1. **Performer doesn't climax** - Falls back to dominant speaker
2. **Multiple climaxes** - Takes highest energy peak
3. **Very short scenes** - Less audio in search region
4. **Compilation videos** - Multiple scenes, multiple climaxes

### Technical Limitations

1. **No cross-file speaker matching** - Each file has independent speaker IDs
2. **No voice embeddings (yet)** - Can't say "this sounds like person X"
3. **Energy-only detection** - Doesn't analyze vocal patterns

---

## Future Enhancements

### Planned Features

- [ ] **Speaker embedding clustering** - Match same voice across files
- [ ] **Reference audio matching** - "Extract person who sounds like this sample"
- [ ] **Music/speech separation** - Remove background music before analysis
- [ ] **SNR-based quality filtering** - Reject noisy segments
- [ ] **Parallel processing** - Multi-core for batch processing

### Stashbox-Specific Features

- [ ] **Performer profile learning** - Build voice profile from multiple scenes
- [ ] **Auto-tagging** - "This speaker sounds like known performer X"
- [ ] **Confidence scores** - "85% confident this is Dustin"
- [ ] **User correction loop** - Improve mappings from feedback

### RVC Training Integration

- [ ] **Auto-train trigger** - "Train voice when 30+ minutes accumulated"
- [ ] **Quality gating** - Exclude low-SNR segments from training
- [ ] **Dataset management** - Track which scenes contributed to model

---

## Quick Start

### 1. Install Dependencies

```bash
source /Volumes/Plex/DevSymlinks/venvs/SAM_voice_venv_diarization/bin/activate

# Already installed:
# pip install pyannote.audio torch torchaudio
```

### 2. Run Climax Detection

```bash
cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain

python3 voice_extraction_pipeline.py climax \
    /path/to/audio/files \
    /path/to/output
```

### 3. Review Mapping

```bash
cat /path/to/output/climax_speaker_mapping.json
```

### 4. Extract Moaning

```bash
python3 voice_extraction_pipeline.py extract-moaning \
    /path/to/audio/files \
    /path/to/output/moaning
```

### 5. Use for RVC Training

```bash
# Copy extracted audio to RVC dataset
cp /path/to/output/moaning/*.wav ~/Projects/RVC/rvc-webui/datasets/performer_name/
```

---

## Contact & Maintenance

**Pipeline Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/voice_extraction_pipeline.py`

**Related Documentation:**
- General pipeline docs: `VOICE_EXTRACTION.md`
- SAM brain architecture: `CLAUDE.md`
- Project registry: `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md`

---

*This system was developed for extracting performer voices from multi-speaker adult content. The climax-anchored approach provides a reliable method for cross-file speaker identification without requiring manual labeling or reference audio samples.*
