# SAM Context Compression Strategies

**Phase:** 2.3.8 - Context Compression Documentation
**Version:** 1.0.0
**Date:** 2026-01-25
**Status:** Production

---

## Table of Contents

1. [Overview](#1-overview)
2. [Token Budget System](#2-token-budget-system)
3. [Smart Summarization Approach](#3-smart-summarization-approach)
4. [Priority Ordering (Primacy/Recency)](#4-priority-ordering-primacyrecency)
5. [Importance Scoring Algorithm](#5-importance-scoring-algorithm)
6. [Adaptive Context by Query Type](#6-adaptive-context-by-query-type)
7. [Monitoring and Stats](#7-monitoring-and-stats)
8. [Configuration Options](#8-configuration-options)
9. [Best Practices](#9-best-practices)

---

## 1. Overview

### 1.1 Why Context Compression Matters for 8GB RAM

SAM operates on an M2 Mac Mini with 8GB RAM, imposing severe context constraints:

- **Local inference**: MLX Qwen2.5-1.5B/3B models
- **Token limits**: 512-2000 tokens depending on model and task
- **Memory balance**: Model weights, KV-cache, and context compete for RAM
- **Quality trade-off**: Must maintain response quality with truncated context

**Compression Goal**: Maximize information density within token budgets (4x compression: 2000 -> 500 tokens).

### 1.2 Key Files

| File | Location | Purpose |
|------|----------|---------|
| `compression.py` | `cognitive/` | Token importance scoring, prompt compression |
| `context_budget.py` | `sam_brain/` | Budget allocation, priority ordering |
| `context_manager.py` | `sam_brain/` | Context window management, RAG integration |
| `token_budget.py` | `cognitive/` | Model-specific token limits |

---

## 2. Token Budget System

### 2.1 Model-Specific Budgets

| Model | Total | System | Context | Query | Generation |
|-------|-------|--------|---------|-------|------------|
| Qwen2.5-1.5B | 512 | 80 (15%) | 250 (49%) | 82 (16%) | 100 (20%) |
| Qwen2.5-3B | 256 | 40 (15%) | 100 (39%) | 46 (18%) | 70 (28%) |

### 2.2 High-Level Section Allocation (2000 tokens)

```python
DEFAULT_RATIOS = {
    "system_prompt": 0.05,       # 100 tokens
    "user_facts": 0.10,          # 200 tokens
    "project_context": 0.075,    # 150 tokens
    "rag_results": 0.20,         # 400 tokens
    "conversation_history": 0.25, # 500 tokens
    "working_memory": 0.075,     # 150 tokens
    # query: remainder
}
```

### 2.3 Budget Allocation Example

```python
from context_budget import ContextBudget, QueryType

budget = ContextBudget(default_budget=2000)
query_type = budget.detect_query_type("How do I implement a decorator?")
allocations = budget.allocate(query_type, available_tokens=2000)
# CODE query: rag_results=600 (1.5x), conversation_history=400 (0.8x)
```

### 2.4 Minimum Thresholds

```python
MIN_TOKENS = {
    "system_prompt": 50,
    "rag_results": 50,
    "conversation_history": 100,
    "query": 50,
    # Others can be 0
}
```

---

## 3. Smart Summarization Approach

### 3.1 LLMLingua-Style Compression

```python
from cognitive.compression import PromptCompressor, ContextualCompressor

# Basic 4x compression
compressor = PromptCompressor(target_ratio=0.25)
compressed = compressor.compress(long_text)

# Query-aware compression
contextual = ContextualCompressor()
compressed = contextual.compress_for_query(context, query, target_tokens=200)
```

### 3.2 Token Importance Scoring

Each token scored 0.0-1.0 based on:

| Signal | Weight | Description |
|--------|--------|-------------|
| Token Type | 50% | Questions/entities/technical = higher |
| TF-IDF | 30% | Rare words = higher |
| Position | 20% | Start/end = higher (U-curve) |

**Token Type Scores:**
- QUESTION: 1.0 (what, how, ?)
- ENTITY: 0.9 (proper nouns)
- TECHNICAL: 0.85 (CamelCase, snake_case)
- ACTION: 0.8 (implement, create)
- OTHER: 0.5
- CONNECTOR: 0.4 (and, but)
- COMMON: 0.3 (the, is)
- FILLER: 0.1 (basically, actually)

### 3.3 Phrase Replacement

```python
PHRASE_REPLACEMENTS = {
    "in order to": "to",
    "due to the fact that": "because",
    "at this point in time": "now",
    "a large number of": "many",
}
```

### 3.4 Conversation Compression

```python
def compress_conversation(messages, target_tokens):
    recent = messages[-2:]  # Keep last 2 verbatim
    older = messages[:-2]   # Compress the rest

    older_target = target_tokens - sum(count_tokens(m) for m in recent)
    compressed = [compress(m, older_target // len(older)) for m in older]
    return compressed + recent
```

---

## 4. Priority Ordering (Primacy/Recency)

### 4.1 The Attention U-Curve

LLMs attend more to context **beginning** (primacy) and **end** (recency). Middle receives less attention.

### 4.2 Section Priority Levels

```python
class SectionPriority(IntEnum):
    CRITICAL = 1   # System prompt, query (start/end)
    HIGH = 2       # Relevant RAG, recent history
    MEDIUM = 3     # User facts, project context
    LOW = 4        # Background, old history
    MINIMAL = 5    # Filler, low-relevance RAG
```

### 4.3 Position Hints

```python
POSITION_HINTS = {
    "system_prompt": "start",       # Always first
    "user_facts": "start",          # Early
    "query": "end",                 # Always last
    "conversation_history": "end",  # Near query
    "rag_results": None,            # Flexible
    "project_context": "middle",
    "working_memory": "middle",
}
```

### 4.4 Ordering Algorithm

1. Group sections by position hint (start/middle/end)
2. Sort each group by effective priority
3. Distribute middle sections with higher-priority items at edges
4. Combine: start -> middle -> end -> query (always last)

### 4.5 Effective Priority

```python
def effective_priority(self) -> float:
    # High relevance (1.0) boosts priority by up to 2 levels
    relevance_boost = (1.0 - self.relevance_score) * 2
    return float(self.priority) + relevance_boost
```

---

## 5. Importance Scoring Algorithm

### 5.1 Multi-Factor Scoring

```python
importance = (
    query_relevance * rel_weight +
    recency_score * rec_weight +
    reliability_score * reliability_weight +
    usage_score * usage_weight
)
```

### 5.2 Weights by Context Type

| Context Type | Relevance | Recency | Reliability | Usage |
|--------------|-----------|---------|-------------|-------|
| RAG Result | 0.50 | 0.15 | 0.20 | 0.15 |
| Conversation | 0.30 | 0.45 | 0.10 | 0.15 |
| User Fact | 0.35 | 0.10 | 0.30 | 0.25 |
| Working Memory | 0.25 | 0.50 | 0.10 | 0.15 |
| Code Snippet | 0.55 | 0.10 | 0.20 | 0.15 |

### 5.3 Query Relevance

**Semantic** (MLX embeddings):
```python
similarity = np.dot(query_emb, content_emb) / (norms)
return (similarity + 1) / 2  # Normalize to [0, 1]
```

**Fallback** (keyword overlap):
```python
overlap = len(query_words & content_words)
return min(1.0, overlap / len(query_words))
```

### 5.4 Recency Score

Exponential decay with type-specific half-life:

| Context Type | Half-Life |
|--------------|-----------|
| Working Memory | 5 minutes |
| Conversation | 1 hour |
| RAG Result | 1 day |
| Code Snippet | 3 days |
| Documentation | 30 days |
| User Fact | 1 year |
| System Prompt | Never decays |

```python
decay = 0.5 ** (age_seconds / halflife)
return max(0.1, decay)
```

### 5.5 Reliability Score

```python
BASE_RELIABILITY = {
    ContextType.SYSTEM_PROMPT: 1.0,
    ContextType.USER_FACT: 0.9,
    ContextType.DOCUMENTATION: 0.85,
    ContextType.CODE_SNIPPET: 0.8,
    ContextType.RAG_RESULT: 0.5,
}
```

### 5.6 Usage Score

Wilson score interval tracking historical effectiveness:

```python
scorer.record_usage(content_id="abc123", was_helpful=True)
# Tracks uses/successes for each content piece
```

---

## 6. Adaptive Context by Query Type

### 6.1 Query Type Detection

```python
def detect_query_type(query: str) -> QueryType:
    # CODE: code, function, class, bug, python
    # RECALL: remember, recall, what was, earlier
    # REASONING: why, explain, analyze, compare
    # PROJECT: project, codebase, architecture
    # ROLEPLAY: roleplay, pretend, act as
    # Default: CHAT
```

### 6.2 Budget Adjustments

| Query Type | RAG | History | User Facts |
|------------|-----|---------|------------|
| CHAT | 0.7x | 1.3x | 1.2x |
| CODE | 1.5x | 0.8x | 1.0x |
| RECALL | 0.7x | 1.3x | 1.5x |
| REASONING | 1.3x | 0.9x | 1.0x |
| ROLEPLAY | 0.5x | 1.4x | 1.0x |
| PROJECT | 1.2x | 1.0x | 0.8x |

### 6.3 Compression Boosts

```python
# CODE queries: boost technical tokens
if query_type == QueryType.CODE:
    if token.token_type == TokenType.TECHNICAL:
        token.importance += 0.15

# DEBUG queries: boost error tokens
elif query_type == QueryType.DEBUG:
    if 'error' in token_lower or 'exception' in token_lower:
        token.importance += 0.2
```

---

## 7. Monitoring and Stats

### 7.1 Compression Statistics

```python
stats = compressor.get_last_stats()
# CompressionStats(
#     original_tokens=800,
#     compressed_tokens=200,
#     ratio=0.25,
#     query_type="code",
#     importance_threshold=0.45
# )
```

### 7.2 Budget Allocation Stats

```python
stats = budget.get_allocation_stats()
# {
#     "total_allocations": 42,
#     "average_by_section": {"system_prompt": 95.2, ...},
#     "last_allocation": {...}
# }
```

### 7.3 Context Metadata

```python
context, metadata = builder.build_ordered(query, ...)
# metadata["section_order"] = [
#     {"position": 0, "name": "system_prompt", "priority": "CRITICAL"},
#     ...
# ]
# metadata["attention_positions"] = {"primacy": "system_prompt", "recency": "query"}
```

---

## 8. Configuration Options

### 8.1 PromptCompressor

```python
compressor = PromptCompressor(target_ratio=0.25)  # 4x compression
compressed = compressor.compress(text, target_tokens=None, preserve_structure=True)
```

### 8.2 ContextBudget

```python
budget = ContextBudget(default_budget=2000)
allocations = budget.allocate(
    query_type=QueryType.CODE,
    available_tokens=2000,
    custom_priorities={"rag_results": 2.0}  # Double RAG
)
```

### 8.3 ContextBuilder

```python
builder = ContextBuilder(budget)

# Standard build
context, usage = builder.build(query, system_prompt, rag_results, ...)

# Ordered build (attention-optimized)
context, metadata = builder.build_ordered(
    query,
    rag_results=[("content", 0.95), ("content", 0.70)]  # With relevance
)
```

### 8.4 ContextImportanceScorer

```python
scorer = ContextImportanceScorer(
    use_embeddings=True,
    usage_history_path="/path/to/history.json"
)
```

### 8.5 Preset Budgets

```python
from cognitive.token_budget import get_preset_budget
budget = get_preset_budget("1.5b_full")  # or "1.5b_minimal", "3b_full", "3b_minimal"
```

---

## 9. Best Practices

### 9.1 When to Compress

**DO compress:** RAG results, old history, long code, multi-document contexts

**DON'T compress:** System prompts, recent conversation (last 2-3 turns), current query

### 9.2 Compression Ratios

| Context Type | Ratio | Notes |
|--------------|-------|-------|
| RAG results | 3-5x | Aggressive OK |
| Old history | 2.5-3x | Keep key points |
| Documentation | 3-4x | Preserve structure |
| Code | 1.5-2x | Conservative |

### 9.3 Preserving Key Information

```python
# Always preserve questions
if token.lower() in QUESTION_WORDS or token.endswith("?"):
    token.is_preserved = True

# Preserve entities
if token[0].isupper() and len(token) > 1:
    token.importance = max(token.importance, 0.9)
```

### 9.4 Tokenization Consistency

Use consistent method across modules:

```python
TOKENIZATION_FACTOR = 1.3  # words * 1.3 = tokens
def count_tokens(text): return int(len(text.split()) * TOKENIZATION_FACTOR)
```

### 9.5 Reduce XML Tag Overhead

Current tags (~40 tokens). Use compact format:

```python
COMPACT_TAGS = {
    "system_prompt": "[S]",
    "user_facts": "[U]",
    "rag_results": "[R]",
    "query": "[Q]",
}
```

### 9.6 Emergency Compression

When massively over budget:

```python
def emergency_compress(context, max_tokens):
    sentences = split_sentences(context)
    kept = [sentences[0]]  # First (primacy)

    # Keep sentences with key markers
    for sent in sentences[1:-1]:
        if any(m in sent.lower() for m in ['error', '?', 'code:']):
            kept.append(sent)

    kept.append(sentences[-1])  # Last (recency)
    return " ".join(kept)
```

### 9.7 Quality Monitoring

```python
if response_quality < 0.7 and compression_applied:
    log_compression_issue({
        "compression_ratio": stats.ratio,
        "importance_threshold": stats.importance_threshold
    })
```

---

## Related Documentation

| Document | Location |
|----------|----------|
| RAG_SYSTEM.md | `sam_brain/docs/` |
| MEMORY_SYSTEM.md | `sam_brain/docs/` |
| TOKEN_USAGE_ANALYSIS.md | `sam_brain/docs/` |

---

*Phase 2.3.8 - Context Compression Strategies*
*Last updated: 2026-01-25*
