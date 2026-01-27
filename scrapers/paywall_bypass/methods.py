"""
Bypass Methods - All the techniques for getting past paywalls.
"""

import asyncio
import aiohttp
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from urllib.parse import urlparse, urljoin, quote

if TYPE_CHECKING:
    from .core import PaywallBypasser


@dataclass
class BypassResult:
    """Result of a bypass attempt."""
    success: bool
    content: Optional[str]
    raw_html: Optional[str]
    method: str
    cached: bool = False
    error: Optional[str] = None


class BypassMethod(ABC):
    """Base class for bypass methods."""

    name: str = "base"
    description: str = "Base bypass method"

    @abstractmethod
    async def execute(
        self,
        url: str,
        bypasser: "PaywallBypasser",
        **kwargs
    ) -> BypassResult:
        """Execute the bypass method."""
        pass


class BypassChain:
    """A chain of bypass methods to try in order."""

    def __init__(self, methods: List[BypassMethod]):
        self.methods = methods

    def __iter__(self):
        return iter(self.methods)


# =============================================================================
# ARCHIVE METHODS
# =============================================================================

class ArchiveMethod(BypassMethod):
    """Try archive.today first - often has full articles."""

    name = "archive_today"
    description = "Check archive.today for cached version"

    ARCHIVE_DOMAINS = [
        "archive.today",
        "archive.ph",
        "archive.is",
        "archive.li",
        "archive.vn",
        "archive.fo",
        "archive.md",
    ]

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        async with aiohttp.ClientSession() as session:
            for domain in self.ARCHIVE_DOMAINS:
                try:
                    archive_url = f"https://{domain}/{url}"

                    async with session.get(
                        archive_url,
                        timeout=15,
                        allow_redirects=True,
                        headers={"User-Agent": bypasser.config["user_agents"][0]}
                    ) as response:
                        if response.status == 200:
                            html = await response.text()

                            # Check if we got actual content (not search page)
                            if len(html) > 5000 and "No results" not in html:
                                return BypassResult(
                                    success=True,
                                    content=html,
                                    raw_html=html,
                                    method=self.name,
                                    cached=True
                                )

                except Exception:
                    continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class WaybackMachineMethod(BypassMethod):
    """Check Internet Archive Wayback Machine."""

    name = "wayback_machine"
    description = "Check Wayback Machine for archived version"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        async with aiohttp.ClientSession() as session:
            try:
                # Check availability
                api_url = f"https://archive.org/wayback/available?url={quote(url)}"

                async with session.get(api_url, timeout=10) as response:
                    if response.status != 200:
                        return BypassResult(success=False, content=None, raw_html=None, method=self.name)

                    data = await response.json()
                    snapshots = data.get("archived_snapshots", {})
                    closest = snapshots.get("closest", {})

                    if not closest.get("available"):
                        return BypassResult(success=False, content=None, raw_html=None, method=self.name)

                    archive_url = closest["url"]

                # Fetch archived version
                async with session.get(
                    archive_url,
                    timeout=20,
                    headers={"User-Agent": bypasser.config["user_agents"][0]}
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Remove Wayback Machine toolbar
                        html = re.sub(
                            r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->',
                            '',
                            html,
                            flags=re.DOTALL
                        )

                        return BypassResult(
                            success=True,
                            content=html,
                            raw_html=html,
                            method=self.name,
                            cached=True
                        )

            except Exception as e:
                return BypassResult(
                    success=False,
                    content=None,
                    raw_html=None,
                    method=self.name,
                    error=str(e)
                )

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class GoogleCacheMethod(BypassMethod):
    """Try Google's cached version."""

    name = "google_cache"
    description = "Check Google Cache for cached version"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{quote(url)}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    cache_url,
                    timeout=15,
                    headers={
                        "User-Agent": bypasser.config["user_agents"][0],
                        "Accept": "text/html",
                    }
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Check it's not an error page
                        if "not available" not in html.lower() and len(html) > 2000:
                            return BypassResult(
                                success=True,
                                content=html,
                                raw_html=html,
                                method=self.name,
                                cached=True
                            )

            except Exception:
                pass

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


# =============================================================================
# USER AGENT METHODS
# =============================================================================

class GoogleBotMethod(BypassMethod):
    """Fetch with Googlebot user agent - many sites serve full content to bots."""

    name = "googlebot"
    description = "Fetch with Googlebot user agent"

    GOOGLEBOT_UAS = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
    ]

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        async with aiohttp.ClientSession() as session:
            for ua in self.GOOGLEBOT_UAS:
                try:
                    async with session.get(
                        url,
                        timeout=15,
                        headers={
                            "User-Agent": ua,
                            "Accept": "text/html,application/xhtml+xml",
                            "Accept-Language": "en-US,en;q=0.9",
                            "From": "googlebot(at)googlebot.com",
                        }
                    ) as response:
                        if response.status == 200:
                            html = await response.text()

                            # Check we got substantial content
                            if len(html) > 5000:
                                return BypassResult(
                                    success=True,
                                    content=html,
                                    raw_html=html,
                                    method=self.name
                                )

                except Exception:
                    continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


# =============================================================================
# ALTERNATE VERSION METHODS
# =============================================================================

class AmpMethod(BypassMethod):
    """Try AMP (Accelerated Mobile Pages) version - often no paywall."""

    name = "amp"
    description = "Try AMP version of article"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        parsed = urlparse(url)
        domain = parsed.netloc

        # Common AMP URL patterns
        amp_urls = [
            url.replace(domain, f"amp.{domain}"),
            f"{url}/amp",
            f"{url}?amp=1",
            f"{url}?outputType=amp",
            url.replace("/article/", "/amp/article/"),
            f"https://www.google.com/amp/s/{domain}{parsed.path}",
        ]

        async with aiohttp.ClientSession() as session:
            for amp_url in amp_urls:
                try:
                    async with session.get(
                        amp_url,
                        timeout=10,
                        headers={"User-Agent": bypasser.config["user_agents"][0]}
                    ) as response:
                        if response.status == 200:
                            html = await response.text()

                            # Verify it's an AMP page with content
                            if "amp" in html.lower() and len(html) > 3000:
                                return BypassResult(
                                    success=True,
                                    content=html,
                                    raw_html=html,
                                    method=self.name
                                )

                except Exception:
                    continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class PrintVersionMethod(BypassMethod):
    """Try print-friendly version - often bypasses paywall."""

    name = "print"
    description = "Try print-friendly version"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        # Common print URL patterns
        print_urls = [
            f"{url}?print=true",
            f"{url}&print=true",
            f"{url}/print",
            f"{url}?view=print",
            f"{url}?format=print",
            url.replace("/article/", "/print/article/"),
        ]

        async with aiohttp.ClientSession() as session:
            for print_url in print_urls:
                try:
                    async with session.get(
                        print_url,
                        timeout=10,
                        headers={"User-Agent": bypasser.config["user_agents"][0]}
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            if len(html) > 3000:
                                return BypassResult(
                                    success=True,
                                    content=html,
                                    raw_html=html,
                                    method=self.name
                                )

                except Exception:
                    continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class MobileVersionMethod(BypassMethod):
    """Try mobile version - sometimes has different paywall behavior."""

    name = "mobile"
    description = "Try mobile version of site"

    MOBILE_UAS = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ]

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        parsed = urlparse(url)

        # Try mobile subdomain and mobile UA
        mobile_urls = [
            url.replace(parsed.netloc, f"m.{parsed.netloc}"),
            url.replace(parsed.netloc, f"mobile.{parsed.netloc}"),
            url,  # Same URL with mobile UA
        ]

        async with aiohttp.ClientSession() as session:
            for mobile_url in mobile_urls:
                for ua in self.MOBILE_UAS:
                    try:
                        async with session.get(
                            mobile_url,
                            timeout=10,
                            headers={"User-Agent": ua}
                        ) as response:
                            if response.status == 200:
                                html = await response.text()
                                if len(html) > 3000:
                                    return BypassResult(
                                        success=True,
                                        content=html,
                                        raw_html=html,
                                        method=self.name
                                    )

                    except Exception:
                        continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class TextOnlyMethod(BypassMethod):
    """Try text-only version - some sites offer this."""

    name = "text_only"
    description = "Try text-only version"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        text_urls = [
            f"{url}?text=1",
            f"{url}?lite=true",
            f"{url}?nojs=1",
            url.replace("www.", "text."),
            url.replace("www.", "lite."),
        ]

        async with aiohttp.ClientSession() as session:
            for text_url in text_urls:
                try:
                    async with session.get(
                        text_url,
                        timeout=10,
                        headers={"User-Agent": bypasser.config["user_agents"][0]}
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            if len(html) > 2000:
                                return BypassResult(
                                    success=True,
                                    content=html,
                                    raw_html=html,
                                    method=self.name
                                )

                except Exception:
                    continue

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


# =============================================================================
# COOKIE/SESSION METHODS
# =============================================================================

class CookieClearMethod(BypassMethod):
    """Clear cookies to reset metered paywalls."""

    name = "cookie_clear"
    description = "Fetch without cookies (incognito mode)"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        # Fresh session with no cookies
        connector = aiohttp.TCPConnector(force_close=True)
        jar = aiohttp.DummyCookieJar()  # Ignore all cookies

        async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:
            try:
                async with session.get(
                    url,
                    timeout=15,
                    headers={
                        "User-Agent": bypasser.config["user_agents"][0],
                        "Accept": "text/html,application/xhtml+xml",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                    }
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        if len(html) > 3000:
                            return BypassResult(
                                success=True,
                                content=html,
                                raw_html=html,
                                method=self.name
                            )

            except Exception:
                pass

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


class ReaderModeMethod(BypassMethod):
    """Extract article content directly (like browser reader mode)."""

    name = "reader_mode"
    description = "Extract article using reader mode parsing"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": bypasser.config["user_agents"][0]}
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Try to extract article content directly
                        # This mimics what browser reader mode does
                        content = await bypasser.extractor.extract_article_text(html)

                        if content and len(content) > 500:
                            return BypassResult(
                                success=True,
                                content=content,
                                raw_html=html,
                                method=self.name
                            )

            except Exception:
                pass

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)


# =============================================================================
# DATA EXTRACTION METHODS
# =============================================================================

class JsonLdMethod(BypassMethod):
    """Extract article from JSON-LD structured data - often contains full text."""

    name = "jsonld"
    description = "Extract from JSON-LD structured data"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        import json

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": bypasser.config["user_agents"][0]}
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Find JSON-LD scripts
                        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
                        matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

                        for match in matches:
                            try:
                                data = json.loads(match)

                                # Handle array of objects
                                if isinstance(data, list):
                                    for item in data:
                                        content = self._extract_from_jsonld(item)
                                        if content:
                                            return BypassResult(
                                                success=True,
                                                content=content,
                                                raw_html=html,
                                                method=self.name
                                            )
                                else:
                                    content = self._extract_from_jsonld(data)
                                    if content:
                                        return BypassResult(
                                            success=True,
                                            content=content,
                                            raw_html=html,
                                            method=self.name
                                        )

                            except json.JSONDecodeError:
                                continue

            except Exception:
                pass

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)

    def _extract_from_jsonld(self, data: Dict) -> Optional[str]:
        """Extract article body from JSON-LD object."""
        if not isinstance(data, dict):
            return None

        # Check for article types
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""

        article_types = ["Article", "NewsArticle", "BlogPosting", "WebPage", "Report"]

        if schema_type in article_types or any(t in str(schema_type) for t in article_types):
            # Try various content fields
            content_fields = ["articleBody", "text", "description", "content"]

            for field in content_fields:
                if field in data and data[field]:
                    content = data[field]
                    if isinstance(content, str) and len(content) > 500:
                        return content

        # Check for nested mainEntity
        if "mainEntity" in data:
            return self._extract_from_jsonld(data["mainEntity"])

        return None


# =============================================================================
# BROWSER AUTOMATION METHODS
# =============================================================================

class StealthBrowserMethod(BypassMethod):
    """Use stealth browser with anti-detection for JS-heavy sites."""

    name = "stealth_browser"
    description = "Use stealth browser automation"

    async def execute(self, url: str, bypasser: "PaywallBypasser", **kwargs) -> BypassResult:
        try:
            # Lazy import playwright
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Launch with stealth settings
                browser = await p.chromium.launch(
                    headless=bypasser.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                )

                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=bypasser.config["user_agents"][0],
                    java_script_enabled=True,
                    ignore_https_errors=True,
                    # Block images/fonts for speed
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                )

                # Add stealth scripts
                await context.add_init_script("""
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Mock plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                """)

                page = await context.new_page()

                # Navigate and wait for content
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait a bit for dynamic content
                await asyncio.sleep(2)

                # Try to dismiss cookie banners / paywalls
                dismiss_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("I agree")',
                    'button:has-text("Continue")',
                    '[class*="close"]',
                    '[class*="dismiss"]',
                ]

                for selector in dismiss_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.is_visible():
                            await button.click()
                            await asyncio.sleep(0.5)
                    except Exception:
                        continue

                # Scroll to load lazy content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                # Get content
                html = await page.content()

                await browser.close()

                if len(html) > 3000:
                    return BypassResult(
                        success=True,
                        content=html,
                        raw_html=html,
                        method=self.name
                    )

        except ImportError:
            return BypassResult(
                success=False,
                content=None,
                raw_html=None,
                method=self.name,
                error="Playwright not installed"
            )
        except Exception as e:
            return BypassResult(
                success=False,
                content=None,
                raw_html=None,
                method=self.name,
                error=str(e)
            )

        return BypassResult(success=False, content=None, raw_html=None, method=self.name)
