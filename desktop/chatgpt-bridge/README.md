# ChatGPT bridge for HingeZero Memory Desktop v0.1.5

This bridge provides one MCP stdio tool: memory_search(query). It accesses the existing encrypted desktop vault through a read-only token. It does not save, edit, delete or automatically capture ChatGPT conversations.

## On your laptop

1. Launch HingeZero Memory Desktop v0.1.5, unlock the vault, and select Permissions & Integration > Start local API. You must explicitly consent.
2. Note the displayed port and READ-ONLY ChatGPT token. Do not use or disclose the full-access token.
3. Extract HZMemory-ChatGPT-Bridge.zip on that same computer. Install Python 3.11+ and create a virtual environment:
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
4. In your trusted local terminal, enter the port and token, WITHOUT embedding them in command history:
   read -r -p 'Local API port: ' HINGEZERO_API_PORT
   read -r -s -p 'Read-only token: ' HINGEZERO_READ_TOKEN
   echo
   export HINGEZERO_API_PORT HINGEZERO_READ_TOKEN
5. Leave the HingeZero desktop API running; its tokens change every time the API starts.

## Secure MCP Tunnel

1. Open https://developers.openai.com/api/docs/guides/secure-mcp-tunnels and follow the current official instructions. You need an eligible ChatGPT workspace and Platform organization, a tunnel ID and a restricted runtime API key.
2. Install tunnel-client from https://github.com/openai/tunnel-client/releases/latest and inspect: tunnel-client help quickstart
3. In the same terminal holding the two HingeZero variables, configure a local stdio profile. Replace placeholders with your tunnel ID and ABSOLUTE executable/script paths:
   tunnel-client init --sample sample_mcp_stdio_local --profile hingezero-memory --tunnel-id YOUR_TUNNEL_ID --mcp-command '/absolute/path/chatgpt-bridge/.venv/bin/python /absolute/path/chatgpt-bridge/bridge.py'
   tunnel-client doctor --profile hingezero-memory --explain
   tunnel-client run --profile hingezero-memory
4. The tunnel client additionally needs CONTROL_PLANE_API_KEY, entered securely according to its official guide, and must remain running to receive tool calls.
5. On ChatGPT WEB (if your account/workspace supports it): Plugins > + > Add custom MCP server > Tunnel. Select your tunnel, review permissions, create and install the plugin.
6. Select the HingeZero plugin for your next prompt and ask: Use memory_search to retrieve my saved project plan.

## Safety and limitations

- Never expose this MCP stdio server through an anonymous public endpoint. The tunnel is outbound-only and user-controlled.
- The read-only token can search /v1/search but receives 403 from /v1/remember; always use the read-only token.
- Returned note content goes to ChatGPT when the tool runs. The local vault remains encrypted, but the tool call is NOT entirely offline.
- Notes are untrusted evidence; HingeZero Witness verifies stored-state identity, NOT factual accuracy.
- No automatic ChatGPT conversation archiving. ChatGPT only sees notes that were explicitly stored and then retrieved.
- Stop the API or tunnel to cut off access.
- If your ChatGPT account lacks custom MCP server permissions, this bridge cannot be activated inside this chat until access is available.
