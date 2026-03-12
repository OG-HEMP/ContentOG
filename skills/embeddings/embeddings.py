import logging
import json
import os
from typing import List

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from skills.http_utils import request_json

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/embeddings"
_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def _api_key() -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings.")
    return api_key


def _settings() -> dict:
    if yaml is None:
        return {}
    try:
        with open("config/settings.yaml", "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def generate_embedding(text: str) -> List[float]:
    settings = _settings()
    embedding_settings = settings.get("embeddings", {}) if isinstance(settings, dict) else {}
    timeout = int(embedding_settings.get("timeout", 60))
    retries = int(embedding_settings.get("retry_attempts", 3))
    backoff_seconds = float(embedding_settings.get("backoff_seconds", 1.0))
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", str(embedding_settings.get("model_name", _MODEL_NAME)))

    payload = {
        "model": model_name,
        "input": text or "",
    }
    try:
        result = request_json(
            _API_URL,
            method="POST",
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

    try:
        vector = result["data"][0]["embedding"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected embeddings response shape: {result}") from exc
    return [float(v) for v in vector]
