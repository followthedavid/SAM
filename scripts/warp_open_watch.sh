#!/usr/bin/env bash
set -Eeuo pipefail
# Simple watcher: polls receipts for new step receipts and shows macOS notifications.
# Usage: ~/ReverseLab/Warp_Open/scripts/warp_open_watch.sh [interval_seconds]

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RDIR="$ROOT/.vg/receipts/warp_open_batch"
INT="${1:-3}"

notify() {
  local title="$1"; shift; local msg="$*"
  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier -group warp_open_batch -title "$title" -message "$msg" >/dev/null 2>&1 || true
  else
    osascript -e 'display notification '"'""$msg"'"' with title '"'""$title"'"'' >/dev/null 2>&1 || true
  fi
}

prev_count=0
while true; do
  mapfile -t files < <(ls -1t "$RDIR"/*.json 2>/dev/null || true)
  count=${#files[@]}
  if (( count > prev_count )); then
    # show the latest
    f="${files[0]}"
    step=$(basename "$f" .json)
    status=$(grep -o '"status":"[^"]*"' "$f" | cut -d '"' -f4)
    notify "Warp_Open" "${status^^} — ${step}"
    prev_count=$count
  fi
  sleep "$INT"
done
