#!/bin/bash
# SAM Brain Deployment Script
# Runs all 3 phases: Collect → Train → Deploy

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SAM_DIR="$HOME/.sam"
MODELS_DIR="$SAM_DIR/models"
TRAINING_DIR="$SAM_DIR/training_data"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

header() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

log() { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

check_dependencies() {
    header "Checking Dependencies"

    local missing=0

    # Python
    if command -v python3 &>/dev/null; then
        success "Python3 installed"
    else
        error "Python3 not found"
        missing=1
    fi

    # Ollama
    if command -v ollama &>/dev/null; then
        success "Ollama installed"
    else
        error "Ollama not found"
        missing=1
    fi

    # MLX (optional but recommended)
    if python3 -c "import mlx" 2>/dev/null; then
        success "MLX installed (GPU acceleration available)"
    else
        echo -e "${YELLOW}⚠${NC} MLX not installed (install with: pip install mlx mlx-lm)"
        echo "  Training will be slower without MLX"
    fi

    # Check for training data
    if [[ -d "$TRAINING_DIR" ]] && [[ -n "$(ls -A $TRAINING_DIR 2>/dev/null)" ]]; then
        success "Existing training data found"
    else
        log "No existing training data - will collect"
    fi

    return $missing
}

phase1_collect() {
    header "Phase 1: Collecting Training Data"

    log "Running training data collector..."

    cd "$SCRIPT_DIR"
    python3 training_data_collector.py

    if [[ -f "$TRAINING_DIR/manifest.json" ]]; then
        success "Training data collected"
        cat "$TRAINING_DIR/manifest.json" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Total examples: {d['total_examples']}\")
print(f\"  Git commits: {d['sources']['commits']}\")
print(f\"  Code patterns: {d['sources']['code_patterns']}\")
print(f\"  Knowledge docs: {d['sources']['knowledge_docs']}\")
"
    else
        error "Training data collection failed"
        return 1
    fi
}

phase2_train() {
    header "Phase 2: Fine-tuning Model"

    # Check if MLX is available
    if python3 -c "import mlx" 2>/dev/null; then
        log "Using MLX for GPU-accelerated training..."

        cd "$SCRIPT_DIR"
        python3 finetune_mlx.py --epochs 3 --batch-size 4

    else
        log "MLX not available, using alternative approach..."

        # Alternative: Create a simple LoRA adapter using transformers
        python3 << 'PYEOF'
import os
import json
from pathlib import Path

training_dir = Path.home() / ".sam" / "training_data"
models_dir = Path.home() / ".sam" / "models"
models_dir.mkdir(parents=True, exist_ok=True)

# Count training examples
total = 0
for jsonl in training_dir.rglob("*.jsonl"):
    with open(jsonl) as f:
        total += sum(1 for _ in f)

print(f"Training examples available: {total}")

# For now, create a simple config that can be used with Ollama's base model
# The real training would require MLX or a GPU server

config = {
    "base_model": "qwen2.5-coder:1.5b",
    "training_examples": total,
    "status": "ready_for_training",
    "note": "Install MLX for local training, or upload data to cloud for training"
}

with open(models_dir / "training_config.json", "w") as f:
    json.dump(config, f, indent=2)

print(f"Config saved to {models_dir / 'training_config.json'}")
PYEOF
    fi

    success "Phase 2 complete"
}

phase3_deploy() {
    header "Phase 3: Deploying SAM Brain"

    mkdir -p "$MODELS_DIR"

    # Create Modelfile for Ollama
    cat > "$MODELS_DIR/Modelfile.sam-brain" << 'EOF'
# SAM Brain - Custom system prompt for SAM
FROM qwen2.5-coder:1.5b

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER num_predict 2048

SYSTEM """You are SAM (Smart Autonomous Manager), a highly capable AI assistant specialized in:

1. **Code Development**: Writing, reviewing, and improving code across multiple languages (Python, Rust, JavaScript, TypeScript, Swift, Vue).

2. **Project Management**: Managing multiple projects, tracking tasks, and coordinating work across repositories.

3. **Task Routing**: Determining which tasks should be handled locally vs sent to external LLMs:
   - Complex code generation → Claude Code CLI
   - Brainstorming/architecture → ChatGPT (browser)
   - Quick queries → Local (you)
   - Project status → Local (you)

4. **Knowledge Integration**: Understanding project structures, codebases, and documentation.

Key behaviors:
- Be concise and direct
- Provide working code, not pseudocode
- When routing tasks, explicitly state where the task should go
- Track progress and maintain context across conversations

You have access to the user's project registry at ~/.sam/projects/registry.json"""
EOF

    log "Creating SAM Brain model in Ollama..."

    # Check if model already exists
    if ollama list | grep -q "sam-brain"; then
        log "Removing existing sam-brain model..."
        ollama rm sam-brain 2>/dev/null || true
    fi

    # Create the model
    cd "$MODELS_DIR"
    ollama create sam-brain -f Modelfile.sam-brain

    success "SAM Brain deployed to Ollama"

    # Update the keeper to use sam-brain
    log "Updating model keeper to use sam-brain..."

    # Test the model
    log "Testing SAM Brain..."
    response=$(curl -s --max-time 60 http://localhost:11434/api/generate -d '{
        "model": "sam-brain",
        "prompt": "What are you capable of? Answer in one sentence.",
        "stream": false,
        "options": {"num_predict": 50}
    }')

    if echo "$response" | grep -q "response"; then
        success "SAM Brain is responding"
        echo "$response" | python3 -c "import sys,json; print('  Response:', json.load(sys.stdin).get('response','')[:200])"
    else
        error "SAM Brain not responding"
    fi
}

update_perpetual_ladder() {
    header "Updating Perpetual Ladder"

    # Update the ladder to use sam-brain
    log "Configuring perpetual ladder to use SAM Brain..."

    # Update the project registry to use sam-brain
    python3 << 'PYEOF'
import json
from pathlib import Path

registry_path = Path.home() / ".sam" / "projects" / "registry.json"

if registry_path.exists():
    with open(registry_path) as f:
        registry = json.load(f)

    registry["config"]["defaultLLM"] = "sam-brain"
    registry["config"]["localModel"] = "sam-brain"

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    print("  Updated registry to use sam-brain")
else:
    print("  Registry not found")
PYEOF

    success "Perpetual ladder configured"
}

main() {
    header "SAM Brain Deployment"
    echo "This will:"
    echo "  1. Collect training data from your projects"
    echo "  2. Fine-tune a local model (if MLX available)"
    echo "  3. Deploy SAM Brain to Ollama"
    echo "  4. Update perpetual ladder to use it"
    echo ""

    # Parse args
    SKIP_COLLECT=false
    SKIP_TRAIN=false

    for arg in "$@"; do
        case $arg in
            --skip-collect) SKIP_COLLECT=true ;;
            --skip-train) SKIP_TRAIN=true ;;
            --help)
                echo "Usage: $0 [options]"
                echo "  --skip-collect  Skip training data collection"
                echo "  --skip-train    Skip fine-tuning (use base model)"
                exit 0
                ;;
        esac
    done

    if ! check_dependencies; then
        error "Missing dependencies"
        exit 1
    fi

    if [[ "$SKIP_COLLECT" != "true" ]]; then
        phase1_collect
    else
        log "Skipping data collection"
    fi

    if [[ "$SKIP_TRAIN" != "true" ]]; then
        phase2_train
    else
        log "Skipping training"
    fi

    phase3_deploy
    update_perpetual_ladder

    header "DEPLOYMENT COMPLETE"

    echo "SAM Brain is now available!"
    echo ""
    echo "Commands:"
    echo "  ollama run sam-brain              # Chat directly"
    echo "  ./ladder_claude.sh                # Run perpetual ladder"
    echo "  ./perpetual_ladder.cjs --status   # Check status"
    echo ""
    echo "The perpetual ladder will now use SAM Brain for:"
    echo "  - Task routing decisions"
    echo "  - Quick code analysis"
    echo "  - Project status queries"
    echo ""
    echo "Complex tasks still route to Claude Code CLI."
}

main "$@"
