# SAM Voice Performance Benchmark

*To generate actual results, run: `python voice_benchmark.py run`*

## Overview

This document tracks voice pipeline performance on the 8GB M2 Mac Mini.

## Expected Performance

Based on system specifications and similar benchmarks:

| Engine | Latency | RAM Usage | Quality |
|--------|---------|-----------|---------|
| macOS say | ~100ms | 0 | Basic |
| edge-tts | 500-1500ms | ~50MB | Natural |
| Coqui TTS | 2-5s | ~800MB | Good |
| F5-TTS | 3-8s | ~1.5GB | Excellent |
| RVC | +2-5s | +2GB | Voice clone |

## Recommendations

### For 8GB RAM System

1. **Default to Balanced Mode**
   - Use F5-TTS when RAM > 2.5GB available
   - Auto-fallback to macOS say when busy

2. **Cache Aggressively**
   - Pre-compute SAM's ~50 common phrases
   - LRU cache with 500MB limit
   - Expected 60-80% cache hit rate in conversation

3. **Monitor Resources**
   - Check RAM before each synthesis
   - Seamless fallback prevents errors

### Quality Level Selection

| Scenario | Recommended Level |
|----------|-------------------|
| Quick acknowledgments | FAST |
| Normal conversation | BALANCED |
| Important responses | QUALITY |
| System busy | Auto-fallback |

## Running Benchmarks

```bash
# Full benchmark suite
python voice_benchmark.py run

# Individual benchmarks
python voice_benchmark.py tts       # TTS engines only
python voice_benchmark.py rvc       # RVC conversion
python voice_benchmark.py pipeline  # Full pipeline

# View results
python voice_benchmark.py report
```

## Cache Performance

```bash
# Check cache stats
python voice_cache.py stats

# Precompute common phrases
python voice_cache.py precompute --voice Daniel

# Clean old entries
python voice_cache.py cleanup --max-age 7
```

## Integration

The voice benchmark and cache integrate with:

- `resource_manager.py` - RAM monitoring
- `tts_pipeline.py` - Automatic fallback
- `voice_output.py` - Engine implementations

---

*Last updated: 2026-01-25*
