"""Fail-closed network policy for SDK-owned outbound connections."""

from __future__ import annotations

from urllib.parse import urlsplit


OPENAI_DOMAIN_SUFFIXES = (
    "chatgpt.com",
    "openai.com",
    "oaiusercontent.com",
    "oaistatic.com",
)


class OpenAINetworkPolicyError(ValueError):
    """Raised when SDK code is asked to contact a non-OpenAI destination."""


def validate_openai_url(url: str, *, allowed_schemes: tuple[str, ...] = ("https",)) -> str:
    """Return *url* only when it targets an approved OpenAI-operated domain."""
    if not isinstance(url, str) or not url:
        raise OpenAINetworkPolicyError("OpenAI destination URL must be a non-empty string")

    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme.lower() not in allowed_schemes:
        raise OpenAINetworkPolicyError(
            f"OpenAI destination must use {', '.join(allowed_schemes)}: {url!r}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise OpenAINetworkPolicyError("OpenAI destination URL must not contain user information")
    try:
        port = parsed.port
    except ValueError as exc:
        raise OpenAINetworkPolicyError(f"OpenAI destination has an invalid port: {url!r}") from exc
    if port not in (None, 443):
        raise OpenAINetworkPolicyError(f"OpenAI destination must use port 443: {url!r}")
    if not any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in OPENAI_DOMAIN_SUFFIXES
    ):
        raise OpenAINetworkPolicyError(f"Refusing non-OpenAI network destination: {url!r}")
    return url


def reject_redirect_response(response: object) -> None:
    """Reject redirects even though Requests does not treat 3xx as an error."""
    status_code = getattr(response, "status_code", 0)
    if 300 <= status_code < 400:
        headers = getattr(response, "headers", {}) or {}
        location = headers.get("Location", "<unspecified>")
        raise OpenAINetworkPolicyError(f"Refusing HTTP redirect to {location!r}")
