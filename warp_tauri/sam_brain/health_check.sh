#!/bin/bash
# SAM Brain Health Check - Run after reboot to verify everything started

echo "=== SAM Brain Health Check ==="
echo ""

# 1. Check launchd daemon
echo "1. Brain Daemon:"
if launchctl list com.sam.brain 2>/dev/null | grep -q "PID"; then
    PID=$(launchctl list com.sam.brain | grep PID | awk '{print $3}')
    echo "   ✓ Running (PID: $PID)"
else
    echo "   ✗ NOT RUNNING"
    echo "   Fix: launchctl load ~/Library/LaunchAgents/com.sam.brain.plist"
fi

# 2. Check Ollama
echo ""
echo "2. Ollama:"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✓ Responding"
    if ollama list 2>/dev/null | grep -q "sam-coder"; then
        echo "   ✓ sam-coder model available"
    else
        echo "   ⚠ sam-coder not found (run: ollama create sam-coder -f Modelfile.sam-coder)"
    fi
else
    echo "   ✗ NOT RESPONDING"
    echo "   Fix: ollama serve"
fi

# 3. Check project inventory
echo ""
echo "3. Project Inventory:"
INVENTORY="$HOME/ReverseLab/SAM/warp_tauri/sam_brain/exhaustive_analysis/master_inventory.json"
if [ -f "$INVENTORY" ]; then
    COUNT=$(python3 -c "import json; print(len(json.load(open('$INVENTORY')).get('projects', {})))" 2>/dev/null)
    echo "   ✓ Loaded ($COUNT projects)"
else
    echo "   ✗ NOT FOUND"
fi

# 4. Check voice
echo ""
echo "4. Voice Output:"
if command -v say &> /dev/null; then
    echo "   ✓ macOS TTS available"
else
    echo "   ✗ 'say' command not found"
fi

# 5. Quick API test
echo ""
echo "5. API Test:"
cd "$HOME/ReverseLab/SAM/warp_tauri/sam_brain"
RESULT=$(python3 -c "from sam_api import api_status; import json; s=api_status(); print('OK' if s.get('success') and s.get('ollama_running') else 'FAIL')" 2>/dev/null)
if [ "$RESULT" = "OK" ]; then
    echo "   ✓ API responding correctly"
else
    echo "   ⚠ API issue (check logs)"
fi

echo ""
echo "=== Summary ==="
echo "If all checks pass, SAM Brain is ready."
echo "Logs: /tmp/sam_brain_daemon.stdout.log"
