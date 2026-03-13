import json
import time
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_MAX_ERROR_BODY_CHARS = 400
_MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # 2MB limit


def _clip_error_text(text: str) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= _MAX_ERROR_BODY_CHARS:
        return normalized
    return normalized[:_MAX_ERROR_BODY_CHARS] + "...(truncated)"


def _should_retry(status_code: Optional[int], attempt: int, retries: int) -> bool:
    if attempt >= retries:
        return False
    if status_code is None:
        return True
    if status_code == 429:
        return True
    return 500 <= status_code < 600


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Dict[str, Any]:
    request_headers = headers or {}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        if "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"

    last_error: Optional[Tuple[Optional[int], str]] = None
    for attempt in range(retries + 1):
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read(_MAX_RESPONSE_SIZE + 1)
                if len(content) > _MAX_RESPONSE_SIZE:
                    raise RuntimeError(f"Response exceeds maximum allowed size of {_MAX_RESPONSE_SIZE} bytes")
                return json.loads(content.decode("utf-8"))
        except HTTPError as exc:
            error_body = _clip_error_text(exc.read().decode("utf-8", errors="ignore"))
            last_error = (exc.code, f"{exc.code} {error_body}".strip())
            if _should_retry(exc.code, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break
        except URLError as exc:
            last_error = (None, str(exc))
            if _should_retry(None, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break
        except Exception as exc:  # pragma: no cover
            last_error = (None, str(exc))
            if _should_retry(None, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break

    code, message = last_error or (None, "Unknown request failure")
    if code is None:
        raise RuntimeError(message)
    raise RuntimeError(f"{code} {message}".strip())


def request_text(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> str:
    request_headers = headers or {}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        if "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"

    last_error: Optional[Tuple[Optional[int], str]] = None
    for attempt in range(retries + 1):
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read(_MAX_RESPONSE_SIZE + 1)
                if len(content) > _MAX_RESPONSE_SIZE:
                    raise RuntimeError(f"Response exceeds maximum allowed size of {_MAX_RESPONSE_SIZE} bytes")
                return content.decode("utf-8", errors="ignore")
        except HTTPError as exc:
            error_body = _clip_error_text(exc.read().decode("utf-8", errors="ignore"))
            last_error = (exc.code, f"{exc.code} {error_body}".strip())
            if _should_retry(exc.code, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break
        except URLError as exc:
            last_error = (None, str(exc))
            if _should_retry(None, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break
        except Exception as exc:  # pragma: no cover
            last_error = (None, str(exc))
            if _should_retry(None, attempt, retries):
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            break

    code, message = last_error or (None, "Unknown request failure")
    if code is None:
        raise RuntimeError(message)
    raise RuntimeError(f"{code} {message}".strip())
