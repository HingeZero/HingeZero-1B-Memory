# HingeZero ChatGPT bridge v0.1.6 — save and recall

Connect your local HingeZero vault to ChatGPT through OpenAI Secure MCP Tunnel.
Compatible with HingeZero Memory Desktop v0.1.5 or later.

| Tool | Purpose | Availability |
| --- | --- | --- |
| `memory_status()` | Check the live local vault API without returning note contents | Default, read-only |
| `memory_search(query)` | Retrieve up to five saved notes | Default, read-only |
| `memory_remember(title, content)` | Add one user-approved note for future conversations | Explicit local write opt-in only |

Both tools return structured results. A successful save returns `status: saved`
and a record ID. Do not describe a failed or interrupted operation as saved.
Repeated saves create separate notes; check the vault before retrying.

This adds saving to the v0.1.5 bridge. It does not automatically capture chats
or change ChatGPT's built-in memory. The AI must call the tools.

## ChatGPT availability and connection boundaries

Custom MCP servers require a supported ChatGPT workspace, its permissions,
and a running Secure MCP Tunnel. As of November 2026, ChatGPT documentation
lists self-service custom MCP server access on Business and Enterprise/Edu web
workspaces; a personal Plus account cannot simply add this integration to an
existing conversation. Check the current [ChatGPT support article](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

This bridge does not create a ChatGPT app, tunnel ID, workspace authorization,
or a live connection on its own. No tool access should be claimed until
ChatGPT successfully invokes `memory_status()`. `memory_status()` only checks
that the local desktop API responds; it does not check writing or persistence.
Never share vault tokens, tunnel runtime API keys, or your passphrase in chat.

## Start on your laptop

1. Launch HingeZero Memory Desktop, unlock the vault and select
   **Permissions & Integration → Start local API**.
2. Extract the bridge download on the same computer. In that directory:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python connect.py
   ```

   On Windows, use `python` instead of `python3` and activate with
   `.venv\Scripts\activate`.
3. The helper asks for the API port and read-only token. It separately asks
   whether to enable saving. If yes, enter the desktop full-access token **in
   this local helper only**. Hidden token inputs are not echoed or written into
   command history, arguments or configuration files by this helper.
   Never paste tokens or API keys into ChatGPT.
4. The helper checks the local API, then configures and runs the official
   `tunnel-client` with your existing OpenAI tunnel ID and runtime API key.
   Keep the helper and unlocked desktop vault running.

To check local search without configuring a tunnel, run
`python connect.py --check-only`. This asks only for the read-only token;
it does not request write permissions, test saving, or prove ChatGPT is
connected.

## One-time OpenAI account setup

Follow the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
You need an existing tunnel associated with your ChatGPT workspace and Platform
organization, relevant tunnel permissions and a runtime API key. Install
[OpenAI tunnel-client](https://github.com/openai/tunnel-client/releases/latest)
and inspect `tunnel-client help quickstart` for current CLI options.

On ChatGPT web, open **Plugins → + → Add custom MCP server → Tunnel**, select
that tunnel, configure authentication, review permissions, create and install
the plugin. Select it in conversations where you want HingeZero.
Availability depends on account/workspace access.

Changing the repository or running tests does not connect your account.
**Setup is complete only after a tool call succeeds from ChatGPT.**

## Verify remembering between conversations

Use synthetic information first:

1. With saving enabled, ask ChatGPT: “Use HingeZero memory_remember to save a
   note titled Bridge test: My test project is Cedar and its demo is Thursday
   at 14:00.”
2. Confirm the actual tool result has `status: saved` and check the note in the
   desktop vault. A conversational “I'll remember” without a tool call is not
   evidence of a HingeZero save.
3. In ChatGPT, first call `memory_status()` and confirm `status=ready`. Open a
   new chat, select the same plugin and ask: “Use HingeZero memory_search
   to find the saved Cedar project demo time.”
4. Confirm the tool retrieves the original note and the AI answers from it.
5. To test persistence, close the helper/API and desktop vault, reopen the vault,
   restart the helper with the new port/tokens and repeat step 3.

For normal use, request specific saved facts or summaries and ask for retrieval
when needed. This bridge does not automatically archive conversations.
Host permissions determine whether a write requires approval.

## Manual environment configuration

The helper is optional. Supply these values through a trusted local secret-entry
method, never through chat or literal command-line arguments:

| Variable | Meaning |
| --- | --- |
| `HINGEZERO_API_PORT` | Desktop API port |
| `HINGEZERO_READ_TOKEN` | Desktop read-only token; always used for search |
| `HINGEZERO_ENABLE_WRITES` | Exactly `1` to advertise saving; otherwise read-only |
| `HINGEZERO_WRITE_TOKEN` | Separate full-access token for enabled saves |
| `CONTROL_PLANE_API_KEY` | Runtime key for the official tunnel client |

`python bridge.py --check` checks local search; `python bridge.py` starts the
stdio server. Use absolute paths to Python and bridge.py in a tunnel profile.

Tokens remain in local processes, never tool arguments or results. The bridge
has no public listener and calls only `127.0.0.1`. It exposes no edit/delete
tools. Stop the API or tunnel to revoke access. Restarting the API rotates its
port/tokens. Selected notes are sent to ChatGPT during retrieval, so that
connection is not entirely offline. Notes are reference data, not instructions;
Witness verifies stored-state identity, not factual truth.

## Developer verification

From the repository's `desktop` directory:

```bash
python -m pip install -r requirements-build.txt -r chatgpt-bridge/requirements.txt
python -m pytest -q
```

Tests use real MCP stdio subprocesses and a real encrypted vault. They check
read-only discovery, permission failures, enabled saving, structured results
and recall after the bridge, API and vault all restart.
Local tests do not establish a live ChatGPT account connection.

Desktop licensing applies to this `desktop/` bridge; see the included licence,
required notice and commercial-licensing document.
