#!/usr/bin/env python3
"""F003: a generator whose input depends on its own output.

A generated artefact is a function of committed sources only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The failure is a generator whose inputs come from OUTSIDE its own repository:
# sibling checkouts vary by machine, so the output does. Scanning a committed
# directory within the same repository is deterministic and fine.
SCAN = re.compile(r"\bSRC\b[^\n]*\.glob\(|src_root[^\n]*\.glob\(")
GENERATOR_HINT = re.compile(r"--check|freshness|regenerat", re.I)


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        d = repo / "tools"
        if not d.is_dir():
            continue
        for py in sorted(d.glob("*.py")):
            try:
                src = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not GENERATOR_HINT.search(src):
                continue
            if not SCAN.search(src):
                continue
            # A scan constrained by a manifest is fine; an unconstrained one
            # is the failure. Look for evidence the set is bounded.
            if re.search(r"manifest|wanted|list_repos\(\)|ALL_REPOS", src):
                continue
            findings.append(
                f"{py.relative_to(fleet)}: a freshness gate scans the working "
                f"tree for its inputs; bound the set from a manifest")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
