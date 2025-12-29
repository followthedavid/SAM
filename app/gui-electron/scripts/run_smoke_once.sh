#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/ReverseLab/Warp_Open/app/gui-electron"
export WARP_OPEN_ENABLE_SMOKE=1
export WARP_OPEN_SMOKE_TIMEOUT_MS="${WARP_OPEN_SMOKE_TIMEOUT_MS:-90000}"
# Use Electron to boot the main process; it exits on smoke completion/timeout
npx electron . || true
echo "Smoke done. See latest file in ~/.warp_open/sessions/"
ls -t ~/.warp_open/sessions/session-*.jsonl | head -1
