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
response = client.responses.create(input="Hello")
```

Omitting `model` selects the current checkout's client default,
`gpt-5.6-sol`. Pass `model=` to `OpenAI(...)` or an individual Responses call
to override it. This local default does not guarantee availability for every
ChatGPT account or rollout.

The compatibility target is the supported subset, not the full official SDK.
CBS pins `openai==2.46.0` as its differential-test baseline; the
official package is a development dependency, not a runtime dependency.
Authentication uses a read-only Codex login instead of an API key, and the
agent-safe boundary intentionally rejects unsupported resources, hosted tools,
caller headers/query/body, custom base URLs, and backend-incompatible official
parameters. Unsupported parameters fail locally instead of being silently
discarded or reinterpreted; `max_output_tokens` remains one such parameter.

See [OpenAI SDK compatibility](docs/openai-sdk-compatibility.md) for the exact
contract and known differences.

## Agent-safety contract

Version 0.4 and later contract the library around the least authority required
for an agent to call Codex Responses. The transport accepts only these exact
requests:

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
- OAuth login, token refresh, credential writes, generic raw request helpers, custom
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

Never print, log, copy, or commit `$CODEX_HOME/auth.json`, prepared
authentication headers, or authenticated response bodies.

See the current [agent-safety security review](security_best_practices_report.md)
for the reviewed boundary, remediations, and deployment requirements.

## Installation

The commands in this section are for an operator or a target project's virtual
environment. They do not authorize GitHub, package-host, or other non-OpenAI
network access inside this repository's offline Codex substrate. Installers may
contact their configured package index when build requirements or dependencies
are unavailable locally.

```bash
git clone https://github.com/jackryan67565/codex-backend-sdk.git
cd codex-backend-sdk
pip install -e .
```

### Install the 0.6.2 wheel in another project

Release artifacts are built locally into the Git-ignored `dist/` directory.
Install the `0.6.2` wheel directly into a target project's virtual environment:

```bash
uv pip install \
  --python /absolute/path/to/project/.venv/bin/python \
  /absolute/path/to/codex-backend-sdk/dist/codex_backend_sdk-0.6.2-py3-none-any.whl
```

Or, when that virtual environment includes pip:

```bash
/absolute/path/to/project/.venv/bin/python -m pip install \
  /absolute/path/to/codex-backend-sdk/dist/codex_backend_sdk-0.6.2-py3-none-any.whl
```

Because `dist/` is not tracked, a fresh clone may not contain the artifact.
Build from the tagged checkout before local distribution, and never substitute
different contents under the same version. For work after the checkpoint, use
an editable path install so the target environment follows the checkout:

```bash
uv pip install \
  --python /absolute/path/to/project/.venv/bin/python \
  --editable /absolute/path/to/codex-backend-sdk
```

Verify an installed copy without authenticating or contacting the backend:

```python
from inspect import signature
from codex_backend_sdk import OpenAI, __version__

print(__version__, signature(OpenAI).parameters["model"].default)
```

The target environment must satisfy `pydantic>=2.0` and `requests>=2.28`.
Package installation is outside the SDK runtime network contract.

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
    input="Explain quicksort in one paragraph.",
)
print(response.output_text)
```

The adapter does not inject a reasoning effort when one is omitted; effective
behavior remains backend-authoritative.

The non-streaming result requires one backend terminal `response.completed`,
`response.failed`, or `response.incomplete` event. For a completed response, a
nonempty terminal `response.output` is authoritative. If that field is absent
or empty, CBS preserves exact completed items from preceding
`response.output_item.done` events in the same stream. It does not reconstruct
output from text deltas or local request state, and it does not fill missing
model names, IDs, timestamps, statuses, usage, or request echoes.
The terminal event must be final; any later event makes non-streaming collection
fail with `APIResponseValidationError`.

### Raw Responses access

The pinned official-client-shaped raw wrapper exposes the submitted application
body, safe HTTP metadata, and the received body before parsing:

```python
raw = client.responses.with_raw_response.create(
    input="Hello",
    reasoning={"effort": "low"},
    store=False,
)

print(raw.status_code, raw.request_id)
submitted_body = raw.http_request.content
response = raw.parse()
```

`raw.http_request.content` (and the Requests-native `.body`) contains the exact
JSON bytes CBS submitted. The retained request deliberately omits
`Authorization` and `ChatGPT-Account-ID`,
and credential-bearing response headers such as cookies are removed. This is a
security difference from the official client; CBS does not expose a generic
transport or prepared authentication headers. Raw bodies may contain sensitive
model input or output and should not be logged.

HTTP status failures use the official error categories exported by the package,
including `BadRequestError`, `AuthenticationError`, `RateLimitError`, and
`InternalServerError`. Status errors preserve the backend error body and safe
request ID. Timeouts and connection failures raise `APITimeoutError` and
`APIConnectionError`.

The client default is `max_retries=2`, matching the pinned official client's
retry-count default for this path. Set `max_retries=0` when a caller requires at
most one transport attempt. Any automatic replay after an ambiguous transport
failure can duplicate a request the backend already accepted; CBS reports the
configured behavior and does not claim exactly-once delivery.

### Service tier

For `responses.create(...)` and `responses.parse(...)`, omit `service_tier` for
normal operation or pass `"default"` to request standard processing:

```python
response = client.responses.create(
    input="Hello",
    service_tier="default",
)
```

`"priority"` is also accepted as a best-effort request, but it does not
guarantee Fast processing on this undocumented backend. Inspect
`response.service_tier` for the processing mode the backend actually reported.
If the terminal event omits the field, the parsed value remains `None` rather
than echoing the requested value.

The official OpenAI Platform also documents `"auto"`, `"flex"`, and `"fast"`.
Live verification against this ChatGPT Codex Responses route on 2026-08-11
found that those explicit values returned HTTP 400, so this adapter rejects
them locally instead of silently translating or transmitting them. This
create/parse finding does not establish the compaction route's behavior.

Responses are caller-managed and stateless. The SDK does not create, list, or
resume ChatGPT UI conversations. Although `previous_response_id` remains in the
official-compatible method signature, this client rejects it locally: a live
probe using the SDK's mandatory `store=False` mode reached the backend and
received HTTP 400. The SDK does not emulate server-side continuation.

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
first = client.responses.create(
    input=history,
    reasoning={"context": "current_turn"},
    store=False,
)

history.extend(first.output)
history.append({"role": "user", "content": "What is my name?"})
second = client.responses.create(
    input=history,
    reasoning={"context": "all_turns"},
    store=False,
)
print(second.output_text)
```

Complete output replay preserves opaque encrypted reasoning items plus standard
assistant message `id`, `status`, and `phase` fields. This is the supported
repair-iteration primitive: the host can append a compact validator result and
request another structured response using the ordinary `responses.create(...)`
shape. CBS does not validate candidates, decide whether to retry, or claim that
replayed tokens were cached.

On a minimal `gpt-5.4` structured repair probe, the initial call reported 101
input, 81 output, 11 reasoning, and 0 cached tokens. The corrective manual
replay reported 225 input, 75 output, 8 reasoning, and 0 cached tokens. Both
used one transport attempt with `max_retries=0`. These measurements demonstrate
usage reporting, not token savings.

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
    input=history,
    instructions="Compact the caller-managed history.",
)

continued = client.responses.create(
    input=[
        *compacted.output,
        {"role": "user", "content": "Continue from the compacted state."},
    ],
    store=False,
)
```

Standalone compaction is stateless. Pass `compacted.output` forward unchanged
as the next request's context window, then append the new user or tool items.
Do not use `compacted.id` as `previous_response_id`; CBS does not support or
imply server-side linkage through the compaction response ID.

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
- honor the configured official `max_retries` semantics for model reads and
  Responses creation; `max_retries=0` permits at most one transport attempt;
- retry Responses only for connection/timeouts, HTTP 408, 409, 429, 5xx, or an
  explicit `x-should-retry: true`; compaction POSTs remain non-retryable;
- require finite positive timeouts of at most ten minutes, cap retry counts at
  five, and use the pinned official client's eight-second backoff cap;
- connect only to `chatgpt.com` over HTTPS on port 443.

URLs inside model input are payload data sent to OpenAI. This SDK does not fetch
them locally.

## Testing

The default suite is offline and must not load stored credentials or contact a
network service:

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest -q
```

Live integration tests are marked `live` and skipped by default. Run them only
after deliberately authorizing stored credential use, OpenAI network access,
and account quota consumption:

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest --live -q \
  tests/test_basic.py \
  tests/test_compaction.py \
  tests/test_conversation.py \
  tests/test_reasoning.py \
  tests/test_repair_iteration.py \
  tests/test_structured_output.py \
  tests/test_tools.py
```

Run the focused compaction smoke test with output capture disabled to print a
sanitized structural report. It reports field names, item types, ciphertext
lengths and hashes, retained-item counts, usage, and continuation success; it
never prints credentials, ciphertext, retained message text, or model output:

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest --live -q -s \
  tests/test_compaction.py
```

## Historical versions

Versions before 0.4 exposed broader ChatGPT, WHAM, upload, Platform, Realtime,
and credential-management helpers. They were removed from the current package
because a bearer accepted by an OpenAI hostname can still authorize data or
state outside the narrow agent task. The append-only [changelog](CHANGELOG.md)
records those historical features; they are not part of the current contract.

Current wire notes are in [docs/backend-api.md](docs/backend-api.md). Frozen
pre-0.4 audit material under `docs/audits/` is historical evidence only.
