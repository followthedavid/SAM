#!/usr/bin/env python3
"""
SAM Deduplication System - Removes duplicate training examples.

Detects duplicates using multiple methods:
- Exact hash matching (identical content)
- Near-duplicate detection (Jaccard similarity with MinHash)
- Semantic similarity (embedding-based)

Integrates with TrainingDataStore and data quality validation.
"""

import re
import hashlib
import json
import struct
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Iterator, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import unicodedata
import time


# MinHash configuration
DEFAULT_NUM_HASHES = 128  # Number of hash functions for MinHash
DEFAULT_SHINGLE_SIZE = 3  # N-gram size for shingling
DEFAULT_JACCARD_THRESHOLD = 0.8  # Similarity threshold for near-duplicates
DEFAULT_SEMANTIC_THRESHOLD = 0.9  # Cosine similarity threshold


@dataclass
class DuplicateGroup:
    """A group of examples that are duplicates of each other."""
    group_id: str
    detection_method: str  # "exact", "near_duplicate", "semantic"
    similarity_score: float
    examples: List[Dict] = field(default_factory=list)
    example_ids: List[str] = field(default_factory=list)
    representative_id: Optional[str] = None  # The best example to keep

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "detection_method": self.detection_method,
            "similarity_score": self.similarity_score,
            "example_count": len(self.examples),
            "example_ids": self.example_ids,
            "representative_id": self.representative_id
        }


@dataclass
class DeduplicationStats:
    """Statistics from a deduplication run."""
    total_examples: int = 0
    unique_examples: int = 0
    duplicate_groups: int = 0
    duplicates_removed: int = 0
    exact_duplicates: int = 0
    near_duplicates: int = 0
    semantic_duplicates: int = 0
    processing_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class MinHash:
    """
    MinHash implementation for efficient near-duplicate detection.

    MinHash approximates Jaccard similarity between sets using hash signatures,
    enabling O(1) similarity comparison instead of O(n) set intersection.
    """

    # Large prime for hash function (Mersenne prime 2^61 - 1)
    PRIME = (1 << 61) - 1
    MAX_HASH = (1 << 32) - 1

    def __init__(self, num_hashes: int = DEFAULT_NUM_HASHES, seed: int = 42):
        """
        Initialize MinHash with specified number of hash functions.

        Args:
            num_hashes: Number of hash functions to use (more = more accurate)
            seed: Random seed for reproducible hash functions
        """
        self.num_hashes = num_hashes
        self.seed = seed

        # Generate hash function coefficients (a, b) for h(x) = (ax + b) mod p
        import random
        rng = random.Random(seed)
        self.a_coeffs = [rng.randint(1, self.PRIME - 1) for _ in range(num_hashes)]
        self.b_coeffs = [rng.randint(0, self.PRIME - 1) for _ in range(num_hashes)]

    def _hash_shingle(self, shingle: str) -> int:
        """Convert a shingle to a hash value."""
        return int(hashlib.md5(shingle.encode()).hexdigest()[:8], 16)

    def compute_signature(self, shingles: Set[str]) -> List[int]:
        """
        Compute MinHash signature for a set of shingles.

        Args:
            shingles: Set of text shingles (n-grams)

        Returns:
            List of minimum hash values (the signature)
        """
        if not shingles:
            return [self.MAX_HASH] * self.num_hashes

        # Initialize with max values
        signature = [self.MAX_HASH] * self.num_hashes

        # For each shingle, update signature with minimum hash
        for shingle in shingles:
            shingle_hash = self._hash_shingle(shingle)

            for i in range(self.num_hashes):
                # Apply hash function: h_i(x) = (a_i * x + b_i) mod p
                hash_val = ((self.a_coeffs[i] * shingle_hash + self.b_coeffs[i]) % self.PRIME) % self.MAX_HASH
                signature[i] = min(signature[i], hash_val)

        return signature

    def estimate_jaccard(self, sig1: List[int], sig2: List[int]) -> float:
        """
        Estimate Jaccard similarity from two MinHash signatures.

        Args:
            sig1: First signature
            sig2: Second signature

        Returns:
            Estimated Jaccard similarity (0-1)
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)


class LSH:
    """
    Locality-Sensitive Hashing for efficient similar item lookup.

    Groups similar items into the same "buckets" with high probability,
    enabling O(1) average lookup for near-duplicates.
    """

    def __init__(self, num_hashes: int = DEFAULT_NUM_HASHES, bands: int = 16):
        """
        Initialize LSH index.

        Args:
            num_hashes: Number of hash values in MinHash signatures
            bands: Number of bands for LSH (more bands = higher recall, lower precision)
        """
        self.num_hashes = num_hashes
        self.bands = bands
        self.rows_per_band = num_hashes // bands

        # Hash tables for each band
        self.buckets: List[Dict[int, Set[str]]] = [defaultdict(set) for _ in range(bands)]

        # Store signatures for similarity computation
        self.signatures: Dict[str, List[int]] = {}

    def add(self, item_id: str, signature: List[int]) -> None:
        """Add an item to the LSH index."""
        self.signatures[item_id] = signature

        # Hash each band and add to corresponding bucket
        for band_idx in range(self.bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band_signature = tuple(signature[start:end])
            bucket_key = hash(band_signature)
            self.buckets[band_idx][bucket_key].add(item_id)

    def get_candidates(self, signature: List[int]) -> Set[str]:
        """
        Get candidate items that might be similar.

        Args:
            signature: MinHash signature to find candidates for

        Returns:
            Set of item IDs that are candidate duplicates
        """
        candidates = set()

        for band_idx in range(self.bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band_signature = tuple(signature[start:end])
            bucket_key = hash(band_signature)
            candidates.update(self.buckets[band_idx].get(bucket_key, set()))

        return candidates

    def clear(self) -> None:
        """Clear the LSH index."""
        self.buckets = [defaultdict(set) for _ in range(self.bands)]
        self.signatures.clear()


class TextNormalizer:
    """Normalizes text for consistent comparison."""

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text for comparison.

        - Lowercase
        - Normalize Unicode
        - Collapse whitespace
        - Remove common punctuation variations
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Normalize Unicode (decompose then compose)
        text = unicodedata.normalize('NFKC', text)

        # Replace various whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Normalize common variations
        text = text.replace('\u2019', "'")  # Smart apostrophe
        text = text.replace('\u201c', '"').replace('\u201d', '"')  # Smart quotes
        text = text.replace('\u2013', '-').replace('\u2014', '-')  # Dashes

        return text.strip()

    @staticmethod
    def to_shingles(text: str, n: int = DEFAULT_SHINGLE_SIZE) -> Set[str]:
        """
        Convert text to character n-grams (shingles).

        Args:
            text: Input text
            n: Shingle size (n-gram length)

        Returns:
            Set of shingles
        """
        normalized = TextNormalizer.normalize(text)
        if len(normalized) < n:
            return {normalized} if normalized else set()

        return {normalized[i:i+n] for i in range(len(normalized) - n + 1)}

    @staticmethod
    def to_word_shingles(text: str, n: int = 2) -> Set[str]:
        """
        Convert text to word n-grams.

        Args:
            text: Input text
            n: Number of words per shingle

        Returns:
            Set of word shingles
        """
        normalized = TextNormalizer.normalize(text)
        words = normalized.split()

        if len(words) < n:
            return {' '.join(words)} if words else set()

        return {' '.join(words[i:i+n]) for i in range(len(words) - n + 1)}


class Deduplicator:
    """
    Removes duplicate training examples using multiple detection methods.

    Usage:
        dedup = Deduplicator()

        # Find duplicates
        groups = dedup.find_duplicates(examples)

        # Get deduplicated set
        unique_examples = dedup.deduplicate(examples)
    """

    # Field aliases for different training data formats
    FIELD_ALIASES = {
        "input": ["input", "prompt", "query", "question", "user", "human"],
        "output": ["output", "response", "answer", "assistant", "good_response", "completion"],
        "instruction": ["instruction", "system", "system_prompt"],
    }

    def __init__(
        self,
        jaccard_threshold: float = DEFAULT_JACCARD_THRESHOLD,
        semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
        num_hashes: int = DEFAULT_NUM_HASHES,
        shingle_size: int = DEFAULT_SHINGLE_SIZE,
        use_semantic: bool = True,
    ):
        """
        Initialize the deduplicator.

        Args:
            jaccard_threshold: Similarity threshold for near-duplicates (0-1)
            semantic_threshold: Cosine similarity threshold for semantic duplicates (0-1)
            num_hashes: Number of hash functions for MinHash
            shingle_size: N-gram size for shingling
            use_semantic: Whether to use semantic (embedding-based) deduplication
        """
        self.jaccard_threshold = jaccard_threshold
        self.semantic_threshold = semantic_threshold
        self.shingle_size = shingle_size
        self.use_semantic = use_semantic

        # Initialize MinHash and LSH
        self.minhash = MinHash(num_hashes=num_hashes)
        self.lsh = LSH(num_hashes=num_hashes, bands=16)

        # Track processed examples
        self.exact_hashes: Dict[str, str] = {}  # content_hash -> example_id
        self.signatures: Dict[str, List[int]] = {}  # example_id -> minhash signature
        self.embeddings: Dict[str, Any] = {}  # example_id -> embedding vector

        # Lazy-load embedding model
        self._embedding_model = None
        self._embedding_tokenizer = None

    def _normalize_fields(self, example: Dict) -> Dict:
        """
        Normalize field names to standard format (input/output).

        Supports different training data formats like prompt/response,
        prompt/good_response, messages, etc.
        """
        normalized = dict(example)

        # Handle messages format (OpenAI style)
        if "messages" in example and isinstance(example["messages"], list):
            messages = example["messages"]
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                if role in ["user", "human"]:
                    normalized["input"] = content
                elif role in ["assistant", "ai", "bot"]:
                    normalized["output"] = content
                elif role in ["system"]:
                    normalized["instruction"] = content

        # Map aliases to standard field names
        for standard_field, aliases in self.FIELD_ALIASES.items():
            if standard_field not in normalized or not normalized.get(standard_field):
                for alias in aliases:
                    if alias in example and example[alias]:
                        normalized[standard_field] = example[alias]
                        break

        return normalized

    def _get_content_hash(self, example: Dict) -> str:
        """Generate hash of example content."""
        # Normalize field names first
        normalized = self._normalize_fields(example)

        # Normalize and combine relevant fields
        content_parts = []
        for field in ['input', 'output', 'instruction']:
            if field in normalized and normalized[field]:
                content_parts.append(TextNormalizer.normalize(str(normalized[field])))

        content = '||'.join(content_parts)
        return hashlib.sha256(content.encode()).hexdigest()

    def _generate_id(self, example: Dict) -> str:
        """Generate unique ID for an example."""
        content = json.dumps(example, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _get_combined_text(self, example: Dict) -> str:
        """Get combined text from example for similarity comparison."""
        # Normalize field names first
        normalized = self._normalize_fields(example)

        parts = []
        for field in ['input', 'output', 'instruction']:
            if field in normalized and normalized[field]:
                parts.append(str(normalized[field]))
        return ' '.join(parts)

    def _get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding for text using MLX."""
        if not self.use_semantic:
            return None

        try:
            import mlx_embeddings
            import numpy as np

            # Lazy load model
            if self._embedding_model is None:
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self._embedding_model, self._embedding_tokenizer = mlx_embeddings.load(model_name)

            # Generate embedding
            output = mlx_embeddings.generate(
                self._embedding_model,
                self._embedding_tokenizer,
                text[:2000]  # Limit text length
            )

            return np.array(output.text_embeds[0])

        except ImportError:
            # MLX not available, disable semantic dedup
            self.use_semantic = False
            return None
        except Exception as e:
            print(f"Embedding error: {e}")
            return None

    def _cosine_similarity(self, vec1: Any, vec2: Any) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np

        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot / (norm1 * norm2))

    def _select_representative(self, examples: List[Dict]) -> Tuple[Dict, str]:
        """
        Select the best representative example from a group of duplicates.

        Selection criteria (in order of priority):
        1. Quality score (if available in metadata)
        2. Completeness (has more fields filled)
        3. Content length (longer is often better)
        4. Recency (newer is better)
        5. Source priority (some sources are more reliable)
        """
        if not examples:
            raise ValueError("Cannot select from empty list")

        if len(examples) == 1:
            return examples[0], self._generate_id(examples[0])

        def score_example(ex: Dict) -> Tuple[float, int, int, str, int]:
            # Quality score from metadata (higher is better)
            quality = ex.get('metadata', {}).get('quality_score', 0.5)

            # Completeness (count of non-empty fields)
            completeness = sum(1 for v in ex.values() if v and str(v).strip())

            # Content length
            content_len = sum(len(str(v)) for v in ex.values() if isinstance(v, str))

            # Timestamp (newer is better, use empty string if no timestamp)
            timestamp = ex.get('metadata', {}).get('timestamp', '') or ''

            # Source priority (lower is better)
            source_priority = {
                'human_curated': 0,
                'human': 1,
                'approved': 2,
                'generated': 3,
                'scraped': 4,
                'unknown': 5
            }
            source = ex.get('metadata', {}).get('source', 'unknown')
            priority = source_priority.get(source, 5)

            return (quality, completeness, content_len, timestamp, -priority)

        # Sort by score (descending) and pick best
        sorted_examples = sorted(examples, key=score_example, reverse=True)
        best = sorted_examples[0]

        return best, self._generate_id(best)

    def find_exact_duplicates(
        self,
        examples: List[Dict],
        progress_callback=None
    ) -> List[DuplicateGroup]:
        """
        Find exact duplicates using content hashing.

        Args:
            examples: List of training examples
            progress_callback: Optional callback(current, total)

        Returns:
            List of duplicate groups
        """
        hash_groups: Dict[str, List[Tuple[str, Dict]]] = defaultdict(list)

        for i, example in enumerate(examples):
            example_id = self._generate_id(example)
            content_hash = self._get_content_hash(example)
            hash_groups[content_hash].append((example_id, example))

            if progress_callback and i % 100 == 0:
                progress_callback(i + 1, len(examples))

        # Convert to duplicate groups (only groups with > 1 item)
        groups = []
        for content_hash, items in hash_groups.items():
            if len(items) > 1:
                example_ids = [item[0] for item in items]
                example_list = [item[1] for item in items]

                representative, rep_id = self._select_representative(example_list)

                groups.append(DuplicateGroup(
                    group_id=content_hash[:12],
                    detection_method="exact",
                    similarity_score=1.0,
                    examples=example_list,
                    example_ids=example_ids,
                    representative_id=rep_id
                ))

        return groups

    def find_near_duplicates(
        self,
        examples: List[Dict],
        progress_callback=None
    ) -> List[DuplicateGroup]:
        """
        Find near-duplicates using MinHash/LSH.

        Args:
            examples: List of training examples
            progress_callback: Optional callback(current, total)

        Returns:
            List of duplicate groups
        """
        # Build LSH index
        self.lsh.clear()
        example_data: Dict[str, Dict] = {}

        for i, example in enumerate(examples):
            example_id = self._generate_id(example)
            example_data[example_id] = example

            # Generate shingles and MinHash signature
            text = self._get_combined_text(example)
            shingles = TextNormalizer.to_shingles(text, self.shingle_size)
            signature = self.minhash.compute_signature(shingles)

            self.signatures[example_id] = signature
            self.lsh.add(example_id, signature)

            if progress_callback and i % 100 == 0:
                progress_callback(i + 1, len(examples))

        # Find candidate pairs and verify with actual Jaccard
        processed_pairs: Set[Tuple[str, str]] = set()
        similarity_graph: Dict[str, Set[str]] = defaultdict(set)

        for example_id, signature in self.signatures.items():
            candidates = self.lsh.get_candidates(signature)
            candidates.discard(example_id)  # Remove self

            for candidate_id in candidates:
                # Avoid processing same pair twice
                pair = tuple(sorted([example_id, candidate_id]))
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)

                # Estimate Jaccard similarity
                similarity = self.minhash.estimate_jaccard(
                    signature,
                    self.signatures[candidate_id]
                )

                if similarity >= self.jaccard_threshold:
                    similarity_graph[example_id].add(candidate_id)
                    similarity_graph[candidate_id].add(example_id)

        # Find connected components (duplicate groups)
        groups = self._find_connected_components(similarity_graph, example_data, "near_duplicate")

        return groups

    def find_semantic_duplicates(
        self,
        examples: List[Dict],
        progress_callback=None
    ) -> List[DuplicateGroup]:
        """
        Find semantic duplicates using embedding similarity.

        Args:
            examples: List of training examples
            progress_callback: Optional callback(current, total)

        Returns:
            List of duplicate groups
        """
        if not self.use_semantic:
            return []

        # Generate embeddings
        example_data: Dict[str, Dict] = {}

        for i, example in enumerate(examples):
            example_id = self._generate_id(example)
            example_data[example_id] = example

            text = self._get_combined_text(example)
            embedding = self._get_embedding(text)

            if embedding is not None:
                self.embeddings[example_id] = embedding

            if progress_callback and i % 50 == 0:
                progress_callback(i + 1, len(examples))

        if not self.embeddings:
            return []

        # Find similar pairs (O(n^2) but limited to semantic comparison)
        similarity_graph: Dict[str, Set[str]] = defaultdict(set)
        example_ids = list(self.embeddings.keys())

        for i, id1 in enumerate(example_ids):
            for id2 in example_ids[i+1:]:
                similarity = self._cosine_similarity(
                    self.embeddings[id1],
                    self.embeddings[id2]
                )

                if similarity >= self.semantic_threshold:
                    similarity_graph[id1].add(id2)
                    similarity_graph[id2].add(id1)

        # Find connected components
        groups = self._find_connected_components(similarity_graph, example_data, "semantic")

        return groups

    def _find_connected_components(
        self,
        graph: Dict[str, Set[str]],
        example_data: Dict[str, Dict],
        method: str
    ) -> List[DuplicateGroup]:
        """Find connected components in similarity graph."""
        visited: Set[str] = set()
        groups = []

        def dfs(node: str, component: List[str]):
            visited.add(node)
            component.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, component)

        for node in graph:
            if node not in visited:
                component: List[str] = []
                dfs(node, component)

                if len(component) > 1:
                    examples = [example_data[eid] for eid in component if eid in example_data]
                    if examples:
                        representative, rep_id = self._select_representative(examples)

                        groups.append(DuplicateGroup(
                            group_id=hashlib.md5(''.join(sorted(component)).encode()).hexdigest()[:12],
                            detection_method=method,
                            similarity_score=self.jaccard_threshold if method == "near_duplicate" else self.semantic_threshold,
                            examples=examples,
                            example_ids=component,
                            representative_id=rep_id
                        ))

        return groups

    def find_duplicates(
        self,
        examples: List[Dict],
        methods: List[str] = None,
        progress_callback=None
    ) -> List[DuplicateGroup]:
        """
        Find all duplicates using specified methods.

        Args:
            examples: List of training examples
            methods: List of methods to use ("exact", "near_duplicate", "semantic")
                     Defaults to all methods
            progress_callback: Optional callback(stage, current, total)

        Returns:
            List of all duplicate groups found
        """
        if methods is None:
            methods = ["exact", "near_duplicate"]
            if self.use_semantic:
                methods.append("semantic")

        all_groups = []

        # Track which examples are already marked as duplicates
        marked_duplicates: Set[str] = set()

        if "exact" in methods:
            if progress_callback:
                progress_callback("exact", 0, len(examples))
            groups = self.find_exact_duplicates(
                examples,
                lambda c, t: progress_callback("exact", c, t) if progress_callback else None
            )

            # Mark duplicates
            for group in groups:
                for eid in group.example_ids:
                    if eid != group.representative_id:
                        marked_duplicates.add(eid)

            all_groups.extend(groups)

        if "near_duplicate" in methods:
            # Filter out already-found exact duplicates
            remaining = [
                ex for ex in examples
                if self._generate_id(ex) not in marked_duplicates
            ]

            if progress_callback:
                progress_callback("near_duplicate", 0, len(remaining))

            groups = self.find_near_duplicates(
                remaining,
                lambda c, t: progress_callback("near_duplicate", c, t) if progress_callback else None
            )

            for group in groups:
                for eid in group.example_ids:
                    if eid != group.representative_id:
                        marked_duplicates.add(eid)

            all_groups.extend(groups)

        if "semantic" in methods and self.use_semantic:
            # Filter out already-found duplicates
            remaining = [
                ex for ex in examples
                if self._generate_id(ex) not in marked_duplicates
            ]

            if progress_callback:
                progress_callback("semantic", 0, len(remaining))

            groups = self.find_semantic_duplicates(
                remaining,
                lambda c, t: progress_callback("semantic", c, t) if progress_callback else None
            )

            all_groups.extend(groups)

        return all_groups

    def deduplicate(
        self,
        examples: List[Dict],
        methods: List[str] = None,
        progress_callback=None
    ) -> Tuple[List[Dict], DeduplicationStats]:
        """
        Remove duplicates and return unique examples.

        Args:
            examples: List of training examples
            methods: Detection methods to use
            progress_callback: Optional callback

        Returns:
            Tuple of (unique_examples, stats)
        """
        start_time = time.time()

        # Find duplicates
        groups = self.find_duplicates(examples, methods, progress_callback)

        # Build set of IDs to remove (keep representatives)
        remove_ids: Set[str] = set()
        exact_count = 0
        near_count = 0
        semantic_count = 0

        for group in groups:
            for eid in group.example_ids:
                if eid != group.representative_id:
                    remove_ids.add(eid)

            # Count by method
            duplicate_count = len(group.example_ids) - 1
            if group.detection_method == "exact":
                exact_count += duplicate_count
            elif group.detection_method == "near_duplicate":
                near_count += duplicate_count
            elif group.detection_method == "semantic":
                semantic_count += duplicate_count

        # Filter to unique examples
        unique_examples = [
            ex for ex in examples
            if self._generate_id(ex) not in remove_ids
        ]

        stats = DeduplicationStats(
            total_examples=len(examples),
            unique_examples=len(unique_examples),
            duplicate_groups=len(groups),
            duplicates_removed=len(remove_ids),
            exact_duplicates=exact_count,
            near_duplicates=near_count,
            semantic_duplicates=semantic_count,
            processing_time=time.time() - start_time
        )

        return unique_examples, stats

    def deduplicate_batch(
        self,
        examples_iter: Iterator[Dict],
        batch_size: int = 1000,
        output_callback=None,
        progress_callback=None
    ) -> DeduplicationStats:
        """
        Deduplicate examples in batches for memory efficiency.

        Args:
            examples_iter: Iterator yielding examples
            batch_size: Number of examples per batch
            output_callback: Callback(unique_examples) for each batch
            progress_callback: Optional callback(batch_num, total_processed)

        Returns:
            Cumulative deduplication stats
        """
        cumulative_stats = DeduplicationStats()
        batch_num = 0

        batch = []
        for example in examples_iter:
            batch.append(example)

            if len(batch) >= batch_size:
                batch_num += 1
                unique, stats = self.deduplicate(batch)

                cumulative_stats.total_examples += stats.total_examples
                cumulative_stats.unique_examples += stats.unique_examples
                cumulative_stats.duplicate_groups += stats.duplicate_groups
                cumulative_stats.duplicates_removed += stats.duplicates_removed
                cumulative_stats.exact_duplicates += stats.exact_duplicates
                cumulative_stats.near_duplicates += stats.near_duplicates
                cumulative_stats.semantic_duplicates += stats.semantic_duplicates
                cumulative_stats.processing_time += stats.processing_time

                if output_callback:
                    output_callback(unique)

                if progress_callback:
                    progress_callback(batch_num, cumulative_stats.total_examples)

                batch = []

        # Process remaining
        if batch:
            unique, stats = self.deduplicate(batch)
            cumulative_stats.total_examples += stats.total_examples
            cumulative_stats.unique_examples += stats.unique_examples
            cumulative_stats.duplicate_groups += stats.duplicate_groups
            cumulative_stats.duplicates_removed += stats.duplicates_removed
            cumulative_stats.exact_duplicates += stats.exact_duplicates
            cumulative_stats.near_duplicates += stats.near_duplicates
            cumulative_stats.semantic_duplicates += stats.semantic_duplicates
            cumulative_stats.processing_time += stats.processing_time

            if output_callback:
                output_callback(unique)

        return cumulative_stats


def deduplicate_jsonl_file(
    input_path: Path,
    output_path: Path,
    jaccard_threshold: float = DEFAULT_JACCARD_THRESHOLD,
    use_semantic: bool = False,
    progress_callback=None
) -> DeduplicationStats:
    """
    Deduplicate a JSONL file and write results.

    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file
        jaccard_threshold: Similarity threshold
        use_semantic: Whether to use semantic deduplication
        progress_callback: Optional callback

    Returns:
        DeduplicationStats
    """
    # Load examples
    examples = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # Deduplicate
    dedup = Deduplicator(
        jaccard_threshold=jaccard_threshold,
        use_semantic=use_semantic
    )
    unique, stats = dedup.deduplicate(examples, progress_callback=progress_callback)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in unique:
            f.write(json.dumps(ex) + '\n')

    return stats


if __name__ == "__main__":
    import sys

    print("SAM Deduplication System")
    print("-" * 40)

    if len(sys.argv) < 2:
        print("\nUsage: python deduplication.py <command> [args]")
        print("\nCommands:")
        print("  dedup <input.jsonl> <output.jsonl>  - Deduplicate training data file")
        print("  analyze <input.jsonl>               - Analyze duplicates without removing")
        print("  demo                                - Run demo with sample data")
        print("\nOptions:")
        print("  --threshold <0-1>                   - Jaccard similarity threshold (default: 0.8)")
        print("  --semantic                          - Enable semantic deduplication")
        sys.exit(0)

    cmd = sys.argv[1]

    # Parse options
    threshold = DEFAULT_JACCARD_THRESHOLD
    use_semantic = False

    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        if idx + 1 < len(sys.argv):
            threshold = float(sys.argv[idx + 1])

    if "--semantic" in sys.argv:
        use_semantic = True

    if cmd == "dedup" and len(sys.argv) > 3:
        input_path = Path(sys.argv[2])
        output_path = Path(sys.argv[3])

        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)

        print(f"\nDeduplicating: {input_path}")
        print(f"Threshold: {threshold}")
        print(f"Semantic: {use_semantic}")

        def progress(stage, current, total):
            print(f"\r  {stage}: {current}/{total}", end='')

        stats = deduplicate_jsonl_file(
            input_path,
            output_path,
            jaccard_threshold=threshold,
            use_semantic=use_semantic,
            progress_callback=progress
        )
        print()  # New line

        print(f"\nResults:")
        print(f"  Input: {stats.total_examples}")
        print(f"  Output: {stats.unique_examples}")
        print(f"  Removed: {stats.duplicates_removed}")
        print(f"  - Exact: {stats.exact_duplicates}")
        print(f"  - Near: {stats.near_duplicates}")
        print(f"  - Semantic: {stats.semantic_duplicates}")
        print(f"  Time: {stats.processing_time:.2f}s")
        print(f"\nSaved to: {output_path}")

    elif cmd == "analyze" and len(sys.argv) > 2:
        input_path = Path(sys.argv[2])

        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)

        # Load examples
        examples = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        examples.append(json.loads(line.strip()))
                    except:
                        pass

        print(f"\nAnalyzing: {input_path} ({len(examples)} examples)")

        dedup = Deduplicator(
            jaccard_threshold=threshold,
            use_semantic=use_semantic
        )

        groups = dedup.find_duplicates(examples)

        print(f"\nFound {len(groups)} duplicate groups:")

        for i, group in enumerate(groups[:10]):  # Show first 10
            print(f"\n  Group {i+1} ({group.detection_method}, {len(group.examples)} examples):")
            for j, ex in enumerate(group.examples[:3]):  # Show first 3 in group
                preview = str(ex.get('input', ''))[:60]
                print(f"    {j+1}. {preview}...")
            if len(group.examples) > 3:
                print(f"    ... and {len(group.examples) - 3} more")

        if len(groups) > 10:
            print(f"\n  ... and {len(groups) - 10} more groups")

    elif cmd == "demo":
        print("\nRunning demo...")

        # Sample data with duplicates
        examples = [
            # Exact duplicates
            {"input": "Write a hello world in Python", "output": "print('Hello, World!')"},
            {"input": "Write a hello world in Python", "output": "print('Hello, World!')"},

            # Near duplicates (slight variations)
            {"input": "How do I write hello world in Python?", "output": "print('Hello, World!')"},
            {"input": "How can I write a hello world program in python?", "output": "print('Hello, World!')"},

            # Unique examples
            {"input": "What is binary search?", "output": "Binary search is a divide-and-conquer algorithm..."},
            {"input": "Explain recursion", "output": "Recursion is when a function calls itself..."},
            {"input": "How do I read a file in Python?", "output": "with open('file.txt', 'r') as f: content = f.read()"},

            # More near duplicates
            {"input": "Sort a list in Python", "output": "sorted_list = sorted(my_list)"},
            {"input": "How to sort a list in python?", "output": "sorted_list = sorted(my_list)"},
        ]

        print(f"Input: {len(examples)} examples")

        dedup = Deduplicator(jaccard_threshold=0.6, use_semantic=False)
        unique, stats = dedup.deduplicate(examples)

        print(f"\nResults:")
        print(f"  Total: {stats.total_examples}")
        print(f"  Unique: {stats.unique_examples}")
        print(f"  Removed: {stats.duplicates_removed}")
        print(f"  - Exact: {stats.exact_duplicates}")
        print(f"  - Near: {stats.near_duplicates}")
        print(f"  Time: {stats.processing_time:.3f}s")

        print(f"\nRemaining unique examples:")
        for i, ex in enumerate(unique):
            print(f"  {i+1}. {ex.get('input', '')[:50]}...")

    else:
        print(f"Unknown command: {cmd}")
        print("Use 'python deduplication.py' for help")
