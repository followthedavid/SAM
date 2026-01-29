#!/usr/bin/env python3
"""
SAM Intelligence Core - Phase 1 Complete

Integrates:
1. Knowledge Distillation - Capture Claude's reasoning
2. Feedback Learning - Learn from user corrections
3. Cross-Session Memory - Remember facts about user

This is the brain's learning layer.

Usage:
    from learn.intelligence_core import IntelligenceCore
    core = IntelligenceCore()

    # Capture Claude escalation
    core.capture_escalation(query, sam_attempt, claude_response)

    # Record feedback
    core.record_feedback(response_id, rating, correction)

    # Get user facts
    facts = core.get_user_facts(user_id)

    # Remember a new fact
    core.remember_fact(user_id, "David prefers Python over JavaScript", "preference")
"""

import os
import sys
import json
import sqlite3
import hashlib
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Storage paths
DB_PATH = Path("/Volumes/David External/sam_memory/intelligence_core.db")
DISTILLED_PATH = Path("/Volumes/David External/sam_training/distilled")


class FactCategory(Enum):
    PREFERENCE = "preference"      # User preferences (likes Python, prefers dark mode)
    BIOGRAPHICAL = "biographical"  # Info about user (name, location, job)
    PROJECT = "project"           # Project-related (working on SAM, uses Tauri)
    SKILL = "skill"               # User skills (knows Rust, learning ML)
    CORRECTION = "correction"     # Things SAM got wrong (don't suggest X)
    CONTEXT = "context"           # Session context (was debugging Y yesterday)


class FeedbackRating(Enum):
    HELPFUL = "helpful"           # 👍 Good response
    NOT_HELPFUL = "not_helpful"   # 👎 Bad response
    WRONG = "wrong"               # Factually incorrect
    CORRECTED = "corrected"       # User provided correction


@dataclass
class UserFact:
    """A fact about the user."""
    id: str
    user_id: str
    fact: str
    category: FactCategory
    confidence: float  # 0.0 - 1.0
    source: str  # Where we learned this
    created_at: datetime
    last_confirmed: datetime
    confirmation_count: int


@dataclass
class ResponseFeedback:
    """Feedback on a SAM response."""
    id: str
    response_id: str
    query: str
    response: str
    rating: FeedbackRating
    correction: Optional[str]
    user_id: str
    timestamp: datetime


@dataclass
class DistilledExample:
    """A training example from Claude escalation."""
    id: str
    query: str
    sam_attempt: Optional[str]
    claude_response: str
    reasoning_extracted: List[str]
    domain: str
    quality_score: float
    timestamp: datetime


class IntelligenceCore:
    """
    The learning core of SAM's intelligence.

    Three pillars:
    1. Distillation - Learn from Claude
    2. Feedback - Learn from corrections
    3. Memory - Remember user facts
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # User facts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                fact TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence REAL DEFAULT 0.7,
                source TEXT,
                created_at REAL,
                last_confirmed REAL,
                confirmation_count INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_facts_user ON user_facts(user_id)")

        # Response feedback table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS response_feedback (
                id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL,
                query TEXT,
                response TEXT,
                rating TEXT NOT NULL,
                correction TEXT,
                user_id TEXT,
                timestamp REAL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON response_feedback(rating)")

        # Distilled examples table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS distilled_examples (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                sam_attempt TEXT,
                claude_response TEXT NOT NULL,
                reasoning_extracted TEXT,
                domain TEXT,
                quality_score REAL DEFAULT 0.8,
                timestamp REAL,
                exported INTEGER DEFAULT 0
            )
        """)

        # Confidence adjustments (track per-topic confidence)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confidence_adjustments (
                topic TEXT PRIMARY KEY,
                adjustment REAL DEFAULT 0.0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                last_updated REAL
            )
        """)

        conn.commit()
        conn.close()

    # =========================================================================
    # DISTILLATION - Capture Claude's reasoning
    # =========================================================================

    def capture_escalation(
        self,
        query: str,
        sam_attempt: Optional[str],
        claude_response: str,
        domain: str = "general"
    ) -> str:
        """
        Capture a Claude escalation for distillation.
        Extracts reasoning patterns and stores for training.
        """
        # Extract reasoning steps from Claude's response
        reasoning = self._extract_reasoning(claude_response)

        # Estimate quality
        quality = self._estimate_quality(claude_response, reasoning)

        # Generate ID
        example_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:12]

        # Store
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO distilled_examples
            (id, query, sam_attempt, claude_response, reasoning_extracted, domain, quality_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            example_id, query, sam_attempt, claude_response,
            json.dumps(reasoning), domain, quality, time.time()
        ))

        conn.commit()
        conn.close()

        return example_id

    def _extract_reasoning(self, response: str) -> List[str]:
        """Extract step-by-step reasoning from response."""
        reasoning = []

        # Pattern 1: Numbered steps
        numbered = re.findall(r'(?:^|\n)\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.|\n\n|$)', response, re.DOTALL)
        for _, step in numbered:
            step_clean = step.strip()[:300]
            if len(step_clean) > 20:
                reasoning.append(step_clean)

        # Pattern 2: Transition words
        if not reasoning:
            transitions = re.findall(
                r'(?:First|Then|Next|After that|Finally|Therefore)[,:]?\s*(.+?)(?=(?:First|Then|Next|After|Finally|Therefore|\n\n|$))',
                response, re.IGNORECASE | re.DOTALL
            )
            for step in transitions:
                step_clean = step.strip()[:300]
                if len(step_clean) > 20:
                    reasoning.append(step_clean)

        # Pattern 3: Paragraphs as steps
        if not reasoning:
            paragraphs = [p.strip() for p in response.split('\n\n') if len(p.strip()) > 50]
            reasoning = [p[:300] for p in paragraphs[:5]]

        return reasoning[:10]  # Max 10 steps

    def _estimate_quality(self, response: str, reasoning: List[str]) -> float:
        """Estimate quality of the response for training value."""
        score = 0.7  # Base score

        # Longer, detailed responses are better
        word_count = len(response.split())
        if word_count > 100:
            score += 0.1
        if word_count > 300:
            score += 0.1

        # Has code examples
        if '```' in response:
            score += 0.1

        # Has clear reasoning steps
        if len(reasoning) >= 3:
            score += 0.1

        # Penalize very short responses
        if word_count < 30:
            score -= 0.3

        return max(0.3, min(1.0, score))

    def get_distillation_stats(self) -> Dict:
        """Get statistics on distilled examples."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM distilled_examples")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM distilled_examples WHERE exported = 0")
        unexported = cur.fetchone()[0]

        cur.execute("SELECT AVG(quality_score) FROM distilled_examples")
        avg_quality = cur.fetchone()[0] or 0.0

        cur.execute("SELECT domain, COUNT(*) FROM distilled_examples GROUP BY domain")
        by_domain = dict(cur.fetchall())

        conn.close()

        return {
            "total": total,
            "unexported": unexported,
            "average_quality": round(avg_quality, 2),
            "by_domain": by_domain
        }

    def export_for_training(self, output_path: Path = None) -> int:
        """Export distilled examples to JSONL for training."""
        if output_path is None:
            output_path = DISTILLED_PATH / f"distilled_{datetime.now().strftime('%Y%m%d')}.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, query, sam_attempt, claude_response, reasoning_extracted, domain
            FROM distilled_examples
            WHERE exported = 0 AND quality_score >= 0.6
        """)

        count = 0
        ids_exported = []

        with open(output_path, 'w') as f:
            for row in cur.fetchall():
                example_id, query, sam_attempt, claude_response, reasoning_json, domain = row
                reasoning = json.loads(reasoning_json) if reasoning_json else []

                # Format as instruction example
                example = {
                    "instruction": query,
                    "input": "",
                    "output": claude_response,
                    "reasoning_steps": reasoning,
                    "domain": domain,
                    "type": "distilled"
                }

                f.write(json.dumps(example) + "\n")
                ids_exported.append(example_id)
                count += 1

        # Mark as exported
        if ids_exported:
            placeholders = ','.join('?' * len(ids_exported))
            cur.execute(f"UPDATE distilled_examples SET exported = 1 WHERE id IN ({placeholders})", ids_exported)
            conn.commit()

        conn.close()
        return count

    # =========================================================================
    # FEEDBACK LEARNING - Learn from corrections
    # =========================================================================

    def record_feedback(
        self,
        response_id: str,
        query: str,
        response: str,
        rating: str,
        correction: Optional[str] = None,
        user_id: str = "default"
    ) -> str:
        """Record user feedback on a response."""

        feedback_id = hashlib.md5(f"{response_id}{time.time()}".encode()).hexdigest()[:12]

        try:
            rating_enum = FeedbackRating(rating)
        except ValueError:
            rating_enum = FeedbackRating.NOT_HELPFUL

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO response_feedback
            (id, response_id, query, response, rating, correction, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_id, response_id, query, response,
            rating_enum.value, correction, user_id, time.time()
        ))

        conn.commit()
        conn.close()

        # Process the feedback
        self._process_feedback(query, response, rating_enum, correction, user_id)

        return feedback_id

    def _process_feedback(
        self,
        query: str,
        response: str,
        rating: FeedbackRating,
        correction: Optional[str],
        user_id: str
    ):
        """Process feedback to improve future responses."""

        # Extract topic from query
        topic = self._extract_topic(query)

        # Adjust confidence for this topic
        adjustment = {
            FeedbackRating.HELPFUL: 0.05,
            FeedbackRating.NOT_HELPFUL: -0.1,
            FeedbackRating.WRONG: -0.2,
            FeedbackRating.CORRECTED: -0.15,
        }.get(rating, 0)

        self._adjust_confidence(topic, adjustment, rating == FeedbackRating.HELPFUL)

        # If corrected, remember the correction as a fact
        if correction and rating in [FeedbackRating.WRONG, FeedbackRating.CORRECTED]:
            self.remember_fact(
                user_id,
                f"When asked about '{query[:50]}...', the correct answer involves: {correction[:200]}",
                FactCategory.CORRECTION,
                source="user_correction"
            )

        # Generate training example from correction
        if correction:
            self._create_correction_example(query, response, correction)

    def _extract_topic(self, query: str) -> str:
        """Extract main topic from query for confidence tracking."""
        # Simple extraction - first few significant words
        words = re.findall(r'\b\w{4,}\b', query.lower())[:3]
        return '_'.join(words) if words else "general"

    def _adjust_confidence(self, topic: str, adjustment: float, is_positive: bool):
        """Adjust confidence for a topic based on feedback."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT adjustment FROM confidence_adjustments WHERE topic = ?", (topic,))
        row = cur.fetchone()

        if row:
            new_adjustment = max(-0.5, min(0.5, row[0] + adjustment))
            if is_positive:
                cur.execute("""
                    UPDATE confidence_adjustments
                    SET adjustment = ?, positive_count = positive_count + 1, last_updated = ?
                    WHERE topic = ?
                """, (new_adjustment, time.time(), topic))
            else:
                cur.execute("""
                    UPDATE confidence_adjustments
                    SET adjustment = ?, negative_count = negative_count + 1, last_updated = ?
                    WHERE topic = ?
                """, (new_adjustment, time.time(), topic))
        else:
            cur.execute("""
                INSERT INTO confidence_adjustments (topic, adjustment, positive_count, negative_count, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (topic, adjustment, 1 if is_positive else 0, 0 if is_positive else 1, time.time()))

        conn.commit()
        conn.close()

    def get_confidence_adjustment(self, query: str) -> float:
        """Get confidence adjustment for a query based on past feedback."""
        topic = self._extract_topic(query)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT adjustment FROM confidence_adjustments WHERE topic = ?", (topic,))
        row = cur.fetchone()

        conn.close()

        return row[0] if row else 0.0

    def _create_correction_example(self, query: str, wrong_response: str, correction: str):
        """Create a training example from a user correction."""
        example_id = hashlib.md5(f"correction_{query}{time.time()}".encode()).hexdigest()[:12]

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Store as a preference pair (wrong vs corrected)
        cur.execute("""
            INSERT INTO distilled_examples
            (id, query, sam_attempt, claude_response, reasoning_extracted, domain, quality_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            example_id, query, wrong_response, correction,
            json.dumps(["User correction: " + correction[:200]]),
            "correction", 0.9, time.time()
        ))

        conn.commit()
        conn.close()

    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT rating, COUNT(*) FROM response_feedback GROUP BY rating")
        by_rating = dict(cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM response_feedback")
        total = cur.fetchone()[0]

        # Topics with worst confidence
        cur.execute("""
            SELECT topic, adjustment FROM confidence_adjustments
            WHERE adjustment < 0 ORDER BY adjustment LIMIT 5
        """)
        struggling_topics = cur.fetchall()

        conn.close()

        helpful = by_rating.get('helpful', 0)
        total_rated = sum(by_rating.values()) or 1

        return {
            "total_feedback": total,
            "by_rating": by_rating,
            "helpful_rate": round(helpful / total_rated * 100, 1),
            "struggling_topics": [{"topic": t, "adjustment": a} for t, a in struggling_topics]
        }

    # =========================================================================
    # CROSS-SESSION MEMORY - Remember facts about user
    # =========================================================================

    def remember_fact(
        self,
        user_id: str,
        fact: str,
        category: FactCategory,
        confidence: float = 0.7,
        source: str = "conversation"
    ) -> str:
        """Remember a fact about the user."""

        # Normalize the fact for deduplication
        normalized = re.sub(r'\s+', ' ', fact.lower().strip())
        fact_id = hashlib.md5(f"{user_id}:{normalized}".encode()).hexdigest()[:12]

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Check if fact exists
        cur.execute("SELECT id, confirmation_count, confidence FROM user_facts WHERE id = ?", (fact_id,))
        existing = cur.fetchone()

        if existing:
            # Reinforce existing fact
            new_count = existing[1] + 1
            new_confidence = min(1.0, existing[2] + 0.1)
            cur.execute("""
                UPDATE user_facts
                SET last_confirmed = ?, confirmation_count = ?, confidence = ?
                WHERE id = ?
            """, (time.time(), new_count, new_confidence, fact_id))
        else:
            # New fact
            cur.execute("""
                INSERT INTO user_facts
                (id, user_id, fact, category, confidence, source, created_at, last_confirmed, confirmation_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                fact_id, user_id, fact, category.value if isinstance(category, FactCategory) else category,
                confidence, source, time.time(), time.time()
            ))

        conn.commit()
        conn.close()

        return fact_id

    def get_user_facts(
        self,
        user_id: str,
        category: Optional[FactCategory] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """Get facts about a user."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        query = """
            SELECT id, fact, category, confidence, source, created_at, last_confirmed, confirmation_count
            FROM user_facts
            WHERE user_id = ? AND is_active = 1 AND confidence >= ?
        """
        params = [user_id, min_confidence]

        if category:
            query += " AND category = ?"
            params.append(category.value if isinstance(category, FactCategory) else category)

        query += " ORDER BY confidence DESC, last_confirmed DESC"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [{
            "id": row[0],
            "fact": row[1],
            "category": row[2],
            "confidence": row[3],
            "source": row[4],
            "created_at": datetime.fromtimestamp(row[5]).isoformat(),
            "last_confirmed": datetime.fromtimestamp(row[6]).isoformat(),
            "confirmation_count": row[7]
        } for row in rows]

    def forget_fact(self, fact_id: str):
        """Mark a fact as inactive (forgotten)."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE user_facts SET is_active = 0 WHERE id = ?", (fact_id,))
        conn.commit()
        conn.close()

    def decay_facts(self, days_threshold: int = 30):
        """Reduce confidence of facts not confirmed recently."""
        threshold = time.time() - (days_threshold * 24 * 60 * 60)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Reduce confidence of old unconfirmed facts
        cur.execute("""
            UPDATE user_facts
            SET confidence = confidence * 0.9
            WHERE last_confirmed < ? AND confidence > 0.3
        """, (threshold,))

        # Deactivate very low confidence facts
        cur.execute("UPDATE user_facts SET is_active = 0 WHERE confidence < 0.2")

        conn.commit()
        conn.close()

    def extract_facts_from_conversation(self, user_id: str, query: str, response: str) -> List[str]:
        """Extract potential facts from a conversation."""
        facts_found = []
        query_lower = query.lower()

        # Preference patterns
        preference_patterns = [
            (r"i (?:prefer|like|love|enjoy|use) (.+?)(?:\.|,|$)", FactCategory.PREFERENCE),
            (r"i (?:don't|hate|dislike|avoid) (.+?)(?:\.|,|$)", FactCategory.PREFERENCE),
            (r"my (?:favorite|preferred) (?:\w+ )?is (.+?)(?:\.|,|$)", FactCategory.PREFERENCE),
        ]

        # Biographical patterns
        bio_patterns = [
            (r"my name is (\w+)", FactCategory.BIOGRAPHICAL),
            (r"i(?:'m| am) (?:a |an )?(\w+ ?\w*?)(?:\.|,| and|$)", FactCategory.BIOGRAPHICAL),
            (r"i work (?:at|for|on) (.+?)(?:\.|,|$)", FactCategory.BIOGRAPHICAL),
            (r"i live in (.+?)(?:\.|,|$)", FactCategory.BIOGRAPHICAL),
        ]

        # Project patterns
        project_patterns = [
            (r"(?:working on|building|developing) (.+?)(?:\.|,|$)", FactCategory.PROJECT),
            (r"my (?:project|app|tool) (?:is |called )?(.+?)(?:\.|,|$)", FactCategory.PROJECT),
        ]

        all_patterns = preference_patterns + bio_patterns + project_patterns

        for pattern, category in all_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                if len(match) > 3 and len(match) < 100:
                    fact = match.strip()
                    fact_id = self.remember_fact(user_id, fact, category, confidence=0.6, source="conversation")
                    facts_found.append(fact_id)

        return facts_found

    def get_context_for_user(self, user_id: str, limit: int = 10) -> str:
        """Get formatted context about user for prompt injection."""
        facts = self.get_user_facts(user_id, min_confidence=0.6)[:limit]

        if not facts:
            return ""

        context_lines = ["[User Context]"]

        for fact in facts:
            context_lines.append(f"- {fact['fact']} ({fact['category']})")

        return "\n".join(context_lines)

    def get_memory_stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM user_facts WHERE is_active = 1")
        total_facts = cur.fetchone()[0]

        cur.execute("SELECT category, COUNT(*) FROM user_facts WHERE is_active = 1 GROUP BY category")
        by_category = dict(cur.fetchall())

        cur.execute("SELECT AVG(confidence) FROM user_facts WHERE is_active = 1")
        avg_confidence = cur.fetchone()[0] or 0.0

        cur.execute("SELECT COUNT(DISTINCT user_id) FROM user_facts")
        unique_users = cur.fetchone()[0]

        conn.close()

        return {
            "total_facts": total_facts,
            "by_category": by_category,
            "average_confidence": round(avg_confidence, 2),
            "unique_users": unique_users
        }

    # =========================================================================
    # UNIFIED STATS
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get comprehensive intelligence stats."""
        return {
            "distillation": self.get_distillation_stats(),
            "feedback": self.get_feedback_stats(),
            "memory": self.get_memory_stats()
        }


# Singleton instance
_intelligence_core = None

def get_intelligence_core() -> IntelligenceCore:
    """Get singleton intelligence core."""
    global _intelligence_core
    if _intelligence_core is None:
        _intelligence_core = IntelligenceCore()
    return _intelligence_core


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Intelligence Core")
    parser.add_argument("command", choices=["stats", "facts", "export", "decay", "test"])
    parser.add_argument("--user", default="david")
    args = parser.parse_args()

    core = get_intelligence_core()

    if args.command == "stats":
        stats = core.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == "facts":
        facts = core.get_user_facts(args.user)
        print(f"\nFacts about {args.user}:")
        for f in facts:
            print(f"  [{f['category']}] {f['fact']} (conf: {f['confidence']:.0%})")

    elif args.command == "export":
        count = core.export_for_training()
        print(f"Exported {count} examples for training")

    elif args.command == "decay":
        core.decay_facts()
        print("Decayed old facts")

    elif args.command == "test":
        # Test all three pillars
        print("Testing Intelligence Core...\n")

        # Test distillation
        eid = core.capture_escalation(
            "How do I implement a binary search?",
            "I think you use divide and conquer...",
            "Here's how to implement binary search:\n\n1. First, ensure the array is sorted\n2. Find the middle element\n3. Compare with target...",
            domain="code"
        )
        print(f"✅ Captured escalation: {eid}")

        # Test feedback
        fid = core.record_feedback(
            response_id="test123",
            query="What's the capital of France?",
            response="London",
            rating="wrong",
            correction="Paris",
            user_id="david"
        )
        print(f"✅ Recorded feedback: {fid}")

        # Test memory
        mid = core.remember_fact("david", "David prefers Python over JavaScript", FactCategory.PREFERENCE)
        print(f"✅ Remembered fact: {mid}")

        facts = core.get_user_facts("david")
        print(f"✅ Retrieved {len(facts)} facts about david")

        print("\n" + "="*50)
        print("All tests passed!")
        print("="*50)
