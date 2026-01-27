#!/usr/bin/env python3
"""
Smart Paywall Bypass - Exploits client-side vs server-side paywall differences.

Key insight: Client-side paywalls send full content to browser, then hide it with JS.
If we disable JS or extract content before overlay loads, we get the full article.

Server-side paywalls never send the content - only archives can help there.
"""

import asyncio
import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from playwright.async_api import async_playwright


@dataclass
class BypassResult:
    success: bool
    content: str
    title: str
    method: str
    paywall_type: str  # "client-side", "server-side", "none"
    word_count: int
    error: Optional[str] = None


class SmartPaywallBypass:
    """
    Intelligent paywall bypass that detects and exploits client-side paywalls.

    Strategy:
    1. First fetch with JS disabled - if content is there, it's client-side (EASY)
    2. Compare with JS enabled fetch - detect what's hidden
    3. For client-side: extract from no-JS version
    4. For server-side: try archives as fallback
    """

    # Known paywall script domains to block
    PAYWALL_SCRIPTS = [
        "*://cdn.tinypass.com/*",
        "*://cdn.piano.io/*",
        "*://js.pelcro.com/*",
        "*://cdn.cxense.com/*",
        "*://meter.bostonglobe.com/*",
        "*://js.matheranalytics.com/*",
        "*://content-meter.nytimes.com/*",
        "*://*.zephr.com/*",
        "*://cdn.blueconic.net/*",
        "*://www.google-analytics.com/*",
        "*://static.chartbeat.com/*",
    ]

    # Overlay/modal selectors to remove
    PAYWALL_SELECTORS = [
        "[class*='paywall']",
        "[class*='subscription']",
        "[class*='meter']",
        "[id*='paywall']",
        "[id*='gateway']",
        ".modal-backdrop",
        ".overlay",
        "[class*='piano']",
        "[class*='regwall']",
        "[data-testid*='paywall']",
        "[aria-label*='subscription']",
    ]

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def _init_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

    async def bypass(self, url: str) -> BypassResult:
        """
        Main bypass method - tries multiple strategies.
        """
        await self._init_browser()

        # Strategy 1: Fetch with JS disabled (catches client-side paywalls)
        print(f"[1] Trying JS-disabled fetch...")
        no_js_result = await self._fetch_no_js(url)

        # Strategy 2: Fetch with JS but block paywall scripts
        print(f"[2] Trying script-blocked fetch...")
        blocked_result = await self._fetch_block_scripts(url)

        # Strategy 3: Fetch normally and remove overlays
        print(f"[3] Trying overlay removal...")
        overlay_result = await self._fetch_remove_overlay(url)

        # Compare results - pick the one with most content
        results = [
            (no_js_result, "js_disabled"),
            (blocked_result, "scripts_blocked"),
            (overlay_result, "overlay_removed"),
        ]

        best_result = None
        best_words = 0
        best_method = ""

        for result, method in results:
            if result and result[0]:  # (content, title)
                words = len(result[0].split())
                print(f"    {method}: {words} words")
                if words > best_words:
                    best_words = words
                    best_result = result
                    best_method = method

        if best_result and best_words > 200:
            content, title = best_result

            # Determine paywall type
            paywall_type = self._determine_paywall_type(
                no_js_result, blocked_result, overlay_result
            )

            return BypassResult(
                success=True,
                content=content,
                title=title,
                method=best_method,
                paywall_type=paywall_type,
                word_count=best_words
            )

        # All strategies failed - likely server-side paywall
        return BypassResult(
            success=False,
            content="",
            title="",
            method="none",
            paywall_type="server-side",
            word_count=0,
            error="Server-side paywall detected - content not sent to browser"
        )

    async def _fetch_no_js(self, url: str) -> Optional[Tuple[str, str]]:
        """Fetch page with JavaScript completely disabled."""
        try:
            context = await self.browser.new_context(
                java_script_enabled=False,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            await page.goto(url, timeout=30000, wait_until='domcontentloaded')

            # Extract content
            content, title = await self._extract_article(page)

            await context.close()
            return (content, title) if content else None

        except Exception as e:
            print(f"    JS-disabled error: {e}")
            return None

    async def _fetch_block_scripts(self, url: str) -> Optional[Tuple[str, str]]:
        """Fetch page but block known paywall scripts."""
        try:
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )

            # Block paywall scripts
            await context.route("**/*", lambda route: self._route_handler(route))

            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until='networkidle')

            content, title = await self._extract_article(page)

            await context.close()
            return (content, title) if content else None

        except Exception as e:
            print(f"    Script-blocked error: {e}")
            return None

    async def _route_handler(self, route):
        """Block requests to paywall script domains."""
        url = route.request.url

        # Block known paywall domains
        blocked_domains = [
            'tinypass.com', 'piano.io', 'pelcro.com', 'cxense.com',
            'matheranalytics.com', 'zephr.com', 'blueconic.net',
            'content-meter', 'meter.', 'paywall'
        ]

        if any(domain in url for domain in blocked_domains):
            await route.abort()
        else:
            await route.continue_()

    async def _fetch_remove_overlay(self, url: str) -> Optional[Tuple[str, str]]:
        """Fetch page normally, then remove paywall overlays via DOM manipulation."""
        try:
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            await page.goto(url, timeout=30000, wait_until='domcontentloaded')

            # Remove paywall overlays
            for selector in self.PAYWALL_SELECTORS:
                try:
                    await page.evaluate(f'''
                        document.querySelectorAll('{selector}').forEach(el => el.remove());
                    ''')
                except:
                    pass

            # Remove overflow:hidden from body (common paywall trick)
            await page.evaluate('''
                document.body.style.overflow = 'auto';
                document.documentElement.style.overflow = 'auto';
            ''')

            # Wait a bit for any remaining JS
            await asyncio.sleep(1)

            content, title = await self._extract_article(page)

            await context.close()
            return (content, title) if content else None

        except Exception as e:
            print(f"    Overlay removal error: {e}")
            return None

    async def _extract_article(self, page) -> Tuple[str, str]:
        """Extract article content from page."""
        # Try common article selectors
        selectors = [
            'article',
            '[role="article"]',
            '.article-body',
            '.article-content',
            '.story-body',
            '.post-content',
            '.entry-content',
            'main article',
            '#article-body',
            '.article__body',
        ]

        content = ""
        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    if len(text) > len(content):
                        content = text
            except:
                continue

        # Fallback to main or body
        if len(content) < 200:
            try:
                main = await page.query_selector('main')
                if main:
                    content = await main.inner_text()
            except:
                pass

        # Get title
        title = ""
        try:
            title_el = await page.query_selector('h1')
            if title_el:
                title = await title_el.inner_text()
        except:
            pass

        if not title:
            title = await page.title()

        # Clean content
        content = self._clean_text(content)

        return content, title

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove common noise
        noise_patterns = [
            r'Advertisement\s*',
            r'ADVERTISEMENT\s*',
            r'Subscribe to.*?\n',
            r'Sign up for.*?\n',
            r'Already a subscriber\?.*?\n',
            r'Read more:.*?\n',
            r'Share this article.*?\n',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _determine_paywall_type(self, no_js, blocked, overlay) -> str:
        """Determine the type of paywall based on results."""
        no_js_words = len(no_js[0].split()) if no_js and no_js[0] else 0
        blocked_words = len(blocked[0].split()) if blocked and blocked[0] else 0
        overlay_words = len(overlay[0].split()) if overlay and overlay[0] else 0

        # If JS-disabled got content, it's client-side
        if no_js_words > 300:
            return "client-side (JS overlay)"

        # If blocking scripts helped, it's client-side
        if blocked_words > overlay_words + 100:
            return "client-side (script-based)"

        # If overlay removal helped, it's client-side
        if overlay_words > 300:
            return "client-side (DOM overlay)"

        return "server-side"

    async def close(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def test_sites():
    """Test the smart bypass on various sites."""
    bypasser = SmartPaywallBypass()

    test_urls = [
        ("https://www.nytimes.com/", "NYT Homepage"),
        ("https://www.wsj.com/", "WSJ Homepage"),
        ("https://wwd.com/fashion-news/", "WWD Fashion"),
        ("https://www.theatlantic.com/", "The Atlantic"),
    ]

    for url, name in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"URL: {url}")
        print(f"{'='*60}")

        result = await bypasser.bypass(url)

        print(f"\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Paywall Type: {result.paywall_type}")
        print(f"  Method: {result.method}")
        print(f"  Word Count: {result.word_count}")
        if result.success:
            print(f"  Title: {result.title}")
            print(f"  Content Preview: {result.content[:300]}...")
        else:
            print(f"  Error: {result.error}")

    await bypasser.close()


if __name__ == "__main__":
    asyncio.run(test_sites())
