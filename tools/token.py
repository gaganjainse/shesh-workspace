#!/usr/bin/env python3
"""Encrypted credential store, so a token is entered once and never again.

Tokens live encrypted at ~/.config/shesh/tokens.enc.json (PBKDF2-SHA256,
200k iterations, Fernet). The password is supplied per session through
SHESH_PAT_PASSWORD or an interactive prompt; it is never written to disk.

An agent must call this rather than asking the operator to paste a token into
a conversation. A token pasted into a chat is exposed permanently in the
transcript, which is how the previous two were burned.

Usage:
    token.py store <name>              # prompts for the token, then encrypts
    token.py get <name>                # print to stdout (for command substitution)
    token.py list                      # names only, never values
    token.py env                       # export lines for eval
    token.py remote <repo>             # authenticated push URL for one repo
    token.py check                     # verify the store decrypts and is valid
"""
from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG = Path(os.path.expanduser("~/.config/shesh"))
STORE = CONFIG / "tokens.enc.json"
OWNER = "gaganjainse"

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:  # noqa: BLE001 - reported, not swallowed
    print("error: python-cryptography is required (pip install cryptography)",
          file=sys.stderr)
    raise SystemExit(2) from None


def _key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=200_000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def password() -> str:
    """Resolve the store password. Never persisted."""
    pw = os.environ.get("SHESH_PAT_PASSWORD")
    if pw:
        return pw
    if not sys.stdin.isatty():
        print("error: set SHESH_PAT_PASSWORD or run interactively",
              file=sys.stderr)
        raise SystemExit(2)
    return getpass.getpass("Shesh token store password: ")


def load() -> dict:
    if not STORE.exists():
        return {}
    return json.loads(STORE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    CONFIG.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(STORE, 0o600)


def encrypt(value: str, pw: str) -> dict:
    salt = os.urandom(16)
    return {
        "salt": base64.b64encode(salt).decode(),
        "token": Fernet(_key(pw, salt)).encrypt(value.encode()).decode(),
        "kdf": "PBKDF2HMAC-SHA256-200k",
    }


def decrypt(entry: dict, pw: str) -> str:
    salt = base64.b64decode(entry["salt"])
    return Fernet(_key(pw, salt)).decrypt(entry["token"].encode()).decode()


def cmd_store(name: str) -> int:
    token = os.environ.get("SHESH_TOKEN_VALUE")
    if not token:
        if not sys.stdin.isatty():
            print("error: set SHESH_TOKEN_VALUE or run interactively",
                  file=sys.stderr)
            return 2
        token = getpass.getpass(f"Token value for {name!r}: ")
    if not token.strip():
        print("error: empty token", file=sys.stderr)
        return 2

    pw = password()
    data = load()
    data[name] = encrypt(token.strip(), pw)
    # Prove it decrypts before claiming success.
    if decrypt(data[name], pw) != token.strip():
        print("error: roundtrip failed; nothing written", file=sys.stderr)
        return 1
    save(data)
    print(f"stored {name!r} ({len(data)} token(s) in the store)")
    return 0


def cmd_get(name: str) -> int:
    data = load()
    if name not in data:
        print(f"error: no token named {name!r}; have: "
              f"{', '.join(sorted(data)) or 'none'}", file=sys.stderr)
        return 1
    try:
        sys.stdout.write(decrypt(data[name], password()))
    except InvalidToken:
        print("error: wrong password", file=sys.stderr)
        return 1
    return 0


def cmd_list() -> int:
    data = load()
    if not data:
        print("store is empty; add one with: token.py store <name>")
        return 0
    print(f"{len(data)} token(s) in {STORE}:")
    for n in sorted(data):
        print(f"  {n}")
    return 0


def cmd_env() -> int:
    """Emit export lines. Intended for `eval "$(token.py env)"`."""
    pw = password()
    for name, entry in sorted(load().items()):
        try:
            value = decrypt(entry, pw)
        except InvalidToken:
            print("error: wrong password", file=sys.stderr)
            return 1
        print(f"export SHESH_TOKEN_{name.upper()}={value!r}")
    return 0


def first_working(pw: str) -> tuple[str, str] | None:
    """Return the first token that authenticates, so a stale one is skipped."""
    for name, entry in sorted(load().items()):
        try:
            value = decrypt(entry, pw)
        except InvalidToken:
            return None
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "-H", f"Authorization: Bearer {value}",
                 "https://api.github.com/user"],
                capture_output=True, text=True, timeout=20)
            if r.stdout.strip() == "200":
                return name, value
        except (subprocess.SubprocessError, OSError):
            continue
    return None


def cmd_remote(repo: str) -> int:
    found = first_working(password())
    if not found:
        print("error: no stored token authenticates; rotate and re-store",
              file=sys.stderr)
        return 1
    _name, value = found
    sys.stdout.write(f"https://x-access-token:{value}@github.com/{OWNER}/{repo}.git")
    return 0


def cmd_check() -> int:
    data = load()
    if not data:
        print("error: store is empty", file=sys.stderr)
        return 1
    pw = password()
    ok = 0
    for name, entry in sorted(data.items()):
        try:
            value = decrypt(entry, pw)
        except InvalidToken:
            print(f"  {name}: WRONG PASSWORD")
            return 1
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-H", f"Authorization: Bearer {value}",
             "https://api.github.com/user"],
            capture_output=True, text=True, timeout=20)
        live = r.stdout.strip() == "200"
        print(f"  {name}: decrypts, {'authenticates' if live else 'REVOKED or expired'}")
        ok += live
    if not ok:
        print("no stored token authenticates", file=sys.stderr)
        return 1
    print(f"{ok} of {len(data)} token(s) usable")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("store").add_argument("name")
    sub.add_parser("get").add_argument("name")
    sub.add_parser("list")
    sub.add_parser("env")
    sub.add_parser("remote").add_argument("repo")
    sub.add_parser("check")

    a = ap.parse_args()
    return {
        "store": lambda: cmd_store(a.name),
        "get": lambda: cmd_get(a.name),
        "list": cmd_list,
        "env": cmd_env,
        "remote": lambda: cmd_remote(a.repo),
        "check": cmd_check,
    }[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
