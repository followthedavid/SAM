#!/bin/bash
# SAM Test Helper - Command-line testing utilities
#
# Usage:
#   ./sam_test.sh ping          - Check if debug server is running
#   ./sam_test.sh state         - Get app state
#   ./sam_test.sh ollama        - Get Ollama status
#   ./sam_test.sh warm          - Warm all models
#   ./sam_test.sh focus         - Bring SAM window to front
#   ./sam_test.sh click X Y     - Click at coordinates
#   ./sam_test.sh type "text"   - Type text into active element
#   ./sam_test.sh ax-dump       - Dump accessibility tree
#   ./sam_test.sh all           - Run all checks

DEBUG_PORT="${SAM_DEBUG_PORT:-9998}"
DEBUG_URL="http://localhost:${DEBUG_PORT}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_debug_server() {
    curl -s "${DEBUG_URL}/debug/ping" > /dev/null 2>&1
    return $?
}

cmd_ping() {
    echo -n "Debug server: "
    if check_debug_server; then
        echo -e "${GREEN}OK${NC}"
        curl -s "${DEBUG_URL}/debug/ping" | python3 -m json.tool 2>/dev/null || cat
    else
        echo -e "${RED}NOT RUNNING${NC}"
        echo "Start SAM app or check port ${DEBUG_PORT}"
        return 1
    fi
}

cmd_state() {
    if ! check_debug_server; then
        echo -e "${RED}Debug server not running${NC}"
        return 1
    fi
    echo "App State:"
    curl -s "${DEBUG_URL}/debug/state" | python3 -m json.tool 2>/dev/null || curl -s "${DEBUG_URL}/debug/state"
}

cmd_ollama() {
    if ! check_debug_server; then
        echo -e "${RED}Debug server not running${NC}"
        return 1
    fi
    echo "Ollama Status:"
    curl -s "${DEBUG_URL}/debug/ollama" | python3 -m json.tool 2>/dev/null || curl -s "${DEBUG_URL}/debug/ollama"
}

cmd_warm() {
    if ! check_debug_server; then
        echo -e "${RED}Debug server not running${NC}"
        return 1
    fi
    echo "Warming models..."
    curl -s -X POST "${DEBUG_URL}/debug/warm" | python3 -m json.tool 2>/dev/null || curl -s -X POST "${DEBUG_URL}/debug/warm"
}

cmd_focus() {
    osascript -e 'tell application "System Events" to tell process "SAM" to set frontmost to true' 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SAM window focused${NC}"
    else
        echo -e "${RED}Could not focus SAM window${NC}"
        return 1
    fi
}

cmd_click() {
    local x="${1:-0}"
    local y="${2:-0}"
    osascript <<EOF
tell application "System Events"
    tell process "SAM"
        set frontmost to true
        click at {${x}, ${y}}
    end tell
end tell
EOF
    echo "Clicked at (${x}, ${y})"
}

cmd_type() {
    local text="$1"
    osascript <<EOF
tell application "System Events"
    tell process "SAM"
        set frontmost to true
        keystroke "${text}"
    end tell
end tell
EOF
    echo "Typed: ${text}"
}

cmd_ax_dump() {
    echo "Accessibility Tree for SAM:"
    osascript <<'EOF'
tell application "System Events"
    tell process "SAM"
        set windowInfo to {}
        repeat with w in windows
            set windowData to {name of w, position of w, size of w}
            set end of windowInfo to windowData

            -- Try to get UI elements
            try
                set uiElements to entire contents of w
                repeat with elem in uiElements
                    try
                        set elemInfo to {class of elem, name of elem, role of elem}
                        set end of windowInfo to elemInfo
                    end try
                end repeat
            end try
        end repeat
        return windowInfo
    end tell
end tell
EOF
}

cmd_window_info() {
    osascript <<'EOF'
tell application "System Events"
    tell process "SAM"
        set windowList to {}
        repeat with w in windows
            set windowData to "Window: " & name of w & ", Position: " & (position of w as string) & ", Size: " & (size of w as string)
            set end of windowList to windowData
        end repeat
        return windowList
    end tell
end tell
EOF
}

cmd_all() {
    echo "========================================"
    echo "  SAM Test Report"
    echo "  $(date)"
    echo "========================================"
    echo ""

    echo "1. Debug Server"
    echo "----------------"
    cmd_ping
    echo ""

    echo "2. App State"
    echo "----------------"
    cmd_state 2>/dev/null || echo "  (unavailable)"
    echo ""

    echo "3. Ollama Status"
    echo "----------------"
    cmd_ollama 2>/dev/null || echo "  (unavailable)"
    echo ""

    echo "4. Window Info"
    echo "----------------"
    cmd_window_info 2>/dev/null || echo "  (no window)"
    echo ""

    echo "========================================"
}

# Main
case "${1:-help}" in
    ping)
        cmd_ping
        ;;
    state)
        cmd_state
        ;;
    ollama)
        cmd_ollama
        ;;
    warm)
        cmd_warm
        ;;
    focus)
        cmd_focus
        ;;
    click)
        cmd_click "$2" "$3"
        ;;
    type)
        cmd_type "$2"
        ;;
    ax-dump|ax)
        cmd_ax_dump
        ;;
    window|win)
        cmd_window_info
        ;;
    all)
        cmd_all
        ;;
    help|*)
        echo "SAM Test Helper"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  ping          Check if debug server is running"
        echo "  state         Get app state"
        echo "  ollama        Get Ollama status"
        echo "  warm          Warm all models"
        echo "  focus         Bring SAM window to front"
        echo "  click X Y     Click at coordinates"
        echo "  type \"text\"   Type text into active element"
        echo "  ax-dump       Dump accessibility tree"
        echo "  window        Get window info"
        echo "  all           Run all checks"
        echo ""
        echo "Environment:"
        echo "  SAM_DEBUG_PORT  Debug server port (default: 9998)"
        ;;
esac
