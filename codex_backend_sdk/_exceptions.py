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
    def __init__(
        self,
        *,
        message: str = "Connection error.",
        request: requests.PreparedRequest,
    ) -> None:
        super().__init__(message, request, body=None)


class APITimeoutError(APIConnectionError):
    def __init__(self, request: requests.PreparedRequest) -> None:
        super().__init__(message="Request timed out.", request=request)


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
