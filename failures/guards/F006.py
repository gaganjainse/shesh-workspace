#!/usr/bin/env python3
"""F006: documenting behaviour that does not exist.

Never write "component X does Y" without reading the code.

The general form is undecidable, so this guard checks the mechanically
checkable subset, which is where the failure actually happened:

1.  A volatile count in prose. "Sixty tools", "40 skills", "63 tests" are true
    on the day they are written and wrong afterwards. The original F006 was a
    claim about what shesh-skills served; the recurrences have all been counts.
2.  A named console script that no pyproject declares.
3.  A named MCP tool that no source file defines.

Each is a claim about the code that the code can be asked about.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# "one repo" and "a single tool" are rhetorical, not counts, so the small
# numbers are excluded. A claim only goes stale once it is specific.
WORD_NUMBERS = (
    "four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    "fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|"
    "fifty|sixty|seventy|eighty|ninety|hundred"
)
COUNTABLE = (
    "skills?|tools?|tests?|chapters?|components?|repositories|repos?|adrs?|"
    "packages?|providers?|guards?|workflows?|crates?"
)
VOLATILE = re.compile(
    rf"\b(?:\d{{2,4}}|{WORD_NUMBERS})\s+(?:{COUNTABLE})\b", re.I)

# Prose that is explicitly historical is exempt: an archive records what was
# true then, and a changelog entry is a dated statement, not a live claim.
EXEMPT_REPOS = {"shesh-docs-archive"}
EXEMPT_NAMES = {"CHANGELOG.md", "TODO.md", "decision-journal.md"}
# .kilo/plans holds dated planning artefacts: a record of what was
# proposed on a day, not a live claim about the code.
EXEMPT_DIRS = {"history", "attic", "adr", "archive", "plans", ".kilo"}

SCRIPT_REF = re.compile(r"`(shesh-[a-z0-9-]+(?:-mcp)?)`")
TOOL_DEF = re.compile(r"@mcp\.tool\(\)\s*(?:async\s+)?def\s+([a-z_][a-z0-9_]*)")


def _iter_docs(repo: Path):
    for f in sorted(repo.rglob("*.md")):
        parts = set(f.relative_to(repo).parts)
        if ".git" in parts or parts & EXEMPT_DIRS:
            continue
        if f.name in EXEMPT_NAMES:
            continue
        yield f


def _declared_scripts(fleet: Path) -> set[str]:
    names: set[str] = set()
    for py in fleet.rglob("pyproject.toml"):
        if ".git" in py.parts:
            continue
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        names.update(data.get("project", {}).get("scripts", {}))
    return names


def check(fleet: Path) -> list[str]:
    findings: list[str] = []
    repos = sorted(p for p in fleet.iterdir() if (p / ".git").is_dir())
    scripts = _declared_scripts(fleet)
    # Repository directory names are legitimate references, not script claims.
    repo_names = {p.name for p in repos}
    # The console-script half of this guard needs every publisher present. In
    # CI only some siblings are cloned, and asserting against a partial fleet
    # reports a script as missing when the repository declaring it was simply
    # not checked out. A guard that cries wolf gets ignored, so that half is
    # skipped unless the publishers are all here.
    PUBLISHERS = {"shesh-core", "shesh-skills", "shesh-memory",
                  "shesh-orchestrator", "shesh-harness", "shesh-omniroute"}
    have_full_fleet = PUBLISHERS <= {p.name for p in repos}

    for repo in repos:
        if repo.name in EXEMPT_REPOS:
            continue
        for doc in _iter_docs(repo):
            rel = doc.relative_to(fleet)
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith(("|", ">", "    ", "\t")):
                    continue  # tables, quotes, and code blocks
                m = VOLATILE.search(line)
                if m:
                    findings.append(
                        f"{rel}:{i}: volatile count {m.group(0)!r} in prose; "
                        f"a number written by hand goes stale silently")
            if not have_full_fleet:
                continue
            for m in SCRIPT_REF.finditer(text):
                name = m.group(1)
                if name in repo_names or name in scripts:
                    continue
                if not name.endswith("-mcp"):
                    continue  # only console-script-shaped names are claims
                findings.append(
                    f"{rel}: names console script {name!r}, which no "
                    f"pyproject declares")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
