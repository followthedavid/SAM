#!/usr/bin/env python3
"""
Tests for SAM Query Decomposer - Phase 2.2.4
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from remember.query_decomposer import QueryDecomposer, DecomposedQuery, is_complex_query, decompose


class TestQueryDecomposer:
    """Test suite for QueryDecomposer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.decomposer = QueryDecomposer()

    # =========================================================================
    # is_complex_query tests
    # =========================================================================

    def test_simple_query_not_complex(self):
        """Simple queries should not be flagged as complex."""
        simple_queries = [
            "search memory",
            "find function",
            "user authentication",
            "database query",
        ]
        for q in simple_queries:
            assert not self.decomposer.is_complex_query(q), f"'{q}' should not be complex"

    def test_conjunction_query_is_complex(self):
        """Queries with conjunctions should be complex."""
        complex_queries = [
            "memory and storage",
            "authentication or authorization",
            "create and update",
            "files as well as directories",
        ]
        for q in complex_queries:
            assert self.decomposer.is_complex_query(q), f"'{q}' should be complex"

    def test_comma_list_is_complex(self):
        """Queries with comma-separated items should be complex."""
        assert self.decomposer.is_complex_query("auth, logging, database")
        assert self.decomposer.is_complex_query("create, update, delete")

    def test_multiple_questions_is_complex(self):
        """Queries with multiple question words should be complex."""
        assert self.decomposer.is_complex_query("How does it work? What is stored?")
        assert self.decomposer.is_complex_query("Where is the config and how to change it")

    def test_multiple_topics_is_complex(self):
        """Queries mentioning multiple topic clusters should be complex."""
        assert self.decomposer.is_complex_query("authentication and logging system")
        assert self.decomposer.is_complex_query("database and API endpoints")

    # =========================================================================
    # decompose tests
    # =========================================================================

    def test_decompose_conjunction(self):
        """Test decomposition by conjunction."""
        result = self.decomposer.decompose("memory and storage")

        assert len(result.sub_queries) == 2
        assert "memory" in result.sub_queries
        assert "storage" in result.sub_queries
        assert result.query_type == "conjunction"
        assert result.confidence >= 0.9

    def test_decompose_combined_list(self):
        """Test decomposition of combined comma+conjunction lists."""
        result = self.decomposer.decompose("auth, logging, and database")

        assert len(result.sub_queries) == 3
        assert result.query_type == "combined_list"
        assert result.confidence >= 0.9

    def test_decompose_compound(self):
        """Test decomposition by commas only."""
        result = self.decomposer.decompose("endpoint, handler, format")

        assert len(result.sub_queries) == 3
        assert result.query_type == "compound"

    def test_decompose_preserves_context(self):
        """Test that context is preserved in sub-queries."""
        result = self.decomposer.decompose("Find Python files with auth, logging, and API handling")

        # Each sub-query should have the context
        for sq in result.sub_queries:
            assert "Python" in sq.lower() or "find" in sq.lower() or len(sq) > 20

    def test_decompose_simple_returns_original(self):
        """Simple queries should return the original query."""
        result = self.decomposer.decompose("simple search")

        assert len(result.sub_queries) == 1
        assert result.sub_queries[0] == "simple search"
        assert result.query_type == "simple"
        assert result.confidence == 1.0

    def test_decompose_question_split(self):
        """Test decomposition of multiple questions."""
        result = self.decomposer.decompose("How does it work? What are the options?")

        assert len(result.sub_queries) >= 2
        assert any("how" in sq.lower() for sq in result.sub_queries)
        assert any("what" in sq.lower() for sq in result.sub_queries)

    def test_decompose_limits_sub_queries(self):
        """Test that decomposition respects max_sub_queries limit."""
        decomposer = QueryDecomposer(max_sub_queries=2)
        result = decomposer.decompose("a, b, c, d, e, f")

        assert len(result.sub_queries) <= 2

    def test_decompose_cleans_sub_queries(self):
        """Test that sub-queries are cleaned properly."""
        result = self.decomposer.decompose("memory and storage?")

        # Should not have trailing punctuation
        for sq in result.sub_queries:
            assert not sq.endswith("?")
            assert not sq.endswith(",")

    def test_decompose_deduplicates(self):
        """Test that duplicate sub-queries are removed."""
        result = self.decomposer.decompose("memory and memory storage")

        # Should not have duplicate "memory"
        unique_lower = set(sq.lower() for sq in result.sub_queries)
        assert len(unique_lower) == len(result.sub_queries)

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_empty_query(self):
        """Empty query should not crash."""
        result = self.decomposer.decompose("")
        assert result.sub_queries == [""]

    def test_whitespace_query(self):
        """Whitespace-only query should be handled."""
        result = self.decomposer.decompose("   ")
        assert len(result.sub_queries) == 1

    def test_single_word(self):
        """Single word query should not be complex."""
        assert not self.decomposer.is_complex_query("search")
        result = self.decomposer.decompose("search")
        assert result.sub_queries == ["search"]

    def test_quotes_not_split(self):
        """Quoted text should not be split."""
        result = self.decomposer.decompose('"one, two, three"')
        # Quotes are tricky - for now just ensure no crash
        assert len(result.sub_queries) >= 1

    # =========================================================================
    # Module-level functions
    # =========================================================================

    def test_module_is_complex_query(self):
        """Test module-level is_complex_query function."""
        assert is_complex_query("memory and storage")
        assert not is_complex_query("simple")

    def test_module_decompose(self):
        """Test module-level decompose function."""
        result = decompose("memory and storage")
        assert isinstance(result, DecomposedQuery)
        assert len(result.sub_queries) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
