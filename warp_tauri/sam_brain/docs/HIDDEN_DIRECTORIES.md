# SAM Brain - Complete Directory Audit

**Created:** 2026-01-29
**Scope:** Every subdirectory in `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`

---

## conversation_engine/ - Natural Voice Conversation System

**Status: ACTIVE but EARLY-STAGE (v0.1.0)**
**Created:** 2026-01-20
**Has __pycache__:** Yes (all 4 modules compiled)
**Imported by:** `voice/voice_pipeline.py` (line 41)

### Files

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 54 | Package exports, describes 3 backend modes (components, moshi, cloud) |
| `engine.py` | 513 | Main `ConversationEngine` class - orchestrates continuous audio processing, turn-taking, backchannels, interrupts, and speculative response caching |
| `events.py` | 203 | Event dataclasses (`BackchannelEvent`, `ResponseEvent`, `InterruptEvent`, `TurnChangeEvent`, `EmotionChangeEvent`, `UserSpeakingEvent`, `UserFinishedEvent`) plus backchannel template library |
| `state.py` | 227 | `ConversationState` class - tracks speaker, phase, turns, emotions, backchannels, interrupt counts, audio buffers, timing stats |
| `turn_predictor.py` | 382 | `TurnPredictor` - heuristic turn-end detection using linguistic cues (sentence completion, trailing phrases), pause duration, and prosodic features (pitch, energy, rate). Includes stub `NeuralTurnPredictor` for future MLX model |

### How It Relates to the Main Orchestrator

The conversation_engine does NOT route through `orchestrator.py`. Instead:

1. `voice/voice_pipeline.py` imports `ConversationEngine` directly (line 41)
2. The engine accepts callback functions (`transcribe_fn`, `generate_fn`, `synthesize_fn`, `detect_emotion_fn`) that wire it to the rest of SAM
3. It operates at a LOWER level than the orchestrator - it handles real-time audio stream processing, turn-taking timing, and backchannel generation
4. The orchestrator handles "what kind of request is this?" routing; the conversation_engine handles "when should SAM start/stop speaking?"

**Data flow:** Microphone -> `conversation_engine.process_audio()` -> emits events -> `voice_pipeline` handles events -> calls orchestrator for response generation

### Duplication Analysis

| conversation_engine component | Potentially overlapping module | Verdict |
|------|------|---------|
| `state.py` (turn tracking) | `conversation_logger.py` (conversation logging to SQLite) | **Different purposes.** State is real-time in-memory; logger is persistent audit trail |
| `state.py` (conversation memory) | `memory/conversation_memory.py` (long-term conversation storage) | **Different purposes.** State is current-session turns; memory is cross-session persistence with fact extraction |
| `events.py` (backchannel templates) | `emotion2vec_mlx/prosody_control.py` (emotion-to-prosody mapping) | **Complementary.** Backchannels decide WHAT to say; prosody decides HOW to say it |
| `engine.py` (response emotion selection) | `cognitive/emotional_model.py` (mood state machine) | **Partial overlap.** Engine has a simple emotion complement map (lines 464-478). Emotional model is more sophisticated with relationship tracking. Should probably use the emotional model instead |

**Conclusion:** Mostly unique functionality. The conversation_engine provides real-time duplex conversation management that does not exist elsewhere in the codebase. Minor overlap in emotion selection logic.

---

## ALL Subdirectories in sam_brain/

### 1. ACTIVE - Populated with Working Code

| Directory | Files | Purpose | Status |
|-----------|-------|---------|--------|
| `cognitive/` | 37 .py files | MLX inference, vision, memory, learning, planning, personality, resource management | **ACTIVE** - Core cognitive engine, heavily used |
| `memory/` | 12 files | Semantic memory (MLX embeddings), fact memory, conversation memory, project context, RAG feedback, context budget | **ACTIVE** - Primary memory system |
| `execution/` | 8 .py files | Command classification, safe execution, auto-fix, escalation handling/learning, execution history | **ACTIVE** - Command execution subsystem |
| `voice/` | 11 .py files + cache dir | Voice pipeline, voice output, bridge, cache, preprocessing, settings, extraction, server, trainer | **ACTIVE** - Full voice subsystem |
| `conversation_engine/` | 4 .py files | Real-time turn-taking, backchannels, interrupts, conversation state | **ACTIVE** - Early stage, imported by voice_pipeline |
| `emotion2vec_mlx/` | 7 .py files + backends/ + models/ + utils/ | MLX-native emotion detection from voice audio, prosody control | **ACTIVE** - Emotion recognition |
| `tests/` | 17 test files | Test suite covering auto-fix, context compression, execution security, fact memory, feedback, vision, voice, RAG, training | **ACTIVE** - Comprehensive test coverage |
| `docs/` | 43 .md files | Detailed documentation for every subsystem | **ACTIVE** - Extensive documentation |
| `utils/` | 1 .py file (`parallel_utils.py`) | Parallel execution utilities | **ACTIVE** - Small but used |
| `startup/` | 1 .py file (`project_context.py`) | Project scanning and registry at startup | **ACTIVE** - Startup initialization |
| `warp_knowledge/` | 5 data files + 2 docs | Extracted Warp terminal knowledge (AI queries, commands, workflows) | **ACTIVE** - Reference data for Warp replication |
| `static/` | 2 HTML files (`index.html`, `mobile.html`) | Web UI for SAM API | **ACTIVE** - Frontend interfaces |

### 2. STUB - Reorganization Placeholders (Created 2026-01-28)

These directories were created as part of the "Revolutionary Reorganization Plan" (`docs/REORGANIZATION_PLAN.md`). Each contains ONLY an `__init__.py` stub and a `README.md` describing what WILL be migrated into them. **No actual code has been migrated yet.**

| Directory | Intended Purpose | Would Consolidate |
|-----------|-----------------|-------------------|
| `core/` | Central brain/router | `orchestrator.py` (1,469 lines), `cognitive/unified_orchestrator.py` (1,817 lines), parts of `sam_api.py` |
| `do/` | Safe command execution | `execution/safe_executor.py`, `execution/command_classifier.py`, `execution/auto_fix.py`, `approval_queue.py` |
| `learn/` | Self-improvement/training | `perpetual_learner.py`, `auto_learner.py`, `knowledge_distillation.py`, 8 training_* files, `feedback_system.py` |
| `listen/` | Voice input (STT + emotion) | STT parts of `voice/voice_pipeline.py`, `emotion2vec_mlx/` |
| `speak/` | Voice output (TTS) | `voice/voice_output.py`, `voice/voice_bridge.py`, `voice/voice_settings.py`, `voice/voice_cache.py`, `tts_pipeline.py` |
| `think/` | LLM inference | `cognitive/mlx_cognitive.py`, `cognitive/mlx_optimized.py`, `cognitive/model_selector.py`, `cognitive/quality_validator.py` |
| `remember/` | Memory systems | `memory/semantic_memory.py`, `memory/fact_memory.py`, `memory/conversation_memory.py`, `memory/project_context.py` |
| `see/` | Vision processing | `cognitive/vision_engine.py`, `cognitive/smart_vision.py`, `cognitive/vision_selector.py`, `apple_ocr.py` |
| `serve/` | HTTP/CLI API | `sam_api.py`, `vision_server.py`, `voice/voice_server.py`, `sam_repl.py` |
| `projects/` | Project awareness | `code_indexer.py`, `cognitive/doc_indexer.py`, project parts of `unified_orchestrator.py` |

**Verdict: All 10 stub directories are ABANDONED placeholders.** The reorganization plan was documented but never executed. All actual code remains in the original locations (root files, `cognitive/`, `memory/`, `execution/`, `voice/`).

### 3. EMPTY - No Content

| Directory | Purpose | Status |
|-----------|---------|--------|
| `audio_output/` | Presumably for generated audio files | **EMPTY** - Never populated or files cleaned up |
| `checkpoints/` | Training checkpoints | **EMPTY** - Checkpoints likely go to external storage |
| `training_logs/` | Training run logs | **EMPTY** - Logs likely go to external storage |
| `escalation_data/` | Data from escalation events | **EMPTY** - Created but unused |

### 4. DATA/ARCHIVE - Not Active Code

| Directory | Contents | Status |
|-----------|----------|--------|
| `archive/` | 1 file: `autonomous_daemon.py` (old daemon, replaced by `unified_daemon.py`) | **ARCHIVED** - Superseded code |
| `auto_training_data/` | `train.jsonl` (401KB) + `valid.jsonl` (45KB) | **DATA** - Generated training data, actively used |
| `exhaustive_analysis/` | `FULL_PROJECT_CATALOG.md` (116KB), `master_inventory.json` (2.8MB), `MASTER_REPORT.md` | **REFERENCE** - One-time project analysis from Jan 6 |
| `voice_cache/` | 2 .aiff files (~560KB total) | **CACHE** - Cached TTS output, old format |
| `voice_cache_v2/` | 1 .wav file (166KB) | **CACHE** - Cached TTS output, newer format |
| `.auto_fix_backups/` | 60 backup files | **BACKUPS** - Auto-fix system backups |
| `.pytest_cache/` | pytest cache | **CACHE** - Standard pytest cache |
| `__pycache__/` | Compiled .pyc files | **CACHE** - Standard Python cache |

### 5. SYMLINKS - External Storage

| Symlink | Target | Purpose |
|---------|--------|---------|
| `data` -> | `/Volumes/Applications/SAM/sam_brain_data` | Runtime data |
| `models` -> | `/Volumes/Applications/SAM/sam_brain_models` | MLX model weights |
| `training_data` -> | `/Volumes/Applications/SAM/training_data` | Training datasets |
| `adapters_new` -> | `/Volumes/Applications/SAM/adapters_new` | LoRA adapters |
| `.venv` -> | `/Volumes/Plex/DevSymlinks/venvs/sam_brain_dotvenv` | Python venv |
| `venv` -> | `/Volumes/Plex/DevSymlinks/venvs/sam_brain_venv` | Alt Python venv |
| `openvoice` -> | `/Volumes/Applications/SAM/openvoice` | OpenVoice models |

---

## Key Findings

### 1. conversation_engine/ is Legitimate and Active
It provides unique real-time duplex conversation management (turn prediction, backchannels, interrupt handling) that exists nowhere else. It is imported by `voice/voice_pipeline.py`. It has compiled `__pycache__` files. Status: early-stage but functional.

### 2. The Reorganization Never Happened
10 stub directories (`core/`, `do/`, `learn/`, `listen/`, `speak/`, `think/`, `remember/`, `see/`, `serve/`, `projects/`) were created on 2026-01-28 with READMEs describing an ambitious reorganization plan. No code was ever migrated. All actual functionality remains in the original locations. These stubs are dead weight that could cause confusion.

### 3. Several Empty Directories Exist
`audio_output/`, `checkpoints/`, `training_logs/`, and `escalation_data/` are empty. They may serve as expected output locations for scripts, or they may be unused.

### 4. conversation_engine is NOT Listed in CLAUDE.md
The `CLAUDE.md` file documents `cognitive/`, `emotion2vec_mlx/`, `voice/`, `memory/`, `execution/`, but does not mention `conversation_engine/` at all. It should be added to the architecture documentation.

### 5. Dual Voice Caches
Both `voice_cache/` (2 .aiff files) and `voice_cache_v2/` (1 .wav file) exist at root level, plus `voice/voice_cache/` (empty). Three cache locations for one feature.
