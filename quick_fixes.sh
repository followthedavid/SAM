#!/usr/bin/env bash
# Quick common fixes script
APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"

echo "🔧 Quick fixes for Warp_Open issues"
echo "Select an option:"
echo "1) Rebuild ABI (fixes runtime version mismatches)"
echo "2) Kill stuck Electron processes" 
echo "3) Show diagnostic info"
echo "4) Run smoke test"
echo "5) Exit"

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo "🔄 Rebuilding ABI..."
        cd "$APP" && npm run rebuild
        echo "✅ Rebuild complete. Launch with: ./scripts/dev_enter_blocks.sh"
        ;;
    2)
        echo "🔪 Killing stuck Electron processes..."
        pkill -f "Electron.app/Contents/MacOS/Electron" || echo "No processes found"
        echo "✅ Process cleanup complete"
        ;;
    3)
        echo "📊 App config snapshot:"
        cd "$APP"
        node -e 'const pkg=require("./package.json"); console.log({electron:pkg.devDependencies?.electron, xterm:pkg.dependencies?.xterm, node_pty:pkg.dependencies?.["node-pty"]})'
        
        echo
        echo "📋 Recent Electron logs:"
        if command -v log >/dev/null 2>&1; then
            log show --predicate 'process == "Electron"' --last 5m --info --debug --style syslog 2>/dev/null | tail -20 || echo "No recent logs"
        else
            echo "macOS log command not available"
        fi
        ;;
    4)
        echo "🧪 Running smoke test..."
        cd "$APP" && npm run smoke:once
        echo "✅ Smoke test complete"
        ;;
    5)
        echo "👋 Exiting"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        ;;
esac
