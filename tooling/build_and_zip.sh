#!/usr/bin/env bash
# tooling/build_and_zip.sh
# Build everything and produce Warp_Open_<timestamp>.zip

set -euo pipefail

ROOT_DIR=$(pwd)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ZIP_NAME="Warp_Open_${TIMESTAMP}.zip"
LONG_SCROLL_LINES=50000

echo "=== Step 1: Build Rust core (release) ==="
cd warp_core
cargo build --release
cd "$ROOT_DIR"

echo "=== Step 2: Generate long scroll fixture ==="
python3 tooling/generate_long_scroll.py $LONG_SCROLL_LINES

echo "=== Step 3: Install Playwright (optional) ==="
if [ -d ui-tests ]; then
  cd ui-tests
  npm ci || true
  npx playwright install --with-deps || true
  cd "$ROOT_DIR"
fi

echo "=== Step 4: Build web UI (optional) ==="
if [ -d app/gui-electron ]; then
  cd app/gui-electron
  npm ci || true
  npm run build || true
  cd "$ROOT_DIR"
fi

echo "=== Step 5: Create zip archive ==="
zip -r "$ZIP_NAME" . \
    -x "*.git*" \
    -x "warp_core/target/debug/*" \
    -x "node_modules/*" \
    -x "ui-tests/node_modules/*" \
    -x "app/gui-electron/node_modules/*"

echo "✅ Build + Zip complete: $ZIP_NAME"
