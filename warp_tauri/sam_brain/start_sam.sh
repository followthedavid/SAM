#!/bin/bash
# SAM Startup Script
# Starts both the API server and the autonomous daemon

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run: python -m venv .venv && pip install numpy requests"
    exit 1
fi

# Parse arguments
API_PORT=${1:-8765}
MODE=${2:-"all"}  # all, api, daemon

case "$MODE" in
    api)
        echo "Starting SAM API server on port $API_PORT..."
        python sam_api.py server "$API_PORT"
        ;;
    daemon)
        echo "Starting SAM autonomous daemon..."
        python autonomous_daemon.py
        ;;
    once)
        echo "Running SAM improvement cycle once..."
        python autonomous_daemon.py --once
        ;;
    all)
        echo "Starting SAM (API on port $API_PORT + Daemon)..."

        # Start API server in background
        python sam_api.py server "$API_PORT" &
        API_PID=$!
        echo "API server started (PID: $API_PID)"

        # Give API time to start
        sleep 2

        # Start daemon in foreground
        echo "Starting autonomous daemon..."
        python autonomous_daemon.py

        # Cleanup
        kill $API_PID 2>/dev/null
        ;;
    status)
        echo "SAM Status:"
        python sam_api.py self
        ;;
    suggest)
        echo "Top Suggestions:"
        python sam_api.py suggest 5
        ;;
    think)
        shift 2
        QUERY="$*"
        python sam_api.py think "$QUERY"
        ;;
    *)
        echo "Usage: $0 [port] [mode]"
        echo ""
        echo "Modes:"
        echo "  all     - Start both API server and daemon (default)"
        echo "  api     - Start API server only"
        echo "  daemon  - Start autonomous daemon only"
        echo "  once    - Run one improvement cycle and exit"
        echo "  status  - Show SAM's current status"
        echo "  suggest - Show top improvement suggestions"
        echo "  think   - Ask SAM a question"
        echo ""
        echo "Examples:"
        echo "  $0              # Start everything on port 8765"
        echo "  $0 9000         # Start everything on port 9000"
        echo "  $0 8765 api     # Start API only on port 8765"
        echo "  $0 8765 daemon  # Start daemon only"
        echo "  $0 0 status     # Check SAM status"
        echo "  $0 0 think what should I work on next?"
        ;;
esac
