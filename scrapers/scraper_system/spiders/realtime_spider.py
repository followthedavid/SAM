"""
Real-Time Streaming Spider

Connects to real-time data streams for continuous fresh content:
1. GitHub Events API - new issues, commits, releases
2. HackerNews Firebase API - tech discussions
3. Reddit Streaming - r/swift, r/iOSProgramming, r/SwiftUI

Runs continuously, yielding items as they arrive.
"""

import json
import logging
import time
import html
import re
from datetime import datetime
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import urljoin

try:
    from scrapy.http import Request, Response
except ImportError:
    pass

from .base_spider import BaseSpider
from ..storage.database import ScrapedItem

logger = logging.getLogger(__name__)


class GitHubEventsSpider(BaseSpider):
    """
    Spider for GitHub Events API.

    Monitors:
    - IssuesEvent (new issues)
    - IssueCommentEvent (solutions)
    - PushEvent (new code)
    - ReleaseEvent (new versions)

    Usage:
        scrapy crawl github_events
        scrapy crawl github_events -a repos="apple/swift,SwiftUI"
    """

    name = "github_events_spider"
    source = "github_events"

    # GitHub Events API
    API_BASE = "https://api.github.com"

    # Repos to monitor (owner/repo format)
    DEFAULT_REPOS = [
        "apple/swift",
        "apple/swift-evolution",
        "SwiftUIX/SwiftUIX",
        "pointfreeco/swift-composable-architecture",
        "Alamofire/Alamofire",
        "vapor/vapor",
        "ReactiveX/RxSwift",
        "onevcat/Kingfisher",
        "SnapKit/SnapKit",
        "realm/realm-swift",
    ]

    # Topics to monitor
    TOPICS = ["swiftui", "swift", "ios", "visionos", "xcode"]

    # Event types we care about
    RELEVANT_EVENTS = [
        "IssuesEvent",
        "IssueCommentEvent",
        "PushEvent",
        "ReleaseEvent",
        "CreateEvent",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, repos: str = None, max_events: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_events = int(max_events)
        self.events_processed = 0
        self.seen_event_ids = set()

        # Parse repos
        if repos:
            self.repos = [r.strip() for r in repos.split(",")]
        else:
            self.repos = self.DEFAULT_REPOS

        # Get GitHub token
        import os
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

    def _get_headers(self) -> dict:
        """Get headers with auth."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAM-Training-Bot/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def start_requests(self) -> Iterator[Request]:
        """Start monitoring repos."""
        # Monitor specific repos
        for repo in self.repos:
            yield self.make_request(
                f"{self.API_BASE}/repos/{repo}/events",
                callback=self.parse_repo_events,
                meta={"repo": repo},
                headers=self._get_headers()
            )

        # Also monitor topics
        for topic in self.TOPICS:
            yield self.make_request(
                f"{self.API_BASE}/search/repositories?q=topic:{topic}+pushed:>2024-01-01&sort=updated&per_page=10",
                callback=self.parse_topic_repos,
                meta={"topic": topic},
                headers=self._get_headers()
            )

    def parse_repo_events(self, response: Response) -> Iterator:
        """Parse events from a repo."""
        repo = response.meta.get("repo", "")

        try:
            events = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse events for {repo}")
            return

        for event in events:
            if self.events_processed >= self.max_events:
                return

            event_id = event.get("id")
            if event_id in self.seen_event_ids:
                continue
            self.seen_event_ids.add(event_id)

            event_type = event.get("type")
            if event_type not in self.RELEVANT_EVENTS:
                continue

            # Process event
            item = self._process_event(event, repo)
            if item:
                self.events_processed += 1
                yield item

    def parse_topic_repos(self, response: Response) -> Iterator[Request]:
        """Parse repos from topic search and fetch their events."""
        topic = response.meta.get("topic", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        repos = data.get("items", [])
        for repo in repos[:5]:  # Top 5 per topic
            full_name = repo.get("full_name", "")
            if full_name and full_name not in self.repos:
                yield self.make_request(
                    f"{self.API_BASE}/repos/{full_name}/events",
                    callback=self.parse_repo_events,
                    meta={"repo": full_name, "topic": topic},
                    headers=self._get_headers()
                )

    def _process_event(self, event: Dict, repo: str) -> Optional[ScrapedItem]:
        """Process a GitHub event into a ScrapedItem."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})
        actor = event.get("actor", {}).get("login", "")
        created_at = event.get("created_at", "")

        content = ""
        title = ""
        url = ""
        metadata = {
            "type": "github_event",
            "event_type": event_type,
            "repo": repo,
            "actor": actor,
            "created_at": created_at,
        }

        if event_type == "IssuesEvent":
            action = payload.get("action", "")
            issue = payload.get("issue", {})

            if action == "opened":
                title = f"New Issue: {issue.get('title', '')}"
                content = f"## {issue.get('title', '')}\n\n{issue.get('body', '')}"
                url = issue.get("html_url", "")
                metadata["labels"] = [l.get("name") for l in issue.get("labels", [])]

        elif event_type == "IssueCommentEvent":
            action = payload.get("action", "")
            issue = payload.get("issue", {})
            comment = payload.get("comment", {})

            if action == "created":
                title = f"Comment on: {issue.get('title', '')}"
                content = f"## Issue: {issue.get('title', '')}\n\n### Comment:\n{comment.get('body', '')}"
                url = comment.get("html_url", "")

        elif event_type == "ReleaseEvent":
            release = payload.get("release", {})
            title = f"New Release: {release.get('name', '')} ({release.get('tag_name', '')})"
            content = f"## {release.get('name', '')}\n\n{release.get('body', '')}"
            url = release.get("html_url", "")

        elif event_type == "PushEvent":
            commits = payload.get("commits", [])
            if commits:
                title = f"Push to {repo}: {len(commits)} commits"
                content = "## Commits:\n\n"
                for commit in commits[:5]:
                    content += f"- {commit.get('message', '').split(chr(10))[0]}\n"
                url = f"https://github.com/{repo}/commits"

        if content and len(content) > 50:
            return ScrapedItem(
                source=self.source,
                url=url or f"https://github.com/{repo}",
                title=title,
                content=content,
                metadata=metadata,
            )

        return None


class HackerNewsSpider(BaseSpider):
    """
    Spider for HackerNews using Firebase API.

    Monitors:
    - Top stories
    - New stories
    - Ask HN / Show HN

    Filters for tech/programming content.

    Usage:
        scrapy crawl hackernews
    """

    name = "hackernews_spider"
    source = "hackernews"

    # HackerNews Firebase API
    API_BASE = "https://hacker-news.firebaseio.com/v0"

    # Keywords to filter for relevance
    RELEVANT_KEYWORDS = [
        "swift", "swiftui", "ios", "macos", "apple", "xcode",
        "programming", "developer", "code", "software", "api",
        "bug", "error", "debug", "fix", "testing",
        "tutorial", "guide", "learn", "beginner",
        "visionos", "vision pro", "spatial",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, max_stories: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_stories = int(max_stories)
        self.stories_processed = 0
        self.seen_ids = set()

    def start_requests(self) -> Iterator[Request]:
        """Start fetching stories."""
        # Top stories
        yield self.make_request(
            f"{self.API_BASE}/topstories.json",
            callback=self.parse_story_list,
            meta={"list_type": "top"}
        )

        # New stories
        yield self.make_request(
            f"{self.API_BASE}/newstories.json",
            callback=self.parse_story_list,
            meta={"list_type": "new"}
        )

        # Ask HN
        yield self.make_request(
            f"{self.API_BASE}/askstories.json",
            callback=self.parse_story_list,
            meta={"list_type": "ask"}
        )

        # Show HN
        yield self.make_request(
            f"{self.API_BASE}/showstories.json",
            callback=self.parse_story_list,
            meta={"list_type": "show"}
        )

    def parse_story_list(self, response: Response) -> Iterator[Request]:
        """Parse list of story IDs and fetch each."""
        list_type = response.meta.get("list_type", "")

        try:
            story_ids = json.loads(response.text)
        except json.JSONDecodeError:
            return

        # Fetch top N stories
        for story_id in story_ids[:100]:
            if story_id in self.seen_ids:
                continue
            self.seen_ids.add(story_id)

            if self.stories_processed >= self.max_stories:
                return

            yield self.make_request(
                f"{self.API_BASE}/item/{story_id}.json",
                callback=self.parse_story,
                meta={"list_type": list_type}
            )

    def parse_story(self, response: Response) -> Iterator:
        """Parse a single story."""
        list_type = response.meta.get("list_type", "")

        try:
            story = json.loads(response.text)
        except json.JSONDecodeError:
            return

        if not story:
            return

        title = story.get("title", "")
        text = story.get("text", "")
        url = story.get("url", "")

        # Check relevance
        combined_text = f"{title} {text}".lower()
        is_relevant = any(kw in combined_text for kw in self.RELEVANT_KEYWORDS)

        if not is_relevant:
            return

        self.stories_processed += 1

        # Build content
        content = f"# {title}\n\n"
        if text:
            content += html.unescape(text)

        # Fetch top comments if it's a discussion
        if story.get("descendants", 0) > 0 and list_type in ["ask", "show"]:
            kids = story.get("kids", [])[:5]
            for kid_id in kids:
                yield self.make_request(
                    f"{self.API_BASE}/item/{kid_id}.json",
                    callback=self.parse_comment,
                    meta={"parent_story": story, "story_content": content}
                )
        else:
            yield ScrapedItem(
                source=self.source,
                url=url or f"https://news.ycombinator.com/item?id={story.get('id')}",
                title=title,
                content=content,
                metadata={
                    "type": "hackernews",
                    "list_type": list_type,
                    "author": story.get("by", ""),
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "time": story.get("time", 0),
                }
            )

    def parse_comment(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a comment and add to story."""
        parent = response.meta.get("parent_story", {})
        content = response.meta.get("story_content", "")

        try:
            comment = json.loads(response.text)
        except json.JSONDecodeError:
            return

        if comment and comment.get("text"):
            content += f"\n\n---\n**{comment.get('by', 'anon')}:** {html.unescape(comment.get('text', ''))}"

        yield ScrapedItem(
            source=self.source,
            url=f"https://news.ycombinator.com/item?id={parent.get('id')}",
            title=parent.get("title", ""),
            content=content,
            metadata={
                "type": "hackernews",
                "author": parent.get("by", ""),
                "score": parent.get("score", 0),
                "comments": parent.get("descendants", 0),
            }
        )


class RedditStreamSpider(BaseSpider):
    """
    Spider for Reddit programming subreddits.

    Monitors:
    - r/swift
    - r/SwiftUI
    - r/iOSProgramming
    - r/apple
    - r/visionos

    Uses Reddit JSON API (no auth required for public).

    Usage:
        scrapy crawl reddit_stream
    """

    name = "reddit_stream_spider"
    source = "reddit_stream"

    # Subreddits to monitor
    SUBREDDITS = [
        "swift",
        "SwiftUI",
        "iOSProgramming",
        "apple",
        "visionos",
        "learnprogramming",
        "AskProgramming",
    ]

    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,  # Reddit rate limits
        "CONCURRENT_REQUESTS": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "SAM-Bot/1.0 (Research Project)",
        },
    }

    def __init__(self, *args, max_posts: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_posts = int(max_posts)
        self.posts_scraped = 0
        self.seen_ids = set()

    def start_requests(self) -> Iterator[Request]:
        """Start fetching from subreddits."""
        for subreddit in self.SUBREDDITS:
            # Hot posts
            yield self.make_request(
                f"https://www.reddit.com/r/{subreddit}/hot.json?limit=50",
                callback=self.parse_listing,
                meta={"subreddit": subreddit, "sort": "hot"}
            )

            # New posts
            yield self.make_request(
                f"https://www.reddit.com/r/{subreddit}/new.json?limit=50",
                callback=self.parse_listing,
                meta={"subreddit": subreddit, "sort": "new"}
            )

    def parse_listing(self, response: Response) -> Iterator:
        """Parse Reddit listing."""
        subreddit = response.meta.get("subreddit", "")
        sort_type = response.meta.get("sort", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Reddit JSON for r/{subreddit}")
            return

        posts = data.get("data", {}).get("children", [])

        for post_data in posts:
            if self.posts_scraped >= self.max_posts:
                return

            post = post_data.get("data", {})
            post_id = post.get("id")

            if post_id in self.seen_ids:
                continue
            self.seen_ids.add(post_id)

            # Skip removed/deleted
            if post.get("removed_by_category") or post.get("selftext") == "[removed]":
                continue

            title = post.get("title", "")
            selftext = post.get("selftext", "")
            url = post.get("url", "")
            permalink = post.get("permalink", "")

            # Build content
            content = f"# {title}\n\n{selftext}"

            self.posts_scraped += 1

            # If post has comments, fetch them
            if post.get("num_comments", 0) > 0:
                yield self.make_request(
                    f"https://www.reddit.com{permalink}.json?limit=10",
                    callback=self.parse_post_with_comments,
                    meta={
                        "post": post,
                        "subreddit": subreddit,
                    }
                )
            else:
                yield ScrapedItem(
                    source=self.source,
                    url=f"https://www.reddit.com{permalink}",
                    title=title,
                    content=content,
                    metadata={
                        "type": "reddit",
                        "subreddit": subreddit,
                        "author": post.get("author", ""),
                        "score": post.get("score", 0),
                        "comments": post.get("num_comments", 0),
                        "created_utc": post.get("created_utc", 0),
                        "flair": post.get("link_flair_text", ""),
                    }
                )

    def parse_post_with_comments(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse post with its comments."""
        post = response.meta.get("post", {})
        subreddit = response.meta.get("subreddit", "")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return

        # First element is post, second is comments
        if len(data) < 2:
            return

        comments_data = data[1].get("data", {}).get("children", [])

        # Build content with comments
        content = f"# {post.get('title', '')}\n\n{post.get('selftext', '')}\n\n---\n\n## Comments:\n\n"

        for comment_data in comments_data[:10]:
            comment = comment_data.get("data", {})
            if comment.get("body") and comment.get("body") != "[removed]":
                author = comment.get("author", "anon")
                body = comment.get("body", "")
                score = comment.get("score", 0)
                content += f"**{author}** ({score} points):\n{body}\n\n"

        yield ScrapedItem(
            source=self.source,
            url=f"https://www.reddit.com{post.get('permalink', '')}",
            title=post.get("title", ""),
            content=content,
            metadata={
                "type": "reddit",
                "subreddit": subreddit,
                "author": post.get("author", ""),
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "has_comments_scraped": True,
                "flair": post.get("link_flair_text", ""),
            }
        )


def register():
    return [
        {
            "name": "github_events",
            "spider_class": GitHubEventsSpider,
            "description": "GitHub Events Stream",
            "type": "realtime",
            "priority": 1,
        },
        {
            "name": "hackernews",
            "spider_class": HackerNewsSpider,
            "description": "HackerNews Stories",
            "type": "realtime",
            "priority": 2,
        },
        {
            "name": "reddit_stream",
            "spider_class": RedditStreamSpider,
            "description": "Reddit Programming",
            "type": "realtime",
            "priority": 2,
        },
    ]
