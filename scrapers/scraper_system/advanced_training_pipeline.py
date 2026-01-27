#!/usr/bin/env python3
"""
Advanced Training Pipeline for SAM

Comprehensive approach for 8GB M2 Mac:
1. Semantic deduplication (not just ID-based)
2. Quality scoring & filtering
3. Diversity sampling via embeddings
4. Curriculum learning (easy → hard)
5. Incremental LoRA with adapter merging
6. Memory-efficient streaming

This is the "do it right" version.
"""

import json
import sqlite3
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import heapq

# Use MLX for embeddings (fast on Apple Silicon)
try:
    import mlx.core as mx
    from mlx_embedding import get_embedder
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("Note: mlx_embedding not available, using hash-based dedup only")


@dataclass
class TrainingExample:
    """A single training example with metadata."""
    id: str
    source: str
    text: str
    quality_score: float = 0.0
    difficulty_score: float = 0.0
    embedding: Optional[np.ndarray] = None
    word_count: int = 0
    hash: str = ""

    def __post_init__(self):
        self.word_count = len(self.text.split())
        self.hash = hashlib.md5(self.text.encode()).hexdigest()


class AdvancedTrainingPipeline:
    """
    Advanced training data pipeline with:
    - Semantic deduplication
    - Quality filtering
    - Diversity sampling
    - Curriculum learning
    - Incremental training support
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / ".sam" / "training_pipeline.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Embedding model for semantic operations
        self.embedder = None
        if MLX_AVAILABLE:
            try:
                self.embedder = get_embedder()
            except:
                pass

    def _init_db(self):
        """Initialize pipeline database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            -- Processed examples with full metadata
            CREATE TABLE IF NOT EXISTS examples (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                quality_score REAL DEFAULT 0,
                difficulty_score REAL DEFAULT 0,
                word_count INTEGER,
                embedding BLOB,
                processed_at TEXT,
                training_batch TEXT,
                UNIQUE(text_hash)  -- Semantic dedup by content hash
            );

            -- Training batches
            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                created_at TEXT,
                examples_count INTEGER,
                avg_quality REAL,
                curriculum_stage INTEGER,
                adapter_path TEXT,
                merged_into TEXT,
                notes TEXT
            );

            -- Curriculum stages
            CREATE TABLE IF NOT EXISTS curriculum (
                stage INTEGER PRIMARY KEY,
                description TEXT,
                min_quality REAL,
                max_difficulty REAL,
                target_diversity REAL
            );

            CREATE INDEX IF NOT EXISTS idx_quality ON examples(quality_score);
            CREATE INDEX IF NOT EXISTS idx_difficulty ON examples(difficulty_score);
            CREATE INDEX IF NOT EXISTS idx_batch ON examples(training_batch);
            CREATE INDEX IF NOT EXISTS idx_hash ON examples(text_hash);
        """)

        # Initialize default curriculum if empty
        cursor = conn.execute("SELECT COUNT(*) FROM curriculum")
        if cursor.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO curriculum (stage, description, min_quality, max_difficulty, target_diversity) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, "Foundation - High quality, simple examples", 0.7, 0.3, 0.5),
                    (2, "Expansion - Good quality, moderate complexity", 0.5, 0.6, 0.7),
                    (3, "Refinement - Acceptable quality, full complexity", 0.3, 1.0, 0.8),
                    (4, "Edge cases - All remaining valid examples", 0.1, 1.0, 0.9),
                ]
            )

        conn.commit()
        conn.close()

    # =========================================================================
    # Quality Scoring
    # =========================================================================

    def score_quality(self, text: str) -> float:
        """
        Score text quality (0-1). Higher = better for training.

        Factors:
        - Length (not too short, not too long)
        - Vocabulary richness
        - Proper formatting
        - No obvious garbage
        """
        score = 1.0

        words = text.split()
        word_count = len(words)

        # Length penalty
        if word_count < 50:
            score *= 0.5  # Too short
        elif word_count > 10000:
            score *= 0.7  # Very long, might be noise
        elif word_count > 5000:
            score *= 0.9  # Long but ok

        # Vocabulary richness (unique words / total words)
        if word_count > 0:
            unique_ratio = len(set(words)) / word_count
            if unique_ratio < 0.2:
                score *= 0.6  # Very repetitive
            elif unique_ratio > 0.8:
                score *= 0.9  # Might be word salad

        # Garbage detection
        garbage_indicators = [
            text.count('�') > 5,  # Encoding issues
            text.count('http') > 10,  # Too many URLs
            len([c for c in text if not c.isascii()]) / max(len(text), 1) > 0.3,  # Too much non-ASCII
            text.count('\n\n\n') > 5,  # Excessive whitespace
        ]
        for is_garbage in garbage_indicators:
            if is_garbage:
                score *= 0.5

        # Formatting quality
        has_paragraphs = '\n\n' in text or '\n' in text
        has_dialogue = '"' in text or '"' in text
        if has_paragraphs:
            score *= 1.1  # Good structure
        if has_dialogue:
            score *= 1.05  # Conversational content

        return min(1.0, max(0.0, score))

    def score_difficulty(self, text: str) -> float:
        """
        Score text difficulty (0-1). Higher = more complex.

        Used for curriculum learning - start with simpler examples.
        """
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Average word length (proxy for vocabulary complexity)
        avg_word_len = sum(len(w) for w in words) / word_count

        # Sentence complexity (words per sentence)
        sentences = text.count('.') + text.count('!') + text.count('?')
        words_per_sentence = word_count / max(sentences, 1)

        # Normalize to 0-1
        difficulty = 0.0
        difficulty += min(1.0, avg_word_len / 8) * 0.3  # Word complexity
        difficulty += min(1.0, words_per_sentence / 30) * 0.3  # Sentence complexity
        difficulty += min(1.0, word_count / 3000) * 0.4  # Length complexity

        return difficulty

    # =========================================================================
    # Semantic Deduplication
    # =========================================================================

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for semantic similarity."""
        if self.embedder is None:
            return None

        # Truncate for embedding (most models have limits)
        truncated = text[:2000]
        try:
            emb = self.embedder.embed(truncated)
            return np.array(emb)
        except:
            return None

    def is_semantic_duplicate(self, embedding: np.ndarray, threshold: float = 0.92) -> bool:
        """Check if embedding is too similar to existing examples."""
        if embedding is None:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT embedding FROM examples WHERE embedding IS NOT NULL LIMIT 1000")

        for row in cursor:
            if row[0]:
                existing = np.frombuffer(row[0], dtype=np.float32)
                similarity = np.dot(embedding, existing) / (np.linalg.norm(embedding) * np.linalg.norm(existing) + 1e-8)
                if similarity > threshold:
                    conn.close()
                    return True

        conn.close()
        return False

    # =========================================================================
    # Diversity Sampling
    # =========================================================================

    def select_diverse_batch(self, examples: List[TrainingExample],
                             batch_size: int,
                             diversity_weight: float = 0.5) -> List[TrainingExample]:
        """
        Select a diverse batch using maximal marginal relevance.

        Balances quality with diversity to avoid training on too-similar examples.
        """
        if len(examples) <= batch_size:
            return examples

        # If no embeddings, fall back to quality-based selection
        if not any(e.embedding is not None for e in examples):
            return sorted(examples, key=lambda x: x.quality_score, reverse=True)[:batch_size]

        selected = []
        remaining = list(examples)

        # Start with highest quality example
        remaining.sort(key=lambda x: x.quality_score, reverse=True)
        selected.append(remaining.pop(0))

        while len(selected) < batch_size and remaining:
            best_score = -float('inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                if candidate.embedding is None:
                    # No embedding - use quality only
                    score = candidate.quality_score
                else:
                    # MMR: balance quality with diversity
                    quality = candidate.quality_score

                    # Max similarity to already selected
                    max_sim = 0
                    for s in selected:
                        if s.embedding is not None:
                            sim = np.dot(candidate.embedding, s.embedding)
                            max_sim = max(max_sim, sim)

                    diversity = 1 - max_sim
                    score = (1 - diversity_weight) * quality + diversity_weight * diversity

                if score > best_score:
                    best_score = score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    # =========================================================================
    # Curriculum Learning
    # =========================================================================

    def get_curriculum_stage(self) -> int:
        """Get current curriculum stage based on completed batches."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT MAX(curriculum_stage) FROM batches")
        result = cursor.fetchone()[0]
        conn.close()
        return result or 1

    def get_examples_for_stage(self, stage: int, limit: int = 5000) -> List[Dict]:
        """Get examples appropriate for current curriculum stage."""
        conn = sqlite3.connect(self.db_path)

        # Get stage parameters
        cursor = conn.execute(
            "SELECT min_quality, max_difficulty FROM curriculum WHERE stage = ?",
            (stage,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []

        min_quality, max_difficulty = row

        # Get matching examples not yet trained
        cursor = conn.execute("""
            SELECT id, source, quality_score, difficulty_score
            FROM examples
            WHERE training_batch IS NULL
              AND quality_score >= ?
              AND difficulty_score <= ?
            ORDER BY quality_score DESC
            LIMIT ?
        """, (min_quality, max_difficulty, limit))

        examples = [
            {"id": r[0], "source": r[1], "quality": r[2], "difficulty": r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return examples

    # =========================================================================
    # Incremental Training Support
    # =========================================================================

    def create_training_batch(self, source: str, examples: List[TrainingExample],
                              batch_id: str = None) -> str:
        """Create a new training batch and record metadata."""
        if not batch_id:
            batch_id = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        stage = self.get_curriculum_stage()
        avg_quality = sum(e.quality_score for e in examples) / len(examples) if examples else 0

        conn = sqlite3.connect(self.db_path)

        # Record batch
        conn.execute("""
            INSERT INTO batches (batch_id, created_at, examples_count, avg_quality, curriculum_stage)
            VALUES (?, ?, ?, ?, ?)
        """, (batch_id, datetime.now().isoformat(), len(examples), avg_quality, stage))

        # Mark examples as used
        for ex in examples:
            conn.execute("""
                UPDATE examples SET training_batch = ? WHERE id = ?
            """, (batch_id, ex.id))

        conn.commit()
        conn.close()

        return batch_id

    # =========================================================================
    # Main Processing
    # =========================================================================

    def process_text(self, id: str, source: str, text: str) -> Optional[TrainingExample]:
        """Process a single text and add to pipeline if valid."""
        # Create example with scores
        example = TrainingExample(
            id=id,
            source=source,
            text=text,
            quality_score=self.score_quality(text),
            difficulty_score=self.score_difficulty(text),
        )

        # Skip low quality
        if example.quality_score < 0.1:
            return None

        # Check for exact duplicates (by hash)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id FROM examples WHERE text_hash = ?",
            (example.hash,)
        )
        if cursor.fetchone():
            conn.close()
            return None  # Duplicate

        # Get embedding for semantic checks
        example.embedding = self.get_embedding(text)

        # Check semantic duplicates (if embeddings available)
        if example.embedding is not None and self.is_semantic_duplicate(example.embedding):
            conn.close()
            return None

        # Store in database
        embedding_blob = example.embedding.tobytes() if example.embedding is not None else None
        conn.execute("""
            INSERT OR IGNORE INTO examples
            (id, source, text_hash, quality_score, difficulty_score, word_count, embedding, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            example.id, example.source, example.hash,
            example.quality_score, example.difficulty_score,
            example.word_count, embedding_blob,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return example

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        conn = sqlite3.connect(self.db_path)

        stats = {}

        # Total examples
        cursor = conn.execute("SELECT COUNT(*), AVG(quality_score), AVG(difficulty_score) FROM examples")
        row = cursor.fetchone()
        stats["total_examples"] = row[0]
        stats["avg_quality"] = round(row[1] or 0, 3)
        stats["avg_difficulty"] = round(row[2] or 0, 3)

        # By source
        cursor = conn.execute("SELECT source, COUNT(*) FROM examples GROUP BY source")
        stats["by_source"] = {r[0]: r[1] for r in cursor.fetchall()}

        # Trained vs untrained
        cursor = conn.execute("SELECT COUNT(*) FROM examples WHERE training_batch IS NOT NULL")
        stats["trained"] = cursor.fetchone()[0]
        stats["untrained"] = stats["total_examples"] - stats["trained"]

        # Batches
        cursor = conn.execute("SELECT COUNT(*) FROM batches")
        stats["batches"] = cursor.fetchone()[0]

        # Current curriculum stage
        stats["curriculum_stage"] = self.get_curriculum_stage()

        conn.close()
        return stats


def show_status():
    """Show pipeline status."""
    pipeline = AdvancedTrainingPipeline()
    stats = pipeline.get_stats()

    print("=" * 60)
    print("Advanced Training Pipeline Status")
    print("=" * 60)
    print(f"\nTotal examples:    {stats['total_examples']:,}")
    print(f"Avg quality:       {stats['avg_quality']}")
    print(f"Avg difficulty:    {stats['avg_difficulty']}")
    print(f"\nTrained:           {stats['trained']:,}")
    print(f"Untrained:         {stats['untrained']:,}")
    print(f"Training batches:  {stats['batches']}")
    print(f"Curriculum stage:  {stats['curriculum_stage']}")
    print(f"\nBy source:")
    for source, count in stats.get("by_source", {}).items():
        print(f"  {source}: {count:,}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_status()
    else:
        print("Advanced Training Pipeline")
        print()
        print("Features:")
        print("  - Semantic deduplication (embedding similarity)")
        print("  - Quality scoring (filters low-quality content)")
        print("  - Diversity sampling (avoids redundant training)")
        print("  - Curriculum learning (easy → hard progression)")
        print("  - Incremental training (never retrain on same data)")
        print()
        print("Usage: python advanced_training_pipeline.py status")
