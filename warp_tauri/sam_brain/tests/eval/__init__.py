"""
SAM Benchmark Evaluation Suite

Sends curated prompts to the SAM API and scores responses across domains:
coding, chat, roleplay, reasoning, macOS, and reverse engineering.

Usage:
    python3 -m tests.eval.run_benchmark
    python3 -m tests.eval.run_benchmark --domain coding
    python3 -m tests.eval.run_benchmark --compare results/a.json results/b.json
"""
