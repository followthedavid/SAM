# SAM RAG/Retrieval System Audit

**Version:** Phase 2.2.1
**Audit Date:** 2026-01-24
**Auditor:** Claude Opus 4.5

---

## Executive Summary

SAM's RAG (Retrieval-Augmented Generation) system is a sophisticated multi-layered architecture spanning seven interconnected modules. The system implements advanced retrieval techniques including HyDE, multi-hop retrieval, cross-encoder reranking, and query decomposition. It also features multiple memory tiers (working, short-term, long-term, episodic) with decay mechanisms and semantic search via MLX embeddings.

**Key Strengths:**
- Comprehensive multi-strategy retrieval pipeline
- Native MLX embeddings (no Ollama dependency)
- Multiple memory systems with different retention characteristics
- Code-aware indexing with language-specific parsers

**Key Gaps:**
- Embedding model mismatch between modules
- Limited integration between memory systems
- No unified vector database
- Missing embedding persistence in enhanced_retrieval.py

---

## 1. Current Implementation Details

### 1.1 Core Retrieval Files

| File | Location | Purpose |
|------|----------|---------|
| `enhanced_retrieval.py` | `cognitive/` | HyDE, multi-hop, reranking pipeline |
| `semantic_memory.py` | `sam_brain/` | MLX vector embeddings, memory storage |
| `code_indexer.py` | `cognitive/` | Code entity extraction and search |
| `context_manager.py` | `sam_brain/` | Context window optimization, basic RAG |
| `conversation_memory.py` | `sam_brain/` | Conversation history with fact extraction |
| `enhanced_memory.py` | `cognitive/` | Working memory, procedural memory, decay |
| `infinite_context.py` | `sam_brain/` | Hierarchical memory for long-form generation |
| `compression.py` | `cognitive/` | LLMLingua-style prompt compression |
| `fact_memory.py` | `sam_brain/` | Structured fact storage with Ebbinghaus decay |

### 1.2 Architecture Overview

```
                    +------------------+
                    |   User Query     |
                    +--------+---------+
                             |
                    +--------v---------+
                    | QueryDecomposer  |  (splits complex queries)
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
+--------v--------+  +-------v--------+  +-------v--------+
| HyDERetriever   |  | DocumentStore  |  | CodeIndexer    |
| (hypothetical   |  | (SQLite search)|  | (code entities)|
|  embeddings)    |  +----------------+  +----------------+
+-----------------+
         |
+--------v---------+
| MultiHopRetriever|  (iterative entity extraction)
+--------+---------+
         |
+--------v---------+
|CrossEncoderRerank|  (ms-marco precision scoring)
+--------+---------+
         |
+--------v---------+
| Final Results    |
+------------------+
```

---

## 2. Embedding Models Used

### 2.1 Primary Embedding Model (semantic_memory.py)

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Dimensions:** 384
**Backend:** MLX (native M2 Silicon)
**Speed:** ~10ms per embedding

```python
# From semantic_memory.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, fast

# Uses mlx_embeddings library
output = mlx_embeddings.generate(_mlx_model, _mlx_tokenizer, text[:2000])
embedding = np.array(output.text_embeds[0])
```

**Migration Note:** Switched from Ollama API to native MLX embeddings on 2026-01-18 for:
- 73% faster embedding generation (local vs network)
- No background process required
- Better memory efficiency on 8GB Mac

### 2.2 Alternative Embedding Model (enhanced_retrieval.py)

**Model:** `all-MiniLM-L6-v2` (via sentence-transformers) OR Ollama fallback
**Fallback:** `nomic-embed-text` (via Ollama API - deprecated)

```python
# From enhanced_retrieval.py
class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Tries sentence-transformers first
        self.model = SentenceTransformer(self.model_name)
        # Falls back to Ollama (deprecated)
```

**Issue:** Enhanced retrieval uses sentence-transformers directly, not MLX, creating potential inconsistency with semantic_memory.py embeddings.

### 2.3 Cross-Encoder Reranking Model

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
**Purpose:** Precision reranking of retrieved candidates
**Backend:** sentence-transformers CrossEncoder

---

## 3. Storage Format and Location

### 3.1 Storage Locations

| Data Type | Location | Format |
|-----------|----------|--------|
| Semantic Memory Entries | `sam_brain/memory/embeddings.json` | JSON |
| Semantic Memory Index | `sam_brain/memory/index.npy` | NumPy array |
| Code Index | `/Volumes/David External/sam_memory/code_index.db` | SQLite |
| Conversation Memory | `/Volumes/David External/sam_memory/memory.db` | SQLite |
| Fact Memory | Same as conversation memory | SQLite |
| Procedural Memory | `/Volumes/David External/sam_memory/procedural.db` | SQLite |
| Decay Tracking | `/Volumes/David External/sam_memory/decay.db` | SQLite |
| Infinite Context | `~/.sam/infinite_context.db` | SQLite |

### 3.2 Default RAG Databases (enhanced_retrieval.py)

```python
default_paths = [
    "/Volumes/David External/dark_psych_archive/dark_psych.db",
    "/Volumes/David External/coding_training/code_training.db",
    "/Volumes/David External/sam_memory/memory.db"
]
```

### 3.3 Data Schemas

**Semantic Memory Entry:**
```python
@dataclass
class MemoryEntry:
    id: str                    # MD5 hash (12 chars)
    content: str               # Full text content
    entry_type: str            # interaction, code, solution, note, improvement_feedback, pattern
    timestamp: str             # ISO format
    metadata: Dict             # Type-specific metadata
    embedding: List[float]     # 384-dim vector (stored separately in .npy)
```

**Code Entity:**
```python
@dataclass
class CodeEntity:
    id: str                    # MD5 hash
    name: str                  # Function/class name
    type: str                  # function, class, method, module, struct
    signature: str             # Full signature
    docstring: Optional[str]   # Documentation
    file_path: str             # Absolute path
    line_number: int           # Line number
    content: str               # Full content for embedding
    project_id: str            # Project identifier
```

**Fact Entry (with Ebbinghaus decay):**
```python
@dataclass
class UserFact:
    id: str
    fact: str                  # The fact statement
    category: str              # preferences, biographical, projects, etc.
    source: str                # explicit, inferred, system
    confidence: float          # 0.0-1.0 (decays over time)
    last_access: datetime
    reinforcement_count: int   # Testing effect
```

---

## 4. Query Capabilities

### 4.1 Retrieval Strategies

| Strategy | Class | Description |
|----------|-------|-------------|
| HyDE | `HyDERetriever` | Generates hypothetical answer, embeds, searches for similar documents |
| Multi-hop | `MultiHopRetriever` | Iteratively extracts entities, searches for related content |
| Cross-encoder Reranking | `CrossEncoderReranker` | Uses ms-marco for precise scoring of candidates |
| Query Decomposition | `QueryDecomposer` | Splits complex queries ("X and Y", "using X") into sub-queries |
| Keyword Search | `DocumentStore` | SQLite LIKE queries as fallback |
| Semantic Search | `SemanticMemory` | Cosine similarity on MLX embeddings |
| Code Search | `CodeIndexer` | Name, signature, content, docstring matching |

### 4.2 Query Pipeline (EnhancedRetrievalSystem.retrieve())

```
1. Query Decomposition → sub-queries
2. For each sub-query:
   a. Multi-hop retrieval (includes HyDE)
   b. Merge results with score boosting
3. Include code index results (if enabled)
4. Cross-encoder reranking
5. Return top-k results
```

### 4.3 Memory Query Types

**Semantic Memory:**
- `search(query, limit, entry_type)` - General semantic search
- `search_similar_problems(problem)` - Find solved problems
- `search_relevant_code(description)` - Find code snippets
- `search_similar_improvements(type, category)` - Find past improvements

**Conversation Memory:**
- `get_context(max_messages)` - Recent conversation
- `get_relevant_facts(query)` - Keyword-matched facts
- `get_preferences(category)` - User preferences

**Code Index:**
- `search(query, project_id, entity_type, limit)` - Code entity search

### 4.4 Compression Capabilities

**PromptCompressor:**
- Target ratio compression (default 4x)
- Phrase replacement for verbose patterns
- Token importance scoring (TF-IDF, position, type)
- Sentence structure preservation option

**ContextualCompressor:**
- Query-type detection (CODE, DEBUG, EXPLAIN, CREATIVE, RESEARCH)
- Adaptive token allocation by section
- Query-term importance boosting

---

## 5. Gaps and Limitations

### 5.1 Critical Issues

| Issue | Severity | Description | Recommendation |
|-------|----------|-------------|----------------|
| Embedding Inconsistency | HIGH | `enhanced_retrieval.py` uses sentence-transformers directly while `semantic_memory.py` uses MLX | Unify on MLX embeddings |
| Ollama Fallback | MEDIUM | `enhanced_retrieval.py` still has Ollama fallback code | Remove deprecated Ollama code |
| No Unified Vector DB | MEDIUM | Embeddings scattered across multiple stores | Consider ChromaDB or FAISS consolidation |
| Missing Embedding Persistence | HIGH | `enhanced_retrieval.py` doesn't persist embeddings | Add embedding cache to DocumentStore |

### 5.2 Feature Gaps

| Gap | Impact | Description |
|-----|--------|-------------|
| No Hybrid Search | MEDIUM | No BM25 + semantic combination |
| Limited Entity Linking | LOW | Entity extractor uses regex, not NER model |
| No Query Expansion | LOW | No synonym/related term expansion |
| No Document Chunking | MEDIUM | Documents searched as-is, not chunked |
| No Metadata Filtering | LOW | Can't filter by date, project, etc. in enhanced retrieval |

### 5.3 Memory Integration Gaps

| Gap | Impact | Description |
|-----|--------|-------------|
| Isolated Memory Systems | HIGH | SemanticMemory, ConversationMemory, FactMemory don't share data |
| No Cross-Memory Search | MEDIUM | Can't search across all memory types at once |
| Decay Not Applied to Semantic Memory | LOW | Only FactMemory has Ebbinghaus decay |
| Working Memory Not Persisted | MEDIUM | Lost on restart |

### 5.4 Performance Concerns

| Concern | Impact | Description |
|---------|--------|-------------|
| Sequential SQLite Queries | MEDIUM | DocumentStore searches DBs one at a time |
| No Batch Embedding | LOW | Embeddings generated one at a time |
| Large Index Files | LOW | Code index can grow large for big projects |
| Memory Pressure | HIGH | Loading sentence-transformers uses significant RAM |

### 5.5 Missing Features for Production

| Feature | Priority | Description |
|---------|----------|-------------|
| Embedding Updates | HIGH | No mechanism to re-embed when content changes |
| Index Versioning | MEDIUM | No version tracking for embeddings |
| Search Analytics | LOW | No tracking of query patterns/success rates |
| Relevance Feedback | MEDIUM | No user feedback incorporation |
| Cache Invalidation | MEDIUM | No strategy for stale cache entries |

---

## 6. Integration Points

### 6.1 Current Integrations

```
UnifiedOrchestrator
    |
    +---> CognitiveControl
    |         |
    |         +---> EnhancedRetrievalSystem
    |         +---> EnhancedMemoryManager
    |         +---> TokenBudgetManager
    |
    +---> SemanticMemory (standalone)
    +---> ConversationMemory (standalone)
    +---> FactMemory (standalone)
```

### 6.2 Code Index Integration

The `EnhancedRetrievalSystem` can optionally use `CodeIndexer`:

```python
# In EnhancedRetrievalSystem.__init__
if self.use_code_index and CODE_INDEXER_AVAILABLE:
    self.code_indexer = get_code_indexer()

# In retrieve()
if include_code and self.use_code_index:
    code_chunks = self._retrieve_from_code_index(query, limit=top_k)
```

### 6.3 Semantic Memory Integration

Currently standalone. Should be integrated with:
- `enhanced_retrieval.py` for unified search
- `conversation_memory.py` for automatic indexing
- `fact_memory.py` for fact embedding

---

## 7. Recommendations

### 7.1 Immediate Actions (Phase 2.2.2)

1. **Unify Embedding Backend**
   - Create `mlx_embeddings_wrapper.py` used by all modules
   - Remove sentence-transformers direct usage in enhanced_retrieval.py
   - Remove Ollama fallback code

2. **Add Embedding Persistence to DocumentStore**
   - Cache embeddings in SQLite alongside text
   - Re-embed on content change

3. **Create Unified Memory Interface**
   - Single `MemoryManager` that wraps all memory types
   - Cross-memory search capability

### 7.2 Medium-Term Improvements (Phase 2.3)

1. **Implement Hybrid Search**
   - Add BM25 scoring alongside semantic
   - RRF (Reciprocal Rank Fusion) for combining scores

2. **Add Document Chunking**
   - Smart chunking with overlap
   - Chunk-level embeddings

3. **Improve Entity Extraction**
   - Use spaCy NER when available
   - Cache entity extractions

### 7.3 Long-Term Enhancements (Phase 3+)

1. **Vector Database Migration**
   - Evaluate ChromaDB, FAISS, or LanceDB
   - Support for metadata filtering
   - Efficient similarity search at scale

2. **Query Understanding**
   - Intent classification
   - Query rewriting
   - Conversational context handling

3. **Feedback Loop**
   - Track which results were used
   - Learn from user corrections
   - Adaptive ranking

---

## 8. File Reference

### Primary Files
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/enhanced_retrieval.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/code_indexer.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/context_manager.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/conversation_memory.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/enhanced_memory.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/infinite_context.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/compression.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/fact_memory.py`

### Supporting Files
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/__init__.py`
- `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`

---

## 9. Appendix: Module Capabilities Matrix

| Capability | enhanced_retrieval | semantic_memory | code_indexer | context_manager | conversation_memory | enhanced_memory | fact_memory |
|------------|-------------------|-----------------|--------------|-----------------|---------------------|-----------------|-------------|
| Vector Embeddings | Yes (sentence-transformers) | Yes (MLX) | No | Optional | No | No | No |
| Cosine Similarity | Yes | Yes | No | Yes | No | No | No |
| SQLite Storage | Yes (search only) | No | Yes | No | Yes | Yes | Yes |
| Keyword Search | Yes | No | Yes | Yes | Yes | No | Yes |
| Memory Decay | No | No | No | No | No | Yes | Yes |
| Entity Extraction | Yes (regex/spaCy) | No | Yes (AST) | No | Yes (regex) | No | No |
| Reranking | Yes (cross-encoder) | No | No | No | No | No | No |
| Query Decomposition | Yes | No | No | No | No | No | No |
| HyDE | Yes | No | No | No | No | No | No |
| Multi-hop | Yes | No | No | No | No | No | No |
| Compression | No | No | No | Yes | No | No | No |

---

*This audit provides a foundation for Phase 2.2.2 improvements to SAM's retrieval capabilities.*
