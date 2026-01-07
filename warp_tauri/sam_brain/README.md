# SAM Brain

A local AI-powered coding assistant with **exhaustive project knowledge** (3,241 projects across 7 drives), custom-trained coding model, voice output, and autonomous background services.

## Quick Start

```bash
# Add aliases to your shell
source ~/ReverseLab/SAM/warp_tauri/sam_brain/sam_aliases.sh

# Run a command
sam "list files in current directory"
sam "git status"
sam "create a hello world script"

# API commands
python3 sam_api.py status      # System status
python3 sam_api.py projects    # All projects grouped by status
python3 sam_api.py search sam  # Search projects
python3 sam_api.py speak "Hello, I am SAM"  # Text-to-speech
```

## System Overview

| Metric | Value |
|--------|-------|
| Projects indexed | 3,241 |
| Drives scanned | 7 (local + Plex + David External + others) |
| Custom model | `sam-coder` (trained on your coding style) |
| Background daemon | `com.sam.brain` (launchd, auto-starts) |
| Voice engines | macOS TTS, Coqui, RVC (swappable) |

## Core Components

### Main Entry Points

| Script | Purpose |
|--------|---------|
| `sam` | Shell wrapper - main entry point |
| `sam.py` | Simple routing + direct execution |
| `sam_enhanced.py` | Project-aware version with memory |
| `sam_agent.py` | Full AI agent with tool execution |
| `sam_api.py` | JSON API for Tauri/GUI integration |

### Exhaustive Analysis (NEW)

| File | Purpose |
|------|---------|
| `exhaustive_analyzer.py` | Deep project scanner (all drives) |
| `exhaustive_analysis/master_inventory.json` | 3,241 projects with metadata |
| `exhaustive_analysis/MASTER_REPORT.md` | Human-readable summary |
| `exhaustive_analysis/FULL_PROJECT_CATALOG.md` | Complete project listing |

### Style Training (NEW)

| File | Purpose |
|------|---------|
| `style_trainer.py` | Extracts coding patterns for model training |
| `training_data/style_profile.json` | Your coding style (43% type hints, 47% f-strings) |
| `training_data/training_samples.jsonl` | 1,949 training examples |
| `Modelfile.sam-coder` | Ollama model definition with style |

### Voice Output (NEW)

| File | Purpose |
|------|---------|
| `voice_output.py` | TTS with swappable engines (macOS/Coqui/RVC) |
| `voice_config.json` | Voice settings (engine, voice, rate) |
| `voice_cache/` | Generated audio files |

### Project Management

| Script | Purpose |
|--------|---------|
| `project_scanner.py` | Discovers projects across all drives |
| `project_manager.py` | Organizes, searches, exports projects |
| `project_browser.py` | Interactive TUI for browsing projects |
| `projects.json` | Active project registry |

### Background Services

| Script | Purpose |
|--------|---------|
| `brain_daemon.py` | **Main daemon** - Ollama keeper, memory consolidation |
| `sam_daemon.py` | Nightly automation tasks |
| `sam_watch.py` | File watcher for auto-actions |
| `smart_router.py` | Routes to local vs external LLMs |
| `ollama_keeper.py` | Keeps Ollama model warm |
| `semantic_memory.py` | Vector-based memory with consolidation |

### Training & Learning

| Script | Purpose |
|--------|---------|
| `training_data_collector.py` | Collects interaction data for fine-tuning |
| `finetune_mlx.py` | MLX-based model fine-tuning |
| `train_8gb.py` | Memory-efficient training |
| `mlx_server.py` | Local MLX model server |

## Architecture

```
User Input
    │
    ▼
┌─────────────────┐
│  sam (shell)    │  <- Main entry point
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ sam_enhanced.py │  <- Project detection + routing
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────────┐
│ Local │ │ External  │
│Ollama │ │ LLM/API   │
└───────┘ └───────────┘
```

## Configuration

### Projects Registry (`projects.json`)

```json
{
  "projects": [
    {
      "name": "sam_brain",
      "path": "/Users/.../sam_brain",
      "type": "python",
      "description": "SAM Brain AI assistant",
      "keywords": ["ai", "assistant", "coding"]
    }
  ],
  "default_project": "sam_brain"
}
```

### Shell Aliases

After sourcing `sam_aliases.sh`:

| Alias | Command |
|-------|---------|
| `sam` | Main SAM command |
| `s` | Short for sam |
| `sam-projects` | Project manager |
| `sam-scan` | Scan for projects |
| `sam-watch` | File watcher |
| `sam-agent` | Full AI agent |
| `sam-cd <name>` | CD into project by name |

## Background Daemon

The brain daemon (`brain_daemon.py`) runs continuously and manages:

| Task | Interval | Description |
|------|----------|-------------|
| Ollama warm-up | 5 min | Keeps model in memory for fast response |
| Memory consolidation | 30 min | Compresses old memories |
| Health check | 1 min | Monitors Ollama, auto-restarts if down |

### Daemon Commands

```bash
# Check if running
launchctl list com.sam.brain

# View logs
tail -f /tmp/sam_brain_daemon.stdout.log
tail -f /tmp/sam_brain_daemon.stderr.log

# Restart daemon
launchctl stop com.sam.brain
launchctl start com.sam.brain

# Manual run (foreground)
python3 brain_daemon.py run
```

### Launchd Auto-Start

The daemon auto-starts on login via launchd:

```bash
# Load the service (already done)
launchctl load ~/Library/LaunchAgents/com.sam.brain.plist

# Check status - should show PID
launchctl list com.sam.brain

# Unload (stop permanently)
launchctl unload ~/Library/LaunchAgents/com.sam.brain.plist
```

### Nightly Tasks (sam_daemon.py)

Additional scheduled tasks for maintenance:

| Task | Interval | Description |
|------|----------|-------------|
| `scan_projects` | 24h | Discover new projects |
| `export_projects` | 24h | Update projects.json |
| `cleanup_memory` | Weekly | Archive old interactions |
| `health_check` | 1h | Check disk space |

## API Server

Start the JSON API server for external integrations:

```bash
python3 sam_api.py server 8765
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status (project count, Ollama, model loaded) |
| GET | `/api/projects` | All projects grouped by status (active/recent/stale) |
| GET | `/api/memory` | Get interaction history |
| GET | `/api/query?q=...` | Query SAM |
| GET | `/api/search?q=...` | Search projects by name/path/tags |
| GET | `/api/categories` | Project categories (sam_core, voice, ml, etc.) |
| GET | `/api/starred` | Get starred/favorite projects |
| POST | `/api/query` | Query SAM (JSON body) |

### CLI Commands

```bash
python3 sam_api.py status       # Full system status
python3 sam_api.py projects     # Projects by status
python3 sam_api.py search voice # Search for "voice" projects
python3 sam_api.py categories   # Category breakdown
python3 sam_api.py starred      # Starred projects only
python3 sam_api.py speak "text" # Text-to-speech
python3 sam_api.py voices       # List available voices
python3 sam_api.py server 8765  # Start HTTP server
```

### Example API Responses

```bash
# Check status
curl http://localhost:8765/api/status
# Returns: project_count, active_projects, starred_projects,
#          ollama_running, sam_coder_loaded, drives_scanned

# Search projects
curl "http://localhost:8765/api/search?q=voice"
# Returns: matching projects with name, path, status, languages
```

## Voice Output

SAM can speak responses using text-to-speech. Three engines are supported:

| Engine | Speed | Quality | Setup |
|--------|-------|---------|-------|
| `macos` | Instant | Good | Built-in (default) |
| `coqui` | 2-3s | Natural | `pip install TTS` |
| `rvc` | 5s | Custom voice | Needs trained model |

### Voice Commands

```bash
# Speak text (plays audio)
python3 voice_output.py speak "Hello, I am SAM"

# Use different voice
python3 voice_output.py speak "Hello" --voice Samantha

# Save without playing
python3 voice_output.py speak "Hello" --output /tmp/hello.aiff --no-play

# List available voices
python3 voice_output.py list-voices

# Test all voices
python3 voice_output.py test

# Configure default settings
python3 voice_output.py config --voice Daniel --rate 180
```

### API Integration

```bash
# Via sam_api.py
python3 sam_api.py speak "Build completed successfully"
python3 sam_api.py voices  # List English voices

# Query with voice (speaks response)
# In sam_api.py, use api_query(query, speak=True)
```

### Switching to Custom Voice (RVC)

When your Dustin Steele RVC model is ready:

```bash
# Edit voice_config.json
{
  "engine": "rvc",
  "rvc_model": "/path/to/dustin_steele.pth"
}

# Or via CLI
python3 voice_output.py config --engine rvc
```

## Tauri Integration

SAM Brain integrates with the SAM Tauri app:

| Command | Function |
|---------|----------|
| `sam_query` | Process natural language queries |
| `sam_projects` | Get project list with categories |
| `sam_status` | System status (projects, Ollama, model) |
| `sam_search` | Search projects |
| `sam_speak` | Text-to-speech |

These are defined in `brain.rs` and call the Python API.

## File Structure

```
sam_brain/
├── sam                      # Shell entry point
├── sam.py                   # Simple router
├── sam_enhanced.py          # Enhanced with projects
├── sam_agent.py             # Full AI agent
├── sam_api.py               # JSON API server (main interface)
│
├── brain_daemon.py          # Background daemon (Ollama keeper)
├── ollama_keeper.py         # Keeps model warm
├── semantic_memory.py       # Vector memory + consolidation
│
├── exhaustive_analyzer.py   # Deep project scanner
├── exhaustive_analysis/     # Analysis output
│   ├── master_inventory.json   # 3,241 projects
│   ├── MASTER_REPORT.md        # Summary
│   └── FULL_PROJECT_CATALOG.md # Complete listing
│
├── style_trainer.py         # Coding style extractor
├── Modelfile.sam-coder      # Ollama model definition
├── training_data/           # Training output
│   ├── style_profile.json      # Your coding style
│   └── training_samples.jsonl  # 1,949 examples
│
├── voice_output.py          # TTS engine (macOS/Coqui/RVC)
├── voice_config.json        # Voice settings
├── voice_cache/             # Generated audio files
│
├── project_scanner.py       # Quick project discovery
├── project_manager.py       # Project organization
├── project_browser.py       # TUI browser
├── projects.json            # Active projects
│
├── smart_router.py          # LLM routing
├── sam_daemon.py            # Nightly automation
├── sam_watch.py             # File watcher
├── sam_chat.py              # Interactive chat
│
├── sam_aliases.sh           # Shell aliases
├── memory.json              # Interaction history
│
└── archive/                 # Superseded files
```

## Dependencies

**Required:**
- Python 3.9+
- Ollama with `sam-coder` model (created from `qwen2.5-coder:1.5b`)

**Optional:**
- `numpy` - For memory consolidation (daemon)
- `TTS` (Coqui) - For natural voice synthesis
- MLX - For Apple Silicon training

## Troubleshooting

### Ollama not responding

```bash
# Check if running
curl http://localhost:11434/api/tags

# Check if sam-coder is loaded
ollama list | grep sam-coder

# Start Ollama
ollama serve

# The daemon will auto-restart it if it crashes
launchctl list com.sam.brain
```

### Custom model not found

```bash
# Recreate sam-coder model
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
ollama create sam-coder -f Modelfile.sam-coder
```

### Projects not loading

```bash
# Check inventory exists
cat exhaustive_analysis/master_inventory.json | head

# Re-scan all drives
python3 exhaustive_analyzer.py --rescan
```

### Daemon not starting

```bash
# Check launchd status
launchctl list com.sam.brain

# View logs
tail -f /tmp/sam_brain_daemon.stdout.log
tail -f /tmp/sam_brain_daemon.stderr.log

# Reload service
launchctl unload ~/Library/LaunchAgents/com.sam.brain.plist
launchctl load ~/Library/LaunchAgents/com.sam.brain.plist
```

### Voice not working

```bash
# Test macOS TTS
say "Hello"

# Check voice config
cat voice_config.json

# List available voices
python3 voice_output.py list-voices
```

---

*Generated: 2026-01-06 | Projects: 3,241 | Drives: 7 | Model: sam-coder*
