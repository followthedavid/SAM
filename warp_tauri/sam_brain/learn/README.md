# learn/ - Self-Improvement

## What This Does
Makes SAM smarter over time by learning from Claude, feedback, and patterns.

## Why It Exists
SAM is a "self-improving AI" - this is where the improvement happens.
We distill knowledge from Claude sessions into SAM's local model.

## When To Use
- After Claude Code sessions (extract what Claude taught)
- When users correct SAM (learn from mistakes)
- Running training cycles (fine-tune the model)
- Checking what SAM has learned recently

## How To Use
```python
from sam.learn import from_claude
examples = from_claude.extract_session("~/.claude/sessions/...")
# Extracts (prompt, response) pairs for training

from sam.learn import train
train.run_lora_training(examples)
# Fine-tunes SAM's model with new knowledge

from sam.learn import curriculum
next_task = curriculum.get_next()
# What should SAM learn next?
```

## Key Files
- `from_claude.py` - Extract knowledge from Claude Code sessions
- `from_feedback.py` - Learn from user corrections and thumbs up/down
- `from_code.py` - Learn patterns from codebases
- `curriculum.py` - Prioritized learning queue
- `train.py` - LoRA fine-tuning pipeline
- `daemon.py` - Background learning daemon
- `training_data.py` - Dataset management

## Learning Sources
| Source | Trigger | Value |
|--------|---------|-------|
| Claude sessions | Auto-detect | High - expert knowledge |
| User feedback | Thumbs up/down | Medium - preference tuning |
| Code patterns | Indexing | Low - style patterns |
| Errors | Escalation | High - capability gaps |

## Dependencies
- **Requires:** think/ (for inference during training)
- **Required by:** core/ (for continuous improvement)

## What Was Here Before
This consolidates:
- `perpetual_learner.py` (1,685 lines)
- `auto_learner.py` (961 lines)
- `knowledge_distillation.py` (3,739 lines)
- `training_runner.py` + `training_scheduler.py` + `training_stats.py` + etc. (8 files)
- `feedback_system.py` (3,872 lines)
