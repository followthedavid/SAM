"""
Architecture Patterns Spider - Scrapes design docs, RFCs, and ADRs

Targets:
1. GitHub Architecture Decision Records (ADRs)
2. RFCs from major projects (Swift Evolution, React, Rust)
3. System design documentation
4. Architecture pattern repositories
5. Technical design documents

Critical for teaching SAM how to plan software architecture.
"""

import json
import logging
import html
import re
import os
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse, quote

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class ArchitectureSpider(BaseSpider):
    """
    Spider for architecture documentation and decision records.

    Extracts:
    - Architecture Decision Records (ADRs)
    - Request for Comments (RFCs)
    - System design documents
    - Architecture patterns
    - Technical specifications

    Usage:
        scrapy crawl architecture
        scrapy crawl architecture -a source=swift_evolution
    """

    name = "architecture_spider"
    source = "architecture"

    # GitHub API
    GH_API = "https://api.github.com"

    # Architecture document sources
    SOURCES = {
        "swift_evolution": {
            "name": "Swift Evolution",
            "type": "rfc",
            "github_repo": "apple/swift-evolution",
            "paths": ["proposals"],
            "file_pattern": r".*\.md$",
            "priority": 1,
        },
        "react_rfcs": {
            "name": "React RFCs",
            "type": "rfc",
            "github_repo": "reactjs/rfcs",
            "paths": ["text"],
            "file_pattern": r".*\.md$",
            "priority": 2,
        },
        "rust_rfcs": {
            "name": "Rust RFCs",
            "type": "rfc",
            "github_repo": "rust-lang/rfcs",
            "paths": ["text"],
            "file_pattern": r".*\.md$",
            "priority": 2,
        },
        "adr_examples": {
            "name": "ADR Examples",
            "type": "adr",
            "github_repo": "joelparkerhenderson/architecture-decision-record",
            "paths": ["examples", "locales/en/templates"],
            "file_pattern": r".*\.md$",
            "priority": 1,
        },
        "system_design": {
            "name": "System Design Primer",
            "type": "design",
            "github_repo": "donnemartin/system-design-primer",
            "paths": [""],
            "file_pattern": r".*\.md$",
            "priority": 1,
        },
        "ios_architecture": {
            "name": "iOS Clean Architecture",
            "type": "architecture",
            "github_repo": "kudoleh/iOS-Clean-Architecture-MVVM",
            "paths": [""],
            "file_pattern": r".*\.md$",
            "priority": 1,
        },
        "swift_composable": {
            "name": "Swift Composable Architecture",
            "type": "architecture",
            "github_repo": "pointfreeco/swift-composable-architecture",
            "paths": ["Sources", ""],
            "file_pattern": r".*\.md$",
            "priority": 1,
        },
        "vapor_docs": {
            "name": "Vapor Framework",
            "type": "architecture",
            "github_repo": "vapor/docs",
            "paths": ["docs"],
            "file_pattern": r".*\.md$",
            "priority": 2,
        },
    }

    # ADR search queries
    ADR_SEARCH_QUERIES = [
        "architecture decision record",
        "ADR template",
        "filename:adr",
        "filename:architecture-decision",
        "path:docs/adr",
        "path:architecture/decisions",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, source: str = None, max_docs: int = 2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_docs = int(max_docs)
        self.docs_scraped = 0
        self.seen_urls = set()

        # GitHub token
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

        # Filter sources
        if source and source in self.SOURCES:
            self.sources = {source: self.SOURCES[source]}
        else:
            self.sources = self.SOURCES

    def _get_headers(self) -> dict:
        """Get GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Architecture-Spider/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def start_requests(self) -> Iterator[Request]:
        """Start fetching architecture documents."""
        # Fetch from configured repos
        for source_id, config in self.sources.items():
            repo = config.get("github_repo")
            if repo:
                for path in config.get("paths", [""]):
                    url = f"{self.GH_API}/repos/{repo}/contents/{path}"
                    yield self.make_request(
                        url,
                        callback=self.parse_github_contents,
                        meta={
                            "source_id": source_id,
                            "config": config,
                            "repo": repo,
                            "path": path,
                        },
                        headers=self._get_headers()
                    )

        # Also search for ADRs across GitHub
        for query in self.ADR_SEARCH_QUERIES[:3]:  # Limit queries
            encoded_query = quote(f"{query} language:markdown")
            url = f"{self.GH_API}/search/code?q={encoded_query}&per_page=30"
            yield self.make_request(
                url,
                callback=self.parse_adr_search,
                meta={"query": query},
                headers=self._get_headers()
            )

    def parse_github_contents(self, response: Response) -> Iterator:
        """Parse GitHub repository contents."""
        source_id = response.meta.get("source_id", "")
        config = response.meta.get("config", {})
        repo = response.meta.get("repo", "")

        try:
            contents = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse GitHub contents for {repo}")
            return

        if not isinstance(contents, list):
            contents = [contents]

        file_pattern = config.get("file_pattern", r".*\.md$")

        for item in contents:
            if self.docs_scraped >= self.max_docs:
                return

            item_type = item.get("type", "")
            name = item.get("name", "")
            path = item.get("path", "")

            if item_type == "file" and re.match(file_pattern, name, re.IGNORECASE):
                # Fetch file content
                download_url = item.get("download_url")
                if download_url and download_url not in self.seen_urls:
                    self.seen_urls.add(download_url)
                    yield self.make_request(
                        download_url,
                        callback=self.parse_markdown_file,
                        meta={
                            "source_id": source_id,
                            "config": config,
                            "repo": repo,
                            "file_path": path,
                            "file_name": name,
                        },
                        headers=self._get_headers()
                    )

            elif item_type == "dir":
                # Recurse into directory
                dir_url = item.get("url")
                if dir_url:
                    yield self.make_request(
                        dir_url,
                        callback=self.parse_github_contents,
                        meta={
                            "source_id": source_id,
                            "config": config,
                            "repo": repo,
                            "path": path,
                        },
                        headers=self._get_headers()
                    )

    def parse_adr_search(self, response: Response) -> Iterator:
        """Parse GitHub code search results for ADRs."""
        query = response.meta.get("query", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        items = data.get("items", [])

        for item in items:
            if self.docs_scraped >= self.max_docs:
                return

            html_url = item.get("html_url", "")
            repo = item.get("repository", {}).get("full_name", "")
            path = item.get("path", "")
            name = item.get("name", "")

            if html_url in self.seen_urls:
                continue
            self.seen_urls.add(html_url)

            # Convert HTML URL to raw URL
            raw_url = html_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

            yield self.make_request(
                raw_url,
                callback=self.parse_markdown_file,
                meta={
                    "source_id": "adr_search",
                    "config": {"name": "ADR Search", "type": "adr"},
                    "repo": repo,
                    "file_path": path,
                    "file_name": name,
                    "search_query": query,
                },
                headers=self._get_headers()
            )

    def parse_markdown_file(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a markdown architecture document."""
        source_id = response.meta.get("source_id", "")
        config = response.meta.get("config", {})
        repo = response.meta.get("repo", "")
        file_path = response.meta.get("file_path", "")
        file_name = response.meta.get("file_name", "")

        content = response.text

        if not content or len(content) < 100:
            return

        self.docs_scraped += 1

        # Extract title from first heading or filename
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_name.replace('.md', '').replace('-', ' ').title()

        # Analyze document type
        content_lower = content.lower()

        is_adr = any(marker in content_lower for marker in [
            "decision", "status:", "context:", "consequences:",
            "architecture decision", "adr-", "we will", "we decided",
        ])

        is_rfc = any(marker in content_lower for marker in [
            "rfc", "proposal", "motivation:", "detailed design",
            "alternatives considered", "prior art",
        ])

        is_design_doc = any(marker in content_lower for marker in [
            "design doc", "technical design", "system design",
            "architecture overview", "high-level design",
        ])

        # Extract key sections
        sections = self._extract_sections(content)

        # Detect status (for ADRs/RFCs)
        status = self._extract_status(content)

        # Detect decision/proposal number
        doc_number = self._extract_doc_number(file_name, content)

        yield ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata={
                "type": config.get("type", "architecture"),
                "author": repo.split("/")[0] if "/" in repo else repo,
                "source_id": source_id,
                "source_name": config.get("name", ""),
                "repo": repo,
                "file_path": file_path,
                "is_adr": is_adr,
                "is_rfc": is_rfc,
                "is_design_doc": is_design_doc,
                "status": status,
                "doc_number": doc_number,
                "sections": list(sections.keys()),
                "has_context": "context" in sections,
                "has_decision": "decision" in sections,
                "has_consequences": "consequences" in sections,
                "has_alternatives": "alternatives" in sections,
            }
        )

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract named sections from document."""
        sections = {}

        # Common section patterns
        section_patterns = [
            (r'##?\s*context\s*\n(.*?)(?=\n##|\Z)', 'context'),
            (r'##?\s*decision\s*\n(.*?)(?=\n##|\Z)', 'decision'),
            (r'##?\s*consequences?\s*\n(.*?)(?=\n##|\Z)', 'consequences'),
            (r'##?\s*alternatives?\s*(?:considered)?\s*\n(.*?)(?=\n##|\Z)', 'alternatives'),
            (r'##?\s*status\s*\n(.*?)(?=\n##|\Z)', 'status'),
            (r'##?\s*motivation\s*\n(.*?)(?=\n##|\Z)', 'motivation'),
            (r'##?\s*(?:detailed\s*)?design\s*\n(.*?)(?=\n##|\Z)', 'design'),
            (r'##?\s*(?:proposed\s*)?solution\s*\n(.*?)(?=\n##|\Z)', 'solution'),
        ]

        for pattern, name in section_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                sections[name] = match.group(1).strip()[:1000]

        return sections

    def _extract_status(self, content: str) -> Optional[str]:
        """Extract document status."""
        status_patterns = [
            r'status[:\s]+([a-z]+)',
            r'\*\*status\*\*[:\s]+([a-z]+)',
            r'^\s*-\s*status[:\s]+([a-z]+)',
        ]

        for pattern in status_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).lower()

        # Check for status keywords
        content_lower = content.lower()
        if "accepted" in content_lower[:500]:
            return "accepted"
        elif "rejected" in content_lower[:500]:
            return "rejected"
        elif "proposed" in content_lower[:500]:
            return "proposed"
        elif "implemented" in content_lower[:500]:
            return "implemented"

        return None

    def _extract_doc_number(self, filename: str, content: str) -> Optional[str]:
        """Extract document number."""
        # From filename
        num_match = re.search(r'(\d{3,4})', filename)
        if num_match:
            return num_match.group(1)

        # From content (SE-0001 style)
        se_match = re.search(r'(SE-\d{4}|RFC-?\d+|ADR-?\d+)', content, re.IGNORECASE)
        if se_match:
            return se_match.group(1).upper()

        return None


def register():
    return {
        "name": "architecture",
        "spider_class": ArchitectureSpider,
        "description": "Architecture Patterns & ADRs",
        "type": "planning",
        "priority": 1,
    }
