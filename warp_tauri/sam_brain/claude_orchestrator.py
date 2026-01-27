#!/usr/bin/env python3
"""
Claude Orchestrator for SAM
===========================

This system allows Claude to direct SAM to improve projects:
1. Claude analyzes project and creates task list
2. SAM executes tasks locally (free, fast)
3. Claude reviews results and iterates

Usage:
  # From Claude Code, create a task file:
  claude_orchestrator.py create-task "Refactor the authentication module"

  # SAM executes tasks:
  claude_orchestrator.py run-tasks

  # Check results:
  claude_orchestrator.py status
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Paths
TASKS_DIR = Path.home() / ".sam" / "orchestrator"
TASKS_FILE = TASKS_DIR / "tasks.json"
RESULTS_FILE = TASKS_DIR / "results.json"
PROJECTS_FILE = TASKS_DIR / "projects.json"

TASKS_DIR.mkdir(parents=True, exist_ok=True)

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"

class TaskType(Enum):
    CODE_CHANGE = "code_change"      # Modify existing code
    CREATE_FILE = "create_file"       # Create new file
    DELETE_FILE = "delete_file"       # Delete file
    RUN_COMMAND = "run_command"       # Execute shell command
    ANALYZE = "analyze"               # Analyze and report (no changes)
    RESEARCH = "research"             # Search/read files

@dataclass
class Task:
    id: str
    type: TaskType
    description: str
    project_path: str
    target_file: Optional[str] = None
    instructions: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self):
        d = asdict(self)
        d['type'] = self.type.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d):
        d['type'] = TaskType(d['type'])
        d['status'] = TaskStatus(d['status'])
        return cls(**d)

def load_tasks() -> List[Task]:
    if TASKS_FILE.exists():
        try:
            data = json.loads(TASKS_FILE.read_text())
            return [Task.from_dict(t) for t in data]
        except:
            return []
    return []

def save_tasks(tasks: List[Task]):
    TASKS_FILE.write_text(json.dumps([t.to_dict() for t in tasks], indent=2))

def generate_task_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]

# =============================================================================
# CLAUDE'S INTERFACE - Create tasks for SAM
# =============================================================================

def create_task(
    task_type: str,
    description: str,
    project_path: str,
    target_file: Optional[str] = None,
    instructions: str = ""
) -> str:
    """Claude calls this to create a task for SAM."""
    tasks = load_tasks()

    task = Task(
        id=generate_task_id(),
        type=TaskType(task_type),
        description=description,
        project_path=project_path,
        target_file=target_file,
        instructions=instructions,
        status=TaskStatus.PENDING,
        created_at=datetime.now().isoformat()
    )

    tasks.append(task)
    save_tasks(tasks)

    return f"Task {task.id} created: {description}"

def create_improvement_plan(project_path: str, improvements: List[Dict]) -> str:
    """
    Claude calls this to create multiple improvement tasks at once.

    improvements = [
        {"type": "code_change", "file": "src/auth.py", "description": "Add input validation", "instructions": "..."},
        {"type": "create_file", "file": "tests/test_auth.py", "description": "Add auth tests", "instructions": "..."},
    ]
    """
    tasks = load_tasks()
    created = []

    for imp in improvements:
        task = Task(
            id=generate_task_id(),
            type=TaskType(imp.get("type", "code_change")),
            description=imp["description"],
            project_path=project_path,
            target_file=imp.get("file"),
            instructions=imp.get("instructions", ""),
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        tasks.append(task)
        created.append(task.id)

    save_tasks(tasks)
    return f"Created {len(created)} tasks: {', '.join(created)}"

# =============================================================================
# SAM'S INTERFACE - Execute tasks
# =============================================================================

def execute_task(task: Task) -> Task:
    """SAM executes a single task."""
    task.status = TaskStatus.IN_PROGRESS

    try:
        # Import SAM's brain
        sys.path.insert(0, str(Path(__file__).parent))
        from escalation_handler import process_request

        # Build prompt based on task type
        if task.type == TaskType.CODE_CHANGE:
            prompt = f"""You are modifying the file: {task.target_file}
Project: {task.project_path}

Task: {task.description}

Instructions:
{task.instructions}

Please provide the exact code changes needed. Show the complete modified sections."""

        elif task.type == TaskType.CREATE_FILE:
            prompt = f"""Create a new file: {task.target_file}
Project: {task.project_path}

Task: {task.description}

Instructions:
{task.instructions}

Provide the complete file contents."""

        elif task.type == TaskType.RUN_COMMAND:
            prompt = f"""Execute this task in project: {task.project_path}

Task: {task.description}

Instructions:
{task.instructions}

What command should be run? Provide the exact command."""

        elif task.type == TaskType.ANALYZE:
            prompt = f"""Analyze the project: {task.project_path}

Focus on: {task.description}

Instructions:
{task.instructions}

Provide your analysis."""

        elif task.type == TaskType.RESEARCH:
            prompt = f"""Research in project: {task.project_path}

Looking for: {task.description}

Instructions:
{task.instructions}

Report what you find."""

        else:
            prompt = f"{task.description}\n\n{task.instructions}"

        # Execute via SAM
        result = process_request(prompt, auto_escalate=False)

        task.result = result.content
        task.status = TaskStatus.NEEDS_REVIEW
        task.completed_at = datetime.now().isoformat()

        # If SAM had low confidence, mark for review
        if result.confidence < 0.5:
            task.result = f"[LOW CONFIDENCE: {result.confidence:.0%}]\n\n{result.content}"

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.result = f"Error: {str(e)}"
        task.completed_at = datetime.now().isoformat()

    return task

def run_pending_tasks(max_tasks: int = 5) -> List[Task]:
    """SAM runs pending tasks."""
    tasks = load_tasks()
    pending = [t for t in tasks if t.status == TaskStatus.PENDING]

    results = []
    for task in pending[:max_tasks]:
        print(f"[SAM] Executing task {task.id}: {task.description[:50]}...")
        task = execute_task(task)
        results.append(task)

        # Update task list
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                break

    save_tasks(tasks)
    return results

# =============================================================================
# STATUS & REVIEW
# =============================================================================

def get_status() -> Dict:
    """Get current orchestrator status."""
    tasks = load_tasks()

    status = {
        "total": len(tasks),
        "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "needs_review": len([t for t in tasks if t.status == TaskStatus.NEEDS_REVIEW]),
        "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
    }

    return status

def get_tasks_for_review() -> List[Task]:
    """Get tasks that need Claude's review."""
    tasks = load_tasks()
    return [t for t in tasks if t.status == TaskStatus.NEEDS_REVIEW]

def approve_task(task_id: str) -> str:
    """Claude approves a task result."""
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            task.status = TaskStatus.COMPLETED
            save_tasks(tasks)
            return f"Task {task_id} approved and marked complete"
    return f"Task {task_id} not found"

def reject_task(task_id: str, feedback: str) -> str:
    """Claude rejects a task with feedback for retry."""
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            task.status = TaskStatus.PENDING
            task.instructions += f"\n\n[FEEDBACK FROM REVIEW]: {feedback}"
            save_tasks(tasks)
            return f"Task {task_id} returned to pending with feedback"
    return f"Task {task_id} not found"

def clear_completed():
    """Clear completed tasks from the list."""
    tasks = load_tasks()
    tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
    save_tasks(tasks)
    return f"Cleared completed tasks. {len(tasks)} remaining."

# =============================================================================
# CLI
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("""
Claude Orchestrator for SAM
===========================

Commands:
  status                              Show task status
  run-tasks [max]                     SAM runs pending tasks
  review                              Show tasks needing review
  approve <task_id>                   Approve a task
  reject <task_id> "<feedback>"       Reject with feedback
  clear                               Clear completed tasks

For Claude to create tasks:
  create <type> "<desc>" <project> [file] [instructions]

Task types: code_change, create_file, delete_file, run_command, analyze, research

Example workflow:
  1. Claude analyzes project, creates tasks via create_improvement_plan()
  2. SAM runs: orchestrator.py run-tasks
  3. Claude reviews: orchestrator.py review
  4. Claude approves/rejects each task
  5. Repeat until all tasks complete
""")
        return

    cmd = sys.argv[1]

    if cmd == "status":
        status = get_status()
        print(json.dumps(status, indent=2))

    elif cmd == "run-tasks":
        max_tasks = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        results = run_pending_tasks(max_tasks)
        print(f"\nExecuted {len(results)} tasks:")
        for t in results:
            print(f"  [{t.status.value}] {t.id}: {t.description[:40]}...")

    elif cmd == "review":
        tasks = get_tasks_for_review()
        if not tasks:
            print("No tasks need review")
        else:
            for t in tasks:
                print(f"\n{'='*60}")
                print(f"Task: {t.id}")
                print(f"Type: {t.type.value}")
                print(f"Description: {t.description}")
                print(f"File: {t.target_file or 'N/A'}")
                print(f"\nResult:\n{t.result[:500]}...")
                print(f"{'='*60}")

    elif cmd == "approve" and len(sys.argv) > 2:
        result = approve_task(sys.argv[2])
        print(result)

    elif cmd == "reject" and len(sys.argv) > 3:
        result = reject_task(sys.argv[2], sys.argv[3])
        print(result)

    elif cmd == "clear":
        result = clear_completed()
        print(result)

    elif cmd == "create" and len(sys.argv) >= 5:
        task_type = sys.argv[2]
        description = sys.argv[3]
        project = sys.argv[4]
        target_file = sys.argv[5] if len(sys.argv) > 5 else None
        instructions = sys.argv[6] if len(sys.argv) > 6 else ""

        result = create_task(task_type, description, project, target_file, instructions)
        print(result)

    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
