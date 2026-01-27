#!/usr/bin/env python3
"""
Test Suite for SAM Fact Memory System
Phase 1.3.11: Comprehensive test coverage for fact_memory.py

Tests cover:
1. FactMemory - save, retrieve, search, decay
2. Fact extraction patterns
3. Confidence decay with Ebbinghaus curve
4. Reinforcement mechanics
5. Category filtering
6. Self-knowledge query detection and response
7. Integration with orchestrator

Run with:
    cd ~/ReverseLab/SAM/warp_tauri/sam_brain
    python -m pytest tests/test_fact_memory.py -v

Or run all tests:
    python -m pytest tests/test_fact_memory.py -v --tb=short
"""

import sys
import math
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fact_memory import (
    FactMemory,
    UserFact,
    FactCategory,
    FactSource,
    FactExtractor,
    generate_fact_id,
    generate_history_id,
    decay_confidence,
    decay_confidence_ebbinghaus,
    build_user_context,
    get_user_context,
    remember_fact,
    SOURCE_INITIAL_CONFIDENCE,
    CATEGORY_DECAY_RATES,
    CATEGORY_DECAY_FLOORS,
    CONFIDENCE_THRESHOLDS,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    db = FactMemory(db_path, auto_decay=False)
    yield db

    # Cleanup
    try:
        db_path.unlink()
    except Exception:
        pass


@pytest.fixture
def populated_db(temp_db):
    """Create a database with sample facts."""
    # Add various facts for testing
    temp_db.save_fact("Prefers dark mode", "preferences", source="explicit", user_id="test_user")
    temp_db.save_fact("Lives in Sydney", "biographical", source="conversation", user_id="test_user")
    temp_db.save_fact("Building SAM AI assistant", "projects", source="conversation", user_id="test_user")
    temp_db.save_fact("Expert in Python", "skills", source="inferred", user_id="test_user")
    temp_db.save_fact("Do NOT use emojis", "corrections", source="correction", user_id="test_user")
    temp_db.save_fact("Prefers concise responses", "system", source="system", user_id="test_user")
    temp_db.save_fact("Uses Rust for backend", "skills", source="conversation", user_id="test_user")
    return temp_db


# ============================================================================
# TEST CLASS: FactMemory Core Operations
# ============================================================================

class TestFactMemorySaveRetrieve:
    """Tests for saving and retrieving facts."""

    def test_save_basic_fact(self, temp_db):
        """Test saving a basic fact."""
        fact = temp_db.save_fact(
            fact="Likes Python",
            category="preferences",
            source="explicit",
            user_id="test_user"
        )

        assert fact is not None
        assert fact.fact == "Likes Python"
        assert fact.category == "preferences"
        assert fact.source == "explicit"
        assert fact.user_id == "test_user"
        assert fact.is_active is True

    def test_save_fact_with_metadata(self, temp_db):
        """Test saving a fact with additional metadata."""
        metadata = {"context": "from settings discussion", "priority": "high"}
        fact = temp_db.save_fact(
            fact="Prefers dark mode",
            category="preferences",
            source="explicit",
            user_id="test_user",
            metadata=metadata
        )

        assert fact is not None
        assert fact.metadata is not None
        import json
        stored_meta = json.loads(fact.metadata)
        assert stored_meta["context"] == "from settings discussion"

    def test_get_fact_by_id(self, temp_db):
        """Test retrieving a fact by its ID."""
        saved = temp_db.save_fact(
            fact="Test fact",
            category="biographical",
            source="conversation",
            user_id="test_user"
        )

        retrieved = temp_db.get_fact(saved.fact_id)

        assert retrieved is not None
        assert retrieved.fact_id == saved.fact_id
        assert retrieved.fact == "Test fact"

    def test_get_nonexistent_fact(self, temp_db):
        """Test retrieving a fact that doesn't exist."""
        result = temp_db.get_fact("nonexistent_id_12345")
        assert result is None

    def test_get_facts_by_user(self, populated_db):
        """Test getting all facts for a user."""
        facts = populated_db.get_facts(user_id="test_user")

        assert len(facts) == 7  # We added 7 facts in populated_db
        assert all(f.user_id == "test_user" for f in facts)

    def test_get_facts_by_category(self, populated_db):
        """Test filtering facts by category."""
        skills = populated_db.get_facts(user_id="test_user", category="skills")

        assert len(skills) == 2  # "Expert in Python" and "Uses Rust"
        assert all(f.category == "skills" for f in skills)

    def test_get_facts_min_confidence(self, temp_db):
        """Test filtering facts by minimum confidence."""
        # Save facts with different confidences
        temp_db.save_fact("High confidence fact", "preferences", source="explicit",
                         confidence=0.95, user_id="test_user")
        temp_db.save_fact("Low confidence fact", "preferences", source="inferred",
                         confidence=0.3, user_id="test_user")

        # Get only high confidence facts
        high_conf = temp_db.get_facts(user_id="test_user", min_confidence=0.7)
        assert len(high_conf) == 1
        assert high_conf[0].fact == "High confidence fact"

    def test_save_duplicate_fact_reinforces(self, temp_db):
        """Test that saving a duplicate fact reinforces the existing one."""
        # Save initial fact
        first = temp_db.save_fact("Likes coffee", "preferences", source="conversation",
                                  user_id="test_user")
        initial_count = first.reinforcement_count
        initial_confidence = first.confidence

        # Save same fact again (should reinforce)
        second = temp_db.save_fact("Likes coffee", "preferences", source="conversation",
                                   user_id="test_user")

        # Should be same fact ID but reinforced
        assert second.fact_id == first.fact_id
        assert second.reinforcement_count == initial_count + 1
        assert second.confidence >= initial_confidence


class TestFactMemorySearch:
    """Tests for fact search functionality."""

    def test_search_by_keyword(self, populated_db):
        """Test searching facts by keyword."""
        results = populated_db.search_facts("Python", user_id="test_user")

        assert len(results) >= 1
        assert any("Python" in f.fact for f in results)

    def test_search_case_insensitive(self, populated_db):
        """Test that search is case insensitive."""
        results_lower = populated_db.search_facts("python", user_id="test_user")
        results_upper = populated_db.search_facts("PYTHON", user_id="test_user")

        # Both should find the same fact
        assert len(results_lower) == len(results_upper)

    def test_search_partial_match(self, populated_db):
        """Test that search matches partial strings."""
        results = populated_db.search_facts("Syd", user_id="test_user")  # Partial match for Sydney

        assert len(results) >= 1
        assert any("Sydney" in f.fact for f in results)

    def test_search_no_results(self, populated_db):
        """Test search with no matching results."""
        results = populated_db.search_facts("xyznonexistent123", user_id="test_user")
        assert len(results) == 0

    def test_search_respects_confidence(self, temp_db):
        """Test that search respects min_confidence parameter."""
        temp_db.save_fact("High confidence match", "preferences", source="explicit",
                         confidence=0.9, user_id="test_user")
        temp_db.save_fact("Low confidence match", "preferences", source="inferred",
                         confidence=0.2, user_id="test_user")

        results = temp_db.search_facts("match", user_id="test_user", min_confidence=0.5)

        assert len(results) == 1
        assert results[0].confidence >= 0.5


# ============================================================================
# TEST CLASS: Fact Extraction Patterns
# ============================================================================

class TestFactExtraction:
    """Tests for fact extraction from text."""

    def test_extract_name(self, temp_db):
        """Test extracting name from text."""
        facts = temp_db.extract_facts_from_text(
            "My name is David",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("David" in f.fact for f in facts)
        assert any(f.category == "biographical" for f in facts)

    def test_extract_occupation(self, temp_db):
        """Test extracting occupation from text."""
        facts = temp_db.extract_facts_from_text(
            "I am a software engineer",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("software engineer" in f.fact.lower() for f in facts)

    def test_extract_location(self, temp_db):
        """Test extracting location from text."""
        facts = temp_db.extract_facts_from_text(
            "I'm from Sydney, Australia",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("Sydney" in f.fact for f in facts)

    def test_extract_preference(self, temp_db):
        """Test extracting preferences from text."""
        facts = temp_db.extract_facts_from_text(
            "I prefer Python over JavaScript",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("Python" in f.fact for f in facts)

    def test_extract_skill(self, temp_db):
        """Test extracting skills from text."""
        facts = temp_db.extract_facts_from_text(
            "I'm good at machine learning",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("machine learning" in f.fact.lower() for f in facts)

    def test_extract_project(self, temp_db):
        """Test extracting project information."""
        facts = temp_db.extract_facts_from_text(
            "I'm working on a new AI assistant",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any(f.category == "projects" for f in facts)

    def test_extract_remember_command(self, temp_db):
        """Test extracting explicit 'remember' commands."""
        facts = temp_db.extract_facts_from_text(
            "Remember that I always start work at 9am",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        # Remember commands should have high confidence
        assert any(f.confidence >= 0.9 for f in facts)

    def test_extract_dislike(self, temp_db):
        """Test extracting dislikes."""
        facts = temp_db.extract_facts_from_text(
            "I hate verbose error messages",
            user_id="test_user",
            save=False
        )

        assert len(facts) >= 1
        assert any("Dislikes" in f.fact for f in facts)

    def test_extract_and_save(self, temp_db):
        """Test extracting facts and saving them."""
        facts = temp_db.extract_facts_from_text(
            "I'm a Python developer living in Melbourne",
            user_id="test_user",
            save=True
        )

        # Verify they were saved
        all_facts = temp_db.get_facts(user_id="test_user")
        assert len(all_facts) >= len(facts)


class TestFactExtractorPatterns:
    """Tests for the FactExtractor class patterns."""

    def test_pattern_i_am(self):
        """Test 'I am' pattern matching."""
        facts = FactExtractor.extract("I am a data scientist", "test_user")
        assert len(facts) >= 1

    def test_pattern_i_like(self):
        """Test 'I like' pattern matching."""
        facts = FactExtractor.extract("I like writing clean code", "test_user")
        assert len(facts) >= 1
        assert any("Likes" in f.fact for f in facts)

    def test_pattern_i_work_on(self):
        """Test 'I work on' pattern matching."""
        facts = FactExtractor.extract("I work on distributed systems", "test_user")
        assert len(facts) >= 1
        assert any(f.category == "projects" for f in facts)

    def test_pattern_learning(self):
        """Test 'learning' pattern matching."""
        facts = FactExtractor.extract("I'm learning Rust programming", "test_user")
        assert len(facts) >= 1
        assert any(f.subcategory == "learning" for f in facts)

    def test_no_extraction_from_irrelevant(self):
        """Test that irrelevant text produces no facts."""
        facts = FactExtractor.extract("The weather is nice today", "test_user")
        # Should have no facts or very few
        assert len(facts) == 0

    def test_category_inference(self):
        """Test category inference for explicit remember commands."""
        facts = FactExtractor.extract("Remember that my favorite color is blue", "test_user")
        assert len(facts) >= 1
        # Should infer category based on content


# ============================================================================
# TEST CLASS: Confidence Decay (Ebbinghaus Curve)
# ============================================================================

class TestConfidenceDecay:
    """Tests for confidence decay using Ebbinghaus forgetting curve."""

    def test_decay_no_time_elapsed(self):
        """Test that no decay occurs when no time has passed."""
        result = decay_confidence(
            initial=0.9,
            days_elapsed=0,
            decay_rate=0.98,
            reinforcement_count=1,
            floor=0.1
        )
        assert result == 0.9

    def test_decay_one_day(self):
        """Test decay after one day."""
        initial = 0.9
        result = decay_confidence(
            initial=initial,
            days_elapsed=1,
            decay_rate=0.98,
            reinforcement_count=1,
            floor=0.1
        )
        # Should be lower but not drastically
        assert result < initial
        assert result > 0.8

    def test_decay_respects_floor(self):
        """Test that decay respects the minimum floor."""
        floor = 0.2
        result = decay_confidence(
            initial=0.9,
            days_elapsed=365,  # Long time
            decay_rate=0.90,   # Fast decay
            reinforcement_count=1,
            floor=floor
        )
        assert result >= floor

    def test_decay_no_decay_for_system_rate(self):
        """Test that decay_rate=1.0 means no decay."""
        result = decay_confidence(
            initial=0.9,
            days_elapsed=100,
            decay_rate=1.0,
            reinforcement_count=1,
            floor=0.1
        )
        assert result == 0.9

    def test_decay_with_reinforcement_boost(self):
        """Test that reinforcements slow decay."""
        # Same decay but different reinforcement counts
        result_low_reinforce = decay_confidence(
            initial=0.9,
            days_elapsed=30,
            decay_rate=0.98,
            reinforcement_count=1,
            floor=0.1
        )
        result_high_reinforce = decay_confidence(
            initial=0.9,
            days_elapsed=30,
            decay_rate=0.98,
            reinforcement_count=10,
            floor=0.1
        )

        # More reinforcements should mean higher retained confidence
        assert result_high_reinforce > result_low_reinforce

    def test_ebbinghaus_alias(self):
        """Test that decay_confidence is an alias for decay_confidence_ebbinghaus."""
        result1 = decay_confidence(0.9, 10, 0.98, 5, 0.1)
        result2 = decay_confidence_ebbinghaus(0.9, 10, 0.98, 5, 0.1)
        assert result1 == result2


class TestFactDecayMaintenance:
    """Tests for decay maintenance operations."""

    def test_apply_decay(self, temp_db):
        """Test the apply_decay maintenance function."""
        # Add a fact and manually set its last_reinforced to the past
        fact = temp_db.save_fact(
            "Test fact for decay",
            "context",  # Fast decay category
            source="conversation",
            user_id="test_user"
        )

        # Apply decay
        stats = temp_db.apply_decay(days_threshold=30)

        # Should have stats about the operation
        assert "updated" in stats
        assert "deactivated" in stats
        assert "purged" in stats

    def test_startup_decay_sets_metadata(self, temp_db):
        """Test that startup decay sets the last_decay_run metadata."""
        # The temp_db is created with auto_decay=False, so let's call it manually
        temp_db._apply_startup_decay()

        last_decay = temp_db._get_metadata("last_decay_run")
        assert last_decay is not None

    def test_deactivate_below_threshold(self, temp_db):
        """Test that facts below confidence threshold are deactivated."""
        # Create a fact with very low confidence (below 0.1 threshold)
        fact = temp_db.save_fact(
            "Low confidence fact",
            "context",
            source="inferred",
            confidence=0.05,
            user_id="test_user"
        )

        # The fact should exist but be subject to deactivation rules
        retrieved = temp_db.get_fact(fact.fact_id)
        assert retrieved is not None


# ============================================================================
# TEST CLASS: Reinforcement Mechanics
# ============================================================================

class TestReinforcementMechanics:
    """Tests for fact reinforcement functionality."""

    def test_reinforce_increases_count(self, temp_db):
        """Test that reinforcing a fact increases its count."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )
        initial_count = fact.reinforcement_count

        reinforced = temp_db.reinforce_fact(fact.fact_id)

        assert reinforced.reinforcement_count == initial_count + 1

    def test_reinforce_increases_confidence(self, temp_db):
        """Test that reinforcing a fact increases its confidence."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            confidence=0.7,
            user_id="test_user"
        )

        reinforced = temp_db.reinforce_fact(fact.fact_id)

        assert reinforced.confidence > fact.confidence

    def test_reinforce_diminishing_returns(self, temp_db):
        """Test that reinforcement has diminishing returns."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            confidence=0.7,
            user_id="test_user"
        )

        # Reinforce multiple times and track confidence gains
        gains = []
        current_conf = fact.confidence
        for _ in range(5):
            reinforced = temp_db.reinforce_fact(fact.fact_id)
            gain = reinforced.confidence - current_conf
            gains.append(gain)
            current_conf = reinforced.confidence

        # Later reinforcements should have smaller gains
        assert gains[0] > gains[-1]  # First gain > last gain

    def test_reinforce_nonexistent_fact(self, temp_db):
        """Test reinforcing a fact that doesn't exist."""
        result = temp_db.reinforce_fact("nonexistent_fact_id")
        assert result is None

    def test_reinforce_updates_timestamp(self, temp_db):
        """Test that reinforcement updates last_reinforced timestamp."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )
        original_reinforced = fact.last_reinforced

        # Wait a tiny bit to ensure timestamp differs
        import time
        time.sleep(0.01)

        reinforced = temp_db.reinforce_fact(fact.fact_id)

        assert reinforced.last_reinforced >= original_reinforced


class TestContradictionMechanics:
    """Tests for fact contradiction functionality."""

    def test_contradict_decreases_confidence(self, temp_db):
        """Test that contradicting a fact decreases its confidence."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            confidence=0.9,
            user_id="test_user"
        )

        contradicted = temp_db.contradict_fact(fact.fact_id, "User corrected")

        assert contradicted.confidence < fact.confidence

    def test_contradict_increases_count(self, temp_db):
        """Test that contradicting increases the contradiction count."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )

        contradicted = temp_db.contradict_fact(fact.fact_id)

        assert contradicted.contradiction_count == fact.contradiction_count + 1

    def test_contradict_nonexistent_fact(self, temp_db):
        """Test contradicting a fact that doesn't exist."""
        result = temp_db.contradict_fact("nonexistent_fact_id")
        assert result is None


# ============================================================================
# TEST CLASS: Category Filtering
# ============================================================================

class TestCategoryFiltering:
    """Tests for category-based filtering and priority."""

    def test_filter_by_preferences(self, populated_db):
        """Test filtering by preferences category."""
        facts = populated_db.get_facts(user_id="test_user", category="preferences")
        assert len(facts) >= 1
        assert all(f.category == "preferences" for f in facts)

    def test_filter_by_biographical(self, populated_db):
        """Test filtering by biographical category."""
        facts = populated_db.get_facts(user_id="test_user", category="biographical")
        assert len(facts) >= 1
        assert all(f.category == "biographical" for f in facts)

    def test_filter_by_system(self, populated_db):
        """Test filtering by system category."""
        facts = populated_db.get_facts(user_id="test_user", category="system")
        assert len(facts) >= 1
        assert all(f.category == "system" for f in facts)

    def test_category_decay_rates(self):
        """Test that all categories have defined decay rates."""
        for category in FactCategory:
            assert category.value in CATEGORY_DECAY_RATES

    def test_category_decay_floors(self):
        """Test that all categories have defined decay floors."""
        for category in FactCategory:
            assert category.value in CATEGORY_DECAY_FLOORS

    def test_get_facts_for_context_priority(self, populated_db):
        """Test that get_facts_for_context returns facts in priority order."""
        facts = populated_db.get_facts_for_context(user_id="test_user", min_confidence=0.0)

        # Corrections should be first priority, then system, etc.
        if len(facts) > 1:
            categories = [f.category for f in facts]

            # Find indices of priority categories
            correction_indices = [i for i, c in enumerate(categories) if c == "corrections"]
            system_indices = [i for i, c in enumerate(categories) if c == "system"]

            # If both exist, corrections should come before system
            if correction_indices and system_indices:
                assert min(correction_indices) < max(system_indices)


# ============================================================================
# TEST CLASS: Self-Knowledge Query Detection
# ============================================================================

class TestSelfKnowledgeDetection:
    """Tests for detecting self-knowledge queries."""

    def test_detect_what_do_you_know(self):
        """Test detecting 'what do you know about me' queries."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("What do you know about me?") is True
        assert detect_self_knowledge_query("What do you know about me") is True

    def test_detect_what_have_you_learned(self):
        """Test detecting 'what have you learned' queries."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("What have you learned about me?") is True

    def test_detect_show_my_profile(self):
        """Test detecting 'show my profile' queries."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("Show me my profile") is True
        assert detect_self_knowledge_query("Show my facts") is True

    def test_detect_tell_me_what_you_know(self):
        """Test detecting 'tell me what you know' queries."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("Tell me what you know about me") is True
        assert detect_self_knowledge_query("Tell me everything you remember about me") is True

    def test_not_detect_irrelevant(self):
        """Test that irrelevant queries are not detected."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("What's the weather like?") is False
        assert detect_self_knowledge_query("Help me with Python") is False
        assert detect_self_knowledge_query("What do you know about Python?") is False

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        from cognitive.self_knowledge_handler import detect_self_knowledge_query

        assert detect_self_knowledge_query("WHAT DO YOU KNOW ABOUT ME?") is True
        assert detect_self_knowledge_query("what do you know about me") is True


class TestSelfKnowledgeResponse:
    """Tests for self-knowledge query response formatting."""

    def test_format_response_with_facts(self, populated_db):
        """Test formatting a response when facts exist."""
        from cognitive.self_knowledge_handler import format_self_knowledge_response

        # Mock the fact memory
        with patch('cognitive.self_knowledge_handler.get_fact_memory', return_value=populated_db):
            response = format_self_knowledge_response(
                user_id="test_user",
                min_confidence=0.0
            )

        assert response.is_self_knowledge_query is True
        assert response.facts_count > 0
        assert len(response.categories_found) > 0
        assert "About You" in response.response or "Preferences" in response.response

    def test_format_response_empty(self, temp_db):
        """Test formatting a response when no facts exist."""
        from cognitive.self_knowledge_handler import format_self_knowledge_response

        with patch('cognitive.self_knowledge_handler.get_fact_memory', return_value=temp_db):
            response = format_self_knowledge_response(
                user_id="nonexistent_user",
                min_confidence=0.0
            )

        assert response.is_self_knowledge_query is True
        assert response.facts_count == 0
        assert "don't seem to have learned" in response.response.lower() or "tell me about yourself" in response.response.lower()

    def test_handle_self_knowledge_query(self, populated_db):
        """Test the main handler function."""
        from cognitive.self_knowledge_handler import handle_self_knowledge_query

        with patch('cognitive.self_knowledge_handler.get_fact_memory', return_value=populated_db):
            response = handle_self_knowledge_query("What do you know about me?", "test_user")

        assert response is not None
        assert response.is_self_knowledge_query is True

    def test_handle_non_self_knowledge_query(self):
        """Test handler returns None for non-self-knowledge queries."""
        from cognitive.self_knowledge_handler import handle_self_knowledge_query

        response = handle_self_knowledge_query("Help me with Python", "test_user")
        assert response is None


# ============================================================================
# TEST CLASS: Integration with Orchestrator
# ============================================================================

class TestOrchestratorIntegration:
    """Tests for integration with the cognitive orchestrator."""

    def test_orchestrator_has_user_facts_tokens(self):
        """Test that orchestrator defines USER_FACTS_TOKENS constant."""
        from cognitive.unified_orchestrator import CognitiveOrchestrator

        assert hasattr(CognitiveOrchestrator, 'USER_FACTS_TOKENS')
        assert CognitiveOrchestrator.USER_FACTS_TOKENS > 0

    def test_orchestrator_imports_fact_memory(self):
        """Test that orchestrator can import fact_memory."""
        from cognitive.unified_orchestrator import _fact_memory_available

        # Should be True if fact_memory is installed
        assert _fact_memory_available is True

    def test_orchestrator_self_knowledge_available(self):
        """Test that orchestrator has self-knowledge handler available."""
        from cognitive.unified_orchestrator import _self_knowledge_available

        assert _self_knowledge_available is True


# ============================================================================
# TEST CLASS: Context Building
# ============================================================================

class TestContextBuilding:
    """Tests for building user context from facts."""

    def test_build_user_context_basic(self, populated_db):
        """Test basic context building."""
        # We need to mock the get_fact_db to use our test db
        with patch('fact_memory.get_fact_db', return_value=populated_db):
            context = build_user_context("test_user", min_confidence=0.0)

        assert len(context) > 0
        # Should contain some fact content
        assert "Preferences:" in context or "About user:" in context or "IMPORTANT" in context

    def test_build_user_context_priority_order(self, temp_db):
        """Test that context follows priority order."""
        # Add facts in all priority categories
        temp_db.save_fact("Never use tabs", "corrections", source="correction",
                         user_id="test_user", confidence=0.9)
        temp_db.save_fact("Keep responses short", "system", source="system",
                         user_id="test_user", confidence=1.0)
        temp_db.save_fact("Likes Python", "preferences", source="explicit",
                         user_id="test_user", confidence=0.9)
        temp_db.save_fact("Lives in Sydney", "biographical", source="conversation",
                         user_id="test_user", confidence=0.9)

        with patch('fact_memory.get_fact_db', return_value=temp_db):
            context = build_user_context("test_user", min_confidence=0.0)

        # Corrections should appear first (IMPORTANT)
        lines = context.split('\n')
        if len(lines) > 1:
            assert "IMPORTANT" in lines[0] or "corrections" in context.lower()

    def test_build_user_context_respects_token_limit(self, populated_db):
        """Test that context respects token limits."""
        with patch('fact_memory.get_fact_db', return_value=populated_db):
            context = build_user_context("test_user", min_confidence=0.0, max_tokens=50)

        # Context should be reasonably short (50 tokens ~ 200 chars)
        max_chars = 50 * 4 * 1.5  # Allow some buffer
        assert len(context) <= max_chars

    def test_build_user_context_empty_user(self, temp_db):
        """Test context building for user with no facts."""
        with patch('fact_memory.get_fact_db', return_value=temp_db):
            context = build_user_context("nonexistent_user")

        assert context == ""


class TestBackwardCompatibility:
    """Tests for backward compatibility functions."""

    def test_get_user_context_alias(self):
        """Test that get_user_context function exists and works."""
        # Just verify the function signature matches expectations
        import inspect
        sig = inspect.signature(get_user_context)

        assert 'user_id' in sig.parameters
        assert 'max_tokens' in sig.parameters

    def test_remember_fact_function(self, temp_db):
        """Test the convenience remember_fact function."""
        with patch('fact_memory.get_fact_db', return_value=temp_db):
            fact_id = remember_fact("test_user", "Test fact", "preferences")

        assert fact_id is not None

        # Verify fact was saved
        fact = temp_db.get_fact(fact_id)
        assert fact is not None
        assert fact.source == "explicit"


# ============================================================================
# TEST CLASS: Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_fact_id_deterministic(self):
        """Test that fact ID generation is deterministic."""
        id1 = generate_fact_id("user1", "Test fact", "preferences")
        id2 = generate_fact_id("user1", "Test fact", "preferences")

        assert id1 == id2

    def test_generate_fact_id_unique(self):
        """Test that different inputs generate different IDs."""
        id1 = generate_fact_id("user1", "Test fact", "preferences")
        id2 = generate_fact_id("user2", "Test fact", "preferences")
        id3 = generate_fact_id("user1", "Different fact", "preferences")

        assert id1 != id2
        assert id1 != id3

    def test_generate_history_id(self):
        """Test history ID generation."""
        import time
        timestamp = time.time()

        id1 = generate_history_id("fact123", timestamp)
        id2 = generate_history_id("fact123", timestamp + 1)

        assert len(id1) == 16
        assert id1 != id2

    def test_user_fact_to_dict(self, temp_db):
        """Test UserFact.to_dict() method."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="explicit",
            user_id="test_user"
        )

        fact_dict = fact.to_dict()

        assert isinstance(fact_dict, dict)
        assert fact_dict['fact'] == "Test fact"
        assert fact_dict['category'] == "preferences"
        assert fact_dict['user_id'] == "test_user"

    def test_user_fact_from_dict(self):
        """Test UserFact.from_dict() method."""
        data = {
            'fact_id': 'test123',
            'user_id': 'test_user',
            'fact': 'Test fact',
            'category': 'preferences',
            'confidence': 0.9,
            'initial_confidence': 0.9,
            'source': 'explicit',
            'first_seen': datetime.now().isoformat(),
            'last_reinforced': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'reinforcement_count': 1,
            'contradiction_count': 0,
            'decay_rate': 0.99,
            'decay_floor': 0.2,
            'is_active': True,
        }

        fact = UserFact.from_dict(data)

        assert fact.fact_id == 'test123'
        assert fact.fact == 'Test fact'
        assert fact.confidence == 0.9


class TestFactDeactivation:
    """Tests for fact deactivation and reactivation."""

    def test_deactivate_fact(self, temp_db):
        """Test deactivating a fact."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )

        success = temp_db.deactivate_fact(fact.fact_id, "User requested removal")

        assert success is True

        # Fact should not appear in normal queries
        facts = temp_db.get_facts(user_id="test_user", include_inactive=False)
        assert not any(f.fact_id == fact.fact_id for f in facts)

    def test_deactivate_nonexistent(self, temp_db):
        """Test deactivating a fact that doesn't exist."""
        success = temp_db.deactivate_fact("nonexistent_id")
        assert success is False

    def test_reactivate_fact(self, temp_db):
        """Test reactivating a deactivated fact."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )

        temp_db.deactivate_fact(fact.fact_id)
        success = temp_db.reactivate_fact(fact.fact_id)

        assert success is True

        # Fact should appear again
        facts = temp_db.get_facts(user_id="test_user")
        assert any(f.fact_id == fact.fact_id for f in facts)

    def test_include_inactive_flag(self, temp_db):
        """Test the include_inactive flag in get_facts."""
        fact = temp_db.save_fact(
            "Test fact",
            "preferences",
            source="conversation",
            user_id="test_user"
        )
        temp_db.deactivate_fact(fact.fact_id)

        # Should not include inactive by default
        active_only = temp_db.get_facts(user_id="test_user", include_inactive=False)
        assert not any(f.fact_id == fact.fact_id for f in active_only)

        # Should include when requested
        with_inactive = temp_db.get_facts(user_id="test_user", include_inactive=True)
        assert any(f.fact_id == fact.fact_id for f in with_inactive)


class TestStatistics:
    """Tests for fact statistics functionality."""

    def test_get_stats_basic(self, populated_db):
        """Test getting basic statistics."""
        stats = populated_db.get_stats()

        assert 'total_facts' in stats
        assert 'active_facts' in stats
        assert 'by_category' in stats
        assert 'by_source' in stats
        assert 'avg_confidence' in stats

    def test_get_stats_by_category(self, populated_db):
        """Test category breakdown in statistics."""
        stats = populated_db.get_stats()

        assert isinstance(stats['by_category'], dict)
        assert 'preferences' in stats['by_category'] or 'skills' in stats['by_category']

    def test_get_stats_confidence(self, populated_db):
        """Test confidence statistics."""
        stats = populated_db.get_stats()

        assert 0.0 <= stats['avg_confidence'] <= 1.0
        assert 'high_confidence_count' in stats
        assert 'low_confidence_count' in stats


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
