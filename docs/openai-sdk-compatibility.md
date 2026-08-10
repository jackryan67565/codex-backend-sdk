# OpenAI Python SDK compatibility

## Compatibility target

This package is a drop-in-oriented adapter for the subset of `openai-python`
that the ChatGPT Codex backend and this repository's agent-safe policy can both
support. The primary import and call pattern is:

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()
response = client.responses.create(model="gpt-5.4", input="Hello")
```

The public compatibility baseline was checked on 2026-08-09 against the locally
installed `openai` 2.46.0 package and the official [Responses create
reference](https://developers.openai.com/api/reference/resources/responses/methods/create).
The official reference demonstrates the same `OpenAI()` client,
`client.responses.create(...)` call, `Response` shape, and iterator-based
`stream=True` pattern used as this adapter's compatibility anchor.

## Supported drop-in subset

- `OpenAI` construction with the adapter's safe local options, followed by the
  adapter-specific read-only `.authenticate()` step.
- `client.responses.create(...)` for non-streaming and `stream=True` calls.
- `client.responses.parse(...)` for Pydantic structured output.
- `client.responses.compact(...)` for the approved Codex compact route.
- `client.models.list()` and `client.models.retrieve(...)`.
- OpenAI-style Pydantic helpers such as `model_dump()`, `to_dict()`, and
  `to_json()`, plus familiar response and SSE event field names.
- Explicit local rejection of official parameters that the Codex backend does
  not support. `max_output_tokens` must raise and must never be silently dropped
  or reinterpreted.

## Intentional incompatibilities

These differences are part of the security contract rather than accidental
API drift:

- Authentication reuses the current Codex login read-only. The constructor does
  not accept API keys, organization/project credentials, custom HTTP clients,
  or custom base URLs.
- Only the approved Codex Responses, compact, and model-list routes exist.
- Caller-provided headers, query parameters, extra bodies, redirects, proxies,
  and raw transport access are unavailable.
- Hosted tools and all resources outside the narrow Responses/Models subset are
  rejected or absent.
- Stateful Platform response chaining is unavailable; callers carry prior input
  and output items themselves.

## Current parity snapshot

A signature comparison with locally installed `openai` 2.46.0 found these
remaining gaps. They are compatibility backlog, not permission to add unrelated
public APIs:

- The constructors share `timeout` and `max_retries`. The official credential,
  base-URL, header/query, WebSocket, and custom-client parameters are
  intentionally unavailable; this adapter instead adds `model`, `instructions`,
  and `retry_base_delay` defaults.
- `responses.create(...)` shares every currently exposed parameter name with the
  official method. The official method additionally has `moderation`,
  `prompt_cache_options`, and the intentionally unsafe `extra_headers`,
  `extra_query`, and `extra_body` transport escapes.
- `responses.parse(...)` also lacks the newer official `stream` and `verbosity`
  keywords in addition to the create-method gaps above.
- `responses.compact(...)` needs a focused compatibility pass: the official
  method includes `previous_response_id`, prompt-cache options/retention,
  `timeout`, and transport escapes, while this adapter currently exposes several
  backend-observed fields that are not in the official 2.46.0 signature.
- The official convenience `responses.stream(...)` manager and broader response
  lifecycle methods are not implemented. Ordinary `create(stream=True)` event
  iteration is supported.

Close these gaps incrementally with focused tests. Unsafe transport or credential
arguments may be accepted only to produce an explicit local unsupported error;
they must never weaken the agent-safe boundary.

## Compatibility rules for changes

1. Keep `OpenAI` as the primary documented name. `CodexClient` may remain an
   alias for existing callers, but must not replace the standard name in normal
   examples.
2. Prefer official resource names, methods, keyword names, model fields, stream
   event fields, and return shapes whenever the backend can support them.
3. When an official parameter cannot be honored, accept it only to raise an
   explicit local unsupported error. Never silently drop or reinterpret it.
4. Do not add an alternative public lifecycle such as `prepare`/`send`, custody
   receipts, raw-event sinks, or capability manifests unless the user explicitly
   approves a non-standard extension. Harness-specific evidence and accounting
   belong in the harness layer.
5. Add compatibility regression tests for any changed public signature, return
   model, or streaming behavior. Compare against a pinned `openai-python`
   version during an intentional compatibility update; do not make the official
   package a runtime dependency merely for parity checks.
