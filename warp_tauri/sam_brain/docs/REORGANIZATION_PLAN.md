# SAM Revolutionary Reorganization Plan

**Created:** 2026-01-28
**Goal:** Transform 160 confusing files → ~50 self-documenting modules
**Principle:** Any new developer or AI should understand everything in 5 minutes

---

## The Problem

The current codebase has:
- **7 files named "orchestrator"** doing different things
- **5 separate "learning" systems** that overlap
- **8 "training" modules** with duplicate logic
- **No naming convention** - names describe WHAT code IS, not WHAT it DOES
- **77 files in root** with no organization

**Example of the confusion:**
```
orchestrator.py         ← Routes requests
unified_orchestrator.py ← Manages projects
system_orchestrator.py  ← Controls scrapers
claude_orchestrator.py  ← Task delegation
sam_parity_orchestrator.py ← Version sync
re_orchestrator.py      ← Context enhancement
```

A new person seeing this has NO IDEA what any of these do.

---

## The Solution: Self-Documenting Architecture

### Naming Principles

1. **Files named for WHAT THEY DO, not what they are**
   - `speak.py` not `voice_output.py`
   - `remember.py` not `semantic_memory.py`
   - `from_claude.py` not `knowledge_distillation.py`

2. **Packages named for CAPABILITIES**
   - `voice/` - Speak and listen
   - `vision/` - See and understand images
   - `memory/` - Remember and recall
   - `learn/` - Self-improvement
   - `execute/` - Do things safely

3. **Every folder has a README explaining WHY**

---

## Target Architecture

```
sam/
├── README.md                    # 5-minute overview
├── sam.py                       # THE entry point
├── ARCHITECTURE.md              # Visual diagrams
│
├── core/                        # THE BRAIN
│   ├── README.md               # "How SAM thinks and routes"
│   ├── brain.py                # Central router (was: orchestrator.py)
│   ├── config.py               # All configuration
│   └── identity.py             # SAM's personality
│
├── think/                       # LLM INFERENCE
│   ├── README.md               # "How SAM generates responses"
│   ├── mlx.py                  # Local MLX inference
│   ├── escalate.py             # When to ask Claude
│   ├── select_model.py         # 1.5B vs 3B
│   └── validate.py             # Response quality checks
│
├── speak/                       # VOICE OUTPUT
│   ├── README.md               # "How SAM talks"
│   ├── tts.py                  # Text to speech
│   ├── rvc.py                  # Voice cloning
│   └── emotion.py              # Emotional speech
│
├── listen/                      # VOICE INPUT
│   ├── README.md               # "How SAM hears"
│   ├── stt.py                  # Speech to text
│   └── emotion_detect.py       # Detect emotion from voice
│
├── see/                         # VISION
│   ├── README.md               # "How SAM sees"
│   ├── ocr.py                  # Apple Vision OCR
│   ├── describe.py             # VLM descriptions
│   └── ui_state.py             # Read macOS UI
│
├── remember/                    # MEMORY
│   ├── README.md               # "How SAM remembers"
│   ├── facts.py                # User facts & preferences
│   ├── conversations.py        # Chat history
│   ├── embeddings.py           # Semantic search
│   └── projects.py             # Project context
│
├── do/                          # EXECUTION
│   ├── README.md               # "How SAM takes action"
│   ├── run.py                  # Safe command execution
│   ├── classify.py             # Is this safe?
│   ├── approve.py              # Approval queue
│   └── history.py              # Audit trail
│
├── learn/                       # SELF-IMPROVEMENT
│   ├── README.md               # "How SAM gets smarter"
│   ├── from_claude.py          # Learn from Claude sessions
│   ├── from_feedback.py        # Learn from corrections
│   ├── curriculum.py           # Learning priorities
│   └── train.py                # Fine-tuning
│
├── projects/                    # PROJECT AWARENESS
│   ├── README.md               # "How SAM understands your work"
│   ├── registry.py             # All 20+ projects
│   ├── search_code.py          # Find code entities
│   └── permissions.py          # What SAM can do where
│
├── serve/                       # EXTERNAL INTERFACES
│   ├── README.md               # "How to interact with SAM"
│   ├── http.py                 # REST API (port 8765)
│   ├── cli.py                  # Command line
│   └── daemon.py               # Background services
│
└── utils/                       # HELPERS
    ├── audio.py                # Audio utilities
    ├── image.py                # Image utilities
    ├── paths.py                # Path resolution
    └── resources.py            # RAM monitoring
```

---

## Migration Map: Old → New

### Core Routing (7 → 1)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `orchestrator.py` | 1,469 | `core/brain.py` | Main router |
| `unified_orchestrator.py` | 1,016 | `projects/registry.py` | Project management |
| `system_orchestrator.py` | 827 | `utils/media_control.py` | Scraper/ARR control |
| `claude_orchestrator.py` | 412 | `serve/task_queue.py` | Keep as utility |
| `sam_parity_orchestrator.py` | 1,034 | ARCHIVE | Superseded |
| `re_orchestrator.py` | 874 | ARCHIVE | Legacy |
| `cognitive/unified_orchestrator.py` | 1,817 | `core/brain.py` (merge) | RAG/context integration |

### Learning Systems (5 → 4)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `perpetual_learner.py` | 1,685 | `learn/daemon.py` + `learn/curriculum.py` | Split |
| `auto_learner.py` | 961 | `learn/from_claude.py` | Rename |
| `claude_learning.py` | ? | MERGE with auto_learner | Duplicate |
| `knowledge_distillation.py` | 3,739 | `learn/from_claude.py` (patterns) | Extract patterns |
| `terminal_learning.py` | 901 | ARCHIVE | Superseded |

### Training Systems (8 → 2)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `training_runner.py` | 980 | `learn/train.py` | Core training |
| `training_scheduler.py` | 942 | `learn/train.py` (merge) | Scheduling |
| `training_stats.py` | 860 | `learn/train.py` (merge) | Statistics |
| `training_pipeline.py` | 260 | `learn/train.py` (merge) | Pipeline |
| `training_prep.py` | 800 | `learn/train.py` (merge) | Data prep |
| `training_data.py` | 1,280 | `learn/training_data.py` | Keep separate |
| `training_capture.py` | 1,226 | `learn/from_feedback.py` | Merge |
| `training_data_collector.py` | 250 | ARCHIVE | Legacy |

### Voice (10 → 6)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `voice/voice_pipeline.py` | 520 | `speak/tts.py` + `listen/stt.py` | Split |
| `voice/voice_output.py` | 323 | `speak/tts.py` | Merge |
| `voice/voice_bridge.py` | 285 | `speak/rvc.py` | Rename |
| `voice/voice_server.py` | 499 | `serve/voice.py` | Move to serve |
| `voice/voice_settings.py` | 561 | `speak/settings.py` | Rename |
| `voice/voice_cache.py` | 623 | `speak/cache.py` | Rename |
| `voice/voice_preprocessor.py` | 690 | `speak/preprocess.py` | Rename |
| `voice/voice_trainer.py` | 202 | `speak/train_voice.py` | Rename |
| `voice/voice_extraction_pipeline.py` | 1,085 | `speak/extract.py` | Rename |
| `tts_pipeline.py` (root) | 422 | DELETE | Duplicate |

### Vision (7 → 4)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `cognitive/vision_engine.py` | 1,054 | `see/describe.py` | Main VLM |
| `cognitive/vision_client.py` | 172 | DELETE | Thin wrapper |
| `cognitive/smart_vision.py` | 542 | MERGE with vision_engine | Duplicate |
| `cognitive/vision_selector.py` | 365 | MERGE with vision_engine | Duplicate |
| `cognitive/image_preprocessor.py` | 232 | `see/preprocess.py` | Rename |
| `apple_ocr.py` | 191 | `see/ocr.py` | Move |
| `vision_server.py` | 476 | `serve/vision.py` | Move |

### Memory (8 → 5)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `memory/semantic_memory.py` | 743 | `remember/embeddings.py` | Rename |
| `memory/fact_memory.py` | 2,506 | `remember/facts.py` | Rename |
| `memory/conversation_memory.py` | 826 | `remember/conversations.py` | Rename |
| `memory/project_context.py` | 3,287 | `remember/projects.py` | Rename |
| `memory/rag_feedback.py` | 1,137 | `remember/rag.py` | Rename |
| `memory/context_budget.py` | 2,866 | `think/budget.py` | Move to think |
| `memory/infinite_context.py` | 1,087 | `think/infinite.py` | Move to think |
| `memory/index_ollama_backup.npy` | - | DELETE | Obsolete |

### Execution (8 → 5)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `execution/safe_executor.py` | 933 | `do/run.py` | Rename |
| `execution/command_classifier.py` | 986 | `do/classify.py` | Rename |
| `execution/command_proposer.py` | 1,344 | `do/propose.py` | Rename |
| `execution/auto_fix.py` | 1,851 | `do/fix.py` | Rename |
| `execution/auto_fix_control.py` | 1,758 | `do/fix.py` (merge) | Merge |
| `execution/escalation_handler.py` | 428 | `think/escalate.py` | Move |
| `execution/escalation_learner.py` | 522 | `learn/from_errors.py` | Rename |
| `execution/execution_history.py` | 1,635 | `do/history.py` | Rename |

### Cognitive (34 → distributed)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `cognitive/mlx_cognitive.py` | 874 | `think/mlx.py` | Rename |
| `cognitive/mlx_optimized.py` | 628 | `think/mlx.py` (merge) | Merge |
| `cognitive/model_selector.py` | 486 | `think/select_model.py` | Rename |
| `cognitive/quality_validator.py` | 627 | `think/validate.py` | Rename |
| `cognitive/resource_manager.py` | 571 | `utils/resources.py` | Move |
| `cognitive/token_budget.py` | 514 | `think/budget.py` | Move |
| `cognitive/emotional_model.py` | 536 | `core/emotion.py` | Move |
| `cognitive/enhanced_memory.py` | 729 | `remember/working.py` | Rename |
| `cognitive/enhanced_retrieval.py` | 734 | `remember/retrieve.py` | Rename |
| `cognitive/enhanced_learning.py` | 679 | `learn/active.py` | Rename |
| `cognitive/learning_strategy.py` | 300 | `learn/strategy.py` | Keep |
| `cognitive/planning_framework.py` | 350 | `core/plan.py` | Move |
| `cognitive/personality.py` | 307 | `core/identity.py` | Rename |
| `cognitive/code_indexer.py` | 676 | `projects/search_code.py` | Rename |
| `cognitive/doc_indexer.py` | 452 | `projects/search_docs.py` | Rename |
| `cognitive/app_knowledge_extractor.py` | 1,330 | `utils/app_knowledge.py` | Move |
| `cognitive/code_pattern_miner.py` | 1,537 | `learn/from_code.py` | Rename |
| `cognitive/ui_awareness.py` | 843 | `see/ui_state.py` | Move |

### Entry Points (6 → 3)

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `sam.py` | 388 | `sam.py` | Keep as main entry |
| `sam_api.py` | 5,658 | `serve/http.py` | Split into routes |
| `sam_chat.py` | 247 | DELETE | Redundant with sam.py |
| `sam_enhanced.py` | 380 | DELETE | Redundant |
| `sam_repl.py` | 380 | `serve/cli.py` (merge) | Merge |
| `sam_agent.py` | 316 | DELETE | Redundant |

### Root Files to Organize

| Old File | Lines | New Location | Notes |
|----------|-------|--------------|-------|
| `data_arsenal.py` | 1,183 | `utils/data_arsenal.py` | Move |
| `feedback_system.py` | 3,872 | `learn/feedback.py` | Split/simplify |
| `code_indexer.py` | 2,074 | `projects/search_code.py` | Merge with cognitive version |
| `response_styler.py` | 427 | `core/style.py` | Move |
| `thinking_verbs.py` | 201 | `core/style.py` (merge) | Merge |
| `privacy_guard.py` | 350 | `do/privacy.py` | Move |
| `approval_queue.py` | 1,015 | `do/approve.py` | Rename |
| `ssot_sync.py` | 317 | `utils/ssot.py` | Move |
| `comfyui_client.py` | 142 | `utils/comfyui.py` | Move |
| `image_generator.py` | 282 | `utils/images.py` | Merge |
| `audio_utils.py` | 239 | `utils/audio.py` | Rename |
| `mlx_inference.py` | 318 | `think/mlx.py` (merge) | Merge |

---

## Implementation Phases

### Phase 1: Create New Structure (Day 1)
- Create all new directories with README.md files
- Create __init__.py files with clear docstrings
- NO code changes yet

### Phase 2: Core (Days 2-3)
- `core/brain.py` ← orchestrator.py
- `core/config.py` ← extract from sam_api.py
- `core/identity.py` ← cognitive/personality.py

### Phase 3: Think (Days 4-5)
- `think/mlx.py` ← cognitive/mlx_*.py
- `think/escalate.py` ← execution/escalation_handler.py
- `think/validate.py` ← cognitive/quality_validator.py

### Phase 4: Voice (Days 6-7)
- `speak/` ← voice/voice_output.py, voice_bridge.py, etc.
- `listen/` ← voice/voice_pipeline.py (STT parts)

### Phase 5: Vision (Day 8)
- `see/` ← cognitive/vision_*.py, apple_ocr.py

### Phase 6: Memory (Days 9-10)
- `remember/` ← memory/*.py

### Phase 7: Execution (Day 11)
- `do/` ← execution/*.py

### Phase 8: Learning (Days 12-14)
- `learn/` ← perpetual_learner.py, auto_learner.py, training_*.py

### Phase 9: Projects (Day 15)
- `projects/` ← unified_orchestrator.py, code_indexer.py

### Phase 10: Serve (Days 16-17)
- `serve/` ← sam_api.py, vision_server.py, voice_server.py

### Phase 11: Cleanup (Days 18-19)
- Archive old files
- Update all imports
- Test everything

### Phase 12: Documentation (Day 20)
- Write all README.md files
- Create ARCHITECTURE.md
- Update SSOT

---

## README Template for Each Package

```markdown
# [Package Name]

## What This Does
[One sentence: what capability this provides]

## Why It Exists
[One sentence: why SAM needs this]

## When To Use
[List of scenarios]

## How To Use
```python
from sam.[package] import [main_function]
[main_function]("example")
```

## Key Files
- `file1.py` - [what it does]
- `file2.py` - [what it does]

## Dependencies
- Requires: [other packages]
- Required by: [other packages]
```

---

## Success Criteria

1. **5-Minute Test**: A new developer can understand the entire system by reading:
   - `README.md` (2 min)
   - Package README files (3 min)

2. **Grep Test**: Searching for functionality finds it immediately:
   - "voice" → `speak/`, `listen/`
   - "learn" → `learn/`
   - "remember" → `remember/`

3. **Import Test**: All imports are intuitive:
   - `from sam.speak import tts`
   - `from sam.remember import facts`
   - `from sam.learn import from_claude`

4. **No Duplicates**: Each capability exists in exactly one place

5. **Self-Documenting**: File names describe function without reading code

---

## File Count Summary

| Category | Before | After | Reduction |
|----------|--------|-------|-----------|
| Root files | 77 | 1 | -76 |
| Orchestrators | 7 | 1 | -6 |
| Learning | 5 | 4 | -1 |
| Training | 8 | 2 | -6 |
| Voice | 10 | 6 | -4 |
| Vision | 7 | 4 | -3 |
| Memory | 8 | 5 | -3 |
| Execution | 8 | 5 | -3 |
| Cognitive | 34 | 0 (distributed) | -34 |
| Entry points | 6 | 3 | -3 |
| **Total** | **~160** | **~50** | **-110** |
