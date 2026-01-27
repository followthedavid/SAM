"""
Core Paywall Bypasser - The main orchestration engine.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse
import asyncio

from .detector import PaywallDetector, PaywallType
from .methods import BypassChain, BypassResult
from .browser import StealthBrowser
from .archives import ArchiveLayer
from .extractors import ContentExtractor
from .rules import RuleDatabase


@dataclass
class BypassAttempt:
    """Record of a bypass attempt."""
    url: str
    domain: str
    paywall_type: str
    method_used: str
    success: bool
    content_length: int
    timestamp: str
    latency_ms: int
    error: Optional[str] = None


@dataclass
class ExtractedContent:
    """Successfully extracted content."""
    url: str
    title: str
    author: Optional[str]
    date: Optional[str]
    content: str
    word_count: int
    images: List[str]
    metadata: Dict[str, Any]
    bypass_method: str
    cached: bool


class PaywallBypasser:
    """
    Universal Paywall Bypass System

    Features:
    - Automatic paywall type detection
    - Multi-method bypass chains
    - Stealth browser automation
    - Archive service integration
    - Smart content extraction
    - Self-healing with success tracking
    - Community rule database
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        rules_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        headless: bool = True,
        proxy_list: Optional[List[str]] = None,
        log_level: int = logging.INFO
    ):
        self.config = self._load_config(config_path)
        self.rules = RuleDatabase(rules_path)
        self.cache_dir = cache_dir or "/tmp/paywall_cache"
        self.headless = headless
        self.proxy_list = proxy_list or []

        # Initialize components
        self.detector = PaywallDetector()
        self.archives = ArchiveLayer()
        self.extractor = ContentExtractor()
        self.browser = None  # Lazy init

        # Stats tracking
        self.attempts: List[BypassAttempt] = []
        self.success_rates: Dict[str, Dict[str, float]] = {}

        # Setup logging
        self.logger = logging.getLogger("PaywallBypasser")
        self.logger.setLevel(log_level)

        os.makedirs(self.cache_dir, exist_ok=True)

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration."""
        default_config = {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 2.0,
            "user_agents": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Googlebot/2.1 (+http://www.google.com/bot.html)",
            ],
            "archive_services": ["wayback", "archive_today", "google_cache"],
            "stealth_mode": True,
            "extract_images": True,
            "min_content_length": 500,
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    async def bypass(self, url: str, force_method: Optional[str] = None) -> Optional[ExtractedContent]:
        """
        Main bypass method - attempts to get content from a paywalled URL.

        Args:
            url: The URL to bypass
            force_method: Force a specific method (skip detection)

        Returns:
            ExtractedContent if successful, None otherwise
        """
        start_time = datetime.now()
        domain = urlparse(url).netloc

        self.logger.info(f"Attempting bypass: {url}")

        # Check cache first
        cached = self._check_cache(url)
        if cached:
            self.logger.info("Found in cache")
            return cached

        # Step 1: Check site-specific rules
        site_rule = self.rules.get_rule(domain)
        if site_rule and not force_method:
            self.logger.info(f"Found site rule for {domain}")
            result = await self._apply_site_rule(url, site_rule)
            if result:
                return result

        # Step 2: Detect paywall type
        paywall_type = await self.detector.detect(url)
        self.logger.info(f"Detected paywall type: {paywall_type.value}")

        # Step 3: Build bypass chain based on paywall type
        chain = self._build_bypass_chain(paywall_type, force_method)

        # Step 4: Execute bypass chain
        for method in chain.methods:
            self.logger.info(f"Trying method: {method.name}")

            try:
                result = await method.execute(url, self)

                if result.success and result.content:
                    # Validate content
                    if len(result.content) >= self.config["min_content_length"]:
                        # Extract structured content
                        extracted = await self.extractor.extract(
                            url, result.content, result.raw_html
                        )

                        if extracted:
                            # Record success
                            self._record_attempt(
                                url, domain, paywall_type.value,
                                method.name, True, len(extracted.content),
                                start_time
                            )

                            # Cache result
                            self._cache_result(url, extracted)

                            return extracted

                    self.logger.warning(f"Content too short from {method.name}")

            except Exception as e:
                self.logger.warning(f"Method {method.name} failed: {e}")
                continue

        # All methods failed
        self._record_attempt(
            url, domain, paywall_type.value,
            "all_failed", False, 0, start_time,
            error="All bypass methods exhausted"
        )

        return None

    def bypass_sync(self, url: str, force_method: Optional[str] = None) -> Optional[ExtractedContent]:
        """Synchronous wrapper for bypass()."""
        return asyncio.run(self.bypass(url, force_method))

    async def bypass_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, Optional[ExtractedContent]]:
        """Bypass multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_bypass(url: str):
            async with semaphore:
                return url, await self.bypass(url)

        tasks = [bounded_bypass(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            url: (content if not isinstance(content, Exception) else None)
            for url, content in results
        }

    def _build_bypass_chain(
        self,
        paywall_type: PaywallType,
        force_method: Optional[str] = None
    ) -> BypassChain:
        """Build optimal bypass chain based on paywall type."""
        from .methods import (
            ArchiveMethod, GoogleCacheMethod, GoogleBotMethod,
            AmpMethod, ReaderModeMethod, CookieClearMethod,
            StealthBrowserMethod, JsonLdMethod, PrintVersionMethod,
            MobileVersionMethod, TextOnlyMethod, WaybackMachineMethod
        )

        if force_method:
            # Single method forced
            method_map = {
                "archive": ArchiveMethod(),
                "wayback": WaybackMachineMethod(),
                "google_cache": GoogleCacheMethod(),
                "googlebot": GoogleBotMethod(),
                "amp": AmpMethod(),
                "reader": ReaderModeMethod(),
                "cookies": CookieClearMethod(),
                "stealth": StealthBrowserMethod(),
                "jsonld": JsonLdMethod(),
                "print": PrintVersionMethod(),
                "mobile": MobileVersionMethod(),
                "text": TextOnlyMethod(),
            }
            if force_method in method_map:
                return BypassChain([method_map[force_method]])

        # Build chain based on paywall type
        chains = {
            PaywallType.NONE: BypassChain([
                JsonLdMethod(),
                ReaderModeMethod(),
            ]),

            PaywallType.SOFT_METERED: BypassChain([
                CookieClearMethod(),
                ArchiveMethod(),
                GoogleCacheMethod(),
                ReaderModeMethod(),
                StealthBrowserMethod(),
            ]),

            PaywallType.SOFT_REGISTRATION: BypassChain([
                ArchiveMethod(),
                GoogleBotMethod(),
                GoogleCacheMethod(),
                AmpMethod(),
                StealthBrowserMethod(),
            ]),

            PaywallType.HARD_SUBSCRIPTION: BypassChain([
                ArchiveMethod(),
                WaybackMachineMethod(),
                GoogleCacheMethod(),
                GoogleBotMethod(),
                PrintVersionMethod(),
                # Hard paywalls - archives are often only hope
            ]),

            PaywallType.DYNAMIC_JS: BypassChain([
                StealthBrowserMethod(),
                ArchiveMethod(),
                JsonLdMethod(),
                AmpMethod(),
            ]),

            PaywallType.GEOGRAPHIC: BypassChain([
                ArchiveMethod(),
                GoogleCacheMethod(),
                StealthBrowserMethod(),  # With proxy
            ]),

            PaywallType.UNKNOWN: BypassChain([
                ArchiveMethod(),
                GoogleCacheMethod(),
                GoogleBotMethod(),
                CookieClearMethod(),
                AmpMethod(),
                ReaderModeMethod(),
                StealthBrowserMethod(),
                JsonLdMethod(),
            ]),
        }

        return chains.get(paywall_type, chains[PaywallType.UNKNOWN])

    async def _apply_site_rule(self, url: str, rule: Dict) -> Optional[ExtractedContent]:
        """Apply a site-specific bypass rule."""
        method_name = rule.get("method")
        if not method_name:
            return None

        # Get method parameters
        params = rule.get("params", {})

        # Execute site-specific method
        chain = self._build_bypass_chain(PaywallType.UNKNOWN, method_name)

        for method in chain.methods:
            try:
                result = await method.execute(url, self, **params)
                if result.success and result.content:
                    extracted = await self.extractor.extract(url, result.content, result.raw_html)
                    if extracted:
                        return extracted
            except Exception as e:
                self.logger.warning(f"Site rule failed: {e}")

        return None

    def _check_cache(self, url: str) -> Optional[ExtractedContent]:
        """Check if URL is in cache."""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    data = json.load(f)
                    data["cached"] = True
                    return ExtractedContent(**data)
            except Exception:
                pass

        return None

    def _cache_result(self, url: str, content: ExtractedContent):
        """Cache successful result."""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        try:
            with open(cache_path, "w") as f:
                json.dump(asdict(content), f)
        except Exception as e:
            self.logger.warning(f"Failed to cache: {e}")

    def _record_attempt(
        self,
        url: str,
        domain: str,
        paywall_type: str,
        method: str,
        success: bool,
        content_length: int,
        start_time: datetime,
        error: Optional[str] = None
    ):
        """Record bypass attempt for analytics."""
        latency = int((datetime.now() - start_time).total_seconds() * 1000)

        attempt = BypassAttempt(
            url=url,
            domain=domain,
            paywall_type=paywall_type,
            method_used=method,
            success=success,
            content_length=content_length,
            timestamp=datetime.now().isoformat(),
            latency_ms=latency,
            error=error
        )

        self.attempts.append(attempt)

        # Update success rates
        if domain not in self.success_rates:
            self.success_rates[domain] = {}

        if method not in self.success_rates[domain]:
            self.success_rates[domain][method] = {"success": 0, "total": 0}

        self.success_rates[domain][method]["total"] += 1
        if success:
            self.success_rates[domain][method]["success"] += 1

    def get_stats(self) -> Dict:
        """Get bypass statistics."""
        total = len(self.attempts)
        successful = sum(1 for a in self.attempts if a.success)

        by_method = {}
        for attempt in self.attempts:
            method = attempt.method_used
            if method not in by_method:
                by_method[method] = {"success": 0, "total": 0}
            by_method[method]["total"] += 1
            if attempt.success:
                by_method[method]["success"] += 1

        return {
            "total_attempts": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "by_method": by_method,
            "by_domain": self.success_rates,
        }

    async def close(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
