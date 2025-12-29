#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/ReverseLab/Warp_Open/app/gui-electron"
BUNDLE_DIR="$APP_DIR/dist/Warp_Open-darwin-arm64/Warp_Open.app"
APP_EXE="$BUNDLE_DIR/Contents/MacOS/Warp_Open"
SESS_DIR="$HOME/.warp_open/sessions"

log() { printf "\n\033[1m%s\033[0m\n" "$*"; }

fail() {
  echo "❌ $*"
  exit 1
}

ok() {
  echo "✅ $*"
}

# --- 0) Basic sanity
[ -d "$APP_DIR" ] || fail "Missing app dir: $APP_DIR"
cd "$APP_DIR"

# --- 1) Dev-side health: rebuild + smoke (proves ABI & PTY)
log "1) Dev health: rebuild node-pty and run headless smoke"
npm run rebuild:pty >/dev/null 2>&1 || true
WARP_OPEN_ENABLE_SMOKE=1 npx electron . >/dev/null 2>&1 || true

[ -d "$SESS_DIR" ] || fail "No session dir created at $SESS_DIR"
LOG="$(ls -t "$SESS_DIR"/session-*.jsonl 2>/dev/null | head -1 || true)"
[ -n "${LOG:-}" ] || fail "No session logs found after dev smoke"

if grep -q '"type":"smoke:start"' "$LOG" \
  && grep -q '"type":"pty:start"' "$LOG" \
  && grep -q '"type":"pty:exit"' "$LOG" \
  && grep -q '"type":"smoke:done"' "$LOG"; then
  ok "Dev smoke log complete: $LOG"
else
  fail "Dev smoke log missing expected markers. See: $LOG"
fi

# --- 2) Bundle presence
log "2) Check packaged app bundle exists"
[ -x "$APP_EXE" ] || fail "Bundle missing or not executable: $APP_EXE"
ok "Found bundle: $BUNDLE_DIR"

# --- 3) Native module location check (asar vs no-asar)
log "3) Verify node-pty native binary is outside app.asar"
UNPACKED_PTY="$BUNDLE_DIR/Contents/Resources/app.asar.unpacked/node_modules/node-pty/build/Release/pty.node"
PLAIN_PTY="$BUNDLE_DIR/Contents/Resources/app/node_modules/node-pty/build/Release/pty.node"

if [ -f "$UNPACKED_PTY" ]; then
  ok "Found unpacked pty.node (asar mode): $UNPACKED_PTY"
elif [ -f "$PLAIN_PTY" ]; then
  ok "Found plain pty.node (no-asar mode): $PLAIN_PTY"
else
  fail "Could not find pty.node in unpacked or plain locations."
fi

# --- 4) Packaged smoke: run the .app executable with smoke env
log "4) Run packaged app in headless smoke mode"
# Kill any existing instance that might hold the session file
pkill -f "$APP_EXE" >/dev/null 2>&1 || true

# Use the app binary directly so env vars are honored
WARP_OPEN_ENABLE_SMOKE=1 "$APP_EXE" >/dev/null 2>&1 || true

# Newest log after packaged run
LOG2="$(ls -t "$SESS_DIR"/session-*.jsonl 2>/dev/null | head -1 || true)"
[ -n "${LOG2:-}" ] || fail "No session logs found after packaged smoke"

if grep -q '"type":"smoke:start"' "$LOG2" \
  && grep -q '"type":"pty:start"' "$LOG2" \
  && grep -q '"type":"pty:exit"' "$LOG2" \
  && grep -q '"type":"smoke:done"' "$LOG2"; then
  ok "Packaged smoke log complete: $LOG2"
else
  fail "Packaged smoke log missing expected markers. See: $LOG2"
fi

# --- 5) Quick interactive sanity: try to open the GUI (non-blocking)
log "5) Launch GUI (non-blocking). You can type: pwd, ls, echo hello"
open "$BUNDLE_DIR" || true

# --- 6) Summary
log "🎉 Final Validation PASSED"
echo "Dev log:       $LOG"
echo "Packaged log:  $LOG2"
echo "Bundle:        $BUNDLE_DIR"
