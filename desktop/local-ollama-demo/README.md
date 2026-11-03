# HingeZero Local AI Memory — developer quickstart

**David Duffy / HingeZero Ltd · 3 November 2026**

**Status: developer preview.** Nine local tests passed against simulated HingeZero and Ollama servers. This is an opt-in client for the *existing* [HingeZero Memory Desktop](https://github.com/HingeZero/HingeZero-1B-Memory/tree/main/desktop) encrypted vault; it is not a replacement memory engine or a released desktop build.

## What this does

- **Search** through the desktop's existing authenticated `/v1/search` endpoint.
- **Remember** through `/v1/remember`, only with a full-access session token and the user's explicit `YES`.
- **Ask** an already-installed local Ollama model using up to five retrieved notes, requesting bracketed citations `[1]`, `[2]`, etc. If no notes match, the helper returns **INSUFFICIENT EVIDENCE** without calling Ollama.
- Both services use localhost (`127.0.0.1`). No cloud services, new listeners, automatic model downloads, or automatic memory capture. The client has no additional Python dependencies.

## Setup (Linux / Pop!_OS)

1. Run [HingeZero Memory Desktop](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md). Unlock the vault and add a synthetic test memory.
2. Choose **Permissions & Integration → Start local API**. Copy the displayed **port** and **read-only session token** from the application. The API must remain enabled for the helper to work.
3. Download [hz_local_assistant.py](hz_local_assistant.py) to your laptop and, in that directory, run:

```bash
python3 hz_local_assistant.py search --port 12345
```

Replace **12345** with the actual port displayed inside the desktop application. The helper will request the token securely without echoing it. Enter a question and inspect the returned original notes.

To ask a locally installed Ollama model:

```bash
ollama list
python3 hz_local_assistant.py ask --port 12345 --model llama3.2:3b
```

Ollama must already be available on `127.0.0.1:11434` with that model installed. The returned text is **model-generated**; verify its claims against the original records.

To save a memory, use the desktop app's **full-access** session token, not the read-only token:

```bash
python3 hz_local_assistant.py remember --port 12345
```

The helper asks for a title, content and explicit `YES` confirmation before writing. A save is reported only after the desktop API returns an actual record ID. On Windows, use `python` instead of `python3` where applicable.

**Never paste session tokens in GitHub, a chat message, or a public issue.** Tokens and port change when the desktop API restarts; the helper does not save them.

## Test

```bash
python3 -m unittest -v test_hz_local_assistant.py
```

**Measured locally:** 9/9 tests passed (Python 3.13). They use fake localhost services to exercise read-only permission enforcement, saved-ID confirmation, explicit confirmation, invalid credentials, input limits, local model invocation and abstention when no memories match. **An end-to-end run against a real unlocked HingeZero vault and a real Ollama installation has not yet been verified.**

## Boundaries

The **original HingeZero Core, Witness verification, retrieval and encryption** remain inside HingeZero Memory Desktop. The helper does not reimplement or bypass them. The current `/v1/search` response does not expose a per-record Witness flag, so this client cannot independently claim to have rechecked one.

The [0–8-step evidence-gate experiment](../../benchmarks/witness-gated-8step-2026-11-03/README.md) is a **separate research prototype** and is *not* automatically enabled by this helper. Retrieved notes can be false, stale or hostile. Search score is not factual certainty; instructing the model to cite notes does not guarantee correctness or defeat prompt injection.

This directory is part of the **desktop component**, governed by its [licence](../LICENSE.md), [required notice](../NOTICE.txt) and [commercial terms](../COMMERCIAL-LICENSING.md).

**Next checkpoint:** user-tested Linux save → close/reopen → search → local-model answer, followed by measurable accuracy, latency, and failure-mode comparisons.
