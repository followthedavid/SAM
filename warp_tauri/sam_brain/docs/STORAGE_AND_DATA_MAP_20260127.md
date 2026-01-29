# SAM Ecosystem Storage & Data Map

**Date:** 2026-01-27
**Author:** Automated audit via Claude Code
**Purpose:** Complete inventory of all drives, data, projects, training resources, services, databases, and cleanup opportunities across the entire SAM ecosystem.

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
| Internal SSD | 228 GB | 127 GB | 101 GB | 44% | Code, configs, system |
| David External | 7.3 TB | 3.4 TB | 3.9 TB | 53% | Training data, archives, music |
| #1 | 7.3 TB | 5.8 TB | 1.5 TB | 21% | Fashion archives, backups |
| # 2 | 7.3 TB | 4.2 TB | 3.1 TB | 42% | Adult content, Tidal |
| Plex | 223 GB | 78 GB | 145 GB | **66%** | DevSymlinks, SSOT, Plex server |
| Applications | 223 GB | 163 GB | 60 GB | 27% | Apps, SAM models, backups |
| Untitled | 1.8 TB | ~1.76 TB | ~38 GB | 2% | Mostly empty (delete candidate) |
| Movies | 13 TB | -- | -- | -- | Media library (not SAM-related) |
| TV | 13 TB | -- | -- | -- | Media library (not SAM-related) |
| Music | 7.3 TB | -- | -- | -- | Media library (not SAM-related) |
| Games | 7.3 TB | -- | -- | -- | Media library (not SAM-related) |

> **WARNING:** /Volumes/Plex is at 66% capacity. Monitor closely.

---

### Internal SSD (228 GB total, 127 GB free)

| Path | Size | Contents |
|------|------|----------|
| /Users/davidquinton/ | 19 GB | Development code, configs, system libraries |

**Storage Strategy:** Code and configs ONLY. No large files. Models, training data, caches, and venvs belong on external drives.

---

### /Volumes/David External (7.3 TB total, 3.4 TB free)

Primary archival and training data storage.

| Path / Category | Size | Details |
|-----------------|------|---------|
| **Music - Lossless** | 1.5 TB | High-quality audio collection |
| **Music - Lossy** | 209 GB | Compressed audio collection |
| **Music - Unorganized** | 434 GB | Needs sorting/dedup |
| **SAM Training (total)** | ~95 GB | All SAM-related training data |
| SAM_Backup/all_training.jsonl | 37 GB | Single historical backup file |
| SAM_master_training/ | 94 MB | 19,246 coding + 11,507 roleplay + 902 planning + 93 personality |
| chatgpt_training/ | 142 MB | 20,978 examples (coding/roleplay/planning/general/coaching) |
| chatgpt_export/ | 2.7 GB | 1,134 files; conversations.json appears empty (NEEDS INVESTIGATION) |
| sam_training/chatgpt_export/ | ~2.7 GB | **DUPLICATE** of above |
| instruction_datasets/ | 2.1 GB | Alpaca, Dolly, ShareGPT, Ultrachat, etc. |
| nifty_archive/training_data/ | 13 MB | 9,016 train + 1,001 valid examples |
| **SAM Voice Training** | 8.7 GB | Videos, extracted audio, speech segments |
| **RVC_logs** | 18 GB | Voice training logs |
| **Photos** | 87 GB | Personal photo archive |
| **Documents** | 2.5 GB | Personal documents |
| **Courses** | 129 GB | Educational content |
| **Scraper Archives** | ~2.8 GB total | See breakdown below |
| - nifty_archive | 1.4 GB | Scraped fiction |
| - ao3_archive | 1.1 GB | 3,336 works (NOT converted to training format) |
| - dark_psych | 281 MB | 313 stories, 193 MB usable (NOT converted) |
| - ao3_roleplay | 60 MB | 6,037 works (NOT converted) |
| - the_cut | -- | 176 articles (NOT converted) |

---

### /Volumes/#1 (7.3 TB total, 5.8 TB free)

| Path / Category | Size | Details |
|-----------------|------|---------|
| **Fashion Archives (total)** | **117 GB** | NOT in any training pipeline |
| - WWD | 48 GB | Women's Wear Daily archive |
| - W Magazine | 40 GB | Fashion magazine archive |
| - V Magazine | 29 GB | Fashion magazine archive |
| **Plex Brain Backups** | 35 GB | Plex metadata/database backups |
| **AI Projects** | 10 GB | Miscellaneous AI project files |
| **Content Archives** | -- | Various archived content |

---

### /Volumes/# 2 (7.3 TB total, 4.2 TB free)

| Path / Category | Size | Details |
|-----------------|------|---------|
| Adult Content | 2.5 TB | Primary content collection |
| Tidal | 234 GB | Music downloads |
| StashGrid | 144 GB | Stash metadata/grid |
| Stash | 120 GB | Stash application data |
| **$RECYCLE.BIN** | **109 GB** | **SHOULD EMPTY - free space** |

---

### /Volumes/Plex (223 GB total, 78 GB free) -- WARNING: 66% FULL

| Path / Category | Size | Details |
|-----------------|------|---------|
| **Plex Media Server** | ~120 GB | Plex application + metadata |
| **DevSymlinks/ (total)** | **101 GB** | Development symlink targets |
| - huggingface/ | 24 GB | Model cache |
| - venvs/ | 20 GB | 5 voice venvs + 2 brain venvs |
| - stash_data/ | 15 GB | Stash application data |
| - ollama/ | 14 GB | **DECOMMISSIONED** (delete candidate) |
| - cargo builds | ~10 GB | Rust compilation artifacts |
| - RVC_assets/ | 2.3 GB | Voice training assets |
| - warp_data/ | 322 MB | Live Warp terminal database |
| - Various caches | ~15 GB | pip, npm, etc. |
| **DockerData** | 22 GB | Docker images/volumes |
| **SSOT/** | 281 MB | Single Source of Truth docs |

---

### /Volumes/Applications (223 GB total, 163 GB free)

| Path / Category | Size | Details |
|-----------------|------|---------|
| **ReverseLab_Cleanup_Backup** | **33 GB** | **Review for deletion** |
| Xcode.app | 12 GB | Apple development tools |
| SAM/ | 5.2 GB | Models, data, scrapers, voice, adapters |
| - sam_brain_data/ | 245 MB | perpetual_merged.jsonl (ACTIVE) |
| claude_archives/ | 1.3 GB | 127 conversation files |
| DAZ_3D/ | 2.3 GB | 3D modeling assets |

---

### /Volumes/Untitled (1.8 TB, mostly empty)

| Path / Category | Size | Details |
|-----------------|------|---------|
| **docker_backup_deleteme** | **38 GB** | **Safe to delete** |

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
| SAM Master | /Volumes/David External/SAM_master_training/ | 94 MB | 31,748 | 19,246 coding + 11,507 roleplay + 902 planning + 93 personality |
| ChatGPT | /Volumes/David External/chatgpt_training/ | 142 MB | 20,978 | Coding, roleplay, planning, general, coaching |
| Instruction Sets | /Volumes/David External/instruction_datasets/ | 2.1 GB | Varies | Alpaca, Dolly, ShareGPT, Ultrachat, etc. |
| Nifty Fiction | /Volumes/David External/nifty_archive/training_data/ | 13 MB | 10,017 | 9,016 train + 1,001 validation |

**Total ready-to-use:** ~2.35 GB across ~62,743+ examples

---

### Raw / Unprocessed Sources (NOT Converted to Training Format)

| Source | Location | Size | Records | Conversion Status |
|--------|----------|------|---------|-------------------|
| AO3 Main Archive | /Volumes/David External/ | 1.1 GB | 3,336 works | **NOT CONVERTED** |
| AO3 Roleplay | /Volumes/David External/ | 60 MB | 6,037 works | **NOT CONVERTED** |
| Dark Psychology | /Volumes/David External/ | 193 MB | 313 stories | **NOT CONVERTED** |
| The Cut | /Volumes/David External/ | -- | 176 articles | **NOT CONVERTED** |
| Code Collection | -- | 138 MB | DB format | **NOT CONVERTED** |
| Apple Developer Docs | -- | 13 MB DB | only 1.8 KB used | **NOT CONVERTED** (99.99% unused) |
| Literotica | -- | minimal | 40 stories | Barely started scraping |
| GQ/Esquire | -- | minimal | Indexed only | Articles not downloaded |
| Interview Magazine | -- | minimal | -- | Minimal data |
| F-List | -- | minimal | -- | Minimal data |
| FirstView Fashion | -- | 79 MB DB | 337,602 photos indexed | **NOT CONVERTED** (photos, not text) |
| Fashion Archives (#1) | /Volumes/#1/ | **117 GB** | WWD + W + V Magazine | **NOT IN PIPELINE AT ALL** |

---

### ChatGPT Export

| Item | Path | Size | Status |
|------|------|------|--------|
| Primary export | /Volumes/David External/chatgpt_export/ | 2.7 GB | 1,134 files |
| Duplicate copy | /Volumes/David External/sam_training/chatgpt_export/ | ~2.7 GB | **DUPLICATE** |
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
| Main training data | /Volumes/David External/SAM_Voice_Training/ | 8.7 GB | Videos + extracted audio + speech segments |
| Raw audio | /Volumes/Plex/DevSymlinks/SAM_voice_audio_raw/ | 631 MB | Extracted audio files |
| Downloads | /Volumes/Plex/DevSymlinks/SAM_voice_downloads/ | 632 MB | Source video downloads |
| RVC logs | /Volumes/David External/RVC_logs/ | 18 GB | Training artifacts |

**Overall Status:** 80% data preparation complete, 0% model trained.

---

### Large Backups

| File | Path | Size | Notes |
|------|------|------|-------|
| Historical training dump | /Volumes/David External/SAM_Backup/all_training.jsonl | 37 GB | Single massive file, historical only |
| RVC training logs | /Volumes/David External/RVC_logs/ | 18 GB | Voice model training artifacts |

---

## 3. Project Inventory

### SAM Core Projects

| # | Project | Path | Size | Status | SAM Aware | Docs |
|---|---------|------|------|--------|-----------|------|
| 1 | **sam_brain** (core) | ~/ReverseLab/SAM/warp_tauri/sam_brain/ | -- | **ACTIVE** | Yes | SSOT + CLAUDE.md + /docs/ |
| 2 | **sam_api** | (within sam_brain) | -- | **ACTIVE** | Yes | In sam_brain docs |
| 3 | **perpetual_learner** | (within sam_brain) | -- | **ACTIVE (CRASHED)** | Yes | In sam_brain docs |
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
| 24 | FirstView Fashion | ~/ReverseLab/SAM/ (scrapers) | -- | IDLE | Partial | 337,602 photos indexed |
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
| Perpetual Learner | com.sam.perpetual | 33573 | perpetual_learner.py | -- | **Running (CRASHED - see Issues)** |
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
  └── STATUS: NameError crash on line 925

auto_learner.py
  ├── reads: ~/.claude/ session files
  ├── writes: sam_brain/auto_training_data/
  └── STATUS: running but only 27% through sessions
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
| Shared (conflict risk) | 1 (code_index.db) |

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

#### Conflict Risk

| Database | Issue |
|----------|-------|
| code_index.db | **Shared by 2 incompatible modules** - data corruption risk |

#### State Files

| File | Size | Issue |
|------|------|-------|
| .perpetual_state.json | 1 MB | Contains 29,688 unbounded dedup hashes. Will grow indefinitely without pruning. |

---

## 6. Cleanup Opportunities

### Immediate Space Savings

| Action | Location | Size | Risk | Drive |
|--------|----------|------|------|-------|
| Delete ollama/ | /Volumes/Plex/DevSymlinks/ollama/ | **14 GB** | None (decommissioned 2026-01-18) | Plex |
| Empty $RECYCLE.BIN | /Volumes/# 2/$RECYCLE.BIN | **109 GB** | Low (recycle bin) | # 2 |
| Delete docker_backup_deleteme | /Volumes/Untitled/docker_backup_deleteme | **38 GB** | None (named "deleteme") | Untitled |
| Review ReverseLab_Cleanup_Backup | /Volumes/Applications/ReverseLab_Cleanup_Backup/ | **33 GB** | Medium (review contents first) | Applications |
| Clear DerivedData | ~/Library/Developer/Xcode/DerivedData/ | **840 MB** | None (rebuild on demand) | Internal |
| **TOTAL** | | **~195 GB** | | |

### Medium-Term Cleanup

| Action | Location | Size | Notes |
|--------|----------|------|-------|
| Remove duplicate chatgpt_export | /Volumes/David External/sam_training/chatgpt_export/ | ~2.7 GB | Duplicate of chatgpt_export/ |
| Prune .perpetual_state.json | sam_brain/.perpetual_state.json | 1 MB | Cap dedup hashes at reasonable limit |
| Deduplicate 7 database pairs | sam_memory/ vs sam_memory/cognitive/ | ~10 MB | Keep active copy, remove duplicate |
| Remove orphaned databases | Various | 70 MB | Confirm no readers first |
| Clean unorganized music | /Volumes/David External/ | 434 GB | Sort into lossless/lossy, remove dupes |

### Plex Drive Specific (66% full, needs attention)

| Action | Savings | Priority |
|--------|---------|----------|
| Delete ollama/ | 14 GB | **HIGH** |
| Review DockerData | up to 22 GB | Medium (check if needed) |
| Clear unused cargo builds | up to 10 GB | Medium |
| Prune huggingface cache | varies | Low (active models needed) |

---

## 7. Critical Issues

### Severity: HIGH

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | ~~perpetual_learner.py NameError on line 925~~ | **FIXED 2026-01-27** - imported correct ResourceManager constants | sam_brain/perpetual_learner.py:925 |
| 2 | **code_index.db shared by 2 incompatible modules** | Data corruption risk. Both modules write different schemas. | sam_memory/code_index.db |
| 3 | **90/10 coding/roleplay training imbalance** | SAM personality is underdeveloped. Missing: fashion, psychology, fiction, planning. | perpetual_merged.jsonl |
| 4 | **Multiple ResourceManager instances** | Defeats resource limiting on 8GB system. Each instance tracks independently. | sam_brain/ (multiple modules) |

### Severity: MEDIUM

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 5 | ~~Ollama pre-warm in main.rs~~ | **FIXED 2026-01-27** - replaced with MLX/sam_api health check on port 8765 | warp_tauri/src-tauri/src/main.rs |
| 6 | **200+ unprocessed Claude sessions** | 198 sessions with potential training data not extracted. | ~/.claude/ |
| 7 | **117 GB fashion archives not in pipeline** | Major content domain completely missing from training. | /Volumes/#1/ (WWD, W, V Magazine) |
| 8 | **Duplicate databases (7 pairs)** | Confusion about which is authoritative. Disk waste. | sam_memory/ vs sam_memory/cognitive/ |
| 9 | **conversations.json appears empty** | 2.7 GB ChatGPT export may be partially corrupt. | /Volumes/David External/chatgpt_export/ |

### Severity: LOW

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 10 | Warp terminal data untapped | 7,220 AI queries not used for training. | /Volumes/Plex/DevSymlinks/warp_data/ |
| 11 | .perpetual_state.json unbounded | 29,688 hashes growing without limit. | sam_brain/.perpetual_state.json |
| 12 | 7 orphaned databases | 70 MB wasted, potential confusion. | Various sam_memory/ paths |
| 13 | Voice training stalled at 80% prep | No trained voice model despite 8.7 GB of data. | /Volumes/David External/SAM_Voice_Training/ |
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
   │ on David  │                   │                 │ _data/       │
   │ External  │                   │                 │ 444KB        │
   │ (mostly   │                   │                 └──────┬───────┘
   │  NOT      │                   │                        │
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
                                │  (FIXED 2026-01-27)│
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
| Training Data (converted) | ~2.35 GB | David External |
| Training Data (raw/unconverted) | ~120 GB | David External, #1 |
| Training Data (backups) | ~37 GB | David External |
| Voice Data | ~28 GB | David External, Plex |
| Photos | 87 GB | David External |
| Courses | 129 GB | David External |
| Fashion Archives | 117 GB | #1 |
| DevSymlinks | 101 GB | Plex |
| Plex Server | ~120 GB | Plex |
| Code (all projects) | ~19 GB | Internal SSD |
| Cleanup candidates | ~195 GB | Various |

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
- SAM_Backup, SAM_Voice_Training, sam_models, sam_training, coding_training, chatgpt_training, scraper_data, nifty_archive, ao3_archive, etc.

## Appendix: ChatGPT Conversations as Training Data

David discussed SAM design extensively with ChatGPT before switching to Claude Code. These conversations contain:
- Architecture decisions and design intent
- Personality direction and character design
- Feature planning and roadmap discussions
- Technical problem-solving context

**Sources to process:**
| Source | Location | Size | Status |
|--------|----------|------|--------|
| ChatGPT export | /Volumes/David External/chatgpt_export/ | 2.7 GB | 1,134 files, needs conversion |
| ChatGPT training | /Volumes/David External/chatgpt_training/ | 142 MB | Already JSONL, 20,978 examples |
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
| Untitled | Yes | 1.8TB, mostly empty |

---

*Document generated 2026-01-27 (updated same day with scan results, fixes, and ChatGPT training notes). This is a point-in-time snapshot. Sizes and statuses will drift over time.*
