#!/usr/bin/env python3
"""F007: a policy nobody scheduled is not a policy.

If it is not on a schedule or in a gate, it will not happen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Tools that exist to run periodically. Each must be reachable from a
# scheduled workflow or a Makefile target, or it will never run.
PERIODIC = ("assimilate.py", "upstream_tracker.py", "fleet_health.py")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        wf = repo / ".github" / "workflows"
        tools = repo / "tools"
        if not tools.is_dir():
            continue
        scheduled = ""
        if wf.is_dir():
            for f in wf.glob("*.yml"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"^\s*schedule:", text, re.M):
                    scheduled += text
        makefile = ""
        if (repo / "Makefile").exists():
            makefile = (repo / "Makefile").read_text(encoding="utf-8", errors="ignore")

        for name in PERIODIC:
            if not (tools / name).exists():
                continue
            if name in scheduled or name in makefile:
                continue
            findings.append(
                f"{repo.name}/tools/{name}: exists but no schedule or Makefile "
                f"target invokes it")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
