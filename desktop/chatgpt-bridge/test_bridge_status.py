"""Regression tests for HingeZero's private ChatGPT bridge diagnostics."""
import importlib.util
import json
import os
from pathlib import Path
from unittest import SkipTest, TestCase
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: str):
    if path == "bridge.py" and importlib.util.find_spec("mcp") is None:
        raise SkipTest("Install chatgpt-bridge/requirements.txt to test MCP server")
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {"HINGEZERO_ENABLE_WRITES": ""}):
        spec.loader.exec_module(module)
    return module


class BridgeStatusTests(TestCase):
    def test_ready_status_returns_no_private_note_text(self):
        bridge = load_module("hzbridge_status_ready", "bridge.py")
        with patch.object(bridge, "_request", return_value={
                "results": [{"title": "secret", "content": "VERY_PRIVATE_NOTE"}]}), \
             patch.object(bridge, "_writes_enabled", return_value=False):
            reply = bridge.memory_status()
        self.assertEqual(reply["status"], "ready")
        self.assertEqual(reply["read_access"], "verified")
        self.assertEqual(reply["write_access"], "disabled")
        self.assertNotIn("VERY_PRIVATE_NOTE", json.dumps(reply))

    def test_unavailable_status_does_not_claim_success(self):
        bridge = load_module("hzbridge_status_error", "bridge.py")
        with patch.object(bridge, "_request", side_effect=RuntimeError("Vault locked")), \
             patch.object(bridge, "_writes_enabled", return_value=True):
            reply = bridge.memory_status()
        self.assertEqual(reply["status"], "unavailable")
        self.assertEqual(reply["read_access"], "not_verified")
        self.assertEqual(reply["write_access"], "configured_not_verified")

    def test_malformed_api_response_rejected(self):
        bridge = load_module("hzbridge_status_malformed", "bridge.py")
        with patch.object(bridge, "_request", return_value={"error": "bad"}):
            reply = bridge.memory_status()
        self.assertEqual(reply["status"], "unavailable")

    def test_check_only_does_not_request_write_token(self):
        setup = load_module("hzbridge_connect_check", "connect.py")
        with patch("builtins.input", return_value="12345") as prompt, \
             patch.object(setup, "getpass", return_value="read-only-token") as secret, \
             patch.object(setup.subprocess, "run") as process:
            result = setup.main(["--check-only"])
        self.assertEqual(result, 0)
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(secret.call_count, 1)
        self.assertEqual(process.call_count, 1)
