---
name: codex-backend-sdk
description: Use codex-backend-sdk as the available OpenAI-Python-shaped stand-in for supported Responses and Models work through an existing ChatGPT Codex login. Apply when a Python harness needs model calls, structured output, streaming, function tools, raw Responses access, stateless replay, retries, installation help, or CBS capability guidance. Do not use it as evidence of full OpenAI Platform API parity or for unsupported ChatGPT surfaces.
---

# Codex Backend SDK

CBS is a tool agents can use in place of the official OpenAI Python client for
the subset it supports. It keeps the familiar `OpenAI()` and
`client.responses.create(...)` shapes while using the user's existing ChatGPT
Codex authentication, backend routes, and usage system. It is unofficial and is
not a stand-in for unsupported OpenAI Platform endpoints.

## Establish the contract

Before integrating or answering capability questions, read the maintained
[README](../../../README.md) and
[compatibility contract](../../../docs/openai-sdk-compatibility.md). Read
[backend wire notes](../../../docs/backend-api.md) only when transport details
matter. Treat the checked-in source as authoritative for editable installs;
inspect a wheel before claiming it matches the worktree.

The current compatibility baseline is `openai==2.46.0`, and the default model
is exactly `gpt-5.6-sol`. Callers may override the model at client or request
scope; the default does not prove account availability.

For Astra work, select `model="gpt-6-astra"` explicitly. CBS preserves that
model ID and `reasoning={"effort": "max"}` on the supported Responses path and
can parse a backend-reported `max` effort. This is an offline-verified adapter
capability, not proof that the user's ChatGPT account or current backend rollout
will serve Astra. Do not infer availability from catalog inclusion or omission.

## Resolve the installed CBS before use

Loading this skill does not select or update a Python package. A target project
uses whichever `codex_backend_sdk` its actual interpreter resolves first.
Before relying on a recently added capability:

1. Identify the interpreter from the target project's own environment and
   instructions. Do not assume that `.venv/bin/python` is the right interpreter.
2. Without authenticating, inspect the installed package version and source:

   ```bash
   /absolute/path/to/python -c 'import codex_backend_sdk as c; print(c.__version__); print(c.__file__)'
   ```

   Treat an import failure as “not installed,” not as permission to install it.
3. Read the desired local version from this CBS checkout's `pyproject.toml`.
   Do not infer the package version from this skill, a Git tag, or an ignored
   artifact filename.
4. Compare both version and import path. An editable installation resolves into
   the checkout and follows its source; a wheel installation remains frozen at
   the installed version until it is replaced. An unexpected global or PyPI
   path is neither one.

If the target environment is missing or stale and its project instructions
permit a local dependency change, use that project's dependency convention.
For a checkpointed wheel, first verify the matching
`dist/SHA256SUMS-<version>.txt`, then reinstall the exact local artifact:

```bash
uv pip install \
  --python /absolute/path/to/project/python \
  --offline --reinstall --no-deps \
  /home/nick/code/codex-backend-sdk/dist/codex_backend_sdk-<version>-py3-none-any.whl
```

Use `--no-deps` only after confirming the target already satisfies CBS's
runtime dependencies. If dependencies are missing, stop rather than contacting
a package index unless the user or target project's instructions authorize that
network access. For an editable integration, reinstall the local checkout with
the target project's normal editable-install command so package metadata stays
aligned with the source.

After any install or upgrade, rerun the version-and-path probe with the same
interpreter. Do not authenticate or make a model call merely to verify package
selection. Report the resolved version, import path, installation mode, and any
reason an intended upgrade was not performed.

## Use the official-shaped path

Prefer the standard client surface:

```python
from codex_backend_sdk import OpenAI

with OpenAI().authenticate() as client:
    response = client.responses.create(
        input="Answer briefly.",
        store=False,
    )
```

Use `responses.parse(...)` for Pydantic structured output,
`responses.create(stream=True)` for event iteration, and
`responses.with_raw_response.create(...)` when the caller needs the exact
submitted application-body bytes, safe HTTP metadata, request ID, or received
body before `.parse()`.

Keep harness-specific validation, experiment policy, accounting, and custody
outside CBS. Do not introduce proprietary `prepare`/`send`, continuation, or
receipt abstractions when the official-shaped call is sufficient.

## Preserve the important differences

- Authentication is the read-only `.authenticate()` step over the existing
  Codex login. Never read, print, copy, refresh, or retain the credential cache
  yourself.
- CBS supports only its documented Responses, compaction, and Models subset.
  Unsupported parameters must fail explicitly rather than being dropped or
  emulated.
- `store=False` is required. Stateful `previous_response_id` continuation is
  unsupported; use standard stateless replay with prior input and complete
  prior `response.output` items.
- `max_output_tokens` remains an explicit local error until the backend has a
  verified equivalent.
- Top-level Responses `input` must be a string or a list of valid items. Do not
  pass a bare mapping; list entries need message role/content or a CBS-supported
  `message`, `reasoning`, `function_call`, `function_call_output`, or
  `compaction` type.
- Only caller-executed function tools are allowed. Hosted web search, computer
  use, MCP, and other backend-executed tools are outside this SDK.
- The model catalog is enumeration, not a Responses support oracle. Submit an
  explicitly requested model and let the Responses backend accept or reject it.
- Parsed fields come from the backend stream. A nonempty terminal output wins;
  if a completed terminal event omits output or carries an empty list, CBS uses
  exact preceding `response.output_item.done` items. Missing IDs, model names,
  timestamps, status, usage, and other fields remain unknown; do not reconstruct
  output from deltas or local request state.

## Handle transport deliberately

Set `max_retries=0` when at most one transport attempt is required. Higher
configured values enable bounded official-style retries and cannot guarantee
exactly-once delivery after an ambiguous failure.

The raw wrapper exposes `raw.http_request.content`, `raw.request_id`, safe
headers, `raw.content`, and `raw.parse()`. Authentication/account headers and
credential-bearing response headers are removed. Raw request or response bodies
may still contain sensitive user or model content, so do not log them.

If a non-streaming body is interrupted before the raw wrapper returns, handle
the resulting `APIConnectionError`. Its `.request` remains the sanitized exact
application request and `.body` remains `None`; CBS may also provide
`status_code`, safe `request_id` and `response_headers`,
`partial_response_body`, `response_body_complete=False`, and `retries_taken`.
Treat partial bytes as sensitive, incomplete custody evidence only. Never parse
them as a Response or infer output, usage, terminality, completion, or whether
the backend expended work. Streaming iterator behavior is separate and remains
incremental.

CBS-owned runtime connections are limited to the three exact `chatgpt.com`
Codex routes documented by the project. Do not add a base URL, caller headers,
proxies, redirects, new routes, or new domains as part of an integration.

## Verify without surprise side effects

Prefer offline mock-transport tests. Installing missing dependencies may require
separate package-host authorization. A live call requires explicit user
authorization for shared credential use, OpenAI network access, and possible
quota consumption; keep live prompts bounded and never print authenticated
bodies.

When modifying CBS itself, follow the repository `AGENTS.md`, run the offline
suite, inspect the route scan when relevant, and commit and push the coherent
change. When merely using CBS from another project, preserve that project's
own instructions and dependency conventions.
