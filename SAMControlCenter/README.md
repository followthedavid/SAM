# SAM Control Center

Native macOS SwiftUI application for interacting with SAM (Self-improving AI Assistant).

## Features

### 5 Tabs

| Tab | Purpose | Backend |
|-----|---------|---------|
| **Chat** | Talk to SAM directly (+ image analysis) | `sam_api.py` → MLX Qwen2.5 |
| **Roleplay** | Character interactions | `sam_api.py` → MLX with personality |
| **Control** | Service management | `unified_daemon.py` |
| **Code** | Dual Claude terminals | `multi_role_orchestrator.py` |
| **Voice** | Voice cloning & RVC training | RVC pipeline |

### Menu Bar
- Brain icon shows health status (green = healthy, orange = degraded)
- Quick access to services and actions
- Click to open dropdown or Control Center window

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SAMControlCenter.app                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐           │
│  │  Chat   │ │ Roleplay │ │ Control │ │  Code  │           │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └───┬────┘           │
└───────┼───────────┼────────────┼──────────┼─────────────────┘
        │           │            │          │
        ▼           ▼            ▼          ▼
   ┌─────────────────────┐  ┌─────────┐  ┌──────────────┐
   │    sam_api.py       │  │ daemon  │  │ orchestrator │
   │    (port 8765)      │  │ state   │  │   socket     │
   │                     │  │ file    │  │              │
   │  /api/orchestrate   │  │         │  │              │
   └──────────┬──────────┘  └────┬────┘  └──────┬───────┘
              │                  │               │
              ▼                  ▼               ▼
        ┌───────────┐     ┌───────────┐    ┌─────────────┐
        │ MLX Brain │     │ Services  │    │ Claude Code │
        │ + LoRA    │     │ (managed) │    │  Terminals  │
        └───────────┘     └───────────┘    └─────────────┘
```

## Requirements

### Dependencies
- macOS 14.0+ (Sonoma)
- Swift 5.9+
- SAM backend services running

### Backend Services

1. **SAM API** (required for Chat/Roleplay):
   ```bash
   cd ~/ReverseLab/SAM/warp_tauri/sam_brain
   python3 sam_api.py server 8765
   ```

2. **Unified Daemon** (required for Control):
   ```bash
   cd ~/ReverseLab/SAM/warp_tauri/sam_brain
   python3 unified_daemon.py start
   ```

3. **Orchestrator** (required for Code):
   ```bash
   cd ~/ReverseLab/SAM/warp_tauri/sam_brain
   python3 multi_role_orchestrator.py server
   ```

## Building

```bash
cd ~/ReverseLab/SAM/SAMControlCenter
swift build
```

## Running

```bash
./.build/debug/SAMControlCenter
```

Or for release build:
```bash
swift build -c release
./.build/release/SAMControlCenter
```

## File Structure

```
SAMControlCenter/
├── Package.swift           # Swift package manifest
├── README.md               # This file
└── Sources/
    ├── SAMControlCenterApp.swift   # App entry, SAMState, models
    └── ContentView.swift           # All views (tabs, components)
```

## API Endpoints Used

### sam_api.py (port 8765)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/orchestrate` | POST | Chat and roleplay |
| `/api/status` | GET | System status |

**Chat Request:**
```json
POST /api/orchestrate
{"message": "Hello SAM"}
```

**Response:**
```json
{
  "success": true,
  "response": "Hey there! What's up?",
  "route": "chat",
  "model": "mlx-1.5b"
}
```

### State Files

| File | Purpose |
|------|---------|
| `~/.sam/daemon/state.json` | Service status |
| `/tmp/sam_multi_orchestrator.sock` | Orchestrator IPC |

## Tabs in Detail

### Chat Tab
- Direct conversation with SAM
- Uses MLX Qwen2.5-1.5B with trained LoRA adapter
- Messages appear as bubbles with timestamps
- SAM's personality: cocky, flirty, helpful

### Roleplay Tab
- Select character from sidebar
- Characters: SAM (default), Custom
- Contextual roleplay interactions
- Purple accent theme

### Control Tab
- Grid of service cards
- Start/Stop individual services
- System resources (RAM, CPU)
- Quick actions: Start All, Stop All, Refresh

**Services Managed:**
- SAM Brain (MLX inference) - Critical
- Orchestrator (Claude coordination) - Critical
- Scrapers (data collection) - High
- Training Pipeline - Medium
- Dashboard - Low

### Code Tab
- Launch dual Claude terminals
- Builder (left) + Reviewer (right)
- Orchestrator status indicator
- Handoff protocol: `[HANDOFF:ROLE]`

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ⌘1 | Chat tab |
| ⌘2 | Roleplay tab |
| ⌘3 | Control tab |
| ⌘4 | Code tab |
| ⌘Q | Quit |

## Troubleshooting

### Chat not working
1. Check if sam_api.py is running: `curl http://localhost:8765/api/status`
2. Start it: `python3 sam_api.py server 8765`

### Services show "stopped" incorrectly
1. Check daemon: `python3 unified_daemon.py status`
2. Verify state file: `cat ~/.sam/daemon/state.json`

### Dual terminals not launching
1. Check orchestrator: `ls /tmp/sam_multi_orchestrator.sock`
2. Start it: `python3 multi_role_orchestrator.py server`

### Window doesn't open
1. Click brain icon in menu bar
2. Select "Open Control Center"
3. Or click app icon in Dock

## Design

- **Liquid Glass**: `.ultraThinMaterial` backgrounds
- **Dark Theme**: Subtle animated gradient
- **SF Symbols**: Native Apple iconography
- **Accent Colors**: Cyan (chat), Purple (roleplay), Green/Red (control)

## Image Analysis (Phase 3.1.8)

The Chat tab supports image analysis via drag & drop, paste, or file picker.

### Progress Indicator
When analyzing images, the UI shows:
- **Elapsed time**: Real-time counter showing how long analysis has taken
- **Phase status**: Current stage (Preparing, Loading model, Analyzing, etc.)
- **Progress bar**: Estimated completion (based on typical 60s processing)
- **Helpful hints**: After 15s, shows "Vision models need ~30-60s for detailed analysis"

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vision/analyze` | POST | Non-streaming image analysis |
| `/api/vision/stream` | POST | SSE streaming analysis (token-by-token) |

**Analyze Request:**
```json
POST /api/vision/analyze
{
  "image_base64": "...",
  "prompt": "What's in this image?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "I can see...",
  "analysis": "I can see...",
  "processing_time_ms": 45000,
  "model_used": "nanollava"
}
```

### Streaming (SSE)

The `/api/vision/stream` endpoint provides real-time progress:

```javascript
// SSE events:
{"status": "loading", "message": "Loading vision model..."}
{"status": "analyzing", "elapsed_ms": 5000}
{"token": "I "}
{"token": "can "}
{"token": "see "}
// ... more tokens ...
{"done": true, "response": "I can see...", "processing_time_ms": 45000}
```

### Technical Notes

- **Streaming supported**: mlx_vlm has `stream_generate` for token-by-token output
- **Model loading**: First analysis takes 30-60s to load nanoLLaVA (4GB model)
- **Subsequent**: After model is loaded, analysis is faster (~10-30s)
- **Vision Server**: For fastest performance, run `python3 vision_server.py 8766`
- **Memory**: Vision model uses ~4GB RAM; unloads automatically when idle

## Version History

- **1.1.0** (2026-01-25): Image analysis with streaming support (Phase 3.1.8)
- **1.0.0** (2026-01-20): Initial release with 4 tabs
