from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from codex_backend_sdk import (
    CodexBackendUnsupportedParameterError,
    OpenAI,
    ParsedResponse,
    Response,
)


class FakeSSE:
    def __init__(self, events):
        self._events = events
        self.closed = False

    def iter_lines(self):
        for event in self._events:
            if event.startswith("event:") or event.startswith("data:"):
                yield event.encode()
            else:
                yield event
        yield b""

    def close(self):
        self.closed = True


class FakeJSONResponse:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}
        self.closed = False

    def json(self):
        return self._payload

    def close(self):
        self.closed = True


class FakeClient(OpenAI):
    def __init__(self):
        super().__init__(model="gpt-test")
        self.posts = []
        self.post_options = []
        self.gets = []

    def _request_response(
        self,
        *,
        body,
        stream=False,
        timeout=None,
    ):
        self.posts.append(("/responses", body, stream))
        self.post_options.append(timeout)
        self.last_response = FakeSSE([
            'data: {"type":"response.content_part.delta","delta":{"text":"hel"}}',
            "",
            'data: {"type":"response.content_part.delta","delta":{"text":"lo"}}',
            "",
            (
                'data: {"type":"response.completed","response":'
                '{"id":"resp_123","model":"gpt-test",'
                '"usage":{"input_tokens":2,"output_tokens":1,"total_tokens":3}}}'
            ),
        ])
        return self.last_response

    def _request_compaction(self, *, body, timeout=None):
        self.posts.append(("/responses/compact", body, False))
        self.post_options.append(timeout)
        self.last_response = FakeJSONResponse({
            "id": "resp_123",
            "output": [{"type": "message", "content": []}],
            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
        })
        return self.last_response

    def _request_models(self, *, client_version, timeout=None):
        self.gets.append(("/models", {"client_version": client_version}))
        self.last_response = FakeJSONResponse(
            {
                "models": [
                    {
                        "slug": "gpt-lower-priority",
                        "display_name": "GPT Lower Priority",
                        "description": "Test model",
                        "context_window": 123,
                        "supported_in_api": True,
                        "priority": 7,
                    },
                    {
                        "slug": "gpt-test",
                        "display_name": "GPT Test",
                        "description": "Test model",
                        "context_window": 456,
                        "supported_in_api": True,
                        "priority": 1,
                    },
                ]
            },
            headers={"ETag": "models-etag"},
        )
        return self.last_response


class ParsedPerson(BaseModel):
    name: str
    age: int


@dataclass
class TextOptions:
    verbosity: str


class ParseFakeClient(FakeClient):
    def _request_response(
        self,
        *,
        body,
        stream=False,
        timeout=None,
    ):
        self.posts.append(("/responses", body, stream))
        self.post_options.append(timeout)
        self.last_response = FakeSSE([
            (
                'data: {"type":"response.output_text.delta","delta":'
                '"{\\"name\\":\\"Ada\\",\\"age\\":37}"}'
            ),
            "",
            (
                'data: {"type":"response.completed","response":'
                '{"id":"resp_parse","model":"gpt-test","output":[{"type":"message",'
                '"role":"assistant","content":[{"type":"output_text",'
                '"text":"{\\"name\\":\\"Ada\\",\\"age\\":37}"}]}]}}'
            ),
        ])
        return self.last_response


class TierReportingFakeClient(FakeClient):
    def _request_response(
        self,
        *,
        body,
        stream=False,
        timeout=None,
    ):
        self.posts.append(("/responses", body, stream))
        self.post_options.append(timeout)
        self.last_response = FakeSSE([
            (
                'data: {"type":"response.completed","response":'
                '{"id":"resp_tier","model":"gpt-test",'
                '"status":"completed","service_tier":"default"}}'
            ),
        ])
        return self.last_response


def test_responses_create_collects_to_pydantic_response():
    client = FakeClient()

    response = client.responses.create(
        model="gpt-test",
        input="Say hello",
        reasoning={"effort": "low", "summary": "auto"},
        text={"verbosity": "low"},
        stream=False,
    )

    assert isinstance(response, Response)
    assert response.id == "resp_123"
    assert response.output_text == "hello"
    assert "output_text" not in response.model_dump()
    assert response.usage.total_tokens == 3
    assert client.last_response.closed is True

    path, payload, stream = client.posts[0]
    assert path == "/responses"
    assert stream is True
    assert payload["model"] == "gpt-test"
    assert payload["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Say hello"}],
        }
    ]
    assert payload["reasoning"] == {"effort": "low", "summary": "auto"}
    assert payload["text"] == {"verbosity": "low"}


def test_responses_create_forwards_only_timeout_transport_option():
    client = FakeClient()

    client.responses.create(input="Hi", timeout=5)

    assert client.post_options[0] == 5


@pytest.mark.parametrize("service_tier", ["default", "priority"])
def test_responses_create_forwards_verified_service_tiers(service_tier):
    client = FakeClient()

    response = client.responses.create(input="Hi", service_tier=service_tier)

    assert client.posts[0][1]["service_tier"] == service_tier
    assert response.service_tier is None


def test_responses_create_uses_the_backend_reported_tier_not_the_request():
    client = TierReportingFakeClient()

    response = client.responses.create(input="Hi", service_tier="priority")

    assert client.posts[0][1]["service_tier"] == "priority"
    assert response.service_tier == "default"


@pytest.mark.parametrize("service_tier", ["auto", "flex", "fast", "standard", "unknown"])
def test_responses_create_rejects_unverified_service_tiers_before_transport(service_tier):
    client = FakeClient()

    with pytest.raises(CodexBackendUnsupportedParameterError, match="service_tier"):
        client.responses.create(input="Hi", service_tier=service_tier)

    assert client.posts == []


def test_responses_create_rejects_non_string_service_tier_before_transport():
    client = FakeClient()

    with pytest.raises(TypeError, match="service_tier"):
        client.responses.create(input="Hi", service_tier=1)

    assert client.posts == []


def test_responses_parse_inherits_create_service_tier_validation():
    client = ParseFakeClient()

    with pytest.raises(CodexBackendUnsupportedParameterError, match="service_tier"):
        client.responses.parse(
            input="Extract",
            text_format=ParsedPerson,
            service_tier="fast",
        )

    assert client.posts == []


def test_response_exposes_tool_calls_and_reasoning_summary():
    response = Response(
        id="resp_helpers",
        output=[
            {
                "type": "reasoning",
                "summary": [
                    {"type": "summary_text", "text": "First"},
                    {"type": "summary_text", "text": "Second"},
                ],
            },
            {
                "type": "function_call",
                "call_id": "call_123",
                "name": "lookup",
                "arguments": "{}",
            },
        ],
    )

    assert response.reasoning_summary == "First\nSecond"
    assert response.tool_calls == [
        {
            "type": "function_call",
            "call_id": "call_123",
            "name": "lookup",
            "arguments": "{}",
        }
    ]


def test_responses_parse_sends_strict_schema_and_returns_parsed_response():
    client = ParseFakeClient()

    parsed = client.responses.parse(
        model="gpt-test",
        input="Extract the person",
        text_format=ParsedPerson,
        text=TextOptions(verbosity="low"),
    )

    assert isinstance(parsed, ParsedResponse)
    assert parsed.id == "resp_parse"
    assert parsed.output_parsed == ParsedPerson(name="Ada", age=37)
    path, payload, stream = client.posts[0]
    assert path == "/responses"
    assert stream is True
    assert payload["text"]["verbosity"] == "low"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["name"] == "ParsedPerson"
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"]["additionalProperties"] is False


def test_responses_parse_rejects_existing_text_format():
    client = ParseFakeClient()

    try:
        client.responses.parse(
            input="Extract",
            text_format=ParsedPerson,
            text={"format": {"type": "json_object"}},
        )
    except TypeError as exc:
        assert "text_format" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_responses_create_normalizes_official_input_items():
    client = FakeClient()

    client.responses.create(
        input=[
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ],
    )

    assert client.posts[0][1]["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hi"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hello"}],
        },
    ]


def test_responses_create_stream_returns_openai_event_objects():
    client = FakeClient()

    events = list(client.responses.create(input="Hi", stream=True))

    assert events[0].type == "response.content_part.delta"
    assert events[0].delta == {"text": "hel"}
    assert events[-1].type == "response.completed"
    assert events[-1].response["id"] == "resp_123"
    assert client.last_response.closed is True


def test_responses_stream_close_releases_response_after_iteration_starts():
    client = FakeClient()
    events = client.responses.create(input="Hi", stream=True)

    next(events)
    assert client.last_response.closed is False
    events.close()

    assert client.last_response.closed is True


def test_models_resource_returns_iterable_page():
    client = FakeClient()

    page = client.models.list()
    model = page[0]

    assert len(page) == 2
    assert model.id == "gpt-test"
    assert model.context_window == 456
    assert page.etag == "models-etag"
    assert client.models.retrieve("gpt-test").id == "gpt-test"
    assert len(client.gets) == 1
    assert client.last_response.closed is True


def test_models_resource_can_force_refresh_cached_page():
    client = FakeClient()

    assert client.models.list() is client.models.list()
    client.models.list(force_refresh=True)

    assert len(client.gets) == 2


def test_responses_compact_sends_shared_request_fields():
    client = FakeClient()

    compacted = client.responses.compact(
        model="gpt-test",
        input=[{"role": "user", "content": "Long context"}],
        instructions="Compact this.",
        tools=[{
            "type": "function",
            "name": "lookup",
            "parameters": {"type": "object", "properties": {}},
        }],
        parallel_tool_calls=True,
        reasoning={"effort": "medium"},
        service_tier="priority",
        prompt_cache_key="cache-key",
        text={"verbosity": "low"},
    )

    assert compacted.id == "resp_123"
    assert compacted.usage is not None
    assert compacted.usage.input_tokens == 11
    assert compacted.usage.output_tokens == 7
    assert compacted.usage.total_tokens == 18
    assert client.last_response.closed is True
    path, payload, stream = client.posts[0]
    assert path == "/responses/compact"
    assert stream is False
    assert payload == {
        "model": "gpt-test",
        "instructions": "Compact this.",
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Long context"}],
            }
        ],
        "tools": [{
            "type": "function",
            "name": "lookup",
            "parameters": {"type": "object", "properties": {}},
        }],
        "parallel_tool_calls": True,
        "reasoning": {"effort": "medium"},
        "service_tier": "priority",
        "prompt_cache_key": "cache-key",
        "text": {"verbosity": "low"},
    }


def test_responses_create_rejects_official_params_not_exposed_by_codex_backend():
    client = FakeClient()

    try:
        client.responses.create(input="Hi", temperature=0.2)
    except NotImplementedError as exc:
        assert "temperature" in str(exc)
    else:
        raise AssertionError("temperature should be rejected before hitting the backend")


def test_responses_rejects_hosted_and_network_capable_tools():
    client = FakeClient()

    for tool_type in ("web_search", "web_search_preview", "computer_use", "mcp"):
        try:
            client.responses.create(input="Hi", tools=[{"type": tool_type}])
        except ValueError as exc:
            assert "caller-executed function tools" in str(exc)
        else:
            raise AssertionError(f"{tool_type} should be rejected")

    assert client.posts == []


def test_responses_rejects_non_function_tool_choice():
    client = FakeClient()
    tools = [{"type": "function", "name": "lookup", "parameters": {"type": "object"}}]

    try:
        client.responses.create(
            input="Hi",
            tools=tools,
            tool_choice={"type": "web_search"},
        )
    except ValueError as exc:
        assert "function tool choices" in str(exc)
    else:
        raise AssertionError("Hosted tool choice should be rejected")

    assert client.posts == []
