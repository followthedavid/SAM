# Behavioral Spec (v0)

## Terminal substrate
- PTY lifecycle (spawn, resize, termination), login shell semantics, env merge.
- ANSI/OSC handling: 24-bit color, OSC 8 hyperlinks, bracketed paste, alt-screen.

## Blocks (concept)
- Boundary: command invocation → exit. Capture stdout/stderr, exit code, timestamps, cwd, env snapshot.
- Actions: copy | rerun | export | annotate.
- Storage: append-only JSONL per session (see data_model.md).

## History & transcripts
- Human-readable transcript + machine JSONL stream; replay should reconstruct session deterministically.

## Palette / Workflows / Snippets
- Fuzzy finder sourcing from ~/.warp_open/workflows.json (imported from mined files).
- Each item: name, command, base_cwd policy, tags, source.

## Settings & project overrides
- Global ~/.warp_open/config.* plus optional project-local ./.warp_open/ overrides.

## AI integrations (optional)
- Local via adapters (e.g., Ollama). Explicit-send only; pass selected block text + cwd file list.
