/**
 * Auto-generated replay script for session: sample_session_1
 * Generated from: /Users/davidquinton/ReverseLab/warp_auto/data/raw_warp_dump/sample_session_1.log
 * Total blocks: 6
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Replay] Terminal renderer not loaded yet');
    return;
  }
  
  console.log('[Replay] Loading session: sample_session_1');

  // Create tab: tab1
  const tab = window.ptyManager.createTab('tab1', '/');
  console.log('[Replay] Created tab: tab1');

  // Block b6 (OUTPUT)
  window.renderer.appendBlock('output', "2025-01-26T12:30:00 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open $ ls -la\\ntotal 48\\ndrwxr-xr-x  12 davidquinton  staff   384 Jan 26 12:30 .\\ndrwxr-xr-x   8 davidquinton  staff   256 Jan 26 12:00 ..\\n-rw-r--r--   1 davidquinton  staff  1234 Jan 26 12:29 README.md\\ndrwxr-xr-x   6 davidquinton  staff   192 Jan 26 12:28 app\\ndrwxr-xr-x   4 davidquinton  staff   128 Jan 26 12:27 warp_core", {
    collapsed: false,
    attach_ai: false,
    label: 'OUTPUT',
    timestamp: '2025-01-26T12:30:00',
    patterns: [],
    sessionId: tab.id
  });

  // Block b7 (INPUT)
  window.renderer.appendBlock('input', "2025-01-26T12:31:15 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open $ cd app/gui-electron", {
    collapsed: false,
    attach_ai: false,
    label: 'INPUT',
    timestamp: '2025-01-26T12:31:15',
    patterns: ["cd_command"],
    sessionId: tab.id
  });

  // Block b8 (📦 NPM)
  window.renderer.appendBlock('input', "2025-01-26T12:31:20 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open/app/gui-electron $ npm run dev\\n> warp-open-electron@0.1.2 dev\\n> electron .\\n\\n[main] Electron app ready\\n[main] Phase 5 V2 PTY manager initialized\\n[TerminalRendererV2] Loading...\\n[TerminalRendererV2] Initializing...\\n[TerminalRendererV2] Created session 1762675548659-717733", {
    collapsed: false,
    attach_ai: false,
    label: '📦 NPM',
    timestamp: '2025-01-26T12:31:20',
    patterns: ["npm_command"],
    sessionId: tab.id
  });

  // Block b9 (🔧 GIT)
  window.renderer.appendBlock('input', "2025-01-26T12:32:45 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open/app/gui-electron $ git status\\nOn branch phase5-v2\\nYour branch is up to date with 'origin/phase5-v2'.\\n\\nChanges not staged for commit:\\n  (use \\\"git add <file>...\\\" to update what will be committed)\\n  (use \\\"git restore <file>...\\\" to discard changes in working directory)\\n\\tmodified:   src/terminal/terminal_renderer_v2.js\\n\\nno changes added to commit (use \\\"git add\\\" and/or \\\"git commit -a\\\")", {
    collapsed: false,
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: '2025-01-26T12:32:45',
    patterns: ["git_command"],
    sessionId: tab.id
  });

  // Block b10 (🔧 GIT)
  window.renderer.appendBlock('input', "2025-01-26T12:33:10 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open/app/gui-electron $ git add .", {
    collapsed: false,
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: '2025-01-26T12:33:10',
    patterns: ["git_command"],
    sessionId: tab.id
  });

  // Block b11 (🔧 GIT)
  window.renderer.appendBlock('input', "2025-01-26T12:33:15 davidquinton@macbook /Users/davidquinton/ReverseLab/Warp_Open/app/gui-electron $ git commit -m \\\"Fix ANSI code stripping in terminal renderer\\\"\\n[phase5-v2 abc1234] Fix ANSI code stripping in terminal renderer\\n 1 file changed, 2 insertions(+), 1 deletion(-)", {
    collapsed: false,
    attach_ai: false,
    label: '🔧 GIT',
    timestamp: '2025-01-26T12:33:15',
    patterns: ["git_command"],
    sessionId: tab.id
  });

  // Macros for this session
  const macros = [
  {
    "name": "git-commit-workflow",
    "description": "Add and commit changes",
    "steps": [
      "git status",
      "git add .",
      "git commit -m \"Fix ANSI code stripping in terminal renderer\""
    ]
  },
  {
    "name": "npm-dev-workflow",
    "description": "NPM development commands",
    "steps": [
      "npm run dev"
    ]
  }
];
  if (window.macroManager) {
    macros.forEach(m => window.macroManager.registerMacro(m));
  }

  console.log('[Replay] Session sample_session_1 loaded successfully');
  console.log('[Replay] Total tabs: 1');
  console.log('[Replay] Total blocks: 6');
  
})();
