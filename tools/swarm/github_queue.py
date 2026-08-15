#!/usr/bin/env python3
"""GitHub Issues + Projects as swarm queue — atomic claim via git refs."""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import github_auth  # noqa: E402

OWNER = os.environ.get("SWARM_OWNER", "gaganjainse")
REPO = os.environ.get("SWARM_REPO", "shesh-ecosystem")
API_BASE = f"https://api.github.com/repos/{OWNER}/{REPO}"
PROJECT_NUMBER = os.environ.get("GITHUB_PROJECT_NUMBER")
BLOCKED_LABELS = {"blocked", "swarm:blocked"}
# Circuit breaker: an issue that fails this many claim cycles is labelled
# swarm:blocked so no autonomous worker retries it forever (2026-08-11 churn).
MAX_ATTEMPTS = int(os.environ.get("SWARM_MAX_ATTEMPTS", "3"))


def is_blocked_issue(issue: dict) -> bool:
    """Return True for issues explicitly marked or described as blocked."""
    labels = {label.get("name", "").lower() for label in issue.get("labels", [])}
    if labels & BLOCKED_LABELS:
        return True
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}"
    return bool(re.search(r"(^|\n)\s*🔴|\bdo not force\b|\bblocked\b", text, re.IGNORECASE))


def _priority_key(issue: dict) -> tuple[int, int]:
    labels = {label.get("name", "") for label in issue.get("labels", [])}
    order = {"P0": 0, "P1": 1, "P2": 2}
    priority = min((order[name] for name in labels if name in order), default=3)
    return (priority, int(issue.get("number", 0)))


def _pat() -> str | None:
    return github_auth.load_pat()


def _headers() -> dict[str, str]:
    pat = _pat()
    if not pat:
        return {}
    return {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "shesh-swarm/1.0",
    }


def _request(method: str, url: str, data: dict | None = None) -> tuple[int, Any]:
    hdrs = _headers()
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            txt = resp.read().decode()
            j = json.loads(txt) if txt else {}
            return resp.status, j
    except urllib.error.HTTPError as e:
        try:
            txt = e.read().decode(errors="replace")
        finally:
            e.close()  # an HTTPError is a live socket; never leak it
        try:
            j = json.loads(txt) if txt else {"message": txt}
        except json.JSONDecodeError:
            j = {"message": txt, "status": e.code}
        return e.code, j
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"message": str(e)}


def ensure_label(name: str, color: str = "fbca04", description: str = "") -> None:
    """Create a repo label if missing (422 = already exists, ignored)."""
    status, resp = _request(
        "POST",
        f"{API_BASE}/labels",
        {"name": name, "color": color, "description": description},
    )
    if status not in (200, 201, 422):
        print(f"ensure_label {name}: {status} {resp}", file=sys.stderr)


def create_issue(task: dict) -> tuple[int, dict] | None:
    pat = _pat()
    if not pat:
        print("No PAT, cannot create issue", file=sys.stderr)
        return None

    title = f"[swarm] {task['id']} {task['title'][:80]}"
    status, issues = _request(
        "GET", f"{API_BASE}/issues?labels=swarm&state=open&per_page=100"
    )
    if status == 200:
        for iss in issues:
            if task["id"] in iss.get("title", ""):
                print(f"Issue exists for {task['id']}: #{iss['number']}")
                return (iss["number"], iss)

    body = f"""**Swarm task**
- ID: `{task['id']}`
- Component: `{task.get('component','general')}`
- Priority: `{task.get('priority','P1')}`
- Raw TODO: {task.get('raw','')}

```
{json.dumps(task, indent=2)}
```
Claim via worker_github.py --issue {task['id']}
Auto-merge Action swarm-auto-merge.yml merges PR if make check green.
"""
    labels = [
        "swarm",
        "swarm:blocked" if task.get("blocked") else "swarm:pending",
        f"component:{task.get('component','general')}",
        task.get("priority", "P1"),
    ]
    for lab in labels:
        ensure_label(lab)
    data = {"title": title, "body": body, "labels": labels}
    status, resp = _request("POST", f"{API_BASE}/issues", data)
    if status in (200, 201):
        print(f"Created issue #{resp.get('number')} for {task['id']}")
        return (resp.get("number"), resp)
    print(f"Failed create {task['id']}: {status} {resp}", file=sys.stderr)
    return None


def list_pending_issues(component: str = "general") -> list[dict]:
    pat = _pat()
    if not pat:
        sys.path.insert(0, str(ROOT / "tools/swarm"))
        import common as fileq

        return fileq.list_tasks("pending")

    status, issues = _request(
        "GET", f"{API_BASE}/issues?labels=swarm:pending&state=open&per_page=100"
    )
    if status != 200:
        print(f"Failed list: {status} {issues}", file=sys.stderr)
        return []

    # Never hand an explicitly blocked issue to an autonomous worker.
    issues = [issue for issue in issues if not is_blocked_issue(issue)]
    if component != "general":
        filtered = []
        for iss in issues:
            labs = [lb["name"] for lb in iss.get("labels", [])]
            if f"component:{component}" in labs or "component:general" in labs:
                filtered.append(iss)
        # Strict: never fall back to arbitrary pending tasks when nothing
        # matches the component (Tab2 fix 29c3891) — wait instead.
        return sorted(filtered, key=_priority_key)
    return sorted(issues, key=_priority_key)


def claim_issue_atomic(issue_number: int, agent_id: str) -> tuple[bool, str]:
    """Atomic claim via lock ref swarm/claims/issue-N (single per issue)."""
    pat = _pat()
    if not pat:
        sys.path.insert(0, str(ROOT / "tools/swarm"))
        import common as fileq

        task_id = f"issue-{issue_number}"
        ok = fileq.try_claim(task_id, agent_id)
        return (ok, f"swarm/{task_id}/{agent_id}" if ok else "file claim failed")

    # Get main sha
    status, data = _request("GET", f"{API_BASE}/git/refs/heads/main")
    if status != 200:
        status, repo_info = _request("GET", f"{API_BASE}")
        default_branch = repo_info.get("default_branch", "main")
        status, data = _request(
            "GET", f"{API_BASE}/git/refs/heads/{default_branch}"
        )
        if status != 200:
            return False, f"cannot get main sha: {status} {data}"
    sha = data.get("object", {}).get("sha")
    if not sha:
        return False, "no sha for main"

    # Atomic lock ref per issue
    lock_ref = f"refs/heads/swarm/claims/issue-{issue_number}"
    payload = {"ref": lock_ref, "sha": sha}
    status, resp = _request("POST", f"{API_BASE}/git/refs", payload)
    if status == 422:
        return False, f"already claimed (lock {lock_ref} exists)"
    if status not in (200, 201):
        return False, f"lock create failed {status} {resp}"

    # Create personal work branch
    work_branch = f"swarm/issue-{issue_number}/{agent_id}"
    work_ref = f"refs/heads/{work_branch}"
    payload = {"ref": work_ref, "sha": sha}
    status, resp = _request("POST", f"{API_BASE}/git/refs", payload)
    if status not in (200, 201, 422):
        print(f"Work branch create failed {status} {resp}", file=sys.stderr)

    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/labels",
        {"labels": ["swarm:claimed"]},
    )
    _request("DELETE", f"{API_BASE}/issues/{issue_number}/labels/swarm:pending")
    comment = (
        f"🤖 Claimed by `{agent_id}`\n"
        f"- Lock: `{lock_ref}`\n"
        f"- Work branch: `{work_branch}`\n"
        f"- Time: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n"
        f"Worker will push to `{work_branch}` and open PR → main. "
        f"Action swarm-auto-merge.yml merges if make check green."
    )
    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/comments",
        {"body": comment},
    )
    return True, work_branch


def comment_issue(issue_number: int, body: str) -> None:
    _request(
        "POST", f"{API_BASE}/issues/{issue_number}/comments", {"body": body}
    )


def _swarm_labels(issue_number: int) -> set[str]:
    status, issue = _request("GET", f"{API_BASE}/issues/{issue_number}")
    if status != 200:
        return set()
    return {label.get("name", "") for label in issue.get("labels", [])}


def attempt_count(issue_number: int) -> int:
    """How many failed claim cycles this issue has absorbed (swarm:attempt-N)."""
    counts = []
    for name in _swarm_labels(issue_number):
        match = re.fullmatch(r"swarm:attempt-(\d+)", name)
        if match:
            counts.append(int(match.group(1)))
    return max(counts, default=0)


def record_attempt(issue_number: int) -> int:
    """Label the next failed-attempt notch; returns the new attempt count."""
    count = attempt_count(issue_number) + 1
    label = f"swarm:attempt-{count}"
    ensure_label(label, color="e99695", description="failed swarm claim cycles")
    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/labels",
        {"labels": [label]},
    )
    return count


def block_issue(issue_number: int, reason: str) -> None:
    """Take an issue out of the autonomous queue until a human unblocks it."""
    ensure_label("swarm:blocked", color="b60205", description="needs human decision")
    _request(
        "DELETE", f"{API_BASE}/issues/{issue_number}/labels/swarm:pending"
    )
    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/labels",
        {"labels": ["swarm:blocked"]},
    )
    comment_issue(
        issue_number,
        "⛔ **Swarm circuit breaker tripped.**\n\n"
        f"Reason: {reason[:800]}\n\n"
        f"This issue failed {MAX_ATTEMPTS} claim cycles, so autonomous workers "
        "will skip it to avoid endless retry churn. A human should refine the "
        "task spec, then remove `swarm:blocked` and re-add `swarm:pending`.",
    )


def _pr_body(issue_number: int, body: str) -> str:
    content = body.strip()
    if issue_number:
        content = f"{content}\n\nCloses #{issue_number}"
    return f"{content}\n\nSwarm auto-merge if make check green."


def create_pr(branch: str, issue_number: int, title: str, body: str = "") -> tuple[int, dict] | None:
    pat = _pat()
    if not pat:
        print("No PAT, cannot create PR", file=sys.stderr)
        return None
    data = {
        "title": title,
        "body": _pr_body(issue_number, body),
        "head": branch,
        "base": "main",
    }
    status, resp = _request("POST", f"{API_BASE}/pulls", data)
    if status in (200, 201):
        print(f"Created PR #{resp.get('number')} {branch} -> main")
        return (resp.get("number"), resp)
    print(f"Failed PR {branch}: {status} {resp}", file=sys.stderr)
    return None


def release_issue_claim(
    issue_number: int,
    agent_id: str,
    work_branch: str,
    reason: str,
) -> bool:
    """Release this worker's claim and put an unfinished issue back in queue.

    This is used only before a PR exists (executor/gate/push failure).  It
    removes both refs created by :func:`claim_issue_atomic`, restores the
    pending label, and leaves an audit comment.  A branch belonging to a
    different agent is never deleted.
    """
    expected_prefix = f"swarm/issue-{issue_number}/{agent_id}"
    if work_branch != expected_prefix:
        print(f"Refusing to release unexpected branch {work_branch}", file=sys.stderr)
        return False

    ok = True
    for ref in (f"swarm/claims/issue-{issue_number}", work_branch):
        status, response = _request("DELETE", f"{API_BASE}/git/refs/heads/{ref}")
        if status not in (204, 404):
            ok = False
            print(f"Failed to delete {ref}: {status} {response}", file=sys.stderr)

    status, response = _request(
        "DELETE", f"{API_BASE}/issues/{issue_number}/labels/swarm:claimed"
    )
    if status not in (200, 404):
        ok = False
        print(f"Failed to remove claimed label: {status} {response}", file=sys.stderr)

    status, response = _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/labels",
        {"labels": ["swarm:pending"]},
    )
    if status not in (200, 201):
        ok = False
        print(f"Failed to restore pending label: {status} {response}", file=sys.stderr)

    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/comments",
        {
            "body": (
                f"↩️ Claim released by `{agent_id}` before PR creation.\n"
                f"Reason: {reason[:500]}\n"
                "Issue returned to `swarm:pending`."
            )
        },
    )

    # Circuit breaker — never let one issue churn autonomous workers forever.
    attempts = record_attempt(issue_number)
    if attempts >= MAX_ATTEMPTS:
        block_issue(
            issue_number,
            f"release by `{agent_id}` was failure #{attempts}: {reason[:300]}",
        )
    return ok


def close_issue(issue_number: int, comment: str = "Completed via swarm") -> None:
    _request(
        "POST",
        f"{API_BASE}/issues/{issue_number}/comments",
        {"body": comment},
    )
    _request(
        "PATCH",
        f"{API_BASE}/issues/{issue_number}",
        {"state": "closed", "labels": ["swarm", "swarm:done"]},
    )
