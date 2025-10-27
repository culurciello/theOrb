# LII Search Implementation Guide

## Problem Summary

Cornell's Legal Information Institute (LII) search has several technical issues:

1. **Web Search Page**: The search results page doesn't populate results via JavaScript
2. **API Endpoint**: Returns 500 Internal Server Error
3. **Google Search**: Blocks automated requests with CAPTCHA

## Solutions

### ✅ Recommended: SerpAPI (Most Reliable)

Use **SerpAPI** to perform Google searches programmatically.

**Setup:**
```bash
# Install SerpAPI client
pip install google-search-results

# Sign up for free account (100 searches/month)
# https://serpapi.com

# Set your API key
export SERPAPI_KEY="your_api_key_here"
```

**Usage:**
```python
from lii_search_serpapi import search_lii_serpapi

results = search_lii_serpapi("privacy law", num_results=5)
for r in results:
    print(f"{r['title']}: {r['url']}")
```

**File:** `lii-search-serpapi.py`

---

### ⚠️ Alternative: Playwright (Unreliable)

Attempts to scrape LII's search page directly. May not work due to JavaScript issues.

**Usage:**
```python
from lii_search import search_lii_playwright

results = search_lii_playwright("privacy law", num_results=5)
```

**Limitations:**
- Requires 30+ second wait times
- May not return results even after waiting
- LII's JavaScript often fails to populate results

**File:** `lii-search.py`

---

### 🔍 Alternative: Search Specific Sections

Instead of general search, target specific LII sections:

```python
sections = {
    "US Code": "https://www.law.cornell.edu/uscode/text/",
    "CFR": "https://www.law.cornell.edu/cfr/text/",
    "Supreme Court": "https://www.law.cornell.edu/supremecourt/text/",
    "Constitution": "https://www.law.cornell.edu/constitution/",
}
```

Navigate directly to these sections and search within them.

---

### 📋 Alternative: Manual Caching

For repeated queries:
1. Perform manual searches on LII
2. Cache the results in a JSON file
3. Load from cache in your application

---

## Testing & Debugging

### Test Files Created:
- `lii-search-debug.py` - Page structure analysis
- `lii-search-debug2.py` - Wait for dynamic content
- `lii-search-debug3.py` - Network request monitoring
- `lii-search-api.py` - Direct API attempts
- `lii-search-interactive.py` - User interaction simulation
- `lii-search-fixed.py` - Extended wait implementation
- `lii-search-google-debug.py` - Google search test

### Debug Artifacts:
- `lii-page-debug.html` - LII search page HTML
- `lii-page-debug.png` - Screenshot of empty results
- `google-search-debug.png` - CAPTCHA screenshot

---

## Cost Comparison

| Method | Cost | Reliability | Speed |
|--------|------|-------------|-------|
| SerpAPI | $0 - $50/mo | ⭐⭐⭐⭐⭐ | Fast |
| ScraperAPI | $0 - $30/mo | ⭐⭐⭐⭐ | Medium |
| Playwright | Free | ⭐ | Very Slow |
| Manual Cache | Free | ⭐⭐⭐ | Instant |

---

## Recommendation

**For Production:** Use SerpAPI
- Reliable and fast
- Handles CAPTCHA automatically
- Free tier available (100 searches/month)
- Easy to implement

**For Development/Testing:** Use manual caching
- Search LII manually
- Save results to JSON
- Load from cache during testing

**Avoid:** Direct scraping with Playwright
- LII's search page is broken
- Extremely unreliable
- Slow (30+ seconds per search)
- Fails most of the time

---

## Example: SerpAPI Implementation

```python
import os
from serpapi import GoogleSearch

def search_lii(query, num_results=5):
    params = {
        "q": f"site:law.cornell.edu {query}",
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": num_results,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", "")
        }
        for r in results.get("organic_results", [])
    ]

# Usage
results = search_lii("data privacy")
for r in results:
    print(f"{r['title']}\n{r['url']}\n{r['snippet']}\n")
```

---

## Support

- SerpAPI Docs: https://serpapi.com/search-api
- LII Homepage: https://www.law.cornell.edu
- Playwright Docs: https://playwright.dev/python/

---

## Summary

The original `lii-search.py` file has been updated with documentation explaining the issues and providing a fallback implementation. However, **for reliable production use, SerpAPI (in `lii-search-serpapi.py`) is strongly recommended**.
