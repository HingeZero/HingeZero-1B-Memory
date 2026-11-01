# HingeZero Memory Desktop v0.1.0

**Private, offline-first memory vault with deterministic associative retrieval.**  
A standalone desktop integration package for HingeZero Memory, built around the dual-tanh memory operator.

## Start in 60 seconds

1. Open the [Releases](https://github.com/HingeZero/HingeZero-1B-Memory/releases) page and download the archive for your operating system **after the release build has passed**.
2. Extract the archive. Start `HZMemory` (Linux), `HZMemory.exe` (Windows), or `HZMemory.app` (macOS).
3. On first launch, read the permissions notice, tick consent and create a passphrase of 12+ characters. There is **no default password and no recovery backdoor**.
4. Select **Add memory** or **Import selected file** and choose what to save.
5. Search from the **Memories & Search** tab. You can also optionally connect a local Ollama AI or another trusted local app.

**Permissions:** The application never asks for administrator privileges, does not scan your files, uses no analytics or telemetry, and only imports files you select. It writes its encrypted vault under `~/HingeZeroMemory/vault.sqlite3` (your home directory). The local API and Ollama connection are off until you turn them on. It does **not** modify or inject itself into other AI programs.

**Realistic compatibility:** Windows and macOS packages are not signed or notarized in v0.1.0; operating-system warnings are expected, so only download from the verified release and check SHA-256 hashes. Linux one-file binaries depend on glibc compatibility. Users can always run from Python source.

## What it does

- **Persistent local encrypted memory:** AES-256-GCM per record, PBKDF2-HMAC-SHA256 password derivation (600k rounds), encrypted backup; no stored password or recovery key.
- **Recall:** Deterministic lexical retrieval (feature-hashed word vectors) plus optional HingeZero dual-tanh two-step candidate refinement. The core equation is `φ(h) = tanh(h) + α·tanh(2h)`. Results provide the original stored notes as evidence.
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

## Scope and IP

This is a new *desktop integration* around the HingeZero operator, not the full 1-billion-record disk-scanning research demonstration. The user-friendly app currently stores up to 20,000 encrypted memory chunks with a linear in-memory candidate search. It is not a substitute for the billion-record C++ engine or a production multi-tenant server.

**License:** No redistribution license is included in this draft. The repository owner should choose the software license and confirm any packaging/release terms before publishing for public reuse. Source accessibility alone is not an open-source license.
