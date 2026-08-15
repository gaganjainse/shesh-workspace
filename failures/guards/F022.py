#!/usr/bin/env python3
"""F022: a credential file is read despite permissive modes.

Enforce the permission rule on read, not only on write; refuse rather than warn.

Writing 0600 is not enough: a mode widened later by a copy, a restore, a
container mount, or an editor writing a new inode goes unnoticed if the read
path does not look. This guard checks both the live store's mode and that the
code reading it enforces the rule.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

STORES = (
    "~/.config/shesh/tokens.enc.json",
    "~/.config/shesh/github.pat",
    "~/.config/shesh/github.pat.enc",
    "~/.netrc",
)
# Readers that must carry a mode check.
READERS = ("tools/tokens.py", "tools/github_auth.py", "tools/secure_pat.py")
MODE_CHECK = re.compile(r"st_mode\s*&\s*0o0?77|_check_perms|S_IRGRP|S_IROTH")


def check(fleet: Path) -> list[str]:
    findings = []
    for s in STORES:
        p = Path(os.path.expanduser(s))
        if not p.exists():
            continue
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            findings.append(
                f"{p}: mode {mode:04o} lets group or other read a credential; "
                f"run chmod 600 {p}")
    for repo in sorted(x for x in fleet.iterdir() if (x / ".git").is_dir()):
        for rel in READERS:
            f = repo / rel
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if "STORE" not in text and "pat" not in text.lower():
                continue
            if not MODE_CHECK.search(text):
                findings.append(
                    f"{repo.name}/{rel}: reads a credential file without "
                    f"checking its mode; a widened permission would go "
                    f"unnoticed")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for x in found:
        print(f"  {x}")
    sys.exit(1 if found else 0)
