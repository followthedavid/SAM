#!/bin/bash
# =============================================================================
# SAM Bridge - Dual Claude Terminal Coordinator
# =============================================================================
# This script coordinates two Claude Code terminals working together.
# SAM acts as the bridge, routing tasks and maintaining context.
#
# Usage:
#   ./sam_bridge.sh                    # Start bridge + both terminals
#   ./sam_bridge.sh --left-only        # Start left terminal (builder)
#   ./sam_bridge.sh --right-only       # Start right terminal (reviewer)
#   ./sam_bridge.sh --status           # Check status
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRAIN_DIR="$SCRIPT_DIR/sam_brain"
STATE_DIR="$HOME/.sam/bridge"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() { echo -e "${GREEN}[SAM Bridge]${NC} $1"; }
warn() { echo -e "${YELLOW}[SAM Bridge]${NC} $1"; }
info() { echo -e "${CYAN}[SAM Bridge]${NC} $1"; }

mkdir -p "$STATE_DIR"

# =============================================================================
# Role Prompts (injected into Claude's context)
# =============================================================================

BUILDER_PROMPT='You are working as SAM'"'"'s BUILDER in a dual-terminal setup.

YOUR ROLE:
- Plan architecture and write code
- Implement features in Swift/SwiftUI
- Follow Apple HIG and best practices

COORDINATION:
- When code is ready for review, say: [HANDOFF:REVIEWER] <summary>
- When you need planning help, say: [REQUEST:PLANNER] <question>
- When you find a bug, say: [BUG:DEBUGGER] <description>

The REVIEWER terminal will see your handoffs and continue the work.
SAM orchestrates between you both.

Current project focus: '

REVIEWER_PROMPT='You are working as SAM'"'"'s REVIEWER in a dual-terminal setup.

YOUR ROLE:
- Review code for quality and security
- Suggest improvements with examples
- Approve or request changes

REVIEW FORMAT:
- CRITICAL: Must fix before merge
- MAJOR: Should fix
- MINOR: Nice to have

COORDINATION:
- When changes needed, say: [HANDOFF:BUILDER] <required changes>
- When approved, say: [APPROVED] <summary>
- When tests needed, say: [HANDOFF:TESTER] <what to test>

The BUILDER terminal will see your feedback and make changes.
SAM orchestrates between you both.

Current project focus: '

# =============================================================================
# Start Orchestrator
# =============================================================================
start_orchestrator() {
    log "Starting orchestrator..."

    local pid_file="$STATE_DIR/orchestrator.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Orchestrator already running (PID $pid)"
            return 0
        fi
    fi

    cd "$BRAIN_DIR"
    source .venv/bin/activate 2>/dev/null || true

    python3 multi_role_orchestrator.py server > "$STATE_DIR/orchestrator.log" 2>&1 &
    echo $! > "$pid_file"

    sleep 2

    if kill -0 $(cat "$pid_file") 2>/dev/null; then
        log "Orchestrator started ✓"
    else
        warn "Orchestrator may have failed to start. Check $STATE_DIR/orchestrator.log"
    fi
}

# =============================================================================
# Get Current Project Focus
# =============================================================================
get_project_focus() {
    python3 -c "
import json
from pathlib import Path
try:
    with open(Path.home() / '.sam/projects/registry.json') as f:
        data = json.load(f)
    active = [p for p in data.get('projects', []) if p.get('status') == 'active']
    if active:
        print(active[0].get('currentFocus', 'General development'))
    else:
        print('No active project')
except:
    print('General development')
" 2>/dev/null
}

# =============================================================================
# Launch Left Terminal (Builder)
# =============================================================================
launch_builder_terminal() {
    log "Launching BUILDER terminal (left)..."

    local focus=$(get_project_focus)
    local full_prompt="${BUILDER_PROMPT}${focus}"

    # Create prompt file for injection
    echo "$full_prompt" > "$STATE_DIR/builder_prompt.txt"

    osascript <<EOF
tell application "Terminal"
    activate

    -- Create new window
    do script "cd '$SCRIPT_DIR' && export SAM_ROLE='builder' && clear && echo '╔═══════════════════════════════════════════════════════════╗' && echo '║             SAM BUILDER TERMINAL                          ║' && echo '║  Role: Plan, architect, write code                        ║' && echo '╚═══════════════════════════════════════════════════════════╝' && echo '' && echo 'Focus: $focus' && echo '' && echo 'Starting Claude Code...' && echo '' && claude --dangerously-skip-permissions"

    -- Position left side
    set bounds of front window to {50, 50, 960, 1000}

    -- Style the window
    set current settings of front window to settings set "Pro"
end tell
EOF

    # Register with orchestrator
    sleep 3
    cd "$BRAIN_DIR"
    python3 multi_role_orchestrator.py register builder 2>/dev/null || true

    log "Builder terminal launched ✓"
}

# =============================================================================
# Launch Right Terminal (Reviewer)
# =============================================================================
launch_reviewer_terminal() {
    log "Launching REVIEWER terminal (right)..."

    local focus=$(get_project_focus)
    local full_prompt="${REVIEWER_PROMPT}${focus}"

    echo "$full_prompt" > "$STATE_DIR/reviewer_prompt.txt"

    osascript <<EOF
tell application "Terminal"
    -- Create new window
    do script "cd '$SCRIPT_DIR' && export SAM_ROLE='reviewer' && clear && echo '╔═══════════════════════════════════════════════════════════╗' && echo '║             SAM REVIEWER TERMINAL                         ║' && echo '║  Role: Review, improve, approve                           ║' && echo '╚═══════════════════════════════════════════════════════════╝' && echo '' && echo 'Focus: $focus' && echo '' && echo 'Starting Claude Code...' && echo '' && claude --dangerously-skip-permissions"

    -- Position right side
    set bounds of front window to {980, 50, 1890, 1000}

    -- Style the window
    set current settings of front window to settings set "Pro"
end tell
EOF

    sleep 3
    cd "$BRAIN_DIR"
    python3 multi_role_orchestrator.py register reviewer 2>/dev/null || true

    log "Reviewer terminal launched ✓"
}

# =============================================================================
# Show Status
# =============================================================================
show_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                  SAM BRIDGE STATUS                         ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Orchestrator
    local orch_pid=$(cat "$STATE_DIR/orchestrator.pid" 2>/dev/null)
    if [[ -n "$orch_pid" ]] && kill -0 "$orch_pid" 2>/dev/null; then
        echo -e "  Orchestrator:  ${GREEN}✓ Running (PID $orch_pid)${NC}"
    else
        echo -e "  Orchestrator:  ${YELLOW}○ Not running${NC}"
    fi

    # Get orchestrator status
    cd "$BRAIN_DIR" 2>/dev/null && {
        local status=$(python3 multi_role_orchestrator.py status 2>/dev/null)
        if [[ -n "$status" ]]; then
            echo ""
            echo "  Terminals:"
            echo "$status" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    terms = d.get('terminals', {})
    for tid, t in terms.items():
        status = '✓' if t.get('status') == 'active' else '○'
        print(f\"    {status} {t.get('role', 'unknown')}: {tid}\")
    tasks = d.get('tasks', {})
    print(f\"\\n  Tasks:\")
    print(f\"    Pending: {tasks.get('pending', 0)}\")
    print(f\"    In Progress: {tasks.get('in_progress', 0)}\")
    print(f\"    Completed: {tasks.get('completed_total', 0)}\")
except:
    pass
"
        fi
    }

    # Project
    local focus=$(get_project_focus)
    echo ""
    echo -e "  Project Focus: ${BLUE}$focus${NC}"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║          SAM BRIDGE - Dual Claude Coordinator             ║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    case "${1:-}" in
        --status|-s)
            show_status
            ;;
        --left-only|--builder)
            start_orchestrator
            launch_builder_terminal
            ;;
        --right-only|--reviewer)
            start_orchestrator
            launch_reviewer_terminal
            ;;
        --help|-h)
            echo "Usage: ./sam_bridge.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (none)         Start both terminals"
            echo "  --left-only    Start builder terminal only"
            echo "  --right-only   Start reviewer terminal only"
            echo "  --status       Show bridge status"
            echo ""
            echo "The bridge coordinates two Claude Code terminals:"
            echo "  LEFT:  Builder - writes code"
            echo "  RIGHT: Reviewer - reviews and approves"
            echo ""
            echo "SAM orchestrates handoffs between them."
            ;;
        *)
            # Start everything
            start_orchestrator
            sleep 1
            launch_builder_terminal
            sleep 2
            launch_reviewer_terminal

            echo ""
            log "Dual terminals launched!"
            echo ""
            echo -e "  ${GREEN}LEFT${NC}  (Builder):  Plans and writes code"
            echo -e "  ${BLUE}RIGHT${NC} (Reviewer): Reviews and approves"
            echo ""
            echo "SAM orchestrates handoffs between terminals."
            echo ""
            echo "Use these signals in your messages:"
            echo "  [HANDOFF:REVIEWER] <summary>  - Send to reviewer"
            echo "  [HANDOFF:BUILDER] <changes>   - Send back for fixes"
            echo "  [APPROVED]                    - Code approved"
            echo ""
            echo "Check status: ./sam_bridge.sh --status"
            echo ""
            ;;
    esac
}

main "$@"
