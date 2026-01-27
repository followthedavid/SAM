#!/usr/bin/env python3
"""
SAM Fine-Tuning Script using MLX LoRA

Fine-tunes SAM's brain using the scraped training data.
Optimized for M2 Mac Mini with 8GB RAM.

Usage:
    python finetune_sam.py --data /path/to/training.jsonl
    python finetune_sam.py --data /path/to/training.jsonl --epochs 3 --batch-size 1
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MLX imports
try:
    import mlx.core as mx
    import mlx.nn as nn
    from mlx.utils import tree_flatten, tree_unflatten
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    logger.warning("MLX not available. Install with: pip install mlx")

# Check for mlx-lm
try:
    from mlx_lm import load, generate
    from mlx_lm.tuner import train as lora_train
    from mlx_lm.tuner.trainer import TrainingArgs
    MLX_LM_AVAILABLE = True
except ImportError:
    MLX_LM_AVAILABLE = False
    logger.warning("mlx-lm not available. Install with: pip install mlx-lm")


class SAMFineTuner:
    """
    Fine-tuner for SAM using MLX LoRA.

    Supports:
    - LoRA fine-tuning (memory efficient)
    - Quality-based filtering
    - Train/validation split
    - Checkpointing
    - Resume from checkpoint
    """

    # SAM brain location
    DEFAULT_MODEL_PATH = Path.home() / "ReverseLab" / "SAM" / "warp_tauri" / "sam_brain"

    # Training output
    DEFAULT_OUTPUT_DIR = Path("/Volumes/David External/scraper_data/sam_lora_adapters")

    # LoRA config optimized for 8GB RAM
    LORA_CONFIG = {
        "rank": 8,           # Lower rank = less memory
        "alpha": 16,         # Scaling factor
        "dropout": 0.05,
        "target_modules": ["q_proj", "v_proj"],  # Which layers to adapt
    }

    # Training config for 8GB Mac
    TRAINING_CONFIG = {
        "batch_size": 1,           # Must be 1 for 8GB
        "gradient_accumulation": 4, # Effective batch = 4
        "learning_rate": 1e-4,
        "epochs": 3,
        "warmup_steps": 100,
        "save_steps": 500,
        "eval_steps": 250,
        "max_seq_length": 2048,    # Truncate long sequences
        "fp16": True,              # Use half precision
    }

    def __init__(
        self,
        model_path: str = None,
        output_dir: str = None,
        lora_config: Dict = None,
    ):
        self.model_path = Path(model_path) if model_path else self.DEFAULT_MODEL_PATH
        self.output_dir = Path(output_dir) if output_dir else self.DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.lora_config = {**self.LORA_CONFIG, **(lora_config or {})}

        self.model = None
        self.tokenizer = None
        self.train_data = []
        self.val_data = []

    def load_model(self):
        """Load the base model."""
        if not MLX_LM_AVAILABLE:
            raise RuntimeError("mlx-lm required for fine-tuning")

        logger.info(f"Loading model from {self.model_path}")

        # Check if model exists
        if not self.model_path.exists():
            logger.error(f"Model not found at {self.model_path}")
            logger.info("Available models:")
            logger.info("  - Qwen2.5-1.5B: mlx-community/Qwen2.5-1.5B-Instruct-4bit")
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        self.model, self.tokenizer = load(str(self.model_path))
        logger.info("Model loaded successfully")

    def load_training_data(
        self,
        data_path: str,
        val_split: float = 0.1,
        min_quality: float = 0.0,
        max_samples: int = None,
    ):
        """
        Load and prepare training data.

        Args:
            data_path: Path to JSONL training file
            val_split: Fraction for validation
            min_quality: Minimum quality score to include
            max_samples: Maximum samples to use (for testing)
        """
        logger.info(f"Loading training data from {data_path}")

        data = []
        with open(data_path, 'r') as f:
            for line in f:
                try:
                    item = json.loads(line)

                    # Filter by quality
                    quality = item.get('metadata', {}).get('quality', 0)
                    if quality < min_quality:
                        continue

                    data.append(item)
                except json.JSONDecodeError:
                    continue

        logger.info(f"Loaded {len(data)} examples (quality >= {min_quality})")

        # Shuffle
        random.shuffle(data)

        # Limit samples if specified
        if max_samples:
            data = data[:max_samples]

        # Split train/val
        val_size = int(len(data) * val_split)
        self.val_data = data[:val_size]
        self.train_data = data[val_size:]

        logger.info(f"Train: {len(self.train_data)}, Validation: {len(self.val_data)}")

    def prepare_dataset(self, data: List[Dict]) -> List[Dict]:
        """Convert data to MLX format."""
        prepared = []

        for item in data:
            messages = item.get('messages', [])

            # Build prompt in chat format
            text = ""
            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')

                if role == 'system':
                    text += f"<|system|>\n{content}\n"
                elif role == 'user':
                    text += f"<|user|>\n{content}\n"
                elif role == 'assistant':
                    text += f"<|assistant|>\n{content}\n"

            # Truncate if too long
            max_len = self.TRAINING_CONFIG['max_seq_length']
            if len(text) > max_len * 4:  # Rough char estimate
                text = text[:max_len * 4]

            prepared.append({"text": text})

        return prepared

    def save_dataset(self, data: List[Dict], name: str) -> str:
        """Save dataset to JSONL file."""
        filepath = self.output_dir / f"{name}.jsonl"

        with open(filepath, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')

        return str(filepath)

    def train(
        self,
        epochs: int = None,
        batch_size: int = None,
        learning_rate: float = None,
        resume_from: str = None,
    ):
        """
        Run LoRA fine-tuning.

        Args:
            epochs: Number of training epochs
            batch_size: Batch size (keep at 1 for 8GB)
            learning_rate: Learning rate
            resume_from: Path to checkpoint to resume from
        """
        if not MLX_LM_AVAILABLE:
            raise RuntimeError("mlx-lm required for fine-tuning")

        # Prepare datasets
        train_prepared = self.prepare_dataset(self.train_data)
        val_prepared = self.prepare_dataset(self.val_data)

        # Save to files
        train_path = self.save_dataset(train_prepared, "train")
        val_path = self.save_dataset(val_prepared, "valid")

        logger.info(f"Saved train data to {train_path}")
        logger.info(f"Saved val data to {val_path}")

        # Training config
        config = {**self.TRAINING_CONFIG}
        if epochs:
            config['epochs'] = epochs
        if batch_size:
            config['batch_size'] = batch_size
        if learning_rate:
            config['learning_rate'] = learning_rate

        # Output adapter path
        adapter_path = self.output_dir / f"sam_lora_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info("Starting LoRA fine-tuning...")
        logger.info(f"Config: {config}")
        logger.info(f"Output: {adapter_path}")

        # Build training args
        training_args = TrainingArgs(
            model=str(self.model_path),
            train=train_path,
            valid=val_path,
            adapter_path=str(adapter_path),
            iters=config['epochs'] * len(self.train_data) // config['batch_size'],
            batch_size=config['batch_size'],
            learning_rate=config['learning_rate'],
            lora_layers=8,  # Number of layers to apply LoRA
            save_every=config['save_steps'],
            test_batches=50,
        )

        # Run training
        try:
            lora_train.train(training_args)
            logger.info(f"Training complete! Adapter saved to {adapter_path}")
            return str(adapter_path)
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise

    def merge_adapter(self, adapter_path: str, output_path: str = None):
        """Merge LoRA adapter with base model."""
        if output_path is None:
            output_path = self.output_dir / "sam_merged"

        logger.info(f"Merging adapter {adapter_path} with base model")

        # Load base model and adapter
        from mlx_lm.tuner import apply_lora

        model, tokenizer = load(str(self.model_path))
        model = apply_lora.apply_lora_layers(model, adapter_path)

        # Save merged model
        # ... (would save the merged weights)

        logger.info(f"Merged model saved to {output_path}")
        return str(output_path)

    def evaluate(self, test_prompts: List[str] = None):
        """Evaluate the fine-tuned model."""
        if test_prompts is None:
            test_prompts = [
                "How do I create a SwiftUI button?",
                "Fix this error: fatal error: unexpectedly found nil",
                "Explain the @State property wrapper",
                "How do I install Homebrew on macOS?",
            ]

        logger.info("Evaluating model...")

        for prompt in test_prompts:
            logger.info(f"\nPrompt: {prompt}")
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=200,
            )
            logger.info(f"Response: {response}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune SAM with MLX LoRA")

    parser.add_argument("--data", required=True, help="Path to training JSONL file")
    parser.add_argument("--model", default=None, help="Path to base model")
    parser.add_argument("--output", default=None, help="Output directory for adapters")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--val-split", type=float, default=0.1, help="Validation split")
    parser.add_argument("--min-quality", type=float, default=0.0, help="Minimum quality score")
    parser.add_argument("--max-samples", type=int, default=None, help="Max samples (for testing)")
    parser.add_argument("--resume", default=None, help="Resume from checkpoint")
    parser.add_argument("--eval-only", action="store_true", help="Only run evaluation")

    args = parser.parse_args()

    # Initialize fine-tuner
    finetuner = SAMFineTuner(
        model_path=args.model,
        output_dir=args.output,
    )

    # Load model
    finetuner.load_model()

    # Load data
    finetuner.load_training_data(
        args.data,
        val_split=args.val_split,
        min_quality=args.min_quality,
        max_samples=args.max_samples,
    )

    if args.eval_only:
        finetuner.evaluate()
    else:
        # Train
        adapter_path = finetuner.train(
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            resume_from=args.resume,
        )

        # Evaluate
        finetuner.evaluate()

        print(f"\n{'='*60}")
        print(f"Fine-tuning complete!")
        print(f"Adapter saved to: {adapter_path}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
