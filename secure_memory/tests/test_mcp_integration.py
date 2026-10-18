"""End-to-end read-only stdio bridge test (requires the optional MCP extra)."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

from hingezero_secure_memory import SecureMemory


class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_only_stdio_service(self):
        try:
            from mcp.client.stdio import StdioServerParameters, stdio_client
            from mcp import ClientSession
        except ImportError:
            self.skipTest("MCP extra not installed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "vault.sqlite"
            secret = "generated-fixture-strong-test-secret"
            with SecureMemory(path, secret) as vault:
                vault.remember("The workshop meeting begins on Thursday morning", "local_test", consent=True)
                _, token = vault.grant("end-to-end-test", right="read", days=1)
            cfg = StdioServerParameters(command=sys.executable,
                args=["-m", "hingezero_secure_memory.mcp_server"],
                env={**os.environ, "HINGEZERO_DB": str(path),
                     "HINGEZERO_VAULT_PASSPHRASE": secret,
                     "HINGEZERO_CAPABILITY": token})
            async with stdio_client(cfg) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), 20)
                    tools = await asyncio.wait_for(session.list_tools(), 20)
                    self.assertEqual([tool.name for tool in tools.tools], ["memory_recall"])
                    result = await asyncio.wait_for(session.call_tool("memory_recall", {"query": "workshop meeting Thursday"}), 20)
                    self.assertFalse(result.isError)
                    combined = "\n".join(str(getattr(c, "text", "")) for c in result.content)
                    self.assertIn("workshop meeting begins", combined)
                    self.assertIn("trusted_as_instruction", combined)


if __name__ == "__main__":
    unittest.main()
