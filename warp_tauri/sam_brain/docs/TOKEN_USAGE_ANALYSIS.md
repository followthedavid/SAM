# SAM Token Usage Analysis

*Phase 2.3.1 Research Document - Created 2026-01-24*

## Executive Summary

SAM's context system operates under extremely tight token constraints (512 tokens for 1.5B model, 256 for 3B model) due to 8GB RAM hardware limits. This analysis identifies **significant redundancy and optimization opportunities** that could recover 80-120 tokens per request.

## Current Token Budgets

### Three Budget Systems (Problem: Overlap & Inconsistency)

SAM has **three separate budget allocation systems** that define different allocations:

#### 1. ContextManager (context_manager.py)
```python
MAX_TOKENS = 512
BUDGET = {
    'critical': 100,   # Personality + system prompt
    'rag': 150,        # Retrieved context
    'history': 200,    # Conversation history
    'query': 62        # User input
}
# Total: 512 tokens
```

#### 2. ContextBudget (context_budget.py)
```python
# For 2000 token budget (higher-level API)
DEFAULT_RATIOS = {
    "system_prompt": 0.05,       # 100 tokens
    "user_facts": 0.10,          # 200 tokens
    "project_context": 0.075,    # 150 tokens
    "rag_results": 0.20,         # 400 tokens
    "conversation_history": 0.25, # 500 tokens
    "working_memory": 0.075,     # 150 tokens
    # query: remainder (~200 tokens)
}
```

#### 3. TokenBudgetManager (token_budget.py)
```python
# 1.5B Model (512 tokens)
ALLOCATION_RATIOS = {
    "system": 0.15,      # 80 tokens
    "context": 0.49,     # 250 tokens
    "query": 0.16,       # 82 tokens
    "generation": 0.20   # 100 tokens
}

# 3B Model (256 tokens)
ALLOCATION_RATIOS = {
    "system": 0.15,     # 40 tokens
    "context": 0.39,    # 100 tokens
    "query": 0.18,      # 46 tokens
    "generation": 0.28  # 70 tokens
}
```

#### 4. CognitiveOrchestrator (unified_orchestrator.py)
```python
MAX_CONTEXT_TOKENS = 512
SYSTEM_PROMPT_TOKENS = 80
USER_FACTS_TOKENS = 200
PROJECT_CONTEXT_TOKENS = 100
RETRIEVAL_TOKENS = 150
HISTORY_TOKENS = 200
QUERY_TOKENS = 62
RESERVE_TOKENS = 20
# Total: 812 tokens (EXCEEDS MAX!)
```

### Budget Inconsistency Analysis

| Section | context_manager | context_budget | token_budget | orchestrator |
|---------|-----------------|----------------|--------------|--------------|
| System | 100 | 100 (5%) | 80 (15%) | 80 |
| User Facts | - | 200 (10%) | - | 200 |
| Project | - | 150 (7.5%) | - | 100 |
| RAG | 150 | 400 (20%) | 250* | 150 |
| History | 200 | 500 (25%) | included* | 200 |
| Working Memory | - | 150 (7.5%) | - | - |
| Query | 62 | ~200 | 82 | 62 |
| Generation | - | - | 100 | 20 |
| **Total** | **512** | **~2000** | **512** | **812** |

**Critical Finding**: The orchestrator's section budgets sum to 812 tokens, but MAX_CONTEXT_TOKENS is 512. This means context is always being truncated.

---

## Typical vs Worst-Case Usage

### Typical Request (Chat)

| Section | Budget | Typical | Worst Case |
|---------|--------|---------|------------|
| System prompt | 80 | 45 | 80 |
| User facts | 200 | 80 | 200 |
| Project context | 100 | 60 | 100 |
| RAG context | 150 | 100 | 300 |
| History | 200 | 150 | 400 |
| Query | 62 | 30 | 100 |
| **Total** | 512 | 465 | 1180 |
| **Overflow** | - | -47 (ok) | +668 (truncated) |

### By Query Type (ContextBudget allocations)

| Query Type | RAG Priority | History Priority | Notable Adjustment |
|------------|--------------|------------------|-------------------|
| CHAT | 0.7x (280) | 1.3x (650) | More history |
| CODE | 1.5x (600) | 0.8x (400) | More RAG |
| RECALL | 0.7x (280) | 1.3x (650) | More user_facts (1.5x) |
| REASONING | 1.3x (520) | 0.9x (450) | Balanced |
| ROLEPLAY | 0.5x (200) | 1.4x (700) | Heavy history |
| PROJECT | 1.2x (480) | - | project_context 1.5x |

---

## Redundancy Patterns Found

### 1. XML Tag Overhead (~40 tokens wasted)

Current context structure uses verbose XML:
```xml
<SYSTEM>
You are SAM, a confident and charming AI assistant...
</SYSTEM>

<USER>
User prefers concise answers...
</USER>

<PROJECT name="sam_brain" status="active">
Working on: Token optimization...
</PROJECT>

<CONTEXT>
Retrieved: Function definitions...
</CONTEXT>

<WORKING>
Recent: Discussed context management...
</WORKING>

<QUERY>
How do I optimize token usage?
</QUERY>
```

**Overhead calculation:**
- `<SYSTEM>\n...\n</SYSTEM>` = ~20 chars = 5 tokens
- `<USER>\n...\n</USER>` = ~18 chars = 4.5 tokens
- `<PROJECT name="..." status="...">` = ~40 chars = 10 tokens
- `<CONTEXT>\n...\n</CONTEXT>` = ~22 chars = 5.5 tokens
- `<WORKING>\n...\n</WORKING>` = ~22 chars = 5.5 tokens
- `<QUERY>\n...\n</QUERY>` = ~18 chars = 4.5 tokens
- Separator newlines = ~12 chars = 3 tokens

**Total XML overhead: ~38 tokens (7% of 512 budget)**

### 2. Repeated Information Across Sections

**System prompt redundancy:**
```python
# In context_manager.py (default personality)
personality = "You are SAM, a confident and flirty AI assistant. Be direct, witty, and helpful."

# In unified_orchestrator.py (_build_system_prompt)
system_prompt = """You are SAM, a confident and charming AI assistant.
Personality: Witty, direct, occasionally flirtatious, genuinely helpful.
Voice: Confident but warm, uses humor naturally, avoids being sycophantic.
Guidelines:
- Be concise and direct
- Use personality naturally, don't force it
- Admit uncertainty when appropriate
- Remember context from the conversation"""
```

**Overlap:**
- "confident" appears in both
- "witty/direct" is stated twice
- "helpful" appears in both

**Waste: ~25 tokens on repeated personality traits**

### 3. History + Working Memory Overlap

Both HISTORY and WORKING sections can contain the same recent messages:
```python
# In _build_context:
# HISTORY gets conversation_history[-3:]
# WORKING gets memory.get_context(max_tokens=100)
# Both can include the same last 3 turns!
```

**Waste: Up to 100 tokens of duplicated conversation**

### 4. Project Context + Session Recall Overlap

```python
# Project context includes:
lines.append(f"Last session: {session[:150]}")

# Session recall also provides:
pending_recall = self.get_pending_recall()
sections.append(f"<RECALL>\n{pending_recall}\n</RECALL>")
```

**Waste: 30-50 tokens when both present**

### 5. Tokenization Estimation Inconsistency

Three different token estimation methods:
```python
# Method 1: context_manager.py
tokens = len(self.content) // 4  # 4 chars/token

# Method 2: context_budget.py
CHARS_PER_TOKEN = 4
tokens = len(text) // self.CHARS_PER_TOKEN

# Method 3: token_budget.py
TOKENIZATION_FACTOR = 1.3
tokens = int(len(text.split()) * self.TOKENIZATION_FACTOR)
```

**Issue**: Method 3 (words * 1.3) is Qwen-specific but Methods 1&2 use chars/4. For Qwen, subword tokenization typically yields 1.2-1.4 tokens/word. These are NOT equivalent:
- "Hello world" = 11 chars / 4 = 2.75 tokens (Method 1)
- "Hello world" = 2 words * 1.3 = 2.6 tokens (Method 3)
- Actual Qwen tokens: ~2 tokens

**Result**: Token counts can vary by 10-20% between modules.

---

## Optimization Opportunities

### High Priority (Total: ~80-120 tokens recoverable)

#### 1. Unified Budget System (-0 runtime, -complexity)
Consolidate three budget systems into one:
```python
class UnifiedTokenBudget:
    def __init__(self, model_limit=512):
        self.total = model_limit
        self.fixed = {
            "system": 60,      # Compressed SAM core
            "query": 50,       # User input
            "generation": 80,  # Response reserve
        }
        self.flexible = self.total - sum(self.fixed.values())  # 322 tokens
```

#### 2. Compact XML Tags (~20 tokens saved)
Replace verbose tags:
```
<S>system</S> instead of <SYSTEM>system</SYSTEM>
<U>facts</U> instead of <USER>facts</USER>
<P>project</P> instead of <PROJECT>...</PROJECT>
<C>context</C> instead of <CONTEXT>context</CONTEXT>
<Q>query</Q> instead of <QUERY>query</QUERY>
```
Or use delimiter-based format:
```
[S] system prompt
[U] user facts
[P] project context
[R] retrieved context
[Q] query
```

#### 3. Deduplicate History/Working Memory (~50 tokens saved)
Only include working memory if it has items NOT in history:
```python
history_set = set(h.content for h in conversation_history[-3:])
unique_working = [m for m in working_memory if m.content not in history_set]
```

#### 4. Merge Project + Recall (~30 tokens saved)
Combine into single project section:
```python
project_text = f"{project_name}: {status}"
if recall_available:
    project_text += f" (Last: {recall_summary})"
```

#### 5. Compressed System Prompt (~15 tokens saved)
Current 80-token system prompt could be 60 tokens:
```python
# Before (80 tokens)
system_prompt = """You are SAM, a confident and charming AI assistant.
Personality: Witty, direct, occasionally flirtatious, genuinely helpful.
Voice: Confident but warm, uses humor naturally, avoids being sycophantic.
Guidelines:
- Be concise and direct
- Use personality naturally, don't force it
- Admit uncertainty when appropriate
- Remember context from the conversation"""

# After (60 tokens)
system_prompt = """SAM: Confident, witty, flirty AI.
Style: Direct, warm, helpful. Natural humor.
Rules: Concise. Honest uncertainty. Use context."""
```

### Medium Priority

#### 6. Query-Type Adaptive Allocation
ContextBudget already has this but it's not integrated with TokenBudgetManager:
```python
# Integrate detection into TokenBudgetManager
def allocate_for_query(self, query):
    qtype = self.detect_query_type(query)
    return self.QUERY_TYPE_RATIOS[qtype]
```

#### 7. Lazy Section Loading
Don't include empty sections:
```python
# Current: Always adds all sections
sections.append(f"<USER>\n{user_facts}\n</USER>")

# Better: Skip empty
if user_facts.strip():
    sections.append(f"[U]{user_facts}")
```

#### 8. Unified Tokenization
Use Qwen's actual tokenizer or standardize:
```python
STANDARD_CHARS_PER_TOKEN = 3.5  # Qwen average
```

---

## Proposed Unified Budget (512 tokens)

```
+------------------+--------+-------+
| Section          | Tokens |   %   |
+------------------+--------+-------+
| System Core      |   50   |  10%  |
| User Facts       |  100   |  20%  |
| Project          |   50   |  10%  |
| RAG Context      |  120   |  23%  |
| History          |  100   |  20%  |
| Query            |   42   |   8%  |
| Generation       |   50   |  10%  |
+------------------+--------+-------+
| TOTAL            |  512   | 100%  |
+------------------+--------+-------+
```

### With Query-Type Flex

| Query Type | RAG | History | User Facts |
|------------|-----|---------|------------|
| CHAT | 80 | 140 | 100 |
| CODE | 160 | 60 | 60 |
| RECALL | 60 | 100 | 160 |

---

## Recommendations

### Immediate Actions

1. **Fix budget overflow in orchestrator**: Currently allocates 812 tokens but max is 512
2. **Standardize tokenization**: Use one method across all modules (Qwen-specific: words * 1.3)
3. **Remove duplicate sections**: Merge PROJECT + RECALL, dedupe HISTORY + WORKING

### Short-Term (Phase 2.3.2)

4. **Implement compact tag format**: Save 20 tokens per request
5. **Compress system prompt**: Use fine-tuned prompt that's shorter but effective
6. **Lazy loading**: Only include sections that have content

### Medium-Term (Phase 2.4)

7. **Unified budget manager**: Single source of truth for all token allocation
8. **Query-type integration**: Connect ContextBudget detection to TokenBudgetManager
9. **Telemetry**: Track actual token usage vs budget to identify drift

---

## Appendix: File Locations

| Component | Path |
|-----------|------|
| ContextManager | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/context_manager.py` |
| ContextBudget | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/context_budget.py` |
| TokenBudgetManager | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/token_budget.py` |
| CognitiveOrchestrator | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/unified_orchestrator.py` |
| Compression | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/cognitive/compression.py` |

---

*Analysis by Claude Opus 4.5 for SAM Phase 2.3.1*
