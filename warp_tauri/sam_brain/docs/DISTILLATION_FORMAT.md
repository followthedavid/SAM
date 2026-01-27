# SAM Distillation Data Format Specification
*Task 1.1.3 - Phase 1: Intelligence Core*
*Created: 2026-01-24*

---

## Overview

This document defines the canonical data format for capturing distilled knowledge from Claude escalations. The goal is to capture not just what Claude said, but HOW Claude reasoned, so SAM can learn the underlying patterns.

### Design Principles

1. **Capture the delta** - SAM's attempt vs Claude's response reveals what SAM needs to learn
2. **Extract reasoning** - Chain-of-thought, tool use, and self-correction are the valuable patterns
3. **Quality over quantity** - Better to have 1000 excellent examples than 10000 mediocre ones
4. **Training-ready** - Format must convert cleanly to instruction/DPO/RLHF formats
5. **Human-reviewable** - Must be easy to audit and approve/reject examples

---

## Primary Data Format: DistillationExample

The core record type for all captured escalations.

### Schema (SQLite)

```sql
CREATE TABLE distillation_examples (
    -- Identifiers
    id TEXT PRIMARY KEY,                     -- SHA256(query + timestamp)[:16]
    session_id TEXT,                         -- Links related queries
    created_at REAL NOT NULL,                -- Unix timestamp

    -- The Interaction
    query TEXT NOT NULL,                     -- Original user query
    query_context TEXT,                      -- Conversation history, project context
    sam_attempt TEXT,                        -- SAM's initial response (may be NULL if error)
    sam_confidence REAL,                     -- SAM's reported confidence (0.0-1.0)
    sam_reasoning TEXT,                      -- SAM's chain-of-thought if available
    claude_response TEXT NOT NULL,           -- Claude's response

    -- Extracted Reasoning Patterns
    reasoning_type TEXT NOT NULL,            -- See ReasoningType enum below
    reasoning_steps TEXT,                    -- JSON array of reasoning steps
    tool_usage TEXT,                         -- JSON array of tool calls/patterns
    corrections TEXT,                        -- JSON: what SAM got wrong, how Claude fixed it
    principles TEXT,                         -- JSON array of extracted principles

    -- Classification
    domain TEXT NOT NULL,                    -- 'code', 'reasoning', 'creative', 'factual', 'planning'
    subdomain TEXT,                          -- e.g., 'python', 'architecture', 'debugging'
    task_type TEXT,                          -- e.g., 'implement', 'explain', 'debug', 'refactor'
    complexity INTEGER,                      -- 1-10 scale

    -- Quality Metrics
    quality_score REAL,                      -- 0.0-1.0, automated assessment
    quality_flags TEXT,                      -- JSON array of quality concerns
    human_reviewed INTEGER DEFAULT 0,        -- 0=pending, 1=approved, -1=rejected
    reviewer_notes TEXT,                     -- Human reviewer feedback

    -- Training Metadata
    training_ready INTEGER DEFAULT 0,        -- 1=ready for training export
    training_format TEXT,                    -- 'instruction', 'preference', 'cot', 'correction'
    export_count INTEGER DEFAULT 0,          -- Times exported to training
    last_exported_at REAL                    -- Timestamp of last export
);

-- Indexes for efficient queries
CREATE INDEX idx_domain ON distillation_examples(domain);
CREATE INDEX idx_quality ON distillation_examples(quality_score);
CREATE INDEX idx_training_ready ON distillation_examples(training_ready);
CREATE INDEX idx_created ON distillation_examples(created_at);
CREATE INDEX idx_human_reviewed ON distillation_examples(human_reviewed);
```

### JSON Schema

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DistillationExample",
    "type": "object",
    "required": ["id", "created_at", "query", "claude_response", "reasoning_type", "domain"],
    "properties": {
        "id": {
            "type": "string",
            "description": "Unique identifier (SHA256 hash prefix)"
        },
        "session_id": {
            "type": "string",
            "description": "Groups related queries from same session"
        },
        "created_at": {
            "type": "number",
            "description": "Unix timestamp"
        },
        "query": {
            "type": "string",
            "description": "Original user query"
        },
        "query_context": {
            "type": "string",
            "description": "Conversation history and project context"
        },
        "sam_attempt": {
            "type": ["string", "null"],
            "description": "SAM's initial response before escalation"
        },
        "sam_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "sam_reasoning": {
            "type": ["string", "null"],
            "description": "SAM's internal reasoning if available"
        },
        "claude_response": {
            "type": "string",
            "description": "Claude's full response"
        },
        "reasoning_type": {
            "type": "string",
            "enum": ["chain_of_thought", "tool_use", "correction", "direct", "multi_step", "meta_cognitive"]
        },
        "reasoning_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_num": {"type": "integer"},
                    "action": {"type": "string"},
                    "content": {"type": "string"},
                    "reasoning": {"type": "string"}
                }
            }
        },
        "tool_usage": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "purpose": {"type": "string"},
                    "input_pattern": {"type": "string"},
                    "output_handling": {"type": "string"}
                }
            }
        },
        "corrections": {
            "type": "object",
            "properties": {
                "sam_errors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "error_type": {"type": "string"},
                            "what_sam_said": {"type": "string"},
                            "what_was_wrong": {"type": "string"},
                            "correct_answer": {"type": "string"}
                        }
                    }
                },
                "improvements": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "principles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "principle": {"type": "string"},
                    "context": {"type": "string"},
                    "importance": {"type": "number"}
                }
            }
        },
        "domain": {
            "type": "string",
            "enum": ["code", "reasoning", "creative", "factual", "planning", "analysis"]
        },
        "subdomain": {"type": "string"},
        "task_type": {"type": "string"},
        "complexity": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10
        },
        "quality_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "quality_flags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "human_reviewed": {
            "type": "integer",
            "enum": [-1, 0, 1]
        },
        "reviewer_notes": {"type": "string"},
        "training_ready": {
            "type": "integer",
            "enum": [0, 1]
        },
        "training_format": {
            "type": "string",
            "enum": ["instruction", "preference", "cot", "correction"]
        }
    }
}
```

---

## Reasoning Types

```python
class ReasoningType(Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"   # Step-by-step breakdown
    TOOL_USE = "tool_use"                   # Using tools/functions
    CORRECTION = "correction"               # Fixing SAM's error
    DIRECT = "direct"                       # Straightforward answer
    MULTI_STEP = "multi_step"               # Multiple sub-tasks
    META_COGNITIVE = "meta_cognitive"       # Self-reflection, uncertainty
```

---

## Reasoning Extraction Patterns

### Chain-of-Thought Detection

Look for these patterns in Claude's response:

```python
COT_INDICATORS = [
    r"(?:Let me|I'll|I will) (?:think|work|break|analyze)",
    r"(?:First|Step 1|To start)",
    r"(?:Second|Next|Then|Step 2)",
    r"(?:Third|After that|Step 3)",
    r"(?:Finally|In conclusion|Therefore|So)",
    r"(?:The reason|Because|Since) .* (?:Therefore|So|Thus)",
    r"\d+\.\s+.*\n\d+\.\s+",  # Numbered lists
]
```

### Tool Use Detection

Patterns indicating tool/function usage:

```python
TOOL_INDICATORS = [
    r"```(?:bash|shell|sh)\n",           # Shell commands
    r"```(?:python|py)\n.*(?:import|def|class)",  # Python code
    r"(?:I would|Let me) (?:run|execute|call)",
    r"(?:Using|With) (?:the|this) (?:tool|function|command)",
    r"(?:curl|git|npm|pip|cargo)\s+",    # CLI tools
]
```

### Correction Detection

When Claude fixes SAM's errors:

```python
CORRECTION_INDICATORS = [
    r"(?:Actually|However|But|Although)",
    r"(?:That's not quite|The correct|A better)",
    r"(?:slight|small|minor) (?:issue|error|mistake)",
    r"(?:missed|forgot|overlooked)",
    r"(?:should be|instead of|rather than)",
]
```

---

## Quality Scoring Algorithm

```python
def calculate_quality_score(example: DistillationExample) -> float:
    """
    Score from 0.0 to 1.0 based on learning value.
    Higher scores = more valuable for training.
    """
    score = 0.5  # Base score

    # Positive factors (max +0.4)
    if example.reasoning_steps and len(example.reasoning_steps) >= 2:
        score += 0.1  # Has meaningful reasoning chain
    if example.corrections and example.corrections.get('sam_errors'):
        score += 0.15  # Has explicit correction (very valuable)
    if example.principles and len(example.principles) >= 1:
        score += 0.1  # Extracted principles
    if example.complexity >= 5:
        score += 0.05  # Non-trivial task

    # Negative factors (max -0.4)
    if len(example.claude_response) < 100:
        score -= 0.2  # Too short to be useful
    if example.reasoning_type == ReasoningType.DIRECT:
        score -= 0.1  # No reasoning to learn
    if 'repetition' in (example.quality_flags or []):
        score -= 0.3  # Repetitive content
    if 'incomplete' in (example.quality_flags or []):
        score -= 0.2  # Incomplete answer

    return max(0.0, min(1.0, score))
```

### Quality Flags

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

---

## Training Export Formats

### 1. Instruction Format (Alpaca-style)

For basic instruction following:

```json
{
    "instruction": "How do I implement a binary search in Python?",
    "input": "",
    "output": "Here's a binary search implementation:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```\n\nKey points:\n1. Requires sorted array\n2. O(log n) time complexity\n3. Returns index or -1 if not found"
}
```

### 2. Chain-of-Thought Format

For teaching reasoning:

```json
{
    "instruction": "A farmer has 17 sheep. All but 9 run away. How many are left?",
    "input": "",
    "output": "Let me think through this step by step:\n\n1. The farmer starts with 17 sheep\n2. The phrase \"all but 9\" means \"all except 9\"\n3. So if all but 9 run away, that means 9 sheep stayed\n4. The question asks how many are left, not how many ran away\n\nTherefore, 9 sheep are left."
}
```

### 3. Preference Pair Format (DPO)

For preference learning from corrections:

```json
{
    "prompt": "Explain the difference between let and const in JavaScript",
    "chosen": "In JavaScript:\n\n**let** allows reassignment:\n```js\nlet x = 1;\nx = 2;  // Valid\n```\n\n**const** prevents reassignment:\n```js\nconst y = 1;\ny = 2;  // TypeError!\n```\n\nHowever, const doesn't make objects immutable - you can still modify properties of a const object.",
    "rejected": "let and const are both used for variables. const is for constants that don't change."
}
```

### 4. Correction Format (for error recovery training)

```json
{
    "instruction": "Here's what I said: [SAM's incorrect response]. What should I have said instead?",
    "input": "Original question: What's the time complexity of quicksort?\n\nMy answer: Quicksort is O(n) because it only passes through the array once.",
    "output": "Your answer has an error. Here's what you should have said:\n\nQuicksort has:\n- **Average case**: O(n log n)\n- **Worst case**: O(n^2) - happens with already sorted arrays or bad pivot selection\n- **Best case**: O(n log n)\n\nThe confusion may have come from thinking about a single partition step (which is O(n)), but quicksort requires log n levels of recursion on average."
}
```

---

## Storage Locations

```
/Volumes/David External/sam_training/
    distilled/
        distillation.db           # SQLite database (primary)
        exports/
            instruction_YYYYMMDD.jsonl
            preference_YYYYMMDD.jsonl
            cot_YYYYMMDD.jsonl
            correction_YYYYMMDD.jsonl
        pending_review/
            batch_YYYYMMDD.json   # Awaiting human review
        approved/
            reviewed_YYYYMMDD.jsonl
```

---

## Example: Complete Distillation Record

```json
{
    "id": "a7f3b2c1d4e5f6a8",
    "session_id": "sess_20260124_143022",
    "created_at": 1737745822.0,
    "query": "How do I fix this error: TypeError: Cannot read properties of undefined (reading 'map')",
    "query_context": "User is working on a React component in SAMControlCenter project",
    "sam_attempt": "The error means you're trying to use .map() on undefined. Try adding a check like: if (data) { data.map(...) }",
    "sam_confidence": 0.4,
    "sam_reasoning": null,
    "claude_response": "This error occurs when you try to call .map() on a variable that's undefined. Let me walk through the debugging steps:\n\n1. **Identify the variable**: Look at the line number in the error. What variable is being mapped?\n\n2. **Trace the data flow**: Where does this variable come from? Common sources:\n   - API response that hasn't arrived yet\n   - State that wasn't initialized\n   - Prop that wasn't passed\n\n3. **Add proper guards**: There are several patterns:\n   ```jsx\n   // Optional chaining (cleanest)\n   data?.map(item => ...)\n   \n   // Default value\n   (data || []).map(item => ...)\n   \n   // Early return\n   if (!data) return <Loading />;\n   return data.map(item => ...);\n   ```\n\n4. **Fix the root cause**: The guard is a band-aid. Find why data is undefined:\n   - Initialize state properly: `useState([])`\n   - Check API error handling\n   - Verify prop types\n\nFor React specifically, this often happens with:\n- `useState()` without initial value\n- Async data not handled with loading state\n- Missing null check on optional props",
    "reasoning_type": "chain_of_thought",
    "reasoning_steps": [
        {"step_num": 1, "action": "identify", "content": "Identify the variable causing the error", "reasoning": "Need to locate the problematic code first"},
        {"step_num": 2, "action": "trace", "content": "Trace the data flow to find source", "reasoning": "Understanding origin helps find root cause"},
        {"step_num": 3, "action": "mitigate", "content": "Add guards to prevent error", "reasoning": "Immediate fix while investigating"},
        {"step_num": 4, "action": "fix", "content": "Fix root cause", "reasoning": "Guards are temporary; fix the real issue"}
    ],
    "tool_usage": [],
    "corrections": {
        "sam_errors": [
            {
                "error_type": "incomplete",
                "what_sam_said": "Try adding a check like: if (data) { data.map(...) }",
                "what_was_wrong": "Only addressed immediate symptom, not debugging process or root cause",
                "correct_answer": "Provide systematic debugging approach and multiple solution patterns"
            }
        ],
        "improvements": [
            "Explain WHY the error occurs",
            "Show multiple solution patterns",
            "Address root cause, not just symptom",
            "Provide React-specific context"
        ]
    },
    "principles": [
        {
            "principle": "When debugging, identify the root cause rather than just fixing symptoms",
            "context": "Debugging undefined errors",
            "importance": 0.9
        },
        {
            "principle": "Provide multiple solution patterns so users can choose appropriate one",
            "context": "Code solutions",
            "importance": 0.7
        }
    ],
    "domain": "code",
    "subdomain": "javascript",
    "task_type": "debug",
    "complexity": 5,
    "quality_score": 0.85,
    "quality_flags": [],
    "human_reviewed": 0,
    "reviewer_notes": null,
    "training_ready": 0,
    "training_format": "correction"
}
```

---

## Migration from Current System

The existing `knowledge_distillation.py` has separate tables:
- `chain_of_thought`
- `principles`
- `preference_pairs`
- `skill_templates`
- `raw_interactions`

**Migration strategy:**
1. Keep existing tables for backward compatibility
2. Add new `distillation_examples` table (unified format)
3. Modify `escalation_handler.py` to write to new format
4. Create migration script to convert existing records

---

## Implementation Checklist

- [ ] Create `distillation_examples` table schema
- [ ] Define `DistillationExample` dataclass
- [ ] Implement reasoning extractors (CoT, tool use, correction)
- [ ] Implement quality scoring algorithm
- [ ] Add quality flag detection
- [ ] Create export functions for each training format
- [ ] Build human review CLI/interface
- [ ] Migrate existing data
- [ ] Add unit tests for extractors and scoring

---

## Related Tasks

- **1.1.4**: Implement reasoning pattern extractor
- **1.1.5**: Create distillation storage at defined location
- **1.1.6**: Build quality filter using quality_score
- **1.1.7**: Add distillation stats to /api/self
- **1.1.8**: Create review interface for human_reviewed workflow

---

*This specification is the foundation for SAM's learning from Claude escalations.*
