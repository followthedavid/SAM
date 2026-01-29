# SAM Brain: Configuration, Requirements, and Platform Audit

*Generated: 2026-01-29*

---

## 1. CONFIGURATION AUDIT

### 1.1 Hardcoded Paths

#### External Drive Paths (`/Volumes/`)

These will break if external drives are not mounted or renamed.

| File | Line(s) | Path |
|------|---------|------|
| `system_orchestrator.py` | 44 | `/Volumes/David External/sam_logs` |
| `system_orchestrator.py` | 79,88,97 | `/Volumes/David External/apple_dev_archive/apple_dev.db` |
| `system_orchestrator.py` | 106 | `/Volumes/David External/nifty_archive/nifty_index.db` |
| `system_orchestrator.py` | 115 | `/Volumes/David External/ao3_archive/ao3_index.db` |
| `system_orchestrator.py` | 124 | `/Volumes/David External/firstview_archive/firstview_index.db` |
| `system_orchestrator.py` | 133 | `/Volumes/#1/wwd_archive/wwd_index.db` |
| `system_orchestrator.py` | 142 | `/Volumes/David External/coding_training/code_collection.db` |
| `system_orchestrator.py` | 368 | `/Volumes/David External/arr_config` |
| `ssot_sync.py` | 29 | `/Volumes/Plex/SSOT` |
| `mlx_inference.py` | 18 | `/Volumes/David External/nifty_archive/models/sam-roleplay-qwen-lora` |
| `perpetual_learner.py` | 39 | `/Volumes/David External` |
| `training_data.py` | 50,52 | `/Volumes/David External/sam_training/...` |
| `knowledge_distillation.py` | 44-48 | `/Volumes/David External/sam_training/distilled/...` |
| `doc_ingestion.py` | 39-40 | `/Volumes/David External/sam_training/documentation/...` |
| `intelligence_core.py` | 43 | `/Volumes/David External/sam_memory/intelligence_core.db` |
| `code_indexer.py` | 42 | `/Volumes/David External/sam_memory/code_index_semantic.db` |
| `cognitive/mlx_cognitive.py` | 92,102,142 | `/Volumes/David External/sam_models/adapters/...` and `sam_memory` |
| `cognitive/mlx_optimized.py` | 69,397 | `/Volumes/David External/sam_memory` |
| `cognitive/enhanced_memory.py` | 242,444,605 | `/Volumes/David External/sam_memory/...` |
| `cognitive/enhanced_learning.py` | 52,278,464,606 | `/Volumes/David External/sam_memory/...` |
| `cognitive/enhanced_retrieval.py` | 834-836 | `/Volumes/David External/...` (3 DBs) |
| `cognitive/unified_orchestrator.py` | 366,1739,1753-1754 | `/Volumes/David External/sam_memory` and training DBs |
| `cognitive/emotional_model.py` | 419,590 | `/Volumes/David External/sam_memory/relationships.db` |
| `cognitive/model_evaluation.py` | 66-67 | `/Volumes/#1/SAM/evaluations` and `ab_tests` |
| `cognitive/code_pattern_miner.py` | 49 | `/Volumes/#1/SAM/training_data/code_patterns` |
| `cognitive/doc_indexer.py` | 407 | `/Volumes/David External/sam_memory/code_index.db` |
| `cognitive/code_indexer.py` | 385 | `/Volumes/David External/sam_memory/code_index.db` |
| `cognitive/resource_manager.py` | 225,240 | `/Volumes/David External/sam_memory/resource_config.json` |
| `cognitive/cognitive_control.py` | 97,403,811 | `/Volumes/David External/sam_memory/...` |
| `cognitive/planning_framework.py` | 162 | `/Volumes/David External/SAM_models/nanoLLaVA` |
| `cognitive/personality.py` | 336 | `/Volumes/David External/sam_training/personality_examples.jsonl` |
| `memory/project_context.py` | 271-273 | `/Volumes/David External/sam_memory/...` and `/Volumes/Plex/SSOT/...` |
| `memory/project_context.py` | 1524,1892 | `/Volumes/Plex/DevSymlinks` and `sam_memory/project_sessions.db` |
| `memory/fact_memory.py` | 126,132 | `/Volumes/David External/sam_memory/facts.db` |
| `memory/conversation_memory.py` | 32 | `/Volumes/David External/sam_memory/memory.db` |
| `memory/rag_feedback.py` | 67,73 | `/Volumes/David External/sam_memory/rag_feedback.db` |
| `feedback_system.py` | 72,78 | `/Volumes/David External/sam_memory/feedback.db` |
| `emotion2vec_mlx/backends/emotion2vec_backend.py` | 100 | `/Volumes/David External/SAM_models/emotion2vec` |
| `execution/auto_fix_control.py` | 60 | `/Volumes/David External/sam_memory/auto_fix.db` |
| `execution/escalation_handler.py` | 36 | `/Volumes/David External/sam_memory/cognitive` |
| `sam_api.py` | 1343 | `/Volumes/David External/sam_memory/cognitive` |
| `unified_orchestrator.py` | 267,279,etc. | Multiple project paths with `~/ReverseLab/...` |

#### User-specific paths (`/Users/`)

| File | Line | Path |
|------|------|------|
| `system_orchestrator.py` | 43 | `/Users/davidquinton/ReverseLab/SAM/scrapers` |
| `memory/project_context.py` | 272 | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/exhaustive_analysis/...` |
| `cognitive/test_e2e_comprehensive.py` | 971 | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/test_report.json` |

#### Home-relative paths (`~/`)

Many files use `Path.home() / ".sam" / ...` or `os.path.expanduser("~/...")` -- these are portable but assume a `~/.sam/` convention. Key locations:
- `~/.sam/approval_queue.db`
- `~/.sam/terminal_sessions.db`
- `~/.sam/conversations.db`
- `~/.sam/permissions.db`
- `~/.sam/thought_logs.db`
- `~/.sam/impact_tracker.db`
- `~/.sam/vision_selector.db`
- `~/.sam/vision_memory.db`
- `~/.sam/training_data.db` (fallback)
- `~/.sam/knowledge_distillation.db` (fallback)
- `~/.sam/auto_fix.db` (fallback)
- `~/.sam/models/sam-brain-fused`
- `~/.sam/models/sam-brain-active`
- `~/.sam/models/sam-abliterated-lora/adapters`
- `~/.sam/models/f5_tts`

**Recommendation**: Centralize all path constants into a single `config.py` with environment variable overrides, e.g. `SAM_EXTERNAL_DRIVE`, `SAM_MEMORY_DIR`, `SAM_MODELS_DIR`.

---

### 1.2 Hardcoded Ports

| File | Port | Service |
|------|------|---------|
| `sam_api.py` | **8765** | SAM API server (main) |
| `vision_server.py` | **8766** | Vision processing server |
| `cognitive/vision_client.py` | **8765** | Vision client default target |
| `cognitive/smart_vision.py` | **8766** | Smart vision server target |
| `cognitive/test_e2e_comprehensive.py` | **8765** | Test base URL |
| `test_new_features.py` | **8765** | Test base URL |
| `comfyui_client.py` | **8188** | ComfyUI server |
| `voice/voice_trainer.py` | **7865** | RVC training UI |
| `unified_daemon.py` | **8765, 8089** | Health check URLs |
| `system_orchestrator.py` | **7878, 8989, 8686, 9696, 6767** | Content services |
| `sam_agent.py` | **11434** | Ollama (STALE - decommissioned) |
| `sam_enhanced.py` | **11434** | Ollama (STALE) |
| `multi_agent.py` | **11434** | Ollama (STALE) |
| `sam_repl.py` | **11434** | Ollama health check (STALE) |
| `cognitive/enhanced_retrieval.py` | **11434** | Ollama embeddings fallback (STALE) |

**Recommendation**: Define all ports in a single config with env var overrides:
```python
SAM_API_PORT = int(os.getenv("SAM_API_PORT", "8765"))
VISION_SERVER_PORT = int(os.getenv("VISION_SERVER_PORT", "8766"))
```

---

### 1.3 Hardcoded Model Names/Paths

| File | Model |
|------|-------|
| `mlx_inference.py:19` | `mlx-community/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit` (BASE_MODEL) |
| `training_pipeline.py:32` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` (BASE_MODEL) |
| `model_deployment.py:59` | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` (BASE_MODEL) |
| `training_runner.py:55` | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` |
| `training_prep.py:48` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| `cognitive/mlx_cognitive.py:91` | `mlx-community/Qwen2.5-1.5B-Instruct-4bit` |
| `cognitive/mlx_cognitive.py:101` | `mlx-community/Qwen2.5-3B-Instruct-4bit` |
| `cognitive/vision_engine.py:125` | `nanollava` (DEFAULT_MODEL) |
| `sam_api.py:3152` | `mlx-community/nanoLLaVA-1.5-bf16` |
| `smart_router.py:147` | `dolphin-llama3:8b` (local_model) |
| `multi_agent.py:94` | `qwen2.5-coder:1.5b` |
| `live_thinking.py:272` | `sam-brain:latest` |
| `tts_pipeline.py:443` | `tts_models/en/ljspeech/tacotron2-DDC` |
| `cognitive/enhanced_retrieval.py:89` | `all-MiniLM-L6-v2` (embeddings) |
| `deduplication.py:415` | `sentence-transformers/all-MiniLM-L6-v2` |

**CONFLICT**: `BASE_MODEL` is defined differently in 3 files:
1. `mlx_inference.py` -> `mlx-community/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit`
2. `training_pipeline.py` -> `Qwen/Qwen2.5-Coder-1.5B-Instruct`
3. `model_deployment.py` -> `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit`

**STALE**: `smart_router.py` references `dolphin-llama3:8b` (Ollama model), `live_thinking.py` references `sam-brain:latest` (Ollama model name format).

---

### 1.4 Environment Variable Usage (`os.environ` / `os.getenv`)

| File | Line | Variable | Default |
|------|------|----------|---------|
| `auto_coordinator.py` | 89 | `CLAUDE_CODE` | (presence check) |
| `auto_coordinator.py` | 111 | `SAM_BRAIN` | (presence check) |
| `perpetual_learner.py` | 1606 | `ANTHROPIC_API_KEY` | None |
| `multi_agent.py` | 32 | `OLLAMA_URL` | `http://localhost:11434` |
| `tests/test_execution_security.py` | 439 | `ANTHROPIC_API_KEY` | (test sets fake key) |
| `execution/safe_executor.py` | 536,541 | `os.environ` | (inherits full env) |
| `voice/voice_server.py` | 200 | `PYTHONPATH` | (sets for RVC) |
| `tool_system.py` | 344 | `LANG` | `en_US.UTF-8` |

**Missing env vars**: No environment variable overrides exist for:
- Database paths
- Model paths / adapter paths
- Server ports
- External drive mount points

---

### 1.5 Argparse / sys.argv Usage

CLI entry points using `argparse`:
- `auto_coordinator.py` (line 563)
- `approval_queue.py` (line 1045)
- `cognitive/model_evaluation.py` (line 1948)
- `cognitive/vision_selector.py` (line 800)
- `cognitive/code_pattern_miner.py` (line 1337)
- `cognitive/app_knowledge_extractor.py` (line 1114)
- `cognitive/doc_indexer.py` (line 837)
- `cognitive/self_knowledge_handler.py` (line 315)
- `cognitive/vision_client.py` (line 754)
- `cognitive/image_preprocessor.py` (line 657)
- `cognitive/vision_engine.py` (line 1572)
- `cognitive/code_indexer.py` (line 637)

CLI entry points using raw `sys.argv`:
- `terminal_sessions.py` (line 855+)
- `ssot_sync.py` (line 650)
- `system_orchestrator.py` (line 704)
- `sam_agent.py` (line 265)
- `cognitive/multi_agent_roles.py` (line 1069)
- `cognitive/personality.py` (line 332)
- `cognitive/planning_framework.py` (line 745)
- `cognitive/ui_awareness.py` (line 760)
- `cognitive/smart_vision.py` (line 679)
- `cognitive/learning_strategy.py` (line 579)
- `smart_router.py` (line 247)
- `vision_server.py` (line 239)
- `sam_api.py` (line 5649)

**Inconsistency**: ~12 files use `argparse`, ~14 use raw `sys.argv`. Consider standardizing on `argparse` for all CLI entry points.

---

### 1.6 Duplicate Config Values Across Files

#### DB Paths defined in multiple places

The path `/Volumes/David External/sam_memory` appears as a default parameter in:
- `cognitive/mlx_cognitive.py` (line 142)
- `cognitive/mlx_optimized.py` (lines 69, 397)
- `cognitive/enhanced_memory.py` (line 605)
- `cognitive/enhanced_learning.py` (lines 464, 606)
- `cognitive/unified_orchestrator.py` (lines 366, 1739)
- `cognitive/emotional_model.py` (line 590)
- `cognitive/cognitive_control.py` (line 811)

The path `/Volumes/David External/sam_memory/code_index.db` is duplicated in:
- `cognitive/doc_indexer.py` (line 407, as `DB_PATH`)
- `cognitive/code_indexer.py` (line 385, as `DB_PATH`)

#### Port 8765 duplicated in:
- `sam_api.py`, `cognitive/vision_client.py`, `cognitive/test_e2e_comprehensive.py`, `test_new_features.py`, `unified_daemon.py`, `perpetual_learner.py`, `proactive_notifier.py`, `terminal_learning.py`

---

### 1.7 Ollama References (Should Be Removed)

Ollama was decommissioned on 2026-01-18 per project docs, but references remain in **16 files**:

#### Active code paths (not just comments):
| File | Lines | Issue |
|------|-------|-------|
| `sam_agent.py` | 19, 74 | `OLLAMA_URL` constant, used in API call |
| `sam_enhanced.py` | 30 | `OLLAMA_URL` constant |
| `multi_agent.py` | 32, 116 | `OLLAMA_URL` env var + API call |
| `cognitive/enhanced_retrieval.py` | 104-132 | Ollama embedding fallback (active code) |
| `memory/infinite_context.py` | 789-799 | Falls back to `ollama run dolphin-llama3` |
| `training_pipeline.py` | 239-264 | `export_to_ollama()` method |
| `training_data_collector.py` | 234-236, 273 | Routes to "ollama" as target |
| `data_arsenal.py` | 160-163 | `ollama_releases` data source config |
| `orchestrator.py` | 885 | Maps "ollama" in routing |
| `sam_repl.py` | 70-85 | Checks Ollama status on startup |
| `smart_router.py` | 19, 147 | `LOCAL = "local"` comment mentions Ollama; `dolphin-llama3:8b` |
| `live_thinking.py` | 272 | `sam-brain:latest` (Ollama model name format) |

#### Comment-only references (lower priority):
- `orchestrator.py` (lines 6, 20, 124-125) - docstrings noting Ollama replacement
- `memory/semantic_memory.py` (line 14) - migration note
- `memory/fact_memory.py` (lines 46, 1336) - example facts
- `sam_api.py` (line 797) - comment
- `live_thinking.py` (line 13) - migration note
- `test_suite.py` (lines 167-175) - test note
- `test_evolution_system.py` (lines 320-328) - test note

**Action needed**: Remove active Ollama code from `sam_agent.py`, `sam_enhanced.py`, `multi_agent.py`, `cognitive/enhanced_retrieval.py`, `memory/infinite_context.py`, `training_pipeline.py`, `training_data_collector.py`, `sam_repl.py`, `smart_router.py`, and `live_thinking.py`.

---

## 2. REQUIREMENTS AUDIT

### 2.1 Requirements File

**No `requirements.txt` found** in the `sam_brain/` directory. Dependencies are not formally declared.

### 2.2 Third-Party Packages Actually Imported

The following third-party (non-stdlib, non-local) packages are imported across the codebase:

| Package | Used In | PyPI Name |
|---------|---------|-----------|
| `requests` | Many files (API calls) | `requests` |
| `numpy` | Many files (`np`) | `numpy` |
| `psutil` | `cognitive/resource_manager.py` etc. | `psutil` |
| `mlx` | `cognitive/mlx_cognitive.py`, `mlx_optimized.py`, `emotion2vec_mlx/`, `audio_utils.py` | `mlx` |
| `mlx_lm` | `mlx_inference.py`, `cognitive/mlx_cognitive.py`, `mlx_optimized.py`, `model_deployment.py`, `sam.py`, `sam_parity_orchestrator.py` | `mlx-lm` |
| `mlx_vlm` | `cognitive/vision_engine.py`, `sam_api.py` | `mlx-vlm` |
| `mlx_embeddings` | `cognitive/doc_indexer.py`, `memory/semantic_memory.py`, `memory/context_budget.py`, `deduplication.py`, `relevance_scorer.py`, `code_indexer.py` | `mlx-embeddings` |
| `mlx_audio` | `emotion2vec_mlx/backends/prosodic_backend.py` | `mlx-audio` |
| `watchdog` | `claude_learning.py` (FileSystemEventHandler, Observer) | `watchdog` |
| `cryptography` | `execution/safe_executor.py` (Fernet, hashes, PBKDF2HMAC) | `cryptography` |
| `pytest` | `tests/`, `cognitive/test_e2e_comprehensive.py` | `pytest` |
| `torch` | `voice/voice_extraction_pipeline.py` | `torch` (PyTorch) |
| `xml` | Various (stdlib but also lxml in some contexts) | (stdlib) |
| `unicodedata` | Used for text processing | (stdlib) |
| `ApplicationServices` | `cognitive/app_knowledge_extractor.py`, `cognitive/ui_awareness.py`, `legitimate_extraction.py` | `pyobjc-framework-ApplicationServices` |
| `Quartz` | `apple_ocr.py`, `cognitive/app_knowledge_extractor.py`, `cognitive/smart_vision.py`, `re_orchestrator.py`, `legitimate_extraction.py` | `pyobjc-framework-Quartz` |
| `Foundation` | `apple_ocr.py`, `cognitive/smart_vision.py` | `pyobjc-framework-Cocoa` |

### 2.3 Packages Missing from Requirements (no requirements.txt exists)

Since there is no `requirements.txt`, ALL third-party packages are undeclared. A `requirements.txt` should be created containing at minimum:

```
# Core
requests
numpy
psutil
watchdog
cryptography

# MLX (Apple Silicon)
mlx
mlx-lm
mlx-vlm
mlx-embeddings
mlx-audio

# macOS native (pyobjc)
pyobjc-framework-ApplicationServices
pyobjc-framework-Quartz
pyobjc-framework-Cocoa

# Voice/Audio
torch  # for RVC voice extraction only
# soundfile  (if used via audio_utils.py)

# Testing
pytest
```

### 2.4 Potentially Unused Imports (Packages imported but may not be needed)

- `torch` -- only used in `voice/voice_extraction_pipeline.py` for MPS device check. Could be made optional.
- `cryptography` -- only in `execution/safe_executor.py`. Could be made optional.
- `mlx_audio` -- only in `emotion2vec_mlx/backends/prosodic_backend.py`, guarded by try/except.

---

## 3. PLATFORM-SPECIFIC CODE AUDIT

### 3.1 macOS-Specific Code (pyobjc / Apple Frameworks)

#### ApplicationServices (Accessibility API)

| File | Lines | Usage |
|------|-------|-------|
| `cognitive/ui_awareness.py` | 35-60 | `AXUIElementCreateSystemWide`, `AXUIElementCopyAttributeValue`, `AXUIElementPerformAction` etc. |
| `cognitive/app_knowledge_extractor.py` | 705, 729, 779, 883 | `AXIsProcessTrusted`, `AXUIElementCreateApplication`, `AXUIElementCopyAttributeValue`, `AXUIElementCopyActionNames` |
| `legitimate_extraction.py` | 359, 370, 406 | `AXIsProcessTrusted`, `AXUIElementCreateApplication` |

**These modules are entirely macOS-only and will not run on Linux/Windows.**

#### Quartz Framework

| File | Lines | Usage |
|------|-------|-------|
| `apple_ocr.py` | 18-19 | `Quartz.CGImageSourceCreateWithURL`, `Foundation.NSURL` -- Apple Vision OCR |
| `cognitive/smart_vision.py` | 362-363 | `Quartz`, `Foundation.NSURL` -- screenshot capture |
| `cognitive/app_knowledge_extractor.py` | 730 | `Quartz` -- window list capture |
| `re_orchestrator.py` | 382 | `Quartz` -- screen capture |
| `legitimate_extraction.py` | 375 | `Quartz` -- window enumeration |
| `cognitive/ui_awareness.py` | 60 | `Quartz` -- window bounds |

#### osascript (AppleScript via subprocess)

| File | Lines | Usage |
|------|-------|-------|
| `unified_daemon.py` | 263-275 | macOS notifications |
| `voice/voice_trainer.py` | 133, 175 | Docker control, app quit |
| `proactive_notifier.py` | 72 | macOS notification display |
| `re_orchestrator.py` | 498 | AppleScript execution |

#### macOS `say` command (TTS)

| File | Lines | Usage |
|------|-------|-------|
| `voice/voice_output.py` | 81, 100 | List voices, generate speech |
| `voice/voice_server.py` | 131 | TTS generation |
| `voice/voice_cache.py` | 687 | Cache voice output |
| `voice/voice_bridge.py` | 43, 142 | Default TTS engine |
| `voice/voice_settings.py` | 479 | Voice enumeration |
| `tts_pipeline.py` | 419 | TTS output |
| `proactive_notifier.py` | 97 | Speak notifications |

### 3.2 Apple Silicon Assumptions (MLX / MPS / Metal)

#### MLX Framework (Apple Silicon only)

MLX is the core inference framework and is **entirely Apple Silicon specific**. It appears in **25+ files**:

- `cognitive/mlx_cognitive.py` -- main engine, `from mlx_lm import load, generate`
- `cognitive/mlx_optimized.py` -- optimized engine with KV-cache quantization, `import mlx.core as mx`
- `mlx_inference.py` -- base inference, `from mlx_lm import load, generate`
- `cognitive/vision_engine.py` -- `import mlx_vlm`
- `sam_api.py` -- `from mlx_vlm import load, stream_generate`
- `memory/semantic_memory.py` -- `import mlx_embeddings`
- `memory/context_budget.py` -- `import mlx_embeddings`
- `cognitive/doc_indexer.py` -- `import mlx_embeddings`
- `emotion2vec_mlx/` -- entire package (models, backends)
- `audio_utils.py` -- `import mlx.core as mx`
- `deduplication.py` -- `import mlx_embeddings`
- `relevance_scorer.py` -- `import mlx_embeddings`
- `code_indexer.py` -- `import mlx_embeddings`
- `model_deployment.py` -- `from mlx_lm import load, generate`
- `sam.py` -- `from mlx_lm import load, generate`
- `sam_parity_orchestrator.py` -- `from mlx_lm import load`
- `training_pipeline.py` -- checks `import mlx; import mlx_lm`
- `cognitive/planning_framework.py` -- `import mlx.core`

**All MLX imports are guarded by try/except** in most files, which is good practice. However, the system fundamentally requires Apple Silicon -- there is no CPU/CUDA fallback path for inference.

#### MPS (Metal Performance Shaders via PyTorch)

| File | Lines | Usage |
|------|-------|-------|
| `voice/voice_extraction_pipeline.py` | 119, 137 | `torch.backends.mps.is_available()` -- GPU acceleration for voice extraction |

This is the only PyTorch MPS usage. It has a CPU fallback.

#### Platform check

| File | Lines | Usage |
|------|-------|-------|
| `cognitive/planning_framework.py` | 138-141 | `platform.system() == "Darwin"` check used for macOS-specific capabilities |

### 3.3 Path Assumptions

#### macOS-specific path patterns

- `/Users/` -- hardcoded user home paths (see section 1.1)
- `/Volumes/` -- macOS external drive mount points (see section 1.1)
- `~/Library/` -- referenced in `cognitive/app_knowledge_extractor.py` for Safari, Notes, Messages databases
- `/Applications/`, `/System/Applications/`, `~/Applications/` -- app discovery paths
- `~/.sam/` -- SAM home directory (works cross-platform via `Path.home()`)
- `~/.claude/` -- Claude Code directory referenced in `claude_learning.py`
- `~/.cache/huggingface/hub/` -- HuggingFace model cache (cross-platform)

#### Privacy-sensitive paths referenced

- `~/Library/Safari/History.db`
- `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`
- `~/Library/Messages/chat.db`

These are in `cognitive/app_knowledge_extractor.py` as known database locations for extraction.

---

## 4. SUMMARY OF CRITICAL ISSUES

### High Priority

1. **No `requirements.txt`** -- Third-party dependencies are completely undeclared. Create one immediately.

2. **Ollama code still active** -- 12+ files contain functional Ollama code paths that should be removed or replaced with MLX equivalents. Key offenders: `sam_agent.py`, `multi_agent.py`, `cognitive/enhanced_retrieval.py`, `memory/infinite_context.py`.

3. **3 conflicting `BASE_MODEL` definitions** -- `mlx_inference.py`, `training_pipeline.py`, and `model_deployment.py` each define a different `BASE_MODEL`. These should be unified.

4. **`/Volumes/David External/sam_memory`** repeated 20+ times as a default parameter -- should be a single constant imported from a config module.

### Medium Priority

5. **Port 8765 hardcoded in 8+ files** -- should be a shared constant with env var override.

6. **Mixed CLI style** -- half the entry points use `argparse`, half use raw `sys.argv`. Standardize on `argparse`.

7. **No platform guards** -- The entire codebase assumes macOS + Apple Silicon. While most MLX imports are try/excepted, there are no top-level warnings or checks at startup.

### Low Priority

8. **Comment-only Ollama references** -- ~8 files have Ollama mentions in comments/docstrings. Clean up for clarity.

9. **`/Users/davidquinton` hardcoded** in 3 files -- should use `Path.home()` or env vars.

10. **Stale model references** -- `dolphin-llama3:8b` in `smart_router.py` and `sam-brain:latest` in `live_thinking.py` are Ollama-era model names.

---

## 5. RECOMMENDED CONFIG ARCHITECTURE

Create a `config.py` at the project root:

```python
"""SAM Brain - Centralized Configuration"""
import os
from pathlib import Path

# External storage
EXTERNAL_DRIVE = Path(os.getenv("SAM_EXTERNAL_DRIVE", "/Volumes/David External"))
SSOT_PATH = Path(os.getenv("SAM_SSOT_PATH", "/Volumes/Plex/SSOT"))

# Memory / databases
MEMORY_DIR = Path(os.getenv("SAM_MEMORY_DIR", str(EXTERNAL_DRIVE / "sam_memory")))
TRAINING_DIR = Path(os.getenv("SAM_TRAINING_DIR", str(EXTERNAL_DRIVE / "sam_training")))
LOCAL_DATA_DIR = Path.home() / ".sam"

# Models
MODELS_DIR = Path(os.getenv("SAM_MODELS_DIR", str(EXTERNAL_DRIVE / "SAM_models")))
BASE_MODEL = os.getenv("SAM_BASE_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit")
BASE_MODEL_3B = os.getenv("SAM_BASE_MODEL_3B", "mlx-community/Qwen2.5-3B-Instruct-4bit")
VISION_MODEL = os.getenv("SAM_VISION_MODEL", "mlx-community/nanoLLaVA-1.5-bf16")

# Servers
SAM_API_PORT = int(os.getenv("SAM_API_PORT", "8765"))
VISION_SERVER_PORT = int(os.getenv("SAM_VISION_PORT", "8766"))
COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8188"))

# Feature flags
PLATFORM = os.getenv("SAM_PLATFORM", "darwin")  # darwin, linux
```

This would eliminate ~80% of the hardcoded values found in this audit.
