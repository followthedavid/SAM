#!/usr/bin/env python3
"""
ChatGPT Export Processor - Extract training data from OpenAI exports

This processes your 197MB ChatGPT export to create high-quality training
data for SAM fine-tuning.

Categories extracted:
1. Code generation (input → working code)
2. Code explanation (code → explanation)
3. Debugging/error fixing (error → solution)
4. Reasoning chains (question → step-by-step answer)
5. Planning (task → plan)
6. SAM personality (conversations that match SAM's style)
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib


CHATGPT_EXPORT_PATH = Path("/Volumes/David External/SAM_training/chatgpt_export/User Online Activity/conversations/personal/conversations/conversations.json")
OUTPUT_DIR = Path("/Volumes/David External/SAM_training/processed")


@dataclass
class TrainingExample:
    """A single training example."""
    instruction: str
    output: str
    category: str
    quality_score: float
    conversation_id: str
    turn_index: int
    has_code: bool = False
    code_language: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class ChatGPTProcessor:
    """Process ChatGPT exports for SAM training."""

    def __init__(self, export_path: Path = CHATGPT_EXPORT_PATH):
        self.export_path = export_path
        self.stats = defaultdict(int)

    def stream_conversations(self) -> Generator[Dict, None, None]:
        """Stream conversations from the export file."""
        print(f"Loading from: {self.export_path}")

        if not self.export_path.exists():
            print(f"Export not found: {self.export_path}")
            return

        # The file is large, so we'll stream it
        with open(self.export_path, 'r') as f:
            # Try to detect format
            first_char = f.read(1)
            f.seek(0)

            if first_char == '[':
                # JSON array format
                data = json.load(f)
                for conv in data:
                    yield conv
            else:
                # JSONL format
                for line in f:
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except:
                            continue

    def extract_messages(self, conversation: Dict) -> List[Tuple[str, str]]:
        """Extract user/assistant message pairs from a conversation."""
        pairs = []

        # Handle different export formats
        mapping = conversation.get("mapping", {})

        if mapping:
            # Standard ChatGPT export format
            messages = []

            for node_id, node in mapping.items():
                message = node.get("message")
                if not message:
                    continue

                author = message.get("author", {}).get("role", "")
                content = message.get("content", {})

                # Extract text content
                text = ""
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0] if isinstance(parts[0], str) else str(parts[0])
                elif isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = ' '.join(str(p) for p in content if p)

                if text and author in ["user", "assistant"]:
                    messages.append({
                        "role": author,
                        "content": text,
                        "create_time": message.get("create_time", 0),
                    })

            # Sort by create_time
            messages.sort(key=lambda x: x.get("create_time", 0))

            # Pair up messages
            for i in range(len(messages) - 1):
                if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                    pairs.append((
                        messages[i]["content"],
                        messages[i + 1]["content"]
                    ))

        return pairs

    def categorize(self, user_msg: str, assistant_msg: str) -> str:
        """Categorize the exchange."""
        user_lower = user_msg.lower()
        assistant_lower = assistant_msg.lower()

        # Check for code
        has_code = "```" in assistant_msg

        # Code generation
        if has_code and any(kw in user_lower for kw in [
            "write", "create", "implement", "code", "function", "class",
            "script", "program", "make a", "build"
        ]):
            return "code_generation"

        # Error/debugging
        if any(kw in user_lower for kw in [
            "error", "exception", "bug", "fix", "broken", "not working",
            "fails", "crash", "traceback", "issue"
        ]):
            return "debugging"

        # Code explanation
        if has_code and any(kw in user_lower for kw in [
            "explain", "what does", "how does", "walk through", "understand"
        ]):
            return "code_explanation"

        # Reasoning/analysis
        if any(kw in assistant_lower for kw in [
            "first,", "then,", "because", "therefore", "step 1", "step 2",
            "let me think", "the reason"
        ]):
            return "reasoning"

        # Planning
        if any(kw in user_lower for kw in [
            "plan", "steps", "how to", "process", "approach", "strategy"
        ]):
            return "planning"

        # Technical explanation
        if any(kw in user_lower for kw in [
            "what is", "how does", "explain", "difference between"
        ]) and len(assistant_msg) > 200:
            return "explanation"

        # General code (if has code but doesn't fit above)
        if has_code:
            return "code_general"

        return "general"

    def estimate_quality(self, user_msg: str, assistant_msg: str, category: str) -> float:
        """Estimate the quality of a training example."""
        score = 0.5

        # Length factors
        if len(assistant_msg) > 200:
            score += 0.1
        if len(assistant_msg) > 500:
            score += 0.1
        if len(assistant_msg) > 1000:
            score += 0.05

        # Structure factors
        if "```" in assistant_msg:
            score += 0.15  # Has code

        if re.search(r'\d+\.\s', assistant_msg):
            score += 0.1  # Has numbered list

        if re.search(r'^#+\s', assistant_msg, re.MULTILINE):
            score += 0.05  # Has headers

        # Reasoning indicators
        reasoning_words = ["because", "therefore", "since", "thus", "hence"]
        if any(w in assistant_msg.lower() for w in reasoning_words):
            score += 0.1

        # Category bonuses
        category_bonus = {
            "code_generation": 0.1,
            "debugging": 0.15,
            "code_explanation": 0.1,
            "reasoning": 0.1,
        }
        score += category_bonus.get(category, 0)

        # Penalties
        if len(user_msg) < 10:
            score -= 0.1  # Very short prompt
        if len(assistant_msg) < 50:
            score -= 0.2  # Very short response
        if "I'm sorry" in assistant_msg or "I cannot" in assistant_msg:
            score -= 0.3  # Refusal

        return max(0.0, min(1.0, score))

    def detect_code_language(self, text: str) -> Optional[str]:
        """Detect programming language from code blocks."""
        match = re.search(r'```(\w+)', text)
        if match:
            return match.group(1).lower()
        return None

    def process_all(self, min_quality: float = 0.4) -> List[TrainingExample]:
        """Process all conversations and extract training examples."""
        examples = []

        print("Processing conversations...")
        for i, conv in enumerate(self.stream_conversations()):
            conv_id = conv.get("id", conv.get("conversation_id", str(i)))
            self.stats["conversations"] += 1

            pairs = self.extract_messages(conv)

            for turn_idx, (user_msg, assistant_msg) in enumerate(pairs):
                self.stats["total_pairs"] += 1

                # Skip very short exchanges
                if len(user_msg) < 10 or len(assistant_msg) < 50:
                    self.stats["skipped_short"] += 1
                    continue

                # Categorize
                category = self.categorize(user_msg, assistant_msg)

                # Estimate quality
                quality = self.estimate_quality(user_msg, assistant_msg, category)

                if quality < min_quality:
                    self.stats["skipped_quality"] += 1
                    continue

                # Create example
                example = TrainingExample(
                    instruction=user_msg[:4000],
                    output=assistant_msg[:8000],
                    category=category,
                    quality_score=quality,
                    conversation_id=conv_id,
                    turn_index=turn_idx,
                    has_code="```" in assistant_msg,
                    code_language=self.detect_code_language(assistant_msg),
                )

                examples.append(example)
                self.stats["accepted"] += 1
                self.stats[f"category_{category}"] += 1

            # Progress
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1} conversations, {len(examples)} examples")

        return examples

    def deduplicate(self, examples: List[TrainingExample]) -> List[TrainingExample]:
        """Remove duplicate or near-duplicate examples."""
        seen = set()
        unique = []

        for ex in examples:
            # Hash based on first 100 chars of instruction
            key = hashlib.md5(ex.instruction[:100].lower().encode()).hexdigest()

            if key not in seen:
                seen.add(key)
                unique.append(ex)
            else:
                self.stats["duplicates_removed"] += 1

        return unique

    def export_mlx_format(
        self,
        examples: List[TrainingExample],
        output_dir: Path = OUTPUT_DIR
    ) -> Path:
        """Export to MLX training format."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Shuffle
        import random
        random.shuffle(examples)

        # Split 90/10
        split = int(len(examples) * 0.9)
        train = examples[:split]
        val = examples[split:]

        # Write train.jsonl
        train_file = output_dir / "train.jsonl"
        with open(train_file, "w") as f:
            for ex in train:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex.instruction},
                        {"role": "assistant", "content": ex.output},
                    ]
                }) + "\n")

        # Write valid.jsonl
        val_file = output_dir / "valid.jsonl"
        with open(val_file, "w") as f:
            for ex in val:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": ex.instruction},
                        {"role": "assistant", "content": ex.output},
                    ]
                }) + "\n")

        # Write stats
        stats_file = output_dir / "processing_stats.json"
        with open(stats_file, "w") as f:
            json.dump({
                "total_examples": len(examples),
                "train_size": len(train),
                "val_size": len(val),
                "stats": dict(self.stats),
                "processed_at": datetime.now().isoformat(),
            }, f, indent=2)

        return output_dir

    def export_by_category(
        self,
        examples: List[TrainingExample],
        output_dir: Path = OUTPUT_DIR
    ) -> Dict[str, Path]:
        """Export separate files by category for targeted training."""
        by_category = defaultdict(list)
        for ex in examples:
            by_category[ex.category].append(ex)

        outputs = {}
        for category, cat_examples in by_category.items():
            cat_dir = output_dir / f"category_{category}"
            cat_dir.mkdir(parents=True, exist_ok=True)

            # Split
            split = int(len(cat_examples) * 0.9)
            train = cat_examples[:split]
            val = cat_examples[split:] or cat_examples[:10]  # Ensure some validation

            # Write
            with open(cat_dir / "train.jsonl", "w") as f:
                for ex in train:
                    f.write(json.dumps({
                        "messages": [
                            {"role": "user", "content": ex.instruction},
                            {"role": "assistant", "content": ex.output},
                        ]
                    }) + "\n")

            with open(cat_dir / "valid.jsonl", "w") as f:
                for ex in val:
                    f.write(json.dumps({
                        "messages": [
                            {"role": "user", "content": ex.instruction},
                            {"role": "assistant", "content": ex.output},
                        ]
                    }) + "\n")

            outputs[category] = cat_dir
            print(f"  {category}: {len(cat_examples)} examples")

        return outputs


def run_full_pipeline():
    """Run the complete processing pipeline."""
    print("=" * 70)
    print("CHATGPT EXPORT PROCESSING PIPELINE")
    print("=" * 70)
    print()

    processor = ChatGPTProcessor()

    # Process
    print("Step 1: Extracting training examples...")
    examples = processor.process_all(min_quality=0.4)
    print(f"  → Extracted {len(examples)} examples")

    # Deduplicate
    print("\nStep 2: Deduplicating...")
    unique_examples = processor.deduplicate(examples)
    print(f"  → {len(unique_examples)} unique examples")

    # Sort by quality
    unique_examples.sort(key=lambda x: -x.quality_score)

    # Export combined
    print("\nStep 3: Exporting MLX format...")
    output = processor.export_mlx_format(unique_examples)
    print(f"  → Exported to {output}")

    # Export by category
    print("\nStep 4: Exporting by category...")
    categories = processor.export_by_category(unique_examples)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for key, value in sorted(processor.stats.items()):
        print(f"  {key}: {value}")

    print(f"\nTotal training examples: {len(unique_examples)}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Quality distribution
    print("\nQuality distribution:")
    quality_buckets = defaultdict(int)
    for ex in unique_examples:
        bucket = int(ex.quality_score * 10) / 10
        quality_buckets[bucket] += 1

    for bucket in sorted(quality_buckets.keys()):
        print(f"  {bucket:.1f}: {'#' * (quality_buckets[bucket] // 100)} ({quality_buckets[bucket]})")

    print("\nTo train SAM on this data:")
    print(f"  cd ~/ReverseLab/SAM/warp_tauri/sam_brain")
    print(f"  source .venv/bin/activate")
    print(f"  python -m mlx_lm.lora \\")
    print(f"    --model Qwen/Qwen2.5-Coder-1.5B-Instruct \\")
    print(f"    --data {OUTPUT_DIR} \\")
    print(f"    --train \\")
    print(f"    --batch-size 4 \\")
    print(f"    --lora-layers 8 \\")
    print(f"    --iters 1000")

    return unique_examples


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            # Just show stats without full processing
            processor = ChatGPTProcessor()
            count = 0
            for conv in processor.stream_conversations():
                count += 1
                if count >= 100:
                    break
            print(f"Sample: {count} conversations loaded")

        elif sys.argv[1] == "sample":
            # Show sample examples
            processor = ChatGPTProcessor()
            examples = processor.process_all(min_quality=0.6)[:10]
            for ex in examples:
                print(f"\n{'='*60}")
                print(f"Category: {ex.category} | Quality: {ex.quality_score:.2f}")
                print(f"Instruction: {ex.instruction[:200]}...")
                print(f"Output: {ex.output[:200]}...")

        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        run_full_pipeline()
