#!/usr/bin/env python3
"""Secure PAT storage — encrypt with password, decrypt on session start.

- Encrypted file: ~/.config/shesh/github.pat.enc (JSON with salt + token, 600)
- Plain file: ~/.config/shesh/github.pat (600) — auto-created after password, auto-deleted on handoff
- Password: user provides each new session via ask_user (prompt) — default hint <YOUR_ENCRYPTION_PASSWORD> but not stored
- Uses PBKDF2HMAC-SHA256 200k + Fernet

Usage:
  python tools/secure_pat.py --encrypt --password "your-password"   # encrypt existing plain -> enc
  python tools/secure_pat.py --decrypt --password "your-password"   # decrypt enc -> plain
  python tools/secure_pat.py --store "ghp_xxx" --password "pw"       # store new PAT encrypted + plain
  python tools/secure_pat.py --check                                 # check files exist, perms
  python tools/secure_pat.py --handoff                               # delete plain, keep enc (for session hop)
  python tools/secure_pat.py --prompt                                # interactive password prompt → decrypt

Integrates with tools/github_auth.py — it will call decrypt if plain missing but enc exists.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import pathlib
import sys

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    print("Missing cryptography — pip install cryptography", file=sys.stderr)
    sys.exit(1)

CONFIG_DIR = pathlib.Path.home() / ".config/shesh"
ENC_FILE = CONFIG_DIR / "github.pat.enc"
PLAIN_FILE = CONFIG_DIR / "github.pat"


def _derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    return base64.urlsafe_b64encode(kdf.derive(password))


def encrypt_pat(pat: str, password: str) -> dict:
    salt = os.urandom(16)
    key = _derive_key(password.encode(), salt)
    f = Fernet(key)
    enc = f.encrypt(pat.encode()).decode()
    return {
        "salt": base64.b64encode(salt).decode(),
        "token": enc,
        "kdf": "PBKDF2HMAC-SHA256-200k",
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }


def decrypt_pat(data: dict, password: str) -> str:
    salt = base64.b64decode(data["salt"])
    key = _derive_key(password.encode(), salt)
    f = Fernet(key)
    return f.decrypt(data["token"].encode()).decode()


def store_encrypted(pat: str, password: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    data = encrypt_pat(pat, password)
    ENC_FILE.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(ENC_FILE, 0o600)
    PLAIN_FILE.write_text(pat + "\n")
    os.chmod(PLAIN_FILE, 0o600)
    print(f"Stored encrypted {ENC_FILE} and plain {PLAIN_FILE} with 600")


def ensure_decrypted(password: str | None = None) -> str | None:
    if PLAIN_FILE.exists():
        try:
            # check perms
            st = PLAIN_FILE.stat()
            if st.st_mode & 0o077:
                print(f"Fixing perms {PLAIN_FILE} -> 600", file=sys.stderr)
                os.chmod(PLAIN_FILE, 0o600)
            return PLAIN_FILE.read_text().strip()
        except (OSError, UnicodeDecodeError):
            # Plain file unreadable — try the encrypted store below.
            pass

    if not ENC_FILE.exists():
        print(f"No encrypted file {ENC_FILE}", file=sys.stderr)
        return None

    if password is None:
        # Try env
        password = os.environ.get("GITHUB_PAT_PASSWORD") or os.environ.get("PAT_PASSWORD")
        if not password:
            try:
                password = getpass.getpass("Enter password to decrypt GitHub PAT: ")
            except (EOFError, KeyboardInterrupt, OSError) as e:
                print(f"Need password to decrypt ({type(e).__name__})", file=sys.stderr)
                return None

    try:
        data = json.loads(ENC_FILE.read_text())
        pat = decrypt_pat(data, password)
        PLAIN_FILE.write_text(pat + "\n")
        os.chmod(PLAIN_FILE, 0o600)
        print(f"Decrypted {ENC_FILE} -> {PLAIN_FILE}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Decrypt failed: {e}", file=sys.stderr)
        return None
    return pat


def main() -> int:
    ap = argparse.ArgumentParser(description="Secure PAT encrypt/decrypt")
    ap.add_argument("--encrypt", action="store_true", help="encrypt existing plain file")
    ap.add_argument("--decrypt", action="store_true", help="decrypt enc to plain")
    ap.add_argument("--store", help="store new PAT (value)")
    ap.add_argument("--password", help="password for encrypt/decrypt (else prompt)")
    ap.add_argument("--check", action="store_true", help="check files")
    ap.add_argument("--handoff", action="store_true", help="delete plain, keep enc (for hop)")
    ap.add_argument("--prompt", action="store_true", help="prompt password and decrypt")
    args = ap.parse_args()

    # Password handling — if not provided, prompt
    pwd = args.password
    if (args.encrypt or args.decrypt or args.store or args.prompt) and not pwd:
        pwd = os.environ.get("GITHUB_PAT_PASSWORD")
        if not pwd:
            try:
                pwd = getpass.getpass("Password: ")
            except (EOFError, KeyboardInterrupt, OSError):
                pwd = ""

    if args.store:
        if not pwd:
            print("Need --password to store", file=sys.stderr)
            return 1
        store_encrypted(args.store, pwd)
        return 0

    if args.encrypt:
        if not PLAIN_FILE.exists():
            print(f"No plain file {PLAIN_FILE}", file=sys.stderr)
            return 1
        pat = PLAIN_FILE.read_text().strip()
        store_encrypted(pat, pwd)
        return 0

    if args.decrypt or args.prompt:
        pat = ensure_decrypted(pwd)
        if pat:
            print(f"PAT ready len {len(pat)}")
            return 0
        return 1

    if args.check:
        print(f"ENC exists: {ENC_FILE.exists()} -> {ENC_FILE}")
        print(f"PLAIN exists: {PLAIN_FILE.exists()} -> {PLAIN_FILE}")
        if ENC_FILE.exists():

            st = ENC_FILE.stat()
            print(f"ENC perms: {oct(st.st_mode & 0o777)}")
        if PLAIN_FILE.exists():

            st = PLAIN_FILE.stat()
            print(f"PLAIN perms: {oct(st.st_mode & 0o777)}")
            # Don't print token
        return 0

    if args.handoff:
        if PLAIN_FILE.exists():
            PLAIN_FILE.unlink()
            print(f"Deleted plain {PLAIN_FILE}, kept enc {ENC_FILE} — next session will need password")
        else:
            print(f"No plain file to delete, enc exists: {ENC_FILE.exists()}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
