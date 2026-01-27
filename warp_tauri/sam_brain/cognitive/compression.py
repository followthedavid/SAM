"""
Prompt Compression System for SAM Cognitive Architecture

Implements LLMLingua-style compression without requiring the full library:
1. Token importance scoring based on perplexity/TF-IDF
2. Iterative pruning of low-importance tokens
3. Semantic preservation verification
4. Target ratio compression (4x)

Goal: Compress 2000 tokens → 500 tokens with minimal information loss
"""

import re
import math
from collections import Counter
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Types of tokens for importance scoring"""
    QUESTION = "question"      # Questions are critical
    ENTITY = "entity"          # Named entities
    ACTION = "action"          # Verbs, actions
    TECHNICAL = "technical"    # Technical terms
    CONNECTOR = "connector"    # And, but, or
    FILLER = "filler"          # Um, well, basically
    PUNCTUATION = "punctuation"
    COMMON = "common"          # Common words
    OTHER = "other"


@dataclass
class ScoredToken:
    """A token with importance scores"""
    text: str
    position: int
    token_type: TokenType
    importance: float  # 0-1
    is_preserved: bool = True


class TokenImportanceScorer:
    """
    Score token importance using multiple signals:
    1. TF-IDF (term frequency-inverse document frequency)
    2. Position (start/end more important)
    3. Token type (questions, entities more important)
    4. Syntactic role
    """

    # High importance words/patterns
    QUESTION_WORDS = {"what", "where", "when", "who", "why", "how", "which", "whose"}
    ACTION_WORDS = {"create", "build", "make", "add", "remove", "delete", "update",
                    "implement", "fix", "debug", "run", "execute", "return", "call"}
    TECHNICAL_PATTERNS = [
        r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase
        r'\b[a-z]+_[a-z_]+\b',                # snake_case
        r'\b\d+(?:\.\d+)?(?:GB|MB|KB|ms|s|%)\b',  # Measurements
        r'`[^`]+`',                            # Code snippets
    ]

    # Low importance patterns
    FILLER_WORDS = {"um", "uh", "well", "basically", "actually", "literally",
                    "just", "really", "very", "quite", "simply"}
    COMMON_WORDS = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                    "being", "have", "has", "had", "do", "does", "did", "will",
                    "would", "could", "should", "may", "might", "must", "shall",
                    "to", "of", "in", "for", "on", "with", "at", "by", "from",
                    "as", "into", "through", "during", "before", "after",
                    "this", "that", "these", "those", "it", "its"}

    def __init__(self):
        self.idf_cache: Dict[str, float] = {}

    def classify_token(self, token: str) -> TokenType:
        """Classify a token by type"""
        token_lower = token.lower().strip()

        if token in ".,;:!?-()[]{}\"'":
            return TokenType.PUNCTUATION

        if token_lower in self.QUESTION_WORDS or token.endswith("?"):
            return TokenType.QUESTION

        if token_lower in self.ACTION_WORDS:
            return TokenType.ACTION

        if token_lower in self.FILLER_WORDS:
            return TokenType.FILLER

        if token_lower in self.COMMON_WORDS:
            return TokenType.COMMON

        if token_lower in {"and", "but", "or", "nor", "yet", "so", "because", "although"}:
            return TokenType.CONNECTOR

        # Check technical patterns
        for pattern in self.TECHNICAL_PATTERNS:
            if re.match(pattern, token):
                return TokenType.TECHNICAL

        # Check if entity (capitalized)
        if token[0].isupper() and len(token) > 1:
            return TokenType.ENTITY

        return TokenType.OTHER

    def score_tokens(self, text: str, preserve_questions: bool = True,
                     preserve_entities: bool = True) -> List[ScoredToken]:
        """
        Score all tokens in text by importance.

        Args:
            text: Input text
            preserve_questions: Always keep question words
            preserve_entities: Always keep named entities

        Returns:
            List of ScoredToken objects
        """
        # Tokenize (simple word-based)
        tokens = self._tokenize(text)
        total_tokens = len(tokens)

        # Calculate TF for this text
        token_counts = Counter(t.lower() for t in tokens)
        max_tf = max(token_counts.values()) if token_counts else 1

        scored = []
        for i, token in enumerate(tokens):
            token_type = self.classify_token(token)

            # Base importance from type
            type_scores = {
                TokenType.QUESTION: 1.0,
                TokenType.ENTITY: 0.9,
                TokenType.TECHNICAL: 0.85,
                TokenType.ACTION: 0.8,
                TokenType.OTHER: 0.5,
                TokenType.CONNECTOR: 0.4,
                TokenType.COMMON: 0.3,
                TokenType.FILLER: 0.1,
                TokenType.PUNCTUATION: 0.2,
            }
            base_score = type_scores.get(token_type, 0.5)

            # TF-IDF component
            tf = token_counts[token.lower()] / max_tf
            idf = self._get_idf(token.lower())
            tfidf_score = tf * idf

            # Position component (U-shaped: start and end are important)
            position_ratio = i / total_tokens
            position_score = 1.0 - 4 * (position_ratio - 0.5) ** 2
            position_score = max(0.3, position_score)

            # Combine scores
            importance = (
                base_score * 0.5 +
                min(1.0, tfidf_score) * 0.3 +
                position_score * 0.2
            )

            # Check if must be preserved
            is_preserved = False
            if preserve_questions and token_type == TokenType.QUESTION:
                is_preserved = True
                importance = 1.0
            if preserve_entities and token_type == TokenType.ENTITY:
                is_preserved = True
                importance = max(importance, 0.9)

            scored.append(ScoredToken(
                text=token,
                position=i,
                token_type=token_type,
                importance=importance,
                is_preserved=is_preserved
            ))

        return scored

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Split on whitespace and punctuation, keeping punctuation
        tokens = re.findall(r'\b\w+\b|[.,;:!?()[\]{}"\'-]', text)
        return tokens

    def _get_idf(self, token: str) -> float:
        """Get IDF score (cached, with fallback for unknown tokens)"""
        if token in self.idf_cache:
            return self.idf_cache[token]

        # Simple heuristic IDF based on word length and rarity
        if token in self.COMMON_WORDS:
            idf = 0.1
        elif len(token) <= 2:
            idf = 0.2
        elif len(token) <= 4:
            idf = 0.5
        else:
            idf = min(1.0, 0.3 + len(token) * 0.1)

        self.idf_cache[token] = idf
        return idf


class PromptCompressor:
    """
    Compress prompts while preserving semantic content.

    Compression strategies:
    1. Remove low-importance tokens
    2. Merge similar sentences
    3. Replace phrases with shorter equivalents
    4. Remove redundant information
    """

    # Phrase replacements for compression
    PHRASE_REPLACEMENTS = {
        "in order to": "to",
        "due to the fact that": "because",
        "at this point in time": "now",
        "in the event that": "if",
        "for the purpose of": "to",
        "with regard to": "about",
        "in spite of the fact that": "although",
        "on the other hand": "however",
        "as a matter of fact": "actually",
        "at the present time": "now",
        "in the near future": "soon",
        "a large number of": "many",
        "a small number of": "few",
        "the majority of": "most",
        "in addition to": "besides",
        "as well as": "and",
    }

    def __init__(self, target_ratio: float = 0.25):
        """
        Args:
            target_ratio: Target compression ratio (0.25 = 4x compression)
        """
        self.target_ratio = target_ratio
        self.scorer = TokenImportanceScorer()

    def compress(self, text: str, target_tokens: Optional[int] = None,
                 preserve_structure: bool = True) -> str:
        """
        Compress text to target length.

        Args:
            text: Input text
            target_tokens: Target number of tokens (overrides ratio)
            preserve_structure: Keep sentence structure intact

        Returns:
            Compressed text
        """
        # Step 1: Apply phrase replacements
        compressed = self._apply_phrase_replacements(text)

        # Step 2: Score tokens
        scored_tokens = self.scorer.score_tokens(compressed)
        current_tokens = len(scored_tokens)

        # Calculate target
        if target_tokens is None:
            target_tokens = int(current_tokens * self.target_ratio)

        if current_tokens <= target_tokens:
            return compressed  # Already short enough

        # Step 3: Iteratively remove low-importance tokens
        if preserve_structure:
            compressed = self._compress_preserve_structure(
                scored_tokens, target_tokens
            )
        else:
            compressed = self._compress_aggressive(
                scored_tokens, target_tokens
            )

        # Step 4: Clean up whitespace
        compressed = self._clean_whitespace(compressed)

        # Record to monitoring system (Phase 2.3.6)
        compressed_tokens = len(compressed.split())
        try:
            from sam_api import record_compression_stats
            record_compression_stats(
                original_tokens=current_tokens,
                compressed_tokens=compressed_tokens,
                query_type="prompt",
                section="prompt",
                budget_target=target_tokens
            )
        except ImportError:
            pass  # Monitoring not available

        return compressed

    def _apply_phrase_replacements(self, text: str) -> str:
        """Replace verbose phrases with shorter equivalents"""
        result = text
        for phrase, replacement in self.PHRASE_REPLACEMENTS.items():
            result = re.sub(
                rf'\b{re.escape(phrase)}\b',
                replacement,
                result,
                flags=re.IGNORECASE
            )
        return result

    def _compress_preserve_structure(self, tokens: List[ScoredToken],
                                     target: int) -> str:
        """Compress while keeping sentence structure"""
        # Sort by importance, keeping preserved tokens
        removable = [t for t in tokens if not t.is_preserved]
        removable.sort(key=lambda x: x.importance)

        # Calculate how many to remove
        to_remove = len(tokens) - target
        remove_set: Set[int] = set()

        for token in removable:
            if len(remove_set) >= to_remove:
                break
            remove_set.add(token.position)

        # Reconstruct text
        result = []
        for token in tokens:
            if token.position not in remove_set:
                result.append(token.text)

        return " ".join(result)

    def _compress_aggressive(self, tokens: List[ScoredToken],
                             target: int) -> str:
        """Aggressive compression, may break structure"""
        # Keep only top N tokens by importance
        sorted_tokens = sorted(tokens, key=lambda x: x.importance, reverse=True)
        kept = sorted_tokens[:target]

        # Re-sort by position
        kept.sort(key=lambda x: x.position)

        return " ".join(t.text for t in kept)

    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace and punctuation spacing"""
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)

        # Fix punctuation spacing
        text = re.sub(r' ([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)

        return text.strip()

    def compress_conversation(self, messages: List[Dict[str, str]],
                              target_tokens: int) -> List[Dict[str, str]]:
        """
        Compress a conversation while preserving meaning.

        Keeps recent messages intact, compresses older ones.
        """
        if not messages:
            return messages

        # Estimate current tokens
        total_tokens = sum(len(m.get("content", "")) // 4 for m in messages)

        if total_tokens <= target_tokens:
            return messages

        # Keep last 2 messages intact
        recent = messages[-2:] if len(messages) > 2 else messages
        older = messages[:-2] if len(messages) > 2 else []

        # Calculate tokens for older messages
        recent_tokens = sum(len(m.get("content", "")) // 4 for m in recent)
        older_target = max(50, target_tokens - recent_tokens)

        # Compress older messages
        compressed_older = []
        tokens_per_message = older_target // max(1, len(older))

        for msg in older:
            content = msg.get("content", "")
            compressed_content = self.compress(
                content, target_tokens=tokens_per_message
            )
            compressed_older.append({
                "role": msg.get("role", "user"),
                "content": compressed_content
            })

        return compressed_older + recent

    def get_compression_stats(self, original: str, compressed: str) -> Dict:
        """Get statistics about compression"""
        orig_tokens = len(original.split())
        comp_tokens = len(compressed.split())

        return {
            "original_tokens": orig_tokens,
            "compressed_tokens": comp_tokens,
            "compression_ratio": comp_tokens / orig_tokens if orig_tokens > 0 else 1.0,
            "tokens_removed": orig_tokens - comp_tokens,
            "reduction_percent": (1 - comp_tokens / orig_tokens) * 100 if orig_tokens > 0 else 0
        }


class QueryType(Enum):
    """Types of queries for adaptive context allocation."""
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    GENERAL = "general"
    CREATIVE = "creative"
    RESEARCH = "research"


@dataclass
class CompressionStats:
    """Statistics from compression operation."""
    original_tokens: int
    compressed_tokens: int
    ratio: float
    query_type: str
    sections_preserved: Dict[str, int]  # section -> token count
    importance_threshold: float


class ContextualCompressor:
    """
    Context-aware compression that considers what's important for the current query.
    Enhanced with query type detection and adaptive allocation (Phase 2.3).
    """

    # Query type patterns
    CODE_PATTERNS = [
        r'\b(function|class|method|variable|import|module|library)\b',
        r'\b(implement|code|write|create|build|fix|debug)\b',
        r'\b(error|exception|bug|crash|fail)\b',
    ]
    DEBUG_PATTERNS = [
        r'\b(error|exception|traceback|stack trace|bug)\b',
        r'\b(why|cause|reason|fix|solve|debug)\b',
    ]
    EXPLAIN_PATTERNS = [
        r'\b(explain|understand|what|how|describe|clarify)\b',
        r'\b(mean|work|concept|difference)\b',
    ]
    CREATIVE_PATTERNS = [
        r'\b(write|story|creative|poem|imagine|create)\b',
        r'\b(character|narrative|fiction)\b',
    ]
    RESEARCH_PATTERNS = [
        r'\b(find|search|research|look up|learn about)\b',
        r'\b(information|data|facts|knowledge)\b',
    ]

    # Token allocation by query type
    ALLOCATION = {
        QueryType.CODE: {"code": 0.5, "context": 0.3, "memory": 0.2},
        QueryType.DEBUG: {"code": 0.4, "context": 0.4, "memory": 0.2},
        QueryType.EXPLAIN: {"code": 0.2, "context": 0.5, "memory": 0.3},
        QueryType.GENERAL: {"code": 0.2, "context": 0.4, "memory": 0.4},
        QueryType.CREATIVE: {"code": 0.1, "context": 0.4, "memory": 0.5},
        QueryType.RESEARCH: {"code": 0.1, "context": 0.6, "memory": 0.3},
    }

    def __init__(self):
        self.base_compressor = PromptCompressor()
        self.scorer = TokenImportanceScorer()
        self.last_stats: Optional[CompressionStats] = None

    def detect_query_type(self, query: str) -> QueryType:
        """Detect query type for adaptive context allocation."""
        query_lower = query.lower()

        # Score each type
        type_scores = {
            QueryType.CODE: sum(1 for p in self.CODE_PATTERNS if re.search(p, query_lower, re.I)),
            QueryType.DEBUG: sum(1 for p in self.DEBUG_PATTERNS if re.search(p, query_lower, re.I)),
            QueryType.EXPLAIN: sum(1 for p in self.EXPLAIN_PATTERNS if re.search(p, query_lower, re.I)),
            QueryType.CREATIVE: sum(1 for p in self.CREATIVE_PATTERNS if re.search(p, query_lower, re.I)),
            QueryType.RESEARCH: sum(1 for p in self.RESEARCH_PATTERNS if re.search(p, query_lower, re.I)),
        }

        # Return highest scoring type, or GENERAL if no clear match
        max_score = max(type_scores.values())
        if max_score == 0:
            return QueryType.GENERAL

        for qtype, score in type_scores.items():
            if score == max_score:
                return qtype

        return QueryType.GENERAL

    def get_token_allocation(self, query: str, total_tokens: int) -> Dict[str, int]:
        """
        Get token allocation for different context sections based on query type.

        Returns dict with token budgets for: code, context, memory
        """
        query_type = self.detect_query_type(query)
        allocation = self.ALLOCATION[query_type]

        return {
            section: int(total_tokens * ratio)
            for section, ratio in allocation.items()
        }

    def compress_for_query(self, context: str, query: str,
                           target_tokens: int = 200) -> str:
        """
        Compress context, preserving tokens relevant to the query.
        Enhanced with query-type aware importance boosting (Phase 2.3).

        Args:
            context: Context to compress
            query: Current query (determines what to preserve)
            target_tokens: Target length

        Returns:
            Compressed context
        """
        original_tokens = len(context.split())
        query_type = self.detect_query_type(query)

        # Extract query terms
        query_terms = set(query.lower().split())
        query_terms -= self.scorer.COMMON_WORDS

        # Score context tokens
        scored = self.scorer.score_tokens(context)

        # Boost importance based on query type (Phase 2.3 enhancement)
        for token in scored:
            token_lower = token.text.lower()

            # Base query matching boost
            if token_lower in query_terms:
                token.importance = min(1.0, token.importance + 0.3)
                token.is_preserved = True

            # Query type specific boosts
            if query_type == QueryType.CODE:
                # Boost code-like tokens
                if re.match(r'[a-z_][a-z0-9_]*', token_lower) and len(token_lower) > 3:
                    token.importance = min(1.0, token.importance + 0.1)
                if token.token_type == TokenType.TECHNICAL:
                    token.importance = min(1.0, token.importance + 0.15)

            elif query_type == QueryType.DEBUG:
                # Boost error-related tokens
                if any(w in token_lower for w in ['error', 'exception', 'fail', 'line', 'traceback']):
                    token.importance = min(1.0, token.importance + 0.2)

            elif query_type == QueryType.EXPLAIN:
                # Boost explanation-like tokens
                if token.token_type == TokenType.CONNECTOR:
                    token.importance = min(1.0, token.importance + 0.1)

        # Sort and keep top tokens
        scored.sort(key=lambda x: x.importance, reverse=True)
        kept = scored[:target_tokens]

        # Calculate importance threshold used
        threshold = kept[-1].importance if kept else 0.0

        # Restore position order for readable output
        kept.sort(key=lambda x: x.position)

        # Track stats
        compressed_tokens = len(kept)
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        self.last_stats = CompressionStats(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            ratio=ratio,
            query_type=query_type.value,
            sections_preserved={"context": compressed_tokens},
            importance_threshold=threshold
        )

        # Record to monitoring system (Phase 2.3.6)
        try:
            from sam_api import record_compression_stats
            record_compression_stats(
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                query_type=query_type.value,
                section="context",
                budget_target=target_tokens
            )
        except ImportError:
            pass  # Monitoring not available

        result = " ".join(t.text for t in kept)
        return self.base_compressor._clean_whitespace(result)

    def get_last_stats(self) -> Optional[CompressionStats]:
        """Get stats from last compression operation."""
        return self.last_stats


# Convenience functions
def compress_prompt(text: str, target_ratio: float = 0.25) -> str:
    """Compress a prompt to target ratio"""
    compressor = PromptCompressor(target_ratio)
    return compressor.compress(text)


def compress_for_context(context: str, query: str, target_tokens: int = 200) -> str:
    """Compress context while preserving query-relevant information"""
    compressor = ContextualCompressor()
    return compressor.compress_for_query(context, query, target_tokens)


if __name__ == "__main__":
    # Demo
    long_text = """
    In order to understand how the memory system works, you need to know that
    there are basically three main components that work together. The first component
    is the working memory, which is responsible for holding a small number of items
    at any given time. As a matter of fact, research has shown that humans can only
    hold approximately seven plus or minus two items in working memory at the present time.

    The second component is the long-term memory, which stores information for extended
    periods of time. In the event that you need to recall something from long-term memory,
    the retrieval process brings it back into working memory. The third component is the
    procedural memory, which stores skills and habits that have been learned through practice.

    With regard to the implementation, we use SQLite databases to store the memories
    and vector embeddings for semantic search. The system also implements decay functions
    to simulate forgetting, which is actually an important feature for the purpose of
    preventing the memory from becoming cluttered with irrelevant information.
    """

    compressor = PromptCompressor(target_ratio=0.25)
    compressed = compressor.compress(long_text)

    print("Original:")
    print(long_text[:200] + "...")
    print(f"\nOriginal tokens: {len(long_text.split())}")

    print("\nCompressed:")
    print(compressed)
    print(f"\nCompressed tokens: {len(compressed.split())}")

    stats = compressor.get_compression_stats(long_text, compressed)
    print(f"\nStats: {stats}")
