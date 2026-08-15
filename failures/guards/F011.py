#!/usr/bin/env python3
"""F011: an unarchived repository runs CI again.

A superseded repository keeps history and README, not source.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SUPERSEDED = re.compile(r"superseded by|consolidated into", re.I)


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        readme = repo / "README.md"
        if not readme.exists():
            continue
        head = readme.read_text(encoding="utf-8", errors="ignore")[:600]
        if not SUPERSEDED.search(head):
            continue
        for d in ("src", "tests"):
            if (repo / d).is_dir():
                findings.append(
                    f"{repo.name}: declares itself superseded but still holds "
                    f"{d}/; two copies of a module drift")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
