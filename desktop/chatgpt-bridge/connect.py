"""Interactive local setup for a private HingeZero Secure MCP Tunnel.

Run on the computer hosting the unlocked desktop vault. Secrets are read with
getpass and passed only in child-process environments, never argv or files.
"""
from __future__ import annotations

import argparse
from getpass import getpass
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true",
                        help="Check the local desktop connection without configuring a tunnel")
    args = parser.parse_args(argv)
    print("Start HingeZero Desktop v0.1.5+, unlock the vault and enable its local API.")
    env = os.environ.copy()
    for name in ("HINGEZERO_ENABLE_WRITES", "HINGEZERO_WRITE_TOKEN"):
        env.pop(name, None)
    env["HINGEZERO_API_PORT"] = input("Local API port: ").strip()
    env["HINGEZERO_READ_TOKEN"] = getpass("Read-only desktop token (hidden): ").strip()
    save = input("Allow this bridge to save notes you request? [y/N]: ").strip().lower()
    if save in ("y", "yes"):
        env["HINGEZERO_WRITE_TOKEN"] = getpass("Desktop full-access token (local only, hidden): ").strip()
        env["HINGEZERO_ENABLE_WRITES"] = "1"
    bridge = Path(__file__).resolve().with_name("bridge.py")
    try:
        subprocess.run([sys.executable, str(bridge), "--check"], env=env, check=True)
        if args.check_only:
            return 0
        tunnel_client = shutil.which("tunnel-client")
        if not tunnel_client:
            print("Local API checked. Install OpenAI tunnel-client before continuing:")
            print("https://github.com/openai/tunnel-client/releases/latest")
            return 1
        tunnel_id = input("Existing OpenAI tunnel ID: ").strip()
        if not re.fullmatch(r"tunnel_[A-Za-z0-9]+", tunnel_id):
            print("Expected a tunnel ID from OpenAI Platform tunnel settings.")
            return 1
        env["CONTROL_PLANE_API_KEY"] = getpass("OpenAI tunnel runtime API key (hidden): ").strip()
        if not env["CONTROL_PLANE_API_KEY"]:
            print("A runtime key is required to start the tunnel.")
            return 1
        command_parts = [sys.executable, str(bridge)]
        command = (subprocess.list2cmdline(command_parts) if os.name == "nt"
                   else shlex.join(command_parts))
        profile = "hingezero-memory-save-recall" if save in ("y", "yes") else "hingezero-memory"
        subprocess.run([tunnel_client, "init", "--sample", "sample_mcp_stdio_local",
                        "--profile", profile, "--tunnel-id", tunnel_id,
                        "--mcp-command", command], env=env, check=True)
        subprocess.run([tunnel_client, "doctor", "--profile", profile, "--explain"],
                       env=env, check=True)
        print("Connect this tunnel in ChatGPT Plugins > Add custom MCP server > Tunnel.")
        print("Keep this terminal and the desktop vault open. Ctrl+C stops the tunnel.")
        print("ChatGPT integration is verified only after a tool call succeeds there.")
        subprocess.run([tunnel_client, "run", "--profile", profile], env=env, check=True)
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nStopped.")
        return 130
    except (OSError, subprocess.CalledProcessError):
        print("Connection setup failed. Check the desktop API and tunnel-client diagnostics.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
