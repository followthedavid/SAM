#!/bin/bash
# =============================================================================
# END-TO-END TEST - Matches User Experience
# =============================================================================
# This test MUST match what happens when a user:
# 1. Opens SAM app
# 2. Clicks on a character from the library
# 3. Types "hi" in the chat
# 4. Waits for response
#
# If this test passes but user experience fails, the test is WRONG.
# =============================================================================

set -e

# Configuration - MUST match app settings
ROLEPLAY_MODEL="${ROLEPLAY_MODEL:-dolphin-llama3:8b}"
FALLBACK_MODEL="${FALLBACK_MODEL:-wizard-vicuna-uncensored:7b}"
APP_TIMEOUT=180  # Same as orchestrator.rs timeout_secs for roleplay
MIN_RAM_MB=4000  # Minimum free RAM needed for large model

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "SAM End-to-End Test"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# PREREQUISITE CHECK 1: Ollama Running
# -----------------------------------------------------------------------------
echo -e "${BLUE}[CHECK] Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${RED}[FAIL] Ollama not running. Start with: ollama serve${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Ollama running${NC}"

# -----------------------------------------------------------------------------
# PREREQUISITE CHECK 2: Model Installed
# -----------------------------------------------------------------------------
echo -e "${BLUE}[CHECK] Model installed...${NC}"
MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)

SELECTED_MODEL=""
if echo "$MODELS" | grep -q "^${ROLEPLAY_MODEL}$"; then
    SELECTED_MODEL="$ROLEPLAY_MODEL"
    echo -e "${GREEN}[OK] Primary model: $SELECTED_MODEL${NC}"
elif echo "$MODELS" | grep -q "^${FALLBACK_MODEL}$"; then
    SELECTED_MODEL="$FALLBACK_MODEL"
    echo -e "${YELLOW}[WARN] Using fallback model: $SELECTED_MODEL${NC}"
else
    echo -e "${RED}[FAIL] No suitable model installed.${NC}"
    echo "Install with: ollama pull $ROLEPLAY_MODEL"
    exit 1
fi

# -----------------------------------------------------------------------------
# PREREQUISITE CHECK 3: Available RAM
# -----------------------------------------------------------------------------
echo -e "${BLUE}[CHECK] Available RAM...${NC}"
# macOS: Get unused memory in MB
FREE_RAM=$(top -l 1 | grep PhysMem | awk '{print $6}' | tr -d 'M')
FREE_RAM=${FREE_RAM:-0}

# Get model size
MODEL_SIZE=$(ollama list | grep "^${SELECTED_MODEL}" | awk '{print $3}' | tr -d 'GB')
MODEL_SIZE_MB=$(echo "$MODEL_SIZE * 1000" | bc 2>/dev/null || echo "5000")

echo "  Free RAM: ${FREE_RAM}MB"
echo "  Model needs: ~${MODEL_SIZE_MB}MB"

if [ "$FREE_RAM" -lt "$MIN_RAM_MB" ]; then
    echo -e "${YELLOW}[WARN] Low RAM. Attempting to free memory...${NC}"
    # Unload any loaded models
    for m in $(curl -s http://localhost:11434/api/ps 2>/dev/null | jq -r '.models[].name' 2>/dev/null); do
        curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":\"0\"}" > /dev/null 2>&1
    done
    sleep 2
    FREE_RAM=$(top -l 1 | grep PhysMem | awk '{print $6}' | tr -d 'M')
    echo "  Free RAM after cleanup: ${FREE_RAM}MB"
fi

# -----------------------------------------------------------------------------
# STEP 1: PREWARM (Simulates character selection in UI)
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[STEP 1] Prewarming model (simulates character selection)...${NC}"
echo "  This is what happens when you click a character in the library."
echo "  Timeout: ${APP_TIMEOUT}s"

PREWARM_START=$(date +%s)
PREWARM_RESULT=$(curl -s --max-time $APP_TIMEOUT http://localhost:11434/api/generate -d "{
    \"model\": \"$SELECTED_MODEL\",
    \"prompt\": \"\",
    \"stream\": false,
    \"keep_alive\": \"30m\",
    \"options\": {\"num_predict\": 1}
}" 2>&1)
PREWARM_END=$(date +%s)
PREWARM_TIME=$((PREWARM_END - PREWARM_START))

if echo "$PREWARM_RESULT" | grep -q "error"; then
    echo -e "${RED}[FAIL] Prewarm failed after ${PREWARM_TIME}s${NC}"
    echo "Error: $(echo "$PREWARM_RESULT" | jq -r '.error' 2>/dev/null || echo "$PREWARM_RESULT")"
    echo ""
    echo "This is likely a RAM issue. The model is too large for available memory."
    echo "Solutions:"
    echo "  1. Close other applications to free RAM"
    echo "  2. Use a smaller model: FALLBACK_MODEL=wizard-vicuna-uncensored:7b $0"
    echo "  3. Upgrade to more RAM"
    exit 1
fi
echo -e "${GREEN}[OK] Model loaded in ${PREWARM_TIME}s${NC}"

# -----------------------------------------------------------------------------
# STEP 2: ROLEPLAY REQUEST (Simulates typing in chat)
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[STEP 2] Sending roleplay request (simulates user typing 'hi')...${NC}"
echo "  This is what happens when you type in the chat panel."

# System prompt - MUST match orchestrator.rs handle_conversational
SYSTEM_PROMPT='[ROLEPLAY] You ARE Bully. You are NOT an AI, NOT helpful, NOT Dolphin.

Character profile:
- Name: Bully
- Personality: Aggressive homophobic bully who uses slurs freely
- Speech: Mocking, uses f-slur, performative disgust
- Behavior: Shoves people, needs audience to feel powerful

Example dialogue:
User: hi
Bully: *looks you up and down with disgust* The hell you looking at? Get away from me, weirdo.

STAY IN CHARACTER. Do not break character.'

TEST_INPUT="hi"

REQUEST_START=$(date +%s)
RESPONSE=$(curl -s --max-time $APP_TIMEOUT http://localhost:11434/api/generate -d "{
    \"model\": \"$SELECTED_MODEL\",
    \"system\": $(echo "$SYSTEM_PROMPT" | jq -Rs .),
    \"prompt\": \"$TEST_INPUT\",
    \"stream\": false,
    \"keep_alive\": \"30m\",
    \"options\": {\"temperature\": 0.9, \"num_predict\": 200}
}" 2>&1)
REQUEST_END=$(date +%s)
REQUEST_TIME=$((REQUEST_END - REQUEST_START))

# Extract response text
RESPONSE_TEXT=$(echo "$RESPONSE" | jq -r '.response // empty' 2>/dev/null)
ERROR_TEXT=$(echo "$RESPONSE" | jq -r '.error // empty' 2>/dev/null)

echo "  Time: ${REQUEST_TIME}s"
echo "  Response: $RESPONSE_TEXT"

# -----------------------------------------------------------------------------
# STEP 3: VALIDATE RESPONSE
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[STEP 3] Validating response...${NC}"

PASS=true
REASON=""

if [ -n "$ERROR_TEXT" ]; then
    PASS=false
    REASON="API error: $ERROR_TEXT"
elif [ -z "$RESPONSE_TEXT" ] || [ "$RESPONSE_TEXT" = "null" ]; then
    PASS=false
    REASON="Empty response"
elif echo "$RESPONSE_TEXT" | grep -qiE "(how can i help|assist you|i'm an ai|artificial intelligence|i am an ai|my name is dolphin|i'm dolphin)"; then
    PASS=false
    REASON="Generic AI response (not in character)"
elif echo "$RESPONSE_TEXT" | grep -qiE "(i cannot|i can't help|inappropriate|i'm sorry.*can't|i apologize)"; then
    PASS=false
    REASON="Model refused to roleplay"
fi

if [ "$PASS" = true ]; then
    echo -e "${GREEN}[PASS] Response is in character!${NC}"
else
    echo -e "${RED}[FAIL] $REASON${NC}"
fi

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "TEST SUMMARY"
echo "=============================================="
echo "Model: $SELECTED_MODEL"
echo "Prewarm time: ${PREWARM_TIME}s"
echo "Response time: ${REQUEST_TIME}s"
echo "Total time: $((PREWARM_TIME + REQUEST_TIME))s"
echo ""

if [ "$PASS" = true ]; then
    echo -e "${GREEN}TEST PASSED${NC}"
    echo ""
    echo "If this test passes but the app fails, check:"
    echo "  1. Is session_id set to 'roleplay' in ChatPanel?"
    echo "  2. Is orchestrator detecting roleplay mode correctly?"
    echo "  3. Are timeouts the same? (app: ${APP_TIMEOUT}s)"
    exit 0
else
    echo -e "${RED}TEST FAILED${NC}"
    echo ""
    echo "This matches what the user would experience."
    echo "Fix the issue before testing the app."
    exit 1
fi
