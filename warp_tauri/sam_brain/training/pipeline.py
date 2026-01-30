#!/usr/bin/env python3
"""
SAM Training Pipeline - Automated model fine-tuning on your coding style.

Workflow:
1. Collect training data from interactions
2. Validate and clean data
3. Convert to training format
4. Run MLX fine-tuning (Apple Silicon optimized)
5. Evaluate and deploy new model

Designed to run periodically when enough new data accumulates.

Moved from learn/training_pipeline.py during Phase 3 consolidation.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field

SCRIPT_DIR = Path(__file__).parent
TRAINING_DATA = SCRIPT_DIR / "training_data.jsonl"
MODELS_DIR = SCRIPT_DIR / "models"
CHECKPOINTS_DIR = SCRIPT_DIR / "checkpoints"
LOGS_DIR = SCRIPT_DIR / "training_logs"

# Training configuration
MIN_SAMPLES_FOR_TRAINING = 100
BASE_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
LORA_RANK = 8
LEARNING_RATE = 1e-4
EPOCHS = 3
BATCH_SIZE = 4


@dataclass
class TrainingRun:
    run_id: str
    start_time: str
    samples_count: int
    status: str  # pending, training, completed, failed
    base_model: str = ""
    metrics: Dict = field(default_factory=dict)
    output_path: Optional[str] = None
    source: Optional[str] = None


class TrainingPipeline:
    def __init__(self):
        MODELS_DIR.mkdir(exist_ok=True)
        CHECKPOINTS_DIR.mkdir(exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)
        self.runs_file = SCRIPT_DIR / "training_runs.json"
        self.runs: List[TrainingRun] = self._load_runs()

    def _load_runs(self) -> List[TrainingRun]:
        """Load training run history."""
        if self.runs_file.exists():
            data = json.load(open(self.runs_file))
            return [TrainingRun(**r) for r in data]
        return []

    def _save_runs(self):
        """Save training run history."""
        data = [
            {
                "run_id": r.run_id,
                "start_time": r.start_time,
                "samples_count": r.samples_count,
                "base_model": r.base_model,
                "status": r.status,
                "metrics": r.metrics,
                "output_path": r.output_path,
                "source": r.source
            }
            for r in self.runs
        ]
        json.dump(data, open(self.runs_file, "w"), indent=2)

    def load_training_data(self) -> List[Dict]:
        """Load and validate training data."""
        if not TRAINING_DATA.exists():
            return []

        samples = []
        for line in TRAINING_DATA.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                sample = json.loads(line)
                # Validate required fields
                if "input" in sample and "output" in sample:
                    samples.append(sample)
            except json.JSONDecodeError:
                pass

        return samples

    def prepare_dataset(self, samples: List[Dict], output_dir: Path) -> Path:
        """Convert samples to MLX training format."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Split into train/val
        split_idx = int(len(samples) * 0.9)
        train_samples = samples[:split_idx]
        val_samples = samples[split_idx:]

        # Convert to chat format for Qwen
        def convert_sample(sample: Dict) -> Dict:
            return {
                "messages": [
                    {"role": "user", "content": sample["input"]},
                    {"role": "assistant", "content": sample["output"]}
                ]
            }

        # Write train.jsonl
        train_file = output_dir / "train.jsonl"
        with open(train_file, "w") as f:
            for sample in train_samples:
                f.write(json.dumps(convert_sample(sample)) + "\n")

        # Write valid.jsonl
        val_file = output_dir / "valid.jsonl"
        with open(val_file, "w") as f:
            for sample in val_samples:
                f.write(json.dumps(convert_sample(sample)) + "\n")

        print(f"Prepared {len(train_samples)} train, {len(val_samples)} val samples")
        return output_dir

    def check_mlx_available(self) -> bool:
        """Check if MLX is available for training."""
        try:
            result = subprocess.run(
                ["python3", "-c", "import mlx; import mlx_lm"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def run_training(self, dataset_dir: Path, output_dir: Path) -> bool:
        """Run MLX LoRA fine-tuning."""
        if not self.check_mlx_available():
            print("MLX not available. Install with: pip install mlx mlx-lm")
            return False

        cmd = [
            "python3", "-m", "mlx_lm.lora",
            "--model", BASE_MODEL,
            "--data", str(dataset_dir),
            "--train",
            "--batch-size", str(BATCH_SIZE),
            "--lora-layers", "8",
            "--iters", str(EPOCHS * 100),  # Approximate
            "--learning-rate", str(LEARNING_RATE),
            "--adapter-path", str(output_dir / "adapters"),
        ]

        log_file = LOGS_DIR / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        print(f"Starting training... Log: {log_file}")
        with open(log_file, "w") as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)

        return result.returncode == 0

    def should_train(self) -> bool:
        """Check if we have enough new data to train."""
        samples = self.load_training_data()
        if len(samples) < MIN_SAMPLES_FOR_TRAINING:
            return False

        # Check if we've trained on this data already
        last_run = self.runs[-1] if self.runs else None
        if last_run and last_run.samples_count >= len(samples):
            return False

        return True

    def start_training(self) -> Optional[TrainingRun]:
        """Start a new training run."""
        samples = self.load_training_data()
        if len(samples) < MIN_SAMPLES_FOR_TRAINING:
            print(f"Not enough samples ({len(samples)}/{MIN_SAMPLES_FOR_TRAINING})")
            return None

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = TrainingRun(
            run_id=run_id,
            start_time=datetime.now().isoformat(),
            samples_count=len(samples),
            base_model=BASE_MODEL,
            status="training",
            metrics={}
        )
        self.runs.append(run)
        self._save_runs()

        # Prepare dataset
        dataset_dir = CHECKPOINTS_DIR / run_id / "dataset"
        output_dir = MODELS_DIR / f"sam-coder-{run_id}"

        self.prepare_dataset(samples, dataset_dir)

        # Run training
        success = self.run_training(dataset_dir, output_dir)

        if success:
            run.status = "completed"
            run.output_path = str(output_dir)
            print(f"Training completed: {output_dir}")
        else:
            run.status = "failed"
            print("Training failed")

        self._save_runs()
        return run

    def list_models(self) -> List[Dict]:
        """List available fine-tuned models."""
        models = []
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                adapter_path = model_dir / "adapters"
                if adapter_path.exists():
                    models.append({
                        "name": model_dir.name,
                        "path": str(model_dir),
                        "adapter_path": str(adapter_path),
                        "created": datetime.fromtimestamp(model_dir.stat().st_mtime).isoformat()
                    })
        return models

    def export_to_ollama(self, model_path: Path, model_name: str) -> bool:
        """Export fine-tuned model to Ollama."""
        # Create Modelfile
        modelfile_content = f"""FROM {BASE_MODEL}
ADAPTER {model_path}/adapters

SYSTEM You are SAM, a helpful AI coding assistant. You help with coding tasks, file operations, and project management.

PARAMETER temperature 0.7
PARAMETER top_p 0.9
"""

        modelfile_path = model_path / "Modelfile"
        modelfile_path.write_text(modelfile_content)

        # Create Ollama model
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", str(modelfile_path)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"Created Ollama model: {model_name}")
            return True
        else:
            print(f"Failed to create Ollama model: {result.stderr}")
            return False

    def stats(self) -> Dict:
        """Get pipeline statistics."""
        samples = self.load_training_data()
        return {
            "total_samples": len(samples),
            "min_for_training": MIN_SAMPLES_FOR_TRAINING,
            "ready_to_train": len(samples) >= MIN_SAMPLES_FOR_TRAINING,
            "training_runs": len(self.runs),
            "completed_runs": len([r for r in self.runs if r.status == "completed"]),
            "available_models": len(self.list_models()),
            "mlx_available": self.check_mlx_available()
        }


def main():
    import sys

    pipeline = TrainingPipeline()

    if len(sys.argv) < 2:
        print("SAM Training Pipeline")
        print("-" * 40)
        stats = pipeline.stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print("\nCommands: train, status, models, export <model> <name>")
        return

    cmd = sys.argv[1]

    if cmd == "train":
        if pipeline.should_train():
            pipeline.start_training()
        else:
            print("Not ready to train (need more data or already trained)")

    elif cmd == "status":
        stats = pipeline.stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "models":
        models = pipeline.list_models()
        if models:
            print("Available models:")
            for m in models:
                print(f"  {m['name']}: {m['path']}")
        else:
            print("No models available")

    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: pipeline.py export <model_path> <ollama_name>")
            return
        model_path = Path(sys.argv[2])
        ollama_name = sys.argv[3]
        pipeline.export_to_ollama(model_path, ollama_name)

    elif cmd == "force":
        # Force training even if below threshold
        pipeline.start_training()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
