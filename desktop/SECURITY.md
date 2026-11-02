# HingeZero Memory Desktop — Security and privacy

## Data flow

1. User explicitly selects a local file or types a note.
2. Text is extracted with limits: 8 MB maximum input, 120k extracted characters, 100 pages for PDFs, 100 chunks maximum, and 10k characters per record.
3. If the user **explicitly enables and confirms local Ollama processing**, relevant content may be sent to `http://127.0.0.1:11434` for embedding or responses. The app makes no cloud requests. The local Ollama process and any installed models have their own security/privacy properties.
4. Notes, titles, source labels and optional embeddings are encrypted as JSON using AES-256-GCM, with a fresh 96-bit nonce for each record and record ID as authenticated associated data (AAD).
5. The vault is an SQLite database in a private per-user directory, with restrictive POSIX permissions. The database file is not fully encrypted; the record IDs, schema and salt are visible. Some OS metadata and forensic artifacts may exist outside app control.
6. On vault unlock, AES keys and decrypted data reside in process RAM; memory wiping is best effort. There is no claim of resistance to a compromised operating system or live-memory inspection.

## Password and consent

- No login server, stored passphrase, telemetry, registration, or administrator permission.
- A first-run passphrase of at least 12 characters; derived via PBKDF2-SHA256 with 600,000 iterations and a random per-vault 16-byte salt. A strong, unique passphrase is recommended.
- No password reset or recovery key. Loss of password = loss of access.
- Wrong password or tampering triggers AES-GCM authentication failure.
- No automatic directory scanning; file access limited to user-selected import files.
- Ollama and local API are disabled by default. The app requests specific consent to send content to local Ollama.

## Optional API

- Binds only to IPv4 loopback `127.0.0.1`, ephemeral TCP port.
- Random 256-bit-equivalent bearer token shown within desktop application only.
- `POST` JSON requests, 16 KiB maximum body; authorization checked using constant-time comparison.
- No CORS support, no persistent token, no listener before user approval.
- API consumers with the token can **read and write** memory contents. Never expose this port via proxies, SSH tunnels, container port-mapping or internet routing. Other local users/processes with stolen token may have access.
- No TLS on localhost. Any compromise of the user's device can bypass this security boundary.

## Imported-content risk

Documents are treated as untrusted *text*, not code. No imported scripts or macros are executed. TXT/MD/CSV/JSON use text read only; DOCX extracts `word/document.xml` without executing macros; PDF uses pypdf text extraction. Large files are rejected. The parser dependencies are included in the vulnerability audit. Parsing adversarial documents is not risk free; only import files from trustworthy sources. **The application does not scan files for viruses** and does not promise perfect protection against parser vulnerabilities.

Prompts explicitly label retrieved memory as untrusted data. That reduces but does not eliminate prompt-injection and hallucination risks. This app does not automatically perform external actions on AI-generated text.

## Open issues before broad public deployment

- Windows app and macOS app are **unsigned and not notarized**. A security warning is possible; do not advise users to bypass OS protections uncritically. Prefer signing/notarizing builds before broad distribution.
- Disk encryption is per record, not whole-database or OS full-disk encryption.
- No automatic password rotation, 2FA or multi-device synchronization.
- Optional Ollama model response is not formally proven correct.
- GitHub workflow needs release assets and dependency audit to pass on every target OS.
- No third-party penetration test or formal security audit has been performed.

## Report a security bug

Please contact the repository owner privately, rather than publishing an exploit with user-data exposure. Avoid submitting real personal data into GitHub issues.

## Automated security verification for v0.1.4

- GitHub Actions executes unit/regression tests, HingeZero self-check, Bandit static Python security analysis, and pip-audit on runtime and build requirements before packaging.
- GitHub CodeQL scans Python and Actions workflows weekly and on pushes to the desktop release branch; findings should be reviewed on GitHub's Security tab. A successful CodeQL run does not imply zero alerts.
- The encrypted backup implementation reserves output atomically with owner-only permissions and preserves permissions of user-selected backup folders.
- DOCX XML parsing uses defusedxml to reject entity expansion.
- Public binaries are **not signed, notarized or independently penetration-tested**. No malware-scanning certificate is claimed.

## Original HingeZero Core

Desktop v0.1.4 integrates the original eight-step HingeZero Core and Witness; the Witness only verifies a returned candidate matches a stored representation. It does not certify correctness, prevent prompt injection, or ensure the intended memory was chosen. The retaining loop checkpoint is session-local, not encrypted for persistence across restarts. The 1-billion C++ research engine remains separate.
