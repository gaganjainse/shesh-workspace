#!/usr/bin/env python3
"""F015: rewriting a pin to a tag is a supply-chain regression.

Every action pin is a 40-character SHA.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

USES = re.compile(r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w./-]+)?)@([^\s#]+)")
# Local and first-party composite actions are referenced by path, not pinned.
EXEMPT_PREFIX = ("./", "docker://")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        wf = repo / ".github" / "workflows"
        if not wf.is_dir():
            continue
        for f in sorted(wf.glob("*.yml")):
            for i, line in enumerate(
                    f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                m = USES.search(line)
                if not m:
                    continue
                action, ref = m.groups()
                if action.startswith(EXEMPT_PREFIX):
                    continue
                if not re.fullmatch(r"[0-9a-f]{40}", ref):
                    findings.append(
                        f"{repo.name}/.github/workflows/{f.name}:{i}: "
                        f"{action}@{ref} is a mutable reference, not a SHA")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
