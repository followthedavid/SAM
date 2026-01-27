#!/usr/bin/env python3
"""
SAM Command Proposal System

Allows SAM to propose actions to users rather than executing them directly.
This creates a collaborative human-AI workflow where:
- SAM analyzes problems and suggests solutions
- User reviews and approves/rejects proposals
- SAM learns from feedback to improve future proposals

Components:
- CommandProposal: Dataclass representing a proposed action
- CommandProposer: Generates proposals for tasks and fixes
- ProposalFormatter: Formats proposals for terminal/chat/GUI display
- ProposalHistory: Tracks proposals and learns from outcomes

Usage:
    from command_proposer import CommandProposer, ProposalFormatter

    proposer = CommandProposer()
    proposal = proposer.propose_fix("Build failing", {"project": "sam_brain"})

    print(ProposalFormatter.format_for_chat(proposal))
"""

import json
import os
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

# Import CommandType if available (we'll create a fallback if not)
try:
    from cognitive.command_classifier import CommandType, CommandClassifier
    _command_classifier_available = True
except ImportError:
    _command_classifier_available = False

    # Fallback CommandType enum
    class CommandType(Enum):
        """Type of command being proposed."""
        SAFE = "safe"               # Read-only, no side effects
        MODIFICATION = "modification"  # Modifies files/state
        DESTRUCTIVE = "destructive"    # Deletes files, irreversible
        NETWORK = "network"         # Network operations
        SYSTEM = "system"           # System-level operations
        UNKNOWN = "unknown"


# Paths for persistence
SCRIPT_DIR = Path(__file__).parent
PROPOSAL_HISTORY_FILE = SCRIPT_DIR / ".proposal_history.json"
PROPOSAL_FEEDBACK_FILE = SCRIPT_DIR / ".proposal_feedback.json"

# Safe command whitelist - commands that can be auto-executed without approval
SAFE_COMMANDS_WHITELIST = [
    # Read-only file operations
    "ls", "cat", "head", "tail", "less", "more", "file", "wc",
    "find", "locate", "which", "whereis", "type",

    # Read-only git operations
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote -v", "git stash list",

    # System info (read-only)
    "pwd", "whoami", "hostname", "uname", "date", "uptime",
    "df", "du", "free", "top -l 1", "ps", "env", "printenv",

    # Python/Node read-only
    "python --version", "python3 --version", "node --version",
    "npm list", "pip list", "pip show", "pip freeze",

    # Safe project operations
    "npm run lint", "npm run test", "pytest --collect-only",
    "cargo check", "cargo clippy", "rustfmt --check",
]

# Patterns for commands that always require approval
APPROVAL_REQUIRED_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+.*\*",
    r"sudo\s+",
    r"chmod\s+",
    r"chown\s+",
    r"mkfs",
    r"dd\s+if=",
    r">\s*/dev/",
    r"curl.*\|\s*sh",
    r"wget.*\|\s*sh",
    r"pip install",
    r"npm install",
    r"brew install",
    r"git push",
    r"git reset --hard",
    r"git checkout\s+\.",
    r"git clean",
]


@dataclass
class CommandProposal:
    """
    Represents a proposed command/action from SAM to the user.

    A proposal includes the command itself, reasoning, expected outcome,
    and risk assessment to help the user make an informed decision.

    Attributes:
        command: The actual command/code to execute
        command_type: Classification of the command (SAFE, MODIFICATION, etc.)
        description: Human-readable explanation of what this does
        reasoning: Why SAM thinks this action is needed
        expected_outcome: What should happen if successful
        risk_assessment: Potential risks or side effects
        alternatives: Other ways to achieve the same goal
        requires_approval: Whether user must explicitly approve
        auto_executable: Whether this can run without approval (whitelist)
        metadata: Additional context (project, files affected, etc.)
    """
    command: str
    command_type: CommandType
    description: str
    reasoning: str
    expected_outcome: str
    risk_assessment: str = "Low risk"
    alternatives: List[str] = field(default_factory=list)
    requires_approval: bool = True
    auto_executable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal tracking
    proposal_id: str = field(default_factory=lambda: "")
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending, approved, rejected, executed, failed

    def __post_init__(self):
        """Generate proposal ID and set auto-execution status."""
        if not self.proposal_id:
            # Generate unique ID from command and timestamp
            content = f"{self.command}:{self.created_at}"
            self.proposal_id = hashlib.md5(content.encode()).hexdigest()[:12]

        # Check if command is on whitelist
        if not self.auto_executable:
            self.auto_executable = self._is_safe_command()

        # Auto-executable commands don't require approval
        if self.auto_executable:
            self.requires_approval = False

    def _is_safe_command(self) -> bool:
        """Check if command is on the safe whitelist."""
        cmd_lower = self.command.lower().strip()

        # Check against approval-required patterns first
        for pattern in APPROVAL_REQUIRED_PATTERNS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
                return False

        # Check against safe whitelist
        for safe_cmd in SAFE_COMMANDS_WHITELIST:
            if cmd_lower.startswith(safe_cmd.lower()):
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proposal_id": self.proposal_id,
            "command": self.command,
            "command_type": self.command_type.value if isinstance(self.command_type, Enum) else self.command_type,
            "description": self.description,
            "reasoning": self.reasoning,
            "expected_outcome": self.expected_outcome,
            "risk_assessment": self.risk_assessment,
            "alternatives": self.alternatives,
            "requires_approval": self.requires_approval,
            "auto_executable": self.auto_executable,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandProposal":
        """Create from dictionary."""
        # Handle command_type conversion
        cmd_type = data.get("command_type", "unknown")
        if isinstance(cmd_type, str):
            try:
                cmd_type = CommandType(cmd_type)
            except ValueError:
                cmd_type = CommandType.UNKNOWN

        return cls(
            command=data["command"],
            command_type=cmd_type,
            description=data.get("description", ""),
            reasoning=data.get("reasoning", ""),
            expected_outcome=data.get("expected_outcome", ""),
            risk_assessment=data.get("risk_assessment", "Low risk"),
            alternatives=data.get("alternatives", []),
            requires_approval=data.get("requires_approval", True),
            auto_executable=data.get("auto_executable", False),
            metadata=data.get("metadata", {}),
            proposal_id=data.get("proposal_id", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            status=data.get("status", "pending"),
        )


@dataclass
class ExecutionResult:
    """
    Result of executing a proposed command.

    Captures success/failure, output, and any errors for display
    and learning purposes.
    """
    proposal_id: str
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    execution_time_ms: int = 0
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class CommandProposer:
    """
    Generates command proposals for tasks and problem fixes.

    The proposer analyzes problems and generates appropriate commands
    with full context about what the command does, why it's needed,
    and what risks it carries.

    Example:
        proposer = CommandProposer()

        # Propose a fix for a problem
        proposal = proposer.propose_fix(
            "Build failing with missing dependency",
            {"project": "sam_brain", "error": "ModuleNotFoundError: mlx"}
        )

        # Propose commands for a task
        proposals = proposer.propose_for_task(
            "Set up the development environment",
            {"project": "sam_brain", "language": "python"}
        )
    """

    def __init__(self, classifier: Optional["CommandClassifier"] = None):
        """
        Initialize the command proposer.

        Args:
            classifier: Optional CommandClassifier for command type detection
        """
        self.classifier = classifier
        self._init_classifier()
        self._pattern_db = self._load_patterns()

    def _init_classifier(self):
        """Initialize classifier if available."""
        if self.classifier is None and _command_classifier_available:
            try:
                self.classifier = CommandClassifier()
            except Exception:
                pass

    def _load_patterns(self) -> Dict[str, List[Dict]]:
        """
        Load common problem-solution patterns.

        Returns:
            Dictionary mapping problem types to solution patterns
        """
        return {
            "dependency_missing": [
                {
                    "pattern": r"ModuleNotFoundError:\s+(?:No module named\s+)?['\"]?(\w+)",
                    "solutions": [
                        {"cmd": "pip install {module}", "desc": "Install missing Python package"},
                        {"cmd": "pip install -r requirements.txt", "desc": "Install from requirements"},
                    ]
                },
                {
                    "pattern": r"Cannot find module ['\"](\w+)['\"]",
                    "solutions": [
                        {"cmd": "npm install {module}", "desc": "Install missing npm package"},
                        {"cmd": "npm install", "desc": "Install all dependencies"},
                    ]
                },
            ],
            "permission_denied": [
                {
                    "pattern": r"Permission denied:?\s*(.+)",
                    "solutions": [
                        {"cmd": "chmod +x {file}", "desc": "Make file executable"},
                        {"cmd": "ls -la {file}", "desc": "Check file permissions"},
                    ]
                },
            ],
            "file_not_found": [
                {
                    "pattern": r"(?:No such file|FileNotFoundError|ENOENT).*['\"]?([^'\"]+)['\"]?",
                    "solutions": [
                        {"cmd": "ls -la {dir}", "desc": "Check directory contents"},
                        {"cmd": "find . -name '{basename}' -type f", "desc": "Search for file"},
                    ]
                },
            ],
            "git_issues": [
                {
                    "pattern": r"error: Your local changes to the following files would be overwritten",
                    "solutions": [
                        {"cmd": "git stash", "desc": "Stash local changes temporarily"},
                        {"cmd": "git status", "desc": "Check current state"},
                    ]
                },
                {
                    "pattern": r"fatal: not a git repository",
                    "solutions": [
                        {"cmd": "git init", "desc": "Initialize git repository"},
                    ]
                },
            ],
            "build_failure": [
                {
                    "pattern": r"error\[E\d+\]:|error:",
                    "solutions": [
                        {"cmd": "cargo check", "desc": "Run Rust type checking"},
                        {"cmd": "cargo clean && cargo build", "desc": "Clean rebuild"},
                    ]
                },
                {
                    "pattern": r"SyntaxError|IndentationError",
                    "solutions": [
                        {"cmd": "python -m py_compile {file}", "desc": "Check Python syntax"},
                    ]
                },
            ],
        }

    def _classify_command(self, command: str) -> CommandType:
        """
        Classify a command by its type/risk level.

        Args:
            command: The command to classify

        Returns:
            CommandType enum value
        """
        if self.classifier:
            try:
                return self.classifier.classify(command)
            except Exception:
                pass

        # Fallback classification based on patterns
        cmd_lower = command.lower()

        # Destructive commands
        if any(p in cmd_lower for p in ["rm -rf", "rm -r", "rmdir", "git reset --hard"]):
            return CommandType.DESTRUCTIVE

        # Network commands
        if any(p in cmd_lower for p in ["curl", "wget", "ssh", "scp", "rsync"]):
            return CommandType.NETWORK

        # System commands
        if any(p in cmd_lower for p in ["sudo", "systemctl", "launchctl", "chmod", "chown"]):
            return CommandType.SYSTEM

        # Modification commands
        if any(p in cmd_lower for p in ["mkdir", "touch", "mv", "cp", "pip install", "npm install", "git commit", "git push"]):
            return CommandType.MODIFICATION

        # Read-only / safe commands
        if any(p in cmd_lower for p in ["ls", "cat", "head", "tail", "grep", "find", "git status", "git log"]):
            return CommandType.SAFE

        return CommandType.UNKNOWN

    def _assess_risk(self, command: str, command_type: CommandType) -> str:
        """
        Assess the risk level of a command.

        Args:
            command: The command to assess
            command_type: The classified type

        Returns:
            Risk assessment string
        """
        if command_type == CommandType.DESTRUCTIVE:
            return "HIGH RISK: This command makes irreversible changes. Data may be permanently deleted."

        if command_type == CommandType.SYSTEM:
            return "MEDIUM-HIGH RISK: System-level changes may affect stability."

        if command_type == CommandType.NETWORK:
            return "MEDIUM RISK: Network operations may expose data or download untrusted content."

        if command_type == CommandType.MODIFICATION:
            return "LOW-MEDIUM RISK: File modifications can be reverted if using version control."

        if command_type == CommandType.SAFE:
            return "LOW RISK: Read-only operation with no side effects."

        return "UNKNOWN RISK: Could not assess this command. Review carefully."

    def propose_fix(
        self,
        problem_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CommandProposal:
        """
        Propose a fix for a described problem.

        Analyzes the problem description and context to generate
        an appropriate command proposal with reasoning.

        Args:
            problem_description: Description of the problem (e.g., error message)
            context: Additional context like project name, file paths, etc.

        Returns:
            CommandProposal with suggested fix

        Example:
            proposal = proposer.propose_fix(
                "ModuleNotFoundError: No module named 'mlx'",
                {"project": "sam_brain", "python_version": "3.12"}
            )
        """
        context = context or {}

        # Try to match against known patterns
        for problem_type, patterns in self._pattern_db.items():
            for pattern_info in patterns:
                match = re.search(pattern_info["pattern"], problem_description, re.IGNORECASE)
                if match:
                    # Found a matching pattern
                    solutions = pattern_info["solutions"]
                    if solutions:
                        solution = solutions[0]  # Take first solution

                        # Substitute captured groups into command
                        cmd = solution["cmd"]
                        groups = match.groups()
                        if groups:
                            cmd = cmd.format(
                                module=groups[0] if groups else "",
                                file=groups[0] if groups else "",
                                dir=os.path.dirname(groups[0]) if groups else ".",
                                basename=os.path.basename(groups[0]) if groups else "",
                            )

                        cmd_type = self._classify_command(cmd)

                        # Build alternatives from other solutions
                        alternatives = [
                            s["cmd"].format(
                                module=groups[0] if groups else "",
                                file=groups[0] if groups else "",
                            )
                            for s in solutions[1:]
                        ]

                        return CommandProposal(
                            command=cmd,
                            command_type=cmd_type,
                            description=solution["desc"],
                            reasoning=f"Detected {problem_type.replace('_', ' ')} pattern in: {problem_description[:100]}",
                            expected_outcome=f"Should resolve the {problem_type.replace('_', ' ')} issue",
                            risk_assessment=self._assess_risk(cmd, cmd_type),
                            alternatives=alternatives,
                            metadata={
                                "problem_type": problem_type,
                                "matched_pattern": pattern_info["pattern"],
                                "context": context,
                            }
                        )

        # No pattern matched - generate generic proposal
        return CommandProposal(
            command="# Unable to generate specific command",
            command_type=CommandType.UNKNOWN,
            description="Manual intervention needed",
            reasoning=f"Could not automatically determine fix for: {problem_description[:100]}",
            expected_outcome="Requires manual review and action",
            risk_assessment="Cannot assess risk without specific command",
            alternatives=[
                "Review error logs for more details",
                "Search documentation for similar issues",
                "Ask for help with more context",
            ],
            metadata={"problem_description": problem_description, "context": context}
        )

    def propose_for_task(
        self,
        task: str,
        project_context: Optional[Dict[str, Any]] = None
    ) -> List[CommandProposal]:
        """
        Propose a sequence of commands to accomplish a task.

        Analyzes the task description and generates a list of
        commands that together accomplish the goal.

        Args:
            task: Description of what needs to be done
            project_context: Context about the project (language, framework, etc.)

        Returns:
            List of CommandProposals in recommended execution order

        Example:
            proposals = proposer.propose_for_task(
                "Set up development environment",
                {"project": "sam_brain", "language": "python", "path": "/path/to/project"}
            )
        """
        project_context = project_context or {}
        proposals = []

        task_lower = task.lower()
        project_path = project_context.get("path", ".")
        language = project_context.get("language", "").lower()
        framework = project_context.get("framework", "").lower()

        # Development environment setup
        if any(kw in task_lower for kw in ["setup", "set up", "initialize", "init"]):
            if "env" in task_lower or "environment" in task_lower:
                # Python project
                if language == "python" or os.path.exists(os.path.join(project_path, "requirements.txt")):
                    proposals.extend([
                        CommandProposal(
                            command=f"cd {project_path} && python3 -m venv .venv",
                            command_type=CommandType.MODIFICATION,
                            description="Create Python virtual environment",
                            reasoning="Isolated Python environment prevents dependency conflicts",
                            expected_outcome="Creates .venv directory with clean Python installation",
                        ),
                        CommandProposal(
                            command=f"source {project_path}/.venv/bin/activate && pip install -r requirements.txt",
                            command_type=CommandType.MODIFICATION,
                            description="Install Python dependencies",
                            reasoning="Install all required packages from requirements.txt",
                            expected_outcome="All dependencies installed in virtual environment",
                        ),
                    ])

                # Node.js project
                if language in ["javascript", "typescript", "node"] or os.path.exists(os.path.join(project_path, "package.json")):
                    proposals.extend([
                        CommandProposal(
                            command=f"cd {project_path} && npm install",
                            command_type=CommandType.MODIFICATION,
                            description="Install Node.js dependencies",
                            reasoning="Install all required npm packages from package.json",
                            expected_outcome="All dependencies installed in node_modules",
                        ),
                    ])

                # Rust project
                if language == "rust" or os.path.exists(os.path.join(project_path, "Cargo.toml")):
                    proposals.extend([
                        CommandProposal(
                            command=f"cd {project_path} && cargo build",
                            command_type=CommandType.MODIFICATION,
                            description="Build Rust project",
                            reasoning="Compile project and download dependencies",
                            expected_outcome="Project compiled with dependencies in target/",
                        ),
                    ])

        # Git operations
        if "git" in task_lower or "commit" in task_lower or "push" in task_lower:
            if "status" in task_lower:
                proposals.append(CommandProposal(
                    command=f"cd {project_path} && git status",
                    command_type=CommandType.SAFE,
                    description="Check git status",
                    reasoning="See current state of working directory",
                    expected_outcome="Shows modified/staged/untracked files",
                ))

            if "commit" in task_lower:
                proposals.extend([
                    CommandProposal(
                        command=f"cd {project_path} && git add -A",
                        command_type=CommandType.MODIFICATION,
                        description="Stage all changes",
                        reasoning="Add all modified and new files to staging",
                        expected_outcome="All changes ready for commit",
                        alternatives=[f"git add {project_path}/<specific-file>"],
                    ),
                    CommandProposal(
                        command=f'cd {project_path} && git commit -m "Your commit message here"',
                        command_type=CommandType.MODIFICATION,
                        description="Create commit",
                        reasoning="Save staged changes with a message",
                        expected_outcome="New commit created on current branch",
                    ),
                ])

            if "push" in task_lower:
                proposals.append(CommandProposal(
                    command=f"cd {project_path} && git push origin HEAD",
                    command_type=CommandType.NETWORK,
                    description="Push changes to remote",
                    reasoning="Upload local commits to remote repository",
                    expected_outcome="Changes available on remote (e.g., GitHub)",
                    risk_assessment="MEDIUM: Pushes code to remote. Ensure you're on correct branch.",
                ))

        # Testing
        if any(kw in task_lower for kw in ["test", "testing"]):
            if language == "python":
                proposals.append(CommandProposal(
                    command=f"cd {project_path} && pytest -v",
                    command_type=CommandType.SAFE,
                    description="Run Python tests",
                    reasoning="Execute pytest test suite with verbose output",
                    expected_outcome="Test results showing pass/fail status",
                    alternatives=["pytest --collect-only", "pytest -x (stop on first failure)"],
                ))
            elif language in ["javascript", "typescript", "node"]:
                proposals.append(CommandProposal(
                    command=f"cd {project_path} && npm test",
                    command_type=CommandType.SAFE,
                    description="Run JavaScript tests",
                    reasoning="Execute test script from package.json",
                    expected_outcome="Test results from configured test runner",
                ))
            elif language == "rust":
                proposals.append(CommandProposal(
                    command=f"cd {project_path} && cargo test",
                    command_type=CommandType.SAFE,
                    description="Run Rust tests",
                    reasoning="Execute cargo test suite",
                    expected_outcome="Test results showing pass/fail status",
                ))

        # Linting / formatting
        if any(kw in task_lower for kw in ["lint", "format", "style"]):
            if language == "python":
                proposals.extend([
                    CommandProposal(
                        command=f"cd {project_path} && black .",
                        command_type=CommandType.MODIFICATION,
                        description="Format Python code with Black",
                        reasoning="Auto-format code to consistent style",
                        expected_outcome="All Python files formatted consistently",
                        alternatives=["black --check . (dry run)"],
                    ),
                    CommandProposal(
                        command=f"cd {project_path} && ruff check .",
                        command_type=CommandType.SAFE,
                        description="Lint Python code with Ruff",
                        reasoning="Check for code quality issues",
                        expected_outcome="List of any linting issues found",
                    ),
                ])
            elif language == "rust":
                proposals.extend([
                    CommandProposal(
                        command=f"cd {project_path} && cargo fmt",
                        command_type=CommandType.MODIFICATION,
                        description="Format Rust code",
                        reasoning="Auto-format with rustfmt",
                        expected_outcome="All Rust files formatted consistently",
                    ),
                    CommandProposal(
                        command=f"cd {project_path} && cargo clippy",
                        command_type=CommandType.SAFE,
                        description="Lint Rust code with Clippy",
                        reasoning="Check for common mistakes and improvements",
                        expected_outcome="List of any linting suggestions",
                    ),
                ])

        # If no specific proposals generated, provide generic exploration
        if not proposals:
            proposals.append(CommandProposal(
                command=f"cd {project_path} && ls -la",
                command_type=CommandType.SAFE,
                description="Explore project structure",
                reasoning=f"First step: understand the project layout for task: {task[:50]}",
                expected_outcome="Directory listing to inform next steps",
                alternatives=[
                    f"cd {project_path} && tree -L 2 (if tree is installed)",
                    f"cd {project_path} && find . -type f -name '*.py' | head -20",
                ],
            ))

        return proposals


class ProposalFormatter:
    """
    Formats CommandProposals for different output contexts.

    Supports:
    - Terminal/chat display (markdown)
    - GUI display (structured JSON for UI rendering)
    - Compact display (single line summary)
    """

    # Risk level colors/indicators for terminal
    RISK_INDICATORS = {
        "high": "[!!!]",
        "medium-high": "[!!]",
        "medium": "[!]",
        "low-medium": "[.]",
        "low": "[~]",
        "unknown": "[?]",
    }

    @staticmethod
    def format_for_chat(proposal: CommandProposal) -> str:
        """
        Format a proposal as markdown for terminal/chat display.

        Creates a human-readable summary with clear sections for
        command, reasoning, risks, and approval options.

        Args:
            proposal: The CommandProposal to format

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Header with risk indicator
        risk_level = ProposalFormatter._extract_risk_level(proposal.risk_assessment)
        indicator = ProposalFormatter.RISK_INDICATORS.get(risk_level, "[?]")

        lines.append(f"## {indicator} SAM Proposes: {proposal.description}")
        lines.append("")

        # Command block
        lines.append("**Command:**")
        lines.append(f"```bash")
        lines.append(proposal.command)
        lines.append("```")
        lines.append("")

        # Type badge
        type_badge = proposal.command_type.value.upper() if isinstance(proposal.command_type, Enum) else str(proposal.command_type).upper()
        lines.append(f"**Type:** `{type_badge}`")
        lines.append("")

        # Reasoning
        lines.append("**Why this command?**")
        lines.append(f"> {proposal.reasoning}")
        lines.append("")

        # Expected outcome
        lines.append("**Expected outcome:**")
        lines.append(f"> {proposal.expected_outcome}")
        lines.append("")

        # Risk assessment
        lines.append("**Risk assessment:**")
        lines.append(f"> {proposal.risk_assessment}")
        lines.append("")

        # Alternatives
        if proposal.alternatives:
            lines.append("**Alternatives:**")
            for alt in proposal.alternatives:
                lines.append(f"- `{alt}`")
            lines.append("")

        # Approval section
        if proposal.requires_approval:
            lines.append("---")
            lines.append("**Action required:** This command needs your approval.")
            lines.append("")
            lines.append("- Reply `yes` or `approve` to execute")
            lines.append("- Reply `no` or `reject` to cancel")
            lines.append("- Reply `modify` to suggest changes")
        elif proposal.auto_executable:
            lines.append("---")
            lines.append("**Auto-executable:** This is a safe read-only command.")
            lines.append("SAM can execute this automatically.")

        return "\n".join(lines)

    @staticmethod
    def format_for_gui(proposal: CommandProposal) -> Dict[str, Any]:
        """
        Format a proposal as structured JSON for GUI display.

        Returns a dictionary that can be rendered by a frontend
        with proper styling, buttons, and interactive elements.

        Args:
            proposal: The CommandProposal to format

        Returns:
            Dictionary with structured proposal data
        """
        risk_level = ProposalFormatter._extract_risk_level(proposal.risk_assessment)

        return {
            "id": proposal.proposal_id,
            "type": "command_proposal",

            # Display content
            "title": proposal.description,
            "command": proposal.command,
            "command_language": "bash",  # For syntax highlighting

            # Classification
            "command_type": proposal.command_type.value if isinstance(proposal.command_type, Enum) else str(proposal.command_type),
            "risk_level": risk_level,
            "risk_color": ProposalFormatter._risk_to_color(risk_level),

            # Details
            "reasoning": proposal.reasoning,
            "expected_outcome": proposal.expected_outcome,
            "risk_assessment": proposal.risk_assessment,
            "alternatives": proposal.alternatives,

            # Interaction
            "requires_approval": proposal.requires_approval,
            "auto_executable": proposal.auto_executable,
            "actions": ProposalFormatter._get_actions(proposal),

            # Metadata
            "created_at": proposal.created_at,
            "status": proposal.status,
            "metadata": proposal.metadata,
        }

    @staticmethod
    def format_compact(proposal: CommandProposal) -> str:
        """
        Format a proposal as a single-line summary.

        Useful for lists and logs where space is limited.

        Args:
            proposal: The CommandProposal to format

        Returns:
            Single-line summary string
        """
        risk_level = ProposalFormatter._extract_risk_level(proposal.risk_assessment)
        indicator = ProposalFormatter.RISK_INDICATORS.get(risk_level, "[?]")

        approval = "*" if proposal.requires_approval else ""
        auto = "(auto)" if proposal.auto_executable else ""

        cmd_preview = proposal.command[:50] + "..." if len(proposal.command) > 50 else proposal.command

        return f"{indicator}{approval} {proposal.description}: `{cmd_preview}` {auto}".strip()

    @staticmethod
    def _extract_risk_level(risk_assessment: str) -> str:
        """Extract risk level from assessment text."""
        risk_lower = risk_assessment.lower()
        if "high" in risk_lower and "medium" not in risk_lower:
            return "high"
        if "medium-high" in risk_lower:
            return "medium-high"
        if "medium" in risk_lower:
            return "medium"
        if "low-medium" in risk_lower:
            return "low-medium"
        if "low" in risk_lower:
            return "low"
        return "unknown"

    @staticmethod
    def _risk_to_color(risk_level: str) -> str:
        """Map risk level to UI color."""
        return {
            "high": "#dc3545",      # Red
            "medium-high": "#fd7e14",  # Orange
            "medium": "#ffc107",    # Yellow
            "low-medium": "#20c997",   # Teal
            "low": "#28a745",       # Green
            "unknown": "#6c757d",   # Gray
        }.get(risk_level, "#6c757d")

    @staticmethod
    def _get_actions(proposal: CommandProposal) -> List[Dict[str, Any]]:
        """Get available actions for a proposal."""
        actions = []

        if proposal.requires_approval:
            actions.extend([
                {
                    "id": "approve",
                    "label": "Approve & Execute",
                    "icon": "check",
                    "style": "primary",
                    "keyboard_shortcut": "y",
                },
                {
                    "id": "reject",
                    "label": "Reject",
                    "icon": "x",
                    "style": "secondary",
                    "keyboard_shortcut": "n",
                },
                {
                    "id": "modify",
                    "label": "Modify",
                    "icon": "edit",
                    "style": "secondary",
                    "keyboard_shortcut": "m",
                },
            ])
        elif proposal.auto_executable:
            actions.append({
                "id": "execute",
                "label": "Execute",
                "icon": "play",
                "style": "primary",
                "keyboard_shortcut": "enter",
            })

        # Always allow copying
        actions.append({
            "id": "copy",
            "label": "Copy Command",
            "icon": "clipboard",
            "style": "link",
            "keyboard_shortcut": "c",
        })

        return actions

    @staticmethod
    def format_execution_result(result: ExecutionResult) -> str:
        """
        Format an execution result for display.

        Shows success/failure status, output, errors, and
        suggestions for next steps if the command failed.

        Args:
            result: The ExecutionResult to format

        Returns:
            Markdown-formatted result string
        """
        lines = []

        # Status header
        if result.success:
            lines.append("## [SUCCESS] Command Executed Successfully")
        else:
            lines.append("## [FAILED] Command Execution Failed")

        lines.append("")

        # Timing
        lines.append(f"**Execution time:** {result.execution_time_ms}ms")
        lines.append(f"**Return code:** {result.return_code}")
        lines.append("")

        # Output
        if result.output:
            lines.append("**Output:**")
            lines.append("```")
            # Truncate very long output
            output = result.output
            if len(output) > 2000:
                output = output[:2000] + "\n... (truncated)"
            lines.append(output)
            lines.append("```")
            lines.append("")

        # Error
        if result.error:
            lines.append("**Error:**")
            lines.append("```")
            lines.append(result.error)
            lines.append("```")
            lines.append("")

            # Suggestions for failure
            lines.append("**Suggested next steps:**")
            lines.append("- Review the error message above")
            lines.append("- Check if required dependencies are installed")
            lines.append("- Verify file paths and permissions")
            lines.append("- Ask SAM to propose a fix for this error")

        return "\n".join(lines)


class ProposalHistory:
    """
    Tracks proposal history and learns from outcomes.

    Maintains a record of all proposals, their outcomes,
    and learns patterns to improve future proposals.
    """

    def __init__(self, history_file: Path = PROPOSAL_HISTORY_FILE,
                 feedback_file: Path = PROPOSAL_FEEDBACK_FILE):
        """
        Initialize the proposal history tracker.

        Args:
            history_file: Path to store proposal history
            feedback_file: Path to store feedback data
        """
        self.history_file = history_file
        self.feedback_file = feedback_file
        self._history: Dict[str, Dict] = self._load_history()
        self._feedback: Dict[str, Dict] = self._load_feedback()
        self._patterns: Dict[str, float] = {}  # Learned success patterns

    def _load_history(self) -> Dict[str, Dict]:
        """Load proposal history from disk."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except Exception:
                pass
        return {}

    def _save_history(self):
        """Save proposal history to disk."""
        self.history_file.write_text(json.dumps(self._history, indent=2, default=str))

    def _load_feedback(self) -> Dict[str, Dict]:
        """Load feedback data from disk."""
        if self.feedback_file.exists():
            try:
                return json.loads(self.feedback_file.read_text())
            except Exception:
                pass
        return {}

    def _save_feedback(self):
        """Save feedback data to disk."""
        self.feedback_file.write_text(json.dumps(self._feedback, indent=2, default=str))

    def record_proposal(self, proposal: CommandProposal):
        """
        Record a new proposal in history.

        Args:
            proposal: The proposal to record
        """
        self._history[proposal.proposal_id] = {
            **proposal.to_dict(),
            "recorded_at": datetime.now().isoformat(),
        }
        self._save_history()

    def record_outcome(
        self,
        proposal_id: str,
        accepted: bool,
        result: Optional[ExecutionResult] = None,
        feedback: str = ""
    ):
        """
        Record the outcome of a proposal.

        Args:
            proposal_id: ID of the proposal
            accepted: Whether the user approved it
            result: Execution result if executed
            feedback: Optional user feedback
        """
        if proposal_id not in self._history:
            return

        # Update history
        self._history[proposal_id]["status"] = "approved" if accepted else "rejected"
        if result:
            self._history[proposal_id]["execution_result"] = result.to_dict()
            self._history[proposal_id]["status"] = "executed" if result.success else "failed"

        self._save_history()

        # Record feedback for learning
        proposal = self._history[proposal_id]
        self._record_feedback_pattern(proposal, accepted, result, feedback)

    def _record_feedback_pattern(
        self,
        proposal: Dict,
        accepted: bool,
        result: Optional[ExecutionResult],
        feedback: str
    ):
        """Record patterns from feedback for learning."""
        # Key patterns to learn from
        cmd_type = proposal.get("command_type", "unknown")
        problem_type = proposal.get("metadata", {}).get("problem_type", "unknown")

        # Build feedback key
        pattern_key = f"{problem_type}:{cmd_type}"

        if pattern_key not in self._feedback:
            self._feedback[pattern_key] = {
                "accepted": 0,
                "rejected": 0,
                "executed_success": 0,
                "executed_failed": 0,
                "feedback_samples": [],
            }

        pattern = self._feedback[pattern_key]

        if accepted:
            pattern["accepted"] += 1
            if result:
                if result.success:
                    pattern["executed_success"] += 1
                else:
                    pattern["executed_failed"] += 1
        else:
            pattern["rejected"] += 1

        if feedback:
            pattern["feedback_samples"].append({
                "feedback": feedback,
                "accepted": accepted,
                "timestamp": datetime.now().isoformat(),
            })
            # Keep only last 10 feedback samples
            pattern["feedback_samples"] = pattern["feedback_samples"][-10:]

        self._save_feedback()
        self._update_patterns()

    def _update_patterns(self):
        """Update learned pattern scores."""
        for pattern_key, data in self._feedback.items():
            total = data["accepted"] + data["rejected"]
            if total > 0:
                # Success rate weighted by execution success
                base_rate = data["accepted"] / total
                exec_total = data["executed_success"] + data["executed_failed"]
                if exec_total > 0:
                    exec_rate = data["executed_success"] / exec_total
                    # Combine acceptance rate and execution success
                    self._patterns[pattern_key] = (base_rate * 0.4) + (exec_rate * 0.6)
                else:
                    self._patterns[pattern_key] = base_rate

    def get_pattern_score(self, problem_type: str, cmd_type: str) -> float:
        """
        Get the learned success score for a pattern.

        Returns a value between 0 and 1 indicating how likely
        this type of proposal is to be accepted and succeed.

        Args:
            problem_type: Type of problem (e.g., "dependency_missing")
            cmd_type: Type of command (e.g., "modification")

        Returns:
            Success score (0-1), or 0.5 if no data
        """
        pattern_key = f"{problem_type}:{cmd_type}"
        return self._patterns.get(pattern_key, 0.5)

    def get_pending_proposals(self) -> List[Dict]:
        """Get all pending (unapproved) proposals."""
        return [
            p for p in self._history.values()
            if p.get("status") == "pending"
        ]

    def get_recent_proposals(self, limit: int = 10) -> List[Dict]:
        """Get most recent proposals."""
        sorted_proposals = sorted(
            self._history.values(),
            key=lambda p: p.get("created_at", ""),
            reverse=True
        )
        return sorted_proposals[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get proposal statistics."""
        total = len(self._history)
        statuses = defaultdict(int)
        for p in self._history.values():
            statuses[p.get("status", "unknown")] += 1

        return {
            "total_proposals": total,
            "by_status": dict(statuses),
            "acceptance_rate": (statuses.get("approved", 0) + statuses.get("executed", 0)) / total if total > 0 else 0,
            "execution_success_rate": statuses.get("executed", 0) / (statuses.get("executed", 0) + statuses.get("failed", 0)) if (statuses.get("executed", 0) + statuses.get("failed", 0)) > 0 else 0,
            "learned_patterns": len(self._patterns),
        }

    def clear_old_proposals(self, days: int = 30):
        """
        Clear proposals older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        self._history = {
            pid: p for pid, p in self._history.items()
            if p.get("created_at", "") > cutoff_str
        }
        self._save_history()


# Convenience functions for integration

def propose_fix(problem: str, context: Dict = None) -> CommandProposal:
    """
    Quick function to propose a fix for a problem.

    Args:
        problem: Description of the problem
        context: Optional context dictionary

    Returns:
        CommandProposal with suggested fix
    """
    proposer = CommandProposer()
    return proposer.propose_fix(problem, context)


def propose_task(task: str, project_context: Dict = None) -> List[CommandProposal]:
    """
    Quick function to propose commands for a task.

    Args:
        task: Description of what needs to be done
        project_context: Optional project context

    Returns:
        List of CommandProposals
    """
    proposer = CommandProposer()
    return proposer.propose_for_task(task, project_context)


def format_proposal(proposal: CommandProposal, format_type: str = "chat") -> Union[str, Dict]:
    """
    Format a proposal for display.

    Args:
        proposal: The proposal to format
        format_type: "chat" (markdown), "gui" (JSON), or "compact"

    Returns:
        Formatted string or dictionary
    """
    if format_type == "gui":
        return ProposalFormatter.format_for_gui(proposal)
    elif format_type == "compact":
        return ProposalFormatter.format_compact(proposal)
    else:
        return ProposalFormatter.format_for_chat(proposal)


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Command Proposal System")
        print("=" * 40)
        print("\nUsage:")
        print("  command_proposer.py fix <problem_description>")
        print("  command_proposer.py task <task_description>")
        print("  command_proposer.py history")
        print("  command_proposer.py stats")
        print("\nExamples:")
        print('  command_proposer.py fix "ModuleNotFoundError: No module named mlx"')
        print('  command_proposer.py task "Set up development environment"')
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "fix" and len(sys.argv) > 2:
        problem = " ".join(sys.argv[2:])
        proposal = propose_fix(problem)
        print(format_proposal(proposal, "chat"))

    elif cmd == "task" and len(sys.argv) > 2:
        task = " ".join(sys.argv[2:])
        proposals = propose_task(task)
        for i, proposal in enumerate(proposals, 1):
            print(f"\n{'=' * 40}")
            print(f"Step {i} of {len(proposals)}")
            print(format_proposal(proposal, "chat"))

    elif cmd == "history":
        history = ProposalHistory()
        recent = history.get_recent_proposals(10)
        print(f"\nRecent Proposals ({len(recent)}):")
        print("-" * 40)
        for p in recent:
            status = p.get("status", "unknown")
            desc = p.get("description", "No description")[:50]
            print(f"[{status}] {desc}")

    elif cmd == "stats":
        history = ProposalHistory()
        stats = history.get_statistics()
        print("\nProposal Statistics:")
        print("-" * 40)
        print(f"Total proposals: {stats['total_proposals']}")
        print(f"Acceptance rate: {stats['acceptance_rate']:.1%}")
        print(f"Execution success rate: {stats['execution_success_rate']:.1%}")
        print(f"Learned patterns: {stats['learned_patterns']}")
        print("\nBy status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")

    else:
        print(f"Unknown command: {cmd}")
        print("Use --help for usage information")
