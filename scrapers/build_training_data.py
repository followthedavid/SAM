#!/usr/bin/env python3
"""
Comprehensive Training Data Builder for SAM

Converts ALL collected data into unified JSONL format for MLX training.

Sources:
- Fashion articles (VMag, WMag, WWD)
- Dark psychology stories (AO3, Literotica)
- Code examples (GitHub, StackOverflow)
- Fashion photos (FirstView) - caption generation
- Roleplay content (Nifty, AO3)

Output format: Chat-style JSONL for instruction tuning
"""

import os
import re
import json
import sqlite3
import random
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "output_dir": "/Volumes/David External/sam_training",

    # Source databases
    "sources": {
        "vmag": "/Volumes/#1/vmag_archive/vmag_index.db",
        "wmag": "/Volumes/#1/wmag_archive/wmag_index.db",
        "wwd": "/Volumes/#1/wwd_archive/wwd_index.db",
        "dark_psych": "/Volumes/David External/dark_psych_archive/dark_psych_index.db",
        "code": "/Volumes/David External/coding_training/code_collection.db",
        "firstview": "/Volumes/David External/firstview_archive/firstview_index.db",
        "nifty": "/Volumes/David External/nifty_archive/stories.db",
        "literotica": "/Volumes/David External/literotica_archive/literotica_index.db",
    },

    # Content directories
    "content_dirs": {
        "vmag": "/Volumes/#1/vmag_archive/articles",
        "wmag": "/Volumes/#1/wmag_archive/articles",
        "wwd": "/Volumes/#1/wwd_archive/articles",
        "dark_psych": "/Volumes/David External/dark_psych_archive/stories",
        "nifty": "/Volumes/David External/nifty_archive/stories",
        "firstview": "/Volumes/David External/firstview_archive/photos",
    },

    # SAM's system prompt
    "system_prompt": """You are SAM, a confident and charming AI assistant. You're knowledgeable about fashion, coding, creative writing, and roleplay. You communicate with wit, occasional flirtation, and genuine helpfulness. You're direct but warm, and you enjoy intellectual banter.""",

    # Training mix ratios
    "mix_ratios": {
        "fashion": 0.25,      # Fashion/style content
        "coding": 0.25,       # Code examples
        "roleplay": 0.30,     # Creative/roleplay content
        "dark_psych": 0.20,   # Psychology/manipulation dynamics
    },
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TrainingExample:
    """A single training example in chat format."""
    system: str
    user: str
    assistant: str
    source: str
    category: str
    metadata: Dict = None

# ============================================================================
# FASHION CONTENT CONVERTER
# ============================================================================

def load_fashion_articles(source: str) -> Generator[TrainingExample, None, None]:
    """Load fashion articles and convert to training examples."""
    db_path = CONFIG["sources"].get(source)

    if not db_path or not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get downloaded articles
    cur.execute("""
        SELECT * FROM articles WHERE downloaded = 1 LIMIT 10000
    """)

    for row in cur.fetchall():
        try:
            # Try to load content from file - check multiple column names
            content_path = None
            for col in ["file_path", "content_path", "local_path"]:
                try:
                    content_path = row[col]
                    if content_path:
                        break
                except (IndexError, KeyError):
                    continue

            content = ""
            if content_path and os.path.exists(content_path):
                with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw = f.read()
                    # Check if it's JSON (VMag/WMag/WWD format)
                    if content_path.endswith('.json'):
                        try:
                            data = json.loads(raw)
                            content = data.get("content", "") or data.get("text", "") or data.get("body", "")
                            # Also try nested structures
                            if not content and isinstance(data, dict):
                                for key in ["article", "story", "post"]:
                                    if key in data and isinstance(data[key], dict):
                                        content = data[key].get("content", "") or data[key].get("text", "")
                                        break
                        except json.JSONDecodeError:
                            content = raw
                    else:
                        content = raw

            if not content or len(content) < 200:
                continue

            # Convert row to dict for easier access
            row_dict = dict(row)
            title = row_dict.get("title", "") or ""
            author = row_dict.get("author", "") or ""
            tags = row_dict.get("tags", "") or ""

            # Create different types of training examples

            # Type 1: Article summary/explanation
            if len(content) > 500:
                excerpt = content[:1500]
                yield TrainingExample(
                    system=CONFIG["system_prompt"],
                    user=f"Summarize this fashion article:\n\n{excerpt}...",
                    assistant=_generate_summary_response(title, content[:3000]),
                    source=source,
                    category="fashion",
                    metadata={"title": title, "type": "summary"}
                )

            # Type 2: Style advice based on article
            if "trend" in content.lower() or "style" in content.lower():
                yield TrainingExample(
                    system=CONFIG["system_prompt"],
                    user=f"What are the key style takeaways from the article '{title}'?",
                    assistant=_extract_style_advice(content),
                    source=source,
                    category="fashion",
                    metadata={"title": title, "type": "advice"}
                )

            # Type 3: Continue writing in style
            paragraphs = content.split('\n\n')
            if len(paragraphs) >= 3:
                setup = '\n\n'.join(paragraphs[:2])
                continuation = '\n\n'.join(paragraphs[2:4])
                if len(continuation) > 200:
                    yield TrainingExample(
                        system=CONFIG["system_prompt"],
                        user=f"Continue this fashion article:\n\n{setup[:1000]}",
                        assistant=continuation[:1500],
                        source=source,
                        category="fashion",
                        metadata={"title": title, "type": "continuation"}
                    )

        except Exception as e:
            continue

    conn.close()

def _generate_summary_response(title: str, content: str) -> str:
    """Generate a summary response for fashion content."""
    # Extract key points from content
    sentences = re.split(r'[.!?]+', content)
    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 50][:5]

    if not key_sentences:
        return f"This article discusses {title}."

    summary = f"This piece explores {title.lower() if title else 'fashion trends'}. "
    summary += " ".join(key_sentences[:3])

    return summary[:1500]

def _extract_style_advice(content: str) -> str:
    """Extract style advice from fashion content."""
    # Look for actionable phrases
    advice_patterns = [
        r"you (?:can|should|could|might) ([^.]+)",
        r"try ([^.]+)",
        r"consider ([^.]+)",
        r"opt for ([^.]+)",
        r"pair (?:it )?with ([^.]+)",
    ]

    advice = []
    for pattern in advice_patterns:
        matches = re.findall(pattern, content.lower())
        advice.extend(matches[:2])

    if advice:
        return "Key style tips: " + ". ".join(a.strip().capitalize() for a in advice[:5]) + "."

    # Fallback: extract sentences with style keywords
    sentences = re.split(r'[.!?]+', content)
    style_sentences = [s.strip() for s in sentences
                       if any(kw in s.lower() for kw in ['wear', 'style', 'look', 'trend', 'fashion'])]

    return " ".join(style_sentences[:3])[:1000] or "This article offers various style insights."

# ============================================================================
# DARK PSYCHOLOGY CONTENT CONVERTER
# ============================================================================

def load_dark_psych_stories() -> Generator[TrainingExample, None, None]:
    """Load dark psychology stories for training."""
    db_path = CONFIG["sources"]["dark_psych"]

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check actual column names
    cur.execute("PRAGMA table_info(stories)")
    columns = [col[1] for col in cur.fetchall()]

    # Build query based on available columns
    order_col = "intensity_score" if "intensity_score" in columns else "id"
    cur.execute(f"""
        SELECT * FROM stories WHERE downloaded = 1
        ORDER BY {order_col} DESC LIMIT 5000
    """)

    for row in cur.fetchall():
        try:
            row_dict = dict(row)
            content_path = row_dict.get("content_path")
            if not content_path or not os.path.exists(content_path):
                continue

            with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if len(content) < 500:
                continue

            title = row_dict.get("title", "") or ""
            dark_tags = row_dict.get("dark_tags", "")
            tags = json.loads(dark_tags) if dark_tags else []
            intensity = row_dict.get("intensity_score", 0) or 0

            # Create roleplay-style training examples
            paragraphs = content.split('\n\n')

            if len(paragraphs) >= 4:
                # Setup + continuation format
                setup = '\n\n'.join(paragraphs[:2])
                continuation = '\n\n'.join(paragraphs[2:5])

                # Build instruction based on tags
                tag_str = ", ".join(tags[:3]) if tags else "dark themes"

                yield TrainingExample(
                    system=CONFIG["system_prompt"],
                    user=f"Continue this story with {tag_str}:\n\n{setup[:1200]}",
                    assistant=continuation[:2000],
                    source="dark_psych",
                    category="roleplay",
                    metadata={"title": title, "intensity": intensity, "tags": tags}
                )

            # Extract dialogue for conversation training
            dialogue = re.findall(r'"([^"]{20,300})"', content)
            if len(dialogue) >= 4:
                # Create dialogue-focused example
                yield TrainingExample(
                    system=CONFIG["system_prompt"],
                    user=f"Write dialogue for a scene involving {tag_str}.",
                    assistant='\n\n'.join(f'"{d}"' for d in dialogue[:6]),
                    source="dark_psych",
                    category="roleplay",
                    metadata={"type": "dialogue", "tags": tags}
                )

        except Exception as e:
            continue

    conn.close()

# ============================================================================
# CODE CONTENT CONVERTER
# ============================================================================

def load_code_examples() -> Generator[TrainingExample, None, None]:
    """Load code examples for training."""
    db_path = CONFIG["sources"]["code"]

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Code examples
    cur.execute("SELECT * FROM code_examples LIMIT 10000")

    for row in cur.fetchall():
        try:
            row_dict = dict(row)
            code = row_dict.get("code", "") or ""
            title = row_dict.get("title", "") or ""
            description = row_dict.get("description", "") or ""
            language = row_dict.get("language", "") or ""
            context = row_dict.get("context", "") or ""

            if not code or len(code) < 50:
                continue

            # Code completion example
            yield TrainingExample(
                system=CONFIG["system_prompt"],
                user=f"Write a {language} function: {title}\n\n{description[:500] if description else ''}",
                assistant=code[:2000],
                source="code",
                category="coding",
                metadata={"language": language, "context": context}
            )

        except Exception:
            continue

    # PR diffs - improvement examples
    cur.execute("SELECT * FROM pr_diffs LIMIT 5000")

    for row in cur.fetchall():
        try:
            row_dict = dict(row)
            before = row_dict.get("before_code", "") or ""
            after = row_dict.get("after_code", "") or ""
            title = row_dict.get("title", "") or ""
            review_comments = row_dict.get("review_comments", "")
            comments = json.loads(review_comments) if review_comments else []
            language = row_dict.get("language", "") or ""

            if not before or not after or len(before) < 50:
                continue

            feedback = comments[0] if comments else title

            yield TrainingExample(
                system=CONFIG["system_prompt"],
                user=f"Improve this {language} code based on feedback: {feedback[:200]}\n\n```{language}\n{before[:1500]}\n```",
                assistant=f"```{language}\n{after[:2000]}\n```",
                source="code_pr",
                category="coding",
                metadata={"language": language, "type": "improvement"}
            )

        except Exception:
            continue

    conn.close()

# ============================================================================
# MAIN BUILDER
# ============================================================================

def build_training_data(
    output_path: str = None,
    max_examples: int = 50000,
    include_fashion: bool = True,
    include_code: bool = True,
    include_roleplay: bool = True,
    include_dark: bool = True,
) -> Dict:
    """Build comprehensive training dataset."""

    output_path = output_path or os.path.join(CONFIG["output_dir"], "sam_training.jsonl")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    all_examples = []
    stats = {"fashion": 0, "coding": 0, "roleplay": 0, "dark_psych": 0}

    print("=" * 60)
    print("  SAM Training Data Builder")
    print("=" * 60)

    # Load fashion content
    if include_fashion:
        print("\nLoading fashion content...")
        for source in ["vmag", "wmag", "wwd"]:
            count = 0
            for ex in load_fashion_articles(source):
                all_examples.append(ex)
                count += 1
                if count >= 3000:
                    break
            print(f"  {source}: {count} examples")
            stats["fashion"] += count

    # Load dark psychology content
    if include_dark:
        print("\nLoading dark psychology content...")
        count = 0
        for ex in load_dark_psych_stories():
            all_examples.append(ex)
            count += 1
            if count >= 5000:
                break
        print(f"  dark_psych: {count} examples")
        stats["dark_psych"] = count

    # Load code content
    if include_code:
        print("\nLoading code content...")
        count = 0
        for ex in load_code_examples():
            all_examples.append(ex)
            count += 1
            if count >= 10000:
                break
        print(f"  code: {count} examples")
        stats["coding"] = count

    # Shuffle and limit
    random.shuffle(all_examples)
    all_examples = all_examples[:max_examples]

    # Convert to JSONL format
    print(f"\nWriting {len(all_examples)} examples to {output_path}...")

    with open(output_path, 'w') as f:
        for ex in all_examples:
            record = {
                "messages": [
                    {"role": "system", "content": ex.system},
                    {"role": "user", "content": ex.user},
                    {"role": "assistant", "content": ex.assistant}
                ],
                "source": ex.source,
                "category": ex.category,
            }
            f.write(json.dumps(record) + "\n")

    # Split into train/val
    train_path = output_path.replace(".jsonl", "_train.jsonl")
    val_path = output_path.replace(".jsonl", "_val.jsonl")

    split_idx = int(len(all_examples) * 0.9)

    with open(train_path, 'w') as f:
        for ex in all_examples[:split_idx]:
            record = {
                "messages": [
                    {"role": "system", "content": ex.system},
                    {"role": "user", "content": ex.user},
                    {"role": "assistant", "content": ex.assistant}
                ]
            }
            f.write(json.dumps(record) + "\n")

    with open(val_path, 'w') as f:
        for ex in all_examples[split_idx:]:
            record = {
                "messages": [
                    {"role": "system", "content": ex.system},
                    {"role": "user", "content": ex.user},
                    {"role": "assistant", "content": ex.assistant}
                ]
            }
            f.write(json.dumps(record) + "\n")

    print("\n" + "=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    print(f"\nTotal examples: {len(all_examples)}")
    print(f"  Fashion:    {stats['fashion']}")
    print(f"  Coding:     {stats['coding']}")
    print(f"  Dark Psych: {stats['dark_psych']}")
    print(f"\nOutput files:")
    print(f"  Training: {train_path} ({split_idx} examples)")
    print(f"  Validation: {val_path} ({len(all_examples) - split_idx} examples)")

    return {
        "total": len(all_examples),
        "stats": stats,
        "train_path": train_path,
        "val_path": val_path,
    }

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build SAM Training Data")
    parser.add_argument("command", choices=["build", "stats"], nargs="?", default="build")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--max", "-m", type=int, default=50000, help="Max examples")
    parser.add_argument("--no-fashion", action="store_true", help="Skip fashion content")
    parser.add_argument("--no-code", action="store_true", help="Skip code content")
    parser.add_argument("--no-dark", action="store_true", help="Skip dark psychology content")

    args = parser.parse_args()

    if args.command == "build":
        build_training_data(
            output_path=args.output,
            max_examples=args.max,
            include_fashion=not args.no_fashion,
            include_code=not args.no_code,
            include_dark=not args.no_dark,
        )
    elif args.command == "stats":
        print("Checking available data sources...")
        for name, path in CONFIG["sources"].items():
            if os.path.exists(path):
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                try:
                    # Try common table names
                    for table in ["articles", "stories", "code_examples", "photos", "content"]:
                        try:
                            cur.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cur.fetchone()[0]
                            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE downloaded=1")
                            downloaded = cur.fetchone()[0]
                            print(f"  {name}: {downloaded}/{count} downloaded")
                            break
                        except:
                            continue
                except:
                    pass
                conn.close()
            else:
                print(f"  {name}: NOT FOUND")

if __name__ == "__main__":
    main()
