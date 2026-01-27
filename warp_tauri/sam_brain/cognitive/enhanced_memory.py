"""
Enhanced Memory System for SAM Cognitive Architecture

Implements:
1. Working Memory with 7±2 cognitive limit
2. Memory decay and forgetting mechanisms
3. Procedural Memory (skills and habits)
4. Importance scoring for retention decisions

Integrates with existing:
- semantic_memory.py (vector embeddings)
- conversation_memory.py (multi-tier storage)
- infinite_context.py (hierarchical state)
"""

import json
import math
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading


class MemoryType(Enum):
    """Types of memory items"""
    FACT = "fact"           # Declarative knowledge
    EVENT = "event"         # Episodic memory
    SKILL = "skill"         # Procedural knowledge
    GOAL = "goal"           # Active goals
    CONTEXT = "context"     # Current context items
    ENTITY = "entity"       # People, places, things


@dataclass
class MemoryItem:
    """A single item in working or long-term memory"""
    id: str
    content: str
    memory_type: MemoryType
    importance: float  # 0-1, affects retention
    activation: float  # Current activation level (decays over time)
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    associations: List[str] = field(default_factory=list)  # IDs of related items
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_accessed, str):
            self.last_accessed = datetime.fromisoformat(self.last_accessed)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "activation": self.activation,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "associations": self.associations,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryItem":
        return cls(**data)


class WorkingMemory:
    """
    Working memory with cognitive limits.

    Implements Miller's Law: humans can hold 7±2 items in working memory.
    Uses activation-based decay and importance-weighted retention.
    """

    # Cognitive limits
    MIN_CAPACITY = 5
    MAX_CAPACITY = 9
    DEFAULT_CAPACITY = 7

    # Decay parameters
    DECAY_RATE = 0.1  # Per turn
    REHEARSAL_BOOST = 0.3  # Activation boost when item is accessed

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self.capacity = max(self.MIN_CAPACITY, min(capacity, self.MAX_CAPACITY))
        self.items: deque[MemoryItem] = deque(maxlen=self.MAX_CAPACITY)
        self.focus_id: Optional[str] = None  # Currently focused item
        self._lock = threading.Lock()

    def add(self, content: str, memory_type: MemoryType = MemoryType.CONTEXT,
            importance: float = 0.5, metadata: Optional[Dict] = None) -> MemoryItem:
        """Add item to working memory, possibly displacing lowest-activation item"""
        with self._lock:
            # Create new item with full activation
            item = MemoryItem(
                id=self._generate_id(content),
                content=content,
                memory_type=memory_type,
                importance=importance,
                activation=1.0,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                metadata=metadata or {}
            )

            # Check if we're at capacity
            if len(self.items) >= self.capacity:
                # Find item with lowest activation * importance
                min_score = float('inf')
                min_idx = 0
                for i, existing in enumerate(self.items):
                    score = existing.activation * existing.importance
                    if score < min_score:
                        min_score = score
                        min_idx = i

                # Only displace if new item has higher score
                new_score = item.activation * item.importance
                if new_score > min_score:
                    # Remove lowest scoring item
                    displaced = self.items[min_idx]
                    del self.items[min_idx]
                    # Return displaced item for potential long-term storage
                    item.metadata['displaced'] = displaced.to_dict()

            self.items.append(item)
            return item

    def access(self, item_id: str) -> Optional[MemoryItem]:
        """Access an item, boosting its activation"""
        with self._lock:
            for item in self.items:
                if item.id == item_id:
                    item.activation = min(1.0, item.activation + self.REHEARSAL_BOOST)
                    item.last_accessed = datetime.now()
                    item.access_count += 1
                    return item
            return None

    def focus(self, item_id: str) -> bool:
        """Set focus on a specific item (keeps it highly activated)"""
        with self._lock:
            for item in self.items:
                if item.id == item_id:
                    self.focus_id = item_id
                    item.activation = 1.0
                    return True
            return False

    def decay(self):
        """Apply decay to all items (call once per turn)"""
        with self._lock:
            for item in self.items:
                if item.id != self.focus_id:
                    # Exponential decay, modified by importance
                    decay_factor = self.DECAY_RATE * (1 - item.importance * 0.5)
                    item.activation = max(0.0, item.activation - decay_factor)

    def get_active_items(self, threshold: float = 0.3) -> List[MemoryItem]:
        """Get items above activation threshold, sorted by activation"""
        with self._lock:
            active = [item for item in self.items if item.activation >= threshold]
            return sorted(active, key=lambda x: x.activation * x.importance, reverse=True)

    def get_context_string(self, max_tokens: int = 200) -> str:
        """Build context string from active items"""
        items = self.get_active_items()
        context_parts = []
        token_count = 0

        for item in items:
            # Rough token estimate
            item_tokens = len(item.content) // 4
            if token_count + item_tokens > max_tokens:
                break
            context_parts.append(f"[{item.memory_type.value}] {item.content}")
            token_count += item_tokens

        return "\n".join(context_parts)

    def clear(self):
        """Clear all items"""
        with self._lock:
            self.items.clear()
            self.focus_id = None

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        hash_input = f"{content}{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]


@dataclass
class Skill:
    """A procedural memory skill"""
    id: str
    name: str
    description: str
    trigger_patterns: List[str]  # Regex patterns that trigger this skill
    implementation: str  # Python code or prompt template
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def confidence(self) -> float:
        """Confidence increases with more uses"""
        total = self.success_count + self.failure_count
        base = self.success_rate
        # Bayesian-like adjustment: more data = higher confidence
        return base * (1 - 1 / (1 + total * 0.1))


class ProceduralMemory:
    """
    Procedural memory for skills and habits.

    Skills are learned patterns that can be triggered by specific inputs.
    Habits are frequently-used skill combinations.
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/procedural.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._skill_cache: Dict[str, Skill] = {}

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                trigger_patterns TEXT,  -- JSON array
                implementation TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT,
                metadata TEXT,  -- JSON
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT,
                success INTEGER,
                duration_ms INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_usage_skill_id
            ON skill_usage(skill_id)
        """)

        conn.commit()
        conn.close()

    def add_skill(self, name: str, description: str, trigger_patterns: List[str],
                  implementation: str, metadata: Optional[Dict] = None) -> Skill:
        """Add a new skill"""
        skill_id = hashlib.sha256(name.encode()).hexdigest()[:12]

        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            implementation=implementation,
            metadata=metadata or {}
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO skills
            (id, name, description, trigger_patterns, implementation, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            skill.id,
            skill.name,
            skill.description,
            json.dumps(skill.trigger_patterns),
            skill.implementation,
            json.dumps(skill.metadata)
        ))

        conn.commit()
        conn.close()

        self._skill_cache[skill_id] = skill
        return skill

    def find_matching_skills(self, input_text: str) -> List[Tuple[Skill, float]]:
        """Find skills that match the input, with confidence scores"""
        import re
        matches = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills")

        for row in cursor.fetchall():
            skill = self._row_to_skill(row)
            for pattern in skill.trigger_patterns:
                try:
                    if re.search(pattern, input_text, re.IGNORECASE):
                        matches.append((skill, skill.confidence))
                        break
                except re.error:
                    continue

        conn.close()

        # Sort by confidence
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def record_usage(self, skill_id: str, input_text: str, output_text: str,
                     success: bool, duration_ms: int = 0):
        """Record skill usage for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Record usage
        cursor.execute("""
            INSERT INTO skill_usage (skill_id, input_text, output_text, success, duration_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (skill_id, input_text, output_text, 1 if success else 0, duration_ms))

        # Update skill stats
        if success:
            cursor.execute(
                "UPDATE skills SET success_count = success_count + 1, last_used = ? WHERE id = ?",
                (datetime.now().isoformat(), skill_id)
            )
        else:
            cursor.execute(
                "UPDATE skills SET failure_count = failure_count + 1, last_used = ? WHERE id = ?",
                (datetime.now().isoformat(), skill_id)
            )

        conn.commit()
        conn.close()

        # Update cache
        if skill_id in self._skill_cache:
            if success:
                self._skill_cache[skill_id].success_count += 1
            else:
                self._skill_cache[skill_id].failure_count += 1

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        if skill_id in self._skill_cache:
            return self._skill_cache[skill_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            skill = self._row_to_skill(row)
            self._skill_cache[skill_id] = skill
            return skill
        return None

    def get_top_skills(self, n: int = 10) -> List[Skill]:
        """Get top N skills by usage and success rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM skills
            ORDER BY (success_count * 1.0 / (success_count + failure_count + 1)) *
                     (success_count + failure_count) DESC
            LIMIT ?
        """, (n,))

        skills = [self._row_to_skill(row) for row in cursor.fetchall()]
        conn.close()
        return skills

    def _row_to_skill(self, row) -> Skill:
        """Convert database row to Skill object"""
        return Skill(
            id=row[0],
            name=row[1],
            description=row[2],
            trigger_patterns=json.loads(row[3]) if row[3] else [],
            implementation=row[4],
            success_count=row[5] or 0,
            failure_count=row[6] or 0,
            last_used=datetime.fromisoformat(row[7]) if row[7] else None,
            metadata=json.loads(row[8]) if row[8] else {}
        )


class MemoryDecayManager:
    """
    Manages memory decay and forgetting across all memory systems.

    Implements:
    - Power law of forgetting (Ebbinghaus)
    - Spacing effect for rehearsal
    - Importance-based retention
    """

    # Forgetting curve parameters
    RETENTION_RATE = 0.9  # Base retention per day
    IMPORTANCE_WEIGHT = 0.5  # How much importance affects retention

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/decay.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize decay tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_strength (
                memory_id TEXT PRIMARY KEY,
                source_system TEXT,  -- 'semantic', 'episodic', 'conversation'
                strength REAL DEFAULT 1.0,
                importance REAL DEFAULT 0.5,
                last_access TEXT,
                access_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strength_source
            ON memory_strength(source_system)
        """)

        conn.commit()
        conn.close()

    def track_memory(self, memory_id: str, source_system: str,
                     importance: float = 0.5):
        """Start tracking a memory's strength"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO memory_strength
            (memory_id, source_system, strength, importance, last_access, access_count)
            VALUES (?, ?, 1.0, ?, ?, 1)
        """, (memory_id, source_system, importance, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def access_memory(self, memory_id: str) -> float:
        """Record memory access, return current strength"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current state
        cursor.execute(
            "SELECT strength, importance, last_access, access_count FROM memory_strength WHERE memory_id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return 0.0

        old_strength, importance, last_access, access_count = row

        # Calculate decayed strength
        if last_access:
            last_dt = datetime.fromisoformat(last_access)
            days_elapsed = (datetime.now() - last_dt).total_seconds() / 86400
            decay = math.pow(self.RETENTION_RATE, days_elapsed)
            decay_adjusted = decay + (1 - decay) * importance * self.IMPORTANCE_WEIGHT
            current_strength = old_strength * decay_adjusted
        else:
            current_strength = old_strength

        # Boost from access (spacing effect)
        spacing_bonus = min(0.2, 0.05 * math.log1p(access_count))
        new_strength = min(1.0, current_strength + spacing_bonus)

        # Update
        cursor.execute("""
            UPDATE memory_strength
            SET strength = ?, last_access = ?, access_count = access_count + 1
            WHERE memory_id = ?
        """, (new_strength, datetime.now().isoformat(), memory_id))

        conn.commit()
        conn.close()

        return new_strength

    def get_weak_memories(self, threshold: float = 0.3,
                          source_system: Optional[str] = None) -> List[str]:
        """Get memory IDs that have decayed below threshold (candidates for forgetting)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # First, calculate current strengths accounting for decay
        now = datetime.now()

        if source_system:
            cursor.execute(
                "SELECT memory_id, strength, importance, last_access FROM memory_strength WHERE source_system = ?",
                (source_system,)
            )
        else:
            cursor.execute(
                "SELECT memory_id, strength, importance, last_access FROM memory_strength"
            )

        weak = []
        for row in cursor.fetchall():
            memory_id, strength, importance, last_access = row
            if last_access:
                last_dt = datetime.fromisoformat(last_access)
                days_elapsed = (now - last_dt).total_seconds() / 86400
                decay = math.pow(self.RETENTION_RATE, days_elapsed)
                decay_adjusted = decay + (1 - decay) * importance * self.IMPORTANCE_WEIGHT
                current_strength = strength * decay_adjusted
            else:
                current_strength = strength

            if current_strength < threshold:
                weak.append(memory_id)

        conn.close()
        return weak

    def prune_memories(self, threshold: float = 0.1) -> int:
        """Remove memories below threshold from tracking (actual deletion handled by caller)"""
        weak = self.get_weak_memories(threshold)

        if not weak:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"DELETE FROM memory_strength WHERE memory_id IN ({','.join('?' * len(weak))})",
            weak
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted


class EnhancedMemoryManager:
    """
    Unified manager integrating all memory systems.

    Coordinates:
    - Working memory (active items)
    - Procedural memory (skills)
    - Decay management (forgetting)
    - Existing semantic/episodic memories
    """

    def __init__(self,
                 working_memory_capacity: int = 7,
                 memory_db_path: str = "/Volumes/David External/sam_memory"):
        self.working_memory = WorkingMemory(capacity=working_memory_capacity)
        self.procedural_memory = ProceduralMemory(
            db_path=f"{memory_db_path}/procedural.db"
        )
        self.decay_manager = MemoryDecayManager(
            db_path=f"{memory_db_path}/decay.db"
        )
        self.turn_count = 0

    def process_turn(self, user_input: str, response: str):
        """Process a conversation turn, updating all memory systems"""
        self.turn_count += 1

        # Add to working memory
        self.working_memory.add(
            content=user_input,
            memory_type=MemoryType.CONTEXT,
            importance=0.7  # User input is important
        )

        # Apply decay to working memory
        self.working_memory.decay()

        # Check for skill triggers
        matching_skills = self.procedural_memory.find_matching_skills(user_input)
        if matching_skills:
            top_skill, confidence = matching_skills[0]
            if confidence > 0.7:
                # Record that we could have used this skill
                self.procedural_memory.record_usage(
                    skill_id=top_skill.id,
                    input_text=user_input,
                    output_text=response,
                    success=True  # Assume success for now
                )

    def get_context(self, max_tokens: int = 200) -> str:
        """Get current context from working memory"""
        return self.working_memory.get_context_string(max_tokens)

    def add_fact(self, fact: str, importance: float = 0.5) -> MemoryItem:
        """Add a fact to working memory"""
        return self.working_memory.add(
            content=fact,
            memory_type=MemoryType.FACT,
            importance=importance
        )

    def add_skill(self, name: str, description: str,
                  triggers: List[str], implementation: str) -> Skill:
        """Add a new skill to procedural memory"""
        return self.procedural_memory.add_skill(
            name=name,
            description=description,
            trigger_patterns=triggers,
            implementation=implementation
        )

    def find_skill(self, query: str) -> Optional[Tuple[Skill, float]]:
        """Find best matching skill for a query"""
        matches = self.procedural_memory.find_matching_skills(query)
        return matches[0] if matches else None

    def run_maintenance(self) -> Dict[str, int]:
        """Run memory maintenance (call periodically)"""
        results = {}

        # Prune very weak memories
        results['pruned'] = self.decay_manager.prune_memories(threshold=0.1)

        # Get weak memories for potential consolidation
        weak = self.decay_manager.get_weak_memories(threshold=0.3)
        results['weak_count'] = len(weak)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "working_memory": {
                "capacity": self.working_memory.capacity,
                "current_items": len(self.working_memory.items),
                "active_items": len(self.working_memory.get_active_items()),
                "focus": self.working_memory.focus_id
            },
            "procedural_memory": {
                "top_skills": [
                    {"name": s.name, "confidence": s.confidence}
                    for s in self.procedural_memory.get_top_skills(5)
                ]
            },
            "turn_count": self.turn_count
        }


# Convenience functions for integration
def create_enhanced_memory(capacity: int = 7) -> EnhancedMemoryManager:
    """Create an enhanced memory manager with default settings"""
    return EnhancedMemoryManager(working_memory_capacity=capacity)


if __name__ == "__main__":
    # Demo
    manager = create_enhanced_memory()

    # Simulate conversation
    manager.process_turn("Remember my name is David", "Got it, David!")
    manager.process_turn("I like Python programming", "Python is great!")
    manager.process_turn("What's 2+2?", "4")

    print("Working memory context:")
    print(manager.get_context())
    print("\nStats:", json.dumps(manager.get_stats(), indent=2))

    # Add a skill
    manager.add_skill(
        name="greeting",
        description="Respond to greetings",
        triggers=[r"\b(hi|hello|hey)\b"],
        implementation="Respond warmly with SAM's personality"
    )

    # Test skill matching
    skill = manager.find_skill("Hello there!")
    if skill:
        print(f"\nMatched skill: {skill[0].name} (confidence: {skill[1]:.2f})")
