#!/usr/bin/env python3
"""
Robust HTTP session with retries, backoff, and connection handling.
Use this in all scrapers for reliable downloads.
"""

import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def create_robust_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: tuple = (10, 30),  # (connect, read)
    pool_connections: int = 5,
    pool_maxsize: int = 5,
) -> requests.Session:
    """
    Create a requests session with automatic retries and backoff.

    Args:
        retries: Number of retries for failed requests
        backoff_factor: Backoff multiplier (1.0 = 1s, 2s, 4s...)
        timeout: (connect_timeout, read_timeout) in seconds
        pool_connections: Number of connection pools
        pool_maxsize: Max connections per pool

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # Retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["HEAD", "GET", "OPTIONS"],  # Only retry safe methods
        raise_on_status=False,  # Don't raise, let us handle
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Default headers
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    })

    return session


def robust_get(
    session: requests.Session,
    url: str,
    timeout: tuple = (10, 30),
    max_retries: int = 3,
    **kwargs
) -> requests.Response:
    """
    GET with manual retry logic for connection errors.

    Args:
        session: requests.Session to use
        url: URL to fetch
        timeout: (connect, read) timeout
        max_retries: Max retry attempts
        **kwargs: Additional arguments for session.get()

    Returns:
        Response object

    Raises:
        requests.RequestException after all retries exhausted
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            return response

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            last_error = e
            wait_time = (2 ** attempt) + (attempt * 0.5)  # Exponential + linear

            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {url[:60]}... (waiting {wait_time:.1f}s)")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} retries: {url[:60]}...")

    raise last_error


def robust_download(
    session: requests.Session,
    url: str,
    local_path: str,
    timeout: tuple = (10, 60),  # Longer read timeout for downloads
    max_retries: int = 3,
    chunk_size: int = 8192,
) -> bool:
    """
    Download a file with retries and streaming.

    Args:
        session: requests.Session to use
        url: URL to download
        local_path: Where to save the file
        timeout: (connect, read) timeout
        max_retries: Max retry attempts
        chunk_size: Download chunk size

    Returns:
        True if successful, False otherwise
    """
    from pathlib import Path

    last_error = None

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout, stream=True)

            if response.status_code == 200:
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                logger.warning(f"HTTP {response.status_code} for {url[:60]}")
                return False

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            last_error = e
            wait_time = (2 ** attempt) + (attempt * 0.5)

            if attempt < max_retries - 1:
                logger.warning(f"Download retry {attempt + 1}/{max_retries} for {url[:60]}...")
                time.sleep(wait_time)
            else:
                logger.error(f"Download failed after {max_retries} retries: {url[:60]}")

    return False
