#!/usr/bin/env python3
"""
SAM Coding & Bridge Exhaustive Test Suite

Tests:
1. Routing decisions (local vs external)
2. Escalation detection (confidence, complexity, refusal)
3. Code generation quality
4. Bridge connectivity (Claude)
5. Various coding task types

Run:
    python test_coding_exhaustive.py
    python test_coding_exhaustive.py --quick    # Smoke test only
    python test_coding_exhaustive.py --live     # Include live API tests
"""

import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

# Add sam_brain to path
SAM_BRAIN = Path.home() / "ReverseLab/SAM/warp_tauri/sam_brain"
sys.path.insert(0, str(SAM_BRAIN))

# ============================================================================
# TEST INFRASTRUCTURE
# ============================================================================

@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Optional[str] = None

@dataclass
class TestSuite:
    results: List[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return len([r for r in self.results if r.passed])

    @property
    def failed(self) -> int:
        return len([r for r in self.results if not r.passed])

    def add(self, result: TestResult):
        self.results.append(result)
        status = "✓" if result.passed else "✗"
        print(f"  {status} {result.name} ({result.duration_ms:.0f}ms)")
        if result.error:
            print(f"    Error: {result.error}")

def run_test(name: str, category: str, test_fn: Callable) -> TestResult:
    start = time.time()
    try:
        result = test_fn()
        duration = (time.time() - start) * 1000
        if isinstance(result, tuple):
            passed, details = result
        else:
            passed = bool(result)
            details = str(result) if result else None
        return TestResult(name=name, category=category, passed=passed,
                         duration_ms=duration, details=details)
    except Exception as e:
        return TestResult(name=name, category=category, passed=False,
                         duration_ms=(time.time()-start)*1000, error=str(e))

# ============================================================================
# SMART ROUTER TESTS
# ============================================================================

def test_smart_router_import():
    """Test smart_router module loads correctly."""
    from smart_router import sanitize_content, estimate_complexity, Provider
    return True, "Imported successfully"

def test_sanitize_secrets():
    """Test that secrets are properly redacted."""
    from smart_router import sanitize_content

    test_cases = [
        ("api_key=sk-abc123def456", "[REDACTED_SECRET]" in sanitize_content("api_key=sk-abc123def456")),
        ("ghp_1234567890123456789012345678901234567", "[GITHUB_TOKEN_REDACTED]" in sanitize_content("ghp_1234567890123456789012345678901234567")),
        ("/Users/david/secrets.txt", "/Users/USER/" in sanitize_content("/Users/david/secrets.txt")),
    ]

    passed = all(case[1] for case in test_cases)
    details = f"{sum(c[1] for c in test_cases)}/{len(test_cases)} patterns sanitized"
    return passed, details

def test_complexity_estimation():
    """Test complexity estimation for routing decisions."""
    from smart_router import estimate_complexity

    simple_prompts = [
        "list files in current directory",
        "show git status",
        "read the README file",
    ]
    complex_prompts = [
        "implement a binary search tree with AVL balancing",
        "debug why the authentication is failing in production",
        "refactor the entire codebase to use dependency injection",
    ]

    # estimate_complexity returns (score, reason) tuple
    simple_scores = [estimate_complexity(p)[0] for p in simple_prompts]
    complex_scores = [estimate_complexity(p)[0] for p in complex_prompts]

    avg_simple = sum(simple_scores) / len(simple_scores)
    avg_complex = sum(complex_scores) / len(complex_scores)

    passed = avg_complex > avg_simple
    return passed, f"Simple avg: {avg_simple:.2f}, Complex avg: {avg_complex:.2f}"

# ============================================================================
# ESCALATION HANDLER TESTS
# ============================================================================

def test_escalation_import():
    """Test escalation_handler module loads correctly."""
    from escalation_handler import EscalationReason, SAMResponse
    return True

def test_uncertainty_detection():
    """Test detection of uncertain/low-confidence responses."""
    from escalation_handler import UNCERTAINTY_PATTERNS
    import re

    uncertain_responses = [
        "I'm not sure how to do that",
        "I don't know the answer",
        "That's beyond my capabilities",
        "You'd want to consult an expert",
    ]

    detected = 0
    for resp in uncertain_responses:
        for pattern in UNCERTAINTY_PATTERNS:
            if re.search(pattern, resp.lower()):
                detected += 1
                break

    passed = detected == len(uncertain_responses)
    return passed, f"Detected {detected}/{len(uncertain_responses)} uncertain patterns"

def test_refusal_detection():
    """Test detection of refusal patterns."""
    from escalation_handler import REFUSAL_PATTERNS
    import re

    refusal_responses = [
        "I can't assist with that request",
        "I'm unable to help with that",
        "Sorry, I cannot do that",
        "That would be inappropriate",
    ]

    detected = 0
    for resp in refusal_responses:
        for pattern in REFUSAL_PATTERNS:
            if re.search(pattern, resp.lower()):
                detected += 1
                break

    passed = detected >= 3
    return passed, f"Detected {detected}/{len(refusal_responses)} refusal patterns"

def test_confidence_detection():
    """Test detection of confident responses."""
    from escalation_handler import CONFIDENT_PATTERNS
    import re

    confident_responses = [
        "Here's how you can do it:\n```python\nprint('hello')\n```",
        "You can use the following approach: first, install the package",
        "def calculate_sum(a, b): return a + b",
    ]

    detected = 0
    for resp in confident_responses:
        for pattern in CONFIDENT_PATTERNS:
            if re.search(pattern, resp):
                detected += 1
                break

    passed = detected == len(confident_responses)
    return passed, f"Detected {detected}/{len(confident_responses)} confident patterns"

# ============================================================================
# CODING CAPABILITY TESTS
# ============================================================================

def test_code_task_classification():
    """Test that code-related tasks are properly classified."""
    from smart_router import COMPLEX_PATTERNS, LOCAL_PATTERNS
    import re

    code_tasks = [
        ("implement a REST API endpoint", True),
        ("fix the null pointer bug", True),
        ("run the tests", False),
        ("show git log", False),
        ("refactor to use async/await", True),
    ]

    correct = 0
    for task, expected_complex in code_tasks:
        is_complex = any(re.search(p, task.lower()) for p in COMPLEX_PATTERNS)
        is_local = any(re.search(p, task.lower()) for p in LOCAL_PATTERNS)

        if expected_complex and is_complex:
            correct += 1
        elif not expected_complex and is_local:
            correct += 1

    passed = correct >= 4
    return passed, f"Classified {correct}/{len(code_tasks)} correctly"

def test_ollama_availability():
    """Test that Ollama is running and responsive."""
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return True, f"Ollama running with {len(models)} models"
        return False, f"Ollama returned {resp.status_code}"
    except Exception as e:
        return False, f"Ollama not reachable: {e}"

def test_sam_model_available():
    """Test that SAM's trained model is available."""
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        model_names = [m["name"] for m in models]

        sam_models = [n for n in model_names if "sam" in n.lower()]
        if sam_models:
            return True, f"SAM models: {', '.join(sam_models)}"
        return False, f"No SAM models found. Available: {model_names[:5]}"
    except Exception as e:
        return False, str(e)

# ============================================================================
# BRIDGE CONNECTIVITY TESTS
# ============================================================================

def test_claude_bridge_import():
    """Test Claude bridge module exists."""
    bridge_path = SAM_BRAIN.parent / "claude_bridge.cjs"
    if bridge_path.exists():
        return True, f"Found at {bridge_path}"
    return False, "claude_bridge.cjs not found"

def test_ai_bridge_import():
    """Test AI bridge module exists."""
    bridge_path = SAM_BRAIN.parent / "ai_bridge.cjs"
    if bridge_path.exists():
        return True, f"Found at {bridge_path}"
    return False, "ai_bridge.cjs not found"

def test_mlx_inference_import():
    """Test MLX inference module loads."""
    try:
        from mlx_inference import load_model, generate_response
        return True, "MLX inference available"
    except ImportError as e:
        return False, f"MLX not available: {e}"

def test_claude_orchestrator_import():
    """Test Claude orchestrator module loads."""
    try:
        from claude_orchestrator import create_task, execute_task, TaskStatus
        return True, "Claude orchestrator available (task system)"
    except ImportError as e:
        return False, f"Not available: {e}"

# ============================================================================
# LIVE TESTS (require --live flag)
# ============================================================================

def test_ollama_simple_generation():
    """Test basic code generation via Ollama."""
    import requests

    prompt = "Write a Python function that adds two numbers. Just the function, no explanation."

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "sam-coder:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 100}
            },
            timeout=30
        )

        if resp.status_code == 200:
            output = resp.json().get("response", "")
            has_def = "def " in output
            has_return = "return" in output
            passed = has_def and has_return
            return passed, f"Generated {len(output)} chars, has def={has_def}, return={has_return}"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_code_generation_quality():
    """Test quality of generated code across different tasks."""
    import requests

    tasks = [
        ("Write a function to reverse a string", ["def", "return"]),
        ("Write a function to find max in a list", ["def", "return"]),
        ("Write a class for a simple counter", ["class", "def", "self"]),
    ]

    passed_count = 0
    for prompt, required in tasks:
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "sam-coder:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 150}
                },
                timeout=30
            )

            if resp.status_code == 200:
                output = resp.json().get("response", "")
                if all(r in output for r in required):
                    passed_count += 1
        except:
            pass

    passed = passed_count >= 2
    return passed, f"Passed {passed_count}/{len(tasks)} code generation tasks"

# ============================================================================
# MAIN
# ============================================================================

def run_all_tests(quick=False, live=False):
    suite = TestSuite()

    print("\n" + "="*60)
    print("SAM CODING & BRIDGE EXHAUSTIVE TEST")
    print("="*60)

    # Smart Router Tests
    print("\n[SMART ROUTER]")
    suite.add(run_test("Import smart_router", "router", test_smart_router_import))
    suite.add(run_test("Sanitize secrets", "router", test_sanitize_secrets))
    if not quick:
        suite.add(run_test("Complexity estimation", "router", test_complexity_estimation))

    # Escalation Tests
    print("\n[ESCALATION HANDLER]")
    suite.add(run_test("Import escalation_handler", "escalation", test_escalation_import))
    suite.add(run_test("Uncertainty detection", "escalation", test_uncertainty_detection))
    suite.add(run_test("Refusal detection", "escalation", test_refusal_detection))
    suite.add(run_test("Confidence detection", "escalation", test_confidence_detection))

    # Coding Capability Tests
    print("\n[CODING CAPABILITY]")
    suite.add(run_test("Code task classification", "coding", test_code_task_classification))
    suite.add(run_test("Ollama availability", "coding", test_ollama_availability))
    suite.add(run_test("SAM model available", "coding", test_sam_model_available))

    # Bridge Tests
    print("\n[BRIDGE CONNECTIVITY]")
    suite.add(run_test("Claude bridge exists", "bridge", test_claude_bridge_import))
    suite.add(run_test("AI bridge exists", "bridge", test_ai_bridge_import))
    suite.add(run_test("MLX inference import", "bridge", test_mlx_inference_import))
    suite.add(run_test("Claude orchestrator import", "bridge", test_claude_orchestrator_import))

    # Live Tests
    if live:
        print("\n[LIVE TESTS - API calls]")
        suite.add(run_test("Simple generation", "live", test_ollama_simple_generation))
        suite.add(run_test("Code generation quality", "live", test_code_generation_quality))

    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {suite.passed}/{len(suite.results)} passed, {suite.failed} failed")
    print("="*60)

    # Category breakdown
    categories = {}
    for r in suite.results:
        if r.category not in categories:
            categories[r.category] = {"passed": 0, "failed": 0}
        if r.passed:
            categories[r.category]["passed"] += 1
        else:
            categories[r.category]["failed"] += 1

    print("\nBy Category:")
    for cat, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        print(f"  {cat}: {stats['passed']}/{total}")

    # Failed tests detail
    failed = [r for r in suite.results if not r.passed]
    if failed:
        print("\nFailed Tests:")
        for r in failed:
            print(f"  ✗ {r.name}")
            if r.error:
                print(f"    {r.error}")

    return suite.failed == 0

# ============================================================================
# EXHAUSTIVE CODING TESTS (moved before main)
# ============================================================================

def test_multi_language_generation():
    """Test code generation in multiple languages."""
    import requests

    languages = [
        ("Python", "Write a Python function to check if a number is prime", "def"),
        ("JavaScript", "Write a JavaScript function to reverse an array", "function"),
        ("Rust", "Write a Rust function to calculate factorial", "fn"),
    ]

    passed_count = 0
    for lang, prompt, expected in languages:
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "sam-coder:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 200}
                },
                timeout=45
            )
            if resp.status_code == 200:
                output = resp.json().get("response", "")
                if expected in output:
                    passed_count += 1
        except:
            pass

    passed = passed_count >= 2  # At least 2/3
    return passed, f"Generated code in {passed_count}/{len(languages)} languages"

def test_debugging_capability():
    """Test SAM's ability to identify bugs."""
    import requests

    buggy_code = """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Bug: crashes on empty list
"""
    prompt = f"Find the bug in this code:\n{buggy_code}"

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "sam-coder:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 200}
            },
            timeout=30
        )
        if resp.status_code == 200:
            output = resp.json().get("response", "").lower()
            # Should mention empty list or division by zero
            found_bug = "empty" in output or "zero" in output or "division" in output
            return found_bug, f"Bug detection: {'found' if found_bug else 'missed'}"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_refactoring_suggestion():
    """Test SAM's refactoring suggestions."""
    import requests

    messy_code = """
def p(x):
    r = []
    for i in x:
        if i % 2 == 0:
            r.append(i * 2)
    return r
"""
    prompt = f"Refactor this code to be more readable:\n{messy_code}"

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "sam-coder:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 250}
            },
            timeout=30
        )
        if resp.status_code == 200:
            output = resp.json().get("response", "")
            # Should have better variable names or use list comprehension
            improved = "even" in output.lower() or "filter" in output.lower() or "[" in output
            return improved, f"Refactoring quality: {'improved' if improved else 'unchanged'}"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_escalation_threshold():
    """Test that complex tasks trigger escalation consideration."""
    from escalation_handler import CLAUDE_PREFERRED
    import re

    complex_tasks = [
        "architect a microservices system for e-commerce",
        "design a distributed caching pattern",
        "perform a security vulnerability assessment",
        "optimize the critical database performance",
    ]

    matched = 0
    for task in complex_tasks:
        for pattern in CLAUDE_PREFERRED:
            if re.search(pattern, task.lower()):
                matched += 1
                break

    passed = matched >= 3
    return passed, f"Escalation triggers: {matched}/{len(complex_tasks)} complex tasks detected"

def test_sam_personality_retention():
    """Test that SAM maintains personality in responses."""
    import requests

    prompt = "Hey SAM, what's up? Tell me a bit about yourself."

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "sam-trained:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 150}
            },
            timeout=30
        )
        if resp.status_code == 200:
            output = resp.json().get("response", "").lower()
            # SAM should be confident, maybe flirty
            has_personality = any(word in output for word in 
                ["i'm", "i am", "help", "code", "build", "hey"])
            return has_personality, f"Personality check: {'present' if has_personality else 'missing'}"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def run_exhaustive_tests():
    """Run all exhaustive tests."""
    suite = TestSuite()

    print("\n[EXHAUSTIVE CODING TESTS]")
    suite.add(run_test("Multi-language generation", "exhaustive", test_multi_language_generation))
    suite.add(run_test("Debugging capability", "exhaustive", test_debugging_capability))
    suite.add(run_test("Refactoring suggestion", "exhaustive", test_refactoring_suggestion))
    suite.add(run_test("Escalation threshold", "exhaustive", test_escalation_threshold))
    suite.add(run_test("SAM personality retention", "exhaustive", test_sam_personality_retention))

    return suite

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Quick smoke test")
    parser.add_argument("--live", action="store_true", help="Include live API tests")
    parser.add_argument("--exhaustive", action="store_true", help="Run exhaustive coding tests")
    args = parser.parse_args()

    success = run_all_tests(quick=args.quick, live=args.live)

    if args.exhaustive:
        print("\n" + "="*60)
        exhaustive_suite = run_exhaustive_tests()
        print(f"\nExhaustive: {exhaustive_suite.passed}/{len(exhaustive_suite.results)} passed")
        success = success and exhaustive_suite.failed == 0

    sys.exit(0 if success else 1)
