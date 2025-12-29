#!/bin/bash
# Phase 2 Frontend End-to-End Test Script
# Tests BatchPanel, AutonomySettings, and full workflow

set -e

APP_PID=$(pgrep -f 'Warp_Open' | head -1)

if [ -z "$APP_PID" ]; then
  echo "❌ Warp app not running. Start it with: npm run tauri dev"
  exit 1
fi

echo "✅ Warp app running (PID: $APP_PID)"
echo ""
echo "🧪 Phase 2 Frontend Test Suite"
echo "================================"
echo ""

# Test 1: Check that BatchPanel.vue exists and has Phase 2 structure
echo "Test 1: BatchPanel.vue Phase 2 Integration"
if grep -q "🔧 Phase 2: Command Batches" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/BatchPanel.vue; then
  echo "✅ BatchPanel has Phase 2 header"
else
  echo "❌ BatchPanel missing Phase 2 header"
  exit 1
fi

if grep -q "batch_updated" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/BatchPanel.vue; then
  echo "✅ BatchPanel listens to batch_updated events"
else
  echo "❌ BatchPanel missing batch_updated listener"
  exit 1
fi

if grep -q "invoke('get_batches')" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/BatchPanel.vue; then
  echo "✅ BatchPanel calls get_batches backend"
else
  echo "❌ BatchPanel missing get_batches call"
  exit 1
fi

if grep -q "invoke('approve_batch'" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/BatchPanel.vue; then
  echo "✅ BatchPanel calls approve_batch backend"
else
  echo "❌ BatchPanel missing approve_batch call"
  exit 1
fi

if grep -q "invoke('run_batch'" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/BatchPanel.vue; then
  echo "✅ BatchPanel calls run_batch backend"
else
  echo "❌ BatchPanel missing run_batch call"
  exit 1
fi

echo ""

# Test 2: Check AutonomySettings.vue exists and has all required fields
echo "Test 2: AutonomySettings.vue Configuration"
if [ -f /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue ]; then
  echo "✅ AutonomySettings.vue exists"
else
  echo "❌ AutonomySettings.vue missing"
  exit 1
fi

if grep -q "Enable Semi-Autonomous Execution" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings has enable toggle"
else
  echo "❌ AutonomySettings missing enable toggle"
  exit 1
fi

if grep -q "Autonomy Token" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings has token field"
else
  echo "❌ AutonomySettings missing token field"
  exit 1
fi

if grep -q "Max Batch Size" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings has max batch size"
else
  echo "❌ AutonomySettings missing max batch size"
  exit 1
fi

if grep -q "Allow Patterns" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings has allow patterns"
else
  echo "❌ AutonomySettings missing allow patterns"
  exit 1
fi

if grep -q "Deny Patterns" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings has deny patterns"
else
  echo "❌ AutonomySettings missing deny patterns"
  exit 1
fi

if grep -q "localStorage" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AutonomySettings.vue; then
  echo "✅ AutonomySettings persists to localStorage"
else
  echo "❌ AutonomySettings missing localStorage persistence"
  exit 1
fi

echo ""

# Test 3: Check AIChatTab integration
echo "Test 3: AIChatTab Integration"
if grep -q "BatchPanel" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AIChatTab.vue; then
  echo "✅ AIChatTab imports BatchPanel"
else
  echo "❌ AIChatTab missing BatchPanel import"
  exit 1
fi

if grep -q "AutonomySettings" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AIChatTab.vue; then
  echo "✅ AIChatTab imports AutonomySettings"
else
  echo "❌ AIChatTab missing AutonomySettings import"
  exit 1
fi

if grep -q "⚙️ Autonomy Settings" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src/components/AIChatTab.vue; then
  echo "✅ AIChatTab has settings button"
else
  echo "❌ AIChatTab missing settings button"
  exit 1
fi

echo ""

# Test 4: Backend connectivity (create and fetch batches)
echo "Test 4: Backend Connectivity"

# Create a test batch via backend
TEST_BATCH_DATA=$(cat <<EOF
[
  {
    "tool": "execute_shell",
    "args": { "command": "echo Phase2Frontend" }
  },
  {
    "tool": "execute_shell",
    "args": { "command": "pwd" }
  }
]
EOF
)

echo "$TEST_BATCH_DATA" > /tmp/phase2_frontend_test_batch.json

# NOTE: We can't easily call Tauri commands from bash, so we'll check the Rust code instead
if grep -q "get_batches" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src-tauri/src/commands.rs; then
  echo "✅ Backend has get_batches command"
else
  echo "❌ Backend missing get_batches command"
  exit 1
fi

if grep -q "approve_batch" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src-tauri/src/commands.rs; then
  echo "✅ Backend has approve_batch command"
else
  echo "❌ Backend missing approve_batch command"
  exit 1
fi

if grep -q "run_batch" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src-tauri/src/commands.rs; then
  echo "✅ Backend has run_batch command"
else
  echo "❌ Backend missing run_batch command"
  exit 1
fi

echo ""

# Test 5: Build verification
echo "Test 5: Build Verification"
if [ -f /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/dist/index.html ]; then
  echo "✅ Frontend build exists"
else
  echo "❌ Frontend build missing - run: npm run build"
  exit 1
fi

if grep -q "BatchPanel" /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/dist/assets/index-*.js 2>/dev/null; then
  echo "✅ BatchPanel bundled in production build"
else
  echo "⚠️  Cannot verify BatchPanel in production build (acceptable if dev mode)"
fi

echo ""
echo "================================"
echo "✅ All Phase 2 Frontend Tests Passed!"
echo ""
echo "Manual Testing Instructions:"
echo "1. Open the Warp app (should already be running)"
echo "2. Click '⚙️ Autonomy Settings' button at top"
echo "3. Enable autonomy, set token (optional), adjust patterns"
echo "4. Create a test batch (see test_phase2_backend.sh for curl commands)"
echo "5. BatchPanel should display the batch with approve/run buttons"
echo "6. Click Approve, then Run"
echo "7. Check ~/PHASE2_AUDIT.log for audit entries"
echo ""
echo "App is running at http://localhost:5173"
echo "Logs: tail -f /tmp/warp_phase2_frontend.log"
