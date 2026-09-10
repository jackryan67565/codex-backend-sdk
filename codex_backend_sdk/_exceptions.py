"""OpenAI-compatible errors for the supported CBS transport path."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

import requests


class OpenAIError(Exception):
    """Base error matching the official SDK's public taxonomy."""


class APIError(OpenAIError):
    message: str
    request: requests.PreparedRequest
    body: object | None
    code: Optional[str]
    param: Optional[str]
    type: Optional[str]

    def __init__(
        self,
        message: str,
        request: requests.PreparedRequest,
        *,
        body: object | None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request = request
        self.body = body
        if isinstance(body, Mapping):
            self.code = _optional_string(body.get("code"))
            self.param = _optional_string(body.get("param"))
            self.type = _optional_string(body.get("type"))
        else:
            self.code = None
            self.param = None
            self.type = None


class APIResponseValidationError(APIError):
    response: requests.Response
    status_code: int

    def __init__(
        self,
        response: requests.Response,
        body: object | None,
        *,
        message: str | None = None,
    ) -> None:
        request = _response_request(response)
        super().__init__(
            message or "Data returned by API invalid for expected schema.",
            request,
            body=body,
        )
        self.response = response
        self.status_code = response.status_code


class APIStatusError(APIError):
    response: requests.Response
    status_code: int
    request_id: str | None

    def __init__(
        self,
        message: str,
        *,
        response: requests.Response,
        body: object | None,
    ) -> None:
        super().__init__(message, _response_request(response), body=body)
        self.response = response
        self.status_code = response.status_code
        self.request_id = response.headers.get("x-request-id")


class APIConnectionError(APIError):
    status_code: int | None
    request_id: str | None
    response_headers: Mapping[str, str] | None
    partial_response_body: bytes | None
    response_body_complete: bool | None
    retries_taken: int | None

    def __init__(
        self,
        *,
        message: str = "Connection error.",
        request: requests.PreparedRequest,
        status_code: int | None = None,
        request_id: str | None = None,
        response_headers: Mapping[str, str] | None = None,
        partial_response_body: bytes | None = None,
        response_body_complete: bool | None = None,
        retries_taken: int | None = None,
    ) -> None:
        super().__init__(message, request, body=None)
        self.status_code = status_code
        self.request_id = request_id
        self.response_headers = (
            requests.structures.CaseInsensitiveDict(response_headers)
            if response_headers is not None
            else None
        )
        self.partial_response_body = partial_response_body
        self.response_body_complete = response_body_complete
        self.retries_taken = retries_taken


class APITimeoutError(APIConnectionError):
    def __init__(self, request: requests.PreparedRequest, **kwargs: Any) -> None:
        super().__init__(message="Request timed out.", request=request, **kwargs)


class BadRequestError(APIStatusError):
    pass


class AuthenticationError(APIStatusError):
    pass


class PermissionDeniedError(APIStatusError):
    pass


class NotFoundError(APIStatusError):
    pass


class ConflictError(APIStatusError):
    pass


class UnprocessableEntityError(APIStatusError):
    pass


class RateLimitError(APIStatusError):
    pass


class InternalServerError(APIStatusError):
    pass


def status_error_from_response(response: requests.Response) -> APIStatusError:
    raw_body: object
    try:
        raw_body = response.json()
    except (requests.JSONDecodeError, ValueError):
        raw_body = response.text

    body = raw_body.get("error", raw_body) if isinstance(raw_body, Mapping) else raw_body
    message = f"Error code: {response.status_code}"
    if raw_body not in (None, "", {}):
        message = f"{message} - {raw_body}"

    error_type: type[APIStatusError]
    if response.status_code == 400:
        error_type = BadRequestError
    elif response.status_code == 401:
        error_type = AuthenticationError
    elif response.status_code == 403:
        error_type = PermissionDeniedError
    elif response.status_code == 404:
        error_type = NotFoundError
    elif response.status_code == 409:
        error_type = ConflictError
    elif response.status_code == 422:
        error_type = UnprocessableEntityError
    elif response.status_code == 429:
        error_type = RateLimitError
    elif response.status_code >= 500:
        error_type = InternalServerError
    else:
        error_type = APIStatusError
    return error_type(message, response=response, body=body)


def _response_request(response: requests.Response) -> requests.PreparedRequest:
    request = response.request
    if request is None:
        request = requests.Request(
            "POST",
            response.url
            or "https://chatgpt.com/backend-api/codex/responses",
        ).prepare()
    return request


def _optional_string(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None
