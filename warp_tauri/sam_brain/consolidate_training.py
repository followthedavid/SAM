#!/usr/bin/env python3
"""
Consolidate all training data sources into master corpus.
Sources: SAM curated, ChatGPT parsed, Nifty roleplay
"""

import json
import random
from pathlib import Path
from typing import Iterator
import hashlib

# Source paths
SOURCES = {
    # SAM brain existing data
    "sam_curated": Path.home() / "ReverseLab/SAM/warp_tauri/sam_brain/training_data/curated_training.jsonl",
    "sam_train": Path.home() / "ReverseLab/SAM/warp_tauri/sam_brain/training_data/train.jsonl",
    "sam_personality": Path.home() / "ReverseLab/SAM/warp_tauri/sam_brain/training_data/claude_generated_personality.jsonl",

    # ChatGPT parsed
    "chatgpt_coding": Path("/Volumes/David External/chatgpt_training/chatgpt_coding.jsonl"),
    "chatgpt_roleplay": Path("/Volumes/David External/chatgpt_training/chatgpt_roleplay.jsonl"),
    "chatgpt_planning": Path("/Volumes/David External/chatgpt_training/chatgpt_planning.jsonl"),
    "chatgpt_coaching": Path("/Volumes/David External/chatgpt_training/chatgpt_coaching.jsonl"),

    # Nifty roleplay
    "nifty_train": Path("/Volumes/David External/nifty_archive/training_data/train.jsonl"),
}

OUTPUT_DIR = Path("/Volumes/David External/SAM_master_training")


def read_jsonl(path: Path) -> Iterator[dict]:
    """Read JSONL file, handling both formats."""
    if not path.exists():
        print(f"  Skipping (not found): {path}")
        return

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                yield normalize_format(item)
            except json.JSONDecodeError:
                continue


def normalize_format(item: dict) -> dict:
    """Normalize to ChatML messages format."""
    # Already in messages format
    if "messages" in item:
        return item

    # Alpaca format (instruction/input/output)
    if "instruction" in item:
        user_content = item["instruction"]
        if item.get("input"):
            user_content += "\n" + item["input"]
        return {
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": item.get("output", "")}
            ]
        }

    # Simple prompt/completion
    if "prompt" in item and "completion" in item:
        return {
            "messages": [
                {"role": "user", "content": item["prompt"]},
                {"role": "assistant", "content": item["completion"]}
            ]
        }

    # Unknown format, skip
    return None


def dedupe_key(item: dict) -> str:
    """Generate deduplication key."""
    if not item or "messages" not in item:
        return None
    user_msg = ""
    for msg in item["messages"]:
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    return hashlib.md5(user_msg.strip().lower().encode()).hexdigest()[:16]


def consolidate():
    """Main consolidation function."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_items = []
    seen_keys = set()
    stats = {}

    for name, path in SOURCES.items():
        print(f"Processing {name}...")
        count = 0
        for item in read_jsonl(path):
            if not item:
                continue

            key = dedupe_key(item)
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)

            all_items.append((name, item))
            count += 1

        stats[name] = count
        print(f"  -> {count} examples")

    # Shuffle
    random.shuffle(all_items)

    # Split train/valid (90/10)
    split_idx = int(len(all_items) * 0.9)
    train_items = all_items[:split_idx]
    valid_items = all_items[split_idx:]

    # Write combined files
    train_file = OUTPUT_DIR / "train.jsonl"
    valid_file = OUTPUT_DIR / "valid.jsonl"

    with open(train_file, 'w') as f:
        for _, item in train_items:
            f.write(json.dumps(item) + "\n")

    with open(valid_file, 'w') as f:
        for _, item in valid_items:
            f.write(json.dumps(item) + "\n")

    # Write category-specific files
    categories = {
        "roleplay": ["chatgpt_roleplay", "nifty_train"],
        "coding": ["chatgpt_coding", "sam_curated"],
        "planning": ["chatgpt_planning"],
        "personality": ["sam_personality", "chatgpt_coaching"]
    }

    for cat, sources in categories.items():
        cat_items = [(n, i) for n, i in all_items if n in sources]
        if cat_items:
            cat_file = OUTPUT_DIR / f"{cat}.jsonl"
            with open(cat_file, 'w') as f:
                for _, item in cat_items:
                    f.write(json.dumps(item) + "\n")
            print(f"  {cat}: {len(cat_items)} examples -> {cat_file}")

    # Summary
    print("\n" + "=" * 50)
    print("CONSOLIDATION SUMMARY")
    print("=" * 50)
    for name, count in stats.items():
        print(f"  {name}: {count}")
    print("-" * 50)
    print(f"  Total unique: {len(all_items)}")
    print(f"  Train: {len(train_items)}")
    print(f"  Valid: {len(valid_items)}")
    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    consolidate()
