import logging
from urllib.parse import urlencode, urlparse

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)
_SERPAPI_URL = "https://serpapi.com/search.json"


def discover_serp_urls(keyword: str) -> list:
    """Discover live SERP URLs using SerpApi with centralized settings."""
    
    query = urlencode(
        {
            "engine": "google",
            "q": keyword,
            "hl": settings.serp_language,
            "gl": settings.serp_region,
            "num": settings.serp_results_per_keyword,
            "api_key": settings.serp_api_key,
        }
    )
    
    try:
        payload = request_json(
            f"{_SERPAPI_URL}?{query}",
            headers={"User-Agent": "ContentOG/1.0"},
            timeout=settings.serp_timeout,
            retries=settings.serp_retry_attempts,
            backoff_seconds=settings.serp_backoff_seconds,
        )
    except Exception as exc:
        raise RuntimeError(f"SerpApi request failed: {exc}") from exc

    if payload.get("error"):
        raise RuntimeError(f"SerpApi returned error: {payload.get('error')}")

    organic_results = payload.get("organic_results", [])
    results = []
    for item in organic_results:
        url = item.get("link")
        if not url:
            continue
        rank = item.get("position")
        if rank is None:
            rank = len(results) + 1
        domain = urlparse(url).netloc
        results.append(
            {
                "url": url,
                "domain": domain,
                "rank": int(rank),
                "keyword": keyword,
            }
        )

    if not results:
        raise RuntimeError(f"No organic SERP results returned for keyword '{keyword}'.")

    logger.info("SERP discovered %d urls for keyword '%s'", len(results), keyword)
    return results
