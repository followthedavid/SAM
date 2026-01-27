# SAM RAG System Documentation

**Version:** Phase 2.2.12
**Last Updated:** 2026-01-24
**Status:** Production

---

## 1. Overview

SAM's Retrieval-Augmented Generation (RAG) system enables intelligent context retrieval for improved response quality. Rather than relying solely on the model's training data, SAM retrieves relevant information from indexed code, documentation, and memories to provide accurate, context-aware responses.

### Design Principles

1. **MLX-Native**: All embeddings use native Apple Silicon via MLX for optimal performance on 8GB RAM
2. **Multi-Source**: Combines code, documentation, and memory retrieval in a unified pipeline
3. **Lightweight**: No heavy dependencies - works without Ollama or external services
4. **Incremental**: File watching enables automatic index updates without full re-indexing

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Semantic Search | Vector similarity using 384-dim MiniLM embeddings |
| Code Indexing | Function, class, and module extraction with signatures |
| Doc Indexing | Markdown sections and code comments |
| Query Decomposition | Complex queries split into sub-queries |
| Multi-Factor Reranking | Combines semantic, keyword, and metadata scores |
| Context Budget | Intelligent token allocation across context sections |

---

## 2. Architecture Diagram

```
+------------------+
|   User Query     |
+--------+---------+
         |
         v
+--------+---------+
| QueryDecomposer  |  Splits complex queries into sub-queries
+--------+---------+  ("X and Y" -> ["X", "Y"])
         |
         +-----------------+-----------------+
         |                 |                 |
         v                 v                 v
+--------+------+  +-------+-------+  +------+--------+
| CodeIndexer   |  | DocIndexer    |  | SemanticMemory|
| (Python, Rust,|  | (Markdown,    |  | (Interactions,|
|  Swift, TS)   |  |  Comments)    |  |  Solutions)   |
+-------+-------+  +-------+-------+  +-------+-------+
         |                 |                 |
         +--------+--------+-----------------+
                  |
                  v
         +--------+--------+
         | RelevanceScorer |  Multi-factor reranking
         +--------+--------+
                  |
                  v
         +--------+--------+
         | ContextBudget   |  Token allocation
         +--------+--------+
                  |
                  v
         +--------+--------+
         | MLX Generation  |  Qwen2.5 + SAM LoRA
         +------------------+
```

### Data Flow

1. **Query Ingestion**: User query enters the system
2. **Decomposition**: Complex queries split into searchable sub-queries
3. **Parallel Retrieval**: Multiple indexers search simultaneously
4. **Deduplication**: Results merged with score boosting for overlaps
5. **Reranking**: Multi-factor scoring adjusts result ordering
6. **Budget Allocation**: Context sections sized by query type
7. **Generation**: Retrieved context augments prompt for MLX inference

---

## 3. Core Components

### 3.1 CodeIndexer

**File:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/code_indexer.py`

The CodeIndexer parses source files and extracts semantic units (functions, classes, modules) with their signatures, docstrings, and content for embedding.

#### Supported Languages

| Language | Parser | Symbol Types |
|----------|--------|--------------|
| Python | AST-based | function, class, method, module |
| Rust | Regex | function, struct, enum, trait, module |
| Swift | Regex | function, class, struct, enum, protocol, module |
| TypeScript/JavaScript | Regex | function, class, interface, type, module |

#### CodeSymbol Structure

```python
@dataclass
class CodeSymbol:
    id: str              # MD5 hash (12 chars)
    name: str            # Symbol name
    symbol_type: str     # function, class, method, module, etc.
    signature: str       # Full signature with type hints
    docstring: str       # Documentation (up to 1000 chars)
    file_path: str       # Absolute file path
    line_number: int     # Starting line
    content: str         # Content for embedding (up to 600 chars)
    project_id: str      # Project identifier
    imports: str         # JSON list of imports (for modules)
    embedding: bytes     # 384-dim float32 vector (serialized)
```

#### Key Methods

```python
# Index an entire project
indexer = CodeIndexer()
stats = indexer.index_project("/path/to/project", project_id="my_project")

# Search with semantic similarity
results = indexer.search("memory storage", limit=10)
# Returns: List[Tuple[CodeSymbol, float]]  # (symbol, similarity_score)

# Get context for a symbol
context = indexer.get_symbol_context("SemanticMemory")
# Returns related symbols in same file and similar names

# Smart search with query decomposition
from code_indexer import smart_search
results = smart_search("auth and logging handlers", limit=10)
```

#### Storage Location

- **Database:** `/Volumes/David External/sam_memory/code_index.db`
- **Tables:** `code_symbols`, `indexed_files`
- **Embeddings:** Stored as BLOB in `code_symbols.embedding`

---

### 3.2 DocIndexer

**File:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/doc_indexer.py`

The DocIndexer extracts and indexes documentation from markdown files and code comments.

#### Document Types

| Type | Source | Description |
|------|--------|-------------|
| markdown | .md, .markdown files | Parsed into sections by headings |
| docstring | Python, Rust | Module/function documentation |
| comment | All languages | Inline comments (consecutive grouped) |
| block_comment | JS/TS, Rust | Multi-line block comments |

#### DocEntity Structure

```python
@dataclass
class DocEntity:
    id: str              # MD5 hash (12 chars)
    doc_type: str        # markdown, docstring, comment, block_comment
    file_path: str       # Source file path
    section_title: str   # Heading or description
    content: str         # Full content (chunked to 1500 chars max)
    line_number: int     # Starting line
    project_id: str      # Project identifier
    embedding: bytes     # 384-dim vector (stored separately)
```

#### Key Methods

```python
# Index documentation
indexer = DocIndexer()
stats = indexer.index_docs("/path/to/project", project_id="my_project")

# Search documents
results = indexer.search_docs("memory system", limit=10, doc_type="markdown")

# Get all docs for a file
docs = indexer.get_doc_context("/path/to/file.md")
```

#### Section Chunking

Markdown files are intelligently chunked:

1. Split by heading hierarchy (h1-h6)
2. Large sections (>1500 chars) chunked by paragraph
3. Code blocks preserved intact
4. Each chunk gets title: "Section Name (part N)"

---

### 3.3 QueryDecomposer

**File:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/query_decomposer.py`

The QueryDecomposer detects complex queries and splits them into simpler sub-queries for better retrieval accuracy.

#### Decomposition Strategies

| Strategy | Pattern | Example |
|----------|---------|---------|
| Conjunction | "X and Y", "X or Y" | "auth and logging" -> ["auth", "logging"] |
| Combined List | "A, B, and C" | "read, write, and delete" -> 3 queries |
| Multi-topic | Multiple topic clusters | "database logging" -> ["database", "logging"] |
| Multi-question | Multiple question words | "How X? Where Y?" -> 2 queries |

#### Key Methods

```python
from query_decomposer import QueryDecomposer, is_complex_query, decompose

decomposer = QueryDecomposer()

# Check if decomposition would help
if decomposer.is_complex_query("auth and logging"):
    result = decomposer.decompose("auth and logging")
    # result.sub_queries = ["auth", "logging"]
    # result.query_type = "conjunction"
    # result.confidence = 0.9

# Search with automatic decomposition
from query_decomposer import search_with_decomposition
results = search_with_decomposition(query, indexer, limit=10)
```

#### Topic Clusters

The decomposer recognizes related terms:

```python
TOPIC_CLUSTERS = {
    'authentication': ['auth', 'login', 'logout', 'session', 'token'],
    'logging': ['log', 'logger', 'debug', 'trace', 'error'],
    'database': ['db', 'sql', 'query', 'model', 'schema'],
    'memory': ['memory', 'cache', 'store', 'storage', 'persist'],
    # ... more clusters
}
```

---

### 3.4 RelevanceScorer

**File:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/relevance_scorer.py`

The RelevanceScorer provides multi-factor reranking of search results, optimized for 8GB RAM constraints.

#### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Semantic | 0.35 | Embedding similarity (MLX) |
| Keyword | 0.20 | Token overlap with stemming |
| Symbol Type | 0.15 | Priority: class > function > variable |
| Doc Quality | 0.10 | Docstring presence and length |
| Name Match | 0.10 | Query terms in symbol name |
| Recency | 0.10 | File modification time decay |

#### Specialized Scorers

```python
# For code results (emphasizes symbol type)
from relevance_scorer import CodeRelevanceScorer
scorer = CodeRelevanceScorer()

# For documentation (emphasizes semantic)
from relevance_scorer import DocRelevanceScorer
scorer = DocRelevanceScorer()

# Mixed results
from relevance_scorer import rerank_mixed_results
results = rerank_mixed_results(query, code_results, doc_results, code_weight=0.6)
```

#### ScoredResult Structure

```python
@dataclass
class ScoredResult:
    id: str
    name: str
    type: str
    content: str
    file_path: str
    line_number: int

    # Score breakdown
    final_score: float
    semantic_score: float
    keyword_score: float
    type_score: float
    doc_quality_score: float
    name_score: float
    recency_score: float
```

---

### 3.5 ContextBudget

**File:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/context_budget.py`

The ContextBudget allocates tokens across context sections based on query type.

#### Query Types

| Type | RAG Weight | History Weight | Best For |
|------|------------|----------------|----------|
| CHAT | 0.7x | 1.3x | Casual conversation |
| CODE | 1.5x | 0.8x | Programming help |
| RECALL | 0.7x | 1.3x | Memory retrieval |
| REASONING | 1.3x | 0.9x | Complex analysis |
| ROLEPLAY | 0.5x | 1.4x | Persona interactions |
| PROJECT | 1.5x | 1.0x | Project-specific queries |

#### Default Token Allocation (2000 tokens)

```
Section              | Base Tokens | Purpose
---------------------|-------------|---------------------------
system_prompt        | 100 (fixed) | SAM personality
user_facts           | 200         | User preferences/info
project_context      | 150         | Current project state
rag_results          | 400         | Retrieved context
conversation_history | 500         | Recent messages
working_memory       | 150         | Short-term memory
query                | ~200        | User's message
```

#### Key Methods

```python
from context_budget import ContextBudget, ContextBuilder, QueryType

budget = ContextBudget(default_budget=2000)

# Detect query type automatically
query_type = budget.detect_query_type("How do I implement a decorator?")
# Returns: QueryType.CODE

# Get optimal RAG budget
rag_tokens = budget.get_rag_budget(2000, QueryType.CODE, consumed=500)

# Build complete context
builder = ContextBuilder(budget)
context, usage = builder.build(
    query="...",
    system_prompt="...",
    rag_results="...",
    conversation_history="...",
    total_tokens=2000
)
```

#### Intelligent Truncation

Different sections use different truncation strategies:

- **System Prompt**: Preserve start (personality first)
- **Conversation History**: Preserve end (recent messages)
- **RAG Results**: Preserve complete chunks

---

## 4. Embedding Model and Storage

### Embedding Model

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Dimensions:** 384
**Backend:** MLX (native Apple Silicon)
**Speed:** ~10ms per embedding

```python
# Embedding generation (from semantic_memory.py)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def _get_embedding(text: str) -> Optional[np.ndarray]:
    import mlx_embeddings

    model, tokenizer = mlx_embeddings.load(EMBEDDING_MODEL)
    output = mlx_embeddings.generate(model, tokenizer, text[:2000])
    return np.array(output.text_embeds[0])  # 384-dim
```

### Storage Locations

| Data | Location | Format |
|------|----------|--------|
| Code Index | `/Volumes/David External/sam_memory/code_index.db` | SQLite |
| Doc Embeddings | Same as code index | SQLite (separate table) |
| Semantic Memory | `sam_brain/memory/embeddings.json` | JSON |
| Semantic Index | `sam_brain/memory/index.npy` | NumPy |

### Database Schema

```sql
-- Code symbols with embeddings
CREATE TABLE code_symbols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    signature TEXT,
    docstring TEXT,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    content TEXT,
    project_id TEXT,
    imports TEXT,
    embedding BLOB,  -- 384 x float32 = 1536 bytes
    indexed_at REAL
);

-- Document entities
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    line_number INTEGER,
    project_id TEXT,
    indexed_at REAL
);

-- Document embeddings (separate for efficiency)
CREATE TABLE doc_embeddings (
    doc_id TEXT PRIMARY KEY,
    embedding BLOB,
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

-- File tracking for incremental updates
CREATE TABLE indexed_files (
    file_path TEXT PRIMARY KEY,
    project_id TEXT,
    mtime REAL,
    indexed_at REAL
);
```

---

## 5. Indexing Workflow

### Initial Project Indexing

```bash
# Index SAM brain codebase
python code_indexer.py index /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain \
    --project sam_brain

# Index documentation
python cognitive/doc_indexer.py index /path/to/docs --project my_project
```

### Incremental Updates (File Watching)

The IndexWatcher monitors for file changes and updates the index automatically.

```python
from code_indexer import IndexWatcher, get_indexer

# Start watching with callbacks
watcher = IndexWatcher(
    indexer=get_indexer(),
    poll_interval=30.0,     # Check every 30 seconds
    auto_index=True,        # Auto-update on changes
    generate_embeddings=True
)

# Register change callback
watcher.on_file_change(lambda change: print(f"{change.change_type}: {change.file_path}"))

# Start watching
watcher.start("/path/to/project", "my_project")

# Later: stop watching
watcher.stop()
```

### Batch Reindexing

```bash
# Force reindex (ignore mtime)
python code_indexer.py index /path/to/project --project my_project --force

# Without embeddings (faster, keyword-only search)
python code_indexer.py index /path/to/project --no-embeddings
```

### Watch Mode CLI

```bash
# Watch with auto-indexing
python code_indexer.py watch /path/to/project --project my_project --interval 30

# Watch and report only (no auto-index)
python code_indexer.py watch /path/to/project --no-auto-index
```

---

## 6. Search Flow

### Complete Search Pipeline

```python
from code_indexer import smart_search
from cognitive.doc_indexer import get_doc_indexer
from relevance_scorer import rerank_mixed_results
from context_budget import ContextBudget, ContextBuilder

# 1. Search code
code_results = smart_search("memory storage implementation", limit=20)

# 2. Search documentation
doc_indexer = get_doc_indexer()
doc_results = doc_indexer.search_docs("memory storage", limit=20)

# 3. Rerank combined results
reranked = rerank_mixed_results(
    query="memory storage implementation",
    code_results=code_results,
    doc_results=doc_results,
    limit=10,
    code_weight=0.6  # Favor code over docs
)

# 4. Allocate context budget
budget = ContextBudget()
builder = ContextBuilder(budget)

# 5. Build context string
rag_content = "\n\n---\n\n".join([
    f"[{r.type}] {r.name}\n{r.content[:500]}"
    for r in reranked[:5]
])

context, usage = builder.build(
    query="How does the memory system store data?",
    rag_results=rag_content,
    total_tokens=2000
)
```

### Semantic Search Details

```python
def search(query: str, limit: int = 10) -> List[Tuple[CodeSymbol, float]]:
    # 1. Generate query embedding
    query_embedding = _get_embedding(query)

    # 2. Load all symbol embeddings from DB
    # 3. Compute cosine similarity
    for symbol in symbols:
        doc_embedding = np.frombuffer(symbol.embedding, dtype=np.float32)
        similarity = np.dot(query_embedding, doc_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
        )
        results.append((symbol, similarity))

    # 4. Sort by similarity
    results.sort(key=lambda x: -x[1])
    return results[:limit]
```

### Fallback to Keyword Search

When embeddings are unavailable (model not loaded, MLX error):

```python
# Keyword fallback in code_indexer.py
sql = """
    SELECT * FROM code_symbols
    WHERE name LIKE ? OR signature LIKE ? OR content LIKE ? OR docstring LIKE ?
"""
params = [f"%{query}%"] * 4
```

---

## 7. CLI Commands

### Code Indexer CLI

```bash
# Index a project
python code_indexer.py index /path/to/project [--project ID] [--force] [--no-embeddings]

# Watch for changes
python code_indexer.py watch /path/to/project [--interval 30] [--no-auto-index]

# Search code
python code_indexer.py search "query" [--project ID] [--type function] [--limit 10] [--smart]

# Get symbol context
python code_indexer.py context SYMBOL_NAME [--project ID]

# Show statistics
python code_indexer.py stats [--project ID]

# List indexed projects
python code_indexer.py list

# Clear project index
python code_indexer.py clear PROJECT_ID
```

### Doc Indexer CLI

```bash
# Index documentation
python cognitive/doc_indexer.py index --path /path/to/docs --project ID [--force]

# Search documents
python cognitive/doc_indexer.py search --query "query" [--type markdown] [--limit 10]

# Get file context
python cognitive/doc_indexer.py context --path /path/to/file.md

# Show statistics
python cognitive/doc_indexer.py stats [--project ID]

# Clear project
python cognitive/doc_indexer.py clear PROJECT_ID
```

### Query Decomposer CLI

```bash
# Check if query is complex
python query_decomposer.py check "auth and logging handlers"

# Decompose a query
python query_decomposer.py decompose "find Python files handling auth, logging, and database"

# Search with decomposition
python query_decomposer.py search "memory system and storage location"

# Run test cases
python query_decomposer.py test
```

### Relevance Scorer CLI

```bash
# Demo with mock results
python relevance_scorer.py demo

# Score single text
python relevance_scorer.py score --query "search" --text "search documents function"

# Show default weights
python relevance_scorer.py weights
```

### Context Budget CLI

```bash
# Run demo (no args needed)
python context_budget.py
```

---

## 8. API Endpoints

The RAG system integrates with SAM's HTTP API via `sam_api.py`.

### Cognitive Processing

```
POST /api/cognitive/process
Content-Type: application/json

{
  "query": "How does the memory system work?",
  "user_id": "default"
}

Response:
{
  "success": true,
  "response": "The memory system uses...",
  "confidence": 0.85,
  "model_used": "mlx-qwen2.5-1.5b",
  "escalated": false
}
```

### Search Endpoints

```
GET /api/search?q=memory+storage
POST /api/code/search
{
  "query": "memory storage",
  "project_id": "sam_brain",
  "limit": 10
}
```

### Index Management

```
POST /api/index/project
{
  "path": "/path/to/project",
  "project_id": "my_project",
  "force": false
}

GET /api/index/stats?project_id=sam_brain
GET /api/index/projects
DELETE /api/index/project/{project_id}
```

### Orchestrator Route

```
POST /api/orchestrate
{
  "message": "How do I implement memory caching?",
  "auto_escalate": true
}

Response:
{
  "route": "code",
  "model": "mlx-1.5b",
  "response": "...",
  "escalated": false
}
```

---

## 9. Integration with Orchestrator

The orchestrator (`orchestrator.py`) routes queries to appropriate handlers and integrates RAG for context.

### Route Detection

```python
def route_request(message: str) -> str:
    message_lower = message.lower()

    # Code patterns -> use code index
    if any(kw in message_lower for kw in ["code", "function", "bug", "python"]):
        return "CODE"

    # Project patterns -> use project context
    if any(kw in message_lower for kw in ["project", "architecture", "structure"]):
        return "PROJECT"

    # Memory/recall -> use semantic memory
    if any(kw in message_lower for kw in ["remember", "recall", "earlier"]):
        return "RECALL"

    return "CHAT"
```

### Context Injection

```python
def handle_code(message: str) -> str:
    # 1. Search code index
    from code_indexer import smart_search
    results = smart_search(message, limit=5)

    # 2. Format as context
    context = "\n".join([
        f"[{s.symbol_type}] {s.name}: {s.signature}\n{s.docstring or ''}"
        for s, score in results
    ])

    # 3. Generate with context
    prompt = f"""Context from codebase:
{context}

User: {message}
Response:"""

    return _mlx_generate(prompt, max_tokens=512)
```

### Memory Integration

```python
from semantic_memory import get_memory

# Add interaction to memory
memory = get_memory()
memory.add_interaction(query, response, project="sam_brain", success=True)

# Retrieve relevant context
context = memory.get_context_for_query(query, max_entries=3)
```

---

## 10. Troubleshooting

### Common Issues

#### MLX Embeddings Not Loading

**Symptom:** Search returns no results or falls back to keyword search

**Solution:**
```bash
# Install mlx-embeddings
pip install mlx-embeddings

# Test embedding generation
python -c "import mlx_embeddings; print(mlx_embeddings.load('sentence-transformers/all-MiniLM-L6-v2'))"
```

#### Empty Search Results

**Symptom:** Search returns empty list

**Causes and Solutions:**

1. **Index not built**: Run `python code_indexer.py index /path`
2. **Wrong project_id**: Check with `python code_indexer.py list`
3. **No embeddings**: Add `--no-embeddings` or generate: `python code_indexer.py index --force`

#### Slow Indexing

**Symptom:** Initial indexing takes too long

**Solutions:**
```bash
# Skip embeddings for faster indexing
python code_indexer.py index /path --no-embeddings

# Index specific subdirectories
python code_indexer.py index /path/to/src --project my_project
```

#### Database Locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Check for running processes
lsof /Volumes/David\ External/sam_memory/code_index.db

# Force close connections (restart Python processes)
```

#### Out of Memory

**Symptom:** Process killed during embedding generation

**Solutions:**
1. Process files in batches
2. Reduce `MAX_CHUNK_SIZE` in doc_indexer.py
3. Use `--no-embeddings` and rely on keyword search

### Diagnostics

```bash
# Check index statistics
python code_indexer.py stats

# Output:
# {
#   "total_symbols": 1234,
#   "by_type": {"function": 500, "class": 200, ...},
#   "with_embeddings": 1200,
#   "files_indexed": 150,
#   "projects": ["sam_brain", "warp_tauri"]
# }

# Verify embedding model
python -c "
from code_indexer import _get_embedding
import numpy as np
e = _get_embedding('test query')
print(f'Embedding shape: {e.shape if e is not None else None}')
print(f'Embedding type: {e.dtype if e is not None else None}')
"
```

### Performance Tuning

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `MAX_CHUNK_SIZE` | doc_indexer.py | 1500 | Max chars per doc chunk |
| `poll_interval` | IndexWatcher | 30s | File change polling interval |
| `CHARS_PER_TOKEN` | context_budget.py | 4 | Token estimation ratio |
| `recency_decay_days` | relevance_scorer.py | 30 | Days until recency = 0.5 |

### Log Locations

- **Embedding errors:** Printed to stderr
- **Index updates:** `watcher.get_stats()` for counts
- **API errors:** sam_api.py console output

---

## 11. File Reference

### Primary Files

| File | Purpose |
|------|---------|
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/code_indexer.py` | Code symbol extraction and indexing |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/doc_indexer.py` | Documentation indexing |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/query_decomposer.py` | Query splitting |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/relevance_scorer.py` | Multi-factor reranking |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/context_budget.py` | Token allocation |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/semantic_memory.py` | Vector memory storage |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/enhanced_retrieval.py` | HyDE and multi-hop retrieval |

### Supporting Files

| File | Purpose |
|------|---------|
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/orchestrator.py` | Request routing and context injection |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/sam_api.py` | HTTP/CLI API |
| `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/__init__.py` | Cognitive module exports |

### Storage Locations

| Data | Path |
|------|------|
| Code Index DB | `/Volumes/David External/sam_memory/code_index.db` |
| Memory Embeddings | `sam_brain/memory/embeddings.json` |
| Memory Index | `sam_brain/memory/index.npy` |

---

## 12. Best Practices

### Indexing

1. **Project Naming**: Use consistent project IDs across code and doc indexing
2. **Incremental Updates**: Use file watching in development, batch in CI
3. **Embedding Generation**: Always generate embeddings for production quality
4. **Skip Patterns**: Add noisy directories to `SKIP_DIRS` set

### Querying

1. **Query Length**: Keep queries 5-20 words for best results
2. **Decomposition**: Let QueryDecomposer handle complex queries automatically
3. **Type Filters**: Use `symbol_type` filter when you know what you want
4. **Project Scope**: Filter by project_id to reduce noise

### Context Building

1. **Budget Awareness**: Check `usage["total"]` doesn't exceed model context
2. **Query Type**: Let `detect_query_type()` adjust allocations automatically
3. **Truncation**: Trust `fit_content()` to preserve important parts
4. **Overlap**: Allow some overlap between sections for coherence

### Performance

1. **Lazy Loading**: Embeddings model loads on first use, not import
2. **Caching**: RelevanceScorer caches embeddings (500 entries)
3. **Batch Processing**: Index files in batches when possible
4. **Parallel Search**: QueryDecomposer searches sub-queries in parallel

---

*This documentation reflects the RAG system as of Phase 2.2.12. For historical context, see RAG_AUDIT.md.*
