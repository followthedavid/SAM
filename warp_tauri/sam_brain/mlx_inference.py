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
ADAPTER_PATH = Path.home() / ".sam" / "models" / "sam-brain-lora" / "adapters"
BASE_MODEL = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

# System prompt for SAM Brain
SYSTEM_PROMPT = """You are SAM (Smart Autonomous Manager), an AI assistant specialized in:
- Software development and code review
- Project management and task routing
- Understanding codebases and documentation

Be concise and direct. Provide working code, not pseudocode."""

def load_model(use_fused=True):
    """Load the fine-tuned model."""
    if use_fused and FUSED_MODEL_PATH.exists():
        print(f"Loading fused model from {FUSED_MODEL_PATH}", file=sys.stderr)
        model, tokenizer = load(str(FUSED_MODEL_PATH))
    elif ADAPTER_PATH.exists():
        print(f"Loading base model with adapters", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    else:
        print(f"Loading base model (no fine-tuning)", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL)

    return model, tokenizer

def generate_response(model, tokenizer, prompt, max_tokens=500):
    """Generate a response."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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

    return response.strip()

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
    args = parser.parse_args()

    # Load model
    model, tokenizer = load_model(use_fused=not args.no_fused)

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
