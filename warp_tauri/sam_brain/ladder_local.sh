#!/bin/bash
# SAM Brain Local Ladder - Uses fine-tuned MLX model for project coordination
# No external APIs required

set -e

# Configuration
MLX_SERVER="http://localhost:11435"
PROJECT_REGISTRY="$HOME/.sam/projects/registry.json"
LADDER_LOG="$HOME/.sam/ladder.log"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    local timestamp=$(date '+%H:%M:%S')
    echo -e "${BLUE}[${timestamp}]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LADDER_LOG"
}

query_sam_brain() {
    local prompt="$1"
    local max_tokens="${2:-300}"

    # Escape prompt for JSON
    local escaped_prompt=$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip())[1:-1])")

    response=$(curl -s "$MLX_SERVER/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"prompt\":\"$escaped_prompt\",\"options\":{\"num_predict\":$max_tokens}}" \
        2>/dev/null)

    if [ -n "$response" ]; then
        echo "$response" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('response','Error: no response'))" 2>/dev/null || echo "Error parsing response"
    else
        echo "Error: No response from server"
    fi
}

check_mlx_server() {
    if ! curl -s "$MLX_SERVER/health" > /dev/null 2>&1; then
        log "${YELLOW}MLX server not running, starting...${NC}"
        source ~/.sam/mlx_venv/bin/activate
        nohup python3 ~/ReverseLab/SAM/warp_tauri/sam_brain/mlx_server.py > /tmp/sam_mlx_server.log 2>&1 &
        sleep 30  # Wait for model to load

        if ! curl -s "$MLX_SERVER/health" > /dev/null 2>&1; then
            log "Failed to start MLX server"
            exit 1
        fi
    fi
}

get_projects() {
    if [ -f "$PROJECT_REGISTRY" ]; then
        python3 -c "
import json
with open('$PROJECT_REGISTRY') as f:
    data = json.load(f)
for p in data.get('projects', []):
    print(f\"{p['id']}|{p['name']}|{p.get('path', '')}|{p.get('priority', 99)}\")
" 2>/dev/null
    fi
}

analyze_project() {
    local project_id="$1"
    local project_path="$2"

    # Get project status
    local status=""
    if [ -d "$project_path" ]; then
        cd "$project_path" 2>/dev/null || return

        # Check for common files
        [ -f "package.json" ] && status="Node.js project"
        [ -f "Cargo.toml" ] && status="Rust project"
        [ -f "requirements.txt" ] && status="Python project"
        [ -f "pyproject.toml" ] && status="Python project (pyproject)"

        # Check git status
        if [ -d ".git" ]; then
            local changes=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
            status="$status, $changes uncommitted changes"
        fi
    else
        status="Directory not found"
    fi

    echo "$status"
}

get_next_task() {
    local project_id="$1"
    local context="$2"

    local prompt="You are SAM Brain coordinating project development. Given this project context:
Project: $project_id
Status: $context

What is the most important next task for this project? Be specific and actionable. One sentence only."

    query_sam_brain "$prompt" 100
}

main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  SAM Brain Local Ladder"
    echo "  Using fine-tuned MLX model (GPU accelerated)"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Check MLX server
    check_mlx_server
    log "${GREEN}MLX server ready${NC}"

    # Load projects
    echo ""
    log "Loading project registry..."

    projects=$(get_projects)
    if [ -z "$projects" ]; then
        log "No projects found in registry"
        echo ""
        echo "Create projects with:"
        echo "  cat > ~/.sam/projects/registry.json << 'EOF'"
        echo "  {\"projects\": [{\"id\": \"myproject\", \"name\": \"My Project\", \"path\": \"/path/to/project\"}]}"
        echo "  EOF"
        exit 1
    fi

    echo ""
    echo "Projects:"
    echo "$projects" | while IFS='|' read -r id name path priority; do
        echo "  [$priority] $name ($id)"
    done

    # Analyze each project and get next tasks
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Project Analysis"
    echo "═══════════════════════════════════════════════════════════"

    echo "$projects" | while IFS='|' read -r id name path priority; do
        if [ -n "$path" ] && [ -d "$path" ]; then
            echo ""
            echo "${GREEN}[$id]${NC} $name"

            # Analyze
            status=$(analyze_project "$id" "$path")
            echo "  Status: $status"

            # Get next task from SAM Brain
            task=$(get_next_task "$id" "$status")
            echo "  ${YELLOW}Next:${NC} $task"
        fi
    done

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Ladder complete. Tasks logged to: $LADDER_LOG"
    echo "═══════════════════════════════════════════════════════════"
}

# Run if called directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
