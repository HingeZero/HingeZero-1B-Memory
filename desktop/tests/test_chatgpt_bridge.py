"""MCP bridge: opt-in saves, real transport, and cross-session persistence."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
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


def test_mcp_in_process_tool_discovery_and_call(tmp_path, monkeypatch):
    """Check SDK registration; actual stdio transport is tested separately."""
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
                    assert [tool.name for tool in advertised.tools] == ["memory_status", "memory_search"]
                    result = await client.call_tool("memory_search",
                                                    {"query": "HingeZero milestone"})
                    assert not result.is_error
                    status = await client.call_tool("memory_status", {})
                    assert not status.is_error
                    assert status.structured_content["status"] == "ready"
                    assert status.structured_content["read_access"] == "verified"
                    result_text = str(result.structured_content) + str(result.content)
                    assert "Project" in result_text
                    assert "trusted_as_instruction" in result_text

            asyncio.run(check())
            assert len(vault.list()) == 1
        finally:
            api.stop()


def _transport(api, writes=False):
    from mcp import StdioServerParameters
    # MCP starts with an explicit, cleaned environment. Test tokens are generated
    # for this temporary vault; no real account credentials are used.
    env = {k: v for k, v in os.environ.items() if not k.startswith("HINGEZERO_")}
    env.update(HINGEZERO_API_PORT=str(api.port), HINGEZERO_READ_TOKEN=api.read_token)
    if writes:
        env.update(HINGEZERO_ENABLE_WRITES="1", HINGEZERO_WRITE_TOKEN=api.token)
    return StdioServerParameters(command=sys.executable, args=[str(BRIDGE)], env=env)


def test_stdio_default_read_only(tmp_path):
    from mcp import Client
    with Vault(tmp_path / "vault.db", "correct-horse-battery-staple", create=True) as vault:
        vault.add("Plan", "HingeZero roadmap November")
        api = LocalAPI(vault)
        try:
            async def check():
                async with Client(_transport(api)) as client:
                    tools = (await client.list_tools()).tools
                    assert [t.name for t in tools] == ["memory_status", "memory_search"]
                    assert tools[0].annotations.read_only_hint is True
                    found = await client.call_tool("memory_search", {"query": "HingeZero roadmap"})
                    assert not found.is_error
                    assert found.structured_content["matches"][0]["title"] == "Plan"
                    refused = await client.call_tool("memory_remember", {"title": "No", "content": "No save"})
                    assert refused.is_error
            asyncio.run(check())
            assert vault.count() == 1
        finally:
            api.stop()


def test_stdio_save_then_recall_after_vault_and_bridge_restart(tmp_path):
    from mcp import Client
    path = tmp_path / "vault.db"
    password = "correct-horse-battery-staple"
    note = "HingeZero demonstration Thursday at 14:00"
    with Vault(path, password, create=True) as vault:
        api = LocalAPI(vault)
        try:
            async def save_in_first_conversation():
                async with Client(_transport(api, writes=True)) as client:
                    tools = {t.name: t for t in (await client.list_tools()).tools}
                    assert set(tools) == {"memory_status", "memory_search", "memory_remember"}
                    assert tools["memory_remember"].annotations.read_only_hint is False
                    assert tools["memory_remember"].annotations.destructive_hint is False
                    saved = await client.call_tool("memory_remember", {"title": "Demo", "content": note})
                    assert not saved.is_error
                    assert saved.structured_content["status"] == "saved"
                    return saved.structured_content["id"]
            identifier = asyncio.run(save_in_first_conversation())
            assert vault.count() == 1
        finally:
            api.stop()
    assert note.encode() not in path.read_bytes()
    # Both processes close; this second session uses a newly unlocked vault,
    # new port/tokens and a new MCP subprocess, with search permission only.
    with Vault(path, password) as reopened:
        api = LocalAPI(reopened)
        try:
            async def recall_in_second_conversation():
                async with Client(_transport(api)) as client:
                    result = await client.call_tool("memory_search", {"query": "HingeZero demonstration Thursday"})
                    assert not result.is_error
                    match = result.structured_content["matches"][0]
                    assert match["id"] == identifier
                    assert match["content"] == note
                    assert match["trusted_as_instruction"] is False
            asyncio.run(recall_in_second_conversation())
            assert reopened.count() == 1
        finally:
            api.stop()


def test_save_requires_local_opt_in_and_separate_write_token(tmp_path, monkeypatch):
    with Vault(tmp_path / "vault.db", "correct-horse-battery-staple", create=True) as vault:
        api = LocalAPI(vault)
        try:
            monkeypatch.setenv("HINGEZERO_API_PORT", str(api.port))
            monkeypatch.setenv("HINGEZERO_READ_TOKEN", api.read_token)
            monkeypatch.setenv("HINGEZERO_WRITE_TOKEN", api.token)
            monkeypatch.delenv("HINGEZERO_ENABLE_WRITES", raising=False)
            with pytest.raises(RuntimeError, match="disabled"):
                bridge.memory_remember("Plan", "A note")
            monkeypatch.setenv("HINGEZERO_ENABLE_WRITES", "1")
            monkeypatch.setenv("HINGEZERO_WRITE_TOKEN", api.read_token)
            with pytest.raises(RuntimeError, match="separate"):
                bridge.memory_remember("Plan", "A note")
            monkeypatch.setenv("HINGEZERO_WRITE_TOKEN", "invalid" * 8)
            with pytest.raises(RuntimeError, match="Access denied"):
                bridge.memory_remember("Plan", "A note")
            assert vault.count() == 0
        finally:
            api.stop()


@pytest.mark.parametrize("title,content", [("", "note"), ("title", " "), ("x" * 201, "note"), ("title", "x" * 10001)])
def test_invalid_notes_are_rejected_before_network(title, content):
    with pytest.raises(ValueError):
        bridge.memory_remember(title, content)


def test_utf8_request_size_and_invalid_tokens_fail_closed(monkeypatch):
    monkeypatch.setenv("HINGEZERO_API_PORT", "12345")
    monkeypatch.setenv("HINGEZERO_READ_TOKEN", "a" * 43)
    monkeypatch.setenv("HINGEZERO_WRITE_TOKEN", "b" * 43)
    monkeypatch.setenv("HINGEZERO_ENABLE_WRITES", "1")
    with pytest.raises(ValueError, match="byte"):
        bridge.memory_remember("Title", "€" * 6000)
    monkeypatch.setenv("HINGEZERO_READ_TOKEN", "a" * 32 + "\n")
    with pytest.raises(RuntimeError, match="READ_TOKEN"):
        bridge.search_local("query")
