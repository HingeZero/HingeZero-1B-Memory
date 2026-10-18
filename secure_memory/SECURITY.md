# Security policy

## Status

Developer preview version 0.1.0. Not independently certified. Never describe this package as 100% secure or universally compliant.

## Included controls

- Original HingeZero refinement and stored-state Witness with a separately encrypted local record store.
- AES-256-GCM encrypted record payloads, Scrypt passphrase-based key derivation and per-vault salt.
- Restricted local POSIX database paths and symlink rejection.
- Revocable, time-limited, scoped read/write capabilities.
- Local stdio MCP bridge provides READ-ONLY retrieval with no network listener.
- User-approved memory writes only, with no raw transcript recording by default.
- Input length limits, retention limits, an upper record cap, and similarity/margin abstention.

## Trust boundaries

Retrieved text is untrusted data, never executable instructions. It must not authorise tool calls, approve memory writes or override the host's policies. The receiving AI host must enforce these boundaries independently. A true value for metadata such as trusted_as_instruction=false is not itself a defence against prompt injection.

A verified stored record can be incorrect, outdated or poisoned; the Witness checks stored-state identity, not factual truth or correct intended identity. The deterministic text hashing adapter is not a semantic encoder or sensitive-data classifier.

This package lacks remote multi-user access management, signed security logs, hardware-backed key storage, key rotation, platform-wide injection prevention, assured deletion from backups, full disaster recovery and production incident management. Environment-based credentials can leak to host processes.

Before production: independent threat modelling and penetration testing, dependency and supply-chain audits, integration-specific prompt-injection testing, OS hardening and privacy/legal sign-off.

## Vulnerability reports

Report vulnerabilities privately through the repository's GitHub security advisories when enabled. Never publish exploits, credentials or private user data in public issues.
