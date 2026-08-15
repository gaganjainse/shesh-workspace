#!/usr/bin/env python3
"""Safe GitHub-Issues swarm worker.

The worker owns queue coordination, branch isolation, gates, and PR creation.
It deliberately does *not* pretend to implement a task: a real implementation
callback must be supplied with ``--executor module:function`` or
``SHESH_WORKER_EXECUTOR``.  Without one, the process polls harmlessly and
never claims an issue or creates a marker-only PR.

Executor protocol::

    def implement(issue: dict, root: pathlib.Path, branch: str, component: str):
        # edit the checked-out worktree and return (success, summary)
        return True, "implemented ..."

A callback may instead return ``True``/``False`` or a summary string.  It runs
only after an atomic GitHub claim and must leave the worktree with the real
source/documentation change.  The worker refuses to commit an empty tree.

GitHub HTTPS pushes use ``tools/git_askpass.py`` with a PAT loaded through
``github_auth``.  The token is kept in the process environment or the 0600
PAT file; it is never put in a remote URL, Git config, command line, or log.
"""

from __future__ import annotations

import argparse
import importlib
import os
import pathlib
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/swarm"))

import common as fileq  # noqa: E402
import github_auth  # noqa: E402
import github_queue as ghq  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)  # visible logs when piped/nohup'd
except (AttributeError, ValueError, OSError):
    # stdout is a StringIO/pipe without reconfigure() — cosmetic only, keep going.
    pass

Executor = Callable[[dict, pathlib.Path, str, str], Any]
DEFAULT_GIT_NAME = "shesh-swarm-worker"
DEFAULT_GIT_EMAIL = "shesh-swarm-worker@users.noreply.github.com"


def has_gh_cli() -> bool:
    import shutil

    return shutil.which("gh") is not None


def _run_git(*args: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run Git without a shell so branch/title text cannot be interpreted."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def _run_command(*args: str, timeout: int = 900) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            list(args),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def configure_git_environment(pat: str) -> None:
    """Configure inherited Git/gh authentication without persisting secrets."""
    os.environ.update(github_auth.git_environment(pat))
    # A clean Arena clone has no user config.  Environment identity works for
    # this process and does not alter the user's global Git identity.
    os.environ.setdefault("GIT_AUTHOR_NAME", DEFAULT_GIT_NAME)
    os.environ.setdefault("GIT_AUTHOR_EMAIL", DEFAULT_GIT_EMAIL)
    os.environ.setdefault("GIT_COMMITTER_NAME", DEFAULT_GIT_NAME)
    os.environ.setdefault("GIT_COMMITTER_EMAIL", DEFAULT_GIT_EMAIL)


class ExecutorSpecError(ValueError):
    """SHESH_WORKER_EXECUTOR was not in module:function form."""

    def __init__(self) -> None:
        super().__init__("executor must use module:function syntax")


class ExecutorNotCallableError(TypeError):
    """The resolved executor attribute is not callable."""

    def __init__(self, spec: str) -> None:
        super().__init__(f"executor {spec!r} is not callable")


def load_executor(spec: str | None) -> Executor | None:
    """Load a ``module:function`` implementation callback."""
    if not spec:
        return None
    module_name, separator, function_name = spec.partition(":")
    if not separator or not module_name or not function_name:
        raise ExecutorSpecError
    module = importlib.import_module(module_name)
    callback = getattr(module, function_name, None)
    if not callable(callback):
        raise ExecutorNotCallableError(spec)
    return callback


def _executor_result(result: Any) -> tuple[bool, str]:
    if isinstance(result, tuple) and len(result) == 2:
        return bool(result[0]), str(result[1])
    if isinstance(result, bool):
        return result, "executor returned success" if result else "executor returned failure"
    if isinstance(result, str):
        return True, result
    if result is None:
        return False, "executor returned no result"
    return True, f"executor completed ({type(result).__name__})"


def do_work(
    issue: dict,
    branch: str,
    agent_id: str,
    component: str,
    executor: Executor | None,
) -> tuple[bool, str]:
    """Run the supplied implementation callback; never create a fake marker."""
    if executor is None:
        return False, "no implementation callback configured"
    print(
        f"[{agent_id}] Implementing issue #{issue['number']} "
        f"{issue['title'][:80]} in branch {branch}"
    )
    try:
        return _executor_result(executor(issue, ROOT, branch, component))
    except Exception as exc:  # noqa: BLE001
        # Boundary: any executor (pluggable user code) failure must release
        # the claim and report failure — an exotic raised type must not
        # leave the task wedged as "claimed" forever. The summary string
        # carries the error into the ledger; nothing is swallowed.
        return False, f"executor failed: {exc}"


def checkout_main() -> bool:
    rc, _, err = _run_git("checkout", "-f", "main")
    if rc != 0:
        print(f"Checkout main failed: {err[:500]}", file=sys.stderr)
        return False
    rc, _, err = _run_git("reset", "--hard", "origin/main")
    if rc != 0:
        print(f"Reset main failed: {err[:500]}", file=sys.stderr)
        return False
    return True


def checkout_branch(branch: str) -> bool:
    """Check out the exact remote branch created by the atomic claim."""
    rc, _, err = _run_git("fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    if rc != 0:
        print(f"Fetch {branch} failed: {err[:500]}", file=sys.stderr)
        return False
    rc, _, err = _run_git("checkout", "-B", branch, f"origin/{branch}")
    if rc != 0:
        print(f"Checkout {branch} failed: {err[:500]}", file=sys.stderr)
        return False
    return True


def commit_work(component: str, issue: dict) -> tuple[bool, str]:
    """Stage and commit real changes; reject an empty worktree."""
    rc, _, err = _run_git("add", "-A")
    if rc != 0:
        return False, f"git add failed: {err[-500:]}"

    rc, _, err = _run_git("diff", "--cached", "--quiet")
    if rc == 0:
        return False, "executor produced no repository changes"
    if rc != 1:
        return False, f"staged diff check failed: {err[-500:]}"

    title = " ".join(issue.get("title", "").split())[:80]
    message = f"feat({component}): swarm #{issue['number']} {title}".strip()
    rc, _, err = _run_git("commit", "-m", message)
    if rc != 0:
        return False, f"git commit failed: {err[-500:]}"
    return True, message


def push_branch(branch: str) -> bool:
    rc, _, err = _run_git("push", "--set-upstream", "origin", branch)
    if rc != 0:
        print(f"Push {branch} failed: {err[:800]}", file=sys.stderr)
        return False
    return True


def run_gate() -> tuple[bool, str]:
    rc, out, err = _run_command("make", "check")
    if rc == 0:
        return True, out[-2000:]
    return False, (out + err)[-3000:]


def run_gh(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["gh", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def create_pr_with_gh(branch: str, issue_number: int, title: str) -> bool:
    if has_gh_cli():
        rc, out, err = run_gh(
            [
                "pr",
                "create",
                "--title",
                title,
                "--body",
                (
                    f"Closes #{issue_number}\n\n"
                    f"Swarm worker branch: {branch}\n\n"
                    "Auto-merge Action will merge only after `make check` passes."
                ),
                "--base",
                "main",
                "--head",
                branch,
                "--label",
                "swarm",
            ]
        )
        if rc == 0:
            print(f"Created PR via gh: {out.strip()}")
            return True
        print(f"gh pr create failed: {err[:800]}", file=sys.stderr)
        return False

    result = ghq.create_pr(branch, issue_number, title, body=f"Swarm worker {branch}")
    return result is not None


def release_claim(issue_number: int, agent_id: str, branch: str, reason: str) -> None:
    """Return failed/no-op work to GitHub and restore the local main branch."""
    ghq.release_issue_claim(issue_number, agent_id, branch, reason)
    checkout_main()


def main() -> int:
    ap = argparse.ArgumentParser(description="Safe swarm worker: GitHub Issues + PR")
    ap.add_argument("--component", default="general", help="component filter, e.g. shesh-memory")
    ap.add_argument("--poll", type=int, default=45, help="poll interval in seconds")
    ap.add_argument("--once", action="store_true", help="inspect/do at most one task")
    ap.add_argument("--github", action="store_true", help="require GitHub Issues queue")
    ap.add_argument("--list", action="store_true", help="list pending issues and exit")
    ap.add_argument("--setup", action="store_true", help="selective clone only needed repos")
    ap.add_argument("--clean", action="store_true", help="clean caches")
    ap.add_argument(
        "--executor",
        default=None,
        help="real implementation callback as module:function (or SHESH_WORKER_EXECUTOR)",
    )
    args = ap.parse_args()

    if args.setup or args.clean:
        if args.clean:
            subprocess.run([sys.executable, "tools/setup_worker.py", "--clean"], cwd=str(ROOT), check=False)
        if args.component != "general":
            subprocess.run(
                [sys.executable, "tools/setup_worker.py", "--component", args.component],
                cwd=str(ROOT),
                check=False,
            )
        else:
            print("Setup efficient — platform role no src clone needed")

    pat = github_auth.load_pat()
    use_github = args.github or pat is not None
    if use_github and not pat:
        print("GitHub mode requested but no PAT is available; refusing unsafe fallback.", file=sys.stderr)
        return 2
    if pat:
        configure_git_environment(pat)

    executor_spec = args.executor or os.environ.get("SHESH_WORKER_EXECUTOR")
    try:
        executor = load_executor(executor_spec)
    except (ImportError, TypeError, ValueError) as exc:
        print(f"Invalid implementation executor: {exc}", file=sys.stderr)
        return 2

    agent_id = fileq.gen_agent_id(f"worker-{args.component}")
    print(
        f"Worker {agent_id} component={args.component} "
        f"use_github={use_github} has_gh={has_gh_cli()} "
        f"executor={executor_spec or 'none'}"
    )
    if pat:
        print(f"PAT present: {pat[:4]}****{pat[-4:] if len(pat) > 8 else ''}")

    if args.list:
        if use_github:
            issues = ghq.list_pending_issues(args.component)
            for issue in issues[:20]:
                labels = ",".join(label["name"] for label in issue.get("labels", []))
                print(f"#{issue['number']} [{labels}] {issue['title']}")
            print(f"Total {len(issues)}")
        else:
            pending = fileq.list_tasks("pending")
            for task in pending[:20]:
                print(f"{task['id']} {task['component']}: {task['title']}")
            print(f"Total {len(pending)}")
        return 0

    if executor is None:
        print(
            "No implementation callback configured; polling safely without "
            "claiming issues or creating marker-only PRs. "
            "Pass --executor module:function to enable work."
        )

    completed = 0
    while True:
        try:
            if executor is None:
                if args.once:
                    return 0
                time.sleep(args.poll)
                continue

            if not use_github:
                print("A real executor requires --github and a PAT; refusing file-queue simulation.")
                return 2

            if not checkout_main():
                time.sleep(args.poll)
                continue
            issues = ghq.list_pending_issues(args.component)
            if not issues:
                print(f"[{agent_id}] No pending GitHub issues for {args.component}, waiting {args.poll}s")
                if args.once:
                    return 0
                time.sleep(args.poll)
                continue

            issue = issues[0]
            issue_number = issue["number"]
            print(f"[{agent_id}] Attempting atomic claim issue #{issue_number}: {issue['title'][:80]}")
            ok, branch_or_err = ghq.claim_issue_atomic(issue_number, agent_id)
            if not ok:
                print(f"[{agent_id}] Claim failed: {branch_or_err}")
                if args.once:
                    return 1
                time.sleep(3)
                continue

            branch = branch_or_err
            if not checkout_branch(branch):
                release_claim(issue_number, agent_id, branch, "could not check out claimed branch")
                if args.once:
                    return 1
                continue

            success, summary = do_work(issue, branch, agent_id, args.component, executor)
            if not success:
                print(f"[{agent_id}] Work refused/failed: {summary}", file=sys.stderr)
                release_claim(issue_number, agent_id, branch, summary)
                if args.once:
                    return 1
                continue

            gate_ok, gate_output = run_gate()
            if not gate_ok:
                reason = f"gate failed: {gate_output}"
                print(f"[{agent_id}] {reason}", file=sys.stderr)
                release_claim(issue_number, agent_id, branch, reason)
                if args.once:
                    return 1
                continue

            committed, commit_summary = commit_work(args.component, issue)
            if not committed:
                print(f"[{agent_id}] {commit_summary}", file=sys.stderr)
                release_claim(issue_number, agent_id, branch, commit_summary)
                if args.once:
                    return 1
                continue

            if not push_branch(branch):
                release_claim(issue_number, agent_id, branch, "GitHub branch push failed")
                if args.once:
                    return 1
                continue

            created = create_pr_with_gh(branch, issue_number, issue["title"])
            if not created:
                # Preserve real pushed work for manual recovery; do not delete a
                # branch that contains a valid commit merely because PR API failed.
                ghq.comment_issue(
                    issue_number,
                    f"⚠️ Branch `{branch}` was pushed by `{agent_id}` but PR creation failed. "
                    "The issue remains claimed for manual recovery.",
                )
                print(f"[{agent_id}] PR creation failed; real branch preserved", file=sys.stderr)
            else:
                completed += 1
                print(f"[{agent_id}] PR created for issue #{issue_number}; completed={completed}")

            if not checkout_main():
                return 1
            if args.once:
                return 0 if created else 1
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nWorker stopped")
            return 0
        except Exception as exc:  # noqa: BLE001
            # Daemon boundary: a poisoned issue must not kill the worker.
            # The error goes to stderr (the daemon log) and polling resumes.
            print(f"Worker error: {exc}", file=sys.stderr)
            if args.once:
                return 1
            time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())
