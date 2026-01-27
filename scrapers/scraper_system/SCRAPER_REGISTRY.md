# SAM Scraper Registry

Master list of all data sources for SAM training. This file is the source of truth.

## Purpose

Train SAM with:
- **Personality**: Confident, cocky, flirty male voice
- **Dark Psychology**: Manipulation, persuasion, power dynamics
- **Fashion/Culture**: Style, trends, cultural awareness
- **Code**: Technical competence
- **Creative Writing**: Dialogue, character voice, roleplay

---

## EXISTING SCRAPERS (Built)

### Fiction/Roleplay

| ID | Name | File | Purpose | Est. Size |
|----|------|------|---------|-----------|
| `ao3` | Archive of Our Own | `ao3_ripper.py` | M/M explicit fiction, character voice | 1.1GB+ |
| `ao3_roleplay` | AO3 Reader-Insert | `ao3_roleplay_ripper.py` | 2nd person POV, interactive | — |
| `nifty` | Nifty Archive | `nifty_ripper.py` | Gay male fiction, dialogue | 1.3GB+ |
| `literotica` | Literotica | `literotica_ripper.py` | Interactive, dialogue-heavy | — |
| `literotica_pw` | Literotica (Playwright) | `literotica_playwright.py` | JS rendering version | — |
| `dark_psych` | Dark Psychology | `dark_psych_ripper.py` | Manipulation, power dynamics | 281MB+ |
| `flist` | F-List | `flist_ripper.py` | Character profiles, RP logs | — |
| `reddit_rp` | Reddit Roleplay | `reddit_roleplay_ripper.py` | DirtyPenPals, EroticRolePlay | — |

### Fashion/Culture

| ID | Name | File | Purpose | Est. Size |
|----|------|------|---------|-----------|
| `wwd` | Women's Wear Daily | `wwd_ripper.py` | Fashion industry news (1967-now) | 600GB+ |
| `wmag` | W Magazine | `wmag_ripper.py` | Fashion/culture articles | — |
| `vmag` | V Magazine | `vmag_ripper.py` | Fashion/culture | — |
| `thecut` | The Cut | `thecut_ripper.py` | Essays, sex diaries, culture | — |
| `gq_esquire` | GQ & Esquire | `gq_esquire_ripper.py` | Male voice, style, interviews | — |
| `interview` | Interview Magazine | `interview_ripper.py` | Celebrity interviews | — |
| `firstview` | FirstView | `firstview_ripper.py` | Runway photos (800K images) | 220GB |

### Code/Technical

| ID | Name | File | Purpose | Est. Size |
|----|------|------|---------|-----------|
| `github` | GitHub | `code_collector.py` | Repos, PRs, Stack Overflow | 138MB+ |

### Training Data

| ID | Name | File | Purpose |
|----|------|------|---------|
| `instruction` | Instruction Sets | `download_instruction_data.py` | Alpaca, Dolly |
| `high_impact` | High Impact | `high_impact_datasets.py` | GSM8K, ARC, personality |
| `builder` | Training Builder | `build_training_data.py` | Convert all to JSONL |

---

## NEW SCRAPERS (To Build)

### Dark Psychology / Persuasion

| ID | Name | Source | Purpose | Difficulty |
|----|------|--------|---------|------------|
| `robert_greene` | Robert Greene Books | EPUBs/PDFs | 48 Laws, Art of Seduction, Mastery | Easy |
| `cialdini` | Cialdini - Influence | EPUB/PDF | Persuasion psychology | Easy |
| `carnegie` | Dale Carnegie | EPUB/PDF | How to Win Friends, social manipulation | Easy |
| `chris_voss` | Chris Voss | EPUB/PDF/YouTube | FBI negotiation tactics | Medium |
| `sales_training` | Sales Training | Various | Objection handling, closing | Medium |
| `pickup_forums` | Seduction Forums | Web scrape | Social dynamics, confidence | Medium |
| `bdsm_guides` | BDSM Negotiation | Web scrape | Power exchange, dominance | Medium |
| `con_artist` | Con Artist Docs | Transcripts | Social engineering case studies | Hard |

### Personality / Voice

| ID | Name | Source | Purpose | Difficulty |
|----|------|--------|---------|------------|
| `standup` | Stand-up Comedy | Transcripts | Wit, timing, delivery | Medium |
| `spy_fiction` | Spy/Heist Fiction | EPUBs | Charm, deception, intelligence | Easy |
| `charisma_cmd` | Charisma on Command | YouTube | Social skills breakdowns | Medium |
| `lex_fridman` | Lex Fridman Podcast | Transcripts | Long-form intelligent conversation | Medium |
| `debate` | Debate Transcripts | Web scrape | Argumentation, wit under pressure | Medium |
| `political` | Political Speeches | Archives | Persuasion, rhetoric | Easy |

### Fiction (Additional)

| ID | Name | Source | Purpose | Difficulty |
|----|------|--------|---------|------------|
| `wattpad` | Wattpad | Web scrape | Dialogue-heavy fiction | Medium |
| `royal_road` | Royal Road | Web scrape | Serial fiction, consistent voice | Easy |
| `qq` | QuestionableQuesting | Web scrape | Adult interactive fiction | Medium |
| `spacebattles` | SpaceBattles/SV | Web scrape | Creative writing forums | Medium |
| `chyoa` | CHYOA | Web scrape | Choose your own adventure (adult) | Medium |

### Books (Bulk)

| ID | Name | Source | Purpose | Difficulty |
|----|------|--------|---------|------------|
| `epub_library` | EPUB Library | Local files | Process existing ebook collection | Easy |
| `pdf_library` | PDF Library | Local files | Process existing PDFs | Easy |
| `audiobook_transcripts` | Audiobook Transcripts | Whisper | Transcribe audiobooks | Medium |

---

## DATA MIX RATIOS (Target)

| Category | Target % | Sources |
|----------|----------|---------|
| Fiction/Roleplay | 30% | AO3, Nifty, Literotica, Wattpad, etc. |
| Dark Psychology | 20% | Dark psych, Robert Greene, Cialdini, pickup |
| Fashion/Culture | 15% | WWD, magazines, The Cut |
| Personality/Voice | 15% | Standup, podcasts, spy fiction |
| Code | 15% | GitHub, Stack Overflow |
| Instruction | 5% | Alpaca, Dolly, GSM8K |

---

## STORAGE LOCATIONS

```
/Volumes/David External/
├── scraper_data/
│   ├── raw_archives/          # Original scraped content
│   │   ├── ao3/
│   │   ├── nifty/
│   │   ├── dark_psych/
│   │   └── ...
│   ├── processed/             # Cleaned content
│   └── training_data/         # Final JSONL for training
│
├── ao3_archive/               # Legacy location
├── nifty_archive/             # Legacy location
└── ...

/Volumes/#1/
├── wwd_archive/               # Large media (600GB+)
├── wmag_archive/
└── vmag_archive/
```

---

## PRIORITY ORDER

Build and run in this order:

### Phase 1: Core Fiction (Highest Value)
1. `ao3` - Already have 1.1GB
2. `nifty` - Already have 1.3GB
3. `literotica` - Started
4. `dark_psych` - Started

### Phase 2: Dark Psychology
5. `robert_greene` - Books (easy)
6. `cialdini` - Books (easy)
7. `carnegie` - Books (easy)
8. `chris_voss` - Books + YouTube

### Phase 3: Personality
9. `standup` - Comedy transcripts
10. `spy_fiction` - EPUBs
11. `lex_fridman` - Podcast transcripts
12. `charisma_cmd` - YouTube

### Phase 4: Additional Fiction
13. `wattpad`
14. `royal_road`
15. `qq`
16. `reddit_rp`

### Phase 5: Culture/Fashion
17. `thecut`
18. `gq_esquire`
19. `interview`
20. `wwd` (large, run overnight)

### Phase 6: Code
21. `github` - Expand existing

---

## NOTES

- All scrapers respect rate limits
- Pause when RAM < 2GB
- Pause when VLM/Ollama running
- Store raw + processed (never delete raw)
- Deduplicate across sources
- Track progress in PostgreSQL
