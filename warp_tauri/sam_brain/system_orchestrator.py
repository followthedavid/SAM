#!/usr/bin/env python3
"""
SAM System Orchestrator - Control Everything

This gives SAM the ability to:
1. Manage all scrapers (start, stop, status, search)
2. Set up and control ARR stack (Radarr, Sonarr, Lidarr, Prowlarr)
3. Intelligent search with filtering (find the best, show only quality)
4. System-wide automation

Architecture:
  SAM says "Find me X" → Orchestrator searches all sources → Returns best

Usage:
    # CLI
    python3 system_orchestrator.py search "SwiftUI animations"
    python3 system_orchestrator.py scraper status
    python3 system_orchestrator.py arr setup

    # From SAM
    orchestrator.find("SwiftUI animations", quality_min=0.8)
    orchestrator.scraper.start("apple_dev")
    orchestrator.arr.add_movie("The Matrix")
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

# Paths
SAM_BRAIN = Path(__file__).parent
SCRAPERS_DIR = Path("/Users/davidquinton/ReverseLab/SAM/scrapers")
LOGS_DIR = Path("/Volumes/David External/sam_logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOGS_DIR / "orchestrator.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScraperConfig:
    name: str
    script: str
    db_path: str
    table: str
    search_column: str
    status_query: str
    priority: int = 2  # 1=critical, 2=high, 3=medium


SCRAPERS = {
    "apple_dev": ScraperConfig(
        name="Apple Developer",
        script="apple_dev_collector.py",
        db_path="/Volumes/David External/apple_dev_archive/apple_dev.db",
        table="docs",
        search_column="content",
        status_query="SELECT COUNT(*) FROM docs WHERE content IS NOT NULL",
        priority=1,
    ),
    "github_code": ScraperConfig(
        name="GitHub Code",
        script="apple_dev_collector.py",
        db_path="/Volumes/David External/apple_dev_archive/apple_dev.db",
        table="github_code",
        search_column="description",
        status_query="SELECT COUNT(*) FROM github_code",
        priority=1,
    ),
    "stackoverflow": ScraperConfig(
        name="StackOverflow",
        script="apple_dev_collector.py",
        db_path="/Volumes/David External/apple_dev_archive/apple_dev.db",
        table="stackoverflow",
        search_column="content",
        status_query="SELECT COUNT(*) FROM stackoverflow",
        priority=1,
    ),
    "nifty": ScraperConfig(
        name="Nifty Archive",
        script="nifty_ripper.py",
        db_path="/Volumes/David External/nifty_archive/nifty_index.db",
        table="stories",
        search_column="content",
        status_query="SELECT COUNT(*) FROM stories WHERE downloaded=1",
        priority=3,
    ),
    "ao3": ScraperConfig(
        name="AO3 Archive",
        script="ao3_ripper.py",
        db_path="/Volumes/David External/ao3_archive/ao3_index.db",
        table="works",
        search_column="content",
        status_query="SELECT COUNT(*) FROM works WHERE downloaded=1",
        priority=3,
    ),
    "firstview": ScraperConfig(
        name="FirstView Fashion",
        script="firstview_ripper.py",
        db_path="/Volumes/David External/firstview_archive/firstview_index.db",
        table="photos",
        search_column="description",
        status_query="SELECT COUNT(*) FROM photos WHERE downloaded=1",
        priority=4,
    ),
    "wwd": ScraperConfig(
        name="WWD",
        script="wwd_scraper.py",
        db_path="/Volumes/#1/wwd_archive/wwd_index.db",
        table="articles",
        search_column="content",
        status_query="SELECT COUNT(*) FROM articles WHERE downloaded=1",
        priority=4,
    ),
    "code_collection": ScraperConfig(
        name="Code Collection",
        script="parallel_code_scraper.py",
        db_path="/Volumes/David External/coding_training/code_collection.db",
        table="code_examples",
        search_column="code",
        status_query="SELECT COUNT(*) FROM code_examples",
        priority=1,
    ),
}


class ScraperManager:
    """Manage all scrapers from one place."""

    def __init__(self):
        self.scrapers = SCRAPERS
        self.running = {}  # pid -> scraper_name

    def status(self, name: str = None) -> Dict:
        """Get status of one or all scrapers."""
        if name:
            return self._get_scraper_status(name)

        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._get_scraper_status, n): n
                       for n in self.scrapers}
            for future in as_completed(futures):
                name = futures[future]
                results[name] = future.result()

        return results

    def _get_scraper_status(self, name: str) -> Dict:
        """Get status for a single scraper."""
        if name not in self.scrapers:
            return {"error": f"Unknown scraper: {name}"}

        config = self.scrapers[name]
        db_path = Path(config.db_path)

        status = {
            "name": config.name,
            "db_exists": db_path.exists(),
            "count": 0,
            "running": self._is_running(config.script),
            "priority": config.priority,
        }

        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute(config.status_query)
                status["count"] = c.fetchone()[0]
                conn.close()
            except Exception as e:
                status["error"] = str(e)

        return status

    def _is_running(self, script: str) -> bool:
        """Check if a scraper script is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", script],
                capture_output=True, text=True, timeout=5
            )
            return bool(result.stdout.strip())
        except:
            return False

    def start(self, name: str, args: List[str] = None) -> Dict:
        """Start a scraper."""
        if name not in self.scrapers:
            return {"error": f"Unknown scraper: {name}"}

        config = self.scrapers[name]
        script_path = SCRAPERS_DIR / config.script

        if not script_path.exists():
            return {"error": f"Script not found: {script_path}"}

        if self._is_running(config.script):
            return {"status": "already_running"}

        cmd = ["python3", str(script_path)]
        if args:
            cmd.extend(args)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self.running[process.pid] = name
            return {"status": "started", "pid": process.pid}
        except Exception as e:
            return {"error": str(e)}

    def stop(self, name: str) -> Dict:
        """Stop a scraper."""
        if name not in self.scrapers:
            return {"error": f"Unknown scraper: {name}"}

        config = self.scrapers[name]
        try:
            result = subprocess.run(
                ["pkill", "-f", config.script],
                capture_output=True, text=True, timeout=10
            )
            return {"status": "stopped"}
        except Exception as e:
            return {"error": str(e)}

    def search(self, query: str, scrapers: List[str] = None,
               limit: int = 20) -> List[Dict]:
        """Search across scrapers."""
        results = []
        search_in = scrapers or list(self.scrapers.keys())

        for name in search_in:
            if name not in self.scrapers:
                continue

            config = self.scrapers[name]
            db_path = Path(config.db_path)

            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()

                # Try FTS first, then LIKE
                try:
                    c.execute(f"""
                        SELECT rowid, {config.search_column}
                        FROM {config.table}
                        WHERE {config.table} MATCH ?
                        LIMIT ?
                    """, (query, limit))
                except:
                    c.execute(f"""
                        SELECT rowid, {config.search_column}
                        FROM {config.table}
                        WHERE {config.search_column} LIKE ?
                        LIMIT ?
                    """, (f"%{query}%", limit))

                for row in c.fetchall():
                    results.append({
                        "source": name,
                        "source_name": config.name,
                        "id": row[0],
                        "content": row[1][:500] if row[1] else "",
                        "priority": config.priority,
                    })

                conn.close()
            except Exception as e:
                logger.error(f"Search error in {name}: {e}")

        # Sort by priority then relevance
        results.sort(key=lambda x: x["priority"])
        return results[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# ARR STACK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ARRService:
    name: str
    port: int
    api_path: str
    content_type: str  # "movie", "series", "music", "indexer"
    docker_image: str


ARR_SERVICES = {
    "radarr": ARRService(
        name="Radarr",
        port=7878,
        api_path="/api/v3",
        content_type="movie",
        docker_image="linuxserver/radarr",
    ),
    "sonarr": ARRService(
        name="Sonarr",
        port=8989,
        api_path="/api/v3",
        content_type="series",
        docker_image="linuxserver/sonarr",
    ),
    "lidarr": ARRService(
        name="Lidarr",
        port=8686,
        api_path="/api/v1",
        content_type="music",
        docker_image="linuxserver/lidarr",
    ),
    "prowlarr": ARRService(
        name="Prowlarr",
        port=9696,
        api_path="/api/v1",
        content_type="indexer",
        docker_image="linuxserver/prowlarr",
    ),
    "bazarr": ARRService(
        name="Bazarr",
        port=6767,
        api_path="/api",
        content_type="subtitles",
        docker_image="linuxserver/bazarr",
    ),
}


class ARRManager:
    """Manage ARR stack (Radarr, Sonarr, Lidarr, etc.)."""

    def __init__(self):
        self.services = ARR_SERVICES
        self.config_dir = Path("/Volumes/David External/arr_config")
        self.api_keys = {}
        self._load_api_keys()

    def _load_api_keys(self):
        """Load API keys from config."""
        key_file = self.config_dir / "api_keys.json"
        if key_file.exists():
            with open(key_file) as f:
                self.api_keys = json.load(f)

    def status(self, service: str = None) -> Dict:
        """Check status of ARR services."""
        if service:
            return self._check_service(service)

        results = {}
        for name in self.services:
            results[name] = self._check_service(name)
        return results

    def _check_service(self, name: str) -> Dict:
        """Check if an ARR service is running."""
        if name not in self.services:
            return {"error": f"Unknown service: {name}"}

        svc = self.services[name]
        status = {
            "name": svc.name,
            "port": svc.port,
            "running": False,
            "docker": False,
            "version": None,
        }

        # Check if port is listening
        try:
            response = requests.get(
                f"http://localhost:{svc.port}/system/status",
                timeout=2
            )
            status["running"] = True
        except:
            pass

        # Check if docker container exists
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={name}"],
                capture_output=True, text=True, timeout=5
            )
            status["docker"] = bool(result.stdout.strip())
        except:
            pass

        return status

    def setup(self, service: str = None) -> Dict:
        """Set up ARR service(s)."""
        if service:
            return self._setup_service(service)

        results = {}
        for name in self.services:
            results[name] = self._setup_service(name)
        return results

    def _setup_service(self, name: str) -> Dict:
        """Set up a single ARR service."""
        if name not in self.services:
            return {"error": f"Unknown service: {name}"}

        svc = self.services[name]
        config_path = self.config_dir / name
        config_path.mkdir(parents=True, exist_ok=True)

        # Generate docker-compose entry
        compose = {
            "version": "3",
            "services": {
                name: {
                    "image": svc.docker_image,
                    "container_name": name,
                    "environment": [
                        "PUID=501",
                        "PGID=20",
                        "TZ=America/Los_Angeles",
                    ],
                    "volumes": [
                        f"{config_path}:/config",
                        "/Volumes:/volumes",
                    ],
                    "ports": [f"{svc.port}:{svc.port}"],
                    "restart": "unless-stopped",
                }
            }
        }

        compose_file = config_path / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            import yaml
            yaml.dump(compose, f, default_flow_style=False)

        return {
            "status": "configured",
            "config_path": str(config_path),
            "compose_file": str(compose_file),
            "start_command": f"docker-compose -f {compose_file} up -d",
        }

    def start(self, service: str) -> Dict:
        """Start an ARR service."""
        if service not in self.services:
            return {"error": f"Unknown service: {service}"}

        compose_file = self.config_dir / service / "docker-compose.yml"
        if not compose_file.exists():
            setup = self._setup_service(service)
            if "error" in setup:
                return setup

        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                capture_output=True, text=True, timeout=60
            )
            return {"status": "started", "output": result.stdout}
        except Exception as e:
            return {"error": str(e)}

    def stop(self, service: str) -> Dict:
        """Stop an ARR service."""
        try:
            result = subprocess.run(
                ["docker", "stop", service],
                capture_output=True, text=True, timeout=30
            )
            return {"status": "stopped"}
        except Exception as e:
            return {"error": str(e)}

    def search(self, query: str, service: str = None) -> List[Dict]:
        """Search for content across ARR services."""
        results = []
        search_services = [service] if service else ["radarr", "sonarr", "lidarr"]

        for svc_name in search_services:
            if svc_name not in self.services:
                continue

            svc = self.services[svc_name]
            api_key = self.api_keys.get(svc_name)

            if not api_key:
                continue

            try:
                response = requests.get(
                    f"http://localhost:{svc.port}{svc.api_path}/{svc.content_type}/lookup",
                    params={"term": query},
                    headers={"X-Api-Key": api_key},
                    timeout=10
                )

                if response.status_code == 200:
                    for item in response.json()[:10]:
                        results.append({
                            "service": svc_name,
                            "title": item.get("title", ""),
                            "year": item.get("year"),
                            "id": item.get("id"),
                        })
            except Exception as e:
                logger.error(f"ARR search error in {svc_name}: {e}")

        return results

    def add(self, service: str, title: str = None, imdb_id: str = None) -> Dict:
        """Add content to an ARR service."""
        if service not in self.services:
            return {"error": f"Unknown service: {service}"}

        svc = self.services[service]
        api_key = self.api_keys.get(service)

        if not api_key:
            return {"error": "No API key configured"}

        # First search for the item
        if title:
            results = self.search(title, service)
            if not results:
                return {"error": f"Not found: {title}"}
            item = results[0]
        elif imdb_id:
            # Look up by IMDB ID
            pass

        # Add to service
        # This would need service-specific implementation
        return {"status": "TODO: implement add"}


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENT SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

class IntelligentSearch:
    """Smart search that finds the best results across all sources."""

    def __init__(self):
        self.scraper_manager = ScraperManager()
        self.arr_manager = ARRManager()

    def find(self, query: str, sources: str = "all",
             quality_min: float = 0.5, limit: int = 10) -> List[Dict]:
        """
        Find content across all sources, return only the best.

        Args:
            query: What to search for
            sources: "all", "code", "creative", "media"
            quality_min: Minimum quality score (0-1)
            limit: Max results to return

        Returns:
            List of best results with quality scores
        """
        results = []

        # Determine which sources to search
        source_map = {
            "code": ["apple_dev", "github_code", "stackoverflow", "code_collection"],
            "creative": ["nifty", "ao3"],
            "media": ["radarr", "sonarr"],
            "fashion": ["firstview", "wwd"],
        }

        if sources == "all":
            scrapers = list(self.scraper_manager.scrapers.keys())
        else:
            scrapers = source_map.get(sources, [])

        # Search scrapers
        scraper_results = self.scraper_manager.search(query, scrapers, limit=50)

        for result in scraper_results:
            quality = self._score_quality(result, query)
            if quality >= quality_min:
                result["quality"] = quality
                results.append(result)

        # Sort by quality
        results.sort(key=lambda x: x.get("quality", 0), reverse=True)

        return results[:limit]

    def _score_quality(self, result: Dict, query: str) -> float:
        """Score the quality of a search result."""
        score = 0.5  # Base score

        content = result.get("content", "").lower()
        query_lower = query.lower()

        # Exact match bonus
        if query_lower in content:
            score += 0.2

        # Priority bonus (lower priority number = higher quality)
        priority = result.get("priority", 3)
        score += (5 - priority) * 0.05

        # Length bonus (more content = more informative)
        if len(content) > 200:
            score += 0.1
        if len(content) > 500:
            score += 0.1

        # Code content bonus
        if "```" in content or "def " in content or "func " in content:
            score += 0.1

        return min(1.0, score)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class SystemOrchestrator:
    """
    The main orchestrator that SAM uses to control everything.

    Example:
        orchestrator = SystemOrchestrator()
        results = orchestrator.find("SwiftUI state management")
        orchestrator.scraper.start("apple_dev")
        orchestrator.arr.add_movie("Inception")
    """

    def __init__(self):
        self.scraper = ScraperManager()
        self.arr = ARRManager()
        self.search = IntelligentSearch()

    def find(self, query: str, sources: str = "all",
             quality_min: float = 0.5, limit: int = 10) -> List[Dict]:
        """Find content with intelligent filtering."""
        return self.search.find(query, sources, quality_min, limit)

    def status(self) -> Dict:
        """Get full system status."""
        return {
            "scrapers": self.scraper.status(),
            "arr": self.arr.status(),
            "timestamp": datetime.now().isoformat(),
        }

    def start_all_scrapers(self, priority: int = None) -> Dict:
        """Start all scrapers (optionally filtered by priority)."""
        results = {}
        for name, config in self.scraper.scrapers.items():
            if priority is None or config.priority <= priority:
                results[name] = self.scraper.start(name)
        return results

    def search_code(self, query: str, limit: int = 10) -> List[Dict]:
        """Convenience method to search only code sources."""
        return self.find(query, sources="code", limit=limit)

    def search_creative(self, query: str, limit: int = 10) -> List[Dict]:
        """Convenience method to search creative content."""
        return self.find(query, sources="creative", limit=limit)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    orchestrator = SystemOrchestrator()
    cmd = sys.argv[1]

    if cmd == "status":
        status = orchestrator.status()
        print(json.dumps(status, indent=2, default=str))

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: system_orchestrator.py search QUERY [--source SOURCE]")
            sys.exit(1)

        query = sys.argv[2]
        source = "all"
        if "--source" in sys.argv:
            idx = sys.argv.index("--source")
            source = sys.argv[idx + 1]

        results = orchestrator.find(query, sources=source)

        print(f"\n🔍 Search Results for: {query}")
        print("=" * 60)
        for i, r in enumerate(results, 1):
            quality = r.get("quality", 0)
            bar = "█" * int(quality * 10) + "░" * (10 - int(quality * 10))
            print(f"\n{i}. [{bar}] {r['source_name']}")
            content = r.get("content", "")[:200]
            print(f"   {content}...")

    elif cmd == "scraper":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else "status"

        if subcmd == "status":
            status = orchestrator.scraper.status()
            print("\n📊 Scraper Status")
            print("=" * 60)
            for name, s in status.items():
                running = "✓ RUNNING" if s.get("running") else "○ stopped"
                count = s.get("count", 0)
                print(f"  {s.get('name', name):20} {running:12} {count:>10,} items")

        elif subcmd == "start":
            name = sys.argv[3] if len(sys.argv) > 3 else None
            if name:
                result = orchestrator.scraper.start(name)
            else:
                result = orchestrator.start_all_scrapers()
            print(json.dumps(result, indent=2))

        elif subcmd == "stop":
            name = sys.argv[3]
            result = orchestrator.scraper.stop(name)
            print(json.dumps(result, indent=2))

    elif cmd == "arr":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else "status"

        if subcmd == "status":
            status = orchestrator.arr.status()
            print("\n🎬 ARR Stack Status")
            print("=" * 60)
            for name, s in status.items():
                running = "✓ RUNNING" if s.get("running") else "○ stopped"
                docker = "🐳" if s.get("docker") else "  "
                print(f"  {s.get('name', name):12} {running:12} {docker} port {s.get('port')}")

        elif subcmd == "setup":
            service = sys.argv[3] if len(sys.argv) > 3 else None
            result = orchestrator.arr.setup(service)
            print(json.dumps(result, indent=2))

        elif subcmd == "search":
            query = sys.argv[3]
            results = orchestrator.arr.search(query)
            for r in results:
                print(f"  [{r['service']}] {r['title']} ({r.get('year', 'N/A')})")

    elif cmd == "find":
        query = " ".join(sys.argv[2:])
        results = orchestrator.find(query)

        print(f"\n🎯 Best Results for: {query}")
        print("=" * 60)
        for i, r in enumerate(results[:10], 1):
            quality = r.get("quality", 0)
            print(f"{i}. [{quality:.0%}] {r['source_name']}: {r['content'][:100]}...")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: status, search, scraper, arr, find")
        sys.exit(1)


if __name__ == "__main__":
    main()
