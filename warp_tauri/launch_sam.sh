#!/bin/bash
# =============================================================================
# SAM Unified Launcher - MLX Native Edition
# =============================================================================
# The ONE script to start SAM. No Ollama dependency.
#
# Usage:
#   ./launch_sam.sh              # Normal launch
#   ./launch_sam.sh --dev        # Development mode
#   ./launch_sam.sh --check      # Just check readiness
#   ./launch_sam.sh --daemon     # Start background services only
#   ./launch_sam.sh --dual       # Launch dual Claude terminals
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRAIN_DIR="$SCRIPT_DIR/sam_brain"
SCRAPER_DIR="$HOME/ReverseLab/SAM/scrapers"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[SAM]${NC} $1"; }
warn() { echo -e "${YELLOW}[SAM]${NC} $1"; }
error() { echo -e "${RED}[SAM]${NC} $1"; }
info() { echo -e "${CYAN}[SAM]${NC} $1"; }

# =============================================================================
# Step 1: Check MLX availability
# =============================================================================
check_mlx() {
    log "Checking MLX..."

    if python3 -c "import mlx" 2>/dev/null; then
        log "MLX available ✓"
        return 0
    fi

    error "MLX not installed!"
    echo "  Install with: pip install mlx mlx-lm"
    return 1
}

# =============================================================================
# Step 2: Check/Start SAM Brain Daemon
# =============================================================================
ensure_brain_daemon() {
    log "Checking SAM Brain daemon..."

    local pid_file="$BRAIN_DIR/.sam_daemon.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Brain daemon running (PID $pid) ✓"
            return 0
        fi
    fi

    warn "Brain daemon not running, starting..."

    cd "$BRAIN_DIR"
    source .venv/bin/activate 2>/dev/null || true

    nohup python3 -c "
from cognitive.unified_orchestrator import CognitiveOrchestrator
import time
orch = CognitiveOrchestrator()
print('SAM Brain initialized')
while True:
    time.sleep(60)
" > /tmp/sam_brain.log 2>&1 &

    echo $! > "$pid_file"
    log "Brain daemon started (PID $!) ✓"
}

# =============================================================================
# Step 3: Check/Start Scraper Daemon
# =============================================================================
ensure_scraper_daemon() {
    log "Checking Scraper daemon..."

    local pid_file="$HOME/.sam_scraper_daemon.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Scraper daemon running (PID $pid) ✓"
            return 0
        fi
    fi

    warn "Scraper daemon not running, starting..."

    cd "$SCRAPER_DIR"
    nohup python3 -m scraper_system.daemon --port 8089 > /tmp/sam_scraper.log 2>&1 &

    echo $! > "$pid_file"
    log "Scraper daemon started (PID $!) ✓"
}

# =============================================================================
# Step 4: Check/Start Training Pipeline
# =============================================================================
ensure_training_pipeline() {
    log "Checking Training pipeline..."

    local pid_file="$HOME/.sam_training_daemon.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Training pipeline running (PID $pid) ✓"
            return 0
        fi
    fi

    warn "Training pipeline not running, starting..."

    cd "$SCRAPER_DIR"
    nohup python3 -m scraper_system.training.continuous_pipeline > /tmp/sam_training.log 2>&1 &

    echo $! > "$pid_file"
    log "Training pipeline started (PID $!) ✓"
}

# =============================================================================
# Step 5: Launch Dual Claude Terminals
# =============================================================================
launch_dual_claude() {
    log "Launching dual Claude terminals..."

    # Create the orchestration script if it doesn't exist
    local orch_script="$SCRIPT_DIR/sam_orchestrator.sh"

    if [[ ! -f "$orch_script" ]]; then
        warn "Orchestrator script missing, creating..."
        # Will be created by the next step
    fi

    # Launch Terminal 1: Builder/Coder role
    osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$SCRIPT_DIR' && export SAM_ROLE='builder' && claude --dangerously-skip-permissions"
    set bounds of front window to {50, 50, 800, 900}
end tell
EOF

    sleep 2

    # Launch Terminal 2: Reviewer/Tester role
    osascript <<EOF
tell application "Terminal"
    do script "cd '$SCRIPT_DIR' && export SAM_ROLE='reviewer' && claude --dangerously-skip-permissions"
    set bounds of front window to {820, 50, 1570, 900}
end tell
EOF

    log "Dual terminals launched ✓"
    log "  Left (Builder): Plans and writes code"
    log "  Right (Reviewer): Reviews, tests, validates"
}

# =============================================================================
# Step 6: Launch Tauri App
# =============================================================================
launch_app() {
    local mode="${1:-prod}"

    if [[ "$mode" == "dev" ]]; then
        log "Launching SAM in development mode..."
        cd "$SCRIPT_DIR"
        npm run tauri:dev
    else
        log "Launching SAM..."

        local app_path="$SCRIPT_DIR/src-tauri/target/release/bundle/macos/SAM.app"
        if [[ -d "$app_path" ]]; then
            open "$app_path"
        else
            warn "Built app not found, running in dev mode..."
            cd "$SCRIPT_DIR"
            npm run tauri:dev
        fi
    fi
}

# =============================================================================
# Status Display
# =============================================================================
show_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    SAM SYSTEM STATUS                        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # MLX
    if python3 -c "import mlx" 2>/dev/null; then
        echo -e "  MLX:           ${GREEN}✓ Available${NC}"
    else
        echo -e "  MLX:           ${RED}✗ Not installed${NC}"
    fi

    # Brain Daemon
    local brain_pid=$(cat "$BRAIN_DIR/.sam_daemon.pid" 2>/dev/null)
    if [[ -n "$brain_pid" ]] && kill -0 "$brain_pid" 2>/dev/null; then
        echo -e "  Brain Daemon:  ${GREEN}✓ Running (PID $brain_pid)${NC}"
    else
        echo -e "  Brain Daemon:  ${YELLOW}○ Not running${NC}"
    fi

    # Scraper Daemon
    local scraper_pid=$(cat "$HOME/.sam_scraper_daemon.pid" 2>/dev/null)
    if [[ -n "$scraper_pid" ]] && kill -0 "$scraper_pid" 2>/dev/null; then
        echo -e "  Scraper:       ${GREEN}✓ Running (PID $scraper_pid)${NC}"
    else
        echo -e "  Scraper:       ${YELLOW}○ Not running${NC}"
    fi

    # Training Pipeline
    local train_pid=$(cat "$HOME/.sam_training_daemon.pid" 2>/dev/null)
    if [[ -n "$train_pid" ]] && kill -0 "$train_pid" 2>/dev/null; then
        echo -e "  Training:      ${GREEN}✓ Running (PID $train_pid)${NC}"
    else
        echo -e "  Training:      ${YELLOW}○ Not running${NC}"
    fi

    # Database stats
    if command -v python3 &>/dev/null; then
        local stats=$(cd "$SCRAPER_DIR" && python3 -c "
from scraper_system.storage.database import get_database
db = get_database()
s = db.get_global_stats()
print(f\"{s.get('total_items', 0)}|{s.get('total_sources', 0)}\")
" 2>/dev/null || echo "0|0")
        local items=$(echo "$stats" | cut -d'|' -f1)
        local sources=$(echo "$stats" | cut -d'|' -f2)
        echo -e "  Database:      ${BLUE}$items items from $sources sources${NC}"
    fi

    # RAM Usage
    local ram_free=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
    local ram_gb=$(echo "scale=1; $ram_free * 4096 / 1024 / 1024 / 1024" | bc 2>/dev/null || echo "?")
    echo -e "  Free RAM:      ${BLUE}${ram_gb}GB${NC}"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              SAM - Self-improving AI Assistant             ║${NC}"
    echo -e "${CYAN}║                    MLX Native Edition                      ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Parse args
    MODE="prod"
    DAEMON_ONLY=false
    CHECK_ONLY=false
    DUAL_MODE=false

    for arg in "$@"; do
        case $arg in
            --dev) MODE="dev" ;;
            --check) CHECK_ONLY=true ;;
            --daemon) DAEMON_ONLY=true ;;
            --dual) DUAL_MODE=true ;;
            --status|-s) show_status; exit 0 ;;
            --help|-h)
                echo "Usage: ./launch_sam.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --dev      Development mode"
                echo "  --check    Check readiness only"
                echo "  --daemon   Start daemons only (no UI)"
                echo "  --dual     Launch dual Claude terminals"
                echo "  --status   Show system status"
                echo ""
                exit 0
                ;;
        esac
    done

    # Step 1: MLX
    if ! check_mlx; then
        error "Cannot proceed without MLX"
        exit 1
    fi

    # Step 2-4: Daemons
    ensure_brain_daemon
    ensure_scraper_daemon
    ensure_training_pipeline

    if [[ "$DAEMON_ONLY" == true ]]; then
        echo ""
        log "All daemons started. SAM is running in background."
        show_status
        exit 0
    fi

    if [[ "$CHECK_ONLY" == true ]]; then
        echo ""
        log "✅ SAM is ready!"
        show_status
        exit 0
    fi

    # Step 5: Dual Claude mode
    if [[ "$DUAL_MODE" == true ]]; then
        launch_dual_claude
        exit 0
    fi

    # Step 6: Launch app
    echo ""
    launch_app "$MODE"
}

main "$@"
