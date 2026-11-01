# Release checklist

## Prerequisites

- Confirm authority to license all desktop code under PolyForm Noncommercial 1.0.0, and obtain legal review of the separately negotiated commercial agreement.
- Review privacy/security language and confirm package name and business ownership.
- Verify tests from a clean environment and review dependency audit.
- Enable GitHub Actions and allow `GITHUB_TOKEN` to create releases (`contents: write` permission).
- Decide whether to obtain a Windows code-signing certificate and Apple Developer ID/notarization. Unsigned builds may be flagged by operating systems.

## Automated release

The v0.1.4 core integration release is built from `desktop-core-integration-v0.1.4`. Source pushes run tests; the reviewed release uses a new tag `desktop-v0.1.4`. Never replace prior binaries. Existing release assets and prior tags must never be overwritten. For later releases, update the version and tag a reviewed commit; the tag-triggered workflow also supports `desktop-v*`.

The `.github/workflows/release.yml` workflow runs tests and a dependency audit, builds the desktop app on Windows, Linux and macOS, attaches archives to a GitHub Release and emits `SHA256SUMS.txt` for download verification. The workflow does not automatically sign binaries or notarize macOS packages.

**Important:** Release tags must begin with `desktop-v` and point to the desktop branch commit, **not** the research/main branch. Never reuse a published release tag.

GitHub Releases are repository-wide. A cleaner future setup is a dedicated `HingeZero-Memory-Desktop` repository, if available. No existing benchmark files need to be overwritten. The `desktop/` licence does not relicense other repository files.

## Licence verification

- Verify each Windows/Linux/macOS distributable includes `LICENSE.md`, `NOTICE.txt` and `COMMERCIAL-LICENSING.md`.
- Ensure HingeZero Ltd has the copyright assignment or necessary rights from all contributors to offer commercial terms.
- Verify bundled third-party dependency licences and distribution notices with legal counsel.
- No fixed fee or signed commercial agreement has been automatically created.
- Older released downloads remain under their previously applicable terms.

## Inspect artifacts before promoting widely

- [ ] GitHub workflow succeeded on all three operating systems.
- [ ] Verify checksums.
- [ ] Fresh Windows user first-run onboarding, vault creation, import and search.
- [ ] Fresh Linux user first-run onboarding, vault creation, import and search.
- [ ] Fresh macOS user first-run onboarding, vault creation, import and search.
- [ ] Confirm locked vault cannot be opened with incorrect passphrase.
- [ ] Confirm local API is disabled by default and rejects missing or invalid token.
- [ ] Confirm optional local Ollama behavior requires consent.
- [ ] Confirm no secrets, private documents or personal tokens included in release.
