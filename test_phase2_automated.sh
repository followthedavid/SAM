#!/bin/bash
# Automated Phase 2 Test - Uses Tauri IPC to test directly

set -e

echo "🧪 Automated Phase 2 Test"
echo "=========================="
echo ""

# Check if app is running
APP_PID=$(pgrep -f 'Warp_Open' | head -1)
if [ -z "$APP_PID" ]; then
  echo "❌ App not running"
  exit 1
fi

echo "✅ App running (PID: $APP_PID)"
echo ""

# Use osascript to send JavaScript to the app via AppleScript
echo "Running automated test via AppleScript..."
echo ""

osascript <<EOF
tell application "System Events"
  tell process "Warp_Open"
    set frontmost to true
  end tell
end tell

tell application "System Events"
  keystroke "i" using {command down, shift down}
  delay 1
  
  set testScript to "(async () => {
  const { invoke } = window.__TAURI__.tauri;
  const wait = (ms) => new Promise(r => setTimeout(r, ms));
  
  console.log('🧪 Automated Phase 2 Test');
  
  try {
    // Test 1: Get initial batches
    console.log('1. Getting initial batches...');
    const initial = await invoke('get_batches');
    console.log('✅ Initial batches:', initial.length);
    
    // Test 2: Create batch
    console.log('2. Creating batch...');
    const batchId = await invoke('create_batch', {
      tabId: 1,
      entries: [
        {tool: 'execute_shell', args: {command: 'echo Phase2'}},
        {tool: 'execute_shell', args: {command: 'pwd'}},
        {tool: 'execute_shell', args: {command: 'whoami'}}
      ]
    });
    console.log('✅ Created:', batchId.substring(0, 8));
    
    await wait(500);
    
    // Test 3: Approve
    console.log('3. Approving batch...');
    await invoke('approve_batch', {batchId, autonomyToken: null});
    console.log('✅ Approved');
    
    await wait(500);
    
    // Test 4: Run
    console.log('4. Running batch...');
    await invoke('run_batch', {batchId, autonomyToken: null});
    console.log('✅ Running');
    
    await wait(2000);
    
    // Test 5: Check results
    console.log('5. Checking results...');
    const batches = await invoke('get_batches');
    const result = batches.find(b => b.id === batchId);
    console.log('Status:', result.status);
    console.log('Entries:', result.entries.length);
    console.log('✅ Test Complete!');
    
    return batchId;
  } catch (e) {
    console.error('❌ Test failed:', e);
  }
})();"
  
  keystroke testScript
  keystroke return
end tell
EOF

echo ""
echo "✅ Test script sent to app"
echo ""
echo "Check the app's console (Cmd+Shift+I) to see results"
echo "Or check the audit log: tail ~/PHASE2_AUDIT.log"
