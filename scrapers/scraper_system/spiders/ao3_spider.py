"""
SAM Scraper System - Archive of Our Own Spider

Scrapes M/M explicit fiction from AO3 for training data.
Integrates with the scraper_system for scheduling, resource management, and storage.

Based on ao3_ripper.py, converted to Scrapy.
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Iterator
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class AO3Spider(BaseSpider):
    """
    Spider for Archive of Our Own (AO3).

    Features:
    - Searches M/M explicit fiction by tag
    - Extracts rich metadata (kudos, hits, tags, relationships)
    - Full work download with chapter content
    - Content analysis for training data quality
    """

    name = "ao3_spider"
    source = "ao3"
    allowed_domains = ["archiveofourown.org"]

    # AO3-specific settings
    rate_limit = 3.0  # AO3 is stricter - be respectful
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 3.0,
        "CONCURRENT_REQUESTS": 1,
        "COOKIES_ENABLED": True,
    }

    # Search filters for M/M explicit content
    SEARCH_FILTERS = {
        "work_search[category_ids][]": "23",  # M/M category
        "work_search[rating_ids][]": "13",    # Explicit rating
        "work_search[complete]": "T",          # Complete works only
        "work_search[language_id]": "en",      # English
        "work_search[sort_column]": "kudos_count",
        "work_search[sort_direction]": "desc",
    }

    # NC-specific search filters (adds Rape/Non-Con warning requirement)
    NC_SEARCH_FILTERS = {
        "work_search[category_ids][]": "23",  # M/M category
        "work_search[rating_ids][]": "13",    # Explicit rating
        "work_search[archive_warning_ids][]": "19",  # Rape/Non-Con warning
        "work_search[complete]": "T",          # Complete works only
        "work_search[language_id]": "en",      # English
        "work_search[sort_column]": "kudos_count",
        "work_search[sort_direction]": "desc",
    }

    # Tags to search (general)
    TAG_SEARCHES = [
        None,  # Main search (no specific tag)
        "Gay Sex",
        "Anal Sex",
        "First Time",
        "Friends to Lovers",
        "Enemies to Lovers",
        "Slow Burn",
        "PWP",
        "Smut",
        "Romance",
    ]

    # NC-specific tags to search
    NC_TAG_SEARCHES = [
        None,  # Main NC search (no specific tag, just warning filter)
        "Non-Consensual",
        "Rape",
        "Dubious Consent",
        "Dubcon",
        "Noncon",
        "Forced",
        "Coercion",
        "Dark",
        "Dead Dove: Do Not Eat",
        "Rape/Non-con Elements",
        "Non-Consensual Touching",
        "Non-Consensual Blow Jobs",
        "Non-Consensual Oral Sex",
        "Sexual Coercion",
        "Blackmail",
        "Manipulation",
        "Power Imbalance",
        "Abuse of Authority",
        "Captivity",
        "Kidnapping",
        "Sexual Slavery",
        "Drugged Sex",
        "Date Rape Drug/Roofies",
        "Somnophilia",
        "Gang Rape",
        "Gangbang",
        "Breeding",
        "Forced Feminization",
        "Forced Prostitution",
        "Human Trafficking",
        "Stockholm Syndrome",
        "Gaslighting",
        "Psychological Manipulation",
        "Incest",
        "Parent/Child Incest",
        "Sibling Incest",
        "Uncle/Nephew Incest",
        "Pseudo-Incest",
        "Step-parent Incest",
        "Age Difference",
        "Older Man/Younger Man",
        "Authority Figures",
        "Teacher-Student Relationship",
        "Boss/Employee Relationship",
        "Prison Sex",
        "Priest Kink",
        "Medical Kink",
        "Sadism",
        "Masochism",
        "BDSM Gone Wrong",
        "Rough Sex",
        "Violent Sex",
        "Choking",
        "Degradation",
        "Humiliation",
        "Objectification",
        "Dehumanization",
        "Crying During Sex",
        "Begging",
        "Helplessness",
        "Fear",
        "Trauma",
        "Aftermath of Violence",
        "Rape Aftermath",
        "Rape Recovery",
        "Past Rape/Non-con",
        "Tentacle Rape",
        "Monster Rape",
        "Alien Sex",
        "Werewolf Sex",
        "Vampire Sex",
        "Demon Sex",
        "Creature Fic",
    ]

    def __init__(self, *args, max_pages: int = 20, min_kudos: int = 100,
                 min_words: int = 2000, tag: str = None, nc_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = max_pages
        self.min_kudos = min_kudos
        self.min_words = min_words
        self.specific_tag = tag
        self.nc_mode = nc_mode
        self.current_page = 1
        self.current_tag_index = 0

        # Select appropriate tag list and filters based on mode
        if self.nc_mode:
            self.active_tags = self.NC_TAG_SEARCHES
            self.active_filters = self.NC_SEARCH_FILTERS
            self.logger.info("NC MODE ENABLED - targeting non-consent content")
        else:
            self.active_tags = self.TAG_SEARCHES
            self.active_filters = self.SEARCH_FILTERS

    def start_requests(self) -> Iterator[Request]:
        """Start by visiting homepage to establish session, then search."""
        # First hit homepage to get session cookies (required by CloudFlare/AO3)
        yield self.make_request(
            "https://archiveofourown.org/",
            callback=self._after_homepage,
            meta={"dont_redirect": False}
        )

    def _after_homepage(self, response: Response) -> Iterator[Request]:
        """After homepage loads (cookies set), start searching."""
        self.logger.info(f"Homepage loaded, cookies established. Starting search...")

        # Resume from progress if available
        progress = self.get_progress()
        self.current_page = progress.get("last_page", 0) + 1
        self.current_tag_index = progress.get("last_tag_index", 0)

        if self.specific_tag:
            # Search specific tag only
            yield self._make_search_request(self.specific_tag, self.current_page)
        else:
            # Search all configured tags
            tag = self.active_tags[self.current_tag_index]
            yield self._make_search_request(tag, self.current_page)

    def _make_search_request(self, tag: Optional[str], page: int) -> Request:
        """Build a search request."""
        params = dict(self.active_filters)
        if tag:
            params["work_search[query]"] = tag
        params["page"] = str(page)

        url = f"https://archiveofourown.org/works/search?{urlencode(params)}"
        return self.make_request(
            url,
            callback=self.parse_search,
            meta={"tag": tag, "page": page}
        )

    def parse_search(self, response: Response) -> Iterator[Any]:
        """Parse search results page."""
        tag = response.meta.get("tag")
        page = response.meta.get("page", 1)

        self.logger.info(f"Parsing search page {page} for tag: {tag or 'all'}")

        # Find all work blurbs
        works = response.css("li.work.blurb")
        works_found = 0

        for work in works:
            work_data = self._parse_work_blurb(work)
            if work_data:
                # Check minimum requirements
                if work_data["kudos"] >= self.min_kudos and work_data["word_count"] >= self.min_words:
                    # Request full work page
                    work_url = f"https://archiveofourown.org/works/{work_data['ao3_id']}?view_adult=true&view_full_work=true"
                    yield self.make_request(
                        work_url,
                        callback=self.parse_work,
                        meta={"work_data": work_data}
                    )
                    works_found += 1

        self.logger.info(f"Found {works_found} qualifying works on page {page}")

        # Save progress
        self.save_progress(last_page=page, last_tag_index=self.current_tag_index)

        # Continue to next page or next tag
        if works_found > 0 and page < self.max_pages:
            yield self._make_search_request(tag, page + 1)
        elif not self.specific_tag:
            # Move to next tag
            self.current_tag_index += 1
            if self.current_tag_index < len(self.active_tags):
                next_tag = self.active_tags[self.current_tag_index]
                yield self._make_search_request(next_tag, 1)

    def _parse_work_blurb(self, work) -> Optional[Dict]:
        """Parse a work blurb from search results."""
        # Get work ID
        work_id_match = re.search(r'work_(\d+)', work.attrib.get("id", ""))
        if not work_id_match:
            return None

        ao3_id = int(work_id_match.group(1))

        # Title
        title_elem = work.css("h4.heading a::text").get()
        title = title_elem.strip() if title_elem else "Untitled"

        # Author
        author_elem = work.css("h4.heading a[rel='author']::text").get()
        author = author_elem.strip() if author_elem else "Anonymous"

        # Rating
        rating = work.css("span.rating::text").get() or "Not Rated"

        # Category
        category = work.css("span.category::text").get() or ""

        # Fandoms
        fandoms = work.css("h5.fandoms a.tag::text").getall()

        # Relationships
        relationships = work.css("li.relationships a.tag::text").getall()

        # Characters
        characters = work.css("li.characters a.tag::text").getall()

        # Tags
        tags = work.css("li.freeforms a.tag::text").getall()

        # Warnings
        warnings = work.css("li.warnings a.tag::text").getall()

        # Stats
        word_count = 0
        kudos = 0
        hits = 0
        bookmarks = 0
        comments = 0
        chapter_count = 0

        words_text = work.css("dd.words::text").get()
        if words_text:
            try:
                word_count = int(words_text.replace(",", ""))
            except ValueError:
                pass

        kudos_text = work.css("dd.kudos a::text").get() or work.css("dd.kudos::text").get()
        if kudos_text:
            try:
                kudos = int(kudos_text.replace(",", ""))
            except ValueError:
                pass

        hits_text = work.css("dd.hits::text").get()
        if hits_text:
            try:
                hits = int(hits_text.replace(",", ""))
            except ValueError:
                pass

        bookmarks_text = work.css("dd.bookmarks a::text").get()
        if bookmarks_text:
            try:
                bookmarks = int(bookmarks_text.replace(",", ""))
            except ValueError:
                pass

        comments_text = work.css("dd.comments a::text").get()
        if comments_text:
            try:
                comments = int(comments_text.replace(",", ""))
            except ValueError:
                pass

        chapters_text = work.css("dd.chapters::text").get()
        if chapters_text:
            chapter_match = re.match(r'(\d+)', chapters_text)
            if chapter_match:
                chapter_count = int(chapter_match.group(1))

        # Date
        date_published = work.css("p.datetime::text").get() or ""

        # Summary
        summary = work.css("blockquote.summary::text").get() or ""

        # Complete status
        complete = "/" in (chapters_text or "") and not (chapters_text or "").endswith("/?")

        return {
            "ao3_id": ao3_id,
            "title": title,
            "author": author,
            "rating": rating,
            "category": category,
            "fandoms": fandoms,
            "relationships": relationships,
            "characters": characters,
            "tags": tags,
            "warnings": warnings,
            "word_count": word_count,
            "chapter_count": chapter_count,
            "kudos": kudos,
            "hits": hits,
            "bookmarks": bookmarks,
            "comments": comments,
            "date_published": date_published,
            "summary": summary,
            "complete": complete,
        }

    def parse_work(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse full work page and extract content."""
        work_data = response.meta.get("work_data", {})
        ao3_id = work_data.get("ao3_id")

        self.logger.info(f"Parsing work: {work_data.get('title')} (ID: {ao3_id})")

        # Extract story text from chapter content
        chapters = response.css("div.userstuff")
        if not chapters:
            self.logger.warning(f"No content found for work {ao3_id}")
            return

        # Combine all chapter text
        full_text = []
        for chapter in chapters:
            # Remove notes sections
            for notes in chapter.css(".notes"):
                notes.root.drop_tree()

            text = chapter.css("*::text").getall()
            chapter_text = " ".join(t.strip() for t in text if t.strip())
            if chapter_text:
                full_text.append(chapter_text)

        story_text = "\n\n---\n\n".join(full_text)

        if len(story_text) < 500:
            self.logger.warning(f"Insufficient content for work {ao3_id}")
            return

        # Analyze content
        analysis = self._analyze_content(story_text)

        # Build combined tags
        all_tags = work_data.get("tags", []) + [work_data.get("rating", ""), work_data.get("category", "")]
        if analysis["content_intensity"]:
            all_tags.append(analysis["content_intensity"])
        if analysis["relationship_type"]:
            all_tags.append(analysis["relationship_type"])

        # Build metadata
        metadata = {
            "ao3_id": ao3_id,
            "author": work_data.get("author"),
            "rating": work_data.get("rating"),
            "category": work_data.get("category"),
            "fandoms": work_data.get("fandoms", []),
            "relationships": work_data.get("relationships", []),
            "characters": work_data.get("characters", []),
            "warnings": work_data.get("warnings", []),
            "kudos": work_data.get("kudos", 0),
            "hits": work_data.get("hits", 0),
            "bookmarks": work_data.get("bookmarks", 0),
            "comments": work_data.get("comments", 0),
            "chapter_count": work_data.get("chapter_count", 1),
            "date_published": work_data.get("date_published"),
            "summary": work_data.get("summary"),
            "complete": work_data.get("complete", True),
            # Analysis results
            "character_count": analysis["character_count"],
            "has_dialogue": analysis["has_dialogue"],
            "pov": analysis["pov"],
            "content_intensity": analysis["content_intensity"],
            "relationship_type": analysis["relationship_type"],
            "setting": analysis["setting"],
            "quality_score": analysis["quality_score"],
            "tags": all_tags,
        }

        # Create ScrapedItem
        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=work_data.get("title", "Untitled"),
            content=story_text,
            metadata=metadata,
        )

        yield item

    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze story content for enhanced metadata."""
        analysis = {
            "character_count": 2,
            "has_dialogue": False,
            "pov": "third-person",
            "content_intensity": "moderate",
            "relationship_type": None,
            "setting": None,
            "quality_score": 0.5,
            # NC-specific analysis fields
            "nc_indicators": [],
            "perpetrator_type": None,
            "scenario_layers": [],
            "nc_score": 0.0,
        }

        text_lower = text.lower()

        # Detect dialogue
        dialogue_markers = text.count('"') + text.count('"') + text.count('"')
        analysis["has_dialogue"] = dialogue_markers > 20

        # Detect POV
        first_person = len(re.findall(r'\bI\b', text)) + len(re.findall(r'\bmy\b', text_lower))
        third_person = len(re.findall(r'\bhe\b', text_lower)) + len(re.findall(r'\bhis\b', text_lower))
        if first_person > third_person * 1.5:
            analysis["pov"] = "first-person"

        # Content intensity
        explicit_terms = ["cock", "dick", "fuck", "ass", "cum", "suck"]
        moderate_terms = ["naked", "hard", "stroke", "moan"]

        explicit_count = sum(text_lower.count(t) for t in explicit_terms)
        moderate_count = sum(text_lower.count(t) for t in moderate_terms)

        if explicit_count > 15:
            analysis["content_intensity"] = "explicit"
        elif moderate_count > 5 or explicit_count > 5:
            analysis["content_intensity"] = "moderate"
        else:
            analysis["content_intensity"] = "mild"

        # Relationship type
        rel_markers = {
            "friends": ["friend", "buddy", "roommate"],
            "strangers": ["stranger", "never met"],
            "enemies": ["enemy", "rival", "hate"],
            "romantic": ["boyfriend", "lover", "love you"],
        }
        for rel_type, markers in rel_markers.items():
            if any(m in text_lower for m in markers):
                analysis["relationship_type"] = rel_type
                break

        # NC-specific analysis
        if self.nc_mode:
            analysis.update(self._analyze_nc_content(text_lower))

        # Quality score
        word_count = len(text.split())
        score = 0.5
        if word_count > 5000:
            score += 0.1
        if word_count > 10000:
            score += 0.1
        if analysis["has_dialogue"]:
            score += 0.1
        if word_count < 2000:
            score -= 0.1
        # Boost score for NC content with good indicators
        if analysis.get("nc_score", 0) > 0.5:
            score += 0.2

        analysis["quality_score"] = min(1.0, max(0.0, score))

        return analysis

    def _analyze_nc_content(self, text_lower: str) -> Dict[str, Any]:
        """Analyze content for NC-specific patterns."""
        nc_analysis = {
            "nc_indicators": [],
            "perpetrator_type": None,
            "scenario_layers": [],
            "nc_score": 0.0,
        }

        # NC indicator patterns
        nc_indicators = {
            "coercion": ["forced", "made him", "had no choice", "couldn't refuse", "threatened"],
            "resistance": ["struggled", "fought", "tried to stop", "pushed away", "begged him to stop"],
            "fear": ["terrified", "scared", "afraid", "trembling", "shaking with fear"],
            "power_imbalance": ["helpless", "powerless", "couldn't escape", "trapped", "pinned"],
            "verbal_nc": ["stop", "please don't", "no", "let me go", "don't want"],
            "physical_force": ["held down", "pinned", "grabbed", "restrained", "tied"],
            "aftermath": ["violated", "used", "broken", "ruined", "shame"],
            "dissociation": ["went away", "somewhere else", "not really there", "floating", "numb"],
        }

        indicator_count = 0
        for category, markers in nc_indicators.items():
            matches = sum(1 for m in markers if m in text_lower)
            if matches > 0:
                nc_analysis["nc_indicators"].append(category)
                indicator_count += matches

        # Perpetrator type detection
        perp_patterns = {
            "authority": ["boss", "teacher", "coach", "officer", "doctor", "priest", "professor"],
            "intimate": ["boyfriend", "partner", "husband", "date", "lover"],
            "stranger": ["stranger", "man he didn't know", "unfamiliar", "random"],
            "trusted": ["friend", "uncle", "neighbor", "family friend", "mentor"],
            "predator": ["stalked", "watched", "followed", "waited", "planned"],
            "sadist": ["enjoyed", "laughed", "smiled as", "pleasure from pain"],
            "entitled": ["deserved", "owed", "belonged to", "mine to"],
            "opportunist": ["drunk", "passed out", "asleep", "vulnerable"],
        }

        for perp_type, markers in perp_patterns.items():
            if any(m in text_lower for m in markers):
                nc_analysis["perpetrator_type"] = perp_type
                break

        # Scenario layer detection
        scenario_patterns = {
            "incest": ["father", "dad", "brother", "uncle", "stepfather", "stepdad", "family"],
            "drugged": ["drugged", "roofied", "slipped something", "drink was", "felt dizzy"],
            "blackmail": ["blackmail", "secret", "tell everyone", "photos", "video"],
            "kidnapped": ["kidnapped", "abducted", "taken", "van", "basement"],
            "prison": ["prison", "jail", "cell", "inmate", "guard"],
            "gang": ["gang", "group", "multiple", "took turns", "one after another"],
            "workplace": ["office", "work", "job", "promotion", "fired"],
            "school": ["school", "class", "dorm", "campus", "student"],
            "military": ["soldier", "army", "barracks", "military", "sergeant"],
            "medical": ["hospital", "doctor", "exam", "clinic", "patient"],
            "religious": ["church", "priest", "confession", "religious", "congregation"],
            "monster": ["creature", "monster", "beast", "tentacle", "alien"],
        }

        for scenario, markers in scenario_patterns.items():
            if any(m in text_lower for m in markers):
                nc_analysis["scenario_layers"].append(scenario)

        # Calculate NC score (0-1)
        score = 0.0
        score += min(0.4, indicator_count * 0.05)  # Up to 0.4 for indicators
        score += 0.2 if nc_analysis["perpetrator_type"] else 0
        score += min(0.3, len(nc_analysis["scenario_layers"]) * 0.1)  # Up to 0.3 for scenarios
        score += 0.1 if len(nc_analysis["nc_indicators"]) >= 3 else 0

        nc_analysis["nc_score"] = min(1.0, score)

        return nc_analysis
