# Agent-safe Codex backend wire notes

This document describes the maintained SDK contract. The backend is
undocumented and may change without notice. `README.md` remains the maintained
user entrypoint.

## Scope

The SDK exposes only stateless Codex Responses and model discovery. It does not
represent the complete ChatGPT backend and does not treat an OpenAI-owned
hostname as blanket authorization to call every route on that host.

The complete runtime allowlist is:

| Method | Scheme | Host | Path |
|---|---|---|---|
| `GET` | `https` | `chatgpt.com` | `/backend-api/codex/models` |
| `POST` | `https` | `chatgpt.com` | `/backend-api/codex/responses` |
| `POST` | `https` | `chatgpt.com` | `/backend-api/codex/responses/compact` |

Only port 443 is accepted. Redirects, URL user information, fragments,
environment proxies, caller base URLs, caller headers, and caller query
parameters are rejected or absent from the public surface.

Only idempotent model-catalog reads are retried. Responses and compaction POSTs
are never replayed automatically after a timeout, connection failure, 429, or
5xx response because the backend may already have accepted the first request.
Timeouts must be finite and positive, are capped at ten minutes, model-read
retries are capped at five, and each retry delay is capped at 60 seconds.

`codex_backend_sdk._network.validate_agent_sdk_request` enforces both method and
route before `requests` opens a connection.

## Authentication

The current client reads a pre-existing Codex credential cache and retains only:

- the ChatGPT OAuth access token;
- the ChatGPT account identifier required for backend routing.

It does not retain API keys, refresh tokens, ID tokens, email addresses, plan
details, or other account metadata in its credential object. The credential
object suppresses the access token from `repr`.

The SDK does not implement login, logout, refresh, token exchange, device code,
browser callbacks, or credential writes. A missing or stale access token must be
renewed by the trusted Codex CLI or ChatGPT desktop app.

The shared cache is opened read-only, must be a regular non-symlink file, and is
bounded to 1 MiB before parsing.

## Request headers

Every allowed backend request receives headers constructed internally:

```http
Authorization: Bearer <access_token>
ChatGPT-Account-ID: <account_id>
originator: <route-specific originator>
```

Model requests use `originator: codex_cli_rs`. Responses requests use
`originator: codex_backend_sdk`. Streaming Responses also use:

```http
Accept: text/event-stream
```

Callers cannot provide or override request headers.
After a request is sent, the transport removes `Authorization` and
`ChatGPT-Account-ID` from retained Requests request, response, and exception
objects before they can escape the SDK. The headers still exist on the wire;
this cleanup reduces accidental credential retention rather than changing
authentication.

## `GET /backend-api/codex/models`

**SDK methods:**

- `client.models.list()`
- `client.models.retrieve(model_id)`

The list request supplies the fixed upstream Codex client-version query used by
the implementation. The response is converted to `Model` objects and cached for
five minutes. `force_refresh=True` bypasses the local cache.

No account, quota, task, or conversation route is consulted during model
discovery.

## `POST /backend-api/codex/responses`

**SDK methods:**

- `client.responses.create(...)`
- `client.responses.parse(...)`

The backend streams SSE. A non-streaming SDK call collects those events into a
typed `Response`; `stream=True` returns the event iterator.

With the default client settings, the prepared payload includes:

```json
{
  "model": "gpt-5.6-sol",
  "instructions": "",
  "input": [],
  "tools": [],
  "tool_choice": "none",
  "parallel_tool_calls": false,
  "store": false,
  "stream": true,
  "include": []
}
```

`gpt-5.6-sol` is the checked-in client's local default. It is not evidence that
the undocumented backend exposes that model to every account or rollout.

Supported optional fields are normalized before transmission. Parameters known
to be unsupported by this backend raise locally rather than being silently
ignored.

### Service tier

`responses.create(...)` and `responses.parse(...)` accept omitted
`service_tier`, `"default"`, or `"priority"`. Omission leaves the field out of
the JSON body. Explicit values are sent only as a JSON body field; they do not
alter authentication, account-routing, originator, or SSE headers.

A six-case live probe on 2026-08-11 using `gpt-5.4` observed:

| Request | HTTP outcome | Raw terminal tier |
|---|---|---|
| omitted | 200 completed | `default` |
| `default` | 200 completed | `default` |
| `priority` | 200 completed | `default` |
| `auto` | 400, no terminal SSE event | none |
| `flex` | 400, no terminal SSE event | none |
| `fast` | 400, no terminal SSE event | none |

This is evidence for the undocumented ChatGPT route, not a claim about the
official Platform API or every account rollout. `"priority"` is therefore a
best-effort request, and the raw terminal response remains authoritative. The
collector returns `None` when that response omits `service_tier`; it never
substitutes the locally requested value.

### Stateless history

The client does not use a ChatGPT conversation ID or a Codex Cloud task ID.
`previous_response_id` remains an official keyword in the public signature but
raises locally. A 2026-08-11 probe that supplied the ID of a completed
`store=false` response received HTTP 400 before any SSE terminal event. The
SDK's `store=true` restriction was not relaxed to test retained server state.

The supported continuation is official stateless replay: the caller supplies
prior input, every item from `response.output`, and the next user message in a
new `input` list. Non-message output items, including opaque reasoning items,
pass through unchanged. Assistant messages retain `id`, `status`, `phase`,
role, and content.

### Reasoning context and structured repair

Live `gpt-5.4` requests verified `reasoning.context="current_turn"` on an
initial structured request and `reasoning.context="all_turns"` on a structured
manual-replay follow-up. Each raw terminal event reported the corresponding
effective context. The initial `store=false` response also contained an opaque
reasoning output item with `encrypted_content` and an assistant message with
`phase="final_answer"`.

The adapter types the returned reasoning object, so callers can inspect
`response.reasoning.context`. It accepts the two verified explicit values and
rejects unverified explicit context values before transport. If the backend
omits the response field, the SDK returns `None` rather than copying the request
and implying reasoning reuse.

Structured output remained valid on both the initial and corrective calls. CBS
only carries the official request and response shapes; admission logic,
validator feedback, retry decisions, and stopping policy belong to the caller.

### Storage, usage, and retries

Every Responses payload includes `store: false`; `store=true` raises before
transport. The SDK does not persist response IDs, output history, or validator
feedback, and it exposes no response retrieval or deletion route. Official
OpenAI documentation says `store=false` disables the Platform's default 30-day
response-object storage. This undocumented ChatGPT route received the field,
but the SDK cannot independently audit provider-side operational retention and
does not claim that all service logs are absent.

The same live repair probe observed raw and parsed usage values:

| Call | Input | Output | Reasoning | Cached |
|---|---:|---:|---:|---:|
| Initial structured response | 101 | 81 | 11 | 0 |
| Corrective manual replay | 225 | 75 | 8 | 0 |

Both raw terminal events explicitly contained cached-input and reasoning-token
detail fields, and the parsed response matched them. Zero cached tokens is a
measurement for these short prompts, not evidence that replay is discounted.
The four instrumented capability-probe POSTs each recorded exactly one
transport attempt with `max_retries=0`. The patched two-call smoke test also
used `max_retries=0`; Responses POSTs remain non-retryable even when the client
is configured with a higher model-read retry count.

### Tools

Only `{"type": "function", ...}` tools are accepted. Each function requires a
non-empty name; `parameters`, when supplied, must be a JSON-schema object.

Allowed choices are `auto`, `none`, `required`, or an explicit function choice
whose name exists in the supplied tool list. Hosted web-search, computer-use,
MCP, and other backend-executed tool types are rejected before transport.

The SDK does not execute returned function calls.

## `POST /backend-api/codex/responses/compact`

**SDK method:** `client.responses.compact(...)`

Compaction accepts caller-supplied history and returns a typed compacted
response. It shares the function-only tool restriction. It does not read any
ChatGPT sidebar, account memory, or Codex Cloud task history.

The returned `output` list is the canonical stateless continuation carrier.
Callers pass it unchanged as the beginning of a later `responses.create(...)`
input and append the next user or tool items. The returned `id` remains typed
response metadata; CBS does not treat it as a `previous_response_id` linkage
token or claim server-side state reuse.

The create-route service-tier validation above is intentionally not applied to
compaction pending separate live verification of this endpoint.

`tests/test_compaction.py` contains the focused live smoke test for the compact
route. It examines the typed response's complete top-level field set and output
item structure, confirms an encrypted compaction item is present, then replays
the canonical window through `responses.create(...)`. Its printed report is
structural only: authenticated plaintext, ciphertext, response text, and
credentials are never emitted. Run it only with the repository's explicit
`--live` credential/network/quota gate.

## Intentionally removed routes and capabilities

Earlier versions recorded or exposed broader observed endpoints. Version 0.4
removed their implementations and transport reachability from the agent-safe
package, including:

- ChatGPT memories and user customization;
- WHAM usage, requirements, tasks, turns, sibling turns, and environments;
- rate-limit reset-credit listing and consumption;
- ChatGPT file creation, signed uploads, and upload finalization;
- ChatGPT batch transcription;
- Codex image generation and editing;
- Codex Realtime call creation;
- OpenAI Platform embeddings and Realtime WebSocket connection material;
- OAuth authorization, refresh, and ID-token-to-API-key exchange;
- generic raw ChatGPT, WHAM, Platform, or signed-upload transport helpers.

These removals are security boundaries in the maintained SDK contract, not
claims that the upstream services ceased to exist. Historical behavior remains
available through Git history and the append-only changelog. Frozen files under
`docs/audits/` describe their pre-0.4 snapshot and must not be treated as current
authority.

## Threat-boundary note

The method/route allowlist constrains SDK-owned connections. It does not prevent
arbitrary code in the same OS process from importing another HTTP library or
reading files granted by the surrounding sandbox. Production agent hosts should
keep credentials in a trusted broker and expose only the narrow operations the
agent is authorized to invoke.
