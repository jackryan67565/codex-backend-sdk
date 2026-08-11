"""HTTP transport helpers shared by client resources."""

from __future__ import annotations

import math
import time
from typing import Any

import requests

from ._network import reject_redirect_response, validate_agent_sdk_request


_MAX_RETRY_DELAY_SECONDS = 60.0
_SENSITIVE_REQUEST_HEADERS = ("Authorization", "ChatGPT-Account-ID")


def request_with_retries(
    session: requests.Session,
    method: str,
    url: str,
    *,
    max_retries: int,
    retry_base_delay: float,
    **kwargs: Any,
) -> requests.Response:
    validate_agent_sdk_request(method, url)
    kwargs["allow_redirects"] = False
    may_retry = method.upper() in {"GET", "HEAD", "OPTIONS"}
    last_error: requests.RequestException | None = None
    for attempt in range(max_retries + 1):
        try:
            response = session.request(method, url, **kwargs)
            _strip_response_request_credentials(response)
            reject_redirect_response(response)
            if may_retry and should_retry_response(response, attempt, max_retries=max_retries):
                sleep_before_retry(response, attempt, retry_base_delay=retry_base_delay)
                continue
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            _strip_exception_request_credentials(exc)
            last_error = exc
            if not may_retry or attempt >= max_retries:
                raise
            sleep_before_retry(None, attempt, retry_base_delay=retry_base_delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Request retry loop exhausted")


def _strip_response_request_credentials(response: requests.Response) -> None:
    _strip_request_credentials(getattr(response, "request", None))


def _strip_exception_request_credentials(exc: requests.RequestException) -> None:
    _strip_request_credentials(getattr(exc, "request", None))
    response = getattr(exc, "response", None)
    if response is not None:
        _strip_response_request_credentials(response)


def _strip_request_credentials(request: object) -> None:
    headers = getattr(request, "headers", None)
    if headers is None:
        return
    for name in _SENSITIVE_REQUEST_HEADERS:
        headers.pop(name, None)


def should_retry_response(
    response: requests.Response,
    attempt: int,
    *,
    max_retries: int,
) -> bool:
    if attempt >= max_retries:
        return False
    return response.status_code == 429 or 500 <= response.status_code < 600


def sleep_before_retry(
    response: requests.Response | None,
    attempt: int,
    *,
    retry_base_delay: float,
) -> None:
    retry_after = response.headers.get("Retry-After") if response is not None else None
    delay = parse_retry_after(retry_after)
    if delay is None:
        delay = min(
            retry_base_delay * (2 ** attempt),
            _MAX_RETRY_DELAY_SECONDS,
        )
    time.sleep(delay)


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        delay = float(value)
    except ValueError:
        return None
    if not math.isfinite(delay):
        return None
    return min(max(0.0, delay), _MAX_RETRY_DELAY_SECONDS)
