import logging
from typing import List

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/embeddings"


def generate_embedding(text: str) -> List[float]:
    """Generate OpenAI embeddings using centralized settings."""
    
    # Truncate text to avoid token limits (Safe estimate for 8k tokens)
    clean_text = (text or "").strip()
    if len(clean_text) > 25000:
        clean_text = clean_text[:25000]

    payload = {
        "model": settings.embeddings_model,
        "input": clean_text,
    }
    
    try:
        result = request_json(
            _API_URL,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=settings.embeddings_timeout,
            retries=settings.embeddings_retry_attempts,
            backoff_seconds=settings.embeddings_backoff_seconds,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

    try:
        vector = result["data"][0]["embedding"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected embeddings response shape: {result}") from exc
    return [float(v) for v in vector]
