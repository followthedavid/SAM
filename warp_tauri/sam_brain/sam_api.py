#!/usr/bin/env python3
"""
SAM API - JSON interface for Tauri integration

Provides a simple CLI that outputs JSON for the Tauri app to consume.
Can also run as a local HTTP server.

Usage:
  sam_api.py query "list files in SAM"
  sam_api.py projects
  sam_api.py memory
  sam_api.py status
  sam_api.py search "<query>"
  sam_api.py categories
  sam_api.py starred
  sam_api.py server [port]
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add sam_brain to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Exhaustive inventory
INVENTORY_FILE = SCRIPT_DIR / "exhaustive_analysis" / "master_inventory.json"
STYLE_FILE = SCRIPT_DIR / "training_data" / "style_profile.json"

def load_inventory():
    """Load the exhaustive project inventory."""
    if INVENTORY_FILE.exists():
        return json.load(open(INVENTORY_FILE))
    return {"projects": {}, "meta": {}}

try:
    from sam_enhanced import sam, load_projects as load_projects_old, load_memory, find_project, route
except ImportError:
    # Fallback if sam_enhanced doesn't exist
    def sam(query): return f"SAM received: {query}"
    def load_projects_old(): return {"projects": []}
    def load_memory(): return {"interactions": []}
    def find_project(q): return None
    def route(q): return ("local", "fallback")


def api_query(query: str, speak: bool = False) -> dict:
    """Process a query and return JSON response."""
    start = datetime.now()

    # Find project
    project = find_project(query)
    handler_type, handler = route(query)

    result = {
        "query": query,
        "project": project["name"] if project else None,
        "route": f"{handler_type}/{handler}",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        output = sam(query)
        result["success"] = True
        result["output"] = output

        # Optionally speak the response
        if speak and output:
            try:
                from voice_output import SAMVoice
                voice = SAMVoice()
                # Truncate long responses for speech
                speech_text = output[:500] if len(output) > 500 else output
                voice_result = voice.speak(speech_text)
                result["voice"] = {
                    "spoken": voice_result.get("success", False),
                    "audio_path": voice_result.get("audio_path"),
                }
            except Exception as ve:
                result["voice"] = {"spoken": False, "error": str(ve)}

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    result["duration_ms"] = (datetime.now() - start).total_seconds() * 1000
    return result


def api_projects() -> dict:
    """Get project list from exhaustive inventory."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Group by status with top projects
    by_status = {}
    for path, data in projects.items():
        status = data.get("status", "unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append({
            "path": path,
            "name": data.get("name", ""),
            "languages": data.get("languages", []),
            "lines": data.get("total_lines", 0),
            "importance": data.get("importance_score", 0),
            "starred": data.get("starred", False),
        })

    # Sort and limit
    for status in by_status:
        by_status[status].sort(key=lambda x: -x["importance"])
        by_status[status] = by_status[status][:25]

    return {
        "success": True,
        "total": len(projects),
        "by_status": {s: len([p for p, d in projects.items() if d.get("status") == s])
                      for s in ["active", "recent", "stale", "abandoned"]},
        "starred_count": sum(1 for d in projects.values() if d.get("starred")),
        "projects": by_status
    }


def api_memory() -> dict:
    """Get memory/history."""
    memory = load_memory()
    return {
        "success": True,
        "interactions": memory.get("interactions", [])[-20:],
        "count": len(memory.get("interactions", []))
    }


def api_status() -> dict:
    """Get SAM status with exhaustive inventory info."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Check Ollama and sam-coder model
    ollama_ok = False
    sam_coder_loaded = False
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        ollama_ok = result.returncode == 0
        sam_coder_loaded = "sam-coder" in result.stdout
    except:
        pass

    # Count by status
    active = sum(1 for d in projects.values() if d.get("status") == "active")
    starred = sum(1 for d in projects.values() if d.get("starred"))

    # Get drives scanned
    drives = set()
    for p in projects.keys():
        if p.startswith("/Volumes/"):
            drives.add(p.split("/")[2])
        elif p.startswith("/Users/"):
            drives.add("local")

    return {
        "success": True,
        "project_count": len(projects),
        "active_projects": active,
        "starred_projects": starred,
        "ollama_running": ollama_ok,
        "sam_coder_loaded": sam_coder_loaded,
        "style_profile_loaded": STYLE_FILE.exists(),
        "drives_scanned": list(drives),
        "last_updated": inv.get("meta", {}).get("generated_at", "unknown"),
        "memory_count": len(load_memory().get("interactions", []))
    }


def api_search(query: str) -> dict:
    """Search projects by name, path, or description."""
    inv = load_inventory()
    projects = inv.get("projects", {})
    query_lower = query.lower()

    results = []
    for path, data in projects.items():
        name = data.get("name", "").lower()
        desc = data.get("description", "").lower()
        tags = " ".join(data.get("tags", [])).lower()

        if query_lower in name or query_lower in path.lower() or query_lower in desc or query_lower in tags:
            results.append({
                "path": path,
                "name": data.get("name", ""),
                "status": data.get("status", "unknown"),
                "languages": data.get("languages", []),
                "lines": data.get("total_lines", 0),
                "importance": data.get("importance_score", 0),
                "starred": data.get("starred", False),
                "description": data.get("description", "")[:100],
            })

    results.sort(key=lambda x: -x["importance"])
    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": results[:50]
    }


def api_categories() -> dict:
    """Get project categories."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    # Category patterns
    patterns = {
        "sam_core": ["sam", "warp_tauri", "warp_core", "sam_brain"],
        "voice": ["rvc", "voice", "tts", "speech", "audio", "clone"],
        "face_avatar": ["face", "deca", "mica", "avatar", "body", "mesh"],
        "image_gen": ["comfy", "diffusion", "lora", "stable"],
        "video": ["video", "rife", "motion", "frame", "animation"],
        "ml": ["train", "model", "neural", "inference"],
        "stash_adult": ["stash", "adult", "performer"],
        "media": ["plex", "media", "gallery", "download"],
        "web": ["react", "vue", "frontend", "dashboard"],
        "api": ["api", "server", "backend", "fastapi"],
        "games": ["unity", "unreal", "game"],
        "ios": ["ios", "swift", "macos"],
        "automation": ["script", "pipeline", "workflow"],
    }

    categories = {cat: 0 for cat in patterns}
    categories["other"] = 0

    for path, data in projects.items():
        name = data.get("name", "").lower()
        path_lower = path.lower()
        matched = False

        for cat, keywords in patterns.items():
            if any(kw in name or kw in path_lower for kw in keywords):
                categories[cat] += 1
                matched = True
                break

        if not matched:
            categories["other"] += 1

    return {
        "success": True,
        "categories": categories,
        "total": len(projects)
    }


def api_starred() -> dict:
    """Get starred/favorite projects."""
    inv = load_inventory()
    projects = inv.get("projects", {})

    starred = []
    for path, data in projects.items():
        if data.get("starred"):
            starred.append({
                "path": path,
                "name": data.get("name", ""),
                "status": data.get("status", "unknown"),
                "languages": data.get("languages", []),
                "lines": data.get("total_lines", 0),
                "importance": data.get("importance_score", 0),
                "description": data.get("description", "")[:100],
            })

    starred.sort(key=lambda x: -x["importance"])
    return {
        "success": True,
        "count": len(starred),
        "projects": starred
    }


def api_speak(text: str, voice: str = None) -> dict:
    """Speak text using TTS."""
    try:
        from voice_output import SAMVoice
        sam_voice = SAMVoice()

        if voice:
            sam_voice.set_voice(voice)

        result = sam_voice.speak(text)
        return {
            "success": result.get("success", False),
            "text": text,
            "audio_path": result.get("audio_path"),
            "voice": result.get("voice"),
            "engine": result.get("engine"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def api_voices() -> dict:
    """List available voices."""
    try:
        from voice_output import SAMVoice
        sam_voice = SAMVoice()
        voices = sam_voice.list_voices()

        # Filter to English voices
        english = [v for v in voices if v.get("locale", "").startswith("en")]

        return {
            "success": True,
            "voices": english,
            "current": sam_voice.config.voice,
            "engine": sam_voice.config.engine,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_server(port: int = 8765):
    """Run a simple HTTP server for the API."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    class SAMHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Quiet

        def send_json(self, data: dict, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            params = urllib.parse.parse_qs(parsed.query)

            if path == "/api/status":
                self.send_json(api_status())
            elif path == "/api/projects":
                self.send_json(api_projects())
            elif path == "/api/memory":
                self.send_json(api_memory())
            elif path == "/api/query":
                query = params.get("q", [""])[0]
                if query:
                    self.send_json(api_query(query))
                else:
                    self.send_json({"success": False, "error": "Missing query parameter 'q'"}, 400)
            else:
                self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

        def do_POST(self):
            if self.path == "/api/query":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                try:
                    data = json.loads(body)
                    query = data.get("query", "")
                    if query:
                        self.send_json(api_query(query))
                    else:
                        self.send_json({"success": False, "error": "Missing query"}, 400)
                except json.JSONDecodeError:
                    self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            else:
                self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

    server = HTTPServer(("localhost", port), SAMHandler)
    print(f"SAM API server running on http://localhost:{port}")
    print("Endpoints:")
    print(f"  GET  /api/status")
    print(f"  GET  /api/projects")
    print(f"  GET  /api/memory")
    print(f"  GET  /api/query?q=<query>")
    print(f"  POST /api/query {{\"query\": \"...\"}}")
    print()
    server.serve_forever()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "query":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_query(query), indent=2))

    elif cmd == "projects":
        print(json.dumps(api_projects(), indent=2))

    elif cmd == "memory":
        print(json.dumps(api_memory(), indent=2))

    elif cmd == "status":
        print(json.dumps(api_status(), indent=2))

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_search(query), indent=2))

    elif cmd == "categories":
        print(json.dumps(api_categories(), indent=2))

    elif cmd == "starred":
        print(json.dumps(api_starred(), indent=2))

    elif cmd == "speak":
        text = " ".join(sys.argv[2:])
        print(json.dumps(api_speak(text), indent=2))

    elif cmd == "voices":
        print(json.dumps(api_voices(), indent=2))

    elif cmd == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        run_server(port)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
