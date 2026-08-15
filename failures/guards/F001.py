#!/usr/bin/env python3
"""F001: a tool that fails silently looks maintained.

A tool exits non-zero when its target is missing. Never return on a missing path.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# A bare `return` immediately after testing that a path is absent, inside a
# function that does not declare None as a legitimate result. A function typed
# `-> X | None` is reporting absence, which is different from swallowing it.
SILENT = re.compile(
    r"if\s+not\s+[\w.]*(?:\.exists\(\)|os\.path\.exists\([^)]*\))\s*:\s*\n"
    r"\s+return\s*(?:None)?\s*\n")
SIGNATURE = re.compile(r"^\s*def\s+(\w+)\s*\(", re.M)
# `-> X | None` and `-> Optional[X]` mean absence is a declared result.
# A bare `-> None` is a procedure: returning early there hides the failure.
OPTIONAL_RETURN = re.compile(r"->\s*(?:[^:\n]*\|\s*None|Optional\[)")

TOOL_DIRS = ("tools", "scripts")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for d in TOOL_DIRS:
            for py in sorted((repo / d).rglob("*.py")) if (repo / d).is_dir() else []:
                # Vendored and inherited trees are out of scope.
                if any(x in py.parts for x in ("swarm", "autopilot", "steal")):
                    continue
                try:
                    src = py.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for m in SILENT.finditer(src):
                    line = src[:m.start()].count("\n") + 1
                    # Find the enclosing def and read its return annotation.
                    defs = [d for d in SIGNATURE.finditer(src) if d.start() < m.start()]
                    if defs:
                        head = src[defs[-1].start():src.find(":\n", defs[-1].start()) + 1]
                        if OPTIONAL_RETURN.search(head):
                            continue      # None is a declared, meaningful result
                    findings.append(
                        f"{py.relative_to(fleet)}:{line}: returns silently when "
                        f"a path is missing; exit non-zero instead")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
