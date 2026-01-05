#!/bin/bash
# Perpetual Ladder - Direct Mode
# Runs Claude Code directly on projects without ChatGPT coordination
# Useful for testing and quick improvements

set -e

REGISTRY="$HOME/.sam/projects/registry.json"
LOGS="$HOME/.sam/logs"

mkdir -p "$LOGS"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

header() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# Get projects from registry
get_projects() {
    cat "$REGISTRY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data['projects']:
    if p['status'] in ['active', 'training']:
        print(f\"{p['id']}|{p['name']}|{p['path']}|{p['currentFocus']}|{p['priority']}\")
"
}

# Run Claude Code on a project
run_claude() {
    local project_path="$1"
    local task="$2"
    local project_name="$3"

    log "Running Claude Code on $project_name..."
    log "Task: $task"

    cd "$project_path"

    # Run claude with the task
    if claude -p "$task" 2>&1 | tee "$LOGS/claude_$(date +%Y%m%d_%H%M%S).log"; then
        success "Task completed"
        return 0
    else
        error "Task failed"
        return 1
    fi
}

# Quick health check on a project
health_check() {
    local project_path="$1"

    if [[ ! -d "$project_path" ]]; then
        echo "missing"
        return
    fi

    local indicators=""
    [[ -f "$project_path/package.json" ]] && indicators+="npm "
    [[ -f "$project_path/Cargo.toml" ]] && indicators+="rust "
    [[ -f "$project_path/requirements.txt" ]] && indicators+="python "
    [[ -d "$project_path/.git" ]] && indicators+="git "

    echo "${indicators:-unknown}"
}

# Main menu
show_menu() {
    header "PERPETUAL LADDER - Direct Mode"

    echo "📊 Projects:"
    echo ""

    local i=1
    while IFS='|' read -r id name path focus priority; do
        local health=$(health_check "$path")
        local status_icon="🟢"
        [[ "$health" == "missing" ]] && status_icon="🔴"

        echo "  $i) $status_icon $name (P$priority)"
        echo "     Focus: $focus"
        echo "     Health: $health"
        echo ""
        i=$((i + 1))
    done <<< "$(get_projects)"

    echo "  a) Run on ALL projects (round-robin)"
    echo "  s) Status check all projects"
    echo "  q) Quit"
    echo ""
}

# Interactive mode
interactive() {
    while true; do
        show_menu
        read -p "Select project (1-9, a, s, q): " choice

        case "$choice" in
            q|Q)
                echo "Goodbye!"
                exit 0
                ;;
            s|S)
                header "Status Check"
                while IFS='|' read -r id name path focus priority; do
                    echo -n "$name: "
                    if [[ -d "$path" ]]; then
                        cd "$path"
                        if [[ -d ".git" ]]; then
                            local changes=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
                            echo "✓ ($changes uncommitted changes)"
                        else
                            echo "✓ (not a git repo)"
                        fi
                    else
                        echo "✗ (path not found)"
                    fi
                done <<< "$(get_projects)"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            a|A)
                header "Running on ALL Projects"
                while IFS='|' read -r id name path focus priority; do
                    if [[ -d "$path" ]]; then
                        echo ""
                        log "Working on: $name"
                        run_claude "$path" "Review this project and make one small improvement. Focus on: $focus" "$name"
                        echo ""
                    fi
                done <<< "$(get_projects)"
                read -p "Press Enter to continue..."
                ;;
            [1-9])
                local project_data=$(get_projects | sed -n "${choice}p")
                if [[ -n "$project_data" ]]; then
                    IFS='|' read -r id name path focus priority <<< "$project_data"

                    header "Working on: $name"
                    echo "Current focus: $focus"
                    echo ""
                    read -p "Enter task (or press Enter for default): " task

                    if [[ -z "$task" ]]; then
                        task="Review this project and make one improvement. Focus on: $focus. Be specific about what you changed."
                    fi

                    run_claude "$path" "$task" "$name"
                    echo ""
                    read -p "Press Enter to continue..."
                else
                    error "Invalid selection"
                fi
                ;;
            *)
                error "Invalid choice"
                ;;
        esac
    done
}

# Single project mode
single_project() {
    local project_id="$1"
    local task="$2"

    local project_data=$(get_projects | grep "^$project_id|")

    if [[ -z "$project_data" ]]; then
        error "Project not found: $project_id"
        echo "Available projects:"
        get_projects | cut -d'|' -f1
        exit 1
    fi

    IFS='|' read -r id name path focus priority <<< "$project_data"

    header "Working on: $name"

    if [[ -z "$task" ]]; then
        task="Review this project and make one improvement. Focus on: $focus"
    fi

    run_claude "$path" "$task" "$name"
}

# CLI
case "${1:-}" in
    --help|-h)
        echo "Perpetual Ladder - Direct Mode"
        echo ""
        echo "Usage:"
        echo "  ./ladder_direct.sh                    # Interactive mode"
        echo "  ./ladder_direct.sh <project_id>       # Run on specific project"
        echo "  ./ladder_direct.sh <project_id> \"task\" # Run specific task"
        echo "  ./ladder_direct.sh --all              # Run on all projects"
        echo ""
        echo "Projects:"
        get_projects | while IFS='|' read -r id name path focus priority; do
            echo "  - $id: $name"
        done
        ;;
    --all|-a)
        header "Running on ALL Projects"
        while IFS='|' read -r id name path focus priority; do
            if [[ -d "$path" ]]; then
                echo ""
                log "Working on: $name"
                run_claude "$path" "Review this project and make one small improvement. Focus on: $focus" "$name"
            fi
        done <<< "$(get_projects)"
        ;;
    "")
        interactive
        ;;
    *)
        single_project "$1" "${2:-}"
        ;;
esac
