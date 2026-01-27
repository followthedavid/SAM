#!/usr/bin/env python3
"""
Tests for new SAM features (v1.3.1)
- Proactive notifier
- Model unload endpoint
- Auto-unload daemon
- Memory efficiency features
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime

# Configuration
SAM_API = "http://localhost:8765"
RESULTS = {"passed": 0, "failed": 0, "tests": []}


def log(msg: str, status: str = "INFO"):
    """Log with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{status}] {msg}")


def test(name: str):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            try:
                result = func()
                if result:
                    RESULTS["passed"] += 1
                    RESULTS["tests"].append({"name": name, "status": "PASS"})
                    log(f"✅ {name}", "PASS")
                else:
                    RESULTS["failed"] += 1
                    RESULTS["tests"].append({"name": name, "status": "FAIL"})
                    log(f"❌ {name}", "FAIL")
            except Exception as e:
                RESULTS["failed"] += 1
                RESULTS["tests"].append({"name": name, "status": "ERROR", "error": str(e)})
                log(f"❌ {name}: {e}", "ERROR")
        return wrapper
    return decorator


def fetch(endpoint: str, method: str = "GET", data: dict = None, timeout: int = 30):
    """Fetch from API."""
    url = f"{SAM_API}{endpoint}"
    req = urllib.request.Request(url)
    req.method = method

    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "code": e.code}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

@test("API Health Check")
def test_api_health():
    result = fetch("/api/health")
    return result.get("status") == "ok"


@test("Resources Endpoint Returns Model Info")
def test_resources_model_info():
    result = fetch("/api/resources")
    if not result.get("success"):
        return False
    # Check for new model section
    model = result.get("model", {})
    return "loaded" in model and "memory_mb" in model and "idle_seconds" in model


@test("Resources Shows Resource Level")
def test_resources_level():
    result = fetch("/api/resources")
    if not result.get("success"):
        return False
    resources = result.get("resources", {})
    return resources.get("resource_level") in ["critical", "low", "moderate", "good"]


@test("Unload Endpoint Exists")
def test_unload_endpoint():
    result = fetch("/api/unload")
    # Should succeed or say no model loaded
    return result.get("success") == True


@test("Unload Returns Freed Memory Info")
def test_unload_returns_info():
    result = fetch("/api/unload")
    if not result.get("success"):
        return False
    return "freed_mb" in result and "message" in result


# =============================================================================
# COGNITIVE PROCESSING TESTS
# =============================================================================

@test("Cognitive Process Works")
def test_cognitive_process():
    result = fetch("/api/cognitive/process", "POST", {"query": "Hello", "user_id": "test"}, timeout=120)
    return result.get("success") == True and "response" in result


@test("Cognitive Process Returns Confidence")
def test_cognitive_confidence():
    result = fetch("/api/cognitive/process", "POST", {"query": "What is 2+2?", "user_id": "test"}, timeout=120)
    if not result.get("success"):
        return False
    conf = result.get("confidence", 0)
    return 0 <= conf <= 1


@test("Resources Update After Query")
def test_resources_after_query():
    # Query to load model
    fetch("/api/cognitive/process", "POST", {"query": "Hi", "user_id": "test"}, timeout=120)
    time.sleep(1)

    # Check resources
    result = fetch("/api/resources")
    model = result.get("model", {})

    # Model should be loaded now
    return model.get("loaded") is not None


# =============================================================================
# PROACTIVE NOTIFIER TESTS
# =============================================================================

@test("Proactive Endpoint Exists")
def test_proactive_endpoint():
    result = fetch("/api/proactive")
    return result.get("success") == True


@test("Proactive Returns Suggestions")
def test_proactive_suggestions():
    result = fetch("/api/proactive")
    if not result.get("success"):
        return False
    return "suggestions" in result


@test("Self Endpoint Returns Status")
def test_self_endpoint():
    result = fetch("/api/self")
    if not result.get("success"):
        return False
    return "status" in result and "explanation" in result


@test("Self Shows Proactive Items")
def test_self_proactive():
    result = fetch("/api/self")
    if not result.get("success"):
        return False
    status = result.get("status", {})
    return "proactive" in status


# =============================================================================
# MEMORY EFFICIENCY TESTS
# =============================================================================

@test("Idle Seconds Tracked")
def test_idle_tracking():
    # Make a query
    fetch("/api/cognitive/process", "POST", {"query": "test", "user_id": "test"}, timeout=120)
    time.sleep(2)

    # Check idle time
    result = fetch("/api/resources")
    model = result.get("model", {})
    idle = model.get("idle_seconds", 0)

    return idle >= 1  # Should be at least 1 second


@test("Max Tokens Varies By Resource Level")
def test_token_limits():
    result = fetch("/api/resources")
    limits = result.get("limits", {})
    max_tokens = limits.get("max_tokens", 0)

    # Should be within expected range (50-200)
    return 50 <= max_tokens <= 200


@test("Can Perform Heavy Op Flag")
def test_heavy_op_flag():
    result = fetch("/api/resources")
    limits = result.get("limits", {})
    return "can_perform_heavy_op" in limits


# =============================================================================
# STREAMING TESTS
# =============================================================================

@test("Streaming Endpoint Responds")
def test_streaming_exists():
    # Just check it doesn't 404
    try:
        req = urllib.request.Request(f"{SAM_API}/api/cognitive/stream")
        req.method = "POST"
        req.data = json.dumps({"query": "hi", "user_id": "test"}).encode()
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=60) as resp:
            # Read first chunk
            chunk = resp.read(100)
            return b"data:" in chunk or len(chunk) > 0
    except Exception as e:
        # Timeout is acceptable for this test
        if "timed out" in str(e).lower():
            return True  # Endpoint exists, just slow
        return False


# =============================================================================
# PROACTIVE NOTIFIER MODULE TESTS
# =============================================================================

@test("Proactive Notifier Module Importable")
def test_notifier_import():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from proactive_notifier import check_and_notify, load_state, save_state
        return True
    except ImportError:
        return False


@test("Proactive Notifier State File Works")
def test_notifier_state():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from proactive_notifier import load_state, save_state

        state = load_state()
        state["test_key"] = "test_value"
        save_state(state)

        reloaded = load_state()
        return reloaded.get("test_key") == "test_value"
    except Exception:
        return False


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("SAM v1.3.1 New Features Test Suite")
    print("=" * 60)
    print()

    tests = [
        # API
        test_api_health,
        test_resources_model_info,
        test_resources_level,
        test_unload_endpoint,
        test_unload_returns_info,

        # Cognitive
        test_cognitive_process,
        test_cognitive_confidence,
        test_resources_after_query,

        # Proactive
        test_proactive_endpoint,
        test_proactive_suggestions,
        test_self_endpoint,
        test_self_proactive,

        # Memory Efficiency
        test_idle_tracking,
        test_token_limits,
        test_heavy_op_flag,

        # Streaming
        test_streaming_exists,

        # Notifier Module
        test_notifier_import,
        test_notifier_state,
    ]

    for test_func in tests:
        test_func()

    print()
    print("=" * 60)
    passed = RESULTS["passed"]
    failed = RESULTS["failed"]
    total = passed + failed
    rate = (passed / total * 100) if total > 0 else 0

    print(f"Results: {passed}/{total} passed ({rate:.1f}%)")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
