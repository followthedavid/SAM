"""SAM API Core Routes - Basic query, project listing, memory, status, search."""

from datetime import datetime
from shared_state import (
    load_inventory, load_memory, find_project, route, sam,
    STYLE_FILE,
)


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
                from voice.voice_output import SAMVoice
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

    # Check MLX availability (Ollama decommissioned 2026-01-18)
    mlx_available = False
    sam_model_ready = False
    try:
        from cognitive.mlx_cognitive import MLXCognitiveEngine
        mlx_available = True
        sam_model_ready = True  # MLX models load on-demand
    except ImportError:
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
        "mlx_available": mlx_available,
        "sam_model_ready": sam_model_ready,
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
        from voice.voice_output import SAMVoice
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
        from voice.voice_output import SAMVoice
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


# Route tables
GET_ROUTES = {
    "/api/health": lambda params: {"status": "ok", "timestamp": datetime.now().isoformat()},
    "/api/status": lambda params: api_status(),
    "/api/projects": lambda params: api_projects(),
    "/api/memory": lambda params: api_memory(),
    "/api/query": lambda params: api_query(params.get("q", [""])[0]) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
}

POST_ROUTES = {
    "/api/query": lambda data: api_query(data.get("query", "")) if data.get("query") else {"success": False, "error": "Missing query"},
}
