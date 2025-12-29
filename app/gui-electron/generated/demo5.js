/**
 * Demo 5: Logs Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo5] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo5] Loading Logs Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Logs Tab', '/Users/davidquinton/projects');
  console.log('[Demo5] Created tab: Logs Tab');
  
  // Block 1: 📋 LOGS
  window.renderer.appendBlock('input', "tail -f /var/log/app.log", {
    attach_ai: false,
    label: '📋 LOGS',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "2025-01-26 12:00:00 [INFO] Application started\n2025-01-26 12:00:01 [INFO] Database connected\n2025-01-26 12:00:02 [INFO] Server ready\n2025-01-26 12:00:05 [DEBUG] Request received: GET /api/status\n2025-01-26 12:00:05 [DEBUG] Response sent: 200 OK", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo5] Logs Tab loaded successfully');
  console.log('[Demo5] 2 blocks created');
  
})();
