/**
 * Demo 2: Build Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo2] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo2] Loading Build Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Build Tab', '/Users/davidquinton/projects');
  console.log('[Demo2] Created tab: Build Tab');
  
  // Block 1: 🔨 BUILD
  window.renderer.appendBlock('input', "npm run build", {
    attach_ai: false,
    label: '🔨 BUILD',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "Building production bundle...\nCompiling TypeScript...\nMinifying JavaScript...\n✓ Build complete in 12.3s", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: ⚠️ WARNING
  window.renderer.appendBlock('error', "Warning: deprecated package xyz@1.0.0", {
    attach_ai: true,
    label: '⚠️ WARNING',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: 🤖 AI
  window.renderer.appendBlock('ai', "Consider updating xyz to version 2.0.0 to avoid future compatibility issues.", {
    attach_ai: true,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo2] Build Tab loaded successfully');
  console.log('[Demo2] 4 blocks created');
  
})();
