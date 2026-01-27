"""
Error Corpus Spider - Scrapes error messages, stack traces, and solutions

Critical for SAM's bug-fixing capability.

Targets:
1. Stack Overflow error-tagged questions
2. GitHub issues with error labels
3. Apple Developer Forums errors
4. Swift error documentation
5. Common iOS/macOS crash reports

Goal: Build comprehensive error→solution training data.
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


class ErrorCorpusSpider(BaseSpider):
    """
    Spider specifically for collecting error messages and solutions.

    Builds training data for debugging capability:
    - Error message patterns
    - Stack trace analysis
    - Solution patterns
    - Fix explanations

    Usage:
        scrapy crawl error_corpus
        scrapy crawl error_corpus -a platform=ios
    """

    name = "error_corpus_spider"
    source = "error_corpus"

    # Error-related search queries for Stack Overflow
    STACKOVERFLOW_ERROR_TAGS = [
        # Swift/iOS errors
        "swift+error", "ios+crash", "xcode+error", "swiftui+error",
        "swift+exception", "ios+exception", "uikit+crash",
        "core-data+error", "swift+runtime-error",
        "swift+compilation-error", "xcode+build-error",

        # Common error types
        "nil+crash+swift", "memory-leak+ios", "exc-bad-access",
        "sigabrt+ios", "thread+crash+swift",

        # Specific Swift errors
        "fatal-error+swift", "assertion-failure+swift",
        "unwrapping+nil+swift", "index-out-of-range+swift",
    ]

    # GitHub error label searches
    GITHUB_ERROR_LABELS = [
        "bug", "crash", "error", "exception",
        "fatal", "regression", "breaking",
    ]

    # Apple-specific error patterns
    APPLE_ERROR_PATTERNS = [
        # Runtime errors
        r"Thread \d+: Fatal error",
        r"Thread \d+: EXC_BAD_ACCESS",
        r"Thread \d+: signal SIGABRT",
        r"Terminating app due to uncaught exception",

        # Swift errors
        r"Fatal error: .*",
        r"Precondition failed: .*",
        r"Assertion failed: .*",
        r"fatalError\(.*\)",

        # Build errors
        r"error: .*",
        r"Cannot find .* in scope",
        r"Type .* has no member .*",
        r"Value of type .* has no member .*",
        r"Missing argument for parameter .*",

        # Common crashes
        r"unexpectedly found nil",
        r"Index out of range",
        r"Array index is out of range",
        r"force unwrap",
    ]

    # Stack Exchange API
    SO_API = "https://api.stackexchange.com/2.3"

    # GitHub API
    GH_API = "https://api.github.com"

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, platform: str = "all", max_errors: int = 2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_errors = int(max_errors)
        self.errors_scraped = 0
        self.seen_urls = set()
        self.platform = platform

        # GitHub token
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

    def start_requests(self) -> Iterator[Request]:
        """Start collecting error corpus."""
        # Stack Overflow error questions
        for tag_combo in self.STACKOVERFLOW_ERROR_TAGS:
            tags = tag_combo.replace("+", ";")
            url = f"{self.SO_API}/questions?order=desc&sort=votes&tagged={tags}&site=stackoverflow&filter=withbody&pagesize=50"

            yield self.make_request(
                url,
                callback=self.parse_stackoverflow,
                meta={"tags": tag_combo}
            )

        # GitHub issues with error labels
        for label in self.GITHUB_ERROR_LABELS:
            # Search in Swift repos
            query = quote(f"label:{label} language:swift state:closed")
            url = f"{self.GH_API}/search/issues?q={query}&sort=comments&order=desc&per_page=30"

            yield self.make_request(
                url,
                callback=self.parse_github_issues,
                meta={"label": label},
                headers=self._get_github_headers()
            )

        # Apple Developer documentation for errors
        error_doc_urls = [
            "https://developer.apple.com/documentation/swift/error",
            "https://developer.apple.com/documentation/foundation/nserror",
            "https://developer.apple.com/documentation/swift/decodingerror",
            "https://developer.apple.com/documentation/swift/encodingerror",
        ]

        for url in error_doc_urls:
            yield self.make_request(
                url,
                callback=self.parse_apple_error_docs,
                meta={"doc_type": "error_handling"}
            )

    def _get_github_headers(self) -> dict:
        """Get GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Error-Corpus/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def parse_stackoverflow(self, response: Response) -> Iterator:
        """Parse Stack Overflow error questions."""
        tags = response.meta.get("tags", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse SO response for {tags}")
            return

        questions = data.get("items", [])

        for question in questions:
            if self.errors_scraped >= self.max_errors:
                return

            question_id = question.get("question_id")
            url = f"https://stackoverflow.com/questions/{question_id}"

            if url in self.seen_urls:
                continue
            self.seen_urls.add(url)

            title = html.unescape(question.get("title", ""))
            body = html.unescape(question.get("body", ""))

            # Extract error patterns from body
            errors_found = self._extract_errors(body)

            if not errors_found:
                continue

            self.errors_scraped += 1

            # Fetch answers
            yield self.make_request(
                f"{self.SO_API}/questions/{question_id}/answers?order=desc&sort=votes&site=stackoverflow&filter=withbody",
                callback=self.parse_so_answers,
                meta={
                    "question": question,
                    "title": title,
                    "body": body,
                    "errors": errors_found,
                    "tags": tags,
                    "url": url,
                }
            )

    def parse_so_answers(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse Stack Overflow answers for error solutions."""
        meta = response.meta

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        answers = data.get("items", [])

        # Build error→solution content
        content = f"## Error Question: {meta['title']}\n\n"
        content += f"### Problem:\n{meta['body'][:2000]}\n\n"
        content += f"### Errors Detected:\n"
        for error in meta['errors']:
            content += f"- `{error}`\n"
        content += "\n### Solutions:\n\n"

        for i, answer in enumerate(answers[:3]):  # Top 3 answers
            is_accepted = answer.get("is_accepted", False)
            score = answer.get("score", 0)
            body = html.unescape(answer.get("body", ""))

            marker = "✓ ACCEPTED" if is_accepted else f"({score} votes)"
            content += f"**Answer {i+1}** {marker}:\n{body[:1500]}\n\n"

        if answers:
            yield ScrapedItem(
                source=self.source,
                url=meta['url'],
                title=f"Error: {meta['title']}",
                content=content,
                metadata={
                    "type": "error_qa",
                    "author": meta['question'].get("owner", {}).get("display_name", ""),
                    "errors": meta['errors'],
                    "tags": meta['question'].get("tags", []),
                    "score": meta['question'].get("score", 0),
                    "has_accepted_answer": any(a.get("is_accepted") for a in answers),
                    "answer_count": len(answers),
                }
            )

    def parse_github_issues(self, response: Response) -> Iterator:
        """Parse GitHub issues with error labels."""
        label = response.meta.get("label", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        issues = data.get("items", [])

        for issue in issues:
            if self.errors_scraped >= self.max_errors:
                return

            url = issue.get("html_url", "")
            if url in self.seen_urls:
                continue
            self.seen_urls.add(url)

            title = issue.get("title", "")
            body = issue.get("body", "") or ""

            # Extract errors
            errors_found = self._extract_errors(body)

            # Get repo info from URL
            # Format: https://github.com/owner/repo/issues/123
            parts = url.split("/")
            if len(parts) >= 5:
                owner = parts[3]
                repo = parts[4]
                issue_number = parts[-1]

                # Fetch comments (solutions)
                comments_url = f"{self.GH_API}/repos/{owner}/{repo}/issues/{issue_number}/comments"

                yield self.make_request(
                    comments_url,
                    callback=self.parse_github_comments,
                    meta={
                        "issue": issue,
                        "errors": errors_found,
                        "url": url,
                        "repo": f"{owner}/{repo}",
                    },
                    headers=self._get_github_headers()
                )

    def parse_github_comments(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse GitHub issue comments for solutions."""
        meta = response.meta
        issue = meta["issue"]

        try:
            comments = json.loads(response.text)
        except json.JSONDecodeError:
            comments = []

        # Build error→solution content
        title = issue.get("title", "")
        body = issue.get("body", "") or ""

        content = f"## Bug Report: {title}\n\n"
        content += f"### Problem:\n{body[:2000]}\n\n"

        if meta["errors"]:
            content += "### Errors Detected:\n"
            for error in meta["errors"][:5]:
                content += f"- `{error}`\n"
            content += "\n"

        content += "### Discussion & Solutions:\n\n"

        solution_markers = ["fixed", "solved", "solution", "resolved", "workaround", "try this"]
        has_solution = False

        for comment in comments[:10]:
            author = comment.get("user", {}).get("login", "unknown")
            comment_body = comment.get("body", "")

            # Check if this looks like a solution
            is_solution = any(marker in comment_body.lower() for marker in solution_markers)
            if is_solution:
                has_solution = True
                content += f"**{author}** (SOLUTION):\n{comment_body[:1000]}\n\n"
            else:
                content += f"**{author}**:\n{comment_body[:500]}\n\n"

        self.errors_scraped += 1

        yield ScrapedItem(
            source=self.source,
            url=meta["url"],
            title=f"Bug: {title}",
            content=content,
            metadata={
                "type": "error_issue",
                "author": issue.get("user", {}).get("login", ""),
                "repo": meta["repo"],
                "errors": meta["errors"],
                "labels": [l.get("name") for l in issue.get("labels", [])],
                "state": issue.get("state", ""),
                "has_solution": has_solution,
                "comments_count": len(comments),
            }
        )

    def parse_apple_error_docs(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse Apple error handling documentation."""
        doc_type = response.meta.get("doc_type", "")
        url = response.url

        if url in self.seen_urls:
            return
        self.seen_urls.add(url)

        # Extract content
        content_elem = response.css("main, article, .content")
        if not content_elem:
            return

        raw_html = content_elem.get()
        content = self._clean_html(raw_html)

        if len(content) < 200:
            return

        title = response.css("title::text").get() or "Apple Error Documentation"
        title = title.strip()

        self.errors_scraped += 1

        yield ScrapedItem(
            source=self.source,
            url=url,
            title=title,
            content=content,
            metadata={
                "type": "error_documentation",
                "author": "Apple Inc.",
                "doc_type": doc_type,
                "is_official": True,
            }
        )

        # Follow error-related links
        for link in response.css("a::attr(href)").getall():
            if any(err in link.lower() for err in ["error", "exception", "throw", "catch"]):
                full_url = urljoin(url, link)
                if "developer.apple.com" in full_url and full_url not in self.seen_urls:
                    yield self.make_request(
                        full_url,
                        callback=self.parse_apple_error_docs,
                        meta={"doc_type": "error_handling"}
                    )

    def _extract_errors(self, text: str) -> List[str]:
        """Extract error patterns from text."""
        errors = []

        for pattern in self.APPLE_ERROR_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            errors.extend(matches)

        # Also look for code blocks that might contain errors
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        for block in code_blocks:
            # Check for error indicators
            if any(err in block.lower() for err in ["error", "fatal", "crash", "exception", "failed"]):
                # Extract the key error line
                lines = block.split('\n')
                for line in lines:
                    if any(err in line.lower() for err in ["error:", "fatal error:", "exception:", "crash:"]):
                        errors.append(line.strip()[:200])

        # Deduplicate
        return list(set(errors))[:10]

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to text."""
        if not html_content:
            return ""

        text = html_content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class SwiftErrorDatabaseSpider(BaseSpider):
    """
    Spider for building Swift-specific error database.

    Scrapes:
    - Swift compiler error messages
    - SwiftLint rules and fixes
    - Common Swift pitfalls
    """

    name = "swift_error_db_spider"
    source = "swift_error_db"

    # Swift error documentation sources
    SOURCES = [
        {
            "url": "https://github.com/apple/swift/tree/main/include/swift/AST/DiagnosticsSema.def",
            "type": "compiler_errors",
        },
        {
            "url": "https://realm.github.io/SwiftLint/rule-directory.html",
            "type": "swiftlint_rules",
        },
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

    def start_requests(self) -> Iterator[Request]:
        """Start scraping Swift error sources."""
        # SwiftLint rules page
        yield self.make_request(
            "https://realm.github.io/SwiftLint/rule-directory.html",
            callback=self.parse_swiftlint_rules,
        )

    def parse_swiftlint_rules(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse SwiftLint rules as error patterns."""
        # Extract rules from the page
        rules = response.css(".rule-container, article")

        for rule in rules:
            name = rule.css("h2::text, h3::text").get()
            description = rule.css("p::text").get()

            if name and description:
                content = f"# SwiftLint Rule: {name}\n\n{description}"

                # Look for code examples
                code = rule.css("pre code::text").get()
                if code:
                    content += f"\n\n## Example:\n```swift\n{code}\n```"

                yield ScrapedItem(
                    source=self.source,
                    url=response.url + f"#{name.lower().replace(' ', '-')}",
                    title=f"SwiftLint: {name}",
                    content=content,
                    metadata={
                        "type": "lint_rule",
                        "author": "SwiftLint",
                        "rule_name": name,
                    }
                )


def register():
    return [
        {
            "name": "error_corpus",
            "spider_class": ErrorCorpusSpider,
            "description": "Error Messages & Solutions",
            "type": "code",
            "priority": 1,
        },
        {
            "name": "swift_error_db",
            "spider_class": SwiftErrorDatabaseSpider,
            "description": "Swift Error Database",
            "type": "code",
            "priority": 2,
        },
    ]
