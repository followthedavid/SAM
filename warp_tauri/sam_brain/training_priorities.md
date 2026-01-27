# SAM Training Priorities

## The Core Insight

Large models like Claude weren't made effective by having *more* data - they were made effective by:

1. **High-quality, filtered data** (not just internet scrape)
2. **Diverse domains** (transfer learning between skills)
3. **Explicit reasoning traces** (chain-of-thought)
4. **Human preference alignment** (RLHF/DPO)
5. **Instruction-following format** (task clarity)

## Priority Matrix for 8GB Hardware

### Tier 1: Essential (Collect First)
These directly teach capabilities:

| Data Type | Source | Why It Works |
|-----------|--------|--------------|
| **Code + Diffs** | GitHub PRs | Teaches iterative improvement (perpetual ladder core) |
| **Instruction Data** | FLAN, Alpaca, Open Assistant | Teaches task following |
| **Chain-of-Thought** | Synthetic from Claude | Teaches reasoning steps |
| **Creative Writing** | Nifty, AO3 | Teaches narrative, character, voice |

### Tier 2: High Value (Collect Second)
| Data Type | Source | Why It Works |
|-----------|--------|--------------|
| **Preference Pairs** | Distilled from Claude | Teaches quality discernment |
| **Stack Overflow Q&A** | API scrape | Problem → solution patterns |
| **Documentation** | ReadTheDocs, MDN | Technical clarity |

### Tier 3: Domain Knowledge (Use RAG Instead)
Don't train on this - retrieve at runtime:

| Data Type | Better Approach |
|-----------|-----------------|
| Wikipedia | RAG retrieval |
| Current events | Web search |
| Specific APIs | RAG + docs |

## Actionable Data Sources

### 1. Instruction-Following Data (FREE, HIGH IMPACT)
```bash
# Download these public datasets:

# FLAN Collection (Google's instruction tuning)
huggingface-cli download bigscience/P3

# Alpaca-style instructions
huggingface-cli download tatsu-lab/alpaca

# Open Assistant conversations
huggingface-cli download OpenAssistant/oasst1

# Dolly instructions
huggingface-cli download databricks/databricks-dolly-15k
```

### 2. Chain-of-Thought Data (SYNTHESIZE)
Generate using Claude:
- Math word problems with step-by-step solutions
- Logic puzzles with explicit reasoning
- Code problems with design rationale

### 3. Preference Pairs (SYNTHESIZE)
Generate using Claude:
- Same prompt → good response vs mediocre response
- Used for DPO (Direct Preference Optimization) training

### 4. Code Data (COLLECTING)
- GitHub PRs with diffs (before → after)
- Stack Overflow accepted answers
- High-star repo functions

### 5. Creative/Roleplay (COLLECTING)
- Nifty stories (character voice, narrative)
- AO3 works (plot structure, dialogue)

## Training Strategy

### Phase 1: Base Capability (LoRA on instruction data)
```
Base: Llama-3-8B or similar
+ FLAN/Alpaca instruction data (100K examples)
+ Our code diffs (10K examples)
Result: Follows instructions, understands code
```

### Phase 2: Personality (LoRA on creative data)
```
Previous model
+ Nifty/AO3 creative writing (50K examples)
+ SAM personality examples (1K curated)
Result: Has voice, can roleplay
```

### Phase 3: Reasoning (LoRA on CoT data)
```
Previous model
+ Chain-of-thought examples (10K synthetic)
+ Math/logic problems with solutions
Result: Can reason step-by-step
```

### Phase 4: Alignment (DPO on preference pairs)
```
Previous model
+ Preference pairs (5K from distillation)
Result: Prefers better responses
```

## Key Numbers

From research on what actually matters:

- **Instruction data**: 10K-100K examples is enough
- **Chain-of-thought**: Even 1K good examples helps significantly
- **Preference pairs**: 5K-10K pairs for DPO
- **Domain data**: Quality matters more than quantity

## What NOT to Do

1. ❌ Don't train on raw internet scrapes (noise)
2. ❌ Don't try to memorize facts (use RAG)
3. ❌ Don't train on too many domains at once (catastrophic forgetting)
4. ❌ Don't skip instruction formatting (model needs task clarity)

## The Secret Sauce

The real insight from Claude's training:

1. **Self-improvement loops**: Model critiques and improves its own outputs
2. **Constitutional training**: Model learns to prefer helpful, harmless responses
3. **Multi-turn refinement**: Not just single responses, but conversations

We replicate this with:
- Perpetual ladder (self-improvement on code)
- Escalation learning (learns from Claude corrections)
- Knowledge distillation (captures reasoning patterns)

## Estimated Training Requirements

For an 8GB M2 Mac Mini using LoRA:

| Phase | Data Size | Training Time | VRAM |
|-------|-----------|---------------|------|
| Instruction | 50K examples | 4-6 hours | 6GB |
| Creative | 30K examples | 3-4 hours | 6GB |
| CoT | 10K examples | 1-2 hours | 6GB |
| DPO | 5K pairs | 2-3 hours | 7GB |

Total: ~12-15 hours of training for a capable model.
