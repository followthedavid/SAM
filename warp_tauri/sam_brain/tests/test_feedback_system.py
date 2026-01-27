#!/usr/bin/env python3
"""
Tests for the Feedback System

Phase 1.2.10: Comprehensive test coverage for the feedback loop system.

Tests cover:
1. FeedbackDB - save, retrieve, stats
2. CorrectionAnalyzer - error detection, diff analysis
3. ConfidenceAdjuster - modifier calculation, escalation decisions
4. TrainingExampleGenerator - format generation, deduplication
5. Integration - full feedback flow from submission to training export

Run with: pytest tests/test_feedback_system.py -v
"""

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest

# Import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from feedback_system import (
    # Core classes
    FeedbackDB,
    FeedbackEntry,
    FeedbackType,
    CorrectionType,
    FlagType,
    CorrectionAnalyzer,
    CorrectionAnalysis,
    ErrorCategory,
    DiffSegment,
    ConfidenceAdjuster,
    TrainingExampleGenerator,
    # Utility functions
    generate_response_id,
    generate_feedback_id,
    calculate_feedback_weight,
    record_feedback_for_confidence,
    get_feedback_db_path,
    is_external_drive_mounted,
)


# =============================================================================
# FIXTURES - Common test data
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_feedback.db"


@pytest.fixture
def feedback_db(temp_db_path):
    """Create a FeedbackDB instance with temporary database."""
    return FeedbackDB(db_path=temp_db_path)


@pytest.fixture
def correction_analyzer():
    """Create a CorrectionAnalyzer instance."""
    return CorrectionAnalyzer()


@pytest.fixture
def confidence_adjuster(temp_db_path):
    """Create a ConfidenceAdjuster instance with temporary database."""
    return ConfidenceAdjuster(db_path=temp_db_path)


@pytest.fixture
def training_generator(temp_db_path):
    """Create a TrainingExampleGenerator instance with temporary database."""
    return TrainingExampleGenerator(db_path=temp_db_path)


@pytest.fixture
def sample_feedback_entry():
    """Create a sample FeedbackEntry for testing."""
    return FeedbackEntry(
        feedback_id="test_fb_001",
        response_id="test_resp_001",
        session_id="test_session_001",
        feedback_type="rating",
        rating=1,
        original_query="What is the capital of Australia?",
        original_response="The capital of Australia is Canberra.",
        domain="factual",
        timestamp=time.time(),
    )


@pytest.fixture
def sample_correction_feedback():
    """Create a sample correction feedback entry."""
    return {
        "response_id": "resp_corr_001",
        "session_id": "sess_001",
        "original_query": "What is the capital of Australia?",
        "original_response": "The capital of Australia is Sydney.",
        "feedback_type": "correction",
        "correction": "The capital of Australia is Canberra, not Sydney.",
        "correction_type": "full_replacement",
        "what_was_wrong": "Wrong city - Sydney is the largest city but not the capital.",
        "domain": "factual",
    }


@pytest.fixture
def sample_preference_feedback():
    """Create a sample preference feedback entry."""
    return {
        "response_id": "resp_pref_001",
        "session_id": "sess_001",
        "original_query": "Explain Python list comprehensions",
        "original_response": "List comprehensions are a way to create lists in Python.",
        "feedback_type": "preference",
        "preferred_response": "List comprehensions provide a concise way to create lists. Example: [x**2 for x in range(10)] creates [0, 1, 4, 9, 16, 25, 36, 49, 64, 81].",
        "comparison_basis": "More detailed with a concrete example",
        "domain": "code",
    }


# =============================================================================
# FEEDBACKDB TESTS
# =============================================================================

class TestFeedbackDB:
    """Tests for FeedbackDB class."""

    def test_db_initialization(self, feedback_db, temp_db_path):
        """Test that database is created with correct schema."""
        assert temp_db_path.exists()

        conn = sqlite3.connect(temp_db_path)
        cur = conn.cursor()

        # Check that tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}

        assert "feedback" in tables
        assert "feedback_aggregates" in tables
        assert "feedback_sessions" in tables
        assert "confidence_tracking" in tables

        conn.close()

    def test_save_rating_feedback(self, feedback_db):
        """Test saving a rating feedback entry."""
        feedback_id = feedback_db.save_feedback(
            response_id="resp_001",
            session_id="sess_001",
            original_query="What is 2+2?",
            original_response="2+2 equals 4.",
            feedback_type="rating",
            rating=1,
            domain="reasoning",
        )

        assert feedback_id is not None
        assert len(feedback_id) == 16  # SHA256 prefix length

    def test_save_correction_feedback(self, feedback_db, sample_correction_feedback):
        """Test saving a correction feedback entry."""
        feedback_id = feedback_db.save_feedback(**sample_correction_feedback)

        assert feedback_id is not None

        # Retrieve and verify
        feedback_list = feedback_db.get_feedback_for_response(sample_correction_feedback["response_id"])
        assert len(feedback_list) == 1

        fb = feedback_list[0]
        assert fb["feedback_type"] == "correction"
        assert fb["correction"] == sample_correction_feedback["correction"]
        assert fb["what_was_wrong"] == sample_correction_feedback["what_was_wrong"]

    def test_save_preference_feedback(self, feedback_db, sample_preference_feedback):
        """Test saving a preference feedback entry."""
        feedback_id = feedback_db.save_feedback(**sample_preference_feedback)

        feedback_list = feedback_db.get_feedback_for_response(sample_preference_feedback["response_id"])
        assert len(feedback_list) == 1

        fb = feedback_list[0]
        assert fb["feedback_type"] == "preference"
        assert fb["preferred_response"] == sample_preference_feedback["preferred_response"]

    def test_get_recent_feedback(self, feedback_db):
        """Test retrieving recent feedback entries."""
        # Save multiple feedback entries
        for i in range(5):
            feedback_db.save_feedback(
                response_id=f"resp_{i:03d}",
                session_id="sess_001",
                original_query=f"Question {i}",
                original_response=f"Answer {i}",
                feedback_type="rating",
                rating=1 if i % 2 == 0 else -1,
                domain="general",
            )

        # Get recent feedback
        recent = feedback_db.get_recent_feedback(limit=3)
        assert len(recent) == 3

        # Most recent should be last added
        assert recent[0]["original_query"] == "Question 4"

    def test_get_recent_feedback_with_filters(self, feedback_db, sample_correction_feedback, sample_preference_feedback):
        """Test filtering recent feedback by type and domain."""
        feedback_db.save_feedback(**sample_correction_feedback)
        feedback_db.save_feedback(**sample_preference_feedback)

        # Filter by feedback type
        corrections = feedback_db.get_recent_feedback(feedback_type="correction")
        assert len(corrections) == 1
        assert corrections[0]["feedback_type"] == "correction"

        # Filter by domain
        code_feedback = feedback_db.get_recent_feedback(domain="code")
        assert len(code_feedback) == 1
        assert code_feedback[0]["domain"] == "code"

    def test_feedback_stats(self, feedback_db, sample_correction_feedback):
        """Test getting feedback statistics."""
        # Add some feedback
        feedback_db.save_feedback(
            response_id="resp_pos",
            session_id="sess_001",
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=1,
            domain="general",
        )
        feedback_db.save_feedback(
            response_id="resp_neg",
            session_id="sess_001",
            original_query="Test2?",
            original_response="Test response 2",
            feedback_type="rating",
            rating=-1,
            domain="general",
        )
        feedback_db.save_feedback(**sample_correction_feedback)

        stats = feedback_db.get_feedback_stats()

        assert stats["total_feedback"] == 3
        assert stats["by_type"]["rating"] == 2
        assert stats["by_type"]["correction"] == 1
        assert stats["sentiment"]["positive"] == 1
        assert stats["sentiment"]["negative"] == 1

    def test_response_aggregates(self, feedback_db):
        """Test response aggregate calculations."""
        response_id = "resp_multi"

        # Add multiple feedback for same response
        feedback_db.save_feedback(
            response_id=response_id,
            session_id="sess_001",
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=1,
            domain="general",
        )
        feedback_db.save_feedback(
            response_id=response_id,
            session_id="sess_002",
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=1,
            domain="general",
        )
        feedback_db.save_feedback(
            response_id=response_id,
            session_id="sess_003",
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=-1,
            domain="general",
        )

        aggregates = feedback_db.get_response_aggregates(response_id)

        assert aggregates is not None
        assert aggregates["thumbs_up_count"] == 2
        assert aggregates["thumbs_down_count"] == 1
        assert len(aggregates["session_ids"]) == 3

    def test_mark_as_processed(self, feedback_db, sample_correction_feedback):
        """Test marking feedback as processed."""
        feedback_id = feedback_db.save_feedback(**sample_correction_feedback)

        # Mark as processed
        success = feedback_db.mark_as_processed(feedback_id, training_format="correction_analysis")
        assert success is True

        # Verify it's marked
        feedback_list = feedback_db.get_feedback_for_response(sample_correction_feedback["response_id"])
        assert feedback_list[0]["processed"] == 1
        assert feedback_list[0]["training_format"] == "correction_analysis"

    def test_get_unprocessed_for_training(self, feedback_db, sample_correction_feedback):
        """Test getting unprocessed feedback for training."""
        # Add correction (high quality)
        feedback_id = feedback_db.save_feedback(**sample_correction_feedback)

        # Add flag (excluded from training)
        feedback_db.save_feedback(
            response_id="resp_flag",
            session_id="sess_001",
            original_query="Test?",
            original_response="Test response",
            feedback_type="flag",
            flag_type="harmful",
            domain="general",
        )

        unprocessed = feedback_db.get_unprocessed_for_training(min_quality=0.0)

        # Should only get the correction, not the flag
        assert len(unprocessed) == 1
        assert unprocessed[0]["feedback_type"] == "correction"

    def test_session_tracking(self, feedback_db):
        """Test session statistics tracking."""
        session_id = "sess_track"

        # Increment responses (simulating SAM generating responses)
        feedback_db.increment_session_responses(session_id)
        feedback_db.increment_session_responses(session_id)
        feedback_db.increment_session_responses(session_id)

        # Add feedback
        feedback_db.save_feedback(
            response_id="resp_001",
            session_id=session_id,
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=1,
            domain="general",
        )

        session_stats = feedback_db.get_session_stats(session_id)

        assert session_stats is not None
        assert session_stats["total_responses"] == 3
        assert session_stats["feedback_given"] == 1
        assert session_stats["positive_count"] == 1

    def test_daily_counts(self, feedback_db, sample_correction_feedback):
        """Test daily correction and negative feedback counts."""
        # Add a correction
        feedback_db.save_feedback(**sample_correction_feedback)

        # Add negative rating
        feedback_db.save_feedback(
            response_id="resp_neg",
            session_id="sess_001",
            original_query="Test?",
            original_response="Test response",
            feedback_type="rating",
            rating=-1,
            domain="general",
        )

        assert feedback_db.get_daily_correction_count() >= 1
        assert feedback_db.get_daily_negative_count() >= 1
        assert feedback_db.get_unprocessed_count() >= 2


# =============================================================================
# CORRECTION ANALYZER TESTS
# =============================================================================

class TestCorrectionAnalyzer:
    """Tests for CorrectionAnalyzer class."""

    def test_analyze_simple_correction(self, correction_analyzer):
        """Test analyzing a simple factual correction."""
        analysis = correction_analyzer.analyze_correction(
            original="The capital of Australia is Sydney.",
            correction="The capital of Australia is Canberra.",
            query="What is the capital of Australia?",
        )

        assert isinstance(analysis, CorrectionAnalysis)
        assert analysis.original_text == "The capital of Australia is Sydney."
        assert analysis.corrected_text == "The capital of Australia is Canberra."
        assert analysis.similarity_ratio > 0.5  # Should be fairly similar
        assert analysis.similarity_ratio < 1.0  # But not identical

    def test_error_type_detection_factual(self, correction_analyzer):
        """Test detection of factual errors."""
        analysis = correction_analyzer.analyze_correction(
            original="Python was created in 1995.",
            correction="Python was created in 1991.",
            what_was_wrong="Wrong year - Python was released in 1991.",
        )

        # Should detect factual error due to year change and "wrong" keyword
        assert "factual" in analysis.error_types

    def test_error_type_detection_incomplete(self, correction_analyzer):
        """Test detection of incomplete responses."""
        analysis = correction_analyzer.analyze_correction(
            original="Python is a programming language.",
            correction="Python is a programming language. It was created by Guido van Rossum and is known for its readable syntax.",
            what_was_wrong="Missing important information about creator and characteristics.",
        )

        # Correction is significantly longer, should detect incomplete
        assert "incomplete" in analysis.error_types

    def test_error_type_detection_verbose(self, correction_analyzer):
        """Test detection of verbose responses."""
        analysis = correction_analyzer.analyze_correction(
            original="It is important to note that at this point in time, the function basically essentially returns the value which is really quite significant.",
            correction="The function returns the value.",
        )

        # Correction is much shorter, should detect verbose
        assert "verbose" in analysis.error_types

    def test_diff_segments(self, correction_analyzer):
        """Test diff segment generation."""
        analysis = correction_analyzer.analyze_correction(
            original="Hello world",
            correction="Hello Python",
        )

        # Should have diff segments
        assert len(analysis.diff_segments) > 0

        # Check that we have a replace operation for "world" -> "Python"
        replace_segments = [s for s in analysis.diff_segments if s.operation == "replace"]
        assert len(replace_segments) > 0

    def test_change_ratio_calculation(self, correction_analyzer):
        """Test change ratio calculation."""
        # Identical texts
        analysis_same = correction_analyzer.analyze_correction(
            original="Hello world",
            correction="Hello world",
        )
        assert analysis_same.change_ratio == 0.0

        # Completely different texts
        analysis_diff = correction_analyzer.analyze_correction(
            original="Hello world",
            correction="Goodbye universe",
        )
        assert analysis_diff.change_ratio > 0.5

    def test_training_example_generation(self, correction_analyzer):
        """Test training example format generation."""
        analysis = correction_analyzer.analyze_correction(
            original="2 + 2 = 5",
            correction="2 + 2 = 4",
            query="What is 2 + 2?",
        )

        assert analysis.training_example is not None
        assert "instruction" in analysis.training_example
        assert "output" in analysis.training_example
        assert analysis.training_example["output"] == "2 + 2 = 4"

    def test_error_patterns_extraction(self, correction_analyzer):
        """Test extraction of specific error patterns."""
        analysis = correction_analyzer.analyze_correction(
            original="The sky is green and water flows uphill.",
            correction="The sky is blue and water flows downhill.",
        )

        # Should extract patterns for the changes
        assert len(analysis.error_patterns) > 0

        # Check pattern structure
        for pattern in analysis.error_patterns:
            assert "original_fragment" in pattern
            assert "corrected_fragment" in pattern
            assert "operation" in pattern

    def test_code_error_detection(self, correction_analyzer):
        """Test detection of code-related errors."""
        analysis = correction_analyzer.analyze_correction(
            original="```python\ndef foo():\n    retrun x\n```",
            correction="```python\ndef foo():\n    return x\n```",
            what_was_wrong="Typo in return statement",
        )

        # Should detect code-related error
        code_errors = [e for e in analysis.error_types if e.startswith("code_")]
        assert len(code_errors) > 0

    def test_to_dict_and_json(self, correction_analyzer):
        """Test serialization of CorrectionAnalysis."""
        analysis = correction_analyzer.analyze_correction(
            original="Test original",
            correction="Test corrected",
        )

        # Test to_dict
        d = analysis.to_dict()
        assert isinstance(d, dict)
        assert d["original_text"] == "Test original"

        # Test to_json
        j = analysis.to_json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["corrected_text"] == "Test corrected"


# =============================================================================
# CONFIDENCE ADJUSTER TESTS
# =============================================================================

class TestConfidenceAdjuster:
    """Tests for ConfidenceAdjuster class."""

    def test_record_positive_feedback(self, confidence_adjuster):
        """Test recording positive feedback updates stats."""
        confidence_adjuster.record_feedback(
            domain="code",
            topic="python",
            is_positive=True,
            is_correction=False,
        )

        # Get stats
        stats = confidence_adjuster.get_domain_stats()
        assert "code" in stats["domains"]

    def test_record_negative_feedback(self, confidence_adjuster):
        """Test recording negative feedback updates stats."""
        # Record enough feedback to be reliable
        for _ in range(5):
            confidence_adjuster.record_feedback(
                domain="factual",
                topic="general",
                is_positive=False,
                is_correction=True,
                error_type="factual",
            )

        stats = confidence_adjuster.get_domain_stats()
        assert stats["domains"]["factual"]["topics"]["general"]["corrections_received"] == 5

    def test_confidence_modifier_calculation(self, confidence_adjuster):
        """Test confidence modifier calculation."""
        # Record mixed feedback
        for _ in range(7):
            confidence_adjuster.record_feedback(
                domain="code",
                topic="general",
                is_positive=True,
            )
        for _ in range(3):
            confidence_adjuster.record_feedback(
                domain="code",
                topic="general",
                is_positive=False,
            )

        modifier = confidence_adjuster.get_confidence_modifier("code", "general")

        # Should be in valid range
        assert -0.3 <= modifier <= 0.3

    def test_escalation_recommendation(self, confidence_adjuster):
        """Test escalation recommendation based on accuracy."""
        # Record mostly negative feedback for reasoning domain
        for _ in range(8):
            confidence_adjuster.record_feedback(
                domain="reasoning",
                topic="general",
                is_positive=False,
            )
        for _ in range(2):
            confidence_adjuster.record_feedback(
                domain="reasoning",
                topic="general",
                is_positive=True,
            )

        # Should recommend escalation for low accuracy
        should_escalate = confidence_adjuster.should_suggest_escalation("reasoning")
        assert should_escalate is True

    def test_no_escalation_for_good_accuracy(self, confidence_adjuster):
        """Test no escalation when accuracy is good."""
        # Record mostly positive feedback
        for _ in range(8):
            confidence_adjuster.record_feedback(
                domain="code",
                topic="general",
                is_positive=True,
            )
        for _ in range(2):
            confidence_adjuster.record_feedback(
                domain="code",
                topic="general",
                is_positive=False,
            )

        # Should not recommend escalation
        should_escalate = confidence_adjuster.should_suggest_escalation("code")
        assert should_escalate is False

    def test_trend_calculation_improving(self, confidence_adjuster):
        """Test trend detection for improving accuracy."""
        # First half: negative
        for _ in range(5):
            confidence_adjuster.record_feedback(
                domain="general",
                topic="general",
                is_positive=False,
            )
        # Second half: positive
        for _ in range(5):
            confidence_adjuster.record_feedback(
                domain="general",
                topic="general",
                is_positive=True,
            )

        stats = confidence_adjuster.get_domain_stats()
        trend = stats["domains"]["general"]["topics"]["general"]["trend"]
        assert trend["direction"] == "improving"

    def test_trend_calculation_declining(self, confidence_adjuster):
        """Test trend detection for declining accuracy."""
        # First half: positive
        for _ in range(5):
            confidence_adjuster.record_feedback(
                domain="general",
                topic="general",
                is_positive=True,
            )
        # Second half: negative
        for _ in range(5):
            confidence_adjuster.record_feedback(
                domain="general",
                topic="general",
                is_positive=False,
            )

        stats = confidence_adjuster.get_domain_stats()
        trend = stats["domains"]["general"]["topics"]["general"]["trend"]
        assert trend["direction"] == "declining"

    def test_error_type_tracking(self, confidence_adjuster):
        """Test tracking of error types per domain."""
        confidence_adjuster.record_feedback(
            domain="code",
            topic="python",
            is_positive=False,
            is_correction=True,
            error_type="syntax",
        )
        confidence_adjuster.record_feedback(
            domain="code",
            topic="python",
            is_positive=False,
            is_correction=True,
            error_type="syntax",
        )
        confidence_adjuster.record_feedback(
            domain="code",
            topic="python",
            is_positive=False,
            is_correction=True,
            error_type="logic",
        )

        error_patterns = confidence_adjuster.get_topic_error_patterns("code", "python")
        assert error_patterns["syntax"] == 2
        assert error_patterns["logic"] == 1

    def test_reset_topic(self, confidence_adjuster):
        """Test resetting confidence tracking for a topic."""
        confidence_adjuster.record_feedback(
            domain="test_domain",
            topic="test_topic",
            is_positive=True,
        )

        # Verify data exists
        stats_before = confidence_adjuster.get_domain_stats()
        assert "test_domain" in stats_before["domains"]

        # Reset
        confidence_adjuster.reset_topic("test_domain", "test_topic")

        # Verify data is gone
        modifier = confidence_adjuster.get_confidence_modifier("test_domain", "test_topic")
        assert modifier == 0.0  # No data returns neutral


# =============================================================================
# TRAINING EXAMPLE GENERATOR TESTS
# =============================================================================

class TestTrainingExampleGenerator:
    """Tests for TrainingExampleGenerator class."""

    def test_instruction_format_from_correction(self, training_generator, temp_db_path):
        """Test generating instruction format from correction feedback."""
        # First add a correction to the database
        db = FeedbackDB(db_path=temp_db_path)
        db.save_feedback(
            response_id="resp_001",
            session_id="sess_001",
            original_query="What is the capital of France?",
            original_response="The capital of France is Lyon.",
            feedback_type="correction",
            correction="The capital of France is Paris.",
            what_was_wrong="Wrong city",
            domain="factual",
        )

        result = training_generator.generate_training_data(
            format_type="instruction",
            min_quality=0.0,
        )

        assert result["count"] >= 1

    def test_dpo_format_generation(self, training_generator, temp_db_path):
        """Test generating DPO preference pairs."""
        db = FeedbackDB(db_path=temp_db_path)
        db.save_feedback(
            response_id="resp_002",
            session_id="sess_001",
            original_query="Explain recursion",
            original_response="Recursion is when a function calls itself.",
            feedback_type="correction",
            correction="Recursion is when a function calls itself to solve a smaller subproblem. For example, calculating factorial: factorial(n) = n * factorial(n-1).",
            domain="code",
        )

        result = training_generator.generate_training_data(
            format_type="dpo",
            min_quality=0.0,
        )

        assert result["count"] >= 1

    def test_deduplication(self, training_generator, temp_db_path):
        """Test that duplicate examples are removed."""
        db = FeedbackDB(db_path=temp_db_path)

        # Add same feedback twice
        for _ in range(2):
            db.save_feedback(
                response_id=f"resp_{time.time()}",  # Unique ID
                session_id="sess_001",
                original_query="What is 2+2?",
                original_response="2+2 equals 4.",
                feedback_type="rating",
                rating=1,
                domain="reasoning",
            )

        result_with_dedup = training_generator.generate_training_data(
            format_type="instruction",
            min_quality=0.0,
            deduplicate=True,
        )

        # Clear seen hashes for next test
        training_generator._seen_hashes.clear()

        result_without_dedup = training_generator.generate_training_data(
            format_type="instruction",
            min_quality=0.0,
            deduplicate=False,
        )

        # With deduplication should have fewer or equal examples
        assert result_with_dedup["count"] <= result_without_dedup["count"]

    def test_quality_filtering(self, training_generator, temp_db_path):
        """Test that low-quality feedback is filtered out."""
        db = FeedbackDB(db_path=temp_db_path)

        # Add high-quality correction (should pass)
        db.save_feedback(
            response_id="resp_high",
            session_id="sess_001",
            original_query="Explain Python decorators",
            original_response="Decorators are things.",
            feedback_type="correction",
            correction="Decorators are functions that modify the behavior of other functions. They are applied using the @decorator syntax above a function definition.",
            correction_type="full_replacement",
            what_was_wrong="Too vague, needs explanation and examples",
            domain="code",
        )

        # Generate with high quality threshold
        result_high = training_generator.generate_training_data(
            format_type="instruction",
            min_quality=0.9,
        )

        # Generate with low quality threshold
        training_generator._seen_hashes.clear()
        result_low = training_generator.generate_training_data(
            format_type="instruction",
            min_quality=0.0,
        )

        # Low threshold should have more or equal examples
        assert result_low["count"] >= result_high["count"]

    def test_training_stats(self, training_generator, temp_db_path):
        """Test getting training data statistics."""
        db = FeedbackDB(db_path=temp_db_path)

        db.save_feedback(
            response_id="resp_stat_1",
            session_id="sess_001",
            original_query="Test query",
            original_response="Test response",
            feedback_type="correction",
            correction="Better response",
            domain="general",
        )
        db.save_feedback(
            response_id="resp_stat_2",
            session_id="sess_001",
            original_query="Test query 2",
            original_response="Test response 2",
            feedback_type="preference",
            preferred_response="Preferred response",
            domain="general",
        )

        stats = training_generator.get_training_stats()

        assert stats["feedback"]["total_corrections"] >= 1
        assert stats["feedback"]["total_preferences"] >= 1
        assert stats["estimated"]["instruction"] >= 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full feedback flow."""

    def test_full_feedback_flow(self, temp_db_path):
        """Test complete flow from feedback submission to training export."""
        # 1. Create database and save feedback
        db = FeedbackDB(db_path=temp_db_path)

        feedback_id = db.save_feedback(
            response_id="resp_flow_001",
            session_id="sess_flow_001",
            original_query="How do I create a Python virtual environment?",
            original_response="Use pip to create a virtual environment.",
            feedback_type="correction",
            correction="Use 'python -m venv myenv' to create a virtual environment. Then activate it with 'source myenv/bin/activate' (Mac/Linux) or 'myenv\\Scripts\\activate' (Windows).",
            correction_type="full_replacement",
            what_was_wrong="Wrong command and missing activation instructions",
            domain="code",
        )

        assert feedback_id is not None

        # 2. Analyze the correction
        analyzer = CorrectionAnalyzer()
        feedback_list = db.get_feedback_for_response("resp_flow_001")
        fb = feedback_list[0]

        analysis = analyzer.analyze_correction(
            original=fb["original_response"],
            correction=fb["correction"],
            query=fb["original_query"],
            what_was_wrong=fb["what_was_wrong"],
        )

        assert analysis is not None
        assert len(analysis.error_types) > 0

        # 3. Update confidence tracking
        adjuster = ConfidenceAdjuster(db_path=temp_db_path)
        adjuster.record_feedback(
            domain="code",
            topic="python",
            is_positive=False,
            is_correction=True,
        )

        modifier = adjuster.get_confidence_modifier("code", "python")
        assert modifier is not None

        # 4. Generate training data
        generator = TrainingExampleGenerator(db_path=temp_db_path)
        result = generator.generate_training_data(
            format_type="instruction",
            min_quality=0.0,
        )

        assert result["count"] >= 1
        assert result["output_path"] is not None

        # 5. Verify the output file
        output_path = Path(result["output_path"])
        assert output_path.exists()

        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1

            example = json.loads(lines[0])
            assert "instruction" in example
            assert "output" in example

    def test_record_feedback_for_confidence_integration(self, temp_db_path):
        """Test the integration helper for updating confidence tracking."""
        adjuster = ConfidenceAdjuster(db_path=temp_db_path)

        # Create a feedback entry
        entry = FeedbackEntry(
            feedback_id="test_int_001",
            response_id="resp_int_001",
            session_id="sess_int_001",
            feedback_type="correction",
            correction="Corrected response",
            original_query="def foo(): How do I write a Python function?",
            original_response="Original response",
            domain="code",
            timestamp=time.time(),
        )

        # Record feedback for confidence
        record_feedback_for_confidence(entry, adjuster)

        # Verify tracking was updated
        stats = adjuster.get_domain_stats()
        assert "code" in stats["domains"]

    def test_feedback_weight_calculation(self):
        """Test feedback weight calculation with various inputs."""
        current_time = time.time()

        # Correction with explanation (high weight)
        correction_entry = FeedbackEntry(
            feedback_id="weight_001",
            response_id="resp_001",
            session_id="sess_001",
            feedback_type="correction",
            correction="A" * 150,  # Substantial correction
            what_was_wrong="This is a detailed explanation of what was wrong with the response" * 2,
            correction_type="full_replacement",
            original_query="Test",
            original_response="Test",
            timestamp=current_time,
        )

        weight_correction = calculate_feedback_weight(correction_entry, current_time)

        # Simple rating (lower weight)
        rating_entry = FeedbackEntry(
            feedback_id="weight_002",
            response_id="resp_002",
            session_id="sess_002",
            feedback_type="rating",
            rating=1,
            original_query="Test",
            original_response="Test",
            timestamp=current_time,
        )

        weight_rating = calculate_feedback_weight(rating_entry, current_time)

        # Correction should have higher weight than simple rating
        assert weight_correction > weight_rating

    def test_feedback_temporal_decay(self):
        """Test that older feedback has lower weight."""
        current_time = time.time()

        # Recent feedback
        recent_entry = FeedbackEntry(
            feedback_id="decay_001",
            response_id="resp_001",
            session_id="sess_001",
            feedback_type="rating",
            rating=1,
            original_query="Test",
            original_response="Test",
            timestamp=current_time,
        )

        # Old feedback (30 days ago)
        old_time = current_time - (30 * 24 * 3600)
        old_entry = FeedbackEntry(
            feedback_id="decay_002",
            response_id="resp_002",
            session_id="sess_002",
            feedback_type="rating",
            rating=1,
            original_query="Test",
            original_response="Test",
            timestamp=old_time,
        )

        weight_recent = calculate_feedback_weight(recent_entry, current_time)
        weight_old = calculate_feedback_weight(old_entry, current_time)

        # Recent feedback should have higher weight due to temporal decay
        assert weight_recent > weight_old


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_response_id(self):
        """Test response ID generation."""
        id1 = generate_response_id("query1", 1000.0)
        id2 = generate_response_id("query1", 1000.0)
        id3 = generate_response_id("query2", 1000.0)

        # Same inputs should give same ID
        assert id1 == id2
        # Different inputs should give different ID
        assert id1 != id3
        # Should be 16 characters
        assert len(id1) == 16

    def test_generate_feedback_id(self):
        """Test feedback ID generation."""
        id1 = generate_feedback_id("resp1", 1000.0)
        id2 = generate_feedback_id("resp1", 1001.0)

        # Different timestamps should give different IDs
        assert id1 != id2
        # Should be 16 characters
        assert len(id1) == 16

    def test_feedback_entry_serialization(self, sample_feedback_entry):
        """Test FeedbackEntry to_dict and from_dict."""
        d = sample_feedback_entry.to_dict()

        assert isinstance(d, dict)
        assert d["feedback_id"] == "test_fb_001"
        assert d["domain"] == "factual"

        # Test from_dict
        restored = FeedbackEntry.from_dict(d)
        assert restored.feedback_id == sample_feedback_entry.feedback_id
        assert restored.domain == sample_feedback_entry.domain


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Tests for enum types."""

    def test_feedback_type_values(self):
        """Test FeedbackType enum values."""
        assert FeedbackType.RATING.value == "rating"
        assert FeedbackType.CORRECTION.value == "correction"
        assert FeedbackType.PREFERENCE.value == "preference"
        assert FeedbackType.FLAG.value == "flag"

    def test_correction_type_values(self):
        """Test CorrectionType enum values."""
        assert CorrectionType.FULL_REPLACEMENT.value == "full_replacement"
        assert CorrectionType.PARTIAL_FIX.value == "partial_fix"
        assert CorrectionType.ADDITION.value == "addition"

    def test_flag_type_values(self):
        """Test FlagType enum values."""
        assert FlagType.HARMFUL.value == "harmful"
        assert FlagType.INCORRECT.value == "incorrect"
        assert FlagType.OFF_TOPIC.value == "off_topic"

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.FACTUAL.value == "factual"
        assert ErrorCategory.INCOMPLETE.value == "incomplete"
        assert ErrorCategory.CODE_SYNTAX.value == "code_syntax"
        assert ErrorCategory.HALLUCINATION.value == "hallucination"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
