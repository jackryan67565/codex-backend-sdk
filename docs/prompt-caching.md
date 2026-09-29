# Prompt caching

CBS exposes prompt caching only through the ordinary OpenAI-shaped Responses
interface. It does not implement a cache, cache session, or CBS-specific cache
API.

## Compatibility boundary

| Surface | CBS behavior | Backend status |
|---|---|---|
| `prompt_cache_key` | Preserved in the JSON request body | Existing Codex field; a key groups accounting but does not guarantee a hit |
| `prompt_cache_options` | Preserved in the JSON request body | Acceptance and effective behavior on the undocumented backend require a separately authorized live test |
| `prompt_cache_options.mode` | Preserves `implicit` or `explicit` | No local emulation |
| `prompt_cache_options.ttl` | Preserves the current `30m` value | No local retention claim |
| `prompt_cache_options.prewarm` | Preserved when supplied, matching the current API field name | Backend support is unverified; rejection remains a typed HTTP error |
| `prompt_cache_breakpoint` | Preserved on content blocks without moving or rewriting them | The backend decides eligibility and writes |
| `usage.input_tokens_details.cached_tokens` | Parsed from the terminal backend Response | Missing remains `None`; zero means the backend reported zero |
| `usage.input_tokens_details.cache_write_tokens` | Parsed from the terminal backend Response | Missing remains `None`; zero means the backend reported zero |
| Response cache key/options | Parsed only when the terminal backend Response reports them | CBS does not echo request values into the Response |
| `prompt_cache_retention` | Rejected locally | The Codex route previously returned HTTP 400 for both official values |

The existing `responses.compact(...)` route also carries
`prompt_cache_key` and `prompt_cache_options` under their official names. Its
effective cache behavior remains separately unverified.

The exact differential baseline remains `openai==2.46.0`. That version types
`prompt_cache_options.mode` and `.ttl`; the current official prompt-caching
guide additionally documents `prewarm`. CBS preserves the standard options
mapping instead of creating a parallel abstraction. A backend HTTP rejection is
returned through the existing official-style error taxonomy with its safe
request ID and error body.

The official Prompt Caching Dashboard and Prompt Cache Diagnostics tool are
separate Platform diagnostics, not response fields. CBS exposes the terminal
usage diagnostics above but does not add another route to reach those tools.

## Ordinary Responses usage

Put stable material first and changing input last. An explicit breakpoint is a
field on a supported content block; top-level `instructions` cannot carry one.

```python
from codex_backend_sdk import OpenAI

client = OpenAI(max_retries=0).authenticate()
stable_reference = "...stable instructions and reference material..."

response = client.responses.create(
    input=[
        {
            "role": "developer",
            "content": [{
                "type": "input_text",
                "text": stable_reference,
                "prompt_cache_breakpoint": {"mode": "explicit"},
            }],
        },
        {"role": "user", "content": "Changing case input"},
    ],
    prompt_cache_key="tma:stable-reference:v1",
    prompt_cache_options={"mode": "explicit", "ttl": "30m"},
    store=False,
)

details = response.usage.input_tokens_details
ordinary_input = (
    response.usage.input_tokens
    - details.cached_tokens
    - details.cache_write_tokens
)
```

The complete runnable form is
[`examples/prompt_caching.py`](../examples/prompt_caching.py). It intentionally
uses the same model, settings, stable material, message structure, cache key,
and breakpoint for both calls; only the trailing user input changes.

## Prompt layout and TMA

The reported TMA aggregate—2,629,048 input tokens, 212,480 cached tokens, or
8.1%—does not by itself identify an SDK defect. CBS now proves offline that the
standard cache fields and exact ordered input items reach its prepared JSON.
TMA must independently make the rendered prefix reusable:

- place stable instructions, tool definitions, schemas, examples, and reference
  material before case-specific metadata;
- keep the stable prefix byte-for-byte and structurally stable, including
  message/content boundaries, tool ordering, schemas, model, reasoning effort,
  and output configuration;
- append new conversation items instead of rewriting or extending earlier
  messages when possible;
- place an explicit content-block breakpoint immediately after the stable
  material when later messages change;
- reuse a stable cache key for the same accounting group and version it when
  the stable material changes;
- remember that GPT-5.6 and later currently require at least 1,024 visible input
  tokens before a prefix is cacheable;
- expect the first eligible request to write rather than read, and account for
  compaction or reconstructed history changing the prefix.

For current API accounting, ordinary uncached input is
`input_tokens - cached_tokens - cache_write_tokens`. Cache-write tokens are a
separate billed category, not an additional count on top of `input_tokens`.

## Bounded live smoke-test proposal

No live request was made for this implementation. A separately authorized test
should use three small Responses calls and stop on the first transport or HTTP
failure:

1. Use one stable developer content block of just over 1,024 visible tokens,
   one explicit breakpoint, one cache key, fixed model/reasoning/tools/text
   settings, `store=False`, and `max_retries=0`.
2. Send a short suffix A once to observe the initial write.
3. Send different short suffixes B and C with the exact same prefix to measure
   reads without repeatedly forcing a write.

For each call, retain the sanitized prepared application body, hash the stable
prefix, and record one-attempt count, HTTP outcome, terminal model,
`input_tokens`, `cached_tokens`, `cache_write_tokens`, ordinary uncached input,
time to first SSE event, and total latency. The acceptance criterion is not a
guaranteed hit: it is truthful field preservation plus backend-reported writes
or reads when they occur. A 400 for `prompt_cache_options` establishes a backend
compatibility gap and must not be retried or simulated locally.
