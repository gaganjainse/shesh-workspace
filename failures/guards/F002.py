#!/usr/bin/env python3
"""F002: moving a file breaks the gate that calls it.

Before moving a file, grep every workflow and Makefile for its name.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REF = re.compile(r"(?:python3?\s+|bash\s+|\./)((?:tools|scripts)/[\w./-]+\.(?:py|sh))")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        sources = list((repo / ".github" / "workflows").glob("*.yml"))
        mk = repo / "Makefile"
        if mk.exists():
            sources.append(mk)
        for src in sources:
            try:
                text = src.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for rel in set(REF.findall(text)):
                # A path may legitimately point at a sibling repository.
                if (repo / rel).exists():
                    continue
                if any((fleet / other.name / rel).exists()
                       for other in fleet.iterdir() if (other / ".git").is_dir()):
                    continue
                findings.append(
                    f"{src.relative_to(fleet)}: calls {rel}, which does not exist")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
