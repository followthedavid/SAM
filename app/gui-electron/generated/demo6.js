/**
 * Demo 6: Tests Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo6] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo6] Loading Tests Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Tests Tab', '/Users/davidquinton/projects');
  console.log('[Demo6] Created tab: Tests Tab');
  
  // Block 1: 🧪 TEST
  window.renderer.appendBlock('input', "npm test", {
    attach_ai: false,
    label: '🧪 TEST',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "Running test suite...\nPASS test/app.test.js\n  ✓ adds numbers correctly (5ms)\n  ✓ handles edge cases (3ms)\n  ✓ validates input (2ms)\n\nTest Suites: 1 passed, 1 total\nTests: 3 passed, 3 total", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 🤖 AI
  window.renderer.appendBlock('input', "/explain What does npm test do?", {
    attach_ai: false,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: 🤖 AI
  window.renderer.appendBlock('ai', "npm test runs the test suite defined in package.json. It executes all test files and reports results, including passed/failed tests and code coverage.", {
    attach_ai: true,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo6] Tests Tab loaded successfully');
  console.log('[Demo6] 4 blocks created');
  
})();
