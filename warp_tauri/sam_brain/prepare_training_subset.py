#!/usr/bin/env python3
"""
Prepare a curated training subset from the 78M samples.

Samples diverse examples while staying within 8GB RAM constraints.
Target: ~15,000 high-quality samples balanced across categories.
"""

import json
import random
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

# Configuration
SOURCE_FILE = Path("/Volumes/David External/SAM_Backup/all_training.jsonl")
OUTPUT_DIR = Path(__file__).parent / "training_data"
OUTPUT_FILE = OUTPUT_DIR / "curated_training.jsonl"

# Target samples per category
CATEGORY_TARGETS = {
    "personality": 3000,     # SAM's personality (cocky, flirty, helpful)
    "coding": 3000,          # Code generation, debugging
    "roleplay": 2000,        # Character roleplay
    "reasoning": 2000,       # Logic, analysis, problem-solving
    "conversation": 2000,    # General chat
    "creative": 1500,        # Creative writing
    "factual": 1500,         # Q&A, explanations
}

TOTAL_TARGET = sum(CATEGORY_TARGETS.values())  # 15,000

# Keywords for categorization
CATEGORY_KEYWORDS = {
    "coding": ["code", "function", "python", "javascript", "bug", "error", "implement",
               "class", "api", "debug", "script", "programming", "def ", "const ", "let "],
    "roleplay": ["roleplay", "pretend", "character", "you are", "act as", "scenario",
                 "*", "narrator", "setting:"],
    "personality": ["flirt", "cocky", "confident", "babe", "gorgeous", "sexy", "charm",
                    "sass", "tease", "wink", "smirk"],
    "reasoning": ["analyze", "think", "logic", "solve", "problem", "reason", "why",
                  "explain", "calculate", "deduce", "figure out"],
    "creative": ["story", "write a", "creative", "poem", "fiction", "imagine",
                 "tale", "narrative", "describe a scene"],
    "factual": ["what is", "how does", "define", "explain", "tell me about",
                "when did", "who was", "where is"],
}


def categorize_sample(text: str) -> str:
    """Categorize a sample based on content."""
    text_lower = text.lower()

    scores = defaultdict(int)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[category] += 1

    if scores:
        return max(scores.keys(), key=lambda k: scores[k])
    return "conversation"


def convert_to_mlx_format(sample: Dict) -> Dict:
    """Convert ShareGPT format to MLX training format."""
    convs = sample.get("conversations", [])
    if len(convs) < 2:
        return None

    # Get first user message as instruction
    instruction = ""
    output = ""

    for turn in convs:
        role = turn.get("role", turn.get("from", ""))
        content = turn.get("content", turn.get("value", ""))

        if role in ["human", "user"] and not instruction:
            instruction = content
        elif role in ["gpt", "assistant"] and instruction and not output:
            output = content
            break

    if not instruction or not output:
        return None

    return {
        "instruction": instruction,
        "input": "",
        "output": output,
    }


def sample_data():
    """Sample and categorize training data."""
    print(f"Reading from {SOURCE_FILE}...")

    if not SOURCE_FILE.exists():
        print(f"Error: {SOURCE_FILE} not found")
        return

    # Reservoirs for each category
    reservoirs = {cat: [] for cat in CATEGORY_TARGETS}
    counts = {cat: 0 for cat in CATEGORY_TARGETS}

    # Stream through file
    total_read = 0
    with open(SOURCE_FILE) as f:
        for line_num, line in enumerate(f):
            if line_num % 1000000 == 0:
                print(f"  Read {line_num:,} lines...")

            try:
                sample = json.loads(line)
                convs = sample.get("conversations", [])

                if len(convs) < 2:
                    continue

                # Get text for categorization
                text = " ".join([
                    turn.get("content", turn.get("value", ""))
                    for turn in convs
                ])

                # Skip very short or very long samples
                if len(text) < 50 or len(text) > 10000:
                    continue

                # Categorize
                category = categorize_sample(text)

                # Reservoir sampling
                target = CATEGORY_TARGETS.get(category, 0)
                if target == 0:
                    continue

                counts[category] += 1

                if len(reservoirs[category]) < target:
                    converted = convert_to_mlx_format(sample)
                    if converted:
                        reservoirs[category].append(converted)
                else:
                    # Replace with probability target/count
                    j = random.randint(0, counts[category] - 1)
                    if j < target:
                        converted = convert_to_mlx_format(sample)
                        if converted:
                            reservoirs[category][j] = converted

                total_read += 1

            except json.JSONDecodeError:
                continue
            except Exception as e:
                continue

    print(f"\nTotal samples read: {total_read:,}")
    print("\nSamples per category:")
    for cat, samples in reservoirs.items():
        print(f"  {cat}: {len(samples)}")

    # Combine all samples
    all_samples = []
    for samples in reservoirs.values():
        all_samples.extend(samples)

    # Shuffle
    random.shuffle(all_samples)

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for sample in all_samples:
            f.write(json.dumps(sample) + "\n")

    print(f"\nWrote {len(all_samples)} samples to {OUTPUT_FILE}")

    # Also create train/valid split
    split_idx = int(len(all_samples) * 0.9)
    train_samples = all_samples[:split_idx]
    valid_samples = all_samples[split_idx:]

    with open(OUTPUT_DIR / "train.jsonl", "w") as f:
        for sample in train_samples:
            f.write(json.dumps(sample) + "\n")

    with open(OUTPUT_DIR / "valid.jsonl", "w") as f:
        for sample in valid_samples:
            f.write(json.dumps(sample) + "\n")

    print(f"Split: {len(train_samples)} train, {len(valid_samples)} valid")


if __name__ == "__main__":
    sample_data()
