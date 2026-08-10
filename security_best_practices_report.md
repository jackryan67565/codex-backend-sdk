# Agent-safety security review

## Executive summary

The `0.4.0` worktree has been contracted from a broad ChatGPT backend SDK to a
narrow agent-use client. Repository-managed connections are limited to Codex
model discovery, Responses, and Responses compaction. Credential lifecycle,
account data, Cloud history, state mutation, arbitrary uploads, Platform APIs,
Realtime material, raw transports, hosted tools, and implicit live testing have
been removed or rejected below the public resource layer.

No unresolved critical or high-severity issue remains in the SDK-managed
surface reviewed here. The package is still not a sandbox for hostile Python
running in the same OS process; the deployment requirements at the end remain
mandatory for untrusted agents.

## Scope and standard

The review covers Python package exports, credential loading, HTTP transport,
Responses tool behavior, test defaults, and the project Codex substrate. The
criteria are least privilege, secret minimization, explicit side effects,
fail-closed routing, non-idempotent operation safety, and defense in depth.

## Critical findings

### AS-001 — Credential material exposed through ordinary SDK surfaces — Remediated

**Impact:** An agent could previously obtain API-key-bearing Realtime headers or
import token storage and refresh primitives directly.

The current public package exports no credential object, loader, writer, OAuth,
refresh, or prepared-header helper. The client retains credentials in slots and
the minimal private credential object redacts both token and account ID from its
representation ([`codex_backend_sdk/_client.py:30`](codex_backend_sdk/_client.py#L30),
[`codex_backend_sdk/_storage.py:43`](codex_backend_sdk/_storage.py#L43)). Negative
export and retired-module checks are in
[`tests/test_agent_safety.py:17`](tests/test_agent_safety.py#L17).

### AS-002 — Bearer accepted by unrelated account and stateful routes — Remediated

**Impact:** Hostname-only validation allowed authenticated access to personal
ChatGPT data, Codex Cloud history, quota mutation, uploads, and other services.

The transport now validates the exact method, host, and path against three
entries before opening a connection
([`codex_backend_sdk/_network.py:11`](codex_backend_sdk/_network.py#L11)). The client
constructs only fixed model, Responses, and compaction operations
([`codex_backend_sdk/_client.py:93`](codex_backend_sdk/_client.py#L93)). The broader
resource and transport modules were deleted.

## High findings

### AS-003 — Arbitrary readable-file and media egress — Remediated

The file-upload, transcription, image, embeddings, and Realtime resource
implementations are no longer shipped. The current source has one
connection-capable `requests.Session`, and its destination passes the exact
route policy. Payload URLs remain data sent to OpenAI and are never fetched by
the SDK.

### AS-004 — Implicit authentication and quota use during tests — Remediated

All credentialed integration modules carry the `live` marker. Pytest skips them
unless the operator supplies `--live`; the shared authenticated fixture remains
lazy ([`tests/conftest.py:7`](tests/conftest.py#L7)). A normal test run is therefore
offline and does not load the user's credential cache.

### AS-005 — Backend-executed hosted tools — Remediated

Only caller-executed `function` tools and matching function choices are
accepted. Web-search, computer-use, MCP, and other hosted tool types fail before
transport
([`codex_backend_sdk/resources/_responses_payloads.py:177`](codex_backend_sdk/resources/_responses_payloads.py#L177)).

## Medium findings

### AS-006 — Automatic replay of non-idempotent Responses POSTs — Remediated

Retries are restricted to idempotent methods. Responses and compaction POSTs
are never replayed after ambiguous timeouts, connection failures, rate limits,
or server errors
([`codex_backend_sdk/_transport.py:17`](codex_backend_sdk/_transport.py#L17)).

### AS-007 — Credential-cache overreach and mutation — Remediated

Authentication is local and read-only. The loader requires a regular,
non-symlink credential file no larger than 1 MiB and retains only the access
token and account ID. The client refuses stale tokens rather than loading a
refresh token, opening a browser, exchanging credentials, or writing the shared
cache ([`codex_backend_sdk/_storage.py:56`](codex_backend_sdk/_storage.py#L56),
[`codex_backend_sdk/_client.py:73`](codex_backend_sdk/_client.py#L73)).

### AS-008 — Agent-controlled indefinite waits and retry amplification — Remediated

Constructor and per-call timeouts must be finite, positive, and at most ten
minutes. Model-read retries are capped at five and individual delays at 60
seconds; non-idempotent requests remain non-retryable
([`codex_backend_sdk/_client.py:40`](codex_backend_sdk/_client.py#L40),
[`codex_backend_sdk/_transport.py:60`](codex_backend_sdk/_transport.py#L60)).

## Verification evidence

- Offline suite: `73 passed, 11 skipped`.
- Python compilation completed for `codex_backend_sdk` and `tests`.
- `git diff --check` completed without whitespace errors.
- Source URL scan found one connection base:
  `https://chatgpt.com/backend-api/codex`.
- Negative tests cover retired modules/resources, credential exports,
  credential representations, symlinked auth files, stale credentials, unsafe
  routes and methods, caller headers/query, hosted tools, redirects, proxy
  inheritance, and non-idempotent retries.

## Deployment requirement

Python privacy conventions are not an adversarial isolation boundary. Code with
arbitrary filesystem and network authority can bypass any SDK by reading files
or importing another HTTP library. The checked-in Codex substrate therefore
keeps command network access disabled by default. A host running genuinely
untrusted agents must additionally keep the auth cache outside their filesystem
permissions and expose these three operations through a trusted credential
broker. Granting raw shell, credential-file read, and unrestricted network
access together is outside the supported security model.
