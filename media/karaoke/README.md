# SAM Karaoke System

A self-hosted karaoke solution that rivals Apple Music Sing, using AI vocal separation and synced lyrics.

## Features

- **Vocal Separation**: Uses Meta's Demucs AI to isolate and reduce vocals
- **Synced Lyrics**: Fetches timed lyrics from LRCLIB (free, open source)
- **Karaoke Video Generation**: Creates videos with scrolling/highlighting lyrics
- **Apple TV Compatible**: Streams via Plex or AirPlay

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    SAM Karaoke Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│   │  Audio   │ → │  Demucs  │ → │  LRCLIB  │ → │  Video   │ │
│   │   File   │   │  Vocal   │   │  Synced  │   │  Output  │ │
│   │          │   │  Split   │   │  Lyrics  │   │          │ │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                                                              │
│   Outputs:                                                   │
│   • vocals.wav        - Isolated vocals                      │
│   • no_vocals.wav     - Instrumental/backing                 │
│   • lyrics.lrc        - Synced lyrics file                   │
│   • karaoke.mp4       - Video with lyrics overlay            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
cd ~/ReverseLab/SAM/media/karaoke
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install demucs torch torchaudio requests ffmpeg-python
```

### 2. Process a Song

```bash
# Full karaoke generation
python3 generate_karaoke.py -i "song.m4a" -o output/

# Just vocal separation
python3 vocal_separator.py -i "song.m4a"

# Just fetch lyrics
python3 fetch_lyrics.py -a "Artist" -t "Track Title"
```

### 3. Stream to Apple TV

**Option A: Plex**
- Add karaoke output folder to Plex library
- Play from Plex app on Apple TV

**Option B: AirPlay**
- Open karaoke video on Mac
- AirPlay to Apple TV

## Components

### vocal_separator.py
Uses Demucs to split audio into stems:
- vocals.wav
- drums.wav
- bass.wav
- other.wav

### fetch_lyrics.py
Fetches synced lyrics (.lrc) from LRCLIB:
- Searches by artist + title
- Returns word-by-word or line-by-line timing
- Falls back to Genius for plain lyrics

### generate_karaoke.py
Creates karaoke videos:
- Combines instrumental track with lyrics overlay
- Highlights current line
- Optional: Album artwork background

## Comparison to Apple Music Sing

| Feature           | Apple Music Sing | SAM Karaoke           |
|-------------------|-----------------|-----------------------|
| Vocal reduction   | ✅              | ✅ (Demucs AI)        |
| Synced lyrics     | ✅              | ✅ (LRCLIB)           |
| Word highlighting | ✅              | ✅ (when available)   |
| Duet mode         | ✅              | 🔄 Planned            |
| Apple TV          | ✅              | ✅ (via Plex/AirPlay) |
| Subscription      | Required        | Free                  |
| Works offline     | No              | Yes                   |
| Your own library  | No              | Yes                   |

## Requirements

- Python 3.8+
- ffmpeg
- ~4GB RAM for Demucs
- GPU optional (speeds up processing)

## Output Structure

```
output/
├── Artist - Track/
│   ├── original.m4a         # Original audio
│   ├── vocals.wav           # Isolated vocals
│   ├── no_vocals.wav        # Instrumental
│   ├── lyrics.lrc           # Synced lyrics
│   ├── karaoke.mp4          # Video with lyrics
│   └── metadata.json        # Track info
```

## Credits

- [Demucs](https://github.com/facebookresearch/demucs) - Meta's AI audio separator
- [LRCLIB](https://lrclib.net) - Free synced lyrics database
- SAM Project

## License

MIT License - Use freely for personal karaoke enjoyment.
