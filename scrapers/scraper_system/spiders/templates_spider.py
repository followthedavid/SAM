"""
Project Templates Spider - Analyzes starter repos and boilerplates

Targets:
1. iOS/Swift project templates
2. SwiftUI starter projects
3. Xcode project templates
4. App architecture examples
5. CI/CD configuration templates

Critical for teaching SAM how to structure new projects.
"""

import json
import logging
import os
import re
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import quote

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class ProjectTemplatesSpider(BaseSpider):
    """
    Spider for project templates and boilerplates.

    Extracts:
    - Project structure patterns
    - Configuration files
    - Build configurations
    - CI/CD setups
    - Directory conventions

    Usage:
        scrapy crawl templates
        scrapy crawl templates -a category=swiftui
    """

    name = "templates_spider"
    source = "templates"

    # GitHub API
    GH_API = "https://api.github.com"

    # Template repositories to analyze
    TEMPLATE_REPOS = {
        # SwiftUI templates
        "swiftui_template": {
            "repo": "nicklockwood/SwiftFormat",
            "category": "tools",
            "description": "Swift formatter config",
        },
        "tca_template": {
            "repo": "pointfreeco/swift-composable-architecture",
            "category": "architecture",
            "description": "Composable Architecture",
        },
        "clean_swift": {
            "repo": "kudoleh/iOS-Clean-Architecture-MVVM",
            "category": "architecture",
            "description": "Clean Architecture MVVM",
        },
        "vapor_template": {
            "repo": "vapor/template",
            "category": "backend",
            "description": "Vapor backend template",
        },
        "swiftui_mvvm": {
            "repo": "nicklockwood/SwiftFormat",
            "category": "architecture",
            "description": "MVVM pattern",
        },
    }

    # Search queries for templates
    TEMPLATE_SEARCHES = [
        "ios template stars:>100",
        "swiftui starter stars:>50",
        "swift boilerplate stars:>50",
        "xcode template stars:>30",
        "ios mvvm template",
        "swiftui clean architecture",
        "swift project structure",
        "ios ci cd template",
    ]

    # Important files to extract
    IMPORTANT_FILES = [
        # Configuration
        "Package.swift",
        "Podfile",
        "Cartfile",
        ".swiftlint.yml",
        ".swiftformat",
        "project.yml",  # XcodeGen
        "Tuist/",

        # CI/CD
        ".github/workflows/",
        ".gitlab-ci.yml",
        "Fastfile",
        "fastlane/",
        "bitrise.yml",
        ".circleci/config.yml",

        # Project structure
        "README.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",

        # Xcode
        "*.xcodeproj/project.pbxproj",
        "*.xcworkspace/",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, category: str = None, max_repos: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_repos = int(max_repos)
        self.repos_analyzed = 0
        self.seen_repos = set()
        self.category_filter = category

        # GitHub token
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

    def _get_headers(self) -> dict:
        """Get GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Templates-Spider/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def start_requests(self) -> Iterator[Request]:
        """Start analyzing templates."""
        # Search for template repos
        for query in self.TEMPLATE_SEARCHES:
            encoded = quote(f"{query} language:swift")
            url = f"{self.GH_API}/search/repositories?q={encoded}&sort=stars&per_page=20"

            yield self.make_request(
                url,
                callback=self.parse_search_results,
                meta={"query": query},
                headers=self._get_headers()
            )

        # Also analyze known template repos
        for template_id, config in self.TEMPLATE_REPOS.items():
            if self.category_filter and config.get("category") != self.category_filter:
                continue

            repo = config["repo"]
            yield self.make_request(
                f"{self.GH_API}/repos/{repo}",
                callback=self.parse_repo_info,
                meta={
                    "template_id": template_id,
                    "config": config,
                },
                headers=self._get_headers()
            )

    def parse_search_results(self, response: Response) -> Iterator:
        """Parse GitHub search results."""
        query = response.meta.get("query", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        repos = data.get("items", [])

        for repo in repos:
            if self.repos_analyzed >= self.max_repos:
                return

            full_name = repo.get("full_name", "")
            if full_name in self.seen_repos:
                continue
            self.seen_repos.add(full_name)

            yield self.make_request(
                f"{self.GH_API}/repos/{full_name}",
                callback=self.parse_repo_info,
                meta={
                    "search_query": query,
                    "from_search": True,
                },
                headers=self._get_headers()
            )

    def parse_repo_info(self, response: Response) -> Iterator:
        """Parse repository information and fetch structure."""
        try:
            repo = json.loads(response.text)
        except json.JSONDecodeError:
            return

        full_name = repo.get("full_name", "")
        default_branch = repo.get("default_branch", "main")

        # Fetch repository contents (root level)
        yield self.make_request(
            f"{self.GH_API}/repos/{full_name}/contents",
            callback=self.parse_repo_contents,
            meta={
                "repo": repo,
                "path": "",
                "default_branch": default_branch,
            },
            headers=self._get_headers()
        )

        # Also fetch README
        yield self.make_request(
            f"{self.GH_API}/repos/{full_name}/readme",
            callback=self.parse_readme,
            meta={"repo": repo},
            headers=self._get_headers()
        )

    def parse_repo_contents(self, response: Response) -> Iterator:
        """Parse repository contents to extract structure."""
        repo = response.meta.get("repo", {})
        current_path = response.meta.get("path", "")

        try:
            contents = json.loads(response.text)
        except json.JSONDecodeError:
            return

        if not isinstance(contents, list):
            return

        full_name = repo.get("full_name", "")

        # Collect directory structure
        structure = {
            "directories": [],
            "files": [],
            "important_files": [],
        }

        for item in contents:
            name = item.get("name", "")
            item_type = item.get("type", "")
            path = item.get("path", "")

            if item_type == "dir":
                structure["directories"].append(name)

                # Recurse into important directories
                important_dirs = [".github", "fastlane", "Sources", "Tests", "Tuist"]
                if name in important_dirs or current_path == "":
                    yield self.make_request(
                        item.get("url"),
                        callback=self.parse_repo_contents,
                        meta={
                            "repo": repo,
                            "path": path,
                        },
                        headers=self._get_headers()
                    )

            elif item_type == "file":
                structure["files"].append(name)

                # Check if it's an important file
                is_important = any(
                    name == imp or name.endswith(imp.lstrip("*")) or imp.rstrip("/") in path
                    for imp in self.IMPORTANT_FILES
                )

                if is_important:
                    structure["important_files"].append(path)

                    # Fetch content of important files
                    download_url = item.get("download_url")
                    if download_url:
                        yield self.make_request(
                            download_url,
                            callback=self.parse_config_file,
                            meta={
                                "repo": repo,
                                "file_path": path,
                                "file_name": name,
                            },
                            headers=self._get_headers()
                        )

        # Only yield structure item for root
        if current_path == "":
            self.repos_analyzed += 1

            yield ScrapedItem(
                source=self.source,
                url=f"https://github.com/{full_name}",
                title=f"Template: {full_name}",
                content=json.dumps(structure, indent=2),
                metadata={
                    "type": "project_structure",
                    "author": repo.get("owner", {}).get("login", ""),
                    "repo": full_name,
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                    "description": repo.get("description", ""),
                    "topics": repo.get("topics", []),
                    "directories": structure["directories"],
                    "file_count": len(structure["files"]),
                    "important_files": structure["important_files"],
                    "has_ci": any(".github" in f or "fastlane" in f.lower() for f in structure["important_files"]),
                    "has_spm": "Package.swift" in structure["files"],
                    "has_cocoapods": "Podfile" in structure["files"],
                    "has_swiftlint": ".swiftlint.yml" in structure["files"],
                }
            )

    def parse_config_file(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse configuration file content."""
        repo = response.meta.get("repo", {})
        file_path = response.meta.get("file_path", "")
        file_name = response.meta.get("file_name", "")

        content = response.text
        full_name = repo.get("full_name", "")

        if not content or len(content) < 10:
            return

        # Determine config type
        config_type = "config"
        if "workflow" in file_path.lower() or file_name.endswith(".yml"):
            config_type = "ci_cd"
        elif file_name == "Package.swift":
            config_type = "spm"
        elif file_name == "Podfile":
            config_type = "cocoapods"
        elif "fastlane" in file_path.lower():
            config_type = "fastlane"
        elif file_name in [".swiftlint.yml", ".swiftformat"]:
            config_type = "linting"
        elif file_name == "project.yml":
            config_type = "xcodegen"

        yield ScrapedItem(
            source=self.source,
            url=f"https://github.com/{full_name}/blob/main/{file_path}",
            title=f"Config: {file_path}",
            content=content,
            metadata={
                "type": "config_file",
                "config_type": config_type,
                "author": repo.get("owner", {}).get("login", ""),
                "repo": full_name,
                "file_path": file_path,
                "file_name": file_name,
            }
        )

    def parse_readme(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse README for project description and setup instructions."""
        repo = response.meta.get("repo", {})

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        # Decode base64 content
        import base64
        content_b64 = data.get("content", "")
        try:
            content = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        except Exception:
            return

        if not content or len(content) < 100:
            return

        full_name = repo.get("full_name", "")

        # Extract sections
        has_installation = bool(re.search(r'##?\s*installation', content, re.IGNORECASE))
        has_usage = bool(re.search(r'##?\s*usage', content, re.IGNORECASE))
        has_architecture = bool(re.search(r'##?\s*architecture', content, re.IGNORECASE))
        has_requirements = bool(re.search(r'##?\s*requirements?', content, re.IGNORECASE))

        yield ScrapedItem(
            source=self.source,
            url=f"https://github.com/{full_name}",
            title=f"README: {full_name}",
            content=content,
            metadata={
                "type": "template_readme",
                "author": repo.get("owner", {}).get("login", ""),
                "repo": full_name,
                "stars": repo.get("stargazers_count", 0),
                "has_installation": has_installation,
                "has_usage": has_usage,
                "has_architecture": has_architecture,
                "has_requirements": has_requirements,
            }
        )


def register():
    return {
        "name": "templates",
        "spider_class": ProjectTemplatesSpider,
        "description": "Project Templates & Boilerplates",
        "type": "planning",
        "priority": 1,
    }
