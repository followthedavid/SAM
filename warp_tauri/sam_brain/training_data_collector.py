#!/usr/bin/env python3
"""
SAM Brain Training Data Collector
Extracts training data from:
1. Git commit history (code patterns, commit messages)
2. Code dedup database (file structures, patterns)
3. SSOT documents (project knowledge)
4. Task completions (successful workflows)

Output: JSONL files ready for LoRA fine-tuning
"""

import os
import sys
import json
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

# Configuration
CONFIG = {
    "output_dir": Path.home() / ".sam" / "training_data",
    "dedup_db": Path("/Volumes/Plex/SSOT/code_dedup.db"),
    "inventory_db": Path("/Volumes/Plex/SSOT/master_inventory.db"),
    "project_registry": Path.home() / ".sam" / "projects" / "registry.json",
    "min_commit_length": 10,
    "max_code_length": 4000,
    "languages": ["python", "rust", "javascript", "typescript", "vue", "swift", "bash"],
}

def setup_output_dir():
    """Create output directory structure."""
    CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)
    for subdir in ["code_patterns", "commits", "tasks", "knowledge", "routing"]:
        (CONFIG["output_dir"] / subdir).mkdir(exist_ok=True)
    print(f"Output directory: {CONFIG['output_dir']}")

def get_git_repos() -> List[Path]:
    """Find all git repositories from known project locations."""
    repos = []

    # From project registry
    if CONFIG["project_registry"].exists():
        with open(CONFIG["project_registry"]) as f:
            registry = json.load(f)
        for project in registry.get("projects", []):
            path = Path(project["path"])
            if (path / ".git").exists():
                repos.append(path)

    # Common locations
    search_paths = [
        Path.home() / "ReverseLab",
        Path.home() / "Projects",
        Path.home() / "ai-studio",
    ]

    for base in search_paths:
        if base.exists():
            for item in base.iterdir():
                if item.is_dir() and (item / ".git").exists():
                    if item not in repos:
                        repos.append(item)

    return repos

def extract_git_commits(repo_path: Path) -> List[Dict]:
    """Extract commit history with diffs."""
    commits = []

    try:
        # Get commit log with stats
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H|%s|%an|%ad", "--date=short", "-n", "500"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return commits

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue

            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            commit_hash, message, author, date = parts

            if len(message) < CONFIG["min_commit_length"]:
                continue

            # Get diff summary
            diff_result = subprocess.run(
                ["git", "diff", "--stat", f"{commit_hash}^..{commit_hash}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            diff_summary = diff_result.stdout.strip()[-500:] if diff_result.returncode == 0 else ""

            commits.append({
                "repo": repo_path.name,
                "hash": commit_hash[:8],
                "message": message,
                "author": author,
                "date": date,
                "diff_summary": diff_summary,
            })

    except Exception as e:
        print(f"  Error extracting commits from {repo_path}: {e}")

    return commits

def extract_code_patterns_from_dedup() -> List[Dict]:
    """Extract code patterns from the dedup database."""
    patterns = []

    if not CONFIG["dedup_db"].exists():
        print("  Dedup database not found, skipping...")
        return patterns

    try:
        conn = sqlite3.connect(CONFIG["dedup_db"])
        cursor = conn.cursor()

        # Get representative code files by language
        cursor.execute("""
            SELECT path, language, size_bytes, content_hash
            FROM files
            WHERE language IN (?, ?, ?, ?, ?, ?, ?)
            AND size_bytes > 100 AND size_bytes < 50000
            ORDER BY RANDOM()
            LIMIT 1000
        """, tuple(CONFIG["languages"]))

        for row in cursor.fetchall():
            path, language, size, content_hash = row

            if not os.path.exists(path):
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(CONFIG["max_code_length"])

                # Extract interesting patterns
                patterns.append({
                    "path": path,
                    "language": language,
                    "size": size,
                    "content_preview": content[:1000],
                    "has_tests": "test" in path.lower() or "spec" in path.lower(),
                    "has_docs": bool(re.search(r'"""[\s\S]*?"""', content) or re.search(r"'''[\s\S]*?'''", content)),
                })
            except:
                continue

        conn.close()

    except Exception as e:
        print(f"  Error reading dedup database: {e}")

    return patterns

def extract_project_knowledge() -> List[Dict]:
    """Extract knowledge from SSOT documents and READMEs."""
    knowledge = []

    # Find all markdown docs
    search_paths = [
        Path("/Volumes/Plex/SSOT"),
        Path.home() / ".sam",
        Path.home() / "ReverseLab" / "SAM",
    ]

    for base in search_paths:
        if not base.exists():
            continue

        for md_file in base.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if len(content) < 100:
                    continue

                knowledge.append({
                    "source": str(md_file),
                    "type": "documentation",
                    "title": md_file.stem,
                    "content": content[:5000],
                    "has_code_blocks": "```" in content,
                })
            except:
                continue

    return knowledge

def generate_routing_examples() -> List[Dict]:
    """Generate training examples for task routing."""
    examples = []

    # Task type patterns
    routing_patterns = {
        "code_generation": [
            ("Write a function that {task}", "claude-code"),
            ("Create a script to {task}", "claude-code"),
            ("Implement {feature} in {language}", "claude-code"),
            ("Add {feature} to the codebase", "claude-code"),
        ],
        "code_review": [
            ("Review this code: {code}", "claude-code"),
            ("What's wrong with this function?", "claude-code"),
            ("Improve this implementation", "claude-code"),
        ],
        "brainstorm": [
            ("What's the best way to {task}?", "chatgpt"),
            ("Help me think through {problem}", "chatgpt"),
            ("What are the options for {decision}?", "chatgpt"),
            ("Design an architecture for {system}", "chatgpt"),
        ],
        "quick_query": [
            ("What is {concept}?", "ollama"),
            ("How do I {simple_task}?", "ollama"),
            ("Explain {term}", "ollama"),
        ],
        "project_management": [
            ("What's the status of {project}?", "local"),
            ("List my projects", "local"),
            ("Show progress on {task}", "local"),
        ],
    }

    for task_type, patterns in routing_patterns.items():
        for template, target in patterns:
            examples.append({
                "task_type": task_type,
                "template": template,
                "route_to": target,
                "is_training_example": True,
            })

    return examples

def format_for_finetuning(data: List[Dict], output_file: Path, format_type: str):
    """Format data as JSONL for fine-tuning."""

    formatted = []

    for item in data:
        if format_type == "commits":
            # Commit message prediction
            formatted.append({
                "instruction": f"Given these code changes in {item['repo']}, write a commit message.",
                "input": item.get("diff_summary", "")[:500],
                "output": item["message"],
            })

        elif format_type == "routing":
            # Task routing
            formatted.append({
                "instruction": "Determine which LLM should handle this task: claude-code, chatgpt, ollama, or local",
                "input": item["template"],
                "output": item["route_to"],
            })

        elif format_type == "knowledge":
            # Knowledge Q&A
            formatted.append({
                "instruction": f"Based on the documentation for {item['title']}, answer questions about this project.",
                "input": item["content"][:2000],
                "output": f"This document covers: {item['title']}",
            })

        elif format_type == "code":
            # Code understanding
            formatted.append({
                "instruction": f"Analyze this {item['language']} code and describe what it does.",
                "input": item["content_preview"],
                "output": f"This is a {item['language']} file that {'includes tests' if item.get('has_tests') else 'is production code'}.",
            })

    with open(output_file, "w") as f:
        for item in formatted:
            f.write(json.dumps(item) + "\n")

    print(f"  Wrote {len(formatted)} examples to {output_file}")
    return len(formatted)

def main():
    print("=" * 60)
    print("SAM Brain Training Data Collector")
    print("=" * 60)
    print()

    setup_output_dir()

    total_examples = 0

    # Phase 1: Git commits
    print("\n[1/4] Extracting git commit history...")
    repos = get_git_repos()
    print(f"  Found {len(repos)} git repositories")

    all_commits = []
    for repo in repos:
        commits = extract_git_commits(repo)
        all_commits.extend(commits)
        print(f"    {repo.name}: {len(commits)} commits")

    if all_commits:
        count = format_for_finetuning(
            all_commits,
            CONFIG["output_dir"] / "commits" / "commit_messages.jsonl",
            "commits"
        )
        total_examples += count

    # Phase 2: Code patterns
    print("\n[2/4] Extracting code patterns from dedup database...")
    code_patterns = extract_code_patterns_from_dedup()
    print(f"  Found {len(code_patterns)} code samples")

    if code_patterns:
        count = format_for_finetuning(
            code_patterns,
            CONFIG["output_dir"] / "code_patterns" / "code_analysis.jsonl",
            "code"
        )
        total_examples += count

    # Phase 3: Project knowledge
    print("\n[3/4] Extracting project knowledge...")
    knowledge = extract_project_knowledge()
    print(f"  Found {len(knowledge)} documentation files")

    if knowledge:
        count = format_for_finetuning(
            knowledge,
            CONFIG["output_dir"] / "knowledge" / "project_docs.jsonl",
            "knowledge"
        )
        total_examples += count

    # Phase 4: Routing examples
    print("\n[4/4] Generating routing examples...")
    routing = generate_routing_examples()
    print(f"  Generated {len(routing)} routing examples")

    if routing:
        count = format_for_finetuning(
            routing,
            CONFIG["output_dir"] / "routing" / "task_routing.jsonl",
            "routing"
        )
        total_examples += count

    # Summary
    print("\n" + "=" * 60)
    print("COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Total training examples: {total_examples}")
    print(f"Output directory: {CONFIG['output_dir']}")
    print()
    print("Files created:")
    for jsonl in CONFIG["output_dir"].rglob("*.jsonl"):
        size = jsonl.stat().st_size / 1024
        print(f"  {jsonl.relative_to(CONFIG['output_dir'])}: {size:.1f} KB")

    # Create manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "total_examples": total_examples,
        "sources": {
            "git_repos": len(repos),
            "commits": len(all_commits),
            "code_patterns": len(code_patterns),
            "knowledge_docs": len(knowledge),
            "routing_examples": len(routing),
        },
        "files": [str(f.relative_to(CONFIG["output_dir"])) for f in CONFIG["output_dir"].rglob("*.jsonl")],
    }

    with open(CONFIG["output_dir"] / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest saved to {CONFIG['output_dir'] / 'manifest.json'}")

if __name__ == "__main__":
    main()
