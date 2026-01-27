#!/usr/bin/env python3
"""
Analyze Warp session data to extract patterns and build SAM knowledge base.
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime

KNOWLEDGE_DIR = Path(__file__).parent

def load_json(filename):
    path = KNOWLEDGE_DIR / filename
    if path.exists():
        return json.load(open(path))
    return []

def analyze_ai_queries():
    """Analyze AI query patterns."""
    queries = load_json("ai_queries.json")

    # Categorize queries
    categories = {
        "file_ops": [],
        "git": [],
        "debugging": [],
        "scripting": [],
        "system": [],
        "search": [],
        "explanation": [],
        "other": []
    }

    keywords = {
        "file_ops": ["file", "directory", "folder", "copy", "move", "delete", "create", "mkdir", "rm", "cp", "mv"],
        "git": ["git", "commit", "push", "pull", "branch", "merge", "repo"],
        "debugging": ["error", "fix", "debug", "issue", "problem", "fail", "broken"],
        "scripting": ["script", "bash", "python", "function", "loop", "if ", "for "],
        "system": ["install", "brew", "npm", "pip", "service", "process", "port"],
        "search": ["find", "grep", "search", "where", "locate"],
        "explanation": ["what", "how", "why", "explain", "show me", "help"]
    }

    for q in queries:
        input_text = q.get("input", "").lower()
        categorized = False

        for cat, kws in keywords.items():
            if any(kw in input_text for kw in kws):
                categories[cat].append(q)
                categorized = True
                break

        if not categorized:
            categories["other"].append(q)

    return {
        "total": len(queries),
        "by_category": {k: len(v) for k, v in categories.items()},
        "categories": categories
    }

def analyze_commands():
    """Analyze command patterns."""
    commands = load_json("commands.json")

    # Extract command prefixes
    prefixes = Counter()
    directories = Counter()

    for cmd in commands:
        command = cmd.get("command", "")
        pwd = cmd.get("pwd", "")

        # Get first word as prefix
        if command:
            prefix = command.split()[0] if command.split() else ""
            prefixes[prefix] += 1

        if pwd:
            directories[pwd] += 1

    return {
        "total": len(commands),
        "top_commands": prefixes.most_common(30),
        "top_directories": directories.most_common(20),
        "success_rate": sum(1 for c in commands if c.get("exit_code") == 0) / len(commands) if commands else 0
    }

def analyze_workflows():
    """Analyze saved workflows."""
    workflows = load_json("workflows.json")
    return {
        "total": len(workflows),
        "workflows": workflows
    }

def generate_summary():
    """Generate complete analysis summary."""
    ai_analysis = analyze_ai_queries()
    cmd_analysis = analyze_commands()
    wf_analysis = analyze_workflows()

    summary = {
        "generated_at": datetime.now().isoformat(),
        "ai_queries": {
            "total": ai_analysis["total"],
            "by_category": ai_analysis["by_category"]
        },
        "commands": {
            "total": cmd_analysis["total"],
            "top_10_commands": cmd_analysis["top_commands"][:10],
            "top_directories": cmd_analysis["top_directories"][:10],
            "success_rate": f"{cmd_analysis['success_rate']:.1%}"
        },
        "workflows": {
            "total": wf_analysis["total"]
        }
    }

    # Save summary
    with open(KNOWLEDGE_DIR / "analysis_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary

def extract_query_samples(category, limit=10):
    """Extract sample queries from a category."""
    ai_analysis = analyze_ai_queries()
    samples = ai_analysis["categories"].get(category, [])[:limit]
    return [{"input": s["input"], "dir": s.get("working_directory", "")} for s in samples]

if __name__ == "__main__":
    print("Analyzing Warp session data...")
    summary = generate_summary()

    print(f"\n=== AI Queries ({summary['ai_queries']['total']}) ===")
    for cat, count in summary["ai_queries"]["by_category"].items():
        print(f"  {cat}: {count}")

    print(f"\n=== Commands ({summary['commands']['total']}) ===")
    print(f"  Success rate: {summary['commands']['success_rate']}")
    print("  Top commands:")
    for cmd, count in summary["commands"]["top_10_commands"]:
        print(f"    {cmd}: {count}")

    print(f"\n=== Workflows ({summary['workflows']['total']}) ===")

    print("\nSummary saved to analysis_summary.json")
