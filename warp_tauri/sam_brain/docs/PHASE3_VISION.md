# Phase 3: Vision in Chat

## Overview
SAM can see and understand images through a **smart multi-tier vision system** that automatically routes tasks to the most efficient handler.

## Smart Vision Architecture (Phase 3.5)

### 4-Tier Routing System

```
                    User Request
                         │
                         ▼
                ┌─────────────────┐
                │  Task Classifier │
                │  (keyword-based) │
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        ▼                ▼                ▼                ▼
   ┌─────────┐     ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ TIER 0  │     │  TIER 1  │    │  TIER 2  │    │  TIER 3  │
   │ZERO_COST│     │LIGHTWEIGHT│    │LOCAL_VLM │    │ CLAUDE   │
   ├─────────┤     ├──────────┤    ├──────────┤    ├──────────┤
   │Apple    │     │CoreML    │    │nanoLLaVA │    │Dual      │
   │Vision   │     │Face Det  │    │1.5B VLM  │    │Terminal  │
   │PIL      │     │Basic     │    │          │    │Bridge    │
   │         │     │Classif.  │    │          │    │          │
   ├─────────┤     ├──────────┤    ├──────────┤    ├──────────┤
   │0 RAM    │     │~200MB    │    │4GB RAM   │    │0 local   │
   │<1 sec   │     │<1 sec    │    │~60 sec   │    │varies    │
   └─────────┘     └──────────┘    └──────────┘    └──────────┘
```

### Task → Tier Routing

| Task | Tier | Handler | Speed |
|------|------|---------|-------|
| OCR / Read text | ZERO_COST | Apple Vision | <2s |
| Color analysis | ZERO_COST | PIL | <1ms |
| Face detection | LIGHTWEIGHT | CoreML/Vision | <1s |
| Basic describe | LIGHTWEIGHT | Quick classifier | <1s |
| Object detection | LOCAL_VLM | nanoLLaVA | ~60s |
| Detailed describe | LOCAL_VLM | nanoLLaVA | ~60s |
| Code review | CLAUDE | Dual terminal | varies |
| UI analysis | CLAUDE | Dual terminal | varies |
| Complex reasoning | CLAUDE | Dual terminal | varies |

### Vision Memory (Caching)

Results are cached in SQLite (`~/.sam/vision_memory.db`):
- Same image + same task type = instant cache hit
- Prevents reprocessing identical requests
- Cache stats available via API

## API Endpoints

### Smart Vision (Recommended)

#### POST /api/vision/smart
Automatically routes to best tier.
```json
{
  "image_path": "/path/to/image.png",  // OR
  "image_base64": "iVBORw0KGgo...",
  "prompt": "What color is this?",
  "force_tier": "ZERO_COST",  // optional override
  "skip_cache": false
}
```

Response:
```json
{
  "success": true,
  "response": "The image is primarily red.",
  "tier_used": "ZERO_COST",
  "task_type": "color",
  "processing_time_ms": 1,
  "confidence": 0.95,
  "from_cache": false,
  "timestamp": "2026-01-18T..."
}
```

#### GET /api/vision/smart?path=...&prompt=...&tier=...&skip_cache=false
Same as POST, via query params.

#### GET /api/vision/smart/stats
Cache statistics.
```json
{
  "success": true,
  "stats": {
    "cached_images": 4,
    "total_cache_hits": 12,
    "db_path": "/Users/.../.sam/vision_memory.db"
  }
}
```

### Legacy Endpoints (Still Available)

#### POST /api/vision/process
Direct VLM processing (always uses nanoLLaVA).
```json
{
  "image_path": "/path/to/image.png",
  "image_base64": "iVBORw0KGgo...",
  "prompt": "What do you see?",
  "max_tokens": 150
}
```

#### POST /api/vision/ocr
Direct Apple Vision OCR.
```json
{
  "image_path": "/path/to/image.png",
  "image_base64": "..."
}
```

#### POST /api/vision/describe
Describe at detail level.
```json
{
  "image_path": "/path/to/image.png",
  "detail_level": "basic" | "medium" | "detailed"
}
```

#### POST /api/vision/detect
Object detection.
```json
{
  "image_path": "/path/to/image.png",
  "target": "cat"
}
```

#### GET /api/vision/models
List available vision models.

#### GET /api/vision/stats
Vision engine statistics.

## Performance Comparison

| Method | Time | RAM | Accuracy | Best For |
|--------|------|-----|----------|----------|
| Apple Vision OCR | 1-2s | 0 | ~100% | Text extraction |
| PIL Color | <1ms | 0 | 100% | Color analysis |
| CoreML Face | <1s | ~200MB | ~95% | Face detection |
| nanoLLaVA | 50-70s | 4GB | ~75% | General understanding |
| Claude (Tier 3) | varies | 0 local | ~95% | Complex reasoning |

## Files

| File | Purpose |
|------|---------|
| `cognitive/smart_vision.py` | Smart 4-tier routing system |
| `cognitive/vision_engine.py` | Legacy vision processing |
| `apple_ocr.py` | Apple Vision OCR wrapper |
| `vision_server.py` | Standalone vision HTTP server |
| `sam_api.py` | API endpoints |

## Configuration

### smart_vision.py
```python
# Task keywords for classification
TASK_KEYWORDS = {
    TaskType.OCR: ["read", "text", "ocr", "words", "says"],
    TaskType.COLOR: ["color", "colour", "hue", "shade", "rgb"],
    TaskType.FACE_DETECT: ["face", "person", "who", "people"],
    # ...
}

# Task → Tier mapping
TASK_ROUTING = {
    TaskType.OCR: VisionTier.ZERO_COST,
    TaskType.COLOR: VisionTier.ZERO_COST,
    TaskType.FACE_DETECT: VisionTier.LIGHTWEIGHT,
    TaskType.DETAILED_DESCRIBE: VisionTier.LOCAL_VLM,
    TaskType.REASONING: VisionTier.CLAUDE,
    # ...
}
```

## Troubleshooting

### GPU Timeout Errors
Vision uses CLI module execution (`python3 -m mlx_vlm generate`) to avoid GPU timeouts.

### Out of Memory
```bash
# Stop Ollama
pkill -f ollama

# Check memory hogs
ps aux -m | head -10

# Need ~4GB free for VLM
```

### Cache Issues
```bash
# View cache
sqlite3 ~/.sam/vision_memory.db "SELECT * FROM vision_cache LIMIT 5;"

# Clear cache
rm ~/.sam/vision_memory.db
```

## Usage Examples

### Python
```python
from sam_api import api_vision_smart

# Auto-routed to ZERO_COST (Apple Vision)
result = api_vision_smart(
    image_path="/path/to/screenshot.png",
    prompt="Read the text"
)
print(result["response"])  # Extracted text
print(result["tier_used"])  # "ZERO_COST"

# Force VLM for detailed analysis
result = api_vision_smart(
    image_path="/path/to/photo.jpg",
    prompt="Describe everything",
    force_tier="LOCAL_VLM"
)
```

### curl
```bash
# Smart routing
curl -X POST http://localhost:8765/api/vision/smart \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/tmp/test.png", "prompt": "What color is this?"}'

# Check cache stats
curl http://localhost:8765/api/vision/smart/stats
```

### GUI (Tauri)
- Drag & drop image into chat
- Paste with Cmd+V
- Click upload button
- SAM auto-routes to appropriate tier
