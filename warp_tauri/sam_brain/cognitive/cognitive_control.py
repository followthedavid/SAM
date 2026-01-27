"""
Cognitive Control System for SAM Cognitive Architecture

Implements:
1. Meta-cognition - Confidence estimation, uncertainty quantification
2. Goal Manager - Goal hierarchy, priority management, progress tracking
3. Reasoning Engine - Chain-of-thought, self-consistency, verification
4. Attention Controller - Salience scoring, focus management

These systems coordinate to make SAM "think about thinking"
and manage complex multi-step tasks.
"""

import json
import math
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading


class ConfidenceLevel(Enum):
    """Confidence levels for meta-cognition"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class GoalStatus(Enum):
    """Status of a goal"""
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalPriority(Enum):
    """Goal priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Confidence:
    """Confidence assessment for a response or decision"""
    level: float  # 0-1
    factors: Dict[str, float]  # Contributing factors
    uncertainties: List[str]  # What we're uncertain about
    suggestions: List[str]  # What would increase confidence

    @property
    def category(self) -> ConfidenceLevel:
        """Get categorical confidence level"""
        if self.level >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.level >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.level >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.level >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def to_dict(self) -> Dict:
        return {
            "level": self.level,
            "category": self.category.name,
            "factors": self.factors,
            "uncertainties": self.uncertainties,
            "suggestions": self.suggestions
        }


class MetaCognition:
    """
    Meta-cognitive system for self-awareness and self-monitoring.

    Tracks:
    - Confidence in responses
    - Knowledge boundaries (what we don't know)
    - Reasoning quality
    - Past performance patterns
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/metacognition.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Performance tracking
        self.recent_confidences: deque = deque(maxlen=100)
        self.calibration_data: List[Tuple[float, bool]] = []

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confidence_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                confidence REAL,
                actual_success INTEGER,
                factors TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_boundaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                boundary_type TEXT,
                description TEXT,
                examples TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def estimate_confidence(self, query: str, context: str,
                            response: str) -> Confidence:
        """
        Estimate confidence in a response.

        Factors considered:
        - Query clarity (how clear is the question)
        - Context relevance (how relevant is available context)
        - Response specificity (how specific/hedged is the response)
        - Domain knowledge (do we have knowledge in this area)
        - Past performance (how have we done with similar queries)
        """
        factors = {}

        # 1. Query clarity
        factors["query_clarity"] = self._assess_query_clarity(query)

        # 2. Context relevance
        factors["context_relevance"] = self._assess_context_relevance(query, context)

        # 3. Response specificity
        factors["response_specificity"] = self._assess_response_specificity(response)

        # 4. Domain knowledge
        factors["domain_knowledge"] = self._assess_domain_knowledge(query)

        # 5. Past performance
        factors["past_performance"] = self._get_past_performance(query)

        # Calculate overall confidence
        weights = {
            "query_clarity": 0.15,
            "context_relevance": 0.25,
            "response_specificity": 0.20,
            "domain_knowledge": 0.25,
            "past_performance": 0.15
        }

        overall = sum(factors[k] * weights[k] for k in factors)

        # Identify uncertainties
        uncertainties = []
        if factors["context_relevance"] < 0.5:
            uncertainties.append("Limited relevant context available")
        if factors["domain_knowledge"] < 0.5:
            uncertainties.append("Outside core knowledge domains")
        if factors["query_clarity"] < 0.5:
            uncertainties.append("Query may be ambiguous")

        # Suggestions for improvement
        suggestions = []
        if factors["context_relevance"] < 0.5:
            suggestions.append("Provide more specific context")
        if factors["query_clarity"] < 0.5:
            suggestions.append("Clarify the question")
        if "code" in query.lower() and factors["domain_knowledge"] < 0.7:
            suggestions.append("Specify programming language/framework")

        confidence = Confidence(
            level=overall,
            factors=factors,
            uncertainties=uncertainties,
            suggestions=suggestions
        )

        self.recent_confidences.append(confidence.level)
        return confidence

    def _assess_query_clarity(self, query: str) -> float:
        """Assess how clear/specific the query is"""
        score = 0.5  # Base score

        # Length (too short or too long = unclear)
        words = len(query.split())
        if 5 <= words <= 30:
            score += 0.2
        elif words < 3 or words > 50:
            score -= 0.2

        # Question markers
        if "?" in query:
            score += 0.1

        # Specific terms
        specific_patterns = [
            r'\b(how|what|when|where|why|which)\b',  # Question words
            r'\b(implement|create|fix|build|explain)\b',  # Action words
            r'`[^`]+`',  # Code snippets
            r'\b\d+\b',  # Numbers (specificity)
        ]
        for pattern in specific_patterns:
            import re
            if re.search(pattern, query, re.IGNORECASE):
                score += 0.05

        return min(1.0, max(0.0, score))

    def _assess_context_relevance(self, query: str, context: str) -> float:
        """Assess how relevant the context is to the query"""
        if not context:
            return 0.3  # No context

        # Simple keyword overlap
        query_words = set(query.lower().split())
        context_words = set(context.lower().split())

        # Remove common words
        common = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "for"}
        query_words -= common
        context_words -= common

        if not query_words:
            return 0.5

        overlap = len(query_words & context_words)
        score = min(1.0, overlap / len(query_words) + 0.3)

        return score

    def _assess_response_specificity(self, response: str) -> float:
        """Assess how specific (vs hedged) the response is"""
        score = 0.7  # Base

        # Hedging words reduce confidence
        hedges = ["maybe", "perhaps", "might", "possibly", "could be",
                  "i think", "i'm not sure", "it depends", "generally"]
        for hedge in hedges:
            if hedge in response.lower():
                score -= 0.1

        # Specific details increase confidence
        import re
        if re.search(r'\d+', response):  # Numbers
            score += 0.05
        if re.search(r'`[^`]+`', response):  # Code
            score += 0.1
        if re.search(r'\b(specifically|exactly|precisely)\b', response, re.I):
            score += 0.05

        return min(1.0, max(0.0, score))

    def _assess_domain_knowledge(self, query: str) -> float:
        """Assess if query is in a domain we have knowledge about"""
        # High-confidence domains for SAM
        high_domains = ["python", "code", "programming", "fashion", "personality",
                        "memory", "ai", "machine learning"]
        medium_domains = ["javascript", "rust", "database", "api", "web"]
        low_domains = ["legal", "medical", "financial", "physics", "chemistry"]

        query_lower = query.lower()

        for domain in high_domains:
            if domain in query_lower:
                return 0.85

        for domain in medium_domains:
            if domain in query_lower:
                return 0.65

        for domain in low_domains:
            if domain in query_lower:
                return 0.35

        return 0.5  # Unknown domain

    def _get_past_performance(self, query: str) -> float:
        """Get past performance on similar queries"""
        if len(self.calibration_data) < 10:
            return 0.5  # Not enough data

        # Calculate calibration
        correct = sum(1 for conf, success in self.calibration_data if success)
        total = len(self.calibration_data)

        return correct / total

    def record_outcome(self, query: str, confidence: float, success: bool):
        """Record actual outcome for calibration"""
        self.calibration_data.append((confidence, success))

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query_hash = hashlib.md5(query.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO confidence_history (query_hash, confidence, actual_success)
            VALUES (?, ?, ?)
        """, (query_hash, confidence, 1 if success else 0))

        conn.commit()
        conn.close()

    def get_calibration_stats(self) -> Dict[str, float]:
        """Get calibration statistics"""
        if len(self.calibration_data) < 10:
            return {"status": "insufficient_data", "samples": len(self.calibration_data)}

        # Bin by confidence
        bins = {
            "low": {"count": 0, "correct": 0},
            "medium": {"count": 0, "correct": 0},
            "high": {"count": 0, "correct": 0}
        }

        for conf, success in self.calibration_data:
            if conf < 0.4:
                bin_name = "low"
            elif conf < 0.7:
                bin_name = "medium"
            else:
                bin_name = "high"

            bins[bin_name]["count"] += 1
            if success:
                bins[bin_name]["correct"] += 1

        return {
            "samples": len(self.calibration_data),
            "bins": {
                name: data["correct"] / data["count"] if data["count"] > 0 else 0
                for name, data in bins.items()
            }
        }


@dataclass
class Goal:
    """A goal in the goal hierarchy"""
    id: str
    description: str
    priority: GoalPriority
    status: GoalStatus
    parent_id: Optional[str] = None
    subgoals: List[str] = field(default_factory=list)
    progress: float = 0.0  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "subgoals": self.subgoals,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "metadata": self.metadata
        }


class GoalManager:
    """
    Manages goal hierarchy and progress tracking.

    Features:
    - Hierarchical goals (goals can have subgoals)
    - Priority-based scheduling
    - Progress tracking
    - Deadline management
    - Conflict detection
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/goals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.goal_cache: Dict[str, Goal] = {}
        self._lock = threading.Lock()

    def _init_db(self):
        """Initialize goals database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                priority INTEGER,
                status TEXT,
                parent_id TEXT,
                progress REAL DEFAULT 0,
                created_at TEXT,
                deadline TEXT,
                metadata TEXT,
                FOREIGN KEY (parent_id) REFERENCES goals(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_status
            ON goals(status)
        """)

        conn.commit()
        conn.close()

    def create_goal(self, description: str, priority: GoalPriority = GoalPriority.MEDIUM,
                    parent_id: Optional[str] = None, deadline: Optional[datetime] = None) -> Goal:
        """Create a new goal"""
        goal_id = hashlib.sha256(f"{description}{datetime.now()}".encode()).hexdigest()[:12]

        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority,
            status=GoalStatus.PENDING,
            parent_id=parent_id,
            deadline=deadline
        )

        # Save to database
        self._save_goal(goal)

        # Update parent's subgoals
        if parent_id:
            parent = self.get_goal(parent_id)
            if parent:
                parent.subgoals.append(goal_id)
                self._save_goal(parent)

        return goal

    def _save_goal(self, goal: Goal):
        """Save goal to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO goals
            (id, description, priority, status, parent_id, progress, created_at, deadline, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.id,
            goal.description,
            goal.priority.value,
            goal.status.value,
            goal.parent_id,
            goal.progress,
            goal.created_at.isoformat(),
            goal.deadline.isoformat() if goal.deadline else None,
            json.dumps(goal.metadata)
        ))

        conn.commit()
        conn.close()

        self.goal_cache[goal.id] = goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID"""
        if goal_id in self.goal_cache:
            return self.goal_cache[goal_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            goal = self._row_to_goal(row)
            self.goal_cache[goal_id] = goal
            return goal
        return None

    def _row_to_goal(self, row) -> Goal:
        """Convert database row to Goal"""
        return Goal(
            id=row[0],
            description=row[1],
            priority=GoalPriority(row[2]),
            status=GoalStatus(row[3]),
            parent_id=row[4],
            progress=row[5] or 0,
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            deadline=datetime.fromisoformat(row[7]) if row[7] else None,
            metadata=json.loads(row[8]) if row[8] else {}
        )

    def activate_goal(self, goal_id: str) -> bool:
        """Activate a goal"""
        goal = self.get_goal(goal_id)
        if goal:
            goal.status = GoalStatus.ACTIVE
            self._save_goal(goal)
            return True
        return False

    def update_progress(self, goal_id: str, progress: float):
        """Update goal progress"""
        goal = self.get_goal(goal_id)
        if goal:
            goal.progress = min(1.0, max(0.0, progress))
            if goal.progress >= 1.0:
                goal.status = GoalStatus.COMPLETED
            self._save_goal(goal)

            # Update parent progress
            if goal.parent_id:
                self._update_parent_progress(goal.parent_id)

    def _update_parent_progress(self, parent_id: str):
        """Update parent goal progress based on subgoals"""
        parent = self.get_goal(parent_id)
        if not parent or not parent.subgoals:
            return

        total_progress = 0
        for subgoal_id in parent.subgoals:
            subgoal = self.get_goal(subgoal_id)
            if subgoal:
                total_progress += subgoal.progress

        parent.progress = total_progress / len(parent.subgoals)
        if parent.progress >= 1.0:
            parent.status = GoalStatus.COMPLETED
        self._save_goal(parent)

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals, sorted by priority"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM goals WHERE status = ? ORDER BY priority, created_at",
            (GoalStatus.ACTIVE.value,)
        )
        goals = [self._row_to_goal(row) for row in cursor.fetchall()]
        conn.close()
        return goals

    def get_next_goal(self) -> Optional[Goal]:
        """Get the highest priority active goal"""
        goals = self.get_active_goals()
        return goals[0] if goals else None

    def detect_conflicts(self) -> List[Tuple[Goal, Goal, str]]:
        """Detect conflicting goals"""
        conflicts = []
        active = self.get_active_goals()

        for i, g1 in enumerate(active):
            for g2 in active[i + 1:]:
                # Check for deadline conflicts
                if g1.deadline and g2.deadline:
                    if abs((g1.deadline - g2.deadline).total_seconds()) < 3600:
                        conflicts.append((g1, g2, "deadline_conflict"))

                # Check for same parent (competing siblings)
                if g1.parent_id and g1.parent_id == g2.parent_id:
                    if g1.priority == g2.priority:
                        conflicts.append((g1, g2, "priority_tie"))

        return conflicts


@dataclass
class ReasoningStep:
    """A step in a reasoning chain"""
    step_num: int
    description: str
    reasoning: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)


class ReasoningEngine:
    """
    Engine for structured reasoning.

    Implements:
    - Chain-of-thought prompting
    - Self-consistency (multiple reasoning paths)
    - Verification of reasoning steps
    """

    def __init__(self, llm_generator: Optional[Callable] = None):
        self.llm_generator = llm_generator

    def chain_of_thought(self, problem: str, context: str = "") -> List[ReasoningStep]:
        """
        Break down a problem into reasoning steps.

        Without an LLM, uses heuristic decomposition.
        """
        steps = []

        # Step 1: Understand the problem
        steps.append(ReasoningStep(
            step_num=1,
            description="Understand the problem",
            reasoning=f"The problem is: {problem[:100]}...",
            confidence=0.8
        ))

        # Step 2: Identify key components
        import re
        entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', problem)
        actions = re.findall(r'\b(create|build|fix|implement|update|find|get|make)\b', problem.lower())

        steps.append(ReasoningStep(
            step_num=2,
            description="Identify key components",
            reasoning=f"Entities: {entities[:5]}, Actions: {actions[:3]}",
            confidence=0.7
        ))

        # Step 3: Formulate approach
        if actions:
            approach = f"Primary action: {actions[0]}"
        else:
            approach = "Analyze and respond"

        steps.append(ReasoningStep(
            step_num=3,
            description="Formulate approach",
            reasoning=approach,
            confidence=0.6,
            alternatives=["Alternative: ask for clarification", "Alternative: break into subtasks"]
        ))

        # Step 4: Consider constraints
        if context:
            steps.append(ReasoningStep(
                step_num=4,
                description="Consider context constraints",
                reasoning=f"Context provides: {context[:100]}...",
                confidence=0.7
            ))

        return steps

    def verify_reasoning(self, steps: List[ReasoningStep]) -> Tuple[bool, List[str]]:
        """
        Verify a reasoning chain for consistency.

        Returns (is_valid, issues)
        """
        issues = []

        # Check for decreasing confidence
        for i in range(1, len(steps)):
            if steps[i].confidence < steps[i - 1].confidence * 0.5:
                issues.append(f"Large confidence drop at step {i + 1}")

        # Check for empty reasoning
        for step in steps:
            if len(step.reasoning) < 10:
                issues.append(f"Step {step.step_num} has insufficient reasoning")

        # Check overall confidence
        avg_confidence = sum(s.confidence for s in steps) / len(steps) if steps else 0
        if avg_confidence < 0.5:
            issues.append("Overall confidence is low")

        return len(issues) == 0, issues


class AttentionController:
    """
    Controls what SAM attends to.

    Features:
    - Salience scoring (what's important)
    - Focus management (current attention target)
    - Distraction filtering
    - Attention history
    """

    def __init__(self, focus_duration: int = 5):
        self.current_focus: Optional[str] = None
        self.focus_started: Optional[datetime] = None
        self.focus_duration = focus_duration  # turns before natural attention shift
        self.attention_history: deque = deque(maxlen=50)
        self.salience_scores: Dict[str, float] = {}

    def score_salience(self, items: List[str], current_goal: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Score salience of items.

        Factors:
        - Relevance to current goal
        - Novelty (new items more salient)
        - Recency
        - Emotional valence
        """
        scored = []

        for item in items:
            score = 0.5  # Base

            # Goal relevance
            if current_goal:
                goal_words = set(current_goal.lower().split())
                item_words = set(item.lower().split())
                overlap = len(goal_words & item_words) / (len(goal_words) + 1)
                score += overlap * 0.3

            # Novelty (not in recent history)
            if item not in self.attention_history:
                score += 0.2

            # Contains question (salient)
            if "?" in item:
                score += 0.15

            # Contains urgency words
            urgent_words = {"urgent", "important", "critical", "asap", "immediately"}
            if any(w in item.lower() for w in urgent_words):
                score += 0.2

            scored.append((item, min(1.0, score)))

        # Sort by salience
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def set_focus(self, item: str):
        """Set current attention focus"""
        self.current_focus = item
        self.focus_started = datetime.now()
        self.attention_history.append(item)
        self.salience_scores[item] = 1.0

    def should_shift_attention(self, new_items: List[str]) -> Optional[str]:
        """
        Determine if attention should shift to a new item.

        Returns the item to shift to, or None.
        """
        if not self.current_focus:
            # No current focus, attend to most salient
            scored = self.score_salience(new_items)
            return scored[0][0] if scored else None

        # Check if focus duration exceeded
        if self.focus_started:
            elapsed = datetime.now() - self.focus_started
            if elapsed.total_seconds() > self.focus_duration * 60:
                # Natural attention shift
                scored = self.score_salience(new_items)
                if scored and scored[0][1] > 0.7:
                    return scored[0][0]

        # Check for high-salience interrupts
        scored = self.score_salience(new_items, self.current_focus)
        for item, salience in scored:
            if salience > 0.9:  # Very high salience = interrupt
                return item

        return None  # Stay focused

    def get_attention_state(self) -> Dict[str, Any]:
        """Get current attention state"""
        return {
            "current_focus": self.current_focus,
            "focus_duration": (datetime.now() - self.focus_started).total_seconds()
            if self.focus_started else 0,
            "recent_history": list(self.attention_history)[-5:],
            "salience_scores": dict(list(self.salience_scores.items())[-10:])
        }


# Unified cognitive control interface
class CognitiveControl:
    """
    Unified interface to all cognitive control systems.
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory"):
        self.metacognition = MetaCognition(f"{db_path}/metacognition.db")
        self.goal_manager = GoalManager(f"{db_path}/goals.db")
        self.reasoning = ReasoningEngine()
        self.attention = AttentionController()

    def process_query(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Process a query through the cognitive control system.

        Returns cognitive assessment including:
        - Confidence estimate
        - Relevant goals
        - Attention state
        - Reasoning steps (if complex)
        """
        # Estimate confidence
        confidence = self.metacognition.estimate_confidence(query, context, "")

        # Check goal relevance
        active_goals = self.goal_manager.get_active_goals()
        relevant_goals = [g for g in active_goals
                         if any(w in g.description.lower()
                                for w in query.lower().split()[:5])]

        # Update attention
        shift = self.attention.should_shift_attention([query])
        if shift:
            self.attention.set_focus(query)

        # Generate reasoning steps for complex queries
        reasoning_steps = []
        if len(query.split()) > 10 or "?" in query:
            reasoning_steps = self.reasoning.chain_of_thought(query, context)

        return {
            "confidence": confidence.to_dict(),
            "relevant_goals": [g.to_dict() for g in relevant_goals],
            "attention_state": self.attention.get_attention_state(),
            "reasoning_steps": [
                {"step": s.step_num, "description": s.description,
                 "reasoning": s.reasoning, "confidence": s.confidence}
                for s in reasoning_steps
            ]
        }


if __name__ == "__main__":
    # Demo
    control = CognitiveControl()

    # Create some goals
    main_goal = control.goal_manager.create_goal(
        "Build complete cognitive system for SAM",
        priority=GoalPriority.HIGH
    )
    control.goal_manager.activate_goal(main_goal.id)

    sub1 = control.goal_manager.create_goal(
        "Implement memory layer",
        parent_id=main_goal.id
    )
    control.goal_manager.activate_goal(sub1.id)
    control.goal_manager.update_progress(sub1.id, 1.0)

    sub2 = control.goal_manager.create_goal(
        "Implement retrieval layer",
        parent_id=main_goal.id
    )
    control.goal_manager.activate_goal(sub2.id)
    control.goal_manager.update_progress(sub2.id, 0.5)

    # Process a query
    result = control.process_query(
        "How do I implement the compression system?",
        context="Building SAM cognitive architecture on 8GB Mac"
    )

    print("Cognitive Assessment:")
    print(json.dumps(result, indent=2, default=str))
