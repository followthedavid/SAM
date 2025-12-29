# Warp_Open (Clean-Room)

This repository hosts the open, clean-room replacement plan and implementation for a Warp-like terminal UX.

- See `docs/spec/*` for behavior, policy, and data models.
- Use `tools/sync_workflows.sh` to merge mined workflows/snippets into `~/.warp_open/workflows.json`.
- Sessions will be logged as JSONL under `~/.warp_open/sessions/` (planned).
- The Electron app lives in `app/gui-electron/`.

## Quickstart

```bash
# Import workflows from Warp_Archive/Extract
~/ReverseLab/Warp_Open/tools/sync_workflows.sh

# Launch the Electron app (from its folder)
cd ~/ReverseLab/Warp_Open/app/gui-electron && npm install && npm run dev
```
