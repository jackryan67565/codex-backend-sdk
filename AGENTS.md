# Codex repository guidance

## Purpose and recovery order

This repository is an agent-safe, unofficial Python client for the undocumented ChatGPT Codex Responses backend. It is not an OpenAI-supported SDK. Start with this file, then read `README.md`, `pyproject.toml`, and only the source or focused backend notes needed for the task. Treat `CHANGELOG.md` and `docs/audits/` as history/evidence, not current authority.

## Working agreements

- After each completed, coherent change, inspect the intended diff, create a descriptive Git commit, and push the current branch before handoff. Do not batch unrelated work or stage changes outside the current task; if repository state, authentication, or remote policy prevents a safe commit or push, report that explicitly.
- Before pushing, verify that `origin` is still the expected repository. Pushes to that configured origin are an explicit development-workflow exception to the offline project substrate; they do not relax the SDK runtime egress boundary or authorize fetch, pull, or other non-OpenAI network access.
- When answering questions about this SDK's features, routes, or behavior, read the project documentation and implementation first. Do not substitute official OpenAI platform documentation for this repository's documented, unofficial backend surface; consult external docs only when the project docs leave a relevant gap or the user explicitly asks for an upstream comparison.
- Preserve the agent-safe runtime boundary. SDK-owned requests must pass `codex_backend_sdk._network.validate_agent_sdk_request`, including an exact method, host, and path match.
- The only runtime routes are `GET https://chatgpt.com/backend-api/codex/models`, `POST https://chatgpt.com/backend-api/codex/responses`, and `POST https://chatgpt.com/backend-api/codex/responses/compact` over TLS on port 443.
- Do not reintroduce ChatGPT account data, conversations, memories, customization, WHAM, Codex Cloud history, quota mutation, uploads, audio, images, embeddings, Realtime, API-key material, OAuth/login/refresh, raw transports, hosted tools, or generic OpenAI-host access without explicit user approval and a new security review.
- Do not add a new network domain or route, proxy support, redirect following, caller-configurable base URL, caller headers/query, remote MCP server, telemetry exporter, webhook, or package registry without explicit user approval and focused policy tests.
- The repository MCP overlay enables only `openaiDeveloperDocs` at `https://developers.openai.com/mcp`; inherited Node REPL, Playwright, and Figma entries are disabled for this project. Re-audit `codex mcp list` if user-level configuration changes.
- Keep `requests.Session.trust_env = False` for SDK-owned sessions so environment proxy variables cannot reroute credentials. Keep redirects disabled; validate every destination before every request.
- Authentication is read-only and non-interactive. Credential state may retain only the access token and account ID from the shared Codex cache. It must not retain API keys or refresh tokens, start login/browser/loopback flows, refresh credentials, or write the cache.
- URLs placed in request payloads are sent to OpenAI but are not fetched locally. Preserve that distinction in code and documentation.
- Never read, print, copy, or commit `~/.codex/auth.json`, tokens, API keys, signed URLs, or authenticated response bodies.
- Never expose credentials or prepared authentication headers through a public method, return value, dataclass representation, or package export.
- Only caller-executed `function` tools are allowed. The SDK must reject hosted web-search, computer-use, MCP, or other backend-executed tool types before transport.
- Keep public behavior typed and synchronous unless the existing Responses contract requires streaming. Prefer focused changes over broad rewrites.

## Verification

Use the existing environment; do not install or update packages unless the user explicitly authorizes non-OpenAI package-host access.

The default suite is offline, skips every `live` test, and must not read stored authentication or contact a network service:

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest -q
```

The tests in `test_basic.py`, `test_conversation.py`, `test_reasoning.py`, `test_structured_output.py`, and `test_tools.py` authenticate and contact live services through the shared `client` fixture. They remain skipped without `--live`. Run them only when the user explicitly requests live integration verification and authorizes credential use, network access, and possible quota consumption.

```bash
env -u TEMP -u TMP .venv/bin/python -m pytest --live -q \
  tests/test_basic.py \
  tests/test_conversation.py \
  tests/test_reasoning.py \
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
- `docs/backend-api.md` records current reverse-engineering notes; mark superseded observations clearly.
- `security_best_practices_report.md` records the current agent-safety review and deployment boundary.
- `CHANGELOG.md` is append-only chronology.
- `docs/audits/cold-substrate-sweep-v1.md` is a frozen pre-repair audit and must not be rewritten.
