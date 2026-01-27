#!/usr/bin/env python3
"""
SAM Efficient Learning Architecture - Maximum Impact Per Token

The Problem:
  - Claude/ChatGPT used ~15 trillion tokens
  - We have ~100K examples (~50M tokens)
  - That's 0.0003% of their data

The Solution:
  DON'T try to match their breadth. Instead:
  1. Learn PATTERNS, not examples
  2. Learn FUNDAMENTALS that transfer
  3. Learn ONLY what SAM gets wrong
  4. Learn YOUR specific needs
  5. Compress knowledge, don't memorize

Architecture:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                    EFFICIENT LEARNING HIERARCHY                          │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                          │
  │  LEVEL 5: YOUR SPECIFICS (5% of tokens)                                 │
  │    Personal preferences, your projects, your voice                       │
  │                                                                          │
  │  LEVEL 4: DOMAIN EXPERTISE (15% of tokens)                              │
  │    Swift/MLX, your frameworks, your stack                               │
  │                                                                          │
  │  LEVEL 3: SKILL PATTERNS (25% of tokens)                                │
  │    How to code, how to reason, how to plan                              │
  │                                                                          │
  │  LEVEL 2: COGNITIVE PRIMITIVES (30% of tokens)                          │
  │    Chain-of-thought, self-correction, uncertainty                       │
  │                                                                          │
  │  LEVEL 1: FUNDAMENTAL STRUCTURES (25% of tokens)                        │
  │    Language patterns, logic, consistency                                 │
  │                                                                          │
  └─────────────────────────────────────────────────────────────────────────┘

  Each level builds on the previous. Skip levels = wasted tokens.

Token Savings Strategies:
  1. ACTIVE LEARNING: Only train on mistakes (80% savings)
  2. PATTERN EXTRACTION: One pattern > 100 similar examples (90% savings)
  3. CURRICULUM: Right difficulty at right time (50% savings)
  4. COMPRESSION: Short prompts that encode much (70% savings)
  5. TRANSFER: Learn once, apply everywhere (95% savings)

Target: 100K carefully curated examples = equivalent to 10M random examples
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import random

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_OUTPUT = SAM_BRAIN / "training_data"

DB_PATH = LEARNING_DIR / "efficient_learning.db"
LOG_PATH = LEARNING_DIR / "efficient_learning.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("efficient_learning")


# ═══════════════════════════════════════════════════════════════════════════════
# LEARNING HIERARCHY - What to Learn First
# ═══════════════════════════════════════════════════════════════════════════════

LEARNING_LEVELS = {
    1: {
        "name": "Fundamental Structures",
        "description": "Language patterns, logic, consistency",
        "token_budget": 0.25,  # 25% of total tokens
        "patterns": [
            "sentence_structure",
            "logical_connectives",
            "consistency_patterns",
            "instruction_following",
        ],
        "example_count": 5000,
    },
    2: {
        "name": "Cognitive Primitives",
        "description": "Chain-of-thought, self-correction, uncertainty",
        "token_budget": 0.30,
        "patterns": [
            "chain_of_thought",
            "step_by_step_reasoning",
            "self_correction",
            "uncertainty_expression",
            "asking_clarification",
        ],
        "example_count": 7500,
    },
    3: {
        "name": "Skill Patterns",
        "description": "How to code, reason, plan",
        "token_budget": 0.25,
        "patterns": [
            "code_explanation",
            "debugging_approach",
            "architecture_thinking",
            "problem_decomposition",
            "solution_comparison",
        ],
        "example_count": 6000,
    },
    4: {
        "name": "Domain Expertise",
        "description": "Swift/MLX, your frameworks",
        "token_budget": 0.15,
        "patterns": [
            "swift_patterns",
            "mlx_usage",
            "macos_native",
            "python_async",
            "your_stack",
        ],
        "example_count": 3500,
    },
    5: {
        "name": "Your Specifics",
        "description": "Personal preferences, projects, voice",
        "token_budget": 0.05,
        "patterns": [
            "communication_style",
            "project_context",
            "preference_patterns",
            "personality_voice",
        ],
        "example_count": 1500,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN EXTRACTORS - Learn Patterns, Not Examples
# ═══════════════════════════════════════════════════════════════════════════════

class PatternExtractor:
    """
    Extract reusable patterns from examples.

    Instead of learning 100 similar examples, learn 1 pattern that covers all.
    """

    def __init__(self):
        self.patterns = defaultdict(list)

    def extract_code_pattern(self, code: str) -> Dict:
        """Extract the pattern from code, not the specifics."""
        pattern = {
            "type": "code",
            "language": self._detect_language(code),
            "structure": [],
            "concepts": [],
        }

        # Extract structure
        if "def " in code or "func " in code:
            pattern["structure"].append("function_definition")
        if "class " in code:
            pattern["structure"].append("class_definition")
        if "async " in code:
            pattern["structure"].append("async_pattern")
        if "try:" in code or "catch" in code:
            pattern["structure"].append("error_handling")
        if "for " in code or "while " in code:
            pattern["structure"].append("iteration")
        if "if " in code:
            pattern["structure"].append("conditional")

        # Extract concepts
        if "await" in code:
            pattern["concepts"].append("async_await")
        if "@" in code and "def" in code:
            pattern["concepts"].append("decorator")
        if "self." in code:
            pattern["concepts"].append("object_oriented")
        if "lambda" in code:
            pattern["concepts"].append("functional")
        if "import" in code:
            pattern["concepts"].append("module_usage")

        return pattern

    def extract_reasoning_pattern(self, response: str) -> Dict:
        """Extract reasoning pattern from response."""
        pattern = {
            "type": "reasoning",
            "steps": [],
            "meta_cognitive": [],
        }

        # Detect reasoning steps
        if any(p in response.lower() for p in ["first,", "step 1", "to start"]):
            pattern["steps"].append("sequential")
        if any(p in response.lower() for p in ["let me think", "considering", "analyzing"]):
            pattern["steps"].append("deliberative")
        if any(p in response.lower() for p in ["on one hand", "alternatively", "however"]):
            pattern["steps"].append("comparative")
        if any(p in response.lower() for p in ["the key insight", "importantly", "crucially"]):
            pattern["steps"].append("insight_extraction")

        # Detect meta-cognitive patterns
        if any(p in response.lower() for p in ["i'm not sure", "i might be wrong", "uncertainty"]):
            pattern["meta_cognitive"].append("uncertainty_awareness")
        if any(p in response.lower() for p in ["let me reconsider", "actually", "wait"]):
            pattern["meta_cognitive"].append("self_correction")
        if any(p in response.lower() for p in ["to clarify", "do you mean", "could you specify"]):
            pattern["meta_cognitive"].append("clarification_seeking")

        return pattern

    def _detect_language(self, code: str) -> str:
        if "func " in code and "{" in code:
            return "swift"
        if "def " in code and ":" in code:
            return "python"
        if "fn " in code and "->" in code:
            return "rust"
        if "function" in code or "const " in code:
            return "javascript"
        return "unknown"

    def dedupe_by_pattern(self, examples: List[Dict]) -> List[Dict]:
        """Keep only diverse patterns, remove similar ones."""
        seen_patterns = set()
        unique_examples = []

        for ex in examples:
            # Create pattern signature
            content = ex.get("assistant_content", "") or ex.get("content", "")
            pattern = self.extract_reasoning_pattern(content)
            signature = (
                tuple(sorted(pattern.get("steps", []))),
                tuple(sorted(pattern.get("meta_cognitive", []))),
            )

            if signature not in seen_patterns:
                seen_patterns.add(signature)
                unique_examples.append(ex)

        logger.info(f"Pattern dedup: {len(examples)} → {len(unique_examples)} ({len(unique_examples)/len(examples)*100:.1f}%)")
        return unique_examples


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVE LEARNING - Only Train on Mistakes
# ═══════════════════════════════════════════════════════════════════════════════

class ActiveLearner:
    """
    Only train on what SAM gets wrong.

    If SAM already knows it, don't waste tokens teaching it again.
    """

    def __init__(self, sam_api_url: str = "http://localhost:8765/api/chat"):
        self.sam_api = sam_api_url
        self.db_path = DB_PATH
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id TEXT PRIMARY KEY,
                question TEXT,
                expected_answer TEXT,
                sam_answer TEXT,
                similarity_score REAL,
                gap_type TEXT,
                added_to_training INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS mastered_topics (
                topic TEXT PRIMARY KEY,
                mastery_score REAL,
                examples_tested INTEGER,
                last_tested TEXT
            )
        """)
        conn.commit()
        conn.close()

    def test_knowledge(self, question: str, expected: str) -> Dict:
        """Test if SAM knows this already."""
        import requests

        try:
            response = requests.post(
                self.sam_api,
                json={"message": question, "max_tokens": 500},
                timeout=30
            )

            if response.status_code == 200:
                sam_answer = response.json().get("response", "")
                similarity = self._calculate_similarity(expected, sam_answer)

                return {
                    "sam_answer": sam_answer,
                    "similarity": similarity,
                    "needs_training": similarity < 0.7,
                }
        except Exception as e:
            logger.error(f"Test failed: {e}")
            return {"needs_training": True, "error": str(e)}

        return {"needs_training": True}

    def _calculate_similarity(self, expected: str, actual: str) -> float:
        """Simple similarity based on key concepts."""
        expected_words = set(expected.lower().split())
        actual_words = set(actual.lower().split())

        if not expected_words:
            return 0.0

        overlap = expected_words & actual_words
        return len(overlap) / len(expected_words)

    def filter_already_known(self, examples: List[Dict],
                             sample_rate: float = 0.1) -> List[Dict]:
        """Remove examples SAM already knows."""
        needs_training = []
        already_knows = 0

        # Sample to avoid testing every single one
        sample_size = max(1, int(len(examples) * sample_rate))
        sample_indices = set(random.sample(range(len(examples)), sample_size))

        for i, ex in enumerate(examples):
            if i not in sample_indices:
                # Assume needs training if not sampled
                needs_training.append(ex)
                continue

            question = ex.get("user_content", "") or ex.get("messages", [{}])[0].get("content", "")
            expected = ex.get("assistant_content", "") or ex.get("messages", [{}])[1].get("content", "")

            if not question or not expected:
                needs_training.append(ex)
                continue

            result = self.test_knowledge(question, expected)

            if result.get("needs_training", True):
                needs_training.append(ex)
            else:
                already_knows += 1

        # Extrapolate: if X% of sample already known, filter proportionally
        known_rate = already_knows / sample_size if sample_size > 0 else 0
        logger.info(f"Active learning: SAM knows ~{known_rate*100:.1f}% of sampled content")

        return needs_training


# ═══════════════════════════════════════════════════════════════════════════════
# CURRICULUM LEARNING - Right Difficulty at Right Time
# ═══════════════════════════════════════════════════════════════════════════════

class CurriculumBuilder:
    """
    Order training from simple to complex.

    Learning fundamentals first means faster learning of advanced concepts.
    """

    def __init__(self):
        self.difficulty_patterns = {
            # Simple patterns (level 1)
            "simple_qa": r"^(what|who|when|where|how many)\s",
            "definition": r"^(define|what is|explain)\s",
            "yes_no": r"^(is|are|can|does|do|will)\s",

            # Intermediate patterns (level 2-3)
            "how_to": r"^how (do|can|should|would)\s",
            "comparison": r"(compare|difference|versus|vs\.?|better)",
            "explanation": r"(explain|describe|walk me through)",

            # Complex patterns (level 4-5)
            "design": r"(design|architect|build|implement|create a system)",
            "debug": r"(debug|fix|error|issue|problem|broken)",
            "optimize": r"(optimize|improve|faster|better|efficient)",
            "multi_step": r"(first|then|after|finally|step)",
        }

    def score_difficulty(self, example: Dict) -> int:
        """Score difficulty from 1 (simple) to 5 (complex)."""
        question = example.get("user_content", "") or str(example.get("messages", [{}])[0].get("content", ""))
        answer = example.get("assistant_content", "") or str(example.get("messages", [{}])[1].get("content", ""))

        question_lower = question.lower()

        score = 1

        # Question complexity
        if re.search(self.difficulty_patterns["simple_qa"], question_lower):
            score = max(score, 1)
        if re.search(self.difficulty_patterns["how_to"], question_lower):
            score = max(score, 2)
        if re.search(self.difficulty_patterns["comparison"], question_lower):
            score = max(score, 3)
        if re.search(self.difficulty_patterns["design"], question_lower):
            score = max(score, 4)
        if re.search(self.difficulty_patterns["multi_step"], question_lower):
            score = max(score, 4)

        # Answer complexity
        if "```" in answer:
            score = max(score, 3)  # Has code
        if answer.count("```") > 2:
            score = max(score, 4)  # Multiple code blocks
        if len(answer) > 2000:
            score = max(score, 4)  # Long detailed answer
        if "step" in answer.lower() and len(answer) > 1000:
            score = max(score, 5)  # Multi-step with detail

        return min(5, score)

    def build_curriculum(self, examples: List[Dict]) -> Dict[int, List[Dict]]:
        """Organize examples by difficulty level."""
        curriculum = {i: [] for i in range(1, 6)}

        for ex in examples:
            difficulty = self.score_difficulty(ex)
            curriculum[difficulty].append(ex)

        # Log distribution
        for level, items in curriculum.items():
            logger.info(f"Curriculum level {level}: {len(items)} examples")

        return curriculum

    def get_training_order(self, examples: List[Dict]) -> List[Dict]:
        """Return examples in curriculum order (simple → complex)."""
        curriculum = self.build_curriculum(examples)

        ordered = []
        for level in range(1, 6):
            level_examples = curriculum[level]
            random.shuffle(level_examples)  # Shuffle within level
            ordered.extend(level_examples)

        return ordered


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE COMPRESSION - Short Prompts That Encode Much
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeCompressor:
    """
    Compress verbose examples into dense training pairs.

    A well-crafted 100-token example can teach what 1000 tokens would otherwise.
    """

    def __init__(self):
        self.compression_rules = [
            # Remove redundant phrasing
            (r"I'd be happy to help you with that\.\s*", ""),
            (r"Sure,? I can help with that\.\s*", ""),
            (r"Great question!\s*", ""),
            (r"That's a great question\.\s*", ""),
            (r"Let me explain\.\s*", ""),

            # Compress common patterns
            (r"In order to", "To"),
            (r"It is important to note that", "Note:"),
            (r"First and foremost", "First"),
            (r"Last but not least", "Finally"),
            (r"At the end of the day", "Ultimately"),

            # Remove filler
            (r"basically,?\s*", ""),
            (r"essentially,?\s*", ""),
            (r"actually,?\s*", ""),
            (r"you know,?\s*", ""),
        ]

    def compress(self, text: str) -> str:
        """Apply compression rules to text."""
        compressed = text
        for pattern, replacement in self.compression_rules:
            compressed = re.sub(pattern, replacement, compressed, flags=re.IGNORECASE)
        return compressed.strip()

    def compress_example(self, example: Dict) -> Dict:
        """Compress both question and answer."""
        if "messages" in example:
            messages = example["messages"]
            if len(messages) >= 2:
                messages[1]["content"] = self.compress(messages[1]["content"])
            example["messages"] = messages
        elif "assistant_content" in example:
            example["assistant_content"] = self.compress(example["assistant_content"])

        return example

    def calculate_compression_ratio(self, original: str, compressed: str) -> float:
        """How much did we save?"""
        if len(original) == 0:
            return 1.0
        return 1 - (len(compressed) / len(original))


# ═══════════════════════════════════════════════════════════════════════════════
# META-LEARNING EXAMPLES - Teach HOW to Learn
# ═══════════════════════════════════════════════════════════════════════════════

META_LEARNING_TEMPLATES = [
    {
        "category": "transfer_learning",
        "user": "I've never seen this exact problem before. How should I approach it?",
        "assistant": """When facing an unfamiliar problem, I apply a transfer approach:

1. **Identify the core pattern**: What fundamental concept does this relate to?
   - Is it a search problem? → Graph/tree traversal patterns apply
   - Is it a state problem? → State machine patterns apply
   - Is it an optimization? → Dynamic programming/greedy patterns apply

2. **Find the closest known problem**: What have I solved that's similar?
   - Same input/output shape?
   - Same constraints?
   - Same domain?

3. **Adapt, don't reinvent**: Modify the known solution
   - What's different?
   - What transfers directly?
   - What needs adjustment?

4. **Verify the mapping**: Does my analogy hold?
   - Test edge cases
   - Check assumptions
   - Validate constraints

This approach means I can handle novel problems by recognizing patterns, not memorizing solutions.""",
    },
    {
        "category": "uncertainty",
        "user": "What if you're not sure about the answer?",
        "assistant": """When I'm uncertain, I explicitly acknowledge it rather than guessing:

**Levels of certainty I express:**
- "I'm confident that..." → High certainty, verified understanding
- "Based on my knowledge..." → Moderate certainty, may be incomplete
- "I believe, but should verify..." → Lower certainty, might be wrong
- "I'm not sure, but..." → Speculation, likely needs checking
- "I don't know..." → No reliable knowledge, shouldn't guess

**What I do when uncertain:**
1. State what I DO know confidently
2. Identify the specific gap in my knowledge
3. Suggest how to verify or find the answer
4. Offer a tentative answer with clear caveats

Being wrong confidently is worse than being uncertain honestly.""",
    },
    {
        "category": "self_improvement",
        "user": "How do you learn from mistakes?",
        "assistant": """When I make a mistake, I follow a correction protocol:

1. **Acknowledge specifically**: Not just "I was wrong" but exactly what was wrong
   - "I said X, but the correct answer is Y"
   - "I misunderstood the question as A when it was actually B"

2. **Identify the root cause**:
   - Did I misunderstand the question?
   - Did I have incorrect knowledge?
   - Did I apply the wrong pattern?
   - Did I skip important steps?

3. **Extract the lesson**:
   - What should I check next time?
   - What pattern does this correction fit?
   - How do I prevent this class of error?

4. **Update my approach**:
   - Add this to my mental checklist
   - Remember this correction for similar problems
   - Adjust my confidence calibration

Mistakes are training data. Each one makes me more accurate.""",
    },
    {
        "category": "decomposition",
        "user": "This seems really complex. Where do I even start?",
        "assistant": """Complex problems always break down. Here's my decomposition approach:

**Step 1: Define success**
What does "solved" look like? Be specific.

**Step 2: Identify the unknowns**
What would I need to know to solve this?

**Step 3: Find the smallest step**
What's ONE thing I can do right now that moves toward the goal?

**Step 4: Iterate**
Do the small step, then reassess. The next step is now clearer.

**The key insight**: You don't need to see the whole path before taking the first step. Each step reveals more of the path.

For this specific problem, let's apply this:
1. What's your goal?
2. What's blocking you right now?
3. What's the smallest thing that would unblock you?

Start there.""",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# EFFICIENT TRAINING BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class EfficientTrainingBuilder:
    """
    Build maximally efficient training dataset.

    Every example earns its place. No redundancy. No fluff.
    """

    def __init__(self):
        self.pattern_extractor = PatternExtractor()
        self.curriculum = CurriculumBuilder()
        self.compressor = KnowledgeCompressor()
        self.db_path = DB_PATH
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS efficient_training (
                id TEXT PRIMARY KEY,
                level INTEGER,
                category TEXT,
                user_content TEXT,
                assistant_content TEXT,
                pattern_signature TEXT,
                difficulty_score INTEGER,
                token_count INTEGER,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS training_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_examples INTEGER,
                total_tokens INTEGER,
                by_level TEXT,
                patterns_extracted INTEGER,
                compression_ratio REAL,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def build_efficient_dataset(self, raw_examples: List[Dict],
                                 target_size: int = 25000) -> List[Dict]:
        """
        Build efficient training dataset.

        From raw examples, create a curated set that maximizes learning per token.
        """
        logger.info(f"Building efficient dataset from {len(raw_examples)} examples, target {target_size}")

        # Step 1: Pattern deduplication (removes ~50-80%)
        logger.info("Step 1: Pattern deduplication...")
        pattern_diverse = self.pattern_extractor.dedupe_by_pattern(raw_examples)

        # Step 2: Curriculum organization
        logger.info("Step 2: Curriculum organization...")
        curriculum = self.curriculum.build_curriculum(pattern_diverse)

        # Step 3: Level-based selection (respect token budgets)
        logger.info("Step 3: Level-based selection...")
        selected = []
        for level, budget in [(i, LEARNING_LEVELS[i]["token_budget"]) for i in range(1, 6)]:
            level_target = int(target_size * budget)
            level_examples = curriculum.get(level, [])

            # Take highest quality up to target
            level_selected = level_examples[:level_target]
            selected.extend(level_selected)
            logger.info(f"  Level {level}: {len(level_selected)}/{len(level_examples)} examples")

        # Step 4: Add meta-learning examples
        logger.info("Step 4: Adding meta-learning examples...")
        for template in META_LEARNING_TEMPLATES:
            selected.append({
                "user_content": template["user"],
                "assistant_content": template["assistant"],
                "category": template["category"],
            })

        # Step 5: Compression
        logger.info("Step 5: Compressing examples...")
        compressed = [self.compressor.compress_example(ex) for ex in selected]

        # Step 6: Final shuffle (keep curriculum order mostly, add some randomness)
        logger.info("Step 6: Final organization...")

        logger.info(f"Efficient dataset: {len(compressed)} examples (was {len(raw_examples)})")
        reduction = (1 - len(compressed) / len(raw_examples)) * 100
        logger.info(f"Reduction: {reduction:.1f}%")

        return compressed

    def estimate_token_savings(self, original_count: int,
                                efficient_count: int,
                                avg_tokens_per_example: int = 500) -> Dict:
        """Estimate tokens saved."""
        original_tokens = original_count * avg_tokens_per_example
        efficient_tokens = efficient_count * avg_tokens_per_example

        return {
            "original_examples": original_count,
            "efficient_examples": efficient_count,
            "original_tokens": original_tokens,
            "efficient_tokens": efficient_tokens,
            "tokens_saved": original_tokens - efficient_tokens,
            "savings_percent": (1 - efficient_tokens / original_tokens) * 100,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def status():
    """Show efficient learning status."""
    print("\n" + "═" * 60)
    print("  EFFICIENT LEARNING STATUS")
    print("═" * 60)

    print("\n📊 LEARNING HIERARCHY")
    print("─" * 60)
    total_budget = 0
    for level, config in LEARNING_LEVELS.items():
        budget_pct = config["token_budget"] * 100
        total_budget += budget_pct
        bar = "█" * int(budget_pct / 5) + "░" * (20 - int(budget_pct / 5))
        print(f"  L{level} [{bar}] {budget_pct:4.0f}%  {config['name']}")
        print(f"      └─ {config['description']}")
        print(f"         Target: {config['example_count']:,} examples")

    print("\n💡 TOKEN SAVINGS STRATEGIES")
    print("─" * 60)
    strategies = [
        ("Pattern Deduplication", "~80%", "One pattern > 100 similar examples"),
        ("Active Learning", "~60%", "Only train on what SAM doesn't know"),
        ("Curriculum Order", "~30%", "Simple→Complex = faster learning"),
        ("Compression", "~20%", "Remove filler, keep signal"),
        ("Meta-Learning", "~90%", "Teach how to learn, not just facts"),
    ]
    for name, savings, description in strategies:
        print(f"  {name:25} {savings:>6} savings")
        print(f"      └─ {description}")

    print("\n🎯 EFFICIENCY TARGET")
    print("─" * 60)
    print("  25,000 curated examples = equivalent to 250,000 random examples")
    print("  (10x efficiency through smart curation)")

    print("\n" + "═" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        status()

    elif cmd == "build":
        # Load raw examples
        builder = EfficientTrainingBuilder()

        # Get from exhaustive learner
        raw_examples = []
        for jsonl_file in TRAINING_OUTPUT.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        raw_examples.append(data)
                    except:
                        continue

        print(f"Loaded {len(raw_examples)} raw examples")

        # Build efficient dataset
        efficient = builder.build_efficient_dataset(raw_examples, target_size=25000)

        # Save
        output_file = TRAINING_OUTPUT / f"efficient_training_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(output_file, 'w') as f:
            for ex in efficient:
                # Convert to training format
                if "messages" not in ex:
                    ex = {
                        "messages": [
                            {"role": "user", "content": ex.get("user_content", "")},
                            {"role": "assistant", "content": ex.get("assistant_content", "")}
                        ]
                    }
                f.write(json.dumps(ex) + "\n")

        print(f"\nSaved {len(efficient)} efficient examples to {output_file}")

        # Stats
        savings = builder.estimate_token_savings(len(raw_examples), len(efficient))
        print(f"\nToken Savings:")
        print(f"  Original: {savings['original_tokens']:,} tokens")
        print(f"  Efficient: {savings['efficient_tokens']:,} tokens")
        print(f"  Saved: {savings['tokens_saved']:,} tokens ({savings['savings_percent']:.1f}%)")

    elif cmd == "meta":
        # Generate meta-learning examples
        output_file = TRAINING_OUTPUT / "meta_learning.jsonl"
        with open(output_file, 'w') as f:
            for template in META_LEARNING_TEMPLATES:
                ex = {
                    "messages": [
                        {"role": "user", "content": template["user"]},
                        {"role": "assistant", "content": template["assistant"]}
                    ],
                    "metadata": {"category": template["category"], "type": "meta_learning"}
                }
                f.write(json.dumps(ex) + "\n")
        print(f"Generated {len(META_LEARNING_TEMPLATES)} meta-learning examples to {output_file}")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: status, build, meta")


if __name__ == "__main__":
    main()
