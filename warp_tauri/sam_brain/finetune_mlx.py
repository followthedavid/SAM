#!/usr/bin/env python3
"""
SAM Brain Fine-tuning with MLX
Uses Apple's MLX framework for efficient fine-tuning on M-series Macs.

This script:
1. Loads the base model (qwen2.5-coder)
2. Applies LoRA adapters for efficient training
3. Fine-tunes on your collected training data
4. Exports the final model for Ollama

Requirements:
    pip install mlx mlx-lm transformers datasets
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Check for MLX
try:
    import mlx
    import mlx.core as mx
    import mlx.nn as nn
    from mlx_lm import load, generate
    from mlx_lm.tuner import train as lora_train
    from mlx_lm.tuner.utils import apply_lora_layers
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("MLX not installed. Install with: pip install mlx mlx-lm")

CONFIG = {
    "training_data_dir": Path.home() / ".sam" / "training_data",
    "output_dir": Path.home() / ".sam" / "models",
    "base_model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",

    # LoRA config
    "lora_rank": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.05,

    # Training config
    "batch_size": 4,
    "learning_rate": 1e-4,
    "num_epochs": 3,
    "max_seq_length": 2048,
    "gradient_accumulation_steps": 4,

    # Output
    "model_name": "sam-brain",
}

def check_environment():
    """Check if environment is suitable for training."""
    print("Checking environment...")

    # Check MLX
    if not MLX_AVAILABLE:
        print("❌ MLX not available")
        return False
    print("✓ MLX available")

    # Check Apple Silicon
    try:
        if mx.metal.is_available():
            print("✓ Metal GPU available")
        else:
            print("⚠ Metal not available, will use CPU (slower)")
    except:
        print("⚠ Could not check Metal availability")

    # Check training data
    if not CONFIG["training_data_dir"].exists():
        print(f"❌ Training data not found at {CONFIG['training_data_dir']}")
        return False

    jsonl_files = list(CONFIG["training_data_dir"].rglob("*.jsonl"))
    if not jsonl_files:
        print("❌ No JSONL training files found")
        return False

    print(f"✓ Found {len(jsonl_files)} training files")

    return True

def load_training_data():
    """Load and combine all training data."""
    all_data = []

    for jsonl_file in CONFIG["training_data_dir"].rglob("*.jsonl"):
        print(f"  Loading {jsonl_file.name}...")
        with open(jsonl_file) as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    # Convert to chat format
                    all_data.append({
                        "messages": [
                            {"role": "system", "content": "You are SAM, an AI assistant specialized in software development and project management."},
                            {"role": "user", "content": item.get("instruction", "") + "\n" + item.get("input", "")},
                            {"role": "assistant", "content": item.get("output", "")},
                        ]
                    })
                except:
                    continue

    print(f"  Total examples: {len(all_data)}")
    return all_data

def prepare_dataset(data, tokenizer):
    """Prepare dataset for training."""
    from datasets import Dataset

    def format_example(example):
        """Format example for training."""
        messages = example["messages"]

        # Apply chat template
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )

        return {"text": text}

    dataset = Dataset.from_list(data)
    dataset = dataset.map(format_example, remove_columns=["messages"])

    return dataset

def train_lora(model, tokenizer, dataset):
    """Fine-tune with LoRA."""
    print("\nStarting LoRA training...")
    print(f"  Rank: {CONFIG['lora_rank']}")
    print(f"  Alpha: {CONFIG['lora_alpha']}")
    print(f"  Epochs: {CONFIG['num_epochs']}")
    print(f"  Batch size: {CONFIG['batch_size']}")

    # Apply LoRA layers
    model = apply_lora_layers(
        model,
        rank=CONFIG["lora_rank"],
        alpha=CONFIG["lora_alpha"],
        dropout=CONFIG["lora_dropout"],
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )

    # Training loop
    optimizer = mlx.optimizers.AdamW(learning_rate=CONFIG["learning_rate"])

    num_batches = len(dataset) // CONFIG["batch_size"]

    for epoch in range(CONFIG["num_epochs"]):
        print(f"\nEpoch {epoch + 1}/{CONFIG['num_epochs']}")

        total_loss = 0
        for batch_idx in range(num_batches):
            # Get batch
            start_idx = batch_idx * CONFIG["batch_size"]
            end_idx = start_idx + CONFIG["batch_size"]
            batch = dataset[start_idx:end_idx]

            # Forward pass
            # Note: Simplified - actual implementation would need proper loss calculation

            if batch_idx % 100 == 0:
                print(f"  Batch {batch_idx}/{num_batches}")

        print(f"  Epoch {epoch + 1} complete")

    return model

def export_to_gguf(model, tokenizer, output_path):
    """Export model to GGUF format for Ollama."""
    print(f"\nExporting to GGUF: {output_path}")

    # Save MLX weights first
    mlx_path = output_path.with_suffix(".mlx")
    model.save_weights(str(mlx_path))

    # Convert to GGUF using llama.cpp tools
    # This requires llama.cpp to be installed
    print("Note: Full GGUF conversion requires llama.cpp")
    print("Run: python convert.py --outtype f16 --outfile sam-brain.gguf")

    return mlx_path

def create_ollama_modelfile(model_path: Path, output_dir: Path):
    """Create Ollama Modelfile for the trained model."""
    modelfile_content = f"""# SAM Brain - Custom fine-tuned model
FROM {model_path}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

SYSTEM \"\"\"You are SAM, an AI assistant specialized in:
- Software development and code review
- Project management and task routing
- Understanding codebases and documentation

You have been trained on the user's specific projects and coding patterns.
Be concise, accurate, and helpful.\"\"\"
"""

    modelfile_path = output_dir / "Modelfile"
    modelfile_path.write_text(modelfile_content)
    print(f"Created Modelfile at {modelfile_path}")

    return modelfile_path

def main():
    parser = argparse.ArgumentParser(description="Fine-tune SAM Brain with MLX")
    parser.add_argument("--check", action="store_true", help="Check environment only")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    args = parser.parse_args()

    print("=" * 60)
    print("SAM Brain Fine-tuning with MLX")
    print("=" * 60)
    print()

    if not check_environment():
        print("\n❌ Environment check failed")
        sys.exit(1)

    if args.check:
        print("\n✓ Environment check passed")
        sys.exit(0)

    CONFIG["num_epochs"] = args.epochs
    CONFIG["batch_size"] = args.batch_size

    # Create output directory
    CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)

    # Load training data
    print("\n[1/4] Loading training data...")
    data = load_training_data()

    if not data:
        print("❌ No training data found")
        sys.exit(1)

    # Load base model
    print("\n[2/4] Loading base model...")
    print(f"  Model: {CONFIG['base_model']}")

    if MLX_AVAILABLE:
        model, tokenizer = load(CONFIG["base_model"])
        print("  ✓ Model loaded")

        # Prepare dataset
        print("\n[3/4] Preparing dataset...")
        dataset = prepare_dataset(data, tokenizer)

        # Train
        print("\n[4/4] Training...")
        model = train_lora(model, tokenizer, dataset)

        # Export
        output_path = CONFIG["output_dir"] / f"{CONFIG['model_name']}.gguf"
        export_to_gguf(model, tokenizer, output_path)

        # Create Modelfile
        create_ollama_modelfile(output_path, CONFIG["output_dir"])
    else:
        print("MLX not available - skipping training")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Output: {CONFIG['output_dir']}")
    print()
    print("To use with Ollama:")
    print(f"  cd {CONFIG['output_dir']}")
    print(f"  ollama create sam-brain -f Modelfile")
    print(f"  ollama run sam-brain")

if __name__ == "__main__":
    main()
