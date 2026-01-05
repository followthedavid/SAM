#!/bin/bash
# SAM System Test Suite
# Comprehensive automated testing for all SAM components

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; ((PASS++)); }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; ((FAIL++)); }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; ((WARN++)); }
info() { echo -e "${BLUE}ℹ INFO${NC}: $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           SAM SYSTEM TEST SUITE                              ║"
echo "║           Comprehensive Automated Testing                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 1. OLLAMA TESTS
# ═══════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. OLLAMA SERVICE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    pass "Ollama service is running"
else
    fail "Ollama service is NOT running"
    info "Start with: ollama serve"
fi

# Test available models
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); print(' '.join([m['name'] for m in data.get('models',[])]))" 2>/dev/null || echo "")
if [ -n "$MODELS" ]; then
    pass "Models available: $MODELS"
else
    warn "No models found in Ollama"
fi

# Test required models
for model in "qwen2.5-coder:1.5b" "tinydolphin:1.1b"; do
    if echo "$MODELS" | grep -q "$model"; then
        pass "Model $model is available"
    else
        warn "Model $model not found (may need: ollama pull $model)"
    fi
done

# Test model response (with timeout)
echo ""
info "Testing model response (10s timeout)..."
RESPONSE=$(timeout 10 curl -s http://localhost:11434/api/generate \
    -d '{"model":"qwen2.5-coder:1.5b","prompt":"Reply with exactly: OK","stream":false}' 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','')[:50])" 2>/dev/null || echo "TIMEOUT")

if [ "$RESPONSE" = "TIMEOUT" ]; then
    warn "Model response timed out (model may be loading)"
elif [ -n "$RESPONSE" ]; then
    pass "Model responded: $RESPONSE"
else
    fail "Model did not respond"
fi

# ═══════════════════════════════════════════════════════════════════
# 2. SAM APP TESTS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. SAM APPLICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test SAM app is installed
if [ -d "/Applications/SAM.app" ]; then
    pass "SAM.app is installed in /Applications"
else
    fail "SAM.app not found in /Applications"
fi

# Test SAM is running
if pgrep -f "SAM" > /dev/null; then
    pass "SAM application is running"
    SAM_PIDS=$(pgrep -f "SAM" | tr '\n' ' ')
    info "PIDs: $SAM_PIDS"
else
    warn "SAM application is not running"
fi

# ═══════════════════════════════════════════════════════════════════
# 3. AI AGENT SERVER TESTS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. AI AGENT SERVER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if pgrep -f "ai_agent_server" > /dev/null; then
    pass "AI Agent Server is running"
else
    warn "AI Agent Server is not running (optional component)"
fi

# Test agent server API if running
if curl -s http://localhost:3847/health > /dev/null 2>&1; then
    pass "Agent Server API responding on port 3847"
else
    info "Agent Server API not available (may not be needed)"
fi

# ═══════════════════════════════════════════════════════════════════
# 4. BRIDGE SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. BRIDGE SYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check bridge scripts exist
BRIDGE_DIR="/Users/davidquinton/ReverseLab/SAM/warp_tauri"
for script in "claude_chatgpt_bridge.cjs" "claude_bridge.cjs" "claude_thread_manager.cjs"; do
    if [ -f "$BRIDGE_DIR/$script" ]; then
        pass "Bridge script exists: $script"
    else
        warn "Bridge script missing: $script"
    fi
done

# Check queue files (they may not exist until first use)
for file in ~/.sam_chatgpt_queue.json ~/.sam_claude_queue.json ~/.sam_bridge_results.json; do
    if [ -f "$file" ]; then
        info "Queue file exists: $file"
    else
        info "Queue file will be created on first use: $file"
    fi
done

# ═══════════════════════════════════════════════════════════════════
# 5. ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. ORCHESTRATOR (Rust Backend)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check orchestrator source exists
ORCH_FILE="/Users/davidquinton/ReverseLab/SAM/warp_tauri/src-tauri/src/scaffolding/orchestrator.rs"
if [ -f "$ORCH_FILE" ]; then
    pass "Orchestrator source exists"
    LINES=$(wc -l < "$ORCH_FILE" | tr -d ' ')
    info "Orchestrator: $LINES lines of code"
else
    fail "Orchestrator source not found"
fi

# Check other scaffolding modules
for module in "hybrid_router" "embedding_engine" "template_library" "micro_model_manager"; do
    if [ -f "/Users/davidquinton/ReverseLab/SAM/warp_tauri/src-tauri/src/scaffolding/${module}.rs" ]; then
        pass "Module exists: ${module}.rs"
    else
        warn "Module missing: ${module}.rs"
    fi
done

# ═══════════════════════════════════════════════════════════════════
# 6. FRONTEND TESTS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. FRONTEND COMPONENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COMPONENTS_DIR="/Users/davidquinton/ReverseLab/SAM/warp_tauri/src/components"
for component in "TopicGrid.vue" "AIChatTab.vue" "TabManager.vue" "StatusBar.vue"; do
    if [ -f "$COMPONENTS_DIR/$component" ]; then
        pass "Component exists: $component"
    else
        fail "Component missing: $component"
    fi
done

# Check topicStore
if [ -f "/Users/davidquinton/ReverseLab/SAM/warp_tauri/src/stores/topicStore.js" ]; then
    TOPICS=$(grep -c "id:" "/Users/davidquinton/ReverseLab/SAM/warp_tauri/src/stores/topicStore.js" || echo "0")
    pass "TopicStore exists with ~$TOPICS topic entries"
else
    fail "TopicStore not found"
fi

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}PASSED${NC}: $PASS"
echo -e "${RED}FAILED${NC}: $FAIL"
echo -e "${YELLOW}WARNINGS${NC}: $WARN"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ALL CRITICAL TESTS PASSED! SAM is ready to use.              ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  SOME TESTS FAILED! Please fix the issues above.              ${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
fi
echo ""
