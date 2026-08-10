"""Models resource."""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from .._models import Model, SyncPage
from .._utils import _UNSET

if TYPE_CHECKING:
    from .._client import CodexClient

# This is the upstream Codex CLI protocol/client version expected by the
# ChatGPT backend, not the PyPI package version.
CLIENT_VERSION = "0.130.0"
_CACHE_TTL = 300


class Models:
    def __init__(self, client: CodexClient) -> None:
        self._client = client
        self._cache: SyncPage | None = None
        self._cache_fetched_at = 0.0

    def list(
        self,
        *,
        force_refresh: bool = False,
        timeout: Any = _UNSET,
    ) -> SyncPage:
        if not force_refresh and self._cache is not None:
            if time.time() - self._cache_fetched_at <= _CACHE_TTL:
                return self._cache

        response = self._client._request_models(
            client_version=CLIENT_VERSION,
            timeout=timeout,
        )
        data = response.json()
        models = [_model_from_backend(item) for item in data.get("models", [])]
        models.sort(key=lambda model: getattr(model, "priority", 0))
        page = SyncPage(data=models, etag=response.headers.get("ETag"))
        self._cache = page
        self._cache_fetched_at = time.time()
        return page

    def retrieve(
        self,
        model: str,
        *,
        timeout: Any = _UNSET,
    ) -> Model:
        if not model:
            raise ValueError(f"Expected a non-empty value for `model` but received {model!r}")
        for candidate in self.list(timeout=timeout):
            if candidate.id == model:
                return candidate
        raise LookupError(f"Model not found: {model}")


def _model_from_backend(raw: dict[str, Any]) -> Model:
    return Model(
        id=raw.get("slug", ""),
        created=0,
        owned_by="openai",
        display_name=raw.get("display_name", raw.get("slug", "")),
        description=raw.get("description", ""),
        context_window=raw.get("context_window"),
        supported_in_api=raw.get("supported_in_api", False),
        priority=raw.get("priority", 0),
        supports_reasoning_summaries=raw.get("supports_reasoning_summaries", False),
        support_verbosity=raw.get("support_verbosity", False),
        default_verbosity=raw.get("default_verbosity"),
        default_reasoning_level=raw.get("default_reasoning_level"),
        supported_reasoning_levels=raw.get("supported_reasoning_levels", []),
        auto_compact_token_limit=raw.get("auto_compact_token_limit"),
        input_modalities=raw.get("input_modalities", []),
    )
