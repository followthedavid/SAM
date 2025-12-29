#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Testing xterm preload regression..."

# Create temp log file
LOG_FILE=".tmp/preload-test.log"
mkdir -p .tmp

# Run headless test with logging
ELECTRON_ENABLE_LOGGING=1 ELECTRON_DISABLE_SECURITY_WARNINGS=1 \
  WARP_OPEN_ENABLE_SMOKE=1 npx electron . > "$LOG_FILE" 2>&1 &

# Give it time to initialize
sleep 3

# Check for success indicators
if grep -q "\[preload] xterm require OK" "$LOG_FILE"; then
  echo "✅ xterm preload: PASS"
  SUCCESS=1
else
  echo "❌ xterm preload: FAIL"
  echo "--- Debug info ---"
  grep -E "\[preload\]" "$LOG_FILE" || echo "No preload logs found"
  SUCCESS=0
fi

# Check sandbox status
if grep -q "\[preload] typeof require = function" "$LOG_FILE"; then
  echo "✅ preload require access: PASS"
else
  echo "❌ preload require access: FAIL (sandbox might be ON)"
fi

# Clean up background processes
pkill -f "npx electron" 2>/dev/null || true

if [ "$SUCCESS" = "1" ]; then
  echo "🎉 Preload regression test: ALL CLEAR"
  exit 0
else
  echo "💥 Preload regression test: FAILED"
  exit 1
fi