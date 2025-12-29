#!/usr/bin/env bash
set -euo pipefail
LOG="${1:-$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl | head -1)}"
echo "Log: $LOG"
grep -E '"type":"(interactive:(start|done)|pty:(start|exit)|block:(start|exec:end))"' "$LOG" | sed -n '1,200p' || true