# HingeZero Memory Desktop release notes

## v0.1.3 — maintenance and security hardening

- Fixed retrieval with mixed lexical and semantic embedding dimensions; deterministic ranking and the original memory evidence are preserved.
- Prevented redirected encrypted backups through dangling symbolic links and added a regression test.
- Added and passed whole-repository functional checks covering C++ parity, sanitizers, secure-memory/MCP, and desktop tests.
- Expanded independent-tool checks with Semgrep Community Edition and Gitleaks across the repository.
- Corrected release instructions and versioned release notes.

**Compatibility:** Encrypted local vault format is unchanged since v0.1.2. Existing v0.1.2 users can update the application without erasing their vault.

**Status:** Unsigned public preview. Signing, independent penetration testing, commercial agreement review, and real-user OS acceptance tests remain outstanding.

