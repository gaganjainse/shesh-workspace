#!/usr/bin/env python3
"""F004: `|| true` hides the failure you needed to see.

Handle the specific expected failure; never blanket-suppress.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MASK = re.compile(r"\|\|\s*(?:true|:)\s*(?:#|$)")
# git writes these itself in hook scaffolding; they are not ours to police.
EXEMPT = ("submodule foreach", "git config --local --unset")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        wf = repo / ".github" / "workflows"
        if not wf.is_dir():
            continue
        for f in sorted(wf.glob("*.yml")):
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if MASK.search(line) and not any(e in line for e in EXEMPT):
                    findings.append(
                        f"{f.relative_to(fleet)}:{i}: masks a failure with "
                        f"|| true; handle the expected case explicitly")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
