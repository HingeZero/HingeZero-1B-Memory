"""Local vault management; never supply secrets as command-line arguments."""
import argparse
import getpass
import json
from pathlib import Path

from .storage import SecureMemory

DEFAULT_DB = str(Path.home() / ".local" / "share" / "hingezero_secure_memory" / "vault.db")


def main():
    parser = argparse.ArgumentParser(prog="hzm", description="HingeZero Secure Memory")
    parser.add_argument("--db", default=DEFAULT_DB, help="private local vault path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    grant = commands.add_parser("grant")
    grant.add_argument("--label", required=True)
    grant.add_argument("--scope", default="general")
    grant.add_argument("--right", choices=["read", "write", "readwrite"], default="read")
    grant.add_argument("--days", type=int, default=30)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("capability_id")
    add = commands.add_parser("add")
    add.add_argument("--scope", default="general")
    add.add_argument("--source", required=True)
    add.add_argument("--consent", action="store_true", required=True)
    add.add_argument("--days", type=int, default=30)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--scope", default="general")
    commands.add_parser("list")
    delete = commands.add_parser("delete")
    delete.add_argument("record_id")
    args = parser.parse_args()
    secret = getpass.getpass("Vault passphrase: ")
    with SecureMemory(args.db, secret) as vault:
        if args.command == "init":
            print("Vault initialised.")
        elif args.command == "grant":
            cap_id, token = vault.grant(args.label, args.scope, args.right, args.days)
            print(f"Capability ID (for revocation): {cap_id}")
            print(f"Store this token securely; shown once: {token}")
        elif args.command == "revoke":
            print("Revoked." if vault.revoke(args.capability_id) else "Capability not found.")
        elif args.command == "add":
            print("Enter the approved memory, then end input with EOF (Ctrl-D on Unix).")
            import sys
            body = sys.stdin.read(4097)
            print("Stored:", vault.remember(body, args.source, scope=args.scope, consent=args.consent, days=args.days))
        elif args.command == "search":
            print(json.dumps(vault.recall(args.query, scope=args.scope).as_dict(), ensure_ascii=False))
        elif args.command == "list":
            print(json.dumps(vault.list_metadata(), indent=2))
        elif args.command == "delete":
            print("Deleted." if vault.delete(args.record_id) else "Record not found.")


if __name__ == "__main__":
    main()
