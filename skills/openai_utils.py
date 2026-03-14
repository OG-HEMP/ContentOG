import json
import logging
from typing import Any, Dict, List, Optional

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)

_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def load_lm_studio_model(model_id: str) -> Dict[str, Any]:
    """Manually trigger model loading in LM Studio if required."""
    base_url = settings.lm_studio_base_url.rstrip("/")
    # Remove /v1 if present for the loading endpoint which often sits at /api/v1 or just /
    api_dir = "/api/v1" if "/v1" in base_url else ""
    load_url = f"{base_url.split('/v1')[0]}{api_dir}/models/load"
    
    logger.info(f"Attempting to load LM Studio model: {model_id} via {load_url}")
    return request_json(
        load_url,
        method="POST",
        payload={"model": model_id},
        timeout=120
    )

def chat_completion_json(
    messages: List[Dict[str, str]],
    *,
    model_env_key: str = "OPENAI_STRATEGY_MODEL",
    default_model: str = "gpt-4o-mini",
    timeout_default: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a chat completion request with specialized JSON output routing."""
    
    # Use centralized settings
    timeout = timeout_default or settings.llm_timeout
    retries = settings.llm_retry_attempts
    backoff = settings.llm_backoff_seconds
    model_name = settings.openai_strategy_model

    payload = {
        "model": model_name,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    
    provider = settings.llm_provider.lower()
    
    if provider == "lm_studio":
        # LM Studio base URL should usually end with /v1
        base_url = settings.lm_studio_base_url.rstrip("/")
        api_url = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
    else:
        api_url = _CHAT_URL
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

    try:
        response = request_json(
            api_url,
            method="POST",
            headers=headers,
            payload=payload,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff,
        )
    except Exception as exc:
        raise RuntimeError(f"{provider.upper()} chat completion failed at {api_url}: {exc}") from exc

    try:
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"Unexpected {provider.upper()} response structure: {response}") from exc
