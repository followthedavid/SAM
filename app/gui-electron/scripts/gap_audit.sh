#!/usr/bin/env bash
set -euo pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
ok(){ printf "✅ %s\n" "$1"; }
miss(){ printf "❌ %s\n" "$1"; }

req_files=(
  "src/main.js" "src/preload.js" "src/renderer.js" "src/index.html"
  "scripts/run_smoke_once.sh" "scripts/validate_smoke.js" "scripts/smoke_summary.sh" "scripts/replay_session.js"
)
for f in "${req_files[@]}"; do [ -f "$APP/$f" ] && ok "$f" || miss "$f"; done

echo "--- main.js checks ---"
grep -q "WARP_OPEN_SMOKE_MARKER" "$APP/src/main.js" && ok "smoke hook marker" || miss "smoke hook marker"
grep -q "sandbox: false"         "$APP/src/main.js" && ok "webPreferences.sandbox=false" || miss "sandbox=false"
grep -q "contextIsolation: true" "$APP/src/main.js" && ok "contextIsolation=true" || miss "contextIsolation=true"
grep -q "nodeIntegration: false" "$APP/src/main.js" && ok "nodeIntegration=false" || miss "nodeIntegration=false"

echo "--- preload.js checks ---"
grep -q "contextBridge" "$APP/src/preload.js" && ok "contextBridge present" || miss "contextBridge"
grep -q "startPTY"      "$APP/src/preload.js" && ok "terminal API exposed"  || miss "terminal API"
grep -q "getBlocks"     "$APP/src/preload.js" && ok "blocks API exposed"    || miss "blocks API"

echo "--- renderer.js checks ---"
grep -q "term.onData"   "$APP/src/renderer.js" && ok "term.onData → sendInput" || miss "term.onData binding"
grep -q "key.toLowerCase() === 'b'" "$APP/src/renderer.js" && ok "Blocks toggle shortcut" || miss "Blocks shortcut"

echo "--- Blocks IPC/UI presence ---"
[ -f "$APP/src/blocks_ipc.js" ] && ok "blocks_ipc.js" || miss "blocks_ipc.js"
[ -f "$APP/src/blocks_ui.js" ]  && ok "blocks_ui.js"  || miss "blocks_ui.js"

echo "--- package.json scripts ---"
node - <<'NODE'
const fs=require('fs'); const p='./package.json';
const expect=['smoke','smoke:validate','smoke:once','rebuild','ci','replay','pack:mac','dev'];
const pkg=JSON.parse(fs.readFileSync(p,'utf8')); const got=Object.keys(pkg.scripts||{});
for (const s of expect){ console.log((got.includes(s)?'✅':'❌')+' script: '+s); }
NODE
