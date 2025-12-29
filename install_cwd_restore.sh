#!/usr/bin/env bash
# --- Per-Tab CWD Restore v2.1: install & verify (idempotent) ---
set -euo pipefail
APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
cd "$APP"

backup_once() { [ -f "$1" ] && [ ! -f "$1.bak" ] && cp "$1" "$1.bak" || true; }

# 1) renderer.js patch (persist/restore CWD per tab + panic save)
if ! grep -q '=== CWD_RESTORE_V21_START ===' src/renderer.js 2>/dev/null; then
  backup_once src/renderer.js
  cat >> src/renderer.js <<'JS'

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
JS
  echo "✓ renderer.js: CWD restore v2.1 added"
else
  echo "• renderer.js already patched"
fi

# 2) main.js: IPC handler to allow spawning tabs with CWD (optional)
if ! grep -q '=== CWD_RESTORE_IPC_START ===' src/main.js 2>/dev/null; then
  backup_once src/main.js
  cat >> src/main.js <<'JS'

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
JS
  echo "✓ main.js: IPC term:new (cwd) installed"
else
  echo "• main.js already patched"
fi

# 3) preload.js: expose bridge.newTabWithCwd (optional)
if ! grep -q '=== CWD_RESTORE_BRIDGE_START ===' src/preload.js 2>/dev/null; then
  backup_once src/preload.js
  cat >> src/preload.js <<'JS'

// === CWD_RESTORE_BRIDGE_START ===
(() => {
  try {
    const { contextBridge, ipcRenderer } = require('electron');
    const api = { newTabWithCwd: (opts) => ipcRenderer.invoke('term:new', opts||{}) };
    if (window.bridge) Object.assign(window.bridge, api);
    else contextBridge.exposeInMainWorld('bridge', api);
  } catch {}
})();
// === CWD_RESTORE_BRIDGE_END ===
JS
  echo "✓ preload.js: bridge.newTabWithCwd exposed"
else
  echo "• preload.js already patched"
fi

echo
echo "NEXT:"
cat <<'NEXTSTEPS'
1) Launch the app:
   cd "$HOME/ReverseLab/Warp_Open/app/gui-electron" && npm run dev

   In the window:
   - Open two tabs.
   - In tab A:  cd ~ ;  ls
   - In tab B:  cd ~/Desktop ;  ls
   - Press Cmd+Opt+S (or Ctrl+Alt+S) to force-save, or click your 💾 Flush button.
   - Quit the app normally.

2) Relaunch (npm run dev) — both tabs should reopen at the same CWDs.
   If your main spawn doesn't honor CWD yet, the restore sends a fallback `cd "…"` automatically.

3) (Optional) Quick log peek:
   LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl | head -1)"; echo "$LOG"
   grep -nE 'cwd:update|session:flush' "$LOG" | sed -n '1,60p'

Troubleshooting:
- If tabs don't restore: open DevTools and run `cwdr.load()` to see saved entries.
- If new tabs open but not in the right folder, your main spawn likely ignores CWD; the fallback `cd` will still correct it shortly after attach.
NEXTSTEPS
