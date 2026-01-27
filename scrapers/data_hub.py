#!/usr/bin/env python3
"""
SAM Data Hub - Central view of all scraped training data.

Shows:
- All sources with indexed/downloaded counts
- WHY things are incomplete (with context)
- Estimated time to completion
- Training readiness

Usage:
    python3 data_hub.py              # Show full dashboard
    python3 data_hub.py --brief      # Quick summary
    python3 data_hub.py --json       # JSON output
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List

# ANSI colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


@dataclass
class DataSource:
    name: str
    category: str  # coding, roleplay, fashion, other
    db_path: str
    table: str
    count_query: str
    downloaded_query: str
    potential: int  # Estimated total available
    why_incomplete: str  # Explanation of gaps
    priority: int  # 1=highest


# All data sources with context
DATA_SOURCES = [
    # ============ CODING (Priority 1) ============
    DataSource(
        name="Apple Dev (Swift/macOS)",
        category="coding",
        db_path="/Volumes/David External/apple_dev_archive/apple_dev.db",
        table="docs",
        count_query="SELECT (SELECT COUNT(*) FROM docs) + (SELECT COUNT(*) FROM github_code) + (SELECT COUNT(*) FROM stackoverflow)",
        downloaded_query="SELECT (SELECT COUNT(*) FROM docs) + (SELECT COUNT(*) FROM github_code) + (SELECT COUNT(*) FROM stackoverflow)",
        potential=50000,
        why_incomplete="New scraper (started today). Collecting Swift Evolution, WWDC, GitHub repos, StackOverflow. Growing rapidly.",
        priority=1,
    ),
    DataSource(
        name="General Code (GitHub/SO)",
        category="coding",
        db_path="/Volumes/David External/coding_training/code_collection.db",
        table="code_examples",
        count_query="SELECT COUNT(*) FROM code_examples",
        downloaded_query="SELECT COUNT(*) FROM code_examples",
        potential=100000,
        why_incomplete="GitHub rate limits (5000 req/hour). StackOverflow API throttling. Running continuously.",
        priority=1,
    ),

    # ============ ROLEPLAY (Priority 2) ============
    DataSource(
        name="Nifty Archive",
        category="roleplay",
        db_path="/Volumes/David External/nifty_archive/nifty_index.db",
        table="stories",
        count_query="SELECT COUNT(*) FROM stories",
        downloaded_query="SELECT COUNT(*) FROM stories WHERE downloaded=1",
        potential=65000,
        why_incomplete="Fully indexed (64K). Download rate limited to avoid blocks. ~50/batch.",
        priority=2,
    ),
    DataSource(
        name="AO3 (Archive of Our Own)",
        category="roleplay",
        db_path="/Volumes/David External/ao3_archive/ao3_index.db",
        table="works",
        count_query="SELECT COUNT(*) FROM works",
        downloaded_query="SELECT COUNT(*) FROM works WHERE downloaded=1",
        potential=10000000,
        why_incomplete="AO3 has 10M+ works but strict rate limits (5s between requests). Only indexed subset. Very slow.",
        priority=2,
    ),
    DataSource(
        name="Literotica",
        category="roleplay",
        db_path="/Volumes/David External/literotica_archive/literotica_index.db",
        table="stories",
        count_query="SELECT COUNT(*) FROM stories",
        downloaded_query="SELECT COUNT(*) FROM stories WHERE downloaded=1",
        potential=500000,
        why_incomplete="Site has 500K+ stories. Indexer limited to recent/popular. Rate limited.",
        priority=3,
    ),

    # ============ FASHION (Priority 3) ============
    DataSource(
        name="FirstView Photos",
        category="fashion",
        db_path="/Volumes/David External/firstview_archive/firstview_index.db",
        table="photos",
        count_query="SELECT COUNT(*) FROM photos",
        downloaded_query="SELECT COUNT(*) FROM photos WHERE downloaded=1",
        potential=8000000,
        why_incomplete="SEASONS list only covers 2017-2026. Site has photos back to 1990s. Need to expand season range to access 20+ years of archives.",
        priority=3,
    ),
    DataSource(
        name="WWD (Women's Wear Daily)",
        category="fashion",
        db_path="/Volumes/#1/wwd_archive/wwd_index.db",
        table="articles",
        count_query="SELECT COUNT(*) FROM articles",
        downloaded_query="SELECT COUNT(*) FROM articles WHERE downloaded=1",
        potential=500000,
        why_incomplete="Fully indexed (247K articles). Downloading at ~50/batch. Paywall limits some content.",
        priority=3,
    ),
    DataSource(
        name="V Magazine",
        category="fashion",
        db_path="/Volumes/#1/vmag_archive/vmag_index.db",
        table="articles",
        count_query="SELECT COUNT(*) FROM articles",
        downloaded_query="SELECT COUNT(*) FROM articles WHERE downloaded=1",
        potential=15000,
        why_incomplete="Smaller archive. Rate limited. Good progress.",
        priority=4,
    ),
    DataSource(
        name="W Magazine",
        category="fashion",
        db_path="/Volumes/#1/wmag_archive/wmag_index.db",
        table="articles",
        count_query="SELECT COUNT(*) FROM articles",
        downloaded_query="SELECT COUNT(*) FROM articles WHERE downloaded=1",
        potential=40000,
        why_incomplete="Site structure makes deep indexing slow. Working through categories.",
        priority=4,
    ),

    # ============ PARSED/READY ============
    DataSource(
        name="ChatGPT Conversations",
        category="parsed",
        db_path="",  # Not a DB, use file check
        table="",
        count_query="",
        downloaded_query="",
        potential=50000,
        why_incomplete="Fully parsed from OpenAI export. 46K+ examples ready for training.",
        priority=0,
    ),
]


def query_db(db_path: str, query: str) -> int:
    """Run a query and return integer result."""
    if not db_path or not Path(db_path).exists():
        return 0
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query)
        result = c.fetchone()[0]
        conn.close()
        return result or 0
    except Exception as e:
        return 0


def count_jsonl_lines(pattern: str) -> int:
    """Count lines in JSONL files matching pattern."""
    try:
        result = subprocess.run(
            ["bash", "-c", f"cat {pattern} 2>/dev/null | wc -l"],
            capture_output=True, text=True
        )
        return int(result.stdout.strip())
    except:
        return 0


def get_all_stats() -> List[Dict]:
    """Gather stats from all sources."""
    stats = []

    for source in DATA_SOURCES:
        if source.name == "ChatGPT Conversations":
            # Special handling for parsed JSONL files
            indexed = count_jsonl_lines("/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/training_data/*.jsonl")
            downloaded = indexed  # Already processed
        else:
            indexed = query_db(source.db_path, source.count_query)
            downloaded = query_db(source.db_path, source.downloaded_query)

        pct = (downloaded / indexed * 100) if indexed > 0 else 0
        coverage = (indexed / source.potential * 100) if source.potential > 0 else 0

        stats.append({
            "name": source.name,
            "category": source.category,
            "indexed": indexed,
            "downloaded": downloaded,
            "potential": source.potential,
            "pct_downloaded": pct,
            "pct_coverage": coverage,
            "why_incomplete": source.why_incomplete,
            "priority": source.priority,
        })

    return stats


def render_dashboard(stats: List[Dict], brief: bool = False):
    """Render the dashboard to terminal."""
    print()
    print(f"{C.BOLD}╔══════════════════════════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}║                        SAM TRAINING DATA HUB                                 ║{C.RESET}")
    print(f"{C.BOLD}║                        {datetime.now().strftime('%Y-%m-%d %H:%M')}                                       ║{C.RESET}")
    print(f"{C.BOLD}╚══════════════════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # Group by category
    categories = {}
    for s in stats:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    # Category order
    cat_order = ["coding", "roleplay", "fashion", "parsed"]
    cat_colors = {
        "coding": C.GREEN,
        "roleplay": C.MAGENTA,
        "fashion": C.CYAN,
        "parsed": C.YELLOW,
    }

    total_indexed = 0
    total_downloaded = 0
    total_potential = 0

    for cat in cat_order:
        if cat not in categories:
            continue

        color = cat_colors.get(cat, C.RESET)
        print(f"{color}┌─ {cat.upper()} {'─' * (72 - len(cat))}┐{C.RESET}")

        for s in sorted(categories[cat], key=lambda x: x["priority"]):
            total_indexed += s["indexed"]
            total_downloaded += s["downloaded"]
            total_potential += s["potential"]

            # Progress bar
            bar_width = 20
            if s["indexed"] > 0:
                fill = int(s["pct_downloaded"] / 100 * bar_width)
            else:
                fill = 0
            bar = "█" * fill + "░" * (bar_width - fill)

            # Color based on status
            if s["pct_downloaded"] >= 90:
                status_color = C.GREEN
            elif s["pct_downloaded"] >= 25:
                status_color = C.YELLOW
            else:
                status_color = C.RED

            # Format numbers
            def fmt(n):
                if n >= 1_000_000:
                    return f"{n/1_000_000:.1f}M"
                if n >= 1_000:
                    return f"{n/1_000:.1f}K"
                return str(n)

            print(f"{color}│{C.RESET} {s['name'][:28]:<28} {status_color}[{bar}]{C.RESET} {fmt(s['downloaded']):>6}/{fmt(s['indexed']):<6} ({s['pct_downloaded']:5.1f}%)")

            if not brief:
                # Show coverage vs potential
                if s["pct_coverage"] < 100:
                    coverage_note = f"Coverage: {s['pct_coverage']:.1f}% of ~{fmt(s['potential'])} available"
                    print(f"{color}│{C.RESET}   {C.DIM}└─ {coverage_note}{C.RESET}")

                # Show why incomplete (truncated)
                if s["pct_downloaded"] < 95 and s["why_incomplete"]:
                    why = s["why_incomplete"][:70] + "..." if len(s["why_incomplete"]) > 70 else s["why_incomplete"]
                    print(f"{color}│{C.RESET}   {C.DIM}   {why}{C.RESET}")

        print(f"{color}└{'─' * 77}┘{C.RESET}")
        print()

    # Summary
    print(f"{C.BOLD}═══════════════════════════════════════════════════════════════════════════════{C.RESET}")
    print(f"{C.BOLD}TOTALS:{C.RESET}")
    print(f"  Indexed:    {total_indexed:>12,}")
    print(f"  Downloaded: {total_downloaded:>12,}")
    print(f"  Potential:  {total_potential:>12,} (estimated)")
    print()

    # Training readiness
    print(f"{C.BOLD}TRAINING READINESS:{C.RESET}")

    coding_ready = sum(s["downloaded"] for s in stats if s["category"] == "coding")
    roleplay_ready = sum(s["downloaded"] for s in stats if s["category"] == "roleplay")
    fashion_ready = sum(s["downloaded"] for s in stats if s["category"] == "fashion")
    parsed_ready = sum(s["downloaded"] for s in stats if s["category"] == "parsed")

    thresholds = {"coding": 5000, "roleplay": 10000, "fashion": 10000}

    for cat, thresh in thresholds.items():
        ready = sum(s["downloaded"] for s in stats if s["category"] == cat)
        if ready >= thresh:
            status = f"{C.GREEN}✓ READY{C.RESET}"
        else:
            status = f"{C.RED}✗ Need {thresh - ready:,} more{C.RESET}"
        print(f"  {cat.capitalize()}: {ready:,} / {thresh:,} {status}")

    print()
    print(f"{C.DIM}Run: python3 parallel_code_scraper.py start  # Max speed coding collection{C.RESET}")
    print(f"{C.DIM}Run: python3 live_status.py                  # Live scraper status{C.RESET}")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Data Hub")
    parser.add_argument("--brief", action="store_true", help="Brief output")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    stats = get_all_stats()

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        render_dashboard(stats, brief=args.brief)


if __name__ == "__main__":
    main()
