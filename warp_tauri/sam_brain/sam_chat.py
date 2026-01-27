#!/usr/bin/env python3
"""
SAM Chat Interface
- Uses fine-tuned MLX model (SAM Brain) for local inference
- Auto-escalates to Claude via browser bridge when needed
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

# Import the escalation handler (uses MLX model + Claude bridge)
sys.path.insert(0, str(Path(__file__).parent))
from escalation_handler import process_request, EscalationReason
from smart_router import Provider, sanitize_content

# Configuration
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


def query_sam_brain(prompt: str, context: str = "", auto_escalate: bool = True):
    """Query SAM Brain (fine-tuned MLX model) with auto-escalation to Claude."""
    try:
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nRequest:\n{prompt}"

        result = process_request(full_prompt, auto_escalate=auto_escalate)

        return {
            "content": result.content,
            "provider": result.provider,
            "confidence": result.confidence,
            "escalation_reason": result.escalation_reason.value
        }

    except Exception as e:
        print(f"[SAM] Brain error: {e}")
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


def chat(prompt: str, project_context: str = "", force_claude: bool = False) -> str:
    """
    Main chat function.
    Uses SAM Brain (MLX) first, auto-escalates to Claude when needed.
    """
    print(f"[SAM] Processing: {prompt[:50]}...")

    # Query SAM Brain with auto-escalation
    result = query_sam_brain(prompt, project_context, auto_escalate=not force_claude)

    if result is None:
        return "[SAM] Error: Could not process request"

    # Show provider info
    provider_icon = "🧠" if result["provider"] == "sam" else "☁️"
    confidence_str = f"{result['confidence']:.0%}" if result["provider"] == "sam" else "N/A"

    header = f"{provider_icon} [{result['provider'].upper()}]"
    if result["escalation_reason"] != "none":
        header += f" (escalated: {result['escalation_reason']})"
    if result["provider"] == "sam":
        header += f" [confidence: {confidence_str}]"

    response = result["content"]

    # Check if response contains a tool call
    tool_call = parse_tool_call(response)
    if tool_call:
        tool_result = execute_tool(tool_call.get("tool"), tool_call.get("args", {}))
        # Feed result back to model for final response
        followup = query_sam_brain(
            f"Tool result:\n{tool_result}\n\nNow provide your response to the user.",
            project_context,
            auto_escalate=False
        )
        if followup:
            return f"{header}\n\n{followup['content']}"
        return f"{header}\n\n{tool_result}"

    return f"{header}\n\n{response}"


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("""
SAM Chat Interface (MLX + Auto-Escalation)
==========================================

Usage:
  sam_chat.py "<your message>"              - Chat with SAM (auto-escalates to Claude if needed)
  sam_chat.py --claude "<message>"          - Force Claude (via browser bridge)
  sam_chat.py --project <path> "<message>"  - Chat with project context
  sam_chat.py --status                      - Show status

SAM uses the fine-tuned MLX model locally and automatically escalates
to Claude via browser bridge when confidence is low or task is complex.

Examples:
  sam_chat.py "list files in the SAM project"
  sam_chat.py "implement a login function"
  sam_chat.py --claude "design a microservices architecture"
  sam_chat.py --project ~/Projects/myapp "explain the main.py file"
""")
        return

    # Parse arguments
    args = sys.argv[1:]
    project_path = None
    force_claude = False

    if "--project" in args:
        idx = args.index("--project")
        project_path = args[idx + 1]
        args = args[:idx] + args[idx+2:]

    if "--claude" in args:
        idx = args.index("--claude")
        force_claude = True
        args = args[:idx] + args[idx+1:]

    if "--status" in args:
        print("SAM Status")
        print("=" * 40)
        # Check MLX model
        try:
            from mlx_inference import ADAPTER_PATH, BASE_MODEL
            if ADAPTER_PATH.exists():
                print(f"SAM Brain: Ready (adapters at {ADAPTER_PATH})")
            else:
                print(f"SAM Brain: Using base model ({BASE_MODEL})")
        except Exception as e:
            print(f"SAM Brain: Error - {e}")

        # Check bridge profile
        bridge_profile = Path.home() / ".sam-ai-bridge-profile"
        if bridge_profile.exists():
            print("Claude Bridge: Profile exists (may need login refresh)")
        else:
            print("Claude Bridge: Not configured (run: node ai_bridge.cjs login claude)")

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
    response = chat(prompt, context, force_claude=force_claude)
    print(f"\n{response}")


if __name__ == "__main__":
    main()
