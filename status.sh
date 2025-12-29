#!/usr/bin/env bash
# Quick status check for Warp_Open
echo "🔧 Warp_Open Status Check"
echo "========================="

APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"

echo
echo "📁 Demo helpers installed:"
[[ -f "./warp_open_demo_helpers.sh" ]] && echo "✅ warp_open_demo_helpers.sh" || echo "❌ warp_open_demo_helpers.sh"
[[ -f "$APP/scripts/dev_enter_blocks.sh" ]] && echo "✅ dev_enter_blocks.sh" || echo "❌ dev_enter_blocks.sh"

echo
echo "🚀 Quick tools available:"
[[ -f "./quick_launch.sh" ]] && echo "✅ quick_launch.sh" || echo "❌ quick_launch.sh"
[[ -f "./quick_proof.sh" ]] && echo "✅ quick_proof.sh" || echo "❌ quick_proof.sh"
[[ -f "./quick_fixes.sh" ]] && echo "✅ quick_fixes.sh" || echo "❌ quick_fixes.sh"
[[ -f "./diagnostic_workflow.sh" ]] && echo "✅ diagnostic_workflow.sh" || echo "❌ diagnostic_workflow.sh"

echo
echo "🔍 App modifications:"
[[ -f "$APP/src/preload.js.bak" ]] && echo "✅ preload.js patched (backup exists)" || echo "❌ preload.js not patched"
[[ -f "$APP/src/main.js.bak" ]] && echo "✅ main.js patched (backup exists)" || echo "❌ main.js not patched"
[[ -f "$APP/src/index.html.bak" ]] && echo "✅ index.html patched (backup exists)" || echo "❌ index.html not patched"
[[ -f "$APP/src/renderer.js.bak" ]] && echo "✅ renderer.js patched (backup exists)" || echo "❌ renderer.js not patched"

echo
echo "📊 Latest session:"
LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl 2>/dev/null | head -1 || echo '')"
if [[ -n "$LOG" && -f "$LOG" ]]; then
    echo "✅ $LOG"
    BLOCKS=$(grep -c 'block:' "$LOG" 2>/dev/null || echo "0")
    INPUTS=$(grep -c 'pty:input' "$LOG" 2>/dev/null || echo "0")
    echo "   📋 Block events: $BLOCKS"
    echo "   ⌨️  Input events: $INPUTS"
else
    echo "❌ No session files found"
fi

echo
echo "🧪 Quick health check:"
cd "$APP"
if npm run smoke:once >/dev/null 2>&1; then
    echo "✅ Smoke test passes"
else
    echo "❌ Smoke test failed"
fi

echo
echo "🎯 Ready to use:"
echo "   ./quick_launch.sh     - Launch with debugging"
echo "   ./quick_proof.sh      - Check session recordings"
echo "   ./quick_fixes.sh      - Common fixes menu"
echo "   ./diagnostic_workflow.sh - Full diagnostic process"
