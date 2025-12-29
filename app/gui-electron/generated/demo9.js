/**
 * Demo 9: Database Tab
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo9] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo9] Loading Database Tab');
  
  // Create tab
  const tab = window.ptyManager.createTab('Database Tab', '/Users/davidquinton/projects');
  console.log('[Demo9] Created tab: Database Tab');
  
  // Block 1: 🗄️ DATABASE
  window.renderer.appendBlock('input', "psql -c \"SELECT * FROM users LIMIT 5\"", {
    attach_ai: false,
    label: '🗄️ DATABASE',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  // Block 2: OUTPUT
  window.renderer.appendBlock('output', " id | username | email | created_at\n----+----------+-------+------------\n  1 | alice    | a@... | 2025-01-20\n  2 | bob      | b@... | 2025-01-21\n  3 | charlie  | c@... | 2025-01-22\n(3 rows)", {
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: new Date().toISOString(),
    sessionId: tab.id
  });

  console.log('[Demo9] Database Tab loaded successfully');
  console.log('[Demo9] 2 blocks created');
  
})();
