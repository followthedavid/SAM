#!/bin/bash
# SAM Health Monitor - Quick verification without screenshots
# Usage: ./sam_health.sh [test|watch|fix]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SAM_APP="/Applications/SAM.app"
SAM_DEV="/Users/davidquinton/ReverseLab/SAM/warp_tauri/src-tauri/target/release/bundle/macos/SAM.app"
ROUTING_LOG="/tmp/sam_routing.log"
HEALTH_LOG="/tmp/sam_health.log"

log() { echo -e "$1" | tee -a "$HEALTH_LOG"; }
ok() { log "${GREEN}✓${NC} $1"; }
fail() { log "${RED}✗${NC} $1"; }
warn() { log "${YELLOW}!${NC} $1"; }

# Check 1: Process running
check_process() {
    if pgrep -f "SAM.app/Contents/MacOS/SAM" > /dev/null; then
        SAM_PID=$(pgrep -f "SAM.app/Contents/MacOS/SAM")
        ok "SAM running (PID: $SAM_PID)"
        return 0
    else
        fail "SAM not running"
        return 1
    fi
}

# Check 2: Window exists and has size
check_window() {
    local info=$(osascript -e 'tell application "System Events" to tell process "SAM" to if (count of windows) > 0 then return (size of window 1) as string' 2>/dev/null || echo "")
    if [[ -n "$info" && "$info" != *"0, 0"* ]]; then
        ok "Window visible ($info)"
        return 0
    else
        fail "No window or zero size"
        return 1
    fi
}

# Check 3: WebKit loaded (check for web content process)
check_webkit() {
    if pgrep -f "SAM.*Web Content" > /dev/null 2>&1 || pgrep -f "com.apple.WebKit" > /dev/null 2>&1; then
        ok "WebKit renderer active"
        return 0
    else
        # Alternative: check if window is responding
        local resp=$(osascript -e 'tell application "SAM" to get name' 2>/dev/null || echo "")
        if [[ -n "$resp" ]]; then
            ok "App responding"
            return 0
        fi
        fail "WebKit not detected"
        return 1
    fi
}

# Check 4: Verify routing log has recent activity
check_routing() {
    if [[ -f "$ROUTING_LOG" ]]; then
        local age=$(( $(date +%s) - $(stat -f %m "$ROUTING_LOG") ))
        local last_path=$(grep -o 'Path: [A-Za-z]*' "$ROUTING_LOG" | tail -1 | cut -d' ' -f2)
        local last_input=$(grep -o 'Raw: "[^"]*"' "$ROUTING_LOG" | tail -1)

        if [[ $age -lt 300 ]]; then  # Updated in last 5 min
            ok "Routing active: $last_path ($last_input)"
            return 0
        else
            warn "Routing stale (${age}s ago): $last_path"
            return 0  # Not a failure, just info
        fi
    else
        warn "No routing log yet - send a message to test"
        return 0  # Not a failure on fresh start
    fi
}

# Check 5: Direct IPC test via curl to dev server (if running)
check_ipc() {
    # Check if Tauri dev server is accessible
    if curl -s --max-time 2 http://localhost:1420 > /dev/null 2>&1; then
        ok "Dev server responding"
        return 0
    fi
    # In production mode, just verify process is healthy
    if kill -0 $(pgrep -f "SAM.app/Contents/MacOS/SAM") 2>/dev/null; then
        ok "Process healthy"
        return 0
    fi
    fail "IPC check failed"
    return 1
}

# Check 5: Binary freshness
check_binary() {
    local app_bin="$SAM_APP/Contents/MacOS/SAM"
    local dev_bin="$SAM_DEV/Contents/MacOS/SAM"

    if [[ -f "$dev_bin" ]]; then
        local app_time=$(stat -f %m "$app_bin" 2>/dev/null || echo 0)
        local dev_time=$(stat -f %m "$dev_bin" 2>/dev/null || echo 0)

        if [[ $dev_time -gt $app_time ]]; then
            warn "Dev binary newer than installed"
            return 1
        fi
    fi
    ok "Binary up to date"
    return 0
}

# Quick health check (no routing test)
quick_check() {
    local failed=0
    check_process || failed=1
    check_window || failed=1
    check_binary || ((failed++)) || true
    return $failed
}

# Full health check including routing
full_check() {
    echo "=== SAM Health $(date +%H:%M:%S) ===" | tee "$HEALTH_LOG"
    local failed=0

    check_process || failed=1
    check_window || failed=1
    check_ipc || ((failed++)) || true
    check_binary || ((failed++)) || true
    check_routing || true  # Info only

    echo ""
    if [[ $failed -eq 0 ]]; then
        ok "HEALTHY"
    else
        fail "$failed critical check(s) failed"
    fi
    return $failed
}

# Auto-fix common issues
auto_fix() {
    echo "=== SAM Auto-Fix ===" | tee "$HEALTH_LOG"

    # Kill if running
    pkill -9 -f "SAM.app" 2>/dev/null && warn "Killed existing SAM" || true
    sleep 1

    # Check if dev binary is newer
    local app_bin="$SAM_APP/Contents/MacOS/SAM"
    local dev_bin="$SAM_DEV/Contents/MacOS/SAM"

    if [[ -f "$dev_bin" ]]; then
        local app_time=$(stat -f %m "$app_bin" 2>/dev/null || echo 0)
        local dev_time=$(stat -f %m "$dev_bin" 2>/dev/null || echo 0)

        if [[ $dev_time -gt $app_time ]]; then
            warn "Installing newer dev binary..."
            rm -rf "$SAM_APP"
            cp -R "$SAM_DEV" "$SAM_APP"
            ok "Installed new binary"
        fi
    fi

    # Start SAM
    open "$SAM_APP"
    sleep 3

    # Verify
    if quick_check; then
        ok "SAM recovered"
        return 0
    else
        fail "Auto-fix failed"
        return 1
    fi
}

# Watch mode - continuous monitoring
watch_mode() {
    echo "Watching SAM health (Ctrl+C to stop)..."
    while true; do
        if ! quick_check > /dev/null 2>&1; then
            echo ""
            warn "Health check failed at $(date +%H:%M:%S)"
            auto_fix
        fi
        sleep 10
    done
}

# Main
# Run Rust routing tests directly
test_routing() {
    echo "=== Testing Routing Logic ==="
    cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/src-tauri
    cargo test test_daily_brief_routing -- --nocapture 2>&1 | grep -E "test.*ok|test.*FAILED|Routing:"
}

# Rebuild and restart SAM
rebuild() {
    echo "=== Rebuilding SAM ==="
    pkill -9 -f "SAM.app" 2>/dev/null || true
    cd /Users/davidquinton/ReverseLab/SAM/warp_tauri
    npm run tauri build 2>&1 | tail -5
    rm -rf "$SAM_APP"
    cp -R "$SAM_DEV" "$SAM_APP"
    open "$SAM_APP"
    sleep 3
    quick_check
}

case "${1:-test}" in
    q|quick) quick_check ;;
    t|test|full) full_check ;;
    f|fix) auto_fix ;;
    w|watch) watch_mode ;;
    r|route) test_routing ;;
    b|build|rebuild) rebuild ;;
    *) echo "Usage: $0 [q]uick|[t]est|[f]ix|[w]atch|[r]oute|[b]uild" ;;
esac
