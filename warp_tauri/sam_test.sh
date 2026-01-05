#!/bin/bash
# SAM Test Runner - Headless batch testing
# No windows, no screenshots, no keyboard hijacking

set -e

SAM_DIR="/Users/davidquinton/ReverseLab/SAM/warp_tauri"
BINARY="$SAM_DIR/src-tauri/target/release/sam-terminal"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                    ${YELLOW}SAM TEST RUNNER${NC}                           ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Test via direct Rust binary (if available)
test_via_binary() {
    if [[ -x "$BINARY" ]]; then
        echo -e "${GREEN}Using binary: $BINARY${NC}"
        "$BINARY" --test "$@"
    else
        echo -e "${YELLOW}Binary not found, using Tauri IPC${NC}"
        return 1
    fi
}

# Test via curl to local server (if SAM is running)
test_via_ipc() {
    # Check if SAM is running
    if ! pgrep -f "SAM.app" > /dev/null; then
        echo -e "${YELLOW}SAM not running. Starting...${NC}"
        open "$SAM_DIR/src-tauri/target/release/bundle/macos/SAM.app" &
        sleep 3
    fi

    # SAM uses Tauri's IPC, we need to invoke commands differently
    # For now, we'll use a Node.js script to invoke the commands
    node - <<'EOF'
const { spawn } = require('child_process');

// Since we can't directly call Tauri IPC from outside,
// we'll output instructions for manual testing
console.log(`
To run tests from within SAM:
1. Open SAM
2. Open the developer console (Cmd+Option+I)
3. Run: await window.__TAURI__.invoke('test_run_suite')
4. Or:  await window.__TAURI__.invoke('test_run_smoke')

Or use the test panel (coming soon).
`);
EOF
}

# Direct orchestrator test (no UI, pure backend)
test_orchestrator() {
    echo -e "${GREEN}Running direct orchestrator tests...${NC}"
    echo ""

    cd "$SAM_DIR/src-tauri"

    # Create a simple Rust test binary
    cat > /tmp/sam_test_runner.rs << 'RUSTEOF'
use std::process::Command;

fn main() {
    println!("SAM Orchestrator Direct Test");
    println!("============================");

    let tests = vec![
        ("git status", "Deterministic"),
        ("where is auth", "Embedding"),
        ("privately discuss", "MicroModel"),
        ("explicit content", "Sanitized"),
        ("daily brief", "Conversational"),
    ];

    for (input, expected) in tests {
        print!("Testing '{}' -> {} ... ", input, expected);
        // In a real implementation, this would call the orchestrator
        println!("PENDING (requires running SAM)");
    }
}
RUSTEOF

    echo -e "${YELLOW}Direct Rust tests require SAM backend. Use sam_test.sh ipc instead.${NC}"
}

# Live monitoring mode
monitor() {
    echo -e "${GREEN}Starting live test monitor...${NC}"
    echo "Press Ctrl+C to exit"
    echo ""

    while true; do
        clear
        print_header

        # Check SAM status
        if pgrep -f "SAM.app" > /dev/null; then
            echo -e "SAM Status: ${GREEN}RUNNING${NC}"
        else
            echo -e "SAM Status: ${RED}NOT RUNNING${NC}"
        fi

        # Check Ollama status
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "Ollama:     ${GREEN}RUNNING${NC}"
        else
            echo -e "Ollama:     ${RED}NOT RUNNING${NC}"
        fi

        # Check test status file
        if [[ -f /tmp/sam_test_results.json ]]; then
            echo ""
            echo "Last Test Results:"
            cat /tmp/sam_test_results.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'summary' in data:
        s = data['summary']
        print(f\"  Total: {s.get('total', '?')} | Passed: {s.get('passed', '?')} | Failed: {s.get('failed', '?')}\")
except:
    print('  No results yet')
"
        fi

        echo ""
        echo "Commands: q=quit, r=run tests, s=smoke test"
        read -t 5 -n 1 cmd || true

        case "$cmd" in
            q) exit 0 ;;
            r) run_full ;;
            s) run_smoke ;;
        esac
    done
}

# Run full test suite
run_full() {
    echo -e "${GREEN}Running full test suite...${NC}"

    # Check if we can run via Node/Tauri
    if command -v node &> /dev/null; then
        node "$SAM_DIR/test_runner.js" full 2>/dev/null || {
            echo -e "${YELLOW}Test runner not available. Building...${NC}"
            npm run build --prefix "$SAM_DIR" 2>/dev/null || true
        }
    else
        echo -e "${RED}Node.js not found. Install Node.js to run tests.${NC}"
    fi
}

# Run smoke test
run_smoke() {
    echo -e "${GREEN}Running smoke test...${NC}"
    if command -v node &> /dev/null; then
        node "$SAM_DIR/test_runner.js" smoke 2>/dev/null || echo "Smoke test runner not available"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  full      Run full test suite"
    echo "  smoke     Run quick smoke test"
    echo "  monitor   Live monitoring mode"
    echo "  ipc       Show IPC testing instructions"
    echo "  help      Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 full              # Run all tests"
    echo "  $0 smoke             # Quick health check"
    echo "  $0 monitor           # Live dashboard"
}

# Main
print_header

case "${1:-help}" in
    full)    run_full ;;
    smoke)   run_smoke ;;
    monitor) monitor ;;
    ipc)     test_via_ipc ;;
    help)    usage ;;
    *)       usage ;;
esac
