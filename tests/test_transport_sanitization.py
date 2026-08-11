import pytest
import requests
from requests.adapters import BaseAdapter

from codex_backend_sdk import OpenAI, OpenAINetworkPolicyError
from codex_backend_sdk._storage import _CredentialStore


_TOKEN = "synthetic-token"
_ACCOUNT_ID = "synthetic-account"
_SECRET_HEADERS = {"Authorization", "ChatGPT-Account-ID"}


class FailureAdapter(BaseAdapter):
    def __init__(self, outcome):
        self.outcome = outcome
        self.request = None
        self.wire_headers = None

    def send(self, request, **kwargs):
        self.request = request
        self.wire_headers = dict(request.headers)
        if self.outcome == "timeout":
            raise requests.Timeout("synthetic timeout", request=request)
        if self.outcome == "connection":
            raise requests.ConnectionError("synthetic connection error", request=request)

        response = requests.Response()
        response.status_code = 302 if self.outcome == "redirect" else 401
        response.url = request.url
        response.request = request
        response._content = b"{}"
        response._content_consumed = True
        if self.outcome == "redirect":
            response.headers["Location"] = "https://attacker.example/redirect"
        return response

    def close(self):
        return None


def _client_with_failure(outcome):
    client = OpenAI(max_retries=0)
    client._CodexClient__credentials = _CredentialStore(
        access_token=_TOKEN,
        account_id=_ACCOUNT_ID,
    )
    adapter = FailureAdapter(outcome)
    client._session.mount("https://", adapter)
    return client, adapter


def _call_models(client):
    client.models.list(force_refresh=True)


def _call_responses(client):
    client.responses.create(input="ping")


def _call_compaction(client):
    client.responses.compact(input=[])


@pytest.mark.parametrize("call", [_call_models, _call_responses, _call_compaction])
@pytest.mark.parametrize(
    ("outcome", "error_type"),
    [
        ("status", requests.HTTPError),
        ("redirect", OpenAINetworkPolicyError),
        ("timeout", requests.Timeout),
        ("connection", requests.ConnectionError),
    ],
)
def test_transport_failures_do_not_retain_credentials(call, outcome, error_type):
    client, adapter = _client_with_failure(outcome)

    with pytest.raises(error_type) as caught:
        call(client)

    assert adapter.wire_headers["Authorization"] == f"Bearer {_TOKEN}"
    assert adapter.wire_headers["ChatGPT-Account-ID"] == _ACCOUNT_ID
    assert adapter.request is not None
    assert _SECRET_HEADERS.isdisjoint(adapter.request.headers)

    exception_request = getattr(caught.value, "request", None)
    if exception_request is not None:
        assert _SECRET_HEADERS.isdisjoint(exception_request.headers)
    exception_response = getattr(caught.value, "response", None)
    if exception_response is not None and exception_response.request is not None:
        assert _SECRET_HEADERS.isdisjoint(exception_response.request.headers)
