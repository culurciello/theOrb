"""
LII Search using SerpAPI - RECOMMENDED SOLUTION

This is the most reliable way to search LII content.

Setup:
1. Sign up at https://serpapi.com (free tier: 100 searches/month)
2. Get your API key
3. Install: pip install google-search-results
4. Set environment variable: export SERPAPI_KEY="your_key_here"
   OR pass it directly to the function
"""

import os

def search_lii_serpapi(query, num_results=5, api_key=None):
    """
    Search LII using SerpAPI for reliable results.

    Args:
        query: Search query
        num_results: Number of results to return
        api_key: SerpAPI key (or set SERPAPI_KEY environment variable)

    Returns:
        List of dicts with keys: title, url, snippet
    """
    try:
        from serpapi import GoogleSearch
    except ImportError:
        print("❌ SerpAPI not installed. Run: pip install google-search-results")
        return []

    # Get API key from parameter or environment
    api_key = api_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        print("❌ No API key provided. Set SERPAPI_KEY environment variable or pass api_key parameter.")
        print("   Sign up at: https://serpapi.com")
        return []

    # Build search query
    search_query = f"site:law.cornell.edu {query}"

    params = {
        "q": search_query,
        "api_key": api_key,
        "num": num_results,
    }

    print(f"🔍 Searching LII via SerpAPI for: {query}")

    try:
        search = GoogleSearch(params)
        results_data = search.get_dict()

        results = []
        organic_results = results_data.get("organic_results", [])

        for item in organic_results[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })

        print(f"✅ Found {len(results)} results")
        return results

    except Exception as e:
        print(f"❌ SerpAPI error: {e}")
        return []


def search_lii_requests_fallback(query, num_results=5):
    """
    Fallback method using requests library.
    Tries to access LII's search API directly with different parameters.
    """
    import requests
    import json

    # Try different API endpoints and parameters
    endpoints_to_try = [
        {
            "url": "https://api.law.cornell.edu/lii/search",
            "params": {"query": query, "size": num_results}
        },
        {
            "url": "https://api.law.cornell.edu/search",
            "params": {"q": query, "limit": num_results}
        },
    ]

    for endpoint in endpoints_to_try:
        try:
            print(f"🔍 Trying API: {endpoint['url']}")
            response = requests.get(
                endpoint["url"],
                params=endpoint["params"],
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ API call successful!")

                # Try to parse results (structure may vary)
                results = []
                # Add parsing logic here based on actual API response
                return results
            else:
                print(f"   Status: {response.status_code}")

        except Exception as e:
            print(f"   Error: {e}")
            continue

    print("❌ All API endpoints failed")
    return []


if __name__ == "__main__":
    query = "privacy"

    # Method 1: SerpAPI (recommended)
    print("=" * 80)
    print("METHOD 1: SerpAPI (Recommended)")
    print("=" * 80)
    results = search_lii_serpapi(query)

    if results:
        for i, r in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Title: {r['title']}")
            print(f"URL: {r['url']}")
            print(f"Snippet: {r['snippet']}\n")
    else:
        print("\n" + "=" * 80)
        print("METHOD 2: Direct API (Fallback)")
        print("=" * 80)
        results = search_lii_requests_fallback(query)
