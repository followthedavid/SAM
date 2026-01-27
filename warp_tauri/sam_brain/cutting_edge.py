#!/usr/bin/env python3
"""
SAM Cutting Edge Module

Philosophy:
- Enterprise-grade, personal use
- Cutting edge first, simple fallback second
- Democratization of upper-level software
- Reverse engineering arsenal
- Continuous evolution from industry trends

Constraints:
- 8GB Mac Mini M2
- Must be smart about what runs locally vs. what needs help

This module:
1. Monitors software developments
2. Reverse engineers interesting patterns
3. Assesses feasibility for our hardware
4. Implements with fallback strategies
5. Sources data and patterns from the web
"""

import json
import time
import hashlib
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════════════════

HARDWARE_PROFILE = {
    "ram_gb": 8,
    "chip": "M2",
    "neural_engine": True,
    "gpu_cores": 8,
    "max_model_size_gb": 4.5,  # Leave headroom for OS + apps
    "max_concurrent_models": 1,
    "can_run_locally": [
        "llm_under_5gb",
        "embedding_models",
        "whisper_small",
        "stable_diffusion_turbo",  # With optimizations
        "sqlite_fts",
        "vector_search_faiss",
    ],
    "needs_cloud_or_queue": [
        "llm_over_5gb",
        "video_generation",
        "large_batch_processing",
        "real_time_training",
    ]
}


class Approach(Enum):
    """Implementation approach levels"""
    CUTTING_EDGE = "cutting_edge"      # Latest, most advanced
    MODERN = "modern"                   # Current best practices
    STABLE = "stable"                   # Proven, reliable
    FALLBACK = "fallback"               # Simple backup


class Feasibility(Enum):
    """Can we run this on 8GB M2?"""
    NATIVE = "native"                   # Runs great locally
    OPTIMIZED = "optimized"             # Runs with optimizations
    HYBRID = "hybrid"                   # Part local, part cloud
    QUEUED = "queued"                   # Queue for external processing
    IMPOSSIBLE = "impossible"           # Can't do this


@dataclass
class TechApproach:
    """A technology approach with fallback chain"""
    name: str
    category: str  # "llm", "vision", "audio", "data", "ui"

    cutting_edge: Dict  # Latest approach
    modern: Dict        # Current best
    stable: Dict        # Proven reliable
    fallback: Dict      # Simple backup

    feasibility: Feasibility
    notes: str


@dataclass
class DiscoveredPattern:
    """A pattern discovered from reverse engineering or research"""
    id: str
    source: str  # "warp", "cursor", "claude_code", "research", etc.
    name: str
    description: str
    category: str

    implementation_hint: str
    feasibility: Feasibility
    priority: int  # 1=high, 2=medium, 3=low

    discovered_at: str
    implemented: bool = False
    implementation_notes: str = ""


@dataclass
class SoftwareTrend:
    """A trend observed in the software industry"""
    id: str
    name: str
    description: str
    sources: List[str]  # Where we saw this

    relevance_to_sam: str
    implementation_difficulty: str  # "trivial", "small", "medium", "large", "massive"
    feasibility: Feasibility

    first_seen: str
    status: str  # "watching", "researching", "implementing", "implemented", "rejected"


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

APPROACH_LIBRARY = {
    "llm_inference": TechApproach(
        name="LLM Inference",
        category="llm",
        cutting_edge={
            "name": "Speculative Decoding + Quantized",
            "tech": ["llama.cpp with speculative", "4-bit quantization", "flash attention"],
            "why": "Fastest inference possible on limited RAM",
        },
        modern={
            "name": "Ollama with Optimized Models",
            "tech": ["ollama", "GGUF Q4_K_M", "keep_alive"],
            "why": "Best balance of speed and quality",
        },
        stable={
            "name": "Standard Ollama",
            "tech": ["ollama", "default settings"],
            "why": "Just works",
        },
        fallback={
            "name": "Cloud API Queue",
            "tech": ["queue to Claude/GPT", "async processing"],
            "why": "When local can't handle it",
        },
        feasibility=Feasibility.OPTIMIZED,
        notes="8GB limits us to ~4.5GB models. Use Q4 quantization."
    ),

    "embedding": TechApproach(
        name="Text Embeddings",
        category="llm",
        cutting_edge={
            "name": "Nomic Embed + FAISS GPU",
            "tech": ["nomic-embed-text", "faiss-gpu", "batch processing"],
            "why": "Fast semantic search with GPU acceleration",
        },
        modern={
            "name": "Nomic Embed + FAISS CPU",
            "tech": ["nomic-embed-text", "faiss-cpu", "sqlite cache"],
            "why": "Good speed, lower memory",
        },
        stable={
            "name": "Ollama Embeddings + Cosine",
            "tech": ["ollama embeddings", "numpy cosine"],
            "why": "Simple, works everywhere",
        },
        fallback={
            "name": "TF-IDF + BM25",
            "tech": ["scikit-learn", "rank_bm25"],
            "why": "No models needed, pure Python",
        },
        feasibility=Feasibility.NATIVE,
        notes="Embeddings are lightweight. Can run alongside main LLM."
    ),

    "image_generation": TechApproach(
        name="Image Generation",
        category="vision",
        cutting_edge={
            "name": "SDXL Turbo + LoRA",
            "tech": ["sdxl-turbo", "custom lora", "4-step generation"],
            "why": "Fast, high quality, consistent characters",
        },
        modern={
            "name": "SD 1.5 Optimized",
            "tech": ["stable-diffusion-1.5", "attention slicing", "vae tiling"],
            "why": "Lower VRAM, still good quality",
        },
        stable={
            "name": "ComfyUI API",
            "tech": ["comfyui", "api mode", "queue system"],
            "why": "Offload to dedicated process",
        },
        fallback={
            "name": "Cloud API",
            "tech": ["replicate", "stability.ai", "queue"],
            "why": "When local GPU can't handle it",
        },
        feasibility=Feasibility.OPTIMIZED,
        notes="8GB unified memory helps. Use attention slicing."
    ),

    "voice_synthesis": TechApproach(
        name="Voice Synthesis",
        category="audio",
        cutting_edge={
            "name": "RVC + Real-time",
            "tech": ["rvc-project", "real-time conversion", "custom voice"],
            "why": "Clone any voice in real-time",
        },
        modern={
            "name": "Coqui TTS + RVC Post",
            "tech": ["coqui-tts", "rvc post-processing"],
            "why": "Good quality, reasonable speed",
        },
        stable={
            "name": "Piper TTS",
            "tech": ["piper-tts", "pre-trained voices"],
            "why": "Fast, low memory, good enough",
        },
        fallback={
            "name": "System TTS",
            "tech": ["macOS say", "espeak"],
            "why": "Always available",
        },
        feasibility=Feasibility.HYBRID,
        notes="RVC needs GPU. Consider pre-generating common phrases."
    ),

    "data_sourcing": TechApproach(
        name="Data Sourcing",
        category="data",
        cutting_edge={
            "name": "Intelligent Scraping + LLM Extract",
            "tech": ["playwright", "readability", "llm extraction", "structured output"],
            "why": "Understand and extract meaning from any page",
        },
        modern={
            "name": "Targeted Scraping + Parsing",
            "tech": ["beautifulsoup", "trafilatura", "json-ld extraction"],
            "why": "Efficient, respects robots.txt",
        },
        stable={
            "name": "API + RSS Feeds",
            "tech": ["official apis", "rss parsing", "webhooks"],
            "why": "Reliable, sanctioned access",
        },
        fallback={
            "name": "Manual + Import",
            "tech": ["manual download", "file import", "clipboard"],
            "why": "Always works",
        },
        feasibility=Feasibility.NATIVE,
        notes="Scraping is CPU-bound. Can run alongside everything."
    ),

    "reverse_engineering": TechApproach(
        name="Reverse Engineering",
        category="research",
        cutting_edge={
            "name": "Dynamic Analysis + Frida",
            "tech": ["frida", "runtime hooks", "api tracing"],
            "why": "See exactly what apps do at runtime",
        },
        modern={
            "name": "Binary Analysis + Network",
            "tech": ["hopper/ghidra", "mitmproxy", "charles"],
            "why": "Understand protocols and structures",
        },
        stable={
            "name": "File Analysis + Observation",
            "tech": ["strings", "file monitoring", "fs_usage"],
            "why": "Low-level but reliable",
        },
        fallback={
            "name": "Documentation + Community",
            "tech": ["official docs", "github issues", "reddit"],
            "why": "Others may have done the work",
        },
        feasibility=Feasibility.NATIVE,
        notes="RE tools are lightweight. The insight is valuable."
    ),

    "ui_framework": TechApproach(
        name="UI Framework",
        category="ui",
        cutting_edge={
            "name": "Tauri + Vue3 + GSAP",
            "tech": ["tauri", "vue3", "gsap", "motion-one"],
            "why": "Native performance, modern animations, small bundle",
        },
        modern={
            "name": "Electron + React",
            "tech": ["electron", "react", "framer-motion"],
            "why": "Large ecosystem, well-documented",
        },
        stable={
            "name": "Web + PWA",
            "tech": ["vanilla js", "pwa", "service workers"],
            "why": "Works everywhere, no install",
        },
        fallback={
            "name": "Terminal UI",
            "tech": ["rich", "textual", "blessed"],
            "why": "No GUI dependencies at all",
        },
        feasibility=Feasibility.NATIVE,
        notes="Tauri is ideal for 8GB - much lighter than Electron."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CUTTING EDGE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class CuttingEdgeMonitor:
    """
    Monitors software developments and identifies patterns to implement.

    Sources:
    - Reverse engineering of tools (Warp, Cursor, Claude Code, etc.)
    - GitHub trending / releases
    - Hacker News / Reddit
    - Research papers (arxiv)
    - Product Hunt / tech blogs
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".sam" / "cutting_edge.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    name TEXT,
                    description TEXT,
                    category TEXT,
                    implementation_hint TEXT,
                    feasibility TEXT,
                    priority INTEGER,
                    discovered_at TEXT,
                    implemented INTEGER DEFAULT 0,
                    implementation_notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trends (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    sources TEXT,
                    relevance TEXT,
                    difficulty TEXT,
                    feasibility TEXT,
                    first_seen TEXT,
                    status TEXT DEFAULT 'watching'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reverse_engineering (
                    id INTEGER PRIMARY KEY,
                    target TEXT,
                    date TEXT,
                    findings TEXT,
                    patterns_extracted TEXT,
                    feasibility_notes TEXT
                )
            """)

    def add_pattern(self, pattern: DiscoveredPattern):
        """Record a discovered pattern"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO patterns
                (id, source, name, description, category, implementation_hint,
                 feasibility, priority, discovered_at, implemented, implementation_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.id, pattern.source, pattern.name, pattern.description,
                pattern.category, pattern.implementation_hint, pattern.feasibility.value,
                pattern.priority, pattern.discovered_at, int(pattern.implemented),
                pattern.implementation_notes
            ))

    def add_trend(self, trend: SoftwareTrend):
        """Record an observed trend"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trends
                (id, name, description, sources, relevance, difficulty,
                 feasibility, first_seen, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trend.id, trend.name, trend.description, json.dumps(trend.sources),
                trend.relevance_to_sam, trend.implementation_difficulty,
                trend.feasibility.value, trend.first_seen, trend.status
            ))

    def record_reverse_engineering(
        self,
        target: str,
        findings: str,
        patterns_extracted: List[str],
        feasibility_notes: str
    ):
        """Record a reverse engineering session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO reverse_engineering
                (target, date, findings, patterns_extracted, feasibility_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                target,
                datetime.now().isoformat(),
                findings,
                json.dumps(patterns_extracted),
                feasibility_notes
            ))

    def get_actionable_patterns(self, limit: int = 10) -> List[Dict]:
        """Get patterns we should implement next"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM patterns
                WHERE implemented = 0
                AND feasibility IN ('native', 'optimized', 'hybrid')
                ORDER BY priority ASC, discovered_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_watching_trends(self) -> List[Dict]:
        """Get trends we're monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM trends
                WHERE status IN ('watching', 'researching')
                ORDER BY first_seen DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def assess_feasibility(self, requirements: Dict) -> Tuple[Feasibility, str]:
        """
        Assess if something can run on our hardware.

        Args:
            requirements: {
                "ram_gb": 2,
                "gpu_required": False,
                "model_size_gb": 1.5,
                "concurrent_with_llm": True,
            }

        Returns:
            (Feasibility, explanation)
        """
        ram_needed = requirements.get("ram_gb", 0)
        model_size = requirements.get("model_size_gb", 0)
        needs_gpu = requirements.get("gpu_required", False)
        concurrent = requirements.get("concurrent_with_llm", False)

        available_ram = HARDWARE_PROFILE["ram_gb"]
        max_model = HARDWARE_PROFILE["max_model_size_gb"]

        # Check model size
        if model_size > max_model:
            return Feasibility.QUEUED, f"Model too large ({model_size}GB > {max_model}GB max)"

        # Check concurrent requirements
        if concurrent and model_size > 2:
            return Feasibility.HYBRID, "Can run but not alongside main LLM"

        # Check total RAM
        if ram_needed > available_ram * 0.6:
            return Feasibility.OPTIMIZED, f"Tight fit, needs optimization ({ram_needed}GB)"

        # Check GPU
        if needs_gpu:
            return Feasibility.OPTIMIZED, "Will use unified memory GPU - may be slow"

        return Feasibility.NATIVE, "Should run well"

    def get_approach(self, category: str) -> Optional[TechApproach]:
        """Get the recommended approach for a category"""
        return APPROACH_LIBRARY.get(category)

    def get_best_feasible(self, category: str) -> Dict:
        """Get the best approach we can actually run"""
        approach = APPROACH_LIBRARY.get(category)
        if not approach:
            return {"error": f"Unknown category: {category}"}

        # Try cutting edge first
        if approach.feasibility in [Feasibility.NATIVE, Feasibility.OPTIMIZED]:
            return {
                "level": "cutting_edge",
                "approach": approach.cutting_edge,
                "feasibility": approach.feasibility.value,
                "notes": approach.notes
            }

        # Fall back through the chain
        if approach.feasibility == Feasibility.HYBRID:
            return {
                "level": "modern",
                "approach": approach.modern,
                "feasibility": "hybrid",
                "notes": "Using modern approach due to hardware limits"
            }

        return {
            "level": "stable",
            "approach": approach.stable,
            "feasibility": "fallback",
            "notes": "Using stable fallback due to hardware constraints"
        }


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWN PATTERNS FROM REVERSE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

KNOWN_PATTERNS = [
    DiscoveredPattern(
        id="warp_thinking_display",
        source="warp",
        name="Live Thinking Display",
        description="Show LLM's reasoning process in real-time with cycling verbs",
        category="ui",
        implementation_hint="Stream tokens, classify into phases, display with animation",
        feasibility=Feasibility.NATIVE,
        priority=1,
        discovered_at="2024-01-01",
        implemented=True,
        implementation_notes="Implemented in live_thinking.py"
    ),
    DiscoveredPattern(
        id="cursor_tab_completion",
        source="cursor",
        name="AI Tab Completion",
        description="Predict next code changes based on context and history",
        category="llm",
        implementation_hint="Small model for fast inference, context window of recent edits",
        feasibility=Feasibility.OPTIMIZED,
        priority=1,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="claude_code_agentic",
        source="claude_code",
        name="Agentic Tool Use",
        description="LLM autonomously uses tools to accomplish multi-step tasks",
        category="llm",
        implementation_hint="Tool definitions, function calling, result parsing loop",
        feasibility=Feasibility.NATIVE,
        priority=1,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="obsidian_graph",
        source="obsidian",
        name="Knowledge Graph Visualization",
        description="Interactive graph of connected notes/concepts",
        category="ui",
        implementation_hint="D3.js force graph, bidirectional links, zoom/pan",
        feasibility=Feasibility.NATIVE,
        priority=2,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="raycast_spotlight",
        source="raycast",
        name="Universal Command Palette",
        description="Fast fuzzy search across all commands and content",
        category="ui",
        implementation_hint="Fuse.js for fuzzy, keyboard navigation, instant preview",
        feasibility=Feasibility.NATIVE,
        priority=2,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="notion_slash_commands",
        source="notion",
        name="Slash Command System",
        description="Type / to get contextual commands",
        category="ui",
        implementation_hint="Input listener, popup menu, command registry",
        feasibility=Feasibility.NATIVE,
        priority=2,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="linear_keyboard_first",
        source="linear",
        name="Keyboard-First UX",
        description="Every action accessible via keyboard shortcuts",
        category="ui",
        implementation_hint="Hotkey registry, vim-like modes, visual hints",
        feasibility=Feasibility.NATIVE,
        priority=2,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
    DiscoveredPattern(
        id="comfyui_node_workflow",
        source="comfyui",
        name="Node-Based Workflow",
        description="Visual programming for complex pipelines",
        category="ui",
        implementation_hint="Vue Flow or React Flow, serializable graphs",
        feasibility=Feasibility.NATIVE,
        priority=3,
        discovered_at="2024-01-01",
        implemented=False,
        implementation_notes=""
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    monitor = CuttingEdgeMonitor()

    # Seed known patterns
    for pattern in KNOWN_PATTERNS:
        monitor.add_pattern(pattern)

    if len(sys.argv) < 2:
        print("SAM Cutting Edge Monitor")
        print("\nEnterprise-grade for personal use. Cutting edge with fallbacks.")
        print("\nUsage:")
        print("  python cutting_edge.py patterns           # Actionable patterns")
        print("  python cutting_edge.py approach <cat>     # Best approach for category")
        print("  python cutting_edge.py assess <json>      # Assess feasibility")
        print("  python cutting_edge.py hardware           # Show hardware profile")
        print("  python cutting_edge.py philosophy         # Show the philosophy")
        print("\nCategories: llm_inference, embedding, image_generation, voice_synthesis,")
        print("            data_sourcing, reverse_engineering, ui_framework")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "patterns":
        patterns = monitor.get_actionable_patterns()
        print("\n🎯 Actionable Patterns (sorted by priority)\n")
        for p in patterns:
            status = "✓" if p["implemented"] else "○"
            print(f"{status} [{p['source']}] {p['name']}")
            print(f"   {p['description']}")
            print(f"   Feasibility: {p['feasibility']} | Priority: {p['priority']}")
            print()

    elif cmd == "approach":
        if len(sys.argv) < 3:
            print("Categories:", ", ".join(APPROACH_LIBRARY.keys()))
            sys.exit(1)

        cat = sys.argv[2]
        result = monitor.get_best_feasible(cat)

        print(f"\n🚀 Best Feasible Approach: {cat}\n")
        print(f"Level: {result.get('level', 'unknown')}")
        print(f"Feasibility: {result.get('feasibility', 'unknown')}")
        print(f"\nApproach: {result.get('approach', {}).get('name', 'N/A')}")
        print(f"Tech: {', '.join(result.get('approach', {}).get('tech', []))}")
        print(f"Why: {result.get('approach', {}).get('why', 'N/A')}")
        print(f"\nNotes: {result.get('notes', 'N/A')}")

    elif cmd == "hardware":
        print("\n💻 Hardware Profile\n")
        for k, v in HARDWARE_PROFILE.items():
            if isinstance(v, list):
                print(f"{k}:")
                for item in v:
                    print(f"  • {item}")
            else:
                print(f"{k}: {v}")

    elif cmd == "philosophy":
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SAM CUTTING EDGE PHILOSOPHY                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. ENTERPRISE-GRADE, PERSONAL USE                                          ║
║     Build like Fortune 500, run on a Mac Mini.                              ║
║     Quality is not negotiable. Scale is optional.                           ║
║                                                                              ║
║  2. CUTTING EDGE FIRST, FALLBACK SECOND                                     ║
║     Try the advanced approach. Have a simple backup.                        ║
║     Never settle for basic when advanced is feasible.                       ║
║                                                                              ║
║  3. DEMOCRATIZATION OF UPPER-LEVEL SOFTWARE                                 ║
║     The patterns that make enterprise software great                        ║
║     should be available to individuals.                                     ║
║                                                                              ║
║  4. ARSENAL OF INTELLIGENCE                                                 ║
║     • Reverse engineering: Learn from the best                              ║
║     • Data sourcing: Gather intelligence from everywhere                    ║
║     • Trend monitoring: Stay on the cutting edge                            ║
║     • Pattern library: Reuse what works                                     ║
║                                                                              ║
║  5. CONSTRAINTS AS FEATURES                                                 ║
║     8GB RAM is not a limitation.                                            ║
║     It's a forcing function for elegant solutions.                          ║
║                                                                              ║
║  6. CONTINUOUS EVOLUTION                                                    ║
║     SAM watches. SAM learns. SAM implements.                                ║
║     Every new tool is a source of patterns.                                 ║
║     Every trend is an opportunity.                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)

    elif cmd == "assess":
        if len(sys.argv) < 3:
            print("Usage: python cutting_edge.py assess '{\"ram_gb\": 2, \"model_size_gb\": 1.5}'")
            sys.exit(1)

        try:
            requirements = json.loads(sys.argv[2])
            feasibility, explanation = monitor.assess_feasibility(requirements)
            print(f"\n⚡ Feasibility Assessment\n")
            print(f"Result: {feasibility.value}")
            print(f"Explanation: {explanation}")
        except json.JSONDecodeError:
            print("Invalid JSON")

    else:
        print(f"Unknown command: {cmd}")
