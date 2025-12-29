#!/usr/bin/env bash
# tooling/test_runner.sh
# Unified test runner for Warp_Open test suite

set -euo pipefail

MODE=${1:-all}

case "$MODE" in
  rust)
    echo "=== Running Rust tests ==="
    cd warp_core && cargo test
    ;;
  integration)
    echo "=== Running integration tests ==="
    python3 tests/integration/run_fullstack_test.py
    ;;
  malformed)
    echo "=== Running malformed stream test ==="
    python3 tests/integration/run_malformed_stream_test.py
    ;;
  partialutf8)
    echo "=== Running partial UTF-8 test ==="
    python3 tests/integration/run_partial_utf8_test.py
    ;;
  longscroll)
    echo "=== Running long scroll (stress) test ==="
    python3 tests/integration/run_long_scroll_test.py
    ;;
  overlapping)
    echo "=== Running overlapping OSC test ==="
    python3 tests/integration/run_overlapping_osc_test.py
    ;;
  cjk)
    echo "=== Running CJK UTF-8 test ==="
    python3 tests/integration/run_cjk_utf8_test.py
    ;;
  partialescape)
    echo "=== Running partial escape test ==="
    python3 tests/integration/run_partial_escape_test.py
    ;;
  all)
    echo "=== Running all tests ==="
    cd warp_core && cargo test && cd ..
    python3 tests/integration/run_fullstack_test.py
    python3 tests/integration/run_malformed_stream_test.py
    python3 tests/integration/run_partial_utf8_test.py
    python3 tests/integration/run_overlapping_osc_test.py
    python3 tests/integration/run_cjk_utf8_test.py
    python3 tests/integration/run_partial_escape_test.py
    python3 tests/integration/run_long_scroll_test.py
    echo "✅ All tests passed!"
    ;;
  *)
    echo "Usage: $0 {rust|integration|malformed|partialutf8|longscroll|overlapping|cjk|partialescape|all}"
    exit 1
    ;;
esac
