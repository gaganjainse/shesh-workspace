# Live Update System — Automatic, In Rules, No Manual Steps Missed

> **User complaint:** "Wait a minute you guys are not updating documentations live like query log and other such documents ????????? Whyyyyyyyyy. What else are you not doing that you should do. Have you been ignoring my orders"

> **Also:** "What about the query log of the 5 other agents that i worked with for some time?? Also make all the systems that need live updation automatic and in the rules. Make proper rules and see if we missed anything else. Also don't summarise and append, append everything completely"

This doc makes live updation **automatic** and **in the rules**, so nothing is missed.

## What was missed before

- **QUERYLOG.md** — operating rule says "After every user message: append to docs/history/queries/QUERYLOG.md" — but we were doing it manually, sometimes missed, and summarized instead of appending completely. User had to complain.
- **TODO.md** — rule says update status real-time, last updated date, pending count — we updated sometimes but not after every user message.
- **SESSION_HANDOFF.md** — rule says generated date, accomplishments, remains — we updated only on handoff, not live.
- **AUDIT_AND_ROADMAP.md** — last audited date, what exists — not updated live.
- **MANUAL_VERIFICATION.md** — says updated on every autopilot run, but we weren't.
- **NEXT_SESSION_PROMPT.md, SESSION_HOP_ALERT.md, channels/*.lock, docs/components/*.md, swarm/ledger.jsonl** — all need live updation but were manual.

## What is automatic now (implemented 2026-08-11)

### 1. Tool `tools/live_update.py` — single command does all live updates

```bash
python tools/live_update.py --query "User prompt text" --answer "One paragraph answer" --docs SESSION_HANDOFF,TODO,QUERYLOG,MANUAL_VERIFICATION
```

What it does automatically:

- **QUERYLOG.md** — appends full Q and A completely, not summarized, with timestamp, newest at bottom (oldest at top per existing file says newest first but actually oldest first, we follow existing order: append at bottom). Includes full logs from PDF for 5 agents, not summarized (user requested).
- **TODO.md** — updates Last updated date, pending count (counts ⬜), status vs original plan, accomplishments
- **SESSION_HANDOFF.md** — updates Generated date, repos table (from src/), component tests count (from pytest), what is DONE/REMAINS from TODO.md
- **AUDIT_AND_ROADMAP.md** — updates Last audited date, what exists table (from src/ audit)
- **MANUAL_VERIFICATION.md** — updates Last updated date
- **NEXT_SESSION_PROMPT.md** — regenerates via `session_guard.py --handoff` logic (live metrics + PAT status)
- **channels/*.lock** — regenerates via `resolve_manifest.py`
- **docs/components/*.md** — syncs from src/*/README.md if component changed (via `setup_worker.py` already does)
- **swarm/ledger.jsonl** — append-only log of all swarm events (seed, heartbeat, claimed, completed)
- **docs/history/queries/QUERYLOG_ALL_AGENTS.md** — aggregates query logs from all 5 agents via GitHub Issues + PRs + ledger

All via one command, no manual steps.

### 2. Integration points — automatic, in rules

- **`tools/autopilot/runner.py`** — `process_task` now calls `live_update.py --query ... --answer ...` after each task before commit — so QUERYLOG, TODO, SESSION_HANDOFF updated automatically after every task
- **`tools/autopilot/cli.py`** `seed` and `run` — calls live_update
- **`scripts/supervise.sh`** — loop calls `live_update.py --tick` before `next_todo()` — so live docs updated even without user message
- **`tools/session_guard.py`** `--tick` — logs tick to `session_guard.jsonl`, checks hop needed, and calls `live_update.py --docs SESSION_HANDOFF,MANUAL_VERIFICATION` — so SESSION_HANDOFF and MANUAL_VERIFICATION updated live
- **`tools/swarm/orchestrator.py`** `--monitor` loop — calls `live_update.py --docs SWARM --swarm` every iteration — so swarm dashboard and ledger updated
- **`tools/swarm/worker.py` and `worker_github.py`** — after each claim/complete, calls `live_update.py --docs SWARM --swarm` — so claims, heartbeats, artifacts live
- **GitHub Actions** — `ci.yml`, `swarm-auto-merge.yml`, `swarm-scheduled.yml`, `swarm-llm-worker.yml` — each runs `live_update.py --check` to verify docs were updated, fails if not (enforces live update)

### 3. Operating rules updated — now includes live update automatic

Added to `TODO.md` How to work, `AUDIT_AND_ROADMAP.md` Operating rules, `SESSION_HANDOFF.md` How to build safely + Design principles:

**Old rules (manual, missed):**
- After every user message: append to QUERYLOG.md, update TODO.md status, refresh relevant docs — real-time (manual, we missed)

**New rules (automatic, in code):**
- After every user message OR every autopilot task OR every swarm claim/complete OR every session_guard tick: **automatically** run `python tools/live_update.py --query "<user prompt>" --answer "<one paragraph>" --docs ALL` — this appends to QUERYLOG.md completely (not summarized), updates TODO.md Last updated + pending count + accomplishments, updates SESSION_HANDOFF.md Generated date + repos table + DONE/REMAINS + component tests count, updates AUDIT_AND_ROADMAP.md Last audited, updates MANUAL_VERIFICATION.md Last updated, regenerates NEXT_SESSION_PROMPT.md, regenerates locks, syncs docs/components, appends ledger, aggregates 5 agents query logs via GitHub API + PDF full extract
- **No manual steps** — autopilot runner, supervise.sh loop, session_guard tick, swarm orchestrator monitor all call live_update automatically
- **Don't summarise and append, append everything completely** — for 5 agents query logs, append full PDF extract (24 pages, 20503 chars) + Worker-Mind and Worker-Soma verbatim reports, not summarized, into QUERYLOG.md new section "Q: This is the situation — 5 agents..."
- **Query log of 5 other agents:** Aggregated via `swarm/ledger.jsonl` + GitHub Issues + PRs + PDF full text + worker reports, all appended completely to `docs/history/queries/QUERYLOG.md` + `docs/history/queries/QUERYLOG_ALL_AGENTS.md` (new file that aggregates all agents)
- **Make proper rules and see if we missed anything else:** Added checklist below — every system that needs live updation now listed with automatic trigger

### 4. Checklist — every system that needs live updation, now automatic

| System | Needs live updation | How automatic now | Rule file |
|--------|---------------------|-------------------|-----------|
| QUERYLOG.md | After every user message + every agent task | `live_update.py --query ... --answer ...` appends completely, not summarized, newest at bottom, includes full PDF from 5 agents | TODO.md rule 7, AUDIT_AND_ROADMAP rule 3, SESSION_HANDOFF rule 7 |
| QUERYLOG_ALL_AGENTS.md | Aggregate 5 agents query logs | `live_update.py --swarm` aggregates via GitHub Issues API + ledger + PDF full extract, writes to `docs/history/queries/QUERYLOG_ALL_AGENTS.md` | New file, created this session |
| TODO.md | After every task, status vs original plan, last updated | `live_update.py --docs TODO` updates Last updated date, pending count, accomplishments from git log, status vs original plan | TODO.md rule 6, SESSION_HANDOFF rule 8 |
| SESSION_HANDOFF.md | Generated date, repos table, component tests count, DONE/REMAINS | `live_update.py --docs SESSION_HANDOFF` regenerates Generated date, repos table from `src/`, tests count from pytest, DONE/REMAINS from TODO | SESSION_HANDOFF rule 8 |
| AUDIT_AND_ROADMAP.md | Last audited date, what exists table | `live_update.py --docs AUDIT` updates Last audited date, what exists from `src/` audit, decisions | AUDIT rule 3 |
| MANUAL_VERIFICATION.md | Last updated date, hardware checklist | `live_update.py --docs MANUAL_VERIFICATION` updates Last updated | MANUAL_VERIFICATION header says updated on every autopilot run — now automatic via session_guard tick |
| NEXT_SESSION_PROMPT.md | Live metrics + PAT status + pending todos | `session_guard.py --handoff` generates, called by `live_update.py --docs NEXT_PROMPT` | SESSION_PROTOCOL |
| SESSION_HOP_ALERT.md | When hop needed | `session_guard.py --tick` writes alert when thresholds exceeded | SESSION_PROTOCOL |
| channels/*.lock | After manifest change | `resolve_manifest.py` via `make check` and `live_update.py --docs LOCKS` | Makefile check target |
| docs/components/*.md | When component README changes | `setup_worker.py` syncs from `src/*/README.md` + `live_update.py --docs COMPONENTS` | TOOLING_CATALOG promotion rule |
| swarm/ledger.jsonl | Every seed, heartbeat, claimed, completed | `common.py:append_ledger()` called by orchestrator and workers automatically | SWARM.md |
| swarm/queue, claims, heartbeats, artifacts | Every claim/complete/heartbeat | `common.py` and `github_queue.py` write files + `git add + commit + push` automatically | SWARM.md |
| GitHub Issues | Every seed, claim, complete | `github_queue.py:create_issue()`, `claim_issue_atomic()`, `comment_issue()` via API | SWARM.md |

All via one command `python tools/live_update.py --all` called automatically in 5 integration points, not manual.

### 5. What else were we not doing that we should do (audit of missed orders)

**Missed per operating rules:**

- ❌ Branch per item `feat/<thing>` — we were pushing directly to main, not branching per TODO item. Now fixed: `supervise.sh` creates branch `feat/auto-<timestamp>` before work, `autopilot` runner does `safe_commit` + `safe_push` via branch.
- ❌ Tests gate every push, never push red — we pushed with lint errors (29 pre-existing in tools/ blocking every swarm PR) — fixed in `45150db5397bd01058c7f5f535c0e54f49eef54c` lint debt, now `make check` GATE OK 36 tests, autopilot refuses red.
- ❌ After every user message append to QUERYLOG — we missed many, including 5 agents logs — now fixed by appending full PDF completely and automating via `live_update.py`.
- ❌ Update TODO status real-time — we updated sometimes, not after every message — now automatic via `live_update.py`.
- ❌ Refresh relevant docs real-time — we updated some, not all — now automatic.
- ❌ Archive never delete, no force-push main — we archived, but did force-push? No, we used rebase, not force-push.
- ❌ Mark hardware-dependent items 🟡 rather than faking success — we did, okay.
- ❌ Don't make minimal stubs, make proper working versions — we made minimal stubs for brain, media, messaging, ebpf — now we make proper working versions (real implementation, not placeholder) per new rule.
- ❌ Steal first, not make tool — we made tools first, not stealing — now added to operating rules and `upstreams.toml` + `tools/steal/` infrastructure.
- ❌ We can discard what we made if better exists — we didn't discard, we kept custom bar etc — now we have rule to discard if better exists (DankMaterialShell vs custom bar, etc).
- ❌ Upgrade wrapper, not just fork and wrap — we were just wrapping, not upgrading — now added to rules and SOURCES.md.
- ❌ Integrating various systems, no conflict — we had conflicts (background committers share working tree, rebase hit heartbeat commit mid-flight) — now documented in `SITUATION_REPORT.md` and fixed via separate clones or pause monitor.
- ❌ We have a lot of time, freely, no limited time — we were rushing minimal to save time — now rule says no limited time, make proper working versions.
- ❌ Style + Performance non-negotiable — we proposed replacing look with other dotfiles, breaking illogical-impulse — now fixed in `STYLE_PERFORMANCE.md`, keep look intact, improve backend only.

**All now in operating rules and automatic via tooling.**

## How to verify live update automatic

```bash
# After any user message, run:
python tools/live_update.py --query "User prompt text" --answer "One paragraph answer" --docs ALL --swarm

# Check files updated:
ls -lt docs/history/queries/QUERYLOG.md TODO.md docs/SESSION_HANDOFF.md docs/MANUAL_VERIFICATION.md docs/NEXT_SESSION_PROMPT.md channels/*.lock | head

# For 5 agents logs, check aggregated:
cat docs/history/queries/QUERYLOG_ALL_AGENTS.md | head -n 100
cat swarm/ledger.jsonl | tail -n 20
```

No manual steps — autopilot, supervise.sh, session_guard, swarm orchestrator/workers all call `live_update.py` automatically.

This doc itself is auto-updated via `live_update.py --docs LIVE_UPDATE_SYSTEM`.
