#!/usr/bin/env python3
"""Worker that uses GitHub Issues + PRs + gh CLI — proper implementation.

Flow:
1. List pending issues via github_queue.list_pending_issues(component)
2. Atomic claim via github_queue.claim_issue_atomic() — creates branch via GitHub API (422 if exists = already claimed)
3. Checkout branch locally: git checkout -b <branch>
4. Do work: here calls autopilot runner or simulated
5. Run gate: make check
6. If green: git add + commit + push origin <branch>
7. Create PR via API (github_queue.create_pr) or gh CLI: gh pr create --title --body --base main --head <branch>
8. Artifact + close issue via comment, label swarm:done handled by auto-merge Action after merge

Fallback: if GH_TOKEN/PAT missing, uses file queue (common.py)

Usage:
  python tools/swarm/worker_github.py --component shesh-memory --poll 45 --once
  python tools/swarm/worker_github.py --github --component shesh-system

Requires PAT with contents:write, issues:write, pull-requests:write
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/swarm"))

import common as fileq
import github_auth
import github_queue as ghq

try:

    HAS_RUNNER = True
except Exception:
    HAS_RUNNER = False


def has_gh_cli() -> bool:
    import shutil

    return shutil.which("gh") is not None


def run_gh(args: list[str]) -> tuple[int, str, str]:
    import subprocess

    try:
        proc = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, timeout=30, cwd=str(ROOT)
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


def do_work(issue: dict, branch: str, agent_id: str, component: str) -> tuple[bool, str]:
    """Real work placeholder — integrate with autopilot."""
    print(f"[{agent_id}] Working on issue #{issue['number']} {issue['title'][:80]} in branch {branch}")

    # Example: if component task, edit its README or run its tests
    # Here we just create a work marker file
    marker = ROOT / f"swarm/artifacts/work-issue-{issue['number']}.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"Worked by {agent_id}\nIssue #{issue['number']}\nTitle: {issue['title']}\nBranch: {branch}\nComponent: {component}\n")

    # Simulate autopilot runner
    # For real: call process_task with task dict parsed from issue body
    # task = json.loads(re.search(r"```(.*)```", issue['body'], re.S).group(1))
    # autopilot_process(task)

    time.sleep(2)
    return True, f"Completed issue #{issue['number']} in {branch}"


def checkout_branch(branch: str) -> bool:
    # Check if branch exists locally
    rc, _, _ = fileq.sh(f"git checkout -b {branch}", cwd=ROOT)
    if rc != 0:
        # Try checkout existing
        rc, _, _ = fileq.sh(f"git checkout {branch}", cwd=ROOT)
        if rc != 0:
            # Fetch and checkout remote
            fileq.sh("git fetch origin", cwd=ROOT)
            rc, _, _ = fileq.sh(f"git checkout {branch}", cwd=ROOT)
    return rc == 0


def push_branch(branch: str) -> bool:
    rc, out, err = fileq.sh(f"git push -u origin {branch}", cwd=ROOT)
    if rc != 0:
        print(f"Push {branch} failed: {err[:500]}", file=sys.stderr)
        # Try push with --force-with-lease? No, we want safety — if push fails, rebase
        fileq.sh(f"git pull --rebase origin {branch} || true", cwd=ROOT)
        rc, out, err = fileq.sh(f"git push -u origin {branch}", cwd=ROOT)
    return rc == 0


def create_pr_with_gh(branch: str, issue_number: int, title: str) -> bool:
    if has_gh_cli():
        rc, out, err = run_gh(
            [
                "pr",
                "create",
                "--title",
                f"{title} (swarm #{issue_number})",
                "--body",
                f"Closes #{issue_number}\n\nSwarm worker {branch}\n\nAuto-merge Action will merge if `make check` green.",
                "--base",
                "main",
                "--head",
                branch,
                "--label",
                "swarm",
            ]
        )
        if rc == 0:
            print(f"Created PR via gh: {out}")
            return True
        else:
            print(f"gh pr create failed: {err}", file=sys.stderr)
            return False
    else:
        # Use API
        res = ghq.create_pr(branch, issue_number, title, body=f"Swarm worker {branch}")
        return res is not None


def main() -> int:
    ap = argparse.ArgumentParser(description="Swarm worker GitHub Issues + PR")
    ap.add_argument("--component", default="general", help="component filter e.g., shesh-memory")
    ap.add_argument("--poll", type=int, default=45)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--github", action="store_true", help="force GitHub Issues queue")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--setup", action="store_true", help="selective clone only needed repos")
    ap.add_argument("--clean", action="store_true", help="clean caches")
    args = ap.parse_args()

    # Efficiency: selective clone
    if args.setup or args.clean:
        import subprocess

        if args.clean:
            subprocess.run(
                ["python", "tools/setup_worker.py", "--clean"], cwd=str(ROOT)
            )
        if args.component != "general":
            subprocess.run(
                ["python", "tools/setup_worker.py", "--component", args.component],
                cwd=str(ROOT),
            )
        else:
            print("Setup efficient — platform role no src clone needed")

    pat = github_auth.load_pat()
    use_github = args.github or (pat is not None)

    agent_id = fileq.gen_agent_id(f"worker-{args.component}")
    print(f"Worker {agent_id} component={args.component} use_github={use_github} has_gh={has_gh_cli()} runner={HAS_RUNNER}")
    if pat:
        print(f"PAT present: {pat[:4]}****{pat[-4:] if len(pat)>8 else ''}")
    else:
        print("No PAT — falling back to file queue for claim, but Issues queue will not work. Set GITHUB_PAT.")

    if args.list:
        if use_github:
            issues = ghq.list_pending_issues(args.component)
            for iss in issues[:20]:
                print(f"#{iss['number']} [{','.join( [lb['name'] for lb in iss.get('labels',[])])}] {iss['title']}")
            print(f"Total {len(issues)}")
        else:
            pending = fileq.list_tasks("pending")
            for t in pending[:20]:
                print(f"{t['id']} {t['component']}: {t['title']}")
        return 0

    completed = 0
    while True:
        try:
            fileq.sh("git pull --rebase origin main", cwd=ROOT)

            if use_github:
                issues = ghq.list_pending_issues(args.component)
                # Filter: if component filter, prefer matching
                if not issues:
                    print(f"[{agent_id}] No pending GitHub issues for {args.component}, waiting {args.poll}s")
                    fileq.heartbeat(agent_id, f"worker-{args.component}", {"tasks_completed": completed})
                    fileq.sh("git add swarm/heartbeats && git commit -m 'swarm: heartbeat' --allow-empty && git push origin main || true", cwd=ROOT)
                    if args.once:
                        break
                    time.sleep(args.poll)
                    continue

                issue = issues[0]
                issue_number = issue["number"]
                print(f"[{agent_id}] Attempting atomic claim issue #{issue_number}: {issue['title'][:60]}")
                ok, branch_or_err = ghq.claim_issue_atomic(issue_number, agent_id)
                if not ok:
                    print(f"[{agent_id}] Claim failed: {branch_or_err}")
                    time.sleep(3)
                    continue

                branch = branch_or_err
                # Checkout branch locally (should already exist remote after claim, but we created via API so fetch)
                fileq.sh("git fetch origin", cwd=ROOT)
                checkout_branch(branch)

                # Do work
                success, summary = do_work(issue, branch, agent_id, args.component)

                # Gate
                rc, out, err = fileq.sh("make check", cwd=ROOT)
                if rc != 0:
                    print(f"Gate failed for issue #{issue_number}: {err[-500:]}")
                    fileq.sh(f"git add -A && git commit -m 'swarm: work {issue_number} failed gate' && git push origin {branch} || true", cwd=ROOT)
                    ghq.comment_issue(issue_number, f"❌ Gate failed for {branch} by {agent_id}: {summary}\n\nFix and push.")
                    # Don't mark done, keep claimed — worker can retry or orchestrator re-queues after stale
                    continue

                # Gate green — push and PR
                fileq.sh(f"git add -A && git commit -m 'feat({args.component}): swarm #{issue_number} {issue['title'][:50]}' --allow-empty && git push origin {branch} || true", cwd=ROOT)
                created = create_pr_with_gh(branch, issue_number, issue["title"])
                if created:
                    print(f"[{agent_id}] PR created for issue #{issue_number}, waiting for auto-merge Action")
                    fileq.heartbeat(agent_id, f"worker-{args.component}", {"tasks_completed": completed + 1, "last_pr": branch})
                else:
                    print(f"[{agent_id}] PR creation failed, but branch pushed {branch}")

                completed += 1
                if args.once:
                    break

            else:
                # File queue fallback (existing worker logic)
                pending = fileq.list_tasks("pending")
                if args.component != "general":
                    filtered = [t for t in pending if args.component in t.get("component", "")]
                    if filtered:
                        pending = filtered
                if not pending:
                    print(f"[{agent_id}] No file queue tasks, waiting")
                    if args.once:
                        break
                    time.sleep(args.poll)
                    continue
                task = pending[0]
                if not fileq.try_claim(task["id"], agent_id):
                    time.sleep(2)
                    continue
                success, summary = do_work({"number": 0, "title": task["title"]}, f"swarm/{task['id']}/{agent_id}", agent_id, args.component)
                rc, _, _ = fileq.sh("make check", cwd=ROOT)
                if rc == 0:
                    fileq.complete_task(task["id"], agent_id, summary, "done")
                else:
                    fileq.complete_task(task["id"], agent_id, f"gate failed {summary}", "failed")
                completed += 1
                if args.once:
                    break

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nWorker stopped")
            break
        except Exception as e:
            print(f"Worker error {e}")
            import traceback

            traceback.print_exc()
            time.sleep(args.poll)

    return 0


if __name__ == "__main__":
    sys.exit(main())
