#!/bin/bash
# Run XCTest UI Tests for SAM
#
# Usage:
#   ./run_xctest.sh              # Run all tests
#   ./run_xctest.sh testAppLaunches  # Run specific test

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/SAMUITests.xcodeproj"

# Check if Xcode command line tools are available
if ! command -v xcodebuild &> /dev/null; then
    echo "Error: xcodebuild not found. Install Xcode command line tools:"
    echo "  xcode-select --install"
    exit 1
fi

# Check if SAM is running
if ! pgrep -x "SAM" > /dev/null; then
    echo "Warning: SAM is not running. Starting it..."
    # Try to start SAM (adjust path as needed)
    SAM_APP="/Volumes/Plex/DevSymlinks/cargo_target/release/bundle/macos/SAM.app"
    if [ -d "$SAM_APP" ]; then
        open "$SAM_APP"
        sleep 5
    else
        echo "Error: SAM.app not found at $SAM_APP"
        echo "Please start SAM manually or adjust the path"
        exit 1
    fi
fi

# Run tests
echo "Running XCTest UI Tests..."
echo "Project: $PROJECT_DIR"
echo ""

if [ -n "$1" ]; then
    # Run specific test
    echo "Running test: $1"
    xcodebuild test \
        -project "$PROJECT_DIR" \
        -scheme SAMUITests \
        -only-testing:"SAMUITests/SAMUITests/$1" \
        -destination 'platform=macOS' \
        2>&1 | xcpretty || xcodebuild test \
        -project "$PROJECT_DIR" \
        -scheme SAMUITests \
        -only-testing:"SAMUITests/SAMUITests/$1" \
        -destination 'platform=macOS'
else
    # Run all tests
    echo "Running all tests..."
    xcodebuild test \
        -project "$PROJECT_DIR" \
        -scheme SAMUITests \
        -destination 'platform=macOS' \
        2>&1 | xcpretty || xcodebuild test \
        -project "$PROJECT_DIR" \
        -scheme SAMUITests \
        -destination 'platform=macOS'
fi

echo ""
echo "Tests complete!"
