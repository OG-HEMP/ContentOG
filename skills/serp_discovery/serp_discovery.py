import logging
import os
from urllib.parse import urlencode, urlparse

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

from skills.http_utils import request_json

logger = logging.getLogger(__name__)
_SERPAPI_URL = "https://serpapi.com/search.json"


def _settings() -> dict:
    if yaml is None:
        return {}
    try:
        with open("config/settings.yaml", "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def _serp_api_key() -> str:
    key = (os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_KEY") or "").strip()
    if not key:
        raise RuntimeError("SERP_API_KEY is required for SERP discovery.")
    return key


def discover_serp_urls(keyword: str) -> list:
    """Discover live SERP URLs using SerpApi."""
    settings = _settings()
    serp_settings = settings.get("serp", {}) if isinstance(settings, dict) else {}
    num_results = int(serp_settings.get("results_per_keyword", 10))
    language = str(serp_settings.get("language", "en"))
    region = str(serp_settings.get("region", "us"))
    timeout = int(serp_settings.get("timeout", 30))
    retries = int(serp_settings.get("retry_attempts", 3))
    backoff_seconds = float(serp_settings.get("backoff_seconds", 1.0))

    query = urlencode(
        {
            "engine": "google",
            "q": keyword,
            "hl": language,
            "gl": region,
            "num": num_results,
            "api_key": _serp_api_key(),
        }
    )
    try:
        payload = request_json(
            f"{_SERPAPI_URL}?{query}",
            headers={"User-Agent": "ContentOG/1.0"},
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
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
