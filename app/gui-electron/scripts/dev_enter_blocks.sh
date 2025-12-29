#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export WARP_OPEN_ENABLE_BLOCKS=1
export WARP_OPEN_BLOCKS_MODE=enter   # force Enter-heuristic boundaries
npm run dev
