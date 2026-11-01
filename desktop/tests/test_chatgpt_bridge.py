"""Read-only ChatGPT MCP bridge tests, including real vault integration."""
import importlib.util
from pathlib import Path
import pytest
from hzdesktop.api import LocalAPI
from hzdesktop.vault import Vault

BRIDGE = Path(__file__).resolve().parents[1] / "chatgpt-bridge" / "bridge.py"
spec = importlib.util.spec_from_file_location("hz_chatgpt_bridge", BRIDGE)
assert spec and spec.loader
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def test_real_vault_search_and_no_write(tmp_path, monkeypatch):
    with Vault(tmp_path / "vault.db", "correct-horse-battery-staple", create=True) as vault:
        vault.add("Plan", "HingeZero roadmap milestones for November")
        api = LocalAPI(vault)
        try:
            monkeypatch.setenv("HINGEZERO_API_PORT", str(api.port))
            monkeypatch.setenv("HINGEZERO_READ_TOKEN", api.read_token)
            result = bridge.search_local("HingeZero roadmap")
            assert result["status"] == "found"
            assert result["matches"][0]["title"] == "Plan"
            assert result["matches"][0]["trusted_as_instruction"] is False
            assert len(vault.list()) == 1
        finally:
            api.stop()


def test_fails_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("HINGEZERO_API_PORT", raising=False)
    monkeypatch.delenv("HINGEZERO_READ_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        bridge.search_local("project")


def test_rejects_oversized_queries(monkeypatch):
    monkeypatch.setenv("HINGEZERO_API_PORT", "1")
    monkeypatch.setenv("HINGEZERO_READ_TOKEN", "a" * 43)
    with pytest.raises(ValueError):
        bridge.search_local("x" * 2001)


def test_only_loopback_search_endpoint(monkeypatch):
    called = {}
    class Response:
        status = 200
        def read(self, size):
            return b'{"results":[{"id":"1","title":"safe","content":"text","source":"user","score":1}]}'
    class Connection:
        def __init__(self, host, port, timeout):
            called.update(host=host, port=port)
        def request(self, method, path, body, headers):
            called.update(method=method, path=path)
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setenv("HINGEZERO_API_PORT", "54231")
    monkeypatch.setenv("HINGEZERO_READ_TOKEN", "a" * 43)
    monkeypatch.setattr(bridge, "HTTPConnection", Connection)
    result = bridge.search_local("memory")
    assert (called["host"], called["method"], called["path"]) == (
        "127.0.0.1", "POST", "/v1/search")
    assert result["matches"][0]["trusted_as_instruction"] is False


def test_mcp_protocol_tool_discovery_and_call(tmp_path, monkeypatch):
    """Exercise the *actual MCP protocol*, not just a Python helper function."""
    import asyncio
    from mcp import Client

    with Vault(tmp_path / "vault.db", "correct-horse-battery-staple", create=True) as vault:
        vault.add("Project", "HingeZero milestone in November")
        api = LocalAPI(vault)
        try:
            monkeypatch.setenv("HINGEZERO_API_PORT", str(api.port))
            monkeypatch.setenv("HINGEZERO_READ_TOKEN", api.read_token)

            async def check():
                async with Client(bridge.mcp) as client:
                    advertised = await client.list_tools()
                    assert [tool.name for tool in advertised.tools] == ["memory_search"]
                    result = await client.call_tool("memory_search",
                                                    {"query": "HingeZero milestone"})
                    assert not result.is_error
                    result_text = str(result.structured_content) + str(result.content)
                    assert "Project" in result_text
                    assert "trusted_as_instruction" in result_text

            asyncio.run(check())
            assert len(vault.list()) == 1
        finally:
            api.stop()
