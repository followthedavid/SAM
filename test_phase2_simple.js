// Simple Phase 2 Test - Copy and paste this entire block into console

(async () => {
  const { invoke } = window.__TAURI__.tauri;
  const wait = (ms) => new Promise(r => setTimeout(r, ms));
  
  console.log('🧪 Phase 2 Quick Test\n');
  
  // Create batch
  console.log('1️⃣ Creating batch...');
  const batchId = await invoke('create_batch', {
    tabId: 1,
    entries: [
      {tool: 'execute_shell', args: {command: 'echo "Phase 2 Test"'}},
      {tool: 'execute_shell', args: {command: 'pwd'}},
      {tool: 'execute_shell', args: {command: 'whoami'}}
    ]
  });
  console.log('✅ Batch created:', batchId.substring(0, 8) + '...');
  
  await wait(500);
  
  // Approve batch
  console.log('\n2️⃣ Approving batch...');
  await invoke('approve_batch', {batchId, autonomyToken: null});
  console.log('✅ Approved');
  
  await wait(500);
  
  // Run batch
  console.log('\n3️⃣ Running batch...');
  await invoke('run_batch', {batchId, autonomyToken: null});
  console.log('✅ Started execution');
  
  await wait(2000);
  
  // Check results
  console.log('\n4️⃣ Checking results...');
  const batches = await invoke('get_batches');
  const result = batches.find(b => b.id === batchId);
  
  console.log('\n📊 Results:');
  console.log('Status:', result.status);
  result.entries.forEach((e, i) => {
    console.log(`\n${i+1}. ${e.args.command}`);
    console.log('   Safe Score:', e.safe_score);
    console.log('   Result:', e.result || 'No result');
  });
  
  console.log('\n✅ Test Complete!');
  console.log('Check audit log: tail ~/PHASE2_AUDIT.log');
  
  return batchId;
})();
