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
  sam_api.py self          # SAM explains itself
  sam_api.py suggest       # Top improvement suggestions
  sam_api.py proactive     # What SAM noticed
  sam_api.py learning      # What SAM has learned
  sam_api.py feedback      # Record feedback (JSON input)
  sam_api.py scan          # Trigger improvement scan
  sam_api.py context       # Full context for Claude (paste-ready)
  sam_api.py warp-status   # Warp replication status
  sam_api.py server [port]

Fact Management (Phase 1.3.9):
  sam_api.py facts list [--user X] [--category X] [--min-confidence 0.5]
  sam_api.py facts add "fact text" --category preferences [--user X]
  sam_api.py facts remove <fact_id>
  sam_api.py facts search "query" [--user X]
  sam_api.py facts get <fact_id>

Index Management (Phase 2.2.10):
  sam_api.py index status                              # Show index stats
  sam_api.py index build [path] [--project X] [--force]  # Build/rebuild index
  sam_api.py index search "query" [--project X] [--type X]  # Search index
  sam_api.py index watch [path] [--project X]          # Start file watcher
  sam_api.py index stop                                # Stop file watcher
  sam_api.py index clear [--project X]                 # Clear index
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add sam_brain to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Import shared state and route tables
from shared_state import (
    SCRIPT_DIR, APPROVAL_AVAILABLE, _start_idle_watcher,
)

# Re-export shared_state symbols that external code might import from sam_api
from shared_state import (
    get_sam_intelligence, get_distillation_db, get_distillation_stats,
    get_feedback_db, get_compression_monitor, record_compression_stats,
    get_vision_stats_monitor, record_vision_stats,
    get_cognitive_orchestrator, get_vision_engine, get_smart_vision_router,
    get_voice_pipeline, load_inventory,
    CompressionMonitor, CompressionRecord, VisionStatsMonitor, VisionRecord,
)

# Import route functions for CLI use
from routes.core import (
    api_query, api_projects, api_memory, api_status, api_search,
    api_categories, api_starred, api_speak, api_voices,
)
from routes.intelligence import (
    api_self, api_suggest, api_proactive, api_learning, api_feedback,
    api_scan, api_think, api_orchestrate,
)
from routes.cognitive import api_cognitive_process, api_cognitive_feedback
from routes.facts import (
    api_intelligence_stats, api_user_facts, api_remember_fact,
    api_fact_context, api_facts_list, api_facts_add, api_facts_remove,
    api_facts_search, api_facts_get,
)
from routes.project import api_code_search
from routes.index import (
    api_index_status, api_index_build, api_index_clear,
    api_index_watch, api_index_watch_stop,
)

# Import route tables
from routes import (
    get_all_get_routes, get_all_post_routes, get_all_delete_routes,
    get_all_stream_post_routes, get_all_prefix_get_routes,
)

# Approval queue imports (conditional)
if APPROVAL_AVAILABLE:
    from shared_state import (
        api_approval_queue, api_approval_approve, api_approval_reject,
        api_approval_history, api_approval_get, api_approval_stats,
    )


def run_server(port: int = 8765):
    """Run a simple HTTP server for the API."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    # Build route tables once at startup
    GET_ROUTES = get_all_get_routes()
    POST_ROUTES = get_all_post_routes()
    DELETE_ROUTES = get_all_delete_routes()
    STREAM_POST_ROUTES = get_all_stream_post_routes()
    PREFIX_GET_ROUTES = get_all_prefix_get_routes()

    class SAMHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Quiet

        def send_json(self, data: dict, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def send_sse_headers(self):
            """Send SSE response headers."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            params = urllib.parse.parse_qs(parsed.query)

            # Serve mobile web interface
            if path == "/" or path == "/mobile":
                try:
                    static_dir = Path(__file__).parent / "static"
                    mobile_html = static_dir / "mobile.html"
                    if mobile_html.exists():
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(mobile_html.read_bytes())
                    else:
                        self.send_json({"error": "Mobile interface not found"}, 404)
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                return

            # Static file serving
            if path.startswith("/static/"):
                try:
                    static_dir = Path(__file__).parent / "static"
                    file_path = (static_dir / path[8:]).resolve()
                    # Prevent path traversal
                    if not str(file_path).startswith(str(static_dir.resolve())):
                        self.send_json({"error": "Access denied"}, 403)
                        return
                    if file_path.exists() and file_path.is_file():
                        content_type = "text/html" if path.endswith(".html") else \
                                      "text/css" if path.endswith(".css") else \
                                      "application/javascript" if path.endswith(".js") else \
                                      "application/octet-stream"
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(file_path.read_bytes())
                    else:
                        self.send_json({"error": "File not found"}, 404)
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                return

            # Exact GET route match
            handler = GET_ROUTES.get(path)
            if handler:
                result = handler(params)
                if isinstance(result, dict) and "error" in result and not result.get("success", True):
                    self.send_json(result, 400)
                else:
                    self.send_json(result)
                return

            # Prefix GET route match (for parameterized routes like /api/facts/<id>)
            for prefix, handler in PREFIX_GET_ROUTES.items():
                if path.startswith(prefix) and path != prefix.rstrip("/"):
                    result = handler(path, params)
                    self.send_json(result)
                    return

            # Approval Queue GET endpoints (Phase 4.1)
            if APPROVAL_AVAILABLE:
                if path == "/api/approval/queue":
                    project_id = params.get("project_id", [None])[0]
                    self.send_json(api_approval_queue(project_id))
                    return
                elif path == "/api/approval/stats":
                    self.send_json(api_approval_stats())
                    return
                elif path == "/api/approval/history":
                    limit = int(params.get("limit", ["50"])[0])
                    project_id = params.get("project_id", [None])[0]
                    status = params.get("status", [None])[0]
                    self.send_json(api_approval_history(limit, project_id, status))
                    return
                elif path.startswith("/api/approval/"):
                    item_id = path.split("/")[-1]
                    if item_id and item_id != "approval":
                        self.send_json(api_approval_get(item_id))
                    else:
                        self.send_json({"success": False, "error": "Missing item ID"}, 400)
                    return

            self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_json({"success": False, "error": "Invalid JSON"}, 400)
                return

            path = self.path

            # Check SSE streaming routes first
            stream_handler = STREAM_POST_ROUTES.get(path)
            if stream_handler:
                generator = stream_handler(data)
                if generator is None:
                    self.send_json({"success": False, "error": "Missing required parameters"}, 400)
                    return
                try:
                    self.send_sse_headers()
                    for event in generator:
                        self.wfile.write(event.encode())
                        self.wfile.flush()
                except Exception as e:
                    try:
                        self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode())
                    except:
                        pass
                return

            # Exact POST route match
            handler = POST_ROUTES.get(path)
            if handler:
                result = handler(data)
                if isinstance(result, dict):
                    status = 400 if not result.get("success", True) and "error" in result else 200
                    self.send_json(result, status)
                else:
                    self.send_json({"success": False, "error": "Invalid handler response"}, 500)
                return

            # Approval Queue POST endpoints (Phase 4.1)
            if APPROVAL_AVAILABLE:
                if path == "/api/approval/approve":
                    item_id = data.get("item_id", "")
                    approved_by = data.get("approved_by", "david")
                    if item_id:
                        self.send_json(api_approval_approve(item_id, approved_by))
                    else:
                        self.send_json({"success": False, "error": "Missing item_id"}, 400)
                    return
                elif path == "/api/approval/reject":
                    item_id = data.get("item_id", "")
                    reason = data.get("reason")
                    if item_id:
                        self.send_json(api_approval_reject(item_id, reason))
                    else:
                        self.send_json({"success": False, "error": "Missing item_id"}, 400)
                    return

            self.send_json({"success": False, "error": "Unknown endpoint"}, 404)

        def do_DELETE(self):
            """Handle DELETE requests."""
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Check prefix DELETE routes
            for prefix, handler in DELETE_ROUTES.items():
                if path.startswith(prefix):
                    result = handler(path)
                    self.send_json(result)
                    return

            self.send_json({"success": False, "error": "DELETE not supported for this endpoint"}, 405)

    # Bind to all interfaces for network access (Tailscale, phone, etc.)
    server = HTTPServer(("0.0.0.0", port), SAMHandler)
    print(f"SAM API server running on http://0.0.0.0:{port}")
    print(f"  Local: http://localhost:{port}")
    print(f"  Network: http://100.100.11.31:{port} (Tailscale)")

    # Start idle watcher for auto-unload
    _start_idle_watcher()

    print(f"\nRoute tables loaded:")
    print(f"  GET routes:    {len(GET_ROUTES)}")
    print(f"  POST routes:   {len(POST_ROUTES)}")
    print(f"  DELETE routes:  {len(DELETE_ROUTES)}")
    print(f"  SSE streams:   {len(STREAM_POST_ROUTES)}")
    print(f"  Prefix GET:    {len(PREFIX_GET_ROUTES)}")

    print("\nEndpoints:")
    print("  Legacy:")
    print("    GET  /api/status         - System status")
    print("    GET  /api/projects       - Project list")
    print("    GET  /api/memory         - Interaction history")
    print("    GET  /api/query?q=...    - Query SAM")
    print("    POST /api/query          - {\"query\": \"...\"}")
    print()
    print("  Intelligence:")
    print("    GET  /api/self           - SAM explains itself")
    print("    GET  /api/suggest        - Top improvement suggestions")
    print("    GET  /api/proactive      - What SAM noticed")
    print("    GET  /api/learning       - What SAM has learned")
    print("    GET  /api/scan           - Trigger improvement scan")
    print("    GET  /api/think?q=...    - SAM thinks about query")
    print("    GET  /api/think/colors   - Color scheme for thought types")
    print("    POST /api/feedback       - {improvement_id, success, impact, lessons}")
    print("    POST /api/think          - {\"query\": \"...\"}")
    print("    POST /api/think/stream   - SSE: {\"query\": \"...\", \"mode\": \"structured|coding|standard\"}")
    print()
    print("  Cognitive (MLX + Full Pipeline):")
    print("    GET  /api/resources                - System resources")
    print("    GET  /api/context/stats            - Compression monitoring")
    print("    GET  /api/unload                   - Unload model to free memory")
    print("    GET  /api/cognitive/state          - Cognitive system state")
    print("    GET  /api/cognitive/mood           - Current emotional state")
    print("    POST /api/cognitive/process        - {\"query\": \"...\", \"user_id\": \"...\"}")
    print("    POST /api/cognitive/feedback       - Save feedback")
    print("    POST /api/cognitive/stream         - SSE streaming tokens")
    print()
    print("  Vision, Voice, Facts, Index, Distillation, Approval - all routes available")
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

    # SAM Intelligence commands
    elif cmd == "self":
        print(json.dumps(api_self(), indent=2))

    elif cmd == "suggest":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(json.dumps(api_suggest(limit), indent=2))

    elif cmd == "proactive":
        print(json.dumps(api_proactive(), indent=2))

    elif cmd == "learning":
        print(json.dumps(api_learning(), indent=2))

    elif cmd == "feedback":
        if len(sys.argv) > 2:
            try:
                data = json.loads(sys.argv[2])
                result = api_feedback(
                    data.get("improvement_id", ""),
                    data.get("success", True),
                    data.get("impact", 0.5),
                    data.get("lessons", "")
                )
                print(json.dumps(result, indent=2))
            except json.JSONDecodeError:
                print(json.dumps({"success": False, "error": "Invalid JSON"}, indent=2))
        else:
            print(json.dumps({"success": False, "error": "Provide JSON: {improvement_id, success, impact, lessons}"}, indent=2))

    elif cmd == "scan":
        print(json.dumps(api_scan(), indent=2))

    elif cmd == "think":
        query = " ".join(sys.argv[2:])
        print(json.dumps(api_think(query), indent=2))

    elif cmd == "context":
        context_file = SCRIPT_DIR / "warp_knowledge" / "CLAUDE_CONTEXT.md"
        if context_file.exists():
            print(context_file.read_text())
        else:
            print("Context file not found. Run analysis first.")

    elif cmd == "warp-status":
        status_file = SCRIPT_DIR / "warp_knowledge" / "WARP_REPLICATION_STATUS.md"
        if status_file.exists():
            print(status_file.read_text())
        else:
            print("Status file not found.")

    # ============ Fact Management CLI (Phase 1.3.9) ============
    elif cmd == "facts":
        if len(sys.argv) < 3:
            print("Usage: sam_api.py facts <subcommand> [options]")
            print()
            print("Subcommands:")
            print("  list [--user X] [--category X] [--min-confidence 0.5]")
            print("  add \"fact\" --category X [--user X] [--source explicit]")
            print("  remove <fact_id>")
            print("  search \"query\" [--user X]")
            print("  get <fact_id>")
            print()
            print("Categories: preferences, biographical, projects, skills, corrections, relationships, context, system")
            print("Sources: explicit, conversation, correction, inferred, system")
            return

        subcmd = sys.argv[2]

        if subcmd == "list":
            user_id = "david"
            category = None
            min_confidence = 0.0
            limit = 50

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                    category = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--min-confidence" and i + 1 < len(sys.argv):
                    min_confidence = float(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_facts_list(user_id, category, min_confidence, limit), indent=2))

        elif subcmd == "add":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts add \"fact\" --category <category> [--user X] [--source X]")
                return

            fact_text = sys.argv[3]
            user_id = "david"
            category = None
            source = "explicit"
            confidence = None

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                    category = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--source" and i + 1 < len(sys.argv):
                    source = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--confidence" and i + 1 < len(sys.argv):
                    confidence = float(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            if not category:
                print("Error: --category is required")
                print("Categories: preferences, biographical, projects, skills, corrections, relationships, context, system")
                return

            print(json.dumps(api_facts_add(fact_text, category, user_id, source, confidence), indent=2))

        elif subcmd == "remove":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts remove <fact_id>")
                return

            fact_id = sys.argv[3]
            print(json.dumps(api_facts_remove(fact_id), indent=2))

        elif subcmd == "search":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts search \"query\" [--user X]")
                return

            query = sys.argv[3]
            user_id = "david"
            limit = 10

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--user" and i + 1 < len(sys.argv):
                    user_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_facts_search(query, user_id, limit), indent=2))

        elif subcmd == "get":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py facts get <fact_id>")
                return

            fact_id = sys.argv[3]
            print(json.dumps(api_facts_get(fact_id), indent=2))

        else:
            print(f"Unknown facts subcommand: {subcmd}")
            print("Available: list, add, remove, search, get")

    # ============ Index Management CLI (Phase 2.2.10) ============
    elif cmd == "index":
        if len(sys.argv) < 3:
            print("Usage: sam_api.py index <subcommand> [options]")
            print()
            print("Subcommands:")
            print("  status                     - Show index statistics")
            print("  build [path] [--project X] [--force]  - Build/rebuild index")
            print("  search \"query\" [--project X] [--type X] [--limit N]")
            print("  watch [path] [--project X] - Start file watcher")
            print("  stop                       - Stop file watcher")
            print("  clear [--project X]        - Clear index (all or specific project)")
            print()
            print("Examples:")
            print("  sam_api.py index status")
            print("  sam_api.py index build ~/Projects/myapp --project myapp")
            print("  sam_api.py index search \"parse function\"")
            print("  sam_api.py index watch . --project current")
            print("  sam_api.py index clear --project myapp")
            return

        subcmd = sys.argv[2]

        if subcmd == "status":
            print(json.dumps(api_index_status(), indent=2))

        elif subcmd == "build":
            path = "."
            project_id = None
            force = False

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--force":
                    force = True
                    i += 1
                elif not sys.argv[i].startswith("-"):
                    path = sys.argv[i]
                    i += 1
                else:
                    i += 1

            print(json.dumps(api_index_build(path, project_id, force), indent=2))

        elif subcmd == "search":
            if len(sys.argv) < 4:
                print("Usage: sam_api.py index search \"query\" [--project X] [--type X] [--limit N]")
                return

            query = sys.argv[3]
            project_id = None
            entity_type = None
            limit = 10

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                    entity_type = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            print(json.dumps(api_code_search(query, project_id, entity_type, limit), indent=2))

        elif subcmd == "watch":
            path = "."
            project_id = None

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                elif not sys.argv[i].startswith("-"):
                    path = sys.argv[i]
                    i += 1
                else:
                    i += 1

            result = api_index_watch(path, project_id)
            print(json.dumps(result, indent=2))

            if result.get("success"):
                print("\nWatching for file changes. Press Ctrl+C to stop.")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    api_index_watch_stop()
                    print("\nWatcher stopped.")

        elif subcmd == "stop":
            print(json.dumps(api_index_watch_stop(), indent=2))

        elif subcmd == "clear":
            project_id = None

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                    project_id = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1

            if project_id is None:
                print("Warning: This will clear the ENTIRE code index.")
                confirm = input("Type 'yes' to confirm: ")
                if confirm.lower() != "yes":
                    print("Cancelled.")
                    return

            print(json.dumps(api_index_clear(project_id), indent=2))

        else:
            print(f"Unknown index subcommand: {subcmd}")
            print("Available: status, build, search, watch, stop, clear")

    elif cmd == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        run_server(port)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
