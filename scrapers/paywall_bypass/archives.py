"""
Archive Layer - Integration with web archive services.
"""

import asyncio
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlparse
import aiohttp


@dataclass
class ArchiveResult:
    """Result from archive lookup."""
    success: bool
    content: str
    raw_html: str
    source: str
    archive_url: str
    cached_date: Optional[str] = None
    error: Optional[str] = None


class ArchiveLayer:
    """
    Multi-service archive integration.

    Services:
    - Wayback Machine (archive.org)
    - Archive.today (archive.is/archive.ph)
    - Google Cache
    - Google Web Cache
    - Bing Cache
    - Yahoo Cache
    - Webcitation.org

    Features:
    - Parallel querying
    - Freshness scoring
    - Fallback chains
    - Auto-save for future
    """

    # Archive service configurations
    SERVICES = {
        "wayback": {
            "name": "Wayback Machine",
            "api_url": "https://archive.org/wayback/available?url={url}",
            "direct_url": "https://web.archive.org/web/{timestamp}/{url}",
            "latest_url": "https://web.archive.org/web/{url}",
            "save_url": "https://web.archive.org/save/{url}",
        },
        "archive_today": {
            "name": "Archive.today",
            "search_url": "https://archive.ph/{url}",
            "alt_domains": ["archive.is", "archive.li", "archive.vn", "archive.md"],
        },
        "google_cache": {
            "name": "Google Cache",
            "url": "https://webcache.googleusercontent.com/search?q=cache:{url}",
        },
        "bing_cache": {
            "name": "Bing Cache",
            "url": "https://cc.bingj.com/cache.aspx?q={url}",
        },
    }

    def __init__(self, timeout: int = 30, max_age_days: int = 30):
        self.timeout = timeout
        self.max_age_days = max_age_days
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Create aiohttp session if needed."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def find_archived(
        self,
        url: str,
        services: Optional[List[str]] = None,
        parallel: bool = True
    ) -> Optional[ArchiveResult]:
        """
        Find archived version of URL.

        Args:
            url: URL to find in archives
            services: List of services to try (default: all)
            parallel: Query services in parallel

        Returns:
            ArchiveResult if found, None otherwise
        """
        await self._ensure_session()

        if services is None:
            services = ["wayback", "archive_today", "google_cache"]

        if parallel:
            # Query all services in parallel
            tasks = [
                self._query_service(service, url)
                for service in services
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Return first successful result
            for result in results:
                if isinstance(result, ArchiveResult) and result.success:
                    return result
        else:
            # Query services sequentially
            for service in services:
                result = await self._query_service(service, url)
                if result and result.success:
                    return result

        return None

    async def _query_service(self, service: str, url: str) -> Optional[ArchiveResult]:
        """Query a specific archive service."""
        handlers = {
            "wayback": self._query_wayback,
            "archive_today": self._query_archive_today,
            "google_cache": self._query_google_cache,
            "bing_cache": self._query_bing_cache,
        }

        handler = handlers.get(service)
        if handler:
            try:
                return await handler(url)
            except Exception as e:
                return ArchiveResult(
                    success=False,
                    content="",
                    raw_html="",
                    source=service,
                    archive_url="",
                    error=str(e)
                )
        return None

    async def _query_wayback(self, url: str) -> ArchiveResult:
        """Query Wayback Machine."""
        # First check availability via API
        api_url = self.SERVICES["wayback"]["api_url"].format(url=quote(url, safe=""))

        try:
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("archived_snapshots", {}).get("closest"):
                        snapshot = data["archived_snapshots"]["closest"]
                        archive_url = snapshot["url"]
                        timestamp = snapshot.get("timestamp", "")

                        # Fetch the archived content
                        async with self.session.get(archive_url) as archive_response:
                            if archive_response.status == 200:
                                html = await archive_response.text()

                                # Clean wayback toolbar from content
                                html = self._clean_wayback_html(html)

                                return ArchiveResult(
                                    success=True,
                                    content=self._extract_text(html),
                                    raw_html=html,
                                    source="wayback",
                                    archive_url=archive_url,
                                    cached_date=timestamp
                                )
        except Exception:
            pass

        # Try direct latest URL
        latest_url = self.SERVICES["wayback"]["latest_url"].format(url=url)
        try:
            async with self.session.get(latest_url) as response:
                if response.status == 200:
                    html = await response.text()
                    html = self._clean_wayback_html(html)

                    return ArchiveResult(
                        success=True,
                        content=self._extract_text(html),
                        raw_html=html,
                        source="wayback",
                        archive_url=latest_url
                    )
        except Exception:
            pass

        return ArchiveResult(
            success=False,
            content="",
            raw_html="",
            source="wayback",
            archive_url="",
            error="No archive found"
        )

    async def _query_archive_today(self, url: str) -> ArchiveResult:
        """Query Archive.today and its mirrors."""
        domains = ["archive.ph", "archive.is", "archive.li", "archive.vn", "archive.md"]

        for domain in domains:
            search_url = f"https://{domain}/{url}"

            try:
                async with self.session.get(search_url, allow_redirects=True) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Check if we got actual content or search results
                        if "No results" not in html and len(html) > 5000:
                            return ArchiveResult(
                                success=True,
                                content=self._extract_text(html),
                                raw_html=html,
                                source="archive_today",
                                archive_url=str(response.url)
                            )

                        # Parse search results for archive links
                        archive_link = self._find_archive_link(html, domain)
                        if archive_link:
                            async with self.session.get(archive_link) as archive_response:
                                if archive_response.status == 200:
                                    archive_html = await archive_response.text()
                                    return ArchiveResult(
                                        success=True,
                                        content=self._extract_text(archive_html),
                                        raw_html=archive_html,
                                        source="archive_today",
                                        archive_url=archive_link
                                    )
            except Exception:
                continue

        return ArchiveResult(
            success=False,
            content="",
            raw_html="",
            source="archive_today",
            archive_url="",
            error="No archive found"
        )

    async def _query_google_cache(self, url: str) -> ArchiveResult:
        """Query Google Cache."""
        cache_url = self.SERVICES["google_cache"]["url"].format(url=quote(url, safe=""))

        try:
            # Google cache requires specific headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with self.session.get(cache_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()

                    # Verify it's actual cached content
                    if "This is Google's cache" in html or len(html) > 5000:
                        # Remove Google cache header
                        html = self._clean_google_cache_html(html)

                        return ArchiveResult(
                            success=True,
                            content=self._extract_text(html),
                            raw_html=html,
                            source="google_cache",
                            archive_url=cache_url
                        )
        except Exception:
            pass

        return ArchiveResult(
            success=False,
            content="",
            raw_html="",
            source="google_cache",
            archive_url="",
            error="No cache found"
        )

    async def _query_bing_cache(self, url: str) -> ArchiveResult:
        """Query Bing Cache."""
        cache_url = self.SERVICES["bing_cache"]["url"].format(url=quote(url, safe=""))

        try:
            async with self.session.get(cache_url) as response:
                if response.status == 200:
                    html = await response.text()
                    if len(html) > 5000:
                        return ArchiveResult(
                            success=True,
                            content=self._extract_text(html),
                            raw_html=html,
                            source="bing_cache",
                            archive_url=cache_url
                        )
        except Exception:
            pass

        return ArchiveResult(
            success=False,
            content="",
            raw_html="",
            source="bing_cache",
            archive_url="",
            error="No cache found"
        )

    async def save_to_wayback(self, url: str) -> Optional[str]:
        """
        Save URL to Wayback Machine for future use.

        Returns archive URL if successful.
        """
        await self._ensure_session()

        save_url = self.SERVICES["wayback"]["save_url"].format(url=url)

        try:
            async with self.session.get(save_url, allow_redirects=True) as response:
                if response.status == 200:
                    # Return the archived URL
                    return str(response.url)
        except Exception:
            pass

        return None

    async def save_to_archive_today(self, url: str) -> Optional[str]:
        """
        Save URL to Archive.today.

        Returns archive URL if successful.
        """
        await self._ensure_session()

        try:
            # Archive.today uses POST to submit URLs
            async with self.session.post(
                "https://archive.ph/submit/",
                data={"url": url},
                allow_redirects=True
            ) as response:
                if response.status == 200:
                    return str(response.url)
        except Exception:
            pass

        return None

    def _clean_wayback_html(self, html: str) -> str:
        """Remove Wayback Machine toolbar and scripts."""
        # Remove wayback toolbar
        html = re.sub(
            r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->',
            '',
            html,
            flags=re.DOTALL
        )

        # Remove wayback scripts
        html = re.sub(
            r'<script[^>]*archive\.org[^>]*>.*?</script>',
            '',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Fix wayback URL rewrites
        html = re.sub(
            r'(href|src)="(/web/\d+[a-z]*_?/)?(https?://)',
            r'\1="\3',
            html
        )

        return html

    def _clean_google_cache_html(self, html: str) -> str:
        """Remove Google cache header."""
        # Remove the "This is Google's cache" header div
        html = re.sub(
            r'<div[^>]*style="[^"]*background:#\w+[^"]*"[^>]*>.*?</div>',
            '',
            html,
            count=1,
            flags=re.DOTALL | re.IGNORECASE
        )

        return html

    def _find_archive_link(self, html: str, domain: str) -> Optional[str]:
        """Find first archive link in search results."""
        pattern = rf'href="(https?://{domain}/[^"]+)"'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return None

    def _extract_text(self, html: str) -> str:
        """Extract text content from HTML."""
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    async def get_all_snapshots(
        self,
        url: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get all available Wayback snapshots for a URL.

        Returns list of snapshots with timestamps.
        """
        await self._ensure_session()

        cdx_url = f"https://web.archive.org/cdx/search/cdx?url={quote(url, safe='')}&output=json&limit={limit}"

        try:
            async with self.session.get(cdx_url) as response:
                if response.status == 200:
                    data = await response.json()

                    if len(data) > 1:
                        # First row is headers
                        headers = data[0]
                        snapshots = []

                        for row in data[1:]:
                            snapshot = dict(zip(headers, row))
                            snapshot["url"] = f"https://web.archive.org/web/{snapshot['timestamp']}/{snapshot['original']}"
                            snapshots.append(snapshot)

                        return snapshots
        except Exception:
            pass

        return []

    async def find_oldest_snapshot(self, url: str) -> Optional[ArchiveResult]:
        """Find the oldest available snapshot."""
        snapshots = await self.get_all_snapshots(url, limit=1)

        if snapshots:
            archive_url = snapshots[0]["url"]

            try:
                async with self.session.get(archive_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        html = self._clean_wayback_html(html)

                        return ArchiveResult(
                            success=True,
                            content=self._extract_text(html),
                            raw_html=html,
                            source="wayback",
                            archive_url=archive_url,
                            cached_date=snapshots[0].get("timestamp")
                        )
            except Exception:
                pass

        return None

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None
