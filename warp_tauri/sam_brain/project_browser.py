#!/usr/bin/env python3
"""
SAM Project Browser - Interactive decision-making for 2,000+ projects.

Usage:
  python project_browser.py                    # Interactive mode
  python project_browser.py list <category>   # List projects in category
  python project_browser.py search <query>    # Search all projects
  python project_browser.py review <path>     # Deep review a project
  python project_browser.py decide <path>     # Mark decision for project
  python project_browser.py summary           # Show decisions made
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
INVENTORY_FILE = SCRIPT_DIR / "exhaustive_analysis" / "master_inventory.json"
DECISIONS_FILE = SCRIPT_DIR / "project_decisions.json"

# Decision options
DECISIONS = {
    "integrate": "Integrate into SAM as module",
    "orchestrate": "SAM orchestrates (separate project)",
    "standalone": "Keep standalone, SAM calls API",
    "archive": "Archive - valuable but not needed now",
    "delete": "Safe to delete - duplicate/outdated",
    "review": "Needs deeper review",
    "skip": "Skip - vendor/node_modules/etc",
}

class ProjectBrowser:
    def __init__(self):
        self.inventory = json.load(open(INVENTORY_FILE))
        self.projects = self.inventory["projects"]
        self.decisions = self._load_decisions()
    
    def _load_decisions(self):
        if DECISIONS_FILE.exists():
            return json.load(open(DECISIONS_FILE))
        return {"decisions": {}, "updated_at": ""}
    
    def _save_decisions(self):
        self.decisions["updated_at"] = datetime.now().isoformat()
        json.dump(self.decisions, open(DECISIONS_FILE, "w"), indent=2)
    
    def categorize(self):
        """Return projects by category."""
        categories = defaultdict(list)
        PURPOSE_PATTERNS = {
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
            "rust": ["rust", "cargo"],
            "automation": ["script", "pipeline", "workflow"],
            "vendor": ["node_modules", "vendor", "packages"],
            "templates": ["template", "theme", "starter"],
        }
        
        for path, data in self.projects.items():
            name = data.get("name", "").lower()
            path_lower = path.lower()
            
            matched = False
            for cat, keywords in PURPOSE_PATTERNS.items():
                if any(kw in name or kw in path_lower for kw in keywords):
                    categories[cat].append((path, data))
                    matched = True
                    break
            
            if not matched:
                categories["other"].append((path, data))
        
        return categories
    
    def list_category(self, category):
        """List all projects in a category."""
        categories = self.categorize()
        if category not in categories:
            print(f"Unknown category: {category}")
            print(f"Available: {', '.join(categories.keys())}")
            return
        
        projs = categories[category]
        projs.sort(key=lambda x: -x[1].get("total_lines", 0))
        
        print(f"\n{'='*80}")
        print(f"📂 {category.upper()} ({len(projs)} projects)")
        print("="*80)
        
        for path, data in projs:
            name = data.get("name", "")[:35]
            lines = data.get("total_lines", 0)
            status = data.get("status", "?")
            decision = self.decisions["decisions"].get(path, {}).get("decision", "")
            dec_icon = "✓" if decision else " "
            status_icon = {"active": "🟢", "recent": "🟡", "stale": "🟠", "abandoned": "🔴"}.get(status, "⚪")
            
            print(f"{dec_icon} {status_icon} {name:35} | {lines:>7} lines | {path[:40]}")
    
    def search(self, query):
        """Search projects by name, path, or description."""
        query = query.lower()
        results = []
        
        for path, data in self.projects.items():
            name = data.get("name", "").lower()
            desc = data.get("description", "").lower()
            
            if query in name or query in path.lower() or query in desc:
                results.append((path, data))
        
        results.sort(key=lambda x: -x[1].get("total_lines", 0))
        
        print(f"\n{'='*80}")
        print(f"🔍 Search: '{query}' ({len(results)} results)")
        print("="*80)
        
        for path, data in results[:30]:
            name = data.get("name", "")[:30]
            lines = data.get("total_lines", 0)
            status = data.get("status", "?")
            desc = data.get("description", "")[:40]
            print(f"  {name:30} | {lines:>6} lines | {status:10} | {desc}")
            print(f"    {path}")
    
    def review(self, path):
        """Deep review of a specific project."""
        if path not in self.projects:
            # Try to find by name
            for p, d in self.projects.items():
                if d.get("name", "").lower() == path.lower():
                    path = p
                    break
        
        if path not in self.projects:
            print(f"Project not found: {path}")
            return
        
        data = self.projects[path]
        
        print(f"\n{'='*80}")
        print(f"📋 PROJECT REVIEW: {data.get('name', '')}")
        print("="*80)
        print(f"Path: {path}")
        print(f"Type: {data.get('project_type', 'unknown')}")
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Complexity: {data.get('complexity', 'unknown')}")
        print(f"Languages: {', '.join(data.get('languages', []))}")
        print(f"Frameworks: {', '.join(data.get('frameworks', []))}")
        print(f"Code Files: {data.get('code_files', 0)}")
        print(f"Lines: {data.get('total_lines', 0):,}")
        print(f"Days Since Modified: {data.get('days_since_modified', 0)}")
        print()
        print(f"Has README: {data.get('has_readme', False)}")
        print(f"Has Tests: {data.get('has_tests', False)}")
        print(f"Has CI/CD: {data.get('has_ci', False)}")
        print(f"Has Docker: {data.get('has_docker', False)}")
        print()
        if data.get("description"):
            print(f"Description: {data['description']}")
        if data.get("purpose"):
            print(f"Purpose: {data['purpose']}")
        print(f"Tags: {', '.join(data.get('tags', []))}")
        
        # Show current decision if any
        if path in self.decisions["decisions"]:
            dec = self.decisions["decisions"][path]
            print(f"\n📌 Current Decision: {dec['decision']} ({dec.get('note', '')})")
    
    def decide(self, path, decision, note=""):
        """Record a decision for a project."""
        if decision not in DECISIONS:
            print(f"Invalid decision: {decision}")
            print(f"Valid options: {', '.join(DECISIONS.keys())}")
            return
        
        self.decisions["decisions"][path] = {
            "decision": decision,
            "description": DECISIONS[decision],
            "note": note,
            "decided_at": datetime.now().isoformat()
        }
        self._save_decisions()
        print(f"✓ Recorded: {path} -> {decision}")
    
    def summary(self):
        """Show summary of decisions made."""
        print(f"\n{'='*80}")
        print("📊 DECISION SUMMARY")
        print("="*80)
        
        by_decision = defaultdict(list)
        for path, dec in self.decisions["decisions"].items():
            by_decision[dec["decision"]].append(path)
        
        total = len(self.decisions["decisions"])
        remaining = len(self.projects) - total
        
        print(f"\nDecisions made: {total}")
        print(f"Remaining: {remaining}")
        print()
        
        for dec, paths in sorted(by_decision.items()):
            print(f"{dec}: {len(paths)}")
            for p in paths[:3]:
                name = self.projects.get(p, {}).get("name", Path(p).name)
                print(f"  - {name}")
            if len(paths) > 3:
                print(f"  ... and {len(paths) - 3} more")
    
    def interactive(self):
        """Interactive mode."""
        print("\n" + "="*80)
        print("🔍 SAM Project Browser - Interactive Mode")
        print("="*80)
        print("\nCommands:")
        print("  categories        - List all categories")
        print("  list <category>   - List projects in category")
        print("  search <query>    - Search projects")
        print("  review <path>     - Deep review project")
        print("  decide <path> <decision> [note] - Record decision")
        print("  summary           - Show decisions made")
        print("  quit              - Exit")
        print(f"\nDecision options: {', '.join(DECISIONS.keys())}")


def main():
    browser = ProjectBrowser()
    
    if len(sys.argv) < 2:
        browser.interactive()
        return
    
    cmd = sys.argv[1]
    
    if cmd == "categories":
        cats = browser.categorize()
        for cat, projs in sorted(cats.items(), key=lambda x: -len(x[1])):
            print(f"  {cat:20}: {len(projs):4} projects")
    
    elif cmd == "list" and len(sys.argv) > 2:
        browser.list_category(sys.argv[2])
    
    elif cmd == "search" and len(sys.argv) > 2:
        browser.search(" ".join(sys.argv[2:]))
    
    elif cmd == "review" and len(sys.argv) > 2:
        browser.review(sys.argv[2])
    
    elif cmd == "decide" and len(sys.argv) > 3:
        path = sys.argv[2]
        decision = sys.argv[3]
        note = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        browser.decide(path, decision, note)
    
    elif cmd == "summary":
        browser.summary()
    
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
