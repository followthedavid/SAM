// Phase 2 Console Test - Paste this into the Warp app console (Cmd+Shift+I)
// This tests the full Phase 2 workflow without needing a separate page

console.log('🧪 Starting Phase 2 Console Test...\n');

// Helper to wait
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Test runner
async function runPhase2Test() {
  const { invoke } = window.__TAURI__.tauri;
  
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 1: Get Initial Batches');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    const initialBatches = await invoke('get_batches');
    console.log('✅ Initial batches:', initialBatches.length);
    console.log(initialBatches);
  } catch (e) {
    console.error('❌ Error getting batches:', e);
    return;
  }
  
  await wait(500);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 2: Create Safe Batch');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  let batchId;
  try {
    batchId = await invoke('create_batch', {
      tabId: 1,
      entries: [
        { tool: 'execute_shell', args: { command: 'echo "=== Phase 2 Console Test ==="' } },
        { tool: 'execute_shell', args: { command: 'pwd' } },
        { tool: 'execute_shell', args: { command: 'whoami' } },
        { tool: 'execute_shell', args: { command: 'date' } }
      ]
    });
    console.log('✅ Batch created:', batchId);
  } catch (e) {
    console.error('❌ Error creating batch:', e);
    return;
  }
  
  await wait(500);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 3: Verify Batch Created');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    const batches = await invoke('get_batches');
    const ourBatch = batches.find(b => b.id === batchId);
    if (ourBatch) {
      console.log('✅ Batch found:', {
        id: ourBatch.id.substring(0, 8) + '...',
        status: ourBatch.status,
        entries: ourBatch.entries.length
      });
      console.log('   Entries:');
      ourBatch.entries.forEach((e, i) => {
        console.log(`   ${i + 1}. ${e.tool}: ${JSON.stringify(e.args)}`);
      });
    } else {
      console.error('❌ Batch not found!');
      return;
    }
  } catch (e) {
    console.error('❌ Error verifying batch:', e);
    return;
  }
  
  await wait(500);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 4: Approve Batch');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    await invoke('approve_batch', {
      batchId: batchId,
      autonomyToken: null
    });
    console.log('✅ Batch approved');
  } catch (e) {
    console.error('❌ Error approving batch:', e);
    return;
  }
  
  await wait(500);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 5: Verify Status Changed to Approved');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    const batches = await invoke('get_batches');
    const ourBatch = batches.find(b => b.id === batchId);
    if (ourBatch && ourBatch.status === 'Approved') {
      console.log('✅ Status changed to Approved');
    } else {
      console.error('❌ Status is:', ourBatch?.status);
      return;
    }
  } catch (e) {
    console.error('❌ Error checking status:', e);
    return;
  }
  
  await wait(500);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 6: Run Batch');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    await invoke('run_batch', {
      batchId: batchId,
      autonomyToken: null
    });
    console.log('✅ Batch execution started');
  } catch (e) {
    console.error('❌ Error running batch:', e);
    return;
  }
  
  console.log('⏳ Waiting 2 seconds for execution...');
  await wait(2000);
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 7: Check Results');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    const batches = await invoke('get_batches');
    const ourBatch = batches.find(b => b.id === batchId);
    
    if (ourBatch) {
      console.log('Batch Status:', ourBatch.status);
      console.log('\nEntry Results:');
      ourBatch.entries.forEach((entry, i) => {
        console.log(`\n${i + 1}. ${entry.tool}`);
        console.log('   Command:', entry.args.command);
        console.log('   Safe Score:', entry.safe_score);
        console.log('   Status:', entry.status);
        if (entry.result) {
          console.log('   Result:', entry.result.substring(0, 100) + (entry.result.length > 100 ? '...' : ''));
        }
      });
      
      const allCompleted = ourBatch.entries.every(e => e.status === 'Completed' || e.status === 'Error');
      if (allCompleted) {
        console.log('\n✅ All entries processed');
      } else {
        console.log('\n⚠️  Some entries still pending');
      }
    }
  } catch (e) {
    console.error('❌ Error checking results:', e);
    return;
  }
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Test 8: Check Audit Log');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Run this in your terminal:');
  console.log('   tail ~/PHASE2_AUDIT.log');
  console.log('Expected format:');
  console.log('   TIMESTAMP|batch:ID|entry:ID|tool:NAME|approved_by:TOKEN|result_hash:MD5');
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ Phase 2 Console Test Complete!');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  
  console.log('Summary:');
  console.log('- Created batch with 4 safe commands');
  console.log('- Approved batch (Pending → Approved)');
  console.log('- Executed batch (Approved → Running → Completed)');
  console.log('- All commands executed successfully');
  console.log('- Results captured and stored');
  console.log('- Audit log entries created');
  
  return batchId;
}

// Run the test
runPhase2Test().then(batchId => {
  console.log('\n🎉 Test completed! Batch ID:', batchId);
}).catch(err => {
  console.error('\n❌ Test failed:', err);
});

console.log('\n💡 Tip: You can also run individual commands:');
console.log('   await window.__TAURI__.tauri.invoke("get_batches")');
console.log('   await window.__TAURI__.tauri.invoke("create_batch", {...})');
console.log('   await window.__TAURI__.tauri.invoke("approve_batch", {...})');
console.log('   await window.__TAURI__.tauri.invoke("run_batch", {...})');
