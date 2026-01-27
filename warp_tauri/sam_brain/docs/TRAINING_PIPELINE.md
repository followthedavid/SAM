# SAM Training Pipeline Documentation

**Phase:** 5.2
**Last Updated:** January 2026
**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`

---

## Overview

The SAM Training Pipeline enables continuous self-improvement through fine-tuning on user interactions. It collects training data from conversations, validates quality, runs MLX-based LoRA fine-tuning, and safely deploys new model versions with automatic rollback capabilities.

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Training Pipeline | `training_pipeline.py` | Orchestrates training workflow |
| 8GB Training | `train_8gb.py` | Memory-optimized MLX training |
| Data Collector | `training_data_collector.py` | Multi-source data extraction |
| Knowledge Distillation | `knowledge_distillation.py` | Claude reasoning capture |
| Model Deployment | `model_deployment.py` | Version control & rollback |
| Fine-tuning | `finetune_mlx.py` | Low-level MLX LoRA training |

---

## Architecture

```
                    Training Pipeline Architecture

    +------------------+     +-------------------+
    | Data Collection  |     | Knowledge         |
    | - Git commits    |     | Distillation      |
    | - Code patterns  |     | - Claude capture  |
    | - Project docs   |     | - Quality filter  |
    +--------+---------+     +--------+----------+
             |                         |
             v                         v
    +------------------------------------------+
    |          Training Data Pool              |
    |  ~/.sam/training_data/ (JSONL format)    |
    +-------------------+----------------------+
                        |
                        v
    +-------------------+----------------------+
    |         Training Pipeline               |
    |  - Validation & cleaning                |
    |  - Train/val split (90/10)              |
    |  - MLX LoRA training                    |
    +-------------------+----------------------+
                        |
                        v
    +-------------------+----------------------+
    |         Model Deployment                |
    |  - Sanity checks                        |
    |  - Version control                      |
    |  - Canary releases                      |
    |  - Auto rollback                        |
    +-------------------+----------------------+
                        |
                        v
    +-------------------+----------------------+
    |         Production Model                |
    |  ~/.sam/models/sam-brain-lora/adapters  |
    +------------------------------------------+
```

---

## Data Preparation

### Data Sources

1. **Git Commits** (`training_data_collector.py`)
   - Commit messages with diff summaries
   - Format: Code changes -> descriptive message

2. **Code Patterns**
   - From dedup database
   - Language-specific analysis

3. **Project Knowledge**
   - SSOT markdown documentation
   - Project descriptions and status

4. **Knowledge Distillation** (`knowledge_distillation.py`)
   - Claude's reasoning chains
   - Error corrections (highest value)
   - Preference pairs for DPO

### Data Format

#### Instruction Format (Alpaca-style)
```json
{
  "instruction": "Write a Python function to...",
  "input": "Additional context",
  "output": "def function():\n    return result"
}
```

#### Chat Format (Qwen)
```json
{
  "messages": [
    {"role": "user", "content": "Write a Python function..."},
    {"role": "assistant", "content": "def function():\n    return result"}
  ]
}
```

### Data Validation

The pipeline validates training data:
- Required fields present (`input`, `output`)
- JSON parsing successful
- Non-empty content
- Optional quality scoring from distillation

---

## Training Configuration

### Hyperparameters

| Parameter | 8GB Value | Full Value | Notes |
|-----------|-----------|------------|-------|
| Base Model | Qwen2.5-Coder-1.5B-4bit | Qwen2.5-Coder-1.5B | Pre-quantized for 8GB |
| LoRA Rank | 4 | 8 | Lower for memory efficiency |
| LoRA Alpha | 8 | 16 | Scaling factor |
| Batch Size | 1 | 4 | Must be 1 for 8GB |
| Grad Accum | 4 | 4 | Effective batch = 4 |
| Learning Rate | 1e-4 | 1e-4 | Conservative |
| Max Seq Length | 512 | 2048 | Limited for 8GB |
| Epochs | 1 | 3 | Start conservative |

### 8GB Optimizations

```python
# train_8gb.py configuration
CONFIG = {
    "model_name": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    "lora_layers": 8,
    "lora_rank": 4,
    "batch_size": 1,
    "grad_accum_steps": 4,
    "max_seq_length": 512,
    "grad_checkpoint": True,  # Critical for 8GB
}
```

### LoRA Targets

Target modules for adaptation:
- `q_proj` - Query projection
- `k_proj` - Key projection
- `v_proj` - Value projection
- `o_proj` - Output projection

---

## Training Monitoring

### Progress Tracking

Each training run is recorded:

```python
@dataclass
class TrainingRun:
    run_id: str           # Timestamp-based ID
    start_time: str       # ISO timestamp
    samples_count: int    # Training samples used
    base_model: str       # Base model identifier
    status: str           # pending, training, completed, failed
    metrics: Dict         # Loss, accuracy, etc.
    output_path: str      # Where adapters saved
```

### Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Training Loss | Cross-entropy loss | < 1.0 |
| Validation Loss | Held-out loss | < 1.5 |
| Perplexity | exp(loss) | < 5.0 |
| Steps | Training iterations | Varies |

### Commands

```bash
# Check pipeline status
python training_pipeline.py status

# View available models
python training_pipeline.py models

# Start training (if ready)
python training_pipeline.py train

# Force training below threshold
python training_pipeline.py force
```

---

## Model Evaluation

### Pre-deployment Validation

1. **Sanity Check**
   - Adapter files exist
   - File sizes reasonable (1MB - 2GB)
   - Correct format (.safetensors, .npz)

2. **Model Validation**
   - Model loads successfully
   - Generates coherent output
   - No repetitive garbage

### Evaluation Metrics

| Metric | Method | Threshold |
|--------|--------|-----------|
| Response Quality | Manual sampling | Subjective |
| Repetition Rate | Token analysis | < 5% |
| Coherence | Claude evaluation | Pass/Fail |
| Task Performance | Benchmark tests | > Baseline |

---

## Deployment System

### Version Control

Versions stored at: `/Volumes/David External/SAM_models/versions/`

```python
@dataclass
class ModelVersion:
    version: str              # e.g., "v1.0.0"
    created_at: str           # ISO timestamp
    deployed_at: str          # When activated
    status: str               # active, rolled_back, canary
    base_model: str           # Base model used
    adapter_path: str         # Path to adapters
    training_run_id: str      # Source training run
    training_samples: int     # Samples used
    metrics: Dict             # Evaluation results
    checksum: str             # File integrity
```

### Deployment Commands

```bash
# Deploy a new model
python model_deployment.py deploy /path/to/adapters --description "Training run X"

# Dry run (validate only)
python model_deployment.py deploy /path/to/adapters --dry-run

# List all versions
python model_deployment.py list

# Show current version
python model_deployment.py current

# View deployment stats
python model_deployment.py stats
```

### Safe Deployment

1. **Sanity Check** - Verify adapter files
2. **Validation** - Test model generation
3. **Copy** - Store in versioned location
4. **Activate** - Update symlink/copy
5. **Monitor** - Track metrics

---

## Rollback System

### Automatic Rollback Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Error Rate | > 15% | Rollback |
| Response Time | > 5000ms avg | Rollback |
| Memory Usage | > 6GB | Rollback |

### Manual Rollback

```bash
# Rollback to previous version
python model_deployment.py rollback

# Rollback to specific version
python model_deployment.py rollback v1.0.0
```

### Canary Releases

Gradual rollout to minimize risk:

```bash
# Start canary at 10% traffic
python model_deployment.py canary /path/to/adapters --traffic 10

# Increase traffic (done automatically or manually)
# Monitor metrics...

# Promote to full deployment
python model_deployment.py promote
```

---

## API Integration

### /api/self Endpoint

The `/api/self` endpoint now includes training stats:

```json
{
  "success": true,
  "explanation": "I am SAM...",
  "status": {...},
  "distillation": {...},
  "training_stats": {
    "model_version": "v1.0.3",
    "deployed_at": "2026-01-25T10:00:00",
    "last_training": {
      "run_id": "20260125_100000",
      "samples_count": 500,
      "status": "completed"
    },
    "training_data": {
      "total_samples": 750,
      "min_for_training": 100,
      "ready_to_train": true,
      "distilled_samples": 200
    },
    "deployment": {
      "total_versions": 3,
      "rollback_available": true,
      "canary_active": false
    }
  }
}
```

---

## Storage Locations

### Primary (External Drive)

```
/Volumes/David External/SAM_models/
├── versions/
│   ├── versions.json        # Version history
│   ├── current.txt          # Active version pointer
│   ├── v1.0.0/
│   │   └── adapters/        # Adapter files
│   ├── v1.0.1/
│   │   └── adapters/
│   └── ...
```

### Local Fallback

```
~/.sam/models/
├── sam-brain-lora/
│   └── adapters/            # Active adapters
├── sam-brain-fused/         # Fused model (optional)
└── versions/                # Local version backup
```

### Training Data

```
~/.sam/training_data/
├── commits/
│   └── commit_messages.jsonl
├── code_patterns/
│   └── code_analysis.jsonl
├── knowledge/
│   └── project_docs.jsonl
├── routing/
│   └── task_routing.jsonl
└── manifest.json
```

---

## Testing

### Test File

Location: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/tests/test_training_pipeline.py`

### Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| Data Preparation | 4 | Data loading and validation |
| Data Splitting | 3 | Train/val split logic |
| Job Runner | 5 | Training execution |
| Monitoring | 3 | Progress tracking |
| Evaluation | 2 | Model metrics |
| Deployment | 10 | Version management |
| Rollback | 3 | Recovery procedures |
| API | 2 | Endpoint integration |
| E2E | 2 | Full workflow |

### Running Tests

```bash
cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain

# Run all training tests
python -m pytest tests/test_training_pipeline.py -v

# Run specific test class
python -m pytest tests/test_training_pipeline.py::TestDataPreparation -v

# Run with coverage
python -m pytest tests/test_training_pipeline.py --cov=. --cov-report=term-missing
```

---

## Workflow: Complete Training Cycle

### Step 1: Data Collection

```bash
# Collect training data from various sources
python training_data_collector.py

# Check distillation database
python knowledge_distillation.py stats
```

### Step 2: Check Readiness

```bash
# View pipeline status
python training_pipeline.py

# Output:
# total_samples: 150
# ready_to_train: True
# mlx_available: True
```

### Step 3: Run Training

```bash
# Option A: Use pipeline orchestrator
python training_pipeline.py train

# Option B: Use 8GB optimized script directly
python train_8gb.py --epochs 1

# Option C: Quick test (10 steps)
python train_8gb.py --test
```

### Step 4: Deploy

```bash
# Validate first
python model_deployment.py deploy ~/.sam/models/sam-brain-lora/adapters --dry-run

# Deploy if validation passes
python model_deployment.py deploy ~/.sam/models/sam-brain-lora/adapters \
  --description "Training run 20260125"
```

### Step 5: Monitor

```bash
# Check deployment stats
python model_deployment.py stats

# Check API self-status
curl http://localhost:8765/api/self | jq '.training_stats'
```

### Step 6: Rollback (if needed)

```bash
# If issues detected
python model_deployment.py rollback
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Not enough samples" | Below 100 threshold | Collect more data or use `force` |
| "MLX not available" | Missing dependencies | `pip install mlx mlx-lm` |
| "Memory error" | 8GB exceeded | Reduce batch size, seq length |
| "Adapter files missing" | Bad path | Check adapter_path in version |
| "Validation failed" | Corrupt model | Re-train or rollback |

### Memory Management

For 8GB Mac:
1. Close other apps during training
2. Use pre-quantized 4-bit model
3. Keep batch_size=1
4. Use grad_checkpoint=True
5. Limit max_seq_length to 512

### Logs

Training logs: `sam_brain/training_logs/training_YYYYMMDD_HHMMSS.log`

---

## Future Enhancements

### Planned for Phase 6

1. **DPO Training** - Use preference pairs
2. **Curriculum Learning** - Train easy to hard
3. **Continuous Learning** - Auto-train nightly
4. **A/B Testing** - Compare versions in production
5. **Distributed Training** - Multi-device support

---

## Quick Reference

### Files

| File | Purpose |
|------|---------|
| `training_pipeline.py` | Main orchestrator |
| `train_8gb.py` | 8GB-optimized training |
| `model_deployment.py` | Version control |
| `training_data_collector.py` | Data extraction |
| `knowledge_distillation.py` | Claude capture |
| `finetune_mlx.py` | Low-level training |

### Commands

```bash
# Status
python training_pipeline.py status
python model_deployment.py stats

# Train
python training_pipeline.py train
python train_8gb.py --epochs 1

# Deploy
python model_deployment.py deploy /path --dry-run
python model_deployment.py deploy /path

# Rollback
python model_deployment.py rollback

# List
python training_pipeline.py models
python model_deployment.py list
```

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/self` | Full status including training |
| `GET /api/training` | Training pipeline status |
| `POST /api/train` | Trigger training run |
