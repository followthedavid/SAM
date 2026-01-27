# SAM Vision Chat Documentation

**Phase 3.1.10 - Vision Capabilities Reference**

---

## 1. Overview

SAM sees images through a **smart 4-tier architecture** that routes tasks to the most
efficient handler, optimized for 8GB RAM.

```
User Input (image + prompt)
          |
    Task Classifier
          |
    +-----+-----+-----+-----+
    |     |     |     |     |
TIER 0  TIER 1  TIER 2  TIER 3
  |       |       |       |
Apple   CoreML  nanoLLaVA Claude
Vision   Face    1.5B    Terminal
PIL      Detect  VLM     Bridge
  |       |       |       |
0 RAM   200MB   4GB     0 local
<2 sec  <1 sec  ~60s    varies
          |
    Vision Memory (SQLite Cache)
          |
    Response + Metadata
```

### Key Features
- **Zero-cost OCR**: Apple Vision extracts text in <2s, no ML overhead
- **Smart routing**: Auto-selects cheapest tier for the task
- **Vision memory**: SQLite cache avoids reprocessing
- **Follow-up questions**: Ask about previous images without re-sending
- **Claude escalation**: Complex reasoning routes to Claude

### Core Files
| File | Purpose |
|------|---------|
| `cognitive/smart_vision.py` | 4-tier routing, task classification |
| `cognitive/vision_engine.py` | Model management, processing |
| `cognitive/vision_client.py` | HTTP + Python client library |
| `apple_ocr.py` | Apple Vision OCR wrapper |
| `vision_server.py` | Persistent server (port 8766) |

---

## 2. Supported Formats and Input Methods

### Image Formats
PNG, JPEG, WebP, GIF (first frame), BMP, TIFF, HEIC (requires pyheif)

### Input Methods

**File Path:**
```python
result = client.process("/path/to/image.png", "What is this?")
```

**Base64 Encoded:**
```python
with open("photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
result = client.process(b64, "Describe this")
```

**Tauri GUI:**
- Drag & drop into chat
- Cmd+V paste clipboard
- Upload button
- Screenshot capture

**Raw Bytes (Python):**
```python
client = DirectVisionClient()
result = client.process(image_bytes, "What is this?")
```

---

## 3. Vision Tiers

### TIER 0: ZERO_COST
**Handler**: Apple Vision, PIL | **RAM**: 0 | **Speed**: <2s

| Task | Keywords | Handler |
|------|----------|---------|
| OCR | read, text, ocr, words, says | Apple Vision |
| Color | color, colour, hue, shade, rgb | PIL |

```python
result = client.ocr("/tmp/screenshot.png")  # ~22ms
result = client.smart("/tmp/photo.jpg", "What color is this?")
```

### TIER 1: LIGHTWEIGHT
**Handler**: CoreML, Apple Vision | **RAM**: ~200MB | **Speed**: <1s

| Task | Keywords | Handler |
|------|----------|---------|
| Face detection | face, person, who, people | Apple Vision |
| Basic description | what, is this, quick | Heuristics |

```python
result = client.smart("/tmp/group.jpg", "How many people?")
# "3 faces detected in the image."
```

### TIER 2: LOCAL_VLM
**Handler**: nanoLLaVA 1.5B (MLX) | **RAM**: ~4GB | **Speed**: 50-70s

| Task | Keywords | Handler |
|------|----------|---------|
| Detailed description | describe, detail, everything | nanoLLaVA |
| Object detection | find, locate, detect, where | nanoLLaVA |

```python
result = client.smart("/tmp/landscape.jpg", "Describe everything")
# Processing time: ~55s
```

### TIER 3: CLAUDE
**Handler**: Terminal bridge | **RAM**: 0 local | **Speed**: varies

| Task | Keywords | Handler |
|------|----------|---------|
| Code review | code, programming, bug, error | Claude |
| UI analysis | ui, interface, button, screen | Claude |
| Reasoning | why, explain, analyze, compare | Claude |

```python
result = client.smart("/tmp/code.png", "Find bugs in this code")
```

### Force Specific Tier
```python
result = client.smart("/tmp/photo.jpg", "...", force_tier="LOCAL_VLM")
```

---

## 4. API Endpoints

Base URL: `http://localhost:8765`

### Smart Vision (Recommended)

**POST /api/vision/smart** - Auto-routed processing
```json
{"image_path": "/tmp/img.png", "prompt": "What is this?", "force_tier": null, "skip_cache": false}
```
Response: `{"success": true, "response": "...", "tier_used": "ZERO_COST", "processing_time_ms": 22}`

**GET /api/vision/smart?path=...&prompt=...** - Query param version

**GET /api/vision/smart/stats** - Cache statistics

### Direct Endpoints

**POST /api/vision/process** - Direct VLM (nanoLLaVA)
```json
{"image_path": "...", "prompt": "...", "max_tokens": 150}
```

**POST /api/vision/analyze** - Non-streaming (Swift UI)
```json
{"image_base64": "...", "prompt": "Describe this"}
```

**POST /api/vision/stream** - SSE streaming (Phase 3.1.8)

**POST /api/vision/describe** - Detail levels: quick/medium/detailed

**POST /api/vision/detect** - Object detection with optional target

**POST /api/vision/ocr** - Apple Vision text extraction (fastest)
```json
{"image_path": "/tmp/screenshot.png"}
```
Response: `{"text": "...", "lines": [...], "processing_time_ms": 22}`

### Image Context (Follow-ups)

**GET /api/image/context** - Get current context
**GET /api/image/context/clear** - Clear context
**GET /api/image/followup/check?q=...** - Check if follow-up
**POST /api/image/chat** - Unified chat (new images + follow-ups)

### Info Endpoints

**GET /api/vision/models** - Available models
**GET /api/vision/stats** - Engine statistics

---

## 5. Follow-up Question Support

Phase 3.1.5: Ask questions about previously shared images without re-sending.

### How It Works
1. User sends image + query
2. SAM stores context (description, metadata) for 5 minutes
3. User asks follow-up: "What color is the car?"
4. SAM uses stored context - no reprocessing

### Detection Patterns

**Strong indicators**: "the image", "in it", "what does it say", "describe more"
**Medium**: "what is it", pronouns with context
**Position refs**: "background", "left", "right", "person", "object"

### Usage
```python
# Initial image
response = orch.image_chat("What is this?", image_path="/tmp/car.jpg")

# Follow-up (no image needed)
response = orch.image_chat("What color is the car?")

# Check/clear context
ctx = orch.get_image_context()
orch.clear_image_context()
```

### API
```bash
curl "http://localhost:8765/api/image/followup/check?q=What%20color%20is%20it"
```

---

## 6. Screenshot Capture

### Command Line
```bash
screencapture -x /tmp/screen.png    # Full screen
screencapture -w /tmp/window.png    # Window
screencapture -s /tmp/select.png    # Selection
```

### Python
```python
import subprocess, tempfile
from cognitive.vision_client import DirectVisionClient

def capture_and_analyze(prompt="What's on my screen?"):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    subprocess.run(["screencapture", "-s", path])
    return DirectVisionClient().smart(path, prompt)
```

### Tauri Integration
```javascript
const path = await invoke('capture_screenshot', { interactive: true });
const response = await fetch('/api/vision/smart', {
  method: 'POST',
  body: JSON.stringify({ image_path: path, prompt: 'What do you see?' })
});
```

### Best Practices
- Use PNG (lossless for text)
- Capture at native resolution
- Use `/api/vision/ocr` for text (fastest)
- Clean up temp files after processing

---

## 7. Memory Integration

### Vision Cache

**Location**: `~/.sam/vision_memory.db`

```sql
CREATE TABLE vision_cache (
    image_hash TEXT PRIMARY KEY,
    task_type TEXT, prompt TEXT, response TEXT,
    tier_used INTEGER, confidence REAL,
    created_at TEXT, access_count INTEGER
);
```

**Behavior**:
- Key: image hash + task type
- Cache hit: instant response
- No auto-expiry

### Commands
```bash
# View cache
sqlite3 ~/.sam/vision_memory.db "SELECT image_hash, task_type FROM vision_cache LIMIT 10;"

# Clear cache
rm ~/.sam/vision_memory.db

# Bypass cache
result = client.smart("/tmp/photo.jpg", "...", skip_cache=True)
```

### Semantic Memory
```python
from semantic_memory import SemanticMemory
memory = SemanticMemory()
memory.store(content=f"Image: {result.response}", memory_type="vision",
             metadata={"image_path": path, "tier_used": result.tier_used})
```

---

## 8. Troubleshooting

### Common Issues

**"Vision processing failed: timeout"**
- Need ~4GB free RAM for VLM
- Use lighter tier for simple tasks
```bash
pkill -f ollama  # Stop if running
```

**"Apple Vision OCR failed"**
```bash
pip install pyobjc-framework-Vision pyobjc-framework-Quartz
```

**"Cannot connect to localhost:8765"**
```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python3 sam_api.py server 8765
```

**"Vision server not available"**
```bash
python3 vision_server.py 8766  # Optional, falls back to CLI
```

**Out of Memory**
```bash
pkill -f ollama
pkill -f "Docker Desktop"
# Force ZERO_COST tier
```

**GPU Timeout**
System uses CLI (`python3 -m mlx_vlm generate`) to avoid GPU context issues.

### Debug Mode
```python
import logging
logging.getLogger("smart_vision").setLevel(logging.DEBUG)
```

### Performance Tips
1. Start vision server for repeated inference: `python3 vision_server.py 8766 &`
2. Use ZERO_COST tier when possible (OCR, colors)
3. Caching is on by default - saves ~60s per repeat
4. Close Docker Desktop (~2GB) before VLM
5. Use follow-up questions instead of re-analyzing

---

## Quick Reference

| Need | Tier | Speed | RAM |
|------|------|-------|-----|
| Read text | ZERO_COST | <2s | 0 |
| Colors | ZERO_COST | <1s | 0 |
| Face count | LIGHTWEIGHT | <1s | 200MB |
| Quick describe | LIGHTWEIGHT | <1s | 200MB |
| Detailed | LOCAL_VLM | ~60s | 4GB |
| Code review | CLAUDE | varies | 0 |

### Common curl Commands
```bash
# OCR
curl -X POST localhost:8765/api/vision/ocr -d '{"image_path":"/tmp/screen.png"}'

# Smart
curl -X POST localhost:8765/api/vision/smart -d '{"image_path":"/tmp/photo.jpg","prompt":"What is this?"}'

# Stats
curl localhost:8765/api/vision/smart/stats
```

### Python Quick Start
```python
from cognitive.vision_client import DirectVisionClient
client = DirectVisionClient()

text = client.ocr("/tmp/screenshot.png").response
result = client.smart("/tmp/photo.jpg", "What do you see?")
print(f"{result.tier_used}: {result.response}")
```

---

*Last Updated: January 2026 - Phase 3.1.10*
*SAM Brain v0.5.0 (Full Multi-Modal - MLX Native)*
