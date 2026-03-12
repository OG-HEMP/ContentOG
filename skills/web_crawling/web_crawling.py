import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from config.config import settings
from skills.http_utils import request_json, request_text

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 20000


def _clean_text(html_text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(html_text: str, url: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return urlparse(url).path.strip("/") or urlparse(url).netloc


def _extract_publish_date(html_text: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']publish_date["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']pubdate["\'][^>]+content=["\'](.*?)["\']',
        r'<time[^>]+datetime=["\'](.*?)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return datetime.utcnow().isoformat()


def _crawl_via_firecrawl(url: str) -> dict:
    if not settings.firecrawl_api_key:
        raise RuntimeError("FIRECRAWL_API_KEY is required when crawler.provider is 'firecrawl'.")

    payload = {
        "url": url,
        "formats": ["markdown", "html"],
    }
    response = request_json(
        "https://api.firecrawl.dev/v1/scrape",
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ContentOG/1.0",
        },
        payload=payload,
        timeout=settings.crawler_timeout,
        retries=settings.crawler_retry_attempts,
        backoff_seconds=settings.crawler_backoff_seconds,
    )
    if response.get("success") is False:
        raise RuntimeError(f"Firecrawl scrape failed: {response}")

    data = response.get("data", {})
    raw_html = str(data.get("html") or "")
    content = str(data.get("markdown") or _clean_text(raw_html))
    title = str((data.get("metadata") or {}).get("title") or _extract_title(raw_html, url))
    publish_date = str((data.get("metadata") or {}).get("publishedTime") or _extract_publish_date(raw_html))
    return {
        "title": title,
        "content": content,
        "word_count": len(content.split()),
        "publish_date": publish_date,
    }


def _crawl_via_http(url: str) -> dict:
    raw_html = request_text(
        url,
        headers={"User-Agent": "ContentOG/1.0"},
        timeout=settings.crawler_timeout,
        retries=settings.crawler_retry_attempts,
        backoff_seconds=settings.crawler_backoff_seconds,
    )
    title = _extract_title(raw_html, url)
    content = _clean_text(raw_html)
    return {
        "title": title,
        "content": content,
        "word_count": len(content.split()),
        "publish_date": _extract_publish_date(raw_html),
    }


def crawl_page(url: str) -> dict:
    """Fetch and extract article-like content using centralized settings."""
    provider = settings.crawler_provider.lower()

    try:
        if provider == "firecrawl":
            payload = _crawl_via_firecrawl(url)
        else:
            payload = _crawl_via_http(url)
    except Exception as exc:
        raise RuntimeError(f"Crawl failed for {url}: {exc}") from exc

    content = payload.get("content") or ""
    if len(content) > _MAX_CONTENT_CHARS:
        content = content[:_MAX_CONTENT_CHARS]
        payload["content"] = content
        payload["word_count"] = len(content.split())

    logger.info("Crawled %s with %d words", url, payload["word_count"])
    return payload
