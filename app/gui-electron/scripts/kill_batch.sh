#!/usr/bin/env bash
PIDFILE="$HOME/ReverseLab/Warp_Open/.vg/receipts/warp_open_batch/batch.pid"
[ -f "$PIDFILE" ] || { echo "No PID file"; exit 0; }
PID=$(cat "$PIDFILE" || true)
[ -n "$PID" ] && kill -9 "$PID" 2>/dev/null || true
echo "Killed batch PID: ${PID:-none}"
