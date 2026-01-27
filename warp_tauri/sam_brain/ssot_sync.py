#!/usr/bin/env python3
"""
SAM SSOT Sync - Bidirectional sync between Evolution Tracker and SSOT Documentation

The SSOT (Single Source of Truth) lives on /Volumes/Plex/SSOT and contains:
- Project inventories and documentation
- Session contexts
- Cross-LLM knowledge
- Exhaustive system documentation
- Progress timelines (auto-generated)

This module keeps SAM and the Evolution Tracker in sync with SSOT:
- Reads project state from SSOT docs
- Writes progress updates back to docs
- Maintains "Progress Timeline" sections in project files
- Updates PROJECT_OVERLAPS.md with integration status
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Paths
SSOT_PATH = Path("/Volumes/Plex/SSOT")
SAM_BRAIN = Path(__file__).parent
SYNC_STATE_FILE = SAM_BRAIN / ".ssot_sync_state.json"


@dataclass
class SyncState:
    last_sync: str
    file_hashes: Dict[str, str]
    imported_files: List[str]


@dataclass
class ProjectDocInfo:
    """Information parsed from a project's SSOT doc"""
    id: str
    name: str
    category: str
    current_progress: float
    status: str
    file_path: Path
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=list)


# Additional paths for projects
PROJECTS_DIR = SSOT_PATH / "projects"
OVERLAPS_FILE = SSOT_PATH / "PROJECT_OVERLAPS.md"


class SSOTSync:
    def __init__(self):
        self.ssot_available = SSOT_PATH.exists()
        self.state = self._load_state()

    def _load_state(self) -> SyncState:
        """Load sync state."""
        if SYNC_STATE_FILE.exists():
            data = json.load(open(SYNC_STATE_FILE))
            return SyncState(**data)
        return SyncState(
            last_sync="never",
            file_hashes={},
            imported_files=[]
        )

    def _save_state(self):
        """Save sync state."""
        json.dump({
            "last_sync": self.state.last_sync,
            "file_hashes": self.state.file_hashes,
            "imported_files": self.state.imported_files
        }, open(SYNC_STATE_FILE, "w"), indent=2)

    def _file_hash(self, path: Path) -> str:
        """Get hash of file contents."""
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _file_changed(self, path: Path) -> bool:
        """Check if file has changed since last sync."""
        current_hash = self._file_hash(path)
        stored_hash = self.state.file_hashes.get(str(path))
        return current_hash != stored_hash

    def check_ssot_available(self) -> bool:
        """Check if SSOT drive is mounted."""
        self.ssot_available = SSOT_PATH.exists()
        return self.ssot_available

    def get_ssot_files(self) -> List[Path]:
        """List important SSOT files."""
        if not self.ssot_available:
            return []

        important_patterns = [
            "*.md",
            "*.json",
            "context/*.md",
            "exhaustive/*.md",
        ]

        files = []
        for pattern in important_patterns:
            files.extend(SSOT_PATH.glob(pattern))

        return sorted(files)

    def import_project_inventory(self) -> int:
        """Import project inventory from SSOT."""
        inventory_file = SSOT_PATH / "drive_code_discovery.md"
        if not inventory_file.exists():
            return 0

        # Parse the markdown to extract projects
        content = inventory_file.read_text()

        # For now, just note that we've synced it
        self.state.file_hashes[str(inventory_file)] = self._file_hash(inventory_file)
        self._save_state()

        return 1

    def import_context(self, context_file: Path) -> Dict:
        """Import a context file from SSOT."""
        if not context_file.exists():
            return {}

        content = context_file.read_text()

        # Update hash
        self.state.file_hashes[str(context_file)] = self._file_hash(context_file)

        return {
            "file": str(context_file),
            "content": content,
            "imported_at": datetime.now().isoformat()
        }

    def export_sam_state(self) -> bool:
        """Export SAM's current state to SSOT."""
        if not self.ssot_available:
            return False

        sam_export_dir = SSOT_PATH / "sam_brain_export"
        sam_export_dir.mkdir(exist_ok=True)

        # Export projects
        projects_file = SAM_BRAIN / "projects.json"
        if projects_file.exists():
            import shutil
            shutil.copy(projects_file, sam_export_dir / "projects.json")

        # Export memory summary
        memory_file = SAM_BRAIN / "memory.json"
        if memory_file.exists():
            memory = json.load(open(memory_file))
            summary = {
                "total_interactions": len(memory.get("interactions", [])),
                "last_updated": datetime.now().isoformat(),
                "recent_queries": [
                    i.get("query", "")[:100]
                    for i in memory.get("interactions", [])[-10:]
                ]
            }
            json.dump(summary, open(sam_export_dir / "memory_summary.json", "w"), indent=2)

        # Export stats
        stats_file = SAM_BRAIN / "stats.json"
        if stats_file.exists():
            import shutil
            shutil.copy(stats_file, sam_export_dir / "stats.json")

        return True

    def get_relevant_context(self, query: str) -> str:
        """Get relevant context from SSOT for a query."""
        if not self.ssot_available:
            return ""

        # Check exhaustive context
        exhaustive_dir = SSOT_PATH / "exhaustive"
        if exhaustive_dir.exists():
            full_context = exhaustive_dir / "full_context.md"
            if full_context.exists():
                content = full_context.read_text()
                # Return first section if query matches
                query_lower = query.lower()
                if any(term in content.lower() for term in query_lower.split()):
                    return content[:2000]

        # Check context files
        context_dir = SSOT_PATH / "context"
        if context_dir.exists():
            for ctx_file in context_dir.glob("*.md"):
                if query.lower() in ctx_file.stem.lower():
                    return ctx_file.read_text()[:2000]

        return ""

    def sync(self) -> Dict:
        """Full sync with SSOT."""
        if not self.check_ssot_available():
            return {"status": "error", "message": "SSOT not available"}

        results = {
            "status": "success",
            "imported": [],
            "exported": False,
            "timestamp": datetime.now().isoformat()
        }

        # Import project inventory
        if self.import_project_inventory():
            results["imported"].append("project_inventory")

        # Import any changed context files
        context_dir = SSOT_PATH / "context"
        if context_dir.exists():
            for ctx_file in context_dir.glob("*.md"):
                if self._file_changed(ctx_file):
                    self.import_context(ctx_file)
                    results["imported"].append(ctx_file.name)

        # Export SAM state
        results["exported"] = self.export_sam_state()

        # Update sync time
        self.state.last_sync = datetime.now().isoformat()
        self._save_state()

        return results

    def status(self) -> Dict:
        """Get sync status."""
        return {
            "ssot_available": self.check_ssot_available(),
            "ssot_path": str(SSOT_PATH),
            "last_sync": self.state.last_sync,
            "synced_files": len(self.state.file_hashes),
            "ssot_files": len(self.get_ssot_files()) if self.ssot_available else 0
        }

    # ===== Evolution Tracker Integration =====

    def _get_tracker(self):
        """Lazy load evolution tracker"""
        try:
            from evolution_tracker import EvolutionTracker
            return EvolutionTracker()
        except ImportError:
            return None

    def discover_project_docs(self) -> List[Path]:
        """Find all project documentation files in SSOT"""
        if not self.ssot_available:
            return []

        project_files = []

        # Look in projects directory
        if PROJECTS_DIR.exists():
            project_files.extend(PROJECTS_DIR.glob("*.md"))

        # Also check for project docs in root
        root_project_patterns = ["SAM_*.md", "*_PROJECT.md", "PROJECT_*.md"]
        for pattern in root_project_patterns:
            project_files.extend(SSOT_PATH.glob(pattern))

        return sorted(set(project_files))

    def parse_project_doc(self, filepath: Path) -> Optional[ProjectDocInfo]:
        """Parse a project markdown file for key information"""
        try:
            content = filepath.read_text()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

        # Extract project name from title (first # heading)
        name_match = re.search(r'^#\s+(.+?)(?:\n|$)', content, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else filepath.stem

        # Generate ID from filename
        project_id = filepath.stem.upper().replace(" ", "_").replace("-", "_")

        # Detect category
        category = self._detect_category(content, name)

        # Extract progress and status
        progress = self._extract_progress(content)
        status = self._extract_status(content)

        # Extract description (first paragraph after title)
        desc_match = re.search(r'^#\s+.+?\n\n(.+?)(?:\n\n|\n#)', content, re.MULTILINE | re.DOTALL)
        description = desc_match.group(1).strip()[:500] if desc_match else ""

        return ProjectDocInfo(
            id=project_id,
            name=name,
            category=category,
            current_progress=progress,
            status=status,
            file_path=filepath,
            description=description,
            dependencies=self._extract_dependencies(content),
            integrations=self._extract_integrations(content)
        )

    def _detect_category(self, content: str, name: str) -> str:
        """Detect project category from content and name"""
        content_lower = content.lower()
        name_lower = name.lower()

        # SAM's own systems get 'sam' category
        if "sam_brain" in name_lower or "sam brain" in name_lower:
            return "sam"
        if "orchestrat" in name_lower:
            return "brain"

        category_keywords = {
            "sam": ["self-improvement", "sam's evolution", "core system"],
            "brain": ["routing", "orchestrat", "model selection", "ai backend"],
            "visual": ["image", "comfyui", "stable diffusion", "lora", "visual"],
            "voice": ["voice", "tts", "speech", "rvc", "audio"],
            "content": ["content", "media", "video", "animation", "creative"],
            "platform": ["platform", "infrastructure", "server", "deployment", "api"],
        }

        for cat, keywords in category_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return cat

        return "platform"

    def _extract_progress(self, content: str) -> float:
        """Extract progress percentage from document"""
        patterns = [
            r'progress[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s+complete',
            r'completion[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'\|\s*Progress\s*\|\s*(\d+(?:\.\d+)?)\s*%',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return float(match.group(1)) / 100.0

        status = self._extract_status(content)
        status_progress = {
            "not_started": 0.0, "planning": 0.1, "in_progress": 0.5,
            "testing": 0.8, "completed": 1.0, "maintenance": 1.0,
        }
        return status_progress.get(status, 0.3)

    def _extract_status(self, content: str) -> str:
        """Extract project status from document"""
        patterns = [
            r'status[:\s]+(\w+)',
            r'\|\s*Status\s*\|\s*(\w+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                status = match.group(1).lower()
                if "progress" in status or "active" in status:
                    return "in_progress"
                elif "complete" in status or "done" in status:
                    return "completed"
                elif "plan" in status:
                    return "planning"
                return status

        return "in_progress"

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract project dependencies from document"""
        dep_section = re.search(
            r'##?\s*Dependencies\s*\n(.*?)(?=\n##|\n#|\Z)',
            content, re.IGNORECASE | re.DOTALL
        )
        if dep_section:
            return re.findall(r'[-*]\s+(.+?)(?:\n|$)', dep_section.group(1))
        return []

    def _extract_integrations(self, content: str) -> List[str]:
        """Extract integrations from document"""
        int_section = re.search(
            r'##?\s*Integrations?\s*\n(.*?)(?=\n##|\n#|\Z)',
            content, re.IGNORECASE | re.DOTALL
        )
        if int_section:
            return re.findall(r'[-*]\s+(.+?)(?:\n|$)', int_section.group(1))
        return []

    def sync_from_ssot_to_tracker(self) -> Dict[str, Any]:
        """Read all SSOT docs and update evolution tracker"""
        tracker = self._get_tracker()
        if not tracker:
            return {"success": False, "error": "Evolution tracker not available"}

        project_docs = self.discover_project_docs()
        synced = 0
        errors = []

        for doc_path in project_docs:
            info = self.parse_project_doc(doc_path)
            if info:
                try:
                    tracker.add_or_update_project(
                        project_id=info.id,
                        name=info.name,
                        category=info.category,
                        current_progress=info.current_progress,
                        ssot_path=str(info.file_path)
                    )
                    synced += 1
                except Exception as e:
                    errors.append(f"{info.id}: {e}")

        return {"success": True, "synced": synced, "total_docs": len(project_docs), "errors": errors}

    def sync_from_tracker_to_ssot(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Update SSOT docs with progress from evolution tracker"""
        tracker = self._get_tracker()
        if not tracker:
            return {"success": False, "error": "Evolution tracker not available"}

        if project_id:
            projects = [tracker.get_project(project_id)]
            projects = [p for p in projects if p]
        else:
            projects = tracker.get_all_projects()

        updated = 0
        errors = []

        for project in projects:
            if not hasattr(project, 'ssot_path') or not project.ssot_path:
                continue
            if not Path(project.ssot_path).exists():
                continue

            try:
                self._update_project_doc_with_progress(project, tracker)
                updated += 1
            except Exception as e:
                errors.append(f"{project.id}: {e}")

        return {"success": True, "updated": updated, "total_projects": len(projects), "errors": errors}

    def _update_project_doc_with_progress(self, project, tracker) -> None:
        """Update a single project's SSOT doc with progress timeline"""
        filepath = Path(project.ssot_path)
        content = filepath.read_text()

        # Get progress history from tracker
        history = tracker.get_progress_history(project.id) if hasattr(tracker, 'get_progress_history') else []

        # Format progress timeline
        timeline_section = self._format_progress_timeline(project, history)

        # Check if Progress Timeline section exists
        timeline_pattern = r'(##?\s*Progress Timeline\s*\n)(.*?)(?=\n##|\n#|\Z)'
        match = re.search(timeline_pattern, content, re.IGNORECASE | re.DOTALL)

        if match:
            new_content = content[:match.start()] + timeline_section + content[match.end():]
        else:
            # Add before ## References or at end
            ref_match = re.search(r'\n##?\s*References', content, re.IGNORECASE)
            if ref_match:
                new_content = content[:ref_match.start()] + "\n" + timeline_section + content[ref_match.start():]
            else:
                new_content = content.rstrip() + "\n\n" + timeline_section

        filepath.write_text(new_content)

    def _format_progress_timeline(self, project, history: list) -> str:
        """Format progress history as markdown timeline"""
        lines = ["## Progress Timeline\n"]
        lines.append(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        progress_val = project.current_progress if hasattr(project, 'current_progress') else 0
        lines.append(f"**Current Progress:** {progress_val * 100:.0f}%\n")

        if history:
            lines.append("\n| Date | Progress | Milestone |")
            lines.append("|------|----------|-----------|")

            for entry in history[-10:]:
                date = entry.recorded_at[:10] if hasattr(entry, 'recorded_at') else "Unknown"
                progress = f"{entry.progress * 100:.0f}%" if hasattr(entry, 'progress') else "?"
                milestone = getattr(entry, 'milestone', None) or "-"
                lines.append(f"| {date} | {progress} | {milestone} |")
        else:
            lines.append("\n*No progress history recorded yet.*")

        lines.append("\n")
        return "\n".join(lines)

    def update_project_overlaps(self) -> Dict[str, Any]:
        """Update PROJECT_OVERLAPS.md with current integration status"""
        tracker = self._get_tracker()
        if not tracker:
            return {"success": False, "error": "Evolution tracker not available"}

        if not OVERLAPS_FILE.exists():
            return {"success": False, "error": f"Overlaps file not found: {OVERLAPS_FILE}"}

        # Get relationships if method exists
        if not hasattr(tracker, 'get_all_relationships'):
            return {"success": False, "error": "Tracker doesn't support relationships"}

        relationships = tracker.get_all_relationships()

        connected = [r for r in relationships if getattr(r, 'status', '') == "connected"]
        planned = [r for r in relationships if getattr(r, 'status', '') == "planned"]
        blocked = [r for r in relationships if getattr(r, 'status', '') == "blocked"]

        content = OVERLAPS_FILE.read_text()
        status_section = self._format_integration_status(connected, planned, blocked)

        status_pattern = r'(##?\s*Integration Status\s*\n)(.*?)(?=\n##|\n#|\Z)'
        match = re.search(status_pattern, content, re.IGNORECASE | re.DOTALL)

        if match:
            new_content = content[:match.start()] + status_section + content[match.end():]
        else:
            new_content = content.rstrip() + "\n\n" + status_section

        OVERLAPS_FILE.write_text(new_content)

        return {
            "success": True,
            "connected": len(connected),
            "planned": len(planned),
            "blocked": len(blocked)
        }

    def _format_integration_status(self, connected: list, planned: list, blocked: list) -> str:
        """Format integration status as markdown"""
        lines = ["## Integration Status\n"]
        lines.append(f"*Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        if connected:
            lines.append("\n### Connected")
            for r in connected:
                lines.append(f"- {r.source_project} ↔ {r.target_project} ({r.relationship_type})")

        if planned:
            lines.append("\n### Planned")
            for r in planned:
                lines.append(f"- {r.source_project} → {r.target_project} ({r.relationship_type})")

        if blocked:
            lines.append("\n### Blocked")
            for r in blocked:
                lines.append(f"- {r.source_project} ✗ {r.target_project} ({r.relationship_type})")

        if not connected and not planned and not blocked:
            lines.append("\n*No integration relationships tracked yet.*")

        lines.append("\n")
        return "\n".join(lines)

    def full_evolution_sync(self) -> Dict[str, Any]:
        """Perform full bidirectional sync between tracker and SSOT"""
        results = {
            "from_ssot": self.sync_from_ssot_to_tracker(),
            "to_ssot": self.sync_from_tracker_to_ssot(),
            "overlaps": self.update_project_overlaps(),
            "timestamp": datetime.now().isoformat()
        }

        results["success"] = all(
            r.get("success", False) for r in [
                results["from_ssot"],
                results["to_ssot"],
                results["overlaps"]
            ]
        )

        return results

    def get_evolution_sync_status(self) -> Dict[str, Any]:
        """Get current sync status between tracker and SSOT"""
        tracker = self._get_tracker()
        if not tracker:
            return {"synced": False, "error": "Tracker not available"}

        project_docs = self.discover_project_docs()
        db_projects = tracker.get_all_projects() if hasattr(tracker, 'get_all_projects') else []

        doc_ids = set()
        for p in project_docs:
            info = self.parse_project_doc(p)
            if info:
                doc_ids.add(info.id)

        db_ids = {p.id for p in db_projects}

        return {
            "synced": doc_ids == db_ids,
            "docs_only": list(doc_ids - db_ids),
            "db_only": list(db_ids - doc_ids),
            "both": list(doc_ids & db_ids),
            "total_docs": len(project_docs),
            "total_db": len(db_projects)
        }


# Global instance
_sync = None


def get_sync() -> SSOTSync:
    """Get global sync instance."""
    global _sync
    if _sync is None:
        _sync = SSOTSync()
    return _sync


def sync() -> Dict:
    """Run sync."""
    return get_sync().sync()


def get_context(query: str) -> str:
    """Get relevant context for a query."""
    return get_sync().get_relevant_context(query)


if __name__ == "__main__":
    import sys

    ssot = SSOTSync()

    if len(sys.argv) < 2:
        print("SAM SSOT Sync - Bidirectional sync with Evolution Tracker")
        print("-" * 55)
        status = ssot.status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("\nBasic Commands:")
        print("  sync          - Full sync with SSOT")
        print("  status        - Get sync status")
        print("  export        - Export SAM state to SSOT")
        print("  files         - List SSOT files")
        print("\nEvolution Tracker Commands:")
        print("  discover      - List discovered project docs")
        print("  from-ssot     - Sync from SSOT docs to tracker")
        print("  to-ssot       - Sync from tracker to SSOT docs")
        print("  overlaps      - Update PROJECT_OVERLAPS.md")
        print("  evolution     - Full bidirectional evolution sync")
        print("  evolution-status - Show evolution sync status")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "sync":
        result = ssot.sync()
        print(json.dumps(result, indent=2))

    elif cmd == "status":
        status = ssot.status()
        print(json.dumps(status, indent=2))

    elif cmd == "export":
        if ssot.export_sam_state():
            print("Exported SAM state to SSOT")
        else:
            print("Export failed (SSOT not available?)")

    elif cmd == "files":
        files = ssot.get_ssot_files()
        print(f"SSOT files ({len(files)}):")
        for f in files[:20]:
            print(f"  {f.name}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more")

    elif cmd == "discover":
        docs = ssot.discover_project_docs()
        print(f"Found {len(docs)} project documents:\n")
        for doc in docs:
            info = ssot.parse_project_doc(doc)
            if info:
                print(f"  {info.id}: {info.name} ({info.category}) - {info.current_progress*100:.0f}%")
            else:
                print(f"  {doc.name}: (parse error)")

    elif cmd == "from-ssot":
        result = ssot.sync_from_ssot_to_tracker()
        if result["success"]:
            print(f"Synced {result['synced']}/{result['total_docs']} projects from SSOT")
            if result.get("errors"):
                print(f"Errors: {result['errors']}")
        else:
            print(f"Sync failed: {result.get('error')}")

    elif cmd == "to-ssot":
        result = ssot.sync_from_tracker_to_ssot()
        if result["success"]:
            print(f"Updated {result['updated']}/{result['total_projects']} SSOT docs")
            if result.get("errors"):
                print(f"Errors: {result['errors']}")
        else:
            print(f"Sync failed: {result.get('error')}")

    elif cmd == "overlaps":
        result = ssot.update_project_overlaps()
        if result["success"]:
            print("Updated PROJECT_OVERLAPS.md")
            print(f"  Connected: {result['connected']}")
            print(f"  Planned: {result['planned']}")
            print(f"  Blocked: {result['blocked']}")
        else:
            print(f"Update failed: {result.get('error')}")

    elif cmd == "evolution":
        result = ssot.full_evolution_sync()
        print(f"Full evolution sync {'succeeded' if result['success'] else 'had errors'}")
        print(f"  From SSOT: {result['from_ssot'].get('synced', 0)} synced")
        print(f"  To SSOT: {result['to_ssot'].get('updated', 0)} updated")
        print(f"  Timestamp: {result['timestamp']}")

    elif cmd == "evolution-status":
        status = ssot.get_evolution_sync_status()
        if status.get("synced"):
            print("SSOT and tracker are in sync")
        else:
            print("SSOT and tracker are NOT in sync")
            if status.get("docs_only"):
                print(f"  Only in SSOT: {status['docs_only']}")
            if status.get("db_only"):
                print(f"  Only in tracker: {status['db_only']}")
        print(f"  Docs: {status.get('total_docs', 0)}, DB: {status.get('total_db', 0)}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
