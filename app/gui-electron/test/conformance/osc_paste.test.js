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

test('bracketed paste sequences are preserved in replay', () => {
  const ptyId = 'pty-2';
  const ESC = '\u001b';
  const pasteStart = `${ESC}[200~`;
  const pasteEnd = `${ESC}[201~`;
  const payload = 'pasted text with spaces & symbols!';
  const lines = [
    { type: 'pty_start', ptyId },
    { type: 'pty_data', ptyId, data: pasteStart },
    { type: 'pty_data', ptyId, data: payload },
    { type: 'pty_data', ptyId, data: pasteEnd },
    { type: 'pty_exit', ptyId, exitCode: 0 }
  ];
  const fp = writeJSONL(lines);
  const script = path.resolve(proj, 'tools', 'replay_session.js');
  const out = spawnSync(process.execPath, [script, fp, ptyId], { encoding: null });
  assert.strictEqual(out.status, 0);
  const buf = out.stdout || Buffer.alloc(0);
  // Expect ESC [ 2 0 0 ~ ... ESC [ 2 0 1 ~
  function includesBytes(hay, needleArr) {
    const n = Buffer.from(needleArr);
    outer: for (let i=0;i<=hay.length-n.length;i++) {
      for (let j=0;j<n.length;j++) if (hay[i+j] !== n[j]) continue outer;
      return true;
    }
    return false;
  }
  const esc = 0x1b;
  const startBytes = [esc, 0x5b, 0x32, 0x30, 0x30, 0x7e];
  const endBytes = [esc, 0x5b, 0x32, 0x30, 0x31, 0x7e];
  assert.ok(includesBytes(buf, startBytes), 'missing paste start');
  assert.ok(buf.toString('utf8').includes(payload), 'missing payload');
  assert.ok(includesBytes(buf, endBytes), 'missing paste end');
});

test('OSC 8 hyperlink sequences pass through replay', () => {
  const ptyId = 'pty-3';
  const ESC = '\u001b';
  const ST = `${ESC}\\`;
  const url = 'https://example.com';
  const seq = `${ESC}]8;;${url}${ST}link${ESC}]8;;${ST}`;
  const lines = [
    { type: 'pty_start', ptyId },
    { type: 'pty_data', ptyId, data: seq },
    { type: 'pty_exit', ptyId, exitCode: 0 }
  ];
  const fp = writeJSONL(lines);
  const script = path.resolve(proj, 'tools', 'replay_session.js');
  const out = spawnSync(process.execPath, [script, fp, ptyId], { encoding: 'utf8' });
  assert.strictEqual(out.status, 0);
  assert.ok(out.stdout.includes('link'), 'missing link text');
  assert.ok(out.stdout.includes(url), 'missing url inside OSC sequence');
});
