#!/usr/bin/env bash
set -Eeuo pipefail

# Monitor receipts for Warp_Open batch (one-shot or loop)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RDIR="$ROOT/.vg/receipts/warp_open_batch"
INTERVAL="2"
ONCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --once) ONCE=1; shift ;;
    -n|--interval) INTERVAL="${2:-2}"; shift 2 ;;
    *) shift ;;
  esac
done

print_report() {
  echo "Warp_Open batch status — $(date)"
  local total=0 ok=0 err=0
  for f in "$RDIR"/*.json; do
    [[ -e "$f" ]] || continue
    local s; s=$(grep -o '"status":"[^"]*"' "$f" | cut -d '"' -f4)
    local id; id=$(basename "$f" .json)
    printf "%-28s %s\n" "$id" "$s"
    total=$((total+1)); [[ "$s" == success ]] && ok=$((ok+1)) || [[ "$s" == error ]] && err=$((err+1))
  done
  echo "\nTotal: $total  Success: $ok  Error: $err"
}

if [[ $ONCE -eq 1 ]]; then
  print_report
  exit 0
fi

while true; do
  clear || true
  print_report
  sleep "$INTERVAL"
done
