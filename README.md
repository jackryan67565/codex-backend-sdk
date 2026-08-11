# codex-backend-sdk

Agent-safe, unofficial Python client for the ChatGPT Codex Responses backend.

The package intentionally exposes a narrow synchronous surface:

- stateless Responses creation, streaming, parsing, and compaction;
- Codex model listing and retrieval;
- caller-executed function-call descriptions and results.

It is not an OpenAI-supported SDK. Within the deliberately narrow Responses and
Models surface documented below, it is designed as a drop-in-oriented adapter
for code written against `openai-python`. It reverse-engineers undocumented
`chatgpt.com` behavior that may change without notice.

> **Requirements:** Python 3.9+ and a current ChatGPT account login with Codex
> access. Availability remains account-, plan-, and rollout-dependent.

## OpenAI SDK compatibility

Use the familiar primary client name and Responses call shape:

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()
response = client.responses.create(model="gpt-5.4", input="Hello")
```

The compatibility target is the supported subset, not the full official SDK.
Authentication uses a read-only Codex login instead of an API key, and the
agent-safe boundary intentionally rejects unsupported resources, hosted tools,
caller headers/query/body, custom base URLs, and backend-incompatible official
parameters. Unsupported parameters fail locally instead of being silently
discarded or reinterpreted; `max_output_tokens` remains one such parameter.

See [OpenAI SDK compatibility](docs/openai-sdk-compatibility.md) for the exact
contract and known differences.

## Agent-safety contract

Version 0.4 contracts the library around the least authority required for an
agent to call Codex Responses. The transport accepts only these exact requests:

| Method | Destination |
|---|---|
| `GET` | `https://chatgpt.com/backend-api/codex/models` |
| `POST` | `https://chatgpt.com/backend-api/codex/responses` |
| `POST` | `https://chatgpt.com/backend-api/codex/responses/compact` |

The route policy is enforced underneath the resource layer. Merely targeting an
OpenAI-owned hostname is not sufficient.

The client does not expose or connect to:

- ChatGPT memories, customization, conversations, or account data;
- Codex Cloud tasks, turns, environments, configuration, or quota controls;
- file uploads, audio transcription, image generation/editing, or embeddings;
- Realtime calls, WebSockets, connection headers, or API-key material;
- OAuth login, token refresh, credential writes, raw request helpers, custom
  base URLs, redirects, proxies, caller headers, or caller query parameters;
- hosted web-search, computer-use, or MCP tools.

Only ordinary function tools are accepted. The SDK returns function calls to
the caller; it never executes them.

The repository's Codex substrate also disables command network access by
default. Live tests require a separate explicit flag.

### Security boundary

This package reduces ambient authority and prevents accidental use of unrelated
backend routes. It is not a sandbox for hostile Python code in the same process.
Code that can read the user's files can attempt to read the shared Codex auth
cache directly, and code that receives unrestricted network permission can
construct its own HTTP client. Use OS/Codex filesystem permissions and a trusted
credential broker when executing untrusted agents.

Never print, log, copy, or commit `$CODEX_HOME/auth.json`, request headers, or
authenticated response bodies.

## Installation

```bash
git clone https://github.com/jackryan67565/codex-backend-sdk.git
cd codex-backend-sdk
pip install -e .
```

Installing packages can contact the package index configured for the local
environment. Package installation is outside the SDK runtime network contract.

### Install the local wheel in another project

Release checkpoints are built into `dist/`. Install the wheel directly into a
project's virtual environment without publishing this unofficial package:

```bash
uv pip install \
  --python /absolute/path/to/project/.venv/bin/python \
  /absolute/path/to/codex-backend-sdk/dist/codex_backend_sdk-0.4.1-py3-none-any.whl
```

Or, when that virtual environment includes pip:

```bash
/absolute/path/to/project/.venv/bin/python -m pip install \
  /absolute/path/to/codex-backend-sdk/dist/codex_backend_sdk-0.4.1-py3-none-any.whl
```

The target environment must also satisfy the wheel's `pydantic>=2.0` and
`requests>=2.28` dependencies. An installer may contact its configured package
index when those dependencies are not already available locally.

## Authentication

Sign in using the trusted Codex CLI or ChatGPT desktop app first. The SDK reuses
the current `$CODEX_HOME/auth.json` login, defaulting to `~/.codex/auth.json`:

```bash
codex login
```

Then create an authenticated client:

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()
```

The client owns its HTTP session. Use it as a context manager when practical so
the session is closed deterministically:

```python
with OpenAI().authenticate() as client:
    response = client.responses.create(input="Hello")
```

`authenticate()` is deliberately read-only and local. It retains only the access
token and ChatGPT account identifier needed by the Codex backend. It does not:

- start a browser or loopback callback server;
- load API keys or refresh tokens into its credential object;
- refresh credentials;
- write the shared authentication file;
- probe an account, quota, or model endpoint.

If the access token is missing, expired, or close to expiry, authentication
fails and asks the operator to refresh it through the trusted Codex CLI or
desktop app.

## Basic Responses use

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()
response = client.responses.create(
    model="gpt-5.4",
    input="Explain quicksort in one paragraph.",
)
print(response.output_text)
```

Responses are caller-managed and stateless. The SDK does not create, list, or
resume ChatGPT UI conversations and the backend does not expose
`previous_response_id` through this client.

## Streaming

```python
stream = client.responses.create(
    input="Say hello in three languages.",
    stream=True,
)

for event in stream:
    if event.type in {"response.output_text.delta", "response.content_part.delta"}:
        delta = event.delta
        print(delta if isinstance(delta, str) else delta.get("text", ""), end="")
```

## Multi-turn input

Pass prior input and output explicitly:

```python
history = [{"role": "user", "content": "My name is Alice. Say OK."}]
first = client.responses.create(input=history)

history.extend(first.output)
history.append({"role": "user", "content": "What is my name?"})
second = client.responses.create(input=history)
print(second.output_text)
```

## Function calling

Only caller-executed functions are allowed:

```python
tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Return weather from the caller's local data.",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
}]

response = client.responses.create(
    input="What is the weather in Paris?",
    tools=tools,
)
```

The caller decides whether and how to execute returned calls, applies its own
authorization, and passes a `function_call_output` item in a later request.
Hosted tool types such as `web_search`, `computer_use`, and `mcp` raise before
any network request.

## Structured output

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

parsed = client.responses.parse(
    input="Ada is 37 years old.",
    text_format=Person,
)
print(parsed.output_parsed)
```

## Compaction

```python
compacted = client.responses.compact(
    model="gpt-5.4",
    input=history,
    instructions="Compact the caller-managed history.",
)
```

## Models

```python
models = client.models.list()
for model in models:
    print(model.id, model.display_name, model.context_window)

selected = client.models.retrieve(models[0].id)
```

## Transport invariants

SDK-owned sessions:

- set `requests.Session.trust_env = False`;
- never follow redirects;
- validate the exact method, host, and path before every request;
- attach authentication and account routing headers internally;
- do not accept caller-provided headers, query parameters, or base URLs;
- retry only idempotent model-catalog reads, never Responses POSTs;
- require finite positive timeouts of at most ten minutes, cap model-read
  retries at five, and cap each retry delay at 60 seconds;
- connect only to `chatgpt.com` over HTTPS on port 443.

URLs inside model input are payload data sent to OpenAI. This SDK does not fetch
them locally.

## Testing

The default suite is offline and must not load stored credentials or contact a
network service:

```bash
python -m pytest -q
```

Live integration tests are marked `live` and skipped by default. Run them only
after deliberately authorizing stored credential use, OpenAI network access,
and account quota consumption:

```bash
python -m pytest --live -q \
  tests/test_basic.py \
  tests/test_conversation.py \
  tests/test_reasoning.py \
  tests/test_structured_output.py \
  tests/test_tools.py
```

## Historical versions

Versions before 0.4 exposed broader ChatGPT, WHAM, upload, Platform, Realtime,
and credential-management helpers. They were removed from the current package
because a bearer accepted by an OpenAI hostname can still authorize data or
state outside the narrow agent task. The append-only [changelog](CHANGELOG.md)
records those historical features; they are not part of the current contract.

Current wire notes are in [docs/backend-api.md](docs/backend-api.md). Frozen
pre-0.4 audit material under `docs/audits/` is historical evidence only.
