"""
Emotion2Vec MLX Implementation

Native MLX port of the Emotion2Vec model for Apple Silicon.
Based on data2vec 2.0 architecture with emotion classification head.

Model outputs:
- 768-dimensional feature vectors
- 9 emotion class probabilities
"""

import mlx.core as mx
import mlx.nn as nn
from dataclasses import dataclass
from typing import Optional, Tuple, List
import math


@dataclass
class Emotion2VecConfig:
    """Configuration for Emotion2Vec model."""

    # Feature extractor (CNN)
    conv_dim: int = 512
    conv_kernel_sizes: Tuple[int, ...] = (10, 3, 3, 3, 3, 2, 2)
    conv_strides: Tuple[int, ...] = (5, 2, 2, 2, 2, 2, 2)

    # Transformer encoder
    hidden_size: int = 768
    num_attention_heads: int = 12
    num_hidden_layers: int = 8  # 8 blocks in emotion2vec base
    intermediate_size: int = 3072
    hidden_dropout_prob: float = 0.1
    attention_dropout_prob: float = 0.1

    # Classifier
    num_emotions: int = 9

    # Audio
    sample_rate: int = 16000

    @classmethod
    def base(cls) -> "Emotion2VecConfig":
        """Base model config (~90M params)."""
        return cls()

    @classmethod
    def large(cls) -> "Emotion2VecConfig":
        """Large model config (~300M params)."""
        return cls(
            hidden_size=1024,
            num_attention_heads=16,
            num_hidden_layers=24,
            intermediate_size=4096,
        )


class ConvFeatureExtractor(nn.Module):
    """
    CNN feature extractor from raw audio waveform.
    Converts raw audio to frame-level features.

    Architecture (7 conv layers):
    - Conv1: kernel=10, stride=5, in=1, out=512
    - Conv2-5: kernel=3, stride=2, in=512, out=512
    - Conv6-7: kernel=2, stride=2, in=512, out=512
    Each followed by GroupNorm (mapped to LayerNorm) and GELU.
    """

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        self.config = config

        # Build conv layers with per-layer norms
        # NOTE: Original model has no bias in conv layers
        self.conv_layers = []
        self.layer_norms = []
        in_channels = 1  # mono audio

        for i, (kernel_size, stride) in enumerate(
            zip(config.conv_kernel_sizes, config.conv_strides)
        ):
            conv = nn.Conv1d(
                in_channels=in_channels,
                out_channels=config.conv_dim,
                kernel_size=kernel_size,
                stride=stride,
                padding=kernel_size // 2,
                bias=False,  # Original model has no conv bias
            )
            self.conv_layers.append(conv)
            self.layer_norms.append(nn.LayerNorm(config.conv_dim))
            in_channels = config.conv_dim

        # Project to hidden size
        self.projection = nn.Linear(config.conv_dim, config.hidden_size)

    def __call__(self, x: mx.array) -> mx.array:
        """
        Args:
            x: Raw audio waveform [batch, time]

        Returns:
            Features [batch, frames, hidden_size]
        """
        # MLX Conv1d expects [batch, sequence, in_channels]
        # Add channel dimension [batch, time, 1]
        x = mx.expand_dims(x, axis=-1)

        # Apply conv layers with layer norm and GELU
        for conv, ln in zip(self.conv_layers, self.layer_norms):
            x = conv(x)
            x = ln(x)
            x = nn.gelu(x)

        # x is now [batch, frames, conv_dim]

        # Project to hidden size
        x = self.projection(x)

        return x


class PositionalEncoding:
    """Sinusoidal positional encoding (not a learnable module)."""

    def __init__(self, hidden_size: int, max_len: int = 5000):
        self.hidden_size = hidden_size
        self.max_len = max_len
        self._pe = None  # Lazy initialization

    def _build_pe(self, seq_len: int) -> mx.array:
        """Build positional encoding matrix."""
        position = mx.arange(seq_len).reshape(-1, 1)
        div_term = mx.exp(
            mx.arange(0, self.hidden_size, 2) * (-math.log(10000.0) / self.hidden_size)
        )

        pe = mx.zeros((seq_len, self.hidden_size))
        pe = pe.at[:, 0::2].add(mx.sin(position * div_term))
        pe = pe.at[:, 1::2].add(mx.cos(position * div_term))
        return pe

    def __call__(self, x: mx.array) -> mx.array:
        """Add positional encoding to input."""
        seq_len = x.shape[1]
        if self._pe is None or self._pe.shape[0] < seq_len:
            self._pe = self._build_pe(max(seq_len, self.max_len))
        return x + self._pe[:seq_len]


class MultiHeadAttention(nn.Module):
    """Multi-head self-attention."""

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        self.num_heads = config.num_attention_heads
        self.head_dim = config.hidden_size // config.num_attention_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.out_proj = nn.Linear(config.hidden_size, config.hidden_size)

        self.dropout = nn.Dropout(config.attention_dropout_prob)

    def __call__(
        self,
        x: mx.array,
        mask: Optional[mx.array] = None,
        cache: Optional[Tuple[mx.array, mx.array]] = None
    ) -> Tuple[mx.array, Optional[Tuple[mx.array, mx.array]]]:
        batch_size, seq_len, _ = x.shape

        # Project to Q, K, V
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        # Reshape for multi-head attention
        q = q.reshape(batch_size, seq_len, self.num_heads, self.head_dim)
        k = k.reshape(batch_size, seq_len, self.num_heads, self.head_dim)
        v = v.reshape(batch_size, seq_len, self.num_heads, self.head_dim)

        # Transpose to [batch, heads, seq, head_dim]
        q = mx.transpose(q, axes=(0, 2, 1, 3))
        k = mx.transpose(k, axes=(0, 2, 1, 3))
        v = mx.transpose(v, axes=(0, 2, 1, 3))

        # Handle KV cache for efficient inference
        if cache is not None:
            k_cache, v_cache = cache
            k = mx.concatenate([k_cache, k], axis=2)
            v = mx.concatenate([v_cache, v], axis=2)
        new_cache = (k, v)

        # Compute attention scores
        attn_weights = (q @ mx.transpose(k, axes=(0, 1, 3, 2))) * self.scale

        if mask is not None:
            attn_weights = attn_weights + mask

        attn_weights = mx.softmax(attn_weights, axis=-1)
        attn_weights = self.dropout(attn_weights)

        # Apply attention to values
        attn_output = attn_weights @ v

        # Reshape back
        attn_output = mx.transpose(attn_output, axes=(0, 2, 1, 3))
        attn_output = attn_output.reshape(batch_size, seq_len, -1)

        # Output projection
        output = self.out_proj(attn_output)

        return output, new_cache


class FeedForward(nn.Module):
    """Feed-forward network."""

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        self.fc1 = nn.Linear(config.hidden_size, config.intermediate_size)
        self.fc2 = nn.Linear(config.intermediate_size, config.hidden_size)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def __call__(self, x: mx.array) -> mx.array:
        x = self.fc1(x)
        x = nn.gelu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        return x


class TransformerEncoderLayer(nn.Module):
    """Single transformer encoder layer."""

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        self.attention = MultiHeadAttention(config)
        self.feed_forward = FeedForward(config)
        self.ln1 = nn.LayerNorm(config.hidden_size)
        self.ln2 = nn.LayerNorm(config.hidden_size)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def __call__(
        self,
        x: mx.array,
        mask: Optional[mx.array] = None,
        cache: Optional[Tuple[mx.array, mx.array]] = None
    ) -> Tuple[mx.array, Optional[Tuple[mx.array, mx.array]]]:
        # Self-attention with residual
        residual = x
        x = self.ln1(x)
        attn_output, new_cache = self.attention(x, mask, cache)
        x = residual + self.dropout(attn_output)

        # Feed-forward with residual
        residual = x
        x = self.ln2(x)
        ff_output = self.feed_forward(x)
        x = residual + ff_output

        return x, new_cache


class TransformerEncoder(nn.Module):
    """Transformer encoder stack."""

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        self.layers = [
            TransformerEncoderLayer(config)
            for _ in range(config.num_hidden_layers)
        ]
        self.final_ln = nn.LayerNorm(config.hidden_size)

    def __call__(
        self,
        x: mx.array,
        mask: Optional[mx.array] = None,
        cache: Optional[List[Tuple[mx.array, mx.array]]] = None
    ) -> Tuple[mx.array, Optional[List[Tuple[mx.array, mx.array]]]]:
        new_cache = []

        for i, layer in enumerate(self.layers):
            layer_cache = cache[i] if cache is not None else None
            x, layer_new_cache = layer(x, mask, layer_cache)
            new_cache.append(layer_new_cache)

        x = self.final_ln(x)

        return x, new_cache if cache is not None else None


class EmotionClassifier(nn.Module):
    """Emotion classification head.

    Simple linear projection from hidden_size to num_emotions.
    The original emotion2vec uses a direct 'proj' layer.
    """

    def __init__(self, config: Emotion2VecConfig):
        super().__init__()
        # Direct projection (matches original 'proj' layer)
        self.classifier = nn.Linear(config.hidden_size, config.num_emotions)

    def __call__(self, x: mx.array) -> mx.array:
        """
        Args:
            x: Encoder output [batch, seq, hidden]

        Returns:
            Logits [batch, num_emotions]
        """
        # Mean pooling over sequence
        x = mx.mean(x, axis=1)
        x = self.classifier(x)
        return x


class Emotion2VecMLX(nn.Module):
    """
    Emotion2Vec model for MLX.

    Full model for speech emotion recognition on Apple Silicon.
    """

    # Emotion labels (matching original model)
    EMOTIONS = [
        "angry", "disgusted", "fearful", "happy",
        "neutral", "other", "sad", "surprised", "unknown"
    ]

    def __init__(self, config: Optional[Emotion2VecConfig] = None):
        super().__init__()
        self.config = config or Emotion2VecConfig.base()

        # Feature extractor
        self.feature_extractor = ConvFeatureExtractor(self.config)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(self.config.hidden_size)

        # Transformer encoder
        self.encoder = TransformerEncoder(self.config)

        # Emotion classifier
        self.classifier = EmotionClassifier(self.config)

    def extract_features(
        self,
        audio: mx.array,
        return_hidden_states: bool = False
    ) -> mx.array:
        """
        Extract emotion features from audio.

        Args:
            audio: Raw audio waveform [batch, time] or [time]
            return_hidden_states: Return all hidden states

        Returns:
            Features [batch, hidden_size] or [batch, seq, hidden_size]
        """
        # Handle unbatched input
        if audio.ndim == 1:
            audio = mx.expand_dims(audio, axis=0)

        # Extract CNN features
        x = self.feature_extractor(audio)

        # Add positional encoding
        x = self.pos_encoding(x)

        # Encode with transformer
        x, _ = self.encoder(x)

        if return_hidden_states:
            return x  # [batch, seq, hidden]

        # Mean pooling for utterance-level features
        return mx.mean(x, axis=1)  # [batch, hidden]

    def __call__(
        self,
        audio: mx.array,
        return_probs: bool = True
    ) -> mx.array:
        """
        Predict emotion from audio.

        Args:
            audio: Raw audio waveform [batch, time] or [time]
            return_probs: Return probabilities (True) or logits (False)

        Returns:
            Emotion probabilities or logits [batch, num_emotions]
        """
        # Handle unbatched input
        if audio.ndim == 1:
            audio = mx.expand_dims(audio, axis=0)

        # Extract CNN features
        x = self.feature_extractor(audio)

        # Add positional encoding
        x = self.pos_encoding(x)

        # Encode with transformer
        x, _ = self.encoder(x)

        # Classify
        logits = self.classifier(x)

        if return_probs:
            return mx.softmax(logits, axis=-1)
        return logits

    def predict(self, audio: mx.array) -> dict:
        """
        Get full prediction with emotion labels and confidence.

        Args:
            audio: Raw audio waveform

        Returns:
            Dict with 'emotion', 'confidence', 'all_probs'
        """
        probs = self(audio)

        if probs.ndim == 2:
            probs = probs[0]  # Unbatch

        top_idx = int(mx.argmax(probs))

        return {
            "emotion": self.EMOTIONS[top_idx],
            "emotion_idx": top_idx,
            "confidence": float(probs[top_idx]),
            "all_probs": {
                self.EMOTIONS[i]: float(probs[i])
                for i in range(len(self.EMOTIONS))
            }
        }

    @classmethod
    def from_pretrained(
        cls,
        model_path: str,
        config: Optional[Emotion2VecConfig] = None
    ) -> "Emotion2VecMLX":
        """
        Load pretrained weights.

        Args:
            model_path: Path to MLX weights (.safetensors or .npz)
            config: Model configuration

        Returns:
            Loaded model
        """
        import os

        model = cls(config)

        if model_path.endswith(".safetensors"):
            weights = mx.load(model_path)
        elif model_path.endswith(".npz"):
            weights = dict(mx.load(model_path))
        else:
            # Try to find weights file
            for ext in [".safetensors", ".npz"]:
                path = os.path.join(model_path, f"weights{ext}")
                if os.path.exists(path):
                    weights = mx.load(path)
                    break
            else:
                raise FileNotFoundError(f"No weights found in {model_path}")

        model.load_weights(list(weights.items()))
        return model


# Convenience functions

def load_emotion2vec(
    model_size: str = "base",
    weights_path: Optional[str] = None
) -> Emotion2VecMLX:
    """
    Load Emotion2Vec model.

    Args:
        model_size: "base" or "large"
        weights_path: Path to converted MLX weights

    Returns:
        Emotion2Vec model
    """
    if model_size == "large":
        config = Emotion2VecConfig.large()
    else:
        config = Emotion2VecConfig.base()

    if weights_path:
        return Emotion2VecMLX.from_pretrained(weights_path, config)

    return Emotion2VecMLX(config)
