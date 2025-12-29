/**
 * Demo 10: Misc Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo10] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo10] Loading Misc Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Misc Tab', '/Users/davidquinton/projects');
  console.log('[Demo10] Created tab: Misc Tab');
  
  // Block 1: 🎉 DEMO
  window.renderer.appendBlock('input', "echo \"Phase 5 V2 Warp Terminal with Automation!\"", {
    attach_ai: false,
    label: '🎉 DEMO',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "Phase 5 V2 Warp Terminal with Automation!", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 🤖 AI
  window.renderer.appendBlock('input', "/ask What features does this terminal have?", {
    attach_ai: false,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: 🤖 AI
  window.renderer.appendBlock('ai', "This terminal features:\n- Multi-PTY tab management\n- Collapsible blocks with metadata\n- AI slash commands (/ask, /fix, /explain)\n- Undo/redo with journaling\n- Keyboard shortcuts\n- Session replay from automation pipeline\n- Real-time command execution via Rust backend", {
    attach_ai: true,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo10] Misc Tab loaded successfully');
  console.log('[Demo10] 4 blocks created');
  
})();
