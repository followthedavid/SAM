# Discogs CD Scan Fetcher

Fetches CD scans, liner notes, and artwork from Discogs using exact catalog number matching.

## Why Catalog Numbers?

CD releases from different countries often have different:
- Bonus tracks (Japan editions are famous for this)
- Liner notes and booklets
- Artwork variations
- Mastering differences

By using catalog numbers (e.g., `AVCZ-95114` for Japanese Britney Spears), we can fetch the **exact** scans for your specific release, not just a generic album cover.

## Folder Naming Convention

Your library uses this format:
```
[Artist] - Year - Album - (Country - Label – Catalog#) - [Format]
```

Examples:
```
[Britney Spears] - 1999 - Baby One More Time - (Japan - Zomba – AVCZ-95114) - [ALAC]
[Air] - 1998 - Moon Safari - (France - Source – 7243 8 45185 2 8) - [FLAC]
[Radiohead] - 1997 - OK Computer - (UK - Parlophone – 7243 8 55229 2 5) - [FLAC]
```

## Usage

### Prerequisites

1. Get a free Discogs API token:
   - Go to https://www.discogs.com/settings/developers
   - Click "Generate new token"
   - Save the token

2. Set the token:
```bash
export DISCOGS_TOKEN="your_token_here"
```

### Commands

```bash
# Scan entire library
python3 fetch_cd_scans.py

# Single album folder
python3 fetch_cd_scans.py --folder "[Air] - 1998 - Moon Safari - (France - Source – 7243 8 45185 2 8) - [FLAC]"

# Preview matches without downloading
python3 fetch_cd_scans.py --dry-run

# Limit to first 10 albums
python3 fetch_cd_scans.py --limit 10

# Custom output directory
python3 fetch_cd_scans.py -o /path/to/scans
```

### Options

| Flag | Description |
|------|-------------|
| `-l, --library` | Music library path (default: `/Volumes/Music/_Music Lossless`) |
| `-o, --output` | Output directory (default: `/Volumes/Music/_CD_Scans`) |
| `-t, --token` | Discogs API token (or use `DISCOGS_TOKEN` env var) |
| `--limit N` | Process only first N albums |
| `--dry-run` | Preview matches without downloading |
| `--folder PATH` | Process a single album folder |

## Output

```
_CD_Scans/
├── Britney Spears - Baby One More Time/
│   ├── cover.jpg           # Front cover
│   ├── back_01.jpg         # Back cover
│   ├── secondary_02.jpg    # Booklet page 1
│   ├── secondary_03.jpg    # Booklet page 2
│   └── release_info.json   # Full Discogs metadata
```

### release_info.json

Contains rich metadata:
- Full tracklist with durations
- Production credits (producers, engineers, etc.)
- Label information
- Release notes
- Original Discogs URL

## Search Strategy

1. **Catalog Number Search** (most accurate)
   - Searches Discogs by exact catalog number
   - Gets the specific pressing you own

2. **Fallback Search**
   - If no catalog match, searches by artist + album + year
   - May return a different pressing

## Rate Limits

| Authentication | Rate Limit |
|---------------|------------|
| With token | 60 requests/minute |
| Without token | 25 requests/minute |

The script automatically enforces rate limits to avoid API bans.

## Integration with SAM

This is part of SAM's media capabilities for building a collector's-grade music library:

```
SAM Media Stack:
├── Animated Artwork   → Apple Music API
├── CD Scans/Booklets  → Discogs API
├── Synced Lyrics      → LRCLIB
├── Music Videos       → (Planned)
└── Karaoke            → Demucs AI + LRCLIB
```

## Credits

- [Discogs API](https://www.discogs.com/developers/) - Comprehensive music database
- SAM Project
