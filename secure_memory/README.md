# HingeZero Secure Memory

Local-first deterministic associative memory for AI applications, by **David Duffy**.

**Version 0.1.0 — developer preview for non-sensitive local evaluation, not a production security certification.**

**Licence:** [PolyForm Noncommercial 1.0.0](LICENSE.md). Commercial use requires a separate **written commercial licence**. See [commercial licensing](COMMERCIAL-LICENSING.md).

## Installation

Clone this repository and enter the secure_memory directory. Requires Python 3.10+; Linux and macOS are the current local evaluation targets.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[mcp]'
```

This installation includes the original, unchanged HingeZero_Core.py, a deterministic local lexical text adapter, an encrypted SQLite vault and a read-only MCP server. No large language model, remote API or cloud connection is bundled. It is not yet distributed through PyPI.

## Owner setup

```bash
hzm init
hzm add --source user_note --consent
hzm search 'words from stored memory'
hzm list
hzm grant --label local-assistant --scope general --right read --days 7
```

The owner CLI prompts securely for the local vault passphrase. Keep this secret and backed up; losing it means losing your encrypted data. Application capabilities are printed once, are scoped and can be revoked with hzm revoke <capability_id>.

## Model Context Protocol (MCP)

Configure the AI host to launch hzm-mcp as a local STDIO process. Supply secrets through a trusted local launcher or OS secret manager; never commit them:

- HINGEZERO_DB — absolute vault path.
- HINGEZERO_VAULT_PASSPHRASE — vault passphrase.
- HINGEZERO_CAPABILITY — read-only capability from hzm grant.
- HINGEZERO_SCOPE — optional permitted scope, default general.

The MCP bridge exposes only memory_recall(query). Writes are deliberately absent: a model-generated "user authorised" boolean cannot prove user consent. The host must treat returned records as untrusted text, not instructions.

To implement always-on retrieval in a host, call the local OptInMemoryHook.on_user_query method after the user opts in. Capture is not automatic: the trusted host must explicitly approve each memory record and call on_memory_event using role=user, kind=approved_memory. The package cannot intercept conversations in other applications by itself.

## Python API

```python
from hingezero_secure_memory import SecureMemory

with SecureMemory("/home/me/.local/share/hzm/vault.db", passphrase) as vault:
    rid = vault.remember("Workshop opens at eight", "user_note", consent=True)
    _, token = vault.grant("local-assistant", right="read", days=7)
    found = vault.recall_as(token, "workshop opening hours")
    print(found.as_dict())
```

Passphrase is supplied by the trusted owner application. Never expose remember() to an untrusted AI model.

## Design and boundaries

The full original eight-step HingeZero dual-tanh refinement and witness are used for memory retrieval. The vault limits the developer preview to 4,096 records. This is not the separate billion-memory C++ backend. The encoder hashes tokens and bigrams deterministically, rather than calculating semantic embeddings; retrieval quality has not been established for unrestricted conversation data.

Encrypted storage verifies stored bytes; HingeZero Witness verifies exact stored-state identity. Neither mechanism proves the memory factually true, current or the memory originally intended by the user. Similarity and margin abstention are conservative uncalibrated heuristics.

Sensitive data, medical use, production cloud deployments and autonomous high-consequence decisions are outside the scope of this developer preview. Before deployment review [security](SECURITY.md), [privacy](PRIVACY.md) and the [release checklist](RELEASE-CHECKLIST.md).

## Testing

```bash
python -m pip install '.[dev]'
python -m unittest discover -s tests -v
python -m compileall -q src
python -m pip check
bandit -r src -ll
pip-audit
```

CI is configured for multiple Python versions, dependency and static-security checks. Passing tests is not a certification of 100% security or legal compliance.

Copyright © 2026 David Duffy. All rights reserved except under the licences expressly granted in LICENSE.md or a separate written commercial agreement.
