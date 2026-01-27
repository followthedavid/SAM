#!/bin/bash
# RVC Native - No Docker Required
# Uses MPS (Apple Silicon GPU) directly
# ~336MB RAM vs ~2GB with Docker

set -e

RVC_DIR=~/Projects/RVC/rvc-webui

cleanup() {
    echo ""
    echo "Shutting down RVC..."
    pkill -f "infer-web.py" 2>/dev/null || true
    echo "Done!"
}

trap cleanup EXIT INT TERM

echo "=== RVC Voice Training (Native MPS) ==="
echo ""

cd "$RVC_DIR"
source venv/bin/activate

echo "Starting RVC WebUI..."
echo "Open: http://localhost:7865"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python infer-web.py
