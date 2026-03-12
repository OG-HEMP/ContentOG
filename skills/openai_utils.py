import json
import os
from typing import Any, Dict, List

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

from skills.http_utils import request_json

load_dotenv()

_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _settings() -> Dict[str, Any]:
    if yaml is None:
        return {}
    try:
        with open("config/settings.yaml", "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def _api_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM reasoning.")
    return key


def chat_completion_json(
    messages: List[Dict[str, str]],
    *,
    model_env_key: str,
    default_model: str,
    timeout_default: int = 60,
) -> Dict[str, Any]:
    settings = _settings()
    llm_settings = settings.get("llm", {}) if isinstance(settings, dict) else {}
    timeout = int(llm_settings.get("timeout", timeout_default))
    retries = int(llm_settings.get("retry_attempts", 3))
    backoff_seconds = float(llm_settings.get("backoff_seconds", 1.0))

    model_name = (os.getenv(model_env_key) or str(llm_settings.get("model_name", default_model))).strip()
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
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc

    try:
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"Unexpected OpenAI chat completion response: {response}") from exc
