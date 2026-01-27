#!/usr/bin/env python3
"""
SAM Training Data Preparation Pipeline

Phase 5.2.2 & 5.2.3: Training data preparation and splitting

Features:
- Convert examples to MLX format (instruction, chat, DPO)
- Tokenization with Qwen2.5 tokenizer
- Sequence length validation and truncation
- Train/val/test splits (90/5/5) with domain stratification
- JSONL output for MLX training

Optimized for 8GB M2 Mac Mini.
"""

import os
import json
import random
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("training_prep")


class TrainingFormat(Enum):
    """Supported training data formats."""
    INSTRUCTION = "instruction"  # instruction/input/output format
    CHAT = "chat"                # messages format (Qwen chat template)
    DPO = "dpo"                  # chosen/rejected format for preference learning


@dataclass
class TokenizationConfig:
    """Configuration for tokenization."""
    max_seq_length: int = 512         # Default for 8GB systems
    truncation_side: str = "right"    # Truncate from right side
    padding_side: str = "right"       # Pad on right side
    add_special_tokens: bool = True
    model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"


@dataclass
class SplitConfig:
    """Configuration for data splitting."""
    train_ratio: float = 0.90
    val_ratio: float = 0.05
    test_ratio: float = 0.05
    stratify_by_domain: bool = True
    random_seed: int = 42
    shuffle: bool = True


@dataclass
class PreparedExample:
    """A single prepared training example."""
    text: str                          # Formatted text ready for tokenization
    token_count: int                   # Estimated token count
    format_type: TrainingFormat
    domain: Optional[str] = None       # Domain for stratification
    source_file: Optional[str] = None  # Original source file
    example_id: str = ""               # Unique identifier
    is_truncated: bool = False         # Whether example was truncated
    original_length: int = 0           # Original length before truncation


@dataclass
class DatasetStats:
    """Statistics about the prepared dataset."""
    total_examples: int = 0
    train_examples: int = 0
    val_examples: int = 0
    test_examples: int = 0
    truncated_count: int = 0
    avg_token_count: float = 0.0
    max_token_count: int = 0
    min_token_count: int = 0
    domains: Dict[str, int] = field(default_factory=dict)
    format_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_examples": self.total_examples,
            "train_examples": self.train_examples,
            "val_examples": self.val_examples,
            "test_examples": self.test_examples,
            "truncated_count": self.truncated_count,
            "avg_token_count": round(self.avg_token_count, 2),
            "max_token_count": self.max_token_count,
            "min_token_count": self.min_token_count,
            "domains": self.domains,
            "format_counts": self.format_counts,
        }


class TrainingDataPrep:
    """
    Training data preparation pipeline for SAM Brain.

    Handles:
    - Loading raw training data from JSONL files
    - Converting to MLX-compatible formats (instruction, chat, DPO)
    - Tokenization with Qwen2.5 tokenizer
    - Sequence length validation and truncation
    - Train/val/test splitting with optional domain stratification

    Usage:
        prep = TrainingDataPrep()
        prep.load_data("/path/to/training_data")
        prep.prepare_for_training()
        prep.split_data("/path/to/output")
    """

    # Qwen2.5 chat template tokens
    CHAT_TEMPLATE = {
        "im_start": "<|im_start|>",
        "im_end": "<|im_end|>",
        "system": "system",
        "user": "user",
        "assistant": "assistant",
    }

    # SAM's default system prompt
    DEFAULT_SYSTEM_PROMPT = """You are SAM, a self-improving AI assistant specialized in:
- Software development and code review
- Project management and task routing
- Understanding codebases and documentation

You are confident, helpful, and direct. Be concise and accurate."""

    def __init__(
        self,
        tokenization_config: Optional[TokenizationConfig] = None,
        split_config: Optional[SplitConfig] = None,
    ):
        """
        Initialize the training data preparation pipeline.

        Args:
            tokenization_config: Configuration for tokenization
            split_config: Configuration for data splitting
        """
        self.tokenization_config = tokenization_config or TokenizationConfig()
        self.split_config = split_config or SplitConfig()

        self._raw_data: List[Dict[str, Any]] = []
        self._prepared_examples: List[PreparedExample] = []
        self._tokenizer = None
        self._stats = DatasetStats()

        # External storage paths (8GB optimization)
        self.external_storage = Path("/Volumes/David External/sam_training")
        self.cache_dir = self.external_storage / "prep_cache"

    def _load_tokenizer(self) -> bool:
        """
        Lazy-load the tokenizer for token counting.

        Returns:
            True if tokenizer loaded successfully
        """
        if self._tokenizer is not None:
            return True

        try:
            from transformers import AutoTokenizer

            logger.info(f"Loading tokenizer: {self.tokenization_config.model_name}")
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.tokenization_config.model_name,
                trust_remote_code=True,
            )
            logger.info("Tokenizer loaded successfully")
            return True

        except ImportError:
            logger.warning("transformers not installed, using character-based estimation")
            return False
        except Exception as e:
            logger.warning(f"Failed to load tokenizer: {e}, using character-based estimation")
            return False

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses actual tokenizer if available, otherwise estimates
        ~4 characters per token (conservative for code).

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if self._tokenizer is not None:
            tokens = self._tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        else:
            # Conservative estimate: ~4 chars per token for code
            return len(text) // 4

    def _generate_example_id(self, content: str) -> str:
        """Generate a unique ID for an example based on content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _detect_domain(self, example: Dict[str, Any]) -> str:
        """
        Detect the domain/category of an example.

        Used for stratified splitting.

        Args:
            example: Raw example data

        Returns:
            Domain string (e.g., "code", "routing", "knowledge", "general")
        """
        # Check source file path for hints
        source = example.get("source", example.get("source_file", ""))
        if isinstance(source, str):
            source_lower = source.lower()
            if "commit" in source_lower:
                return "commits"
            elif "routing" in source_lower:
                return "routing"
            elif "knowledge" in source_lower or "doc" in source_lower:
                return "knowledge"
            elif "code" in source_lower:
                return "code"

        # Check content for hints
        instruction = example.get("instruction", "")
        content = example.get("input", "") + example.get("output", "")

        if "```" in content or "def " in content or "class " in content:
            return "code"
        elif "route" in instruction.lower() or "which" in instruction.lower():
            return "routing"
        elif len(content) > 1000:
            return "knowledge"
        else:
            return "general"

    def load_data(
        self,
        data_path: Union[str, Path],
        recursive: bool = True,
    ) -> int:
        """
        Load raw training data from JSONL files.

        Args:
            data_path: Path to directory or single JSONL file
            recursive: Whether to search subdirectories

        Returns:
            Number of examples loaded
        """
        data_path = Path(data_path)
        self._raw_data = []

        if data_path.is_file():
            files = [data_path]
        elif data_path.is_dir():
            pattern = "**/*.jsonl" if recursive else "*.jsonl"
            files = list(data_path.glob(pattern))
        else:
            logger.error(f"Invalid data path: {data_path}")
            return 0

        logger.info(f"Loading data from {len(files)} files...")

        for jsonl_file in files:
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            example = json.loads(line)
                            example["source_file"] = str(jsonl_file)
                            self._raw_data.append(example)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Skipping invalid JSON at {jsonl_file}:{line_num}: {e}")
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")

        logger.info(f"Loaded {len(self._raw_data)} raw examples")
        return len(self._raw_data)

    def _format_instruction(self, example: Dict[str, Any]) -> str:
        """
        Format example as instruction format with Qwen chat template.

        Input format: {"instruction": str, "input": str, "output": str}
        """
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")

        # Combine instruction and input for user message
        user_content = instruction
        if input_text:
            user_content = f"{instruction}\n\n{input_text}"

        # Apply Qwen chat template
        text = (
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['system']}\n"
            f"{self.DEFAULT_SYSTEM_PROMPT}{self.CHAT_TEMPLATE['im_end']}\n"
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['user']}\n"
            f"{user_content}{self.CHAT_TEMPLATE['im_end']}\n"
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['assistant']}\n"
            f"{output}{self.CHAT_TEMPLATE['im_end']}"
        )

        return text

    def _format_chat(self, example: Dict[str, Any]) -> str:
        """
        Format example as chat format with Qwen chat template.

        Input format: {"messages": [{"role": str, "content": str}, ...]}
        """
        messages = example.get("messages", [])
        if not messages:
            return ""

        parts = []
        has_system = any(m.get("role") == "system" for m in messages)

        # Add default system prompt if not present
        if not has_system:
            parts.append(
                f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['system']}\n"
                f"{self.DEFAULT_SYSTEM_PROMPT}{self.CHAT_TEMPLATE['im_end']}"
            )

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(
                f"{self.CHAT_TEMPLATE['im_start']}{role}\n"
                f"{content}{self.CHAT_TEMPLATE['im_end']}"
            )

        return "\n".join(parts)

    def _format_dpo(self, example: Dict[str, Any]) -> Tuple[str, str]:
        """
        Format example for DPO (Direct Preference Optimization).

        Input format: {"prompt": str, "chosen": str, "rejected": str}

        Returns:
            Tuple of (chosen_text, rejected_text)
        """
        prompt = example.get("prompt", "")
        chosen = example.get("chosen", "")
        rejected = example.get("rejected", "")

        # Format with chat template
        prompt_formatted = (
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['system']}\n"
            f"{self.DEFAULT_SYSTEM_PROMPT}{self.CHAT_TEMPLATE['im_end']}\n"
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['user']}\n"
            f"{prompt}{self.CHAT_TEMPLATE['im_end']}\n"
            f"{self.CHAT_TEMPLATE['im_start']}{self.CHAT_TEMPLATE['assistant']}\n"
        )

        chosen_text = f"{prompt_formatted}{chosen}{self.CHAT_TEMPLATE['im_end']}"
        rejected_text = f"{prompt_formatted}{rejected}{self.CHAT_TEMPLATE['im_end']}"

        return chosen_text, rejected_text

    def _detect_format(self, example: Dict[str, Any]) -> TrainingFormat:
        """
        Detect the format of a raw example.

        Returns:
            Detected TrainingFormat
        """
        if "messages" in example:
            return TrainingFormat.CHAT
        elif "chosen" in example and "rejected" in example:
            return TrainingFormat.DPO
        else:
            return TrainingFormat.INSTRUCTION

    def _truncate_text(self, text: str, max_tokens: int) -> Tuple[str, bool]:
        """
        Truncate text to fit within max tokens.

        Args:
            text: Text to truncate
            max_tokens: Maximum token count

        Returns:
            Tuple of (truncated_text, was_truncated)
        """
        current_tokens = self._estimate_tokens(text)
        if current_tokens <= max_tokens:
            return text, False

        # Binary search for truncation point
        if self._tokenizer is not None:
            tokens = self._tokenizer.encode(text, add_special_tokens=False)
            truncated_tokens = tokens[:max_tokens]
            truncated_text = self._tokenizer.decode(truncated_tokens)
        else:
            # Character-based truncation
            target_chars = max_tokens * 4  # Approximate
            truncated_text = text[:target_chars]

        return truncated_text, True

    def prepare_for_training(
        self,
        target_format: Optional[TrainingFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> List[PreparedExample]:
        """
        Convert raw examples to MLX training format.

        Args:
            target_format: Force conversion to specific format (auto-detect if None)
            system_prompt: Override default system prompt

        Returns:
            List of PreparedExample objects
        """
        if not self._raw_data:
            logger.error("No data loaded. Call load_data() first.")
            return []

        if system_prompt:
            self.DEFAULT_SYSTEM_PROMPT = system_prompt

        # Load tokenizer for accurate token counting
        self._load_tokenizer()

        self._prepared_examples = []
        max_seq = self.tokenization_config.max_seq_length

        logger.info(f"Preparing {len(self._raw_data)} examples for training...")

        for idx, example in enumerate(self._raw_data):
            # Detect or use specified format
            fmt = target_format or self._detect_format(example)
            domain = self._detect_domain(example)

            try:
                if fmt == TrainingFormat.INSTRUCTION:
                    text = self._format_instruction(example)
                elif fmt == TrainingFormat.CHAT:
                    text = self._format_chat(example)
                elif fmt == TrainingFormat.DPO:
                    # For DPO, we only use the chosen response for now
                    chosen_text, _ = self._format_dpo(example)
                    text = chosen_text
                else:
                    continue

                if not text:
                    continue

                # Truncate if necessary
                original_tokens = self._estimate_tokens(text)
                text, was_truncated = self._truncate_text(text, max_seq)
                final_tokens = self._estimate_tokens(text)

                # Create prepared example
                prepared = PreparedExample(
                    text=text,
                    token_count=final_tokens,
                    format_type=fmt,
                    domain=domain,
                    source_file=example.get("source_file"),
                    example_id=self._generate_example_id(text),
                    is_truncated=was_truncated,
                    original_length=original_tokens,
                )

                self._prepared_examples.append(prepared)

            except Exception as e:
                logger.warning(f"Error preparing example {idx}: {e}")
                continue

        # Update statistics
        self._update_stats()

        logger.info(f"Prepared {len(self._prepared_examples)} examples")
        logger.info(f"  Truncated: {self._stats.truncated_count}")
        logger.info(f"  Avg tokens: {self._stats.avg_token_count:.1f}")

        return self._prepared_examples

    def _update_stats(self):
        """Update dataset statistics."""
        if not self._prepared_examples:
            return

        token_counts = [e.token_count for e in self._prepared_examples]
        domains = defaultdict(int)
        formats = defaultdict(int)
        truncated = 0

        for ex in self._prepared_examples:
            domains[ex.domain or "unknown"] += 1
            formats[ex.format_type.value] += 1
            if ex.is_truncated:
                truncated += 1

        self._stats = DatasetStats(
            total_examples=len(self._prepared_examples),
            truncated_count=truncated,
            avg_token_count=sum(token_counts) / len(token_counts),
            max_token_count=max(token_counts),
            min_token_count=min(token_counts),
            domains=dict(domains),
            format_counts=dict(formats),
        )

    def split_data(
        self,
        output_dir: Union[str, Path],
        config: Optional[SplitConfig] = None,
    ) -> Dict[str, Path]:
        """
        Split prepared data into train/val/test sets.

        Uses stratified splitting by domain if enabled.

        Args:
            output_dir: Directory to save split JSONL files
            config: Override split configuration

        Returns:
            Dict mapping split names to output file paths
        """
        if not self._prepared_examples:
            logger.error("No prepared examples. Call prepare_for_training() first.")
            return {}

        config = config or self.split_config
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Set random seed for reproducibility
        random.seed(config.random_seed)

        examples = self._prepared_examples.copy()
        if config.shuffle:
            random.shuffle(examples)

        if config.stratify_by_domain:
            # Group by domain
            by_domain: Dict[str, List[PreparedExample]] = defaultdict(list)
            for ex in examples:
                by_domain[ex.domain or "unknown"].append(ex)

            train_data, val_data, test_data = [], [], []

            # Split each domain proportionally
            for domain, domain_examples in by_domain.items():
                n = len(domain_examples)
                train_end = int(n * config.train_ratio)
                val_end = train_end + int(n * config.val_ratio)

                train_data.extend(domain_examples[:train_end])
                val_data.extend(domain_examples[train_end:val_end])
                test_data.extend(domain_examples[val_end:])

            # Shuffle the combined splits
            random.shuffle(train_data)
            random.shuffle(val_data)
            random.shuffle(test_data)

        else:
            # Simple split
            n = len(examples)
            train_end = int(n * config.train_ratio)
            val_end = train_end + int(n * config.val_ratio)

            train_data = examples[:train_end]
            val_data = examples[train_end:val_end]
            test_data = examples[val_end:]

        # Update stats
        self._stats.train_examples = len(train_data)
        self._stats.val_examples = len(val_data)
        self._stats.test_examples = len(test_data)

        # Write output files
        output_files = {}
        splits = {
            "train": train_data,
            "valid": val_data,  # MLX expects "valid" not "val"
            "test": test_data,
        }

        for split_name, split_data in splits.items():
            output_file = output_dir / f"{split_name}.jsonl"

            with open(output_file, "w", encoding="utf-8") as f:
                for ex in split_data:
                    # MLX expects {"text": ...} format
                    f.write(json.dumps({"text": ex.text}) + "\n")

            output_files[split_name] = output_file
            logger.info(f"Wrote {len(split_data)} examples to {output_file}")

        # Save stats/manifest
        manifest = {
            "created": datetime.now().isoformat(),
            "config": {
                "max_seq_length": self.tokenization_config.max_seq_length,
                "model_name": self.tokenization_config.model_name,
                "train_ratio": config.train_ratio,
                "val_ratio": config.val_ratio,
                "test_ratio": config.test_ratio,
                "stratify_by_domain": config.stratify_by_domain,
                "random_seed": config.random_seed,
            },
            "stats": self._stats.to_dict(),
            "files": {k: str(v) for k, v in output_files.items()},
        }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Saved manifest to {manifest_path}")

        return output_files

    def get_stats(self) -> DatasetStats:
        """Get current dataset statistics."""
        return self._stats

    def validate_data(self) -> Dict[str, Any]:
        """
        Validate prepared data for training.

        Checks:
        - Minimum number of examples
        - Token length distribution
        - Format consistency

        Returns:
            Validation report
        """
        report = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "stats": self._stats.to_dict() if self._stats else {},
        }

        if not self._prepared_examples:
            report["valid"] = False
            report["errors"].append("No prepared examples available")
            return report

        # Check minimum count
        min_examples = 50
        if len(self._prepared_examples) < min_examples:
            report["warnings"].append(
                f"Only {len(self._prepared_examples)} examples (recommended: {min_examples}+)"
            )

        # Check for truncation
        if self._stats.truncated_count > len(self._prepared_examples) * 0.5:
            report["warnings"].append(
                f"High truncation rate: {self._stats.truncated_count}/{len(self._prepared_examples)} examples truncated"
            )

        # Check token distribution
        if self._stats.max_token_count - self._stats.min_token_count > 400:
            report["warnings"].append(
                f"Wide token range: {self._stats.min_token_count}-{self._stats.max_token_count}"
            )

        # Check domain balance
        if self._stats.domains:
            max_domain = max(self._stats.domains.values())
            min_domain = min(self._stats.domains.values())
            if max_domain > min_domain * 10:
                report["warnings"].append("Domain imbalance detected")

        return report


def main():
    """CLI interface for training data preparation."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Data Preparation")
    parser.add_argument("input", help="Input directory or JSONL file")
    parser.add_argument("--output", "-o", default=None, help="Output directory")
    parser.add_argument("--max-seq-length", type=int, default=512, help="Maximum sequence length")
    parser.add_argument("--train-ratio", type=float, default=0.90, help="Training split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.05, help="Validation split ratio")
    parser.add_argument("--no-stratify", action="store_true", help="Disable domain stratification")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't split")

    args = parser.parse_args()

    # Configure
    tok_config = TokenizationConfig(max_seq_length=args.max_seq_length)
    split_config = SplitConfig(
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=1.0 - args.train_ratio - args.val_ratio,
        stratify_by_domain=not args.no_stratify,
        random_seed=args.seed,
    )

    # Run pipeline
    prep = TrainingDataPrep(
        tokenization_config=tok_config,
        split_config=split_config,
    )

    print("=" * 60)
    print("SAM Training Data Preparation")
    print("=" * 60)

    # Load data
    count = prep.load_data(args.input)
    if count == 0:
        print("No data found!")
        return 1

    # Prepare
    prep.prepare_for_training()

    # Validate
    report = prep.validate_data()
    print("\nValidation Report:")
    print(f"  Valid: {report['valid']}")
    for warning in report.get("warnings", []):
        print(f"  Warning: {warning}")
    for error in report.get("errors", []):
        print(f"  Error: {error}")

    if args.validate_only:
        return 0

    # Split and save
    output_dir = args.output or Path(args.input).parent / "prepared"
    files = prep.split_data(output_dir)

    print("\nOutput files:")
    for name, path in files.items():
        print(f"  {name}: {path}")

    # Print final stats
    stats = prep.get_stats()
    print("\nFinal Statistics:")
    for key, value in stats.to_dict().items():
        print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    exit(main())
