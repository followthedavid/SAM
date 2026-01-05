#!/usr/bin/env python3
"""Quick routing test with restrictive patterns"""

# More restrictive creative patterns
CREATIVE_PATTERNS = [
    "roleplay", "role play", "role-play",
    "pretend to be", "pretend you're", "pretend you are",
    "imagine you're", "imagine you are", "imagine we",
    "be my", "act as", "act like", "play as",
    "you are a", "you're a",
    "write me a story", "create a story", "tell me a story",
    "write a poem", "creative writing",
    "let's chat", "just chat", "casual chat",
]

PRIVACY_KEYWORDS = ["private", "privately", "local"]

def is_creative(text):
    lower = text.lower()
    return any(p in lower for p in CREATIVE_PATTERNS)

def wants_privacy(text):
    lower = text.lower()
    return any(kw in lower for kw in PRIVACY_KEYWORDS)

# Test cases
test_cases = [
    # Should NOT trigger creative mode
    ("how can we get all my projects improving?", False),
    ("can we fix this bug?", False),
    ("help me understand this code", False),
    ("i want to improve performance", False),
    ("would you review this PR?", False),
    
    # SHOULD trigger creative mode
    ("let's roleplay", True),
    ("pretend to be a pirate", True),
    ("imagine you're a wizard", True),
    ("be my coding assistant", True),
    ("act as a senior developer", True),
    ("write me a story about coding", True),
    ("let's chat about life", True),
]

print("=== RESTRICTIVE ROUTING TEST ===\n")

passed = 0
failed = 0

for input_text, expected_creative in test_cases:
    actual_creative = is_creative(input_text)

    if actual_creative == expected_creative:
        status = "✓"
        passed += 1
    else:
        status = "✗"
        failed += 1

    mode = "Creative" if actual_creative else "Normal"
    expected_mode = "Creative" if expected_creative else "Normal"
    
    if actual_creative == expected_creative:
        print(f"✓ '{input_text[:40]}...' → {mode}")
    else:
        print(f"✗ '{input_text[:40]}...'")
        print(f"  Expected: {expected_mode}, Got: {mode}")

print(f"\n=== RESULTS ===")
print(f"Passed: {passed}/{len(test_cases)}")
print(f"Failed: {failed}/{len(test_cases)}")
