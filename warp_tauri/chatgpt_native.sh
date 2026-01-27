#!/bin/bash
# Native ChatGPT bridge using AppleScript (no automation detection)
# Uses real Brave browser - Cloudflare can't detect this

PROMPT="$1"

if [ -z "$PROMPT" ]; then
    echo "Usage: ./chatgpt_native.sh \"your prompt here\""
    exit 1
fi

# Escape prompt for AppleScript
ESCAPED_PROMPT=$(echo "$PROMPT" | sed 's/"/\\"/g' | sed "s/'/\\\\'/g")

osascript << EOF
-- Activate Brave
tell application "Brave Browser"
    activate
end tell

delay 0.5

-- Type the prompt using System Events
tell application "System Events"
    tell process "Brave Browser"
        set frontmost to true
        delay 0.3

        -- Type the prompt
        keystroke "$ESCAPED_PROMPT"
        delay 0.3

        -- Send (Enter)
        key code 36
    end tell
end tell

return "Prompt sent"
EOF

echo "✓ Prompt sent to ChatGPT"
