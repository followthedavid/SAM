#!/bin/bash
# Start SAM Voice Server
# Usage: ./start_voice_server.sh [port]

PORT=${1:-8765}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Starting SAM Voice Server on port $PORT..."
echo "Access from iPhone: http://$(ipconfig getifaddr en0):$PORT/api/speak"
echo ""

python voice_server.py --port $PORT --host 0.0.0.0
