#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== deps =="
npm ci || npm install --no-audit --no-fund --legacy-peer-deps
npx electron-rebuild -f -w node-pty
echo "== lint/typecheck/tests (best-effort) =="
npm run ci
echo "== smoke summary =="
./scripts/smoke_summary.sh || true