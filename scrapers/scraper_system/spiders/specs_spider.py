"""
Specification Corpus Spider - Scrapes PRDs, tech specs, and requirements docs

Targets:
1. Product Requirements Documents (PRDs)
2. Technical Specifications
3. Software Requirements Specifications (SRS)
4. API Specifications (OpenAPI, GraphQL schemas)
5. Feature specifications from open source projects

Critical for teaching SAM how to write and understand specifications.
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


class SpecificationSpider(BaseSpider):
    """
    Spider for specification documents.

    Extracts:
    - Product requirements documents
    - Technical specifications
    - API specifications
    - Feature specs
    - Design documents

    Usage:
        scrapy crawl specs
        scrapy crawl specs -a source=openapi
    """

    name = "specs_spider"
    source = "specifications"

    # GitHub API
    GH_API = "https://api.github.com"

    # Spec document sources
    SOURCES = {
        "openapi_specs": {
            "name": "OpenAPI Specifications",
            "type": "api_spec",
            "search_queries": [
                "openapi.yaml stars:>10",
                "openapi.json stars:>10",
                "swagger.yaml stars:>10",
                "api specification openapi",
            ],
            "file_patterns": [r"openapi\.(yaml|yml|json)$", r"swagger\.(yaml|yml|json)$"],
            "priority": 1,
        },
        "graphql_schemas": {
            "name": "GraphQL Schemas",
            "type": "api_spec",
            "search_queries": [
                "schema.graphql stars:>10",
                "graphql schema language:graphql",
            ],
            "file_patterns": [r".*\.graphql$", r"schema\.gql$"],
            "priority": 2,
        },
        "prd_templates": {
            "name": "PRD Templates",
            "type": "prd",
            "search_queries": [
                "product requirements document template",
                "PRD template markdown",
                "product spec template",
            ],
            "file_patterns": [r".*prd.*\.md$", r".*requirements.*\.md$"],
            "priority": 1,
        },
        "tech_specs": {
            "name": "Technical Specifications",
            "type": "tech_spec",
            "search_queries": [
                "technical specification document",
                "tech spec template",
                "engineering spec markdown",
            ],
            "file_patterns": [r".*spec.*\.md$", r".*design.*\.md$"],
            "priority": 1,
        },
        "feature_specs": {
            "name": "Feature Specifications",
            "type": "feature_spec",
            "github_repos": [
                "uber/ribs",
                "airbnb/lottie-ios",
                "realm/realm-swift",
            ],
            "paths": ["docs", "spec", "specifications"],
            "priority": 2,
        },
    }

    # Known spec documentation sites
    DOC_SITES = {
        "stripe_api": {
            "name": "Stripe API Docs",
            "start_urls": ["https://stripe.com/docs/api"],
            "allowed_domains": ["stripe.com"],
            "content_selector": "main, article",
            "type": "api_spec",
        },
        "github_api": {
            "name": "GitHub API Docs",
            "start_urls": ["https://docs.github.com/en/rest"],
            "allowed_domains": ["docs.github.com"],
            "content_selector": "main, article",
            "type": "api_spec",
        },
        "apple_api": {
            "name": "Apple API Guidelines",
            "start_urls": ["https://developer.apple.com/documentation/swift/swift-standard-library"],
            "allowed_domains": ["developer.apple.com"],
            "content_selector": "main, article",
            "type": "api_spec",
        },
    }

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, source: str = None, max_docs: int = 1500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_docs = int(max_docs)
        self.docs_scraped = 0
        self.seen_urls = set()

        # GitHub token
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

        # Filter source
        self.source_filter = source

    def _get_headers(self) -> dict:
        """Get GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Specs-Spider/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def start_requests(self) -> Iterator[Request]:
        """Start fetching specifications."""
        # GitHub code searches
        for source_id, config in self.SOURCES.items():
            if self.source_filter and source_id != self.source_filter:
                continue

            # Search queries
            for query in config.get("search_queries", [])[:3]:
                encoded = quote(query)
                url = f"{self.GH_API}/search/code?q={encoded}&per_page=30"

                yield self.make_request(
                    url,
                    callback=self.parse_github_search,
                    meta={
                        "source_id": source_id,
                        "config": config,
                        "query": query,
                    },
                    headers=self._get_headers()
                )

            # Specific repos
            for repo in config.get("github_repos", []):
                for path in config.get("paths", [""]):
                    url = f"{self.GH_API}/repos/{repo}/contents/{path}"
                    yield self.make_request(
                        url,
                        callback=self.parse_repo_contents,
                        meta={
                            "source_id": source_id,
                            "config": config,
                            "repo": repo,
                        },
                        headers=self._get_headers()
                    )

        # Documentation sites
        for site_id, config in self.DOC_SITES.items():
            if self.source_filter and site_id != self.source_filter:
                continue

            for url in config.get("start_urls", []):
                yield self.make_request(
                    url,
                    callback=self.parse_doc_site,
                    meta={
                        "site_id": site_id,
                        "config": config,
                        "depth": 0,
                    }
                )

    def parse_github_search(self, response: Response) -> Iterator:
        """Parse GitHub code search results."""
        source_id = response.meta.get("source_id", "")
        config = response.meta.get("config", {})

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        items = data.get("items", [])
        file_patterns = config.get("file_patterns", [])

        for item in items:
            if self.docs_scraped >= self.max_docs:
                return

            name = item.get("name", "")
            html_url = item.get("html_url", "")
            repo = item.get("repository", {}).get("full_name", "")

            # Check file pattern
            if file_patterns:
                if not any(re.match(p, name, re.IGNORECASE) for p in file_patterns):
                    continue

            if html_url in self.seen_urls:
                continue
            self.seen_urls.add(html_url)

            # Get raw URL
            raw_url = html_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

            yield self.make_request(
                raw_url,
                callback=self.parse_spec_file,
                meta={
                    "source_id": source_id,
                    "config": config,
                    "repo": repo,
                    "file_name": name,
                    "html_url": html_url,
                },
                headers=self._get_headers()
            )

    def parse_repo_contents(self, response: Response) -> Iterator:
        """Parse repository contents for spec files."""
        source_id = response.meta.get("source_id", "")
        config = response.meta.get("config", {})
        repo = response.meta.get("repo", "")

        try:
            contents = json.loads(response.text)
        except json.JSONDecodeError:
            return

        if not isinstance(contents, list):
            contents = [contents]

        file_patterns = config.get("file_patterns", [r".*\.(md|yaml|yml|json|graphql)$"])

        for item in contents:
            if self.docs_scraped >= self.max_docs:
                return

            item_type = item.get("type", "")
            name = item.get("name", "")
            download_url = item.get("download_url")
            url = item.get("url")

            if item_type == "file":
                if any(re.match(p, name, re.IGNORECASE) for p in file_patterns):
                    if download_url and download_url not in self.seen_urls:
                        self.seen_urls.add(download_url)
                        yield self.make_request(
                            download_url,
                            callback=self.parse_spec_file,
                            meta={
                                "source_id": source_id,
                                "config": config,
                                "repo": repo,
                                "file_name": name,
                            },
                            headers=self._get_headers()
                        )

            elif item_type == "dir" and url:
                yield self.make_request(
                    url,
                    callback=self.parse_repo_contents,
                    meta={
                        "source_id": source_id,
                        "config": config,
                        "repo": repo,
                    },
                    headers=self._get_headers()
                )

    def parse_spec_file(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a specification file."""
        source_id = response.meta.get("source_id", "")
        config = response.meta.get("config", {})
        repo = response.meta.get("repo", "")
        file_name = response.meta.get("file_name", "")

        content = response.text

        if not content or len(content) < 50:
            return

        self.docs_scraped += 1

        # Detect spec type
        spec_type = self._detect_spec_type(file_name, content)

        # Extract title
        title = self._extract_title(file_name, content)

        # Analyze content
        content_lower = content.lower()

        is_openapi = "openapi" in content_lower or "swagger" in content_lower
        is_graphql = "type Query" in content or "schema {" in content
        is_prd = any(marker in content_lower for marker in [
            "product requirements", "user stories", "acceptance criteria",
            "stakeholders", "business requirements",
        ])
        is_tech_spec = any(marker in content_lower for marker in [
            "technical specification", "system design", "architecture",
            "api design", "data model", "sequence diagram",
        ])

        # Extract sections
        sections = self._extract_spec_sections(content)

        yield ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata={
                "type": config.get("type", "specification"),
                "spec_type": spec_type,
                "author": repo.split("/")[0] if repo else "",
                "source_id": source_id,
                "source_name": config.get("name", ""),
                "repo": repo,
                "file_name": file_name,
                "is_openapi": is_openapi,
                "is_graphql": is_graphql,
                "is_prd": is_prd,
                "is_tech_spec": is_tech_spec,
                "sections": list(sections.keys()),
                "has_endpoints": "endpoints" in sections or is_openapi,
                "has_data_models": "models" in sections or "schema" in sections,
                "has_requirements": "requirements" in sections or is_prd,
            }
        )

    def parse_doc_site(self, response: Response) -> Iterator:
        """Parse documentation site for API specs."""
        site_id = response.meta.get("site_id", "")
        config = response.meta.get("config", {})
        depth = response.meta.get("depth", 0)
        url = response.url

        if url in self.seen_urls:
            return
        self.seen_urls.add(url)

        if self.docs_scraped >= self.max_docs:
            return

        # Extract content
        content_selector = config.get("content_selector", "main, article")
        content_elem = response.css(content_selector)

        if content_elem:
            raw_html = content_elem.get()
            content = self._clean_html(raw_html)

            if content and len(content) > 300:
                self.docs_scraped += 1

                title = response.css("title::text").get() or ""
                title = title.strip()

                # Detect API documentation patterns
                content_lower = content.lower()

                has_endpoints = bool(re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+/', content))
                has_params = "parameters" in content_lower or "arguments" in content_lower
                has_responses = "response" in content_lower or "returns" in content_lower
                has_examples = "example" in content_lower or "```" in content

                yield ScrapedItem(
                    source=self.source,
                    url=url,
                    title=title,
                    content=content,
                    metadata={
                        "type": config.get("type", "api_docs"),
                        "author": config.get("name", site_id),
                        "site": site_id,
                        "depth": depth,
                        "has_endpoints": has_endpoints,
                        "has_params": has_params,
                        "has_responses": has_responses,
                        "has_examples": has_examples,
                    }
                )

        # Follow links (limited depth)
        if depth < 2:
            allowed_domains = config.get("allowed_domains", [])

            for link in response.css("a::attr(href)").getall()[:20]:
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)

                if parsed.netloc and not any(d in parsed.netloc for d in allowed_domains):
                    continue

                if full_url in self.seen_urls:
                    continue

                # Skip non-content
                if any(skip in full_url.lower() for skip in [".pdf", ".zip", "/login", "/signup"]):
                    continue

                # Prefer API-related links
                if any(api in full_url.lower() for api in ["/api", "/reference", "/endpoint", "/docs"]):
                    yield self.make_request(
                        full_url,
                        callback=self.parse_doc_site,
                        meta={
                            "site_id": site_id,
                            "config": config,
                            "depth": depth + 1,
                        }
                    )

    def _detect_spec_type(self, filename: str, content: str) -> str:
        """Detect specification type from filename and content."""
        filename_lower = filename.lower()
        content_lower = content.lower()

        if "openapi" in filename_lower or "swagger" in filename_lower:
            return "openapi"
        if filename_lower.endswith(".graphql") or filename_lower.endswith(".gql"):
            return "graphql"
        if "prd" in filename_lower or "product" in filename_lower:
            return "prd"
        if "spec" in filename_lower or "specification" in filename_lower:
            return "tech_spec"
        if "requirements" in filename_lower:
            return "requirements"
        if "design" in filename_lower:
            return "design_doc"

        # Content-based detection
        if "openapi" in content_lower:
            return "openapi"
        if "type Query" in content:
            return "graphql"
        if "user stories" in content_lower:
            return "prd"

        return "specification"

    def _extract_title(self, filename: str, content: str) -> str:
        """Extract title from file."""
        # Try markdown heading
        match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Try YAML title
        match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Fall back to filename
        return filename.replace('.md', '').replace('-', ' ').replace('_', ' ').title()

    def _extract_spec_sections(self, content: str) -> Dict[str, bool]:
        """Extract which sections are present."""
        sections = {}

        section_patterns = [
            ("overview", r"##?\s*overview"),
            ("requirements", r"##?\s*requirements?"),
            ("endpoints", r"##?\s*(?:api\s*)?endpoints?"),
            ("models", r"##?\s*(?:data\s*)?models?"),
            ("schema", r"##?\s*schema"),
            ("authentication", r"##?\s*auth(?:entication)?"),
            ("errors", r"##?\s*errors?"),
            ("examples", r"##?\s*examples?"),
            ("testing", r"##?\s*testing"),
        ]

        for name, pattern in section_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                sections[name] = True

        return sections

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to text."""
        if not html_content:
            return ""

        text = html_content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def register():
    return {
        "name": "specs",
        "spider_class": SpecificationSpider,
        "description": "PRDs, Tech Specs & API Specs",
        "type": "planning",
        "priority": 1,
    }
