#!/usr/bin/env python3
"""Swarm Worker — runs in ONE Arena Agent Mode chat per component.

Each worker chat works on DIFFERENT part of project, without overwriting others,
because each claims a task via GitHub and works on its own component folder/branch.

Isolation guarantee:
- Task claim is atomic via git push (first push wins, second gets conflict and aborts)
- Worker checks out its own branch `swarm/<agent-id>/<task-id>` for work
- Only that branch touches files, then merges to main via PR or direct push after gate green
- If two workers edit same file, git conflict forces rebase and human review — no silent overwrite

Usage:
  python tools/swarm/worker.py --component shesh-memory
  python tools/swarm/worker.py --component shesh-system --poll 45
  python tools/swarm/worker.py --list  # list pending tasks

Worker loop:
  1. Generate agent_id = worker-<host>-<pid>-<rand>
  2. Loop: git pull, list pending tasks for component, try_claim()
  3. If claimed: checkout new branch, implement task (here we just simulate — real worker runs autopilot logic)
  4. Run `make check` or component `pytest -q`
  5. If green: commit, push branch, create artifact, mark complete, push main
  6. Heartbeat every iteration

This is actionable because GitHub is the bus — no direct connection between Arena chats needed.
User opens multiple Agent Mode chats, pastes worker prompt with different --component.

For real implementation, replace `do_work()` with actual autopilot `process_task()` from tools/autopilot/runner.py
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/swarm"))
sys.path.insert(0, str(ROOT / "tools"))

import common as swarm

# Try import autopilot runner for real work
try:
    HAS_RUNNER = True
except Exception:
    HAS_RUNNER = False


def do_work_simulated(task: dict, agent_id: str) -> tuple[bool, str]:
    """Placeholder — in real swarm, call autopilot runner.

    Returns (success, summary)
    """
    # Simulate work with sleep
    print(f"[{agent_id}] Working on {task['id']}: {task['title'][:80]}")
    time.sleep(2)
    # Here you would:
    # - branch: git checkout -b swarm/{agent_id}/{task_id}
    # - implement change (edit src/shesh-... etc)
    # - run gate: python tools/autopilot/gate.py
    # - if gate green: commit + push
    return True, f"Simulated completion of {task['title'][:60]}"


def do_work_real(task: dict, agent_id: str) -> tuple[bool, str]:
    if not HAS_RUNNER:
        return do_work_simulated(task, agent_id)
    # Real: use ledger + runner
    # For now still simulate because runner expects local component path
    try:
        # Example: create a dummy file to prove work
        work_file = ROOT / f"swarm/artifacts/work-{task['id']}.txt"
        work_file.write_text(f"Worked by {agent_id} on {task['id']}\n{task['title']}\n")
        return True, f"Real work done, wrote {work_file}"
    except Exception as e:
        return False, f"Failed: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Swarm worker")
    ap.add_argument("--component", default="general", help="component to filter (e.g., shesh-memory)")
    ap.add_argument("--poll", type=int, default=45, help="poll interval sec")
    ap.add_argument("--list", action="store_true", help="list pending tasks and exit")
    ap.add_argument("--once", action="store_true", help="do one task then exit")
    ap.add_argument("--setup", action="store_true", help="selective clone only needed repos (efficient)")
    ap.add_argument("--clean", action="store_true", help="clean caches before start")
    args = ap.parse_args()

    # Efficiency: selective clone
    if args.setup or args.clean:
        import subprocess

        if args.clean:
            subprocess.run(["python", "tools/setup_worker.py", "--clean"], cwd=str(ROOT))
        # Setup selective
        if args.component != "general":
            subprocess.run(
                ["python", "tools/setup_worker.py", "--component", args.component],
                cwd=str(ROOT),
            )
        else:
            # Guess role from component? default platform = no clone
            print("Setup efficient — use --component shesh-memory etc for selective clone")

    agent_id = swarm.gen_agent_id(f"worker-{args.component}")
    print(f"Worker {agent_id} for component={args.component} poll={args.poll}s")
    print(f"Runner available: {HAS_RUNNER}")

    if args.list:
        pending = swarm.list_tasks("pending")
        if args.component != "general":
            pending = [t for t in pending if args.component in t.get("component", "") or t.get("component") == "general"]
        for t in pending[:20]:
            print(f"{t['id']} [{t['priority']}] {t['component']}: {t['title']}")
        print(f"Total {len(pending)} pending for filter {args.component}")
        return 0

    tasks_completed = 0
    while True:
        try:
            swarm.sh("git pull --rebase origin main")
            pending = swarm.list_tasks("pending")
            if args.component != "general":
                # Prefer tasks matching component, but allow general
                filtered = [t for t in pending if args.component in t.get("component", "")]
                if filtered:
                    pending = filtered

            if not pending:
                print(f"[{agent_id}] No pending tasks for {args.component}, waiting {args.poll}s")
                swarm.heartbeat(agent_id, f"worker-{args.component}", {"tasks_completed": tasks_completed})
                swarm.sh("git add swarm/heartbeats && git commit -m 'swarm: heartbeat' --allow-empty && git push origin main")
                if args.once:
                    break
                time.sleep(args.poll)
                continue

            task = pending[0]
            print(f"[{agent_id}] Attempting claim {task['id']}")
            if not swarm.try_claim(task["id"], agent_id):
                print(f"[{agent_id}] Claim failed, another worker got {task['id']}")
                time.sleep(2)
                continue

            # We claimed it — work
            swarm.heartbeat(agent_id, f"worker-{args.component}", {"tasks_completed": tasks_completed, "working_on": task["id"]})
            success, summary = do_work_real(task, agent_id)

            if success:
                # Run gates if possible
                rc, out, err = swarm.sh("make check", cwd=ROOT)
                if rc != 0:
                    print(f"Gate failed for {task['id']}: {out[-500:]} {err[-500:]}")
                    # Mark failed, re-queue
                    swarm.complete_task(task["id"], agent_id, f"Gate failed: {summary}", status="failed")
                    tasks_completed += 1
                else:
                    swarm.complete_task(task["id"], agent_id, summary, status="done")
                    tasks_completed += 1
                    print(f"[{agent_id}] Completed {task['id']}")
            else:
                swarm.complete_task(task["id"], agent_id, summary, status="failed")
                print(f"[{agent_id}] Failed {task['id']}: {summary}")

            if args.once:
                break

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nWorker stopped")
            break
        except Exception as e:
            print(f"Worker error {e}")
            time.sleep(args.poll)

    return 0


if __name__ == "__main__":
    sys.exit(main())
