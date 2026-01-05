#!/usr/bin/env python3
"""
SAM Brain Training - Optimized for 8GB Mac
Uses MLX with LoRA for memory-efficient fine-tuning
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# MLX imports
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx_lm import load, generate
from mlx_lm.tuner.trainer import TrainingArgs, train
from mlx_lm.tuner.datasets import load_dataset

# Configuration for 8GB
CONFIG = {
    "model_name": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",  # Pre-quantized
    "training_data": Path.home() / ".sam" / "training_data",
    "output_dir": Path.home() / ".sam" / "models" / "sam-brain-lora",

    # LoRA config (memory efficient)
    "lora_layers": 8,       # Number of layers to adapt
    "lora_rank": 4,         # Low rank for 8GB
    "lora_alpha": 8,
    "lora_dropout": 0.05,

    # Training config (8GB optimized)
    "batch_size": 1,        # Must be 1 for 8GB
    "grad_accum_steps": 4,  # Effective batch = 4
    "learning_rate": 1e-4,
    "num_epochs": 1,        # Start with 1 epoch
    "max_seq_length": 512,  # Shorter for memory
    "warmup_steps": 10,

    # Save config
    "save_every": 100,
    "val_batches": 10,
}

def prepare_training_data():
    """Load and format training data."""
    print("\n[1/4] Preparing training data...")

    all_data = []

    # Load all JSONL files
    for jsonl_file in CONFIG["training_data"].rglob("*.jsonl"):
        print(f"  Loading {jsonl_file.name}...")
        with open(jsonl_file) as f:
            for line in f:
                try:
                    item = json.loads(line.strip())

                    # Format as chat
                    instruction = item.get("instruction", "")
                    input_text = item.get("input", "")
                    output = item.get("output", "")

                    # Combine into single prompt-response pair
                    prompt = f"{instruction}\n{input_text}".strip()

                    if prompt and output:
                        all_data.append({
                            "prompt": prompt[:CONFIG["max_seq_length"]],
                            "response": output[:CONFIG["max_seq_length"]],
                        })
                except:
                    continue

    print(f"  Total examples: {len(all_data)}")

    # Split train/val
    split_idx = int(len(all_data) * 0.95)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]

    print(f"  Train: {len(train_data)}, Val: {len(val_data)}")

    # Save formatted data
    train_path = CONFIG["output_dir"] / "train.jsonl"
    val_path = CONFIG["output_dir"] / "val.jsonl"

    CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)

    with open(train_path, "w") as f:
        for item in train_data:
            f.write(json.dumps({"text": f"<|im_start|>user\n{item['prompt']}<|im_end|>\n<|im_start|>assistant\n{item['response']}<|im_end|>"}) + "\n")

    with open(val_path, "w") as f:
        for item in val_data:
            f.write(json.dumps({"text": f"<|im_start|>user\n{item['prompt']}<|im_end|>\n<|im_start|>assistant\n{item['response']}<|im_end|>"}) + "\n")

    return train_path, val_path, len(train_data)

def train_lora():
    """Run LoRA fine-tuning with MLX."""

    print("\n" + "=" * 60)
    print("SAM Brain Training - 8GB Optimized")
    print("=" * 60)

    # Check GPU
    print(f"\nMetal GPU: {mx.metal.is_available()}")
    print(f"Device: {mx.default_device()}")

    # Prepare data
    train_path, val_path, num_examples = prepare_training_data()

    # Calculate steps
    steps_per_epoch = num_examples // (CONFIG["batch_size"] * CONFIG["grad_accum_steps"])
    total_steps = steps_per_epoch * CONFIG["num_epochs"]

    print(f"\n[2/4] Training configuration:")
    print(f"  Model: {CONFIG['model_name']}")
    print(f"  LoRA rank: {CONFIG['lora_rank']}")
    print(f"  Batch size: {CONFIG['batch_size']} (effective: {CONFIG['batch_size'] * CONFIG['grad_accum_steps']})")
    print(f"  Learning rate: {CONFIG['learning_rate']}")
    print(f"  Steps per epoch: {steps_per_epoch}")
    print(f"  Total steps: {total_steps}")

    # Load model
    print(f"\n[3/4] Loading model...")
    print("  This may take a minute...")

    model, tokenizer = load(CONFIG["model_name"])
    print("  Model loaded!")

    # Set up training args
    adapter_file = str(CONFIG["output_dir"] / "adapters.safetensors")
    training_args = TrainingArgs(
        batch_size=CONFIG["batch_size"],
        iters=total_steps,
        val_batches=CONFIG["val_batches"],
        steps_per_report=10,
        steps_per_eval=50,
        steps_per_save=CONFIG["save_every"],
        adapter_file=adapter_file,
        max_seq_length=CONFIG["max_seq_length"],
        grad_checkpoint=True,  # Save memory
        grad_accumulation_steps=CONFIG["grad_accum_steps"],
    )

    # LoRA config
    lora_config = {
        "rank": CONFIG["lora_rank"],
        "alpha": CONFIG["lora_alpha"],
        "dropout": CONFIG["lora_dropout"],
        "scale": CONFIG["lora_alpha"] / CONFIG["lora_rank"],
    }

    print(f"\n[4/4] Starting training...")
    print("  (This will take 1-2 hours for 1 epoch)")
    print("  Progress will be shown every 10 steps")
    print("-" * 60)

    # Train
    start_time = datetime.now()

    try:
        train(
            model=model,
            tokenizer=tokenizer,
            args=training_args,
            train_dataset=load_dataset(str(train_path)),
            val_dataset=load_dataset(str(val_path)),
            lora_config=lora_config,
        )

        duration = datetime.now() - start_time
        print("-" * 60)
        print(f"\n✓ Training complete!")
        print(f"  Duration: {duration}")
        print(f"  Adapters saved to: {CONFIG['output_dir'] / 'adapters'}")

        # Save config
        with open(CONFIG["output_dir"] / "training_config.json", "w") as f:
            json.dump({
                "model": CONFIG["model_name"],
                "lora_rank": CONFIG["lora_rank"],
                "training_examples": num_examples,
                "duration_seconds": duration.total_seconds(),
                "completed": datetime.now().isoformat(),
            }, f, indent=2)

        return True

    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        return False

def quick_test():
    """Quick test with minimal training."""
    print("\n" + "=" * 60)
    print("Quick Training Test (10 steps)")
    print("=" * 60)

    # Use even smaller settings for test
    CONFIG["num_epochs"] = 1
    CONFIG["max_seq_length"] = 256

    # Prepare minimal data
    train_path, val_path, num_examples = prepare_training_data()

    print(f"\nLoading model {CONFIG['model_name']}...")
    model, tokenizer = load(CONFIG["model_name"])
    print("Model loaded!")

    # Just 10 steps for test
    adapter_file = str(CONFIG["output_dir"] / "test_adapters.safetensors")
    training_args = TrainingArgs(
        batch_size=1,
        iters=10,
        val_batches=2,
        steps_per_report=2,
        steps_per_eval=5,
        adapter_file=adapter_file,
        max_seq_length=256,
        grad_checkpoint=True,
        grad_accumulation_steps=1,
    )

    lora_config = {
        "rank": 4,
        "alpha": 8,
        "dropout": 0.0,
        "scale": 2.0,
    }

    print("\nRunning 10 training steps...")

    try:
        train(
            model=model,
            tokenizer=tokenizer,
            args=training_args,
            train_dataset=load_dataset(str(train_path)),
            val_dataset=load_dataset(str(val_path)),
            lora_config=lora_config,
        )
        print("\n✓ Quick test passed! GPU training works.")
        return True
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run quick 10-step test")
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs")
    args = parser.parse_args()

    if args.test:
        success = quick_test()
    else:
        CONFIG["num_epochs"] = args.epochs
        success = train_lora()

    sys.exit(0 if success else 1)
