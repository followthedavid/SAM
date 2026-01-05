#!/usr/bin/env python3
"""
SAM Project Registry - Scans and tracks all projects for cross-project awareness
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
import glob

REGISTRY_PATH = Path.home() / ".sam_project_registry.json"

# Projects to track
PROJECT_ROOTS = [
    Path.home() / "ReverseLab",
    Path.home() / "Projects",
]

# Known project configs
PROJECT_INDICATORS = {
    "rust": ["Cargo.toml"],
    "node": ["package.json"],
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "tauri": ["tauri.conf.json"],
}

def detect_project_type(path: Path) -> str:
    """Detect project type from files present"""
    for ptype, indicators in PROJECT_INDICATORS.items():
        for ind in indicators:
            if (path / ind).exists():
                return ptype
    return "unknown"

def get_git_info(path: Path) -> dict:
    """Get git status for a project"""
    git_dir = path / ".git"
    if not git_dir.exists():
        return None

    try:
        # Get branch
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path, capture_output=True, text=True, timeout=5
        ).stdout.strip() or "detached"

        # Get uncommitted changes count
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path, capture_output=True, text=True, timeout=5
        ).stdout
        changes = len([l for l in status.split('\n') if l.strip()])

        # Get last commit info
        log = subprocess.run(
            ["git", "log", "-1", "--format=%ar|||%s"],
            cwd=path, capture_output=True, text=True, timeout=5
        ).stdout.strip()

        if "|||" in log:
            time_ago, message = log.split("|||", 1)
        else:
            time_ago, message = "unknown", ""

        return {
            "branch": branch,
            "uncommitted_changes": changes,
            "last_commit_time": time_ago,
            "last_commit_message": message[:80]
        }
    except Exception as e:
        return {"error": str(e)}

def get_recent_files(path: Path, extensions: list) -> list:
    """Get recently modified source files"""
    files = []
    for ext in extensions:
        files.extend(path.rglob(f"*{ext}"))

    # Sort by modification time, get top 5
    files = [(f, f.stat().st_mtime) for f in files if f.is_file()]
    files.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            "path": str(f.relative_to(path)),
            "modified": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")
        }
        for f, t in files[:5]
    ]

def check_running_services(name: str) -> list:
    """Check for running processes related to project"""
    try:
        result = subprocess.run(
            ["pgrep", "-fl", name],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip().split('\n')[:3]
    except:
        pass
    return []

def get_project_health(project: dict) -> str:
    """Determine project health status"""
    git = project.get("git")
    if not git:
        return "unknown"

    if git.get("uncommitted_changes", 0) > 10:
        return "needs_commit"
    if "error" in git:
        return "git_error"

    return "healthy"

def scan_project(path: Path) -> dict:
    """Scan a single project directory"""
    name = path.name
    ptype = detect_project_type(path)

    # Extension map for file scanning
    ext_map = {
        "rust": [".rs"],
        "node": [".ts", ".tsx", ".js", ".jsx"],
        "python": [".py"],
        "tauri": [".rs", ".ts", ".vue"],
        "unknown": [".py", ".rs", ".ts", ".js"]
    }

    extensions = ext_map.get(ptype, ext_map["unknown"])

    project = {
        "name": name,
        "path": str(path),
        "type": ptype,
        "git": get_git_info(path),
        "recent_files": get_recent_files(path, extensions),
        "running_services": check_running_services(name),
        "scanned_at": datetime.now().isoformat()
    }

    project["health"] = get_project_health(project)

    return project

def scan_all_projects() -> list:
    """Scan all project directories"""
    projects = []

    for root in PROJECT_ROOTS:
        if not root.exists():
            continue

        for item in root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Skip non-project directories
                if item.name in ['venvs', 'logs', 'samples', 'bin', 'VMs', 'analysis']:
                    continue

                project = scan_project(item)
                projects.append(project)

    return projects

def save_registry(projects: list):
    """Save registry to disk"""
    registry = {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "projects": projects
    }

    with open(REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)

    return REGISTRY_PATH

def load_registry() -> dict:
    """Load existing registry"""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return None

def get_summary() -> str:
    """Generate human-readable summary"""
    registry = load_registry()
    if not registry:
        return "No registry found. Run scan first."

    lines = [
        f"**Project Registry** (updated {registry['updated_at'][:16]})",
        ""
    ]

    # Group by health
    healthy = []
    needs_attention = []

    for p in registry['projects']:
        if p['health'] == 'healthy':
            healthy.append(p)
        else:
            needs_attention.append(p)

    if needs_attention:
        lines.append("**Needs Attention:**")
        for p in needs_attention:
            git = p.get('git') or {}
            changes = git.get('uncommitted_changes', 0)
            reason = f"{changes} uncommitted changes" if changes else p['health']
            lines.append(f"  • {p['name']} ({p['type']}) - {reason}")
        lines.append("")

    lines.append("**Active Projects:**")
    for p in sorted(registry['projects'], key=lambda x: (x.get('git') or {}).get('last_commit_time', 'zzz')):
        git = p.get('git', {})
        if git and 'last_commit_time' in git:
            lines.append(f"  • {p['name']} - last commit {git['last_commit_time']}")
            if p['running_services']:
                lines.append(f"    └ Running: {len(p['running_services'])} process(es)")

    return '\n'.join(lines)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        print(get_summary())
    else:
        print("Scanning projects...")
        projects = scan_all_projects()
        path = save_registry(projects)
        print(f"Saved {len(projects)} projects to {path}")
        print()
        print(get_summary())
