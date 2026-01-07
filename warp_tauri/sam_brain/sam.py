#!/usr/bin/env python3
"""
SAM - Smart Assistant Manager
Fast routing + direct execution + browser bridge for complex tasks

Usage:
  sam "list files in src"           → Executes locally (instant)
  sam "git status"                  → Executes locally (instant)
  sam "implement login feature"     → Routes to ChatGPT/Claude (browser)
  sam --project ~/myapp "explain"   → With project context
"""

import os
import re
import sys
import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Configuration
BRIDGE_QUEUE = Path.home() / ".sam_chatgpt_queue.json"

# ============== ROUTING (regex, instant) ==============

LOCAL_PATTERNS = [
    (r'\b(list|ls|show|dir)\b.*\b(file|folder|dir)', 'list_dir'),
    (r'\b(read|cat|view|open)\b.*\b(file|\.py|\.js|\.rs|\.ts|\.json|\.md)', 'read_file'),
    (r'\bgit\s+(status|diff|log|branch)', 'git'),
    (r'\b(run|exec|execute)\b.*\b(test|build|lint|npm|cargo|python)', 'run'),
    (r'\b(search|find|grep)\b.*(for|code|file|pattern)', 'search'),
]

EXTERNAL_PATTERNS = [
    (r'\b(implement|create|build|write|add)\b.*\b(feature|function|class|component)', 'implement'),
    (r'\b(debug|fix|solve|why)\b.*\b(error|bug|crash|fail|issue)', 'debug'),
    (r'\b(explain|understand|how|what)\b.*\b(work|does|code|function)', 'explain'),
    (r'\b(refactor|improve|optimize|clean)', 'refactor'),
]

def route(query: str) -> Tuple[str, str]:
    """Route query to handler. Returns (handler, reason)."""
    q = query.lower()

    for pattern, handler in LOCAL_PATTERNS:
        if re.search(pattern, q):
            return ('local', handler)

    for pattern, handler in EXTERNAL_PATTERNS:
        if re.search(pattern, q):
            return ('external', handler)

    # Default: try local first for short queries
    if len(query.split()) < 10:
        return ('local', 'short_query')

    return ('external', 'complex')

# ============== LOCAL EXECUTION (no LLM) ==============

def execute_local(query: str, handler: str, project_path: str = ".") -> str:
    """Execute locally without LLM."""

    try:
        if handler == 'list_dir':
            # Extract path from query or use project path
            path = project_path
            match = re.search(r'(?:in|at|from)\s+([^\s]+)', query)
            if match:
                path = os.path.expanduser(match.group(1))

            entries = sorted(Path(path).iterdir(), key=lambda x: (x.is_file(), x.name))
            result = []
            for e in entries[:50]:
                prefix = "📁 " if e.is_dir() else "📄 "
                result.append(f"{prefix}{e.name}")
            return '\n'.join(result) or "Empty directory"

        elif handler == 'read_file':
            # Extract filename from query
            match = re.search(r'([^\s]+\.(py|js|rs|ts|json|md|txt|yaml|yml|toml))', query)
            if match:
                filepath = match.group(1)
                # Try relative to project, then absolute
                for base in [project_path, '.', os.path.expanduser('~')]:
                    full = Path(base) / filepath
                    if full.exists():
                        content = full.read_text()
                        if len(content) > 3000:
                            return f"# {filepath} (truncated)\n{content[:3000]}\n...[truncated]..."
                        return f"# {filepath}\n{content}"
            return "Could not find file. Try: sam read <filename>"

        elif handler == 'git':
            cmd = re.search(r'git\s+(\w+)', query.lower())
            git_cmd = cmd.group(1) if cmd else 'status'

            if git_cmd in ['status', 'diff', 'log', 'branch']:
                result = subprocess.run(
                    f"git {git_cmd}" + (" --oneline -10" if git_cmd == 'log' else ""),
                    shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout or result.stderr or f"git {git_cmd}: no output"
            return f"Unsupported git command: {git_cmd}"

        elif handler == 'run':
            # Extract command
            match = re.search(r'(?:run|exec)\s+(.+)', query, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                # Safety check
                if any(d in cmd for d in ['rm -rf', 'sudo', '> /dev/', 'dd if=']):
                    return f"BLOCKED: Potentially dangerous command: {cmd}"

                result = subprocess.run(
                    cmd, shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=60
                )
                output = result.stdout + result.stderr
                return output[:2000] if output else "Command completed (no output)"
            return "Usage: sam run <command>"

        elif handler == 'search':
            match = re.search(r'(?:search|find|grep)\s+(?:for\s+)?["\']?([^"\']+)["\']?', query)
            if match:
                pattern = match.group(1).strip()
                result = subprocess.run(
                    f"grep -rn '{pattern}' --include='*.py' --include='*.js' --include='*.rs' --include='*.ts' . | head -20",
                    shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=30
                )
                return result.stdout or "No matches found"
            return "Usage: sam search <pattern>"

        elif handler == 'short_query':
            # Try to interpret as a command
            if query.strip().startswith(('ls', 'cat', 'git', 'npm', 'cargo', 'python')):
                result = subprocess.run(
                    query.strip(), shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=30
                )
                return result.stdout or result.stderr or "No output"
            return f"I can help with: list files, read file, git status, run command, search code\nFor complex tasks, I'll route to ChatGPT/Claude."

        return f"Handler '{handler}' not implemented for local execution"

    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"

# ============== EXTERNAL ROUTING (browser bridge) ==============

def sanitize(text: str) -> str:
    """Remove secrets before sending externally."""
    patterns = [
        (r'(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*["\']?[\w\-\.]+["\']?', '[REDACTED]'),
        (r'sk-[a-zA-Z0-9]{20,}', '[KEY]'),
        (r'ghp_[a-zA-Z0-9]{36}', '[TOKEN]'),
        (r'/Users/\w+/', '/Users/USER/'),
    ]
    result = text
    for pattern, repl in patterns:
        result = re.sub(pattern, repl, result)
    return result

def queue_external(query: str, context: str = "", provider: str = "chatgpt") -> str:
    """Queue request for browser bridge."""
    queue = []
    if BRIDGE_QUEUE.exists():
        try:
            queue = json.load(open(BRIDGE_QUEUE))
        except:
            queue = []

    # Build clean prompt
    prompt_parts = [sanitize(query)]
    if context:
        prompt_parts.append(f"\nContext:\n{sanitize(context)[:1000]}")

    request_id = str(uuid.uuid4())[:8]
    queue.append({
        "id": request_id,
        "prompt": '\n'.join(prompt_parts),
        "provider": provider,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    })

    json.dump(queue, open(BRIDGE_QUEUE, 'w'), indent=2)

    return f"""📤 Queued to {provider.upper()}

Request ID: {request_id}
Open {provider} in your browser - the bridge will send it automatically.

Check status: sam --check {request_id}"""

# ============== MAIN ==============

def sam(query: str, project_path: str = ".") -> str:
    """Main SAM function."""
    handler_type, handler = route(query)

    if handler_type == 'local':
        print(f"[SAM] Local: {handler}")
        return execute_local(query, handler, project_path)
    else:
        print(f"[SAM] External: {handler}")
        # Get project context
        context = ""
        readme = Path(project_path) / "README.md"
        if readme.exists():
            context = readme.read_text()[:500]
        return queue_external(query, context)

def main():
    if len(sys.argv) < 2:
        print("""
SAM - Smart Assistant Manager
=============================

Usage:
  sam "list files"              → Shows files (local, instant)
  sam "read main.py"            → Shows file content (local)
  sam "git status"              → Git status (local)
  sam "run npm test"            → Runs command (local)
  sam "search TODO"             → Searches code (local)
  sam "implement login"         → Routes to ChatGPT (browser)
  sam "debug api error"         → Routes to ChatGPT (browser)

Options:
  --project <path>              → Set project context
  --check <id>                  → Check bridge response
  --status                      → Show SAM status
""")
        return

    args = sys.argv[1:]
    project_path = "."

    if "--project" in args:
        idx = args.index("--project")
        project_path = os.path.expanduser(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    if "--status" in args:
        print("SAM Status")
        print("=" * 40)
        # Check bridge queue
        if BRIDGE_QUEUE.exists():
            queue = json.load(open(BRIDGE_QUEUE))
            pending = [q for q in queue if q.get('status') == 'pending']
            print(f"Pending requests: {len(pending)}")
        else:
            print("Bridge queue: empty")
        return

    if "--check" in args:
        idx = args.index("--check")
        req_id = args[idx + 1]
        resp_file = Path.home() / ".sam_bridge_responses" / f"{req_id}.json"
        if resp_file.exists():
            data = json.load(open(resp_file))
            print(f"Response:\n{data.get('response', 'No response')}")
        else:
            print(f"No response yet for {req_id}")
        return

    query = " ".join(args)
    result = sam(query, project_path)
    print(result)

if __name__ == "__main__":
    main()
