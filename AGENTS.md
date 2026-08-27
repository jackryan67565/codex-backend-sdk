# Codex repository guidance

## Purpose and recovery order

This repository is an agent-safe, unofficial Python client for the undocumented ChatGPT Codex Responses backend. It is not an OpenAI-supported SDK. Start with this file, then read `README.md`, `pyproject.toml`, and only the source or focused backend notes needed for the task. Treat `CHANGELOG.md` and `docs/audits/` as history/evidence, not current authority.

## Current model default

- The checked-in `OpenAI()` client defaults to the exact `gpt-5.6-sol` model ID. Omitting `model` uses that default; a constructor-level or request-level `model=` explicitly overrides it. The local default is not proof that every ChatGPT account or rollout can serve the model.
- Keep dated `gpt-5.4` probes, measurements, and their pinned live test unchanged unless a newly authorized live run replaces that evidence. They describe observed history, not the current default.
- Treat the checked-in source as authoritative during unreleased work. `dist/` is ignored and may be absent or older than the worktree; never tell another agent that a wheel contains the current default without inspecting or rebuilding a new versioned checkpoint.

## Working agreements

- After each completed, coherent change, inspect the intended diff, create a descriptive Git commit, and push the current branch before handoff. Do not batch unrelated work or stage changes outside the current task; if repository state, authentication, or remote policy prevents a safe commit or push, report that explicitly.
- Before pushing, verify that `origin` is still the expected repository. Pushes to that configured origin are an explicit development-workflow exception to the offline project substrate; they do not relax the SDK runtime egress boundary or authorize fetch, pull, or other non-OpenAI network access.
- When answering questions about this SDK's features, routes, or behavior, read the project documentation and implementation first. Do not substitute official OpenAI platform documentation for this repository's documented, unofficial backend surface; consult external docs only when the project docs leave a relevant gap or the user explicitly asks for an upstream comparison.
- Preserve the agent-safe runtime boundary. SDK-owned requests must pass `codex_backend_sdk._network.validate_agent_sdk_request`, including an exact method, host, and path match.
- The only runtime routes are `GET https://chatgpt.com/backend-api/codex/models`, `POST https://chatgpt.com/backend-api/codex/responses`, and `POST https://chatgpt.com/backend-api/codex/responses/compact` over TLS on port 443.
- Do not reintroduce ChatGPT account data, conversations, memories, customization, WHAM, Codex Cloud history, quota mutation, uploads, audio, images, embeddings, Realtime, API-key material, OAuth/login/refresh, generic raw transports beyond the sanitized official-compatible `responses.with_raw_response.create(...)` wrapper, hosted tools, or generic OpenAI-host access without explicit user approval and a new security review.
- Do not add a new network domain or route, proxy support, redirect following, caller-configurable base URL, caller headers/query, remote MCP server, telemetry exporter, webhook, or package registry without explicit user approval and focused policy tests.
- The repository MCP overlay enables only `openaiDeveloperDocs` at `https://developers.openai.com/mcp`; inherited Node REPL, Playwright, and Figma entries are disabled for this project. Re-audit `codex mcp list` if user-level configuration changes.
- Keep `requests.Session.trust_env = False` for SDK-owned sessions so environment proxy variables cannot reroute credentials. Keep redirects disabled; validate every destination before every request.
- Authentication is read-only and non-interactive. Credential state may retain only the access token and account ID from the shared Codex cache. It must not retain API keys or refresh tokens, start login/browser/loopback flows, refresh credentials, or write the cache.
- URLs placed in request payloads are sent to OpenAI but are not fetched locally. Preserve that distinction in code and documentation.
- Never read, print, copy, or commit `~/.codex/auth.json`, tokens, API keys, signed URLs, or authenticated response bodies.
- Never expose credentials or prepared authentication headers through a public method, return value, dataclass representation, or package export.
- Only caller-executed `function` tools are allowed. The SDK must reject hosted web-search, computer-use, MCP, or other backend-executed tool types before transport.
- Preserve OpenAI Python SDK compatibility across the supported Responses and Models subset. Keep `OpenAI` as the primary documented client name, prefer official method names, keyword names, response fields, event fields, and return shapes, and do not add a competing public request lifecycle such as `prepare`/`send`, receipts, custody sinks, or capability manifests without explicit user approval.
- The exact compatibility baseline is the development pin `openai==2.46.0`. Responses creation honors the bounded official retry conditions and configured retry count; `max_retries=0` must perform at most one transport attempt. Compaction POSTs remain non-retryable. Never expose bearer/account headers through the raw or error paths.
- Safety restrictions take precedence over breadth. Official SDK parameters that the Codex backend or agent-safe boundary cannot honor must remain explicit local errors; never silently drop, forward, or reinterpret them. In particular, keep raising for `max_output_tokens` until the backend has a verified equivalent.
- Keep public behavior typed and synchronous unless the existing Responses contract requires streaming. Prefer focused changes over broad rewrites.

## Verification

Use the existing environment; do not install or update packages unless the user explicitly authorizes non-OpenAI package-host access.

The default suite is offline, skips every `live` test, and must not read stored authentication or contact a network service:

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest -q
```

The live test cases in `test_basic.py`, `test_compaction.py`, `test_conversation.py`, `test_reasoning.py`, `test_repair_iteration.py`, `test_structured_output.py`, and `test_tools.py` authenticate and contact live services through the shared fixture or a test-owned client. They remain skipped without `--live`. Run them only when the user explicitly requests live integration verification and authorizes credential use, network access, and possible quota consumption.

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

For network-boundary changes, also run:

```bash
rg -n 'https?://|wss?://' codex_backend_sdk
```

Every connection-capable match must be one of the three exact routes above. JWT claim names and payload-only URLs are data, not connections. Do not equate a passing source scan with operating-system egress enforcement.

## Documentation

- `README.md` is the maintained user entrypoint.
- `docs/openai-sdk-compatibility.md` defines the supported drop-in subset and intentional incompatibilities.
- `docs/backend-api.md` records current reverse-engineering notes; mark superseded observations clearly.
- `security_best_practices_report.md` records the current agent-safety review and deployment boundary.
- `CHANGELOG.md` is append-only chronology.
- `docs/audits/cold-substrate-sweep-v1.md` is a frozen pre-repair audit and must not be rewritten.
- When the model default changes, keep the constructor, README quickstart, compatibility contract, wire-payload example, tests, and changelog aligned. Do not mechanically rewrite dated backend evidence.
