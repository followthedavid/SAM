#!/bin/bash
# Verify that test pages are accessible and working

set -e

echo "🔍 Verifying Phase 2 Test Pages"
echo "================================"
echo ""

# Check if app is running
APP_PID=$(pgrep -f 'Warp_Open' | head -1)
if [ -z "$APP_PID" ]; then
  echo "❌ App not running"
  exit 1
fi

echo "✅ App running (PID: $APP_PID)"
echo ""

# Check if the test page file exists
if [ ! -f /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/public/test_phase2_interactive.html ]; then
  echo "❌ Test page not found in public directory"
  exit 1
fi

echo "✅ Test page exists in public directory"
echo ""

# Check if vite is serving
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
  echo "❌ Vite dev server not responding on localhost:5173"
  exit 1
fi

echo "✅ Vite dev server responding"
echo ""

# Check if the test page is accessible
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/test_phase2_interactive.html)
if [ "$HTTP_STATUS" != "200" ]; then
  echo "❌ Test page returned HTTP $HTTP_STATUS"
  exit 1
fi

echo "✅ Test page accessible (HTTP 200)"
echo ""

# Check if Tauri window is open
WINDOW_COUNT=$(osascript -e 'tell application "System Events" to count (every window of every process whose name is "Warp_Open")' 2>/dev/null || echo "0")

if [ "$WINDOW_COUNT" -eq "0" ]; then
  echo "⚠️  Warning: No Warp_Open window detected"
  echo "   The test page must be opened IN the Tauri app window, not a regular browser"
else
  echo "✅ Warp_Open window is open"
fi

echo ""
echo "================================"
echo "📋 Access Instructions"
echo "================================"
echo ""
echo "The test page CANNOT be opened in a regular browser."
echo "It must be opened IN the Tauri app window."
echo ""
echo "How to access it:"
echo ""
echo "Method 1: Via App Dev Console"
echo "------------------------------"
echo "1. Focus the Warp_Open app window"
echo "2. Open DevTools (Cmd+Shift+I or View → Toggle DevTools)"
echo "3. In the Console tab, run:"
echo ""
echo "   window.location.href = '/test_phase2_interactive.html'"
echo ""
echo "Method 2: Add Navigation Button (Permanent)"
echo "--------------------------------------------"
echo "We can add a button to the main app UI that navigates to the test page."
echo "This would make it accessible with a single click."
echo ""
echo "Method 3: Use Main App Console Instead"
echo "---------------------------------------"
echo "You can test directly in the main app's console without a separate page:"
echo ""
echo "1. Open the app"
echo "2. Press Cmd+Shift+I to open DevTools"
echo "3. In Console, paste the test commands from test_phase2_comprehensive.sh"
echo ""
echo "================================"
echo ""
echo "Would you like me to:"
echo "A) Add a 'Test Mode' button to the main app UI"
echo "B) Create console-only test commands (no separate page needed)"
echo "C) Both"
echo ""
