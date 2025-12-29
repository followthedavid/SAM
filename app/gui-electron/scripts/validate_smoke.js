/* Validate latest (or given) JSONL for expected smoke markers and content.
 * Usage: node scripts/validate_smoke.js [path/to/session-*.jsonl]
 * Exits non-zero if requirements are not met.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

function latestJsonl() {
  const dir = path.join(os.homedir(), '.warp_open', 'sessions');
  const files = fs.readdirSync(dir).filter(f => f.startsWith('session-') && f.endsWith('.jsonl'))
    .map(f => path.join(dir, f))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!files.length) throw new Error('No session-*.jsonl files found');
  return files[0];
}

const file = process.argv[2] || latestJsonl();
const lines = fs.readFileSync(file, 'utf8').trim().split(/\r?\n/).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);

const have = (type) => lines.some(o => o.type === type);
const getAll = (type) => lines.filter(o => o.type === type);

function assert(cond, msg) { if (!cond) { console.error('FAIL:', msg); process.exit(1); } }

assert(have('smoke:start'), 'missing smoke:start');
assert(have('pty:start'), 'missing pty:start');
assert(have('pty:exit'), 'missing pty:exit');
assert(have('smoke:done') || have('smoke:timeout'), 'missing smoke:done/timeout');

const data = getAll('pty:data').map(o => String(o.data)).join('');
assert(data.length > 0, 'no pty:data captured');

assert(/\[smoke] hello/.test(data), 'expected greeting not found in pty:data');
assert(/uname\s+-a/.test(data) || /Darwin/.test(data) || /Linux/.test(data), 'uname evidence missing');
assert(/\]8;;https:\/\/example\.com/.test(data), 'OSC8 hyperlink sequence not found');

console.log('OK:', path.basename(file));
process.exit(0);