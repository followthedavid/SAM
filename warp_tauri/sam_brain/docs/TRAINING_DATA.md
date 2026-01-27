# SAM Training Data Pipeline Documentation

**Phase 5.1.12: Complete documentation for training data system**
**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/TRAINING_DATA.md`
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Schema](#data-schema)
4. [Data Sources](#data-sources)
5. [Quality Criteria](#quality-criteria)
6. [Pipeline Workflow](#pipeline-workflow)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Monitoring & Stats](#monitoring--stats)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The SAM Training Data Pipeline is a comprehensive system for collecting, validating, and preparing training data for SAM's MLX fine-tuning process. It supports multiple data sources, quality tiers, and automated scheduling.

### Key Features

- **Multi-source data collection**: Git commits, code patterns, documentation, conversations
- **Quality tiering**: Gold, Silver, Bronze, Raw quality levels
- **Automated scheduling**: Periodic mining, deduplication, and validation
- **Resource-aware**: Integrates with unified_daemon.py for RAM management
- **Stats dashboard**: Real-time visibility into data pipeline health

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Stats Dashboard | `training_stats.py` | Statistics and monitoring |
| Scheduler | `training_scheduler.py` | Automated job management |
| Collector | `training_data_collector.py` | Multi-source data extraction |
| Pipeline | `training_pipeline.py` | MLX fine-tuning orchestration |
| Tests | `tests/test_training_data.py` | Comprehensive test coverage |

---

## Architecture

```
                                ┌─────────────────────────────────────┐
                                │       Data Sources                   │
                                ├─────────────────────────────────────┤
                                │ • Git Commits                        │
                                │ • Code Dedup Database                │
                                │ • SSOT Documentation                 │
                                │ • Conversation Capture               │
                                │ • Knowledge Distillation             │
                                │ • Manual Curation                    │
                                └─────────────┬───────────────────────┘
                                              │
                                              ▼
                                ┌─────────────────────────────────────┐
                                │   Training Data Collector            │
                                │   (training_data_collector.py)       │
                                │                                      │
                                │ • Extract from sources               │
                                │ • Format conversion                  │
                                │ • Initial deduplication              │
                                └─────────────┬───────────────────────┘
                                              │
                                              ▼
                                ┌─────────────────────────────────────┐
                                │   Training Data Scheduler            │
                                │   (training_scheduler.py)            │
                                │                                      │
                                │ • Periodic mining jobs               │
                                │ • Quality validation                 │
                                │ • Deduplication                      │
                                │ • Export preparation                 │
                                └─────────────┬───────────────────────┘
                                              │
                                              ▼
                                ┌─────────────────────────────────────┐
                                │   Training Data Store                │
                                │   (training_data/)                   │
                                │                                      │
                                │ • JSONL files by source              │
                                │ • Manifest tracking                  │
                                │ • Quality metadata                   │
                                └─────────────┬───────────────────────┘
                                              │
                                              ▼
                                ┌─────────────────────────────────────┐
                                │   Training Pipeline                  │
                                │   (training_pipeline.py)             │
                                │                                      │
                                │ • Data preparation                   │
                                │ • MLX LoRA fine-tuning               │
                                │ • Model evaluation                   │
                                │ • Adapter deployment                 │
                                └─────────────────────────────────────┘
```

### Data Flow

1. **Collection**: Data is extracted from multiple sources by `training_data_collector.py`
2. **Scheduling**: `training_scheduler.py` runs periodic jobs for mining, validation, deduplication
3. **Storage**: Data is stored in `training_data/` directory as JSONL files
4. **Quality Check**: Examples are validated and assigned quality tiers
5. **Training**: `training_pipeline.py` prepares data and runs MLX LoRA fine-tuning
6. **Monitoring**: `training_stats.py` provides real-time visibility

---

## Data Schema

### Primary Training Format: Instruction

The primary format for training data is the instruction format, compatible with MLX fine-tuning:

```json
{
  "instruction": "The task or question for SAM to respond to",
  "input": "Optional additional context or input data",
  "output": "The expected response from SAM",
  "metadata": {
    "source": "git_commits|code_patterns|knowledge|distillation|manual",
    "quality_tier": "gold|silver|bronze|raw",
    "quality_score": 0.85,
    "timestamp": "2026-01-25T10:30:00Z",
    "validated": true,
    "human_reviewed": false
  }
}
```

### Chat Format

Alternative format for conversational data:

```json
{
  "messages": [
    {"role": "user", "content": "User message here"},
    {"role": "assistant", "content": "SAM's response here"}
  ],
  "metadata": {
    "source": "conversation_capture",
    "quality_tier": "silver",
    "timestamp": "2026-01-25T10:30:00Z"
  }
}
```

### Completion Format

Simple prompt-completion pairs:

```json
{
  "prompt": "Given this code:\n```python\ndef add(a, b):\n```\nComplete the function.",
  "completion": "    return a + b",
  "metadata": {
    "source": "code_patterns",
    "quality_tier": "bronze"
  }
}
```

### Quality Tiers

| Tier | Quality Score | Criteria |
|------|---------------|----------|
| **Gold** | 0.9+ | Human-verified, explicit corrections, high-value examples |
| **Silver** | 0.7-0.9 | Auto-validated, good structure, reasonable length |
| **Bronze** | 0.5-0.7 | Basic format validation passed |
| **Raw** | <0.5 | Unvalidated, needs review |

---

## Data Sources

### 1. Git Commits

**Source**: Repository commit history
**Collector**: `extract_git_commits()` in `training_data_collector.py`

Extracts commit messages and diffs to teach SAM how to write good commit messages.

```json
{
  "instruction": "Given these code changes in sam_brain, write a commit message.",
  "input": "training_stats.py | 150 +++\ntraining_scheduler.py | 200 +++",
  "output": "feat: add training data statistics and scheduler"
}
```

**Quality Indicators**:
- Commit message length > 10 characters
- Has associated diff summary
- From active project

### 2. Code Patterns

**Source**: Code deduplication database (`/Volumes/Plex/SSOT/code_dedup.db`)
**Collector**: `extract_code_patterns_from_dedup()` in `training_data_collector.py`

Extracts representative code samples by language.

```json
{
  "instruction": "Analyze this python code and describe what it does.",
  "input": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    ...",
  "output": "This is a python file that is production code."
}
```

**Supported Languages**: Python, Rust, JavaScript, TypeScript, Vue, Swift, Bash

### 3. Knowledge Documentation

**Source**: SSOT documents and project READMEs
**Collector**: `extract_project_knowledge()` in `training_data_collector.py`

Extracts project knowledge for SAM's self-awareness.

```json
{
  "instruction": "Based on the documentation for SAM_BRAIN, answer questions about this project.",
  "input": "# SAM Brain - AI Companion Core\n\n## What is SAM?...",
  "output": "This document covers: SAM_BRAIN"
}
```

### 4. Routing Examples

**Source**: Template-based generation
**Collector**: `generate_routing_examples()` in `training_data_collector.py`

Teaches SAM how to route tasks to the right handler.

```json
{
  "instruction": "Determine which LLM should handle this task: claude-code, chatgpt, ollama, or local",
  "input": "Write a function that sorts a list",
  "output": "claude-code"
}
```

### 5. Knowledge Distillation

**Source**: Claude reasoning extraction (`knowledge_distillation.py`)
**Storage**: `~/.sam/memory/distillation.db`

High-quality reasoning chains extracted from Claude escalations.

```json
{
  "instruction": "Explain how to implement a binary search tree",
  "input": "",
  "output": "A binary search tree is a data structure where each node has at most two children...",
  "metadata": {
    "source": "distillation",
    "quality_tier": "gold",
    "category": "coding",
    "validated": true
  }
}
```

### 6. Conversation Capture

**Source**: SAM API interactions
**Storage**: Conversation logs

Real interactions that were successful.

```json
{
  "messages": [
    {"role": "user", "content": "List my active projects"},
    {"role": "assistant", "content": "Here are your active projects:\n1. SAM Brain...\n2. Warp Tauri..."}
  ],
  "metadata": {
    "source": "conversation_capture",
    "feedback": "positive",
    "quality_tier": "silver"
  }
}
```

---

## Quality Criteria

### Automatic Validation

The scheduler runs `schedule_quality_check()` to validate examples:

1. **Format Validation**
   - Must have valid instruction/output or messages format
   - JSON must be parseable

2. **Length Bounds**
   - Minimum: 20 characters total
   - Maximum: 50,000 characters total
   - Optimal: 100-4000 characters

3. **Content Quality**
   - Non-empty output/response
   - No excessive repetition
   - Proper language (detected via heuristics)

4. **Structural Quality**
   - Complete code blocks
   - Balanced brackets/parentheses
   - Valid markdown (if applicable)

### Quality Score Calculation

```python
def calculate_quality_score(example: Dict) -> float:
    score = 0.5  # Base score

    # Format bonus (+0.1)
    if has_valid_format(example):
        score += 0.1

    # Length bonus (+0.1)
    if optimal_length(example):
        score += 0.1

    # Source bonus (+0.2)
    if example.get("source") in ["distillation", "manual"]:
        score += 0.2

    # Verified bonus (+0.2)
    if example.get("verified") or example.get("human_reviewed"):
        score += 0.2

    return min(1.0, score)
```

---

## Pipeline Workflow

### Manual Collection

```bash
# Run data collector manually
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python training_data_collector.py
```

### Scheduled Collection

```bash
# Start scheduler
python training_scheduler.py start

# Check status
python training_scheduler.py status

# Run specific job manually
python training_scheduler.py run --job mining_code
```

### Training

```bash
# Check if ready to train
python training_pipeline.py status

# Start training
python training_pipeline.py train

# Force training (below threshold)
python training_pipeline.py force
```

### Full Pipeline

```
1. Scheduler runs mining job (every 6 hours)
   → Extracts from git, code patterns, SSOT

2. Scheduler runs quality check (every 12 hours)
   → Validates all examples
   → Updates quality tiers

3. Scheduler runs deduplication (every 24 hours)
   → Removes duplicates
   → Compacts storage

4. Scheduler runs export (every 24 hours)
   → Creates training-ready JSONL

5. Training pipeline (manual or triggered)
   → Loads exported data
   → Runs MLX LoRA fine-tuning
   → Saves adapters
```

---

## API Reference

### Training Stats API

#### `GET /api/training/stats`

Returns comprehensive training data statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "overall": {
      "total_examples": 5000,
      "by_source": {"train": 3000, "distillation": 1500, "commits": 500},
      "by_format": {"instruction": 4000, "chat": 1000},
      "by_quality": {"gold": 500, "silver": 2000, "bronze": 2000, "raw": 500},
      "avg_token_length": 256.5,
      "total_tokens": 1282500,
      "storage_bytes": 15000000
    },
    "summary": {
      "total_examples": 5000,
      "storage_mb": 14.3,
      "healthy_sources": 4,
      "top_quality_percentage": 50.0
    }
  }
}
```

#### `GET /api/training/daily`

Returns daily collection statistics.

**Parameters:**
- `days` (int): Number of days to include (default: 30)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "date": "2026-01-25",
      "total_examples": 50,
      "by_source": {"distillation": 30, "mining": 20},
      "by_quality": {"silver": 40, "bronze": 10}
    }
  ],
  "days": 30
}
```

#### `GET /api/training/sources`

Returns source health information.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "source": "distillation",
      "total_examples": 1500,
      "quality_distribution": {"gold": 500, "silver": 800, "bronze": 200},
      "health_score": 0.85,
      "examples_24h": 25,
      "last_updated": "2026-01-25T10:00:00Z"
    }
  ]
}
```

### Scheduler API

#### `GET /api/scheduler/status`

Returns scheduler status and job information.

#### `POST /api/scheduler/run`

Runs a specific job immediately.

**Body:**
```json
{
  "job_id": "mining_code"
}
```

#### `PUT /api/scheduler/job`

Configures a scheduled job.

**Body:**
```json
{
  "job_id": "mining_code",
  "enabled": true,
  "interval_minutes": 360
}
```

---

## Configuration

### Scheduler Default Intervals

| Job | Default Interval | Purpose |
|-----|------------------|---------|
| `mining_code` | 6 hours | Extract patterns from code |
| `dedup_cleanup` | 24 hours | Remove duplicates |
| `quality_check` | 12 hours | Validate examples |
| `export_training` | 24 hours | Prepare training files |

### Training Pipeline Config

```python
# In training_pipeline.py
MIN_SAMPLES_FOR_TRAINING = 100
BASE_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
LORA_RANK = 8
LEARNING_RATE = 1e-4
EPOCHS = 3
BATCH_SIZE = 4
```

### 8GB Optimized Training Config

```python
# In train_8gb.py
CONFIG = {
    "model_name": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    "lora_layers": 8,
    "lora_rank": 4,
    "batch_size": 1,
    "grad_accum_steps": 4,
    "max_seq_length": 512,
}
```

### Storage Paths

| Data | Path |
|------|------|
| Training JSONL | `~/ReverseLab/SAM/warp_tauri/sam_brain/training_data/` |
| Distillation DB | `~/.sam/memory/distillation.db` |
| Scheduler State | `~/.sam/scheduler/` |
| Model Adapters | `~/ReverseLab/SAM/warp_tauri/sam_brain/models/` |

---

## Monitoring & Stats

### Dashboard CLI

```bash
# Summary stats
python training_stats.py summary

# Daily breakdown
python training_stats.py daily --days 14

# Source health
python training_stats.py sources

# Full JSON output
python training_stats.py json
```

### Scheduler CLI

```bash
# Check scheduler status
python training_scheduler.py status

# View scheduled jobs
python training_scheduler.py list

# View recent logs
cat ~/.sam/scheduler/scheduler.log | tail -50
```

### Key Metrics to Monitor

1. **Total Examples**: Should grow steadily
2. **Quality Distribution**: Aim for >50% gold/silver
3. **Source Health**: All sources should have score >0.6
4. **Examples/Day**: Consistent collection indicates healthy pipeline
5. **Storage Usage**: Monitor for runaway growth

---

## Troubleshooting

### Common Issues

#### No Data Being Collected

1. Check if scheduler is running:
   ```bash
   python training_scheduler.py status
   ```

2. Verify source availability:
   - Git repos exist and have commits
   - Dedup database is accessible
   - SSOT documents are present

3. Run manual collection to see errors:
   ```bash
   python training_data_collector.py
   ```

#### Low Quality Scores

1. Check quality validation criteria
2. Review examples with low scores:
   ```bash
   python training_stats.py sources
   ```
3. Consider adjusting thresholds in scheduler config

#### Training Won't Start

1. Verify minimum samples:
   ```bash
   python training_pipeline.py status
   ```

2. Check MLX availability:
   ```python
   python -c "import mlx; print('MLX available')"
   ```

3. Verify training data format:
   ```bash
   head -1 training_data/train.jsonl | python -m json.tool
   ```

#### Scheduler Jobs Failing

1. Check logs:
   ```bash
   cat ~/.sam/scheduler/scheduler.log | tail -100
   ```

2. Verify RAM availability (jobs have minimum RAM requirements)

3. Run job manually with debug output:
   ```bash
   python training_scheduler.py run --job quality_check
   ```

### Log Files

| Log | Path | Purpose |
|-----|------|---------|
| Scheduler | `~/.sam/scheduler/scheduler.log` | Job execution logs |
| Training | `sam_brain/training_logs/` | MLX training logs |
| Daemon | `~/.sam/daemon/daemon.log` | Unified daemon logs |

---

## Related Documentation

- **Training Pipeline Audit**: `docs/TRAINING_PIPELINE_AUDIT.md`
- **Distillation System**: `docs/DISTILLATION.md`
- **Feedback Learning**: `docs/FEEDBACK_LEARNING.md`
- **Knowledge Distillation Format**: `docs/DISTILLATION_FORMAT.md`
- **SAM Brain Architecture**: `CLAUDE.md`

---

*This documentation is maintained as part of SAM's Phase 5.1 training data pipeline implementation.*
