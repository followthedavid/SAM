# SAM Training Data Inventory

**Generated:** 2026-01-29
**Total estimated storage:** ~49 GB across all locations

---

## 1. Active Training Data (Internal SSD)

### 1.1 auto_training_data/ (Active - MLX LoRA Training)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `sam_brain/auto_training_data/train.jsonl` | 396 KB | 687 | Chat JSONL (messages array) | 2026-01-25 |
| `sam_brain/auto_training_data/valid.jsonl` | 48 KB | 77 | Chat JSONL (messages array) | 2026-01-25 |

- **What reads it:** `auto_learner.py` (generates it), `parity_system.py` (generates it), MLX LoRA training via `training_runner.py`
- **What writes it:** `auto_learner.py` captures Claude Code session data, `parity_system.py` outputs prepared data
- **Content:** Captured conversation pairs from ChatGPT export, formatted as Qwen2.5 chat messages
- **Active in training:** YES - this is the primary dataset fed to MLX LoRA fine-tuning

### 1.2 ~/.sam/training_data/ (Collector Output)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `combined/all_training_data.jsonl` | 3.2 MB | ~3,200 | Instruction JSONL | 2026-01-11 |
| `commits/commit_messages.jsonl` | 318 KB | ~2,500 | Instruction JSONL | 2026-01-04 |
| `training_samples.jsonl` | 436 KB | ~3,000 | Instruction JSONL | 2026-01-19 |
| `roleplay_expanded.jsonl` | 45 KB | ~300 | Instruction JSONL | 2026-01-11 |
| `rust_examples.jsonl` | 20 KB | ~150 | Instruction JSONL | 2026-01-12 |
| `claude_generated_escalation.jsonl` | 3.7 KB | ~20 | Instruction JSONL | 2026-01-19 |
| `claude_generated_personality.jsonl` | 5.3 KB | ~30 | Instruction JSONL | 2026-01-19 |
| `personality_corrections.jsonl` | 816 B | ~5 | Instruction JSONL | 2026-01-15 |
| `bridge_interactions.jsonl` | 608 B | ~5 | Instruction JSONL | 2026-01-15 |
| `code_patterns/patterns.db` | 40 KB | N/A | SQLite | 2026-01-25 |
| `documentation/` | ~empty | - | - | 2026-01-25 |
| `manifest.json` | 333 B | N/A | JSON manifest | 2026-01-04 |

- **What reads it:** `training_pipeline.py` (loads from TRAINING_DATA path), `training_prep.py` (load_data)
- **What writes it:** `training_data_collector.py` (main collector - extracts from git commits, dedup DB, SSOT docs, routing patterns)
- **Active in training:** PARTIALLY - some data gets merged into the active training set

---

## 2. External Drive: /Volumes/David External/sam_training/ (2.8 GB total)

### 2.1 Primary Training Files

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `sam_training.jsonl` | 23 MB | 11,336 | Instruction JSONL | 2026-01-16 |
| `sam_training_train.jsonl` | 20 MB | 10,202 | Instruction JSONL | 2026-01-16 |
| `sam_training_val.jsonl` | 2.2 MB | 1,134 | Instruction JSONL | 2026-01-16 |
| `train.jsonl` | 20 MB | 10,452 | Instruction JSONL | 2026-01-17 |
| `valid.jsonl` | 2.2 MB | 1,134 | Instruction JSONL | 2026-01-17 |
| `context_attention.jsonl` | 64 KB | 150 | JSONL | 2026-01-17 |
| `personality_examples.jsonl` | 16 KB | 20 | JSONL | 2026-01-16 |

- **What reads it:** `training_data.py` (TrainingDataStore, DB at this path), `training_runner.py` (jobs dir here)
- **What writes it:** `training_data.py` (export_to_jsonl), `training_capture.py` (batch flush)
- **Active in training:** YES - `train.jsonl`/`valid.jsonl` are used by training pipeline

### 2.2 training_data.db (SQLite Training Store)

| File | Size | Format | Last Updated |
|------|------|--------|-------------|
| `training_data.db` | 80 KB | SQLite | 2026-01-25 |

- **What reads/writes it:** `training_data.py` (TrainingDataStore class) - central storage for all training examples
- **Schema:** training_examples, export_history, training_runs, validation_log, stats_cache tables
- **Active in training:** YES - master training data store

### 2.3 processed/ (Category-Split Training Data)

| File | Size | Format | Last Updated |
|------|------|--------|-------------|
| `processed/train.jsonl` | 34 MB | Chat JSONL | 2026-01-25 |
| `processed/valid.jsonl` | 3.7 MB | Chat JSONL | 2026-01-25 |
| `processed/category_code_general/train.jsonl` | 4.7 MB | Chat JSONL | 2026-01-25 |
| `processed/category_code_explanation/train.jsonl` | 182 KB | Chat JSONL | 2026-01-25 |
| `processed/category_code_generation/` | varies | Chat JSONL | 2026-01-25 |
| `processed/category_debugging/` | varies | Chat JSONL | 2026-01-25 |
| `processed/category_explanation/` | varies | Chat JSONL | 2026-01-25 |
| `processed/category_general/` | varies | Chat JSONL | 2026-01-25 |
| `processed/category_planning/` | varies | Chat JSONL | 2026-01-25 |
| `processed/category_reasoning/` | varies | Chat JSONL | 2026-01-25 |
| `processed/processing_stats.json` | 564 B | JSON | 2026-01-25 |

- **What writes it:** ChatGPT export processing pipeline (category-stratified splits)
- **Active in training:** YES - most recent processed dataset

### 2.4 feedback_derived/ (DPO Training Pairs)

| Files | Count | Format | Date Range |
|-------|-------|--------|------------|
| `feedback_dpo_*.jsonl` | 9 files | DPO JSONL (chosen/rejected) | 2026-01-24 to 2026-01-27 |
| `feedback_instruction_*.jsonl` | 9 files | Instruction JSONL | 2026-01-24 to 2026-01-27 |
| `feedback_correction_*.jsonl` | 1 file | Correction JSONL | 2026-01-24 |

- **What writes it:** `training_capture.py` (CorrectionCapture, ConversationCapture), feedback system
- **Each file:** ~300-600 bytes (individual feedback pairs)
- **Active in training:** YES - feeds into DPO training

### 2.5 distilled/ (Knowledge Distillation)

| File | Size | Format | Last Updated |
|------|------|--------|-------------|
| `distillation.db` | 116 KB | SQLite | 2026-01-24 |
| `exports/distilled_instruction_*.jsonl` | 1.4 KB | Instruction JSONL | 2026-01-24 |
| `exports/corrections_distilled_*.jsonl` | 891 B | Instruction JSONL | 2026-01-24 |

- **What writes it:** Knowledge distillation pipeline
- **Active in training:** MINIMAL - small dataset so far

### 2.6 merged/

| File | Size | Format | Last Updated |
|------|------|--------|-------------|
| `merged_training_20260124_170329.jsonl` | 2.9 KB | JSONL | 2026-01-24 |

- **Purpose:** Merged training data from multiple feedback sources
- **Active in training:** NO - superseded by processed/ data

### 2.7 chatgpt_export/ (Raw ChatGPT Data Export)

| Item | Size | Format |
|------|------|--------|
| `chatgpt_export/` (total) | 2.7 GB | Mixed (JSON, audio, video) |
| `conversations.json` | 197 MB | JSON (raw ChatGPT export) |
| Audio files (WAV) | ~2 GB | WAV audio from voice conversations |
| Video files (MP4) | ~500 MB | Video from conversations |

- **What reads it:** `build_training_data.py` (SAM scrapers), chatgpt processing scripts
- **Purpose:** Raw source material - David's ChatGPT conversations for personality training
- **Active in training:** INDIRECTLY - processed into chatgpt_training JSONL files

---

## 3. External Drive: /Volumes/#1/SAM/training_data/ (5.3 GB total)

### 3.1 SAM_master_training/ (Curated SAM Personality Data)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `train.jsonl` | 42 MB | 19,246 | Chat JSONL | 2026-01-25 |
| `valid.jsonl` | 4.8 MB | 2,139 | Chat JSONL | 2026-01-25 |
| `coding.jsonl` | 24 MB | 8,883 | Chat JSONL | 2026-01-25 |
| `personality.jsonl` | 208 KB | 93 | Chat JSONL | 2026-01-25 |
| `planning.jsonl` | 2.2 MB | 902 | Chat JSONL | 2026-01-25 |
| `roleplay.jsonl` | 20 MB | 11,507 | Chat JSONL | 2026-01-25 |

- **What reads it:** MLX training pipeline (train.jsonl/valid.jsonl are the split versions)
- **What writes it:** Data curation pipeline, `build_training_data.py`
- **Content:** SAM personality + coding + roleplay + planning combined
- **Active in training:** YES - primary curated training set

### 3.2 chatgpt_training/ (Processed ChatGPT Conversations)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `chatgpt_all.jsonl` | 71 MB | 20,978 | Chat JSONL | 2026-01-25 |
| `chatgpt_coding.jsonl` | 23 MB | 6,114 | Chat JSONL | 2026-01-25 |
| `chatgpt_roleplay.jsonl` | 24 MB | 6,737 | Chat JSONL | 2026-01-25 |
| `chatgpt_planning.jsonl` | 17 MB | 4,354 | Chat JSONL | 2026-01-25 |
| `chatgpt_general.jsonl` | 5.4 MB | 3,403 | Chat JSONL | 2026-01-25 |
| `chatgpt_coaching.jsonl` | 1.5 MB | 370 | Chat JSONL | 2026-01-25 |

- **What writes it:** ChatGPT export processing (converts raw conversations.json to categorized JSONL)
- **Content:** David's ChatGPT conversations split by topic category
- **Active in training:** YES - feeds into SAM_master_training

### 3.3 instruction_datasets/ (Public Instruction Datasets)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `combined_training.jsonl` | 352 MB | 178,033 | JSONL | 2026-01-15 |
| `dolly/dolly-15k.jsonl` | 12 MB | 15,010 | JSONL | - |
| `open_assistant/oasst_trees.jsonl` | 159 MB | 10,364 | JSONL | - |
| `ultrachat/ultrachat_sample.jsonl` | 919 MB | 150,000 | JSONL | - |
| `code_alpaca/code_alpaca_20k.json` | 7.7 MB | ~20,000 | JSON | - |
| `evol_instruct/evol_instruct_143k.json` | 358 MB | ~143,000 | JSON | - |
| `sharegpt/sharegpt_v3.json` | 642 MB | ~90,000 convos | JSON | - |

- **What reads it:** `build_training_data.py`, data mixing pipeline
- **Content:** Public open-source instruction-following datasets
- **Active in training:** PARTIALLY - combined_training.jsonl is the merged version used

### 3.4 chatgpt_export/ (Duplicate Raw Export)

| Item | Size | Format |
|------|------|--------|
| `chatgpt_export/` (total) | 2.7 GB | Mixed (JSON, WAV, MP4) |
| `conversations.json` | 197 MB | JSON (22 conversation threads with audio/video) |

- **Purpose:** Second copy of David's ChatGPT data export (also on David External)
- **Active in training:** NO - duplicate; the David External copy is the primary

### 3.5 code_patterns/

| File | Size | Lines | Format |
|------|------|-------|--------|
| `training_examples.jsonl` | 0 B | 0 | JSONL (empty) |
| `patterns.db` | 40 KB | N/A | SQLite |

- **What writes it:** `training_data_collector.py` (code pattern extraction from dedup DB)
- **Active in training:** NO - empty JSONL, only DB populated

---

## 4. Training Backup: /Volumes/#1/SAM/training_backups/ (37 GB)

| File | Size | Lines | Format | Last Updated |
|------|------|-------|--------|-------------|
| `SAM_Backup/all_training.jsonl` | 37 GB | unknown | JSONL | 2026-01-11 |

- **Purpose:** Massive consolidated backup of all training data
- **Active in training:** NO - backup only
- **Note:** At 37 GB, this likely contains raw unprocessed data or duplicates

---

## 5. Voice Training Data: /Volumes/David External/SAM_Voice_Training/ (8.7 GB total)

### 5.1 Source Videos (Dustin Steele)

| Item | Count | Size | Format |
|------|-------|------|--------|
| Source MP4 videos | 28 files | ~7.7 GB | MP4 video |
| `dustin_reference.wav` | 1 file | ~5 MB | WAV reference |

### 5.2 Extracted Audio

| Directory | Size | File Count | Format | Purpose |
|-----------|------|-----------|--------|---------|
| `extracted_audio/` | 637 MB | 29 files | WAV | Raw audio extracted from videos |
| `extracted_dustin_full/` | 72 MB | 17 files | WAV | Full Dustin speech segments |
| `extracted_dustin/` | 0 B | 0 files | WAV | Empty (incomplete extraction) |
| `dustin_speech/` | 97 MB | 30 files | WAV | Isolated speech segments |
| `dustin_verified/` | 6.7 MB | 14 files | WAV | Verified clean speech clips |
| `dustin_moaning/` | 16 MB | varies | WAV | Vocal samples (non-speech) |
| `moaning_only/` | 122 MB | varies | WAV | Vocal samples (non-speech) |

- **What reads it:** `voice/voice_trainer.py` (VoiceTrainer class), RVC training pipeline
- **What writes it:** Audio extraction scripts, manual curation
- **Active in training:** YES - `dustin_verified/` is the curated RVC training set
- **Pipeline:** Videos -> `extracted_audio/` -> `dustin_speech/` -> `dustin_verified/` (final)

---

## 6. Code That Reads/Writes Training Data

### Writers (Data Generation)

| File | What It Generates | Output Location |
|------|-------------------|-----------------|
| `training_data_collector.py` | Git commits, code patterns, docs, routing | `~/.sam/training_data/` |
| `training_capture.py` | Claude escalation captures, corrections (DPO) | External `training_data.db` + batch JSONL |
| `training_data.py` | SQLite store, JSONL exports | External `sam_training/` |
| `auto_learner.py` | Claude Code session captures | `auto_training_data/` |
| `parity_system.py` | Parity check training data | `auto_training_data/` |
| `build_training_data.py` (scrapers) | Fashion, roleplay, code, psychology content | `/Volumes/#1/SAM/training_data/` |

### Readers (Training Pipeline)

| File | What It Reads | Purpose |
|------|---------------|---------|
| `training_pipeline.py` | `training_data.jsonl` (local) | Legacy pipeline, loads + trains |
| `training_prep.py` | Any JSONL directory | Converts to MLX format, splits train/val/test |
| `training_runner.py` | `train.jsonl` + `valid.jsonl` | MLX LoRA job execution |
| `training_scheduler.py` | Scheduled data gathering | Periodic mining, dedup, quality checks |
| `training_stats.py` | Training DB | Statistics dashboard |
| `voice/voice_trainer.py` | Audio WAV files | RVC voice cloning |

---

## 7. Summary: What Is Actively Used?

### Text/LLM Training (MLX LoRA on Qwen2.5-1.5B)

| Dataset | Location | Status |
|---------|----------|--------|
| `auto_training_data/train.jsonl` (687 lines) | Internal SSD | ACTIVE - current training input |
| `sam_training/processed/train.jsonl` (34 MB) | David External | ACTIVE - processed ChatGPT data |
| `SAM_master_training/train.jsonl` (19K lines) | #1 drive | ACTIVE - curated personality + skills |
| `training_data.db` (80 KB) | David External | ACTIVE - central example store |
| `feedback_derived/*.jsonl` | David External | ACTIVE - DPO pairs from corrections |

### Voice Training (RVC)

| Dataset | Location | Status |
|---------|----------|--------|
| `dustin_verified/` (14 clips, 6.7 MB) | David External | ACTIVE - clean voice clips for RVC |
| `dustin_speech/` (30 clips, 97 MB) | David External | STAGING - needs further curation |

### Inactive / Archival

| Dataset | Location | Status |
|---------|----------|--------|
| `all_training.jsonl` (37 GB) | #1 Backups | BACKUP - not used directly |
| `instruction_datasets/` (2.4 GB) | #1 drive | ARCHIVE - public datasets, used in mixing |
| `chatgpt_export/` (2.7 GB x2) | Both drives | SOURCE - raw data, processed elsewhere |
| `code_patterns/training_examples.jsonl` | #1 drive | EMPTY - never populated |

---

## 8. Known Issues

1. **Duplicate chatgpt_export:** Exists on both `/Volumes/David External/` and `/Volumes/#1/` (2.7 GB each). Consider removing one copy.
2. **37 GB backup:** `all_training.jsonl` on #1 backups is enormous and may contain unfiltered/duplicate data. Verify if still needed.
3. **Empty datasets:** `code_patterns/training_examples.jsonl` on #1 is empty (0 bytes). The collector ran but produced no output.
4. **training_data.jsonl missing:** `training_pipeline.py` expects `sam_brain/training_data.jsonl` but this file does not exist. The pipeline would find 0 samples.
5. **Conversations symlink:** `/Volumes/David External/sam_training/conversations.json` points to a nested path that exists but is fragile.
6. **Small training_data.db:** At 80 KB the SQLite store has very few examples - most training data lives in flat JSONL files outside this store.
7. **DPO feedback files are tiny:** Each feedback_derived file is ~300-600 bytes (1-2 examples each). These should be periodically merged.
