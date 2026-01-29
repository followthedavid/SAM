#!/usr/bin/env python3
"""
SAM Agent - Local AI coding assistant
Uses qwen2.5-coder:1.5b with tool access for real coding tasks.

Usage:
  sam-agent "add a function to utils.py that validates email addresses"
  sam-agent --project ~/myapp "fix the bug in main.py"
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:1.5b"

# System prompt that teaches tool use
SYSTEM_PROMPT = """You are SAM. Execute exactly ONE tool per response. Wait for the result before continuing.

TOOLS:
TOOL: LIST .          (list directory)
TOOL: READ file.py    (read file)
TOOL: WRITE file.py   (write file - content on next lines, end with END_WRITE)
TOOL: RUN command     (run shell command)
TOOL: SEARCH pattern  (search in code)

EXAMPLE SESSION:
User: create hello.py that prints hi
SAM: TOOL: WRITE hello.py
print("hi")
END_WRITE

[Result: Wrote 11 bytes to hello.py]

SAM: TOOL: RUN python3 hello.py

[Result: hi]

SAM: Done! Created hello.py that prints hi.

RULES:
- ONE tool per response, then STOP and wait
- No markdown code fences in WRITE content
- Say "Done!" when task is complete"""


def query_model(prompt: str, context: str = "") -> str:
    """Query the local model."""
    import urllib.request

    full_prompt = SYSTEM_PROMPT
    if context:
        full_prompt += f"\n\nPREVIOUS:\n{context}\n"
    full_prompt += f"\n\nUSER: {prompt}\n\nSAM:"

    data = json.dumps({
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "keep_alive": "24h",
        "options": {
            "num_predict": 300,  # Shorter to reduce hallucination
            "temperature": 0.1,
            "stop": ["USER:", "\n\nUSER", "[Result:", "SAM:"]  # Stop before hallucinating
        }
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            response = result.get("response", "").strip()
            # Stop at first [Result which indicates hallucination
            if "[Result" in response:
                response = response.split("[Result")[0].strip()
            return response
    except Exception as e:
        return f"[Error: {e}]"


def parse_tool_call(response: str) -> Optional[Tuple[str, str]]:
    """Parse a tool call from response."""
    # Only look at first 300 chars to avoid matching hallucinated results
    first_part = response[:300]

    # Try "TOOL: X arg" format first
    patterns = [
        (r'TOOL:\s*READ\s+(\S+)', 'read'),
        (r'TOOL:\s*LIST\s+(\S+)', 'list'),
        (r'TOOL:\s*RUN\s+(.+?)(?:\n|$)', 'run'),
        (r'TOOL:\s*SEARCH\s+(.+?)(?:\n|$)', 'search'),
        (r'TOOL:\s*WRITE\s+(\S+)', 'write'),
        # Fallback: plain format
        (r'^READ\s+(\S+)', 'read'),
        (r'^LIST\s+(\S+)', 'list'),
        (r'^RUN\s+(.+?)(?:\n|$)', 'run'),
        (r'^SEARCH\s+(.+?)(?:\n|$)', 'search'),
        (r'^WRITE\s+(\S+)', 'write'),
    ]

    for pattern, tool in patterns:
        match = re.search(pattern, first_part, re.IGNORECASE | re.MULTILINE)
        if match:
            return (tool, match.group(1).strip())
    return None


def execute_tool(tool: str, arg: str, response: str = "", cwd: str = ".") -> str:
    """Execute a tool and return result."""
    try:
        if tool == 'read':
            path = Path(cwd) / arg if not arg.startswith('/') else Path(arg)
            if path.exists():
                content = path.read_text()
                if len(content) > 2000:
                    return f"[{arg} - showing first 2000 chars]\n{content[:2000]}\n[...truncated...]"
                return f"[{arg}]\n{content}"
            return f"[Error: File not found: {arg}]"

        elif tool == 'list':
            path = Path(cwd) / arg if not arg.startswith('/') else Path(arg)
            if path.exists():
                entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
                return '\n'.join(str(e.name) + ('/' if e.is_dir() else '') for e in entries[:30])
            return f"[Error: Directory not found: {arg}]"

        elif tool == 'run':
            # Safety check - block dangerous commands
            dangerous = ['rm -rf /', 'sudo rm', '> /dev/', 'dd if=', 'mkfs', ':(){',
                         'curl|', 'wget|', '|bash', '|sh', '$(', '`']
            if any(d in arg for d in dangerous):
                return f"[BLOCKED: Dangerous command]"

            # Fix common command issues
            cmd = arg
            if cmd.startswith('python ') and not cmd.startswith('python3'):
                cmd = 'python3' + cmd[6:]  # Replace 'python ' with 'python3'

            import shlex
            try:
                cmd_parts = shlex.split(cmd)
            except ValueError as e:
                return f"[Error: Invalid command syntax: {e}]"

            result = subprocess.run(
                cmd_parts, shell=False, cwd=cwd,
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            return output[:1500] if output else "[Command completed - no output]"

        elif tool == 'search':
            import shlex
            safe_pattern = arg  # grep pattern (not shell-interpreted)
            result = subprocess.run(
                ['grep', '-rn', safe_pattern,
                 '--include=*.py', '--include=*.js', '--include=*.ts', '--include=*.rs',
                 '.'],
                shell=False, cwd=cwd,
                capture_output=True, text=True, timeout=30
            )
            # Limit output to first 20 lines
            lines = result.stdout.split('\n')[:20]
            output = '\n'.join(lines)
            return output or "[No matches]"

        elif tool == 'write':
            # Extract content between WRITE and END_WRITE (handles TOOL: prefix too)
            match = re.search(r'(?:TOOL:\s*)?WRITE\s+\S+\s*\n(.*?)(?:END_WRITE|$)', response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Strip markdown code fences if present
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
                content = content.strip()
                if not content:
                    return "[Error: No content found for WRITE]"
                path = Path(cwd) / arg if not arg.startswith('/') else Path(arg)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                return f"[Wrote {len(content)} bytes to {arg}]"
            return "[Error: No content found for WRITE]"

        return f"[Unknown tool: {tool}]"

    except subprocess.TimeoutExpired:
        return "[Command timed out]"
    except Exception as e:
        return f"[Error: {e}]"


def run_agent(task: str, project_path: str = ".", max_iterations: int = 10, auto: bool = False) -> None:
    """Run the agent on a task."""
    print(f"\n{'='*60}")
    print(f"SAM Agent {'(auto mode)' if auto else ''}")
    print(f"Task: {task}")
    print(f"Project: {project_path}")
    print(f"{'='*60}\n")

    context = ""
    no_tool_count = 0
    last_tool_call = None
    repeat_count = 0

    for i in range(max_iterations):
        print(f"[Step {i+1}]")

        # Query model
        next_prompt = task if i == 0 else "Task: " + task + "\nWhat tool should I use next? Or say Done! if complete."
        response = query_model(next_prompt, context)
        print(f"SAM: {response}\n")

        # Check for tool call
        tool_call = parse_tool_call(response)

        if tool_call:
            tool, arg = tool_call

            # Check for repetition
            current_call = f"{tool}:{arg}"
            if current_call == last_tool_call:
                repeat_count += 1
                if repeat_count >= 2:
                    print("[Auto: Detected repetition, task likely complete]")
                    break
            else:
                repeat_count = 0
                last_tool_call = current_call

            print(f"[Executing: {tool} {arg}]")
            result = execute_tool(tool, arg, response, project_path)
            print(f"{result}\n")

            # Add to context for next iteration
            context += f"\n[{tool} {arg}]\n{result}\n"
            no_tool_count = 0

            # Limit context size
            if len(context) > 4000:
                context = context[-3000:]
        else:
            no_tool_count += 1
            # No tool call - check if done
            if any(word in response.lower() for word in ['done', 'complete', 'finished', 'that should']):
                print("[Task appears complete]")
                break

            # In auto mode, stop after 2 consecutive no-tool responses
            if auto:
                if no_tool_count >= 2:
                    print("[Auto: No more tool calls, stopping]")
                    break
                continue

            # Ask if should continue
            cont = input("\nContinue? (y/n/instruction): ").strip()
            if cont.lower() == 'n':
                break
            elif cont.lower() != 'y' and cont:
                task = cont
                context = ""

    print(f"\n{'='*60}")
    print("Session ended")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("""
SAM Agent - Local AI Coding Assistant
=====================================

Usage:
  sam-agent "<task>"                    Run a task (interactive)
  sam-agent --auto "<task>"             Run in auto mode (no prompts)
  sam-agent --project <path> "<task>"   Run with project context

Examples:
  sam-agent "create a hello.py that prints Hello World"
  sam-agent --auto "read main.py and explain what it does"
  sam-agent --project ~/myapp "add input validation to the login function"

The agent will:
1. Understand your request
2. Read relevant files
3. Make changes
4. Test if needed
""")
        return

    args = sys.argv[1:]
    project_path = "."
    auto_mode = False

    if "--project" in args:
        idx = args.index("--project")
        project_path = os.path.expanduser(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    if "--auto" in args:
        args.remove("--auto")
        auto_mode = True

    task = " ".join(args)

    # Warm up model first
    print("Warming up model...")
    query_model("ready")

    run_agent(task, project_path, auto=auto_mode)


if __name__ == "__main__":
    main()
