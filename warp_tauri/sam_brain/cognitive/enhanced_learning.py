"""
Enhanced Learning System for SAM Cognitive Architecture

Implements:
1. Active Learning - Ask for what's needed to improve
2. Predictive Caching - Pre-load likely context
3. Sleep Consolidation - Background memory reorganization

Integrates with existing:
- sam_intelligence.py (pattern learning)
- escalation_learner.py (API dependency reduction)
- knowledge_distillation.py (reasoning extraction)
"""

import json
import sqlite3
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from queue import PriorityQueue
import random


@dataclass
class LearningOpportunity:
    """An opportunity to learn something new"""
    id: str
    query: str
    uncertainty_type: str  # 'knowledge_gap', 'ambiguity', 'missing_context'
    importance: float  # 0-1
    suggested_question: str
    created_at: datetime = field(default_factory=datetime.now)
    addressed: bool = False


class ActiveLearner:
    """
    Active learning system that identifies what SAM needs to learn.

    Instead of passively waiting for information, actively:
    1. Identifies knowledge gaps
    2. Generates questions to fill gaps
    3. Prioritizes learning opportunities
    4. Tracks what's been learned
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/active_learning.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Track recent uncertainties
        self.uncertainty_buffer: List[LearningOpportunity] = []
        self.knowledge_gaps: Set[str] = set()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_opportunities (
                id TEXT PRIMARY KEY,
                query TEXT,
                uncertainty_type TEXT,
                importance REAL,
                suggested_question TEXT,
                created_at TEXT,
                addressed INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                learned_from TEXT,
                confidence REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_addressed
            ON learning_opportunities(addressed)
        """)

        conn.commit()
        conn.close()

    def identify_uncertainty(self, query: str, response: str,
                             confidence: float) -> Optional[LearningOpportunity]:
        """
        Identify if there's an uncertainty worth addressing.

        Args:
            query: The user's query
            response: SAM's response
            confidence: Confidence in the response

        Returns:
            LearningOpportunity if uncertainty found, None otherwise
        """
        if confidence > 0.8:
            return None  # Confident enough

        # Analyze the type of uncertainty
        uncertainty_type = self._classify_uncertainty(query, response, confidence)

        # Generate a question that would help
        suggested_question = self._generate_learning_question(query, uncertainty_type)

        opportunity = LearningOpportunity(
            id=hashlib.sha256(f"{query}{datetime.now()}".encode()).hexdigest()[:12],
            query=query,
            uncertainty_type=uncertainty_type,
            importance=1.0 - confidence,
            suggested_question=suggested_question
        )

        # Store
        self._save_opportunity(opportunity)
        self.uncertainty_buffer.append(opportunity)

        return opportunity

    def _classify_uncertainty(self, query: str, response: str,
                              confidence: float) -> str:
        """Classify the type of uncertainty"""
        query_lower = query.lower()

        # Check for knowledge gap indicators
        if any(word in query_lower for word in ["what is", "how does", "explain"]):
            return "knowledge_gap"

        # Check for ambiguity
        if "or" in query_lower or len(query.split()) < 5:
            return "ambiguity"

        # Check for missing context
        hedges = ["maybe", "perhaps", "might", "not sure", "depends"]
        if any(hedge in response.lower() for hedge in hedges):
            return "missing_context"

        return "general_uncertainty"

    def _generate_learning_question(self, query: str, uncertainty_type: str) -> str:
        """Generate a question that would help reduce uncertainty"""
        templates = {
            "knowledge_gap": [
                "Could you provide more details about {topic}?",
                "What specific aspect of {topic} would be most helpful?",
                "Do you have examples of {topic} I could learn from?"
            ],
            "ambiguity": [
                "Could you clarify what you mean by '{query}'?",
                "Are you asking about A or B specifically?",
                "What context should I consider for this?"
            ],
            "missing_context": [
                "What's the context for this question?",
                "Are there any constraints I should know about?",
                "What have you tried so far?"
            ],
            "general_uncertainty": [
                "Could you provide more details?",
                "What would be most helpful to know?",
                "Is there specific information I'm missing?"
            ]
        }

        # Extract potential topic from query
        words = query.split()
        topic = " ".join(words[:3]) if len(words) >= 3 else query

        template = random.choice(templates.get(uncertainty_type, templates["general_uncertainty"]))
        return template.format(topic=topic, query=query[:50])

    def _save_opportunity(self, opp: LearningOpportunity):
        """Save opportunity to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO learning_opportunities
            (id, query, uncertainty_type, importance, suggested_question, created_at, addressed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            opp.id, opp.query, opp.uncertainty_type, opp.importance,
            opp.suggested_question, opp.created_at.isoformat(), 1 if opp.addressed else 0
        ))

        conn.commit()
        conn.close()

    def get_top_learning_needs(self, n: int = 5) -> List[LearningOpportunity]:
        """Get top N unaddressed learning opportunities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, query, uncertainty_type, importance, suggested_question, created_at
            FROM learning_opportunities
            WHERE addressed = 0
            ORDER BY importance DESC
            LIMIT ?
        """, (n,))

        opportunities = []
        for row in cursor.fetchall():
            opportunities.append(LearningOpportunity(
                id=row[0],
                query=row[1],
                uncertainty_type=row[2],
                importance=row[3],
                suggested_question=row[4],
                created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now()
            ))

        conn.close()
        return opportunities

    def mark_learned(self, opportunity_id: str, topic: str, source: str):
        """Mark that we learned something"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Mark opportunity as addressed
        cursor.execute(
            "UPDATE learning_opportunities SET addressed = 1 WHERE id = ?",
            (opportunity_id,)
        )

        # Record what we learned
        cursor.execute("""
            INSERT INTO learned_items (topic, learned_from, confidence)
            VALUES (?, ?, 0.8)
        """, (topic, source))

        conn.commit()
        conn.close()

        # Update local state
        for opp in self.uncertainty_buffer:
            if opp.id == opportunity_id:
                opp.addressed = True


@dataclass
class CacheEntry:
    """An entry in the predictive cache"""
    key: str
    content: str
    predicted_need_time: datetime
    actual_use_count: int = 0
    creation_time: datetime = field(default_factory=datetime.now)
    priority: float = 0.5


class PredictiveCache:
    """
    Predictive caching for context.

    Predicts what context will be needed based on:
    1. Usage patterns (what's accessed together)
    2. Time-of-day patterns
    3. Conversation momentum
    4. Goal relevance
    """

    MAX_CACHE_SIZE = 100

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.cache: Dict[str, CacheEntry] = {}
        self.access_patterns: Dict[str, List[str]] = defaultdict(list)
        self.time_patterns: Dict[int, Counter] = defaultdict(Counter)  # hour -> topics

    def _init_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                hour INTEGER,
                day_of_week INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_access (
                key1 TEXT,
                key2 TEXT,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (key1, key2)
            )
        """)

        conn.commit()
        conn.close()

    def record_access(self, key: str, related_keys: Optional[List[str]] = None):
        """Record that a key was accessed"""
        now = datetime.now()

        # Log access
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO access_log (key, hour, day_of_week)
            VALUES (?, ?, ?)
        """, (key, now.hour, now.weekday()))

        # Record co-accesses
        if related_keys:
            for related in related_keys:
                cursor.execute("""
                    INSERT INTO co_access (key1, key2, count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(key1, key2) DO UPDATE SET count = count + 1
                """, (key, related))

        conn.commit()
        conn.close()

        # Update in-memory patterns
        self.time_patterns[now.hour][key] += 1
        if related_keys:
            self.access_patterns[key].extend(related_keys)

        # Update cache if entry exists
        if key in self.cache:
            self.cache[key].actual_use_count += 1

    def predict_needed(self, current_context: str, current_hour: Optional[int] = None,
                       n: int = 5) -> List[str]:
        """
        Predict what keys will likely be needed next.

        Args:
            current_context: Current conversation context
            current_hour: Hour of day (default: now)
            n: Number of predictions

        Returns:
            List of predicted keys
        """
        if current_hour is None:
            current_hour = datetime.now().hour

        predictions: Counter = Counter()

        # Factor 1: Co-access patterns
        context_words = set(current_context.lower().split())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for word in list(context_words)[:10]:
            cursor.execute("""
                SELECT key2, count FROM co_access
                WHERE key1 LIKE ?
                ORDER BY count DESC
                LIMIT 5
            """, (f"%{word}%",))
            for row in cursor.fetchall():
                predictions[row[0]] += row[1]

        # Factor 2: Time-of-day patterns
        cursor.execute("""
            SELECT key, COUNT(*) as cnt FROM access_log
            WHERE hour = ?
            GROUP BY key
            ORDER BY cnt DESC
            LIMIT 10
        """, (current_hour,))
        for row in cursor.fetchall():
            predictions[row[0]] += row[1] * 0.5

        conn.close()

        # Factor 3: Recent access patterns (in-memory)
        for key, related in self.access_patterns.items():
            if any(w in current_context.lower() for w in key.lower().split()):
                for r in related[-5:]:
                    predictions[r] += 1

        # Return top predictions
        return [key for key, _ in predictions.most_common(n)]

    def pre_warm(self, keys: List[str], content_getter: callable):
        """
        Pre-warm the cache with predicted content.

        Args:
            keys: Keys to pre-warm
            content_getter: Function to get content for a key
        """
        for key in keys:
            if key not in self.cache:
                try:
                    content = content_getter(key)
                    if content:
                        self.cache[key] = CacheEntry(
                            key=key,
                            content=content,
                            predicted_need_time=datetime.now() + timedelta(minutes=5),
                            priority=0.7
                        )
                except Exception:
                    pass

        # Evict if over size
        self._evict_if_needed()

    def get(self, key: str) -> Optional[str]:
        """Get content from cache"""
        if key in self.cache:
            self.cache[key].actual_use_count += 1
            return self.cache[key].content
        return None

    def _evict_if_needed(self):
        """Evict low-priority entries if cache is full"""
        if len(self.cache) <= self.MAX_CACHE_SIZE:
            return

        # Sort by priority and use count
        entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].priority * (1 + x[1].actual_use_count * 0.1)
        )

        # Remove bottom 20%
        to_remove = len(self.cache) - int(self.MAX_CACHE_SIZE * 0.8)
        for key, _ in entries[:to_remove]:
            del self.cache[key]


class SleepConsolidator:
    """
    Background memory consolidation (like human sleep).

    Periodically:
    1. Reorganizes memories by similarity
    2. Merges duplicate/similar entries
    3. Rebuilds indices for speed
    4. Removes orphaned data
    5. Updates statistics
    """

    def __init__(self, memory_db_path: str = "/Volumes/David External/sam_memory"):
        self.memory_path = Path(memory_db_path)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_consolidation: Optional[datetime] = None
        self.consolidation_interval = timedelta(hours=6)  # Run every 6 hours

    def start_background(self):
        """Start background consolidation thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop background consolidation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _consolidation_loop(self):
        """Main consolidation loop"""
        while self.running:
            # Check if consolidation is due
            if self._should_consolidate():
                self.consolidate()

            # Sleep for a while
            time.sleep(300)  # Check every 5 minutes

    def _should_consolidate(self) -> bool:
        """Check if consolidation is due"""
        if self.last_consolidation is None:
            return True
        return datetime.now() - self.last_consolidation > self.consolidation_interval

    def consolidate(self) -> Dict[str, Any]:
        """
        Run consolidation process.

        Returns statistics about what was done.
        """
        stats = {
            "start_time": datetime.now().isoformat(),
            "duplicates_merged": 0,
            "orphans_removed": 0,
            "indices_rebuilt": 0,
            "clusters_formed": 0
        }

        # Find all SQLite databases
        db_files = list(self.memory_path.glob("*.db"))

        for db_path in db_files:
            try:
                db_stats = self._consolidate_db(db_path)
                for key in ["duplicates_merged", "orphans_removed"]:
                    stats[key] += db_stats.get(key, 0)
            except Exception as e:
                stats[f"error_{db_path.name}"] = str(e)

        stats["end_time"] = datetime.now().isoformat()
        self.last_consolidation = datetime.now()

        # Log consolidation
        self._log_consolidation(stats)

        return stats

    def _consolidate_db(self, db_path: Path) -> Dict[str, int]:
        """Consolidate a single database"""
        stats = {"duplicates_merged": 0, "orphans_removed": 0}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            # Skip system tables
            if table.startswith("sqlite_"):
                continue

            # Find and merge duplicates (content-based)
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]

                # Look for content/text columns
                content_cols = [c for c in columns if 'content' in c.lower() or 'text' in c.lower()]

                for col in content_cols:
                    # Find exact duplicates
                    cursor.execute(f"""
                        SELECT {col}, COUNT(*) as cnt, GROUP_CONCAT(rowid) as ids
                        FROM {table}
                        WHERE {col} IS NOT NULL
                        GROUP BY {col}
                        HAVING cnt > 1
                    """)

                    for row in cursor.fetchall():
                        ids = row[2].split(",")
                        # Keep first, delete rest
                        for id_to_delete in ids[1:]:
                            cursor.execute(f"DELETE FROM {table} WHERE rowid = ?", (id_to_delete,))
                            stats["duplicates_merged"] += 1

            except Exception:
                continue

        # Vacuum to reclaim space
        conn.commit()
        try:
            conn.execute("VACUUM")
        except Exception:
            pass

        conn.close()
        return stats

    def _log_consolidation(self, stats: Dict[str, Any]):
        """Log consolidation results"""
        log_path = self.memory_path / "consolidation_log.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(stats) + "\n")


class EnhancedLearningSystem:
    """
    Unified enhanced learning system.

    Combines:
    - Active learning (identifying what to learn)
    - Predictive caching (pre-loading context)
    - Sleep consolidation (background maintenance)
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory"):
        self.active_learner = ActiveLearner(f"{db_path}/active_learning.db")
        self.predictive_cache = PredictiveCache(f"{db_path}/cache.db")
        self.consolidator = SleepConsolidator(db_path)

        # Start background consolidation
        self.consolidator.start_background()

    def process_interaction(self, query: str, response: str,
                            confidence: float, context_keys: List[str] = None):
        """
        Process an interaction for learning.

        Args:
            query: User's query
            response: SAM's response
            confidence: Confidence in response
            context_keys: Keys of context that was used
        """
        # Check for learning opportunities
        opportunity = self.active_learner.identify_uncertainty(query, response, confidence)

        # Record access patterns
        if context_keys:
            for key in context_keys:
                self.predictive_cache.record_access(key, context_keys)

    def get_learning_suggestions(self, n: int = 3) -> List[str]:
        """Get suggestions for what SAM should learn"""
        opportunities = self.active_learner.get_top_learning_needs(n)
        return [opp.suggested_question for opp in opportunities]

    def predict_context(self, current_context: str) -> List[str]:
        """Predict what context will be needed"""
        return self.predictive_cache.predict_needed(current_context)

    def get_cached(self, key: str) -> Optional[str]:
        """Get cached content"""
        return self.predictive_cache.get(key)

    def run_maintenance(self) -> Dict[str, Any]:
        """Run manual maintenance (consolidation)"""
        return self.consolidator.consolidate()

    def stop(self):
        """Stop background processes"""
        self.consolidator.stop()


# Convenience function
def create_learning_system() -> EnhancedLearningSystem:
    """Create an enhanced learning system with default settings"""
    return EnhancedLearningSystem()


if __name__ == "__main__":
    # Demo
    system = create_learning_system()

    # Simulate interactions
    system.process_interaction(
        query="How do I implement vector search?",
        response="You can use FAISS or hnswlib for vector search...",
        confidence=0.6,
        context_keys=["vector_search", "embeddings", "similarity"]
    )

    system.process_interaction(
        query="What's the best database for this?",
        response="It depends on your requirements...",
        confidence=0.4,
        context_keys=["database", "storage"]
    )

    # Get learning suggestions
    print("Learning suggestions:")
    for suggestion in system.get_learning_suggestions():
        print(f"  - {suggestion}")

    # Predict context
    predictions = system.predict_context("implementing vector database")
    print(f"\nPredicted context needs: {predictions}")

    # Clean up
    system.stop()
