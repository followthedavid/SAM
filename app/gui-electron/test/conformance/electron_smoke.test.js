/* eslint-disable */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const appDir = path.resolve(__dirname, '..', '..'); // app/gui-electron

function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }

// This smoke launches Electron for ~2s and verifies a session JSONL file appears
// Skips silently if electron CLI cannot be resolved

test('electron smoke: creates session JSONL', async (t) => {
  if (!process.env.WARP_OPEN_ENABLE_SMOKE) { t.diagnostic('skipping smoke test (set WARP_OPEN_ENABLE_SMOKE=1 to enable)'); return; }
  let cli;
  try { cli = require.resolve('electron/cli.js'); } catch { t.diagnostic('electron not installed'); return; }
  const sessionId = `smoketest-${Date.now()}`;
  const tmpDir = path.join(process.env.TMPDIR || '/tmp', `warp_open_sessions_${Date.now()}`);
  fs.mkdirSync(tmpDir, { recursive: true });
  const env = Object.assign({}, process.env, { WARP_OPEN_SESSION: sessionId, WARP_OPEN_LOG_DIR: tmpDir });
  const child = spawn(process.execPath, [cli, '.'], { cwd: appDir, env, stdio: 'ignore' });
  // Poll up to ~6s for session log to appear
  let hit = null;
  for (let i=0; i<24; i++) {
    await sleep(250);
    const files = fs.existsSync(tmpDir) ? fs.readdirSync(tmpDir) : [];
    hit = files.find(f => f.includes(sessionId));
    if (hit) break;
  }
  child.kill('SIGTERM');
  await sleep(300);
  assert.ok(hit, 'no session JSONL created');
});
