# SAM Development Roadmap

## Current Status: Phase 3.5 Complete

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Smart Vision (4-tier) | ✅ Done | Auto-routes to cheapest capable tier |
| Apple Vision OCR | ✅ Done | 100% accurate, instant, 0 RAM |
| Face Detection | ✅ Done | CoreML, <1 second |
| Color Analysis | ✅ Done | PIL, instant |
| nanoLLaVA VLM | ✅ Done | 60s, 4GB RAM, general understanding |
| Vision Caching | ✅ Done | SQLite, prevents reprocessing |
| SAM API | ✅ Done | HTTP server on port 8765 |
| Tauri GUI | ⚠️ Partial | Needs testing |

### What's Pending

| Feature | Status | Blocker |
|---------|--------|---------|
| Claude Escalation (Tier 3) | 🔄 Stubbed | Needs dual terminal bridge |
| Voice Input (Whisper) | ❌ Not started | — |
| Voice Output (TTS) | ⚠️ Partial | Needs integration |
| Full GUI Testing | ❌ Not done | — |

---

## Phase 4: Complete Core (Current Priority)

### 4.1 Claude Escalation Bridge
Connect Tier 3 vision to dual terminal Claude system.

```
Vision Request (complex)
        │
        ▼
  SmartVisionRouter
        │ (Tier 3)
        ▼
  escalation_handler.py
        │
        ▼
  Dual Terminal Bridge
        │
        ▼
  Claude Response
```

**Files to create:**
- `escalation_handler.py` - Bridge to dual terminal system

### 4.2 Voice Integration
- Whisper for speech-to-text
- TTS for responses
- Wake word detection (optional)

### 4.3 End-to-End Testing
- Test all API endpoints
- Test Tauri GUI
- Test vision through GUI
- Document any issues

---

## Phase 5: Multi-Device (Future)

### Architecture: Hub and Spoke

```
┌─────────────────────────────────────────────────────────────┐
│                     SAM DISTRIBUTED                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│   │  iPhone  │     │   iPad   │     │ Apple TV │           │
│   │  App     │     │   App    │     │   App    │           │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘           │
│        │                │                │                  │
│        └────────────────┼────────────────┘                  │
│                         │                                   │
│                         ▼                                   │
│              ┌─────────────────────┐                        │
│              │  Cloudflare Tunnel  │                        │
│              │  (sam.domain.com)   │                        │
│              └──────────┬──────────┘                        │
│                         │                                   │
│                         ▼                                   │
│              ┌─────────────────────┐     ┌──────────┐       │
│              │      Mac Mini       │     │  Watch   │       │
│              │   (SAM Brain Hub)   │◄────│ (sensors)│       │
│              │    Always On        │     └──────────┘       │
│              └─────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why Cloudflare Tunnel?
- Already have it set up ✓
- Works from anywhere (not just local network)
- Secure (HTTPS, no port forwarding)
- Reliable (no Multipeer Connectivity flakiness)
- Simple client apps (just HTTPS requests)

### Device Capabilities

| Device | Can Do | Can't Do |
|--------|--------|----------|
| iPhone | Voice I/O, camera, quick AI, notifications, **rendering** | Heavy LLM |
| iPad | Same as iPhone + better display, **rendering** | Heavy LLM |
| Apple TV | Background tasks, always-on, speakers, **rendering** | Camera, portable |
| Watch | Sensors, triggers, haptics | Any real processing |
| Mac Mini | LLM, VLM, memory, orchestration | Portable, **no rendering** |

### Critical: Keep Mac From Choking

Mac Mini (8GB) is already maxed with AI inference. **Do NOT render on Mac.**

```
WRONG:  Mac renders avatar → streams video → device displays
        (Mac GPU busy, bandwidth heavy, latency)

RIGHT:  Mac sends state → device renders locally
        (Mac GPU free for AI, minimal bandwidth)
```

**What Mac Sends:**
```json
{
  "response": "Hello! How can I help?",
  "emotion": "friendly",
  "action": "wave",
  "intensity": 0.8
}
```

**Device Handles:**
- Avatar rendering (60fps)
- Animations, lip sync
- UI, transitions
- Audio playback

**Benefits:**
- Mac RAM/GPU free for models
- Smooth visuals on device
- Works offline (avatar still responsive)
- Device GPUs are underutilized anyway

### Implementation Order

```
Phase 5.1: Expose SAM API via Cloudflare Tunnel
           └── Test from browser outside home network

Phase 5.2: iPhone App (SwiftUI)
           ├── Voice input → SAM API → Voice output
           ├── Camera → Vision API
           └── Local fallback when offline

Phase 5.3: iPad App (shared codebase with iPhone)

Phase 5.4: Apple TV App
           └── Voice control, display responses

Phase 5.5: Watch App (complications + voice)
           └── Quick queries, health data integration
```

### Security Considerations
- API key or device certificates
- Cloudflare Zero Trust (optional)
- Rate limiting
- Audit logging

---

## Phase 6: Advanced Features (Later)

### 6.1 Intelligent Routing
- Local network detection (use direct connection when home)
- Latency-aware routing
- Battery-aware on mobile

### 6.2 Distributed Processing
- iPhone/iPad handle quick tasks locally
- Escalate heavy tasks to Mac
- Apple TV for overnight batch jobs

### 6.3 Context Mesh
- Watch provides health/activity context
- iPhone provides location context
- All feeds into SAM's awareness

### 6.4 Proactive SAM
- SAM initiates conversations based on context
- "You seem stressed, heart rate is elevated"
- "Traffic is bad, leave 10 minutes early"

---

## Hardware Constraints

| Resource | Limit | Impact |
|----------|-------|--------|
| Mac Mini RAM | 8GB | One model at a time |
| iPhone RAM | 6GB | Small models only (~500MB) |
| GPU (Metal) | Shared | VLM blocks other GPU tasks |
| Storage | Internal limited | Large files → external drive |

### Memory Management Rules
1. Stop Ollama before VLM tasks
2. One heavy model at a time
3. Use tiered routing (cheap first)
4. Cache aggressively

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `sam_api.py` | Main API server |
| `cognitive/smart_vision.py` | 4-tier vision routing |
| `apple_ocr.py` | Apple Vision OCR |
| `vision_server.py` | Standalone vision server |
| `escalation_handler.py` | Claude bridge (TODO) |
| `start_sam.sh` | Startup script |

---

## Quick Commands

```bash
# Start SAM API
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python3 sam_api.py server 8765

# Test smart vision
curl -X POST http://localhost:8765/api/vision/smart \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/tmp/test.png", "prompt": "What is this?"}'

# Check status
curl http://localhost:8765/api/health

# View cache
sqlite3 ~/.sam/vision_memory.db "SELECT * FROM vision_cache;"
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-18 | Use Apple Vision for OCR | 100% accurate, instant, no RAM |
| 2026-01-18 | 4-tier routing | Don't waste 4GB RAM on simple tasks |
| 2026-01-18 | Cloudflare tunnel for multi-device | More reliable than local mesh |
| 2026-01-18 | Hub-and-spoke, not mesh | Simpler, fewer failure points |
| 2026-01-18 | Finish Mac app before multi-device | Foundation must be solid first |
