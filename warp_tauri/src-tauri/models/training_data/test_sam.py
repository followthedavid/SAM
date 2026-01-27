#!/usr/bin/env python3
"""Test the fine-tuned SAM model"""
import sys
sys.path.insert(0, 'venv/lib/python3.14/site-packages')

from mlx_lm import load, generate

# Load fine-tuned model
model, tokenizer = load(
    "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
    adapter_path="./sam-finetuned/adapters"
)

def chat(prompt):
    response = generate(
        model, tokenizer,
        prompt=prompt,
        max_tokens=200,
        verbose=False
    )
    return response

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Hello, how are you?"

    print(chat(prompt))
