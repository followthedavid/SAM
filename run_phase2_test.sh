#!/bin/bash
# Run Phase 2 End-to-End Test via Rust endpoint

echo "🧪 Running Phase 2 End-to-End Test"
echo "===================================="
echo ""

# Check app running
APP_PID=$(pgrep -f 'Warp_Open' | head -1)
if [ -z "$APP_PID" ]; then
  echo "❌ App not running"
  exit 1
fi

echo "✅ App running (PID: $APP_PID)"
echo ""

# Clean audit log
rm -f ~/PHASE2_AUDIT.log
echo "🧹 Cleaned audit log"
echo ""

echo "⚡ Executing test endpoint..."
echo ""

# Use osascript to call the test endpoint via the app console
osascript <<'EOF'
tell application "System Events"
  tell process "Warp_Open"
    set frontmost to true
  end tell
end tell

delay 0.5

tell application "System Events"
  keystroke "i" using {command down, shift down}
  delay 1.5
  keystroke "await window.__TAURI__.tauri.invoke('test_phase2_workflow')"
  delay 0.3
  key code 36
  delay 5
end tell
EOF

echo "✅ Test command sent!"
echo ""
echo "📊 Checking results..."
sleep 6

# Check audit log
if [ -f ~/PHASE2_AUDIT.log ]; then
  LINES=$(wc -l < ~/PHASE2_AUDIT.log)
  echo ""
  echo "✅ Audit log created with $LINES entries"
  echo ""
  echo "Audit log entries:"
  cat ~/PHASE2_AUDIT.log
  echo ""
else
  echo "⚠️  No audit log found"
fi

echo ""
echo "=================================="
echo "Check the app console (Cmd+Shift+I) for detailed test results!"
echo "=================================="
