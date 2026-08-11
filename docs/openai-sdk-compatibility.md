# OpenAI Python SDK compatibility

## Compatibility target

This package is a drop-in-oriented adapter for the subset of `openai-python`
that the ChatGPT Codex backend and this repository's agent-safe policy can both
support. The primary import and call pattern is:

```python
from codex_backend_sdk import OpenAI

client = OpenAI().authenticate()
response = client.responses.create(input="Hello")
```

The adapter's client default is the explicit `gpt-5.6-sol` model ID. Supplying
`model=` at client construction or on an individual request continues to
override that default.

The public compatibility baseline was checked on 2026-08-09 against the locally
installed `openai` 2.46.0 package and the official [Responses create
reference](https://developers.openai.com/api/reference/resources/responses/methods/create).
The official reference demonstrates the same `OpenAI()` client,
`client.responses.create(...)` call, `Response` shape, and iterator-based
`stream=True` pattern used as this adapter's compatibility anchor.

## Supported drop-in subset

- `OpenAI` construction with the adapter's safe local options, followed by the
  adapter-specific read-only `.authenticate()` step. The client supports
  `close()` and context-manager cleanup for its owned HTTP session.
- `client.responses.create(...)` for non-streaming and `stream=True` calls.
- `client.responses.parse(...)` for Pydantic structured output.
- `client.responses.compact(...)` for the approved Codex compact route.
- `client.models.list()` and `client.models.retrieve(...)`.
- OpenAI-style Pydantic helpers such as `model_dump()`, `to_dict()`, and
  `to_json()`, plus familiar response and SSE event field names.
- Explicit local rejection of official parameters that the Codex backend does
  not support. `max_output_tokens` must raise and must never be silently dropped
  or reinterpreted.

### Service-tier subset

Official OpenAI documentation describes `auto`, `default`, `flex`, and Fast
mode through either `fast` or `priority`. The undocumented ChatGPT Codex route
does not currently expose the same subset:

| Value | Official Platform contract | Verified Codex Responses behavior |
|---|---|---|
| omitted | Behaves as project-configured `auto` | Accepted; observed terminal tier `default` |
| `auto` | Project-configured tier | HTTP 400; rejected locally by this adapter |
| `default` | Standard processing | Accepted; observed terminal tier `default` |
| `flex` | Flex processing | HTTP 400; rejected locally by this adapter |
| `priority` | Fast-mode request alias | Accepted, but observed terminal tier `default` |
| `fast` | Fast-mode request | HTTP 400; rejected locally by this adapter |

The Codex observations are one minimal live request per value on 2026-08-11
using `gpt-5.4`; they are not Platform guarantees or latency benchmarks.
`responses.create(...)` and `responses.parse(...)` therefore type and accept
only `default` and `priority`, plus omission. They never translate an unsupported
value. A returned `Response.service_tier` reflects only the terminal backend
event and remains `None` when that event omits the field.

This matrix does not cover `responses.compact(...)`; its existing field remains
unchanged pending separate endpoint verification.

### Repair-iteration capability matrix

OpenAI's official [conversation-state
guide](https://developers.openai.com/api/docs/guides/conversation-state) defines
both stored `previous_response_id` chaining and stateless manual replay. The
official [reasoning
guide](https://developers.openai.com/api/docs/guides/reasoning#preserve-reasoning-across-calls)
requires complete output replay when `store=false`, including encrypted
reasoning items and assistant phase.

The following Codex observations are from a bounded live `gpt-5.4` probe on
2026-08-11. Each POST used `store=false`, `max_retries=0`, and exactly one
transport attempt.

| Capability | Codex result | Public contract |
|---|---|---|
| `previous_response_id` | HTTP 400 with a prior `store=false` response ID; no terminal SSE event | Keyword remains in `responses.create(...)` but raises locally; no stateful emulation |
| Prior `response.output` items in `input` | Supported; replay included reasoning and assistant message items | Use ordinary `input=[*previous_input, *previous.output, feedback]` |
| Structured output on follow-up | Supported; corrective output validated against the same strict JSON schema | Use ordinary `text.format` or `responses.parse(...)` |
| `reasoning.context` | `current_turn` and `all_turns` accepted and reported as effective raw response values | Use the standard `reasoning` parameter and inspect typed `response.reasoning.context` |
| `store=false` continuation | Supported only through complete manual replay | No server-state or response-ID reuse claim |
| Cached-input usage | Raw detail field present; measured 0 on both short calls | Exposed as `usage.input_tokens_details.cached_tokens` |
| Reasoning-token usage | Raw detail field present; measured 11 initially and 8 on correction | Exposed as `usage.output_tokens_details.reasoning_tokens` |

The initial call measured 101 input / 81 output / 182 total tokens. The
corrective replay measured 225 input / 75 output / 300 total tokens. This sample
showed no cached-input discount, so CBS must not advertise token savings.
Provider-side caching may vary with prompt length and backend policy; the raw
usage response is authoritative.

Every request carried `store=false`. The SDK neither stores the repair history
nor exposes retrieval/deletion. Official Platform documentation describes
response objects as stored for 30 days by default unless `store=false`; this
adapter can confirm the wire request but cannot independently prove all
operational retention behavior of the undocumented ChatGPT backend.

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
- The official Platform's broader service-tier vocabulary is intentionally
  narrowed to the create-route values verified above.
- Explicit `reasoning.context="auto"` remains unverified on this backend;
  omission is available, while the verified `current_turn` and `all_turns`
  values are supported.

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
6. Keep repair validation, retry/stopping policy, experiment orchestration, and
   custody records outside CBS. Do not add a proprietary continuation method.
