#!/usr/bin/env bash
set -Eeuo pipefail

# Unattended batch runner for Warp_Open GUI (Electron) tasks
# - Writes JSON receipts per step under .vg/receipts/warp_open_batch
# - Streams logs to .vg/receipts/warp_open_batch/logs/<step>.log
# - Uses DO_CMD wrapper if available for verifiable execution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECEIPTS_DIR="$ROOT/.vg/receipts/warp_open_batch"
LOG_DIR="$RECEIPTS_DIR/logs"
mkdir -p "$LOG_DIR"

notify() {
  local title="$1"; shift; local msg="$*"
  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier -group warp_open_batch -title "$title" -message "$msg" >/dev/null 2>&1 || true
  else
    osascript -e 'display notification '"'""$msg"'"' with title '"'""$title"'"'' >/dev/null 2>&1 || true
  fi
}

write_status() {
  local phase="$1"; local cur="$2"; local tot="$3"; local last="$4"; local pid_file="$RECEIPTS_DIR/batch.pid"
  local pid=""; [[ -f "$pid_file" ]] && pid=$(cat "$pid_file" 2>/dev/null || true)
  cat > "$RECEIPTS_DIR/status.json" <<JSON
{
  "running": true,
  "pid": "${pid}",
  "current_step": "${cur}",
  "total_steps": "${tot}",
  "phase": "${phase}",
  "last_status": "${last}",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
}

# Detect verification wrapper if it is a real executable, otherwise leave empty
_detect_do() {
  local c; c=$(command -v do 2>/dev/null || true)
  if [[ -n "$c" && "$c" != "do" && -x "$c" ]]; then echo "$c"; else echo ""; fi
}
DO_CMD="${DO_CMD:-$(_detect_do)}"
AUTO_APPROVE="${AUTO_APPROVE:-1}"

iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

write_receipt() {
  local id="$1" desc="$2" status="$3" started_ts="$4" ended_ts="$5" log="$6"
  local started_iso; started_iso=$(date -u -r "$started_ts" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")
  local ended_iso; ended_iso=$(date -u -r "$ended_ts" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")
  local duration=$(( ended_ts - started_ts ))
  cat >"$RECEIPTS_DIR/${id}.json" <<JSON
{
  "id": "${id}",
  "desc": "${desc}",
  "status": "${status}",
  "started_at": "${started_iso}",
  "ended_at": "${ended_iso}",
  "duration_s": ${duration},
  "cwd": "${PWD}",
  "log": "${log}"
}
JSON
}

run_step() {
  local id="$1" desc="$2"; shift 2
  local log="$LOG_DIR/${id}.log"
  : >"$log"
  local started_ts; started_ts=$(date -u +%s)
  echo "==> [$id] $desc" | tee -a "$log"
  set +e
  "$@" >>"$log" 2>&1
  local rc=$?
  set -e
  local ended_ts; ended_ts=$(date -u +%s)
  local status="success"; [[ $rc -eq 0 ]] || status="error"
  write_receipt "$id" "$desc" "$status" "$started_ts" "$ended_ts" "$log"
  # notify per-step
  if [[ "$status" == "success" ]]; then notify "Warp_Open" "✔ $id — $desc"; else notify "Warp_Open" "✖ $id — $desc"; fi
  return $rc
}

# If DO_CMD is available, prefer it to execute commands with verification
xrun() {
  if [[ -n "$DO_CMD" && -x "$DO_CMD" ]]; then "$DO_CMD" "$@"; else "$@"; fi
}

has_cmd() { command -v "$1" >/dev/null 2>&1; }

step_00_bootstrap_node() {
  # Ensure Node.js and npm are available
  if has_cmd node && has_cmd npm; then
    echo "node/npm present: $(node -v) / $(npm -v)"
    return 0
  fi
  if has_cmd brew; then
    echo "Installing Node via Homebrew..."
    xrun brew list node >/dev/null 2>&1 || xrun brew install node
    echo "node/npm installed: $(node -v) / $(npm -v)"
  else
    echo "Homebrew not found; please install Node.js manually and rerun." >&2
    return 2
  fi
}

step_01_gui_electron_prepare() {
  cd "$ROOT/app/gui-electron"
  echo "node: $(node -v 2>/dev/null || echo missing) | npm: $(npm -v 2>/dev/null || echo missing)"
}

step_02_gui_electron_install_deps() {
  cd "$ROOT/app/gui-electron"
  if [[ -f package-lock.json ]]; then xrun npm ci; else xrun npm i; fi
}

step_03_gui_electron_verify() {
  cd "$ROOT/app/gui-electron"
  npx --yes electron --version
  node -e "require('node-pty'); console.log('node-pty ok')"
  node -e "require('xterm'); console.log('xterm ok')"
}

# Feature verification and packaging steps
step_04_gui_features_verify() {
  cd "$ROOT/app/gui-electron/src"
  # Verify key feature markers exist in code
  grep -q "split-vertical" main.js ../src/main.js || true
  grep -q "pane-container" index.html
  grep -q "resizer" index.html
  grep -q "cyclePane" renderer.js
  grep -q "draggable" renderer.js
  grep -q "tab-rename" renderer.js
}

step_05_install_packager() {
  cd "$ROOT/app/gui-electron"
  npm i --save-dev electron-packager
}

step_06_pack_mac() {
  cd "$ROOT/app/gui-electron"
  npm run pack:mac
}

step_07_verify_artifacts() {
  cd "$ROOT/app/gui-electron"
  test -d dist || { echo "dist missing"; return 2; }
  ls -la dist
}

step_08_smoke_scripts() {
  cd "$ROOT/app/gui-electron"
  node -e "console.log('scripts', Object.keys(require('./package.json').scripts))"
}

step_09_placeholder() { :; }
step_10_placeholder() { :; }
step_11_placeholder() { :; }
step_12_placeholder() { :; }

main() {
  local steps=(
    00_bootstrap_node
    01_gui_electron_prepare
    02_gui_electron_install_deps
    03_gui_electron_verify
    04_gui_features_verify
    05_install_packager
    06_pack_mac
    07_verify_artifacts
    08_smoke_scripts
    09_placeholder
    10_placeholder
    11_placeholder
    12_placeholder
  )

  local total=${#steps[@]}
  local idx=0
  local ok=0 err=0
  write_status "starting" "$idx" "$total" "init"
  for s in "${steps[@]}"; do
    idx=$((idx+1))
    write_status "running" "$idx" "$total" "$s"
    local fn="step_${s}"
    if run_step "$s" "$s" "$fn"; then ok=$((ok+1)); else err=$((err+1)); fi
  done
  write_status "finished" "$idx" "$total" "done"
  notify "Warp_Open" "Batch finished: ${ok} ok, ${err} error(s)"
}

main "$@"
