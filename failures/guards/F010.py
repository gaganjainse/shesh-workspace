#!/usr/bin/env python3
"""F010: a stale pin fails before any job starts.

Every repository references the same revision of a shared workflow.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REUSABLE = re.compile(r"uses:\s*([\w-]+/[\w-]+/\.github/workflows/[\w.-]+)@([0-9a-f]{40})")


def check(fleet: Path) -> list[str]:
    seen: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        wf = repo / ".github" / "workflows"
        if not wf.is_dir():
            continue
        for f in sorted(wf.glob("*.yml")):
            for path, sha in REUSABLE.findall(
                    f.read_text(encoding="utf-8", errors="ignore")):
                seen[path][sha].append(repo.name)

    findings = []
    for path, pins in seen.items():
        if len(pins) > 1:
            majority = max(pins, key=lambda s: len(pins[s]))
            for sha, repos in pins.items():
                if sha == majority:
                    continue
                findings.append(
                    f"{', '.join(repos)}: pins {path} at {sha[:8]} while "
                    f"{len(pins[majority])} repositories use {majority[:8]}")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
