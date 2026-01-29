# think/ - LLM Inference

## What This Does
Generates text responses using local MLX models. This is where SAM's thoughts become words.

## Why It Exists
SAM runs on an 8GB M2 Mac Mini - we can't just call OpenAI for everything.
MLX lets us run local inference efficiently on Apple Silicon.

## When To Use
- Processing any prompt that needs a text response
- Deciding whether to use the small (1.5B) or large (3B) model
- Escalating complex questions to Claude
- Validating response quality before returning

## How To Use
```python
from sam.think import mlx
response = mlx.generate("Explain quantum computing")

from sam.think import escalate
if escalate.should_escalate(prompt):
    # Too complex for local model
    pass
```

## Key Files
- `mlx.py` - Core MLX inference with KV-cache quantization (75% memory savings)
- `escalate.py` - Decides when to ask Claude instead of answering locally
- `select_model.py` - Picks 1.5B (fast) vs 3B (smart) based on task complexity
- `validate.py` - Checks responses for quality, repetition, coherence
- `budget.py` - Context window management (don't OOM on 8GB)

## Dependencies
- **Requires:** Nothing (leaf node)
- **Required by:** core/ (to generate responses)

## What Was Here Before
This consolidates:
- `cognitive/mlx_cognitive.py` (874 lines)
- `cognitive/mlx_optimized.py` (628 lines)
- `cognitive/model_selector.py` (486 lines)
- `cognitive/quality_validator.py` (627 lines)
- `execution/escalation_handler.py` (428 lines)
