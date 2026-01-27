"""
SAM Scraper System - Nifty.org Spider

Scrapes gay male stories from nifty.org for training data.
Integrates with the scraper_system for scheduling, resource management, and storage.

Based on nifty_ripper.py, converted to Scrapy.
"""

import re
from typing import Dict, Any, Optional, Iterator, List

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class NiftySpider(BaseSpider):
    """
    Spider for Nifty.org gay male fiction archive.

    Features:
    - Category-based crawling
    - Series/multi-part story support
    - Email-format and HTML parsing
    - Content analysis for training data
    """

    name = "nifty_spider"
    source = "nifty"
    allowed_domains = ["www.nifty.org", "nifty.org"]

    # Nifty-specific settings
    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    # Gay male categories to scrape
    CATEGORIES = [
        "adult-friends",
        "athletics",
        "beginnings",
        "camping",
        "celebrity",
        "college",
        "encounters",
        "first-time",
        "high-school",
        "historical",
        "interracial",
        "military",
        "relationships",
        "rural",
        "sf-fantasy",
        "young-friends",
    ]

    BASE_URL = "https://www.nifty.org"
    GAY_INDEX = "/nifty/gay/"

    def __init__(self, *args, category: str = None, min_words: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.specific_category = category
        self.min_words = min_words
        self.current_category_index = 0

    def start_requests(self) -> Iterator[Request]:
        """Start crawling categories."""
        # Resume from progress
        progress = self.get_progress()
        self.current_category_index = progress.get("last_category_index", 0)

        if self.specific_category:
            yield self._make_category_request(self.specific_category)
        else:
            category = self.CATEGORIES[self.current_category_index]
            yield self._make_category_request(category)

    def _make_category_request(self, category: str) -> Request:
        """Build request for a category index page."""
        url = f"{self.BASE_URL}{self.GAY_INDEX}{category}/"
        return self.make_request(
            url,
            callback=self.parse_category,
            meta={"category": category}
        )

    def parse_category(self, response: Response) -> Iterator[Any]:
        """Parse category index page."""
        category = response.meta.get("category")
        self.logger.info(f"Parsing category: {category}")

        stories_found = 0

        # Find story rows (the .ftr class contains file table rows)
        for row in response.css(".ftr"):
            cells = row.css("div")
            if len(cells) >= 3:
                # Parse: size | date | title link
                size_text = cells[0].css("::text").get() or ""
                date_text = cells[1].css("::text").get() or ""

                link = cells[2].css("a")
                if link:
                    href = link.attrib.get("href", "")
                    title = link.css("::text").get() or ""

                    if not href or href.startswith(".."):
                        continue

                    # Check if it's a series (directory)
                    is_series = href.endswith("/") or size_text.lower() == "dir"

                    # Build full URL
                    if not href.startswith("http"):
                        story_url = f"{self.BASE_URL}{self.GAY_INDEX}{category}/{href}"
                    else:
                        story_url = href

                    if is_series:
                        # Queue series for expansion
                        yield self.make_request(
                            story_url,
                            callback=self.parse_series,
                            meta={
                                "category": category,
                                "series_name": title.strip(),
                            }
                        )
                    else:
                        # Queue individual story
                        yield self.make_request(
                            story_url,
                            callback=self.parse_story,
                            meta={
                                "category": category,
                                "title": title.strip(),
                                "date_published": date_text.strip(),
                                "file_size": size_text.strip(),
                            }
                        )
                        stories_found += 1

        self.logger.info(f"Found {stories_found} stories in {category}")

        # Save progress
        self.save_progress(last_category_index=self.current_category_index)

        # Check for pagination (jscroll)
        next_link = response.css("a.jscroll-next::attr(href)").get()
        if next_link:
            if not next_link.startswith("http"):
                if next_link.startswith("/"):
                    next_url = f"{self.BASE_URL}{next_link}"
                else:
                    next_url = f"{self.BASE_URL}{self.GAY_INDEX}{category}/{next_link}"
            else:
                next_url = next_link

            yield self.make_request(
                next_url,
                callback=self.parse_category,
                meta={"category": category}
            )
        elif not self.specific_category:
            # Move to next category
            self.current_category_index += 1
            if self.current_category_index < len(self.CATEGORIES):
                next_category = self.CATEGORIES[self.current_category_index]
                yield self._make_category_request(next_category)

    def parse_series(self, response: Response) -> Iterator[Any]:
        """Parse series directory to get individual parts."""
        category = response.meta.get("category")
        series_name = response.meta.get("series_name")

        self.logger.info(f"Parsing series: {series_name}")

        part_number = 0
        for row in response.css(".ftr"):
            cells = row.css("div")
            if len(cells) >= 3:
                link = cells[2].css("a")
                if link:
                    href = link.attrib.get("href", "")
                    title = link.css("::text").get() or ""

                    # Skip parent directory and sub-directories
                    if href.startswith("..") or href.endswith("/"):
                        continue

                    part_number += 1

                    # Try to extract part number from title
                    part_match = re.search(r'(?:part|chapter|ch)?[\s\-_]*(\d+)', title, re.I)
                    if part_match:
                        part_num = int(part_match.group(1))
                    else:
                        part_num = part_number

                    story_url = f"{response.url}{href}"

                    yield self.make_request(
                        story_url,
                        callback=self.parse_story,
                        meta={
                            "category": category,
                            "title": f"{series_name} - {title.strip()}",
                            "series_name": series_name,
                            "part_number": part_num,
                            "date_published": cells[1].css("::text").get() or "",
                        }
                    )

    def parse_story(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse individual story page."""
        category = response.meta.get("category")
        title = response.meta.get("title", "Untitled")
        series_name = response.meta.get("series_name")
        part_number = response.meta.get("part_number")
        date_published = response.meta.get("date_published")

        self.logger.info(f"Parsing story: {title}")

        # Get raw content
        raw_html = response.text

        # Parse content (handles both email-format and HTML)
        parsed = self._parse_story_content(raw_html)

        if not parsed["text"] or parsed["word_count"] < self.min_words:
            self.logger.warning(f"Skipping {response.url}: insufficient content ({parsed['word_count']} words)")
            return

        # Analyze content
        analysis = self._analyze_content(parsed["text"])

        # Build tags
        tags = [category, "gay", "male"]
        if analysis["content_intensity"]:
            tags.append(analysis["content_intensity"])
        if analysis["relationship_type"]:
            tags.append(analysis["relationship_type"])
        if analysis["setting"]:
            tags.append(analysis["setting"])
        if analysis["pov"]:
            tags.append(analysis["pov"])

        # Build metadata
        metadata = {
            "category": category,
            "author": parsed["author"] or "Anonymous",
            "author_email": parsed["author_email"],
            "date_published": date_published or parsed["date"],
            "series_name": series_name,
            "part_number": part_number,
            # Analysis
            "character_count": analysis["character_count"],
            "has_dialogue": analysis["has_dialogue"],
            "pov": analysis["pov"],
            "content_intensity": analysis["content_intensity"],
            "relationship_type": analysis["relationship_type"],
            "setting": analysis["setting"],
            "quality_score": analysis["quality_score"],
            "tags": tags,
        }

        # Create item
        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=parsed["title"] or title,
            content=parsed["text"],
            metadata=metadata,
        )

        yield item

    def _parse_story_content(self, html: str) -> Dict[str, Any]:
        """Parse story content from email-style OR HTML format."""
        result = {
            "author": None,
            "author_email": None,
            "date": None,
            "title": None,
            "text": "",
            "word_count": 0
        }

        # Detect if this is HTML format
        is_html = bool(re.search(r'<(html|p|body|div)\b', html, re.I))

        if is_html:
            result = self._parse_html_story(html)
        else:
            result = self._parse_email_story(html)

        return result

    def _parse_html_story(self, html: str) -> Dict[str, Any]:
        """Parse HTML-formatted story."""
        from scrapy import Selector

        result = {
            "author": None,
            "author_email": None,
            "date": None,
            "title": None,
            "text": "",
            "word_count": 0
        }

        sel = Selector(text=html)

        # Extract title
        title = sel.css("title::text").get()
        if title:
            result["title"] = title.strip()

        # Try to find author from h5 or similar
        author_tag = sel.css("h5::text").get()
        if author_tag:
            author_text = author_tag.strip()
            if author_text.lower().startswith("by "):
                result["author"] = author_text[3:].strip()
            else:
                result["author"] = author_text

        # Extract paragraphs
        paragraphs = []
        for elem in sel.css("p, div"):
            # Skip containers
            if elem.css("div"):
                continue

            text = "".join(elem.css("*::text").getall()).strip()

            # Skip donation notices and disclaimers
            text_lower = text.lower()
            if "donate" in text_lower and "nifty" in text_lower:
                continue
            if "disclaimer" in text_lower:
                continue
            if len(text) < 10:
                continue

            if text:
                paragraphs.append(text)

        result["text"] = "\n\n".join(paragraphs)
        result["word_count"] = len(result["text"].split())

        return result

    def _parse_email_story(self, html: str) -> Dict[str, Any]:
        """Parse email-formatted story (plain text)."""
        result = {
            "author": None,
            "author_email": None,
            "date": None,
            "title": None,
            "text": "",
            "word_count": 0
        }

        lines = html.split("\n")
        content_start = 0

        # Parse email headers
        for i, line in enumerate(lines):
            if line.startswith("From:"):
                match = re.match(r'From:\s*(.+?)\s*<([^>]+)>', line)
                if match:
                    result["author"] = match.group(1).strip()
                    result["author_email"] = match.group(2).strip()
                else:
                    result["author"] = line.replace("From:", "").strip()
            elif line.startswith("Date:"):
                result["date"] = line.replace("Date:", "").strip()
            elif line.startswith("Subject:"):
                result["title"] = line.replace("Subject:", "").strip()
            elif line.strip() == "" and i > 0:
                content_start = i + 1
                break

        content_lines = lines[content_start:]

        # Skip donation notices at beginning
        skip_until = 0
        for i, line in enumerate(content_lines[:20]):
            line_lower = line.lower()
            if "donate" in line_lower and "nifty" in line_lower:
                for j in range(i, min(i + 5, len(content_lines))):
                    if content_lines[j].strip() == "":
                        skip_until = j + 1
                        break
                break

        content_lines = content_lines[skip_until:]

        # Find and remove end promo content
        promo_markers = [
            "if you want to read", "if you enjoyed this",
            "support nifty", "patreon", "send feedback",
            "comments to:", "the end"
        ]

        content_end = len(content_lines)
        for i in range(len(content_lines) - 1, max(0, len(content_lines) - 30), -1):
            line_lower = content_lines[i].lower().strip()
            if any(marker in line_lower for marker in promo_markers):
                content_end = i
                break

        text = "\n".join(content_lines[:content_end]).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)

        result["text"] = text
        result["word_count"] = len(text.split())

        return result

    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze story content for enhanced metadata."""
        analysis = {
            "character_count": 2,
            "has_dialogue": False,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "setting": None,
            "quality_score": 0.5
        }

        text_lower = text.lower()

        # Detect dialogue
        dialogue_markers = text.count('"') + text.count("'")
        analysis["has_dialogue"] = dialogue_markers > 20

        # Detect POV
        first_person = len(re.findall(r'\bI\b', text)) + len(re.findall(r'\bmy\b', text_lower))
        third_person = len(re.findall(r'\bhe\b', text_lower)) + len(re.findall(r'\bhis\b', text_lower))
        if first_person > third_person * 1.5:
            analysis["pov"] = "first-person"

        # Character count from dialogue attribution
        name_pattern = re.findall(r'(?:said|asked|replied|whispered|moaned|groaned)\s+([A-Z][a-z]+)', text)
        unique_names = set(name_pattern)
        if len(unique_names) >= 2:
            analysis["character_count"] = len(unique_names)

        # Content intensity
        mild_terms = ["kiss", "touch", "hold", "embrace", "caress"]
        moderate_terms = ["naked", "hard", "stroke", "moan", "erect"]
        explicit_terms = ["cock", "dick", "fuck", "ass", "cum", "suck", "thrust"]

        mild_count = sum(text_lower.count(t) for t in mild_terms)
        moderate_count = sum(text_lower.count(t) for t in moderate_terms)
        explicit_count = sum(text_lower.count(t) for t in explicit_terms)

        if explicit_count > 10:
            analysis["content_intensity"] = "explicit"
        elif moderate_count > 5 or explicit_count > 3:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Relationship type
        relationship_markers = {
            "friends": ["friend", "buddy", "pal", "roommate"],
            "strangers": ["stranger", "never met", "first time seeing"],
            "authority": ["boss", "coach", "teacher", "professor", "officer"],
            "family": ["brother", "cousin", "uncle"],
            "romantic": ["boyfriend", "lover", "dating", "love you"],
        }
        for rel_type, markers in relationship_markers.items():
            if any(m in text_lower for m in markers):
                analysis["relationship_type"] = rel_type
                break

        # Setting detection
        setting_markers = {
            "bedroom": ["bed", "bedroom", "sheets", "pillow"],
            "dorm": ["dorm", "roommate", "campus", "college room"],
            "locker room": ["locker", "shower", "gym", "bench"],
            "office": ["office", "desk", "work"],
            "outdoors": ["woods", "beach", "park", "outside", "tent", "camping"],
            "car": ["car", "backseat", "truck", "parking"],
            "military": ["barracks", "base", "deployment", "uniform"],
        }
        for setting, markers in setting_markers.items():
            if any(m in text_lower for m in markers):
                analysis["setting"] = setting
                break

        # Quality score
        word_count = len(text.split())
        score = 0.5

        if word_count > 3000:
            score += 0.1
        if word_count > 6000:
            score += 0.1
        if analysis["has_dialogue"]:
            score += 0.1
        if analysis["character_count"] >= 2:
            score += 0.1
        if word_count < 1000:
            score -= 0.2

        analysis["quality_score"] = min(1.0, max(0.0, score))

        return analysis
