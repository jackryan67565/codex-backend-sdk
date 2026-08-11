# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.4.1] - 2026-08-10

### Security
- Removed bearer and account-routing headers from retained Requests objects before successful responses or transport failures escape the internal transport, while preserving existing exception classes and retry behavior.
- Replaced the internal transport's arbitrary Requests keyword forwarding with an explicit, closed set of request options.

### Changed
- Added client `close()` and context-manager support, and deterministically close consumed model, compaction, retry, redirect, and SSE response resources.

### Tests
- Added a synthetic offline matrix covering HTTP status, redirect, timeout, and connection failures across Models, Responses, and Compaction, including wire-header presence followed by retained-object sanitization.

### Packaging
- Refreshed package metadata and the lockfile for a local-install checkpoint.
- Verified the wheel by installing it into a fresh isolated virtual environment and importing the packaged client.

## [0.4.0] - 2026-08-09

### Security
- Contracted the public client to agent-safe stateless Responses and model discovery; removed account data, Cloud history, quota mutation, uploads, audio, images, embeddings, Realtime, and broad ChatGPT/WHAM/Platform resource namespaces.
- Added a fail-closed method-and-route allowlist for exactly three `chatgpt.com/backend-api/codex` operations rather than trusting every path on an approved hostname.
- Removed public credential/storage exports, interactive OAuth and callback handling, token refresh, credential writes, API-key derivation, Realtime credential-return helpers, and prepared-header access.
- Reduced loaded credential state to a non-repr access token and account identifier; reject linked, non-regular, oversized, missing, or stale credential caches.
- Removed caller-controlled headers, query parameters, generic request helpers, custom connection material, and hosted web-search/computer-use/MCP tools.
- Limited automatic retries to idempotent model reads so ambiguous failures cannot replay billable Responses or compaction POSTs.
- Bounded timeouts, model-read retry counts, and retry delays to prevent agent-controlled indefinite waits or retry amplification.

### Changed
- `authenticate()` now reuses only a current local Codex login and directs the operator to the trusted Codex CLI or ChatGPT desktop app when renewal is required.
- Function tools remain supported because the SDK returns calls to the caller and never executes them.
- Bumped the package to `0.4.0` for the intentionally breaking security contraction.

### Tests
- Made all credentialed/network integration tests mechanically skip unless `--live` is supplied.
- Added negative coverage for unsafe public resources, credential exports and representations, linked auth files, stale tokens, hosted tools, caller transport controls, and every retired route family.
- Retained final-wire, retry, typed Responses, compaction, parsing, streaming, model, and function-call coverage in the offline suite.

### Documentation
- Rewrote the maintained contract and wire notes around the narrow agent-safe surface, explicit non-goals, read-only authentication, live-test gate, and same-process threat-boundary caveat.

## [0.3.10] - 2026-07-17

### Added
- Added typed Codex rate-limit reset credit listing and explicit idempotent consumption through `client.codex.rate_limit_reset_credits`.
- Added ChatGPT-authenticated image generation and editing through `client.images.generate(...)` and `client.images.edit(...)`, returning typed base64 image data from the Codex backend.

### Documentation
- Documented that image generation uses the ChatGPT Codex backend rather than the separately billed Platform image endpoint, and that consuming reset credits mutates account quota state.
- Documented the verified Codex JSON image-edit contract using ordinary URLs or base64 data URLs.

### Tests
- Added behavioral coverage for credit payloads, redemption validation, image request construction, defaults, URL normalization, and typed responses; verified read-only credit listing plus real image generation and editing against the authenticated backend.

## [0.3.9] - 2026-07-17

### Fixed
- Detect anonymous audio buffers by their file signature before ChatGPT transcription uploads, correcting filenames and MIME types when callers provide misleading generic names such as `audio.mp3` for WAV data.
- Restored reliable `AIClient.audio_to_text(bytes)` integration with `/backend-api/transcribe` without requiring callers to understand multipart backend constraints.

### Tests
- Added regression coverage for WAV buffers carrying an incorrect `.mp3` name and verified the complete Codex Agent transcription path against the real ChatGPT backend.

## [0.3.8] - 2026-07-17

### Changed
- Routed `client.audio.transcriptions.create(...)` through the ChatGPT-native `/backend-api/transcribe` endpoint instead of the billable Platform `/v1/audio/transcriptions` endpoint.
- Preserved the OpenAI-shaped `json` and `text` response behavior used by Codex Agent while rejecting unsupported streaming, timestamp, speaker, chunking, SRT, and VTT options explicitly.
- Added a reusable raw ChatGPT multipart request helper to the client transport.

### Documentation
- Clarified that embeddings still use the OpenAI Platform endpoint and its developer-account quota, while batch transcription now uses the authenticated ChatGPT backend.

### Tests
- Added coverage for ChatGPT transcription routing, account authentication headers, text responses, and unsupported parameters.

## [0.3.7] - 2026-07-17

### Added
- Added typed Realtime call results through `RealtimeCallResponse.answer_sdp` and `RealtimeCallResponse.call_id`.
- Added Codex AVAS session payload support, including automatic removal of the server-generated session `id` and the required `quicksilver` query parameters.

### Documentation
- Documented that the ChatGPT-authenticated Codex WebRTC route is experimental and rollout-dependent, while the public Realtime WebSocket route still requires a developer API key.

### Tests
- Added coverage for SDP response parsing, call ID validation, AVAS payload construction, and invalid session payloads.

## [0.3.6] - 2026-07-11

### Added
- Added Voice v2 WebSocket headers through `client.realtime.websocket_headers(...)`, using the API key stored by OAuth when available or `OPENAI_API_KEY` as a fallback.
- Added `authenticate(force=True)` for explicit interactive reauthentication.

### Changed
- ChatGPT OAuth now attempts the same optional ID-token-to-API-key exchange as Codex CLI and persists the result in the official `OPENAI_API_KEY` auth field.
- Removed the legacy `request_api_key` authentication option; API-key acquisition is now an internal OAuth concern and never prevents regular Codex login.

### Tests
- Added coverage for forced authentication and Realtime credential selection/error behavior.

## [0.3.5] - 2026-05-18

### Fixed
- Preserved `usage` on `client.responses.compact(...)` results so `CompactedResponse` exposes backend token accounting.

### Tests
- Added coverage to verify compact responses retain `input_tokens`, `output_tokens`, and `total_tokens`.

## [0.3.4] - 2026-05-15

### Added
- Added `authenticate(interactive=False)` to allow non-interactive credential checks without triggering the browser OAuth flow.
- Added `client.authenticated` for simple auth-state introspection.
- Added `client.account_info()` to expose safe non-secret account metadata (`authenticated`, `account_id`, `email`, `plan_type`).

### Documentation
- Documented the non-interactive authentication helpers in `README.md`.
