"""
training/ - Unified Training Package
=====================================
Consolidates all training-related functionality for SAM.

Components:
- pipeline: MLX LoRA fine-tuning pipeline (moved from learn/training_pipeline.py)
- voice: RVC voice training (re-exported from voice/voice_trainer.py)
- scheduler: Resource-aware training scheduler (re-exported from learning/scheduler.py)

Usage:
    # LoRA fine-tuning pipeline
    from training.pipeline import TrainingPipeline, TrainingRun
    pipeline = TrainingPipeline()
    pipeline.start_training()

    # Voice training (RVC)
    from training import VoiceTrainer, voice_status, voice_start
    trainer = VoiceTrainer()

    # Training scheduler (resource-aware)
    from training import TrainingScheduler

Created during Phase 3 codebase consolidation.
"""

# Primary: LoRA fine-tuning pipeline (canonical location)
from training.pipeline import (
    TrainingPipeline,
    TrainingRun,
    MIN_SAMPLES_FOR_TRAINING,
    BASE_MODEL,
)

# Re-export: Voice training from voice/ (stays in voice/ as canonical location)
from voice.voice_trainer import (
    VoiceTrainer,
    get_trainer,
    voice_status,
    voice_prepare,
    voice_start,
    voice_stop,
)

# Re-export: Training scheduler from learning/ (stays in learning/ as canonical location)
from learning.scheduler import TrainingScheduler

__all__ = [
    # Pipeline (canonical)
    "TrainingPipeline",
    "TrainingRun",
    "MIN_SAMPLES_FOR_TRAINING",
    "BASE_MODEL",
    # Voice training (re-export)
    "VoiceTrainer",
    "get_trainer",
    "voice_status",
    "voice_prepare",
    "voice_start",
    "voice_stop",
    # Scheduler (re-export)
    "TrainingScheduler",
]
