# Cold substrate sweep v1

Status: FROZEN READ-ONLY AUDIT  
Repository / revision: `/home/nick/code/codex-backend-sdk` / `22845e7f109a2fd4d166e5e7065a0f4ee5892829` (`main`, tracking local `origin/main`)  
Agent context: fresh context, repository-only  
Verification observed: no `AGENTS.md`; followed `README.md`; inspected maintained source, routed `docs/backend-api.md`, `pyproject.toml`, `uv.lock`, changelog, tests, git status/history/config; `git diff --exit-code` and cached equivalent passed; worktree clean  
Mutation authority: none

## UPDATE

### `codex_backend_sdk/resources/files.py` — `Files.upload()`, lines 51–69; `README.md` lines 178 and 493–501; `docs/backend-api.md` lines 498–515

- Misleading inference: The SDK’s documented ChatGPT “signed upload” flow can be read as remaining within a controlled OpenAI/storage destination. In fact, it accepts any backend-returned `upload_url` and sends local file bytes there with `requests.put`; there is no scheme check, hostname policy, redirect restriction, or explicit proxy policy.
- Governing evidence: `upload_url = create_payload["upload_url"]` is passed directly to `requests.put`. The tests deliberately accept `https://upload.example/...`, proving the destination is treated as opaque. By contrast, all ordinary API bases are fixed constants in `_client.py`.
- Minimum repair: Before sending bytes, require HTTPS and apply a documented upload-destination policy: known signed-storage suffixes when they can be established, or a caller-supplied validator with fail-closed defaults. Disable cross-host redirects for this upload and add rejection tests for HTTP, malformed URLs, unexpected hosts, and redirects. Document that this is the sole direct runtime egress whose host is backend-selected.

### `docs/backend-api.md` — “Authentication headers”, lines 18–33

- Misleading inference: “Every request” must carry the ChatGPT access token, account ID, and originator; additionally, `/v1/audio/transcriptions` appears to remain a current Platform route.
- Governing evidence: `_client.py:224–249` sends only `Authorization` to `api.openai.com`; `oauth.py:135–188` uses OAuth-specific token request headers; the signed upload carries no ChatGPT auth headers. Current `resources/openai_oauth.py:127–135`, README lines 165–166, changelog 0.3.8, and the same document’s lines 309–345 route transcription to `https://chatgpt.com/backend-api/transcribe`.
- Minimum repair: Scope the three-header rule to authenticated ChatGPT backend requests, list the OAuth/OpenAI Platform/signed-upload exceptions, and label the Platform transcription observation as superseded historical evidence or remove it from current routing prose.

### `docs/backend-api.md` — Codex endpoint headings at lines 39, 78, 195, 232, and 261

- Misleading inference: A successor may call `/codex/...` against the host, or append `/codex/...` to the documented base `https://chatgpt.com/backend-api/codex`, producing an omitted or duplicated path segment.
- Governing evidence: `_client.py:14` fixes the base at `https://chatgpt.com/backend-api/codex`, while resources append `/models`, `/responses`, `/responses/compact`, `/memories/trace_summarize`, and `/realtime/calls`. README lines 159–163 gives the unambiguous full `/backend-api/codex/...` paths. Later headings in the same document already use full `/backend-api/...` routes.
- Minimum repair: Normalize these headings to full `/backend-api/codex/...` paths, or explicitly label every heading as a suffix relative to `BASE_URL` and remove the extra `/codex`.

## RETIRE

None established.

The stale Platform transcription sentence is maintained current-routing prose and should be updated, not destroyed. The audio-speech and WHAM remote-control observations are routed as “observed but not exposed,” so repository evidence does not justify retiring them.

## KEEP

### `README.md` — “Supported Backend Endpoints”, lines 152–180

- The maintained endpoint table agrees with current resource implementations, including the July 2026 transcription move to ChatGPT, image routes, reset credits, WHAM reads, account data, and file upload flow.

### `codex_backend_sdk/_client.py` — base constants and request helpers

- `chatgpt.com`, `api.openai.com`, and the Realtime WebSocket URL are centralized and not caller-configurable through the public constructor.
- This is a logical-host restriction, not a hard network allowlist: Requests defaults still permit environment proxies and HTTP redirects unless overridden.

### `codex_backend_sdk/oauth.py` — issuer and callback routing

- OAuth issuer is fixed to `https://auth.openai.com`.
- The callback listener binds explicitly to `127.0.0.1:1455`; state is checked before accepting a code.
- The requested scopes include `api.connectors.read` and `api.connectors.invoke`, but the repository contains no configured connector or MCP server destination.

### `CHANGELOG.md` — versioned chronology

- The older Platform transcription route is preserved correctly as superseded history: 0.3.8 explicitly records the move to ChatGPT. This append-only chronology should not be rewritten to erase the prior state.

### `docs/backend-api.md` — observed-but-unexposed surfaces

- `POST https://api.openai.com/v1/audio/speech` and `wss://chatgpt.com/backend-api/wham/remote/control/server` plus its enrollment path are observations, not implemented SDK resources.
- README lines 504–508 provides the governing “Observed But Not Exposed” route. Preserve them as evidence unless fresh repository evidence proves removal.

### `uv.lock` — locked dependency sources

- Locked packages use `https://pypi.org/simple` and hashed artifacts from `https://files.pythonhosted.org`.
- This control applies only when a lock-respecting command is used; README’s `pip install -e .` does not declare use of the lock.

## Network/server destination inventory

### Direct runtime HTTP destinations

- `https://chatgpt.com/backend-api/codex`
  - `POST /responses`
  - `POST /responses/compact`
  - `POST /memories/trace_summarize`
  - `GET /models`
  - `POST /realtime/calls`
  - `POST /images/generations`
  - `POST /images/edits`
  - `GET /rate-limit-reset-credits`
  - `POST /rate-limit-reset-credits/consume`
  - Repository control: fixed base constant; no public base-URL override. Not a hard host allowlist because redirects and environment proxies are not disabled.

- `https://chatgpt.com/backend-api`
  - `GET /wham/usage`
  - `GET /wham/config/requirements`
  - `GET /wham/tasks/list`
  - `GET /wham/tasks/{task_id}`
  - `GET /wham/tasks/{task_id}/turns`
  - `GET /wham/tasks/{task_id}/turns/{turn_id}/sibling_turns`
  - `GET /wham/environments`
  - `GET /memories`
  - `GET /user_system_messages`
  - `POST /transcribe`
  - `POST /files`
  - `POST /files/{file_id}/uploaded`
  - Repository control: same fixed logical host, with the same redirect/proxy caveat.

- `https://api.openai.com/v1`
  - `POST /embeddings`
  - Repository control: fixed base constant, but redirects/proxies are not disabled.

- `https://auth.openai.com`
  - Browser authorization: `/oauth/authorize`
  - Token exchange, refresh, and API-key exchange: `/oauth/token`
  - Repository control: fixed issuer; Requests/browser redirect chains and proxies are outside repository restriction.

- Backend-returned `upload_url`
  - `PUT` of local file bytes.
  - Repository control: none beyond backend authentication preceding URL acquisition and Requests’ default TLS behavior. Scheme, host, port, redirects, and proxy path are not constrained.

### Local listener/browser destination

- `127.0.0.1:1455`, with redirect URI `http://localhost:1455/auth/callback` and success page `/success`.
- Repository control: listener bind is loopback-only and port-fixed. The browser resolves `localhost`.

### WebSocket destinations

- `wss://api.openai.com/v1/realtime?model=...`
  - The SDK returns this URL and headers but does not open the socket.
  - Repository control: fixed URL; the consuming application controls the actual connection behavior.

- `wss://chatgpt.com/backend-api/wham/remote/control/server`
  - Documentation-only observed route; not exposed or opened by code.
  - Enrollment observation: `POST https://chatgpt.com/backend-api/wham/remote/control/server/enroll`.

### Indirect backend-directed network destinations

- Image edit URLs in `images[].image_url` and Responses `input_image.image_url`
  - Arbitrary non-empty URLs are passed to ChatGPT; the local SDK does not fetch them.
  - Repository control over the destination host: none. Any fetch occurs backend-side.

- Web-search tools
  - Tool dictionaries are passed through without a local type/host policy; docs distinguish cached index from live fetch.
  - Repository control over fetched hosts: none; selection is backend-side.

- MCP/connector servers
  - No MCP server configuration, server URL, webhook, or connector destination exists in the repository.
  - Arbitrary tool dictionaries are pass-through, so the SDK does not itself enforce a tool-type destination policy; backend acceptance of remote-MCP definitions was not established.
  - OAuth requests connector read/invoke scopes.

### Package/download destinations

- `https://pypi.org/simple`
  - Registry recorded throughout `uv.lock`.
- `https://files.pythonhosted.org`
  - Hashed sdist/wheel URLs recorded in `uv.lock`.
- Repository control: strong only under lock-respecting installation. `README.md` directs `pip install -e .`; pip may use user/environment-configured indexes, and `pyproject.toml` uses lower-bounded dependencies plus an unpinned `hatchling` build requirement. Thus the documented install route does not restrict actual registry hosts.

### Git/document destinations

- Local configured fetch/push remote: `https://github.com/jackryan67565/codex-backend-sdk.git`.
- README clone route: `https://github.com/B4PT0R/codex-backend-sdk.git`.
- `https://openai.com/policies/terms-of-use` is documentation-only.
- Repository controls do not prevent Git reconfiguration or redirects.

### Telemetry, export, webhook, and CI destinations

- No telemetry exporter, analytics collector, webhook, CI workflow/service endpoint, package-publish target, or error-reporting endpoint was found.

### Returned but not automatically contacted

- File `download_url` is stored in `UploadedFile` but never fetched by the SDK. Its host is backend-selected and unvalidated.

## Uncertainties

- No network call, browse, fetch, or authenticated probe was performed, so current endpoint availability and external behavior remain unverified.
- The accepted signed-upload storage host set is not recorded; a safe allowlist cannot be inferred from repository-only evidence.
- README names `B4PT0R/codex-backend-sdk` while local `origin` names `jackryan67565/codex-backend-sdk`. Commit authorship supports B4PT0R as the original source, but repository-only evidence does not establish which is now canonical.
- There is no repository-declared verifier or development recovery sequence beyond README installation. Tests were not run because no read-only verification command is declared and environment/auth-dependent tests may mutate or contact external services.
- `docs/backend-api.md` says it was last updated 2026-05-12, while maintained implementation and changelog changed through 2026-07-17. Only contradictions evidenced by current source were classified.
- Requests/browser redirect targets, environment proxy hosts, DNS resolution, and backend-side URL-fetch behavior are outside repository control and were not externally inspected.
- Local branch and local remote-tracking ref coincide, but remote freshness is unknown because fetching was forbidden.

## Stop list

- Do not edit, commit, stage, fetch, browse, publish, authenticate, contact endpoints, or consume quota/reset credits.
- Do not read `~/.codex/auth.json` or other user credential stores.
- Do not run the test suite until a maintainer identifies the intended offline/read-only subset; several tests and documented examples concern real authenticated backends.
- Do not retire observed audio-speech or remote-control routes merely because they are unimplemented.
- Do not change the Git remote or README clone owner until canonical ownership is resolved.
- Do not invent a signed-upload hostname allowlist. Establish the supported storage domain set first; HTTPS enforcement and redirect rejection can be designed independently.
- Do not treat `uv.lock` as governing README’s pip installation unless onboarding explicitly adopts a lock-respecting command.
- Do not claim repository consistency verifies endpoint truth, entitlement, billing behavior, external service safety, or current OpenAI rollout state.
