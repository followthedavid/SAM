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
