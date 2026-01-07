#!/usr/bin/env python3
"""
SAM Project Manager - Organize, search, and manage discovered projects

Commands:
  list [type]        - List projects (optionally by type)
  search <query>     - Search projects by name/path/description
  stats              - Show statistics
  duplicates         - Find potential duplicates
  stale              - Find old/unused projects
  categorize         - Auto-categorize projects
  export             - Export active projects for SAM
  interactive        - Interactive browser
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DISCOVERED_FILE = Path(__file__).parent / "projects_discovered.json"
PROJECTS_FILE = Path(__file__).parent / "projects.json"
METADATA_FILE = Path(__file__).parent / "projects_metadata.json"


def load_discovered() -> dict:
    """Load discovered projects."""
    if DISCOVERED_FILE.exists():
        return json.load(open(DISCOVERED_FILE))
    return {"projects": []}


def load_metadata() -> dict:
    """Load project metadata (status, notes, etc)."""
    if METADATA_FILE.exists():
        return json.load(open(METADATA_FILE))
    return {}


def save_metadata(metadata: dict):
    """Save project metadata."""
    json.dump(metadata, open(METADATA_FILE, 'w'), indent=2)


def get_project_id(project: dict) -> str:
    """Generate a unique ID for a project."""
    return project["path"]


def cmd_stats():
    """Show project statistics."""
    data = load_discovered()
    projects = data.get("projects", [])

    print(f"Total Projects: {len(projects)}")
    print(f"Scan Date: {data.get('scan_date', 'unknown')}")
    print()

    # By type
    type_counts = defaultdict(int)
    for p in projects:
        for t in p.get("types", ["unknown"]):
            type_counts[t] += 1

    print("By Type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:15} {count:5}")

    # By location
    print()
    print("By Location:")
    location_counts = defaultdict(int)
    for p in projects:
        path = p["path"]
        if path.startswith("/Volumes/"):
            parts = path.split("/")
            loc = f"/Volumes/{parts[2]}"
        elif path.startswith("/Users/"):
            parts = path.split("/")
            if len(parts) > 3:
                loc = f"~/{parts[3]}"
            else:
                loc = "~"
        else:
            loc = "other"
        location_counts[loc] += 1

    for loc, count in sorted(location_counts.items(), key=lambda x: -x[1]):
        print(f"  {loc:30} {count:5}")


def cmd_list(type_filter: str = None, limit: int = 50):
    """List projects, optionally filtered by type."""
    data = load_discovered()
    projects = data.get("projects", [])

    if type_filter:
        projects = [p for p in projects if type_filter.lower() in [t.lower() for t in p.get("types", [])]]

    print(f"Projects ({len(projects)} total):")
    print("-" * 80)

    for i, p in enumerate(projects[:limit]):
        types = ", ".join(p.get("types", []))
        name = p.get("name", "?")[:25]
        desc = p.get("description", "")[:40]
        print(f"{name:25} [{types:15}] {desc}")

    if len(projects) > limit:
        print(f"\n... and {len(projects) - limit} more")


def cmd_search(query: str):
    """Search projects."""
    data = load_discovered()
    projects = data.get("projects", [])

    query_lower = query.lower()
    matches = []

    for p in projects:
        score = 0
        name = p.get("name", "").lower()
        path = p.get("path", "").lower()
        desc = p.get("description", "").lower()
        keywords = [k.lower() for k in p.get("keywords", [])]

        if query_lower in name:
            score += 10
        if query_lower in path:
            score += 5
        if query_lower in desc:
            score += 3
        if query_lower in keywords:
            score += 7

        if score > 0:
            matches.append((score, p))

    matches.sort(key=lambda x: -x[0])

    print(f"Search results for '{query}' ({len(matches)} matches):")
    print("-" * 80)

    for score, p in matches[:30]:
        types = ", ".join(p.get("types", []))[:15]
        print(f"{p['name']:25} [{types:15}] {p['path']}")


def cmd_duplicates():
    """Find potential duplicate projects."""
    data = load_discovered()
    projects = data.get("projects", [])

    # Group by name
    by_name = defaultdict(list)
    for p in projects:
        by_name[p["name"].lower()].append(p)

    print("Potential Duplicates:")
    print("-" * 80)

    count = 0
    for name, group in sorted(by_name.items()):
        if len(group) > 1:
            count += 1
            print(f"\n{name} ({len(group)} copies):")
            for p in group:
                print(f"  {p['path']}")

    print(f"\n{count} duplicate names found")


def cmd_stale():
    """Find old/potentially unused projects."""
    data = load_discovered()
    projects = data.get("projects", [])

    print("Checking for stale projects...")
    print("-" * 80)

    stale = []
    for p in projects:
        path = Path(p["path"])
        if not path.exists():
            continue

        # Check most recent file modification
        try:
            newest = None
            for f in path.rglob("*"):
                if f.is_file() and not any(skip in str(f) for skip in ['.git', 'node_modules', '__pycache__']):
                    try:
                        mtime = f.stat().st_mtime
                        if newest is None or mtime > newest:
                            newest = mtime
                    except:
                        pass

            if newest:
                age_days = (datetime.now().timestamp() - newest) / 86400
                if age_days > 365:  # Over 1 year old
                    stale.append((age_days, p))
        except:
            pass

    stale.sort(key=lambda x: -x[0])

    print(f"Projects not modified in over 1 year ({len(stale)}):")
    for age, p in stale[:30]:
        years = age / 365
        print(f"  {years:.1f}y old: {p['name']:25} {p['path']}")


def cmd_categorize():
    """Auto-categorize projects into groups."""
    data = load_discovered()
    projects = data.get("projects", [])

    categories = {
        "AI/ML": ["comfyui", "stable", "diffusion", "llm", "model", "training", "neural", "torch", "tensorflow"],
        "Media": ["video", "audio", "music", "image", "media", "player", "stash", "plex"],
        "Games": ["unity", "unreal", "game", "godot"],
        "Automation": ["automation", "bot", "scraper", "crawler"],
        "Web": ["react", "vue", "angular", "nextjs", "django", "flask", "api"],
        "Tools": ["cli", "tool", "utility", "script"],
        "Voice": ["voice", "rvc", "tts", "speech", "audio"],
        "3D": ["3d", "blender", "daz", "character", "avatar", "mesh"],
    }

    categorized = defaultdict(list)

    for p in projects:
        name = p.get("name", "").lower()
        path = p.get("path", "").lower()
        desc = p.get("description", "").lower()
        keywords = " ".join(p.get("keywords", []))
        full_text = f"{name} {path} {desc} {keywords}".lower()

        matched = False
        for cat, terms in categories.items():
            if any(term in full_text for term in terms):
                categorized[cat].append(p)
                matched = True
                break

        if not matched:
            categorized["Other"].append(p)

    print("Projects by Category:")
    print("-" * 80)

    for cat in ["AI/ML", "Media", "Games", "Automation", "Web", "Tools", "Voice", "3D", "Other"]:
        if cat in categorized:
            print(f"\n{cat} ({len(categorized[cat])}):")
            for p in categorized[cat][:5]:
                print(f"  {p['name']:30} {p['path'][:50]}")
            if len(categorized[cat]) > 5:
                print(f"  ... and {len(categorized[cat]) - 5} more")


def cmd_export(min_types: int = 1):
    """Export top projects to projects.json for SAM."""
    data = load_discovered()
    projects = data.get("projects", [])

    # Filter to "real" projects (have git, or multiple types, or description)
    quality_projects = []
    for p in projects:
        score = 0
        if "git" in p.get("types", []):
            score += 5
        if len(p.get("types", [])) >= 2:
            score += 3
        if p.get("description"):
            score += 2
        if any(t in p.get("types", []) for t in ["rust", "tauri", "docker"]):
            score += 3
        if "/Volumes/" not in p["path"]:  # Prefer local
            score += 1

        if score >= 3:
            p["quality_score"] = score
            quality_projects.append(p)

    quality_projects.sort(key=lambda x: -x.get("quality_score", 0))

    # Convert to SAM format
    sam_projects = []
    for p in quality_projects[:50]:  # Top 50
        sam_projects.append({
            "name": p["name"],
            "path": p["path"],
            "type": p["types"][0] if p.get("types") else "unknown",
            "description": p.get("description", f"{p['name']} project"),
            "keywords": p.get("keywords", [p["name"].lower()])
        })

    output = {
        "projects": sam_projects,
        "default_project": "sam_brain",
        "total_discovered": len(projects),
        "exported": len(sam_projects),
        "export_date": datetime.now().isoformat()
    }

    json.dump(output, open(PROJECTS_FILE, 'w'), indent=2)
    print(f"Exported {len(sam_projects)} quality projects to {PROJECTS_FILE}")


def cmd_interactive():
    """Interactive project browser."""
    data = load_discovered()
    projects = data.get("projects", [])

    print("SAM Project Browser")
    print("Commands: list, search <q>, stats, type <t>, quit")
    print("-" * 60)

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue
        elif cmd == "quit" or cmd == "q":
            break
        elif cmd == "list":
            cmd_list(limit=20)
        elif cmd == "stats":
            cmd_stats()
        elif cmd.startswith("search "):
            cmd_search(cmd[7:])
        elif cmd.startswith("type "):
            cmd_list(type_filter=cmd[5:], limit=20)
        else:
            print("Unknown command")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nQuick stats:")
        cmd_stats()
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        cmd_stats()
    elif cmd == "list":
        type_filter = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(type_filter)
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: project_manager.py search <query>")
            return
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "duplicates":
        cmd_duplicates()
    elif cmd == "stale":
        cmd_stale()
    elif cmd == "categorize":
        cmd_categorize()
    elif cmd == "export":
        cmd_export()
    elif cmd == "interactive" or cmd == "i":
        cmd_interactive()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
