#!/usr/bin/env python3
"""
SAM Memory Bootstrap - Load salvaged knowledge into semantic memory.

Run this once to import patterns and knowledge from salvaged scripts
into SAM's semantic memory for instant recall.
"""

import json
from pathlib import Path
from semantic_memory import SemanticMemory

SALVAGED_PATH = Path("/Volumes/Plex/SSOT/salvaged")
SSOT_PATH = Path("/Volumes/Plex/SSOT")


def bootstrap_memory():
    """Load key knowledge into SAM's semantic memory."""
    memory = SemanticMemory()

    print("SAM Memory Bootstrap")
    print("=" * 40)

    # 1. Load salvaged script summaries
    script_knowledge = [
        {
            "content": "StashDB GraphQL API client for querying scenes, performers, and studios. "
                      "Use stashdb_query.py from salvaged/stash_scripts/ for Stash Enhancement integration.",
            "type": "solution",
            "tags": ["stash", "graphql", "api"]
        },
        {
            "content": "Image categorization with OpenCV face detection and image hashing. "
                      "Use image_categorizer.py for promo/behind_scenes/photoshoot sorting. "
                      "Requires: PIL, imagehash, cv2.",
            "type": "solution",
            "tags": ["opencv", "image", "categorization"]
        },
        {
            "content": "Memory relationships pattern: SQLite table linking memories together. "
                      "Schema: relationships(source_id, target_id, relationship_type, metadata). "
                      "From salvaged/memory_core/memory_manager.py.",
            "type": "solution",
            "tags": ["memory", "sqlite", "relationships"]
        },
        {
            "content": "External memory scanning pattern: Iterate through Claude/ChatGPT/Warp export paths, "
                      "extract insights from .json/.md files, store in database. "
                      "From salvaged/ai_24_7_system/local_ai_orchestrator.py.",
            "type": "solution",
            "tags": ["memory", "import", "external"]
        },
        {
            "content": "ChatGPT Manager system has orchestrator, memory_manager, batch_queue, "
                      "resource_monitor, phone_control, improvement_system. "
                      "15 scripts at salvaged/chatgpt_manager/.",
            "type": "note",
            "tags": ["chatgpt", "automation", "patterns"]
        },
        {
            "content": "Knowledge stream JSONL format with relationships field. "
                      "Can import using: id, timestamp, source, entry_type, content, metadata, relationships. "
                      "Sample at salvaged/memory_data/knowledge_stream.jsonl.",
            "type": "solution",
            "tags": ["jsonl", "import", "format"]
        },
        {
            "content": "Task priority calculation: base 10, +5 per dependency, +3 per blocking task, "
                      "+2 * completion_rate. From local_ai_orchestrator.py.",
            "type": "solution",
            "tags": ["tasks", "priority", "algorithm"]
        },
        {
            "content": "Chat categorization schema with 30 topics: Code_Development, System_Optimization, "
                      "Data_Analysis, Health_Medical, etc. From unified_chats/.",
            "type": "note",
            "tags": ["chat", "categories", "organization"]
        },
    ]

    print(f"\nLoading {len(script_knowledge)} script knowledge entries...")
    for item in script_knowledge:
        memory.add(item["content"], item["type"], {"tags": item["tags"], "source": "salvaged"})

    # 2. Load project information
    projects = [
        "SAM Brain: Local AI orchestrator with CHAT/ROLEPLAY/CODE/REASON/IMAGE routing via Ollama",
        "SAM Terminal: Warp-based interface for SAM interactions",
        "RVC Voice: Voice cloning with Dustin Steele model for SAM's voice",
        "Character Pipeline: Daz3D automation for character generation",
        "Stash Enhancement: Media organization with StashDB integration",
        "ComfyUI LoRA: Image generation with athletic men LoRA models",
        "Account Automation: Browser automation with Playwright",
        "iOS Companion: Swift app for HomeKit/watchOS/tvOS integration",
    ]

    print(f"Loading {len(projects)} project summaries...")
    for project in projects:
        memory.add(project, "note", {"category": "project", "source": "ssot"})

    # 3. Load key file locations
    locations = [
        "Training data: /Volumes/David External/SAM_Backup/all_training.jsonl (37GB, 78M lines)",
        "Salvaged scripts: /Volumes/Plex/SSOT/salvaged/ (115 scripts in 8 folders)",
        "SSOT documentation: /Volumes/Plex/SSOT/projects/ (20+ project docs)",
        "SAM source code: /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/",
    ]

    print(f"Loading {len(locations)} key locations...")
    for loc in locations:
        memory.add(loc, "note", {"category": "location", "source": "bootstrap"})

    # 4. Import knowledge stream if available
    knowledge_stream = SALVAGED_PATH / "memory_data" / "knowledge_stream.jsonl"
    if knowledge_stream.exists():
        print(f"\nImporting knowledge stream from {knowledge_stream}...")
        count = 0
        for line in knowledge_stream.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                content = json.dumps(data.get("content", {}))
                if content and content != "{}":
                    memory.add(
                        content,
                        data.get("entry_type", "note"),
                        {"source": "knowledge_stream", "original_id": data.get("id")}
                    )
                    count += 1
            except:
                pass
        print(f"  Imported {count} entries from knowledge stream")

    # Summary
    stats = memory.stats()
    print("\n" + "=" * 40)
    print("Bootstrap complete!")
    print(f"Total entries: {stats['total_entries']}")
    print(f"Embedded: {stats['embedded_entries']}")
    print(f"By type: {stats['by_type']}")

    return memory


if __name__ == "__main__":
    bootstrap_memory()
