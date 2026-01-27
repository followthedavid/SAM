"""
SAM Scraper System - Literotica Spider

Scrapes gay male stories from Literotica for training data.
"""

import re
from typing import Dict, Any, Iterator

from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class LiteroticaSpider(BaseSpider):
    """Spider for Literotica gay male stories."""

    name = "literotica_spider"
    source = "literotica"
    allowed_domains = ["literotica.com", "www.literotica.com"]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    # Gay male category
    BASE_URL = "https://www.literotica.com"
    CATEGORY_URL = "/c/gay-male-stories"

    def __init__(self, *args, max_pages: int = 50, min_words: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max_pages
        self.min_words = min_words

    def start_requests(self) -> Iterator[Request]:
        """Start crawling the gay male category."""
        progress = self.get_progress()
        start_page = progress.get("last_page", 0) + 1

        url = f"{self.BASE_URL}{self.CATEGORY_URL}/{start_page}/"
        yield self.make_request(url, callback=self.parse_listing, meta={"page": start_page})

    def parse_listing(self, response: Response) -> Iterator[Any]:
        """Parse category listing page."""
        page = response.meta.get("page", 1)
        self.logger.info(f"Parsing listing page {page}")

        # Find story links
        stories = response.css("div.b-story-list-box")
        for story in stories:
            link = story.css("a.b-story-list-box__title::attr(href)").get()
            title = story.css("a.b-story-list-box__title::text").get()
            author = story.css("span.b-story-list-box__author a::text").get()

            if link and title:
                yield self.make_request(
                    link,
                    callback=self.parse_story,
                    meta={
                        "title": title.strip(),
                        "author": author.strip() if author else "Anonymous",
                    }
                )

        self.save_progress(last_page=page)

        # Next page
        if page < self.max_pages:
            next_url = f"{self.BASE_URL}{self.CATEGORY_URL}/{page + 1}/"
            yield self.make_request(
                next_url,
                callback=self.parse_listing,
                meta={"page": page + 1}
            )

    def parse_story(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse individual story page."""
        title = response.meta.get("title", "Untitled")
        author = response.meta.get("author", "Anonymous")

        self.logger.info(f"Parsing story: {title}")

        # Extract story text
        content_div = response.css("div.aa_ht")
        if not content_div:
            content_div = response.css("div.b-story-body-x")

        if not content_div:
            self.logger.warning(f"No content found: {response.url}")
            return

        paragraphs = content_div.css("p::text").getall()
        text = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        word_count = len(text.split())
        if word_count < self.min_words:
            self.logger.warning(f"Skipping {title}: only {word_count} words")
            return

        # Get tags/categories
        tags = response.css("a.av_as::text").getall()
        tags = [t.strip() for t in tags if t.strip()]
        tags.extend(["gay", "male", "literotica"])

        # Analysis
        analysis = self._analyze_content(text)

        metadata = {
            "author": author,
            "tags": tags,
            "character_count": analysis["character_count"],
            "has_dialogue": analysis["has_dialogue"],
            "pov": analysis["pov"],
            "content_intensity": analysis["content_intensity"],
            "relationship_type": analysis["relationship_type"],
            "quality_score": analysis["quality_score"],
        }

        yield ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=text,
            metadata=metadata,
        )

        # Check for multi-page stories
        next_page = response.css("a.b-pager-next::attr(href)").get()
        if next_page:
            yield self.make_request(
                next_page,
                callback=self.parse_story_continuation,
                meta={
                    "title": title,
                    "author": author,
                    "accumulated_text": text,
                }
            )

    def parse_story_continuation(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse continuation pages of multi-page stories."""
        title = response.meta.get("title")
        author = response.meta.get("author")
        accumulated = response.meta.get("accumulated_text", "")

        content_div = response.css("div.aa_ht, div.b-story-body-x")
        if content_div:
            paragraphs = content_div.css("p::text").getall()
            new_text = "\n\n".join(p.strip() for p in paragraphs if p.strip())
            accumulated += "\n\n" + new_text

        # Check for more pages
        next_page = response.css("a.b-pager-next::attr(href)").get()
        if next_page:
            yield self.make_request(
                next_page,
                callback=self.parse_story_continuation,
                meta={
                    "title": title,
                    "author": author,
                    "accumulated_text": accumulated,
                }
            )
        # Final page - don't yield again, already yielded first page

    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze content for metadata."""
        text_lower = text.lower()

        analysis = {
            "character_count": 2,
            "has_dialogue": text.count('"') > 20,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "quality_score": 0.5,
        }

        # POV
        first_person = len(re.findall(r'\bI\b', text))
        third_person = len(re.findall(r'\bhe\b', text_lower))
        if first_person > third_person * 1.5:
            analysis["pov"] = "first-person"

        # Intensity
        explicit_terms = ["cock", "dick", "fuck", "cum", "suck"]
        explicit_count = sum(text_lower.count(t) for t in explicit_terms)
        if explicit_count > 15:
            analysis["content_intensity"] = "explicit"
        elif explicit_count > 5:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Quality
        word_count = len(text.split())
        score = 0.5
        if word_count > 3000:
            score += 0.2
        if analysis["has_dialogue"]:
            score += 0.1
        analysis["quality_score"] = min(1.0, score)

        return analysis
