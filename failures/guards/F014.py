#!/usr/bin/env python3
"""F014: a shallow clone has no merge base.

Deepen the fetch before comparing branches; match on CONFLICT.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Reading merge-tree's exit code conflates "conflict" with "no merge base",
# which is what a shallow clone produces.
BAD = re.compile(r"if\s+!\s+git\s+merge-tree[^\n]*\n", re.M)


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        wf = repo / ".github" / "workflows"
        if not wf.is_dir():
            continue
        for f in sorted(wf.glob("*.yml")):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for m in BAD.finditer(text):
                line = text[:m.start()].count("\n") + 1
                findings.append(
                    f"{f.relative_to(fleet)}:{line}: reads the exit code of "
                    f"git merge-tree; a shallow clone has no merge base, so "
                    f"this reports a conflict that does not exist")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
