# Data Arsenal Audit - Phase 5 Preparation

**Audit Date:** 2026-01-25
**Auditor:** Claude Opus 4.5
**Status:** Research Complete

---

## Executive Summary

The SAM data gathering ecosystem consists of multiple interconnected systems designed to collect, process, and prepare training data for fine-tuning SAM's MLX-based language model. The primary components are:

1. **data_arsenal.py** - Web scraping and intelligence gathering
2. **training_data_collector.py** - Local data extraction from code and docs
3. **knowledge_distillation.py** - Claude reasoning pattern capture
4. **cutting_edge.py** - Software trend monitoring and pattern discovery
5. **Supporting systems** - Code indexing, voice extraction, SSOT sync

---

## 1. Data Arsenal (`data_arsenal.py`)

**Purpose:** SAM's "eyes and ears on the world" - web intelligence gathering

### 1.1 Current Data Sources Supported

| Source Type | Implementation | Status |
|-------------|----------------|--------|
| `WEBSITE` | Generic web scraping with trafilatura/bs4 | Working |
| `GITHUB` | Trending repos, releases parsing | Working |
| `HACKERNEWS` | Firebase API integration | Working |
| `REDDIT` | JSON API (no auth required) | Working |
| `ARXIV` | Research paper listing | Working |
| `DOCUMENTATION` | Deep crawling with link following | Working |
| `RSS` | Feed parsing via feedparser | Working |
| `API` | Generic API endpoints | Defined, not implemented |
| `EXPORT` | Claude/ChatGPT exports | Defined, not implemented |
| `LOCAL` | Local file ingestion | Defined, not implemented |

### 1.2 Pre-Configured Sources

```
- github_trending      : GitHub Trending (refresh: 12h)
- hackernews_front     : Hacker News Top Stories (refresh: 6h)
- ollama_releases      : Ollama GitHub Releases (refresh: 24h)
- tauri_releases       : Tauri GitHub Releases (refresh: 24h)
- arxiv_ai             : arXiv cs.AI Papers (refresh: 24h)
- reddit_localllama    : r/LocalLLaMA Hot Posts (refresh: 12h)
- warp_docs            : Warp Documentation (refresh: 168h)
```

### 1.3 Extraction Types

| Type | Description | Implementation |
|------|-------------|----------------|
| `FULL_CONTENT` | Complete page content | Yes |
| `ARTICLE` | Main article text only | Yes (trafilatura) |
| `CODE` | Code blocks extraction | Yes |
| `LINKS` | Link harvesting | Yes |
| `METADATA` | Title, date, author | Yes |
| `STRUCTURED` | JSON-LD, schema.org | Not implemented |
| `PATTERNS` | UI/UX patterns | Partial |
| `CHANGELOG` | Version changes | Yes |

### 1.4 Data Format and Storage

**Database:** SQLite at `~/.sam/data_arsenal.db`

**Tables:**
- `items` - Scraped content with content hash for deduplication
- `patterns` - Extracted patterns with relevance scoring
- `scrape_log` - Scrape history and statistics
- `items_fts` - Full-text search index (FTS5)

**ScrapedItem Schema:**
```python
@dataclass
class ScrapedItem:
    id: str
    source_name: str
    source_type: str
    url: str
    title: str
    content: str
    content_type: str  # "article", "code", "discussion", etc.
    metadata: Dict
    extracted_patterns: List[str]
    extracted_code: List[str]
    extracted_links: List[str]
    scraped_at: str
    content_hash: str  # For deduplication
```

### 1.5 Quality Controls

| Control | Implementation |
|---------|----------------|
| Content deduplication | MD5 hash comparison |
| Rate limiting | Configurable per source (1000-3000ms) |
| Content size limits | 50,000 chars for webpages, 30,000 for docs |
| Code block limits | Max 10 blocks per page |
| Link limits | Max 50 links per page |

### 1.6 Gaps Identified

1. **No authentication support for private APIs** - auth_type/auth_value defined but unused
2. **EXPORT and LOCAL source types not implemented** - Critical for Phase 5
3. **No structured data extraction** (JSON-LD, schema.org)
4. **No scheduled scraping** - Manual trigger only
5. **No proxy support** for rate-limited sources
6. **No content validation** beyond deduplication
7. **Limited pattern extraction** - Basic keyword matching only

---

## 2. Training Data Collector (`training_data_collector.py`)

**Purpose:** Extract training data from local repositories and documentation

### 2.1 Data Sources

| Source | Extraction Type |
|--------|-----------------|
| Git repositories | Commit messages, diff summaries |
| Code dedup database | Code samples by language |
| SSOT documents | Markdown documentation |
| Synthetic | Routing examples (hardcoded) |

### 2.2 Output Format

**JSONL files in `~/.sam/training_data/`:**
```
commits/commit_messages.jsonl
code_patterns/code_analysis.jsonl
knowledge/project_docs.jsonl
routing/task_routing.jsonl
```

**Training Example Format:**
```json
{
  "instruction": "Task description",
  "input": "Context/input data",
  "output": "Expected response"
}
```

### 2.3 Supported Languages
Python, Rust, JavaScript, TypeScript, Vue, Swift, Bash

### 2.4 Quality Controls
- Minimum commit message length: 10 chars
- Maximum code length: 4,000 chars
- Automatic test file detection
- Documentation detection (docstrings)

### 2.5 Gaps Identified

1. **Limited training format** - Basic instruction/input/output only
2. **No conversation format** - Missing multi-turn examples
3. **No quality scoring** - All samples treated equally
4. **No deduplication** across collection runs
5. **Static routing examples** - Not learning from actual usage

---

## 3. Knowledge Distillation (`knowledge_distillation.py`)

**Purpose:** Capture Claude's reasoning patterns for SAM training

### 3.1 Distillation Types

| Type | Description |
|------|-------------|
| `CHAIN_OF_THOUGHT` | Step-by-step reasoning capture |
| `PRINCIPLE` | Core rules/guidelines extraction |
| `PREFERENCE_PAIR` | Good vs bad response pairs |
| `SKILL_TEMPLATE` | Reusable reasoning patterns |
| `ERROR_CORRECTION` | Mistake to fix pairs |
| `SYNTHETIC` | Generated training examples |

### 3.2 Storage Locations

**Primary:** `/Volumes/David External/sam_training/distilled/`
**Fallback:** `~/.sam/knowledge_distillation.db`

**Subdirectories:**
- `exports/` - Exported training files
- `pending_review/` - Awaiting human approval
- `approved/` - Verified training data

### 3.3 Reasoning Types Captured

- Chain of thought
- Tool use patterns
- Error corrections
- Direct answers
- Multi-step reasoning
- Meta-cognitive (self-reflection)

### 3.4 Gaps Identified

1. **No automated capture** - Manual process required
2. **Human review bottleneck** - Pending review queue
3. **No real-time learning** - Batch processing only
4. **Limited domain coverage** - Mostly code-focused

---

## 4. Cutting Edge Monitor (`cutting_edge.py`)

**Purpose:** Track software trends and reverse engineering insights

### 4.1 Pattern Sources

| Source | Patterns Tracked |
|--------|------------------|
| Warp | Live thinking display, UI patterns |
| Cursor | AI tab completion |
| Claude Code | Agentic tool use |
| Obsidian | Knowledge graph visualization |
| Raycast | Universal command palette |
| Notion | Slash commands |
| Linear | Keyboard-first UX |
| ComfyUI | Node-based workflows |

### 4.2 Approach Library

Categories covered:
- `llm_inference` - Model running strategies
- `embedding` - Vector embeddings
- `image_generation` - Image creation
- `voice_synthesis` - TTS/RVC
- `data_sourcing` - Web scraping
- `reverse_engineering` - App analysis
- `ui_framework` - Interface building

### 4.3 Feasibility Assessment

Hardware-aware feasibility levels:
- `NATIVE` - Runs well on 8GB M2
- `OPTIMIZED` - Requires optimization
- `HYBRID` - Part local, part cloud
- `QUEUED` - External processing
- `IMPOSSIBLE` - Cannot run locally

### 4.4 Gaps Identified

1. **Pattern discovery is manual** - No automated trend detection
2. **Limited web monitoring** - Relies on data_arsenal
3. **No implementation tracking** - "Implemented" flag manual
4. **Static pattern library** - Not self-updating

---

## 5. Supporting Systems

### 5.1 Code Indexer (`code_indexer.py`)

**Purpose:** Semantic code search with MLX embeddings

**Features:**
- Function/class signature extraction
- Docstring indexing
- Cross-language support (Python, Rust, Swift, TS/JS)
- Incremental updates with file watching

**Storage:** `/Volumes/David External/sam_memory/code_index.db`

### 5.2 Semantic Memory (`semantic_memory.py`)

**Purpose:** Vector embeddings for intelligent recall

**Features:**
- MLX MiniLM-L6-v2 embeddings (384-dim)
- Interaction logging
- Code snippet storage
- Cosine similarity search

**Storage:** Local `memory/` directory

### 5.3 Voice Extraction Pipeline (`voice_extraction_pipeline.py`)

**Purpose:** Extract training audio from video files

**Features:**
- VAD (Voice Activity Detection)
- Speaker diarization
- Noise reduction
- Quality filtering

**Storage:** `/Volumes/David External/SAM_Voice_Training/`

### 5.4 SSOT Sync (`ssot_sync.py`)

**Purpose:** Bidirectional sync with documentation

**Features:**
- Project state tracking
- Progress timeline maintenance
- Change detection

**Storage:** `/Volumes/Plex/SSOT/`

---

## 6. Integration Points

### 6.1 Orchestrator Integration

The orchestrator (`orchestrator.py`) routes DATA requests to DataArsenal:
```python
from data_arsenal import DataArsenal
DATA_ARSENAL = DataArsenal()
```

Routing keywords: "scrape", "gather data", "intelligence", "monitor", "trend"

### 6.2 Memory Integration

- SemanticMemory stores interactions
- CodeIndexer provides searchable code context
- Both use MLX embeddings for consistency

### 6.3 Training Pipeline

The `training_pipeline.py` connects collected data to MLX fine-tuning:
- Minimum 100 samples before training
- Qwen2.5-Coder-1.5B-Instruct base model
- LoRA rank 8, learning rate 1e-4

---

## 7. Current Training Data Inventory

**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_data/`

| File | Size | Purpose |
|------|------|---------|
| `curated_training.jsonl` | 8.4 MB | Primary training set |
| `train.jsonl` | 8.1 MB | MLX training split |
| `valid.jsonl` | 907 KB | Validation split |
| `train_old.jsonl` | 7.6 MB | Previous version |
| `valid_old.jsonl` | 848 KB | Previous validation |
| `training_samples.jsonl` | 446 KB | Additional samples |
| `patterns_*.json` | 3.6 MB | Style patterns |
| `claude_generated_*.jsonl` | ~9 KB | Claude-generated examples |

---

## 8. Phase 5 Recommendations

### 8.1 High Priority Enhancements

1. **Implement EXPORT source type** - Import Claude/ChatGPT conversation exports
   - Parse conversation JSON format
   - Extract high-quality Q&A pairs
   - Filter for SAM-relevant domains

2. **Implement LOCAL source type** - Direct file ingestion
   - Support markdown, text, code files
   - Preserve metadata and provenance
   - Handle large file batching

3. **Add conversation format output** - Multi-turn training data
   - Chat completion format for fine-tuning
   - System prompt integration
   - User/assistant role separation

4. **Implement quality scoring** - Automated quality assessment
   - Content relevance scoring
   - Response quality metrics
   - Automatic rejection thresholds

### 8.2 Medium Priority Enhancements

5. **Scheduled scraping** - Automatic data refresh
   - Cron-based scheduling
   - Source-specific intervals
   - Failure retry logic

6. **Authentication support** - Access private APIs
   - Bearer token handling
   - Cookie-based auth
   - OAuth integration

7. **Real-time distillation** - Automatic Claude capture
   - Hook into conversation flow
   - Immediate pattern extraction
   - Background processing

8. **Structured data extraction** - Rich metadata capture
   - JSON-LD parsing
   - Schema.org recognition
   - Microformat extraction

### 8.3 Lower Priority Enhancements

9. **Proxy support** - Rate limit management
   - Rotating proxy integration
   - Regional distribution
   - Ban detection/recovery

10. **Pattern auto-discovery** - Automated trend detection
    - GitHub trending analysis
    - HN front page patterns
    - Social signal correlation

11. **Cross-run deduplication** - Training data hygiene
    - Content hash comparison
    - Semantic similarity detection
    - Version tracking

---

## 9. Storage Strategy Compliance

Per project rules, large files must go to external storage:

| System | Current Location | Compliant |
|--------|------------------|-----------|
| Data Arsenal DB | `~/.sam/data_arsenal.db` | Review needed |
| Code Index DB | External drive | Yes |
| Distillation DB | External drive (fallback to local) | Yes |
| Training Data | Local `training_data/` | Review needed |
| Voice Training | External drive | Yes |

**Recommendation:** Move data_arsenal.db and training_data/ to external storage if they exceed 10MB.

---

## 10. Conclusion

The current data gathering infrastructure is functional but fragmented. For Phase 5 success, the key priorities are:

1. **Unify data formats** - Standard JSONL with consistent schemas
2. **Implement missing source types** - EXPORT and LOCAL are critical
3. **Add quality controls** - Automated scoring and filtering
4. **Enable scheduled operation** - Move from manual to automated
5. **Optimize storage** - External drive for all large datasets

The foundation is solid. The architecture supports expansion. Phase 5 should focus on automation, quality, and coverage.

---

*Generated by Claude Opus 4.5 for SAM Phase 5 Preparation*
