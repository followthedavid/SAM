let __REPLAY_WIRED=false; try { const { wireReplayIpc } = require("./replay_ipc"); wireReplayIpc(); __REPLAY_WIRED=true; } catch{}
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const pty = require('node-pty');
const { createOscDecoder } = require('./osc');
const { BlockTracker } = require('./blocks');

// === PHASE4: Wire ai2-main module ===
try {
  const initAi2Main = require('./ai2-main');
  app.whenReady().then(() => {
    initAi2Main(app, ipcMain, { projectRoot: path.resolve(__dirname, '..') });
    console.log('[main] Phase 4 ai2 API initialized');
  });
} catch (e) {
  console.error('[main] Phase 4 ai2-main init failed:', e);
}

// === PHASE5: Wire PTY manager for multi-session terminals ===
try {
  const ptyManager = require('./terminal/ptyManager');
  app.whenReady().then(() => {
    ptyManager.init(app, ipcMain);
    console.log('[main] Phase 5 V2 PTY manager initialized');
  });
} catch (e) {
  console.error('[main] Phase 5 PTY manager init failed:', e);
}

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
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, spellcheck: false }
  });
  win.loadFile(path.join(__dirname, 'index.html'));

  const env = { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' };
  const term = pty.spawn(process.env.SHELL || '/bin/zsh', ['-il'], {
    name: 'xterm-256color', cols: 120, rows: 34, cwd: process.env.HOME, env
  });
  const blocks = new BlockTracker({ sessionId, writeJsonl: (obj) => writeJsonl(logFile, obj) });
  
  // Store references for Blocks UI
  global.__warpOpenBlocksStore.activePty = term;
  global.__warpOpenBlocksStore.activeCwd = process.env.HOME;
  
  // Hook into BlockTracker to populate global store
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
  
  // OSC decoder for precise command boundaries and CWD tracking
  const oscDecoder = createOscDecoder({
    onOsc133: (mark) => blocks.osc133(mark),
    onOsc7: (cwd) => {
      blocks.onCwd(cwd);
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
    if (blocks.active) {
      blocks.write({ t: blocks.now(), type: 'block:end', id: blocks.active.id, exit: e.exitCode ?? 0, forced: true });
      blocks.active = null;
    }
    win && win.webContents.send('pty:exit', e);
  });

  // Multi-session PTY management
  const sessions = new Map(); // sessionId -> { term, sessionId }
  
  ipcMain.handle('pty:spawn', async (_e, { sessionId, cols = 120, rows = 32, cwd }) => {
    if (sessions.has(sessionId)) {
      console.warn(`[main] session ${sessionId} already exists`);
      return { id: sessionId }; // Return existing session ID
    }
    
    const sessionTerm = pty.spawn(process.env.SHELL || '/bin/zsh', ['-il'], {
      name: 'xterm-256color', 
      cols, 
      rows, 
      cwd: cwd || process.env.HOME, 
      env: { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' }
    });
    
    sessions.set(sessionId, { term: sessionTerm, sessionId });
    writeJsonl(logFile, { t: nowIso(), type: 'pty:spawn', sessionId, cols, rows, cwd: cwd || process.env.HOME });
    
    sessionTerm.onData(d => {
      writeJsonl(logFile, { t: nowIso(), type: 'pty:data', sessionId, data: d });
      win.webContents.send('pty:data', { id: sessionId, data: d });
    });
    
    sessionTerm.onExit(e => {
      writeJsonl(logFile, { t: nowIso(), type: 'pty:exit', sessionId, code: e.exitCode, signal: e.signal });
      win.webContents.send('pty:exit', { id: sessionId, exitCode: e.exitCode });
      sessions.delete(sessionId);
    });
    
    return { id: sessionId }; // Return the session ID
  });
  
  ipcMain.on('pty:input', (_e, { sessionId, data }) => {
    const session = sessions.get(sessionId);
    if (!session) return;
    
    writeJsonl(logFile, { t: nowIso(), type: 'pty:input', sessionId, data });
    if (typeof data === 'string' && /\r|\n/.test(data)) {
      win.webContents.send('blocks:request-line');
    }
    session.term.write(data);
  });
  
  ipcMain.on('pty:resize', (_e, { sessionId, cols, rows }) => {
    const session = sessions.get(sessionId);
    if (!session || !cols || !rows) return;
    
    session.term.resize(cols, rows);
    writeJsonl(logFile, { t: nowIso(), type: 'pty:resize', sessionId, cols, rows });
  });
  
  ipcMain.on('pty:kill', (_e, { sessionId }) => {
    const session = sessions.get(sessionId);
    if (!session) return;
    
    try {
      session.term.kill();
    } catch (e) {
      console.error(`[main] failed to kill session ${sessionId}:`, e);
    }
    sessions.delete(sessionId);
    writeJsonl(logFile, { t: nowIso(), type: 'pty:kill', sessionId });
  });
  
  // Legacy single-session support for backwards compatibility
  ipcMain.handle('pty:start', () => {
    writeJsonl(logFile, { t: nowIso(), type: 'pty:start', cols: 120, rows: 34, cwd: process.env.HOME });
    return { ok: true };
  });
  
  // Add missing IPC handlers for preload compatibility
  ipcMain.on('pty:ensure', () => {
    // PTY is already created in createWindow(), nothing to do
    writeJsonl(logFile, { t: nowIso(), type: 'pty:ensure' });
  });
  
  ipcMain.handle('session:flush', async () => {
    try {
      // Force flush the current session log
      writeJsonl(logFile, { t: nowIso(), type: 'session:flush' });
      return { success: true };
    } catch (e) {
      return { success: false, error: e.message };
    }
  });
  
  ipcMain.handle('clipboard:write', async (_e, text) => {
    try {
      require('electron').clipboard.writeText(text || '');
      return { success: true };
    } catch (e) {
      return { success: false, error: e.message };
    }
  });
  
  ipcMain.handle('terminal:clear', async () => {
    try {
      // Send clear screen sequence to terminal
      term.write('\x1b[2J\x1b[H');
      return { success: true };
    } catch (e) {
      return { success: false, error: e.message };
    }
  });
  
  // Add session list handler
  ipcMain.handle('sessions:listLatest', async (_e, { limit = 50 } = {}) => {
    try {
      const sessionsDir = path.join(require('os').homedir(), '.warp_open', 'sessions');
      if (!fs.existsSync(sessionsDir)) return [];
      
      const files = fs.readdirSync(sessionsDir)
        .filter(f => f.startsWith('session-') && f.endsWith('.jsonl'))
        .map(f => {
          const fullPath = path.join(sessionsDir, f);
          const stat = fs.statSync(fullPath);
          return { file: f, path: fullPath, mtime: stat.mtime.getTime() };
        })
        .sort((a, b) => b.mtime - a.mtime)
        .slice(0, limit);
      
      return files.map(f => ({ name: f.file, path: f.path, lastModified: f.mtime }));
    } catch (e) {
      console.error('sessions:listLatest error:', e);
      return [];
    }
  });

  // --- AI bridge (OpenAI or Ollama fallback) ---
  let OpenAIClient = null;
  try { OpenAIClient = require('openai').OpenAI; } catch {}
  const fetch = (...a) => import('node-fetch').then(({default: f}) => f(...a));

  function mkId() { return Math.random().toString(36).slice(2); }

  // === AI_BRIDGE_V2_START ===
  const AI_MODEL = process.env.WARP_AI_OLLAMA_MODEL || 'deepseek-coder:6.7b';
  const AI_BASE  = process.env.WARP_OPEN_AI_BASE || 'http://localhost:11434/v1';
  const AI_KEY   = process.env.WARP_OPEN_AI_KEY || 'ollama';

  // Small helper: OpenAI-style chat call (non-streaming fallback for node-fetch)
  async function aiChat({messages, model = AI_MODEL, temperature = 0.1, max_tokens = 800}) {
    const r = await fetch(`${AI_BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'authorization': `Bearer ${AI_KEY}` },
      body: JSON.stringify({ model, messages, temperature, max_tokens, stream: false })
    });
    if (!r.ok) throw new Error(`AI HTTP ${r.status}`);
    const j = await r.json();
    const txt = j.choices?.[0]?.message?.content ?? '';
    return txt;
  }

  // Simple file tools (confirmations happen in renderer)
  ipcMain.handle('ai:writeFile', async (_e, { filePath, content }) => {
    await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
    await fs.promises.writeFile(filePath, content, 'utf8');
    return { ok: true };
  });

  ipcMain.handle('ai:patchFile', async (_e, { filePath, unifiedDiff }) => {
    // naive apply: if file doesn't exist, create; else append patch as a comment
    let existing = '';
    try { existing = await fs.promises.readFile(filePath, 'utf8'); } catch {}
    const patched = `${existing}\n/* --- AI PATCH --- */\n${unifiedDiff}\n`;
    await fs.promises.writeFile(filePath, patched, 'utf8');
    return { ok: true };
  });

  ipcMain.handle('ai:runCommand', async (_e, { cmd }) => {
    // Pipe to the active PTY if you expose one; as a safe default return the command.
    return { ok: true, echoed: cmd };
  });

  ipcMain.handle('ai:chat', async (_e, payload) => {
    const text = await aiChat(payload);
    return { text, model: payload.model || AI_MODEL };
  });
  // === AI_BRIDGE_V2_END ===

  // === AI TOOLS: unified diff apply & run script (safe) ===
  const os = require('os');
  const { spawn } = require('child_process');
  const { mkdtempSync, writeFileSync, rmSync } = require('fs');

  function execWithTimeout(cmd, args, opts, timeoutMs = 3000) {
    return new Promise((resolve) => {
      const proc = spawn(cmd, args, { stdio: 'pipe', ...opts });
      let stdout = '', stderr = '';
      let killed = false;
      
      const timer = setTimeout(() => {
        killed = true;
        proc.kill('SIGTERM');
        setTimeout(() => proc.kill('SIGKILL'), 500);
      }, timeoutMs);
      
      proc.stdout?.on('data', d => stdout += d);
      proc.stderr?.on('data', d => stderr += d);
      
      proc.on('close', (code) => {
        clearTimeout(timer);
        resolve({ 
          ok: !killed && code === 0, 
          status: code, 
          stdout, 
          stderr,
          timedOut: killed 
        });
      });
      
      proc.on('error', (err) => {
        clearTimeout(timer);
        resolve({ ok: false, status: -1, stdout, stderr: err.message, timedOut: false });
      });
    });
  }

  ipcMain.handle('ai:applyUnifiedDiff', async (_e, { diffText, cwd }) => {
    try {
      const tmp = mkdtempSync(path.join(os.tmpdir(), 'warp_ai_patch_'));
      const patchFile = path.join(tmp, 'change.diff');
      writeFileSync(patchFile, diffText, 'utf8');

      const baseOpts = { cwd: cwd || require('os').homedir() };

      // 1) Try git apply (dry-run first) with timeout
      let r = await execWithTimeout('git', ['apply', '--check', patchFile], baseOpts, 2000);
      if (r.timedOut) {
        rmSync(tmp, { recursive: true, force: true });
        return { ok: false, error: 'git apply timed out' };
      }
      
      if (!r.ok) {
        // 2) Try patch (dry-run) with timeout
        r = await execWithTimeout('patch', ['-p0', '--dry-run', '--silent'], { ...baseOpts, input: diffText }, 2000);
        if (r.timedOut || !r.ok) {
          rmSync(tmp, { recursive: true, force: true });
          return { ok: false, stage: 'dry-run', tool: 'git/patch', error: r.timedOut ? 'timed out' : (r.stderr || r.stdout || 'dry-run failed').slice(0, 4000) };
        }
        // Real apply with patch
        const r2 = await execWithTimeout('patch', ['-p0', '--silent'], { ...baseOpts, input: diffText }, 2000);
        rmSync(tmp, { recursive: true, force: true });
        return r2.ok ? { ok: true, tool: 'patch' } : { ok: false, stage: 'apply', tool: 'patch', error: (r2.timedOut ? 'timed out' : (r2.stderr || r2.stdout || '')).slice(0, 4000) };
      } else {
        // Real apply with git
        const r2 = await execWithTimeout('git', ['apply', patchFile], baseOpts, 2000);
        rmSync(tmp, { recursive: true, force: true });
        return r2.ok ? { ok: true, tool: 'git' } : { ok: false, stage: 'apply', tool: 'git', error: (r2.timedOut ? 'timed out' : (r2.stderr || r2.stdout || '')).slice(0, 4000) };
      }
    } catch (err) {
      return { ok: false, error: String(err).slice(0, 4000) };
    }
  });

  ipcMain.handle('ai:makeScript', async (_e, { scriptText, cwd }) => {
    try {
      const tmp = mkdtempSync(path.join(os.tmpdir(), 'warp_ai_run_'));
      const scriptPath = path.join(tmp, 'run.sh');
      const text = scriptText.endsWith('\n') ? scriptText : scriptText + '\n';
      writeFileSync(scriptPath, text, { mode: 0o700 });
      return { ok: true, scriptPath, cwd: cwd || require('os').homedir() };
    } catch (err) {
      return { ok: false, error: String(err).slice(0, 4000) };
    }
  });

  ipcMain.handle('ai:ask', async (_evt, { prompt, context }) => {
    const useOllama = !!process.env.WARP_AI_OLLAMA_MODEL && !process.env.OPENAI_API_KEY;
    try {
      if (useOllama) {
        // Ollama local inference via OpenAI-compatible endpoint
        const baseUrl = process.env.WARP_OPEN_AI_BASE || 'http://localhost:11434/v1';
        const body = {
          model: process.env.WARP_AI_OLLAMA_MODEL,
          messages: [{ role: 'user', content: context ? `${prompt}\n\nContext:\n${context}` : prompt }],
          stream: false
        };
        const r = await fetch(`${baseUrl}/chat/completions`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!r.ok) throw new Error(`ollama http ${r.status}`);
        const j = await r.json();
        return { ok: true, text: j.choices?.[0]?.message?.content || '' };
      }
      
      if (process.env.OPENAI_API_KEY && OpenAIClient) {
        const openai = new OpenAIClient({ apiKey: process.env.OPENAI_API_KEY });
        const sys = 'You are a concise coding assistant in a terminal. Reply in markdown. Prefer short, runnable answers.';
        const resp = await openai.chat.completions.create({
          model: process.env.WARP_OPENAI_MODEL || 'gpt-4o-mini',
          temperature: 0.2,
          messages: [
            { role: 'system', content: sys }, 
            { role: 'user', content: context ? `${prompt}\n\nContext:\n${context}` : prompt }
          ],
        });
        return { ok: true, text: resp.choices?.[0]?.message?.content || '' };
      }
      
      return { ok: false, error: 'No AI backend configured. Set WARP_AI_OLLAMA_MODEL or OPENAI_API_KEY.' };
    } catch (err) {
      return { ok: false, error: String(err?.message || err) };
    }
  });

  // Streaming AI (best UX). Renderer calls ai:askStream, we push ai:chunk.
  ipcMain.on('ai:askStream', async (evt, { id, prompt, context }) => {
    const web = evt.sender;
    const send = (type, payload) => web.send('ai:chunk', { id, type, ...payload });
    const useOllama = !!process.env.WARP_AI_OLLAMA_MODEL && !process.env.OPENAI_API_KEY;
    
    try {
      if (useOllama) {
        // For streaming, fall back to non-streaming for simplicity with node-fetch
        const baseUrl = process.env.WARP_OPEN_AI_BASE || 'http://localhost:11434/v1';
        const body = {
          model: process.env.WARP_AI_OLLAMA_MODEL,
          messages: [{ role: 'user', content: context ? `${prompt}\n\nContext:\n${context}` : prompt }],
          stream: false // Use non-streaming to avoid node-fetch issues
        };
        const r = await fetch(`${baseUrl}/chat/completions`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!r.ok) throw new Error(`ollama http ${r.status}`);
        
        send('start', {});
        const j = await r.json();
        const text = j.choices?.[0]?.message?.content || '';
        if (text) send('delta', { text });
        send('done', {});
        return;
      }
      
      if (process.env.OPENAI_API_KEY && OpenAIClient) {
        const openai = new OpenAIClient({ apiKey: process.env.OPENAI_API_KEY });
        send('start', {});
        const stream = await openai.chat.completions.create({
          model: process.env.WARP_OPENAI_MODEL || 'gpt-4o-mini',
          temperature: 0.2,
          stream: true,
          messages: [
            { role: 'system', content: 'You are a concise coding assistant in a terminal. Reply in markdown. Prefer short, runnable answers.' },
            { role: 'user', content: context ? `${prompt}\n\nContext:\n${context}` : prompt }
          ],
        });
        for await (const part of stream) {
          const delta = part.choices?.[0]?.delta?.content;
          if (delta) send('delta', { text: delta });
        }
        send('done', {});
        return;
      }
      
      send('error', { error: 'No AI backend configured.' });
    } catch (err) {
      send('error', { error: String(err?.message || err) });
    }
  });

  // Renderer replies with the committed command line on Enter (fallback heuristic)
  ipcMain.on('blocks:line-commit', (_e, { line, cwd }) => {
    blocks.onEnterHeuristic(line || '');
    if (cwd && cwd !== blocks.cwd) {
      blocks.onCwd(cwd);
    }
  });
  ipcMain.on('blocks:line-exit', (_e, { exitCode }) => {
    // For heuristic mode, force close the block
    if (blocks.active) {
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

// === FILESYSTEM IPC HANDLERS START ===
const os = require('os');

// File system handlers
ipcMain.handle('fs:home', () => os.homedir());

ipcMain.handle('fs:writeText', async (_e, { path, text }) => {
  try {
    await fs.promises.mkdir(require('path').dirname(path), { recursive: true });
    await fs.promises.writeFile(path, text ?? '', 'utf8');
    return { ok: true };
  } catch (err) {
    throw new Error(`Failed to write file: ${err.message}`);
  }
});

ipcMain.handle('fs:readText', async (_e, { path }) => {
  try {
    const s = await fs.promises.readFile(path, 'utf8');
    return { ok: true, content: s };
  } catch (err) {
    throw new Error(`Failed to read file: ${err.message}`);
  }
});

ipcMain.handle('fs:chmod', async (_e, { path, mode }) => {
  try {
    await fs.promises.chmod(path, mode);
    return true;
  } catch (err) {
    throw new Error(`Failed to chmod: ${err.message}`);
  }
});

ipcMain.handle('fs:stat', async (_e, { path }) => {
  try {
    const st = await fs.promises.stat(path);
    return { isFile: st.isFile(), size: st.size };
  } catch {
    return null;
  }
});

// PTY and current working directory handlers
ipcMain.handle('pty:get-cwd', (_e) => {
  // Return the active tab's cwd or home as fallback
  return globalThis.__warpOpenBlocksStore?.activeCwd || global.__warpOpenBlocksStore?.activeCwd || os.homedir();
});

ipcMain.handle('pty:run-script', async (_e, { path }) => {
  try {
    // Send script execution to the active PTY
    const activePty = global.__warpOpenBlocksStore?.activePty;
    if (activePty) {
      const cmd = `bash "${path}"\r`;
      activePty.write(cmd);
      return true;
    }
    return false;
  } catch (err) {
    throw new Error(`Failed to run script: ${err.message}`);
  }
});
// === FILESYSTEM IPC HANDLERS END ===

// === CRASH_GUARD_START (idempotent) ===
(() => {
  try {
    const { app, BrowserWindow, ipcMain } = require('electron');
    const fs = require('fs');
    const path = require('path');

    // Safe JSONL writer
    function writeJsonlSafe(file, obj) {
      try {
        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.appendFileSync(file, JSON.stringify(obj) + '\n');
      } catch {}
    }

    // Locate latest session (best-effort)
    function latestSessionFile() {
      const dir = path.join(app.getPath('home'), '.warp_open', 'sessions');
      try {
        const files = fs.readdirSync(dir).filter(f => f.startsWith('session-') && f.endsWith('.jsonl'))
          .map(f => ({ f, t: fs.statSync(path.join(dir, f)).mtimeMs }))
          .sort((a,b) => b.t - a.t);
        return files.length ? path.join(dir, files[0].f) : null;
      } catch { return null; }
    }

    // Only add soft reload handler (session:flush already exists)
    if (!ipcMain.listenerCount('app:soft-reload')) {
      ipcMain.handle('app:soft-reload', async () => {
        const win = BrowserWindow.getFocusedWindow() || BrowserWindow.getAllWindows()[0];
        if (win) {
          win.webContents.reloadIgnoringCache();
          return true;
        }
        return false;
      });
    }

    // Broadcast crash toast to all windows
    function broadcastCrashToast(payload) {
      for (const w of BrowserWindow.getAllWindows()) {
        try { w.webContents.send('crash:toast', payload); } catch {}
      }
    }

    // Crash logger -> JSONL + toast + flush
    function logCrash(kind, err) {
      const f = latestSessionFile();
      const payload = {
        t: new Date().toISOString(),
        type: 'app:crash',
        kind,
        message: (err && err.message) || String(err),
        stack: (err && err.stack) || null,
      };
      if (f) writeJsonlSafe(f, payload);
      broadcastCrashToast({ title: 'Crash Detected', body: `${kind}: ${(payload.message||'')}`.slice(0,240) });
    }

    // Node-level guards
    if (!process.__warpopen_crash_guard_installed) {
      process.__warpopen_crash_guard_installed = true;
      process.on('uncaughtException', (e) => logCrash('uncaughtException', e));
      process.on('unhandledRejection', (e) => logCrash('unhandledRejection', e));
    }

    // Renderer crash guard: listen for renderer-process crashes
    app.on('render-process-gone', (_e, wc, details) => {
      logCrash(`render-process-gone(${details && details.reason})`, details);
    });
  } catch (e) {
    console.error('[main][crash-guard] init failed', e);
  }
})();
// === CRASH_GUARD_END ===

// === CWD_RESTORE_IPC_START ===
(() => {
  try {
    const { ipcMain } = require('electron');
    if (!ipcMain.listenerCount('term:new')) {
      ipcMain.handle('term:new', async (_e, opts = {}) => {
        const cwd = (typeof opts.cwd === 'string' && opts.cwd.length) ? opts.cwd : undefined;
        if (global.createTabWithOptions) return await global.createTabWithOptions({ cwd });
        if (global.createTab)           return await global.createTab({ cwd });
        return null;
      });
    }
  } catch {}
})();
// === CWD_RESTORE_IPC_END ===

// === DEV_MAIN_CRASH_SIM_START ===
(() => {
  try {
    const { ipcMain } = require('electron');
    if (!ipcMain.listenerCount('dev:simulate-main-crash')) {
      ipcMain.handle('dev:simulate-main-crash', () => {
        setTimeout(() => { throw new Error('Simulated main-process crash'); }, 10);
        return true;
      });
    }
  } catch (e) { /* noop */ }
})();
// === DEV_MAIN_CRASH_SIM_END ===
