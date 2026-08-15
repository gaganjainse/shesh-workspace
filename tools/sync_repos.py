#!/usr/bin/env python3
"""tools/sync_repos.py — restore origin remotes on every sibling clone, fetch, report.

Adopted from the orchestrator's recovery toolkit (2026-08-12): sandbox
snapshot restores silently drop `origin` remotes, strip exec bits, and rewind
local HEADs while the worktree keeps newer content. This tool re-adds the
remote, fetches, and reports behind/ahead/dirty per repo so the (manual)
mixed-reset realignment stays an explicit, reviewable decision.

Never resets, never force-pushes. Report-only beyond the remote fix.

Env:
    SHESH_SRC   directory holding the clones (default: ~/src)
    SHESH_ORG   GitHub org/user for rebuilt remote URLs (default: gaganjainse)

Usage:
    GIT_ASKPASS=tools/git_askpass.py python3 tools/sync_repos.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess

SRC = pathlib.Path(os.environ.get("SHESH_SRC", pathlib.Path.home() / "src"))
ORG = os.environ.get("SHESH_ORG", "gaganjainse")

# Local dir name -> GitHub repo name, only where they differ.
NAME_MAP: dict[str, str] = {}


def git(*args: str, cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60, check=False
    )


def main() -> None:
    report = {}
    for d in sorted(SRC.iterdir()):
        if not (d / ".git").exists():
            continue
        name = d.name
        repo = NAME_MAP.get(name, name)
        url = f"https://github.com/{ORG}/{repo}.git"
        r = git("remote", "get-url", "origin", cwd=d)
        added = False
        if r.returncode != 0:
            git("remote", "add", "origin", url, cwd=d)
            added = True
        elif r.stdout.strip() != url:
            git("remote", "set-url", "origin", url, cwd=d)

        f = git("fetch", "origin", "--prune", cwd=d)
        head = git("rev-parse", "--abbrev-ref", "HEAD", cwd=d).stdout.strip()
        # Default branch from origin/HEAD, falling back to the current branch.
        def_ref = git("symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", cwd=d)
        default_branch = (
            def_ref.stdout.strip().split("/", 1)[-1] if def_ref.returncode == 0 else head
        )
        counts = ""
        for cand in (f"origin/{head}", f"origin/{default_branch}", "origin/main", "origin/master"):
            if git("rev-parse", "--verify", cand, cwd=d).returncode == 0:
                c = git(
                    "rev-list", "--left-right", "--count", f"{cand}...HEAD", cwd=d
                ).stdout.strip()
                counts = f"{cand}: {c}"
                break
        dirty = len(git("status", "--porcelain", cwd=d).stdout.strip().splitlines())
        report[name] = {
            "remote_added": added,
            "branch": head,
            "fetch_ok": f.returncode == 0,
            "vs_remote": counts,
            "dirty_files": dirty,
        }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
