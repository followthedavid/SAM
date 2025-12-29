#!/usr/bin/env node
/**
 * Generate comprehensive 10-tab demo for Phase 5 Terminal
 * 
 * Creates demo1.js through demo10.js with realistic workflows:
 * 1. Dev - Development workflow
 * 2. Build - Build and compilation
 * 3. Git - Version control operations
 * 4. Docker - Container management
 * 5. Logs - Log viewing and analysis
 * 6. Tests - Test execution
 * 7. Server - Server operations
 * 8. GitDiff - Code review and diffs
 * 9. Database - Database operations
 * 10. Misc - Miscellaneous commands
 */

const fs = require('fs');
const path = require('path');

const GENERATED_DIR = path.join(__dirname, '..', 'generated');

const demos = [
  {
    id: 1,
    name: 'Dev Tab',
    blocks: [
      { type: 'input', content: 'ls -la', label: '📁 LIST' },
      { type: 'output', content: 'total 48\ndrwxr-xr-x  12 user staff  384 Jan 26 12:30 .\n-rw-r--r--   1 user staff  200 README.md\ndrwxr-xr-x   6 user staff  192 app\ndrwxr-xr-x   4 user staff  128 warp_core' },
      { type: 'input', content: 'cd app/gui-electron', label: '📂 CD' },
      { type: 'input', content: 'npm run dev', label: '📦 NPM' },
      { type: 'output', content: '> electron .\n[main] Electron app ready\n[main] Phase 5 V2 PTY manager initialized' }
    ]
  },
  {
    id: 2,
    name: 'Build Tab',
    blocks: [
      { type: 'input', content: 'npm run build', label: '🔨 BUILD' },
      { type: 'output', content: 'Building production bundle...\nCompiling TypeScript...\nMinifying JavaScript...\n✓ Build complete in 12.3s' },
      { type: 'error', content: 'Warning: deprecated package xyz@1.0.0', label: '⚠️ WARNING', attach_ai: true },
      { type: 'ai', content: 'Consider updating xyz to version 2.0.0 to avoid future compatibility issues.', label: '🤖 AI', attach_ai: true }
    ]
  },
  {
    id: 3,
    name: 'Git Tab',
    blocks: [
      { type: 'input', content: 'git status', label: '🔧 GIT' },
      { type: 'output', content: 'On branch main\nYour branch is up to date with origin/main\nChanges not staged for commit:\n  modified: src/terminal_renderer_v2.js' },
      { type: 'input', content: 'git add .', label: '🔧 GIT' },
      { type: 'input', content: 'git commit -m "Add automation pipeline"', label: '🔧 GIT' },
      { type: 'output', content: '[main abc1234] Add automation pipeline\n 3 files changed, 450 insertions(+), 12 deletions(-)' }
    ]
  },
  {
    id: 4,
    name: 'Docker Tab',
    blocks: [
      { type: 'input', content: 'docker ps', label: '🐳 DOCKER' },
      { type: 'output', content: 'CONTAINER ID   IMAGE          STATUS          PORTS\nabc123def456   node:18        Up 5 minutes    0.0.0.0:3000->3000/tcp' },
      { type: 'input', content: 'docker logs abc123def456', label: '🐳 DOCKER' },
      { type: 'output', content: '[Server] Listening on port 3000\n[Server] Connected to database\n[Server] Ready to accept connections' }
    ]
  },
  {
    id: 5,
    name: 'Logs Tab',
    blocks: [
      { type: 'input', content: 'tail -f /var/log/app.log', label: '📋 LOGS' },
      { type: 'output', content: '2025-01-26 12:00:00 [INFO] Application started\n2025-01-26 12:00:01 [INFO] Database connected\n2025-01-26 12:00:02 [INFO] Server ready\n2025-01-26 12:00:05 [DEBUG] Request received: GET /api/status\n2025-01-26 12:00:05 [DEBUG] Response sent: 200 OK' }
    ]
  },
  {
    id: 6,
    name: 'Tests Tab',
    blocks: [
      { type: 'input', content: 'npm test', label: '🧪 TEST' },
      { type: 'output', content: 'Running test suite...\nPASS test/app.test.js\n  ✓ adds numbers correctly (5ms)\n  ✓ handles edge cases (3ms)\n  ✓ validates input (2ms)\n\nTest Suites: 1 passed, 1 total\nTests: 3 passed, 3 total' },
      { type: 'input', content: '/explain What does npm test do?', label: '🤖 AI' },
      { type: 'ai', content: 'npm test runs the test suite defined in package.json. It executes all test files and reports results, including passed/failed tests and code coverage.', label: '🤖 AI', attach_ai: true }
    ]
  },
  {
    id: 7,
    name: 'Server Tab',
    blocks: [
      { type: 'input', content: 'node server.js', label: '🚀 SERVER' },
      { type: 'output', content: 'Server starting...\nLoading configuration...\nConnecting to database...\n✓ Connected to MongoDB\n✓ Server listening on http://localhost:3000\n✓ Ready to accept connections' }
    ]
  },
  {
    id: 8,
    name: 'GitDiff Tab',
    blocks: [
      { type: 'input', content: 'git diff', label: '🔧 GIT' },
      { type: 'output', content: 'diff --git a/src/terminal_renderer_v2.js b/src/terminal_renderer_v2.js\nindex 123..456 100644\n--- a/src/terminal_renderer_v2.js\n+++ b/src/terminal_renderer_v2.js\n@@ -1,4 +1,4 @@\n-console.log("Hello")\n+console.log("Hello Warp!")\n+// Added automation pipeline integration', label: 'DIFF' },
      { type: 'ai', content: 'Changes add greeting message and automation pipeline comment', label: '🤖 AI', attach_ai: true }
    ]
  },
  {
    id: 9,
    name: 'Database Tab',
    blocks: [
      { type: 'input', content: 'psql -c "SELECT * FROM users LIMIT 5"', label: '🗄️ DATABASE' },
      { type: 'output', content: ' id | username | email | created_at\n----+----------+-------+------------\n  1 | alice    | a@... | 2025-01-20\n  2 | bob      | b@... | 2025-01-21\n  3 | charlie  | c@... | 2025-01-22\n(3 rows)' }
    ]
  },
  {
    id: 10,
    name: 'Misc Tab',
    blocks: [
      { type: 'input', content: 'echo "Phase 5 V2 Warp Terminal with Automation!"', label: '🎉 DEMO' },
      { type: 'output', content: 'Phase 5 V2 Warp Terminal with Automation!' },
      { type: 'input', content: '/ask What features does this terminal have?', label: '🤖 AI' },
      { type: 'ai', content: 'This terminal features:\n- Multi-PTY tab management\n- Collapsible blocks with metadata\n- AI slash commands (/ask, /fix, /explain)\n- Undo/redo with journaling\n- Keyboard shortcuts\n- Session replay from automation pipeline\n- Real-time command execution via Rust backend', label: '🤖 AI', attach_ai: true }
    ]
  }
];

function generateDemoScript(demo) {
  let script = `/**
 * Demo ${demo.id}: ${demo.name}
 * Auto-generated 10-tab demo
 */

(function() {
  'use strict';
  
  if (typeof window === 'undefined' || !window.ptyManager || !window.renderer) {
    console.warn('[Demo${demo.id}] Terminal renderer not loaded');
    return;
  }
  
  console.log('[Demo${demo.id}] Loading ${demo.name}');
  
  // Create tab
  const tab = window.ptyManager.createTab('${demo.name}', '/Users/davidquinton/projects');
  console.log('[Demo${demo.id}] Created tab: ${demo.name}');
  
`;

  demo.blocks.forEach((block, idx) => {
    const content = block.content.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
    const label = block.label || block.type.toUpperCase();
    const attach_ai = block.attach_ai ? 'true' : 'false';
    
    script += `  // Block ${idx + 1}: ${label}\n`;
    script += `  window.renderer.appendBlock('${block.type}', "${content}", {\n`;
    script += `    attach_ai: ${attach_ai},\n`;
    script += `    label: '${label}',\n`;
    script += `    timestamp: new Date().toISOString(),\n`;
    script += `    sessionId: tab.id\n`;
    script += `  });\n\n`;
  });

  script += `  console.log('[Demo${demo.id}] ${demo.name} loaded successfully');\n`;
  script += `  console.log('[Demo${demo.id}] ${demo.blocks.length} blocks created');\n`;
  script += `  \n})();\n`;

  return script;
}

function main() {
  console.log('='.repeat(60));
  console.log('10-Tab Demo Generation');
  console.log('='.repeat(60));
  
  if (!fs.existsSync(GENERATED_DIR)) {
    fs.mkdirSync(GENERATED_DIR, { recursive: true });
  }

  demos.forEach(demo => {
    const script = generateDemoScript(demo);
    const filename = `demo${demo.id}.js`;
    const filepath = path.join(GENERATED_DIR, filename);
    
    fs.writeFileSync(filepath, script);
    console.log(`  ✓ ${filename} (${demo.blocks.length} blocks)`);
  });

  console.log(`\n✓ Generated ${demos.length} demo files`);
  console.log(`✓ Output directory: ${GENERATED_DIR}`);
  console.log('\nTo load all demos:');
  console.log('  Add to index.html: <script src="generated/demo1.js"></script>');
  console.log('  Or load via: window.replayLoader.loadReplay("demo1")');
}

if (require.main === module) {
  main();
}

module.exports = { demos, generateDemoScript };
