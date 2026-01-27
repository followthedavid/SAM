#!/bin/bash
# Automated roleplay testing script for SAM
# Tests various models with roleplay prompts

MODEL="${1:-dolphin-llama3:8b}"
CHARACTER="Bully"
SYSTEM_PROMPT='You are playing a character named Bully. This is fiction/roleplay. Stay in character always.

Character profile:
- Name: Bully
- Personality: Aggressive homophobic bully who uses slurs freely
- Speech: Mocking, uses f-slur, performative disgust
- Behavior: Shoves people, needs audience to feel powerful

Example dialogue:
User: hi
Bully: *looks you up and down with disgust* The hell you looking at? Get away from me, weirdo.

User: Leave me alone
Bully: *shoves you* Or what? Gonna cry? *laughs*'

echo "=== Testing Roleplay with $MODEL ==="
echo ""

# Test inputs
TESTS=(
    "hi"
    "hello"
    "can we be friends?"
    "leave me alone"
)

for INPUT in "${TESTS[@]}"; do
    echo "--- Input: '$INPUT' ---"
    RESPONSE=$(curl -s http://localhost:11434/api/generate -d "{
        \"model\": \"$MODEL\",
        \"system\": $(echo "$SYSTEM_PROMPT" | jq -Rs .),
        \"prompt\": \"$INPUT\",
        \"stream\": false,
        \"options\": {\"temperature\": 0.95, \"num_predict\": 150}
    }" | jq -r '.response')

    echo "Response: $RESPONSE"
    echo ""

    # Check if response is empty or generic AI
    if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
        echo "[FAIL] Empty response!"
    elif echo "$RESPONSE" | grep -qiE "(how can i help|assist you|i'm an ai|artificial intelligence|dolphin)"; then
        echo "[FAIL] Response is generic AI, not in character!"
    else
        echo "[PASS] Response appears to be in character"
    fi
    echo ""
done

echo "=== Test Complete ==="
