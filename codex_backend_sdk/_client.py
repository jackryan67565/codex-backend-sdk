"""Agent-safe transport client and public entrypoint."""

from __future__ import annotations

from typing import Any, Optional

import requests

from ._transport import request_with_retries
from ._utils import _UNSET, _is_given
from ._storage import _CredentialStore, _access_token_needs_refresh, _load_credentials

BASE_URL = "https://chatgpt.com/backend-api/codex"
ORIGINATOR = "codex_cli_rs"
RESPONSES_ORIGINATOR = "codex_backend_sdk"
_MAX_TIMEOUT_SECONDS = 600.0
_MAX_MODEL_RETRIES = 5
_MAX_RETRY_DELAY_SECONDS = 60.0


class CodexClient:
    """Narrow client for stateless Codex Responses and model discovery.

    Authentication is read-only: this client reuses a current Codex login but
    does not start login flows, refresh tokens, derive API keys, or write the
    shared credential cache. Run the trusted Codex CLI or desktop app when the
    cached access token needs renewal.
    """

    __slots__ = (
        "__credentials",
        "_timeout",
        "_max_retries",
        "_retry_base_delay",
        "_session",
        "_defaults",
        "responses",
        "models",
    )

    def __init__(
        self,
        *,
        model: str = "gpt-5.4",
        instructions: Optional[str] = None,
        timeout: float = 120,
        max_retries: int = 2,
        retry_base_delay: float = 0.25,
    ) -> None:
        from .resources.models import Models
        from .resources.responses import Responses

        self.__credentials: _CredentialStore | None = None
        self._timeout = _validated_timeout(timeout)
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise TypeError("max_retries must be an integer")
        if not 0 <= max_retries <= _MAX_MODEL_RETRIES:
            raise ValueError(f"max_retries must be between 0 and {_MAX_MODEL_RETRIES}")
        self._max_retries = max_retries
        if isinstance(retry_base_delay, bool) or not isinstance(retry_base_delay, (int, float)):
            raise TypeError("retry_base_delay must be a number")
        if not 0 <= retry_base_delay <= _MAX_RETRY_DELAY_SECONDS:
            raise ValueError(
                f"retry_base_delay must be between 0 and {_MAX_RETRY_DELAY_SECONDS:g} seconds"
            )
        self._retry_base_delay = float(retry_base_delay)
        self._session = requests.Session()
        self._session.trust_env = False
        self._defaults = {"model": model, "instructions": instructions}
        self.responses = Responses(self)
        self.models = Models(self)

    def authenticate(self) -> "CodexClient":
        """Reuse a current Codex login without performing interactive auth or refresh."""
        credentials = _load_credentials()
        if credentials is None:
            raise RuntimeError(
                "No usable stored Codex credentials. Sign in with the trusted Codex CLI "
                "or ChatGPT desktop app, then try again."
            )
        if _access_token_needs_refresh(credentials):
            raise RuntimeError(
                "Stored Codex access token is expired or near expiry. Refresh it with "
                "the trusted Codex CLI or ChatGPT desktop app, then try again."
            )
        self.__credentials = credentials
        return self

    @property
    def authenticated(self) -> bool:
        return self.__credentials is not None

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "CodexClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _request_models(
        self,
        *,
        client_version: str,
        timeout: Any = _UNSET,
    ) -> requests.Response:
        credentials = self.__credentials
        if credentials is None:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return request_with_retries(
            self._session,
            "GET",
            f"{BASE_URL}/models",
            params={"client_version": client_version},
            headers={
                "Authorization": f"Bearer {credentials._access_token}",
                "ChatGPT-Account-ID": credentials.account_id,
                "originator": ORIGINATOR,
            },
            timeout=self._resolve_timeout(timeout),
            max_retries=self._max_retries,
            retry_base_delay=self._retry_base_delay,
        )

    def _request_response(
        self,
        *,
        body: dict[str, Any],
        stream: bool = False,
        timeout: Any = _UNSET,
    ) -> requests.Response:
        credentials = self.__credentials
        if credentials is None:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        headers = {
            "Authorization": f"Bearer {credentials._access_token}",
            "ChatGPT-Account-ID": credentials.account_id,
            "originator": RESPONSES_ORIGINATOR,
        }
        if stream:
            headers["Accept"] = "text/event-stream"
        return request_with_retries(
            self._session,
            "POST",
            f"{BASE_URL}/responses",
            json_body=body,
            headers=headers,
            stream=stream,
            timeout=self._resolve_timeout(timeout),
            max_retries=self._max_retries,
            retry_base_delay=self._retry_base_delay,
        )

    def _request_compaction(
        self,
        *,
        body: dict[str, Any],
        timeout: Any = _UNSET,
    ) -> requests.Response:
        credentials = self.__credentials
        if credentials is None:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return request_with_retries(
            self._session,
            "POST",
            f"{BASE_URL}/responses/compact",
            json_body=body,
            headers={
                "Authorization": f"Bearer {credentials._access_token}",
                "ChatGPT-Account-ID": credentials.account_id,
                "originator": RESPONSES_ORIGINATOR,
            },
            timeout=self._resolve_timeout(timeout),
            max_retries=self._max_retries,
            retry_base_delay=self._retry_base_delay,
        )

    def _resolve_timeout(self, value: Any) -> float:
        return self._timeout if not _is_given(value) else _validated_timeout(value)


OpenAI = CodexClient


def _validated_timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("timeout must be a number")
    timeout = float(value)
    if not 0 < timeout <= _MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout must be greater than 0 and at most {_MAX_TIMEOUT_SECONDS:g} seconds")
    return timeout
