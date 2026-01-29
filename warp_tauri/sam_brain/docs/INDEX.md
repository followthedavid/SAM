# SAM Documentation Index

**Last Updated:** 2026-01-28
**Total Specs:** 33 documents

---

## Quick Start

| Document | Description |
|----------|-------------|
| [CLAUDE.md](../CLAUDE.md) | Primary reference - architecture, APIs, usage |
| [ROADMAP.md](ROADMAP.md) | Development roadmap and milestones |
| [PHASE3_VISION.md](PHASE3_VISION.md) | Phase 3 strategic vision |

---

## Core System Specifications

### Memory & Knowledge

| Document | Size | Description |
|----------|------|-------------|
| [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) | 35 KB | Vector embeddings, semantic search, fact storage |
| [FACT_SCHEMA.md](FACT_SCHEMA.md) | 33 KB | Structured knowledge storage schema |
| [MEMORY_AUDIT.md](MEMORY_AUDIT.md) | 14 KB | Memory system health audit |
| [CONTEXT_COMPRESSION.md](CONTEXT_COMPRESSION.md) | 12 KB | LLMLingua-style prompt compression |

### RAG (Retrieval-Augmented Generation)

| Document | Size | Description |
|----------|------|-------------|
| [RAG_SYSTEM.md](RAG_SYSTEM.md) | 27 KB | RAG architecture and pipelines |
| [RAG_AUDIT.md](RAG_AUDIT.md) | 15 KB | RAG system health audit |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | 28 KB | Project-aware context system |
| [PROJECT_CONTEXT_FORMAT.md](PROJECT_CONTEXT_FORMAT.md) | 18 KB | Context format specification |

### Voice & Audio

| Document | Size | Description |
|----------|------|-------------|
| [VOICE_SYSTEM.md](VOICE_SYSTEM.md) | 14 KB | Voice pipeline (STT, processing, TTS) |
| [VOICE_OUTPUT_AUDIT.md](VOICE_OUTPUT_AUDIT.md) | 16 KB | TTS engine comparison and audit |
| [VOICE_BENCHMARK.md](VOICE_BENCHMARK.md) | 2 KB | Voice latency metrics |

### Vision

| Document | Size | Description |
|----------|------|-------------|
| [VISION_CHAT.md](VISION_CHAT.md) | 10 KB | Multi-tier vision processing |
| [VISION_MEMORY_BENCHMARK.md](VISION_MEMORY_BENCHMARK.md) | 9 KB | Vision system RAM usage |

### Execution & Safety

| Document | Size | Description |
|----------|------|-------------|
| [EXECUTION_SYSTEM.md](EXECUTION_SYSTEM.md) | 22 KB | Safe command execution pipeline |
| [AUTO_FIX.md](AUTO_FIX.md) | 15 KB | Automatic error correction system |

---

## Training & Learning

| Document | Size | Description |
|----------|------|-------------|
| [TRAINING_PIPELINE.md](TRAINING_PIPELINE.md) | 14 KB | Training orchestration |
| [TRAINING_DATA.md](TRAINING_DATA.md) | 19 KB | Training data management |
| [TRAINING_DATA_SCHEMA.md](TRAINING_DATA_SCHEMA.md) | 14 KB | Training data format specification |
| [TRAINING_PIPELINE_AUDIT.md](TRAINING_PIPELINE_AUDIT.md) | 20 KB | Training system health audit |
| [DISTILLATION.md](DISTILLATION.md) | 36 KB | Knowledge distillation system |
| [DISTILLATION_FORMAT.md](DISTILLATION_FORMAT.md) | 19 KB | Distillation example format |
| [FEEDBACK_LEARNING.md](FEEDBACK_LEARNING.md) | 27 KB | User feedback integration |
| [FEEDBACK_FORMAT.md](FEEDBACK_FORMAT.md) | 28 KB | Feedback data format |

---

## Data Collection

| Document | Size | Description |
|----------|------|-------------|
| [SCRAPER_PIPELINE.md](SCRAPER_PIPELINE.md) | 32 KB | All 20 legacy + 29 Scrapy scrapers, daemon config |
| [DATA_ARSENAL_AUDIT.md](DATA_ARSENAL_AUDIT.md) | 13 KB | Data collection system audit |

---

## Performance & Analysis

| Document | Size | Description |
|----------|------|-------------|
| [TOKEN_USAGE_ANALYSIS.md](TOKEN_USAGE_ANALYSIS.md) | 12 KB | Token efficiency analysis |

---

## Storage & Infrastructure

| Document | Size | Description |
|----------|------|-------------|
| [STORAGE_AND_DATA_MAP_20260128.md](STORAGE_AND_DATA_MAP_20260128.md) | 32 KB | **Current** storage layout (post-migration) |
| [STORAGE_AND_DATA_MAP_20260127.md](STORAGE_AND_DATA_MAP_20260127.md) | 30 KB | Previous day's storage map (archive) |

---

## Audits & Session Logs

| Document | Size | Description |
|----------|------|-------------|
| [DATABASE_AUDIT_20260128.md](DATABASE_AUDIT_20260128.md) | 10 KB | Database health, token budget audit |
| [CODEBASE_AUDIT_20260127.md](CODEBASE_AUDIT_20260127.md) | 18 KB | Code health audit |
| [SESSION_LOG_20260128.md](SESSION_LOG_20260128.md) | 8 KB | Latest session work log |

---

## Document Categories

### By Purpose

- **Architecture Specs:** MEMORY_SYSTEM, RAG_SYSTEM, VOICE_SYSTEM, VISION_CHAT, EXECUTION_SYSTEM
- **Data Formats:** FACT_SCHEMA, TRAINING_DATA_SCHEMA, FEEDBACK_FORMAT, DISTILLATION_FORMAT, PROJECT_CONTEXT_FORMAT
- **Audits:** MEMORY_AUDIT, RAG_AUDIT, DATABASE_AUDIT, CODEBASE_AUDIT, TRAINING_PIPELINE_AUDIT, VOICE_OUTPUT_AUDIT, DATA_ARSENAL_AUDIT
- **Performance:** TOKEN_USAGE_ANALYSIS, VOICE_BENCHMARK, VISION_MEMORY_BENCHMARK
- **Session Logs:** SESSION_LOG_* (rolling daily)
- **Storage Maps:** STORAGE_AND_DATA_MAP_* (rolling daily)

### Freshness Guide

- **Daily Updated:** SESSION_LOG, STORAGE_AND_DATA_MAP
- **Weekly Review:** Audit documents
- **Stable References:** System specs, format docs

---

## Related Documentation

### SSOT (Single Source of Truth)

- `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md` - Master entry point
- `/Volumes/Plex/SSOT/MASTER_STATE.md` - Current system state
- `/Volumes/Plex/SSOT/projects/` - Per-project docs (20 files)
- `/Volumes/Plex/SSOT/context/davidquinton.md` - Session context

### Root-Level Docs

- `../CLAUDE.md` - Primary project README
- `../PROJECT_STATUS.md` - Component health matrix
- `../UNIFIED_VISION.md` - Strategic vision
- `../MASTER_TASK_LIST.md` - Comprehensive task tracking

---

## How to Use This Index

1. **New to SAM?** Start with [CLAUDE.md](../CLAUDE.md) for architecture overview
2. **Working on a system?** Find its spec doc in the categories above
3. **Debugging issues?** Check relevant audit docs
4. **Tracking changes?** See SESSION_LOG and STORAGE_AND_DATA_MAP
5. **Training SAM?** See Training & Learning section
