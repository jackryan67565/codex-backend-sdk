# Cold substrate sweep v2

Status: FROZEN READ-ONLY AUDIT  
Repository / revision: `/home/nick/code/codex-backend-sdk` / `dee8ea435b94dc90ab5a7d9d41bce832d7418eba` (`main`, tag `v0.6.0`, tracking local `origin/main`)  
Agent context: zero-context cold successor  
Verification observed: followed `AGENTS.md` recovery order; inspected maintained entrypoints, source, focused backend/security/compatibility notes, project substrate, routed frozen v1 evidence, tests, local Git state, configured origin, and ignored distribution inventory; worktree and index diff checks passed; source URL scan found only the approved Codex route family; offline pytest and live verification were not run under read-only mutation authority  
Mutation authority: none

## UPDATE

### `AGENTS.md` — `## Verification`, live-test inventory and command

- Misleading inference: The canonical repository instructions identify six credentialed integration modules and direct an authorized operator to run those six, omitting the live compaction smoke test. A successor following only the governing recovery path could conclude that compaction has no declared live verification or unintentionally leave the third runtime route unverified.
- Governing evidence: `tests/test_compaction.py` contains `test_live_compaction_endpoint_shape_and_continuation`, explicitly marked `@pytest.mark.live`, and authenticates an `OpenAI(max_retries=0)` client before calling both compaction and Responses. `README.md` under `## Testing` includes `tests/test_compaction.py` in the full live command and provides a focused live command. `docs/backend-api.md` under ``## `POST /backend-api/codex/responses/compact` `` routes operators to the same gated smoke test.
- Minimum repair: Add `test_compaction.py` to the prose inventory and the canonical multi-file live command in `AGENTS.md`. Preserve its explicit credential, network, quota, and `--live` authorization gate.

### `security_best_practices_report.md` — `### AS-004 — Implicit authentication and quota use during tests — Remediated`

- Misleading inference: “All credentialed integration modules carry the `live` marker” implies module-level marking is the repository-wide mechanical invariant. `tests/test_compaction.py` is intentionally mixed: it has an offline sanitizer test and marks only its credentialed test function. A successor auditing by module-level markers could falsely report drift or, worse, miss the actual case-level safety invariant.
- Governing evidence: Six integration modules define `pytestmark = pytest.mark.live`; `tests/test_compaction.py` instead places `@pytest.mark.live` directly on `test_live_compaction_endpoint_shape_and_continuation`, while `test_safe_compaction_report_excludes_ciphertext_and_plaintext` remains offline. `tests/conftest.py` skips collected items whose keywords contain `live`, so the effective invariant is test-case marking, not universal module marking.
- Minimum repair: Replace “all credentialed integration modules carry” with “all credentialed integration test cases carry,” and note that wholly live modules use `pytestmark` while the mixed compaction module uses a function marker. Do not mark the entire compaction module live.

## RETIRE

None established.

The pre-0.4 architecture remains present only in append-only chronology, the frozen v1 audit, its repair receipt, and an explicitly labeled “Intentionally removed routes and capabilities” section. Maintained routing consistently rejects that architecture as current.

## KEEP

### `AGENTS.md` — `## Purpose and recovery order`

- KEEP. It establishes one canonical successor route: repository instructions, maintained README, package metadata, then only task-relevant source or focused notes. It explicitly demotes `CHANGELOG.md` and `docs/audits/` to history/evidence.

### `AGENTS.md` and `README.md` — current model and release routing

- KEEP. The exact `gpt-5.6-sol` default is aligned across `codex_backend_sdk/_client.py`, README quickstarts, compatibility notes, backend wire example, integration skill, example, and regression tests.
- Dated `gpt-5.4` observations are clearly scoped as historical live evidence rather than the current default.
- Package version `0.6.0` is aligned across `pyproject.toml`, `codex_backend_sdk/__init__.py`, changelog, README installation guidance, current tag, and local artifact names.
- README explicitly warns that ignored `dist/` contents are not checkout authority and directs post-checkpoint work to editable installation.

### `codex_backend_sdk/_network.py`, `_client.py`, and `_transport.py` — runtime boundary

- KEEP. The implementation admits exactly:
  - `GET https://chatgpt.com/backend-api/codex/models`
  - `POST https://chatgpt.com/backend-api/codex/responses`
  - `POST https://chatgpt.com/backend-api/codex/responses/compact`
- Method, scheme, normalized host, port, path, query, fragment, and user-information checks precede transport. SDK-owned sessions disable environment proxies, redirects are disabled and rejected, and retained request/response paths strip credential-bearing headers.
- The source URL scan found one connection base plus two Responses fallback URLs used as request/error metadata; all remain inside the approved route family.

### `docs/backend-api.md` — maintained wire contract

- KEEP. Full route locators, authentication limits, retry ambiguity, terminal-event authority, stateless replay, function-only tools, compaction behavior, and removed capabilities agree with checked-in implementation.
- The document explicitly separates current contract from dated backend observations and routes frozen audit material away from present authority.

### `docs/openai-sdk-compatibility.md` — supported subset and backlog

- KEEP. It distinguishes the supported OpenAI-shaped subset from full Platform parity, pins `openai==2.46.0`, retains explicit incompatibilities, and labels parity gaps as backlog rather than authorization.
- Service-tier and repair-iteration matrices retain their `gpt-5.4`, date, route, and sample-size limits.
- `max_output_tokens`, stateful continuation, hosted tools, transport escapes, and provider-retention claims remain explicitly bounded.

### `security_best_practices_report.md` — security boundary apart from AS-004 wording

- KEEP. Current critical/high/medium findings match the narrowed source, including credential minimization, exact-route enforcement, removal of file/media egress, hosted-tool rejection, bounded retries, and same-process isolation limits.
- Its dated `144 passed, 13 skipped` statement is framed as verification evidence from 2026-08-26, not a perpetual current test result.

### `.codex/config.toml` and `.codex/rules/network.rules` — project substrate

- KEEP. Project defaults disable command-network access and browser/plugin surfaces, disable the three named inherited MCP integrations, enable the official OpenAI documentation MCP entry, and forbid common network clients, remote Git reads, and package installation/synchronization.
- Push authorization remains separately and narrowly governed by `AGENTS.md`.

### `.agents/skills/codex-backend-sdk/SKILL.md` — consumer integration route

- KEEP. The skill routes capability questions to maintained README and compatibility surfaces, preserves exact default/baseline facts, names intentional incompatibilities, and directs repository modifications back to `AGENTS.md`.
- Its scope is consumption/integration guidance, not a competing repository governance document.

### `CHANGELOG.md` and `docs/audits/`

- KEEP. `CHANGELOG.md` is append-only chronology and clearly records the 0.4 contraction after broader historical releases.
- `docs/audits/cold-substrate-sweep-v1.md` is visibly frozen at a pre-repair revision and is explicitly demoted by current instructions and wire notes.
- `docs/audits/cold-substrate-sweep-v1-repair-receipt.md` records the prior repair verdict without being routed as current implementation authority.

## Uncertainties

- No network, authenticated, browser, fetch, or live test was performed. Endpoint availability, account entitlement, rollout support for `gpt-5.6-sol`, provider retention, quota effects, and backend behavior remain unverified.
- The declared offline pytest suite was not executed because the audit had no mutation authority and pytest may write ignored cache or bytecode state. The dated security-report result was inspected but not independently reproduced.
- Local `main`, tag `v0.6.0`, and the local `origin/main` ref coincide. Remote freshness was not checked because fetch was forbidden.
- `dist/` contains named 0.6.0 wheel/source artifacts and checksums, but artifact contents were not inspected. No claim is made that an ignored artifact matches the checkout.
- Repository inspection establishes only the checked-in MCP overlay. It does not prove the effective merged MCP inventory if user-level configuration has added or changed entries since the overlay was authored.
- The source scan verifies repository literals and policy structure, not DNS behavior, operating-system egress enforcement, Requests-library correctness, or backend-side fetching of payload URLs.
- The compatibility snapshot cites a local mock differential check against installed `openai==2.46.0`; this audit inspected its documentation and tests but did not rerun the comparison.

## Stop list

- Do not edit, stage, commit, push, fetch, pull, browse, publish, authenticate, contact endpoints, or consume quota under this audit.
- Do not read, print, copy, hash, inspect, or expose `~/.codex/auth.json`, tokens, prepared authentication headers, signed URLs, or authenticated bodies.
- Do not rewrite `CHANGELOG.md`, the frozen v1 audit, or its receipt to make historical prose resemble current architecture.
- Do not retire dated `gpt-5.4` probes or replace them with the current default; preserve their date, model, route, and evidence ceiling until a newly authorized live run supersedes them.
- Do not infer model availability from the local default, model catalog, tag, or artifact filename.
- Do not treat the ignored 0.6.0 wheel as matching source without inspecting or rebuilding a new versioned checkpoint.
- Do not run the live suite or focused compaction smoke test without explicit authorization for credential use, OpenAI network access, and possible quota consumption.
- Do not broaden the three-route runtime allowlist, restore retired resources, admit hosted tools, add transport escapes, or reinterpret unsupported parameters without explicit user approval and a focused security review.
- Do not claim the checked-in MCP overlay proves the effective merged MCP inventory after user-level configuration changes; re-audit the effective configuration first.
- Do not treat passing documentation, source scans, or offline tests as proof of external service truth, entitlement, billing behavior, retention, or operating-system-wide containment.
