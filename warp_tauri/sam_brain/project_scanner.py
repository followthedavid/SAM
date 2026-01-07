#!/usr/bin/env python3
"""
SAM Project Scanner - Discovers and catalogs all projects across drives

Scans for:
- Python projects (setup.py, pyproject.toml, requirements.txt)
- Rust projects (Cargo.toml)
- Node projects (package.json)
- Git repositories
- Unity/Unreal projects
- Generic code directories

Outputs to projects_discovered.json with metadata.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

# Configuration
OUTPUT_FILE = Path(__file__).parent / "projects_discovered.json"
SCAN_PATHS = [
    Path.home() / "Projects",
    Path.home() / "ReverseLab",
    Path.home() / "ai-studio",
    Path("/Volumes/Plex"),
    Path("/Volumes/David External"),
    Path("/Volumes/Games"),
    Path("/Volumes/#1"),
    Path("/Volumes/# 2"),
    Path("/Volumes/Music"),
]

# Project indicators
PROJECT_MARKERS = {
    "python": ["setup.py", "pyproject.toml", "requirements.txt", "__init__.py"],
    "rust": ["Cargo.toml"],
    "node": ["package.json"],
    "tauri": ["tauri.conf.json"],
    "unity": ["ProjectSettings/ProjectVersion.txt", "Assets"],
    "unreal": [".uproject"],
    "git": [".git"],
    "docker": ["docker-compose.yml", "Dockerfile"],
    "go": ["go.mod"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle"],
}

# Skip patterns
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".cache", "cache", "Cache", ".Trash", "Library",
    "site-packages", "dist", "build", ".eggs", "target",
    "Pods", "DerivedData", ".gradle", ".idea", ".vs"
}

SKIP_PATHS = {
    "/Volumes/Plex/DevSymlinks/cargo_registry",
    "/Volumes/Plex/DevSymlinks/homebrew_cache",
    "/Volumes/Plex/DevSymlinks/huggingface",
}


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    path_str = str(path)

    # Skip specific paths
    for skip in SKIP_PATHS:
        if path_str.startswith(skip):
            return True

    # Skip hidden directories (except .git which we detect)
    if any(part.startswith('.') and part != '.git' for part in path.parts):
        return True

    return False


def detect_project_type(path: Path) -> Optional[Dict]:
    """Detect project type and gather metadata."""
    if not path.is_dir():
        return None

    project_types = []

    for ptype, markers in PROJECT_MARKERS.items():
        for marker in markers:
            marker_path = path / marker
            if marker_path.exists():
                project_types.append(ptype)
                break

    if not project_types:
        # Check for code files as fallback
        code_extensions = {'.py', '.rs', '.js', '.ts', '.go', '.rb', '.java', '.swift'}
        has_code = False
        try:
            for item in path.iterdir():
                if item.is_file() and item.suffix in code_extensions:
                    has_code = True
                    break
        except PermissionError:
            return None

        if has_code:
            project_types = ["code"]
        else:
            return None

    # Gather metadata
    metadata = {
        "name": path.name,
        "path": str(path),
        "types": project_types,
        "discovered_at": datetime.now().isoformat(),
    }

    # Try to get description from README
    for readme in ["README.md", "README.txt", "README"]:
        readme_path = path / readme
        if readme_path.exists():
            try:
                content = readme_path.read_text(errors='ignore')[:500]
                # Extract first paragraph
                lines = content.split('\n')
                desc_lines = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        desc_lines.append(line.strip())
                        if len(' '.join(desc_lines)) > 100:
                            break
                metadata["description"] = ' '.join(desc_lines)[:200]
                break
            except:
                pass

    # Get git info if available
    git_dir = path / ".git"
    if git_dir.exists():
        try:
            config_file = git_dir / "config"
            if config_file.exists():
                content = config_file.read_text()
                for line in content.split('\n'):
                    if 'url = ' in line:
                        metadata["git_remote"] = line.split('url = ')[1].strip()
                        break
        except:
            pass

    # Get package info for node projects
    if "node" in project_types:
        pkg_file = path / "package.json"
        if pkg_file.exists():
            try:
                pkg = json.load(open(pkg_file))
                if "description" not in metadata and pkg.get("description"):
                    metadata["description"] = pkg["description"][:200]
                metadata["version"] = pkg.get("version")
            except:
                pass

    # Get cargo info for rust projects
    if "rust" in project_types:
        cargo_file = path / "Cargo.toml"
        if cargo_file.exists():
            try:
                content = cargo_file.read_text()
                for line in content.split('\n'):
                    if line.startswith('description'):
                        desc = line.split('=')[1].strip().strip('"\'')
                        if "description" not in metadata:
                            metadata["description"] = desc[:200]
                        break
            except:
                pass

    # Generate keywords from path and type
    keywords = set(project_types)
    keywords.add(path.name.lower())
    for part in path.parts[-3:]:
        if part and len(part) > 2:
            keywords.add(part.lower())
    metadata["keywords"] = list(keywords)

    return metadata


def scan_directory(base_path: Path, max_depth: int = 6) -> List[Dict]:
    """Recursively scan a directory for projects."""
    projects = []

    if not base_path.exists():
        return projects

    def scan(path: Path, depth: int):
        if depth > max_depth:
            return

        if should_skip(path):
            return

        # Check if this is a project
        project = detect_project_type(path)
        if project:
            projects.append(project)
            # Don't descend into detected projects (they may have subprojects but we got the main one)
            # Exception: monorepos
            if "node_modules" not in str(path) and depth < max_depth - 2:
                pass  # Continue scanning
            else:
                return

        # Scan subdirectories
        try:
            for item in path.iterdir():
                if item.is_dir() and item.name not in SKIP_DIRS:
                    scan(item, depth + 1)
        except PermissionError:
            pass
        except Exception as e:
            pass

    scan(base_path, 0)
    return projects


def main():
    print("SAM Project Scanner")
    print("=" * 60)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Scanning {len(SCAN_PATHS)} locations...")
    print()

    all_projects = []
    seen_paths = set()

    for scan_path in SCAN_PATHS:
        if not scan_path.exists():
            print(f"  Skipping (not mounted): {scan_path}")
            continue

        print(f"  Scanning: {scan_path}")
        projects = scan_directory(scan_path)

        # Deduplicate
        for p in projects:
            if p["path"] not in seen_paths:
                seen_paths.add(p["path"])
                all_projects.append(p)

        print(f"    Found {len(projects)} projects")

    # Sort by path
    all_projects.sort(key=lambda x: x["path"])

    # Save results
    output = {
        "scan_date": datetime.now().isoformat(),
        "total_projects": len(all_projects),
        "scan_paths": [str(p) for p in SCAN_PATHS],
        "projects": all_projects
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Total projects discovered: {len(all_projects)}")
    print(f"Results saved to: {OUTPUT_FILE}")

    # Print summary by type
    type_counts = {}
    for p in all_projects:
        for t in p.get("types", []):
            type_counts[t] = type_counts.get(t, 0) + 1

    print()
    print("By type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
