"""
Relevance Scorer for SAM RAG System (Phase 2.2.5)

Provides intelligent reranking of search results from code_indexer and doc_indexer.
Designed to be lightweight and MLX-compatible for 8GB RAM constraint.

Scoring factors:
1. Semantic similarity (from embeddings - already computed)
2. Keyword match boost (exact and fuzzy matching)
3. Symbol type priority (class > function > variable)
4. Documentation quality (has docstring, docstring length)
5. Recency (recently modified files score higher)
6. Name relevance (query terms in symbol name)

Usage:
    from remember.relevance_scorer import RelevanceScorer, get_relevance_scorer

    scorer = get_relevance_scorer()
    reranked = scorer.rerank(query, results, limit=10)

    # Or score a single result
    score = scorer.score_single(query, result)
"""

import re
import time
import os
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from datetime import datetime

# Optional MLX embeddings for semantic scoring
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import mlx_embeddings
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ScoringWeights:
    """Configurable weights for different scoring factors."""
    semantic: float = 0.35      # Base semantic similarity (from embeddings)
    keyword: float = 0.20       # Keyword match boost
    symbol_type: float = 0.15   # Symbol type priority
    doc_quality: float = 0.10   # Documentation quality
    name_match: float = 0.10    # Query terms in symbol name
    recency: float = 0.10       # Recently modified files

    def normalize(self) -> "ScoringWeights":
        """Ensure weights sum to 1.0."""
        total = (self.semantic + self.keyword + self.symbol_type +
                 self.doc_quality + self.name_match + self.recency)
        if total > 0:
            return ScoringWeights(
                semantic=self.semantic / total,
                keyword=self.keyword / total,
                symbol_type=self.symbol_type / total,
                doc_quality=self.doc_quality / total,
                name_match=self.name_match / total,
                recency=self.recency / total
            )
        return self


# Symbol type priorities (higher = more important)
SYMBOL_TYPE_PRIORITY = {
    # Code symbols
    "class": 1.0,
    "protocol": 1.0,
    "trait": 1.0,
    "interface": 0.95,
    "struct": 0.9,
    "enum": 0.85,
    "function": 0.8,
    "method": 0.75,
    "module": 0.7,
    "type": 0.65,
    "import": 0.3,
    # Documentation types
    "markdown": 0.6,
    "docstring": 0.7,
    "comment": 0.4,
    "block_comment": 0.5,
}


# =============================================================================
# Result Types (generic to work with both code_indexer and doc_indexer)
# =============================================================================

@dataclass
class ScoredResult:
    """A search result with detailed scoring breakdown."""
    id: str
    name: str
    type: str  # symbol_type or doc_type
    content: str
    file_path: str
    line_number: int

    # Scores
    final_score: float = 0.0
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    type_score: float = 0.0
    doc_quality_score: float = 0.0
    name_score: float = 0.0
    recency_score: float = 0.0

    # Optional metadata
    docstring: Optional[str] = None
    signature: Optional[str] = None
    project_id: Optional[str] = None
    section_title: Optional[str] = None
    mtime: Optional[float] = None
    original_score: float = 0.0  # Score from the indexer

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "content": self.content[:200] if self.content else "",
            "file_path": self.file_path,
            "line_number": self.line_number,
            "final_score": round(self.final_score, 4),
            "scores": {
                "semantic": round(self.semantic_score, 4),
                "keyword": round(self.keyword_score, 4),
                "type": round(self.type_score, 4),
                "doc_quality": round(self.doc_quality_score, 4),
                "name": round(self.name_score, 4),
                "recency": round(self.recency_score, 4),
            },
            "signature": self.signature,
            "docstring": self.docstring[:100] if self.docstring else None,
        }


# =============================================================================
# Keyword Matcher
# =============================================================================

class KeywordMatcher:
    """
    Efficient keyword matching with stemming and fuzzy matching.
    Lightweight alternative to full text search engines.
    """

    # Common programming stopwords to ignore
    STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "under",
        "again", "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
        "very", "just", "but", "and", "or", "if", "this", "that", "these",
        "those", "what", "which", "who", "whom", "i", "me", "my", "we", "our",
        "you", "your", "he", "him", "his", "she", "her", "it", "its", "they",
        "them", "their"
    }

    # Simple stemming suffixes
    STEM_SUFFIXES = ["ing", "ed", "ly", "er", "est", "ness", "ment", "tion", "sion", "es", "s"]

    def __init__(self):
        self._cache: Dict[str, List[str]] = {}

    def tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text."""
        if not text:
            return []

        cache_key = text[:200]  # Limit cache key length
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract tokens preserving case first (for camelCase splitting)
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)

        # Split camelCase and snake_case
        expanded = []
        for token in tokens:
            # camelCase/PascalCase: searchDocuments -> search, Documents
            # Split on transitions from lowercase to uppercase
            camel_parts = re.split(r'(?<=[a-z])(?=[A-Z])', token)
            if len(camel_parts) > 1:
                expanded.extend([p.lower() for p in camel_parts])

            # Also split consecutive caps: HTTPResponse -> HTTP, Response
            upper_parts = re.split(r'(?<=[A-Z])(?=[A-Z][a-z])', token)
            if len(upper_parts) > 1:
                expanded.extend([p.lower() for p in upper_parts])

            # snake_case: search_documents -> search, documents
            if '_' in token:
                snake_parts = [p.lower() for p in token.split('_') if p]
                if len(snake_parts) > 1:
                    expanded.extend(snake_parts)

            # Always include the original token (lowercased)
            expanded.append(token.lower())

        # Remove stopwords and short tokens
        filtered = [t for t in expanded if t not in self.STOPWORDS and len(t) > 1]

        # Apply simple stemming
        stemmed = [self._stem(t) for t in filtered]

        # Deduplicate while preserving order
        seen = set()
        result = []
        for t in stemmed:
            if t not in seen:
                seen.add(t)
                result.append(t)

        self._cache[cache_key] = result
        return result

    def _stem(self, word: str) -> str:
        """Simple suffix-based stemming."""
        for suffix in self.STEM_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        return word

    def match_score(self, query: str, text: str) -> float:
        """
        Calculate keyword match score between query and text.

        Returns:
            Score from 0.0 to 1.0
        """
        query_tokens = set(self.tokenize(query))
        text_tokens = set(self.tokenize(text))

        if not query_tokens or not text_tokens:
            return 0.0

        # Exact matches
        exact_matches = len(query_tokens & text_tokens)

        # Fuzzy matches (prefix matching)
        fuzzy_matches = 0
        for qt in query_tokens:
            for tt in text_tokens:
                if qt != tt and (tt.startswith(qt) or qt.startswith(tt)):
                    fuzzy_matches += 0.5

        total_matches = exact_matches + fuzzy_matches
        max_possible = len(query_tokens)

        return min(1.0, total_matches / max_possible)

    def exact_match_positions(self, query: str, text: str) -> List[int]:
        """Find positions of exact query matches in text."""
        positions = []
        query_lower = query.lower()
        text_lower = text.lower()

        start = 0
        while True:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        return positions


# =============================================================================
# MLX Cross-Encoder (Lightweight)
# =============================================================================

class MLXCrossEncoder:
    """
    Lightweight cross-encoder scoring using MLX.

    Instead of a full cross-encoder model (too heavy for 8GB RAM),
    we use the existing MLX embeddings to compute query-document similarity
    with additional context-aware adjustments.
    """

    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._embedding_cache: Dict[str, Any] = {}
        self._cache_limit = 500

    def _ensure_loaded(self) -> bool:
        """Lazy load the embedding model."""
        if self._model is not None:
            return True

        if not MLX_AVAILABLE:
            return False

        try:
            self._model, self._tokenizer = mlx_embeddings.load(self.EMBEDDING_MODEL)
            return True
        except Exception as e:
            print(f"MLX embedding load failed: {e}")
            return False

    def _get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding with caching."""
        if not NUMPY_AVAILABLE:
            return None

        # Check cache
        cache_key = hash(text[:500])
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self._ensure_loaded():
            return None

        try:
            output = mlx_embeddings.generate(
                self._model,
                self._tokenizer,
                text[:2000]
            )
            embedding = np.array(output.text_embeds[0])

            # Cache management
            if len(self._embedding_cache) >= self._cache_limit:
                # Remove oldest entries (simple FIFO)
                keys = list(self._embedding_cache.keys())
                for k in keys[:100]:
                    del self._embedding_cache[k]

            self._embedding_cache[cache_key] = embedding
            return embedding

        except Exception as e:
            print(f"MLX embedding error: {e}")
            return None

    def score(self, query: str, document: str) -> float:
        """
        Compute cross-encoder style score between query and document.

        This is a lightweight approximation using bi-encoder embeddings
        with query-document concatenation for context awareness.
        """
        if not NUMPY_AVAILABLE:
            return 0.5  # Default score

        # Get individual embeddings
        query_emb = self._get_embedding(query)
        doc_emb = self._get_embedding(document[:1000])

        if query_emb is None or doc_emb is None:
            return 0.5

        # Cosine similarity
        similarity = float(np.dot(query_emb, doc_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(doc_emb) + 1e-8
        ))

        # Normalize to 0-1 range (cosine similarity is -1 to 1)
        return (similarity + 1) / 2

    def batch_score(self, query: str, documents: List[str]) -> List[float]:
        """Score multiple documents against a query."""
        return [self.score(query, doc) for doc in documents]


# =============================================================================
# Main Relevance Scorer
# =============================================================================

class RelevanceScorer:
    """
    Multi-factor relevance scorer for search results.

    Combines semantic similarity, keyword matching, symbol type priority,
    documentation quality, name relevance, and recency for comprehensive
    relevance scoring.
    """

    def __init__(self,
                 weights: Optional[ScoringWeights] = None,
                 use_mlx_scorer: bool = True,
                 recency_decay_days: float = 30.0):
        """
        Initialize the relevance scorer.

        Args:
            weights: Custom scoring weights (default: balanced weights)
            use_mlx_scorer: Use MLX-based semantic scoring
            recency_decay_days: Days after which recency score decays to 0.5
        """
        self.weights = (weights or ScoringWeights()).normalize()
        self.keyword_matcher = KeywordMatcher()
        self.mlx_scorer = MLXCrossEncoder() if use_mlx_scorer else None
        self.recency_decay_days = recency_decay_days
        self._now = time.time()

    def score_single(self, query: str, result: Any) -> ScoredResult:
        """
        Score a single search result.

        Args:
            query: The search query
            result: A CodeSymbol, DocEntity, or dict-like result

        Returns:
            ScoredResult with detailed scoring breakdown
        """
        # Normalize result to dict-like access
        r = self._normalize_result(result)

        # Calculate individual scores
        semantic_score = self._score_semantic(query, r)
        keyword_score = self._score_keyword(query, r)
        type_score = self._score_symbol_type(r)
        doc_quality_score = self._score_doc_quality(r)
        name_score = self._score_name_match(query, r)
        recency_score = self._score_recency(r)

        # Compute weighted final score
        final_score = (
            semantic_score * self.weights.semantic +
            keyword_score * self.weights.keyword +
            type_score * self.weights.symbol_type +
            doc_quality_score * self.weights.doc_quality +
            name_score * self.weights.name_match +
            recency_score * self.weights.recency
        )

        return ScoredResult(
            id=r.get("id", ""),
            name=r.get("name", ""),
            type=r.get("type", r.get("symbol_type", r.get("doc_type", "unknown"))),
            content=r.get("content", ""),
            file_path=r.get("file_path", ""),
            line_number=r.get("line_number", 0),
            final_score=final_score,
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            type_score=type_score,
            doc_quality_score=doc_quality_score,
            name_score=name_score,
            recency_score=recency_score,
            docstring=r.get("docstring"),
            signature=r.get("signature"),
            project_id=r.get("project_id"),
            section_title=r.get("section_title"),
            mtime=r.get("mtime"),
            original_score=r.get("original_score", 0.0)
        )

    def rerank(self, query: str, results: List[Any], limit: int = 10) -> List[ScoredResult]:
        """
        Rerank search results using multi-factor scoring.

        Args:
            query: The search query
            results: List of search results (CodeSymbol, DocEntity, or dicts)
            limit: Maximum number of results to return

        Returns:
            Sorted list of ScoredResult objects
        """
        if not results:
            return []

        # Score all results
        scored_results = [self.score_single(query, r) for r in results]

        # Sort by final score (descending)
        scored_results.sort(key=lambda x: x.final_score, reverse=True)

        return scored_results[:limit]

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """Normalize different result types to a common dict format."""
        if isinstance(result, dict):
            return result

        # Handle tuples (result, score) from code_indexer
        if isinstance(result, tuple) and len(result) == 2:
            result, score = result
            r = self._normalize_result(result)
            r["original_score"] = score
            return r

        # Handle dataclass-like objects
        r = {}
        for attr in ["id", "name", "type", "symbol_type", "doc_type", "content",
                     "file_path", "line_number", "docstring", "signature",
                     "project_id", "section_title", "mtime"]:
            if hasattr(result, attr):
                r[attr] = getattr(result, attr)

        # Normalize type field
        if "symbol_type" in r and "type" not in r:
            r["type"] = r["symbol_type"]
        elif "doc_type" in r and "type" not in r:
            r["type"] = r["doc_type"]

        return r

    def _score_semantic(self, query: str, result: Dict) -> float:
        """Score based on semantic similarity."""
        # If result already has a score from embeddings, use it
        if "original_score" in result and result["original_score"] > 0:
            return min(1.0, result["original_score"])

        # Use MLX scorer if available
        if self.mlx_scorer:
            content = result.get("content", "")
            if content:
                return self.mlx_scorer.score(query, content)

        # Fallback to keyword-based approximation
        return self._score_keyword(query, result) * 0.8

    def _score_keyword(self, query: str, result: Dict) -> float:
        """Score based on keyword matching."""
        # Combine searchable fields
        searchable = " ".join(filter(None, [
            result.get("name", ""),
            result.get("content", ""),
            result.get("docstring", ""),
            result.get("signature", ""),
            result.get("section_title", "")
        ]))

        return self.keyword_matcher.match_score(query, searchable)

    def _score_symbol_type(self, result: Dict) -> float:
        """Score based on symbol type priority."""
        symbol_type = result.get("type", result.get("symbol_type",
                                  result.get("doc_type", "unknown")))
        return SYMBOL_TYPE_PRIORITY.get(symbol_type.lower(), 0.5)

    def _score_doc_quality(self, result: Dict) -> float:
        """Score based on documentation quality."""
        score = 0.3  # Base score

        docstring = result.get("docstring", "")
        if docstring:
            # Has docstring
            score += 0.3

            # Length bonus
            length = len(docstring)
            if length > 50:
                score += 0.1
            if length > 100:
                score += 0.1
            if length > 200:
                score += 0.1

            # Contains useful patterns
            if "@param" in docstring.lower() or "args:" in docstring.lower():
                score += 0.05
            if "@return" in docstring.lower() or "returns:" in docstring.lower():
                score += 0.05

        # Check for type hints in signature
        signature = result.get("signature", "")
        if signature:
            if "->" in signature:  # Return type annotation
                score += 0.05
            if ":" in signature and "def" in signature:  # Parameter annotations
                score += 0.05

        return min(1.0, score)

    def _score_name_match(self, query: str, result: Dict) -> float:
        """Score based on query terms appearing in the symbol name."""
        name = result.get("name", "")
        if not name:
            return 0.0

        # Direct match boost
        query_lower = query.lower()
        name_lower = name.lower()

        if query_lower == name_lower:
            return 1.0

        if query_lower in name_lower:
            return 0.8

        if name_lower in query_lower:
            return 0.6

        # Token overlap
        query_tokens = set(self.keyword_matcher.tokenize(query))
        name_tokens = set(self.keyword_matcher.tokenize(name))

        if not query_tokens or not name_tokens:
            return 0.0

        overlap = len(query_tokens & name_tokens)
        return min(1.0, overlap / len(query_tokens))

    def _score_recency(self, result: Dict) -> float:
        """Score based on file modification time."""
        mtime = result.get("mtime")

        if not mtime:
            # Try to get mtime from file
            file_path = result.get("file_path", "")
            if file_path and os.path.exists(file_path):
                try:
                    mtime = os.path.getmtime(file_path)
                except OSError:
                    pass

        if not mtime:
            return 0.5  # Neutral score if unknown

        # Calculate age in days
        age_seconds = self._now - mtime
        age_days = age_seconds / 86400

        # Exponential decay with configurable half-life
        decay_factor = 0.5 ** (age_days / self.recency_decay_days)

        # Clamp to reasonable range
        return max(0.1, min(1.0, decay_factor))


# =============================================================================
# Specialized Scorers
# =============================================================================

class CodeRelevanceScorer(RelevanceScorer):
    """
    Specialized scorer for code search results.
    Emphasizes symbol type and documentation quality.
    """

    def __init__(self):
        weights = ScoringWeights(
            semantic=0.30,
            keyword=0.20,
            symbol_type=0.20,  # Higher for code
            doc_quality=0.15,  # Higher for code
            name_match=0.10,
            recency=0.05
        )
        super().__init__(weights=weights)


class DocRelevanceScorer(RelevanceScorer):
    """
    Specialized scorer for documentation search results.
    Emphasizes semantic similarity and keyword matching.
    """

    def __init__(self):
        weights = ScoringWeights(
            semantic=0.40,  # Higher for docs
            keyword=0.25,  # Higher for docs
            symbol_type=0.05,
            doc_quality=0.15,
            name_match=0.10,
            recency=0.05
        )
        super().__init__(weights=weights)


# =============================================================================
# Integration Helpers
# =============================================================================

def rerank_code_results(query: str,
                        results: List[Tuple[Any, float]],
                        limit: int = 10) -> List[ScoredResult]:
    """
    Convenience function to rerank code_indexer search results.

    Args:
        query: The search query
        results: List of (CodeSymbol, score) tuples from code_indexer.search()
        limit: Maximum results to return

    Returns:
        Reranked list of ScoredResult objects
    """
    scorer = CodeRelevanceScorer()
    return scorer.rerank(query, results, limit)


def rerank_doc_results(query: str,
                       results: List[Tuple[Any, float]],
                       limit: int = 10) -> List[ScoredResult]:
    """
    Convenience function to rerank doc_indexer search results.

    Args:
        query: The search query
        results: List of (DocEntity, score) tuples from doc_indexer.search_docs()
        limit: Maximum results to return

    Returns:
        Reranked list of ScoredResult objects
    """
    scorer = DocRelevanceScorer()
    return scorer.rerank(query, results, limit)


def rerank_mixed_results(query: str,
                         code_results: List[Tuple[Any, float]],
                         doc_results: List[Tuple[Any, float]],
                         limit: int = 10,
                         code_weight: float = 0.6) -> List[ScoredResult]:
    """
    Rerank combined results from both code and doc indexers.

    Args:
        query: The search query
        code_results: Results from code_indexer
        doc_results: Results from doc_indexer
        limit: Maximum results to return
        code_weight: Weight for code results (0-1, rest goes to docs)

    Returns:
        Merged and reranked list of ScoredResult objects
    """
    # Score separately
    code_scored = rerank_code_results(query, code_results, limit=limit * 2)
    doc_scored = rerank_doc_results(query, doc_results, limit=limit * 2)

    # Adjust scores based on source weights
    for r in code_scored:
        r.final_score *= code_weight
    for r in doc_scored:
        r.final_score *= (1 - code_weight)

    # Merge and sort
    all_results = code_scored + doc_scored
    all_results.sort(key=lambda x: x.final_score, reverse=True)

    return all_results[:limit]


# =============================================================================
# Singleton
# =============================================================================

_relevance_scorer = None
_code_scorer = None
_doc_scorer = None


def get_relevance_scorer() -> RelevanceScorer:
    """Get singleton general relevance scorer."""
    global _relevance_scorer
    if _relevance_scorer is None:
        _relevance_scorer = RelevanceScorer()
    return _relevance_scorer


def get_code_scorer() -> CodeRelevanceScorer:
    """Get singleton code relevance scorer."""
    global _code_scorer
    if _code_scorer is None:
        _code_scorer = CodeRelevanceScorer()
    return _code_scorer


def get_doc_scorer() -> DocRelevanceScorer:
    """Get singleton doc relevance scorer."""
    global _doc_scorer
    if _doc_scorer is None:
        _doc_scorer = DocRelevanceScorer()
    return _doc_scorer


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="SAM Relevance Scorer (Phase 2.2.5)")
    parser.add_argument("command", choices=["demo", "score", "weights"])
    parser.add_argument("--query", "-q", default="", help="Search query")
    parser.add_argument("--text", "-t", default="", help="Text to score")
    args = parser.parse_args()

    if args.command == "demo":
        # Demo with mock results
        print("Relevance Scorer Demo")
        print("=" * 50)

        scorer = RelevanceScorer()

        mock_results = [
            {
                "id": "1",
                "name": "search_documents",
                "type": "function",
                "content": "def search_documents(query: str) -> List[Document]: ...",
                "file_path": "/path/to/file.py",
                "line_number": 42,
                "docstring": "Search for documents matching the query.",
                "signature": "def search_documents(query: str) -> List[Document]",
                "original_score": 0.85
            },
            {
                "id": "2",
                "name": "DocumentStore",
                "type": "class",
                "content": "class DocumentStore: A store for documents with full-text search.",
                "file_path": "/path/to/store.py",
                "line_number": 10,
                "docstring": "A store for documents with full-text search and semantic retrieval.",
                "signature": "class DocumentStore",
                "original_score": 0.75
            },
            {
                "id": "3",
                "name": "utils",
                "type": "module",
                "content": "Various utility functions for text processing.",
                "file_path": "/path/to/utils.py",
                "line_number": 1,
                "docstring": None,
                "signature": "Module: utils.py",
                "original_score": 0.5
            }
        ]

        query = "search documents semantic"
        print(f"\nQuery: '{query}'")
        print(f"\nOriginal order (by embedding score):")
        for r in mock_results:
            print(f"  {r['name']}: {r['original_score']}")

        reranked = scorer.rerank(query, mock_results, limit=10)
        print(f"\nReranked order:")
        for r in reranked:
            print(f"  {r.name}: {r.final_score:.4f}")
            print(f"    Semantic: {r.semantic_score:.4f}, Keyword: {r.keyword_score:.4f}")
            print(f"    Type: {r.type_score:.4f}, DocQuality: {r.doc_quality_score:.4f}")
            print(f"    Name: {r.name_score:.4f}, Recency: {r.recency_score:.4f}")

    elif args.command == "score":
        if not args.query or not args.text:
            print("Please provide --query and --text")
        else:
            scorer = RelevanceScorer()
            result = scorer.score_single(args.query, {
                "id": "test",
                "name": "test",
                "type": "function",
                "content": args.text,
                "file_path": "test.py",
                "line_number": 1
            })
            print(json.dumps(result.to_dict(), indent=2))

    elif args.command == "weights":
        weights = ScoringWeights()
        print("Default Scoring Weights:")
        print(f"  Semantic:     {weights.semantic:.2f}")
        print(f"  Keyword:      {weights.keyword:.2f}")
        print(f"  Symbol Type:  {weights.symbol_type:.2f}")
        print(f"  Doc Quality:  {weights.doc_quality:.2f}")
        print(f"  Name Match:   {weights.name_match:.2f}")
        print(f"  Recency:      {weights.recency:.2f}")
        print(f"\nCode Scorer Weights:")
        code_weights = CodeRelevanceScorer().weights
        print(f"  Semantic:     {code_weights.semantic:.2f}")
        print(f"  Symbol Type:  {code_weights.symbol_type:.2f}")
        print(f"\nDoc Scorer Weights:")
        doc_weights = DocRelevanceScorer().weights
        print(f"  Semantic:     {doc_weights.semantic:.2f}")
        print(f"  Keyword:      {doc_weights.keyword:.2f}")
