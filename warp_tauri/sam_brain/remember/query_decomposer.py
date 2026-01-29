#!/usr/bin/env python3
"""
SAM Query Decomposer - Phase 2.2.4

Intelligently decomposes complex multi-part queries into sub-searches
for improved retrieval accuracy. Uses simple heuristics (no LLM calls)
to keep it lightweight and fast.

Examples:
    "How does the memory system work and where is it stored?"
    -> ["memory system architecture", "memory storage location"]

    "Find all Python files that handle authentication and logging"
    -> ["Python authentication handler", "Python logging handler"]

Usage:
    from remember.query_decomposer import QueryDecomposer, search_with_decomposition

    decomposer = QueryDecomposer()
    if decomposer.is_complex_query(query):
        results = decomposer.search_decomposed(query, indexer)
    else:
        results = indexer.search(query)
"""

import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass

# Type hints for code_indexer types (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from code_indexer import CodeIndexer, CodeSymbol


@dataclass
class DecomposedQuery:
    """Represents a decomposed query with its sub-queries."""
    original: str
    sub_queries: List[str]
    query_type: str  # 'conjunction', 'multi_topic', 'compound', 'simple'
    confidence: float  # How confident we are in the decomposition


@dataclass
class SearchResult:
    """Unified search result with deduplication support."""
    symbol_id: str
    symbol: 'CodeSymbol'
    score: float
    matched_queries: List[str]  # Which sub-queries matched this result

    def __hash__(self):
        return hash(self.symbol_id)

    def __eq__(self, other):
        if isinstance(other, SearchResult):
            return self.symbol_id == other.symbol_id
        return False


class QueryDecomposer:
    """
    Decomposes complex queries into simpler sub-queries for better retrieval.
    Uses lightweight heuristics - no LLM calls required.
    """

    # Conjunctions that indicate multi-part queries
    CONJUNCTIONS = {
        'and', 'or', 'as well as', 'along with', 'plus',
        'also', 'together with', 'in addition to'
    }

    # Question words that often indicate separate aspects
    QUESTION_MARKERS = {
        'how', 'what', 'where', 'when', 'why', 'which', 'who'
    }

    # Verbs that suggest action-oriented sub-queries
    ACTION_VERBS = {
        'find', 'search', 'get', 'show', 'list', 'display',
        'locate', 'fetch', 'retrieve', 'handle', 'process',
        'manage', 'create', 'update', 'delete', 'store'
    }

    # Topic keywords that often co-occur
    TOPIC_CLUSTERS = {
        'authentication': ['auth', 'login', 'logout', 'session', 'token', 'jwt', 'oauth'],
        'logging': ['log', 'logger', 'debug', 'trace', 'error', 'warning'],
        'database': ['db', 'sql', 'query', 'model', 'schema', 'migration', 'orm'],
        'api': ['endpoint', 'route', 'request', 'response', 'handler', 'rest'],
        'testing': ['test', 'spec', 'mock', 'fixture', 'assert', 'expect'],
        'memory': ['memory', 'cache', 'store', 'storage', 'persist', 'save'],
        'file': ['file', 'path', 'read', 'write', 'directory', 'folder'],
        'network': ['http', 'socket', 'connection', 'client', 'server', 'request'],
        'ui': ['view', 'component', 'render', 'display', 'button', 'form'],
        'config': ['config', 'settings', 'options', 'environment', 'env'],
    }

    # Common file type patterns
    FILE_TYPE_PATTERNS = {
        'python': ['python', 'py', '.py'],
        'javascript': ['javascript', 'js', '.js', 'typescript', 'ts', '.ts'],
        'rust': ['rust', 'rs', '.rs'],
        'swift': ['swift', '.swift'],
    }

    def __init__(self, min_query_length: int = 3, max_sub_queries: int = 5):
        """
        Initialize the query decomposer.

        Args:
            min_query_length: Minimum length for a sub-query to be valid
            max_sub_queries: Maximum number of sub-queries to generate
        """
        self.min_query_length = min_query_length
        self.max_sub_queries = max_sub_queries

        # Pre-compile regex patterns
        self._conjunction_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(c) for c in self.CONJUNCTIONS) + r')\b',
            re.IGNORECASE
        )
        self._question_pattern = re.compile(
            r'\b(' + '|'.join(self.QUESTION_MARKERS) + r')\b',
            re.IGNORECASE
        )

    def is_complex_query(self, query: str) -> bool:
        """
        Determine if a query is complex enough to benefit from decomposition.

        A query is considered complex if it:
        - Contains conjunctions (and, or, etc.)
        - Has multiple question words
        - Mentions multiple distinct topics
        - Is longer than a threshold

        Args:
            query: The search query

        Returns:
            True if the query should be decomposed
        """
        query_lower = query.lower()

        # Check for conjunctions
        if self._conjunction_pattern.search(query):
            return True

        # Check for multiple question words
        question_matches = self._question_pattern.findall(query)
        if len(question_matches) >= 2:
            return True

        # Check for multiple topic clusters
        topics_found = 0
        for topic, keywords in self.TOPIC_CLUSTERS.items():
            if any(kw in query_lower for kw in keywords):
                topics_found += 1

        if topics_found >= 2:
            return True

        # Check for comma-separated items
        if ',' in query and len(query.split(',')) >= 2:
            return True

        # Long queries (>50 chars) with multiple words often benefit from decomposition
        words = query.split()
        if len(query) > 50 and len(words) > 6:
            return True

        return False

    def decompose(self, query: str) -> DecomposedQuery:
        """
        Decompose a complex query into sub-queries.

        Args:
            query: The search query to decompose

        Returns:
            DecomposedQuery with original query and sub-queries
        """
        query = query.strip()
        sub_queries = []
        query_type = 'simple'
        confidence = 0.5

        # Strategy 1: Try combined comma + conjunction (e.g., "a, b, and c")
        combined_parts = self._split_combined_list(query)
        if len(combined_parts) > 1:
            sub_queries.extend(combined_parts)
            query_type = 'combined_list'
            confidence = 0.92

        # Strategy 2: Split by conjunctions only
        if not sub_queries:
            conjunction_parts = self._split_by_conjunctions(query)
            if len(conjunction_parts) > 1:
                sub_queries.extend(conjunction_parts)
                query_type = 'conjunction'
                confidence = 0.9

        # Strategy 3: Split by commas
        if not sub_queries:
            comma_parts = self._split_by_commas(query)
            if len(comma_parts) > 1:
                sub_queries.extend(comma_parts)
                query_type = 'compound'
                confidence = 0.85

        # Strategy 4: Extract topic-based sub-queries
        if not sub_queries:
            topic_queries = self._extract_topic_queries(query)
            if len(topic_queries) > 1:
                sub_queries.extend(topic_queries)
                query_type = 'multi_topic'
                confidence = 0.75

        # Strategy 5: Split question-based queries
        if not sub_queries:
            question_parts = self._split_by_questions(query)
            if len(question_parts) > 1:
                sub_queries.extend(question_parts)
                query_type = 'multi_question'
                confidence = 0.7

        # Clean and deduplicate sub-queries
        sub_queries = self._clean_sub_queries(sub_queries)

        # If no decomposition worked, use the original query
        if not sub_queries:
            sub_queries = [query]
            query_type = 'simple'
            confidence = 1.0

        # Limit the number of sub-queries
        sub_queries = sub_queries[:self.max_sub_queries]

        return DecomposedQuery(
            original=query,
            sub_queries=sub_queries,
            query_type=query_type,
            confidence=confidence
        )

    def _split_combined_list(self, query: str) -> List[str]:
        """
        Split queries that use both commas and conjunctions (e.g., "a, b, and c").

        This handles common list patterns like:
        - "auth, database, and API handling"
        - "create, update, or delete records"
        """
        # Pattern: items separated by commas with optional "and/or" before the last item
        # First check if there's a comma followed later by a conjunction
        if ',' not in query:
            return []

        # Look for pattern: "word, word, and word" or "word, word and word"
        # Remove the trailing conjunction pattern to get clean list
        query_lower = query.lower()

        # Check for ", and " or ", or " patterns
        final_conjunction = None
        for conj in ['and', 'or']:
            pattern = f', {conj} '
            if pattern in query_lower:
                final_conjunction = conj
                break
            # Also check without comma: "a, b and c"
            pattern2 = f' {conj} '
            if f', ' in query and pattern2 in query_lower:
                final_conjunction = conj
                break

        if not final_conjunction:
            return []

        # Split by commas first
        comma_parts = self._split_by_commas(query)
        if len(comma_parts) < 2:
            return []

        # The last part might contain "and X" - split it
        last_part = comma_parts[-1]
        last_part_lower = last_part.lower()

        # Check if last part starts with conjunction
        for conj in ['and ', 'or ']:
            if last_part_lower.startswith(conj):
                last_part = last_part[len(conj):].strip()
                comma_parts[-1] = last_part
                break
        else:
            # Check for " and " or " or " in the last part
            for conj in [' and ', ' or ']:
                if conj in last_part_lower:
                    idx = last_part_lower.index(conj)
                    before = last_part[:idx].strip()
                    after = last_part[idx + len(conj):].strip()
                    # Replace last part with before, add after
                    comma_parts[-1] = before
                    if after:
                        comma_parts.append(after)
                    break

        # Extract base context (like "Find Python files with")
        # and prepend to short items
        base_context = self._extract_list_context(query)

        # Add context to items that are just keywords
        enhanced_parts = []
        for part in comma_parts:
            part = part.strip()
            if len(part) < 15 and base_context:
                enhanced_parts.append(f"{base_context} {part}")
            else:
                enhanced_parts.append(part)

        return enhanced_parts

    def _extract_list_context(self, query: str) -> str:
        """Extract the prefix context before a list of items."""
        # Look for patterns like "Find X with" or "Search for X that"
        # The context is the part before the list items

        # Common list-introducing phrases
        list_starters = [
            r'(?:find|search|get|show|list)\s+(?:\w+\s+)?(?:with|that|for|handling|containing)',
            r'(?:looking for|searching for)',
            r'(?:files|functions|classes|methods)\s+(?:that|with|for)',
        ]

        query_lower = query.lower()

        for pattern in list_starters:
            match = re.search(pattern, query_lower)
            if match:
                # Return the original case version
                return query[:match.end()].strip()

        return ""

    def _split_by_conjunctions(self, query: str) -> List[str]:
        """Split query by conjunctions like 'and', 'or'."""
        parts = self._conjunction_pattern.split(query)
        # Filter out the conjunctions themselves and empty parts
        return [p.strip() for p in parts if p.strip() and p.lower() not in self.CONJUNCTIONS]

    def _split_by_commas(self, query: str) -> List[str]:
        """Split query by commas."""
        # Don't split if commas are inside quotes or parentheses
        parts = []
        current = []
        depth = 0
        in_quotes = False

        for char in query:
            if char == '"' or char == "'":
                in_quotes = not in_quotes
            elif char == '(' or char == '[' or char == '{':
                depth += 1
            elif char == ')' or char == ']' or char == '}':
                depth -= 1
            elif char == ',' and depth == 0 and not in_quotes:
                if current:
                    parts.append(''.join(current).strip())
                current = []
                continue
            current.append(char)

        if current:
            parts.append(''.join(current).strip())

        return [p for p in parts if len(p) >= self.min_query_length]

    def _extract_topic_queries(self, query: str) -> List[str]:
        """Extract sub-queries based on detected topics."""
        query_lower = query.lower()
        detected_topics = []

        for topic, keywords in self.TOPIC_CLUSTERS.items():
            for kw in keywords:
                if kw in query_lower:
                    detected_topics.append(topic)
                    break

        if len(detected_topics) < 2:
            return []

        # Create sub-queries for each topic, preserving context
        sub_queries = []
        base_context = self._extract_base_context(query)

        for topic in detected_topics:
            sub_query = f"{base_context} {topic}".strip() if base_context else topic
            sub_queries.append(sub_query)

        return sub_queries

    def _extract_base_context(self, query: str) -> str:
        """Extract the base context from a query (file type, language, etc.)."""
        query_lower = query.lower()
        context_parts = []

        # Check for file type mentions
        for lang, patterns in self.FILE_TYPE_PATTERNS.items():
            if any(p in query_lower for p in patterns):
                context_parts.append(lang)
                break

        # Check for action verbs at the start
        words = query.split()
        if words and words[0].lower() in self.ACTION_VERBS:
            # Skip the verb itself
            pass

        return ' '.join(context_parts)

    def _split_by_questions(self, query: str) -> List[str]:
        """Split queries that contain multiple questions."""
        # Pattern for question boundaries
        question_starters = r'(?:how|what|where|when|why|which|who)\s+'

        # Find all question-like segments
        parts = re.split(
            r'(?=\b(?:how|what|where|when|why|which|who)\b)',
            query,
            flags=re.IGNORECASE
        )

        return [p.strip() for p in parts if len(p.strip()) >= self.min_query_length]

    def _clean_sub_queries(self, queries: List[str]) -> List[str]:
        """Clean and deduplicate sub-queries."""
        cleaned = []
        seen = set()

        for q in queries:
            # Clean whitespace
            q = ' '.join(q.split())

            # Remove trailing punctuation
            q = q.rstrip('?.!,;:')

            # Skip if too short
            if len(q) < self.min_query_length:
                continue

            # Skip duplicates (case-insensitive)
            q_lower = q.lower()
            if q_lower in seen:
                continue
            seen.add(q_lower)

            cleaned.append(q)

        return cleaned

    def search_decomposed(
        self,
        query: str,
        indexer: 'CodeIndexer',
        project_id: Optional[str] = None,
        symbol_type: Optional[str] = None,
        limit: int = 10,
        parallel: bool = True
    ) -> List[Tuple['CodeSymbol', float]]:
        """
        Search using query decomposition with combined and deduplicated results.

        Args:
            query: The search query
            indexer: CodeIndexer instance to search with
            project_id: Optional project ID filter
            symbol_type: Optional symbol type filter
            limit: Maximum results to return
            parallel: Whether to run sub-searches in parallel

        Returns:
            List of (CodeSymbol, score) tuples, deduplicated and ranked
        """
        # Decompose the query
        decomposed = self.decompose(query)

        if len(decomposed.sub_queries) == 1:
            # Simple query, no decomposition needed
            return indexer.search(
                query, project_id=project_id,
                symbol_type=symbol_type, limit=limit
            )

        # Run sub-searches
        all_results: Dict[str, SearchResult] = {}

        if parallel:
            # Parallel execution for better performance
            with ThreadPoolExecutor(max_workers=min(len(decomposed.sub_queries), 4)) as executor:
                futures = {
                    executor.submit(
                        indexer.search, sub_q, project_id, symbol_type, limit * 2
                    ): sub_q
                    for sub_q in decomposed.sub_queries
                }

                for future in as_completed(futures):
                    sub_query = futures[future]
                    try:
                        results = future.result()
                        self._merge_results(all_results, results, sub_query)
                    except Exception as e:
                        # Log but don't fail on individual sub-query errors
                        pass
        else:
            # Sequential execution
            for sub_query in decomposed.sub_queries:
                try:
                    results = indexer.search(
                        sub_query, project_id=project_id,
                        symbol_type=symbol_type, limit=limit * 2
                    )
                    self._merge_results(all_results, results, sub_query)
                except Exception:
                    pass

        # Score and rank combined results
        ranked_results = self._rank_combined_results(all_results, decomposed)

        # Return in expected format
        return [(r.symbol, r.score) for r in ranked_results[:limit]]

    def _merge_results(
        self,
        all_results: Dict[str, SearchResult],
        new_results: List[Tuple['CodeSymbol', float]],
        sub_query: str
    ):
        """Merge new search results into the combined results dict."""
        for symbol, score in new_results:
            symbol_id = symbol.id

            if symbol_id in all_results:
                # Update existing result with better score and add query match
                existing = all_results[symbol_id]
                if score > existing.score:
                    existing.score = score
                if sub_query not in existing.matched_queries:
                    existing.matched_queries.append(sub_query)
            else:
                # Add new result
                all_results[symbol_id] = SearchResult(
                    symbol_id=symbol_id,
                    symbol=symbol,
                    score=score,
                    matched_queries=[sub_query]
                )

    def _rank_combined_results(
        self,
        all_results: Dict[str, SearchResult],
        decomposed: DecomposedQuery
    ) -> List[SearchResult]:
        """
        Rank combined results considering:
        - Number of sub-queries matched (coverage)
        - Individual search scores
        - Query decomposition confidence
        """
        results = list(all_results.values())
        total_queries = len(decomposed.sub_queries)

        for result in results:
            # Coverage bonus: results matching multiple sub-queries rank higher
            coverage = len(result.matched_queries) / total_queries
            coverage_bonus = coverage * 0.3  # Up to 30% bonus

            # Adjust score with coverage bonus
            result.score = result.score * (1.0 + coverage_bonus)

            # Apply decomposition confidence as a slight modifier
            result.score *= (0.8 + decomposed.confidence * 0.2)

        # Sort by adjusted score
        results.sort(key=lambda r: -r.score)

        return results


# =============================================================================
# Convenience Functions
# =============================================================================

_decomposer = None


def get_decomposer() -> QueryDecomposer:
    """Get singleton decomposer instance."""
    global _decomposer
    if _decomposer is None:
        _decomposer = QueryDecomposer()
    return _decomposer


def is_complex_query(query: str) -> bool:
    """Check if a query should be decomposed."""
    return get_decomposer().is_complex_query(query)


def decompose(query: str) -> DecomposedQuery:
    """Decompose a query into sub-queries."""
    return get_decomposer().decompose(query)


def search_with_decomposition(
    query: str,
    indexer: 'CodeIndexer',
    project_id: Optional[str] = None,
    symbol_type: Optional[str] = None,
    limit: int = 10
) -> List[Tuple['CodeSymbol', float]]:
    """
    Search with automatic query decomposition.

    This is the main entry point - it automatically detects complex queries
    and decomposes them for better results.
    """
    decomposer = get_decomposer()

    if decomposer.is_complex_query(query):
        return decomposer.search_decomposed(
            query, indexer, project_id, symbol_type, limit
        )
    else:
        return indexer.search(query, project_id, symbol_type, limit)


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    decomposer = QueryDecomposer()

    if len(sys.argv) < 2:
        print("SAM Query Decomposer - Phase 2.2.4")
        print("-" * 40)
        print("\nUsage:")
        print("  python query_decomposer.py check <query>   - Check if query is complex")
        print("  python query_decomposer.py decompose <query> - Decompose a query")
        print("  python query_decomposer.py search <query>  - Search with decomposition")
        print("\nExamples:")
        print('  python query_decomposer.py check "How does memory work and where is it stored?"')
        print('  python query_decomposer.py decompose "Find Python files handling auth and logging"')
        sys.exit(0)

    cmd = sys.argv[1]
    query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "check":
        if not query:
            print("Error: Please provide a query")
            sys.exit(1)

        is_complex = decomposer.is_complex_query(query)
        print(f"Query: {query}")
        print(f"Is complex: {is_complex}")

    elif cmd == "decompose":
        if not query:
            print("Error: Please provide a query")
            sys.exit(1)

        result = decomposer.decompose(query)
        print(f"Original: {result.original}")
        print(f"Type: {result.query_type}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"\nSub-queries ({len(result.sub_queries)}):")
        for i, sq in enumerate(result.sub_queries, 1):
            print(f"  {i}. {sq}")

    elif cmd == "search":
        if not query:
            print("Error: Please provide a query")
            sys.exit(1)

        # Import and use code_indexer
        try:
            from code_indexer import get_indexer
            indexer = get_indexer()

            print(f"Query: {query}")
            print("-" * 40)

            # First show decomposition
            decomposed = decomposer.decompose(query)
            if len(decomposed.sub_queries) > 1:
                print(f"Decomposed into {len(decomposed.sub_queries)} sub-queries:")
                for sq in decomposed.sub_queries:
                    print(f"  - {sq}")
                print()

            # Then search
            results = search_with_decomposition(query, indexer)

            print(f"Found {len(results)} results:\n")
            for symbol, score in results:
                print(f"  [{symbol.symbol_type}] {symbol.name} (score: {score:.3f})")
                print(f"      {symbol.signature}")
                print(f"      @ {symbol.file_path}:{symbol.line_number}")
                print()

        except ImportError:
            print("Error: code_indexer not available. Run from sam_brain directory.")
            sys.exit(1)

    elif cmd == "test":
        # Run test cases
        test_queries = [
            "How does the memory system work and where is it stored?",
            "Find all Python files that handle authentication and logging",
            "What is the database schema for users",
            "Search for functions that create, update, or delete records",
            "voice pipeline processing and emotion detection",
            "api endpoint, request handler, response format",
            "How does MLX inference work? What about embeddings?",
            "simple search query",
        ]

        print("Query Decomposer Test Cases")
        print("=" * 60)

        for query in test_queries:
            print(f"\nQuery: {query}")
            print(f"  Is complex: {decomposer.is_complex_query(query)}")

            if decomposer.is_complex_query(query):
                result = decomposer.decompose(query)
                print(f"  Type: {result.query_type}")
                print(f"  Confidence: {result.confidence:.2f}")
                print(f"  Sub-queries:")
                for sq in result.sub_queries:
                    print(f"    - {sq}")

    else:
        print(f"Unknown command: {cmd}")
        print("Use: check, decompose, search, or test")
