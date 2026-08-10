import pytest

from codex_backend_sdk import OpenAINetworkPolicyError
from codex_backend_sdk._network import (
    reject_redirect_response,
    validate_agent_sdk_request,
)


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "https://chatgpt.com/backend-api/codex/models"),
        ("POST", "https://chatgpt.com/backend-api/codex/responses"),
        ("POST", "https://chatgpt.com/backend-api/codex/responses/compact"),
    ],
)
def test_agent_request_policy_accepts_only_core_routes(method, url):
    assert validate_agent_sdk_request(method, url) == url


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "http://chatgpt.com/backend-api/codex/models"),
        ("GET", "https://attacker.example/backend-api/codex/models"),
        ("GET", "https://chatgpt.com.attacker.example/backend-api/codex/models"),
        ("GET", "https://chatgpt.com:444/backend-api/codex/models"),
        ("GET", "https://user@chatgpt.com/backend-api/codex/models"),
        ("GET", "https://chatgpt.com/backend-api/codex/models#fragment"),
        ("GET", "not-a-url"),
    ],
)
def test_network_policy_rejects_non_openai_or_unsafe_destinations(method, url):
    with pytest.raises(OpenAINetworkPolicyError):
        validate_agent_sdk_request(method, url)


def test_network_policy_rejects_redirect_responses():
    class Response:
        status_code = 302
        headers = {"Location": "https://attacker.example/redirect"}

    with pytest.raises(OpenAINetworkPolicyError, match="redirect"):
        reject_redirect_response(Response())


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("POST", "https://chatgpt.com/backend-api/codex/models"),
        ("GET", "https://chatgpt.com/backend-api/memories"),
        ("GET", "https://chatgpt.com/backend-api/user_system_messages"),
        ("GET", "https://chatgpt.com/backend-api/wham/tasks/list"),
        ("POST", "https://chatgpt.com/backend-api/files"),
        ("POST", "https://chatgpt.com/backend-api/transcribe"),
        ("POST", "https://api.openai.com/v1/embeddings"),
        ("POST", "https://auth.openai.com/oauth/token"),
        ("GET", "https://chatgpt.com/backend-api/codex/models?unsafe=true"),
    ],
)
def test_agent_request_policy_rejects_account_upload_platform_and_auth_routes(method, url):
    with pytest.raises(OpenAINetworkPolicyError, match="[Aa]gent-safe"):
        validate_agent_sdk_request(method, url)
