# codex-backend-sdk

Unofficial Python SDK for the ChatGPT Codex backend API
(`chatgpt.com/backend-api/codex`).

This package intentionally resembles selected synchronous `openai-python`
resources where the Codex backend overlaps with them. It is not a drop-in
replacement: routes differ in authentication, billing, availability, response
typing, and supported parameters.

> **Requirements:** Python 3.9+ and a ChatGPT account with Codex access.
> Availability is account-, plan-, and rollout-dependent. Authentication uses
> ChatGPT OAuth and shares `$CODEX_HOME/auth.json` with Codex CLI, defaulting to
> `~/.codex/auth.json`.

> **Disclaimer:** This is an independent, community-maintained library that
> reverse-engineers undocumented endpoints of `chatgpt.com`. It is not
> affiliated with, endorsed by, or supported by OpenAI.

This README is the maintained SDK contract. [Backend API notes](docs/backend-api.md)
record dated reverse-engineering observations and include some routes that the
SDK does not expose.

## Installation

```bash
git clone https://github.com/B4PT0R/codex-backend-sdk.git
cd codex-backend-sdk
pip install -e .
```

For development dependencies, use `pip install -e ".[dev]"`. Package
installation may contact the package indexes configured for your environment;
it is not covered by the SDK runtime network boundary described below.

## Authentication Behavior

`OpenAI().authenticate()` reuses the shared Codex credentials at
`$CODEX_HOME/auth.json` (default `~/.codex/auth.json`). It may refresh and
rewrite those credentials. If no usable credentials exist, it opens the system
browser and listens on `127.0.0.1:1455` for the OAuth callback.

`authenticate(interactive=False)` prevents browser login, but it is not an
offline operation: it may refresh credentials or probe ChatGPT, and it raises
`RuntimeError` when stored credentials cannot be used. Never print or commit the
credential file or authenticated response bodies.

## Basic Usage

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()

response = client.responses.create(
    model="gpt-5.4",
    input="Explain quicksort in one paragraph.",
)

print(response.output_text)
```

## Streaming

```python
stream = client.responses.create(
    model="gpt-5.4",
    input="Say 'hi' five times.",
    stream=True,
)

for event in stream:
    if event.type in {"response.output_text.delta", "response.content_part.delta"}:
        delta = event.delta
        print(delta if isinstance(delta, str) else delta.get("text", ""), end="")
```

## Models

```python
models = client.models.list()
for model in models:
    print(model.id, model.display_name, model.context_window)

info = client.models.retrieve("gpt-5.4")
```

## Multi-Turn Input

The Codex backend does not expose `previous_response_id`, so pass prior
input/output items explicitly. Responses calls are caller-managed and
stateless: they do not create, list, or resume ChatGPT UI conversations.

```python
history = [
    {"role": "user", "content": "My name is Alice. Say OK."},
]

reply1 = client.responses.create(input=history).output_text
history.append({"role": "assistant", "content": reply1})
history.append({"role": "user", "content": "What is my name?"})

reply2 = client.responses.create(input=history).output_text
print(reply2)
```

## Function Calling

```python
import json

tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
}]

history = [{"role": "user", "content": "What's the weather in Paris?"}]
first = client.responses.create(input=history, tools=tools)

call = next(item for item in first.output if item["type"] == "function_call")
result = {"temperature": 18, "unit": "celsius", "condition": "cloudy"}
history.extend(first.output)
history.append({
    "type": "function_call_output",
    "call_id": call["call_id"],
    "output": json.dumps(result),
})

second = client.responses.create(
    input=history,
    tools=tools,
)

print(second.output_text)
```

## Structured Output

```python
schema = {
    "title": "person",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
    "additionalProperties": False,
}

response = client.responses.create(
    input="Extract: Bob is 42 years old.",
    text={
        "format": {
            "type": "json_schema",
            "name": "person",
            "schema": schema,
            "strict": True,
        }
    },
)
```

## Exposed Backend Resources

The SDK exposes backend endpoints through OpenAI-shaped or backend-specific
top-level resources (`responses`, `models`, `realtime`, `embeddings`, `audio`,
`images`, and `files`) plus the `codex` namespace for Codex/ChatGPT-only account
resources.

“Exposed” means that a client method exists; it does not guarantee that every
account is entitled to the route. Experimental, Platform-billed, raw, and
plan-dependent behavior is called out below.

| Backend endpoint | SDK method | Notes |
|---|---|---|
| `POST /backend-api/codex/responses` | `client.responses.create(...)` | Stream-only backend; non-streaming SDK calls are collected from SSE events. |
| `POST /backend-api/codex/responses/compact` | `client.responses.compact(...)` | Codex-specific helper for encrypted context compaction. |
| `POST /backend-api/codex/memories/trace_summarize` | `client.codex.memories.trace_summarize(...)` | Raw Codex memory trace summarization helper. |
| `GET /backend-api/codex/models` | `client.models.list()` / `client.models.retrieve(...)` | OpenAI-shaped model objects with Codex metadata preserved as extra fields. |
| `POST /backend-api/codex/realtime/calls` | `client.realtime.calls.create(...)` | Experimental SDP call creation. The protocol is implemented by Codex, but ChatGPT routing is rollout-dependent and may return `404 Not Found`. |
| `wss://api.openai.com/v1/realtime?model=...` | `client.realtime_websocket_url(...)` / `client.realtime.websocket_headers(...)` | Voice v2 connection-material helpers; requires a Realtime API key from the auth store or `OPENAI_API_KEY`. The SDK does not open the socket. |
| `POST /v1/embeddings` | `client.embeddings.create(...)` | Uses the Codex OAuth access token against `api.openai.com`; usage is charged to the associated OpenAI Platform organization. |
| `POST /backend-api/transcribe` | `client.audio.transcriptions.create(...)` | Uses the authenticated ChatGPT backend for non-streaming batch transcription; no developer API key is required. |
| `POST /backend-api/codex/images/generations` | `client.images.generate(...)` | Generates images through the authenticated Codex backend and returns typed base64 image data. |
| `POST /backend-api/codex/images/edits` | `client.images.edit(...)` | Edits one or more URL/data-URL images through the authenticated Codex backend. |
| `GET /backend-api/codex/rate-limit-reset-credits` | `client.codex.rate_limit_reset_credits.list()` | Lists detailed reset credits available to the authenticated account. |
| `POST /backend-api/codex/rate-limit-reset-credits/consume` | `client.codex.rate_limit_reset_credits.consume(...)` | Consumes a reset credit using an idempotent redemption request ID. |
| `GET /backend-api/wham/usage` | `client.codex.usage()` | Codex/ChatGPT quota and rate-limit status. |
| `GET /backend-api/wham/config/requirements` | `client.codex.config.requirements()` | Raw managed requirements/config payload for the authenticated account. |
| `GET /backend-api/wham/tasks/list` | `client.codex.tasks.list(...)` | Raw Codex cloud task listing. |
| `GET /backend-api/wham/tasks/{task_id}` | `client.codex.tasks.retrieve(task_id)` | Raw Codex cloud task detail. |
| `GET /backend-api/wham/tasks/{task_id}/turns` | `client.codex.tasks.turns.list(task_id)` | Raw task turn mapping. |
| `GET /backend-api/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns` | `client.codex.tasks.turns.sibling_turns(task_id, turn_id)` | Raw sibling turn list. |
| `GET /backend-api/wham/environments` | `client.codex.environments.list()` | Raw Codex cloud environment list. |
| `POST /backend-api/files` + signed upload | `client.files.upload(...)` | Uploads local files only when the signed URL remains on an approved OpenAI-operated domain and returns `sediment://...` metadata. |
| `GET /backend-api/memories` | `client.codex.memories.list()` | Raw ChatGPT memory payload for the authenticated account. |
| `GET /backend-api/user_system_messages` | `client.codex.user_system_messages.retrieve()` | Raw ChatGPT customization/system-message payload. |

### Responses

`client.responses.create(...)` follows the official OpenAI Responses API where
the Codex backend overlaps with it.

Supported request fields:

- `model`
- `input`
- `instructions`
- `include`
- `parallel_tool_calls`
- `prompt_cache_key`
- `reasoning`
- `service_tier`
- `store=False`
- `stream`
- `text`
- `tool_choice`
- `tools`

The backend itself requires streaming. When `stream=True`, the SDK yields
`ResponseStreamEvent` objects directly. When `stream` is omitted or false, the
SDK consumes the SSE stream and returns a collected `Response`.

HTTP Responses requests use the ChatGPT OAuth bearer, account ID, Codex
originator, and `Accept: text/event-stream`. They do not send the historical
`OpenAI-Beta: responses=experimental` header. `extra_headers`, `extra_query`,
and per-call `timeout` are forwarded. For Responses only, `extra_headers`
cannot override `Authorization`, `ChatGPT-Account-ID`, `originator`,
`OpenAI-Beta`, `Host`, `Content-Length`, or the required `Accept` header; names
are matched case-insensitively.

```python
response = client.responses.create(
    model="gpt-5.4",
    instructions="Be concise.",
    input=[
        {"role": "user", "content": "Summarize this API shape."},
    ],
    reasoning={"effort": "medium", "summary": "auto"},
    include=["reasoning.encrypted_content"],
    text={"verbosity": "medium"},
    prompt_cache_key="session-123",
)
```

For structured output, `client.responses.parse(...)` accepts a Pydantic model,
sends it as a strict JSON schema, and returns `ParsedResponse`:

```python
from pydantic import BaseModel


class Person(BaseModel):
    name: str
    age: int


parsed = client.responses.parse(
    model="gpt-5.4",
    input="Extract: Ada is 37 years old.",
    text_format=Person,
)
print(parsed.output_parsed.name)
```

Collected responses expose convenience properties for common output items:
`response.output_text`, `response.reasoning_summary`, and
`response.tool_calls`.

Unsupported official Responses parameters are rejected explicitly with
`CodexBackendUnsupportedParameterError`, including `temperature`, `top_p`,
`top_logprobs`, `max_output_tokens`, `max_tool_calls`, `metadata`, `user`,
`safety_identifier`, `truncation`, `previous_response_id`, `conversation`,
`context_management`, `background`, `prompt`, `prompt_cache_retention`,
`stream_options`, and `extra_body`.

### Context Compaction

`client.responses.compact(...)` is specific to the Codex backend. It compresses
a long Responses-style input list into an opaque encrypted compaction summary
that can be replayed in later `input` arrays.

```python
compacted = client.responses.compact(
    model="gpt-5.4",
    instructions="Keep task-critical context.",
    input=history,
)

history = compacted.output
```

The returned `CompactedResponse.output` contains regular response items plus
one or more `{"type": "compaction_summary", ...}` items. Treat those summaries
as opaque backend state.

### Models

`client.models.list()` and `client.models.retrieve(model)` mirror the official
OpenAI models resource, while preserving Codex-specific metadata as extra
Pydantic fields. The returned page also exposes the backend `ETag` when present.
Lists are cached per client for five minutes; use
`client.models.list(force_refresh=True)` to refresh. `retrieve(model)` searches
that list rather than calling a model-specific route. The OpenAI-compatibility
arguments `extra_headers`, `extra_query`, `extra_body`, and `timeout` are
currently accepted by these two model methods but ignored.

```python
models = client.models.list()
print(models.etag)
for model in models:
    print(
        model.id,
        model.context_window,
        model.supported_in_api,
        model.supports_reasoning_summaries,
    )
```

Common extra fields include:

- `display_name`
- `description`
- `context_window`
- `supported_in_api`
- `supports_reasoning_summaries`
- `support_verbosity`
- `default_verbosity`
- `default_reasoning_level`
- `supported_reasoning_levels`
- `auto_compact_token_limit`
- `prefer_websockets`
- `input_modalities`
- `available_in_plans`
- `base_instructions`
- `priority`
- `raw`

### Realtime

The SDK keeps the realtime surface available for integrations that bridge Codex
auth with voice sessions.

`client.realtime.calls.create(...)` mirrors the official OpenAI SDK call shape:

```python
answer = client.realtime.calls.create(
    sdp=offer_sdp,
    session={"type": "realtime", "model": "gpt-realtime-1.5"},
)

print(answer.text)
```

For WebSocket-based plugins such as `codex-agent`, the client also exposes the
Voice v2 connection details:

```python
url = client.realtime_websocket_url(model="gpt-realtime-1.5")
headers = client.realtime.websocket_headers(session_id="voice-session")
```

During interactive ChatGPT OAuth login, the SDK exchanges the fresh ID token for
the temporary API key required by Realtime and stores it with the other local
credentials. Existing credentials created by older SDK versions may require one
forced interactive login before these headers are available. The header helper
prefers that stored Realtime key and falls back to `OPENAI_API_KEY`; neither is
the ChatGPT OAuth access token.

For non-interactive checks, you can avoid triggering a browser login flow:

```python
try:
    client = OpenAI().authenticate(interactive=False)
except RuntimeError:
    print("No usable stored Codex credentials")
else:
    print(client.authenticated)
    print(client.account_info())
```

### Embeddings

`client.embeddings.create(...)` mirrors the official OpenAI embeddings resource
and sends the Codex OAuth access token directly to `api.openai.com/v1`.

```python
embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input="Embed this sentence.",
    dimensions=256,
)

print(embedding.data[0].embedding)
```

### Audio Transcriptions

`client.audio.transcriptions.create(...)` mirrors the official OpenAI
transcriptions resource for non-streaming calls.

```python
with open("meeting.wav", "rb") as audio:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("meeting.wav", audio, "audio/wav"),
        response_format="json",
    )

print(transcription.text)
```

JSON format returns a typed `Transcription`; `response_format="text"` returns a
string.

### Image Generation

`client.images.generate(...)` uses the ChatGPT-authenticated Codex image backend,
not the separately billed OpenAI Platform image endpoint.

```python
import base64


image = client.images.generate(
    prompt="A cheerful blue robot holding a red flower",
    model="gpt-image-2",
    quality="auto",
    size="auto",
)

with open("robot.png", "wb") as output:
    output.write(base64.b64decode(image.data[0].b64_json))
```

The Codex contract supports `prompt`, `model`, `background`, `n`, `quality`,
and `size`. Editing accepts one or more ordinary URLs or data URLs:

```python
edited = client.images.edit(
    images=["data:image/png;base64,..."],
    prompt="Add a small red star in the center",
    quality="low",
)
```

### Quota And Usage

`client.codex.usage()` calls the ChatGPT WHAM usage endpoint. It returns the raw
quota payload from the backend because the shape contains plan-specific fields.

```python
quota = client.codex.usage()
primary = quota.get("rate_limit", {}).get("primary_window", {})
print(primary.get("used_percent"))
```

Typical fields include:

- `plan_type`
- `rate_limit.allowed`
- `rate_limit.limit_reached`
- `rate_limit.primary_window`
- `rate_limit.secondary_window`
- `additional_rate_limits`
- `credits`
- `rate_limit_reached_type`

Detailed reset credits are available separately:

```python
import uuid


credits = client.codex.rate_limit_reset_credits.list()
for credit in credits.credits:
    print(credit.id, credit.title, credit.expires_at)

# Consuming a credit is an account mutation. Use a unique idempotency key.
result = client.codex.rate_limit_reset_credits.consume(
    redeem_request_id=str(uuid.uuid4()),
    credit_id=credits.credits[0].id,
)
```

### Codex Cloud Tasks

The `client.codex.tasks` and `client.codex.environments` namespaces expose
read-only WHAM Codex Cloud payloads as raw JSON. Task calls return mappings;
`environments.list()` is currently observed as a list of environment objects.
Treat fields defensively because availability and payload shape are
account-dependent.

```python
page = client.codex.tasks.list(limit=10)
for summary in page.get("items", []):
    task_id = summary["id"]
    task = client.codex.tasks.retrieve(task_id)
    turns = client.codex.tasks.turns.list(task_id)
    current_turn_id = turns.get("current_turn_id")
    siblings = (
        client.codex.tasks.turns.sibling_turns(task_id, current_turn_id)
        if current_turn_id
        else None
    )

environments = client.codex.environments.list()
```

Supported task-list filters are `limit`, `cursor`, `task_filter`, and
`environment_id`. These task and turn routes represent Codex Cloud execution
history. They do **not** list or load ordinary ChatGPT sidebar conversations;
this SDK currently exposes no general ChatGPT conversation-history resource.

### ChatGPT Account Data

The `client.codex` namespace also exposes read-only ChatGPT account data that is
not part of the official OpenAI SDK.

```python
memories = client.codex.memories.list()
customization = client.codex.user_system_messages.retrieve()
requirements = client.codex.config.requirements()
```

These methods return raw backend dictionaries because these payloads can contain
personal account-specific fields and may change without notice. ChatGPT
memories and customization are separate from ChatGPT conversation history.

`client.codex.memories.trace_summarize(...)` exposes the Codex memory
summarization endpoint used by the official client. It accepts dictionaries or
`RawMemory` objects and returns a typed `MemorySummarizeResponse`:

```python
from codex_backend_sdk import RawMemory

summary = client.codex.memories.trace_summarize(
    model="gpt-5.4",
    traces=[
        RawMemory(
            id="trace_1",
            metadata={"source_path": "memory.jsonl"},
            items=[{"type": "message", "content": "Remember this"}],
        )
    ],
    reasoning={"effort": "low"},
)
print(summary.output[0].memory_summary)
```

### File Uploads

`client.files.upload(...)` follows the currently observed Codex client flow for
Apps/MCP file parameters: create file metadata under ChatGPT, upload bytes to
the signed URL, then finalize the upload. The SDK rejects non-HTTPS,
non-standard-port, or non-OpenAI upload destinations and never follows upload
redirects. The local upload limit is 512 MiB.

```python
uploaded = client.files.upload("report.csv")
print(uploaded.uri)  # sediment://file_...
```

The returned `download_url` is opaque metadata. The SDK does not validate or
fetch it.

### Retries

Requests sent through the shared API transport retry `429`, `5xx`, timeout, and
connection failures by default. Configure this with
`OpenAI(max_retries=..., retry_base_delay=...)`. This includes POST requests, so
a request may be replayed; use an idempotency key whenever a mutating resource
provides one. SSE failures after response consumption begins are not resumed.

OAuth token exchanges and the signed file-upload `PUT` do not use the shared
retry loop. File finalization separately polls while the backend returns
`status: "retry"`.

## Network Boundary

SDK-owned HTTP requests enforce an application-level hostname policy: HTTPS on
port 443 to `chatgpt.com`, `openai.com`, `oaiusercontent.com`, or
`oaistatic.com`, including their subdomains. The HTTP clients ignore environment
proxy variables and do not follow redirects. This is not operating-system egress
enforcement.

The OAuth flow additionally opens an approved `auth.openai.com` URL in the
system browser and listens on loopback `127.0.0.1:1455` for the callback. Browser
navigation is outside the SDK HTTP policy. The Realtime WebSocket helpers only
return a validated URL and headers; the caller-owned WebSocket transport is
responsible for its own proxy and redirect behavior.

URLs included inside API request payloads are sent to OpenAI but are not fetched
by this SDK. Package installation and Git remotes are development-time tooling,
not SDK runtime egress, and are outside this boundary.

## Development Verification

Do not run bare `pytest` unless you intend to run authenticated integration
tests. The offline unit suite is:

```bash
python3 -m pytest -q \
  tests/test_account_info.py \
  tests/test_client_retry.py \
  tests/test_codex_resources.py \
  tests/test_files_resource.py \
  tests/test_images.py \
  tests/test_network_policy.py \
  tests/test_openai_oauth_resources.py \
  tests/test_realtime_resource.py \
  tests/test_responses_resource.py \
  tests/test_transport_headers.py
```

`test_basic.py`, `test_conversation.py`, `test_reasoning.py`,
`test_structured_output.py`, and `test_tools.py` authenticate through the shared
fixture and contact live services. Run them only when you intend to use stored
credentials, network access, and account quota.

### Observed But Not Exposed

The reverse-engineering notes in `docs/backend-api.md` include additional
observed endpoints. They are not exposed as SDK resources yet because they are
plan-gated, unavailable on `chatgpt.com`, or not stable enough:

- `POST /v1/audio/speech` (auth reaches the endpoint, but Pro OAuth lacks
  `api.model.audio.request` in current tests)
- `wss://chatgpt.com/backend-api/wham/remote/control/server` and its enrollment
  route (observed in Codex clients; not opened or exposed by this SDK)
