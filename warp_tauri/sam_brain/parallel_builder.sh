#!/usr/bin/env bash
# SAM Brain Parallel Builder
# Builds/tests all 20 projects in parallel - NO AI REQUIRED
#
# Usage: ./parallel_builder.sh [build|test|lint|all|status]

LOG_DIR="/Volumes/Plex/SSOT/build_logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Project definitions: name|path|type
PROJECTS="
sam-terminal|/Users/davidquinton/ReverseLab/SAM/warp_tauri|tauri
orchestrator|/Volumes/Plex/SSOT|python
rvc-voice|/Users/davidquinton/Projects/RVC/rvc-webui|python
comfyui|/Users/davidquinton/ai-studio/ComfyUI|python
motion-pipeline|/Users/davidquinton/Projects/motion-pipeline|python
topaz-parity|/Users/davidquinton/.topaz_parity|python
stash|/Users/davidquinton/stash|docker
animated-covers|/Users/davidquinton/ReverseLab/SAM/media/apple_music|python
account-automation|/Volumes/Plex/DevSymlinks/account_automation|python
warp-auto|/Users/davidquinton/ReverseLab/warp_auto|python
character-pipeline|/Users/davidquinton/Projects/character-pipeline|python
reverselab|/Users/davidquinton/ReverseLab|mixed
gridplayer|/Users/davidquinton/Projects/GridPlayer|python
"

run_action() {
    local name=$1
    local path=$2
    local type=$3
    local action=$4
    local log_file="$LOG_DIR/${name}_${action}_${TIMESTAMP}.log"

    if [[ ! -d "$path" ]]; then
        echo "[$name] SKIP - path not found"
        return 0
    fi

    cd "$path" 2>/dev/null || return 0
    echo "[$name] Running $action..."

    case "$action:$type" in
        build:tauri)
            npm run build >> "$log_file" 2>&1 && echo "[$name] ✓ build" || echo "[$name] ✗ build"
            ;;
        build:python)
            python3 -m py_compile *.py >> "$log_file" 2>&1 && echo "[$name] ✓ build" || echo "[$name] ✗ build"
            ;;
        build:node)
            npm run build >> "$log_file" 2>&1 && echo "[$name] ✓ build" || echo "[$name] ✗ build"
            ;;
        build:rust)
            cargo check >> "$log_file" 2>&1 && echo "[$name] ✓ build" || echo "[$name] ✗ build"
            ;;
        lint:python)
            python3 -m flake8 --select=E9,F63,F7,F82 . >> "$log_file" 2>&1 && echo "[$name] ✓ lint" || echo "[$name] ✗ lint"
            ;;
        lint:tauri|lint:rust)
            cargo clippy >> "$log_file" 2>&1 && echo "[$name] ✓ lint" || echo "[$name] ✗ lint"
            ;;
        lint:node)
            npx eslint . >> "$log_file" 2>&1 && echo "[$name] ✓ lint" || echo "[$name] ✗ lint"
            ;;
        test:python)
            python3 -m pytest --tb=short >> "$log_file" 2>&1 && echo "[$name] ✓ test" || echo "[$name] ✗ test"
            ;;
        test:tauri|test:rust)
            cargo test >> "$log_file" 2>&1 && echo "[$name] ✓ test" || echo "[$name] ✗ test"
            ;;
        test:node)
            npm test >> "$log_file" 2>&1 && echo "[$name] ✓ test" || echo "[$name] ✗ test"
            ;;
        *:docker|*:mixed|*:unity|*:unreal)
            echo "[$name] SKIP ($type)"
            ;;
        *)
            echo "[$name] No $action for $type"
            ;;
    esac
}

# Main
ACTION=${1:-build}
echo "=============================================="
echo "SAM Brain Parallel Builder"
echo "Action: $ACTION"
echo "Timestamp: $TIMESTAMP"
echo "=============================================="

case $ACTION in
    build|test|lint)
        echo "$PROJECTS" | while IFS='|' read -r name path type; do
            [[ -z "$name" ]] && continue
            run_action "$name" "$path" "$type" "$ACTION" &
        done
        wait
        ;;
    all)
        echo "--- LINT ---"
        $0 lint
        echo ""
        echo "--- BUILD ---"
        $0 build
        echo ""
        echo "--- TEST ---"
        $0 test
        ;;
    status)
        echo "Recent logs:"
        ls -lt "$LOG_DIR"/*.log 2>/dev/null | head -10
        echo ""
        echo "Errors in last run:"
        grep -l "error\|Error\|ERROR" "$LOG_DIR"/*_${TIMESTAMP}.log 2>/dev/null || echo "None"
        ;;
    *)
        echo "Usage: $0 [build|test|lint|all|status]"
        exit 1
        ;;
esac

echo ""
echo "Done! Logs: $LOG_DIR"
