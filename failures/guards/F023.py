#!/usr/bin/env python3
"""F023: the fleet targets a platform the reference machine does not run.

Record the target platform as a fact checked against the machine, not an
assumption. A probe that skips because the platform differs is a finding.

Documentation names a distribution and a compositor. Hardware evidence records
what the machine actually runs. When the two disagree, every claim resting on
the assumed platform is unverifiable, and the skips in the evidence file look
like missing coverage rather than a missing platform.

This guard compares the two and fails when documentation asserts a platform the
evidence contradicts.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EVIDENCE = ("evidence/hardware-verification.json", "hardware-verification.json")
# Platform tokens the documentation asserts, and how they show up in evidence.
COMPOSITORS = {"hyprland": "hypr", "gnome": "gnome", "kde": "kde", "sway": "sway"}


def _evidence(fleet: Path) -> dict | None:
    for repo in sorted(fleet.iterdir()):
        for name in EVIDENCE:
            cand = repo / name
            if cand.is_file():
                try:
                    return json.loads(cand.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
    return None


def check(fleet: Path) -> list[str]:
    ev = _evidence(fleet)
    if ev is None:
        return []  # nothing to compare against; F021 covers the missing run

    session = ""
    for r in ev.get("results", []):
        if r.get("id") == "env-001" and r.get("status") == "pass":
            session = (r.get("detail") or "").lower()
    if not session:
        return []

    actual = {name for name, token in COMPOSITORS.items() if token in session}
    if not actual:
        return []

    findings: list[str] = []
    # A page that names a compositor the machine does not run, and claims a
    # hardware date, is asserting something the evidence cannot support.
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        if repo.name.endswith("-docs-archive"):
            continue
        for doc in sorted(repo.rglob("*.md")):
            parts = set(doc.relative_to(fleet).parts)
            if parts & {"archive", "history", "attic", ".git", "plans"}:
                continue
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            hw = re.search(r"^hardware_verified:\s*(\S+)", text, re.M)
            if not hw or hw.group(1).strip().lower() in ("no", "false", "none"):
                continue
            low = text.lower()
            claimed = {n for n in COMPOSITORS if n in low}
            wrong = claimed - actual
            if wrong:
                findings.append(
                    f"{doc.relative_to(fleet)}: claims hardware_verified "
                    f"{hw.group(1)} while naming {sorted(wrong)}, but the "
                    f"evidence records a {sorted(actual)} session. The claim "
                    f"cannot rest on that run.")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found[:20]:
        print(f"  {f}")
    sys.exit(1 if found else 0)
