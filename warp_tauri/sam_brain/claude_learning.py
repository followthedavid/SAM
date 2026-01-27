#!/usr/bin/env python3
"""
Claude Learning System - Extract knowledge from Claude conversations

This is the KEY to reaching parity: Every Claude session is free training data.

What we extract:
1. Code generation patterns (input → code output)
2. Reasoning chains (how Claude thinks through problems)
3. Error→fix mappings (debugging patterns)
4. Explanation styles (how to explain code)
5. Tool use patterns (when to use which tool)
6. Planning patterns (how to decompose tasks)

The insight: We're not stealing Claude's weights. We're learning from
its outputs in conversations WE already paid for.
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TrainingPair:
    """A single training example."""
    instruction: str
    input: str  # Optional additional context
    output: str
    category: str  # code, reasoning, error_fix, explanation, planning
    quality_score: float  # 0-1, estimated
    source: str  # chatgpt, claude, manual
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConversationAnalysis:
    """Analysis of a single conversation."""
    conversation_id: str
    title: str
    message_count: int
    training_pairs: List[TrainingPair]
    capabilities_demonstrated: List[str]
    quality_assessment: Dict


class ClaudeLearner:
    """
    Extract training data from Claude Code sessions.

    Claude Code stores conversations in ~/.claude/
    We can parse these to learn:
    - What requests lead to what tool usage
    - How Claude structures multi-step solutions
    - Code patterns for specific tasks
    """

    def __init__(self, claude_dir: Path = None):
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.output_dir = Path(__file__).parent / "claude_training_data"
        self.output_dir.mkdir(exist_ok=True)

    def find_conversations(self) -> List[Path]:
        """Find all Claude conversation files."""
        conversations = []

        # Claude Code stores projects in ~/.claude/projects/
        projects_dir = self.claude_dir / "projects"
        if projects_dir.exists():
            for project in projects_dir.iterdir():
                if project.is_dir():
                    # Look for conversation files
                    for conv_file in project.glob("**/*.json"):
                        conversations.append(conv_file)

        # Also check for conversation exports
        exports_dir = self.claude_dir / "exports"
        if exports_dir.exists():
            conversations.extend(exports_dir.glob("*.json"))

        return conversations

    def parse_claude_conversation(self, conv_file: Path) -> Optional[ConversationAnalysis]:
        """Parse a Claude conversation file."""
        try:
            data = json.load(open(conv_file))
        except:
            return None

        # Handle different formats
        messages = data.get("messages", data.get("conversation", []))
        if not messages:
            return None

        pairs = []
        capabilities = set()

        # Group into request/response pairs
        current_user_msg = None

        for msg in messages:
            role = msg.get("role", msg.get("type", ""))
            content = self._extract_content(msg)

            if role in ["user", "human"]:
                current_user_msg = content
            elif role in ["assistant", "ai"] and current_user_msg:
                # Extract training pair
                pair = self._extract_training_pair(current_user_msg, content)
                if pair:
                    pairs.append(pair)
                    capabilities.add(pair.category)

                current_user_msg = None

        if not pairs:
            return None

        return ConversationAnalysis(
            conversation_id=conv_file.stem,
            title=data.get("title", conv_file.stem),
            message_count=len(messages),
            training_pairs=pairs,
            capabilities_demonstrated=list(capabilities),
            quality_assessment=self._assess_quality(pairs),
        )

    def _extract_content(self, msg: Dict) -> str:
        """Extract text content from a message."""
        content = msg.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            # Handle content blocks
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
            return "\n".join(text_parts)

        return str(content)

    def _extract_training_pair(
        self,
        user_msg: str,
        assistant_msg: str
    ) -> Optional[TrainingPair]:
        """Extract a training pair from a message exchange."""

        # Skip very short exchanges
        if len(user_msg) < 10 or len(assistant_msg) < 50:
            return None

        # Categorize the exchange
        category = self._categorize_exchange(user_msg, assistant_msg)

        # Estimate quality
        quality = self._estimate_quality(user_msg, assistant_msg)

        # Skip low quality
        if quality < 0.3:
            return None

        return TrainingPair(
            instruction=user_msg[:2000],  # Truncate long messages
            input="",
            output=assistant_msg[:4000],
            category=category,
            quality_score=quality,
            source="claude",
            metadata={
                "has_code": "```" in assistant_msg,
                "has_reasoning": any(w in assistant_msg.lower() for w in ["because", "therefore", "since"]),
            }
        )

    def _categorize_exchange(self, user: str, assistant: str) -> str:
        """Categorize the type of exchange."""
        user_lower = user.lower()
        assistant_lower = assistant.lower()

        # Code generation
        if "```" in assistant and any(w in user_lower for w in ["write", "create", "implement", "function", "code"]):
            return "code_generation"

        # Error fixing
        if any(w in user_lower for w in ["error", "exception", "bug", "fix", "not working"]):
            return "error_fix"

        # Explanation
        if any(w in user_lower for w in ["explain", "what does", "how does", "why"]):
            return "explanation"

        # Planning
        if any(w in user_lower for w in ["plan", "steps", "how to", "implement"]):
            return "planning"

        # Reasoning
        if any(w in assistant_lower for w in ["first", "then", "because", "therefore"]):
            return "reasoning"

        # Code review
        if any(w in user_lower for w in ["review", "check", "analyze"]):
            return "code_review"

        return "general"

    def _estimate_quality(self, user: str, assistant: str) -> float:
        """Estimate the quality of a training pair."""
        score = 0.5  # Base score

        # Longer, detailed responses are usually better
        if len(assistant) > 200:
            score += 0.1
        if len(assistant) > 500:
            score += 0.1

        # Code with explanation is high quality
        if "```" in assistant and len(assistant) > len(assistant.split("```")[1] if "```" in assistant else ""):
            score += 0.15

        # Structured responses
        if re.search(r'\d+\.\s', assistant):  # Numbered lists
            score += 0.1

        # Clear reasoning
        reasoning_words = ["because", "therefore", "this means", "the reason"]
        if any(w in assistant.lower() for w in reasoning_words):
            score += 0.1

        # Penalize very short user messages (might be ambiguous)
        if len(user) < 20:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    def _assess_quality(self, pairs: List[TrainingPair]) -> Dict:
        """Assess overall quality of extracted pairs."""
        if not pairs:
            return {"quality": "none", "count": 0}

        avg_quality = sum(p.quality_score for p in pairs) / len(pairs)
        categories = defaultdict(int)
        for p in pairs:
            categories[p.category] += 1

        return {
            "quality": "high" if avg_quality > 0.7 else "medium" if avg_quality > 0.5 else "low",
            "average_score": avg_quality,
            "count": len(pairs),
            "by_category": dict(categories),
        }

    def extract_all(self) -> List[TrainingPair]:
        """Extract training pairs from all conversations."""
        all_pairs = []

        conversations = self.find_conversations()
        print(f"Found {len(conversations)} conversation files")

        for conv_file in conversations:
            analysis = self.parse_claude_conversation(conv_file)
            if analysis:
                all_pairs.extend(analysis.training_pairs)
                print(f"  {conv_file.name}: {len(analysis.training_pairs)} pairs")

        return all_pairs


class ChatGPTLearner:
    """
    Extract training data from ChatGPT exports.

    ChatGPT exports are in conversations.json format.
    """

    def __init__(self, export_path: Path = None):
        self.export_path = export_path
        self.output_dir = Path(__file__).parent / "chatgpt_training_data"
        self.output_dir.mkdir(exist_ok=True)

    def find_exports(self) -> List[Path]:
        """Find ChatGPT export files."""
        exports = []

        # Common locations
        search_paths = [
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path("/Volumes/David External"),
        ]

        for path in search_paths:
            if path.exists():
                exports.extend(path.glob("**/conversations.json"))
                exports.extend(path.glob("**/chatgpt*.json"))

        return exports

    def parse_export(self, export_file: Path) -> List[TrainingPair]:
        """Parse a ChatGPT export file."""
        try:
            data = json.load(open(export_file))
        except:
            return []

        pairs = []

        # Handle different export formats
        conversations = data if isinstance(data, list) else [data]

        for conv in conversations:
            conv_pairs = self._parse_conversation(conv)
            pairs.extend(conv_pairs)

        return pairs

    def _parse_conversation(self, conv: Dict) -> List[TrainingPair]:
        """Parse a single ChatGPT conversation."""
        pairs = []

        # Get message mapping
        mapping = conv.get("mapping", {})
        if not mapping:
            return []

        # Build message chain
        messages = []
        for msg_id, msg_data in mapping.items():
            msg = msg_data.get("message")
            if not msg:
                continue

            role = msg.get("author", {}).get("role", "")
            content = msg.get("content", {})

            # Extract text
            text = ""
            if isinstance(content, dict):
                parts = content.get("parts", [])
                text = parts[0] if parts else ""
            elif isinstance(content, str):
                text = content

            if text and role in ["user", "assistant"]:
                messages.append({"role": role, "content": text})

        # Group into pairs
        for i in range(len(messages) - 1):
            if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                user_msg = messages[i]["content"]
                assistant_msg = messages[i + 1]["content"]

                pair = self._create_pair(user_msg, assistant_msg)
                if pair:
                    pairs.append(pair)

        return pairs

    def _create_pair(self, user: str, assistant: str) -> Optional[TrainingPair]:
        """Create a training pair from a message exchange."""
        if len(user) < 10 or len(assistant) < 50:
            return None

        category = self._categorize(user, assistant)
        quality = self._estimate_quality(user, assistant)

        if quality < 0.3:
            return None

        return TrainingPair(
            instruction=user[:2000],
            input="",
            output=assistant[:4000],
            category=category,
            quality_score=quality,
            source="chatgpt",
        )

    def _categorize(self, user: str, assistant: str) -> str:
        """Categorize the exchange."""
        user_lower = user.lower()

        if "```" in assistant and any(w in user_lower for w in ["write", "code", "function"]):
            return "code_generation"
        if any(w in user_lower for w in ["error", "bug", "fix"]):
            return "error_fix"
        if any(w in user_lower for w in ["explain", "what", "how"]):
            return "explanation"
        return "general"

    def _estimate_quality(self, user: str, assistant: str) -> float:
        """Estimate quality."""
        score = 0.5

        if len(assistant) > 300:
            score += 0.2
        if "```" in assistant:
            score += 0.15
        if re.search(r'\d+\.\s', assistant):
            score += 0.1

        return min(score, 1.0)


class UnifiedTrainingExporter:
    """
    Combine all sources and export to MLX training format.
    """

    def __init__(self, brain_dir: Path = None):
        self.brain_dir = brain_dir or Path(__file__).parent
        self.output_dir = self.brain_dir / "unified_training_data"
        self.output_dir.mkdir(exist_ok=True)

    def collect_all_pairs(self) -> List[TrainingPair]:
        """Collect training pairs from all sources."""
        all_pairs = []

        # Claude conversations
        print("Extracting from Claude...")
        claude = ClaudeLearner()
        claude_pairs = claude.extract_all()
        all_pairs.extend(claude_pairs)
        print(f"  → {len(claude_pairs)} pairs from Claude")

        # ChatGPT exports
        print("Extracting from ChatGPT...")
        chatgpt = ChatGPTLearner()
        for export in chatgpt.find_exports():
            pairs = chatgpt.parse_export(export)
            all_pairs.extend(pairs)
            print(f"  → {len(pairs)} pairs from {export.name}")

        # Existing training data
        existing_file = self.brain_dir / "training_data.jsonl"
        if existing_file.exists():
            print("Loading existing training data...")
            for line in open(existing_file):
                try:
                    data = json.loads(line)
                    all_pairs.append(TrainingPair(
                        instruction=data.get("input", data.get("instruction", "")),
                        input="",
                        output=data.get("output", ""),
                        category="existing",
                        quality_score=0.7,
                        source="manual",
                    ))
                except:
                    continue
            print(f"  → Loaded existing data")

        # Escalation learning data
        escalation_file = self.brain_dir / "escalation_data" / "escalation_events.jsonl"
        if escalation_file.exists():
            print("Loading escalation learning data...")
            count = 0
            for line in open(escalation_file):
                try:
                    data = json.loads(line)
                    all_pairs.append(TrainingPair(
                        instruction=data["request"],
                        input="",
                        output=data["claude_response"],
                        category=data.get("capability", "escalation"),
                        quality_score=0.85,  # Claude responses are high quality
                        source="escalation",
                    ))
                    count += 1
                except:
                    continue
            print(f"  → {count} pairs from escalation learning")

        return all_pairs

    def deduplicate(self, pairs: List[TrainingPair]) -> List[TrainingPair]:
        """Remove duplicate or near-duplicate pairs."""
        seen = set()
        unique = []

        for pair in pairs:
            # Create a hash of the instruction
            key = hash(pair.instruction[:100].lower())

            if key not in seen:
                seen.add(key)
                unique.append(pair)

        return unique

    def balance_categories(self, pairs: List[TrainingPair]) -> List[TrainingPair]:
        """Balance training data across categories."""
        by_category = defaultdict(list)
        for p in pairs:
            by_category[p.category].append(p)

        # Find the median category size
        sizes = sorted(len(v) for v in by_category.values())
        target_size = sizes[len(sizes) // 2] if sizes else 100

        balanced = []
        for category, cat_pairs in by_category.items():
            # Sort by quality
            cat_pairs.sort(key=lambda x: -x.quality_score)

            # Take up to target_size, but always keep high quality
            high_quality = [p for p in cat_pairs if p.quality_score > 0.7]
            others = [p for p in cat_pairs if p.quality_score <= 0.7]

            balanced.extend(high_quality[:target_size])
            remaining = target_size - len(high_quality[:target_size])
            if remaining > 0:
                balanced.extend(others[:remaining])

        return balanced

    def export_mlx_format(self, pairs: List[TrainingPair]) -> Path:
        """Export to MLX LoRA training format."""
        # Shuffle for training
        import random
        random.shuffle(pairs)

        # Split train/val
        split = int(len(pairs) * 0.9)
        train = pairs[:split]
        val = pairs[split:]

        # Write train.jsonl
        train_file = self.output_dir / "train.jsonl"
        with open(train_file, "w") as f:
            for pair in train:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": pair.instruction},
                        {"role": "assistant", "content": pair.output},
                    ]
                }) + "\n")

        # Write valid.jsonl
        val_file = self.output_dir / "valid.jsonl"
        with open(val_file, "w") as f:
            for pair in val:
                f.write(json.dumps({
                    "messages": [
                        {"role": "user", "content": pair.instruction},
                        {"role": "assistant", "content": pair.output},
                    ]
                }) + "\n")

        # Write stats
        stats = {
            "total_pairs": len(pairs),
            "train_size": len(train),
            "val_size": len(val),
            "by_category": dict(defaultdict(int, {p.category: 1 for p in pairs})),
            "by_source": dict(defaultdict(int, {p.source: 1 for p in pairs})),
            "exported_at": datetime.now().isoformat(),
        }

        stats_file = self.output_dir / "training_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        return self.output_dir

    def run_full_pipeline(self) -> Dict:
        """Run the full training data pipeline."""
        print("=" * 60)
        print("UNIFIED TRAINING DATA PIPELINE")
        print("=" * 60)
        print()

        # Collect
        all_pairs = self.collect_all_pairs()
        print(f"\nTotal collected: {len(all_pairs)} pairs")

        # Deduplicate
        unique_pairs = self.deduplicate(all_pairs)
        print(f"After deduplication: {len(unique_pairs)} pairs")

        # Balance (optional)
        # balanced_pairs = self.balance_categories(unique_pairs)
        # print(f"After balancing: {len(balanced_pairs)} pairs")

        # Export
        output_dir = self.export_mlx_format(unique_pairs)
        print(f"\nExported to: {output_dir}")

        # Category breakdown
        categories = defaultdict(int)
        sources = defaultdict(int)
        for p in unique_pairs:
            categories[p.category] += 1
            sources[p.source] += 1

        print("\nBy category:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        print("\nBy source:")
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"  {src}: {count}")

        return {
            "total": len(unique_pairs),
            "output_dir": str(output_dir),
            "categories": dict(categories),
            "sources": dict(sources),
        }


# =============================================================================
# REAL-TIME LEARNING HOOK
# =============================================================================

class RealTimeLearner:
    """
    Hook into Claude Code sessions to learn in real-time.

    This can be integrated into SAM's orchestrator to:
    1. Intercept requests that go to Claude
    2. Capture the responses
    3. Automatically add to training data
    """

    def __init__(self, brain_dir: Path = None):
        self.brain_dir = brain_dir or Path(__file__).parent
        self.queue_file = self.brain_dir / "realtime_learning_queue.jsonl"

    def record_interaction(
        self,
        user_request: str,
        response: str,
        source: str = "claude",
        category: str = "auto",
    ):
        """Record an interaction for learning."""
        if len(user_request) < 10 or len(response) < 50:
            return

        with open(self.queue_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "instruction": user_request[:2000],
                "output": response[:4000],
                "source": source,
                "category": category,
            }) + "\n")

    def get_queue_size(self) -> int:
        """Get number of queued interactions."""
        if not self.queue_file.exists():
            return 0
        return sum(1 for _ in open(self.queue_file))

    def flush_to_training(self, min_quality: float = 0.5) -> int:
        """Move queue to training data."""
        if not self.queue_file.exists():
            return 0

        training_file = self.brain_dir / "training_data.jsonl"
        count = 0

        with open(training_file, "a") as out:
            for line in open(self.queue_file):
                try:
                    data = json.loads(line)
                    out.write(json.dumps({
                        "input": data["instruction"],
                        "output": data["output"],
                    }) + "\n")
                    count += 1
                except:
                    continue

        # Clear queue
        self.queue_file.unlink()

        return count


# =============================================================================
# CLI
# =============================================================================

def main():
    import sys

    if len(sys.argv) < 2:
        print("Claude Learning System")
        print("=" * 60)
        print()
        print("Commands:")
        print("  extract    - Extract from all sources and export")
        print("  claude     - Extract from Claude conversations only")
        print("  chatgpt    - Extract from ChatGPT exports only")
        print("  stats      - Show current training data stats")
        print("  flush      - Move realtime queue to training data")
        print()
        return

    cmd = sys.argv[1]

    if cmd == "extract":
        exporter = UnifiedTrainingExporter()
        result = exporter.run_full_pipeline()
        print(f"\nReady for training: {result['total']} pairs")
        print(f"Run: python -m mlx_lm.lora --model Qwen/Qwen2.5-Coder-1.5B-Instruct --data {result['output_dir']} --train")

    elif cmd == "claude":
        learner = ClaudeLearner()
        pairs = learner.extract_all()
        print(f"Extracted {len(pairs)} pairs from Claude")

    elif cmd == "chatgpt":
        learner = ChatGPTLearner()
        for export in learner.find_exports():
            pairs = learner.parse_export(export)
            print(f"{export.name}: {len(pairs)} pairs")

    elif cmd == "stats":
        brain_dir = Path(__file__).parent
        print("Training Data Statistics")
        print("-" * 40)

        training_file = brain_dir / "training_data.jsonl"
        if training_file.exists():
            count = sum(1 for _ in open(training_file))
            print(f"training_data.jsonl: {count} pairs")

        unified_dir = brain_dir / "unified_training_data"
        if unified_dir.exists():
            stats_file = unified_dir / "training_stats.json"
            if stats_file.exists():
                stats = json.load(open(stats_file))
                print(f"unified_training_data: {stats['total_pairs']} pairs")
                print(f"  Last exported: {stats['exported_at']}")

        realtime = RealTimeLearner()
        queue_size = realtime.get_queue_size()
        print(f"Realtime queue: {queue_size} pending")

    elif cmd == "flush":
        learner = RealTimeLearner()
        count = learner.flush_to_training()
        print(f"Flushed {count} interactions to training data")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
