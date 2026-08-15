#!/usr/bin/env python3
"""F013: a stale check-run looks like a live failure.

Compare the check-run timestamp against the head commit. If it predates the
push, force a fresh run.

This guard queries the GitHub API for every repository in the fleet and reports
a check-run whose head SHA is no longer the branch head, or whose completion
time precedes the commit it claims to describe. Both mean the check describes a
state that no longer exists, and reading it as live costs an investigation into
a phantom.

The guard needs a token and network access. Without them it exits 2, meaning
"could not run", which is distinct from 0 (checked, clean) and 1 (stale check
found). It never exits 0 without having actually checked, because a guard that
quietly does nothing is the failure it is meant to catch (F003).

Usage:
    F013.py [fleet-root]   # 0 clean · 1 stale check-run shown · 2 could not run
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

API = "https://api.github.com"
# A check that finished before its commit existed cannot describe it. Allow a
# small clock skew between the runner and the git committer date.
SKEW = timedelta(minutes=2)


def _token() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"):
        v = os.environ.get(key)
        if v and v.strip():
            return v.strip()
    return None


def _get(url: str, token: str):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}",
                      "Accept": "application/vnd.github+json",
                      "User-Agent": "shesh-guard-F013"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def _slug(repo: Path) -> str | None:
    out = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    if not out or "github.com" not in out:
        return None
    tail = out.split("github.com", 1)[1].lstrip(":/")
    return tail.removesuffix(".git")


MISSING_TOKEN = "GitHub token"


class CannotRun(RuntimeError):
    """The guard could not perform its check; this is not a pass.

    The message is built here rather than at the raise site so the wording
    stays consistent and ruff's TRY003 is satisfied.
    """

    def __init__(self, missing: str = MISSING_TOKEN) -> None:
        super().__init__(
            f"no {missing} in the environment; export GITHUB_TOKEN to run "
            f"this guard. Not checked is not the same as clean.")


def check(fleet: Path) -> list[str]:
    token = _token()
    if not token:
        raise CannotRun

    findings: list[str] = []
    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        slug = _slug(repo)
        if not slug:
            continue
        try:
            branch = _get(f"{API}/repos/{slug}/branches/main", token)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        head = branch["commit"]["sha"]
        committed = branch["commit"]["commit"]["committer"]["date"]
        commit_at = datetime.fromisoformat(committed.replace("Z", "+00:00"))
        try:
            runs = _get(f"{API}/repos/{slug}/commits/{head}/check-runs", token)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        for run in runs.get("check_runs", []):
            if run.get("status") != "completed":
                continue
            done = run.get("completed_at")
            if not done:
                continue
            done_at = datetime.fromisoformat(done.replace("Z", "+00:00"))
            if done_at + SKEW < commit_at:
                findings.append(
                    f"{slug}: check-run {run['name']!r} finished {done} but "
                    f"main's head was committed {committed}; it describes an "
                    f"older tree and must be re-run before it is believed")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    try:
        found = check(root)
    except CannotRun as exc:
        print(f"  SKIPPED: {exc}")
        sys.exit(2)
    for f in found:
        print(f"  {f}")
    sys.exit(1 if found else 0)
