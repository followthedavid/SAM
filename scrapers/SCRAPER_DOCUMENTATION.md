# SAM Scraper System Documentation

## Overview

A collection of site rippers and paywall bypass tools for archiving content from various sources.

**Location:** `/Users/davidquinton/ReverseLab/SAM/scrapers/`

---

## Active Scrapers

### 1. Nifty.org Ripper (`nifty_ripper.py`)

**Target:** Gay male erotic stories from nifty.org (1992-present)

**Storage:** `/Volumes/David External/nifty_archive/`

**Status:** ✅ Working - downloading

| Metric | Value |
|--------|-------|
| Total indexed | 64,536 stories |
| Valid/downloadable | ~38,000 |
| Average story | ~3,000 words |
| Estimated size | ~1.5 GB text |

**Commands:**
```bash
cd /Users/davidquinton/ReverseLab/SAM/scrapers
source .venv/bin/activate

# Index all categories
python3 nifty_ripper.py index

# Download stories
python3 nifty_ripper.py download --limit 999999

# Export training data
python3 nifty_ripper.py export --output /path/to/output.json

# Check stats
python3 nifty_ripper.py stats
```

**Output Format:** JSON with metadata (title, author, category, word count, content)

---

### 2. AO3 Ripper (`ao3_ripper.py`)

**Target:** Archive of Our Own - M/M explicit works with high kudos

**Storage:** `/Volumes/David External/ao3_archive/`

**Status:** ✅ Working - downloading

| Metric | Value |
|--------|-------|
| Filter | M/M, Explicit, kudos≥100, words≥2000 |
| Indexed | ~3,300+ works |
| Average work | ~40,000 words |
| Estimated size | ~2-5 GB text |

**Commands:**
```bash
# Index works
python3 ao3_ripper.py index --limit 10000

# Download works
python3 ao3_ripper.py download --limit 999999

# Export training data
python3 ao3_ripper.py export

# Check stats
python3 ao3_ripper.py stats
```

**Note:** AO3 has rate limiting. Scraper includes respectful delays.

---

### 3. WWD Ripper (`wwd_ripper.py`)

**Target:** Women's Wear Daily - fashion industry news (1967-present)

**Storage:** `/Volumes/#1/wwd_archive/`

**Status:** ✅ Working - indexing phase

| Metric | Value |
|--------|-------|
| Sitemaps | 326 monthly archives |
| Total articles | ~293,000 estimated |
| Includes | Text, images, galleries, video URLs |
| Estimated size | ~600 GB with media |

**Paywall:** Client-side (Piano) - **BYPASSED** via JS-disabled fetch

**Commands:**
```bash
# Index all sitemaps
python3 wwd_ripper.py index

# Download articles with media
python3 wwd_ripper.py download --limit 999999

# Export training data
python3 wwd_ripper.py export

# Check stats
python3 wwd_ripper.py stats
```

**Directory Structure:**
```
/Volumes/#1/wwd_archive/
└── articles/
    └── {category}/
        └── {subcategory}/
            └── {year}/
                └── {month}/
                    └── {article_id}/
                        ├── article.json
                        ├── featured_*.jpg
                        ├── images/
                        └── gallery/
```

---

## Paywall Bypass System

**Location:** `/Users/davidquinton/ReverseLab/SAM/scrapers/paywall_bypass/`

### Core Files

| File | Purpose |
|------|---------|
| `smart_bypass.py` | Main bypass logic - tries multiple strategies |
| `browser.py` | Playwright stealth browser automation |
| `archives.py` | Wayback Machine / Archive.today integration |
| `extractors.py` | Content extraction (JSON-LD, article parsing) |
| `rules.py` | Site-specific bypass rules |
| `PAYWALL_KNOWLEDGE.md` | Comprehensive documentation |

### Usage

```python
from paywall_bypass.smart_bypass import SmartPaywallBypass

bypasser = SmartPaywallBypass()
result = await bypasser.bypass("https://www.nytimes.com/article")

if result.success:
    print(f"Title: {result.title}")
    print(f"Content: {result.content}")
    print(f"Method: {result.method}")
    print(f"Paywall Type: {result.paywall_type}")
```

### Bypass Strategies

1. **JS-disabled fetch** - Load page without JavaScript
2. **Script blocking** - Block paywall script domains (Piano, Zephr, etc.)
3. **Overlay removal** - Remove paywall DOM elements after load

### Site Classification

#### Client-Side Paywalls (BYPASSABLE)
| Site | Method | Notes |
|------|--------|-------|
| nytimes.com | overlay_removed | Metered paywall |
| wwd.com | js_disabled | Piano paywall |
| theatlantic.com | js_disabled | Metered |
| medium.com | js_disabled | Member stories |
| washingtonpost.com | js_disabled | Metered |

#### Server-Side Paywalls (NOT BYPASSABLE)
| Site | Reason |
|------|--------|
| wsj.com | Content never sent without auth |
| bloomberg.com | Hard paywall |
| archive.vogue.com | ProQuest academic database |
| ft.com | Hard paywall |
| economist.com | Hard paywall |

---

## Site Probes (Ready to Build)

### W Magazine (wmagazine.com)

**Target:** Fashion/culture magazine articles

**Status:** ✅ OPEN - Full content accessible via JS-disabled fetch

| Metric | Value |
|--------|-------|
| Content per article | ~13,000 chars |
| Paragraphs per article | ~33 |
| Has sitemap | Yes |
| Paywall | None detected |

**Priority:** HIGH - Most content per article of probed sites

---

### V Magazine (vmagazine.com)

**Target:** Fashion/culture magazine articles

**Status:** ✅ OPEN - Content accessible

| Metric | Value |
|--------|-------|
| Content per article | ~1,700 chars |
| Paragraphs per article | ~8 |
| Platform | WordPress |
| Paywall | None |

---

### Juxtapoz (juxtapoz.com)

**Target:** Art and culture articles

**Status:** ✅ OPEN - Articles accessible

| Metric | Value |
|--------|-------|
| Content | Full articles |
| Has sitemap | Yes |
| Paywall | None |

---

### The Pop Covers (thepop.com/covers)

**Target:** Magazine cover images

**Status:** ✅ OPEN - Images accessible

| Metric | Value |
|--------|-------|
| Images found | 46+ covers |
| CDN | Webflow (cdn.prod.website-files.com) |
| Login required | No |

---

### FirstView.com

**Target:** Fashion runway photography

**Status:** ✅ Probed - open access, no ripper built yet

| Metric | Value |
|--------|-------|
| Estimated images | ~800,000 |
| Image size | ~277 KB full-res |
| Storage estimate | ~220 GB |
| Login required | **NO** |

**Access Pattern:**
```
Thumbnail: https://firstview.com/files/{id}/thumb_{filename}.jpg
Full size: https://firstview.com/files/{id}/{filename}.jpg
```

Just remove `thumb_` prefix for full resolution.

---

## Vogue Archive Deep Analysis

**Site:** archive.vogue.com

**Status:** ❌ Server-side paywall - NOT bypassable

### Infrastructure
- Platform: WordPress + Laravel
- CDN: Azure Blob Storage (`vogueprod.blob.core.windows.net`)
- Static assets: Pugpig CDN
- Hosted by: ProQuest (academic database provider)

### What's Accessible
- Thumbnails up to 0x600 (~51 KB)
- Article titles and metadata
- Issue navigation

### What's NOT Accessible
- Full article text (0 paragraphs in any response)
- Full-resolution page scans
- PDF exports

### Tested Techniques (ALL FAILED)
- JS-disabled fetch
- Googlebot/Bingbot UA spoofing
- API endpoint probing
- CDN size manipulation
- Wayback Machine (also has no content)

### JWT Config (Proves Server-Side)
```json
{
  "is_authenticated": false,
  "HasAccess": false,
  "auth": {"cheatCode": null}
}
```

### Legitimate Access
- Library access (free via ProQuest Fashion Studies Collection)
- University access
- Direct subscription ($1,575/year)

---

## Blocked/Paywalled Sites (Not Accessible)

| Site | Status | Reason |
|------|--------|--------|
| commarts.com | ❌ PAYWALLED | Server-side, only 50 chars accessible |
| idnworld.com/mags | ❌ PAYWALLED | Purchase required, 0 paragraphs |
| hifructose.com | ❌ BLOCKED | 415 error (rejecting all requests) |
| ui8.net | ❌ BLOCKED | Cloudflare 403 protection |
| youworkforthem.com | ⚠️ Marketplace | Preview images only, purchase required for files |

---

## Current Download Status

| Scraper | Location | Progress | ETA |
|---------|----------|----------|-----|
| Nifty | David External | ~2K/38K stories | ~18 hours |
| AO3 | David External | ~1K/3K works | ~5 hours |
| WWD | #1 | Indexing 293K articles | Then ~days for full download |

---

## Storage Summary

| Drive | Used For | Estimated Final Size |
|-------|----------|---------------------|
| David External | Nifty, AO3 | ~5-10 GB |
| #1 | WWD | ~600 GB |
| (TBD) | FirstView | ~220 GB |

---

## Dependencies

```bash
pip install requests beautifulsoup4 playwright aiohttp
playwright install chromium
```

---

## Environment Setup

```bash
cd /Users/davidquinton/ReverseLab/SAM/scrapers
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if exists
```

---

## Key Insights

### Client-Side vs Server-Side Paywalls

**Client-Side:**
- Full content sent to browser
- JavaScript hides it with overlay
- **Bypass:** Disable JS or remove overlay
- Examples: NYT, WWD, Atlantic, Medium

**Server-Side:**
- Content NEVER sent without authentication
- No client-side trick works
- **Only option:** Archives or legitimate access
- Examples: WSJ, Bloomberg, Vogue Archive, FT

### Rate Limiting Best Practices
- Nifty: 2 second delay
- AO3: 3-5 second delay (strict)
- WWD: 1.5 second delay
- Always use realistic User-Agent

---

*Last Updated: January 2026*
*System: SAM Scraper Collection*
