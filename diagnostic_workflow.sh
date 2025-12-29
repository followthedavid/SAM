#!/usr/bin/env bash
# === Warp_Open: Diagnostic & Recovery Workflow ===
set -euo pipefail

APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
echo "🔧 Warp_Open Diagnostic & Recovery Workflow"
echo "============================================="

# 1) Relaunch with Enter-heuristic blocks + verbose logs
echo
echo "📋 Step 1: Setting up verbose launch environment"
export ELECTRON_ENABLE_LOGGING=1
export ELECTRON_ENABLE_STACK_DUMPING=1
export WARP_OPEN_ENABLE_BLOCKS=1
export WARP_OPEN_BLOCKS_MODE=enter

echo "✅ Environment variables set:"
echo "   ELECTRON_ENABLE_LOGGING=1"
echo "   ELECTRON_ENABLE_STACK_DUMPING=1" 
echo "   WARP_OPEN_ENABLE_BLOCKS=1"
echo "   WARP_OPEN_BLOCKS_MODE=enter"

echo
echo "🚀 Ready to launch with: cd $APP && ./scripts/dev_enter_blocks.sh"
echo "   In the window: type 'echo hello', 'pwd', 'ls' (press Enter each)"
echo "   Click 💾 Flush, then close the window (Cmd+Q or red X)"

read -p "Press Enter to continue to Step 2 (proof collection)..."

# 2) Prove blocks & inputs were recorded
echo
echo "📊 Step 2: Collecting proof of block recording"
LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl 2>/dev/null | head -1 || echo '')"

if [[ -n "$LOG" && -f "$LOG" ]]; then
    echo "✅ Latest session: $LOG"
    
    echo
    echo "🔍 Block + CWD updates:"
    if grep -nE 'block:(start|exec|end)|cwd:update' "$LOG" 2>/dev/null; then
        echo "✅ Block events found!"
    else
        echo "❌ No block events found"
    fi
    
    echo
    echo "📝 Last 20 inputs (look for '\r' on Enter):"
    if grep -n 'pty:input' "$LOG" 2>/dev/null | tail -20 | sed -n l; then
        echo "✅ Input events found!"
    else
        echo "❌ No input events found"
    fi
else
    echo "❌ No session files found in ~/.warp_open/sessions/"
fi

read -p "Press Enter to continue to Step 3 (diagnostics)..."

# 3) Capture diagnostics if window closed unexpectedly
echo
echo "🏥 Step 3: Diagnostic information capture"

echo
echo "===== Electron console (last run) ====="
echo "Recent Electron log entries:"
if command -v log >/dev/null 2>&1; then
    log show --predicate 'process == "Electron"' --last 5m --info --debug --style syslog 2>/dev/null | tail -200 || echo "No recent Electron logs found"
else
    echo "macOS log command not available"
fi

echo
echo "===== App config snapshot ====="
cd "$APP"
node -e 'const pkg=require("./package.json"); console.log({electron:pkg.devDependencies?.electron, xterm:pkg.dependencies?.xterm, node_pty:pkg.dependencies?.["node-pty"]})'

if [[ -n "$LOG" && -f "$LOG" ]]; then
    echo
    echo "===== Last session head (first 80 lines) ====="
    sed -n '1,80p' "$LOG"
fi

read -p "Press Enter to continue to Step 4 (common fixes)..."

# 4) Fast common fixes
echo
echo "🔧 Step 4: Common fixes"

echo
echo "Option A: Rebuild ABI (if wrong runtime used):"
echo "   cd $APP && npm run rebuild && ./scripts/dev_enter_blocks.sh"

echo
echo "Option B: Kill stuck processes:"
echo "   pkill -f 'Electron.app/Contents/MacOS/Electron' || true"

echo
echo "Option C: Open DevTools for renderer debugging:"
echo "   In Electron window: View → Toggle DevTools, then Cmd+R to reload"

read -p "Press Enter to continue to Step 5 (UI checks)..."

# 5) Quick UI checks
echo
echo "✅ Step 5: UI verification checklist"
echo "When the app is running, verify these features:"
echo "   • Press Cmd+B to toggle the Blocks panel (or click 📋)"
echo "   • Press Cmd+Opt+B to print mini block summary in DevTools"
echo "   • Click 💾 Flush and look for toast + '[session.flush] { ok: true }' in Console"

echo
echo "🎯 What 'good' looks like:"
echo "   • Session log shows block:start, block:exec:end, block:end lines"
echo "   • pty:input lines include \\r when you pressed Enter"
echo "   • DevTools shows '[blocks] total=... running=... done=... failed=...' on Cmd+Opt+B"

echo
echo "🔧 If issues persist:"
echo "   • Run: npm run smoke:once (should exit cleanly)"
echo "   • Check for JavaScript errors in DevTools Console"
echo "   • Look for 'No block events found' but pty:input with \\r exists"

echo
echo "📋 Quick test commands:"
echo "   cd $APP"
echo "   npm run smoke:once  # Should show '[main] Smoke test initiated'"
echo "   ./scripts/dev_enter_blocks.sh  # Launch GUI with block mode"

echo
echo "✅ Diagnostic workflow complete!"
