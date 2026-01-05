# SAM (Warp_Open)

A comprehensive terminal replacement and media management system.

## Overview

SAM combines a clean-room Warp-like terminal UX with powerful media management capabilities for music libraries.

## Core Components

| Component | Description | Location |
|-----------|-------------|----------|
| **warp_core** | Rust backend for terminal emulation | `warp_core/` |
| **warp_tauri** | Tauri-based terminal UI | `warp_tauri/` |
| **Media Capabilities** | Music library management tools | `media/` |

## Quick Start

### Terminal

```bash
# Launch the terminal app
cd ~/ReverseLab/SAM/warp_tauri && npm run dev
```

### Media Capabilities

```bash
# Download animated album artwork from Apple Music
~/ReverseLab/SAM/scripts/sam_media.sh artwork

# Check media collection status
~/ReverseLab/SAM/scripts/sam_media.sh status

# Preview available artwork (dry run)
~/ReverseLab/SAM/scripts/sam_media.sh artwork-scan
```

## Media Capabilities

### Apple Music Animated Artwork

Automatically download official animated album artwork for your entire music library.

**Features:**
- No Apple Music subscription required
- Full artist discography scanning
- Highest quality HEVC (up to 2160x2160)
- Beets library integration
- Automatic metadata tagging

**Usage:**
```bash
# Full library scan and download
~/ReverseLab/SAM/scripts/sam_media.sh artwork

# Single artist
~/ReverseLab/SAM/scripts/sam_media.sh artwork-artist "Beyoncé"

# Custom output directory
cd ~/ReverseLab/SAM/media/apple_music
source venv/bin/activate
python3 bulk_fetch.py -o /custom/path
```

**Documentation:** [`media/apple_music/README.md`](media/apple_music/README.md)

### Album Experience Vision

SAM aims to create rich, immersive album experiences with:

- Animated artwork
- CD scans and liner notes
- Historical context and reviews
- Full production credits
- Artist photos and promotional material

See the full vision: [`docs/capabilities/ALBUM_EXPERIENCE_VISION.md`](docs/capabilities/ALBUM_EXPERIENCE_VISION.md)

## Documentation

| Document | Description |
|----------|-------------|
| [`ROADMAP.md`](ROADMAP.md) | Development roadmap and milestones |
| [`docs/capabilities/MEDIA_CAPABILITIES.md`](docs/capabilities/MEDIA_CAPABILITIES.md) | Media feature documentation |
| [`docs/capabilities/ALBUM_EXPERIENCE_VISION.md`](docs/capabilities/ALBUM_EXPERIENCE_VISION.md) | Future vision for album experiences |
| [`warp_core/README.md`](warp_core/README.md) | Terminal core documentation |
| [`warp_tauri/README.md`](warp_tauri/README.md) | UI application documentation |

## Project Structure

```
SAM/
├── warp_core/              # Rust terminal emulation core
├── warp_tauri/             # Tauri-based terminal UI
├── media/                  # Media management capabilities
│   └── apple_music/        # Apple Music animated artwork fetcher
├── scripts/                # Utility scripts
│   └── sam_media.sh        # Media CLI interface
├── docs/
│   ├── spec/               # Technical specifications
│   └── capabilities/       # Feature documentation
├── app/                    # Legacy Electron app
├── tools/                  # Development tools
└── tests/                  # Test suites
```

## Requirements

### Terminal
- Rust (for warp_core)
- Node.js (for warp_tauri)
- Tauri CLI

### Media Capabilities
- Python 3.x
- ffmpeg
- beets (for library metadata)

## Current Status

| Feature | Status |
|---------|--------|
| Terminal Core (PTY) | Phase 1 In Progress |
| Terminal UI | Phase 2 Pending |
| Apple Music Artwork | ✅ Complete |
| CD Scans | Planned |
| Album Experience | Vision Documented |

## Credits

- Terminal architecture inspired by Warp
- Apple Music fetcher based on [bunnykek's work](https://github.com/bunnykek/Apple-Music-Animated-Artwork-Fetcher)
- Album experience vision by SAM development team
