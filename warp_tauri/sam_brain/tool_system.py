#!/usr/bin/env python3
"""
SAM Tool System - Claude Code-equivalent capabilities

This gives SAM the same tool-calling abilities as Claude Code:
- File operations (read, write, edit, glob, grep)
- Bash execution with safety
- Git operations
- Web fetching
- Multi-step planning
- Task tracking

The key difference: SAM runs these tools LOCALLY with full system access,
while Claude Code runs them through a sandboxed proxy.

SAM advantage: No API costs, no rate limits, full disk access.
"""

import os
import re
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import fnmatch
import difflib


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

class ToolCategory(Enum):
    FILE = "file"
    SEARCH = "search"
    BASH = "bash"
    GIT = "git"
    WEB = "web"
    PLANNING = "planning"
    MEMORY = "memory"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Tool:
    """Definition of a tool SAM can use."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Dict]  # param_name -> {type, required, description}
    handler: Callable
    safety_level: str = "safe"  # safe, caution, dangerous


# =============================================================================
# FILE TOOLS
# =============================================================================

class FileTools:
    """File operation tools matching Claude Code capabilities."""

    @staticmethod
    def read(file_path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
        """Read a file with optional line range."""
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return ToolResult(False, "", f"File not found: {file_path}")

            if path.is_dir():
                return ToolResult(False, "", f"Path is a directory: {file_path}")

            # Handle binary files
            if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip']:
                return ToolResult(
                    True,
                    f"[Binary file: {path.suffix}, {path.stat().st_size} bytes]",
                    metadata={"binary": True, "size": path.stat().st_size}
                )

            content = path.read_text(errors='replace')
            lines = content.split('\n')

            # Apply offset and limit
            if offset > 0 or limit < len(lines):
                lines = lines[offset:offset + limit]

            # Add line numbers
            numbered = [f"{i + offset + 1:>6}\t{line}" for i, line in enumerate(lines)]

            return ToolResult(
                True,
                '\n'.join(numbered),
                metadata={"total_lines": len(content.split('\n')), "shown": len(lines)}
            )

        except Exception as e:
            return ToolResult(False, "", str(e))

    @staticmethod
    def write(file_path: str, content: str) -> ToolResult:
        """Write content to a file."""
        try:
            path = Path(file_path).expanduser()

            # Safety: Don't write to system directories
            dangerous_prefixes = ['/System', '/usr', '/bin', '/sbin', '/Library']
            for prefix in dangerous_prefixes:
                if str(path).startswith(prefix):
                    return ToolResult(False, "", f"Cannot write to system directory: {prefix}")

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Check if overwriting
            existed = path.exists()
            old_content = path.read_text() if existed else None

            path.write_text(content)

            return ToolResult(
                True,
                f"{'Overwrote' if existed else 'Created'} {file_path} ({len(content)} bytes)",
                metadata={"existed": existed, "bytes": len(content)}
            )

        except Exception as e:
            return ToolResult(False, "", str(e))

    @staticmethod
    def edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        """Edit a file by replacing old_string with new_string."""
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return ToolResult(False, "", f"File not found: {file_path}")

            content = path.read_text()

            # Check if old_string exists
            if old_string not in content:
                return ToolResult(False, "", f"String not found in file:\n{old_string[:100]}...")

            # Check uniqueness unless replace_all
            if not replace_all and content.count(old_string) > 1:
                return ToolResult(
                    False, "",
                    f"String appears {content.count(old_string)} times. Use replace_all=True or provide more context."
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1

            path.write_text(new_content)

            return ToolResult(
                True,
                f"Replaced {count} occurrence(s) in {file_path}",
                metadata={"replacements": count}
            )

        except Exception as e:
            return ToolResult(False, "", str(e))

    @staticmethod
    def glob(pattern: str, path: str = ".") -> ToolResult:
        """Find files matching a glob pattern."""
        try:
            base = Path(path).expanduser()
            if not base.exists():
                return ToolResult(False, "", f"Path not found: {path}")

            matches = list(base.glob(pattern))

            # Sort by modification time, newest first
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Limit results
            matches = matches[:100]

            output = '\n'.join(str(m) for m in matches)

            return ToolResult(
                True,
                output or "No matches found",
                metadata={"count": len(matches)}
            )

        except Exception as e:
            return ToolResult(False, "", str(e))

    @staticmethod
    def grep(
        pattern: str,
        path: str = ".",
        glob_filter: str = None,
        case_insensitive: bool = False,
        context_lines: int = 0
    ) -> ToolResult:
        """Search for pattern in files using ripgrep."""
        try:
            cmd = ["rg", "--no-heading", "--line-number"]

            if case_insensitive:
                cmd.append("-i")

            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])

            if glob_filter:
                cmd.extend(["--glob", glob_filter])

            cmd.extend([pattern, path])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout
            if len(output) > 30000:
                output = output[:30000] + "\n... (truncated)"

            return ToolResult(
                True,
                output or "No matches found",
                metadata={"exit_code": result.returncode}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(False, "", "Search timed out")
        except FileNotFoundError:
            # Fallback to grep if rg not available
            return FileTools._grep_fallback(pattern, path, glob_filter, case_insensitive)
        except Exception as e:
            return ToolResult(False, "", str(e))

    @staticmethod
    def _grep_fallback(pattern, path, glob_filter, case_insensitive):
        """Fallback grep using Python."""
        try:
            base = Path(path).expanduser()
            matches = []

            glob_pattern = glob_filter or "**/*"
            for file_path in base.glob(glob_pattern):
                if not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text(errors='replace')
                    flags = re.IGNORECASE if case_insensitive else 0
                    for i, line in enumerate(content.split('\n'), 1):
                        if re.search(pattern, line, flags):
                            matches.append(f"{file_path}:{i}:{line}")
                except:
                    continue

            return ToolResult(
                True,
                '\n'.join(matches[:100]) or "No matches found",
                metadata={"count": len(matches)}
            )
        except Exception as e:
            return ToolResult(False, "", str(e))


# =============================================================================
# BASH TOOLS
# =============================================================================

class BashTools:
    """Bash execution with safety checks."""

    # Commands that are always safe
    SAFE_COMMANDS = {
        'ls', 'pwd', 'whoami', 'date', 'echo', 'cat', 'head', 'tail',
        'wc', 'sort', 'uniq', 'grep', 'find', 'which', 'type',
        'python3', 'python', 'pip', 'npm', 'node', 'git', 'brew',
        'cargo', 'rustc', 'go', 'swift', 'swiftc', 'xcodebuild',
        'make', 'cmake', 'gcc', 'g++', 'clang',
    }

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+~',
        r'sudo\s+rm',
        r'>\s*/dev/',
        r'dd\s+if=',
        r'mkfs',
        r':\(\)\{',  # Fork bomb
        r'chmod\s+-R\s+777',
        r'curl.*\|\s*bash',
        r'wget.*\|\s*bash',
    ]

    @classmethod
    def execute(
        cls,
        command: str,
        cwd: str = None,
        timeout: int = 120,
        allow_dangerous: bool = False
    ) -> ToolResult:
        """Execute a bash command with safety checks."""

        # Safety check
        if not allow_dangerous:
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return ToolResult(
                        False, "",
                        f"Blocked dangerous command pattern: {pattern}"
                    )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or os.getcwd(),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'LANG': 'en_US.UTF-8'}
            )

            output = result.stdout + result.stderr
            if len(output) > 30000:
                output = output[:30000] + "\n... (truncated)"

            return ToolResult(
                result.returncode == 0,
                output,
                error=None if result.returncode == 0 else f"Exit code: {result.returncode}",
                metadata={"exit_code": result.returncode}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(False, "", f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, "", str(e))


# =============================================================================
# GIT TOOLS
# =============================================================================

class GitTools:
    """Git operations with safety rules."""

    # Operations that are safe
    SAFE_OPS = {'status', 'diff', 'log', 'branch', 'show', 'ls-files', 'remote'}

    # Operations that need confirmation
    CAUTION_OPS = {'add', 'commit', 'checkout', 'merge', 'rebase', 'stash'}

    # Operations that are dangerous
    DANGEROUS_OPS = {'push --force', 'reset --hard', 'clean -f', 'branch -D'}

    @classmethod
    def status(cls, cwd: str = None) -> ToolResult:
        """Get git status."""
        return BashTools.execute("git status", cwd=cwd)

    @classmethod
    def diff(cls, staged: bool = False, cwd: str = None) -> ToolResult:
        """Get git diff."""
        cmd = "git diff --staged" if staged else "git diff"
        return BashTools.execute(cmd, cwd=cwd)

    @classmethod
    def log(cls, count: int = 10, oneline: bool = True, cwd: str = None) -> ToolResult:
        """Get git log."""
        format_str = "--oneline" if oneline else "--pretty=format:'%h %s (%an, %ar)'"
        cmd = f"git log -{count} {format_str}"
        return BashTools.execute(cmd, cwd=cwd)

    @classmethod
    def add(cls, files: List[str], cwd: str = None) -> ToolResult:
        """Stage files for commit."""
        if not files:
            return ToolResult(False, "", "No files specified")

        # Don't use 'git add .' - be explicit
        file_list = ' '.join(f'"{f}"' for f in files)
        cmd = f"git add {file_list}"
        return BashTools.execute(cmd, cwd=cwd)

    @classmethod
    def commit(cls, message: str, cwd: str = None) -> ToolResult:
        """Create a commit."""
        # Add co-author line
        full_message = f"{message}\n\nCo-Authored-By: SAM <sam@local>"

        # Use heredoc for proper formatting
        cmd = f'''git commit -m "$(cat <<'EOF'
{full_message}
EOF
)"'''
        return BashTools.execute(cmd, cwd=cwd)

    @classmethod
    def branch(cls, name: str = None, create: bool = False, cwd: str = None) -> ToolResult:
        """List or create branches."""
        if name and create:
            cmd = f"git checkout -b {name}"
        elif name:
            cmd = f"git checkout {name}"
        else:
            cmd = "git branch -a"
        return BashTools.execute(cmd, cwd=cwd)


# =============================================================================
# PLANNING TOOLS
# =============================================================================

@dataclass
class Task:
    """A task in the todo list."""
    id: str
    subject: str
    description: str
    status: str = "pending"  # pending, in_progress, completed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)


class PlanningTools:
    """Planning and task tracking tools."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(__file__).parent / "tasks.json"
        self.tasks: Dict[str, Task] = self._load_tasks()

    def _load_tasks(self) -> Dict[str, Task]:
        """Load tasks from storage."""
        if self.storage_path.exists():
            try:
                data = json.load(open(self.storage_path))
                return {k: Task(**v) for k, v in data.items()}
            except:
                pass
        return {}

    def _save_tasks(self):
        """Save tasks to storage."""
        data = {k: {
            "id": v.id,
            "subject": v.subject,
            "description": v.description,
            "status": v.status,
            "created_at": v.created_at,
            "metadata": v.metadata,
        } for k, v in self.tasks.items()}
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_task(self, subject: str, description: str) -> ToolResult:
        """Create a new task."""
        task_id = hashlib.md5(f"{subject}{datetime.now()}".encode()).hexdigest()[:8]
        task = Task(
            id=task_id,
            subject=subject,
            description=description,
        )
        self.tasks[task_id] = task
        self._save_tasks()
        return ToolResult(True, f"Created task {task_id}: {subject}")

    def list_tasks(self, status: str = None) -> ToolResult:
        """List all tasks."""
        tasks = self.tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]

        output = []
        for t in tasks:
            status_icon = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
            output.append(f"{status_icon.get(t.status, '[ ]')} {t.id}: {t.subject}")

        return ToolResult(True, '\n'.join(output) or "No tasks")

    def update_task(self, task_id: str, status: str = None, subject: str = None) -> ToolResult:
        """Update a task."""
        if task_id not in self.tasks:
            return ToolResult(False, "", f"Task not found: {task_id}")

        task = self.tasks[task_id]
        if status:
            task.status = status
        if subject:
            task.subject = subject

        self._save_tasks()
        return ToolResult(True, f"Updated task {task_id}")

    def complete_task(self, task_id: str) -> ToolResult:
        """Mark a task as completed."""
        return self.update_task(task_id, status="completed")

    def decompose_task(self, task: str) -> ToolResult:
        """Decompose a complex task into subtasks."""
        # This would normally call the LLM, but we'll provide a template
        subtasks = [
            "1. Analyze requirements and understand the problem",
            "2. Explore the codebase for relevant files",
            "3. Design the solution approach",
            "4. Implement the changes",
            "5. Test the implementation",
            "6. Review and refine",
        ]
        return ToolResult(True, '\n'.join(subtasks))


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """
    Registry of all available tools.

    This mirrors Claude Code's tool system, allowing SAM to:
    1. List available tools
    2. Execute tools by name
    3. Parse tool calls from LLM output
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.planning = PlanningTools()
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all available tools."""

        # File tools
        self.register(Tool(
            name="Read",
            description="Read a file from the filesystem",
            category=ToolCategory.FILE,
            parameters={
                "file_path": {"type": "string", "required": True, "description": "Path to file"},
                "offset": {"type": "integer", "required": False, "description": "Starting line"},
                "limit": {"type": "integer", "required": False, "description": "Number of lines"},
            },
            handler=FileTools.read,
        ))

        self.register(Tool(
            name="Write",
            description="Write content to a file",
            category=ToolCategory.FILE,
            parameters={
                "file_path": {"type": "string", "required": True, "description": "Path to file"},
                "content": {"type": "string", "required": True, "description": "Content to write"},
            },
            handler=FileTools.write,
            safety_level="caution",
        ))

        self.register(Tool(
            name="Edit",
            description="Edit a file by replacing text",
            category=ToolCategory.FILE,
            parameters={
                "file_path": {"type": "string", "required": True, "description": "Path to file"},
                "old_string": {"type": "string", "required": True, "description": "Text to replace"},
                "new_string": {"type": "string", "required": True, "description": "Replacement text"},
                "replace_all": {"type": "boolean", "required": False, "description": "Replace all occurrences"},
            },
            handler=FileTools.edit,
            safety_level="caution",
        ))

        self.register(Tool(
            name="Glob",
            description="Find files matching a pattern",
            category=ToolCategory.SEARCH,
            parameters={
                "pattern": {"type": "string", "required": True, "description": "Glob pattern"},
                "path": {"type": "string", "required": False, "description": "Base path"},
            },
            handler=FileTools.glob,
        ))

        self.register(Tool(
            name="Grep",
            description="Search for text in files",
            category=ToolCategory.SEARCH,
            parameters={
                "pattern": {"type": "string", "required": True, "description": "Search pattern"},
                "path": {"type": "string", "required": False, "description": "Path to search"},
                "glob_filter": {"type": "string", "required": False, "description": "File pattern filter"},
                "case_insensitive": {"type": "boolean", "required": False, "description": "Case insensitive"},
            },
            handler=FileTools.grep,
        ))

        # Bash tools
        self.register(Tool(
            name="Bash",
            description="Execute a shell command",
            category=ToolCategory.BASH,
            parameters={
                "command": {"type": "string", "required": True, "description": "Command to execute"},
                "cwd": {"type": "string", "required": False, "description": "Working directory"},
                "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds"},
            },
            handler=BashTools.execute,
            safety_level="caution",
        ))

        # Git tools
        self.register(Tool(
            name="GitStatus",
            description="Get git repository status",
            category=ToolCategory.GIT,
            parameters={
                "cwd": {"type": "string", "required": False, "description": "Repository path"},
            },
            handler=GitTools.status,
        ))

        self.register(Tool(
            name="GitDiff",
            description="Show changes in the repository",
            category=ToolCategory.GIT,
            parameters={
                "staged": {"type": "boolean", "required": False, "description": "Show staged changes"},
                "cwd": {"type": "string", "required": False, "description": "Repository path"},
            },
            handler=GitTools.diff,
        ))

        self.register(Tool(
            name="GitLog",
            description="Show commit history",
            category=ToolCategory.GIT,
            parameters={
                "count": {"type": "integer", "required": False, "description": "Number of commits"},
                "cwd": {"type": "string", "required": False, "description": "Repository path"},
            },
            handler=GitTools.log,
        ))

        self.register(Tool(
            name="GitCommit",
            description="Create a git commit",
            category=ToolCategory.GIT,
            parameters={
                "message": {"type": "string", "required": True, "description": "Commit message"},
                "cwd": {"type": "string", "required": False, "description": "Repository path"},
            },
            handler=GitTools.commit,
            safety_level="caution",
        ))

        # Planning tools
        self.register(Tool(
            name="TaskCreate",
            description="Create a new task",
            category=ToolCategory.PLANNING,
            parameters={
                "subject": {"type": "string", "required": True, "description": "Task title"},
                "description": {"type": "string", "required": True, "description": "Task details"},
            },
            handler=self.planning.create_task,
        ))

        self.register(Tool(
            name="TaskList",
            description="List all tasks",
            category=ToolCategory.PLANNING,
            parameters={
                "status": {"type": "string", "required": False, "description": "Filter by status"},
            },
            handler=self.planning.list_tasks,
        ))

        self.register(Tool(
            name="TaskUpdate",
            description="Update a task",
            category=ToolCategory.PLANNING,
            parameters={
                "task_id": {"type": "string", "required": True, "description": "Task ID"},
                "status": {"type": "string", "required": False, "description": "New status"},
            },
            handler=self.planning.update_task,
        ))

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict]:
        """List all available tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "parameters": t.parameters,
                "safety": t.safety_level,
            }
            for t in self.tools.values()
        ]

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(False, "", f"Unknown tool: {tool_name}")

        try:
            return tool.handler(**kwargs)
        except TypeError as e:
            return ToolResult(False, "", f"Invalid parameters: {e}")
        except Exception as e:
            return ToolResult(False, "", f"Tool error: {e}")

    def parse_tool_call(self, text: str) -> Optional[Tuple[str, Dict]]:
        """
        Parse a tool call from LLM output.

        Supports formats:
        - TOOL: Read file_path=/path/to/file
        - <tool name="Read"><param name="file_path">/path</param></tool>
        - {"tool": "Read", "file_path": "/path"}
        """

        # Format 1: TOOL: Name param=value
        match = re.search(r'TOOL:\s*(\w+)\s*(.*?)(?:\n|$)', text)
        if match:
            tool_name = match.group(1)
            params_str = match.group(2)

            params = {}
            for param_match in re.finditer(r'(\w+)=(["\']?)(.+?)\2(?:\s|$)', params_str):
                params[param_match.group(1)] = param_match.group(3)

            return (tool_name, params)

        # Format 2: JSON
        try:
            # Find JSON in text
            json_match = re.search(r'\{[^{}]+\}', text)
            if json_match:
                data = json.loads(json_match.group())
                if "tool" in data:
                    tool_name = data.pop("tool")
                    return (tool_name, data)
        except:
            pass

        return None

    def generate_tool_prompt(self) -> str:
        """Generate a prompt describing available tools."""
        lines = ["Available tools:\n"]

        for tool in self.tools.values():
            params = ', '.join(
                f"{name}: {info['type']}" + ("" if info.get('required') else "?")
                for name, info in tool.parameters.items()
            )
            lines.append(f"- {tool.name}({params}): {tool.description}")

        lines.append("\nTo use a tool, output: TOOL: ToolName param1=value1 param2=value2")

        return '\n'.join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    import sys

    registry = ToolRegistry()

    if len(sys.argv) < 2:
        print("SAM Tool System")
        print("=" * 60)
        print()
        print("Available tools:")
        for tool in registry.list_tools():
            print(f"  {tool['name']}: {tool['description']}")
        print()
        print("Usage: tool_system.py <tool_name> [param=value ...]")
        return

    tool_name = sys.argv[1]

    # Parse parameters
    params = {}
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Try to parse as JSON for complex types
            try:
                value = json.loads(value)
            except:
                pass
            params[key] = value

    result = registry.execute(tool_name, **params)

    if result.success:
        print(result.output)
    else:
        print(f"Error: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
