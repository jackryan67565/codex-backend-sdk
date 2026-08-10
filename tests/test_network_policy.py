import pytest

from codex_backend_sdk import OpenAINetworkPolicyError
from codex_backend_sdk._network import reject_redirect_response, validate_openai_url


@pytest.mark.parametrize(
    "url",
    [
        "https://chatgpt.com/backend-api/codex",
        "https://api.openai.com/v1/responses",
        "https://auth.openai.com/oauth/token",
        "https://files.oaiusercontent.com/file-123",
        "https://persistent.oaistatic.com/asset",
    ],
)
def test_network_policy_accepts_openai_operated_domains(url):
    assert validate_openai_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.openai.com/v1/responses",
        "https://attacker.example/upload",
        "https://openai.com.attacker.example/upload",
        "https://api.openai.com:444/v1/responses",
        "https://user@api.openai.com/v1/responses",
        "not-a-url",
    ],
)
def test_network_policy_rejects_non_openai_or_unsafe_destinations(url):
    with pytest.raises(OpenAINetworkPolicyError):
        validate_openai_url(url)


def test_network_policy_allows_openai_realtime_websocket_only_explicitly():
    url = "wss://api.openai.com/v1/realtime"
    assert validate_openai_url(url, allowed_schemes=("wss",)) == url
    with pytest.raises(OpenAINetworkPolicyError):
        validate_openai_url(url)


def test_network_policy_rejects_redirect_responses():
    class Response:
        status_code = 302
        headers = {"Location": "https://attacker.example/redirect"}

    with pytest.raises(OpenAINetworkPolicyError, match="redirect"):
        reject_redirect_response(Response())
