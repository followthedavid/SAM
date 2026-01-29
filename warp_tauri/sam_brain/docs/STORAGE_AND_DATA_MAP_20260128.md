# SAM Ecosystem Storage & Data Map

**Date:** 2026-01-28
**Author:** Automated audit via Claude Code
**Purpose:** Complete inventory of all drives, data, projects, training resources, services, databases, and cleanup opportunities across the entire SAM ecosystem.

---

## Changes from 2026-01-27

### Phase 1: Cleanup Deletes (195 GB freed)

| Item | Location | Size Freed | Status |
|------|----------|-----------|--------|
| $RECYCLE.BIN | /Volumes/# 2/ | 109 GB | Deleted |
| docker_backup_deleteme | /Volumes/Untitled/ | 38 GB | Deleted |
| Ollama cache | /Volumes/Plex/DevSymlinks/ollama/ | 14 GB | Deleted |
| ReverseLab_Cleanup_Backup | /Volumes/Applications/ | 33 GB | Deleted (hidden macOS metadata remains) |
| Xcode DerivedData | ~/Library/Developer/Xcode/DerivedData/ | 840 MB | Deleted |

### Phase 2: New Directory Structure on #1

`/Volumes/#1/SAM/` created with organized subdirectories:

```
/Volumes/#1/SAM/
  scraper_archives/      -- nifty, ao3, literotica, dark_psych, firstview,
                            gq_esquire, thecut, interview, apple_dev, code archives
  fashion_archives/      -- vmag, wmag, wwd (reorganized from #1 root)
  training_data/         -- SAM_master_training, chatgpt_training,
                            instruction_datasets, chatgpt_export
  training_backups/      -- SAM_Backup
  voice_data/            -- SAM_Voice_Training, RVC_logs
  scraper_daemon/        -- daemon state (moved from David External)
  dead_code_archive/     -- 59 files, ~25K lines archived
```

### Phase 3: Data Moves (David External to #1)

All scraper archives, training data, voice data, and scraper daemon state moved from David External to `/Volumes/#1/SAM/`. Symlinks created at old David External locations for backward compatibility.

Estimated ~70 GB moved to #1.

### Phase 4: Code Path Updates

| File | Change |
|------|--------|
| scraper_daemon.py | All 17 storage paths updated from David External to #1/SAM/ |
| build_training_data.py | All source/content paths updated to #1/SAM/ |
| code_indexer.py | DB renamed to code_index_semantic.db to avoid dual-module conflict |

### Phase 5: Code Fixes

| File | Fix |
|------|-----|
| perpetual_learner.py | MAX_DEDUP_HASHES=10000 with LRU pruning (was unbounded) |
| firstview_ripper.py | Complete rewrite for 8M photo catalog support |
| code_indexer.py | Fixed dual-module DB conflict (renamed DB) |

---

## Table of Contents

1. [Drive Overview](#1-drive-overview)
2. [Training Data Inventory](#2-training-data-inventory)
3. [Project Inventory](#3-project-inventory)
4. [Active Services](#4-active-services)
5. [Database Inventory](#5-database-inventory)
6. [Cleanup Opportunities](#6-cleanup-opportunities)
7. [Critical Issues](#7-critical-issues)

---

## 1. Drive Overview

### Summary Table

| Drive | Total | Free | Used | Usage | Primary Purpose |
|-------|-------|------|------|-------|-----------------|
| Internal SSD | 228 GB | 128 GB | 100 GB | 44% | Code, configs, system |
| David External | 7.3 TB | 3.47 TB | 3.83 TB | 52% | Music, photos, courses (training data moved to #1) |
| #1 | 7.3 TB | 5.73 TB | 1.57 TB | 22% | SAM data hub, fashion archives, backups |
| # 2 | 7.3 TB | 4.31 TB | 2.99 TB | 41% | Adult content, Tidal |
| Plex | 223 GB | 92 GB | 131 GB | **59%** | DevSymlinks, SSOT, Plex server |
| Applications | 223 GB | 196 GB | 27 GB | 12% | Apps, SAM models |
| Untitled | 1.8 TB | ~1.80 TB | ~0 GB | ~0% | Empty |
| Movies | 13 TB | -- | -- | -- | Media library (not SAM-related) |
| TV | 13 TB | -- | -- | -- | Media library (not SAM-related) |
| Music | 7.3 TB | -- | -- | -- | Media library (not SAM-related) |
| Games | 7.3 TB | -- | -- | -- | Media library (not SAM-related) |

> **Plex drive improved** from 66% to ~59% after ollama cache deletion (14 GB freed).
> **Applications drive improved** from 27% to ~12% after ReverseLab_Cleanup_Backup deletion (33 GB freed).
> **# 2 improved** from 42% to ~41% after $RECYCLE.BIN deletion (109 GB freed).

---

### Internal SSD (228 GB total, ~128 GB free)

| Path | Size | Contents |
|------|------|----------|
| /Users/davidquinton/ | 19 GB | Development code, configs, system libraries |

**Storage Strategy:** Code and configs ONLY. No large files. Models, training data, caches, and venvs belong on external drives.

---

### /Volumes/David External (7.3 TB total, ~3.47 TB free)

Primary archival storage. Training data and scraper archives have been **moved to #1** with symlinks remaining at old locations.

| Path / Category | Size | Details |
|-----------------|------|---------|
| **Music - Lossless** | 1.5 TB | High-quality audio collection |
| **Music - Lossy** | 209 GB | Compressed audio collection |
| **Music - Unorganized** | 434 GB | Needs sorting/dedup |
| **Photos** | 87 GB | Personal photo archive |
| **Documents** | 2.5 GB | Personal documents |
| **Courses** | 129 GB | Educational content |
| **Symlinks to #1/SAM/** | -- | Training data, scraper archives, voice data, daemon state (all moved to #1) |

---

### /Volumes/#1 (7.3 TB total, ~5.73 TB free)

Now the **primary SAM data hub** after 2026-01-28 reorganization.

| Path / Category | Size | Details |
|-----------------|------|---------|
| **SAM/ (total)** | **~187 GB** | All SAM data consolidated here |
| SAM/scraper_archives/ | ~2.8 GB | nifty, ao3, literotica, dark_psych, firstview, gq_esquire, thecut, interview, apple_dev, code archives |
| SAM/fashion_archives/ | 117 GB | vmag, wmag, wwd (reorganized from #1 root) |
| SAM/training_data/ | ~5 GB | SAM_master_training, chatgpt_training, instruction_datasets, chatgpt_export |
| SAM/training_backups/ | ~37 GB | SAM_Backup (all_training.jsonl) |
| SAM/voice_data/ | ~27 GB | SAM_Voice_Training (8.7 GB), RVC_logs (18 GB) |
| SAM/scraper_daemon/ | -- | Daemon state files |
| SAM/dead_code_archive/ | -- | 59 files, ~25K lines of archived dead code |
| **Plex Brain Backups** | 35 GB | Plex metadata/database backups |
| **AI Projects** | 10 GB | Miscellaneous AI project files |
| **Content Archives** | -- | Various archived content |

---

### /Volumes/# 2 (7.3 TB total, ~4.31 TB free)

| Path / Category | Size | Details |
|-----------------|------|---------|
| Adult Content | 2.5 TB | Primary content collection |
| Tidal | 234 GB | Music downloads |
| StashGrid | 144 GB | Stash metadata/grid |
| Stash | 120 GB | Stash application data |

> $RECYCLE.BIN (109 GB) deleted 2026-01-28.

---

### /Volumes/Plex (223 GB total, ~92 GB free) -- Improved from 66% to 59%

| Path / Category | Size | Details |
|-----------------|------|---------|
| **Plex Media Server** | ~120 GB | Plex application + metadata |
| **DevSymlinks/ (total)** | **~87 GB** | Development symlink targets |
| - huggingface/ | 24 GB | Model cache |
| - venvs/ | 20 GB | 5 voice venvs + 2 brain venvs |
| - stash_data/ | 15 GB | Stash application data |
| - cargo builds | ~10 GB | Rust compilation artifacts |
| - RVC_assets/ | 2.3 GB | Voice training assets |
| - warp_data/ | 322 MB | Live Warp terminal database |
| - Various caches | ~15 GB | pip, npm, etc. |
| **DockerData** | 22 GB | Docker images/volumes |
| **SSOT/** | 281 MB | Single Source of Truth docs |

> Ollama cache (14 GB) deleted 2026-01-28.

---

### /Volumes/Applications (223 GB total, ~196 GB free)

| Path / Category | Size | Details |
|-----------------|------|---------|
| Xcode.app | 12 GB | Apple development tools |
| SAM/ | 5.2 GB | Models, data, scrapers, voice, adapters |
| - sam_brain_data/ | 245 MB | perpetual_merged.jsonl (ACTIVE) |
| claude_archives/ | 1.3 GB | 127 conversation files |
| DAZ_3D/ | 2.3 GB | 3D modeling assets |

> ReverseLab_Cleanup_Backup (33 GB) deleted 2026-01-28. Hidden macOS metadata may remain.

---

### /Volumes/Untitled (1.8 TB, empty)

docker_backup_deleteme (38 GB) deleted 2026-01-28. Drive is now effectively empty.

---

### Media Drives (not SAM-related)

| Drive | Size | Purpose |
|-------|------|---------|
| /Volumes/Movies | 13 TB | Plex movie library |
| /Volumes/TV | 13 TB | Plex TV library |
| /Volumes/Music | 7.3 TB | Plex music library |
| /Volumes/Games | 7.3 TB | Game storage |

---

## 2. Training Data Inventory

### Pipeline Status at a Glance

```
RAW SOURCES ──> CONVERSION ──> JSONL ──> TRAINING
    │               │            │          │
    │  AO3 (1.1GB)  │            │          │
    │  Dark Psych    │  NOT DONE  │          │
    │  Fashion 117GB │            │          │
    │  Warp 322MB    │            │          │
    │  Claude 165MB  │  27% done  │          │
    │                │            │          │
    │                │   SAM_master ─────> perpetual_learner
    │                │   ChatGPT     ────> perpetual_learner
    │                │   Instruction ────> (available)
    │                │   Nifty       ────> (available)
    │                │            │          │
    │                │            │   perpetual_merged.jsonl (245MB)
    │                │            │   90% coding / 10% roleplay
    │                │            │   *** IMBALANCED ***
```

> All raw sources and converted JSONL now stored on #1 at `/Volumes/#1/SAM/`.
> Symlinks at old David External paths provide backward compatibility.

---

### Currently Active Training Data

| Source | Path | Size | Status |
|--------|------|------|--------|
| Perpetual merged | /Volumes/Applications/SAM/sam_brain_data/perpetual_merged.jsonl | 245 MB | **ACTIVE** - used by perpetual_learner |
| Auto-learner output | ~/ReverseLab/SAM/warp_tauri/sam_brain/auto_training_data/ | 444 KB | Active but tiny |

**Distribution Problem:** 90% coding, 10% roleplay. Missing: fashion, psychology, fiction, personality, planning.

---

### Converted to JSONL (Ready to Use)

| Dataset | Path | Size | Examples | Categories |
|---------|------|------|----------|------------|
| SAM Master | /Volumes/#1/SAM/training_data/SAM_master_training/ | 94 MB | 31,748 | 19,246 coding + 11,507 roleplay + 902 planning + 93 personality |
| ChatGPT | /Volumes/#1/SAM/training_data/chatgpt_training/ | 142 MB | 20,978 | Coding, roleplay, planning, general, coaching |
| Instruction Sets | /Volumes/#1/SAM/training_data/instruction_datasets/ | 2.1 GB | Varies | Alpaca, Dolly, ShareGPT, Ultrachat, etc. |
| Nifty Fiction | /Volumes/#1/SAM/scraper_archives/nifty_archive/training_data/ | 13 MB | 10,017 | 9,016 train + 1,001 validation |

**Total ready-to-use:** ~2.35 GB across ~62,743+ examples

> Paths updated 2026-01-28. Old David External paths remain as symlinks.

---

### Raw / Unprocessed Sources (NOT Converted to Training Format)

| Source | Location | Size | Records | Conversion Status |
|--------|----------|------|---------|-------------------|
| AO3 Main Archive | /Volumes/#1/SAM/scraper_archives/ | 1.1 GB | 3,336 works | **NOT CONVERTED** |
| AO3 Roleplay | /Volumes/#1/SAM/scraper_archives/ | 60 MB | 6,037 works | **NOT CONVERTED** |
| Dark Psychology | /Volumes/#1/SAM/scraper_archives/ | 193 MB | 313 stories | **NOT CONVERTED** |
| The Cut | /Volumes/#1/SAM/scraper_archives/ | -- | 176 articles | **NOT CONVERTED** |
| Code Collection | /Volumes/#1/SAM/scraper_archives/ | 138 MB | DB format | **NOT CONVERTED** |
| Apple Developer Docs | /Volumes/#1/SAM/scraper_archives/ | 13 MB DB | only 1.8 KB used | **NOT CONVERTED** (99.99% unused) |
| Literotica | /Volumes/#1/SAM/scraper_archives/ | minimal | 40 stories | Barely started scraping |
| GQ/Esquire | /Volumes/#1/SAM/scraper_archives/ | minimal | Indexed only | Articles not downloaded |
| Interview Magazine | /Volumes/#1/SAM/scraper_archives/ | minimal | -- | Minimal data |
| F-List | -- | minimal | -- | Minimal data |
| FirstView Fashion | /Volumes/#1/SAM/scraper_archives/ | 79 MB DB | 337,602 photos indexed (8M catalog support after rewrite) | **NOT CONVERTED** (photos, not text) |
| Fashion Archives | /Volumes/#1/SAM/fashion_archives/ | **117 GB** | WWD + W + V Magazine | **NOT IN PIPELINE AT ALL** |

---

### ChatGPT Export

| Item | Path | Size | Status |
|------|------|------|--------|
| Primary export | /Volumes/#1/SAM/training_data/chatgpt_export/ | 2.7 GB | 1,134 files |
| Duplicate copy | /Volumes/David External/sam_training/chatgpt_export/ (symlink) | ~2.7 GB | **DUPLICATE** |
| conversations.json | (within export) | -- | **Appears empty - needs investigation** |

---

### Claude Code Sessions

| Metric | Value |
|--------|-------|
| Location | ~/.claude/ |
| Total size | 165 MB |
| Total JSONL files | 273 |
| Files processed by auto_learner | 75 / 273 (**27%**) |
| Training examples extracted | 777 |
| Remaining unprocessed | **198 sessions** |

---

### Warp Terminal Data (UNTAPPED)

| Source | Path | Size | Records |
|--------|------|------|---------|
| **Live database** | /Volumes/Plex/DevSymlinks/warp_data/ | 322 MB | 7,220 AI queries, 2,841 commands, 292 blocks |
| Static extract | sam_brain/warp_knowledge/ | 3.3 MB | 836 AI queries (OUTDATED) |

**Status:** NOT being used by any training system. The live database has 8.6x more AI queries than the static extract.

---

### Voice Training Data

| Component | Path | Size | Status |
|-----------|------|------|--------|
| Main training data | /Volumes/#1/SAM/voice_data/SAM_Voice_Training/ | 8.7 GB | Videos + extracted audio + speech segments |
| Raw audio | /Volumes/Plex/DevSymlinks/SAM_voice_audio_raw/ | 631 MB | Extracted audio files |
| Downloads | /Volumes/Plex/DevSymlinks/SAM_voice_downloads/ | 632 MB | Source video downloads |
| RVC logs | /Volumes/#1/SAM/voice_data/RVC_logs/ | 18 GB | Training artifacts |

> Paths updated 2026-01-28: voice data moved from David External to #1/SAM/voice_data/.

**Overall Status:** 80% data preparation complete, 0% model trained.

---

### Large Backups

| File | Path | Size | Notes |
|------|------|------|-------|
| Historical training dump | /Volumes/#1/SAM/training_backups/SAM_Backup/all_training.jsonl | 37 GB | Single massive file, historical only |
| RVC training logs | /Volumes/#1/SAM/voice_data/RVC_logs/ | 18 GB | Voice model training artifacts |

---

## 3. Project Inventory

### SAM Core Projects

| # | Project | Path | Size | Status | SAM Aware | Docs |
|---|---------|------|------|--------|-----------|------|
| 1 | **sam_brain** (core) | ~/ReverseLab/SAM/warp_tauri/sam_brain/ | -- | **ACTIVE** | Yes | SSOT + CLAUDE.md + /docs/ |
| 2 | **sam_api** | (within sam_brain) | -- | **ACTIVE** | Yes | In sam_brain docs |
| 3 | **perpetual_learner** | (within sam_brain) | -- | **ACTIVE** | Yes | In sam_brain docs |
| 4 | **auto_learner** | (within sam_brain) | -- | **ACTIVE** | Yes | In sam_brain docs |
| 5 | **warp_tauri** (shell) | ~/ReverseLab/SAM/warp_tauri/ | -- | **ACTIVE** | Yes | SSOT |
| 6 | **orchestrator** | (within sam_brain) | -- | **ACTIVE** | Yes | In sam_brain docs |

### SAM Tool Projects (Integrated)

| # | Project | Path | Size | Status | SAM Aware | Docs |
|---|---------|------|------|--------|-----------|------|
| 7 | Voice System (RVC) | ~/ReverseLab/SAM/ (voice components) | -- | IDLE | Yes | Voice docs in /docs/ |
| 8 | Memory System | (within sam_brain) | -- | ACTIVE | Yes | MEMORY_SYSTEM.md |
| 9 | RAG System | (within sam_brain) | -- | ACTIVE | Yes | RAG_SYSTEM.md |
| 10 | Scraper System | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | DATA_ARSENAL_AUDIT.md |

### Projects SAM is BLIND To

| # | Project | Path | Size | Status | SAM Aware | Notes |
|---|---------|------|------|--------|-----------|-------|
| 11 | **CalCareers Automation** | ~/Projects/calcareers-automation/ | -- | **ACTIVE** | **NO** | 92 tracked jobs, 78 SOQs generated, auto-apply ready. ZERO SAM awareness |
| 12 | **Account Automation** | /Volumes/Plex/DevSymlinks/account_automation/ | -- | **ACTIVE** | **NO** | HideMyEmail integration, 6/54 aliases created. Not in orchestrator |
| 13 | **Topaz Video Parity** | -- | -- | ACTIVE | **NO** | Not in orchestrator |
| 14 | **Muse** | ~/Projects/Muse/ | -- | SCAFFOLDED | **NO** | Extensive docs exist but no SAM integration |
| 15 | **Media Processing** | ~/ReverseLab/SAM/media/ | -- | ACTIVE | **NO** | Audio quality, lossless verification, catalog research. Not routed |

### Other Known Projects

| # | Project | Path | Size | Status | SAM Aware | Notes |
|---|---------|------|------|--------|-----------|-------|
| 16 | Nifty Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 1.4 GB scraped |
| 17 | AO3 Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 3,336 + 6,037 works |
| 18 | Dark Psychology Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 313 stories |
| 19 | The Cut Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 176 articles |
| 20 | Literotica Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 40 stories (barely started) |
| 21 | GQ/Esquire Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | Indexed, not downloaded |
| 22 | Interview Magazine | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | Minimal data |
| 23 | F-List Scraper | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | Minimal data |
| 24 | FirstView Fashion | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 337,602 photos indexed; rewritten for 8M catalog |
| 25 | Stash/StashGrid | /Volumes/# 2/ | 264 GB | ACTIVE | No | Adult content management |
| 26 | DAZ_3D | /Volumes/Applications/DAZ_3D/ | 2.3 GB | IDLE | No | 3D modeling |
| 27 | Claude Archives | /Volumes/Applications/claude_archives/ | 1.3 GB | ACTIVE | Partial | 127 conversation files |
| 28+ | Additional projects | Various | -- | Various | Various | See SSOT registry for full list (20+ registered) |

### SAM Awareness Gap Summary

- **5 major projects** have zero SAM integration (CalCareers, Account Automation, Topaz, Muse, Media Processing)
- Orchestrator cannot route to these projects
- CalCareers is the most critical gap: production-ready job automation with no SAM awareness

---

## 4. Active Services

### Running LaunchAgents

| Service | Label | PID | Script | Port | Status |
|---------|-------|-----|--------|------|--------|
| SAM API Server | com.sam.api | 1449 | sam_api.py | 8765 | **Running** |
| Auto Learner | com.sam.autolearner | 33587 | auto_learner.py | -- | **Running** |
| Perpetual Learner | com.sam.perpetual | 33573 | perpetual_learner.py | -- | **Running** |
| Scraper Daemon | com.sam.scraper-daemon | -- | -- | -- | Loaded, NOT running |
| Scraper Watchdog | com.sam.scraper-watchdog | -- | -- | -- | Loaded |

### Disabled LaunchAgents

9 `.plist.disabled` files exist. These are services that were previously active but have been intentionally stopped.

### Service Dependencies

```
sam_api.py (port 8765)
  ├── orchestrator (routes queries)
  ├── memory system (context retrieval)
  ├── RAG system (document search)
  └── MLX inference (Qwen2.5-1.5B + SAM LoRA)

perpetual_learner.py
  ├── reads: /Volumes/Applications/SAM/sam_brain_data/perpetual_merged.jsonl
  ├── writes: MLX LoRA adapter updates
  ├── MAX_DEDUP_HASHES: 10000 with LRU pruning (fixed 2026-01-28)
  └── STATUS: FIXED (NameError resolved 2026-01-27)

auto_learner.py
  ├── reads: ~/.claude/ session files
  ├── writes: sam_brain/auto_training_data/
  └── STATUS: running but only 27% through sessions

scraper_daemon.py
  ├── All 17 storage paths updated to /Volumes/#1/SAM/ (2026-01-28)
  └── STATUS: loaded, not running
```

---

## 5. Database Inventory

### Summary

| Metric | Count |
|--------|-------|
| Total databases | ~45 |
| Total size | ~163 MB |
| Duplicate pairs | 7 |
| Orphaned (no active writer) | 7 (~70 MB wasted) |
| Shared (conflict risk) | 0 (code_index.db conflict resolved) |

### Database Issues

#### Duplicate Database Pairs (7 pairs)

Databases exist at both `sam_memory/` and `sam_memory/cognitive/` paths:

| Database Name | Path A (sam_memory/) | Path B (sam_memory/cognitive/) | Action Needed |
|---------------|---------------------|-------------------------------|---------------|
| (7 duplicate pairs) | Original location | Duplicate location | Deduplicate - keep one, remove other |

#### Orphaned Databases (No Active Writer)

| Database | Size | Notes |
|----------|------|-------|
| advanced_tags.db | 58 MB | Largest orphan |
| (6 others) | ~12 MB total | Various abandoned databases |
| **Total wasted** | **~70 MB** | |

#### Resolved Conflicts

| Database | Resolution | Date |
|----------|-----------|------|
| code_index.db | Renamed to code_index_semantic.db for code_indexer.py to avoid dual-module conflict | 2026-01-28 |

#### State Files

| File | Size | Issue |
|------|------|-------|
| .perpetual_state.json | ~1 MB | Now capped at MAX_DEDUP_HASHES=10000 with LRU pruning (fixed 2026-01-28) |

---

## 6. Cleanup Opportunities

### Completed Cleanup (2026-01-28)

| Action | Location | Size Freed | Status |
|--------|----------|-----------|--------|
| Emptied $RECYCLE.BIN | /Volumes/# 2/ | 109 GB | Done |
| Deleted docker_backup_deleteme | /Volumes/Untitled/ | 38 GB | Done |
| Deleted ollama cache | /Volumes/Plex/DevSymlinks/ollama/ | 14 GB | Done |
| Deleted ReverseLab_Cleanup_Backup | /Volumes/Applications/ | 33 GB | Done (macOS metadata remains) |
| Cleared DerivedData | ~/Library/Developer/Xcode/DerivedData/ | 840 MB | Done |
| **TOTAL FREED** | | **~195 GB** | |

### Remaining Medium-Term Cleanup

| Action | Location | Size | Notes |
|--------|----------|------|-------|
| Remove duplicate chatgpt_export | /Volumes/David External/sam_training/chatgpt_export/ | ~2.7 GB | Duplicate (may now be symlink) |
| Deduplicate 7 database pairs | sam_memory/ vs sam_memory/cognitive/ | ~10 MB | Keep active copy, remove duplicate |
| Remove orphaned databases | Various | 70 MB | Confirm no readers first |
| Clean unorganized music | /Volumes/David External/ | 434 GB | Sort into lossless/lossy, remove dupes |

### Plex Drive Specific (59% full, improved from 66%)

| Action | Savings | Priority |
|--------|---------|----------|
| Review DockerData | up to 22 GB | Medium (check if needed) |
| Clear unused cargo builds | up to 10 GB | Medium |
| Prune huggingface cache | varies | Low (active models needed) |

---

## 7. Critical Issues

### Severity: HIGH

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | ~~perpetual_learner.py NameError on line 925~~ | **FIXED 2026-01-27** - imported correct ResourceManager constants | sam_brain/perpetual_learner.py:925 |
| 2 | ~~code_index.db shared by 2 incompatible modules~~ | **FIXED 2026-01-28** - code_indexer.py now uses code_index_semantic.db | sam_memory/code_index.db |
| 3 | **90/10 coding/roleplay training imbalance** | SAM personality is underdeveloped. Missing: fashion, psychology, fiction, planning. | perpetual_merged.jsonl |
| 4 | **Multiple ResourceManager instances** | Defeats resource limiting on 8GB system. Each instance tracks independently. | sam_brain/ (multiple modules) |

### Severity: MEDIUM

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 5 | ~~Ollama pre-warm in main.rs~~ | **FIXED 2026-01-27** - replaced with MLX/sam_api health check on port 8765 | warp_tauri/src-tauri/src/main.rs |
| 6 | **200+ unprocessed Claude sessions** | 198 sessions with potential training data not extracted. | ~/.claude/ |
| 7 | **117 GB fashion archives not in pipeline** | Major content domain completely missing from training. Now at /Volumes/#1/SAM/fashion_archives/ | /Volumes/#1/SAM/fashion_archives/ |
| 8 | **Duplicate databases (7 pairs)** | Confusion about which is authoritative. Disk waste. | sam_memory/ vs sam_memory/cognitive/ |
| 9 | **conversations.json appears empty** | 2.7 GB ChatGPT export may be partially corrupt. | /Volumes/#1/SAM/training_data/chatgpt_export/ |

### Severity: LOW

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 10 | Warp terminal data untapped | 7,220 AI queries not used for training. | /Volumes/Plex/DevSymlinks/warp_data/ |
| 11 | ~~.perpetual_state.json unbounded~~ | **FIXED 2026-01-28** - MAX_DEDUP_HASHES=10000 with LRU pruning | sam_brain/.perpetual_state.json |
| 12 | 7 orphaned databases | 70 MB wasted, potential confusion. | Various sam_memory/ paths |
| 13 | Voice training stalled at 80% prep | No trained voice model despite 8.7 GB of data. | /Volumes/#1/SAM/voice_data/SAM_Voice_Training/ |
| 14 | 5 projects invisible to SAM | CalCareers, Account Automation, Topaz, Muse, Media Processing. | Various paths |

---

## Appendix: Data Flow Diagram

```
                        ┌─────────────────────────┐
                        │    EXTERNAL SOURCES      │
                        └──────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
   ┌────▼────┐             ┌──────▼──────┐           ┌───────▼──────┐
   │ Scrapers │             │ ChatGPT     │           │ Claude Code  │
   │ (IDLE)   │             │ Export      │           │ Sessions     │
   │          │             │ 2.7GB       │           │ 165MB        │
   │ AO3      │             └──────┬──────┘           └──────┬───────┘
   │ Nifty    │                    │                         │
   │ DarkPsych│             ┌──────▼──────┐          ┌───────▼──────┐
   │ Fashion  │             │ chatgpt_    │          │ auto_learner │
   │ etc.     │             │ training/   │          │ (27% done)   │
   └────┬─────┘             │ 142MB JSONL │          └──────┬───────┘
        │                   └──────┬──────┘                 │
        │                          │                        │
   ┌────▼──────┐                   │                 ┌──────▼───────┐
   │ Raw data  │                   │                 │ auto_training│
   │ on #1/SAM │                   │                 │ _data/       │
   │ (mostly   │                   │                 │ 444KB        │
   │  NOT      │                   │                 └──────┬───────┘
   │  converted)                   │                        │
   └───────────┘                   │                        │
                                   │                        │
                        ┌──────────▼────────────────────────▼──┐
                        │  perpetual_merged.jsonl (245MB)      │
                        │  90% coding / 10% roleplay           │
                        │  /Volumes/Applications/SAM/          │
                        │  sam_brain_data/                     │
                        └──────────────────┬───────────────────┘
                                           │
                                ┌──────────▼──────────┐
                                │  perpetual_learner  │
                                │  (dedup capped @10K)│
                                └──────────┬──────────┘
                                           │
                                ┌──────────▼──────────┐
                                │  MLX LoRA Adapter    │
                                │  Qwen2.5-1.5B       │
                                └──────────┬──────────┘
                                           │
                                ┌──────────▼──────────┐
                                │  sam_api.py :8765    │
                                │  (orchestrator)      │
                                └─────────────────────┘
```

---

## Appendix: Storage by Category

| Category | Total Size | Drive(s) |
|----------|-----------|----------|
| Music (all) | ~2.14 TB | David External |
| Adult Content | ~2.76 TB | # 2 |
| Training Data (converted) | ~2.35 GB | #1/SAM/training_data/ (symlinked from David External) |
| Training Data (raw/unconverted) | ~120 GB | #1/SAM/scraper_archives/, #1/SAM/fashion_archives/ |
| Training Data (backups) | ~37 GB | #1/SAM/training_backups/ |
| Voice Data | ~28 GB | #1/SAM/voice_data/, Plex |
| Photos | 87 GB | David External |
| Courses | 129 GB | David External |
| Fashion Archives | 117 GB | #1/SAM/fashion_archives/ |
| DevSymlinks | ~87 GB | Plex |
| Plex Server | ~120 GB | Plex |
| Code (all projects) | ~19 GB | Internal SSD |
| Dead Code Archive | ~25K lines | #1/SAM/dead_code_archive/ |

---

## Appendix: Internal Drive Detail (19GB used)

| Path | Size | Contents |
|------|------|----------|
| ~/ReverseLab/ | 2.6 GB | SAM (2.3G), Warp_Archive (301M), analysis (36M), tools (32M), gridplayer (26M) |
| ~/Projects/ | 2.6 GB | Muse (1.2G), StashGrid (850M), RVC (257M), character-pipeline (227M), calcareers (57M) |
| ~/.claude/ | 194 MB | Claude AI workspace, 273 session files |
| ~/ai-studio/ | 201 MB | ComfyUI reference |
| ~/.cache/ | 157 MB | whisper (141M), mediapipe (14M) |
| ~/.chatgpt-stealth-*/ | 147 MB | Browser automation profiles (3 profiles) |
| ~/.sam-ai-bridge-*/ | 118 MB | SAM automation profiles (2 profiles) |
| ~/.docker/ | 59 MB | Docker config |
| ~/.zsh_sessions/ | 41 MB | Shell history |
| ~/stash/ | 230 MB | Stash server data |

## Appendix: David External Folder Convention

Folders with `_` prefix are **older personal content** (not coding):
- _Inspiration, _Funny Stuff, _Yoworld, _Music Lossless, _Personal Photos, _Graphic Design, _Documents, _Cute Stuff, _Wallpapers, _Recipes, _Health, etc.

Folders **without** `_` prefix are **newer coding/SAM work**:
- Now mostly **symlinks** pointing to /Volumes/#1/SAM/ after 2026-01-28 migration.
- Original folder names preserved: SAM_Backup, SAM_Voice_Training, sam_models, sam_training, coding_training, chatgpt_training, scraper_data, nifty_archive, ao3_archive, etc.

## Appendix: ChatGPT Conversations as Training Data

David discussed SAM design extensively with ChatGPT before switching to Claude Code. These conversations contain:
- Architecture decisions and design intent
- Personality direction and character design
- Feature planning and roadmap discussions
- Technical problem-solving context

**Sources to process:**
| Source | Location | Size | Status |
|--------|----------|------|--------|
| ChatGPT export | /Volumes/#1/SAM/training_data/chatgpt_export/ | 2.7 GB | 1,134 files, needs conversion |
| ChatGPT training | /Volumes/#1/SAM/training_data/chatgpt_training/ | 142 MB | Already JSONL, 20,978 examples |
| ChatGPT manager scripts | /Volumes/Plex/SSOT/salvaged/chatgpt_manager/ | -- | 15 Python scripts with patterns |
| Claude sessions | ~/.claude/ | 194 MB | 273 files, 27% processed |
| Claude archives | /Volumes/Applications/claude_archives/ | 1.3 GB | 127 conversation files |

## Appendix: Volume Health Check (2026-01-27)

All 11 volumes responded to read operations without errors during this audit.
If a drive in the TerraMaster is power cycling, it may be intermittent.

| Volume | Accessible | Notes |
|--------|-----------|-------|
| Macintosh HD | Yes | Internal SSD, healthy |
| David External | Yes | 7.3TB spinning disk |
| #1 | Yes | 7.3TB spinning disk |
| # 2 | Yes | 7.3TB spinning disk |
| Plex | Yes | 223GB SSD partition |
| Applications | Yes | 223GB APFS SSD |
| Games | Yes | 7.3TB spinning disk |
| Movies | Yes | 13TB |
| Music | Yes | 7.3TB |
| TV | Yes | 13TB |
| Untitled | Yes | 1.8TB, empty after cleanup |

---

*Document generated 2026-01-27, updated 2026-01-28 with Phase 1-5 cleanup/reorganization results. All training data and scraper archives consolidated to /Volumes/#1/SAM/ with symlinks at old David External paths. 195 GB freed from cleanup deletes. This is a point-in-time snapshot. Sizes and statuses will drift over time.*
