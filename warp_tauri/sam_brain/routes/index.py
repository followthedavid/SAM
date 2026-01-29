"""SAM API Index Routes - Code index management, build, clear, watch."""

from datetime import datetime
from pathlib import Path
import shared_state


def api_index_status() -> dict:
    """Get comprehensive index statistics."""
    try:
        from cognitive.code_indexer import get_code_indexer
        indexer = get_code_indexer()

        stats = indexer.get_stats()

        import sqlite3
        conn = sqlite3.connect(indexer.db_path)
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT project_id FROM code_entities")
        projects = [row[0] for row in cur.fetchall()]

        project_stats = {}
        for project_id in projects:
            cur.execute(
                "SELECT type, COUNT(*) FROM code_entities WHERE project_id = ? GROUP BY type",
                (project_id,)
            )
            project_stats[project_id] = {
                "by_type": {row[0]: row[1] for row in cur.fetchall()}
            }
            cur.execute(
                "SELECT COUNT(*) FROM indexed_files WHERE project_id = ?",
                (project_id,)
            )
            project_stats[project_id]["files_indexed"] = cur.fetchone()[0]

            cur.execute(
                "SELECT MAX(indexed_at) FROM indexed_files WHERE project_id = ?",
                (project_id,)
            )
            last_indexed = cur.fetchone()[0]
            if last_indexed:
                project_stats[project_id]["last_indexed"] = datetime.fromtimestamp(last_indexed).isoformat()

        conn.close()

        watcher_running = shared_state._watcher_observer is not None and shared_state._watcher_observer.is_alive()

        return {
            "success": True,
            "total_entities": stats.get("total_entities", 0),
            "files_indexed": stats.get("files_indexed", 0),
            "by_type": stats.get("by_type", {}),
            "projects": project_stats,
            "project_count": len(projects),
            "db_path": str(indexer.db_path),
            "watcher_running": watcher_running,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_build(project_path: str, project_id: str = None, force: bool = False) -> dict:
    """Build or rebuild the code index for a project."""
    try:
        import os
        from cognitive.code_indexer import get_code_indexer

        indexer = get_code_indexer()
        abs_path = os.path.abspath(project_path)

        if not project_id:
            project_id = Path(abs_path).name

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path not found: {abs_path}"
            }

        start_time = datetime.now()
        stats = indexer.index_project(abs_path, project_id, force)
        duration = (datetime.now() - start_time).total_seconds()

        return {
            "success": True,
            "project_id": project_id,
            "project_path": abs_path,
            "stats": stats,
            "duration_seconds": round(duration, 2),
            "force": force,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_clear(project_id: str = None) -> dict:
    """Clear the index for a project or all projects."""
    try:
        from cognitive.code_indexer import get_code_indexer
        import sqlite3

        indexer = get_code_indexer()

        if project_id:
            indexer.clear_project(project_id)
            return {
                "success": True,
                "cleared": project_id,
                "message": f"Cleared index for project: {project_id}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            conn = sqlite3.connect(indexer.db_path)
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM code_entities")
            entities_cleared = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM indexed_files")
            files_cleared = cur.fetchone()[0]

            cur.execute("DELETE FROM code_entities")
            cur.execute("DELETE FROM indexed_files")
            conn.commit()
            conn.close()

            return {
                "success": True,
                "cleared": "all",
                "entities_cleared": entities_cleared,
                "files_cleared": files_cleared,
                "message": "Cleared entire code index",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_watch(project_path: str, project_id: str = None) -> dict:
    """Start a file watcher for automatic index updates."""
    try:
        import os
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        from cognitive.code_indexer import get_code_indexer

        abs_path = os.path.abspath(project_path)

        if not project_id:
            project_id = Path(abs_path).name

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path not found: {abs_path}"
            }

        # Stop existing watcher if running
        if shared_state._watcher_observer is not None and shared_state._watcher_observer.is_alive():
            shared_state._watcher_observer.stop()
            shared_state._watcher_observer.join(timeout=2)

        indexer = get_code_indexer()

        class IndexUpdateHandler(FileSystemEventHandler):
            """Handler that updates the code index on file changes."""

            EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs'}
            SKIP_DIRS = {'node_modules', '.git', '__pycache__', 'target', 'dist', 'build', '.venv', 'venv'}

            def __init__(self, indexer, project_id):
                self.indexer = indexer
                self.project_id = project_id
                self.last_event = {}
                self.debounce_seconds = 1

            def should_process(self, path: str) -> bool:
                """Check if file should be processed."""
                path_obj = Path(path)

                if path_obj.suffix not in self.EXTENSIONS:
                    return False

                if any(skip in path_obj.parts for skip in self.SKIP_DIRS):
                    return False

                import time
                now = time.time()
                if path in self.last_event and (now - self.last_event[path]) < self.debounce_seconds:
                    return False
                self.last_event[path] = now

                return True

            def on_modified(self, event):
                if event.is_directory:
                    return
                if not self.should_process(event.src_path):
                    return

                from cognitive.code_indexer import PythonParser, JavaScriptParser, RustParser
                import sqlite3
                import time

                file_path = Path(event.src_path)

                parsers = {
                    '.py': PythonParser,
                    '.js': JavaScriptParser,
                    '.ts': JavaScriptParser,
                    '.jsx': JavaScriptParser,
                    '.tsx': JavaScriptParser,
                    '.rs': RustParser,
                }

                if file_path.suffix not in parsers:
                    return

                parser = parsers[file_path.suffix]()
                entities = parser.parse(file_path, self.project_id)

                conn = sqlite3.connect(self.indexer.db_path)
                cur = conn.cursor()

                cur.execute("DELETE FROM code_entities WHERE file_path = ?", (str(file_path),))

                for entity in entities:
                    cur.execute("""
                        INSERT OR REPLACE INTO code_entities
                        (id, name, type, signature, docstring, file_path, line_number, content, project_id, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entity.id, entity.name, entity.type, entity.signature,
                        entity.docstring, entity.file_path, entity.line_number,
                        entity.content, entity.project_id, time.time()
                    ))

                cur.execute("""
                    INSERT OR REPLACE INTO indexed_files (file_path, project_id, mtime, indexed_at)
                    VALUES (?, ?, ?, ?)
                """, (str(file_path), self.project_id, file_path.stat().st_mtime, time.time()))

                conn.commit()
                conn.close()

                print(f"[Index Watch] Updated: {file_path.name} ({len(entities)} entities)")

            def on_created(self, event):
                self.on_modified(event)

            def on_deleted(self, event):
                if event.is_directory:
                    return

                import sqlite3
                conn = sqlite3.connect(self.indexer.db_path)
                cur = conn.cursor()
                cur.execute("DELETE FROM code_entities WHERE file_path = ?", (event.src_path,))
                cur.execute("DELETE FROM indexed_files WHERE file_path = ?", (event.src_path,))
                conn.commit()
                conn.close()
                print(f"[Index Watch] Removed: {Path(event.src_path).name}")

        shared_state._index_watcher = IndexUpdateHandler(indexer, project_id)
        shared_state._watcher_observer = Observer()
        shared_state._watcher_observer.schedule(shared_state._index_watcher, abs_path, recursive=True)
        shared_state._watcher_observer.start()

        return {
            "success": True,
            "watching": abs_path,
            "project_id": project_id,
            "message": f"Started watching {abs_path} for changes",
            "timestamp": datetime.now().isoformat(),
        }
    except ImportError:
        return {
            "success": False,
            "error": "watchdog package not installed. Install with: pip install watchdog"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_index_watch_stop() -> dict:
    """Stop the file watcher."""
    try:
        if shared_state._watcher_observer is None:
            return {
                "success": True,
                "message": "No watcher was running",
                "timestamp": datetime.now().isoformat(),
            }

        if shared_state._watcher_observer.is_alive():
            shared_state._watcher_observer.stop()
            shared_state._watcher_observer.join(timeout=2)

        shared_state._watcher_observer = None

        return {
            "success": True,
            "message": "Watcher stopped",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/index/status": lambda params: api_index_status(),
    "/api/index/search": lambda params: _index_search_handler(params),
    "/api/index/watch/stop": lambda params: api_index_watch_stop(),
}

def _index_search_handler(params):
    """Handle /api/index/search GET route."""
    from routes.project import api_code_search
    query = params.get("q", [""])[0]
    if not query:
        return {"success": False, "error": "Missing query parameter 'q'"}
    project_id = params.get("project", [None])[0]
    entity_type = params.get("type", [None])[0]
    limit = int(params.get("limit", ["10"])[0])
    return api_code_search(query, project_id, entity_type, limit)

POST_ROUTES = {
    "/api/index/build": lambda data: api_index_build(data.get("path", "."), data.get("project_id"), data.get("force", False)),
    "/api/index/clear": lambda data: api_index_clear(data.get("project_id")),
    "/api/index/watch": lambda data: api_index_watch(data.get("path", "."), data.get("project_id")),
}
