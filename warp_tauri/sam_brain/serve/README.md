# serve/ - External Interfaces

## What This Does
Exposes SAM's capabilities via HTTP API, CLI, and background services.

## Why It Exists
SAM needs to be accessible from:
- The Tauri app (HTTP)
- Terminal (CLI)
- Background services (daemons)
- Other scripts (API)

## When To Use
- Starting the SAM API server
- Using SAM from command line
- Setting up background learning/watching
- Adding a new way to interact with SAM

## How To Use
```bash
# Start HTTP API on port 8765
python -m sam.serve.http

# Use CLI
sam "What's the weather?"

# Start all daemons
launchctl load ~/Library/LaunchAgents/com.sam.*.plist
```

## Key Files
- `http.py` - REST API (port 8765) - main interface
- `cli.py` - Command-line interface
- `daemon.py` - Background service manager
- `voice.py` - Voice-specific API endpoints
- `vision.py` - Vision-specific API endpoints

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get response |
| `/api/voice/speak` | POST | Text to speech |
| `/api/vision/describe` | POST | Describe image |
| `/api/learn/status` | GET | Learning daemon status |
| `/api/health` | GET | Health check |

## Daemons
| Name | Purpose | Port |
|------|---------|------|
| com.sam.api | HTTP API | 8765 |
| com.sam.perpetual | Learning daemon | - |
| com.sam.autolearner | Claude session watcher | - |

## Dependencies
- **Requires:** All other packages (exposes them)
- **Required by:** External apps, scripts

## What Was Here Before
This consolidates:
- `sam_api.py` (5,658 lines) - split into routes
- `vision_server.py` (476 lines)
- `voice/voice_server.py` (499 lines)
- `sam_repl.py` (380 lines)
