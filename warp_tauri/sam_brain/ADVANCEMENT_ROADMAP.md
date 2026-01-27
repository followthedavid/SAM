# SAM Advancement Roadmap

**Created:** 2026-01-17
**Current Version:** v1.3.1
**Goal:** Most advanced local AI companion possible on 8GB hardware

---

## Current State (Completed)

| Feature | Status | Notes |
|---------|--------|-------|
| Cognitive Pipeline | ✅ | MLX inference, quality validation |
| Memory System | ✅ | Semantic + conversation memory |
| Resource Management | ✅ | Prevents freezes, auto-unload |
| Proactive Notifications | ✅ | macOS alerts + voice |
| Frontend Integration | ✅ | Tauri GUI with SAM mode |
| Testing | ✅ | 124/127 tests passing (97.6%) |
| Documentation | ✅ | SYSTEM_STATUS.md updated |

---

## Phase 1: Intelligence Enhancement (Week 1-2)

### 1.1 Knowledge Distillation
**Goal:** Capture Claude's reasoning to improve SAM

```
User asks complex question → SAM tries → Escalates to Claude
                                              ↓
                              Claude's answer captured
                                              ↓
                              Extract: reasoning patterns
                                              ↓
                              Add to SAM training data
```

**Files to modify:**
- `knowledge_distillation.py` (exists, needs activation)
- `escalation_handler.py` (add capture hook)

**Effort:** Medium

### 1.2 Learning from Feedback
**Goal:** Improve based on 👍/👎 reactions

```
User: "That's wrong, the answer is X"
           ↓
SAM: Records correction
           ↓
Adjusts future confidence + training data
```

**Files to modify:**
- `cognitive/enhanced_learning.py`
- Add feedback endpoint to GUI

**Effort:** Medium

### 1.3 Cross-Session Memory
**Goal:** Remember everything across restarts

Current: Memory resets each session
Target: Persistent long-term facts about user

**Files to modify:**
- `conversation_memory.py` (enhance persistence)
- `semantic_memory.py` (better fact extraction)

**Effort:** Low-Medium

---

## Phase 2: Context Intelligence (Week 2-3)

### 2.1 Project-Aware Context Injection
**Goal:** SAM knows which project you're working on

```
User opens warp_tauri folder
           ↓
SAM: "I see you're in the SAM project.
      Last time you were fixing the streaming bug.
      There are 3 TODOs in mlx_cognitive.py"
```

**Implementation:**
- Watch working directory changes
- Inject project context into prompts
- Remember per-project state

**Files:**
- NEW: `project_context_watcher.py`
- Modify: `context_manager.py`

**Effort:** Medium

### 2.2 Dynamic RAG Enhancement
**Goal:** Retrieve relevant docs/code automatically

```
User asks about "voice output"
           ↓
RAG finds: voice_output.py, SAMVoice class, TTS docs
           ↓
Injects into context before generation
```

**Files:**
- `cognitive/enhanced_retrieval.py` (already exists)
- Need: Better document indexing

**Effort:** Medium-High

---

## Phase 3: Multi-Modal Integration (Week 3-4)

### 3.1 Vision in Chat
**Goal:** "What's in this screenshot?" works in main chat

```
User drops image into chat
           ↓
SAM: Uses vision_engine.py to analyze
           ↓
Responds with description + can answer questions
```

**Files:**
- `src/components/AIChatTab.vue` (add image drop)
- `cognitive/vision_engine.py` (already complete)
- `sam_api.py` (already has /api/vision/*)

**Effort:** Low-Medium

### 3.2 Voice I/O
**Goal:** Talk to SAM, SAM talks back

```
"Hey SAM" (wake word)
           ↓
Listen for command
           ↓
Process → Respond via TTS
```

**Components needed:**
- Wake word detection (Porcupine/Whisper)
- Continuous listening toggle
- Voice activity detection

**Effort:** High

---

## Phase 4: Autonomous Capabilities (Week 4-5)

### 4.1 Supervised Code Execution
**Goal:** SAM can run commands with approval

```
SAM: "I can fix this by running: npm install lodash"
     [Approve] [Deny] [Edit]
           ↓
User approves → SAM executes → Reports result
```

**Files:**
- `src/composables/useCodeExecution.ts` (exists)
- Need: Approval queue UI
- Need: Sandboxing for safety

**Effort:** Medium-High

### 4.2 Proactive Improvement Execution
**Goal:** SAM auto-fixes simple issues

```
SAM notices: "ESLint error in App.vue line 45"
           ↓
SAM: "I can auto-fix this. [Allow]"
           ↓
Runs: eslint --fix App.vue
           ↓
Reports: "Fixed 1 error"
```

**Restrictions:**
- Only safe commands (lint, format, build)
- User must enable per-project
- Rollback capability

**Effort:** High

---

## Phase 5: Data & Training (Ongoing)

### 5.1 Training Data Pipeline
**Goal:** Continuously gather high-quality training data

**Sources:**
- Claude conversation captures
- User corrections/feedback
- Code commit patterns
- Documentation ingestion

**Files:**
- `training_data_collector.py` (exists)
- `data_arsenal.py` (scraping framework)

**Effort:** High (ongoing)

### 5.2 Periodic Retraining
**Goal:** Improve SAM's LoRA adapter with new data

**Pipeline:**
1. Accumulate 1000+ new examples
2. Validate data quality
3. Fine-tune LoRA adapter
4. A/B test against old model
5. Deploy if better

**Effort:** High

---

## Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Knowledge Distillation | High | Medium | 🔴 P1 |
| Learning from Feedback | High | Medium | 🔴 P1 |
| Cross-Session Memory | Medium | Low | 🔴 P1 |
| Project Context | High | Medium | 🟡 P2 |
| Vision in Chat | Medium | Low | 🟡 P2 |
| Dynamic RAG | High | High | 🟡 P2 |
| Voice I/O | High | High | 🟢 P3 |
| Code Execution | High | High | 🟢 P3 |
| Auto-Improvements | Medium | High | 🟢 P3 |
| Training Pipeline | High | High | 🟢 P3 |

---

## Immediate Next Steps (Today/Tomorrow)

1. **Activate Knowledge Distillation**
   - Hook into escalation flow
   - Start capturing Claude reasoning

2. **Add Feedback UI**
   - 👍/👎 buttons on responses
   - Wire to learning system

3. **Enable Cross-Session Facts**
   - Persist user facts to disk
   - Load on startup

4. **Test Vision in Chat**
   - Verify vision API works
   - Add image drop to chat

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | 97.6% | >95% |
| Response Latency (warm) | ~30s | <10s |
| Memory Usage | ~1.2GB | <1.5GB |
| User Corrections/Day | N/A | <5 |
| Successful Escalations | N/A | >90% |
| Proactive Suggestions Used | N/A | >50% |

---

## Hardware Constraints

- **8GB RAM**: Max one model at a time
- **M2 Mac Mini**: MLX-optimized inference
- **External Storage**: Models + data on /Volumes/David External

These constraints drive the architecture:
- Aggressive context compression
- Smart model selection (1.5B default)
- Auto-unload to free memory
- Token limits based on resources

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Model OOM | Resource manager + auto-unload |
| Bad training data | Quality validation before training |
| Runaway commands | Approval queue + safe command list |
| Context overflow | Token budgets + compression |
| Notification spam | Cooldown system + smart filtering |

---

*This roadmap is a living document. Update as features complete.*
