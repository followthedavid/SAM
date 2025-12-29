/**
 * Demo 3: Git Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo3] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo3] Loading Git Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Git Tab', '/Users/davidquinton/projects');
  console.log('[Demo3] Created tab: Git Tab');
  
  // Block 1: 🔧 GIT
  window.renderer.appendBlock('input', "git status", {
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "On branch main\nYour branch is up to date with origin/main\nChanges not staged for commit:\n  modified: src/terminal_renderer_v2.js", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 🔧 GIT
  window.renderer.appendBlock('input', "git add .", {
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: 🔧 GIT
  window.renderer.appendBlock('input', "git commit -m \"Add automation pipeline\"", {
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 5: OUTPUT
  window.renderer.appendBlock('output', "[main abc1234] Add automation pipeline\n 3 files changed, 450 insertions(+), 12 deletions(-)", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo3] Git Tab loaded successfully');
  console.log('[Demo3] 5 blocks created');
  
})();
