#!/usr/bin/env python3
"""
SAM Project Favorites - Manage starred/favorite projects and quick access.

Features:
- Star/unstar projects
- Quick jump to favorites
- Project notes and tags
- Recent projects tracking
- Project health status
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

SCRIPT_DIR = Path(__file__).parent
FAVORITES_FILE = SCRIPT_DIR / "project_favorites.json"
PROJECTS_FILE = SCRIPT_DIR / "projects.json"
DISCOVERED_FILE = SCRIPT_DIR / "projects_discovered.json"


@dataclass
class FavoriteProject:
    path: str
    name: str
    starred: bool = True
    pinned: bool = False  # Show at top
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    last_accessed: str = ""
    access_count: int = 0
    added_at: str = ""
    color: str = ""  # For UI display


@dataclass
class ProjectFavorites:
    favorites: Dict[str, FavoriteProject] = field(default_factory=dict)
    recent: List[str] = field(default_factory=list)  # paths
    max_recent: int = 20
    updated_at: str = ""


class FavoritesManager:
    def __init__(self):
        self.data = self._load()

    def _load(self) -> ProjectFavorites:
        """Load favorites data."""
        if FAVORITES_FILE.exists():
            raw = json.load(open(FAVORITES_FILE))
            favorites = {}
            for path, fav_data in raw.get("favorites", {}).items():
                favorites[path] = FavoriteProject(**fav_data)
            return ProjectFavorites(
                favorites=favorites,
                recent=raw.get("recent", []),
                max_recent=raw.get("max_recent", 20),
                updated_at=raw.get("updated_at", "")
            )
        return ProjectFavorites()

    def _save(self):
        """Save favorites data."""
        data = {
            "favorites": {p: asdict(f) for p, f in self.data.favorites.items()},
            "recent": self.data.recent,
            "max_recent": self.data.max_recent,
            "updated_at": datetime.now().isoformat()
        }
        json.dump(data, open(FAVORITES_FILE, "w"), indent=2)

    def _get_project_info(self, path: str) -> Optional[Dict]:
        """Get project info from discovered projects."""
        if DISCOVERED_FILE.exists():
            discovered = json.load(open(DISCOVERED_FILE))
            for p in discovered.get("projects", []):
                if p["path"] == path:
                    return p
        return None

    def star(self, path: str, name: str = None) -> FavoriteProject:
        """Star a project."""
        if path in self.data.favorites:
            self.data.favorites[path].starred = True
        else:
            # Get info
            info = self._get_project_info(path)
            if not name and info:
                name = info.get("name", Path(path).name)
            elif not name:
                name = Path(path).name

            self.data.favorites[path] = FavoriteProject(
                path=path,
                name=name,
                starred=True,
                added_at=datetime.now().isoformat()
            )

        self._save()
        return self.data.favorites[path]

    def unstar(self, path: str):
        """Unstar a project."""
        if path in self.data.favorites:
            self.data.favorites[path].starred = False
            self._save()

    def pin(self, path: str):
        """Pin a project to top."""
        if path in self.data.favorites:
            self.data.favorites[path].pinned = True
            self._save()
        else:
            fav = self.star(path)
            fav.pinned = True
            self._save()

    def unpin(self, path: str):
        """Unpin a project."""
        if path in self.data.favorites:
            self.data.favorites[path].pinned = False
            self._save()

    def add_tag(self, path: str, tag: str):
        """Add a tag to a project."""
        if path not in self.data.favorites:
            self.star(path)
        if tag not in self.data.favorites[path].tags:
            self.data.favorites[path].tags.append(tag)
            self._save()

    def remove_tag(self, path: str, tag: str):
        """Remove a tag from a project."""
        if path in self.data.favorites:
            if tag in self.data.favorites[path].tags:
                self.data.favorites[path].tags.remove(tag)
                self._save()

    def set_note(self, path: str, note: str):
        """Set note for a project."""
        if path not in self.data.favorites:
            self.star(path)
        self.data.favorites[path].notes = note
        self._save()

    def set_color(self, path: str, color: str):
        """Set display color for a project."""
        if path not in self.data.favorites:
            self.star(path)
        self.data.favorites[path].color = color
        self._save()

    def access(self, path: str):
        """Record project access."""
        # Update access stats
        if path in self.data.favorites:
            self.data.favorites[path].access_count += 1
            self.data.favorites[path].last_accessed = datetime.now().isoformat()

        # Update recent list
        if path in self.data.recent:
            self.data.recent.remove(path)
        self.data.recent.insert(0, path)
        self.data.recent = self.data.recent[:self.data.max_recent]

        self._save()

    def get_starred(self) -> List[FavoriteProject]:
        """Get all starred projects."""
        return [f for f in self.data.favorites.values() if f.starred]

    def get_pinned(self) -> List[FavoriteProject]:
        """Get pinned projects."""
        return [f for f in self.data.favorites.values() if f.pinned]

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recently accessed projects."""
        results = []
        for path in self.data.recent[:limit]:
            if path in self.data.favorites:
                results.append(asdict(self.data.favorites[path]))
            else:
                info = self._get_project_info(path)
                if info:
                    results.append(info)
        return results

    def get_by_tag(self, tag: str) -> List[FavoriteProject]:
        """Get projects by tag."""
        return [f for f in self.data.favorites.values() if tag in f.tags]

    def search(self, query: str) -> List[FavoriteProject]:
        """Search favorites."""
        query = query.lower()
        results = []
        for fav in self.data.favorites.values():
            if (query in fav.name.lower() or
                query in fav.path.lower() or
                query in fav.notes.lower() or
                any(query in t.lower() for t in fav.tags)):
                results.append(fav)
        return results

    def all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        for fav in self.data.favorites.values():
            tags.update(fav.tags)
        return sorted(tags)

    def stats(self) -> Dict:
        """Get favorites statistics."""
        return {
            "total_favorites": len(self.data.favorites),
            "starred": len(self.get_starred()),
            "pinned": len(self.get_pinned()),
            "recent_count": len(self.data.recent),
            "tags": self.all_tags(),
            "most_accessed": sorted(
                self.data.favorites.values(),
                key=lambda f: f.access_count,
                reverse=True
            )[:5]
        }

    def export_active(self) -> int:
        """Export starred/pinned to main projects.json."""
        active = [f for f in self.data.favorites.values() if f.starred or f.pinned]

        # Load existing projects
        if PROJECTS_FILE.exists():
            existing = json.load(open(PROJECTS_FILE))
        else:
            existing = {"projects": []}

        # Get existing paths
        existing_paths = {p["path"] for p in existing["projects"]}

        # Add favorites not already in projects
        added = 0
        for fav in active:
            if fav.path not in existing_paths:
                info = self._get_project_info(fav.path) or {}
                existing["projects"].append({
                    "name": fav.name,
                    "path": fav.path,
                    "type": info.get("types", ["unknown"])[0] if info.get("types") else "unknown",
                    "description": fav.notes or info.get("description", ""),
                    "keywords": fav.tags + info.get("keywords", []),
                    "favorite": True
                })
                added += 1

        existing["updated_at"] = datetime.now().isoformat()
        json.dump(existing, open(PROJECTS_FILE, "w"), indent=2)

        return added


def main():
    import sys

    manager = FavoritesManager()

    if len(sys.argv) < 2:
        print("SAM Project Favorites")
        print("-" * 40)
        stats = manager.stats()
        print(f"  Starred: {stats['starred']}")
        print(f"  Pinned: {stats['pinned']}")
        print(f"  Tags: {', '.join(stats['tags'][:10])}")
        print("\nCommands: star <path>, unstar <path>, pin <path>, tag <path> <tag>")
        print("          list, recent, search <query>, export")
        return

    cmd = sys.argv[1]

    if cmd == "star" and len(sys.argv) > 2:
        path = sys.argv[2]
        fav = manager.star(path)
        print(f"⭐ Starred: {fav.name}")

    elif cmd == "unstar" and len(sys.argv) > 2:
        manager.unstar(sys.argv[2])
        print("Unstarred")

    elif cmd == "pin" and len(sys.argv) > 2:
        manager.pin(sys.argv[2])
        print("📌 Pinned")

    elif cmd == "tag" and len(sys.argv) > 3:
        manager.add_tag(sys.argv[2], sys.argv[3])
        print(f"Tagged with: {sys.argv[3]}")

    elif cmd == "list":
        starred = manager.get_starred()
        print(f"Starred projects ({len(starred)}):")
        for fav in starred:
            pin = "📌" if fav.pinned else "  "
            tags = f" [{', '.join(fav.tags)}]" if fav.tags else ""
            print(f"  {pin} ⭐ {fav.name}{tags}")
            print(f"      {fav.path}")

    elif cmd == "recent":
        recent = manager.get_recent()
        print("Recent projects:")
        for r in recent:
            name = r.get("name", Path(r.get("path", "")).name)
            print(f"  {name}: {r.get('path', '')}")

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = manager.search(query)
        print(f"Search results for '{query}':")
        for fav in results:
            print(f"  {fav.name}: {fav.path}")

    elif cmd == "export":
        added = manager.export_active()
        print(f"Exported {added} projects to projects.json")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
