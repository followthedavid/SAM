#!/bin/bash
# SAM Karaoke Auto-Redeploy Script
# Rebuilds and deploys to iOS and tvOS devices over WiFi
#
# Prerequisites:
# 1. Devices paired for wireless debugging in Xcode
# 2. Xcode project generated (./setup.sh)
# 3. Signing configured in Xcode
#
# Run weekly via: crontab -e
# 0 9 * * 0 /Users/davidquinton/ReverseLab/SAM/apps/karaoke/redeploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$SCRIPT_DIR/SAMKaraoke.xcodeproj"
LOG_FILE="$SCRIPT_DIR/redeploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "SAM Karaoke Auto-Redeploy"
log "=========================================="

# Check if project exists
if [ ! -d "$PROJECT" ]; then
    log "ERROR: Xcode project not found. Run ./setup.sh first"
    exit 1
fi

cd "$SCRIPT_DIR"

# Get list of connected devices (USB or WiFi)
log "Finding connected devices..."
DEVICES=$(xcrun xctrace list devices 2>/dev/null | grep -E "iPhone|Apple TV" | head -2)
echo "$DEVICES" | tee -a "$LOG_FILE"

if [ -z "$DEVICES" ]; then
    log "ERROR: No devices found. Ensure devices are:"
    log "  - On same WiFi network"
    log "  - Paired for wireless debugging in Xcode"
    exit 1
fi

# Extract device IDs
IOS_DEVICE=$(echo "$DEVICES" | grep -i "iPhone" | sed 's/.*(\(.*\))/\1/' | head -1)
TVOS_DEVICE=$(echo "$DEVICES" | grep -i "Apple TV" | sed 's/.*(\(.*\))/\1/' | head -1)

# Build and deploy iOS app
if [ -n "$IOS_DEVICE" ]; then
    log "Building iOS app..."
    xcodebuild -project "$PROJECT" \
        -scheme "SAMKaraoke" \
        -destination "id=$IOS_DEVICE" \
        -allowProvisioningUpdates \
        build 2>&1 | tail -5 | tee -a "$LOG_FILE"

    log "Installing on iPhone ($IOS_DEVICE)..."
    xcodebuild -project "$PROJECT" \
        -scheme "SAMKaraoke" \
        -destination "id=$IOS_DEVICE" \
        -allowProvisioningUpdates \
        install 2>&1 | tail -5 | tee -a "$LOG_FILE"

    log "iOS deployment complete"
else
    log "WARNING: No iPhone found"
fi

# Build and deploy tvOS app
if [ -n "$TVOS_DEVICE" ]; then
    log "Building tvOS app..."
    xcodebuild -project "$PROJECT" \
        -scheme "SAMKaraokeTV" \
        -destination "id=$TVOS_DEVICE" \
        -allowProvisioningUpdates \
        build 2>&1 | tail -5 | tee -a "$LOG_FILE"

    log "Installing on Apple TV ($TVOS_DEVICE)..."
    xcodebuild -project "$PROJECT" \
        -scheme "SAMKaraokeTV" \
        -destination "id=$TVOS_DEVICE" \
        -allowProvisioningUpdates \
        install 2>&1 | tail -5 | tee -a "$LOG_FILE"

    log "tvOS deployment complete"
else
    log "WARNING: No Apple TV found"
fi

log "=========================================="
log "Redeploy complete!"
log "Next expiry: $(date -v+7d '+%Y-%m-%d')"
log "=========================================="

# Optional: Send notification
osascript -e 'display notification "Apps refreshed for 7 more days" with title "SAM Karaoke"' 2>/dev/null || true
