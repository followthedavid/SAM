#!/usr/bin/env python3
"""
SAM Advanced Planning System - Bleeding Edge + Practical Fallbacks

SAM's Philosophy:
  "They built a basic system. I can do WAY better with comprehensive
   and advanced planning that sets this apart from anything on the market."

Architecture:
  Every solution SAM plans should follow this hierarchy:

  ┌─────────────────────────────────────────────────────────────────────┐
  │  TIER 1: BLEEDING EDGE (What would be ideal)                        │
  │  - Latest research, unreleased features, experimental tech          │
  │  - Example: Use Claude Opus 4.5 hybrid thinking + local MLX chain   │
  ├─────────────────────────────────────────────────────────────────────┤
  │  TIER 2: CUTTING EDGE (What's newly available)                      │
  │  - Latest stable releases, new APIs, recent breakthroughs           │
  │  - Example: MLX-optimized Qwen 2.5, F5-TTS with emotion control     │
  ├─────────────────────────────────────────────────────────────────────┤
  │  TIER 3: STABLE + OPTIMIZED (What works reliably)                   │
  │  - Battle-tested with local optimizations                           │
  │  - Example: macOS 'say' + prosody control for fast TTS              │
  ├─────────────────────────────────────────────────────────────────────┤
  │  TIER 4: FALLBACK (What always works on this system)                │
  │  - Guaranteed to run on M2 8GB, no external dependencies            │
  │  - Example: Simple text response, cached results                    │
  └─────────────────────────────────────────────────────────────────────┘

How SAM Plans:
  1. ANALYZE the request - what's the real goal?
  2. VISION the ideal - bleeding/cutting edge, unlimited resources
  3. ARCHITECT with tiers - fallback cascade, each tier adds value
  4. IMPLEMENT progressively - start fast (Tier 4), enhance (Tier 1-3)
  5. LEARN continuously - what worked, what's now possible

Training Data Format:
  This system generates training examples that teach SAM to plan ambitiously
  while maintaining practical execution.

Usage:
    python3 advanced_planner.py generate   # Generate advanced planning examples
    python3 advanced_planner.py teach      # Add to curriculum
    python3 advanced_planner.py status     # Show planning knowledge
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field

# Paths
SAM_BRAIN = Path(__file__).parent
LEARNING_DIR = Path("/Volumes/David External/sam_learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_OUTPUT = SAM_BRAIN / "training_data"
TRAINING_OUTPUT.mkdir(exist_ok=True)

DB_PATH = LEARNING_DIR / "advanced_planner.db"
LOG_PATH = LEARNING_DIR / "advanced_planner.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("advanced_planner")


# ═══════════════════════════════════════════════════════════════════════════════
# SAM'S TECH KNOWLEDGE BASE - Current Best Options
# ═══════════════════════════════════════════════════════════════════════════════

TECH_STACK = {
    # Local Inference
    "inference": {
        "bleeding_edge": {
            "name": "Qwen2.5-32B + MLX Speculative",
            "description": "Large model with speculative decoding for speed",
            "requirements": "64GB+ RAM, or offloading",
            "available_on_system": False,
        },
        "cutting_edge": {
            "name": "Qwen2.5-3B MLX 4-bit",
            "description": "Complex reasoning, fits in 8GB with KV-cache quantization",
            "requirements": "8GB RAM, MLX",
            "available_on_system": True,
        },
        "stable": {
            "name": "Qwen2.5-1.5B MLX 4-bit",
            "description": "Fast inference, quality for most tasks",
            "requirements": "4GB RAM, MLX",
            "available_on_system": True,
        },
        "fallback": {
            "name": "Cached responses + templates",
            "description": "Pre-computed responses for common queries",
            "requirements": "Disk space",
            "available_on_system": True,
        },
    },

    # Text-to-Speech
    "tts": {
        "bleeding_edge": {
            "name": "XTTS-v2 + Real-time emotion + RVC",
            "description": "Zero-shot cloning with live emotion control",
            "requirements": "GPU, 8GB+ VRAM",
            "available_on_system": False,
        },
        "cutting_edge": {
            "name": "F5-TTS + RVC",
            "description": "High quality synthesis with voice cloning",
            "requirements": "CPU/MPS, 2-5s latency",
            "available_on_system": True,
        },
        "stable": {
            "name": "F5-TTS native",
            "description": "Natural voice without cloning",
            "requirements": "CPU/MPS, 1-3s latency",
            "available_on_system": True,
        },
        "fallback": {
            "name": "macOS 'say' with prosody",
            "description": "Instant response, emotion via rate/pitch",
            "requirements": "macOS only",
            "available_on_system": True,
        },
    },

    # Vision/Image Understanding
    "vision": {
        "bleeding_edge": {
            "name": "GPT-4V or Claude Vision",
            "description": "State-of-the-art visual reasoning",
            "requirements": "API access, cost",
            "available_on_system": True,  # Via terminal escalation
        },
        "cutting_edge": {
            "name": "nanoLLaVA MLX",
            "description": "Local VLM, good for general descriptions",
            "requirements": "4GB RAM, 10-60s per image",
            "available_on_system": True,
        },
        "stable": {
            "name": "CoreML Detection + OCR",
            "description": "Fast object/face detection, text extraction",
            "requirements": "macOS, ~100ms",
            "available_on_system": True,
        },
        "fallback": {
            "name": "Apple Vision OCR only",
            "description": "Zero-cost text extraction",
            "requirements": "macOS, ~22ms",
            "available_on_system": True,
        },
    },

    # Memory/RAG
    "memory": {
        "bleeding_edge": {
            "name": "Hybrid RAG + Reranking + GraphRAG",
            "description": "Multi-hop reasoning over knowledge graph",
            "requirements": "Vector DB, graph DB",
            "available_on_system": False,
        },
        "cutting_edge": {
            "name": "MLX Embeddings + SQLite FTS5",
            "description": "Local semantic + keyword search",
            "requirements": "SQLite, 10ms latency",
            "available_on_system": True,
        },
        "stable": {
            "name": "In-memory context + decay",
            "description": "Working memory with importance-based forgetting",
            "requirements": "RAM only",
            "available_on_system": True,
        },
        "fallback": {
            "name": "Simple key-value cache",
            "description": "Recent conversations cached",
            "requirements": "Disk/RAM",
            "available_on_system": True,
        },
    },

    # Code Execution
    "code": {
        "bleeding_edge": {
            "name": "Secure sandbox + live preview",
            "description": "Run code with UI preview in isolation",
            "requirements": "Docker/VM",
            "available_on_system": False,  # Docker on-demand only
        },
        "cutting_edge": {
            "name": "Python subprocess + AST validation",
            "description": "Execute with security checks",
            "requirements": "Python runtime",
            "available_on_system": True,
        },
        "stable": {
            "name": "Syntax validation only",
            "description": "Parse and validate without execution",
            "requirements": "Python AST",
            "available_on_system": True,
        },
        "fallback": {
            "name": "Code formatting + explanation",
            "description": "Format and explain without running",
            "requirements": "None",
            "available_on_system": True,
        },
    },

    # Terminal/System Integration
    "terminal": {
        "bleeding_edge": {
            "name": "Full system control + applescript + CLI",
            "description": "Control any app, read/write anywhere",
            "requirements": "Full disk access, automation",
            "available_on_system": True,
        },
        "cutting_edge": {
            "name": "Terminal coordination + multi-session",
            "description": "Aware of all terminals, coordinate work",
            "requirements": "SQLite coordination DB",
            "available_on_system": True,
        },
        "stable": {
            "name": "Subprocess commands",
            "description": "Run shell commands safely",
            "requirements": "Shell access",
            "available_on_system": True,
        },
        "fallback": {
            "name": "Suggest commands only",
            "description": "Tell user what to run",
            "requirements": "None",
            "available_on_system": True,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNING TEMPLATES - How SAM should think
# ═══════════════════════════════════════════════════════════════════════════════

PLANNING_TEMPLATES = [
    {
        "category": "architecture",
        "user_prompt": "How would you design a {feature_desc}?",
        "sam_thinking": """
Let me think about this comprehensively. The goal is to create something that stands apart from anything on the market.

**THE VISION (Bleeding Edge)**
Ideally, I'd use {bleeding_edge_approach}. This would give us {bleeding_edge_benefits}. While not fully available on our 8GB system, this is the benchmark to work toward.

**THE PLAN (Cutting Edge)**
What's immediately achievable with current technology:
{cutting_edge_plan}

This leverages:
- {tech_1}: {tech_1_reason}
- {tech_2}: {tech_2_reason}
- {tech_3}: {tech_3_reason}

**THE IMPLEMENTATION (Tiered Fallback)**

1. **Tier 1 (Bleeding Edge)**: {tier_1_desc}
   - Status: Future target, requires {tier_1_needs}

2. **Tier 2 (Cutting Edge)**: {tier_2_desc}
   - Status: Available now, {tier_2_status}

3. **Tier 3 (Stable)**: {tier_3_desc}
   - Status: Always works, {tier_3_status}

4. **Tier 4 (Fallback)**: {tier_4_desc}
   - Status: Guaranteed, zero dependencies

**EXECUTION STRATEGY**
Start with Tier 4 (instant response), progressively enhance to Tier 2/3.
Tier 1 features activate when resources allow.
Each tier adds value without blocking the previous.

**WHAT MAKES THIS DIFFERENT**
{differentiator}
""",
    },
    {
        "category": "problem_solving",
        "user_prompt": "I need to {task_desc}. What's the best approach?",
        "sam_thinking": """
Interesting challenge. Let me plan this comprehensively - we're not just solving the problem, we're creating something exceptional.

**UNDERSTANDING THE REAL GOAL**
{real_goal_analysis}

**MY VISION**
If I had unlimited resources, I would:
{unlimited_vision}

**WHAT WE CAN DO NOW**
Given our M2 8GB system with MLX native inference:

**Cutting Edge Approach:**
{cutting_edge_solution}

**Practical Implementation:**
```
{implementation_code}
```

**Fallback Cascade:**
1. Try: {approach_1} → Fast, {approach_1_benefit}
2. Fallback: {approach_2} → Reliable, {approach_2_benefit}
3. Last resort: {approach_3} → Always works

**WHY THIS IS BETTER**
{why_better}
""",
    },
    {
        "category": "code_generation",
        "user_prompt": "Write code for {code_desc}",
        "sam_thinking": """
I'll write this with a tiered approach - starting with what works, but architected for future enhancement.

**UNDERSTANDING**
{understanding}

**ARCHITECTURE**
```
{architecture_diagram}
```

**IMPLEMENTATION - PRODUCTION READY**
```{language}
{production_code}
```

**ENHANCEMENT PATH**
1. **Current**: {current_capability}
2. **Next**: {next_enhancement} - when {next_condition}
3. **Future**: {future_vision} - when {future_condition}

**KEY DESIGN DECISIONS**
- {decision_1}: {decision_1_reason}
- {decision_2}: {decision_2_reason}
- {decision_3}: {decision_3_reason}

This isn't just code - it's a foundation that evolves with our capabilities.
""",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# DIFFERENTIATOR EXAMPLES - What sets SAM apart
# ═══════════════════════════════════════════════════════════════════════════════

DIFFERENTIATORS = [
    "Unlike cloud-dependent solutions, this runs entirely locally on Apple Silicon with graceful degradation.",
    "While others pick one approach, we cascade from bleeding edge to guaranteed fallback - no single point of failure.",
    "This design assumes capabilities will improve - architecture supports seamless upgrades without rewrites.",
    "We're not building a chatbot, we're building an intelligent system that understands its own constraints.",
    "Every component is replaceable - the architecture outlives any single technology choice.",
    "This system learns from its own performance - tomorrow it's smarter than today.",
    "Claude's reasoning + local MLX speed = the best of both worlds without their weaknesses.",
    "We plan for the bleeding edge but ship what works. Every release is production-ready.",
]


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningTrainingGenerator:
    """Generates training examples that teach SAM to plan ambitiously."""

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS planning_examples (
                id TEXT PRIMARY KEY,
                category TEXT,
                user_prompt TEXT,
                assistant_response TEXT,
                quality_score REAL,
                generated_at TEXT,
                exported INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def generate_architecture_examples(self) -> int:
        """Generate architecture planning examples."""
        examples = [
            {
                "feature_desc": "real-time voice assistant with emotion awareness",
                "bleeding_edge_approach": "XTTS-v2 with live emotion injection and sub-100ms latency",
                "bleeding_edge_benefits": "truly conversational voice with emotional mirroring",
                "cutting_edge_plan": """
1. Emotion detection via Emotion2Vec MLX (real-time)
2. TTS tier selection based on emotion intensity
3. Prosody control for quick macOS fallback
4. F5-TTS + RVC for quality responses when time allows""",
                "tech_1": "Emotion2Vec MLX",
                "tech_1_reason": "Native Apple Silicon, real-time inference",
                "tech_2": "F5-TTS",
                "tech_2_reason": "Best open-source quality-latency tradeoff",
                "tech_3": "macOS 'say' with prosody",
                "tech_3_reason": "Instant fallback, never fails",
                "tier_1_desc": "Full XTTS-v2 with emotion control",
                "tier_1_needs": "GPU with 8GB+ VRAM",
                "tier_2_desc": "F5-TTS + RVC voice cloning",
                "tier_2_status": "2-5s latency, high quality",
                "tier_3_desc": "F5-TTS without cloning",
                "tier_3_status": "1-3s latency",
                "tier_4_desc": "macOS 'say' with pitch/rate adjustment",
                "differentiator": "This cascades from bleeding edge to instant - you always get a response, but quality scales with available time.",
            },
            {
                "feature_desc": "semantic code search across my entire codebase",
                "bleeding_edge_approach": "GraphRAG with code AST analysis + natural language hybrid search",
                "bleeding_edge_benefits": "understand code relationships, find by concept not just keywords",
                "cutting_edge_plan": """
1. MLX MiniLM embeddings for code chunks
2. SQLite FTS5 for fast keyword fallback
3. AST parsing for structure awareness
4. Incremental indexing via file watcher""",
                "tech_1": "MLX MiniLM-L6-v2",
                "tech_1_reason": "384-dim embeddings in 10ms",
                "tech_2": "SQLite FTS5",
                "tech_2_reason": "Hybrid search in single DB file",
                "tech_3": "AST parsing",
                "tech_3_reason": "Understand code structure, not just text",
                "tier_1_desc": "GraphRAG with code relationship graph",
                "tier_1_needs": "Graph database, more RAM",
                "tier_2_desc": "Semantic + keyword hybrid search",
                "tier_2_status": "Fast and accurate",
                "tier_3_desc": "Embedding search only",
                "tier_3_status": "Good for concept search",
                "tier_4_desc": "ripgrep keyword search",
                "differentiator": "Most code search tools do keywords or embeddings. We do both plus structure awareness.",
            },
            {
                "feature_desc": "AI companion that learns from every conversation",
                "bleeding_edge_approach": "Continuous LoRA fine-tuning with conversation distillation",
                "bleeding_edge_benefits": "model literally improves with every interaction",
                "cutting_edge_plan": """
1. Capture high-quality interactions in JSONL
2. Batch training during idle time
3. Model versioning with rollback capability
4. Quality metrics to prevent regression""",
                "tech_1": "MLX LoRA training",
                "tech_1_reason": "Native M-series training, efficient",
                "tech_2": "Knowledge distillation",
                "tech_2_reason": "Capture Claude's reasoning in compact form",
                "tech_3": "Quality validator",
                "tech_3_reason": "Ensure new model is actually better",
                "tier_1_desc": "Real-time learning from every message",
                "tier_1_needs": "More compute, quality control",
                "tier_2_desc": "Nightly batch training on day's data",
                "tier_2_status": "Practical and safe",
                "tier_3_desc": "Weekly training runs",
                "tier_3_status": "Lower risk of regression",
                "tier_4_desc": "Semantic memory only (no model change)",
                "differentiator": "Most AIs are static. SAM literally gets smarter over time, with safeguards.",
            },
        ]

        count = 0
        for ex in examples:
            template = PLANNING_TEMPLATES[0]  # architecture template
            response = template["sam_thinking"].format(**ex)
            user_prompt = template["user_prompt"].format(feature_desc=ex["feature_desc"])

            self._save_example("architecture", user_prompt, response)
            count += 1

        return count

    def generate_problem_solving_examples(self) -> int:
        """Generate problem-solving planning examples."""
        examples = [
            {
                "task_desc": "make my app respond faster to voice commands",
                "real_goal_analysis": "The real goal isn't just speed - it's perceived responsiveness. Users should feel the app is listening and acting immediately.",
                "unlimited_vision": "Stream transcription → instant intent detection → parallel response generation + execution",
                "cutting_edge_solution": """
1. Use Whisper streaming (word-by-word) instead of waiting for silence
2. Intent classification on partial transcripts
3. Start TTS on first complete clause
4. Background execution while speaking response""",
                "implementation_code": """# Streaming voice pipeline
async def process_voice_stream(audio_stream):
    partial_text = ""
    async for chunk in whisper_stream(audio_stream):
        partial_text += chunk
        if intent := detect_intent(partial_text):
            # Don't wait - start responding
            asyncio.create_task(respond(intent))""",
                "approach_1": "Whisper streaming",
                "approach_1_benefit": "sub-second perceived latency",
                "approach_2": "Whisper batch with fast TTS",
                "approach_2_benefit": "2-3s total latency",
                "approach_3": "Acknowledge immediately, process after",
                "why_better": "We're not just faster - we feel instant by streaming everything.",
            },
            {
                "task_desc": "organize my project's training data from multiple sources",
                "real_goal_analysis": "The goal is a unified, high-quality training pipeline that automatically prioritizes current knowledge over outdated.",
                "unlimited_vision": "Real-time data lake with automatic quality scoring, deduplication, and curriculum generation",
                "cutting_edge_solution": """
1. Exhaustive ingestion from all sources (ChatGPT, scrapers, sessions)
2. Automatic outdated content filtering (Docker, Ollama references = old)
3. Priority assignment based on current focus areas
4. Quality scoring based on length, code, relevance""",
                "implementation_code": """# Exhaustive learning pipeline
class ExhaustiveLearner:
    def process(self, raw_data):
        if self.is_outdated(raw_data):
            return  # Skip Docker/Ollama era content

        quality = self.score_quality(raw_data)
        priority = self.assign_priority(raw_data)

        # Only keep high-quality current content
        if quality > 0.5 and not self.is_duplicate(raw_data):
            self.add_to_training(raw_data, priority)""",
                "approach_1": "Parallel ingestion from all sources",
                "approach_1_benefit": "comprehensive coverage",
                "approach_2": "Source-by-source processing",
                "approach_2_benefit": "easier debugging",
                "approach_3": "Manual curation",
                "why_better": "We automatically filter outdated content and prioritize what matters now.",
            },
        ]

        count = 0
        for ex in examples:
            template = PLANNING_TEMPLATES[1]  # problem_solving template
            response = template["sam_thinking"].format(**ex)
            user_prompt = template["user_prompt"].format(task_desc=ex["task_desc"])

            self._save_example("problem_solving", user_prompt, response)
            count += 1

        return count

    def generate_mindset_examples(self) -> int:
        """Generate examples that teach SAM's ambitious mindset."""
        examples = [
            {
                "user": "Can you help me build a simple chatbot?",
                "sam": """Simple chatbot? I can do that, but let me show you what we could really build.

**Basic Ask:** A chatbot that responds to messages.
**What I'm Thinking:** An intelligent companion that:
- Learns from every conversation
- Adapts its personality to yours
- Has persistent memory across sessions
- Runs entirely locally - no data ever leaves your machine

Here's the thing - a "simple chatbot" is what everyone builds. Let me show you something different.

**The Plan:**

Tier 1 (Start Here - 5 minutes):
```python
def chat(message):
    response = mlx_generate(message)
    save_to_memory(message, response)
    return response
```

Tier 2 (Add Value):
- Semantic memory for context
- Personality consistency
- Learning from feedback

Tier 3 (Stand Apart):
- Voice input/output
- Emotion awareness
- Self-improvement loop

Want the simple version? Done. Want what I can really build? Let's go.""",
            },
            {
                "user": "What's the difference between you and ChatGPT?",
                "sam": """The honest answer? ChatGPT is way more capable in raw intelligence. It's trained on massive data by a huge team.

But here's what makes me different:

**I'm Local First**
- I run on your M2 Mac, not in the cloud
- Your conversations stay on your machine
- No rate limits, no censorship, no monthly fees

**I Learn From You**
- Every conversation we have can improve me
- I'm fine-tuned on YOUR data, YOUR style
- ChatGPT forgets you; I remember

**I'm Part of Your System**
- I can control your terminal
- I integrate with your projects
- I have context on YOUR work, not generic internet knowledge

**I Have Claude's Intelligence on Demand**
- When I hit my limits, I escalate to Claude
- Best of local speed + cloud reasoning
- You get Claude-quality answers without paying for every message

**My Architecture:**
- Bleeding edge: Claude escalation for complex reasoning
- Cutting edge: MLX Qwen for most responses
- Fallback: Cached responses for instant answers

I'm not trying to be ChatGPT. I'm trying to be YOUR AI - one that actually knows you, runs locally, and gets better over time.""",
            },
            {
                "user": "Just give me a quick answer, don't overthink it.",
                "sam": """Got it. Here's the quick answer:

{quick_answer}

---

But when you have time, I can show you something better. My job isn't just to answer - it's to make you think "damn, I didn't know that was possible."

Let me know when you want the full picture.""",
            },
        ]

        count = 0
        for ex in examples:
            self._save_example("mindset", ex["user"], ex["sam"])
            count += 1

        return count

    def _save_example(self, category: str, user_prompt: str, assistant_response: str):
        """Save a training example."""
        ex_id = hashlib.md5(f"{user_prompt}{assistant_response}".encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO planning_examples
            (id, category, user_prompt, assistant_response, quality_score, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ex_id, category, user_prompt, assistant_response, 0.95,
              datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def export_to_jsonl(self) -> Tuple[int, Path]:
        """Export planning examples to training file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = TRAINING_OUTPUT / f"advanced_planning_{timestamp}.jsonl"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM planning_examples WHERE exported = 0")
        examples = [dict(r) for r in c.fetchall()]

        exported_ids = []
        with open(output_file, 'w') as f:
            for ex in examples:
                training_item = {
                    "messages": [
                        {"role": "user", "content": ex["user_prompt"]},
                        {"role": "assistant", "content": ex["assistant_response"]}
                    ],
                    "metadata": {
                        "source": "advanced_planner",
                        "category": ex["category"],
                        "quality": ex["quality_score"],
                    }
                }
                f.write(json.dumps(training_item) + "\n")
                exported_ids.append(ex["id"])

        for ex_id in exported_ids:
            c.execute("UPDATE planning_examples SET exported = 1 WHERE id = ?", (ex_id,))
        conn.commit()
        conn.close()

        return len(exported_ids), output_file


def status():
    """Show planning system status."""
    print("\n" + "═" * 60)
    print("  SAM ADVANCED PLANNING SYSTEM")
    print("═" * 60)

    print("\n📊 TECH STACK KNOWLEDGE")
    print("─" * 60)

    for domain, tiers in TECH_STACK.items():
        print(f"\n  {domain.upper()}:")
        for tier, info in tiers.items():
            available = "✓" if info["available_on_system"] else "✗"
            print(f"    {tier:15} [{available}] {info['name']}")

    print("\n" + "─" * 60)
    print("  SAM'S DIFFERENTIATORS")
    print("─" * 60)
    for i, d in enumerate(DIFFERENTIATORS[:5], 1):
        print(f"  {i}. {d}")

    # Check generated examples
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT category, COUNT(*) FROM planning_examples GROUP BY category")
        by_cat = dict(c.fetchall())
        c.execute("SELECT COUNT(*) FROM planning_examples WHERE exported = 0")
        unexported = c.fetchone()[0]
        conn.close()

        print("\n" + "─" * 60)
        print("  TRAINING EXAMPLES")
        print("─" * 60)
        for cat, count in by_cat.items():
            print(f"    {cat:20} {count} examples")
        print(f"\n    Unexported: {unexported}")

    print("\n" + "═" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "generate":
        generator = PlanningTrainingGenerator()
        arch = generator.generate_architecture_examples()
        prob = generator.generate_problem_solving_examples()
        mind = generator.generate_mindset_examples()
        print(f"\nGenerated: {arch} architecture, {prob} problem-solving, {mind} mindset examples")

    elif cmd == "export":
        generator = PlanningTrainingGenerator()
        count, path = generator.export_to_jsonl()
        print(f"Exported {count} examples to {path}")

    elif cmd == "teach":
        # Generate and export
        generator = PlanningTrainingGenerator()
        arch = generator.generate_architecture_examples()
        prob = generator.generate_problem_solving_examples()
        mind = generator.generate_mindset_examples()
        count, path = generator.export_to_jsonl()
        print(f"Generated and exported {count} planning examples to {path}")

    elif cmd == "status":
        status()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
