#!/usr/bin/env python3
"""Apply the factory conventions to every repository.

Issue and pull-request templates, the label set, and the commit hooks are
identical everywhere, so a contributor moving between repositories meets the
same process. Anything copied by hand drifts; this copies by rule.

Usage:
    factory_sync.py                 # apply locally
    factory_sync.py --check         # non-zero if anything drifted
    factory_sync.py --labels        # print `gh label` commands
"""
from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
FLEET = os.path.dirname(WS)
TEMPLATES = os.path.join(WS, "templates", "github")

REPOS = [
    "shesh-core", "shesh-memory", "shesh-orchestrator", "shesh-harness",
    "shesh-phone", "shesh-omniroute", "shesh-skills", "shesh-voice",
    "shesh-desktop", "SheshAOS", "shesh-ecosystem", "shesh-workspace",
    "shesh-docs", "shesh-docs-archive",
]

# FACTORY.md §10. Colour is meaning: red blocks, amber waits, blue is routine.
LABELS = [
    ("type:bug", "d73a4a", "Something behaves incorrectly"),
    ("type:feat", "0e8a16", "A capability that does not exist yet"),
    ("type:docs", "0075ca", "Documentation only"),
    ("type:refactor", "5319e7", "Behaviour unchanged"),
    ("type:chore", "cfd3d7", "Maintenance"),
    ("p0", "b60205", "Blocker: work stops for this"),
    ("p1", "d93f0b", "Next"),
    ("p2", "fbca04", "Planned"),
    ("p3", "c5def5", "Someday"),
    ("area:core", "1d76db", "shesh-core"),
    ("area:memory", "1d76db", "shesh-memory"),
    ("area:orchestrator", "1d76db", "shesh-orchestrator"),
    ("area:desktop", "1d76db", "Desktop and device control"),
    ("area:docs", "1d76db", "Documentation"),
    ("area:ci", "1d76db", "Pipelines and gates"),
    ("area:security", "b60205", "Security posture"),
    ("blocked", "000000", "Waiting on something external"),
    ("needs-decision", "e99695", "Needs a maintainer decision"),
    ("good-first-issue", "7057ff", "Small and well specified"),
]


def files_to_sync() -> list[tuple[str, str]]:
    out = []
    for root, _dirs, files in os.walk(TEMPLATES):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, TEMPLATES)
            out.append((src, os.path.join(".github", rel)))
    return sorted(out)


def sync(check: bool) -> int:
    pairs = files_to_sync()
    drift, wrote = [], 0

    for repo in REPOS:
        root = os.path.join(FLEET, repo)
        if not os.path.isdir(root):
            continue
        for src, rel in pairs:
            dst = os.path.join(root, rel)
            same = os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False)
            if same:
                continue
            if check:
                drift.append(os.path.join(repo, rel))
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            wrote += 1

    if check:
        if drift:
            print(f"{len(drift)} file(s) drifted from the factory templates:")
            for d in drift:
                print(f"  {d}")
            print("\nRun: python3 tools/factory_sync.py")
            return 1
        print("Factory templates are in sync.")
        return 0

    print(f"synced {wrote} file(s) across {len(REPOS)} repositories")
    return 0


def print_labels() -> int:
    print("# Apply the fleet label set. Requires the GitHub CLI.")
    print("# Idempotent: --force updates an existing label.\n")
    for repo in REPOS:
        print(f"# {repo}")
        for name, colour, desc in LABELS:
            print(f'gh label create "{name}" --repo gaganjainse/{repo} '
                  f'--color {colour} --description "{desc}" --force')
        print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--labels", action="store_true")
    a = ap.parse_args()
    if a.labels:
        return print_labels()
    return sync(a.check)


if __name__ == "__main__":
    sys.exit(main())
