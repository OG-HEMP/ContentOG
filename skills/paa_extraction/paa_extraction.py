import logging
import os
from urllib.parse import urlencode

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
        raise RuntimeError("SERP_API_KEY is required for PAA extraction.")
    return key


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
    """Extract live PAA questions for a keyword via SerpApi."""
    settings = _settings()
    serp_settings = settings.get("serp", {}) if isinstance(settings, dict) else {}
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
        raise RuntimeError(f"SerpApi PAA request failed: {exc}") from exc

    if payload.get("error"):
        raise RuntimeError(f"SerpApi returned error: {payload.get('error')}")

    questions = _extract_questions(payload)
    if not questions:
        raise RuntimeError(f"No PAA questions returned for keyword '{keyword}'.")

    logger.info("PAA extracted %d questions for keyword '%s'", len(questions), keyword)
    return questions
