# SAM Routing Rules - Credit Optimization Guide

## Core Principle
**Route locally first. Escalate to Claude only when necessary.**

The goal: Handle 70-80% of interactions locally to save Claude credits while maintaining quality.

---

## Routing Decision Matrix

### ALWAYS LOCAL (Free - No Claude Credits)

| Category | Examples | Handler |
|----------|----------|---------|
| **Greetings** | "hi", "hello", "hey sam" | sam-brain |
| **Status Queries** | "what projects?", "build status?", "what's running?" | Direct DB/file read |
| **Memory Retrieval** | "what did we discuss?", "show me that code from earlier" | Semantic memory search |
| **File Operations** | "read file X", "list directory", "show config" | Filesystem API |
| **Simple Math** | "what's 15% of 200?", "convert 5km to miles" | Local calculation |
| **Time/Date** | "what time is it?", "what day?", "how long since X?" | System time |
| **Definitions** | "what does X mean?" (if in local knowledge) | Local dictionary |
| **Acknowledgments** | "thanks", "got it", "ok" | Canned response |
| **Yes/No Questions** | About local state only | Boolean check |
| **Formatting** | "make this a list", "format as JSON" | Template/regex |
| **Repetition** | "say that again", "repeat" | Replay last response |

### LOCAL WITH FALLBACK (Try Local First)

| Category | Try First | Fallback to Claude When |
|----------|-----------|------------------------|
| **Code Explanation** | Cached explanations | Novel/complex code |
| **Error Messages** | Known error patterns | Unknown errors |
| **How-To Questions** | Stored solutions | No match found |
| **Summarization** | Template summaries | Complex content |
| **Translation** | Simple phrases | Nuanced text |
| **Recommendations** | Previous suggestions | New context needed |

### ALWAYS CLAUDE (Credits Required)

| Category | Why Claude? |
|----------|-------------|
| **Novel Reasoning** | Requires multi-step logic not seen before |
| **Code Generation** | New code that doesn't match templates |
| **Creative Writing** | Original content creation |
| **Complex Analysis** | Multiple factors to weigh |
| **Debugging** | Non-obvious bug investigation |
| **Architecture Decisions** | Trade-off analysis |
| **Ambiguous Requests** | Needs clarification/interpretation |
| **Safety-Critical** | Medical, legal, financial advice |

---

## Routing Algorithm

```python
def route_request(message: str) -> str:
    # Step 1: Check for exact matches (instant, free)
    if is_greeting(message):
        return "LOCAL_GREETING"

    if is_acknowledgment(message):
        return "LOCAL_ACK"

    # Step 2: Check for status/state queries (free)
    if asks_about_status(message):
        return "LOCAL_STATUS"

    if asks_about_files(message):
        return "LOCAL_FILE"

    # Step 3: Check semantic memory (might be free)
    memory_match = search_memory(message)
    if memory_match and memory_match.confidence > 0.85:
        return "LOCAL_MEMORY"

    # Step 4: Check for cached solutions
    cached = get_cached_solution(message)
    if cached and cached.age_days < 30:
        return "LOCAL_CACHED"

    # Step 5: Classify complexity
    complexity = estimate_complexity(message)

    if complexity == "simple":
        return "LOCAL_SIMPLE"  # Try local LLM

    if complexity == "medium":
        return "LOCAL_WITH_FALLBACK"  # Try local, escalate if bad

    # Step 6: Complex tasks go to Claude
    return "CLAUDE"
```

---

## Complexity Estimation Rules

### SIMPLE (Handle Locally)
- Single concept/entity
- Yes/no answerable
- Lookup-based
- Pattern matches known template
- Less than 20 words in query
- No "why", "how would you", "compare"

### MEDIUM (Try Local First)
- Two concepts to relate
- Requires some reasoning
- Has partial match in memory
- 20-50 words in query
- Contains "explain" or "describe"

### COMPLEX (Use Claude)
- Multiple interacting concepts
- Requires multi-step reasoning
- Novel combination of ideas
- Contains "design", "architect", "optimize"
- Asks for trade-off analysis
- No memory matches
- Over 50 words with nuance

---

## Credit-Saving Strategies

### 1. Context Compression
Before sending to Claude:
```python
def compress_context(full_context: str) -> str:
    # Remove redundant info
    # Keep only last 3 relevant exchanges
    # Summarize older context
    # Strip formatting/whitespace
    return compressed
```
**Savings:** 40-60% token reduction

### 2. Response Caching
```python
def cache_response(query: str, response: str):
    # Store with semantic embedding
    # Tag with topic/category
    # Set expiration (30 days default)
    memory.store(query, response)
```
**Savings:** 100% on repeated questions

### 3. Batch Queries
```python
def batch_if_possible(queries: list) -> str:
    # Combine related queries
    # "Answer these 5 questions:"
    # Parse responses back
```
**Savings:** 30-50% vs individual calls

### 4. Template Responses
```python
TEMPLATES = {
    "file_created": "Created {filename} with {lines} lines.",
    "build_status": "Build {status}. {details}",
    "project_summary": "{name}: {progress}% complete. Next: {next_task}"
}
```
**Savings:** 100% (no LLM needed)

### 5. Progressive Disclosure
```python
def answer_progressively(query):
    # First: Give short answer
    # Then: "Want more details?"
    # Only expand if user asks
```
**Savings:** 50-70% on verbose responses

---

## Special Cases

### Code Requests
```
User: "Write a function to sort a list"
→ Check code templates first
→ Check previous similar implementations
→ Only if novel: Claude

User: "Fix this error: [error message]"
→ Check error database
→ Pattern match known solutions
→ Only if unknown: Claude
```

### Roleplay/Creative
```
User: "Pretend you're a pirate"
→ Local sam-roleplay model (no Claude needed)
→ Personality templates work fine locally
```

### Image Generation
```
User: "Generate an image of..."
→ Route to ComfyUI (local)
→ No Claude credits needed
```

### Project/Task Management
```
User: "What should I work on next?"
→ Query evolution_tracker DB
→ Run priority algorithm locally
→ No Claude needed
```

---

## Metrics to Track

| Metric | Target | Purpose |
|--------|--------|---------|
| Local resolution rate | >70% | Credit savings |
| Fallback rate | <15% | Local model quality |
| Claude calls/day | <20 | Budget control |
| Avg tokens/Claude call | <2000 | Efficiency |
| Cache hit rate | >40% | Memory effectiveness |
| User satisfaction | >90% | Quality check |

---

## Implementation Checklist

- [ ] Greeting/acknowledgment patterns
- [ ] Status query handlers
- [ ] Memory search integration
- [ ] Response caching system
- [ ] Complexity classifier
- [ ] Context compressor
- [ ] Batch query support
- [ ] Template library
- [ ] Metrics dashboard
- [ ] Fallback detection

---

## Example Routing Flows

### Flow 1: Simple Query
```
User: "What projects am I tracking?"
→ Pattern: status query
→ Route: LOCAL_STATUS
→ Action: Query evolution_tracker.db
→ Response: "You're tracking 17 projects..."
→ Credits used: 0
```

### Flow 2: Memory Retrieval
```
User: "What did we decide about the auth system?"
→ Pattern: memory query
→ Route: Search semantic memory
→ Match found: 0.92 confidence
→ Response: [cached response]
→ Credits used: 0
```

### Flow 3: Complex Escalation
```
User: "Design a caching system for SAM"
→ Pattern: "design" keyword
→ Complexity: HIGH
→ Route: CLAUDE
→ Action: Compress context, send to Claude
→ Response: [Claude's design]
→ Cache response for future
→ Credits used: ~1500 tokens
```

---

**Last Updated:** 2026-01-12
**Version:** 1.0
