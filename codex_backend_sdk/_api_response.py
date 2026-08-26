"""Official-compatible raw response wrapper for the supported Responses path."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast

import requests


ResponseT = TypeVar("ResponseT")
_NOT_PARSED = object()


class LegacyAPIResponse(Generic[ResponseT]):
    """Narrow equivalent of openai-python 2.46.0's raw response object."""

    def __init__(
        self,
        *,
        raw: requests.Response,
        parser: Callable[[], ResponseT],
        retries_taken: int = 0,
    ) -> None:
        self.http_response = raw
        self.retries_taken = retries_taken
        self._parser = parser
        self._parsed: object = _NOT_PARSED
        self._closed = False

    @property
    def request_id(self) -> str | None:
        return getattr(self.http_response, "headers", {}).get("x-request-id")

    def parse(self) -> ResponseT:
        if self._parsed is _NOT_PARSED:
            parsed = self._parser()
            if hasattr(parsed, "_request_id"):
                parsed._request_id = self.request_id
            self._parsed = parsed
        return cast(ResponseT, self._parsed)

    @property
    def headers(self) -> requests.structures.CaseInsensitiveDict[str]:
        return self.http_response.headers

    @property
    def http_request(self) -> requests.PreparedRequest:
        request = self.http_response.request
        if request is None:
            raise RuntimeError("Raw response has no associated HTTP request.")
        return request

    @property
    def status_code(self) -> int:
        return self.http_response.status_code

    @property
    def url(self) -> str:
        return self.http_response.url

    @property
    def method(self) -> str:
        return self.http_request.method

    @property
    def content(self) -> bytes:
        return self.http_response.content

    @property
    def text(self) -> str:
        return self.http_response.text

    @property
    def http_version(self) -> str:
        version = getattr(getattr(self.http_response, "raw", None), "version", None)
        return {10: "HTTP/1.0", 11: "HTTP/1.1", 20: "HTTP/2"}.get(
            version,
            "HTTP/1.1",
        )

    @property
    def is_closed(self) -> bool:
        raw = getattr(self.http_response, "raw", None)
        return self._closed or bool(getattr(raw, "closed", False))

    @property
    def elapsed(self) -> datetime.timedelta:
        return self.http_response.elapsed

    def read(self) -> bytes:
        return self.content

    def close(self) -> None:
        self.http_response.close()
        self._closed = True

    def __enter__(self) -> "LegacyAPIResponse[ResponseT]":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<LegacyAPIResponse [{self.status_code}]>"


APIResponse = LegacyAPIResponse
