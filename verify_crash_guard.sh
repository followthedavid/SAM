#!/usr/bin/env bash
echo "🛡️  Verifying Crash Guard + Autosave System"
echo "========================================="

APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
cd "$APP"

echo
echo "📋 Features installed:"
grep -q "CRASH_GUARD_START" src/preload.js && echo "✅ Preload crash guard" || echo "❌ Preload missing"
grep -q "CRASH_GUARD_START" src/main.js && echo "✅ Main process crash guard" || echo "❌ Main process missing"  
grep -q "CRASH_GUARD_START" src/renderer.js && echo "✅ Renderer crash guard + toast" || echo "❌ Renderer missing"
grep -q "toast-crash" src/styles.css && echo "✅ Toast styling" || echo "❌ Toast styling missing"

echo
echo "🔑 New features:"
echo "   • Cmd+Opt+X (Mac) / Ctrl+Alt+X - Simulate crash for testing"
echo "   • Red toast with 💾 Flush, ↻ Reload, ✖︎ buttons"
echo "   • Automatic session flush on errors"
echo "   • window.appctl.softReload() for recovery"

echo
echo "🧪 Test it:"
echo "   1. npm run dev"
echo "   2. Press Cmd+Opt+X to simulate crash"  
echo "   3. Should see red crash toast with buttons"
echo "   4. Click 💾 Flush, then ↻ Reload"
echo "   5. Check session log for crash markers"

echo
echo "📊 Proof command after testing:"
echo '   LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl | head -1)"'
echo '   grep -nE "app:crash|session:flush" "$LOG"'
