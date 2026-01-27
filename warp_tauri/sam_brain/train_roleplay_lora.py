#!/usr/bin/env python3
"""
SAM Roleplay LoRA Training - Optimized for 8GB Mac
Trains on nifty archive data for creative fiction mode
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace

# MLX imports
import mlx.core as mx
import mlx.optimizers as optim
from mlx_lm import load
from mlx_lm.tuner.trainer import TrainingArgs, train
from mlx_lm.tuner.datasets import load_dataset, CacheDataset
from mlx_lm.tuner.utils import linear_to_lora_layers

# Configuration for 8GB
CONFIG = {
    "model_name": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    "training_data": Path("/Volumes/David External/nifty_archive/training_data"),
    "output_dir": Path("/Volumes/David External/nifty_archive/models/sam-roleplay-qwen-lora"),

    # LoRA config
    "lora_layers": 16,  # Apply to more layers
    "lora_rank": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.05,

    # Training config (8GB optimized)
    "batch_size": 1,
    "grad_accum_steps": 4,
    "learning_rate": 2e-5,  # Lower learning rate for stability
    "num_iters": 300,
    "max_seq_length": 1024,

    # Save config
    "save_every": 100,
    "val_batches": 10,
}


def count_params(params):
    """Recursively count parameters in nested dict."""
    total = 0
    for v in params.values():
        if isinstance(v, dict):
            total += count_params(v)
        elif hasattr(v, 'size'):
            total += v.size
    return total


def convert_training_data():
    """Convert nifty training data to MLX format."""
    print("\n[1/4] Converting training data to MLX format...")

    train_path = CONFIG["training_data"] / "train.jsonl"
    valid_path = CONFIG["training_data"] / "valid.jsonl"

    if not train_path.exists():
        print(f"ERROR: Training data not found at {train_path}")
        sys.exit(1)

    CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)

    mlx_train_path = CONFIG["output_dir"] / "train.jsonl"
    mlx_valid_path = CONFIG["output_dir"] / "valid.jsonl"

    def convert_file(input_path: Path, output_path: Path) -> int:
        count = 0
        with open(input_path) as f_in, open(output_path, "w") as f_out:
            for line in f_in:
                try:
                    item = json.loads(line.strip())
                    messages = item.get("messages", [])

                    text_parts = []
                    for msg in messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")

                        if role == "system":
                            text_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
                        elif role == "user":
                            text_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
                        elif role == "assistant":
                            text_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

                    if text_parts:
                        full_text = "\n".join(text_parts)
                        if len(full_text) <= CONFIG["max_seq_length"] * 4:
                            f_out.write(json.dumps({"text": full_text}) + "\n")
                            count += 1
                except:
                    continue
        return count

    train_count = convert_file(train_path, mlx_train_path)
    valid_count = convert_file(valid_path, mlx_valid_path)

    print(f"  Converted: {train_count} train, {valid_count} valid examples")
    return mlx_train_path, mlx_valid_path, train_count


def train_lora():
    """Train LoRA adapter on roleplay data."""
    print("\n[2/4] Loading base model...")

    model, tokenizer = load(CONFIG["model_name"])

    print(f"  Model: {CONFIG['model_name']}")
    print(f"  Parameters: {count_params(model.parameters()):,}")

    print("\n[3/4] Setting up LoRA training...")

    # LoRA config
    lora_config = {
        "rank": CONFIG["lora_rank"],
        "alpha": CONFIG["lora_alpha"],
        "dropout": CONFIG["lora_dropout"],
        "scale": CONFIG["lora_alpha"] / CONFIG["lora_rank"],
    }

    # Apply LoRA layers
    linear_to_lora_layers(model, CONFIG["lora_layers"], lora_config)

    trainable = count_params(model.trainable_parameters())
    total = count_params(model.parameters())
    print(f"  Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # Create args namespace for load_dataset
    train_path = CONFIG["output_dir"] / "train.jsonl"
    valid_path = CONFIG["output_dir"] / "valid.jsonl"

    data_args = SimpleNamespace(
        data=str(CONFIG["output_dir"]),
        train=True,
        test=False,
        hf_dataset=False,
    )

    # Load datasets and wrap in CacheDataset for tokenization
    train_raw, valid_raw, _ = load_dataset(data_args, tokenizer)
    train_set = CacheDataset(train_raw)
    valid_set = CacheDataset(valid_raw)

    print(f"  Train samples: {len(train_set)}")
    print(f"  Valid samples: {len(valid_set)}")

    # Create optimizer
    optimizer = optim.Adam(learning_rate=CONFIG["learning_rate"])

    # Training args
    adapter_file = str(CONFIG["output_dir"] / "adapters.safetensors")
    args = TrainingArgs(
        batch_size=CONFIG["batch_size"],
        iters=CONFIG["num_iters"],
        val_batches=CONFIG["val_batches"],
        steps_per_report=10,
        steps_per_eval=50,
        steps_per_save=CONFIG["save_every"],
        adapter_file=adapter_file,
        max_seq_length=CONFIG["max_seq_length"],
        grad_checkpoint=True,
        grad_accumulation_steps=CONFIG["grad_accum_steps"],
    )

    print("\n[4/4] Training LoRA adapter...")
    print("  Progress will be shown every 10 steps")
    print("-" * 60)

    start_time = datetime.now()

    # Train
    train(
        model=model,
        optimizer=optimizer,
        train_dataset=train_set,
        val_dataset=valid_set,
        args=args,
    )

    duration = datetime.now() - start_time

    print("-" * 60)
    print(f"\n✓ Training complete!")
    print(f"  Duration: {duration}")
    print(f"  Adapter saved to: {CONFIG['output_dir']}")

    # Save config
    config_path = CONFIG["output_dir"] / "adapter_config.json"
    with open(config_path, "w") as f:
        json.dump({
            "adapter_path": str(CONFIG["output_dir"]),
            "base_model": CONFIG["model_name"],
            "lora_config": lora_config,
            "training_data": str(CONFIG["training_data"]),
            "trained_at": datetime.now().isoformat(),
            "duration_seconds": duration.total_seconds(),
            "purpose": "roleplay/creative_fiction",
        }, f, indent=2)


def test_inference():
    """Test the trained adapter."""
    print("\n[Test] Loading trained adapter...")

    adapter_path = CONFIG["output_dir"] / "adapters.safetensors"
    if not adapter_path.exists():
        print("  No adapter found, skipping test")
        return

    from mlx_lm import generate

    model, tokenizer = load(
        CONFIG["model_name"],
        adapter_path=str(CONFIG["output_dir"]),
    )

    prompt = """<|im_start|>system
You are roleplaying as a character in adult creative fiction. Stay in character.<|im_end|>
<|im_start|>user
Write a short romantic scene between two characters meeting at a coffee shop.<|im_end|>
<|im_start|>assistant
"""

    print("\nTest prompt:", prompt[:80] + "...")

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=256,
        temp=0.7,
    )

    print("\nResponse:")
    print(response[:500])


def main():
    parser = argparse.ArgumentParser(description="Train SAM Roleplay LoRA")
    parser.add_argument("--convert-only", action="store_true", help="Only convert data")
    parser.add_argument("--test-only", action="store_true", help="Only test adapter")
    parser.add_argument("--iters", type=int, help="Override iterations")
    args = parser.parse_args()

    if args.iters:
        CONFIG["num_iters"] = args.iters

    print("=" * 60)
    print("SAM Roleplay LoRA Training")
    print("=" * 60)
    print(f"Base model: {CONFIG['model_name']}")
    print(f"Training data: {CONFIG['training_data']}")
    print(f"Output: {CONFIG['output_dir']}")
    print(f"Iterations: {CONFIG['num_iters']}")
    print("=" * 60)

    if args.test_only:
        test_inference()
        return

    convert_training_data()

    if args.convert_only:
        print("\n✓ Data conversion complete")
        return

    train_lora()
    test_inference()


if __name__ == "__main__":
    main()
