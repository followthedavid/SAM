#!/bin/bash
# Ollama Model Keeper - keeps models loaded in memory
# Usage: ollama_keeper.sh [model_name]

MODEL="${1:-qwen2.5-coder:1.5b}"
KEEPALIVE_INTERVAL=60

echo "═══════════════════════════════════════════════════"
echo "  Ollama Model Keeper"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Model: $MODEL"
echo "  Keepalive: every ${KEEPALIVE_INTERVAL}s"
echo ""
echo "  Press Ctrl+C to stop"
echo "───────────────────────────────────────────────────"
echo ""

# Initial load with 24h keepalive
echo "[$(date +%H:%M:%S)] Loading model into memory..."
RESPONSE=$(curl -s http://localhost:11434/api/generate -d "{
  \"model\": \"$MODEL\",
  \"prompt\": \"hello\",
  \"keep_alive\": \"24h\",
  \"stream\": false,
  \"options\": {\"num_predict\": 1}
}" 2>&1)

if echo "$RESPONSE" | grep -q "response"; then
    echo "[$(date +%H:%M:%S)] ✓ Model loaded and ready"
else
    echo "[$(date +%H:%M:%S)] ✗ Failed to load: $RESPONSE"
fi

# Keepalive loop
while true; do
    sleep $KEEPALIVE_INTERVAL
    
    # Check if model is still loaded
    LOADED=$(curl -s http://localhost:11434/api/ps | grep -c "$MODEL")
    
    if [ "$LOADED" -gt 0 ]; then
        echo "[$(date +%H:%M:%S)] ✓ Model still loaded"
    else
        echo "[$(date +%H:%M:%S)] ⚠ Model unloaded, reloading..."
        curl -s http://localhost:11434/api/generate -d "{
          \"model\": \"$MODEL\",
          \"prompt\": \".\",
          \"keep_alive\": \"24h\",
          \"stream\": false,
          \"options\": {\"num_predict\": 1}
        }" > /dev/null 2>&1
    fi
done
