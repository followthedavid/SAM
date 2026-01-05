#!/bin/bash
# SAM Interactive Tester
# Usage: ./test_sam.sh [prompt]
# Or run without args for interactive mode

SAM_DIR="/Users/davidquinton/ReverseLab/SAM/warp_tauri"
cd "$SAM_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to test a prompt via Ollama directly (faster iteration)
test_ollama() {
    local prompt="$1"
    echo -e "${BLUE}Testing:${NC} $prompt"
    echo -e "${YELLOW}---${NC}"

    # Call Ollama with SAM's tool prompt format
    local result=$(curl -s http://localhost:11434/api/generate -d "{
        \"model\": \"qwen2.5-coder:1.5b\",
        \"prompt\": \"You are an AI assistant that completes tasks using tools.\n\nTOOLS:\n- read_file(path): Read a file\n- write_file(path, content): Write a file\n- execute_shell(command): Run shell command\n- search_code(query): Search code semantically\n- edit_file(path, old_string, new_string): Edit file\n- list_files(path): List directory\n\nRULES:\n1. Output ONLY a single JSON tool call, nothing else\n2. Format: {\\\"tool\\\": \\\"name\\\", \\\"args\\\": {...}}\n3. No explanations, no markdown, no extra text\n4. After seeing tool results, give a brief final answer\n\nWorking directory: $SAM_DIR\n\nUser request: $prompt\",
        \"stream\": false,
        \"options\": {\"temperature\": 0.2, \"num_predict\": 512}
    }" | jq -r '.response // .error // "No response"')

    echo -e "${GREEN}Response:${NC}"
    echo "$result"
    echo -e "${YELLOW}---${NC}"
    echo ""
}

# Function to test conversational prompt
test_chat() {
    local prompt="$1"
    echo -e "${BLUE}Chat:${NC} $prompt"
    echo -e "${YELLOW}---${NC}"

    local result=$(curl -s http://localhost:11434/api/generate -d "{
        \"model\": \"qwen2.5-coder:1.5b\",
        \"prompt\": \"You are SAM, a friendly and helpful AI assistant.\nRespond naturally and conversationally. Be concise but warm.\nDo not output JSON or tool calls - just respond in plain text.\n\nUser: $prompt\nSAM:\",
        \"stream\": false,
        \"options\": {\"temperature\": 0.7, \"num_predict\": 256}
    }" | jq -r '.response // .error // "No response"')

    echo -e "${GREEN}Response:${NC}"
    echo "$result"
    echo -e "${YELLOW}---${NC}"
    echo ""
}

# Quick rebuild function
rebuild() {
    echo -e "${YELLOW}Rebuilding SAM...${NC}"
    pkill -f "SAM" 2>/dev/null
    npm run build 2>&1 | tail -5
    open "$SAM_DIR/src-tauri/target/release/bundle/macos/SAM.app"
    echo -e "${GREEN}SAM rebuilt and launched${NC}"
}

# Run test suite
run_tests() {
    echo -e "${BLUE}=== SAM Test Suite ===${NC}"
    echo ""

    echo "1. Conversational"
    test_chat "hi"

    echo "2. Tool Call - Search"
    test_ollama "find files related to authentication"

    echo "3. Tool Call - Read"
    test_ollama "read the package.json file"

    echo "4. Tool Call - Shell"
    test_ollama "list files in src directory"

    echo -e "${GREEN}=== Tests Complete ===${NC}"
}

# Interactive mode
interactive() {
    echo -e "${BLUE}=== SAM Interactive Tester ===${NC}"
    echo "Commands:"
    echo "  /chat <msg>  - Test conversational path"
    echo "  /tool <msg>  - Test tool-calling path"
    echo "  /rebuild     - Rebuild and relaunch SAM"
    echo "  /tests       - Run test suite"
    echo "  /quit        - Exit"
    echo ""

    while true; do
        echo -n -e "${GREEN}sam> ${NC}"
        read -r input

        case "$input" in
            /quit|/exit|/q)
                echo "Bye!"
                exit 0
                ;;
            /rebuild)
                rebuild
                ;;
            /tests)
                run_tests
                ;;
            /chat\ *)
                test_chat "${input#/chat }"
                ;;
            /tool\ *)
                test_ollama "${input#/tool }"
                ;;
            "")
                continue
                ;;
            *)
                # Default: auto-detect based on content
                if [[ "$input" =~ ^(hi|hello|hey|thanks|bye) ]]; then
                    test_chat "$input"
                else
                    test_ollama "$input"
                fi
                ;;
        esac
    done
}

# Main
if [ "$1" = "--tests" ]; then
    run_tests
elif [ "$1" = "--rebuild" ]; then
    rebuild
elif [ -n "$1" ]; then
    # Single prompt mode
    test_ollama "$*"
else
    # Interactive mode
    interactive
fi
