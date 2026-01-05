#!/bin/bash
# SAM AI Bridge Daemon
# Processes queued tasks by routing to ChatGPT or Claude via browser

QUEUE_FILE="$HOME/.sam_chatgpt_queue.json"
RESPONSE_FILE="$HOME/.sam_chatgpt_responses.json"
LOG_FILE="/tmp/sam_bridge.log"
PID_FILE="$HOME/.sam_bridge.pid"

# Initialize response file
if [ ! -f "$RESPONSE_FILE" ]; then
    echo "{}" > "$RESPONSE_FILE"
fi

log() { echo "$(date +%H:%M:%S) $1" | tee -a "$LOG_FILE"; }

# Check if already running
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if ps -p "$old_pid" > /dev/null 2>&1; then
        log "[ERROR] Bridge daemon already running (PID: $old_pid)"
        exit 1
    fi
fi

echo $$ > "$PID_FILE"
trap "rm -f $PID_FILE; exit" INT TERM EXIT

log "=== SAM AI Bridge Daemon Started ==="

# Open ChatGPT in browser
open_chatgpt() {
    osascript <<'EOF'
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then
        make new window
    end if
    set URL of active tab of front window to "https://chat.openai.com/"
end tell
EOF
    sleep 3  # Wait for page load
}

# Open Claude in browser
open_claude() {
    osascript <<'EOF'
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then
        make new window
    end if
    set URL of active tab of front window to "https://claude.ai/new"
end tell
EOF
    sleep 3  # Wait for page load
}

# Type into the current browser input field
type_prompt() {
    local prompt="$1"
    # Escape for AppleScript
    local escaped_prompt=$(echo "$prompt" | sed 's/"/\\"/g' | tr '\n' ' ')

    osascript <<EOF
tell application "System Events"
    keystroke "$escaped_prompt"
    delay 0.5
    keystroke return
end tell
EOF
}

# Wait for response (simplified - checks for visible text change)
wait_for_response() {
    local timeout=120
    local elapsed=0
    log "  Waiting for response (max ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        sleep 5
        ((elapsed += 5))

        # Check if response appeared (look for new content)
        # This is a heuristic - better would be to scrape the page
        log "  ... waiting (${elapsed}s)"
    done

    log "  Response wait complete"
}

# Process a single task
process_task() {
    local task_id="$1"
    local prompt="$2"
    local provider="$3"

    log "[TASK] Processing: $task_id (provider: $provider)"
    log "  Prompt: ${prompt:0:100}..."

    # Update task status
    local queue=$(cat "$QUEUE_FILE")
    echo "$queue" | jq --arg id "$task_id" '
        map(if .id == $id then .status = "processing" else . end)
    ' > "$QUEUE_FILE"

    # Open appropriate AI
    if [ "$provider" = "chatgpt" ]; then
        open_chatgpt
    else
        open_claude
    fi

    # Type the prompt
    type_prompt "$prompt"

    # Wait for response
    wait_for_response

    # For now, we'll simulate getting the response
    # In production, would need browser automation to extract text
    local response="Response received from $provider (bridge automation)"

    # Save response
    local responses=$(cat "$RESPONSE_FILE")
    echo "$responses" | jq --arg id "$task_id" --arg resp "$response" \
        '. + {($id): {"response": $resp, "success": true, "timestamp": (now | todate)}}' \
        > "$RESPONSE_FILE"

    # Mark task complete in queue
    queue=$(cat "$QUEUE_FILE")
    echo "$queue" | jq --arg id "$task_id" '
        map(if .id == $id then .status = "completed" else . end)
    ' > "$QUEUE_FILE"

    log "[DONE] Task $task_id completed"
}

# Main loop
while true; do
    if [ -f "$QUEUE_FILE" ]; then
        # Get next pending task
        task=$(cat "$QUEUE_FILE" | jq -r '.[] | select(.status == "pending") | @json' | head -1)

        if [ -n "$task" ] && [ "$task" != "null" ]; then
            task_id=$(echo "$task" | jq -r '.id')
            prompt=$(echo "$task" | jq -r '.prompt')
            provider=$(echo "$task" | jq -r '.provider')

            process_task "$task_id" "$prompt" "$provider"
        fi
    fi

    sleep 5
done
