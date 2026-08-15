# SWARM — Multi-Session Parallel Work via GitHub as Bus (PROPER IMPLEMENTATION DONE)

> **Status 2026-08-11: Future improvements IMPLEMENTED — Issues + Projects API + atomic lock + gh CLI PR + auto-merge Action**

TL;DR: Open 1 orchestrator + 2-3 workers in Arena.ai. They coordinate ONLY through GitHub (Issues + git refs + PRs). No direct chat-to-chat, no overwrite, no manual maintenance beyond opening tabs. PAT encrypted with password, auto-prompted each new session.

## Why

- Single Arena session: snapshot 128 MB / 10k files, slows after 60 min, context overflows — you experienced session hops.
- Big project: 19 components, 40 docs, 238 tests — one session can't finish TODO.
- Solution: parallel sessions, different components, GitHub as bus.

## Architecture — Two Queue Backends (file offline + GitHub Issues proper)

### Backend 1: File queue (offline fallback, original)

```
swarm/
  queue/<task-id>.json       pending {id,title,component,priority,status}
  claims/<task-id>.json      claimed {task_id, agent_id, claimed_at, branch}
  heartbeats/<agent-id>.json agent alive
  artifacts/<task-id>.json   result done/failed
  ledger.jsonl               append-only log
```

Claim via atomic git push: `git add claims/... + commit + push` — first push wins, second gets `[rejected] fetch first` and aborts.

Branch per task: `swarm/<agent-id>/<task-id>` — work isolated, gate before merge.

### Backend 2: GitHub Issues + Projects + atomic git ref lock (PROPER — implemented 2026-08-11)

**Queue = GitHub Issues** with labels: `swarm`, `swarm:pending`, `component:shesh-memory`, `P0`/`P1`/`P2`

- **Create:** `tools/swarm/github_queue.py:create_issue(task)` — POST `/repos/{owner}/{repo}/issues` — checks existing by task id in title to avoid dup
- **List:** `list_pending_issues(component)` — GET `/issues?labels=swarm:pending&state=open` — client filter by component
- **Atomic claim:** `claim_issue_atomic(issue_number, agent_id)`:
  1. **Lock ref** `refs/heads/swarm/claims/issue-<N>` — POST `/git/refs` with main SHA
     - GitHub returns **422 if ref exists** → already claimed → fail → atomic CAS
     - We tested: agent-A creates lock → 201, agent-B tries same lock → 422 already claimed
  2. If lock acquired, create **work branch** `swarm/issue-<N>/<agent-id>` from main SHA
  3. Label issue `swarm:claimed`, remove `swarm:pending`, comment with agent_id + branches + timestamp

This is **truly atomic** — lock ref is single per issue, not per agent, so second claim always fails.

- **Work:** checkout work branch locally, implement, `make check`, push
- **PR:** `create_pr(branch, issue_number, title)` — POST `/pulls` head=work_branch base=main, body `Closes #N`
  - Also via gh CLI: `gh pr create --title --body --base main --head <branch> --label swarm`
- **Auto-merge:** `.github/workflows/swarm-auto-merge.yml` — triggers on `pull_request` with `head_ref=swarm/*`
  - Runs ruff, pytest ecosystem, license gate, resolve locks, component gates `src/shesh-*/tests`
  - If green: `gh pr review --approve` + `gh pr merge --squash --auto --delete-branch`
  - On success: comments issue `✅ PR #N auto-merged`, edits labels `swarm:pending,swarm:claimed → swarm:done`, closes issue
  - On failure: comments `❌ gate failed`

**Projects API (optional):** If `GITHUB_PROJECT_NUMBER` set, `add_issue_to_project()` via GraphQL mutation `addProjectV2ItemById` — needs PAT with `project` scope + `GITHUB_PROJECT_ID` env with project node id. Prints skip if not configured.

**Offline fallback:** If PAT missing, `github_queue.py` falls back to file queue (`common.py:list_tasks`).

### Orchestrator vs Workers

- **Orchestrator** `tools/swarm/orchestrator.py`:
  - `--seed TODO.md` — parses ⬜/🟡 from TODO.md (regex), creates task id `todo-<sha>`, component from `` `shesh-*` ``, priority P0/P1/P2
    - If PAT present and `SWARM_USE_GITHUB=1` (default), creates **GitHub Issues** via `github_queue.create_issue()` (checks dup), else file queue `swarm/queue/*.json`
  - `--dashboard` — prints pending, claims, heartbeats, artifacts, ledger lines
  - `--monitor` — loop every 60s: `git pull --rebase`, heartbeat, dashboard, re-queue stale claims >10 min no heartbeat, push

- **Worker file** `tools/swarm/worker.py` — original file queue, `try_claim()` via git push, `do_work()` placeholder (would call `tools/autopilot/runner.py:process_task`), gate, `complete_task()`

- **Worker GitHub** `tools/swarm/worker_github.py` — safe implementation:
  - `--component shesh-memory --poll 45 --list --github`
  - Requires a real implementation callback: `--executor module:function` or `SHESH_WORKER_EXECUTOR`. Without one it polls idle and never claims an issue or creates a marker-only PR.
  - Lists pending Issues in P0/P1/P2 order, skips `swarm:blocked`/blocked prose, atomically claims via a lock ref, checks out the work branch, runs the callback, gates with `make check`, refuses empty commits, pushes through `git_askpass.py`, and creates a PR only after a successful push.
  - Failed/no-op/gate/push work releases its claim and restores `swarm:pending`; a pushed branch is preserved if only PR creation fails.
  - `github_auth.py` supplies temporary `GIT_ASKPASS`/`GH_TOKEN` environment values without putting secrets in URLs or Git config.
  - Detects `gh` CLI via `shutil.which("gh")`.

You open **1 orchestrator + N workers** (N=2-3). A worker without an executor is intentionally safe idle; a real executor may be an agent callback or a separately reviewed automation worker.

## Is it actionable? (Was future improvement, now DONE)

| Question | Old | Now Proper |
|----------|-----|------------|
| Issues + Projects API instead of files? | Future | **DONE**: `github_queue.py` uses Issues API with labels `swarm`, `swarm:pending`, `component:X`, `P0`; atomic lock via `refs/heads/swarm/claims/issue-N`; Projects V2 via GraphQL optional |
| Auto-merge artifact PRs after gate? | Future | **DONE**: `.github/workflows/swarm-auto-merge.yml` runs on `swarm/*` PRs, ruff+pytest+license+locks+component tests, then `gh pr review --approve` + `gh pr merge --squash --auto --delete-branch`, comments issue, labels `swarm:done` |
| gh CLI branch + PR per task? | Future | **DONE**: `worker_github.py` uses `gh pr create` if available, else API; branch `swarm/issue-N/agent-id`; PR body `Closes #N` |
| No crash/overwrite? | Branch per task + atomic file push | **Branch per task + atomic lock ref** — second claim gets 422, no overwrite; PR merge conflict forces rebase |
| No maintenance? | Open tabs manually | Same — Arena can't auto-spawn, but workers auto-poll and re-queue stale |
| Orchestrator as command center? | File bus | **Issues as bus + file fallback** — GitHub is workspace, `swarm/` still exists for ledger/artifacts |

**Verdict:** Fully actionable for 2-4 parallel sessions with component partitioning. Tested real API: created issue #1/#2, claim A succeeds, claim B fails `already claimed (lock exists)`, branches deleted, issues closed — PAT works.

## How to start swarm (copy-paste)

### Prerequisites (once, secure PAT)

```bash
# Encrypted PAT with password — you already have it
ls ~/.config/shesh/
cat ~/.config/shesh/github.pat.enc  # encrypted JSON salt+token 600
# Plain is auto-deleted on handoff for security — next session will need password

# Decrypt (auto-prompted in new session)
python tools/secure_pat.py --prompt
# Enter password: <YOUR_ENCRYPTION_PASSWORD>
# -> writes ~/.config/shesh/github.pat 600
python tools/github_auth.py --check  # shows gith****Q0WZ len 93

# Ensure git
git config --global user.name "Gagan Jain"
git config --global user.email "gagan.jain.se@gmail.com"
```

### Orchestrator (tab 1) — Issues queue

```bash
Read docs/SESSION_HANDOFF.md FIRST, then docs/SWARM.md

You are orchestrator for shesh-ecosystem, GitHub gaganjainse/shesh-ecosystem
PAT encrypted at ~/.config/shesh/github.pat.enc — agent will ask password

cd /home/user && git pull origin main && python tools/session_guard.py --status
# If NEED_PASSWORD → enter <YOUR_ENCRYPTION_PASSWORD> when asked via ask_user UI
python tools/github_auth.py --check
make check

# Seed Issues from TODO (also file queue fallback)
SWARM_USE_GITHUB=1 python tools/swarm/orchestrator.py --seed TODO.md --dashboard

# Monitor
python tools/swarm/orchestrator.py --monitor
```

### Workers (tabs 2-3) — GitHub Issues + PRs

```bash
# Tab 2 — memory
Read SESSION_HANDOFF.md FIRST, then SWARM.md
You are worker for shesh-memory, GitHub gaganjainse/shesh-ecosystem
PAT same — will be auto-decrypted after password prompt

cd /home/user && git pull
python tools/swarm/worker_github.py --component shesh-memory --github --poll 45

# Tab 3 — system
python tools/swarm/worker_github.py --component shesh-system --github --poll 45

# Or file queue fallback (offline):
python tools/swarm/worker.py --component shesh-memory
```

### Session hopping WITH swarm + secure PAT

1. Worker runs `session_guard.py --tick` before task — if hop needed, finishes task, pushes branch + PR, exits
2. Handoff: `python tools/session_guard.py --handoff` — generates NEXT_SESSION_PROMPT.md + deletes plain PAT, keeps enc
3. Close tab, open new, paste NEXT_SESSION_PROMPT.md — agent detects `enc_exists True plain_exists False need_password True` → automatically asks for password via ask_user UI → you give <YOUR_ENCRYPTION_PASSWORD> → decrypts → plain 600 → continues from queue (no overlap, claim already completed)
4. Orchestrator same — new orchestrator tab picks up ledger, re-queues stale after 10 min

No central server.

## Files

- `tools/secure_pat.py` — encrypt/decrypt PAT with password PBKDF2HMAC 200k + Fernet, --store/--prompt/--check/--handoff, 600 perms
- `tools/github_auth.py` — secure PAT loader (env > plain 600 > enc+password > gh hosts.yml), refuses world-readable, never logs value, `needs_password()` check
- `tools/session_guard.py` — hop detection (100 MB / 8000 files / 60 min / 5s latency / 20 uncommitted), writes ALERT, generates NEXT_SESSION_PROMPT with PAT status, on --handoff deletes plain for security
- `tools/swarm/common.py` — file queue fallback: gen_agent_id, list_tasks, try_claim via git push, heartbeat, complete_task
- `tools/swarm/github_queue.py` — **PROPER** Issues queue: create_issue, list_pending_issues, claim_issue_atomic via lock ref `swarm/claims/issue-N` (atomic 422), comment_issue, create_pr, close_issue, add_issue_to_project via GraphQL
- `tools/swarm/orchestrator.py` — seed TODO → Issues or file queue, dashboard, monitor stale claims, heartbeat
- `tools/swarm/worker.py` — file queue worker
- `tools/swarm/worker_github.py` — **PROPER** Issues worker: atomic claim, checkout work branch, do_work, gate make check, push branch, PR via gh or API, artifact
- `.github/workflows/swarm-auto-merge.yml` — auto-merge swarm/* PRs if gates green (ruff, pytest, license, locks, component tests), approve + squash + delete-branch + comment issue + label done
- `swarm/` — queue, claims, heartbeats, artifacts, ledger.jsonl, README
- `docs/SESSION_PROTOCOL.md` — 60-sec handoff + PAT password flow
- `docs/NEXT_SESSION_PROMPT.md` — auto-generated paste for next session with live metrics + PAT status
- `docs/GETTING_STARTED.md`, `docs/history/adr/`, etc.

## Security

- PAT never committed — `.gitignore` has `.config/shesh/` and `.config/gh/`
- Plain `github.pat` 600, enc `github.pat.enc` 600, `~/.config/shesh/` 700
- Encrypted with PBKDF2HMAC-SHA256 200k + Fernet, salt random 16 bytes — needs password to decrypt
- On handoff, plain deleted, enc kept — next session needs password (ask_user UI)
- `github_auth.py` redacts `ghp_****`, refuses world-readable file, never logs value
- Swarm files contain only agent_id, not token
- Provenance via `scripts/sign_artifacts.py` SHA256 + SLSA, optional sigstore cosign keyless

## Future (now optional)

- Use GitHub Projects board custom fields component/priority/status — `GITHUB_PROJECT_NUMBER` + `GITHUB_PROJECT_ID` env, GraphQL `addProjectV2ItemById` already stubbed
- Dedicated `shesh-swarm` repo as pure bus (currently reuse shesh-ecosystem to avoid new repo)
- Auto-scale workers via GitHub Actions self-hosted runners (instead of manual Arena tabs)

---

## Proper workspace layout (post multi-tab incident, 2026-08-11)

Lessons from running 5 agent tabs + Actions concurrently:

1. **Daemons never share your checkout.** Run them via `tools/swarm/daemon.sh start [component]` — it maintains an isolated clone at `$SHESH_STATE/swarm-tree` with its own `.git`, so heartbeat/seed commits can never land on your feature branch (previously: rebase conflicts, fixes committed onto worker branches). `daemon.sh status|logs|stop` give pids, heartbeat freshness and real log files.
2. **Long-running tools are line-buffered** (`sys.stdout.reconfigure`) — piped/nohup logs appear in real time. Heartbeat files remain the ground-truth liveness signal.
3. **`session_guard.py --status/--tick` are read-only.** Only explicit `--handoff` regenerates the prompt and deletes the plain PAT. (A hop advisory used to nuke the plain PAT out from under running daemons.)
4. **Sandbox snapshots wipe `.git/config` and site-packages** — after any restore, run `bash scripts/bootstrap_workspace.sh` (idempotent: pip toolchain, git identity, PAT-based credential helper, optional `GITHUB_PAT_PASSWORD` decrypt, gate).
5. **The 24/7 loop lives on GitHub, not in chat tabs.** `swarm-scheduled.yml` (hourly janitor) + `swarm-llm-worker.yml` (2-hourly) + `swarm-auto-merge.yml` kept working with zero tabs open. Chat agents are turn-based: use them for curation, deep fixes, and review — daemons for plumbing.
6. **Workers fail closed without an executor** (`--executor module:function` / `SHESH_WORKER_EXECUTOR`). No executor → claim released back to `swarm:pending`. No more placeholder PRs closing real TODOs.
