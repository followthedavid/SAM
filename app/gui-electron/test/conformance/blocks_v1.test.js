const {strict: assert} = require('node:assert');
const {test} = require('node:test');
const {parseOSC} = require('../../src/blocks.js');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const wantInteractive = process.env.WARP_OPEN_TEST_INTERACTIVE === '1';
const dir = path.join(os.homedir(), '.warp_open', 'sessions');
const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter(f=>f.startsWith('session-') && f.endsWith('.jsonl')).map(f=>path.join(dir,f)) : [];

if (!files.length && wantInteractive) {
  throw new Error('No session logs found, but interactive required');
}

const f = files.length > 0 ? files.sort((a,b)=>fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0] : null;

test('has expected events in session logs', () => {
  if (!f) {
    console.log('No session logs yet; skipping strict block assertions.');
    return;
  }
  
  const lines = fs.readFileSync(f, 'utf8').trim().split(/\r?\n/).map(JSON.parse);
  assert(lines.some(e=>e.type==='pty:start'), 'pty:start missing');

  if (wantInteractive) {
    assert(lines.some(e=>e.type==='block:start'), 'block:start missing (interactive required)');
    assert(lines.some(e=>e.type==='block:exec:end' || e.type==='block:end'), 'block:end missing (interactive required)');
  }
});
