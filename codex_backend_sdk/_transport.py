"""HTTP transport helpers shared by client resources."""

from __future__ import annotations

import email.utils
import math
import random
import time
from typing import Any, Mapping, Optional

import requests

from ._exceptions import (
    APIConnectionError,
    APITimeoutError,
    status_error_from_response,
)
from ._network import OpenAINetworkPolicyError, reject_redirect_response, validate_agent_sdk_request


_MAX_RETRY_DELAY_SECONDS = 8.0
_MAX_SERVER_RETRY_AFTER_SECONDS = 60.0
_SENSITIVE_REQUEST_HEADERS = ("Authorization", "ChatGPT-Account-ID")
_SENSITIVE_RESPONSE_HEADERS = (
    "Authorization",
    "ChatGPT-Account-ID",
    "Proxy-Authenticate",
    "Set-Cookie",
    "Set-Cookie2",
    "WWW-Authenticate",
)


def request_with_retries(
    session: requests.Session,
    method: str,
    url: str,
    *,
    max_retries: int,
    retry_base_delay: float,
    headers: Mapping[str, str],
    timeout: float,
    params: Optional[Mapping[str, str]] = None,
    json_body: Optional[dict[str, Any]] = None,
    stream: bool = False,
    retry_non_idempotent: bool = False,
    translate_errors: bool = False,
) -> requests.Response:
    validate_agent_sdk_request(method, url)
    request_options: dict[str, Any] = {
        "allow_redirects": False,
        "headers": dict(headers),
        "timeout": timeout,
    }
    if params is not None:
        request_options["params"] = dict(params)
    if json_body is not None:
        request_options["json"] = json_body
    if stream:
        request_options["stream"] = True
    may_retry = method.upper() in {"GET", "HEAD", "OPTIONS"} or retry_non_idempotent
    last_error: requests.RequestException | None = None
    for attempt in range(max_retries + 1):
        try:
            response = session.request(method, url, **request_options)
            _strip_response_request_credentials(response)
            _strip_response_sensitive_headers(response)
            try:
                reject_redirect_response(response)
            except OpenAINetworkPolicyError:
                response.close()
                raise
            if may_retry and should_retry_response(response, attempt, max_retries=max_retries):
                response.close()
                sleep_before_retry(response, attempt, retry_base_delay=retry_base_delay)
                continue
            if response.status_code >= 400:
                if translate_errors:
                    response.content
                    raise status_error_from_response(response)
                response.raise_for_status()
            response._codex_retries_taken = attempt
            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            _strip_exception_request_credentials(exc)
            last_error = exc
            if not may_retry or attempt >= max_retries:
                if translate_errors:
                    request = _exception_request(
                        exc,
                        method=method,
                        url=url,
                        headers=headers,
                        json_body=json_body,
                    )
                    if isinstance(exc, requests.Timeout):
                        raise APITimeoutError(request) from exc
                    raise APIConnectionError(request=request) from exc
                raise
            sleep_before_retry(None, attempt, retry_base_delay=retry_base_delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Request retry loop exhausted")


def _strip_response_request_credentials(response: requests.Response) -> None:
    _strip_request_credentials(getattr(response, "request", None))


def _strip_response_sensitive_headers(response: requests.Response) -> None:
    for name in _SENSITIVE_RESPONSE_HEADERS:
        response.headers.pop(name, None)


def _strip_exception_request_credentials(exc: requests.RequestException) -> None:
    _strip_request_credentials(getattr(exc, "request", None))
    response = getattr(exc, "response", None)
    if response is not None:
        _strip_response_request_credentials(response)
        _strip_response_sensitive_headers(response)


def _strip_request_credentials(request: object) -> None:
    headers = getattr(request, "headers", None)
    if headers is None:
        return
    for name in _SENSITIVE_REQUEST_HEADERS:
        headers.pop(name, None)
    body = getattr(request, "body", None)
    if isinstance(body, str):
        body = body.encode()
    if isinstance(body, bytes):
        # httpx.Request exposes `.content`; retain the same read-only
        # application-body observation on the sanitized Requests object.
        request.content = body


def should_retry_response(
    response: requests.Response,
    attempt: int,
    *,
    max_retries: int,
) -> bool:
    if attempt >= max_retries:
        return False
    explicit = response.headers.get("x-should-retry")
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    return response.status_code in {408, 409, 429} or response.status_code >= 500


def sleep_before_retry(
    response: requests.Response | None,
    attempt: int,
    *,
    retry_base_delay: float,
) -> None:
    retry_after_ms = (
        response.headers.get("Retry-After-Ms") if response is not None else None
    )
    delay = parse_retry_after_ms(retry_after_ms)
    if delay is None:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        delay = parse_retry_after(retry_after)
    if delay is None or not 0 < delay <= _MAX_SERVER_RETRY_AFTER_SECONDS:
        base_delay = min(
            retry_base_delay * (2 ** attempt),
            _MAX_RETRY_DELAY_SECONDS,
        )
        delay = max(0.0, base_delay * (1 - 0.25 * random.random()))
    time.sleep(delay)


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        delay = float(value)
    except ValueError:
        parsed_date = email.utils.parsedate_tz(value)
        if parsed_date is None:
            return None
        delay = float(email.utils.mktime_tz(parsed_date) - time.time())
    return delay if math.isfinite(delay) else None


def parse_retry_after_ms(value: str | None) -> float | None:
    if not value:
        return None
    try:
        delay_ms = float(value)
    except ValueError:
        return None
    if not math.isfinite(delay_ms):
        return None
    return delay_ms / 1000.0


def _exception_request(
    exc: requests.RequestException,
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    json_body: Optional[dict[str, Any]],
) -> requests.PreparedRequest:
    request = getattr(exc, "request", None)
    if request is None:
        request = requests.Request(
            method,
            url,
            headers=dict(headers),
            json=json_body,
        ).prepare()
    _strip_request_credentials(request)
    return request
