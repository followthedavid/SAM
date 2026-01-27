#!/usr/bin/env python3
"""
Accessibility API Inspector for SAM

Uses macOS Accessibility APIs to inspect and interact with the SAM app.
Requires: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz

Usage:
    python ax_inspector.py dump          # Dump accessibility tree
    python ax_inspector.py find "button" # Find elements by role
    python ax_inspector.py click "Send"  # Click element by name
    python ax_inspector.py window        # Get window info
"""

import sys
import json
import subprocess
from typing import Optional, Dict, List, Any

try:
    from ApplicationServices import (
        AXUIElementCreateSystemWide,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
        AXUIElementPerformAction,
        AXUIElementCreateApplication,
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
        kAXPressAction,
    )
    from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False
    print("Warning: pyobjc not installed. Install with:")
    print("  pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz")


def get_sam_pid() -> Optional[int]:
    """Get SAM process ID."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "SAM"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0])
    except:
        pass
    return None


def get_ax_value(element, attribute) -> Any:
    """Get accessibility attribute value."""
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err == kAXErrorSuccess:
        return value
    return None


def element_to_dict(element, depth=0, max_depth=5) -> Dict:
    """Convert AXUIElement to dictionary."""
    if depth > max_depth:
        return {"truncated": True}

    result = {}

    # Get common attributes
    attrs_to_get = [
        (kAXRoleAttribute, "role"),
        (kAXTitleAttribute, "title"),
        (kAXRoleDescriptionAttribute, "roleDescription"),
        (kAXValueAttribute, "value"),
        (kAXEnabledAttribute, "enabled"),
        (kAXFocusedAttribute, "focused"),
    ]

    for ax_attr, key in attrs_to_get:
        value = get_ax_value(element, ax_attr)
        if value is not None:
            # Convert to JSON-serializable type
            if isinstance(value, (str, int, float, bool)):
                result[key] = value
            elif hasattr(value, "__iter__") and not isinstance(value, str):
                result[key] = str(value)
            else:
                result[key] = str(value)

    # Get position and size
    pos = get_ax_value(element, kAXPositionAttribute)
    if pos:
        try:
            result["position"] = {"x": pos.x, "y": pos.y}
        except:
            result["position"] = str(pos)

    size = get_ax_value(element, kAXSizeAttribute)
    if size:
        try:
            result["size"] = {"width": size.width, "height": size.height}
        except:
            result["size"] = str(size)

    # Get children
    children = get_ax_value(element, kAXChildrenAttribute)
    if children and len(children) > 0:
        result["children"] = []
        for child in children[:20]:  # Limit children to prevent huge dumps
            result["children"].append(element_to_dict(child, depth + 1, max_depth))

    return result


def find_elements(element, role_filter: str = None, name_filter: str = None, depth=0, max_depth=10) -> List[Dict]:
    """Find elements matching filters."""
    if depth > max_depth:
        return []

    results = []

    role = get_ax_value(element, kAXRoleAttribute)
    title = get_ax_value(element, kAXTitleAttribute)

    # Check if matches
    matches = True
    if role_filter and (not role or role_filter.lower() not in str(role).lower()):
        matches = False
    if name_filter and (not title or name_filter.lower() not in str(title).lower()):
        matches = False

    if matches and (role_filter or name_filter):
        results.append({
            "role": str(role) if role else None,
            "title": str(title) if title else None,
            "position": str(get_ax_value(element, kAXPositionAttribute)),
            "element": element
        })

    # Search children
    children = get_ax_value(element, kAXChildrenAttribute)
    if children:
        for child in children:
            results.extend(find_elements(child, role_filter, name_filter, depth + 1, max_depth))

    return results


def click_element(element) -> bool:
    """Click an accessibility element."""
    try:
        err = AXUIElementPerformAction(element, kAXPressAction)
        return err == kAXErrorSuccess
    except Exception as e:
        print(f"Click failed: {e}")
        return False


def dump_tree(pid: int, max_depth: int = 5) -> Dict:
    """Dump accessibility tree for process."""
    app = AXUIElementCreateApplication(pid)
    windows = get_ax_value(app, kAXWindowsAttribute)

    result = {"pid": pid, "windows": []}

    if windows:
        for window in windows:
            result["windows"].append(element_to_dict(window, 0, max_depth))

    return result


def get_window_info(pid: int) -> List[Dict]:
    """Get window information using Quartz."""
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    result = []

    for window in windows:
        if window.get("kCGWindowOwnerPID") == pid:
            result.append({
                "name": window.get("kCGWindowName", ""),
                "layer": window.get("kCGWindowLayer", 0),
                "bounds": dict(window.get("kCGWindowBounds", {})),
                "alpha": window.get("kCGWindowAlpha", 1.0),
                "isOnscreen": window.get("kCGWindowIsOnscreen", False),
            })

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if not HAS_PYOBJC:
        print("Error: pyobjc required. Install with:")
        print("  pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    pid = get_sam_pid()
    if not pid:
        print("Error: SAM is not running")
        sys.exit(1)

    if command == "dump":
        max_depth = int(args[0]) if args else 5
        result = dump_tree(pid, max_depth)
        print(json.dumps(result, indent=2, default=str))

    elif command == "window":
        result = get_window_info(pid)
        print(json.dumps(result, indent=2))

    elif command == "find":
        if not args:
            print("Usage: ax_inspector.py find <role|name>")
            sys.exit(1)

        filter_text = args[0]
        app = AXUIElementCreateApplication(pid)
        windows = get_ax_value(app, kAXWindowsAttribute)

        all_results = []
        if windows:
            for window in windows:
                # Search by role and name
                results = find_elements(window, role_filter=filter_text)
                results.extend(find_elements(window, name_filter=filter_text))
                all_results.extend(results)

        # Remove element refs for JSON output
        for r in all_results:
            del r["element"]

        print(json.dumps(all_results, indent=2, default=str))

    elif command == "click":
        if not args:
            print("Usage: ax_inspector.py click <element_name>")
            sys.exit(1)

        name = args[0]
        app = AXUIElementCreateApplication(pid)
        windows = get_ax_value(app, kAXWindowsAttribute)

        if windows:
            for window in windows:
                results = find_elements(window, name_filter=name)
                if results:
                    element = results[0]["element"]
                    if click_element(element):
                        print(f"Clicked: {results[0]['title']}")
                        sys.exit(0)
                    else:
                        print(f"Failed to click: {results[0]['title']}")
                        sys.exit(1)

        print(f"Element not found: {name}")
        sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
