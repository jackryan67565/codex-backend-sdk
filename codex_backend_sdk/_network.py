"""Fail-closed network policy for SDK-owned outbound connections."""

from __future__ import annotations

from urllib.parse import urlsplit


# The agent-safe SDK intentionally supports only the stateless Codex Responses
# and model-catalog routes. Host validation alone is not sufficient: a bearer
# accepted by chatgpt.com can authorize unrelated account and workspace APIs.
AGENT_SAFE_REQUESTS = frozenset({
    ("GET", "chatgpt.com", "/backend-api/codex/models"),
    ("POST", "chatgpt.com", "/backend-api/codex/responses"),
    ("POST", "chatgpt.com", "/backend-api/codex/responses/compact"),
})


class OpenAINetworkPolicyError(ValueError):
    """Raised when a request falls outside the exact agent-safe route policy."""


def validate_agent_sdk_request(method: str, url: str) -> str:
    """Allow only exact HTTPS method and route pairs in the agent SDK."""
    if not isinstance(url, str) or not url:
        raise OpenAINetworkPolicyError("Agent-safe destination URL must be a non-empty string")

    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme.lower() != "https":
        raise OpenAINetworkPolicyError(f"Agent-safe destination must use HTTPS: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise OpenAINetworkPolicyError("Agent-safe destination URL must not contain user information")
    if parsed.fragment:
        raise OpenAINetworkPolicyError("Agent-safe destination URL must not contain a fragment")
    if parsed.query:
        raise OpenAINetworkPolicyError("Agent-safe destination URL must not contain a query")
    try:
        port = parsed.port
    except ValueError as exc:
        raise OpenAINetworkPolicyError(f"Agent-safe destination has an invalid port: {url!r}") from exc
    if port not in (None, 443):
        raise OpenAINetworkPolicyError(f"Agent-safe destination must use port 443: {url!r}")
    request = (
        method.upper(),
        hostname,
        parsed.path,
    )
    if request not in AGENT_SAFE_REQUESTS:
        raise OpenAINetworkPolicyError(
            f"Refusing route outside the agent-safe SDK surface: {request[0]} {url!r}"
        )
    return url


def reject_redirect_response(response: object) -> None:
    """Reject redirects even though Requests does not treat 3xx as an error."""
    status_code = getattr(response, "status_code", 0)
    if 300 <= status_code < 400:
        headers = getattr(response, "headers", {}) or {}
        location = headers.get("Location", "<unspecified>")
        raise OpenAINetworkPolicyError(f"Refusing HTTP redirect to {location!r}")
