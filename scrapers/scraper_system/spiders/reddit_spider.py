"""
SAM Scraper System - Reddit Roleplay Spider

Scrapes roleplay content from Reddit roleplay subreddits.
Uses Reddit JSON API and Arctic Shift for historical data.
"""

import re
import json
import hashlib
from typing import Dict, Any, Optional, Iterator, List
from datetime import datetime

import scrapy
from scrapy.http import Request, Response, JsonRequest

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class RedditRoleplaySpider(BaseSpider):
    """
    Spider for Reddit roleplay subreddits.

    Features:
    - Multiple roleplay subreddits
    - Roleplay content detection (action markers, dialogue)
    - Scenario extraction
    - Comment thread support
    """

    name = "reddit_roleplay_spider"
    source = "reddit"
    allowed_domains = ["reddit.com", "arctic-shift.photon-reddit.com"]

    rate_limit = 1.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "SAM-Training-Collector/1.0",
            "Accept": "application/json",
        },
    }

    # Target subreddits
    SUBREDDITS = [
        "DirtyPenPals",
        "DirtyWritingPrompts",
        "EroticRolePlay",
        "NSFWroleplay",
        "dirtyr4r",
        "DPPprofiles",
    ]

    ARCTIC_SHIFT_API = "https://arctic-shift.photon-reddit.com/api"

    def __init__(self, *args, subreddit: str = None, max_posts: int = 1000,
                 min_score: int = 5, use_arctic: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_subreddit = subreddit
        self.max_posts = max_posts
        self.min_score = min_score
        self.use_arctic = use_arctic
        self.posts_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start fetching from subreddits."""
        progress = self.get_progress()
        self.posts_scraped = progress.get("total_items", 0)

        subreddits = [self.target_subreddit] if self.target_subreddit else self.SUBREDDITS

        for subreddit in subreddits:
            # Use Arctic Shift for historical data
            if self.use_arctic:
                yield self.make_request(
                    f"{self.ARCTIC_SHIFT_API}/posts/search?subreddit={subreddit}&limit=500&sort=score&sort_type=desc",
                    callback=self.parse_arctic_shift,
                    meta={"subreddit": subreddit, "source": "arctic"}
                )

            # Also fetch recent from Reddit
            yield self.make_request(
                f"https://www.reddit.com/r/{subreddit}/new.json?limit=100",
                callback=self.parse_reddit_listing,
                meta={"subreddit": subreddit, "source": "reddit"}
            )

    def parse_arctic_shift(self, response: Response) -> Iterator[Any]:
        """Parse Arctic Shift API response."""
        subreddit = response.meta.get("subreddit")

        try:
            data = json.loads(response.text)
            posts = data.get("data", [])
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse Arctic Shift response for r/{subreddit}")
            return

        self.logger.info(f"Got {len(posts)} posts from Arctic Shift for r/{subreddit}")

        for post in posts:
            if self.posts_scraped >= self.max_posts:
                return

            item = self._parse_post(post, subreddit)
            if item:
                self.posts_scraped += 1
                yield item

        self.save_progress(total_items=self.posts_scraped)

    def parse_reddit_listing(self, response: Response) -> Iterator[Any]:
        """Parse Reddit JSON listing."""
        subreddit = response.meta.get("subreddit")

        try:
            data = json.loads(response.text)
            children = data.get("data", {}).get("children", [])
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse Reddit response for r/{subreddit}")
            return

        self.logger.info(f"Got {len(children)} posts from Reddit for r/{subreddit}")

        for child in children:
            if self.posts_scraped >= self.max_posts:
                return

            post = child.get("data", {})
            item = self._parse_post(post, subreddit)
            if item:
                self.posts_scraped += 1
                yield item

        # Paginate
        after = data.get("data", {}).get("after")
        if after and self.posts_scraped < self.max_posts:
            yield self.make_request(
                f"https://www.reddit.com/r/{subreddit}/new.json?limit=100&after={after}",
                callback=self.parse_reddit_listing,
                meta={"subreddit": subreddit, "source": "reddit"}
            )

        self.save_progress(total_items=self.posts_scraped)

    def _parse_post(self, post: dict, subreddit: str) -> Optional[ScrapedItem]:
        """Parse a post into a ScrapedItem."""
        reddit_id = post.get("id", "")
        title = post.get("title", "")
        selftext = post.get("selftext", "") or ""
        author = post.get("author", "[deleted]")
        score = post.get("score", 0)
        created_utc = post.get("created_utc", 0)

        # Skip if below minimum score
        if score < self.min_score:
            return None

        # Skip deleted/removed content
        if selftext in ["[deleted]", "[removed]", ""]:
            return None

        if len(selftext) < 100:
            return None

        # Detect roleplay content
        is_roleplay = self._is_roleplay_content(selftext) or self._is_roleplay_content(title)
        has_scenario = self._has_scenario(selftext)

        # Skip non-roleplay content unless it has a scenario
        if not is_roleplay and not has_scenario:
            return None

        # Build metadata
        metadata = {
            "reddit_id": reddit_id,
            "subreddit": subreddit,
            "author": author,
            "score": score,
            "created_utc": created_utc,
            "is_roleplay_content": is_roleplay,
            "has_scenario": has_scenario,
            "word_count": len(selftext.split()),
            "tags": ["roleplay", "reddit", subreddit.lower()],
        }

        return ScrapedItem(
            source=self.source,
            url=f"https://reddit.com/r/{subreddit}/comments/{reddit_id}",
            title=title,
            content=selftext,
            metadata=metadata,
        )

    def _is_roleplay_content(self, text: str) -> bool:
        """Check if text contains actual roleplay content."""
        if not text:
            return False

        # Action markers (asterisks, tildes)
        action_pattern = r'\*[^*]+\*|~[^~]+~|_[^_]+_'
        if re.search(action_pattern, text):
            return True

        # Dialogue patterns
        dialogue_pattern = r'"[^"]{10,}"|\'[^\']{10,}\''
        if re.search(dialogue_pattern, text):
            return True

        # Common RP phrases
        text_lower = text.lower()
        rp_phrases = [
            "i walk", "you see", "she says", "he whispers",
            "i look at you", "you feel", "i lean", "i smile",
            "*smiles*", "*laughs*", "*looks*", "*nods*",
        ]
        if any(phrase in text_lower for phrase in rp_phrases):
            return True

        return False

    def _has_scenario(self, text: str) -> bool:
        """Check if post contains a scenario setup."""
        if not text:
            return False

        text_lower = text.lower()
        scenario_markers = [
            "scenario:", "setting:", "premise:", "plot:",
            "the scene:", "you are", "you're a", "you play",
            "looking for someone to play", "i'll be playing",
        ]

        return any(marker in text_lower for marker in scenario_markers)


class AO3RoleplaySpider(BaseSpider):
    """
    Spider for AO3 roleplay/chat fiction.

    Focuses on chat-format and script-format works.
    """

    name = "ao3_roleplay_spider"
    source = "ao3_roleplay"
    allowed_domains = ["archiveofourown.org"]

    rate_limit = 3.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 3.0,
        "CONCURRENT_REQUESTS": 1,
        "COOKIES_ENABLED": True,
    }

    # Search for chat/script format works
    CHAT_TAGS = [
        "Chatting & Messaging",
        "Text Messages",
        "Chat Format",
        "Script Format",
        "Social Media",
        "Epistolary",
    ]

    def __init__(self, *args, max_pages: int = 20, min_kudos: int = 50, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max_pages
        self.min_kudos = min_kudos
        self.current_tag_index = 0
        self.works_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start with chat/script format tag searches."""
        progress = self.get_progress()
        self.current_tag_index = progress.get("last_tag_index", 0)
        self.works_scraped = progress.get("total_items", 0)

        for i, tag in enumerate(self.CHAT_TAGS[self.current_tag_index:], self.current_tag_index):
            yield self._make_tag_request(tag, 1, i)

    def _make_tag_request(self, tag: str, page: int, tag_index: int) -> Request:
        """Build a tag search request."""
        from urllib.parse import quote

        encoded_tag = quote(tag)
        url = f"https://archiveofourown.org/tags/{encoded_tag}/works?page={page}"

        return self.make_request(
            url,
            callback=self.parse_tag_page,
            meta={"tag": tag, "page": page, "tag_index": tag_index}
        )

    def parse_tag_page(self, response: Response) -> Iterator[Any]:
        """Parse a tag search results page."""
        tag = response.meta.get("tag")
        page = response.meta.get("page", 1)
        tag_index = response.meta.get("tag_index", 0)

        self.logger.info(f"Parsing tag '{tag}' page {page}")

        # Find work blurbs
        works = response.css("li.work.blurb")

        for work in works:
            # Get work ID
            work_id_match = re.search(r'work_(\d+)', work.attrib.get("id", ""))
            if not work_id_match:
                continue

            ao3_id = work_id_match.group(1)

            # Get kudos
            kudos_text = work.css("dd.kudos a::text, dd.kudos::text").get()
            kudos = 0
            if kudos_text:
                try:
                    kudos = int(kudos_text.replace(",", ""))
                except ValueError:
                    pass

            if kudos < self.min_kudos:
                continue

            # Get title
            title = work.css("h4.heading a::text").get()
            if title:
                title = title.strip()

            work_url = f"https://archiveofourown.org/works/{ao3_id}?view_adult=true&view_full_work=true"

            yield self.make_request(
                work_url,
                callback=self.parse_work,
                meta={
                    "ao3_id": ao3_id,
                    "title": title,
                    "kudos": kudos,
                    "tag": tag,
                }
            )

        # Save progress
        self.save_progress(last_tag_index=tag_index, last_page=page, total_items=self.works_scraped)

        # Paginate
        if len(works) > 0 and page < self.max_pages:
            yield self._make_tag_request(tag, page + 1, tag_index)

    def parse_work(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a work page."""
        ao3_id = response.meta.get("ao3_id")
        title = response.meta.get("title", "Untitled")
        kudos = response.meta.get("kudos", 0)
        tag = response.meta.get("tag", "")

        self.logger.info(f"Parsing work: {title}")

        # Extract content
        chapters = response.css("div.userstuff")
        if not chapters:
            return

        full_text = []
        for chapter in chapters:
            text = chapter.css("*::text").getall()
            chapter_text = " ".join(t.strip() for t in text if t.strip())
            if chapter_text:
                full_text.append(chapter_text)

        content = "\n\n---\n\n".join(full_text)

        if len(content) < 500:
            return

        # Check for chat/dialogue format
        dialogue_count = content.count(":") + content.count('"')
        is_chat_format = dialogue_count > len(content) / 200  # High ratio of dialogue markers

        metadata = {
            "ao3_id": ao3_id,
            "kudos": kudos,
            "format_tag": tag,
            "is_chat_format": is_chat_format,
            "word_count": len(content.split()),
            "tags": ["roleplay", "ao3", "chat", tag.lower().replace(" ", "_")],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata=metadata,
        )

        self.works_scraped += 1
        yield item
