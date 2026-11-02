"""Check setup does not place credentials in command arguments or files."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "chatgpt-bridge" / "connect.py"
spec = importlib.util.spec_from_file_location("hz_bridge_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def test_read_only_check_does_not_configure_tunnel(monkeypatch):
    replies = iter(["12345", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    monkeypatch.setattr(setup, "getpass", lambda _: "r" * 43)
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda args, **kw: calls.append((args, kw)))
    monkeypatch.setenv("HINGEZERO_ENABLE_WRITES", "1")
    monkeypatch.setenv("HINGEZERO_WRITE_TOKEN", "inherited-token")
    assert setup.main(["--check-only"]) == 0
    assert len(calls) == 1 and calls[0][0][-1] == "--check"
    assert "HINGEZERO_ENABLE_WRITES" not in calls[0][1]["env"]
    assert "HINGEZERO_WRITE_TOKEN" not in calls[0][1]["env"]


def test_write_setup_keeps_secrets_out_of_arguments_and_output(monkeypatch, capsys):
    replies = iter(["12345", "yes", "tunnel_synthetic123"])
    secrets = ["r" * 43, "w" * 43, "synthetic-runtime-key"]
    hidden_replies = iter(secrets)
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    monkeypatch.setattr(setup, "getpass", lambda _: next(hidden_replies))
    monkeypatch.setattr(setup.shutil, "which", lambda _: "/synthetic/tunnel-client")
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda args, **kw: calls.append((args, kw)))
    assert setup.main([]) == 0
    assert len(calls) == 4
    for args, _ in calls:
        assert not any(secret in " ".join(args) for secret in secrets)
    output = capsys.readouterr().out
    assert not any(secret in output for secret in secrets)
    assert calls[-1][1]["env"]["HINGEZERO_ENABLE_WRITES"] == "1"
    assert calls[-1][1]["env"]["CONTROL_PLANE_API_KEY"] == secrets[-1]
