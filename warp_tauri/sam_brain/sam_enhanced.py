#!/usr/bin/env python3
"""
SAM Enhanced - Project-aware AI coding assistant with full brain integration

Features:
- Project auto-detection from keywords
- Semantic memory with vector embeddings
- Multi-agent orchestration for complex tasks
- SSOT sync for external knowledge
- Project favorites with starred/pinned
- Voice output support (RVC)
- Smart escalation to browser bridges
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, List

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECTS_FILE = SCRIPT_DIR / "projects.json"
MEMORY_FILE = Path.home() / ".sam_memory.json"
BRIDGE_QUEUE = Path.home() / ".sam_chatgpt_queue.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:1.5b"

# Import brain modules (lazy load to avoid startup delay)
_semantic_memory = None
_multi_agent = None
_ssot_sync = None
_favorites = None
_voice = None

def get_semantic_memory():
    global _semantic_memory
    if _semantic_memory is None:
        try:
            from semantic_memory import get_memory
            _semantic_memory = get_memory()
        except ImportError:
            _semantic_memory = False
    return _semantic_memory if _semantic_memory else None

def get_multi_agent():
    global _multi_agent
    if _multi_agent is None:
        try:
            from multi_agent import get_orchestrator
            _multi_agent = get_orchestrator()
        except ImportError:
            _multi_agent = False
    return _multi_agent if _multi_agent else None

def get_ssot():
    global _ssot_sync
    if _ssot_sync is None:
        try:
            from ssot_sync import get_sync
            _ssot_sync = get_sync()
        except ImportError:
            _ssot_sync = False
    return _ssot_sync if _ssot_sync else None

def get_favorites():
    global _favorites
    if _favorites is None:
        try:
            from project_favorites import FavoritesManager
            _favorites = FavoritesManager()
        except ImportError:
            _favorites = False
    return _favorites if _favorites else None

def get_voice():
    global _voice
    if _voice is None:
        try:
            from voice_bridge import get_bridge
            _voice = get_bridge()
        except ImportError:
            _voice = False
    return _voice if _voice else None

# ============== PROJECT MANAGEMENT ==============

def load_projects() -> Dict:
    """Load project registry."""
    if PROJECTS_FILE.exists():
        return json.load(open(PROJECTS_FILE))
    return {"projects": [], "default_project": "."}

def find_project(query: str) -> Optional[Dict]:
    """Find matching project from query keywords, with favorites boost."""
    data = load_projects()
    query_lower = query.lower()

    # Get favorites for boost
    favorites_mgr = get_favorites()
    starred_paths = set()
    pinned_paths = set()
    if favorites_mgr:
        starred_paths = {f.path for f in favorites_mgr.get_starred()}
        pinned_paths = {f.path for f in favorites_mgr.get_pinned()}

    best_match = None
    best_score = 0

    for project in data["projects"]:
        score = 0
        # Check project name
        if project["name"].lower() in query_lower:
            score += 10
        # Check keywords
        for kw in project.get("keywords", []):
            if kw.lower() in query_lower:
                score += 3
        # Check description words
        for word in project.get("description", "").lower().split():
            if len(word) > 3 and word in query_lower:
                score += 1

        # Favorites boost
        if project["path"] in pinned_paths:
            score += 5  # Pinned projects get strong boost
        elif project["path"] in starred_paths:
            score += 2  # Starred projects get small boost

        if score > best_score:
            best_score = score
            best_match = project

    # Record access if found
    if best_match and favorites_mgr:
        favorites_mgr.access(best_match["path"])

    return best_match if best_score >= 3 else None

def get_project_context(project: Dict, max_chars: int = 1500) -> str:
    """Get relevant context from a project."""
    path = Path(project["path"])
    context_parts = []

    # Try README
    for readme in ["README.md", "README.txt", "README"]:
        readme_path = path / readme
        if readme_path.exists():
            content = readme_path.read_text()[:500]
            context_parts.append(f"README:\n{content}")
            break

    # List key files
    if path.exists():
        files = []
        for f in path.iterdir():
            if f.is_file() and f.suffix in ['.py', '.rs', '.ts', '.js', '.json', '.toml']:
                files.append(f.name)
        if files:
            context_parts.append(f"Key files: {', '.join(files[:15])}")

    return '\n'.join(context_parts)[:max_chars]

# ============== MEMORY ==============

def load_memory() -> Dict:
    """Load persistent memory."""
    if MEMORY_FILE.exists():
        try:
            return json.load(open(MEMORY_FILE))
        except:
            pass
    return {
        "interactions": [],
        "preferences": {},
        "learned_patterns": []
    }

def save_memory(memory: Dict):
    """Save memory to disk."""
    # Keep only last 100 interactions
    if len(memory.get("interactions", [])) > 100:
        memory["interactions"] = memory["interactions"][-100:]
    json.dump(memory, open(MEMORY_FILE, 'w'), indent=2)

def remember(query: str, result: str, project: str = None):
    """Remember an interaction - uses semantic memory if available."""
    # Store in semantic memory
    sem_mem = get_semantic_memory()
    if sem_mem:
        sem_mem.add(
            content=f"Q: {query}\nA: {result[:500]}",
            entry_type="interaction",
            metadata={"project": project, "query": query[:200]}
        )

    # Also store in basic memory for fallback
    memory = load_memory()
    memory["interactions"].append({
        "timestamp": datetime.now().isoformat(),
        "query": query[:200],
        "result_preview": result[:100],
        "project": project
    })
    save_memory(memory)

def get_relevant_memories(query: str, limit: int = 3) -> List[str]:
    """Get memories relevant to current query - semantic search if available."""
    # Try semantic memory first
    sem_mem = get_semantic_memory()
    if sem_mem:
        results = sem_mem.search(query, limit=limit)
        if results:
            return [f"[{r[1]:.2f}] {r[0].content[:150]}" for r in results]

    # Fallback to basic memory
    memory = load_memory()
    query_words = set(query.lower().split())

    scored = []
    for interaction in memory.get("interactions", []):
        past_words = set(interaction.get("query", "").lower().split())
        overlap = len(query_words & past_words)
        if overlap >= 2:
            scored.append((overlap, interaction))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [f"Past: {s[1]['query']} → {s[1]['result_preview']}" for s in scored[:limit]]

# ============== ROUTING ==============

LOCAL_PATTERNS = [
    (r'\b(list|ls|show|dir)\b.*\b(file|folder|dir)', 'list_dir'),
    (r'\b(read|cat|view|open)\b.*\.(py|js|rs|ts|json|md|txt)', 'read_file'),
    (r'\bgit\s+(status|diff|log|branch)', 'git'),
    (r'\b(run|exec)\b', 'run'),
    (r'\b(search|find|grep)\b.*(for|code|pattern)', 'search'),
]

AGENT_PATTERNS = [
    (r'\b(create|write|add|make)\b.*\.(py|js|rs|ts)', 'create'),
    (r'\b(fix|debug|solve)\b', 'fix'),
    (r'\b(modify|change|update|edit)\b', 'modify'),
]

EXTERNAL_PATTERNS = [
    (r'\b(implement|build)\b.*\b(feature|system|api)', 'implement'),
    (r'\b(explain|understand|how|what|why)\b.*\b(work|does|architecture)', 'explain'),
    (r'\b(design|plan|architect)\b', 'design'),
    (r'\b(refactor|optimize)\b.*\b(entire|whole|all)', 'refactor'),
]

def route(query: str) -> Tuple[str, str]:
    """Route query to handler type."""
    q = query.lower()

    for pattern, handler in LOCAL_PATTERNS:
        if re.search(pattern, q):
            return ('local', handler)

    for pattern, handler in AGENT_PATTERNS:
        if re.search(pattern, q):
            return ('agent', handler)

    for pattern, handler in EXTERNAL_PATTERNS:
        if re.search(pattern, q):
            return ('external', handler)

    # Default based on length
    if len(query.split()) < 8:
        return ('local', 'short')
    return ('agent', 'default')

# ============== EXECUTION ==============

def execute_local(query: str, handler: str, project_path: str = ".") -> str:
    """Execute locally without LLM."""
    try:
        if handler == 'list_dir':
            path = project_path
            match = re.search(r'(?:in|at|from)\s+([^\s]+)', query)
            if match:
                specified = match.group(1)
                # Check if it matches a project name (ignore) or is a real path
                projects = load_projects()
                project_names = [p["name"].lower() for p in projects["projects"]]
                if specified.lower() not in project_names:
                    path = os.path.expanduser(specified)

            entries = sorted(Path(path).iterdir(), key=lambda x: (x.is_file(), x.name))
            result = []
            for e in entries[:40]:
                prefix = "📁 " if e.is_dir() else "📄 "
                result.append(f"{prefix}{e.name}")
            return '\n'.join(result) or "Empty directory"

        elif handler == 'read_file':
            match = re.search(r'([^\s]+\.(py|js|rs|ts|json|md|txt|yaml|yml|toml))', query)
            if match:
                filepath = match.group(1)
                for base in [project_path, '.', os.path.expanduser('~')]:
                    full = Path(base) / filepath
                    if full.exists():
                        content = full.read_text()
                        if len(content) > 3000:
                            return f"# {filepath} (truncated)\n{content[:3000]}\n...[truncated]..."
                        return f"# {filepath}\n{content}"
            return "File not found"

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

        elif handler == 'run':
            match = re.search(r'(?:run|exec)\s+(.+)', query, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                if any(d in cmd for d in ['rm -rf', 'sudo', '> /dev/', 'dd if=']):
                    return f"BLOCKED: Dangerous command"
                result = subprocess.run(
                    cmd, shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=60
                )
                return (result.stdout + result.stderr)[:2000] or "Command completed"

        elif handler == 'search':
            match = re.search(r'(?:search|find|grep)\s+(?:for\s+)?["\']?([^"\']+)["\']?', query)
            if match:
                pattern = match.group(1).strip()
                result = subprocess.run(
                    f"grep -rn '{pattern}' --include='*.py' --include='*.js' --include='*.rs' --include='*.ts' . | head -20",
                    shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=30
                )
                return result.stdout or "No matches"

        return f"Use: list files, read <file>, git status, run <cmd>, search for <pattern>"

    except Exception as e:
        return f"Error: {e}"

def run_agent(task: str, project_path: str = ".", use_multi_agent: bool = True) -> str:
    """Run the agent for complex tasks - uses multi-agent orchestration if available."""

    # Check if task is complex enough for multi-agent
    is_complex = len(task.split()) > 15 or any(
        kw in task.lower() for kw in ['and', 'then', 'also', 'with tests', 'with docs']
    )

    # Use multi-agent orchestrator for complex tasks
    if use_multi_agent and is_complex:
        orchestrator = get_multi_agent()
        if orchestrator:
            print("[SAM] Using multi-agent orchestration...")
            return orchestrator.run(task)

    # Fallback to basic agent
    try:
        import sam_agent
        sam_agent.run_agent(task, project_path, max_iterations=8, auto=True)
        return "[Agent completed]"
    except ImportError:
        return "[Agent not available]"

def queue_external(query: str, context: str = "") -> str:
    """Queue for browser bridge."""
    import uuid

    queue = []
    if BRIDGE_QUEUE.exists():
        try:
            queue = json.load(open(BRIDGE_QUEUE))
        except:
            pass

    # Sanitize
    def sanitize(text):
        text = re.sub(r'(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*["\']?[\w\-\.]+["\']?', '[REDACTED]', text)
        text = re.sub(r'sk-[a-zA-Z0-9]{20,}', '[KEY]', text)
        text = re.sub(r'/Users/\w+/', '/Users/USER/', text)
        return text

    request_id = str(uuid.uuid4())[:8]
    prompt = sanitize(query)
    if context:
        prompt += f"\n\nContext:\n{sanitize(context)[:800]}"

    queue.append({
        "id": request_id,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    })

    json.dump(queue, open(BRIDGE_QUEUE, 'w'), indent=2)

    return f"""📤 Queued for external AI (ID: {request_id})

The browser bridge will process this automatically.
Check status: sam --check {request_id}"""

# ============== MAIN ==============

def sam(query: str, voice_output: bool = False) -> str:
    """Main SAM function with full brain integration."""

    # Find relevant project (with favorites boost)
    project = find_project(query)
    project_path = project["path"] if project else "."
    project_name = project["name"] if project else None

    if project:
        print(f"[SAM] Project: {project['name']}")

    # Get SSOT context if available
    ssot = get_ssot()
    ssot_context = ""
    if ssot and ssot.check_ssot_available():
        ssot_context = ssot.get_relevant_context(query)
        if ssot_context:
            print("[SAM] Found SSOT context")

    # Route the query
    handler_type, handler = route(query)
    print(f"[SAM] Route: {handler_type}/{handler}")

    # Execute
    if handler_type == 'local':
        result = execute_local(query, handler, project_path)

    elif handler_type == 'agent':
        result = run_agent(query, project_path)

    elif handler_type == 'external':
        context = get_project_context(project) if project else ""

        # Add SSOT context
        if ssot_context:
            context += f"\n\nSSOT Knowledge:\n{ssot_context[:500]}"

        # Add semantic memories
        memories = get_relevant_memories(query)
        if memories:
            context += "\n\nRelevant history:\n" + "\n".join(memories)
        result = queue_external(query, context)

    else:
        result = "Unknown route"

    # Remember this interaction
    remember(query, result, project_name)

    # Voice output if requested
    if voice_output:
        voice = get_voice()
        if voice and voice.config.config.get("enabled"):
            # Speak a summary (first 200 chars)
            summary = result[:200].replace('\n', ' ')
            voice.speak(summary)

    return result

def main():
    if len(sys.argv) < 2:
        print("""
SAM Enhanced - Full Brain AI Coding Assistant
==============================================

Usage:
  sam "<query>"                    Auto-route to best handler
  sam --projects                   List known projects
  sam --memory                     Show recent memory
  sam --check <id>                 Check bridge response
  sam --brain                      Show brain module status
  sam --favorites                  List starred projects
  sam --voice                      Enable/disable voice output
  sam --ssot                       Sync with SSOT

Examples:
  sam "list files in SAM"          → Routes to SAM project
  sam "create hello.py"            → Uses local agent
  sam "explain the architecture"   → Queues for ChatGPT/Claude
  sam "fix bug and write tests"    → Multi-agent orchestration
""")
        return

    args = sys.argv[1:]

    if "--projects" in args:
        data = load_projects()
        print("Known Projects:")
        for p in data["projects"]:
            print(f"  {p['name']:20} {p['path']}")
        return

    if "--memory" in args:
        memory = load_memory()
        print("Recent Memory:")
        for m in memory.get("interactions", [])[-10:]:
            print(f"  [{m.get('project', '?')}] {m['query'][:50]}")
        return

    if "--brain" in args:
        print("SAM Brain Status:")
        print(f"  Semantic Memory: {'✓' if get_semantic_memory() else '✗'}")
        print(f"  Multi-Agent:     {'✓' if get_multi_agent() else '✗'}")
        print(f"  SSOT Sync:       {'✓' if get_ssot() else '✗'}")
        print(f"  Favorites:       {'✓' if get_favorites() else '✗'}")
        print(f"  Voice Bridge:    {'✓' if get_voice() else '✗'}")

        sem = get_semantic_memory()
        if sem:
            print(f"  Memory entries:  {len(sem.entries)}")

        ssot = get_ssot()
        if ssot:
            status = ssot.status()
            print(f"  SSOT available:  {status['ssot_available']}")
        return

    if "--favorites" in args:
        fav = get_favorites()
        if fav:
            starred = fav.get_starred()
            print(f"Starred Projects ({len(starred)}):")
            for f in starred:
                pin = "📌" if f.pinned else "  "
                print(f"  {pin}⭐ {f.name}")
        else:
            print("Favorites not available")
        return

    if "--voice" in args:
        voice = get_voice()
        if voice:
            if "on" in args:
                voice.config.enable()
                print("Voice output enabled")
            elif "off" in args:
                voice.config.disable()
                print("Voice output disabled")
            else:
                status = voice.status()
                print("Voice Bridge Status:")
                for k, v in status.items():
                    print(f"  {k}: {v}")
        else:
            print("Voice bridge not available")
        return

    if "--ssot" in args:
        ssot = get_ssot()
        if ssot:
            if "sync" in args:
                result = ssot.sync()
                print(json.dumps(result, indent=2))
            else:
                status = ssot.status()
                print("SSOT Status:")
                for k, v in status.items():
                    print(f"  {k}: {v}")
        else:
            print("SSOT sync not available")
        return

    if "--check" in args:
        idx = args.index("--check")
        req_id = args[idx + 1]
        resp_file = Path.home() / ".sam_chatgpt_responses.json"
        if resp_file.exists():
            responses = json.load(open(resp_file))
            if req_id in responses:
                print(responses[req_id].get("response", "No response yet"))
                return
        print(f"No response for {req_id}")
        return

    # Check for voice flag
    voice_output = "--speak" in args
    if voice_output:
        args.remove("--speak")

    query = " ".join(args)
    result = sam(query, voice_output=voice_output)
    print(result)

if __name__ == "__main__":
    main()
