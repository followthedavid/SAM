# SAM Training Data Schema

Phase 5.1.2 - Unified Training Data System

## Overview

This document describes the unified training data schema for SAM's self-improvement system. All training data from various sources (Claude captures, user corrections, synthetic examples, etc.) flows through this schema for consistent processing and export.

## Architecture

```
                    +------------------+
                    |  Data Sources    |
                    +------------------+
                           |
         +-----------------+------------------+
         |                 |                  |
         v                 v                  v
+----------------+  +---------------+  +---------------+
| Claude Capture |  | User Feedback |  | Distillation  |
| (escalations)  |  | (corrections) |  | (knowledge)   |
+----------------+  +---------------+  +---------------+
         |                 |                  |
         v                 v                  v
+--------------------------------------------------+
|              TrainingExample Dataclass           |
|  - Unified schema for all training data          |
|  - Quality scoring and validation                |
|  - Multiple export formats                       |
+--------------------------------------------------+
                           |
                           v
+--------------------------------------------------+
|              TrainingDataStore (SQLite)          |
|  - Persistent storage                            |
|  - Deduplication                                 |
|  - Export to JSONL                               |
+--------------------------------------------------+
                           |
         +-----------------+------------------+
         |                 |                  |
         v                 v                  v
+----------------+  +---------------+  +---------------+
| MLX LoRA       |  | HuggingFace   |  | Custom        |
| (instruction)  |  | (chat/DPO)    |  | (JSONL)       |
+----------------+  +---------------+  +---------------+
```

## Core Components

### Files

| File | Purpose |
|------|---------|
| `training_data.py` | Schema definitions, TrainingDataStore |
| `training_capture.py` | Capture systems (Claude, corrections) |
| `training_pipeline.py` | Existing training runner |
| `feedback_system.py` | User feedback (corrections, preferences) |
| `knowledge_distillation.py` | Claude response distillation |

### Storage

Primary: `/Volumes/David External/sam_training/training_data.db`
Fallback: `~/.sam/training_data.db`

## TrainingExample Schema

```python
@dataclass
class TrainingExample:
    # === Required ===
    source: str                    # Data source identifier
    format: str                    # Training format (instruction, chat, dpo)
    input_text: str                # User query/prompt
    output_text: str               # Expected response

    # === Identity ===
    id: str                        # Unique ID (auto-generated)

    # === Optional ===
    system_prompt: Optional[str]   # System prompt for chat format
    context: Optional[str]         # Additional context

    # === DPO Fields ===
    rejected_output: Optional[str]     # Bad response for DPO
    preference_reason: Optional[str]   # Why chosen > rejected

    # === Multi-turn ===
    conversation_history: Optional[List[Dict]]  # Prior turns

    # === Metadata ===
    metadata: Dict[str, Any]       # Flexible metadata
    domain: str                    # code, reasoning, creative, etc.
    complexity: int                # 1-10 scale
    quality_tier: str              # gold, silver, bronze, unverified
    quality_score: float           # 0.0-1.0

    # === Provenance ===
    created_at: float              # Unix timestamp
    source_id: Optional[str]       # Original source ID
    parent_id: Optional[str]       # Parent example ID

    # === Processing ===
    validated: bool                # Quality validated
    used_in_training: bool         # Used in a training run
    training_run_id: Optional[str] # Which run used this
```

## Training Formats

### 1. INSTRUCTION Format
Standard instruction-following format for MLX LoRA training.

```json
{
    "instruction": "You are SAM, a helpful AI assistant.",
    "input": "How do I reverse a list in Python?",
    "output": "You can reverse a list using list[::-1] or list.reverse()..."
}
```

### 2. CHAT Format
Multi-turn conversation format for chat models.

```json
{
    "messages": [
        {"role": "system", "content": "You are SAM..."},
        {"role": "user", "content": "How do I reverse a list?"},
        {"role": "assistant", "content": "Use list[::-1]..."}
    ]
}
```

### 3. DPO (Direct Preference Optimization)
Preference learning with chosen vs rejected responses.

```json
{
    "prompt": "What is the capital of France?",
    "chosen": "The capital of France is Paris.",
    "rejected": "The capital of France is Lyon.",
    "reason": "Paris is correct, Lyon is not the capital."
}
```

### 4. COMPLETION Format
Simple text completion.

```json
{
    "text": "Question: How do I reverse a list?\n\nAnswer: Use list[::-1]..."
}
```

### 5. MULTI_TURN Format
Extended chat with context.

```json
{
    "messages": [...],
    "context": "User is working on a Python project..."
}
```

## Data Sources

### 1. Claude Captures (`claude_capture`)

Captured from escalation_handler.py when SAM escalates to Claude.

**Triggers:**
- Low confidence responses
- Complex tasks
- SAM errors/refusals
- User-requested escalation

**Creates:**
- CHAT examples (Claude response only)
- DPO examples (Claude chosen, SAM rejected)

### 2. User Corrections (`user_correction`)

From feedback_system.py when users correct SAM's responses.

**Triggers:**
- User provides correction
- User explains what was wrong

**Creates:**
- DPO examples (correction chosen, original rejected)

### 3. User Preferences (`user_preference`)

From feedback_system.py when users provide preferred alternatives.

**Triggers:**
- User provides preferred response
- User explains why preferred

**Creates:**
- DPO examples (preferred chosen, original rejected)

### 4. Knowledge Distillation (`distillation`)

From knowledge_distillation.py analyzing Claude responses.

**Extracts:**
- Reasoning patterns
- Principles
- Error correction pairs

**Creates:**
- CHAT examples with reasoning
- INSTRUCTION examples

### 5. Positive Feedback (`feedback`)

From feedback_system.py positive ratings.

**Triggers:**
- Thumbs up / positive rating

**Creates:**
- INSTRUCTION examples (lower weight)

## Quality System

### Quality Tiers

| Tier | Score Range | Description |
|------|-------------|-------------|
| gold | 0.8 - 1.0 | Manually verified, highest quality |
| silver | 0.6 - 0.8 | High confidence automated capture |
| bronze | 0.4 - 0.6 | Standard automated capture |
| unverified | 0.0 - 0.4 | Not yet evaluated or low quality |

### Quality Scoring

Base score: 0.5

**Positive Factors:**
- Response length > 200 chars: +0.1
- Response length > 500 chars: +0.05
- High-quality source (manual, claude): +0.15
- DPO format (more curation): +0.1
- Code blocks in code domain: +0.1

**Negative Factors:**
- Validation issues: -0.1 each
- Empty fields: reject
- Excessive repetition: -0.3
- Incomplete response: -0.15

### Validation Checks

- Empty input/output: REJECT
- Length > 32K characters: REJECT
- DPO missing rejected_output: REJECT
- Repetition > 30%: FLAG
- Incomplete (ends with ...): FLAG

## PII Detection

The capture system detects and redacts:

| Type | Pattern Example |
|------|-----------------|
| Email | user@domain.com |
| Phone | (123) 456-7890 |
| SSN | 123-45-6789 |
| Credit Card | 1234-5678-9012-3456 |
| API Keys | api_key: sk-xxx... |
| Passwords | password: secret123 |
| Usernames in paths | /Users/david/... |

Detected PII is replaced with `[REDACTED_TYPE]`.

## Database Schema

### training_examples
```sql
CREATE TABLE training_examples (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    format TEXT NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    system_prompt TEXT,
    context TEXT,
    rejected_output TEXT,
    preference_reason TEXT,
    conversation_history TEXT,  -- JSON
    metadata TEXT,              -- JSON
    domain TEXT DEFAULT 'general',
    complexity INTEGER DEFAULT 5,
    quality_tier TEXT DEFAULT 'bronze',
    quality_score REAL DEFAULT 0.5,
    created_at REAL NOT NULL,
    source_id TEXT,
    parent_id TEXT,
    validated INTEGER DEFAULT 0,
    used_in_training INTEGER DEFAULT 0,
    training_run_id TEXT,
    content_hash TEXT,
    input_hash TEXT,
    updated_at REAL
);
```

### Indexes

- `idx_examples_source`: Filter by data source
- `idx_examples_format`: Filter by training format
- `idx_examples_domain`: Filter by domain
- `idx_examples_quality`: Filter by quality
- `idx_examples_content_hash`: Deduplication

## API Usage

### Adding Examples

```python
from training_data import TrainingExample, TrainingFormat, get_training_store

store = get_training_store()

# Instruction example
example = TrainingExample(
    source="manual",
    format=TrainingFormat.INSTRUCTION,
    input_text="How do I sort a list?",
    output_text="Use sorted() or list.sort()...",
    domain="code",
)
example_id = store.add_example(example)

# DPO example
dpo_example = TrainingExample(
    source="user_correction",
    format=TrainingFormat.DPO,
    input_text="What is 2+2?",
    output_text="2+2 equals 4.",
    rejected_output="2+2 equals 5.",
    preference_reason="Math error in original",
)
store.add_example(dpo_example)
```

### Querying Examples

```python
# Get examples for training
examples = store.get_examples_for_training(
    formats=[TrainingFormat.INSTRUCTION, TrainingFormat.CHAT],
    domains=["code", "reasoning"],
    min_quality=0.5,
    exclude_used=True,
    limit=1000,
)

# Get by source
claude_examples = store.get_examples_by_source("claude_capture", limit=100)
```

### Export to JSONL

```python
# Export for MLX training
count = store.export_to_jsonl(
    "/Volumes/David External/sam_training/instruction.jsonl",
    format=TrainingFormat.INSTRUCTION,
    filters={
        "domains": ["code"],
        "min_quality": 0.5,
    },
    mark_as_used=True,
)
print(f"Exported {count} examples")
```

### Deduplication

```python
# Find duplicates (dry run)
stats = store.deduplicate(strategy='content', dry_run=True)
print(f"Found {stats['duplicates_found']} duplicates")

# Actually remove duplicates
stats = store.deduplicate(strategy='content', dry_run=False)
```

## Capture System Usage

### Claude Conversation Capture

```python
from training_capture import get_conversation_capture

capture = get_conversation_capture()

# Capture an escalation
example_id = capture.capture_escalation(
    query="How do I implement quicksort?",
    sam_attempt="I'm not sure...",  # Optional
    claude_response="Here's quicksort:\n```python...",
    domain="code",
    escalation_reason="complexity",
)
```

### Correction Capture

```python
from training_capture import get_correction_capture

capture = get_correction_capture()

# Direct capture
example_id = capture.capture_correction(
    original_query="What's the capital of France?",
    original_response="Lyon",
    correction="Paris",
    what_was_wrong="Incorrect city",
)

# Process from feedback database
stats = capture.process_feedback_corrections(limit=100)
```

## CLI Commands

### Training Data Store

```bash
# View statistics
python training_data.py stats

# Export to JSONL
python training_data.py export -o /path/to/output.jsonl -f instruction

# Deduplicate (dry run)
python training_data.py dedupe --dry-run

# Validate all
python training_data.py validate --min-quality 0.3
```

### Capture System

```bash
# View capture stats
python training_capture.py stats

# Process corrections from feedback DB
python training_capture.py process-corrections --limit 100

# Process preferences from feedback DB
python training_capture.py process-preferences --limit 100

# Run test capture
python training_capture.py test
```

## Integration Points

### With escalation_handler.py

Add to `escalate_to_claude()`:

```python
# After successful Claude response
from training_capture import capture_from_escalation_handler

capture_from_escalation_handler(
    query=prompt,
    sam_response=sam_attempt,
    claude_response=response,
    escalation_reason=reason.value,
    domain=domain,
)
```

### With feedback_system.py

Add to `save_feedback()`:

```python
# When feedback is saved
from training_capture import capture_from_feedback

if feedback_type in ('correction', 'preference'):
    capture_from_feedback(feedback_entry)
```

## Domain Classification

Automatic domain detection based on keywords:

| Domain | Keywords |
|--------|----------|
| code | code, function, class, implement, bug, error, python, javascript... |
| reasoning | explain, why, how does, analyze, compare, evaluate... |
| creative | write, story, poem, creative, imagine, describe... |
| factual | what is, who is, when did, where is, define, fact... |
| planning | plan, schedule, organize, project, task, workflow... |
| conversation | hello, hi, how are, thanks, goodbye, chat... |

## Best Practices

1. **Quality over Quantity**: Focus on high-quality examples over volume
2. **Diversity**: Include examples from all domains
3. **Balance DPO pairs**: Ensure chosen/rejected are meaningfully different
4. **Review gold tier**: Manually verify gold-tier examples
5. **Regular deduplication**: Run deduplication weekly
6. **Export incrementally**: Export only unused examples for training
7. **Track provenance**: Always set source_id for traceability

## Related Documentation

- `/Volumes/Plex/SSOT/projects/SAM_TERMINAL.md` - Main SAM documentation
- `docs/FEEDBACK_FORMAT.md` - Feedback system schema
- `docs/DISTILLATION_FORMAT.md` - Knowledge distillation format
- `training_pipeline.py` - Training execution
