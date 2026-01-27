"""
Emotion Detection Backends

Modular backends for voice emotion detection:
- emotion2vec: Full Emotion2Vec MLX model (best quality)
- hybrid: Emotion2Vec + prosodic analysis combined
- whisper_mlx: MLX Whisper embeddings + trained classifier
- prosodic: Pure prosodic feature analysis (no ML, fast)
"""

from typing import List, Dict, Any
import os

# Available backends
BACKENDS = {
    "emotion2vec": {
        "name": "Emotion2Vec MLX",
        "description": "Full Emotion2Vec model ported to MLX (best accuracy)",
        "requires": ["mlx"],
        "memory_mb": 400,
        "quality": "excellent",
        "speed": "moderate"
    },
    "hybrid": {
        "name": "Hybrid (Emotion2Vec + Prosodic)",
        "description": "Combines neural classification with prosodic VAD",
        "requires": ["mlx"],
        "memory_mb": 450,
        "quality": "excellent",
        "speed": "moderate"
    },
    "whisper_mlx": {
        "name": "Whisper MLX Embeddings",
        "description": "MLX-native Whisper encoder + emotion classifier",
        "requires": ["mlx", "mlx_whisper"],
        "memory_mb": 500,
        "quality": "good",
        "speed": "fast"
    },
    "prosodic": {
        "name": "Prosodic Features",
        "description": "Pure prosodic analysis (pitch, rate, energy)",
        "requires": [],  # Uses mlx-audio or torchaudio
        "memory_mb": 50,
        "quality": "basic",
        "speed": "very_fast"
    },
}


def get_available_backends() -> List[str]:
    """Return list of backends available on this system."""
    available = []

    # Prosodic is always available
    available.append("prosodic")

    # Check for MLX
    try:
        import mlx.core
        available.append("whisper_mlx")

        # Check if Emotion2Vec weights exist
        from .emotion2vec_backend import Emotion2VecBackend
        e2v = Emotion2VecBackend()
        if e2v.weights_path and os.path.exists(e2v.weights_path):
            available.insert(0, "emotion2vec")  # Prefer E2V if weights exist
            available.insert(1, "hybrid")
        else:
            # Still available but will use random weights (for testing)
            available.append("emotion2vec")
            available.append("hybrid")

    except ImportError:
        pass

    return available


def get_backend_info(name: str) -> Dict[str, Any]:
    """Get info about a specific backend."""
    return BACKENDS.get(name, {})


def get_best_backend() -> str:
    """Get the best available backend."""
    available = get_available_backends()
    # Priority order
    for backend in ["emotion2vec", "hybrid", "whisper_mlx", "prosodic"]:
        if backend in available:
            return backend
    return "prosodic"


# Backend factory
def create_backend(name: str, **kwargs):
    """Create a backend instance."""
    if name == "prosodic":
        from .prosodic_backend import ProsodicEmotionBackend
        return ProsodicEmotionBackend(**kwargs)
    elif name == "whisper_mlx":
        from .whisper_backend import WhisperMLXBackend
        return WhisperMLXBackend(**kwargs)
    elif name == "emotion2vec":
        from .emotion2vec_backend import Emotion2VecBackend
        return Emotion2VecBackend(**kwargs)
    elif name == "hybrid":
        from .emotion2vec_backend import HybridEmotionBackend
        return HybridEmotionBackend(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {name}")
