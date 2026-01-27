# Project Context Format Specification

*Phase 2.1.3 - Project Context Injection Design*
*Version: 1.0.0 | Created: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Token Budget Allocation](#token-budget-allocation)
3. [Project Context Schema](#project-context-schema)
4. [Priority Ordering for Truncation](#priority-ordering-for-truncation)
5. [Prompt Injection Format](#prompt-injection-format)
6. [Example Context Strings](#example-context-strings)
7. [Integration with USER Facts](#integration-with-user-facts)
8. [Implementation Guidelines](#implementation-guidelines)
9. [Testing and Validation](#testing-and-validation)

---

## Overview

### Purpose

Project context injection provides SAM with awareness of what the user is currently working on. This enables:

- **Continuity** - Resume conversations about ongoing work without re-explaining
- **Relevance** - Tailor responses to the active project's tech stack and conventions
- **Proactive Help** - Surface related TODOs, blockers, and session notes
- **Cross-Session Memory** - Remember project state between interactions

### Design Principles

1. **Token Efficiency** - Maximum 150-200 tokens for project context
2. **Priority-Based Truncation** - Critical info survives context limits
3. **Complementary** - Works alongside USER facts, not replacing them
4. **Dynamic** - Updates as the user switches projects
5. **Minimal Noise** - Only include actionable, relevant information

### Relationship to USER Facts

| Context Type | Purpose | Token Budget | Source |
|--------------|---------|--------------|--------|
| USER Facts | Who the user is | ~200-300 tokens | facts.db |
| PROJECT Context | What they're working on | ~150-200 tokens | project_context.db |
| Conversation | Recent messages | Variable | Working memory |

---

## Token Budget Allocation

### Overall Budget: 150-200 Tokens

Breaking down the typical allocation:

| Component | Tokens | Priority | Notes |
|-----------|--------|----------|-------|
| Project Name + Status | 10-15 | P0 | Always included |
| Last Session Summary | 40-60 | P1 | What happened last time |
| Active TODOs | 30-50 | P2 | Current focus items |
| Recent Files | 20-30 | P3 | Context for code questions |
| Tech Stack | 15-25 | P4 | Language/framework hints |
| Blockers/Notes | 20-30 | P5 | Important warnings |

### Token Counting Strategy

```python
# Approximate: 1 token ~ 4 characters for English text
# For code/paths: 1 token ~ 3 characters

def estimate_tokens(text: str) -> int:
    """Rough token estimate for context budgeting."""
    # Adjust for code-heavy content
    if '/' in text or '.' in text:  # Paths, filenames
        return len(text) // 3
    return len(text) // 4
```

### Dynamic Budget Adjustment

When total context exceeds budget:

1. Truncate from lowest priority first (P5 -> P0)
2. Within same priority, prefer recency (newer = keep)
3. Never truncate project name or status

---

## Project Context Schema

### Core Data Structure

```python
@dataclass
class ProjectContext:
    """Context for a single project."""

    # === Identity (P0) ===
    project_id: str              # Unique identifier
    name: str                    # Display name (e.g., "SAM Terminal")
    status: ProjectStatus        # active, paused, blocked, completed

    # === Session Notes (P1) ===
    last_session_summary: str    # What happened last time (1-2 sentences)
    last_session_date: datetime  # When last worked on

    # === TODOs (P2) ===
    active_todos: List[Todo]     # Current focus items (max 3)

    # === Recent Files (P3) ===
    recent_files: List[str]      # Recently edited files (max 5)

    # === Tech Stack (P4) ===
    languages: List[str]         # Primary languages
    frameworks: List[str]        # Key frameworks/libraries

    # === Notes/Blockers (P5) ===
    blockers: List[str]          # Current blockers (max 2)
    notes: List[str]             # Important context notes (max 2)

    # === Metadata ===
    path: str                    # Project root path
    last_updated: datetime       # When context was last refreshed

class ProjectStatus(Enum):
    ACTIVE = "active"           # Currently being worked on
    PAUSED = "paused"           # Temporarily on hold
    BLOCKED = "blocked"         # Waiting on something
    COMPLETED = "completed"     # Finished
    IDLE = "idle"               # Not recently touched

@dataclass
class Todo:
    """A single TODO item."""
    text: str                   # The TODO description
    priority: int               # 1=high, 2=medium, 3=low
    added_date: datetime        # When added
```

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS project_contexts (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idle',

    -- Session info
    last_session_summary TEXT,
    last_session_date TEXT,

    -- JSON arrays
    active_todos TEXT,          -- JSON: [{text, priority, added}]
    recent_files TEXT,          -- JSON: [path1, path2, ...]
    languages TEXT,             -- JSON: ["Python", "Rust"]
    frameworks TEXT,            -- JSON: ["MLX", "Tauri"]
    blockers TEXT,              -- JSON: [blocker1, blocker2]
    notes TEXT,                 -- JSON: [note1, note2]

    -- Metadata
    path TEXT NOT NULL,
    last_updated TEXT NOT NULL,

    CHECK (status IN ('active', 'paused', 'blocked', 'completed', 'idle'))
);

CREATE INDEX IF NOT EXISTS idx_project_status ON project_contexts(status);
CREATE INDEX IF NOT EXISTS idx_project_updated ON project_contexts(last_updated DESC);
```

---

## Priority Ordering for Truncation

### Priority Levels

| Priority | Component | Truncation Strategy | Min Chars |
|----------|-----------|---------------------|-----------|
| P0 | Project Name + Status | Never truncate | Full |
| P1 | Last Session Summary | Truncate to first sentence | 50 |
| P2 | Active TODOs | Reduce to top 1-2 items | 30 |
| P3 | Recent Files | Reduce to basename only | 20 |
| P4 | Tech Stack | Reduce to primary lang only | 10 |
| P5 | Blockers/Notes | Omit entirely if needed | 0 |

### Truncation Algorithm

```python
def truncate_context(context: ProjectContext, max_tokens: int = 175) -> str:
    """Build context string, truncating from lowest priority."""

    # Build full context first
    parts = []

    # P0: Always include (never truncate)
    parts.append(format_header(context))

    # P1-P5: Add progressively, checking budget
    components = [
        (1, format_session_summary(context)),
        (2, format_todos(context)),
        (3, format_recent_files(context)),
        (4, format_tech_stack(context)),
        (5, format_blockers_notes(context)),
    ]

    current_tokens = estimate_tokens(parts[0])

    for priority, text in components:
        if not text:
            continue

        text_tokens = estimate_tokens(text)

        if current_tokens + text_tokens <= max_tokens:
            parts.append(text)
            current_tokens += text_tokens
        else:
            # Try truncated version
            truncated = truncate_component(text, priority, max_tokens - current_tokens)
            if truncated:
                parts.append(truncated)
                current_tokens += estimate_tokens(truncated)
            # If no room, skip this component

    return "\n".join(parts)
```

### Component Truncation Rules

```python
def truncate_component(text: str, priority: int, available_tokens: int) -> Optional[str]:
    """Truncate a component to fit available token budget."""

    if available_tokens < 10:
        return None  # Not worth including

    if priority == 1:  # Session summary
        # Take first sentence only
        sentences = text.split('. ')
        return sentences[0] + ('.' if not sentences[0].endswith('.') else '')

    elif priority == 2:  # TODOs
        # Take highest priority TODO only
        lines = text.strip().split('\n')
        return lines[0] if lines else None

    elif priority == 3:  # Files
        # Just basenames
        lines = text.strip().split('\n')
        truncated = [line.split('/')[-1] for line in lines]
        return '\n'.join(truncated[:2])

    elif priority == 4:  # Tech stack
        # First language only
        if ':' in text:
            langs = text.split(':')[1].strip()
            return f"Stack: {langs.split(',')[0].strip()}"
        return None

    else:  # P5 - blockers/notes
        return None  # Omit entirely
```

---

## Prompt Injection Format

### XML-Style Tags

Project context uses XML-style tags consistent with Claude's expected format:

```xml
<PROJECT name="SAM Terminal" status="active">
Last session (2 days ago): Implemented fact extraction from conversations, started on context injection.
TODOs:
- Finish project context format spec
- Test with MLX orchestrator
Recent: fact_memory.py, unified_orchestrator.py, self_knowledge_handler.py
Stack: Python, Rust | MLX, Tauri
Note: Blocked on external drive space for training data.
</PROJECT>
```

### Minimal Format (Under Budget Pressure)

When heavily truncated:

```xml
<PROJECT name="SAM Terminal" status="active">
Last: Implemented fact extraction. TODO: Finish context spec.
</PROJECT>
```

### No Project Context

When no active project is detected:

```xml
<PROJECT>
No active project detected. Ask what they're working on.
</PROJECT>
```

### Multiple Project Awareness

When user works across projects:

```xml
<PROJECT name="SAM Terminal" status="active" primary="true">
Last: Working on memory system.
TODOs: Finish context injection
</PROJECT>
<PROJECT name="RVC Voice Training" status="paused" secondary="true">
Status: Paused - waiting on more training data.
</PROJECT>
```

---

## Example Context Strings

### Full Context (185 tokens)

```xml
<PROJECT name="SAM Terminal" status="active">
Last session (Jan 23): Implemented fact extraction from conversations. Added decay algorithm with Ebbinghaus curve. Fixed bug where facts weren't persisting to external drive.
TODOs:
- [HIGH] Finish project context format specification
- [MED] Integrate context injection with orchestrator
- [LOW] Add fact visualization to CLI
Recent files:
- sam_brain/fact_memory.py
- sam_brain/cognitive/unified_orchestrator.py
- sam_brain/docs/FACT_SCHEMA.md
Stack: Python, Rust | MLX, Tauri, SQLite
Blocker: Need more disk space on external drive for training data export.
Note: User prefers concise responses - keep code explanations brief.
</PROJECT>
```

### Medium Context (120 tokens)

```xml
<PROJECT name="SAM Terminal" status="active">
Last session: Implemented fact extraction, added decay algorithm.
TODOs:
- Finish project context format specification
- Integrate with orchestrator
Recent: fact_memory.py, unified_orchestrator.py
Stack: Python, Rust
</PROJECT>
```

### Minimal Context (50 tokens)

```xml
<PROJECT name="SAM Terminal" status="active">
Last: Implemented fact extraction. TODO: Finish context spec.
Stack: Python
</PROJECT>
```

### Blocked Project

```xml
<PROJECT name="RVC Voice Training" status="blocked">
Last session (Jan 20): Trained Dustin Steele voice model.
BLOCKED: Waiting for more training audio samples.
Note: Docker required for training - quit after use to save RAM.
</PROJECT>
```

### Completed Project

```xml
<PROJECT name="SlamRush Archive" status="completed">
Completed Jan 15. All 2847 assets downloaded and cataloged.
Archive: /Volumes/David External/SlamRush_Assets/
</PROJECT>
```

---

## Integration with USER Facts

### Combined Context Building

```python
def build_full_context(user_id: str, project_id: Optional[str] = None) -> str:
    """
    Build complete context combining USER facts and PROJECT context.

    Total budget: ~400-500 tokens
    - USER facts: ~200-300 tokens
    - PROJECT context: ~150-200 tokens
    """
    parts = []

    # 1. USER Facts (existing system)
    user_context = build_user_context(user_id, min_confidence=0.5)
    if user_context:
        parts.append(f"<USER id=\"{user_id}\">\n{user_context}\n</USER>")

    # 2. PROJECT Context (new system)
    project_context = build_project_context(project_id or detect_active_project())
    if project_context:
        parts.append(project_context)  # Already formatted with <PROJECT> tags

    return "\n\n".join(parts)
```

### Context Priority When Overlapping

Some information may appear in both USER facts and PROJECT context. Resolution:

| Overlap Type | Resolution | Example |
|--------------|------------|---------|
| Tech skills vs Stack | Both keep - different purposes | "Expert in Python" (user) vs "Stack: Python" (project) |
| Current task | PROJECT wins (more specific) | Project TODOs take precedence |
| Preferences | USER wins (persistent) | "Keep responses concise" |
| Hardware constraints | USER wins (global) | "8GB RAM limit" |

### Complementary Information Flow

```
USER Facts (Who):
- Expert in Python and Rust
- Prefers concise responses
- Has M2 Mac Mini 8GB
- Located in Sydney (AEDT)

PROJECT Context (What):
- Working on SAM Terminal
- Last implemented: fact extraction
- TODO: context injection
- Recent files: fact_memory.py
- Blocked: disk space
```

Together they tell SAM:
1. Who is asking (skills, preferences, constraints)
2. What they're doing (project state, recent work, next steps)

### Avoiding Duplication

```python
def deduplicate_context(user_context: str, project_context: str) -> str:
    """Remove redundant information between contexts."""

    # Extract project name from project context
    project_name_match = re.search(r'name="([^"]+)"', project_context)
    project_name = project_name_match.group(1) if project_name_match else None

    # Remove "working on X" from user facts if project context covers it
    if project_name:
        user_context = re.sub(
            rf'[^.]*working on {re.escape(project_name)}[^.]*\.\s*',
            '',
            user_context,
            flags=re.IGNORECASE
        )

    return user_context.strip()
```

---

## Implementation Guidelines

### 1. Context Detection

```python
def detect_active_project() -> Optional[str]:
    """
    Detect which project the user is currently working on.

    Detection methods (priority order):
    1. Explicit project mention in current message
    2. File path in recent conversation
    3. Most recently updated project context
    4. Project with status='active'
    """
    # Method 1: Check current message for project keywords
    # Method 2: Extract paths from message, map to projects
    # Method 3: Query last_updated from project_contexts
    # Method 4: Query status='active' from project_contexts
    pass
```

### 2. Context Refresh Triggers

Update project context when:

- User mentions working on a specific project
- File paths are discussed (update recent_files)
- TODOs are mentioned or completed
- User explicitly updates status ("I'm done with X")
- New session starts (refresh last_session fields)
- User asks about project status

### 3. Session Summary Generation

```python
def generate_session_summary(messages: List[Message]) -> str:
    """
    Generate a 1-2 sentence summary of what happened in a session.

    Focus on:
    - What was built/implemented
    - What was fixed/resolved
    - What was decided
    """
    # Use MLX to summarize, or extract key action verbs
    # "Implemented X, fixed Y, decided to Z"
    pass
```

### 4. TODO Extraction

```python
# Patterns for extracting TODOs from conversation
TODO_PATTERNS = [
    r"(?:need to|should|must|have to|gotta)\s+(.+?)(?:\.|,|$)",
    r"TODO:\s*(.+?)(?:\n|$)",
    r"next(?:\s+step)?(?:\s+is)?:?\s*(.+?)(?:\.|$)",
    r"let'?s\s+(.+?)(?:\s+next|\.|$)",
]

# Patterns for TODO completion
COMPLETION_PATTERNS = [
    r"(?:done|finished|completed)\s+(?:with\s+)?(.+)",
    r"(?:that'?s|it'?s)\s+(?:done|working|fixed)",
]
```

### 5. Storage Location

```python
# Primary: External drive (with facts.db)
PROJECT_CONTEXT_DB = "/Volumes/David External/sam_memory/project_context.db"

# Fallback: Local
PROJECT_CONTEXT_FALLBACK = "~/.sam/project_context.db"
```

---

## Testing and Validation

### Token Count Validation

```python
def validate_context_tokens(context: str, max_tokens: int = 200) -> bool:
    """Ensure context stays within budget."""
    actual = estimate_tokens(context)
    if actual > max_tokens:
        logging.warning(f"Context over budget: {actual} > {max_tokens}")
        return False
    return True
```

### Test Cases

```python
# Test 1: Full context fits budget
assert estimate_tokens(build_project_context("sam_terminal")) <= 200

# Test 2: Truncation preserves P0
truncated = truncate_context(full_context, max_tokens=50)
assert "SAM Terminal" in truncated
assert "status=" in truncated

# Test 3: Combined context stays reasonable
combined = build_full_context("david", "sam_terminal")
assert estimate_tokens(combined) <= 500

# Test 4: No project returns placeholder
no_project = build_project_context(None)
assert "No active project" in no_project
```

### CLI Testing

```bash
# Preview project context
python project_context.py show sam_terminal

# Show truncated version
python project_context.py show sam_terminal --max-tokens 100

# Show combined USER + PROJECT context
python project_context.py combined david sam_terminal

# Estimate token usage
python project_context.py tokens sam_terminal
```

---

## Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| FACT_SCHEMA.md | `sam_brain/docs/` | USER facts schema |
| MEMORY_SYSTEM.md | `sam_brain/docs/` | Overall memory architecture |
| PROJECT_REGISTRY.md | `/Volumes/Plex/SSOT/` | Master project list |
| CLAUDE.md | `sam_brain/` | SAM Brain overview |

---

## Changelog

### v1.0.0 (2026-01-24)
- Initial specification
- Defined token budget allocation
- Created XML-style prompt format
- Documented integration with USER facts
- Added truncation algorithm

---

*This specification is for SAM Phase 2.1.3 - Project Context Format Design.*
*Implementation will follow in Phase 2.1.4.*
