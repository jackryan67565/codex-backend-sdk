import json

import pytest
import requests
from requests.adapters import BaseAdapter

from codex_backend_sdk import OpenAI
from codex_backend_sdk._storage import _CredentialStore


class RecordingAdapter(BaseAdapter):
    def __init__(self):
        self.request = None
        self.wire_headers = None
        self.send_kwargs = None

    def send(self, request, **kwargs):
        self.request = request
        self.wire_headers = dict(request.headers)
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
    store = _CredentialStore(
        access_token="access-secret",
        account_id="acct_123",
    )
    client = OpenAI(model="gpt-test", max_retries=0)
    client._CodexClient__credentials = store
    adapter = RecordingAdapter()
    client._session.mount("https://", adapter)
    return client, adapter


def test_responses_final_wire_headers_and_options():
    client, adapter = _client_with_adapter()

    response = client.responses.create(
        input="ping",
        timeout=7,
    )

    assert response.id == "resp_wire"
    assert adapter.request is not None
    assert adapter.request.method == "POST"
    assert adapter.request.url == "https://chatgpt.com/backend-api/codex/responses"
    assert adapter.wire_headers["Authorization"] == "Bearer access-secret"
    assert adapter.wire_headers["ChatGPT-Account-ID"] == "acct_123"
    assert adapter.wire_headers["originator"] == "codex_backend_sdk"
    assert adapter.wire_headers["Accept"] == "text/event-stream"
    assert adapter.wire_headers["Content-Type"] == "application/json"
    assert "OpenAI-Beta" not in adapter.wire_headers
    assert "Authorization" not in adapter.request.headers
    assert "ChatGPT-Account-ID" not in adapter.request.headers
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


def test_responses_does_not_accept_caller_headers_or_query():
    client, adapter = _client_with_adapter()

    with pytest.raises(TypeError):
        client.responses.create(input="ping", extra_headers={"X-Test": "unsafe"})
    with pytest.raises(TypeError):
        client.responses.create(input="ping", extra_query={"unsafe": "true"})

    assert adapter.request is None
