# SAM Backup & Recovery Analysis

**Date:** 2026-01-29
**Scope:** Full analysis of backup, recovery, and data durability for the SAM ecosystem
**Status:** CRITICAL GAPS IDENTIFIED

---

## Executive Summary

SAM has **no systematic backup strategy**. There is a git repo with infrequent commits, dead code archiving on `/Volumes/#1/`, and external drive symlinks for large assets, but no automated backup of databases, no database replication, no recovery scripts, no Time Machine, and several broken symlinks pointing to a volume (`/Volumes/Applications/`) that no longer exists. If the internal SSD fails or an external drive disconnects, significant data loss would occur.

---

## 1. Code Backup

### Git Repository

| Aspect | Status | Details |
|--------|--------|---------|
| Location | `/Users/davidquinton/ReverseLab/SAM/.git` | Parent of warp_tauri/sam_brain |
| Remote | `https://github.com/followthedavid/SAM.git` | GitHub origin |
| Last commit | `afc2091` (Jan 27, 2026) | "SAM Phase 1-6 complete implementation" |
| Total commits | 7 | Very infrequent commits |
| Uncommitted changes | ~2,740 files changed | Massive drift from last commit |
| Branch | main | Single branch |

**CRITICAL ISSUE:** There are approximately 2,740 files changed since the last commit. The git history has only 7 commits total, most of which are bulk "auto-commit" pushes. This means the vast majority of current code is NOT backed up to GitHub.

### Time Machine

| Aspect | Status |
|--------|--------|
| Configured | NO |
| Destinations | None configured |
| Running | Not running |

**Time Machine is not set up.** There is zero automatic backup of the internal SSD.

### Dead Code Archive

| Location | Files | Lines | Purpose |
|----------|-------|-------|---------|
| `/Volumes/#1/SAM/dead_code_archive/` | 59 | ~24,949 | Superseded code, safely archived |
| `sam_brain_learners/` | 6 | 4,514 | Old learning systems |
| `sam_brain_orchestrators/` | 4 | 2,482 | Old orchestrators |
| `sam_brain_experiments/` | 10 | 7,683 | Experimental modules |
| `warp_tauri_root_scripts/` | 39 | 10,270 | ChatGPT/Claude bridges, Frida scripts |
| `sam_brain_additional/` | ~53 | varies | Additional archived files |

The archive has a well-maintained `manifest.md` documenting what was archived and why. Originals were kept (copies only). This is the strongest part of the backup story, but it only covers dead/superseded code, not active code.

---

## 2. Database Backup

### Databases on Internal SSD (`sam_brain/`)

| Database | Size | Backed Up? | Recovery? |
|----------|------|-----------|-----------|
| `evolution.db` | 15 MB | NO | None |
| `auto_learning.db` | 652 KB | NO | None |

Both use SQLite `DELETE` journal mode (not WAL). Current integrity: both pass `PRAGMA integrity_check`.

### Databases on External (`/Volumes/David External/sam_memory/`)

| Database | Size | Backed Up? | Recovery? |
|----------|------|-----------|-----------|
| `code_index.db` | 8.3 MB | NO | Rebuildable from source code |
| `memory.db` | 64 KB | NO | None |
| `facts.db` | 72 KB | NO | None |
| `feedback.db` | 88 KB | NO | None |
| `rag_feedback.db` | 80 KB | NO | None |
| `intelligence_core.db` | 48 KB | NO | None |
| `project_context.db` | 32 KB | NO | None |
| `project_sessions.db` | 24 KB | NO | None |
| `active_learning.db` | 24 KB | NO | None |
| `cache.db` | 24 KB | NO | Rebuildable (cache) |
| `decay.db` | 16 KB | NO | None |
| `goals.db` | 16 KB | NO | None |
| `metacognition.db` | 16 KB | NO | None |
| `procedural.db` | 24 KB | NO | None |
| `relationships.db` | 24 KB | NO | None |

### Databases on External (`/Volumes/David External/SAM_models/sam_fused/`)

| Database | Size | Backed Up? | Recovery? |
|----------|------|-----------|-----------|
| `advanced_tags.db` | 58 MB | NO | Rebuildable from scraping |
| `content_tags.db` | 12 MB | NO | Rebuildable from scraping |
| `approval_queue.db` | 28 KB | NO | Ephemeral |
| `conversations.db` | 28 KB | NO | None |

### State Files (JSON, not backed up)

| File | Size | Location | Criticality |
|------|------|----------|-------------|
| `.perpetual_state.json` | 1.0 MB | Internal SSD | HIGH - perpetual learner state |
| `projects_discovered.json` | 802 KB | Internal SSD | MEDIUM - rebuildable via scan |
| `projects.json` | 21 KB | Internal SSD | HIGH - project configuration |
| `warp_knowledge/ai_queries.json` | 3.0 MB | Internal SSD | MEDIUM - accumulated AI knowledge |
| `exhaustive_analysis/master_inventory.json` | 2.7 MB | Internal SSD | LOW - rebuildable |
| `memory/embeddings.json` | 22 KB | Internal SSD | MEDIUM - semantic embeddings |
| `memory/index.npy` | 5 KB | Internal SSD | MEDIUM - embedding index |

**VERDICT: No database is backed up. No database has a backup script, snapshot mechanism, or replication. All databases use DELETE journal mode, which provides crash recovery but not corruption recovery.**

---

## 3. Model Files

### Location: `/Volumes/David External/SAM_models/` (6.9 GB total)

| Asset | Size | Backed Up? |
|-------|------|-----------|
| `sam_fused/` (fused model) | 1.6 GB | NO |
| `adapters/` (7 LoRA variants) | 151 MB | NO |
| `emotion2vec/` | varies | NO |
| Training logs | various | NO |

### Broken Symlinks (CRITICAL)

Four symlinks in sam_brain point to `/Volumes/Applications/SAM/` which **does not exist** as a mounted volume:

| Symlink | Target | Status |
|---------|--------|--------|
| `adapters_new` | `/Volumes/Applications/SAM/adapters_new` | **BROKEN** |
| `models` | `/Volumes/Applications/SAM/sam_brain_models` | **BROKEN** |
| `data` | `/Volumes/Applications/SAM/sam_brain_data` | **BROKEN** |
| `training_data` | `/Volumes/Applications/SAM/training_data` | **BROKEN** |
| `openvoice` | `/Volumes/Applications/SAM/openvoice` | **BROKEN** |

The volume `/Volumes/Applications/` is not currently mounted and does not appear in `/Volumes/`. These symlinks will cause import errors or silent failures in any code that references them.

### Working Symlinks

| Symlink | Target | Status |
|---------|--------|--------|
| `.venv` | `/Volumes/Plex/DevSymlinks/venvs/sam_brain_dotvenv` | OK (Plex mounted) |
| `venv` | `/Volumes/Plex/DevSymlinks/venvs/sam_brain_venv` | OK (Plex mounted) |

---

## 4. Training Data

### On Internal SSD

| Path | Size | Contents |
|------|------|----------|
| `auto_training_data/train.jsonl` | 392 KB | Auto-captured training examples |
| `auto_training_data/valid.jsonl` | 45 KB | Validation split |
| `checkpoints/` | Empty | No saved checkpoints |

### On External (`/Volumes/#1/SAM/training_data/`)

| Directory | Contents |
|-----------|----------|
| `chatgpt_export/` | Exported ChatGPT conversations |
| `chatgpt_training/` | Formatted training data from ChatGPT |
| `code_patterns/` | Mined code patterns |
| `instruction_datasets/` | Curated instruction datasets |
| `SAM_master_training/` | Master training dataset |

### Training Backup

| Path | Size | Contents |
|------|------|----------|
| `/Volumes/#1/SAM/training_backups/SAM_Backup/all_training.jsonl` | **37 GB** | Full training data backup |

This is the single most significant backup that exists. However, it is a single file on a single drive with no redundancy.

---

## 5. Internal SSD vs External Drives

### Internal SSD (`~/ReverseLab/SAM/warp_tauri/sam_brain/`) - 43 MB

Contains:
- All Python source code (~120+ .py files)
- Two SQLite databases (evolution.db 15MB, auto_learning.db 652KB)
- State/config JSON files (~8 MB total)
- Log files (~800 KB)
- Documentation (~45 .md files)
- Memory system (embeddings.json, index.npy)
- Symlinks to external storage

### External Drive: `/Volumes/David External/`

| Path | Size | Contents |
|------|------|----------|
| `SAM_models/` | 6.9 GB | Fused model, LoRA adapters, training logs |
| `sam_memory/` | 9.1 MB | 15 SQLite databases (memory, facts, RAG, etc.) |
| `ollama_backup/` | varies | Decommissioned Ollama model backups |

### External Drive: `/Volumes/#1/SAM/`

| Path | Contents |
|------|----------|
| `dead_code_archive/` | 59 archived files with manifest |
| `training_data/` | Master training datasets |
| `training_backups/` | 37GB all_training.jsonl |
| `voice_data/` | RVC logs, voice training samples |
| `scraper_archives/` | Historical scraper output |
| `scraper_daemon/` | Daemon state |
| `doc_archive/` | Archived documentation |
| `evaluations/` | Model evaluation results |
| `ab_tests/` | A/B test results |

### External Drive: `/Volumes/Plex/`

| Path | Contents |
|------|----------|
| `DevSymlinks/venvs/` | Python virtual environments |
| `SSOT/` | Single Source of Truth documentation |

---

## 6. What Happens If External Drive Disconnects?

### `/Volumes/David External/` disconnects:

| Impact | Severity |
|--------|----------|
| SAM model inference fails (sam_fused model gone) | **CRITICAL** |
| All 15 memory databases inaccessible | **CRITICAL** |
| Semantic memory, facts, relationships - all gone | **CRITICAL** |
| Code will throw FileNotFoundError or sqlite3.OperationalError | **HIGH** |
| No graceful degradation in code | **HIGH** |

### `/Volumes/#1/` disconnects:

| Impact | Severity |
|--------|----------|
| Training backups inaccessible | **MEDIUM** (not needed at runtime) |
| Dead code archive inaccessible | **LOW** (archival only) |
| Scraper archives inaccessible | **LOW** (not needed at runtime) |
| Voice training data inaccessible | **MEDIUM** (RVC training blocked) |

### `/Volumes/Applications/` disconnects (ALREADY DISCONNECTED):

| Impact | Severity |
|--------|----------|
| 5 broken symlinks for adapters, models, data, training_data, openvoice | **CRITICAL** |
| Any code referencing these paths silently fails | **HIGH** |
| This drive appears to be permanently unmounted | **UNKNOWN** |

### `/Volumes/Plex/` disconnects:

| Impact | Severity |
|--------|----------|
| Python venvs inaccessible - SAM cannot start | **CRITICAL** |
| SSOT documentation unavailable | **MEDIUM** |

---

## 7. What Happens If a Database Corrupts?

### Current State

- **Journal mode:** DELETE (both databases on internal SSD)
- **WAL mode:** Not used
- **Integrity checks:** Both pass as of 2026-01-29
- **Recovery mechanism:** NONE

### Corruption Scenarios

| Database | If Corrupted | Recovery Path |
|----------|-------------|---------------|
| `evolution.db` (15 MB) | Lose all evolution history, improvements, feedback, relationships, projects | **TOTAL LOSS** - no backup exists |
| `auto_learning.db` (652 KB) | Lose learned examples, training runs | **TOTAL LOSS** - no backup exists |
| `sam_memory/*.db` (9.1 MB total) | Lose all memory, facts, goals, metacognition, relationships | **TOTAL LOSS** - no backup exists |
| `.perpetual_state.json` (1 MB) | Perpetual learner restarts from scratch | Partially recoverable from logs |

### What the Code Does NOT Do

- No `PRAGMA wal_checkpoint` calls
- No periodic `VACUUM` or `PRAGMA integrity_check`
- No `shutil.copy` or `rsync` of database files
- No write-ahead logging for crash safety
- No database export/import scripts
- No versioned snapshots

---

## 8. Recovery Mechanisms in Code

### Auto-Fix Backup System

The auto-fix system (for code formatting) creates backups in `.auto_fix_backups/` before modifying files. This is a **code-level** backup only, used by the test suite, not a data backup mechanism. Files are tiny (16-52 bytes each, test artifacts only).

### Ollama Backup

`/Volumes/David External/ollama_backup/` contains `.bak` files for decommissioned Ollama model configurations. These are historical artifacts, not an active backup system.

### Memory Index Backup

`memory/index_ollama_backup.npy` (161 KB) is a backup of the old Ollama-era embedding index. The current index is `memory/index.npy` (5 KB, MLX-era).

### What Recovery Code Exists

Searching all Python files for backup/restore/recover/checkpoint/snapshot patterns reveals:

| File | Pattern | Purpose |
|------|---------|---------|
| `training_pipeline.py` | `CHECKPOINTS_DIR` | Defines a checkpoints directory, but it is empty |
| `cognitive/resource_manager.py` | checkpoint references | Memory management, not data backup |
| `tests/test_auto_fix_safety.py` | backup test | Tests the auto-fix backup mechanism |
| `unified_daemon.py` | checkpoint | Process checkpointing (not data) |
| `memory/infinite_context.py` | snapshot | Memory snapshot concept, not disk backup |

**VERDICT: There is no functional recovery mechanism for any database or critical data file.**

---

## 9. Dead Code Archive Inventory (`/Volumes/#1/SAM/dead_code_archive/`)

### Purpose
Archived 2026-01-28 during a major cleanup. Contains code superseded by the current cognitive/ architecture. Originals were NOT deleted -- copies only.

### Categories

| Category | Files | Status |
|----------|-------|--------|
| **Dormant (reusable)** | 5 key files | teacher_student.py (in progress merge), syncWatcher.js (dormant for mobile) |
| **Learners** | 6 files | Superseded by perpetual_learner.py + auto_learner.py |
| **Orchestrators** | 4 files | Superseded by orchestrator.py + cognitive/unified_orchestrator.py |
| **Experiments** | 10 files | Mixed: some extracted to cognitive/, rest dormant |
| **Warp Tauri scripts** | 39 files | ChatGPT/Claude bridges, Frida RE scripts, agent servers |

### Extraction Status

Some archived code has been partially or fully extracted into the current architecture:

| Archived File | Extracted To | Status |
|---------------|-------------|--------|
| `ui_verifier.py` | `cognitive/ui_awareness.py` | COMPLETE |
| `legitimate_extraction.py` | `cognitive/app_knowledge_extractor.py` | COMPLETE |
| `advanced_planner.py` | `cognitive/planning_framework.py` | COMPLETE |
| `efficient_learning.py` | `cognitive/learning_strategy.py` | COMPLETE |
| `project_registry.py` | `startup/project_context.py` | COMPLETE |
| `teacher_student.py` | `perpetual_learner.py` | IN PROGRESS |
| `parallel_learn.py` | `utils/parallel_utils.py` | IN PROGRESS |

---

## 10. Recommendations

### IMMEDIATE (Do Today)

1. **Fix broken symlinks** - The 5 symlinks pointing to `/Volumes/Applications/SAM/` need to be updated to point to actual locations (likely `/Volumes/David External/SAM_models/` or `/Volumes/#1/SAM/`).

2. **Git commit and push** - There are ~2,740 uncommitted file changes. Run `git add` and commit to GitHub immediately.

3. **Back up databases** - Copy `evolution.db` and `auto_learning.db` to `/Volumes/#1/SAM/training_backups/`:
   ```bash
   cp sam_brain/evolution.db /Volumes/#1/SAM/training_backups/evolution_$(date +%Y%m%d).db
   cp sam_brain/auto_learning.db /Volumes/#1/SAM/training_backups/auto_learning_$(date +%Y%m%d).db
   ```

4. **Back up sam_memory** - Copy the entire directory:
   ```bash
   cp -r /Volumes/David\ External/sam_memory/ /Volumes/#1/SAM/training_backups/sam_memory_$(date +%Y%m%d)/
   ```

### SHORT-TERM (This Week)

5. **Create a backup script** (`backup_sam.sh`) that:
   - Copies all `.db` files to `/Volumes/#1/SAM/training_backups/`
   - Copies critical JSON state files
   - Runs `PRAGMA integrity_check` on all databases
   - Rotates backups (keep last 7 days)

6. **Switch databases to WAL mode** for better crash resilience:
   ```sql
   PRAGMA journal_mode=WAL;
   ```

7. **Add graceful degradation** for external drive disconnects - check if paths exist before using them, fall back to in-memory or cached state.

8. **Add a launchd plist** to run the backup script daily.

### MEDIUM-TERM (This Month)

9. **Set up Time Machine** or a manual rsync to an external drive for the internal SSD.

10. **Add database export** capability - dump critical tables to JSONL for portable backup.

11. **Duplicate critical model files** - The sam_fused model (1.6 GB) and adapters (151 MB) exist only on David External with no redundancy. Copy to `/Volumes/#1/`.

12. **Create a disaster recovery runbook** documenting how to rebuild SAM from scratch if the internal SSD dies.

---

## 11. Risk Matrix

| Scenario | Probability | Impact | Current Mitigation | Risk Level |
|----------|------------|--------|-------------------|------------|
| Internal SSD failure | Low | Total code loss | Git (but 2740 files uncommitted) | **CRITICAL** |
| David External disconnects | Medium | No inference, no memory | None | **CRITICAL** |
| Database corruption | Low-Medium | Lose learning/evolution history | None | **HIGH** |
| `/Volumes/#1/` disconnects | Low | Lose training backups, archives | None | **MEDIUM** |
| `/Volumes/Plex/` disconnects | Low | SAM cannot start (no venv) | None | **HIGH** |
| Accidental file deletion | Medium | Varies | Git (partial), dead code archive | **MEDIUM** |
| Model weights corruption | Low | Need to retrain from scratch | 37GB training backup on #1 | **MEDIUM** |

---

*Last updated: 2026-01-29*
*Generated by automated analysis of the SAM ecosystem*
