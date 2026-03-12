import json
import logging
from typing import Any, Dict, List, Optional

from config.config import settings
from skills.http_utils import request_json

logger = logging.getLogger(__name__)

_CHAT_URL = "https://api.openai.com/v1/chat/completions"


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
    
    try:
        response = request_json(
            _CHAT_URL,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc

    try:
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"Unexpected OpenAI chat completion response: {response}") from exc
