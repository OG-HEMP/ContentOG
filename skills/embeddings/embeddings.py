import logging
from typing import List

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/embeddings"


_LOCAL_MODEL = None

def _get_local_model():
    global _LOCAL_MODEL
    if _LOCAL_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = settings.embeddings_model if "embedding" not in settings.embeddings_model else "all-MiniLM-L6-v2"
            logger.info(f"Loading local embedding model: {model_name}...")
            _LOCAL_MODEL = SentenceTransformer(model_name)
        except Exception as exc:
            raise RuntimeError(f"Failed to load local embedding model: {exc}")
    return _LOCAL_MODEL

def generate_embedding(text: str) -> List[float]:
    """Generate embeddings using the configured provider (openai or local)."""
    clean_text = (text or "").strip()
    if not clean_text:
        return [0.0] * 1536 # Fallback if empty
        
    if settings.embeddings_provider.lower() == "local":
        model = _get_local_model()
        vector = model.encode(clean_text)
        return [float(v) for v in vector]

    # OpenAI Provider (Default)
    # Truncate text to avoid token limits (Safe estimate for 8k tokens)
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
        vector = result["data"][0]["embedding"]
        return [float(v) for v in vector]
    except Exception as exc:
        if "insufficient_quota" in str(exc) or "429" in str(exc):
            logger.warning("OpenAI quota exceeded. Recommend switching EMBEDDINGS_PROVIDER to 'local'.")
        raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc
