#!/usr/bin/env python3
"""
Auto Coordinator - Transparent Multi-Terminal Coordination

Makes terminal coordination completely invisible. Just import this module
and everything happens automatically:
- Auto-registers on import
- Auto-broadcasts tasks by parsing Claude Code output
- Auto-checks conflicts before starting work
- Auto-shares context between terminals
- Auto-cleans up on exit

Usage:
    # Just import - that's it!
    import auto_coordinator

    # Or for SAM integration, the orchestrator imports this automatically

For Claude Code integration, add to CLAUDE.md:
    ## Terminal Coordination
    This project uses auto_coordinator.py for multi-terminal awareness.
    Before starting major work, SAM checks if other terminals are already on it.
"""

import os
import sys
import re
import atexit
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

# Import our coordination system
from do.terminal_coordination import TerminalCoordinator, TerminalStatus


class AutoCoordinator:
    """
    Transparent coordination that requires zero manual intervention.

    Auto-detects:
    - Terminal type (Claude Code, SAM, custom)
    - Current working directory (as project context)
    - Git branch (if available)
    - Active files being edited

    Auto-broadcasts:
    - Task descriptions parsed from commands
    - File modifications
    - Git operations
    """

    _instance: Optional['AutoCoordinator'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton - only one coordinator per terminal."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.coordinator = TerminalCoordinator()
        self.session = None
        self.current_task_id = None
        self._heartbeat_thread = None
        self._stop_heartbeat = threading.Event()

        # Auto-register
        self._auto_register()

        # Start heartbeat
        self._start_heartbeat()

        # Register cleanup on exit
        atexit.register(self._cleanup)

    def _detect_terminal_type(self) -> str:
        """Detect what kind of terminal we're running in."""
        # Check for Claude Code indicators
        if os.environ.get('CLAUDE_CODE'):
            return "claude-code"

        # Check parent process
        try:
            import psutil
            parent = psutil.Process(os.getppid())
            parent_name = parent.name().lower()

            if 'claude' in parent_name:
                return "claude-code"
            if 'warp' in parent_name:
                return "warp"
            if 'sam' in parent_name or 'python' in parent_name:
                # Check if SAM is in the command line
                cmdline = ' '.join(parent.cmdline()).lower()
                if 'sam' in cmdline:
                    return "sam"
        except Exception:
            pass

        # Check for SAM environment
        if 'SAM_BRAIN' in os.environ or Path.cwd().name == 'sam_brain':
            return "sam"

        return "terminal"

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch if in a repo."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _get_project_name(self) -> str:
        """Get project name from current directory or git."""
        cwd = Path.cwd()

        # Check for common project files
        for marker in ['.git', 'package.json', 'Cargo.toml', 'pyproject.toml', 'setup.py']:
            if (cwd / marker).exists():
                return cwd.name

        # Walk up to find project root
        for parent in cwd.parents:
            for marker in ['.git', 'package.json', 'Cargo.toml']:
                if (parent / marker).exists():
                    return parent.name

        return cwd.name

    def _auto_register(self):
        """Automatically register this terminal."""
        terminal_type = self._detect_terminal_type()
        project = self._get_project_name()
        branch = self._get_git_branch()

        tags = [f"project:{project}"]
        if branch:
            tags.append(f"branch:{branch}")

        self.session = self.coordinator.register_terminal(
            terminal_type=terminal_type,
            tags=tags
        )

        # Set shared context
        self.coordinator.set_shared_context(
            "project", project, self.session.id
        )
        if branch:
            self.coordinator.set_shared_context(
                "branch", branch, self.session.id
            )

    def _start_heartbeat(self):
        """Start background heartbeat thread."""
        def heartbeat_loop():
            while not self._stop_heartbeat.wait(5):
                if self.session:
                    self.coordinator.heartbeat(self.session.id)

        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _cleanup(self):
        """Cleanup on exit."""
        self._stop_heartbeat.set()
        if self.session:
            self.coordinator.disconnect(self.session.id)

    # =========================================================================
    # Public API - Use these for explicit coordination when needed
    # =========================================================================

    def start_task(self, description: str, files: Optional[List[str]] = None) -> str:
        """
        Explicitly start a task. Usually auto-detected, but can be called manually.

        Returns task_id or raises ConflictError if someone else is on it.
        """
        # Check for conflicts first
        conflicts = self.coordinator.check_conflicts(description, exclude_session=self.session.id)

        if conflicts:
            # Someone else is working on this
            conflict_info = conflicts[0]
            raise ConflictError(
                f"Terminal [{conflict_info['session_id']}] ({conflict_info['terminal_type']}) "
                f"is already working on: {conflict_info['task']}"
            )

        # Broadcast task
        self.current_task_id = self.coordinator.broadcast_task(
            self.session.id,
            description,
            files=files
        )

        return self.current_task_id

    def finish_task(self):
        """Mark current task as complete."""
        if self.current_task_id:
            self.coordinator.complete_task(self.current_task_id, self.session.id)
            self.current_task_id = None

    def check_conflicts(self, description: str) -> List[Dict]:
        """Check if anyone is already working on this."""
        return self.coordinator.check_conflicts(description, exclude_session=self.session.id)

    def get_status(self) -> Dict:
        """Get status of all terminals (what SAM sees)."""
        return self.coordinator.get_global_context()

    def wait_for_others(self, task_keywords: List[str], timeout: int = 60) -> bool:
        """
        Wait for other terminals working on related tasks to finish.

        Returns True if all cleared, False if timeout.
        """
        for keyword in task_keywords:
            conflicts = self.check_conflicts(keyword)
            for conflict in conflicts:
                success = self.coordinator.wait_for(
                    self.session.id,
                    conflict['session_id'],
                    timeout=timeout
                )
                if not success:
                    return False
        return True

    @contextmanager
    def task(self, description: str, files: Optional[List[str]] = None):
        """
        Context manager for tasks - auto-broadcasts and completes.

        Usage:
            with auto_coord.task("Implementing auth"):
                # do work
                pass
            # Auto-completed when exiting
        """
        task_id = self.start_task(description, files)
        try:
            yield task_id
        finally:
            self.finish_task()

    # =========================================================================
    # Claude Code Integration Helpers
    # =========================================================================

    def parse_claude_output(self, output: str) -> Optional[str]:
        """
        Parse Claude Code output to detect tasks.

        Looks for patterns like:
        - "I'll implement X"
        - "Let me work on Y"
        - "Creating Z"
        - Todo list items
        """
        patterns = [
            r"(?:I'll|I will|Let me|I'm going to)\s+(?:implement|work on|create|fix|update|add|build)\s+(.+?)(?:\.|$)",
            r"(?:Working on|Implementing|Creating|Fixing|Adding)\s+(.+?)(?:\.|$)",
            r"(?:Task|TODO):\s+(.+?)(?:\.|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def auto_broadcast_from_output(self, output: str):
        """
        Automatically detect and broadcast tasks from Claude Code output.

        Call this in a hook that captures Claude's responses.
        """
        task = self.parse_claude_output(output)
        if task:
            try:
                self.start_task(task)
            except ConflictError:
                # Someone else is on it - let the user know
                pass


class ConflictError(Exception):
    """Raised when another terminal is already working on the same task."""
    pass


# =========================================================================
# Auto-initialize on import
# =========================================================================

# Global instance - created on import
_auto_coord: Optional[AutoCoordinator] = None


def get_coordinator() -> AutoCoordinator:
    """Get the auto-coordinator instance."""
    global _auto_coord
    if _auto_coord is None:
        _auto_coord = AutoCoordinator()
    return _auto_coord


# Convenience functions that delegate to the global coordinator
def start_task(description: str, files: Optional[List[str]] = None) -> str:
    return get_coordinator().start_task(description, files)

def finish_task():
    get_coordinator().finish_task()

def check_conflicts(description: str) -> List[Dict]:
    return get_coordinator().check_conflicts(description)

def get_status() -> Dict:
    return get_coordinator().get_status()

def wait_for_others(task_keywords: List[str], timeout: int = 60) -> bool:
    return get_coordinator().wait_for_others(task_keywords, timeout)


# =========================================================================
# Command Wrappers - Auto-coordinate common operations
# =========================================================================

def coordinated_git(cmd: str, args: List[str] = None):
    """
    Auto-coordinated git command.

    Broadcasts the operation, checks for conflicts on push/merge,
    and updates shared branch context.
    """
    import subprocess

    coord = get_coordinator()
    full_cmd = ['git', cmd] + (args or [])
    task_desc = f"git {cmd} {' '.join(args or [])}".strip()

    # Check conflicts for destructive operations
    if cmd in ['push', 'merge', 'rebase', 'reset', 'checkout']:
        conflicts = coord.check_conflicts(f"git {cmd}")
        if conflicts:
            print(f"Warning: {conflicts[0]['terminal_type']} is doing git operations")

    # Broadcast
    with coord.task(task_desc):
        result = subprocess.run(full_cmd, capture_output=True, text=True)

        # Update branch context if we switched
        if cmd in ['checkout', 'switch']:
            branch = coord._get_git_branch()
            if branch:
                coord.coordinator.set_shared_context("branch", branch, coord.session.id)

        return result


def coordinated_build(build_cmd: str = "npm run build"):
    """
    Auto-coordinated build command.

    Only one terminal builds at a time.
    """
    import subprocess

    coord = get_coordinator()

    # Wait for any other builds
    conflicts = coord.check_conflicts("build")
    if conflicts:
        print(f"Waiting for {conflicts[0]['terminal_type']} to finish building...")
        coord.wait_for_others(["build"], timeout=300)

    with coord.task(f"Building ({build_cmd})"):
        return subprocess.run(build_cmd.split(), capture_output=True, text=True)


def coordinated_test(test_cmd: str = "npm test"):
    """
    Auto-coordinated test command.

    Broadcasts test runs, shares results.
    """
    import subprocess

    coord = get_coordinator()

    with coord.task(f"Running tests ({test_cmd})"):
        result = subprocess.run(test_cmd.split(), capture_output=True, text=True)

        # Share test result
        coord.coordinator.set_shared_context(
            "last_test_result",
            {"success": result.returncode == 0, "output": result.stdout[-500:]},
            coord.session.id
        )

        return result


def coordinated_edit(file_path: str, description: str = None):
    """
    Context manager for coordinated file edits.

    Prevents multiple terminals editing same file.

    Usage:
        with coordinated_edit("src/auth.py", "Adding login"):
            # edit the file
            pass
    """
    coord = get_coordinator()
    task_desc = description or f"Editing {file_path}"

    # Check if anyone else is editing this file
    conflicts = coord.check_conflicts(file_path)
    if conflicts:
        raise ConflictError(f"File {file_path} is being edited by {conflicts[0]['terminal_type']}")

    return coord.task(task_desc, files=[file_path])


def coordinated_deploy(env: str = "staging"):
    """
    Auto-coordinated deployment.

    Only one deploy at a time per environment.
    """
    coord = get_coordinator()

    conflicts = coord.check_conflicts(f"deploy {env}")
    if conflicts:
        raise ConflictError(f"Deploy to {env} already in progress by {conflicts[0]['terminal_type']}")

    return coord.task(f"Deploying to {env}")


def coordinated_db(operation: str):
    """
    Auto-coordinated database operations.

    Migrations, seeds, etc should not overlap.
    """
    coord = get_coordinator()

    conflicts = coord.check_conflicts(f"database {operation}")
    if conflicts:
        print(f"Warning: {conflicts[0]['terminal_type']} is doing database operations")
        coord.wait_for_others(["database", "migration", "seed"], timeout=120)

    return coord.task(f"Database: {operation}")


class CoordinatedSession:
    """
    Wrapper class that auto-coordinates common operations.

    Usage:
        session = CoordinatedSession()

        # Auto-coordinated git
        session.git("pull")
        session.git("push", ["origin", "main"])

        # Auto-coordinated build
        session.build()

        # Auto-coordinated file edit
        with session.edit("src/app.py"):
            # make changes
            pass
    """

    def __init__(self):
        self.coord = get_coordinator()

    def git(self, cmd: str, args: List[str] = None):
        return coordinated_git(cmd, args)

    def build(self, cmd: str = "npm run build"):
        return coordinated_build(cmd)

    def test(self, cmd: str = "npm test"):
        return coordinated_test(cmd)

    def edit(self, file_path: str, description: str = None):
        return coordinated_edit(file_path, description)

    def deploy(self, env: str = "staging"):
        return coordinated_deploy(env)

    def db(self, operation: str):
        return coordinated_db(operation)

    def task(self, description: str, files: List[str] = None):
        return self.coord.task(description, files)

    @property
    def status(self):
        return self.coord.get_status()


# =========================================================================
# Orchestrator Integration
# =========================================================================

def wrap_orchestrator_call(route: str, message: str, handler_fn):
    """
    Wrap an orchestrator handler with auto-coordination.

    Auto-broadcasts the task and checks conflicts.
    """
    coord = get_coordinator()

    # Create task description from route + message
    task_desc = f"{route}: {message[:50]}"

    # Check conflicts for certain routes
    if route.upper() in ['CODE', 'IMPROVE', 'PROJECT']:
        conflicts = coord.check_conflicts(message)
        if conflicts:
            # Don't block, but note it in the response
            pass

    # Execute with task tracking
    with coord.task(task_desc):
        return handler_fn(message)


# Auto-initialize when imported
try:
    _auto_coord = AutoCoordinator()
except Exception as e:
    # Don't crash if coordination fails - it's optional
    print(f"[auto_coordinator] Warning: Failed to initialize ({e})", file=sys.stderr)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto Terminal Coordinator")
    parser.add_argument("command", choices=["status", "conflicts", "start", "finish"])
    parser.add_argument("args", nargs="*")

    args = parser.parse_args()
    coord = get_coordinator()

    if args.command == "status":
        import json
        print(json.dumps(coord.get_status(), indent=2))

    elif args.command == "conflicts":
        task = " ".join(args.args)
        conflicts = coord.check_conflicts(task)
        if conflicts:
            print(f"Conflicts found for '{task}':")
            for c in conflicts:
                print(f"  [{c['session_id']}] {c['task']}")
        else:
            print(f"No conflicts for '{task}'")

    elif args.command == "start":
        task = " ".join(args.args)
        try:
            task_id = coord.start_task(task)
            print(f"Started task: {task_id}")
        except ConflictError as e:
            print(f"Conflict: {e}")

    elif args.command == "finish":
        coord.finish_task()
        print("Task finished")
