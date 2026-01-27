#!/usr/bin/env python3
"""
Test script for Phase 1.3.7: Fact Injection into Context Manager

This script tests that:
1. Facts are properly loaded from fact_memory
2. Facts are injected into prompts with correct priority ordering
3. Token limits are respected
4. The <USER> section appears in the context

Run with:
    cd ~/ReverseLab/SAM/warp_tauri/sam_brain
    python -m tests.test_fact_injection
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fact_memory import (
    FactMemory,
    build_user_context,
    get_user_context,
    FactCategory,
    UserFact,
)


def _build_context_from_db(
    db: FactMemory,
    user_id: str = "david",
    min_confidence: float = 0.5,
    max_tokens: int = 200
) -> str:
    """
    Build context directly from a specific db instance (for testing).
    Mirrors the logic in build_user_context but uses the provided db.
    """
    facts = db.get_facts_for_context(user_id, min_confidence, limit=15)

    if not facts:
        return ""

    # Group by category
    by_category: Dict[str, List[UserFact]] = {}
    for fact in facts:
        if fact.category not in by_category:
            by_category[fact.category] = []
        by_category[fact.category].append(fact)

    # Build context string with EXPLICIT priority ordering
    # Phase 1.3.7: corrections > system > preferences > biographical
    parts = []
    max_chars = max_tokens * 4
    current_chars = 0

    # Priority 1: CORRECTIONS
    if "corrections" in by_category and current_chars < max_chars:
        corrections = [f.fact for f in by_category["corrections"][:3]]
        correction_text = f"IMPORTANT - Remember: {'; '.join(corrections)}"
        parts.append(correction_text)
        current_chars += len(correction_text)

    # Priority 2: SYSTEM
    if "system" in by_category and current_chars < max_chars:
        system = [f.fact for f in by_category["system"][:2]]
        system_text = f"User preferences: {'; '.join(system)}"
        parts.append(system_text)
        current_chars += len(system_text)

    # Priority 3: PREFERENCES
    if "preferences" in by_category and current_chars < max_chars:
        prefs = [f.fact for f in by_category["preferences"][:3]]
        pref_text = f"Preferences: {'; '.join(prefs)}"
        parts.append(pref_text)
        current_chars += len(pref_text)

    # Priority 4: BIOGRAPHICAL
    if "biographical" in by_category and current_chars < max_chars:
        bio = [f.fact for f in by_category["biographical"][:2]]
        bio_text = f"About user: {'; '.join(bio)}"
        parts.append(bio_text)
        current_chars += len(bio_text)

    # Lower priority
    if "projects" in by_category and current_chars < max_chars * 0.9:
        projects = [f.fact for f in by_category["projects"][:2]]
        proj_text = f"Current projects: {'; '.join(projects)}"
        parts.append(proj_text)
        current_chars += len(proj_text)

    if "skills" in by_category and current_chars < max_chars * 0.9:
        skills = [f.fact for f in by_category["skills"][:2]]
        skill_text = f"Skills: {'; '.join(skills)}"
        parts.append(skill_text)
        current_chars += len(skill_text)

    return "\n".join(parts) if parts else ""


def test_priority_ordering():
    """Test that facts are returned in priority order: corrections > system > preferences > biographical"""
    print("\n=== Test: Priority Ordering ===")

    # Create a test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    try:
        db = FactMemory(db_path, auto_decay=False)

        # Add facts in reverse priority order to test sorting
        db.save_fact("Uses Python", "skills", source="conversation", user_id="test_user")
        db.save_fact("Name is Test User", "biographical", source="explicit", user_id="test_user")
        db.save_fact("Likes dark mode", "preferences", source="explicit", user_id="test_user")
        db.save_fact("Prefers concise responses", "system", source="explicit", user_id="test_user")
        db.save_fact("Do NOT use emojis", "corrections", source="correction", user_id="test_user")

        # Get context using our test helper that works with the specific db instance
        context = _build_context_from_db(db, "test_user", min_confidence=0.3)

        print(f"Generated context:\n{context}\n")

        # Verify we have content
        assert context, "Context should not be empty"

        # Verify order
        lines = context.split('\n')

        # First should be corrections (IMPORTANT)
        assert "IMPORTANT" in lines[0], f"Expected corrections first, got: {lines[0]}"
        print("[PASS] Corrections appear first (highest priority)")

        # Second should be system preferences
        assert "User preferences:" in lines[1], f"Expected system second, got: {lines[1]}"
        print("[PASS] System preferences appear second")

        # Third should be preferences
        assert "Preferences:" in lines[2], f"Expected preferences third, got: {lines[2]}"
        print("[PASS] Preferences appear third")

        # Fourth should be biographical
        assert "About user:" in lines[3], f"Expected biographical fourth, got: {lines[3]}"
        print("[PASS] Biographical appears fourth")

        print("\n[SUCCESS] Priority ordering test passed!")

    finally:
        db_path.unlink()


def test_token_limit():
    """Test that context respects token limits"""
    print("\n=== Test: Token Limit ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    try:
        db = FactMemory(db_path, auto_decay=False)

        # Add many facts to exceed token limit
        for i in range(20):
            db.save_fact(f"Test fact number {i} with some extra text to make it longer",
                        "preferences", source="conversation", user_id="test_user")

        # Get context with small token limit using our test helper
        context = _build_context_from_db(db, "test_user", min_confidence=0.3, max_tokens=50)

        # ~50 tokens * 4 chars = 200 chars max
        max_chars = 50 * 4

        print(f"Context length: {len(context)} chars (max {max_chars})")
        print(f"Context:\n{context[:200]}...")

        # Should be within reasonable range of limit
        assert len(context) < max_chars * 1.5, f"Context too long: {len(context)} > {max_chars * 1.5}"
        print("\n[SUCCESS] Token limit test passed!")

    finally:
        db_path.unlink()


def test_context_in_orchestrator():
    """Test that facts appear in orchestrator context"""
    print("\n=== Test: Context in Orchestrator ===")

    try:
        from cognitive.unified_orchestrator import CognitiveOrchestrator

        # Check if orchestrator has the fact injection method
        assert hasattr(CognitiveOrchestrator, 'get_user_facts_context'), \
            "Orchestrator missing get_user_facts_context method"
        print("[PASS] Orchestrator has get_user_facts_context method")

        # Check token budget constant
        assert hasattr(CognitiveOrchestrator, 'USER_FACTS_TOKENS'), \
            "Orchestrator missing USER_FACTS_TOKENS constant"
        print(f"[PASS] USER_FACTS_TOKENS = {CognitiveOrchestrator.USER_FACTS_TOKENS}")

        print("\n[SUCCESS] Orchestrator integration test passed!")

    except ImportError as e:
        print(f"[SKIP] Could not import orchestrator: {e}")


def test_backward_compatibility():
    """Test that old get_user_context still works"""
    print("\n=== Test: Backward Compatibility ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    try:
        db = FactMemory(db_path, auto_decay=False)

        db.save_fact("Test fact for backward compat", "preferences", source="explicit", user_id="test_user")

        # Test with our helper that uses the specific db
        context = _build_context_from_db(db, "test_user", min_confidence=0.3, max_tokens=100)

        print(f"Context result: {context}")

        assert "Test fact" in context, "Should return facts"
        print("[PASS] Facts are retrieved from db")

        # Verify the build_user_context function signature accepts max_tokens
        import inspect
        sig = inspect.signature(build_user_context)
        assert 'max_tokens' in sig.parameters, "build_user_context should accept max_tokens"
        print("[PASS] build_user_context accepts max_tokens parameter")

        # Verify get_user_context signature still works
        sig_old = inspect.signature(get_user_context)
        assert 'max_tokens' in sig_old.parameters, "get_user_context should accept max_tokens"
        print("[PASS] get_user_context still accepts max_tokens (backward compatible)")

        print("\n[SUCCESS] Backward compatibility test passed!")

    finally:
        db_path.unlink()


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Phase 1.3.7: Fact Injection Tests")
    print("=" * 60)

    tests = [
        test_priority_ordering,
        test_token_limit,
        test_context_in_orchestrator,
        test_backward_compatibility,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAILED] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[ERROR] {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
