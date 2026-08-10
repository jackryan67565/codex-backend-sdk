# Codex repository guidance

## Purpose and recovery order

This repository is an unofficial Python SDK for undocumented ChatGPT Codex backend endpoints. It is not an OpenAI-supported SDK. Start with this file, then read `README.md`, `pyproject.toml`, and only the source or focused backend notes needed for the task. Treat `CHANGELOG.md` and `docs/audits/` as history/evidence, not current authority.

## Working agreements

- After each completed, coherent change, inspect the intended diff, create a descriptive Git commit, and push the current branch before handoff. Do not batch unrelated work or stage changes outside the current task; if repository state, authentication, or remote policy prevents a safe commit or push, report that explicitly.
- Before pushing, verify that `origin` is still the expected repository. Pushes to that configured origin are an explicit development-workflow exception to the offline project substrate; they do not relax the SDK runtime egress boundary or authorize fetch, pull, or other non-OpenAI network access.
- When answering questions about this SDK's features, routes, or behavior, read the project documentation and implementation first. Do not substitute official OpenAI platform documentation for this repository's documented, unofficial backend surface; consult external docs only when the project docs leave a relevant gap or the user explicitly asks for an upstream comparison.
- Preserve the OpenAI-only outbound boundary. SDK-owned HTTP(S) and WebSocket destinations must pass `codex_backend_sdk._network.validate_openai_url`.
- Approved runtime domain families are `chatgpt.com`, `openai.com`, `oaiusercontent.com`, and `oaistatic.com`, including their subdomains, over TLS on port 443.
- Do not add a new network domain, proxy support, redirect following, caller-configurable base URL, remote MCP server, telemetry exporter, webhook, or package registry without explicit user approval and focused policy tests.
- The repository MCP overlay enables only `openaiDeveloperDocs` at `https://developers.openai.com/mcp`; inherited Node REPL, Playwright, and Figma entries are disabled for this project. Re-audit `codex mcp list` if user-level configuration changes.
- Keep `requests.Session.trust_env = False` for SDK-owned sessions so environment proxy variables cannot reroute credentials or file bytes. Keep redirects disabled; validate a new destination before every request.
- The OAuth callback listener on `127.0.0.1:1455` is the sole local-server exception. The system browser handles the OpenAI authorization page and loopback callback outside the SDK transport.
- URLs placed in request payloads are sent to OpenAI but are not fetched locally. Preserve that distinction in code and documentation.
- Never read, print, copy, or commit `~/.codex/auth.json`, tokens, API keys, signed URLs, or authenticated response bodies.
- Keep public behavior typed and synchronous unless the existing resource contract requires streaming. Prefer focused changes over broad rewrites.

## Verification

Use the existing environment; do not install or update packages unless the user explicitly authorizes non-OpenAI package-host access.

Offline unit suite (no authentication or external network expected):

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

The tests in `test_basic.py`, `test_conversation.py`, `test_reasoning.py`, `test_structured_output.py`, and `test_tools.py` authenticate and contact live services through the shared `client` fixture. Run them only when the user explicitly requests live integration verification and authorizes credential use, network access, and possible quota consumption.

For network-boundary changes, also run:

```bash
rg -n 'https?://|wss?://' codex_backend_sdk
```

Classify each match as an approved SDK-owned destination, the loopback OAuth callback, documentation text, or payload-only data. Do not equate a passing source scan with operating-system egress enforcement.

## Documentation

- `README.md` is the maintained user entrypoint.
- `docs/backend-api.md` records current reverse-engineering notes; mark superseded observations clearly.
- `CHANGELOG.md` is append-only chronology.
- `docs/audits/cold-substrate-sweep-v1.md` is a frozen pre-repair audit and must not be rewritten.
