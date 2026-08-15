#!/usr/bin/env python3
"""F005: `allowed-tools` grants, it does not restrict.

A safety skill carries no grant at all.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# A skill that is always active and governs destructive action. A grant here
# pre-approves those tools in every session.
SAFETY = ("safety", "governance", "guard", "policy")


def check(fleet: Path) -> list[str]:
    findings = []
    for skills in fleet.glob("*/skills"):
        for d in sorted(p for p in skills.iterdir() if p.is_dir()):
            f = d / "SKILL.md"
            if not f.exists():
                continue
            if not any(s in d.name for s in SAFETY):
                continue
            m = re.match(r"\A---\n(.*?)\n---\n", f.read_text(encoding="utf-8"), re.S)
            if not m:
                continue
            if re.search(r"^allowed-tools:", m.group(1), re.M):
                findings.append(
                    f"{f.relative_to(fleet)}: a safety skill carries an "
                    f"allowed-tools grant, which widens every session")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
