const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const pty = require('node-pty');

let win;

// ---- Session store -----------------------------------------------------------
const sessions = new Map(); // id -> {pty, cwd}
const genId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;

function createWindow() {
  win = new BrowserWindow({
    width: 1140,
    height: 740,
    backgroundColor: '#0b0f14',
    title: 'Warp_Open — Terminal',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      sandbox: false, // Keep false for xterm loading (black screen fix)
      nodeIntegration: false,
      spellcheck: false
    }
  });
  win.loadFile(path.join(__dirname, 'index.html'));
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// ---- PTY lifecycle per tab ---------------------------------------------------
function spawnPTY({ cols = 120, rows = 32, cwd, envExtra } = {}) {
  const id = genId();
  const shellPath = process.env.SHELL || '/bin/zsh';
  const env = Object.assign({}, process.env, {
    TERM: 'xterm-256color',
    COLORTERM: 'truecolor'
  }, envExtra || {});
  
  const term = pty.spawn(shellPath, ['-l'], {
    name: 'xterm-256color',
    cols, rows,
    cwd: cwd || process.env.HOME,
    env
  });
  
  sessions.set(id, { pty: term, cwd: cwd || process.env.HOME });

  term.onData(data => {
    if (win && !win.isDestroyed()) {
      win.webContents.send('pty:data', { id, data });
    }
  });
  
  term.onExit(e => {
    sessions.delete(id);
    if (win && !win.isDestroyed()) {
      win.webContents.send('pty:exit', { id, exitCode: e?.exitCode, signal: e?.signal });
    }
  });
  
  return id;
}

// IPC handlers
ipcMain.handle('pty:start', (_e, opts = {}) => {
  const id = spawnPTY(opts);
  return { ok: true, id };
});

ipcMain.on('pty:input', (_e, { id, data }) => {
  const s = sessions.get(id);
  if (s) s.pty.write(data);
});

ipcMain.on('pty:resize', (_e, { id, cols, rows }) => {
  const s = sessions.get(id);
  if (s && cols && rows) s.pty.resize(cols, rows);
});

ipcMain.on('pty:kill', (_e, { id }) => {
  const s = sessions.get(id);
  if (s) {
    try { s.pty.kill(); } catch {}
    sessions.delete(id);
  }
});

ipcMain.on('open:external', (_e, href) => {
  if (typeof href === 'string' && /^https?:\/\//.test(href)) {
    shell.openExternal(href);
  }
});

// WARP_OPEN_INTERACTIVE_MARKER
try {
  const { maybeRunInteractive } = require("./interactive_smoke");
  if (maybeRunInteractive(require("electron").app)) {
    module.exports = {}; return;
  }
} catch (e) { /* interactive smoke not fatal */ }
// WARP_OPEN_INTERACTIVE_MARKER
// ---------- Smoke hook (runs headless and exits) ----------
function nowIso(){ return new Date().toISOString(); }
function writeJsonl(file, obj){ fs.appendFileSync(file, JSON.stringify(obj) + '\n'); }

function maybeRunSmoke(appRef) {
  if (!process.env.WARP_OPEN_ENABLE_SMOKE) return false;
  const sessionId = `${Date.now()}-${Math.floor(Math.random()*1e6)}`;
  const logFile = path.join(require('os').homedir(), '.warp_open', 'sessions', `session-${sessionId}.jsonl`);
  const timeoutMs = parseInt(process.env.WARP_OPEN_SMOKE_TIMEOUT_MS || '120000', 10);

  writeJsonl(logFile, { t: nowIso(), type: 'smoke:start', sessionId, timeoutMs, shell: process.env.SHELL || '/bin/zsh' });

  const env = { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor', ZDOTDIR: fs.mkdtempSync(path.join(require('os').tmpdir(), 'zdot-')) };
  const term = pty.spawn(process.env.SHELL || '/bin/zsh', ['-il'], {
    name: 'xterm-256color', cols: 100, rows: 28, cwd: process.env.HOME, env
  });

  writeJsonl(logFile, { t: nowIso(), type: 'pty:start', cols: 100, rows: 28, cwd: process.env.HOME });

  const send = (s) => { writeJsonl(logFile, { t: nowIso(), type: 'pty:input', data: s }); term.write(s); };
  term.onData(d => writeJsonl(logFile, { t: nowIso(), type: 'pty:data', data: d }));
  term.onExit(e => writeJsonl(logFile, { t: nowIso(), type: 'pty:exit', code: e.exitCode, signal: e.signal }));

  (async () => {
    const delay = (ms) => new Promise(r => setTimeout(r, ms));
    await delay(250);
    send('echo "[smoke] hello from warp_open headless"\r');
    await delay(150);
    // OSC8 hyperlink
    send('printf "\\e]8;;https://example.com\\e\\\\link\\e]8;;\\e\\\\"; echo\r');
    await delay(150);
    send('uname -a\r');
    await delay(150);
    send('sleep 0.2\r');
    await delay(250);
    send('exit\r');
  })().catch(()=>{});

  const killTimer = setTimeout(() => {
    writeJsonl(logFile, { t: nowIso(), type: 'smoke:timeout' });
    try { term.kill(); } catch {}
    setTimeout(() => appRef.quit(), 150);
  }, timeoutMs);

  term.onExit(() => {
    clearTimeout(killTimer);
    writeJsonl(logFile, { t: nowIso(), type: 'smoke:done', logFile });
    setTimeout(() => appRef.quit(), 150);
  });

  return true;
}


// ---------- Regular GUI path ----------
let win;
function createWindow() {
  const sessionId = `${Date.now()}-${Math.floor(Math.random()*1e6)}`;
  const logFile = path.join(require('os').homedir(), '.warp_open', 'sessions', `session-${sessionId}.jsonl`);
  writeJsonl(logFile, { t: nowIso(), type: 'session:start', sessionId });

  win = new BrowserWindow({
    width: 1180, height: 760, backgroundColor: '#0b0f14', title: 'Warp_Open',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: false, spellcheck: false }
  });
  win.loadFile(path.join(__dirname, 'index.html'));

  const env = { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' };
  const term = pty.spawn(process.env.SHELL || '/bin/zsh', ['-il'], {
    name: 'xterm-256color', cols: 120, rows: 34, cwd: process.env.HOME, env
  });
  
  // Only create BlockTracker if blocks are enabled
  const blocksEnabled = process.env.WARP_OPEN_ENABLE_BLOCKS === '1';
  const blocks = blocksEnabled ? new BlockTracker({ sessionId, writeJsonl: (obj) => writeJsonl(logFile, obj) }) : null;
  
  // Store references for Blocks UI
  global.__warpOpenBlocksStore.activePty = term;
  global.__warpOpenBlocksStore.activeCwd = process.env.HOME;
  
  // Hook into BlockTracker to populate global store (only if blocks enabled)
  if (blocks) {
    const originalWrite = blocks.write;
    blocks.write = function(obj) {
      originalWrite.call(this, obj);
      if (obj.type === 'block:start') {
        global.__warpOpenBlocksStore.list.push({
          id: obj.id,
          cmd: obj.cmd,
          cwd: obj.cwd,
          exit: null,
          startedAt: new Date(obj.t).getTime(),
          endedAt: null
        });
      } else if (obj.type === 'block:exec:end' || obj.type === 'block:end') {
        const block = global.__warpOpenBlocksStore.list.find(b => b.id === obj.id);
        if (block) {
          block.exit = obj.exit;
          block.endedAt = new Date(obj.t).getTime();
        }
      }
    };
  }
  
  // OSC decoder for precise command boundaries and CWD tracking
  const oscDecoder = createOscDecoder({
    onOsc133: (mark) => blocks && blocks.osc133(mark),
    onOsc7: (cwd) => {
      blocks && blocks.onCwd(cwd);
      global.__warpOpenBlocksStore.activeCwd = cwd;
    }
  });

  term.onData(d => {
    writeJsonl(logFile, { t: nowIso(), type: 'pty:data', data: d });
    // Feed OSC decoder for command boundary detection
    try { oscDecoder.feed(d); } catch(e) {}
    win.webContents.send('pty:data', d);
  });
  term.onExit(e => {
    writeJsonl(logFile, { t: nowIso(), type: 'pty:exit', code: e.exitCode, signal: e.signal });
    // Force close any active block on exit
    if (blocks && blocks.active) {
      blocks.write({ t: blocks.now(), type: 'block:end', id: blocks.active.id, exit: e.exitCode ?? 0, forced: true });
      blocks.active = null;
    }
    win && win.webContents.send('pty:exit', e);
  });

  ipcMain.handle('pty:start', () => {
    writeJsonl(logFile, { t: nowIso(), type: 'pty:start', cols: 120, rows: 34, cwd: process.env.HOME });
    return { ok: true };
  });
  ipcMain.on('pty:input', (_e, data) => {
    writeJsonl(logFile, { t: nowIso(), type: 'pty:input', data });
    // Simple boundary detection: on Enter, snapshot the current line (best-effort).
    if (typeof data === 'string' && /\r|\n/.test(data)) {
      // Ask renderer for the input line (it tracks keystrokes).
      win.webContents.send('blocks:request-line');
    }
    term.write(data);
  });
  ipcMain.on('pty:resize', (_e, { cols, rows }) => {
    if (cols && rows) term.resize(cols, rows);
    writeJsonl(logFile, { t: nowIso(), type: 'pty:resize', cols, rows });
  });

  // Renderer replies with the committed command line on Enter (fallback heuristic)
  ipcMain.on('blocks:line-commit', (_e, { line, cwd }) => {
    if (blocks) {
      blocks.onEnterHeuristic(line || '');
      if (cwd && cwd !== blocks.cwd) {
        blocks.onCwd(cwd);
      }
    }
  });
  ipcMain.on('blocks:line-exit', (_e, { exitCode }) => {
    // For heuristic mode, force close the block
    if (blocks && blocks.active) {
      blocks.write({ t: blocks.now(), type: 'block:end', id: blocks.active.id, exit: exitCode ?? 0, heuristic: true });
      blocks.active = null;
    }
  });

  ipcMain.on('open:external', (_e, href) => {
    if (typeof href === 'string' && href.startsWith('http')) shell.openExternal(href);
  });

  win.on('closed', () => { writeJsonl(logFile, { t: nowIso(), type: 'session:end', sessionId }); });
  
  // === Interactive smoke automation ===
  if (global.__WARP_OPEN_INTERACTIVE_MODE) {
    writeJsonl(logFile, { t: nowIso(), type: 'interactive:start', sessionId });
    
    const delay = (ms) => new Promise(r => setTimeout(r, ms));
    const sendCommand = (cmd) => {
      writeJsonl(logFile, { t: nowIso(), type: 'pty:input', data: cmd + '\r' });
      term.write(cmd + '\r');
    };
    
    // Run automated commands after a short delay
    setTimeout(async () => {
      try {
        await delay(300);
        sendCommand('pwd');
        await delay(400);
        sendCommand('echo "hello blocks"');
        await delay(400);
        sendCommand('sleep 0.2 && uname -a');
        await delay(600);
        writeJsonl(logFile, { t: nowIso(), type: 'interactive:done', sessionId });
        // Auto-quit after commands complete
        setTimeout(() => app.quit(), 500);
      } catch (e) {
        console.error('Interactive automation failed:', e);
        app.quit();
      }
    }, 500);
  }
}

app.whenReady().then(() => {
  if (maybeRunSmoke(app)) return; // headless run already handled
  createWindow();
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// === Blocks UI v1.5 IPC wiring ===
try {
  const { wireBlocksIpc } = require('./blocks_ipc');
  // Expect these three accessors to exist in your main (or polyfill here):
  // 1) getBlocksSnapshot(): [{id,cmd,cwd,exit,startedAt,endedAt,output?:string[]}, ...]
  // 2) writeToActivePty(text, {inNewTab?:boolean})
  // 3) getActiveCwd(): string | undefined
  // If your main already has a BlockTracker, adapt the accessors below:

  const _global = globalThis;
  if (!_global.__warpOpenBlocksStore) _global.__warpOpenBlocksStore = { list: [], activePty: null };

  // Real accessors connected to BlockTracker:
  function getBlocksSnapshot(){ 
    return Array.isArray(_global.__warpOpenBlocksStore.list) ? _global.__warpOpenBlocksStore.list : []; 
  }
  function writeToActivePty(text, options={}){ 
    if (_global.__warpOpenBlocksStore.activePty) {
      _global.__warpOpenBlocksStore.activePty.write(text);
    }
  }
  function getActiveCwd(){ 
    return _global.__warpOpenBlocksStore.activeCwd || process.env.HOME; 
  }

  wireBlocksIpc({ getBlocksSnapshot, writeToActivePty, getActiveCwd });
} catch(e) {
  // non-fatal
}
