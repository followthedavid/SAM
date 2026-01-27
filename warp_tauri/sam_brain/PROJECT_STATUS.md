# SAM Internal Projects Status

**Last Updated**: 2026-01-25

All SAM internal projects with status, dependencies, and path to evolution.

---

## Core Systems (Must Work)

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **SAM API** | sam_api.py | ✅ Working | 🟢 | Main entry point, port 8765 |
| **Orchestrator** | orchestrator.py | ✅ Working | 🟢 | Request routing |
| **MLX Cognitive** | cognitive/mlx_cognitive.py | ✅ Working | 🟢 | Local inference |
| **Semantic Memory** | semantic_memory.py | ✅ Working | 🟢 | Vector search |
| **Voice Pipeline** | voice_pipeline.py | ✅ Working | 🟢 | STT→TTS chain |
| **Terminal Coord** | terminal_coordination.py | ✅ Working | 🟢 | Multi-terminal awareness |

---

## Learning & Evolution

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **Exhaustive Learner** | exhaustive_learner.py | ✅ NEW | 🟡 | Comprehensive data ingestion |
| **Teacher Student** | teacher_student.py | ✅ Working | 🟡 | Claude curriculum |
| **Terminal Learning** | terminal_learning.py | ✅ NEW | 🟡 | Credit-free bridge |
| **Advanced Planner** | advanced_planner.py | ✅ NEW | 🟢 | Mindset training |
| **Knowledge Distill** | knowledge_distillation.py | 🔧 Partial | 🟡 | Capture Claude wisdom |
| **Auto Fix** | auto_fix.py | ✅ Working | 🟢 | Self-improvement |
| **SAM Intelligence** | sam_intelligence.py | ✅ Working | 🟡 | Self-awareness |

---

## Data Processing

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **Code Indexer** | code_indexer.py | ✅ Working | 🟢 | Codebase search |
| **Code Pattern Miner** | code_pattern_miner.py | ✅ Working | 🟡 | Learn patterns |
| **Data Quality** | data_quality.py | ✅ Working | 🟢 | Quality scoring |
| **Deduplication** | deduplication.py | ✅ Working | 🟢 | Remove dupes |
| **Context Manager** | context_manager.py | ✅ Working | 🟢 | Context window |
| **Parse ChatGPT** | parse_chatgpt.py | ✅ Working | 🟢 | Import history |

---

## Training Pipeline

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **Train LoRA** | train_roleplay_lora.py | ✅ Working | 🟢 | MLX fine-tuning |
| **Consolidate Training** | consolidate_training.py | ✅ Working | 🟢 | Merge datasets |
| **Feedback Loop** | feedback_loop.py | 🔧 Partial | 🟡 | Learn from feedback |

---

## Voice & Emotion

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **Voice Pipeline** | voice_pipeline.py | ✅ Working | 🟢 | Main voice |
| **Voice Output** | voice_output.py | ✅ Working | 🟢 | TTS engines |
| **Voice Settings** | voice_settings.py | ✅ Working | 🟢 | Config |
| **Emotion2Vec** | emotion2vec_mlx/ | ✅ Working | 🟢 | MLX emotion |
| **Prosody Control** | prosody_control.py | ✅ Working | 🟢 | Voice tone |

---

## Vision

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **Vision Engine** | cognitive/vision_engine.py | ✅ Working | 🟢 | Multi-tier |
| **Smart Vision** | cognitive/smart_vision.py | ✅ Working | 🟢 | Auto-routing |
| **Apple OCR** | apple_ocr.py | ✅ Working | 🟢 | Free OCR |
| **Vision Server** | vision_server.py | ✅ Working | 🟢 | Port 8766 |

---

## System Integration

| Project | File | Status | Health | Notes |
|---------|------|--------|--------|-------|
| **System Orchestrator** | system_orchestrator.py | ✅ NEW | 🟢 | Control everything |
| **Approval Queue** | approval_queue.py | ✅ Working | 🟢 | Human approval |
| **Command Classifier** | command_classifier.py | ✅ Working | 🟢 | Intent detection |
| **Command Proposer** | command_proposer.py | ✅ Working | 🟢 | Suggest actions |
| **Claude Orchestrator** | claude_orchestrator.py | ✅ Working | 🟢 | Escalation |

---

## Scrapers (18 Total)

| Scraper | Status | Items | Priority | Auto-Refresh |
|---------|--------|-------|----------|--------------|
| **apple_dev_collector** | ✅ Running | 507+ | P1 | Weekly |
| **parallel_code_scraper** | ✅ Running | 1,226 | P1 | Daily |
| **code_collector** | ✅ Working | ~10K | P1 | Daily |
| **nifty_ripper** | ⏸️ Paused | 2,191 | P3 | - |
| **ao3_ripper** | ⏸️ Paused | 3,273 | P3 | - |
| **ao3_roleplay_ripper** | ⏸️ Paused | - | P3 | - |
| **firstview_ripper** | ⏸️ Paused | 255 | P4 | - |
| **wwd_scraper** | ⏸️ Paused | 6,171 | P4 | - |
| **literotica_ripper** | 🔧 Needs work | - | P3 | - |
| **dark_psych_ripper** | 🔧 Needs work | - | P3 | - |
| **reddit_roleplay_ripper** | 🔧 Needs work | - | P3 | - |
| **gq_esquire_ripper** | 🔧 Needs work | - | P4 | - |
| **interview_ripper** | 🔧 Needs work | - | P4 | - |
| **high_impact_datasets** | ✅ Working | - | P2 | - |
| **download_instruction_data** | ✅ Working | - | P2 | - |
| **build_training_data** | ✅ Working | - | P2 | - |

---

## Control Centers

| Project | File | Status | Notes |
|---------|------|--------|-------|
| **SAM Control Center** | sam_control_center.py | ✅ NEW | Visual dashboard |
| **Live Status** | live_status.py | ✅ NEW | Scraper monitor |
| **Data Hub** | data_hub.py | ✅ NEW | Training data view |

---

## Documentation (Created This Session)

| Document | Purpose |
|----------|---------|
| **PARITY_ROADMAP.md** | Multi-phase plan to 100% parity |
| **GAPS_ANALYSIS.md** | What's missing everywhere |
| **UNIFIED_VISION.md** | The complete SAM vision |
| **PROJECT_STATUS.md** | This file |

---

## Evolution Plan

### Phase 1: Foundation (Now - Week 2)
- [x] Exhaustive data ingestion
- [x] Advanced planning training
- [x] System orchestrator
- [ ] Complete first LoRA training run
- [ ] Verify all scrapers working

### Phase 2: Cognitive Depth (Week 3-4)
- [ ] Chain-of-thought training
- [ ] Multi-turn coherence
- [ ] Uncertainty awareness
- [ ] Quality metrics dashboard

### Phase 3: Full Automation (Month 2)
- [ ] 24/7 learning daemon
- [ ] Auto-evolution pipeline
- [ ] Claude distillation continuous
- [ ] Self-improvement cycle

### Phase 4: Mastery (Month 3+)
- [ ] Proactive suggestions
- [ ] Emotional model depth
- [ ] Ambient awareness
- [ ] True continuity

---

## Quick Commands

```bash
# Check all systems
python3 system_orchestrator.py status

# Start priority scrapers
python3 system_orchestrator.py scraper start

# View training data
python3 exhaustive_learner.py status

# Run learning cycle
python3 terminal_learning.py start

# Generate planning examples
python3 advanced_planner.py teach

# Control center (live dashboard)
python3 sam_control_center.py
```

---

## Health Legend

- 🟢 Healthy - Working well, no issues
- 🟡 Attention - Works but needs optimization
- 🔴 Critical - Broken or major issues
- 🔧 Partial - Some features work

---

## Dependencies Between Projects

```
sam_api.py
    ├── orchestrator.py
    │   ├── cognitive/mlx_cognitive.py
    │   ├── semantic_memory.py
    │   ├── voice_pipeline.py
    │   └── vision_engine.py
    │
    ├── terminal_coordination.py
    │   └── terminal_learning.py
    │       └── teacher_student.py
    │
    └── system_orchestrator.py
        ├── ScraperManager (all scrapers)
        └── ARRManager (media stack)

exhaustive_learner.py
    ├── parse_chatgpt.py (input)
    ├── data_quality.py
    ├── deduplication.py
    └── train_roleplay_lora.py (output)
```

---

## What Needs Attention

### Immediate (This Week)
1. **Database locking** - Processing steps conflict with status checks
2. **Apple dev schema** - 'code' column doesn't exist in current table
3. **Scraper health checks** - Some scrapers need updates

### Soon (This Month)
1. **ARR stack** - Set up docker configs
2. **Continuous learning** - Daemon for 24/7 operation
3. **Quality metrics** - Dashboard for training progress

### Future
1. **Proactive help** - SAM suggests before asked
2. **Ambient awareness** - Watch screen context
3. **Multi-modal fusion** - Seamless text/voice/vision
