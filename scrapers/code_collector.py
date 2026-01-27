#!/usr/bin/env python3
"""
Coding Training Data Collector for SAM

Collects code examples from multiple sources to train SAM on coding tasks.
Sources:
1. GitHub repositories (permissive licenses)
2. Stack Overflow Q&As
3. GitHub Pull Request diffs (for perpetual ladder training)

Usage:
    python code_collector.py github --lang python --limit 1000
    python code_collector.py stackoverflow --tags python,rust --limit 5000
    python code_collector.py prs --repos anthropics/claude-code --limit 500
    python code_collector.py status
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import re

# Output location
OUTPUT_DIR = Path("/Volumes/David External/coding_training")
DB_PATH = OUTPUT_DIR / "code_collection.db"

# Rate limiting
GITHUB_RATE_LIMIT = 1.0  # seconds between requests
SO_RATE_LIMIT = 0.5

@dataclass
class CodeExample:
    """A single code training example"""
    id: str
    source: str  # github, stackoverflow, pr
    language: str
    title: str
    description: str
    code: str
    context: str  # surrounding code, question text, etc.
    tags: List[str]
    url: str
    quality_score: float  # stars, votes, etc.
    collected_at: str

@dataclass
class PRDiff:
    """A pull request diff for perpetual ladder training"""
    id: str
    repo: str
    pr_number: int
    title: str
    description: str
    before_code: str
    after_code: str
    review_comments: List[str]
    file_path: str
    language: str
    url: str
    collected_at: str


class CodeCollectorDB:
    """SQLite database for tracking collected code"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Code examples table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_examples (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                language TEXT,
                title TEXT,
                description TEXT,
                code TEXT,
                context TEXT,
                tags TEXT,
                url TEXT,
                quality_score REAL,
                collected_at TEXT
            )
        """)

        # PR diffs table (for perpetual ladder training)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pr_diffs (
                id TEXT PRIMARY KEY,
                repo TEXT NOT NULL,
                pr_number INTEGER,
                title TEXT,
                description TEXT,
                before_code TEXT,
                after_code TEXT,
                review_comments TEXT,
                file_path TEXT,
                language TEXT,
                url TEXT,
                collected_at TEXT
            )
        """)

        # Progress tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS collection_progress (
                source TEXT PRIMARY KEY,
                last_cursor TEXT,
                total_collected INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_example(self, example: CodeExample) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO code_examples
                (id, source, language, title, description, code, context, tags, url, quality_score, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example.id, example.source, example.language, example.title,
                example.description, example.code, example.context,
                json.dumps(example.tags), example.url, example.quality_score,
                example.collected_at
            ))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def add_pr_diff(self, diff: PRDiff) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO pr_diffs
                (id, repo, pr_number, title, description, before_code, after_code,
                 review_comments, file_path, language, url, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                diff.id, diff.repo, diff.pr_number, diff.title, diff.description,
                diff.before_code, diff.after_code, json.dumps(diff.review_comments),
                diff.file_path, diff.language, diff.url, diff.collected_at
            ))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {}

        # Code examples by source
        cur.execute("SELECT source, COUNT(*) FROM code_examples GROUP BY source")
        stats["examples_by_source"] = dict(cur.fetchall())

        # Code examples by language
        cur.execute("SELECT language, COUNT(*) FROM code_examples GROUP BY language")
        stats["examples_by_language"] = dict(cur.fetchall())

        # PR diffs
        cur.execute("SELECT COUNT(*) FROM pr_diffs")
        stats["total_pr_diffs"] = cur.fetchone()[0]

        # PR diffs by repo
        cur.execute("SELECT repo, COUNT(*) FROM pr_diffs GROUP BY repo")
        stats["pr_diffs_by_repo"] = dict(cur.fetchall())

        conn.close()
        return stats


class GitHubCollector:
    """Collects code from GitHub repositories"""

    LANGUAGES = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "rust": [".rs"],
        "go": [".go"],
    }

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.db = CodeCollectorDB()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search_repos(self, language: str, min_stars: int = 100, limit: int = 100) -> List[Dict]:
        """Search for high-quality repos in a language"""
        repos = []
        page = 1

        while len(repos) < limit:
            # Build URL with proper encoding
            per_page = min(100, limit - len(repos))
            url = f"https://api.github.com/search/repositories?q=language:{language}+stars:%3E{min_stars}&sort=stars&order=desc&per_page={per_page}&page={page}"

            resp = self.session.get(url)
            if resp.status_code != 200:
                print(f"GitHub API error: {resp.status_code} - {resp.text[:200]}")
                break

            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            repos.extend(items)
            page += 1
            time.sleep(GITHUB_RATE_LIMIT)

        return repos[:limit]

    def get_repo_files(self, owner: str, repo: str, language: str, path: str = "") -> List[Dict]:
        """Get all files of a specific language from a repo"""
        files = []
        extensions = self.LANGUAGES.get(language, [])

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        resp = self.session.get(url)

        if resp.status_code != 200:
            return files

        for item in resp.json():
            if item["type"] == "file":
                if any(item["name"].endswith(ext) for ext in extensions):
                    files.append(item)
            elif item["type"] == "dir" and not item["name"].startswith("."):
                # Recurse into directories (limit depth)
                if path.count("/") < 3:
                    time.sleep(GITHUB_RATE_LIMIT)
                    files.extend(self.get_repo_files(owner, repo, language, item["path"]))

        return files

    def extract_functions(self, code: str, language: str) -> List[Tuple[str, str, str]]:
        """Extract functions/classes with their docstrings"""
        examples = []

        if language == "python":
            # Match Python functions and classes with docstrings
            pattern = r'((?:async\s+)?def\s+\w+[^:]+:|class\s+\w+[^:]*:)\s*\n\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')?[\s\S]*?(?=\n(?:(?:async\s+)?def\s+|\nclass\s+|\Z))'
            matches = re.findall(pattern, code)

            for match in matches:
                signature = match[0].strip()
                docstring = match[1].strip() if match[1] else ""
                # Get the full function body
                full_match = re.search(re.escape(signature) + r'[\s\S]*?(?=\n(?:(?:async\s+)?def\s+|\nclass\s+|\Z))', code)
                if full_match:
                    body = full_match.group(0)
                    name = re.search(r'(?:def|class)\s+(\w+)', signature)
                    if name and len(body) > 50:  # Minimum meaningful size
                        examples.append((name.group(1), docstring, body))

        elif language in ["typescript", "javascript"]:
            # Match JS/TS functions
            pattern = r'(/\*\*[\s\S]*?\*/\s*)?((?:export\s+)?(?:async\s+)?function\s+\w+[^{]+\{[\s\S]*?\n\})'
            matches = re.findall(pattern, code)
            for match in matches:
                docstring = match[0].strip() if match[0] else ""
                body = match[1].strip()
                name = re.search(r'function\s+(\w+)', body)
                if name and len(body) > 50:
                    examples.append((name.group(1), docstring, body))

        elif language == "rust":
            # Match Rust functions
            pattern = r'(///.*\n)*\s*(pub\s+)?(async\s+)?fn\s+\w+[^{]+\{[\s\S]*?\n\}'
            matches = re.findall(pattern, code)
            for match in matches:
                docstring = match[0].strip() if match[0] else ""
                body = "".join(match).strip()
                name = re.search(r'fn\s+(\w+)', body)
                if name and len(body) > 50:
                    examples.append((name.group(1), docstring, body))

        return examples

    def collect_from_repos(self, language: str, limit: int = 1000, min_stars: int = 100):
        """Collect code examples from GitHub repos"""
        print(f"Searching for {language} repos with {min_stars}+ stars...")
        repos = self.search_repos(language, min_stars, limit=50)

        collected = 0
        for repo in repos:
            if collected >= limit:
                break

            owner = repo["owner"]["login"]
            name = repo["name"]
            stars = repo["stargazers_count"]

            print(f"\n📦 {owner}/{name} ({stars}⭐)")

            files = self.get_repo_files(owner, name, language)
            print(f"   Found {len(files)} {language} files")

            for file_info in files[:20]:  # Limit files per repo
                if collected >= limit:
                    break

                # Get file content
                time.sleep(GITHUB_RATE_LIMIT)
                resp = self.session.get(file_info["download_url"])
                if resp.status_code != 200:
                    continue

                code = resp.text
                functions = self.extract_functions(code, language)

                for func_name, docstring, body in functions:
                    example = CodeExample(
                        id=hashlib.md5(body.encode()).hexdigest(),
                        source="github",
                        language=language,
                        title=func_name,
                        description=docstring,
                        code=body,
                        context=f"From {owner}/{name}: {file_info['path']}",
                        tags=[language, owner, name],
                        url=file_info["html_url"],
                        quality_score=stars,
                        collected_at=datetime.now().isoformat()
                    )

                    if self.db.add_example(example):
                        collected += 1
                        if collected % 100 == 0:
                            print(f"   ✓ Collected {collected} examples")

        print(f"\n✅ Total collected: {collected} {language} examples")
        return collected


class StackOverflowCollector:
    """Collects Q&A pairs from Stack Overflow"""

    BASE_URL = "https://api.stackexchange.com/2.3"

    def __init__(self):
        self.db = CodeCollectorDB()
        self.session = requests.Session()

    def search_questions(self, tags: List[str], limit: int = 1000) -> int:
        """Search for questions with accepted answers"""
        collected = 0
        page = 1

        tag_str = ";".join(tags)

        while collected < limit:
            url = f"{self.BASE_URL}/questions"
            params = {
                "order": "desc",
                "sort": "votes",
                "tagged": tag_str,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": 100,
                "page": page
            }

            resp = self.session.get(url, params=params)
            if resp.status_code != 200:
                print(f"SO API error: {resp.status_code}")
                break

            data = resp.json()
            questions = data.get("items", [])

            if not questions:
                break

            for q in questions:
                if collected >= limit:
                    break

                if not q.get("accepted_answer_id"):
                    continue

                # Get the accepted answer
                time.sleep(SO_RATE_LIMIT)
                ans_resp = self.session.get(
                    f"{self.BASE_URL}/answers/{q['accepted_answer_id']}",
                    params={"site": "stackoverflow", "filter": "withbody"}
                )

                if ans_resp.status_code != 200:
                    continue

                ans_data = ans_resp.json()
                if not ans_data.get("items"):
                    continue

                answer = ans_data["items"][0]

                # Extract code blocks from answer
                code_blocks = re.findall(r'<code>([\s\S]*?)</code>', answer.get("body", ""))
                if not code_blocks:
                    continue

                code = "\n\n".join(code_blocks)

                # Detect language from tags
                lang_map = {"python": "python", "javascript": "javascript",
                           "typescript": "typescript", "rust": "rust", "go": "go"}
                language = "unknown"
                for tag in q.get("tags", []):
                    if tag in lang_map:
                        language = lang_map[tag]
                        break

                example = CodeExample(
                    id=hashlib.md5(f"so_{q['question_id']}".encode()).hexdigest(),
                    source="stackoverflow",
                    language=language,
                    title=q.get("title", ""),
                    description=re.sub(r'<[^>]+>', '', q.get("body", ""))[:500],
                    code=code,
                    context=f"Question: {q.get('title', '')}",
                    tags=q.get("tags", []),
                    url=q.get("link", ""),
                    quality_score=q.get("score", 0),
                    collected_at=datetime.now().isoformat()
                )

                if self.db.add_example(example):
                    collected += 1
                    if collected % 50 == 0:
                        print(f"✓ Collected {collected} SO examples")

            page += 1

            # Check rate limit
            if data.get("quota_remaining", 100) < 10:
                print("Approaching rate limit, pausing...")
                time.sleep(60)

        print(f"\n✅ Total collected: {collected} Stack Overflow examples")
        return collected


class PRDiffCollector:
    """Collects PR diffs for perpetual ladder training

    This is the key data for teaching SAM to improve code iteratively.
    Each PR shows: before_code → after_code + review_comments
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.db = CodeCollectorDB()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_pr_list(self, repo: str, state: str = "closed", limit: int = 100) -> List[Dict]:
        """Get list of PRs from a repo"""
        prs = []
        page = 1

        while len(prs) < limit:
            url = f"https://api.github.com/repos/{repo}/pulls"
            params = {
                "state": state,
                "sort": "updated",
                "direction": "desc",
                "per_page": min(100, limit - len(prs)),
                "page": page
            }

            resp = self.session.get(url, params=params)
            if resp.status_code != 200:
                print(f"Error fetching PRs: {resp.status_code}")
                break

            items = resp.json()
            if not items:
                break

            # Only include merged PRs (successful improvements)
            merged = [pr for pr in items if pr.get("merged_at")]
            prs.extend(merged)
            page += 1
            time.sleep(GITHUB_RATE_LIMIT)

        return prs[:limit]

    def get_pr_files(self, repo: str, pr_number: int) -> List[Dict]:
        """Get files changed in a PR"""
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        resp = self.session.get(url)

        if resp.status_code != 200:
            return []

        return resp.json()

    def get_pr_comments(self, repo: str, pr_number: int) -> List[str]:
        """Get review comments on a PR"""
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
        resp = self.session.get(url)

        if resp.status_code != 200:
            return []

        comments = []
        for comment in resp.json():
            body = comment.get("body", "").strip()
            if body and len(body) > 20:  # Skip trivial comments
                comments.append(body)

        return comments

    def get_file_at_commit(self, repo: str, path: str, sha: str) -> Optional[str]:
        """Get file content at a specific commit"""
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        params = {"ref": sha}

        resp = self.session.get(url, params=params)
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("encoding") == "base64":
            import base64
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")

        return None

    def detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
        }

        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                return lang
        return "unknown"

    def collect_from_repo(self, repo: str, limit: int = 100) -> int:
        """Collect PR diffs from a repository"""
        print(f"Fetching PRs from {repo}...")
        prs = self.get_pr_list(repo, limit=limit)
        print(f"Found {len(prs)} merged PRs")

        collected = 0

        for pr in prs:
            pr_number = pr["number"]
            base_sha = pr["base"]["sha"]
            head_sha = pr["head"]["sha"]

            print(f"\n📝 PR #{pr_number}: {pr['title'][:50]}...")

            # Get files changed
            time.sleep(GITHUB_RATE_LIMIT)
            files = self.get_pr_files(repo, pr_number)

            # Get review comments
            time.sleep(GITHUB_RATE_LIMIT)
            comments = self.get_pr_comments(repo, pr_number)

            for file_info in files[:5]:  # Limit files per PR
                filename = file_info.get("filename", "")
                language = self.detect_language(filename)

                if language == "unknown":
                    continue

                # Skip huge files
                if file_info.get("changes", 0) > 500:
                    continue

                # Get before/after content
                time.sleep(GITHUB_RATE_LIMIT)
                before = self.get_file_at_commit(repo, filename, base_sha) or ""

                time.sleep(GITHUB_RATE_LIMIT)
                after = self.get_file_at_commit(repo, filename, head_sha) or ""

                if not before or not after:
                    continue

                diff = PRDiff(
                    id=hashlib.md5(f"{repo}_{pr_number}_{filename}".encode()).hexdigest(),
                    repo=repo,
                    pr_number=pr_number,
                    title=pr.get("title", ""),
                    description=pr.get("body", "") or "",
                    before_code=before,
                    after_code=after,
                    review_comments=comments,
                    file_path=filename,
                    language=language,
                    url=pr.get("html_url", ""),
                    collected_at=datetime.now().isoformat()
                )

                if self.db.add_pr_diff(diff):
                    collected += 1
                    print(f"   ✓ {filename} ({language})")

        print(f"\n✅ Total collected: {collected} PR diffs from {repo}")
        return collected


def convert_to_training_format(output_path: Path):
    """Convert collected data to JSONL training format"""
    db = CodeCollectorDB()
    conn = sqlite3.connect(db.db_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w") as f:
        # Code examples (instruction format)
        cur = conn.cursor()
        cur.execute("SELECT * FROM code_examples")

        for row in cur.fetchall():
            example = {
                "instruction": f"Write a {row[2]} function/class that: {row[4]}" if row[4] else f"Write this {row[2]} code:",
                "input": row[7] if row[7] else "",  # context
                "output": row[5],  # code
                "source": row[1],
                "language": row[2]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

        # PR diffs (improvement format - key for perpetual ladder!)
        cur.execute("SELECT * FROM pr_diffs")

        for row in cur.fetchall():
            # Format: given this code + feedback, improve it
            comments = json.loads(row[7]) if row[7] else []
            feedback = " ".join(comments[:3]) if comments else row[3]  # Use PR title if no comments

            example = {
                "instruction": f"Improve this {row[9]} code based on feedback: {feedback[:200]}",
                "input": row[5],  # before_code
                "output": row[6],  # after_code
                "source": "pr_diff",
                "language": row[9],
                "repo": row[1]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

    conn.close()
    print(f"✅ Exported {count} examples to {output_path}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Collect coding training data for SAM")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # GitHub command
    gh_parser = subparsers.add_parser("github", help="Collect from GitHub repos")
    gh_parser.add_argument("--lang", default="python", help="Language to collect")
    gh_parser.add_argument("--limit", type=int, default=1000, help="Max examples")
    gh_parser.add_argument("--min-stars", type=int, default=100, help="Min repo stars")

    # Stack Overflow command
    so_parser = subparsers.add_parser("stackoverflow", help="Collect from Stack Overflow")
    so_parser.add_argument("--tags", default="python", help="Comma-separated tags")
    so_parser.add_argument("--limit", type=int, default=1000, help="Max examples")

    # PR diffs command
    pr_parser = subparsers.add_parser("prs", help="Collect PR diffs for improvement training")
    pr_parser.add_argument("--repos", required=True, help="Comma-separated repo list (owner/repo)")
    pr_parser.add_argument("--limit", type=int, default=100, help="Max PRs per repo")

    # Export command
    exp_parser = subparsers.add_parser("export", help="Export to training format")
    exp_parser.add_argument("--output", default="/Volumes/David External/coding_training/training.jsonl")

    # Status command
    subparsers.add_parser("status", help="Show collection status")

    args = parser.parse_args()

    if args.command == "github":
        collector = GitHubCollector()
        collector.collect_from_repos(args.lang, args.limit, args.min_stars)

    elif args.command == "stackoverflow":
        collector = StackOverflowCollector()
        tags = args.tags.split(",")
        collector.search_questions(tags, args.limit)

    elif args.command == "prs":
        collector = PRDiffCollector()
        repos = args.repos.split(",")
        for repo in repos:
            collector.collect_from_repo(repo.strip(), args.limit)

    elif args.command == "export":
        convert_to_training_format(Path(args.output))

    elif args.command == "status":
        db = CodeCollectorDB()
        stats = db.get_stats()

        print("\n" + "=" * 50)
        print("  CODING TRAINING DATA STATUS")
        print("=" * 50)

        print("\n📊 Code Examples by Source:")
        for source, count in stats.get("examples_by_source", {}).items():
            print(f"   {source}: {count:,}")

        print("\n💻 Code Examples by Language:")
        for lang, count in stats.get("examples_by_language", {}).items():
            print(f"   {lang}: {count:,}")

        print(f"\n🔄 PR Diffs (Improvement Examples): {stats.get('total_pr_diffs', 0):,}")
        if stats.get("pr_diffs_by_repo"):
            for repo, count in stats["pr_diffs_by_repo"].items():
                print(f"   {repo}: {count:,}")

        total = sum(stats.get("examples_by_source", {}).values()) + stats.get("total_pr_diffs", 0)
        print(f"\n✨ TOTAL TRAINING EXAMPLES: {total:,}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
