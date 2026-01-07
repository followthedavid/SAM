#!/usr/bin/env python3
"""
SAM Daemon - Background service for nightly automation tasks

Tasks:
- Project re-scanning (discover new projects)
- Training data cleanup (remove old entries)
- Memory optimization (archive old interactions)
- Health checks (verify Ollama, disk space, etc.)

Usage:
  sam_daemon.py start     - Start daemon in foreground
  sam_daemon.py schedule  - Show scheduled tasks
  sam_daemon.py run <task> - Run specific task now
  sam_daemon.py status    - Show daemon status
"""

import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
import threading

SCRIPT_DIR = Path(__file__).parent
PID_FILE = SCRIPT_DIR / ".sam_daemon.pid"
LOG_FILE = SCRIPT_DIR / "daemon.log"
STATE_FILE = SCRIPT_DIR / ".daemon_state.json"

# Task definitions
TASKS = {
    "scan_projects": {
        "description": "Scan for new projects",
        "interval_hours": 24,
        "script": "project_scanner.py"
    },
    "export_projects": {
        "description": "Export quality projects to SAM",
        "interval_hours": 24,
        "script": "project_manager.py",
        "args": ["export"]
    },
    "cleanup_memory": {
        "description": "Archive old interactions",
        "interval_hours": 168,  # Weekly
        "function": "cleanup_memory"
    },
    "cleanup_training": {
        "description": "Remove stale training data",
        "interval_hours": 168,  # Weekly
        "function": "cleanup_training"
    },
    "health_check": {
        "description": "Check system health",
        "interval_hours": 1,
        "function": "health_check"
    },
    "update_stats": {
        "description": "Update usage statistics",
        "interval_hours": 6,
        "function": "update_stats"
    }
}


def log(message: str):
    """Log to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_state() -> dict:
    """Load daemon state."""
    if STATE_FILE.exists():
        try:
            return json.load(open(STATE_FILE))
        except:
            pass
    return {"last_run": {}, "stats": {}}


def save_state(state: dict):
    """Save daemon state."""
    json.dump(state, open(STATE_FILE, "w"), indent=2, default=str)


# Task implementations

def cleanup_memory():
    """Archive old interactions to keep memory.json small."""
    memory_file = SCRIPT_DIR / "memory.json"
    archive_file = SCRIPT_DIR / "memory_archive.json"

    if not memory_file.exists():
        return "No memory file"

    memory = json.load(open(memory_file))
    interactions = memory.get("interactions", [])

    if len(interactions) <= 100:
        return f"Memory OK ({len(interactions)} interactions)"

    # Keep last 100, archive the rest
    to_archive = interactions[:-100]
    memory["interactions"] = interactions[-100:]

    # Load or create archive
    archive = {"interactions": []}
    if archive_file.exists():
        archive = json.load(open(archive_file))

    archive["interactions"].extend(to_archive)
    archive["archived_at"] = datetime.now().isoformat()

    json.dump(memory, open(memory_file, "w"), indent=2)
    json.dump(archive, open(archive_file, "w"), indent=2)

    return f"Archived {len(to_archive)} interactions"


def cleanup_training():
    """Remove old training data entries."""
    training_file = SCRIPT_DIR / "training_data.jsonl"

    if not training_file.exists():
        return "No training data"

    lines = training_file.read_text().strip().split("\n")
    original_count = len(lines)

    # Keep only last 1000 entries
    if len(lines) > 1000:
        lines = lines[-1000:]
        training_file.write_text("\n".join(lines) + "\n")
        return f"Trimmed {original_count - len(lines)} old training entries"

    return f"Training data OK ({len(lines)} entries)"


def health_check() -> str:
    """Check system health."""
    results = []

    # Check Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            results.append("Ollama: OK")
        else:
            results.append("Ollama: DOWN")
    except:
        results.append("Ollama: ERROR")

    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage(SCRIPT_DIR)
        free_gb = free / (1024**3)
        if free_gb < 10:
            results.append(f"Disk: LOW ({free_gb:.1f}GB free)")
        else:
            results.append(f"Disk: OK ({free_gb:.1f}GB free)")
    except:
        results.append("Disk: ERROR")

    # Check project count
    projects_file = SCRIPT_DIR / "projects.json"
    if projects_file.exists():
        data = json.load(open(projects_file))
        count = len(data.get("projects", []))
        results.append(f"Projects: {count}")

    return ", ".join(results)


def update_stats():
    """Update usage statistics."""
    stats_file = SCRIPT_DIR / "stats.json"
    memory_file = SCRIPT_DIR / "memory.json"
    training_file = SCRIPT_DIR / "training_data.jsonl"

    stats = {
        "updated_at": datetime.now().isoformat(),
        "memory_interactions": 0,
        "training_entries": 0,
        "projects": 0,
        "discovered_projects": 0
    }

    if memory_file.exists():
        memory = json.load(open(memory_file))
        stats["memory_interactions"] = len(memory.get("interactions", []))

    if training_file.exists():
        stats["training_entries"] = len(training_file.read_text().strip().split("\n"))

    projects_file = SCRIPT_DIR / "projects.json"
    if projects_file.exists():
        data = json.load(open(projects_file))
        stats["projects"] = len(data.get("projects", []))

    discovered_file = SCRIPT_DIR / "projects_discovered.json"
    if discovered_file.exists():
        data = json.load(open(discovered_file))
        stats["discovered_projects"] = len(data.get("projects", []))

    json.dump(stats, open(stats_file, "w"), indent=2)
    return f"Stats updated: {stats['memory_interactions']} interactions, {stats['projects']} projects"


def run_task(task_name: str) -> str:
    """Run a specific task."""
    if task_name not in TASKS:
        return f"Unknown task: {task_name}"

    task = TASKS[task_name]
    log(f"Running task: {task_name}")

    try:
        if "function" in task:
            # Run internal function
            func = globals().get(task["function"])
            if func:
                result = func()
            else:
                result = f"Function not found: {task['function']}"
        elif "script" in task:
            # Run external script
            script_path = SCRIPT_DIR / task["script"]
            args = ["python3", str(script_path)] + task.get("args", [])
            proc = subprocess.run(args, capture_output=True, text=True, timeout=300)
            result = proc.stdout.strip() or proc.stderr.strip() or "OK"
        else:
            result = "No handler defined"

        log(f"Task {task_name} completed: {result[:100]}")
        return result

    except Exception as e:
        log(f"Task {task_name} failed: {e}")
        return f"Error: {e}"


def should_run_task(task_name: str, state: dict) -> bool:
    """Check if task should run based on interval."""
    task = TASKS[task_name]
    last_run = state["last_run"].get(task_name)

    if not last_run:
        return True

    try:
        last_time = datetime.fromisoformat(last_run)
        interval = timedelta(hours=task["interval_hours"])
        return datetime.now() - last_time >= interval
    except:
        return True


def daemon_loop():
    """Main daemon loop."""
    log("SAM Daemon started")
    state = load_state()

    # Write PID
    PID_FILE.write_text(str(os.getpid()))

    def shutdown(signum, frame):
        log("Daemon shutting down")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    check_interval = 300  # Check every 5 minutes

    while True:
        for task_name in TASKS:
            if should_run_task(task_name, state):
                result = run_task(task_name)
                state["last_run"][task_name] = datetime.now().isoformat()
                state["stats"][task_name] = {
                    "last_result": result[:200],
                    "last_run": datetime.now().isoformat()
                }
                save_state(state)

        time.sleep(check_interval)


def cmd_start():
    """Start daemon."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text())
        try:
            os.kill(pid, 0)
            print(f"Daemon already running (PID {pid})")
            return
        except:
            pass  # Process doesn't exist

    print("Starting SAM daemon...")
    daemon_loop()


def cmd_schedule():
    """Show scheduled tasks."""
    state = load_state()

    print("SAM Daemon Tasks")
    print("-" * 70)

    for name, task in TASKS.items():
        last_run = state["last_run"].get(name, "Never")
        if last_run != "Never":
            try:
                last_time = datetime.fromisoformat(last_run)
                next_run = last_time + timedelta(hours=task["interval_hours"])
                next_str = next_run.strftime("%Y-%m-%d %H:%M")
            except:
                next_str = "Unknown"
        else:
            next_str = "ASAP"

        print(f"{name:20} every {task['interval_hours']:3}h | Last: {str(last_run)[:19]} | Next: {next_str}")
        print(f"  {task['description']}")


def cmd_status():
    """Show daemon status."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text())
        try:
            os.kill(pid, 0)
            print(f"Daemon running (PID {pid})")
        except:
            print("Daemon not running (stale PID file)")
    else:
        print("Daemon not running")

    print()

    # Show last task results
    state = load_state()
    if state.get("stats"):
        print("Recent task results:")
        for name, info in state["stats"].items():
            print(f"  {name}: {info.get('last_result', 'N/A')[:50]}")


def cmd_run(task_name: str):
    """Run a specific task."""
    result = run_task(task_name)
    print(f"Result: {result}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "start":
        cmd_start()
    elif cmd == "schedule":
        cmd_schedule()
    elif cmd == "status":
        cmd_status()
    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: sam_daemon.py run <task>")
            print(f"Tasks: {', '.join(TASKS.keys())}")
            return
        cmd_run(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
