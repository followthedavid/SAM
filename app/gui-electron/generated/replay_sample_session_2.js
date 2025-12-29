/**
 * Auto-generated replay script for session: sample_session_2
 * Generated from: /Users/davidquinton/ReverseLab/warp_auto/data/raw_warp_dump/sample_session_2.log
 * Total blocks: 5
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Replay] Terminal renderer not loaded yet');
    return;
  }
  
  console.log('[Replay] Loading session: sample_session_2');

  // Create tab: tab1
  const tab = window.ptyManager.createTab('tab1', '/');
  console.log('[Replay] Created tab: tab1');

  // Block b1 (❌ ERROR)
  window.renderer.appendBlock('error', "2025-01-26T14:00:00 davidquinton@macbook ~/projects/demo $ python test.py\\nTraceback (most recent call last):\\n  File \\\"test.py\\\", line 5, in <module>\\n    result = divide(10, 0)\\n  File \\\"test.py\\\", line 2, in divide\\n    return a / b\\nZeroDivisionError: division by zero", {
    collapsed: false,
    attach_ai: true,
    label: '❌ ERROR',
    timestamp: '2025-01-26T14:00:00',
    patterns: ["python_command","error","python_traceback"],
    sessionId: tab.id
  });

  // Block b2 (❌ ERROR)
  window.renderer.appendBlock('ai', "2025-01-26T14:01:30 davidquinton@macbook ~/projects/demo $ /ask How do I handle division by zero in Python?\\nAI: You can handle division by zero using try-except blocks. Here's an example:\\n\\n```python\\ndef safe_divide(a, b):\\n    try:\\n        return a / b\\n    except ZeroDivisionError:\\n        return \\\"Error: Cannot divide by zero\\\"\\n```\\n\\nThis will catch the ZeroDivisionError and return a friendly message instead of crashing.", {
    collapsed: false,
    attach_ai: true,
    label: '❌ ERROR',
    timestamp: '2025-01-26T14:01:30',
    patterns: ["error","ai_command"],
    sessionId: tab.id
  });

  // Block b3 (❌ ERROR)
  window.renderer.appendBlock('error', "2025-01-26T14:02:45 davidquinton@macbook ~/projects/demo $ cat > test_fixed.py\\ndef safe_divide(a, b):\\n    try:\\n        return a / b\\n    except ZeroDivisionError:\\n        return \\\"Error: Cannot divide by zero\\\"\\n\\nresult = safe_divide(10, 0)\\nprint(result)", {
    collapsed: false,
    attach_ai: true,
    label: '❌ ERROR',
    timestamp: '2025-01-26T14:02:45',
    patterns: ["file_write","error"],
    sessionId: tab.id
  });

  // Block b4 (❌ ERROR)
  window.renderer.appendBlock('error', "2025-01-26T14:03:00 davidquinton@macbook ~/projects/demo $ python test_fixed.py\\nError: Cannot divide by zero", {
    collapsed: false,
    attach_ai: true,
    label: '❌ ERROR',
    timestamp: '2025-01-26T14:03:00',
    patterns: ["python_command","error"],
    sessionId: tab.id
  });

  // Block b5 (❌ ERROR)
  window.renderer.appendBlock('ai', "2025-01-26T14:03:15 davidquinton@macbook ~/projects/demo $ /explain What does try-except do?\\nAI: The try-except block in Python is used for exception handling. The code inside the 'try' block is executed, and if an exception occurs, Python looks for a matching 'except' block to handle it. This prevents your program from crashing and allows you to handle errors gracefully.", {
    collapsed: false,
    attach_ai: true,
    label: '❌ ERROR',
    timestamp: '2025-01-26T14:03:15',
    patterns: ["error","ai_command"],
    sessionId: tab.id
  });

  console.log('[Replay] Session sample_session_2 loaded successfully');
  console.log('[Replay] Total tabs: 1');
  console.log('[Replay] Total blocks: 5');
  
})();
