# utils/ - Helpers

## What This Does
Shared utilities that don't belong to any specific capability.

## Why It Exists
Some code is used everywhere but doesn't fit in speak/, see/, etc.
This is the catch-all for genuinely shared utilities.

## When To Use
- Audio format conversion
- Image utilities
- Path resolution
- RAM monitoring
- External service clients

## Key Files
- `audio.py` - Audio loading, format conversion (soundfile backend)
- `image.py` - Image loading, resizing, format conversion
- `paths.py` - Resolve paths across internal/external storage
- `resources.py` - RAM monitoring, prevent 8GB OOM
- `data_arsenal.py` - Data scraping and collection tools
- `comfyui.py` - ComfyUI client for image generation
- `ssot.py` - SSOT sync utilities
- `app_knowledge.py` - Extract knowledge from macOS apps

## Storage Paths
```python
from sam.utils import paths

paths.models()      # /Volumes/David External/SAM_models/
paths.memory()      # /Volumes/David External/sam_memory/
paths.training()    # /Volumes/David External/SAM_Voice_Training/
paths.cache()       # /Volumes/Plex/DevSymlinks/
```

## Resource Monitoring
```python
from sam.utils import resources

if resources.available_ram_gb() < 2:
    # Don't load the 3B model
    pass
```

## Dependencies
- **Requires:** Nothing (leaf node)
- **Required by:** Many packages

## What Was Here Before
This consolidates:
- `audio_utils.py` (239 lines)
- `cognitive/resource_manager.py` (571 lines)
- `data_arsenal.py` (1,183 lines)
- `comfyui_client.py` (142 lines)
- `ssot_sync.py` (317 lines)
