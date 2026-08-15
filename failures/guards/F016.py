#!/usr/bin/env python3
"""F016: a moved script loses its executable bit.

A file with a shebang carries the executable bit.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SEARCH = ("tools", "scripts", "failures/guards")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for d in SEARCH:
            base = repo / d
            if not base.is_dir():
                continue
            for f in sorted(base.rglob("*")):
                if not f.is_file() or f.suffix not in (".py", ".sh"):
                    continue
                try:
                    first = f.open("rb").readline(120)
                except OSError:
                    continue
                if not first.startswith(b"#!"):
                    continue
                if not os.access(f, os.X_OK):
                    findings.append(
                        f"{f.relative_to(fleet)}: has a shebang but is not "
                        f"executable; spawning it raises PermissionError")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
