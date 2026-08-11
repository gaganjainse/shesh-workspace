"""Swarm common — file-based queue over GitHub.

GitHub is the only shared state between Arena Agent Mode sessions.
We use git as message bus with atomic push + conflict retry.

Structure in repo root:

swarm/
  queue/<task-id>.json         # pending tasks {id, title, component, priority, created_at, status=pending}
  claims/<task-id>.json        # claimed {task_id, agent_id, claimed_at, branch}
  heartbeats/<agent-id>.json   # {agent_id, role, last_seen, tasks_completed}
  artifacts/<task-id>.json     # result {task_id, agent_id, status=done|failed, summary, commit_sha}
  ledger.jsonl                 # append-only log of all swarm events

Agent ID: <hostname>-<pid>-<timestamp hex>

Claim protocol (to avoid overwrite):
1. Agent creates claims/<task>.json locally
2. git pull --rebase, git add claims/<task>.json, git commit, git push
3. If push fails (conflict — another agent claimed), pull again, check if claim exists, if yes abort this task
4. If push succeeds, you own the task

No real-time pubsub — workers poll: git pull every 30-60s.

Security: PAT loaded via tools/github_auth.py, never logged.
"""

from __future__ import annotations

import json
import pathlib
import random
import socket
import string
import subprocess
import time
from datetime import datetime, UTC

ROOT = pathlib.Path(__file__).resolve().parents[2]
SWARM = ROOT / "swarm"
QUEUE = SWARM / "queue"
CLAIMS = SWARM / "claims"
HEARTBEATS = SWARM / "heartbeats"
ARTIFACTS = SWARM / "artifacts"
LEDGER = SWARM / "ledger.jsonl"


def sh(cmd: str, cwd: pathlib.Path = ROOT) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=30
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return 1, "", f"timeout {e}"


def gen_agent_id(role: str = "worker") -> str:
    host = socket.gethostname()[:8]
    pid = str(os.getpid() if (os := __import__("os")) else "0")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    ts = format(int(time.time()), "x")[-6:]
    return f"{role}-{host}-{pid}-{ts}-{rand}"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_dirs() -> None:
    for d in [QUEUE, CLAIMS, HEARTBEATS, ARTIFACTS]:
        d.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists():
        LEDGER.write_text("")


def append_ledger(event: dict) -> None:
    ensure_dirs()
    event["ts"] = utc_now()
    with LEDGER.open("a") as f:
        f.write(json.dumps(event) + "\n")


def list_tasks(status: str = "pending") -> list[dict]:
    ensure_dirs()
    tasks = []
    for p in QUEUE.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            if data.get("status", "pending") == status:
                tasks.append(data)
        except Exception:
            continue
    # Sort by priority (P0 first) then created_at
    def prio_key(t):
        p = t.get("priority", "P1")
        order = {"P0": 0, "P1": 1, "P2": 2}.get(p, 3)
        return (order, t.get("created_at", ""))
    tasks.sort(key=prio_key)
    return tasks


def heartbeat(agent_id: str, role: str, extra: dict | None = None) -> None:
    ensure_dirs()
    data = {
        "agent_id": agent_id,
        "role": role,
        "last_seen": utc_now(),
        "tasks_completed": extra.get("tasks_completed", 0) if extra else 0,
    }
    if extra:
        data.update(extra)
    (HEARTBEATS / f"{agent_id}.json").write_text(json.dumps(data, indent=2) + "\n")
    append_ledger({"type": "heartbeat", "agent_id": agent_id, "role": role})


def try_claim(task_id: str, agent_id: str) -> bool:
    """Attempt atomic claim via git push. Returns True if we own it."""
    ensure_dirs()
    task_file = QUEUE / f"{task_id}.json"
    claim_file = CLAIMS / f"{task_id}.json"

    if not task_file.exists():
        return False
    if claim_file.exists():
        # Already claimed
        try:
            existing = json.loads(claim_file.read_text())
            if existing.get("agent_id") != agent_id:
                return False
        except Exception:
            return False

    # Create claim locally
    claim = {
        "task_id": task_id,
        "agent_id": agent_id,
        "claimed_at": utc_now(),
        "branch": f"swarm/{agent_id}/{task_id}",
    }
    claim_file.write_text(json.dumps(claim, indent=2) + "\n")

    # Try push with rebase loop (max 3 retries)
    for attempt in range(3):
        # pull rebase
        sh("git pull --rebase origin main", cwd=ROOT)
        # Check again after pull if someone else claimed
        if claim_file.exists():
            try:
                existing = json.loads(claim_file.read_text())
                # If file was overwritten by pull, check content
                if existing.get("agent_id") != agent_id:
                    # conflict — remove our claim file that got recreated?
                    # Actually our claim file would have been merged — if it's not ours, we lost
                    print(f"Task {task_id} already claimed by {existing.get('agent_id')}")
                    # Clean up: remove our version if we created it but pull overwrote?
                    # If pull kept our version, we'd still have ours — so check
                    # Best: if existing claim not ours, abort
                    # Remove local file that may be ours incorrectly
                    if attempt == 0:
                        # The file on disk after pull is the remote one, not ours
                        pass
                    return False
            except Exception:
                pass

        # Ensure our claim file still exists with our id (re-create if pull removed)
        claim_file.write_text(json.dumps(claim, indent=2) + "\n")

        rc, out, err = sh(f"git add {claim_file} && git commit -m 'swarm: claim {task_id} by {agent_id}' && git push origin main", cwd=ROOT)
        if rc == 0:
            append_ledger({"type": "claimed", "task_id": task_id, "agent_id": agent_id})
            print(f"Claimed {task_id} as {agent_id}")
            return True
        else:
            print(f"Claim push failed attempt {attempt+1}: {err[:500]}")
            # pull and retry
            sh("git pull --rebase origin main", cwd=ROOT)
            time.sleep(1 + attempt)

    # Failed to claim after retries
    try:
        claim_file.unlink()
    except Exception:
        pass
    return False


def complete_task(task_id: str, agent_id: str, summary: str, status: str = "done") -> None:
    ensure_dirs()
    artifact = {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": status,
        "summary": summary,
        "completed_at": utc_now(),
    }
    (ARTIFACTS / f"{task_id}.json").write_text(json.dumps(artifact, indent=2) + "\n")

    # Mark task as done in queue
    qfile = QUEUE / f"{task_id}.json"
    if qfile.exists():
        try:
            data = json.loads(qfile.read_text())
            data["status"] = status
            data["completed_by"] = agent_id
            data["completed_at"] = utc_now()
            qfile.write_text(json.dumps(data, indent=2) + "\n")
        except Exception:
            pass

    append_ledger({"type": "completed", "task_id": task_id, "agent_id": agent_id, "status": status})
    # Push
    sh(f"git add {ARTIFACTS / f'{task_id}.json'} {qfile} && git commit -m 'swarm: complete {task_id} by {agent_id} [{status}]' && git push origin main", cwd=ROOT)
