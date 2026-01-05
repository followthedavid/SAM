# SAM Media Capabilities

SAM includes powerful media management capabilities for handling music libraries, artwork, and multimedia content.

## Available Capabilities

### 1. Apple Music Animated Artwork Fetcher

**Location:** `~/ReverseLab/SAM/media/apple_music/`

Automatically downloads official animated album artwork from Apple Music for your entire music library.

#### What It Does

- Scans your beets music library for artists
- Searches Apple Music for each artist's discography
- Identifies albums with animated artwork
- Downloads highest quality HEVC video (up to 2160x2160)
- Tags files with metadata (artist, album, year, etc.)

#### Quick Start

```bash
cd ~/ReverseLab/SAM/media/apple_music
source venv/bin/activate
python3 bulk_fetch.py
```

#### Key Commands

| Command | Description |
|---------|-------------|
| `python3 bulk_fetch.py` | Scan full library |
| `python3 bulk_fetch.py --dry-run` | Preview only |
| `python3 bulk_fetch.py --artist "Name"` | Single artist |
| `python3 bulk_fetch.py -o /path` | Custom output |

#### Requirements

- Python 3.x with venv
- ffmpeg (for video processing)
- beets (for library metadata)
- No Apple Music subscription needed

#### Output

- Directory: `/Volumes/Music/_Animated_Covers_Apple/`
- Format: `Artist - Album (Year).mp4`
- Quality: HEVC, up to 2160x2160, ~17MB average

#### Coverage

Animated artwork is typically available for:
- Major label releases from 2015+
- Pop, hip-hop, electronic, R&B genres
- Artists: Ariana Grande, Beyoncé, The Weeknd, Doja Cat, Taylor Swift, Britney Spears, etc.

See full documentation: [`media/apple_music/README.md`](../../media/apple_music/README.md)

---

### 2. SAM Karaoke System

**Location:** `~/ReverseLab/SAM/media/karaoke/`

A self-hosted karaoke solution that rivals Apple Music Sing, using AI vocal separation and synced lyrics.

#### What It Does

- Separates vocals using Meta's Demucs AI model
- Fetches synced lyrics from LRCLIB (free, open source)
- Generates karaoke videos with scrolling/highlighting lyrics
- Outputs Apple TV-compatible videos for Plex streaming

#### Quick Start

```bash
cd ~/ReverseLab/SAM/media/karaoke
source venv/bin/activate
python3 generate_karaoke.py -i "song.m4a" -o output/
```

#### Key Commands

| Command | Description |
|---------|-------------|
| `generate_karaoke.py -i song.m4a` | Full karaoke generation |
| `generate_karaoke.py --batch -i folder/` | Batch process folder |
| `generate_karaoke.py --no-guide -i song.m4a` | Pure instrumental |
| `vocal_separator.py -i song.m4a` | Vocal separation only |
| `fetch_lyrics.py -a "Artist" -t "Title"` | Fetch lyrics only |

#### Requirements

- Python 3.8+ with demucs, torch, torchaudio
- ffmpeg
- ~4GB RAM (GPU optional but speeds up processing)
- No subscriptions needed

#### Output

```
output/
├── Artist - Song (Karaoke).mp4    # Video with lyrics + guide vocals
├── Artist - Song (Instrumental).mp4  # Video with lyrics, no vocals
├── vocals.wav                     # Isolated vocals
├── no_vocals.wav                  # Instrumental
├── lyrics.lrc                     # Synced lyrics
└── lyrics.ass                     # ASS subtitle format
```

#### Comparison to Apple Music Sing

| Feature           | Apple Music Sing | SAM Karaoke        |
|-------------------|------------------|--------------------|
| Vocal reduction   | ✅               | ✅ (Demucs AI)     |
| Synced lyrics     | ✅               | ✅ (LRCLIB)        |
| Word highlighting | ✅               | ✅ (when available)|
| Apple TV          | ✅               | ✅ (via Plex)      |
| Subscription      | Required         | Free               |
| Works offline     | No               | Yes                |
| Your own library  | No               | Yes                |

See full documentation: [`media/karaoke/README.md`](../../media/karaoke/README.md)

---

### 3. Discogs CD Scan Fetcher

**Location:** `~/ReverseLab/SAM/media/discogs/`

Fetches CD scans, liner notes, and artwork from Discogs using exact catalog number matching.

#### What It Does

- Parses your folder naming convention: `[Artist] - Year - Album - (Country - Label – Catalog#) - [Format]`
- Uses catalog number for exact Discogs release matching
- Downloads all available CD scans (front, back, booklet, disc)
- Saves release information as JSON

#### Quick Start

```bash
cd ~/ReverseLab/SAM/media/discogs
python3 fetch_cd_scans.py --token YOUR_TOKEN --limit 10
```

#### Key Commands

| Command | Description |
|---------|-------------|
| `fetch_cd_scans.py -t TOKEN` | Scan full library |
| `fetch_cd_scans.py --dry-run` | Preview matches |
| `fetch_cd_scans.py --folder "path"` | Single album |
| `fetch_cd_scans.py --limit 50` | Process first 50 |

#### Requirements

- Discogs API token (free at discogs.com/settings/developers)
- Rate limit: 60 req/min authenticated, 25 unauthenticated

#### Output

```
_CD_Scans/
├── Artist - Album/
│   ├── cover.jpg           # Front cover
│   ├── back_01.jpg         # Back cover
│   ├── secondary_02.jpg    # Booklet pages
│   └── release_info.json   # Discogs metadata
```

See full documentation: [`media/discogs/README.md`](../../media/discogs/README.md)

---

## Future Media Capabilities

### Planned

- **Spotify Canvas Downloader** - Download Spotify's looping video backgrounds
- **YouTube Music Visualizer Extractor** - Extract official visualizers
- **AI Artwork Generator** - Generate animated covers using Stable Video Diffusion
- **Cover Art Upscaler** - Enhance low-resolution album artwork

### Integration Points

SAM media capabilities integrate with:

- **Beets** - Music library management and metadata
- **Plex/Navidrome** - Media server artwork display
- **Terminal UI** - Progress display and controls

---

## Architecture

```
SAM/media/
├── apple_music/           # Apple Music animated artwork
│   ├── bulk_fetch.py      # Batch downloader
│   ├── deploy_animated_covers.py  # WebP deployer
│   └── README.md          # Module documentation
├── karaoke/               # SAM Karaoke System
│   ├── generate_karaoke.py    # Main video generator
│   ├── vocal_separator.py     # Demucs wrapper
│   ├── fetch_lyrics.py        # LRCLIB client
│   └── README.md              # Module documentation
├── discogs/               # CD Scan Fetcher
│   ├── fetch_cd_scans.py      # Catalog-based fetcher
│   └── README.md              # Module documentation
├── spotify_canvas/        # (Planned) Spotify Canvas
└── youtube_music/         # (Planned) YouTube Music
```

---

## Storage Planning

### Current Usage

| Type | Files | Size |
|------|-------|------|
| Apple Music Animations | 48 | 857 MB |

### Projections

| Library Size | Est. Animations | Storage |
|--------------|-----------------|---------|
| 1,000 albums | 150 | 2.5 GB |
| 10,000 albums | 1,500 | 25 GB |
| 50,000 albums | 7,500 | 125 GB |

Your available space: **5.5 TB** - more than sufficient.

---

## Related Documentation

- [Apple Music Animated Artwork README](../../media/apple_music/README.md)
- [Beets Configuration](https://beets.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
