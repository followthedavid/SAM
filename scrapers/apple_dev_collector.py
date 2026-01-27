#!/usr/bin/env python3
"""
Apple Developer Documentation & Code Collector

Collects training data for native Mac/iOS development:
- Apple Developer Documentation (Swift, SwiftUI, AppKit, UIKit, etc.)
- Apple Sample Code
- GitHub Swift/macOS repositories
- Stack Overflow Swift/macOS questions
- WWDC session content

Output: JSONL training data for SAM to learn native Apple development
"""

import os
import re
import json
import time
import sqlite3
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "storage_root": "/Volumes/David External/apple_dev_archive",
    "db_name": "apple_dev.db",
    "rate_limit": 1.0,
    "timeout": 30,
    "max_retries": 3,
}

# Apple frameworks to collect
FRAMEWORKS = [
    # Core Mac
    "AppKit", "Cocoa", "Foundation", "CoreFoundation",
    # Modern UI
    "SwiftUI", "Combine", "Swift", "SwiftData", "SwiftNIO",
    # iOS/Cross-platform
    "UIKit", "CoreGraphics", "CoreAnimation", "QuartzCore",
    # System
    "Darwin", "Dispatch", "os", "System", "IOKit",
    # Media
    "AVFoundation", "CoreMedia", "VideoToolbox", "AudioToolbox",
    "CoreAudio", "CoreImage", "CoreML", "Vision", "NaturalLanguage",
    # Data
    "CoreData", "CloudKit", "FileProvider", "UniformTypeIdentifiers",
    # Network
    "Network", "URLSession", "MultipeerConnectivity", "NearbyInteraction",
    # Security
    "Security", "CryptoKit", "LocalAuthentication",
    # Hardware
    "CoreBluetooth", "CoreLocation", "CoreMotion", "ARKit", "RealityKit",
    # App Services
    "UserNotifications", "BackgroundTasks", "WidgetKit", "AppIntents",
    "Shortcuts", "SiriKit", "ActivityKit",
    # Metal/Graphics
    "Metal", "MetalKit", "ModelIO", "SceneKit", "SpriteKit", "GameKit",
    # Accessibility
    "Accessibility", "VoiceOver",
    # Mac-specific
    "ServiceManagement", "LaunchServices", "ApplicationServices",
    "Automator", "ScriptingBridge", "AppleScript", "OSAKit",
]

# GitHub search queries for Mac development
GITHUB_QUERIES = [
    "language:swift stars:>100 macos app",
    "language:swift stars:>50 appkit",
    "language:swift stars:>100 swiftui",
    "language:swift stars:>50 menu bar app macos",
    "language:swift stars:>50 cocoa",
    "language:swift stars:>100 combine",
    "language:swift stars:>50 core data",
    "language:swift stars:>50 metal",
    "language:swift stars:>50 avfoundation",
    "language:swift stars:>100 networking",
    "language:swift stars:>50 webkit",
    "language:swift stars:>50 file provider",
    "language:swift stars:>50 automation macos",
    "language:swift mlx apple silicon",
    "language:swift coreml vision",
    "language:objective-c stars:>100 macos",
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE
# ============================================================================

class AppleDevDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Documentation entries
        c.execute('''
            CREATE TABLE IF NOT EXISTS docs (
                id TEXT PRIMARY KEY,
                framework TEXT,
                title TEXT,
                url TEXT UNIQUE,
                content TEXT,
                code_examples TEXT,
                collected_at TEXT,
                training_exported INTEGER DEFAULT 0
            )
        ''')

        # GitHub repos/files
        c.execute('''
            CREATE TABLE IF NOT EXISTS github_code (
                id TEXT PRIMARY KEY,
                repo TEXT,
                file_path TEXT,
                url TEXT UNIQUE,
                language TEXT,
                content TEXT,
                stars INTEGER,
                description TEXT,
                collected_at TEXT,
                training_exported INTEGER DEFAULT 0
            )
        ''')

        # Stack Overflow
        c.execute('''
            CREATE TABLE IF NOT EXISTS stackoverflow (
                id INTEGER PRIMARY KEY,
                title TEXT,
                question TEXT,
                accepted_answer TEXT,
                tags TEXT,
                score INTEGER,
                url TEXT UNIQUE,
                collected_at TEXT,
                training_exported INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def save_doc(self, doc: dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO docs
            (id, framework, title, url, content, code_examples, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            doc['id'], doc['framework'], doc['title'], doc['url'],
            doc['content'], json.dumps(doc.get('code_examples', [])),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def save_github_code(self, code: dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO github_code
            (id, repo, file_path, url, language, content, stars, description, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code['id'], code['repo'], code['file_path'], code['url'],
            code['language'], code['content'], code.get('stars', 0),
            code.get('description', ''), datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def save_stackoverflow(self, qa: dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO stackoverflow
            (id, title, question, accepted_answer, tags, score, url, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            qa['id'], qa['title'], qa['question'], qa['accepted_answer'],
            json.dumps(qa.get('tags', [])), qa.get('score', 0),
            qa['url'], datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        stats = {}
        for table in ['docs', 'github_code', 'stackoverflow']:
            c.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = c.fetchone()[0]

        conn.close()
        return stats


# ============================================================================
# COLLECTORS
# ============================================================================

class GitHubCollector:
    """Collect Swift/macOS code from GitHub."""

    def __init__(self, db: AppleDevDB):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Training-Collector/1.0"
        })

        # Use GitHub token if available
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"token {token}"
            logger.info("Using GitHub API token")

    def search_repos(self, query: str, limit: int = 100) -> List[dict]:
        """Search GitHub for repositories."""
        repos = []
        page = 1
        per_page = min(limit, 100)

        while len(repos) < limit:
            try:
                url = "https://api.github.com/search/repositories"
                params = {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page
                }

                resp = self.session.get(url, params=params, timeout=30)

                if resp.status_code == 403:
                    logger.warning("GitHub rate limit hit, waiting 60s...")
                    time.sleep(60)
                    continue

                if resp.status_code != 200:
                    logger.error(f"GitHub API error: {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("items", [])

                if not items:
                    break

                repos.extend(items)
                page += 1
                time.sleep(1)  # Rate limit

            except Exception as e:
                logger.error(f"GitHub search error: {e}")
                break

        return repos[:limit]

    def get_repo_swift_files(self, repo: dict, limit: int = 20) -> List[dict]:
        """Get Swift files from a repository."""
        files = []

        try:
            # Search for Swift files in repo
            url = "https://api.github.com/search/code"
            params = {
                "q": f"repo:{repo['full_name']} extension:swift",
                "per_page": min(limit, 100)
            }

            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 403:
                time.sleep(60)
                return []

            if resp.status_code != 200:
                return []

            data = resp.json()

            for item in data.get("items", [])[:limit]:
                # Get file content
                raw_url = item.get("html_url", "").replace(
                    "github.com", "raw.githubusercontent.com"
                ).replace("/blob/", "/")

                try:
                    content_resp = self.session.get(raw_url, timeout=30)
                    if content_resp.status_code == 200:
                        content = content_resp.text

                        # Skip if too short or too long
                        if 100 < len(content) < 50000:
                            files.append({
                                "id": item["sha"],
                                "repo": repo["full_name"],
                                "file_path": item["path"],
                                "url": item["html_url"],
                                "language": "swift",
                                "content": content,
                                "stars": repo.get("stargazers_count", 0),
                                "description": repo.get("description", "")
                            })

                    time.sleep(0.5)

                except Exception as e:
                    logger.debug(f"Error fetching file: {e}")

        except Exception as e:
            logger.error(f"Error getting repo files: {e}")

        return files

    def collect(self, limit_repos: int = 50, limit_files: int = 10):
        """Collect Swift code from GitHub."""
        total_files = 0

        for query in GITHUB_QUERIES:
            logger.info(f"Searching: {query}")

            repos = self.search_repos(query, limit=limit_repos)
            logger.info(f"  Found {len(repos)} repos")

            for repo in repos:
                files = self.get_repo_swift_files(repo, limit=limit_files)

                for f in files:
                    self.db.save_github_code(f)
                    total_files += 1

                if files:
                    logger.info(f"  {repo['full_name']}: {len(files)} files")

                time.sleep(1)

        logger.info(f"Collected {total_files} Swift files")
        return total_files


class StackOverflowCollector:
    """Collect Swift/macOS Q&A from Stack Overflow."""

    def __init__(self, db: AppleDevDB):
        self.db = db
        self.session = requests.Session()

    def search_questions(self, tag: str, limit: int = 100) -> List[dict]:
        """Search Stack Overflow for questions."""
        questions = []
        page = 1

        while len(questions) < limit:
            try:
                url = "https://api.stackexchange.com/2.3/questions"
                params = {
                    "order": "desc",
                    "sort": "votes",
                    "tagged": tag,
                    "site": "stackoverflow",
                    "filter": "withbody",
                    "pagesize": min(100, limit),
                    "page": page
                }

                resp = self.session.get(url, params=params, timeout=30)

                if resp.status_code != 200:
                    break

                data = resp.json()
                items = data.get("items", [])

                if not items:
                    break

                # Get accepted answers
                for q in items:
                    if q.get("accepted_answer_id"):
                        answer = self._get_answer(q["accepted_answer_id"])
                        if answer:
                            questions.append({
                                "id": q["question_id"],
                                "title": q["title"],
                                "question": self._clean_html(q.get("body", "")),
                                "accepted_answer": self._clean_html(answer),
                                "tags": q.get("tags", []),
                                "score": q.get("score", 0),
                                "url": q.get("link", "")
                            })

                page += 1
                time.sleep(0.5)

                if data.get("has_more") is False:
                    break

            except Exception as e:
                logger.error(f"Stack Overflow error: {e}")
                break

        return questions[:limit]

    def _get_answer(self, answer_id: int) -> Optional[str]:
        """Get answer content."""
        try:
            url = f"https://api.stackexchange.com/2.3/answers/{answer_id}"
            params = {
                "site": "stackoverflow",
                "filter": "withbody"
            }

            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    return items[0].get("body", "")

        except Exception:
            pass

        return None

    def _clean_html(self, html: str) -> str:
        """Convert HTML to plain text with code blocks preserved."""
        soup = BeautifulSoup(html, "html.parser")

        # Replace code blocks with markdown
        for code in soup.find_all("code"):
            code.replace_with(f"`{code.get_text()}`")

        for pre in soup.find_all("pre"):
            pre.replace_with(f"\n```\n{pre.get_text()}\n```\n")

        return soup.get_text().strip()

    def collect(self, limit_per_tag: int = 100):
        """Collect Q&A from Stack Overflow."""
        tags = [
            "swift", "swiftui", "macos", "appkit", "cocoa",
            "ios", "uikit", "xcode", "core-data", "combine",
            "avfoundation", "metal", "spritekit", "arkit",
            "swift-concurrency", "async-await"
        ]

        total = 0
        for tag in tags:
            logger.info(f"Collecting Stack Overflow: {tag}")
            questions = self.search_questions(tag, limit=limit_per_tag)

            for q in questions:
                self.db.save_stackoverflow(q)
                total += 1

            logger.info(f"  {tag}: {len(questions)} Q&A pairs")
            time.sleep(2)

        logger.info(f"Collected {total} Stack Overflow Q&A")
        return total


# ============================================================================
# TRAINING DATA EXPORT
# ============================================================================

def export_training_data(db: AppleDevDB, output_path: Path):
    """Export collected data to training JSONL format."""
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row

    training_pairs = []

    # GitHub code -> explanation pairs
    cur = conn.cursor()
    cur.execute("SELECT * FROM github_code WHERE training_exported = 0")

    for row in cur.fetchall():
        content = row["content"]

        # Create "explain this code" pairs
        if len(content) > 200:
            training_pairs.append({
                "messages": [
                    {"role": "user", "content": f"Explain this Swift code:\n\n```swift\n{content[:2000]}\n```"},
                    {"role": "assistant", "content": f"This Swift code from {row['repo']} ({row['description'] or 'a macOS/iOS project'}):\n\n{_generate_code_explanation(content)}"}
                ]
            })

        # Create "how to implement" pairs
        if row["description"]:
            training_pairs.append({
                "messages": [
                    {"role": "user", "content": f"How do I implement {row['description'].lower()} in Swift for macOS?"},
                    {"role": "assistant", "content": f"Here's an implementation approach:\n\n```swift\n{content[:3000]}\n```\n\nThis code demonstrates the key patterns for {row['description'].lower()}."}
                ]
            })

    # Stack Overflow Q&A
    cur.execute("SELECT * FROM stackoverflow WHERE training_exported = 0")

    for row in cur.fetchall():
        if row["accepted_answer"]:
            training_pairs.append({
                "messages": [
                    {"role": "user", "content": row["question"][:2000]},
                    {"role": "assistant", "content": row["accepted_answer"][:4000]}
                ]
            })

    conn.close()

    # Write training file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        for pair in training_pairs:
            f.write(json.dumps(pair) + "\n")

    logger.info(f"Exported {len(training_pairs)} training pairs to {output_path}")
    return len(training_pairs)


def _generate_code_explanation(code: str) -> str:
    """Generate a basic explanation of Swift code structure."""
    explanations = []

    if "import " in code:
        imports = re.findall(r'import (\w+)', code)
        if imports:
            explanations.append(f"Uses frameworks: {', '.join(imports)}")

    if "class " in code:
        classes = re.findall(r'class (\w+)', code)
        if classes:
            explanations.append(f"Defines classes: {', '.join(classes[:5])}")

    if "struct " in code:
        structs = re.findall(r'struct (\w+)', code)
        if structs:
            explanations.append(f"Defines structs: {', '.join(structs[:5])}")

    if "@main" in code or "@MainActor" in code:
        explanations.append("Uses Swift concurrency and main actor")

    if "async " in code or "await " in code:
        explanations.append("Uses async/await for concurrency")

    if "@Published" in code or "ObservableObject" in code:
        explanations.append("Uses Combine for reactive programming")

    if "@State" in code or "@Binding" in code:
        explanations.append("Uses SwiftUI state management")

    if "NSWindow" in code or "NSView" in code:
        explanations.append("Uses AppKit for native macOS UI")

    return " ".join(explanations) if explanations else "Swift implementation."


# ============================================================================
# CUTTING EDGE SOURCES (Auto-updating)
# ============================================================================

class CuttingEdgeCollector:
    """Collect bleeding-edge Apple development content."""

    def __init__(self, db: AppleDevDB):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
        })

    def collect_swift_evolution(self):
        """Collect Swift Evolution proposals - the future of Swift."""
        logger.info("Collecting Swift Evolution proposals...")
        proposals = []

        try:
            # Swift Evolution proposals are on GitHub
            url = "https://api.github.com/repos/apple/swift-evolution/contents/proposals"
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 200:
                files = resp.json()

                for f in files:
                    if f["name"].endswith(".md"):
                        # Get proposal content
                        raw_url = f["download_url"]
                        content_resp = self.session.get(raw_url, timeout=30)

                        if content_resp.status_code == 200:
                            content = content_resp.text

                            # Parse proposal
                            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                            title = title_match.group(1) if title_match else f["name"]

                            self.db.save_doc({
                                "id": f"swift-evolution-{f['name']}",
                                "framework": "Swift-Evolution",
                                "title": title,
                                "url": f["html_url"],
                                "content": content,
                                "code_examples": re.findall(r'```swift\n(.*?)```', content, re.DOTALL)
                            })
                            proposals.append(title)

                        time.sleep(0.5)

            logger.info(f"  Collected {len(proposals)} Swift Evolution proposals")

        except Exception as e:
            logger.error(f"Swift Evolution error: {e}")

        return len(proposals)

    def collect_apple_sample_code(self):
        """Collect Apple's official sample code from GitHub."""
        logger.info("Collecting Apple sample code...")
        samples = 0

        apple_repos = [
            "apple/swift-algorithms",
            "apple/swift-collections",
            "apple/swift-async-algorithms",
            "apple/swift-nio",
            "apple/swift-argument-parser",
            "apple/swift-log",
            "apple/swift-metrics",
            "apple/swift-crypto",
            "apple/swift-atomics",
            "apple/swift-system",
            "apple/swift-distributed-actors",
            "apple/swift-markdown",
            "apple/swift-syntax",
            "apple/swift-format",
            "apple/swift-testing",
            "apple/ml-stable-diffusion",
            "apple/coremltools",
            "apple/tensorflow_macos",
        ]

        for repo in apple_repos:
            try:
                # Get README and key Swift files
                api_url = f"https://api.github.com/repos/{repo}/contents"
                resp = self.session.get(api_url, timeout=30)

                if resp.status_code == 200:
                    files = resp.json()

                    for f in files:
                        if f["name"].endswith((".swift", ".md")) and f["size"] < 100000:
                            raw_url = f.get("download_url")
                            if raw_url:
                                content_resp = self.session.get(raw_url, timeout=30)
                                if content_resp.status_code == 200:
                                    self.db.save_github_code({
                                        "id": f"{repo}-{f['name']}",
                                        "repo": repo,
                                        "file_path": f["path"],
                                        "url": f["html_url"],
                                        "language": "swift" if f["name"].endswith(".swift") else "markdown",
                                        "content": content_resp.text,
                                        "stars": 0,  # Official Apple
                                        "description": f"Official Apple: {repo}"
                                    })
                                    samples += 1

                time.sleep(1)

            except Exception as e:
                logger.debug(f"Error with {repo}: {e}")

        logger.info(f"  Collected {samples} Apple sample files")
        return samples

    def collect_wwdc_content(self):
        """Collect WWDC session information and code."""
        logger.info("Collecting WWDC content...")
        sessions = 0

        # WWDC sessions are indexed by various sources
        # Using Apple's developer documentation structure
        try:
            # Get recent WWDC years
            for year in [2024, 2023, 2022, 2021]:
                # Search GitHub for WWDC sample code
                url = "https://api.github.com/search/repositories"
                params = {
                    "q": f"wwdc{year} language:swift",
                    "sort": "stars",
                    "per_page": 20
                }

                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    repos = resp.json().get("items", [])

                    for repo in repos[:10]:
                        self.db.save_github_code({
                            "id": f"wwdc{year}-{repo['name']}",
                            "repo": repo["full_name"],
                            "file_path": "README.md",
                            "url": repo["html_url"],
                            "language": "swift",
                            "content": repo.get("description", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "description": f"WWDC {year}: {repo['name']}"
                        })
                        sessions += 1

                time.sleep(2)

        except Exception as e:
            logger.error(f"WWDC collection error: {e}")

        logger.info(f"  Collected {sessions} WWDC-related repos")
        return sessions

    def collect_swift_package_index(self):
        """Collect popular Swift packages from Swift Package Index."""
        logger.info("Collecting Swift Package Index...")
        packages = 0

        try:
            # Swift Package Index API
            url = "https://swiftpackageindex.com/api/packages"
            # Note: This is a simplified approach; real API may differ

            # Search for popular packages via GitHub instead
            queries = [
                "swift package stars:>500",
                "swiftui package stars:>200",
                "macos utility swift stars:>100",
            ]

            for query in queries:
                api_url = "https://api.github.com/search/repositories"
                params = {"q": query, "sort": "stars", "per_page": 30}

                resp = self.session.get(api_url, params=params, timeout=30)
                if resp.status_code == 200:
                    repos = resp.json().get("items", [])

                    for repo in repos:
                        self.db.save_github_code({
                            "id": f"pkg-{repo['full_name'].replace('/', '-')}",
                            "repo": repo["full_name"],
                            "file_path": "Package.swift",
                            "url": repo["html_url"],
                            "language": "swift",
                            "content": repo.get("description", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "description": f"Swift Package: {repo['name']}"
                        })
                        packages += 1

                time.sleep(2)

        except Exception as e:
            logger.error(f"Package index error: {e}")

        logger.info(f"  Collected {packages} Swift packages")
        return packages

    def collect_all(self):
        """Collect all cutting-edge content."""
        total = 0
        total += self.collect_swift_evolution()
        total += self.collect_apple_sample_code()
        total += self.collect_wwdc_content()
        total += self.collect_swift_package_index()
        return total


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Apple Developer Data Collector")
    parser.add_argument("command", choices=["github", "stackoverflow", "cutting-edge", "export", "stats", "all"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=str, default=None)

    args = parser.parse_args()

    storage = Path(CONFIG["storage_root"])
    storage.mkdir(parents=True, exist_ok=True)
    db = AppleDevDB(storage / CONFIG["db_name"])

    if args.command == "github":
        collector = GitHubCollector(db)
        collector.collect(limit_repos=args.limit, limit_files=10)

    elif args.command == "stackoverflow":
        collector = StackOverflowCollector(db)
        collector.collect(limit_per_tag=args.limit)

    elif args.command == "cutting-edge":
        collector = CuttingEdgeCollector(db)
        collector.collect_all()

    elif args.command == "export":
        output = Path(args.output) if args.output else storage / "apple_dev_training.jsonl"
        export_training_data(db, output)

    elif args.command == "stats":
        stats = db.get_stats()
        print("\n=== Apple Developer Archive Stats ===")
        for k, v in stats.items():
            print(f"  {k}: {v:,}")

    elif args.command == "all":
        # Collect everything including cutting edge
        github = GitHubCollector(db)
        github.collect(limit_repos=args.limit, limit_files=10)

        so = StackOverflowCollector(db)
        so.collect(limit_per_tag=args.limit)

        cutting = CuttingEdgeCollector(db)
        cutting.collect_all()

        # Export
        output = storage / "apple_dev_training.jsonl"
        export_training_data(db, output)

        print(f"\n✓ Training data exported to: {output}")


if __name__ == "__main__":
    main()
