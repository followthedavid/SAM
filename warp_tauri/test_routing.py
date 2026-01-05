#!/usr/bin/env python3
"""Quick routing test without building the full app"""

import re

# Routing patterns from hybrid_router.rs
CONVERSATIONAL_PATTERNS = [
    "hi", "hello", "hey", "howdy", "sup", "yo",
    "good morning", "good afternoon", "good evening",
    "what's up", "how are you", "how's it going",
    "who are you", "what are you", "what can you do",
    "what is sam", "tell me about yourself",
    "thanks", "thank you", "thx", "ty",
    "got it", "ok", "okay", "cool", "nice",
    "bye", "goodbye", "see you", "later", "cya",
    "daily brief", "what needs attention", "show my progress",
    "status update", "what's pending", "summary", "overview",
    "what did i accomplish", "what have i done", "my projects",
    "priorities", "what should i focus",
]

CREATIVE_PATTERNS = [
    "roleplay", "role play", "pretend", "imagine", "story",
    "chat", "talk", "conversation", "discuss", "tell me",
    "be my", "act as", "you are", "pretend you're",
    "write me", "create a story", "poem", "script",
    "let's", "can we", "would you", "could you",
    "help me", "i want to", "i need",
]

DETERMINISTIC_PATTERNS = [
    "list files", "show files", "git status", "git log", "git diff",
    "git branch", "git commit", "git push", "git pull",
    "run build", "run test", "npm install", "cargo build", "cargo test",
    "docker ps", "docker build", "kill process", "find process",
]

PRIVACY_KEYWORDS = ["private", "privately", "local"]

def classify_input(text):
    """Classify input using the same logic as hybrid_router.rs"""
    lower = text.lower()
    word_count = len(lower.split())

    # Check for privacy mode
    wants_privacy = any(kw in lower for kw in PRIVACY_KEYWORDS)

    # Check if creative/conversational
    is_creative = any(p in lower for p in CREATIVE_PATTERNS)

    # Check conversational
    is_conversational = any(p in lower for p in CONVERSATIONAL_PATTERNS)
    is_status_query = any(w in lower for w in ["brief", "status", "progress", "attention", "summary"])
    length_ok = word_count <= 15 if is_status_query else word_count <= 8

    # Check deterministic
    is_deterministic = any(p in lower for p in DETERMINISTIC_PATTERNS)

    # Routing logic
    if is_deterministic:
        return "Deterministic", "No AI needed"

    if is_conversational and length_ok:
        return "Conversational", "Simple chat"

    # Privacy + Creative = Conversational (local)
    if wants_privacy and is_creative:
        return "Conversational", "Private creative mode"

    if wants_privacy:
        return "MicroModel", "Private mode - local only"

    # Default
    return "MicroModel", "General AI task"

# Test cases
test_cases = [
    # Conversational
    ("hello", "Conversational"),
    ("hi there", "Conversational"),
    ("daily brief", "Conversational"),
    ("what needs attention", "Conversational"),
    ("thanks", "Conversational"),

    # Private/Roleplay -> Conversational
    ("let's roleplay privately", "Conversational"),
    ("can we chat privately", "Conversational"),
    ("pretend you're my assistant", "Conversational"),
    ("imagine we're in a story", "Conversational"),

    # Private non-creative -> MicroModel
    ("keep this local please", "MicroModel"),

    # Deterministic
    ("git status", "Deterministic"),
    ("list files", "Deterministic"),
    ("cargo build", "Deterministic"),
    ("npm install", "Deterministic"),
]

print("=== SAM ROUTING TEST ===\n")

passed = 0
failed = 0

for input_text, expected_path in test_cases:
    actual_path, reason = classify_input(input_text)

    if actual_path == expected_path:
        print(f"✓ '{input_text}' → {actual_path}")
        passed += 1
    else:
        print(f"✗ '{input_text}'")
        print(f"  Expected: {expected_path}")
        print(f"  Got: {actual_path} ({reason})")
        failed += 1

print(f"\n=== RESULTS ===")
print(f"Passed: {passed}/{len(test_cases)}")
print(f"Failed: {failed}/{len(test_cases)}")

if failed == 0:
    print("✓ ALL TESTS PASSED")
else:
    print("✗ SOME TESTS FAILED")
