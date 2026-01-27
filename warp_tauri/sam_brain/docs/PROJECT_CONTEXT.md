# SAM Project Context System

*Phase 2.1.11 - Complete Documentation*
*Version: 1.0.0 | Created: 2026-01-24*

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Components](#components)
   - [ProjectDetector](#projectdetector)
   - [ProjectProfileLoader](#projectprofileloader)
   - [ProjectWatcher](#projectwatcher)
   - [SessionState](#sessionstate)
   - [Recall System](#recall-system)
4. [SSOT Integration](#ssot-integration)
5. [Session Persistence](#session-persistence)
6. [CLI Commands](#cli-commands)
7. [API Endpoints](#api-endpoints)
8. [Integration with Orchestrator](#integration-with-orchestrator)
9. [Troubleshooting](#troubleshooting)
10. [Configuration Reference](#configuration-reference)

---

## Overview

### Purpose

The Project Context System enables SAM to understand **what the user is currently working on**. This awareness allows SAM to:

- **Provide continuity** - Resume conversations without re-explaining context
- **Tailor responses** - Adapt to the project's tech stack and conventions
- **Surface relevant info** - Show TODOs, blockers, and session history
- **Remember across sessions** - Track what happened last time

### Design Philosophy

1. **Lightweight Detection** - Quick path-based detection without heavy parsing
2. **SSOT-First** - Known projects from the registry get priority
3. **Layered Recall** - Combines detection, profiles, and session history
4. **Token-Efficient** - Context injection stays under 200 tokens
5. **Zero Configuration** - Works out of the box from any project directory

### Key Files

| File | Purpose |
|------|---------|
| `project_context.py` | Main module with all components |
| `project_scanner.py` | Discovers projects across drives |
| `project_manager.py` | Organizes and searches projects |
| `docs/PROJECT_CONTEXT_FORMAT.md` | Format specification for context injection |

### Related Systems

| System | Relationship |
|--------|--------------|
| Fact Memory | USER facts complement PROJECT context |
| Semantic Memory | Stores project-related interactions |
| Orchestrator | Consumes project context for routing |
| SSOT | Source of truth for project registry |

---

## Architecture Diagram

```
                              +------------------+
                              |    User Input    |
                              +--------+---------+
                                       |
                                       v
+------------------+           +-------+--------+           +------------------+
|                  |           |                |           |                  |
|  ProjectDetector +---------->+   Orchestrator +---------->+  MLX Cognitive   |
|                  |           |                |           |                  |
+--------+---------+           +-------+--------+           +------------------+
         |                             |
         |                             |
         v                             v
+--------+---------+           +-------+--------+
|                  |           |                |
| ProjectProfile   |           |  Context       |
| Loader           +---------->+  Builder       |
|                  |           |                |
+--------+---------+           +-------+--------+
         |                             |
         |                             |
         v                             v
+--------+---------+           +-------+--------+
|                  |           |                |
|  SSOT Markdown   |           |  Prompt with   |
|  Files           |           |  PROJECT Tag   |
|                  |           |                |
+------------------+           +----------------+


    +----------------+        +----------------+        +----------------+
    |                |        |                |        |                |
    | ProjectWatcher +------->+ SessionState   +------->+ SQLite DB      |
    | (Background)   |        | Manager        |        | (External)     |
    |                |        |                |        |                |
    +----------------+        +----------------+        +----------------+


                         DATA FLOW
    +------------------------------------------------------------+
    |                                                            |
    |  1. Detect project from cwd or file path                   |
    |  2. Load SSOT profile if available                         |
    |  3. Retrieve last session state                            |
    |  4. Build context string (<PROJECT> tag)                   |
    |  5. Inject into prompt alongside USER facts                |
    |  6. Track session for next time                            |
    |                                                            |
    +------------------------------------------------------------+
```

---

## Components

### ProjectDetector

**Purpose**: Quickly identify which project a path belongs to.

**Location**: `project_context.py` line ~300

**How It Works**:

1. Check against known SSOT projects (sorted by path length, longest first)
2. Walk up directory tree looking for project markers
3. Return `ProjectInfo` dataclass with detected details

**Project Markers Recognized**:

| Marker | Language |
|--------|----------|
| `Cargo.toml` | Rust |
| `package.json` | JavaScript/TypeScript |
| `pyproject.toml` | Python |
| `setup.py` | Python |
| `requirements.txt` | Python |
| `go.mod` | Go |
| `Package.swift` | Swift |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `build.gradle` | Java |
| `CMakeLists.txt` | C++ |
| `CLAUDE.md` | Claude/SAM project |
| `.git` | Generic (any) |

**Usage**:

```python
from project_context import ProjectDetector, get_current_project

# Create detector instance
detector = ProjectDetector()

# Detect from current working directory
project = detector.detect()

# Detect from specific path
project = detector.detect("/Users/david/Projects/my-app")

# Or use convenience function
project = get_current_project()

if project:
    print(f"Project: {project.name}")
    print(f"Type: {project.type}")
    print(f"Language: {project.language}")
    print(f"Is SSOT registered: {project.is_known}")
```

**ProjectInfo Dataclass**:

```python
@dataclass
class ProjectInfo:
    name: str              # Display name (e.g., "SAM Brain")
    type: str              # Project type (e.g., "python", "rust")
    root_path: str         # Absolute path to project root
    language: str          # Primary language
    status: str            # "active", "detected", "idle", etc.
    tier: int = 0          # SSOT tier (1-8, 0 if not registered)
    is_known: bool = False # True if in SSOT registry
    markers_found: List[str] = []  # Which markers were found
```

**Known SSOT Projects**:

The detector knows about these projects from the registry:

| Path | Name | Tier |
|------|------|------|
| `~/ReverseLab/SAM/warp_tauri` | SAM Terminal | 1 |
| `~/ReverseLab/SAM/warp_tauri/sam_brain` | SAM Brain | 1 |
| `~/ReverseLab/SAM/warp_core` | Warp Core | 1 |
| `/Volumes/Plex/SSOT` | SSOT System | 1 |
| `~/Projects/RVC` | RVC Voice Training | 2 |
| `~/ai-studio/ComfyUI` | ComfyUI/LoRA | 2 |
| `~/Projects/character-pipeline` | Character Pipeline | 5 |
| And more... | | |

---

### ProjectProfileLoader

**Purpose**: Load rich project profiles from SSOT markdown files.

**Location**: `project_context.py` line ~500+

**SSOT Path**: `/Volumes/Plex/SSOT/projects/`

**How It Works**:

1. Scans SSOT projects directory for `.md` files
2. Parses markdown to extract structured fields
3. Returns `ProjectProfile` with full metadata

**Usage**:

```python
from project_context import ProjectProfileLoader, get_profile_loader

# Create loader
loader = ProjectProfileLoader()

# Load specific profile by name
profile = loader.load_profile("SAM_TERMINAL")

# Alternative: load by fuzzy match
profile = loader.load_profile("orchestrator")

# Get all profiles
all_profiles = loader.get_all_profiles()

# Generate context string for prompt injection
context = profile.to_context_string()

# Use singleton
loader = get_profile_loader()
```

**ProjectProfile Fields**:

```python
@dataclass
class ProjectProfile:
    name: str                    # Project name
    file_path: str               # Path to markdown file
    description: str             # Brief description
    status: str                  # Current status
    tech_stack: List[str]        # Languages and frameworks
    dependencies: List[str]      # Other projects this depends on
    key_files: List[str]         # Important files to know about
    conventions: List[str]       # Coding conventions
    current_focus: str           # What's being worked on now
    blockers: List[str]          # Current blockers
    notes: List[str]             # Freeform notes
    last_updated: datetime       # When profile was last modified
```

**Markdown Format Expected**:

```markdown
# Project Name

Brief description here.

## Status
Active - Building core features

## Tech Stack
- Python 3.11
- MLX
- SQLite

## Dependencies
- SSOT System
- Semantic Memory

## Key Files
- orchestrator.py
- sam_api.py
- cognitive/mlx_cognitive.py

## Current Focus
Working on project context injection

## Blockers
- Need more external drive space

## Notes
- Use MLX not Ollama
- Keep responses concise
```

---

### ProjectWatcher

**Purpose**: Monitor for project switches in real-time.

**Location**: `project_context.py` line ~700+

**How It Works**:

1. Polls current working directory at configurable interval
2. Detects when project changes
3. Fires callbacks when switch occurs
4. Optionally loads new project's profile

**Usage**:

```python
from project_context import ProjectWatcher, get_project_watcher

# Create watcher with custom interval
watcher = ProjectWatcher(poll_interval=5.0)

# Define callback
def on_project_switch(old_project, new_project, profile):
    if new_project:
        print(f"Switched to: {new_project.name}")
        if profile:
            print(f"Status: {profile.status}")
            print(f"Focus: {profile.current_focus}")
    else:
        print("Left project directory")

# Register callback
watcher.on_project_change(on_project_switch)

# Start watching
watcher.start()

# Later: stop
watcher.stop()

# Or use context manager
with ProjectWatcher(poll_interval=3.0) as watcher:
    watcher.on_project_change(on_project_switch)
    # ... do work ...

# Singleton with auto-start
watcher = get_project_watcher(auto_start=True)
```

**Callback Signature**:

```python
def callback(
    old_project: Optional[ProjectInfo],  # Previous project (None if none)
    new_project: Optional[ProjectInfo],  # New project (None if left all projects)
    profile: Optional[ProjectProfile]    # SSOT profile if available
) -> None:
    pass
```

**Thread Safety**:

- Watcher runs in background thread
- Callbacks execute in watcher thread
- Use thread-safe structures if updating shared state

---

### SessionState

**Purpose**: Persist per-project session information across SAM restarts.

**Location**: `project_context.py` line ~900+

**Storage**: `/Volumes/David External/sam_memory/project_context.db`

**Fallback**: `~/.sam/project_context.db`

**How It Works**:

1. SQLite database stores session records per project
2. Each session captures: summary, files touched, TODOs, notes
3. Retrieval returns last session or full history

**Usage**:

```python
from project_context import (
    SessionState, ProjectSessionState, get_session_state
)

# Get singleton
session_state = get_session_state()

# Create a session record
state = SessionState(
    project_name="SAM Brain",
    conversation_summary="Added project context system",
    files_touched=["project_context.py", "docs/PROJECT_CONTEXT.md"],
    todos_added=["Write tests", "Add API endpoints"],
    notes=["Remember: use SQLite not JSON for persistence"]
)

# Save session
session_state.save_session("SAM Brain", state)

# Get last session for a project
last = session_state.get_last_session("SAM Brain")
if last:
    print(f"Last time: {last.conversation_summary}")
    print(f"Files: {last.files_touched}")

# Update files during active session
session_state.update_files_touched("SAM Brain", ["new_module.py"])

# Add notes during session
session_state.add_session_note("SAM Brain", "Edge case: empty projects")

# Get full history
history = session_state.get_session_history("SAM Brain", limit=10)
for session in history:
    print(f"- {session.timestamp}: {session.conversation_summary[:50]}...")
```

**SessionState Dataclass**:

```python
@dataclass
class SessionState:
    project_name: str               # Which project
    conversation_summary: str       # What happened
    files_touched: List[str]        # Files edited/viewed
    todos_added: List[str]          # New TODOs created
    todos_completed: List[str]      # TODOs marked done
    blockers_identified: List[str]  # New blockers found
    notes: List[str]                # Freeform notes
    timestamp: datetime             # When session occurred
    session_id: str                 # Unique identifier
```

**Database Schema**:

```sql
CREATE TABLE IF NOT EXISTS project_sessions (
    session_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    conversation_summary TEXT,
    files_touched TEXT,       -- JSON array
    todos_added TEXT,         -- JSON array
    todos_completed TEXT,     -- JSON array
    blockers_identified TEXT, -- JSON array
    notes TEXT,               -- JSON array
    timestamp TEXT NOT NULL,

    -- Indexes
    FOREIGN KEY (project_name) REFERENCES projects(name)
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON project_sessions(project_name);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON project_sessions(timestamp DESC);
```

---

### Recall System

**Purpose**: Build complete context by combining detection, profiles, and session history.

**Location**: Integrated across components

**How It Works**:

```
                    Recall Pipeline
    +--------------------------------------------------+
    |                                                  |
    |  1. ProjectDetector.detect(cwd)                  |
    |         |                                        |
    |         v                                        |
    |  2. ProjectProfileLoader.load_profile(name)      |
    |         |                                        |
    |         v                                        |
    |  3. SessionState.get_last_session(name)          |
    |         |                                        |
    |         v                                        |
    |  4. build_project_context()                      |
    |         |                                        |
    |         v                                        |
    |  5. <PROJECT> tag for prompt injection           |
    |                                                  |
    +--------------------------------------------------+
```

**Combined Context Building**:

```python
from project_context import (
    get_current_project,
    get_profile_loader,
    get_session_state,
    build_project_context
)

# Step by step
project = get_current_project()
profile = get_profile_loader().load_profile(project.name) if project else None
session = get_session_state().get_last_session(project.name) if project else None

# Or use combined function
context = build_project_context()

# Result is XML-style tag for prompt:
# <PROJECT name="SAM Brain" status="active">
# Last session (2 hours ago): Implemented context injection.
# TODOs:
# - Finish documentation
# - Add CLI commands
# Recent: project_context.py, orchestrator.py
# Stack: Python, MLX, SQLite
# </PROJECT>
```

---

## SSOT Integration

### Project Registry Location

**Path**: `/Volumes/Plex/SSOT/PROJECT_REGISTRY.md`

This master document defines all known projects with:
- Name and description
- Path on disk
- Tier (priority level 1-8)
- Status (active, idle, planned, etc.)
- Related projects

### Project Documentation Location

**Path**: `/Volumes/Plex/SSOT/projects/*.md`

Each project has a dedicated markdown file:

| File | Project |
|------|---------|
| `SAM_TERMINAL.md` | SAM Terminal (warp_tauri) |
| `ORCHESTRATOR.md` | Orchestrator system |
| `RVC_VOICE_TRAINING.md` | Voice cloning |
| `CHARACTER_PIPELINE.md` | Daz-to-Unity pipeline |
| `COMFYUI_LORA.md` | Image generation |
| `MOTION_PIPELINE.md` | Motion extraction |
| `SSOT_SYSTEM.md` | This documentation system |

### Synchronization

The project context system reads from SSOT but does not write to it:

```
SSOT (read-only)                    Project Context (read-write)
+------------------+                +------------------+
| PROJECT_REGISTRY | <--- reads --- | ProjectDetector  |
+------------------+                +------------------+
        |
        v
+------------------+                +------------------+
| projects/*.md    | <--- reads --- | ProfileLoader    |
+------------------+                +------------------+
```

Updates to SSOT should be done manually or via dedicated SSOT tooling.

### Adding New Projects to SSOT

1. Add entry to `PROJECT_REGISTRY.md`
2. Create `/Volumes/Plex/SSOT/projects/PROJECT_NAME.md`
3. Add path mapping to `SSOT_PROJECTS` dict in `project_context.py`

---

## Session Persistence

### Storage Strategy

**Primary Location**: `/Volumes/David External/sam_memory/project_context.db`

**Rationale**:
- External drive has more space
- Same location as facts.db and semantic memory
- Survives internal drive issues

**Fallback**: `~/.sam/project_context.db`

Used when external drive is not mounted.

### Automatic Session Capture

Sessions are captured when:

1. SAM conversation ends
2. Project switch detected
3. Explicit save via API
4. SAM daemon periodic checkpoint

### Session Data Retention

| Data Type | Retention |
|-----------|-----------|
| Recent sessions | Keep 10 per project |
| Old sessions | Summarize and archive after 30 days |
| Deleted projects | Keep 90 days then purge |

### Session Recovery

If SAM crashes mid-session:

```python
# On next startup, check for incomplete session
session_state = get_session_state()
incomplete = session_state.get_incomplete_sessions()

for session in incomplete:
    # Mark as interrupted
    session_state.mark_session_interrupted(session.session_id)
```

---

## CLI Commands

### Detection Commands

```bash
# Detect project in current directory
python project_context.py detect

# Detect from specific path
python project_context.py detect /Users/david/Projects/my-app

# Output as JSON
python project_context.py detect . --json

# List all known SSOT projects
python project_context.py list
```

### Profile Commands

```bash
# Load specific profile
python project_context.py profile SAM_TERMINAL

# Output as JSON
python project_context.py profile SAM_TERMINAL --json

# List all profiles
python project_context.py profiles

# List as JSON
python project_context.py profiles --json
```

### Watcher Commands

```bash
# Start watching for project switches
python project_context.py watch

# Custom poll interval (seconds)
python project_context.py watch --interval 3

# Verbose output
python project_context.py watch --verbose
```

### Session Commands

```bash
# Show last session for current project
python project_context.py session

# Show last session for specific project
python project_context.py session "SAM Brain"

# Show session history
python project_context.py history "SAM Brain" --limit 5

# Add session note
python project_context.py note "SAM Brain" "Remember edge cases"
```

### Context Commands

```bash
# Build full context for current project
python project_context.py context

# Build context with specific max tokens
python project_context.py context --max-tokens 150

# Output raw XML
python project_context.py context --raw
```

---

## API Endpoints

### HTTP API (via sam_api.py server)

#### GET /api/project

Returns current project information.

**Request**:
```http
GET /api/project HTTP/1.1
```

**Response**:
```json
{
  "success": true,
  "project": {
    "name": "SAM Brain",
    "type": "python",
    "root_path": "/Users/david/ReverseLab/SAM/warp_tauri/sam_brain",
    "language": "python",
    "status": "active",
    "tier": 1,
    "is_known": true
  }
}
```

#### GET /api/project/profile

Returns SSOT profile for current or specified project.

**Request**:
```http
GET /api/project/profile?name=SAM_TERMINAL HTTP/1.1
```

**Response**:
```json
{
  "success": true,
  "profile": {
    "name": "SAM Terminal",
    "description": "Tauri-based terminal application",
    "status": "active",
    "tech_stack": ["Rust", "TypeScript", "Tauri"],
    "current_focus": "Project context integration",
    "blockers": []
  }
}
```

#### GET /api/project/session

Returns last session for project.

**Request**:
```http
GET /api/project/session?name=SAM%20Brain HTTP/1.1
```

**Response**:
```json
{
  "success": true,
  "session": {
    "project_name": "SAM Brain",
    "conversation_summary": "Added project context system",
    "files_touched": ["project_context.py"],
    "todos_added": ["Write tests"],
    "timestamp": "2026-01-24T18:30:00"
  }
}
```

#### POST /api/project/session

Save a session.

**Request**:
```http
POST /api/project/session HTTP/1.1
Content-Type: application/json

{
  "project_name": "SAM Brain",
  "conversation_summary": "Implemented new feature",
  "files_touched": ["module.py", "test_module.py"],
  "todos_added": ["Update docs"]
}
```

**Response**:
```json
{
  "success": true,
  "session_id": "sess_abc123"
}
```

#### GET /api/project/context

Returns full context string for prompt injection.

**Request**:
```http
GET /api/project/context?max_tokens=150 HTTP/1.1
```

**Response**:
```json
{
  "success": true,
  "context": "<PROJECT name=\"SAM Brain\" status=\"active\">\nLast session: Added context system.\nTODOs:\n- Write tests\nStack: Python, MLX\n</PROJECT>",
  "token_estimate": 45
}
```

### Python API

```python
from sam_api import (
    api_project_detect,
    api_project_profile,
    api_project_session,
    api_project_context
)

# Detection
result = api_project_detect("/path/to/check")

# Profile loading
result = api_project_profile("SAM_TERMINAL")

# Session management
result = api_project_session("SAM Brain")

# Context building
result = api_project_context(max_tokens=150)
```

---

## Integration with Orchestrator

### Context Injection Flow

```python
# In orchestrator.py orchestrate() function:

def orchestrate(message: str, privacy_level: str = "full") -> dict:
    # ... existing code ...

    # Phase 2.1: Add project context
    project_context = build_project_context()

    # Combine with USER facts
    full_context = build_full_context(
        user_id="david",
        project_context=project_context
    )

    # Inject into prompt
    prompt = f"""
{full_context}

User: {message}

SAM:"""

    # ... continue with generation ...
```

### Route-Specific Context

Different routes may use context differently:

| Route | Context Usage |
|-------|---------------|
| CHAT | Full context for conversation |
| CODE | Emphasize tech stack and recent files |
| PROJECT | Use current_focus and blockers |
| IMPROVE | Use TODOs and session history |

### Context Priority

When building prompts with limited tokens:

1. **P0** - Project name and status (always included)
2. **P1** - Last session summary
3. **P2** - Active TODOs
4. **P3** - Recent files
5. **P4** - Tech stack
6. **P5** - Blockers and notes

See `PROJECT_CONTEXT_FORMAT.md` for detailed truncation rules.

---

## Troubleshooting

### Common Issues

#### Project Not Detected

**Symptom**: `detect()` returns `None` when in a project directory.

**Causes**:
1. No project markers in directory tree
2. Path not in SSOT registry

**Solutions**:
```bash
# Check if markers exist
ls -la Cargo.toml package.json pyproject.toml

# Add CLAUDE.md as marker
touch CLAUDE.md

# Or add to SSOT registry in project_context.py
```

#### SSOT Profile Not Loading

**Symptom**: Profile is `None` even for known projects.

**Causes**:
1. External drive not mounted
2. Markdown file doesn't exist
3. Name mismatch

**Solutions**:
```bash
# Check drive is mounted
ls /Volumes/Plex/SSOT/projects/

# List available profiles
python project_context.py profiles

# Check exact name matching
grep -l "SAM" /Volumes/Plex/SSOT/projects/*.md
```

#### Session Not Persisting

**Symptom**: Last session returns `None` even after saving.

**Causes**:
1. Database not initialized
2. External drive unmounted between save and load
3. Project name mismatch

**Solutions**:
```python
# Check database location
from project_context import DB_PATH
print(f"DB at: {DB_PATH}")
print(f"Exists: {DB_PATH.exists()}")

# Force re-initialization
session_state = ProjectSessionState()
session_state._init_db()

# Check for name variations
history = session_state.get_all_projects()
print(f"Known projects: {history}")
```

#### Watcher Not Firing Callbacks

**Symptom**: Project switches aren't detected.

**Causes**:
1. Watcher not started
2. Poll interval too long
3. Exception in callback

**Solutions**:
```python
# Verify watcher is running
watcher = get_project_watcher()
print(f"Running: {watcher.is_running}")

# Reduce poll interval
watcher = ProjectWatcher(poll_interval=1.0)

# Add error handling to callback
def safe_callback(old, new, profile):
    try:
        # ... your code ...
    except Exception as e:
        print(f"Callback error: {e}")
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from project_context import ProjectDetector
detector = ProjectDetector()
project = detector.detect()  # Will show debug info
```

### Database Reset

If data is corrupted:

```python
from project_context import DB_PATH
import os

# Backup existing
if DB_PATH.exists():
    os.rename(DB_PATH, DB_PATH.with_suffix('.db.bak'))

# Re-initialize
from project_context import get_session_state
session_state = get_session_state()  # Creates fresh DB
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAM_PROJECT_DB_PATH` | External drive | Override database location |
| `SAM_SSOT_PATH` | `/Volumes/Plex/SSOT` | SSOT root directory |
| `SAM_POLL_INTERVAL` | `5.0` | Watcher poll interval (seconds) |

### Constants

Located at top of `project_context.py`:

```python
# Storage paths
DB_PATH = Path("/Volumes/David External/sam_memory/project_context.db")
INVENTORY_PATH = Path(".../exhaustive_analysis/master_inventory.json")
SSOT_PROJECTS_PATH = Path("/Volumes/Plex/SSOT/projects/")

# Detection settings
PROJECT_MARKERS = {
    "Cargo.toml": "rust",
    "package.json": "javascript",
    # ... etc ...
}

# Known projects
SSOT_PROJECTS = {
    "~/ReverseLab/SAM/warp_tauri": {...},
    # ... etc ...
}
```

### Token Budgets

From `PROJECT_CONTEXT_FORMAT.md`:

| Component | Tokens | Priority |
|-----------|--------|----------|
| Project Name + Status | 10-15 | P0 |
| Last Session Summary | 40-60 | P1 |
| Active TODOs | 30-50 | P2 |
| Recent Files | 20-30 | P3 |
| Tech Stack | 15-25 | P4 |
| Blockers/Notes | 20-30 | P5 |
| **Total Budget** | **150-200** | - |

---

## Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| PROJECT_CONTEXT_FORMAT.md | `sam_brain/docs/` | XML tag format specification |
| FACT_SCHEMA.md | `sam_brain/docs/` | USER facts that complement project context |
| MEMORY_SYSTEM.md | `sam_brain/docs/` | Overall memory architecture |
| PROJECT_REGISTRY.md | `/Volumes/Plex/SSOT/` | Master project list |
| CLAUDE.md | `sam_brain/` | SAM Brain overview |

---

## Changelog

### v1.0.0 (2026-01-24)
- Initial documentation
- Comprehensive coverage of all components
- Architecture diagrams
- CLI and API reference
- Troubleshooting guide

---

*This documentation is for SAM Phase 2.1.11 - Project Context Documentation.*
*Part of the SAM self-improving AI assistant system.*
