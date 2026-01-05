# Apple Music Animated Artwork Fetcher

A powerful tool for automatically downloading animated album artwork from Apple Music for your entire music library.

## Overview

This module enables SAM to fetch official animated album artwork that artists publish on Apple Music. These are real animations created by artists and labels - not simple Ken Burns effects, but actual motion graphics, particle effects, and artistic visualizations.

**Key Features:**
- No Apple Music subscription required
- Automatic artist discography scanning
- Highest quality HEVC downloads (up to 2160x2160)
- Batch processing for entire music libraries
- Beets library integration
- Automatic metadata tagging

## Quick Start

```bash
# Navigate to the module
cd ~/ReverseLab/SAM/media/apple_music

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run on your beets library
python3 bulk_fetch.py
```

## Files

| File | Description |
|------|-------------|
| `bulk_fetch.py` | Main batch downloader - scans artist discographies |
| `fetcher.py` | Original single-album fetcher (from bunnykek) |
| `requirements.txt` | Python dependencies |

## Usage

### Basic Usage

```bash
# Scan all artists in your beets library and download animated artwork
python3 bulk_fetch.py

# Dry run - see what's available without downloading
python3 bulk_fetch.py --dry-run

# Process a single artist
python3 bulk_fetch.py --artist "Beyoncé"

# Limit to first N artists
python3 bulk_fetch.py --limit 10

# Custom output directory
python3 bulk_fetch.py -o /path/to/output
```

### Single Album Download

```bash
# Download from a specific Apple Music URL
python3 fetcher.py "https://music.apple.com/us/album/renaissance/1636789969"

# With options
python3 fetcher.py -T square -L 2 "https://music.apple.com/us/album/renaissance/1636789969"
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output directory | `/Volumes/Music/_Animated_Covers_Apple` |
| `-l, --limit` | Limit number of artists | 0 (no limit) |
| `-a, --artist` | Process single artist | None |
| `--dry-run` | Check only, no download | False |
| `-T, --type` | Artwork type (square/tall) | square |
| `-L, --loops` | Number of loops | 1 |

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Beets Music Library                       │
│              (artist, album metadata)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Apple Music Search API                          │
│         amp-api.music.apple.com/v1/catalog                  │
│                                                              │
│  1. Search for artist by name                               │
│  2. Get artist ID                                           │
│  3. Fetch all albums with editorialVideo extension          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Animated Artwork Detection                      │
│                                                              │
│  Check for 'editorialVideo' in album attributes:            │
│  - motionDetailSquare (preferred)                           │
│  - motionSquareVideo1x1                                     │
│  - motionDetailTall                                         │
│  - motionTallVideo3x4                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              HLS Stream Download                             │
│                                                              │
│  1. Parse M3U8 playlist                                     │
│  2. Select highest quality HEVC stream                      │
│  3. Download via ffmpeg                                     │
│  4. Tag with metadata (artist, album, year, etc.)          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Output Directory                                │
│         /Volumes/Music/_Animated_Covers_Apple               │
│                                                              │
│  Files named: "Artist - Album (Year).mp4"                   │
│  Typical size: 10-30MB per animation                        │
│  Resolution: Up to 2160x2160                                │
│  Codec: HEVC (hvc1) or H.264 (avc1)                        │
└─────────────────────────────────────────────────────────────┘
```

### API Details

The fetcher uses Apple Music's public API endpoints:

1. **Token Acquisition**: Extracts JWT token from Apple Music web player JavaScript
2. **Artist Search**: `GET /v1/catalog/{country}/search?term={artist}&types=artists`
3. **Album List**: `GET /v1/catalog/{country}/artists/{id}/albums?extend=editorialVideo`
4. **Video Stream**: HLS m3u8 playlist from `editorialVideo.motionDetailSquare.video`

### Quality Tiers

The API provides multiple quality options:

| Resolution | Bitrate | Codec | Recommended |
|------------|---------|-------|-------------|
| 2160x2160 | ~30 Mb/s | HEVC | Best quality |
| 1920x1920 | ~18 Mb/s | HEVC | High quality |
| 1080x1080 | ~10 Mb/s | HEVC | Good quality |
| 960x960 | ~4 Mb/s | HEVC/AVC | Medium |
| 768x768 | ~2 Mb/s | HEVC | Low |

The fetcher automatically selects the highest available HEVC stream.

## Storage Requirements

### Estimation Formula

```
Storage = (Albums with animation) × (Average file size)
        = (Total albums × 0.15) × 17MB
```

Most music from 2015+ has ~15% animated artwork coverage.

### Example Calculations

| Library Size | Estimated Animations | Storage Needed |
|--------------|---------------------|----------------|
| 100 albums | ~15 | ~255 MB |
| 1,000 albums | ~150 | ~2.5 GB |
| 10,000 albums | ~1,500 | ~25 GB |
| 50,000 albums | ~7,500 | ~125 GB |

### Current Stats (Your Library)

- Available space: **5.5 TB**
- Current animations: 48 files, 857 MB
- Average file size: 17 MB
- Plenty of space for full collection

## Artists with Animated Artwork

### High Coverage Artists (5+ albums)

These artists have extensive animated artwork catalogs:

- **Ariana Grande** - 9+ albums (Positions, eternal sunshine, Wicked soundtracks)
- **Britney Spears** - 12+ albums (entire catalog remastered with animations)
- **The Weeknd** - 12+ albums (After Hours, Dawn FM, etc.)
- **Doja Cat** - 15+ albums (Planet Her, Scarlet, Hot Pink)
- **Taylor Swift** - 5+ albums (evermore, folklore, Midnights)
- **Beyoncé** - 4+ albums (RENAISSANCE, Lemonade, B'Day, 4)
- **Air** - 7+ albums (Moon Safari 25th anniversary editions)

### Artists Typically WITHOUT Animated Artwork

- Most pre-2015 releases
- Independent/small label artists
- Classical music
- Jazz catalogs
- Legacy/deceased artists (unless remastered)

## Integration with SAM

### Terminal Command

```bash
# From SAM terminal, invoke the media fetcher
sam media fetch-artwork --source apple-music

# Or directly
~/ReverseLab/SAM/media/apple_music/bulk_fetch.py
```

### Automation Script

Create `~/.sam/hooks/post-import-artwork.sh`:

```bash
#!/bin/bash
# Automatically fetch animated artwork after beets import

cd ~/ReverseLab/SAM/media/apple_music
source venv/bin/activate

# Get the newly imported artist
ARTIST="$1"

if [ -n "$ARTIST" ]; then
    python3 bulk_fetch.py --artist "$ARTIST"
fi
```

## Troubleshooting

### Common Issues

**Token Expired**
```
Token expired!
Updating the token...
```
This is normal - the fetcher automatically refreshes expired tokens.

**No Animated Artwork**
```
No animated artwork available
```
The artist/album doesn't have animated artwork on Apple Music.

**Rate Limiting**
If you see connection errors, add a longer delay:
```python
time.sleep(2)  # Increase from 0.5 to 2 seconds
```

**FFmpeg Not Found**
```bash
brew install ffmpeg
```

### Debug Mode

Enable verbose output:
```python
# In bulk_fetch.py, change:
subprocess.run(['ffmpeg', '-loglevel', 'error', ...])
# To:
subprocess.run(['ffmpeg', '-loglevel', 'info', ...])
```

## Credits

- Original single-album fetcher by [bunnykek](https://github.com/bunnykek/Apple-Music-Animated-Artwork-Fetcher)
- Bulk fetcher and SAM integration by SAM development team
- Apple Music API reverse engineering by community contributors

## Legal Notice

This tool is for personal use only. Downloaded artwork is subject to Apple's terms of service. The artwork remains the intellectual property of the respective artists and labels.

## Changelog

### v1.0.0 (2024-12-28)
- Initial SAM integration
- Full discography scanning
- Automatic quality selection
- Beets library integration
- Comprehensive documentation
