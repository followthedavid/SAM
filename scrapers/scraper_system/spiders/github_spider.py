"""
GitHub Spider - Scrapes READMEs, Issues, and Installation Docs

Targets:
1. Popular repository READMEs (installation instructions)
2. Issues with solutions (bug fixing patterns)
3. Discussions (troubleshooting)

Uses GitHub API where possible for efficiency.
"""

import json
import logging
import os
import re
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class GitHubSpider(BaseSpider):
    """
    Spider for GitHub content - READMEs, issues, and docs.

    Usage:
        # Scrape popular repos
        scrapy crawl github

        # Scrape specific topics
        scrapy crawl github -a topics="homebrew,cli,installer"

        # Scrape issues for debugging patterns
        scrapy crawl github -a mode=issues
    """

    name = "github_spider"
    source = "github"

    # GitHub API base
    API_BASE = "https://api.github.com"

    # Topics relevant for app installer training
    INSTALLER_TOPICS = [
        "homebrew", "apt", "package-manager", "installer",
        "cli", "command-line", "terminal", "shell",
        "automation", "setup", "dotfiles", "bootstrap",
        "macos", "linux", "windows", "cross-platform",
    ]

    # Topics for debugging/bug fixing
    DEBUG_TOPICS = [
        "debugging", "error-handling", "troubleshooting",
        "testing", "ci-cd", "github-actions",
    ]

    # Topics for UI testing
    UI_TOPICS = [
        "ui-testing", "e2e-testing", "accessibility", "a11y",
        "selenium", "playwright", "cypress", "puppeteer",
        "screenshot", "visual-testing",
    ]

    # Languages to focus on (beginner-friendly)
    LANGUAGES = ["python", "javascript", "typescript", "shell", "go", "rust"]

    # Mode: readme, issues, discussions, all
    MODE_README = "readme"
    MODE_ISSUES = "issues"
    MODE_ALL = "all"

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,  # GitHub API has rate limits
        "CONCURRENT_REQUESTS": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Training-Bot/1.0 (Research Project)",
        },
    }

    def __init__(self, *args, mode: str = "all", topics: str = None,
                 min_stars: int = 100, max_repos: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.min_stars = int(min_stars)
        self.max_repos = int(max_repos)
        self.repos_scraped = 0

        # Parse custom topics or use defaults
        if topics:
            self.topics = [t.strip() for t in topics.split(",")]
        else:
            self.topics = self.INSTALLER_TOPICS + self.DEBUG_TOPICS + self.UI_TOPICS

        # Get GitHub token from environment
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        if self.github_token:
            logger.info("Using GitHub token for higher rate limits")
        else:
            logger.warning("No GITHUB_TOKEN set - rate limits will be lower (60/hour)")

    def _get_headers(self) -> dict:
        """Get headers including auth token if available."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Training-Bot/1.0 (Research Project)",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def start_requests(self) -> Iterator[Request]:
        """Start by searching for repos by topic."""
        for topic in self.topics:
            # Search for repos with this topic
            url = f"{self.API_BASE}/search/repositories"
            params = {
                "q": f"topic:{topic} stars:>{self.min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": 30,
            }
            query_string = "&".join(f"{k}={v}" for k, v in params.items())

            yield self.make_request(
                f"{url}?{query_string}",
                callback=self.parse_search_results,
                meta={"topic": topic, "page": 1},
                headers=self._get_headers()
            )

    def parse_search_results(self, response: Response) -> Iterator:
        """Parse GitHub search results."""
        topic = response.meta.get("topic", "unknown")
        page = response.meta.get("page", 1)

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {response.url}")
            return

        repos = data.get("items", [])
        logger.info(f"Found {len(repos)} repos for topic '{topic}' (page {page})")

        for repo in repos:
            if self.repos_scraped >= self.max_repos:
                logger.info(f"Reached max repos limit ({self.max_repos})")
                return

            owner = repo.get("owner", {}).get("login", "")
            name = repo.get("name", "")
            full_name = f"{owner}/{name}"

            # Skip if already scraped
            if self._db and self._db.url_exists(f"https://github.com/{full_name}"):
                continue

            self.repos_scraped += 1

            # Fetch README
            if self.mode in [self.MODE_README, self.MODE_ALL]:
                yield self.make_request(
                    f"{self.API_BASE}/repos/{full_name}/readme",
                    callback=self.parse_readme,
                    meta={"repo": repo, "topic": topic}, headers=self._get_headers()
                )

            # Fetch issues with solutions
            if self.mode in [self.MODE_ISSUES, self.MODE_ALL]:
                # Get closed issues with "bug" or "help" labels
                yield self.make_request(
                    f"{self.API_BASE}/repos/{full_name}/issues?state=closed&labels=bug&per_page=20",
                    callback=self.parse_issues,
                    meta={"repo": repo, "topic": topic, "label": "bug"}, headers=self._get_headers()
                )

        # Pagination
        if len(repos) == 30 and page < 5:  # Max 5 pages per topic
            next_url = response.url.replace(f"page={page}", f"page={page+1}")
            if f"page=" not in response.url:
                next_url = f"{response.url}&page={page+1}"

            yield self.make_request(
                next_url,
                callback=self.parse_search_results,
                meta={"topic": topic, "page": page + 1}, headers=self._get_headers()
            )

    def parse_readme(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a repository README."""
        repo = response.meta.get("repo", {})
        topic = response.meta.get("topic", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        # README content is base64 encoded
        import base64
        content_b64 = data.get("content", "")
        try:
            content = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        except Exception:
            return

        if not content or len(content) < 100:
            return

        # Extract installation section if present
        installation_section = self._extract_installation_section(content)

        full_name = repo.get("full_name", "unknown")

        yield ScrapedItem(
            source=self.source,
            url=f"https://github.com/{full_name}",
            title=f"README: {full_name}",
            content=content,
            metadata={
                "type": "readme",
                "author": repo.get("owner", {}).get("login", ""),
                "topic": topic,
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language", ""),
                "description": repo.get("description", ""),
                "has_installation": bool(installation_section),
                "installation_section": installation_section,
                "topics": repo.get("topics", []),
                "license": repo.get("license", {}).get("spdx_id", "") if repo.get("license") else "",
            }
        )

    def _extract_installation_section(self, content: str) -> str:
        """Extract installation/setup section from README."""
        # Common installation section headers
        patterns = [
            r"#+\s*(?:Installation|Install|Getting Started|Setup|Quick Start|Prerequisites)\s*\n(.*?)(?=\n#+|\Z)",
            r"\*\*(?:Installation|Install|Setup)\*\*\s*\n(.*?)(?=\n\*\*|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                section = match.group(1).strip()
                # Limit to reasonable size
                if len(section) > 100:
                    return section[:5000]

        return ""

    def parse_issues(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse closed issues (solved bugs)."""
        repo = response.meta.get("repo", {})
        topic = response.meta.get("topic", "")
        label = response.meta.get("label", "")

        try:
            issues = json.loads(response.text)
        except json.JSONDecodeError:
            return

        full_name = repo.get("full_name", "unknown")

        for issue in issues:
            # Only issues with comments (likely has solution)
            if issue.get("comments", 0) < 1:
                continue

            issue_number = issue.get("number", 0)

            # Fetch comments for this issue
            yield self.make_request(
                f"{self.API_BASE}/repos/{full_name}/issues/{issue_number}/comments",
                callback=self.parse_issue_comments,
                meta={
                    "repo": repo,
                    "issue": issue,
                    "topic": topic,
                    "label": label,
                }
            )

    def parse_issue_comments(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse issue with its comments (problem + solution pattern)."""
        repo = response.meta.get("repo", {})
        issue = response.meta.get("issue", {})
        topic = response.meta.get("topic", "")
        label = response.meta.get("label", "")

        try:
            comments = json.loads(response.text)
        except json.JSONDecodeError:
            return

        if not comments:
            return

        full_name = repo.get("full_name", "unknown")
        issue_number = issue.get("number", 0)

        # Build conversation: issue + comments
        conversation = f"## Issue: {issue.get('title', '')}\n\n"
        conversation += f"**Reporter:** {issue.get('user', {}).get('login', 'unknown')}\n\n"
        conversation += issue.get("body", "") or "(no description)"
        conversation += "\n\n---\n\n## Comments:\n\n"

        for i, comment in enumerate(comments[:10]):  # Max 10 comments
            author = comment.get("user", {}).get("login", "unknown")
            body = comment.get("body", "")
            conversation += f"**{author}:** {body}\n\n"

        # Analyze if this looks like a solved bug
        content_lower = conversation.lower()
        has_solution_markers = any(marker in content_lower for marker in [
            "fixed", "solved", "solution", "worked", "thank",
            "this worked", "that fixed", "resolved",
        ])

        has_error_markers = any(marker in content_lower for marker in [
            "error", "exception", "traceback", "failed", "crash",
            "bug", "issue", "problem", "not working",
        ])

        yield ScrapedItem(
            source=self.source,
            url=f"https://github.com/{full_name}/issues/{issue_number}",
            title=f"Issue #{issue_number}: {issue.get('title', '')}",
            content=conversation,
            metadata={
                "type": "issue",
                "author": issue.get("user", {}).get("login", ""),
                "topic": topic,
                "label": label,
                "repo": full_name,
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language", ""),
                "state": issue.get("state", ""),
                "comments_count": len(comments),
                "has_solution_markers": has_solution_markers,
                "has_error_markers": has_error_markers,
                "labels": [l.get("name", "") for l in issue.get("labels", [])],
            }
        )


# Register with the spider registry
def register():
    return {
        "name": "github",
        "spider_class": GitHubSpider,
        "description": "GitHub READMEs and Issues",
        "type": "code",
        "priority": 1,
    }
