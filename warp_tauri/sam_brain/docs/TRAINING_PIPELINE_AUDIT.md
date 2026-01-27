# SAM Brain Training Pipeline Audit - Phase 5

**Date:** January 25, 2026
**Auditor:** Claude
**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`
**Purpose:** Document existing training capabilities and identify Phase 5 enhancements

---

## Executive Summary

The SAM Brain training pipeline consists of five primary components:

1. **`finetune_mlx.py`** - Original MLX fine-tuning script (LoRA-based)
2. **`train_8gb.py`** - 8GB RAM-optimized training with MLX LoRA
3. **`training_pipeline.py`** - Automated pipeline orchestration
4. **`training_data_collector.py`** - Multi-source data collection
5. **`knowledge_distillation.py`** - Claude reasoning extraction and quality filtering

The infrastructure is functional but underutilized. The knowledge distillation system is sophisticated but not yet integrated with the actual training pipeline.

---

## File-by-File Analysis

### 1. finetune_mlx.py

**Path:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/finetune_mlx.py`
**Status:** Basic implementation, needs enhancement

#### Current Capabilities

- MLX framework integration for Apple Silicon
- LoRA adapter training on attention projections (q, k, v, o)
- Loads Qwen2.5-Coder-1.5B-Instruct as base model
- JSONL training data loading from `~/.sam/training_data/`
- Ollama Modelfile generation for deployment

#### Configuration

```python
CONFIG = {
    "base_model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "lora_rank": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "batch_size": 4,
    "learning_rate": 1e-4,
    "num_epochs": 3,
    "max_seq_length": 2048,
    "gradient_accumulation_steps": 4,
}
```

#### LoRA Configuration

```python
target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
```

#### Limitations

1. **Simplified training loop** - Does not implement proper loss calculation
2. **No evaluation metrics** - Training completion without validation
3. **Hardcoded system prompt** - "You are SAM, an AI assistant specialized in software development..."
4. **GGUF export incomplete** - Requires external llama.cpp tools
5. **No checkpointing during training**

---

### 2. train_8gb.py

**Path:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/train_8gb.py`
**Status:** Production-ready, 8GB optimized

#### Current Capabilities

- Uses pre-quantized 4-bit model: `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit`
- Aggressive memory optimization for 8GB Mac
- MLX native training with gradient checkpointing
- Proper train/validation split (95/5)
- Checkpoint saving every 100 steps
- Quick test mode (10 steps) for validation

#### 8GB Optimizations

```python
CONFIG = {
    "model_name": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    "lora_layers": 8,
    "lora_rank": 4,         # Lower rank for memory
    "lora_alpha": 8,
    "batch_size": 1,        # Must be 1 for 8GB
    "grad_accum_steps": 4,  # Effective batch = 4
    "max_seq_length": 512,  # Shorter sequences
    "num_epochs": 1,        # Conservative
}
```

#### Data Format

Uses Qwen chat template:
```
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
{response}<|im_end|>
```

#### Training Args

```python
TrainingArgs(
    batch_size=1,
    iters=total_steps,
    val_batches=10,
    steps_per_report=10,
    steps_per_eval=50,
    steps_per_save=100,
    max_seq_length=512,
    grad_checkpoint=True,
    grad_accumulation_steps=4,
)
```

#### Limitations

1. **Short sequence length** (512) limits context learning
2. **Single epoch default** may underfit
3. **No learning rate scheduling**
4. **No early stopping**
5. **Limited evaluation beyond validation loss**

---

### 3. training_pipeline.py

**Path:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_pipeline.py`
**Status:** Orchestration layer, functional

#### Current Capabilities

- Automated training trigger when data threshold met (100 samples)
- Training run history tracking (JSON-based)
- Dataset preparation with train/val split (90/10)
- MLX LoRA training via subprocess
- Model listing and Ollama export
- Status and statistics reporting

#### Configuration

```python
MIN_SAMPLES_FOR_TRAINING = 100
BASE_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
LORA_RANK = 8
LEARNING_RATE = 1e-4
EPOCHS = 3
BATCH_SIZE = 4
```

#### CLI Commands

```bash
python training_pipeline.py           # Show stats
python training_pipeline.py train     # Start training if ready
python training_pipeline.py status    # JSON stats
python training_pipeline.py models    # List fine-tuned models
python training_pipeline.py export <path> <name>  # Export to Ollama
python training_pipeline.py force     # Force training below threshold
```

#### Run Tracking Schema

```python
@dataclass
class TrainingRun:
    run_id: str
    start_time: str
    samples_count: int
    base_model: str
    status: str  # pending, training, completed, failed
    metrics: Dict
    output_path: Optional[str]
```

#### Limitations

1. **No integration with knowledge_distillation.py output**
2. **Uses subprocess instead of Python API** for MLX training
3. **Limited metrics collection**
4. **No model versioning or rollback**
5. **Training runs sequentially only**

---

### 4. training_data_collector.py

**Path:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_data_collector.py`
**Status:** Data extraction tool, functional

#### Data Sources

1. **Git commits** - Commit messages and diff summaries from local repos
2. **Code patterns** - From dedup database (`/Volumes/Plex/SSOT/code_dedup.db`)
3. **Project knowledge** - SSOT markdown documentation
4. **Routing examples** - Synthetic task routing training data

#### Supported Languages

```python
["python", "rust", "javascript", "typescript", "vue", "swift", "bash"]
```

#### Output Format (Alpaca-style)

```json
{
  "instruction": "Given these code changes in {repo}, write a commit message.",
  "input": "{diff_summary}",
  "output": "{commit_message}"
}
```

#### Output Locations

- `~/.sam/training_data/commits/commit_messages.jsonl`
- `~/.sam/training_data/code_patterns/code_analysis.jsonl`
- `~/.sam/training_data/knowledge/project_docs.jsonl`
- `~/.sam/training_data/routing/task_routing.jsonl`
- `~/.sam/training_data/manifest.json`

#### Data Types Generated

| Type | Description | Training Goal |
|------|-------------|---------------|
| commits | Code changes -> commit message | Commit message generation |
| routing | User task -> target LLM | Task routing decisions |
| knowledge | Project docs -> summary | Project understanding |
| code | Code sample -> analysis | Code comprehension |

#### Limitations

1. **Routing examples are synthetic templates** - not real interactions
2. **Knowledge output is weak** - just title parroting
3. **No quality filtering** on collected data
4. **Code analysis outputs are generic**
5. **No deduplication across runs**

---

### 5. knowledge_distillation.py

**Path:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/knowledge_distillation.py`
**Status:** Most sophisticated component, comprehensive

#### Core Concept

Captures Claude's reasoning patterns and distills them into training data for SAM. Extracts:

1. **Chain-of-Thought patterns** - Step-by-step reasoning
2. **Principle extraction** - Core rules/guidelines
3. **Preference pairs** - Good vs bad response examples (DPO format)
4. **Skill templates** - Reusable reasoning patterns
5. **Error corrections** - SAM mistakes corrected by Claude (highest value)

#### Reasoning Types Supported

```python
class ReasoningType(Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TOOL_USE = "tool_use"
    CORRECTION = "correction"
    DIRECT = "direct"
    MULTI_STEP = "multi_step"
    META_COGNITIVE = "meta_cognitive"
```

#### Quality Filter System

Sophisticated quality scoring (0.0-1.0):

**Base score:** 0.5

**Positive factors (+0.4 max):**
- Reasoning chains with 2+ steps: +0.1
- Explicit corrections of SAM errors: +0.15
- Extracted principles: +0.1
- Task complexity >= 5: +0.05

**Negative factors (-0.5 max):**
- Response too short (<100 chars): -0.2
- Direct answers (no reasoning): -0.1
- Repetitive content: -0.3
- Incomplete response: -0.2

**Auto-rejection criteria:**
- quality_score < 0.3
- Response too short (<50 chars)
- High repetition ratio (>40%)
- Refusal patterns detected

#### Quality Flags

```python
QUALITY_FLAGS = [
    'repetition', 'incomplete', 'no_reasoning', 'too_short',
    'too_long', 'code_only', 'refusal', 'uncertain',
    'outdated', 'hallucination_risk'
]
```

#### Database Schema (SQLite)

**Primary Tables:**
- `examples` - Training examples with full metadata
- `reasoning_patterns` - Extracted reasoning structure
- `corrections` - SAM error corrections (highest value)
- `principles` - Reusable guidelines
- `review_queue` - Human review queue

**Legacy Tables (backwards compatibility):**
- `chain_of_thought`
- `preference_pairs`
- `skill_templates`
- `raw_interactions`
- `filter_rejections`

#### Storage Paths

```python
EXTERNAL_DB_PATH = "/Volumes/David External/sam_training/distilled/distillation.db"
LOCAL_DB_PATH = "~/.sam/knowledge_distillation.db"
EXPORT_PATH = "/Volumes/David External/sam_training/distilled/exports"
PENDING_REVIEW_PATH = "/Volumes/David External/sam_training/distilled/pending_review"
APPROVED_PATH = "/Volumes/David External/sam_training/distilled/approved"
```

#### Export Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| instruction | Alpaca-style instruction/input/output | Standard SFT |
| preference | DPO format with chosen/rejected | Preference learning |
| raw | Full example with metadata | Analysis |

#### Human Review Workflow

```python
db.get_pending_review(limit=10)           # Get pending examples
db.approve_example(id, notes, quality_override)  # Approve
db.reject_example(id, reason)             # Reject
db.batch_approve_above_threshold(0.7)     # Auto-approve high quality
db.batch_reject_below_threshold(0.2)      # Auto-reject low quality
```

#### CLI Commands

```bash
python knowledge_distillation.py listen              # Capture mode
python knowledge_distillation.py generate --domain code --count 100
python knowledge_distillation.py extract-principles
python knowledge_distillation.py export --output training_distilled.jsonl
```

---

## Existing Training Data

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_data/`

| File | Description |
|------|-------------|
| `train.jsonl` | Primary training data (chat format) |
| `valid.jsonl` | Validation split |
| `curated_training.jsonl` | Hand-curated examples |
| `training_samples.jsonl` | Additional samples |
| `claude_generated_personality.jsonl` | SAM personality examples |
| `claude_generated_escalation.jsonl` | Escalation handling examples |

#### Data Format (Chat)

```json
{
  "messages": [
    {"role": "user", "content": "How do I merge two dictionaries in Python?"},
    {"role": "assistant", "content": "Python 3.9+:\n```python\nmerged = dict1 | dict2\n```..."}
  ]
}
```

#### Observed Training Data Quality

- Good variety of topics (code, emotional support, roleplay, factual)
- SAM personality is present and consistent
- Responses are detailed and well-structured
- Missing: explicit reasoning chains, corrections, multi-turn conversations

---

## Inference Infrastructure

### mlx_inference.py

**Status:** Production inference with trained model

- Loads fused model or base + adapters
- Repetition detection and truncation
- Interactive mode available
- JSON output option

**Model Paths:**
```python
FUSED_MODEL_PATH = "~/.sam/models/sam-brain-fused"
ADAPTER_PATH = "~/.sam/models/sam-abliterated-lora/adapters"
BASE_MODEL = "mlx-community/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit"
```

---

## Current Limitations Summary

### Training Pipeline Gaps

1. **No knowledge distillation integration** - Sophisticated distillation system exists but is not connected to training pipeline
2. **Limited evaluation metrics** - No perplexity, task-specific evaluation
3. **No curriculum learning** - All data treated equally
4. **No DPO/RLHF support** - Only SFT despite preference pairs available
5. **No multi-turn conversation training** - Single turn only
6. **No active learning loop** - Manual data collection only

### 8GB Constraints

1. **Max 512 tokens** limits complex reasoning learning
2. **Batch size 1** slows training
3. **4-bit quantization** may reduce learning capacity
4. **No model parallelism** options

### Data Quality

1. **Synthetic routing examples** lack real-world patterns
2. **Knowledge extraction is weak** (title-only summaries)
3. **No deduplication** across data sources
4. **No difficulty grading** for curriculum

### Missing Features

1. **Model versioning and A/B testing**
2. **Continuous learning from production**
3. **Automated data validation**
4. **Training metrics dashboard**
5. **Rollback capability**

---

## Phase 5 Enhancement Recommendations

### Priority 1: Connect Knowledge Distillation to Training

**Goal:** Use knowledge_distillation.py output as primary training source

```python
# Proposed integration flow:
1. knowledge_distillation.db -> export_for_training()
2. Filter by approved=1 and quality_score >= threshold
3. Convert to train.jsonl format
4. Feed to train_8gb.py
```

**Required Changes:**
- Add `distillation_to_training.py` converter script
- Update `training_pipeline.py` to pull from distillation DB
- Implement format conversion (instruction -> chat format)

### Priority 2: Correction-Focused Training

**Goal:** Prioritize SAM error corrections (highest learning value)

```python
# Correction examples format:
{
  "messages": [
    {"role": "system", "content": "You are SAM. The user will show you an error and correction."},
    {"role": "user", "content": "SAM said: {incorrect}. This was wrong because: {reason}"},
    {"role": "assistant", "content": "I understand. The correct answer is: {correct}. I'll remember this."}
  ]
}
```

**Required Changes:**
- Separate corrections into dedicated training file
- Weight corrections higher in training (oversample)
- Track correction patterns for systematic improvement

### Priority 3: Enhanced Evaluation Metrics

**Goal:** Meaningful training progress measurement

**Metrics to Add:**
1. Validation perplexity (already available in MLX)
2. Task-specific accuracy (routing, code generation)
3. Response quality score (using existing quality filter)
4. Repetition rate in generated text
5. Hallucination detection rate

**Implementation:**
```python
class TrainingEvaluator:
    def evaluate_routing_accuracy(self, model, test_set) -> float
    def evaluate_code_generation(self, model, test_set) -> float
    def measure_repetition_rate(self, model, prompts) -> float
    def measure_quality_scores(self, model, prompts) -> float
```

### Priority 4: Curriculum Learning

**Goal:** Train on easier examples first, progress to harder ones

```python
# Sort training data by complexity
curriculum_order = sorted(examples, key=lambda x: x['complexity'])

# Train in phases
phase_1 = [x for x in curriculum_order if x['complexity'] <= 3]  # Simple
phase_2 = [x for x in curriculum_order if x['complexity'] <= 6]  # Medium
phase_3 = curriculum_order  # All (including complex)
```

**Required Changes:**
- Add complexity scoring to all training data
- Modify train_8gb.py to support curriculum phases
- Track per-phase metrics

### Priority 5: DPO Training Support

**Goal:** Leverage preference pairs for alignment

**knowledge_distillation.py already exports preference format:**
```json
{
  "prompt": "user query",
  "chosen": "Claude's response",
  "rejected": "SAM's incorrect attempt"
}
```

**Required Changes:**
- Integrate MLX DPO training (mlx-lm supports this)
- Create DPO training script (`train_dpo.py`)
- Schedule SFT -> DPO training sequence

### Priority 6: Continuous Learning Pipeline

**Goal:** Automatic improvement from production usage

```
User Query -> SAM Response -> Claude Escalation -> Extract Correction
                                                         |
                                                         v
                                              Knowledge Distillation
                                                         |
                                                         v
                                              Review Queue (if needed)
                                                         |
                                                         v
                                              Approved Training Data
                                                         |
                                                         v
                                              Nightly Training Run
```

**Required Changes:**
- Hook escalation_handler.py to knowledge_distillation.py
- Implement nightly training cron job
- Add model deployment pipeline

---

## Integration with knowledge_distillation.py Output

### Current State

knowledge_distillation.py exports to:
- `/Volumes/David External/sam_training/distilled/exports/distilled_instruction_*.jsonl`
- `/Volumes/David External/sam_training/distilled/exports/corrections_*.jsonl`

### Proposed Integration

```python
# New file: distillation_to_training.py

def convert_distilled_to_training(
    distillation_db: Path,
    output_dir: Path,
    min_quality: float = 0.5,
    include_corrections: bool = True
) -> Dict[str, int]:
    """
    Convert knowledge distillation output to training format.

    Returns:
        Dict with counts of examples by type
    """
    db = DistillationDB(distillation_db)

    # Export approved examples
    instruction_count = db.export_for_training(
        output_path=output_dir / "train_distilled.jsonl",
        only_approved=True,
        format="instruction"
    )

    # Convert to chat format for train_8gb.py
    convert_instruction_to_chat(
        input_path=output_dir / "train_distilled.jsonl",
        output_path=output_dir / "train.jsonl"
    )

    # Export preference pairs for DPO
    preference_count = db.export_for_training(
        output_path=output_dir / "preferences.jsonl",
        only_approved=True,
        format="preference"
    )

    return {
        "instruction_examples": instruction_count,
        "preference_pairs": preference_count
    }
```

---

## Recommended Implementation Order

1. **Week 1:** Connect knowledge_distillation.py to training_pipeline.py
2. **Week 2:** Implement enhanced evaluation metrics
3. **Week 3:** Add correction-focused training with oversampling
4. **Week 4:** Implement curriculum learning
5. **Week 5:** Add DPO training support
6. **Week 6:** Build continuous learning pipeline

---

## Testing Recommendations

### Before Training Changes

1. **Baseline capture:**
   - Current model performance on test prompts
   - Routing accuracy on synthetic tasks
   - Response quality scores

2. **Test data preservation:**
   - Hold out 10% of distilled data for evaluation
   - Create benchmark test set

### During Training

1. **Checkpoint comparison:**
   - Evaluate each checkpoint against baseline
   - Watch for regression

2. **Overfitting detection:**
   - Compare train vs validation loss
   - Test on unseen prompts

### After Training

1. **A/B testing:**
   - Run new model alongside current
   - Compare user satisfaction (if measurable)

2. **Rollback test:**
   - Verify ability to restore previous model

---

## Conclusion

The SAM Brain training infrastructure has solid foundations, particularly:
- Well-optimized 8GB training with `train_8gb.py`
- Sophisticated knowledge distillation with quality filtering
- Production-ready inference with `mlx_inference.py`

The primary gap is **integration** - the distillation system and training system are not connected. Phase 5 should focus on:

1. Connecting knowledge_distillation.py output to training
2. Prioritizing correction-based learning
3. Adding meaningful evaluation metrics
4. Enabling continuous improvement from production

With these enhancements, SAM can learn from every Claude escalation, systematically improving over time.
