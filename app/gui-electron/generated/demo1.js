/**
 * Demo 1: Dev Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo1] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo1] Loading Dev Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Dev Tab', '/Users/davidquinton/projects');
  console.log('[Demo1] Created tab: Dev Tab');
  
  // Block 1: 📁 LIST
  window.renderer.appendBlock('input', "ls -la", {
    attach_ai: false,
    label: '📁 LIST',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "total 48\ndrwxr-xr-x  12 user staff  384 Jan 26 12:30 .\n-rw-r--r--   1 user staff  200 README.md\ndrwxr-xr-x   6 user staff  192 app\ndrwxr-xr-x   4 user staff  128 warp_core", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 📂 CD
  window.renderer.appendBlock('input', "cd app/gui-electron", {
    attach_ai: false,
    label: '📂 CD',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: 📦 NPM
  window.renderer.appendBlock('input', "npm run dev", {
    attach_ai: false,
    label: '📦 NPM',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 5: OUTPUT
  window.renderer.appendBlock('output', "> electron .\n[main] Electron app ready\n[main] Phase 5 V2 PTY manager initialized", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo1] Dev Tab loaded successfully');
  console.log('[Demo1] 5 blocks created');
  
})();
