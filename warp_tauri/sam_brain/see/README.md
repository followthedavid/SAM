# see/ - Vision

## What This Does
Processes images - OCR, descriptions, object detection. Makes SAM see.

## Why It Exists
SAM needs to understand screenshots, photos, and documents.
This package provides tiered vision with zero-cost OCR via Apple Vision.

## When To Use
- Extracting text from images (OCR)
- Describing what's in an image
- Detecting objects or faces
- Reading macOS UI state

## How To Use
```python
from sam.see import ocr
text = ocr.extract("/path/to/screenshot.png")

from sam.see import describe
description = describe.image("/path/to/photo.jpg")
# "A cat sitting on a laptop keyboard"

from sam.see import ui_state
windows = ui_state.get_active_windows()
```

## Key Files
- `ocr.py` - Apple Vision OCR (22ms, zero RAM cost)
- `describe.py` - VLM image descriptions (nanoLLaVA)
- `ui_state.py` - Read macOS UI elements
- `preprocess.py` - Memory-efficient image handling

## Vision Tiers
| Tier | Speed | RAM | Use Case |
|------|-------|-----|----------|
| ZERO_COST | 22ms | 0 | Text extraction |
| LIGHTWEIGHT | ~100ms | 200MB | Face detection |
| LOCAL_VLM | 10-60s | 4GB | General vision |
| CLAUDE | varies | 0 | Complex reasoning |

## Dependencies
- **Requires:** pyobjc (for Apple Vision)
- **Required by:** core/ (for image processing)

## What Was Here Before
This consolidates:
- `cognitive/vision_engine.py` (1,054 lines)
- `cognitive/smart_vision.py` (542 lines) - duplicate, merged
- `cognitive/vision_selector.py` (365 lines) - duplicate, merged
- `apple_ocr.py` (191 lines)
- `cognitive/ui_awareness.py` (843 lines)
