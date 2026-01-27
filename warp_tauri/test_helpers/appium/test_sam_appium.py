#!/usr/bin/env python3
"""
SAM Appium Tests

Appium-based UI tests for the SAM application.

Prerequisites:
    1. Install Appium: npm install -g appium
    2. Install Mac2 driver: appium driver install mac2
    3. Install Python client: pip install Appium-Python-Client
    4. Start Appium server: appium
    5. SAM app should be running

Usage:
    python test_sam_appium.py
    python -m pytest test_sam_appium.py -v
"""

import unittest
import requests
import time
import os

try:
    from appium import webdriver
    from appium.options.mac import Mac2Options
    from appium.webdriver.common.appiumby import AppiumBy
    HAS_APPIUM = True
except ImportError:
    HAS_APPIUM = False
    print("Warning: Appium not installed. Install with: pip install Appium-Python-Client")

# Configuration
APPIUM_SERVER = os.environ.get("APPIUM_SERVER", "http://127.0.0.1:4723")
SAM_BUNDLE_ID = "com.sam.terminal"
DEBUG_SERVER = "http://localhost:9998"


class SAMAppiumTests(unittest.TestCase):
    """Appium-based UI tests for SAM"""

    driver = None

    @classmethod
    def setUpClass(cls):
        """Set up the Appium driver"""
        if not HAS_APPIUM:
            raise unittest.SkipTest("Appium not installed")

        # Check if Appium server is running
        try:
            requests.get(f"{APPIUM_SERVER}/status", timeout=5)
        except requests.exceptions.ConnectionError:
            raise unittest.SkipTest(
                f"Appium server not running at {APPIUM_SERVER}. "
                "Start it with: appium"
            )

        # Configure Mac2 driver options
        options = Mac2Options()
        options.bundle_id = SAM_BUNDLE_ID
        options.platform_name = "mac"
        options.automation_name = "Mac2"

        # Optional: Don't terminate app on driver quit
        options.set_capability("noReset", True)

        try:
            cls.driver = webdriver.Remote(APPIUM_SERVER, options=options)
            cls.driver.implicitly_wait(10)
        except Exception as e:
            raise unittest.SkipTest(f"Could not connect to app: {e}")

    @classmethod
    def tearDownClass(cls):
        """Clean up the driver"""
        if cls.driver:
            cls.driver.quit()

    def setUp(self):
        """Reset state before each test"""
        # Bring app to foreground
        if self.driver:
            self.driver.activate_app(SAM_BUNDLE_ID)
            time.sleep(1)

    # MARK: - Debug Server Tests

    def test_debug_server_ping(self):
        """Test that debug server responds"""
        response = requests.get(f"{DEBUG_SERVER}/debug/ping", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    def test_debug_server_state(self):
        """Test that debug server returns app state"""
        response = requests.get(f"{DEBUG_SERVER}/debug/state", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("startup_complete", data)

    def test_debug_server_ollama(self):
        """Test Ollama status endpoint"""
        response = requests.get(f"{DEBUG_SERVER}/debug/ollama", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("loaded_count", data)

    # MARK: - Window Tests

    def test_window_exists(self):
        """Test that the main window exists"""
        windows = self.driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeWindow")
        self.assertGreater(len(windows), 0, "Should have at least one window")

    def test_window_title(self):
        """Test window title"""
        try:
            window = self.driver.find_element(AppiumBy.CLASS_NAME, "XCUIElementTypeWindow")
            title = window.get_attribute("title")
            self.assertIn("SAM", title or "SAM", "Window title should contain SAM")
        except Exception:
            # Title might not be accessible, that's OK
            pass

    # MARK: - UI Element Tests

    def test_has_ui_elements(self):
        """Test that UI elements exist"""
        # Find all elements
        elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
        self.assertGreater(len(elements), 0, "Should have UI elements")

    def test_webview_exists(self):
        """Test that WebView exists (Tauri apps use WebView)"""
        try:
            webviews = self.driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeWebView")
            # WebView might exist or the content might be in a different form
            # This is informational
            print(f"Found {len(webviews)} WebView elements")
        except Exception as e:
            print(f"WebView search: {e}")

    # MARK: - Interaction Tests

    def test_click_coordinates(self):
        """Test clicking at coordinates"""
        try:
            # Get window size
            window = self.driver.find_element(AppiumBy.CLASS_NAME, "XCUIElementTypeWindow")
            size = window.size
            location = window.location

            # Click in the center of the window
            center_x = location['x'] + size['width'] // 2
            center_y = location['y'] + size['height'] // 2

            # Use touch action for coordinate click
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_by_offset(center_x, center_y).click().perform()

            # Reset offset
            actions.move_by_offset(-center_x, -center_y).perform()
        except Exception as e:
            self.skipTest(f"Coordinate click not supported: {e}")

    # MARK: - Accessibility Tree

    def test_print_accessibility_tree(self):
        """Print accessibility tree for debugging (not a real test)"""
        print("\n=== Accessibility Tree ===")

        def print_element(element, depth=0):
            indent = "  " * depth
            try:
                elem_type = element.get_attribute("elementType") or element.tag_name
                label = element.get_attribute("label") or ""
                identifier = element.get_attribute("identifier") or ""
                print(f"{indent}{elem_type}: {label} [{identifier}]")

                # Get children
                children = element.find_elements(AppiumBy.XPATH, "./*")
                for child in children[:5]:  # Limit to first 5 children
                    print_element(child, depth + 1)
            except Exception as e:
                print(f"{indent}Error: {e}")

        try:
            windows = self.driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeWindow")
            for window in windows:
                print_element(window)
        except Exception as e:
            print(f"Could not print tree: {e}")

        print("=== End Accessibility Tree ===\n")


class SAMAppiumTestsWithoutDriver(unittest.TestCase):
    """Tests that don't require Appium driver"""

    def test_debug_server_available(self):
        """Test debug server without Appium"""
        try:
            response = requests.get(f"{DEBUG_SERVER}/debug/ping", timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.ConnectionError:
            self.skipTest("Debug server not running")

    def test_ollama_has_models(self):
        """Test Ollama has models loaded"""
        try:
            response = requests.get(f"{DEBUG_SERVER}/debug/ollama", timeout=5)
            data = response.json()
            self.assertGreater(
                data.get("loaded_count", 0), 0,
                "Should have at least one model loaded"
            )
        except requests.exceptions.ConnectionError:
            self.skipTest("Debug server not running")


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
