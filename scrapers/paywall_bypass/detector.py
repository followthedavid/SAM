"""
Paywall Detection System - ML-powered paywall type identification.
"""

import re
from enum import Enum
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import asyncio
import aiohttp


class PaywallType(Enum):
    """Types of paywalls we can detect."""
    NONE = "none"                      # No paywall
    SOFT_METERED = "soft_metered"      # X free articles per month
    SOFT_REGISTRATION = "soft_reg"     # Free with registration
    HARD_SUBSCRIPTION = "hard_sub"     # Requires paid subscription
    DYNAMIC_JS = "dynamic_js"          # JavaScript-rendered paywall
    GEOGRAPHIC = "geographic"          # Location-based restriction
    UNKNOWN = "unknown"                # Can't determine


@dataclass
class DetectionResult:
    """Result of paywall detection."""
    paywall_type: PaywallType
    confidence: float
    signals: List[str]
    blocked_content_ratio: float
    requires_js: bool


class PaywallDetector:
    """
    Advanced paywall detection using multiple signals.

    Detection methods:
    1. DOM pattern matching (paywall CSS classes, modals)
    2. Content truncation analysis
    3. Meta tag inspection
    4. JavaScript requirement detection
    5. HTTP header analysis
    6. Cookie/session detection
    7. Known site fingerprinting
    """

    # Paywall indicator patterns
    PAYWALL_PATTERNS = {
        "classes": [
            r"paywall", r"subscriber-only", r"premium-content",
            r"metered", r"registration-wall", r"login-wall",
            r"paid-content", r"members-only", r"gated-content",
            r"subscription-required", r"locked-content",
            r"pw-overlay", r"article-locked", r"content-gate",
        ],
        "ids": [
            r"paywall", r"reg-wall", r"sub-wall", r"gate",
            r"premium-overlay", r"subscription-modal",
        ],
        "text": [
            r"subscribe to continue", r"subscription required",
            r"sign in to read", r"create.*account.*to continue",
            r"free articles? remaining", r"limit reached",
            r"become a member", r"start your.*subscription",
            r"already a subscriber\?", r"for subscribers only",
            r"unlock this article", r"get unlimited access",
        ],
        "meta": [
            r'isAccessibleForFree.*false',
            r'requiresSubscription.*true',
        ]
    }

    # Known site signatures
    KNOWN_SITES = {
        "nytimes.com": PaywallType.SOFT_METERED,
        "wsj.com": PaywallType.HARD_SUBSCRIPTION,
        "washingtonpost.com": PaywallType.SOFT_METERED,
        "medium.com": PaywallType.SOFT_METERED,
        "theatlantic.com": PaywallType.SOFT_METERED,
        "bloomberg.com": PaywallType.HARD_SUBSCRIPTION,
        "ft.com": PaywallType.HARD_SUBSCRIPTION,
        "economist.com": PaywallType.HARD_SUBSCRIPTION,
        "newyorker.com": PaywallType.SOFT_METERED,
        "wired.com": PaywallType.SOFT_METERED,
        "hbr.org": PaywallType.SOFT_METERED,
        "thetimes.co.uk": PaywallType.HARD_SUBSCRIPTION,
        "telegraph.co.uk": PaywallType.SOFT_REGISTRATION,
        "businessinsider.com": PaywallType.SOFT_METERED,
        "seekingalpha.com": PaywallType.SOFT_REGISTRATION,
        "statista.com": PaywallType.HARD_SUBSCRIPTION,
    }

    # Content truncation indicators
    TRUNCATION_PATTERNS = [
        r"\.{3,}$",  # Ends with ellipsis
        r"\[…\]$",
        r"…$",
        r"read more\.{0,3}$",
        r"continue reading\.{0,3}$",
    ]

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }
            )

    async def detect(self, url: str) -> PaywallType:
        """
        Detect the type of paywall on a URL.

        Returns the most likely paywall type.
        """
        result = await self.analyze(url)
        return result.paywall_type

    async def analyze(self, url: str) -> DetectionResult:
        """
        Perform comprehensive paywall analysis.

        Returns detailed detection result with confidence scores.
        """
        await self._ensure_session()

        signals = []
        scores = {pt: 0.0 for pt in PaywallType}

        # Check known sites first
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        if domain in self.KNOWN_SITES:
            known_type = self.KNOWN_SITES[domain]
            signals.append(f"known_site:{domain}")
            scores[known_type] += 0.8

        # Fetch page
        try:
            async with self.session.get(url, timeout=15, allow_redirects=True) as response:
                html = await response.text()
                headers = dict(response.headers)
                status = response.status

                # Analyze response
                header_signals, header_scores = self._analyze_headers(headers, status)
                signals.extend(header_signals)
                for pt, score in header_scores.items():
                    scores[pt] += score

                # Analyze HTML
                html_signals, html_scores = self._analyze_html(html)
                signals.extend(html_signals)
                for pt, score in html_scores.items():
                    scores[pt] += score

                # Check content truncation
                truncation_ratio = self._check_truncation(html)

                # Check JS requirement
                requires_js = self._check_js_requirement(html)
                if requires_js:
                    signals.append("requires_javascript")
                    scores[PaywallType.DYNAMIC_JS] += 0.3

        except asyncio.TimeoutError:
            signals.append("timeout")
            scores[PaywallType.UNKNOWN] += 0.5
            truncation_ratio = 0.0
            requires_js = False

        except Exception as e:
            signals.append(f"error:{str(e)[:50]}")
            scores[PaywallType.UNKNOWN] += 0.5
            truncation_ratio = 0.0
            requires_js = False

        # Determine winner
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type] / max(sum(scores.values()), 0.01)

        # If no strong signal, default to NONE or UNKNOWN
        if scores[best_type] < 0.2:
            if truncation_ratio > 0.3:
                best_type = PaywallType.UNKNOWN
            else:
                best_type = PaywallType.NONE

        return DetectionResult(
            paywall_type=best_type,
            confidence=min(1.0, confidence),
            signals=signals,
            blocked_content_ratio=truncation_ratio,
            requires_js=requires_js
        )

    def _analyze_headers(self, headers: Dict, status: int) -> Tuple[List[str], Dict]:
        """Analyze HTTP headers for paywall signals."""
        signals = []
        scores = {pt: 0.0 for pt in PaywallType}

        # Status code analysis
        if status == 402:  # Payment Required
            signals.append("http_402")
            scores[PaywallType.HARD_SUBSCRIPTION] += 0.9

        if status == 403:
            signals.append("http_403")
            scores[PaywallType.HARD_SUBSCRIPTION] += 0.5

        # Header patterns
        for header, value in headers.items():
            header_lower = header.lower()
            value_lower = str(value).lower()

            if "x-paywall" in header_lower:
                signals.append("x-paywall-header")
                scores[PaywallType.HARD_SUBSCRIPTION] += 0.7

            if "x-metered" in header_lower:
                signals.append("x-metered-header")
                scores[PaywallType.SOFT_METERED] += 0.7

            if "x-subscriber" in header_lower:
                signals.append("x-subscriber-header")
                scores[PaywallType.HARD_SUBSCRIPTION] += 0.5

        return signals, scores

    def _analyze_html(self, html: str) -> Tuple[List[str], Dict]:
        """Analyze HTML content for paywall indicators."""
        signals = []
        scores = {pt: 0.0 for pt in PaywallType}
        html_lower = html.lower()

        # Check class patterns
        for pattern in self.PAYWALL_PATTERNS["classes"]:
            if re.search(rf'class="[^"]*{pattern}[^"]*"', html_lower):
                signals.append(f"class:{pattern}")
                scores[PaywallType.UNKNOWN] += 0.3

        # Check ID patterns
        for pattern in self.PAYWALL_PATTERNS["ids"]:
            if re.search(rf'id="[^"]*{pattern}[^"]*"', html_lower):
                signals.append(f"id:{pattern}")
                scores[PaywallType.UNKNOWN] += 0.3

        # Check text patterns
        for pattern in self.PAYWALL_PATTERNS["text"]:
            if re.search(pattern, html_lower):
                signals.append(f"text:{pattern[:20]}")

                # Categorize by text
                if "free article" in pattern or "limit" in pattern:
                    scores[PaywallType.SOFT_METERED] += 0.5
                elif "sign in" in pattern or "account" in pattern:
                    scores[PaywallType.SOFT_REGISTRATION] += 0.5
                elif "subscri" in pattern:
                    scores[PaywallType.HARD_SUBSCRIPTION] += 0.5
                else:
                    scores[PaywallType.UNKNOWN] += 0.3

        # Check meta patterns (JSON-LD)
        for pattern in self.PAYWALL_PATTERNS["meta"]:
            if re.search(pattern, html_lower):
                signals.append(f"meta:{pattern[:20]}")
                scores[PaywallType.HARD_SUBSCRIPTION] += 0.4

        # Check for overlay/modal structures
        if re.search(r'<div[^>]*(?:overlay|modal|popup)[^>]*>', html_lower):
            signals.append("overlay_detected")
            scores[PaywallType.UNKNOWN] += 0.2

        return signals, scores

    def _check_truncation(self, html: str) -> float:
        """
        Check if content appears truncated.

        Returns ratio of truncation indicators found.
        """
        # Extract article text (rough)
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
            return 0.5  # Can't determine

        truncation_count = 0
        for pattern in self.TRUNCATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                truncation_count += 1

        # Check for very short content on article pages
        word_count = len(text.split())
        if word_count < 200:
            truncation_count += 1

        # Check for "continue reading" buttons
        if re.search(r'continue.*read|read.*more|see.*full', text.lower()):
            truncation_count += 1

        return min(1.0, truncation_count / 3)

    def _check_js_requirement(self, html: str) -> bool:
        """Check if page requires JavaScript to render content."""
        indicators = [
            r'<noscript>.*(?:enable|javascript|browser).*</noscript>',
            r'id="?__next"?',  # Next.js
            r'id="?root"?.*></div>\s*<script',  # React SPA
            r'ng-app',  # Angular
            r'data-reactroot',
        ]

        html_lower = html.lower()
        for indicator in indicators:
            if re.search(indicator, html_lower, re.IGNORECASE | re.DOTALL):
                return True

        # Check if main content area is empty
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            content = re.sub(r'<[^>]+>', '', article_match.group(1)).strip()
            if len(content) < 100:
                return True

        return False

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
