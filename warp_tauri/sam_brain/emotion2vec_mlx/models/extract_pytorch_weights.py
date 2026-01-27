#!/usr/bin/env python3
"""
Extract Emotion2Vec weights from PyTorch format to numpy.
This script only requires torch, not mlx.

The extracted numpy weights can then be converted to MLX
using convert_to_mlx.py.
"""

import argparse
import os
from pathlib import Path
import numpy as np


def download_emotion2vec(model_name: str, cache_dir: str = None) -> str:
    """Download Emotion2Vec model."""
    try:
        from huggingface_hub import snapshot_download

        hf_name = model_name.replace("iic/", "emotion2vec/")
        print(f"Downloading {hf_name} from HuggingFace...")

        model_dir = snapshot_download(
            repo_id=hf_name,
            cache_dir=cache_dir,
        )
        return model_dir

    except Exception as e:
        print(f"Download failed: {e}")
        raise


def extract_weights(model_path: str, output_path: str):
    """
    Extract weights from PyTorch checkpoint to numpy format.
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

    # Convert to numpy and save
    weights = {}
    for name, tensor in state_dict.items():
        weights[name] = tensor.numpy()

    print(f"Loaded {len(weights)} weight tensors")
    print("\nWeight shapes:")
    for name, arr in list(weights.items())[:10]:
        print(f"  {name}: {arr.shape}")
    if len(weights) > 10:
        print(f"  ... and {len(weights) - 10} more")

    # Save as npz
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, **weights)

    print(f"\nSaved numpy weights to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Extract Emotion2Vec PyTorch weights to numpy")
    parser.add_argument(
        "--model",
        default="emotion2vec/emotion2vec_plus_base",
        help="Model name on HuggingFace"
    )
    parser.add_argument(
        "--output",
        default="./emotion2vec_weights.npz",
        help="Output npz file path"
    )
    parser.add_argument(
        "--local",
        help="Path to local checkpoint (skip download)"
    )

    args = parser.parse_args()

    if args.local:
        model_path = args.local
    else:
        model_path = download_emotion2vec(args.model)

    extract_weights(model_path, args.output)
    print("\nNext step: Convert to MLX format with:")
    print(f"  python3 convert_to_mlx.py --input {args.output}")


if __name__ == "__main__":
    main()
