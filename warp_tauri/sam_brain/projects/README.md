# projects/ - Project Awareness

## What This Does
Understands your codebase structure, permissions, and context.

## Why It Exists
SAM helps with 20+ different projects. Each has different tech stacks,
conventions, and what SAM is allowed to do. This keeps track of all that.

## When To Use
- Getting context for a coding question
- Searching for code entities (functions, classes)
- Checking what SAM can do in a given project
- Adding a new project to SAM's knowledge

## How To Use
```python
from sam.projects import registry
project = registry.get("sam_brain")
# {'path': '~/ReverseLab/SAM/...', 'tech': ['python', 'mlx'], ...}

from sam.projects import search_code
results = search_code.find("class VoicePipeline")
# Returns file locations and definitions

from sam.projects import permissions
can_commit = permissions.check("sam_brain", "git_commit")
```

## Key Files
- `registry.py` - All 20+ projects with metadata
- `search_code.py` - Find functions, classes, variables
- `search_docs.py` - Find documentation
- `permissions.py` - What SAM can do in each project

## Registered Projects
| Project | Path | Tech |
|---------|------|------|
| sam_brain | ~/ReverseLab/SAM/warp_tauri/sam_brain | Python, MLX |
| warp_tauri | ~/ReverseLab/SAM/warp_tauri | Rust, Tauri |
| PixelForge | ~/ReverseLab/Godot/PixelForge | GDScript |
| ... | 17 more projects | ... |

## Dependencies
- **Requires:** External code indexes
- **Required by:** core/ (for coding context)

## What Was Here Before
This consolidates:
- `unified_orchestrator.py` (1,016 lines) - project parts
- `code_indexer.py` (2,074 lines root + 676 lines cognitive/)
- `cognitive/doc_indexer.py` (452 lines)
