#!/usr/bin/env python3
"""
SAM Chat Interface
- Routes requests intelligently (local first, browser bridge for complex)
- Sanitizes before external routing
- Executes tools (read/write/run)
- Maintains conversation context
"""

import os
import sys
import json
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Import the router
sys.path.insert(0, str(Path(__file__).parent))
from smart_router import route_request, Provider, sanitize_content, format_external_prompt

# Configuration
OLLAMA_URL = "http://localhost:11434"
LOCAL_MODEL = "dolphin-llama3:8b"  # Best local model available
FALLBACK_MODEL = "qwen2.5-coder:3b"  # Fallback if 8b not loaded
BRIDGE_QUEUE = Path.home() / ".sam_chatgpt_queue.json"
CONVERSATION_LOG = Path("/Volumes/Plex/SSOT/sam_conversations.json")

# Tool definitions that SAM can execute
TOOLS = {
    "read_file": "Read contents of a file",
    "write_file": "Write content to a file",
    "list_dir": "List directory contents",
    "run_command": "Execute a shell command",
    "git_status": "Get git status of a project",
    "search_code": "Search for patterns in code",
}


def query_local(prompt: str, context: str = "", model: str = LOCAL_MODEL) -> Optional[str]:
    """Query local Ollama model."""
    try:
        system = """You are SAM, a local AI assistant. You help with coding projects.
You can execute tools by responding with JSON like: {"tool": "read_file", "args": {"path": "/path/to/file"}}
For direct answers, just respond normally.
Be concise and actionable."""

        messages = [
            {"role": "system", "content": system},
        ]

        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
            messages.append({"role": "assistant", "content": "I understand the context. What would you like me to do?"})

        messages.append({"role": "user", "content": prompt})

        data = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1000,
            }
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            return result.get("message", {}).get("content", "")

    except Exception as e:
        print(f"[SAM] Local model error: {e}")
        return None


def queue_browser_request(prompt: str, provider: str = "chatgpt") -> str:
    """Queue a request for browser bridge (ChatGPT/Claude)."""
    import uuid

    queue = []
    if BRIDGE_QUEUE.exists():
        try:
            with open(BRIDGE_QUEUE) as f:
                queue = json.load(f)
        except:
            queue = []

    request_id = str(uuid.uuid4())
    queue.append({
        "id": request_id,
        "prompt": prompt,
        "provider": provider,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    })

    with open(BRIDGE_QUEUE, "w") as f:
        json.dump(queue, f, indent=2)

    return request_id


def check_bridge_response(request_id: str) -> Optional[str]:
    """Check if browser bridge has a response."""
    response_file = Path.home() / ".sam_bridge_responses" / f"{request_id}.json"
    if response_file.exists():
        with open(response_file) as f:
            data = json.load(f)
        return data.get("response")
    return None


def execute_tool(tool: str, args: Dict) -> str:
    """Execute a tool and return result."""
    try:
        if tool == "read_file":
            path = args.get("path", "")
            if Path(path).exists():
                return Path(path).read_text()[:5000]  # Limit size
            return f"File not found: {path}"

        elif tool == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            Path(path).write_text(content)
            return f"Wrote {len(content)} bytes to {path}"

        elif tool == "list_dir":
            path = args.get("path", ".")
            entries = list(Path(path).iterdir())
            return "\n".join(str(e) for e in entries[:50])

        elif tool == "run_command":
            cmd = args.get("command", "")
            # Safety check
            dangerous = ["rm -rf", "sudo rm", "dd if=", "> /dev/"]
            if any(d in cmd for d in dangerous):
                return f"BLOCKED: Dangerous command detected: {cmd}"

            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout + result.stderr

        elif tool == "git_status":
            path = args.get("path", ".")
            result = subprocess.run(
                "git status --short", shell=True, cwd=path,
                capture_output=True, text=True, timeout=10
            )
            return result.stdout or "Clean working directory"

        elif tool == "search_code":
            pattern = args.get("pattern", "")
            path = args.get("path", ".")
            result = subprocess.run(
                f"grep -r '{pattern}' {path} --include='*.py' --include='*.rs' --include='*.ts' -l",
                shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout or "No matches found"

        else:
            return f"Unknown tool: {tool}"

    except Exception as e:
        return f"Tool error: {e}"


def parse_tool_call(response: str) -> Optional[Dict]:
    """Parse a tool call from response."""
    try:
        # Look for JSON in response
        import re
        match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None


def chat(prompt: str, project_context: str = "") -> str:
    """
    Main chat function.
    Routes intelligently, executes tools, returns response.
    """
    print(f"[SAM] Processing: {prompt[:50]}...")

    # Get routing decision
    decision = route_request(prompt, project_context)
    print(f"[SAM] Route: {decision.provider.value} ({decision.reason})")

    if decision.provider == Provider.LOCAL:
        # Try local model
        response = query_local(prompt, project_context)

        if response:
            # Check if response contains a tool call
            tool_call = parse_tool_call(response)
            if tool_call:
                tool_result = execute_tool(tool_call.get("tool"), tool_call.get("args", {}))
                # Feed result back to model
                followup = query_local(
                    f"Tool result:\n{tool_result}\n\nNow provide your response to the user.",
                    project_context
                )
                return followup or tool_result
            return response

        # Local failed, escalate to browser bridge
        print("[SAM] Local model failed, escalating to browser bridge...")
        decision.provider = Provider.CHATGPT

    # External routing (browser bridge)
    if decision.provider in [Provider.CHATGPT, Provider.CLAUDE]:
        provider = "chatgpt" if decision.provider == Provider.CHATGPT else "claude"

        # Sanitize before sending
        clean_prompt = format_external_prompt(decision, "SAM Project")

        print(f"[SAM] Queuing to {provider} browser bridge...")
        request_id = queue_browser_request(clean_prompt, provider)

        return f"""[Queued to {provider.upper()}]
Request ID: {request_id}

Your request has been sanitized and queued for {provider}.
Open {provider} in your browser - the bridge will send it automatically.

To check for response: sam chat --check {request_id}"""

    return "Unable to process request."


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("""
SAM Chat Interface
==================

Usage:
  sam_chat.py "<your message>"              - Chat with SAM
  sam_chat.py --project <path> "<message>"  - Chat with project context
  sam_chat.py --check <request_id>          - Check browser bridge response
  sam_chat.py --status                      - Show status

Examples:
  sam_chat.py "list files in the SAM project"
  sam_chat.py "implement a login function"
  sam_chat.py --project ~/Projects/myapp "explain the main.py file"
""")
        return

    # Parse arguments
    args = sys.argv[1:]
    project_path = None
    check_id = None

    if "--project" in args:
        idx = args.index("--project")
        project_path = args[idx + 1]
        args = args[:idx] + args[idx+2:]

    if "--check" in args:
        idx = args.index("--check")
        check_id = args[idx + 1]
        response = check_bridge_response(check_id)
        if response:
            print(f"Response from bridge:\n{response}")
        else:
            print(f"No response yet for {check_id}")
        return

    if "--status" in args:
        # Check Ollama
        try:
            resp = urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5)
            models = json.loads(resp.read())
            print(f"Ollama: Online ({len(models.get('models', []))} models)")
        except:
            print("Ollama: Offline")

        # Check bridge queue
        if BRIDGE_QUEUE.exists():
            with open(BRIDGE_QUEUE) as f:
                queue = json.load(f)
            pending = [q for q in queue if q.get("status") == "pending"]
            print(f"Bridge queue: {len(pending)} pending")
        else:
            print("Bridge queue: Empty")
        return

    # Get project context if specified
    context = ""
    if project_path:
        readme = Path(project_path) / "README.md"
        if readme.exists():
            context = f"Project README:\n{readme.read_text()[:2000]}"

    # Chat
    prompt = " ".join(args)
    response = chat(prompt, context)
    print(f"\n{response}")


if __name__ == "__main__":
    main()
