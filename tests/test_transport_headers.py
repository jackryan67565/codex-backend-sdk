import json
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from codex_backend_sdk import OpenAI, TokenStore


class RecordingAdapter(BaseAdapter):
    def __init__(self):
        self.request = None
        self.send_kwargs = None

    def send(self, request, **kwargs):
        self.request = request
        self.send_kwargs = kwargs
        response = requests.Response()
        response.status_code = 200
        response.url = request.url
        response.request = request
        response.headers["Content-Type"] = "text/event-stream"
        response._content = (
            b'data: {"type":"response.completed","response":'
            b'{"id":"resp_wire","model":"gpt-test","output":[]}}\n\n'
        )
        response._content_consumed = True
        return response

    def close(self):
        return None


def _client_with_adapter():
    store = TokenStore(
        access_token="access-secret",
        refresh_token="refresh-secret",
        id_token_raw="id-secret",
        account_id="acct_123",
    )
    client = OpenAI(store=store, model="gpt-test", max_retries=0)
    adapter = RecordingAdapter()
    client._session.mount("https://", adapter)
    return client, adapter


def test_responses_final_wire_headers_and_options():
    client, adapter = _client_with_adapter()
    extra_headers = {"X-Trace-ID": "trace-123"}

    response = client.responses.create(
        input="ping",
        extra_headers=extra_headers,
        extra_query={"trace": "enabled"},
        timeout=7,
    )

    assert response.id == "resp_wire"
    assert adapter.request is not None
    assert adapter.request.method == "POST"
    assert adapter.request.url.startswith(
        "https://chatgpt.com/backend-api/codex/responses?"
    )
    assert parse_qs(urlsplit(adapter.request.url).query) == {"trace": ["enabled"]}
    assert adapter.request.headers["Authorization"] == "Bearer access-secret"
    assert adapter.request.headers["ChatGPT-Account-ID"] == "acct_123"
    assert adapter.request.headers["originator"] == "codex_backend_sdk"
    assert adapter.request.headers["Accept"] == "text/event-stream"
    assert adapter.request.headers["Content-Type"] == "application/json"
    assert adapter.request.headers["X-Trace-ID"] == "trace-123"
    assert "OpenAI-Beta" not in adapter.request.headers
    assert json.loads(adapter.request.body) == {
        "model": "gpt-test",
        "instructions": "",
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "ping"}],
            }
        ],
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "store": False,
        "stream": True,
        "include": [],
    }
    assert adapter.send_kwargs["timeout"] == 7
    assert adapter.send_kwargs["stream"] is True
    assert extra_headers == {"X-Trace-ID": "trace-123"}


@pytest.mark.parametrize(
    "header",
    [
        "Authorization",
        "authorization",
        "CHATGPT-ACCOUNT-ID",
        "Originator",
        "OpenAI-Beta",
        "Host",
        "Content-Length",
        "accept",
    ],
)
def test_responses_rejects_protected_header_overrides(header):
    client, adapter = _client_with_adapter()

    with pytest.raises(ValueError, match="protected backend header"):
        client.responses.create(input="ping", extra_headers={header: "override"})

    assert adapter.request is None
