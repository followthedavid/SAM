# SAM Brain Deep Duplicate Analysis

**Date:** 2026-01-29
**Scope:** All `.py` files in `sam_brain/` (excluding `__pycache__`, `.auto_fix_backups`)
**Method:** Manual code reading and comparison of all suspected duplicates

---

## Summary

| Category | Count | Lines Recoverable |
|----------|-------|-------------------|
| Near-exact file duplicates | 2 | ~1,000 |
| Overlapping logic (same job, different approaches) | 6 | ~4,500 |
| Duplicate class definitions | 8 | ~200 |
| Duplicate enum definitions | 5 | ~100 |
| Total estimated removable lines | - | **~5,800** |

---

## 1. CODE INDEXER DUPLICATES

### Files
| File | Lines | Class | DB |
|------|-------|-------|----|
| `code_indexer.py` (root) | 2,074 | `CodeSymbol`, `CodeIndexer` | `code_index_semantic.db` |
| `cognitive/code_indexer.py` | 676 | `CodeEntity`, `CodeIndexer` | `code_index.db` |

### What's Duplicated
Both files:
- Define a `PythonParser` class that uses `ast.parse()` to extract functions, classes, and docstrings
- Define a `RustParser` class using regex for `fn`, `struct` patterns
- Define a `CodeIndexer` class with `index_project()`, `search()`, `get_stats()`, `clear_project()` methods
- Use SQLite for storage with nearly identical schemas
- Have a `get_code_indexer()` singleton function
- Have identical CLI with `index`, `search`, `stats`, `clear` commands

### Key Differences
- **Root version** (2,074 lines) is the NEWER, more complete version:
  - Adds `SwiftParser`, `TypeScriptParser` (cognitive/ only has `JavaScriptParser`)
  - Uses MLX embeddings for semantic search (`_get_embedding()`)
  - Has `IndexWatcher` class for file change monitoring
  - Uses `CodeSymbol` dataclass with `imports` and `embedding` fields
  - Uses a SEPARATE database (`code_index_semantic.db`)
- **Cognitive version** (676 lines) is OLDER, simpler:
  - Has `JavaScriptParser` (root has `TypeScriptParser` with more coverage)
  - No embeddings, pure text search
  - Uses `CodeEntity` dataclass (simpler, no embedding field)

### Recommendation
**KEEP:** `code_indexer.py` (root) -- it is the superset with embeddings, Swift support, and file watching.
**REMOVE:** `cognitive/code_indexer.py` -- update any imports pointing to `cognitive.code_indexer` to use root `code_indexer`.

**Shared duplicated code:**
- `PythonParser._parse_function()` -- nearly identical AST traversal logic (~40 lines)
- `PythonParser._parse_class()` -- nearly identical (~30 lines)
- `RustParser` -- identical regex patterns and `_find_doc_comment()` logic (~80 lines)
- `CodeIndexer._init_db()` -- same SQLite schema creation (~30 lines)
- `CodeIndexer.index_project()` -- same file scanning and mtime-based skip logic (~50 lines)
- `CodeIndexer.search()` -- same LIKE-based SQL query (~40 lines)

---

## 2. VISION SYSTEM DUPLICATES (4 files with overlapping VisionTier)

### Files
| File | Lines | Purpose |
|------|-------|---------|
| `cognitive/smart_vision.py` | 695 | Multi-tier vision routing + OCR/color/VLM/Claude handlers |
| `cognitive/vision_selector.py` | 881 | Resource-aware tier selection with success tracking |
| `cognitive/vision_engine.py` | 1,604 | Core vision engine with SmolVLM/Moondream models |
| `cognitive/vision_client.py` | 811 | HTTP + direct client wrapper for vision API |

### Duplicated Class: `VisionTier(Enum)`
Defined in **4 separate files** with slightly different values:

```python
# smart_vision.py - integer values
class VisionTier(Enum):
    ZERO_COST = 0
    LIGHTWEIGHT = 1
    LOCAL_VLM = 2
    CLAUDE = 3

# vision_selector.py - integer values (identical)
class VisionTier(Enum):
    ZERO_COST = 0
    LIGHTWEIGHT = 1
    LOCAL_VLM = 2
    CLAUDE = 3

# vision_client.py - STRING values (different!)
class VisionTier(Enum):
    ZERO_COST = "ZERO_COST"
    LIGHTWEIGHT = "LIGHTWEIGHT"
    LOCAL_VLM = "LOCAL_VLM"
    CLAUDE = "CLAUDE"

# resource_manager.py - integer values
class VisionTier(Enum):
    ZERO_COST = 0
    LIGHTWEIGHT = 1
    LOCAL_VLM = 2
    CLAUDE = 3
```

### Duplicated Logic: Task Classification
Both `smart_vision.py` and `vision_selector.py` implement keyword-based task classification:

```python
# smart_vision.py: TASK_KEYWORDS dict + SmartVisionRouter.classify_task()
# vision_selector.py: task_keywords dict + VisionSelector._classify_task_type()
# IDENTICAL keyword lists, same scoring algorithm (count matches, pick max)
```

### Overlapping Logic: Image Analysis
- `smart_vision.py` has `analyze_image_basic()` -- PIL-based edge detection, brightness, color
- `vision_selector.py` has `_looks_like_text_image()` -- PIL-based edge detection (subset)
- `vision_engine.py` has its own image preprocessing

### Recommendation
**KEEP:** `cognitive/vision_engine.py` as the core engine (most complete, referenced in CLAUDE.md).
**KEEP:** `cognitive/vision_selector.py` as the resource-aware selector (unique success tracking).
**MERGE INTO vision_engine.py:** The OCR/color/face handlers from `smart_vision.py` (they're simple and useful).
**REMOVE:** `cognitive/smart_vision.py` -- its `SmartVisionRouter` duplicates `vision_selector.py`'s `VisionSelector` (both route tasks to tiers, but vision_selector does it better with resource monitoring).
**KEEP:** `cognitive/vision_client.py` -- it's a client wrapper, different purpose. Fix its `VisionTier` to import from one canonical location.

**Single source for VisionTier:** Define once in `cognitive/resource_manager.py` (already imported by vision_selector), import everywhere else.

---

## 3. VOICE/TTS DUPLICATES (3 files)

### Files
| File | Lines | Classes |
|------|-------|---------|
| `voice/voice_output.py` | 320 | `VoiceConfig`, `VoiceEngine`, `MacOSVoice`, `CoquiVoice`, `RVCVoice`, `SAMVoice` |
| `voice/voice_bridge.py` | 306 | `VoiceConfig`, `VoiceBridge` |
| `tts_pipeline.py` (root) | 632 | `TTSEngine`, `QualityLevel`, `TTSPipeline` |

### Duplicated Class: `VoiceConfig`
Defined in BOTH `voice_output.py` and `voice_bridge.py`:

```python
# voice_output.py: dataclass-based VoiceConfig
@dataclass
class VoiceConfig:
    engine: str = "macos"
    voice: str = "Daniel"
    rate: int = 180
    # ... loads from voice/voice_config.json

# voice_bridge.py: dict-based VoiceConfig
class VoiceConfig:
    def __init__(self):
        self.config = self._load()  # dict from voice/voice_config.json
    # ... loads from SAME voice/voice_config.json
```

Both read/write the SAME `voice_config.json` file. Dangerous conflict potential.

### Duplicated Logic: macOS `say` TTS
All 3 files implement macOS `say` command for TTS:

```python
# voice_output.py: MacOSVoice.speak()
subprocess.run(["say", "-v", self.voice, "-r", str(self.rate), "-o", str(output_path), text])

# voice_bridge.py: VoiceBridge.text_to_speech()
subprocess.run(["say", "-o", str(output_path), text])

# tts_pipeline.py: TTSPipeline._synth_macos_say()
subprocess.run(["say", "-v", self.voice, "-r", str(self.rate), "-o", str(output_path), text])
```

### Duplicated Logic: Audio Playback
All 3 files have `subprocess.run(["afplay", str(path)])` for audio playback.

### Duplicated Logic: Coqui TTS
Both `voice_output.py` and `tts_pipeline.py` import and call `TTS.api.TTS` with model `tts_models/en/ljspeech/tacotron2-DDC`.

### Duplicated Logic: RVC Voice Conversion
Both `voice_output.py` (RVCVoice class) and `voice_bridge.py` (VoiceBridge.convert_voice()) implement RVC inference via subprocess, though both are placeholders/partial.

### Recommendation
**KEEP:** `tts_pipeline.py` -- it is the most complete (resource-aware fallback, caching, stats, thread-safe). This is the canonical TTS interface per CLAUDE.md.
**KEEP:** `voice/voice_output.py` -- referenced in CLAUDE.md as the "TTS engines interface". However, its logic is a subset of `tts_pipeline.py`. Consider making it a thin wrapper around `tts_pipeline.py`.
**REMOVE:** `voice/voice_bridge.py` -- its `VoiceBridge` is a less complete version of both other files. Its unique feature (listing RVC models/training data) could be moved to `voice_output.py` or a dedicated `voice/rvc_manager.py`.

---

## 4. AUTO-LEARNER vs CLAUDE-LEARNING DUPLICATES

### Files
| File | Lines | Main Class |
|------|-------|------------|
| `auto_learner.py` | 961 | `AutoLearner` (daemon with watchdog) |
| `claude_learning.py` | 764 | `ClaudeLearner` |

### What's Duplicated
Both files:
- Parse Claude Code conversations from `~/.claude/`
- Extract training pairs from user+Claude message pairs
- Categorize training data (code, reasoning, error_fix, explanation, planning)
- Calculate quality scores for extracted examples
- Store results for fine-tuning

### Key Differences
- **`auto_learner.py`** is a full DAEMON (watchdog-based file watching, SQLite storage, auto-triggers training, launchd integration, signal handling)
- **`claude_learning.py`** is a LIBRARY (conversation parsing logic, one-shot extraction, more detailed analysis with `ConversationAnalysis`)

### Duplicated Dataclass
```python
# auto_learner.py
@dataclass
class TrainingExample:
    id: str
    user_input: str
    claude_response: str
    category: str
    quality_score: float
    source_file: str
    extracted_at: str
    used_in_training: bool = False

# claude_learning.py
@dataclass
class TrainingPair:
    instruction: str
    input: str
    output: str
    category: str
    quality_score: float
    source: str
    metadata: Dict = field(default_factory=dict)
```

Same data, slightly different field names.

### Recommendation
**KEEP BOTH** but refactor:
- **`claude_learning.py`** should be the LIBRARY (parsing/extraction logic)
- **`auto_learner.py`** should be the DAEMON that calls `claude_learning.py` for extraction
- Currently `auto_learner.py` duplicates the parsing logic instead of importing it
- Unify `TrainingExample`/`TrainingPair` into one dataclass in `training_data.py`

---

## 5. PROJECT CONTEXT DUPLICATES

### Files
| File | Lines | Main Classes |
|------|-------|--------------|
| `startup/project_context.py` | 505 | `ProjectType`, `ProjectHealth`, `Project`, `ProjectRegistry` |
| `memory/project_context.py` | 3,287 | `ProjectDetector`, `ProjectInfo`, `Project`, `ProjectContext`, `ProjectProfile`, `ProjectProfileLoader`, `ProjectWatcher`, `ProjectSessionState` |

### What's Duplicated
Both files define a `Project` class with project scanning:

```python
# startup/project_context.py: Project.scan()
# - Detects type (Rust/Node/Python/Tauri) from config files
# - Gets git info (branch, changes, last commit)
# - Gets recent files
# - Checks running services

# memory/project_context.py: ProjectDetector.detect() + Project dataclass
# - Detects project from cwd or explicit path
# - Looks up project in known project map
# - Gets git info, file counts
```

Both define `ProjectHealth` / health evaluation.
Both define `ProjectType` detection from config files (Cargo.toml, package.json, etc.).
Both scan `~/ReverseLab` and `~/Projects` directories.

### Key Differences
- **`startup/project_context.py`** (505 lines) is a NEWER, cleaner, standalone module for startup scanning. It has `ProjectRegistry` with JSON persistence.
- **`memory/project_context.py`** (3,287 lines) is the OLDER, much more comprehensive module with:
  - SSOT integration (reads markdown project docs)
  - `ProjectProfileLoader` (loads from `/Volumes/Plex/SSOT/projects/`)
  - `ProjectWatcher` (directory monitoring for project switches)
  - `ProjectSessionState` (per-project session persistence)
  - `SessionRecall` (session continuity)
  - `ProjectContext` (legacy full context class)

### Recommendation
**KEEP:** `memory/project_context.py` -- it is far more comprehensive and is the canonical import used by `cognitive/unified_orchestrator.py`.
**MERGE INTO memory/:** The clean `ProjectRegistry` class from `startup/project_context.py` (it has a nice scan+save+load pattern).
**REMOVE:** `startup/project_context.py` after merging its `ProjectRegistry` into `memory/project_context.py`.

---

## 6. ORCHESTRATOR PROLIFERATION (7 files!)

### Files
| File | Lines | Purpose |
|------|-------|---------|
| `orchestrator.py` | 1,469 | **CANONICAL** MLX orchestrator - routes CHAT/CODE/VISION/VOICE/etc. |
| `cognitive/unified_orchestrator.py` | 1,817 | **CANONICAL** cognitive integration - memory/retrieval/learning/emotion |
| `unified_orchestrator.py` (root) | 1,016 | Project management orchestrator (project DB, priorities) |
| `system_orchestrator.py` | 802 | Scraper/ARR stack management |
| `re_orchestrator.py` | 874 | Reverse engineering tool orchestration |
| `sam_parity_orchestrator.py` | 530 | Parity tracking (local vs Claude capabilities) |
| `claude_orchestrator.py` | 399 | Task queue for Claude-directed work |

### Analysis
These are NOT exact duplicates -- each orchestrates a **different domain**. However, there is significant overlap in patterns:

**Actually duplicated:**
- `orchestrator.py` and `cognitive/unified_orchestrator.py` both do request routing with overlapping logic. The cognitive version integrates memory/learning while the root version integrates MLX/privacy/response styling.
- `unified_orchestrator.py` (root) and `sam_parity_orchestrator.py` both track project status, both define `Project` dataclasses with `ProjectStatus` enums.

### Recommendation
**KEEP (distinct domains):**
- `orchestrator.py` -- main request router (CLAUDE.md canonical)
- `cognitive/unified_orchestrator.py` -- cognitive systems integration
- `system_orchestrator.py` -- scraper/media management (different domain)
- `re_orchestrator.py` -- reverse engineering (different domain)

**MERGE/REMOVE:**
- `unified_orchestrator.py` (root, 1,016 lines) -- project management. Its `Project` class duplicates `startup/project_context.py` and `memory/project_context.py`. Merge unique bits into `memory/project_context.py`, then remove.
- `sam_parity_orchestrator.py` (530 lines) -- parity tracking. This is essentially a documentation file disguised as code. Its capability matrix is a static dict. Consider converting to `docs/PARITY_MATRIX.md` or merging the runtime logic into `orchestrator.py`.
- `claude_orchestrator.py` (399 lines) -- task queue for Claude-directed work. Overlaps with `execution/` modules. Consider merging into `execution/command_proposer.py`.

---

## 7. TRAINING FILE DUPLICATES (8 files)

### Files
| File | Lines | Purpose |
|------|-------|---------|
| `training_data.py` | 1,280 | Unified schema + SQLite store (`TrainingExample`, `TrainingDataStore`) |
| `training_capture.py` | 1,226 | Captures from Claude escalations and user corrections |
| `training_data_collector.py` | 401 | Extracts from git/code/SSOT |
| `training_pipeline.py` | 333 | End-to-end training trigger |
| `training_prep.py` | 779 | Data formatting for MLX (tokenization, splits) |
| `training_runner.py` | 980 | Job lifecycle (start/stop/monitor training) |
| `training_scheduler.py` | 942 | Scheduled data gathering jobs |
| `training_stats.py` | 775 | Statistics dashboard |

### Duplicated Definitions

**`TrainingFormat(Enum)` defined in 2 files:**
```python
# training_data.py
class TrainingFormat(Enum):
    INSTRUCTION = "instruction"
    CHAT = "chat"
    DPO = "dpo"

# training_prep.py
class TrainingFormat(Enum):
    INSTRUCTION = "instruction"
    CHAT = "chat"
    DPO = "dpo"
```
Identical enum. `training_prep.py` should import from `training_data.py`.

**`TrainingExample` defined in 3 files:**
```python
# training_data.py: TrainingExample (canonical, full schema)
# auto_learner.py: TrainingExample (different fields)
# Also: TrainingPair in claude_learning.py (same concept, different name)
```

### Overlapping Logic

**`training_pipeline.py` vs `training_runner.py`:**
- `training_pipeline.py` (333 lines) has `MIN_SAMPLES_FOR_TRAINING`, `BASE_MODEL`, `LORA_RANK`, `TrainingRun` -- basic training trigger
- `training_runner.py` (980 lines) has `TrainingConfig`, `TrainingJobRunner` with full lifecycle management
- `training_pipeline.py` is an OLDER, simpler version that `training_runner.py` supersedes

**`training_data_collector.py` vs `training_capture.py`:**
- `training_data_collector.py` (401 lines) extracts from git/code/SSOT (batch collection)
- `training_capture.py` (1,226 lines) captures from live Claude sessions (real-time capture)
- These are complementary but have overlapping quality scoring logic

### Recommendation
**KEEP (each has distinct purpose):**
- `training_data.py` -- canonical schema + store
- `training_capture.py` -- real-time capture from Claude
- `training_prep.py` -- MLX format conversion (but fix `TrainingFormat` import)
- `training_runner.py` -- job runner
- `training_scheduler.py` -- scheduling
- `training_stats.py` -- stats

**REMOVE:**
- `training_pipeline.py` (333 lines) -- older, simpler version superseded by `training_runner.py`
- `training_data_collector.py` (401 lines) -- its git/SSOT extraction can be absorbed into `training_capture.py` or `training_scheduler.py`

**FIX:** `training_prep.py` should `from training_data import TrainingFormat` instead of redefining it.

---

## 8. INTELLIGENCE/LEARNING DUPLICATES

### Files
| File | Lines | Purpose |
|------|-------|---------|
| `sam_intelligence.py` | 751 | Self-awareness, proactive intelligence, action execution |
| `intelligence_core.py` | 813 | Knowledge distillation, feedback learning, cross-session memory |

### Analysis
Both are "intelligence" modules but focus on different aspects:
- `sam_intelligence.py` -- self-awareness, evolution tracking, improvement detection
- `intelligence_core.py` -- learning from escalations, user corrections, fact memory

They overlap in concept (both are "SAM's brain learning layer") but their implementations are largely distinct. However, `intelligence_core.py` imports from `evolution_tracker.py` and `improvement_detector.py`, which are also imported by `sam_intelligence.py`.

### Recommendation
**MERGE:** These should be one module. `intelligence_core.py` + `sam_intelligence.py` -> single `sam_intelligence.py` with both learning and self-awareness features.

---

## 9. MLX INFERENCE DUPLICATES

### Files
| File | Lines | Purpose |
|------|-------|---------|
| `mlx_inference.py` | 231 | Simple MLX inference (load model, generate) |
| `cognitive/mlx_cognitive.py` | 855 | Full cognitive engine (model selection, system prompts, generation config) |
| `cognitive/mlx_optimized.py` | 430 | KV-cache optimized engine |

### Analysis
- `mlx_inference.py` is the OLDEST, simplest version -- just `load_model()` + `generate_response()`
- `cognitive/mlx_cognitive.py` is the CANONICAL version referenced in CLAUDE.md
- `cognitive/mlx_optimized.py` adds KV-cache quantization on top of `mlx_cognitive.py`

### Recommendation
**KEEP:** `cognitive/mlx_cognitive.py` + `cognitive/mlx_optimized.py`
**REMOVE:** `mlx_inference.py` (231 lines) -- legacy, superseded by `cognitive/mlx_cognitive.py`. Update any remaining imports.

---

## 10. QUERY DECOMPOSER DUPLICATES

### Files
| File | Lines | Location |
|------|-------|----------|
| `query_decomposer.py` (root) | ~200 | Standalone module |
| `cognitive/enhanced_retrieval.py` | inline | Class within retrieval system (lines 528+) |

### What's Duplicated
Both implement `QueryDecomposer` with the same logic:
- Split on "and" / "or"
- Extract "how to X using Y" patterns
- Return list of sub-queries

### Recommendation
**KEEP:** The one in `cognitive/enhanced_retrieval.py` (it's used inline by the retrieval system).
**REMOVE:** `query_decomposer.py` (root) -- standalone duplicate. Update imports if any.

---

## 11. ADDITIONAL CLASS NAME CONFLICTS

These are classes with the same name defined in multiple files. While not always functional duplicates, they create import confusion:

| Class | Files | Risk |
|-------|-------|------|
| `VisionTier(Enum)` | `smart_vision.py`, `vision_selector.py`, `vision_client.py`, `resource_manager.py` | **HIGH** -- 4 definitions with inconsistent values |
| `VoiceConfig` | `voice_output.py`, `voice_bridge.py` | **HIGH** -- both read same config file |
| `TaskType(Enum)` | `smart_vision.py`, `model_selector.py`, `perpetual_learner.py`, `claude_orchestrator.py` | **MEDIUM** -- different enums with same name |
| `TaskStatus(Enum)` | `claude_orchestrator.py`, `utils/parallel_utils.py` | **LOW** -- different contexts |
| `TrainingExample` | `training_data.py`, `auto_learner.py` | **HIGH** -- same concept, different fields |
| `TrainingPair` | `claude_learning.py`, `cognitive/app_knowledge_extractor.py` | **MEDIUM** -- similar concept |
| `TrainingFormat(Enum)` | `training_data.py`, `training_prep.py` | **HIGH** -- identical, should import |
| `Project` | `startup/project_context.py`, `memory/project_context.py`, `unified_orchestrator.py`, `evolution_tracker.py` | **HIGH** -- 4 different Project classes |

---

## Recommended Cleanup Priority

### Phase 1: Quick Wins (fix imports, no logic changes)
1. `training_prep.py`: Change `TrainingFormat` to import from `training_data.py`
2. `vision_client.py`: Import `VisionTier` from `resource_manager.py`
3. `vision_selector.py`: Import `VisionTier` from `resource_manager.py`
4. `smart_vision.py`: Import `VisionTier` from `resource_manager.py`

### Phase 2: Safe Removals (files fully superseded)
1. **DELETE** `cognitive/code_indexer.py` (676 lines) -- superseded by root `code_indexer.py`
2. **DELETE** `mlx_inference.py` (231 lines) -- superseded by `cognitive/mlx_cognitive.py`
3. **DELETE** `training_pipeline.py` (333 lines) -- superseded by `training_runner.py`
4. **DELETE** `query_decomposer.py` (~200 lines) -- duplicated in `enhanced_retrieval.py`

### Phase 3: Merges (requires careful refactoring)
1. **MERGE** `voice_bridge.py` into `voice_output.py` (move RVC model listing)
2. **MERGE** `startup/project_context.py` into `memory/project_context.py`
3. **MERGE** `intelligence_core.py` + `sam_intelligence.py` into one module
4. **REFACTOR** `auto_learner.py` to import extraction logic from `claude_learning.py`

### Phase 4: Orchestrator Consolidation
1. **MERGE** `unified_orchestrator.py` (root) project tracking into `memory/project_context.py`
2. **CONVERT** `sam_parity_orchestrator.py` to documentation or merge into `orchestrator.py`
3. **MERGE** `claude_orchestrator.py` task queue into `execution/` module
4. **REMOVE** `smart_vision.py` after merging handlers into `vision_engine.py`

### Estimated Impact
- **~5,800 lines removable** across all phases
- **8 files removable**, 4 files mergeable
- **5 enum/class conflicts resolved**
- Import confusion significantly reduced

---

*Analysis performed by deep file-by-file code reading, not just filename matching.*
