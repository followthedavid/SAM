#!/bin/bash
# Install SAM launchd services for auto-start at login

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS"
mkdir -p "$HOME/.sam/daemon"

echo "Installing SAM launchd services..."

# Copy plist files
cp "$SCRIPT_DIR/com.sam.daemon.plist" "$LAUNCH_AGENTS/"
cp "$SCRIPT_DIR/com.sam.api.plist" "$LAUNCH_AGENTS/"

# Set permissions
chmod 644 "$LAUNCH_AGENTS/com.sam.daemon.plist"
chmod 644 "$LAUNCH_AGENTS/com.sam.api.plist"

# Unload if already loaded (ignore errors)
launchctl unload "$LAUNCH_AGENTS/com.sam.daemon.plist" 2>/dev/null
launchctl unload "$LAUNCH_AGENTS/com.sam.api.plist" 2>/dev/null

# Load services
echo "Loading com.sam.api..."
launchctl load "$LAUNCH_AGENTS/com.sam.api.plist"

echo "Loading com.sam.daemon..."
launchctl load "$LAUNCH_AGENTS/com.sam.daemon.plist"

# Check status
echo ""
echo "Status:"
launchctl list | grep com.sam || echo "Services not yet started"

echo ""
echo "Done! SAM services will now start automatically at login."
echo ""
echo "Commands:"
echo "  launchctl stop com.sam.api       # Stop API"
echo "  launchctl start com.sam.api      # Start API"
echo "  launchctl stop com.sam.daemon    # Stop daemon"
echo "  launchctl start com.sam.daemon   # Start daemon"
echo ""
echo "Logs:"
echo "  tail -f ~/.sam/daemon/api.stdout.log"
echo "  tail -f ~/.sam/daemon/launchd.stdout.log"
