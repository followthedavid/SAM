"""
Emotion2Vec MLX Models

Native MLX implementations of emotion recognition models.
"""

from .emotion2vec_mlx import (
    Emotion2VecMLX,
    Emotion2VecConfig,
    load_emotion2vec,
)

__all__ = [
    "Emotion2VecMLX",
    "Emotion2VecConfig",
    "load_emotion2vec",
]
