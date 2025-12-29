const { spawn } = require('node:child_process');
const path = require('node:path');
const electron = require('electron');
const args = ['.'];
const env = {
  ...process.env,
  ELECTRON_ENABLE_LOGGING: '1',
  ELECTRON_DISABLE_SECURITY_WARNINGS: '1',
  WARP_OPEN_ENABLE_SMOKE: '1'
};
let buf = '';
const p = spawn(electron, args, { cwd: process.cwd(), env });
p.stdout.on('data', d => { buf += d.toString(); process.stdout.write(d); });
p.stderr.on('data', d => { buf += d.toString(); process.stderr.write(d); });

const timeoutMs = 60_000;
const timer = setTimeout(() => {
  console.error('[test:preload] timeout');
  p.kill('SIGKILL');
}, timeoutMs);

p.on('exit', (code) => {
  clearTimeout(timer);
  const ok = /\[preload\]\s*xterm require OK/i.test(buf);
  if (!ok) {
    console.error('\n[test:preload] FAIL: did not see "[preload] xterm require OK" in Electron logs');
    process.exit(1);
  }
  console.log('\n[test:preload] PASS');
  process.exit(0);
});