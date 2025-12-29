# Data Models

## Block JSONL record (example)
```json
{
  "ts": "2025-10-15T20:30:00.123Z",
  "session": "c7f7…",
  "cwd": "/Users/user/ReverseLab",
  "shell": "zsh",
  "cmdline": "rg -n warp .",
  "exit": 0,
  "duration_ms": 512,
  "stdout": "…",
  "stderr": "",
  "meta": { "env": { "PATH": "…" } }
}
```

## Workflow item (example)
```json
{
  "name": "search docs",
  "command": "./search_docs.sh \"~/Docs\" term",
  "kind": "workflow",
  "base_cwd": "~/repo",
  "tags": ["docs"],
  "source": "mined_workflow.json#42"
}
```
