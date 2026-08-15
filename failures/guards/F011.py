#!/usr/bin/env python3
"""F011: an unarchived repository runs CI again.

A superseded repository keeps history and README, not source.

There is a third state that is neither live nor a tombstone: a repository whose
successor exists but whose code has not finished moving. shesh-kernel is the
case ADR-0008 records, where force-merging two diverged Rust trees would have
shipped a broken build, so the archive deliberately keeps the crates that have
no counterpart yet.

That state is allowed, but only when it is declared and bounded: the README
must name the superseding repository, say the merge is staged rather than done,
cite the ADR, and list what is still only here. Without that a reader cannot
tell a planned archive from a repository somebody forgot to empty, which is the
drift this rule exists to prevent.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SUPERSEDED = re.compile(r"superseded by|consolidated into", re.I)
# Evidence that the retained source is a recorded decision, not an oversight.
STAGED = re.compile(r"\bADR-\d{4}\b")
SCOPED = re.compile(r"only here|not been rebased|no counterpart|merge plan|"
                    r"staged rebase", re.I)


def check(fleet: Path) -> list[str]:
    findings = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        readme = repo / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8", errors="ignore")
        head = text[:600]
        if not SUPERSEDED.search(head):
            continue
        held = [d for d in ("src", "tests") if (repo / d).is_dir()]
        if not held:
            continue
        if STAGED.search(text) and SCOPED.search(text):
            continue  # declared staged archive; the retention is on the record
        for d in held:
            findings.append(
                f"{repo.name}: declares itself superseded but still holds "
                f"{d}/; two copies of a module drift. If the code is staying "
                f"until a staged merge, say so in the README: cite the ADR and "
                f"list what is only here.")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
