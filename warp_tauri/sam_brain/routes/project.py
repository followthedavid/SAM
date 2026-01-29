"""SAM API Project Routes - Project context, sessions, TODOs, code index."""

from datetime import datetime


def api_project_context(path: str = ".") -> dict:
    """Get project context for a path."""
    try:
        import os
        from memory.project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(path))
        if not project:
            return {"success": True, "project": None, "message": "No project detected"}

        todos = ctx.get_project_todos(project.id, limit=5)
        session = ctx.get_last_session(project.id)
        context_text = ctx.get_project_context(project)

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "category": project.category,
                "tech_stack": project.tech_stack,
                "last_accessed": project.last_accessed.isoformat(),
            },
            "todos": todos,
            "last_session": {
                "working_on": session.working_on,
                "recent_files": session.recent_files,
                "timestamp": session.timestamp.isoformat(),
            } if session else None,
            "context_for_prompt": context_text,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_save_session(project_path: str, working_on: str = "", notes: str = "") -> dict:
    """Save session state for a project."""
    try:
        import os
        from memory.project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(project_path))
        if not project:
            return {"success": False, "error": "No project detected at path"}

        ctx.save_session_state(
            project_id=project.id,
            working_on=working_on,
            notes=notes
        )

        return {
            "success": True,
            "project": project.name,
            "working_on": working_on,
            "saved": True,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_recent_projects(limit: int = 5) -> dict:
    """Get recently accessed projects."""
    try:
        from memory.project_context import get_project_context
        ctx = get_project_context()

        projects = ctx.get_recent_projects(limit)

        return {
            "success": True,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "path": p.path,
                    "category": p.category,
                    "tech_stack": p.tech_stack,
                    "last_accessed": p.last_accessed.isoformat(),
                }
                for p in projects
            ],
            "count": len(projects),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_project_current() -> dict:
    """Get the current project based on active terminal/IDE working directory."""
    try:
        from memory.project_context import get_project_watcher, get_current_project, SSOT_PROJECTS

        watcher = get_project_watcher(auto_start=False)
        current_project = None
        detected_from = "none"

        if watcher and watcher._current_project:
            current_project = watcher._current_project
            detected_from = "watcher"
        else:
            current_project = get_current_project()
            if current_project:
                detected_from = "cwd"

        if not current_project:
            return {
                "success": True,
                "project": None,
                "message": "No project detected",
                "detected_from": detected_from,
                "timestamp": datetime.now().isoformat(),
            }

        type_icons = {
            "python": "chevron.left.forwardslash.chevron.right",
            "swift": "swift",
            "swiftui": "swift",
            "rust": "gearshape.2.fill",
            "tauri": "macwindow",
            "typescript": "t.square.fill",
            "javascript": "j.square.fill",
            "unity": "gamecontroller.fill",
            "comfyui": "photo.artframe",
            "docker": "shippingbox.fill",
            "shell": "terminal.fill",
        }

        project_type = getattr(current_project, 'type', 'unknown')
        if hasattr(current_project, 'tech_stack') and current_project.tech_stack:
            project_type = current_project.tech_stack[0] if isinstance(current_project.tech_stack, list) else current_project.tech_stack

        project_type_lower = project_type.lower() if project_type else "unknown"
        icon = type_icons.get(project_type_lower, "folder.fill")

        status = getattr(current_project, 'status', 'active')

        return {
            "success": True,
            "project": {
                "name": current_project.name,
                "path": getattr(current_project, 'path', None),
                "type": project_type,
                "status": status,
                "icon": icon,
                "tier": getattr(current_project, 'tier', None),
            },
            "detected_from": detected_from,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "project": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def api_project_todos(path: str = ".", limit: int = 10) -> dict:
    """Get TODOs for a project."""
    try:
        import os
        from memory.project_context import get_project_context
        ctx = get_project_context()

        project = ctx.detect_project(os.path.abspath(path))
        if not project:
            return {"success": True, "project": None, "todos": [], "message": "No project detected"}

        found = ctx.scan_for_todos(project.path, project.id)

        todos = ctx.get_project_todos(project.id, limit)

        return {
            "success": True,
            "project": project.name,
            "todos": todos,
            "count": len(todos),
            "scanned": found,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_index(path: str, project_id: str = "default", force: bool = False) -> dict:
    """Index code files for a project."""
    try:
        import os
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        stats = indexer.index_project(os.path.abspath(path), project_id, force)

        return {
            "success": True,
            "project_id": project_id,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_search(query: str, project_id: str = None, entity_type: str = None, limit: int = 10) -> dict:
    """Search indexed code."""
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        results = indexer.search(query, project_id, entity_type, limit)

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "name": r.name,
                    "type": r.type,
                    "signature": r.signature,
                    "docstring": r.docstring[:200] if r.docstring else None,
                    "file": r.file_path.split("/")[-1],
                    "file_path": r.file_path,
                    "line": r.line_number,
                }
                for r in results
            ],
            "count": len(results),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_code_stats(project_id: str = None) -> dict:
    """Get code index statistics."""
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        stats = indexer.get_stats(project_id)

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/project": lambda params: api_project_context(params.get("path", ["."])[0]),
    "/api/project/recent": lambda params: api_recent_projects(int(params.get("limit", ["5"])[0])),
    "/api/project/current": lambda params: api_project_current(),
    "/api/project/todos": lambda params: api_project_todos(params.get("path", ["."])[0], int(params.get("limit", ["10"])[0])),
    "/api/code/search": lambda params: api_code_search(params.get("q", [""])[0], params.get("project", [None])[0], params.get("type", [None])[0], int(params.get("limit", ["10"])[0])) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
    "/api/code/stats": lambda params: api_code_stats(params.get("project", [None])[0]),
}

POST_ROUTES = {
    "/api/project/session": lambda data: api_save_session(data.get("path", "."), data.get("working_on", ""), data.get("notes", "")),
    "/api/code/index": lambda data: api_code_index(data.get("path", "."), data.get("project_id", "default"), data.get("force", False)),
}
