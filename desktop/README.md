# HingeZero Memory Desktop v0.1.5

**Private, offline-first memory vault with deterministic associative retrieval.**  
A standalone desktop integration package for HingeZero Memory, built around the dual-tanh memory operator.

## Start in 60 seconds

1. Open the [Releases](https://github.com/HingeZero/HingeZero-1B-Memory/releases) page and download the archive for your operating system **after the release build has passed**.
2. Extract the archive. Start `HZMemory` (Linux), `HZMemory.exe` (Windows), or `HZMemory.app` (macOS).
3. On first launch, read the permissions notice, tick consent and create a passphrase of 12+ characters. There is **no default password and no recovery backdoor**.
4. Select **Add memory** or **Import selected file** and choose what to save.
5. Search from the **Memories & Search** tab. You can also optionally connect a local Ollama AI or another trusted local app.

**Permissions:** The application never asks for administrator privileges, does not scan your files, uses no analytics or telemetry, and only imports files you select. It writes its encrypted vault under `~/HingeZeroMemory/vault.sqlite3` (your home directory). The local API and Ollama connection are off until you turn them on. It does **not** modify or inject itself into other AI programs.

**Realistic compatibility:** Windows and macOS packages are not signed or notarized in v0.1.5; operating-system warnings are expected, so only download from the verified release and check SHA-256 hashes. Linux one-file binaries depend on glibc compatibility. Users can always run from Python source.

## What it does

- **Persistent local encrypted memory:** AES-256-GCM per record, PBKDF2-HMAC-SHA256 password derivation (600k rounds), encrypted backup; no stored password or recovery key.
- **Recall:** Deterministic lexical candidate retrieval with the **unchanged original HingeZero Core** (8-step dual-tanh refinement), genuine HingeZero Witness verification of stored-state identity, and a session-local retaining loop with rollback. The core equation is `φ(h) = tanh(h) + α·tanh(2h)`. Results provide the original stored notes as evidence; Witness verification does not establish factual truth.
- **Local AI integration:** Optional Ollama embedding model `embeddinggemma` and chat model `llama3.2:3b`. These models must be installed separately; app never downloads them automatically. Memory sent to Ollama is sent to **127.0.0.1** only, after the user enables it and approves the action.
- **Documents:** User-selected TXT, Markdown, CSV, JSON, DOCX and text-based PDF; importer enforces type and size limits. Scanned/image PDFs require OCR, not included.
- **Local API:** Optional bearer-token-protected JSON endpoints for `/v1/search` and `/v1/remember`, bound to `127.0.0.1` on a random free port. The token changes each launch, and access stops on shutdown.

**Important limitations:** This app does not turn an LLM into AGI, eliminate hallucinations, automatically remember every conversation or improve every retrieval. Lexical search is not semantic until you opt into a local embedding model. The refinement may help some queries but not all. Retrieved text can contain untrusted instructions; the app tells the model to treat it as data, but prompt injection defenses are not guaranteed. Do not rely on this for clinical, emergency or safety-critical decisions.

## Running from source (Python 3.11+)

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python -m hzdesktop
```

Linux Python may need the system package `python3-tk`. `tkinter` is included in most Windows/macOS Python installers. All app behavior works without Ollama, internet access or an external service.

## Optional local AI

1. Install [Ollama](https://ollama.com/) **independently** and ensure it only binds locally.
2. In a terminal run:

   ```bash
   ollama pull embeddinggemma
   ollama pull llama3.2:3b
   ```
3. Open **Permissions & Integration**, select **Allow sharing with local Ollama** and verify the two model names. On every embed/chat operation, consent is requested. This app connects only to `127.0.0.1:11434`, never to cloud APIs.
4. Create or import new notes with embedding enabled to store their embeddings **encrypted**. Switching models doesn't automatically re-embed old notes.
5. Use **Ask local AI** to retrieve source notes and ask your model a question. Inspect the original records before relying on an answer.

## Local API for existing AI tools

With the app running, open **Permissions & Integration → Start local API**. Copy the port and session token shown only in the app. On the same computer:

```python
import json
from urllib.request import Request, urlopen

port = 12345                  # replace with shown port
token = 'PASTE_SESSION_TOKEN'  # do not hardcode into shared source code
body = json.dumps({'query': 'What is the project deadline?'}).encode('utf-8')
request = Request(f'http://127.0.0.1:{port}/v1/search', data=body,
                  headers={'Content-Type':'application/json',
                           'Authorization': 'Bearer ' + token})
with urlopen(request, timeout=5) as response:
    print(json.load(response))
```

To save a new memory use `POST /v1/remember` with JSON `{"title":"Title","content":"New memory content"}` and the same Authorization header. There are **no external network endpoints** and no CORS. Treat the session token as a password: anyone with it who can access localhost can read and write memories. The API is disabled by default and must be started manually each session. Use the Stop button to revoke access.

## Security, data control and backup

See [SECURITY.md](SECURITY.md) for threat model, safeguards, risks and reporting. Original imported files are not modified. Saved records are encrypted before being written to SQLite. Notes may be deleted individually. Click **Encrypted backup** to copy the encrypted database; its passphrase is the same as the original vault. Back up regularly; losing the password makes your data unrecoverable. You can remove the app and erase the vault folder yourself to remove local records (also check any backups).

## Test locally

```bash
python -m pip install -r requirements-build.txt
python -m pytest -q
python -m hzdesktop.selfcheck
```

This checks encrypted persistence, wrong-password failure, deterministic retrieval, document ingestion, and authenticated localhost API. Actual signed installation packages, platform security warnings and all possible models are not covered by unit tests.

## Release mechanics

The provided GitHub Actions workflow builds Windows, Linux and macOS standalone archives, runs tests and a dependency vulnerability audit, creates SHA256 checksums, and publishes downloadable assets under a tagged GitHub Release. Workflow permissions are limited to repository content write for the release job. Read [RELEASING.md](RELEASING.md) before making the release public.

## Licensing: free noncommercial / paid commercial

**HingeZero Memory Desktop (the `desktop/` application source and the desktop binaries distributed under this release) is source-available under [PolyForm Noncommercial 1.0.0](LICENSE.md), subject to the [Required Notice](NOTICE.txt).**

- Free noncommercial personal use, study, experiments, and other purposes permitted by the licence. Some charities, universities and other noncommercial organizations have rights under the standard licence text. The official licence controls, not this summary.
- **Commercial deployment, internal business use, incorporation into paid products, SaaS offerings or commercial redistribution require a separate paid written licence.** See [Commercial Licensing](COMMERCIAL-LICENSING.md). No commercial rights are granted automatically by downloading a binary.
- Commercial licence pricing and scope are negotiated; there is no checkout or automatic entitlement yet.
- This desktop-specific licence does **not** change the rights or licensing of other research/source files in the parent `HingeZero-1B-Memory` repository or other HingeZero projects. Independent third-party software retains its own licences.
- Before relying on the company as licensor, confirm chain of ownership and third-party obligations. Previous versions remain under the terms that applied when distributed.

## Scope and IP

This is a new *desktop integration* around the HingeZero operator, not the full 1-billion-record disk-scanning research demonstration. The user-friendly app currently stores up to 20,000 encrypted memory chunks with a linear lexical/optional local-embedding candidate search and up to 256 candidates supplied to the original HingeZero Core. It is not a substitute for the billion-record C++ engine or a production multi-tenant server.

**Licence:** See [LICENSE.md](LICENSE.md), [NOTICE.txt](NOTICE.txt), and [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md). PolyForm Noncommercial is **source-available, not an OSI-approved open-source licence**. A separate paid written agreement is needed for commercial use.

## Verification status (v0.1.5)

The release pipeline gates downloads behind tests, dependency audits (runtime **and** build-time) and Python Bandit security analysis. GitHub CodeQL analyzes Python and workflows separately. The checks cannot prove absence of security flaws, and unsigned binaries may be blocked by Windows/macOS. The software source is public, but commercial/open-source redistribution rights require the copyright owner's explicit choice of licence.

## Changes in v0.1.3

- Fixed associative retrieval when the vault contains a mixture of lexical and local semantic embeddings, avoiding mismatched vector dimensions.
- Prevented encrypted backups from following dangling symlink destinations; a regression test confirms no redirected file is created.
- Added regression checks and whole-repository tests, plus free Semgrep and Gitleaks reviews.
- Existing v0.1.2 encrypted vaults use the same schema and can be opened with the same passphrase. No import or migration step is required.


## Core integration in v0.1.5

**Source fidelity:** The original `HingeZero_Core.py` (Git blob `ec0ec9c56c233b97038d88618ad9f2bcff26bcab`) is bundled **byte-for-byte unchanged** as `hzdesktop/HingeZero_Core.py`. Desktop retrieval calls its `HingeZeroWitness.refine()`, `observe()` and `verify()`; repeated desktop searches use `HingeZeroRetainingLoop` to maintain a session-local checkpoint with rollback under drift. Checkpoints reset when candidates change and are **not** persisted through restarts.

**Limits:** The desktop still uses a lexical/optional local embedding shortlist (maximum 256 candidates) and a local encrypted store (20,000 records). This is not the separate one-billion-bipolar-pattern C++ backend. Benchmarks of that backend or other HingeZero configurations are **not desktop performance measurements**. Witness verification checks stored-state identity, not memory correctness or the intended answer. There is no general-purpose semantic understanding without a separately enabled embedding model.


## ChatGPT MCP bridge (v0.1.5)

Optional separate HZMemory-ChatGPT-Bridge.zip provides a **read-only** MCP stdio server through OpenAI Secure MCP Tunnel. The desktop application now displays independent read-only and full-access local tokens. Never share the full-access token with the bridge. **Not automatically connected to ChatGPT**: requires eligible account/workspace permissions, a configured local tunnel, and an unlocked desktop vault. A retrieved note is sent to ChatGPT if the user invokes the search tool. See [bridge setup](chatgpt-bridge/README.md).
