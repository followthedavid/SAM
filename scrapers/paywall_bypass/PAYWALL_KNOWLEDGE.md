# Paywall Bypass Knowledge Base

## Core Insight: Client-Side vs Server-Side Paywalls

The critical distinction that determines if a paywall can be bypassed:

| Type | How It Works | Bypassable? |
|------|-------------|-------------|
| **Client-Side** | Full content sent to browser, hidden by JavaScript overlay | ✅ YES |
| **Server-Side** | Content NOT sent unless authenticated server-side | ❌ NO |

---

## Client-Side Paywalls (BYPASSABLE)

### How They Work
1. Server sends full article HTML to browser
2. JavaScript checks subscription status
3. If not subscribed, JS adds overlay/modal to hide content
4. Content is still in the DOM, just visually hidden

### Why They Exist
- **SEO**: Publishers want Google to index full content for search rankings
- **Ease of Implementation**: Just add JS to existing site
- **Metered Access**: Easy to track "X free articles" with cookies

### Known Client-Side Sites
- New York Times (metered)
- WWD (Women's Wear Daily)
- The Atlantic
- Medium
- Washington Post (some content)
- Most Piano/TinyPass powered paywalls

### Bypass Techniques (in order of effectiveness)

#### 1. JavaScript Disabled Fetch
```python
context = await browser.new_context(java_script_enabled=False)
```
- Load page with JS completely off
- Paywall script never executes
- Content is already in HTML

#### 2. Block Paywall Scripts
Block requests to known paywall domains:
- `tinypass.com` - Piano paywall
- `piano.io` - Piano paywall
- `pelcro.com` - Pelcro paywall
- `zephr.com` - Zephr paywall
- `cxense.com` - Content analytics
- `matheranalytics.com` - Metering
- `blueconic.net` - Personalization

#### 3. DOM Overlay Removal
Remove paywall elements after page loads:
```javascript
document.querySelectorAll('[class*="paywall"]').forEach(el => el.remove());
document.body.style.overflow = 'auto';
```

#### 4. Reader Mode / Readability
Extract article content using readability algorithms before JS executes.

#### 5. Cookie Clearing
For metered paywalls, clear cookies to reset article count:
- Clear all cookies for domain
- Use incognito/private mode
- Rotate IP addresses

---

## Server-Side Paywalls (NOT BYPASSABLE)

### How They Work
1. Browser requests article
2. Server checks authentication/subscription status
3. If not subscribed, server sends ONLY teaser/preview
4. Full content is NEVER transmitted to browser

### Why They're Secure
- Content literally doesn't exist in browser
- No client-side trick can reveal what wasn't sent
- Authentication happens before content delivery

### Known Server-Side Sites
- Wall Street Journal (WSJ)
- Bloomberg
- Financial Times (FT)
- The Economist
- Vogue Archive
- Barron's
- Most premium financial/business publications

### Limited Options for Server-Side

#### 1. Web Archives (Historical Content Only)
- **Wayback Machine** (archive.org): Check if article was previously archived
- **Archive.today**: Community-saved snapshots
- **Google Cache**: Increasingly deprecated

Limitation: Only works if someone previously saved the article.

#### 2. Library Access (Legitimate)
Many libraries provide free digital access to:
- NYT, WSJ, Bloomberg via library card
- Academic databases (JSTOR, etc.)
- Check your local library's digital offerings

#### 3. Referrer Tricks (Mostly Patched)
Some sites historically gave free access via:
- Google search referrer
- Facebook/Twitter referrer
- AMP versions

**Status**: Most major sites have patched these. Worth trying but low success rate.

#### 4. Googlebot User-Agent (Mostly Patched)
```python
user_agent = "Googlebot/2.1 (+http://www.google.com/bot.html)"
```
**Status**: Major sites now detect and block this. May work on smaller sites.

---

## Site-Specific Intelligence

### Confirmed Client-Side (Bypassable)
| Site | Method That Works | Notes |
|------|-------------------|-------|
| nytimes.com | overlay_removed | 2315 words extracted |
| wwd.com | js_disabled | 756 words extracted |
| theatlantic.com | js_disabled | Metered paywall |
| medium.com | js_disabled | Member-only stories |
| washingtonpost.com | js_disabled | Metered |

### Confirmed Server-Side (Not Bypassable)
| Site | Tested Methods | Result |
|------|----------------|--------|
| wsj.com | all | 401 Unauthorized for all user agents |
| bloomberg.com | all | 403 Forbidden for all requests |
| archive.vogue.com | all | See detailed analysis below |
| ft.com | all | Hard paywall |
| economist.com | all | Hard paywall |

---

## Vogue Archive Deep Analysis (COMPREHENSIVE)

### Infrastructure Overview
- **Platform**: WordPress backend (`/wp-admin/` in robots.txt)
- **Backend**: Laravel PHP framework (laravel_session cookie)
- **CDN**: Azure Blob Storage (`vogueprod.blob.core.windows.net`)
- **Static Assets**: Pugpig CDN (`vogue.archive.content.pugpig.com`)
- **Robots.txt**: Minimal - only blocks `/wp-admin/`
- **Sitemaps**: 2,931 issues indexed (1892-present), ~32 articles per issue

### CDN Architecture (Discovered via Network Interception)
```
Image URL Pattern:
https://vogueprod.blob.core.windows.net/vogueoutput{YYYYMMDD}thumbnails/{Type}/0x{Height}/{Filename}.jpg

Types: Covers, Spreads, Pages, Media
Heights: 90, 300, 420, 600 (MAX)
```

**Maximum Available Sizes:**
| Type | Max Size | File Size |
|------|----------|-----------|
| Covers | 0x600 | ~51 KB |
| Pages | 0x600 | ~52 KB |
| Spreads | 0x600 | ~43 KB |

**Full-resolution images are NOT publicly accessible.**

### JWT Configuration (Extracted from window.ReactConfig)
```json
{
  "client": "VG",
  "blobAccount": "vogueprod",
  "blobPrefix": "vogueoutput",
  "thumbHeight": "360",
  "cdnDomain": "https://vogue.archive.content.pugpig.com",
  "is_authenticated": false,
  "auth": {
    "enabled": true,
    "cheatCode": null
  },
  "latestIssue": {
    "HasAccess": false
  }
}
```

**Key Findings from JWT:**
- `is_authenticated: false` - Confirms unauthenticated state
- `HasAccess: false` - No content access
- `cheatCode: null` - No backdoor exists
- `auth.enabled: true` - Authentication required

### What's Accessible Without Login
- Issue covers and thumbnails (up to 600px height)
- Article titles and short summaries (metadata only)
- Article metadata (author, date, page numbers)
- Page counts and issue navigation
- Sitemap with all 2,931 issues and article URLs

### What's NOT Accessible
- Full article text (0 paragraphs in any HTML response)
- High-resolution page scans (only thumbnails)
- Full-page images (gated behind auth)
- PDF downloads
- Print-quality exports

### Tested Techniques (ALL FAILED - January 2026)

| Technique | Result |
|-----------|--------|
| Raw HTTP fetch | 93KB HTML, 0 content paragraphs |
| JavaScript disabled | Same - 0 content |
| Googlebot UA | Same - 0 content |
| Bingbot UA | Same - 0 content |
| Facebook crawler UA | Same - 0 content |
| Twitter bot UA | Same - 0 content |
| Archive.org bot UA | Same - 0 content |
| Wayback Machine | Archived pages have 0 content |
| JSON-LD extraction | No articleBody present |
| API endpoints (/graphql, /wp-json, etc.) | All redirect to homepage |
| CDN size manipulation (0x1200, etc.) | 404 - larger sizes don't exist |
| Alternative containers | None found |
| Pugpig CDN content paths | 400/404 errors |
| Viewer/reader endpoints | Redirect to homepage |

### API Probing Results
```
/graphql         → 200 (returns homepage HTML)
/wp-json/        → 200 (returns homepage HTML)
/feed/           → 200 (returns homepage HTML)
/sitemap.xml     → 200 (valid XML, 3 sub-sitemaps)
/magazine        → 200 (49KB - different page)
/view            → 200 (82KB - different page)
```

All "API" endpoints return the homepage - they're rewritten, not actual APIs.

### Why It's Unbreakable (Technical Proof)

1. **Authentication at Server Level**
   - JWT explicitly shows `is_authenticated: false`
   - No content is included in ANY response for unauthenticated users
   - Content containers in Azure Blob Storage are private

2. **No Full-Size Images in CDN**
   - Only thumbnail containers exist (`vogueoutput{date}thumbnails`)
   - No `vogueoutput{date}`, `vogueoutput{date}full`, etc.
   - Maximum size is 0x600 (intentionally limited)

3. **No Backdoors**
   - `cheatCode: null` in JWT config
   - No debug endpoints
   - No alternative access patterns

4. **Historical Archives Also Empty**
   - Wayback Machine captures have 0 content paragraphs
   - Server-side paywall has been in place since launch
   - No historical "free period" to exploit

### Legitimate Access Options
1. **Library Access (FREE)**: Many public/academic libraries subscribe to ProQuest
   - Search your library for "Vogue Archive" or "Fashion Studies Collection"
   - As of June 2025, Vogue Archive is part of ProQuest's Fashion Studies Collection
2. **University Access**: Most fashion/design schools have access
3. **Direct Subscription**: $1,575/year at archive.vogue.com

---

## Detection Algorithm

To determine paywall type programmatically:

```python
async def detect_paywall_type(url):
    # Fetch with JS disabled
    no_js_content = await fetch_no_js(url)

    # Fetch with JS enabled
    js_content = await fetch_with_js(url)

    if len(no_js_content) > 500:
        return "client-side"  # Content present without JS
    elif len(js_content) > len(no_js_content) + 200:
        return "client-side"  # JS adds content (rare)
    else:
        return "server-side"  # No content either way
```

---

## Implementation: SmartPaywallBypass

Location: `/Users/davidquinton/ReverseLab/SAM/scrapers/paywall_bypass/smart_bypass.py`

### Usage
```python
from paywall_bypass.smart_bypass import SmartPaywallBypass

bypasser = SmartPaywallBypass()
result = await bypasser.bypass("https://www.nytimes.com/article")

if result.success:
    print(f"Title: {result.title}")
    print(f"Content: {result.content}")
    print(f"Paywall Type: {result.paywall_type}")
else:
    print(f"Failed: {result.error}")
```

### What It Does
1. **JS-disabled fetch**: Loads without JavaScript
2. **Script-blocked fetch**: Blocks paywall script domains
3. **Overlay removal**: Removes paywall DOM elements
4. Compares all three, returns best result
5. Classifies paywall type for future reference

---

## Server-Side Paywall Research (COMPLETED)

### Techniques That NO LONGER WORK

#### 1. First Click Free (DEAD - October 2017)
- Google ended this policy in favor of "Flexible Sampling"
- Publishers now choose how many (if any) free articles to show
- WSJ, Bloomberg, FT chose ZERO free articles
- [Source: Google ended First Click Free](https://searchengineland.com/google-first-click-free-replaced-flexible-sampling-283667)

#### 2. Google Referrer Bypass (PATCHED)
- No longer required for search indexing
- Publishers can fully block Google referrer access
- WSJ traffic dropped 44% but subscriptions jumped 110K when they blocked it
- [Source: WSJ Traffic Drop](https://news.slashdot.org/story/17/06/05/2315228/wall-street-journals-google-traffic-drops-44-after-pulling-out-of-first-click-free)

#### 3. AMP Cache (PATCHED)
- Sites now use `noarchive` meta tag
- AMP versions also require authentication
- Publishers are abandoning AMP entirely
- [Source: AMP Paywall Challenges](https://dangoldin.com/2017/04/16/amp-and-subscription-paywalls/)

#### 4. RSS Feeds (SUMMARIES ONLY)
- Major publications only provide headlines + snippets
- Full text deliberately withheld
- Third-party generators can't get content that isn't published

#### 5. Googlebot User-Agent (DETECTED)
- Major sites fingerprint and detect UA spoofing
- May work on small sites, fails on WSJ/Bloomberg/FT

### Techniques With LIMITED Success

#### 1. Web Archives (HISTORICAL ONLY)
- Wayback Machine: Only if previously archived
- Archive.today: Community-submitted snapshots
- Success rate: ~10-20% for recent articles
- Better for older/viral content

#### 2. Social Media Links (INCONSISTENT)
- Some publishers give limited free access via social sharing
- Mostly patched by major publications
- Worth trying but don't rely on it

### LEGITIMATE Options That WORK

#### 1. Library Access (FREE & LEGAL)
Many public libraries offer digital access to:
- New York Times
- Wall Street Journal
- The Economist
- Bloomberg (some libraries)
- Financial Times (some libraries)

**How to access:**
1. Get a library card (free with proof of residence)
2. Go to library's digital resources page
3. Find newspaper/magazine section
4. Log in with library credentials

#### 2. University/Academic Access
- Most universities provide WSJ, NYT, Bloomberg
- Use .edu email to register
- Available to students, faculty, staff

#### 3. Employer Subscriptions
- Many companies have corporate accounts
- Check with IT/HR department

#### 4. Free Tiers & Promotions
- NYT: ~10 free articles/month
- Washington Post: Some free content
- Watch for promotional $1/month offers

---

## Why Server-Side Paywalls Win

### The Business Reality
- WSJ proved subscription revenue beats ad revenue
- When they blocked free access: 44% traffic drop, BUT 110K new subscribers
- ROI favors hard paywalls for premium content

### The Technical Reality
- Content literally not transmitted without auth
- No client-side trick reveals server-side content
- Authentication happens BEFORE content delivery

### The Legal Reality
- Terms of Service prohibit bypass
- CFAA may apply to circumvention
- Archives are legal (Fair Use for preservation)

---

## Conclusion: Accept the Limits

**For client-side paywalls**: Our techniques work well (NYT, WWD, Atlantic, Medium, etc.)

**For server-side paywalls**:
- Accept that bypass isn't technically possible
- Use archives for historical content
- Use library access for legitimate free access
- Subscribe if you need regular access

---

## Future Research Areas

### For Improving Client-Side Bypass
- [ ] More paywall script domains to block
- [ ] Better content extraction selectors
- [ ] Cookie isolation per-request
- [ ] Fingerprint randomization

---

## Legal & Ethical Notes

- This documentation is for educational/research purposes
- Bypassing paywalls may violate Terms of Service
- Consider supporting journalism through subscriptions
- Library access is a legitimate free alternative
- Archive services preserve public interest content

---

## References

- [Client-Side vs Server-Side Paywalls](https://www.amediaoperator.com/analysis/comparing-server-side-and-client-side-paywall-methods/)
- [Piano Paywall Architecture](https://www.piano.io/resources/piano-lessons-optimize-audience-targeting-dynamic-paywall)
- [NYT Paywall History](https://www.niemanlab.org/2011/03/that-was-quick-four-lines-of-code-is-all-it-takes-for-the-new-york-times-paywall-to-come-tumbling-down-2/)
- [Bypass Paywalls Chrome Extension](https://github.com/iamadamdev/bypass-paywalls-chrome)

---

*Last Updated: January 2026*
*Tested by: SAM Scraper System*
