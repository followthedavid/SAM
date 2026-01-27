#!/usr/bin/env python3
"""
SAM - Smart Assistant Manager
Fast routing + direct execution + MLX inference + Claude escalation learning

Usage:
  sam "list files in src"           → Executes locally (instant)
  sam "git status"                  → Executes locally (instant)
  sam "explain this code"           → MLX inference (local LLM)
  sam "implement login feature"     → Escalates to Claude + learns
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
BRAIN_PATH = Path(__file__).parent
BRIDGE_QUEUE = Path.home() / ".sam_chatgpt_queue.json"
ESCALATION_LOG = BRAIN_PATH / "data" / "escalations.jsonl"
ADAPTER_PATH = BRAIN_PATH / "models" / "chatgpt_trained" / "adapters"
MODEL_ID = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

# Ensure directories exist
ESCALATION_LOG.parent.mkdir(parents=True, exist_ok=True)

# MLX model (lazy loaded)
_mlx_model = None
_mlx_tokenizer = None
_mlx_generate = None

def get_mlx():
    """Lazy load MLX model."""
    global _mlx_model, _mlx_tokenizer, _mlx_generate
    if _mlx_model is None:
        try:
            from mlx_lm import load, generate
            if ADAPTER_PATH.exists():
                _mlx_model, _mlx_tokenizer = load(MODEL_ID, adapter_path=str(ADAPTER_PATH))
            else:
                _mlx_model, _mlx_tokenizer = load(MODEL_ID)
            _mlx_generate = generate
        except ImportError:
            return None, None, None
    return _mlx_model, _mlx_tokenizer, _mlx_generate


def mlx_respond(query: str, context: str = "") -> Optional[str]:
    """Get response from local MLX model."""
    model, tokenizer, generate = get_mlx()
    if model is None:
        return None

    system = "You are SAM, a helpful coding assistant. Be direct and concise."
    user_msg = query
    if context:
        user_msg = f"Context:\n{context[:1500]}\n\nQuestion: {query}"

    prompt = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n"

    response = generate(model, tokenizer, prompt=prompt, max_tokens=500, verbose=False)
    if "<|im_end|>" in response:
        response = response.split("<|im_end|>")[0]
    return response.strip()


def log_escalation(query: str, handler: str, response: str = None):
    """Log escalation for later training."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "handler": handler,
        "response": response,
        "learned": False
    }
    with open(ESCALATION_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def learn_from_claude_history():
    """Extract training data from recent Claude Code sessions."""
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        return 0

    training_data = []

    # Find recent history files
    for history_file in claude_dir.glob("**/history.jsonl"):
        try:
            with open(history_file) as f:
                messages = []
                for line in f:
                    if line.strip():
                        msg = json.loads(line)
                        messages.append(msg)

                # Pair user/assistant messages
                for i in range(0, len(messages) - 1, 2):
                    if i + 1 < len(messages):
                        user_msg = messages[i]
                        asst_msg = messages[i + 1]

                        user_text = user_msg.get("message", {}).get("content", "")
                        asst_text = asst_msg.get("message", {}).get("content", "")

                        if isinstance(user_text, list):
                            user_text = " ".join(t.get("text", "") for t in user_text if isinstance(t, dict))
                        if isinstance(asst_text, list):
                            asst_text = " ".join(t.get("text", "") for t in asst_text if isinstance(t, dict))

                        if user_text and asst_text and len(asst_text) > 50:
                            training_data.append({
                                "instruction": user_text[:1000],
                                "response": asst_text[:2000]
                            })
        except Exception as e:
            continue

    # Save new training data
    if training_data:
        output_path = BRAIN_PATH / "data" / "claude_learned.jsonl"
        with open(output_path, 'a') as f:
            for item in training_data[-100:]:  # Last 100 examples
                f.write(json.dumps(item) + '\n')

    return len(training_data)

# ============== ROUTING (regex, instant) ==============

LOCAL_PATTERNS = [
    (r'\b(list|ls|show|dir)\b.*\b(file|folder|dir)', 'list_dir'),
    (r'\b(read|cat|view|open)\b.*\b(file|\.py|\.js|\.rs|\.ts|\.json|\.md)', 'read_file'),
    (r'\bgit\s+(status|diff|log|branch)', 'git'),
    (r'\b(run|exec|execute)\b.*\b(test|build|lint|npm|cargo|python)', 'run'),
    (r'\b(search|find|grep)\b.*(for|code|file|pattern)', 'search'),
]

# MLX can handle these - use local LLM
MLX_PATTERNS = [
    (r'\b(explain|understand|how|what)\b.*\b(work|does|code|function)', 'explain'),
    (r'\b(what|how|why|when)\b.+\?', 'question'),
    (r'\b(write|create)\b.*\b(function|code|script)\b', 'code_gen'),
    (r'\b(help|assist)\b', 'help'),
]

# These need Claude escalation - SAM learns from the response
ESCALATION_PATTERNS = [
    (r'\b(implement|create|build|add)\b.*\b(feature|system|component)', 'implement'),
    (r'\b(debug|fix|solve)\b.*\b(error|bug|crash|fail|issue)', 'debug'),
    (r'\b(refactor|improve|optimize|redesign)', 'refactor'),
    (r'\b(architecture|design|plan)\b', 'design'),
    (r'\b(multi.?file|across|entire|all)\b', 'multi_file'),
]

def route(query: str) -> Tuple[str, str]:
    """Route query to handler. Returns (handler_type, handler)."""
    q = query.lower()

    # 1. Check for direct local commands (instant, no LLM)
    for pattern, handler in LOCAL_PATTERNS:
        if re.search(pattern, q):
            return ('local', handler)

    # 2. Check for MLX-handleable queries (local LLM)
    for pattern, handler in MLX_PATTERNS:
        if re.search(pattern, q):
            return ('mlx', handler)

    # 3. Check for escalation patterns (needs Claude, SAM learns)
    for pattern, handler in ESCALATION_PATTERNS:
        if re.search(pattern, q):
            return ('escalate', handler)

    # 4. Default: short queries → MLX, long/complex → escalate
    if len(query.split()) < 15:
        return ('mlx', 'general')

    return ('escalate', 'complex')

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
        print(f"[SAM] Local: {handler}", file=sys.stderr)
        return execute_local(query, handler, project_path)

    elif handler_type == 'mlx':
        print(f"[SAM] MLX: {handler}", file=sys.stderr)
        # Get context if file mentioned
        context = ""
        file_match = re.search(r'([^\s]+\.(py|js|rs|ts|json|md))', query)
        if file_match:
            filepath = Path(project_path) / file_match.group(1)
            if filepath.exists():
                context = filepath.read_text()[:2000]

        response = mlx_respond(query, context)
        if response:
            return response
        else:
            # Fallback to escalation if MLX fails
            print(f"[SAM] MLX unavailable, escalating", file=sys.stderr)
            handler_type = 'escalate'

    if handler_type == 'escalate':
        print(f"[SAM] Escalate to Claude: {handler}", file=sys.stderr)
        # Log this for learning later
        log_escalation(query, handler)

        # Get project context
        context = ""
        readme = Path(project_path) / "README.md"
        if readme.exists():
            context = readme.read_text()[:500]

        # Open Claude Code terminal with the query
        return f"""[SAM needs Claude for this - {handler}]

Run in Claude Code:
  {query}

SAM will learn from Claude's response automatically.
(Auto-learner daemon captures ~/.claude/ history)"""

def main():
    if len(sys.argv) < 2:
        print("""
SAM - Smart Assistant Manager
=============================

Usage:
  sam "list files"              → Local exec (instant)
  sam "read main.py"            → File content (instant)
  sam "git status"              → Git command (instant)
  sam "what does X do?"         → MLX inference (local LLM)
  sam "explain this code"       → MLX inference (local LLM)
  sam "implement feature"       → Escalate to Claude (learns)
  sam "debug this error"        → Escalate to Claude (learns)

Options:
  --project <path>              → Set project context
  --learn                       → Learn from Claude history NOW
  --status                      → Show SAM status
  --train                       → Trigger training with new data
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

        # Check MLX model
        model, _, _ = get_mlx()
        print(f"MLX Model: {'Loaded' if model else 'Not loaded'}")
        print(f"Adapter: {'Yes' if ADAPTER_PATH.exists() else 'No'}")

        # Check escalation log
        if ESCALATION_LOG.exists():
            with open(ESCALATION_LOG) as f:
                count = sum(1 for _ in f)
            print(f"Escalations logged: {count}")

        # Check training data
        training_file = BRAIN_PATH / "data" / "claude_learned.jsonl"
        if training_file.exists():
            with open(training_file) as f:
                count = sum(1 for _ in f)
            print(f"Training examples: {count}")

        # Auto-learner daemon
        result = subprocess.run(["launchctl", "list", "com.sam.autolearner"],
                               capture_output=True, text=True)
        print(f"Auto-learner: {'Running' if result.returncode == 0 else 'Stopped'}")
        return

    if "--learn" in args:
        print("Learning from Claude history...")
        count = learn_from_claude_history()
        print(f"Extracted {count} training examples")
        return

    if "--train" in args:
        print("Triggering training with new data...")
        # Run accelerated training
        subprocess.run(["python3", str(BRAIN_PATH / "accelerate.py"), "train"])
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
