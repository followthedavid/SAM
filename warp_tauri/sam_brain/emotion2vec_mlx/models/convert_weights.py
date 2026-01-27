#!/usr/bin/env python3
"""
Convert Emotion2Vec PyTorch weights to MLX format.

Usage:
    python convert_weights.py --model emotion2vec_plus_base --output ./weights
    python convert_weights.py --model emotion2vec_plus_large --output ./weights
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any

import mlx.core as mx
import numpy as np


def download_emotion2vec_pytorch(model_name: str, cache_dir: str = None) -> str:
    """
    Download Emotion2Vec model using HuggingFace/FunASR/ModelScope.

    Args:
        model_name: Model identifier (e.g., "emotion2vec/emotion2vec_plus_base")
        cache_dir: Directory to cache model

    Returns:
        Path to downloaded model
    """
    # Try HuggingFace first (most common)
    try:
        from huggingface_hub import snapshot_download

        # Convert iic/ prefix to emotion2vec/ for HuggingFace
        hf_name = model_name.replace("iic/", "emotion2vec/")
        print(f"Downloading {hf_name} from HuggingFace...")

        model_dir = snapshot_download(
            repo_id=hf_name,
            cache_dir=cache_dir,
            local_dir=cache_dir,  # Download to specific location if provided
        )
        return model_dir

    except Exception as e:
        print(f"HuggingFace download failed: {e}")

    # Try FunASR
    try:
        from funasr import AutoModel

        print(f"Downloading {model_name} via FunASR...")
        model = AutoModel(
            model=model_name,
            hub="hf",
        )
        return model.model_path

    except ImportError:
        pass
    except Exception as e:
        print(f"FunASR download failed: {e}")

    # Try ModelScope
    try:
        from modelscope.hub.snapshot_download import snapshot_download

        print(f"Downloading {model_name} via ModelScope...")
        model_dir = snapshot_download(model_name, cache_dir=cache_dir)
        return model_dir

    except ImportError:
        pass
    except Exception as e:
        print(f"ModelScope download failed: {e}")

    raise RuntimeError(
        "Failed to download model. Install one of:\n"
        "  pip install huggingface_hub\n"
        "  pip install funasr\n"
        "  pip install modelscope"
    )


def load_pytorch_weights(model_path: str) -> Dict[str, np.ndarray]:
    """
    Load PyTorch weights from Emotion2Vec checkpoint.

    Args:
        model_path: Path to model directory or checkpoint file

    Returns:
        Dictionary of weight name -> numpy array
    """
    import torch

    model_path = Path(model_path)

    # Find checkpoint file
    checkpoint_file = None
    for name in ["model.pt", "pytorch_model.bin", "model.bin"]:
        candidate = model_path / name
        if candidate.exists():
            checkpoint_file = candidate
            break

    if checkpoint_file is None:
        # Maybe it's a direct file path
        if model_path.is_file():
            checkpoint_file = model_path
        else:
            raise FileNotFoundError(f"No checkpoint found in {model_path}")

    print(f"Loading PyTorch weights from {checkpoint_file}")

    # Load checkpoint
    state_dict = torch.load(checkpoint_file, map_location="cpu")

    # Handle nested state dicts
    if "model" in state_dict:
        state_dict = state_dict["model"]
    elif "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    # Convert to numpy
    weights = {}
    for name, tensor in state_dict.items():
        weights[name] = tensor.numpy()

    return weights


def map_weight_names(pytorch_weights: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """
    Map PyTorch weight names to MLX model structure.

    Emotion2Vec uses data2vec/wav2vec2-style naming.
    """
    mlx_weights = {}

    # Weight name mapping patterns
    mapping = {
        # Feature extractor (CNN)
        "feature_extractor.conv_layers": "feature_extractor.conv_layers",
        "post_extract_proj": "feature_extractor.projection",
        "layer_norm": "feature_extractor.layer_norm",

        # Transformer encoder
        "encoder.layers": "encoder.layers",
        "encoder.layer_norm": "encoder.final_ln",

        # Attention
        "self_attn.q_proj": "attention.q_proj",
        "self_attn.k_proj": "attention.k_proj",
        "self_attn.v_proj": "attention.v_proj",
        "self_attn.out_proj": "attention.out_proj",

        # Feed-forward
        "fc1": "feed_forward.fc1",
        "fc2": "feed_forward.fc2",

        # Layer norms
        "self_attn_layer_norm": "ln1",
        "final_layer_norm": "ln2",

        # Classifier
        "classifier": "classifier",
    }

    for pt_name, weight in pytorch_weights.items():
        mlx_name = pt_name

        # Apply mappings
        for pt_pattern, mlx_pattern in mapping.items():
            if pt_pattern in mlx_name:
                mlx_name = mlx_name.replace(pt_pattern, mlx_pattern)

        # Handle conv layers specially
        if "conv_layers" in mlx_name:
            # Transpose conv weights from [out, in, kernel] to [out, kernel, in]
            if weight.ndim == 3:
                weight = np.transpose(weight, (0, 2, 1))

        mlx_weights[mlx_name] = weight

    return mlx_weights


def convert_emotion2vec(
    model_name: str = "iic/emotion2vec_plus_base",
    output_dir: str = "./weights",
    format: str = "safetensors"
) -> str:
    """
    Download and convert Emotion2Vec model to MLX format.

    Args:
        model_name: Model identifier
        output_dir: Output directory
        format: Output format ("safetensors" or "npz")

    Returns:
        Path to converted weights
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine model size from name
    if "large" in model_name.lower():
        model_size = "large"
    else:
        model_size = "base"

    print(f"Converting {model_name} ({model_size})")

    # Download model
    try:
        model_path = download_emotion2vec_pytorch(model_name)
    except Exception as e:
        print(f"Failed to download model: {e}")
        print("\nAlternative: Download manually and provide path")
        return None

    # Load PyTorch weights
    pytorch_weights = load_pytorch_weights(model_path)
    print(f"Loaded {len(pytorch_weights)} weight tensors")

    # Map weight names
    mlx_weights = map_weight_names(pytorch_weights)

    # Convert to MLX arrays
    mlx_arrays = {
        name: mx.array(weight)
        for name, weight in mlx_weights.items()
    }

    # Save
    if format == "safetensors":
        output_file = output_dir / f"emotion2vec_{model_size}.safetensors"
        mx.save_safetensors(str(output_file), mlx_arrays)
    else:
        output_file = output_dir / f"emotion2vec_{model_size}.npz"
        mx.savez(str(output_file), **mlx_arrays)

    print(f"Saved MLX weights to {output_file}")

    # Save config
    config_file = output_dir / f"config_{model_size}.json"
    import json
    config = {
        "model_size": model_size,
        "hidden_size": 1024 if model_size == "large" else 768,
        "num_attention_heads": 16 if model_size == "large" else 12,
        "num_hidden_layers": 24 if model_size == "large" else 12,
        "intermediate_size": 4096 if model_size == "large" else 3072,
        "num_emotions": 9,
        "emotions": [
            "angry", "disgusted", "fearful", "happy",
            "neutral", "other", "sad", "surprised", "unknown"
        ],
        "source_model": model_name,
    }
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Saved config to {config_file}")

    return str(output_file)


def convert_from_local(
    checkpoint_path: str,
    output_dir: str = "./weights",
    model_size: str = "base",
    format: str = "safetensors"
) -> str:
    """
    Convert a local PyTorch checkpoint to MLX.

    Args:
        checkpoint_path: Path to PyTorch checkpoint
        output_dir: Output directory
        model_size: "base" or "large"
        format: Output format

    Returns:
        Path to converted weights
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting local checkpoint: {checkpoint_path}")

    # Load PyTorch weights
    pytorch_weights = load_pytorch_weights(checkpoint_path)
    print(f"Loaded {len(pytorch_weights)} weight tensors")

    # Print some weight names for debugging
    print("\nSample weight names:")
    for i, name in enumerate(list(pytorch_weights.keys())[:10]):
        print(f"  {name}: {pytorch_weights[name].shape}")

    # Map weight names
    mlx_weights = map_weight_names(pytorch_weights)

    # Convert to MLX arrays
    mlx_arrays = {
        name: mx.array(weight)
        for name, weight in mlx_weights.items()
    }

    # Save
    if format == "safetensors":
        output_file = output_dir / f"emotion2vec_{model_size}.safetensors"
        mx.save_safetensors(str(output_file), mlx_arrays)
    else:
        output_file = output_dir / f"emotion2vec_{model_size}.npz"
        mx.savez(str(output_file), **mlx_arrays)

    print(f"Saved MLX weights to {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="Convert Emotion2Vec to MLX")
    parser.add_argument(
        "--model",
        default="iic/emotion2vec_plus_base",
        help="Model name or local path"
    )
    parser.add_argument(
        "--output",
        default="./weights",
        help="Output directory"
    )
    parser.add_argument(
        "--format",
        choices=["safetensors", "npz"],
        default="safetensors",
        help="Output format"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Model path is a local checkpoint"
    )
    parser.add_argument(
        "--size",
        choices=["base", "large"],
        default="base",
        help="Model size (for local conversion)"
    )

    args = parser.parse_args()

    if args.local:
        convert_from_local(
            args.model,
            args.output,
            args.size,
            args.format
        )
    else:
        convert_emotion2vec(
            args.model,
            args.output,
            args.format
        )


if __name__ == "__main__":
    main()
