#!/bin/bash
# RVC Training - Fully Automatic
# Just run: rvc
# Docker starts automatically, quits when you close RVC

set -e

cleanup() {
    echo ""
    echo "Shutting down..."
    cd ~/Projects/RVC/rvc-webui
    docker-compose down 2>/dev/null || true

    # Quit Docker Desktop to free RAM
    echo "Quitting Docker to free ~2GB RAM..."
    osascript -e 'quit app "Docker"' 2>/dev/null || true
    echo "Done! RAM freed."
}

# Trap exit to always cleanup
trap cleanup EXIT INT TERM

echo "=== RVC Voice Training ==="
echo ""

# Start Docker if needed
if ! docker info &>/dev/null; then
    echo "Starting Docker..."
    open -a Docker

    printf "Waiting for Docker"
    for i in {1..60}; do
        if docker info &>/dev/null; then
            echo " Ready!"
            break
        fi
        sleep 1
        printf "."
    done
fi

if ! docker info &>/dev/null; then
    echo "ERROR: Docker failed to start"
    exit 1
fi

cd ~/Projects/RVC/rvc-webui

echo ""
echo "Starting RVC WebUI..."
echo "Open: http://localhost:7865"
echo ""
echo ">>> When done, just close this terminal or Ctrl+C <<<"
echo ">>> Docker will quit automatically to free RAM <<<"
echo ""

# Start RVC and wait for it
docker-compose up

# cleanup() runs automatically on exit
