"""Minimal, read-only access to the shared Codex credential cache.

The agent-safe SDK retains only the access token and ChatGPT account identifier
needed to call Codex Responses. It never loads refresh tokens or API keys into
its credential object and never writes the shared authentication file.
"""

from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import Any

_MAX_AUTH_FILE_BYTES = 1024 * 1024


def _codex_home() -> Path:
    if value := os.environ.get("CODEX_HOME"):
        return Path(value)
    return Path.home() / ".codex"


def _auth_path() -> Path:
    return _codex_home() / "auth.json"


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except Exception:
        return {}
    return decoded if isinstance(decoded, dict) else {}


class _CredentialStore:
    """The minimum credential material required by the Codex backend."""

    __slots__ = ("_access_token", "account_id")

    def __init__(self, *, access_token: str, account_id: str) -> None:
        self._access_token = access_token
        self.account_id = account_id

    def __repr__(self) -> str:
        return "_CredentialStore(<redacted>)"


def _load_credentials() -> _CredentialStore | None:
    """Load minimal credentials without following links or retaining other secrets."""
    path = _auth_path()
    try:
        if path.is_symlink():
            raise RuntimeError(f"Refusing linked Codex credential file: {path}")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError(f"Unable to open Codex credential file: {path}") from exc

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(f"Codex credential path is not a regular file: {path}")
        if metadata.st_size > _MAX_AUTH_FILE_BYTES:
            raise RuntimeError(f"Codex credential file is unexpectedly large: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            data = json.load(handle)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to parse Codex credential file: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    tokens = data.get("tokens") if isinstance(data, dict) else None
    if not isinstance(tokens, dict):
        return None
    access_token = tokens.get("access_token")
    account_id = tokens.get("account_id")
    # Drop references to refresh tokens, API keys, ID tokens, and other cache
    # fields as soon as the two required values have been copied.
    tokens.clear()
    if isinstance(data, dict):
        data.clear()
    if not isinstance(access_token, str) or not access_token:
        return None
    if not isinstance(account_id, str) or not account_id:
        return None
    return _CredentialStore(access_token=access_token, account_id=account_id)


def _access_token_needs_refresh(store: _CredentialStore, *, margin_seconds: int = 300) -> bool:
    """Reject expired or nearly expired credentials instead of refreshing in-agent."""
    import time

    expires_at = _decode_jwt_payload(store._access_token).get("exp")
    return isinstance(expires_at, (int, float)) and expires_at <= time.time() + margin_seconds
