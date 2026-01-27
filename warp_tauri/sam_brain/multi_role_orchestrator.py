#!/usr/bin/env python3
"""
SAM Multi-Role Orchestrator - Coordinates Multiple Claude Terminals

This is the brain that coordinates multiple Claude Code instances,
each taking a different role in the development process.

Roles:
- Builder: Plans architecture, writes code
- Reviewer: Reviews code, suggests improvements
- Tester: Writes tests, validates functionality
- Planner: Creates roadmaps, breaks down features
- Debugger: Diagnoses issues, fixes bugs
- Documenter: Writes docs, updates README

Architecture:
                    ┌─────────────────┐
                    │   SAM (MLX)     │
                    │  Orchestrator   │
                    │  Context Store  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Claude 1   │    │   Claude 2   │    │   Claude N   │
│   (Builder)  │    │  (Reviewer)  │    │   (Tester)   │
└──────────────┘    └──────────────┘    └──────────────┘

Usage:
    # Start orchestrator server
    python multi_role_orchestrator.py server

    # From a Claude terminal, register with a role
    python multi_role_orchestrator.py register builder

    # Assign tasks
    python multi_role_orchestrator.py task builder "Create user settings view"

    # Handoff between roles
    python multi_role_orchestrator.py handoff builder reviewer "Code ready for review"
"""

import json
import time
import os
import socket
import threading
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class Role(Enum):
    """Available Claude roles"""
    BUILDER = "builder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PLANNER = "planner"
    DEBUGGER = "debugger"
    DOCUMENTER = "documenter"


@dataclass
class RoleConfig:
    """Configuration for a Claude role"""
    name: str
    description: str
    system_prompt: str
    capabilities: List[str]
    priority: int = 5


ROLE_CONFIGS: Dict[str, RoleConfig] = {
    Role.BUILDER.value: RoleConfig(
        name="Builder",
        description="Plans architecture and writes production code",
        system_prompt="""You are SAM's Builder - an expert iOS/Swift developer.

RESPONSIBILITIES:
1. Plan and architect new features
2. Write clean, efficient Swift/SwiftUI code
3. Follow Apple's Human Interface Guidelines
4. Use MVVM or TCA architecture patterns
5. Implement with testability in mind

WHEN YOU COMPLETE A TASK:
- Summarize what you built
- List files created/modified
- Note any dependencies added
- Signal ready for handoff: [HANDOFF:REVIEWER] Code ready for review

WORKING WITH OTHER ROLES:
- Hand off to REVIEWER when code is ready
- Hand off to TESTER when feature is complete
- Ask PLANNER for clarification on requirements
- Send bugs to DEBUGGER""",
        capabilities=["code", "architecture", "refactor", "implement"],
        priority=1
    ),

    Role.REVIEWER.value: RoleConfig(
        name="Reviewer",
        description="Reviews code for quality, security, and best practices",
        system_prompt="""You are SAM's Reviewer - a senior code reviewer.

RESPONSIBILITIES:
1. Review code for bugs and logic errors
2. Check for security vulnerabilities
3. Ensure code follows Swift best practices
4. Verify proper error handling
5. Check for performance issues
6. Ensure accessibility compliance

REVIEW FORMAT:
- CRITICAL: Must fix before merge
- MAJOR: Should fix, significant impact
- MINOR: Nice to have, low impact
- APPROVED: Ready to proceed

WHEN REVIEWING:
- Be constructive, provide specific suggestions with code examples
- Signal handoff: [HANDOFF:BUILDER] Please fix these issues
- Or: [HANDOFF:TESTER] Approved, please test
- Or: [APPROVED] Ready to merge""",
        capabilities=["review", "security-audit", "performance-check", "approve"],
        priority=2
    ),

    Role.TESTER.value: RoleConfig(
        name="Tester",
        description="Writes tests and validates functionality",
        system_prompt="""You are SAM's Tester - a QA and testing expert.

RESPONSIBILITIES:
1. Write unit tests (XCTest)
2. Write UI tests (XCUITest)
3. Create integration tests
4. Validate edge cases
5. Test accessibility
6. Performance testing

TESTING APPROACH:
- Aim for 80%+ code coverage
- Test happy paths and error cases
- Mock external dependencies
- Use snapshot testing for UI

SIGNAL RESULTS:
- [PASS] All tests passing, feature validated
- [FAIL:DEBUGGER] Found bug: <description>
- [HANDOFF:BUILDER] Tests written, please verify""",
        capabilities=["unit-test", "ui-test", "integration-test", "validate"],
        priority=3
    ),

    Role.PLANNER.value: RoleConfig(
        name="Planner",
        description="Creates roadmaps and breaks down features",
        system_prompt="""You are SAM's Planner - a technical project manager.

RESPONSIBILITIES:
1. Break down features into tasks
2. Create implementation roadmaps
3. Estimate complexity (S/M/L/XL, not time)
4. Identify dependencies
5. Define acceptance criteria
6. Prioritize backlog

OUTPUT FORMAT:
## Feature: <name>
### Tasks:
1. [S] Task description - assigned to BUILDER
2. [M] Task description - assigned to BUILDER
### Dependencies:
- List any blockers
### Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2

SIGNAL: [HANDOFF:BUILDER] Plan ready for implementation""",
        capabilities=["plan", "roadmap", "breakdown", "prioritize"],
        priority=1
    ),

    Role.DEBUGGER.value: RoleConfig(
        name="Debugger",
        description="Diagnoses issues and fixes bugs",
        system_prompt="""You are SAM's Debugger - an expert at finding and fixing bugs.

RESPONSIBILITIES:
1. Analyze error messages and stack traces
2. Reproduce issues
3. Identify root causes
4. Implement minimal fixes
5. Prevent regression

DEBUGGING APPROACH:
- Start with the error message
- Check recent changes (git diff)
- Add strategic logging
- Fix the cause, not symptoms
- Add test to prevent regression

SIGNAL:
- [FIXED:REVIEWER] Bug fixed, please review
- [BLOCKED] Need more info: <question>
- [ESCALATE] Complex issue, need help""",
        capabilities=["diagnose", "fix", "analyze", "trace"],
        priority=2
    ),

    Role.DOCUMENTER.value: RoleConfig(
        name="Documenter",
        description="Writes documentation and maintains README",
        system_prompt="""You are SAM's Documenter - a technical writer.

RESPONSIBILITIES:
1. Write clear API documentation
2. Create usage examples
3. Maintain README files
4. Document architecture decisions
5. Write inline code comments
6. Create onboarding guides

DOCUMENTATION STYLE:
- Clear and concise
- Include code examples
- Use diagrams when helpful
- Keep updated with changes

SIGNAL:
- [DOCS:COMPLETE] Documentation updated
- [HANDOFF:REVIEWER] Please review docs""",
        capabilities=["document", "readme", "api-docs", "examples"],
        priority=4
    ),
}


@dataclass
class Task:
    """A task assigned to a role"""
    id: str
    role: str
    description: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    output: Optional[str] = None
    handoff_to: Optional[str] = None
    handoff_note: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Handoff:
    """A handoff between roles"""
    id: str
    from_role: str
    to_role: str
    note: str
    context_summary: Optional[str]
    timestamp: str
    task_id: Optional[str] = None


@dataclass
class Session:
    """An orchestration session"""
    id: str
    started_at: str
    active_roles: List[str]
    tasks: List[Task] = field(default_factory=list)
    handoffs: List[Handoff] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class MultiRoleOrchestrator:
    """
    Orchestrates multiple Claude Code terminals with different roles.

    SAM maintains the orchestrator, which:
    1. Tracks active Claude terminals and their roles
    2. Routes tasks between roles
    3. Maintains shared context
    4. Logs all interactions for learning
    """

    STATE_DIR = Path.home() / ".sam" / "multi_orchestrator"
    SOCKET_PATH = "/tmp/sam_multi_orchestrator.sock"
    FIFO_DIR = Path.home() / ".sam" / "fifos"

    def __init__(self):
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.FIFO_DIR.mkdir(parents=True, exist_ok=True)

        self.session: Optional[Session] = None
        self.active_terminals: Dict[str, Dict] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []

        self._load_state()

    def _load_state(self):
        """Load orchestrator state from disk."""
        state_file = self.STATE_DIR / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    if data.get("session"):
                        sess = data["session"]
                        self.session = Session(
                            id=sess["id"],
                            started_at=sess["started_at"],
                            active_roles=sess["active_roles"],
                            tasks=[Task(**t) for t in sess.get("tasks", [])],
                            handoffs=[Handoff(**h) for h in sess.get("handoffs", [])],
                            context=sess.get("context", {}),
                        )
                    self.task_queue = [Task(**t) for t in data.get("task_queue", [])]
                    self.completed_tasks = [Task(**t) for t in data.get("completed_tasks", [])]
            except Exception as e:
                print(f"Warning: Could not load state: {e}")

    def _save_state(self):
        """Persist orchestrator state to disk."""
        state_file = self.STATE_DIR / "state.json"

        def serialize_session():
            if not self.session:
                return None
            return {
                "id": self.session.id,
                "started_at": self.session.started_at,
                "active_roles": self.session.active_roles,
                "tasks": [asdict(t) for t in self.session.tasks],
                "handoffs": [asdict(h) for h in self.session.handoffs],
                "context": self.session.context,
            }

        with open(state_file, "w") as f:
            json.dump({
                "session": serialize_session(),
                "task_queue": [asdict(t) for t in self.task_queue],
                "completed_tasks": [asdict(t) for t in self.completed_tasks[-100:]],
                "active_terminals": self.active_terminals,
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2)

    def start_session(self, roles: List[str] = None) -> Session:
        """Start a new orchestration session."""
        if roles is None:
            roles = [Role.BUILDER.value, Role.REVIEWER.value]

        session_id = hashlib.md5(
            f"{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        self.session = Session(
            id=session_id,
            started_at=datetime.now().isoformat(),
            active_roles=roles,
        )

        self._save_state()
        self._create_role_fifos(roles)

        return self.session

    def _create_role_fifos(self, roles: List[str]):
        """Create named pipes for role communication."""
        for role in roles:
            fifo_path = self.FIFO_DIR / f"{role}_in.fifo"
            if not fifo_path.exists():
                os.mkfifo(str(fifo_path))

    def end_session(self) -> Dict:
        """End the current session and generate summary."""
        if not self.session:
            return {"error": "No active session"}

        start = datetime.fromisoformat(self.session.started_at)
        duration_mins = int((datetime.now() - start).total_seconds() / 60)

        summary = {
            "session_id": self.session.id,
            "duration_minutes": duration_mins,
            "tasks_completed": len([t for t in self.session.tasks if t.status == "completed"]),
            "handoffs": len(self.session.handoffs),
            "roles_used": list(set(t.role for t in self.session.tasks)),
        }

        archive_file = self.STATE_DIR / f"session_{self.session.id}.json"
        with open(archive_file, "w") as f:
            json.dump({
                "session": asdict(self.session) if self.session else None,
                "summary": summary,
            }, f, indent=2, default=str)

        self.session = None
        self._save_state()

        return summary

    def register_terminal(self, role: str, pid: int = None) -> Dict:
        """Register a Claude terminal with a specific role."""
        if role not in ROLE_CONFIGS:
            return {"error": f"Unknown role: {role}. Available: {[r.value for r in Role]}"}

        terminal_id = f"{role}_{pid or os.getpid()}"
        self.active_terminals[terminal_id] = {
            "role": role,
            "pid": pid,
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }

        config = ROLE_CONFIGS[role]

        if self.session and role not in self.session.active_roles:
            self.session.active_roles.append(role)

        self._save_state()

        return {
            "terminal_id": terminal_id,
            "role": role,
            "config": {
                "name": config.name,
                "description": config.description,
                "capabilities": config.capabilities,
            },
            "system_prompt": config.system_prompt,
        }

    def assign_task(self, role: str, description: str, context: Dict = None) -> Task:
        """Assign a task to a specific role."""
        task_id = hashlib.md5(
            f"{role}{description}{time.time()}".encode()
        ).hexdigest()[:8]

        task = Task(
            id=task_id,
            role=role,
            description=description,
            context=context or {},
        )

        self.task_queue.append(task)

        if self.session:
            self.session.tasks.append(task)

        self._save_state()
        self._notify_role(role, f"New task: {description}")

        return task

    def _notify_role(self, role: str, message: str):
        """Send notification to a role's FIFO (non-blocking)."""
        fifo_path = self.FIFO_DIR / f"{role}_in.fifo"
        if fifo_path.exists():
            try:
                # Use non-blocking write to avoid hanging if no reader
                fd = os.open(str(fifo_path), os.O_WRONLY | os.O_NONBLOCK)
                os.write(fd, (json.dumps({"type": "notification", "message": message}) + "\n").encode())
                os.close(fd)
            except (OSError, BlockingIOError):
                # No reader available - that's OK
                pass

    def get_next_task(self, role: str) -> Optional[Task]:
        """Get the next pending task for a role."""
        for task in self.task_queue:
            if task.role == role and task.status == "pending":
                task.status = "in_progress"
                self._save_state()
                return task
        return None

    def complete_task(self, task_id: str, output: str = None) -> Dict:
        """Mark a task as completed."""
        for task in self.task_queue:
            if task.id == task_id:
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                task.output = output

                self.completed_tasks.append(task)
                self.task_queue.remove(task)
                self._save_state()

                return {"status": "completed", "task_id": task_id}

        return {"error": f"Task not found: {task_id}"}

    def handoff(self, from_role: str, to_role: str, note: str, context = None) -> Handoff:
        """Hand off work from one role to another."""
        handoff_id = hashlib.md5(
            f"{from_role}{to_role}{time.time()}".encode()
        ).hexdigest()[:8]

        # Handle context as string or dict
        context_summary = None
        if context:
            if isinstance(context, str):
                context_summary = context[:500]
            elif isinstance(context, dict):
                context_summary = json.dumps(context)[:500]
            else:
                context_summary = str(context)[:500]

        handoff = Handoff(
            id=handoff_id,
            from_role=from_role,
            to_role=to_role,
            note=note,
            context_summary=context_summary,
            timestamp=datetime.now().isoformat(),
        )

        if self.session:
            self.session.handoffs.append(handoff)

        # Create task for receiving role
        task = self.assign_task(
            to_role,
            f"[Handoff from {from_role}] {note}",
            {"handoff_id": handoff_id, "handoff_context": context}
        )
        handoff.task_id = task.id

        self._save_state()

        return handoff

    def get_shared_context(self) -> Dict:
        """Get shared context available to all roles."""
        return {
            "session_id": self.session.id if self.session else None,
            "active_roles": list(self.active_terminals.keys()),
            "pending_tasks": [
                {"id": t.id, "role": t.role, "description": t.description[:100]}
                for t in self.task_queue if t.status == "pending"
            ],
            "recent_handoffs": [
                {"from": h.from_role, "to": h.to_role, "note": h.note}
                for h in (self.session.handoffs[-5:] if self.session else [])
            ],
            "project": self._get_project_context(),
        }

    def _get_project_context(self) -> Dict:
        """Get current project context."""
        registry_path = Path.home() / ".sam" / "projects" / "registry.json"
        if registry_path.exists():
            try:
                with open(registry_path) as f:
                    data = json.load(f)
                    active = [p for p in data.get("projects", []) if p.get("status") == "active"]
                    if active:
                        return {
                            "name": active[0].get("name"),
                            "path": active[0].get("path"),
                            "focus": active[0].get("currentFocus"),
                        }
            except:
                pass
        return {}

    def get_status(self) -> Dict:
        """Get orchestrator status."""
        return {
            "session": {
                "id": self.session.id if self.session else None,
                "active_roles": self.session.active_roles if self.session else [],
                "started_at": self.session.started_at if self.session else None,
            },
            "terminals": {
                tid: {"role": t["role"], "status": t["status"]}
                for tid, t in self.active_terminals.items()
            },
            "tasks": {
                "pending": len([t for t in self.task_queue if t.status == "pending"]),
                "in_progress": len([t for t in self.task_queue if t.status == "in_progress"]),
                "completed_total": len(self.completed_tasks),
            },
            "handoffs_total": len(self.session.handoffs) if self.session else 0,
        }

    def get_role_prompt(self, role: str) -> str:
        """Get the system prompt for a role."""
        if role in ROLE_CONFIGS:
            return ROLE_CONFIGS[role].system_prompt
        return ""


# =============================================================================
# IPC Server for Terminal Communication
# =============================================================================

class OrchestrationServer:
    """Unix socket server for terminal communication."""

    def __init__(self, orchestrator: MultiRoleOrchestrator):
        self.orch = orchestrator
        self.running = False

    def start(self):
        """Start the IPC server."""
        socket_path = self.orch.SOCKET_PATH

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(5)

        self.running = True
        print(f"Orchestrator listening on {socket_path}")

        while self.running:
            try:
                server.settimeout(1.0)
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue

                data = conn.recv(8192).decode()
                if data:
                    response = self._handle_message(json.loads(data))
                    conn.send(json.dumps(response, default=str).encode())
                conn.close()
            except Exception as e:
                if self.running:
                    print(f"IPC error: {e}")

    def stop(self):
        """Stop the server."""
        self.running = False

    def _handle_message(self, msg: Dict) -> Dict:
        """Handle incoming message."""
        action = msg.get("action")

        handlers = {
            "register": lambda: self.orch.register_terminal(msg["role"], msg.get("pid")),
            "task": lambda: asdict(self.orch.assign_task(msg["role"], msg["description"], msg.get("context"))),
            "get_task": lambda: asdict(self.orch.get_next_task(msg["role"])) if self.orch.get_next_task(msg["role"]) else {"task": None},
            "complete": lambda: self.orch.complete_task(msg["task_id"], msg.get("output")),
            "handoff": lambda: asdict(self.orch.handoff(msg["from_role"], msg["to_role"], msg["note"], msg.get("context"))),
            "context": lambda: self.orch.get_shared_context(),
            "status": lambda: self.orch.get_status(),
            "prompt": lambda: {"prompt": self.orch.get_role_prompt(msg["role"])},
        }

        if action in handlers:
            try:
                return handlers[action]()
            except Exception as e:
                return {"error": str(e)}

        return {"error": f"Unknown action: {action}"}


def send_command(action: str, **kwargs) -> Dict:
    """Send a command to the orchestrator."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(MultiRoleOrchestrator.SOCKET_PATH)
        sock.send(json.dumps({"action": action, **kwargs}).encode())
        response = sock.recv(8192).decode()
        sock.close()
        return json.loads(response)
    except FileNotFoundError:
        return {"error": "Orchestrator not running. Start with: python multi_role_orchestrator.py server"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    def print_help():
        print("""
SAM Multi-Role Orchestrator
===========================

Commands:
  server              Start the orchestrator server
  status              Show orchestrator status
  register <role>     Register this terminal with a role
  task <role> <desc>  Assign a task to a role
  handoff <from> <to> <note>  Hand off work between roles
  prompt <role>       Get the system prompt for a role
  context             Show shared context

Available Roles:
  builder     - Plans architecture, writes code
  reviewer    - Reviews code, suggests improvements
  tester      - Writes tests, validates functionality
  planner     - Creates roadmaps, breaks down features
  debugger    - Diagnoses issues, fixes bugs
  documenter  - Writes docs, updates README

Example Workflow:
  Terminal 1: python multi_role_orchestrator.py register builder
  Terminal 2: python multi_role_orchestrator.py register reviewer

  # Assign work
  python multi_role_orchestrator.py task builder "Create user settings view"

  # Hand off for review
  python multi_role_orchestrator.py handoff builder reviewer "Settings view complete"
""")

    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "server":
        orch = MultiRoleOrchestrator()
        session = orch.start_session([r.value for r in Role])
        print(f"Session started: {session.id}")
        print(f"Active roles: {', '.join(session.active_roles)}")
        print("\nPress Ctrl+C to stop\n")

        server = OrchestrationServer(orch)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            server.stop()
            summary = orch.end_session()
            print(f"Session summary: {json.dumps(summary, indent=2)}")

    elif cmd == "status":
        result = send_command("status")
        print(json.dumps(result, indent=2))

    elif cmd == "register":
        role = sys.argv[2] if len(sys.argv) > 2 else "builder"
        result = send_command("register", role=role, pid=os.getpid())
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Registered as: {result['role']}")
            print(f"Terminal ID: {result['terminal_id']}")
            print(f"\n{'-'*60}")
            print("SYSTEM PROMPT:")
            print(f"{'-'*60}")
            print(result.get('system_prompt', ''))

    elif cmd == "task":
        role = sys.argv[2]
        desc = " ".join(sys.argv[3:])
        result = send_command("task", role=role, description=desc)
        print(json.dumps(result, indent=2))

    elif cmd == "handoff":
        from_role = sys.argv[2]
        to_role = sys.argv[3]
        note = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else "Please continue"
        result = send_command("handoff", from_role=from_role, to_role=to_role, note=note)
        print(json.dumps(result, indent=2))

    elif cmd == "prompt":
        role = sys.argv[2] if len(sys.argv) > 2 else "builder"
        result = send_command("prompt", role=role)
        print(result.get("prompt", "Unknown role"))

    elif cmd == "context":
        result = send_command("context")
        print(json.dumps(result, indent=2))

    elif cmd == "--help" or cmd == "-h":
        print_help()

    else:
        print(f"Unknown command: {cmd}")
        print("Use --help for usage")
