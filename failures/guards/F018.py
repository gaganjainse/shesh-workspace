#!/usr/bin/env python3
"""F018: a local module shadows a standard-library module.

Before naming a module, check the name against sys.stdlib_module_names.

A file named token.py, types.py, or select.py on sys.path is imported in
preference to the standard library's. The break surfaces far from the cause:
an unrelated import fails with a message naming your own file.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Directories that end up on sys.path: script directories and source roots.
ON_PATH = ("tools", "scripts", "src", "bin")
# A package directory makes its contents `pkg.name`, not top-level `name`,
# so only modules directly inside an unpackaged path directory can shadow.
STDLIB = set(sys.stdlib_module_names)


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for d in ON_PATH:
            base = repo / d
            if not base.is_dir():
                continue
            for f in sorted(base.rglob("*.py")):
                # inside a package? then it is namespaced and cannot shadow
                if (f.parent / "__init__.py").exists():
                    continue
                if f.stem in STDLIB and f.stem != "__init__":
                    findings.append(
                        f"{f.relative_to(fleet)}: shadows the standard-library "
                        f"module {f.stem!r}; anything importing it from this "
                        f"sys.path gets your file instead")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
