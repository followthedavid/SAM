#!/usr/bin/env python3
"""
Convert extracted numpy weights to MLX format.
Maps data2vec naming to our MLX model structure.

Usage:
    python3 convert_to_mlx.py --input emotion2vec_pytorch.npz --output weights.safetensors
"""

import argparse
from pathlib import Path
import numpy as np
import mlx.core as mx


def map_weights(pytorch_weights: dict) -> dict:
    """
    Map data2vec/emotion2vec weight names to our MLX model structure.

    Emotion2Vec uses the data2vec 2.0 architecture with:
    - d2v_model.modality_encoders.AUDIO.local_encoder: CNN feature extractor
    - d2v_model.modality_encoders.AUDIO.context_encoder.blocks: Audio encoder layers
    - d2v_model.blocks: Shared transformer blocks (8 layers)

    Weight naming:
    - attn.qkv.weight: Combined Q, K, V projection (2304, 768)
    - attn.proj.weight: Output projection
    - mlp.fc1/fc2: Feed-forward
    - norm1/norm2: Layer norms
    """
    mlx_weights = {}

    for pt_name, weight in pytorch_weights.items():
        mlx_name = None

        # ============ Feature Extractor (CNN) ============
        # d2v_model.modality_encoders.AUDIO.local_encoder.conv_layers.X.0.weight
        if "local_encoder.conv_layers" in pt_name:
            parts = pt_name.split(".")
            # Find the layer index
            for i, p in enumerate(parts):
                if p == "conv_layers" and i + 1 < len(parts):
                    layer_idx = parts[i + 1]
                    sub_idx = parts[i + 2] if i + 2 < len(parts) else ""

                    if sub_idx == "0":  # Conv layer
                        if "weight" in pt_name:
                            # Conv weight: [out, in, kernel] -> [out, kernel, in] for MLX
                            weight = np.transpose(weight, (0, 2, 1))
                            mlx_name = f"feature_extractor.conv_layers.{layer_idx}.weight"
                        elif "bias" in pt_name:
                            mlx_name = f"feature_extractor.conv_layers.{layer_idx}.bias"
                    elif sub_idx == "2":  # Group norm
                        if "weight" in pt_name:
                            mlx_name = f"feature_extractor.layer_norms.{layer_idx}.weight"
                        elif "bias" in pt_name:
                            mlx_name = f"feature_extractor.layer_norms.{layer_idx}.bias"
                    break

        # d2v_model.modality_encoders.AUDIO.project_features
        # project_features.2 is the main projection (512 -> 768)
        elif "project_features.2" in pt_name:
            if "weight" in pt_name:
                mlx_name = "feature_extractor.projection.weight"
                # Weight is [768, 512] in PyTorch, MLX Linear expects [out, in] = [768, 512]
                # No transpose needed
            elif "bias" in pt_name:
                mlx_name = "feature_extractor.projection.bias"
        elif "project_features" in pt_name:
            # Skip project_features.1 (layer norm before projection)
            continue

        # ============ Transformer Blocks ============
        # Use d2v_model.blocks (shared transformer, 8 layers) as main encoder
        # These are at top level: d2v_model.blocks.0.attn.qkv.weight
        elif pt_name.startswith("d2v_model.blocks."):
            parts = pt_name.split(".")
            if len(parts) >= 4:
                layer_idx = parts[2]  # Block index (0-7 for 8 layers)

                # Attention: attn.qkv and attn.proj
                if ".attn.qkv." in pt_name:
                    # Combined QKV: [2304, 768] -> split to [768, 768] x 3
                    # PyTorch and MLX both use [out, in] format - no transpose needed
                    hidden_size = weight.shape[0] // 3
                    if "weight" in pt_name:
                        q_weight = weight[:hidden_size]
                        k_weight = weight[hidden_size:2*hidden_size]
                        v_weight = weight[2*hidden_size:]
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.q_proj.weight"] = q_weight
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.k_proj.weight"] = k_weight
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.v_proj.weight"] = v_weight
                    elif "bias" in pt_name:
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.q_proj.bias"] = weight[:hidden_size]
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.k_proj.bias"] = weight[hidden_size:2*hidden_size]
                        mlx_weights[f"encoder.layers.{layer_idx}.attention.v_proj.bias"] = weight[2*hidden_size:]
                    continue  # Already handled

                elif ".attn.proj." in pt_name:
                    if "weight" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.attention.out_proj.weight"
                        # PyTorch and MLX both use [out, in] for Linear - no transpose
                    elif "bias" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.attention.out_proj.bias"

                # Feed-forward: mlp.fc1/fc2
                elif ".mlp.fc1." in pt_name:
                    if "weight" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.feed_forward.fc1.weight"
                        # PyTorch and MLX both use [out, in] for Linear - no transpose
                    elif "bias" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.feed_forward.fc1.bias"

                elif ".mlp.fc2." in pt_name:
                    if "weight" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.feed_forward.fc2.weight"
                        # PyTorch and MLX both use [out, in] for Linear - no transpose
                    elif "bias" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.feed_forward.fc2.bias"

                # Layer norms
                elif ".norm1." in pt_name:
                    if "weight" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.ln1.weight"
                    elif "bias" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.ln1.bias"

                elif ".norm2." in pt_name:
                    if "weight" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.ln2.weight"
                    elif "bias" in pt_name:
                        mlx_name = f"encoder.layers.{layer_idx}.ln2.bias"

        # ============ Final Layer Norm ============
        # context_encoder.norm is the final layer norm
        elif "context_encoder.norm" in pt_name:
            if "weight" in pt_name:
                mlx_name = "encoder.final_ln.weight"
            elif "bias" in pt_name:
                mlx_name = "encoder.final_ln.bias"

        # ============ Classifier ============
        # proj.weight/bias is the emotion classifier in emotion2vec
        # PyTorch Linear stores as [out, in] = [9, 768], MLX same format - no transpose
        elif pt_name == "proj.weight":
            mlx_name = "classifier.classifier.weight"
        elif pt_name == "proj.bias":
            mlx_name = "classifier.classifier.bias"

        # ============ Legacy Classifier (if present) ============
        elif "classifier" in pt_name or "head" in pt_name:
            if "weight" in pt_name:
                mlx_name = "classifier.classifier.weight"
                # No transpose - PyTorch and MLX both use [out, in]
            elif "bias" in pt_name:
                mlx_name = "classifier.classifier.bias"

        # Skip special tensors
        if mlx_name is None:
            if any(x in pt_name for x in [
                "extra_tokens", "alibi", "decoder", "target", "ema",
                "context_encoder", "modality"  # Skip audio-specific encoder for now
            ]):
                continue
            # Uncomment to see what's being skipped:
            # print(f"Skipping: {pt_name}")
            continue

        mlx_weights[mlx_name] = weight

    return mlx_weights


def convert_to_mlx(input_path: str, output_path: str, format: str = "safetensors"):
    """Convert numpy weights to MLX format."""

    print(f"Loading numpy weights from {input_path}")
    data = np.load(input_path)
    pytorch_weights = {name: data[name] for name in data.files}
    print(f"Loaded {len(pytorch_weights)} weight tensors")

    print("\nMapping weight names...")
    mlx_weights = map_weights(pytorch_weights)
    print(f"Mapped {len(mlx_weights)} weights to MLX format")

    print("\nMLX weight names:")
    for name in sorted(mlx_weights.keys())[:20]:
        print(f"  {name}: {mlx_weights[name].shape}")
    if len(mlx_weights) > 20:
        print(f"  ... and {len(mlx_weights) - 20} more")

    # Convert to MLX arrays
    print("\nConverting to MLX arrays...")
    mlx_arrays = {name: mx.array(weight) for name, weight in mlx_weights.items()}

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "safetensors":
        if not str(output_path).endswith(".safetensors"):
            output_path = output_path.with_suffix(".safetensors")
        mx.save_safetensors(str(output_path), mlx_arrays)
    else:
        if not str(output_path).endswith(".npz"):
            output_path = output_path.with_suffix(".npz")
        mx.savez(str(output_path), **mlx_arrays)

    print(f"\nSaved MLX weights to {output_path}")

    # Also save config
    config_path = output_path.parent / "config.json"
    import json
    config = {
        "model_type": "emotion2vec",
        "model_size": "base",
        "hidden_size": 768,
        "num_attention_heads": 12,
        "num_hidden_layers": 8,  # 8 transformer blocks in emotion2vec
        "intermediate_size": 3072,
        "conv_dim": 512,
        "conv_layers": 7,
        "num_emotions": 9,
        "emotions": [
            "angry", "disgusted", "fearful", "happy",
            "neutral", "other", "sad", "surprised", "unknown"
        ],
        "weights_format": format,
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Saved config to {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert numpy weights to MLX")
    parser.add_argument("--input", required=True, help="Input npz file")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--format", choices=["safetensors", "npz"], default="safetensors")

    args = parser.parse_args()

    if args.output is None:
        args.output = Path(args.input).parent / f"emotion2vec_base.{args.format}"

    convert_to_mlx(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
