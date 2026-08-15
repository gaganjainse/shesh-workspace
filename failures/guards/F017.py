#!/usr/bin/env python3
"""F017: a git hook that is not executable is silently ignored.

Install a hook with mode 0o755 and verify it fires.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HOOKS = ("commit-msg", "pre-push", "pre-commit")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for name in HOOKS:
            h = repo / ".git" / "hooks" / name
            if not h.is_file():
                continue
            if not os.access(h, os.X_OK):
                findings.append(
                    f"{repo.name}: .git/hooks/{name} is installed but not "
                    f"executable, so git ignores it and enforcement is off")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
