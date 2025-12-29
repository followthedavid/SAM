#!/usr/bin/env bash
# scripts/run_ci_local.sh
# Mirrors CI steps locally for debugging

set -euo pipefail

echo "=== Running CI locally ==="

echo "[1/6] Building Rust in release..."
( cd warp_core && cargo build --release )

echo "[2/6] Running Rust tests..."
( cd warp_core && cargo test --all --verbose )

echo "[3/6] Generating long scroll fixture..."
python3 tooling/generate_long_scroll.py 20000

echo "[4/6] Running integration: normal..."
python3 tests/integration/run_fullstack_test.py

echo "[5/6] Running integration: edge cases..."
python3 tests/integration/run_malformed_stream_test.py
python3 tests/integration/run_partial_utf8_test.py
python3 tests/integration/run_overlapping_osc_test.py
python3 tests/integration/run_cjk_utf8_test.py
python3 tests/integration/run_partial_escape_test.py

echo "[6/6] Running integration: longscroll..."
python3 tests/integration/run_long_scroll_test.py

echo "=== CI local run finished OK ==="
