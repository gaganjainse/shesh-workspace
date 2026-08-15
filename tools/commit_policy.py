#!/usr/bin/env python3
"""Enforce the commit and push rules in FACTORY.md.

Rules that are only written down drift. These are the mechanically checkable
subset, usable as a commit-msg hook, a pre-push hook, and a CI gate.

Usage:
    commit_policy.py message <file>     # commit-msg hook
    commit_policy.py push [--remote R]  # pre-push: batching and gate
    commit_policy.py range <base>..<head>
    commit_policy.py install [repo...]  # install hooks
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

TYPES = {"feat", "fix", "docs", "refactor", "test", "perf",
         "build", "ci", "chore", "revert"}

SUBJECT_MAX = 72
BODY_MAX = 72
PUSH_BATCH = 5          # FACTORY.md §7: push at five or more commits

HEADER = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9._/-]+)\))?"
                    r"(?P<bang>!)?: (?P<subject>.+)$")

# A credential in a commit message is as bad as one in a file.
SECRETS = [
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "GitHub personal access token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "API secret key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
]

PAST_TENSE = re.compile(r"^(added|fixed|updated|removed|changed|created|"
                        r"deleted|renamed|moved|refactored|implemented|"
                        r"adds|fixes|updates|removes|changes|creates)\b", re.I)


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          cwd=cwd).stdout.strip()


def check_message(text: str) -> list[str]:
    """Validate one commit message. Returns a list of problems."""
    errors: list[str] = []
    lines = [ln.rstrip() for ln in text.strip().split("\n")]
    lines = [ln for ln in lines if not ln.startswith("#")]
    if not lines or not lines[0].strip():
        return ["empty commit message"]

    subject = lines[0]

    # Merge and revert commits are generated; do not police them.
    if subject.startswith(("Merge ", "Revert ")):
        return []

    m = HEADER.match(subject)
    if not m:
        errors.append(
            f"subject must be '<type>(<scope>): <subject>', got: {subject!r}\n"
            f"        valid types: {', '.join(sorted(TYPES))}")
        return errors

    ctype = m.group("type")
    body_subject = m.group("subject")

    if ctype not in TYPES:
        errors.append(f"unknown type {ctype!r}; valid: {', '.join(sorted(TYPES))}")
    if len(subject) > SUBJECT_MAX:
        errors.append(f"subject is {len(subject)} chars, limit {SUBJECT_MAX}")
    if body_subject[:1].isupper() and not body_subject.split()[0].isupper():
        errors.append("subject must not start with a capital letter")
    if body_subject.endswith("."):
        errors.append("subject must not end with a full stop")
    if PAST_TENSE.match(body_subject):
        errors.append(f"use the imperative: {body_subject.split()[0]!r} "
                      f"should be 'add', 'fix', 'update', …")

    # Blank line between subject and body
    if len(lines) > 1 and lines[1].strip():
        errors.append("leave a blank line between the subject and the body")

    for i, line in enumerate(lines[2:], start=3):
        if len(line) > BODY_MAX and not re.search(r"https?://|`|\|", line):
            errors.append(f"body line {i} is {len(line)} chars, wrap at {BODY_MAX}")

    if m.group("bang") and "BREAKING CHANGE:" not in text:
        errors.append("'!' marks a breaking change; add a BREAKING CHANGE: footer")

    for pattern, what in SECRETS:
        if pattern.search(text):
            errors.append(f"commit message contains a {what}; remove it and "
                          f"rotate the credential")
    return errors


def cmd_message(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    errors = check_message(text)
    if not errors:
        return 0
    print("Commit message rejected (FACTORY.md §6):\n", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print("\nExample:\n  fix(a2a): resolve broker socket path at call time\n",
          file=sys.stderr)
    return 1


def cmd_range(rng: str) -> int:
    out = git("log", "--format=%H", rng)
    shas = [s for s in out.split("\n") if s]
    bad = 0
    for sha in shas:
        msg = git("log", "-1", "--format=%B", sha)
        errors = check_message(msg)
        if errors:
            bad += 1
            print(f"\n{sha[:8]} {msg.splitlines()[0][:60]}")
            for e in errors:
                print(f"    - {e}")
    print(f"\n{len(shas)} commit(s) checked, {bad} rejected")
    return 1 if bad else 0


def cmd_push(remote: str) -> int:
    """Pre-push: enforce batching, branch protection, and the gate."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD")

    if branch in {"main", "master"} and not os.environ.get("SHESH_ALLOW_MAIN"):
        print("Refusing to push to a protected branch (FACTORY.md §8).\n"
              "Open a pull request from a feature branch.\n\n"
              "Single-maintainer exception (FACTORY.md §9): when the gate is\n"
              "green and there is no second reviewer, push deliberately with\n"
              "  SHESH_ALLOW_MAIN=1 git push\n"
              "The variable exists so the choice is explicit and greppable,\n"
              "not so the rule can be forgotten.", file=sys.stderr)
        return 1

    upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    base = upstream if upstream else f"{remote}/main"
    ahead = git("rev-list", "--count", f"{base}..HEAD")
    n = int(ahead) if ahead.isdigit() else 0

    if n == 0:
        print("Nothing to push.")
        return 0

    # FACTORY.md §7: batch pushes. Override for an explicit or urgent push.
    if n < PUSH_BATCH and not os.environ.get("SHESH_PUSH_NOW"):
        print(f"Holding {n} commit(s); the batch size is {PUSH_BATCH} "
              f"(FACTORY.md §7).\n"
              f"Push anyway with:  SHESH_PUSH_NOW=1 git push", file=sys.stderr)
        return 1

    rc = cmd_range(f"{base}..HEAD")
    if rc:
        print("\nFix the messages with an interactive rebase before pushing.",
              file=sys.stderr)
    return rc


HOOK_MSG = """#!/bin/sh
# Installed by shesh-workspace/tools/commit_policy.py
exec python3 "{tool}" message "$1"
"""

HOOK_PUSH = """#!/bin/sh
# Installed by shesh-workspace/tools/commit_policy.py
exec python3 "{tool}" push --remote "$1"
"""


def cmd_install(repos: list[str]) -> int:
    tool = os.path.abspath(__file__)
    n = 0
    for repo in repos:
        hooks = os.path.join(repo, ".git", "hooks")
        if not os.path.isdir(hooks):
            print(f"  skip {repo}: not a git repository")
            continue
        for name, body in (("commit-msg", HOOK_MSG), ("pre-push", HOOK_PUSH)):
            p = os.path.join(hooks, name)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body.format(tool=tool))
            os.chmod(p, 0o755)
        n += 1
        print(f"  hooks installed: {os.path.basename(os.path.abspath(repo))}")
    print(f"{n} repository/repositories configured")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("message"); p.add_argument("file")
    p = sub.add_parser("range"); p.add_argument("range")
    p = sub.add_parser("push"); p.add_argument("--remote", default="origin")
    p = sub.add_parser("install"); p.add_argument("repos", nargs="+")

    a = ap.parse_args()
    if a.cmd == "message":
        return cmd_message(a.file)
    if a.cmd == "range":
        return cmd_range(a.range)
    if a.cmd == "push":
        return cmd_push(a.remote)
    if a.cmd == "install":
        return cmd_install(a.repos)
    return 2


if __name__ == "__main__":
    sys.exit(main())
