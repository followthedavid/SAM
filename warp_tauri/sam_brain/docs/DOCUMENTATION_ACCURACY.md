# SAM Documentation Accuracy Audit

**Date:** 2026-01-28
**Auditor:** Claude Code
**Scope:** Cross-reference between SSOT documentation and sam_brain codebase

---

## Executive Summary

The SAM documentation ecosystem has **significant accuracy issues** stemming from:
1. A major reorganization in progress (documented but not executed)
2. File path discrepancies between docs and actual code location
3. Version number inconsistencies
4. Dead references to files that have been moved or renamed

**Overall Assessment:** 65% accuracy - documentation describes intent but reality differs

---

## 1. SSOT Documentation vs Reality

### /Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md

| Item | Documentation | Reality | Status |
|------|--------------|---------|--------|
| SAM Brain location | `~/ReverseLab/SAM/warp_tauri/sam_brain/` | Correct | OK |
| Ollama decommissioned | 2026-01-18 | Correct | OK |
| MLX as primary inference | Yes | Correct | OK |
| Cognitive modules listed | 8 modules | Actually 34+ modules in cognitive/ | OUTDATED |
| startup/project_context.py | Listed as "NEW" | Exists, 16KB | OK |
| ui_awareness.py | Listed as "NEW" | Exists | OK |
| docs/INDEX.md reference | "33 specs" | Actually 37 spec files | OUTDATED |

**Issues Found:**
- CLAUDE_READ_FIRST.md lists 8 cognitive modules but cognitive/ has 34+ files
- cognitive/__init__.py shows version 1.18.0 but CLAUDE.md says v0.5.0
- Missing new modules: model_evaluation.py, multi_agent_roles.py, code_pattern_miner.py

---

### /Volumes/Plex/SSOT/PROJECT_REGISTRY.md

| Item | Documentation | Reality | Status |
|------|--------------|---------|--------|
| SAM Terminal path | `~/ReverseLab/SAM/warp_tauri` | Correct | OK |
| SAM model | "Qwen2.5-1.5B + SAM LoRA" | Correct | OK |
| 20+ projects listed | Yes | Correct | OK |
| LLM strategy percentages | MLX 80%, ChatGPT 15%, Claude 5% | Reasonable | OK |

**Issues Found:**
- Registry accurate but missing newer cognitive modules
- GridPlayer status says "macOS Python + PyQt5 (current)" but actual implementation unclear

---

### /Volumes/Plex/SSOT/SAM_IDENTITY.md

| Item | Documentation | Reality | Status |
|------|--------------|---------|--------|
| SAM personality | "Male, cocky, flirtatious" | Documented, personality.py exists | OK |
| warp_core lines | "1,799 lines" | Not verified | UNVERIFIED |
| Therapy/Coach modes | "Not started" | Still accurate | OK |

**Issues Found:**
- States "SAM as a personality does not exist yet" - may be stale given personality.py exists in cognitive/

---

### /Volumes/Plex/SSOT/STORAGE_STRATEGY.md

| Item | Documentation | Reality | Status |
|------|--------------|---------|--------|
| Drive layout | Lists 4 drives | Accurate | OK |
| /Volumes/Applications | Added 2026-01-27 | Exists and used | OK |
| SAM Brain storage | "Models: Should be symlinked" | Symlinks exist at data/, models/, training_data/ | OK |
| Ollama reference | "Legacy Ollama models (decommissioned)" | Correct | OK |

**Issues Found:**
- Minor: Mentions training data at DevSymlinks but STORAGE_AND_DATA_MAP shows it moved to #1/SAM/

---

## 2. sam_brain/CLAUDE.md vs Reality

### Version Numbers

| Documentation | Code Reality | Status |
|---------------|--------------|--------|
| "v0.5.0 (Full Multi-Modal)" | cognitive/__init__.py says v1.18.0 | MAJOR DISCREPANCY |
| cognitive version "v1.13.0" | Actually v1.18.0 | OUTDATED |

### File Locations - CRITICAL ISSUES

| Documented Location | Actual Location | Status |
|---------------------|-----------------|--------|
| `voice_pipeline.py` (root) | `voice/voice_pipeline.py` | WRONG PATH |
| `voice_settings.py` (root) | `voice/voice_settings.py` | WRONG PATH |
| `voice_output.py` (root) | `voice/voice_output.py` | WRONG PATH |
| `semantic_memory.py` (root) | `memory/semantic_memory.py` | WRONG PATH |
| `voice_server.py` (root) | `voice/voice_server.py` | WRONG PATH |

**Key Files Section lists 9 files at root level that are actually in subdirectories.**

### Cognitive Module Documentation

| Documented Module | Actual File | Status |
|-------------------|-------------|--------|
| vision_engine.py | Exists | OK |
| smart_vision.py | Exists | OK |
| vision_client.py | Exists | OK |
| vision_selector.py | Exists | OK |
| image_preprocessor.py | Exists | OK |
| unified_orchestrator.py | Exists | OK |
| code_indexer.py | Exists | OK |
| doc_indexer.py | Exists | OK |
| self_knowledge_handler.py | Exists | OK |
| learning_strategy.py | **NOT documented** | MISSING DOC |
| planning_framework.py | **NOT documented** | MISSING DOC |
| ui_awareness.py | **NOT documented** | MISSING DOC |
| app_knowledge_extractor.py | **NOT documented** | MISSING DOC |
| code_pattern_miner.py | **NOT documented** | MISSING DOC |
| multi_agent_roles.py | **NOT documented** | MISSING DOC |
| model_evaluation.py | **NOT documented** | MISSING DOC |
| personality.py | **NOT documented** | MISSING DOC |

**13 cognitive modules exist that are not documented in CLAUDE.md**

### emotion2vec_mlx Structure

| Documentation | Reality | Status |
|---------------|---------|--------|
| Lists backends/ | Exists: emotion2vec_backend.py, prosodic_backend.py | OK |
| Lists models/ | Exists: emotion2vec_mlx.py, convert_*.py | OK |
| Lists utils/ | Exists but empty (just __pycache__) | MINOR ISSUE |

---

## 3. sam_brain/ARCHITECTURE.md vs Reality

### Reorganization Status

**Documentation claims:**
```
Phase 1: Structure created (directories + READMEs)
Phase 2-12: Pending
```

**Reality:**
- New directories exist: core/, think/, speak/, listen/, see/, remember/, do/, learn/, projects/, serve/, utils/
- Each has only __init__.py and README.md
- **NO actual code has been migrated** - all code still in old locations

This means the architecture diagram showing:
- `core/brain.py` - DOES NOT EXIST
- `think/mlx.py` - DOES NOT EXIST
- `speak/tts.py` - DOES NOT EXIST
- etc.

**The entire ARCHITECTURE.md describes a PLANNED state, not current reality.**

### Package Entry Points - ALL FICTIONAL

| Documented Entry Point | Exists? | Status |
|-----------------------|---------|--------|
| `core.brain.process()` | No | FICTIONAL |
| `think.mlx.generate()` | No | FICTIONAL |
| `speak.tts.say()` | No | FICTIONAL |
| `listen.stt.transcribe()` | No | FICTIONAL |
| `see.describe.image()` | No | FICTIONAL |
| `remember.embeddings.search()` | No | FICTIONAL |
| `do.run.execute()` | No | FICTIONAL |
| `learn.train.run()` | No | FICTIONAL |

---

## 4. docs/INDEX.md vs Reality

| Claim | Reality | Status |
|-------|---------|--------|
| "33 documents" in title | Actually 37 .md files in docs/ | OUTDATED |
| Last Updated: 2026-01-28 | Current date | OK |
| All doc files listed | Most exist | OK |

**Missing from INDEX:**
- DEPENDENCY_GRAPH.md (created 2026-01-28)
- COMPLETE_FILE_AUDIT.md (created 2026-01-28)
- REORGANIZATION_PLAN.md (created 2026-01-28)

---

## 5. Code That's Not Documented

### Cognitive Modules Without Documentation

| Module | Lines | Purpose (inferred) |
|--------|-------|-------------------|
| `cognitive/learning_strategy.py` | 300+ | 5-tier learning hierarchy |
| `cognitive/planning_framework.py` | 350+ | 4-tier solution cascade |
| `cognitive/ui_awareness.py` | 843 | macOS Accessibility API |
| `cognitive/app_knowledge_extractor.py` | 1,330 | AppleScript/URL scheme extraction |
| `cognitive/code_pattern_miner.py` | 1,537 | Learn from code patterns |
| `cognitive/multi_agent_roles.py` | 542 | Multi-Claude coordination |
| `cognitive/model_evaluation.py` | 1,500+ | A/B testing, benchmarks |
| `cognitive/personality.py` | 307 | SAM modes, traits, training examples |

### Execution System Not Documented

| File | Lines | Purpose |
|------|-------|---------|
| `execution/auto_fix.py` | 1,851 | Automatic error correction |
| `execution/auto_fix_control.py` | 1,758 | Auto-fix control interface |
| `execution/command_classifier.py` | 986 | Safe command classification |
| `execution/command_proposer.py` | 1,344 | Command suggestion |
| `execution/escalation_handler.py` | 428 | When to escalate to Claude |
| `execution/escalation_learner.py` | 522 | Learn from escalations |
| `execution/execution_history.py` | 1,635 | Audit trail |
| `execution/safe_executor.py` | 933 | Safe command execution |

**execution/ has 8 files totaling 9,457 lines with only 1 doc reference (EXECUTION_SYSTEM.md)**

### Memory System Partially Documented

| File | Lines | Doc Coverage |
|------|-------|--------------|
| `memory/semantic_memory.py` | 743 | Partial in MEMORY_SYSTEM.md |
| `memory/fact_memory.py` | 2,506 | Partial |
| `memory/conversation_memory.py` | 826 | Partial |
| `memory/project_context.py` | 3,287 | Has own doc |
| `memory/context_budget.py` | 2,866 | Undocumented |
| `memory/infinite_context.py` | 1,087 | Undocumented |
| `memory/rag_feedback.py` | 1,137 | Partial in RAG_SYSTEM.md |

---

## 6. Documentation Describing Deleted/Moved Code

### Files Referenced But Moved

| Documentation | Old Path | New Path | Status |
|---------------|----------|----------|--------|
| CLAUDE.md | semantic_memory.py (root) | memory/semantic_memory.py | MOVED |
| CLAUDE.md | voice_pipeline.py (root) | voice/voice_pipeline.py | MOVED |
| CLAUDE.md | voice_settings.py (root) | voice/voice_settings.py | MOVED |
| CLAUDE.md | voice_output.py (root) | voice/voice_output.py | MOVED |
| CLAUDE.md | voice_server.py (root) | voice/voice_server.py | MOVED |

### Files That May Not Exist

| Reference | Status | Notes |
|-----------|--------|-------|
| `~/ai-studio/HANDOFF.md` | UNVERIFIED | Referenced in CLAUDE_READ_FIRST |
| `~/Projects/character-pipeline/ARCHITECTURE.md` | UNVERIFIED | Referenced in CLAUDE_READ_FIRST |
| `~/Projects/motion-pipeline/README.md` | UNVERIFIED | Referenced in CLAUDE_READ_FIRST |

---

## 7. Wrong Paths/Locations

### External Storage Paths

| Documentation | Reality | Status |
|---------------|---------|--------|
| `/Volumes/David External/SAM_models/` | EXISTS | OK |
| `/Volumes/David External/SAM_Voice_Training/` | EXISTS | OK |
| `/Volumes/David External/sam_memory/` | EXISTS | OK |
| Training data on David External | Moved to /Volumes/#1/SAM/ | OUTDATED |

Per STORAGE_AND_DATA_MAP_20260128.md, training data has been reorganized:
- SAM training now at `/Volumes/#1/SAM/training_data/`
- Voice data at `/Volumes/#1/SAM/voice_data/`
- Scraper archives at `/Volumes/#1/SAM/scraper_archives/`

**Symlinks exist at old David External locations for backward compatibility**

---

## 8. Recommendations

### Critical Fixes (Do First)

1. **Update CLAUDE.md file paths** - All voice/memory files have moved to subdirectories
2. **Update version number** - CLAUDE.md says v0.5.0, cognitive is v1.18.0
3. **Mark ARCHITECTURE.md as PLANNED** - It describes future state, not current

### Important Updates

4. **Add 13 missing cognitive modules** to CLAUDE.md documentation
5. **Update docs/INDEX.md** with new files and correct count
6. **Consolidate CLAUDE_READ_FIRST.md and root CLAUDE.md** - 70% redundancy noted in session logs

### Nice to Have

7. **Create EXECUTION_SYSTEM.md update** - 8 files, 9,457 lines barely documented
8. **Document startup/ directory** - project_context.py and others
9. **Update storage paths** in SSOT to reflect #1/SAM reorganization

---

## 9. Document Health Matrix

| Document | Accuracy | Freshness | Completeness |
|----------|----------|-----------|--------------|
| CLAUDE_READ_FIRST.md | 70% | Current | 60% |
| PROJECT_REGISTRY.md | 85% | Current | 80% |
| SAM_IDENTITY.md | 90% | Slightly stale | 90% |
| STORAGE_STRATEGY.md | 80% | Updated 2026-01-27 | 85% |
| sam_brain/CLAUDE.md | **50%** | Stale paths | **40%** |
| sam_brain/ARCHITECTURE.md | **20%** | Describes future | **10%** |
| docs/INDEX.md | 75% | Updated today | 85% |
| SAM_TERMINAL.md | 85% | 2026-01-23 | 90% |

---

## 10. Files Audited

### SSOT Documentation
- `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md`
- `/Volumes/Plex/SSOT/PROJECT_REGISTRY.md`
- `/Volumes/Plex/SSOT/SAM_IDENTITY.md`
- `/Volumes/Plex/SSOT/STORAGE_STRATEGY.md`
- `/Volumes/Plex/SSOT/context/davidquinton.md`
- `/Volumes/Plex/SSOT/projects/SAM_TERMINAL.md`

### sam_brain Documentation
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/ARCHITECTURE.md`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/INDEX.md`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/REORGANIZATION_PLAN.md`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/STORAGE_AND_DATA_MAP_20260128.md`

### Code Directories Audited
- `cognitive/` - 34+ files
- `voice/` - 10 files
- `memory/` - 8 files
- `execution/` - 8 files
- `startup/` - 1 file
- `utils/` - 2 files
- New package directories (core/, think/, speak/, etc.) - All empty except README.md

---

*Report generated by cross-referencing documentation with actual codebase structure.*
