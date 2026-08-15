#!/usr/bin/env python3
"""F012: "green on main" is not "the PR is green".

Judge a pull request by the checks on its head SHA.

This guard does not inspect GitHub: it enforces that the tooling used to make
that judgement reads the head SHA rather than a branch. A wrong tool produces
a wrong answer every time it is used.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# fleet_health reports default-branch state. Anything that claims to report
# pull-request readiness must key on the head commit.
PR_TOOL = re.compile(r"pulls?/|pull_request", re.I)
HEAD_SHA = re.compile(r"head'?\]?\[?'?sha|head_sha|head\.sha")


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        for d in ("tools", "scripts"):
            base = repo / d
            if not base.is_dir():
                continue
            for py in sorted(base.glob("*.py")):
                src = py.read_text(encoding="utf-8", errors="ignore")
                if "check-runs" not in src and "check_runs" not in src:
                    continue
                if not PR_TOOL.search(src):
                    continue
                if not HEAD_SHA.search(src):
                    findings.append(
                        f"{py.relative_to(fleet)}: reads check-runs for a pull "
                        f"request without keying on its head SHA")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
