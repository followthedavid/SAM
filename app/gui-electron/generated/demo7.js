/**
 * Demo 7: Server Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo7] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo7] Loading Server Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Server Tab', '/Users/davidquinton/projects');
  console.log('[Demo7] Created tab: Server Tab');
  
  // Block 1: 🚀 SERVER
  window.renderer.appendBlock('input', "node server.js", {
    attach_ai: false,
    label: '🚀 SERVER',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "Server starting...\nLoading configuration...\nConnecting to database...\n✓ Connected to MongoDB\n✓ Server listening on http://localhost:3000\n✓ Ready to accept connections", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo7] Server Tab loaded successfully');
  console.log('[Demo7] 2 blocks created');
  
})();
