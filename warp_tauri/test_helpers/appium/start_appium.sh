#!/bin/bash
# Start Appium server for SAM testing

set -e

# Check if Appium is installed
if ! command -v appium &> /dev/null; then
    echo "Appium not installed. Installing..."
    npm install -g appium
fi

# Check if Mac2 driver is installed
if ! appium driver list --installed 2>/dev/null | grep -q "mac2"; then
    echo "Installing Mac2 driver..."
    appium driver install mac2
fi

echo "Starting Appium server..."
echo "Press Ctrl+C to stop"
echo ""

appium --log-level info
