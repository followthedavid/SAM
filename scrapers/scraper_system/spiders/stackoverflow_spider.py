"""
Stack Overflow Spider - Scrapes Q&A for debugging/error patterns

Targets:
1. Questions with accepted answers (solved problems)
2. Error messages and their solutions
3. Installation/setup questions
4. Beginner-friendly content

Uses Stack Exchange API for efficiency.
"""

import json
import logging
import html
import re
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlencode

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class StackOverflowSpider(BaseSpider):
    """
    Spider for Stack Overflow Q&A content.

    Focuses on:
    - Installation/setup questions
    - Error resolution
    - Beginner-friendly content
    - Accepted answers (verified solutions)

    Usage:
        # Scrape general programming Q&A
        scrapy crawl stackoverflow

        # Focus on specific tags
        scrapy crawl stackoverflow -a tags="homebrew,macos,installation"

        # Focus on error messages
        scrapy crawl stackoverflow -a mode=errors
    """

    name = "stackoverflow_spider"
    source = "stackoverflow"

    # Stack Exchange API
    API_BASE = "https://api.stackexchange.com/2.3"
    SITE = "stackoverflow"

    # Tags for app installation/setup (what SAM needs to know)
    INSTALLER_TAGS = [
        "homebrew", "apt", "apt-get", "pip", "npm", "yarn",
        "installation", "setup", "configuration", "environment-variables",
        "path", "command-line", "terminal", "bash", "zsh", "shell",
        "macos", "linux", "ubuntu", "windows", "wsl",
        "python", "node.js", "docker", "git",
    ]

    # Tags for debugging/errors
    ERROR_TAGS = [
        "error-handling", "debugging", "exception", "stack-trace",
        "runtime-error", "syntax-error", "import-error", "module-not-found",
        "permission-denied", "file-not-found", "connection-refused",
        "segmentation-fault", "memory-leak", "null-pointer",
    ]

    # Tags for UI testing
    UI_TAGS = [
        "selenium", "playwright", "cypress", "puppeteer",
        "web-scraping", "automation", "testing", "e2e-testing",
        "accessibility", "screen-reader", "aria",
    ]

    # Filter for beginner content
    BEGINNER_KEYWORDS = [
        "how to", "what is", "why does", "getting started",
        "beginner", "simple", "basic", "tutorial", "example",
        "first time", "new to", "help understanding",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.5,  # Stack API is generous
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, mode: str = "all", tags: str = None,
                 min_score: int = 5, max_questions: int = 2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.min_score = int(min_score)
        self.max_questions = int(max_questions)
        self.questions_scraped = 0

        # Parse custom tags or use defaults
        if tags:
            self.tags = [t.strip() for t in tags.split(",")]
        else:
            self.tags = self.INSTALLER_TAGS + self.ERROR_TAGS + self.UI_TAGS

        # API key (optional but increases quota)
        import os
        self.api_key = os.environ.get("STACK_API_KEY", "")

    def start_requests(self) -> Iterator[Request]:
        """Start by fetching questions for each tag."""
        for tag in self.tags:
            params = {
                "order": "desc",
                "sort": "votes",
                "tagged": tag,
                "site": self.SITE,
                "filter": "withbody",  # Include question body
                "pagesize": 50,
                "page": 1,
            }
            if self.api_key:
                params["key"] = self.api_key

            url = f"{self.API_BASE}/questions?{urlencode(params)}"

            yield self.make_request(
                url,
                callback=self.parse_questions,
                meta={"tag": tag, "page": 1, "params": params}
            )

    def parse_questions(self, response: Response) -> Iterator:
        """Parse Stack Overflow questions."""
        tag = response.meta.get("tag", "unknown")
        page = response.meta.get("page", 1)
        params = response.meta.get("params", {})

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {response.url}")
            return

        questions = data.get("items", [])
        has_more = data.get("has_more", False)
        quota_remaining = data.get("quota_remaining", 0)

        logger.info(f"Tag '{tag}' page {page}: {len(questions)} questions, quota: {quota_remaining}")

        for q in questions:
            if self.questions_scraped >= self.max_questions:
                logger.info(f"Reached max questions limit ({self.max_questions})")
                return

            # Filter by score
            if q.get("score", 0) < self.min_score:
                continue

            # Must have accepted answer
            if not q.get("accepted_answer_id"):
                continue

            question_id = q.get("question_id")

            # Skip if already scraped
            url = f"https://stackoverflow.com/questions/{question_id}"
            if self._db and self._db.url_exists(url):
                continue

            self.questions_scraped += 1

            # Fetch the question with its answers
            answer_params = {
                "order": "desc",
                "sort": "votes",
                "site": self.SITE,
                "filter": "withbody",
            }
            if self.api_key:
                answer_params["key"] = self.api_key

            yield self.make_request(
                f"{self.API_BASE}/questions/{question_id}/answers?{urlencode(answer_params)}",
                callback=self.parse_answers,
                meta={"question": q, "tag": tag}
            )

        # Pagination (max 5 pages per tag to avoid quota exhaustion)
        if has_more and page < 5 and quota_remaining > 100:
            params["page"] = page + 1
            next_url = f"{self.API_BASE}/questions?{urlencode(params)}"

            yield self.make_request(
                next_url,
                callback=self.parse_questions,
                meta={"tag": tag, "page": page + 1, "params": params}
            )

    def parse_answers(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse answers and yield the complete Q&A."""
        question = response.meta.get("question", {})
        tag = response.meta.get("tag", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        answers = data.get("items", [])
        if not answers:
            return

        question_id = question.get("question_id")
        accepted_answer_id = question.get("accepted_answer_id")

        # Build the Q&A content
        title = html.unescape(question.get("title", ""))
        question_body = self._clean_html(question.get("body", ""))

        content = f"# {title}\n\n"
        content += f"**Tags:** {', '.join(question.get('tags', []))}\n"
        content += f"**Score:** {question.get('score', 0)} | **Views:** {question.get('view_count', 0)}\n\n"
        content += f"## Question\n\n{question_body}\n\n"
        content += "---\n\n## Answers\n\n"

        # Sort answers: accepted first, then by score
        answers_sorted = sorted(
            answers,
            key=lambda a: (a.get("answer_id") == accepted_answer_id, a.get("score", 0)),
            reverse=True
        )

        for i, answer in enumerate(answers_sorted[:5]):  # Max 5 answers
            is_accepted = answer.get("answer_id") == accepted_answer_id
            score = answer.get("score", 0)
            answer_body = self._clean_html(answer.get("body", ""))

            marker = "✓ ACCEPTED" if is_accepted else f"Answer {i+1}"
            content += f"### {marker} (Score: {score})\n\n"
            content += f"{answer_body}\n\n"

        # Analyze content for training value
        content_lower = content.lower()

        # Check for error patterns
        has_error = any(err in content_lower for err in [
            "error", "exception", "traceback", "failed", "not working",
            "crash", "bug", "issue", "problem",
        ])

        # Check for installation patterns
        has_installation = any(inst in content_lower for inst in [
            "install", "setup", "configure", "pip install", "npm install",
            "brew install", "apt install", "how to install",
        ])

        # Check for beginner-friendly content
        is_beginner = any(beg in content_lower for beg in self.BEGINNER_KEYWORDS)

        # Check for code examples
        has_code = "```" in content or "<code>" in question.get("body", "")

        yield ScrapedItem(
            source=self.source,
            url=f"https://stackoverflow.com/questions/{question_id}",
            title=title,
            content=content,
            metadata={
                "type": "qa",
                "author": question.get("owner", {}).get("display_name", ""),
                "tag": tag,
                "all_tags": question.get("tags", []),
                "score": question.get("score", 0),
                "view_count": question.get("view_count", 0),
                "answer_count": len(answers),
                "has_accepted_answer": True,
                "has_error": has_error,
                "has_installation": has_installation,
                "is_beginner": is_beginner,
                "has_code": has_code,
                "creation_date": question.get("creation_date"),
            }
        )

    def _clean_html(self, html_content: str) -> str:
        """Convert HTML to markdown-ish text."""
        if not html_content:
            return ""

        text = html_content

        # Convert code blocks
        text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
                     r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

        # Convert links
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text)

        # Convert lists
        text = re.sub(r'<li>(.*?)</li>', r'- \1\n', text)
        text = re.sub(r'<[uo]l[^>]*>', '', text)
        text = re.sub(r'</[uo]l>', '', text)

        # Convert paragraphs and line breaks
        text = re.sub(r'<p[^>]*>', '\n\n', text)
        text = re.sub(r'</p>', '', text)
        text = re.sub(r'<br\s*/?>', '\n', text)

        # Convert headers
        text = re.sub(r'<h(\d)[^>]*>(.*?)</h\d>', lambda m: '#' * int(m.group(1)) + ' ' + m.group(2), text)

        # Convert bold/italic
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)

        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text


# Register with the spider registry
def register():
    return {
        "name": "stackoverflow",
        "spider_class": StackOverflowSpider,
        "description": "Stack Overflow Q&A",
        "type": "code",
        "priority": 1,
    }
