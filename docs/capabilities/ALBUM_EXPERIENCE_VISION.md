# Album Experience Vision

Transform each album into a rich, immersive experience - like a Rolling Stone magazine feature with full multimedia content, historical context, and nostalgia.

## The Vision

When viewing an album in SAM, users should experience:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌────────────────┐    RENAISSANCE                                  │
│  │                │    Beyoncé (2022)                               │
│  │   [ANIMATED    │                                                  │
│  │    ARTWORK]    │    "A masterwork of dance music history,        │
│  │                │     sampling from Chicago house to Donna        │
│  │                │     Summer to Grace Jones..."                   │
│  └────────────────┘                                                  │
│                                                                      │
│  ══════════════════════════════════════════════════════════════════ │
│                                                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                               │
│  │FRONT │ │BACK  │ │DISC  │ │BOOK  │   CD Scans & Physical Media   │
│  │COVER │ │COVER │ │ART   │ │LET   │                               │
│  └──────┘ └──────┘ └──────┘ └──────┘                               │
│                                                                      │
│  ══════════════════════════════════════════════════════════════════ │
│                                                                      │
│  THE CONTEXT                                                         │
│  ────────────                                                        │
│  Released July 29, 2022 during the post-pandemic dance music        │
│  renaissance. Beyoncé's first solo album in six years, created      │
│  during lockdown as a celebration of Black and queer dance          │
│  culture. Samples 26 songs spanning disco, house, and Afrobeats... │
│                                                                      │
│  CREDITS                                 REVIEWS                     │
│  ───────                                 ───────                     │
│  Written by: Beyoncé, The-Dream,         Rolling Stone: ★★★★★       │
│              Tricky Stewart...           Pitchfork: 8.8              │
│  Produced by: Beyoncé, The-Dream         NME: ★★★★★                 │
│  Mixed at: Jungle City Studios                                       │
│                                                                      │
│  ══════════════════════════════════════════════════════════════════ │
│                                                                      │
│  PHOTOS & PRESS                                                      │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                                │
│  │    │ │    │ │    │ │    │ │    │  Promo shots, tour photos,     │
│  │    │ │    │ │    │ │    │ │    │  magazine covers, interviews   │
│  └────┘ └────┘ └────┘ └────┘ └────┘                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Content Layers

### 1. Visual Media (Current + Planned)

| Type | Status | Source | Description |
|------|--------|--------|-------------|
| Animated Artwork | ✅ **Done** | Apple Music | Official motion graphics |
| High-res Cover | Planned | Apple Music, Discogs | 3000x3000 album art |
| CD Scans | Planned | Discogs, Archive.org | Front, back, disc, booklet |
| Liner Notes | Planned | Discogs, OCR | Credits, lyrics, thank yous |
| Promotional Photos | Planned | Last.fm, Fanart.tv | Artist and album promo shots |
| Music Videos | Planned | YouTube | Official videos from album |

### 2. Historical Context

| Type | Source | Description |
|------|--------|-------------|
| Release Context | Wikipedia, MusicBrainz | What was happening when album dropped |
| Chart Performance | Billboard API | Peak positions, weeks on chart |
| Critical Reception | Metacritic, Pitchfork | Review scores and excerpts |
| Awards | Grammy API, Wikipedia | Nominations and wins |
| Samples & Interpolations | WhoSampled | What it samples, what samples it |
| Musical Influences | Last.fm, AllMusic | Genre tags, similar artists |

### 3. Technical Metadata

| Type | Source | Description |
|------|--------|-------------|
| Full Credits | Discogs, MusicBrainz | Every musician, engineer, studio |
| Recording Details | Discogs | Studios, dates, equipment |
| Mastering Info | DR Database | Dynamic range, loudness |
| Release Variants | Discogs | All pressings, editions, formats |
| Catalog Numbers | MusicBrainz | UPC, ISRC, catalog codes |

## Data Sources

### Primary Sources

1. **Apple Music API** - Animated artwork, metadata, editorial content
2. **Discogs API** - CD scans, credits, pressings, marketplace data
3. **MusicBrainz API** - Canonical metadata, relationships, credits
4. **Last.fm API** - Artist bios, photos, similar artists, tags
5. **Fanart.tv API** - Artist artwork, album art, logos
6. **Wikipedia API** - Historical context, article excerpts
7. **WhoSampled** - Sample data, covers, remixes

### Secondary Sources

8. **Pitchfork** - Reviews (scraping)
9. **Metacritic** - Aggregate scores
10. **Billboard** - Chart data
11. **Internet Archive** - Scans, historical press
12. **YouTube** - Music videos, interviews

## Implementation Roadmap

### Phase 1: Visual Media (Current)
- [x] Apple Music animated artwork
- [ ] High-resolution cover art (Apple Music, Discogs)
- [ ] CD scans from Discogs

### Phase 2: Extended Artwork
- [ ] Disc art / label scans
- [ ] Booklet page scans
- [ ] Back cover with tracklist
- [ ] Promotional photos (Fanart.tv)

### Phase 3: Context & Credits
- [ ] Full credits from Discogs/MusicBrainz
- [ ] Wikipedia article excerpts
- [ ] Release date context ("On this day in history...")
- [ ] Chart performance data

### Phase 4: Reviews & Reception
- [ ] Pitchfork/Rolling Stone review excerpts
- [ ] Metacritic aggregate score
- [ ] Grammy nominations/wins
- [ ] Contemporary press quotes

### Phase 5: Interactive Experience
- [ ] Timeline view of artist discography
- [ ] Sample/influence web visualization
- [ ] "Similar albums" recommendations
- [ ] User annotations and notes

## Technical Architecture

```
SAM/media/
├── apple_music/           # ✅ Animated artwork (done)
├── discogs/               # CD scans, credits, pressings
├── musicbrainz/           # Canonical metadata
├── lastfm/                # Artist info, photos
├── fanart/                # High-res artist images
├── wikipedia/             # Historical context
├── whosampled/            # Sample data
├── reviews/               # Pitchfork, Metacritic
└── album_experience/      # Unified album page generator
    ├── templates/         # HTML/React templates
    ├── cache/             # Downloaded media cache
    └── output/            # Generated album pages
```

## Storage Estimates

| Content Type | Per Album | 10K Albums |
|--------------|-----------|------------|
| Animated artwork | 17 MB | 170 GB |
| High-res cover | 2 MB | 20 GB |
| CD scans (4 images) | 8 MB | 80 GB |
| Liner notes (10 pages) | 5 MB | 50 GB |
| Promo photos (5 images) | 3 MB | 30 GB |
| Metadata & text | 0.1 MB | 1 GB |
| **Total** | **35 MB** | **350 GB** |

With 5.5 TB available, this is very achievable.

## Example Output

For an album like "Thriller" by Michael Jackson:

```
~/Music/_Album_Experience/
└── Michael Jackson - Thriller (1982)/
    ├── animated_artwork.mp4      # If available (newer remaster)
    ├── cover_front_3000x3000.jpg
    ├── cover_back.jpg
    ├── disc_label.jpg
    ├── booklet/
    │   ├── page_01.jpg
    │   ├── page_02.jpg
    │   └── ...
    ├── photos/
    │   ├── promo_01.jpg
    │   ├── thriller_video_still.jpg
    │   └── ...
    ├── metadata.json             # All structured data
    ├── context.md                # Historical writeup
    ├── credits.json              # Full production credits
    ├── reviews.json              # Critical reception
    └── album_page.html           # Generated experience page
```

## The Nostalgia Factor

This system recreates the experience of:

- **Opening a CD case** - Seeing all the artwork, reading the liner notes
- **Reading a magazine review** - Critical context and historical perspective
- **Browsing a record store** - Rich visual experience, discovery
- **Music documentaries** - Behind-the-scenes context and stories

Each album becomes a mini-museum exhibit, not just a collection of audio files.

## Next Steps

1. **Discogs Integration** - Add CD scan fetcher
2. **MusicBrainz Enrichment** - Full credits pipeline
3. **Wikipedia Context** - Historical writeups
4. **Album Page Generator** - HTML/React template system
5. **UI Integration** - Display in SAM terminal or web view

---

*"The album is not just music - it's an artifact, a time capsule, a piece of cultural history."*
