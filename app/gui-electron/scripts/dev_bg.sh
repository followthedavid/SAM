#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/ReverseLab/Warp_Open/app/gui-electron"
unset WARP_OPEN_ENABLE_SMOKE
nohup npm run dev >/dev/null 2>&1 &
echo "Electron dev started in background (PID $!)."
