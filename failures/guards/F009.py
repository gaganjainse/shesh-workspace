#!/usr/bin/env python3
"""F009: a standardiser can standardise a repository into breaking.

A setting belongs only where the thing it configures exists.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        pyproject = repo / "pyproject.toml"
        if not pyproject.exists():
            continue
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "asyncio_mode" not in text:
            continue
        # The key is only valid when pytest-asyncio is installed, which CI
        # does not do unless the component actually has async tests.
        has_async = False
        for d in ("tests", "src"):
            p = repo / d
            if not p.is_dir():
                continue
            for py in p.rglob("*.py"):
                body = py.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"^\s*async def |@pytest\.mark\.asyncio", body, re.M):
                    has_async = True
                    break
            if has_async:
                break
        if not has_async:
            findings.append(
                f"{repo.name}/pyproject.toml: declares asyncio_mode but has no "
                f"async tests; pytest aborts on an unknown key")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
