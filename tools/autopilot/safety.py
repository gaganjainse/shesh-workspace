"""Hard safety invariants for the autopilot.

These are the "foolproof" layer: even if the planner makes a mistake,
these refuse actions that could lose work or push broken code. Git commands
use `git -C`; test/lint commands run directly in the repo's cwd.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class SafetyError(RuntimeError):
    """Raised when an action would violate a hard invariant."""


@dataclass(frozen=True)
class SafetyReport:
    ok: bool
    reason: str = ""


def _git(repo: Path, *args: str, timeout: int = 30) -> tuple[int, str, str]:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def _cmd(repo: Path, *args: str, timeout: int = 300) -> tuple[int, str, str]:
    p = subprocess.run(
        list(args), cwd=repo, capture_output=True, text=True, timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def is_git_repo(repo: Path) -> bool:
    return (repo / ".git").exists()


def current_branch(repo: Path) -> str:
    rc, out, _ = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if rc == 0 else ""


def has_uncommitted(repo: Path) -> bool:
    rc, out, _ = _git(repo, "status", "--porcelain")
    return rc == 0 and bool(out.strip())


def tests_pass(repo: Path) -> bool:
    """Run the component's test suite in isolation."""
    rc, _, _ = _cmd(
        repo, "python3", "-m", "pytest", "tests/", "-q",
        "-p", "no:cacheprovider", "-o", "addopts=", "--confcutdir", str(repo),
        timeout=300,
    )
    return rc == 0


def ruff_clean(repo: Path) -> bool:
    if not shutil.which("ruff"):
        return True
    rc, _, _ = _cmd(repo, "python3", "-m", "ruff", "check", "src/", "tests/",
                     timeout=120)
    return rc == 0


PROTECTED_PATHS = (".ssh", ".gnupg", "Vaults", "Documents/Job", "Projects/job")


def assert_safe_path(path: Path) -> None:
    resolved = path.resolve()
    for bad in PROTECTED_PATHS:
        if bad in str(resolved):
            raise SafetyError(f"refusing to touch protected path: {resolved}")


def assert_can_commit(repo: Path) -> SafetyReport:
    if not is_git_repo(repo):
        return SafetyReport(False, f"{repo}: not a git repo")
    if not has_uncommitted(repo):
        return SafetyReport(False, "nothing staged to commit")
    if not tests_pass(repo):
        raise SafetyError(f"{repo}: tests fail; refusing to commit")
    return SafetyReport(True, "ok")


def assert_can_push(repo: Path) -> SafetyReport:
    branch = current_branch(repo)
    if not branch:
        return SafetyReport(False, "no current branch")
    rc, url, _ = _git(repo, "remote", "get-url", "origin")
    if rc != 0 or not url.strip():
        return SafetyReport(False, "no origin remote")
    url = url.strip()
    # Canonical GitHub remotes are required for pushes. Local paths / file://
    # are allowed (tests, local mirrors). Refuse unknown http(s) remotes.
    if url.startswith(("http://", "https://", "git@")):
        if "gaganjainse/shesh-" not in url:
            return SafetyReport(False, f"refusing non-canonical remote: {url!r}")
    if has_uncommitted(repo):
        return SafetyReport(False, "uncommitted changes; commit first")
    return SafetyReport(True, "ok")


def safe_commit(repo: Path, message: str) -> str:
    report = assert_can_commit(repo)
    if not report.ok:
        raise SafetyError(report.reason)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=shesh-bot",
         "-c", "user.email=shesh-bot@users.noreply.github.com",
         "commit", "-q", "-m", message)
    rc, sha, _ = _git(repo, "rev-parse", "HEAD")
    return sha.strip()


def safe_push(repo: Path) -> None:
    report = assert_can_push(repo)
    if not report.ok:
        raise SafetyError(report.reason)
    rc, _, err = _git(repo, "push", "-q", "origin", "HEAD")
    if rc != 0:
        raise SafetyError(f"push failed: {err.strip()}")


def rollback(repo: Path) -> None:
    if is_git_repo(repo):
        _git(repo, "reset", "--soft", "HEAD~1")
