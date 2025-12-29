const assert = require('assert');
const { test } = require('node:test');
const fs = require('fs');
const { execFileSync } = require('child_process');
function latestLog(){
  const home = process.env.HOME;
  const files = fs.readdirSync(`${home}/.warp_open/sessions`).filter(f=>f.startsWith('session-') && f.endsWith('.jsonl'));
  files.sort((a,b)=>fs.statSync(`${home}/.warp_open/sessions/${b}`).mtimeMs - fs.statSync(`${home}/.warp_open/sessions/${a}`).mtimeMs);
  return `${home}/.warp_open/sessions/${files[0]}`;
}
test('smoke log has expected events', () => {
  const log = latestLog();
  const txt = fs.readFileSync(log, 'utf8');
  for (const key of ['smoke:start','pty:start','pty:data','pty:exit','smoke:done']) {
    assert.ok(txt.includes(key), `missing ${key}`);
  }
});