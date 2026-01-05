#!/bin/bash
# SAM Watch & Test - Auto-rebuild on changes, continuous testing
# Usage: ./watch_and_test.sh

SAM_DIR="/Users/davidquinton/ReverseLab/SAM/warp_tauri"
cd "$SAM_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

LAST_HASH=""

# Quick test function
quick_test() {
    echo -e "${BLUE}[TEST]${NC} Running quick tests..."

    # Test 1: Conversational
    local chat=$(curl -s http://localhost:11434/api/generate -d '{
        "model": "qwen2.5-coder:1.5b",
        "prompt": "You are SAM. User: hi\nSAM:",
        "stream": false,
        "options": {"num_predict": 50}
    }' | jq -r '.response[:50]')

    if [[ "$chat" =~ [Hh]ello|[Hh]i|[Hh]ey ]]; then
        echo -e "  ${GREEN}✓${NC} Conversational: $chat"
    else
        echo -e "  ${RED}✗${NC} Conversational: $chat"
    fi

    # Test 2: Tool call format
    local tool=$(curl -s http://localhost:11434/api/generate -d '{
        "model": "qwen2.5-coder:1.5b",
        "prompt": "Output ONLY: {\"tool\": \"read_file\", \"args\": {\"path\": \"test.txt\"}}",
        "stream": false,
        "options": {"num_predict": 100}
    }' | jq -r '.response')

    if [[ "$tool" =~ \"tool\" ]]; then
        echo -e "  ${GREEN}✓${NC} Tool format: JSON detected"
    else
        echo -e "  ${RED}✗${NC} Tool format: $tool"
    fi

    echo ""
}

# Build function
build() {
    echo -e "${YELLOW}[BUILD]${NC} Compiling..."
    pkill -f "SAM" 2>/dev/null

    # Only rebuild Rust (faster)
    cd src-tauri
    cargo build --release 2>&1 | grep -E "(Compiling sam-terminal|Finished|error)"
    cd ..

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[BUILD]${NC} Success"

        # Relaunch
        open "$SAM_DIR/src-tauri/target/release/bundle/macos/SAM.app" 2>/dev/null || \
        "$SAM_DIR/src-tauri/target/release/sam-terminal" &

        sleep 2
        quick_test
    else
        echo -e "${RED}[BUILD]${NC} Failed"
    fi
}

# Get hash of source files
get_hash() {
    find src-tauri/src -name "*.rs" -exec md5 -q {} \; 2>/dev/null | md5
}

echo -e "${BLUE}=== SAM Watch Mode ===${NC}"
echo "Watching for changes in src-tauri/src/*.rs"
echo "Press Ctrl+C to stop"
echo ""

# Initial build
build

# Watch loop
while true; do
    CURRENT_HASH=$(get_hash)

    if [ "$CURRENT_HASH" != "$LAST_HASH" ] && [ -n "$LAST_HASH" ]; then
        echo -e "${YELLOW}[CHANGE]${NC} Detected file changes"
        build
    fi

    LAST_HASH="$CURRENT_HASH"
    sleep 2
done
