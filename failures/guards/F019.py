#!/usr/bin/env python3
"""F019: a shell redirect leaks into a filename.

A package directory has an __init__.py whose name is exactly that.

A file called `__init__.py">` leaves the package with no __init__.py at all.
Tests that insert src/ on sys.path still pass, because a directory without
__init__.py is importable as a namespace package, so the break only appears
once the distribution is installed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Characters that a shell produces and a source filename never legitimately has.
SUSPECT = re.compile(r'["\'<>|&;$`\\]|\s$')


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for f in sorted(repo.rglob("*")):
            if ".git" in f.parts or not f.is_file():
                continue
            if SUSPECT.search(f.name):
                findings.append(
                    f"{f.relative_to(fleet)}: filename contains a shell "
                    f"metacharacter; a redirect or quote leaked into it")
        # A src-layout package directory must carry a real __init__.py.
        src = repo / "src"
        if not src.is_dir():
            continue
        for pkg in sorted(p for p in src.iterdir() if p.is_dir()):
            if pkg.name.startswith((".", "__")):
                continue
            has_py = any(pkg.glob("*.py"))
            if has_py and not (pkg / "__init__.py").is_file():
                findings.append(
                    f"{pkg.relative_to(fleet)}: holds modules but has no "
                    f"__init__.py; it installs as a namespace package and "
                    f"tests using a sys.path hack will not notice")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
