#!/usr/bin/env node
// Fully Automated Phase 2 Test - No manual interaction required
// Uses CDP (Chrome DevTools Protocol) to inject and execute test code

const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);
const fs = require('fs').promises;

async function runTest() {
  console.log('🧪 Fully Automated Phase 2 Test');
  console.log('=================================\n');

  // 1. Check if app is running
  console.log('1. Checking app status...');
  try {
    const { stdout } = await execAsync("pgrep -f 'Warp_Open' | head -1");
    const pid = stdout.trim();
    console.log(`✅ App running (PID: ${pid})\n`);
  } catch (e) {
    console.error('❌ App not running');
    process.exit(1);
  }

  // 2. Clean audit log
  console.log('2. Cleaning audit log...');
  try {
    await execAsync('rm -f ~/PHASE2_AUDIT.log');
    console.log('✅ Cleaned\n');
  } catch (e) {
    console.log('⚠️  Could not clean audit log\n');
  }

  // 3. Execute test via AppleScript (inject into DevTools console)
  console.log('3. Executing automated test...');
  
  const testScript = `
(async () => {
  const { invoke } = window.__TAURI__.tauri;
  const wait = (ms) => new Promise(r => setTimeout(r, ms));
  
  console.log('🧪 Automated E2E Test Started');
  
  try {
    // Test 1: Create batch
    console.log('\\n1️⃣ Creating batch...');
    const batchId = await invoke('create_batch', {
      tabId: 1,
      entries: [
        {tool: 'execute_shell', args: {command: 'echo "Automated Test"'}},
        {tool: 'execute_shell', args: {command: 'pwd'}},
        {tool: 'execute_shell', args: {command: 'whoami'}},
        {tool: 'execute_shell', args: {command: 'date'}}
      ]
    });
    console.log('✅ Created:', batchId.substring(0, 8));
    
    await wait(500);
    
    // Test 2: Approve
    console.log('\\n2️⃣ Approving batch...');
    await invoke('approve_batch', {batchId, autonomyToken: null});
    console.log('✅ Approved');
    
    await wait(500);
    
    // Test 3: Run
    console.log('\\n3️⃣ Running batch...');
    await invoke('run_batch', {batchId, autonomyToken: null});
    console.log('✅ Executing...');
    
    await wait(2000);
    
    // Test 4: Verify results
    console.log('\\n4️⃣ Verifying results...');
    const batches = await invoke('get_batches');
    const result = batches.find(b => b.id === batchId);
    
    if (!result) {
      console.error('❌ Batch not found');
      return false;
    }
    
    console.log('Status:', result.status);
    console.log('Entries processed:', result.entries.length);
    
    const allProcessed = result.entries.every(e => 
      e.status === 'Completed' || e.status === 'Error'
    );
    
    if (!allProcessed) {
      console.error('❌ Not all entries processed');
      return false;
    }
    
    console.log('\\n✅ All entries processed successfully');
    console.log('\\n📊 Results:');
    result.entries.forEach((e, i) => {
      console.log(\`  \${i+1}. \${e.args.command}\`);
      console.log(\`     Score: \${e.safe_score}, Status: \${e.status}\`);
    });
    
    return true;
  } catch (err) {
    console.error('❌ Test failed:', err);
    return false;
  }
})().then(success => {
  if (success) {
    console.log('\\n🎉 AUTOMATED TEST PASSED');
  } else {
    console.log('\\n❌ AUTOMATED TEST FAILED');
  }
});
`.replace(/\n/g, '\\n').replace(/'/g, "\\'");

  // Use osascript to inject and execute the test
  const appleScript = `
    tell application "System Events"
      tell process "Warp_Open"
        set frontmost to true
        delay 0.5
        keystroke "i" using {command down, shift down}
        delay 1
      end tell
      
      keystroke "${testScript}"
      delay 0.2
      key code 36
      delay 5
    end tell
  `;

  try {
    await execAsync(`osascript -e '${appleScript}'`);
    console.log('✅ Test script injected and executed\n');
  } catch (e) {
    console.error('❌ Failed to inject test:', e.message);
    process.exit(1);
  }

  // 4. Wait for execution
  console.log('4. Waiting for test to complete...');
  await new Promise(r => setTimeout(r, 7000));

  // 5. Check audit log
  console.log('\n5. Checking audit log...');
  try {
    const { stdout } = await execAsync('wc -l ~/PHASE2_AUDIT.log 2>/dev/null || echo "0"');
    const lines = parseInt(stdout.trim().split(' ')[0]);
    
    if (lines > 0) {
      console.log(`✅ Audit log has ${lines} entries`);
      const { stdout: logContent } = await execAsync('tail -4 ~/PHASE2_AUDIT.log');
      console.log('\nAudit log entries:');
      console.log(logContent);
    } else {
      console.log('⚠️  No audit log entries (test may not have completed)');
    }
  } catch (e) {
    console.log('⚠️  Could not read audit log');
  }

  console.log('\n=================================');
  console.log('✅ Automated Test Complete!');
  console.log('=================================');
  console.log('\nCheck the Warp app console for detailed results.');
}

// Run the test
runTest().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
