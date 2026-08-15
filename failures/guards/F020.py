#!/usr/bin/env python3
"""F020: two repositories publish the same package name.

One package name and one console script have exactly one publisher.

pip does not warn when two distributions install a package or a script of the
same name: whichever is installed last wins. The copies then drift and the
behaviour depends on install order rather than on anything recorded.
"""
from __future__ import annotations

import sys
import tomllib
from collections import defaultdict
from pathlib import Path


def check(fleet: Path) -> list[str]:
    scripts: dict[str, list[str]] = defaultdict(list)
    packages: dict[str, list[str]] = defaultdict(list)
    dists: dict[str, list[str]] = defaultdict(list)

    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for py in sorted(repo.rglob("pyproject.toml")):
            if ".git" in py.parts:
                continue
            try:
                data = tomllib.loads(py.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                continue
            proj = data.get("project", {})
            where = str(py.parent.relative_to(fleet))
            if proj.get("name"):
                dists[proj["name"]].append(where)
            for s in proj.get("scripts", {}):
                scripts[s].append(where)
            src = py.parent / "src"
            if src.is_dir():
                for pkg in src.iterdir():
                    if pkg.is_dir() and (pkg / "__init__.py").exists():
                        packages[pkg.name].append(where)

    findings = []
    for label, table in (("console script", scripts),
                         ("python package", packages),
                         ("distribution name", dists)):
        for name, owners in sorted(table.items()):
            if len(set(owners)) > 1:
                findings.append(
                    f"{label} {name!r} is published by "
                    f"{', '.join(sorted(set(owners)))}; install order decides "
                    f"which one wins and pip does not warn")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
