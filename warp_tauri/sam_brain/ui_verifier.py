#!/usr/bin/env python3
"""
SAM UI Verifier - Knows What's ACTUALLY Happening

No screenshots. No guessing. SAM reads the actual UI state.

Uses macOS Accessibility APIs to:
1. Read exact UI element state (text, buttons, status)
2. Detect errors, loading states, success/failure
3. Verify actions actually completed
4. Monitor apps in real-time

How It Works:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │  macOS Accessibility APIs (AXUIElement)                                 │
  │    │                                                                     │
  │    ├── Application Tree                                                 │
  │    │   ├── Window 1                                                     │
  │    │   │   ├── Button: "Submit" (enabled: true)                        │
  │    │   │   ├── TextField: "user input here"                            │
  │    │   │   ├── StaticText: "Error: Invalid input"  ◄── SAM sees this   │
  │    │   │   └── ProgressIndicator (running: true)   ◄── SAM sees this   │
  │    │   └── Window 2...                                                  │
  │    │                                                                     │
  │    └── SAM can:                                                         │
  │        • Read all text without screenshots                              │
  │        • See if buttons are enabled/disabled                            │
  │        • Detect loading spinners                                        │
  │        • Find error messages                                            │
  │        • Click buttons programmatically                                 │
  │        • Type into text fields                                          │
  │                                                                          │
  └─────────────────────────────────────────────────────────────────────────┘

Requirements:
    pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz

    System Preferences > Privacy & Security > Accessibility > Enable Terminal/Python

Usage:
    # Verify an app's state
    python3 ui_verifier.py verify SAM

    # Watch for changes
    python3 ui_verifier.py watch SAM

    # Find errors
    python3 ui_verifier.py errors SAM

    # Check if something succeeded
    python3 ui_verifier.py check SAM "Success"
"""

import os
import sys
import json
import time
import re
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

# Paths
LOG_PATH = Path("/Volumes/David External/sam_logs/ui_verifier.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ui_verifier")

# Try to import Accessibility APIs
try:
    from ApplicationServices import (
        AXUIElementCreateSystemWide,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
        AXUIElementPerformAction,
        AXUIElementCreateApplication,
        AXUIElementSetAttributeValue,
        AXIsProcessTrusted,
        kAXErrorSuccess,
        kAXFocusedApplicationAttribute,
        kAXWindowsAttribute,
        kAXTitleAttribute,
        kAXRoleAttribute,
        kAXRoleDescriptionAttribute,
        kAXPositionAttribute,
        kAXSizeAttribute,
        kAXChildrenAttribute,
        kAXEnabledAttribute,
        kAXFocusedAttribute,
        kAXValueAttribute,
        kAXDescriptionAttribute,
        kAXPressAction,
        kAXSelectedTextAttribute,
    )
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    HAS_AX = True
except ImportError:
    HAS_AX = False
    logger.warning("pyobjc not installed. Run: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz")


# ═══════════════════════════════════════════════════════════════════════════════
# UI STATE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class UIState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    WAITING = "waiting"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    role: str
    title: Optional[str]
    value: Optional[str]
    enabled: bool
    focused: bool
    position: Optional[Dict]
    size: Optional[Dict]
    children_count: int
    description: Optional[str] = None


@dataclass
class AppState:
    name: str
    pid: int
    state: UIState
    windows: List[Dict]
    errors: List[str]
    loading_indicators: List[str]
    success_indicators: List[str]
    all_text: List[str]
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR/SUCCESS DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

ERROR_PATTERNS = [
    r"error",
    r"failed",
    r"failure",
    r"could not",
    r"couldn't",
    r"unable to",
    r"invalid",
    r"not found",
    r"timed? out",
    r"exception",
    r"crash",
    r"denied",
    r"refused",
    r"unauthorized",
    r"forbidden",
    r"bad request",
    r"not available",
    r"disconnected",
    r"offline",
]

SUCCESS_PATTERNS = [
    r"success",
    r"completed",
    r"done",
    r"saved",
    r"created",
    r"updated",
    r"uploaded",
    r"connected",
    r"ready",
    r"✓",
    r"✔",
    r"👍",
]

LOADING_PATTERNS = [
    r"loading",
    r"please wait",
    r"processing",
    r"in progress",
    r"working",
    r"thinking",
    r"\.\.\.",
    r"fetching",
    r"connecting",
]


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESSIBILITY HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_accessibility_permissions() -> bool:
    """Check if we have accessibility permissions."""
    if not HAS_AX:
        return False
    return AXIsProcessTrusted()


def get_ax_value(element, attribute) -> Any:
    """Get accessibility attribute value."""
    if not HAS_AX:
        return None
    try:
        err, value = AXUIElementCopyAttributeValue(element, attribute, None)
        if err == kAXErrorSuccess:
            return value
    except:
        pass
    return None


def get_ax_attributes(element) -> List[str]:
    """Get all attribute names for an element."""
    if not HAS_AX:
        return []
    try:
        err, attrs = AXUIElementCopyAttributeNames(element, None)
        if err == kAXErrorSuccess:
            return list(attrs)
    except:
        pass
    return []


def find_app_pid(app_name: str) -> Optional[int]:
    """Find PID for an app by name."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            return int(pids[0]) if pids else None
    except:
        pass

    # Try case-insensitive
    try:
        result = subprocess.run(
            ["pgrep", "-i", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            return int(pids[0]) if pids else None
    except:
        pass

    return None


def find_all_apps() -> List[Dict]:
    """Find all running GUI apps."""
    apps = []

    if not HAS_AX:
        return apps

    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    seen_pids = set()
    for window in windows:
        pid = window.get("kCGWindowOwnerPID")
        name = window.get("kCGWindowOwnerName", "")

        if pid and pid not in seen_pids and name:
            seen_pids.add(pid)
            apps.append({
                "name": name,
                "pid": pid,
            })

    return apps


# ═══════════════════════════════════════════════════════════════════════════════
# UI ELEMENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_element(element, depth=0, max_depth=10) -> Optional[UIElement]:
    """Extract UI element info."""
    if depth > max_depth:
        return None

    role = get_ax_value(element, kAXRoleAttribute)
    title = get_ax_value(element, kAXTitleAttribute)
    value = get_ax_value(element, kAXValueAttribute)
    enabled = get_ax_value(element, kAXEnabledAttribute)
    focused = get_ax_value(element, kAXFocusedAttribute)
    desc = get_ax_value(element, kAXDescriptionAttribute)

    pos = get_ax_value(element, kAXPositionAttribute)
    size = get_ax_value(element, kAXSizeAttribute)

    children = get_ax_value(element, kAXChildrenAttribute)
    children_count = len(children) if children else 0

    position = None
    if pos:
        try:
            position = {"x": pos.x, "y": pos.y}
        except:
            pass

    size_dict = None
    if size:
        try:
            size_dict = {"width": size.width, "height": size.height}
        except:
            pass

    return UIElement(
        role=str(role) if role else "",
        title=str(title) if title else None,
        value=str(value) if value else None,
        enabled=bool(enabled) if enabled is not None else True,
        focused=bool(focused) if focused is not None else False,
        position=position,
        size=size_dict,
        children_count=children_count,
        description=str(desc) if desc else None,
    )


def extract_all_text(element, depth=0, max_depth=15) -> List[str]:
    """Extract all visible text from UI tree."""
    if depth > max_depth:
        return []

    texts = []

    # Get text from this element
    title = get_ax_value(element, kAXTitleAttribute)
    value = get_ax_value(element, kAXValueAttribute)
    desc = get_ax_value(element, kAXDescriptionAttribute)

    for text in [title, value, desc]:
        if text and isinstance(text, str) and len(text.strip()) > 0:
            texts.append(text.strip())

    # Recurse into children
    children = get_ax_value(element, kAXChildrenAttribute)
    if children:
        for child in children:
            texts.extend(extract_all_text(child, depth + 1, max_depth))

    return texts


def find_elements_by_role(element, role_filter: str, depth=0, max_depth=15) -> List:
    """Find all elements with matching role."""
    if depth > max_depth:
        return []

    results = []

    role = get_ax_value(element, kAXRoleAttribute)
    if role and role_filter.lower() in str(role).lower():
        results.append(element)

    children = get_ax_value(element, kAXChildrenAttribute)
    if children:
        for child in children:
            results.extend(find_elements_by_role(child, role_filter, depth + 1, max_depth))

    return results


def find_elements_by_text(element, text_filter: str, depth=0, max_depth=15) -> List:
    """Find all elements containing text."""
    if depth > max_depth:
        return []

    results = []

    title = get_ax_value(element, kAXTitleAttribute)
    value = get_ax_value(element, kAXValueAttribute)

    for text in [title, value]:
        if text and text_filter.lower() in str(text).lower():
            results.append(element)
            break

    children = get_ax_value(element, kAXChildrenAttribute)
    if children:
        for child in children:
            results.extend(find_elements_by_text(child, text_filter, depth + 1, max_depth))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# STATE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_state(all_text: List[str]) -> Tuple[UIState, List[str], List[str], List[str]]:
    """Detect app state from extracted text."""
    errors = []
    loading = []
    success = []

    combined_text = " ".join(all_text).lower()

    # Check for errors
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, combined_text):
            # Find the actual text that matched
            for text in all_text:
                if re.search(pattern, text.lower()):
                    errors.append(text)
                    break

    # Check for loading
    for pattern in LOADING_PATTERNS:
        if re.search(pattern, combined_text):
            for text in all_text:
                if re.search(pattern, text.lower()):
                    loading.append(text)
                    break

    # Check for success
    for pattern in SUCCESS_PATTERNS:
        if re.search(pattern, combined_text):
            for text in all_text:
                if re.search(pattern, text.lower()):
                    success.append(text)
                    break

    # Determine overall state
    if errors:
        state = UIState.ERROR
    elif loading:
        state = UIState.LOADING
    elif success:
        state = UIState.SUCCESS
    elif all_text:
        state = UIState.IDLE
    else:
        state = UIState.UNKNOWN

    return state, errors, loading, success


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN VERIFIER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class UIVerifier:
    """
    Verifies actual UI state without screenshots.

    SAM uses this to KNOW what's happening, not guess.
    """

    def __init__(self):
        if not HAS_AX:
            raise RuntimeError("pyobjc required: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz")

        if not check_accessibility_permissions():
            logger.warning("Accessibility permissions not granted. Enable in System Preferences > Privacy > Accessibility")

    def get_app_state(self, app_name: str) -> Optional[AppState]:
        """Get complete state of an app."""
        pid = find_app_pid(app_name)
        if not pid:
            logger.error(f"App not found: {app_name}")
            return None

        app = AXUIElementCreateApplication(pid)
        windows = get_ax_value(app, kAXWindowsAttribute)

        if not windows:
            return AppState(
                name=app_name,
                pid=pid,
                state=UIState.UNKNOWN,
                windows=[],
                errors=[],
                loading_indicators=[],
                success_indicators=[],
                all_text=[],
                timestamp=datetime.now().isoformat(),
            )

        all_text = []
        window_info = []

        for window in windows:
            title = get_ax_value(window, kAXTitleAttribute)
            pos = get_ax_value(window, kAXPositionAttribute)
            size = get_ax_value(window, kAXSizeAttribute)

            window_info.append({
                "title": str(title) if title else "",
                "position": {"x": pos.x, "y": pos.y} if pos else None,
                "size": {"width": size.width, "height": size.height} if size else None,
            })

            # Extract all text from this window
            all_text.extend(extract_all_text(window))

        # Detect state
        state, errors, loading, success = detect_state(all_text)

        return AppState(
            name=app_name,
            pid=pid,
            state=state,
            windows=window_info,
            errors=errors,
            loading_indicators=loading,
            success_indicators=success,
            all_text=all_text,
            timestamp=datetime.now().isoformat(),
        )

    def verify_contains(self, app_name: str, text: str) -> bool:
        """Verify app UI contains specific text."""
        state = self.get_app_state(app_name)
        if not state:
            return False

        text_lower = text.lower()
        for t in state.all_text:
            if text_lower in t.lower():
                return True
        return False

    def verify_no_errors(self, app_name: str) -> Tuple[bool, List[str]]:
        """Verify app has no error states."""
        state = self.get_app_state(app_name)
        if not state:
            return False, ["App not found"]

        if state.errors:
            return False, state.errors
        return True, []

    def verify_ready(self, app_name: str) -> bool:
        """Verify app is in ready/idle state (not loading, no errors)."""
        state = self.get_app_state(app_name)
        if not state:
            return False

        return state.state in [UIState.IDLE, UIState.SUCCESS]

    def wait_for_state(self, app_name: str, target_state: UIState,
                       timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """Wait for app to reach target state."""
        start = time.time()

        while time.time() - start < timeout:
            state = self.get_app_state(app_name)
            if state and state.state == target_state:
                return True
            time.sleep(poll_interval)

        return False

    def wait_for_text(self, app_name: str, text: str,
                      timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """Wait for specific text to appear."""
        start = time.time()

        while time.time() - start < timeout:
            if self.verify_contains(app_name, text):
                return True
            time.sleep(poll_interval)

        return False

    def wait_for_no_loading(self, app_name: str,
                            timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """Wait for loading to complete."""
        start = time.time()

        while time.time() - start < timeout:
            state = self.get_app_state(app_name)
            if state and state.state != UIState.LOADING:
                return True
            time.sleep(poll_interval)

        return False

    def click_button(self, app_name: str, button_name: str) -> bool:
        """Click a button by name."""
        pid = find_app_pid(app_name)
        if not pid:
            return False

        app = AXUIElementCreateApplication(pid)
        windows = get_ax_value(app, kAXWindowsAttribute)

        if not windows:
            return False

        for window in windows:
            buttons = find_elements_by_role(window, "button")
            for button in buttons:
                title = get_ax_value(button, kAXTitleAttribute)
                if title and button_name.lower() in str(title).lower():
                    try:
                        err = AXUIElementPerformAction(button, kAXPressAction)
                        return err == kAXErrorSuccess
                    except:
                        pass

            # Also check by text content
            text_matches = find_elements_by_text(window, button_name)
            for element in text_matches:
                role = get_ax_value(element, kAXRoleAttribute)
                if role and "button" in str(role).lower():
                    try:
                        err = AXUIElementPerformAction(element, kAXPressAction)
                        return err == kAXErrorSuccess
                    except:
                        pass

        return False

    def type_text(self, app_name: str, text: str) -> bool:
        """Type text into focused field."""
        pid = find_app_pid(app_name)
        if not pid:
            return False

        app = AXUIElementCreateApplication(pid)

        # Find focused element
        focused = get_ax_value(app, kAXFocusedAttribute)
        if focused:
            try:
                err = AXUIElementSetAttributeValue(focused, kAXValueAttribute, text)
                return err == kAXErrorSuccess
            except:
                pass

        return False

    def watch(self, app_name: str, callback: Callable[[AppState], None],
              interval: float = 1.0, duration: int = 60):
        """Watch app state changes."""
        start = time.time()
        last_state = None

        while time.time() - start < duration:
            state = self.get_app_state(app_name)

            if state and (not last_state or state.state != last_state.state):
                callback(state)
                last_state = state

            time.sleep(interval)


# ═══════════════════════════════════════════════════════════════════════════════
# SAM INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class SAMUIAwareness:
    """
    Gives SAM real awareness of what's happening in apps.

    No more saying "it should work" - SAM KNOWS if it worked.
    """

    def __init__(self):
        self.verifier = UIVerifier()
        self.last_states = {}

    def check_action_result(self, app_name: str, expected_outcome: str) -> Dict:
        """
        After SAM suggests an action, verify it actually worked.

        Returns:
            {
                "success": bool,
                "actual_state": "...",
                "expected": "...",
                "errors_found": [...],
                "confidence": 0.0-1.0
            }
        """
        state = self.verifier.get_app_state(app_name)

        if not state:
            return {
                "success": False,
                "actual_state": "unknown",
                "expected": expected_outcome,
                "errors_found": ["Could not access app"],
                "confidence": 0.0,
            }

        # Check if expected outcome is present
        expected_found = any(
            expected_outcome.lower() in t.lower()
            for t in state.all_text
        )

        # Check for errors
        has_errors = len(state.errors) > 0

        # Determine success
        success = expected_found and not has_errors

        # Calculate confidence
        if success:
            confidence = 0.9
        elif expected_found and has_errors:
            confidence = 0.5  # Partial success
        elif not expected_found and not has_errors:
            confidence = 0.3  # Uncertain
        else:
            confidence = 0.1  # Likely failed

        return {
            "success": success,
            "actual_state": state.state.value,
            "expected": expected_outcome,
            "errors_found": state.errors,
            "all_visible_text": state.all_text[:20],  # First 20 for context
            "confidence": confidence,
        }

    def verify_before_responding(self, app_name: str, claim: str) -> str:
        """
        Before SAM says "it worked", verify it actually did.

        Returns a verified statement or correction.
        """
        state = self.verifier.get_app_state(app_name)

        if not state:
            return f"I cannot verify the state of {app_name} - it may not be running or I lack accessibility permissions."

        if state.errors:
            return f"Actually, I see an error: {state.errors[0]}. The action may not have succeeded."

        if state.state == UIState.LOADING:
            return f"The action is still in progress - I see: {state.loading_indicators[0] if state.loading_indicators else 'loading indicator'}"

        if state.state == UIState.SUCCESS:
            return claim  # Original claim is verified

        # Uncertain - be honest
        return f"I initiated the action but cannot confirm success. Current state: {state.state.value}"

    def get_real_situation(self, app_name: str) -> str:
        """
        Get honest assessment of what's happening in the app.
        """
        state = self.verifier.get_app_state(app_name)

        if not state:
            return f"Cannot access {app_name}. Either it's not running or accessibility permissions are needed."

        lines = [f"**{app_name} Current State: {state.state.value}**"]

        if state.errors:
            lines.append(f"\n⚠️ Errors detected:")
            for err in state.errors[:5]:
                lines.append(f"  - {err}")

        if state.loading_indicators:
            lines.append(f"\n⏳ Loading:")
            for load in state.loading_indicators[:3]:
                lines.append(f"  - {load}")

        if state.success_indicators:
            lines.append(f"\n✅ Success indicators:")
            for succ in state.success_indicators[:3]:
                lines.append(f"  - {succ}")

        if state.windows:
            lines.append(f"\n📱 Windows: {len(state.windows)}")
            for w in state.windows[:3]:
                lines.append(f"  - {w.get('title', 'Untitled')}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print(__doc__)

        # Show running apps
        print("\n📱 Running Apps:")
        for app in find_all_apps():
            print(f"  - {app['name']} (PID: {app['pid']})")

        # Check permissions
        if HAS_AX:
            if check_accessibility_permissions():
                print("\n✅ Accessibility permissions: GRANTED")
            else:
                print("\n❌ Accessibility permissions: NOT GRANTED")
                print("   Enable in: System Preferences > Privacy & Security > Accessibility")
        else:
            print("\n❌ pyobjc not installed. Run:")
            print("   pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz")

        sys.exit(0)

    cmd = sys.argv[1]
    app_name = sys.argv[2] if len(sys.argv) > 2 else "SAM"

    verifier = UIVerifier()

    if cmd == "verify" or cmd == "state":
        state = verifier.get_app_state(app_name)
        if state:
            print(f"\n📱 {app_name} State")
            print("=" * 50)
            print(f"State: {state.state.value}")
            print(f"PID: {state.pid}")
            print(f"Windows: {len(state.windows)}")

            if state.errors:
                print(f"\n⚠️ Errors:")
                for err in state.errors:
                    print(f"  - {err}")

            if state.loading_indicators:
                print(f"\n⏳ Loading:")
                for load in state.loading_indicators:
                    print(f"  - {load}")

            if state.success_indicators:
                print(f"\n✅ Success:")
                for succ in state.success_indicators:
                    print(f"  - {succ}")

            print(f"\n📝 All Text ({len(state.all_text)} items):")
            for text in state.all_text[:20]:
                print(f"  - {text[:80]}...")

        else:
            print(f"Could not get state for: {app_name}")

    elif cmd == "errors":
        ok, errors = verifier.verify_no_errors(app_name)
        if ok:
            print(f"✅ No errors in {app_name}")
        else:
            print(f"❌ Errors in {app_name}:")
            for err in errors:
                print(f"  - {err}")

    elif cmd == "check":
        text = sys.argv[3] if len(sys.argv) > 3 else ""
        if not text:
            print("Usage: ui_verifier.py check APP_NAME TEXT_TO_FIND")
            sys.exit(1)

        if verifier.verify_contains(app_name, text):
            print(f"✅ Found '{text}' in {app_name}")
        else:
            print(f"❌ '{text}' not found in {app_name}")

    elif cmd == "watch":
        def on_change(state: AppState):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {state.state.value}: {len(state.all_text)} text items")
            if state.errors:
                print(f"  ⚠️ Errors: {state.errors}")

        print(f"Watching {app_name}... (Ctrl+C to stop)")
        try:
            verifier.watch(app_name, on_change, interval=1.0, duration=3600)
        except KeyboardInterrupt:
            print("\nStopped.")

    elif cmd == "click":
        button_name = sys.argv[3] if len(sys.argv) > 3 else ""
        if not button_name:
            print("Usage: ui_verifier.py click APP_NAME BUTTON_NAME")
            sys.exit(1)

        if verifier.click_button(app_name, button_name):
            print(f"✅ Clicked '{button_name}'")
        else:
            print(f"❌ Could not click '{button_name}'")

    elif cmd == "apps":
        print("\n📱 Running Apps:")
        for app in find_all_apps():
            print(f"  - {app['name']} (PID: {app['pid']})")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: verify, errors, check, watch, click, apps")


if __name__ == "__main__":
    main()
