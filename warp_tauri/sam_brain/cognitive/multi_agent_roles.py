#!/usr/bin/env python3
"""
SAM Multi-Agent Role Coordination System

Enables multiple Claude Code instances to coordinate with different development roles.
Each role has specialized capabilities, system prompts, and handoff protocols.

Roles:
- BUILDER: Plans architecture, writes production code
- REVIEWER: Reviews code for quality, security, best practices
- TESTER: Writes tests, validates functionality
- PLANNER: Creates roadmaps, breaks down features
- DEBUGGER: Diagnoses issues, fixes bugs
- DOCUMENTER: Writes documentation, maintains README

Architecture:
                    +-------------------+
                    |   SAM Coordinator |
                    |   Task Queue      |
                    |   Context Store   |
                    +--------+----------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+---------------+    +---------------+    +---------------+
|   Claude 1    |    |   Claude 2    |    |   Claude N    |
|   (Builder)   |    |   (Reviewer)  |    |   (Tester)    |
+---------------+    +---------------+    +---------------+

Usage as library:
    from cognitive.multi_agent_roles import (
        MultiAgentCoordinator,
        Role,
        create_coordinator
    )

    # Create coordinator
    coord = create_coordinator()

    # Register a terminal with a role
    reg = coord.register_terminal(Role.BUILDER)
    print(reg.system_prompt)  # Get role-specific system prompt

    # Assign tasks
    task = coord.assign_task(Role.BUILDER, "Implement user settings view")

    # Handoff between roles
    handoff = coord.handoff(
        from_role=Role.BUILDER,
        to_role=Role.REVIEWER,
        note="Code ready for review",
        context={"files": ["settings.swift"]}
    )

    # Get shared context
    ctx = coord.get_shared_context()

CLI usage:
    python multi_agent_roles.py status
    python multi_agent_roles.py register builder
    python multi_agent_roles.py task builder "Create user settings"
    python multi_agent_roles.py handoff builder reviewer "Ready for review"
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# =============================================================================
# Role Definitions
# =============================================================================

class Role(Enum):
    """
    Available development roles for Claude instances.

    Each role has specialized capabilities and system prompts
    optimized for specific development tasks.
    """
    BUILDER = "builder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PLANNER = "planner"
    DEBUGGER = "debugger"
    DOCUMENTER = "documenter"

    @classmethod
    def from_string(cls, value: str) -> "Role":
        """
        Convert a string to a Role enum.

        Args:
            value: Role name as string (case-insensitive)

        Returns:
            Role enum value

        Raises:
            ValueError: If role name is not recognized
        """
        value = value.lower()
        for role in cls:
            if role.value == value:
                return role
        raise ValueError(f"Unknown role: {value}. Valid roles: {[r.value for r in cls]}")


@dataclass
class RoleConfig:
    """
    Configuration for a development role.

    Defines the behavior, capabilities, and system prompt
    that guides a Claude instance in this role.
    """
    name: str
    description: str
    system_prompt: str
    capabilities: List[str]
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "priority": self.priority,
        }


# Default role configurations
ROLE_CONFIGS: Dict[Role, RoleConfig] = {
    Role.BUILDER: RoleConfig(
        name="Builder",
        description="Plans architecture and writes production code",
        system_prompt="""You are a Builder - an expert developer focused on implementation.

RESPONSIBILITIES:
1. Plan and architect new features
2. Write clean, efficient code
3. Follow best practices and design patterns
4. Implement with testability in mind
5. Consider edge cases and error handling

WHEN YOU COMPLETE A TASK:
- Summarize what you built
- List files created/modified
- Note any dependencies added
- Signal readiness: [HANDOFF:REVIEWER] Code ready for review

WORKING WITH OTHER ROLES:
- Hand off to REVIEWER when code is ready
- Hand off to TESTER when feature is complete
- Ask PLANNER for clarification on requirements
- Send bugs to DEBUGGER""",
        capabilities=["code", "architecture", "refactor", "implement"],
        priority=1
    ),

    Role.REVIEWER: RoleConfig(
        name="Reviewer",
        description="Reviews code for quality, security, and best practices",
        system_prompt="""You are a Reviewer - a senior code reviewer.

RESPONSIBILITIES:
1. Review code for bugs and logic errors
2. Check for security vulnerabilities
3. Ensure code follows best practices
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

    Role.TESTER: RoleConfig(
        name="Tester",
        description="Writes tests and validates functionality",
        system_prompt="""You are a Tester - a QA and testing expert.

RESPONSIBILITIES:
1. Write unit tests
2. Write integration tests
3. Write UI/E2E tests
4. Validate edge cases
5. Test accessibility
6. Performance testing

TESTING APPROACH:
- Aim for 80%+ code coverage
- Test happy paths and error cases
- Mock external dependencies
- Use snapshot testing for UI when appropriate

SIGNAL RESULTS:
- [PASS] All tests passing, feature validated
- [FAIL:DEBUGGER] Found bug: <description>
- [HANDOFF:BUILDER] Tests written, please verify""",
        capabilities=["unit-test", "ui-test", "integration-test", "validate"],
        priority=3
    ),

    Role.PLANNER: RoleConfig(
        name="Planner",
        description="Creates roadmaps and breaks down features",
        system_prompt="""You are a Planner - a technical project manager.

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

    Role.DEBUGGER: RoleConfig(
        name="Debugger",
        description="Diagnoses issues and fixes bugs",
        system_prompt="""You are a Debugger - an expert at finding and fixing bugs.

RESPONSIBILITIES:
1. Analyze error messages and stack traces
2. Reproduce issues
3. Identify root causes
4. Implement minimal fixes
5. Prevent regression

DEBUGGING APPROACH:
- Start with the error message
- Check recent changes (git diff)
- Add strategic logging if needed
- Fix the cause, not symptoms
- Add test to prevent regression

SIGNAL:
- [FIXED:REVIEWER] Bug fixed, please review
- [BLOCKED] Need more info: <question>
- [ESCALATE] Complex issue, need help""",
        capabilities=["diagnose", "fix", "analyze", "trace"],
        priority=2
    ),

    Role.DOCUMENTER: RoleConfig(
        name="Documenter",
        description="Writes documentation and maintains README",
        system_prompt="""You are a Documenter - a technical writer.

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


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Task:
    """
    A task assigned to a specific role.

    Tasks track work items with status, context, and handoff information.
    """
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Handoff:
    """
    A handoff of work from one role to another.

    Handoffs coordinate work transitions with context preservation.
    """
    id: str
    from_role: str
    to_role: str
    note: str
    context_summary: Optional[str]
    timestamp: str
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TerminalRegistration:
    """
    Registration information for a Claude terminal.

    Contains the role assignment, system prompt, and capabilities
    for a registered terminal.
    """
    terminal_id: str
    role: Role
    config: RoleConfig
    system_prompt: str
    registered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "terminal_id": self.terminal_id,
            "role": self.role.value,
            "config": self.config.to_dict(),
            "system_prompt": self.system_prompt,
            "registered_at": self.registered_at,
        }


@dataclass
class Session:
    """
    An orchestration session tracking all coordination activity.

    Sessions group related tasks and handoffs for a work period.
    """
    id: str
    started_at: str
    active_roles: List[str]
    tasks: List[Task] = field(default_factory=list)
    handoffs: List[Handoff] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "started_at": self.started_at,
            "active_roles": self.active_roles,
            "tasks": [t.to_dict() for t in self.tasks],
            "handoffs": [h.to_dict() for h in self.handoffs],
            "context": self.context,
        }


@dataclass
class CoordinatorStatus:
    """
    Current status of the coordinator.

    Provides overview of active session, terminals, and task statistics.
    """
    session_id: Optional[str]
    session_started_at: Optional[str]
    active_roles: List[str]
    terminal_count: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    total_handoffs: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session": {
                "id": self.session_id,
                "started_at": self.session_started_at,
                "active_roles": self.active_roles,
            },
            "terminals": self.terminal_count,
            "tasks": {
                "pending": self.pending_tasks,
                "in_progress": self.in_progress_tasks,
                "completed": self.completed_tasks,
            },
            "handoffs_total": self.total_handoffs,
        }


# =============================================================================
# Main Coordinator
# =============================================================================

class MultiAgentCoordinator:
    """
    Coordinates multiple Claude Code instances with different development roles.

    The coordinator:
    1. Tracks active terminals and their assigned roles
    2. Routes tasks between roles
    3. Maintains shared context across roles
    4. Logs all interactions for learning

    Example:
        coord = MultiAgentCoordinator()
        coord.start_session([Role.BUILDER, Role.REVIEWER])

        # Register terminals
        builder_reg = coord.register_terminal(Role.BUILDER)
        reviewer_reg = coord.register_terminal(Role.REVIEWER)

        # Assign and track tasks
        task = coord.assign_task(Role.BUILDER, "Create API endpoint")
        coord.complete_task(task.id, "Implemented GET /users")

        # Coordinate handoffs
        coord.handoff(Role.BUILDER, Role.REVIEWER, "Ready for review")
    """

    DEFAULT_STATE_DIR = Path.home() / ".sam" / "multi_agent"

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        auto_save: bool = True
    ):
        """
        Initialize the coordinator.

        Args:
            state_dir: Directory for persisting state. Defaults to ~/.sam/multi_agent
            auto_save: Whether to auto-save state after changes
        """
        self.state_dir = state_dir or self.DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save

        # State
        self.session: Optional[Session] = None
        self.active_terminals: Dict[str, Dict[str, Any]] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []

        # Load any existing state
        self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID."""
        raw = f"{prefix}{time.time()}{os.getpid()}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def _load_state(self) -> None:
        """Load coordinator state from disk."""
        state_file = self.state_dir / "state.json"
        if not state_file.exists():
            return

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
            self.active_terminals = data.get("active_terminals", {})

        except Exception as e:
            print(f"[MultiAgentCoordinator] Warning: Could not load state: {e}")

    def _save_state(self) -> None:
        """Persist coordinator state to disk."""
        if not self.auto_save:
            return

        state_file = self.state_dir / "state.json"

        data = {
            "session": self.session.to_dict() if self.session else None,
            "task_queue": [t.to_dict() for t in self.task_queue],
            "completed_tasks": [t.to_dict() for t in self.completed_tasks[-100:]],
            "active_terminals": self.active_terminals,
            "updated_at": datetime.now().isoformat(),
        }

        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(
        self,
        roles: Optional[List[Union[Role, str]]] = None
    ) -> Session:
        """
        Start a new coordination session.

        Args:
            roles: Roles to activate. Defaults to BUILDER and REVIEWER.

        Returns:
            The created Session
        """
        if roles is None:
            roles = [Role.BUILDER, Role.REVIEWER]

        # Normalize roles to strings
        role_strs = [
            r.value if isinstance(r, Role) else r
            for r in roles
        ]

        self.session = Session(
            id=self._generate_id("sess"),
            started_at=datetime.now().isoformat(),
            active_roles=role_strs,
        )

        self._save_state()
        return self.session

    def end_session(self) -> Dict[str, Any]:
        """
        End the current session and return summary.

        Returns:
            Summary dictionary with session statistics
        """
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

        # Archive session
        archive_file = self.state_dir / f"session_{self.session.id}.json"
        with open(archive_file, "w") as f:
            json.dump({
                "session": self.session.to_dict(),
                "summary": summary,
            }, f, indent=2, default=str)

        self.session = None
        self._save_state()

        return summary

    # -------------------------------------------------------------------------
    # Terminal Registration
    # -------------------------------------------------------------------------

    def register_terminal(
        self,
        role: Union[Role, str],
        pid: Optional[int] = None
    ) -> TerminalRegistration:
        """
        Register a Claude terminal with a specific role.

        Args:
            role: The role to assign (Role enum or string)
            pid: Process ID (defaults to current process)

        Returns:
            TerminalRegistration with role config and system prompt

        Raises:
            ValueError: If role is unknown
        """
        # Normalize role
        if isinstance(role, str):
            role = Role.from_string(role)

        config = ROLE_CONFIGS[role]
        terminal_id = f"{role.value}_{pid or os.getpid()}"

        self.active_terminals[terminal_id] = {
            "role": role.value,
            "pid": pid or os.getpid(),
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }

        # Add role to session if not already present
        if self.session and role.value not in self.session.active_roles:
            self.session.active_roles.append(role.value)

        self._save_state()

        return TerminalRegistration(
            terminal_id=terminal_id,
            role=role,
            config=config,
            system_prompt=config.system_prompt,
            registered_at=datetime.now().isoformat(),
        )

    def unregister_terminal(self, terminal_id: str) -> bool:
        """
        Unregister a terminal.

        Args:
            terminal_id: The terminal ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        if terminal_id in self.active_terminals:
            del self.active_terminals[terminal_id]
            self._save_state()
            return True
        return False

    # -------------------------------------------------------------------------
    # Task Management
    # -------------------------------------------------------------------------

    def assign_task(
        self,
        role: Union[Role, str],
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Assign a task to a specific role.

        Args:
            role: The target role
            description: Task description
            context: Optional context dictionary

        Returns:
            The created Task
        """
        if isinstance(role, str):
            role = Role.from_string(role)

        task = Task(
            id=self._generate_id("task"),
            role=role.value,
            description=description,
            context=context or {},
        )

        self.task_queue.append(task)

        if self.session:
            self.session.tasks.append(task)

        self._save_state()
        return task

    def get_next_task(self, role: Union[Role, str]) -> Optional[Task]:
        """
        Get the next pending task for a role.

        Args:
            role: The role to get tasks for

        Returns:
            Next pending Task or None
        """
        if isinstance(role, str):
            role = Role.from_string(role)

        for task in self.task_queue:
            if task.role == role.value and task.status == "pending":
                task.status = "in_progress"
                self._save_state()
                return task

        return None

    def get_tasks_for_role(
        self,
        role: Union[Role, str],
        status: Optional[str] = None
    ) -> List[Task]:
        """
        Get all tasks for a role, optionally filtered by status.

        Args:
            role: The role to get tasks for
            status: Optional status filter ("pending", "in_progress", "completed")

        Returns:
            List of matching Tasks
        """
        if isinstance(role, str):
            role = Role.from_string(role)

        tasks = [t for t in self.task_queue if t.role == role.value]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def complete_task(
        self,
        task_id: str,
        output: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a task as completed.

        Args:
            task_id: The task ID
            output: Optional output/result description

        Returns:
            Status dictionary
        """
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

    # -------------------------------------------------------------------------
    # Handoff Management
    # -------------------------------------------------------------------------

    def handoff(
        self,
        from_role: Union[Role, str],
        to_role: Union[Role, str],
        note: str,
        context: Optional[Union[str, Dict[str, Any]]] = None
    ) -> Handoff:
        """
        Hand off work from one role to another.

        Creates a handoff record and a new task for the receiving role.

        Args:
            from_role: The source role
            to_role: The target role
            note: Handoff note/instructions
            context: Optional context (string or dict)

        Returns:
            The created Handoff
        """
        # Normalize roles
        if isinstance(from_role, str):
            from_role = Role.from_string(from_role)
        if isinstance(to_role, str):
            to_role = Role.from_string(to_role)

        # Process context
        context_summary = None
        if context:
            if isinstance(context, str):
                context_summary = context[:500]
            elif isinstance(context, dict):
                context_summary = json.dumps(context)[:500]
            else:
                context_summary = str(context)[:500]

        handoff = Handoff(
            id=self._generate_id("hoff"),
            from_role=from_role.value,
            to_role=to_role.value,
            note=note,
            context_summary=context_summary,
            timestamp=datetime.now().isoformat(),
        )

        if self.session:
            self.session.handoffs.append(handoff)

        # Create task for receiving role
        task = self.assign_task(
            to_role,
            f"[Handoff from {from_role.value}] {note}",
            {"handoff_id": handoff.id, "handoff_context": context}
        )
        handoff.task_id = task.id

        self._save_state()
        return handoff

    # -------------------------------------------------------------------------
    # Context Management
    # -------------------------------------------------------------------------

    def get_shared_context(self) -> Dict[str, Any]:
        """
        Get shared context available to all roles.

        Returns:
            Dictionary with session, tasks, and handoff information
        """
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
        }

    def add_shared_context(self, key: str, value: Any) -> None:
        """
        Add or update shared context.

        Args:
            key: Context key
            value: Context value (must be JSON-serializable)
        """
        if self.session:
            self.session.context[key] = value
            self._save_state()

    # -------------------------------------------------------------------------
    # Status and Info
    # -------------------------------------------------------------------------

    def get_status(self) -> CoordinatorStatus:
        """
        Get current coordinator status.

        Returns:
            CoordinatorStatus with session and task statistics
        """
        return CoordinatorStatus(
            session_id=self.session.id if self.session else None,
            session_started_at=self.session.started_at if self.session else None,
            active_roles=self.session.active_roles if self.session else [],
            terminal_count=len(self.active_terminals),
            pending_tasks=len([t for t in self.task_queue if t.status == "pending"]),
            in_progress_tasks=len([t for t in self.task_queue if t.status == "in_progress"]),
            completed_tasks=len(self.completed_tasks),
            total_handoffs=len(self.session.handoffs) if self.session else 0,
        )

    def get_role_config(self, role: Union[Role, str]) -> RoleConfig:
        """
        Get configuration for a role.

        Args:
            role: The role to get config for

        Returns:
            RoleConfig for the role

        Raises:
            ValueError: If role is unknown
        """
        if isinstance(role, str):
            role = Role.from_string(role)
        return ROLE_CONFIGS[role]

    def get_role_prompt(self, role: Union[Role, str]) -> str:
        """
        Get the system prompt for a role.

        Args:
            role: The role to get prompt for

        Returns:
            System prompt string
        """
        return self.get_role_config(role).system_prompt

    def list_roles(self) -> List[Dict[str, Any]]:
        """
        List all available roles with their descriptions.

        Returns:
            List of role info dictionaries
        """
        return [
            {
                "role": role.value,
                "name": config.name,
                "description": config.description,
                "capabilities": config.capabilities,
                "priority": config.priority,
            }
            for role, config in ROLE_CONFIGS.items()
        ]


# =============================================================================
# Factory Functions
# =============================================================================

def create_coordinator(
    state_dir: Optional[Path] = None,
    auto_start_session: bool = True
) -> MultiAgentCoordinator:
    """
    Create a multi-agent coordinator with sensible defaults.

    Args:
        state_dir: Optional custom state directory
        auto_start_session: Whether to auto-start a session if none exists

    Returns:
        Configured MultiAgentCoordinator
    """
    coord = MultiAgentCoordinator(state_dir=state_dir)

    if auto_start_session and coord.session is None:
        coord.start_session()

    return coord


def get_role_prompt(role: Union[Role, str]) -> str:
    """
    Get the system prompt for a role without creating a coordinator.

    Convenience function for quickly getting a role's prompt.

    Args:
        role: The role to get prompt for

    Returns:
        System prompt string
    """
    if isinstance(role, str):
        role = Role.from_string(role)
    return ROLE_CONFIGS[role].system_prompt


def get_role_config(role: Union[Role, str]) -> RoleConfig:
    """
    Get the configuration for a role without creating a coordinator.

    Args:
        role: The role to get config for

    Returns:
        RoleConfig for the role
    """
    if isinstance(role, str):
        role = Role.from_string(role)
    return ROLE_CONFIGS[role]


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point for testing and standalone usage."""
    import sys

    def print_help():
        print("""
SAM Multi-Agent Role Coordinator
================================

Commands:
  status              Show coordinator status
  roles               List available roles
  register <role>     Register this terminal with a role
  task <role> <desc>  Assign a task to a role
  tasks <role>        List tasks for a role
  complete <task_id>  Mark a task as completed
  handoff <from> <to> <note>  Hand off work between roles
  prompt <role>       Get the system prompt for a role
  context             Show shared context
  end                 End the current session

Available Roles:
  builder     - Plans architecture, writes code
  reviewer    - Reviews code, suggests improvements
  tester      - Writes tests, validates functionality
  planner     - Creates roadmaps, breaks down features
  debugger    - Diagnoses issues, fixes bugs
  documenter  - Writes docs, updates README

Example Workflow:
  Terminal 1: python multi_agent_roles.py register builder
  Terminal 2: python multi_agent_roles.py register reviewer

  # Assign work
  python multi_agent_roles.py task builder "Create user settings view"

  # Hand off for review
  python multi_agent_roles.py handoff builder reviewer "Settings view complete"
""")

    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1]
    coord = create_coordinator(auto_start_session=True)

    if cmd == "status":
        status = coord.get_status()
        print(json.dumps(status.to_dict(), indent=2))

    elif cmd == "roles":
        roles = coord.list_roles()
        print("\nAvailable Roles:")
        print("-" * 60)
        for r in roles:
            print(f"\n{r['name']} ({r['role']})")
            print(f"  {r['description']}")
            print(f"  Capabilities: {', '.join(r['capabilities'])}")

    elif cmd == "register":
        role = sys.argv[2] if len(sys.argv) > 2 else "builder"
        try:
            reg = coord.register_terminal(role)
            print(f"Registered as: {reg.role.value}")
            print(f"Terminal ID: {reg.terminal_id}")
            print(f"\n{'-' * 60}")
            print("SYSTEM PROMPT:")
            print(f"{'-' * 60}")
            print(reg.system_prompt)
        except ValueError as e:
            print(f"Error: {e}")

    elif cmd == "task":
        if len(sys.argv) < 4:
            print("Usage: task <role> <description>")
            return
        role = sys.argv[2]
        desc = " ".join(sys.argv[3:])
        try:
            task = coord.assign_task(role, desc)
            print(f"Task created: {task.id}")
            print(f"Role: {task.role}")
            print(f"Description: {task.description}")
        except ValueError as e:
            print(f"Error: {e}")

    elif cmd == "tasks":
        role = sys.argv[2] if len(sys.argv) > 2 else "builder"
        try:
            tasks = coord.get_tasks_for_role(role)
            print(f"\nTasks for {role}:")
            print("-" * 40)
            for t in tasks:
                print(f"[{t.status}] {t.id}: {t.description[:50]}")
            if not tasks:
                print("No tasks")
        except ValueError as e:
            print(f"Error: {e}")

    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: complete <task_id>")
            return
        task_id = sys.argv[2]
        output = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        result = coord.complete_task(task_id, output)
        print(json.dumps(result, indent=2))

    elif cmd == "handoff":
        if len(sys.argv) < 4:
            print("Usage: handoff <from_role> <to_role> [note]")
            return
        from_role = sys.argv[2]
        to_role = sys.argv[3]
        note = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else "Please continue"
        try:
            handoff = coord.handoff(from_role, to_role, note)
            print(f"Handoff created: {handoff.id}")
            print(f"From: {handoff.from_role} -> To: {handoff.to_role}")
            print(f"Note: {handoff.note}")
            if handoff.task_id:
                print(f"Task created: {handoff.task_id}")
        except ValueError as e:
            print(f"Error: {e}")

    elif cmd == "prompt":
        role = sys.argv[2] if len(sys.argv) > 2 else "builder"
        try:
            prompt = get_role_prompt(role)
            print(f"\n{role.upper()} SYSTEM PROMPT:")
            print("-" * 60)
            print(prompt)
        except ValueError as e:
            print(f"Error: {e}")

    elif cmd == "context":
        ctx = coord.get_shared_context()
        print(json.dumps(ctx, indent=2))

    elif cmd == "end":
        summary = coord.end_session()
        print("Session ended.")
        print(json.dumps(summary, indent=2))

    elif cmd in ("--help", "-h", "help"):
        print_help()

    else:
        print(f"Unknown command: {cmd}")
        print("Use --help for usage")


if __name__ == "__main__":
    main()
