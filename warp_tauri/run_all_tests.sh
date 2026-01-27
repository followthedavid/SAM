#!/usr/bin/env bash
#
# SAM Comprehensive Test Runner
# Runs all tests headlessly in background with full logging
#
# Usage:
#   ./run_all_tests.sh           # Run all tests
#   ./run_all_tests.sh quick     # Quick tests only (no E2E)
#   ./run_all_tests.sh ui        # UI tests only
#   ./run_all_tests.sh model     # Model/API tests only
#   ./run_all_tests.sh rust      # Rust tests only
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/test_run_$TIMESTAMP.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

header() {
    log ""
    log "${BLUE}════════════════════════════════════════════════════════════${NC}"
    log "${BLUE}  $1${NC}"
    log "${BLUE}════════════════════════════════════════════════════════════${NC}"
    log ""
}

success() {
    log "${GREEN}✅ $1${NC}"
}

warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

error() {
    log "${RED}❌ $1${NC}"
}

# Results tracking (compatible with bash 3.x)
TEST_RESULTS=""
TOTAL_PASSED=0
TOTAL_FAILED=0

run_test() {
    local name="$1"
    local command="$2"
    local timeout_secs="${3:-300}"

    log "\n${YELLOW}Running: $name${NC}"
    log "Command: $command"
    log "Timeout: ${timeout_secs}s"
    log "---"

    local start_time=$(date +%s)

    # Use gtimeout on macOS if available, otherwise use perl
    if command -v gtimeout &> /dev/null; then
        gtimeout "$timeout_secs" bash -c "$command" >> "$LOG_FILE" 2>&1
        local exit_code=$?
    else
        # Fallback without timeout
        bash -c "$command" >> "$LOG_FILE" 2>&1
        local exit_code=$?
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $exit_code -eq 0 ]; then
        success "$name completed in ${duration}s"
        TEST_RESULTS="${TEST_RESULTS}PASS:${name}\n"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
        return 0
    else
        error "$name failed (exit code: $exit_code, duration: ${duration}s)"
        TEST_RESULTS="${TEST_RESULTS}FAIL:${name}\n"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        return 1
    fi
}

# Pre-flight checks
preflight_checks() {
    header "PRE-FLIGHT CHECKS"

    # Check Ollama
    log "Checking Ollama..."
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        success "Ollama is running"
    else
        error "Ollama not running!"
        log "Starting Ollama..."
        ollama serve &
        sleep 5
    fi

    # Check loaded model
    log "Checking loaded model..."
    local loaded=$(curl -s http://localhost:11434/api/ps | grep -o '"name":"[^"]*"' | head -1)
    if [ -n "$loaded" ]; then
        log "Currently loaded: $loaded"
    else
        warning "No model loaded - will load on first request"
    fi

    # Check sam-trained availability
    log "Checking sam-trained model..."
    if curl -s http://localhost:11434/api/tags | grep -q "sam-trained"; then
        success "sam-trained model available"
    else
        error "sam-trained model not found!"
        return 1
    fi

    # Check Node.js
    log "Checking Node.js..."
    if command -v node &> /dev/null; then
        success "Node.js: $(node --version)"
    else
        error "Node.js not found!"
        return 1
    fi

    # Check npm dependencies
    log "Checking npm dependencies..."
    if [ -d "$SCRIPT_DIR/node_modules" ]; then
        success "node_modules exists"
    else
        warning "Installing dependencies..."
        cd "$SCRIPT_DIR" && npm install
    fi

    success "Pre-flight checks passed"
}

# Model/API Tests
run_model_tests() {
    header "MODEL & API TESTS"
    cd "$SCRIPT_DIR"

    run_test "Ollama Connection" "curl -s http://localhost:11434/api/tags | grep -q models"

    run_test "sam-trained Available" "curl -s http://localhost:11434/api/tags | grep -q sam-trained"

    run_test "sam-trained Response" "curl -s http://localhost:11434/api/generate -d '{\"model\":\"sam-trained:latest\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":5}}' | grep -q response"

    run_test "Chat API Format" "curl -s http://localhost:11434/api/chat -d '{\"model\":\"sam-trained:latest\",\"messages\":[{\"role\":\"user\",\"content\":\"test\"}],\"stream\":false,\"options\":{\"num_predict\":5}}' | grep -q message"

    run_test "Model API Tests (Vitest)" "npm test -- tests/sam-model-api.test.ts --reporter=verbose" 120
}

# Unit Tests
run_unit_tests() {
    header "UNIT TESTS (Vitest)"
    cd "$SCRIPT_DIR"

    run_test "Vue Component Tests" "npm test -- --reporter=verbose" 120
}

# Rust Tests
run_rust_tests() {
    header "RUST BACKEND TESTS"
    cd "$SCRIPT_DIR/src-tauri"

    run_test "Cargo Tests" "cargo test --release 2>&1" 300
}

# E2E UI Tests
run_ui_tests() {
    header "E2E UI TESTS (Playwright)"
    cd "$SCRIPT_DIR"

    # Check if dev server is running
    if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
        log "Starting dev server..."
        npm run dev &
        DEV_PID=$!
        sleep 10
    fi

    run_test "Playwright E2E Tests" "npx playwright test tests/ui/e2e/sam-full-test.spec.ts --reporter=list" 300

    # Cleanup dev server if we started it
    if [ -n "$DEV_PID" ]; then
        kill $DEV_PID 2>/dev/null || true
    fi
}

# Generate summary report
generate_report() {
    header "TEST RESULTS SUMMARY"

    log "\nTest Results:"
    log "─────────────────────────────────────────"
    echo -e "$TEST_RESULTS" | while IFS=: read -r result name; do
        if [ -n "$name" ]; then
            if [ "$result" = "PASS" ]; then
                log "${GREEN}✅ PASS${NC}  $name"
            else
                log "${RED}❌ FAIL${NC}  $name"
            fi
        fi
    done
    log "─────────────────────────────────────────"
    log ""
    log "Total Passed: ${GREEN}$TOTAL_PASSED${NC}"
    log "Total Failed: ${RED}$TOTAL_FAILED${NC}"
    log ""

    if [ $TOTAL_FAILED -eq 0 ]; then
        log "${GREEN}════════════════════════════════════════${NC}"
        log "${GREEN}  ALL TESTS PASSED! ✅${NC}"
        log "${GREEN}════════════════════════════════════════${NC}"
    else
        log "${RED}════════════════════════════════════════${NC}"
        log "${RED}  SOME TESTS FAILED! ❌${NC}"
        log "${RED}════════════════════════════════════════${NC}"
    fi

    log "\nFull log: $LOG_FILE"
    log "Screenshots: $LOG_DIR/*.png"
    log ""
}

# Main execution
main() {
    header "SAM COMPREHENSIVE TEST SUITE"
    log "Started: $(date)"
    log "Mode: ${1:-all}"
    log "Log file: $LOG_FILE"

    preflight_checks || exit 1

    case "${1:-all}" in
        quick)
            run_model_tests
            run_unit_tests
            ;;
        ui)
            run_ui_tests
            ;;
        model)
            run_model_tests
            ;;
        rust)
            run_rust_tests
            ;;
        unit)
            run_unit_tests
            ;;
        all)
            run_model_tests
            run_unit_tests
            run_rust_tests
            run_ui_tests
            ;;
        *)
            log "Usage: $0 [quick|ui|model|rust|unit|all]"
            exit 1
            ;;
    esac

    generate_report

    log "\nCompleted: $(date)"

    # Return appropriate exit code
    [ $TOTAL_FAILED -eq 0 ]
}

# Run in background mode if requested
if [ "$2" = "background" ]; then
    main "$1" > "$LOG_FILE" 2>&1 &
    echo "Tests running in background. PID: $!"
    echo "Log file: $LOG_FILE"
    echo "Monitor with: tail -f $LOG_FILE"
else
    main "$1"
fi
