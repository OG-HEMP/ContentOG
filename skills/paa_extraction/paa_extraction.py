import logging
from urllib.parse import urlencode

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)
_SERPAPI_URL = "https://serpapi.com/search.json"


def _extract_questions(payload: dict) -> list:
    candidates = []
    for key in ("related_questions", "people_also_ask", "inline_people_also_ask"):
        items = payload.get(key, [])
        if isinstance(items, list):
            candidates.extend(items)

    questions = []
    seen = set()
    for item in candidates:
        question = ""
        if isinstance(item, dict):
            question = str(item.get("question", "")).strip()
        elif isinstance(item, str):
            question = item.strip()
        if question and question.lower() not in seen:
            seen.add(question.lower())
            questions.append(question)
    return questions


def extract_paa_questions(keyword: str) -> list:
    """Extract live PAA questions for a keyword via SerpApi with centralized settings."""
    
    query = urlencode(
        {
            "engine": "google",
            "q": keyword,
            "hl": settings.serp_language,
            "gl": settings.serp_region,
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
        raise RuntimeError(f"SerpApi PAA request failed: {exc}") from exc

    if payload.get("error"):
        raise RuntimeError(f"SerpApi returned error: {payload.get('error')}")

    questions = _extract_questions(payload)
    if not questions:
        logger.warning(f"No PAA questions returned for keyword '{keyword}'. Continuing without PAA.")
        return []

    logger.info("PAA extracted %d questions for keyword '%s'", len(questions), keyword)
    return questions
