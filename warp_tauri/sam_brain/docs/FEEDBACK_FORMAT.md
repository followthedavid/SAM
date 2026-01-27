# SAM Feedback System Design
*Phase 1.2.1 - Feedback Data Model*
*Version: 1.0.0 | Created: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Core Data Model](#core-data-model)
3. [Feedback Types](#feedback-types)
4. [SQLite Schema](#sqlite-schema)
5. [Feedback-to-Training Pipeline](#feedback-to-training-pipeline)
6. [Quality Weighting Algorithm](#quality-weighting-algorithm)
7. [Integration Points](#integration-points)
8. [API Endpoints](#api-endpoints)
9. [Implementation Notes](#implementation-notes)
10. [Examples](#examples)

---

## Overview

### Purpose

The feedback system captures user signals about SAM's response quality, enabling:

1. **Immediate improvement** - Bad responses are flagged for correction
2. **Training data generation** - Thumbs up/down become preference pairs
3. **Error pattern detection** - Repeated negative feedback reveals weaknesses
4. **Correction learning** - User-provided corrections become high-value training data
5. **Session continuity** - Track feedback across conversation sessions

### Design Principles

1. **Low friction** - Thumbs up/down is always available (1 click)
2. **Rich data when offered** - Corrections capture maximum signal
3. **Training-first design** - Every field maps to a training format
4. **Temporal awareness** - Recent feedback weighted higher
5. **Session coherence** - Related feedback grouped for context

### Relationship to Distillation

The feedback system complements the existing distillation pipeline:

| System | Source | Quality | Volume |
|--------|--------|---------|--------|
| Distillation | Claude escalations | Very high (Claude's reasoning) | Low (only escalations) |
| Feedback | User signals | High (ground truth preference) | Medium (when users provide it) |

Feedback is especially valuable for:
- Validating distilled examples (was SAM's learned behavior correct?)
- Generating preference pairs (DPO training)
- Identifying where SAM needs improvement

---

## Core Data Model

### Primary Record: FeedbackEntry

```python
@dataclass
class FeedbackEntry:
    """A single piece of user feedback about a SAM response."""

    # === Identifiers ===
    feedback_id: str          # Unique ID (SHA256(response_id + timestamp)[:16])
    response_id: str          # Links to the SAM response being rated
    session_id: str           # Groups feedback within a conversation session
    user_id: Optional[str]    # User identifier (if multi-user)

    # === Timestamps ===
    timestamp: float          # Unix timestamp when feedback was given
    response_timestamp: float # When the original response was generated

    # === Feedback Type ===
    feedback_type: str        # rating, correction, preference, flag

    # === Rating (for feedback_type="rating") ===
    rating: Optional[int]     # Thumbs: -1 (down) or +1 (up)
                              # Scale: 1-5 (if enabled)

    # === Correction (for feedback_type="correction") ===
    correction: Optional[str]           # User-provided correct answer
    correction_type: Optional[str]      # full_replacement, partial_fix, addition
    what_was_wrong: Optional[str]       # User explanation of the error

    # === Preference (for feedback_type="preference") ===
    preferred_response: Optional[str]   # User's preferred alternative
    comparison_basis: Optional[str]     # Why this is better (tone, accuracy, etc.)

    # === Flag (for feedback_type="flag") ===
    flag_type: Optional[str]  # harmful, incorrect, off_topic, unhelpful, other
    flag_details: Optional[str]

    # === Context ===
    original_query: str       # The user's original question
    original_response: str    # SAM's response that received feedback
    conversation_context: Optional[str]  # Recent conversation history

    # === Metadata ===
    domain: str               # code, reasoning, creative, factual, planning
    response_confidence: Optional[float]  # SAM's confidence when responding
    escalated_to_claude: bool  # Was this an escalated response?

    # === Processing Status ===
    processed: bool           # Has this been converted to training data?
    training_format: Optional[str]  # preference, correction, or excluded
    quality_weight: float     # Computed weight for training (0.0-1.0)
    processed_at: Optional[float]
```

### Supporting Types

#### FeedbackType Enum

```python
class FeedbackType(Enum):
    """Types of feedback users can provide."""
    RATING = "rating"           # Simple thumbs up/down or 1-5 scale
    CORRECTION = "correction"   # User provides the correct answer
    PREFERENCE = "preference"   # User provides a preferred alternative
    FLAG = "flag"              # User flags problematic content
```

#### CorrectionType Enum

```python
class CorrectionType(Enum):
    """Types of corrections users can provide."""
    FULL_REPLACEMENT = "full_replacement"  # Completely replace the response
    PARTIAL_FIX = "partial_fix"           # Fix specific parts
    ADDITION = "addition"                  # Add missing information
    CLARIFICATION = "clarification"        # Rephrase for clarity
```

#### FlagType Enum

```python
class FlagType(Enum):
    """Types of flags for problematic responses."""
    HARMFUL = "harmful"         # Potentially dangerous content
    INCORRECT = "incorrect"     # Factually wrong
    OFF_TOPIC = "off_topic"     # Didn't address the question
    UNHELPFUL = "unhelpful"     # Technically correct but not useful
    REPETITIVE = "repetitive"   # Too much repetition
    INCOMPLETE = "incomplete"   # Missing important information
    OTHER = "other"             # Other issues
```

---

## Feedback Types

### 1. Rating Feedback

The simplest form - thumbs up/down or 1-5 scale.

**Use Case:** Quick signal about response quality with minimal effort.

**Training Value:**
- Thumbs up: Potential positive example for SFT
- Thumbs down: Triggers correction request or becomes "rejected" in DPO pair

```json
{
  "feedback_type": "rating",
  "rating": 1,
  "response_id": "resp_abc123",
  "session_id": "sess_xyz789",
  "original_query": "How do I reverse a list in Python?",
  "original_response": "You can use list[::-1] to reverse a list..."
}
```

### 2. Correction Feedback

User provides the correct answer - HIGHEST VALUE for training.

**Use Case:** SAM gave a wrong or incomplete answer, user knows the right one.

**Training Value:**
- Creates error correction training pair (Task 1.1.3 format)
- Very high weight in training (corrections are most valuable)

```json
{
  "feedback_type": "correction",
  "correction": "Actually, list.reverse() modifies in-place while list[::-1] creates a new list. You should mention both options.",
  "correction_type": "addition",
  "what_was_wrong": "Only mentioned one method, didn't explain the difference",
  "response_id": "resp_abc123",
  "original_query": "How do I reverse a list in Python?",
  "original_response": "You can use list[::-1] to reverse a list."
}
```

### 3. Preference Feedback

User provides an alternative response they'd prefer.

**Use Case:** SAM's answer was okay but user knows a better way to phrase it.

**Training Value:**
- Direct DPO preference pair (chosen vs rejected)
- Medium-high weight (user preference is ground truth)

```json
{
  "feedback_type": "preference",
  "preferred_response": "There are two main ways to reverse a list:\n1. `list[::-1]` - creates a new reversed list\n2. `list.reverse()` - reverses in-place\n\nChoose based on whether you need the original list preserved.",
  "comparison_basis": "More complete and organized",
  "response_id": "resp_abc123",
  "original_query": "How do I reverse a list in Python?",
  "original_response": "You can use list[::-1] to reverse a list."
}
```

### 4. Flag Feedback

User flags problematic content.

**Use Case:** Response is harmful, incorrect, or off-topic.

**Training Value:**
- Negative example (should NOT generate this)
- May trigger safety review if harmful
- Contributes to pattern detection

```json
{
  "feedback_type": "flag",
  "flag_type": "incorrect",
  "flag_details": "The syntax shown would cause an error in Python 2",
  "response_id": "resp_abc123",
  "original_query": "How do I reverse a list?",
  "original_response": "Use list.reverse()..."
}
```

---

## SQLite Schema

### Main Feedback Table

```sql
-- Primary feedback storage
CREATE TABLE feedback (
    -- Identifiers
    feedback_id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT,

    -- Timestamps
    timestamp REAL NOT NULL,
    response_timestamp REAL,

    -- Feedback type and data
    feedback_type TEXT NOT NULL,  -- rating, correction, preference, flag

    -- Rating data (when feedback_type = 'rating')
    rating INTEGER,  -- -1, +1 (thumbs) or 1-5 (scale)

    -- Correction data (when feedback_type = 'correction')
    correction TEXT,
    correction_type TEXT,
    what_was_wrong TEXT,

    -- Preference data (when feedback_type = 'preference')
    preferred_response TEXT,
    comparison_basis TEXT,

    -- Flag data (when feedback_type = 'flag')
    flag_type TEXT,
    flag_details TEXT,

    -- Context
    original_query TEXT NOT NULL,
    original_response TEXT NOT NULL,
    conversation_context TEXT,

    -- Metadata
    domain TEXT DEFAULT 'general',
    response_confidence REAL,
    escalated_to_claude INTEGER DEFAULT 0,

    -- Processing status
    processed INTEGER DEFAULT 0,
    training_format TEXT,
    quality_weight REAL DEFAULT 0.5,
    processed_at REAL,

    -- Timestamps
    created_at REAL DEFAULT (unixepoch('now'))
);

-- Indexes for efficient queries
CREATE INDEX idx_feedback_response ON feedback(response_id);
CREATE INDEX idx_feedback_session ON feedback(session_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_feedback_processed ON feedback(processed);
CREATE INDEX idx_feedback_domain ON feedback(domain);
CREATE INDEX idx_feedback_timestamp ON feedback(timestamp);
CREATE INDEX idx_feedback_quality ON feedback(quality_weight);
```

### Feedback Aggregates Table

```sql
-- Aggregate feedback statistics per response
CREATE TABLE feedback_aggregates (
    response_id TEXT PRIMARY KEY,

    -- Rating counts
    thumbs_up_count INTEGER DEFAULT 0,
    thumbs_down_count INTEGER DEFAULT 0,
    avg_rating REAL,  -- If using 1-5 scale

    -- Feedback type counts
    correction_count INTEGER DEFAULT 0,
    preference_count INTEGER DEFAULT 0,
    flag_count INTEGER DEFAULT 0,

    -- Computed metrics
    net_sentiment REAL,  -- (up - down) / total
    confidence_delta REAL,  -- How much feedback changed confidence

    -- Timestamps
    first_feedback_at REAL,
    last_feedback_at REAL,

    -- Links
    session_ids TEXT,  -- JSON array of session_ids that provided feedback

    updated_at REAL DEFAULT (unixepoch('now'))
);

CREATE TRIGGER update_feedback_aggregates
AFTER INSERT ON feedback
BEGIN
    INSERT INTO feedback_aggregates (response_id, first_feedback_at, last_feedback_at)
    VALUES (NEW.response_id, NEW.timestamp, NEW.timestamp)
    ON CONFLICT(response_id) DO UPDATE SET
        thumbs_up_count = thumbs_up_count + CASE WHEN NEW.rating = 1 THEN 1 ELSE 0 END,
        thumbs_down_count = thumbs_down_count + CASE WHEN NEW.rating = -1 THEN 1 ELSE 0 END,
        correction_count = correction_count + CASE WHEN NEW.feedback_type = 'correction' THEN 1 ELSE 0 END,
        preference_count = preference_count + CASE WHEN NEW.feedback_type = 'preference' THEN 1 ELSE 0 END,
        flag_count = flag_count + CASE WHEN NEW.feedback_type = 'flag' THEN 1 ELSE 0 END,
        last_feedback_at = NEW.timestamp,
        updated_at = unixepoch('now');
END;
```

### Session Tracking Table

```sql
-- Track feedback patterns across sessions
CREATE TABLE feedback_sessions (
    session_id TEXT PRIMARY KEY,

    -- Session metrics
    total_responses INTEGER DEFAULT 0,
    feedback_given INTEGER DEFAULT 0,
    feedback_rate REAL,  -- feedback_given / total_responses

    -- Sentiment
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,

    -- Session quality score
    session_quality REAL,

    -- Timestamps
    started_at REAL,
    last_activity_at REAL,

    -- Context
    primary_domain TEXT,
    topics TEXT  -- JSON array of topics discussed
);
```

---

## Feedback-to-Training Pipeline

### Conversion Flow

```
Feedback Entry
    |
    v
+------------------------+
| 1. VALIDATION          |
|   - Check required fields
|   - Verify response exists
|   - Deduplicate
+------------------------+
    |
    v
+------------------------+
| 2. QUALITY WEIGHTING   |
|   - Apply temporal decay
|   - Weight by type
|   - Adjust for context
+------------------------+
    |
    v
+------------------------+
| 3. FORMAT CONVERSION   |
|   - Map to training format
|   - Extract signals
+------------------------+
    |
    v
+------------------------+
| 4. MERGE WITH          |
|    DISTILLATION        |
|   - Combine with Claude
|   - Cross-reference
+------------------------+
    |
    v
+------------------------+
| 5. EXPORT              |
|   - Write JSONL
|   - Update processed flag
+------------------------+
```

### Training Format Mapping

| Feedback Type | Training Format | Output |
|--------------|-----------------|--------|
| Rating (+1) | instruction | `{instruction, input, output}` - positive example |
| Rating (-1) | excluded | Not used directly (may trigger correction request) |
| Correction | correction | `{instruction, input, output, error_type}` |
| Preference | preference | `{prompt, chosen, rejected}` (DPO format) |
| Flag | excluded | Logged for analysis, not for training |

### Instruction Format (from positive ratings)

```json
{
  "instruction": "How do I reverse a list in Python?",
  "input": "",
  "output": "You can use list[::-1] to reverse a list...",
  "source": "feedback_positive",
  "quality_weight": 0.7,
  "domain": "code"
}
```

### Correction Format

```json
{
  "instruction": "SAM said: 'You can use list[::-1] to reverse a list.'\n\nWhat was the issue and how should it be corrected?",
  "input": "How do I reverse a list in Python?",
  "output": "The issue was: Only mentioned one method, didn't explain the difference.\n\nCorrected answer: Actually, list.reverse() modifies in-place while list[::-1] creates a new list. You should mention both options.",
  "error_type": "incomplete",
  "source": "feedback_correction",
  "quality_weight": 0.95,
  "domain": "code"
}
```

### Preference Format (DPO)

```json
{
  "prompt": "How do I reverse a list in Python?",
  "chosen": "There are two main ways to reverse a list:\n1. `list[::-1]` - creates a new reversed list\n2. `list.reverse()` - reverses in-place\n\nChoose based on whether you need the original list preserved.",
  "rejected": "You can use list[::-1] to reverse a list.",
  "source": "feedback_preference",
  "quality_weight": 0.85,
  "domain": "code"
}
```

---

## Quality Weighting Algorithm

### Weight Calculation

```python
def calculate_feedback_weight(
    feedback: FeedbackEntry,
    current_time: float
) -> float:
    """
    Calculate training weight for a feedback entry.

    Weights range from 0.0 to 1.0:
    - Higher = more influence in training
    - Corrections weighted highest
    - Recent feedback weighted higher than old
    """
    weight = 0.5  # Base weight

    # ===== FEEDBACK TYPE WEIGHTS =====

    type_weights = {
        'correction': 0.3,     # Corrections are most valuable
        'preference': 0.2,     # Preferences are very valuable
        'rating': 0.1,         # Ratings provide signal
        'flag': 0.0,           # Flags are for analysis, not training
    }
    weight += type_weights.get(feedback.feedback_type, 0.0)

    # ===== TEMPORAL DECAY =====

    # Recent feedback is more relevant than old feedback
    age_hours = (current_time - feedback.timestamp) / 3600

    # Half-life of 30 days (720 hours)
    half_life_hours = 720
    decay = 0.5 ** (age_hours / half_life_hours)

    # Apply decay as a multiplier (range: 0.5 to 1.0)
    temporal_factor = 0.5 + (0.5 * decay)
    weight *= temporal_factor

    # ===== CORRECTION QUALITY BONUSES =====

    if feedback.feedback_type == 'correction':
        # Bonus for detailed explanation
        if feedback.what_was_wrong and len(feedback.what_was_wrong) > 50:
            weight += 0.05

        # Bonus for substantial correction
        if feedback.correction and len(feedback.correction) > 100:
            weight += 0.05

        # Bonus for full replacement (complete answer)
        if feedback.correction_type == 'full_replacement':
            weight += 0.05

    # ===== PREFERENCE QUALITY BONUSES =====

    if feedback.feedback_type == 'preference':
        # Bonus for explaining why preferred
        if feedback.comparison_basis and len(feedback.comparison_basis) > 30:
            weight += 0.05

    # ===== CONTEXT BONUSES =====

    # Bonus if this was a Claude-escalated response
    # (Feedback on Claude responses validates distillation)
    if feedback.escalated_to_claude:
        weight += 0.05

    # Bonus for high-confidence responses that got negative feedback
    # (Overconfident mistakes are important to learn)
    if (feedback.response_confidence and
        feedback.response_confidence > 0.8 and
        feedback.rating == -1):
        weight += 0.1

    # ===== CLAMP TO VALID RANGE =====

    return max(0.0, min(1.0, weight))
```

### Weight Interpretation

| Weight Range | Interpretation | Usage |
|-------------|----------------|-------|
| 0.9 - 1.0 | Premium quality | Always include, high sampling weight |
| 0.7 - 0.9 | High quality | Include in training |
| 0.5 - 0.7 | Standard quality | Include with standard weight |
| 0.3 - 0.5 | Low quality | Consider for augmentation only |
| 0.0 - 0.3 | Very low quality | Exclude from training |

---

## Integration Points

### 1. SAM API Integration

The feedback system integrates with `sam_api.py`:

```
POST /api/feedback          - Submit feedback
GET  /api/feedback/stats    - Get feedback statistics
GET  /api/feedback/{id}     - Get specific feedback
GET  /api/feedback/session/{session_id} - Get session feedback
POST /api/feedback/batch    - Submit batch feedback
```

### 2. Distillation Pipeline Integration

Feedback connects to `knowledge_distillation.py`:

```python
# In knowledge_distillation.py
class DistillationDB:
    def merge_feedback(self, feedback_db: "FeedbackDB"):
        """
        Merge feedback data into distillation pipeline.

        - Corrections become error_correction examples
        - Preferences become preference_pairs
        - Ratings validate existing examples
        """
        pass

    def export_with_feedback(
        self,
        output_path: Path,
        include_feedback: bool = True
    ) -> int:
        """Export training data including feedback-derived examples."""
        pass
```

### 3. Response Tracking

Every SAM response needs a trackable ID:

```python
# In orchestrator.py or response generation
def generate_response(query: str, session_id: str) -> dict:
    response_id = generate_response_id()  # SHA256(query + timestamp)[:16]

    response = {
        "response_id": response_id,
        "session_id": session_id,
        "query": query,
        "response": generated_text,
        "timestamp": time.time(),
        "confidence": model_confidence,
        "escalated": was_escalated
    }

    # Store for feedback linking
    store_response_for_feedback(response)

    return response
```

### 4. Real-time Feedback Processing

```python
# Feedback webhook for immediate processing
async def on_feedback_received(feedback: FeedbackEntry):
    """Process feedback as it arrives."""

    # 1. Store feedback
    feedback_db.save(feedback)

    # 2. Update aggregates
    feedback_db.update_aggregates(feedback.response_id)

    # 3. If correction, immediately queue for training review
    if feedback.feedback_type == "correction":
        distillation_db.queue_for_review(
            source="user_correction",
            query=feedback.original_query,
            response=feedback.original_response,
            correction=feedback.correction,
            priority=8  # High priority
        )

    # 4. If flag, log for safety review
    if feedback.feedback_type == "flag" and feedback.flag_type == "harmful":
        safety_log.record(feedback)
```

---

## API Endpoints

### POST /api/feedback

Submit feedback for a response.

**Request:**
```json
{
  "response_id": "resp_abc123",
  "session_id": "sess_xyz789",
  "feedback_type": "rating",
  "rating": 1
}
```

**Response:**
```json
{
  "success": true,
  "feedback_id": "fb_def456",
  "message": "Feedback recorded"
}
```

### POST /api/feedback (with correction)

**Request:**
```json
{
  "response_id": "resp_abc123",
  "session_id": "sess_xyz789",
  "feedback_type": "correction",
  "correction": "The correct answer is...",
  "correction_type": "full_replacement",
  "what_was_wrong": "The original response was incomplete because..."
}
```

### GET /api/feedback/stats

Get feedback statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_feedback": 1234,
    "by_type": {
      "rating": 1000,
      "correction": 150,
      "preference": 50,
      "flag": 34
    },
    "sentiment": {
      "positive": 750,
      "negative": 250,
      "net_sentiment": 0.5
    },
    "processed": {
      "total": 1100,
      "pending": 134
    },
    "quality": {
      "avg_weight": 0.65,
      "high_quality_count": 450
    },
    "recent_24h": 45
  }
}
```

### GET /api/feedback/session/{session_id}

Get all feedback for a session.

**Response:**
```json
{
  "success": true,
  "session_id": "sess_xyz789",
  "feedback": [
    {
      "feedback_id": "fb_001",
      "response_id": "resp_abc123",
      "feedback_type": "rating",
      "rating": 1,
      "timestamp": 1737745822.0
    },
    {
      "feedback_id": "fb_002",
      "response_id": "resp_def456",
      "feedback_type": "correction",
      "correction": "...",
      "timestamp": 1737745900.0
    }
  ],
  "session_quality": 0.75
}
```

---

## Implementation Notes

### Storage Location

Following the existing storage strategy:

```python
# Primary storage (external drive)
EXTERNAL_FEEDBACK_PATH = Path("/Volumes/David External/sam_training/distilled/feedback.db")

# Fallback (local)
LOCAL_FEEDBACK_PATH = Path.home() / ".sam" / "feedback.db"

def get_feedback_db_path() -> Path:
    """Get feedback database path, preferring external drive."""
    if Path("/Volumes/David External").exists():
        EXTERNAL_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_FEEDBACK_PATH
    return LOCAL_FEEDBACK_PATH
```

### Database Initialization

```python
class FeedbackDB:
    """SQLite database for feedback storage."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_feedback_db_path()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(FEEDBACK_SCHEMA)  # SQL from schema section
```

### Response ID Generation

```python
def generate_response_id(query: str, timestamp: float) -> str:
    """Generate unique response ID."""
    content = f"{query}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

### Session ID Management

```python
def get_or_create_session_id() -> str:
    """Get current session ID or create new one."""
    # Session persists across conversation until:
    # - User explicitly ends it
    # - 30 minutes of inactivity
    # - Application restart
    pass
```

---

## Examples

### Example 1: Simple Thumbs Up

User liked a response - becomes positive training example.

```python
feedback = FeedbackEntry(
    feedback_id="fb_001",
    response_id="resp_abc123",
    session_id="sess_xyz789",
    timestamp=1737745822.0,
    feedback_type="rating",
    rating=1,
    original_query="How do I center a div in CSS?",
    original_response="Use flexbox: display: flex; justify-content: center; align-items: center;",
    domain="code"
)

# Converts to instruction format:
training_example = {
    "instruction": "How do I center a div in CSS?",
    "input": "",
    "output": "Use flexbox: display: flex; justify-content: center; align-items: center;",
    "source": "feedback_positive",
    "quality_weight": 0.6
}
```

### Example 2: User Correction

User corrects an incomplete response - highest value training data.

```python
feedback = FeedbackEntry(
    feedback_id="fb_002",
    response_id="resp_def456",
    session_id="sess_xyz789",
    timestamp=1737745900.0,
    feedback_type="correction",
    correction="There are actually three main methods to center a div:\n1. Flexbox: display: flex; justify-content: center; align-items: center;\n2. Grid: display: grid; place-items: center;\n3. Position absolute with transform: position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);",
    correction_type="full_replacement",
    what_was_wrong="Only mentioned one method when there are several common approaches",
    original_query="How do I center a div in CSS?",
    original_response="Use flexbox: display: flex; justify-content: center; align-items: center;",
    domain="code"
)

# Converts to correction format:
correction_example = {
    "instruction": "SAM said: 'Use flexbox: display: flex; justify-content: center; align-items: center;'\n\nWhat was the issue and how should it be corrected?",
    "input": "How do I center a div in CSS?",
    "output": "The issue was: Only mentioned one method when there are several common approaches.\n\nCorrected answer: There are actually three main methods...",
    "error_type": "incomplete",
    "source": "feedback_correction",
    "quality_weight": 0.95
}
```

### Example 3: Preference Pair

User provides preferred alternative - becomes DPO training pair.

```python
feedback = FeedbackEntry(
    feedback_id="fb_003",
    response_id="resp_ghi789",
    session_id="sess_xyz789",
    timestamp=1737746000.0,
    feedback_type="preference",
    preferred_response="To center a div, I recommend flexbox as the most reliable modern approach:\n\n```css\n.container {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  height: 100vh; /* or specific height */\n}\n```\n\nThis works in all modern browsers and handles both horizontal and vertical centering elegantly.",
    comparison_basis="More practical with a code example and browser compatibility note",
    original_query="How do I center a div in CSS?",
    original_response="Use flexbox with justify-content and align-items set to center.",
    domain="code"
)

# Converts to DPO preference format:
preference_example = {
    "prompt": "How do I center a div in CSS?",
    "chosen": "To center a div, I recommend flexbox as the most reliable modern approach...",
    "rejected": "Use flexbox with justify-content and align-items set to center.",
    "source": "feedback_preference",
    "quality_weight": 0.85
}
```

---

## Related Documentation

- **Distillation System:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/DISTILLATION.md`
- **Data Format Spec:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/DISTILLATION_FORMAT.md`
- **SAM API:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/sam_api.py`
- **Storage Strategy:** `/Volumes/Plex/SSOT/STORAGE_STRATEGY.md`

---

## Implementation Checklist

- [ ] Create `FeedbackDB` class with SQLite schema
- [ ] Define `FeedbackEntry` and related dataclasses
- [ ] Implement `calculate_feedback_weight()` algorithm
- [ ] Add response ID generation to orchestrator
- [ ] Add session ID management
- [ ] Create API endpoints in `sam_api.py`
- [ ] Implement feedback-to-training conversion
- [ ] Integrate with `DistillationDB` for merged exports
- [ ] Add CLI commands for feedback management
- [ ] Create feedback statistics dashboard
- [ ] Add unit tests for weight calculation
- [ ] Test end-to-end feedback flow

---

## Next Phase Tasks

This design document enables:
- **Phase 1.2.2:** Implement `FeedbackDB` class
- **Phase 1.2.3:** Add feedback API endpoints
- **Phase 1.2.4:** Build feedback-to-training pipeline
- **Phase 1.2.5:** Create feedback CLI tools
- **Phase 1.2.6:** Integrate with distillation exports

---

*This specification defines the feedback data model for SAM Phase 1.2. The feedback system complements distillation by capturing user signals about response quality, converting them into high-value training data.*
