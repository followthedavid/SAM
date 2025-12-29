console.log('[renderer] starting...');

// SAFE GUARDS — prevent hard crashes
window.bridge  = window.bridge  || {};
window.ai      = window.ai      || window.ai2 || { chat: async ()=>({text:'(ai unavailable)'}), writeFile: async()=>({}), patchFile: async()=>({}), runCommand: async()=>({}) };

// DOM elements
const tabsEl = document.getElementById('tabs');
const stageEl = document.getElementById('stage');
const copyBtn = document.getElementById('copy');
const clearBtn = document.getElementById('clear');
const blocksBtn = document.getElementById('blocks');
const blocksPanel = document.getElementById('blocksPanel');

// State
const terms = new Map(); // sessionId -> { term, fit, el }
const tabSessions = new Map(); // tabElement -> sessionId
let activeSessionId = null;

// Utility functions
function activeTabIndex() {
  const items = [...document.querySelectorAll('#tabs .tab')];
  return items.findIndex(el => el.classList.contains('active'));
}

// Create a terminal view for a session id
function createTerminalView(sessionId) {
  const wrap = document.createElement('div');
  wrap.className = 'termwrap';
  wrap.dataset.sessionId = sessionId;
  stageEl.appendChild(wrap);

  // Create terminal directly using xterm.js
  let term;
  if (window.Terminal && window.FitAddon) {
    term = new window.Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: { background: '#0b0f14', foreground: '#c7d2fe' }
    });
    const fitAddon = new window.FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(wrap);
    term.fit = () => fitAddon.fit();
  } else {
    console.error('[renderer] xterm.js not loaded properly');
    // Fallback to dummy terminal
    term = {
      write: (data) => console.log('[terminal]', data),
      onData: () => {},
      fit: () => {},
      clear: () => {},
      dispose: () => {}
    };
  }

  // Send keystrokes to the correct session with /ai command interception
  if (term.onData) {
    let inputBuffer = '';
    
    term.onData(async d => {
      // Track input for /ai command detection
      if (d === '\r' || d === '\n') {
        // Check for /ai command before sending to PTY
        if (await maybeHandleSlashAI(inputBuffer)) {
          inputBuffer = '';
          return; // Don't send /ai command to shell
        }
        inputBuffer = '';
      } else if (d === '\x7f' || d === '\b') {
        // Handle backspace
        inputBuffer = inputBuffer.slice(0, -1);
      } else if (d.charCodeAt(0) >= 32 && d.charCodeAt(0) <= 126) {
        // Only track printable ASCII characters
        inputBuffer += d;
      }
      
      // Send to PTY as normal
      window.bridge.sendInput(sessionId, d);
    });
  }

  // Store reference (term object already has fit method)
  terms.set(sessionId, { term, el: wrap });
  
  // Set up scrollback helper
  if (term.buffer) {
    window.__getScrollback = (n=200) => {
      try { 
        return term.buffer.active.getLine ? Array.from({length:Math.min(n, term.buffer.active.length)}, (_,i)=> {
          const line = term.buffer.active.getLine(term.buffer.active.length-1-i);
          return line?.translateToString() || '';
        }).reverse().join('\n') : ''; 
      } catch { return ''; }
    };
  }
  
  // Initialize cwd tracking
  window.__cwd = window.__cwd || '';
  
  // Welcome message
  if (term.write) {
    term.write(`\x1b[38;5;111m[${sessionId}] terminal ready\x1b[0m\r\n`);
  }
  
  return { term, el: wrap };
}

function activateSession(sessionId) {
  activeSessionId = sessionId;
  
  // Show active terminal
  for (const { el } of terms.values()) {
    el.classList.remove('active');
  }
  
  const obj = terms.get(sessionId);
  if (obj) {
    obj.el.classList.add('active');
    // Store global reference for /ai command
    window.__term = obj.term;
    
    // Refit after layout change
    setTimeout(() => {
      obj.term.fit();
      window.bridge.resizePTY(sessionId, obj.term.cols, obj.term.rows);
    }, 0);
  }
  
  // Update tab UI (works with new li-based tabs)
  document.querySelectorAll('#tabs .tab').forEach(li => {
    const sid = tabSessions.get(li);
    li.classList.toggle('active', sid === sessionId);
  });
}

// Create a new tab with enhanced functionality
function createTab(title = 'tab') {
  const newTabLi = document.createElement('li');
  newTabLi.className = 'tab';
  
  const titleEl = document.createElement('span');
  titleEl.className = 'title';
  titleEl.textContent = title;

  // Rename on double-click
  titleEl.addEventListener('dblclick', () => {
    titleEl.setAttribute('contenteditable', 'true');
    titleEl.focus();
    const sel = window.getSelection(); 
    const r = document.createRange();
    r.selectNodeContents(titleEl); 
    sel.removeAllRanges(); 
    sel.addRange(r);
  });
  
  // End rename on Enter / blur
  titleEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { 
      e.preventDefault(); 
      titleEl.blur(); 
    }
  });
  
  titleEl.addEventListener('blur', () => {
    titleEl.removeAttribute('contenteditable');
  });

  const closeBtn = document.createElement('button');
  closeBtn.className = 'close';
  closeBtn.textContent = '×';
  closeBtn.title = 'Close tab (⌘W)';

  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    closeTabElement(newTabLi);
  });

  newTabLi.appendChild(titleEl);
  newTabLi.appendChild(closeBtn);

  newTabLi.addEventListener('click', () => {
    setActiveTabElement(newTabLi);
  });

  // Insert before the [+ New] button
  const plus = document.getElementById('new-tab');
  tabsEl.insertBefore(newTabLi, plus);

  setActiveTabElement(newTabLi);
  return newTabLi;
}

function setActiveTabElement(li) {
  document.querySelectorAll('#tabs .tab').forEach(n => n.classList.remove('active'));
  li.classList.add('active');
  
  // Switch to the session for this tab
  const sessionId = tabSessions.get(li);
  if (sessionId) {
    activateSession(sessionId);
  }
}

function closeTabElement(li) {
  const tabs = [...document.querySelectorAll('#tabs .tab')];
  const idx = tabs.indexOf(li);
  const isActive = li.classList.contains('active');
  
  // Kill the PTY session
  const sessionId = tabSessions.get(li);
  if (sessionId) {
    const obj = terms.get(sessionId);
    if (obj) {
      try { obj.term.dispose(); } catch {}
      obj.el.remove();
    }
    terms.delete(sessionId);
    window.bridge.killPTY(sessionId);
  }
  
  tabSessions.delete(li);
  li.remove();
  
  // Select a neighbor so the UI stays usable
  if (isActive) {
    const neighbors = [...document.querySelectorAll('#tabs .tab')];
    const next = neighbors[idx] || neighbors[idx - 1];
    if (next) {
      setActiveTabElement(next);
    } else {
      activeSessionId = null;
    }
  }
}

// Create a new tab+session
async function newTab({ cwd } = {}) {
  const res = await window.bridge.startPTY({ cols: 120, rows: 32, cwd });
  const sessionId = res?.id;
  if (!sessionId) return;

  const dirName = cwd ? cwd.split('/').pop() || 'tab' : 'home';
  const tabElement = createTab(dirName);
  
  // Associate tab with session
  tabSessions.set(tabElement, sessionId);
  
  // Create terminal view
  createTerminalView(sessionId);
  activateSession(sessionId);
  
  return tabElement;
}

// Expose globally for testing
window.newTab = newTab;

// Wire the "+ New" button
document.getElementById('new-tab')?.addEventListener('click', (e) => {
  if (e.target.tagName === 'BUTTON') {
    newTab({});
  }
});

// Middle-click to close tab
tabsEl.addEventListener('auxclick', (ev) => {
  if (ev.button !== 1) return; // only middle-click
  const li = ev.target.closest('.tab');
  if (!li) return;
  
  closeTabElement(li);
});

// Button handlers
copyBtn.addEventListener('click', () => {
  if (!activeSessionId) return;
  const obj = terms.get(activeSessionId);
  const sel = obj?.term?.getSelection();
  if (sel) window.bridge.copy(sel);
});

clearBtn.addEventListener('click', () => {
  if (!activeSessionId) return;
  const obj = terms.get(activeSessionId);
  obj?.term?.clear();
});

blocksBtn.addEventListener('click', () => {
  const isVisible = blocksPanel.style.display === 'block';
  blocksPanel.style.display = isVisible ? 'none' : 'block';
  if (!isVisible) {
    blocksPanel.innerHTML = `
      <div style="text-align:center;color:var(--muted);margin-top:40px;">
        <div style="font-size:24px;">📋</div>
        <p>Blocks Panel</p>
        <p style="font-size:11px;">Command history will appear here<br/>when blocks are enabled</p>
      </div>
    `;
  }
});

// PTY data routing
window.bridge.onPTYData(({ id, data }) => {
  const obj = terms.get(id);
  if (obj) obj.term.write(data);
});

window.bridge.onPTYExit(({ id, exitCode }) => {
  const obj = terms.get(id);
  if (obj) {
    obj.term.write(`\r\n\x1b[31m[process exited ${exitCode ?? ''}]\x1b[0m\r\n`);
  }
});

// Layout resize -> refit active
window.addEventListener('resize', () => {
  if (!activeSessionId) return;
  const obj = terms.get(activeSessionId);
  if (obj) {
    obj.term.fit();
    window.bridge.resizePTY(activeSessionId, obj.term.cols, obj.term.rows);
  }
});

// Boot: create first tab
(async function boot() {
  try {
    console.log('[renderer] booting, bridge available:', !!window.bridge);
    console.log('[renderer] bridge.startPTY available:', !!window.bridge?.startPTY);
    
    // Wait a bit for bridge to be ready
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const result = await newTab({});
    console.log('[renderer] first tab created:', !!result);
    console.log('[renderer] boot complete');
    
    // Initialize AI dock after boot
    initAIDock();
  } catch (e) {
    console.error('[renderer] boot failed:', e);
    // Try to show error in UI
    document.body.insertAdjacentHTML('beforeend', `
      <div style="position:fixed;top:10px;left:10px;background:#b00020;color:#fff;padding:8px;border-radius:4px;z-index:9999">
        Boot failed: ${e.message}
      </div>
    `);
  }
})();

// Enhanced keyboard shortcuts
window.addEventListener('keydown', (e) => {
  const meta = e.metaKey || e.ctrlKey; // ⌘ on mac, Ctrl elsewhere
  
  // New tab: ⌘T
  if (meta && !e.shiftKey && e.key.toLowerCase() === 't') {
    e.preventDefault(); 
    newTab({}); 
    return;
  }
  
  // Close tab: ⌘W
  if (meta && !e.shiftKey && e.key.toLowerCase() === 'w') {
    e.preventDefault();
    const active = document.querySelector('#tabs .tab.active');
    if (active) closeTabElement(active);
    return;
  }
  
  // Switch tabs: ⌘1…⌘9
  if (meta && /^[1-9]$/.test(e.key)) {
    e.preventDefault();
    const n = parseInt(e.key, 10) - 1;
    const tabs = [...document.querySelectorAll('#tabs .tab')];
    if (tabs[n]) setActiveTabElement(tabs[n]);
    return;
  }
  
  // Toggle blocks panel: ⌘B
  if (meta && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    const isVisible = blocksPanel.style.display === 'block';
    blocksPanel.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
      blocksPanel.innerHTML = `
        <div style="text-align:center;color:var(--muted);margin-top:40px;">
          <div style="font-size:24px;">📋</div>
          <p>Blocks Panel</p>
          <p style="font-size:11px;">Command history will appear here<br/>when blocks are enabled</p>
        </div>
      `;
    }
  }
  
  // Toggle AI panel: ⌘I
  if (meta && e.key.toLowerCase() === 'i') {
    e.preventDefault();
    toggleAIPanel();
  }
});

// AI Panel functionality
function toggleAIPanel(show) {
  const el = document.getElementById('ai-panel');
  el.hidden = (show === undefined) ? !el.hidden : !show;
  if (!el.hidden) {
    document.getElementById('ai-input').focus();
    document.getElementById('ai-output').textContent = '';
  }
}

function sendAIFromPanel() {
  const q = document.getElementById('ai-input').value.trim();
  const out = document.getElementById('ai-output');
  if (!q) return;
  
  out.textContent = 'thinking…\n';
  // Stream for snappiness
  window.ai.askStream(q, '', delta => { 
    out.textContent += delta; 
    out.scrollTop = out.scrollHeight;
  });
}

// Wire AI panel buttons
document.getElementById('ai-send')?.addEventListener('click', sendAIFromPanel);
document.getElementById('ai-close')?.addEventListener('click', () => toggleAIPanel(false));

// Cmd+Enter in AI textarea
document.getElementById('ai-input')?.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { 
    e.preventDefault(); 
    sendAIFromPanel(); 
  }
});

// /ai command handler
let currentInputBuffer = '';

// Intercept /ai <question>
async function maybeHandleSlashAI(input) {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/ai ')) return false;
  
  const q = trimmed.slice(4);
  const context = ''; // Could grab selected text or cwd later
  
  // Find active terminal
  if (!activeSessionId) return true;
  const obj = terms.get(activeSessionId);
  if (!obj || !obj.term) return true;
  
  const term = obj.term;
  
  term.writeln('\x1b[36m[ai]\x1b[0m thinking…');
  
  try {
    // Use streaming for better UX
    window.ai.askStream(q, context, delta => {
      // Convert markdown/newlines to terminal output
      const lines = delta.split(/\r?\n/);
      for (const line of lines) {
        if (line || lines.length === 1) {
          term.write(line.replace(/\r/g, '') + '\r\n');
        }
      }
    });
  } catch (e) {
    term.writeln(`\x1b[31m[ai error]\x1b[0m ${e?.message || e}`);
  }
  
  return true;
}

// Hook into terminal input to track current line and handle /ai
function hookTerminalInput() {
  if (!activeSessionId) return;
  const obj = terms.get(activeSessionId);
  if (!obj || !obj.term) return;
  
  // This is a basic implementation - in a real terminal you'd track the input buffer properly
  // For now, we'll set up basic /ai command detection
  // (This could be enhanced to properly track shell input)
}

// Store reference to active term globally for /ai command
function updateGlobalTermRef() {
  if (activeSessionId) {
    const obj = terms.get(activeSessionId);
    window.__term = obj?.term;
  }
}

// --- SESSION_RESTORE_V1 ---
(function(){
  if (!window.newTab || !window.bridge || !window.bridge.sendInput) return;
  const KEY = 'warp_open:tabs:v1';

  function snapshot() {
    // expect a global terms map and per-tab cwd tracking; fall back to HOME
    try {
      const home = (window.files && window.files.getHomeDir) ? window.files.getHomeDir() : '';
      const tabs = [];
      // Assume each Terminal view has data-cwd attr (or derive via last-known cwd)
      document.querySelectorAll('.tab[data-kind="tab"]').forEach((btn) => {
        const sid = btn.getAttribute('data-session-id') || '';
        let cwd = '';
        try { cwd = btn.getAttribute('data-cwd') || ''; } catch {}
        if (!cwd) cwd = home || '~';
        tabs.push({ cwd });
      });
      localStorage.setItem(KEY, JSON.stringify({ tabs, ts: Date.now() }));
    } catch {}
  }

  function restore() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return false;
      const data = JSON.parse(raw);
      if (!data || !Array.isArray(data.tabs) || !data.tabs.length) return false;
      // Clear existing default tab if empty
      // Then recreate each tab
      let first = true;
      data.tabs.forEach(({cwd}) => {
        if (first) { window.newTab({ cwd }); first=false; }
        else window.newTab({ cwd });
      });
      return true;
    } catch { return false; }
  }

  // Try restore shortly after boot; if fails, do nothing (default tab stays)
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => { restore(); }, 250);
  });

  // Periodic + on-exit snapshot
  setInterval(snapshot, 5000);
  window.addEventListener('beforeunload', snapshot);
})();
 // --- SESSION_RESTORE_V1 ---

// === WARP_OPEN_SHORTCUTS_AND_STATE_MARKER ===
(function () {
  // Defensive guards: only add features if core hooks exist.
  const hasNewTab = typeof window.newTab === 'function';
  const hasCloseActive = typeof window.closeActiveTab === 'function';
  const KEY_ACTIVE = 'warp_open:lastActiveTabIndex';
  const KEY_TABS = 'warp_open:tabs:v1'; // from Session Restore v1

  function isMac() {
    return navigator.platform.toLowerCase().includes('mac');
  }
  function modKey(e) {
    return isMac() ? e.metaKey : e.ctrlKey;
  }

  // Find tab buttons; assumes you render them with .tab[data-kind="tab"]
  function allTabButtons() {
    return Array.from(document.querySelectorAll('.tab[data-kind="tab"]'));
  }
  function activeTabButton() {
    return document.querySelector('.tab[data-kind="tab"].active') || allTabButtons()[0] || null;
  }
  function indexOfActive() {
    const all = allTabButtons();
    const a = activeTabButton();
    return Math.max(0, all.indexOf(a));
  }

  // Persist last active tab index
  function saveLastActive() {
    try { localStorage.setItem(KEY_ACTIVE, String(indexOfActive())); } catch {}
  }
  function restoreLastActiveSoon() {
    // Delay a tick to let initial tabs render
    setTimeout(() => {
      try {
        const raw = localStorage.getItem(KEY_ACTIVE);
        if (!raw) return;
        const idx = Math.max(0, parseInt(raw, 10) || 0);
        const btn = allTabButtons()[idx];
        if (btn) btn.click();
      } catch {}
    }, 300);
  }

  // When user clicks any tab, remember it immediately
  function wireTabClicks() {
    document.addEventListener('click', (e) => {
      const el = e.target && (e.target.closest ? e.target.closest('.tab[data-kind="tab"]') : null);
      if (!el) return;
      // The app's own click handler should toggle .active; we just persist after a tiny delay
      setTimeout(saveLastActive, 50);
    });
  }

  // Keyboard shortcuts: Cmd/Ctrl+T (new tab), Cmd/Ctrl+W (close tab)
  function wireShortcuts() {
    window.addEventListener('keydown', (e) => {
      if (!modKey(e)) return;

      const k = (e.key || '').toLowerCase();
      if (k === 't' && hasNewTab) {
        e.preventDefault();
        // Try to reuse the active tab's cwd if available
        let cwd = '';
        const active = activeTabButton();
        if (active) cwd = active.getAttribute('data-cwd') || '';
        window.newTab({ cwd });
        // Give layout a moment, then mark the new tab active in storage
        setTimeout(saveLastActive, 100);
      }
      if (k === 'w' && hasCloseActive) {
        e.preventDefault();
        window.closeActiveTab();
        setTimeout(saveLastActive, 150);
      }
    });
  }

  // Track CWD on each tab:
  // If your preload/bridge emits cwd updates (e.g. OSC 7 parsed),
  // attach them here to keep data-cwd current on the active tab button.
  function wireCwdUpdates() {
    const bridge = window.bridge || {};
    const onCwd = bridge.onCwdUpdate || bridge.onCwd || null; // be flexible with names
    if (typeof onCwd !== 'function') return;

    onCwd(({ cwd, sessionId }) => {
      try {
        // Prefer matching by data-session-id if you render it; otherwise fall back to active tab.
        let btn = null;
        if (sessionId) {
          btn = document.querySelector(`.tab[data-kind="tab"][data-session-id="${CSS.escape(sessionId)}"]`);
        }
        btn = btn || activeTabButton();
        if (btn && cwd) {
          btn.setAttribute('data-cwd', cwd);
          // Also refresh Session Restore snapshot so it captures the latest cwd
          // (Session Restore v1 runs its own interval; this is just a safety poke)
          try {
            const snapRaw = localStorage.getItem(KEY_TABS);
            if (snapRaw) {
              const data = JSON.parse(snapRaw);
              const idx = indexOfActive();
              if (data && data.tabs && data.tabs[idx]) {
                data.tabs[idx].cwd = cwd;
                localStorage.setItem(KEY_TABS, JSON.stringify(data));
              }
            }
          } catch {}
        }
      } catch {}
    });
  }

  // Boot
  window.addEventListener('DOMContentLoaded', () => {
    wireTabClicks();
    wireShortcuts();
    wireCwdUpdates();
    restoreLastActiveSoon();
  });
})();
 // === WARP_OPEN_SHORTCUTS_AND_STATE_MARKER ===

// === WARP_OPEN_TABS_QOL_MARKER ===
(function () {
  const KEY_ACTIVE = 'warp_open:lastActiveTabIndex';
  const KEY_SCROLL = 'warp_open:scrollback:v1';          // { byTabKey: { key -> {lines: [...], cursor:number} } }
  const MAX_LINES = 2000;                                 // persisted lines per tab
  const CLOSED_STACK_KEY = 'warp_open:closedTabsStack';   // LIFO stack for reopen-closed
  const isMac = () => navigator.platform.toLowerCase().includes('mac');
  const modKey = (e) => isMac() ? e.metaKey : e.ctrlKey;

  // ---- helpers to address tabs in the DOM ----
  const tabSelector = '.tab[data-kind="tab"]';
  const allTabButtons = () => Array.from(document.querySelectorAll(tabSelector));
  const activeTabButton = () => document.querySelector(`${tabSelector}.active`) || allTabButtons()[0] || null;
  const indexOfActive = () => {
    const all = allTabButtons(); const a = activeTabButton();
    return Math.max(0, all.indexOf(a));
  };
  const tabKeyFor = (btn) => {
    // prefer a stable ID if present; else fall back to index
    if (!btn) return `idx:${indexOfActive()}`;
    const sid = btn.getAttribute('data-session-id');
    if (sid) return `sid:${sid}`;
    const idx = allTabButtons().indexOf(btn);
    return `idx:${idx >= 0 ? idx : 0}`;
  };

  // ---- persist last active tab index (already present from previous patch) ----
  function saveLastActive() { try { localStorage.setItem(KEY_ACTIVE, String(indexOfActive())); } catch {} }
  function restoreLastActiveSoon() {
    setTimeout(() => {
      try {
        const raw = localStorage.getItem(KEY_ACTIVE); if (!raw) return;
        const idx = Math.max(0, parseInt(raw, 10) || 0);
        const btn = allTabButtons()[idx]; if (btn) btn.click();
      } catch {}
    }, 250);
  }

  // ---- CLOSED TAB STACK (reopen with Cmd+Shift+T) ----
  function readClosedStack() {
    try { return JSON.parse(localStorage.getItem(CLOSED_STACK_KEY) || '[]') || []; } catch { return []; }
  }
  function writeClosedStack(arr) {
    try { localStorage.setItem(CLOSED_STACK_KEY, JSON.stringify(arr.slice(-20))); } catch {}
  }
  function pushClosedTab(info) {
    const st = readClosedStack(); st.push(info); writeClosedStack(st);
  }
  function popClosedTab() {
    const st = readClosedStack(); const v = st.pop(); writeClosedStack(st); return v;
  }

  // Wrap window.closeActiveTab (if present) to capture info before closing
  (function wrapCloseActive() {
    const orig = window.closeActiveTab;
    if (typeof orig !== 'function') return;
    window.closeActiveTab = function wrappedCloseActiveTab() {
      try {
        const btn = activeTabButton();
        if (btn) {
          pushClosedTab({
            title: btn.textContent?.trim() || 'Tab',
            cwd: btn.getAttribute('data-cwd') || '',
            // If you have a way to map tab -> shell args/env, add here:
            ts: Date.now()
          });
        }
      } catch {}
      return orig.apply(this, arguments);
    };
  })();

  // Reopen last closed: tries to create a tab with captured cwd/title
  window.reopenLastClosedTab = function () {
    const info = popClosedTab();
    if (!info) return;
    // Prefer your app's newTab API if available
    if (typeof window.newTab === 'function') {
      window.newTab({ cwd: info.cwd || '' });
      setTimeout(saveLastActive, 100);
    }
  };

  // ---- shortcuts (tabs jump/cycle/reopen) ----
  function wireMoreShortcuts() {
    window.addEventListener('keydown', (e) => {
      if (!modKey(e)) return;
      const k = (e.key || '').toLowerCase();

      // Cmd/Ctrl+Shift+T => reopen closed
      if (e.shiftKey && k === 't') {
        e.preventDefault();
        window.reopenLastClosedTab && window.reopenLastClosedTab();
        return;
      }

      // Cmd/Ctrl+Shift+[ / ] => prev/next tab
      if (e.shiftKey && (k === '[' || k === ']')) {
        e.preventDefault();
        const tabs = allTabButtons(); if (!tabs.length) return;
        const i = indexOfActive();
        const j = k === ']' ? (i + 1) % tabs.length : (i - 1 + tabs.length) % tabs.length;
        tabs[j].click(); setTimeout(saveLastActive, 50);
        return;
      }

      // Cmd/Ctrl+1..9 => select tab index (1-based)
      if (/^[1-9]$/.test(k)) {
        e.preventDefault();
        const idx = Math.min(8, parseInt(k, 10) - 1);
        const btn = allTabButtons()[idx]; if (btn) { btn.click(); setTimeout(saveLastActive, 50); }
      }
    });
  }

  // ---- SCROLLBACK persistence (per tab) ----
  // We'll capture output lines by listening to PTY data if your preload exposes it,
  // else (fallback) from xterm instance if your window.terminal provides hooks.
  const Scroll = {
    readAll() {
      try { return JSON.parse(localStorage.getItem(KEY_SCROLL) || '{"byTabKey":{}}'); }
      catch { return { byTabKey: {} }; }
    },
    writeAll(obj) {
      try { localStorage.setItem(KEY_SCROLL, JSON.stringify(obj)); } catch {}
    },
    snapshotFor(key) {
      const obj = this.readAll(); return obj.byTabKey[key] || { lines: [], cursor: 0 };
    },
    putFor(key, snap) {
      const obj = this.readAll();
      obj.byTabKey[key] = snap;
      this.writeAll(obj);
    },
    pushLine(key, line) {
      const snap = this.snapshotFor(key);
      snap.lines.push(line);
      if (snap.lines.length > MAX_LINES) snap.lines.splice(0, snap.lines.length - MAX_LINES);
      this.putFor(key, snap);
    }
  };

  // Buffer aggregator: join incoming chunks until newline
  const accumulators = new Map(); // key -> {buf:string}
  function appendDataForTab(btn, chunk) {
    const key = tabKeyFor(btn);
    const st = (accumulators.get(key) || { buf: '' });
    st.buf += chunk;
    // split on newlines and persist complete lines
    let idx;
    while ((idx = st.buf.indexOf('\n')) !== -1) {
      const line = st.buf.slice(0, idx + 1);
      Scroll.pushLine(key, line);
      st.buf = st.buf.slice(idx + 1);
    }
    accumulators.set(key, st);
  }

  // Restore scrollback to the active terminal when a tab becomes active
  function restoreScrollbackToActive() {
    const btn = activeTabButton(); if (!btn) return;
    const key = tabKeyFor(btn);
    const snap = Scroll.snapshotFor(key);
    // If your renderer exposes a write-to-active-terminal API:
    const writer = (window.writeToActiveTerminal || window.termWrite || ((s) => {
      // fallback to bridge if available
      if (window.bridge && typeof window.bridge.appendToTerminal === 'function') {
        window.bridge.appendToTerminal(s);
      } else {
        // last resort: no-op
      }
    }));
    if (snap.lines && snap.lines.length) {
      // throttle to avoid blocking UI
      const chunk = snap.lines.join('');
      try { writer(chunk); } catch {}
    }
  }

  // Wire PTY data → scrollback store (needs a data source)
  function wireScrollbackCapture() {
    // Preferred: bridge.onData(id,data) or bridge.onData(data)
    const b = window.bridge || {};
    if (typeof b.onData === 'function') {
      b.onData((payload) => {
        // payload may be string or {id,data}
        const data = (payload && typeof payload === 'object') ? payload.data : payload;
        const btn = activeTabButton(); // heuristic: store against active tab
        if (btn && typeof data === 'string' && data) appendDataForTab(btn, data);
      });
      return;
    }
    // Fallback: if an xterm instance is available globally
    if (window.terminal && typeof window.terminal.onData === 'function') {
      window.terminal.onData((d) => {
        const btn = activeTabButton();
        if (btn && typeof d === 'string' && d) appendDataForTab(btn, d);
      });
    }
  }

  // Restore scrollback when tabs change
  function wireTabActivationRestore() {
    document.addEventListener('click', (e) => {
      const el = e.target && (e.target.closest ? e.target.closest(tabSelector) : null);
      if (!el) return;
      // after your app switches terminals internally, repaint with restored content
      setTimeout(() => { restoreScrollbackToActive(); saveLastActive(); }, 120);
    });
  }

  // initial boot
  window.addEventListener('DOMContentLoaded', () => {
    wireMoreShortcuts();
    wireScrollbackCapture();
    wireTabActivationRestore();
    // First run restore (after initial terminal attach)
    setTimeout(restoreScrollbackToActive, 400);
    // Keep last-active up to date (if you didn't wire in earlier)
    document.addEventListener('click', (e) => {
      const el = e.target && (e.target.closest ? e.target.closest(tabSelector) : null);
      if (!el) return; setTimeout(saveLastActive, 50);
    });
    restoreLastActiveSoon();
  });
})();
 // === WARP_OPEN_TABS_QOL_MARKER ===

// ===================== Real tabs: receive "tabs:new" from main =====================
(function wireTabsNew(){
  try {
    if (!window.tabs || !window.tabs.onNew) return;
    window.tabs.onNew(async ({ initialCmd } = {}) => {
      // Create new tab and seed command if provided
      if (window.newTab) {
        await newTab({}); // Create new tab
        if (initialCmd && activeSessionId) {
          // Send command to active session
          window.bridge.sendInput(activeSessionId, initialCmd);
        }
      }
    });
  } catch(e) {
    console.log('[renderer] tabs.onNew setup failed:', e.message);
  }
})();

// Update palette to support new tab via Cmd+Enter
(function updatePaletteNewTab(){
  try {
    if (!window.palette) return;
    
    // Override the palette's runSelected to support Cmd+Enter
    const originalRunSelected = window.palette.runSelected;
    if (originalRunSelected) {
      window.palette.runSelected = function(newTab, cmdKey) {
        const arr = window.palette.state?.filtered?.length ? window.palette.state.filtered : window.palette.state?.items?.slice(0, 200) || [];
        const it = arr[window.palette.state?.sel || 0];
        if (!it) return;
        
        const base = (it.base_cwd || window.files?.getHomeDir() || '~');
        const cmd = it.command || '';
        const line = (base ? `cd ${JSON.stringify(base)} && ` : '') + cmd + '\r';

        if (cmdKey && window.tabs) {
          // Cmd+Enter: new tab
          window.tabs.new(line);
        } else if (newTab && window.newTab) {
          // Shift+Enter: new tab (existing behavior)
          window.newTab({ cwd: base });
          setTimeout(() => window.bridge.sendInput(activeSessionId, line), 60);
        } else {
          // Enter: current tab
          if (activeSessionId) window.bridge.sendInput(activeSessionId, line);
        }
        
        window.palette.toggle(false);
      };
    }
  } catch(e) {
    console.log('[renderer] palette update failed:', e.message);
  }
})();

// <<< FT_THEME_API_START >>>
(() => {
  const el = document.getElementById("btn-theme");
  const root = document.documentElement;
  const KEY = "warp_theme";
  function apply(t){ root.setAttribute("data-theme", t); localStorage.setItem(KEY,t); }
  function current(){ return root.getAttribute("data-theme") || localStorage.getItem(KEY) || "warp-dark"; }
  apply(current());
  if(el) el.onclick = () => apply(current()==="warp-dark"?"warp-light":"warp-dark");
  window.__theme = { apply, current };
})();
// <<< FT_THEME_API_END >>>

// <<< FT_SESSION_RESTORE_V2_START >>>
(() => {
  const KEY="warp_tabs_state_v2";
  function save(){ try{
    const tabs=[...document.querySelectorAll(".tab")].map(t=>({
      title:t.textContent||"Tab", id:t.getAttribute("data-id")||"", active:t.classList.contains("active")
    })); localStorage.setItem(KEY, JSON.stringify({tabs})); }catch{} }
  function load(){ try{ const s=localStorage.getItem(KEY); if(!s) return;
    const state=JSON.parse(s); if(!state||!Array.isArray(state.tabs)) return;
    if(typeof window.restoreTabsFromState==='function') window.restoreTabsFromState(state.tabs);
  }catch{} }
  window.addEventListener("beforeunload", save);
  setTimeout(load, 50);
  window.__tabsState={save,load};
})();
// <<< FT_SESSION_RESTORE_V2_END >>>

// <<< FT_REPLAY_ENH_START >>>
(() => {
  const listEl = document.getElementById("replay-list");
  const outEl  = document.getElementById("replay-output");
  const scrub  = document.getElementById("replay-scrub");
  const sval   = document.getElementById("replay-scrub-val");
  if(!listEl||!outEl) return;
  async function autoload(){
    try{
      const files = (window.sessions && window.sessions.listLatest)? window.sessions.listLatest(10):[];
      if(!files.length) return;
      // Populate list if empty
      if(!listEl.querySelector("li")){
        files.forEach((p,i)=>{ const li=document.createElement("li"); li.textContent=p;
          li.onclick=()=>window.loadSessionFile && window.loadSessionFile(p);
          listEl.appendChild(li); if(i===0) li.classList.add("active"); });
      }
      if(typeof window.loadSessionFile==='function') window.loadSessionFile(files[0]);
    }catch(e){ console.warn("replay autoload skip",e); }
  }
  function hookScrub(){ if(!scrub||!sval) return;
    scrub.addEventListener("input", ()=>{ sval.textContent = scrub.value+"%";
      if(typeof window.replayScrub==='function') window.replayScrub(parseInt(scrub.value,10));
    });
  }
  setTimeout(()=>{autoload(); hookScrub();}, 120);
})();
// <<< FT_REPLAY_ENH_END >>>

// <<< FT_THEME_SHORTCUT_START >>>
(() => {
  window.addEventListener("keydown", (e)=>{
    const isMac = navigator.platform.includes("Mac");
    const mod = isMac ? e.metaKey : e.ctrlKey;
    if(mod && e.shiftKey && (e.key.toLowerCase()==="t")){
      e.preventDefault(); if(window.__theme) window.__theme.apply(window.__theme.current()==="warp-dark"?"warp-light":"warp-dark");
    }
  }, {capture:true});
})();
// <<< FT_THEME_SHORTCUT_END >>>


// WARP_OPEN_DEMO_RENDERER
(function(){
  const byId = id => document.getElementById(id);
  const flushBtn = byId('flushBtn');
  if (flushBtn) {
    flushBtn.addEventListener('click', async () => {
      try {
        const res = await (window.session?.flush?.() || Promise.resolve({ok:false}));
        console.log('[session.flush]', res);
        // Optional toast
        try { const el = document.createElement('div');
              el.textContent = res?.ok ? 'Session flushed' : 'Flush attempted';
              el.style.cssText='position:fixed;top:10px;right:10px;background:#222;color:#fff;padding:6px 10px;border-radius:8px;opacity:.9;z-index:9999;font:12px/1.2 Menlo,monospace';
              document.body.appendChild(el); setTimeout(()=>el.remove(),1200);} catch {}
      } catch(e){ console.error(e); }
    });
  }

  // Mini block summary: Cmd+Opt+B (mac) / Ctrl+Alt+B (others)
  window.addEventListener('keydown', (e) => {
    const mac = navigator.platform.toLowerCase().includes('mac');
    const want = (mac && e.metaKey && e.altKey && (e.key==='b' || e.key==='B'))
              || (!mac && e.ctrlKey && e.altKey && (e.key==='b' || e.key==='B'));
    if (want) {
      e.preventDefault();
      if (window.blocksExtra?.summary) window.blocksExtra.summary();
      else if (window.blocks?.getBlocks) {
        window.blocks.getBlocks().then(list=>{
          const running = list.filter(b=>!b.endedAt).length;
          const done    = list.filter(b=>b.endedAt).length;
          const failed  = list.filter(b=>b.exitCode && b.exitCode!==0).length;
          console.log('[blocks] total=%d running=%d done=%d failed=%d',
            list.length, running, done, failed);
        }).catch(console.error);
      } else {
        console.warn('[blocks] summary unavailable');
      }
    }
  });
})();

// === CRASH_GUARD_START (idempotent) ===
(() => {
  const TOAST_ID = 'warpopen-toast';
  function ensureToastContainer() {
    if (document.getElementById(TOAST_ID)) return;
    const div = document.createElement('div');
    div.id = TOAST_ID;
    div.className = 'toast-crash hidden';
    div.innerHTML = `
      <div class="toast-title">Crash Detected</div>
      <div class="toast-body"></div>
      <div class="toast-actions">
        <button id="toast-flush">💾 Flush</button>
        <button id="toast-reload">↻ Reload</button>
        <button id="toast-dismiss">✖︎</button>
      </div>`;
    document.body.appendChild(div);
    document.getElementById('toast-flush').onclick = async () => { try { await window.session?.flush(); } catch {} };
    document.getElementById('toast-reload').onclick = async () => { try { await window.appctl?.softReload(); } catch {} };
    document.getElementById('toast-dismiss').onclick = () => div.classList.add('hidden');
  }

  function showCrashToast(msg) {
    ensureToastContainer();
    const div = document.getElementById(TOAST_ID);
    div.querySelector('.toast-body').textContent = msg || 'Unexpected error';
    div.classList.remove('hidden');
  }

  // Window-level guards → toast + flush + optional soft reload
  window.addEventListener('error', async (e) => {
    showCrashToast(e?.message || 'Renderer error');
    try { await window.session?.flush(); } catch {}
    // give the user control; no auto-reload here
  });

  window.addEventListener('unhandledrejection', async (e) => {
    const msg = (e && e.reason && (e.reason.message || String(e.reason))) || 'Unhandled rejection';
    showCrashToast(msg);
    try { await window.session?.flush(); } catch {}
  });

  // Listen for main->renderer crash toast
  window.addEventListener('warpopen-crash', (ev) => {
    const d = ev.detail || {};
    showCrashToast(`${d.title||'Crash'}: ${d.body||''}`);
  });

  // Developer hotkey to simulate crash: Cmd+Opt+X (Mac) / Ctrl+Alt+X (others)
  document.addEventListener('keydown', (ev) => {
    const mac = /Mac|iPhone|iPad/.test(navigator.platform);
    const modOK = mac ? (ev.metaKey && ev.altKey) : (ev.ctrlKey && ev.altKey);
    if (modOK && (ev.key === 'x' || ev.key === 'X')) {
      // Simulate crash
      setTimeout(() => { throw new Error('Simulated renderer crash'); }, 10);
      ev.preventDefault();
    }
  });
})();
// === CRASH_GUARD_END ===

// === CWD_RESTORE_V21_START ===
(() => {
  const LS_KEY = 'warp_open.restore.tabs.v21';
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);

  const loadState = () => { try { return JSON.parse(localStorage.getItem(LS_KEY)||'[]'); } catch { return []; } };
  const saveState = (arr) => { try { localStorage.setItem(LS_KEY, JSON.stringify(arr)); } catch {} };

  const cwdByTab = new Map();

  const getOpenTabs = () => (window.tabs?.list?.() || []);   // expected: [{id,title}]
  const getActiveTab = () => window.tabs?.active?.();
  const onTabsChanged = (fn) => window.tabs?.onChange?.(fn);

  const onCwdUpdate = (handler) => {
    if (window.blocks?.onCwdUpdate)        return window.blocks.onCwdUpdate(({tabId,cwd})=>handler(tabId,cwd));
    if (window.bridge?.onCwdUpdate)        return window.bridge.onCwdUpdate((tabId,cwd)=>handler(tabId,cwd));
    if (window.bus?.on)                    return window.bus.on('cwd:update',({tabId,cwd})=>handler(tabId,cwd));
  };

  onCwdUpdate?.((tabId, cwd) => { if (tabId!=null && cwd) cwdByTab.set(tabId, cwd); });

  const persistAll = () => {
    const tabs = getOpenTabs();
    const now = Date.now();
    const out = tabs.map(t => ({ id: t.id, title: t.title||'', cwd: cwdByTab.get(t.id)||null, ts: now }));
    saveState(out);
  };

  onTabsChanged?.(persistAll);
  window.addEventListener('beforeunload', persistAll);

  const newTabAtCwd = async (cwd) => {
    if (window.bridge?.newTabWithCwd) return window.bridge.newTabWithCwd({ cwd });
    let id;
    if (window.tabs?.new) id = await window.tabs.new();
    else if (window.bridge?.newTab) id = await window.bridge.newTab();
    if (id && window.bridge?.sendInputToTab) {
      const esc = cwd.replace(/(["\\\s$`])/g,'\\$1');
      window.bridge.sendInputToTab(id, `cd "${esc}"\r`);
    }
    return id;
  };

  const restoreTabs = async () => {
    const saved = loadState();
    if (!Array.isArray(saved) || saved.length===0) return;
    const existing = getOpenTabs();
    let reused = false;

    for (const item of saved) {
      if (!item?.cwd) continue;
      if (!reused && existing.length===1) {
        const active = getActiveTab?.();
        if (active && window.bridge?.sendInputToTab) {
          const esc = item.cwd.replace(/(["\\\s$`])/g,'\\$1');
          window.bridge.sendInputToTab(active.id, `cd "${esc}"\r`);
          reused = true;
          continue;
        }
      }
      await newTabAtCwd(item.cwd);
    }
  };

  // Panic save: Cmd+Opt+S (mac) / Ctrl+Alt+S (others)
  document.addEventListener('keydown', async (e) => {
    const mod = isMac ? (e.metaKey && e.altKey) : (e.ctrlKey && e.altKey);
    if (mod && (e.key==='s' || e.key==='S')) {
      e.preventDefault();
      persistAll();
      try { await window.session?.flush?.(); } catch {}
      console.log('[cwd-restore] persisted & flushed');
    }
  });

  window.addEventListener('DOMContentLoaded', () => setTimeout(()=>restoreTabs().catch(()=>{}), 120));

  window.cwdr = { save: persistAll, load: () => loadState(), last: () => loadState().map(x=>({id:x.id,cwd:x.cwd})) };
})();
// === CWD_RESTORE_V21_END ===

// === SCROLLBACK_SNAPSHOT_START ===
// Per-tab scrollback snapshot (last ~2000 "lines" of output chunks)
// Safe: operates only in renderer localStorage, not JSONL session writer.
(() => {
  const KEY = 'warp_open.scrollback.v1';
  const { debounceJson } = (() => {
    function debounce(fn, wait=250) { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); }; } return { debounceJson: debounce };
  })();

  const readAll = () => {
    try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; }
  };
  const writeAll = (obj) => { try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch {} };

  const saveBuffered = debounceJson(() => {
    // noop wrapper to coalesce writes; actual write happens in save() directly
  });

  const save = (id, arr) => {
    const all = readAll();
    all[id] = arr.slice(-2000);
    writeAll(all);
    saveBuffered(); // coalesce
  };
  const load = (id) => {
    const all = readAll();
    return all[id] || [];
  };

  // Attach to global term write if available later.
  const hookWrite = () => {
    const t = (window.term || globalThis.term);
    if (!t || t.__scrollbackHooked) return;
    t.__scrollbackHooked = true;
    const orig = t.write.bind(t);
    t.write = (data) => {
      try {
        const id = (window.tabs && window.tabs.active && window.tabs.active().id) || 'main';
        const existing = load(id);
        existing.push(data);
        save(id, existing);
      } catch {}
      orig(data);
    };
  };

  // Try immediately and again after a tick (in case term initializes later)
  try { hookWrite(); } catch {}
  setTimeout(hookWrite, 300);

  // Restore when tab is (re)activated (if your tabs expose onActivate)
  const restoreScrollback = (id) => {
    const lines = load(id);
    const t = (window.term || globalThis.term);
    if (t && lines.length) t.write(lines.join(''));
  };
  if (window.tabs && typeof window.tabs.onActivate === 'function') {
    window.tabs.onActivate(restoreScrollback);
  } else {
    // fallback: restore once for 'main' shortly after boot
    setTimeout(() => restoreScrollback('main'), 500);
  }
})();
// === SCROLLBACK_SNAPSHOT_END ===

// ---------- Smart intent + content extraction ----------
function sanitizeFilename(name) {
  const base = String(name || '').split('/').pop().split('\\').pop();
  const cleaned = base.replace(/[^\p{L}\p{N}._+\- ]/gu, '').trim();
  return cleaned && !/^\.+$/.test(cleaned) ? cleaned : '';
}

// pull "hello_ai.txt" from either user or AI text
function extractFilenameFrom(text) {
  if (!text) return '';
  const patterns = [
    /(?:create|save|write|update)\s+(?:a\s+)?(?:file\s+)?(?:called|named|as|to)?\s*["'`](.+?\.[A-Za-z0-9]{1,8})["'`]/i,
    /^(?:file(?:name)?|path)\s*:\s*["'`](.+?)["'`]/im,
    /\b([A-Za-z0-9._+\-]+?\.(?:txt|md|sh|js|ts|json|yml|yaml|toml|py|rb|go|rs|c|cpp|css|html|tsx))\b/
  ];
  for (const rx of patterns) {
    const m = text.match(rx);
    if (m && m[1]) return sanitizeFilename(m[1]);
  }
  return '';
}

// pull content that follows "with content: …" (or code fences) from either text
function extractContentFrom(text) {
  if (!text) return '';

  // prefer fenced code
  const fence = /```(?:\w+)?\n([\s\S]*?)```/m.exec(text);
  if (fence && fence[1]) return fence[1].trim();

  // common phrasings
  const keys = [
    /with\s+content\s*:\s*([\s\S]+)/i,
    /content\s*:\s*([\s\S]+)/i,
    /write\s+this\s*:\s*([\s\S]+)/i
  ];
  for (const rx of keys) {
    const m = text.match(rx);
    if (m && m[1]) return m[1].trim();
  }

  // fallback: if user clearly asked to create a file, treat remaining AI text as content
  if (/\b(create|save|write)\b/i.test(text)) return text.trim();

  return '';
}

// same as before; prefer Desktop → PTY cwd → Home
async function resolveTargetPath(proposedName) {
  const finalName = sanitizeFilename(proposedName) || `ai_created_${Date.now()}.txt`;
  const cwd = await window.bridge?.getCwd?.();
  const home = await window.files?.getHomeDir?.();
  const desktop = home ? `${home}/Desktop` : '';
  
  // Prefer Desktop for AI-created files unless in a project directory
  let dir = desktop || (typeof cwd === 'string' && cwd) || home || '';
  
  // If cwd is a project directory (not home), use it instead
  if (typeof cwd === 'string' && cwd && cwd !== home && !cwd.startsWith(home + '/Desktop')) {
    dir = cwd;
  }
  
  if (!dir) throw new Error('No writable base path resolved');
  if (dir.endsWith('/')) dir = dir.slice(0, -1);
  return `${dir}/${finalName}`;
}

async function ensureUniquePath(path) {
  const exists = async p => {
    const st = await window.files?.stat?.(p);
    return !!(st && st.isFile);
  };
  if (!(await exists(path))) return path;
  const dot = path.lastIndexOf('.');
  const stem = dot >= 0 ? path.slice(0, dot) : path;
  const ext  = dot >= 0 ? path.slice(dot) : '';
  for (let n=2; n<1000; n++) {
    const cand = `${stem} (${n})${ext}`;
    if (!(await exists(cand))) return cand;
  }
  return `${stem}-${Date.now()}${ext}`;
}

function extractBlocks(aiText) {
  let fileContent = '';
  let bashScript = '';
  let unifiedDiff = '';
  
  // Extract code blocks
  const codeBlockRegex = /```(?:(\w+)\n)?([\s\S]*?)```/g;
  let match;
  
  while ((match = codeBlockRegex.exec(aiText)) !== null) {
    const [, language, content] = match;
    if (language === 'bash' || language === 'sh') {
      bashScript = content.trim();
    } else if (language === 'diff') {
      unifiedDiff = content.trim();
    } else if (!fileContent) {
      fileContent = content.trim();
    }
  }
  
  // Check for diff without code blocks
  if (!unifiedDiff && (aiText.includes('+++') && aiText.includes('---'))) {
    unifiedDiff = aiText;
  }
  
  // If no code blocks, treat as file content if creating files
  if (!fileContent && !bashScript && !unifiedDiff) {
    const lower = aiText.toLowerCase();
    if (lower.includes('create') && (lower.includes('file') || lower.includes('save'))) {
      fileContent = aiText;
    }
  }
  
  return { fileContent, bashScript, unifiedDiff };
}

// === RENDERER_AI_V1_START ===
function initAIDock() {
  const dock = document.getElementById('ai-dock');
  const threadsEl = document.getElementById('ai-threads');
  const msgsEl = document.getElementById('ai-messages');
  const inputEl = document.getElementById('ai-dock-input');
  const sendBtn = document.getElementById('ai-dock-send');
  const closeDockBtn = document.getElementById('ai-close-dock');
  const newThreadBtn = document.getElementById('ai-new-thread');
  const modelSel = document.getElementById('ai-model');
  const actionsBtn = document.getElementById('ai-dock-actions');

  const STORAGE_KEY = 'warp_open_ai_threads_v1';
  let state = { threads: [], activeId: null };
  const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  const load = () => { 
    try { 
      state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {}; 
    } catch {} 
    state.threads = state.threads || []; 
    if (!state.activeId && state.threads[0]) state.activeId = state.threads[0].id; 
  };

  const uid = () => Math.random().toString(36).slice(2);
  const now = () => new Date().toISOString();

  function renderThreads() {
    threadsEl.innerHTML = '';
    state.threads.forEach(t => {
      const b = document.createElement('button');
      b.textContent = t.title || (t.messages[0]?.content?.slice(0, 18) || 'New thread');
      b.style.cssText = `display:block;width:100%;text-align:left;padding:6px;background:${state.activeId === t.id ? '#132029' : 'transparent'};color:#cdd6f4;border:0;cursor:pointer;border-radius:4px;margin-bottom:2px`;
      b.onclick = () => { state.activeId = t.id; save(); render(); };
      threadsEl.appendChild(b);
    });
  }

  function renderMessages() {
    msgsEl.innerHTML = '';
    const t = state.threads.find(x => x.id === state.activeId);
    if (!t) return;
    t.messages.forEach(m => {
      const d = document.createElement('div');
      d.style.margin = '6px 0';
      const role = m.role === 'user' ? 'You' : 'AI';
      const time = new Date(m.t || now()).toLocaleTimeString();
      d.innerHTML = `<div style="opacity:.7;font-size:12px">${role} • ${time}</div><div style="margin-top:4px">${escapeHtml(m.content)}</div>`;
      msgsEl.appendChild(d);
    });
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function render() { renderThreads(); renderMessages(); }

  function ensureThread() {
    if (!state.activeId) {
      const id = uid();
      state.threads.unshift({ id, title: 'New thread', createdAt: now(), messages: [] });
      state.activeId = id;
    }
  }

  function activeThread() { return state.threads.find(x => x.id === state.activeId); }

  function contextForAI() {
    // Get current working directory from active tab if available
    const cwd = window.bridge?.getCwd?.() || '';
    
    // Get scrollback from terminal
    const scrollback = window.bridge?.getScrollback?.(200) || '';
    
    return `Context:
- cwd: ${cwd || '~'}
- last_terminal_output:
${scrollback.slice(-500)}`; // Last 500 chars
  }

  // AI Power Tools
  function toast(msg) {
    const el = document.createElement('div');
    el.textContent = msg;
    el.style.cssText = 'position:fixed;top:20px;right:20px;background:#333;color:#fff;padding:8px 12px;border-radius:6px;z-index:10000;font:12px/1.2 ui-monospace,monospace';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  function stripCodeFenceBlock(t) {
    const head = t.match(/^```[a-zA-Z0-9._-]*\s*\n/);
    const tail = t.match(/\n```$/);
    if (head && tail) return t.replace(/^```[a-zA-Z0-9._-]*\s*\n/,'').replace(/\n```$/,'');
    return t;
  }

  async function aiApplyPatchFromText(diffText) {
    const cwd = window.bridge?.getCwd?.() || '';
    const cleanDiff = stripCodeFenceBlock(diffText);
    const res = await window.ai2.applyUnifiedDiff(cleanDiff, cwd);
    if (res?.ok) {
      toast(`✅ Patch applied with ${res.tool}`);
    } else {
      toast(`❌ Patch failed (${res?.tool || 'n/a'}): ${res?.error || 'unknown'}`);
    }
  }

  async function aiRunAsScript(text) {
    const cwd = window.bridge?.getCwd?.() || '';
    const cleanScript = stripCodeFenceBlock(text);
    const res = await window.ai2.makeScript(cleanScript, cwd);
    if (!res?.ok) return toast(`❌ Script create failed: ${res?.error || ''}`);
    // Execute through the PTY so all output appears in the terminal:
    const cmd = `bash "${res.scriptPath}"\r`;
    if (activeSessionId && window.bridge?.sendInput) {
      window.bridge.sendInput(activeSessionId, cmd);
      toast(`▶️ Running ${res.scriptPath}`);
    }
  }

  async function autoExecuteOperations({ aiText, userText }) {
    try {
      console.log('[auto-exec] calling with', { userText, aiText });
      
      // Extract filename for all operations
      const intendedFromUser = extractFilenameFrom(userText);
      const intendedFromAI   = extractFilenameFrom(aiText);
      const intended = intendedFromUser || intendedFromAI;

      // 1) PRIORITY: Script detection (bash code blocks or shebang) → create and run
      if (/\b(script|run|execute)\b/i.test(userText)) {
        // Try fenced code blocks first
        let scriptFence = /```(?:bash|sh)?\n([\s\S]*?)```/m.exec(aiText) || /```(?:bash|sh)?\n([\s\S]*?)```/m.exec(userText);
        let scriptContent = scriptFence?.[1];
        
        // Fallback: detect raw bash with shebang
        if (!scriptContent && (aiText.startsWith('#!/bin/bash') || aiText.startsWith('#!/bin/sh'))) {
          scriptContent = aiText.trim();
        }
        
        if (scriptContent) {
          const scriptName = (intended || 'ai_script.sh').endsWith('.sh') ? (intended || 'ai_script.sh') : `${intended || 'ai_script'}.sh`;
          const p0 = await resolveTargetPath(scriptName);
          const p  = await ensureUniquePath(p0);
          await window.files.writeTextFile(p, scriptContent.replace(/\r\n/g, '\n'));
          await window.bridge?.chmod?.(p, 0o755);
          await window.bridge?.runScript?.(p);
          console.log('[auto-exec:script] ran:', p);
          toast(`🚀 Ran script: ${p}`);
          await window.session?.appendAction?.('script:run', { path: p });
          return;
        }
      }

      // 2) PRIORITY: Unified diff detection → apply patch
      if (/\b(apply|diff|patch|update)\b/i.test(userText)) {
        // Check if user input or AI response contains a diff
        const hasDiff = (aiText.includes('+++') && aiText.includes('---')) || 
                        (userText.includes('+++') && userText.includes('---'));
        
        if (hasDiff) {
          try {
            // Try to extract from fenced code block first
            let diffBody = /```diff\n([\s\S]*?)```/m.exec(aiText)?.[1];
            
            // Fallback: if AI returned raw diff, use it directly
            if (!diffBody && aiText.includes('---') && aiText.includes('+++')) {
              diffBody = aiText.trim();
            }
            
            // Fallback: extract diff from user text
            if (!diffBody && userText.includes('---') && userText.includes('+++')) {
              diffBody = userText.split('\n').slice(userText.split('\n').findIndex(l => l.startsWith('---'))).join('\n');
            }
            
            if (!diffBody) {
              toast('⚠️ No valid diff found');
              return;
            }
            
            console.log('[auto-exec:patch] applying diff:', diffBody.slice(0, 200));
            
            // Get CWD for patch context
            const cwd = await window.bridge?.getCwd?.() || '';
            console.log('[auto-exec:patch] cwd:', cwd);
            
            // Add timeout protection
            const timeoutPromise = new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Patch operation timed out after 5s')), 5000)
            );
            
            console.log('[auto-exec:patch] calling applyUnifiedDiff...');
            const patchPromise = window.ai2?.applyUnifiedDiff?.(diffBody, cwd);
            const res = await Promise.race([patchPromise, timeoutPromise]);
            
            console.log('[auto-exec:patch] result:', res);
            
            // If git/patch failed, try simple file replacement for single-file diffs
            if (!res?.ok && intended) {
              console.log('[auto-exec:patch] git/patch failed, trying manual replacement...');
              
              // Extract old and new content from diff (skip header lines ---/+++)
              // Match lines that start with single - or + (not -- or ++)
              const oldLine = /^-([^-].*)$/m.exec(diffBody)?.[1];
              const newLine = /^\+([^+].*)$/m.exec(diffBody)?.[1];
              
              console.log('[auto-exec:patch] extracted oldLine:', oldLine);
              console.log('[auto-exec:patch] extracted newLine:', newLine);
              
              if (oldLine && newLine) {
                try {
                  // Try to find and update the file on Desktop
                  const home = await window.files?.getHomeDir?.();
                  console.log('[auto-exec:patch] home:', home);
                  console.log('[auto-exec:patch] intended filename:', intended);
                  
                  const possiblePaths = [
                    `${home}/Desktop/${intended}`,
                    `${cwd}/${intended}`,
                    intended
                  ];
                  
                  console.log('[auto-exec:patch] trying paths:', possiblePaths);
                  
                  for (const tryPath of possiblePaths) {
                    console.log('[auto-exec:patch] trying path:', tryPath);
                    try {
                      const result = await window.files?.readTextFile?.(tryPath);
                      const existing = result?.content || result; // Handle both {ok, content} and raw string
                      console.log('[auto-exec:patch] file read, length:', existing?.length, 'content:', JSON.stringify(existing));
                      console.log('[auto-exec:patch] looking for:', JSON.stringify(oldLine));
                      console.log('[auto-exec:patch] includes?', existing?.includes(oldLine));
                      
                      if (existing && existing.includes(oldLine)) {
                        const updated = existing.replace(oldLine, newLine);
                        await window.files?.writeTextFile?.(tryPath, updated);
                        console.log('[auto-exec:patch] manual replacement succeeded:', tryPath);
                        toast(`🧩 Patch applied (manual): ${tryPath}`);
                        await window.session?.appendAction?.('patch:apply', { ok: true, method: 'manual' });
                        return;
                      }
                    } catch (e) {
                      console.log('[auto-exec:patch] path failed:', tryPath, e.message);
                      continue;
                    }
                  }
                  
                  console.log('[auto-exec:patch] no paths worked');
                  toast(`⚠️ Patch failed: file not found or content mismatch`);
                } catch (err) {
                  console.error('[auto-exec:patch] manual fallback error:', err);
                  toast(`⚠️ Patch failed: ${res?.error || 'unknown'}`);
                }
              } else {
                console.log('[auto-exec:patch] no oldLine or newLine extracted');
                toast(`⚠️ Patch failed: ${res?.error || 'unknown'}`);
              }
            } else {
              toast(res?.ok ? '🧩 Patch applied' : `⚠️ Patch failed: ${res?.error || 'unknown'}`);
            }
            
            await window.session?.appendAction?.('patch:apply', { ok: !!res?.ok });
            return;
          } catch (err) {
            console.error('[auto-exec:patch] error:', err);
            toast(`⚠️ Patch error: ${err.message}`);
            return;
          }
        }
      }

      // 3) FALLBACK: Generic file creation
      const userWantsFile = /\b(create|save|write)\b/i.test(userText) && /\b(file|as|named|called)\b/i.test(userText);
      const aiMentionsFile = /\b(file|save|create|write)\b/i.test(aiText);

      const contentFromUser = extractContentFrom(userText);
      const contentFromAI   = extractContentFrom(aiText);
      const content = contentFromUser || contentFromAI;

      if ((userWantsFile || aiMentionsFile) && content) {
        const target0 = await resolveTargetPath(intended);
        const target  = await ensureUniquePath(target0);
        await window.files.writeTextFile(target, content);
        console.log('[auto-exec:file] wrote:', target);
        toast(`✅ File saved: ${target}`);
        await window.session?.appendAction?.('file:create', { target, bytes: content.length });
        return;
      }

      // No action matched; that's okay.
      console.log('[auto-exec] no actionable intent');
    } catch (e) {
      console.error('[auto-exec] error:', e);
      toast(`❌ Auto-exec error: ${e.message}`);
    }
  }

  async function send() {
    ensureThread();
    const t = activeThread(); 
    if (!t) return;
    const user = inputEl.value.trim(); 
    if (!user) return;
    const content = preprocessSlash(user);

    t.messages.push({ role: 'user', content, t: now() });
    inputEl.value = '';
    save(); 
    render();

    const model = modelSel.value;
    // system primer
    const system = { 
      role: 'system', 
      content: `You are an autonomous coding assistant with real system access.

Your capabilities:
- Create, read, write, and edit files directly on the system
- Execute bash scripts and commands via the terminal
- Apply unified diffs to modify existing files
- All operations happen automatically when you decide to use them

Available functions (use automatically as needed):
- writeFile(path, content) - creates or overwrites files
- applyUnifiedDiff(diffText, cwd) - applies patches to files
- makeScript(scriptText, cwd) - creates and executes bash scripts
- sendToTerminal(command) - runs commands in the terminal

When creating files:
- Always specify the exact filename you want (e.g. "test_file.txt")
- Use clear language like "I'll create a file called filename.ext"
- The system will automatically extract the filename and create it

When creating scripts:
- ALWAYS provide the actual script code in a bash code block
- Example: \`\`\`bash\nls *.txt\n\`\`\`
- The system will automatically extract, save, and execute it

When asked to create files, edit files, or run scripts - do it immediately and report the results.
Don't ask for permission or tell the user to click buttons - just execute the operations.

Be autonomous and helpful.`
    };
    // context
    const ctx = { role: 'system', content: contextForAI() };

    try {
      msgsEl.insertAdjacentHTML('beforeend', `<div id="ai-spinner" style="opacity:.7">…thinking</div>`);
      const res = await (window.ai2 || window.ai).chat({ 
        messages: [system, ctx, ...t.messages], 
        model, 
        temperature: 0.1, 
        max_tokens: 800 
      });
      document.getElementById('ai-spinner')?.remove();
      const assistant = res.text || '(no output)';
      
      // Auto-execute file operations based on AI response
      await autoExecuteOperations({ aiText: assistant, userText: user });
      
      t.messages.push({ role: 'assistant', content: assistant, t: now() });
      // rename thread on first answer
      if (!t.title || t.title === 'New thread') t.title = user.slice(0, 24);
      save(); 
      render();
    } catch (err) {
      document.getElementById('ai-spinner')?.remove();
      t.messages.push({ role: 'assistant', content: `Error: ${String(err)}`, t: now() });
      save(); 
      render();
    }
  }

  function preprocessSlash(s) {
    if (s.startsWith('/explain ')) return `Explain clearly: ${s.slice(9)}`;
    if (s.startsWith('/fix ')) return `Propose a minimal fix with a diff:\n${s.slice(5)}`;
    if (s.startsWith('/test ')) return `Write a small test:\n${s.slice(6)}`;
    if (s.startsWith('/unit ')) return `Add unit tests and explain:\n${s.slice(6)}`;
    if (s.startsWith('/diff ')) return `Return only a unified diff for:\n${s.slice(6)}`;
    return s;
  }

  // actions menu
  actionsBtn?.addEventListener('click', async () => {
    const t = activeThread(); 
    if (!t) return;
    const last = [...t.messages].reverse().find(m => m.role === 'assistant')?.content || '';
    if (!last) return toast('No assistant message yet.');
    
    // Create a simple menu
    const menu = document.createElement('div');
    menu.style.cssText = 'position:absolute;top:100%;right:0;background:#222;border:1px solid #444;border-radius:6px;padding:8px;z-index:1000;min-width:200px';
    menu.innerHTML = `
      <button class="action-btn" data-action="terminal">Insert to terminal</button>
      <button class="action-btn" data-action="file">Create/Update file</button>
      <button class="action-btn" data-action="patch">Apply patch</button>
      <button class="action-btn" data-action="script">Run as script</button>
    `;
    
    // Style the buttons
    menu.querySelectorAll('.action-btn').forEach(btn => {
      btn.style.cssText = 'display:block;width:100%;padding:8px;margin:2px 0;background:#333;color:#fff;border:1px solid #555;border-radius:4px;cursor:pointer;text-align:left';
      btn.addEventListener('mouseover', () => btn.style.background = '#444');
      btn.addEventListener('mouseout', () => btn.style.background = '#333');
    });
    
    // Position relative to actions button
    actionsBtn.style.position = 'relative';
    actionsBtn.appendChild(menu);
    
    // Handle clicks
    menu.addEventListener('click', async (e) => {
      const action = e.target.dataset.action;
      menu.remove();
      
      if (action === 'terminal') {
        const cmd = last.trim().split('\n').slice(-1)[0];
        if (activeSessionId && window.bridge?.sendInput) {
          window.bridge.sendInput(activeSessionId, cmd + '\r');
          toast('Sent to terminal.');
        }
      } else if (action === 'file') {
        const fp = '/Users/davidquinton/Desktop/ai_output.txt';
        try {
          const result = await (window.ai2 || window.ai).writeFile({ filePath: fp, content: last });
          if (result?.ok !== false) {
            toast('✅ Successfully wrote file to ' + fp);
          } else {
            toast('❌ Failed to write file: ' + (result?.error || 'Unknown error'));
          }
        } catch (err) {
          toast('❌ Error writing file: ' + err.message);
        }
      } else if (action === 'patch') {
        await aiApplyPatchFromText(last);
      } else if (action === 'script') {
        await aiRunAsScript(last);
      }
    });
    
    // Close menu when clicking outside
    setTimeout(() => {
      document.addEventListener('click', function closeMenu(e) {
        if (!menu.contains(e.target)) {
          menu.remove();
          document.removeEventListener('click', closeMenu);
        }
      });
    }, 0);
  });

  // open/close/toggle & shortcuts
  closeDockBtn?.addEventListener('click', () => dock.style.display = 'none');
  newThreadBtn?.addEventListener('click', () => {
    const id = uid();
    state.threads.unshift({ id, title: 'New thread', createdAt: now(), messages: [] });
    state.activeId = id; 
    save(); 
    render();
  });
  sendBtn?.addEventListener('click', send);
  inputEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { 
      e.preventDefault(); 
      send(); 
    }
  });

  function escapeHtml(s) { 
    return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]); 
  }

  // Replace the legacy AI panel toggle with dock toggle
  window.toggleAIPanel = function(show) {
    if (show === false) {
      dock.style.display = 'none';
    } else {
      dock.style.display = (dock.style.display === 'flex') ? 'none' : 'flex';
      if (dock.style.display === 'flex') inputEl?.focus();
    }
  };

  // init
  load(); 
  ensureThread(); 
  render();
  
  // Start with dock hidden initially
  dock.style.display = 'none';
  
  // Expose autoExecuteOperations globally for testing
  window.autoExecuteOperations = autoExecuteOperations;
  
  // === PHASE4.1: Journal & Context Panels ===
  const journalEntriesEl = document.getElementById('journal-entries');
  const journalUndoBtn = document.getElementById('journal-undo-btn');
  const journalRefreshBtn = document.getElementById('journal-refresh-btn');
  const contextPackEl = document.getElementById('context-pack');
  const contextRefreshBtn = document.getElementById('context-refresh-btn');
  
  // Tab switching
  document.querySelectorAll('.ai-dock-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      
      // Update tab styles
      document.querySelectorAll('.ai-dock-tab').forEach(t => {
        t.classList.remove('active');
        t.style.background = 'transparent';
        t.style.color = '#6c7a8a';
        t.style.border = '1px solid transparent';
      });
      tab.classList.add('active');
      tab.style.background = '#132029';
      tab.style.color = '#cdd6f4';
      tab.style.border = '1px solid #1b2530';
      
      // Show/hide content
      document.querySelectorAll('.ai-dock-content').forEach(c => c.style.display = 'none');
      document.getElementById(`ai-dock-${targetTab}`).style.display = 'flex';
      
      // Load data for new tab
      if (targetTab === 'journal') loadJournal();
      if (targetTab === 'context') loadContext();
    });
  });
  
  // Load Journal
  async function loadJournal() {
    try {
      const res = await window.ai2.getJournal({ limit: 25 });
      const entries = res.entries || [];
      
      if (entries.length === 0) {
        journalEntriesEl.innerHTML = '<div style="color:#6c7a8a;text-align:center;padding:20px">No actions recorded yet.</div>';
        return;
      }
      
      journalEntriesEl.innerHTML = entries.map(e => `
        <div style="background:rgba(255,255,255,0.05);border:1px solid #1b2530;border-radius:6px;padding:8px;font-size:12px">
          <div style="display:flex;justify-between;margin-bottom:4px">
            <span style="color:#4c9aff;font-weight:600">${e.type}</span>
            <span style="color:#6c7a8a;font-size:10px">${e.id.slice(0, 8)}</span>
          </div>
          <div style="color:#cdd6f4;font-family:ui-monospace,monospace;font-size:11px">${e.summary}</div>
          <div style="color:#6c7a8a;font-size:10px;margin-top:4px">${new Date(e.timestamp).toLocaleString()}</div>
        </div>
      `).join('');
    } catch (err) {
      console.error('[journal] load error:', err);
      journalEntriesEl.innerHTML = '<div style="color:#b91c1c">Failed to load journal</div>';
    }
  }
  
  // Undo Last
  journalUndoBtn?.addEventListener('click', async () => {
    try {
      const res = await window.ai2.undoLast();
      if (res.ok) {
        toast(`✅ Undone: ${res.undone?.type || 'action'}`);
        loadJournal();
      } else {
        toast(`⚠️ ${res.error || 'No actions to undo'}`);
      }
    } catch (err) {
      console.error('[journal] undo error:', err);
      toast('❌ Undo failed');
    }
  });
  
  journalRefreshBtn?.addEventListener('click', loadJournal);
  
  // Load Context Pack
  async function loadContext() {
    try {
      const ctx = await window.ai2.getContextPack();
      
      const html = `
        <div style="margin-bottom:16px">
          <div style="color:#4c9aff;font-weight:600;margin-bottom:8px">📁 Current Directory</div>
          <div style="color:#cdd6f4;background:rgba(255,255,255,0.05);padding:8px;border-radius:4px;font-size:11px">${ctx.cwd}</div>
        </div>
        
        <div style="margin-bottom:16px">
          <div style="color:#4c9aff;font-weight:600;margin-bottom:8px">📝 Recent Actions (${ctx.recentActions?.length || 0})</div>
          ${ctx.recentActions && ctx.recentActions.length ? 
            ctx.recentActions.slice(0, 5).map(a => 
              `<div style="color:#6c7a8a;font-size:11px;padding:4px 0">• ${a.type}: ${a.summary}</div>`
            ).join('') : 
            '<div style="color:#6c7a8a;font-size:11px">No recent actions</div>'
          }
        </div>
        
        <div style="margin-bottom:16px">
          <div style="color:#4c9aff;font-weight:600;margin-bottom:8px">🔧 Environment</div>
          <div style="color:#6c7a8a;font-size:11px">Shell: ${ctx.env?.SHELL || 'unknown'}</div>
          <div style="color:#6c7a8a;font-size:11px">Project: ${ctx.projectRoot || 'unknown'}</div>
        </div>
        
        <div>
          <div style="color:#4c9aff;font-weight:600;margin-bottom:8px">ℹ️ Context ID</div>
          <div style="color:#6c7a8a;font-size:10px;font-family:ui-monospace,monospace">${ctx.id}</div>
        </div>
      `;
      
      contextPackEl.innerHTML = html;
    } catch (err) {
      console.error('[context] load error:', err);
      contextPackEl.innerHTML = '<div style="color:#b91c1c">Failed to load context</div>';
    }
  }
  
  contextRefreshBtn?.addEventListener('click', loadContext);
  // === PHASE4.1 END ===
}
// === RENDERER_AI_V1_END ===
