#!/usr/bin/env python3
"""
Test the paywall bypass system on specific sites.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/davidquinton/ReverseLab/SAM/scrapers')

from paywall_bypass import PaywallBypasser, PaywallDetector
from paywall_bypass.detector import PaywallType

async def test_detection(url: str):
    """Test paywall detection on a URL."""
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print(f"{'='*60}")

    detector = PaywallDetector()

    try:
        result = await detector.analyze(url)
        print(f"Paywall Type: {result.paywall_type.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Requires JS: {result.requires_js}")
        print(f"Blocked Content Ratio: {result.blocked_content_ratio:.2f}")
        print(f"Signals: {', '.join(result.signals[:5])}")

        await detector.close()
        return result
    except Exception as e:
        print(f"Error: {e}")
        await detector.close()
        return None

async def test_bypass(url: str):
    """Test full bypass on a URL."""
    print(f"\n{'='*60}")
    print(f"Bypassing: {url}")
    print(f"{'='*60}")

    bypasser = PaywallBypasser(headless=True)

    try:
        content = await bypasser.bypass(url)

        if content:
            print(f"SUCCESS!")
            print(f"Title: {content.title}")
            print(f"Author: {content.author}")
            print(f"Word Count: {content.word_count}")
            print(f"Method Used: {content.bypass_method}")
            print(f"\nFirst 500 chars of content:")
            print(content.content[:500])
            print("...")
        else:
            print("FAILED - No content extracted")

        await bypasser.close()
        return content
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await bypasser.close()
        return None

async def test_archives(url: str):
    """Test archive lookup for a URL."""
    from paywall_bypass.archives import ArchiveLayer

    print(f"\n{'='*60}")
    print(f"Archive Search: {url}")
    print(f"{'='*60}")

    archives = ArchiveLayer()

    try:
        result = await archives.find_archived(url)

        if result and result.success:
            print(f"FOUND in: {result.source}")
            print(f"Archive URL: {result.archive_url}")
            print(f"Content length: {len(result.content)} chars")
            if result.cached_date:
                print(f"Cached date: {result.cached_date}")
            print(f"\nFirst 500 chars:")
            print(result.content[:500])
        else:
            print("Not found in archives")

        await archives.close()
        return result
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await archives.close()
        return None

async def main():
    # Test with specific article URLs
    test_urls = [
        # WWD articles
        "https://wwd.com/fashion-news/fashion-scoops/tommy-hilfiger-fall-2024-campaign-1236543210/",
        "https://wwd.com/business-news/business-features/lvmh-luxury-market-analysis-1236500000/",
        # Vogue archive
        "https://archive.vogue.com/article/1990/1/vogue-point-of-view",
    ]

    print("="*60)
    print("PAYWALL BYPASS SYSTEM TEST")
    print("="*60)

    # Test detection on each
    for url in test_urls[:2]:
        await test_detection(url)

    # Test archive lookup
    print("\n\n" + "="*60)
    print("TESTING ARCHIVE SERVICES")
    print("="*60)

    for url in test_urls:
        await test_archives(url)

if __name__ == "__main__":
    asyncio.run(main())
