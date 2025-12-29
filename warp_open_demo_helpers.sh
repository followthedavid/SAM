#!/usr/bin/env bash
# === Warp_Open: fast demo helpers (Enter-heuristic blocks, Flush button, console summary) ===
set -euo pipefail
APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
cd "$APP"

backup_once() {
  local f="$1"; [ -f "$f" ] && [ ! -f "$f.bak" ] && cp "$f" "$f.bak" || true
}

# 1) Preload: expose session.flush() and blocksExtra.summary()
backup_once src/preload.js
node - <<'NODE'
const fs = require('fs'); const p='src/preload.js'; let s=fs.readFileSync(p,'utf8');
if(!s.includes('// WARP_OPEN_DEMO_PRELOAD')) {
  s = s.replace(/const \{ contextBridge, ipcRenderer[^}]*\}/,
                'const { contextBridge, ipcRenderer } = require("electron")');
  s += `

/* WARP_OPEN_DEMO_PRELOAD */
try {
  // Safe session flush hook -> main
  contextBridge.exposeInMainWorld('session', {
    flush: () => ipcRenderer.invoke('session:flush').catch(()=>({ok:false}))
  });

  // Optional blocks helper summary (renderer can call blocksExtra.summary())
  contextBridge.exposeInMainWorld('blocksExtra', {
    async summary() {
      try {
        const getBlocks = (window.blocks && window.blocks.getBlocks)
                       || (window.bridge && window.bridge.getBlocks);
        if(!getBlocks) { console.warn('[blocksExtra] no getBlocks'); return; }
        const list = await getBlocks();
        const running = list.filter(b=>!b.endedAt).length;
        const done    = list.filter(b=>b.endedAt).length;
        const failed  = list.filter(b=>b.exitCode && b.exitCode!==0).length;
        const lastCmd = list.length ? (list[list.length-1].command||'') : '';
        console.log('[blocks] total=%d running=%d done=%d failed=%d last="%s"',
          list.length, running, done, failed, lastCmd);
      } catch(e) { console.error('[blocksExtra.summary]', e); }
    }
  });
} catch(e) { console.error('[preload demo wiring]', e); }
`;
  fs.writeFileSync(p,s);
  console.log('✅ preload.js patched');
} else {
  console.log('✅ preload.js already has demo block');
}
NODE

# 2) Main: IPC handler for session:flush (best-effort)
backup_once src/main.js
node - <<'NODE'
const fs = require('fs'); const p='src/main.js'; let s=fs.readFileSync(p,'utf8');
if(!s.includes('WARP_OPEN_DEMO_MAIN_FLUSH')){
  // ensure ipcMain imported
  if(!/ipcMain/.test(s)){
    s = s.replace(/require\(["']electron["']\)\)/,
      `require("electron"))\nconst { ipcMain } = require("electron")`);
  }
  s += `

// WARP_OPEN_DEMO_MAIN_FLUSH
try {
  // Try to call whatever session logger the app keeps (no-op if absent)
  ipcMain.handle('session:flush', async () => {
    try {
      if (globalThis.__warpOpenSession?.flush) {
        await globalThis.__warpOpenSession.flush();
      }
      // Also broadcast to renderers in case they buffer anything
      const { BrowserWindow } = require('electron');
      BrowserWindow.getAllWindows().forEach(w => {
        try { w.webContents.send('session:flush:ack'); } catch {}
      });
      return { ok: true };
    } catch(e) {
      return { ok:false, error:String(e) };
    }
  });
} catch(e) { /* non-fatal */ }
`;
  fs.writeFileSync(p,s);
  console.log('✅ main.js patched (session:flush handler)');
} else {
  console.log('✅ main.js already has session:flush handler');
}
NODE

# 3) HTML: add 💾 Flush button next to your header actions
backup_once src/index.html
node - <<'NODE'
const fs=require('fs'); const p='src/index.html'; let s=fs.readFileSync(p,'utf8');
if(!s.includes('id="flushBtn"')){
  s = s.replace(/id="header-actions"[^>]*>/,
    m => m + '\n      <button id="flushBtn" title="Flush Session">💾 Flush</button>');
  fs.writeFileSync(p,s);
  console.log('✅ index.html: Flush button added');
} else {
  console.log('✅ index.html already has Flush button');
}
NODE

# 4) Renderer: wire the button + keyboard shortcut + summary printer
backup_once src/renderer.js
node - <<'NODE'
const fs=require('fs'); const p='src/renderer.js'; let s=fs.readFileSync(p,'utf8');

if(!s.includes('// WARP_OPEN_DEMO_RENDERER')){
  s += `

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
`;
  fs.writeFileSync(p,s);
  console.log('✅ renderer.js patched (Flush + summary hotkey)');
} else {
  console.log('✅ renderer.js already has demo wiring');
}
NODE

# 5) Add a helper runner to always use Enter-heuristic mode for demos
mkdir -p scripts
cat > scripts/dev_enter_blocks.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export WARP_OPEN_ENABLE_BLOCKS=1
export WARP_OPEN_BLOCKS_MODE=enter   # force Enter-heuristic boundaries
npm run dev
SH
chmod +x scripts/dev_enter_blocks.sh
echo "✅ scripts/dev_enter_blocks.sh created"

echo
echo "=== Done. How to verify ==="
echo "1) Headless health check:"
echo "   npm run smoke:once && scripts/smoke_summary.sh"
echo "2) GUI demo (Enter heuristic on):"
echo "   ./scripts/dev_enter_blocks.sh"
echo "   - Type: echo hello ; pwd ; ls"
echo "   - Click 💾 Flush; press Cmd+Opt+B (or Ctrl+Alt+B) to print block summary"
echo "   - Open 📋 Blocks panel (Cmd+B) to view recorded blocks"
echo "3) Inspect latest session:"
echo '   LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl | head -1)"; echo "$LOG";'
echo "   grep -nE 'block:(start|exec|end)|cwd:update' \"\$LOG\" || echo 'No block events found'"
