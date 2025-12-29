#!/usr/bin/env bash
set -euo pipefail
RDIR="${1:-$HOME/ReverseLab/Warp_Open/.vg/receipts/warp_open_batch}"
echo "== Receipts =="
if command -v jq >/dev/null 2>&1; then
  for f in "$RDIR"/*.json; do
    [ -f "$f" ] && printf "%s: %s\n" "$f" "$(jq -r '.status // .Status // "unknown"' "$f" 2>/dev/null || echo unknown)"
  done
fi
echo; echo "== Last 80 lines of batch.out =="
tail -n 80 "$RDIR/batch.out" 2>/dev/null || echo "(no batch.out)"
