#!/usr/bin/env python3
"""
SAM Brain Autonomous Improvement Daemon
Continuously cycles through projects, analyzing and improving them.

GUARDRAILS:
- No deleting without approval
- No filling internal drive (outputs to external)
- Disk space monitoring
- Approval queue for destructive operations
"""

import os
import sys
import json
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Configuration
REGISTRY_PATH = Path.home() / ".sam" / "projects" / "registry.json"
MLX_SERVER = "http://localhost:11435"
LOG_PATH = Path("/Volumes/Plex/SSOT/daemon.log")
APPROVAL_QUEUE = Path("/Volumes/Plex/SSOT/pending_approvals.json")
OUTPUT_DIR = Path("/Volumes/Plex/SSOT/outputs")
MIN_DISK_SPACE_GB = 10
CYCLE_INTERVAL_MINUTES = 30

# Dangerous commands that require approval
DANGEROUS_COMMANDS = ["rm", "delete", "remove", "drop", "truncate", "git push --force"]

# Safe commands that can run automatically (read-only or non-destructive)
SAFE_COMMANDS = [
    "lint", "flake8", "eslint", "pylint",  # Linting (read-only)
    "format", "prettier", "black",           # Formatting (can be auto-approved)
    "test", "pytest", "jest", "cargo test",  # Testing
    "build", "cargo build", "npm run build", # Building
    "audit", "npm audit",                    # Security audit (read-only)
    "check", "cargo check",                  # Type checking
    "docs", "cargo doc",                     # Documentation
    "git status", "git diff", "git log",     # Git read operations
    "git add", "git commit",                 # Git write (local only)
    "ls", "cat", "head", "tail", "wc",       # Read-only file ops
]


def log(message: str, level: str = "INFO"):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(log_line + "\n")


def check_disk_space() -> Dict[str, float]:
    """Check available disk space on internal and external drives."""
    spaces = {}

    # Internal drive
    internal = shutil.disk_usage(Path.home())
    spaces["internal_gb"] = internal.free / (1024**3)

    # External drives
    for mount in ["/Volumes/Plex", "/Volumes/Music", "/Volumes/David External"]:
        if Path(mount).exists():
            try:
                usage = shutil.disk_usage(mount)
                spaces[mount] = usage.free / (1024**3)
            except:
                pass

    return spaces


def is_internal_path(path: str) -> bool:
    """Check if path is on internal drive."""
    path = str(path)
    external_prefixes = ["/Volumes/"]
    return not any(path.startswith(p) for p in external_prefixes)


def load_registry() -> Dict:
    """Load project registry."""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {"projects": [], "config": {}, "guardrails": {}}


def query_sam_brain(prompt: str, max_tokens: int = 300) -> str:
    """Query the local SAM Brain MLX model."""
    import urllib.request
    import urllib.error

    try:
        data = json.dumps({
            "prompt": prompt,
            "options": {"num_predict": max_tokens}
        }).encode()

        req = urllib.request.Request(
            f"{MLX_SERVER}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            return result.get("response", "")
    except Exception as e:
        log(f"SAM Brain query failed: {e}", "ERROR")
        return ""


def is_command_safe(command: str) -> bool:
    """Check if a command is safe to execute automatically."""
    command_lower = command.lower()

    # Check for dangerous patterns
    for danger in DANGEROUS_COMMANDS:
        if danger in command_lower:
            return False

    # Check for safe patterns
    for safe in SAFE_COMMANDS:
        if safe in command_lower:
            return True

    # Default to requiring approval for unknown commands
    return False


def add_to_approval_queue(project_id: str, action: str, command: str, reason: str):
    """Add a destructive action to the approval queue."""
    queue = []
    if APPROVAL_QUEUE.exists():
        with open(APPROVAL_QUEUE) as f:
            queue = json.load(f)

    queue.append({
        "id": f"{project_id}_{int(time.time())}",
        "project": project_id,
        "action": action,
        "command": command,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    })

    APPROVAL_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with open(APPROVAL_QUEUE, "w") as f:
        json.dump(queue, f, indent=2)

    log(f"Added to approval queue: {action} for {project_id}", "APPROVAL")


def execute_safe_command(command: str, cwd: str) -> Dict:
    """Execute a safe command and return result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:2000],  # Limit output
            "stderr": result.stderr[:500],
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_project(project: Dict) -> Dict:
    """Analyze a project and determine improvement actions."""
    project_path = project.get("path", "")
    project_id = project.get("id", "")

    if not Path(project_path).exists():
        return {"status": "missing", "actions": []}

    analysis = {
        "status": "analyzed",
        "actions": [],
        "issues": [],
        "suggestions": []
    }

    # Check for common project files
    path = Path(project_path)

    # Git status
    if (path / ".git").exists():
        result = execute_safe_command("git status --porcelain", project_path)
        if result.get("success"):
            changes = len(result.get("stdout", "").strip().split("\n"))
            if changes > 0 and result.get("stdout").strip():
                analysis["issues"].append(f"{changes} uncommitted changes")

    # Python projects
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        # Check for lint issues
        analysis["actions"].append({
            "type": "lint",
            "command": "python3 -m flake8 --count --select=E9,F63,F7,F82 --show-source --statistics . 2>/dev/null || true",
            "safe": True
        })

    # Node projects
    if (path / "package.json").exists():
        # Check for outdated packages
        analysis["actions"].append({
            "type": "audit",
            "command": "npm audit --json 2>/dev/null | head -50 || true",
            "safe": True
        })

    # Rust projects
    if (path / "Cargo.toml").exists():
        analysis["actions"].append({
            "type": "check",
            "command": "cargo check 2>&1 | tail -20 || true",
            "safe": True
        })

    # Ask SAM Brain for suggestions
    prompt = f"""Analyze this project and suggest ONE specific improvement:
Project: {project.get('name')}
Path: {project_path}
Status: {project.get('status')}
Issues: {', '.join(analysis['issues']) or 'None detected'}

Respond with a single actionable task (one sentence, no commands)."""

    suggestion = query_sam_brain(prompt, 100)
    if suggestion:
        analysis["suggestions"].append(suggestion.strip())

    return analysis


def process_project(project: Dict) -> Dict:
    """Process a single project through the improvement cycle."""
    project_id = project.get("id", "")
    project_path = project.get("path", "")

    log(f"Processing: {project.get('name')} ({project_id})")

    # Check disk space first
    spaces = check_disk_space()
    if spaces.get("internal_gb", 0) < MIN_DISK_SPACE_GB:
        log(f"LOW DISK SPACE: {spaces.get('internal_gb', 0):.1f}GB - skipping write operations", "WARN")
        return {"status": "skipped", "reason": "low disk space"}

    # Analyze project
    analysis = analyze_project(project)

    results = {
        "project_id": project_id,
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis,
        "actions_taken": [],
        "approvals_needed": []
    }

    # Execute safe actions
    for action in analysis.get("actions", []):
        if action.get("safe") and is_command_safe(action.get("command", "")):
            result = execute_safe_command(action["command"], project_path)
            results["actions_taken"].append({
                "type": action["type"],
                "success": result.get("success"),
                "output": result.get("stdout", "")[:500]
            })
        else:
            # Add to approval queue
            add_to_approval_queue(
                project_id,
                action.get("type"),
                action.get("command"),
                "Requires manual approval"
            )
            results["approvals_needed"].append(action)

    # Log suggestions
    for suggestion in analysis.get("suggestions", []):
        log(f"  Suggestion for {project_id}: {suggestion}")

    return results


def run_improvement_cycle():
    """Run one complete improvement cycle through all projects."""
    log("=" * 60)
    log("Starting improvement cycle")
    log("=" * 60)

    registry = load_registry()
    projects = registry.get("projects", [])

    # Sort by priority
    projects.sort(key=lambda p: p.get("priority", 99))

    cycle_results = {
        "timestamp": datetime.now().isoformat(),
        "projects_processed": 0,
        "actions_taken": 0,
        "approvals_needed": 0,
        "results": []
    }

    for project in projects:
        if project.get("status") in ["planned", "archived"]:
            continue

        try:
            result = process_project(project)
            cycle_results["results"].append(result)
            cycle_results["projects_processed"] += 1
            cycle_results["actions_taken"] += len(result.get("actions_taken", []))
            cycle_results["approvals_needed"] += len(result.get("approvals_needed", []))
        except Exception as e:
            log(f"Error processing {project.get('id')}: {e}", "ERROR")

    # Save cycle results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_file = OUTPUT_DIR / f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(cycle_results, f, indent=2)

    log(f"Cycle complete: {cycle_results['projects_processed']} projects, "
        f"{cycle_results['actions_taken']} actions, "
        f"{cycle_results['approvals_needed']} pending approvals")

    return cycle_results


def daemon_loop():
    """Main daemon loop - runs continuously."""
    log("=" * 60)
    log("SAM Brain Autonomous Daemon Starting")
    log(f"Cycle interval: {CYCLE_INTERVAL_MINUTES} minutes")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Approval queue: {APPROVAL_QUEUE}")
    log("=" * 60)

    # Initial disk space check
    spaces = check_disk_space()
    log(f"Disk space - Internal: {spaces.get('internal_gb', 0):.1f}GB, "
        f"Plex: {spaces.get('/Volumes/Plex', 0):.1f}GB")

    while True:
        try:
            run_improvement_cycle()
        except Exception as e:
            log(f"Cycle error: {e}", "ERROR")

        log(f"Sleeping for {CYCLE_INTERVAL_MINUTES} minutes...")
        time.sleep(CYCLE_INTERVAL_MINUTES * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Brain Autonomous Daemon")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--project", type=str, help="Process single project by ID")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    args = parser.parse_args()

    if args.status:
        registry = load_registry()
        projects = registry.get("projects", [])
        print(f"\nProjects: {len(projects)}")
        for p in projects:
            print(f"  [{p.get('priority', '?')}] {p.get('name')} - {p.get('status')}")

        spaces = check_disk_space()
        print(f"\nDisk space:")
        for drive, gb in spaces.items():
            print(f"  {drive}: {gb:.1f} GB free")

        if APPROVAL_QUEUE.exists():
            with open(APPROVAL_QUEUE) as f:
                queue = json.load(f)
            pending = [a for a in queue if a.get("status") == "pending"]
            print(f"\nPending approvals: {len(pending)}")
        return

    if args.project:
        registry = load_registry()
        project = next((p for p in registry.get("projects", []) if p.get("id") == args.project), None)
        if project:
            result = process_project(project)
            print(json.dumps(result, indent=2))
        else:
            print(f"Project not found: {args.project}")
        return

    if args.once:
        run_improvement_cycle()
    else:
        daemon_loop()


if __name__ == "__main__":
    main()
