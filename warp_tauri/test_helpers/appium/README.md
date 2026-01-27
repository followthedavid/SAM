# Appium Setup for SAM Testing

Appium provides cross-platform automation for testing macOS applications.

## Installation

1. Install Node.js (if not already installed):
   ```bash
   brew install node
   ```

2. Install Appium:
   ```bash
   npm install -g appium
   ```

3. Install the Mac2 driver (for macOS testing):
   ```bash
   appium driver install mac2
   ```

4. Install Python Appium client:
   ```bash
   pip install Appium-Python-Client
   ```

## Running Tests

1. Start Appium server:
   ```bash
   appium
   ```
   Or use the included script:
   ```bash
   ./start_appium.sh
   ```

2. Make sure SAM is running

3. Run tests:
   ```bash
   python test_sam_appium.py
   ```

## Capabilities

The Mac2 driver uses these capabilities:

- `platformName`: "mac"
- `automationName`: "Mac2"
- `bundleId`: "com.sam.terminal"
- `arguments`: [] (optional launch arguments)
- `environment`: {} (optional environment variables)

## Troubleshooting

1. **Driver not found**: Make sure you installed the mac2 driver
   ```bash
   appium driver list --installed
   ```

2. **Permission denied**: Grant accessibility permissions to Terminal/Appium
   System Preferences > Security & Privacy > Privacy > Accessibility

3. **App not found**: Verify the bundle ID matches your app
   ```bash
   mdls -name kMDItemCFBundleIdentifier /path/to/SAM.app
   ```
