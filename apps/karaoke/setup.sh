#!/bin/bash
# SAM Karaoke App Setup Script
# Generates Xcode projects using XcodeGen

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  SAM Karaoke - Xcode Project Setup"
echo "========================================"
echo

# Check for XcodeGen
if ! command -v xcodegen &> /dev/null; then
    echo "XcodeGen not found. Installing via Homebrew..."
    brew install xcodegen
fi

# Create karaoke library directory
LIBRARY_DIR="/Users/Shared/SAMKaraoke"
if [ ! -d "$LIBRARY_DIR" ]; then
    echo "Creating karaoke library directory: $LIBRARY_DIR"
    mkdir -p "$LIBRARY_DIR"
fi

# Generate Xcode project
echo "Generating Xcode project..."
xcodegen generate

echo
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo
echo "Next steps:"
echo
echo "1. Open the project:"
echo "   open SAMKaraoke.xcodeproj"
echo
echo "2. Select your Apple ID for signing:"
echo "   - Click SAMKaraoke project in sidebar"
echo "   - Select each target (SAMKaraoke, SAMKaraokeTV)"
echo "   - Signing & Capabilities → Team → Your Apple ID"
echo
echo "3. Deploy iOS app:"
echo "   - Connect iPhone via USB"
echo "   - Select iPhone in device dropdown"
echo "   - Press Cmd+R to build & run"
echo "   - Trust developer: Settings → General → VPN & Device Management"
echo
echo "4. Deploy tvOS app:"
echo "   - Connect Apple TV via USB-C"
echo "   - Select Apple TV in device dropdown"
echo "   - Press Cmd+R to build & run"
echo
echo "5. Generate karaoke videos:"
echo "   cd ~/ReverseLab/SAM/media/karaoke"
echo "   python3 generate_karaoke.py -i song.m4a -o $LIBRARY_DIR/"
echo
echo "Karaoke library: $LIBRARY_DIR"
echo
