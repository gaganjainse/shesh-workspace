#!/usr/bin/env python3
"""Secure GitHub PAT loader — never logs secret value.

Order:
1. Env GITHUB_PAT > GH_TOKEN > GITHUB_TOKEN
2. File ~/.config/shesh/github.pat (must be 0600, refuses world-readable)
3. Encrypted file ~/.config/shesh/github.pat.enc + password (auto-decrypt)
4. File ~/.config/shesh/github_token (legacy)
5. gh CLI hosts.yml (~/.config/gh/hosts.yml)

Usage:
  python tools/github_auth.py --check   # verifies loading, prints redacted
  python tools/github_auth.py --token   # prints token to stdout (use with care)
  python tools/github_auth.py --need-password  # returns 0 if encrypted exists but plain missing (needs password)
"""

from __future__ import annotations

import argparse
import os
import pathlib
import stat
import subprocess
import sys


def _check_perms(p: pathlib.Path) -> bool:
    try:
        st = p.stat()
        if st.st_mode & stat.S_IRWXO:
            print(f"REFUSE world-readable {p} (chmod 600 required)", file=sys.stderr)
            return False
        if st.st_mode & stat.S_IRWXG:
            print(f"WARN group-readable {p}, should be 600", file=sys.stderr)
    except OSError:
        # stat failed (file vanished mid-check): treat the file as unusable.
        return False
    return True


def _try_decrypt_encrypted(password: str | None = None) -> str | None:
    """Try to decrypt .enc file if plain missing."""
    enc_file = pathlib.Path.home() / ".config/shesh/github.pat.enc"
    plain_file = pathlib.Path.home() / ".config/shesh/github.pat"
    if not enc_file.exists():
        return None
    if plain_file.exists():
        # plain exists, let normal loader handle
        return None
    try:
        # Import secure_pat logic inline to avoid circular
        import json
        import base64

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        if password is None:
            password = os.environ.get("GITHUB_PAT_PASSWORD") or os.environ.get("PAT_PASSWORD")

        if password is None:
            # No password provided — cannot decrypt non-interactively
            return None

        data = json.loads(enc_file.read_text())
        salt = base64.b64decode(data["salt"])
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        pat = f.decrypt(data["token"].encode()).decode()
        # Write plain with 600
        plain_file.parent.mkdir(parents=True, exist_ok=True)
        plain_file.write_text(pat + "\n")
        os.chmod(plain_file, 0o600)
        print(f"Decrypted {enc_file} -> {plain_file}", file=sys.stderr)
    except (OSError, ValueError, KeyError) as e:
        # Wrong password / corrupt blob / unreadable file all land here and
        # are reported on stderr — never silently retried or ignored.
        print(f"Decrypt failed: {e}", file=sys.stderr)
        return None
    return pat


def load_pat(password: str | None = None) -> str | None:
    # 1. env
    for key in ("GITHUB_PAT", "GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(key)
        if v and v.strip():
            return v.strip()

    # 2. file ~/.config/shesh/github.pat
    cfg_dir = pathlib.Path.home() / ".config/shesh"
    for fname in ("github.pat", "github_token", "pat"):
        p = cfg_dir / fname
        if p.exists():
            if not _check_perms(p):
                continue
            try:
                token = p.read_text().strip()
                if token:
                    return token
            except (OSError, UnicodeDecodeError):
                # This candidate file is unusable — try the next known path.
                continue

    # 2b. try encrypted with provided password
    pat = _try_decrypt_encrypted(password)
    if pat:
        return pat

    # 3. gh cli hosts.yml
    gh_hosts = pathlib.Path.home() / ".config/gh/hosts.yml"
    if gh_hosts.exists():
        try:
            txt = gh_hosts.read_text()
            for line in txt.splitlines():
                line = line.strip()
                if "oauth_token:" in line:
                    token = line.split("oauth_token:")[-1].strip().strip('"').strip("'")
                    if token:
                        return token
        except (OSError, IndexError, UnicodeDecodeError):
            # Probe chain: this source is unusable -> try the next one.
            pass

    return None


def needs_password() -> bool:
    """True if enc exists but plain missing — need password to decrypt."""
    enc = pathlib.Path.home() / ".config/shesh/github.pat.enc"
    plain = pathlib.Path.home() / ".config/shesh/github.pat"
    return enc.exists() and not plain.exists()


def git_environment(pat: str | None = None) -> dict[str, str]:
    """Return a child environment that can authenticate GitHub HTTPS pushes.

    Git's HTTPS transport does not read ``GITHUB_PAT`` by itself.  The
    askpass helper reads the token from the process environment or the
    0600 PAT file only when Git asks for credentials; the token is never
    embedded in a remote URL, config file, command line, or log message.
    """
    token = pat or load_pat()
    if not token:
        return dict(os.environ)

    env = dict(os.environ)
    env["GITHUB_PAT"] = token
    env.setdefault("GH_TOKEN", token)
    env["GIT_ASKPASS"] = str(pathlib.Path(__file__).with_name("git_askpass.py"))
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_USERNAME", "x-access-token")
    return env


def git_repo_root(start: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find the Git worktree containing *start*, if any."""
    cwd = start or pathlib.Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        value = result.stdout.strip()
        if value:
            return pathlib.Path(value)
    # Fallback: pure-path detection (works even when git refuses the
    # checkout as "dubious ownership", e.g. root containers on CI).
    # A real repo root has a `.git` entry that is a directory (clone) or
    # a file (worktree/submodule).
    for candidate in [cwd, *cwd.parents]:
        dot_git = candidate / ".git"
        if dot_git.is_dir() or dot_git.is_file():
            return candidate
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub PAT loader")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--token", action="store_true")
    ap.add_argument("--need-password", action="store_true", help="exit 0 if password needed")
    ap.add_argument("--password", help="password to decrypt enc file")
    args = ap.parse_args()

    if args.need_password:
        if needs_password():
            print("NEED_PASSWORD: encrypted exists but plain missing — ask user for password")
            return 0
        else:
            print("No password needed")
            return 1

    pat = load_pat(password=args.password)
    if not pat:
        if needs_password():
            print("No PAT found but encrypted exists — need password to decrypt", file=sys.stderr)
            print("Run: python tools/secure_pat.py --prompt", file=sys.stderr)
        else:
            print("No PAT found. Set GITHUB_PAT env or create ~/.config/shesh/github.pat with chmod 600", file=sys.stderr)
            print("Or run: gh auth login or python tools/secure_pat.py --store <pat> --password <pw>", file=sys.stderr)
        return 1

    if args.token:
        print(pat)
        return 0

    # default check
    redacted = pat[:4] + "*" * (len(pat) - 8) + pat[-4:] if len(pat) > 8 else "****"
    print(f"PAT found: {redacted} (len {len(pat)})")
    print(f"Source: env or {pathlib.Path.home() / '.config/shesh/github.pat'} or enc or gh hosts.yml")
    try:
        repo = git_repo_root()
        if repo:
            remote = subprocess.check_output(
                ["git", "-C", str(repo), "remote", "get-url", "origin"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            print(f"git remote origin: {remote}")
    except (OSError, subprocess.SubprocessError) as e:
        # Diagnostic print only — the auth outcome was already decided above.
        print(f"(git remote probe failed: {e})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--check")
    sys.exit(main())

