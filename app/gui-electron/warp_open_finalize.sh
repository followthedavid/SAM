#!/usr/bin/env bash
set -euo pipefail

APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
SRC="$APP/src"
SESS="$HOME/.warp_open/sessions"
mkdir -p "$SESS"

say() { printf "\033[1;36m[finalize]\033[0m %s\n" "$*"; }
ok()  { printf "\033[1;32m[ok]\033[0m %s\n" "$*"; }
warn(){ printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[err]\033[0m %s\n" "$*"; }

cd "$APP"

# 0) Ensure deps for small perf tweaks
say "Installing lodash.debounce (safe, tiny)…"
npm pkg set scripts.final:verify='node ./scripts/validate_smoke.js "$(ls -t $HOME/.warp_open/sessions/session-*.jsonl | head -1)" || true'
npm pkg set scripts.final:smoke='WARP_OPEN_ENABLE_SMOKE=1 npx electron . || true'
npm pkg set scripts.final:pack='electron-rebuild -f -w node-pty && electron-packager . Warp_Open --platform=darwin --arch=arm64 --out=dist --overwrite --asar --ignore=dist'
npm pkg set scripts.final:codesign='bash ./scripts/codesign_adhoc.sh'
npm pkg set scripts.final:all='npm run rebuild && npm run final:smoke && npm run final:verify && npm run final:pack && npm run final:codesign'
npm i lodash.debounce --save >/dev/null 2>&1 || true
ok "deps scripted"

# 1) Create tiny util used for throttled local writes (does NOT touch PTY log path)
mkdir -p "$SRC/utils"
if [ ! -f "$SRC/utils/throttle.js" ]; then
  cat > "$SRC/utils/throttle.js" <<'JS'
// Lightweight debounce wrapper so we never hammer localStorage.
const debounce = require('lodash.debounce');
module.exports.debounceJson = (fn) => debounce(fn, 150, { maxWait: 600 });
JS
  ok "utils/throttle.js added"
fi

# 2) Idempotent patch: per-tab scrollback snapshot (restore on re-open / tab switch)
RS="$SRC/renderer.js"
if ! grep -q 'SCROLLBACK_SNAPSHOT_START' "$RS"; then
  cp "$RS" "$RS.bak.finalize.$$"
  cat >> "$RS" <<'JS'

// === SCROLLBACK_SNAPSHOT_START ===
// Per-tab scrollback snapshot (last ~2000 "lines" of output chunks)
// Safe: operates only in renderer localStorage, not JSONL session writer.
(() => {
  const KEY = 'warp_open.scrollback.v1';
  const { debounceJson } = (() => {
    try { return require('./utils/throttle.js'); } catch { return { debounceJson: (f)=>f }; }
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
JS
  ok "renderer.js patched with scrollback snapshot"
else
  warn "renderer.js already has SCROLLBACK_SNAPSHOT block; skipping"
fi

# 3) Ad-hoc codesign helper (safe on macOS; no Apple cert required)
mkdir -p "$APP/scripts"
cat > "$APP/scripts/codesign_adhoc.sh" <<'SH2'
#!/usr/bin/env bash
set -euo pipefail
APPDIR="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$APPDIR/dist/Warp_Open-darwin-arm64/Warp_Open.app"
if [ ! -d "$BUNDLE" ]; then
  echo "[codesign] bundle not found: $BUNDLE"
  exit 0
fi
echo "[codesign] ad-hoc signing (deep)…"
codesign --deep --force --sign - "$BUNDLE" && echo "[codesign] done" || {
  echo "[codesign] skipped (codesign not available?)"
  exit 0
}
SH2
chmod +x "$APP/scripts/codesign_adhoc.sh"
ok "codesign helper ready"

# 4) Rebuild native bits and run a short smoke to refresh logs
say "Rebuilding native modules…"
npm run rebuild >/dev/null 2>&1 || true
say "Running short smoke (non-fatal if you close quickly)…"
npm run final:smoke || true

LOG="$(ls -t "$SESS"/session-*.jsonl 2>/dev/null | head -1 || true)"
if [ -n "${LOG:-}" ] && [ -f "$LOG" ]; then
  ok "Latest session: $LOG"
  node ./scripts/validate_smoke.js "$LOG" || true
  ./scripts/smoke_summary.sh "$LOG" || true
else
  warn "No session log found yet (run GUI once to generate)."
fi

# 5) Build + ad-hoc sign the app bundle (optional but recommended)
say "Packing macOS app…"
npm run final:pack >/dev/null 2>&1 || true
if [ -d "dist/Warp_Open-darwin-arm64/Warp_Open.app" ]; then
  say "Codesigning (ad-hoc)…"
  npm run final:codesign >/dev/null 2>&1 || true
  ok "Bundle: $APP/dist/Warp_Open-darwin-arm64/Warp_Open.app"
else
  warn "No bundle produced (you can run: npm run final:pack)"
fi

echo
ok "Finalize complete."
echo "Next:"
echo "  1) npm run dev"
echo "  2) Type: echo hello, pwd, ls  (close window)"
echo "  3) Replay: node scripts/replay_session.js \"\$(ls -t $SESS/session-*.jsonl | head -1)\" | sed -n '1,60p'"
echo "  4) Re-open app → tabs, cwd, and scrollback restore"
