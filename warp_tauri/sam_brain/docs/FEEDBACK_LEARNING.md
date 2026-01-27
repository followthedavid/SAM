# SAM Feedback Learning System

*Phase 1.2.11 - Feedback-Driven Self-Improvement*
*Version: 1.0.0 | Created: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Data Flow](#data-flow)
5. [CLI Commands](#cli-commands)
6. [API Endpoints](#api-endpoints)
7. [Integration with Distillation](#integration-with-distillation)
8. [Configuration Options](#configuration-options)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Feedback Learning?

The Feedback Learning system enables SAM to learn from user signals about response quality. When users give thumbs up/down, provide corrections, or flag issues, SAM captures this data and converts it into training improvements.

### Key Capabilities

1. **FeedbackDB** - Stores all user feedback with quality weighting
2. **CorrectionAnalyzer** - Extracts structured learning from corrections
3. **ConfidenceAdjuster** - Adjusts SAM's confidence based on historical accuracy
4. **TrainingExampleGenerator** - Converts feedback into fine-tuning data

### Why It Matters

| Data Source | Signal Type | Training Value |
|-------------|-------------|----------------|
| Thumbs Up | Positive reinforcement | Validates good responses |
| Thumbs Down | Negative signal | Triggers correction request |
| Corrections | Ground truth | **Highest value** - teaches what was wrong |
| Preferences | Comparative | DPO training pairs |
| Flags | Safety/quality | Patterns to avoid |

### Storage Location

```
Primary:   /Volumes/David External/sam_memory/feedback.db
Fallback:  ~/.sam/feedback.db (if external drive not mounted)
```

---

## Architecture

### System Overview

```
+============================================================================+
|                    FEEDBACK LEARNING ARCHITECTURE                           |
+============================================================================+

                              USER INTERACTION
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                         SAM Response                                   |
    |  orchestrator.py -> generate response -> return with response_id       |
    +-----------------------------------------------------------------------+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                       USER FEEDBACK                                    |
    |  Thumbs up/down | Correction | Preference | Flag                       |
    +-----------------------------------------------------------------------+
                                    |
                                    v
    +=======================================================================+
    ||                    FEEDBACK SYSTEM                                  ||
    ||                                                                     ||
    ||  +--------------------+    +------------------------+               ||
    ||  |    FeedbackDB      |    |  ConfidenceAdjuster    |               ||
    ||  |                    |    |                        |               ||
    ||  | - Store feedback   |--->| - Track accuracy       |               ||
    ||  | - Quality weight   |    | - Compute modifier     |               ||
    ||  | - Aggregates       |    | - Escalation trigger   |               ||
    ||  +--------------------+    +------------------------+               ||
    ||           |                          |                              ||
    ||           v                          v                              ||
    ||  +--------------------+    +------------------------+               ||
    ||  | CorrectionAnalyzer |    |  Domain Stats          |               ||
    ||  |                    |    |                        |               ||
    ||  | - Diff analysis    |    | - Per-domain accuracy  |               ||
    ||  | - Error detection  |    | - Trend analysis       |               ||
    ||  | - Pattern extract  |    | - Error distribution   |               ||
    ||  +--------------------+    +------------------------+               ||
    ||           |                                                         ||
    ||           v                                                         ||
    ||  +--------------------+                                             ||
    ||  | Training Export    |                                             ||
    ||  |                    |                                             ||
    ||  | - JSONL output     |                                             ||
    ||  | - Merge w/ distill |                                             ||
    ||  +--------------------+                                             ||
    ||                                                                     ||
    +=======================================================================+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                    TRAINING PIPELINE                                   |
    |  MLX fine-tuning with LoRA on Qwen2.5-1.5B                            |
    +-----------------------------------------------------------------------+
```

### Component Interactions

```
+------------------+     saves     +------------------+
|  sam_api.py      |-------------->|   FeedbackDB     |
|  (API endpoints) |               |   (SQLite)       |
+------------------+               +--------+---------+
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
                    v                      v                      v
          +-----------------+    +------------------+    +------------------+
          | confidence_     |    | feedback_        |    | feedback_        |
          | tracking table  |    | aggregates table |    | sessions table   |
          +-----------------+    +------------------+    +------------------+
                    |
                    v
          +-----------------+
          | Confidence      |
          | Adjuster        |
          +-----------------+
                    |
                    v
          +-----------------+
          | Escalation      |
          | Recommendation  |
          +-----------------+
```

---

## Components

### 1. FeedbackDB

**Location:** `feedback_system.py`

Stores and manages all user feedback with quality weighting.

#### FeedbackEntry Schema

```python
@dataclass
class FeedbackEntry:
    # Identifiers
    feedback_id: str          # SHA256(response_id + timestamp)[:16]
    response_id: str          # Links to SAM response
    session_id: str           # Groups feedback in session
    user_id: Optional[str]    # Multi-user support

    # Timestamps
    timestamp: float          # When feedback given
    response_timestamp: float # When response generated

    # Feedback Type
    feedback_type: str        # rating, correction, preference, flag

    # Rating (feedback_type="rating")
    rating: Optional[int]     # -1 (down), +1 (up), or 1-5 scale

    # Correction (feedback_type="correction")
    correction: Optional[str]         # User's correct answer
    correction_type: Optional[str]    # full_replacement, partial_fix, addition
    what_was_wrong: Optional[str]     # Explanation of error

    # Preference (feedback_type="preference")
    preferred_response: Optional[str] # User's preferred alternative
    comparison_basis: Optional[str]   # Why this is better

    # Flag (feedback_type="flag")
    flag_type: Optional[str]          # harmful, incorrect, off_topic, etc.
    flag_details: Optional[str]

    # Context
    original_query: str               # User's question
    original_response: str            # SAM's response
    domain: str                       # code, reasoning, creative, etc.

    # Processing
    processed: bool                   # Converted to training data?
    quality_weight: float             # 0.0-1.0 training weight
```

#### Key Methods

```python
from feedback_system import FeedbackDB

db = FeedbackDB()

# Save feedback
feedback_id = db.save_feedback(
    response_id="resp_abc123",
    session_id="sess_xyz789",
    feedback_type="correction",
    correction="The correct answer is...",
    original_query="How do I...",
    original_response="You should...",
    domain="code"
)

# Get feedback for a response
feedback = db.get_feedback_for_response("resp_abc123")

# Get recent feedback
recent = db.get_recent_feedback(limit=20, domain="code")

# Get unprocessed feedback for training
training_data = db.get_unprocessed_for_training(limit=100, min_quality=0.3)

# Get comprehensive statistics
stats = db.get_feedback_stats()
```

---

### 2. CorrectionAnalyzer

**Location:** `feedback_system.py`

Analyzes corrections to extract structured training data. Detects error types, computes diffs, and generates training examples.

#### Error Categories

```python
class ErrorCategory(Enum):
    FACTUAL = "factual"             # Wrong facts
    INCOMPLETE = "incomplete"       # Missing information
    FORMAT = "format"               # Wrong structure
    TONE = "tone"                   # Wrong tone
    OUTDATED = "outdated"           # Stale information
    LOGICAL = "logical"             # Logic error
    CODE_SYNTAX = "code_syntax"     # Syntax error in code
    CODE_LOGIC = "code_logic"       # Logic error in code
    CODE_STYLE = "code_style"       # Style issues
    MISUNDERSTOOD = "misunderstood" # Wrong interpretation
    HALLUCINATION = "hallucination" # Made up info
    VERBOSE = "verbose"             # Too wordy
    UNCLEAR = "unclear"             # Confusing
    OTHER = "other"
```

#### Usage

```python
from feedback_system import CorrectionAnalyzer

analyzer = CorrectionAnalyzer()

# Analyze a single correction
analysis = analyzer.analyze_correction(
    original="The capital of Australia is Sydney.",
    correction="The capital of Australia is Canberra.",
    query="What is the capital of Australia?",
    what_was_wrong="Sydney is the largest city, not the capital"
)

print(f"Error types: {analysis.error_types}")        # ['factual']
print(f"Similarity: {analysis.similarity_ratio}")    # 0.87
print(f"Change ratio: {analysis.change_ratio}")      # 0.13
print(f"Patterns: {len(analysis.error_patterns)}")   # 1

# Process all unprocessed corrections from database
training_data = analyzer.process_corrections_from_db(db, limit=100)

# Export as training data
count = analyzer.export_training_data(
    analyses=training_data,
    output_path=Path("/Volumes/David External/sam_training/corrections.jsonl")
)

# Get error statistics
stats = analyzer.get_error_statistics(training_data)
```

#### CorrectionAnalysis Output

```python
@dataclass
class CorrectionAnalysis:
    original_text: str              # What SAM said
    corrected_text: str             # What it should be
    error_type: str                 # Primary error category
    error_types: List[str]          # All detected errors
    diff_segments: List[DiffSegment] # Specific changes
    similarity_ratio: float         # 0.0-1.0
    change_ratio: float             # % of text changed
    error_patterns: List[Dict]      # Patterns to avoid
    training_example: Dict          # Ready for fine-tuning
```

---

### 3. ConfidenceAdjuster

**Location:** `feedback_system.py`

Tracks historical accuracy per domain/topic and provides confidence modifiers. Helps SAM know when to be more/less confident and when to escalate to Claude.

#### Domain Expertise Levels

```python
DOMAIN_EXPERTISE = {
    "code": 0.7,       # SAM trained on code
    "roleplay": 0.8,   # SAM's personality
    "general": 0.5,    # General knowledge
    "factual": 0.4,    # Facts need verification
    "reasoning": 0.4,  # Complex reasoning
    "creative": 0.6,   # Creative tasks
    "planning": 0.5,   # Planning tasks
}
```

#### Usage

```python
from feedback_system import ConfidenceAdjuster

adjuster = ConfidenceAdjuster()

# Get confidence modifier for a domain
modifier = adjuster.get_confidence_modifier("code", "python")
# Returns: -0.3 to +0.3

# Adjust SAM's base confidence
base_confidence = 0.7
adjusted = base_confidence + modifier

# Record feedback to update tracking
adjuster.record_feedback(
    domain="code",
    topic="python",
    is_positive=False,
    is_correction=True,
    error_type="code_logic"
)

# Check if should escalate to Claude
if adjuster.should_suggest_escalation("reasoning"):
    # Accuracy in reasoning domain is below threshold
    escalate_to_claude()

# Get comprehensive domain statistics
stats = adjuster.get_domain_stats()
# Returns: {domain: {accuracy_rate, trend, modifier, errors, escalate?}}
```

#### Confidence Modifier Calculation

```
modifier = 0.0

# Accuracy factor (deviation from domain expertise)
accuracy_delta = accuracy_rate - domain_expertise
modifier += accuracy_delta * 0.3

# Trend factor
if improving: modifier += 0.05 * trend_strength
if declining: modifier -= 0.10 * trend_strength

# Sample size confidence
if total_feedback < 5:
    modifier *= total_feedback / 5

# Clamp to [-0.3, +0.3]
```

---

### 4. TrainingExampleGenerator

Training examples are generated automatically by CorrectionAnalyzer. The output format is compatible with MLX fine-tuning.

#### Output Formats

**Instruction Format (from corrections):**
```json
{
  "instruction": "Correct this response: The capital of Australia is Sydney...",
  "input": "What is the capital of Australia?",
  "output": "The capital of Australia is Canberra.",
  "error_type": "factual"
}
```

**Preference Format (from preference feedback):**
```json
{
  "prompt": "How do I reverse a list in Python?",
  "chosen": "Use list[::-1] for a new list, or list.reverse() for in-place.",
  "rejected": "Use list[::-1]."
}
```

---

## Data Flow

### Complete Feedback Flow

```
USER QUERY
    |
    v
+-------------------+
| SAM generates     |
| response with     |
| response_id       |
+-------------------+
    |
    v
+-------------------+
| User provides     |
| feedback          |
| (thumbs/correct)  |
+-------------------+
    |
    v
+-------------------+
| FeedbackDB        |
| save_feedback()   |
|                   |
| - Generate ID     |
| - Calculate weight|
| - Store in SQLite |
+-------------------+
    |
    +----------------+----------------+
    |                |                |
    v                v                v
+---------+   +-----------+   +-----------+
| Update  |   | Update    |   | Update    |
| aggre-  |   | session   |   | confidence|
| gates   |   | tracking  |   | tracking  |
+---------+   +-----------+   +-----------+
                                   |
                                   v
                             +-----------+
                             | Confidence|
                             | Adjuster  |
                             | recalc    |
                             +-----------+

IF feedback_type == "correction":
    |
    v
+-------------------+
| Correction        |
| Analyzer          |
|                   |
| - Compute diff    |
| - Detect errors   |
| - Extract patterns|
| - Generate        |
|   training example|
+-------------------+
    |
    v
+-------------------+
| Export to         |
| training JSONL    |
+-------------------+
    |
    v
+-------------------+
| MLX fine-tuning   |
| with LoRA         |
+-------------------+
```

### Quality Weighting Algorithm

```python
def calculate_feedback_weight(feedback, current_time):
    weight = 0.5  # Base

    # Feedback type weights
    type_weights = {
        'correction': +0.3,   # Most valuable
        'preference': +0.2,   # Very valuable
        'rating': +0.1,       # Signal
        'flag': 0.0,          # Analysis only
    }
    weight += type_weights[feedback.feedback_type]

    # Temporal decay (30-day half-life)
    age_hours = (current_time - feedback.timestamp) / 3600
    decay = 0.5 ** (age_hours / 720)
    weight *= 0.5 + (0.5 * decay)

    # Quality bonuses
    if correction and len(correction) > 100: weight += 0.05
    if what_was_wrong and len(what_was_wrong) > 50: weight += 0.05
    if escalated_to_claude: weight += 0.05
    if high_confidence_mistake: weight += 0.1

    return clamp(weight, 0.0, 1.0)
```

---

## CLI Commands

### Via sam_api.py CLI

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain

# Get feedback statistics
python sam_api.py feedback-stats

# Record feedback (JSON input)
python sam_api.py feedback '{"improvement_id": "...", "success": true}'
```

### Via Python Directly

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain

# Get feedback stats
python -c "
from feedback_system import get_feedback_db
db = get_feedback_db()
stats = db.get_feedback_stats()
import json
print(json.dumps(stats, indent=2))
"

# Process corrections for training
python -c "
from feedback_system import FeedbackDB, CorrectionAnalyzer
db = FeedbackDB()
analyzer = CorrectionAnalyzer()
analyses = analyzer.process_corrections_from_db(db, limit=50)
print(f'Processed {len(analyses)} corrections')

# Export training data
from pathlib import Path
count = analyzer.export_training_data(
    analyses,
    Path('/Volumes/David External/sam_training/corrections.jsonl')
)
print(f'Exported {count} training examples')
"

# Get confidence modifiers
python -c "
from feedback_system import ConfidenceAdjuster
adjuster = ConfidenceAdjuster()

domains = ['code', 'reasoning', 'general', 'roleplay']
for domain in domains:
    mod = adjuster.get_confidence_modifier(domain)
    esc = adjuster.should_suggest_escalation(domain)
    print(f'{domain}: modifier={mod:+.2f}, escalate={esc}')
"

# Check domain statistics
python -c "
from feedback_system import ConfidenceAdjuster
import json
adjuster = ConfidenceAdjuster()
stats = adjuster.get_domain_stats()
print(json.dumps(stats, indent=2))
"
```

---

## API Endpoints

The SAM API server (port 8765) exposes feedback endpoints.

### Start Server

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python sam_api.py server 8765
```

### POST /api/cognitive/feedback

Submit feedback for a response.

**Request:**
```bash
curl -X POST http://localhost:8765/api/cognitive/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "response_id": "resp_abc123",
    "session_id": "sess_xyz789",
    "feedback_type": "rating",
    "rating": 1
  }'
```

**With correction:**
```bash
curl -X POST http://localhost:8765/api/cognitive/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "response_id": "resp_abc123",
    "session_id": "sess_xyz789",
    "feedback_type": "correction",
    "correction": "The correct answer is...",
    "correction_type": "full_replacement",
    "what_was_wrong": "The original was incomplete",
    "query": "How do I...",
    "response": "You should...",
    "domain": "code"
  }'
```

**Response:**
```json
{
  "success": true,
  "feedback_id": "fb_def456",
  "response_id": "resp_abc123",
  "feedback_type": "correction"
}
```

### GET /api/cognitive/feedback

Get feedback statistics.

```bash
curl http://localhost:8765/api/cognitive/feedback
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_feedback": 142,
    "by_type": {"rating": 100, "correction": 30, "preference": 10, "flag": 2},
    "sentiment": {"positive": 80, "negative": 20, "net_sentiment": 0.75},
    "processed": {"total": 120, "pending": 22},
    "quality": {"avg_weight": 0.65, "high_quality_count": 45},
    "recent_24h": 12,
    "by_domain": {"code": 80, "general": 40, "reasoning": 22},
    "storage": {"location": "/Volumes/David External/sam_memory/feedback.db"}
  }
}
```

### GET /api/cognitive/feedback/recent

Get recent feedback entries.

```bash
# Basic
curl "http://localhost:8765/api/cognitive/feedback/recent"

# With filters
curl "http://localhost:8765/api/cognitive/feedback/recent?limit=20&domain=code&type=correction"
```

### GET /api/notifications

Get proactive feedback notifications (Phase 1.2.8).

```bash
curl http://localhost:8765/api/notifications
```

**Response:**
```json
{
  "success": true,
  "daily_corrections": 3,
  "daily_negative": 2,
  "unprocessed_count": 8,
  "declining_domains": [
    {"domain": "reasoning", "recent_accuracy": 0.6, "previous_accuracy": 0.8}
  ],
  "threshold_alerts": [
    {"type": "corrections_threshold", "message": "3 corrections today", "urgency": "medium"},
    {"type": "training_ready", "message": "8 items ready for training", "urgency": "low"}
  ]
}
```

---

## Integration with Distillation

The feedback system complements the distillation pipeline (Phase 1.1).

### Comparison

| System | Source | Quality | Volume |
|--------|--------|---------|--------|
| Distillation | Claude escalations | Very high (Claude's reasoning) | Low (only escalations) |
| Feedback | User signals | High (ground truth preference) | Medium (user-provided) |

### Merging for Training

```python
from knowledge_distillation import DistillationDB
from feedback_system import FeedbackDB, CorrectionAnalyzer
from pathlib import Path

# Get distillation examples
dist_db = DistillationDB()
distilled = dist_db.export_for_training(
    output_path=Path("/tmp/distilled.jsonl"),
    only_approved=True,
    format="instruction"
)

# Get feedback examples
fb_db = FeedbackDB()
analyzer = CorrectionAnalyzer()
corrections = analyzer.process_corrections_from_db(fb_db)
analyzer.export_training_data(
    corrections,
    Path("/tmp/corrections.jsonl")
)

# Combine for training
# cat /tmp/distilled.jsonl /tmp/corrections.jsonl > /tmp/combined.jsonl
```

### Feedback Validates Distillation

When users provide feedback on Claude-escalated responses, it validates whether the distilled example was good:

```python
# Feedback on escalated response
if feedback.escalated_to_claude:
    if feedback.rating == 1:
        # Claude's response was good - validate distillation
        distillation_db.mark_as_validated(response_id)
    elif feedback.rating == -1:
        # Claude's response was bad - flag for review
        distillation_db.flag_for_review(response_id)
```

---

## Configuration Options

### FeedbackDB Configuration

```python
from feedback_system import FeedbackDB
from pathlib import Path

# Use default path (external drive if mounted)
db = FeedbackDB()

# Use explicit path
db = FeedbackDB(db_path=Path("/custom/path/feedback.db"))
```

### ConfidenceAdjuster Configuration

```python
# Customize domain expertise levels
ConfidenceAdjuster.DOMAIN_EXPERTISE["custom_domain"] = 0.6

# Customize escalation thresholds
ConfidenceAdjuster.ESCALATION_THRESHOLDS["custom_domain"] = 0.45

# Adjust recent feedback window
ConfidenceAdjuster.RECENT_WINDOW_SIZE = 30

# Adjust minimum samples for reliable stats
ConfidenceAdjuster.MIN_FEEDBACK_FOR_STATS = 10
```

### Quality Thresholds

```python
# Minimum quality for training export
MIN_QUALITY_FOR_TRAINING = 0.3

# High quality threshold
HIGH_QUALITY_THRESHOLD = 0.7
```

---

## Troubleshooting

### Common Issues

#### 1. "External drive not mounted"

**Symptom:** Using local fallback path

**Solution:**
```bash
# Check if drive is mounted
ls -la "/Volumes/David External"

# If not mounted, connect drive or work with local fallback
# Data will be stored in ~/.sam/feedback.db
```

#### 2. No feedback being captured

**Symptom:** `get_feedback_stats()` shows 0 total

**Cause:** API not receiving feedback or missing response_id

**Solution:**
```bash
# Check API is running
curl http://localhost:8765/api/cognitive/feedback

# Ensure responses include response_id
python -c "
from feedback_system import generate_response_id
import time
rid = generate_response_id('test query', time.time())
print(f'Response ID: {rid}')
"
```

#### 3. Low quality weights

**Symptom:** Most feedback has weight < 0.5

**Cause:** Short corrections, missing explanations

**Solution:**
- Encourage detailed corrections with explanations
- Provide `what_was_wrong` field when submitting corrections

#### 4. Confidence modifier always 0

**Symptom:** `get_confidence_modifier()` returns 0.0

**Cause:** Not enough feedback samples (< 5)

**Solution:**
```bash
# Check sample counts
python -c "
from feedback_system import ConfidenceAdjuster
import json
adjuster = ConfidenceAdjuster()
stats = adjuster.get_domain_stats()
print(json.dumps(stats, indent=2))
"

# Need at least 5 feedback items per domain for reliable modifiers
```

### Diagnostic Commands

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain

# Full system check
python -c "
from feedback_system import (
    FeedbackDB, get_feedback_db_path, is_external_drive_mounted,
    CorrectionAnalyzer, ConfidenceAdjuster
)
import json

print('=== Feedback System Diagnostics ===')
print(f'External mounted: {is_external_drive_mounted()}')
print(f'DB path: {get_feedback_db_path()}')

db = FeedbackDB()
stats = db.get_feedback_stats()
print(f'Total feedback: {stats[\"total_feedback\"]}')
print(f'By type: {stats[\"by_type\"]}')
print(f'Sentiment: {stats[\"sentiment\"]}')

adjuster = ConfidenceAdjuster()
domain_stats = adjuster.get_domain_stats()
print(f'Domains tracked: {len(domain_stats)}')

print('\\n=== OK ===')
"

# Test correction analysis
python -c "
from feedback_system import CorrectionAnalyzer

analyzer = CorrectionAnalyzer()
analysis = analyzer.analyze_correction(
    original='Python lists are mutable arrays.',
    correction='Python lists are mutable sequences that can hold items of any type.',
    query='What is a Python list?'
)

print(f'Error types: {analysis.error_types}')
print(f'Similarity: {analysis.similarity_ratio:.2f}')
print(f'Change ratio: {analysis.change_ratio:.2f}')
print(f'Training example keys: {list(analysis.training_example.keys())}')
"

# Verify API endpoints
curl -s http://localhost:8765/api/cognitive/feedback | python -m json.tool
```

---

## Related Documentation

- **Feedback Schema:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/FEEDBACK_FORMAT.md`
- **Distillation System:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/DISTILLATION.md`
- **Data Format Spec:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/DISTILLATION_FORMAT.md`
- **SAM Brain Architecture:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`
- **Storage Strategy:** `/Volumes/Plex/SSOT/STORAGE_STRATEGY.md`

---

## Quick Reference

### Common Operations

```python
from feedback_system import (
    FeedbackDB, CorrectionAnalyzer, ConfidenceAdjuster,
    get_feedback_db
)

# === Save feedback ===
db = get_feedback_db()
fb_id = db.save_feedback(
    response_id="...",
    session_id="...",
    feedback_type="correction",
    correction="...",
    original_query="...",
    original_response="...",
    domain="code"
)

# === Analyze corrections ===
analyzer = CorrectionAnalyzer()
analysis = analyzer.analyze_correction(original, correction)

# === Get confidence modifier ===
adjuster = ConfidenceAdjuster()
modifier = adjuster.get_confidence_modifier("code", "python")

# === Check if should escalate ===
if adjuster.should_suggest_escalation("reasoning"):
    escalate_to_claude()

# === Export for training ===
corrections = analyzer.process_corrections_from_db(db)
analyzer.export_training_data(corrections, Path("corrections.jsonl"))
```

---

*This documentation covers SAM Phase 1.2 Feedback Learning System. The feedback system enables SAM to learn from user signals, improving response quality over time through continuous self-improvement.*
