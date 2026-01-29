# remember/ - Memory

## What This Does
Stores and retrieves information across conversations. SAM's long-term memory.

## Why It Exists
SAM needs to remember user preferences, past conversations, and project context.
Without memory, every conversation starts from scratch.

## When To Use
- Storing user facts and preferences
- Retrieving relevant past conversations
- Loading project context for coding help
- Semantic search across all memories

## How To Use
```python
from sam.remember import facts
facts.store("user_name", "David")
name = facts.get("user_name")

from sam.remember import embeddings
similar = embeddings.search("How do I fix the auth bug?")
# Returns relevant past conversations and solutions

from sam.remember import projects
context = projects.get_context("sam_brain")
```

## Key Files
- `facts.py` - User facts and preferences (structured)
- `conversations.py` - Chat history with timestamps
- `embeddings.py` - Semantic search via MLX MiniLM (384-dim, 10ms)
- `projects.py` - Project context, file mappings, permissions
- `working.py` - Short-term working memory with decay

## Storage Locations
- Facts DB: `~/.sam/memory/facts.db`
- Embeddings: `/Volumes/David External/sam_memory/`
- Project Index: `/Volumes/David External/sam_memory/code_index.db`

## Dependencies
- **Requires:** External storage for large indexes
- **Required by:** core/ (for context injection)

## What Was Here Before
This consolidates:
- `memory/semantic_memory.py` (743 lines)
- `memory/fact_memory.py` (2,506 lines)
- `memory/conversation_memory.py` (826 lines)
- `memory/project_context.py` (3,287 lines)
- `cognitive/enhanced_memory.py` (729 lines)
