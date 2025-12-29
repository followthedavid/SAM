/**
 * Demo 8: GitDiff Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo8] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo8] Loading GitDiff Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('GitDiff Tab', '/Users/davidquinton/projects');
  console.log('[Demo8] Created tab: GitDiff Tab');
  
  // Block 1: 🔧 GIT
  window.renderer.appendBlock('input', "git diff", {
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: DIFF
  window.renderer.appendBlock('output', "diff --git a/src/terminal_renderer_v2.js b/src/terminal_renderer_v2.js\nindex 123..456 100644\n--- a/src/terminal_renderer_v2.js\n+++ b/src/terminal_renderer_v2.js\n@@ -1,4 +1,4 @@\n-console.log(\"Hello\")\n+console.log(\"Hello Warp!\")\n+// Added automation pipeline integration", {
    attach_ai: false,
    label: 'DIFF',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 🤖 AI
  window.renderer.appendBlock('ai', "Changes add greeting message and automation pipeline comment", {
    attach_ai: true,
    label: '🤖 AI',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo8] GitDiff Tab loaded successfully');
  console.log('[Demo8] 3 blocks created');
  
})();
