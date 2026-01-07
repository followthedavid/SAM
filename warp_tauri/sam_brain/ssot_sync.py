#!/usr/bin/env python3
"""
SAM SSOT Sync - Keep SAM's knowledge synced with the external SSOT.

The SSOT (Single Source of Truth) lives on /Volumes/Plex/SSOT and contains:
- Project inventories
- Session contexts
- Cross-LLM knowledge
- Exhaustive system documentation

This module keeps SAM in sync with that knowledge.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Paths
SSOT_PATH = Path("/Volumes/Plex/SSOT")
SAM_BRAIN = Path(__file__).parent
SYNC_STATE_FILE = SAM_BRAIN / ".ssot_sync_state.json"


@dataclass
class SyncState:
    last_sync: str
    file_hashes: Dict[str, str]
    imported_files: List[str]


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
        print("SAM SSOT Sync")
        print("-" * 40)
        status = ssot.status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("\nCommands: sync, status, export, files")
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

    else:
        print(f"Unknown command: {cmd}")
