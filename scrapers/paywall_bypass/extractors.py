"""
Content Extraction - Intelligent article content extraction.
"""

import re
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urljoin


@dataclass
class ExtractedArticle:
    """Extracted article content."""
    url: str
    title: str
    author: Optional[str]
    date: Optional[str]
    content: str
    word_count: int
    images: List[str]
    metadata: Dict[str, Any]
    bypass_method: str
    cached: bool = False


class ContentExtractor:
    """
    Intelligent content extraction from HTML.

    Methods:
    1. JSON-LD structured data parsing
    2. Open Graph / meta tag extraction
    3. Readability-style content extraction
    4. Site-specific extraction rules
    5. Fallback heuristics
    """

    # Article container selectors (priority order)
    ARTICLE_SELECTORS = [
        "article",
        "[role='article']",
        "[itemtype*='Article']",
        ".article-content",
        ".article-body",
        ".article__body",
        ".post-content",
        ".entry-content",
        ".story-body",
        ".story-content",
        "#article-body",
        "#story-body",
        ".content-article",
        ".article-text",
        ".post-body",
        "main article",
        "main .content",
        ".main-content",
        "#main-content",
    ]

    # Elements to remove
    REMOVE_SELECTORS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        ".advertisement",
        ".ad",
        ".ads",
        ".social-share",
        ".share-buttons",
        ".related-articles",
        ".recommended",
        ".newsletter",
        ".subscription",
        ".paywall",
        ".comments",
        "#comments",
        ".sidebar",
        ".nav",
        ".menu",
        ".breadcrumb",
        ".author-bio",
        ".more-stories",
    ]

    # Title selectors
    TITLE_SELECTORS = [
        "h1",
        "[itemprop='headline']",
        ".article-title",
        ".post-title",
        ".entry-title",
        ".story-headline",
        "meta[property='og:title']",
        "meta[name='title']",
    ]

    # Author selectors
    AUTHOR_SELECTORS = [
        "[itemprop='author']",
        "[rel='author']",
        ".author-name",
        ".byline",
        ".article-author",
        ".post-author",
        "meta[name='author']",
        "meta[property='article:author']",
    ]

    # Date selectors
    DATE_SELECTORS = [
        "[itemprop='datePublished']",
        "[datetime]",
        ".publish-date",
        ".article-date",
        ".post-date",
        "time",
        "meta[property='article:published_time']",
        "meta[name='date']",
    ]

    def __init__(self):
        self.site_rules: Dict[str, Dict] = {}

    async def extract(
        self,
        url: str,
        content: str,
        raw_html: str,
        bypass_method: str = "unknown"
    ) -> Optional[ExtractedArticle]:
        """
        Extract article content from HTML.

        Args:
            url: Original URL
            content: Pre-extracted content (if any)
            raw_html: Full HTML
            bypass_method: Method used to get content

        Returns:
            ExtractedArticle if successful
        """
        # Try JSON-LD first (most reliable)
        jsonld = self._extract_jsonld(raw_html)
        if jsonld and self._validate_jsonld_article(jsonld):
            return self._build_from_jsonld(url, jsonld, raw_html, bypass_method)

        # Try Open Graph
        og_data = self._extract_opengraph(raw_html)

        # Try structured extraction
        title = self._extract_title(raw_html, og_data)
        author = self._extract_author(raw_html, og_data)
        date = self._extract_date(raw_html, og_data)
        article_content = self._extract_content(raw_html, content)
        images = self._extract_images(raw_html, url)

        # Validate we got meaningful content
        if not article_content or len(article_content) < 100:
            return None

        word_count = len(article_content.split())

        return ExtractedArticle(
            url=url,
            title=title or "Untitled",
            author=author,
            date=date,
            content=article_content,
            word_count=word_count,
            images=images,
            metadata={
                "og": og_data,
                "extraction_method": "heuristic"
            },
            bypass_method=bypass_method
        )

    def _extract_jsonld(self, html: str) -> Optional[Dict]:
        """Extract JSON-LD structured data."""
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match.strip())

                # Handle array of items
                if isinstance(data, list):
                    for item in data:
                        if self._is_article_type(item):
                            return item
                elif self._is_article_type(data):
                    return data

                # Check @graph
                if isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if self._is_article_type(item):
                            return item

            except (json.JSONDecodeError, KeyError):
                continue

        return None

    def _is_article_type(self, data: Dict) -> bool:
        """Check if JSON-LD data represents an article."""
        article_types = [
            "Article", "NewsArticle", "BlogPosting", "WebPage",
            "ReportageNewsArticle", "AnalysisNewsArticle",
            "OpinionNewsArticle", "ReviewNewsArticle"
        ]

        item_type = data.get("@type", "")

        if isinstance(item_type, list):
            return any(t in article_types for t in item_type)
        return item_type in article_types

    def _validate_jsonld_article(self, data: Dict) -> bool:
        """Validate JSON-LD has enough content."""
        article_body = data.get("articleBody", "")
        if article_body and len(article_body) > 500:
            return True

        # Check for content in other fields
        text = data.get("text", "")
        if text and len(text) > 500:
            return True

        return False

    def _build_from_jsonld(
        self,
        url: str,
        data: Dict,
        raw_html: str,
        bypass_method: str
    ) -> ExtractedArticle:
        """Build ExtractedArticle from JSON-LD data."""
        # Extract content
        content = data.get("articleBody") or data.get("text", "")

        # Extract title
        title = data.get("headline") or data.get("name", "Untitled")

        # Extract author
        author = None
        author_data = data.get("author")
        if author_data:
            if isinstance(author_data, dict):
                author = author_data.get("name")
            elif isinstance(author_data, list) and author_data:
                author = author_data[0].get("name") if isinstance(author_data[0], dict) else str(author_data[0])
            else:
                author = str(author_data)

        # Extract date
        date = data.get("datePublished") or data.get("dateCreated")

        # Extract images
        images = []
        image_data = data.get("image")
        if image_data:
            if isinstance(image_data, str):
                images.append(image_data)
            elif isinstance(image_data, dict):
                images.append(image_data.get("url", ""))
            elif isinstance(image_data, list):
                for img in image_data:
                    if isinstance(img, str):
                        images.append(img)
                    elif isinstance(img, dict):
                        images.append(img.get("url", ""))

        # Also extract images from HTML
        images.extend(self._extract_images(raw_html, url))
        images = list(set(images))  # Dedupe

        return ExtractedArticle(
            url=url,
            title=title,
            author=author,
            date=date,
            content=content,
            word_count=len(content.split()),
            images=images,
            metadata={
                "jsonld": data,
                "extraction_method": "jsonld"
            },
            bypass_method=bypass_method
        )

    def _extract_opengraph(self, html: str) -> Dict[str, str]:
        """Extract Open Graph meta tags."""
        og_data = {}

        # OG tags
        og_pattern = r'<meta[^>]*property=["\']og:([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']'
        for match in re.finditer(og_pattern, html, re.IGNORECASE):
            og_data[f"og:{match.group(1)}"] = match.group(2)

        # Reverse pattern (content before property)
        og_pattern_rev = r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:([^"\']+)["\']'
        for match in re.finditer(og_pattern_rev, html, re.IGNORECASE):
            og_data[f"og:{match.group(2)}"] = match.group(1)

        # Article tags
        article_pattern = r'<meta[^>]*property=["\']article:([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']'
        for match in re.finditer(article_pattern, html, re.IGNORECASE):
            og_data[f"article:{match.group(1)}"] = match.group(2)

        return og_data

    def _extract_title(self, html: str, og_data: Dict) -> Optional[str]:
        """Extract article title."""
        # Try OG title
        if "og:title" in og_data:
            return og_data["og:title"]

        # Try h1
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        if h1_match:
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            if title:
                return title

        # Try title tag
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # Clean up common patterns
            title = re.sub(r'\s*[\|–-]\s*.*$', '', title)
            return title

        return None

    def _extract_author(self, html: str, og_data: Dict) -> Optional[str]:
        """Extract article author."""
        # Try article:author
        if "article:author" in og_data:
            return og_data["article:author"]

        # Try meta author
        author_match = re.search(
            r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if author_match:
            return author_match.group(1)

        # Try byline class
        byline_match = re.search(
            r'<[^>]*class=["\'][^"\']*byline[^"\']*["\'][^>]*>(.*?)</[^>]+>',
            html, re.DOTALL | re.IGNORECASE
        )
        if byline_match:
            author = re.sub(r'<[^>]+>', '', byline_match.group(1)).strip()
            # Clean common patterns
            author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
            if author and len(author) < 100:
                return author

        # Try itemprop author
        itemprop_match = re.search(
            r'<[^>]*itemprop=["\']author["\'][^>]*>(.*?)</[^>]+>',
            html, re.DOTALL | re.IGNORECASE
        )
        if itemprop_match:
            author = re.sub(r'<[^>]+>', '', itemprop_match.group(1)).strip()
            if author:
                return author

        return None

    def _extract_date(self, html: str, og_data: Dict) -> Optional[str]:
        """Extract publication date."""
        # Try article:published_time
        if "article:published_time" in og_data:
            return og_data["article:published_time"]

        # Try datetime attribute
        datetime_match = re.search(
            r'<time[^>]*datetime=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if datetime_match:
            return datetime_match.group(1)

        # Try itemprop datePublished
        itemprop_match = re.search(
            r'<[^>]*itemprop=["\']datePublished["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if itemprop_match:
            return itemprop_match.group(1)

        # Try meta date
        meta_match = re.search(
            r'<meta[^>]*name=["\']date["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if meta_match:
            return meta_match.group(1)

        return None

    def _extract_content(self, html: str, pre_content: str) -> str:
        """Extract main article content."""
        # If we have good pre-content, use it
        if pre_content and len(pre_content) > 500:
            return pre_content

        # Clean HTML first
        cleaned = self._remove_unwanted_elements(html)

        # Try to find article content
        for selector in self.ARTICLE_SELECTORS:
            content = self._extract_by_selector(cleaned, selector)
            if content and len(content) > 500:
                return content

        # Fallback: find largest text block
        return self._find_largest_text_block(cleaned)

    def _remove_unwanted_elements(self, html: str) -> str:
        """Remove unwanted elements from HTML."""
        # Remove script and style
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove comments
        cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

        # Remove common noise elements
        noise_patterns = [
            r'<nav[^>]*>.*?</nav>',
            r'<header[^>]*>.*?</header>',
            r'<footer[^>]*>.*?</footer>',
            r'<aside[^>]*>.*?</aside>',
            r'<div[^>]*class=["\'][^"\']*(?:ad|advertisement|sidebar|social|share|related|comment)[^"\']*["\'][^>]*>.*?</div>',
        ]

        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        return cleaned

    def _extract_by_selector(self, html: str, selector: str) -> Optional[str]:
        """Extract content by CSS-like selector (simplified)."""
        # Handle tag selectors
        if selector.startswith("["):
            # Attribute selector
            attr_match = re.match(r'\[([^=\]]+)(?:=["\']?([^"\'\]]+)["\']?)?\]', selector)
            if attr_match:
                attr, value = attr_match.groups()
                if value:
                    pattern = rf'<[^>]*{attr}=["\'][^"\']*{value}[^"\']*["\'][^>]*>(.*?)</[^>]+>'
                else:
                    pattern = rf'<[^>]*{attr}[^>]*>(.*?)</[^>]+>'
        elif selector.startswith("."):
            # Class selector
            class_name = selector[1:]
            pattern = rf'<[^>]*class=["\'][^"\']*{class_name}[^"\']*["\'][^>]*>(.*?)</[^>]+>'
        elif selector.startswith("#"):
            # ID selector
            id_name = selector[1:]
            pattern = rf'<[^>]*id=["\']?{id_name}["\']?[^>]*>(.*?)</[^>]+>'
        else:
            # Tag selector
            tag = selector.split()[0]
            pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'

        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
            # Strip remaining tags
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            return content

        return None

    def _find_largest_text_block(self, html: str) -> str:
        """Find the largest continuous text block."""
        # Split by major block elements
        blocks = re.split(r'<(?:div|section|article|p)[^>]*>', html)

        largest = ""
        for block in blocks:
            # Strip tags
            text = re.sub(r'<[^>]+>', ' ', block)
            text = re.sub(r'\s+', ' ', text).strip()

            # Skip very short blocks
            if len(text) > len(largest) and len(text.split()) > 50:
                largest = text

        return largest

    def _extract_images(self, html: str, base_url: str) -> List[str]:
        """Extract article images."""
        images = []
        parsed = urlparse(base_url)

        # Find img tags
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(img_pattern, html, re.IGNORECASE):
            src = match.group(1)

            # Skip common non-article images
            skip_patterns = [
                r'logo', r'icon', r'avatar', r'button', r'arrow',
                r'spinner', r'loading', r'ad', r'pixel', r'tracking',
                r'\.gif$', r'1x1', r'spacer'
            ]
            if any(re.search(p, src, re.IGNORECASE) for p in skip_patterns):
                continue

            # Resolve relative URLs
            if src.startswith("//"):
                src = f"{parsed.scheme}:{src}"
            elif src.startswith("/"):
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            elif not src.startswith("http"):
                src = urljoin(base_url, src)

            if src not in images:
                images.append(src)

        return images[:10]  # Limit to 10 images

    def set_site_rule(self, domain: str, rule: Dict):
        """Set custom extraction rule for a domain."""
        self.site_rules[domain] = rule

    async def extract_with_rule(
        self,
        url: str,
        html: str,
        rule: Dict
    ) -> Optional[ExtractedArticle]:
        """Extract using site-specific rule."""
        content_selector = rule.get("content_selector")
        title_selector = rule.get("title_selector")
        author_selector = rule.get("author_selector")
        date_selector = rule.get("date_selector")

        content = self._extract_by_selector(html, content_selector) if content_selector else None
        title = self._extract_by_selector(html, title_selector) if title_selector else None
        author = self._extract_by_selector(html, author_selector) if author_selector else None
        date = self._extract_by_selector(html, date_selector) if date_selector else None

        if not content or len(content) < 100:
            return None

        return ExtractedArticle(
            url=url,
            title=title or "Untitled",
            author=author,
            date=date,
            content=content,
            word_count=len(content.split()),
            images=self._extract_images(html, url),
            metadata={"rule": rule, "extraction_method": "site_rule"},
            bypass_method="site_rule"
        )
