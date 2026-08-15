# Swarm — GitHub as Command Center for Parallel Arena Sessions

> **Problem:** Arena.ai Agent Mode chats have NO connection between them. You can't spawn a worker from orchestrator. But you can open 3-4 Agent Mode tabs manually and want them to work on different parts of Shesh without overwriting each other.

**Solution:** GitHub repo **IS** the bus. File-based queue + atomic git push for locking.

## How it works

```
Arena Chat 1 (Orchestrator)          Arena Chat 2 (Worker shesh-memory)       Arena Chat 3 (Worker shesh-system)
        |                                      |                                      |
        | seed tasks from TODO.md              |                                      |
        |-> swarm/queue/todo-abc123.json --push--> git pull sees task                  |
        |                                      | try_claim() -> git add claims/... -> push (wins)
        |                                      | work in src/shesh-memory/, make check, push
        |                                      |-> swarm/artifacts/todo-abc123.json --push--> git pull
        | dashboard sees done, updates TODO    |                                      |
        |                                      |                                      | claim different component
```

All via `git pull --rebase` + `git push`. First push wins, second gets conflict and aborts — no overwrite.

## Directory

- `swarm/queue/*.json` — pending tasks {id, title, component, priority, status}
- `swarm/claims/*.json` — claimed {task_id, agent_id, claimed_at}
- `swarm/heartbeats/*.json` — {agent_id, role, last_seen, tasks_completed}
- `swarm/artifacts/*.json` — result {task_id, agent_id, status=done|failed, summary}
- `swarm/ledger.jsonl` — append-only event log

## Quick start

### 1. Orchestrator (ONE chat)

Open **one** Arena chat, paste:

```
Read docs/SESSION_HANDOFF.md FIRST, then docs/SWARM.md
GitHub: gaganjainse/shesh-ecosystem
PAT in GITHUB_PAT env or ~/.config/shesh/github.pat (0600)
Run: cd /home/user && git pull && python tools/swarm/orchestrator.py --seed TODO.md --dashboard
Then: python tools/swarm/orchestrator.py --monitor
```

It seeds queue from TODO.md ⬜ items and monitors.

Leave it open.

### 2. Workers (2-3 chats)

Open **another** Arena chat per component. The GitHub worker is safe-idle
unless a real implementation callback is supplied; it never creates a
marker-only PR:

```
Read docs/SESSION_HANDOFF.md FIRST
GitHub: gaganjainse — you are worker for shesh-memory
PAT same as orchestrator
Run: cd /home/user && git pull && python tools/swarm/worker.py --component shesh-memory
```

Open third:

```
... worker for shesh-system
Run: python tools/swarm/worker.py --component shesh-system
```

They will claim different tasks and work in parallel, each pushing to its own branch `swarm/<agent-id>/<task-id>` then merging to main after gate green.

### 3. Safety

- Each worker checks out its own branch — no direct edit to main until gate green
- Claim via atomic push — if two workers claim same task, one fails and retries next task
- Autopilot gate `make check` runs before any push to main — no red commits
- Heartbeats — orchestrator re-queues stale claims (>10 min no heartbeat)
- No secrets in repo — PAT via env/file, never logged
- Components isolated — shesh-memory worker edits `src/shesh-memory/` only, shesh-system edits `src/shesh-system/` only unless task says otherwise

## Is this actionable?

**Yes, with caveats:**

| Promise | Reality |
|---------|---------|
| No maintenance | Need to open/close Arena chats manually — Arena doesn't auto-spawn |
| No crashing | Git push conflict retry handles race, but if two workers edit same line, merge conflict needs human `git rebase` |
| No overwriting | Branch per task + gate prevents overwrite, but if workers edit same file `manifests/components.toml`, last merged wins — filter tasks by component to avoid |
| Orchestrator | Works, but is just another Arena chat polling GitHub, not a real daemon — if you close it, swarm continues but no re-queue of stale claims |

**Best practice:** 1 orchestrator + 2 workers max — more workers increase git push conflicts. Use component filter to partition work.

## Future improvement

- Use GitHub Issues + Projects API instead of files (better atomicity, labels for component)
- Use GitHub Actions to auto-merge artifact PRs after gate
- Use `gh` CLI to create branch + PR per task, orchestrator merges

But file-based queue already works offline and is what we have now.

## Files

- `tools/swarm/common.py` — claim, heartbeat, ledger
- `tools/swarm/orchestrator.py` — seed + monitor
- `tools/swarm/worker.py` — claim + work loop
- `tools/github_auth.py` — secure PAT loader
- `tools/session_guard.py` — hop detection
