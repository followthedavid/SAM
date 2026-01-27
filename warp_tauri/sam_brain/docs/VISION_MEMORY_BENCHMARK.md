# Vision Memory Benchmark

**Phase 3.2.1 Documentation**
**Date:** 2026-01-25
**System:** M2 Mac Mini, 8GB RAM

## Overview

SAM's vision system uses a 4-tier architecture to minimize memory usage while maximizing capability. This document provides memory benchmarks for each tier and guidance on tier selection.

## Tier Memory Requirements

### Tier 0: Zero-Cost (Apple APIs)

| Component | Memory Cost | Processing Time | Use Cases |
|-----------|-------------|-----------------|-----------|
| Apple Vision OCR | ~0 MB | 20-50ms | Text extraction, reading screenshots |
| PIL Analysis | ~0 MB | <1ms | Color analysis, basic image properties |

**How it works:**
- Uses macOS Vision.framework via pyobjc
- Runs on Apple Neural Engine (ANE), not system RAM
- No model loading required
- Result: Instant, zero RAM overhead

**Files:**
- `apple_ocr.py` - Vision framework wrapper
- `cognitive/smart_vision.py` - PIL analysis functions

### Tier 1: Lightweight (CoreML)

| Component | Memory Cost | Processing Time | Use Cases |
|-----------|-------------|-----------------|-----------|
| CoreML Face Detection | ~200 MB | 100-500ms | Face detection, counting |
| Basic Classifiers | ~100-300 MB | 50-200ms | Object presence, scene type |

**How it works:**
- Uses Vision.framework VNDetectFaceRectanglesRequest
- CoreML models run on ANE with minimal RAM spillover
- Models cached by system

**Files:**
- `cognitive/smart_vision.py` - `handle_face_detection()`, `handle_basic_describe()`

### Tier 2: Local VLM (nanoLLaVA)

| Component | Memory Cost | Processing Time | Use Cases |
|-----------|-------------|-----------------|-----------|
| nanoLLaVA 1.5B bf16 | ~3-4 GB | 10-60s | General vision Q&A, descriptions |

**How it works:**
- Uses mlx_vlm for MLX-native inference
- Model ID: `mlx-community/nanoLLaVA-1.5-bf16`
- Single model kept loaded (others unloaded to save RAM)
- Can use persistent vision server (port 8766) for faster repeated calls

**Memory Breakdown:**
```
Model weights:        ~1.5 GB
KV-cache:            ~1.0 GB (varies with context)
Image processing:    ~0.5 GB
MLX overhead:        ~0.5 GB
Total peak:          ~3.5-4.0 GB
```

**Files:**
- `cognitive/vision_engine.py` - Main VLM processing
- `vision_server.py` - Persistent server (model stays loaded)

### Tier 3: Claude Escalation

| Component | Memory Cost | Processing Time | Use Cases |
|-----------|-------------|-----------------|-----------|
| Terminal bridge | ~0 MB local | Varies (10-60s) | Complex reasoning, code review, UI analysis |

**How it works:**
- Uses dual terminal bridge to send image to Claude Code
- Zero local memory cost (processing happens in Claude's context)
- Best for complex multi-step reasoning

**Files:**
- `cognitive/smart_vision.py` - `handle_claude_escalation()`
- `escalation_handler.py` - Bridge implementation

## Memory Configurations in Code

### vision_engine.py Model Registry

```python
VISION_MODELS = {
    "nanollava": {
        "model_id": "mlx-community/nanoLLaVA-1.5-bf16",
        "memory_mb": 1500,      # Reported model size
        "max_tokens": 512,
        "quality": "good",
        "trust_remote_code": True,
    },
    "smolvlm-256m": {
        "model_id": "mlx-community/SmolVLM2-256M-Video-Instruct-mlx",
        "memory_mb": 500,
        "requires_pytorch": True,  # Not usable without torch
    },
    "smolvlm-500m": {
        "memory_mb": 1000,
        "requires_pytorch": True,
    },
    "smolvlm-2b-4bit": {
        "memory_mb": 3500,       # Too large for 8GB system
        "requires_pytorch": True,
    },
}
```

**Note:** SmolVLM models require PyTorch for their processor, making them unusable in our PyTorch-free MLX environment. nanoLLaVA is the primary VLM.

### VisionModelSelector Memory Constraints

```python
class VisionModelSelector:
    def __init__(self, max_memory_mb: int = 3000):
        self.max_memory_mb = max_memory_mb

    def get_available_memory_mb(self) -> int:
        # Uses psutil to check available RAM
        # Returns 40% of available, max 3GB
        pass

    def select_model(self, prompt, ...):
        # Filters models by: memory_mb <= available_mem
        # Excludes: requires_pytorch=True, deprecated=True
        pass
```

## Resource Manager Integration

The `cognitive/resource_manager.py` defines memory thresholds:

```python
@dataclass
class ResourceConfig:
    # Memory thresholds (in GB)
    memory_critical_gb: float = 0.2   # Refuse heavy operations
    memory_low_gb: float = 0.4        # Minimal tokens
    memory_moderate_gb: float = 0.7   # Reduced tokens
    # Above 0.7GB = GOOD: full capability
```

### Token Limits by Resource Level

| Resource Level | Available RAM | Max Tokens |
|----------------|---------------|------------|
| CRITICAL | <0.2 GB | 50 |
| LOW | 0.2-0.4 GB | 100 |
| MODERATE | 0.4-0.7 GB | 150 |
| GOOD | >0.7 GB | 200 |

## Benchmark Function

A `measure_memory_usage()` function is available in `cognitive/vision_engine.py`:

```python
from cognitive.vision_engine import measure_memory_usage

# Get detailed memory report
report = measure_memory_usage()
print(report)
```

### Example Output (Typical 8GB System)

```json
{
  "system": {
    "available_gb": 1.46,
    "available_mb": 1495.0,
    "total_gb": 8.0,
    "used_percent": 81.7
  },
  "vision_tiers": {
    "ZERO_COST": {
      "ram_mb": 0,
      "description": "Apple Vision OCR, PIL analysis",
      "status": "always_available"
    },
    "LIGHTWEIGHT": {
      "ram_mb": 200,
      "description": "CoreML face detection, basic classifiers",
      "status": "available"
    },
    "LOCAL_VLM": {
      "ram_mb": 4000,
      "description": "nanoLLaVA 1.5B for general vision Q&A",
      "status": "insufficient_memory"
    },
    "CLAUDE": {
      "ram_mb": 0,
      "description": "Escalation to Claude via terminal bridge",
      "status": "always_available"
    }
  },
  "recommended_tier": "LIGHTWEIGHT",
  "can_run_vlm": false,
  "resource_level": "GOOD",
  "models": {
    "nanollava": {
      "model_id": "mlx-community/nanoLLaVA-1.5-bf16",
      "reported_mb": 1500,
      "actual_peak_mb": 4000,
      "available": false
    }
  },
  "recommendations": [
    "VLM unavailable - use Tier 0/1 or escalate to Claude",
    "Need ~4GB free for nanoLLaVA",
    "Limited memory - prefer OCR and CoreML tasks",
    "VLM may work but could be slow"
  ]
}
```

### Quick Test Command

```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
python3 -c "from cognitive.vision_engine import measure_memory_usage; import json; print(json.dumps(measure_memory_usage(), indent=2))"
```

## Performance Matrix

| Tier | Memory | Speed | Quality | Reliability |
|------|--------|-------|---------|-------------|
| ZERO_COST | 0 | Instant | Perfect (OCR) | 100% |
| LIGHTWEIGHT | 200MB | Fast | Good | 95% |
| LOCAL_VLM | 4GB | Slow | Good | 75% |
| CLAUDE | 0 local | Variable | Excellent | 95% |

## Recommendations for 8GB System

1. **Always try Tier 0 first** - OCR and color analysis are free
2. **Use Tier 1 for quick answers** - Face detection, basic classification
3. **Reserve Tier 2 for necessary cases** - Complex scene understanding
4. **Escalate to Tier 3 for reasoning** - Code review, UI analysis, comparisons

### Optimal Task Routing

```
"Read the text"          -> Tier 0 (Apple Vision OCR)
"What color is this?"    -> Tier 0 (PIL analysis)
"How many faces?"        -> Tier 1 (CoreML)
"Describe this image"    -> Tier 2 (nanoLLaVA) or Tier 1 (basic)
"Explain why this fails" -> Tier 3 (Claude)
"Review this code"       -> Tier 3 (Claude)
```

## Monitoring Memory

### Quick Check
```python
from cognitive.resource_manager import check_resources
print(check_resources())
```

### Vision-Specific Check
```python
from cognitive.vision_engine import measure_memory_usage
print(measure_memory_usage())
```

### Before VLM Operation
```python
from cognitive.resource_manager import ResourceManager
manager = ResourceManager()
can_run, reason = manager.can_perform_heavy_operation()
if not can_run:
    print(f"Cannot run VLM: {reason}")
```

## Memory Optimization Strategies

1. **Use vision server** (`vision_server.py` on port 8766) - Keeps model loaded
2. **Unload after use** - Call `engine.unload_models()` when done
3. **Check before loading** - Use `measure_memory_usage()` first
4. **Prefer lower tiers** - OCR and CoreML are virtually free
5. **Quit Docker when idle** - Saves ~2GB if running

## Files Reference

| File | Purpose |
|------|---------|
| `cognitive/vision_engine.py` | Main VLM processing, `measure_memory_usage()` |
| `cognitive/smart_vision.py` | 4-tier routing, task classification |
| `cognitive/resource_manager.py` | Memory thresholds, operation limits |
| `apple_ocr.py` | Zero-cost OCR |
| `vision_server.py` | Persistent VLM server |

## Change Log

- **2026-01-25**: Initial benchmark documentation (Phase 3.2.1)
- Documented all 4 tiers with memory requirements
- Added `measure_memory_usage()` function reference
- Mapped task types to optimal tiers
