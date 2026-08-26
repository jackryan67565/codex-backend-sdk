"""Offline conformance tests against the pinned official Responses client."""

from __future__ import annotations

import inspect
import json
from typing import Any

import httpx
import openai as official_openai
import pytest
import requests
from requests.adapters import BaseAdapter

from codex_backend_sdk import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    CodexBackendUnsupportedParameterError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from codex_backend_sdk._storage import _CredentialStore


_PINNED_OPENAI_VERSION = "2.46.0"
_TERMINAL_RESPONSE = {
    "id": "resp_backend",
    "created_at": 7.0,
    "model": "backend-model",
    "object": "response",
    "output": [],
    "parallel_tool_calls": False,
    "tool_choice": "auto",
    "tools": [],
    "status": "completed",
}


def _sse(*payloads: dict[str, Any]) -> bytes:
    return b"".join(
        b"data: " + json.dumps(payload, separators=(",", ":")).encode() + b"\n\n"
        for payload in payloads
    )


class RecordingAdapter(BaseAdapter):
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[requests.PreparedRequest] = []
        self.wire_headers: list[dict[str, str]] = []

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        self.requests.append(request)
        self.wire_headers.append(dict(request.headers))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            outcome.request = request
            raise outcome
        if callable(outcome):
            outcome = outcome(request)
        outcome.request = request
        outcome.url = request.url
        return outcome

    def close(self) -> None:
        return None


def _http_response(
    status: int = 200,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    response._content = body if body is not None else _sse({
        "type": "response.completed",
        "response": _TERMINAL_RESPONSE,
    })
    response._content_consumed = True
    return response


def _cbs_client(
    outcomes: list[Any],
    *,
    max_retries: int = 0,
) -> tuple[OpenAI, RecordingAdapter]:
    client = OpenAI(max_retries=max_retries, retry_base_delay=0)
    client._CodexClient__credentials = _CredentialStore(
        access_token="synthetic-token",
        account_id="synthetic-account",
    )
    adapter = RecordingAdapter(outcomes)
    client._session.mount("https://", adapter)
    return client, adapter


def _official_body(kwargs: dict[str, Any]) -> dict[str, Any]:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=_TERMINAL_RESPONSE,
        )

    client = official_openai.OpenAI(
        api_key="synthetic",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client.responses.create(**kwargs)
    return json.loads(captured[0].content)


def _official_raw_response() -> tuple[Any, official_openai.OpenAI]:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "x-request-id": "req_official"},
            json=_TERMINAL_RESPONSE,
        )

    client = official_openai.OpenAI(
        api_key="synthetic",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return client.responses.with_raw_response.create(input="Hi"), client


def _official_status_error(status: int, error: dict[str, Any]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            headers={"content-type": "application/json", "x-request-id": "req_error"},
            json={"error": error},
        )

    client = official_openai.OpenAI(
        api_key="synthetic",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        client.responses.create(input="Hi")
    except official_openai.APIStatusError as exc:
        return exc
    finally:
        client.close()
    raise AssertionError("Pinned official client did not raise APIStatusError")


def _official_retry_attempts(max_retries: int) -> int:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                500,
                headers={
                    "content-type": "application/json",
                    "retry-after-ms": "1",
                },
                json={"error": {"message": "retryable"}},
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=_TERMINAL_RESPONSE,
        )

    client = official_openai.OpenAI(
        api_key="synthetic",
        max_retries=max_retries,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        client.responses.create(input="Hi")
    except official_openai.InternalServerError:
        pass
    finally:
        client.close()
    return attempts


def _request_body(request: requests.PreparedRequest) -> dict[str, Any]:
    body = request.body
    if isinstance(body, str):
        body = body.encode()
    assert isinstance(body, bytes)
    return json.loads(body)


def _supported_kwargs(effort: str) -> dict[str, Any]:
    return {
        "model": "model-explicit",
        "instructions": "Preserve the request exactly.",
        "input": [{
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hi"}],
        }],
        "include": ["reasoning.encrypted_content"],
        "tools": [{
            "type": "function",
            "name": "lookup",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
                "additionalProperties": False,
            },
            "strict": True,
        }],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "reasoning": {"effort": effort},
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "result",
                "schema": {
                    "type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        },
    }


def test_differential_baseline_is_pinned_openai_2_46_0():
    assert official_openai.__version__ == _PINNED_OPENAI_VERSION


@pytest.mark.parametrize("effort", ["medium", "low"])
def test_supported_prepared_body_matches_pinned_official_values(effort: str):
    kwargs = _supported_kwargs(effort)
    official_body = _official_body(kwargs)
    client, adapter = _cbs_client([_http_response()])

    client.responses.create(**kwargs)

    cbs_body = _request_body(adapter.requests[0])
    for key in kwargs:
        assert cbs_body[key] == official_body[key]
    assert cbs_body["reasoning"]["effort"] == effort
    assert set(cbs_body) - set(official_body) == {"stream"}
    assert cbs_body["stream"] is True


def test_output_limit_is_explicitly_rejected_instead_of_dropped():
    official_body = _official_body({
        "model": "model-explicit",
        "input": "Hi",
        "max_output_tokens": 64,
    })
    client, adapter = _cbs_client([_http_response()])

    assert official_body["max_output_tokens"] == 64
    with pytest.raises(CodexBackendUnsupportedParameterError, match="max_output_tokens"):
        client.responses.create(
            model="model-explicit",
            input="Hi",
            max_output_tokens=64,
        )
    assert adapter.requests == []


def test_raw_response_exposes_sanitized_request_response_and_request_id():
    body = _sse({"type": "response.completed", "response": _TERMINAL_RESPONSE})
    client, adapter = _cbs_client([_http_response(
        body=body,
        headers={
            "Content-Type": "text/event-stream",
            "X-Request-ID": "req_backend",
            "Set-Cookie": "sensitive-cookie",
        },
    )])

    raw = client.responses.with_raw_response.create(
        model="model-explicit",
        input="Hi",
        reasoning={"effort": "low"},
        store=False,
    )

    assert raw.status_code == 200
    assert raw.request_id == "req_backend"
    assert raw.retries_taken == 0
    assert raw.method == "POST"
    assert str(raw.url) == "https://chatgpt.com/backend-api/codex/responses"
    assert raw.content == body
    assert raw.text == body.decode()
    assert raw.http_request is adapter.requests[0]
    assert raw.http_request.content == raw.http_request.body
    assert _request_body(raw.http_request)["reasoning"] == {"effort": "low"}
    assert "Authorization" not in raw.http_request.headers
    assert "ChatGPT-Account-ID" not in raw.http_request.headers
    assert raw.http_request.headers["originator"] == "codex_backend_sdk"
    assert "Set-Cookie" not in raw.headers

    parsed = raw.parse()

    assert parsed.id == "resp_backend"
    assert parsed._request_id == "req_backend"
    assert parsed.model == "backend-model"

    official_raw, official_client = _official_raw_response()
    try:
        expected_surface = {
            "content",
            "headers",
            "http_request",
            "method",
            "parse",
            "request_id",
            "retries_taken",
            "status_code",
            "text",
            "url",
        }
        assert type(raw).__name__ == type(official_raw).__name__
        assert all(hasattr(raw, name) for name in expected_surface)
        assert all(hasattr(official_raw, name) for name in expected_surface)
    finally:
        official_client.close()


def test_raw_response_create_keeps_the_create_signature():
    client, _ = _cbs_client([_http_response()])

    assert inspect.signature(client.responses.with_raw_response.create) == inspect.signature(
        client.responses.create
    )


def test_sparse_terminal_response_does_not_echo_or_invent_request_facts():
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "response.completed",
        "response": {"id": "resp_sparse"},
    }))])

    response = client.responses.create(
        model="model-requested",
        instructions="requested instructions",
        input="Hi",
        reasoning={"effort": "medium"},
        text={"format": {"type": "text"}},
    )

    assert response.model_fields_set == {"id"}
    assert response.id == "resp_sparse"
    assert response.model is None
    assert response.created_at is None
    assert response.completed_at is None
    assert response.instructions is None
    assert response.output is None
    assert response.parallel_tool_calls is None
    assert response.reasoning is None
    assert response.status is None
    assert response.text is None
    assert response.usage is None


def test_partial_usage_remains_partial():
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "response.completed",
        "response": {
            **_TERMINAL_RESPONSE,
            "usage": {"input_tokens": 3},
        },
    }))])

    response = client.responses.create(input="Hi")

    assert response.usage is not None
    assert response.usage.model_fields_set == {"input_tokens"}
    assert response.usage.input_tokens == 3
    assert response.usage.output_tokens is None
    assert response.usage.total_tokens is None
    assert response.usage.input_tokens_details is None


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, UnprocessableEntityError),
        (429, RateLimitError),
        (500, InternalServerError),
    ],
)
def test_status_errors_preserve_official_categories_and_safe_material(
    status: int,
    error_type: type[APIStatusError],
):
    error = {
        "message": "backend rejected input",
        "type": "invalid_request_error",
        "param": "input",
        "code": "rejected",
    }
    official_error = _official_status_error(status, error)
    client, adapter = _cbs_client([_http_response(
        status,
        body=json.dumps({"error": error}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": "req_error",
            "Set-Cookie": "sensitive-cookie",
        },
    )])

    with pytest.raises(error_type) as caught:
        client.responses.create(model="model-explicit", input="Hi")

    exc = caught.value
    assert type(exc).__name__ == type(official_error).__name__
    assert exc.status_code == status
    assert exc.status_code == official_error.status_code
    assert exc.request_id == "req_error"
    assert exc.request_id == official_error.request_id
    assert exc.body == error
    assert exc.body == official_error.body
    assert exc.code == "rejected"
    assert exc.param == "input"
    assert exc.type == "invalid_request_error"
    assert _request_body(exc.request)["model"] == "model-explicit"
    assert exc.request.content == exc.request.body
    assert "Authorization" not in exc.request.headers
    assert "ChatGPT-Account-ID" not in exc.request.headers
    assert "Set-Cookie" not in exc.response.headers
    assert len(adapter.requests) == 1


@pytest.mark.parametrize(
    ("transport_error", "error_type"),
    [
        (requests.Timeout("synthetic timeout"), APITimeoutError),
        (requests.ConnectionError("synthetic connection failure"), APIConnectionError),
    ],
)
def test_transport_errors_use_official_categories(
    transport_error: requests.RequestException,
    error_type: type[APIConnectionError],
):
    client, adapter = _cbs_client([transport_error])

    with pytest.raises(error_type) as caught:
        client.responses.create(model="model-explicit", input="Hi")

    assert _request_body(caught.value.request)["model"] == "model-explicit"
    assert "Authorization" not in caught.value.request.headers
    assert "ChatGPT-Account-ID" not in caught.value.request.headers
    assert len(adapter.requests) == 1


def test_max_retries_zero_makes_exactly_one_response_attempt():
    client, adapter = _cbs_client([
        _http_response(500, body=b'{"error":{"message":"retryable"}}'),
        _http_response(),
    ], max_retries=0)

    with pytest.raises(InternalServerError):
        client.responses.create(input="Hi")

    assert _official_retry_attempts(0) == 1
    assert len(adapter.requests) == 1


def test_configured_response_retry_policy_is_not_globally_disabled():
    client, adapter = _cbs_client([
        _http_response(500, body=b'{"error":{"message":"retryable"}}'),
        _http_response(),
    ], max_retries=1)

    response = client.responses.create(input="Hi")

    assert response.id == "resp_backend"
    assert _official_retry_attempts(1) == 2
    assert len(adapter.requests) == 2


def test_catalog_omission_does_not_preflight_reject_response_model():
    client, adapter = _cbs_client([_http_response()])

    response = client.responses.create(model="not-in-local-catalog", input="Hi")

    assert response.id == "resp_backend"
    assert _request_body(adapter.requests[0])["model"] == "not-in-local-catalog"


def test_streaming_events_preserve_backend_payloads_in_order():
    payloads = [
        {
            "type": "response.output_text.delta",
            "sequence_number": 1,
            "delta": "hi",
            "custom_backend_field": {"observed": True},
        },
        {
            "type": "response.completed",
            "sequence_number": 2,
            "response": _TERMINAL_RESPONSE,
        },
    ]
    client, _ = _cbs_client([_http_response(body=_sse(*payloads))])

    events = list(client.responses.create(input="Hi", stream=True))

    assert [event.model_dump(exclude_unset=True) for event in events] == payloads


def test_failed_terminal_event_returns_backend_response_instead_of_runtime_error():
    failed = {
        **_TERMINAL_RESPONSE,
        "status": "failed",
        "error": {"code": "model_error", "message": "generation failed"},
    }
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "response.failed",
        "response": failed,
    }))])

    response = client.responses.create(input="Hi")

    assert response.status == "failed"
    assert response.error == failed["error"]


def test_stream_without_terminal_event_fails_explicitly():
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "response.output_text.delta",
        "delta": "partial",
    }))])

    with pytest.raises(APIConnectionError, match="terminal response event"):
        client.responses.create(input="Hi")


def test_malformed_sse_fails_as_response_validation_error():
    response = _http_response(body=b"data: {not-json}\n\n")
    closed: list[bool] = []
    response.close = lambda: closed.append(True)
    client, _ = _cbs_client([response])

    with pytest.raises(APIResponseValidationError, match="invalid SSE event"):
        client.responses.create(input="Hi")

    assert closed == [True]


def test_terminal_event_without_response_fails_validation():
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "response.completed",
    }))])

    with pytest.raises(APIResponseValidationError, match="Response object"):
        client.responses.create(input="Hi")


def test_error_event_preserves_event_error_body():
    event_error = {
        "message": "stream failed",
        "type": "server_error",
        "code": "stream_error",
    }
    client, _ = _cbs_client([_http_response(body=_sse({
        "type": "error",
        "error": event_error,
    }))])

    with pytest.raises(APIError) as caught:
        client.responses.create(input="Hi")

    assert caught.value.body == event_error
    assert caught.value.code == "stream_error"
