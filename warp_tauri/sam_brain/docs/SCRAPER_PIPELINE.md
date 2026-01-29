# SAM Scraper Pipeline Documentation

Comprehensive reference for SAM's entire data collection, conversion, and training pipeline.

**Last updated:** 2026-01-28

---

## 1. Architecture Overview

```
                         SAM SCRAPER PIPELINE
                         ====================

   +-----------+    +----------------+    +------------+
   | Web Sites |    | Legacy Rippers |    | Scrapy     |
   | (AO3,     |--->| (*_ripper.py)  |    | Spiders    |
   | Nifty,    |    | Simple scripts |    | (scraper_  |
   | WWD, etc) |    | with SQLite    |    |  system/)  |
   +-----------+    +-------+--------+    +-----+------+
                            |                   |
                            v                   v
                    +-------+--------+  +-------+--------+
                    | SQLite DBs     |  | PostgreSQL     |
                    | (per-scraper)  |  | (sam_scraper)  |
                    | *_index.db     |  | Unified store  |
                    +-------+--------+  +-------+--------+
                            |                   |
                            +--------+----------+
                                     |
                                     v
                    +----------------+------------------+
                    | build_training_data.py            |
                    | Reads all DBs + content files     |
                    | Converts to chat-format JSONL     |
                    | Applies mix ratios                |
                    | Splits train/val (90/10)          |
                    +----------------+------------------+
                                     |
                                     v
                    +----------------+------------------+
                    | sam_training_train.jsonl           |
                    | sam_training_val.jsonl             |
                    | /Volumes/David External/sam_training/
                    +----------------+------------------+
                                     |
                                     v
                    +----------------+------------------+
                    | perpetual_learner.py               |
                    | MLX LoRA fine-tuning               |
                    | Qwen2.5-1.5B base                  |
                    +----------------+------------------+
                                     |
                                     v
                    +----------------+------------------+
                    | SAM LoRA adapter                   |
                    | ~/ReverseLab/SAM/warp_tauri/       |
                    |   sam_brain/ (active model)        |
                    +-----------------------------------+
```

### Two Scraper Systems

SAM has **two parallel scraper systems** that coexist:

**System A: Legacy Rippers** (in `/Users/davidquinton/ReverseLab/SAM/scrapers/`)
- Individual Python scripts (`*_ripper.py`) -- one per site
- Each manages its own SQLite database for indexing and checkpoint
- Coordinated by `scraper_daemon.py` which runs ONE at a time
- Simpler, battle-tested, currently the primary system

**System B: Scrapy Spider System** (in `/Users/davidquinton/ReverseLab/SAM/scrapers/scraper_system/`)
- Unified Scrapy-based framework with 29 spider classes
- PostgreSQL backend for unified storage and deduplication
- Resource governor (RAM/CPU awareness, pauses for VLM)
- Includes its own daemon (`daemon.py`) with HTTP status API
- Broader scope: includes jobs, news, planning, error corpus spiders
- Orchestration via Prefect or Celery (configurable in `config/settings.py`)

Both systems feed into `build_training_data.py` for JSONL conversion.

### Third Component: Data Arsenal

**Data Arsenal** (`/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/data_arsenal.py`) is a separate real-time intelligence gathering system inside sam_brain itself. It scrapes trending content (GitHub, HN, Reddit, arXiv) and stores it in its own SQLite DB at `~/.sam/data_arsenal.db`. This is NOT part of the training pipeline -- it feeds SAM's live knowledge during conversations.

---

## 2. Storage Layout

### Current Locations (Updated January 2026)

All scraper output is migrating to `/Volumes/#1/SAM/scraper_archives/`. Fashion archives are at `/Volumes/#1/SAM/fashion_archives/`. Old `/Volumes/David External/` paths are symlinked to `#1`.

```
/Volumes/#1/
+-- SAM/
|   +-- scraper_archives/          # Primary scraper output
|   +-- fashion_archives/          # Fashion-specific content
|
+-- wwd_archive/                   # WWD (600GB+, already on #1)
+-- wmag_archive/                  # W Magazine (already on #1)
|   +-- articles/                  # Downloaded article JSON files
|   +-- wmag_index.db              # SQLite index
+-- vmag_archive/                  # V Magazine (already on #1)
|   +-- articles/
|   +-- vmag_index.db

/Volumes/David External/           # Legacy paths (many symlinked to #1)
+-- scraper_daemon/                # Daemon state
|   +-- daemon_state.db            # SQLite run history
|   +-- daemon.log                 # Daemon log
|   +-- daemon.pid                 # PID file
|
+-- nifty_archive/                 # 64,557 stories indexed, 1.3GB+
|   +-- stories/
|   +-- stories.db
|
+-- ao3_archive/                   # AO3 fiction, 1.1GB+
|
+-- literotica_archive/            # Literotica stories
|   +-- literotica_index.db
|
+-- dark_psych_archive/            # Dark psychology, 281MB+
|   +-- stories/
|   +-- dark_psych_index.db
|
+-- firstview_archive/             # 337K runway photos indexed, 220GB
|   +-- photos/
|   +-- firstview_index.db
|
+-- code_archive/                  # GitHub + StackOverflow code
+-- coding_training/               # Code collection DB
|   +-- code_collection.db
|
+-- apple_dev_archive/             # Apple dev content (GitHub, SO, cutting-edge)
|
+-- gq_esquire_archive/            # GQ + Esquire articles
+-- thecut_archive/                # The Cut articles
+-- interview_archive/             # Interview Magazine articles
+-- cai_archive/                   # Character.AI dumps (disabled)
|
+-- sam_training/                  # Final JSONL output directory
    +-- sam_training.jsonl          # Combined dataset
    +-- sam_training_train.jsonl    # 90% training split
    +-- sam_training_val.jsonl      # 10% validation split

/Volumes/David External/scraper_data/   # Scrapy system output
+-- raw_archives/                  # Raw scraped content
+-- processed/                     # Cleaned content
+-- training_data/                 # Scrapy-system training JSONL
```

### Storage Rules
- NEVER write large files to the internal SSD
- Models and training data go to `/Volumes/David External/` or `/Volumes/#1/`
- Raw content is NEVER deleted -- always preserved

---

## 3. Scraper Inventory

### Legend
- **Priority**: Lower number = runs first in daemon rotation
- **Rate limit**: Seconds between HTTP requests
- **Status**: Working / Stalled / Broken / Disabled

### 3.1 Roleplay / Fiction Content (Priority 1-10)

| ID | Script | Target Site | Priority | Rate Limit | Storage | Status |
|----|--------|------------|----------|------------|---------|--------|
| `nifty` | `nifty_ripper.py` | Nifty Archive | 1 | 3.0s | `/Volumes/David External/nifty_archive` | **Working** |
| `ao3` | `ao3_ripper.py` | Archive of Our Own | 2 | 5.0s | `/Volumes/David External/ao3_archive` | **Working** |
| `ao3_roleplay` | `ao3_roleplay_ripper.py` | AO3 (reader-insert) | 8 | 5.0s | `/Volumes/David External/ao3_archive` | **Working** |
| `literotica` | `literotica_ripper.py` | Literotica | 9 | 3.0s | `/Volumes/David External/literotica_archive` | **Stalled** |
| `dark_psych` | `dark_psych_ripper.py` | Dark psychology sources | 10 | 3.0s | `/Volumes/David External/dark_psych_archive` | **Working** |

**nifty** -- Gay male fiction and dialogue. Already fully indexed with 64,557 stories. No init needed. Downloads 50 stories per daemon batch. Estimated 1.3GB+ of content.

**ao3** -- M/M explicit fiction from Archive of Our Own. Already indexed. Downloads 20 works per batch. AO3 is strict on rate limiting (5s delay). Estimated 1.1GB+.

**ao3_roleplay** -- Reader-insert / 2nd person POV works from AO3. Shares storage with ao3. Does small index runs (100 per init). Downloads 10 per batch due to slow site.

**literotica** -- Interactive, dialogue-heavy fiction. Indexes 500 stories per init, downloads 30 per batch. **Known issue**: Anti-bot detection causes stalling. A Playwright-based alternative (`literotica_playwright.py`) exists for JS rendering.

**dark_psych** -- Dark psychology and manipulation dynamics content. Indexes 300 items per init, downloads 30 per batch. Estimated 281MB+ collected.

### 3.2 Fashion / Magazine Content (Priority 3-25)

| ID | Script | Target Site | Priority | Rate Limit | Storage | Status |
|----|--------|------------|----------|------------|---------|--------|
| `firstview` | `firstview_ripper.py` | FirstView.com | 3 | 0.3s | `/Volumes/David External/firstview_archive` | **Stalled** |
| `wwd` | `wwd_ripper.py` | Women's Wear Daily | 4 | 2.0s | `/Volumes/#1/wwd_archive` | **Working** |
| `wmag` | `wmag_ripper.py` | W Magazine | 21 | 2.0s | `/Volumes/David External/wmag_archive` | **Working** |
| `vmag` | `vmag_ripper.py` | V Magazine | 22 | 2.0s | `/Volumes/David External/vmag_archive` | **Working** |
| `gq_esquire` | `gq_esquire_ripper.py` | GQ & Esquire | 23 | 2.0s | `/Volumes/David External/gq_esquire_archive` | **Working** |
| `thecut` | `thecut_ripper.py` | The Cut (NY Mag) | 24 | 2.0s | `/Volumes/David External/thecut_archive` | **Working** |
| `interview_mag` | `interview_ripper.py` | Interview Magazine | 25 | 2.0s | `/Volumes/David External/interview_archive` | **Working** |

**firstview** -- Runway photography archive. Already indexed 337K photos. No init needed. Downloads 500 photos per batch at aggressive 0.3s rate limit. Estimated 220GB when complete. **Known issue**: Downloads stall intermittently -- currently being fixed.

**wwd** -- Women's Wear Daily, fashion industry news from 1967 to present. Already indexed 247K articles. Stored directly on `/Volumes/#1/` (not David External) due to size -- estimated 600GB+. Downloads 50 articles per batch.

**wmag, vmag, gq_esquire, thecut, interview_mag** -- Fashion and culture magazines. Each indexes 500 items per init, downloads 30 per batch at 2.0s rate limit.

### 3.3 Coding / Technical Content (Priority 5-13)

| ID | Script | Target Site | Priority | Rate Limit | Storage | Status |
|----|--------|------------|----------|------------|---------|--------|
| `apple_github` | `apple_dev_collector.py` | Apple-related GitHub repos | 5 | 1.0s | `/Volumes/David External/apple_dev_archive` | **Working** |
| `apple_stackoverflow` | `apple_dev_collector.py` | Apple SO questions | 6 | 1.0s | `/Volumes/David External/apple_dev_archive` | **Working** |
| `apple_cutting_edge` | `apple_dev_collector.py` | Swift Evolution, WWDC | 7 | 2.0s | `/Volumes/David External/apple_dev_archive` | **Working** |
| `code_github` | `code_collector.py` | GitHub repos/code | 11 | 1.0s | `/Volumes/David External/code_archive` | **Working** |
| `code_stackoverflow` | `code_collector.py` | Stack Overflow Q&A | 12 | 1.0s | `/Volumes/David External/code_archive` | **Working** |
| `code_prs` | `code_collector.py` | GitHub PR diffs | 13 | 1.0s | `/Volumes/David External/code_archive` | **Working** |

**apple_***: Three sub-scrapers using the same `apple_dev_collector.py` script, each with its own refresh schedule:
- `apple_github`: Weekly refresh (`refresh_days: 7`), fetches 200 repos per run
- `apple_stackoverflow`: Every 3 days (`refresh_days: 3`), fetches 200 Q&A per run
- `apple_cutting_edge`: Daily refresh (`refresh_days: 1`), catches Swift Evolution proposals and WWDC updates, 100 items per run

**code_***: Three sub-scrapers using `code_collector.py` for general coding knowledge:
- `code_github`: 100 repos per run
- `code_stackoverflow`: 100 Q&A per run
- `code_prs`: 50 PR diffs per run (before/after code + review comments)

Estimated combined code archive: 138MB+.

### 3.4 Other Content (Priority 31+)

| ID | Script | Target | Priority | Status |
|----|--------|--------|----------|--------|
| `cai_dumps` | `cai_dumps_finder.py` | Character.AI exports | 31 | **Disabled** |
| `flist` | `flist_ripper.py` | F-List character profiles | -- | **Broken** |
| `reddit_rp` | `reddit_roleplay_ripper.py` | Reddit RP subreddits | -- | Available |

**cai_dumps** -- Processes exported Character.AI conversation dumps. Disabled by default; enable if you have CAI dumps to process. Local processing only (0.5s rate limit).

**flist** -- F-List character profiles and RP logs. **Known issue**: Currently broken, not registered in the daemon.

**reddit_rp** -- Scrapes DirtyPenPals, EroticRolePlay, and similar subreddits. Has a ripper script but not registered in the legacy daemon.

### 3.5 Scrapy System Spiders (scraper_system/)

The Scrapy-based system has 29 spider classes across these categories. These are managed by the scraper_system daemon, NOT the legacy `scraper_daemon.py`:

**Fiction/Roleplay**: `ao3_spider`, `nifty_spider`, `literotica_spider`, `dark_psych_spider`, `flist_spider`, `reddit_spider`

**Fashion/Culture**: `wwd_spider`, `thecut_spider`, `gq_esquire_spider`

**Code/Technical**: `github_spider`, `stackoverflow_spider`, `devto_spider`, `docs_spider`, `uiux_spider`

**Apple Ecosystem**: `apple_spider`, `swift_spider`, `wwdc_spider`

**Real-Time**: `realtime_spider` (GitHub events, HN, Reddit streams)

**Error Corpus**: `error_corpus_spider`

**Jobs**: `jobs_spider` (CalCareers, resumes, cover letters, SOQ examples)

**News**: `news_spider` (RSS aggregation, bias ratings, full article fetcher)

**Planning/Architecture**: `curriculum_spider`, `architecture_spider`, `templates_spider`, `planning_qa_spider`, `specs_spider`

All spiders inherit from `base_spider.py` (class `BaseSpider`) which provides:
- Automatic database integration (PostgreSQL)
- Progress tracking and resume support
- Rate limiting
- Resource checking (RAM/CPU)
- Logging

---

## 4. Daemon Configuration

### Legacy Daemon (`scraper_daemon.py`)

**Location**: `/Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py`

#### Starting and Stopping

```bash
# Foreground (see output live)
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py start

# Background (fork to daemon)
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py start --bg

# Check status (shows last run per scraper, items processed)
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py status

# Stop daemon
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py stop
```

#### LaunchAgent Integration

Install a macOS launchd plist for automatic restart on crash:

```bash
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_daemon.py install
```

This creates: `~/Library/LaunchAgents/com.sam.scraper-daemon.plist`

Then load with:
```bash
launchctl load ~/Library/LaunchAgents/com.sam.scraper-daemon.plist
launchctl start com.sam.scraper-daemon
```

The plist is configured with `KeepAlive > Crashed = true`, so launchd will restart the daemon if it crashes. `ThrottleInterval` is 60 seconds (minimum time between restarts).

#### Priority System

Scrapers are sorted by a scoring function:
```
score = priority - (hours_since_last_run * 0.1)
```

Lower score runs first. Scrapers that have not run recently get a bonus. Scrapers with a `refresh_days` setting get a massive priority boost (`-100`) when they are due for refresh.

Priority ranges:
- 1-10: Roleplay content + high-value fashion (FirstView, WWD)
- 5-7: Apple dev content (with refresh schedules)
- 11-13: General coding content
- 21-25: Fashion magazines
- 31+: Other/optional content

#### State Tracking

The daemon stores all state in SQLite at `/Volumes/David External/scraper_daemon/daemon_state.db`:
- `runs` table: Full history of every scraper run (start time, end time, items processed, status, errors)
- `daemon_state` table: Key-value store for daemon metadata

#### Execution Model

- Runs ONE scraper at a time (safe for 8GB RAM)
- Each scraper batch has a 30-minute timeout
- After each batch, sleeps for `max(rate_limit * 10, 30)` seconds
- If 5 consecutive errors occur, sleeps 10 minutes then resets error count
- Checks that storage path parent directory exists before running (skips if external drive not mounted)

#### Init System

Scrapers with an `init_command` need initialization (indexing) before downloading. The daemon checks if init has been completed (status `init_complete` in the runs table). Init has a 5-minute timeout.

### Scrapy System Daemon (`scraper_system/daemon.py`)

**Location**: `/Users/davidquinton/ReverseLab/SAM/scrapers/scraper_system/daemon.py`

```bash
# Start daemon
python -m scraper_system.daemon

# Custom status port
python -m scraper_system.daemon --port 8089

# Add a scraper to the queue
python -m scraper_system.daemon --add ao3

# Check status
python -m scraper_system.daemon --status
```

Features:
- HTTP status API for monitoring
- Queue management (multiple scrapers, one at a time)
- Resource-aware: pauses when RAM is low or VLM is running
- States: idle, queued, starting, running, rate_limited, paused_low_ram, paused_vlm, completed, failed, waiting_retry
- Tracks: current page, items scraped, bytes downloaded, current URL, ETA

#### Scrapy System CLI

```bash
python -m scraper_system status           # Show system status
python -m scraper_system list             # List all scrapers
python -m scraper_system run <name>       # Run a scraper now
python -m scraper_system schedule <name> <cron>  # Schedule a scraper
python -m scraper_system pause            # Pause all scrapers
python -m scraper_system resume           # Resume all scrapers
python -m scraper_system stats            # Show statistics
python -m scraper_system history [name]   # Show job history
python -m scraper_system resources        # Show resource status
python -m scraper_system init-db          # Initialize database
```

#### Resource Governor

The Scrapy system includes a resource governor (`core/resource_governor.py`) that:
- Monitors available RAM (minimum 1GB free required)
- Limits to 1 concurrent spider (configurable, `MAX_CONCURRENT_SPIDERS`)
- Pauses scraping when these processes are detected: `mlx_vlm`, `ollama`, `python.*vlm`

#### Scheduling (Scrapy System)

Configured in `config/settings.py`:
```
ao3:        0 2 * * *    (2 AM daily)
nifty:      0 3 * * *    (3 AM daily)
literotica: 0 4 * * *    (4 AM daily)
dark_psych: 0 5 * * *    (5 AM daily)
reddit:     0 1 * * *    (1 AM daily)
github:     0 0 * * 0    (midnight Sunday)
wwd:        0 2 * * 6    (2 AM Saturday)
```

Default for unspecified scrapers: `0 2 * * *` (2 AM daily).

---

## 5. Conversion Pipeline

### `build_training_data.py`

**Location**: `/Users/davidquinton/ReverseLab/SAM/scrapers/build_training_data.py`

This script reads content from all scraper databases and content directories, converts it into chat-format JSONL suitable for MLX instruction tuning.

#### Input Sources

| Source | Database Path | Content Directory |
|--------|--------------|-------------------|
| vmag | `/Volumes/#1/vmag_archive/vmag_index.db` | `/Volumes/#1/vmag_archive/articles` |
| wmag | `/Volumes/#1/wmag_archive/wmag_index.db` | `/Volumes/#1/wmag_archive/articles` |
| wwd | `/Volumes/#1/wwd_archive/wwd_index.db` | `/Volumes/#1/wwd_archive/articles` |
| dark_psych | `/Volumes/David External/dark_psych_archive/dark_psych_index.db` | `/Volumes/David External/dark_psych_archive/stories` |
| code | `/Volumes/David External/coding_training/code_collection.db` | -- (inline in DB) |
| firstview | `/Volumes/David External/firstview_archive/firstview_index.db` | `/Volumes/David External/firstview_archive/photos` |
| nifty | `/Volumes/David External/nifty_archive/stories.db` | `/Volumes/David External/nifty_archive/stories` |
| literotica | `/Volumes/David External/literotica_archive/literotica_index.db` | -- |

#### Output Format

Each record in the JSONL file is a chat-format conversation:

```json
{
  "messages": [
    {"role": "system", "content": "You are SAM, a confident and charming AI assistant..."},
    {"role": "user", "content": "Summarize this fashion article:\n\n..."},
    {"role": "assistant", "content": "This piece explores..."}
  ],
  "source": "vmag",
  "category": "fashion"
}
```

The system prompt used for all examples:
> "You are SAM, a confident and charming AI assistant. You're knowledgeable about fashion, coding, creative writing, and roleplay. You communicate with wit, occasional flirtation, and genuine helpfulness. You're direct but warm, and you enjoy intellectual banter."

#### Training Example Types

**Fashion content** (vmag, wmag, wwd) generates three example types per article:
1. **Summary**: "Summarize this fashion article:" with extracted key sentences
2. **Style advice**: "What are the key style takeaways from..." with extracted actionable phrases
3. **Continuation**: "Continue this fashion article:" with first 2 paragraphs as input, next 2 as output

**Dark psychology content** generates two types:
1. **Story continuation**: Setup paragraphs as input, continuation as output, tagged with dark themes
2. **Dialogue extraction**: Dialogue lines extracted via regex, formatted as dialogue-writing examples

**Code content** generates two types:
1. **Code completion**: "Write a {language} function: {title}" with code as output
2. **Code improvement**: PR diffs with "Improve this code based on feedback:" using before/after code

#### Mix Ratios

```
Fashion:     25%
Coding:      25%
Roleplay:    30%
Dark Psych:  20%
```

Per-source caps: 3,000 examples per fashion source, 5,000 dark psychology, 10,000 code.

#### Running the Pipeline

```bash
# Full build (default: 50,000 max examples)
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/build_training_data.py build

# Custom output path
python3 build_training_data.py build --output /path/to/output.jsonl

# Limit total examples
python3 build_training_data.py build --max 10000

# Skip categories
python3 build_training_data.py build --no-fashion --no-code --no-dark

# Check available data sources and counts
python3 build_training_data.py stats
```

#### Output Files

Default output directory: `/Volumes/David External/sam_training/`

| File | Description |
|------|-------------|
| `sam_training.jsonl` | Combined dataset (all examples with source/category metadata) |
| `sam_training_train.jsonl` | 90% split for training (messages only, no metadata) |
| `sam_training_val.jsonl` | 10% split for validation (messages only, no metadata) |

The train/val splits strip the `source` and `category` fields -- they only contain `messages` arrays. This is the format expected by MLX LoRA fine-tuning.

---

## 6. How to Add a New Scraper

### Option A: Legacy Ripper (Simpler)

1. **Create the script** at `/Users/davidquinton/ReverseLab/SAM/scrapers/yoursite_ripper.py`

   Follow the existing pattern:
   - Accept CLI commands: `index` (discover URLs) and `download` (fetch content)
   - Use SQLite for indexing and checkpoint tracking
   - Accept `--limit N` flag to control batch size
   - Store content in a dedicated directory on external storage
   - Print progress to stdout (the daemon captures it)
   - Respect rate limits with `time.sleep()`
   - Return exit code 0 on success

2. **Register in the daemon** by adding an entry to the `SCRAPERS` dict in `scraper_daemon.py`:

   ```python
   "yoursite": {
       "script": "yoursite_ripper.py",
       "init_command": ["index", "--limit", "500"],  # or None if pre-indexed
       "command": ["download", "--limit", "30"],
       "storage": "/Volumes/#1/SAM/scraper_archives/yoursite_archive",
       "rate_limit": 2.0,
       "priority": 15,       # Pick a priority slot
       "enabled": True,
       "category": "roleplay",  # or "fashion", "coding", "other"
       "refresh_days": 7,    # Optional: auto-refresh schedule
   },
   ```

3. **Add to build_training_data.py** if the content needs to be converted to training data. Add the database path to `CONFIG["sources"]` and optionally the content directory to `CONFIG["content_dirs"]`.

4. **Storage convention**: `/Volumes/#1/SAM/scraper_archives/yoursite_archive/` for new scrapers.

### Option B: Scrapy Spider (More Powerful)

1. **Create the spider** at `/Users/davidquinton/ReverseLab/SAM/scrapers/scraper_system/spiders/yoursite_spider.py`

   ```python
   from .base_spider import BaseSpider
   from ..storage.database import ScrapedItem

   class YourSiteSpider(BaseSpider):
       name = "yoursite_spider"
       source = "yoursite"
       start_urls = ["https://yoursite.com"]

       def parse(self, response):
           yield ScrapedItem(
               source=self.source,
               url=response.url,
               title=response.css("h1::text").get(),
               content=response.css("article::text").getall(),
           )
   ```

2. **Register in settings** by adding to `DATA_SOURCES` in `config/settings.py`:

   ```python
   "yoursite": {
       "name": "Your Site",
       "type": "fiction",
       "spider": "yoursite_spider",
       "priority": 2,
       "enabled": True,
   },
   ```

3. Add a rate limit entry in the `RATE_LIMITS` dict if needed.

---

## 7. How to Update / Refresh Existing Archives

### Incremental Updates (Legacy Daemon)

The legacy daemon handles incremental updates automatically:
1. Each scraper's SQLite database tracks what has been indexed and downloaded
2. The `download` command only fetches items not yet marked as `downloaded = 1`
3. The `index` command discovers new URLs and adds them (existing URLs are skipped via dedup)

To force a re-index of a specific scraper:

```bash
# Run index command directly
cd /Users/davidquinton/ReverseLab/SAM/scrapers
python3 nifty_ripper.py index --limit 1000

# Then run download
python3 nifty_ripper.py download --limit 50
```

### Refresh Scheduling (Daemon)

Scrapers with `refresh_days` set in the daemon config are automatically re-run on schedule:
- `apple_github`: Every 7 days
- `apple_stackoverflow`: Every 3 days
- `apple_cutting_edge`: Every day

When a scraper's `refresh_days` threshold is exceeded, it gets a massive priority boost (`-100` to its score), ensuring it runs before anything else.

### Checkpoint Resume

If the daemon crashes or is stopped mid-scrape:
- The daemon records run start/end in SQLite
- The scraper's own SQLite tracks per-item download status
- On restart, the daemon picks up where it left off -- only undownloaded items are attempted
- The daemon's `KeepAlive` launchd config auto-restarts on crash

### Manual Refresh

```bash
# Rebuild training data after new content is scraped
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/build_training_data.py build

# Check what data is available before building
python3 /Users/davidquinton/ReverseLab/SAM/scrapers/build_training_data.py stats
```

---

## 8. Known Issues

### FirstView Stalling
- **Status**: Being fixed
- **Symptom**: Downloads stall intermittently after processing some photos
- **Details**: 337K photos indexed, 220GB estimated total. Rate limit is aggressive (0.3s). Stalling may be related to connection timeouts or server-side throttling.
- **Priority**: 3 (high) because it is already indexed and just needs downloading

### Literotica Anti-Bot Detection
- **Status**: Stalled
- **Symptom**: Standard HTTP requests get blocked by anti-bot measures
- **Workaround**: A Playwright-based version (`literotica_playwright.py`) exists that renders JavaScript, but is heavier on resources
- **Priority**: 9 in daemon

### F-List Broken
- **Status**: Broken
- **Symptom**: `flist_ripper.py` exists but is not registered in the legacy daemon and is not functional
- **Details**: Was intended to scrape character profiles and RP logs from F-List

### Path Migration to #1
- **Status**: In progress
- **Details**: Scraper output is migrating from `/Volumes/David External/` to `/Volumes/#1/SAM/scraper_archives/`. Some paths (vmag, wmag, wwd) are already on #1. Others still reference David External. Old paths should be symlinked during migration.
- **Impact**: `build_training_data.py` CONFIG paths need updating as archives move. Currently the config has a mix of #1 and David External paths.

### Duplicate Daemon Systems
- **Status**: Architectural debt
- **Details**: Two daemon systems exist (legacy `scraper_daemon.py` and Scrapy `scraper_system/daemon.py`). The legacy daemon is simpler and currently primary. The Scrapy system is more powerful but adds PostgreSQL and Redis dependencies. They should not both run simultaneously.

### Build Pipeline Limitations
- `build_training_data.py` does not include nifty or literotica content in its loader functions (only fashion, dark_psych, and code are actively loaded despite database paths being configured)
- Roleplay training examples come only from `dark_psych` stories, not from the larger AO3 or Nifty archives
- Fashion content loader depends on specific SQLite column names (`file_path`, `content_path`, `local_path`) which may not match all scraper DB schemas

---

## 9. Data Arsenal (sam_brain)

### Overview

**File**: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/data_arsenal.py`

The Data Arsenal is a **separate system** from the scraper pipeline. It lives inside sam_brain and provides SAM with real-time intelligence during conversations. It does NOT feed into the training pipeline.

### How It Works

The `DataArsenal` class provides:
- Web scraping with rate limiting (trafilatura or BeautifulSoup fallback)
- Content extraction and parsing (code blocks, links, patterns)
- Full-text search (SQLite FTS5)
- Deduplication via content hashing
- Scheduled refreshes per source

Data is stored in SQLite at `~/.sam/data_arsenal.db` with tables:
- `items`: All scraped content (URL-deduplicated)
- `patterns`: Extracted architectural/design patterns
- `scrape_log`: History of all scrape runs
- `items_fts`: Full-text search index

### Pre-Configured Sources

| Name | Type | URL | Refresh | Description |
|------|------|-----|---------|-------------|
| `github_trending` | GitHub | github.com/trending | 12h | Trending repositories |
| `hackernews_front` | Hacker News | news.ycombinator.com | 6h | Top stories via Firebase API |
| `ollama_releases` | GitHub | ollama/ollama/releases | 24h | Ollama release notes |
| `tauri_releases` | GitHub | tauri-apps/tauri/releases | 24h | Tauri release notes |
| `arxiv_ai` | arXiv | arxiv.org/list/cs.AI/recent | 24h | Recent AI papers |
| `reddit_localllama` | Reddit | r/LocalLLaMA | 12h | Local LLM community |
| `warp_docs` | Documentation | docs.warp.dev | 168h (weekly) | Warp terminal docs |

### CLI Usage

```bash
cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain

python3 data_arsenal.py sources              # List all configured sources
python3 data_arsenal.py scrape <source>      # Scrape a specific source
python3 data_arsenal.py scrape-all           # Scrape all sources
python3 data_arsenal.py search <query>       # Full-text search across all content
python3 data_arsenal.py code <query>         # Search code examples specifically
python3 data_arsenal.py recent [source]      # Recent items (optionally filtered)
python3 data_arsenal.py stats                # Show statistics (counts, DB size)
```

### Adding Custom Sources

```python
from data_arsenal import DataArsenal, SourceConfig, SourceType, ExtractionType

arsenal = DataArsenal()
arsenal.add_custom_source(SourceConfig(
    name="My Source",
    source_type=SourceType.WEBSITE,
    url="https://example.com",
    extraction_types=[ExtractionType.ARTICLE],
    rate_limit_ms=2000,
    max_pages=10,
    refresh_hours=24,
))
result = arsenal.scrape_source("My Source")
```

### Integration with SAM

The Data Arsenal is accessed via the orchestrator's `DATA` route. When SAM receives a data/intelligence query, the orchestrator delegates to `data_arsenal.py` for search, scrape, or stats operations. Results are returned inline during conversations -- they are not persisted into the training data.
