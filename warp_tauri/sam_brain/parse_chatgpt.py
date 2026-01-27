#!/usr/bin/env python3
"""
Parse ChatGPT export and convert to SAM training format.
Filters for: coding, roleplay, planning, coaching content.
"""

import json
import os
from pathlib import Path
from typing import Generator
import hashlib

# Paths
CHATGPT_DIR = Path("/Volumes/David External/chatgpt_export/conversations/personal/conversations")
OUTPUT_DIR = Path("/Volumes/David External/chatgpt_training")
CONVERSATIONS_JSON = CHATGPT_DIR / "conversations.json"

# Categories and their keywords
CATEGORIES = {
    "coding": [
        "python", "javascript", "rust", "code", "function", "class", "error",
        "debug", "api", "database", "sql", "git", "docker", "deploy", "test",
        "import", "async", "await", "json", "http", "server", "client"
    ],
    "roleplay": [
        "roleplay", "character", "scenario", "villain", "dragon", "fantasy",
        "story", "narrative", "dialogue", "scene", "act as", "pretend",
        "[", "]", "*", "~"  # Common roleplay markers
    ],
    "planning": [
        "plan", "architecture", "design", "strategy", "roadmap", "phase",
        "implement", "build", "project", "task", "milestone", "dependency",
        "approach", "solution", "system"
    ],
    "coaching": [
        "confidence", "imposter", "anxiety", "motivation", "habit", "goal",
        "advice", "help me", "struggling", "feel like", "how do i", "should i"
    ]
}


def load_conversations() -> list:
    """Load all conversations from the export."""
    if not CONVERSATIONS_JSON.exists():
        print(f"Error: {CONVERSATIONS_JSON} not found")
        return []

    with open(CONVERSATIONS_JSON, 'r') as f:
        return json.load(f)


def extract_messages(conversation: dict) -> list[tuple[str, str]]:
    """Extract user/assistant message pairs from a conversation."""
    pairs = []
    mapping = conversation.get("mapping", {})

    # Build message chain
    messages = []
    for node_id, node in mapping.items():
        msg = node.get("message")
        if msg and msg.get("content", {}).get("parts"):
            role = msg.get("author", {}).get("role", "")
            # Handle mixed content types (strings, dicts for code/images)
            parts = []
            for part in msg["content"]["parts"]:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    # Extract text from dict parts (code blocks, etc.)
                    if "text" in part:
                        parts.append(part["text"])
                    elif "content" in part:
                        parts.append(str(part["content"]))
            content = "\n".join(parts)
            if content.strip() and role in ("user", "assistant"):
                messages.append((role, content, msg.get("create_time", 0)))

    # Sort by time
    messages.sort(key=lambda x: x[2] if x[2] else 0)

    # Pair user/assistant
    for i, (role, content, _) in enumerate(messages):
        if role == "user" and i + 1 < len(messages):
            next_role, next_content, _ = messages[i + 1]
            if next_role == "assistant" and next_content.strip():
                pairs.append((content, next_content))

    return pairs


def categorize_content(user_msg: str, assistant_msg: str) -> list[str]:
    """Determine which categories a message pair belongs to."""
    combined = (user_msg + " " + assistant_msg).lower()
    categories = []

    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score >= 2:  # At least 2 keyword matches
            categories.append(category)

    return categories if categories else ["general"]


def dedupe_key(user_msg: str) -> str:
    """Create deduplication key from user message."""
    return hashlib.md5(user_msg.strip().lower().encode()).hexdigest()[:16]


def convert_to_training_format(user_msg: str, assistant_msg: str) -> dict:
    """Convert to JSONL training format."""
    # ChatML format (matches existing SAM training data)
    return {
        "messages": [
            {"role": "user", "content": user_msg.strip()},
            {"role": "assistant", "content": assistant_msg.strip()}
        ]
    }


def process_conversations():
    """Main processing function."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conversations = load_conversations()
    print(f"Loaded {len(conversations)} conversations")

    # Track by category
    categorized = {cat: [] for cat in CATEGORIES.keys()}
    categorized["general"] = []
    seen_keys = set()

    total_pairs = 0
    for conv in conversations:
        pairs = extract_messages(conv)
        for user_msg, assistant_msg in pairs:
            # Skip very short or very long
            if len(user_msg) < 10 or len(assistant_msg) < 20:
                continue
            if len(user_msg) > 10000 or len(assistant_msg) > 10000:
                continue

            # Dedupe
            key = dedupe_key(user_msg)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            # Categorize
            cats = categorize_content(user_msg, assistant_msg)
            training_item = convert_to_training_format(user_msg, assistant_msg)

            for cat in cats:
                categorized[cat].append(training_item)

            total_pairs += 1

    # Write output files
    for category, items in categorized.items():
        if items:
            output_file = OUTPUT_DIR / f"chatgpt_{category}.jsonl"
            with open(output_file, 'w') as f:
                for item in items:
                    f.write(json.dumps(item) + "\n")
            print(f"  {category}: {len(items)} examples -> {output_file}")

    # Write combined file
    all_items = []
    for items in categorized.values():
        all_items.extend(items)

    combined_file = OUTPUT_DIR / "chatgpt_all.jsonl"
    with open(combined_file, 'w') as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")

    print(f"\nTotal: {total_pairs} unique training pairs")
    print(f"Combined: {len(all_items)} (includes multi-category)")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    process_conversations()
