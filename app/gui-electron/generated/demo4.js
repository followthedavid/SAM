/**
 * Demo 4: Docker Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo4] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo4] Loading Docker Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Docker Tab', '/Users/davidquinton/projects');
  console.log('[Demo4] Created tab: Docker Tab');
  
  // Block 1: 🐳 DOCKER
  window.renderer.appendBlock('input', "docker ps", {
    attach_ai: false,
    label: '🐳 DOCKER',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', "CONTAINER ID   IMAGE          STATUS          PORTS\nabc123def456   node:18        Up 5 minutes    0.0.0.0:3000->3000/tcp", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 3: 🐳 DOCKER
  window.renderer.appendBlock('input', "docker logs abc123def456", {
    attach_ai: false,
    label: '🐳 DOCKER',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 4: OUTPUT
  window.renderer.appendBlock('output', "[Server] Listening on port 3000\n[Server] Connected to database\n[Server] Ready to accept connections", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo4] Docker Tab loaded successfully');
  console.log('[Demo4] 4 blocks created');
  
})();
