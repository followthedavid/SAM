# SAM Test Helpers

A comprehensive suite of testing tools for the SAM application.

## Quick Start

```bash
# Check app status (debug server, Ollama, window)
./sam_test.sh all

# Warm models
./sam_test.sh warm

# Query app state
curl http://localhost:9998/debug/state
```

## Available Tools

### 1. Debug Server (Built-in)

HTTP endpoints for querying app state. Runs automatically on port 9998.

```bash
# Health check
curl http://localhost:9998/debug/ping

# App state (tabs, errors, routing)
curl http://localhost:9998/debug/state

# Ollama status (loaded models)
curl http://localhost:9998/debug/ollama

# Force-warm models
curl -X POST http://localhost:9998/debug/warm

# Help
curl http://localhost:9998/debug/help
```

### 2. Shell Script Helper (`sam_test.sh`)

Command-line testing utility.

```bash
./sam_test.sh ping       # Check debug server
./sam_test.sh state      # Get app state
./sam_test.sh ollama     # Get Ollama status
./sam_test.sh warm       # Warm all models
./sam_test.sh focus      # Bring SAM window to front
./sam_test.sh click X Y  # Click at coordinates
./sam_test.sh type "hi"  # Type text
./sam_test.sh ax-dump    # Dump accessibility tree
./sam_test.sh all        # Run all checks
```

### 3. JavaScript Automation (`sam_automation.js`)

JXA (JavaScript for Automation) for advanced scripting.

```bash
osascript sam_automation.js focus
osascript sam_automation.js windows
osascript sam_automation.js click 100 200
osascript sam_automation.js type "Hello"
osascript sam_automation.js inspect
osascript sam_automation.js test startup
```

### 4. Accessibility Inspector (`ax_inspector.py`)

Python tool using macOS Accessibility APIs.

```bash
# Requires: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz

python ax_inspector.py dump          # Dump accessibility tree
python ax_inspector.py find "button" # Find elements by role/name
python ax_inspector.py click "Send"  # Click element by name
python ax_inspector.py window        # Get window info
```

### 5. XCTest UI Tests (`SAMUITests.xcodeproj`)

Native Xcode UI testing framework.

```bash
# Run all tests
./run_xctest.sh

# Run specific test
./run_xctest.sh testAppLaunches

# Or open in Xcode
open SAMUITests.xcodeproj
# Then press Cmd+U to run tests
```

### 6. Appium Tests (`appium/`)

Cross-platform automation framework.

```bash
# Setup
npm install -g appium
appium driver install mac2
pip install Appium-Python-Client

# Start Appium server
./appium/start_appium.sh

# Run tests (in another terminal)
python appium/test_sam_appium.py
```

## Testing Workflow

### Quick Smoke Test
```bash
./sam_test.sh all
```

### Full Test Suite
```bash
# 1. Check debug server
./sam_test.sh ping

# 2. Warm models
./sam_test.sh warm

# 3. Run XCTest
./run_xctest.sh

# 4. Run Appium tests (if configured)
python appium/test_sam_appium.py
```

### Debugging UI Issues
```bash
# 1. Dump accessibility tree
./sam_test.sh ax-dump

# 2. Get detailed tree with Python
python ax_inspector.py dump

# 3. Check app state
curl http://localhost:9998/debug/state | python -m json.tool
```

## Environment Variables

- `SAM_DEBUG_PORT` - Debug server port (default: 9998)
- `APPIUM_SERVER` - Appium server URL (default: http://127.0.0.1:4723)

## Troubleshooting

### Debug server not responding
- Make sure SAM is running
- Check if port 9998 is in use: `lsof -i :9998`

### XCTest can't find elements
- WebView content may not expose accessibility
- Add `aria-label` attributes to Vue components
- Use coordinate-based clicks as fallback

### Appium connection failed
- Start Appium server: `appium`
- Install Mac2 driver: `appium driver install mac2`
- Grant accessibility permissions to Terminal

### Models not loading
- Warm models: `./sam_test.sh warm`
- Check Ollama: `curl http://localhost:11434/api/ps`
- Restart Ollama if needed
