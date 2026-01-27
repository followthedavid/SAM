#!/usr/bin/env python3
"""
Download High-Value Public Training Datasets

These are the same types of data that made Claude and GPT effective:
- Instruction-following data (FLAN, Alpaca style)
- Chain-of-thought reasoning examples
- Conversation data (Open Assistant)
- Code instruction data

Usage:
    python download_instruction_data.py all        # Download everything
    python download_instruction_data.py alpaca     # Just Alpaca
    python download_instruction_data.py status     # Check what we have
"""

import os
import sys
import json
import requests
import gzip
import shutil
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Output directory
OUTPUT_DIR = Path("/Volumes/David External/instruction_datasets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, output_path: Path, desc: str = "") -> bool:
    """Download a file with progress bar"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def download_alpaca():
    """
    Stanford Alpaca - 52K instruction-following examples
    Format: {"instruction": ..., "input": ..., "output": ...}
    This is the gold standard for instruction tuning.
    """
    print("\n📥 Downloading Stanford Alpaca...")
    output = OUTPUT_DIR / "alpaca"
    output.mkdir(exist_ok=True)

    url = "https://raw.githubusercontent.com/tatsu-lab/stanford_alpaca/main/alpaca_data.json"
    output_file = output / "alpaca_data.json"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "alpaca_data.json"):
        # Count examples
        with open(output_file) as f:
            data = json.load(f)
        print(f"  ✅ Downloaded {len(data):,} instruction examples")
        return True
    return False


def download_dolly():
    """
    Databricks Dolly - 15K human-written instruction examples
    Higher quality than Alpaca (human-written, not GPT-generated)
    """
    print("\n📥 Downloading Databricks Dolly...")
    output = OUTPUT_DIR / "dolly"
    output.mkdir(exist_ok=True)

    url = "https://huggingface.co/datasets/databricks/databricks-dolly-15k/resolve/main/databricks-dolly-15k.jsonl"
    output_file = output / "dolly-15k.jsonl"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "dolly-15k.jsonl"):
        # Count examples
        with open(output_file) as f:
            count = sum(1 for _ in f)
        print(f"  ✅ Downloaded {count:,} instruction examples")
        return True
    return False


def download_oasst():
    """
    Open Assistant - High-quality conversation trees
    Real human conversations with AI, includes rankings
    Perfect for preference learning (DPO)
    """
    print("\n📥 Downloading Open Assistant...")
    output = OUTPUT_DIR / "open_assistant"
    output.mkdir(exist_ok=True)

    # The main dataset
    url = "https://huggingface.co/datasets/OpenAssistant/oasst1/resolve/main/2023-04-12_oasst_ready.trees.jsonl.gz"
    gz_file = output / "oasst_trees.jsonl.gz"
    output_file = output / "oasst_trees.jsonl"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, gz_file, "oasst_trees.jsonl.gz"):
        # Decompress
        print("  Decompressing...")
        with gzip.open(gz_file, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        gz_file.unlink()  # Remove compressed file

        # Count
        with open(output_file) as f:
            count = sum(1 for _ in f)
        print(f"  ✅ Downloaded {count:,} conversation trees")
        return True
    return False


def download_cot():
    """
    Chain-of-Thought examples - FLAN Collection subset
    These teach step-by-step reasoning
    """
    print("\n📥 Downloading Chain-of-Thought examples...")
    output = OUTPUT_DIR / "chain_of_thought"
    output.mkdir(exist_ok=True)

    # FLAN CoT subset
    datasets = [
        ("https://huggingface.co/datasets/kaist-ai/CoT-Collection/resolve/main/data/aqua_rat/train.json",
         "aqua_rat_cot.json", "Math word problems with reasoning"),
        ("https://huggingface.co/datasets/kaist-ai/CoT-Collection/resolve/main/data/gsm8k/train.json",
         "gsm8k_cot.json", "Grade school math with steps"),
    ]

    for url, filename, desc in datasets:
        output_file = output / filename
        if output_file.exists():
            print(f"  Already exists: {filename}")
            continue

        if download_file(url, output_file, filename):
            try:
                with open(output_file) as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, list) else 1
                print(f"  ✅ {desc}: {count:,} examples")
            except:
                print(f"  ✅ Downloaded {filename}")


def download_code_alpaca():
    """
    Code Alpaca - 20K code instruction examples
    Teaches code generation, explanation, debugging
    """
    print("\n📥 Downloading Code Alpaca...")
    output = OUTPUT_DIR / "code_alpaca"
    output.mkdir(exist_ok=True)

    url = "https://raw.githubusercontent.com/sahil280114/codealpaca/master/data/code_alpaca_20k.json"
    output_file = output / "code_alpaca_20k.json"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "code_alpaca_20k.json"):
        with open(output_file) as f:
            data = json.load(f)
        print(f"  ✅ Downloaded {len(data):,} code instruction examples")
        return True
    return False


def download_evol_instruct():
    """
    Evol-Instruct - WizardLM's evolved instructions
    Instructions made more complex through evolution
    Better for teaching nuanced understanding
    """
    print("\n📥 Downloading Evol-Instruct (WizardLM)...")
    output = OUTPUT_DIR / "evol_instruct"
    output.mkdir(exist_ok=True)

    url = "https://huggingface.co/datasets/WizardLM/WizardLM_evol_instruct_V2_196k/resolve/main/WizardLM_evol_instruct_V2_143k.json"
    output_file = output / "evol_instruct_143k.json"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "evol_instruct_143k.json"):
        with open(output_file) as f:
            data = json.load(f)
        print(f"  ✅ Downloaded {len(data):,} evolved instruction examples")
        return True
    return False


def download_ultrachat():
    """
    UltraChat - Synthetic multi-turn conversations
    Good for teaching conversation flow
    """
    print("\n📥 Downloading UltraChat sample...")
    output = OUTPUT_DIR / "ultrachat"
    output.mkdir(exist_ok=True)

    # Just get a sample (full dataset is huge)
    url = "https://huggingface.co/datasets/stingning/ultrachat/resolve/main/train_0.jsonl"
    output_file = output / "ultrachat_sample.jsonl"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "ultrachat_sample.jsonl"):
        with open(output_file) as f:
            count = sum(1 for _ in f)
        print(f"  ✅ Downloaded {count:,} conversation examples")
        return True
    return False


def download_sharegpt():
    """
    ShareGPT - Real ChatGPT conversations shared by users
    Excellent for learning conversational patterns
    """
    print("\n📥 Downloading ShareGPT...")
    output = OUTPUT_DIR / "sharegpt"
    output.mkdir(exist_ok=True)

    url = "https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json"
    output_file = output / "sharegpt_v3.json"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    if download_file(url, output_file, "sharegpt_v3.json"):
        with open(output_file) as f:
            data = json.load(f)
        print(f"  ✅ Downloaded {len(data):,} conversation examples")
        return True
    return False


def convert_to_training_format(output_path: Path = OUTPUT_DIR / "combined_training.jsonl"):
    """Convert all downloaded datasets to unified JSONL format"""
    print("\n🔄 Converting to unified training format...")

    count = 0

    with open(output_path, "w") as out:
        # Alpaca format
        alpaca_file = OUTPUT_DIR / "alpaca" / "alpaca_data.json"
        if alpaca_file.exists():
            with open(alpaca_file) as f:
                data = json.load(f)
            for item in data:
                out.write(json.dumps({
                    "instruction": item.get("instruction", ""),
                    "input": item.get("input", ""),
                    "output": item.get("output", ""),
                    "source": "alpaca"
                }) + "\n")
                count += 1

        # Dolly format
        dolly_file = OUTPUT_DIR / "dolly" / "dolly-15k.jsonl"
        if dolly_file.exists():
            with open(dolly_file) as f:
                for line in f:
                    item = json.loads(line)
                    out.write(json.dumps({
                        "instruction": item.get("instruction", ""),
                        "input": item.get("context", ""),
                        "output": item.get("response", ""),
                        "source": "dolly"
                    }) + "\n")
                    count += 1

        # Code Alpaca format
        code_file = OUTPUT_DIR / "code_alpaca" / "code_alpaca_20k.json"
        if code_file.exists():
            with open(code_file) as f:
                data = json.load(f)
            for item in data:
                out.write(json.dumps({
                    "instruction": item.get("instruction", ""),
                    "input": item.get("input", ""),
                    "output": item.get("output", ""),
                    "source": "code_alpaca"
                }) + "\n")
                count += 1

        # Evol-Instruct format
        evol_file = OUTPUT_DIR / "evol_instruct" / "evol_instruct_143k.json"
        if evol_file.exists():
            with open(evol_file) as f:
                data = json.load(f)
            for item in data:
                # This format has conversations
                if isinstance(item, dict) and "conversations" in item:
                    convs = item["conversations"]
                    for i in range(0, len(convs)-1, 2):
                        if i+1 < len(convs):
                            out.write(json.dumps({
                                "instruction": convs[i].get("value", ""),
                                "input": "",
                                "output": convs[i+1].get("value", ""),
                                "source": "evol_instruct"
                            }) + "\n")
                            count += 1

    print(f"✅ Created {output_path} with {count:,} examples")
    return count


def show_status():
    """Show what datasets we have"""
    print("\n" + "="*60)
    print("  INSTRUCTION DATASET STATUS")
    print("="*60)

    datasets = [
        ("alpaca", "alpaca_data.json"),
        ("dolly", "dolly-15k.jsonl"),
        ("open_assistant", "oasst_trees.jsonl"),
        ("code_alpaca", "code_alpaca_20k.json"),
        ("evol_instruct", "evol_instruct_143k.json"),
        ("ultrachat", "ultrachat_sample.jsonl"),
        ("sharegpt", "sharegpt_v3.json"),
        ("chain_of_thought", "gsm8k_cot.json"),
    ]

    total = 0
    for folder, filename in datasets:
        path = OUTPUT_DIR / folder / filename
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            # Count examples
            try:
                with open(path) as f:
                    if filename.endswith('.json'):
                        data = json.load(f)
                        count = len(data) if isinstance(data, list) else 1
                    else:
                        count = sum(1 for _ in f)
            except:
                count = "?"
            print(f"  ✅ {folder}: {count:,} examples ({size_mb:.1f} MB)")
            if isinstance(count, int):
                total += count
        else:
            print(f"  ❌ {folder}: not downloaded")

    print(f"\n  Total examples available: {total:,}")

    # Check combined file
    combined = OUTPUT_DIR / "combined_training.jsonl"
    if combined.exists():
        with open(combined) as f:
            count = sum(1 for _ in f)
        print(f"\n  📦 Combined training file: {count:,} examples")


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_instruction_data.py [command]")
        print("\nCommands:")
        print("  all       - Download all datasets")
        print("  alpaca    - Download Stanford Alpaca")
        print("  dolly     - Download Databricks Dolly")
        print("  oasst     - Download Open Assistant")
        print("  code      - Download Code Alpaca")
        print("  evol      - Download Evol-Instruct")
        print("  cot       - Download Chain-of-Thought")
        print("  convert   - Convert to unified format")
        print("  status    - Show download status")
        return

    cmd = sys.argv[1].lower()

    if cmd == "all":
        download_alpaca()
        download_dolly()
        download_oasst()
        download_code_alpaca()
        download_evol_instruct()
        download_cot()
        download_ultrachat()
        download_sharegpt()
        print("\n" + "="*50)
        convert_to_training_format()

    elif cmd == "alpaca":
        download_alpaca()
    elif cmd == "dolly":
        download_dolly()
    elif cmd == "oasst":
        download_oasst()
    elif cmd == "code":
        download_code_alpaca()
    elif cmd == "evol":
        download_evol_instruct()
    elif cmd == "cot":
        download_cot()
    elif cmd == "convert":
        convert_to_training_format()
    elif cmd == "status":
        show_status()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
