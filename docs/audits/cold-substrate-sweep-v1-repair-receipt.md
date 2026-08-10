# Cold substrate sweep repair receipt v1

Status: PASS  
Audit artifact: `docs/audits/cold-substrate-sweep-v1.md`  
Repair revision: working tree based on `22845e7f109a2fd4d166e5e7065a0f4ee5892829`  
Verifier context: fresh read-only hostile diff review

## High-leverage repairs

- Added repository Codex guidance, conservative project configuration, and command rules.
- Disabled inherited non-OpenAI MCP entries for this project and pinned the sole enabled MCP server to `https://developers.openai.com/mcp`.
- Added a fail-closed SDK network policy for approved OpenAI-operated domains over TLS port 443.
- Disabled environment-proxy inheritance and redirect following for SDK-owned HTTP sessions, and made 3xx responses explicit policy failures.
- Validated signed upload destinations before file bytes are sent.
- Corrected current backend routing and authentication documentation without rewriting frozen chronology.

## Repair-created failures caught

- None established by the cold verifier.
- The declared offline pytest suite could not collect because `pydantic` is absent from the existing environment. No non-OpenAI package host was contacted to install it.

## Final verdict

PASS. The effective project MCP inventory enables only the official OpenAI Developer Docs endpoint. Source and configuration checks support an OpenAI-only boundary for SDK-owned outbound connections, with the documented loopback OAuth callback as the local exception.

## Evidence ceiling

This verifies maintained routing against the frozen audit and declared structural checks. It does not verify external state, source truth, scientific claims, or project quality. It also does not verify DNS/browser behavior, backend-side URL fetches, operating-system-wide egress enforcement, endpoint availability, entitlements, billing, or signed-host behavior outside the approved domain policy.
