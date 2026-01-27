# SAM Knowledge Distillation System

*Phase 1.1 - Intelligence Core*
*Version: 1.0.0 | Updated: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [Components](#components)
5. [Storage Locations & Schema](#storage-locations--schema)
6. [CLI Commands](#cli-commands)
7. [API Endpoints](#api-endpoints)
8. [Quality Scoring Algorithm](#quality-scoring-algorithm)
9. [Training Export Formats](#training-export-formats)
10. [Configuration Options](#configuration-options)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Knowledge Distillation?

Knowledge distillation is the process of capturing Claude's reasoning patterns when SAM escalates complex queries, then converting those patterns into high-quality training data. The goal is to teach SAM not just *what* Claude said, but *how* Claude reasoned - enabling SAM to handle similar queries independently in the future.

### Why SAM Uses It

SAM is a local 1.5B/3B parameter model running on an 8GB M2 Mac Mini. While powerful for its size, it cannot match Claude's reasoning capabilities for complex tasks. The distillation system bridges this gap by:

1. **Capturing the delta** - SAM's attempt vs Claude's response reveals what SAM needs to learn
2. **Extracting reasoning** - Chain-of-thought, tool use, and self-correction patterns are the valuable signals
3. **Quality over quantity** - Better to have 1,000 excellent examples than 10,000 mediocre ones
4. **Training-ready output** - Format converts cleanly to instruction/DPO/RLHF formats
5. **Human reviewable** - Examples can be audited and approved/rejected

### Key Metrics

The system targets:
- **>20% rejection rate** of low-value captures (prevents training noise)
- **>0.7 quality score** for auto-approval candidates
- **Corrections are highest priority** (when Claude fixes SAM's errors)

---

## Architecture

### System Overview

```
SAM Brain Architecture - Knowledge Distillation Flow
====================================================

User Query
    |
    v
+-------------------+
|   Orchestrator    |  Routes requests based on complexity
+-------------------+
    |
    v
+-------------------+
|  SAM (MLX Local)  |  Attempts to answer first
+-------------------+
    |
    | (Low confidence or complex task)
    v
+-------------------+
| Escalation Handler|  Decides when to escalate
+-------------------+
    |
    v
+-------------------+
|   Claude (API)    |  Via browser bridge (no API cost)
+-------------------+
    |
    | (Response captured)
    v
+-------------------------------------+
|      DISTILLATION PIPELINE          |
|  +-------------------------------+  |
|  | ReasoningPatternExtractor     |  |  <- Extracts CoT, tools, corrections
|  +-------------------------------+  |
|              |                      |
|              v                      |
|  +-------------------------------+  |
|  | QualityFilter                 |  |  <- Scores and filters examples
|  +-------------------------------+  |
|              |                      |
|              v                      |
|  +-------------------------------+  |
|  | DistillationDB                |  |  <- SQLite storage
|  +-------------------------------+  |
+-------------------------------------+
    |
    v
+-------------------+
| Review Interface  |  CLI and API for human review
+-------------------+
    |
    v
+-------------------+
|  Training Export  |  JSONL for fine-tuning
+-------------------+
```

### Component Relationships

| Component | Location | Purpose |
|-----------|----------|---------|
| `escalation_handler.py` | sam_brain/ | Decides when to escalate, captures Claude responses |
| `knowledge_distillation.py` | sam_brain/ | Main distillation module with all components |
| `intelligence_core.py` | sam_brain/ | Higher-level learning integration |
| `sam_api.py` | sam_brain/ | HTTP API for review endpoints |

---

## Data Flow

### ASCII Data Flow Diagram

```
+============================================================================+
|                         DISTILLATION DATA FLOW                              |
+============================================================================+

                                USER QUERY
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                        1. ESCALATION                                   |
    |   escalation_handler.py → process_request() → escalate_to_claude()     |
    +-----------------------------------------------------------------------+
                                    |
             +----------------------+----------------------+
             |                                             |
             v                                             v
    +-----------------+                          +-----------------+
    |  SAM's Attempt  |                          | Claude Response |
    |  (Optional)     |                          |  (Required)     |
    +-----------------+                          +-----------------+
             |                                             |
             +----------------------+----------------------+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                        2. EXTRACTION                                   |
    |   ReasoningPatternExtractor.extract(query, claude_response, sam_attempt)|
    |                                                                         |
    |   Outputs:                                                             |
    |   - ReasoningType (chain_of_thought, tool_use, correction, etc.)       |
    |   - ReasoningSteps[] (structured breakdown)                            |
    |   - ToolUsage[] (tools/commands identified)                            |
    |   - Corrections (if SAM attempt provided)                              |
    |   - Principles[] (reusable guidelines extracted)                       |
    |   - Complexity score (1-10)                                            |
    +-----------------------------------------------------------------------+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                        3. FILTERING                                    |
    |   QualityFilter.filter(query, response, pattern, sam_attempt)          |
    |                                                                         |
    |   Hard Rejections:                                                     |
    |   - Response < 50 chars                                                |
    |   - Repetition ratio > 40%                                             |
    |   - Contains refusal patterns                                          |
    |                                                                         |
    |   Soft Scoring:                                                        |
    |   - Base score: 0.5                                                    |
    |   - Positive: reasoning steps (+0.1), corrections (+0.15), etc.        |
    |   - Negative: too short (-0.2), no reasoning (-0.1), etc.              |
    |                                                                         |
    |   Output: FilterResult(accepted, quality_score, flags)                 |
    +-----------------------------------------------------------------------+
                                    |
              +---------------------+---------------------+
              |                                           |
              v                                           v
    +------------------+                        +------------------+
    |     REJECTED     |                        |     ACCEPTED     |
    | filter_rejections|                        |    examples      |
    |     table        |                        |     table        |
    +------------------+                        +------------------+
                                                         |
                                                         v
    +-----------------------------------------------------------------------+
    |                        4. STORAGE                                      |
    |   DistillationDB.save_example()                                        |
    |                                                                         |
    |   Tables populated:                                                    |
    |   - examples (main training data)                                      |
    |   - reasoning_patterns (extracted patterns)                            |
    |   - corrections (SAM error → Claude fix pairs)                         |
    |   - principles (reusable guidelines)                                   |
    |   - review_queue (for human review)                                    |
    +-----------------------------------------------------------------------+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                        5. REVIEW                                       |
    |   Via CLI: python knowledge_distillation.py review                     |
    |   Via API: GET/POST /api/distillation/review                          |
    |                                                                         |
    |   Actions:                                                             |
    |   - approve_example(id, notes)                                         |
    |   - reject_example(id, reason)                                         |
    |   - batch_approve_above_threshold(0.7)                                 |
    |   - batch_reject_below_threshold(0.3)                                  |
    +-----------------------------------------------------------------------+
                                    |
                                    v
    +-----------------------------------------------------------------------+
    |                        6. EXPORT                                       |
    |   DistillationDB.export_for_training(format="instruction|preference")  |
    |                                                                         |
    |   Output Formats:                                                      |
    |   - instruction: Alpaca-style {instruction, input, output}             |
    |   - preference: DPO-style {prompt, chosen, rejected}                   |
    |   - raw: Full example data for custom processing                       |
    |                                                                         |
    |   Storage: /Volumes/David External/sam_training/distilled/exports/     |
    +-----------------------------------------------------------------------+
```

---

## Components

### 1. ReasoningPatternExtractor

**Location:** `knowledge_distillation.py`

Extracts structured reasoning patterns from Claude responses. This is the core intelligence of the distillation system.

#### Reasoning Types Detected

| Type | Description | Detection Patterns |
|------|-------------|-------------------|
| `chain_of_thought` | Step-by-step reasoning | "Let me think", "First...", "Step 1", numbered lists |
| `tool_use` | Uses tools/commands | Code blocks, "I'll run", CLI commands |
| `correction` | Fixes SAM's error | "Actually", "However", "The issue is" |
| `direct` | Simple direct answer | Short response, no reasoning patterns |
| `multi_step` | Complex multi-part | "There are several steps", "Part 1" |
| `meta_cognitive` | Self-reflection | "I'm not sure", "Let me reconsider" |

#### Usage Example

```python
from knowledge_distillation import ReasoningPatternExtractor

extractor = ReasoningPatternExtractor()

pattern = extractor.extract(
    query="How do I fix this IndexError?",
    claude_response="Let me analyze this step by step...",
    sam_attempt="Try using len() to check the list first.",  # Optional
    domain="code"
)

print(f"Type: {pattern.reasoning_type.value}")
print(f"Steps: {len(pattern.reasoning_steps)}")
print(f"Corrections: {pattern.corrections}")
print(f"Complexity: {pattern.complexity}/10")
print(f"Confidence: {pattern.confidence}")
```

#### Extracted Data Classes

```python
@dataclass
class ReasoningStep:
    step_num: int           # 1, 2, 3...
    action: str             # "identify", "analyze", "solve", "verify"
    content: str            # What was done in this step
    reasoning: str          # Why this step was taken

@dataclass
class ToolUsage:
    tool: str               # "bash", "python", "Read", "git"
    purpose: str            # Why it was used
    input_pattern: str      # What input was provided
    output_handling: str    # How output was processed

@dataclass
class Corrections:
    sam_errors: List[SamError]    # List of errors SAM made
    improvements: List[str]        # Suggestions for improvement
```

---

### 2. QualityFilter

**Location:** `knowledge_distillation.py`

Scores and filters examples to ensure only high-value data enters the training pipeline.

#### Scoring Algorithm

```
Base score: 0.5

POSITIVE FACTORS (max +0.4):
  +0.10  Reasoning chains with 2+ steps
  +0.15  Explicit corrections of SAM errors (MOST VALUABLE)
  +0.10  Extracted principles (1+)
  +0.05  Task complexity >= 5

NEGATIVE FACTORS (max -0.5):
  -0.20  Response too short (<100 chars)
  -0.10  Direct answers (no reasoning)
  -0.30  Repetitive content (>20% repetition)
  -0.20  Incomplete response
  -0.10  Code-only (no explanation)
  -0.10  High uncertainty

FINAL: clamp(score, 0.0, 1.0)
```

#### Hard Rejection Criteria

Examples are immediately rejected (before scoring) if:
- Response length < 50 characters
- Repetition ratio > 40%
- Contains refusal patterns ("I can't help with that")

#### Quality Flags

```python
QUALITY_FLAGS = [
    'repetition',        # Response has repetitive patterns
    'incomplete',        # Answer seems cut off
    'no_reasoning',      # No chain-of-thought present
    'too_short',         # Less than 50 tokens
    'too_long',          # Over 4000 tokens (may be rambling)
    'code_only',         # Just code, no explanation
    'refusal',           # Claude refused to answer
    'uncertain',         # Claude expressed uncertainty
    'outdated',          # Information may be stale
    'hallucination_risk' # Facts that should be verified
]
```

#### Usage Example

```python
from knowledge_distillation import QualityFilter

filter = QualityFilter(
    min_quality_threshold=0.3,
    min_response_length=50,
    max_repetition_ratio=0.4
)

result = filter.filter(
    query="What is Python?",
    response="Python is a programming language...",
    pattern=extracted_pattern,  # Optional
    sam_attempt=None
)

if result.accepted:
    print(f"Quality score: {result.quality_score}")
    print(f"Flags: {result.quality_flags}")
else:
    print(f"Rejected: {result.rejection_reason}")

# Get filter statistics
stats = filter.get_stats()
print(f"Acceptance rate: {stats['acceptance_rate']:.1%}")
print(f"Rejection reasons: {stats['rejection_reasons']}")
```

---

### 3. DistillationDB

**Location:** `knowledge_distillation.py`

SQLite database for storing and managing distilled knowledge.

#### Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `examples` | Main training examples | id, query, claude_response, sam_attempt, quality_score, approved |
| `reasoning_patterns` | Extracted patterns | reasoning_type, reasoning_steps (JSON), tool_usage (JSON) |
| `corrections` | SAM error corrections | error_type, what_sam_said, what_was_wrong, correct_answer |
| `principles` | Reusable guidelines | domain, principle, importance, source_count |
| `review_queue` | Pending human review | example_id, priority, status, reason |
| `filter_rejections` | Rejected examples | query, quality_score, rejection_reason |

#### Key Methods

```python
from knowledge_distillation import DistillationDB

db = DistillationDB()

# Save a new example (auto-extracts patterns and filters)
example_id = db.save_example(
    query="How do I sort a list?",
    claude_response="Here's how to sort...",
    sam_attempt="Use list.sort()",  # Optional
    domain="code",
    auto_extract=True,
    auto_filter=True
)

# Get pending review items
pending = db.get_pending_review(limit=10, domain="code")

# Approve/reject examples
db.approve_example("abc123", notes="High quality example")
db.reject_example("xyz789", reason="Too short")

# Batch operations
db.batch_approve_above_threshold(0.8)  # Auto-approve high quality
db.batch_reject_below_threshold(0.2)   # Auto-reject low quality

# Export for training
count = db.export_for_training(
    output_path=Path("training.jsonl"),
    only_approved=True,
    format="instruction"  # or "preference", "raw"
)

# Get statistics
stats = db.get_stats()
print(f"Total examples: {stats['total_examples']}")
print(f"Approved: {stats['approved_examples']}")
print(f"Pending review: {stats['pending_review']}")
```

---

### 4. Review Interface

#### CLI Review (Interactive)

```bash
# Start interactive review session
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python knowledge_distillation.py review

# Review session commands:
#   [a]pprove - Approve current example
#   [r]eject  - Reject current example
#   [s]kip    - Skip to next example
#   [q]uit    - Exit review session
```

#### API Review Endpoints

See [API Endpoints](#api-endpoints) section below.

---

## Storage Locations & Schema

### File Locations

```
/Volumes/David External/sam_training/distilled/
├── distillation.db           # Primary SQLite database
├── exports/                   # Training export files
│   ├── distilled_instruction_YYYYMMDD_HHMMSS.jsonl
│   ├── distilled_preference_YYYYMMDD_HHMMSS.jsonl
│   └── corrections_distilled_*.jsonl
├── pending_review/           # Batch review files (optional)
└── approved/                 # Reviewed and approved batches

# Fallback (if external drive not mounted):
~/.sam/knowledge_distillation.db
~/.sam/exports/
```

### Database Schema

```sql
-- Primary examples table
CREATE TABLE examples (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    sam_attempt TEXT,
    claude_response TEXT NOT NULL,
    reasoning_type TEXT,
    domain TEXT DEFAULT 'general',
    complexity INTEGER DEFAULT 5,
    quality_score REAL DEFAULT 0.5,
    human_reviewed INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    reviewer_notes TEXT,
    reasoning_pattern_id TEXT,
    created_at REAL,
    reviewed_at REAL,
    exported_at REAL
);

-- Reasoning patterns (linked to examples)
CREATE TABLE reasoning_patterns (
    id TEXT PRIMARY KEY,
    example_id TEXT,
    reasoning_type TEXT NOT NULL,
    reasoning_steps TEXT,      -- JSON array
    tool_usage TEXT,           -- JSON array
    complexity INTEGER,
    confidence REAL,
    created_at REAL
);

-- Corrections (highest value for training)
CREATE TABLE corrections (
    id TEXT PRIMARY KEY,
    example_id TEXT NOT NULL,
    error_type TEXT,           -- incomplete, incorrect, missing_context, etc.
    what_sam_said TEXT,
    what_was_wrong TEXT,
    correct_answer TEXT,
    improvements TEXT,         -- JSON array
    lesson_learned TEXT,
    created_at REAL
);

-- Review queue
CREATE TABLE review_queue (
    id TEXT PRIMARY KEY,
    example_id TEXT NOT NULL,
    priority INTEGER DEFAULT 5,  -- Higher = review first
    reason TEXT,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    assigned_to TEXT,
    created_at REAL,
    updated_at REAL
);

-- Indexes for efficient queries
CREATE INDEX idx_examples_domain ON examples(domain);
CREATE INDEX idx_examples_approved ON examples(approved);
CREATE INDEX idx_examples_reviewed ON examples(human_reviewed);
CREATE INDEX idx_review_queue_status ON review_queue(status);
```

---

## CLI Commands

### Main CLI Entry Point

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python knowledge_distillation.py <command> [options]
```

### Available Commands

#### View Statistics

```bash
# Show distillation database statistics
python knowledge_distillation.py stats

# Output:
# Total examples: 42
# Approved: 15
# Pending review: 20
# Rejected: 7
# By domain: {'code': 30, 'general': 12}
# By reasoning type: {'chain_of_thought': 25, 'correction': 10, ...}
```

#### Interactive Review

```bash
# Start review session
python knowledge_distillation.py review

# Review with domain filter
python knowledge_distillation.py review --domain code

# Review with custom batch size
python knowledge_distillation.py review --limit 20
```

#### Export for Training

```bash
# Export approved examples (default: instruction format)
python knowledge_distillation.py export

# Export with specific format
python knowledge_distillation.py export --format preference
python knowledge_distillation.py export --format instruction
python knowledge_distillation.py export --format raw

# Export to specific location
python knowledge_distillation.py export --output /path/to/training.jsonl

# Export all examples (not just approved)
python knowledge_distillation.py export --all
```

#### Batch Operations

```bash
# Auto-approve high quality examples (>= 0.7 score)
python knowledge_distillation.py batch-approve --threshold 0.7

# Auto-reject low quality examples (< 0.3 score)
python knowledge_distillation.py batch-reject --threshold 0.3
```

#### Extract from Existing Data

```bash
# Process unprocessed raw interactions
python knowledge_distillation.py process-raw

# Extract principles from all examples
python knowledge_distillation.py extract-principles
```

---

## API Endpoints

The SAM API server (default port 8765) exposes distillation review endpoints.

### Start the API Server

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python sam_api.py server 8765
```

### GET Endpoints

#### Get Pending Review Examples

```bash
# Get pending examples (default limit: 10)
curl http://localhost:8765/api/distillation/review

# With filters
curl "http://localhost:8765/api/distillation/review?limit=20&domain=code"
```

**Response:**
```json
{
  "success": true,
  "examples": [
    {
      "id": "abc123def456",
      "query": "How do I implement binary search?",
      "response_preview": "Here's how to implement binary search...",
      "sam_attempt_preview": "Use a for loop...",
      "domain": "code",
      "reasoning_type": "correction",
      "quality_score": 0.85,
      "complexity": 6,
      "priority": 8,
      "review_reason": "Correction detected",
      "has_correction": true
    }
  ],
  "stats": {
    "pending": 20,
    "approved": 15,
    "rejected": 5
  }
}
```

#### Get Review Statistics

```bash
curl http://localhost:8765/api/distillation/review/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "pending": 20,
    "approved": 15,
    "rejected": 5,
    "pending_by_quality": {
      "high": 8,
      "medium": 10,
      "low": 2,
      "very_low": 0
    },
    "pending_by_domain": {
      "code": 15,
      "general": 5
    },
    "pending_corrections": 7
  }
}
```

#### Get Example Details

```bash
curl http://localhost:8765/api/distillation/review/abc123def456
```

**Response:**
```json
{
  "success": true,
  "example": {
    "id": "abc123def456",
    "query": "How do I fix this IndexError?",
    "sam_attempt": "Try using len() first...",
    "claude_response": "The issue is that you're accessing an index that doesn't exist...",
    "reasoning_type": "correction",
    "domain": "code",
    "quality_score": 0.85,
    "complexity": 6,
    "reasoning_pattern": {
      "reasoning_steps": [
        {"step_num": 1, "action": "identify", "content": "..."},
        {"step_num": 2, "action": "analyze", "content": "..."}
      ],
      "tool_usage": []
    },
    "corrections": [
      {
        "error_type": "incomplete",
        "what_sam_said": "Try using len() first...",
        "what_was_wrong": "This doesn't address the root cause...",
        "correct_answer": "..."
      }
    ]
  }
}
```

### POST Endpoints

#### Approve/Reject Example

```bash
# Approve an example
curl -X POST http://localhost:8765/api/distillation/review \
  -H "Content-Type: application/json" \
  -d '{"example_id": "abc123def456", "action": "approve", "notes": "High quality correction example"}'

# Reject an example
curl -X POST http://localhost:8765/api/distillation/review \
  -H "Content-Type: application/json" \
  -d '{"example_id": "xyz789", "action": "reject", "notes": "Too short, not useful"}'
```

**Response:**
```json
{
  "success": true,
  "action": "approved",
  "example_id": "abc123def456"
}
```

#### Batch Approve/Reject

```bash
# Batch approve all examples with quality >= 0.8
curl -X POST http://localhost:8765/api/distillation/review/batch \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "threshold": 0.8}'

# Batch reject all examples with quality < 0.25
curl -X POST http://localhost:8765/api/distillation/review/batch \
  -H "Content-Type: application/json" \
  -d '{"action": "reject", "threshold": 0.25}'
```

**Response:**
```json
{
  "success": true,
  "action": "approve",
  "threshold": 0.8,
  "affected_count": 12
}
```

---

## Quality Scoring Algorithm

### Complete Algorithm Implementation

```python
def calculate_quality_score(
    response: str,
    pattern: Optional[ReasoningPattern] = None,
    sam_attempt: Optional[str] = None
) -> float:
    """
    Score from 0.0 to 1.0 based on learning value.
    Higher scores = more valuable for training.
    """
    score = 0.5  # Base score

    # ===== POSITIVE FACTORS (max +0.4) =====

    # Reasoning chains with 2+ steps: +0.1
    if pattern and len(pattern.reasoning_steps) >= 2:
        score += 0.1
    elif _has_reasoning_markers(response):
        score += 0.05  # Partial credit

    # Explicit corrections of SAM errors: +0.15 (MOST VALUABLE)
    if pattern and pattern.corrections and pattern.corrections.sam_errors:
        score += 0.15
    elif sam_attempt and _has_correction_markers(response):
        score += 0.1  # Partial credit

    # Extracted principles: +0.1
    if pattern and len(pattern.principles) >= 1:
        score += 0.1
    elif _has_principle_markers(response):
        score += 0.05  # Partial credit

    # Task complexity >= 5: +0.05
    if pattern and pattern.complexity >= 5:
        score += 0.05
    elif len(response.split()) > 200:  # Proxy for complexity
        score += 0.03

    # ===== NEGATIVE FACTORS (max -0.5) =====

    # Response length penalties
    if len(response) < 100:
        score -= 0.2
    elif len(response) > 8000:
        score -= 0.1  # May be rambling

    # Direct answers (no reasoning): -0.1
    # Don't penalize corrections - inherently valuable
    if pattern and pattern.reasoning_type == ReasoningType.DIRECT:
        if not (pattern.corrections and pattern.corrections.sam_errors):
            score -= 0.1

    # Repetitive content: -0.15
    if _calculate_repetition_ratio(response) > 0.2:
        score -= 0.15

    # Incomplete response: -0.2
    if _is_incomplete(response):
        score -= 0.2

    # Code-only (no explanation): -0.1
    if _is_code_only(response):
        score -= 0.1

    # High uncertainty: -0.1
    if _has_high_uncertainty(response):
        score -= 0.1

    # Clamp to valid range
    return max(0.0, min(1.0, score))
```

### Score Interpretation

| Score Range | Interpretation | Recommended Action |
|-------------|----------------|-------------------|
| 0.8 - 1.0 | Excellent quality | Auto-approve |
| 0.6 - 0.8 | Good quality | Review recommended |
| 0.4 - 0.6 | Moderate quality | Review required |
| 0.3 - 0.4 | Low quality | Consider rejection |
| 0.0 - 0.3 | Very low quality | Auto-reject |

---

## Training Export Formats

### 1. Instruction Format (Alpaca-style)

Best for: Standard instruction fine-tuning

```json
{
    "instruction": "How do I implement binary search in Python?",
    "input": "",
    "output": "Here's a binary search implementation:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```\n\nKey points:\n1. Requires sorted array\n2. O(log n) time complexity\n3. Returns index or -1 if not found",
    "domain": "code",
    "reasoning_type": "chain_of_thought",
    "quality": 0.85
}
```

### 2. Preference Format (DPO-style)

Best for: Direct Preference Optimization training

```json
{
    "prompt": "How do I remove negative numbers from a list?",
    "chosen": "The safest approach is to use list comprehension:\n\n```python\nitems = [item for item in items if item >= 0]\n```\n\nThis creates a new list without modifying the original during iteration. Avoid using `list.remove()` in a loop as it causes undefined behavior.",
    "rejected": "Here's how to remove negative numbers:\n\n```python\nfor item in items:\n    if item < 0:\n        items.remove(item)\n```",
    "domain": "code"
}
```

### 3. Correction Format

Automatically generated from examples where Claude corrected SAM's errors:

```json
{
    "instruction": "SAM said: Use list.remove() in a for loop to remove items.\n\nWhat was the issue?",
    "input": "How do I remove negative numbers from a list?",
    "output": "The issue was: Modifying a list while iterating over it causes undefined behavior and skipped elements.\n\nThe correct answer is: Use list comprehension: items = [x for x in items if x >= 0]",
    "error_type": "incorrect",
    "domain": "code",
    "type": "correction"
}
```

### Export File Locations

```
/Volumes/David External/sam_training/distilled/exports/
├── distilled_instruction_20260124_130814.jsonl    # Main instruction format
├── distilled_preference_20260124_130814.jsonl     # DPO preference pairs
└── corrections_distilled_instruction_*.jsonl      # Correction pairs
```

---

## Configuration Options

### QualityFilter Configuration

```python
from knowledge_distillation import QualityFilter

filter = QualityFilter(
    min_quality_threshold=0.3,    # Minimum score to accept (default: 0.3)
    min_response_length=50,       # Minimum response chars (default: 50)
    max_repetition_ratio=0.4      # Max repetition before rejection (default: 0.4)
)
```

### DistillationDB Configuration

```python
from knowledge_distillation import DistillationDB
from pathlib import Path

# Use external drive (default)
db = DistillationDB()

# Use explicit path
db = DistillationDB(db_path=Path("/custom/path/distillation.db"))

# Check current storage location
print(f"Database path: {db.db_path}")
print(f"Using external drive: {db.is_external_drive_mounted()}")
```

### Environment Variables

None currently - all configuration is via code or storage strategy.

### Default Paths

```python
# External drive (preferred)
EXTERNAL_DB_PATH = Path("/Volumes/David External/sam_training/distilled/distillation.db")
EXPORT_PATH = Path("/Volumes/David External/sam_training/distilled/exports")

# Local fallback
LOCAL_DB_PATH = Path.home() / ".sam" / "knowledge_distillation.db"
```

---

## Troubleshooting

### Common Issues

#### 1. "External drive not mounted" Warning

**Symptom:** Warning message about using local fallback path

**Cause:** External drive `/Volumes/David External` is not mounted

**Solution:**
```bash
# Check if drive is mounted
ls -la "/Volumes/David External"

# If not mounted, connect the drive or work with local fallback
# Data will be stored in ~/.sam/knowledge_distillation.db
```

#### 2. No Examples Captured

**Symptom:** `get_stats()` shows 0 examples

**Cause:** Escalations not happening or not being captured

**Solution:**
```bash
# 1. Check escalation handler is logging
python -c "from escalation_handler import get_cognitive; print(get_cognitive())"

# 2. Force an escalation to test
python escalation_handler.py --interactive
# Then ask a complex question that will escalate

# 3. Check distillation DB is being written
python -c "from knowledge_distillation import DistillationDB; db = DistillationDB(); print(db.get_stats())"
```

#### 3. High Rejection Rate (>50%)

**Symptom:** Too many examples being rejected by quality filter

**Cause:** Filter thresholds may be too strict or responses are low quality

**Solution:**
```python
# Check rejection reasons
from knowledge_distillation import DistillationDB
db = DistillationDB()
stats = db.get_filter_stats()
print(f"Rejection breakdown: {stats['db_rejection_breakdown']}")

# Adjust filter if needed
from knowledge_distillation import QualityFilter
filter = QualityFilter(
    min_quality_threshold=0.25,  # Lower threshold
    min_response_length=30       # Allow shorter responses
)
```

#### 4. API Endpoints Return 404

**Symptom:** Distillation review endpoints not found

**Cause:** Server not running or wrong port

**Solution:**
```bash
# Start the server
python sam_api.py server 8765

# Verify distillation endpoints are available
curl http://localhost:8765/api/distillation/review/stats
```

#### 5. Export Creates Empty File

**Symptom:** JSONL export file is empty or has 0 examples

**Cause:** No approved examples to export

**Solution:**
```bash
# Check approval status
python -c "from knowledge_distillation import DistillationDB; db = DistillationDB(); print(db.get_stats())"

# If approved = 0, approve some examples first
python knowledge_distillation.py review

# Or batch approve high quality
python -c "from knowledge_distillation import DistillationDB; db = DistillationDB(); print(db.batch_approve_above_threshold(0.7))"
```

#### 6. Database Locked Errors

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Multiple processes accessing the database

**Solution:**
```bash
# Check for processes using the database
lsof "/Volumes/David External/sam_training/distilled/distillation.db"

# Kill stuck processes if necessary
# Or wait for other processes to complete
```

### Diagnostic Commands

```bash
# Full system check
cd ~/ReverseLab/SAM/warp_tauri/sam_brain

# 1. Check database exists and is accessible
python -c "
from knowledge_distillation import DistillationDB, get_db_path, is_external_drive_mounted
print(f'External mounted: {is_external_drive_mounted()}')
print(f'DB path: {get_db_path()}')
db = DistillationDB()
print(f'Stats: {db.get_stats()}')
"

# 2. Check quality filter is working
python -c "
from knowledge_distillation import QualityFilter
f = QualityFilter()
result = f.filter('test query', 'This is a test response that should pass quality checks because it has enough content.')
print(f'Accepted: {result.accepted}, Score: {result.quality_score}')
"

# 3. Test extraction
python -c "
from knowledge_distillation import ReasoningPatternExtractor
e = ReasoningPatternExtractor()
pattern = e.extract(
    'How does this work?',
    'First, we identify the problem. Then, we analyze it. Finally, we solve it.',
    None,
    'general'
)
print(f'Type: {pattern.reasoning_type.value}')
print(f'Steps: {len(pattern.reasoning_steps)}')
print(f'Complexity: {pattern.complexity}')
"

# 4. Verify API endpoints
curl -s http://localhost:8765/api/distillation/review/stats | python -m json.tool
```

---

## Related Documentation

- **Data Format Specification:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/DISTILLATION_FORMAT.md`
- **SAM Brain Architecture:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`
- **Storage Strategy:** `/Volumes/Plex/SSOT/STORAGE_STRATEGY.md`
- **Phase 1 Roadmap:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/ROADMAP.md`

---

*This documentation covers SAM Phase 1.1 Knowledge Distillation System. For questions or issues, check the troubleshooting section or review the source code in `knowledge_distillation.py`.*
