#!/bin/bash
# Uninstall SAM launchd services

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "Uninstalling SAM launchd services..."

# Unload services
launchctl unload "$LAUNCH_AGENTS/com.sam.daemon.plist" 2>/dev/null
launchctl unload "$LAUNCH_AGENTS/com.sam.api.plist" 2>/dev/null

# Remove plist files
rm -f "$LAUNCH_AGENTS/com.sam.daemon.plist"
rm -f "$LAUNCH_AGENTS/com.sam.api.plist"

echo "Done! SAM services will no longer start automatically."
