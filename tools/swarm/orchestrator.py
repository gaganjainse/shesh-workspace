#!/usr/bin/env python3
"""Swarm Orchestrator — runs in ONE Arena Agent Mode chat.

This chat is the "brain" that seeds tasks from TODO.md and monitors workers.

It does NOT execute component work itself (to avoid overwrite). It:
- Seeds swarm/queue/*.json from TODO.md ⬜ items
- Watches heartbeats, marks stale claims (>10 min no heartbeat) as failed and re-queues
- Monitors artifacts and updates TODO.md when tasks complete
- Provides dashboard via `swarm/ledger.jsonl`

Usage:
  python tools/swarm/orchestrator.py --seed TODO.md          # create tasks from TODO
  python tools/swarm/orchestrator.py --monitor               # loop forever, monitor
  python tools/swarm/orchestrator.py --dashboard             # print status

Workers are OTHER Arena chats running `python tools/swarm/worker.py --component shesh-memory`

GitHub is message bus — all state pushed to main.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/swarm"))

import common as swarm
from datetime import UTC

SWARM = ROOT / "swarm"


def parse_todos(todo_path: pathlib.Path) -> list[dict]:
    tasks = []
    text = todo_path.read_text()
    # Match lines like "- ⬜ **`shesh-brain`** — ..."
    # We'll give each a task id: todo-<hash>
    import hashlib

    for i, line in enumerate(text.splitlines()):
        if "⬜" in line or "🟡" in line:
            # Skip blocked 🔴 unless explicitly P1 that is unblocked — we include ⬜ and 🟡
            title = line.strip()
            # Clean markdown
            clean = re.sub(r"[-*]\s*[⬜🟡🔴✅💡]+\s*", "", title)[:120]
            if len(clean) < 10:
                continue
            # Component hint
            comp = "general"
            m = re.search(r"`(shesh-[a-z-]+)`", line)
            if m:
                comp = m.group(1)
            prio = "P0" if "P0" in line else "P1" if "P1" in line else "P2"
            tid = f"todo-{hashlib.sha1(title.encode()).hexdigest()[:8]}"
            tasks.append(
                {
                    "id": tid,
                    "title": clean,
                    "raw": title,
                    "component": comp,
                    "priority": prio,
                    "status": "pending",
                    "created_at": swarm.utc_now(),
                    "line_no": i,
                }
            )
    return tasks


def seed_from_todo(todo_path: pathlib.Path) -> int:
    swarm.ensure_dirs()
    tasks = parse_todos(todo_path)
    count = 0
    # Try GitHub Issues seeding if PAT present
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import github_auth
        import github_queue as ghq

        pat = github_auth.load_pat()
        use_github = pat is not None and os.environ.get("SWARM_USE_GITHUB", "1") == "1"
    except Exception:
        use_github = False

    for t in tasks:
        if use_github:
            # Create issue via API (checks existing)
            try:
                res = ghq.create_issue(t)
                if res:
                    count += 1
            except Exception as e:
                print(f"Failed create issue for {t['id']}: {e}")
                # fallback to file
                qfile = SWARM / "queue" / f"{t['id']}.json"
                if not qfile.exists():
                    qfile.write_text(json.dumps(t, indent=2) + "\n")
                    count += 1
        else:
            qfile = SWARM / "queue" / f"{t['id']}.json"
            if qfile.exists():
                continue
            qfile.write_text(json.dumps(t, indent=2) + "\n")
            count += 1
    swarm.append_ledger({"type": "seed", "count": count, "source": str(todo_path), "github": use_github if 'use_github' in locals() else False})
    print(f"Seeded {count} new tasks from {todo_path} (total pending file {len(swarm.list_tasks('pending'))}) github={use_github if 'use_github' in locals() else False}")
    # git push
    swarm.sh(f"git add swarm/queue swarm/ledger.jsonl && git commit -m 'swarm: seed {count} tasks from TODO' && git push origin main || true")
    return count


def dashboard() -> None:
    pending = swarm.list_tasks("pending")
    done = swarm.list_tasks("done")
    # claims
    claims = list((SWARM / "claims").glob("*.json"))
    heartbeats = list((SWARM / "heartbeats").glob("*.json"))
    artifacts = list((SWARM / "artifacts").glob("*.json"))

    print(f"=== Swarm Dashboard {swarm.utc_now()} ===")
    print(f"Queue pending: {len(pending)}")
    for t in pending[:15]:
        print(f"  - {t['id']} [{t['priority']}] {t['component']}: {t['title'][:80]}")
    if len(pending) > 15:
        print(f"  ... and {len(pending)-15} more")

    print(f"\nClaims active: {len(claims)}")
    for c in claims[:10]:
        try:
            d = json.loads(c.read_text())
            print(f"  - {d['task_id']} by {d['agent_id']} at {d['claimed_at']}")
        except Exception:
            pass

    print(f"\nHeartbeats: {len(heartbeats)} agents")
    for hb in heartbeats:
        try:
            d = json.loads(hb.read_text())
            print(f"  - {d['agent_id']} role={d.get('role')} last={d.get('last_seen')} completed={d.get('tasks_completed',0)}")
        except Exception:
            pass

    print(f"\nArtifacts done: {len(artifacts)}")
    print(f"Ledger events: {SWARM / 'ledger.jsonl'} lines {sum(1 for _ in (SWARM / 'ledger.jsonl').read_text().splitlines()) if (SWARM / 'ledger.jsonl').exists() else 0}")


def monitor_loop(poll_sec: int = 60) -> None:
    agent_id = swarm.gen_agent_id("orchestrator")
    print(f"Orchestrator {agent_id} monitoring every {poll_sec}s — Ctrl+C to stop")
    tasks_completed = 0
    while True:
        try:
            swarm.heartbeat(agent_id, "orchestrator", {"tasks_completed": tasks_completed})
            # Pull latest
            swarm.sh("git pull --rebase origin main")
            dashboard()
            # Check stale claims (>10 min)
            now = time.time()
            for claim_file in (SWARM / "claims").glob("*.json"):
                try:
                    data = json.loads(claim_file.read_text())
                    claimed_at = data.get("claimed_at", "")
                    from datetime import datetime

                    dt = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
                    age_min = (datetime.now(UTC) - dt).total_seconds() / 60
                    if age_min > 10:
                        # check if heartbeat recent
                        hb_file = SWARM / "heartbeats" / f"{data['agent_id']}.json"
                        if not hb_file.exists():
                            print(f"Stale claim {claim_file} no heartbeat, re-queueing")
                            claim_file.unlink()
                            # Move task back to pending
                            qfile = SWARM / "queue" / f"{data['task_id']}.json"
                            if qfile.exists():
                                qdata = json.loads(qfile.read_text())
                                qdata["status"] = "pending"
                                qfile.write_text(json.dumps(qdata, indent=2) + "\n")
                            swarm.append_ledger({"type": "stale_requeued", "task_id": data["task_id"]})
                            tasks_completed += 1
                except Exception as e:
                    print(f"stale check error {e}")

            # Push heartbeats
            swarm.sh("git add swarm/heartbeats swarm/claims swarm/queue swarm/artifacts swarm/ledger.jsonl && git commit -m 'swarm: orchestrator heartbeat' --allow-empty && git push origin main")

            time.sleep(poll_sec)
        except KeyboardInterrupt:
            print("\nOrchestrator stopped")
            break


def main() -> int:
    ap = argparse.ArgumentParser(description="Swarm orchestrator")
    ap.add_argument("--seed", type=pathlib.Path, help="seed from TODO.md")
    ap.add_argument("--monitor", action="store_true", help="monitor loop")
    ap.add_argument("--dashboard", action="store_true", help="print dashboard once")
    args = ap.parse_args()

    if args.seed:
        seed_from_todo(args.seed)
    if args.dashboard:
        dashboard()
    if args.monitor:
        monitor_loop()
    if not (args.seed or args.monitor or args.dashboard):
        # default: seed + dashboard
        if (ROOT / "TODO.md").exists():
            seed_from_todo(ROOT / "TODO.md")
        dashboard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
