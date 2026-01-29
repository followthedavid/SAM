# core/ - The Brain

## What This Does
Routes all requests to the right subsystem. This is SAM's central nervous system.

## Why It Exists
SAM needs ONE place that understands all capabilities and decides how to respond to any request.
Without this, you'd have 7 different "orchestrators" (we did - it was confusing).

## When To Use
- When you need to process any user request
- When adding a new capability to SAM
- When understanding how SAM makes decisions

## How To Use
```python
from sam.core import brain
response = brain.process("What time is it?")
```

## Key Files
- `brain.py` - Central router: receives request, decides handler, returns response
- `config.py` - All configuration in one place (no hunting through 20 files)
- `identity.py` - SAM's personality traits, tone, and self-image
- `emotion.py` - Current emotional state that affects responses

## Dependencies
- **Requires:** think/ (for responses), remember/ (for context)
- **Required by:** serve/ (exposes via API), sam.py (entry point)

## What Was Here Before
This consolidates:
- `orchestrator.py` (1,469 lines) - main routing
- `cognitive/unified_orchestrator.py` (1,817 lines) - RAG integration
- Parts of `sam_api.py` - request handling logic
