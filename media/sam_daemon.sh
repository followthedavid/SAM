#!/bin/bash
# SAM Background Daemon
# Monitors transfer and runs job queue
# Persists state, survives crashes

LOG_FILE="$HOME/.sam_daemon.log"
PID_FILE="$HOME/.sam_daemon.pid"
QUEUE_SCRIPT="/Users/davidquinton/ReverseLab/SAM/media/job_queue.py"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "SAM daemon already running (PID: $OLD_PID)"
        exit 1
    fi
fi

# Save our PID
echo $$ > "$PID_FILE"

log "SAM Daemon started"
log "PID: $$"
log "Log: $LOG_FILE"
log "Queue: ~/.sam_job_queue.json"

# Cleanup on exit
cleanup() {
    log "SAM Daemon stopping..."
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for transfer to complete
wait_for_transfer() {
    log "Waiting for rsync transfer to complete..."

    while pgrep -f "rsync.*David External" > /dev/null; do
        CURRENT=$(du -sg '/Volumes/Music/_Music Lossless' 2>/dev/null | cut -f1)
        log "Transfer in progress: ${CURRENT}GB"
        sleep 300  # Check every 5 minutes
    done

    log "Transfer complete!"
}

# Main loop
main() {
    # First, wait for transfer if it's running
    if pgrep -f "rsync.*David External" > /dev/null; then
        wait_for_transfer
    fi

    log "Starting job queue processor..."

    # Activate venv
    source ~/ReverseLab/SAM/media/venv/bin/activate
    export DISCOGS_TOKEN="ZVyTkhRtDtwJBXkoBDDJmmHcnpLdvuYlYzZCOLte"

    # Run the job queue
    python3 "$QUEUE_SCRIPT" run 2>&1 | tee -a "$LOG_FILE"
}

# Run
main
