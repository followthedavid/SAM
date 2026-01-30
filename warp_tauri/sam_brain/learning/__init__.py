"""
SAM Learning Package
====================
Unified learning system consolidating perpetual_learner.py and auto_learner.py.

Provides:
- LearningDatabase: Unified SQLite storage for examples, curriculum, training runs
- CurriculumManager: Prioritized learning with confidence scoring
- ClaudeSessionExtractor: Extract training pairs from Claude Code sessions
- TrainingScheduler: Resource-aware training scheduler
- UnifiedLearnerDaemon: Coordinated daemon entry point

Usage:
    from learning.database import LearningDatabase
    from learning.curriculum import CurriculumManager, TaskType, TaskPriority, CurriculumTask
    from learning.extractors import ClaudeSessionExtractor, TrainingExample
    from learning.scheduler import TrainingScheduler
    from learning.daemon import UnifiedLearnerDaemon
"""

from learning.database import LearningDatabase
from learning.curriculum import CurriculumManager, TaskType, TaskPriority, CurriculumTask
from learning.extractors import ClaudeSessionExtractor, TrainingExample
from learning.scheduler import TrainingScheduler
from learning.daemon import UnifiedLearnerDaemon

__all__ = [
    "LearningDatabase",
    "CurriculumManager",
    "TaskType",
    "TaskPriority",
    "CurriculumTask",
    "ClaudeSessionExtractor",
    "TrainingExample",
    "TrainingScheduler",
    "UnifiedLearnerDaemon",
]
