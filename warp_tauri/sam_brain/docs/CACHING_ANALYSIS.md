# SAM Brain Caching Analysis

**Generated:** 2026-01-28
**Purpose:** Document all caching mechanisms, identify issues, and recommend improvements

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Caching Mechanisms by Category](#caching-mechanisms-by-category)
3. [Cache Storage Locations](#cache-storage-locations)
4. [TTL and Expiration Policies](#ttl-and-expiration-policies)
5. [Cache Size Limits](#cache-size-limits)
6. [Potential Issues](#potential-issues)
7. [Missing Caches](#missing-caches)
8. [Recommendations](#recommendations)

---

## Executive Summary

SAM Brain uses **16+ distinct caching mechanisms** across different subsystems. Caches are implemented using:
- **In-memory dictionaries** (most common)
- **JSON files on disk** (for persistence across restarts)
- **SQLite databases** (for structured cache data)
- **Filesystem directories** (for audio/image cache)

### Key Findings

| Category | Count | Concerns |
|----------|-------|----------|
| Unbounded in-memory caches | 8 | Potential memory leaks |
| Disk caches without cleanup | 3 | Disk space growth |
| TTL-based caches | 4 | Well-managed |
| LRU caches | 2 | Well-managed |

---

## Caching Mechanisms by Category

### 1. Intelligence/Learning Caches

#### IntelligenceCache (`sam_intelligence.py`)
```python
class IntelligenceCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.cache: Dict[str, Tuple[Any, float]] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory + disk (`.sam_intelligence_cache.json`) |
| Storage | JSON file at `sam_brain/.sam_intelligence_cache.json` |
| TTL | 300 seconds (5 minutes) default |
| Size Limit | **None** (unbounded) |
| Invalidation | Manual via `invalidate(pattern)` method |
| Persistence | Yes - loads/saves to JSON file |

**What's Cached:**
- `projects` - list of tracked projects (60s TTL)
- `level_{project_id}` - evolution level (300s TTL)
- `top_suggestions` - improvement suggestions (120s TTL)

**Concern:** No maximum entry count limit.

---

#### TrainingDataStats Cache (`training_stats.py`)
```python
CACHE_TTL_SECONDS = 300  # 5 minutes
stats_cache_file = SCRIPT_DIR / ".training_stats_cache.json"
```

| Property | Value |
|----------|-------|
| Location | Disk only (`.training_stats_cache.json`) |
| TTL | 300 seconds (5 minutes) |
| Size Limit | Single cached result |
| Invalidation | Time-based |
| Persistence | Yes |

**What's Cached:**
- Overall training data statistics

**Status:** Well-managed, single entry cache.

---

### 2. Voice/Audio Caches

#### VoiceCache (`voice/voice_cache.py`)
```python
DEFAULT_CACHE_DIR = Path.home() / ".sam" / "voice_cache"
DEFAULT_MAX_CACHE_SIZE = 500 * 1024 * 1024  # 500MB
DEFAULT_MAX_AGE_DAYS = 7
```

| Property | Value |
|----------|-------|
| Location | `~/.sam/voice_cache/` + metadata JSON |
| Storage | Audio files (WAV/AIFF) + `cache_metadata.json` |
| TTL | 7 days (`DEFAULT_MAX_AGE_DAYS`) |
| Size Limit | 500MB (`DEFAULT_MAX_CACHE_SIZE`) |
| Invalidation | LRU eviction + age-based cleanup |
| Persistence | Yes |

**What's Cached:**
- Pre-generated TTS audio for common phrases
- Cached voice outputs keyed by `hash(text + voice + settings)`

**Features:**
- LRU eviction when max size exceeded
- Background cleanup of old entries
- Pre-computes SAM's common phrases
- Stats tracking (hits, misses, evictions)

**Status:** Well-designed with proper limits.

---

#### Voice Cache Directories (observed)
```
/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/voice_cache/     # 556KB
/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/voice_cache_v2/  # 164KB
/Users/davidquinton/.sam/voice_cache/                                     # Empty
```

**Concern:** Multiple voice cache directories exist. The v2 cache may be orphaned.

---

### 3. Embedding/Semantic Caches

#### HyDE Retriever Cache (`cognitive/enhanced_retrieval.py`)
```python
class HyDERetriever:
    def __init__(self, ...):
        self.cache: Dict[str, List[float]] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| Storage | Dict of `{query_hash: embedding}` |
| TTL | **None** (session lifetime) |
| Size Limit | **None** (unbounded) |
| Invalidation | None |

**Concern:** Unbounded memory growth. No eviction strategy.

---

#### DocumentStore Embedding Cache (`cognitive/enhanced_retrieval.py`)
```python
class DocumentStore:
    def __init__(self, ...):
        self._embedding_cache: Dict[str, List[float]] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | **None** |
| Size Limit | **None** |

**Concern:** Same as HyDE - unbounded memory growth.

---

#### MLXCrossEncoder Cache (`relevance_scorer.py`)
```python
class MLXCrossEncoder:
    def __init__(self):
        self._embedding_cache: Dict[str, Any] = {}
        self._cache_limit = 500
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | **None** |
| Size Limit | 500 entries (FIFO eviction) |
| Invalidation | Oldest 100 entries removed when limit hit |

**Status:** Has size limit, but FIFO instead of LRU.

---

#### KeywordMatcher Cache (`relevance_scorer.py`)
```python
class KeywordMatcher:
    def __init__(self):
        self._cache: Dict[str, List[str]] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | **None** |
| Size Limit | **None** (keys limited to 200 chars) |

**Concern:** Unbounded growth for unique text inputs.

---

### 4. MLX/Model Caches

#### MLX Conversation Cache (`cognitive/mlx_optimized.py`)
```python
class OptimizedMLXEngine:
    def __init__(self):
        self._system_prompt_cache: Dict[str, Any] = {}
        self._conversation_cache: Optional[Any] = None
        cache_dir: Path = Path("/tmp/sam_kv_cache")
```

| Property | Value |
|----------|-------|
| Location | Memory + `/tmp/sam_kv_cache/` |
| TTL | Session lifetime |
| Size Limit | Single conversation cache |
| Invalidation | `clear_conversation_cache()` method |

**What's Cached:**
- System prompt KV cache per model
- Conversation context for continuation

**Status:** Well-managed, tracks hit/miss stats.

---

#### MLX Model Cache (`cognitive/mlx_cognitive.py`)
```python
class MLXCognitiveEngine:
    def __init__(self):
        self._current_model_key: Optional[str] = None
        self._model = None
        self._tokenizer = None
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | Until `unload_model()` called |
| Size Limit | 1 model at a time |

**What's Cached:**
- Currently loaded MLX model and tokenizer
- Only one model kept in memory

**Status:** Well-managed with explicit unload.

---

### 5. Vision Caches

#### Smart Vision DB Cache (`cognitive/smart_vision.py`)
```sql
CREATE TABLE IF NOT EXISTS vision_cache (
    image_hash TEXT PRIMARY KEY,
    task_type TEXT,
    result TEXT,
    created_at REAL,
    access_count INTEGER DEFAULT 1
)
```

| Property | Value |
|----------|-------|
| Location | SQLite database |
| TTL | **None** |
| Size Limit | **None** |
| Invalidation | None automatic |

**Concern:** Database grows indefinitely without cleanup.

---

#### Image Preprocessor Cache (`cognitive/image_preprocessor.py`)
```python
class ImagePreprocessor:
    def __init__(self, cache_dir=TEMP_DIR):
        self._processed_files: Dict[str, str] = {}
        self.cache_dir = cache_dir  # Default: /tmp/sam_images
```

| Property | Value |
|----------|-------|
| Location | `/tmp/sam_images/` + memory dict |
| TTL | Configurable via `cleanup_cache(max_age_hours=24)` |
| Size Limit | **None** |
| Invalidation | Manual `clear_cache()` or `cleanup_cache()` |

**Concern:** No automatic cleanup scheduled.

---

### 6. Memory System Caches

#### Procedural Memory Skill Cache (`cognitive/enhanced_memory.py`)
```python
class ProceduralMemory:
    def __init__(self):
        self._skill_cache: Dict[str, Skill] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory (backed by SQLite) |
| TTL | **None** |
| Size Limit | **None** |

**What's Cached:**
- Skill objects loaded from database

**Status:** Acts as read-through cache for database.

---

#### User Model Cache (`cognitive/emotional_model.py`)
```python
class RelationshipTracker:
    def __init__(self):
        self.user_cache: Dict[str, UserModel] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory (backed by SQLite) |
| TTL | **None** |
| Size Limit | **None** |

**What's Cached:**
- UserModel objects for relationship tracking

**Concern:** No eviction for inactive users.

---

#### Goal Cache (`cognitive/cognitive_control.py`)
```python
class GoalManager:
    def __init__(self):
        self.goal_cache: Dict[str, Goal] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory (backed by SQLite) |
| TTL | **None** |
| Size Limit | **None** |

**Status:** Read-through cache, goals have natural lifecycle.

---

#### IDF Cache (`cognitive/compression.py`)
```python
class PromptCompressor:
    def __init__(self):
        self.idf_cache: Dict[str, float] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | **None** |
| Size Limit | **None** |

**Concern:** Grows with vocabulary size. Could be very large.

---

### 7. Planning/Availability Cache

#### Capability Availability Cache (`cognitive/planning_framework.py`)
```python
class CapabilityChecker:
    def __init__(self):
        self._availability_cache: Dict[str, bool] = {}
```

| Property | Value |
|----------|-------|
| Location | Memory only |
| TTL | **None** |
| Size Limit | Bounded by capability/tier combinations |
| Invalidation | `clear_cache()` method |

**Status:** Naturally bounded, small cache.

---

## Cache Storage Locations

### Memory-Only Caches
| Cache | Module | Concern |
|-------|--------|---------|
| HyDE embedding cache | `enhanced_retrieval.py` | Unbounded |
| DocumentStore embedding cache | `enhanced_retrieval.py` | Unbounded |
| Keyword matcher cache | `relevance_scorer.py` | Unbounded |
| IDF cache | `compression.py` | Unbounded |
| Skill cache | `enhanced_memory.py` | Backed by DB |
| User cache | `emotional_model.py` | Unbounded |
| Goal cache | `cognitive_control.py` | Backed by DB |
| Availability cache | `planning_framework.py` | Bounded |
| MLX cross-encoder cache | `relevance_scorer.py` | 500 entry limit |

### Disk Caches
| Cache | Location | Size Limit | TTL |
|-------|----------|------------|-----|
| Intelligence cache | `.sam_intelligence_cache.json` | None | 5 min |
| Training stats cache | `.training_stats_cache.json` | Single entry | 5 min |
| Voice cache | `~/.sam/voice_cache/` | 500MB | 7 days |
| Image preprocessor | `/tmp/sam_images/` | None | Manual |
| MLX KV cache | `/tmp/sam_kv_cache/` | Single | Session |

### Database Caches
| Cache | Database | Cleanup |
|-------|----------|---------|
| Vision cache | `vision_memory.db` | None |
| Vision selector | `vision_selector.db` | None |

---

## TTL and Expiration Policies

| Cache | TTL | Expiration Method |
|-------|-----|-------------------|
| Intelligence cache | 5 min | Time-based check on access |
| Training stats | 5 min | Time-based check on access |
| Voice cache | 7 days | Background cleanup |
| All memory caches | None | Session lifetime |
| Vision DB cache | None | None |

---

## Cache Size Limits

| Cache | Limit | Eviction Strategy |
|-------|-------|-------------------|
| Voice cache | 500MB | LRU eviction |
| MLX cross-encoder | 500 entries | FIFO (oldest 100) |
| All others | **None** | None |

---

## Potential Issues

### 1. Memory Leaks from Unbounded Caches

**High Risk:**
- `HyDERetriever.cache` - Embedding vectors (384 floats each) accumulate
- `DocumentStore._embedding_cache` - Same issue
- `KeywordMatcher._cache` - Tokenized text accumulates
- `PromptCompressor.idf_cache` - Vocabulary growth

**Estimated Impact:**
- Each embedding: ~1.5KB (384 floats * 4 bytes)
- 1000 cached embeddings: ~1.5MB
- Long-running session could accumulate 10,000+ embeddings: ~15MB+

### 2. Disk Space Growth

**Concerns:**
- `vision_cache` SQLite table has no cleanup
- `vision_selector.db` - unknown growth pattern
- Multiple orphaned voice cache directories

### 3. Stale Cache Issues

**IntelligenceCache:**
- Uses timestamp-based expiration
- Cache persists to disk - could serve stale data after restart if clock issues

**Vision DB Cache:**
- No TTL - cached results may become stale
- Image hash based - same image always returns same result

### 4. Missing Cache Invalidation

The following caches have no invalidation mechanism:
- All embedding caches
- IDF cache
- User model cache
- Vision DB cache

---

## Missing Caches (Opportunities)

### 1. Semantic Memory Search Results
**Current:** Each search recomputes cosine similarity across all embeddings
**Opportunity:** Cache recent query results (would need invalidation on new entries)

### 2. Code Indexer Search Results
**Current:** Each search queries SQLite
**Opportunity:** LRU cache of recent code searches

### 3. Project Detection Results
**Current:** `ProjectDetector.detect()` scans filesystem each time
**Opportunity:** Cache with filesystem watcher invalidation

### 4. MLX Model Selection
**Current:** `_select_model()` analyzes each query
**Opportunity:** Cache model selection for similar query patterns

---

## Recommendations

### Immediate Actions (High Priority)

1. **Add size limits to embedding caches:**
```python
class HyDERetriever:
    MAX_CACHE_SIZE = 1000

    def get_hyde_embedding(self, query: str) -> List[float]:
        # Evict oldest if at limit
        if len(self.cache) >= self.MAX_CACHE_SIZE:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
```

2. **Add cleanup job for vision_cache table:**
```python
def cleanup_vision_cache(max_age_days=30):
    """Remove stale vision cache entries."""
    cutoff = time.time() - (max_age_days * 86400)
    cursor.execute(
        "DELETE FROM vision_cache WHERE created_at < ?",
        (cutoff,)
    )
```

3. **Consolidate voice cache directories:**
- Remove orphaned `voice_cache_v2/`
- Use only `~/.sam/voice_cache/`

### Medium Priority

4. **Add LRU eviction to MLXCrossEncoder:**
- Current FIFO is suboptimal
- Use `collections.OrderedDict` for LRU

5. **Add session-end cleanup:**
```python
def cleanup_session_caches():
    """Clear memory caches on session end."""
    HyDERetriever.cache.clear()
    DocumentStore._embedding_cache.clear()
    KeywordMatcher._cache.clear()
```

6. **Monitor cache effectiveness:**
- Add hit/miss tracking to all caches
- Log cache stats periodically

### Long-term Improvements

7. **Unified cache manager:**
- Single class to manage all caches
- Consistent TTL and size policies
- Memory pressure-aware eviction

8. **Consider Redis/memcached:**
- For caches that need cross-process sharing
- Better memory management

9. **Add cache metrics endpoint:**
```
GET /api/cache/stats
{
  "intelligence_cache": {"entries": 5, "hit_rate": 0.85},
  "embedding_cache": {"entries": 234, "memory_mb": 0.35},
  "voice_cache": {"files": 47, "size_mb": 12.3},
  ...
}
```

---

## Summary Table

| Cache | Type | Location | TTL | Size Limit | Risk |
|-------|------|----------|-----|------------|------|
| IntelligenceCache | Dict+JSON | Memory+Disk | 5min | None | Medium |
| TrainingStatsCache | JSON | Disk | 5min | 1 entry | Low |
| VoiceCache | Files+JSON | Disk | 7 days | 500MB | Low |
| HyDE Embedding | Dict | Memory | None | None | **High** |
| DocStore Embedding | Dict | Memory | None | None | **High** |
| MLX CrossEncoder | Dict | Memory | None | 500 | Medium |
| KeywordMatcher | Dict | Memory | None | None | **High** |
| Vision DB | SQLite | Disk | None | None | Medium |
| ImagePreprocessor | Files+Dict | Disk | Manual | None | Medium |
| Skill Cache | Dict | Memory | None | None | Low |
| User Cache | Dict | Memory | None | None | Medium |
| Goal Cache | Dict | Memory | None | None | Low |
| IDF Cache | Dict | Memory | None | None | **High** |
| Availability Cache | Dict | Memory | None | ~20 | Low |
| MLX Model | Single | Memory | Manual | 1 | Low |
| MLX Conv Cache | Single | Memory | Manual | 1 | Low |

---

*Document generated by caching analysis task. Review and update periodically.*
