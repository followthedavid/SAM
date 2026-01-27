"""
SAM Scraper System - F-List Character Spider

Scrapes character profiles from F-List for roleplay training data.
Includes character descriptions, kinks, custom fields, and personality.

Note: F-List character search requires authentication.
This spider needs a list of character names provided via:
- Command line: scrapy crawl flist_spider -a names_file=characters.txt
- Or by providing names directly via settings
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Iterator
from urllib.parse import urljoin

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class FListSpider(BaseSpider):
    """
    Spider for F-List character profiles.

    Features:
    - Character profiles with descriptions
    - Kink preferences (favorites, yes, maybe, no)
    - Custom fields (scenarios, backstory, etc.)
    - Species/gender/orientation metadata
    """

    name = "flist_spider"
    source = "flist"
    allowed_domains = ["f-list.net"]

    # F-List rate limiting
    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
        "COOKIES_ENABLED": True,
    }

    # Default character names to search (can be overridden)
    DEFAULT_NAMES_FILE = "/Volumes/David External/flist_archive/characters.txt"

    def __init__(self, *args, names_file: str = None, names: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.names_file = names_file or self.DEFAULT_NAMES_FILE
        self.character_names = []

        # Load names from file
        if names:
            # Names provided directly as comma-separated string
            self.character_names = [n.strip() for n in names.split(",") if n.strip()]
        elif self.names_file:
            self._load_names_from_file()

        self.current_index = 0

    def _load_names_from_file(self):
        """Load character names from file."""
        try:
            with open(self.names_file, "r") as f:
                for line in f:
                    name = line.strip()
                    if name and not name.startswith("#"):
                        self.character_names.append(name)
            self.logger.info(f"Loaded {len(self.character_names)} character names from {self.names_file}")
        except FileNotFoundError:
            self.logger.warning(f"Names file not found: {self.names_file}")
            self.logger.info("Provide character names via -a names='Name1,Name2' or -a names_file=path/to/file.txt")
        except Exception as e:
            self.logger.error(f"Error loading names file: {e}")

    def start_requests(self) -> Iterator[Request]:
        """Start fetching character profiles."""
        # Resume from progress
        progress = self.get_progress()
        self.current_index = progress.get("last_index", 0)

        if not self.character_names:
            self.logger.error("No character names provided. Use -a names='Name1,Name2' or -a names_file=path/to/file.txt")
            return

        self.logger.info(f"Starting from index {self.current_index} of {len(self.character_names)} characters")

        for i in range(self.current_index, len(self.character_names)):
            name = self.character_names[i]
            yield self._make_character_request(name, i)

    def _make_character_request(self, name: str, index: int) -> Request:
        """Build request for a character profile."""
        url = f"https://www.f-list.net/c/{name}"
        return self.make_request(
            url,
            callback=self.parse_character,
            meta={"name": name, "index": index}
        )

    def parse_character(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a character profile page."""
        name = response.meta.get("name")
        index = response.meta.get("index", 0)

        self.logger.info(f"[{index + 1}/{len(self.character_names)}] Parsing: {name}")

        # Check for errors (private profile, not found, etc.)
        if "does not exist" in response.text.lower() or response.status == 404:
            self.logger.warning(f"Character not found: {name}")
            self.save_progress(last_index=index + 1)
            return

        if "private" in response.text.lower() and "profile" in response.text.lower():
            self.logger.warning(f"Private profile: {name}")
            self.save_progress(last_index=index + 1)
            return

        try:
            # Parse profile data
            profile = self._extract_profile(response, name)

            if not profile:
                self.logger.warning(f"Could not parse profile: {name}")
                self.save_progress(last_index=index + 1)
                return

            # Build content from profile data
            content_parts = []

            if profile.get("description"):
                content_parts.append(f"Description:\n{profile['description']}")

            if profile.get("personality"):
                content_parts.append(f"Personality:\n{profile['personality']}")

            for field_name, field_content in profile.get("customs", {}).items():
                if field_content and len(field_content) > 50:
                    content_parts.append(f"{field_name}:\n{field_content}")

            content = "\n\n".join(content_parts)

            if len(content) < 100:
                self.logger.warning(f"Insufficient content for {name}: {len(content)} chars")
                self.save_progress(last_index=index + 1)
                return

            # Build metadata
            metadata = {
                "flist_id": name,
                "species": profile.get("species", ""),
                "gender": profile.get("gender", ""),
                "orientation": profile.get("orientation", ""),
                "kinks_fave": profile.get("kinks_fave", []),
                "kinks_yes": profile.get("kinks_yes", []),
                "kinks_maybe": profile.get("kinks_maybe", []),
                "kinks_no": profile.get("kinks_no", []),
                "customs": profile.get("customs", {}),
                "images": profile.get("images", []),
                "tags": self._generate_tags(profile),
            }

            # Create ScrapedItem
            item = ScrapedItem(
                source=self.source,
                url=response.url,
                title=name,
                content=content,
                metadata=metadata,
            )

            # Save progress
            self.save_progress(last_index=index + 1, total_items=index + 1)

            yield item

        except Exception as e:
            self.logger.error(f"Error parsing {name}: {e}")
            self.save_progress(last_index=index + 1)

    def _extract_profile(self, response: Response, name: str) -> Optional[Dict[str, Any]]:
        """Extract profile data from page."""
        profile = {
            "name": name,
            "species": "",
            "gender": "",
            "orientation": "",
            "description": "",
            "personality": "",
            "kinks_fave": [],
            "kinks_yes": [],
            "kinks_maybe": [],
            "kinks_no": [],
            "customs": {},
            "images": [],
        }

        # Extract basic info fields
        info_items = response.css(".info-field, .profile-field, dt")
        for item in info_items:
            label = item.css("::text").get()
            if not label:
                continue
            label = label.strip().lower()

            value_elem = item.css("+ dd ::text").get() or item.xpath("following-sibling::*[1]/text()").get()
            if value_elem:
                value = value_elem.strip()

                if "species" in label:
                    profile["species"] = value
                elif "gender" in label:
                    profile["gender"] = value
                elif "orientation" in label:
                    profile["orientation"] = value

        # Extract description
        desc_selectors = [
            ".character-description",
            "#character-description",
            ".profile-description",
            "[data-field='description']",
        ]
        for selector in desc_selectors:
            desc_elem = response.css(selector)
            if desc_elem:
                profile["description"] = " ".join(desc_elem.css("*::text").getall()).strip()
                break

        # Extract personality
        personality_elem = response.css("[data-field='personality'], .personality")
        if personality_elem:
            profile["personality"] = " ".join(personality_elem.css("*::text").getall()).strip()

        # Extract kinks by category
        kink_sections = response.css(".kink-group, .kinks-section")
        for section in kink_sections:
            header = section.css("h3 ::text, .kink-header ::text").get()
            if not header:
                continue

            header_text = header.strip().lower()
            kink_items = section.css(".kink-item ::text, li ::text").getall()
            kink_names = [k.strip() for k in kink_items if k.strip()]

            if "fave" in header_text or "favorite" in header_text:
                profile["kinks_fave"].extend(kink_names)
            elif "yes" in header_text:
                profile["kinks_yes"].extend(kink_names)
            elif "maybe" in header_text:
                profile["kinks_maybe"].extend(kink_names)
            elif "no" in header_text:
                profile["kinks_no"].extend(kink_names)

        # Extract custom fields (scenarios, backstory, etc.)
        custom_sections = response.css(".custom-field, .infotag-group")
        for section in custom_sections:
            title = section.css(".field-title ::text, h4 ::text").get()
            content = section.css(".field-content ::text, .infotag-content ::text").getall()

            if title and content:
                title = title.strip()
                content_text = " ".join(c.strip() for c in content if c.strip())
                if content_text:
                    profile["customs"][title] = content_text

        # Extract images
        for img in response.css(".character-image img, .profile-image img"):
            src = img.attrib.get("src") or img.attrib.get("data-src")
            if src:
                profile["images"].append(src)

        return profile

    def _generate_tags(self, profile: Dict) -> List[str]:
        """Generate tags from profile data."""
        tags = ["roleplay", "character"]

        if profile.get("species"):
            tags.append(profile["species"].lower())

        if profile.get("gender"):
            tags.append(profile["gender"].lower())

        if profile.get("orientation"):
            tags.append(profile["orientation"].lower())

        # Add some kinks as tags (limit to prevent explosion)
        for kink in profile.get("kinks_fave", [])[:5]:
            tags.append(kink.lower())

        return tags


class BlueMoonSpider(BaseSpider):
    """
    Spider for Blue Moon Roleplaying forum threads.

    Scrapes public roleplay threads for training data.
    """

    name = "bluemoon_spider"
    source = "bluemoon"
    allowed_domains = ["bluemoonroleplaying.com"]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, *args, thread_urls: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.thread_urls = []

        if thread_urls:
            self.thread_urls = [u.strip() for u in thread_urls.split(",") if u.strip()]

    def start_requests(self) -> Iterator[Request]:
        """Start fetching forum threads."""
        if not self.thread_urls:
            self.logger.error("No thread URLs provided. Use -a thread_urls='url1,url2'")
            return

        for url in self.thread_urls:
            yield self.make_request(url, callback=self.parse_thread)

    def parse_thread(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a roleplay thread."""
        # Extract title
        title_elem = response.css("h1.p-title-value ::text, .thread-title ::text").get()
        title = title_elem.strip() if title_elem else "Unknown Thread"

        self.logger.info(f"Parsing thread: {title}")

        # Extract posts
        posts = response.css(".message-body, .post-content, article.message")

        participants = set()
        content_parts = []
        turn_count = 0

        for post in posts:
            # Get author
            author_elem = post.css(".username ::text, .message-name a ::text").get()
            author = author_elem.strip() if author_elem else "Unknown"
            participants.add(author)

            # Get content
            content_elem = post.css(".bbWrapper, .message-content")
            if content_elem:
                text = " ".join(content_elem.css("*::text").getall()).strip()
                if text and len(text) > 20:
                    content_parts.append(f"[{author}]:\n{text}")
                    turn_count += 1

        if turn_count < 2:
            self.logger.warning(f"Insufficient turns in thread: {turn_count}")
            return

        full_content = "\n\n".join(content_parts)
        word_count = len(full_content.split())

        if word_count < 500:
            self.logger.warning(f"Insufficient content: {word_count} words")
            return

        metadata = {
            "participants": list(participants),
            "turn_count": turn_count,
            "word_count": word_count,
            "tags": ["roleplay", "forum", "collaborative"],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=full_content,
            metadata=metadata,
        )

        yield item
