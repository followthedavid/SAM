"""
Curriculum Learning System
==========================
Prioritized learning with confidence-based correction.

Extracted from perpetual_learner.py CurriculumManager and related classes.

Features:
- Priority-ordered task queue (CRITICAL > HIGH > MEDIUM > LOW)
- Confidence scoring for SAM's attempts
- Correction example generation when confidence < 0.7
- Teacher-student verification loop integration
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Paths
BRAIN_PATH = Path(__file__).parent.parent
DATA_PATH = BRAIN_PATH / "data"


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)


class TaskType(Enum):
    """Types of learning tasks for curriculum prioritization."""
    CODING = "coding"
    REASONING = "reasoning"
    ROLEPLAY = "roleplay"
    KNOWLEDGE = "knowledge"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"


class TaskPriority(Enum):
    """Priority levels for curriculum tasks."""
    CRITICAL = 1    # Learn immediately
    HIGH = 2        # Learn today
    MEDIUM = 3      # Learn this week
    LOW = 4         # Learn eventually


@dataclass
class CurriculumTask:
    """
    A prioritized learning task with confidence scoring.

    Tasks are processed based on priority, with lower numbers processed first.
    Confidence scoring enables correction example generation for low-confidence
    attempts (< 0.7).
    """
    id: str
    task_type: str
    instruction: str           # What to learn
    context: Optional[str]     # Additional context
    expected_skills: List[str] # What SAM should learn from this
    priority: int
    created_at: str
    created_by: str            # "claude_code", "perpetual_learner", "user", "self"

    # Learning progress
    attempted: bool = False
    sam_attempt: Optional[str] = None
    sam_confidence: float = 0.0
    verified_response: Optional[str] = None
    learning_captured: bool = False
    completed_at: Optional[str] = None


class CurriculumManager:
    """
    Manages prioritized curriculum learning with confidence-based correction.

    Features:
    - Priority-ordered task queue (CRITICAL > HIGH > MEDIUM > LOW)
    - Confidence scoring for SAM's attempts
    - Correction example generation when confidence < 0.7
    - Teacher-student verification loop integration

    Usage:
        from learning.database import LearningDatabase
        db = LearningDatabase()
        manager = CurriculumManager(db)

        # Add learning tasks
        task_id = manager.add_task(
            instruction="Explain SwiftUI @State vs @Binding",
            task_type="coding",
            priority=TaskPriority.HIGH.value,
            expected_skills=["swift", "swiftui"]
        )

        # Process next task
        task = manager.get_next_task()
        if task:
            attempt, confidence = manager.attempt_task(task)
            manager.mark_attempted(task['id'], attempt, confidence)

            if confidence < 0.7:
                verified = get_better_answer(task['instruction'])
                manager.capture_learning(task, attempt, verified)
    """

    def __init__(self, db):
        """
        Initialize CurriculumManager.

        Args:
            db: A LearningDatabase instance
        """
        self.db = db
        self.training_output = DATA_PATH / "curriculum_learned.jsonl"

    def add_task(self, instruction: str, task_type: str = "coding",
                 context: str = None, expected_skills: List[str] = None,
                 priority: int = TaskPriority.MEDIUM.value,
                 created_by: str = "perpetual_learner") -> Optional[str]:
        """
        Add a learning task to the curriculum.

        Returns task_id if added, None if task already exists.
        """
        task = CurriculumTask(
            id=hashlib.md5(instruction.encode()).hexdigest()[:16],
            task_type=task_type,
            instruction=instruction,
            context=context,
            expected_skills=expected_skills or [],
            priority=priority,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
        )

        added = self.db.add_curriculum_task(
            task_id=task.id,
            task_type=task.task_type,
            instruction=task.instruction,
            context=task.context,
            expected_skills=task.expected_skills,
            priority=task.priority,
            created_at=task.created_at,
            created_by=task.created_by,
        )

        if added:
            log(f"[Curriculum] Added task: {instruction[:60]}...")
            return task.id
        return None

    def add_batch(self, tasks: List[Dict]) -> int:
        """Add multiple learning tasks. Returns count added."""
        added = 0
        for t in tasks:
            if self.add_task(
                instruction=t["instruction"],
                task_type=t.get("type", "coding"),
                context=t.get("context"),
                expected_skills=t.get("skills", []),
                priority=t.get("priority", TaskPriority.MEDIUM.value),
                created_by=t.get("created_by", "perpetual_learner")
            ):
                added += 1
        return added

    def get_next_task(self) -> Optional[Dict]:
        """Get the next pending task, ordered by priority."""
        return self.db.get_next_curriculum_task()

    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return self.db.get_pending_curriculum_count()

    def get_low_confidence_tasks(self, threshold: float = 0.7, limit: int = 10) -> List[Dict]:
        """Get attempted tasks with confidence below threshold (need correction)."""
        return self.db.get_low_confidence_tasks(threshold, limit)

    def mark_attempted(self, task_id: str, sam_attempt: str, confidence: float):
        """Mark a task as attempted with SAM's response and confidence."""
        self.db.mark_curriculum_attempted(task_id, sam_attempt, confidence)

    def mark_learned(self, task_id: str, verified_response: str):
        """Mark a task as learned with the verified response."""
        self.db.mark_curriculum_learned(task_id, verified_response)

    def estimate_confidence(self, response: str) -> float:
        """
        Estimate confidence in a response based on heuristics.

        Returns value between 0.1 and 0.95.
        """
        confidence = 0.5  # Base

        # Longer responses often better
        if len(response) > 500:
            confidence += 0.1
        if len(response) > 1000:
            confidence += 0.1

        # Code blocks indicate practical answer
        if "```" in response:
            confidence += 0.15

        # Hedging language reduces confidence
        hedges = ["i think", "maybe", "possibly", "not sure", "i don't know"]
        for hedge in hedges:
            if hedge in response.lower():
                confidence -= 0.1

        return max(0.1, min(0.95, confidence))

    def capture_learning(self, task: Dict, sam_attempt: str, verified_response: str):
        """
        Convert learning into training data.

        Creates:
        1. Standard instruction-following example (always)
        2. Correction example if confidence < 0.7 (teaches SAM to improve)
        """
        # Create instruction-following training example
        example = {
            "messages": [
                {"role": "user", "content": task["instruction"]},
                {"role": "assistant", "content": verified_response}
            ],
            "metadata": {
                "source": "curriculum_learning",
                "task_type": task.get("task_type", "unknown"),
                "task_id": task.get("id", ""),
                "sam_attempt_confidence": task.get("sam_confidence", 0),
                "learned_at": datetime.now().isoformat(),
            }
        }

        # Also create a correction example if SAM was low confidence
        if task.get("sam_confidence", 0) < 0.7:
            correction_example = {
                "messages": [
                    {"role": "user", "content": task["instruction"]},
                    {"role": "assistant", "content": sam_attempt},
                    {"role": "user", "content": "That's not quite right. Can you do better?"},
                    {"role": "assistant", "content": verified_response}
                ],
                "metadata": {
                    "source": "curriculum_correction",
                    "task_type": task.get("task_type", "unknown"),
                    "original_confidence": task.get("sam_confidence", 0),
                }
            }

            with open(self.training_output, "a") as f:
                f.write(json.dumps(correction_example) + "\n")
            log(f"[Curriculum] Created correction example (confidence: {task.get('sam_confidence', 0):.2f})")

        # Write main example
        with open(self.training_output, "a") as f:
            f.write(json.dumps(example) + "\n")

        # Mark as learned in DB
        self.mark_learned(task.get("id", ""), verified_response)
        log(f"[Curriculum] Captured learning for: {task['instruction'][:40]}...")

    def get_stats(self) -> Dict:
        """Get curriculum statistics."""
        return self.db.get_curriculum_stats()
