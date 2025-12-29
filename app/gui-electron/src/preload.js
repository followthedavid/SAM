/**
 * Minimal, safe preload.
 * - contextIsolation: true (required)
 * - nodeIntegration: false (renderer stays sandboxed)
 * - sandbox: false (preload can require)
 *
 * Exposes: window.bridge, window.session, window.blocks (no-ops if main lacks handlers)
 */
const { contextBridge, ipcRenderer } = require('electron');

function on(channel, cb) {
  // Safe wrapper so we never leak the event object
  const handler = (_evt, ...args) => { try { cb(...args); } catch (e) { console.error('[preload] on() cb error', e); } };
  ipcRenderer.on(channel, handler);
  return () => ipcRenderer.removeListener(channel, handler);
}

function once(channel, cb) {
  const handler = (_evt, ...args) => { try { cb(...args); } catch (e) { console.error('[preload] once() cb error', e); } };
  ipcRenderer.once(channel, handler);
}

// --- Terminal / PTY bridge ---
const bridge = {
  // Simple terminal factory placeholder - actual terminal creation happens in renderer
  createTerminal(container) {
    // Return a simple interface for the renderer to use
    return {
      _container: container,
      _needsInit: true,
      write: () => console.warn('[preload] terminal not initialized'),
      onData: () => console.warn('[preload] terminal not initialized'),
      fit: () => console.warn('[preload] terminal not initialized'),
      clear: () => console.warn('[preload] terminal not initialized'),
      dispose: () => console.warn('[preload] terminal not initialized')
    };
  },

  // PTY session management
  async startPTY({ cols = 120, rows = 32, cwd } = {}) {
    try {
      const sessionId = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
      const result = await ipcRenderer.invoke('pty:spawn', { sessionId, cols, rows, cwd });
      return result; // Should return { id: sessionId }
    } catch (e) {
      console.error('[preload] startPTY failed:', e);
      return null;
    }
  },

  // Send input to specific session
  sendInput(sessionId, data) { ipcRenderer.send('pty:input', { sessionId, data }); },
  
  // Resize PTY
  resizePTY(sessionId, cols, rows) { ipcRenderer.send('pty:resize', { sessionId, cols, rows }); },
  
  // Kill PTY session
  killPTY(sessionId) { ipcRenderer.send('pty:kill', { sessionId }); },

  // Main -> renderer subscriptions (multi-session aware)
  onPTYData(cb) { return on('pty:data', cb); },
  onPTYExit(cb) { return on('pty:exit', cb); },
  onStatus(cb)  { return on('app:status', cb); },

  // Utility functions
  copy(text) { return ipcRenderer.invoke('clipboard:write', text); },
  appendToTerminal(text) { /* for compatibility */ },
  blocksToggle() { /* for compatibility */ },

  // Legacy compatibility
  flushSession() { return ipcRenderer.invoke('session:flush').catch(e => console.error('[preload] flush failed', e)); },
  copySelection(text) { return this.copy(text); },
  clearScrollback() { return ipcRenderer.invoke('terminal:clear'); },
};

// --- Optional: sessions + blocks (graceful if main didn't wire handlers) ---
const session = {
  listLatest(limit = 50)    { return ipcRenderer.invoke('sessions:listLatest', { limit }).catch(() => []); },
};

const blocks = {
  listRecent(limit = 50)    { return ipcRenderer.invoke('blocks:list', { limit }).catch(() => []); },
  exportBlock(id)           { return ipcRenderer.invoke('blocks:export', { id }).catch(() => null); },
};

// --- AI bridge ---
const ai = {
  ask: (prompt, context = '') => ipcRenderer.invoke('ai:ask', { prompt, context }),
  askStream: (prompt, context = '', onDelta) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (_evt, msg) => {
      if (msg.id !== id) return;
      if (msg.type === 'delta' && onDelta) onDelta(msg.text || '');
      if (msg.type === 'error' && onDelta) onDelta(`\n[error] ${msg.error}\n`);
      if (msg.type === 'done') {
        ipcRenderer.removeListener('ai:chunk', handler);
      }
    };
    ipcRenderer.on('ai:chunk', handler);
    ipcRenderer.send('ai:askStream', { id, prompt, context });
  }
};

// === PRELOAD_AI_V2_START ===
const aiAPI = {
  chat: (payload) => ipcRenderer.invoke('ai:chat', payload),
  writeFile: (args) => ipcRenderer.invoke('ai:writeFile', args),
  patchFile: (args) => ipcRenderer.invoke('ai:patchFile', args),
  runCommand: (args) => ipcRenderer.invoke('ai:runCommand', args),
  applyUnifiedDiff: (diffText, cwd) => ipcRenderer.invoke('ai:applyUnifiedDiff', { diffText, cwd }),
  makeScript: (scriptText, cwd) => ipcRenderer.invoke('ai:makeScript', { scriptText, cwd }),
};
// === PRELOAD_AI_V2_END ===

// === PHASE4_AI2_START ===
// New modular ai2 API
const ai2New = {
  // cwd
  cd: (target) => ipcRenderer.invoke('ai2:cd', target),
  getCwd: () => ipcRenderer.invoke('ai2:getCwd'),

  // file ops
  readFile: (filePath, opts) => ipcRenderer.invoke('ai2:readFile', filePath, opts),
  writeFile: (filePath, content, opts) => ipcRenderer.invoke('ai2:writeFile', filePath, content, opts),
  applyUnifiedDiff: (filePath, diff, opts) => ipcRenderer.invoke('ai2:applyUnifiedDiff', filePath, diff, opts),

  // run scripts
  runScript: (command, args, opts) => ipcRenderer.invoke('ai2:runScript', command, args || [], opts || {}),

  // journal
  getJournal: (opts) => ipcRenderer.invoke('ai2:getJournal', opts || {}),
  undoLast: () => ipcRenderer.invoke('ai2:undoLast'),

  // context pack
  getContextPack: () => ipcRenderer.invoke('ai2:getContextPack')
};
// === PHASE4_AI2_END ===

// === PHASE5_PTYBRIDGE_START ===
// Phase 5 V2 PTY Bridge for multi-session terminal management
const ptyBridge = {
  // Create new PTY session
  create: (opts) => ipcRenderer.invoke('pty:create', opts),
  
  // Write data to PTY session
  write: (id, data) => ipcRenderer.send('pty:write', { id, data }),
  
  // Resize PTY session
  resize: (id, cols, rows) => ipcRenderer.send('pty:resize', { id, cols, rows }),
  
  // Kill PTY session
  kill: (opts) => ipcRenderer.invoke('pty:kill', opts),
  
  // List sessions
  list: () => ipcRenderer.invoke('pty:list'),
  
  // Event listeners with unsubscribe capability
  onData: (callback) => {
    const handler = (_evt, payload) => callback(payload);
    ipcRenderer.on('pty:data', handler);
    return () => ipcRenderer.removeListener('pty:data', handler);
  },
  
  onExit: (callback) => {
    const handler = (_evt, payload) => callback(payload);
    ipcRenderer.on('pty:exit', handler);
    return () => ipcRenderer.removeListener('pty:exit', handler);
  },
  
  onTitle: (callback) => {
    const handler = (_evt, payload) => callback(payload);
    ipcRenderer.on('pty:title', handler);
    return () => ipcRenderer.removeListener('pty:title', handler);
  }
};
// === PHASE5_PTYBRIDGE_END ===

// Expose to the renderer
try {
  const safeGet = (obj, fn, fallback='') => { try { return fn(obj); } catch { return fallback; } };
  contextBridge.exposeInMainWorld('bridge', {
    ...bridge,
    getCwd: () => ipcRenderer.invoke('pty:get-cwd'),
    getScrollback: (n=200) => safeGet(window, x => (x.__getScrollback?.(n) || '')),
    chmod: (path, mode) => ipcRenderer.invoke('fs:chmod', { path, mode }),
    runScript: (path) => ipcRenderer.invoke('pty:run-script', { path }),
  });
  contextBridge.exposeInMainWorld('files', {
    getHomeDir: () => ipcRenderer.invoke('fs:home'),
    writeTextFile: (path, text) => ipcRenderer.invoke('fs:writeText', { path, text }),
    readTextFile: (path) => ipcRenderer.invoke('fs:readText', { path }),
    stat: (path) => ipcRenderer.invoke('fs:stat', { path }),
  });
  contextBridge.exposeInMainWorld('session', session);
  contextBridge.exposeInMainWorld('blocksAPI', blocks);
  contextBridge.exposeInMainWorld('ai', ai);
  // Merge existing aiAPI with new ai2New (Phase 4 takes precedence)
  contextBridge.exposeInMainWorld('ai2', { ...aiAPI, ...ai2New });
  // Expose Phase 5 V2 ptyBridge
  contextBridge.exposeInMainWorld('ptyBridge', ptyBridge);
  console.log('[preload] loaded OK (Phase 4 ai2 API + Phase 5 ptyBridge added)');
} catch (e) {
  // Add a visible banner so failures are obvious
  console.error('[preload] expose failed', e);
  try {
    const banner = document.createElement('div');
    banner.textContent = 'Preload failed — check console';
    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:8px;background:#b00020;color:#fff;font:12px system-ui;z-index:999999';
    document.addEventListener('DOMContentLoaded', () => document.body.appendChild(banner));
  } catch {}
}
