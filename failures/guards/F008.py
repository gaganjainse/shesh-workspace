#!/usr/bin/env python3
"""F008: a credential in a chat is burned.

Use token.py. Never ask for a paste, and never commit a credential.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SECRETS = [
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "GitHub personal access token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}"), "GitHub fine-grained token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
]


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        # A credential embedded in the remote URL leaks on every push.
        try:
            url = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                                 capture_output=True, text=True, timeout=15).stdout
        except (subprocess.SubprocessError, OSError):
            url = ""
        for pattern, what in SECRETS:
            if pattern.search(url):
                findings.append(f"{repo.name}: {what} embedded in the git remote")

        try:
            tracked = subprocess.run(["git", "-C", str(repo), "ls-files"],
                                     capture_output=True, text=True,
                                     timeout=30).stdout.splitlines()
        except (subprocess.SubprocessError, OSError):
            continue
        for rel in tracked:
            if not rel.endswith((".md", ".py", ".sh", ".yml", ".yaml", ".toml",
                                 ".json", ".txt", ".env")):
                continue
            p = repo / rel
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern, what in SECRETS:
                if pattern.search(text):
                    findings.append(f"{repo.name}/{rel}: {what} committed")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
