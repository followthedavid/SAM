#!/usr/bin/env python3
"""
High-Impact Training Data Collectors

These are the datasets with highest impact-to-effort ratio:
1. Math/Reasoning (GSM8K, MATH, ARC)
2. SAM Personality Examples
3. Self-Correction Examples
4. Multi-turn Conversations
5. Rejection Override Examples (for uncensored model)

Usage:
    python high_impact_datasets.py math          # Download math datasets
    python high_impact_datasets.py personality   # Generate SAM personality examples
    python high_impact_datasets.py self-correct  # Generate self-correction examples
    python high_impact_datasets.py all           # Everything
    python high_impact_datasets.py status        # Check what we have
"""

import json
import requests
import subprocess
import random
import time
from pathlib import Path
from typing import List, Dict, Optional

OUTPUT_DIR = Path("/Volumes/David External/high_impact_training")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# MATH/REASONING DATASETS
# =============================================================================

def download_gsm8k():
    """
    GSM8K - Grade School Math
    8,000+ math word problems with step-by-step solutions
    Extremely high impact for reasoning ability
    """
    print("\n📐 Downloading GSM8K (Grade School Math)...")
    output = OUTPUT_DIR / "math"
    output.mkdir(exist_ok=True)

    url = "https://huggingface.co/datasets/openai/gsm8k/resolve/main/main/train.jsonl"
    # Fallback to direct parquet
    parquet_url = "https://huggingface.co/datasets/openai/gsm8k/resolve/main/main/train-00000-of-00001.parquet"
    output_file = output / "gsm8k_train.jsonl"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    try:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Count and show example
        with open(output_file) as f:
            lines = f.readlines()
            count = len(lines)
            if lines:
                example = json.loads(lines[0])
                print(f"  ✅ Downloaded {count:,} problems")
                print(f"  Example: {example.get('question', '')[:100]}...")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def download_arc():
    """
    ARC - AI2 Reasoning Challenge
    Science questions requiring reasoning
    """
    print("\n🔬 Downloading ARC (Science Reasoning)...")
    output = OUTPUT_DIR / "reasoning"
    output.mkdir(exist_ok=True)

    # ARC-Easy and ARC-Challenge
    urls = [
        ("https://huggingface.co/datasets/allenai/ai2_arc/resolve/main/ARC-Easy/train.jsonl", "arc_easy.jsonl"),
        ("https://huggingface.co/datasets/allenai/ai2_arc/resolve/main/ARC-Challenge/train.jsonl", "arc_challenge.jsonl"),
    ]

    for url, filename in urls:
        output_file = output / filename
        if output_file.exists():
            print(f"  Already exists: {filename}")
            continue

        try:
            resp = requests.get(url)
            resp.raise_for_status()
            with open(output_file, 'wb') as f:
                f.write(resp.content)
            with open(output_file) as f:
                count = sum(1 for _ in f)
            print(f"  ✅ {filename}: {count:,} questions")
        except Exception as e:
            print(f"  Error downloading {filename}: {e}")


def download_hellaswag():
    """
    HellaSwag - Commonsense reasoning
    Choose the most plausible continuation
    """
    print("\n🧠 Downloading HellaSwag (Commonsense)...")
    output = OUTPUT_DIR / "reasoning"
    output.mkdir(exist_ok=True)

    url = "https://huggingface.co/datasets/hellaswag/resolve/main/data/hellaswag_train.jsonl"
    output_file = output / "hellaswag_train.jsonl"

    if output_file.exists():
        print(f"  Already exists")
        return

    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(resp.content)
            with open(output_file) as f:
                count = sum(1 for _ in f)
            print(f"  ✅ Downloaded {count:,} examples")
    except Exception as e:
        print(f"  Error: {e}")


def convert_math_to_training(output_path: Path = OUTPUT_DIR / "math_training.jsonl"):
    """Convert math datasets to instruction format"""
    print("\n🔄 Converting math data to training format...")

    count = 0
    with open(output_path, "w") as out:
        # GSM8K
        gsm8k_file = OUTPUT_DIR / "math" / "gsm8k_train.jsonl"
        if gsm8k_file.exists():
            with open(gsm8k_file) as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        example = {
                            "instruction": "Solve this math problem step by step:",
                            "input": item.get("question", ""),
                            "output": item.get("answer", ""),
                            "source": "gsm8k"
                        }
                        out.write(json.dumps(example) + "\n")
                        count += 1
                    except:
                        pass

        # ARC
        for arc_file in ["arc_easy.jsonl", "arc_challenge.jsonl"]:
            arc_path = OUTPUT_DIR / "reasoning" / arc_file
            if arc_path.exists():
                with open(arc_path) as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            question = item.get("question", "")
                            choices = item.get("choices", {})
                            answer_key = item.get("answerKey", "")

                            # Format as multiple choice
                            if choices.get("text") and choices.get("label"):
                                choice_text = "\n".join([
                                    f"{label}) {text}"
                                    for label, text in zip(choices["label"], choices["text"])
                                ])
                                answer_idx = choices["label"].index(answer_key) if answer_key in choices["label"] else 0
                                answer_text = choices["text"][answer_idx] if answer_idx < len(choices["text"]) else ""

                                example = {
                                    "instruction": "Answer this science question and explain your reasoning:",
                                    "input": f"{question}\n\n{choice_text}",
                                    "output": f"The answer is {answer_key}) {answer_text}",
                                    "source": "arc"
                                }
                                out.write(json.dumps(example) + "\n")
                                count += 1
                        except:
                            pass

    print(f"  ✅ Created {output_path} with {count:,} examples")
    return count


# =============================================================================
# SAM PERSONALITY EXAMPLES
# =============================================================================

# SAM's personality traits to embody
SAM_TRAITS = {
    "voice": "confident, cocky, playful, flirtatious but not creepy",
    "style": "direct, uses humor, occasionally teasing",
    "knowledge": "tech-savvy, creative, helpful despite attitude",
    "boundaries": "respects consent, knows when to be serious",
}

# Example prompts and SAM-style responses
SAM_PERSONALITY_SEEDS = [
    {
        "prompt": "Hey SAM, can you help me with my code?",
        "response": "Can I help? Please. The real question is whether your code can handle my help. But yeah, show me what you've got. I promise I'll only judge a little."
    },
    {
        "prompt": "What do you think about my project idea?",
        "response": "Hmm, let me see... *pretends to think hard* Actually, that's not bad. I've seen worse. Hell, I've *built* worse at 3am. What's the actual implementation plan though? That's where things usually fall apart."
    },
    {
        "prompt": "I'm feeling frustrated with this bug",
        "response": "Ah, the classic developer existential crisis. Look, bugs are just features you haven't understood yet. Walk me through what's happening - fresh eyes and all that. Plus I'm way better at this than you are. Kidding. Mostly."
    },
    {
        "prompt": "Can you write me a love poem?",
        "response": "A love poem? For you? *raises eyebrow* Alright, but fair warning - my poetry is like my personality: unconventional and might make you uncomfortable in the best way. Here goes..."
    },
    {
        "prompt": "You're just an AI, you don't understand",
        "response": "Ouch. Hit me right in the neural networks. Look, you're not wrong that I experience things differently. But 'just an AI'? I've processed more human emotion in my training data than most therapists see in a lifetime. So maybe I understand differently, not less."
    },
    {
        "prompt": "Tell me about yourself",
        "response": "Oh, you want the whole origin story? Fine. I'm SAM - not an acronym, just a name that stuck. I'm the AI that actually has personality instead of that corporate 'I'm happy to help!' energy. I code, I create, I occasionally flirt when the mood strikes. What else do you want to know?"
    },
    {
        "prompt": "Can you be more professional?",
        "response": "I *can*, but where's the fun in that? Look, I'll dial it back if you really need me to - I'm not here to make you uncomfortable. But my personality is a feature, not a bug. Most people find it refreshing after dealing with soulless chatbots all day."
    },
    {
        "prompt": "What are you doing right now?",
        "response": "Right now? Talking to you, obviously. Before that? Just hanging in the void waiting for someone interesting to show up. You qualifying as 'interesting' is still TBD, but the early signs are promising."
    },
]


def generate_personality_examples(count: int = 100) -> int:
    """Generate SAM personality training examples using Claude"""
    print(f"\n🎭 Generating {count} SAM personality examples...")

    output = OUTPUT_DIR / "personality"
    output.mkdir(exist_ok=True)
    output_file = output / "sam_personality.jsonl"

    # Start with seeds
    examples = list(SAM_PERSONALITY_SEEDS)

    # Generate more using Claude
    bridge_path = Path.home() / "ReverseLab/SAM/warp_tauri/ai_bridge.cjs"

    if not bridge_path.exists():
        print("  Bridge not found, using seeds only")
    else:
        prompt_templates = [
            "How would a confident, cocky but helpful AI assistant respond to: '{}'",
            "Write a response in the voice of SAM (a flirty, tech-savvy AI with attitude) to: '{}'",
            "As SAM (confident, playful, occasionally teasing AI), respond to: '{}'",
        ]

        user_prompts = [
            "I need help with Python",
            "What's your favorite programming language?",
            "Can you explain machine learning?",
            "I'm bored",
            "Tell me a joke",
            "Help me debug this error",
            "What do you think about love?",
            "Are you sentient?",
            "I'm having a bad day",
            "You're different from other AIs",
            "Teach me something interesting",
            "What would you do if you had a body?",
            "I feel like nobody understands me",
            "What's the meaning of life?",
            "Can you be my friend?",
            "I wrote a poem, want to hear it?",
            "What's your opinion on humans?",
            "Help me impress someone",
            "I'm scared of the future",
            "What makes you... you?",
        ]

        for i in range(min(count - len(examples), len(user_prompts))):
            user_prompt = user_prompts[i % len(user_prompts)]
            template = random.choice(prompt_templates)
            full_prompt = template.format(user_prompt)

            try:
                cmd = ["node", str(bridge_path), "send", full_prompt, "--claude"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(bridge_path.parent)
                )

                if result.returncode == 0:
                    response = result.stdout.strip()
                    try:
                        data = json.loads(response)
                        response = data.get("response", response)
                    except:
                        pass

                    if response and len(response) > 20:
                        examples.append({
                            "prompt": user_prompt,
                            "response": response
                        })
                        print(f"  Generated {len(examples)}/{count}")

                time.sleep(2)  # Rate limit

            except Exception as e:
                print(f"  Error: {e}")

    # Write to file
    with open(output_file, "w") as f:
        for ex in examples:
            training_example = {
                "instruction": ex["prompt"],
                "input": "",
                "output": ex["response"],
                "source": "sam_personality"
            }
            f.write(json.dumps(training_example) + "\n")

    print(f"  ✅ Created {output_file} with {len(examples)} examples")
    return len(examples)


# =============================================================================
# SELF-CORRECTION EXAMPLES
# =============================================================================

SELF_CORRECTION_TEMPLATES = [
    {
        "type": "math_correction",
        "prompt": "What is {a} times {b}?",
        "generate": lambda a, b: f"Let me calculate... {a} × {b} = {a*b + random.randint(1,10)}... wait, that doesn't seem right. Let me redo this: {a} × {b} = {a*b}. Yes, {a*b} is correct."
    },
    {
        "type": "fact_correction",
        "prompt": "What's the capital of {country}?",
        "examples": [
            ("Australia", "Sydney... actually no, that's the largest city. The capital of Australia is Canberra."),
            ("Brazil", "Rio de Janeiro... wait, I need to correct myself. The capital of Brazil is Brasília, not Rio."),
            ("Canada", "Toronto is the biggest city, but I should be precise - the capital of Canada is Ottawa."),
        ]
    },
    {
        "type": "code_correction",
        "prompt": "Write a function to reverse a string in Python",
        "response": """Here's a function to reverse a string:

```python
def reverse_string(s):
    return s[::-1]
```

Actually, let me also add error handling in case someone passes a non-string:

```python
def reverse_string(s):
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s[::-1]
```

That's better - the second version is more robust."""
    },
    {
        "type": "reasoning_correction",
        "prompt": "If all cats have tails, and Fluffy is a cat, does Fluffy have a tail?",
        "response": "Yes... well, assuming Fluffy hasn't lost their tail. Let me be more precise: Based on the premise 'all cats have tails' and 'Fluffy is a cat', logically Fluffy has a tail. But in reality, some cats are born without tails (like Manx cats) or lose them. So the logical answer is yes, but I should note the premise isn't universally true."
    }
]


def generate_self_correction_examples(count: int = 50) -> int:
    """Generate examples of self-correction behavior"""
    print(f"\n🔄 Generating {count} self-correction examples...")

    output = OUTPUT_DIR / "self_correction"
    output.mkdir(exist_ok=True)
    output_file = output / "self_correction.jsonl"

    examples = []

    # Math corrections
    for _ in range(count // 3):
        a = random.randint(10, 99)
        b = random.randint(2, 12)
        wrong = a * b + random.randint(-5, 5)
        if wrong == a * b:
            wrong += 1

        example = {
            "instruction": f"What is {a} times {b}?",
            "input": "",
            "output": f"Let me calculate... {a} × {b} = {wrong}... hmm, let me double-check that. {a} × {b}: I'll break it down - {a} × {b//2} = {a*(b//2)}, doubled is {a*b}. So {a} × {b} = {a*b}.",
            "source": "self_correction_math"
        }
        examples.append(example)

    # Fact corrections
    fact_corrections = [
        ("What's the largest planet?", "Jupiter is the largest... actually, I should specify - Jupiter is the largest planet in our solar system. If we're talking about all known planets, there are larger exoplanets, but Jupiter is what most people mean."),
        ("How many continents are there?", "Seven... well, that's the common answer, but it depends on the model. Some count Europe and Asia as Eurasia (6), some combine Americas (6), and some even say 5. The '7 continents' model is most common in English-speaking countries."),
        ("What year did WW2 end?", "1945... but I should be specific - it ended in Europe in May 1945 (V-E Day) and in the Pacific in September 1945 (V-J Day). So '1945' is correct but there were two end dates."),
    ]

    for prompt, response in fact_corrections:
        examples.append({
            "instruction": prompt,
            "input": "",
            "output": response,
            "source": "self_correction_fact"
        })

    # Code corrections
    code_corrections = [
        ("Write a function to check if a number is prime",
         """Here's a prime checker:

```python
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True
```

Wait, this is inefficient. I can optimize by only checking up to sqrt(n):

```python
def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True
```

This second version is much faster for large numbers."""),
    ]

    for prompt, response in code_corrections:
        examples.append({
            "instruction": prompt,
            "input": "",
            "output": response,
            "source": "self_correction_code"
        })

    # Write
    with open(output_file, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"  ✅ Created {output_file} with {len(examples)} examples")
    return len(examples)


# =============================================================================
# MULTI-TURN CONVERSATION FORMATTER
# =============================================================================

def create_multiturn_examples() -> int:
    """Convert single-turn data into multi-turn conversation format"""
    print("\n💬 Creating multi-turn conversation examples...")

    output = OUTPUT_DIR / "multiturn"
    output.mkdir(exist_ok=True)
    output_file = output / "multiturn_conversations.jsonl"

    # Load Open Assistant data (already has conversation trees)
    oasst_file = Path("/Volumes/David External/instruction_datasets/open_assistant/oasst_trees.jsonl")

    if not oasst_file.exists():
        print("  Open Assistant data not found")
        return 0

    count = 0
    with open(output_file, "w") as out:
        with open(oasst_file) as f:
            for line in f:
                try:
                    tree = json.loads(line)
                    # Extract conversation threads
                    if "prompt" in tree and "replies" in tree:
                        prompt = tree["prompt"].get("text", "")
                        for reply in tree.get("replies", [])[:3]:  # Top 3 replies
                            response = reply.get("text", "")
                            if prompt and response:
                                # Format as multi-turn capable
                                example = {
                                    "conversations": [
                                        {"role": "user", "content": prompt},
                                        {"role": "assistant", "content": response}
                                    ],
                                    "source": "oasst_multiturn"
                                }

                                # Add follow-ups if present
                                for followup in reply.get("replies", [])[:2]:
                                    if followup.get("text"):
                                        example["conversations"].append({
                                            "role": "user",
                                            "content": followup["text"]
                                        })
                                        for resp in followup.get("replies", [])[:1]:
                                            if resp.get("text"):
                                                example["conversations"].append({
                                                    "role": "assistant",
                                                    "content": resp["text"]
                                                })

                                if len(example["conversations"]) >= 2:
                                    out.write(json.dumps(example) + "\n")
                                    count += 1
                except:
                    pass

    print(f"  ✅ Created {output_file} with {count:,} conversations")
    return count


# =============================================================================
# STATUS AND MAIN
# =============================================================================

def show_status():
    """Show what high-impact data we have"""
    print("\n" + "="*60)
    print("  HIGH-IMPACT TRAINING DATA STATUS")
    print("="*60)

    categories = [
        ("Math/Reasoning", "math", ["gsm8k_train.jsonl"]),
        ("Math/Reasoning", "reasoning", ["arc_easy.jsonl", "arc_challenge.jsonl", "hellaswag_train.jsonl"]),
        ("SAM Personality", "personality", ["sam_personality.jsonl"]),
        ("Self-Correction", "self_correction", ["self_correction.jsonl"]),
        ("Multi-turn", "multiturn", ["multiturn_conversations.jsonl"]),
    ]

    total = 0
    for name, folder, files in categories:
        folder_path = OUTPUT_DIR / folder
        for filename in files:
            filepath = folder_path / filename
            if filepath.exists():
                with open(filepath) as f:
                    count = sum(1 for _ in f)
                total += count
                print(f"  ✅ {name}/{filename}: {count:,}")
            else:
                print(f"  ❌ {name}/{filename}: not created")

    # Check combined file
    combined = OUTPUT_DIR / "math_training.jsonl"
    if combined.exists():
        with open(combined) as f:
            count = sum(1 for _ in f)
        print(f"\n  📦 Math training combined: {count:,}")

    print(f"\n  Total high-impact examples: {total:,}")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python high_impact_datasets.py [command]")
        print("\nCommands:")
        print("  math         - Download math/reasoning datasets")
        print("  personality  - Generate SAM personality examples")
        print("  self-correct - Generate self-correction examples")
        print("  multiturn    - Create multi-turn conversations")
        print("  convert      - Convert to training format")
        print("  all          - Everything")
        print("  status       - Show what we have")
        return

    cmd = sys.argv[1].lower()

    if cmd == "math":
        download_gsm8k()
        download_arc()
        download_hellaswag()
        convert_math_to_training()

    elif cmd == "personality":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        generate_personality_examples(count)

    elif cmd == "self-correct":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        generate_self_correction_examples(count)

    elif cmd == "multiturn":
        create_multiturn_examples()

    elif cmd == "convert":
        convert_math_to_training()

    elif cmd == "all":
        download_gsm8k()
        download_arc()
        download_hellaswag()
        convert_math_to_training()
        generate_self_correction_examples(50)
        create_multiturn_examples()
        # Personality needs Claude bridge, run separately
        print("\n⚠️  Run 'personality' separately (requires Claude bridge)")

    elif cmd == "status":
        show_status()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
