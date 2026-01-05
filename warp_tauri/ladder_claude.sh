#!/bin/bash
# Perpetual Ladder - Claude Code Only
# Uses Claude Code CLI directly - no Ollama dependency
# Fast, reliable, uses your Claude subscription

set -e

REGISTRY="$HOME/.sam/projects/registry.json"
LOGS="$HOME/.sam/logs"
STATE="$HOME/.sam/state/ladder_claude.json"

mkdir -p "$LOGS" "$(dirname $STATE)"

# Initialize state if needed
if [[ ! -f "$STATE" ]]; then
    echo '{"completed":[],"iteration":0}' > "$STATE"
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }

# Get active projects
get_projects() {
    python3 << 'PYEOF'
import json
with open("$HOME/.sam/projects/registry.json".replace("$HOME", __import__("os").environ["HOME"])) as f:
    data = json.load(f)
for p in sorted(data['projects'], key=lambda x: x['priority']):
    if p['status'] in ['active', 'training']:
        print(f"{p['id']}|{p['name']}|{p['path']}|{p['currentFocus']}|{p['priority']}")
PYEOF
}

# Run Claude Code on a project
improve_project() {
    local id="$1"
    local name="$2"
    local path="$3"
    local focus="$4"

    log "🔨 Working on: $name"
    log "   Focus: $focus"
    log "   Path: $path"
    echo ""

    if [[ ! -d "$path" ]]; then
        log "⚠️  Path not found, skipping"
        return 1
    fi

    # Build a focused task
    local task="Review this project and make ONE concrete improvement.

Current focus: $focus

Guidelines:
- Make a real, useful change (not just adding comments)
- Fix a bug, improve performance, or add a small feature
- Run tests if they exist
- Summarize what you changed in 1-2 sentences at the end

If you can't make an improvement, explain why and suggest what's needed."

    # Run Claude Code
    cd "$path"
    local log_file="$LOGS/ladder_${id}_$(date +%Y%m%d_%H%M%S).log"

    echo "Running claude -p ..."
    if timeout 300 claude -p "$task" 2>&1 | tee "$log_file"; then
        success "Completed work on $name"

        # Update state
        python3 << PYEOF
import json
from datetime import datetime
state_path = "$STATE"
with open(state_path) as f:
    state = json.load(f)
state['completed'].append({
    "project": "$name",
    "timestamp": datetime.now().isoformat(),
    "log": "$log_file"
})
state['completed'] = state['completed'][-50:]  # Keep last 50
state['iteration'] += 1
with open(state_path, 'w') as f:
    json.dump(state, f, indent=2)
PYEOF
        return 0
    else
    
        log "⚠️  Claude Code returned non-zero"
        return 1
    fi
}

# Show current status
show_status() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  PERPETUAL LADDER STATUS${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""

    local iteration=$(python3 -c "import json; print(json.load(open('$STATE'))['iteration'])" 2>/dev/null || echo "0")
    echo "Total iterations: $iteration"
    echo ""

    echo "📊 Projects (by priority):"
    echo ""
    get_projects | while IFS='|' read -r id name path focus priority; do
        local status="🟢"
        [[ ! -d "$path" ]] && status="🔴"
        echo "  P$priority $status $name"
        echo "      Focus: $focus"
    done

    echo ""
    echo "Recent completions:"
    python3 << 'PYEOF'
import json
try:
    with open("$STATE".replace("$STATE", __import__("os").path.expandvars("$STATE"))) as f:
        state = json.load(f)
    for item in state.get('completed', [])[-5:]:
        print(f"  ✓ {item['project']} ({item['timestamp'][:10]})")
except:
    print("  (none)")
PYEOF
    echo ""
}

# Run one iteration on each project
run_all() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  PERPETUAL LADDER - Full Run${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""

    local total=0
    local success_count=0

    get_projects | while IFS='|' read -r id name path focus priority; do
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        if improve_project "$id" "$name" "$path" "$focus"; then
            ((success_count++)) || true
        fi
        ((total++)) || true
        echo ""
    done

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  Run complete"
    echo "═══════════════════════════════════════════════════"
}

# Run on single project
run_single() {
    local target_id="$1"
    local custom_task="$2"

    get_projects | while IFS='|' read -r id name path focus priority; do
        if [[ "$id" == "$target_id" ]] || [[ "$name" == *"$target_id"* ]]; then
            echo ""
            echo "═══════════════════════════════════════════════════"
            echo "  Working on: $name"
            echo "═══════════════════════════════════════════════════"
            echo ""

            if [[ -n "$custom_task" ]]; then
                cd "$path"
                claude -p "$custom_task"
            else
    
                improve_project "$id" "$name" "$path" "$focus"
            fi
            exit 0
        fi
    done

    echo "Project not found: $target_id"
    echo ""
    echo "Available projects:"
    get_projects | cut -d'|' -f1,2
}

# Continuous mode
run_continuous() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  PERPETUAL LADDER - Continuous Mode${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Press Ctrl+C to stop"
    echo ""

    while true; do
        run_all
        log "Sleeping 5 minutes before next round..."
        sleep 300
    done
}

# CLI
case "${1:-}" in
    --help|-h)
        echo "Perpetual Ladder - Claude Code Edition"
        echo ""
        echo "Usage:"
        echo "  ./ladder_claude.sh                     # Run once on all projects"
        echo "  ./ladder_claude.sh <project>           # Run on specific project"
        echo "  ./ladder_claude.sh <project> \"task\"    # Run custom task"
        echo "  ./ladder_claude.sh --continuous        # Run forever"
        echo "  ./ladder_claude.sh --status            # Show status"
        echo ""
        echo "Projects:"
        get_projects | while IFS='|' read -r id name path focus priority; do
            echo "  - $id: $name (P$priority)"
        done
        ;;
    --status|-s)
        show_status
        ;;
    --continuous|-c)
        run_continuous
        ;;
    "")
        run_all
        ;;
    *)
        run_single "$1" "${2:-}"
        ;;
esac
