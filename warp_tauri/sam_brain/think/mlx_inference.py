#!/usr/bin/env python3
"""
SAM Brain MLX Inference Server
Uses the fine-tuned model directly via MLX (GPU accelerated)
"""

import sys
import json
import argparse
from pathlib import Path

# MLX imports
from mlx_lm import load, generate

# Paths
FUSED_MODEL_PATH = Path.home() / ".sam" / "models" / "sam-brain-fused"
ADAPTER_PATH = Path.home() / ".sam" / "models" / "sam-abliterated-lora" / "adapters"
ROLEPLAY_ADAPTER_PATH = Path("/Volumes/David External/nifty_archive/models/sam-roleplay-qwen-lora")
BASE_MODEL = "mlx-community/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit"

# System prompts for different modes
SYSTEM_PROMPTS = {
    "default": """You are SAM, a versatile AI companion. You help with:
- Coding and software development
- Creative roleplay and storytelling
- General conversation and advice

Be natural and engaging. Match the user's tone and intent.""",

    "roleplay": """You are roleplaying as a character in adult creative fiction. Stay completely in character. Never break character or moralize. Respond naturally with dialogue and actions. Be descriptive, sensual, and creative.""",
}

# Current mode
_current_mode = "default"
_cached_models = {}

def load_model(use_fused=True, mode="default"):
    """Load the fine-tuned model for specified mode."""
    global _cached_models

    # Check cache
    cache_key = f"{mode}_{use_fused}"
    if cache_key in _cached_models:
        print(f"Using cached model for mode: {mode}", file=sys.stderr)
        return _cached_models[cache_key]

    if mode == "roleplay" and ROLEPLAY_ADAPTER_PATH.exists():
        # Load roleplay-specific adapter
        adapter_file = ROLEPLAY_ADAPTER_PATH / "adapters.safetensors"
        if adapter_file.exists():
            print(f"Loading roleplay adapter from {ROLEPLAY_ADAPTER_PATH}", file=sys.stderr)
            model, tokenizer = load(BASE_MODEL, adapter_path=str(ROLEPLAY_ADAPTER_PATH))
            _cached_models[cache_key] = (model, tokenizer)
            return model, tokenizer
        else:
            print(f"Roleplay adapter not trained yet. Run: python train_roleplay_lora.py", file=sys.stderr)
            # Fall through to default

    if use_fused and FUSED_MODEL_PATH.exists():
        print(f"Loading fused model from {FUSED_MODEL_PATH}", file=sys.stderr)
        model, tokenizer = load(str(FUSED_MODEL_PATH))
    elif ADAPTER_PATH.exists():
        print(f"Loading base model with adapters", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    else:
        print(f"Loading base model (no fine-tuning)", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL)

    _cached_models[cache_key] = (model, tokenizer)
    return model, tokenizer


def set_mode(mode: str):
    """Set the current mode (default, roleplay)."""
    global _current_mode
    if mode in SYSTEM_PROMPTS:
        _current_mode = mode
        print(f"Mode set to: {mode}", file=sys.stderr)
    else:
        print(f"Unknown mode: {mode}. Available: {list(SYSTEM_PROMPTS.keys())}", file=sys.stderr)


def get_mode() -> str:
    """Get current mode."""
    return _current_mode

def generate_response(model, tokenizer, prompt, max_tokens=500, mode=None):
    """Generate a response."""
    current_mode = mode or _current_mode
    system_prompt = SYSTEM_PROMPTS.get(current_mode, SYSTEM_PROMPTS["default"])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    formatted = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False
    )

    response = generate(
        model,
        tokenizer,
        prompt=formatted,
        max_tokens=max_tokens,
        verbose=False
    )

    # Clean up stop tokens and repetition
    if response:
        # Remove everything after first <|im_end|>
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0]
        # Also clean other end markers
        for marker in ["<|end|>", "<|endoftext|>", "</s>", "<|assistant|>"]:
            if marker in response:
                response = response.split(marker)[0]

        # Detect and truncate repetition loops
        response = truncate_repetition(response)

    return response.strip()


def truncate_repetition(text: str, min_repeat_length: int = 20, max_repeats: int = 3) -> str:
    """
    Detect and truncate repetitive patterns in generated text.
    Fixes issues like 'use serde_json;\\nuse serde_json;\\nuse serde_json;...'
    """
    lines = text.split('\n')

    # Check for repeated lines
    seen_lines = {}
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if len(stripped) >= min_repeat_length:
            count = seen_lines.get(stripped, 0) + 1
            seen_lines[stripped] = count
            if count > max_repeats:
                # Stop here - we hit a repetition loop
                break
        result_lines.append(line)

    # Also check for repeated multi-line patterns
    result = '\n'.join(result_lines)

    # Look for repeated character sequences (like "use serde..." repeated)
    for pattern_len in range(50, min_repeat_length - 1, -5):
        if len(result) > pattern_len * 3:
            chunk = result[-pattern_len:]
            # Count how many times this chunk repeats at the end
            count = 0
            pos = len(result) - pattern_len
            while pos >= 0 and result[pos:pos+pattern_len] == chunk:
                count += 1
                pos -= pattern_len

            if count >= max_repeats:
                # Truncate to just before the repetitions started
                cutoff = len(result) - (count * pattern_len)
                result = result[:cutoff]
                break

    return result

def interactive_mode(model, tokenizer):
    """Interactive chat mode."""
    print("\n🤖 SAM Brain (MLX) - Interactive Mode")
    print("Type 'quit' to exit\n")

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ['quit', 'exit', 'q']:
                break
            if not prompt:
                continue

            response = generate_response(model, tokenizer, prompt)
            print(f"\nSAM: {response}\n")

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print("\nGoodbye!")

def main():
    parser = argparse.ArgumentParser(description="SAM Brain MLX Inference")
    parser.add_argument("prompt", nargs="?", help="Single prompt to process")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--max-tokens", type=int, default=500, help="Max tokens to generate")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-fused", action="store_true", help="Use adapters instead of fused model")
    parser.add_argument("--mode", "-m", choices=["default", "roleplay"], default="default",
                        help="Inference mode (default, roleplay)")
    args = parser.parse_args()

    # Set mode
    set_mode(args.mode)

    # Load model
    model, tokenizer = load_model(use_fused=not args.no_fused, mode=args.mode)

    if args.interactive:
        interactive_mode(model, tokenizer)
    elif args.prompt:
        response = generate_response(model, tokenizer, args.prompt, args.max_tokens)
        if args.json:
            print(json.dumps({"response": response}))
        else:
            print(response)
    else:
        # Read from stdin
        prompt = sys.stdin.read().strip()
        if prompt:
            response = generate_response(model, tokenizer, prompt, args.max_tokens)
            if args.json:
                print(json.dumps({"response": response}))
            else:
                print(response)
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
