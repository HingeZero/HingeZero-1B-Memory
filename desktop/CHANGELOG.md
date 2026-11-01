# HingeZero Memory Desktop release notes

## v0.1.5 — local ChatGPT bridge

- Added optional MCP stdio bridge with read-only memory_search tool.
- Added an independently generated read-only API token; write requests with that token return HTTP 403.
- Kept existing original HingeZero Core and Witness in desktop retrieval.
- Added functional and permission tests for the bridge.
- Bridge must be connected by an eligible user through Secure MCP Tunnel; it is not automatically linked to ChatGPT.
- Tool results share selected saved notes with ChatGPT; no automatic note capture.

## v0.1.4 — original-core integration

- Integrated the **unchanged original HingeZero Core** (source blob `ec0ec9c56c233b97038d88618ad9f2bcff26bcab`) into desktop retrieval.
- Replaced the simplified dual-tanh surrogate with original eight-step refinement and Witness verification of stored-state identity.
- Connected the original retaining loop to repeated desktop searches and exposed verified session checkpoint rollback logic.
- Added source-fidelity, Witness invocation, retention/rollback, mixed-embedding and false-factual-truth tests.
- Existing encrypted local vault format remains unchanged; optional local AI and explicit-consent behaviour are preserved.
- **Not included:** the separate billion-pattern C++ research engine. Benchmark throughput figures do not describe desktop performance.

**Status:** Unsigned preview; no independent penetration test or production security certification. Source-available under PolyForm Noncommercial; commercial rights require a separate agreement.

## v0.1.3 — maintenance and security hardening

- Fixed retrieval with mixed lexical and semantic embedding dimensions; deterministic ranking and the original memory evidence are preserved.
- Prevented redirected encrypted backups through dangling symbolic links and added a regression test.
- Added and passed whole-repository functional checks covering C++ parity, sanitizers, secure-memory/MCP, and desktop tests.
- Expanded independent-tool checks with Semgrep Community Edition and Gitleaks across the repository.
- Corrected release instructions and versioned release notes.

**Compatibility:** Encrypted local vault format is unchanged since v0.1.2. Existing v0.1.2 users can update the application without erasing their vault.

**Status:** Unsigned public preview. Signing, independent penetration testing, commercial agreement review, and real-user OS acceptance tests remain outstanding.

