#!/usr/bin/env bash
# Quick proof collection script
echo "📊 Proving blocks & inputs were recorded"

LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl 2>/dev/null | head -1 || echo '')"
echo "Latest session: $LOG"

if [[ -n "$LOG" && -f "$LOG" ]]; then
    echo
    echo "🔍 Blocks + CWD updates:"
    grep -nE 'block:(start|exec|end)|cwd:update' "$LOG" || echo "No block events found"
    
    echo
    echo "📝 Last 20 inputs (look for '\r' on Enter):"
    grep -n 'pty:input' "$LOG" | tail -20 | sed -n l
else
    echo "❌ No session files found in ~/.warp_open/sessions/"
fi
