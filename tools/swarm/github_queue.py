#!/usr/bin/env python3
"""GitHub Issues + Projects as swarm queue — atomic claim via git refs."""

from __future__ import annotations

import json
import os
import pathlib
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
        txt = e.read().decode() if hasattr(e, "read") else ""
        try:
            j = json.loads(txt) if txt else {"message": txt}
        except Exception:
            j = {"message": txt, "status": e.code}
        return e.code, j
    except Exception as e:
        return 0, {"message": str(e)}


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
        "swarm:pending",
        f"component:{task.get('component','general')}",
        task.get("priority", "P1"),
    ]
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
    if component != "general":
        filtered = []
        for iss in issues:
            labs = [lb["name"] for lb in iss.get("labels", [])]
            if f"component:{component}" in labs or "component:general" in labs:
                filtered.append(iss)
        if not filtered:
            filtered = issues
        return filtered
    return issues


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


def create_pr(branch: str, issue_number: int, title: str, body: str = "") -> tuple[int, dict] | None:
    pat = _pat()
    if not pat:
        print("No PAT, cannot create PR", file=sys.stderr)
        return None
    pr_body = f"{body}\n\nCloses #{issue_number}\n\nSwarm auto-merge if make check green."
    data = {"title": title, "body": pr_body, "head": branch, "base": "main"}
    status, resp = _request("POST", f"{API_BASE}/pulls", data)
    if status in (200, 201):
        print(f"Created PR #{resp.get('number')} {branch} -> main")
        return (resp.get("number"), resp)
    print(f"Failed PR {branch}: {status} {resp}", file=sys.stderr)
    return None


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
