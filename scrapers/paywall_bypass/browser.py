"""
Stealth Browser - Anti-detection browser automation using Playwright.
"""

import asyncio
import random
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class BrowserResult:
    """Result of a browser operation."""
    success: bool
    content: str
    raw_html: str
    status_code: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    screenshots: List[bytes]
    error: Optional[str] = None


class StealthBrowser:
    """
    Anti-detection browser automation.

    Techniques:
    - WebDriver detection bypass
    - Navigator property masking
    - WebGL fingerprint randomization
    - Canvas fingerprint protection
    - Timezone/language consistency
    - Human-like mouse movements
    - Realistic typing patterns
    - Smart scroll behavior
    """

    # Stealth JavaScript to inject
    STEALTH_SCRIPTS = [
        # Remove webdriver flag
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """,

        # Mock plugins
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name: 'Native Client', filename: 'internal-nacl-plugin'},
            ]
        });
        """,

        # Mock languages
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        """,

        # Mock permissions
        """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """,

        # Mock chrome object
        """
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        """,

        # Canvas fingerprint protection
        """
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
            const imageData = getImageData.call(this, x, y, w, h);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] = imageData.data[i] ^ (Math.random() * 0.01);
            }
            return imageData;
        };
        """,

        # WebGL fingerprint protection
        """
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
        """,
    ]

    # User agent rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Viewport sizes for realism
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1366, "height": 768},
        {"width": 2560, "height": 1440},
    ]

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30000,
        slow_mo: int = 50
    ):
        self.headless = headless
        self.proxy = proxy
        self.timeout = timeout
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None

    async def launch(self):
        """Launch stealth browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        self.playwright = await async_playwright().start()

        # Browser launch options
        launch_options = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certifcate-errors",
                "--ignore-certifcate-errors-spki-list",
            ]
        }

        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self.browser = await self.playwright.chromium.launch(**launch_options)

        # Create context with stealth settings
        viewport = random.choice(self.VIEWPORTS)
        user_agent = random.choice(self.USER_AGENTS)

        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            color_scheme="light",
            device_scale_factor=random.choice([1, 1.25, 1.5, 2]),
            has_touch=False,
            is_mobile=False,
        )

        # Inject stealth scripts before page loads
        await self.context.add_init_script("\n".join(self.STEALTH_SCRIPTS))

        self.page = await self.context.new_page()

        # Set extra headers
        await self.page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })

    async def navigate(
        self,
        url: str,
        wait_for: str = "networkidle",
        wait_timeout: Optional[int] = None
    ) -> BrowserResult:
        """
        Navigate to URL with human-like behavior.
        """
        if not self.page:
            await self.launch()

        timeout = wait_timeout or self.timeout

        try:
            # Add random delay before navigation (human-like)
            await asyncio.sleep(random.uniform(0.5, 2.0))

            # Navigate
            response = await self.page.goto(
                url,
                timeout=timeout,
                wait_until=wait_for
            )

            # Random scroll behavior
            await self._human_scroll()

            # Wait for any dynamic content
            await asyncio.sleep(random.uniform(1.0, 3.0))

            # Get content
            content = await self.page.content()

            # Try to get article text
            article_text = await self._extract_article_text()

            # Get cookies
            cookies = await self.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            return BrowserResult(
                success=True,
                content=article_text or content,
                raw_html=content,
                status_code=response.status if response else 0,
                headers=dict(response.headers) if response else {},
                cookies=cookie_dict,
                screenshots=[]
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                content="",
                raw_html="",
                status_code=0,
                headers={},
                cookies={},
                screenshots=[],
                error=str(e)
            )

    async def _human_scroll(self):
        """Simulate human-like scrolling."""
        if not self.page:
            return

        try:
            # Get page height
            height = await self.page.evaluate("document.body.scrollHeight")

            # Scroll down in chunks
            current = 0
            while current < height * 0.7:  # Scroll 70% of page
                scroll_amount = random.randint(200, 500)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                current += scroll_amount
                await asyncio.sleep(random.uniform(0.1, 0.5))

            # Scroll back up slightly
            await self.page.evaluate(f"window.scrollBy(0, -{random.randint(100, 300)})")

        except Exception:
            pass

    async def _extract_article_text(self) -> Optional[str]:
        """Try to extract article text from page."""
        if not self.page:
            return None

        selectors = [
            "article",
            "[role='article']",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".story-body",
            "#article-body",
            ".article__body",
            "main article",
            ".content-article",
        ]

        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if len(text) > 500:
                        return text
            except Exception:
                continue

        return None

    async def click_element(self, selector: str, timeout: int = 5000):
        """Click element with human-like behavior."""
        if not self.page:
            return False

        try:
            # Wait for element
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            # Get element position
            box = await element.bounding_box()
            if not box:
                return False

            # Move to element with natural curve
            target_x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
            target_y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)

            await self.page.mouse.move(target_x, target_y, steps=random.randint(10, 30))

            # Small delay before click
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Click
            await self.page.mouse.click(target_x, target_y)

            return True

        except Exception:
            return False

    async def type_text(self, selector: str, text: str, timeout: int = 5000):
        """Type text with human-like timing."""
        if not self.page:
            return False

        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            # Click to focus
            await element.click()
            await asyncio.sleep(random.uniform(0.2, 0.5))

            # Type character by character
            for char in text:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            return True

        except Exception:
            return False

    async def clear_cookies(self, url: Optional[str] = None):
        """Clear cookies for domain."""
        if not self.context:
            return

        try:
            if url:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                cookies = await self.context.cookies()
                for cookie in cookies:
                    if domain in cookie.get("domain", ""):
                        await self.context.clear_cookies()
                        break
            else:
                await self.context.clear_cookies()
        except Exception:
            pass

    async def screenshot(self, full_page: bool = False) -> Optional[bytes]:
        """Take screenshot."""
        if not self.page:
            return None

        try:
            return await self.page.screenshot(full_page=full_page)
        except Exception:
            return None

    async def execute_js(self, script: str) -> Any:
        """Execute JavaScript on page."""
        if not self.page:
            return None

        try:
            return await self.page.evaluate(script)
        except Exception:
            return None

    async def wait_for_content(
        self,
        selector: str,
        timeout: int = 10000
    ) -> bool:
        """Wait for specific content to appear."""
        if not self.page:
            return False

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def bypass_cookie_banner(self):
        """Try to dismiss cookie consent banners."""
        if not self.page:
            return

        # Common cookie banner selectors
        selectors = [
            # Accept buttons
            "button[id*='accept']",
            "button[class*='accept']",
            "button[id*='consent']",
            "button[class*='consent']",
            "button[id*='agree']",
            "button[class*='agree']",
            "[data-testid*='accept']",
            "[data-testid*='consent']",
            ".cookie-accept",
            ".cookie-consent-accept",
            "#onetrust-accept-btn-handler",
            ".qc-cmp2-summary-buttons button:first-child",
            # Close buttons
            "button[class*='cookie'] button[class*='close']",
            ".cookie-banner button[class*='close']",
        ]

        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    await element.click()
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue

    async def get_with_googlebot(self, url: str) -> BrowserResult:
        """Navigate as Googlebot."""
        if not self.page:
            await self.launch()

        # Set Googlebot user agent
        await self.context.set_extra_http_headers({
            "User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"
        })

        return await self.navigate(url)

    async def close(self):
        """Clean up resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
