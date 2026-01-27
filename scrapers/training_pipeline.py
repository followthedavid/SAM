#!/usr/bin/env python3
"""
MLX Training Pipeline for 8GB Mac Mini M2
Optimized for LoRA fine-tuning on Apple Silicon with limited RAM.

Supports:
- Llama 3.2 3B (recommended for 8GB)
- Qwen2.5-Coder 3B
- Phi-3 Mini 3.8B

Training data sources:
- Nifty.org stories (roleplay)
- AO3 works (roleplay)
- Your codebase (coding)
"""

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import re

# ============================================================================
# EXPLICIT CONTENT FILTER
# ============================================================================

class ExplicitContentFilter:
    """
    Filters and extracts explicit content from stories.
    Identifies relevant passages for erotic roleplay training.
    """

    # Keywords that indicate explicit content (weighted by relevance)
    EXPLICIT_KEYWORDS = {
        # High relevance (3 points)
        "cock": 3, "dick": 3, "cum": 3, "fucked": 3, "fucking": 3,
        "sucked": 3, "sucking": 3, "moaned": 3, "thrust": 3, "stroked": 3,
        "ass": 2, "hole": 2, "hard": 2, "wet": 2, "tight": 2,
        "naked": 2, "erection": 3, "orgasm": 3, "climax": 3,
        "licked": 2, "tongue": 2, "nipple": 2, "balls": 2,
        "precum": 3, "load": 2, "swallow": 2, "deep": 2,
        # Medium relevance (2 points)
        "pleasure": 2, "desire": 2, "aroused": 2, "panting": 2,
        "gasped": 2, "groaned": 2, "begged": 2, "whimpered": 2,
        "spread": 2, "entered": 2, "filled": 2, "pressed": 2,
        "gripped": 2, "grabbed": 2, "skin": 1, "body": 1,
        # Lower but relevant (1 point)
        "kiss": 1, "lips": 1, "touch": 1, "hands": 1, "fingers": 1,
        "breath": 1, "hot": 1, "warm": 1, "closer": 1,
    }

    # Phrases that strongly indicate explicit scenes
    EXPLICIT_PHRASES = [
        r"took (him|his cock|it) (in|into)",
        r"pushed (into|inside)",
        r"felt (him|it) (enter|inside)",
        r"began to (move|thrust|stroke)",
        r"(faster|harder|deeper)",
        r"couldn't (hold|last|stop)",
        r"about to (cum|come|explode)",
        r"(came|cumming|coming) (hard|inside|together)",
    ]

    # Non-explicit context to skip
    SKIP_INDICATORS = [
        r"^chapter \d+",
        r"^author'?s? note",
        r"^\*\*\*",
        r"^---",
        r"years? (ago|later|before)",
        r"(next|following) (day|morning|week)",
        r"(drove|walked|ran) (to|away|home)",
    ]

    def __init__(self, min_score: int = 8, min_length: int = 200):
        self.min_score = min_score
        self.min_length = min_length

    def score_passage(self, text: str) -> int:
        """Score a passage for explicit content relevance."""
        text_lower = text.lower()
        score = 0

        # Check skip indicators
        for pattern in self.SKIP_INDICATORS:
            if re.search(pattern, text_lower):
                return 0

        # Score keywords
        for keyword, points in self.EXPLICIT_KEYWORDS.items():
            count = text_lower.count(keyword)
            score += count * points

        # Bonus for explicit phrases
        for pattern in self.EXPLICIT_PHRASES:
            matches = len(re.findall(pattern, text_lower))
            score += matches * 3

        # Normalize by length (per 100 words)
        word_count = len(text.split())
        if word_count > 0:
            score = int(score * 100 / word_count)

        return score

    def extract_explicit_passages(self, text: str, max_passages: int = 10) -> list:
        """
        Extract explicit passages from a longer text.
        Returns list of (passage, score) tuples.
        """
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        # Score and group consecutive explicit paragraphs
        passages = []
        current_passage = []
        current_score = 0

        for para in paragraphs:
            para = para.strip()
            if len(para) < 50:
                continue

            score = self.score_passage(para)

            if score >= 3:  # Paragraph is somewhat explicit
                current_passage.append(para)
                current_score += score
            else:
                # End of explicit section
                if current_passage and current_score >= self.min_score:
                    combined = "\n\n".join(current_passage)
                    if len(combined) >= self.min_length:
                        passages.append((combined, current_score))
                current_passage = []
                current_score = 0

        # Don't forget last passage
        if current_passage and current_score >= self.min_score:
            combined = "\n\n".join(current_passage)
            if len(combined) >= self.min_length:
                passages.append((combined, current_score))

        # Sort by score and return top passages
        passages.sort(key=lambda x: x[1], reverse=True)
        return passages[:max_passages]

    def filter_story(self, text: str, word_count: int) -> list:
        """
        Filter a story for training data.

        For short stories (<5000 words): check overall score
        For long stories: extract explicit passages only
        """
        if word_count < 5000:
            # Short story - check if overall explicit enough
            score = self.score_passage(text)
            if score >= self.min_score:
                return [(text, score)]
            return []
        else:
            # Long story - extract explicit passages
            return self.extract_explicit_passages(text)


# Global filter instance
CONTENT_FILTER = ExplicitContentFilter(min_score=8, min_length=300)

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Model settings (optimized for 8GB RAM)
    # Using models that don't require HF gated access
    "base_model": "mlx-community/Qwen2.5-3B-Instruct-4bit",
    "coding_model": "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",

    # Training settings (conservative for 8GB)
    "lora_rank": 8,           # Lower rank = less memory
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "batch_size": 1,          # Must be 1 for 8GB
    "gradient_accumulation": 4,
    "learning_rate": 1e-4,
    "epochs": 3,
    "max_seq_length": 1024,   # Shorter sequences for memory

    # Paths
    "data_root": "/Volumes/David External",
    "output_root": "/Volumes/David External/sam_models",
    "nifty_data": "/Volumes/David External/nifty_archive/stories",
    "ao3_data": "/Volumes/David External/ao3_archive/works",
}

# ============================================================================
# DATA PREPARATION
# ============================================================================

@dataclass
class TrainingExample:
    """A single training example."""
    instruction: str
    input: str
    output: str
    source: str  # "nifty", "ao3", "code"

def load_nifty_stories(data_dir: str, max_examples: int = 5000) -> List[TrainingExample]:
    """Load nifty stories and convert to training format."""
    examples = []

    for category in os.listdir(data_dir):
        category_path = os.path.join(data_dir, category)
        if not os.path.isdir(category_path):
            continue

        for filename in os.listdir(category_path):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(category_path, filename)
            try:
                with open(filepath, "r") as f:
                    story = json.load(f)

                # Skip very short or very long stories
                word_count = story.get("word_count", 0)
                if word_count < 500 or word_count > 10000:
                    continue

                text = story.get("text", "")
                if not text:
                    continue

                # Create roleplay training examples
                # Format: Given a scenario setup, continue the story
                paragraphs = text.split("\n\n")
                if len(paragraphs) < 3:
                    continue

                # Use first paragraph(s) as setup, rest as continuation
                setup = "\n\n".join(paragraphs[:2])
                continuation = "\n\n".join(paragraphs[2:5])  # Limit length

                # Build instruction based on metadata
                setting = story.get("setting", "")
                relationship = story.get("relationship_type", "")
                intensity = story.get("content_intensity", "moderate")

                instruction = f"Continue this {intensity} gay erotic story"
                if setting:
                    instruction += f" set in a {setting}"
                if relationship:
                    instruction += f" involving {relationship}"
                instruction += "."

                examples.append(TrainingExample(
                    instruction=instruction,
                    input=setup[:1500],  # Limit input length
                    output=continuation[:2000],  # Limit output length
                    source="nifty"
                ))

                if len(examples) >= max_examples:
                    return examples

            except Exception as e:
                continue

    return examples

def load_ao3_works(data_dir: str, max_examples: int = 3000) -> List[TrainingExample]:
    """Load AO3 works and convert to training format."""
    examples = []

    for fandom in os.listdir(data_dir):
        fandom_path = os.path.join(data_dir, fandom)
        if not os.path.isdir(fandom_path):
            continue

        for filename in os.listdir(fandom_path):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(fandom_path, filename)
            try:
                with open(filepath, "r") as f:
                    work = json.load(f)

                text = work.get("text", "")
                word_count = work.get("word_count", 0)

                if word_count < 1000 or word_count > 15000:
                    continue

                paragraphs = text.split("\n\n")
                if len(paragraphs) < 4:
                    continue

                # Use beginning as prompt, middle as output
                setup = "\n\n".join(paragraphs[:2])
                continuation = "\n\n".join(paragraphs[2:6])

                # Rich instruction from AO3 metadata
                tags = work.get("tags", [])
                relationships = work.get("relationships", [])

                instruction = "Continue this explicit M/M fanfiction"
                if relationships:
                    instruction += f" featuring {relationships[0]}"
                if tags:
                    relevant_tags = [t for t in tags[:3] if len(t) < 30]
                    if relevant_tags:
                        instruction += f" with themes of {', '.join(relevant_tags)}"
                instruction += "."

                examples.append(TrainingExample(
                    instruction=instruction,
                    input=setup[:1500],
                    output=continuation[:2000],
                    source="ao3"
                ))

                if len(examples) >= max_examples:
                    return examples

            except Exception:
                continue

    return examples

def load_code_examples(repo_paths: List[str], max_examples: int = 2000) -> List[TrainingExample]:
    """Load code from your repositories for training."""
    examples = []

    code_extensions = {".py", ".ts", ".js", ".rs", ".vue", ".tsx", ".jsx"}

    for repo_path in repo_paths:
        if not os.path.exists(repo_path):
            continue

        for root, dirs, files in os.walk(repo_path):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {
                "node_modules", ".git", "__pycache__", "venv", ".venv",
                "target", "build", "dist", ".next"
            }]

            for filename in files:
                ext = os.path.splitext(filename)[1]
                if ext not in code_extensions:
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()

                    # Skip very short or very long files
                    lines = code.split("\n")
                    if len(lines) < 20 or len(lines) > 500:
                        continue

                    # Create code completion examples
                    # Split file and ask model to complete
                    split_point = len(lines) // 2
                    context = "\n".join(lines[:split_point])
                    completion = "\n".join(lines[split_point:split_point + 30])

                    lang_map = {
                        ".py": "Python", ".ts": "TypeScript", ".js": "JavaScript",
                        ".rs": "Rust", ".vue": "Vue", ".tsx": "TypeScript React",
                        ".jsx": "JavaScript React"
                    }
                    lang = lang_map.get(ext, "code")

                    examples.append(TrainingExample(
                        instruction=f"Complete this {lang} code:",
                        input=context[-2000:],  # Last 2000 chars as context
                        output=completion[:1500],
                        source="code"
                    ))

                    if len(examples) >= max_examples:
                        return examples

                except Exception:
                    continue

    return examples

def prepare_training_data(
    include_nifty: bool = True,
    include_ao3: bool = True,
    include_code: bool = True,
    code_repos: List[str] = None
) -> List[Dict]:
    """Prepare combined training dataset."""

    all_examples = []

    if include_nifty and os.path.exists(CONFIG["nifty_data"]):
        print("Loading Nifty stories...")
        nifty = load_nifty_stories(CONFIG["nifty_data"])
        all_examples.extend(nifty)
        print(f"  Loaded {len(nifty)} examples")

    if include_ao3 and os.path.exists(CONFIG["ao3_data"]):
        print("Loading AO3 works...")
        ao3 = load_ao3_works(CONFIG["ao3_data"])
        all_examples.extend(ao3)
        print(f"  Loaded {len(ao3)} examples")

    if include_code and code_repos:
        print("Loading code examples...")
        code = load_code_examples(code_repos)
        all_examples.extend(code)
        print(f"  Loaded {len(code)} examples")

    # Shuffle
    random.shuffle(all_examples)

    # Convert to MLX format
    mlx_data = []
    for ex in all_examples:
        mlx_data.append({
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{ex.instruction}\n\n{ex.input}"},
                {"role": "assistant", "content": ex.output}
            ]
        })

    print(f"\nTotal training examples: {len(mlx_data)}")
    return mlx_data

def save_training_data(data: List[Dict], output_path: str):
    """Save training data in JSONL format for MLX."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Split into train/val
    random.shuffle(data)
    split_idx = int(len(data) * 0.9)
    train_data = data[:split_idx]
    val_data = data[split_idx:]

    train_path = output_path.replace(".jsonl", "_train.jsonl")
    val_path = output_path.replace(".jsonl", "_val.jsonl")

    with open(train_path, "w") as f:
        for item in train_data:
            f.write(json.dumps(item) + "\n")

    with open(val_path, "w") as f:
        for item in val_data:
            f.write(json.dumps(item) + "\n")

    print(f"Saved {len(train_data)} training examples to {train_path}")
    print(f"Saved {len(val_data)} validation examples to {val_path}")

    return train_path, val_path

# ============================================================================
# MLX TRAINING
# ============================================================================

def create_lora_config() -> Dict:
    """Create LoRA configuration for MLX."""
    return {
        "lora_layers": 16,  # Number of layers to apply LoRA
        "lora_parameters": {
            "rank": CONFIG["lora_rank"],
            "alpha": CONFIG["lora_alpha"],
            "dropout": CONFIG["lora_dropout"],
            "scale": CONFIG["lora_alpha"] / CONFIG["lora_rank"]
        }
    }

def train_with_mlx(
    train_path: str,
    val_path: str,
    model_name: str,
    output_dir: str,
    adapter_name: str = "sam_adapter"
):
    """Train LoRA adapter using MLX."""

    print(f"\n{'='*60}")
    print(f"MLX LoRA Training")
    print(f"{'='*60}")
    print(f"Model: {model_name}")
    print(f"Output: {output_dir}")
    print(f"Adapter: {adapter_name}")
    print(f"{'='*60}\n")

    # Create output directory
    adapter_dir = os.path.join(output_dir, adapter_name)
    os.makedirs(adapter_dir, exist_ok=True)

    # Save config
    config = {
        "base_model": model_name,
        "lora_config": create_lora_config(),
        "training_config": {
            "batch_size": CONFIG["batch_size"],
            "gradient_accumulation": CONFIG["gradient_accumulation"],
            "learning_rate": CONFIG["learning_rate"],
            "epochs": CONFIG["epochs"],
            "max_seq_length": CONFIG["max_seq_length"]
        }
    }

    with open(os.path.join(adapter_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    # Generate MLX training command
    cmd = f"""
mlx_lm.lora \\
    --model {model_name} \\
    --train \\
    --data {os.path.dirname(train_path)} \\
    --batch-size {CONFIG['batch_size']} \\
    --lora-layers {create_lora_config()['lora_layers']} \\
    --iters 1000 \\
    --adapter-path {adapter_dir}
"""

    print("To train, run:")
    print(cmd)

    # Save as shell script
    script_path = os.path.join(adapter_dir, "train.sh")
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(cmd)
    os.chmod(script_path, 0o755)

    print(f"\nOr run: bash {script_path}")

    return adapter_dir

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Pipeline")
    parser.add_argument("command", choices=["prepare", "train", "merge", "test"],
                       help="Command to run")
    parser.add_argument("--type", "-t", choices=["roleplay", "coding", "both"],
                       default="both", help="Type of training data")
    parser.add_argument("--model", "-m", default=CONFIG["base_model"],
                       help="Base model to use")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--repos", "-r", nargs="+", help="Code repositories to include")

    args = parser.parse_args()

    if args.command == "prepare":
        # Prepare training data
        include_nifty = args.type in ["roleplay", "both"]
        include_ao3 = args.type in ["roleplay", "both"]
        include_code = args.type in ["coding", "both"]

        code_repos = args.repos or [
            "/Users/davidquinton/ReverseLab/SAM",
            "/Users/davidquinton/Projects/character-pipeline",
        ]

        data = prepare_training_data(
            include_nifty=include_nifty,
            include_ao3=include_ao3,
            include_code=include_code,
            code_repos=code_repos
        )

        output_path = args.output or os.path.join(
            CONFIG["output_root"], "training_data", "combined.jsonl"
        )

        save_training_data(data, output_path)

    elif args.command == "train":
        # Set up training
        data_dir = args.output or os.path.join(CONFIG["output_root"], "training_data")
        train_path = os.path.join(data_dir, "combined_train.jsonl")
        val_path = os.path.join(data_dir, "combined_val.jsonl")

        if not os.path.exists(train_path):
            print(f"Training data not found at {train_path}")
            print("Run 'prepare' command first.")
            return 1

        adapter_name = "sam_roleplay" if args.type == "roleplay" else "sam_coding" if args.type == "coding" else "sam_combined"

        train_with_mlx(
            train_path=train_path,
            val_path=val_path,
            model_name=args.model,
            output_dir=os.path.join(CONFIG["output_root"], "adapters"),
            adapter_name=adapter_name
        )

    elif args.command == "test":
        print("Testing model with adapter...")
        print("TODO: Implement inference test")

    return 0

if __name__ == "__main__":
    exit(main())
