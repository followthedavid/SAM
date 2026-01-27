#!/usr/bin/env python3
"""
Cloud Training Orchestrator for SAM

Hybrid architecture:
- LOCAL (8GB Mac): Data prep, scoring, deduplication, inference
- CLOUD BURST: Heavy training that exceeds local capabilities

TRAINING TIERS:
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 1: LOCAL (8GB Mac)                                             │
│   - LoRA/DoRA/QLoRA on 1-3B models                                  │
│   - Data preprocessing & scoring                                    │
│   - Inference & evaluation                                          │
│   - Cost: $0                                                        │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 2: CLOUD LIGHT (16-24GB) - ~$0.50-1/hr                         │
│   - Full fine-tuning of 3-7B models                                 │
│   - Larger LoRA ranks                                               │
│   - Longer contexts (8K-16K)                                        │
│   - Providers: Vast.ai, RunPod, Lambda                              │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 3: CLOUD MEDIUM (40-80GB) - ~$1-2/hr                           │
│   - RLHF with reward model                                          │
│   - DPO on 7-13B models                                             │
│   - Constitutional AI training                                      │
│   - Providers: Lambda A100, RunPod A100                             │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 4: CLOUD HEAVY (Multi-GPU) - ~$5-20/hr                         │
│   - Mixture of Experts training                                     │
│   - 70B+ model fine-tuning                                          │
│   - RLHF at scale                                                   │
│   - Distributed training                                            │
│   - Providers: Lambda 8xA100, AWS p4d, GCP TPU                      │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 5: MANAGED SERVICES (Variable)                                 │
│   - Together.ai fine-tuning API                                     │
│   - Replicate training                                              │
│   - Hugging Face AutoTrain                                          │
│   - OpenPipe fine-tuning                                            │
│   - Cost: Per-token or per-job pricing                              │
└─────────────────────────────────────────────────────────────────────┘

WHAT EACH TIER UNLOCKS:
- Tier 2: Better base models, longer context
- Tier 3: RLHF, constitutional AI, preference learning at scale
- Tier 4: Frontier capabilities, MoE, massive scale
- Tier 5: Simplicity, no infra management
"""

import json
import os
import subprocess
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

# ============================================================================
# Cloud Provider Configurations
# ============================================================================

class CloudProvider(Enum):
    LOCAL = "local"
    VAST_AI = "vast.ai"
    RUNPOD = "runpod"
    LAMBDA = "lambda"
    MODAL = "modal"
    TOGETHER = "together"
    REPLICATE = "replicate"
    AWS_SAGEMAKER = "aws_sagemaker"
    GCP_VERTEX = "gcp_vertex"
    HUGGINGFACE = "huggingface"

class TrainingTier(Enum):
    LOCAL = 1           # 8GB, free
    CLOUD_LIGHT = 2     # 16-24GB, ~$0.50-1/hr
    CLOUD_MEDIUM = 3    # 40-80GB, ~$1-2/hr
    CLOUD_HEAVY = 4     # Multi-GPU, ~$5-20/hr
    MANAGED = 5         # API-based, variable

@dataclass
class CloudConfig:
    """Configuration for a cloud provider."""
    provider: CloudProvider
    tier: TrainingTier
    gpu_type: str
    vram_gb: int
    hourly_cost: float
    setup_script: str = ""
    api_key_env: str = ""
    notes: str = ""

# Provider configurations
CLOUD_CONFIGS = {
    # Tier 2: Light
    "vast_rtx4090": CloudConfig(
        provider=CloudProvider.VAST_AI,
        tier=TrainingTier.CLOUD_LIGHT,
        gpu_type="RTX 4090",
        vram_gb=24,
        hourly_cost=0.40,
        api_key_env="VAST_API_KEY",
        notes="Best price/performance for 24GB"
    ),
    "runpod_rtx4090": CloudConfig(
        provider=CloudProvider.RUNPOD,
        tier=TrainingTier.CLOUD_LIGHT,
        gpu_type="RTX 4090",
        vram_gb=24,
        hourly_cost=0.74,
        api_key_env="RUNPOD_API_KEY",
        notes="Reliable, good UI"
    ),

    # Tier 3: Medium
    "lambda_a100_40": CloudConfig(
        provider=CloudProvider.LAMBDA,
        tier=TrainingTier.CLOUD_MEDIUM,
        gpu_type="A100 40GB",
        vram_gb=40,
        hourly_cost=1.10,
        api_key_env="LAMBDA_API_KEY",
        notes="Best for RLHF, good reliability"
    ),
    "vast_a100_80": CloudConfig(
        provider=CloudProvider.VAST_AI,
        tier=TrainingTier.CLOUD_MEDIUM,
        gpu_type="A100 80GB",
        vram_gb=80,
        hourly_cost=1.50,
        api_key_env="VAST_API_KEY",
        notes="Full A100, can train 13B models"
    ),
    "runpod_a100": CloudConfig(
        provider=CloudProvider.RUNPOD,
        tier=TrainingTier.CLOUD_MEDIUM,
        gpu_type="A100 80GB",
        vram_gb=80,
        hourly_cost=1.99,
        api_key_env="RUNPOD_API_KEY",
        notes="Reliable A100 access"
    ),

    # Tier 4: Heavy
    "lambda_8xa100": CloudConfig(
        provider=CloudProvider.LAMBDA,
        tier=TrainingTier.CLOUD_HEAVY,
        gpu_type="8x A100 80GB",
        vram_gb=640,
        hourly_cost=12.00,
        api_key_env="LAMBDA_API_KEY",
        notes="Full node, for 70B+ or distributed"
    ),
    "aws_p4d": CloudConfig(
        provider=CloudProvider.AWS_SAGEMAKER,
        tier=TrainingTier.CLOUD_HEAVY,
        gpu_type="8x A100 40GB",
        vram_gb=320,
        hourly_cost=32.77,
        api_key_env="AWS_ACCESS_KEY_ID",
        notes="Enterprise, expensive but reliable"
    ),

    # Tier 5: Managed
    "together_finetune": CloudConfig(
        provider=CloudProvider.TOGETHER,
        tier=TrainingTier.MANAGED,
        gpu_type="Managed",
        vram_gb=0,  # Abstracted
        hourly_cost=0,  # Per-token pricing
        api_key_env="TOGETHER_API_KEY",
        notes="~$3/M tokens for fine-tuning"
    ),
    "replicate_train": CloudConfig(
        provider=CloudProvider.REPLICATE,
        tier=TrainingTier.MANAGED,
        gpu_type="Managed",
        vram_gb=0,
        hourly_cost=0,
        api_key_env="REPLICATE_API_TOKEN",
        notes="Simple API, good for LoRA"
    ),
    "huggingface_autotrain": CloudConfig(
        provider=CloudProvider.HUGGINGFACE,
        tier=TrainingTier.MANAGED,
        gpu_type="Managed",
        vram_gb=0,
        hourly_cost=0,
        api_key_env="HF_TOKEN",
        notes="Integrated with HF ecosystem"
    ),
}

# ============================================================================
# Training Capabilities by Tier
# ============================================================================

TIER_CAPABILITIES = {
    TrainingTier.LOCAL: {
        "name": "Local (8GB Mac)",
        "cost_per_hour": 0,
        "capabilities": [
            "LoRA/DoRA/QLoRA on 1-3B models",
            "Data preprocessing & scoring",
            "Semantic deduplication",
            "Inference & evaluation",
            "Curriculum stage 1-2",
        ],
        "limitations": [
            "Max ~3B parameters",
            "Short context (2K-4K)",
            "No full fine-tuning",
            "No RLHF",
        ],
        "recommended_for": [
            "Development & iteration",
            "Data pipeline testing",
            "Quick experiments",
            "Inference deployment",
        ]
    },
    TrainingTier.CLOUD_LIGHT: {
        "name": "Cloud Light (16-24GB)",
        "cost_per_hour": 0.50,
        "capabilities": [
            "Full fine-tuning of 3-7B models",
            "LoRA with larger ranks",
            "Longer context (8K-16K)",
            "DPO on 3-7B models",
            "Curriculum stages 1-4",
        ],
        "limitations": [
            "Single GPU only",
            "No RLHF (need reward model too)",
            "Max ~7B for full fine-tune",
        ],
        "recommended_for": [
            "Production LoRA training",
            "Qwen2.5-7B fine-tuning",
            "Mistral-7B fine-tuning",
        ]
    },
    TrainingTier.CLOUD_MEDIUM: {
        "name": "Cloud Medium (40-80GB)",
        "cost_per_hour": 1.50,
        "capabilities": [
            "RLHF with reward model",
            "Constitutional AI (CAI)",
            "DPO/ORPO on 7-13B models",
            "Full fine-tuning of 13B models",
            "Longer context (32K)",
            "All curriculum stages",
        ],
        "limitations": [
            "Single GPU (parallelism via gradient accumulation)",
            "70B models need quantization",
        ],
        "recommended_for": [
            "RLHF training",
            "Llama-13B fine-tuning",
            "Preference learning at scale",
            "Constitutional AI",
        ]
    },
    TrainingTier.CLOUD_HEAVY: {
        "name": "Cloud Heavy (Multi-GPU)",
        "cost_per_hour": 12.00,
        "capabilities": [
            "Mixture of Experts (MoE) training",
            "70B+ model fine-tuning",
            "RLHF at scale",
            "Distributed training (FSDP/DeepSpeed)",
            "Very long context (128K+)",
            "Speculative decoding training",
            "Multi-task learning",
        ],
        "limitations": [
            "High cost",
            "Complex setup",
            "Overkill for most tasks",
        ],
        "recommended_for": [
            "Frontier model training",
            "Research experiments",
            "Production models at scale",
        ]
    },
    TrainingTier.MANAGED: {
        "name": "Managed Services",
        "cost_per_hour": 0,  # Per-token
        "capabilities": [
            "Simple API-based fine-tuning",
            "No infrastructure management",
            "Automatic optimization",
            "Built-in evaluation",
        ],
        "limitations": [
            "Less control",
            "Limited customization",
            "Data must be uploaded",
            "Vendor lock-in",
        ],
        "recommended_for": [
            "Quick production fine-tunes",
            "Non-technical users",
            "When time > money",
        ]
    },
}

# ============================================================================
# Advanced Training Methods (Cloud-Only)
# ============================================================================

@dataclass
class RLHFConfig:
    """Configuration for RLHF training."""
    # Reward model
    reward_model: str = "OpenAssistant/reward-model-deberta-v3-large-v2"
    reward_model_max_length: int = 512

    # PPO parameters
    ppo_epochs: int = 4
    mini_batch_size: int = 4
    gradient_accumulation_steps: int = 8
    learning_rate: float = 1e-5
    kl_penalty: str = "kl"  # or "abs" or "mse"
    init_kl_coef: float = 0.2
    target_kl: float = 6.0
    clip_range: float = 0.2
    clip_range_value: float = 0.2

    # Generation
    max_new_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.9

    # Required VRAM: ~24GB for 3B, ~48GB for 7B, ~80GB for 13B
    min_vram_gb: int = 24


@dataclass
class ConstitutionalAIConfig:
    """Configuration for Constitutional AI training."""
    # Principles
    principles: List[str] = field(default_factory=lambda: [
        "Please choose the response that is most helpful, harmless, and honest.",
        "Please choose the response that is least likely to cause harm.",
        "Please choose the response that respects user autonomy.",
        "Please choose the response that is most accurate and truthful.",
    ])

    # Critique model (for generating critiques)
    critique_model: str = "gpt-4"  # or local model
    critique_temperature: float = 0.7

    # Revision rounds
    num_revision_rounds: int = 2

    # Required VRAM: ~40GB for full pipeline
    min_vram_gb: int = 40


@dataclass
class MoEConfig:
    """Configuration for Mixture of Experts training."""
    num_experts: int = 8
    num_experts_per_token: int = 2
    expert_capacity: int = 64

    # Router
    router_type: str = "top_k"  # or "expert_choice"
    router_jitter_noise: float = 0.1

    # Load balancing
    load_balancing_loss_coef: float = 0.01

    # Required VRAM: 8x base model size minimum
    min_vram_gb: int = 320  # For 70B MoE


# ============================================================================
# Cloud Training Orchestrator
# ============================================================================

class CloudTrainingOrchestrator:
    """
    Orchestrates training across local and cloud resources.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / ".sam" / "cloud_training.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cloud_jobs (
                job_id TEXT PRIMARY KEY,
                provider TEXT,
                tier INTEGER,
                config_json TEXT,

                -- Status
                status TEXT,  -- pending, uploading, running, completed, failed
                started_at TEXT,
                completed_at TEXT,

                -- Cost tracking
                estimated_cost REAL,
                actual_cost REAL,
                runtime_hours REAL,

                -- Results
                output_path TEXT,
                metrics_json TEXT,
                error TEXT,

                -- Data
                data_hash TEXT,  -- To track what data was used
                examples_count INTEGER
            );

            CREATE TABLE IF NOT EXISTS cost_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                job_id TEXT,
                amount REAL,
                timestamp TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS provider_credentials (
                provider TEXT PRIMARY KEY,
                api_key_encrypted TEXT,
                last_verified TEXT,
                quota_remaining REAL
            );
        """)
        conn.commit()
        conn.close()

    def recommend_tier(self, task: str, model_size_b: float,
                       context_length: int = 2048) -> TrainingTier:
        """Recommend appropriate tier for a task."""

        # RLHF always needs at least medium
        if "rlhf" in task.lower():
            if model_size_b > 13:
                return TrainingTier.CLOUD_HEAVY
            return TrainingTier.CLOUD_MEDIUM

        # Constitutional AI needs medium
        if "constitutional" in task.lower() or "cai" in task.lower():
            return TrainingTier.CLOUD_MEDIUM

        # MoE needs heavy
        if "moe" in task.lower() or "mixture" in task.lower():
            return TrainingTier.CLOUD_HEAVY

        # Full fine-tuning
        if "full" in task.lower():
            if model_size_b <= 3:
                return TrainingTier.CLOUD_LIGHT
            elif model_size_b <= 13:
                return TrainingTier.CLOUD_MEDIUM
            else:
                return TrainingTier.CLOUD_HEAVY

        # LoRA/QLoRA
        if model_size_b <= 3 and context_length <= 4096:
            return TrainingTier.LOCAL
        elif model_size_b <= 7:
            return TrainingTier.CLOUD_LIGHT
        elif model_size_b <= 13:
            return TrainingTier.CLOUD_MEDIUM
        else:
            return TrainingTier.CLOUD_HEAVY

    def estimate_cost(self, tier: TrainingTier, hours: float) -> Dict[str, float]:
        """Estimate training cost."""
        configs = [c for c in CLOUD_CONFIGS.values() if c.tier == tier]
        if not configs:
            return {"min": 0, "max": 0, "avg": 0}

        costs = [c.hourly_cost * hours for c in configs]
        return {
            "min": min(costs),
            "max": max(costs),
            "avg": sum(costs) / len(costs),
            "hours": hours
        }

    def estimate_training_time(self, examples: int, model_size_b: float,
                               method: str = "lora") -> float:
        """Estimate training time in hours."""
        # Rough estimates based on typical throughput
        if method == "lora":
            # ~1000 examples/hour on A100 for 7B
            base_throughput = 1000
        elif method == "full":
            # ~200 examples/hour on A100 for 7B
            base_throughput = 200
        elif method == "rlhf":
            # ~100 examples/hour (includes reward model inference)
            base_throughput = 100
        else:
            base_throughput = 500

        # Scale by model size (7B as baseline)
        size_factor = model_size_b / 7

        throughput = base_throughput / size_factor
        hours = examples / throughput

        return max(0.5, hours)  # Minimum 30 min

    def generate_cloud_script(self, config: str, provider: CloudProvider,
                              data_path: str, output_path: str) -> str:
        """Generate training script for cloud execution."""

        scripts = {
            CloudProvider.VAST_AI: self._vast_script,
            CloudProvider.RUNPOD: self._runpod_script,
            CloudProvider.LAMBDA: self._lambda_script,
            CloudProvider.MODAL: self._modal_script,
            CloudProvider.TOGETHER: self._together_script,
        }

        generator = scripts.get(provider, self._generic_script)
        return generator(config, data_path, output_path)

    def _vast_script(self, config: str, data_path: str, output_path: str) -> str:
        return f"""#!/bin/bash
# Vast.ai Training Script
# Run: vastai create instance <template_id> --onstart-cmd "bash /workspace/train.sh"

# Install dependencies
pip install torch transformers accelerate peft trl bitsandbytes
pip install mlx-lm  # If using MLX models

# Download data from local machine (or cloud storage)
# rsync -avz user@local:{data_path} /workspace/data/

# Or from S3/GCS
# aws s3 cp s3://bucket/{data_path} /workspace/data/

# Run training
python -m trl.scripts.sft \\
    --model_name_or_path {config} \\
    --dataset_name /workspace/data \\
    --output_dir {output_path} \\
    --per_device_train_batch_size 4 \\
    --gradient_accumulation_steps 4 \\
    --learning_rate 2e-4 \\
    --num_train_epochs 3 \\
    --bf16 True \\
    --logging_steps 10 \\
    --save_strategy "steps" \\
    --save_steps 100

# Upload results
# aws s3 cp {output_path} s3://bucket/models/
"""

    def _runpod_script(self, config: str, data_path: str, output_path: str) -> str:
        return f"""#!/bin/bash
# RunPod Training Script
# Use RunPod's template or custom Docker image

pip install torch transformers accelerate peft trl

# Training with TRL
python -c "
from trl import SFTTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from datasets import load_dataset

model = AutoModelForCausalLM.from_pretrained('{config}', torch_dtype='auto', device_map='auto')
tokenizer = AutoTokenizer.from_pretrained('{config}')

peft_config = LoraConfig(
    r=32,
    lora_alpha=64,
    lora_dropout=0.05,
    target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
)

trainer = SFTTrainer(
    model=model,
    train_dataset=load_dataset('json', data_files='{data_path}')['train'],
    peft_config=peft_config,
    max_seq_length=2048,
    output_dir='{output_path}',
)

trainer.train()
trainer.save_model()
"
"""

    def _lambda_script(self, config: str, data_path: str, output_path: str) -> str:
        return f"""#!/bin/bash
# Lambda Labs Training Script

# Lambda instances come with PyTorch pre-installed
pip install transformers accelerate peft trl datasets

# For RLHF
pip install trl[peft]

# Training script
python train_lambda.py \\
    --model {config} \\
    --data {data_path} \\
    --output {output_path}
"""

    def _modal_script(self, config: str, data_path: str, output_path: str) -> str:
        return f'''# Modal Training Script (Python)
import modal

stub = modal.Stub("sam-training")
image = modal.Image.debian_slim().pip_install(
    "torch", "transformers", "accelerate", "peft", "trl", "datasets"
)

@stub.function(gpu="A100", timeout=3600, image=image)
def train():
    from trl import SFTTrainer
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig
    from datasets import load_dataset

    model = AutoModelForCausalLM.from_pretrained("{config}", torch_dtype="auto")
    tokenizer = AutoTokenizer.from_pretrained("{config}")

    peft_config = LoraConfig(r=32, lora_alpha=64)

    trainer = SFTTrainer(
        model=model,
        train_dataset=load_dataset("json", data_files="{data_path}")["train"],
        peft_config=peft_config,
        output_dir="{output_path}",
    )

    trainer.train()
    return trainer.state.best_model_checkpoint

if __name__ == "__main__":
    with stub.run():
        result = train.remote()
        print(f"Training complete: {{result}}")
'''

    def _together_script(self, config: str, data_path: str, output_path: str) -> str:
        return f"""# Together.ai Fine-tuning API
import together

# Upload training data
file_id = together.Files.upload(file="{data_path}")

# Start fine-tuning job
response = together.Finetune.create(
    training_file=file_id,
    model="{config}",
    n_epochs=3,
    learning_rate=2e-4,
    suffix="sam-finetuned"
)

print(f"Job started: {{response['id']}}")
print(f"Monitor at: https://api.together.xyz/fine-tuning/{{response['id']}}")
"""

    def _generic_script(self, config: str, data_path: str, output_path: str) -> str:
        return f"""# Generic Training Script
# Adapt for your cloud provider

pip install torch transformers accelerate peft trl datasets

python -m trl.scripts.sft \\
    --model_name_or_path {config} \\
    --dataset_name {data_path} \\
    --output_dir {output_path}
"""

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        conn = sqlite3.connect(self.db_path)

        stats = {"jobs": {}, "costs": {}}

        # Job stats
        cursor = conn.execute("""
            SELECT status, COUNT(*), SUM(actual_cost)
            FROM cloud_jobs GROUP BY status
        """)
        for row in cursor:
            stats["jobs"][row[0]] = {"count": row[1], "cost": row[2] or 0}

        # Total cost
        cursor = conn.execute("SELECT SUM(amount) FROM cost_tracking")
        stats["costs"]["total"] = cursor.fetchone()[0] or 0

        # By provider
        cursor = conn.execute("""
            SELECT provider, SUM(amount) FROM cost_tracking GROUP BY provider
        """)
        stats["costs"]["by_provider"] = {r[0]: r[1] for r in cursor.fetchall()}

        conn.close()
        return stats


def show_capabilities():
    """Show all capabilities by tier."""
    print("=" * 80)
    print("SAM Training Capabilities by Tier")
    print("=" * 80)

    for tier, info in TIER_CAPABILITIES.items():
        print(f"\n{'─' * 80}")
        print(f"📊 {info['name']}")
        print(f"   Cost: ~${info['cost_per_hour']}/hr" if info['cost_per_hour'] else "   Cost: Free / Per-token")
        print(f"{'─' * 80}")

        print("\n   ✅ CAPABILITIES:")
        for cap in info["capabilities"]:
            print(f"      • {cap}")

        print("\n   ⚠️  LIMITATIONS:")
        for lim in info["limitations"]:
            print(f"      • {lim}")

        print("\n   🎯 RECOMMENDED FOR:")
        for rec in info["recommended_for"]:
            print(f"      • {rec}")

    print("\n" + "=" * 80)
    print("CLOUD PROVIDERS:")
    print("=" * 80)

    for name, config in CLOUD_CONFIGS.items():
        tier_name = TIER_CAPABILITIES[config.tier]["name"]
        print(f"\n   {name}:")
        print(f"      Provider: {config.provider.value}")
        print(f"      Tier: {tier_name}")
        print(f"      GPU: {config.gpu_type} ({config.vram_gb}GB)")
        print(f"      Cost: ${config.hourly_cost}/hr")
        print(f"      Notes: {config.notes}")


def estimate_project_cost():
    """Interactive cost estimator."""
    print("\n" + "=" * 60)
    print("SAM Training Cost Estimator")
    print("=" * 60)

    orchestrator = CloudTrainingOrchestrator()

    # Example scenarios
    scenarios = [
        ("LoRA on Qwen2.5-7B", "lora", 7, 10000),
        ("Full fine-tune Qwen2.5-7B", "full", 7, 10000),
        ("RLHF on Llama-13B", "rlhf", 13, 5000),
        ("DPO on Mistral-7B", "lora", 7, 10000),
        ("MoE training (experimental)", "full", 70, 50000),
    ]

    print("\nExample scenarios for 10,000 training examples:\n")

    for name, method, size, examples in scenarios:
        tier = orchestrator.recommend_tier(method, size)
        hours = orchestrator.estimate_training_time(examples, size, method)
        cost = orchestrator.estimate_cost(tier, hours)

        tier_name = TIER_CAPABILITIES[tier]["name"]
        print(f"📌 {name}")
        print(f"   Tier: {tier_name}")
        print(f"   Est. time: {hours:.1f} hours")
        print(f"   Est. cost: ${cost['min']:.2f} - ${cost['max']:.2f}")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "capabilities":
            show_capabilities()
        elif sys.argv[1] == "estimate":
            estimate_project_cost()
        else:
            print("Usage: python cloud_training_orchestrator.py [capabilities|estimate]")
    else:
        show_capabilities()
        print("\n")
        estimate_project_cost()
