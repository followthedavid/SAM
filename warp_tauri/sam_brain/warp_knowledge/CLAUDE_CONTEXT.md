# Complete Project Context for Claude Analysis

**Last Updated:** 2026-01-12
**Purpose:** Paste this to Claude for deep analysis of any project

---

## Who I Am

David Quinton - Building a personal AI system called SAM (Self-improving AI companion)

### Constraints
- Mac Mini with 8GB RAM
- Can only run one LLM at a time
- No Warp Terminal subscription anymore
- Use Claude for complex thinking, local LLMs for quick tasks

---

## Current Project State

### SAM System

| Component | Purpose | Status |
|-----------|---------|--------|
| **sam_intelligence.py** | Self-awareness, learning, suggestions | Working |
| **sam_api.py** | HTTP API for GUI (port 8765) | Working |
| **autonomous_daemon.py** | Background improvement worker | Working |
| **evolution_tracker.py** | SQLite project progress database | Working |
| **orchestrator.py** | Routes queries to handlers | Working |
| **semantic_memory.py** | Vector embeddings for context | Working |

### SAM Capabilities
- Tracks 17 projects across multiple drives
- Self-awareness (can explain its own state)
- Learning from feedback (records outcomes)
- Proactive suggestions (notices issues before asked)
- HTTP API ready for GUI

### Warp Replication (warp_core)

| Module | What It Does | Status |
|--------|--------------|--------|
| `pty.rs` | PTY with bidirectional I/O | Done |
| `osc_parser.rs` | OSC 133 block detection | Done |
| `session.rs` | Tab/pane persistence | Done |
| `journal_store.rs` | Action history with undo | Done |
| `fs_ops.rs` | File ops with diff support | Done |
| `cwd_tracker.rs` | Directory sandboxing | Done |
| `napi_bridge.rs` | Node.js bindings | Done |

**Gap:** Frontend not connected. Core works, UI missing.

---

## Historical Context

### From Warp Session (836 AI queries)
Most queries were file operations and FMLA workflow automation.

### FMLA Automation System (Built in Warp)
- Auto-loading context memory into every terminal tab
- LaunchAgent background services
- iCloud backup integration
- Custom aliases and shortcuts

### Key Directories
```
/Users/davidquinton/ReverseLab/SAM/        - Main SAM project
/Users/davidquinton/ReverseLab/SAM/warp_core/  - Rust terminal core
/Users/davidquinton/ReverseLab/SAM/warp_tauri/ - Tauri app
/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/ - Python AI
```

---

## 17 Tracked Projects

| Project | Category | Progress | Priority |
|---------|----------|----------|----------|
| SAM Brain | brain | 60% | Critical |
| Orchestrator | brain | 50% | Critical |
| Warp Tauri | platform | 40% | High |
| RVC Voice | voice | 40% | High |
| ComfyUI/LoRA | visual | 35% | Medium |
| Character Pipeline | visual | 30% | Medium |
| Stash Enhancement | content | 10% | Medium |
| Motion Pipeline | visual | 25% | Medium |
| SSOT System | brain | 45% | High |
| Music Library | content | 20% | Low |
| (+ 7 more) | various | various | various |

---

## What SAM Knows About Itself

```
I'm SAM v0.3.0
Currently at Level 0 (Unknown)

My capabilities:
  - memory (online)
  - evolution (online)
  - detector (needs work)
  - ssot (online)

I'm tracking 17 projects
with 6 pending improvements
and 0 completed.

I've learned from 2 outcomes
with a 100% success rate.

Things I noticed:
  - Stash Enhancement is at 10% - needs attention
  - Apple Ecosystem is at 0% - needs attention
  - Unity Unreal is at 0% - needs attention
```

---

## Common Questions to Ask Claude

### Project Planning
- "Given my 8GB RAM constraint, what's the best approach to [X]?"
- "I have warp_core done but no UI. What's fastest path to usable terminal?"
- "Should I focus on SAM Intelligence or terminal replication?"

### Technical
- "My OSC 133 parser works. How do I render blocks in xterm.js?"
- "How should SAM's learning system weight feedback?"
- "What's the minimal Tauri setup to display a PTY?"

### Architecture
- "Is it better to have SAM as service or embedded?"
- "Should memory be SQLite or vector DB for my use case?"
- "How to structure project scanning without killing performance?"

---

## How to Get More Context

### Read Project Status
```bash
cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain
python sam_api.py self
```

### Get Suggestions
```bash
python sam_api.py suggest 10
```

### Ask SAM
```bash
python sam_api.py think "what should I work on next?"
```

### View Warp Session Data
```bash
cat warp_knowledge/analysis_summary.json
```

---

## Files Claude Should Read First

1. **This file** - Overall context
2. **WARP_REPLICATION_STATUS.md** - Detailed gap analysis
3. **CLAUDE.md** - SAM Brain documentation
4. **evolution_tracker.py** - How projects are tracked
5. **sam_intelligence.py** - SAM's brain

---

## Decision Points Needing Input

1. **Terminal UI:** xterm.js vs custom rendering vs existing terminal + overlay?
2. **SAM Focus:** Full Warp replacement or SAM as standalone assistant?
3. **Learning System:** How aggressive should auto-improvements be?
4. **Memory:** Keep vector embeddings or switch to pure SQLite?

---

## Quick Command Reference

```bash
# SAM Status
./start_sam.sh 0 status

# API Server (for GUI)
./start_sam.sh 8765 api

# Ask SAM
./start_sam.sh 0 think "your question"

# Background daemon
./start_sam.sh 8765 daemon

# All (API + daemon)
./start_sam.sh
```

---

**END OF CONTEXT - Paste above to Claude for analysis**
