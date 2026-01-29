# SAM Training Pipeline Deep Dive

**Date:** 2026-01-29
**Scope:** Complete analysis of all training-related Python files
**Files Analyzed:** 8 files (build_training_data.py does not exist)

---

## 1. Complete Training Workflow End-to-End

The training pipeline has **four distinct phases**, handled by different files:

```
PHASE 1: Data Collection
  training_data_collector.py  -- Mine raw data from git, code, docs
  training_capture.py         -- Capture live interactions & corrections

PHASE 2: Data Storage & Quality
  training_data.py            -- SQLite-backed unified storage (TrainingDataStore)
  training_stats.py           -- Statistics dashboard & health monitoring

PHASE 3: Data Preparation & Scheduling
  training_prep.py            -- Convert to MLX format, tokenize, split train/val/test
  training_scheduler.py       -- Periodic job scheduling for mining/dedup/quality/export

PHASE 4: Training Execution
  training_pipeline.py        -- High-level orchestrator (simpler, legacy)
  training_runner.py          -- Full-featured job runner with memory monitoring
```

### End-to-End Flow

```
1. COLLECT: training_data_collector.py mines git repos, code dedup DB, SSOT docs
   --> Outputs JSONL to ~/.sam/training_data/{commits,code_patterns,knowledge,routing}/

2. CAPTURE: training_capture.py hooks into escalation_handler.py and feedback_system.py
   --> Claude escalation responses become training examples (DPO or chat format)
   --> User corrections become DPO pairs (chosen=correction, rejected=SAM's wrong answer)
   --> Stores into TrainingDataStore (SQLite on external drive)

3. VALIDATE: training_data.py runs auto_validate_all()
   --> Checks: empty content, length, repetition, completeness
   --> Assigns quality tiers: gold/silver/bronze/unverified
   --> Deduplication via content_hash and input_hash

4. PREPARE: training_prep.py converts to MLX format
   --> Applies Qwen2.5 chat template (<|im_start|>/<|im_end|>)
   --> Tokenizes with Qwen tokenizer (or estimates ~4 chars/token)
   --> Truncates to max_seq_length (default 512 tokens)
   --> Splits: 90% train / 5% val / 5% test (stratified by domain)
   --> Writes train.jsonl, valid.jsonl, test.jsonl

5. TRAIN: training_runner.py or training_pipeline.py invokes MLX LoRA
   --> Runs: python -m mlx_lm.lora with config params
   --> Monitors memory, auto-pauses if free RAM < 0.3GB
   --> Tracks loss curves, ETA, metrics history

6. DEPLOY: Adapters copied to /Volumes/David External/sam_models/adapters/
   --> mlx_cognitive.py loads adapters at runtime via adapter_path config
```

---

## 2. What Data Goes In, What Model Comes Out

### Data Sources (Input)

| Source | File | Format | Description |
|--------|------|--------|-------------|
| Git commits | training_data_collector.py | instruction | Commit message prediction from diff summaries |
| Code patterns | training_data_collector.py | instruction | Code analysis from dedup database files |
| Project docs | training_data_collector.py | instruction | Knowledge Q&A from SSOT markdown files |
| Task routing | training_data_collector.py | instruction | Which LLM handles which task type |
| Claude escalations | training_capture.py | chat or DPO | Claude responses SAM couldn't handle |
| User corrections | training_capture.py | DPO | User-corrected SAM mistakes |
| User preferences | training_capture.py | DPO | User-preferred alternative responses |
| Positive feedback | training_data.py | instruction | Interactions users rated positively |
| Knowledge distillation | training_data.py | chat | Distilled from larger models |

### Training Data Formats

All data ultimately converts to one of these for MLX:

- **Instruction:** `{"instruction": "...", "input": "...", "output": "..."}`
- **Chat (Qwen template):** `{"messages": [{"role":"system",...}, {"role":"user",...}, {"role":"assistant",...}]}`
- **DPO:** `{"prompt": "...", "chosen": "...", "rejected": "..."}`
- **Completion:** `{"text": "<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n...<|im_end|>"}`

### Storage Locations (Current State)

| Location | Contents |
|----------|----------|
| `~/.sam/training_data/` | JSONL files from training_data_collector.py (commits, code_patterns, knowledge, routing) |
| `/Volumes/David External/sam_training/training_data.db` | SQLite database from TrainingDataStore (training_data.py) |
| `/Volumes/David External/sam_training/` | Exported JSONL, train/valid splits, conversation captures |
| `/Volumes/David External/sam_training/batches/` | Auto-flushed capture batches |

### Model Output

- **Base model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct` (training_pipeline.py) or `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` (training_runner.py)
- **Output:** LoRA adapter weights (not a full model)
- **Adapter location:** `/Volumes/David External/sam_models/adapters/`
- **Existing adapters (12 versions):**
  - `sam_lora`, `sam_lora_v2`
  - `sam_lora_1.5b`, `sam_lora_1.5b_v2`, `sam_lora_1.5b_576`, `sam_lora_1.5b_640`, `sam_lora_1.5b_768`, `sam_lora_1.5b_1024`
  - `sam_lora_3b`, `sam_lora_3b_320`, `sam_lora_3b_384`, `sam_lora_3b_384v2`, `sam_lora_3b_lite`

---

## 3. How Are Training Jobs Scheduled?

### TrainingDataScheduler (training_scheduler.py)

Four default scheduled jobs, managed via `~/.sam/scheduler/`:

| Job ID | Name | Type | Interval | Purpose |
|--------|------|------|----------|---------|
| `mining_code` | Code Pattern Mining | mining | 6 hours | Extract from git repos and dedup DB |
| `dedup_cleanup` | Data Deduplication | deduplication | 24 hours | MD5 hash-based exact dedup on JSONL files |
| `quality_check` | Quality Validation | quality_check | 12 hours | Validate format, length, content of all JSONL |
| `export_training` | Training Export | export | 24 hours | Export quality-filtered data to dated train_YYYYMMDD.jsonl |

### Scheduler Architecture

- **State persistence:** `~/.sam/scheduler/jobs.json` and `~/.sam/scheduler/history.json`
- **Main loop:** Checks every 60 seconds if any job is due (based on `next_run` timestamp)
- **PID file:** `~/.sam/scheduler/scheduler.pid` for single-instance guarantee
- **Resource checks:** Uses `psutil` to verify available RAM before each job
- **RAM requirements:** mining=0.5GB, dedup=0.3GB, quality_check=0.5GB, export=0.2GB
- **Daemon integration:** Can register with `unified_daemon.py` as a low-priority auto-restart service

### Scheduler CLI

```bash
python3 training_scheduler.py start    # Run scheduler in foreground
python3 training_scheduler.py stop     # Stop scheduler
python3 training_scheduler.py status   # Show job status
python3 training_scheduler.py run --job mining_code  # Run a job immediately
python3 training_scheduler.py register # Register with unified daemon
```

---

## 4. What Triggers Training?

There are **two trigger mechanisms**, both manual:

### training_pipeline.py (Legacy, Simpler)

Training is triggered by `should_train()` which checks:
1. At least **100 samples** in `training_data.jsonl` (MIN_SAMPLES_FOR_TRAINING)
2. The sample count exceeds the last completed training run's count

```bash
python3 training_pipeline.py train   # Triggers if should_train() is True
python3 training_pipeline.py force   # Bypasses threshold check
```

### training_runner.py (Full-Featured)

Training is triggered explicitly via CLI or API:

```bash
python3 training_runner.py start /path/to/data --epochs 1 --lora-rank 4
```

Or programmatically:
```python
runner = TrainingJobRunner()
config = TrainingConfig(data_dir="/path/to/data")
job = runner.start_training(config)
```

### What Does NOT Exist (Gap)

There is **no automatic trigger** that says "enough new data has accumulated, start training." The scheduler handles data collection/quality/export, but does not automatically kick off training_runner.py. Training must be manually initiated.

---

## 5. Where Are Trained Adapters Stored?

### Training Output Paths

| System | Output Location |
|--------|----------------|
| training_pipeline.py | `sam_brain/models/sam-coder-YYYYMMDD_HHMMSS/adapters/` |
| training_runner.py | `/Volumes/David External/sam_training/jobs/YYYYMMDD_HHMMSS/output/adapters/` |

### Production Adapter Location

The cognitive engine (`cognitive/mlx_cognitive.py`) loads adapters from:

```python
# 1.5B model (primary)
adapter_path = Path("/Volumes/David External/sam_models/adapters/sam_lora_1.5b_v2")
lora_layers = 4

# 3B model (complex tasks)
adapter_path = Path("/Volumes/David External/sam_models/adapters/sam_lora_3b_lite")
lora_layers = 2
```

### Existing Adapters on Disk

12 adapter versions exist at `/Volumes/David External/sam_models/adapters/`, with corresponding training logs at `/Volumes/David External/sam_models/training_*.log`. The naming convention suggests iterative refinement with different sequence lengths (576, 640, 768, 1024) and model sizes (1.5B, 3B).

---

## 6. How Are Adapters Deployed to Production?

### Current Deployment Process (Manual)

1. Training outputs adapters to a job-specific directory
2. Someone manually copies/renames the adapter directory to `/Volumes/David External/sam_models/adapters/sam_lora_1.5b_v2` (or whichever slot)
3. The cognitive engine loads the adapter at next model load (or restart)

### Adapter Loading in mlx_cognitive.py

```python
# If adapter_path exists, load model with adapter
if config.adapter_path.exists():
    model, tokenizer = load(
        config.model_id,
        adapter_path=str(config.adapter_path)
    )
```

### Legacy Ollama Export (Obsolete)

`training_pipeline.py` has an `export_to_ollama()` method that creates an Ollama Modelfile, but Ollama is decommissioned as of 2026-01-18. This code path is dead.

### What Does NOT Exist (Gap)

There is **no automated deployment pipeline**. No A/B testing, no validation gate, no automatic rollback. The `model_deployment.py` mentioned in `docs/TRAINING_PIPELINE.md` was not among the files requested for analysis, but the core pipeline files have no deployment automation built in.

---

## 7. What's Working vs Broken

### WORKING

| Component | Status | Evidence |
|-----------|--------|----------|
| Data collection (training_data_collector.py) | Working | Output exists at `~/.sam/training_data/` with commits, code_patterns, knowledge, routing subdirs |
| Training data schema (training_data.py) | Working | SQLite DB exists at `/Volumes/David External/sam_training/training_data.db` |
| Training capture hooks (training_capture.py) | Working (code-complete) | Full PII detection, quality evaluation, domain classification, DPO pair generation |
| Data preparation (training_prep.py) | Working (code-complete) | Qwen chat template, tokenization, stratified splitting, validation |
| Training execution (training_runner.py) | Working | 12 adapter versions trained successfully, logs exist on external drive |
| MLX LoRA training | Working | Adapters loaded and used by cognitive engine in production |
| Training stats (training_stats.py) | Working (code-complete) | Full stats dashboard with API integration |
| Adapter loading (mlx_cognitive.py) | Working | `sam_lora_1.5b_v2` and `sam_lora_3b_lite` configured as production adapters |

### NOT WORKING / NEVER RUN

| Component | Status | Evidence |
|-----------|--------|----------|
| Training scheduler (training_scheduler.py) | Never run | All jobs show `run_count: 0`, `last_run: null`, `next_run: null` |
| Automated training triggers | Does not exist | No code connects scheduler to training_runner |
| Automated deployment | Does not exist | No pipeline from training output to production adapter slot |
| build_training_data.py | Does not exist | File was requested but not found in the project |
| Ollama export | Obsolete | Ollama decommissioned 2026-01-18, dead code in training_pipeline.py |

### STRUCTURAL ISSUES

1. **Two competing pipeline orchestrators:** `training_pipeline.py` (legacy, simpler, uses `Qwen/Qwen2.5-Coder-1.5B-Instruct` full-precision) and `training_runner.py` (newer, 8GB-optimized, uses 4-bit quantized model). They are not integrated and have different config defaults.

2. **Two competing data paths:**
   - `training_data_collector.py` writes JSONL files to `~/.sam/training_data/`
   - `training_data.py` (TrainingDataStore) writes to SQLite on external drive
   - `training_pipeline.py` reads from `sam_brain/training_data.jsonl` (which does not exist)
   - There is no unified path from collection to training.

3. **training_pipeline.py inconsistencies:**
   - Reads from `training_data.jsonl` in `sam_brain/` (file does not exist)
   - Uses `BATCH_SIZE = 4` which contradicts the 8GB constraint documented in training_runner.py (`batch_size = 1`)
   - Uses full-precision base model name, not the 4-bit quantized version
   - Has `MIN_SAMPLES_FOR_TRAINING = 100` but the training data file doesn't exist

4. **Scheduler registered but never started:** The `~/.sam/scheduler/jobs.json` has all four jobs with `run_count: 0`. The scheduler has never been started as a daemon.

5. **No validation gate before deployment:** Training runs produce adapters, but there is no automated check (e.g., val loss threshold, eval benchmark) before an adapter is promoted to production.

6. **DPO training not implemented:** `training_capture.py` generates DPO pairs (chosen/rejected), and `training_prep.py` supports DPO format, but `training_runner.py` invokes `mlx_lm.lora` which is SFT (supervised fine-tuning), not DPO. The DPO data is collected but the training command doesn't use it as DPO -- it just takes the "chosen" response.

---

## File-by-File Summary

### training_data_collector.py (401 lines)
- **Purpose:** Batch extraction of training data from local sources
- **Sources:** Git repos (commit messages + diffs), code dedup SQLite DB, SSOT markdown docs, synthetic routing examples
- **Output:** JSONL files in instruction format to `~/.sam/training_data/`
- **CLI:** `python3 training_data_collector.py` (runs all four phases)

### training_data.py (1281 lines)
- **Purpose:** Unified training data schema + SQLite storage
- **Key class:** `TrainingDataStore` -- full CRUD, deduplication, quality validation, export to JSONL
- **Key class:** `TrainingExample` -- dataclass with 20+ fields including DPO, multi-turn, quality tiers
- **Storage:** SQLite at `/Volumes/David External/sam_training/training_data.db` (falls back to `~/.sam/`)
- **Tables:** training_examples, export_history, training_runs, validation_log, stats_cache

### training_capture.py (1227 lines)
- **Purpose:** Real-time capture of training data from live system
- **Key classes:**
  - `ConversationCapture` -- hooks into escalation_handler.py, captures Claude responses as chat/DPO examples
  - `CorrectionCapture` -- hooks into feedback_system.py, captures user corrections as DPO pairs
  - `PIIDetector` -- regex-based detection and redaction of emails, phones, SSNs, API keys, passwords, paths
  - `QualityEvaluator` -- heuristic scoring (length, patterns, repetition, completeness)
- **Integration hooks:** `capture_from_escalation_handler()`, `capture_from_feedback()`

### training_prep.py (780 lines)
- **Purpose:** Convert raw examples to MLX-ready training format
- **Key class:** `TrainingDataPrep`
  - Loads JSONL files, detects format (instruction/chat/DPO)
  - Applies Qwen2.5 chat template with SAM system prompt
  - Tokenizes (real tokenizer or ~4 chars/token estimate)
  - Truncates to max_seq_length (default 512)
  - Domain-stratified splitting: 90/5/5 train/val/test
  - Writes `train.jsonl`, `valid.jsonl`, `test.jsonl` + manifest

### training_runner.py (981 lines)
- **Purpose:** Full training job lifecycle management
- **Key class:** `TrainingJobRunner`
  - Starts `python -m mlx_lm.lora` as subprocess
  - Parses stdout for `Iter X: train loss Y, val loss Z, it/s A` metrics
  - Memory monitoring thread: auto-pause if free RAM < 0.3GB, auto-resume at 0.5GB
  - Job persistence to `/Volumes/David External/sam_training/jobs/`
  - Loss curve plotting via matplotlib
  - ETA estimation from rolling step times
- **8GB defaults:** batch_size=1, grad_accumulation=4, lora_rank=4, max_seq_length=512, gradient_checkpointing=True

### training_scheduler.py (943 lines)
- **Purpose:** Periodic scheduling of data maintenance jobs
- **Key class:** `TrainingDataScheduler`
  - Four default jobs: mining (6h), dedup (24h), quality_check (12h), export (24h)
  - Main loop checks every 60s, resource-aware (checks RAM before running)
  - State persisted to `~/.sam/scheduler/`
  - Can register with `unified_daemon.py`
- **Current state:** All jobs at run_count=0, never executed

### training_pipeline.py (334 lines)
- **Purpose:** Simpler, legacy training orchestrator
- **Key class:** `TrainingPipeline`
  - Loads data from `training_data.jsonl` (does not exist)
  - 90/10 train/val split (no test set)
  - Converts to chat format for Qwen
  - Runs `mlx_lm.lora` directly
  - Has Ollama export (dead code)
- **Status:** Partially superseded by training_runner.py

### training_stats.py (776 lines)
- **Purpose:** Statistics dashboard for training data health
- **Key class:** `TrainingDataStats`
  - Analyzes JSONL files and distillation database
  - Overall stats, daily trends, per-source health scores
  - 5-minute cache with file-based persistence
  - API-ready: `api_training_stats()`, `api_training_daily()`, `api_training_sources()`

---

## Recommendations (Observations Only)

1. The scheduler has never been started -- all data maintenance is manual
2. `training_pipeline.py` reads from a non-existent file and should probably be retired in favor of `training_runner.py`
3. The data flow from collection to training is fragmented across two storage systems (JSONL files vs SQLite)
4. DPO pairs are collected but never used for actual DPO training
5. No automated path from "training completes" to "adapter deployed to production"
6. The `build_training_data.py` file referenced in the original request does not exist
