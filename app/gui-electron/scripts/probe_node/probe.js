const os = require('os');
const process = require('process');

function log(k, v) { console.log(`${k}: ${v}`); }

(async () => {
  log('node.version', process.version);
  log('node.modules.abi', process.versions.modules);
  log('platform', process.platform);
  log('arch', process.arch);

  // Load node-pty built for *system Node* in this subproject
  const pty = require('node-pty');
  const shell = process.env.SHELL || (process.platform === 'win32' ? 'pwsh.exe' : '/bin/zsh');

  const term = pty.spawn(shell, ['-il'], {
    name: 'xterm-256color',
    cols: 80,
    rows: 24,
    cwd: process.env.HOME,
    env: { ...process.env, PS1: '> ' }
  });

  let sawOK = false;
  term.onData(d => {
    process.stdout.write(d);            // show what we get
    if (/PROBE_OK/.test(d)) sawOK = true;
  });

  // Drive a short scripted session
  setTimeout(() => term.write('echo PROBE_OK\r'), 200);
  setTimeout(() => term.write('exit\r'), 500);

  term.onExit(e => {
    log('pty.exit.code', e.exitCode);
    if (e.exitCode === 0 && sawOK) {
      console.log('RESULT: PASS');
      process.exit(0);
    } else {
      console.log('RESULT: FAIL');
      process.exit(1);
    }
  });

  // Safety timeout
  setTimeout(() => {
    console.error('Timeout: no exit');
    try { term.kill(); } catch {}
    process.exit(2);
  }, 10000);
})();