# Release checklist

## Prerequisites

- Decide and add a legal licence. No explicit redistribution licence is included by default.
- Review privacy/security language and confirm package name and business ownership.
- Verify tests from a clean environment and review dependency audit.
- Enable GitHub Actions and allow `GITHUB_TOKEN` to create releases (`contents: write` permission).
- Decide whether to obtain a Windows code-signing certificate and Apple Developer ID/notarization. Unsigned builds may be flagged by operating systems.

## Automated release

When the desktop branch is published, its CI also attempts to create a `desktop-v0.1.0` release automatically. If that does not run or fails, push an annotated version tag to build manually:

```bash
git tag -a v0.1.0 -m 'HingeZero Memory Desktop v0.1.0'
git push origin v0.1.0
```

The `.github/workflows/release.yml` workflow runs tests and a dependency audit, builds the desktop app on Windows, Linux and macOS, attaches archives to a GitHub Release and emits `SHA256SUMS.txt` for download verification. The workflow does not automatically sign binaries or notarize macOS packages.

If you are using the **separate release branch**, tag that branch commit, not the research/main branch:

```bash
git switch desktop-release-v0.1.0
git tag -a v0.1.0 -m 'HingeZero Memory Desktop v0.1.0'
git push origin v0.1.0
```

GitHub Releases are repository-wide. A cleaner future setup is a dedicated `HingeZero-Memory-Desktop` repository, if available. No existing benchmark files need to be overwritten.

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
