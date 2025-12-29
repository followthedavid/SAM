const fs = require('fs');
const path = require('path');
const os = require('os');
const pty = require('node-pty');

function nowIso() { return new Date().toISOString(); }
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }
function ensureDir(p) { try { fs.mkdirSync(p, { recursive: true }); } catch {} }
function writeJsonl(file, obj){ try{ fs.appendFileSync(file, JSON.stringify(obj)+'\n','utf8'); }catch{} }

function makeCleanZdotdir(sessionId){
  const dir = path.join(os.tmpdir(), `warp_open_zdotdir_${sessionId}`);
  ensureDir(dir);
  // empty startup files so zsh is predictable and exits cleanly
  const files = ['.zshenv','.zprofile','.zshrc','.zlogin','.zlogout'];
  for (const f of files) {
    const p = path.join(dir, f);
    if (!fs.existsSync(p)) fs.writeFileSync(p, '', 'utf8');
  }
  return dir;
}

async function runSmokeOnce(app) {
  if (!process.env.WARP_OPEN_ENABLE_SMOKE) return false;

  const sessionId = `${Date.now()}-${Math.floor(Math.random()*1e6)}`;
  const outDir = path.join(os.homedir(), '.warp_open', 'sessions');
  ensureDir(outDir);
  const logFile = path.join(outDir, `session-${sessionId}.jsonl`);
  const timeoutMs = Number(process.env.WARP_OPEN_SMOKE_TIMEOUT_MS || 120000);
  const cols = 100, rows = 28;
  const cwd = os.homedir();
  const shellPath = process.env.SHELL || (process.platform === 'win32' ? 'pwsh.exe' : '/bin/zsh');

  const ZDOTDIR = makeCleanZdotdir(sessionId);

  writeJsonl(logFile, { t: nowIso(), type: 'smoke:start', sessionId, timeoutMs, shell: shellPath, zdotdir: ZDOTDIR });

  const env = {
    ...process.env,
    TERM: 'xterm-256color',
    COLORTERM: 'truecolor',
    LANG: 'en_US.UTF-8',
    LC_ALL: 'en_US.UTF-8',
    // Minimal prompt for predictability
    PS1: '$ ',
    // Make zsh load only the empty sandboxed rc files
    ZDOTDIR,
    // Avoid compinit prompts / slowdowns
    ZSH_DISABLE_COMPFIX: 'true',
    WARP_OPEN_SESSION: sessionId
  };

  const term = pty.spawn(shellPath, ['-il'], { name: 'xterm-256color', cols, rows, cwd, env });
  writeJsonl(logFile, { t: nowIso(), type: 'pty:start', cols, rows, cwd });

  let exited = false;
  term.onData(d => writeJsonl(logFile, { t: nowIso(), type: 'pty:data', data: d }));
  term.onExit(e => { exited = true; writeJsonl(logFile, { t: nowIso(), type: 'pty:exit', code: e.exitCode, signal: e.signal }); });

  // Give shell a moment to print prompt
  await delay(500);

  const send = s => { writeJsonl(logFile, { t: nowIso(), type: 'pty:input', data: s }); term.write(s); };

  // Exercise: greeting, OSC8 link, uname, sleep
  send('echo "[smoke] hello from warp_open headless"\r');
  await delay(100);
  send('printf "\\e]8;;https://example.com\\e\\\\link\\e]8;;\\e\\\\\\n"\r');
  await delay(100);
  send('uname -a\r');
  await delay(120);
  send('sleep 0.2\r');
  await delay(250);

  // Try graceful exit
  send('exit\r');

  // Fallback #1: if not exited soon, send EOT (Ctrl-D)
  const gracefulWindowMs = 1500;
  const begin = Date.now();
  while (!exited && Date.now() - begin < gracefulWindowMs) await delay(50);
  if (!exited) {
    // Ctrl-D
    send('\x04');
  }

  // Fallback #2: if still not exited, kill the PTY
  const killWindowMs = 1500;
  const begin2 = Date.now();
  while (!exited && Date.now() - begin2 < killWindowMs) await delay(50);
  if (!exited) {
    writeJsonl(logFile, { t: nowIso(), type: 'smoke:forced_exit' });
    try { term.kill(); } catch {}
  }

  // Safety timeout (paranoia)
  const killTimer = setTimeout(() => {
    writeJsonl(logFile, { t: nowIso(), type: 'smoke:timeout' });
    try { term.kill(); } catch {}
    setTimeout(() => app.quit(), 150);
  }, timeoutMs);

  // When PTY is done, finish app
  const finish = () => {
    clearTimeout(killTimer);
    writeJsonl(logFile, { t: nowIso(), type: 'smoke:done', logFile });
    setTimeout(() => app.quit(), 150);
  };

  if (exited) finish();
  else term.onExit(finish);

  return true;
}

function maybeRunSmoke(app) {
  try { return !!runSmokeOnce(app); } catch { return false; }
}

module.exports = { maybeRunSmoke };
