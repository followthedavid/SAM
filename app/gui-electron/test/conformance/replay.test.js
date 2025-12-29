/* eslint-disable */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..', '..'); // app/gui-electron
const proj = path.resolve(root, '..', '..'); // Warp_Open

function writeJSONL(lines) {
  const fp = path.join(process.env.TMPDIR || '/tmp', `warp_open_test_${Date.now()}.jsonl`);
  fs.writeFileSync(fp, lines.map(o => JSON.stringify(o)).join('\n') + '\n');
  return fp;
}

test('replay_session.js concatenates PTY data in order', () => {
  const ptyId = 'pty-1';
  const lines = [
    { ts: 't1', type: 'pty_start', ptyId },
    { ts: 't2', type: 'pty_data', ptyId, data: 'hello ' },
    { ts: 't3', type: 'pty_data', ptyId, data: 'world' },
    { ts: 't4', type: 'pty_exit', ptyId, exitCode: 0 }
  ];
  const fp = writeJSONL(lines);
  const script = path.resolve(proj, 'tools', 'replay_session.js');
  const out = spawnSync(process.execPath, [script, fp, ptyId], { encoding: 'utf8' });
  assert.strictEqual(out.status, 0);
  assert.strictEqual(out.stdout, 'hello world');
});